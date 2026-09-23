"""Fine Fuel Moisture Code stage (SPEC §5.2). Real: M7 daily FFMC. Stub and off: constant FFMC."""
from __future__ import annotations

from collections import deque

import numpy as np

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


def ffmc_daily(ffmc_yda, T, H, W_kmh, rain_mm, coef: float):
    """M7 — daily Fine Fuel Moisture Code (Van Wagner & Pickett 1985 eqs. 1–10; Van Wagner 1987).

    `coef` is the moisture-conversion constant: 250·59.5/101 = 147.277 as in cffdrs (erratum E-6;
    the SPEC's earlier 147.2 misses the cffdrs reference by up to 0.12). Vectorised; wind in km/h.
    """
    F = np.asarray(ffmc_yda, dtype=float)
    T, H, W, ro = (np.asarray(v, dtype=float) for v in (T, H, W_kmh, rain_mm))
    mo = coef * (101.0 - F) / (59.5 + F)                                               # eq. 1
    rf = np.where(ro > 0.5, ro - 0.5, 1.0)                                              # eq. 2
    add = 42.5 * rf * np.exp(-100.0 / (251.0 - mo)) * (1.0 - np.exp(-6.93 / rf))       # eq. 3a
    add = add + np.where(mo > 150.0, 0.0015 * (mo - 150.0) ** 2 * np.sqrt(rf), 0.0)     # eq. 3b
    mo = np.where(ro > 0.5, np.minimum(mo + add, 250.0), mo)
    wet = 1.0 - np.exp(-0.115 * H)
    ed = 0.942 * H ** 0.679 + 11.0 * np.exp((H - 100.0) / 10.0) + 0.18 * (21.1 - T) * wet   # eq. 4
    ew = 0.618 * H ** 0.753 + 10.0 * np.exp((H - 100.0) / 10.0) + 0.18 * (21.1 - T) * wet  # eq. 5
    temp = 0.581 * np.exp(0.0365 * T)
    kd = (0.424 * (1 - (H / 100.0) ** 1.7) + 0.0694 * np.sqrt(W) * (1 - (H / 100.0) ** 8)) * temp       # eq. 6
    kw = (0.424 * (1 - ((100.0 - H) / 100.0) ** 1.7)
          + 0.0694 * np.sqrt(W) * (1 - ((100.0 - H) / 100.0) ** 8)) * temp                            # eq. 7
    m = np.where(mo > ed, ed + (mo - ed) * 10.0 ** (-kd),                               # eq. 8 drying
                 np.where(mo < ew, ew - (ew - mo) * 10.0 ** (-kw), mo))                 # eq. 9 wetting
    return np.clip(59.5 * (250.0 - m) / (coef + m), 0.0, 101.0)                          # eq. 10


@register("ffmc", kind="real")
class FFMCReal(Stage):
    equation = "M7"
    tag = "LIT"
    description = "Daily FFMC at noon (Van Wagner 1987), verified against cffdrs"

    def reset(self, ctx) -> None:
        self._F = float(self.params["startup_ffmc"])
        self._rain = deque()                     # (t, mm) over the last 24 h
        self._rain_sum = 0.0

    def step(self, env, ctx) -> FuelState:
        t = ctx.t
        if env.rain_mm > 0:
            self._rain.append((t, env.rain_mm))
            self._rain_sum += env.rain_mm
        while self._rain and self._rain[0][0] <= t - 1440:
            self._rain_sum -= self._rain.popleft()[1]
        if ctx.clock.tod_minutes(t) == int(self.params["update_minute"]):
            self._F = float(ffmc_daily(self._F, env.T, env.RH, env.wind_ms * 3.6, max(self._rain_sum, 0.0),
                                       self.params["coefficient"]))
        return FuelState(ffmc=self._F)

    def snapshot(self) -> dict:
        return {"ffmc": self._F, "rain_24h_mm": self._rain_sum}
