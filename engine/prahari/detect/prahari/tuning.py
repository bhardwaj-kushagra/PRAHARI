"""Replay tuning of CUSUM thresholds (SPEC §5.8, M28; also P1t of M23). Pure functions plus a tick-by-tick buffer.

h is found by bisection on the tuning days so that node-local false candidates match the target rate. Common-mode
periods — at least 25% of nodes with slow z ≥ 3, padded by ±60 minutes — are excluded from the count: they are the
edge layer's job (SCMR). Semantics follow the report simulation (`reference/prahari_simulation.py`).
"""
from __future__ import annotations

import numpy as np


def cusum_replay(S, k: float, h: float, ref_ticks: int):
    """M28 — CUSUM over scores S (T, N): G ← max(0, G + S − k); a hit when G > h and the node's refractory counter
    is 0, then G ← 0 and the counter is set to `ref_ticks` (decremented the same tick). Returns (t_idx, node) arrays."""
    T, n = S.shape
    G = np.zeros(n)
    ref = np.zeros(n, dtype=np.int64)
    ts, ns = [], []
    for t in range(T):
        G = np.maximum(0.0, G + S[t] - k)
        hit = (G > h) & (ref == 0)
        if hit.any():
            idx = np.flatnonzero(hit)
            ts.append(np.full(idx.size, t))
            ns.append(idx)
            G[hit] = 0.0
            ref[hit] = ref_ticks
        ref = np.maximum(ref - 1, 0)
    if not ts:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)
    return np.concatenate(ts), np.concatenate(ns)


def cm_mask(frac, thr: float, pad: int):
    """M28 — common-mode ticks: fraction of elevated nodes ≥ thr, padded by ±pad ticks."""
    m = (np.asarray(frac) >= thr).astype(float)
    return np.convolve(m, np.ones(2 * pad + 1), "same") > 0


def tune_h(S, k: float, cm, target: float, lo: float, hi: float, iters: int, ref_ticks: int) -> float:
    """M28 — bisection on h so that candidates outside common-mode ticks match `target`; returns the upper bound.
    If even `hi` gives more than the target, `hi` is returned (the search cap)."""
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        t, _ = cusum_replay(S, k, mid, ref_ticks)
        if int((~cm[t]).sum()) > target:
            lo = mid
        else:
            hi = mid
    return hi


class TuningBuffer:
    """Scores (T, N) over the tuning window [t0, t1) and the elevated-node fraction from t0 − pad, filled per tick.

    The report simulation pads the common-mode mask with hindsight on both sides; a tick loop tunes at t1, so the
    60 minutes after t1 are not available (DECISIONS P5-4).
    """

    def __init__(self, t0: int, t1: int, pad_min: int, tick: int):
        self.t0, self.t1, self.tick = t0, t1, tick
        self.pad = pad_min // tick
        self.f0 = max(t0 - pad_min, 0)
        self.S = None
        self.frac = None

    def add(self, t: int, s, frac: float) -> None:
        if not self.f0 <= t < self.t1:
            return
        if self.frac is None:
            self.frac = np.zeros((self.t1 - self.f0) // self.tick)
            self.S = np.zeros(((self.t1 - self.t0) // self.tick, s.size))
        self.frac[(t - self.f0) // self.tick] = frac
        if t >= self.t0:
            self.S[(t - self.t0) // self.tick] = s

    def ready(self, t: int) -> bool:
        return self.S is not None and t >= self.t1

    def mask(self, thr: float):
        """Common-mode mask over the tuning window, padded with the minutes before t0 that were seen."""
        head = (self.t0 - self.f0) // self.tick
        return cm_mask(self.frac, thr, self.pad)[head:]


def tune_from_buffer(buf: TuningBuffer, p: dict, k: float, ref_ticks: int) -> tuple[float, bool]:
    """M28 — tune h on a filled buffer with the parameters in `p`; returns (h, at the search cap)."""
    n = buf.S.shape[1]
    days = (buf.t1 - buf.t0) / 1440.0
    target = float(p["target_per_node_30d"]) / 30.0 * n * days       # M28 — r · N · D_tune
    hi = float(p["h_hi"])
    h = tune_h(buf.S, k, buf.mask(float(p["cm_frac"])), target, float(p["h_lo"]), hi, int(p["bisect_iters"]),
               ref_ticks)
    return h, h >= hi
