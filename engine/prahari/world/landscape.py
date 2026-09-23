"""Landscape stage (SPEC §5.1): the static ignition-intensity map.

Real: M2 distance fields and M3 static intensity. Stub and off: uniform intensity over the whole map.
"""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import Landscape
from prahari.core.registry import Stage, register
from prahari.world.interfaces import distance_fields, excluded_mask, raster_centres


def static_lambda(dist: dict, weights: dict, decay_m: dict, lambda0: float, activity: float = 1.0):
    """M3 — λ(x) = λ₀ a(t) Σ_k w_k exp(−D_k(x) / L_k), without the lightning term.

    Classes absent from `dist` contribute nothing (D_k = ∞). `activity` is a(t); the static
    map uses a = 1, and coverage fractions do not depend on λ₀ or a(t).
    """
    total = None
    for k, d in dist.items():
        term = weights[k] * np.exp(-d / decay_m[k])
        total = term if total is None else total + term
    if total is None:
        raise ValueError("no interfaces: M3 needs at least one interface class")
    return lambda0 * activity * total


@register("landscape", kind="real")
class LandscapeReal(Stage):
    equation = "M2, M3"
    tag = "ASM"
    description = "Distance fields to paths, village, road and power line; static ignition intensity"

    def step(self, world: dict, ctx) -> Landscape:
        p = self.params
        x0, y0, nx, ny = raster_centres(world["width_m"], world["height_m"], p["raster_m"])
        gx, gy = np.meshgrid(x0 + p["raster_m"] * np.arange(nx), y0 + p["raster_m"] * np.arange(ny))
        px, py = gx.ravel(), gy.ravel()
        feats = world["interfaces"]
        dist = distance_fields(px, py, feats)                                  # M2
        lam = static_lambda(dist, p["weights"], p["decay_m"], p["lambda0"])     # M3
        forest = ~excluded_mask(px, py, feats, tuple(p["non_forest"]))
        lam = np.where(forest, lam, 0.0)
        return Landscape(cell_m=float(p["raster_m"]), x0=x0, y0=y0, lam=lam.reshape(ny, nx),
                         forest=forest.reshape(ny, nx), width_m=float(world["width_m"]),
                         height_m=float(world["height_m"]),
                         dist={k: v.reshape(ny, nx) for k, v in dist.items()})


@register("landscape", kind="stub")
class LandscapeStub(Stage):
    equation = "—"
    tag = "ASM"
    description = "Uniform ignition intensity everywhere"

    def step(self, world: dict, ctx) -> Landscape:
        p = self.params
        x0, y0, nx, ny = raster_centres(world["width_m"], world["height_m"], p["raster_m"])
        return Landscape(cell_m=float(p["raster_m"]), x0=x0, y0=y0, lam=np.full((ny, nx), float(p["lambda0"])),
                         forest=np.ones((ny, nx), dtype=bool), width_m=float(world["width_m"]),
                         height_m=float(world["height_m"]), modelled=False)


@register("landscape", kind="off")
class LandscapeOff(LandscapeStub):
    description = "Uniform ignition intensity (off)"
