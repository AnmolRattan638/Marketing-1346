"""Graph-based cascade simulator (from SocialNetSim): enhanced preferential-attachment network,
SIR-style diffusion with fatigue / saturation / backlash / social proof, moderation, and
bounded-confidence opinion dynamics. Complements the feed-driven wave model: use this one when the
platform is follower-graph-driven (X, Facebook, LinkedIn) or you care about structure and polarisation."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ..audience import AudiencePool
from ..engagement import engage_all
from ..metrics import bimodality, cascade_metrics, echo_chamber_index, polarization
from ..schema import Content
from ..trends import TrendSnapshot


@dataclass
class NetworkConfig:
    n_users: int = 2000
    m_edges: int = 4
    w_degree: float = 0.4
    w_interest: float = 0.3
    w_ideology: float = 0.3
    steps: int = 40
    exposure_base: float = 0.25      # chance a follower sees a share in a step (scaled by their activity)
    saturation_const: float = 100.0
    fatigue_rate: float = 0.1
    fatigue_decay: float = 0.02
    backlash_threshold: int = 5
    backlash_strength: float = 0.3
    exposure_decay: float = 0.05
    share_scale: float = 15.0        # maps persona share propensity to a per-exposure share probability
    confidence_bound: float = 0.5    # Deffuant epsilon
    convergence_rate: float = 0.1    # Deffuant mu
    seed: int = 7


def build_network(pool: AudiencePool, idx: np.ndarray, cfg: NetworkConfig, rng: np.random.Generator) -> list[list[int]]:
    """Undirected graph over the sampled personas; P(attach) = w_d*deg + w_i*interest cosine + w_id*(1-|d ideology|/2)."""
    n = len(idx)
    X = pool.interests[idx]
    X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)
    ide = pool.ideology[idx]
    adj: list[set[int]] = [set() for _ in range(n)]
    deg = np.zeros(n)
    m0 = cfg.m_edges + 1
    for i in range(m0):
        for j in range(i):
            adj[i].add(j), adj[j].add(i)
        deg[i] = m0 - 1
    for v in range(m0, n):
        sim = X[:v] @ X[v]
        idsim = 1 - np.abs(ide[:v] - ide[v]) / 2
        p = cfg.w_degree * deg[:v] / max(deg[:v].sum(), 1) + cfg.w_interest * np.clip(sim, 0, None) / max(np.clip(sim, 0, None).sum(), 1e-9) \
            + cfg.w_ideology * idsim / idsim.sum()
        p = p / p.sum()
        for u in rng.choice(v, size=min(cfg.m_edges, v), replace=False, p=p):
            adj[v].add(int(u)), adj[int(u)].add(v)
            deg[v] += 1
            deg[u] += 1
    return [sorted(a) for a in adj]


@dataclass
class ModerationConfig:
    detect_accuracy: float = 0.0     # 0 disables moderation
    false_positive: float = 0.02
    suppression: float = 0.7         # fraction of exposure removed once flagged


@dataclass
class NetworkResult:
    metrics: dict
    share_times: list[float]
    shares_per_step: list[int]
    opinions_before: np.ndarray
    opinions_after: np.ndarray
    polarization_before: float
    polarization_after: float
    bimodality_after: float
    echo_chamber_index: float
    flagged: bool = False


def simulate_cascade(pool: AudiencePool, content: Content, trend: TrendSnapshot | None = None, cfg: NetworkConfig | None = None,
                     stance: float = 0.0, is_misinfo: bool = False, moderation: ModerationConfig | None = None,
                     n_seeds: int = 5, adj: list[list[int]] | None = None, idx: np.ndarray | None = None) -> NetworkResult:
    cfg, trend = cfg or NetworkConfig(), trend or TrendSnapshot.neutral()
    rng = np.random.default_rng(cfg.seed)
    n = min(cfg.n_users, len(pool))
    idx = rng.choice(len(pool), n, replace=False) if idx is None else idx
    adj = adj or build_network(pool, idx, cfg, rng)
    pe = engage_all(pool, content, trend.alignment(content))
    share_p = np.clip(pe.share[idx] * cfg.share_scale, 0, 0.8)
    like_p = pe.watch[idx]
    activity = pool.activity[idx]
    sus = pool.misinfo_susceptibility[idx]
    opinion = pool.ideology[idx].copy()
    op0 = opinion.copy()
    fatigue, exposures = np.zeros(n), np.zeros(n, dtype=int)
    state = np.zeros(n, dtype=int)            # 0 S, 1 exposed, 2 shared, 3 immune
    sentiment = np.zeros(n)
    parent: dict[int, int | None] = {}
    step_of: dict[int, int] = {}
    degree = np.array([len(a) for a in adj])
    seeds = rng.choice(n, n_seeds, replace=False, p=degree / degree.sum())      # seeded among well-connected users
    for s in seeds:
        state[s], parent[int(s)], step_of[int(s)] = 2, None, 0
    newly = list(map(int, seeds))
    n_shared, shares_per_step, times = len(seeds), [len(seeds)], [0.0] * len(seeds)
    mod, flagged, suppress = moderation or ModerationConfig(), False, 1.0
    if mod.detect_accuracy > 0:
        flagged = rng.random() < (mod.detect_accuracy if is_misinfo else mod.false_positive)
        suppress = 1 - mod.suppression if flagged else 1.0
    for step in range(1, cfg.steps + 1):
        sat = 1 - math.exp(-n_shared / cfg.saturation_const)
        time_f = math.exp(-step * cfg.exposure_decay)
        cand: dict[int, list[int]] = {}
        for u in newly:
            for v in adj[u]:
                if state[v] in (0, 1):
                    cand.setdefault(v, []).append(u)
        newly = []
        for v, sharers in cand.items():
            p_exp = min(0.9, cfg.exposure_base * (0.5 + activity[v]) * time_f * (1 - 0.5 * sat) * (1 - 0.5 * fatigue[v]) * suppress)
            if rng.random() > 1 - (1 - p_exp) ** len(sharers):
                continue
            exposures[v] += 1
            fatigue[v] = min(1.0, fatigue[v] + cfg.fatigue_rate)
            if exposures[v] >= cfg.backlash_threshold:               # overexposure turns sentiment negative
                sentiment[v] -= cfg.backlash_strength
            # bounded-confidence update towards the content's stance
            if abs(opinion[v] - stance) < cfg.confidence_bound:
                opinion[v] += cfg.convergence_rate * (stance - opinion[v])
            if state[v] == 0:
                state[v] = 1
            p_share = share_p[v] * (1 + 0.3 * math.log1p(len(sharers))) * (1 + 0.3 * np.clip(sentiment[v], -1, 1)) * (1 - 0.5 * fatigue[v])
            if is_misinfo:
                p_share *= 0.7 + 0.6 * sus[v]
            if rng.random() < min(0.8, max(0.0, p_share)):
                state[v] = 2
                parent[v], step_of[v] = int(sharers[int(rng.integers(len(sharers)))]), step
                newly.append(v)
                times.append(step - 1 + float(rng.random()))
        for u in range(n):                                            # fatigue decay + short-lived immunity
            if fatigue[u] > 0:
                fatigue[u] = max(0.0, fatigue[u] - cfg.fatigue_decay)
        n_shared += len(newly)
        shares_per_step.append(len(newly))
        if not newly:
            break
    m = cascade_metrics(parent, step_of)
    m["reach_fraction"] = float(np.mean(exposures > 0))
    m["share_fraction"] = float(np.mean(state == 2))
    return NetworkResult(m, sorted(times), shares_per_step, op0, opinion, polarization(op0), polarization(opinion),
                         bimodality(opinion), echo_chamber_index(adj, opinion), flagged)
