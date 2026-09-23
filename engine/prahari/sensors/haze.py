"""Regional haze (SPEC §5.6, M20). Real: Poisson trapezoid episodes with node gains. Stub and off: none."""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import Additive
from prahari.core.registry import Stage, register


def trapezoid(age, duration: float, ramp: float, amp: float):
    """M20 — haze profile: linear ramp up over `ramp`, plateau for `duration`, ramp down; 0 outside."""
    age = np.asarray(age, dtype=float)
    total = duration + 2.0 * ramp
    shape = np.clip(np.minimum(age / ramp, (total - age) / ramp), 0.0, 1.0)
    return np.where((age >= 0) & (age < total), amp * shape, 0.0)


@register("haze", kind="real")
class HazeReal(Stage):
    equation = "M20 (haze)"
    tag = "ASM"
    description = "Regional haze episodes (1 per 10 days × season multiplier), node gains g_i"

    def reset(self, ctx) -> None:
        p, n = self.params, ctx.n_nodes
        self.gain = np.clip(self.rng.normal(1.0, p["gain_sd"], n), p["gain_clip"][0], p["gain_clip"][1])
        self._rate = p["base_rate_per_10d"] * p["crop_burning_multiplier"] / (10.0 * 1440.0)
        self.episodes = [(float(e["t_min"]), float(e["duration_min"]), float(e["amplitude"]))
                         for e in p["scripted"]]
        self.n_started = 0                       # random (non-scripted) episodes started so far

    def step(self, t, ctx) -> Additive:
        p, rng = self.params, self.rng
        if rng.random() < 1.0 - np.exp(-self._rate * ctx.tick_minutes):              # Poisson episode starts
            dur = rng.uniform(p["duration_range"][0], p["duration_range"][1])         # M20 — D ~ U(180, 720)
            amp = rng.uniform(p["amp_range"][0], p["amp_range"][1])                   # M20 — U(0.8, 2.5)
            self.episodes.append((float(t), float(dur), float(amp)))
            self.n_started += 1
        ramp = p["ramp_min"]
        self.episodes = [e for e in self.episodes if t - e[0] < e[1] + 2 * ramp]   # drop finished episodes
        level = sum(float(trapezoid(t - s, d, ramp, a)) for s, d, a in self.episodes)
        return Additive(v=self.gain * level, level=level)                              # M20 — g_i H(t)


@register("haze", kind="stub")
class HazeStub(Stage):
    equation = "—"
    description = "No haze"

    def step(self, t, ctx) -> Additive:
        return Additive(v=np.zeros(ctx.n_nodes))


@register("haze", kind="off")
class HazeOff(HazeStub):
    pass
