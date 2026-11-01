"""Cascade and opinion metrics: depth, breadth, structural virality (true Wiener-index definition),
effective reproduction number, polarisation, bimodality, echo-chamber index."""
from __future__ import annotations

from collections import defaultdict

import numpy as np


def cascade_metrics(parent: dict[int, int | None], step_of: dict[int, int]) -> dict:
    """parent: node -> who exposed/shared it first (root -> None). step_of: node -> time step shared."""
    nodes = list(parent)
    n = len(nodes)
    if n == 0:
        return {"size": 0, "max_depth": 0, "structural_virality": 0.0, "breadth_by_step": {}, "r_effective": 0.0}
    children = defaultdict(list)
    roots = []
    for v, p in parent.items():
        (children[p].append(v) if p is not None else roots.append(v))
    depth, order = {}, []
    stack = [(r, 0) for r in roots]
    while stack:
        v, d = stack.pop()
        depth[v] = d
        order.append(v)
        stack.extend((c, d + 1) for c in children.get(v, []))
    size = {v: 1 for v in order}
    for v in reversed(order):
        p = parent[v]
        if p is not None:
            size[p] += size[v]
    # structural virality = mean pairwise distance in the cascade forest; a virtual super-root joins multiple seeds
    total_nodes = n + (1 if len(roots) > 1 else 0)
    wiener = sum(size[v] * (total_nodes - size[v]) for v in order if parent[v] is not None)
    if len(roots) > 1:
        wiener += sum(size[r] * (total_nodes - size[r]) for r in roots)
    sv = wiener / (total_nodes * (total_nodes - 1) / 2) if total_nodes > 1 else 0.0
    breadth = defaultdict(int)
    for v in nodes:
        breadth[step_of.get(v, 0)] += 1
    steps = sorted(breadth)
    r_eff = (np.mean([breadth[steps[i + 1]] / breadth[steps[i]] for i in range(len(steps) - 1)]) if len(steps) > 1 else 0.0)
    return {"size": n, "max_depth": max(depth.values()), "structural_virality": round(sv, 4),
            "max_out_degree": max((len(c) for c in children.values()), default=0),
            "breadth_by_step": dict(sorted(breadth.items())), "r_effective": round(float(r_eff), 4)}


def polarization(opinions: np.ndarray) -> float:
    """Std-dev of opinions in [-1, 1], scaled to 0-1 (1 = perfectly split between extremes)."""
    return float(np.clip(np.std(opinions), 0, 1))


def bimodality(opinions: np.ndarray) -> float:
    """Sarle's bimodality coefficient; > 0.555 suggests a bimodal (polarised) distribution."""
    x = np.asarray(opinions, dtype=float)
    n = len(x)
    if n < 4 or np.std(x) == 0:
        return 0.0
    m = x.mean()
    s2 = ((x - m) ** 2).mean()
    skew = ((x - m) ** 3).mean() / s2 ** 1.5
    kurt = ((x - m) ** 4).mean() / s2 ** 2 - 3
    return float((skew ** 2 + 1) / (kurt + 3 * (n - 1) ** 2 / ((n - 2) * (n - 3))))


def echo_chamber_index(adj: list[list[int]], opinions: np.ndarray) -> float:
    """Mean |opinion gap| across random pairs minus mean gap across edges, scaled to 0-1.
    Positive = neighbours think alike more than strangers do."""
    gaps = [abs(opinions[u] - opinions[v]) for u, nb in enumerate(adj) for v in nb if u < v]
    if not gaps:
        return 0.0
    rng = np.random.default_rng(0)
    i, j = rng.integers(0, len(opinions), 4000), rng.integers(0, len(opinions), 4000)
    base = float(np.mean(np.abs(opinions[i] - opinions[j])))
    return float(np.clip((base - np.mean(gaps)) / max(base, 1e-9), 0, 1))
