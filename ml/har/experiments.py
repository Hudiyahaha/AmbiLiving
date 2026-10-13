"""Summarise tuning / repeated-seed runs into results/experiments.md.

    python -m har.experiments

Runs started with ``--tag`` or ``--seeds`` are saved under
``results/<dataset>/<split>/experiments/<model>[+ctx][+tag][+s<seed>]/``.
Runs that differ only in their seed are grouped, and the table reports the
mean ± std over seeds, so a 1-2 point difference between two settings can be
checked against run-to-run noise before it is reported.

These runs are kept out of results/summary.md (``har.compare``), which stays
the main one-run-per-approach comparison table.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict

import numpy as np

from .data import ML_DIR

RESULTS_DIR = ML_DIR / "results"
SEED_RE = re.compile(r"\+s\d+$")


def _mean_std(values: list[float]) -> str:
    v = np.array(values) * 100
    return f"{v.mean():.2f} ± {v.std():.2f}" if len(v) > 1 else f"{v[0]:.2f}"


def write_experiments() -> str:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for path in sorted(RESULTS_DIR.glob("*/*/experiments/*/metrics.json")):
        r = json.loads(path.read_text())
        groups[(r["dataset"], r["split"], SEED_RE.sub("", r["model"]))].append(r)

    lines = ["# Tuning and repeated-seed runs", "",
             "Mean ± std over seeds (n = number of seeds). Values in %. For cv runs each",
             "seed's score is itself the mean over folds. Settings not shown in the",
             "name are the defaults: lr 1e-3, patience 6, batch size 64.", ""]
    current = None
    rows = sorted(groups.items(), key=lambda kv: (
        kv[0][0], kv[0][1], -np.mean([r["summary"]["macro_f1"]["mean"] for r in kv[1]])))
    for (dataset, split, name), runs in rows:
        if (dataset, split) != current:
            current = (dataset, split)
            lines += ["", f"## {dataset} - {split}", "",
                      "| Run | n | Macro-F1 | Accuracy | Weighted-F1 | Time per run (s) |",
                      "|---|---|---|---|---|---|"]
        f1 = [r["summary"]["macro_f1"]["mean"] for r in runs]
        acc = [r["summary"]["accuracy"]["mean"] for r in runs]
        wf1 = [r["summary"]["weighted_f1"]["mean"] for r in runs]
        secs = np.mean([r["train_seconds"] for r in runs])
        lines.append(f"| {name} | {len(runs)} | **{_mean_std(f1)}** | {_mean_std(acc)} | "
                     f"{_mean_std(wf1)} | {secs:.0f} |")
    if current is None:
        lines.append("No experiment runs yet. Start one with --seeds or --tag (see har/run.py).")

    text = "\n".join(lines) + "\n"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "experiments.md").write_text(text, encoding="utf8")
    return text


if __name__ == "__main__":
    print(write_experiments())
