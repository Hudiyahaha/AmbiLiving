"""Episode-level view of live window recognition.

The window models are scored per event (macro-F1 over every test event). Routine
deviation detection does not use single events. It uses *episodes*: did a meal
happen, when did it start, how long was it, how many were there. This script
checks the stored per-event predictions at that level, against the annotated
activities of the test days:

* found      share of annotated episodes overlapped by a predicted episode of the
             same activity (within +-``tol`` minutes)
* start err  median |predicted start - annotated start| of found episodes (min)
* dur ratio  median predicted / annotated duration of found episodes
* true/day, pred/day
             annotated vs predicted episodes per day. pred >> true means the
             prediction flickers and the routine model sees many fake episodes.
* precision  share of predicted episodes that overlap an annotated episode of the
             same activity (within +-``tol``)

``--min-minutes m`` also reports a cleaned stream, where predicted runs shorter than
m minutes are absorbed into the run before them (past-only, so it can run live).
This is a diagnostic, not a tuned setting.

    python -m har.episode_eval --dataset all --run bilstm+s1
"""

from __future__ import annotations

import argparse
import gzip
from pathlib import Path

import numpy as np
import pandas as pd

from .data import DATASETS, load_home
from .run import RESULTS_DIR
from .windows import day_split

DOC = RESULTS_DIR / "episodes.md"


def runs(times: np.ndarray, labels: np.ndarray) -> pd.DataFrame:
    """Consecutive equal labels -> episodes (start = first event, end = next run's first event)."""
    change = np.r_[True, labels[1:] != labels[:-1]]
    first = np.where(change)[0]
    nxt = np.r_[first[1:], len(labels) - 1]
    return pd.DataFrame({"activity": labels[first], "start": times[first], "end": times[nxt]})


def clean(times: np.ndarray, labels: np.ndarray, min_minutes: float) -> np.ndarray:
    """Absorb runs shorter than ``min_minutes`` into the preceding run (left to right)."""
    if min_minutes <= 0:
        return labels
    out = labels.copy()
    lim = np.timedelta64(int(min_minutes * 60), "s")
    change = np.r_[True, out[1:] != out[:-1]]
    first = np.where(change)[0]
    nxt = np.r_[first[1:], len(out)]
    cur = out[first[0]]
    for a, b in zip(first, nxt):
        end_t = times[b] if b < len(out) else times[-1]
        if a > 0 and end_t - times[a] < lim:
            out[a:b] = cur
        else:
            cur = out[a]
    return out


def score(true_eps: pd.DataFrame, pred_eps: pd.DataFrame, n_days: int,
          tol_min: float) -> pd.DataFrame:
    tol = pd.Timedelta(minutes=tol_min)
    rows = []
    for act in sorted(true_eps["activity"].unique()):
        t = true_eps[true_eps["activity"] == act]
        p = pred_eps[pred_eps["activity"] == act]
        ps, pe = p["start"].to_numpy(), p["end"].to_numpy()
        found, starts, ratios = 0, [], []
        for s, e in zip(t["start"].to_numpy(), t["end"].to_numpy()):
            hit = (ps <= e + tol) & (pe >= s - tol)
            if hit.any():
                found += 1
                k = np.argmin(np.abs(ps[hit] - s))
                starts.append(abs((ps[hit][k] - s) / np.timedelta64(1, "m")))
                td = max((e - s) / np.timedelta64(1, "m"), 0.5)
                ratios.append(((pe[hit][k] - ps[hit][k]) / np.timedelta64(1, "m")) / td)
        ts, te = t["start"].to_numpy(), t["end"].to_numpy()
        prec = (np.mean([((ts <= e + tol) & (te >= s - tol)).any() for s, e in zip(ps, pe)])
                if len(p) else np.nan)
        rows.append({
            "activity": act, "true_episodes": len(t),
            "found_%": 100 * found / len(t),
            "start_err_min": float(np.median(starts)) if starts else np.nan,
            "dur_ratio": float(np.median(ratios)) if ratios else np.nan,
            "true_per_day": len(t) / n_days, "pred_per_day": len(p) / n_days,
            "precision_%": 100 * prec,
        })
    return pd.DataFrame(rows)


