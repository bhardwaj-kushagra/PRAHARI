"""Regional haze (SPEC §5.6, M20). Real: Poisson trapezoid episodes with node gains. Stub and off: none.

`params.haze.form` selects the real model: `m20` (default, release 1.0, unchanged) or `m20b` (protocol R2 §2), where
each node sees an episode through a correlated gain field, a per-episode unevenness, a swath coverage and an arrival
delay (a moving front plus per-node jitter), and episode starts are weighted towards the night. M20b draws from the
same `haze` stream (no other module reads it); the `m20` form draws exactly as before.
"""
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
        if p.get("form", "m20") == "m20b":
            self._b = M20b(p, self.rng, np.asarray(ctx.xy, dtype=float))
            return
        self._b = None
        self.gain = np.clip(self.rng.normal(1.0, p["gain_sd"], n), p["gain_clip"][0], p["gain_clip"][1])
        self._rate = p["base_rate_per_10d"] * p["crop_burning_multiplier"] / (10.0 * 1440.0)
        self.episodes = [(float(e["t_min"]), float(e["duration_min"]), float(e["amplitude"]))
                         for e in p["scripted"]]
        self.n_started = 0                       # random (non-scripted) episodes started so far

    def step(self, t, ctx) -> Additive:
        if self._b is not None:
            return self._b.step(t, ctx.tick_minutes)
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


    def snapshot(self) -> dict:
        b = getattr(self, "_b", None)
        return {"form": "m20b", "episodes": b.meta} if b is not None else {}


def gain_field(xy, sd: float, corr_len: float, rho: float, clip, rng) -> np.ndarray:
    """R2 M20b — g_i = clip(1 + σ_g (ρ_s Z_i + √(1−ρ_s²) ε_i)): Z a unit Gaussian field over the nodes with
    correlation exp(−d/L), ε independent N(0, 1)."""
    n = xy.shape[0]
    d = np.hypot(xy[:, None, 0] - xy[None, :, 0], xy[:, None, 1] - xy[None, :, 1])
    L = np.linalg.cholesky(np.exp(-d / corr_len) + 1e-9 * np.eye(n))
    z = L @ rng.standard_normal(n)
    e = rng.standard_normal(n)
    return np.clip(1.0 + sd * (rho * z + np.sqrt(1.0 - rho * rho) * e), clip[0], clip[1])


def swath_coverage(xy, frac: float, angle: float, centre: float, width_m: float, edge_m: float,
                   floor: float) -> np.ndarray:
    """R2 M20b — c_i: 1 inside a swath of width f·W across the network (axis at `angle`, centre offset `centre` along
    its normal), `floor` outside, linear soft edges of `edge_m`; f = 1 covers every node."""
    if frac >= 1.0:
        return np.ones(xy.shape[0])
    u = xy @ np.array([-np.sin(angle), np.cos(angle)])                     # position along the swath's normal
    inside = np.clip((0.5 * frac * width_m - np.abs(u - centre)) / edge_m + 0.5, 0.0, 1.0)
    return floor + (1.0 - floor) * inside


def front_delays(xy, direction: float, speed_ms: float) -> np.ndarray:
    """R2 M20b — δ_i (min): position along the front's direction over its speed, the first node at 0; ∞ speed → 0."""
    if not np.isfinite(speed_ms):
        return np.zeros(xy.shape[0])
    s = xy @ np.array([np.cos(direction), np.sin(direction)])
    return (s - s.min()) / speed_ms / 60.0


def night_factor(t: float, share: float, night) -> float:
    """R2 M20b — rate multiplier by time of day: share/½ in the 12-hour night window, (1 − share)/½ outside, so the
    mean rate is unchanged and a start falls at night with probability `share`."""
    m, (a, b) = t % 1440, night
    at_night = (m >= a or m < b) if a > b else (a <= m < b)
    return (share if at_night else 1.0 - share) / 0.5


