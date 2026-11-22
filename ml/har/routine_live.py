"""Save the resident's routine model and run it live on new sensor events (ROADMAP 4.3).

``har.replay`` (D17) fits the routine model on the observation days of the live
stream every time it exports, then replays fixed days. A live system needs that
model on disk, and a way to run it on whatever events have arrived so far. This
module provides both:

    python -m har.routine_live                  # fit + save both homes -> models/<home>/
    python -m har.routine_live --home milan --check

Fitting follows the E20 operating point exactly (as ``har.replay`` does): the saved
window BiLSTM recognises the observation days (the middle 20 % of days) every 10th
event; predictions become episodes with the home's live-stream rule (Aruba: runs
shorter than 3 minutes absorbed, ``winc``; Milan: 3-point rule, ``win``); the
routine model is fitted on them, and thresholds are set to 0.1 alerts per normal
day per aspect with leave-one-day-out calibration.

Running live (``LiveRoutine.run``) mirrors ``replay.live_alerts``: every 2 minutes
of the day so far, the routine model is re-run on only what had happened by then,
and each alert is reported from the first minute it appears. Routing follows D15
(``replay.route_live``). ``--check`` replays each home's real monitoring day from
the raw data and compares predictions and alerts with ``public/replay/``.
"""

from __future__ import annotations

import argparse
import json
import pickle
import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .anomaly import DAILY_KINDS, DayData, RoutineModel, budget_threshold, calibrate_routine
from .data import DATASETS, Home, load_home
from .run import RESULTS_DIR
from .run_anomaly import OPERATING, minutes_to_episodes, points_to_episodes
from .saved_model import MODELS_DIR, WindowModel
from .saved_model import load as load_window_model
from .saved_model import model_path
from .windows import day_split

FORMAT = 1
SIZE, STRIDE = 100, 10
STEP = pd.Timedelta(minutes=2)
WIN_SEED = 1
FOLDER = "anomaly-e20"
DEFAULT_STREAM = {"aruba": "winc", "milan": "win"}  # E20, as in har.replay


def routine_path(home: str) -> "Path":  # noqa: F821
    return MODELS_DIR / home / "routine.pkl"


def _sec(t, day) -> int:
    return int((pd.Timestamp(t) - day).total_seconds())


@dataclass
class LiveRoutine:
    """A fitted routine model plus everything needed to run it on new events."""

    home: str
    model: RoutineModel
    theta: dict[str, float]
    stream: str  # "win" (3-point rule) or "winc" (time-based cleanup)
    clean_minutes: float | None
    meta: dict = field(default_factory=dict)

    def episodes(self, times: np.ndarray, labels, end) -> pd.DataFrame:
        """Per-point predictions -> episodes, cut at ``end``."""
        if self.stream == "winc":
            return minutes_to_episodes(times, list(labels), end, self.clean_minutes)
        return points_to_episodes(times, list(labels), end)

    def run(self, day: pd.Timestamp, event_times: np.ndarray, pred_times: np.ndarray,
            pred_labels: np.ndarray, until: pd.Timestamp, step: pd.Timedelta = STEP) -> list[dict]:
        """Alerts raised on ``day`` up to ``until``, each from the first step it appears.

        ``event_times`` are the day's sensor events; ``pred_times`` / ``pred_labels``
        the live recogniser's answers during the day. Only data before each step is
        used at that step, so nothing depends on the future.
        """
        end = day + pd.Timedelta(days=1)
        until = min(pd.Timestamp(until), end)
        first: dict[tuple, dict] = {}
        g = day + step
        last = False
        while not last:
            if g >= until:
                g, last = until, True
            self.step(day, event_times, pred_times, pred_labels, g, first)
            g += step
        return sorted(first.values(), key=lambda r: r["raisedAt"])

    def step(self, day: pd.Timestamp, event_times: np.ndarray, pred_times: np.ndarray,
             pred_labels: np.ndarray, g: pd.Timestamp, first: dict) -> list[dict]:
        """Re-run the routine model at clock time ``g`` on data before ``g``.

        Alerts not raised before are added to ``first`` (keyed by kind, activity and
        minute) and returned.
        """
        end = day + pd.Timedelta(days=1)
        g64 = g.to_datetime64()
        ev = event_times[event_times < g64]
        # The clock is an observation too: a silence lasting until now is a silence.
        ev = np.append(ev, g64) if g < end else ev
        m = pred_times < g64
        eps = self.episodes(pred_times[m], pred_labels[m], g)
        new = []
        for a in self.model.alerts(DayData(0, day, ev, eps), self.theta):
            if a.time > g:
                continue
            key = (a.kind, a.activity, a.time.floor("min"))
            if key not in first:
                first[key] = {"raisedAt": _sec(g, day), "time": a.time, "kind": a.kind,
                              "activity": a.activity, **a.record}
                new.append(first[key])
        return new

    def usual_day(self) -> list[dict]:
        """Daily activities with the usual time they first happen (as in the replay)."""
        out = []
        for a, f in self.model.first.items():
            h = float(np.median(f[np.isfinite(f)]))
            out.append({"activity": a, "usualFirst": f"{int(h):02d}:{int(h % 1 * 60):02d}",
                        "pDay": round(self.model.p_day[a], 2)})
        return sorted(out, key=lambda r: r["usualFirst"])


