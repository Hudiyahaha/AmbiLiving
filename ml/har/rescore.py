"""Recompute the metrics of every saved run from its predictions.csv.

    python -m har.rescore

Use this after a change to how metrics are computed (``evaluate.scalar_metrics``):
no model is retrained. For every ``results/**/metrics.json`` it re-reads the
true and predicted labels, rewrites the per-fold / summary / pooled scores,
redraws ``confusion.png`` with the new score in its title, and then rebuilds
``results/summary.md`` and ``results/experiments.md``.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .compare import write_summary
from .data import ML_DIR
from .evaluate import MACRO_OVER, SCALARS, plot_confusion, scalar_metrics
from .experiments import write_experiments

RESULTS_DIR = ML_DIR / "results"


def rescore_all() -> list[tuple[str, float, float]]:
    changed = []
    for path in sorted(RESULTS_DIR.glob("**/metrics.json")):
        run_dir = path.parent
        preds_path = run_dir / "predictions.csv"
        if not preds_path.exists():
            continue
        r = json.loads(path.read_text())
        index = {c: i for i, c in enumerate(r["classes"])}
        preds = pd.read_csv(preds_path)
        y_true = preds["true"].map(index).to_numpy()
        y_pred = preds["pred"].map(index).to_numpy()
        fold_ids = preds["fold"].to_numpy()

        folds = [scalar_metrics(y_true[fold_ids == k], y_pred[fold_ids == k])
                 for k in np.unique(fold_ids)]
        old = r["summary"]["macro_f1"]["mean"]
        r["per_fold"] = folds
        r["summary"] = {m: {"mean": float(np.mean([f[m] for f in folds])),
                            "std": float(np.std([f[m] for f in folds]))} for m in SCALARS}
        r["pooled"] = scalar_metrics(y_true, y_pred)
        r["macro_over"] = MACRO_OVER
        path.write_text(json.dumps(r, indent=2))

        new = r["summary"]["macro_f1"]["mean"]
        if abs(new - old) > 1e-9:
            plot_confusion(
                y_true, y_pred, r["classes"],
                f"{r['dataset']} / {r['model']} / {r['split']}  -  macro-F1 {new:.3f}",
                run_dir / "confusion.png",
            )
            changed.append((str(run_dir.relative_to(RESULTS_DIR)), old, new))
    return changed


def main():
    changed = rescore_all()
    print(f"{len(changed)} runs changed (macro scores now average over {MACRO_OVER}):")
    for name, old, new in changed:
        print(f"  {name:55s} macro-F1 {old * 100:6.2f} -> {new * 100:6.2f}")
    write_summary()
    write_experiments()
    print("\nRebuilt results/summary.md and results/experiments.md")


if __name__ == "__main__":
    main()
