"""PRAHARI edge decision, real implementations — situational prior (M33, legacy day type) and the risk-adaptive
quorum (M34). SPEC §5.9. Stubs (constant prior, fixed quorum of 2) are in `srp.py` and `raq.py`.

- SRP legacy: each simulated day is dry/busy (prior odds 1e-4) or wet/quiet (1e-6). Day types are drawn from the
  `srp` stream with P(dry) = 0.5, as the report simulation does, and may be overridden per day by a scenario or by the
  experiment harness (which shares its protocol's day types).
- SRP `integral` (Phase 9, advanced): M33 as written — π_C = 1 − exp(−p_s(FFMC) Δt ∫_{A_C} λ(x, t) dx), with A_C the
  raster cells within R of any cluster member and λ(x, t) = a(t) × the landscape's M3 shape, scaled so the map expects
  `fires_per_30d` sustained fires in 30 days at the reference FFMC (as the ignition model scales λ₀). RAQ uses each
  cluster's own prior; the day type still sets the displayed odds and the legacy quorum.
- RAQ `legacy` (default): the quorum is the rule's consequence — 2 agreeing nodes on dry/busy days, 3 on wet/quiet.
  RAQ `bayes`: alarm when BF(p_C) · prior odds ≥ C_FA / C_miss with the Sellke–Bayarri–Berger bound. With the
  M32 candidate p-value the two agree (Phase 6 acceptance 2); the reported quorum is always the Bayes reverse view.
"""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import Prior, Raq
from prahari.core.registry import Stage, register
from prahari.detect.prahari.edge_real import fisher_combine
from prahari.detect.prahari.learn import sbb_bound
from prahari.fire.ignition import activity, sustained_probability

DRY, WET = "dry_busy", "wet_quiet"


def day_types(rng, n_days: int, p_dry: float, overrides=()) -> list[str]:
    """M33 legacy — one type per day (drawn first, so overrides never shift the random stream)."""
    dry = rng.random(n_days) < p_dry
    types = [DRY if d else WET for d in dry]
    for o in overrides:
        k = int(o["day"]) - 1
        if 0 <= k < n_days:
            types[k] = o["type"]
    return types


def bayes_quorum(odds: float, threshold: float, p_cand: float, k_max: int = 20) -> int:
    """M34 reverse view — the fewest agreeing candidates whose Fisher p_C clears the threshold on these prior odds."""
    for k in range(1, k_max + 1):
        _, _, pc = fisher_combine(np.full(k, p_cand))
        if float(sbb_bound(pc)) * odds >= threshold:
            return k
    return k_max


def integral_setup(ctx, p: dict):
    """M33 — per-cell sustained-fire rate per minute per unit activity, scaled so the whole map expects
    `fires_per_30d` sustained fires in 30 days at the reference FFMC; and the raster cells within R of each node."""
    land = ctx.landscape
    shape = (land.lam * land.forest).ravel()
    a_day = sum(float(activity(m / 60.0, p["activity_night"], p["activity_day"], p["activity_ramp_up_h"],
                               p["activity_ramp_down_h"])) for m in range(1440))
    ps_ref = float(sustained_probability(p["ps_reference_ffmc"], p["ps_a"], p["ps_b"]))
    rate = float(p["fires_per_30d"]) * shape / max(shape.sum(), 1e-300) / (30.0 * a_day * ps_ref)   # DER, as λ₀
    ny, nx = land.lam.shape
    gx, gy = np.meshgrid(land.x0 + land.cell_m * np.arange(nx), land.y0 + land.cell_m * np.arange(ny))
    cx, cy = gx.ravel(), gy.ravel()
    disk = tuple(np.flatnonzero(np.hypot(cx - x, cy - y) <= ctx.radius_m) for x, y in ctx.xy)
    return rate, disk


