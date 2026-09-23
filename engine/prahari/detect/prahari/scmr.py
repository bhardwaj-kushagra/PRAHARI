"""Spatial common-mode rejection, SCMR (SPEC §5.9). Real M31: Phase 6. Stub and off: always pass."""
from __future__ import annotations

from prahari.core.contracts import Clusters, Scmr
from prahari.core.registry import Stage, register


@register("scmr", kind="stub")
class ScmrStub(Stage):
    equation = "—"
    tag = "ASM"
    description = "Always pass"

    def step(self, clusters: Clusters, ctx) -> Scmr:
        k = len(clusters.members)
        return Scmr(f_loc=(0.0,) * k, f_net=(0.0,) * k, ratio=(0.0,) * k, passed=(True,) * k)


@register("scmr", kind="off")
class ScmrOff(ScmrStub):
    pass
