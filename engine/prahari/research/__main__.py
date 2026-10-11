"""`python -m prahari.research`: run protocol R1 (docs/research/protocol.md) and build its analysis and figures.

  run selection|test [--jobs N] [--seeds a,b]   per-seed operating curves → results/research/<stage>/seed<N>.json
  sweep [--jobs N] [--only ar_phi,haze]         sensitivity sweeps → results/research/sweeps/
  analyse                                       → results/research/r1_*.json
  figures                                       → docs/research/figures/
  realdata                                      → results/research/real_thompson2026.json (REAL, exploratory)
  hazesplit                                     → results/research/r1_haze_split.json (R2-10, descriptive)
  realdata-india                                → results/research/real_india.json (REAL, exploratory; addendum C)
  r2-run selection|test [--scenarios H-mix,..]  protocol R2 → results/research/r2/<stage>/<scenario>/seed<N>.json
  r2-analyse                                    → results/research/r2_*.json
  r2-figures                                    → docs/research/figures/r2_*
  r3-run selection|test [--scenarios H-mix,..]  protocol R3 → results/research/r3/<stage>/<scenario>/seed<N>.json
  r3-analyse                                    → results/research/r3_*.json
  r3-figures                                    → docs/research/figures/r3_*
  r4-run selection|test [--scenarios H-none,..] protocol R4 → results/research/r4/<stage>/<scenario>/seed<N>.json
  r4-analyse [--selection-only|--test-table]    → results/research/r4_selection.json (and r4_test/r4_analysis)
  r4-seeds-archive selection|test               → results/research/r4_seeds_<stage>.tar.gz (byte-reproducible)
  r4-figures                                    → docs/research/figures/r4_*
  paper                                         → docs/research/paper/ (T1–T3 tables, evidence map)
  paper-figures                                 → docs/research/figures/paper_* (strategies, real data)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from prahari.research.runner import DEFAULT_CONFIG, DEFAULT_OUT, load_r1, run_stage, run_sweeps


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m prahari.research", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["run", "sweep", "analyse", "figures", "realdata", "realdata-sc", "hazesplit",
                                        "numbers", "r2-run", "r2-analyse", "r2-figures", "realdata-india",
                                        "r3-run", "r3-analyse", "r3-figures", "r4-run", "r4-analyse",
                                        "r4-seeds-archive", "r4-figures", "paper", "paper-figures"])
    ap.add_argument("stage", nargs="?", choices=["selection", "test"])
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--seeds", default=None, help="comma list (default: the protocol's seeds)")
    ap.add_argument("--only", default=None, help="sweep names, comma list")
    ap.add_argument("--scenarios", default=None, help="R2 scenarios, comma list (default: every one with the stage)")
    ap.add_argument("--selection-only", action="store_true", help="r4-analyse: the selection file only")
    ap.add_argument("--test-table", action="store_true", help="r4-analyse: only the compact test table, no endpoint")
    a = ap.parse_args(argv)
    if a.command.startswith("r2-"):
        return _r2(a, ap)
    if a.command.startswith("r3-"):
        return _r3(a, ap)
    if a.command.startswith("r4-"):
        return _r4(a, ap)
    if a.command == "paper":
        from prahari.research.paper import write_paper
        print(f"{len(write_paper())} files")
        return 0
    if a.command == "paper-figures":
        from prahari.research.figures_paper import write_figures_paper
        print(f"{len(write_figures_paper(Path(a.out)))} files")
        return 0
    r1 = load_r1(a.config)
    seeds = [int(s) for s in a.seeds.split(",")] if a.seeds else None
    out = Path(a.out)
    if a.command == "run":
        if not a.stage:
            ap.error("run needs a stage: selection or test")
        done = run_stage(r1, a.stage, a.jobs, out, seeds)
    elif a.command == "sweep":
        done = run_sweeps(r1, a.jobs, out, a.only.split(",") if a.only else None, seeds)
    elif a.command == "analyse":
        from prahari.research.analysis import write_analysis
        done = write_analysis(r1, out)
    elif a.command == "numbers":
        from prahari.research.numbers import write_numbers
        done = write_numbers(out)
    elif a.command == "realdata-india":
        from prahari.research.realdata_india import write_realdata_india
        done = write_realdata_india(out)
    elif a.command == "realdata-sc":
        from prahari.research.realdata_sc import write_realdata_sc
        done = write_realdata_sc(out)
    elif a.command == "hazesplit":
        from prahari.research.hazesplit_report import write_haze_split
        done = write_haze_split(out)
    elif a.command == "realdata":
        from prahari.research.realdata_report import write_realdata
        done = write_realdata(out)
    else:
        from prahari.research.figures import write_figures
        done = write_figures(out)
    print(f"{len(done)} files")
    return 0


def _r2(a, ap) -> int:
    from prahari.research.runner_r2 import load_r2, run_r2
    r2 = load_r2(a.config if a.config != str(DEFAULT_CONFIG) else "configs/research/r2.yaml")
    out = Path(a.out)
    if a.command == "r2-run":
        if not a.stage:
            ap.error("r2-run needs a stage: selection or test")
        seeds = [int(s) for s in a.seeds.split(",")] if a.seeds else None
        done = run_r2(r2, a.stage, a.scenarios.split(",") if a.scenarios else None, a.jobs, out, seeds)
    elif a.command == "r2-analyse":
        from prahari.research.analysis_r2 import write_analysis_r2
        done = write_analysis_r2(r2, out)
    else:
        from prahari.research.figures_r2 import write_figures_r2
        done = write_figures_r2(out)
    print(f"{len(done)} files")
    return 0


def _r3(a, ap) -> int:
    from prahari.research.runner_r2 import load_r2, run_r2
    r3 = load_r2(a.config if a.config != str(DEFAULT_CONFIG) else "configs/research/r3.yaml")
    out = Path(a.out)
    if a.command == "r3-run":
        if not a.stage:
            ap.error("r3-run needs a stage: selection or test")
        seeds = [int(s) for s in a.seeds.split(",")] if a.seeds else None
        done = run_r2(r3, a.stage, a.scenarios.split(",") if a.scenarios else None, a.jobs, out, seeds)
    elif a.command == "r3-analyse":
        from prahari.research.analysis_r3 import write_analysis_r3
        done = write_analysis_r3(r3, out)
    else:
        from prahari.research.figures_r2 import write_figures_r2
        done = write_figures_r2(out, "r3_analysis.json")
    print(f"{len(done)} files")
    return 0


def _r4(a, ap) -> int:
    from prahari.research.runner_r2 import load_r2, run_r2
    r4 = load_r2(a.config if a.config != str(DEFAULT_CONFIG) else "configs/research/r4.yaml")
    out = Path(a.out)
    if a.command == "r4-run":
        if not a.stage:
            ap.error("r4-run needs a stage: selection or test")
        seeds = [int(s) for s in a.seeds.split(",")] if a.seeds else None
        done = run_r2(r4, a.stage, a.scenarios.split(",") if a.scenarios else None, a.jobs, out, seeds)
    elif a.command == "r4-analyse":
        from prahari.research.analysis_r4 import write_analysis_r4, write_test_table_r4
        done = write_test_table_r4(r4, out) if a.test_table else write_analysis_r4(r4, out, a.selection_only)
    elif a.command == "r4-figures":
        from prahari.research.figures_r4 import write_figures_r4
        done = write_figures_r4(out)
    else:
        if not a.stage:
            ap.error("r4-seeds-archive needs a stage: selection or test")
        from prahari.research.archive import archive_seeds
        done = [str(archive_seeds(out, r4.get("round", "r4"), a.stage))]
    print(f"{len(done)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