# --------------------------------------------------------------------------- live monitor

def route(first: dict) -> list[dict]:
    """D15 routing of one day's alerts so far (``replay.route_live`` on copies).

    Summary items are only final at the 21:00 summary: a more important deviation
    raised before then can still take an earlier item's place.
    """
    from .replay import route_live
    return route_live(sorted((dict(a) for a in first.values()), key=lambda a: a["raisedAt"]))


def events_home(name: str, times: np.ndarray, sensors: np.ndarray, states: np.ndarray) -> Home:
    """A ``Home`` over raw events, without annotations (for the window model)."""
    seg = pd.DataFrame({"activity": pd.Series(dtype=object),
                        "start": pd.Series(dtype="datetime64[ns]"),
                        "end": pd.Series(dtype="datetime64[ns]"),
                        "lo": pd.Series(dtype=np.int64), "hi": pd.Series(dtype=np.int64)})
    return Home(name=name, times=times, sensors=sensors, states=states, segments=seg,
                sensor_list=sorted(set(sensors)))


@dataclass
class DayResult:
    day: pd.Timestamp
    alerts: list[dict]  # routed


class LiveMonitor:
    """The live pipeline over events as they arrive: recognition, routine, routing.

    Push sensor events in time order (``push``), optionally with the current clock
    time so that silences are noticed without new events. Recognition runs every
    ``STRIDE``-th event of each monitored day (windows of the last 100 events, which
    may reach into earlier days), and the routine model every 2 minutes of the clock.
    Days are monitored from ``monitor_from`` (a midnight); earlier events only fill
    the first recognition windows. The result is the same as re-running the whole
    day (``LiveRoutine.run``); ``tests/test_api.py`` checks it on a real day.
    """

    def __init__(self, wm: WindowModel, routine: LiveRoutine, monitor_from,
                 stride: int = STRIDE, step: pd.Timedelta = STEP, keep_days: int = 7):
        self.wm, self.routine, self.stride, self.step = wm, routine, stride, step
        self.t = np.array([], "datetime64[ns]")
        self.s = np.array([], object)
        self.v = np.array([], object)
        self.clock: pd.Timestamp | None = None
        self.keep_days = keep_days
        self.closed: list[DayResult] = []
        self._start_day(pd.Timestamp(monitor_from).normalize())

    def _start_day(self, day: pd.Timestamp) -> None:
        self.day = day
        self.k = 0  # window ends of this day handled so far
        self.pt: list = []
        self.pl: list = []
        self.pc: list = []
        self.first: dict[tuple, dict] = {}
        self.next_step = day + self.step

    def push(self, times, sensors, states, now=None) -> dict:
        """Add events (sorted here; none may be earlier than the clock) and advance.

        Returns the new predictions, the newly raised alerts and the days that ended.
        """
        times = np.asarray(pd.to_datetime(pd.Series(list(times))).to_numpy(), "datetime64[ns]")
        order = np.argsort(times, kind="stable")
        times = times[order]
        if self.clock is not None and len(times) and times[0] < self.clock.to_datetime64():
            raise ValueError(f"event at {pd.Timestamp(times[0])} is earlier than the clock "
                             f"({self.clock}); push events in time order")
        self.t = np.concatenate([self.t, times])
        self.s = np.concatenate([self.s, np.asarray(list(sensors), dtype=object)[order]])
        self.v = np.concatenate([self.v, np.asarray(list(states), dtype=object)[order]])
        clock = [pd.Timestamp(times[-1])] if len(times) else []
        if now is not None:
            clock.append(pd.Timestamp(now))
        if self.clock is not None:
            clock.append(self.clock)
        if clock:
            self.clock = max(clock)
        return self._advance()

    def _advance(self) -> dict:
        new_preds, new_alerts, closed = [], [], []
        while True:
            day, end = self.day, self.day + pd.Timedelta(days=1)
            lo, hi = (int(i) for i in np.searchsorted(self.t, [day.to_datetime64(),
                                                               end.to_datetime64()]))
            ends = np.arange(lo + 1 + self.stride * self.k, hi + 1, self.stride)
            self.k += len(ends)
            ends = ends[ends >= self.wm.size]
            if len(ends):
                h = events_home(self.routine.home, self.t, self.s, self.v)
                names, conf = self.wm.predict(h, ends)
                for e, n, c in zip(ends, names, conf):
                    self.pt.append(self.t[e - 1])
                    self.pl.append(n)
                    self.pc.append(float(c))
                    new_preds.append((pd.Timestamp(self.t[e - 1]), n, float(c)))
            if self.clock is None:
                break
            pt = np.asarray(self.pt, "datetime64[ns]")
            pl = np.asarray(self.pl, dtype=object)
            ev = self.t[lo:hi]
            while self.next_step <= min(self.clock, end):
                new_alerts += self.routine.step(day, ev, pt, pl, self.next_step, self.first)
                self.next_step += self.step
            if self.clock < end:
                break
            # The day is over: close it and start the next one.
            closed.append(DayResult(day, route(self.first)))
            self.closed = (self.closed + closed[-1:])[-self.keep_days:]
            keep = max(0, hi - self.wm.size)  # enough history for the next day's windows
            self.t, self.s, self.v = self.t[keep:], self.s[keep:], self.v[keep:]
            self._start_day(end)
        return {"predictions": new_preds, "alerts": new_alerts, "closed": closed}

    # ---- current state
    def alerts(self) -> list[dict]:
        return route(self.first)

    def episodes(self) -> pd.DataFrame:
        end = self.day if self.clock is None else min(self.clock, self.day + pd.Timedelta(days=1))
        return self.routine.episodes(np.asarray(self.pt, "datetime64[ns]"),
                                     np.asarray(self.pl, dtype=object), end)

    def current(self) -> dict | None:
        """Latest recognised activity and the episode it belongs to."""
        if not self.pt:
            return None
        eps = self.episodes()
        last = eps.iloc[-1] if len(eps) else None
        return {"activity": self.pl[-1], "confidence": self.pc[-1],
                "at": pd.Timestamp(self.pt[-1]),
                "episode": last["activity"] if last is not None else self.pl[-1],
                "episodeSince": pd.Timestamp(last["start"]) if last is not None
                else pd.Timestamp(self.pt[-1])}