def cluster_prior(members, prior) -> tuple[float, float]:
    """M33 — (π_C/(1 − π_C), Λ_C Δt) for a cluster: π_C = 1 − exp(−p_s Δt a(t) Σ_{cells within R} rate)."""
    cells = np.unique(np.concatenate([prior.disk[i] for i in members]))
    lam_c = prior.lam * float(prior.lam_map[cells].sum())
    pi = -np.expm1(-prior.p_s * lam_c)
    return float(pi / max(1.0 - pi, 1e-300)), lam_c


@register("srp", kind="real")
class SrpReal(Stage):
    equation = "M33 (legacy day type)"
    tag = "TGT"
    description = "Prior odds 1e-4 on dry, busy days and 1e-6 on wet, quiet days"

    def reset(self, ctx) -> None:
        p = self.params
        n_days = int(np.ceil(ctx.clock.n_ticks * ctx.tick_minutes / 1440.0)) + 1
        self._types = day_types(self.rng, n_days, float(p["p_dry"]), p["day_type_overrides"])
        self._map = self._disk = None
        if p["form"] == "integral" and ctx.landscape is not None:
            self._map, self._disk = integral_setup(ctx, p)

    def _a(self, t: int, ctx) -> float:
        p, w = self.params, ctx.clock.wall(t)
        return float(activity(w.hour + w.minute / 60.0, p["activity_night"], p["activity_day"],
                              p["activity_ramp_up_h"], p["activity_ramp_down_h"]))

    def step(self, inputs, ctx) -> Prior:
        fuel = inputs[2] if isinstance(inputs, tuple) and len(inputs) > 2 else None   # (t, weather, fuel)
        p = self.params
        dt = self._types[min(ctx.t // 1440, len(self._types) - 1)]
        odds = float(p["odds_dry"] if dt == DRY else p["odds_wet"])
        storm = bool(getattr(ctx, "storm", False))
        if self._map is None or fuel is None:
            return Prior(odds=odds, day_type=dt, lightning=storm)
        ps = float(sustained_probability(fuel.ffmc, p["ps_a"], p["ps_b"]))                          # M8
        lam = self._a(ctx.t, ctx) * float(p["window_min"])                                           # a(t) Δt
        return Prior(odds=odds, day_type=dt, lam=lam, p_s=ps, lightning=storm, lam_map=self._map, disk=self._disk)

    def snapshot(self) -> dict:
        return {"day_types": "".join("D" if d == DRY else "W" for d in getattr(self, "_types", []))}


@register("raq", kind="real")
class RaqReal(Stage):
    equation = "M34"
    tag = "LIT"
    description = "Risk-adaptive quorum: legacy day-type quorum (2 dry, 3 wet) or the Bayes rule"

    def reset(self, ctx) -> None:
        p = self.params
        self._p_cand = float(p["rate_per_node_30d"]) / (30.0 * 1440.0) * float(p["window_min"])
        self._cache: dict[float, int] = {}

    def step(self, inputs, ctx) -> Raq:
        clusters, scmr, bf, prior = inputs
        p, thr = self.params, float(self.params["cost_ratio"])
        if prior.odds not in self._cache:
            self._cache[prior.odds] = bayes_quorum(prior.odds, thr, self._p_cand)
        odds_c, lam_c = (), ()
        if prior.lam_map is not None and prior.disk is not None:             # M33 integral: each cluster's prior
            pairs = [cluster_prior(m, prior) for m in clusters.members]
            odds_c, lam_c = tuple(o for o, _ in pairs), tuple(lc for _, lc in pairs)
        post = tuple(float(b * (odds_c[j] if odds_c else prior.odds)) for j, b in enumerate(bf.bf))   # M34
        if p["form"] == "bayes":
            decide = tuple(bool(po >= thr and ok) for po, ok in zip(post, scmr.passed))
            q, method = self._cache[prior.odds], "bayes"
        else:
            q = int(p["quorum_dry"] if prior.day_type == DRY else p["quorum_wet"])
            decide = tuple(bool(len(m) >= q and ok) for m, ok in zip(clusters.members, scmr.passed))
            method = "legacy quorum"
        return Raq(quorum=q, threshold=thr, posterior_odds=post, decide=decide, method=method, odds_c=odds_c, lam_c=lam_c)
