"""Sensor model (SPEC §5.6). Stub: baseline plus white noise plus plume signal. Off is not allowed.

Real: the composite reading M18 with M19 AR(1) noise and M17 (legacy, linear) response (Phase 2).
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


def residual_cycle(tod_frac, phase, day_amp):
    """M18 — daily-cycle shape A_day · sin(2π tod − π/2 + φ_i) (before the per-node amplitude c_i)."""
    return day_amp * np.sin(2.0 * np.pi * tod_frac - np.pi / 2.0 + phase)


def heteroscedastic_scale(tod_frac, extra: float):
    """M19 — 1 + extra · max(0, sin(2π tod − π/2)): noisier by day."""
    return 1.0 + extra * max(0.0, float(np.sin(2.0 * np.pi * tod_frac - np.pi / 2.0)))


@register("sensor", kind="real")
class SensorReal(Stage):
    equation = "M17 (linear), M18, M19"
    tag = "ASM"
    description = "Drift + residual daily cycle + AR(1) noise + heavy tail + nuisance + haze + plume"

    def reset(self, ctx) -> None:
        p, rng, n = self.params, self.rng, ctx.n_nodes
        self._c = rng.uniform(p["cycle_amp"][0], p["cycle_amp"][1], n)                 # M18 — c_i
        self._phase = rng.uniform(-p["phase_range"], p["phase_range"], n)              # M18 — φ_i
        run_min = max(1, ctx.clock.n_ticks * ctx.tick_minutes)
        self._slope = rng.normal(0.0, p["ageing_sd"], n) / run_min                      # M18 — linear ageing
        self._drift = np.zeros(n)
        self._e = np.zeros(n)
        self._day = None
        self._day_amp = 1.0
        self._start = ctx.clock.start.date()

    def step(self, inputs, ctx) -> Readings:
        t, conc, env, nuis, haze = inputs
        p, rng, n = self.params, self.rng, ctx.n_nodes
        wall = ctx.clock.wall(t)
        day = (wall.date() - self._start).days
        if day != self._day:
            self._day = day
            self._day_amp = float(np.clip(1.0 + p["day_amp_sd"] * rng.normal(),
                                          p["day_amp_clip"][0], p["day_amp_clip"][1]))   # M18 — A_day ±30%
        tod = (wall.hour * 60 + wall.minute) / 1440.0
        self._drift += rng.normal(0.0, p["drift_step_sd"], n)                           # M18 — drift random walk
        het = heteroscedastic_scale(tod, p["het_extra"])
        self._e = p["ar_phi"] * self._e + p["sigma_e"] * het * rng.normal(size=n)        # M19 — AR(1) noise
        tail = p["tail_scale"] * rng.standard_t(p["tail_df"], n)                          # M18 — heavy tail
        cyc = residual_cycle(tod, self._phase, self._day_amp)
        x = (self._drift + self._slope * t + self._c * cyc + self._e + tail
             + nuis.v + haze.v + mox_linear(conc.c))                                     # M18 composite, M17 linear
        x_raw = x + p["raw_extra"] * cyc                                                  # M18 — uncompensated channel
        return Readings(x=x[:, None], x_raw=x_raw[:, None], fault=np.zeros(n, dtype=bool))
