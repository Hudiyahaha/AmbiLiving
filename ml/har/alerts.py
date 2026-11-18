"""Alert routing: which routine deviations reach the caregiver, and how (decision D15).

Detection (``har.anomaly``) is deliberately sensitive. Routing decides delivery:

``notify``   push now — possible danger: long silence at home, very long bathroom /
             toilet visit, leaving home or cooking between 00:00 and 05:00, missed meds
``summary``  one evening message, at most 3 items by priority
``insight``  dashboard only — day-timeline and activity-order deviations

with a 2-hour cool-down per (type, activity) for notifications.

    python -m har.alerts          # -> results/alerts.md, results/<home>/anomaly/routing.json

Evaluated from the operating-point alert files written by ``har.run_anomaly``.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .anomaly import AWAY, BATHROOM, MEDS
from .anomaly_inject import COOKING
from .data import DATASETS
from .run import RESULTS_DIR

TIERS = ["notify", "summary", "insight"]
SEVERITY = {"notify": "high", "summary": "medium", "insight": "low"}
PRIORITY = ["missed", "prolonged", "frequency", "drift", "unusual_time"]
COOLDOWN = pd.Timedelta(hours=2)
SUMMARY_CAP = 3
URGENT = {"inactivity", "prolonged_bathroom", "unusual_time"}  # injected types that must notify
STREAMS = {"gt": "Annotations", "seg": "Segment GB", "win": "Live BiLSTM"}


def tier(kind: str, activity: str, time: pd.Timestamp) -> str:
    if kind == "inactivity":
        return "notify"
    if kind == "prolonged" and activity in BATHROOM:
        return "notify"
    if kind == "unusual_time" and time.hour < 5 and activity in AWAY | set(COOKING):
        return "notify"
    if kind == "missed" and activity in MEDS:
        return "notify"
    if kind in ("timeline", "unusual_order", "outlier"):
        return "insight"
    return "summary"


def route(alerts: pd.DataFrame) -> pd.DataFrame:
    """Add ``tier`` and ``delivered`` (after cool-down and the daily summary cap)."""
    a = alerts.copy()
    a["time"] = pd.to_datetime(a["time"])
    a["tier"] = [tier(k, act, t) for k, act, t in zip(a["kind"], a["activity"], a["time"])]
    a = a.sort_values(["vid", "time"]).reset_index(drop=True)
    delivered = np.ones(len(a), bool)
    # cool-down for notifications
    last: dict[tuple, pd.Timestamp] = {}
    for i, r in a[a["tier"] == "notify"].iterrows():
        key = (r["vid"], r["kind"], r["activity"])
        if key in last and r["time"] - last[key] < COOLDOWN:
            delivered[i] = False
        else:
            last[key] = r["time"]
    # daily summary cap, by priority then time
    s = a[a["tier"] == "summary"].copy()
    s["prio"] = s["kind"].map({k: i for i, k in enumerate(PRIORITY)}).fillna(len(PRIORITY))
    for _, grp in s.groupby("vid"):
        keep = grp.sort_values(["prio", "time"]).index[:SUMMARY_CAP]
        delivered[grp.index.difference(keep)] = False
    a["delivered"] = delivered
    return a


def _injected_type(kind: str, target: str) -> str:
    if kind == "prolonged":
        return "prolonged_bathroom" if target in BATHROOM else "prolonged_other"
    return kind


def _matched(a: pd.DataFrame, inj) -> pd.DataFrame:
    """Delivered alerts on this day copy that explain the injected deviation (D13 rule)."""
    day = a[(a["vid"] == inj.vid) & a["delivered"]]
    if inj.kind == "missed":
        return day[(day["kind"] == "missed") & (day["activity"] == inj.target)]
    lo = pd.Timestamp(inj.start) - pd.Timedelta(minutes=30)
    hi = pd.Timestamp(inj.end) + pd.Timedelta(minutes=60)
    return day[(day["time"] >= lo) & (day["time"] <= hi)]


def evaluate(home: str, stream: str, method: str = "routine") -> dict:
    d = RESULTS_DIR / home / "anomaly"
    a = route(pd.read_csv(d / f"alerts_{stream}_{method}.csv"))
    inj = pd.read_csv(d / "injections.csv")
    clean = inj[inj["kind"] == "clean"]
    n_clean = len(clean)
    on_clean = a[a["vid"].isin(clean["vid"]) & a["delivered"]]
    out = {"per_clean_day": {t: float((on_clean["tier"] == t).sum() / n_clean) for t in TIERS},
           "clean_days_with_notification": float(
               on_clean[on_clean["tier"] == "notify"]["vid"].nunique() / n_clean),
           "types": {}}
    rows = []
    for r in inj[~inj["kind"].isin(["clean", "drift"])].itertuples():
        m = _matched(a, r)
        t = _injected_type(r.kind, r.target)
        notified = m[m["tier"] == "notify"]
        rows.append({"type": t, "notified": len(notified) > 0,
                     "surfaced": len(m[m["tier"].isin(["notify", "summary"])]) > 0,
                     "delay": (notified["time"].min() - pd.Timestamp(r.start)).total_seconds() / 60
                     if len(notified) else np.nan})
    rows = pd.DataFrame(rows)
    for t, g in rows.groupby("type"):
        out["types"][t] = {"n": int(len(g)), "urgent": t in URGENT,
                           "notified": float(g["notified"].mean()),
                           "surfaced": float(g["surfaced"].mean()),
                           "median_notify_delay_min": float(g["delay"].median())
                           if g["notified"].any() else None}
    urg = rows[rows["type"].isin(URGENT)]
    non = rows[~rows["type"].isin(URGENT)]
    out["urgent_notified"] = float(urg["notified"].mean()) if len(urg) else None
    out["non_urgent_surfaced"] = float(non["surfaced"].mean()) if len(non) else None
    return out


def main():
    lines = ["# Alert routing results", "",
             "Generated by `python -m har.alerts` (decision D15) from the routine model's "
             "operating-point alerts (0.1 alerts per normal day per aspect). Detection is "
             "unchanged; routing decides what reaches the caregiver: **notify** (push now), "
             "**summary** (evening message, max 3) or **insight** (dashboard only).", "",
             "*Urgent* injected deviations: long inactivity, prolonged bathroom/toilet visit, "
             "leaving home or cooking at night — they should **notify**. *Non-urgent*: missed meal, "
             "other prolonged activity, extra night toilet trips — they should appear in the "
             "notification or the summary.", ""]
    for home in DATASETS:
        res = {s: evaluate(home, s) for s in STREAMS
               if (RESULTS_DIR / home / "anomaly" / f"alerts_{s}_routine.csv").exists()}
        (RESULTS_DIR / home / "anomaly" / "routing.json").write_text(json.dumps(res, indent=2))
        lines += [f"## {home.capitalize()}", "",
                  "| Activity stream | Notifications / clean day | Clean days with a notification "
                  "| Summary items / clean day | Insights / clean day | Urgent deviations notified "
                  "| Median notify delay (min) | Non-urgent surfaced |",
                  "|---|---|---|---|---|---|---|---|"]
        for s, r in res.items():
            urg = [r["types"][t] for t in r["types"] if r["types"][t]["urgent"]]
            delays = [u["median_notify_delay_min"] for u in urg if u["median_notify_delay_min"]]
            lines.append(
                f"| {STREAMS[s]} | {r['per_clean_day']['notify']:.2f} | "
                f"{100 * r['clean_days_with_notification']:.0f} % | "
                f"{r['per_clean_day']['summary']:.2f} | {r['per_clean_day']['insight']:.2f} | "
                f"**{100 * r['urgent_notified']:.0f} %** | "
                f"{np.median(delays):.0f} | {100 * r['non_urgent_surfaced']:.0f} % |"
                if delays else
                f"| {STREAMS[s]} | {r['per_clean_day']['notify']:.2f} | "
                f"{100 * r['clean_days_with_notification']:.0f} % | "
                f"{r['per_clean_day']['summary']:.2f} | {r['per_clean_day']['insight']:.2f} | "
                f"**{100 * r['urgent_notified']:.0f} %** | – | "
                f"{100 * r['non_urgent_surfaced']:.0f} % |")
        lines += ["", "Per injected type (notified / surfaced in notify or summary):", "",
                  "| Activity stream | " + " | ".join(
                      t.replace("_", " ") for t in next(iter(res.values()))["types"]) + " |",
                  "|---|" + "---|" * len(next(iter(res.values()))["types"])]
        for s, r in res.items():
            lines.append(f"| {STREAMS[s]} | " + " | ".join(
                f"{100 * v['notified']:.0f} / {100 * v['surfaced']:.0f}"
                for v in r["types"].values()) + " |")
        lines.append("")
    (RESULTS_DIR / "alerts.md").write_text("\n".join(lines), encoding="utf8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