class M20b:
    """R2 M20b — h_i(t) = Σ_e g_i · u_i,e · c_i,e · A_e · trapezoid(t − t_e − δ_i,e)."""

    def __init__(self, p: dict, rng, xy):
        if abs(((p["night_window"][0] - p["night_window"][1]) % 1440) - 720) > 1e-9:
            raise ValueError("night_window must span 12 hours (the rate factor assumes it)")
        self.p, self.rng, self.xy = p, rng, xy
        self.gain = gain_field(xy, float(p["gain_sd"]), float(p["gain_corr_len_m"]), float(p["gain_corr_rho"]),
                               p["gain_clip"], rng)
        self._rate = p["base_rate_per_10d"] * p["crop_burning_multiplier"] / (10.0 * 1440.0)
        span = xy.max(axis=0) - xy.min(axis=0)
        self.width = float(p.get("network_width_m") or span.max())
        self.episodes: list = []                  # (t_e, D, A, weights (N,), delays (N,))
        self.meta: list = []
        for e in p["scripted"]:
            self._add(float(e["t_min"]), float(e["duration_min"]), float(e["amplitude"]))

    def _draw_geometry(self):
        p, rng, n = self.p, self.rng, self.xy.shape[0]
        s = rng.uniform(*p["uneven_s_range"])
        u = np.exp(s * rng.standard_normal(n) - 0.5 * s * s)                      # u_i,e, mean 1
        f = 1.0 if rng.random() < p["coverage_full_prob"] else rng.uniform(*p["coverage_partial_range"])
        ang = rng.uniform(0.0, np.pi)
        proj = self.xy @ np.array([-np.sin(ang), np.cos(ang)])
        centre = rng.uniform(proj.min(), proj.max())
        c = swath_coverage(self.xy, f, ang, centre, self.width, float(p["swath_edge_m"]), float(p["outside_floor"]))
        direction = rng.uniform(0.0, 2.0 * np.pi)
        v = rng.uniform(*p["front_speed_ms"]) if p["front_speed_ms"] else np.inf
        J = rng.uniform(*p["jitter_max_range_min"])
        delay = front_delays(self.xy, direction, v) + rng.uniform(0.0, J, n)
        return u, c, delay, {"s": s, "coverage": f, "swath_angle": ang, "direction": direction,
                             "speed_ms": None if not np.isfinite(v) else v, "jitter_max_min": J}

    def _add(self, t0: float, dur: float, amp: float) -> None:
        u, c, delay, m = self._draw_geometry()
        self.episodes.append((t0, dur, amp, self.gain * u * c, delay))
        self.meta.append({"t_min": t0, "duration_min": round(dur, 3), "amplitude": round(amp, 4),
                          **{k: (None if v is None else round(float(v), 4)) for k, v in m.items()},
                          "delay_max_min": round(float(delay.max()), 3)})

    def step(self, t, tick_minutes) -> Additive:
        p, rng = self.p, self.rng
        rate = self._rate * night_factor(t, float(p["night_share"]), p["night_window"])
        if rng.random() < 1.0 - np.exp(-rate * tick_minutes):                  # Poisson starts, night-weighted
            dur = rng.uniform(p["duration_range"][0], p["duration_range"][1])    # M20 — D ~ U(180, 720)
            amp = rng.uniform(p["amp_range"][0], p["amp_range"][1])              # M20 — U(0.8, 2.5)
            self._add(float(t), float(dur), float(amp))
        ramp = p["ramp_min"]
        self.episodes = [e for e in self.episodes if t - e[0] < e[1] + 2 * ramp + e[4].max()]
        v = np.zeros(self.xy.shape[0])
        level = 0.0
        for t0, dur, amp, w, delay in self.episodes:
            shape = trapezoid(t - t0 - delay, dur, ramp, 1.0)
            v += w * amp * shape
            level += amp * float(shape.max())                                  # positive while any node sees it
        return Additive(v=v, level=level)


@register("haze", kind="stub")
class HazeStub(Stage):
    equation = "—"
    description = "No haze"

    def step(self, t, ctx) -> Additive:
        return Additive(v=np.zeros(ctx.n_nodes))


@register("haze", kind="off")
class HazeOff(HazeStub):
    pass
