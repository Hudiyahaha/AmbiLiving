"""Synthetic routine anomalies injected into the raw sensor stream (decision D13).

CASAS has no anomaly labels, so we make them: every monitoring day is copied and
one anomaly is planted in the copy by editing the *sensor events* (and the matching
annotations). The recognisers then have to see the anomaly through the sensors,
exactly as a deployed system would, which is what lets us measure how recognition
errors propagate into anomaly detection.

Anomaly types (decision D12):

``missed``          delete every event inside the target activity's segments that day
``prolonged``       stretch one segment's events by +60-120 min, shift the rest of the day
``unusual_time``    move one segment's events to a random time between 01:00 and 04:30
``night_frequency`` insert 4 Bed_to_Toilet episodes (copied from training days) 00:30-05:30
``inactivity``      delete all events in a 2.5-4 h window starting 08:00-15:00 while at home

All variants of all days are then laid out on one synthetic timeline
(``build_combined``) so the existing feature code runs on them unchanged. Each
copy is shifted by a whole number of weeks, which keeps time of day and weekday.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .data import Home

TYPES = ["missed", "prolonged", "unusual_time", "night_frequency", "inactivity"]
DRIFT_DAYS = 7
DRIFT_STEP_MIN = 20  # the first cooking episode moves this much later per day of the run
COOKING = ["Meal_Preparation", "Kitchen_Activity"]

# Target activities per home and type (D12). Only activities present in that home are used.
TARGETS = {
    "missed": ["Meal_Preparation", "Kitchen_Activity", "Morning_Meds"],
    "prolonged": ["Meal_Preparation", "Bed_to_Toilet", "Kitchen_Activity", "Master_Bathroom",
                  "Guest_Bathroom"],
    "unusual_time": ["Meal_Preparation", "Kitchen_Activity", "Leave_Home"],
    "night_frequency": ["Bed_to_Toilet"],
}
AWAY = {"Leave_Home"}
DAY = pd.Timedelta(days=1)
MIN = pd.Timedelta(minutes=1)


@dataclass
class Variant:
    """One monitoring day, clean or with one injected anomaly (real timestamps)."""

    vid: int
    day: pd.Timestamp
    kind: str  # "clean" or one of TYPES
    times: np.ndarray  # datetime64[ns], sorted, all inside [day, day + 1)
    sensors: np.ndarray
    states: np.ndarray
    segments: pd.DataFrame  # activity, start, end (annotations after the edit)
    target: str = ""
    a_start: pd.Timestamp | None = None  # anomaly interval, for matching alerts
    a_end: pd.Timestamp | None = None
    note: str = ""
    seq: int = -1  # drift run id (multi-day drift only)
    pos: int = 0  # day number inside the drift run, 1..DRIFT_DAYS
    # filled by build_combined
    offset: pd.Timedelta = field(default=pd.Timedelta(0))
    lo: int = 0  # first day event in the combined home
    hi: int = 0


def day_events(home: Home, day: pd.Timestamp):
    t = home.times
    lo = int(np.searchsorted(t, np.datetime64(day), side="left"))
    hi = int(np.searchsorted(t, np.datetime64(day + DAY), side="left"))
    seg = home.segments
    seg = seg[(seg["start"] >= day) & (seg["start"] < day + DAY)][["activity", "start", "end"]]
    return t[lo:hi].copy(), home.sensors[lo:hi].copy(), home.states[lo:hi].copy(), \
        seg.reset_index(drop=True)


def _inside(times: np.ndarray, start, end) -> np.ndarray:
    return (times >= pd.Timestamp(start).to_datetime64()) & (times <= pd.Timestamp(end).to_datetime64())


def _sorted(times, sensors, states):
    o = np.argsort(times, kind="stable")
    return times[o], sensors[o], states[o]


def _present(seg: pd.DataFrame, names: list[str]) -> list[str]:
    return [a for a in names if a in set(seg["activity"])]


def inject(kind: str, home: Home, day: pd.Timestamp, rng: np.random.Generator,
           library: pd.DataFrame, daily: set[str]) -> Variant | None:
    """Return a copy of ``day`` with one anomaly of ``kind``, or None if impossible that day.

    ``library``: Bed_to_Toilet segments from training days to copy for night_frequency.
    ``daily``: activities present on >= 80 % of training days (targets for ``missed``).
    """
    times, sensors, states, seg = day_events(home, day)
    v = dict(vid=-1, day=day, kind=kind)

    if kind == "missed":
        cands = [a for a in _present(seg, TARGETS["missed"]) if a in daily]
        if not cands:
            return None
        act = cands[rng.integers(len(cands))]
        rows = seg[seg["activity"] == act]
        drop = np.zeros(len(times), bool)
        for s, e in zip(rows["start"], rows["end"]):
            drop |= _inside(times, s, e)
        seg = seg[seg["activity"] != act]
        return Variant(**v, times=times[~drop], sensors=sensors[~drop], states=states[~drop],
                       segments=seg.reset_index(drop=True), target=act,
                       a_start=rows["start"].min(), a_end=day + DAY,
                       note=f"removed {len(rows)} {act} episodes ({int(drop.sum())} events)")

    if kind == "prolonged":
        cands = _present(seg, TARGETS["prolonged"])
        if not cands:
            return None
        act = cands[rng.integers(len(cands))]
        rows = seg[(seg["activity"] == act) & (seg["start"] < day + pd.Timedelta(hours=21))]
        if rows.empty:
            return None
        i = rows.index[rng.integers(len(rows))]
        s, e = seg.loc[i, "start"], seg.loc[i, "end"]
        dur = max(e - s, pd.Timedelta(seconds=30))
        extra = pd.Timedelta(minutes=float(rng.uniform(60, 120)))
        factor = (dur + extra) / dur
        t = times.astype("datetime64[ns]").copy()
        ins = _inside(t, s, e)
        after = t > e.to_datetime64()
        t[ins] = s.to_datetime64() + ((t[ins] - s.to_datetime64()) * factor).astype("timedelta64[ns]")
        t[after] = t[after] + extra.to_timedelta64()
        seg = seg.copy()
        later = seg["start"] > e
        seg.loc[later, ["start", "end"]] = seg.loc[later, ["start", "end"]] + extra
        seg.loc[i, "end"] = e + extra
        keep = t < (day + DAY).to_datetime64()
        seg = seg[seg["start"] < day + DAY]
        return Variant(**v, times=t[keep], sensors=sensors[keep], states=states[keep],
                       segments=seg.reset_index(drop=True), target=act, a_start=s,
                       a_end=e + extra,
                       note=f"{act} at {s:%H:%M} stretched from {dur.total_seconds() / 60:.0f} "
                            f"to {(dur + extra).total_seconds() / 60:.0f} min")

    if kind == "unusual_time":
        cands = _present(seg, TARGETS["unusual_time"])
        if not cands:
            return None
        act = cands[rng.integers(len(cands))]
        rows = seg[(seg["activity"] == act) & (seg["start"] >= day + pd.Timedelta(hours=7))]
        if rows.empty:
            return None
        i = rows.index[rng.integers(len(rows))]
        s, e = seg.loc[i, "start"], seg.loc[i, "end"]
        new_s = day + pd.Timedelta(minutes=float(rng.uniform(60, 270)))
        shift = new_s - s
        ins = _inside(times, s, e)
        t = times.copy()
        t[ins] = t[ins] + shift.to_timedelta64()
        seg = seg.copy()
        seg.loc[i, ["start", "end"]] = [new_s, e + shift]
        t, se, st = _sorted(t, sensors, states)
        return Variant(**v, times=t, sensors=se, states=st,
                       segments=seg.sort_values("start").reset_index(drop=True), target=act,
                       a_start=new_s, a_end=e + shift,
                       note=f"{act} moved from {s:%H:%M} to {new_s:%H:%M}")

    if kind == "night_frequency":
        if library.empty:
            return None
        add_t, add_s, add_v, add_rows = [], [], [], []
        slots = np.sort(rng.choice(np.arange(30, 330, 25), size=4, replace=False))
        for m in slots:
            src = library.iloc[rng.integers(len(library))]
            lo, hi = int(src["lo"]), int(src["hi"])
            st = day + pd.Timedelta(minutes=float(m + rng.uniform(0, 10)))
            shift = st.to_datetime64() - home.times[lo]
            add_t.append(home.times[lo:hi] + shift)
            add_s.append(home.sensors[lo:hi])
            add_v.append(home.states[lo:hi])
            add_rows.append(("Bed_to_Toilet", st, st + (src["end"] - src["start"])))
        t = np.concatenate([times, *add_t])
        se = np.concatenate([sensors, *add_s])
        sv = np.concatenate([states, *add_v])
        t, se, sv = _sorted(t, se, sv)
        new = pd.DataFrame(add_rows, columns=["activity", "start", "end"])
        seg = pd.concat([seg, new]).sort_values("start").reset_index(drop=True)
        return Variant(**v, times=t, sensors=se, states=sv, segments=seg,
                       target="Bed_to_Toilet", a_start=new["start"].min(),
                       a_end=new["end"].max(),
                       note="4 extra Bed_to_Toilet trips between "
                            f"{new['start'].min():%H:%M} and {new['end'].max():%H:%M}")

    if kind == "inactivity":
        for _ in range(20):
            s = day + pd.Timedelta(minutes=float(rng.uniform(8 * 60, 15 * 60)))
            e = s + pd.Timedelta(minutes=float(rng.uniform(150, 240)))
            ins = _inside(times, s, e)
            # The resident must be at home and actually active in the window.
            near = seg[(seg["end"] >= s - pd.Timedelta(hours=1)) & (seg["start"] <= e)]
            if ins.sum() < 50 or near["activity"].isin(AWAY | {"Enter_Home"}).any():
                continue
            prev = seg[seg["start"] < s]
            if not prev.empty and prev["activity"].iloc[-1] in AWAY:
                continue
            seg2 = seg.copy()
            seg2.loc[(seg2["start"] >= s) & (seg2["start"] <= e), "start"] = e
            seg2.loc[(seg2["end"] >= s) & (seg2["end"] <= e), "end"] = s
            seg2 = seg2[seg2["end"] > seg2["start"]]
            return Variant(**v, times=times[~ins], sensors=sensors[~ins], states=states[~ins],
                           segments=seg2.reset_index(drop=True), target="",
                           a_start=s, a_end=e,
                           note=f"no events {s:%H:%M}-{e:%H:%M} "
                                f"({(e - s).total_seconds() / 60:.0f} min, "
                                f"{int(ins.sum())} events removed)")
        return None

    raise ValueError(kind)


def make_variants(home: Home, days: list[pd.Timestamp], train_cut: pd.Timestamp,
                  per_day: int, seed: int) -> list[Variant]:
    """Clean copy of every day plus ``per_day`` injected copies per type."""
    rng = np.random.default_rng(seed)
    seg = home.segments
    train_seg = seg[seg["start"] < train_cut]
    library = train_seg[train_seg["activity"] == "Bed_to_Toilet"]
    library = library[(library["hi"] - library["lo"]) >= 3]
    tdays = train_seg["start"].dt.normalize()
    p_day = train_seg.groupby("activity")["start"].apply(
        lambda s: s.dt.normalize().nunique()) / tdays.nunique()
    daily = set(p_day[p_day >= 0.8].index)

    out: list[Variant] = []
    for day in days:
        t, s, v, sg = day_events(home, day)
        out.append(Variant(vid=-1, day=day, kind="clean", times=t, sensors=s, states=v,
                           segments=sg))
        for kind in TYPES:
            seen: set[str] = set()
            for _ in range(per_day * 3):
                if len(seen) == per_day:
                    break
                var = inject(kind, home, day, rng, library, daily)
                # Identical copies (e.g. the only `missed` target that day) add no information.
                if var is not None and var.note not in seen:
                    seen.add(var.note)
                    out.append(var)
    # Multi-day drift: runs of DRIFT_DAYS consecutive days in which the first cooking
    # episode after 05:00 moves DRIFT_STEP_MIN minutes later per day.
    n = len(days)
    starts = sorted(set(range(0, n - DRIFT_DAYS + 1, DRIFT_DAYS)) | {max(n - DRIFT_DAYS, 0)})
    for seq, s0 in enumerate(starts if n >= DRIFT_DAYS else []):
        for k in range(1, DRIFT_DAYS + 1):
            out.append(drift_day(home, days[s0 + k - 1], k, seq))
    for i, var in enumerate(out):
        var.vid = i
    return out


def drift_day(home: Home, day: pd.Timestamp, k: int, seq: int) -> Variant:
    """Day ``k`` of a drift run: first cooking episode after 05:00 moved k * step later."""
    times, sensors, states, seg = day_events(home, day)
    acts = _present(seg, COOKING)
    base = dict(vid=-1, day=day, kind="drift", seq=seq, pos=k)
    rows = seg[seg["activity"].isin(acts) & (seg["start"] >= day + pd.Timedelta(hours=5))]
    if rows.empty:
        return Variant(**base, times=times, sensors=sensors, states=states, segments=seg,
                       target=acts[0] if acts else COOKING[0], note="no cooking to shift")
    i = rows.index[0]
    act, s, e = seg.loc[i, "activity"], seg.loc[i, "start"], seg.loc[i, "end"]
    shift = pd.Timedelta(minutes=DRIFT_STEP_MIN * k)
    ins = _inside(times, s, e)
    t = times.copy()
    t[ins] = t[ins] + shift.to_timedelta64()
    keep = t < (day + DAY).to_datetime64()
    seg = seg.copy()
    seg.loc[i, ["start", "end"]] = [s + shift, e + shift]
    t, se, st = _sorted(t[keep], sensors[keep], states[keep])
    return Variant(**base, times=t, sensors=se, states=st,
                   segments=seg.sort_values("start").reset_index(drop=True), target=act,
                   a_start=s + shift, a_end=e + shift,
                   note=f"drift run {seq} day {k}: first {act} moved {s:%H:%M} -> "
                        f"{s + shift:%H:%M}")


def build_combined(home: Home, base_end: int, base_cut: pd.Timestamp,
                   variants: list[Variant], prefix_hours: float = 6.0,
                   min_prefix: int = 150) -> Home:
    """One ``Home`` = real events [0, base_end) followed by every variant on its own week.

    Each variant block is the real ``prefix_hours`` before its day (at least
    ``min_prefix`` events, so the first windows and the pre-segment context are
    complete) followed by the variant's day events. Segments keep columns
    activity/start/end/lo/hi plus ``vid`` (-1 for the real part).
    """
    t_parts = [home.times[:base_end]]
    s_parts = [home.sensors[:base_end]]
    v_parts = [home.states[:base_end]]
    base_seg = home.segments[home.segments["start"] < base_cut][["activity", "start", "end"]]
    seg_parts = [base_seg.assign(vid=-1)]
    week = pd.Timedelta(days=7)
    prev_end = pd.Timestamp(home.times[base_end - 1])
    n = base_end
    for var in variants:
        d = np.datetime64(var.day)
        p_lo = min(int(np.searchsorted(home.times, d - np.timedelta64(int(prefix_hours * 3600), "s"))),
                   int(np.searchsorted(home.times, d)) - min_prefix)
        p_hi = int(np.searchsorted(home.times, d))
        p_start = pd.Timestamp(home.times[p_lo])
        need = prev_end + pd.Timedelta(hours=1) - p_start
        weeks = max(1, int(np.ceil(need / week)))
        off = weeks * week
        var.offset = off
        o = off.to_timedelta64()
        t_parts += [home.times[p_lo:p_hi] + o, var.times + o]
        s_parts += [home.sensors[p_lo:p_hi], var.sensors]
        v_parts += [home.states[p_lo:p_hi], var.states]
        var.lo = n + (p_hi - p_lo)
        var.hi = var.lo + len(var.times)
        n = var.hi
        seg_parts.append(var.segments.assign(start=var.segments["start"] + off,
                                             end=var.segments["end"] + off, vid=var.vid))
        last = var.times[-1] if len(var.times) else home.times[p_hi - 1]
        prev_end = pd.Timestamp(last) + off

    times = np.concatenate(t_parts)
    assert np.all(np.diff(times.astype(np.int64)) >= 0), "combined timeline must be sorted"
    seg = pd.concat(seg_parts, ignore_index=True)
    seg["lo"] = np.searchsorted(times, seg["start"].to_numpy(), side="left")
    seg["hi"] = np.searchsorted(times, seg["end"].to_numpy(), side="right")
    # Keep each variant's segments inside its own block.
    for var in variants:
        m = (seg["vid"] == var.vid).to_numpy()
        seg.loc[m, "lo"] = seg.loc[m, "lo"].clip(var.lo, var.hi)
        seg.loc[m, "hi"] = seg.loc[m, "hi"].clip(var.lo, var.hi)
    seg = seg[seg["hi"] > seg["lo"]].reset_index(drop=True)
    return Home(name=home.name + "+variants", times=times,
                sensors=np.concatenate(s_parts), states=np.concatenate(v_parts),
                segments=seg, sensor_list=home.sensor_list, temperature=None)
