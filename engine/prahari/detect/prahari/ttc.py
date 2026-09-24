"""Two-timescale conditioning, TTC (SPEC §5.8). Real M24 + M25: Phase 5.

Stub: slow EWMA residual only, v1 behaviour (M24 without the freeze cap).
Off: raw reading minus the first-day mean.
"""
from __future__ import annotations

import numpy as np

from prahari.core.clock import MINUTES_PER_DAY
from prahari.core.contracts import Readings, Residuals
from prahari.core.registry import Stage, register


def ewma_update(b, s2, x, alpha, freeze):
    """M24 (v1, no freeze cap) — b ← b + α(x − b), s² ← s² + α[(x − b)² − s²], frozen while |z| ≥ freeze.

    `alpha` may be an array (per node) for the warm-up below.
    Returns (r, z, b_new, s2_new) with r = x − b_{t−1} and z = r / s_{t−1}.
    """
    r = x - b
    z = r / np.sqrt(s2)
    upd = np.abs(z) < freeze
    b_new = np.where(upd, b + alpha * r, b)
    s2_new = np.where(upd, s2 + alpha * (r * r - s2), s2)
    return r, z, b_new, s2_new


@register("ttc", kind="stub")
class TTCStub(Stage):
    equation = "M24 (v1, no freeze cap)"
    tag = "ASM"
    description = "Slow EWMA residual only (v1 behaviour)"

    def reset(self, ctx) -> None:
        self._b = None
        self._s2 = None
        self._n = 0

    def step(self, readings: Readings, ctx) -> Residuals:
        x = readings.x
        if self._b is None:
            self._b = x.copy()
            self._s2 = np.full_like(x, float(self.params["initial_sd_su"]) ** 2)
        self._n += 1
        # Warm-up (ASM): running mean until n reaches the time constant, then the fixed α of M24.
        alpha = max(1.0 / (self._n + 1), 1.0 / self.params["slow_tau_min"])
        r, z, self._b, self._s2 = ewma_update(self._b, self._s2, x, alpha, self.params["freeze_z"])
        return Residuals(r=r, z=z, b=self._b.copy())


@register("ttc", kind="off")
class TTCOff(Stage):
    description = "Raw reading minus first-day mean"

    def reset(self, ctx) -> None:
        self._sum = None
        self._n = 0

    def step(self, readings: Readings, ctx) -> Residuals:
        x = readings.x_raw
        if self._sum is None:
            self._sum = np.zeros_like(x)
        if ctx.t < MINUTES_PER_DAY or self._n == 0:
            self._sum += x
            self._n += 1
        b = self._sum / self._n
        r = x - b
        return Residuals(r=r, z=r / float(self.params["initial_sd_su"]), b=b)
