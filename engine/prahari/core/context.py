"""Run context shared by all stages: geometry, clock and the current tick."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from prahari.core.clock import Clock


@dataclass
class RunContext:
    clock: Clock
    xy: np.ndarray                   # (N, 2) node positions, m
    spacing_m: float
    radius_m: float                  # neighbourhood radius R = 1.6 s (M30)
    gateways: list = field(default_factory=list)
    t: int = 0                       # minutes since start
    tick: int = 0
    landscape: object = None         # Landscape from the setup modules (Phase 3a: ignition needs λ)
    z_slow: object = None            # latest TTC slow z (N, C), set by the pipeline; M28 common-mode exclusion

    @property
    def n_nodes(self) -> int:
        return int(self.xy.shape[0])

    @property
    def tick_minutes(self) -> int:
        return self.clock.tick_minutes

    @property
    def dist(self) -> np.ndarray:
        """(N, N) node-to-node distances, computed once."""
        if not hasattr(self, "_dist"):
            d = self.xy[:, None, :] - self.xy[None, :, :]
            self._dist = np.hypot(d[..., 0], d[..., 1])
        return self._dist

    @property
    def neighbours(self) -> np.ndarray:
        """(N, N) bool, True when two nodes are within R (a node is its own neighbour)."""
        if not hasattr(self, "_nbr"):
            self._nbr = self.dist <= self.radius_m
        return self._nbr
