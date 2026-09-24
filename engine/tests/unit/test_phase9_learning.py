"""Phase 9: the learning loop (M36) — logistic fit by IRLS, the fitted likelihood ratio, the switch from the SBB bound
at K ≥ k_min, cluster-window labels, the training set of K burns and the fixed-budget operating point — and the M26
conformal floor used by the maturity curve (SPEC §9.2: n = 1,000 → p_min = 1/1001)."""
import json

import numpy as np
import pytest
from scipy.special import expit

from prahari.core.contracts import Clusters, Fisher, Scmr
from prahari.detect.prahari.learn import LearnStub, sbb_bound
from prahari.detect.prahari.learn_real import LearnReal, fit_logistic, ln_lr_hat, lr_hat, window_features
from prahari.detect.prahari.qcc_real import conformal_p_counts
from prahari.eval.learning import label_windows, operating_point, training_set

PARAMS = {"k_min": 10, "l2": 1.0, "rho_clip": [1e-3, 1e3], "model_file": None}


def synthetic(n=4000, seed=3):
    rng = np.random.default_rng(seed)                                        # test fixture only
    F = rng.normal(0, 1, (n, 4))
    y = (rng.random(n) < expit(-1.0 + 2.0 * F[:, 0] - 1.0 * F[:, 2])).astype(float)
    return F, y


def test_m36_irls_recovers_the_coefficients():
    F, y = synthetic()
    m = fit_logistic(F, y, l2=1e-6)
    w = np.asarray(m["w"]) / np.r_[1.0, m["sd"]]                              # back to the raw feature scale
    w[0] -= (np.asarray(m["w"][1:]) / np.asarray(m["sd"]) * np.asarray(m["mu"])).sum()
    assert w == pytest.approx([-1.0, 2.0, 0.0, -1.0, 0.0], abs=0.15)
    assert m["n_pos"] + m["n_neg"] == len(y) and m["pi_train"] == pytest.approx(y.mean())


def test_m36_l2_shrinks_and_a_constant_feature_gets_no_weight():
    F, y = synthetic()
    F[:, 3] = 1.0                                                             # c̄ = 1 with the score stub
    loose, tight = fit_logistic(F, y, l2=1e-6), fit_logistic(F, y, l2=1e4)
    assert np.abs(tight["w"][1:]).sum() < 0.2 * np.abs(loose["w"][1:]).sum()
    assert loose["w"][4] == 0.0


def test_m36_likelihood_ratio_divides_out_the_training_prior():
    F, y = synthetic()
    m = fit_logistic(F, y)
    P = expit(m["w"][0] + ((F - m["mu"]) / m["sd"]) @ np.asarray(m["w"][1:]))
    pi = m["pi_train"]
    assert np.exp(ln_lr_hat(m, F)) == pytest.approx((P / (1 - P)) / (pi / (1 - pi)), rel=1e-9)
    flat = fit_logistic(np.zeros((100, 4)), np.r_[np.ones(10), np.zeros(90)])
    assert lr_hat(flat, np.zeros((3, 4))) == pytest.approx(1.0, abs=1e-6)   # uninformative features → LR 1


def test_window_features():
    f = window_features([10.0, 20.0], [2, 3], [3.0, 1e9], None)
    assert f[:, 0].tolist() == [10.0, 20.0] and f[:, 1].tolist() == [2, 3]
    assert f[:, 2] == pytest.approx([np.log(3.0), np.log(1e3)]) and f[:, 3].tolist() == [1.0, 1.0]


def inputs():
    cl = Clusters(members=((1, 2), (3, 4, 5)), p=((1e-3, 1e-3), (1e-3, 1e-3, 1e-3)))
    fi = Fisher(X=(27.6, 41.4), dof=(4, 6), p_cluster=(1.6e-5, 3.3e-7))
    return fi, cl, Scmr(f_loc=(0.5, 0.5), f_net=(0.05, 0.05), ratio=(10.0, 10.0), passed=(True, True))


