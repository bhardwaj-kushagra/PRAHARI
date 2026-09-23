"""Ignition stage (SPEC §5.3). Real: scripted fires plus M3/M8 Poisson ignitions. Stub: scripted only. Off: no fires."""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import Fire, Fires
from prahari.core.registry import Stage, register


@register("ignition", kind="stub")
class IgnitionStub(Stage):
    equation = "—"
    tag = "ASM"
    description = "Fires at scripted times and places from the scenario file"

    def reset(self, ctx) -> None:
        script = sorted(self.params.get("scripted", []), key=lambda s: (s["t_min"], s["x"], s["y"]))
        self._pending = [Fire(id=k, x=float(s["x"]), y=float(s["y"]), t0=int(s["t_min"])) for k, s in enumerate(script)]
        self._active: list[Fire] = []

    def step(self, inputs, ctx) -> Fires:
        t = inputs[0]
        new = [f for f in self._pending if f.t0 <= t]
        self._pending = [f for f in self._pending if f.t0 > t]
        self._active += new
        life = float(self.params["fire_lifetime_min"])
        self._active = [f for f in self._active if t - f.t0 < life]
        return Fires(active=tuple(self._active), new=tuple(f.id for f in new))

    def snapshot(self) -> dict:
        return {"pending": len(self._pending), "active": len(self._active)}


@register("ignition", kind="off")
class IgnitionOff(Stage):
    description = "No fires"

    def step(self, inputs, ctx) -> Fires:
        return Fires()


def sustained_probability(ffmc, a: float, b: float):
    """M8 — p_s(M) = 1 / (1 + exp(−(a + b M))), M = FFMC."""
    return 1.0 / (1.0 + np.exp(-(a + b * np.asarray(ffmc, dtype=float))))


def activity(tod_hours, night: float, day: float, ramp_up: tuple, ramp_down: tuple):
    """M3 — human activity a(t): `night` outside, `day` between the ramps, smooth (smoothstep) ramps between."""
    h = np.asarray(tod_hours, dtype=float)

    def smooth(x):
        x = np.clip(x, 0.0, 1.0)
        return x * x * (3.0 - 2.0 * x)

    up = smooth((h - ramp_up[0]) / (ramp_up[1] - ramp_up[0]))
    down = 1.0 - smooth((h - ramp_down[0]) / (ramp_down[1] - ramp_down[0]))
    return night + (day - night) * np.minimum(up, down)


@register("ignition", kind="real")
class IgnitionReal(IgnitionStub):
    equation = "M3, M8"
    tag = "ASM"
    description = "Scripted fires plus Poisson attempts from the M3 map (thinning), sustained with p_s(FFMC)"

    def _a(self, t: int, ctx) -> float:
        p = self.params
        w = ctx.clock.wall(t)
        a = float(activity(w.hour + w.minute / 60.0, p["activity_night"], p["activity_day"],
                           p["activity_ramp_up_h"], p["activity_ramp_down_h"]))
        day = (w.date() - ctx.clock.start.date()).days
        return a * (p["market_multiplier"] if day in p["market_days"] else 1.0)

    def reset(self, ctx) -> None:
        super().reset(ctx)
        p = self.params
        self._next_id = len(self._pending)
        self.attempts = 0
        self._lam0 = 0.0
        if p["expected_fires"] <= 0:
            return
        land = ctx.landscape
        if land is None:
            raise RuntimeError("ignition: no landscape in the run context")
        shape = land.lam * land.forest
        self._S = shape / shape.max()                                          # S(x) = Σ_k w_k e^{−D_k/L_k}, scaled to max 1
        self._land = land
        a_sum = sum(self._a(t, ctx) for t in ctx.clock.minutes()) * ctx.tick_minutes
        ps_ref = float(sustained_probability(p["ps_reference_ffmc"], p["ps_a"], p["ps_b"]))
        # DER — λ₀ so that E[sustained fires] = expected_fires at the reference FFMC
        self._lam0 = p["expected_fires"] / (a_sum * self._S.sum() * land.cell_m ** 2 * ps_ref)
        self._a_max = max(p["activity_day"], p["activity_night"]) * (p["market_multiplier"] if p["market_days"] else 1.0)

    def step(self, inputs, ctx) -> Fires:
        t, env, fuel = inputs
        base = super().step(inputs, ctx)
        if self._lam0 <= 0:
            return Fires(active=base.active, new=base.new, new_causes=("scripted",) * len(base.new),
                         attempts=self.attempts)
        p, rng, land = self.params, self.rng, self._land
        area = land.width_m * land.height_m
        lam_max = self._lam0 * self._a_max                                     # thinning envelope (S_max = 1)
        n = int(rng.poisson(lam_max * area * ctx.tick_minutes))
        new, causes = list(base.new), ["scripted"] * len(base.new)
        if n:
            xy = rng.uniform((0.0, 0.0), (land.width_m, land.height_m), (n, 2))
            col = np.clip((xy[:, 0] // land.cell_m).astype(int), 0, self._S.shape[1] - 1)
            row = np.clip((xy[:, 1] // land.cell_m).astype(int), 0, self._S.shape[0] - 1)
            accept = rng.random(n) < (self._a(t, ctx) / self._a_max) * self._S[row, col]   # M3 — λ(x,t)/λ_max
            self.attempts += int(accept.sum())
            ps = float(sustained_probability(fuel.ffmc, p["ps_a"], p["ps_b"]))              # M8
            keep = accept & (rng.random(n) < ps)
            for x, y in xy[keep]:
                f = Fire(id=self._next_id, x=float(x), y=float(y), t0=int(t))
                self._next_id += 1
                self._active.append(f)
                new.append(f.id)
                causes.append("poisson")
        return Fires(active=tuple(self._active), new=tuple(new), new_causes=tuple(causes), attempts=self.attempts)

    def snapshot(self) -> dict:
        return {**super().snapshot(), "attempts": self.attempts, "lambda0": self._lam0}
