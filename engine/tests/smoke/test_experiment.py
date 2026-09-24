"""Harness smoke test: a shortened M46 protocol (1 + 1 + 2 days) runs both passes and writes a sane summary."""
import json

from prahari.core.config import load_config
from prahari.eval.experiments import protocol_fires, run_experiment

from ..conftest import REPO

SHORT = {"params": {"evaluation": {"calibration_days": 1, "tuning_days": 1, "test_days": 2}}}


def test_short_protocol_writes_results(tmp_path):
    cfg = load_config(REPO / "configs" / "experiments" / "golden.yaml", SHORT)
    summary = run_experiment(cfg, "short", [11], ["P0", "P1"], tmp_path)
    assert summary["label"] == "SIMULATION" and summary["seeds"] == [11]
    assert json.loads((tmp_path / "short.json").read_text()) == json.loads(json.dumps(summary))
    combined = json.loads((tmp_path / "summary.json").read_text())             # Phase 7: the report-format table
    assert [r["pipeline"] for r in combined["table"]] == ["P0", "P1"] and combined["sources"] == {"short": {"seeds": [11]}}
    per_seed = json.loads((tmp_path / "short_seed11.json").read_text())
    assert per_seed["n_fires"] == len(per_seed["fires"])          # may be 0 by chance in a 2-day test window
    for name in ("P0", "P1"):
        p = summary["pipelines"][name]
        fa = p["false_incidents_per_month"]
        assert fa["days"] == 2 and fa["ci95"][0] <= fa["rate"] <= fa["ci95"][1]
        assert p["confirmed_within_3h"]["n"] == per_seed["n_fires"]
        assert per_seed["pipelines"][name]["state"] == "real"
    assert summary["reference"]["pipelines"]["P0"]["false_incidents_per_month"] == 291   # labelled report values


def test_protocol_fires_are_deterministic_and_follow_the_slots(tmp_path):
    import numpy as np
    xy = np.array([[385.0, 385.0], [1015.0, 1015.0]])
    ev = load_config(REPO / "configs" / "experiments" / "golden.yaml")["params"]["evaluation"]
    a, dry = protocol_fires(11, ev, xy, 58 * 1440)
    b, _ = protocol_fires(11, ev, xy, 58 * 1440)
    assert [t for t, _ in a] == [t for t, _ in b]
    test0 = 28 * 1440
    assert all(test0 + 120 <= t < 58 * 1440 - 400 + 60 for t, _ in a)
    assert all(385 <= p[0] <= 1015 and 385 <= p[1] <= 1015 for _, p in a)
    assert 0.2 < np.mean(dry) < 0.8 and 40 < len(a) < 100          # 119 slots × (0.8 or 0.2)
