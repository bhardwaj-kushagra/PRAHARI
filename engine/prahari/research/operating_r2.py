"""Protocol R2 per-seed operating surfaces (docs/research/protocol-r2.md §3–§6): every common-mode method over its
knob grid (one or two knobs) from one quiet and one fire pass.

Node layers: `main` (the readings), `med` (R3) and `factor` (R9). For each node layer and target r, h is replay-tuned
as in R1 and the edge stages run once (`edge2.py`); the SCMR threshold ρ and the evidence gate θ (R10) are applied to
the recorded clusters afterwards. Mei's procedure (R11) reads the node p-values directly. Each cell keeps the false
incidents, their first-alarm minutes and every fire's latency (M46).
"""
from __future__ import annotations

import numpy as np

from prahari.core.rng import make_rngs
from prahari.research.edge2 import alarms_at, edge_records
from prahari.research.gate import evidence_share, gated
from prahari.research.hazesplit import episodes, fire_overlaps, incident_list
from prahari.research.mei import mei_alarms
from prahari.research.baselines import ar_innovation, capped_z, confirm
from prahari.research.operating import SeedEval, _cands, _hits

NODE_LAYERS = ("main", "med", "factor")
# Node layers each method needs (R3 evaluates a subset; protocol R3). "main" is always recorded (the factor reference
# and every main-layer method read it).
METHOD_LAYERS = {"P2": "main", "P2-med": "med", "P2-medSCMR": "med", "P2-factor": "factor", "P2-gate": "main",
                 "Mei": "main", "Mei-med": "med", "AR": None}
ALL_METHODS = tuple(METHOD_LAYERS)


def score_r2(se: SeedEval, quiet, burn) -> tuple:
    """The registered M46 scoring (`SeedEval.score`) plus two descriptive fields for the validity rule (DECISIONS
    R2-D1): the longest false incident (minutes, first to last alarm) and the number of quiet-pass alarms in the test
    period."""
    k, lat, starts = se.score(quiet, burn)
    ev = se.ev
    inc = incident_list(quiet, se.dist, se.R, se.test0, se.T, ev["merge_min"], ev["merge_radius_factor"])
    longest = max((m[1] - m[0] for m in inc), default=0)
    n_alarms = sum(1 for a in quiet if se.test0 <= a[0] < se.T)
    return k, lat, starts, int(longest), int(n_alarms)


def _cells(knob: str, grid: list, scored: list, h=None, cap=None) -> dict:
    row = {"knob": knob, "grid": grid, "false_incidents": [int(s[0]) for s in scored],
           "latencies": [s[1] for s in scored], "fi_starts": [s[2] for s in scored],
           "fi_longest_min": [s[3] for s in scored], "n_alarms_quiet": [s[4] for s in scored]}
    if h is not None:
        row["h_by_target"] = [round(float(v), 6) for v in h]
        row["at_cap_by_target"] = [bool(c) for c in cap]
    return row


def eval_ar_r2(se: SeedEval, targets, cap) -> dict:
    """R1's AR(1) residual chart (`operating.eval_v1_tuned` with ar=True), unchanged except that it is scored with
    `score_r2`, so it carries the validity-rule fields too."""
    p = se.cfg["params"]["baseline_p1t"]
    k, ref, w, qn = float(p["k"]), int(p["refractory_min"]), int(p["window_min"]), int(p["quorum"])
    zs, fr = [], []
    for r in (se.q, se.f):
        z = capped_z(r.x, p)
        fr.append((z >= float(p["cm_z"])).mean(axis=1))                  # M28 — elevated share of this z
        zs.append(ar_innovation(z, int(p["init_min"]), se.ev["calibration_days"] * 1440)[0])
    hq, hf, cap_hit = se.tuned_both(zs[0], fr[0], zs[1], fr[1], targets, k, p, cap)
    cq, cf = _hits(zs[0], se.test0, k, hq, ref), _hits(zs[1], se.test0, k, hf, ref)
    scored = [score_r2(se, confirm(a, se.nbr, w, qn), confirm(b, se.nbr, w, qn)) for a, b in zip(cq, cf)]
    row = _cells("target", [float(g) for g in targets], scored)
    row["h"] = [round(float(v), 6) for v in hq]
    row["at_cap"] = [bool(c) for c in cap_hit]
    return row


