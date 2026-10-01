"""Protocol R2 R11 — Mei (2010): the sum of local CUSUMs as a network detector, with no common-mode handling.

Each node keeps W_i ← max(0, W_i + S_i − k) on its evidence S = −ln p (M26); the network alarms when Σ W_i > h_M.
The alarm's anchor is argmax W and its members are the nodes with W_i ≥ ½ max W; then every W_i resets to 0 and no
alarm can fire for the refractory period (the statistics keep accumulating, as the node CUSUM M28 does).
"""
from __future__ import annotations

import numpy as np

from prahari.detect.prahari.qcc import P_FLOOR


def mei_alarms(P, hs, k: float = 1.5, refractory: int = 30, t0: int = 0) -> list[list]:
    """R11 — alarms (t + t0, anchor, members) for every threshold in `hs`, on p-values P (T, N) from tick 0."""
    S = -np.log(np.clip(np.asarray(P, dtype=float), P_FLOOR, 1.0))
    hs = np.asarray(hs, dtype=float)
    M, (T, n) = hs.size, S.shape
    W = np.zeros((M, n))
    ref = np.zeros(M, dtype=np.int64)
    out: list = [[] for _ in range(M)]
    for t in range(T):
        W = np.maximum(0.0, W + S[t] - k)
        fire = (W.sum(axis=1) > hs) & (ref == 0)
        for m in np.flatnonzero(fire):
            w = W[m]
            top = float(w.max())
            out[m].append((t + t0, int(np.argmax(w)), [int(i) for i in np.flatnonzero(w >= 0.5 * top)]))
            W[m] = 0.0
            ref[m] = refractory
        ref = np.maximum(ref - 1, 0)
    return out
