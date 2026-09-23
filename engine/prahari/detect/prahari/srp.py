"""Situational risk prior, SRP (SPEC §5.9). Real M33: Phase 6/9. Stub and off: constant prior odds."""
from __future__ import annotations

from prahari.core.contracts import Prior
from prahari.core.registry import Stage, register


@register("srp", kind="stub")
class SrpStub(Stage):
    equation = "—"
    tag = "TGT"
    description = "Constant prior odds from configuration"

    def step(self, inputs, ctx) -> Prior:
        return Prior(odds=float(self.params["prior_odds"]), day_type=self.params["day_type"])


@register("srp", kind="off")
class SrpOff(SrpStub):
    pass
