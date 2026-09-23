"""Sensor faults (M21, Phase 9). Stub and off: none generated (readings pass through)."""
from __future__ import annotations

from prahari.core.contracts import Readings
from prahari.core.registry import Stage, register


@register("faults", kind="stub")
class FaultsStub(Stage):
    equation = "—"
    description = "No faults injected"

    def step(self, readings: Readings, ctx) -> Readings:
        return readings


@register("faults", kind="off")
class FaultsOff(FaultsStub):
    pass
