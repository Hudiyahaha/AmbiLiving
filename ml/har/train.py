"""Training loop shared by all neural approaches."""

from __future__ import annotations

import copy
import random
import time

import numpy as np
import torch
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from torch import nn

from .features import SequenceData
from .models import sequence


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def class_weights(y: np.ndarray, n_classes: int, power: float = 0.5) -> torch.Tensor:
    """Inverse-frequency weights softened by ``power`` (0.5 = sqrt).

    Full inverse frequency over-weights tiny classes like Aruba's Respirate (6
    instances) and hurts the large ones; sqrt is a common compromise.
    """
    counts = np.bincount(y, minlength=n_classes).astype(np.float64)
    w = (counts.sum() / (n_classes * np.maximum(counts, 1))) ** power
    return torch.tensor(w / w.mean(), dtype=torch.float32)


def _tensors(d: SequenceData, ctx_mean, ctx_std):
    return (
        torch.from_numpy(d.tokens),
        torch.from_numpy(d.cont),
        torch.from_numpy(d.mask),
        torch.from_numpy(((d.context - ctx_mean) / ctx_std).astype(np.float32)),
    )


def _batch(tensors, idx):
    """Select rows and trim padding to the longest sequence in the batch."""
    tokens, cont, mask, context = (t[idx] for t in tensors)
    L = max(int(mask.sum(1).max()), 1)
    return tokens[:, :L], cont[:, :L], mask[:, :L], context


def _bucketed_batches(lengths: torch.Tensor, batch_size: int, g: torch.Generator):
    """Shuffle, then sort within large chunks so each batch has similar lengths.

    Segment lengths range from ~4 events (Enter_Home) to the 128 cap, so this
    removes most padding and speeds CPU training several-fold.
    """
    perm = torch.randperm(len(lengths), generator=g)
    chunk = batch_size * 32
    batches = []
    for s in range(0, len(perm), chunk):
        part = perm[s:s + chunk]
        part = part[torch.argsort(lengths[part], stable=True)]
        batches += [part[i:i + batch_size] for i in range(0, len(part), batch_size)]
    order = torch.randperm(len(batches), generator=g)
    return [batches[i] for i in order]


@torch.no_grad()
def _predict(model, tensors, batch_size=256) -> np.ndarray:
    model.eval()
    lengths = tensors[2].sum(1)
    order = torch.argsort(lengths)
    pred = torch.empty(len(order), dtype=torch.long)
    for s in range(0, len(order), batch_size):
        idx = order[s:s + batch_size]
        pred[idx] = model(*_batch(tensors, idx)).argmax(1)
    return pred.numpy()


def fit_predict(
    name: str,
    train: SequenceData,
    y_train: np.ndarray,
    test: SequenceData,
    n_classes: int,
    seed: int,
    max_epochs: int = 40,
    patience: int = 6,
    batch_size: int = 64,
    lr: float = 1e-3,
    verbose: bool = True,
) -> np.ndarray:
    set_seed(seed)

    # Hold out 10% of the training fold for early stopping (never the test fold).
    idx = np.arange(len(y_train))
    counts = np.bincount(y_train)
    stratify = y_train if counts[counts > 0].min() >= 2 else None
    tr_idx, va_idx = train_test_split(idx, test_size=0.1, stratify=stratify, random_state=seed)
    tr, va = train.subset(tr_idx), train.subset(va_idx)
    y_tr, y_va = y_train[tr_idx], y_train[va_idx]

    ctx_mean = tr.context.mean(0)
    ctx_std = tr.context.std(0) + 1e-6
    tr_t, va_t, te_t = (_tensors(d, ctx_mean, ctx_std) for d in (tr, va, test))
    y_tr_t = torch.from_numpy(y_tr)

    model = sequence.build(name, len(train.vocab), train.cont.shape[-1],
                           train.context.shape[-1], n_classes, train.tokens.shape[1])
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, mode="max", factor=0.5, patience=2)
    loss_fn = nn.CrossEntropyLoss(weight=class_weights(y_tr, n_classes), label_smoothing=0.05)

    best_f1, best_state, bad_epochs = -1.0, None, 0
    g = torch.Generator().manual_seed(seed)
    for epoch in range(1, max_epochs + 1):
        t0 = time.time()
        model.train()
        total = 0.0
        for b in _bucketed_batches(tr_t[2].sum(1), batch_size, g):
            opt.zero_grad()
            loss = loss_fn(model(*_batch(tr_t, b)), y_tr_t[b])
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            total += loss.item() * len(b)

        val_f1 = f1_score(y_va, _predict(model, va_t), average="macro", zero_division=0)
        sched.step(val_f1)
        if verbose:
            print(f"    epoch {epoch:2d}  loss {total / len(y_tr):.4f}  val macro-F1 {val_f1:.4f}"
                  f"  ({time.time() - t0:.1f}s)")
        if val_f1 > best_f1 + 1e-4:
            best_f1, best_state, bad_epochs = val_f1, copy.deepcopy(model.state_dict()), 0
        else:
            bad_epochs += 1
            if bad_epochs >= patience:
                break

    model.load_state_dict(best_state)
    return _predict(model, te_t)
