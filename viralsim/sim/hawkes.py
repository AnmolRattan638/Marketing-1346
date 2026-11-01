"""Self-exciting (Hawkes) point process: lambda(t) = mu + sum alpha*exp(-beta (t-ti)).
Branching ratio n = alpha/beta < 1 means the cascade dies out; expected total size ~ 1/(1-n)."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize


@dataclass
class HawkesParams:
    mu: float
    alpha: float
    beta: float

    @property
    def branching_ratio(self) -> float:
        return self.alpha / self.beta


def simulate_hawkes(p: HawkesParams, horizon: float, rng: np.random.Generator, max_events: int = 100000) -> np.ndarray:
    """Ogata thinning."""
    t, times, ex = 0.0, [], 0.0   # ex = excitation part of intensity at time t
    while t < horizon and len(times) < max_events:
        lam_bar = p.mu + ex
        w = rng.exponential(1 / lam_bar)
        ex_new = ex * math.exp(-p.beta * w)
        t += w
        if t >= horizon:
            break
        if rng.random() <= (p.mu + ex_new) / lam_bar:
            times.append(t)
            ex = ex_new + p.alpha
        else:
            ex = ex_new
    return np.array(times)


def _nll(theta, times, T):
    mu, alpha, beta = np.exp(theta)
    if alpha / beta >= 0.999:
        return 1e12
    r, ll = 0.0, 0.0
    prev = None
    for t in times:
        if prev is not None:
            r = math.exp(-beta * (t - prev)) * (1 + r)
        ll += math.log(mu + alpha * r)
        prev = t
    comp = mu * T + (alpha / beta) * float(np.sum(1 - np.exp(-beta * (T - times))))
    return -(ll - comp)


def fit_hawkes(times, horizon: float) -> HawkesParams:
    times = np.sort(np.asarray(times, dtype=float))
    if len(times) < 5:
        raise ValueError("need at least 5 events to fit a Hawkes process")
    best = None
    for b0 in (0.5, 2.0, 8.0):
        x0 = np.log([max(len(times) / horizon * 0.3, 1e-3), 0.5 * b0, b0])
        res = minimize(_nll, x0, args=(times, horizon), method="Nelder-Mead", options={"maxiter": 800, "xatol": 1e-4, "fatol": 1e-6})
        if best is None or res.fun < best.fun:
            best = res
    mu, alpha, beta = np.exp(best.x)
    return HawkesParams(float(mu), float(alpha), float(beta))


def forecast_remaining(times, horizon: float, p: HawkesParams) -> float:
    """Expected further events after `horizon` caused by already-observed events (baseline excluded)."""
    n = min(p.branching_ratio, 0.999)
    times = np.asarray(times, dtype=float)
    return float(np.sum(n * np.exp(-p.beta * (horizon - times))) / (1 - n))
