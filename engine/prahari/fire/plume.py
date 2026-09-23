"""Smoke transport (SPEC §5.5). Stub: legacy exponential-directional model (M12, M13, M16). Off: no smoke.

The Gaussian plume (M11, M14, M15) is the real upgrade, in `fire/gaussian.py` (Phase 3b).
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


def plume_at_nodes(xy, sx, sy, age, q_max, tau_g, wind_ms, wind_dir_deg, decay_length_m, per_fire=None):
    """M12 with M16 delay for M fires at N nodes, before intermittency. Returns (M, N).

    `per_fire` (legacy injection, as the report simulation): (downwind unit vectors (M, 2), speeds (M,) in m/min)
    that replace the weather wind for each fire."""
    v = xy[None, :, :] - np.stack([sx, sy], axis=1)[:, None, :]        # (M, N, 2) fire -> node
    d = np.hypot(v[..., 0], v[..., 1]) + 1e-6
    if per_fire is None:
        w = np.broadcast_to(downwind_unit(wind_dir_deg), (len(sx), 2))
        u = np.full(len(sx), max(wind_ms, 1e-3) * 60.0)                   # m/min
    else:
        w, u = per_fire
    cosphi = (v[..., 0] * w[:, 0:1] + v[..., 1] * w[:, 1:2]) / d
    tau = age[:, None] - d / u[:, None]                                    # M16 — transport delay d/u
    q = source_strength(tau, q_max[:, None], tau_g)
    return legacy_concentration(q, d, cosphi, decay_length_m)


@register("plume", kind="stub")
class PlumeStub(Stage):
    equation = "M12, M13, M16"
    tag = "ASM"
    description = "Exponential-decay directional plume with mean-one lognormal intermittency"

    def _per_fire(self, src):
        """Legacy injection (`wind: per_fire`, the report simulation): each fire gets a constant random downwind
        direction θ ~ U(0, 2π) and speed u ~ U(30, 120) m/min, drawn when it is first seen."""
        if self.params.get("wind", "weather") != "per_fire":
            return None
        if not hasattr(self, "_fire_wind"):
            self._fire_wind = {}
        lo, hi = self.params["per_fire_speed_m_min"]
        for i in src.ids:
            if i not in self._fire_wind:
                th = self.rng.uniform(0.0, 2.0 * np.pi)
                self._fire_wind[i] = (np.cos(th), np.sin(th), self.rng.uniform(lo, hi))
        vals = np.array([self._fire_wind[i] for i in src.ids], dtype=float)
        return vals[:, :2], vals[:, 2]

    def step(self, inputs, ctx) -> Concentration:
        src, env = inputs
        n = ctx.n_nodes
        if not src.ids:
            return Concentration(c=np.zeros(n))
        c = plume_at_nodes(ctx.xy, src.x, src.y, src.age_min, src.q_max, src.tau_g,
                           env.wind_ms, env.wind_dir_deg, self.params["decay_length_m"], self._per_fire(src))
        s = self.params["intermittency_sigma"]
        eps = np.exp(self.rng.normal(0.0, s, c.shape) - s * s / 2.0)       # M12 — ε mean-one intermittency
        return Concentration(c=(c * eps).sum(axis=0))                      # multiple fires add linearly

    def field(self, points, src, env):
        """Mean concentration at arbitrary points (no intermittency), for the dashboard plume grid (SPEC §5.5)."""
        if not src.ids:
            return np.zeros(len(points))
        return plume_at_nodes(np.asarray(points, dtype=float), src.x, src.y, src.age_min, src.q_max, src.tau_g,
                              env.wind_ms, env.wind_dir_deg, self.params["decay_length_m"], self._per_fire(src)).sum(axis=0)


@register("plume", kind="off")
class PlumeOff(Stage):
    description = "No smoke reaches sensors"

    def step(self, inputs, ctx) -> Concentration:
        return Concentration(c=np.zeros(ctx.n_nodes))

    def field(self, points, src, env):
        return np.zeros(len(points))