# --------------------------------------------------------------------------- fit

def recognise_points(wm: WindowModel, home: Home, lo: int, hi: int,
                     stride: int = STRIDE) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Live predictions at every ``stride``-th event of [lo, hi): windows end at lo+1,
    lo+1+stride, … (as in the evaluation), skipping ends without a full window."""
    ends = np.arange(lo + 1, hi + 1, stride)
    ends = ends[ends >= wm.size]
    if not len(ends):
        return np.array([], "datetime64[ns]"), np.array([], object), np.array([], float)
    names, conf = wm.predict(home, ends)
    return home.times[ends - 1], np.asarray(names, dtype=object), np.asarray(conf)


def fit(home_name: str, stream: str | None = None) -> LiveRoutine:
    t0 = time.time()
    stream = stream or DEFAULT_STREAM[home_name]
    summary = json.loads((RESULTS_DIR / home_name / FOLDER / "summary.json").read_text())
    minutes = float(summary["win_clean"]["minutes"]) if stream == "winc" else None
    home = load_home(home_name)
    train_end, test_start, train_cut, test_cut = day_split(home, 0.6, 0.2)
    wm = load_window_model(model_path(home_name, "bilstm", WIN_SEED, SIZE))

    # Observation days: days of annotated activities in [train_cut, test_cut), as in
    # run_anomaly.build_streams.
    seg = home.segments
    obs = seg[(seg["start"] >= train_cut) & (seg["start"] < test_cut)]
    obs_days = sorted(obs["start"].dt.normalize().unique())
    pt, lab, _ = recognise_points(wm, home, train_end, test_start)

    live = LiveRoutine(home_name, RoutineModel(), {}, stream, minutes)
    ref = []
    for i, day in enumerate(obs_days):
        day = pd.Timestamp(day)
        nxt = day + pd.Timedelta(days=1)
        lo, hi = np.searchsorted(home.times, [np.datetime64(day), np.datetime64(nxt)])
        m = (pt >= np.datetime64(day)) & (pt < np.datetime64(nxt))
        ref.append(DayData(-1 - i, day, home.times[lo:hi], live.episodes(pt[m], lab[m], nxt)))

    live.model = RoutineModel().fit(ref)
    pool = calibrate_routine(ref)
    live.theta = {k: budget_threshold(pool[k], len(ref), OPERATING) for k in DAILY_KINDS}
    live.meta = {
        "format": FORMAT, "home": home_name, "stream": stream, "clean_minutes": minutes,
        "recogniser": str(model_path(home_name, "bilstm", WIN_SEED, SIZE).name),
        "stride": STRIDE, "operating_alerts_per_day": OPERATING,
        "observation_days": len(ref), "observed_from": str(obs_days[0].date()),
        "observed_until": str(obs_days[-1].date()),
        "expected_observation_days": summary.get("n_observation_days"),
        "fit_seconds": round(time.time() - t0, 1),
    }
    return live


def save(live: LiveRoutine) -> "Path":  # noqa: F821
    path = routine_path(live.home)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump({"meta": live.meta, "model": live.model, "theta": live.theta,
                     "stream": live.stream, "clean_minutes": live.clean_minutes}, f)
    path.with_suffix(".json").write_text(json.dumps(
        live.meta | {"theta": {k: (None if not np.isfinite(v) else round(float(v), 4))
                               for k, v in live.theta.items()},
                     "usual_day": live.usual_day()}, indent=2))
    return path


def load(home: str) -> LiveRoutine:
    with open(routine_path(home), "rb") as f:
        ck = pickle.load(f)
    if ck["meta"].get("format") != FORMAT:
        raise ValueError(f"{routine_path(home)}: unknown routine file format")
    return LiveRoutine(home, ck["model"], ck["theta"], ck["stream"], ck["clean_minutes"],
                       ck["meta"])


# --------------------------------------------------------------------------- check

def check(home_name: str, live: LiveRoutine) -> dict:
    """Replay the home's real monitoring day from raw data; compare with public/replay/."""
    from .replay import OUT_DIR, route_live

    sc = json.loads((OUT_DIR / f"{home_name}-normal.json").read_text())
    day = pd.Timestamp(sc["day"]).normalize()
    home = load_home(home_name)
    wm = load_window_model(model_path(home_name, "bilstm", WIN_SEED, SIZE))
    nxt = day + pd.Timedelta(days=1)
    lo, hi = np.searchsorted(home.times, [np.datetime64(day), np.datetime64(nxt)])
    pt, lab, _ = recognise_points(wm, home, int(lo), int(hi))

    labels = sc["labels"]
    ref_pred = [(t, labels[a]) for t, a, _ in sc["predictions"]]
    ours = [(_sec(t, day), l) for t, l in zip(pt, lab)]
    same_pred = float(np.mean([a == b for a, b in zip(ours, ref_pred)])) if ours else 0.0

    t0 = time.time()
    alerts = route_live(live.run(day, home.times[lo:hi], pt, lab, nxt))
    secs = time.time() - t0
    key = lambda a: (a["raisedAt"], a["kind"], a["activity"], a["tier"], a["delivered"])  # noqa: E731
    ref_alerts = sorted(key(a) for a in sc["alerts"])
    our_alerts = sorted(key(a) for a in alerts)
    res = {"day": str(day.date()), "predictions": len(ours), "reference_predictions": len(ref_pred),
           "predictions_identical": same_pred, "alerts": len(our_alerts),
           "reference_alerts": len(ref_alerts), "alerts_identical": our_alerts == ref_alerts,
           "run_seconds": round(secs, 1)}
    print(f"  [{home_name}] check on {res['day']}: predictions {len(ours)} vs {len(ref_pred)} "
          f"({same_pred:.1%} identical); alerts {len(our_alerts)} vs {len(ref_alerts)} "
          f"({'identical' if res['alerts_identical'] else 'DIFFERENT'}); "
          f"whole day re-run every 2 min in {secs:.1f}s")
    if not res["alerts_identical"]:
        print("    ours:     ", our_alerts)
        print("    reference:", ref_alerts)
    return res


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--home", default="all", choices=[*DATASETS, "all"])
    p.add_argument("--stream", default=None, choices=["win", "winc"],
                   help="live stream rule (default per home, see DEFAULT_STREAM)")
    p.add_argument("--check", action="store_true",
                   help="after saving, compare a replayed real day with public/replay/")
    p.add_argument("--check-only", action="store_true", help="load the saved model and check")
    args = p.parse_args(argv)
    for h in (list(DATASETS) if args.home == "all" else [args.home]):
        if args.check_only:
            live = load(h)
        else:
            live = fit(h, args.stream)
            path = save(live)
            m = live.meta
            print(f"  [{h}] routine ({m['stream']}) fitted on {m['observation_days']} observation "
                  f"days ({m['observed_from']} – {m['observed_until']}; evaluation used "
                  f"{m['expected_observation_days']}) in {m['fit_seconds']:.0f}s -> {path}")
        if args.check or args.check_only:
            check(h, live)


if __name__ == "__main__":
    main()
