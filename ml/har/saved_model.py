"""Save and load the final window model so other parts can use it without retraining.

A saved file holds everything needed to predict on new sensor events: the network
weights, the context normalisation, the token vocabulary, the class list and the
window settings. Training uses only the training days (first 60 %), with the same
data, split and seed as ``har.run_windows``, so a saved model reproduces the
reported test predictions.

Train and save (from ml/):

    python -m har.saved_model --dataset all --model bilstm --seed 1

Use it:

    from har.saved_model import load
    wm = load("models/aruba/window100-bilstm-s1.pt")
    proba = wm.predict_proba(home, window_ends)   # one row per window end

``--check`` reloads the file and compares its test predictions with the stored
``results/<home>/window100-last/experiments/<model>+s<seed>/predictions.csv.gz``.
"""

from __future__ import annotations

import argparse
import gzip
import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from . import models
from .data import DATASETS, ML_DIR, Home, load_home
from .features import encode_sequences
from .models import sequence
from .run import RESULTS_DIR
from .train import Trained, fit, predict_proba
from .windows import day_split, make_windows

MODELS_DIR = ML_DIR / "models"
FORMAT = 1


@dataclass
class WindowModel:
    """A trained window classifier plus what it needs to read new events."""

    trained: Trained
    name: str
    dataset: str
    classes: list[str]
    vocab: list[str]
    size: int
    meta: dict

    def predict_proba(self, home: Home, window_ends: np.ndarray) -> np.ndarray:
        """Class probabilities for the windows ending at ``window_ends`` (event index, exclusive).

        Each window is the ``size`` events before its end. Sensor/state pairs the
        model never saw are mapped to padding, so a new home with extra sensors
        does not crash (those events are simply ignored).
        """
        ends = np.asarray(window_ends)
        if len(ends) and ends.min() < self.size:
            raise ValueError(f"a window needs {self.size} earlier events; got an end at {ends.min()}")
        wh = make_windows(home, ends, self.size, "other")  # labels are not used
        data = encode_sequences(wh, max_len=self.size)
        if data.vocab != self.vocab:
            pos = {t: i for i, t in enumerate(self.vocab)}
            remap = np.array([pos.get(t, 0) for t in data.vocab], np.int64)
            data.tokens = remap[data.tokens]
            data.mask &= data.tokens != 0
            data.vocab = self.vocab
        return predict_proba(self.trained, data)

    def predict(self, home: Home, window_ends: np.ndarray) -> tuple[list[str], np.ndarray]:
        """Predicted activity name and confidence for each window."""
        p = self.predict_proba(home, window_ends)
        return [self.classes[i] for i in p.argmax(1)], p.max(1)


def model_path(dataset: str, name: str, seed: int, size: int = 100) -> Path:
    return MODELS_DIR / dataset / f"window{size}-{name}-s{seed}.pt"


def train_and_save(dataset: str, name: str = "bilstm", seed: int = 1, size: int = 100,
                   train_stride: int = 50, train_frac: float = 0.6, test_frac: float = 0.2,
                   epochs: int = 40, verbose: bool = False) -> Path:
    """Train on the training days only and write the model file. Returns its path."""
    if name in models.CLASSICAL:
        raise SystemExit("only the sequence models (bilstm, cnn, transformer) can be saved")
    home = load_home(dataset)
    train_end, _, train_cut, test_cut = day_split(home, train_frac, test_frac)
    tw = make_windows(home, np.arange(size, train_end + 1, train_stride), size, "last")
    classes = home.activities
    cidx = {c: i for i, c in enumerate(classes)}
    y = tw.segments["activity"].map(cidx).to_numpy()
    counts = np.bincount(y, minlength=len(classes))
    keep = counts[y] >= 2  # same rule as run_windows
    if not keep.all():
        tw = make_windows(home, tw.segments["hi"].to_numpy()[keep], size, "last")
        y = y[keep]
    X = encode_sequences(tw, max_len=max(size, 8))

    t0 = time.time()
    trained = fit(name, X, y, len(classes), seed, max_epochs=epochs, verbose=verbose)
    meta = {
        "format": FORMAT, "model": name, "dataset": dataset, "seed": seed, "size": size,
        "label_rule": "last", "train_stride": train_stride, "train_frac": train_frac,
        "test_frac": test_frac, "train_until": str(train_cut.date()),
        "test_from": str(test_cut.date()), "train_windows": int(len(y)),
        "n_cont": int(X.cont.shape[-1]), "n_context": int(X.context.shape[-1]),
        "train_seconds": round(time.time() - t0, 1),
    }
    path = model_path(dataset, name, seed, size)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"meta": meta, "classes": classes, "vocab": X.vocab,
                "state": trained.model.state_dict(),
                "ctx_mean": trained.ctx_mean, "ctx_std": trained.ctx_std}, path)
    path.with_suffix(".json").write_text(json.dumps(meta | {"classes": classes}, indent=2))
    print(f"  [{dataset}] {name} trained in {meta['train_seconds']:.0f}s -> {path}")
    return path


def load(path: str | Path) -> WindowModel:
    """Load a file written by ``train_and_save``."""
    ck = torch.load(Path(path), weights_only=False)
    m = ck["meta"]
    if m.get("format") != FORMAT:
        raise ValueError(f"{path}: unknown model file format {m.get('format')}")
    net = sequence.build(m["model"], len(ck["vocab"]), m["n_cont"], m["n_context"],
                         len(ck["classes"]), max(m["size"], 8))
    net.load_state_dict(ck["state"])
    net.eval()
    return WindowModel(Trained(net, ck["ctx_mean"], ck["ctx_std"]), m["model"], m["dataset"],
                       list(ck["classes"]), list(ck["vocab"]), m["size"], m)


def check(path: Path) -> float:
    """Reload ``path`` and compare its test predictions with the stored run."""
    wm = load(path)
    m = wm.meta
    stored = (RESULTS_DIR / m["dataset"] / f"window{m['size']}-last" / "experiments"
              / f"{m['model']}+s{m['seed']}" / "predictions.csv.gz")
    if not stored.exists():
        print(f"  no stored run at {stored}; skipping the check")
        return float("nan")
    home = load_home(m["dataset"])
    _, test_start, _, _ = day_split(home, m["train_frac"], m["test_frac"])
    ends = np.arange(test_start + 1, len(home.times) + 1)
    names, _ = wm.predict(home, ends)
    with gzip.open(stored, "rt") as f:
        ref = pd.read_csv(f, usecols=["pred"])["pred"].to_numpy()
    if len(ref) != len(names):
        print(f"  stored run has {len(ref):,} predictions, model gave {len(names):,}")
        return float("nan")
    agree = float(np.mean(np.asarray(names) == ref))
    print(f"  [{m['dataset']}] reloaded model agrees with the stored test predictions "
          f"on {agree:.2%} of {len(ref):,} windows")
    return agree


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset", default="all", choices=[*DATASETS, "all"])
    p.add_argument("--model", default="bilstm", choices=["bilstm", "cnn", "transformer"])
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--epochs", type=int, default=40)
    p.add_argument("--check", action="store_true",
                   help="after saving, reload and compare with the stored test predictions")
    p.add_argument("--check-only", action="store_true", help="only run the check")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args(argv)
    for ds in (list(DATASETS) if args.dataset == "all" else [args.dataset]):
        path = model_path(ds, args.model, args.seed)
        if not args.check_only:
            path = train_and_save(ds, args.model, args.seed, epochs=args.epochs,
                                  verbose=args.verbose)
        if args.check or args.check_only:
            check(path)


if __name__ == "__main__":
    main()
