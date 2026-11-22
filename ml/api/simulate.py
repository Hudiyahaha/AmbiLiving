"""Simulated live homes: recorded feeds played into live sessions (decisions D19, D20).

A simulation plays a recorded feed (``har.feeds``: one day, or a week of consecutive
days) into a live monitoring session (D18) at ``speed`` times real time. Every
``TICK`` seconds it pushes the events whose time has come, together with the
simulated clock, so the BiLSTM, the routine model and alert routing run exactly as
they would on a real sensor feed. Clients follow it over server-sent events: a full
``snapshot`` first, then ``tick`` messages with only what changed.

Everything a client is sent is about the day the session monitors now (times are
seconds of that day). When the clock passes midnight the session closes the day
(its last routine check and the final routing) and a new ``snapshot`` starts the
next day. Closed days stay available as day reports (``closed_day``).
"""

from __future__ import annotations

import asyncio
import json
import secrets
import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from starlette.concurrency import run_in_threadpool

from har.anomaly import BINS
from har.feeds import WEEK_ID, decode, feed_days, feed_path
from har.feeds import load as load_feed
from har.replay import STATE, STATE_NAMES, SUMMARY_AT
from har.routine_live import DayResult

from . import live, sessions
from .store import NotFound, check_home, replay_index

TICK = 0.5  # seconds of real time between pushes
MAX_SIMULATIONS = 8
IDLE_SECONDS = 1800  # drop simulations nobody watched for this long
QUEUE = 256  # messages a slow client may fall behind before it is dropped
DAY = 86400.0


def scenarios(home: str) -> list[dict]:
    """Recorded feeds that can be played: the week first, then the single days."""
    entry = replay_index().get(check_home(home), {})
    out = [{"id": s["id"], "title": s["title"], "day": s["day"], "kind": s["kind"], "days": 1}
           for s in entry.get("scenarios", []) if feed_path(home, s["id"]).is_file()]
    if feed_path(home, WEEK_ID).is_file():
        f = load_feed(home, WEEK_ID)
        out.insert(0, {"id": WEEK_ID, "title": f["title"], "day": f["dayLabel"],
                       "kind": f["kind"], "days": len(feed_days(f))})
    return out


# --------------------------------------------------------------------------- views

def _sec(t, day: pd.Timestamp) -> float:
    return round((pd.Timestamp(t) - day).total_seconds(), 3)


def episodes_view(d: DayResult) -> list[dict]:
    """Episodes with mean recognition confidence and the sensors that fired in them."""
    if d.episodes is None or not len(d.episodes):
        return []
    out = []
    pt, pc = d.pred_times, d.pred_conf
    for r in d.episodes.itertuples():
        s64, e64 = pd.Timestamp(r.start).to_datetime64(), pd.Timestamp(r.end).to_datetime64()
        m = (pt >= s64) & (pt < e64)
        lo, hi = np.searchsorted(d.times, [s64, e64])
        sens, counts = np.unique(d.sensors[lo:hi], return_counts=True)
        top = [str(x) for x in sens[np.argsort(-counts, kind="stable")][:8]]
        out.append({"activity": r.activity, "start": _sec(r.start, d.day),
                    "end": _sec(r.end, d.day),
                    "confidence": round(float(pc[m].mean()), 3) if m.any() else None,
                    "predictions": int(m.sum()), "sensors": top})
    return out


def alerts_view(d: DayResult) -> list[dict]:
    return [{**{k: v for k, v in a.items() if k not in ("raisedAt", "time")},
             "id": sessions.alert_id(a), "raisedAt": a["raisedAt"], "time": _sec(a["time"], d.day)}
            for a in d.alerts]


def current_view(d: DayResult) -> dict | None:
    if not len(d.pred_times):
        return None
    eps = d.episodes
    last = eps.iloc[-1] if eps is not None and len(eps) else None
    return {"activity": d.pred_labels[-1], "confidence": round(float(d.pred_conf[-1]), 3),
            "at": _sec(d.pred_times[-1], d.day),
            "episode": last["activity"] if last is not None else d.pred_labels[-1],
            "episodeSince": _sec(last["start"], d.day) if last is not None else None}


