"""Risk-adaptive quorum, RAQ (SPEC §5.9). Real M34 decision rule: Phase 6. Stub and off: fixed quorum."""
from __future__ import annotations

from prahari.core.contracts import Raq
from prahari.core.registry import Stage, register


@register("raq", kind="stub")
class RaqStub(Stage):
    equation = "—"
    tag = "ASM"
    description = "Fixed quorum of agreeing nodes"

    def step(self, inputs, ctx) -> Raq:
        clusters, scmr, bf, prior = inputs
        q = int(self.params["fixed_quorum"])
        post = tuple(float(b * prior.odds) for b in bf.bf)
        decide = tuple(len(m) >= q and ok for m, ok in zip(clusters.members, scmr.passed))
        return Raq(quorum=q, threshold=float(self.params["cost_ratio"]), posterior_odds=post, decide=decide)


@register("raq", kind="off")
class RaqOff(RaqStub):
    pass
