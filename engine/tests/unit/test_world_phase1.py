"""Phase 1 unit tests: distance fields (M2), static intensity (M3), layouts (M1), greedy siting (M4), path loss (M38)."""
import copy
from itertools import combinations

import numpy as np
import pytest

from prahari.comms.pathloss import (LinksReal, LinksStub, exponent_from_two_points, max_range, path_loss,
                                    rx_power, select_sf)
from prahari.world.geometry import corridor_layout, grid_origin
from prahari.world.interfaces import distance_fields, excluded_mask, inside_polygon, point_segment_distance, segments
from prahari.world.landscape import LandscapeReal, LandscapeStub, static_lambda
from prahari.world.siting import SitingReal, SitingStub, covered_fraction, disk_kernel, greedy_sites

SQUARE = [[0, 0], [100, 0], [100, 100], [0, 100]]


# -- M2 distance fields -------------------------------------------------------
def test_m2_point_to_segment_beside_and_beyond_the_end():
    seg = segments([[-10, 0], [10, 0]])
    d = point_segment_distance(np.array([0.0, 13.0, -10.0]), np.array([10.0, 4.0, 0.0]), seg)
    np.testing.assert_allclose(d, [10.0, 5.0, 0.0])          # beside; beyond the end (3-4-5); on the line


def test_m2_polygon_inside_is_zero_and_outside_is_edge_distance():
    feats = [{"kind": "village", "closed": True, "points": SQUARE}]
    d = distance_fields(np.array([50.0, 130.0, 50.0]), np.array([50.0, 50.0, -20.0]), feats)["village"]
    np.testing.assert_allclose(d, [0.0, 30.0, 20.0])
    assert inside_polygon(np.array([50.0, 150.0]), np.array([50.0, 50.0]), SQUARE).tolist() == [True, False]
    assert excluded_mask(np.array([50.0, 150.0]), np.array([50.0, 50.0]), feats).tolist() == [True, False]


def test_m2_nearest_feature_of_a_class_and_absent_classes():
    feats = [{"kind": "path", "points": [[0, 0], [0, 100]]}, {"kind": "path", "points": [[50, 0], [50, 100]]}]
    d = distance_fields(np.array([40.0]), np.array([50.0]), feats)
    assert set(d) == {"path"} and d["path"][0] == pytest.approx(10.0)
    with pytest.raises(ValueError, match="unknown interface kind"):
        distance_fields(np.array([0.0]), np.array([0.0]), [{"kind": "river", "points": [[0, 0], [1, 1]]}])


# -- M3 static intensity --------------------------------------------------------
def test_m3_lambda_at_zero_and_one_decay_length():
    d = {"path": np.array([0.0, 30.0, np.inf])}
    lam = static_lambda(d, {"path": 1.0}, {"path": 30.0}, lambda0=2.0)
    np.testing.assert_allclose(lam, [2.0, 2.0 / np.e, 0.0])
    both = static_lambda({"path": np.array([0.0]), "village": np.array([0.0])},
                         {"path": 1.0, "village": 1.5}, {"path": 30.0, "village": 150.0}, 1.0)
    assert both[0] == pytest.approx(2.5)                     # Σ_k w_k at D = 0


def test_landscape_real_masks_the_village_and_stub_is_uniform(smoke_cfg):
    world, p = smoke_cfg["world"], smoke_cfg["params"]["landscape"]
    land = LandscapeReal(p, None).step(world, None)
    land.validate(0)
    assert land.lam.shape == (140, 140) and land.cell_m == 10.0
    assert not land.forest.all() and (land.lam[~land.forest] == 0).all()
    assert set(land.dist) == {"village", "path", "road", "power_line"}
    stub = LandscapeStub(p, None).step(world, None)
    assert stub.forest.all() and np.ptp(stub.lam) == 0 and not stub.modelled


