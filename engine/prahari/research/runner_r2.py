"""Running protocol R2: scenario configurations and seed stages, one JSON file per seed (atomic; existing files are
kept, so an interrupted run resumes; every file regenerates byte for byte)."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml

from prahari.cli import _in_repo
from prahari.record.writer import write_text_atomic
from prahari.research.operating_r2 import evaluate_seed_r2
from prahari.research.runner import DEFAULT_OUT, _pool_map, base_config, seed_list, set_key

DEFAULT_R2 = Path("configs") / "research" / "r2.yaml"


def load_r2(path: str | Path = DEFAULT_R2) -> dict:
    return yaml.safe_load(_in_repo(Path(path)).read_text(encoding="utf-8"))


def scenario_config(r2: dict, name: str) -> dict:
    """The simulation configuration of a scenario: base, plus the M20b haze (unless `m20`) and any dotted overrides."""
    sc = r2["scenarios"][name]
    cfg = base_config(r2)
    if not sc.get("m20"):
        cfg["params"]["haze"].update(copy.deepcopy(r2["m20b"]))
        cfg["params"]["haze"].update(copy.deepcopy(sc.get("haze", {})))
    for k, v in sc.get("set", {}).items():
        set_key(cfg, k, v)
    return cfg


def _job(args) -> str:
    cfg, seed, r2, path = args
    if path.exists():
        return str(path)
    cap = (float(r2["cap"]["h_hi"]), int(r2["cap"]["bisect_iters"]))
    res = evaluate_seed_r2(cfg, seed, r2["grids"], cap, r2.get("methods"))
    write_text_atomic(path, json.dumps(res, separators=(",", ":")))
    return str(path)


def run_r2(r2: dict, stage: str, scenarios=None, jobs: int = 1, out_dir: Path = DEFAULT_OUT, seeds=None) -> list:
    """A stage (selection or test) of the given scenarios (default: every scenario that has the stage)."""
    tasks = []
    for name, sc in r2["scenarios"].items():
        if (scenarios and name not in scenarios) or stage not in sc["seeds"]:
            continue
        cfg = scenario_config(r2, name)
        out = Path(out_dir) / r2.get("round", "r2") / stage / name
        out.mkdir(parents=True, exist_ok=True)
        tasks += [(cfg, s, r2, out / f"seed{s}.json") for s in (seeds or seed_list(sc["seeds"][stage]))]
    return _pool_map(_job, tasks, jobs)
