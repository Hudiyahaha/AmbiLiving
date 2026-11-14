"""Sliding-window activity recognition on the raw event stream.

Protocol (raw-stream setting of LastAct, Liu et al. 2026, for comparability):

* every sample is the last ``--size`` events (default 100);
* chronological split by days: first 60% train, last 20% test
  (the 20% in between is LastAct's validation period and is not used here);
* training windows every ``--train-stride`` events (default 50),
  test windows at every event (``--test-stride 1``), i.e. one prediction per event;
* label = activity of the most recent annotated event (``--label last``),
  or "Other" for unannotated events (``--label other``, the product setting);
* macro-F1 over the activities present in the test period.

Examples (from ml/):

    python -m har.run_windows --dataset aruba --model hgb --context
    python -m har.run_windows --dataset all --model hgb --context --label other
    python -m har.run_windows --dataset milan --model bilstm --test-stride 10 --seeds 1 2 3

Results go to results/<dataset>/window<size>-<label>/<model>/.
"""

from __future__ import annotations

import argparse
import gzip
import shutil
import time

import numpy as np

from . import models
from .data import DATASETS, load_home
from .evaluate import write_report
from .features import encode_sequences, handcrafted_features
from .models import classical
from .run import RESULTS_DIR
from .train import fit_predict as fit_predict_sequence
from .window_history import history_features, stream_predictions
from .windows import OTHER, day_split, make_windows


def smooth_causal(proba: np.ndarray, k: int) -> np.ndarray:
    """Average each window's class probabilities with the previous k-1 windows.

    Uses only past predictions, so it can run live. Test windows are in event
    order, one per event (or per ``--test-stride`` events), so k windows cover
    the last k (or k * stride) events. Activities last minutes, so a single
    window that disagrees with its neighbours is usually noise.
    """
    c = np.cumsum(proba, axis=0)
    out = c.copy()
    out[k:] = c[k:] - c[:-k]
    n = np.minimum(np.arange(1, len(proba) + 1), k)[:, None]
    return out / n


def build(home, args):
    train_end, test_start, train_cut, test_cut = day_split(home, args.train_frac, args.test_frac)
    n = len(home.times)
    train = make_windows(home, np.arange(args.size, train_end + 1, args.train_stride),
                         args.size, args.label)
    test = make_windows(home, np.arange(test_start + 1, n + 1, args.test_stride),
                        args.size, args.label)
    return train, test, train_cut, test_cut, train_end


def features(wh, model, args):
    if model in models.CLASSICAL:
        X, _ = handcrafted_features(wh, preceding=args.context)
        return X
    return encode_sequences(wh, max_len=max(args.size, 8), preceding=args.context)


