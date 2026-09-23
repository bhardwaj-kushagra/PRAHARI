"""World geometry (SPEC §5.1). Phase 0 provides the grid layout only; corridor and greedy siting arrive in Phase 1."""
from __future__ import annotations

import numpy as np


def grid_layout(n_nodes: int, spacing_m: float, offset_m: float = 0.0) -> np.ndarray:
    """M1 — grid layout: node (a, b) at (a s, b s) for a, b = 0 .. sqrt(N) - 1. Returns (N, 2)."""
    side = int(round(np.sqrt(n_nodes)))
    if side * side != n_nodes:
        raise ValueError(f"grid layout needs a square node count, got {n_nodes}")
    g = np.arange(side, dtype=float) * spacing_m + offset_m
    a, b = np.meshgrid(g, g, indexing="ij")          # node id = a_index * side + b_index, as in the oracle
    return np.column_stack([a.ravel(), b.ravel()])


def neighbourhood_radius(spacing_m: float, factor: float) -> float:
    """M30 — neighbourhood radius R = factor × s (default factor 1.6)."""
    return factor * spacing_m
