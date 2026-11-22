"""Live monitoring sessions (ROADMAP 4.3): push sensor events, get activities and alerts.

A session runs the whole live pipeline for one home on events as they arrive
(``har.routine_live.LiveMonitor``): the saved BiLSTM every 10th event, the saved
routine model every 2 minutes of the clock, and D15 alert routing. Sessions live
in memory; idle ones are dropped after an hour.
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field
from functools import lru_cache

import pandas as pd

from har.routine_live import LiveMonitor, LiveRoutine, routine_path
from har.routine_live import load as load_routine

from . import live
from .store import NotFound, check_home, read_json

MAX_SESSIONS = 32
IDLE_SECONDS = 3600


@lru_cache(maxsize=None)
def get_routine(home: str) -> LiveRoutine:
    if not routine_path(check_home(home)).is_file():
        raise NotFound(f"no saved routine model for '{home}'; run "
                       f"`py -m har.routine_live --home {home}` in ml/ first")
    return load_routine(home)


def routine_info(home: str) -> dict:
    """The saved routine model's summary (``models/<home>/routine.json``)."""
    path = routine_path(check_home(home)).with_suffix(".json")
    return read_json(path)


@dataclass
class Session:
    id: str
    home: str
    monitor_from: pd.Timestamp | None
    monitor: LiveMonitor | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)
    created: float = field(default_factory=time.time)
    used: float = field(default_factory=time.time)

    def push(self, timestamps, sensors, states, now=None) -> dict:
        times, mapped = live.normalise(timestamps, states)
        with self.lock:
            self.used = time.time()
            if self.monitor is None:
                start = self.monitor_from
                if start is None:
                    if not len(times) and now is None:
                        raise ValueError("the first push needs events or a clock time")
                    start = pd.Timestamp(times.min() if len(times) else now)
                self.monitor = LiveMonitor(live.get_model(self.home), get_routine(self.home),
                                           start)
            return self.monitor.push(times, sensors, mapped, now)


_sessions: dict[str, Session] = {}
_lock = threading.Lock()


def _expire() -> None:
    cutoff = time.time() - IDLE_SECONDS
    for sid in [s for s, v in _sessions.items() if v.used < cutoff]:
        del _sessions[sid]


def create(home: str, monitor_from=None) -> Session:
    check_home(home)
    get_routine(home)  # fail now, not on the first push
    with _lock:
        _expire()
        if len(_sessions) >= MAX_SESSIONS:
            oldest = min(_sessions.values(), key=lambda s: s.used)
            del _sessions[oldest.id]
        s = Session(secrets.token_hex(8), home,
                    pd.Timestamp(monitor_from).normalize() if monitor_from else None)
        _sessions[s.id] = s
        return s


def get(session_id: str) -> Session:
    with _lock:
        s = _sessions.get(session_id)
    if s is None:
        raise NotFound(f"no live session '{session_id}' (sessions expire after "
                       f"{IDLE_SECONDS // 60} idle minutes)")
    return s


def delete(session_id: str) -> None:
    with _lock:
        if _sessions.pop(session_id, None) is None:
            raise NotFound(f"no live session '{session_id}'")


# --------------------------------------------------------------------------- JSON

def _iso(t) -> str:
    return pd.Timestamp(t).isoformat()


def alert_id(a: dict) -> str:
    return f"{a['kind']}-{a['activity']}-{pd.Timestamp(a['time']):%Y%m%d%H%M}"


def alert_json(a: dict, day: pd.Timestamp) -> dict:
    out = {"id": alert_id(a), "raisedAt": _iso(day + pd.Timedelta(seconds=a["raisedAt"])),
           "time": _iso(a["time"])}
    out |= {k: v for k, v in a.items() if k not in ("raisedAt", "time")}
    return out


def state_json(s: Session) -> dict:
    m = s.monitor
    if m is None:
        return {"session": s.id, "home": s.home, "started": False,
                "monitorFrom": _iso(s.monitor_from) if s.monitor_from is not None else None}
    cur = m.current()
    eps = m.episodes()
    return {
        "session": s.id, "home": s.home, "started": True,
        "clock": _iso(m.clock) if m.clock is not None else None,
        "day": f"{m.day:%Y-%m-%d}",
        "current": None if cur is None else {
            "activity": cur["activity"], "confidence": round(cur["confidence"], 4),
            "at": _iso(cur["at"]), "episode": cur["episode"],
            "episodeSince": _iso(cur["episodeSince"])},
        "episodes": [{"activity": r.activity, "start": _iso(r.start), "end": _iso(r.end)}
                     for r in eps.itertuples()],
        "alerts": [alert_json(a, m.day) for a in m.alerts()],
        "closedDays": [{"day": f"{d.day:%Y-%m-%d}",
                        "alerts": [alert_json(a, d.day) for a in d.alerts]} for d in m.closed],
    }


def push_json(s: Session, result: dict) -> dict:
    m = s.monitor
    state = state_json(s)
    return {
        "predictions": [{"time": _iso(t), "activity": n, "confidence": round(c, 4)}
                        for t, n, c in result["predictions"]],
        "newAlerts": sorted({alert_id(a) for a in result["alerts"]}),
        "closed": [{"day": f"{d.day:%Y-%m-%d}", "alerts": [alert_json(a, d.day) for a in d.alerts]}
                   for d in result["closed"]],
        **{k: state[k] for k in ("clock", "day", "current", "alerts")},
        "session": s.id, "home": m.routine.home,
    }
