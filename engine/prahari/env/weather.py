"""Weather stage (SPEC §5.2). Stub: constant weather (SPEC §4.2). Real M5 diurnal model: Phase 2."""
from __future__ import annotations

from prahari.core.contracts import Weather
from prahari.core.registry import Stage, register


@register("weather", kind="stub")
class WeatherStub(Stage):
    equation = "—"
    tag = "ASM"
    description = "Constant 30 °C, 40% RH, 1.5 m/s wind from the west"

    def step(self, t, ctx) -> Weather:
        p = self.params
        return Weather(T=float(p["T_c"]), RH=float(p["RH_pct"]), wind_ms=float(p["wind_ms"]),
                       wind_dir_deg=float(p["wind_dir_deg"]), rain_mm=0.0)
