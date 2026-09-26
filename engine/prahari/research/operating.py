"""Per-seed operating curves (protocol R1 §3): every pipeline over its knob grid from one quiet and one fire pass.

Knobs: P0 k (μ + kσ), P1 h, and the replay-tuning target r for P1t, AR and every PRAHARI variant. For each knob value
the seed's row keeps the false incidents (M46, quiet pass) and every fire's latency (M46, fire pass; None = missed).
With `default=True` each pipeline is evaluated only at its configured knob and search cap: the fidelity setting that
must reproduce the online harness exactly.
"""
from __future__ import annotations

import copy

import numpy as np

from prahari.core.rng import make_rngs
from prahari.eval.experiments import protocol_config, protocol_fires
from prahari.eval.offline import edge_alarms, edge_stages, tuning_mask
from prahari.eval.stats import detect, incidents
from prahari.research.baselines import ar_innovation, capped_z, confirm, p0_alarms, v1_z
from prahari.research.cusum import by_tick, cusum_multi, tune_multi
from prahari.research.record import record_pass

# PRAHARI variants: (node-layer variant, edge module overrides, extra parameter overrides).
EDGE_VARIANTS = {"P2": ("main", {}, {}), "P2-SCMR": ("main", {"scmr": "stub"}, {}),
                 "P2-Q2": ("main", {"raq": "stub"}, {"raq.fixed_quorum": 2}),
                 "P2-Q3": ("main", {"raq": "stub"}, {"raq.fixed_quorum": 3}),
                 "P2-med": ("med", {"scmr": "stub"}, {}), "P2-QCC": ("qcc", {}, {}), "P2-TTC": ("ttc", {}, {})}


def flipped_day_types(cfg: dict, seed: int, q: float) -> dict:
    """Wrong-prior sweep (protocol R1 §5): each day's srp type flipped with probability q (stream `research`;
    the same draws for every q, so the flips are nested)."""
    c = copy.deepcopy(cfg)
    days = c["params"]["srp"]["day_type_overrides"]
    u = make_rngs(seed)["research"].random(len(days))
    for d, flip in zip(days, u < q):
        if flip:
            d["type"] = "wet_quiet" if d["type"] == "dry_busy" else "dry_busy"
    return c


def _tuned(S, frac, targets, k: float, p: dict, n: int, cap: tuple | None):
    """M28 — replay-tuned h per target on the tuning window (batched `tune_h`); cap = (h_hi, iters) or configured."""
    t0, t1 = int(p["tune_start_min"]), int(p["tune_end_min"])
    tg = np.asarray(targets, dtype=float) / 30.0 * n * (t1 - t0) / 1440.0      # M28 — r · N · D_tune
    hi, iters = cap if cap else (float(p["h_hi"]), int(p["bisect_iters"]))
    return tune_multi(S[t0:t1], k, tuning_mask(frac, t0, t1, p), tg, float(p["h_lo"]), hi, iters,
                      int(p["refractory_min"]))


def _hits(S, test0: int, k: float, hs, ref: int) -> list:
    """Candidates {t: [nodes]} from `test0` on for each threshold (CUSUM restarted at the test period)."""
    hits, _ = cusum_multi(S[test0:], k, hs, ref)
    return [by_tick(t, i, test0) for t, i in hits]


class SeedEval:
    """The recorded passes of one seed and the M46 scoring shared by every pipeline."""

    def __init__(self, base_cfg: dict, seed: int, variants, fires=None):
        self.cfg, self.ev, self.test0, self.T = protocol_config(base_cfg, seed)
        self.seed = seed
        self.sim, self.q = record_pass(self.cfg, (), variants)
        ctx = self.sim.ctx
        self.xy, self.dist, self.R, self.nbr, self.n = ctx.xy, ctx.dist, ctx.radius_m, ctx.neighbours, ctx.n_nodes
        self.fires, self.dry = fires or protocol_fires(seed, self.ev, self.xy, self.T)
        _, self.f = record_pass(self.cfg, self.fires, variants)

    def score(self, quiet, burn) -> tuple[int, list]:
        """M46 — false incidents of the quiet-pass alarms and fire latencies of the fire-pass alarms."""
        ev = self.ev
        k = incidents(quiet, self.dist, self.R, self.test0, self.T, ev["merge_min"], ev["merge_radius_factor"])
        return k, detect(burn, self.fires, self.xy, ev["detect_radius_m"], ev["detect_window_min"])

    def tuned_both(self, Sq, fq, Sf, ff, targets, k, p, cap):
        """Tuned h for each pass. The passes share their tuning window exactly (fires start in the test period), so the
        quiet pass's h is reused when the inputs are identical, as the online harness would tune them."""
        hq, cq = _tuned(Sq, fq, targets, k, p, self.n, cap)
        t0, t1, pad = int(p["tune_start_min"]), int(p["tune_end_min"]), int(p["cm_pad_min"])
        same = np.array_equal(Sq[t0:t1], Sf[t0:t1]) and np.array_equal(fq[t0 - pad:t1], ff[t0 - pad:t1])
        hf = hq if same else _tuned(Sf, ff, targets, k, p, self.n, cap)[0]
        return hq, hf, cq


def _row(knob: str, grid, scored, h=None, cap=None) -> dict:
    row = {"knob": knob, "grid": [float(g) for g in grid], "false_incidents": [int(s[0]) for s in scored],
           "latencies": [s[1] for s in scored]}
    if h is not None:
        row["h"] = [round(float(v), 6) for v in h]
        row["at_cap"] = [bool(c) for c in cap]
    return row


