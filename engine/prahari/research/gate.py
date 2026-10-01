"""Protocol R2 R10 — evidence gate: hold alarms while a large share of nodes shows strong evidence at once.

e(t) is the share of nodes whose M26 p-value was ≤ `p_thr` at least once in (t − window, t]. An alarm at t is held
when e(t) ≥ θ. The gate reads node evidence, not candidates, so it sees regional haze before the CUSUMs fire.
"""
from __future__ import annotations

import numpy as np


def evidence_share(P, p_thr: float = 0.01, window: int = 30) -> np.ndarray:
    """R10 — e(t) for every tick of p-values P (T, N)."""
    hit = (np.asarray(P) <= p_thr).astype(np.int32)
    c = np.cumsum(hit, axis=0)
    lag = np.zeros_like(c)
    lag[window:] = c[:-window]
    return ((c - lag) > 0).mean(axis=1)


def gated(alarms: list, e: np.ndarray, theta: float | None) -> list:
    """R10 — the alarms (t, anchor, members) not held by the gate at threshold θ (None: the gate is off)."""
    if theta is None:
        return list(alarms)
    return [a for a in alarms if e[a[0]] < theta]
