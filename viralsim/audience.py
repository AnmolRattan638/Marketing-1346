"""Synthetic audience: array-backed persona pool (bundled 50k Nemotron-derived pool, JSONL loader,
or a calibrated synthetic generator)."""
from __future__ import annotations

import gzip
import json
import os
from dataclasses import dataclass

import numpy as np

from .schema import DIMS, TOPICS, DIM_IDX, TOPIC_IDX

PROPS = ("retention", "like", "comment", "share", "save", "follow")
BUNDLED = os.path.join(os.path.dirname(__file__), "data", "personas_50k.jsonl.gz")


@dataclass
class AudiencePool:
    age: np.ndarray            # (N,)
    affinity: np.ndarray       # (N, 8) signed -1..1
    interests: np.ndarray      # (N, 24) 0..1
    props: np.ndarray          # (N, 6) retention, like, comment, share, save, follow
    trend_susceptibility: np.ndarray
    activity: np.ndarray
    ideology: np.ndarray       # (N,) -1..1 (used by network/opinion sims)
    misinfo_susceptibility: np.ndarray

    def __len__(self) -> int:
        return int(self.age.shape[0])

    @classmethod
    def from_records(cls, recs: list[dict], seed: int = 0) -> "AudiencePool":
        n = len(recs)
        aff, intr, props = np.zeros((n, 8)), np.zeros((n, 24)), np.zeros((n, 6))
        age, ts, act = np.zeros(n), np.zeros(n), np.full(n, 0.5)
        for i, r in enumerate(recs):
            age[i] = (r.get("demographics") or {}).get("age", 30)
            for k, v in (r.get("affinities") or {}).items():
                if k in DIM_IDX:
                    aff[i, DIM_IDX[k]] = v
            for k, v in (r.get("interests") or {}).items():
                if k in TOPIC_IDX:
                    intr[i, TOPIC_IDX[k]] = v
            pr = r.get("propensities") or {}
            for j, k in enumerate(PROPS):
                props[i, j] = pr.get(k, 0.0)
            ts[i] = r.get("trend_susceptibility", 0.0)
            act[i] = r.get("activity", 0.5)
        rng = np.random.default_rng(seed)
        # ideology / misinformation susceptibility are not in the source schema: derive deterministically
        ideology = np.clip(rng.normal(0, 0.5, n) + 0.25 * aff[:, DIM_IDX["controversy"]], -1, 1)
        misinfo = np.clip(0.3 + 0.4 * ts + rng.normal(0, 0.1, n) - 0.2 * aff[:, DIM_IDX["educational"]], 0, 1)
        return cls(age, aff, intr, props, ts, act, ideology, misinfo)

    @classmethod
    def load_jsonl(cls, path: str, limit: int | None = None) -> "AudiencePool":
        opener = gzip.open if path.endswith(".gz") else open
        recs = []
        with opener(path, "rt", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    recs.append(json.loads(line))
                    if limit and len(recs) >= limit:
                        break
        if not recs:
            raise ValueError(f"no personas in {path}")
        return cls.from_records(recs)

    @classmethod
    def bundled(cls, limit: int | None = None) -> "AudiencePool":
        return cls.load_jsonl(BUNDLED, limit)

    @classmethod
    def synthetic(cls, n: int = 20000, seed: int = 42) -> "AudiencePool":
        """Calibrated generator mirroring the documented corrections: young skew (~72% <35), rare
        save/follow, signed affinities that include repulsion, 3-5 genuine interests each."""
        rng = np.random.default_rng(seed)
        young = rng.random(n) < 0.72
        age = np.where(young, rng.integers(13, 35, n), rng.integers(35, 75, n)).astype(float)
        youth = np.clip((50 - age) / 37, 0, 1)
        aff = np.clip(rng.normal(0.1, 0.45, (n, 8)), -1, 1)
        intr = np.zeros((n, 24))
        for i in range(n):
            k = rng.integers(3, 6)
            idx = rng.choice(24, k, replace=False)
            intr[i, idx] = np.sort(rng.uniform(0.4, 1.0, k))[::-1]
        props = np.zeros((n, 6))
        props[:, 0] = np.clip(rng.normal(0.5, 0.2, n), 0, 1)
        props[:, 1] = np.clip(rng.beta(2, 3, n) * (1.1 - 0.3 * youth), 0, 1)
        props[:, 2] = rng.beta(1, 12, n)
        props[:, 3] = rng.beta(1, 10, n)
        props[:, 4] = rng.beta(1, 6, n)
        props[:, 5] = rng.beta(1, 14, n)
        ts = np.clip(0.25 + 0.5 * youth + rng.normal(0, 0.15, n), 0, 1)
        act = np.clip(0.35 + 0.35 * youth + rng.normal(0, 0.15, n), 0, 1)
        ideology = np.clip(rng.normal(0, 0.5, n), -1, 1)
        misinfo = np.clip(rng.beta(2, 5, n), 0, 1)
        return cls(age, aff, intr, props, ts, act, ideology, misinfo)
