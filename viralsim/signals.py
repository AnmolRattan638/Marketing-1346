"""Platform-signal engine: plain-text features -> expected audience actions, negative-signal risks, a 0-100 score and concrete writing tips.

Original work written for this repository (no code, weights or patterns from any other project). It is a transparent rule table, not a model of any
platform's real ranking: every multiplier below is a hand-set judgement about what usually helps or hurts a short post on Instagram, LinkedIn or
Bluesky, and none of it is fitted to data. The repo's backtest (src/virality.py) is what says whether it earns trust.

Two functions are the contract used by the rest of viralsim:
    analyze_text(text, **media) -> TextFeatures
    predict_signals(features, creator=None) -> SignalPrediction   (.score .probs .risks .expected .insights)
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .schema import clamp

# ---------------------------------------------------------------- text patterns
_EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⬆✅]")
_LINK = re.compile(r"(?:https?://|www\.)\S+|\b[a-z0-9-]+\.(?:com|in|co|io|net|org|app|me|ly|ai|dev)\b(?:/\S*)?", re.I)
_HASHTAG, _MENTION = re.compile(r"#\w+"), re.compile(r"@\w+")
_LIST_LINE = re.compile(r"^\s*(?:[→\-•*▪✓✔]|\d+[.)])\s+")
_HOOK_MARK = re.compile(r"\b(?:vs|versus|myth|mistake|stop|never|why|how|secret|truth|nobody|wrong|instead|before|after|only|without)\b", re.I)
_CTA = re.compile(r"\b(?:dm|message|comment|reply|save|share|follow|book|call|whatsapp|enquire|inquire|link in bio|tap|send)\b", re.I)
_BAIT = re.compile(r"like (?:and|&) share|tag (?:a|your) friend|comment (?:yes|below if)|follow for follow|\bf4f\b|share if you agree|double tap if", re.I)
_HYPE = re.compile(r"\bguarantee[sd]?\b|100\s?%|best price|limited (?:time|offer)|act now|\bhurry\b|don'?t miss|cheapest|number one|#1\b|risk[- ]free|get rich", re.I)
_CONTRARIAN = re.compile(r"unpopular opinion|\bmyth\b|overrated|\bwrong\b|nobody tells you|hot take|\bstop\b|\bnever\b|\bworst\b", re.I)
_WHIMSY = re.compile(r"\bimagine\b|what if\b|plot twist|plot-twist|\bweird\b|\bstrange\b|\bunexpected\b", re.I)
_HOWTO = re.compile(r"\bhow to\b|\bsteps?\b|\btips?\b|\bchecklist\b|\btemplate\b|\bguide\b|\bmistakes?\b|\bways\b", re.I)


@dataclass
class TextFeatures:
    words: int = 0
    lines: int = 0
    first_line_words: int = 0
    has_question: bool = False
    has_hook: bool = False
    has_cta: bool = False
    has_number: bool = False
    emojis: int = 0
    hashtags: int = 0
    mentions: int = 0
    links: int = 0
    list_lines: int = 0
    exclamations: int = 0
    caps_ratio: float = 0.0
    bait: int = 0
    hype: int = 0
    howto: int = 0
    absurd: float = 0.0              # 0-1, whimsical framing ("imagine", "plot twist")
    controversial: float = 0.0       # 0-1, contrarian framing ("myth", "unpopular opinion")
    has_video: bool = False
    has_image: bool = False
    is_thread: bool = False
    thread_length: int = 1


def analyze_text(text: str, *, has_video: bool = False, has_image: bool = False, is_thread: bool = False, thread_length: int = 1, **_) -> TextFeatures:
    t = unicodedata.normalize("NFKC", str(text or "")).replace("**", "")        # Unicode-bold letters and markdown stars read as plain words
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    first = lines[0] if lines else ""
    words = re.findall(r"[^\W_]+(?:['’][^\W_]+)?", t)
    letters = [c for c in t if c.isalpha()]
    first_words = len(first.split())
    caps_run = bool(re.search(r"\b[A-Z]{3,}\b", first))
    return TextFeatures(
        words=len(words), lines=len(lines), first_line_words=first_words,
        has_question="?" in t,
        has_hook=bool(first) and first_words <= 14 and (first.endswith("?") or bool(re.search(r"\d", first)) or bool(_HOOK_MARK.search(first)) or caps_run),
        has_cta=bool(_CTA.search(t)), has_number=bool(re.search(r"\d", t)),
        emojis=len(_EMOJI.findall(t)), hashtags=len(_HASHTAG.findall(t)), mentions=len(_MENTION.findall(t)), links=len(_LINK.findall(t)),
        list_lines=sum(1 for ln in lines if _LIST_LINE.match(ln)), exclamations=t.count("!"),
        caps_ratio=(sum(1 for c in letters if c.isupper()) / len(letters)) if letters else 0.0,
        bait=len(_BAIT.findall(t)), hype=len(_HYPE.findall(t)), howto=len(_HOWTO.findall(t)),
        absurd=min(1.0, 0.5 * len(_WHIMSY.findall(t))), controversial=min(1.0, 0.5 * len(_CONTRARIAN.findall(t))),
        has_video=bool(has_video), has_image=bool(has_image), is_thread=bool(is_thread), thread_length=max(1, int(thread_length or 1)))


# ---------------------------------------------------------------- the rule table
# Baseline chance that a viewer takes each action on an ordinary short post; every rule below multiplies some of them.
BASE = {"favorite": 0.040, "reply": 0.008, "repost": 0.003, "quote": 0.001, "click": 0.025, "profile_click": 0.010,
        "share": 0.004, "bookmark": 0.004, "dwell": 0.12, "follow": 0.002}
BASE_RISK = {"not_interested": 0.030, "mute": 0.008, "block": 0.003, "report": 0.002}
# How much each action is worth when scoring (a reply or share says more than a like) and how much each risk costs.
VALUE = {"favorite": 1.0, "reply": 5.0, "repost": 4.0, "quote": 3.0, "click": 0.6, "profile_click": 1.5, "share": 5.0, "bookmark": 3.0, "dwell": 0.35, "follow": 6.0}
COST = {"not_interested": 1.2, "mute": 3.2, "block": 4.8, "report": 8.0}
SCORE_REF = 0.25                    # raw value at which the score reaches ~63; hand-set so a strong caption lands near 60-70, a plain sentence near 15 and spam near 0


@dataclass
class SignalPrediction:
    score: float
    probs: dict
    risks: dict
    expected: dict
    insights: list = field(default_factory=list)


def _mul(d, keys, k):
    for key in keys:
        d[key] *= k


def predict_signals(f: TextFeatures, creator=None) -> SignalPrediction:
    p, r = dict(BASE), dict(BASE_RISK)
    media = f.has_video or f.has_image
    # --- what helps
    if f.has_question:
        _mul(p, ("reply",), 2.0)
    if f.has_hook:
        _mul(p, ("favorite", "click", "dwell"), 1.3)
    if f.has_cta:
        _mul(p, ("reply", "profile_click", "follow"), 1.25)
    if f.list_lines >= 2:
        _mul(p, ("dwell", "bookmark"), 1.3)
    if f.howto:
        _mul(p, ("bookmark", "share"), 1.35)
    if f.has_number:
        _mul(p, ("click", "dwell"), 1.1)
    if media:
        _mul(p, ("dwell", "favorite", "profile_click"), 1.25)
    if f.is_thread:
        _mul(p, ("dwell", "follow"), 1.0 + min(0.4, 0.05 * f.thread_length))
    if f.controversial:
        _mul(p, ("reply", "quote"), 1.0 + 0.5 * f.controversial)
        _mul(r, ("mute", "block", "report"), 1.0 + 0.6 * f.controversial)
    if f.absurd:
        _mul(p, ("share", "repost"), 1.0 + 0.3 * f.absurd)
    if f.emojis:
        _mul(p, ("favorite",), 1.0 + min(0.15, 0.05 * f.emojis))
    # --- what hurts
    if f.words < 8:
        _mul(p, tuple(p), 0.7)
    elif f.words > 180:
        _mul(p, ("dwell", "share"), 0.8)
    elif 25 <= f.words <= 100:
        _mul(p, ("dwell",), 1.12)
    if f.links:
        _mul(p, ("reply", "favorite", "share", "repost"), 0.6)
        _mul(p, ("click",), 1.4)
    if f.hashtags > 6:
        _mul(p, ("favorite", "reply"), 0.85)
        _mul(r, ("not_interested",), 1.3)
    if f.bait:
        _mul(p, ("reply", "share"), 0.7)
        _mul(r, ("not_interested", "mute", "report"), 1.8)
    if f.hype:
        _mul(p, ("share", "bookmark", "follow"), 0.75)
        _mul(r, ("not_interested", "report"), 1.6)
    if f.exclamations >= 3:
        _mul(r, ("not_interested", "mute"), 1.4)
    if f.caps_ratio > 0.5 and f.words > 6:
        _mul(r, ("not_interested", "mute"), 1.3)
    if f.mentions > 3:
        _mul(r, ("not_interested", "report"), 1.3)
    # --- the account: a bigger, more engaged, older account earns more of each action (mild, capped)
    c = creator
    eng = clamp((getattr(c, "avg_engagement_rate", 2.0) or 0) / 2.0, 0.5, 1.6) if c else 1.0
    age = 1.0 if not c else clamp(0.85 + 0.15 * min(1.0, getattr(c, "account_age_days", 365) / 365.0), 0.85, 1.0)
    boost = eng * age * (1.1 if c and getattr(c, "verified", False) else 1.0)
    p = {k: round(clamp(v * boost, 0.0, 0.95), 4) for k, v in p.items()}
    r = {k: round(clamp(v, 0.0, 0.95), 4) for k, v in r.items()}
    raw = sum(VALUE[k] * p[k] for k in p) - sum(COST[k] * r[k] for k in r)
    score = round(clamp(100.0 * (1.0 - 2.718281828 ** (-max(raw, 0.0) / SCORE_REF)), 0.0, 100.0), 1)
    followers = float(getattr(c, "followers", 1000.0)) if c else 1000.0
    views = followers * clamp(0.10 + score / 200.0, 0.1, 0.6)                       # share of followers who see it: 10-60%, higher for stronger posts
    expected = {"views": round(views), "likes": round(views * p["favorite"]), "reposts": round(views * p["repost"]),
                "replies": round(views * p["reply"]), "bookmarks": round(views * p["bookmark"])}
    return SignalPrediction(score, p, r, expected, _insights(f, media))


# ---------------------------------------------------------------- writing tips
_IMPACT = {"high": 0, "medium": 1, "low": 2}


def _insights(f: TextFeatures, media: bool) -> list[dict]:
    out = []
    add = lambda kind, title, desc, impact: out.append({"type": kind, "title": title, "description": desc, "impact": impact})
    if not f.has_hook:
        add("neutral", "Sharpen the first line", "Make the opening line short and specific: a number, a question or a clear contrast.", "high")
    else:
        add("positive", "Strong opening line", "The first line is short and gives a reason to keep reading.", "medium")
    if f.links:
        add("negative", "Link inside the text", "Outbound links tend to cut reach and replies; point people to a DM or the bio instead.", "high")
    if f.bait:
        add("negative", "Engagement-bait wording", "Phrases like 'tag a friend' or 'share if you agree' read as spam and raise mute and report risk.", "high")
    if f.hype:
        add("negative", "Hype or guarantee words", "Words like 'guaranteed', '100%' or 'limited offer' make a post read as an ad; show the work instead.", "medium")
    if f.hashtags > 6:
        add("negative", "Too many hashtags", "Keep to the few most relevant tags; a long tag block looks like spam.", "medium")
    if f.exclamations >= 3:
        add("warning", "Too many exclamation marks", "Calm, specific wording earns more trust than shouting.", "low")
    if f.caps_ratio > 0.5 and f.words > 6:
        add("warning", "Mostly capital letters", "Keep capitals for the hook line and one or two keywords.", "low")
    if f.words < 8:
        add("warning", "Very short post", "Add one concrete detail or example so there is something to react to.", "medium")
    elif f.words > 180:
        add("warning", "Long post", "Cut it to the one idea a busy reader needs; long posts lose the scroll.", "medium")
    if not f.has_number and not f.list_lines:
        add("neutral", "Add one concrete detail", "A number, a named situation or a short list makes a post easier to believe and to save.", "medium")
    if f.list_lines >= 2:
        add("positive", "Scannable structure", "Short list lines are easy to scan and worth saving.", "low")
    if not f.has_question and not f.has_cta:
        add("neutral", "Give readers a next step", "End with a question or a clear action (reply, DM, save) so engaged readers know what to do.", "medium")
    elif f.has_question:
        add("positive", "Conversation starter", "A real question invites replies, which are the strongest signal.", "medium")
    if not media:
        add("warning", "No image or video", "Posts with a picture or video usually hold attention longer.", "low")
    if not f.howto and not f.list_lines:
        add("neutral", "Make it worth saving", "Practical, reference-style content (steps, a checklist, a rule of thumb) gets saved and shared.", "low")
    return sorted(out, key=lambda i: _IMPACT[i["impact"]])