def test_learn_real_keeps_the_bound_until_k_min(tmp_path):
    fi, cl, sc = inputs()
    bound = LearnStub({}, None).step(fi, None).bf
    assert bound == pytest.approx(tuple(sbb_bound(fi.p_cluster)))
    F, y = synthetic(400)
    for K, fitted in ((5, False), (10, True)):
        path = tmp_path / f"m{K}.json"
        model = {"K": K, **fit_logistic(F, y)}
        path.write_text(json.dumps(model))
        st = LearnReal(dict(PARAMS, model_file=str(path)), None)
        st.reset(None)
        out = st.step((fi, cl, sc, np.ones((10, 1))), None)
        out.validate(10)
        assert st.fitted is fitted
        want = bound if not fitted else tuple(lr_hat(model, window_features(fi.X, [2, 3], sc.ratio, [1.0, 1.0])))
        assert out.bf == pytest.approx(want)
    st = LearnReal(PARAMS, None)                                              # no model file → the bound
    st.reset(None)
    assert st.step((fi, cl, sc, None), None).bf == pytest.approx(bound)
    assert LearnStub({}, None).step((fi, cl, sc, None), None).bf == pytest.approx(bound)   # stub takes both inputs


def windows(t, members, fire=None, passed=None):
    k = len(t)
    return {"t": np.asarray(t, float), "anchor": np.array([m[0] for m in members], float), "members": members,
            "X": np.full(k, 20.0), "size": np.array([len(m) for m in members], float), "ratio": np.full(k, 5.0),
            "passed": np.ones(k) if passed is None else np.asarray(passed, float), "odds": np.full(k, 1e-4),
            "p_cluster": np.full(k, 1e-6), "fire": np.full(k, -1) if fire is None else np.asarray(fire)}


def test_labels_and_the_training_set_of_k_burns():
    xy = np.array([[0.0, 0.0], [100.0, 0.0], [1000.0, 0.0]])
    fires = [(100, np.array([0.0, 0.0])), (500, np.array([1000.0, 0.0]))]
    w = windows([120, 300, 510, 900], [[0, 1], [0, 1], [2], [1]])
    assert label_windows(w, fires, xy, 150.0, 180).tolist() == [0, -1, 1, -1]
    s1 = {"fires": fires, "fire": windows([120, 510], [[0, 1], [2]], fire=[0, 1]),
          "quiet": windows([50, 60, 70], [[0], [1], [2]], passed=[1, 1, 0])}
    s2 = {"fires": fires[:1], "fire": windows([130], [[0, 1]], fire=[0]), "quiet": windows([80], [[1]])}
    F, y = training_set([s1, s2], 1, (1e-3, 1e3))
    assert y.tolist() == [1, 0, 0, 0]                  # one burn; every seed's quiet data; the SCMR-failed window left out
    F, y = training_set([s1, s2], 3, (1e-3, 1e3))
    assert y.tolist() == [1, 1, 1, 0, 0, 0]                                    # burns counted across seeds in order


def test_operating_point_holds_the_false_alarm_budget():
    ev = {"merge_min": 60, "merge_radius_factor": 2.0, "detect_radius_m": 150.0, "detect_window_min": 180}
    xy = np.array([[0.0, 0.0], [1000.0, 0.0], [2000.0, 0.0]])
    dist = np.hypot(*(xy[:, None] - xy[None]).transpose(2, 0, 1))
    s = {"quiet": windows([100, 400, 700], [[0], [1], [2]]), "fire": windows([1010, 2010], [[0], [1]]),
         "fires": [(1000, xy[0]), (2000, xy[1])], "xy": xy, "dist": dist, "R": 100.0, "test0": 0, "t_total": 3000}
    scores = [(np.array([5.0, 3.0, 1.0]), np.array([4.0, 2.0]))]
    one = operating_point([s], scores, 1, ev)
    assert one["false_incidents"] == 1 and one["ln_threshold"] == 3.0 and one["confirmed"] == 1
    two = operating_point([s], scores, 2, ev)
    assert two["false_incidents"] == 2 and two["confirmed"] == 2 and two["rate"] == 1.0
    assert operating_point([s], scores, 0, ev)["confirmed"] == 0


def test_m26_conformal_floor_reference():
    cal = np.zeros((1, 1000))
    assert conformal_p_counts(cal, 1000, np.array([1.0]))[0] == pytest.approx(1 / 1001)   # SPEC §9.2
