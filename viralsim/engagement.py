"""Per-persona engagement model, vectorised over the whole pool.

P(action) = propensity x f(appeal).  pull = quality x gate, where the gate mixes interest match,
signed affinity match (repulsion allowed) and trend alignment x susceptibility."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .audience import AudiencePool
from .schema import DIMS, TOPICS, Content

G_BASE, G_INT, G_POS, G_NEG, G_TREND = 0.25, 0.45, 0.40, 0.50, 0.25
W_WATCH, W_LIKE, W_COMMENT, W_SHARE, W_SAVE = 0.35, 0.15, 0.15, 0.25, 0.10
D_EDU, D_CONTRO, D_EMO, D_PRAC = 2, 4, 5, 7


@dataclass
class PoolEngagement:
    fit: np.ndarray
    watch: np.ndarray
    like: np.ndarray
    comment: np.ndarray
    share: np.ndarray
    save: np.ndarray
    follow: np.ndarray
    match: np.ndarray | None = None      # signed affinity match (-1..1)
    interest: np.ndarray | None = None

    @property
    def distribution_score(self) -> np.ndarray:
        return (W_WATCH * self.watch + W_LIKE * self.like + W_COMMENT * self.comment
                + W_SHARE * self.share + W_SAVE * self.save)


def engage_all(pool: AudiencePool, content: Content, trend_alignment: float = 0.0) -> PoolEngagement:
    content.ensure_composites()
    dims = np.array([float(content.dims.get(d, 0.0)) for d in DIMS])
    topics = np.array([float(content.topics.get(t, 0.0)) for t in TOPICS])
    quality = dims.sum() / (len(DIMS) * 10.0)
    dsum = dims.sum()
    match = (pool.affinity @ dims) / dsum if dsum > 0 else np.zeros(len(pool))
    tsum = topics.sum()
    interest = (pool.interests @ topics) / tsum if tsum > 0 else np.zeros(len(pool))
    trend = trend_alignment * pool.trend_susceptibility
    gate = G_BASE + G_INT * interest + G_POS * np.maximum(0, match) + G_NEG * np.minimum(0, match) + G_TREND * trend
    pull = np.clip(quality * np.maximum(0, gate), 0, 1)
    ret, like, com, sh, sv, fo = (pool.props[:, i] for i in range(6))
    watch = pull * (0.35 + 0.65 * ret) * (0.75 + 0.25 * pool.activity)
    provoke = (dims[D_CONTRO] + dims[D_EMO]) / 20.0
    useful = (dims[D_EDU] + dims[D_PRAC]) / 20.0
    fit = 0.6 * interest + 0.4 * match
    return PoolEngagement(
        fit=fit, watch=watch,
        like=watch * like * (0.55 + 0.45 * pull),
        comment=watch * com * (0.30 + 0.70 * provoke),
        share=np.minimum(1.0, watch * sh * (0.15 + 0.85 * content.shareability / 10.0) * (1 + 0.5 * trend)),
        save=watch * sv * (0.15 + 0.85 * content.saveability / 10.0) * (0.5 + 0.5 * useful),
        follow=watch * fo * pull, match=match, interest=interest)
