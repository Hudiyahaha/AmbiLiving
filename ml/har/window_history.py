"""Routine-history features for sliding windows, built from the system's own predictions.

In the segment setting, ``features.activity_history`` told the model which
activities happened earlier ("Eating ended 9 minutes ago"). Here the same idea
is rebuilt for a live stream, where there are no annotated activities at all:

1. A stage-1 model predicts the activity every ``step`` events along the whole
   stream (the *prediction stream*).
2. The stream is turned into *episodes*: runs of the same predicted activity.
   A run counts only once it has lasted ``min_run`` stream points, so a single
   stray prediction is not mistaken for a new activity.
3. For a window ending at event e, history is computed from stream points
   strictly before e (past only, as a live system would have it):
     * log seconds since each activity's latest episode ended (capped at 24 h)
     * one-hot of the previous activity (latest episode differing from the current one)
     * number of episodes of each activity started earlier the same day
   plus log seconds since the previous activity ended.

No annotation is used anywhere in these features. Leakage on the training side
is avoided in ``stream_predictions``: training-period stream points are
predicted by models that never saw that part of the data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .data import Home
from .features import handcrafted_features
from .models import classical
from .windows import make_windows

CAP_S = 86400.0


def _predict(model, X, n_classes):
    p = np.zeros((len(X), n_classes))
    p[:, model.classes_] = model.predict_proba(X)
    return p


def stream_predictions(home: Home, train_hi: np.ndarray, y_tr: np.ndarray, X_tr: np.ndarray,
                       train_end: int, size: int, step: int, n_classes: int, rule: str,
                       seed: int, inner_blocks: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """Stage-1 predicted class at every ``step``-th event (window end), whole stream.

    Training period: split into ``inner_blocks`` contiguous blocks of events; each
    block is predicted by a model trained only on training windows that do not
    overlap that block. After the training period: the model trained on all
    training windows.
    Returns (stream_ends, stream_labels).
    """
    n = len(home.times)
    ends = np.arange(size, n + 1, step)
    labels = np.full(len(ends), -1)

    def fit(mask):
        y = y_tr[mask]
        cnt = np.bincount(y, minlength=n_classes)
        ok = cnt[y] >= 2
        return classical._fit("hgb", X_tr[mask][ok], y[ok], seed, "sqrt")

    def feats(sel_ends):
        wh = make_windows(home, sel_ends, size, "other")  # labels unused; rule-free window cut
        return handcrafted_features(wh, preceding=False)[0], wh.segments["hi"].to_numpy()

    edges = np.linspace(size, train_end, inner_blocks + 1).astype(int)
    tr_lo = train_hi - size
    for b in range(inner_blocks):
        a, z = edges[b], edges[b + 1]
        sel = (ends > a) & (ends <= z)
        if not sel.any():
            continue
        far = (train_hi <= a) | (tr_lo >= z)  # training windows not overlapping the block
        model = fit(far)
        X, hi = feats(ends[sel])
        labels[np.isin(ends, hi)] = _predict(model, X, n_classes).argmax(1)

    model = fit(np.ones(len(y_tr), bool))
    sel = ends > train_end
    X, hi = feats(ends[sel])
    labels[np.isin(ends, hi)] = _predict(model, X, n_classes).argmax(1)
    ok = labels >= 0
    return ends[ok], labels[ok]


def history_features(home: Home, window_ends: np.ndarray, stream_ends: np.ndarray,
                     stream_labels: np.ndarray, classes: list[str],
                     min_run: int = 3, ongoing: bool = True) -> tuple[np.ndarray, list[str]]:
    """History features for windows ending at ``window_ends`` (any order).

    With ``ongoing=False`` the run still in progress at the window end is ignored:
    only *completed* earlier activities are described. This removes the shortcut
    "keep predicting what was predicted a moment ago" and keeps the routine part
    ("Eating ended 9 minutes ago").
    """
    C = len(classes)
    t = home.times.astype("datetime64[ms]").astype(np.float64) / 1000.0
    st = t[stream_ends - 1]                      # time of each stream point
    sday = home.times[stream_ends - 1].astype("datetime64[D]")

    # Runs of identical predictions.
    change = np.r_[True, stream_labels[1:] != stream_labels[:-1]]
    run_start = np.where(change)[0]
    run_end = np.r_[run_start[1:], len(stream_labels)] - 1  # inclusive
    run_lab = stream_labels[run_start]

    order = np.argsort(window_ends, kind="stable")
    out = np.zeros((len(window_ends), 3 * C + 1), np.float32)

    last_end = np.full(C, -np.inf)               # completed qualifying episodes
    today_day, today = None, np.zeros(C)
    prev_lab, prev_end = -1, -np.inf             # label/end of latest completed episode
    before_prev = -1                             # episode label before prev_lab
    r = 0                                        # next run not yet completed
    for i in order:
        e = window_ends[i]
        j = int(np.searchsorted(stream_ends, e, side="left"))  # stream points < e
        now = t[e - 1]
        day = home.times[e - 1].astype("datetime64[D]")
        if day != today_day:
            today_day, today = day, np.zeros(C)
            # episodes completed earlier today
        # Complete every run that ends before stream point j-1.
        while r < len(run_start) and run_end[r] < j - 1:
            if run_end[r] - run_start[r] + 1 >= min_run:
                lab = run_lab[r]
                last_end[lab] = st[run_end[r]]
                if sday[run_start[r]] == today_day:
                    today[lab] += 1
                if lab != prev_lab:
                    before_prev, prev_lab = prev_lab, lab
                prev_end = st[run_end[r]]
            r += 1
        # Ongoing run (contains stream point j-1), truncated at j-1.
        since = last_end.copy()
        cur = -1
        if ongoing and j > 0 and r < len(run_start) and run_start[r] <= j - 1:
            if (j - 1) - run_start[r] + 1 >= min_run:
                cur = run_lab[r]
                since[cur] = st[j - 1]
        prev = before_prev if (cur >= 0 and cur == prev_lab) else prev_lab
        out[i, :C] = np.log1p(np.minimum(np.maximum(now - since, 0), CAP_S))
        if prev >= 0:
            out[i, C + prev] = 1
        out[i, 2 * C:3 * C] = today + (np.eye(C)[cur] if cur >= 0 else 0)
        out[i, 3 * C] = np.log1p(min(max(now - prev_end, 0), CAP_S))
    names = ([f"since_{c}" for c in classes] + [f"prev_{c}" for c in classes]
             + [f"today_{c}" for c in classes] + ["since_prev_activity"])
    return out, names
