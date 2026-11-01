"""Creator model: five intelligence scores (ported from Content-diffusion's User Engine) and the
simulation mechanics derived from them (seed size, algorithmic favourability, consistency)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .schema import clamp


def _div(a: float, b: float) -> float:
    return a / b if b else 0.0


def _c100(x: float) -> float:
    return clamp(x, 0.0, 100.0)


def posting_frequency(timestamps: list[str]) -> float:
    """Posts per month from ISO timestamps."""
    dates = []
    for ts in timestamps:
        try:
            dates.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))
        except (ValueError, AttributeError):
            continue
    if len(dates) < 2:
        return 0.0
    dates.sort()
    span = (dates[-1] - dates[0]).days or 1
    return len(dates) / span * 30


def consistency(values: list[float]) -> float:
    """1 - coefficient of variation, clamped to 0-1."""
    if len(values) < 2:
        return 1.0
    mean = sum(values) / len(values)
    if mean == 0:
        return 0.0
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return clamp(1 - math.sqrt(var) / mean)


def compute_scores(youtube: dict | None = None, instagram: dict | None = None) -> dict[str, Any]:
    """Trust / momentum / niche authority / audience quality / volatility (0-100) from platform metrics."""
    yt = ig = {}
    if youtube:
        rv = youtube.get("recent_videos", [])
        rates = [(v.get("likes", 0) + v.get("comments", 0)) / v["views"] for v in rv if v.get("views", 0) > 0]
        yt = {"subscribers": youtube.get("subscribers", 0),
              "avg_views": _div(youtube.get("total_views", 0), youtube.get("video_count", 1) or 1),
              "eng": sum(rates) / len(rates) if rates else 0.0,
              "freq": posting_frequency([v.get("published_at", "") for v in rv]),
              "cons": consistency([v.get("views", 0) for v in rv])}
    if instagram:
        followers = instagram.get("followers", 0)
        rp = instagram.get("recent_posts", [])
        rates = [(p.get("like_count", 0) + p.get("comments_count", 0)) / followers for p in rp] if followers else []
        ig = {"followers": followers, "reach": instagram.get("monthly_reach", 0),
              "eng": sum(rates) / len(rates) if rates else 0.0,
              "freq": posting_frequency([p.get("timestamp", "") for p in rp]),
              "ratio": _div(followers, instagram.get("following", 1) or 1)}
    k = 2 if (yt and ig) else 1
    trust = (min(50, max(0, yt["subscribers"] / 1e6 * 50)) + min(50, max(0, yt["eng"] * 1000)) if yt else 0.0) + \
            (min(50, max(0, ig["followers"] / 5e5 * 50)) + min(50, max(0, ig["eng"] * 500)) if ig else 0.0)
    trust = _c100(trust / k)
    mom = 0.0
    if yt:
        mom += min(50, yt["freq"] * 5) + yt["cons"] * 50
    if ig:
        mom += min(50, ig["freq"] * 3)
    mom = _c100(mom / k)
    niche = 0.0
    if yt and yt["subscribers"] > 0:
        niche += _c100(_div(yt["avg_views"], yt["subscribers"]) * 100)
    if ig and ig["followers"] > 0:
        niche += _c100(_div(ig["reach"], ig["followers"]) * 50)
    niche = _c100(niche / k)
    q = 0.0
    if yt:
        q += _c100(yt["eng"] * 2000)
    if ig:
        q += min(50, ig["ratio"] * 10) + min(50, ig["eng"] * 1000)
    q = _c100(q / k)
    vol = _c100((1 - yt["cons"]) * 100) if yt else 0.0
    return {"creator_trust_score": round(trust, 1), "creator_momentum_score": round(mom, 1),
            "niche_authority_score": round(niche, 1), "audience_quality_score": round(q, 1),
            "creator_volatility_score": round(vol, 1)}


@dataclass
class Creator:
    followers: float = 1000.0
    following: float = 500.0
    monthly_reach: float = 3000.0
    posting_freq: float = 8.0            # posts / month
    trust: float = 40.0
    momentum: float = 50.0
    niche_authority: float = 40.0
    audience_quality: float = 50.0
    volatility: float = 50.0
    avg_engagement_rate: float = 2.0     # percent; used by the signal engine
    account_age_days: int = 365
    verified: bool = False
    niche: str = "general"

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Creator":
        m = {"creator_trust_score": "trust", "creator_momentum_score": "momentum",
             "niche_authority_score": "niche_authority", "audience_quality_score": "audience_quality",
             "creator_volatility_score": "volatility"}
        kw = {}
        for k, v in d.items():
            k = m.get(k, k)
            if k in cls.__dataclass_fields__:
                kw[k] = v
        return cls(**kw)

    def data_confidence(self) -> float:
        return min(1.0, (math.log1p(self.followers) / 14.0 + math.log1p(self.monthly_reach) / 17.0) / 2.0)

    def mechanics(self, pool: int) -> dict[str, float]:
        """Seed size (soft-capped at 10% of pool), algorithmic favourability, consistency."""
        dc = self.data_confidence()
        rpp = self.monthly_reach / max(1.0, self.posting_freq)
        aq = 0.25 + 0.75 * self.audience_quality / 100.0
        raw = 300 + 40.0 * math.sqrt(max(0.0, rpp)) + 5.0 * math.sqrt(max(0.0, self.followers)) * aq \
            + 200.0 * self.momentum / 100.0
        cap = 0.10 * pool
        seed = cap * math.tanh(raw / cap) if cap > 0 else raw
        fav = 0.6 + 0.6 * self.trust / 100 + 0.3 * self.niche_authority / 100 + 0.3 * self.audience_quality / 100 \
            + 0.30 * dc * (self.momentum - 50.0) / 100.0
        cons = dc * (1.0 - self.volatility / 100.0) + (1.0 - dc) * 0.3
        return {"seed_size": seed, "algo_favorability": fav, "consistency": cons}
