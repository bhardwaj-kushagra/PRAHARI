"""PRAHARI edge decision, real implementations — situational prior (M33, legacy day type) and the risk-adaptive
quorum (M34). SPEC §5.9. Stubs (constant prior, fixed quorum of 2) are in `srp.py` and `raq.py`.

- SRP legacy: each simulated day is dry/busy (prior odds 1e-4) or wet/quiet (1e-6). Day types are drawn from the
  `srp` stream with P(dry) = 0.5, as the report simulation does, and may be overridden per day by a scenario or by the
  experiment harness (which shares its protocol's day types). The full M33 integral (λ × p_s over the cluster's
  area) needs per-cluster priors and is left for the regime work (Phase 9).
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


@register("srp", kind="real")
class SrpReal(Stage):
    equation = "M33 (legacy day type)"
    tag = "TGT"
    description = "Prior odds 1e-4 on dry, busy days and 1e-6 on wet, quiet days"

    def reset(self, ctx) -> None:
        p = self.params
        n_days = int(np.ceil(ctx.clock.n_ticks * ctx.tick_minutes / 1440.0)) + 1
        self._types = day_types(self.rng, n_days, float(p["p_dry"]), p["day_type_overrides"])

    def step(self, inputs, ctx) -> Prior:
        dt = self._types[min(ctx.t // 1440, len(self._types) - 1)]
        odds = float(self.params["odds_dry"] if dt == DRY else self.params["odds_wet"])
        return Prior(odds=odds, day_type=dt)

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
        post = tuple(float(b * prior.odds) for b in bf.bf)                   # M34 — posterior odds
        if p["form"] == "bayes":
            decide = tuple(bool(po >= thr and ok) for po, ok in zip(post, scmr.passed))
            q, method = self._cache[prior.odds], "bayes"
        else:
            q = int(p["quorum_dry"] if prior.day_type == DRY else p["quorum_wet"])
            decide = tuple(bool(len(m) >= q and ok) for m, ok in zip(clusters.members, scmr.passed))
            method = "legacy quorum"
        return Raq(quorum=q, threshold=thr, posterior_odds=post, decide=decide, method=method)