def day_report(home: str, d: DayResult) -> dict:
    """A closed day in the shape of a replay scenario (``public/replay``), for Past days."""
    model = sessions.get_routine(home).model
    usual = [model._expected_states([b]) for b in range(BINS)]
    daily = sessions.get_routine(home).usual_day()
    eps = d.episodes if d.episodes is not None else pd.DataFrame(
        {"activity": [], "start": [], "end": []})
    names = (list(live.get_model(home).classes) + list(d.pred_labels) + list(eps["activity"])
             + [a for u in usual for a in u] + [x["activity"] for x in daily])
    labels = list(dict.fromkeys(names))
    li = {n: i for i, n in enumerate(labels)}
    sens = sorted(set(d.sensors))
    si = {x: i for i, x in enumerate(sens)}
    return {
        "home": home, "id": f"live-{d.day:%Y-%m-%d}", "title": f"{d.day:%a %d %b %Y}",
        "kind": "live", "day": f"{d.day:%a %d %b %Y}", "date": f"{d.day:%Y-%m-%d}",
        "injected": None, "typical": None,
        "sensors": sens, "states": STATE_NAMES, "labels": labels,
        "events": [[_sec(t, d.day), si[x], STATE[v]]
                   for t, x, v in zip(d.times, d.sensors, d.states) if v in STATE],
        "predictions": [[_sec(t, d.day), li[n], round(float(c), 2)]
                        for t, n, c in zip(d.pred_times, d.pred_labels, d.pred_conf)],
        "episodes": [[_sec(e.start, d.day), min(_sec(e.end, d.day), DAY), li[e.activity]]
                     for e in eps.itertuples()],
        "annotations": [], "usual": usual, "daily": daily, "summaryAt": SUMMARY_AT,
        "alerts": [{k: v for k, v in a.items() if k != "severity"} for a in alerts_view(d)],
    }


# --------------------------------------------------------------------------- simulation

