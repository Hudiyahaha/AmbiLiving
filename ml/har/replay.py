"""Live-demo replays: one day at a time through the live pipeline (decision D17).

    python -m har.replay                  # both homes -> public/replay/
    python -m har.replay --home milan

For each home a handful of scenario days are replayed **causally** through what a
deployed system would run:

1. the live window recogniser (BiLSTM on the last 100 sensor events, every 10th
   event), with the probability of its answer as confidence;
2. the resident's routine model, fitted on the observation days of the same live
   stream, at the operating point (0.1 alerts per normal day per aspect);
3. alert routing (D15): notify now, evening summary, dashboard only.

"Causally" is checked, not assumed: every 2 minutes of the day the routine model is
re-run on only what had happened by then (events and predictions up to that minute,
episodes cut at that minute). An alert is shown in the replay from the first minute
it appears this way, with the text it had then. So nothing in the replay uses the
future.

Scenarios: one real monitoring day (nothing injected), and one day copy for each
injected deviation type, chosen among the copies where the batch evaluation says
the deviation reached the caregiver. Every scenario carries the *overall* rate for
its type on the live stream, so the chosen example is never mistaken for typical.

Live stream per home (E20): Aruba uses the time-based cleanup (``winc``: predicted
runs shorter than the length chosen on the observation days are absorbed), which
raised live detection from 16 % to 45 %; Milan keeps the original 3-point rule
(``win``), because the cleanup brought no gain there at matched false alerts and
tripled notifications. Override with ``--stream``.

Needs ``python -m har.run_anomaly --win-clean auto --tag e20`` and
``python -m har.alerts --folder anomaly-e20`` first (streams.pkl, alert files,
routing.json); the BiLSTM comes from ``har.saved_model``.
Writes ``public/replay/index.json`` and ``public/replay/<home>-<scenario>.json``.
"""

from __future__ import annotations

import argparse
import json
import pickle
import time

import numpy as np
import pandas as pd
import torch

from .alerts import COOLDOWN, PRIORITY, SUMMARY_CAP, URGENT, _matched, route, tier
from .anomaly import (BATHROOM, BINS, DAILY_KINDS, DayData, RoutineModel, budget_threshold,
                      calibrate_routine)
from .anomaly_inject import COOKING
from .data import DATASETS, ML_DIR, load_home
from .features import encode_sequences
from .anomaly_inject import build_combined
from .models import sequence
from .run import RESULTS_DIR
from .run_anomaly import (OPERATING, _windows, add_clean_stream, minutes_to_episodes,
                          points_to_episodes)
from .saved_model import load as load_saved
from .saved_model import model_path
from .train import Trained
from .train import predict_proba as predict_sequence
from .windows import day_split

OUT_DIR = ML_DIR.parent / "public" / "replay"
SIZE, STRIDE = 100, 10
STEP = pd.Timedelta(minutes=2)
FOLDER = "anomaly-e20"
DEFAULT_STREAM = {"aruba": "winc", "milan": "win"}  # E20
SUMMARY_AT = 21 * 3600  # evening summary sent at 21:00 in the demo
STATE = {"ON": 0, "OFF": 1, "OPEN": 2, "CLOSE": 3}
STATE_NAMES = ["active", "inactive", "open", "closed"]

SCENARIOS = [
    # id, injected kind, target filter, title
    ("normal", "clean", None, "A real day, nothing injected"),
    ("inactivity", "inactivity", None, "Long silence at home"),
    ("bathroom", "prolonged", BATHROOM, "Very long bathroom visit"),
    ("night", "unusual_time", None, "Out of bed and active at night"),
    ("missed-meal", "missed", set(COOKING), "Meal not prepared"),
    ("toilet-trips", "night_frequency", None, "Extra night-time toilet trips"),
]
INJECTED_TYPE = {"inactivity": "inactivity", "prolonged": "prolonged_bathroom",
                 "unusual_time": "unusual_time", "missed": "missed",
                 "night_frequency": "night_frequency"}


def _sec(t, day) -> int:
    return int((pd.Timestamp(t) - day).total_seconds())


# --------------------------------------------------------------------------- choose days

