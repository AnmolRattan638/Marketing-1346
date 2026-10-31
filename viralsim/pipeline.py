"""Unified pipeline: text/media -> content vector -> {signal engine, Monte-Carlo waves, hybrid agents,
graph cascade} -> risk-adjusted Viral Score + report. Every component is optional and degrades gracefully."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .agents import run_hybrid
from .audience import AudiencePool
from .creator import Creator
from .dimensions import HeuristicScorer, LLMScorer
from .llm import LLMClient
from .optimize import analyse, text_edits
from .risk import detect_controversy
from .schema import Content
from .signals import analyze_text, predict_signals
from .sim.network import NetworkConfig, simulate_cascade
from .sim.wave import SimConfig, run_monte_carlo
from .trends import TrendSnapshot

_pool_cache: dict[str, AudiencePool] = {}


def default_pool(kind: str = "bundled") -> AudiencePool:
    if kind not in _pool_cache:
        _pool_cache[kind] = AudiencePool.bundled() if kind == "bundled" else AudiencePool.synthetic(20000)
    return _pool_cache[kind]


def viral_score(viral_probability: float, reach_p50_frac: float, signal_score: float | None, penalty: float) -> float:
    """0-100. Blend of (a) Monte-Carlo breakout probability (saturating), (b) typical reach as a share of
    the pool, (c) platform-signal score when available, minus a backlash penalty. Weights are heuristic."""
    sim = 100 * (0.6 * (1 - np.exp(-4 * viral_probability)) + 0.4 * min(1.0, reach_p50_frac * 6))
    base = sim if signal_score is None else 0.8 * sim + 0.2 * signal_score
    return float(np.clip(base - penalty, 0, 100))


def analyze(text: str, *, creator: Creator | None = None, trend: TrendSnapshot | None = None, llm: LLMClient | None = None,
            pool: AudiencePool | None = None, platform: str = "generic", has_video=False, has_image=False, is_thread=False,
            thread_length=1, runs: int = 2000, with_agents: bool = True, with_network: bool = False,
            with_levers: bool = True, market: str = "en", seed: int = 42, content: Content | None = None) -> dict[str, Any]:
    creator, trend, pool = creator or Creator(), trend or TrendSnapshot.neutral(), pool or default_pool()
    media = dict(has_video=has_video, has_image=has_image, is_thread=is_thread, thread_length=thread_length)
    scorer = LLMScorer(llm) if llm is not None else HeuristicScorer()
    c = content or scorer.score(text, **media)
    c.platform = platform
    sig = predict_signals(analyze_text(text, **media), creator)
    risk = detect_controversy(text, llm, market)
    mc = run_monte_carlo(pool, c, creator, trend, SimConfig(runs=runs, base_seed=seed))
    score = viral_score(mc["viral_probability"], mc["reach_p50"] / len(pool), sig.score, risk.score_penalty)
    out: dict[str, Any] = {
        "viral_score": round(score, 1), "score_components": {"signal_engine": sig.score, "backlash_penalty": risk.score_penalty,
                                                           "viral_probability": mc["viral_probability"]},
        "content": c.to_dict(), "scorer": "llm" if llm is not None else "heuristic",
        "forecast": mc, "signals": {"probs": sig.probs, "risks": sig.risks, "expected": sig.expected, "insights": sig.insights},
        "risk": {"level": risk.overall_risk, "issues": risk.issues, "penalty": risk.score_penalty, "source": risk.source},
        "caveats": caveats(c, llm, creator)}
    if with_agents:
        out["agents"] = run_hybrid(c, pool, creator=creator, trend=trend, llm=llm, seed=seed).summary()
    if with_network:
        r = simulate_cascade(pool, c, trend, NetworkConfig(seed=seed))
        out["network"] = {"cascade": r.metrics, "polarization_after": r.polarization_after, "echo_chamber_index": r.echo_chamber_index}
    if with_levers:
        lv = analyse(pool, c, creator, trend, runs=min(runs, 800), seed=seed)
        out["suggestions"] = {"counterfactual": lv["suggestions"], "text_edits": text_edits(text, creator, **media)}
    return out


def caveats(c: Content, llm, creator: Creator) -> list[str]:
    out = ["Forecasts are model-based estimates, not guarantees; 'confidence' is a reliability heuristic, not a calibrated probability."]
    if llm is None:
        out.append("Dimensions were scored by a lexical heuristic (no LLM). Treat scores as coarse; provide an LLM for rubric-based scoring.")
    if creator.data_confidence() < 0.5:
        out.append("Little creator history was provided, so creator-dependent numbers lean on neutral defaults.")
    if not c.topics:
        out.append("No topic detected, so audience interest matching is weak.")
    return out
