"""Energy — real implementation (SPEC §5.13, M41–M43, Phase 8).

Each minute every node harvests solar power on a half-sine from 06:00 to 18:00 (M42; cloudy days scale the day by
U(0.1, 0.4)), draws its sensor and MCU currents for its power mode plus the radio energy of the frames it sent this
minute (M41), and keeps the balance in a supercapacitor store (M43). Below 20% state of charge a node scans in ULP
mode; below 5% it stops (no sensing current, no transmissions) until it recovers to `resume_at`.
"""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import EnergyState
from prahari.core.registry import Stage, register
from prahari.energy.power import (MODES, mcu_current_ma, next_mode, radio_wh, sensor_current_ma, solar_day_wh,
                                  solar_power_w, usable_wh)


@register("energy", kind="real")
class EnergyReal(Stage):
    equation = "M41, M42, M43"
    tag = "VEN"
    description = "Supercapacitor store fed by a canopy-shaded panel; draw by power mode and radio airtime"

    def reset(self, ctx) -> None:
        p, n = self.params, ctx.n_nodes
        self._emax = usable_wh(float(p["capacitance_f"]), float(p["v_max"]), float(p["v_min"]), int(p["cells"]))
        self._e = np.full(n, float(p["initial_soc"]) * self._emax)
        self._mode = next_mode(self._e / self._emax, np.zeros(n, dtype=int), float(p["ulp_below"]),
                               float(p["stop_below"]), float(p["resume_at"]))
        spread = float(p["canopy_spread"])                        # ASM: per-node shade around k_canopy
        self._shade = self.rng.uniform(1.0 - spread, 1.0 + spread, n) if spread > 0 else np.ones(n)
        self._cloud: dict[int, float] = {}
        self._draw_mw = np.array([(sensor_current_ma(p, m) + mcu_current_ma(p, m)) * float(p["voltage_v"])
                                  for m in MODES])               # M41 — continuous draw per mode, mW

    def _cloud_factor(self, day: int) -> float:
        """M42 — 1 on a clear day; U(lo, hi) on a scripted or randomly cloudy day (day numbers from 1)."""
        if day not in self._cloud:
            p = self.params
            cloudy = day in p["cloudy_days"] or (float(p["cloudy_day_prob"]) > 0
                                                  and self.rng.random() < float(p["cloudy_day_prob"]))
            self._cloud[day] = float(self.rng.uniform(*p["cloudy_factor"])) if cloudy else 1.0
        return self._cloud[day]

    def step(self, inputs, ctx) -> EnergyState:
        t, _env, dl = inputs
        p, hours = self.params, ctx.tick_minutes / 60.0
        e_day = solar_day_wh(p) * self._cloud_factor(t // 1440 + 1) * self._shade
        harvest = solar_power_w(ctx.clock.tod_minutes(t), e_day) * hours                    # M42 — Wh this tick
        draw = self._draw_mw[self._mode] / 1000.0 * hours                                    # M41 — Wh this tick
        radio = np.zeros(ctx.n_nodes)
        sent = [(pk["from"], pk["toa_ms"]) for pk in dl.packets if pk.get("toa_ms")]
        if sent:
            who, toa = np.array(sent).T
            np.add.at(radio, who.astype(int), radio_wh(p, toa / 1000.0))                   # M41 — TX + RX windows
        self._e = np.clip(self._e + harvest - draw - radio, 0.0, self._emax)                 # M43 — store
        soc = self._e / self._emax
        self._mode = next_mode(soc, self._mode, float(p["ulp_below"]), float(p["stop_below"]), float(p["resume_at"]))
        return EnergyState(soc=soc, mode=self._mode.copy())

    def snapshot(self) -> dict:
        p = self.params
        return {"usable_wh": round(self._emax, 3), "solar_day_wh": round(solar_day_wh(p), 3),
                "sensor": p["sensor_kind"], "cloudy_days": list(p["cloudy_days"])}
