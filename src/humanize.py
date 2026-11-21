"""Humanize the final text posts with open-humanizer (vendored UNMODIFIED in third_party/open-humanizer/).

The package runs an adversarial Writer <-> Critic loop over a text: the Critic (an LLM) scores how machine-like it reads, the Writer rewrites it with more
varied rhythm and less predictable wording. Here it sits between the fact-check and captions.finalize_posts, behind guards, because a rewrite can break
what the rest of the pipeline worked for. The package itself is used as it is; everything below only decides WHAT to give it and WHETHER to keep the result.

What is sent: only the body of a post. The hook (first block, already scored and fact-checked), any block that carries the DM keyword (the CTA), hashtag lines
and lines with links or @mentions stay verbatim and never leave the machine. Posts with a body under MIN_BODY_WORDS are skipped (too short for the loop to help).
What is kept: a rewrite is accepted ONLY if every check passes (same numbers, same names/keywords/hashtags, no new em dashes or markdown, same paragraph
structure, length within bounds, no new marketing-rule break, no language switch, and the Critic did not score it worse). Otherwise the original stays.
Fail-open: no key, no package, a rate limit, a timeout or any error means the original post, and a line in the draft says why. Nothing here can stop the day.

LLM: Groq through its OpenAI-compatible endpoint, keys rotated like the other agents (llm.groq_keys), a model with its own rate-limit bucket (not the one the
writer and planner use). Env: HUMANIZE=0 switches it off, HUMANIZE_MODEL, HUMANIZE_TARGET (Critic AI% to stop at, default 15), HUMANIZE_BASE_URL and
HUMANIZE_API_KEY (any other OpenAI-compatible endpoint), HUMANIZE_BUDGET (seconds for the whole step, default 150), HUMANIZE_DEBUG=1 (print the traceback of a failed call).
"""
from __future__ import annotations

import contextlib
import os
import re
import sys
import time

from . import captions, llm, marketingskills
from .config import ROOT

VENDOR = ROOT / "third_party" / "open-humanizer"
BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "openai/gpt-oss-20b"
MIN_BODY_WORDS = 30
MAX_KEYS = 3                      # keys tried per post when one is rate limited or refused
PLATFORM_ORDER = ("linkedin", "instagram", "bluesky")

HOUSE_RULES = """HOUSE RULES (they override everything above wherever they conflict):
This is a social media post written by a freelance web developer in India for small-business owners. Keep it clear and plain: a stranger must understand every sentence on the first read. No slang, no idiom that needs explaining, no journalist voice.
Keep the language, names, numbers, prices, product names, words in CAPITALS, hashtags, @mentions and links exactly as they are. Do not add any fact, number, example, client, promise or claim, and do not make any sentence more salesy or more dramatic.
Never use em dashes or en dashes. No "it's not X, it's Y" constructions, no stacked rhetorical questions, no hype words, no lists or bullets.
Keep every emoji exactly where it is. Keep the SAME paragraphs (one blank line between them) and about the same length (within 10%). Vary sentence length and use contractions only where they sound natural: one real person talking."""

_NUM = re.compile(r"\d[\d,.]*\d|\d")
_state: dict = {}


def enabled() -> bool:
    on = os.getenv("HUMANIZE", "1").strip().lower() not in ("0", "false", "off", "no")
    return on and bool(os.getenv("HUMANIZE_API_KEY") or llm.groq_keys())


def _load():
    """(HumanizerPipeline, PromptManager) from the vendored package. ImportError when openai/pydantic are not installed."""
    if "pm" not in _state:
        if str(VENDOR) not in sys.path:
            sys.path.insert(0, str(VENDOR))
        from open_humanizer import HumanizerPipeline
        from open_humanizer.prompt_manager import PromptManager
        _state["pipeline"], _state["pm"] = HumanizerPipeline, PromptManager
    return _state["pipeline"], _state["pm"]


def _engine(key: str):
    """One pipeline on one key. max_retries=0 so a rate limit fails at once and the next key is tried instead of waiting."""
    from openai import OpenAI
    pipeline, _ = _load()
    base = os.getenv("HUMANIZE_BASE_URL") or BASE_URL
    model = os.getenv("HUMANIZE_MODEL") or DEFAULT_MODEL
    return pipeline(api_key=key, base_url=base, model_name=model, client=OpenAI(api_key=key, base_url=base, max_retries=0, timeout=60))


