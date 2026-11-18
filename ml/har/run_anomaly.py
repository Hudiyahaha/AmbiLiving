"""End-to-end routine-deviation experiment: injection -> recognition -> routine -> alerts.

Protocol (decision D13), per home:

1. Chronological day split 60 / 20 / 20: recognisers train on the first 60 % of days,
   the resident's routine is learned on the middle 20 % (observation period), and the
   last 20 % is the monitoring period.
2. Every monitoring day is copied; ``--per-day`` copies per deviation type get one
   synthetic routine deviation injected into the raw sensor events (``anomaly_inject``),
   plus 7-day drift runs in which breakfast moves later each day.
3. Three activity streams are produced for all observation and monitoring days:
   ``gt``   annotated activities (upper bound: perfect recognition),
   ``seg``  segment recogniser, Gradient Boosting + pre-segment context, with the
            annotated boundaries (the dashboard's current model),
   ``win``  live window recogniser, BiLSTM on the last 100 events every 10th event
            (the final window model, no boundaries).
4. For each stream, the routine model (``routine``, ours) and the generic
   anomaly-detection baseline (``generic``, autoencoder) are fitted on the observation
   period, thresholds are calibrated to an alert budget per normal day, and alerts on
   monitoring days are matched to the injected deviations.

    python -m har.run_anomaly --dataset all
    python -m har.run_anomaly --dataset milan --streams gt seg   # skip the BiLSTM

Outputs in results/<home>/anomaly/: summary.json, sweep.csv, injections.csv,
alerts_<stream>_<method>.csv; ``python -m har.anomaly_report`` builds results/anomaly.md.
"""

from __future__ import annotations

import argparse
import json
import pickle
import time
from dataclasses import replace

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import f1_score

from .anomaly import (DAILY_KINDS, DayData, GenericAD, RoutineDrift, RoutineModel,
                      budget_threshold, calibrate_drift, calibrate_routine, match)
from .anomaly_inject import DRIFT_DAYS, TYPES, build_combined, make_variants
from .data import DATASETS, load_home
from .features import encode_sequences, handcrafted_features
from .models import classical
from .run import RESULTS_DIR
from .models import sequence
from .train import Trained
from .train import fit as fit_sequence
from .train import predict_proba as predict_sequence
from .windows import day_split, make_windows

