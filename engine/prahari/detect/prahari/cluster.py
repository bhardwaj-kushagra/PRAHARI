"""Candidate clustering (SPEC §5.9). Real M30 connected components: Phase 6.

Stub and off: every candidate in the window forms one cluster. The edge is
evaluated only on ticks when new candidates arrive.
"""
from __future__ import annotations

from collections import deque

from prahari.core.contracts import Clusters, Delivered
from prahari.core.registry import Stage, register


@register("cluster", kind="stub")
class ClusterStub(Stage):
    equation = "—"
    tag = "ASM"
    description = "All candidates in the window form one cluster"

    def reset(self, ctx) -> None:
        self._recent: deque = deque()      # (t, node, p)

    def step(self, delivered: Delivered, ctx) -> Clusters:
        t, w = ctx.t, self.params["window_min"]
        for i, p in zip(delivered.nodes, delivered.p):
            self._recent.append((t, int(i), float(p)))
        while self._recent and self._recent[0][0] <= t - w:
            self._recent.popleft()
        if not delivered.nodes:
            return Clusters()
        best: dict[int, float] = {}
        for _, i, p in self._recent:
            best[i] = min(p, best.get(i, 1.0))
        members = tuple(sorted(best))
        return Clusters(members=(members,), p=(tuple(best[i] for i in members),))

    def recent_nodes(self) -> set:
        """Nodes with a candidate still inside the cluster window."""
        return {i for _, i, _ in self._recent}

    def snapshot(self) -> dict:
        return {"window": len(self._recent)}


@register("cluster", kind="off")
class ClusterOff(ClusterStub):
    pass
