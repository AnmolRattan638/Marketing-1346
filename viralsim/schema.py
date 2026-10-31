"""Shared data model: content vector, constants and helpers."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

DIMS = ("humor", "curiosity", "educational", "novelty", "controversy",
        "emotional_intensity", "relatability", "practical_value")
TOPICS = ("comedy", "gaming", "tech", "fitness", "food_cooking", "beauty_fashion",
          "travel", "music", "sports", "education_howto", "news_politics",
          "finance_business", "art_design", "science", "lifestyle_vlog",
          "parenting_family", "pets_animals", "automotive", "diy_crafts",
          "motivation_selfhelp", "relationships", "nature_outdoors", "film_tv",
          "health_wellness")
DIM_IDX = {d: i for i, d in enumerate(DIMS)}
TOPIC_IDX = {t: i for i, t in enumerate(TOPICS)}

SHARE_WEIGHTS = {"emotional_intensity": 0.30, "humor": 0.20, "novelty": 0.20,
                 "relatability": 0.15, "controversy": 0.15}
SAVE_WEIGHTS = {"practical_value": 0.45, "educational": 0.35, "novelty": 0.20}
for _name, _w in (("SHARE", SHARE_WEIGHTS), ("SAVE", SAVE_WEIGHTS)):
    assert abs(sum(_w.values()) - 1.0) < 1e-9, f"{_name}_WEIGHTS must sum to 1"


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


@dataclass
class Content:
    """A piece of content described by 8 engagement dimensions (0-10), topics,
    entities and tags. ``text`` and the media flags feed the signal engine."""
    text: str = ""
    dims: dict[str, float] = field(default_factory=dict)
    shareability: float | None = None
    saveability: float | None = None
    topics: dict[str, float] = field(default_factory=dict)
    entities: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    platform: str = "generic"
    has_video: bool = False
    has_image: bool = False
    is_thread: bool = False
    thread_length: int = 1

    def ensure_composites(self) -> "Content":
        d = {k: float(self.dims.get(k, 0.0)) for k in DIMS}
        if self.shareability is None:
            self.shareability = round(sum(d[k] * w for k, w in SHARE_WEIGHTS.items()), 1)
        if self.saveability is None:
            self.saveability = round(sum(d[k] * w for k, w in SAVE_WEIGHTS.items()), 1)
        return self

    def copy(self) -> "Content":
        return copy.deepcopy(self)

    def to_dict(self) -> dict[str, Any]:
        self.ensure_composites()
        return {"text": self.text, "dims": dict(self.dims),
                "composites": {"shareability": self.shareability, "saveability": self.saveability},
                "topics": dict(self.topics), "entities": list(self.entities), "tags": list(self.tags),
                "platform": self.platform, "has_video": self.has_video, "has_image": self.has_image,
                "is_thread": self.is_thread, "thread_length": self.thread_length}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Content":
        comp = d.get("composites") or {}
        ents = []
        for e in d.get("entities") or []:
            if isinstance(e, str):
                ents.append(e)
            elif isinstance(e, dict):
                lab = e.get("label") or e.get("name") or e.get("entity")
                if isinstance(lab, str):
                    ents.append(lab)
        return cls(text=d.get("text", ""),
                   dims={k: float(v) for k, v in (d.get("dims") or {}).items() if k in DIM_IDX},
                   shareability=comp.get("shareability", d.get("shareability")),
                   saveability=comp.get("saveability", d.get("saveability")),
                   topics={k: float(v) for k, v in (d.get("topics") or {}).items() if k in TOPIC_IDX},
                   entities=ents, tags=[t for t in d.get("tags") or [] if isinstance(t, str)],
                   platform=d.get("platform", "generic"), has_video=bool(d.get("has_video")),
                   has_image=bool(d.get("has_image")), is_thread=bool(d.get("is_thread")),
                   thread_length=int(d.get("thread_length", 1)))
