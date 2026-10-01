"""Protocol R2 fast two-knob edge replay: the M30–M34 stages run once per candidate set, SCMR's threshold applied
afterwards.

With the legacy RAQ quorum, a cluster is confirmed when `len(members) ≥ quorum AND scmr.passed`, and SCMR passes when
its M31 ratio is ≥ ρ. No edge stage keeps state that depends on SCMR's verdict (clustering keeps every candidate, the
Fisher stage reads only the members, the Bayes-factor stub ignores SCMR), so one replay that records every cluster's
ratio and quorum verdict gives the alarms at every ρ. The replay refuses configurations where that does not hold.
"""
from __future__ import annotations

from dataclasses import replace

from prahari.core.contracts import Delivered
from prahari.eval.offline import edge_stages


def check_fast(cfg: dict) -> None:
    """The fast replay's conditions: legacy RAQ, the Bayes-factor stub, and no lightning relaxation of SCMR."""
    p, mods = cfg["params"], cfg["modules"]
    if mods["raq"] == "real" and p["raq"]["form"] != "legacy":
        raise ValueError("fast replay needs the legacy RAQ quorum")
    if mods["learn"] != "stub":
        raise ValueError("fast replay needs the Bayes-factor stub (M34 bound)")
    if mods["scmr"] != "real":
        raise ValueError("fast replay records the real SCMR ratio")


def edge_records(cands: dict, cfg: dict, ctx, rng) -> list:
    """Replay candidates {t: (nodes, p)}: every cluster as (t, anchor, members, M31 ratio, quorum verdict)."""
    check_fast(cfg)
    st = edge_stages(cfg, ctx, rng)
    out = []
    for t in sorted(cands):
        nodes, p = cands[t]
        ctx.t = t
        prior = st["srp"].step((t, None, None), ctx)
        if getattr(prior, "lightning", False) or getattr(getattr(ctx, "prior", None), "lightning", False):
            raise ValueError("fast replay: lightning relaxation of SCMR is active")
        cl = st["cluster"].step(Delivered(nodes=tuple(nodes), p=tuple(p)), ctx)
        if not cl.members:
            continue
        sc = st["scmr"].step(cl, ctx)
        open_sc = replace(sc, passed=(True,) * len(sc.passed))                # quorum verdict without SCMR
        bf = st["learn"].step((st["fisher"].step(cl, ctx), cl, open_sc, None), ctx)
        raq = st["raq"].step((cl, open_sc, bf, prior), ctx)
        anchors = cl.anchor or tuple(m[0] for m in cl.members)
        out += [(t, int(a), list(m), float(r), bool(d)) for a, m, r, d in zip(anchors, cl.members, sc.ratio, raq.decide)]
    return out


def alarms_at(records: list, rho: float) -> list:
    """Alarms (t, anchor, members) at SCMR threshold ρ (ρ = 0: SCMR off)."""
    return [(t, a, m) for t, a, m, r, d in records if d and (rho <= 0 or r >= rho)]

