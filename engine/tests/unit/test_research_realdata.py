"""Real-data analysis helpers (docs/research/realdata-plan.md) on synthetic inputs with known answers."""
import numpy as np

from prahari.research.realdata import (DAY, TICK_S, find_events, haversine_km, local_excursions, node_layer, replay,
                                       share, to_grid)


def test_to_grid_means_bins_and_carries_short_gaps_only():
    t0 = 1_000_000 - 1_000_000 % TICK_S
    ep = [t0 + 10, t0 + 20, t0 + 300 + 5, t0 + 7 * 300]
    g = to_grid(ep, np.array([1.0, 3.0, 5.0, 9.0]), t0, 9, carry=3)
    assert g[0] == 2.0 and g[1] == 5.0
    assert g[2:5].tolist() == [5.0, 5.0, 5.0] and np.isnan(g[5]) and np.isnan(g[6]) and g[7] == 9.0


def test_share_and_events():
    elev = np.zeros((40, 6), dtype=bool)
    elev[10:20, :4] = True            # 4 of 6 stations for 10 ticks: core (f ≥ 0.5)
    elev[8:10, :2] = True             # 2 of 6 before: span (f ≥ 0.25)
    elev[30:32, :4] = True            # too short a core (2 ticks)
    act = np.ones_like(elev)
    f = share(elev, act)
    assert np.isclose(f[12], 4 / 6) and np.isclose(f[8], 2 / 6)
    assert find_events(f) == [(8, 20)]
    assert np.isnan(share(elev, act, min_active=7)).all()


def test_events_merge_when_close():
    f = np.zeros(100)
    f[10:15] = 0.6
    f[20:25] = 0.6
    assert find_events(f, merge=12) == [(10, 25)]
    assert find_events(f, merge=3) == [(10, 15), (20, 25)]


def test_local_excursions_counts_single_station_runs():
    elev = np.zeros((20, 5), dtype=bool)
    elev[2:6, 1] = True
    elev[10:11, 2] = True
    f = elev.mean(axis=1)
    assert local_excursions(elev, f) == 1


def test_haversine_one_degree_latitude():
    assert abs(haversine_km(np.array([[50.0, 10.0], [51.0, 10.0]]))[0, 1] - 111.2) < 0.3


def test_node_layer_calibrated_on_white_noise():
    """M26 — on exchangeable noise the achieved exceedance at 1% after calibration is close to 1%."""
    rng = np.random.default_rng(5)
    T, N = 20 * DAY, 6
    y = rng.normal(2.0, 0.1, (T, N))
    nl = node_layer(y, 0, 0)
    p = nl["p"][7 * DAY:]
    assert abs(float((p <= 0.01).mean()) - 0.01) < 0.004
    rp = replay(nl["p"], nl["z_slow"], np.isfinite(y))
    assert rp["cand_t"].min() >= 14 * DAY and not rp["h_at_cap"]
