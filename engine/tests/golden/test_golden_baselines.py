"""Golden test (SPEC §9.3): legacy-mode P0 and P1 false-incident rates against the report's 95% intervals.

Slow (≈ 8 minutes): runs only when PRAHARI_GOLDEN=1. The report values are the only hard-coded result numbers in
the project, and they live here (CLAUDE.md rule 10).
"""
import json
import os
from pathlib import Path

import pytest

from prahari.core.config import load_config
from prahari.eval.experiments import run_experiment

from ..conftest import REPO

REF = json.loads((Path(__file__).parent / "report_reference.json").read_text(encoding="utf-8"))
golden = pytest.mark.skipif(os.environ.get("PRAHARI_GOLDEN") != "1", reason="set PRAHARI_GOLDEN=1 to run (slow)")


@pytest.fixture(scope="module")
def summary(tmp_path_factory):
    cfg = load_config(REPO / "configs" / "experiments" / "golden.yaml")
    return run_experiment(cfg, "golden", cfg["experiment"]["seeds"], ["P0", "P1"], tmp_path_factory.mktemp("golden"))


@golden
@pytest.mark.parametrize("pipeline", ["P0", "P1"])
def test_false_incidents_within_report_interval(summary, pipeline):
    ours = summary["pipelines"][pipeline]["false_incidents_per_month"]["rate"]
    lo, hi = REF["pipelines"][pipeline]["ci95"]
    assert lo <= ours <= hi, f"{pipeline}: {ours:.1f} per month outside the report's {lo}–{hi} (see DECISIONS)"
