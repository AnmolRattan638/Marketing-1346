"""A/B testing: simulation-based (paired Monte Carlo), vote-based (proper two-proportion z-test) and
LLM-persona based (viral-predictor's idea, with heterogeneous personas instead of one repeated prompt)."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .audience import AudiencePool
from .creator import Creator
from .engagement import engage_all
from .llm import LLMClient, extract_json
from .schema import Content
from .trends import TrendSnapshot
from .sim.wave import SimConfig, simulate_once


def two_proportion_z(x1: int, n1: int, x2: int, n2: int) -> dict:
    """One-sided test that p1 > p2. confidence = 1 - p_value. Handles degenerate cells."""
    if n1 <= 0 or n2 <= 0:
        return {"z": 0.0, "p_value": 1.0, "confidence": 0.0}
    p1, p2, pp = x1 / n1, x2 / n2, (x1 + x2) / (n1 + n2)
    se = math.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2))
    if se == 0:
        return {"z": 0.0, "p_value": 0.5, "confidence": 0.5}
    z = (p1 - p2) / se
    p = 0.5 * math.erfc(z / math.sqrt(2))
    return {"z": z, "p_value": p, "confidence": 1 - p}


def compare_votes(a: dict[str, int], b: dict[str, int], n: int) -> dict:
    out = {}
    for k in a:
        win, (hi, lo) = ("A", (a[k], b[k])) if a[k] >= b.get(k, 0) else ("B", (b[k], a[k]))
        t = two_proportion_z(hi, n, lo, n)
        out[k] = {"winner": win if hi != lo else "tie", "a": a[k], "b": b[k], **t}
    return out


def ab_simulated(pool: AudiencePool, a: Content, b: Content, creator: Creator | None = None,
                 trend: TrendSnapshot | None = None, cfg: SimConfig | None = None) -> dict:
    """Paired Monte Carlo: both variants share seeds, so differences are due to the content, not luck."""
    cfg, creator, trend = cfg or SimConfig(runs=1500), creator or Creator(), trend or TrendSnapshot.neutral()
    mech, n = creator.mechanics(len(pool)), len(pool)
    reach = {}
    for name, c in (("A", a), ("B", b)):
        pe = engage_all(pool, c, trend.alignment(c))
        d = pe.distribution_score
        reach[name] = np.array([simulate_once(pe, d, mech, n, cfg, np.random.default_rng(cfg.base_seed + i))["reach"]
                                for i in range(cfg.runs)], dtype=float)
    diff = reach["B"] - reach["A"]
    boot = np.random.default_rng(0).choice(diff, (400, len(diff))).mean(axis=1)
    p_b = float((diff > 0).mean() + 0.5 * (diff == 0).mean())
    thr = cfg.viral_threshold * n
    return {"mean_reach": {k: float(v.mean()) for k, v in reach.items()},
            "viral_probability": {k: float((v > thr).mean()) for k, v in reach.items()},
            "p_b_beats_a": p_b, "winner": "B" if p_b > 0.5 else "A" if p_b < 0.5 else "tie",
            "mean_lift_b_vs_a": float(diff.mean()), "lift_ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
            "decisive": bool(np.percentile(boot, 2.5) > 0 or np.percentile(boot, 97.5) < 0)}


def ab_llm_personas(llm: LLMClient, text_a: str, text_b: str, platform: str, pool: AudiencePool,
                    n_users: int = 40, seed: int = 0) -> dict:
    """Each simulated user is a sampled persona (age + interests) deciding like/comment/share/quote."""
    from .schema import TOPICS
    rng = np.random.default_rng(seed)
    keys = ("like", "comment", "share", "quote")
    tally = {"A": dict.fromkeys(keys, 0), "B": dict.fromkeys(keys, 0)}
    done = 0
    for i in rng.integers(0, len(pool), n_users):
        top = [TOPICS[j] for j in np.argsort(-pool.interests[i])[:3] if pool.interests[i, j] > 0]
        who = f"You are a {int(pool.age[i])}-year-old who mostly follows {', '.join(top) or 'varied topics'}."
        for name, txt in (("A", text_a), ("B", text_b)):
            prompt = (f"{who} You are scrolling {platform} and see:\n'''{txt}'''\nDecide if you like, comment, share, or quote. "
                      'Reply JSON: {"like":bool,"comment":bool,"share":bool,"quote":bool}')
            try:
                r = extract_json(llm.complete("Act as the described real user.", prompt, json_mode=True, temperature=0.8))
            except Exception:
                continue
            for k in keys:
                tally[name][k] += bool(r.get(k))
        done += 1
    return {"users": done, "tally": tally, "comparison": compare_votes(tally["A"], tally["B"], max(done, 1))}
