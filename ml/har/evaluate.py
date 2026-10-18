"""Metrics, reports and plots for one experiment (dataset x model x split)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    precision_score,
    recall_score,
)

SCALARS = ("accuracy", "macro_f1", "weighted_f1", "macro_precision", "macro_recall")


MACRO_OVER = "activities present in the test fold"


def scalar_metrics(y_true, y_pred) -> dict[str, float]:
    """Macro scores average over the activities that occur in the test fold.

    sklearn's default averages over every label in y_true *or* y_pred. On the
    temporal split some activities have no test instances at all (Aruba
    Housekeeping, Milan Chores: their labels stop part-way through the
    recording). With the default, a single false prediction of such an
    activity adds a class with F1 = 0 and drops macro-F1 by ~8 points, so the
    score depended on whether a model happened to make that one mistake.
    Such a mistake is still penalised: the segment is a missed instance of
    its true activity, which lowers that activity's recall and F1.
    """
    labels = np.unique(y_true)
    macro = dict(labels=labels, average="macro", zero_division=0)
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "macro_f1": f1_score(y_true, y_pred, **macro),
        "weighted_f1": f1_score(y_true, y_pred, average="weighted", zero_division=0),
        "macro_precision": precision_score(y_true, y_pred, **macro),
        "macro_recall": recall_score(y_true, y_pred, **macro),
    }


def confidence_summary(y_true, y_pred, confidence, thresholds=(0.6, 0.8)) -> dict:
    """How sure the model was, and whether low confidence flags its mistakes.

    For each threshold: share of predictions below it, and accuracy of the
    predictions at or above it (what an "Unknown below X%" rule would keep).
    """
    right = y_true == y_pred
    out = {
        "mean_when_correct": float(confidence[right].mean()) if right.any() else None,
        "mean_when_wrong": float(confidence[~right].mean()) if (~right).any() else None,
    }
    for th in thresholds:
        keep = confidence >= th
        out[f"below_{th}"] = float((~keep).mean())
        out[f"accuracy_at_or_above_{th}"] = float(right[keep].mean()) if keep.any() else None
        out[f"wrong_caught_below_{th}"] = float((~keep[~right]).mean()) if (~right).any() else None
    return out


def per_class_table(y_true, y_pred, classes: list[str]) -> pd.DataFrame:
    labels = np.arange(len(classes))
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    return pd.DataFrame(
        {"activity": classes, "precision": p, "recall": r, "f1": f, "support": s}
    ).sort_values("support", ascending=False)


def plot_confusion(y_true, y_pred, classes: list[str], title: str, path: Path) -> None:
    cm = confusion_matrix(y_true, y_pred, labels=np.arange(len(classes)))
    norm = cm / np.maximum(cm.sum(1, keepdims=True), 1)
    n = len(classes)
    fig, ax = plt.subplots(figsize=(0.62 * n + 3, 0.55 * n + 2.5))
    im = ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(n), classes, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(n), classes, fontsize=9)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(title, fontsize=11)
    for i in range(n):
        for j in range(n):
            if cm[i, j]:
                ax.text(j, i, f"{norm[i, j]:.2f}\n({cm[i, j]})", ha="center", va="center",
                        fontsize=6.5, color="white" if norm[i, j] > 0.55 else "#1f2937")
    fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02, label="Row-normalised recall")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def write_report(
    out_dir: Path,
    *,
    dataset: str,
    model: str,
    split: str,
    classes: list[str],
    y_true: np.ndarray,
    y_pred: np.ndarray,
    fold_ids: np.ndarray,
    segments: pd.DataFrame,
    config: dict,
    seconds: float,
    confidence: np.ndarray | None = None,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    folds = [scalar_metrics(y_true[fold_ids == k], y_pred[fold_ids == k])
             for k in np.unique(fold_ids)]
    summary = {
        m: {"mean": float(np.mean([f[m] for f in folds])),
            "std": float(np.std([f[m] for f in folds]))}
        for m in SCALARS
    }
    pooled = scalar_metrics(y_true, y_pred)
    per_class = per_class_table(y_true, y_pred, classes)

    result = {
        "dataset": dataset,
        "model": model,
        "split": split,
        "n_segments": int(len(y_true)),
        "n_classes": len(classes),
        "classes": classes,
        "per_fold": folds,
        "summary": summary,
        "pooled": pooled,
        "macro_over": MACRO_OVER,
        "config": config,
        "train_seconds": round(seconds, 1),
    }
    if confidence is not None:
        result["confidence"] = confidence_summary(y_true, y_pred, confidence)
    (out_dir / "metrics.json").write_text(json.dumps(result, indent=2))
    per_class.round(4).to_csv(out_dir / "per_class.csv", index=False)
    pd.DataFrame(
        {
            "start": segments["start"].to_numpy(),
            "end": segments["end"].to_numpy(),
            "fold": fold_ids,
            "true": np.asarray(classes)[y_true],
            "pred": np.asarray(classes)[y_pred],
            **({"confidence": np.round(confidence, 4)} if confidence is not None else {}),
        }
    ).to_csv(out_dir / "predictions.csv", index=False)
    plot_confusion(
        y_true, y_pred, classes,
        f"{dataset} / {model} / {split}  -  macro-F1 {summary['macro_f1']['mean']:.3f}",
        out_dir / "confusion.png",
    )
    return result
