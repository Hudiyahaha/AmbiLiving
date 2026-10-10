"""Load CASAS smart-home logs and cut them into labelled activity segments.

Raw line format (whitespace separated, annotation columns optional):

    2010-11-04 00:03:50.209589 M003 ON Sleeping begin

Each annotated begin/end pair becomes one *segment*: every sensor event whose
timestamp lies inside [begin, end]. This is the "explicit segmentation" setting
used by most CASAS HAR papers (Aruba -> 6,477 instances, Milan -> 2,353).
"""

from __future__ import annotations

import pickle
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

ML_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ML_DIR / "data" / "raw"
CACHE_DIR = ML_DIR / "data" / "cache"

DATASETS = {"aruba": "aruba.txt", "milan": "milan.txt"}

SENSOR_RE = re.compile(r"^[MDT]\d{3}$")
NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _clean_state(sensor: str, raw: str) -> str | None:
    """Normalise corrupted binary states, e.g. Aruba's 'ONc', 'OFF5', 'OFcF', 'CLOSED'."""
    v = raw.upper()
    if sensor[0] == "M":
        if v.startswith("ON"):
            return "ON"
        if v.startswith("OF"):
            return "OFF"
    elif sensor[0] == "D":
        if v.startswith("OPEN"):
            return "OPEN"
        if v.startswith("CLOSE"):
            return "CLOSE"
    return None


@dataclass
class Home:
    """All events of one dataset plus its activity segments."""

    name: str
    # Binary (motion + door) event stream, sorted by time.
    times: np.ndarray  # datetime64[ns]
    sensors: np.ndarray  # str, e.g. "M003"
    states: np.ndarray  # str, "ON"/"OFF"/"OPEN"/"CLOSE"
    # Segments: one row per annotated activity instance.
    segments: pd.DataFrame  # columns: activity, start, end, lo, hi
    sensor_list: list[str] = field(default_factory=list)
    temperature: pd.DataFrame | None = None  # timestamp, sensor, value

    @property
    def activities(self) -> list[str]:
        return sorted(self.segments["activity"].unique())

    def segment_slice(self, i: int) -> slice:
        row = self.segments.iloc[i]
        return slice(int(row.lo), int(row.hi))


def parse_raw(path: Path, name: str) -> Home:
    ts_bin, sens_bin, state_bin = [], [], []
    ts_temp, sens_temp, val_temp = [], [], []
    annotations: list[tuple[str, str, str]] = []  # (timestamp, activity, begin|end)
    dropped = 0

    with open(path, encoding="utf8", errors="replace") as f:
        for line in f:
            t = line.split()
            if len(t) < 4:
                continue
            ts = f"{t[0]} {t[1]}"
            sensor, raw = t[2], t[3]
            if len(t) >= 6 and t[5] in ("begin", "end"):
                annotations.append((ts, t[4], t[5]))
            if not SENSOR_RE.match(sensor):
                dropped += 1
                continue
            if sensor[0] == "T":
                m = NUM_RE.search(raw)
                if m:
                    ts_temp.append(ts)
                    sens_temp.append(sensor)
                    val_temp.append(float(m.group()))
                else:
                    dropped += 1
                continue
            state = _clean_state(sensor, raw)
            if state is None:
                dropped += 1
                continue
            ts_bin.append(ts)
            sens_bin.append(sensor)
            state_bin.append(state)

    times = pd.to_datetime(pd.Series(ts_bin), format="ISO8601").to_numpy()
    order = np.argsort(times, kind="stable")
    times = times[order]
    sensors = np.asarray(sens_bin, dtype=object)[order]
    states = np.asarray(state_bin, dtype=object)[order]

    # Pair begin/end per activity name. Milan has many nested/overlapping
    # activities, so a single global stack would mis-pair them.
    open_begins: dict[str, list[pd.Timestamp]] = {}
    rows = []
    ann_times = pd.to_datetime(pd.Series([a[0] for a in annotations]), format="ISO8601")
    for t_ann, (_, act, kind) in zip(ann_times, annotations):
        if kind == "begin":
            open_begins.setdefault(act, []).append(t_ann)
        elif open_begins.get(act):
            start = open_begins[act].pop()
            rows.append((act, start, t_ann))
    unclosed = sum(len(v) for v in open_begins.values())

    seg = pd.DataFrame(rows, columns=["activity", "start", "end"])
    seg = seg.sort_values("start", kind="stable").reset_index(drop=True)
    seg["lo"] = np.searchsorted(times, seg["start"].to_numpy(), side="left")
    seg["hi"] = np.searchsorted(times, seg["end"].to_numpy(), side="right")
    empty = int((seg["hi"] <= seg["lo"]).sum())
    seg = seg[seg["hi"] > seg["lo"]].reset_index(drop=True)

    temperature = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(pd.Series(ts_temp), format="ISO8601"),
            "sensor": sens_temp,
            "value": val_temp,
        }
    )

    print(
        f"[{name}] {len(times):,} binary events, {len(temperature):,} temperature readings, "
        f"{dropped} malformed lines dropped, {len(seg):,} segments "
        f"({empty} empty, {unclosed} unclosed annotations skipped)",
        file=sys.stderr,
    )
    return Home(
        name=name,
        times=times,
        sensors=sensors,
        states=states,
        segments=seg,
        sensor_list=sorted(set(sensors)),
        temperature=temperature,
    )


def load_home(name: str, raw_dir: Path = RAW_DIR, use_cache: bool = True) -> Home:
    if name not in DATASETS:
        raise ValueError(f"Unknown dataset {name!r}; choose from {sorted(DATASETS)}")
    path = raw_dir / DATASETS[name]
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Put the raw CASAS file there (see ml/README.md)."
        )
    cache = CACHE_DIR / f"{name}.pkl"
    if use_cache and cache.exists() and cache.stat().st_mtime > path.stat().st_mtime:
        with open(cache, "rb") as f:
            return pickle.load(f)
    home = parse_raw(path, name)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache, "wb") as f:
        pickle.dump(home, f)
    return home


if __name__ == "__main__":
    # python -m har.data aruba   -> prints class distribution and segment stats
    # Import via the package so cached pickles reference har.data.Home, not __main__.Home.
    from har.data import load_home

    for ds in sys.argv[1:] or list(DATASETS):
        h = load_home(ds, use_cache=False)
        seg = h.segments
        n_ev = seg["hi"] - seg["lo"]
        dur = (seg["end"] - seg["start"]).dt.total_seconds() / 60
        print(f"\n=== {ds}: {len(seg)} segments, {len(h.activities)} classes, "
              f"{len(h.sensor_list)} binary sensors ===")
        summary = pd.DataFrame(
            {
                "count": seg.groupby("activity").size(),
                "median_events": n_ev.groupby(seg["activity"]).median(),
                "median_minutes": dur.groupby(seg["activity"]).median().round(1),
            }
        ).sort_values("count", ascending=False)
        print(summary.to_string())
