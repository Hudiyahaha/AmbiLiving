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


def _fit(name: str, X_tr, y_tr, seed: int, balance: str):
    model = build(name, seed)
    if name == "hgb":
        # HGB has no class_weight="balanced_subsample"; weight samples instead.
        w = compute_sample_weight("balanced", y_tr)
        model.fit(X_tr, y_tr, sample_weight=w ** 0.5 if balance == "sqrt" else w)
    else:
        model.fit(X_tr, y_tr)
    return model


def fit_predict(name: str, X_tr, y_tr, X_te, seed: int, balance: str = "sqrt") -> np.ndarray:
    """``balance`` (HGB only): "sqrt" softens inverse-frequency weights, "full" uses
    them as-is. "full" raises recall on rare classes at the cost of precision."""
    return _fit(name, X_tr, y_tr, seed, balance).predict(X_te)


def fit_predict_proba(name: str, X_tr, y_tr, X_te, seed: int, n_classes: int,
                      balance: str = "sqrt") -> np.ndarray:
    """Like ``fit_predict`` but returns class probabilities, shape (len(X_te), n_classes).

    Columns follow the global class index, so a class missing from the training
    fold (possible for tiny classes in the temporal split) gets probability 0.
    ``proba.argmax(1)`` gives the same answer as ``fit_predict``.
    """
    model = _fit(name, X_tr, y_tr, seed, balance)
    proba = np.zeros((len(X_te), n_classes))
    proba[:, model.classes_] = model.predict_proba(X_te)
    return proba
