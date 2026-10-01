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
from prahari.research.hazesplit import episodes, fire_overlaps
from prahari.research.mei import mei_alarms
from prahari.research.operating import SeedEval, _cands, _hits, eval_v1_tuned

NODE_LAYERS = ("main", "med", "factor")


def _cells(knob: str, grid: list, scored: list, h=None, cap=None) -> dict:
    row = {"knob": knob, "grid": grid, "false_incidents": [int(s[0]) for s in scored],
           "latencies": [s[1] for s in scored], "fi_starts": [s[2] for s in scored]}
    if h is not None:
        row["h_by_target"] = [round(float(v), 6) for v in h]
        row["at_cap_by_target"] = [bool(c) for c in cap]
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


def evaluate_seed_r2(base_cfg: dict, seed: int, grids: dict, cap) -> dict:
    """Protocol R2 for one seed: every method's operating surface, the haze episodes and the fires' haze overlap."""
    se = SeedEval(base_cfg, seed, NODE_LAYERS)
    targets, rhos = grids["node"], grids["rho"]
    thetas, h_mei = grids["theta"], grids["h_mei"]
    k_mei, ref_mei = float(grids["mei_k"]), int(grids["mei_refractory_min"])
    rec = {v: _records(se, v, targets, cap) for v in NODE_LAYERS}

    def surface(v, rho_grid):
        recs, h, c = rec[v]
        grid, scored = [], []
        for r, (rq, rf) in zip(targets, recs):
            for rho in rho_grid:
                grid.append([float(r), float(rho)])
                scored.append(se.score(alarms_at(rq, rho), alarms_at(rf, rho)))
        return _cells("target×rho" if len(rho_grid) > 1 else "target", grid if len(rho_grid) > 1 else
                      [g[0] for g in grid], scored, h, c)

    e = {name: evidence_share(r.nodes["main"].p, float(grids["gate_p"]), int(grids["gate_window_min"]))
         for name, r in (("q", se.q), ("f", se.f))}
    recs, h, c = rec["main"]
    g_grid, g_scored = [], []
    for r, (rq, rf) in zip(targets, recs):
        aq, af = alarms_at(rq, 0.0), alarms_at(rf, 0.0)
        for th in thetas:
            g_grid.append([float(r), th])
            g_scored.append(se.score(gated(aq, e["q"], th), gated(af, e["f"], th)))

    def mei(v):
        aq = mei_alarms(se.q.nodes[v].p[se.test0:], h_mei, k_mei, ref_mei, se.test0)
        af = mei_alarms(se.f.nodes[v].p[se.test0:], h_mei, k_mei, ref_mei, se.test0)
        return _cells("h_M", [float(x) for x in h_mei], [se.score(a, b) for a, b in zip(aq, af)])

    fe = episodes(se.f.haze)
    return {"seed": seed, "test_days": se.ev["test_days"], "n_fires": len(se.fires),
            "degraded": sorted(n for n, slot in se.sim.slots.items() if slot.health.state == "degraded"),
            "fires_dry": [bool(se.dry[t0 // 1440]) for t0, _ in se.fires],
            "haze_episodes": episodes(se.q.haze), "haze_notes": se.q.haze_notes,
            "haze_passes_equal": bool(np.array_equal(se.q.haze, se.f.haze)),
            "fires_haze_overlap": fire_overlaps(fe, se.fires, se.T, se.ev["detect_window_min"]),
            "factor_gain": None if se.q.factor_gain is None else [round(float(g), 4) for g in se.q.factor_gain],
            "pipelines": {"P2": surface("main", rhos), "P2-med": surface("med", [0.0]),
                          "P2-medSCMR": surface("med", rhos), "P2-factor": surface("factor", [0.0]),
                          "P2-gate": _cells("target×theta", g_grid, g_scored, h, c),
                          "Mei": mei("main"), "Mei-med": mei("med"),
                          "AR": eval_v1_tuned(se, grids["v1t"], cap, ar=True)}}
