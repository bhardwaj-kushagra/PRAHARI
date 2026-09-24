"""Node siting (SPEC §5.1): grid and corridor layouts (M1) and greedy maximum-coverage siting (M4).

Real: builds all three layouts, scores each by the fraction of ignition intensity within
the detection radius, and returns the one `world.layout` selects. Stub: grid only (the
SPEC §7 Phase 1 fallback). Off is not allowed: the run needs node positions.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import correlate
from scipy.spatial import cKDTree

from prahari.core.contracts import Landscape, Layout
from prahari.core.registry import Stage, register
from prahari.world.geometry import corridor_layout, grid_layout, grid_origin


def covered_fraction(centres, weights, sites, r_d: float) -> float:
    """M4 objective — Σ_x λ(x)·1[min_s ‖x − s‖ ≤ r_d] / Σ_x λ(x), over raster cell centres."""
    total = float(weights.sum())
    if total <= 0 or len(sites) == 0:
        return 0.0
    d, _ = cKDTree(np.asarray(sites, dtype=float)).query(centres, k=1)
    return float(weights[d <= r_d + 1e-9].sum() / total)


def disk_kernel(r_d: float, cell_m: float) -> np.ndarray:
    """Cells whose centres lie within r_d of the centre cell (same rule as covered_fraction)."""
    r = int(np.floor(r_d / cell_m))
    di, dj = np.meshgrid(np.arange(-r, r + 1), np.arange(-r, r + 1), indexing="ij")
    return (di * di + dj * dj) * cell_m * cell_m <= r_d * r_d + 1e-9


def greedy_sites(lam, forest, cell_m: float, x0: float, y0: float, n: int, r_d: float) -> np.ndarray:
    """M4 — greedy maximum coverage: add the forest cell with the largest marginal covered λ, n times.

    The marginal gain of every candidate is one correlation of λ·uncovered with the detection
    disk. Greedy is within (1 − 1/e) of the optimum (submodular maximisation, LIT).
    Ties go to the lowest row-major index, so the result is deterministic. Returns (n, 2).
    """
    ker = disk_kernel(r_d, cell_m)
    r = ker.shape[0] // 2
    ny, nx = lam.shape
    w = np.where(forest, lam, 0.0)
    uncovered = np.ones_like(forest, dtype=bool)
    chosen = np.zeros_like(forest, dtype=bool)
    sites = np.empty((n, 2))
    for k in range(n):
        gain = correlate(w * uncovered, ker.astype(float), mode="constant", cval=0.0)
        gain[~forest | chosen] = -1.0
        i, j = divmod(int(np.argmax(gain)), nx)
        chosen[i, j] = True
        i0, i1, j0, j1 = max(i - r, 0), min(i + r + 1, ny), max(j - r, 0), min(j + r + 1, nx)
        uncovered[i0:i1, j0:j1] &= ~ker[i0 - i + r:i1 - i + r, j0 - j + r:j1 - j + r]
        sites[k] = (x0 + j * cell_m, y0 + i * cell_m)
    return sites


def corridor_lines(features: list, classes) -> tuple[list, list]:
    """Polylines of the chosen interface classes (closed rings closed), and every closed ring."""
    lines, rings = [], []
    for f in features:
        pts = np.asarray(f["points"], dtype=float)
        if f.get("closed", False):
            rings.append(pts)
            pts = np.vstack([pts, pts[:1]])
        if f["kind"] in classes:
            lines.append(pts)
    return lines, rings


def world_grid(world: dict) -> np.ndarray:
    """M1 grid at `world.spacing_m`, placed at `world.offset_m` or centred when that is null."""
    n, s = world["n_nodes"], world["spacing_m"]
    return grid_layout(n, s) + grid_origin(n, s, world["width_m"], world["height_m"], world["offset_m"])


@register("siting", kind="real")
class SitingReal(Stage):
    equation = "M1, M4"
    tag = "ASM"
    description = "Grid, corridor and greedy maximum-coverage layouts, scored by covered ignition likelihood"

    def step(self, inputs, ctx) -> Layout:
        world, land = inputs
        p = self.params
        n, r_d = int(world["n_nodes"]), float(p["detection_radius_m"])
        centres, weights = land.centres(), (land.lam * land.forest).ravel()
        layouts, s_eff = {}, 0.0
        try:
            layouts["grid"] = world_grid(world)
        except ValueError:
            pass                                     # non-square N: no grid to compare against
        lines, rings = corridor_lines(world["interfaces"], p["corridor_classes"])
        if lines:
            layouts["corridor"], s_eff = corridor_layout(lines, n, world["spacing_m"], p["corridor_offset_m"], rings)
        layouts["greedy"] = greedy_sites(land.lam, land.forest, land.cell_m, land.x0, land.y0, n, r_d)
        active = world["layout"]
        if active not in layouts:
            raise ValueError(f"layout '{active}' could not be built (check world.interfaces and siting.corridor_classes)")
        alts = {k: {"xy": xy, "covered": covered_fraction(centres, weights, xy, r_d)} for k, xy in layouts.items()}
        return Layout(name=active, xy=layouts[active], covered=alts[active]["covered"], alternatives=alts,
                      corridor_spacing_m=float(s_eff))


@register("siting", kind="stub")
class SitingStub(Stage):
    equation = "M1 (grid)"
    tag = "ASM"
    description = "Grid layout only"

    def step(self, inputs, ctx) -> Layout:
        world, _ = inputs
        xy = world_grid(world)
        return Layout(name="grid", xy=xy, alternatives={"grid": {"xy": xy, "covered": -1.0}})


def check_layout_inside(layout: Layout, land: Landscape) -> None:
    """Raise when any node lies outside the map (used as a runner check)."""
    xy = layout.xy
    if (xy < 0).any() or (xy[:, 0] > land.width_m).any() or (xy[:, 1] > land.height_m).any():
        raise ValueError("layout places nodes outside the map")