# -- M1 layouts ---------------------------------------------------------------------
def test_m1_grid_origin_centres_the_grid():
    np.testing.assert_allclose(grid_origin(100, 70.0, 1400, 1400), [385.0, 385.0])
    np.testing.assert_allclose(grid_origin(100, 70.0, 1400, 1400, offset_m=35), [35.0, 35.0])


def test_m1_corridor_spacing_and_alternating_offsets():
    line = [np.array([[0.0, 0.0], [1000.0, 0.0]])]
    xy, s = corridor_layout(line, 10, 70.0, 15.0)
    assert s == 70.0 and xy.shape == (10, 2)
    np.testing.assert_allclose(np.diff(xy[:, 0]), 70.0)
    np.testing.assert_allclose(xy[:, 1], [15.0, -15.0] * 5)
    xy, s = corridor_layout(line, 40, 70.0, 15.0)            # 1000 m cannot fit 40 nodes at 70 m
    assert s == pytest.approx(25.0) and xy.shape == (40, 2)


def test_m1_corridor_keeps_nodes_outside_closed_rings():
    ring = np.array(SQUARE + [SQUARE[0]], dtype=float)
    xy, _ = corridor_layout([ring], 8, 50.0, 15.0, rings=[np.array(SQUARE, dtype=float)])
    assert not inside_polygon(xy[:, 0], xy[:, 1], SQUARE).any()


# -- M4 coverage and greedy siting --------------------------------------------------
def test_m4_covered_fraction_hand_example():
    centres = np.array([[0.0, 0.0], [10.0, 0.0], [100.0, 0.0]])
    w = np.array([1.0, 1.0, 2.0])
    assert covered_fraction(centres, w, [[0.0, 0.0]], 10.0) == pytest.approx(0.5)
    assert covered_fraction(centres, w, [[100.0, 0.0]], 10.0) == pytest.approx(0.5)
    assert covered_fraction(centres, w, [[0.0, 0.0], [100.0, 0.0]], 10.0) == pytest.approx(1.0)


def test_m4_greedy_is_within_one_minus_one_over_e_of_brute_force():
    rng = np.random.default_rng(3)                           # test fixture only
    lam = rng.random((6, 6)) ** 3
    forest = np.ones_like(lam, dtype=bool)
    cell, r_d = 10.0, 10.0
    gx, gy = np.meshgrid(5 + cell * np.arange(6), 5 + cell * np.arange(6))
    centres = np.column_stack([gx.ravel(), gy.ravel()])
    w = lam.ravel()
    best = max(covered_fraction(centres, w, centres[list(c)], r_d) for c in combinations(range(36), 2))
    got = covered_fraction(centres, w, greedy_sites(lam, forest, cell, 5.0, 5.0, 2, r_d), r_d)
    assert got >= (1 - 1 / np.e) * best - 1e-12
    assert disk_kernel(10.0, 10.0).sum() == 5                # centre plus four neighbours


def test_acceptance_1_greedy_covers_at_least_the_grid_on_the_default_landscape(smoke_cfg):
    world, params = smoke_cfg["world"], smoke_cfg["params"]
    land = LandscapeReal(params["landscape"], None).step(world, None)
    lay = SitingReal(params["siting"], None).step((world, land), None)
    lay.validate(100)
    cov = {k: v["covered"] for k, v in lay.alternatives.items()}
    assert set(cov) == {"grid", "corridor", "greedy"}
    assert cov["greedy"] >= cov["grid"] and cov["greedy"] >= cov["corridor"]
    assert lay.name == "grid" and lay.covered == cov["grid"]
    g = lay.alternatives["greedy"]["xy"]
    rows = np.rint((g[:, 1] - land.y0) / land.cell_m).astype(int)
    cols = np.rint((g[:, 0] - land.x0) / land.cell_m).astype(int)
    assert land.forest[rows, cols].all()                     # greedy never sites a node in the village


