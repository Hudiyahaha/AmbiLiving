"""Approach 1: hand-crafted segment features + classical classifiers."""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.utils.class_weight import compute_sample_weight


def build(name: str, seed: int):
    if name == "rf":
        return RandomForestClassifier(
            n_estimators=500,
            min_samples_leaf=1,
            max_features="sqrt",
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=seed,
        )
    if name == "hgb":
        return HistGradientBoostingClassifier(
            learning_rate=0.08,
            max_iter=400,
            max_leaf_nodes=31,
            l2_regularization=1.0,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=20,
            random_state=seed,
        )
    raise ValueError(f"unknown classical model {name!r}")


def fit_predict(name: str, X_tr, y_tr, X_te, seed: int) -> np.ndarray:
    model = build(name, seed)
    if name == "hgb":
        # HGB has no class_weight="balanced_subsample"; weight samples instead.
        w = compute_sample_weight("balanced", y_tr) ** 0.5
        model.fit(X_tr, y_tr, sample_weight=w)
    else:
        model.fit(X_tr, y_tr)
    return model.predict(X_te)