@contextlib.contextmanager
def _house_rules():
    """Append our rules to the Writer's system prompt for the duration of one call, then restore the package exactly as it was."""
    _, pm = _load()
    orig = pm.get_humanizer_system_prompt
    pm.get_humanizer_system_prompt = staticmethod(lambda: orig() + "\n\n" + HOUSE_RULES)
    try:
        yield
    finally:
        pm.get_humanizer_system_prompt = staticmethod(orig)


def _nums(t: str) -> list[str]:
    return sorted({x.strip(",.") for x in _NUM.findall(t or "")})


def _protected_tokens(t: str) -> set[str]:
    """Things a rewrite must not lose: CAPS words (the keyword, SEO), CamelCase brands, names in the middle of a sentence, hashtags, mentions, links."""
    toks = set(re.findall(r"\b[A-Z]{2,}[A-Z0-9]*\b", t))
    toks |= set(re.findall(r"\b[A-Za-z]*[a-z][A-Z][A-Za-z]*\b", t))
    toks |= set(re.findall(r"(?<=[a-z,;:] )([A-Z][a-z]{2,})\b", t))
    toks |= set(re.findall(r"[#@]\w+", t)) | set(re.findall(r"https?://\S+", t))
    return toks


def _is_protected(block: str, keyword: str) -> bool:
    words = block.split()
    return bool((keyword and keyword in block) or "http" in block or (words and all(w.startswith(("#", "@")) for w in words)))


def _run(blocks: list[str], keyword: str) -> tuple[int, int]:
    """[a, b) = the longest stretch of blocks that may be rewritten (not the hook, not the CTA, not hashtag or link lines)."""
    best, a = (0, 0), None
    for i, b in enumerate(blocks + [None]):
        free = b is not None and i > 0 and not _is_protected(b, keyword)
        if free and a is None:
            a = i
        if not free and a is not None:
            if captions.words("\n".join(blocks[a:i])) > captions.words("\n".join(blocks[best[0]:best[1]])):
                best = (a, i)
            a = None
    return best


def problems(old: str, new: str, platform: str, focus: dict, sep: str) -> list[str]:
    """Why a rewrite must NOT replace the original. [] = safe to use."""
    out = []
    if not isinstance(new, str) or not new.strip():
        return ["empty"]
    if _nums(old) != _nums(new):
        out.append(f"numbers changed {_nums(old)} -> {_nums(new)}")
    lost = sorted(_protected_tokens(old) - _protected_tokens(new))
    if lost:
        out.append("lost: " + ", ".join(lost[:5]))
    dashes = lambda t: t.count("\u2014") + t.count("\u2013") + t.count(" -- ")
    if dashes(new) > dashes(old):
        out.append("new dashes")
    if new.count("**") != old.count("**") or "```" in new or re.search(r"(?m)^\s*([-*\u2022]|#{1,6})\s", new) and not re.search(r"(?m)^\s*([-*\u2022]|#{1,6})\s", old):
        out.append("new markdown or bullets")
    ob, nb = old.split(sep), new.split(sep)
    pre = next((i for i, (x, y) in enumerate(zip(ob, nb)) if x != y), min(len(ob), len(nb)))          # blocks the rewrite left alone, at the start and at the end
    suf = next((i for i, (x, y) in enumerate(zip(reversed(ob[pre:]), reversed(nb[pre:]))) if x != y), min(len(ob), len(nb)) - pre)
    n_old, n_new = len(ob) - pre - suf, len(nb) - pre - suf                                             # paragraphs of the rewritten body, before and after
    body = sep.join(nb[pre:len(nb) - suf]).strip()                                                       # what the rewrite actually changed
    if body and (re.match(r"(here'?s|here is|sure|certainly|rewritten|revised)\b", body, re.I) or body[0] in "\"'"):
        out.append("has a preamble or wrapping quotes")
    if n_old and not n_old - n_old // 4 <= n_new <= n_old + 1:
        out.append(f"paragraphs {n_old} -> {n_new}")
    w_old, w_new = captions.words(old), captions.words(new)
    if not 0.85 * w_old <= w_new <= 1.15 * w_old:
        out.append(f"length {w_old} -> {w_new} words")
    if platform == "linkedin" and not captions.LINKEDIN_MIN - 20 <= w_new <= captions.LIMITS["linkedin"] + 40:
        out.append("outside the LinkedIn length window")
    if bool(re.search("[\u0900-\u097F]", old)) != bool(re.search("[\u0900-\u097F]", new)):
        out.append("script switched")
    fresh = set(marketingskills.text_problems(new, focus, where=platform)) - set(marketingskills.text_problems(old, focus, where=platform))
    if fresh:
        out.append("new rule break: " + "; ".join(sorted(fresh))[:160])
    return out


