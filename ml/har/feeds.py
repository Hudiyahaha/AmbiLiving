"""Recorded sensor feeds for the live dashboard (decision D19).

    python -m har.feeds                  # -> feeds/<home>-<scenario>.json, then check them
    python -m har.feeds --check-only

There are no real sensors in this project, so the live dashboard is driven by
recorded days played back as if they were happening now. A *feed* is one day of
raw sensor events with full timestamps (plus 150 events from the evening before,
so the first recognition windows of the day are full), for each scenario of the
live demo (``har.replay``): the real monitoring day, and one day per injected
deviation type. Injected days are rebuilt with the same injection code, seed and
settings as the evaluation (``run_anomaly``: 3 copies per type and day, seed 0)
and matched to the scenario by day, type, target and start.

A *week* feed (``<home>-week.json``, decision D20) is seven consecutive real days
of the test period, with a scenario's injected copy in place of the real day on
that scenario's date (``WEEK``). It lets the dashboard run on past midnight: at
24:00 the live session closes the day and starts the next, as a real deployment
would. Every injected day follows a real day, so its first recognition windows
(which reach into the evening before) are the same as in its single-day feed.

The backend plays a feed into a live session (``LiveMonitor``) event by event, so
recognition, the routine model and routing run live. ``--check`` replays every
feed through ``LiveMonitor`` in one push and requires the same predictions and
alerts as the scenario in ``public/replay/`` — for a week feed, on every day that
has a scenario (its injected days and the home's real ``normal`` day), and all
seven days must close.

Feed format (compact JSON): ``day`` (first midnight), ``sensors``, ``states`` (CASAS
states), and ``events`` as ``[microseconds since that midnight, sensor index,
state index]`` — negative offsets are the prefix from the previous day. Week feeds
add ``days``: one entry per day (``day``, ``dayLabel``, ``scenario`` or null).
"""

from __future__ import annotations

import argparse
import json
import time

import numpy as np
import pandas as pd

from .anomaly_inject import make_variants
from .data import DATASETS, ML_DIR, load_home
from .replay import OUT_DIR as REPLAY_DIR
from .windows import day_split

FEEDS_DIR = ML_DIR / "feeds"
PREFIX = 150
PER_DAY, SEED = 3, 0  # run_anomaly defaults used for E14 / E20
STATES = ["ON", "OFF", "OPEN", "CLOSE"]
WEEK_ID = "week"
WEEK_DAYS = 7
# First day of each home's week, and the scenario played on a date (else the real day).
WEEK = {
    "aruba": ("2011-05-05", {"2011-05-07": "inactivity", "2011-05-11": "missed-meal"}),
    "milan": ("2009-12-25", {"2009-12-25": "inactivity", "2009-12-30": "night"}),
}


def feed_path(home: str, scenario: str):
    return FEEDS_DIR / f"{home}-{scenario}.json"


def _sec(t, day) -> int:
    return int((pd.Timestamp(t) - day).total_seconds())


