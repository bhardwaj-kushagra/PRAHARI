"""Phase 7 follow-up: the report simulation's node ablations as legacy forms (DECISIONS P7-12) — the capped slow z as
the detection residual, the median/MAD z of the fast residual, and a CUSUM on the signed z — each checked against the
report simulation's own functions on identical inputs."""
import importlib.util

import numpy as np
import pytest
from scipy.special import ndtr

from prahari.core.contracts import PValues, Residuals, Scores
from prahari.detect.prahari.cusum_real import CusumReal
from prahari.detect.prahari.qcc_real import QCCReal
from prahari.detect.prahari.score import ScoreStub
from prahari.detect.prahari.ttc_real import TTCReal
from prahari.eval.experiments import _groups

from .test_eval_phase4 import synthetic
from .test_node_phase5 import ORACLE_PATH, context, run_ttc


@pytest.fixture(scope="module")
def oracle():
    spec = importlib.util.spec_from_file_location("prahari_oracle_p7", ORACLE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ttc_detect_on_slow_gives_the_capped_slow_z(oracle, smoke_cfg):
    x = synthetic(21).astype(float)
    r, z, _ = run_ttc(TTCReal(dict(smoke_cfg["params"]["ttc"], detect_on="slow"), None), x)
    assert np.array_equal(r, z)
    ref = oracle.ewma_z(x, lockup_fix=True)
    assert np.allclose(r[:, 1439:], ref[:, 1439:], rtol=1e-9, atol=1e-9)    # exact from the end of day 1
    r_fast, _, _ = run_ttc(TTCReal(smoke_cfg["params"]["ttc"], None), x)
    assert not np.allclose(r_fast, r)                                        # default unchanged: the fast residual


def test_qcc_robust_z_matches_gauss_z(oracle, monkeypatch, smoke_cfg):
    T, cal_days = 4 * 1440, 2
    r = oracle.fast_resid(synthetic(22, T).astype(float)).astype(float)
    monkeypatch.setattr(oracle, "CAL", slice(0, cal_days * 1440))
    ref = oracle.gauss_z(r)
    ctx = context(T, r.shape[0])
    st = QCCReal(dict(smoke_cfg["params"]["qcc"], cal_days=cal_days, form="robust_z"), None)
    st.reset(ctx)
    Z, P = np.zeros(r.shape), np.zeros(r.shape)
    for t in range(T):
        ctx.t = t
        col = r[:, t][:, None]
        out = st.step(Residuals(r=col, z=col, b=col), ctx)
        out.validate(r.shape[0])
        Z[:, t], P[:, t] = out.z[:, 0], out.p[:, 0]
    t0 = cal_days * 1440
    assert np.allclose(Z[:, t0:], ref[:, t0:], rtol=1e-5, atol=1e-5)       # the oracle returns float32
    assert (Z[:, :t0] == 0).all() and (P[:, :t0] == 1).all()                # no evidence before the scale exists
    assert np.allclose(P[:, t0:], np.clip(ndtr(-Z[:, t0:]), 1e-300, 1.0))    # p = Φ(−z)


def test_score_stub_passes_z_through():
    z = np.array([[1.5], [-2.0]])
    sc = ScoreStub({}, None).step(PValues(p=np.array([[0.1], [0.9]]), n_cal=np.zeros(2), z=z), None)
    assert np.array_equal(sc.z, z[:, 0])
    assert ScoreStub({}, None).step(PValues(p=np.ones((2, 1)), n_cal=np.zeros(2)), None).z is None


def test_cusum_on_z_matches_oracle(oracle, monkeypatch, smoke_cfg):
    rng = np.random.default_rng(23)                                          # test fixture only
    T, t0, t1 = 3000, 1000, 2400
    Z = rng.standard_t(4, (100, T)) + (rng.random((100, T)) < 0.01) * 4.0   # signed, heavy-tailed
    p = dict(smoke_cfg["params"]["cusum"], tune_start_min=t0, tune_end_min=t1, start_min=t1, statistic="z")
    ctx = context(T)
    st = CusumReal(p, None)
    st.reset(ctx)
    cands = []
    for t in range(T):
        ctx.t, ctx.z_slow = t, np.zeros((100, 1))
        pn = np.full(100, 0.5)
        out = st.step(Scores(s=-np.log(pn), p_node=pn, c=np.ones((100, 1)), z=Z[:, t]), ctx)
        cands += [(t, i) for i in out.nodes]
    monkeypatch.setattr(oracle, "TUNE", slice(t0, t1))
    monkeypatch.setattr(oracle, "D_TUNE", (t1 - t0) / 1440)
    h = oracle.tune_h(Z, 0.5, np.zeros(T, bool))
    snap = st.snapshot()
    assert snap["tuned"] and snap["h"] == round(h, 3) and snap["k"] == 0.5 and snap["statistic"] == "z"
    assert cands == oracle.cusum(Z, 0.5, h, t1) and len(cands) > 0


def test_cusum_z_without_z_raises(smoke_cfg):
    st = CusumReal(dict(smoke_cfg["params"]["cusum"], statistic="z"), None)
    st.reset(context(10))
    try:
        st.step(Scores(s=np.zeros(100), p_node=np.ones(100), c=np.ones((100, 1))), context(10))
    except ValueError:
        return
    raise AssertionError("a z-statistic CUSUM without Scores.z must fail (and degrade through the runner)")


def test_legacy_groups():
    g = _groups(["P0", "P2", "P2-SCMR", "P2-QCC", "P2-TTC"], "legacy")
    assert g[()] == ["P2", "P2-SCMR"]
    assert g[(("cusum.statistic", "z"), ("qcc.form", "robust_z"))] == ["P2-QCC"]
    assert g[(("ttc.detect_on", "slow"),)] == ["P2-TTC"] and len(g) == 3
    assert _groups(["P2-QCC"], "stub") == {(("qcc", "stub"),): ["P2-QCC"]}
