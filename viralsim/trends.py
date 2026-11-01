"""Trend snapshot + trend alignment (topic 0.60 / entity 0.25 / tag 0.15, Jaccard >= 0.5)."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .schema import TOPICS, TOPIC_IDX, Content, clamp

W_TOPIC, W_ENTITY, W_TAG = 0.60, 0.25, 0.15


def tokenize(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


def jaccard(a: list[str], b: list[str]) -> float:
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    # the original counts duplicates in the intersection; sets are the textbook definition
    return len(sa & sb) / len(sa | sb)


def _contains(seq: list[str], sub: list[str]) -> bool:
    n, m = len(seq), len(sub)
    return m > 0 and any(seq[i:i + m] == sub for i in range(n - m + 1))


def best_match_weight(s: str, candidates: list[tuple[str, float]]) -> float:
    st = tokenize(s)
    best = 0.0
    for label, weight in candidates:
        lt = tokenize(label)
        if jaccard(st, lt) >= 0.5 or _contains(st, lt) or _contains(lt, st):
            best = max(best, weight)
    return best


@dataclass
class TrendSnapshot:
    topic_trends: dict[str, float] = field(default_factory=dict)
    trending_entities: list[dict[str, Any]] = field(default_factory=list)
    tag_trends: dict[str, float] = field(default_factory=dict)

    @classmethod
    def neutral(cls) -> "TrendSnapshot":
        return cls()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TrendSnapshot":
        return cls(topic_trends={k: float(v) for k, v in (d.get("topic_trends") or {}).items() if k in TOPIC_IDX},
                   trending_entities=[e for e in d.get("trending_entities") or [] if isinstance(e, dict) and e.get("label")],
                   tag_trends={k: float(v) for k, v in (d.get("tag_trends") or {}).items()})

    @classmethod
    def load(cls, path: str) -> "TrendSnapshot":
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def alignment(self, c: Content) -> float:
        """0-1: how well the content matches what is trending right now."""
        num = sum(c.topics.get(t, 0.0) * self.topic_trends.get(t, 0.0) for t in TOPICS)
        den = sum(c.topics.get(t, 0.0) for t in TOPICS)
        topic = num / den if den > 0 else 0.0
        ents = [(e["label"], float(e.get("weight", 0.0))) for e in self.trending_entities]
        tags = list(self.tag_trends.items())
        entity = min(1.0, sum(best_match_weight(e, ents) for e in c.entities))
        tag = min(1.0, sum(max(best_match_weight(t, tags), best_match_weight(t, ents)) for t in c.tags))
        return clamp(W_TOPIC * topic + W_ENTITY * entity + W_TAG * tag)
