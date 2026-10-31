"""Early-signal virality predictor (SocialNetSim idea): simulate many cascades, then learn to predict
the final outcome from the first few steps + content features. Uses scikit-learn
(GradientBoosting); install xgboost and pass model='xgboost' to use it instead."""
from __future__ import annotations

import numpy as np

from .audience import AudiencePool
from .calibrate import auc
from .schema import DIMS, Content
from .sim.network import NetworkConfig, simulate_cascade

EARLY = 4


def _features(c: Content, shares: list[int], early: int) -> list[float]:
    s = (shares + [0] * early)[:early]
    c.ensure_composites()
    growth = (s[-1] + 1) / (s[1] + 1) if early > 1 else 1.0
    return [float(sum(s)), float(s[-1]), growth] + [c.dims.get(d, 0.0) for d in DIMS] + [c.shareability, c.saveability]


def build_dataset(pool: AudiencePool, contents: list[Content], n_per_content: int = 4, early: int = EARLY,
                  n_users: int = 600, seed: int = 0):
    X, final = [], []
    for ci, c in enumerate(contents):
        for k in range(n_per_content):
            r = simulate_cascade(pool, c, cfg=NetworkConfig(n_users=n_users, seed=seed + ci * 100 + k, steps=30))
            X.append(_features(c, r.shares_per_step, early))
            final.append(r.metrics["size"])
    return np.array(X), np.array(final)


def train_early_predictor(X, final, viral_quantile: float = 0.7, model: str = "sklearn", test_size: float = 0.25, seed: int = 0):
    from sklearn.model_selection import train_test_split
    thr = float(np.quantile(final, viral_quantile))
    y = (final >= thr).astype(int)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=test_size, random_state=seed, stratify=y)
    if model == "xgboost":
        from xgboost import XGBClassifier
        clf = XGBClassifier(n_estimators=200, max_depth=3, learning_rate=0.1)
    else:
        from sklearn.ensemble import GradientBoostingClassifier
        clf = GradientBoostingClassifier(random_state=seed)
    clf.fit(Xtr, ytr)
    p = clf.predict_proba(Xte)[:, 1]
    return clf, {"viral_threshold_size": thr, "test_auc": auc(p, yte), "n_train": len(ytr), "n_test": len(yte)}
