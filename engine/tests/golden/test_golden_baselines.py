"""Golden tests (SPEC §9.3 and §7 Phases 5 and 7): legacy-mode pipelines against the report's 95% intervals, the
node-layer acceptance targets (QCC exceedance, replay-tuned local false candidates), the ablations and the spacing
sweep.

Where the report gives an interval, our point estimate must fall inside it (§9.3). Where it gives a point value only
(ablation confirmation rates, spacing), the report's value must fall inside our own M44 interval (DECISIONS P7-6).

Slow (≈ 25 minutes on one core; set PRAHARI_JOBS=4 to run seeds in parallel): runs only when PRAHARI_GOLDEN=1. The
report values are the only hard-coded result numbers in the project, and they live here (CLAUDE.md rule 10).
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
JOBS = int(os.environ.get("PRAHARI_JOBS", "1"))
MAIN = ["P0", "P1", "P1t", "P2"]
ABLATIONS = ["P2-QCC", "P2-TTC", "P2-SCMR", "P2-RAQ"]


def _preset(name, tmp, pipelines=None, **kw):
    cfg = load_config(REPO / "configs" / "experiments" / f"{name}.yaml")
    ex = cfg["experiment"]
    return run_experiment(cfg, name, ex["seeds"], pipelines or ex["pipelines"], tmp, jobs=JOBS, **kw)


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    return tmp_path_factory.mktemp("golden")


@pytest.fixture(scope="module")
def summary(out):
    s = _preset("golden", out, node_metrics=True)
    s["pipelines"].update(_preset("ablation", out)["pipelines"])
    return s


@pytest.fixture(scope="module")
def spacing(out):
    cfg = load_config(REPO / "configs" / "experiments" / "spacing.yaml")
    return _preset("spacing", out, spacings=cfg["experiment"]["spacings"])


@golden
@pytest.mark.parametrize("pipeline", MAIN + ABLATIONS)
def test_false_incidents_within_report_interval(summary, pipeline):
    ours = summary["pipelines"][pipeline]["false_incidents_per_month"]["rate"]
    lo, hi = REF["pipelines"][pipeline]["ci95"]
    assert lo <= ours <= hi, f"{pipeline}: {ours:.1f} per month outside the report's {lo}–{hi} (see DECISIONS)"


@golden
@pytest.mark.parametrize("pipeline", MAIN)
def test_confirmed_within_report_interval(summary, pipeline):
    ours = summary["pipelines"][pipeline]["confirmed_within_3h"]["rate"]
    lo, hi = REF["pipelines"][pipeline]["confirmed_ci95"]
    assert lo <= ours <= hi, f"{pipeline}: {ours:.1%} confirmed outside the report's {lo:.0%}–{hi:.0%} (see DECISIONS)"


@golden
@pytest.mark.parametrize("pipeline", ABLATIONS)
def test_ablation_confirmed_report_value_in_our_interval(summary, pipeline):
    lo, hi = summary["pipelines"][pipeline]["confirmed_within_3h"]["ci95"]
    ref = REF["pipelines"][pipeline]["confirmed_within_3h"]
    assert lo <= ref <= hi, f"{pipeline}: report {ref:.0%} outside our interval {lo:.1%}–{hi:.1%} (see DECISIONS)"


@golden
@pytest.mark.parametrize("spacing_m", ["70", "100", "150"])
def test_spacing_report_value_in_our_interval(spacing, spacing_m):
    lo, hi = spacing["by_spacing"][spacing_m]["pipelines"]["P2"]["confirmed_within_3h"]["ci95"]
    ref = REF["spacing"]["confirmed_within_3h"][spacing_m]
    assert lo <= ref <= hi, f"{spacing_m} m: report {ref:.0%} outside our interval {lo:.1%}–{hi:.1%} (see DECISIONS)"


@golden
def test_node_acceptance_1_qcc_exceedance(summary):
    nd = summary["node"]
    lo, hi = nd["targets"]["exceed"]
    assert lo <= nd["exceed_mean"] <= hi, f"QCC exceedance {nd['exceed_mean']:.2%} outside {lo:.1%}–{hi:.1%}"


@golden
def test_node_acceptance_2_local_false_candidates(summary):
    nd = summary["node"]
    lo, hi = nd["targets"]["local_cand_per_node_30d"]
    assert lo <= nd["local_cand_mean"] <= hi, \
        f"local false candidates {nd['local_cand_mean']:.2f} per node per 30 d outside {lo}–{hi} (see DECISIONS)"
