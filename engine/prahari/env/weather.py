"""Weather stage (SPEC §5.2). Real: M5 diurnal weather and M6 humidity. Stub: constant weather (SPEC §4.2)."""
from __future__ import annotations

import numpy as np

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


def magnus_rh(T, dew):
    """M6 — RH = 100 · exp(17.625 T_dew / (243.04 + T_dew)) / exp(17.625 T / (243.04 + T))."""
    T = np.asarray(T, dtype=float)
    dew = np.asarray(dew, dtype=float)
    return 100.0 * np.exp(17.625 * dew / (243.04 + dew)) / np.exp(17.625 * T / (243.04 + T))


def diurnal_temperature(t_bar, amp, hour):
    """M5 — T̄_d + A_T sin(2π (h − 9) / 24): minimum near 03:00, maximum at 15:00."""
    return t_bar + amp * np.sin(2.0 * np.pi * (np.asarray(hour, dtype=float) - 9.0) / 24.0)


def ar1_step(x, phi: float, sd_stationary: float, z):
    """AR(1) with a given stationary standard deviation: x ← φ x + σ √(1 − φ²) z."""
    return phi * x + sd_stationary * np.sqrt(1.0 - phi * phi) * z


@register("weather", kind="real")
class WeatherReal(Stage):
    equation = "M5, M6"
    tag = "ASM"
    description = "Diurnal temperature with AR(1) noise, dew point and Magnus RH, lognormal wind, rain events"

    def reset(self, ctx) -> None:
        p = self.params
        rng = self.rng
        self._start = ctx.clock.start.date()
        self._day = None
        self._t_dev = rng.normal(0.0, p["day_sd_c"])
        self._dew_dev = rng.normal(0.0, p["day_sd_c"])
        self._eps = rng.normal(0.0, p["noise_sd_c"])
        self._eta = rng.normal(0.0, p["wind_sigma_log"])
        self._dir = rng.normal(0.0, p["dir_sd_deg"])
        self._rain: list[tuple[int, int, float]] = []          # (start, end, mm per minute)

    def _new_day(self, day: int, t: int, tod: int) -> None:
        p, rng = self.params, self.rng
        self._t_dev = ar1_step(self._t_dev, p["day_phi"], p["day_sd_c"], rng.normal())
        self._dew_dev = ar1_step(self._dew_dev, p["day_phi"], p["day_sd_c"], rng.normal())
        if rng.random() < p["rain_prob_day"]:
            start = t - tod + int(rng.integers(0, 1440))
            dur = int(rng.integers(p["rain_duration_min"][0], p["rain_duration_min"][1] + 1))
            amount = float(np.exp(rng.normal(np.log(p["rain_median_mm"]), p["rain_sigma_log"])))
            self._rain.append((start, start + dur, amount / dur))
        self._rain = [r for r in self._rain if r[1] > t]
        self._day = day

    def step(self, t, ctx) -> Weather:
        p, rng = self.params, self.rng
        wall = ctx.clock.wall(t)
        tod = wall.hour * 60 + wall.minute
        day = (wall.date() - self._start).days
        if day != self._day:
            self._new_day(day, t, tod)
        z = rng.normal(size=3)
        self._eps = ar1_step(self._eps, p["noise_phi"], p["noise_sd_c"], z[0])            # M5 — ε_T AR(1)
        self._eta = ar1_step(self._eta, p["wind_phi"], p["wind_sigma_log"], z[1])
        self._dir = ar1_step(self._dir, p["dir_phi"], p["dir_sd_deg"], z[2])
        T = float(diurnal_temperature(p["t_mean_c"] + self._t_dev, p["t_amp_c"], tod / 60.0) + self._eps)
        dew = min(p["dew_point_c"] + self._dew_dev, T)
        rh = float(np.clip(magnus_rh(T, dew), 1.0, 100.0))                                  # M6
        rain = sum(rate for s, e, rate in self._rain if s <= t < e) * ctx.tick_minutes
        return Weather(T=T, RH=rh, wind_ms=float(p["wind_median_ms"] * np.exp(self._eta)),
                       wind_dir_deg=float((p["prevailing_dir_deg"] + self._dir) % 360.0),
                       rain_mm=float(rain), dew_c=float(dew))
