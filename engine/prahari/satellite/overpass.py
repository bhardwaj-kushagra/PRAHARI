"""Satellite baseline (SPEC §5.11). Real M37: Phase 9. Stub: alert a fixed delay after ignition. Off: not shown."""
from __future__ import annotations

from prahari.core.contracts import Fires, SatelliteAlerts
from prahari.core.registry import Stage, register


@register("satellite", kind="stub")
class SatelliteStub(Stage):
    equation = "—"
    tag = "ASM"
    description = "Alert a fixed time after ignition"

    def reset(self, ctx) -> None:
        self._alerts: dict[int, float] = {}

    def step(self, fires: Fires, ctx) -> SatelliteAlerts:
        for f in fires.active:
            self._alerts.setdefault(f.id, float(f.t0 + self.params["fixed_delay_min"]))
        return SatelliteAlerts(alert_t=tuple(sorted(self._alerts.items())))


@register("satellite", kind="off")
class SatelliteOff(Stage):
    description = "Not shown"

    def step(self, fires: Fires, ctx) -> SatelliteAlerts:
        return SatelliteAlerts()
