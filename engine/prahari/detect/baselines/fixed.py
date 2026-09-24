"""P0 fixed-threshold baseline (SPEC §5.7, M22). Stub and off: no alarms."""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import BaselineAlarms, Readings
from prahari.core.registry import Stage, register


def first_day_threshold(x_raw_day, n_sigma: float):
    """M22 — μ_i + 3σ_i from the first day of the raw channel (population σ). x_raw_day is (T, N)."""
    return x_raw_day.mean(axis=0) + n_sigma * x_raw_day.std(axis=0)


@register("baseline_p0", kind="real")
class FixedThreshold(Stage):
    equation = "M22"
    tag = "ASM"
    description = "P0: alarm on rising edges above μ + 3σ of the first day (raw channel), 30-min refractory"

    def reset(self, ctx) -> None:
        n, init = ctx.n_nodes, int(self.params["init_min"])
        self._buf = np.zeros((init, n))
        self._thr = None
        self._prev = np.zeros(n, dtype=bool)
        self._last = np.full(n, -(10 ** 9))

    def step(self, readings: Readings, ctx) -> BaselineAlarms:
        p, t, xr = self.params, ctx.t, readings.x_raw[:, 0]
        init = self._buf.shape[0]
        if t < init:
            self._buf[t] = xr
            if t == init - 1:
                self._thr = first_day_threshold(self._buf, p["n_sigma"])            # M22
            return BaselineAlarms()
        above = xr > self._thr
        edge = above & ~self._prev
        self._prev = above
        if t <= p["start_min"]:                        # the oracle ignores an edge at the first counted tick
            return BaselineAlarms()
        hit = edge & (t - self._last >= p["refractory_min"])
        self._last = np.where(hit, t, self._last)
        nodes = np.flatnonzero(hit)
        return BaselineAlarms(candidates=tuple(int(i) for i in nodes),
                              alarms=tuple((int(i), (int(i),)) for i in nodes))     # any node alarm is a network alarm


@register("baseline_p0", kind="stub")
class FixedThresholdStub(Stage):
    equation = "—"
    description = "No P0 alarms"

    def step(self, readings, ctx) -> BaselineAlarms:
        return BaselineAlarms()


@register("baseline_p0", kind="off")
class FixedThresholdOff(FixedThresholdStub):
    pass
