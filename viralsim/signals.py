"""Platform-signal engine (from x-virality-predictor): text features -> Phoenix-style action
probabilities -> weighted score with negative-signal risk. Weights are ESTIMATES inspired by the
open-sourced X ranking architecture; production weights are not public. Treat as a heuristic."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from .creator import Creator

W = dict(favorite=1.0, reply=27.0, repost=1.0, quote=1.0, share=1.0, click=0.5, profile_click=1.0, dwell=1.0,
         follow=4.0, not_interested=-74.0, block=-74.0, mute=-74.0, report=-369.0, bookmark_mult=50.0,
         video=2.0, image=1.5, link=0.25)

HOOKS = [r"^(here's|here is|this is|i just|just|wow|breaking|unpopular opinion|hot take|thread|🧵)",
         r"^(the truth about|nobody talks about|what they don't tell you|secret|revealed)",
         r"^(stop|don't|never|always|you need to|you have to|you should)",
         r"^\d+\s*(things|ways|reasons|tips|tricks|secrets|lessons)"]
CTA = [r"\b(follow|retweet|rt|share|like|comment|reply|subscribe|join|click|tap|check out)\b",
       r"(link in bio|dm me|let me know|what do you think|thoughts\?)"]
CONTROVERSY = [r"politic|democrat|republican|liberal|conservative", r"controvers|debate|fight|\bwar\b|\bhate\b|love it or hate"]
ABSURD = [r"fireplace|warmer|bizarre|crazy|insane|wild|unhinged", r"🔥|💀|😭|🤯|😱"]
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")


@dataclass
class TextFeatures:
    text: str
    words: int
    chars: int
    has_link: bool
    hashtags: int
    mentions: int
    emojis: int
    has_question: bool
    has_cta: bool
    has_hook: bool
    absurd: bool
    controversial: bool
    has_video: bool = False
    has_image: bool = False
    is_thread: bool = False
    thread_length: int = 1


def analyze_text(text: str, *, has_video=False, has_image=False, is_thread=False, thread_length=1) -> TextFeatures:
    urls = re.findall(r"https?://\S+", text)
    body = re.sub(r"https?://\S+", "", text)
    any_ = lambda pats, flags=re.I: any(re.search(p, text.strip(), flags) for p in pats)
    return TextFeatures(text=text, words=len(body.split()), chars=len(text), has_link=bool(urls),
                        hashtags=len(re.findall(r"#\w+", text)), mentions=len(re.findall(r"@\w+", text)),
                        emojis=len(EMOJI.findall(text)), has_question="?" in text, has_cta=any_(CTA),
                        has_hook=any_(HOOKS), absurd=any_(ABSURD), controversial=any_(CONTROVERSY),
                        has_video=has_video, has_image=has_image, is_thread=is_thread, thread_length=thread_length)


@dataclass
class SignalPrediction:
    score: float                       # 0-100
    probs: dict[str, float]
    risks: dict[str, float]
    weighted: float
    expected: dict[str, float]
    insights: list[dict] = field(default_factory=list)


def predict_signals(f: TextFeatures, creator: Creator | None = None) -> SignalPrediction:
    c = creator or Creator()
    base_mult = math.log10(max(c.followers, 100)) / 6
    eng_mult = c.avg_engagement_rate / 2
    q = 0.5 + 0.15 * f.has_hook + 0.10 * f.absurd + 0.08 * f.has_question + 0.05 * f.has_cta
    if 10 <= f.words <= 50:
        q += 0.10
    if f.has_video:
        q *= W["video"]
    elif f.has_image:
        q *= W["image"]
    if f.has_link:
        q *= W["link"]
    if f.is_thread and f.thread_length > 1:
        q *= 1 + 0.1 * f.thread_length
    if 1 <= f.hashtags <= 2:
        q += 0.05
    elif f.hashtags >= 3:            # original left exactly 3 un-penalised; >=3 reads as spammy
        q -= 0.10
    b = min(q * base_mult * eng_mult, 0.95)
    m = lambda x, cap: min(x, cap)
    p = {"favorite": m(b, .95), "reply": m(b * .15 * (2.5 if f.has_question else 1), .7), "repost": m(b * .08, .5),
         "quote": m(b * .03, .3), "click": m(b * .4, .8), "profile_click": m(b * .12, .5), "share": m(b * .05, .3),
         "bookmark": m(b * .04, .25), "dwell": m(b * .6 * (1.5 if f.has_video else 1), .9), "follow": m(b * .02, .15)}
    r = {"not_interested": .05, "block": .01, "mute": .02, "report": .005}
    if f.controversial:
        for k, v in zip(r, (.15, .05, .08, .02)):
            r[k] += v
    pos = (p["favorite"] * W["favorite"] + p["reply"] * W["reply"] + p["repost"] * W["repost"] + p["quote"] * W["quote"]
           + p["click"] * W["click"] + p["profile_click"] * W["profile_click"] + p["share"] * W["share"]
           + p["dwell"] * W["dwell"] + p["follow"] * W["follow"] + p["bookmark"] * W["bookmark_mult"] * 0.01)
    neg = sum(r[k] * abs(W[k]) for k in r)
    weighted = pos - neg
    score = max(0.0, min(100.0, weighted + 50.0))
    vf = score / 100
    views = c.followers * (0.1 + vf * 0.5) * (vf ** 3 * 10 if vf > 0.7 else 1)
    exp = {"views": views, "likes": views * p["favorite"] * .05, "reposts": views * p["repost"] * .02,
           "replies": views * p["reply"] * .01, "bookmarks": views * p["bookmark"] * .005}
    return SignalPrediction(round(score, 1), p, r, weighted, {k: round(v) for k, v in exp.items()}, insights(f, p, r))


def insights(f: TextFeatures, p: dict, r: dict) -> list[dict]:
    out = []
    add = lambda kind, title, desc, impact: out.append({"type": kind, "title": title, "description": desc, "impact": impact})
    add("positive" if f.has_hook else "neutral", "Hook" if f.has_hook else "Add a stronger hook",
        "Opening creates curiosity and lifts early dwell." if f.has_hook else "Open with a pattern interrupt, number or provocative claim.", "high")
    if f.has_link:
        add("negative", "Outbound link penalty", "Links reduce reach (modelled as x0.25). Move the link to a reply or bio.", "high")
    if f.has_question:
        add("positive", "Conversation bait", "Questions drive replies, the most heavily weighted signal.", "high")
    else:
        add("neutral", "Invite replies", "End with a question or ask for opinions; replies carry the largest weight.", "high")
    if not (f.has_video or f.has_image):
        add("warning", "Text-only", "Media-rich posts get dwell/expand signals that text-only posts miss.", "medium")
    if f.controversial:
        add("warning", "Polarising topic", "Raises block/mute/report odds; negatives hit small accounts hardest.", "high")
    if f.hashtags >= 3:
        add("negative", "Too many hashtags", "Use 1-2 relevant hashtags.", "medium")
    if p["bookmark"] < 0.02:
        add("neutral", "Make it save-worthy", "Reference-worthy content earns bookmarks.", "medium")
    return out