def _records(se: SeedEval, v: str, targets, cap) -> tuple:
    """Per target: the edge records of the quiet and the fire pass for node layer v, and the tuned h."""
    tq, tf = se.q.nodes[v], se.f.nodes[v]
    p = tq.params
    hq, hf, cap_hit = se.tuned_both(tq.s, tq.frac, tf.s, tf.frac, targets, tq.k, p, cap)
    ref = int(p["refractory_min"])
    cq, cf = _hits(tq.s, se.test0, tq.k, hq, ref), _hits(tf.s, se.test0, tq.k, hf, ref)
    recs = []
    for a, b in zip(cq, cf):
        recs.append(tuple(edge_records(_cands(h, r.nodes[v].p), se.cfg, se.sim.ctx, make_rngs(se.seed)["srp"])
                          for h, r in ((a, se.q), (b, se.f))))
    return recs, hq, cap_hit


def evaluate_seed_r2(base_cfg: dict, seed: int, grids: dict, cap, methods=None) -> dict:
    """Protocol R2 for one seed: every method's operating surface, the haze episodes and the fires' haze overlap.
    `methods` (protocol R3) restricts the evaluation to a subset and records only the node layers it needs; the
    default (None) is the registered R2 evaluation."""
    methods = tuple(methods) if methods else ALL_METHODS
    layers = tuple(v for v in NODE_LAYERS if v == "main" or any(METHOD_LAYERS[m] == v for m in methods))
    se = SeedEval(base_cfg, seed, layers)
    targets, rhos = grids["node"], grids["rho"]
    thetas = grids["theta"]
    h_mei = grids.get("h_mei", [])
    k_mei, ref_mei = float(grids.get("mei_k", 1.5)), int(grids.get("mei_refractory_min", 30))
    rec = {v: _records(se, v, targets, cap) for v in layers}

    def surface(v, rho_grid):
        recs, h, c = rec[v]
        grid, scored = [], []
        for r, (rq, rf) in zip(targets, recs):
            for rho in rho_grid:
                grid.append([float(r), float(rho)])
                scored.append(score_r2(se, alarms_at(rq, rho), alarms_at(rf, rho)))
        return _cells("target×rho" if len(rho_grid) > 1 else "target", grid if len(rho_grid) > 1 else
                      [g[0] for g in grid], scored, h, c)

    def gate():
        e = {name: evidence_share(r.nodes["main"].p, float(grids["gate_p"]), int(grids["gate_window_min"]))
             for name, r in (("q", se.q), ("f", se.f))}
        recs, h, c = rec["main"]
        g_grid, g_scored = [], []
        for r, (rq, rf) in zip(targets, recs):
            aq, af = alarms_at(rq, 0.0), alarms_at(rf, 0.0)
            for th in thetas:
                g_grid.append([float(r), th])
                g_scored.append(score_r2(se, gated(aq, e["q"], th), gated(af, e["f"], th)))
        return _cells("target×theta", g_grid, g_scored, h, c)

    def mei(v):
        aq = mei_alarms(se.q.nodes[v].p[se.test0:], h_mei, k_mei, ref_mei, se.test0)
        af = mei_alarms(se.f.nodes[v].p[se.test0:], h_mei, k_mei, ref_mei, se.test0)
        return _cells("h_M", [float(x) for x in h_mei], [score_r2(se, a, b) for a, b in zip(aq, af)])

    build = {"P2": lambda: surface("main", rhos), "P2-med": lambda: surface("med", [0.0]),
             "P2-medSCMR": lambda: surface("med", rhos), "P2-factor": lambda: surface("factor", [0.0]),
             "P2-gate": gate, "Mei": lambda: mei("main"), "Mei-med": lambda: mei("med"),
             "AR": lambda: eval_ar_r2(se, grids["v1t"], cap)}
    fe = episodes(se.f.haze)
    return {"seed": seed, "test_days": se.ev["test_days"], "n_fires": len(se.fires),
            "degraded": sorted(n for n, slot in se.sim.slots.items() if slot.health.state == "degraded"),
            "fires_dry": [bool(se.dry[t0 // 1440]) for t0, _ in se.fires],
            "haze_episodes": episodes(se.q.haze), "haze_notes": se.q.haze_notes,
            "haze_passes_equal": bool(np.array_equal(se.q.haze, se.f.haze)),
            "fires_haze_overlap": fire_overlaps(fe, se.fires, se.T, se.ev["detect_window_min"]),
            "factor_gain": None if se.q.factor_gain is None else [round(float(g), 4) for g in se.q.factor_gain],
            "pipelines": {m: build[m]() for m in ALL_METHODS if m in methods}}