def test_acceptance_1_greedy_covers_at_least_the_grid_on_a_synthetic_field(smoke_cfg):
    world = copy.deepcopy(smoke_cfg["world"])
    rng = np.random.default_rng(7)                           # test fixture only
    world["interfaces"] = [{"kind": "path", "points": rng.uniform(0, 1400, (6, 2)).tolist()},
                           {"kind": "road", "points": rng.uniform(0, 1400, (4, 2)).tolist()}]
    land = LandscapeReal(smoke_cfg["params"]["landscape"], None).step(world, None)
    lay = SitingReal(smoke_cfg["params"]["siting"], None).step((world, land), None)
    assert lay.alternatives["greedy"]["covered"] >= lay.alternatives["grid"]["covered"]


def test_siting_stub_is_grid_only_whatever_the_layout(smoke_cfg):
    world = dict(smoke_cfg["world"], layout="greedy")
    lay = SitingStub(smoke_cfg["params"]["siting"], None).step((world, None), None)
    assert lay.name == "grid" and lay.covered == -1.0 and set(lay.alternatives) == {"grid"}
    assert lay.xy.min() == 385.0 and lay.xy.max() == 1015.0


def test_siting_real_builds_the_selected_layout(smoke_cfg):
    params = smoke_cfg["params"]
    land = LandscapeReal(params["landscape"], None).step(smoke_cfg["world"], None)
    for name in ("corridor", "greedy"):
        lay = SitingReal(params["siting"], None).step((dict(smoke_cfg["world"], layout=name), land), None)
        assert lay.name == name
        np.testing.assert_array_equal(lay.xy, lay.alternatives[name]["xy"])
    assert 0 < lay.corridor_spacing_m <= 70.0


# -- M38 path loss and spreading factors -----------------------------------------
def test_acceptance_2_m38_reference_values():
    # §9.2 — d = 200 m, 400 m, no shadowing → 100 dB, 120 dB
    n = exponent_from_two_points(100, 200, 120, 400)
    assert n == pytest.approx(20 / (10 * np.log10(2))) and n == pytest.approx(6.644, abs=1e-3)
    np.testing.assert_allclose(path_loss([200.0, 400.0], 100.0, 200.0, n), [100.0, 120.0])
    assert rx_power(100.0, 14, 2, 2) == pytest.approx(-82.0)


def test_config_exponent_matches_its_derivation(smoke_cfg):
    assert smoke_cfg["params"]["links"]["pl_exponent"] == pytest.approx(exponent_from_two_points(100, 200, 120, 400),
                                                                        abs=1e-3)


def test_m38_sf_boundaries_and_no_link(smoke_cfg):
    p = smoke_cfg["params"]["links"]
    ranges = {sf: max_range(sf, p) for sf in range(7, 13)}
    assert [round(ranges[sf]) for sf in range(7, 13)] == [746, 828, 919, 1020, 1112, 1213]
    d = np.array([ranges[7] - 1, ranges[7] + 1, ranges[12] - 1, ranges[12] + 1])
    prx = rx_power(path_loss(d, p["pl_ref_db"], p["d_ref_m"], p["pl_exponent"]), p["ptx_dbm"],
                   p["gain_tx_dbi"], p["gain_rx_dbi"])
    assert select_sf(prx, p["sensitivity_dbm"], p["margin_db"]).tolist() == [7, 8, 12, 0]


def test_links_real_picks_best_gateway_and_flags_unreachable_nodes(smoke_cfg):
    p = smoke_cfg["params"]["links"]
    xy = np.array([[0.0, 100.0], [0.0, 900.0], [0.0, 3000.0]])
    gws = [{"id": "a", "x": 0.0, "y": 0.0}, {"id": "b", "x": 0.0, "y": 1000.0}]
    links = LinksReal(p, None).step((xy, gws), None)
    links.validate(3)
    assert links.gateway.tolist() == [0, 1, -1] and links.sf.tolist() == [7, 7, 0]
    np.testing.assert_allclose(links.d_m[:2], [100.0, 100.0])
    stub = LinksStub(p, None).step((xy, gws), None)
    assert stub.sf.tolist() == [7, 7, 7] and not stub.modelled
