"""`python -m prahari.research`: run protocol R1 (docs/research/protocol.md) and build its analysis and figures.

  run selection|test [--jobs N] [--seeds a,b]   per-seed operating curves → results/research/<stage>/seed<N>.json
  sweep [--jobs N] [--only ar_phi,haze]         sensitivity sweeps → results/research/sweeps/
  analyse                                       → results/research/r1_*.json
  figures                                       → docs/research/figures/
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from prahari.research.runner import DEFAULT_CONFIG, DEFAULT_OUT, load_r1, run_stage, run_sweeps


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m prahari.research", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["run", "sweep", "analyse", "figures"])
    ap.add_argument("stage", nargs="?", choices=["selection", "test"])
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--seeds", default=None, help="comma list (default: the protocol's seeds)")
    ap.add_argument("--only", default=None, help="sweep names, comma list")
    a = ap.parse_args(argv)
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
    else:
        from prahari.research.figures import write_figures
        done = write_figures(out)
    print(f"{len(done)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
