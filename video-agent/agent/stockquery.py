"""Keep stock footage and photos strictly about AI and technology.

Two guards, both applied inside footage.py so every route (a scene's own query, per-shot cutaways, the fallbacks) goes through them:
  1. tech_queries(): the search text always carries an AI/tech anchor (a query without one gets an anchor appended), and the list ends with
     generic AI/tech searches, so a weak query falls back to something on-topic instead of something random.
  2. relevant(): a result whose own tags / title / description are known must mention a tech term, otherwise it is skipped
     (a stock site's "technology" search still returns cafes and girls with cameras; this is what stops them).
Tune both lists in config.json -> stock (keywords = relevance terms, anchors = what gets searched).
"""
from __future__ import annotations

import hashlib
import re

# Terms that make a result relevant (matched on whole words / word starts in tags, titles, descriptions, URL slugs).
KEYWORDS = [
    "ai", "a.i", "artificial", "intelligence", "agent", "agents", "bot", "bots", "chatbot", "robot", "robots", "robotic", "robotics", "android", "humanoid",
    "automation", "automate", "automated", "machine", "learning", "neural", "algorithm", "technology", "tech", "digital", "cyber", "futuristic", "future",
    "data", "database", "server", "servers", "cloud", "network", "code", "coding", "coder", "programming", "programmer", "developer", "software", "app", "api",
    "computer", "laptop", "screen", "monitor", "keyboard", "website", "web", "interface", "dashboard", "hologram", "holographic", "circuit", "chip", "processor",
    "startup", "analytics", "innovation", "binary", "matrix", "virtual", "vr", "drone", "smartphone", "mobile", "hacker", "workflow",
]
# What gets searched when a query has no anchor of its own, and as the fallbacks at the end of the list.
ANCHORS = [
    "ai agents", "ai automation", "technology", "ai bots doing work", "artificial intelligence", "robot working on computer", "futuristic technology interface",
    "machine learning", "neural network", "coding on screen", "data visualization technology", "digital automation workflow", "humanoid robot", "software developer coding",
]
FALLBACKS = 2


def _terms(cfg_words: list[str] | None) -> set[str]:
    return {w.lower() for w in (cfg_words or KEYWORDS)}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9\.]+", (text or "").lower())


def has_tech(text: str, keywords: list[str] | None = None) -> bool:
    terms = _terms(keywords)
    return any(t in terms or t.rstrip("s") in terms for t in _tokens(text))


def tech_queries(query: str, cfg: dict | None = None) -> list[str]:
    """The searches to run for `query`: the query made on-topic, a shorter form, then generic AI/tech searches (never random ones)."""
    scfg = (cfg or {}).get("stock") or {}
    anchors = scfg.get("anchors") or ANCHORS
    q = " ".join((query or "").split())
    pick = int(hashlib.sha256(q.encode()).hexdigest(), 16)

    def on_topic(text: str) -> str:
        if not text:
            return anchors[pick % len(anchors)]
        return text if has_tech(text, scfg.get("keywords")) else f"{text} {anchors[pick % len(anchors)]}"

    words = q.split()
    out = [on_topic(q)]
    if len(words) > 3:
        short = on_topic(" ".join(words[:3]))
        if short not in out:
            out.append(short)
    for k in range(FALLBACKS):
        a = anchors[(pick + 1 + k * 3) % len(anchors)]
        if a not in out:
            out.append(a)
    return out


def relevant(*meta: str, keywords: list[str] | None = None) -> bool:
    """True when the result's own words mention a tech term. A result that tells us nothing about itself is accepted (the query already did the work)."""
    text = " ".join(m for m in meta if m).strip()
    return True if not text else has_tech(text, keywords)
