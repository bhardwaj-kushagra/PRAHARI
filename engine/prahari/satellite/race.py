"""Satellite baseline — real implementation (SPEC §5.11, M37, Phase 9).

Overpasses come at fixed local times (Terra 10:30 and 22:30, Aqua 13:30 and 01:30, VIIRS 13:30 and 01:30 IST). The
first overpass at which a fire's burned area has reached A_det detects it with probability 1 − p_miss; the alert
follows after the platform's processing delay (MODIS U(40, 60) min, VIIRS U(60, 90) min). Area from the M37 fallback
A(τ) = A_15 (τ/15)². The satellite model assumes an unattended fire keeps growing after the sensing model's 180-minute
smoke window ends (ASM). The whole plan is drawn when a fire ignites and is published for the race timeline (View 4).
"""
from __future__ import annotations

from prahari.core.contracts import Fires, SatelliteAlerts
from prahari.core.registry import Stage, register
from prahari.fire.growth import burned_area


def pass_minutes(start_tod_min: int, first_day: int, days: int, passes: list) -> list[tuple[int, str, str]]:
    """M37 — overpasses as (minute since run start, platform, sensor), sorted, for `days` days from `first_day`."""
    out = []
    for d in range(first_day, first_day + days):
        for p in passes:
            hh, mm = (int(v) for v in p["time"].split(":"))
            out.append((d * 1440 + hh * 60 + mm - start_tod_min, p["platform"], p["sensor"]))
    return sorted(out)


def plan_fire(t0: int, schedule: list, a15: float, a_det: float, p_miss: float, delay: dict, rng) -> dict:
    """M37 — the first overpass that sees the fire (area ≥ A_det, not missed) and its alert time; None if none."""
    looked = []
    for tp, platform, sensor in schedule:
        if tp <= t0 or float(burned_area(tp - t0, a15)) < a_det:
            continue
        seen = rng.random() >= p_miss
        looked.append({"t": tp, "platform": platform, "seen": bool(seen)})
        if seen:
            lo, hi = delay[sensor]
            return {"overpass_t": tp, "platform": platform, "sensor": sensor,
                    "alert_t": tp + float(rng.uniform(lo, hi)), "passes": looked}
    return {"overpass_t": None, "platform": None, "sensor": None, "alert_t": None, "passes": looked}


@register("satellite", kind="real")
class SatelliteReal(Stage):
    equation = "M37"
    tag = "LIT"
    description = "Fixed-time overpasses; detection above 500 m² unless missed; MODIS/VIIRS processing delay"

    def reset(self, ctx) -> None:
        p = self.params
        start = ctx.clock.start
        days = int(ctx.clock.n_ticks * ctx.tick_minutes // 1440) + int(p["horizon_days"]) + 1
        self._schedule = pass_minutes(start.hour * 60 + start.minute, 0, days, p["passes"])
        self._plans: dict[int, dict] = {}

    def step(self, fires: Fires, ctx) -> SatelliteAlerts:
        p = self.params
        new = []
        for f in fires.active:
            if f.id not in self._plans:
                self._plans[f.id] = plan_fire(f.t0, self._schedule, float(p["area_15min_m2"]), float(p["a_det_m2"]),
                                              float(p["p_miss"]), p["delay_min"], self.rng)
                new.append({"fire": int(f.id), "t0": int(f.t0), **self._plans[f.id]})
        alerts = tuple(sorted((fid, pl["alert_t"]) for fid, pl in self._plans.items() if pl["alert_t"] is not None))
        return SatelliteAlerts(alert_t=alerts, plan=tuple(new))

    def snapshot(self) -> dict:
        p = self.params
        return {"a_det_m2": p["a_det_m2"], "p_miss": p["p_miss"], "passes": len(p["passes"])}
