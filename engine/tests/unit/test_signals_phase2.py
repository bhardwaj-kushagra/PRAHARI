"""Phase 2 unit tests: weather (M5, M6), FFMC (M7, verified against cffdrs), sensor (M17–M19), nuisance and haze (M20)."""
import csv
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import chi2

from prahari.core.clock import Clock
from prahari.core.contracts import Additive, Concentration, Weather
from prahari.core.context import RunContext
from prahari.env.ffmc import FFMCReal, ffmc_daily
from prahari.env.weather import WeatherReal, ar1_step, diurnal_temperature, magnus_rh
from prahari.sensors.haze import HazeReal, trapezoid
from prahari.sensors.mox import SensorReal, residual_cycle
from prahari.sensors.nuisance import NuisanceReal, event_signal

CFFDRS = Path(__file__).parent / "data" / "cffdrs_fwi_01.csv"


def make_ctx(n=10, days=1.0):
    clock = Clock(datetime(2026, 4, 15), days, 1)
    return RunContext(clock=clock, xy=np.zeros((n, 2)), spacing_m=70.0, radius_m=112.0)


def poisson_ci(k):
    """Exact Poisson 95% interval for an observed count k (the M45 form)."""
    lo = 0.5 * chi2.ppf(0.025, 2 * k) if k > 0 else 0.0
    return lo, 0.5 * chi2.ppf(0.975, 2 * k + 2)


# -- M6, M5 weather ---------------------------------------------------------------
def test_m6_rh_from_dew_point():
    # §9.2 — T = 30 °C, dew point 10 °C → RH ≈ 28.9%
    assert magnus_rh(30.0, 10.0) == pytest.approx(28.9, abs=0.05)
    assert magnus_rh(20.0, 20.0) == pytest.approx(100.0)


def test_m5_diurnal_shape():
    h = np.arange(0, 24, 0.25)
    T = diurnal_temperature(30.0, 7.0, h)
    assert h[T.argmax()] == 15.0 and h[T.argmin()] == 3.0
    assert T.mean() == pytest.approx(30.0, abs=1e-9) and T.max() == pytest.approx(37.0)


def test_m5_noise_has_the_stated_stationary_sd():
    rng = np.random.default_rng(1)                               # test fixture only
    x, xs = 0.0, np.empty(200_000)
    for i, z in enumerate(rng.normal(size=xs.size)):
        x = ar1_step(x, 0.98, 0.3, z)
        xs[i] = x
    assert xs.std() == pytest.approx(0.3, rel=0.1)
    assert np.corrcoef(xs[:-1], xs[1:])[0, 1] == pytest.approx(0.98, abs=0.005)


def test_weather_stage_outputs_are_valid_and_diurnal(smoke_cfg):
    p = dict(smoke_cfg["params"]["weather"], rain_prob_day=1.0)
    ctx = make_ctx(days=3)
    st = WeatherReal(p, np.random.default_rng(2))
    st.reset(ctx)
    out = []
    for t in range(3 * 1440):
        ctx.t = t
        w = st.step(t, ctx)
        w.validate(10)
        out.append(w)
    T = np.array([w.T for w in out]).reshape(3, 1440)
    peak_hour = T.argmax(axis=1) / 60.0
    assert np.all(np.abs(peak_hour - 15.0) < 2.0)
    assert sum(w.rain_mm for w in out) > 0                       # rain events happen when rain_prob_day = 1
    assert all(w.dew_c <= w.T for w in out)


# -- M7 FFMC ------------------------------------------------------------------------
def load_cffdrs():
    with open(CFFDRS) as f:
        return list(csv.DictReader(f))


def chain(rows, coef):
    F, out = 85.0, []
    for r in rows:
        F = float(ffmc_daily(F, float(r["TEMP"]), float(r["RH"]), float(r["WS"]), float(r["PREC"]), coef))
        out.append(F)
    return np.array(out)


def test_acceptance_3_m7_matches_cffdrs_over_48_days(smoke_cfg):
    rows = load_cffdrs()
    ref = np.array([float(r["FFMC"]) for r in rows])
    got = chain(rows, smoke_cfg["params"]["ffmc"]["coefficient"])
    assert len(rows) == 48 and np.abs(got - ref).max() < 0.1       # SPEC §5.2 tolerance
    assert np.abs(got - ref).max() < 0.01                            # in fact it matches to rounding
    assert any(float(r["PREC"]) > 0.5 for r in rows)                 # the rain branch is exercised


def test_m7_erratum_e6_the_old_coefficient_fails_the_tolerance():
    rows = load_cffdrs()
    ref = np.array([float(r["FFMC"]) for r in rows])
    assert np.abs(chain(rows, 147.2) - ref).max() > 0.1


def test_ffmc_stage_updates_at_noon_with_24h_rain(smoke_cfg):
    p = smoke_cfg["params"]["ffmc"]

    def run(rain_morning):
        ctx = make_ctx(days=2)
        st = FFMCReal(p, None)
        st.reset(ctx)
        vals = []
        for t in range(2 * 1440):
            ctx.t = t
            rain = rain_morning if t == 600 else 0.0
            vals.append(st.step(Weather(T=30, RH=30, wind_ms=2.0, wind_dir_deg=250, rain_mm=rain), ctx).ffmc)
        return np.array(vals)

    dry, wet = run(0.0), run(10.0)
    changes = np.flatnonzero(np.diff(dry)) + 1
    assert changes.tolist() == [720, 2160]                           # daily code, at noon only
    assert dry[719] == 85.0 and dry[720] == pytest.approx(ffmc_daily(85.0, 30, 30, 7.2, 0.0, p["coefficient"]))
    assert wet[720] < dry[720]                                       # 10 mm in the previous 24 h wets the fuel
    assert wet[2160] > wet[720]                                      # the rain has left the 24 h window