def _is_limit(e: Exception) -> bool:
    s = f"{type(e).__name__} {e}".lower()
    return getattr(e, "status_code", None) in (401, 403, 429) or "rate" in s or "429" in s or "quota" in s or "unauthorized" in s


def _rewrite(body: str, deadline: float, rep: dict) -> dict | None:
    """The package's result for one body, trying up to MAX_KEYS keys. None when none worked (the reason goes into rep)."""
    own = os.getenv("HUMANIZE_API_KEY")
    keys = ([own] if own else llm.groq_keys())[:MAX_KEYS]
    for key in keys:
        if llm.out_of_time() or time.time() > deadline:
            rep["reason"] = "out of time"
            return None
        try:
            with _house_rules():
                return _engine(key).humanize(body, max_retries=1, target_score=float(os.getenv("HUMANIZE_TARGET") or 15.0))
        except Exception as e:
            rep["reason"] = f"{type(e).__name__}: {str(e)[:100]}"
            if os.getenv("HUMANIZE_DEBUG"):
                import traceback
                traceback.print_exc()
            if not _is_limit(e):
                return None
    return None


def humanize_text(text: str, platform: str, focus: dict, deadline: float) -> tuple[str, dict]:
    """-> (text to use, report). The original text unless every guard passed."""
    rep: dict = {"status": "kept"}
    keyword = (focus or {}).get("dm_keyword", "")
    sep = "\n\n" if "\n\n" in text else "\n"
    blocks = text.split(sep)
    a, b = _run(blocks, keyword)
    body = sep.join(blocks[a:b])
    if captions.words(body) < MIN_BODY_WORDS:
        return text, {"status": "skipped", "reason": f"body under {MIN_BODY_WORDS} words"}
    res = _rewrite(body, deadline, rep)
    if not res:
        rep["status"] = "error"
        return text, rep
    new_body = (res.get("text") or "").strip()
    hist = res.get("metrics_history") or [{}]
    rep["ai_before"], rep["ai_after"] = hist[0].get("ai_percentage"), res.get("final_score")
    if new_body == body.strip():
        rep["reason"] = "already reads human to the Critic"
        return text, rep
    if rep["ai_before"] is not None and rep["ai_after"] is not None and rep["ai_after"] > rep["ai_before"]:
        rep["reason"] = "the Critic scored the rewrite worse"
        return text, rep
    full = sep.join(blocks[:a] + [new_body] + blocks[b:])
    why = problems(text, full, platform, focus, sep)
    if why:
        rep["reason"] = "kept the original: " + "; ".join(why)
        return text, rep
    rep["status"] = "humanized"
    return full, rep


def humanize_posts(posts: dict, focus: dict) -> tuple[dict, dict]:
    """-> (posts, report). Never raises; posts that were not humanized are returned exactly as they came in."""
    report = {"model": os.getenv("HUMANIZE_MODEL") or DEFAULT_MODEL, "platforms": {}}
    out = dict(posts)
    if not enabled():
        return out, {}
    try:
        _load()
    except Exception as e:
        return out, {"model": report["model"], "error": f"humanizer not available ({type(e).__name__}: {str(e)[:100]})"}
    deadline = time.time() + float(os.getenv("HUMANIZE_BUDGET") or 150)
    for p in PLATFORM_ORDER:
        if not isinstance(out.get(p), str) or not out[p].strip():
            continue
        try:
            out[p], report["platforms"][p] = humanize_text(out[p], p, focus, deadline)
        except Exception as e:          # a bug here must never cost the day's draft
            report["platforms"][p] = {"status": "error", "reason": f"{type(e).__name__}: {str(e)[:100]}"}
    return out, report


def summary_line(report: dict) -> str:
    if not report:
        return ""
    if report.get("error"):
        return report["error"]
    bits = []
    for p, r in report.get("platforms", {}).items():
        if r["status"] == "humanized":
            bits.append(f"{p} humanized (Critic AI {r.get('ai_before')}% -> {r.get('ai_after')}%)")
        else:
            bits.append(f"{p} {r['status']}" + (f" ({r['reason']})" if r.get("reason") else ""))
    return "; ".join(bits)
