"""Unit tests for the equations the Phase 0 stubs use, with SPEC §9.2 reference values."""
import numpy as np
import pytest

from prahari.detect.prahari.cusum import cusum_step, h_for_arl, siegmund_arl
from prahari.detect.prahari.fisher import bonferroni
from prahari.detect.prahari.learn import sbb_bound
from prahari.detect.prahari.qcc import conformal_p, gaussian_p
from prahari.detect.prahari.score import node_score
from prahari.fire.growth import source_strength
from prahari.fire.plume import directional_factor, downwind_unit, legacy_concentration, plume_at_nodes
from prahari.world.geometry import grid_layout, neighbourhood_radius


def test_m23_h_for_30_day_arl():
    # §9.2 — k = 0.5, ARL 43,200 → h ≈ 8.8
    h = h_for_arl(43200, 0.5)
    assert h == pytest.approx(8.8, abs=0.05)
    assert siegmund_arl(h, 0.5) == pytest.approx(43200, rel=1e-6)


def test_m13_directional_factor():
    # §9.2 — φ = 0, π/2, π → 1.0, 0.325, 0.1
    np.testing.assert_allclose(directional_factor(np.cos([0, np.pi / 2, np.pi])), [1.0, 0.325, 0.1], atol=1e-12)


def test_m12_downwind_and_upwind_at_50m():
    # Phase 3a acceptance values, already provided by the stub: 2.5 su downwind, 0.25 su upwind at full growth
    q_ref = 2.5 * np.exp(50 / 40)
    assert legacy_concentration(q_ref, 50.0, 1.0, 40.0) == pytest.approx(2.5, abs=1e-9)
    assert legacy_concentration(q_ref, 50.0, -1.0, 40.0) == pytest.approx(0.25, abs=1e-9)


def test_m9_source_ramp():
    q = source_strength(np.array([-5.0, 0.0, 10.0, 1e6]), 2.0, 10.0)
    np.testing.assert_allclose(q, [0.0, 0.0, 2.0 * (1 - np.exp(-1)), 2.0])


def test_m16_transport_delay_and_wind_direction():
    # Wind from the west (270°) carries smoke east (+x).
    np.testing.assert_allclose(downwind_unit(270.0), [1.0, 0.0], atol=1e-12)
    xy = np.array([[150.0, 100.0], [50.0, 100.0]])          # 50 m downwind, 50 m upwind
    u_ms = 1.0                                               # 60 m/min → 50 m takes 0.833 min
    before = plume_at_nodes(xy, np.array([100.0]), np.array([100.0]), np.array([0.8]), np.array([1.0]), 10.0,
                            u_ms, 270.0, 40.0)
    after = plume_at_nodes(xy, np.array([100.0]), np.array([100.0]), np.array([1e6]), np.array([1.0]), 10.0,
                           u_ms, 270.0, 40.0)
    assert before[0, 0] == 0.0                               # smoke has not arrived yet
    assert after[0, 0] == pytest.approx(np.exp(-50 / 40), rel=1e-6)
    assert after[0, 1] == pytest.approx(0.1 * np.exp(-50 / 40), rel=1e-6)


def test_m26_conformal_floor():
    # §9.2 — n = 1000 → p_min = 1/1001
    cal = np.sort(np.random.default_rng(0).normal(size=1000))
    assert conformal_p(cal, 1e9) == pytest.approx(1 / 1001)
    assert conformal_p(cal, -1e9) == pytest.approx(1.0)


def test_m34_bound_reference_values():
    # §9.2 — BF bound 100 at p ≈ 4.8e-4, 1e4 at p ≈ 2.9e-6
    np.testing.assert_allclose(sbb_bound([4.8e-4, 2.9e-6]), [100.0, 1e4], rtol=0.01)
    assert sbb_bound([0.5])[0] == 1.0
    assert np.isfinite(sbb_bound([0.0])[0])                  # clipped at 1e-300 (SPEC §10)


def test_m27_single_channel_score_and_gaussian_p():
    p = gaussian_p(np.array([[0.0], [3.0]]))
    assert p[0, 0] == pytest.approx(0.5)
    np.testing.assert_allclose(node_score(p, np.ones_like(p)), -np.log(p[:, 0]))
    assert bonferroni([0.01, 0.2, 0.5]) == pytest.approx(0.03)


def test_cusum_step_candidate_and_refractory():
    G = np.zeros(2)
    ref = np.zeros(2)
    G, hit, ref = cusum_step(G, np.array([20.0, 0.0]), 0.5, 8.8, ref, 30, 1)
    assert hit.tolist() == [True, False] and G[0] == 0.0 and ref[0] == 30
    G, hit, ref = cusum_step(G, np.array([20.0, 0.0]), 0.5, 8.8, ref, 30, 1)
    assert not hit[0]                                         # refractory blocks a second candidate


def test_m1_grid_and_m30_radius():
    xy = grid_layout(100, 70.0, 35.0)
    assert xy.shape == (100, 2)
    assert xy[0].tolist() == [35.0, 35.0] and xy[-1].tolist() == [665.0, 665.0]
    assert neighbourhood_radius(70.0, 1.6) == pytest.approx(112.0)
    with pytest.raises(ValueError):
        grid_layout(10, 70.0)