@dataclass
class Simulation:
    id: str
    home: str
    scenario: str
    feed: dict
    times: np.ndarray
    sensors: np.ndarray
    states: np.ndarray
    session: sessions.Session
    speed: float
    start_at: int  # second of the first day the simulation starts at
    status: str = "starting"  # starting | running | paused | finished | error
    error: str | None = None
    pos: int = 0  # next feed event to push
    sim_anchor: float = 0.0  # simulated seconds since the first midnight at wall_anchor
    wall_anchor: float = 0.0
    sent_events: int = 0  # events of the shown day already sent to clients
    sent_preds: int = 0
    shown_day: pd.Timestamp | None = None  # the day clients were last sent
    subscribers: set = field(default_factory=set)
    task: asyncio.Task | None = None
    used: float = field(default_factory=time.time)

    @property
    def first(self) -> pd.Timestamp:
        return pd.Timestamp(self.feed["day"])

    @property
    def days(self) -> list[dict]:
        return feed_days(self.feed)

    @property
    def end(self) -> pd.Timestamp:
        return self.first + pd.Timedelta(days=len(self.days))

    def clock(self) -> float:
        """Simulated seconds since the feed's first midnight."""
        top = DAY * len(self.days)
        if self.status != "running":
            return min(top, self.sim_anchor)
        return min(top, self.sim_anchor + (time.monotonic() - self.wall_anchor) * self.speed)

    def day_clock(self, day: pd.Timestamp) -> float:
        """Simulated second of ``day`` now (86400 once it is over)."""
        return max(0.0, min(DAY, self.clock() - (day - self.first).total_seconds()))

    def _reanchor(self) -> None:
        self.sim_anchor = self.clock()
        self.wall_anchor = time.monotonic()

    def set_speed(self, speed: float) -> None:
        self._reanchor()
        self.speed = speed

    def pause(self) -> None:
        if self.status == "running":
            self._reanchor()
            self.status = "paused"

    def resume(self) -> None:
        if self.status == "paused":
            self.wall_anchor = time.monotonic()
            self.status = "running"

    # ---- what clients see
    def day_result(self) -> DayResult:
        """The day being monitored now (the last day once the feed is over)."""
        m = self.session.monitor
        if m is None:
            return DayResult(self.first, [])
        if m.day >= self.end:  # every day of the feed has ended
            return m.closed[-1] if m.closed else DayResult(self.first, [])
        return m.today()

    def closed_days(self) -> list[DayResult]:
        m = self.session.monitor
        return [d for d in m.closed if self.first <= d.day < self.end] if m else []

    def day_label(self, day: pd.Timestamp) -> str:
        key = f"{day:%Y-%m-%d}"
        return next((d["dayLabel"] for d in self.days if d["day"] == key), f"{day:%a %d %b %Y}")

    def meta(self, d: DayResult | None = None) -> dict:
        f = self.feed
        r = sessions.get_routine(self.home)
        if d is None:
            with self.session.lock:
                d = self.day_result()
                closed = self.closed_days()
        else:
            closed = self.closed_days()
        single = len(self.days) == 1
        return {"simulation": self.id, "session": self.session.id, "home": self.home,
                "scenario": self.scenario, "title": f["title"], "kind": f["kind"],
                "day": f"{d.day:%Y-%m-%d}", "dayLabel": self.day_label(d.day),
                "dayIndex": (d.day - self.first).days, "days": len(self.days),
                "feedLabel": f["dayLabel"],
                "injected": f["injected"] if single else None,
                "typical": f["typical"] if single else None,
                "closedDays": [{"day": f"{c.day:%Y-%m-%d}", "dayLabel": self.day_label(c.day)}
                               for c in closed],
                "status": self.status, "error": self.error,
                "speed": self.speed, "startAt": self.start_at,
                "clock": round(self.day_clock(d.day), 1),
                "recogniser": "BiLSTM on the last 100 sensor events, every 10th event",
                "episodeRule": (f"runs shorter than {r.clean_minutes:g} min merged"
                                if r.stream == "winc" else "runs shorter than 3 predictions merged"),
                "routineLearnedFrom": f"{r.meta['observation_days']} observation days "
                                      f"({r.meta['observed_from']} – {r.meta['observed_until']})"}

    def snapshot(self) -> dict:
        """Everything so far on the current day (for a client that connects or reconnects,
        and for everyone when a new day starts)."""
        with self.session.lock:
            d = self.day_result()
            return {"type": "snapshot", **self.meta(d),
                    "events": [[_sec(t, d.day), s, v]
                               for t, s, v in zip(d.times, d.sensors, d.states)],
                    "predictions": [[_sec(t, d.day), n, round(float(c), 3)]
                                    for t, n, c in zip(d.pred_times, d.pred_labels, d.pred_conf)],
                    "episodes": episodes_view(d), "alerts": alerts_view(d),
                    "current": current_view(d)}

    def tick_message(self, new_alerts: list[str]) -> dict:
        """What changed since the last tick. ``eventsFrom`` / ``predictionsFrom`` give the
        index of the first item sent, so a client splices them in at that index (a client
        that joined between ticks may already have some of them)."""
        with self.session.lock:
            d = self.day_result()
            ev = slice(min(self.sent_events, len(d.times)), len(d.times))
            pr = slice(min(self.sent_preds, len(d.pred_times)), len(d.pred_times))
            self.sent_events, self.sent_preds = len(d.times), len(d.pred_times)
            return {"type": "tick", "status": self.status, "error": self.error,
                    "speed": self.speed, "clock": round(self.day_clock(d.day), 1),
                    "day": f"{d.day:%Y-%m-%d}",
                    "eventsFrom": ev.start, "predictionsFrom": pr.start,
                    "events": [[_sec(t, d.day), s, v] for t, s, v in
                               zip(d.times[ev], d.sensors[ev], d.states[ev])],
                    "predictions": [[_sec(t, d.day), n, round(float(c), 3)] for t, n, c in
                                    zip(d.pred_times[pr], d.pred_labels[pr], d.pred_conf[pr])],
                    "episodes": episodes_view(d), "alerts": alerts_view(d),
                    "newAlerts": new_alerts, "current": current_view(d)}

    def broadcast(self, msg: dict) -> None:
        text = json.dumps(msg, separators=(",", ":"), default=str)
        for q in list(self.subscribers):
            try:
                q.put_nowait((msg["type"], text))
            except asyncio.QueueFull:  # too slow: disconnect it; the browser reconnects
                self.subscribers.discard(q)
                while not q.empty():
                    q.get_nowait()
                q.put_nowait(None)

    # ---- the loop
    def _current_day(self) -> pd.Timestamp:
        with self.session.lock:
            return self.day_result().day

    async def _send_snapshot(self) -> None:
        snap = await run_in_threadpool(self.snapshot)
        self.sent_events, self.sent_preds = len(snap["events"]), len(snap["predictions"])
        self.shown_day = pd.Timestamp(snap["day"])
        self.broadcast(snap)

    async def run(self) -> None:
        first, end = self.first, self.end
        try:
            # History and the part of the first day before start_at, in one catch-up push.
            await self._push_until(first + pd.Timedelta(seconds=self.start_at))
            self.sim_anchor, self.wall_anchor = float(self.start_at), time.monotonic()
            self.status = "running"
            await self._send_snapshot()
            while True:
                if self.status == "paused":
                    await asyncio.sleep(TICK)
                    continue
                now = first + pd.Timedelta(seconds=self.clock())
                new = await self._push_until(now)
                if now >= end:
                    self.status, self.sim_anchor = "finished", DAY * len(self.days)
                if self._current_day() != self.shown_day:
                    await self._send_snapshot()  # past midnight: the next day starts
                else:
                    self.broadcast(await run_in_threadpool(self.tick_message, new))
                if self.status == "finished":
                    return
                await asyncio.sleep(TICK)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # report it to clients instead of dying silently
            self.status, self.error = "error", f"{type(exc).__name__}: {exc}"
            self.broadcast({"type": "tick", "status": self.status, "error": self.error,
                            "clock": round(self.clock() % DAY, 1)})

    async def _push_until(self, now: pd.Timestamp) -> list[str]:
        hi = int(np.searchsorted(self.times, now.to_datetime64(), side="right"))
        sl = slice(self.pos, hi)
        result = await run_in_threadpool(self.session.push, self.times[sl], self.sensors[sl],
                                         self.states[sl], now)
        self.pos = hi
        return sorted({sessions.alert_id(a) for a in result["alerts"]})