def run_one(dataset: str, model: str, seed: int, args) -> dict:
    home = load_home(dataset)
    train, test, train_cut, test_cut, train_end = build(home, args)
    classes = home.activities + ([OTHER] if args.label == "other" else [])
    cidx = {c: i for i, c in enumerate(classes)}
    y_tr = train.segments["activity"].map(cidx).to_numpy()
    y_te = test.segments["activity"].map(cidx).to_numpy()
    # A class with a single training window cannot be learned (and breaks HGB's
    # stratified early-stopping split). Drop it from training only; its test
    # windows stay in the evaluation and count as misses.
    counts = np.bincount(y_tr, minlength=len(classes))
    keep = counts[y_tr] >= 2
    if not keep.all():
        dropped = [classes[c] for c in np.where((counts > 0) & (counts < 2))[0]]
        print(f"  dropping from training (fewer than 2 windows): {dropped}")
        train = make_windows(home, train.segments["hi"].to_numpy()[keep], args.size, args.label)
        y_tr = y_tr[keep]
    print(f"  [{dataset}/{model}/window{args.size}-{args.label}] train {len(y_tr):,} windows "
          f"(days before {train_cut.date()}), test {len(y_te):,} windows "
          f"(days from {test_cut.date()})")

    t0 = time.time()
    X_tr, X_te = features(train, model, args), features(test, model, args)
    if args.history:
        # Stage 1 is always the gradient-boosting model on handcrafted features;
        # its prediction stream is turned into history features for stage 2.
        hi_tr = train.segments["hi"].to_numpy()
        X1 = X_tr if model in models.CLASSICAL else handcrafted_features(train, preceding=False)[0]
        s_ends, s_lab = stream_predictions(home, hi_tr, y_tr, X1, train_end, args.size,
                                           args.history_step, len(classes), args.label, seed)
        H_tr, _ = history_features(home, hi_tr, s_ends, s_lab, classes, args.min_run,
                                   ongoing=args.history_mode == "full")
        H_te, _ = history_features(home, test.segments["hi"].to_numpy(), s_ends, s_lab,
                                   classes, args.min_run, ongoing=args.history_mode == "full")
        if model in models.CLASSICAL:
            X_tr, X_te = np.hstack([X_tr, H_tr]), np.hstack([X_te, H_te])
        else:  # sequence models read history next to the window's context vector
            X_tr.context = np.hstack([X_tr.context, H_tr]).astype(np.float32)
            X_te.context = np.hstack([X_te.context, H_te]).astype(np.float32)
    if model in models.CLASSICAL:
        proba = classical.fit_predict_proba(model, X_tr, y_tr, X_te, seed, len(classes),
                                            args.balance)
    else:
        proba = fit_predict_sequence(
            model, X_tr, y_tr, X_te, len(classes), seed=seed, max_epochs=args.epochs,
            verbose=args.verbose, return_proba=True,
        )
    if args.smooth > 1:
        proba = smooth_causal(proba, args.smooth)
    seconds = time.time() - t0

    tag = (model + ("+ctx" if args.context else "")
           + (("+hist" if args.history_mode == "full" else "+histpast") if args.history else "")
           + ("+bal" if args.balance == "full" else "")
           + (f"+tr{args.train_stride}" if args.train_stride != 50 else "")
           + (f"+te{args.test_stride}" if args.test_stride != 1 else "")
           + (f"+sm{args.smooth}" if args.smooth > 1 else ""))
    split = f"window{args.size}-{args.label}"
    out_dir = RESULTS_DIR / dataset / split / tag
    if args.run_seed is not None:
        out_dir = RESULTS_DIR / dataset / split / "experiments" / f"{tag}+s{seed}"
        tag += f"+s{seed}"
    result = write_report(
        out_dir, dataset=dataset, model=tag, split=split, classes=classes,
        y_true=y_te, y_pred=proba.argmax(1), fold_ids=np.zeros(len(y_te), int),
        confidence=proba.max(1), segments=test.segments, seconds=seconds,
        config={k: v for k, v in vars(args).items() if k not in ("dataset", "model")}
        | {"train_windows": int(len(y_tr)), "test_windows": int(len(y_te)),
           "train_until": str(train_cut.date()), "test_from": str(test_cut.date())},
    )
    # One prediction per event makes predictions.csv large; keep it compressed.
    csv = out_dir / "predictions.csv"
    with open(csv, "rb") as f_in, gzip.open(str(csv) + ".gz", "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    csv.unlink()
    s = result["summary"]
    print(f"  => accuracy {s['accuracy']['mean']:.4f}   macro-F1 {s['macro_f1']['mean']:.4f}   "
          f"weighted-F1 {s['weighted_f1']['mean']:.4f}   ({seconds:.0f}s)  -> {out_dir}")
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset", default="aruba", choices=[*DATASETS, "all"])
    p.add_argument("--model", default="hgb", choices=[*models.ALL, "all"])
    p.add_argument("--size", type=int, default=100, help="events per window")
    p.add_argument("--train-stride", type=int, default=50)
    p.add_argument("--test-stride", type=int, default=1)
    p.add_argument("--label", default="last", choices=["last", "other"])
    p.add_argument("--train-frac", type=float, default=0.6)
    p.add_argument("--test-frac", type=float, default=0.2)
    p.add_argument("--context", action="store_true",
                   help="add the past-only context features (activity in the 10 min before)")
    p.add_argument("--balance", default="sqrt", choices=["sqrt", "full"])
    p.add_argument("--history", action="store_true",
                   help="add routine-history features built from stage-1 (hgb) predictions")
    p.add_argument("--history-mode", default="full", choices=["full", "past"],
                   help="full: include the activity in progress; past: completed activities only")
    p.add_argument("--history-step", type=int, default=10,
                   help="stage-1 prediction every N events for the history stream")
    p.add_argument("--min-run", type=int, default=3,
                   help="stream points a predicted activity must last to count as an episode")
    p.add_argument("--smooth", type=int, default=1,
                   help="average predictions over the last k test windows (past only); 1 = off")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--seeds", type=int, nargs="+", help="repeat once per seed")
    p.add_argument("--epochs", type=int, default=40)
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args(argv)

    datasets = list(DATASETS) if args.dataset == "all" else [args.dataset]
    model_names = list(models.ALL) if args.model == "all" else [args.model]
    for ds in datasets:
        for m in model_names:
            for seed in (args.seeds or [args.seed]):
                args.run_seed = seed if args.seeds else None
                run_one(ds, m, seed, args)


if __name__ == "__main__":
    main()
