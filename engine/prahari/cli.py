"""Command-line interface: `prahari run --config <scenario.yaml> --out <recording.prs.jsonl.gz>`."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from prahari.core.config import ConfigError, load_config
from prahari.core.pipeline import Simulation
from prahari.record.writer import RecordingWriter, write_text_atomic


REPO = Path(__file__).resolve().parents[2]                  # engine/prahari/cli.py → repository root


def _in_repo(path: Path) -> Path:
    """A relative configuration path as given (from the current folder), or else under the repository root."""
    return path if path.is_absolute() or path.exists() or not (REPO / path).exists() else REPO / path


def _seed_list(text: str) -> list[int]:
    """`--seeds 11,22,33` → [11, 22, 33]; anything else is an argument error, not a traceback."""
    try:
        seeds = [int(v) for v in text.split(",") if v.strip()]
    except ValueError:
        raise argparse.ArgumentTypeError(f"seeds must be whole numbers separated by commas, got {text!r}") from None
    if not seeds:
        raise argparse.ArgumentTypeError("give at least one seed")
    return seeds


def _positive_int(text: str) -> int:
    try:
        v = int(text)
    except ValueError:
        v = 0
    if v < 1:
        raise argparse.ArgumentTypeError(f"must be a whole number ≥ 1, got {text!r}")
    return v


def health_path(out: Path) -> Path:
    """`recordings/x.prs.jsonl.gz` → `recordings/x.health.json` (per-module state and timings of a run)."""
    name = out.name.split(".prs")[0] if ".prs" in out.name else out.stem
    return out.with_name(f"{name}.health.json")


def run(config: str, out: str, seed: int | None = None, days: float | None = None) -> dict:
    """`prahari run`: simulate one scenario and write its recording and health file; returns the run summary."""
    overrides: dict = {"run": {}}
    if seed is not None:
        overrides["run"]["seed"] = seed
    if days is not None:
        overrides["run"]["days"] = days
    cfg = load_config(config, overrides if overrides["run"] else None)
    sim = Simulation(cfg)
    writer = RecordingWriter(out)
    t0 = time.perf_counter()
    health = sim.run(writer)
    elapsed = time.perf_counter() - t0
    summary = {"recording": str(out), "seconds": round(elapsed, 3), "frames": writer.n_frames,
               "traces": writer.n_traces, "modules": health}
    write_text_atomic(health_path(Path(out)), json.dumps(summary, indent=2))
    return summary


def experiment(args) -> int:
    """`prahari experiment`: the M46 protocol for a preset (or the Phase 9 learning preset) → results/*.json."""
    from prahari.eval.experiments import run_experiment
    path = Path(args.config) if args.config else _in_repo(Path("configs") / "experiments" / f"{args.preset}.yaml")
    if not args.config and not path.is_file():
        known = sorted(p.stem for p in (REPO / "configs" / "experiments").glob("*.yaml"))
        raise ConfigError(f"unknown preset {args.preset!r}; presets: {', '.join(known)}")
    try:
        cfg = load_config(path)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2
    if cfg["experiment"]["train_seeds"]:                  # Phase 9: learning curve and calibration maturity
        return learning(cfg, args)
    seeds = args.seeds if args.seeds else cfg["experiment"]["seeds"]
    pipes = args.pipelines.split(",") if args.pipelines else cfg["experiment"]["pipelines"]
    t0 = time.perf_counter()
    ex = cfg["experiment"]
    summary = run_experiment(cfg, path.stem, seeds, pipes, args.out, bool(ex.get("node_metrics", False)),
                             jobs=args.jobs, dial=ex.get("dial", []), spacings=ex.get("spacings", []))
    blocks = summary["by_spacing"].items() if "by_spacing" in summary else [("", summary)]
    for sp, block in blocks:
        for name, p in block["pipelines"].items():
            fa, det = p["false_incidents_per_month"], p["confirmed_within_3h"]
            print(f"{sp + ' m ' if sp else ''}{name}: {fa['rate']:.1f} false incidents/month (95% CI "
                  f"{fa['ci95'][0]:.1f}–{fa['ci95'][1]:.1f}; per seed {[round(v, 1) for v in fa['per_seed']]}), "
                  f"confirmed within 3 h {det['k']}/{det['n']} — SIMULATION")
    for pt in summary.get("dial", []):
        print(f"dial r = {pt['target_per_node_30d']:.2f}/node/30 d: {pt['false_incidents_per_month']['rate']:.1f} "
              f"false incidents/month, confirmed {pt['confirmed_within_3h']['k']}/{pt['confirmed_within_3h']['n']}, "
              f"median latency {pt['latency_median_min']} min — SIMULATION")
    if "node" in summary:
        nd = summary["node"]
        print(f"node layer: QCC exceedance at p ≤ {nd['targets']['exceed_p']} {nd['exceed_mean']:.2%}; node-local false "
              f"candidates {nd['local_cand_mean']:.2f} per node per 30 d (median {nd['local_cand_median']:.2f}); "
              f"mean tuned h {nd['h_mean']:.1f} — SIMULATION")
    print(f"wrote {args.out}/{path.stem}.json and {args.out}/summary.json in {time.perf_counter() - t0:.0f} s")
    return 0


def learning(cfg: dict, args) -> int:
    """Phase 9: M36 learning curve and M26 calibration maturity → results/learning.json."""
    from prahari.eval.learning import run_learning
    t0 = time.perf_counter()
    cur = run_learning(cfg, args.out, jobs=args.jobs)
    b = cur["bound"]
    print(f"budget {cur['fa_budget_per_month']} false incidents/month on held-out seeds {cur['test_seeds']} — SIMULATION")
    print(f"bound: confirmed {b['confirmed']}/{b['fires']}, median {b['latency_median_min']} min, "
          f"{b['false_incidents']} false incidents")
    for r in cur["rows"]:
        print(f"K = {r['K']} ({r['rule']}, {r['n_pos']} fire / {r['n_neg']} quiet windows): confirmed "
              f"{r['confirmed']}/{r['fires']} ({r['ci95'][0]:.2f}–{r['ci95'][1]:.2f}), median {r['latency_median_min']} min, "
              f"{r['false_incidents']} false incidents")
    for r in cur["maturity"]["rows"]:
        print(f"{r['cal_days']} d calibration: p_min {r['p_min']:.1e}, candidates {r['candidate_rate']:.2f} of "
              f"{r['fires']} fires, median {r['candidate_latency_median_min']} min, h {r['h']}")
    print(f"wrote {args.out}/learning.json and {args.out}/summary.json in {time.perf_counter() - t0:.0f} s")
    return 0


def energy(args) -> int:
    """Phase 8: M41–M43 energy comparison → results/energy.json, then rebuild results/summary.json."""
    from prahari.eval.energy_table import energy_table
    from prahari.eval.report import combine
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    table = energy_table(load_config(_in_repo(Path(args.config))))
    write_text_atomic(out / "energy.json", json.dumps(table, indent=1))
    combine(out)
    for r in table["rows"]:
        print(f"{r['sensor']} {r['mode']}: {r['wh_day']:.3f} Wh/day, {r['autonomy_days']:.1f} days on a full store — SIMULATION")
    print(f"harvest {table['harvest_wh_day']['clear']} Wh/day clear, {table['harvest_wh_day']['cloudy']} cloudy; "
          f"store {table['store_wh']} Wh; wrote {out}/energy.json")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point of the `prahari` command. Errors end in one line on stderr and a non-zero exit, never a traceback:
    2 for a configuration problem, 1 for a file problem, 130 when interrupted (nothing is written then)."""
    ap = argparse.ArgumentParser(prog="prahari", description="PRAHARI-SIM engine (all output is SIMULATION)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run one scenario and write a recording")
    r.add_argument("--config", required=True, help="scenario YAML (composed over configs/default.yaml)")
    r.add_argument("--out", required=True, help="output recording, e.g. recordings/smoke.prs.jsonl.gz")
    r.add_argument("--seed", type=int, default=None, help="override run.seed")
    r.add_argument("--days", type=float, default=None, help="override run.days")
    e = sub.add_parser("experiment", help="run the M46 evaluation protocol and write results/*.json")
    e.add_argument("--preset", default="golden", help="configs/experiments/<preset>.yaml")
    e.add_argument("--config", default=None, help="explicit experiment YAML (overrides --preset)")
    e.add_argument("--pipelines", default=None, help="comma list, e.g. P0,P1 (default from the preset)")
    e.add_argument("--seeds", default=None, type=_seed_list, help="comma list, e.g. 11,22,33 (default from the preset)")
    e.add_argument("--out", default="results", help="output directory")
    e.add_argument("--jobs", type=_positive_int, default=1, help="seeds run in parallel processes")
    g = sub.add_parser("energy", help="M41–M43 energy comparison (MQ-2 against BME688) → results/energy.json")
    g.add_argument("--config", default="configs/default.yaml", help="configuration to read the energy parameters from")
    g.add_argument("--out", default="results", help="output directory")
    args = ap.parse_args(argv)
    try:
        return _dispatch(args)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"file error: {exc.strerror or exc}{f': {exc.filename}' if exc.filename else ''}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("interrupted — nothing was written for the unfinished run", file=sys.stderr)
        return 130


def _dispatch(args) -> int:
    if args.cmd == "experiment":
        return experiment(args)
    if args.cmd == "energy":
        return energy(args)
    s = run(args.config, args.out, args.seed, args.days)
    degraded = [k for k, v in s["modules"].items() if v["state"] == "degraded"]
    print(f"wrote {s['recording']}: {s['frames']} frames, {s['traces']} traces in {s['seconds']} s"
          + (f"; DEGRADED: {', '.join(degraded)}" if degraded else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
