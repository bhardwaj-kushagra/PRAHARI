"""Running protocol R1: seed stages (selection, test) and sensitivity sweeps, one JSON file per seed.

Files are written atomically and an existing file is kept (so an interrupted run resumes). Every file is regenerated
byte for byte from its seed, configuration and code.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml

from prahari.cli import REPO, _in_repo
from prahari.core.config import load_config
from prahari.record.writer import write_text_atomic
from prahari.research.operating import EDGE_VARIANTS, evaluate_seed

DEFAULT_CONFIG = Path("configs") / "research" / "r1.yaml"
DEFAULT_OUT = REPO / "results" / "research"


def load_r1(path: str | Path = DEFAULT_CONFIG) -> dict:
    """The research protocol configuration (plain YAML; the simulation configuration is its `base`)."""
    return yaml.safe_load(_in_repo(Path(path)).read_text(encoding="utf-8"))


def seed_list(spec) -> list[int]:
    """Seeds from {from, to} (inclusive) or an explicit list."""
    if isinstance(spec, dict):
        return list(range(int(spec["from"]), int(spec["to"]) + 1))
    return [int(s) for s in spec]


def base_config(r1: dict) -> dict:
    """The release-1.0 simulation configuration the protocol evaluates."""
    return load_config(_in_repo(Path(r1["base"])))


def set_key(cfg: dict, dotted: str, value) -> None:
    """Set cfg["a"]["b"]["c"] from "a.b.c"."""
    *head, last = dotted.split(".")
    d = cfg
    for k in head:
        d = d[k]
    d[last] = value


def get_key(cfg: dict, dotted: str):
    """Read cfg["a"]["b"]["c"] from "a.b.c"."""
    d = cfg
    for k in dotted.split("."):
        d = d[k]
    return d


def sweep_points(r1: dict, base: dict) -> list[tuple[str, dict]]:
    """Protocol R1 §5 — (label, {dotted key: value}) for every non-default sweep point, in configuration order."""
    out = []
    for name, sp in r1["sweeps"].items():
        if "values" in sp:
            out += [(f"{name}={v:g}" if isinstance(v, (int, float)) else f"{name}={v}", {sp["key"]: v})
                    for v in sp["values"]]
        else:
            out += [(f"{name}=x{s:g}", {k: get_key(base, k) * s for k in sp["keys"]}) for s in sp["scale"]]
    return out


def _job(args) -> str:
    cfg, seed, r1, edge_names, priors, path = args
    if path.exists():
        return str(path)
    cap = (float(r1["cap"]["h_hi"]), int(r1["cap"]["bisect_iters"]))
    res = evaluate_seed(cfg, seed, r1["grids"], cap, tuple(edge_names), tuple(priors))
    write_text_atomic(path, json.dumps(res, separators=(",", ":")))
    return str(path)


def _pool(tasks: list, jobs: int) -> list:
    if jobs > 1 and len(tasks) > 1:
        import multiprocessing as mp
        with mp.get_context("fork").Pool(min(jobs, len(tasks))) as pool:
            return pool.map(_job, tasks, chunksize=1)
    return [_job(t) for t in tasks]


def run_stage(r1: dict, stage: str, jobs: int = 1, out_dir: Path = DEFAULT_OUT, seeds=None) -> list:
    """Selection or test seeds: every pipeline, every PRAHARI variant and the wrong-prior variants."""
    cfg = base_config(r1)
    out = Path(out_dir) / stage
    out.mkdir(parents=True, exist_ok=True)
    tasks = [(cfg, s, r1, list(EDGE_VARIANTS), r1["priors"], out / f"seed{s}.json")
             for s in (seeds or seed_list(r1["seeds"][stage]))]
    return _pool(tasks, jobs)


def run_sweeps(r1: dict, jobs: int = 1, out_dir: Path = DEFAULT_OUT, only=None, seeds=None) -> list:
    """Sensitivity sweeps: each point's configuration on the sweep seeds (main node layer only)."""
    base = base_config(r1)
    out = Path(out_dir) / "sweeps"
    out.mkdir(parents=True, exist_ok=True)
    tasks = []
    for label, over in sweep_points(r1, base):
        if only and label.split("=")[0] not in only:
            continue
        cfg = copy.deepcopy(base)
        for k, v in over.items():
            set_key(cfg, k, v)
        tasks += [(cfg, s, r1, r1["sweep_pipelines"], (), out / f"{label}_seed{s}.json")
                  for s in (seeds or seed_list(r1["seeds"]["sweep"]))]
    return _pool(tasks, jobs)
