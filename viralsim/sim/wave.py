"""Monte-Carlo wave propagation: replays one post thousands of times across the audience pool.

Port of Content-diffusion's C++ simulator (same equations; numpy RNG so numbers are statistically,
not bit-for-bit, identical). Because persona reactions are deterministic given the content, they are
precomputed once and each run only samples viewers, which makes 5,000 runs take a second or two."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ..audience import AudiencePool
from ..creator import Creator
from ..engagement import PoolEngagement, engage_all
from ..schema import Content
from ..trends import TrendSnapshot

SAMPLE_N, R_GAIN, FLOOR, BETA0, BETA_DECAY = 600, 4.5, 0.86, 5.0, 0.5
OBS_LIKE, OBS_COMMENT, OBS_SHARE, OBS_SAVE, OBS_FOLLOW = 1.0, 0.15, 0.5, 1.0, 0.12
C_FLOOR, C_DATA, C_TIGHT = 0.20, 0.45, 0.35


@dataclass
class SimConfig:
    runs: int = 5000
    max_waves: int = 14
    min_wave: int = 20
    viral_threshold: float = 0.3
    base_seed: int = 42


def _lognormal_mult(rng: np.random.Generator, sigma: float) -> float:
    return math.exp(rng.normal(-0.5 * sigma * sigma, sigma))   # mean exactly 1


def simulate_once(pe: PoolEngagement, dist: np.ndarray, mech: dict, pool_n: int, cfg: SimConfig,
                  rng: np.random.Generator) -> dict:
    sigma = 0.15 + 0.6 * (1.0 - mech["consistency"])
    luck = _lognormal_mult(rng, 0.30 + 0.25 * (1.0 - mech["consistency"]))
    wave = mech["seed_size"] * _lognormal_mult(rng, sigma)
    cum, beta = 0, BETA0
    waves, acts = [], np.zeros(5)
    for w in range(cfg.max_waves):
        shown = min(int(round(wave)), pool_n - cum)
        if shown < cfg.min_wave:
            break
        idx = rng.integers(0, pool_n, min(SAMPLE_N, shown))
        wt = np.exp(beta * pe.fit[idx])
        den = wt.sum()
        rate = float((wt * dist[idx]).sum() / den) if den > 0 else 0.0
        if den > 0:
            for k, (arr, obs) in enumerate(((pe.like, OBS_LIKE), (pe.comment, OBS_COMMENT), (pe.share, OBS_SHARE),
                                            (pe.save, OBS_SAVE), (pe.follow, OBS_FOLLOW))):
                acts[k] += shown * obs * float((wt * arr[idx]).sum() / den)
        waves.append(shown)
        cum += shown
        if cum >= pool_n:
            break
        R = R_GAIN * rate * mech["algo_favorability"] * luck * _lognormal_mult(rng, sigma)
        wave = shown * R * FLOOR ** w
        beta *= BETA_DECAY
    return {"reach": cum, "waves": waves, "acts": acts, "viral": cum > cfg.viral_threshold * pool_n}


def run_monte_carlo(pool: AudiencePool, content: Content, creator: Creator | None = None,
                    trend: TrendSnapshot | None = None, cfg: SimConfig | None = None) -> dict:
    cfg, creator, trend = cfg or SimConfig(), creator or Creator(), trend or TrendSnapshot.neutral()
    n = len(pool)
    alignment = trend.alignment(content)
    pe = engage_all(pool, content, alignment)
    dist = pe.distribution_score
    mech = creator.mechanics(n)
    results = [simulate_once(pe, dist, mech, n, cfg, np.random.default_rng(cfg.base_seed + i)) for i in range(cfg.runs)]
    reach = np.sort(np.array([r["reach"] for r in results], dtype=float))
    pct = lambda a, q: float(a[int(round(q * (len(a) - 1)))])
    W = max((len(r["waves"]) for r in results), default=0)
    mat = np.zeros((cfg.runs, W))
    for i, r in enumerate(results):
        mat[i, :len(r["waves"])] = r["waves"]
    mat.sort(axis=0)
    spread = (pct(reach, .9) - pct(reach, .1)) / max(1.0, pct(reach, .5))
    conf = min(1.0, max(0.0, C_FLOOR + C_DATA * creator.data_confidence() + C_TIGHT / (1 + 0.5 * spread)))
    acts = np.mean([r["acts"] for r in results], axis=0)
    return {"runs": cfg.runs, "audience_pool": n, "trend_alignment": alignment,
            "expected_reach": float(reach.mean()), "reach_p10": pct(reach, .1), "reach_p50": pct(reach, .5),
            "reach_p90": pct(reach, .9), "viral_probability": float(np.mean([r["viral"] for r in results])),
            "confidence": conf,
            "mean_wave": [float(x) for x in (mat.mean(axis=0) if W else [])],
            "wave_p10": [pct(mat[:, w], .1) for w in range(W)], "wave_p50": [pct(mat[:, w], .5) for w in range(W)],
            "wave_p90": [pct(mat[:, w], .9) for w in range(W)],
            "engagement": dict(zip(("likes", "comments", "shares", "saves", "follows"), map(float, acts)))}
