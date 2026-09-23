"""Two-timescale conditioning, TTC — real implementation (SPEC §5.8, M24 with the freeze cap and M25).

Slow EWMA baseline and spread for drift and health (M24): frozen while |z| ≥ 3; after 180 frozen minutes it resumes
with a winsorised residual, so the baseline cannot lock up. Detection uses the fast residual against a lagged
60–180-minute window mean (M25), which removes most of the daily cycle. The stub (v1 behaviour) is in `ttc.py`.
"""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import Readings, Residuals
from prahari.core.registry import Stage, register


def ttc_slow_step(b, s2, x, fz, alpha: float, freeze: float, fmax: int):
    """M24 with the freeze cap — one step of the slow baseline.

    z = (x − b)/s from the previous state; update where |z| < freeze; after `fmax` consecutive frozen ticks update
    with the winsorised residual x̃ − b = clip(x − b, −freeze·s, freeze·s). Returns (z, b, s², frozen-tick count).
    """
    d = x - b
    s = np.sqrt(s2)
    z = d / s
    ok = np.abs(z) < freeze
    fz = np.where(ok, 0, fz + 1)
    upd = ok | (fz > fmax)                                   # M24 — cap: resume after fmax frozen ticks
    dw = np.clip(d, -freeze * s, freeze * s)                 # M24 — winsorised residual (equals d where ok)
    b = np.where(upd, b + alpha * dw, b)
    s2 = np.where(upd, s2 + alpha * (dw * dw - s2), s2)
    return z, b, s2, fz


class FastResidual:
    """M25 — r_t = x_t − mean(x_{t−lag1} … x_{t−lag0−1}), from a ring of cumulative sums (O(1) per tick).

    While fewer than `lag1` samples exist the window is truncated at the first sample, as in the report simulation.
    """

    def __init__(self, shape, lag0: int, lag1: int):
        self.lag0, self.lag1 = lag0, lag1
        self.cs = np.zeros((lag1 + 2, *shape))               # cs_k = Σ x_0 … x_{k−1}, for k = t − lag1 … t + 1
        self.t = 0

    def step(self, x):
        t, L = self.t, self.cs.shape[0]
        self.cs[(t + 1) % L] = self.cs[t % L] + x
        a, b = max(t - self.lag1, 0), max(t - self.lag0, 1)
        base = (self.cs[b % L] - self.cs[a % L]) / max(b - a, 1)
        self.t += 1
        return x - base


@register("ttc", kind="real")
class TTCReal(Stage):
    equation = "M24 (freeze cap), M25"
    tag = "LIT"
    description = "Slow baseline with the 180-minute freeze cap; detection on the lagged-window fast residual"

    def reset(self, ctx) -> None:
        p, tick = self.params, ctx.tick_minutes
        self._alpha = tick / float(p["slow_tau_min"])
        self._fmax = int(p["freeze_cap_min"]) // tick
        self._init = int(p["init_min"]) // tick
        self._lags = (int(p["fast_lag0_min"]) // tick, int(p["fast_lag1_min"]) // tick)
        self._buf = None
        self._fast = None
        self._b = self._s2 = self._fz = None
        self._k = 0

    def _init_from_first_day(self):
        """Report simulation: b, s² from the whole first day, then the filter runs over that same day."""
        buf = self._buf
        self._b = buf.mean(axis=0)
        self._s2 = buf.var(axis=0) + float(self.params["var_floor"])
        self._fz = np.zeros(buf.shape[1:], dtype=np.int64)
        z = None
        for row in buf:
            z, self._b, self._s2, self._fz = ttc_slow_step(self._b, self._s2, row, self._fz, self._alpha,
                                                           float(self.params["freeze_z"]), self._fmax)
        self._buf = None
        return z

    def step(self, readings: Readings, ctx) -> Residuals:
        x = readings.x
        if self._fast is None:
            self._fast = FastResidual(x.shape, *self._lags)
            self._buf = np.zeros((self._init, *x.shape))
            self._sum = np.zeros_like(x)
            self._sq = np.zeros_like(x)
        r = self._fast.step(x)                                   # M25 — fast residual
        k = self._k
        self._k += 1
        if self._buf is not None:
            self._buf[k] = x
            if k == self._init - 1:
                z = self._init_from_first_day()
                return Residuals(r=r, z=z, b=self._b.copy())
            # Warm-up display during day 1 (ASM): running mean of the samples so far; spread floored at initial_sd.
            self._sum += x
            self._sq += x * x
            b = self._sum / (k + 1)
            sd = np.maximum(np.sqrt(np.maximum(self._sq / (k + 1) - b * b, 0.0)), float(self.params["initial_sd_su"]))
            return Residuals(r=r, z=(x - b) / sd, b=b)
        z, self._b, self._s2, self._fz = ttc_slow_step(self._b, self._s2, x, self._fz, self._alpha,
                                                       float(self.params["freeze_z"]), self._fmax)
        return Residuals(r=r, z=z, b=self._b.copy())

    def snapshot(self) -> dict:
        return {"freeze_cap_min": self.params["freeze_cap_min"],
                "fast_window_min": [self.params["fast_lag0_min"], self.params["fast_lag1_min"]]}