def _pack(home_name: str, day: pd.Timestamp, times, sensors, states, prefix: int,
          **info) -> dict:
    keep = np.isin(states, STATES)
    times, sensors, states = times[keep], sensors[keep], states[keep]
    sens = sorted(set(sensors))
    sidx = {s: i for i, s in enumerate(sens)}
    st = {s: i for i, s in enumerate(STATES)}
    us = ((times - day.to_datetime64()) // np.timedelta64(1, "us")).astype(np.int64)
    head = {k: info.pop(k) for k in ("id", "title", "kind")}
    return {"home": home_name, **head, "day": f"{day:%Y-%m-%d}", **info, "prefixEvents": prefix,
            "sensors": sens, "states": STATES,
            "events": [[int(u), sidx[s], st[x]] for u, s, x in zip(us, sensors, states)]}


def build(home_name: str) -> list[dict]:
    """The single-day feed of every replay scenario, then the week feed."""
    index = json.loads((REPLAY_DIR / "index.json").read_text())[home_name]
    home = load_home(home_name)
    _, test_start, train_cut, _ = day_split(home, 0.6, 0.2)
    days = sorted(pd.to_datetime(home.times[test_start:]).normalize().unique())
    t0 = time.time()
    variants = make_variants(home, days, train_cut, PER_DAY, SEED)
    print(f"  [{home_name}] {len(variants)} day copies rebuilt in {time.time() - t0:.0f}s")

    feeds, chosen = [], {}
    for ref in index["scenarios"]:
        sc = json.loads((REPLAY_DIR / ref["file"]).read_text())
        day = pd.Timestamp(sc["day"]).normalize()
        cands = [v for v in variants if v.day == day and v.kind == sc["kind"]]
        if sc["injected"]:
            inj = sc["injected"]
            cands = [v for v in cands if v.target == inj["target"]
                     and _sec(v.a_start, v.day) == inj["start"] and v.note == inj["note"]]
        if len(cands) != 1:
            raise SystemExit(f"{home_name}/{sc['id']}: {len(cands)} matching day copies")
        v = chosen[sc["id"]] = cands[0]
        p_hi = int(np.searchsorted(home.times, day.to_datetime64()))
        p_lo = max(0, p_hi - PREFIX)
        feeds.append(_pack(
            home_name, day,
            np.concatenate([home.times[p_lo:p_hi], v.times]),
            np.concatenate([home.sensors[p_lo:p_hi], v.sensors]),
            np.concatenate([home.states[p_lo:p_hi], v.states]), int(p_hi - p_lo),
            id=sc["id"], title=sc["title"], kind=sc["kind"], dayLabel=sc["day"],
            injected=sc["injected"], typical=sc["typical"]))
    feeds.append(build_week(home_name, home, chosen))
    return feeds


def build_week(home_name: str, home, chosen: dict) -> dict:
    """Seven consecutive days from ``WEEK``, injected copies on their scenario dates."""
    first, swaps = WEEK[home_name]
    first = pd.Timestamp(first)
    week = [first + pd.Timedelta(days=i) for i in range(WEEK_DAYS)]
    p_hi = int(np.searchsorted(home.times, first.to_datetime64()))
    p_lo = max(0, p_hi - PREFIX)
    parts = [(home.times[p_lo:p_hi], home.sensors[p_lo:p_hi], home.states[p_lo:p_hi])]
    days = []
    for i, day in enumerate(week):
        sid = swaps.get(f"{day:%Y-%m-%d}")
        if sid:
            v = chosen[sid]
            if v.day != day:
                raise SystemExit(f"{home_name}: scenario {sid} is on {v.day:%Y-%m-%d}, not {day}")
            if i and swaps.get(f"{week[i - 1]:%Y-%m-%d}"):
                raise SystemExit(f"{home_name}: {sid} must follow a real day")
            parts.append((v.times, v.sensors, v.states))
        else:
            lo, hi = np.searchsorted(home.times, [day.to_datetime64(),
                                                  (day + pd.Timedelta(days=1)).to_datetime64()])
            if hi == lo:
                raise SystemExit(f"{home_name}: no events on {day:%Y-%m-%d}")
            parts.append((home.times[lo:hi], home.sensors[lo:hi], home.states[lo:hi]))
        days.append({"day": f"{day:%Y-%m-%d}", "dayLabel": f"{day:%a %d %b %Y}", "scenario": sid})
    times, sensors, states = (np.concatenate(x) for x in zip(*parts))
    return _pack(home_name, first, times, sensors, states, int(p_hi - p_lo),
                 id=WEEK_ID, title="A week at home", kind="week",
                 dayLabel=f"{first:%a %d %b} – {week[-1]:%a %d %b %Y}",
                 injected=None, typical=None, days=days)


def load(home: str, scenario: str) -> dict:
    return json.loads(feed_path(home, scenario).read_text())


def decode(feed: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Absolute times (datetime64[ns]), sensors and states of a feed."""
    day = np.datetime64(feed["day"], "ns")
    ev = np.asarray(feed["events"], dtype=np.int64).reshape(-1, 3)
    times = day + ev[:, 0].astype("timedelta64[us]")
    sensors = np.asarray(feed["sensors"], dtype=object)[ev[:, 1]]
    states = np.asarray(feed["states"], dtype=object)[ev[:, 2]]
    return times, sensors, states


def feed_days(feed: dict) -> list[dict]:
    """The days a feed covers (one for a single-day feed)."""
    return feed.get("days") or [{"day": feed["day"], "dayLabel": feed["dayLabel"],
                                 "scenario": feed["id"]}]


def _key(a: dict) -> tuple:
    return (a["raisedAt"], a["kind"], a["activity"], a["tier"], a["delivered"])


def check(feed: dict) -> bool:
    """Play the whole feed into a LiveMonitor; compare each day with its replay scenario."""
    from .routine_live import LiveMonitor
    from .routine_live import load as load_routine
    from .saved_model import load as load_wm
    from .saved_model import model_path

    h = feed["home"]
    first = pd.Timestamp(feed["day"])
    days = feed_days(feed)
    times, sensors, states = decode(feed)
    mon = LiveMonitor(load_wm(model_path(h, "bilstm", 1)), load_routine(h), first,
                      keep_days=len(days))
    t0 = time.time()
    r = mon.push(times, sensors, states, now=first + pd.Timedelta(days=len(days)))
    secs = time.time() - t0
    closed = {f"{d.day:%Y-%m-%d}": d for d in r["closed"]}
    ok = len(closed) == len(days)
    normal_day = pd.Timestamp(json.loads((REPLAY_DIR / f"{h}-normal.json").read_text())["day"])
    for d in days:
        sid = d["scenario"] or ("normal" if normal_day.normalize() == pd.Timestamp(d["day"])
                                else None)
        res = closed.get(d["day"])
        if res is None:
            print(f"  [{h}] {feed['id']:<13} {d['day']} NOT CLOSED")
            ok = False
            continue
        if sid is None:
            print(f"  [{h}] {feed['id']:<13} {d['day']} real day: {len(res.pred_times)} "
                  f"predictions, {len(res.alerts)} alerts")
            continue
        sc = json.loads((REPLAY_DIR / f"{h}-{sid}.json").read_text())
        day = pd.Timestamp(d["day"])
        labels = sc["labels"]
        ours = [(_sec(t, day), n) for t, n in zip(res.pred_times, res.pred_labels)]
        ref = [(t, labels[a]) for t, a, _ in sc["predictions"]]
        a_ours = sorted(_key(a) for a in res.alerts)
        a_ref = sorted(_key(a) for a in sc["alerts"])
        ok &= ours == ref and a_ours == a_ref
        print(f"  [{h}] {feed['id']:<13} {d['day']} {sid:<12} predictions {len(ours)} / "
              f"{len(ref)} {'same' if ours == ref else 'DIFFERENT'}; alerts {len(a_ours)} / "
              f"{len(a_ref)} {'same' if a_ours == a_ref else 'DIFFERENT'}")
        if a_ours != a_ref:
            print("    ours:", a_ours, "\n    ref: ", a_ref)
    print(f"  [{h}] {feed['id']:<13} {len(closed)}/{len(days)} days closed in {secs:.0f}s")
    return ok


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--home", default="all", choices=[*DATASETS, "all"])
    p.add_argument("--check-only", action="store_true")
    p.add_argument("--no-check", action="store_true")
    args = p.parse_args(argv)
    homes = list(DATASETS) if args.home == "all" else [args.home]
    ok = True
    for h in homes:
        if args.check_only:
            index = json.loads((REPLAY_DIR / "index.json").read_text())[h]
            ids = [s["id"] for s in index["scenarios"]] + [WEEK_ID]
            feeds = [load(h, i) for i in ids if feed_path(h, i).is_file()]
        else:
            feeds = build(h)
            FEEDS_DIR.mkdir(parents=True, exist_ok=True)
            for f in feeds:
                path = feed_path(h, f["id"])
                path.write_text(json.dumps(f, separators=(",", ":")), encoding="utf8")
                print(f"  [{h}] {f['id']:<13} {len(f['events']):,} events "
                      f"({f['prefixEvents']} from the evening before) -> {path.name} "
                      f"({path.stat().st_size // 1024} KB)")
        if not args.no_check:
            ok &= all([check(f) for f in feeds])
    if not args.no_check:
        print("all feeds reproduce the replay" if ok else "SOME FEEDS DIFFER")


if __name__ == "__main__":
    main()
