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

SUFFIXES = {
    "ctx": "pre-segment context",
    "hist": "activity history",
    "bal": "full class balancing",
}


def _approach(model: str) -> str:
    base, *tags = model.split("+")
    return " + ".join([APPROACH.get(base, base), *(SUFFIXES.get(t, t) for t in tags)])


def _fmt(s: dict, split: str = "cv") -> str:
    if split == "temporal":  # single hold-out: no spread to report
        return f"{s['mean'] * 100:.2f}"
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
        s, sp = r["summary"], r["split"]
        lines.append(
            f"| {_approach(r['model'])} | {_fmt(s['accuracy'], sp)} | "
            f"**{_fmt(s['macro_f1'], sp)}** | {_fmt(s['weighted_f1'], sp)} | "
            f"{_fmt(s['macro_precision'], sp)} | {_fmt(s['macro_recall'], sp)} | "
            f"{r['train_seconds']:.0f} |"
        )
    text = "\n".join(lines) + "\n"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "summary.md").write_text(text, encoding="utf8")
    return text


if __name__ == "__main__":
    print(write_summary())