def choose(home: str, variants, inj: pd.DataFrame, stream: str = "win",
           folder: str = "anomaly") -> list[tuple]:
    d = RESULTS_DIR / home / folder
    a = route(pd.read_csv(d / f"alerts_{stream}_routine.csv"))
    shown = a[a["delivered"] & a["tier"].isin(["notify", "summary"])]
    per_day = shown.groupby("vid").size()
    by_vid = {v.vid: v for v in variants}
    out = []
    for sid, kind, targets, title in SCENARIOS:
        rows = inj[inj["kind"] == kind]
        if targets is not None:
            rows = rows[rows["target"].isin(targets)]
        if rows.empty:
            continue
        if kind == "clean":
            n = rows["vid"].map(per_day).fillna(0)
            # the day with the median number of caregiver-facing alerts: typical, not quiet
            pick = rows.iloc[int(np.argsort(n.to_numpy(), kind="stable")[len(n) // 2])]
            out.append((sid, title, by_vid[int(pick.vid)], None))
            continue
        caught = []
        for r in rows.itertuples():
            m = _matched(a, r)
            urgent = kind in URGENT or (kind == "prolonged" and r.target in BATHROOM)
            ok = (m["tier"] == "notify").any() if urgent else m["tier"].isin(
                ["notify", "summary"]).any()
            caught.append(ok)
        rows = rows.assign(caught=caught, n=rows["vid"].map(per_day).fillna(0))
        good = rows[rows["caught"]].sort_values(["n", "vid"])
        pick = good.iloc[0] if len(good) else rows.sort_values(["n", "vid"]).iloc[0]
        out.append((sid, title, by_vid[int(pick.vid)], bool(len(good))))
    return out


# --------------------------------------------------------------------------- live recogniser

def recognise(home_name: str, chosen: list, out_dir) -> dict[int, tuple]:
    """Per-point BiLSTM predictions (times, labels, confidence) for the chosen day copies."""
    home = load_home(home_name)
    _, test_start, _, test_cut = day_split(home, 0.6, 0.2)
    variants = [v for *_, v, _ in chosen]
    comb = build_combined(home, test_start, test_cut, variants)
    classes = home.activities
    ends = np.concatenate([np.arange(v.lo + 1, v.hi + 1, STRIDE) for v in variants])
    wh = _windows(comb, ends, SIZE)
    data = encode_sequences(wh, max_len=SIZE)
    if (out_dir / "bilstm.pt").exists():
        ck = torch.load(out_dir / "bilstm.pt", weights_only=False)
        net = sequence.build("bilstm", len(data.vocab), data.cont.shape[-1],
                             data.context.shape[-1], len(classes), SIZE)
        net.load_state_dict(ck["state"])
        trained = Trained(net, ck["ctx_mean"], ck["ctx_std"])
    else:
        wm = load_saved(model_path(home_name, "bilstm", 1, SIZE))
        assert wm.vocab == data.vocab, "saved model vocabulary must match"
        trained = wm.trained
    p = predict_sequence(trained, data)
    e_hi = wh.segments["hi"].to_numpy()
    out = {}
    for v in variants:
        m = (e_hi > v.lo) & (e_hi <= v.hi)
        times = comb.times[e_hi[m] - 1] - v.offset.to_timedelta64()
        pr = p[m]
        out[v.vid] = (times, np.asarray(classes, dtype=object)[pr.argmax(1)], pr.max(1))
    return out


# --------------------------------------------------------------------------- causal replay

def live_alerts(model: RoutineModel, theta: dict, v, times, labels,
                to_eps=points_to_episodes) -> tuple[list[dict], int]:
    """Alerts as a live system raises them: re-run on the day so far every STEP."""
    first: dict[tuple, dict] = {}
    g = v.day + STEP
    end = v.day + pd.Timedelta(days=1)
    while g <= end:
        g64 = g.to_datetime64()
        ev = v.times[v.times < g64]
        # The clock is an observation too: a silence lasting until now is a silence.
        ev = np.append(ev, g64) if g < end else ev
        m = times < g64
        eps = to_eps(times[m], list(labels[m]), g)
        for a in model.alerts(DayData(v.vid, v.day, ev, eps), theta):
            if a.time > g:
                continue
            key = (a.kind, a.activity, a.time.floor("min"))
            if key not in first:
                first[key] = {"raisedAt": _sec(g, v.day), "time": a.time, "kind": a.kind,
                              "activity": a.activity, **a.record}
        g += STEP
    # Batch alerts (whole day at once) must all have been raised live.
    full = model.alerts(DayData(v.vid, v.day, v.times,
                                to_eps(times, list(labels), end)), theta)
    missing = sum((a.kind, a.activity, a.time.floor("min")) not in first for a in full)
    return sorted(first.values(), key=lambda r: r["raisedAt"]), missing


def route_live(alerts: list[dict]) -> list[dict]:
    """D15 routing in raise order: cool-down for notifications, 21:00 summary of 3."""
    last: dict[tuple, int] = {}
    for a in alerts:
        a["tier"] = tier(a["kind"], a["activity"], a["time"])
        a["delivered"] = True
        if a["tier"] == "notify":
            key = (a["kind"], a["activity"])
            if key in last and a["raisedAt"] - last[key] < COOLDOWN.total_seconds():
                a["delivered"] = False
            else:
                last[key] = a["raisedAt"]
    prio = {k: i for i, k in enumerate(PRIORITY)}
    summ = [a for a in alerts if a["tier"] == "summary" and a["raisedAt"] <= SUMMARY_AT]
    keep = sorted(summ, key=lambda a: (prio.get(a["kind"], len(prio)), a["raisedAt"]))
    keep = {id(a) for a in keep[:SUMMARY_CAP]}
    for a in alerts:
        if a["tier"] == "summary":
            a["inSummary"] = id(a) in keep
            a["delivered"] = a["inSummary"] or a["raisedAt"] > SUMMARY_AT
    return alerts


# --------------------------------------------------------------------------- export

def export(home_name: str, stream: str | None = None, folder: str = FOLDER) -> dict:
    t0 = time.time()
    stream = stream or DEFAULT_STREAM.get(home_name, "win")
    out_dir = RESULTS_DIR / home_name / folder
    with open(out_dir / "streams.pkl", "rb") as f:
        S = pickle.load(f)
    variants, classes = S["variants"], S["classes"]
    if stream == "winc":
        add_clean_stream(S, "auto")
    ref, test = S["streams"][stream]
    if stream == "winc":
        mins = S["win_clean"]["minutes"]

        def to_eps(t, l, end):
            return minutes_to_episodes(t, l, end, mins)
    else:
        mins, to_eps = None, points_to_episodes
    print(f"  [{home_name}] live stream '{stream}'"
          + (f" (runs shorter than {mins:g} min absorbed)" if mins else " (3-point rule)"))
    inj = pd.read_csv(out_dir / "injections.csv")
    summary = json.loads((out_dir / "summary.json").read_text())
    routing = json.loads((out_dir / "routing.json").read_text())[stream]
    res = summary["results"][f"{stream}/routine"]

    model = RoutineModel().fit(ref)
    pool = calibrate_routine(ref)
    theta = {k: budget_threshold(pool[k], len(ref), OPERATING) for k in DAILY_KINDS}
    chosen = choose(home_name, variants, inj, stream, folder)
    preds = recognise(home_name, chosen, out_dir)
    lab_idx = {c: i for i, c in enumerate(classes)}
    usual = [model._expected_states([b]) for b in range(BINS)]
    daily = [{"activity": a,
              "usualFirst": f"{int(np.median(f[np.isfinite(f)])):02d}:"
                            f"{int(np.median(f[np.isfinite(f)]) % 1 * 60):02d}",
              "pDay": round(model.p_day[a], 2)}
             for a, f in sorted(model.first.items(),
                                key=lambda kv: np.median(kv[1][np.isfinite(kv[1])]))]

    scenarios = []
    for sid, title, v, caught in chosen:
        times, labels, conf = preds[v.vid]
        # The re-run must reproduce the live stream the evaluation used.
        same = to_eps(times, list(labels), v.day + pd.Timedelta(days=1))
        ref_eps = test[v.vid].eps
        agree = (len(same) == len(ref_eps)
                 and (same["activity"].to_numpy() == ref_eps["activity"].to_numpy()).all())
        alerts, missing = live_alerts(model, theta, v, times, labels, to_eps)
        alerts = route_live(alerts)
        if v.kind != "clean":
            lo = pd.Timestamp(v.a_start) - pd.Timedelta(minutes=30)
            hi = pd.Timestamp(v.a_end) + pd.Timedelta(minutes=60)
            for a in alerts:
                a["explainsInjection"] = bool(
                    (a["kind"] == "missed" and a["activity"] == v.target) if v.kind == "missed"
                    else lo <= a["time"] <= hi)
        itype = INJECTED_TYPE.get(v.kind)
        rate = res["types"].get(v.kind, {}).get("detection_rate")
        rt = routing["types"].get(itype, {})
        sc = {
            "home": home_name, "id": sid, "title": title, "kind": v.kind,
            "day": f"{v.day:%a %d %b %Y}",
            "injected": None if v.kind == "clean" else {
                "target": v.target, "start": _sec(v.a_start, v.day),
                "end": min(_sec(v.a_end, v.day), 86399), "note": v.note},
            "typical": None if v.kind == "clean" else {
                "detected": rate, "notified": rt.get("notified"), "surfaced": rt.get("surfaced"),
                "thisOneCaught": caught},
            "sensors": [], "events": [], "states": STATE_NAMES,
            "labels": list(classes),
            "predictions": [[_sec(t, v.day), lab_idx[l], round(float(c), 2)]
                            for t, l, c in zip(times, labels, conf)],
            "episodes": [[_sec(r.start, v.day), min(_sec(r.end, v.day), 86400),
                          lab_idx[r.activity]] for r in same.itertuples()],
            "annotations": [[_sec(r.start, v.day), min(_sec(r.end, v.day), 86400),
                             lab_idx[r.activity]] for r in v.segments.itertuples()
                            if r.activity in lab_idx],
            "usual": usual,  # most likely activities in each half hour
            "daily": daily,
            "summaryAt": SUMMARY_AT,
            "alerts": [{k: (_sec(val, v.day) if k == "time" else val) for k, val in a.items()
                        if k not in ("severity",)} for a in alerts],
        }
        sens = sorted(set(v.sensors))
        sidx = {s: i for i, s in enumerate(sens)}
        sc["sensors"] = sens
        sc["events"] = [[_sec(t, v.day), sidx[s], STATE[st]]
                        for t, s, st in zip(v.times, v.sensors, v.states) if st in STATE]
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUT_DIR / f"{home_name}-{sid}.json"
        path.write_text(json.dumps(sc, separators=(",", ":")), encoding="utf8")
        shown = [a for a in alerts if a["tier"] != "insight"]
        print(f"  [{home_name}] {sid:<13} {v.day:%d %b} vid {v.vid:<5} stream reproduced: "
              f"{'yes' if agree else 'NO'}; batch alerts not raised live: {missing}; "
              f"{len(alerts)} live alerts ({len(shown)} caregiver-facing); "
              f"{path.stat().st_size // 1024} KB")
        scenarios.append({"id": sid, "title": title, "day": sc["day"], "kind": v.kind,
                          "file": path.name, "reproduced": bool(agree), "notRaisedLive": missing})
    print(f"  [{home_name}] done in {time.time() - t0:.0f}s")
    return {"recogniser": "BiLSTM, last 100 events, every 10th event"
                          + (f"; runs shorter than {mins:g} min absorbed" if mins else ""),
            "recogniserMacroF1": round(summary["har"]["win"]["macro_f1"], 3),
            "routineLearnedFrom": f"{len(ref)} observation days",
            "falseAlertsPerDay": round(res["false_alerts_per_day"], 2),
            "detectionRate": round(res["mean_detection_rate"], 3),
            "urgentNotified": routing["urgent_notified"],
            "scenarios": scenarios}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--home", default="all", choices=[*DATASETS, "all"])
    p.add_argument("--stream", default=None, choices=["win", "winc"],
                   help="live stream to replay (default per home, see DEFAULT_STREAM)")
    p.add_argument("--folder", default=FOLDER, help="results/<home>/<folder>/ to read")
    args = p.parse_args(argv)
    homes = list(DATASETS) if args.home == "all" else [args.home]
    index_path = OUT_DIR / "index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    for h in homes:
        index[h] = export(h, args.stream, args.folder)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2), encoding="utf8")
    print("->", index_path)


if __name__ == "__main__":
    main()
