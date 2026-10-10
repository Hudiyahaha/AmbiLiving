"""Approaches 2 & 3: neural models over the ordered sensor-event sequence.

All share the same input: token embedding (sensor + state) concatenated with
per-event timing features, and the same head: pooled sequence representation
concatenated with segment context (time of day, duration, ...).
"""

from __future__ import annotations

import torch
from torch import nn


def masked_mean(h: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    m = mask.unsqueeze(-1).float()
    return (h * m).sum(1) / m.sum(1).clamp(min=1.0)


def masked_max(h: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    return h.masked_fill(~mask.unsqueeze(-1), -1e4).max(1).values


class _Base(nn.Module):
    def __init__(self, vocab_size: int, n_cont: int, n_context: int, n_classes: int,
                 emb_dim: int, pooled_dim: int, dropout: float):
        super().__init__()
        self.emb = nn.Embedding(vocab_size, emb_dim, padding_idx=0)
        self.in_dim = emb_dim + n_cont
        self.head = nn.Sequential(
            nn.Linear(pooled_dim + n_context, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, n_classes),
        )

    def embed(self, tokens, cont):
        return torch.cat([self.emb(tokens), cont], dim=-1)

    def encode(self, x, mask) -> torch.Tensor:  # -> (B, pooled_dim)
        raise NotImplementedError

    def forward(self, tokens, cont, mask, context):
        pooled = self.encode(self.embed(tokens, cont), mask)
        return self.head(torch.cat([pooled, context], dim=-1))


class BiLSTMClassifier(_Base):
    """Approach 2: bidirectional LSTM, mean + max pooled over time."""

    def __init__(self, vocab_size, n_cont, n_context, n_classes,
                 emb_dim=48, hidden=64, dropout=0.3):
        super().__init__(vocab_size, n_cont, n_context, n_classes, emb_dim, 4 * hidden, dropout)
        self.lstm = nn.LSTM(self.in_dim, hidden, batch_first=True, bidirectional=True)
        self.drop = nn.Dropout(dropout)

    def encode(self, x, mask):
        lengths = mask.sum(1).clamp(min=1).cpu()
        packed = nn.utils.rnn.pack_padded_sequence(x, lengths, batch_first=True,
                                                   enforce_sorted=False)
        out, _ = self.lstm(packed)
        h, _ = nn.utils.rnn.pad_packed_sequence(out, batch_first=True,
                                                total_length=x.size(1))
        h = self.drop(h)
        return torch.cat([masked_mean(h, mask), masked_max(h, mask)], dim=-1)


class CNNClassifier(_Base):
    """Approach 3a: multi-width 1D convolutions (local sensor patterns), max pooled."""

    def __init__(self, vocab_size, n_cont, n_context, n_classes,
                 emb_dim=48, channels=64, kernels=(3, 5, 9), dropout=0.3):
        super().__init__(vocab_size, n_cont, n_context, n_classes, emb_dim,
                         channels * len(kernels), dropout)
        self.convs = nn.ModuleList(
            nn.Sequential(
                nn.Conv1d(self.in_dim, channels, k, padding=k // 2),
                nn.BatchNorm1d(channels),
                nn.ReLU(),
                nn.Conv1d(channels, channels, k, padding=k // 2),
                nn.ReLU(),
            )
            for k in kernels
        )
        self.drop = nn.Dropout(dropout)

    def encode(self, x, mask):
        x = x.transpose(1, 2)  # (B, C, L)
        outs = [masked_max(conv(x).transpose(1, 2), mask) for conv in self.convs]
        return self.drop(torch.cat(outs, dim=-1))


class TransformerClassifier(_Base):
    """Approach 3b: Transformer encoder with self-attention over events."""

    def __init__(self, vocab_size, n_cont, n_context, n_classes, max_len=128,
                 emb_dim=48, d_model=64, heads=4, layers=2, dropout=0.2):
        super().__init__(vocab_size, n_cont, n_context, n_classes, emb_dim, 2 * d_model, dropout)
        self.proj = nn.Linear(self.in_dim, d_model)
        self.pos = nn.Embedding(max_len, d_model)
        layer = nn.TransformerEncoderLayer(d_model, heads, dim_feedforward=2 * d_model,
                                           dropout=dropout, batch_first=True)
        self.encoder = nn.TransformerEncoder(layer, layers, enable_nested_tensor=False)

    def encode(self, x, mask):
        pos = torch.arange(x.size(1), device=x.device)
        h = self.proj(x) + self.pos(pos)
        h = self.encoder(h, src_key_padding_mask=~mask)
        return torch.cat([masked_mean(h, mask), masked_max(h, mask)], dim=-1)


MODELS = {
    "bilstm": BiLSTMClassifier,
    "cnn": CNNClassifier,
    "transformer": TransformerClassifier,
}


def build(name: str, vocab_size: int, n_cont: int, n_context: int, n_classes: int,
          max_len: int) -> nn.Module:
    cls = MODELS[name]
    kwargs = {"max_len": max_len} if name == "transformer" else {}
    return cls(vocab_size, n_cont, n_context, n_classes, **kwargs)
