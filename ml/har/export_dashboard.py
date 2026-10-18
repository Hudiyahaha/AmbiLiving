"""Export one real day per home, with model-recognised activities, for the dashboard.

    python -m har.export_dashboard                       # both homes, day chosen automatically
    python -m har.export_dashboard --home aruba --day 2011-05-12

For each home:

1. Train Gradient Boosting + pre-segment context (the best model on the temporal
   split) on the first 70% of days only, exactly like ``run.py --split temporal``.
2. Pick one day from the remaining 30% (never seen in training). By default the
   day with the most distinct annotated activities.
3. Recognise every annotated activity segment of that day: predicted activity +
   confidence (the model's probability for its answer).
4. Write the day's real sensor events and the recognised activities to
   ``src/data/homes/generated/<home>.json`` in the dashboard's data shape.

Activity boundaries still come from the annotations (explicit segmentation),
as in every experiment so far; the dashboard does not yet do live segmentation.
The annotated activity is exported next to the prediction so every entry can be
checked by hand.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .data import DATASETS, ML_DIR, load_home
from .features import handcrafted_features
from .models import classical

OUT_DIR = ML_DIR.parent / "src" / "data" / "homes" / "generated"
STATE = {"ON": "active", "OFF": "inactive", "OPEN": "open", "CLOSE": "closed"}


def _clock(t) -> str:
    return pd.Timestamp(t).strftime("%H:%M:%S")


def pick_day(seg: pd.DataFrame, test_mask: np.ndarray) -> pd.Timestamp:
    days = seg.loc[test_mask, "start"].dt.normalize()
    stats = seg.loc[test_mask].groupby(days)["activity"].agg(["nunique", "size"])
    return stats.sort_values(["nunique", "size"], ascending=False).index[0]


def export_home(name: str, day: str | None, train_frac: float = 0.7, seed: int = 42) -> dict:
    home = load_home(name)
    seg = home.segments
    classes = home.activities
    y = seg["activity"].map({c: i for i, c in enumerate(classes)}).to_numpy()

    # Same split as run.py --split temporal.
    seg_day = seg["start"].dt.normalize()
    unique_days = np.sort(seg_day.unique())
    cutoff = unique_days[int(len(unique_days) * train_frac)]
    is_train = (seg_day < cutoff).to_numpy()

    the_day = pd.Timestamp(day) if day else pick_day(seg, ~is_train)
    if the_day < cutoff:
        raise SystemExit(f"{the_day.date()} is a training day; pick one on or after {pd.Timestamp(cutoff).date()}")
    on_day = (seg_day == the_day).to_numpy()
    if not on_day.any():
        raise SystemExit(f"No annotated activities on {the_day.date()}")

    X, _ = handcrafted_features(home, preceding=True)
    proba = classical.fit_predict_proba("hgb", X[is_train], y[is_train], X[on_day],
                                        seed, len(classes))
    pred = proba.argmax(1)

    # Real sensor events of that calendar day (motion, door, temperature).
    next_day = the_day + pd.Timedelta(days=1)
    t = pd.DatetimeIndex(home.times)
    in_day = (t >= the_day) & (t < next_day)
    events = [{"timestamp": _clock(ts), "sensorId": s, "state": STATE[v], "_t": ts}
              for ts, s, v in zip(t[in_day], home.sensors[in_day], home.states[in_day])]
    temp = home.temperature
    tt = temp[(temp["timestamp"] >= the_day) & (temp["timestamp"] < next_day)]
    events += [{"timestamp": _clock(ts), "sensorId": s, "state": float(v), "_t": ts}
               for ts, s, v in zip(tt["timestamp"], tt["sensor"], tt["value"])]
    events.sort(key=lambda e: e["_t"])
    for e in events:
        del e["_t"]

    history = []
    day_seg = seg[on_day]
    for k, (row, p, pr) in enumerate(zip(day_seg.itertuples(), pred, proba)):
        sensors = sorted(set(home.sensors[row.lo:row.hi]))
        history.append({
            "id": f"{name}-{the_day.date()}-{k}",
            "activityId": classes[p].lower(),
            "label": classes[p],
            "start": _clock(row.start),
            "end": _clock(row.end),
            "durationMinutes": round((row.end - row.start).total_seconds() / 60, 1),
            "confidence": round(float(pr[p]), 3),
            "sensorIds": sensors,
            "dayLabel": "Today",
            "annotatedActivityId": row.activity.lower(),
            "annotatedLabel": row.activity,
        })

    correct = int((pred == y[on_day]).sum())
    out = {
        "home": name,
        "date": str(the_day.date()),
        "model": "Gradient Boosting + pre-segment context",
        "trainedOn": f"{pd.Timestamp(unique_days[0]).date()} to "
                     f"{(pd.Timestamp(cutoff) - pd.Timedelta(days=1)).date()} "
                     f"({int(is_train.sum())} activities)",
        "correct": correct,
        "total": len(history),
        "events": events,
        "activityHistory": history,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.json"
    path.write_text(json.dumps(out, indent=1), encoding="utf8")

    print(f"[{name}] day {the_day.date()} (unseen; training ended {pd.Timestamp(cutoff).date()}): "
          f"{len(events)} sensor events, {len(history)} activities, "
          f"{correct}/{len(history)} recognised correctly -> {path}")
    for h in history:
        mark = "ok " if h["activityId"] == h["annotatedActivityId"] else "XX "
        print(f"   {mark}{h['start']}-{h['end']}  predicted {h['label']:<24} "
              f"({h['confidence']:.0%})  annotated {h['annotatedLabel']}")
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--home", default="all", choices=[*DATASETS, "all"])
    p.add_argument("--day", help="YYYY-MM-DD, must be in the test period (last 30%% of days)")
    args = p.parse_args(argv)
    for name in (list(DATASETS) if args.home == "all" else [args.home]):
        export_home(name, args.day if args.home != "all" else None)


if __name__ == "__main__":
    main()
