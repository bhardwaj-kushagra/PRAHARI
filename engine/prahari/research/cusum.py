"""Batched CUSUM replay and threshold tuning over several thresholds at once (protocol R1 §3).

Each row m behaves exactly as `detect.prahari.tuning.cusum_replay` / `tune_h` with its own threshold (same operation
order, so results are bitwise identical); batching only shares the pass over time between rows.
"""
from __future__ import annotations

import numpy as np


def cusum_multi(S, k: float, hs, ref_ticks: int, count_mask=None, collect: bool = True):
    """M28 / M23 — CUSUM G ← max(0, G + S − k) over S (T, N) for every threshold in `hs` (M,).

    Returns (hits, counts): hits[m] = (t_idx, node) arrays as `cusum_replay` returns them (when `collect`), and
    counts[m] = hits at ticks where `count_mask` is False (all ticks when it is None)."""
    S = np.asarray(S, dtype=float)
    hs = np.asarray(hs, dtype=float)[:, None]
    T, n = S.shape
    M = hs.shape[0]
    G = np.zeros((M, n))
    ref = np.zeros((M, n), dtype=np.int64)
    counts = np.zeros(M, dtype=np.int64)
    ts: list = [[] for _ in range(M)]
    ns: list = [[] for _ in range(M)]
    for t in range(T):
        G = np.maximum(0.0, G + S[t] - k)
        hit = (G > hs) & (ref == 0)
        if hit.any():
            G[hit] = 0.0
            ref[hit] = ref_ticks
            if count_mask is None or not count_mask[t]:
                counts += hit.sum(axis=1)
            if collect:
                for m in np.flatnonzero(hit.any(axis=1)):
                    idx = np.flatnonzero(hit[m])
                    ts[m].append(np.full(idx.size, t))
                    ns[m].append(idx)
        ref = np.maximum(ref - 1, 0)
    hits = [(np.concatenate(ts[m]) if ts[m] else np.zeros(0, dtype=np.int64),
             np.concatenate(ns[m]) if ns[m] else np.zeros(0, dtype=np.int64)) for m in range(M)]
    return hits, counts


def tune_multi(S, k: float, cm, targets, lo: float, hi: float, iters: int, ref_ticks: int):
    """M28 — `tune_h` for every target at once: bisection on h so that candidates outside common-mode ticks `cm`
    match each target; returns the upper bounds (M,) and whether each ended at the search cap."""
    targets = np.asarray(targets, dtype=float)
    lo_a = np.full(targets.size, float(lo))
    hi_a = np.full(targets.size, float(hi))
    for _ in range(iters):
        mid = 0.5 * (lo_a + hi_a)
        _, c = cusum_multi(S, k, mid, ref_ticks, count_mask=cm, collect=False)
        over = c > targets
        lo_a = np.where(over, mid, lo_a)
        hi_a = np.where(over, hi_a, mid)
    return hi_a, hi_a >= float(hi)


def by_tick(t_idx, nodes, offset: int = 0) -> dict:
    """Hits (t_idx, node) → {t + offset: [nodes ascending]} in time order."""
    out: dict[int, list] = {}
    order = np.lexsort((nodes, t_idx))
    for t, i in zip(t_idx[order].tolist(), nodes[order].tolist()):
        out.setdefault(t + offset, []).append(i)
    return out
