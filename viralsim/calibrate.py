"""Backtesting + calibration metrics. Use these to measure how trustworthy a predictor actually is
before relying on it. Scores are compared against known outcomes (the bundled campaign set mirrors
PhantomCrowd's 50-campaign backtest)."""
from __future__ import annotations

import json
import math
import os
from typing import Callable

import numpy as np

DATA = os.path.join(os.path.dirname(__file__), "data", "backtest_campaigns.json")
BUCKETS = [(0, 15), (16, 30), (31, 45), (46, 55), (56, 70), (71, 85), (86, 100)]


def load_campaigns(path: str = DATA) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _bucket(x: float) -> int:
    return next(i for i, (lo, hi) in enumerate(BUCKETS) if lo <= round(x) <= hi) if 0 <= round(x) <= 100 else (0 if x < 0 else len(BUCKETS) - 1)


def auc(scores, labels) -> float:
    s, y = np.asarray(scores, float), np.asarray(labels, int)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    gt = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    return float(gt / (len(pos) * len(neg)))


def brier(p, y) -> float:
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def ece(p, y, bins: int = 10) -> float:
    p, y = np.asarray(p, float), np.asarray(y, float)
    e = 0.0
    for b in range(bins):
        m = (p >= b / bins) & (p < (b + 1) / bins + (b == bins - 1))
        if m.any():
            e += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(e)


def score_metrics(pred, expected) -> dict:
    pred, exp = np.asarray(pred, float), np.asarray(expected, float)
    r = float(np.corrcoef(pred, exp)[0, 1]) if np.std(pred) > 0 and np.std(exp) > 0 else float("nan")
    pb, eb = [_bucket(x) for x in pred], [_bucket(x) for x in exp]
    return {"n": len(pred), "pearson": r, "mae": float(np.mean(np.abs(pred - exp))),
            "directional_accuracy": float(np.mean((pred >= 50) == (exp >= 50))),
            "exact_bucket": int(sum(a == b for a, b in zip(pb, eb))),
            "near_bucket": int(sum(abs(a - b) <= 1 for a, b in zip(pb, eb))),
            "auc_success_vs_failure": auc(pred, exp >= 50)}


def backtest(predict: Callable[[dict], float], campaigns: list[dict] | None = None) -> dict:
    camps = campaigns or load_campaigns()
    pred = [float(predict(c)) for c in camps]
    exp = [c["expected_score"] for c in camps]
    m = score_metrics(pred, exp)
    m["results"] = [{"name": c["name"], "expected": e, "predicted": round(p, 1)} for c, p, e in zip(camps, pred, exp)]
    return m


def baseline_always(value: float = 50.0) -> Callable[[dict], float]:
    """Reference predictor: any real model should beat this."""
    return lambda c: value
