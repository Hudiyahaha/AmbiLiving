"""Sliding-window samples over the raw event stream (no activity boundaries needed).

The segment pipeline in ``data.py`` cuts the log at the annotated begin/end of
each activity. A deployed system has no annotations, so here every sample is
simply the last ``size`` sensor events at some point in the stream:

    events:  e1 e2 e3 ... e100 e101 e102 ...
    window at e100 = [e1 .. e100],  window at e101 = [e2 .. e101], ...

Each window is labelled with the activity going on at its *last* event, which
is the activity a live system would have to report at that moment.

Two labelling rules:

``last``   The activity of the most recent annotated event, carried forward
           through unannotated gaps. No "Other" class. This is the raw-stream
           protocol of LastAct (Liu et al., 2026), so results are comparable
           with that paper.
``other``  The activity of the last event if it is annotated, otherwise
           "Other". This is what the product needs: periods that match no
           named activity must be recognised as such.

Windows are returned as a ``Home`` whose ``segments`` table has the same
columns as the annotated segments (activity, start, end, lo, hi), so every
feature function in ``features.py`` works on them unchanged.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from .data import Home

OTHER = "Other"


def event_labels(home: Home) -> tuple[np.ndarray, list[str]]:
    """Activity index for every event (-1 = not inside any annotated activity).

    Where annotated activities overlap (frequent in Milan), the one that started
    most recently wins, since that is the activity the resident switched to.
    """
    classes = home.activities
    idx = {c: i for i, c in enumerate(classes)}
    labels = np.full(len(home.times), -1, dtype=np.int32)
    seg = home.segments.sort_values("start", kind="stable")
    for act, lo, hi in zip(seg["activity"], seg["lo"], seg["hi"]):
        labels[lo:hi] = idx[act]
    return labels, classes


def _carry_forward(labels: np.ndarray) -> np.ndarray:
    """Replace -1 by the previous annotated label (stays -1 before the first one)."""
    pos = np.where(labels >= 0, np.arange(len(labels)), -1)
    np.maximum.accumulate(pos, out=pos)
    out = np.where(pos >= 0, labels[np.maximum(pos, 0)], -1)
    return out


def make_windows(home: Home, ends: np.ndarray, size: int, rule: str = "last") -> Home:
    """Windows ending at the given event indices (exclusive end: window = [end-size, end)).

    Windows whose label is undefined (before the first annotation with
    ``rule='last'``) are dropped.
    """
    labels, classes = event_labels(home)
    if rule == "last":
        lab = _carry_forward(labels)
        names = classes
    elif rule == "other":
        lab = np.where(labels >= 0, labels, len(classes))
        names = classes + [OTHER]
    else:
        raise ValueError(rule)

    ends = np.asarray(ends)
    ends = ends[ends >= size]
    last = ends - 1
    y = lab[last]
    keep = y >= 0
    ends, last, y = ends[keep], last[keep], y[keep]
    lo = ends - size
    segments = pd.DataFrame({
        "activity": np.asarray(names, dtype=object)[y],
        "start": pd.to_datetime(home.times[lo]),
        "end": pd.to_datetime(home.times[last]),
        "lo": lo,
        "hi": ends,
    })
    return replace(home, segments=segments)


def day_split(home: Home, train_frac: float = 0.6, test_frac: float = 0.2):
    """Event-index ranges for a chronological split by calendar day.

    Returns (train_end, test_start): events [0, train_end) are in the first
    ``train_frac`` of days, events [test_start, n) in the last ``test_frac``.
    The days in between are the validation period, unused here.
    """
    days = pd.to_datetime(home.times).normalize()
    unique = np.sort(days.unique())
    train_cut = unique[int(len(unique) * train_frac)]
    test_cut = unique[int(len(unique) * (1 - test_frac))]
    t = home.times
    train_end = int(np.searchsorted(t, np.datetime64(train_cut), side="left"))
    test_start = int(np.searchsorted(t, np.datetime64(test_cut), side="left"))
    return train_end, test_start, pd.Timestamp(train_cut), pd.Timestamp(test_cut)
