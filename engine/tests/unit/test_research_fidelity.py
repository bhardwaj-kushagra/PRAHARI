"""Research track R1 (docs/research/protocol.md §3): the offline pipelines must reproduce the online harness exactly
at the configured knobs, and the batched CUSUM and tuning must equal the release-1.0 functions row by row."""
import numpy as np
import pytest

from prahari.core.config import load_config
from prahari.detect.prahari.tuning import cusum_replay, tune_h
from prahari.eval.experiments import run_seed
from prahari.research.baselines import ar_innovation
from prahari.research.cusum import by_tick, cusum_multi, tune_multi
from prahari.research.operating import evaluate_seed, flipped_day_types
from prahari.eval.experiments import protocol_config

from ..conftest import REPO

ONLINE = {"P0": "P0", "P1": "P1", "P1t": "P1t", "P2": "P2", "P2-SCMR": "P2-SCMR", "P2-RAQ": "P2-Q2",
          "P2-QCC": "P2-QCC", "P2-TTC": "P2-TTC"}


def short_cfg():
    """The golden configuration on a short protocol (2 d calibration, 2 d tuning, 4 d test) and 36 nodes."""
    cfg = load_config(REPO / "configs" / "experiments" / "golden.yaml")
    ev = cfg["params"]["evaluation"]
    ev["calibration_days"], ev["tuning_days"], ev["test_days"] = 2, 2, 4
    cfg["world"]["n_nodes"] = 36
    cfg["experiment"]["ablation_form"] = "legacy"
    return cfg


def test_batched_cusum_equals_cusum_replay_row_by_row():
    rng = np.random.default_rng(1)
    S, cm = rng.exponential(1.2, (3000, 20)), rng.random(3000) < 0.1
    hits, counts = cusum_multi(S, 1.5, [5.0, 10.0, 20.0], 30, cm)
    for m, h in enumerate([5.0, 10.0, 20.0]):
        t, n = cusum_replay(S, 1.5, h, 30)
        assert np.array_equal(t, hits[m][0]) and np.array_equal(n, hits[m][1])
        assert counts[m] == int((~cm[t]).sum())


def test_batched_tuning_equals_tune_h():
    rng = np.random.default_rng(2)
    S, cm = rng.exponential(1.2, (3000, 20)), rng.random(3000) < 0.1
    hs, _ = tune_multi(S, 1.5, cm, [3, 10, 40], 0.5, 400.0, 18, 30)
    assert hs.tolist() == [tune_h(S, 1.5, cm, g, 0.5, 400.0, 18, 30) for g in (3, 10, 40)]


def test_by_tick_groups_hits_in_time_order():
    assert by_tick(np.array([5, 2, 5]), np.array([3, 1, 0]), 100) == {102: [1], 105: [0, 3]}


def test_ar_innovation_recovers_phi():
    """R1 — the least-squares coefficient of a simulated AR(1) series is close to the true φ (SPEC §9.2 style check)."""
    rng = np.random.default_rng(3)
    z = np.zeros((20000, 3))
    for t in range(1, 20000):
        z[t] = np.array([0.5, 0.9, 0.95]) * z[t - 1] + rng.normal(size=3)
    u, phi, sd = ar_innovation(z, 0, 20000)
    assert np.allclose(phi, [0.5, 0.9, 0.95], atol=0.01)
    assert np.allclose(u[1:].std(axis=0), 1.0, atol=1e-6) and np.allclose(sd, 1.0, atol=0.02)


def test_wrong_prior_flips_are_nested_and_seeded():
    cfg, *_ = protocol_config(short_cfg(), 11)
    def types(q):
        return [d["type"] for d in flipped_day_types(cfg, 11, q)["params"]["srp"]["day_type_overrides"]]

    base = types(0.0)
    assert all(a != b for a, b in zip(base, types(1.0)))                        # q = 1 flips every day

    def flipped(q):
        return {i for i, (a, b) in enumerate(zip(base, types(q))) if a != b}

    assert flipped(0.3) and flipped(0.3) <= flipped(0.6)                        # nested: the same draws for every q
    assert types(0.3) == types(0.3)                                             # seeded


@pytest.mark.parametrize("seed", [11])
def test_offline_pipelines_reproduce_the_online_harness(seed):
    """Protocol R1 §3 fidelity: at the configured knobs every offline pipeline equals the online harness exactly
    (false incidents and every fire's latency)."""
    cfg = short_cfg()
    on = run_seed(cfg, seed, list(ONLINE))
    off = evaluate_seed(cfg, seed, None, default=True)
    assert on["n_fires"] == off["n_fires"] > 0
    for a, b in ONLINE.items():
        assert on["pipelines"][a]["false_incidents"] == off["pipelines"][b]["false_incidents"][0], a
        assert on["pipelines"][a]["latencies_min"] == off["pipelines"][b]["latencies"][0], a
