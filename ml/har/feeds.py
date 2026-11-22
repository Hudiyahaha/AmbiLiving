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

The backend plays a feed into a live session (``LiveMonitor``) event by event, so
recognition, the routine model and routing run live. ``--check`` replays every
feed through ``LiveMonitor`` in one push and requires the same predictions and
alerts as the scenario in ``public/replay/``.

Feed format (compact JSON): ``day`` (midnight), ``sensors``, ``states`` (CASAS
states), and ``events`` as ``[microseconds since day midnight, sensor index,
state index]`` — negative offsets are the prefix from the previous day.
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


def feed_path(home: str, scenario: str):
    return FEEDS_DIR / f"{home}-{scenario}.json"


def _sec(t, day) -> int:
    return int((pd.Timestamp(t) - day).total_seconds())


def build(home_name: str) -> list[dict]:
    index = json.loads((REPLAY_DIR / "index.json").read_text())[home_name]
    home = load_home(home_name)
    _, test_start, train_cut, _ = day_split(home, 0.6, 0.2)
    days = sorted(pd.to_datetime(home.times[test_start:]).normalize().unique())
    t0 = time.time()
    variants = make_variants(home, days, train_cut, PER_DAY, SEED)
    print(f"  [{home_name}] {len(variants)} day copies rebuilt in {time.time() - t0:.0f}s")

    feeds = []
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
        v = cands[0]
        p_hi = int(np.searchsorted(home.times, day.to_datetime64()))
        p_lo = max(0, p_hi - PREFIX)
        times = np.concatenate([home.times[p_lo:p_hi], v.times])
        sensors = np.concatenate([home.sensors[p_lo:p_hi], v.sensors])
        states = np.concatenate([home.states[p_lo:p_hi], v.states])
        keep = np.isin(states, STATES)
        times, sensors, states = times[keep], sensors[keep], states[keep]
        sens = sorted(set(sensors))
        sidx = {s: i for i, s in enumerate(sens)}
        st = {s: i for i, s in enumerate(STATES)}
        us = ((times - day.to_datetime64()) // np.timedelta64(1, "us")).astype(np.int64)
        feeds.append({
            "home": home_name, "id": sc["id"], "title": sc["title"], "kind": sc["kind"],
            "day": f"{day:%Y-%m-%d}", "dayLabel": sc["day"], "injected": sc["injected"],
            "typical": sc["typical"], "prefixEvents": int(p_hi - p_lo),
            "sensors": sens, "states": STATES,
            "events": [[int(u), sidx[s], st[x]] for u, s, x in zip(us, sensors, states)],
        })
    return feeds


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


def check(feed: dict) -> bool:
    """Play the whole feed into a LiveMonitor; compare with the replay scenario."""
    from .routine_live import LiveMonitor
    from .routine_live import load as load_routine
    from .saved_model import load as load_wm
    from .saved_model import model_path

    h = feed["home"]
    sc = json.loads((REPLAY_DIR / f"{h}-{feed['id']}.json").read_text())
    day = pd.Timestamp(feed["day"])
    times, sensors, states = decode(feed)
    mon = LiveMonitor(load_wm(model_path(h, "bilstm", 1)), load_routine(h), day)
    t0 = time.time()
    r = mon.push(times, sensors, states, now=day + pd.Timedelta(days=1))
    secs = time.time() - t0
    labels = sc["labels"]
    ours = [(_sec(t, day), n) for t, n, _ in r["predictions"]]
    ref = [(t, labels[a]) for t, a, _ in sc["predictions"]]
    key = lambda a: (a["raisedAt"], a["kind"], a["activity"], a["tier"], a["delivered"])  # noqa: E731
    a_ours = sorted(key(a) for a in r["closed"][0].alerts)
    a_ref = sorted(key(a) for a in sc["alerts"])
    ok = ours == ref and a_ours == a_ref
    print(f"  [{h}] {feed['id']:<13} predictions {len(ours)} / {len(ref)} "
          f"{'same' if ours == ref else 'DIFFERENT'}; alerts {len(a_ours)} / {len(a_ref)} "
          f"{'same' if a_ours == a_ref else 'DIFFERENT'}  ({secs:.0f}s)")
    if a_ours != a_ref:
        print("    ours:", a_ours, "\n    ref: ", a_ref)
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
            feeds = [load(h, s["id"]) for s in index["scenarios"]]
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
