"""Fisher combination (SPEC §5.9). Real M32: Phase 6.

Stub: Bonferroni, p_C = min(1, |C| · min p). Off: p_C = min p.
"""
from __future__ import annotations

from prahari.core.contracts import Clusters, Fisher
from prahari.core.registry import Stage, register


def bonferroni(p) -> float:
    return min(1.0, len(p) * min(p))


@register("fisher", kind="stub")
class FisherStub(Stage):
    equation = "—"
    tag = "ASM"
    description = "Bonferroni: minimum p times cluster size"

    def step(self, clusters: Clusters, ctx) -> Fisher:
        pc = tuple(bonferroni(p) for p in clusters.p)
        return Fisher(X=(0.0,) * len(pc), dof=(0,) * len(pc), p_cluster=pc)


@register("fisher", kind="off")
class FisherOff(Stage):
    description = "Minimum p-value"

    def step(self, clusters: Clusters, ctx) -> Fisher:
        pc = tuple(min(p) for p in clusters.p)
        return Fisher(X=(0.0,) * len(pc), dof=(0,) * len(pc), p_cluster=pc)
