"""Fine Fuel Moisture Code stage (SPEC §5.2). Stub and off: constant FFMC. Real M7: Phase 2."""
from __future__ import annotations

from prahari.core.contracts import FuelState
from prahari.core.registry import Stage, register


@register("ffmc", kind="stub")
class FFMCStub(Stage):
    equation = "—"
    tag = "ASM"
    description = "Constant FFMC"

    def step(self, weather, ctx) -> FuelState:
        return FuelState(ffmc=float(self.params["constant_ffmc"]))


@register("ffmc", kind="off")
class FFMCOff(FFMCStub):
    description = "Constant FFMC (off)"