def evaluate(dataset: str, run: str, tol: float, min_minutes: float) -> dict[str, pd.DataFrame]:
    home = load_home(dataset)
    _, _, _, test_cut = day_split(home, 0.6, 0.2)
    path = RESULTS_DIR / dataset / "window100-last" / "experiments" / run / "predictions.csv.gz"
    if not path.exists():
        path = RESULTS_DIR / dataset / "window100-last" / run / "predictions.csv.gz"
    if not path.exists():
        print(f"  [{dataset}] no stored run {run}; skipped")
        return {}
    with gzip.open(path, "rt") as f:
        pr = pd.read_csv(f, usecols=["end", "pred"], parse_dates=["end"])
    times = pr["end"].to_numpy()
    labels = pr["pred"].to_numpy().astype(object)
    seg = home.segments
    true_eps = seg[seg["start"] >= test_cut][["activity", "start", "end"]]
    n_days = len(pd.unique(pd.to_datetime(times).normalize()))
    out = {"raw": score(true_eps, runs(times, labels), n_days, tol)}
    # What the routine-deviation pipeline sees: every 10th event, runs < 3 points
    # absorbed, built per day (har.run_anomaly.points_to_episodes).
    from .run_anomaly import points_to_episodes
    pt, pl = times[::10], labels[::10]
    days = pd.to_datetime(pt).normalize()
    eps = [points_to_episodes(pt[days == d], list(pl[days == d]), d + pd.Timedelta(days=1))
           for d in pd.unique(days)]
    out["anomaly-pipeline"] = score(true_eps, pd.concat(eps, ignore_index=True), n_days, tol)
    if min_minutes > 0:
        out[f"clean{min_minutes:g}"] = score(true_eps, runs(times, clean(times, labels, min_minutes)),
                                            n_days, tol)
    return out


def _table(df: pd.DataFrame) -> str:
    cols = ["activity", "true_episodes", "found_%", "precision_%", "start_err_min", "dur_ratio",
            "true_per_day", "pred_per_day"]
    head = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    body = ""
    for _, r in df[cols].iterrows():
        body += "| " + " | ".join(
            str(r[c]) if c in ("activity", "true_episodes") else
            ("–" if pd.isna(r[c]) else f"{r[c]:.1f}" if c != "dur_ratio" else f"{r[c]:.2f}")
            for c in cols) + " |\n"
    t = df["true_per_day"].sum()
    p = df["pred_per_day"].sum()
    body += (f"| **all** | {df['true_episodes'].sum()} | **{df['found_%'].mean():.1f}** (mean) | "
             f"**{df['precision_%'].mean():.1f}** (mean) | | | {t:.1f} | {p:.1f} |\n")
    return head + body


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset", default="all", choices=[*DATASETS, "all"])
    p.add_argument("--run", nargs="+", default=["bilstm+s1"],
                   help="stored window run(s), e.g. bilstm+s1 hgb+histpast+bal+tr10+s1")
    p.add_argument("--tol", type=float, default=15.0, help="matching tolerance in minutes")
    p.add_argument("--min-minutes", type=float, default=2.0,
                   help="also score a cleaned stream (runs shorter than this are absorbed)")
    p.add_argument("--write", action="store_true", help=f"write the tables to {DOC}")
    args = p.parse_args(argv)
    md = ["# Episode-level recognition (live windows)\n",
          "Generated by `python -m har.episode_eval`. Annotated test-day episodes vs episodes "
          "formed from the stored per-event predictions (runs of the same predicted activity). "
          f"Match tolerance ±{args.tol:g} min. *found* = recall of episodes, *precision* = share "
          "of predicted episodes that overlap a true one, *pred/day* ≫ *true/day* = flickering. "
          "*anomaly-pipeline* = the episodes the routine-deviation detector actually uses "
          "(every 10th event, runs shorter than 3 points absorbed, per day; "
          "`har.run_anomaly.points_to_episodes`). "
          f"*clean{args.min_minutes:g}* absorbs predicted runs shorter than {args.min_minutes:g} "
          "min into the run before (past only; diagnostic, not tuned).\n"]
    for ds in (list(DATASETS) if args.dataset == "all" else [args.dataset]):
        for run in args.run:
            res = evaluate(ds, run, args.tol, args.min_minutes)
            for name, df in res.items():
                title = f"## {ds} — {run} — {name}"
                print(f"\n{title}")
                print(df.round(2).to_string(index=False))
                print(f"  mean found {df['found_%'].mean():.1f} %, mean precision "
                      f"{df['precision_%'].mean():.1f} %, episodes/day true "
                      f"{df['true_per_day'].sum():.1f} vs predicted {df['pred_per_day'].sum():.1f}")
                md.append(f"{title}\n\n{_table(df)}")
    if args.write:
        DOC.write_text("\n".join(md), encoding="utf-8")
        print(f"\nwrote {DOC}")


if __name__ == "__main__":
    main()
