"""Sensor model (SPEC §5.6). Stub: baseline plus white noise plus plume signal. Off is not allowed.

The composite reading M18 with M19 AR(1) noise and M20 events is the Phase 2 real model.
"""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import Readings
from prahari.core.registry import Stage, register


def mox_linear(c):
    """M17 (legacy) — plume concentration in su adds linearly to the reading."""
    return np.asarray(c, dtype=float)


@register("sensor", kind="stub")
class SensorStub(Stage):
    equation = "M17 (linear)"
    tag = "ASM"
    description = "Constant baseline + white noise + plume + nuisance + haze"

    def reset(self, ctx) -> None:
        self._base = np.full(ctx.n_nodes, float(self.params["baseline_su"]))

    def step(self, inputs, ctx) -> Readings:
        t, conc, env, nuis, haze = inputs
        noise = self.rng.normal(0.0, self.params["noise_sd_su"], ctx.n_nodes)
        x = self._base + noise + mox_linear(conc.c) + nuis.v + haze.v
        col = x[:, None]
        return Readings(x=col, x_raw=col.copy(), fault=np.zeros(ctx.n_nodes, dtype=bool))
