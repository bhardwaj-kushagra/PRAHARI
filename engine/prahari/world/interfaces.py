"""Ignition interfaces and distance fields (SPEC §5.1, M2).

Interfaces come from configuration as {kind, points, closed}. Open features
(path, road, power line) are polylines; closed features (village) are polygons
whose interior is at distance 0. Pure functions: arrays in, arrays out.
"""
from __future__ import annotations

import numpy as np

CLASSES = ("path", "village", "road", "power_line")


def raster_centres(width_m: float, height_m: float, cell_m: float):
    """Cell centres of a raster covering [0, W] × [0, H]. Returns (x0, y0, nx, ny)."""
    nx = int(round(width_m / cell_m))
    ny = int(round(height_m / cell_m))
    return cell_m / 2.0, cell_m / 2.0, nx, ny


def segments(points, closed: bool = False) -> np.ndarray:
    """(S, 4) segments [x1, y1, x2, y2] of a polyline, closing the ring when `closed`."""
    p = np.asarray(points, dtype=float)
    if closed:
        p = np.vstack([p, p[:1]])
    return np.hstack([p[:-1], p[1:]])


def point_segment_distance(px, py, segs) -> np.ndarray:
    """M2 — Euclidean distance from each point to the nearest of the segments. Returns (P,)."""
    px = np.asarray(px, dtype=float)[:, None]
    py = np.asarray(py, dtype=float)[:, None]
    x1, y1, x2, y2 = (segs[:, k][None, :] for k in range(4))
    dx, dy = x2 - x1, y2 - y1
    len2 = dx * dx + dy * dy
    t = np.where(len2 > 0, ((px - x1) * dx + (py - y1) * dy) / np.where(len2 > 0, len2, 1.0), 0.0)
    t = np.clip(t, 0.0, 1.0)
    return np.hypot(px - (x1 + t * dx), py - (y1 + t * dy)).min(axis=1)


def inside_polygon(px, py, points) -> np.ndarray:
    """Even–odd rule point-in-polygon test, vectorised over points. Returns (P,) bool."""
    px = np.asarray(px, dtype=float)[:, None]
    py = np.asarray(py, dtype=float)[:, None]
    s = segments(points, closed=True)
    x1, y1, x2, y2 = (s[:, k][None, :] for k in range(4))
    straddles = (y1 > py) != (y2 > py)
    with np.errstate(divide="ignore", invalid="ignore"):
        x_cross = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
    return (straddles & (px < x_cross)).sum(axis=1) % 2 == 1


def feature_distance(px, py, feature: dict) -> np.ndarray:
    """M2 — distance to one feature; 0 inside a closed feature."""
    closed = bool(feature.get("closed", False))
    d = point_segment_distance(px, py, segments(feature["points"], closed))
    if closed:
        d = np.where(inside_polygon(px, py, feature["points"]), 0.0, d)
    return d


def distance_fields(px, py, features: list) -> dict:
    """M2 — D_k(x) for every interface class k present in `features`. Returns {kind: (P,)}."""
    out: dict[str, np.ndarray] = {}
    for f in features:
        kind = f["kind"]
        if kind not in CLASSES:
            raise ValueError(f"unknown interface kind {kind!r}; expected one of {CLASSES}")
        d = feature_distance(px, py, f)
        out[kind] = np.minimum(out[kind], d) if kind in out else d
    return out


def excluded_mask(px, py, features: list, kinds=("village",)) -> np.ndarray:
    """True for points inside closed features of the given kinds (not forest: no nodes, no ignitions)."""
    m = np.zeros(np.asarray(px).shape[0], dtype=bool)
    for f in features:
        if f["kind"] in kinds and f.get("closed", False):
            m |= inside_polygon(px, py, f["points"])
    return m
