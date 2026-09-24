"""Phase 6 tests: clustering (M30), SCMR (M31), Fisher (M32), legacy prior (M33), RAQ (M34), escalation (M35), the
edge chain against the report simulation's `confirm`, and complete evidence traces for every alert."""
import importlib.util
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from prahari.core.clock import Clock
from prahari.core.contracts import Clusters, Delivered, Prior, Raq, Scmr
from prahari.core.context import RunContext
from prahari.detect.prahari.decide_real import RaqReal, SrpReal, bayes_quorum, day_types
from prahari.detect.prahari.edge_real import ClusterReal, FisherReal, ScmrReal, components, fisher_combine
from prahari.detect.prahari.escalate_real import EscalateReal
from prahari.detect.prahari.learn import LearnStub, sbb_bound

from ..helpers import run_cfg

ORACLE_PATH = Path(__file__).resolve().parents[3] / "reference" / "prahari_simulation.py"
P_CAND = 1.0 / (30 * 1440) * 30                                              # M32 — r·ΔT ≈ 6.9e-4


@pytest.fixture(scope="module")
def oracle():
    spec = importlib.util.spec_from_file_location("prahari_oracle_p6", ORACLE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def context(days=10):
    xy = np.array([(a, b) for a in np.arange(10) * 70.0 for b in np.arange(10) * 70.0])
    return RunContext(clock=Clock(datetime(2026, 4, 15), days, 1), xy=xy, spacing_m=70.0, radius_m=112.0)


def edge(cfg, ctx, rng=None):
    p = cfg["params"]
    stages = {"cluster": ClusterReal(p["cluster"], None), "scmr": ScmrReal(p["scmr"], None),
              "fisher": FisherReal(p["fisher"], None), "learn": LearnStub({}, None), "raq": RaqReal(p["raq"], None),
              "escalate": EscalateReal(p["escalate"], None)}
    for s in stages.values():
        s.reset(ctx)
    return stages


def run_edge(stages, ctx, t, nodes, prior):
    cl = stages["cluster"].step(Delivered(nodes=tuple(nodes), p=(P_CAND,) * len(nodes)), ctx)
    sc = stages["scmr"].step(cl, ctx)
    fi = stages["fisher"].step(cl, ctx)
    bf = stages["learn"].step(fi, ctx)
    rq = stages["raq"].step((cl, sc, bf, prior), ctx)
    dec = stages["escalate"].step((cl, sc, rq), ctx)
    for out in (cl, sc, fi, bf, rq):
        out.validate(ctx.n_nodes)
    return cl, sc, fi, rq, dec


# -- SPEC §9.2 reference values ----------------------------------------------------------------------
def test_m32_fisher_reference_values():
    assert fisher_combine([6.9e-4] * 2)[2] == pytest.approx(7.4e-6, rel=0.02)
    X, dof, pc = fisher_combine([6.9e-4] * 3)
    assert (round(X, 1), dof) == (43.7, 6) and pc == pytest.approx(8.6e-8, rel=0.02)


def test_m34_bound_reference_values():
    assert float(sbb_bound(4.8e-4)) == pytest.approx(100, rel=0.03)
    assert float(sbb_bound(2.9e-6)) == pytest.approx(1e4, rel=0.03)


# -- Acceptance 2: legacy and Bayes RAQ agree on the worked example ------------------------------------
def test_acceptance_2_legacy_and_bayes_quorum_agree(smoke_cfg):
    assert bayes_quorum(1e-4, 0.01, P_CAND) == 2 and bayes_quorum(1e-6, 0.01, P_CAND) == 3
    ctx = context()
    for form in ("legacy", "bayes"):
        raq = RaqReal(dict(smoke_cfg["params"]["raq"], form=form), None)
        raq.reset(ctx)
        for day, odds, need in (("dry_busy", 1e-4, 2), ("wet_quiet", 1e-6, 3)):
            members = tuple(tuple(range(k)) for k in range(1, 5))
            cl = Clusters(members=members, p=tuple((P_CAND,) * len(m) for m in members))
            bf = LearnStub({}, None).step(_fisher(smoke_cfg, cl), ctx)
            out = raq.step((cl, Scmr(f_loc=(1.0,) * 4, f_net=(0.0,) * 4, ratio=(9.0,) * 4, passed=(True,) * 4), bf,
                            Prior(odds=odds, day_type=day)), ctx)
            assert out.quorum == need
            assert out.decide == tuple(k >= need for k in range(1, 5)), (form, day)


def _fisher(cfg, cl):
    f = FisherReal(cfg["params"]["fisher"], None)
    f.reset(context())
    return f.step(cl, context())


# -- M30/M31/M34 legacy form against the report's `confirm` -------------------------------------------
def test_legacy_edge_matches_oracle_confirm(oracle, smoke_cfg):
    rng = np.random.default_rng(21)                                          # test fixture only
    T = 4 * 1440
    cands = []
    for t in range(T):                                                       # sparse background plus two bursts
        hit = np.flatnonzero(rng.random(100) < 0.0015)
        if 1000 <= t < 1030:
            hit = np.union1d(hit, np.flatnonzero(rng.random(100) < 0.4))    # common mode: SCMR must reject
        if 3000 <= t < 3040 and t % 7 == 0:
            hit = np.union1d(hit, [44, 45, 54])                             # a local event
        cands += [(t, int(i)) for i in hit]
    daytype = np.array([True, False, True, False])
    xy, dist, R = oracle.geometry(70.0)
    ref = oracle.confirm(cands, dist, R, daytype, True, True)
    ctx = context(4)
    stages = edge(smoke_cfg, ctx)
    ours, by_t = [], {}
    for t, i in cands:
        by_t.setdefault(t, []).append(i)
    for t in range(T):
        ctx.t = t
        prior = Prior(odds=1e-4 if daytype[t // 1440] else 1e-6, day_type="dry_busy" if daytype[t // 1440] else "wet_quiet")
        cl, sc, fi, rq, dec = run_edge(stages, ctx, t, by_t.get(t, []), prior)
        ours += [(t, a, sorted(m)) for a, m, d in zip(cl.anchor, cl.members, rq.decide) if d]
    assert len(ref) > 5
    assert ours == [(t, i, sorted(loc)) for t, i, loc in ref]


# -- M30 components form, M31 ratio --------------------------------------------------------------------
def test_m30_components_separate_two_fires(smoke_cfg):
    ctx = context()
    nbr = ctx.neighbours
    assert components([0, 1, 98, 99], nbr) == [[0, 1], [98, 99]] or components([0, 1, 98, 99], nbr) == [[98, 99], [0, 1]]
    st = ClusterReal(dict(smoke_cfg["params"]["cluster"], form="components"), None)
    st.reset(ctx)
    ctx.t = 10
    cl = st.step(Delivered(nodes=(0, 1, 98, 99), p=(0.01,) * 4), ctx)
    assert sorted(cl.members) == [(0, 1), (98, 99)] and cl.anchor == (-1, -1)
    sc = ScmrReal(smoke_cfg["params"]["scmr"], None).step(cl, ctx)
    assert all(sc.passed) and sc.f_net == (0.04, 0.04)


def test_m31_rejects_network_wide_events(smoke_cfg):
    ctx = context()
    st = ClusterReal(smoke_cfg["params"]["cluster"], None)
    st.reset(ctx)
    ctx.t = 5
    st.step(Delivered(nodes=tuple(range(0, 100, 2)), p=(0.01,) * 50), ctx)                 # half the network
    ctx.t = 6
    cl = st.step(Delivered(nodes=(45,), p=(0.01,)), ctx)                                    # one more, inside it
    sc = ScmrReal(smoke_cfg["params"]["scmr"], None).step(cl, ctx)
    assert sc.f_net == (0.51,) and not sc.passed[0] and sc.ratio[0] < 3


# -- M33 legacy day types -------------------------------------------------------------------------------
def test_m33_day_types_and_overrides_do_not_shift_the_stream():
    a = day_types(np.random.default_rng(3), 400, 0.5)
    b = day_types(np.random.default_rng(3), 400, 0.5, [{"day": 2, "type": "wet_quiet"}])
    assert 0.43 < a.count("dry_busy") / 400 < 0.57
    assert b[1] == "wet_quiet" and a[2:] == b[2:]


def test_m33_srp_stage_follows_the_day(smoke_cfg):
    ctx = context(3)
    st = SrpReal(dict(smoke_cfg["params"]["srp"], day_type_overrides=[{"day": 1, "type": "dry_busy"},
                                                                         {"day": 2, "type": "wet_quiet"}]),
                 np.random.default_rng(1))
    st.reset(ctx)
    ctx.t = 600
    assert st.step(None, ctx).odds == 1e-4
    ctx.t = 1440 + 600
    out = st.step(None, ctx)
    assert (out.odds, out.day_type) == (1e-6, "wet_quiet")


# -- M35 escalation ----------------------------------------------------------------------------------------
def test_m35_ladder_alerts_and_clearing(smoke_cfg):
    ctx = context()
    esc = EscalateReal(smoke_cfg["params"]["escalate"], None)
    esc.reset(ctx)

    def step(t, members, ok, dec):
        ctx.t = t
        k = len(members)
        return esc.step((Clusters(members=tuple(members), p=tuple((0.01,) * len(m) for m in members)),
                         Scmr(f_loc=(0.5,) * k, f_net=(0.0,) * k, ratio=(9.0,) * k, passed=(ok,) * k),
                         Raq(quorum=2, threshold=0.01, posterior_odds=(1.0,) * k, decide=(dec,) * k)), ctx)

    assert step(0, [(44,)], False, False).levels == ("WATCH",)
    d = step(5, [(44,)], True, False)
    assert d.levels == ("CANDIDATE",) and d.new_alert == (False,)
    d = step(10, [(44, 45)], True, True)
    assert d.levels == ("CONFIRMED",) and d.new_alert == (True,)
    d = step(20, [(44, 45, 54, 55)], True, True)                  # grew by 2 nodes within 30 min
    assert d.levels == ("ESCALATED",) and d.new_alert == (True,)
    assert step(25, [(45,)], True, False).new_alert == (False,)    # stays escalated, no repeat alert
    d = step(200, [(44,)], True, False)                            # cleared after 120 min: a new incident
    assert d.levels == ("CANDIDATE",) and d.incident != (0,)


# -- Acceptance 3: every alert carries a complete trace ----------------------------------------------------
def test_acceptance_3_every_alert_has_a_complete_trace(smoke_cfg, tmp_path):
    _, health, rec = run_cfg(smoke_cfg, tmp_path / "r.prs.jsonl.gz")
    traces = {tr["trace_id"]: tr for tr in rec.traces}
    alerts = [a for f in rec.frames for a in f["alerts"]]
    assert alerts and all(health[m]["state"] == "real" for m in ("cluster", "scmr", "fisher", "srp", "raq", "escalate"))
    for a in alerts:
        tr = traces[a["trace_id"]]
        assert tr["level"] in ("CONFIRMED", "ESCALATED") and tr["cluster"] == a["cluster"]
        assert set(tr) >= {"per_node", "scmr", "fisher", "prior", "bayes", "explanation", "incident", "anchor"}
        assert tr["scmr"]["modelled"] and tr["fisher"]["method"] == "fisher" and tr["bayes"]["method"] == "legacy quorum"
        assert tr["fisher"]["dof"] == 2 * len(tr["cluster"]) and tr["bayes"]["decision"]
        assert "legacy RAQ" in tr["explanation"] and "Fisher p" in tr["explanation"]
