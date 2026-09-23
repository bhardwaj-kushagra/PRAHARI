"""Command-line interface: `prahari run --config <scenario.yaml> --out <recording.prs.jsonl.gz>`."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from prahari.core.config import ConfigError, load_config
from prahari.core.pipeline import Simulation
from prahari.record.writer import RecordingWriter


def health_path(out: Path) -> Path:
    name = out.name.split(".prs")[0] if ".prs" in out.name else out.stem
    return out.with_name(f"{name}.health.json")


def run(config: str, out: str, seed: int | None = None, days: float | None = None) -> dict:
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
    health_path(Path(out)).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def experiment(args) -> int:
    from prahari.eval.experiments import run_experiment
    path = Path(args.config) if args.config else Path("configs") / "experiments" / f"{args.preset}.yaml"
    try:
        cfg = load_config(path)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2
    seeds = [int(v) for v in args.seeds.split(",")] if args.seeds else cfg["experiment"]["seeds"]
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


def energy(args) -> int:
    """Phase 8: M41–M43 energy comparison → results/energy.json, then rebuild results/summary.json."""
    from prahari.eval.energy_table import energy_table
    from prahari.eval.report import combine
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    table = energy_table(load_config(args.config))
    (out / "energy.json").write_text(json.dumps(table, indent=1), encoding="utf-8")
    combine(out)
    for r in table["rows"]:
        print(f"{r['sensor']} {r['mode']}: {r['wh_day']:.3f} Wh/day, {r['autonomy_days']:.1f} days on a full store — SIMULATION")
    print(f"harvest {table['harvest_wh_day']['clear']} Wh/day clear, {table['harvest_wh_day']['cloudy']} cloudy; "
          f"store {table['store_wh']} Wh; wrote {out}/energy.json")
    return 0


def main(argv: list[str] | None = None) -> int:
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
    e.add_argument("--seeds", default=None, help="comma list, e.g. 11,22,33 (default from the preset)")
    e.add_argument("--out", default="results", help="output directory")
    e.add_argument("--jobs", type=int, default=1, help="seeds run in parallel processes")
    g = sub.add_parser("energy", help="M41–M43 energy comparison (MQ-2 against BME688) → results/energy.json")
    g.add_argument("--config", default="configs/default.yaml", help="configuration to read the energy parameters from")
    g.add_argument("--out", default="results", help="output directory")
    args = ap.parse_args(argv)
    if args.cmd == "experiment":
        return experiment(args)
    if args.cmd == "energy":
        return energy(args)
    try:
        s = run(args.config, args.out, args.seed, args.days)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2
    degraded = [k for k, v in s["modules"].items() if v["state"] == "degraded"]
    print(f"wrote {s['recording']}: {s['frames']} frames, {s['traces']} traces in {s['seconds']} s"
          + (f"; DEGRADED: {', '.join(degraded)}" if degraded else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
