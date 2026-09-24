"""World geometry (SPEC §5.1): node layouts (M1). Greedy siting (M4) lives in `world/siting.py`."""
from __future__ import annotations

import numpy as np

from prahari.world.interfaces import inside_polygon


def grid_layout(n_nodes: int, spacing_m: float, offset_m: float = 0.0) -> np.ndarray:
    """M1 — grid layout: node (a, b) at (a s, b s) for a, b = 0 .. sqrt(N) - 1. Returns (N, 2)."""
    side = int(round(np.sqrt(n_nodes)))
    if side * side != n_nodes:
        raise ValueError(f"grid layout needs a square node count, got {n_nodes}")
    g = np.arange(side, dtype=float) * spacing_m + offset_m
    a, b = np.meshgrid(g, g, indexing="ij")          # node id = a_index * side + b_index, as in the oracle
    return np.column_stack([a.ravel(), b.ravel()])


def grid_origin(n_nodes: int, spacing_m: float, width_m: float, height_m: float, offset_m=None) -> np.ndarray:
    """Origin of the M1 grid: `offset_m` on both axes, or centred in the map when it is None."""
    if offset_m is not None:
        return np.array([float(offset_m), float(offset_m)])
    extent = (int(round(np.sqrt(n_nodes))) - 1) * spacing_m
    return np.array([(width_m - extent) / 2.0, (height_m - extent) / 2.0])


def _chain(polylines):
    """Concatenate polylines into one list of segments with cumulative arc length."""
    segs = np.vstack([np.hstack([p[:-1], p[1:]]) for p in polylines])
    seg_len = np.hypot(segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1])
    keep = seg_len > 0
    return segs[keep], seg_len[keep]


def corridor_layout(polylines, n_nodes: int, spacing_m: float, offset_m: float, rings=()):
    """M1 — corridor: nodes every s metres along interface polylines, alternating a lateral offset of ±d.

    `polylines` is a list of (K, 2) arrays (closed rings already closed). When the lines are
    shorter than N·s the spacing becomes L/N so that exactly N nodes fit (DER). A node whose
    offset lands inside one of `rings` (closed polygons, e.g. a village) takes the other side.
    Returns (xy (N, 2), effective spacing).
    """
    segs, seg_len = _chain([np.asarray(p, dtype=float) for p in polylines])
    total = float(seg_len.sum())
    s_eff = min(spacing_m, total / n_nodes)
    arc = s_eff * (np.arange(n_nodes) + 0.5)
    cum = np.concatenate([[0.0], np.cumsum(seg_len)])
    k = np.clip(np.searchsorted(cum, arc, side="right") - 1, 0, len(seg_len) - 1)
    u = (arc - cum[k]) / seg_len[k]
    base = segs[k, :2] + u[:, None] * (segs[k, 2:] - segs[k, :2])
    tangent = (segs[k, 2:] - segs[k, :2]) / seg_len[k][:, None]
    normal = np.column_stack([-tangent[:, 1], tangent[:, 0]])
    sign = np.where(np.arange(n_nodes) % 2 == 0, 1.0, -1.0)
    xy = base + (sign * offset_m)[:, None] * normal
    for ring in rings:
        flip = inside_polygon(xy[:, 0], xy[:, 1], ring)
        xy = np.where(flip[:, None], base - (sign * offset_m)[:, None] * normal, xy)
    return xy, s_eff


def neighbourhood_radius(spacing_m: float, factor: float) -> float:
    """M30 — neighbourhood radius R = factor × s (default factor 1.6)."""
    return factor * spacing_m
