"""Validation helpers shared by the contract modules."""
from __future__ import annotations

import numpy as np


class ContractError(ValueError):
    """A stage returned output that breaks its contract."""


def _arr(name: str, a, shape: tuple, lo: float | None = None, hi: float | None = None) -> None:
    if not isinstance(a, np.ndarray):
        raise ContractError(f"{name}: expected ndarray, got {type(a).__name__}")
    if a.shape != shape:
        raise ContractError(f"{name}: expected shape {shape}, got {a.shape}")
    if a.size and not np.all(np.isfinite(a)):
        raise ContractError(f"{name}: contains NaN or inf")
    if lo is not None and a.size and a.min() < lo:
        raise ContractError(f"{name}: value {a.min()} below {lo}")
    if hi is not None and a.size and a.max() > hi:
        raise ContractError(f"{name}: value {a.max()} above {hi}")


def _num(name: str, v: float, lo: float | None = None, hi: float | None = None) -> None:
    if not np.isfinite(v):
        raise ContractError(f"{name}: not finite")
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        raise ContractError(f"{name}: {v} outside [{lo}, {hi}]")


def _same_len(name: str, *seqs) -> None:
    if len({len(s) for s in seqs}) > 1:
        raise ContractError(f"{name}: per-cluster fields have different lengths")