BUDGETS = [0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
OPERATING = 0.1


# --------------------------------------------------------------------------- streams

def _windows(home, ends: np.ndarray, size: int):
    """Window table ending at ``ends`` (exclusive), without labels."""
    ends = ends[ends >= size]
    lo = ends - size
    seg = pd.DataFrame({"activity": "?", "start": pd.to_datetime(home.times[lo]),
                        "end": pd.to_datetime(home.times[ends - 1]), "lo": lo, "hi": ends})
    return replace(home, segments=seg)


def points_to_episodes(times: np.ndarray, labels: list[str], day_end, min_run: int = 3):
    """Per-point predictions -> episodes. Runs shorter than ``min_run`` points are
    absorbed into the previous episode (one stray window is not a new activity)."""
    rows = []
    for t, lab in zip(times, labels):
        if rows and rows[-1][0] == lab:
            rows[-1][2] += 1
            continue
        rows.append([lab, pd.Timestamp(t), 1])
    merged: list[list] = []
    for lab, t, n in rows:
        if merged and (n < min_run or merged[-1][0] == lab):
            merged[-1][2] += n
            continue
        merged.append([lab, t, n])
    out = [(lab, t, merged[i + 1][1] if i + 1 < len(merged) else day_end)
           for i, (lab, t, _) in enumerate(merged)]
    return pd.DataFrame(out, columns=["activity", "start", "end"])


def build_streams(dataset: str, args, out_dir) -> dict:
    home = load_home(dataset)
    train_end, test_start, train_cut, test_cut = day_split(home, 0.6, 0.2)
    days = sorted(pd.to_datetime(home.times[test_start:]).normalize().unique())
    variants = make_variants(home, days, train_cut, args.per_day, args.seed)
    comb = build_combined(home, test_start, test_cut, variants)
    classes = home.activities
    print(f"[{dataset}] train < {train_cut.date()} <= observe < {test_cut.date()} <= monitor; "
          f"{len(days)} monitoring days, {len(variants)} day copies, {len(comb.times):,} events")

    seg = comb.segments
    vids = seg["vid"].to_numpy()
    offs = {v.vid: v.offset for v in variants}
    real_start = seg["start"] - seg["vid"].map(offs).fillna(pd.Timedelta(0))
    real_end = seg["end"] - seg["vid"].map(offs).fillna(pd.Timedelta(0))
    obs = (vids == -1) & (seg["start"] >= train_cut).to_numpy()

    # Observation-day event times come from the real home.
    obs_days = sorted(pd.Series(real_start[obs]).dt.normalize().unique())
    t_all = home.times

    def obs_times(day):
        lo = np.searchsorted(t_all, np.datetime64(day))
        hi = np.searchsorted(t_all, np.datetime64(day + pd.Timedelta(days=1)))
        return t_all[lo:hi]

    def seg_stream(labels: np.ndarray) -> tuple[list[DayData], dict[int, DayData]]:
        df = pd.DataFrame({"activity": labels, "start": real_start, "end": real_end, "vid": vids})
        ref = []
        o = df[obs]
        for i, day in enumerate(obs_days):
            e = o[o["start"].dt.normalize() == day].sort_values("start")
            ref.append(DayData(-1 - i, pd.Timestamp(day), obs_times(day),
                               e[["activity", "start", "end"]].reset_index(drop=True)))
        test = {}
        for v in variants:
            e = df[df["vid"] == v.vid].sort_values("start")
            test[v.vid] = DayData(v.vid, v.day, v.times,
                                  e[["activity", "start", "end"]].reset_index(drop=True))
        return ref, test

    out = {"variants": variants, "classes": classes, "streams": {}, "har": {}}
    gt_labels = seg["activity"].to_numpy()
    out["streams"]["gt"] = seg_stream(gt_labels)

    if "seg" in args.streams:
        t0 = time.time()
        X, _ = handcrafted_features(comb, preceding=True)
        cidx = {c: i for i, c in enumerate(classes)}
        y = seg["activity"].map(cidx).to_numpy()
        tr = (vids == -1) & (seg["start"] < train_cut).to_numpy()
        proba = classical.fit_predict_proba("hgb", X[tr], y[tr], X, args.seed, len(classes))
        pred = np.asarray(classes, dtype=object)[proba.argmax(1)]
        pred[tr] = gt_labels[tr]  # never used; keeps the column complete
        out["streams"]["seg"] = seg_stream(pred)
        clean = np.isin(vids, [v.vid for v in variants if v.kind == "clean"])
        out["har"]["seg"] = _har_scores(gt_labels[clean], pred[clean])
        print(f"  seg stream ready ({time.time() - t0:.0f}s), clean-day macro-F1 "
              f"{out['har']['seg']['macro_f1']:.3f}")

    if "win" in args.streams:
        t0 = time.time()
        size = 100
        tw = make_windows(home, np.arange(size, train_end + 1, 50), size, "last")
        cidx = {c: i for i, c in enumerate(classes)}
        y_tr = tw.segments["activity"].map(cidx).to_numpy()
        counts = np.bincount(y_tr, minlength=len(classes))
        keep = counts[y_tr] >= 2
        tw = make_windows(home, tw.segments["hi"].to_numpy()[keep], size, "last")
        y_tr = y_tr[keep]
        Xtr = encode_sequences(tw, max_len=size)
        saved = out_dir / "bilstm.pt"
        if saved.exists():  # same split, seed and data: reuse instead of retraining
            ck = torch.load(saved, weights_only=False)
            net = sequence.build("bilstm", len(Xtr.vocab), Xtr.cont.shape[-1],
                                 Xtr.context.shape[-1], len(classes), size)
            net.load_state_dict(ck["state"])
            model = Trained(net, ck["ctx_mean"], ck["ctx_std"])
            print("  BiLSTM loaded from", saved)
        else:
            model = fit_sequence("bilstm", Xtr, y_tr, len(classes), seed=args.win_seed,
                                 max_epochs=args.epochs, verbose=args.verbose)
            torch.save({"state": model.model.state_dict(), "ctx_mean": model.ctx_mean,
                        "ctx_std": model.ctx_std}, saved)
            print(f"  BiLSTM trained ({time.time() - t0:.0f}s) -> {saved}")

        def predict(h, ends):
            wh = _windows(h, ends, size)
            data = encode_sequences(wh, max_len=size)
            assert data.vocab == Xtr.vocab, "token vocabulary must match training"
            p = predict_sequence(model, data)
            return wh.segments["hi"].to_numpy(), np.asarray(classes, dtype=object)[p.argmax(1)]

        ends_obs, lab_obs = predict(home, np.arange(train_end + 1, test_start + 1, args.stride))
        pt = home.times[ends_obs - 1]
        ref = []
        for i, day in enumerate(obs_days):
            m = (pt >= np.datetime64(day)) & (pt < np.datetime64(day + pd.Timedelta(days=1)))
            ref.append(DayData(-1 - i, pd.Timestamp(day), obs_times(day),
                               points_to_episodes(pt[m], list(lab_obs[m]),
                                                  pd.Timestamp(day) + pd.Timedelta(days=1))))
        test, all_true, all_pred = {}, [], []
        chunk = 40
        for c0 in range(0, len(variants), chunk):
            vs = variants[c0:c0 + chunk]
            ends = np.concatenate([np.arange(v.lo + 1, v.hi + 1, args.stride) for v in vs])
            e_hi, lab = predict(comb, ends)
            for v in vs:
                m = (e_hi > v.lo) & (e_hi <= v.hi)
                times = comb.times[e_hi[m] - 1] - v.offset.to_timedelta64()
                test[v.vid] = DayData(v.vid, v.day, v.times,
                                      points_to_episodes(times, list(lab[m]),
                                                         v.day + pd.Timedelta(days=1)))
                if v.kind == "clean":  # recognition quality on the untouched monitoring days
                    s = v.segments.sort_values("start")
                    j = np.searchsorted(s["start"].to_numpy(), times, side="right") - 1
                    ok = j >= 0
                    all_true += list(s["activity"].to_numpy()[j[ok]])
                    all_pred += list(lab[m][ok])
            print(f"    predicted {min(c0 + chunk, len(variants))}/{len(variants)} day copies "
                  f"({time.time() - t0:.0f}s)")
        out["streams"]["win"] = (ref, test)
        out["har"]["win"] = _har_scores(np.array(all_true), np.array(all_pred))
        print(f"  win stream ready ({time.time() - t0:.0f}s), clean-day macro-F1 "
              f"{out['har']['win']['macro_f1']:.3f}")
    return out


def _har_scores(y, p) -> dict:
    labels = sorted(set(y))
    return {"accuracy": float(np.mean(y == p)),
            "macro_f1": float(f1_score(y, p, labels=labels, average="macro", zero_division=0)),
            "n": int(len(y))}


# --------------------------------------------------------------------------- detection

def evaluate(ref: list[DayData], test: dict[int, DayData], variants, classes, method: str,
             seed: int) -> tuple[list[dict], dict[float, list]]:
    """Alerts and per-variant outcomes for every budget in BUDGETS.

    ``routine``: our routine model (all daily aspects + multi-day drift).
    ``generic``: the generic anomaly-detection baseline (autoencoder only).
    """
    n_ref = len(ref)
    daily = [v for v in variants if v.kind != "drift"]
    clean = sorted([v for v in variants if v.kind == "clean"], key=lambda v: v.day)
    runs: dict[int, list] = {}
    for v in variants:
        if v.kind == "drift":
            runs.setdefault(v.seq, []).append(v)
    if method == "routine":
        model = RoutineModel().fit(ref)
        pool = calibrate_routine(ref)
        drift = RoutineDrift().fit(ref)
        d_pool, d_n = calibrate_drift(ref, DRIFT_DAYS)
    else:
        model = GenericAD(classes, seed).fit(ref)
        g_pool = model.oof_scores(ref)
    rows, alerts_at = [], {}
    for b in BUDGETS:
        if method == "routine":
            theta = {k: budget_threshold(pool[k], n_ref, b) for k in DAILY_KINDS}
            th_drift = budget_threshold(d_pool, d_n, b)
        else:
            th_g = budget_threshold(g_pool, n_ref, b)
        all_alerts = []
        for v in daily:
            al = model.alerts(test[v.vid], theta if method == "routine" else th_g)
            all_alerts += al
            row = {"budget": b, "vid": v.vid, "kind": v.kind, "target": v.target,
                   "n_alerts": len(al)}
            if v.kind != "clean":
                hit = match(al, v.kind, v.target, v.a_start, v.a_end)
                row["detected"] = hit is not None
                row["delay"] = ((hit.time - v.a_start).total_seconds() / 60
                                if hit is not None else np.nan)
                row["by"] = hit.kind if hit is not None else ""
            rows.append(row)
        if method == "routine":
            # Drift on the real monitoring days: one rolling window per day (false alerts).
            for i in range(2, len(clean)):
                win = [test[v.vid] for v in clean[max(0, i - DRIFT_DAYS + 1):i + 1]]
                al = drift.alerts(win, th_drift)
                all_alerts += al
                rows.append({"budget": b, "vid": clean[i].vid, "kind": "clean_drift",
                             "target": "", "n_alerts": len(al)})
            # Drift runs: detected on the first day (>= 3) a drift alert names the target.
            for seq, vs in runs.items():
                vs = sorted(vs, key=lambda v: v.pos)
                hit_day = None
                for k in range(3, len(vs) + 1):
                    al = drift.alerts([test[v.vid] for v in vs[:k]], th_drift)
                    if any(a.activity == vs[0].target and a.record.get("what") == "time"
                           for a in al):
                        hit_day = k
                        all_alerts += al
                        break
                rows.append({"budget": b, "vid": vs[-1].vid, "kind": "drift",
                             "target": vs[0].target, "n_alerts": 0,
                             "detected": hit_day is not None,
                             "delay": float(hit_day) if hit_day else np.nan,
                             "by": "drift" if hit_day else ""})
        alerts_at[b] = all_alerts
    return rows, alerts_at


def summarise(rows: pd.DataFrame) -> dict:
    clean = rows[rows["kind"] == "clean"]
    fa = float(clean["n_alerts"].mean())
    fp_rate = float((clean["n_alerts"] > 0).mean())
    out = {"false_alerts_per_day": fa, "clean_days_with_alert": fp_rate, "types": {}}
    f1s, rec = [], []
    for t in TYPES:
        r = rows[rows["kind"] == t]
        if r.empty:
            continue
        tp = float(r["detected"].sum())
        n = len(r)
        fp = fp_rate * n  # balanced: as many clean days as injected days of this type
        p = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / n
        f1 = 2 * p * rc / (p + rc) if p + rc else 0.0
        out["types"][t] = {"n": n, "detection_rate": rc, "precision": p, "f1": f1,
                           "median_delay_min": float(r["delay"].median())
                           if r["detected"].any() else None}
        f1s.append(f1)
        rec.append(rc)
    out["macro_f1"] = float(np.mean(f1s)) if f1s else 0.0
    out["mean_detection_rate"] = float(np.mean(rec)) if rec else 0.0
    dr = rows[rows["kind"] == "drift"]
    cd = rows[rows["kind"] == "clean_drift"]
    if len(dr):
        out["drift"] = {"runs": int(len(dr)), "detected": int(dr["detected"].sum()),
                        "median_delay_days": float(dr["delay"].median())
                        if dr["detected"].any() else None,
                        "false_alerts_per_day": float(cd["n_alerts"].mean()) if len(cd) else None}
    return out


def run(dataset: str, args):
    out_dir = RESULTS_DIR / dataset / "anomaly"
    out_dir.mkdir(parents=True, exist_ok=True)
    cache = out_dir / "streams.pkl"
    if args.reuse and cache.exists():
        with open(cache, "rb") as f:
            S = pickle.load(f)
        print(f"[{dataset}] reusing {cache}")
    else:
        S = build_streams(dataset, args, out_dir)
        with open(cache, "wb") as f:
            pickle.dump(S, f)
    variants = S["variants"]
    pd.DataFrame([{"vid": v.vid, "day": v.day.date(), "kind": v.kind, "target": v.target,
                   "start": v.a_start, "end": v.a_end, "seq": v.seq, "pos": v.pos,
                   "note": v.note} for v in variants]
                 ).to_csv(out_dir / "injections.csv", index=False)

    summary = {"dataset": dataset, "operating_budget": OPERATING, "har": S["har"],
               "n_observation_days": None, "n_monitoring_days":
                   sum(v.kind == "clean" for v in variants), "results": {}}
    sweep = []
    kinds = {v.vid: v.kind for v in variants}
    for stream, (ref, test) in S["streams"].items():
        summary["n_observation_days"] = len(ref)
        for method in args.methods:
            t0 = time.time()
            rows, alerts_at = evaluate(ref, test, variants, S["classes"], method, args.seed)
            rows = pd.DataFrame(rows)
            for b in BUDGETS:
                s = summarise(rows[rows["budget"] == b])
                sweep.append({"stream": stream, "method": method, "budget": b,
                              "false_alerts_per_day": s["false_alerts_per_day"],
                              "mean_detection_rate": s["mean_detection_rate"],
                              "macro_f1": s["macro_f1"],
                              "drift_detected": s.get("drift", {}).get("detected"),
                              "drift_runs": s.get("drift", {}).get("runs")}
                             | {f"rate_{t}": s["types"].get(t, {}).get("detection_rate")
                                for t in TYPES})
                if b == OPERATING:
                    summary["results"][f"{stream}/{method}"] = s
            pd.DataFrame([{"vid": a.key, "day_kind": kinds[a.key], "kind": a.kind,
                           "activity": a.activity, "time": a.time, "score": round(a.score, 3)}
                          | {k: v for k, v in a.record.items() if k != "what"}
                          for a in alerts_at[OPERATING]]
                         ).to_csv(out_dir / f"alerts_{stream}_{method}.csv", index=False)
            s = summary["results"][f"{stream}/{method}"]
            drift = s.get("drift")
            print(f"  {stream:>3}/{method:<7} detection {s['mean_detection_rate']:.2f}  "
                  f"F1 {s['macro_f1']:.2f}  false alerts/day {s['false_alerts_per_day']:.2f}  "
                  + "  ".join(f"{t[:6]} {s['types'][t]['detection_rate']:.2f}"
                              for t in TYPES if t in s["types"])
                  + (f"  drift {drift['detected']}/{drift['runs']}" if drift else "")
                  + f"  ({time.time() - t0:.0f}s)")
    pd.DataFrame(sweep).to_csv(out_dir / "sweep.csv", index=False)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(f"  -> {out_dir}")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset", default="all", choices=[*DATASETS, "all"])
    p.add_argument("--streams", nargs="+", default=["gt", "seg", "win"],
                   choices=["gt", "seg", "win"])
    p.add_argument("--methods", nargs="+", default=["routine", "generic"],
                   choices=["routine", "generic"])
    p.add_argument("--per-day", type=int, default=3, help="injected copies per type per day")
    p.add_argument("--stride", type=int, default=10, help="window recogniser runs every N events")
    p.add_argument("--seed", type=int, default=0, help="injection / detector seed")
    p.add_argument("--win-seed", type=int, default=1, help="BiLSTM seed")
    p.add_argument("--epochs", type=int, default=40)
    p.add_argument("--reuse", action="store_true", help="reuse cached streams.pkl")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args(argv)
    for ds in (list(DATASETS) if args.dataset == "all" else [args.dataset]):
        run(ds, args)


if __name__ == "__main__":
    main()
