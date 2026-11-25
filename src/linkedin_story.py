"""LinkedIn is a person talking, not an advertisement.

This file decides WHAT today's LinkedIn post is (a true story, something I built, a real question, who I am, or, one post in five, a soft pitch of at most 30%) and whether a
finished post is acceptable. The facts it may use live in config/about_me.json and nowhere else. The checks are plain code, so the rules hold even when the model forgets them:
no DM or price or "pay after approval" language, no banned facts, no number that is not in the facts file, a curious hook, a sensible length."""
from __future__ import annotations

import json
import re

from . import captions, config

FACTS_PATH = config.ROOT / "config" / "about_me.json"
MIN_WORDS, MAX_WORDS = 110, 250
ROTATION = ("story", "build", "question")           # intro opens the series and returns rarely; pitch comes one post in five (see choose)

OPENERS = re.compile(r"^(small|many|most|every|all)\s+(business|owner|compan|brand)|^in today|^did you know|^are you\b|^attention\b|^hey (everyone|linkedin|folks)|^as a\b|^i'?m (excited|thrilled|happy|proud)|^happy to|^thrilled", re.I)
INSTAGRAM = re.compile(r"\bDMs?\b|pays?\s+(only\s+)?after|payment\s+(happens\s+)?(only\s+)?(after|once)|only after (you |the owner |they )?approv|\bpay\s+(once|when)\b|comment\s+\w+\s+(below|and)|link in bio|₹|\brs\.?\s*\d|\bpricing\b|\bprices?\s+(start|from|begin|are|is)\b|\$\s?\d|\bdiscount|free (audit|demo|trial|consult)|guarantee|limited (time|spots)|"
                       r"book a call|\bclick\b|\bswipe\b|follow (me|for)|game[- ]?changer|\bunlock|supercharge|\b10x\b|revolution|skyrocket|\bboost", re.I)
