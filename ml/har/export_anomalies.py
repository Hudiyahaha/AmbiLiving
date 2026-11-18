"""Export routine deviations found on real days to the dashboard.

    python -m har.export_anomalies

Takes the alerts the resident's routine model raised on the **clean** monitoring
days (real CASAS days, nothing injected) for the segment recogniser — the
same Gradient Boosting + context model the dashboard's activity history uses —
at the operating point (0.1 alerts per normal day per score). Writes
``src/data/homes/generated/<home>-anomalies.json`` in the dashboard's
``AnomalyRecord`` shape.

Run ``python -m har.run_anomaly`` first.
"""

from __future__ import annotations

import argparse
import json

import pandas as pd

from .data import DATASETS
from .export_dashboard import OUT_DIR
from .run import RESULTS_DIR


def export(home: str, stream: str, method: str) -> None:
    d = RESULTS_DIR / home / "anomaly"
    alerts = pd.read_csv(d / f"alerts_{stream}_{method}.csv", parse_dates=["time"])
    alerts = alerts[alerts["day_kind"] == "clean"].sort_values("time", ascending=False)
    summary = json.loads((d / "summary.json").read_text())
    days = pd.read_csv(d / "injections.csv")
    clean = pd.to_datetime(days.loc[days["kind"] == "clean", "day"])
    records = []
    for i, a in enumerate(alerts.itertuples()):
        records.append({
            "id": f"{home}-anomaly-{i + 1}",
            "title": a.title,
            "observed": a.observed,
            "expected": a.expected,
            "reason": a.reason,
            "severity": a.severity,
            "timestamp": f"{a.time:%a %d %b %Y} · {a.time:%H:%M}",
            "requiresAttention": a.severity != "low",
            "kind": a.kind,
        })
    r = summary["results"][f"{stream}/{method}"]
    out = {
        "detector": "Routine model" if method == "routine" else "Generic anomaly detector",
        "recogniser": "Gradient Boosting + context" if stream == "seg" else stream,
        "routineLearnedFrom": f"{summary['n_observation_days']} observation days",
        "period": f"{clean.min():%d %b %Y} – {clean.max():%d %b %Y}",
        "days": int(len(clean)),
        "falseAlertsPerDay": round(r["false_alerts_per_day"], 2),
        "detectionRate": round(r["mean_detection_rate"], 3),
        "anomalies": records,
    }
    path = OUT_DIR / f"{home}-anomalies.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf8")
    print(f"{home}: {len(records)} anomalies on {len(clean)} real days -> {path}")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--stream", default="seg", choices=["gt", "seg", "win"])
    p.add_argument("--method", default="routine", choices=["routine", "generic"])
    args = p.parse_args(argv)
    for home in DATASETS:
        export(home, args.stream, args.method)


if __name__ == "__main__":
    main()
