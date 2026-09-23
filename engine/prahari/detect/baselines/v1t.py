"""P1t — v1 with a replay-tuned threshold (SPEC §5.7: "P1t is P1 with h tuned by M28"). Stub and off: none.

As the report simulation's P1t: the slow EWMA z with the freeze cap (M24, `ttc_slow_step`), CUSUM on z with k = 0.5,
h tuned by bisection on the tuning days (M28, common-mode periods excluded, mask from this z), and v1's confirmation
(two candidates within R and 30 minutes). Before tuning completes, h is `h_default`.
"""
from __future__ import annotations

from collections import deque

import numpy as np

from prahari.core.contracts import BaselineAlarms, Readings
from prahari.core.registry import Stage, register
from prahari.detect.prahari.ttc_real import ttc_slow_step
from prahari.detect.prahari.tuning import TuningBuffer, tune_from_buffer


def confirm_step(recent: deque, t: int, cands, nbr, window: int, quorum: int) -> list:
    """M23 — v1 confirmation: a candidate confirms when ≥ quorum distinct nodes within R raised candidates in the
    last `window` minutes (itself included). Mutates `recent`; returns [(node, members)]."""
    alarms = []
    for i in cands:
        while recent and recent[0][0] < t - window:
            recent.popleft()
        recent.append((t, int(i)))
        local = sorted({j for _, j in recent if nbr[i, j]})
        if len(local) >= quorum:
            alarms.append((int(i), tuple(local)))
    return alarms


@register("baseline_p1t", kind="real")
class V1ReplayTuned(Stage):
    equation = "M23 (k 0.5), M24 (cap), M28 tuning"
    tag = "LIT"
    description = "P1t: v1 CUSUM on the capped slow z with h replay-tuned (M28), 2 candidates within R and 30 min"

    def reset(self, ctx) -> None:
        p, n = self.params, ctx.n_nodes
        self._buf = np.zeros((int(p["init_min"]), n))
        self._b = self._s2 = None
        self._fz = np.zeros(n, dtype=np.int64)
        self._G = np.zeros(n)
        self._ref = np.zeros(n, dtype=np.int64)
        self._recent: deque = deque()
        self._h = float(p["h_default"])
        self._tuned = self._at_cap = False
        self._tb = TuningBuffer(int(p["tune_start_min"]), int(p["tune_end_min"]), int(p["cm_pad_min"]), 1)
        self.n_candidates = 0

    def _slow(self, x):
        p = self.params
        z, self._b, self._s2, self._fz = ttc_slow_step(self._b, self._s2, x, self._fz, 1.0 / p["slow_tau_min"],
                                                       p["freeze_z"], int(p["freeze_cap_min"]))
        return z

    def step(self, readings: Readings, ctx) -> BaselineAlarms:
        p, t, x = self.params, ctx.t, readings.x[:, 0]
        init = self._buf.shape[0]
        if t < init:
            self._buf[t] = x
            if t == init - 1:                        # report simulation: first-day statistics, then replay day 1
                self._b = self._buf.mean(axis=0)
                self._s2 = self._buf.var(axis=0) + p["var_floor"]
                for row in self._buf:
                    self._slow(row)
            return BaselineAlarms()
        z = self._slow(x)
        if self._tb is not None:
            self._tb.add(t, z, float((z >= p["cm_z"]).mean()))
        if self._tb is not None and self._tb.ready(t):
            self._h, self._at_cap = tune_from_buffer(self._tb, p, float(p["k"]), int(p["refractory_min"]))
            self._tuned, self._tb = True, None
            self._G[:] = 0.0
            self._ref[:] = 0
        if t < p["start_min"]:
            return BaselineAlarms()
        self._G = np.maximum(0.0, self._G + z - p["k"])                                 # M23 — CUSUM on z
        hit = (self._G > self._h) & (self._ref == 0)
        self._G[hit] = 0.0
        self._ref[hit] = int(p["refractory_min"])
        self._ref = np.maximum(self._ref - 1, 0)
        cands = np.flatnonzero(hit)
        self.n_candidates += cands.size
        alarms = confirm_step(self._recent, t, cands, ctx.neighbours, int(p["window_min"]), int(p["quorum"]))
        return BaselineAlarms(candidates=tuple(int(i) for i in cands), alarms=tuple(alarms))

    def snapshot(self) -> dict:
        return {"h": round(self._h, 3), "tuned": self._tuned, "at_cap": self._at_cap, "k": self.params["k"]}


@register("baseline_p1t", kind="stub")
class V1TunedStub(Stage):
    equation = "—"
    description = "No P1t alarms"

    def step(self, readings, ctx) -> BaselineAlarms:
        return BaselineAlarms()


@register("baseline_p1t", kind="off")
class V1TunedOff(V1TunedStub):
    pass
