"""Offline evaluation of the PRAHARI edge layer and the operating dial (Phase 7).

A pass records every tick's node evidence S = −ln p^node, the share of nodes with slow z ≥ 3, and the candidates the
node CUSUM raised. From that record, edge variants (P2, P2 without SCMR, P2 without RAQ) are replayed through the
same registered stages the simulator runs, and the operating dial re-tunes the CUSUM threshold (M28) for other
false-candidate targets with the same functions (`tuning.py`). Only ablations that change the node layer need passes
of their own.
"""
from __future__ import annotations

import numpy as np

from prahari.core import registry
from prahari.core.contracts import Delivered
from prahari.detect.prahari.cusum_real import elevated_fraction
from prahari.detect.prahari.qcc import P_FLOOR
from prahari.detect.prahari.tuning import cm_mask, cusum_replay, tune_h

EDGE = ("cluster", "scmr", "fisher", "learn", "srp", "raq")


class ScoreRecorder:
    """Observer for `run_pass`: keeps S (T, N) as float32, the elevated-node share and the live candidates."""

    def __init__(self, t_total: int, n: int, cm_z: float):
        self.S = np.zeros((t_total, n), dtype=np.float32)
        self.frac = np.zeros(t_total)
        self.cands: dict[int, tuple] = {}
        self.cm_z = cm_z

    def __call__(self, t: int, res, pv, cand, sc=None) -> None:
        p = sc.p_node if sc is not None else pv.p[:, 0]
        self.S[t] = -np.log(np.clip(p, P_FLOOR, 1.0))           # M28 — node evidence
        self.frac[t] = elevated_fraction(res.z, self.cm_z)
        if cand.nodes:
            self.cands[t] = (cand.nodes, cand.p)


def edge_stages(cfg: dict, ctx, rng, overrides: dict | None = None) -> dict:
    """The edge stages as the configuration (plus `overrides`, e.g. {"scmr": "stub"}) selects them."""
    states = {**cfg["modules"], **(overrides or {})}
    out = {}
    for name in EDGE:
        built = registry.build(name, states[name], cfg["params"].get(name, {}), rng if name == "srp" else None)
        built.stage.reset(ctx)
        out[name] = built.stage
    return out


def edge_alarms(cands: dict, stages: dict, ctx) -> list:
    """Replay candidates {t: (nodes, p)} through the edge: an alarm (t, anchor, members) per cluster RAQ confirms."""
    alarms = []
    for t in sorted(cands):
        nodes, p = cands[t]
        ctx.t = t
        prior = stages["srp"].step((t, None, None), ctx)
        cl = stages["cluster"].step(Delivered(nodes=tuple(nodes), p=tuple(p)), ctx)
        if not cl.members:
            continue
        sc = stages["scmr"].step(cl, ctx)
        bf = stages["learn"].step((stages["fisher"].step(cl, ctx), cl, sc, None), ctx)
        raq = stages["raq"].step((cl, sc, bf, prior), ctx)
        anchors = cl.anchor or tuple(m[0] for m in cl.members)
        alarms += [(t, int(a), list(m)) for a, m, d in zip(anchors, cl.members, raq.decide) if d]
    return alarms


def tuning_mask(frac, t0: int, t1: int, p: dict):
    """M28 — the common-mode mask over [t0, t1) exactly as the live tuning buffer builds it (causal at t1)."""
    pad = int(p["cm_pad_min"])
    f0 = max(t0 - pad, 0)
    return cm_mask(frac[f0:t1], float(p["cm_frac"]), pad)[t0 - f0:]


def tuned_h(S, frac, t0: int, t1: int, p: dict, target_per_node_30d: float) -> tuple[float, bool]:
    """M28 — replay-tuned h for another false-candidate target, as the node CUSUM tunes itself."""
    n = S.shape[1]
    target = target_per_node_30d / 30.0 * n * (t1 - t0) / 1440.0
    hi = float(p["h_hi"])
    h = tune_h(S[t0:t1].astype(float), float(p["k_node"]), tuning_mask(frac, t0, t1, p), target, float(p["h_lo"]),
               hi, int(p["bisect_iters"]), int(p["refractory_min"]))
    return h, h >= hi


def replay_candidates(S, start: int, h: float, p: dict) -> dict:
    """M28 — node candidates from `start` on with threshold h (G = 0 at `start`), as {t: (nodes, p)}."""
    ts, ns = cusum_replay(S[start:].astype(float), float(p["k_node"]), h, int(p["refractory_min"]))
    out: dict[int, tuple] = {}
    for t, i in zip((ts + start).tolist(), ns.tolist()):
        nodes, pv = out.get(t, ((), ()))
        out[t] = (nodes + (i,), pv + (float(np.exp(-S[t, i])),))
    return out