# -- M17–M19 sensor -------------------------------------------------------------------
def run_sensor(smoke_cfg, n=40, days=3):
    ctx = make_ctx(n, days)
    st = SensorReal(smoke_cfg["params"]["sensor"], np.random.default_rng(3))
    st.reset(ctx)
    zero = Additive(v=np.zeros(n))
    es, xs, raws, cycs, tods = [], [], [], [], []
    for t in range(int(days * 1440)):
        ctx.t = t
        r = st.step((t, Concentration(c=np.zeros(n)), None, zero, zero), ctx)
        r.validate(n)
        es.append(st._e.copy())
        xs.append(r.x[:, 0])
        raws.append(r.x_raw[:, 0])
        cycs.append(residual_cycle((t % 1440) / 1440.0, st._phase, st._day_amp))
        tods.append(t % 1440)
    return st, np.array(es), np.array(xs), np.array(raws), np.array(cycs), np.array(tods)


def test_acceptance_1a_ar1_lag1_correlation(smoke_cfg):
    _, e, *_ = run_sensor(smoke_cfg)
    lag1 = np.mean([np.corrcoef(e[:-1, i], e[1:, i])[0, 1] for i in range(e.shape[1])])
    assert lag1 == pytest.approx(0.95, abs=0.02)                     # M19, SPEC Phase 2 acceptance


def test_m19_noisier_by_day(smoke_cfg):
    _, e, _, _, _, tod = run_sensor(smoke_cfg)
    innov = e[1:] - 0.95 * e[:-1]
    day = (tod[1:] > 10 * 60) & (tod[1:] < 14 * 60)
    night = (tod[1:] < 4 * 60) | (tod[1:] > 22 * 60)
    assert innov[day].std() > 1.4 * innov[night].std()


def test_m18_raw_channel_adds_the_uncompensated_cycle(smoke_cfg):
    st, _, x, raw, cyc, _ = run_sensor(smoke_cfg, n=10, days=1)
    np.testing.assert_allclose(raw - x, 0.7 * cyc, atol=1e-12)
    assert np.all((st._c >= 0.2) & (st._c <= 0.4))


# -- M20 nuisance and haze -------------------------------------------------------------
def test_m20_event_shape():
    np.testing.assert_allclose(event_signal([0, 5, 59, 60, -1], 1.5, 5.0, 60), [1.5, 1.5 / np.e, 1.5 * np.exp(-59 / 5), 0, 0])


def test_acceptance_1b_nuisance_counts_within_poisson_bounds(smoke_cfg):
    p, n, days = smoke_cfg["params"]["nuisance"], 100, 30
    ctx = make_ctx(n, days)
    st = NuisanceReal(p, np.random.default_rng(4))
    st.reset(ctx)
    for t in range(days * 1440):
        ctx.t = t
        st.step(t, ctx)
    for mask, rate in ((st.roadside, p["rate_roadside_per_day"]), (~st.roadside, p["rate_other_per_day"])):
        k = int(st.counts[mask].sum())
        lo, hi = poisson_ci(k)
        assert lo <= rate * mask.sum() * days <= hi, (k, rate * mask.sum() * days)


def test_m20_haze_trapezoid_and_rate(smoke_cfg):
    np.testing.assert_allclose(trapezoid([0, 30, 60, 300, 420, 450, 480, 500], 360, 60, 2.0),
                               [0, 1.0, 2.0, 2.0, 2.0, 1.0, 0.0, 0.0])
    p = dict(smoke_cfg["params"]["haze"], crop_burning_multiplier=3.0)
    n, days = 20, 100
    ctx = make_ctx(n, days)
    st = HazeReal(p, np.random.default_rng(5))
    st.reset(ctx)
    for t in range(days * 1440):
        ctx.t = t
        out = st.step(t, ctx)
    lo, hi = poisson_ci(st.n_started)
    assert lo <= 3.0 * days / 10 <= hi
    assert st.gain.min() >= 0.5 and st.gain.max() <= 1.5
    out.validate(n)


def test_scripted_haze_episode(smoke_cfg):
    p = dict(smoke_cfg["params"]["haze"], base_rate_per_10d=0.0,
             scripted=[{"t_min": 100, "duration_min": 200, "amplitude": 1.6}])
    ctx = make_ctx(5)
    st = HazeReal(p, np.random.default_rng(6))
    st.reset(ctx)
    levels = []
    for t in range(500):
        ctx.t = t
        a = st.step(t, ctx)
        levels.append(a.level)
    np.testing.assert_allclose(a.v, st.gain * a.level)
    assert levels[99] == 0 and levels[130] == pytest.approx(0.8) and levels[200] == pytest.approx(1.6)
    assert levels[400] == pytest.approx(1.6 * 20 / 60) and levels[420] == 0   # ramps down, ends at 100 + 200 + 120
