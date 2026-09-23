"""P1 "v1 as written" baseline (SPEC §5.7, M23), reproducing the report's reference simulation. Stub and off: none.

Slow EWMA baseline and variance with the freeze but no cap (M24 without the cap), z = (x − b)/s, CUSUM with k = 0.5
and h from Siegmund's approximation (M23), and confirmation by two candidates within R and 30 minutes.
"""
from __future__ import annotations

from collections import deque

import numpy as np

from prahari.core.contracts import BaselineAlarms, Readings
from prahari.core.registry import Stage, register


def v1_ewma_step(b, s2, x, alpha: float, freeze: float):
    """M24 without the freeze cap — z from the previous baseline, then update only where |z| < freeze."""
    d = x - b
    z = d / np.sqrt(s2)
    u = np.abs(z) < freeze
    return z, np.where(u, b + alpha * d, b), np.where(u, s2 + alpha * (d * d - s2), s2)


@register("baseline_p1", kind="real")
class V1AsWritten(Stage):
    equation = "M23, M24 (no cap)"
    tag = "ASM"
    description = "P1: v1 EWMA z-score CUSUM (k 0.5, h from the ARL formula), 2 candidates within R and 30 min"

    def reset(self, ctx) -> None:
        n, init = ctx.n_nodes, int(self.params["init_min"])
        self._buf = np.zeros((init, n))
        self._b = self._s2 = None
        self._G = np.zeros(n)
        self._ref = np.zeros(n, dtype=int)
        self._recent: deque = deque()
        self.n_candidates = 0

    def _init_from_first_day(self) -> None:
        p = self.params
        self._b = self._buf.mean(axis=0)
        self._s2 = self._buf.var(axis=0) + p["var_floor"]
        for row in self._buf:                           # v1 replays day 1 from its day-1 statistics (as the report)
            _, self._b, self._s2 = v1_ewma_step(self._b, self._s2, row, 1.0 / p["slow_tau_min"], p["freeze_z"])

    def step(self, readings: Readings, ctx) -> BaselineAlarms:
        p, t, x = self.params, ctx.t, readings.x[:, 0]
        init = self._buf.shape[0]
        if t < init:
            self._buf[t] = x
            if t == init - 1:
                self._init_from_first_day()
            return BaselineAlarms()
        z, self._b, self._s2 = v1_ewma_step(self._b, self._s2, x, 1.0 / p["slow_tau_min"], p["freeze_z"])
        if t < p["start_min"]:
            return BaselineAlarms()
        self._G = np.maximum(0.0, self._G + z - p["k"])                                 # M23 — CUSUM
        hit = (self._G > p["h"]) & (self._ref == 0)
        self._G[hit] = 0.0
        self._ref[hit] = int(p["refractory_min"])
        self._ref = np.maximum(self._ref - 1, 0)
        cands = np.flatnonzero(hit)
        self.n_candidates += cands.size
        alarms = []
        nbr = ctx.neighbours
        for i in cands:                                  # candidates only: a handful per tick at most
            while self._recent and self._recent[0][0] < t - p["window_min"]:
                self._recent.popleft()
            self._recent.append((t, int(i)))
            local = sorted({j for _, j in self._recent if nbr[i, j]})
            if len(local) >= p["quorum"]:
                alarms.append((int(i), tuple(local)))
        return BaselineAlarms(candidates=tuple(int(i) for i in cands), alarms=tuple(alarms))

    def snapshot(self) -> dict:
        return {"h": self.params["h"], "k": self.params["k"]}


@register("baseline_p1", kind="stub")
class V1Stub(Stage):
    equation = "—"
    description = "No P1 alarms"

    def step(self, readings, ctx) -> BaselineAlarms:
        return BaselineAlarms()


@register("baseline_p1", kind="off")
class V1Off(V1Stub):
    pass
