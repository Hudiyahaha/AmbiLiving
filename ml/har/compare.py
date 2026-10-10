"""Collect every results/*/*/*/metrics.json into results/summary.md.

    python -m har.compare
"""

from __future__ import annotations

import json

from .data import ML_DIR

RESULTS_DIR = ML_DIR / "results"

APPROACH = {
    "rf": "1 - Features + Random Forest",
    "hgb": "1 - Features + Gradient Boosting",
    "bilstm": "2 - BiLSTM",
    "cnn": "3 - 1D-CNN",
    "transformer": "3 - Transformer",
}

CTX_SUFFIX = " + pre-segment context"


def _approach(model: str) -> str:
    base, ctx = model.removesuffix("+ctx"), model.endswith("+ctx")
    return APPROACH.get(base, base) + (CTX_SUFFIX if ctx else "")


def _fmt(s: dict) -> str:
    return f"{s['mean'] * 100:.2f} ± {s['std'] * 100:.2f}"


def write_summary() -> str:
    rows = []
    for path in sorted(RESULTS_DIR.glob("*/*/*/metrics.json")):
        r = json.loads(path.read_text())
        rows.append(r)
    rows.sort(key=lambda r: (r["dataset"], r["split"], -r["summary"]["macro_f1"]["mean"]))

    lines = ["# HAR results", "",
             "Mean ± std over folds (cv) or single hold-out (temporal). Values in %.",
             "Macro-F1 is the headline metric: it weights every activity equally, so it",
             "is not inflated by the majority classes (Relax, Meal_Preparation, ...).", ""]
    current = None
    for r in rows:
        key = (r["dataset"], r["split"])
        if key != current:
            current = key
            lines += ["", f"## {r['dataset']} - {r['split']} ({r['n_segments']} test segments, "
                          f"{r['n_classes']} classes)", "",
                      "| Approach | Accuracy | Macro-F1 | Weighted-F1 | Macro-P | Macro-R | Time (s) |",
                      "|---|---|---|---|---|---|---|"]
        s = r["summary"]
        lines.append(
            f"| {_approach(r['model'])} | {_fmt(s['accuracy'])} | "
            f"**{_fmt(s['macro_f1'])}** | {_fmt(s['weighted_f1'])} | "
            f"{_fmt(s['macro_precision'])} | {_fmt(s['macro_recall'])} | {r['train_seconds']:.0f} |"
        )
    text = "\n".join(lines) + "\n"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "summary.md").write_text(text, encoding="utf8")
    return text


if __name__ == "__main__":
    print(write_summary())
