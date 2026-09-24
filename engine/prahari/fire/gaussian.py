"""Gaussian plume — the real `plume` module (SPEC §5.5, Phase 3b): M11, M14, M15 and `calibrate_q()`.

The legacy exponential-directional model (M12) stays the stub and the default for golden runs;
this advanced model is selected per scenario with `modules.plume: real`.
"""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import Concentration
from prahari.core.registry import Stage, register
from prahari.fire.growth import source_strength
from prahari.fire.plume import downwind_unit

# M14 — Briggs open-country coefficients: σ = a·x·(1 + b·x)^p
BRIGGS = {
    "A": ((0.22, 0.0001, -0.5), (0.20, 0.0, 1.0)),
    "B": ((0.16, 0.0001, -0.5), (0.12, 0.0, 1.0)),
    "C": ((0.11, 0.0001, -0.5), (0.08, 0.0002, -0.5)),
    "D": ((0.08, 0.0001, -0.5), (0.06, 0.0015, -0.5)),
    "E": ((0.06, 0.0001, -0.5), (0.03, 0.0003, -1.0)),
    "F": ((0.04, 0.0001, -0.5), (0.016, 0.0003, -1.0)),
}


def briggs_sigmas(x, stability: str, floor_m: float = 1.0):
    """M14 — σ_y(x), σ_z(x) for a stability class; clamped ≥ `floor_m` below the fitted range (ASM)."""
    x = np.maximum(np.asarray(x, dtype=float), 0.0)
    (ay, by, py), (az, bz, pz) = BRIGGS[stability]
    sy = ay * x * (1.0 + by * x) ** py
    sz = az * x * (1.0 + bz * x) ** pz if pz != 1.0 else az * x
    return np.maximum(sy, floor_m), np.maximum(sz, floor_m)


def canopy_wind(u10, alpha: float, floor_ms: float):
    """M15 — u_c = α_c u10, floored at `floor_ms`."""
    return np.maximum(alpha * np.asarray(u10, dtype=float), floor_ms)


def gaussian_plume(Q, x, y, u_c, stability: str, z: float, H: float):
    """M11 — ground-reflected steady-state concentration; 0 for x ≤ 0 (upwind)."""
    x = np.asarray(x, dtype=float)
    sy, sz = briggs_sigmas(x, stability)
    vert = np.exp(-(z - H) ** 2 / (2 * sz * sz)) + np.exp(-(z + H) ** 2 / (2 * sz * sz))
    c = Q / (2 * np.pi * u_c * sy * sz) * np.exp(-np.asarray(y, dtype=float) ** 2 / (2 * sy * sy)) * vert
    return np.where(x > 0, c, 0.0)


def calibrate_q(target_su: float, x_m: float, stability: str, u_c: float, z: float, H: float) -> float:
    """M11 calibration (DER) — Q such that the ground concentration x_m downwind on the centreline, at full growth,
    equals the legacy model's value there (2.5 su at 50 m in class C)."""
    return float(target_su / gaussian_plume(1.0, x_m, 0.0, u_c, stability, z, H))


def gaussian_at_points(points, sx, sy, age, q_legacy_max, tau_g, wind_ms, wind_dir_deg, p: dict,
                       q_cal: float, stability: str):
    """Mean concentration (no intermittency) from M fires at P points. Returns (M, P).

    Source strength follows the legacy M9 ramp, rescaled so that a legacy-strength source gives the calibrated Q:
    Q(τ) = Q_cal · q(τ) · e^{−x_ref/L} / C_ref. Transport delay (M16) is x / u_c downwind and d / u_c for the floor.
    """
    v = np.asarray(points, dtype=float)[None, :, :] - np.stack([sx, sy], axis=1)[:, None, :]
    w = downwind_unit(wind_dir_deg)
    x = v[..., 0] * w[0] + v[..., 1] * w[1]                                  # downwind distance
    y = -v[..., 0] * w[1] + v[..., 1] * w[0]                                 # crosswind distance
    d = np.hypot(v[..., 0], v[..., 1])
    u_c = float(canopy_wind(wind_ms, p["canopy_alpha"], p["canopy_floor_ms"]))           # M15
    scale = q_cal * np.exp(-p["calibration_distance_m"] / p["decay_length_m"]) / p["calibration_target_su"]
    to_min = 1.0 / (u_c * 60.0)
    q_down = source_strength(age[:, None] - np.maximum(x, 0.0) * to_min, q_legacy_max[:, None], tau_g) * scale
    q_all = source_strength(age[:, None] - d * to_min, q_legacy_max[:, None], tau_g) * scale      # M16
    c = gaussian_plume(q_down, x, y, u_c, stability, p["receptor_height_m"], p["source_height_m"])   # M11
    floor = p["upwind_floor"] * gaussian_plume(q_all, np.maximum(d, 1.0), 0.0, u_c, stability,
                                               p["receptor_height_m"], p["source_height_m"])
    return np.maximum(c, floor)                                              # M13 upwind floor (~10%)


@register("plume", kind="real")
class PlumeReal(Stage):
    equation = "M11, M14, M15, M16"
    tag = "LIT"
    description = "Gaussian plume with ground reflection, Briggs σ by stability class, sub-canopy wind"

    def reset(self, ctx) -> None:
        p = self.params
        u_ref = float(canopy_wind(p["calibration_wind_ms"], p["canopy_alpha"], p["canopy_floor_ms"]))
        self.q_cal = calibrate_q(p["calibration_target_su"], p["calibration_distance_m"], p["calibration_class"],
                                 u_ref, p["receptor_height_m"], p["source_height_m"])
        self.stability = p["stability_day"]

    def _class(self, ctx) -> str:
        p = self.params
        h = ctx.clock.tod_minutes(ctx.t) / 60.0
        return p["stability_day"] if p["day_hours"][0] <= h < p["day_hours"][1] else p["stability_night"]

    def step(self, inputs, ctx) -> Concentration:
        src, env = inputs
        self.stability = self._class(ctx)
        if not src.ids:
            return Concentration(c=np.zeros(ctx.n_nodes))
        c = gaussian_at_points(ctx.xy, src.x, src.y, src.age_min, src.q_max, src.tau_g, env.wind_ms,
                               env.wind_dir_deg, self.params, self.q_cal, self.stability)
        s = self.params["intermittency_sigma"]
        eps = np.exp(self.rng.normal(0.0, s, c.shape) - s * s / 2.0)          # same mean-one intermittency as M12
        return Concentration(c=(c * eps).sum(axis=0))

    def field(self, points, src, env):
        """Mean concentration at arbitrary points, for the dashboard plume grid."""
        if not src.ids:
            return np.zeros(len(points))
        return gaussian_at_points(points, src.x, src.y, src.age_min, src.q_max, src.tau_g, env.wind_ms,
                                  env.wind_dir_deg, self.params, self.q_cal, self.stability).sum(axis=0)

    def snapshot(self) -> dict:
        return {"q_cal": round(self.q_cal, 3), "stability": self.stability}