_sims: dict[str, Simulation] = {}


def _expire() -> None:
    cutoff = time.time() - IDLE_SECONDS
    for sid, s in list(_sims.items()):
        if not s.subscribers and s.used < cutoff:
            stop(sid)


async def create(home: str, scenario: str, speed: float, start_at: int) -> Simulation:
    check_home(home)
    if not feed_path(home, scenario).is_file():
        ids = ", ".join(s["id"] for s in scenarios(home)) or "none"
        raise NotFound(f"no recorded feed '{scenario}' for {home}; available: {ids}")
    _expire()
    if len(_sims) >= MAX_SIMULATIONS:
        stop(min(_sims.values(), key=lambda s: s.used).id)
    feed = load_feed(home, scenario)
    times, sensors, states = decode(feed)
    session = sessions.create(home, feed["day"], keep_days=max(7, len(feed_days(feed))))
    sim = Simulation(secrets.token_hex(8), home, scenario, feed, times, sensors, states,
                     session, speed, start_at, sim_anchor=float(start_at))
    _sims[sim.id] = sim
    sim.task = asyncio.get_running_loop().create_task(sim.run())
    return sim


def get(sim_id: str) -> Simulation:
    s = _sims.get(sim_id)
    if s is None:
        raise NotFound(f"no simulation '{sim_id}' (idle simulations are dropped after "
                       f"{IDLE_SECONDS // 60} minutes)")
    s.used = time.time()
    return s


def closed_day(sim_id: str, day: str) -> dict:
    """A day the simulation's session has closed, as a day report."""
    sim = get(sim_id)
    with sim.session.lock:
        done = [d for d in sim.closed_days() if f"{d.day:%Y-%m-%d}" == day]
        have = ", ".join(f"{d.day:%Y-%m-%d}" for d in sim.closed_days()) or "none yet"
    if not done:
        raise NotFound(f"day {day} has not ended in simulation '{sim_id}' (ended: {have})")
    return day_report(sim.home, done[-1])


def stop(sim_id: str) -> None:
    s = _sims.pop(sim_id, None)
    if s is None:
        raise NotFound(f"no simulation '{sim_id}'")
    if s.task:
        s.task.cancel()
    for q in list(s.subscribers):
        q.put_nowait(None)
    try:
        sessions.delete(s.session.id)
    except NotFound:
        pass


async def events(sim: Simulation):
    """Server-sent events for one client: a snapshot, then ticks until it finishes."""
    q: asyncio.Queue = asyncio.Queue(QUEUE)
    sim.subscribers.add(q)
    try:
        if sim.status != "starting":
            snap = await run_in_threadpool(sim.snapshot)
            yield _sse("snapshot", json.dumps(snap, separators=(",", ":"), default=str))
            if snap["status"] in ("finished", "error"):
                return  # nothing more will happen
        else:
            meta = await run_in_threadpool(sim.meta)
            yield _sse("status", json.dumps({"type": "status", **meta}, default=str))
        while True:
            try:
                item = await asyncio.wait_for(q.get(), timeout=15)
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
                continue
            if item is None:
                return
            kind, text = item
            yield _sse(kind, text)
            sim.used = time.time()
            if kind in ("tick", "snapshot") and sim.status in ("finished", "error"):
                return
    finally:
        sim.subscribers.discard(q)


def _sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"
