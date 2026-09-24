"""Node score with health weights — real implementation (SPEC §5.8, M27 with M29, Phase 9).

c_i = 1[fresh] · 1[not stuck] · exp(−max(0, |q_i| − 3) / 2)   (M29), then S_t = Σ c (−ln p)   (M27):

- fresh: data received within the last `fresh_min` minutes (a dropout makes the node abstain);
- not stuck: the reading's rolling 60-minute variance is above `stuck_frac` of the node's median hourly variance
  (a frozen sensor abstains once its window is flat);
- q_i: robust z of the node's slow baseline against the median of its neighbours' baselines, smoothed over a day
  (neighbour consensus; a large offset makes the node lose weight).

A node with c = 0 contributes no evidence (p_node = 1): "this sensor abstains". The stub (c = 1) is in `score.py`.
"""
from __future__ import annotations

from collections import deque

import numpy as np

from prahari.core.contracts import Scores
from prahari.core.registry import Stage, register
from prahari.detect.prahari.qcc import P_FLOOR
from prahari.detect.prahari.score import node_score


def robust_z(v):
    """(v − median) / (1.4826 MAD) across nodes; zeros when the spread is nil."""
    med = np.median(v)
    mad = 1.4826 * np.median(np.abs(v - med))
    return (v - med) / mad if mad > 0 else np.zeros_like(v)


def health_weight(fresh, not_stuck, q):
    """M29 — c = 1[fresh] · 1[not stuck] · exp(−max(0, |q| − 3) / 2)."""
    return fresh * not_stuck * np.exp(-np.maximum(0.0, np.abs(q) - 3.0) / 2.0)


@register("score", kind="real")
class ScoreReal(Stage):
    equation = "M27, M29"
    tag = "ASM"
    description = "Σ c·(−ln p) with health weights: freshness, stuck test, neighbour-consensus baseline"

    def reset(self, ctx) -> None:
        p, n = self.params, ctx.n_nodes
        self._w = int(p["stuck_window_min"]) // ctx.tick_minutes
        self._ring = np.zeros((self._w, n))
        self._k = 0
        self._seen = np.zeros(n)
        self._hourly: deque = deque(maxlen=int(p["variance_history_h"]))
        nbr = ctx.neighbours.copy()
        np.fill_diagonal(nbr, False)
        k = max(int(nbr.sum(axis=1).max()), 1)                   # padded neighbour lists (−1 = none): O(N·k), not O(N²)
        self._nb_idx = np.full((n, k), -1)
        for i in range(n):                                       # once, at reset
            js = np.flatnonzero(nbr[i])
            self._nb_idx[i, :js.size] = js
        self._dbar = None
        self._every = max(1, int(p["consensus_every_min"]) // ctx.tick_minutes)
        self._alpha = self._every * ctx.tick_minutes / float(p["consensus_min"])
        self._ref = None                                         # the node's reference variance, refreshed hourly
        self._q = np.zeros(n)

    def step(self, inputs, ctx) -> Scores:
        pv, x, res = inputs
        p, t = self.params, ctx.t
        xm = x.x[:, 0]
        miss = x.missing if x.missing is not None else np.zeros(xm.size, dtype=bool)
        self._seen = np.where(miss, self._seen, t)
        fresh = (t - self._seen) <= float(p["fresh_min"])                            # M29 — fresh data
        self._ring[self._k % self._w] = xm
        self._k += 1
        if self._k >= self._w:
            var = self._ring.var(axis=0)
            if self._ref is None:
                self._ref = var
            not_stuck = var > np.maximum(float(p["stuck_frac"]) * self._ref, float(p["stuck_floor"]))   # M29 — not stuck
            if self._k % self._w == 0:                           # the node's reference: hours it was not stuck
                self._hourly.append(np.where(not_stuck, var, np.nan))
                h = np.stack(self._hourly)
                ok = np.isfinite(h).any(axis=0)
                self._ref = np.where(ok, np.nanmedian(np.where(ok[None, :], h, 0.0), axis=0), self._ref)
        else:
            not_stuck = np.ones(xm.size, dtype=bool)
        if self._dbar is None or self._k % self._every == 0:  # neighbour consensus, smoothed over a day
            b = res.b[:, 0]
            nb = np.where(self._nb_idx >= 0, b[np.maximum(self._nb_idx, 0)], np.nan)
            has = (self._nb_idx >= 0).any(axis=1)
            d = b - np.where(has, np.nanmedian(np.where(has[:, None], nb, 0.0), axis=1), b)   # baseline vs neighbours
            self._dbar = d if self._dbar is None else self._dbar + self._alpha * (d - self._dbar)
            self._q = robust_z(self._dbar) if t >= float(p["consensus_min"]) else np.zeros(xm.size)   # M29 — q_i
        q = self._q
        c = health_weight(fresh, not_stuck, q)
        cm = np.repeat(c[:, None], pv.p.shape[1], axis=1)
        s = node_score(pv.p, cm)                                                     # M27 — S = Σ c (−ln p)
        z = None if pv.z is None else pv.z[:, 0] * c
        return Scores(s=s, p_node=np.clip(np.exp(-s), P_FLOOR, 1.0), c=cm, z=z)

    def snapshot(self) -> dict:
        p = self.params
        return {"fresh_min": p["fresh_min"], "stuck_window_min": p["stuck_window_min"], "stuck_frac": p["stuck_frac"]}
