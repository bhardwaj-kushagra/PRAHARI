"""Fire growth and source strength (SPEC §5.4). Stub: legacy M9 ramp. Off is not allowed."""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import Sources
from prahari.core.registry import Stage, register


def source_strength(tau, q_max, tau_g):
    """M9 — legacy source strength Q(τ) = Q_max (1 − exp(−τ/τ_g)), zero before ignition."""
    tau = np.asarray(tau, dtype=float)
    return np.where(tau > 0, q_max * (1.0 - np.exp(-np.clip(tau, 0, None) / tau_g)), 0.0)


def burned_area(tau, a15):
    """M37 (fallback area) — A(τ) = A_15 (τ/15)², used when M10 is not enabled."""
    tau = np.clip(np.asarray(tau, dtype=float), 0, None)
    return a15 * (tau / 15.0) ** 2


@register("growth", kind="stub")
class GrowthStub(Stage):
    equation = "M9"
    tag = "ASM"
    description = "Source strength ramp Q(t) with lognormal Q_max"

    def reset(self, ctx) -> None:
        self._qmax: dict[int, float] = {}

    def step(self, inputs, ctx) -> Sources:
        t, fires = inputs[0], inputs[1]
        p = self.params
        for f in fires.active:
            if f.id not in self._qmax:
                # M9 — Q_max ~ Q_ref · Lognormal(0, σ)
                self._qmax[f.id] = float(p["q_ref"] * np.exp(self.rng.normal(0.0, p["qmax_lognormal_sigma"])))
        ids = tuple(f.id for f in fires.active)
        age = np.array([t - f.t0 for f in fires.active], dtype=float)
        q_max = np.array([self._qmax[i] for i in ids], dtype=float)
        return Sources(ids=ids, x=np.array([f.x for f in fires.active], dtype=float),
                       y=np.array([f.y for f in fires.active], dtype=float), age_min=age, q_max=q_max,
                       tau_g=float(p["tau_g_min"]), q=source_strength(age, q_max, p["tau_g_min"]),
                       area_m2=burned_area(age, p["area_15min_m2"]))
