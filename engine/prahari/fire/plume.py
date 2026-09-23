"""Smoke transport (SPEC §5.5). Stub: legacy exponential-directional model (M12, M13, M16). Off: no smoke.

The Gaussian plume (M11, M14, M15) is the optional real upgrade in Phase 3b.
"""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import Concentration
from prahari.core.registry import Stage, register
from prahari.fire.growth import source_strength


def directional_factor(cosphi):
    """M13 — h(φ) = 0.1 + 0.9 ((1 + cos φ) / 2)²."""
    return 0.1 + 0.9 * ((1.0 + np.asarray(cosphi, dtype=float)) / 2.0) ** 2


def downwind_unit(wind_dir_deg: float) -> np.ndarray:
    """Unit vector the smoke travels along, for a meteorological 'from' direction (x east, y north)."""
    th = np.deg2rad(wind_dir_deg)
    return np.array([-np.sin(th), -np.cos(th)])


def legacy_concentration(q, d, cosphi, decay_length_m):
    """M12 — C = Q · exp(−d/L) · h(φ), before intermittency."""
    return q * np.exp(-np.asarray(d, dtype=float) / decay_length_m) * directional_factor(cosphi)


def plume_at_nodes(xy, sx, sy, age, q_max, tau_g, wind_ms, wind_dir_deg, decay_length_m):
    """M12 with M16 delay for M fires at N nodes, before intermittency. Returns (M, N)."""
    v = xy[None, :, :] - np.stack([sx, sy], axis=1)[:, None, :]        # (M, N, 2) fire -> node
    d = np.hypot(v[..., 0], v[..., 1]) + 1e-6
    w = downwind_unit(wind_dir_deg)
    cosphi = (v[..., 0] * w[0] + v[..., 1] * w[1]) / d
    u = max(wind_ms, 1e-3) * 60.0                                          # m/min
    tau = age[:, None] - d / u                                             # M16 — transport delay d/u
    q = source_strength(tau, q_max[:, None], tau_g)
    return legacy_concentration(q, d, cosphi, decay_length_m)


@register("plume", kind="stub")
class PlumeStub(Stage):
    equation = "M12, M13, M16"
    tag = "ASM"
    description = "Exponential-decay directional plume with mean-one lognormal intermittency"

    def step(self, inputs, ctx) -> Concentration:
        src, env = inputs
        n = ctx.n_nodes
        if not src.ids:
            return Concentration(c=np.zeros(n))
        c = plume_at_nodes(ctx.xy, src.x, src.y, src.age_min, src.q_max, src.tau_g,
                           env.wind_ms, env.wind_dir_deg, self.params["decay_length_m"])
        s = self.params["intermittency_sigma"]
        eps = np.exp(self.rng.normal(0.0, s, c.shape) - s * s / 2.0)       # M12 — ε mean-one intermittency
        return Concentration(c=(c * eps).sum(axis=0))                      # multiple fires add linearly

    def field(self, points, src, env):
        """Mean concentration at arbitrary points (no intermittency), for the dashboard plume grid (SPEC §5.5)."""
        if not src.ids:
            return np.zeros(len(points))
        return plume_at_nodes(np.asarray(points, dtype=float), src.x, src.y, src.age_min, src.q_max, src.tau_g,
                              env.wind_ms, env.wind_dir_deg, self.params["decay_length_m"]).sum(axis=0)


@register("plume", kind="off")
class PlumeOff(Stage):
    description = "No smoke reaches sensors"

    def step(self, inputs, ctx) -> Concentration:
        return Concentration(c=np.zeros(ctx.n_nodes))

    def field(self, points, src, env):
        return np.zeros(len(points))
