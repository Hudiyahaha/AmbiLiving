"""Turn activity segments into model inputs.

Two representations:

* ``handcrafted_features`` - one fixed-length vector per segment (Approach 1).
* ``encode_sequences``     - the ordered event sequence of each segment as
                             token ids + per-event continuous features
                             (Approaches 2 and 3).

Both share ``segment_context``: when the segment happened and how long it
lasted. Note that duration / event count are only known once the segment has
ended; that is inherent to the explicit-segmentation setting.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .data import Home

SECONDS_PER_DAY = 86400.0


def _cyclic(x: np.ndarray, period: float) -> tuple[np.ndarray, np.ndarray]:
    angle = 2 * np.pi * x / period
    return np.sin(angle), np.cos(angle)


def _seconds_of_day(t: np.ndarray) -> np.ndarray:
    day = t.astype("datetime64[D]")
    return (t - day).astype("timedelta64[ms]").astype(np.float64) / 1000.0


def preceding_context(home: Home, window_s: float = 600.0) -> tuple[np.ndarray, list[str]]:
    """What the house looked like just *before* each segment (past only, no lookahead).

    Motivation: in Aruba, Enter_Home and Leave_Home segments contain nearly the
    same events (D004 OPEN, M030 ON, D004 CLOSE, M030 OFF). What separates them
    is the preceding activity: a silent house before the door opens means
    someone is entering; recent motion inside means someone is leaving.
    """
    t_sec = home.times.astype("datetime64[ms]").astype(np.float64) / 1000.0
    lo = home.segments["lo"].to_numpy()
    start = home.segments["start"].to_numpy().astype("datetime64[ms]").astype(np.float64) / 1000.0
    sensors = home.sensors

    n = len(lo)
    X = np.zeros((n, 3), np.float32)
    w_lo = np.searchsorted(t_sec, start - window_s, side="left")
    for i in range(n):
        gap = start[i] - t_sec[lo[i] - 1] if lo[i] > 0 else window_s * 100
        k = lo[i] - w_lo[i]
        X[i] = [
            np.log1p(max(gap, 0.0)),
            np.log1p(k),
            len(set(sensors[w_lo[i]:lo[i]])) if k else 0,
        ]
    return X, ["log_gap_before_s", "log_events_prev_10min", "distinct_sensors_prev_10min"]


def preceding_profile(home: Home, window_s: float = 600.0) -> tuple[np.ndarray, list[str]]:
    """*Which* sensors fired just before each segment (past only, no lookahead).

    Motivation: ``preceding_context`` collapses the pre-segment window to a
    count of distinct sensors, which cannot separate Wash_Dishes from
    Meal_Preparation — both are short kitchen bursts with near-identical
    durations (median 4.8 vs 5.3 min) and sensor proportions. What separates
    them is that Wash_Dishes follows a *meal*: 38 of 65 Aruba Wash_Dishes
    segments are preceded by Eating, against 39 of 1,606 Meal_Preparation
    segments. That shows up in the dining-area sensor M014, which holds 24.5%
    of pre-window events before Wash_Dishes but only 6.0% before
    Meal_Preparation.

    Two blocks, both derived from sensor events alone (never from labels, so
    there is no leakage and it still works live):

    * per-sensor share of events in the preceding ``window_s``;
    * one-hot of the single most recent sensor before the segment starts.
    """
    sensors = home.sensor_list
    s_idx = {s: i for i, s in enumerate(sensors)}
    S = len(sensors)
    sensor_ids = np.array([s_idx[s] for s in home.sensors], dtype=np.int32)

    t_sec = home.times.astype("datetime64[ms]").astype(np.float64) / 1000.0
    lo = home.segments["lo"].to_numpy()
    start = home.segments["start"].to_numpy().astype("datetime64[ms]").astype(np.float64) / 1000.0

    n = len(lo)
    share = np.zeros((n, S), np.float32)
    prev_last = np.zeros((n, S), np.float32)
    w_lo = np.searchsorted(t_sec, start - window_s, side="left")
    for i in range(n):
        ids = sensor_ids[w_lo[i]:lo[i]]
        if len(ids):
            share[i] = np.bincount(ids, minlength=S) / len(ids)
        if lo[i] > 0:
            prev_last[i, sensor_ids[lo[i] - 1]] = 1

    names = ([f"prev_frac_{s}" for s in sensors] + [f"prev_last_{s}" for s in sensors])
    return np.hstack([share, prev_last]), names


def segment_context(
    home: Home, preceding: bool = False, profile: bool = False
) -> tuple[np.ndarray, list[str]]:
    """Time-of-day, weekday, duration and size of each segment.

    With ``preceding=True`` also appends ``preceding_context``, and with
    ``profile=True`` also appends ``preceding_profile``.
    """
    seg = home.segments
    start = seg["start"].to_numpy()
    end = seg["end"].to_numpy()
    n_events = (seg["hi"] - seg["lo"]).to_numpy().astype(np.float64)
    duration = (end - start).astype("timedelta64[ms]").astype(np.float64) / 1000.0

    s_sin, s_cos = _cyclic(_seconds_of_day(start), SECONDS_PER_DAY)
    e_sin, e_cos = _cyclic(_seconds_of_day(end), SECONDS_PER_DAY)
    weekday = seg["start"].dt.weekday.to_numpy()
    w_sin, w_cos = _cyclic(weekday.astype(np.float64), 7.0)

    X = np.column_stack(
        [
            np.log1p(np.maximum(duration, 0)),
            np.log1p(n_events),
            np.log1p(n_events / np.maximum(duration / 60.0, 1 / 60.0)),
            s_sin, s_cos, e_sin, e_cos, w_sin, w_cos,
        ]
    )
    names = ["log_duration_s", "log_n_events", "log_events_per_min",
             "start_sin", "start_cos", "end_sin", "end_cos", "weekday_sin", "weekday_cos"]
    X = X.astype(np.float32)
    if preceding:
        P, p_names = preceding_context(home)
        X, names = np.hstack([X, P]), names + p_names
    return X, names


def handcrafted_features(home: Home, preceding: bool = False) -> tuple[np.ndarray, list[str]]:
    """Fixed-length feature vector per segment for classical ML."""
    ctx, ctx_names = segment_context(home, preceding)
    sensors = home.sensor_list
    s_idx = {s: i for i, s in enumerate(sensors)}
    S = len(sensors)
    sensor_ids = np.array([s_idx[s] for s in home.sensors], dtype=np.int32)
    is_active = np.isin(home.states, ["ON", "OPEN"])
    t_sec = home.times.astype("datetime64[ms]").astype(np.float64) / 1000.0

    seg = home.segments
    n = len(seg)
    frac_all = np.zeros((n, S), np.float32)  # share of segment events per sensor
    frac_active = np.zeros((n, S), np.float32)  # share of ON/OPEN events per sensor
    first = np.zeros((n, S), np.float32)
    last = np.zeros((n, S), np.float32)
    extra = np.zeros((n, 5), np.float32)

    for i, (lo, hi) in enumerate(zip(seg["lo"].to_numpy(), seg["hi"].to_numpy())):
        ids = sensor_ids[lo:hi]
        k = len(ids)
        frac_all[i] = np.bincount(ids, minlength=S) / k
        act = ids[is_active[lo:hi]]
        if len(act):
            frac_active[i] = np.bincount(act, minlength=S) / len(act)
        first[i, ids[0]] = 1
        last[i, ids[-1]] = 1
        gaps = np.diff(t_sec[lo:hi]) if k > 1 else np.zeros(1)
        n_distinct = len(np.unique(ids))
        # Number of times the resident moved to a different sensor.
        transitions = int((np.diff(ids) != 0).sum()) if k > 1 else 0
        extra[i] = [
            n_distinct,
            n_distinct / k,
            np.log1p(gaps.mean()),
            np.log1p(gaps.max()),
            transitions / k,
        ]

    X = np.hstack([ctx, extra, frac_all, frac_active, first, last])
    names = (
        ctx_names
        + ["n_distinct_sensors", "distinct_ratio", "log_mean_gap", "log_max_gap", "transition_rate"]
        + [f"frac_{s}" for s in sensors]
        + [f"frac_active_{s}" for s in sensors]
        + [f"first_{s}" for s in sensors]
        + [f"last_{s}" for s in sensors]
    )
    return X, names


@dataclass
class SequenceData:
    tokens: np.ndarray  # (N, L) int64, 0 = padding
    cont: np.ndarray  # (N, L, C) float32 per-event features
    mask: np.ndarray  # (N, L) bool, True = real event
    context: np.ndarray  # (N, K) float32 segment-level features
    vocab: list[str]  # index -> "M003_ON"; index 0 is "<pad>"

    def subset(self, idx: np.ndarray) -> "SequenceData":
        return SequenceData(self.tokens[idx], self.cont[idx], self.mask[idx],
                            self.context[idx], self.vocab)


def encode_sequences(home: Home, max_len: int = 128, preceding: bool = False) -> SequenceData:
    """Each event becomes a token "<sensor>_<state>" plus timing features.

    Segments longer than ``max_len`` are uniformly subsampled (order kept), so
    long activities like Sleeping still show their whole sensor footprint.
    Timing features are computed on the full sequence before subsampling.
    """
    vocab = ["<pad>"] + sorted({f"{s}_{v}" for s, v in zip(home.sensors, home.states)})
    tok_idx = {t: i for i, t in enumerate(vocab)}
    all_tokens = np.array([tok_idx[f"{s}_{v}"] for s, v in zip(home.sensors, home.states)],
                          dtype=np.int64)
    t_sec = home.times.astype("datetime64[ms]").astype(np.float64) / 1000.0
    tod_sin, tod_cos = _cyclic(_seconds_of_day(home.times), SECONDS_PER_DAY)

    seg = home.segments
    n = len(seg)
    tokens = np.zeros((n, max_len), np.int64)
    cont = np.zeros((n, max_len, 4), np.float32)
    mask = np.zeros((n, max_len), bool)

    for i, (lo, hi) in enumerate(zip(seg["lo"].to_numpy(), seg["hi"].to_numpy())):
        k = hi - lo
        ts = t_sec[lo:hi]
        gap = np.concatenate([[0.0], np.diff(ts)])
        since_start = ts - ts[0]
        feats = np.column_stack([
            np.log1p(gap),
            np.log1p(since_start),
            tod_sin[lo:hi],
            tod_cos[lo:hi],
        ])
        if k > max_len:
            pick = np.linspace(0, k - 1, max_len).round().astype(int)
        else:
            pick = np.arange(k)
        m = len(pick)
        tokens[i, :m] = all_tokens[lo:hi][pick]
        cont[i, :m] = feats[pick]
        mask[i, :m] = True

    context, _ = segment_context(home, preceding)
    return SequenceData(tokens, cont, mask, context, vocab)
