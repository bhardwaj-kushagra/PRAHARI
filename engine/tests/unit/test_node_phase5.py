"""Phase 5 tests: TTC (M24 with the cap, M25), QCC (M26), node CUSUM and replay tuning (M28), P1t — checked against
the SPEC reference values, closed-form values and the report's reference simulation on identical inputs."""
import importlib.util
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from prahari.core import registry
from prahari.core.clock import Clock
from prahari.core.contracts import Readings, Residuals, Scores
from prahari.core.context import RunContext
from prahari.detect.baselines.v1t import V1ReplayTuned
from prahari.detect.prahari.cusum_real import CusumReal
from prahari.detect.prahari.qcc_real import QCCReal, RowSearch, conformal_p_counts
from prahari.detect.prahari.ttc import TTCStub
from prahari.detect.prahari.ttc_real import FastResidual, TTCReal
from prahari.detect.prahari.tuning import cm_mask, cusum_replay, tune_h

from ..helpers import run_cfg
from .test_eval_phase4 import step_all, synthetic

ORACLE_PATH = Path(__file__).resolve().parents[3] / "reference" / "prahari_simulation.py"
XY = np.array([(a, b) for a in np.arange(10) * 70.0 for b in np.arange(10) * 70.0])


@pytest.fixture(scope="module")
def oracle():
    spec = importlib.util.spec_from_file_location("prahari_oracle_p5", ORACLE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def context(T, n=100):
    xy = XY if n == 100 else XY[:n]
    return RunContext(clock=Clock(datetime(2026, 4, 15), T / 1440, 1), xy=xy, spacing_m=70.0, radius_m=112.0)


def run_ttc(stage, x):
    """Step a TTC stage over x (N, T); returns r, z, b as (N, T) arrays."""
    ctx = context(x.shape[1], x.shape[0])
    stage.reset(ctx)
    out = {k: np.zeros(x.shape) for k in "rzb"}
    for t in range(x.shape[1]):
        ctx.t = t
        res = stage.step(Readings(x=x[:, t][:, None], x_raw=x[:, t][:, None]), ctx)
        res.validate(x.shape[0])
        for k in "rzb":
            out[k][:, t] = getattr(res, k)[:, 0]
    return out["r"], out["z"], out["b"]


# -- M24 / M25 against the oracle ---------------------------------------------------------------
def test_m24_capped_baseline_matches_oracle(oracle, smoke_cfg):
    x = synthetic(6).astype(float)
    _, z, _ = run_ttc(TTCReal(smoke_cfg["params"]["ttc"], None), x)
    ref = oracle.ewma_z(x, lockup_fix=True)
    assert np.allclose(z[:, 1439:], ref[:, 1439:], rtol=1e-9, atol=1e-9)    # exact from the end of day 1


def test_m25_fast_residual_matches_oracle(oracle):
    x = synthetic(7).astype(float)
    f = FastResidual((100,), 60, 180)
    r = np.stack([f.step(x[:, t]) for t in range(x.shape[1])], axis=1)
    assert np.allclose(r, oracle.fast_resid(x), rtol=1e-5, atol=1e-5)         # the oracle returns float32


# -- Acceptance 3: the TTC stub reproduces v1's lock-up and daily-cycle leakage ------------------
def test_acceptance_3a_stub_locks_up_real_recovers(smoke_cfg):
    rng = np.random.default_rng(1)                                           # test fixture only
    T = 5 * 1440
    x = rng.normal(0.0, 0.1, (4, T))
    x[:, 2 * 1440:] += 2.0                                                   # sustained +2 su step (20 sd)
    p = smoke_cfg["params"]["ttc"]
    _, z_s, b_s = run_ttc(TTCStub(p, None), x)
    _, z_r, b_r = run_ttc(TTCReal(p, None), x)
    last = slice(4 * 1440, T)
    assert np.all(np.abs(b_s[:, -1]) < 0.1) and np.all(np.abs(z_s[:, last]) >= 3)     # v1: frozen for good
    assert np.all(np.abs(b_r[:, -1] - 2.0) < 0.2) and np.median(np.abs(z_r[:, last])) < 3  # cap: re-baselined


def test_acceptance_3b_daily_cycle_leakage(smoke_cfg):
    T = 6 * 1440
    x = np.sin(2 * np.pi * np.arange(T) / 1440)[None, :].repeat(2, axis=0)
    p = smoke_cfg["params"]["ttc"]
    r_s, _, _ = run_ttc(TTCStub(p, None), x)
    r_r, _, _ = run_ttc(TTCReal(p, None), x)
    amp = lambda r: (r[0, -1440:].max() - r[0, -1440:].min()) / 2            # noqa: E731
    wt = np.pi                                                               # ωτ with τ = 720 min, 24 h period
    assert wt / np.sqrt(1 + wt * wt) == pytest.approx(0.953, abs=5e-4)       # M25 note (DER)
    assert amp(r_s) == pytest.approx(0.953, abs=0.02)                        # slow baseline alone: ~95% leaks
    w = 2 * np.pi / 1440                                                     # lagged 120-min window centred 120.5 back
    sinc = np.sin(60 * w) / (120 * np.sin(w / 2))
    assert amp(r_r) == pytest.approx(abs(1 - sinc * np.exp(-1j * w * 120.5)), abs=0.01)   # ≈ 0.52
    assert amp(r_r) < 0.6


# -- M26 --------------------------------------------------------------------------------------------
def test_m26_floor_reference_value():
    rows = np.random.default_rng(2).normal(size=(3, 1000))                   # test fixture only
    assert RowSearch(rows).p(np.full(3, 99.0)) == pytest.approx(np.full(3, 1 / 1001))
    assert RowSearch(rows).p(np.full(3, -99.0)) == pytest.approx(np.ones(3))


def test_m26_binary_search_equals_counting_with_ties():
    rng = np.random.default_rng(3)                                           # test fixture only
    cal = np.round(rng.normal(size=(50, 400)), 1)                            # many ties
    s = np.round(rng.normal(size=50) * 2, 1)
    assert np.array_equal(RowSearch(cal).p(s), conformal_p_counts(cal, 400, s))


def run_qcc(p, r):
    ctx = context(r.shape[1], r.shape[0])
    stage = QCCReal(p, None)
    stage.reset(ctx)
    P, n = np.zeros(r.shape), np.zeros(r.shape[1])
    for t in range(r.shape[1]):
        ctx.t = t
        out = stage.step(Residuals(r=r[:, t][:, None], z=r[:, t][:, None], b=r[:, t][:, None]), ctx)
        out.validate(r.shape[0])
        P[:, t], n[t] = out.p[:, 0], out.n_cal[0]
    return P, n


def test_m26_frozen_calibration_matches_oracle(oracle, monkeypatch, smoke_cfg):
    T, cal_days = 4 * 1440, 2
    r = oracle.fast_resid(synthetic(8, T).astype(float)).astype(float)
    monkeypatch.setattr(oracle, "T", T)
    monkeypatch.setattr(oracle, "CAL", slice(0, cal_days * 1440))
    ref = oracle.conformal_p(r, np.arange(T) % 1440)
    P, n = run_qcc(dict(smoke_cfg["params"]["qcc"], cal_days=cal_days), r)
    assert np.array_equal(P[:, cal_days * 1440:], ref[:, cal_days * 1440:])
    assert n[0] == 0 and n[-1] == cal_days * 240 and P.min() >= 1 / (cal_days * 240 + 1)   # floor 1/(n+1)


def test_m26_exceedance_on_exchangeable_data(smoke_cfg):
    r = np.random.default_rng(9).normal(size=(100, 6 * 1440))                # test fixture only
    P, _ = run_qcc(dict(smoke_cfg["params"]["qcc"], cal_days=4), r)
    ex = (P[:, 4 * 1440:] <= 0.01).mean()
    assert ex == pytest.approx(9 / 961, abs=0.003)                           # ⌊0.01·961⌋ / 961 with n = 960


def test_m26_sliding_window_keeps_the_last_days(smoke_cfg):
    r = np.random.default_rng(10).normal(size=(4, 5 * 1440))                 # test fixture only
    _, n = run_qcc(dict(smoke_cfg["params"]["qcc"], window="sliding", window_days=2), r)
    assert n.max() == 2 * 240 and n[-1] == 2 * 240


# -- M28 and the P1t tuning against the oracle -------------------------------------------------------
def test_m28_cusum_mask_and_tuning_match_oracle(oracle, monkeypatch):
    rng = np.random.default_rng(11)                                          # test fixture only
    T = 3 * 1440
    S = rng.exponential(1.0, (100, T)) + (rng.random((100, T)) < 0.01) * 6.0
    ours_t, ours_i = cusum_replay(S.T, 1.5, 12.0, 30)
    assert list(zip(ours_t.tolist(), ours_i.tolist())) == oracle.cusum(S, 1.5, 12.0)
    z = rng.normal(size=(100, T))
    z[:40, 2000:2030] += 5.0                                                 # a common-mode burst
    frac = (z >= 3).mean(axis=0)
    cm = cm_mask(frac, 0.25, 60)
    assert np.array_equal(cm, oracle.cm_mask(z)) and cm[1940:2090].all() and cm.sum() == 150
    monkeypatch.setattr(oracle, "TUNE", slice(1440, 2880))
    monkeypatch.setattr(oracle, "D_TUNE", 1)
    h_ref = oracle.tune_h(S, 1.5, cm)
    h = tune_h(S.T[1440:2880], 1.5, cm[1440:2880], 100 / 30, 0.5, 400.0, 18, 30)
    assert h == h_ref and 1.0 < h < 400.0
    assert tune_h(S.T[1440:2880] + 5.0, 1.5, cm[1440:2880], 100 / 30, 0.5, 400.0, 18, 30) == 400.0  # search cap


def test_m28_stage_tunes_and_restarts(oracle, monkeypatch, smoke_cfg):
    rng = np.random.default_rng(12)                                          # test fixture only
    T, t0, t1 = 3000, 1000, 2400
    S = rng.exponential(1.0, (100, T)) + (rng.random((100, T)) < 0.01) * 6.0
    p = dict(smoke_cfg["params"]["cusum"], tune_start_min=t0, tune_end_min=t1, start_min=t1)
    ctx = context(T)
    st = CusumReal(p, None)
    st.reset(ctx)
    cands = []
    for t in range(T):
        ctx.t, ctx.z_slow = t, np.zeros((100, 1))
        out = st.step(Scores(s=S[:, t], p_node=np.exp(-S[:, t]), c=np.ones((100, 1))), ctx)
        out.validate(100)
        cands += [(t, i) for i in out.nodes]
    monkeypatch.setattr(oracle, "TUNE", slice(t0, t1))
    monkeypatch.setattr(oracle, "D_TUNE", (t1 - t0) / 1440)
    h = oracle.tune_h(S, 1.5, np.zeros(T, bool))
    assert st.snapshot()["tuned"] and st.snapshot()["h"] == round(h, 3)
    assert cands == oracle.cusum(S, 1.5, h, t1) and len(cands) > 0


def test_p1t_matches_oracle(oracle, monkeypatch, smoke_cfg):
    x = synthetic(13).astype(float)
    x[:40, 2600:2630] += 20.0                                                # common mode inside the tuning window
    t0, t1 = 2000, 3400
    p = dict(smoke_cfg["params"]["baseline_p1t"], tune_start_min=t0, tune_end_min=t1, start_min=t1)
    stage = V1ReplayTuned(p, None)
    cands, alarms = step_all(stage, x, x, t1)
    zs = oracle.ewma_z(x)
    cm = oracle.cm_mask(zs)
    monkeypatch.setattr(oracle, "TUNE", slice(t0, t1))
    monkeypatch.setattr(oracle, "D_TUNE", (t1 - t0) / 1440)
    h = oracle.tune_h(zs, 0.5, cm)
    assert cm[2600:2630].all() and stage.snapshot()["h"] == round(h, 3)
    ref_c = oracle.cusum(zs, 0.5, h, t1)
    xy, dist, R = oracle.geometry(70.0)
    ref_a = oracle.confirm(ref_c, dist, R, np.ones(10, bool), False, False)
    assert cands == ref_c and [(t, i, sorted(m)) for t, i, m in ref_a] == alarms


# -- Isolation: a failing real node stage degrades to its stub -------------------------------------
class RaisingQCC(QCCReal):
    def step(self, res, ctx):
        if ctx.t >= 30:
            raise RuntimeError("qcc failed")
        return super().step(res, ctx)


def test_failing_qcc_degrades_to_stub(smoke_cfg, tmp_path, monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, ("qcc", "real"), RaisingQCC)
    cfg = dict(smoke_cfg, run=dict(smoke_cfg["run"], days=0.05),
               modules=dict(smoke_cfg["modules"], ttc="real", qcc="real", cusum="real"))
    _, health, rec = run_cfg(cfg, tmp_path / "r.prs.jsonl.gz")
    assert health["qcc"]["state"] == "degraded" and health["qcc"]["running"] == "stub"
    assert health["ttc"]["state"] == "real" and health["cusum"]["state"] == "real"
    assert rec.frames[-1]["t"] == 71 and "n_cal" in rec.frames[-1]["nodes"]


# -- Warm start (record.from_day): simulate from day 0, record from a later day ------------------------
def test_warm_start_records_from_the_given_day(smoke_cfg, tmp_path):
    import hashlib
    cfg = dict(smoke_cfg, run=dict(smoke_cfg["run"], days=0.1), record=dict(smoke_cfg["record"], from_day=0.05))
    _, _, rec = run_cfg(cfg, tmp_path / "a.prs.jsonl.gz")
    run_cfg(cfg, tmp_path / "b.prs.jsonl.gz")
    assert rec.header["record_from_min"] == 72 and rec.frames[0]["t"] == 72
    assert all(f["t"] >= 72 for f in rec.frames) and all(tr["t"] >= 72 for tr in rec.traces)
    sha = [hashlib.sha256((tmp_path / n).read_bytes()).hexdigest() for n in ("a.prs.jsonl.gz", "b.prs.jsonl.gz")]
    assert sha[0] == sha[1]
    _, _, cold = run_cfg(dict(cfg, record=dict(cfg["record"], from_day=0)), tmp_path / "c.prs.jsonl.gz")
    assert "record_from_min" not in cold.header and cold.frames[0]["t"] == 0
