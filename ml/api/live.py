"""Live recognition with the saved window model (ROADMAP 4.3).

The final window model (BiLSTM, decision in ``ml/results/windows.md``) classifies
the last 100 sensor events. Each home's model is loaded from ``ml/models/`` once,
on first use, and kept in memory.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np
import pandas as pd

from har.data import Home
from har.saved_model import WindowModel, load, model_path

from .store import ROOT, NotFound, check_home

MODEL_NAME, SEED, SIZE = "bilstm", 1, 100

# Raw CASAS states, plus the words the dashboard uses for them.
STATE_ALIASES = {
    "ON": "ON", "OFF": "OFF", "OPEN": "OPEN", "CLOSE": "CLOSE",
    "ACTIVE": "ON", "INACTIVE": "OFF", "CLOSED": "CLOSE",
}

_models: dict[str, WindowModel] = {}
_lock = threading.Lock()


def model_file(home: str):
    return model_path(check_home(home), MODEL_NAME, SEED, SIZE)


def get_model(home: str) -> WindowModel:
    path = model_file(home)
    with _lock:
        if home not in _models:
            if not path.is_file():
                raise NotFound(f"no saved window model for '{home}' at ml/models/; run "
                               f"`py -m har.saved_model --dataset {home}` first")
            _models[home] = load(path)
        return _models[home]


def model_info(home: str) -> dict:
    """What the API knows about a home's model, without loading torch weights."""
    path = model_file(home)
    info = {"available": path.is_file(), "loaded": home in _models,
            "file": path.relative_to(ROOT).as_posix()}
    if home in _models:
        wm = _models[home]
        info |= {"model": wm.name, "windowEvents": wm.size, "classes": wm.classes,
                 "trainedUntil": wm.meta.get("train_until")}
    return info


@dataclass
class Recognised:
    end: int  # index (exclusive) of the window's last event in the sorted input
    timestamp: pd.Timestamp
    activity: str
    confidence: float
    top: list[tuple[str, float]]


def to_home(home: str, timestamps, sensors, states) -> Home:
    """Build a ``Home`` from posted events, sorted by time (stable for equal times)."""
    times = pd.to_datetime(pd.Series(list(timestamps)), utc=False)
    if getattr(times.dt, "tz", None) is not None:
        times = times.dt.tz_localize(None)
    mapped = []
    for s in states:
        m = STATE_ALIASES.get(str(s).upper())
        if m is None:
            raise ValueError(f"unknown sensor state '{s}'; use ON/OFF/OPEN/CLOSE "
                             "(or active/inactive/open/closed)")
        mapped.append(m)
    order = np.argsort(times.to_numpy(), kind="stable")
    sensors = np.asarray([str(s) for s in sensors], dtype=object)[order]
    segments = pd.DataFrame({"activity": pd.Series(dtype=object),
                             "start": pd.Series(dtype="datetime64[ns]"),
                             "end": pd.Series(dtype="datetime64[ns]"),
                             "lo": pd.Series(dtype=np.int64), "hi": pd.Series(dtype=np.int64)})
    return Home(name=home, times=times.to_numpy(dtype="datetime64[ns]")[order], sensors=sensors,
                states=np.asarray(mapped, dtype=object)[order], segments=segments,
                sensor_list=sorted(set(sensors)))


def recognise(home: str, timestamps, sensors, states, every: int | None = None,
              top_k: int = 3) -> tuple[list[Recognised], dict]:
    """Recognise the activity at the last event, or at every ``every``-th event.

    With ``every``, windows end at the last event and every ``every`` events before
    it (as far back as a full window allows), in time order.
    """
    wm = get_model(home)
    h = to_home(home, timestamps, sensors, states)
    n = len(h.times)
    if n < wm.size:
        raise ValueError(f"need at least {wm.size} events to fill a window; got {n}")
    ends = np.arange(n, wm.size - 1, -every)[::-1] if every else np.array([n])
    p = wm.predict_proba(h, ends)
    known = set(wm.vocab)
    unknown = sorted({f"{s}_{v}" for s, v in zip(h.sensors, h.states)} - known)
    out = []
    for e, row in zip(ends, p):
        best = np.argsort(row)[::-1][:top_k]
        out.append(Recognised(int(e), pd.Timestamp(h.times[e - 1]), wm.classes[best[0]],
                              float(row[best[0]]), [(wm.classes[i], float(row[i])) for i in best]))
    return out, {"events": n, "unknownSensorStates": unknown}