def eval_p0(se: SeedEval, grid) -> dict:
    """P0 over its k grid (M22)."""
    p = se.cfg["params"]["baseline_p0"]
    return _row("k", grid, [se.score(p0_alarms(se.q.x_raw, k, p), p0_alarms(se.f.x_raw, k, p)) for k in grid])


def eval_p1(se: SeedEval, grid) -> dict:
    """P1 over its h grid (M23, uncapped EWMA z, quorum confirmation)."""
    p = se.cfg["params"]["baseline_p1"]
    w, qn, ref = int(p["window_min"]), int(p["quorum"]), int(p["refractory_min"])
    cq, cf = (_hits(v1_z(r.x, p), se.test0, float(p["k"]), grid, ref) for r in (se.q, se.f))
    return _row("h", grid, [se.score(confirm(a, se.nbr, w, qn), confirm(b, se.nbr, w, qn)) for a, b in zip(cq, cf)])


def eval_v1_tuned(se: SeedEval, targets, cap, ar: bool = False) -> dict:
    """P1t (M23 on the capped z, M28 tuning) or, with `ar`, the AR(1) residual chart (R1, R2) with the same tuning,
    common-mode mask and confirmation."""
    p = se.cfg["params"]["baseline_p1t"]
    k, ref, w, qn = float(p["k"]), int(p["refractory_min"]), int(p["window_min"]), int(p["quorum"])
    zs, fr = [], []
    for r in (se.q, se.f):
        z = capped_z(r.x, p)
        fr.append((z >= float(p["cm_z"])).mean(axis=1))                  # M28 — elevated share of this z
        zs.append(ar_innovation(z, int(p["init_min"]), se.ev["calibration_days"] * 1440)[0] if ar else z)
    hq, hf, cap_hit = se.tuned_both(zs[0], fr[0], zs[1], fr[1], targets, k, p, cap)
    cq, cf = _hits(zs[0], se.test0, k, hq, ref), _hits(zs[1], se.test0, k, hf, ref)
    scored = [se.score(confirm(a, se.nbr, w, qn), confirm(b, se.nbr, w, qn)) for a, b in zip(cq, cf)]
    return _row("target", targets, scored, hq, cap_hit)


def _cands(hits: dict, P) -> dict:
    return {t: (tuple(ns), tuple(float(P[t, i]) for i in ns)) for t, ns in hits.items()}


def eval_edge(se: SeedEval, names, targets, cap, priors=()) -> dict:
    """PRAHARI variants (`EDGE_VARIANTS`, plus P2 under wrong priors q) over the target grid: node CUSUM replay,
    then the registered edge stages (M30–M34) exactly as the online harness replays them."""
    out, cache = {}, {}
    jobs = [(nm, *EDGE_VARIANTS[nm], se.cfg) for nm in names]
    jobs += [(f"P2-prior{q:g}", "main", {}, {}, flipped_day_types(se.cfg, se.seed, q)) for q in priors]
    for name, v, mods, params, cfg in jobs:
        if v not in cache:
            tq, tf = se.q.nodes[v], se.f.nodes[v]
            p = tq.params
            hq, hf, cap_hit = se.tuned_both(tq.s, tq.frac, tf.s, tf.frac, targets, tq.k, p, cap)
            ref = int(p["refractory_min"])
            cache[v] = (hq, cap_hit, _hits(tq.s, se.test0, tq.k, hq, ref), _hits(tf.s, se.test0, tq.k, hf, ref))
        hq, cap_hit, cq, cf = cache[v]
        c = copy.deepcopy(cfg)
        for key, val in params.items():
            m, param = key.split(".", 1)
            c["params"][m][param] = val
        scored = []
        for a, b in zip(cq, cf):
            al = [edge_alarms(_cands(h, r.nodes[v].p), edge_stages(c, se.sim.ctx, make_rngs(se.seed)["srp"], mods),
                              se.sim.ctx) for h, r in ((a, se.q), (b, se.f))]
            scored.append(se.score(*al))
        out[name] = _row("target", targets, scored, hq, cap_hit)
    return out


def evaluate_seed(base_cfg: dict, seed: int, grids: dict, cap=None, edge_names=tuple(EDGE_VARIANTS), priors=(),
                  default: bool = False) -> dict:
    """Protocol R1 for one seed: every pipeline's operating curve (or, with `default`, its configured point)."""
    variants = sorted({EDGE_VARIANTS[n][0] for n in edge_names} | ({"main"} if priors else set()))
    se = SeedEval(base_cfg, seed, variants)
    prm = se.cfg["params"]
    g = {"P0": [prm["baseline_p0"]["n_sigma"]], "P1": [prm["baseline_p1"]["h"]],
         "v1t": [prm["baseline_p1t"]["target_per_node_30d"]], "node": [prm["cusum"]["target_per_node_30d"]]} \
        if default else grids
    cap = None if default else cap
    out = {"seed": seed, "test_days": se.ev["test_days"], "n_fires": len(se.fires),
           "degraded": sorted(n for n, slot in se.sim.slots.items() if slot.health.state == "degraded"),
           "fires_dry": [bool(se.dry[t0 // 1440]) for t0, _ in se.fires],
           "pipelines": {"P0": eval_p0(se, g["P0"]), "P1": eval_p1(se, g["P1"]),
                         "P1t": eval_v1_tuned(se, g["v1t"], cap), "AR": eval_v1_tuned(se, g["v1t"], cap, ar=True),
                         **eval_edge(se, edge_names, g["node"], cap, priors)}}
    return out