SELL = re.compile(r"\b(hire me|work with me|my services|my packages|get a quote|need a (website|chatbot|developer)|looking for clients|get in touch)\b", re.I)
OFFER = re.compile(r"\b(i build|i can build|i can help|i offer|open to (freelance|collab|partner|project)|message me|reach out|work with me|hire me|get in touch)\b", re.I)
COUNT_CLAIM = re.compile(r"\b(\d+|two|three|four|five|six|seven|eight|nine|ten|dozens?|hundreds?|several|many)\s+(paying\s+|happy\s+|new\s+|real\s+)?(clients|customers)\b", re.I)
LINK = re.compile(r"https?://|www\.|\b[\w-]+\.(com|in|org|net|io|app|dev)\b", re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def facts(path=None) -> dict:
    return json.loads((path or FACTS_PATH).read_text(encoding="utf-8"))


def recent(n: int = 12) -> list[dict]:
    """The last drafts' LinkedIn mode and topic, oldest first."""
    out = []
    for f in sorted(config.DRAFTS.glob("*.json"))[-n:]:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("linkedin_mode"):
            out.append({"mode": d["linkedin_mode"], "topic": d.get("linkedin_topic"), "post": (d.get("posts") or {}).get("linkedin", "")})
    return out


def choose(fx: dict, history: list[dict]) -> tuple[str, str]:
    """-> (mode, topic id). The first post introduces me; a pitch comes only after four posts without one; otherwise the least recently used of story / build / question."""
    every = int((fx.get("rules") or {}).get("pitch_one_post_in", 5))
    modes = [h["mode"] for h in history]
    if not modes:
        mode = "intro"
    else:
        since_pitch = modes[::-1].index("pitch") if "pitch" in modes else len(modes)      # posts since the last pitch
        if len(modes) >= every - 1 and since_pitch >= every - 1:
            mode = "pitch"
        elif "intro" not in modes[-12:] and len(modes) >= 6:
            mode = "intro"
        else:
            last_used = {m: (len(modes) - 1 - modes[::-1].index(m)) if m in modes else -1 for m in ROTATION}
            mode = min(ROTATION, key=lambda m: last_used[m])
    pool_modes = ("story", "build") if mode == "pitch" else (mode,)
    topics = [t for t in fx["topics"] if t["mode"] in pool_modes]
    used = [h["topic"] for h in history if h.get("topic")]
    age = lambda t: used[::-1].index(t["id"]) if t["id"] in used else 10**6           # posts since this topic was last used; never used = oldest
    topic = max(topics, key=lambda t: (age(t), -topics.index(t)))                    # the least recently used; ties go to the first in the file
    return mode, topic["id"]


def topic_facts(fx: dict, topic_id: str) -> dict:
    t = next(x for x in fx["topics"] if x["id"] == topic_id)
    if t.get("built"):
        b = fx["built"][t["built"]]
        return {"id": t["id"], "about": b["what"], "how_it_works": b["how"], "honest_limit": b["limit"]}
    return {"id": t["id"], "facts": t["facts"]}


def _never(text: str, phrases) -> list[str]:
    out = []
    for ph in phrases:
        rx = (r"(?<![A-Za-z])" if ph[:1].isalnum() else "") + re.escape(ph) + (r"(?![A-Za-z])" if ph[-1:].isalnum() else "")
        if re.search(rx, text, re.I):
            out.append(ph)
    return out


def problems(text: str, mode: str, fx: dict, pitch=()) -> list[str]:
    """Why this post is not acceptable, as concrete reasons tagged linkedin[...] (empty list = fine). The tags become the keys of the lessons the writer reads next time."""
    text = (text or "").strip()
    out: list[str] = []
    n = captions.words(text)
    if not text:
        return ["linkedin[length]: the post is empty"]
    if not MIN_WORDS <= n <= MAX_WORDS or len(text) > captions.LINKEDIN_CHARS:
        out.append(f"linkedin[length]: the post has {n} words and {len(text)} characters; it must have {MIN_WORDS} to {MAX_WORDS} words and stay under {captions.LINKEDIN_CHARS} characters")
    paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paras) < 3 or any(captions.words(p) > 70 for p in paras):
        out.append("linkedin[shape]: write at least 3 short paragraphs separated by a blank line, none longer than 70 words")
    first = text.splitlines()[0].strip()
    if len(first) > 140 or captions.words(first) > 22:
        out.append(f"linkedin[hook]: the first line is {captions.words(first)} words; make it one curious sentence of 18 words or fewer (LinkedIn shows only the first lines): \"{first[:70]}...\"")
    if OPENERS.search(first) or "!" in first or first.isupper() or EMOJI.search(first):
        out.append(f"linkedin[hook]: the first line \"{first[:70]}\" is a generic or loud opener; start with a specific true detail, an admission or a real question")
    if not re.search(r"\b(I|I'm|I've|I'd|my|me)\b", text):
        out.append("linkedin[shape]: write in the first person (I, my): this is a person talking")
    for m in LINK.finditer(text):
        out.append(f"linkedin[links]: remove \"{m[0]}\"; LinkedIn posts carry no links or web addresses")
        break
    if "#" in text or "!" in text or len(EMOJI.findall(text)) > 1 or "%" in text:
        out.append("linkedin[shape]: no hashtags, no exclamation marks, no percentage figures and at most one emoji")
    for m in INSTAGRAM.finditer(text):
        out.append(f"linkedin[pitchy]: the post says \"{m[0]}\", a sales or Instagram phrase; LinkedIn posts here are personal. Remove it and say it in plain words")
        break
    if mode != "pitch":
        for m in SELL.finditer(text):
            out.append(f"linkedin[pitchy]: \"{m[0]}\" sells; today is not a pitch day. Remove every offer and invitation to hire")
            break
    for ph in _never(text, (fx.get("never_say") or {}).get("phrases", [])):
        out.append(f"linkedin[never]: the post says \"{ph}\", which the facts file bans")
    allowed = {x.replace(",", "") for x in NUMBER.findall(json.dumps(fx, ensure_ascii=False))}
    bad_nums = sorted({x.replace(",", "") for x in NUMBER.findall(text)} - allowed)
    if bad_nums:
        out.append(f"linkedin[numbers]: the number(s) {bad_nums} are not in the facts file; use only numbers that are written there, or write no number")
    m = COUNT_CLAIM.search(text)
    if m:
        out.append(f"linkedin[numbers]: \"{m[0]}\" claims a count of clients or customers that is not in the facts file; remove it")
    if mode == "question" and not text.rstrip().endswith("?"):
        out.append("linkedin[shape]: a question post must end with its question (the last line ends with a question mark)")
    if mode == "intro" and "Anmol" not in text:
        out.append("linkedin[shape]: an introduction post must say the name Anmol")
    sentences = [s.strip() for s in re.split(r"(?<=[.?!])\s+|\n+", text) if s.strip()]
    declared = [p.strip() for p in pitch if isinstance(p, str) and p.strip()]
    if mode == "pitch":
        if not declared or len(declared) > 3 or any(d not in text for d in declared):
            out.append("linkedin[pitch-share]: list the 1 to 3 offer sentences exactly as written in pitch_sentences (each must appear word for word in the post)")
        else:
            share = captions.words(" ".join(declared)) / max(1, n)
            if share > float((fx.get("rules") or {}).get("pitch_max_share", 0.3)):
                out.append(f"linkedin[pitch-share]: the offer is {share:.0%} of the post; it must be 30% or less. Shorten the offer or lengthen the story")
            hidden = [s for s in sentences if OFFER.search(s) and not any(s in d or d in s for d in declared)]
            if hidden:
                out.append(f"linkedin[pitch-share]: \"{hidden[0][:80]}\" is an offer that is not listed in pitch_sentences")
    elif declared:
        out.append("linkedin[pitch-share]: today is not a pitch day, so pitch_sentences must be empty and the post must contain no offer")
    return out
