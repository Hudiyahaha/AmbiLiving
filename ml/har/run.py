"""Run HAR experiments.

Examples (from the ml/ directory):

    python -m har.run --dataset aruba --model rf
    python -m har.run --dataset milan --model bilstm --split temporal
    python -m har.run --dataset all --model all          # full comparison

Splits
------
cv        Stratified k-fold over segments (default, k=5). Comparable to most
          CASAS papers, but neighbouring segments from the same day can fall in
          train and test, which is mildly optimistic.
temporal  Train on the first 70% of days, test on the remaining 30%. Closer to
          deployment: the model never sees the future.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
from sklearn.model_selection import StratifiedKFold

from . import models
from .data import DATASETS, ML_DIR, load_home
from .evaluate import write_report
from .features import activity_history, encode_sequences, handcrafted_features
from .models import classical
from .train import fit_predict as fit_predict_sequence

RESULTS_DIR = ML_DIR / "results"


def make_splits(home, y, split: str, folds: int, seed: int, train_frac: float):
    if split == "cv":
        skf = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
        return list(skf.split(np.zeros(len(y)), y))
    if split == "temporal":
        days = home.segments["start"].dt.normalize()
        unique_days = np.sort(days.unique())
        cutoff = unique_days[int(len(unique_days) * train_frac)]
        is_train = (days < cutoff).to_numpy()
        return [(np.where(is_train)[0], np.where(~is_train)[0])]
    raise ValueError(split)


def fit_predict_with_history(model, home, X, y, tr, te, classes, seed, balance,
                             inner_folds: int = 3) -> np.ndarray:
    """Two-stage model: stage 1 recognises every segment from its own events, stage 2
    adds ``activity_history`` built from stage-1 *predictions* of earlier segments.

    No ground-truth label of any segment reaches the history features:
    training segments get out-of-fold stage-1 predictions (inner CV on the training
    fold), test segments get predictions from the stage-1 model trained on the whole
    training fold. This mirrors deployment, where only earlier recognitions are known.
    """
    labels = np.empty_like(y)
    inner = StratifiedKFold(n_splits=inner_folds, shuffle=True, random_state=seed)
    for itr, ite in inner.split(X[tr], y[tr]):
        labels[tr[ite]] = classical.fit_predict(model, X[tr[itr]], y[tr[itr]], X[tr[ite]],
                                                seed, balance)
    labels[te] = classical.fit_predict(model, X[tr], y[tr], X[te], seed, balance)
    H, _ = activity_history(home, labels, classes)
    XH = np.hstack([X, H])
    return classical.fit_predict(model, XH[tr], y[tr], XH[te], seed, balance)


def run_one(dataset: str, model: str, args) -> dict:
    home = load_home(dataset)
    classes = home.activities
    y = home.segments["activity"].map({c: i for i, c in enumerate(classes)}).to_numpy()
    splits = make_splits(home, y, args.split, args.folds, args.seed, args.train_frac)

    if args.history and model not in models.CLASSICAL:
        raise SystemExit("--history is only implemented for the classical models (rf, hgb)")
    if model in models.CLASSICAL:
        X, _ = handcrafted_features(home, preceding=args.context)
    else:
        seqs = encode_sequences(home, max_len=args.max_len, preceding=args.context)

    y_pred = np.full_like(y, -1)
    fold_ids = np.full_like(y, -1)
    t0 = time.time()
    for k, (tr, te) in enumerate(splits):
        print(f"  [{dataset}/{model}/{args.split}] fold {k + 1}/{len(splits)}: "
              f"{len(tr)} train, {len(te)} test")
        if model in models.CLASSICAL and args.history:
            y_pred[te] = fit_predict_with_history(model, home, X, y, tr, te, classes,
                                                  args.seed + k, args.balance)
        elif model in models.CLASSICAL:
            y_pred[te] = classical.fit_predict(model, X[tr], y[tr], X[te], args.seed + k,
                                               args.balance)
        else:
            y_pred[te] = fit_predict_sequence(
                model, seqs.subset(tr), y[tr], seqs.subset(te), len(classes),
                seed=args.seed + k, max_epochs=args.epochs, verbose=args.verbose,
            )
        fold_ids[te] = k
    seconds = time.time() - t0

    evaluated = fold_ids >= 0  # temporal split leaves training segments unevaluated
    tag = (model + ("+ctx" if args.context else "") + ("+hist" if args.history else "")
           + ("+bal" if args.balance == "full" and model == "hgb" else ""))
    out_dir = RESULTS_DIR / dataset / args.split / tag
    result = write_report(
        out_dir,
        dataset=dataset, model=tag, split=args.split, classes=classes,
        y_true=y[evaluated], y_pred=y_pred[evaluated], fold_ids=fold_ids[evaluated],
        segments=home.segments[evaluated], seconds=seconds,
        config={k: v for k, v in vars(args).items() if k not in ("dataset", "model")},
    )
    s = result["summary"]
    print(f"  => accuracy {s['accuracy']['mean']:.4f} ± {s['accuracy']['std']:.4f}   "
          f"macro-F1 {s['macro_f1']['mean']:.4f} ± {s['macro_f1']['std']:.4f}   "
          f"weighted-F1 {s['weighted_f1']['mean']:.4f}   ({seconds:.0f}s)  -> {out_dir}")
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset", default="aruba", choices=[*DATASETS, "all"])
    p.add_argument("--model", default="rf", choices=[*models.ALL, "all"])
    p.add_argument("--split", default="cv", choices=["cv", "temporal"])
    p.add_argument("--folds", type=int, default=5)
    p.add_argument("--train-frac", type=float, default=0.7, help="temporal split only")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--epochs", type=int, default=40, help="max epochs (early stopping)")
    p.add_argument("--max-len", type=int, default=128, help="events kept per segment")
    p.add_argument("--context", action="store_true",
                   help="add pre-segment context features (gap before, activity in previous 10 min)")
    p.add_argument("--history", action="store_true",
                   help="add features about earlier (predicted) activities; rf/hgb only")
    p.add_argument("--balance", default="sqrt", choices=["sqrt", "full"],
                   help="hgb class weighting: sqrt-inverse-frequency (default) or full inverse")
    p.add_argument("--verbose", action="store_true", help="print per-epoch progress")
    args = p.parse_args(argv)

    datasets = list(DATASETS) if args.dataset == "all" else [args.dataset]
    model_names = list(models.ALL) if args.model == "all" else [args.model]
    for ds in datasets:
        for m in model_names:
            run_one(ds, m, args)

    from .compare import write_summary
    print("\n" + write_summary())


if __name__ == "__main__":
    main()
