"""Paper figures the rounds do not already draw, built only from committed result files and the configuration
(charter rule 4): `paper_strategies` (SIM, R2: where each common-mode strategy breaks) and `paper_realdata` (REAL:
node calibration and event rates on public networks). Same palette as the round figures; colour follows the method.
Needs the optional `paper` extra (matplotlib)."""
from __future__ import annotations

import json
from pathlib import Path

from prahari.cli import REPO
from prahari.core.config import load_config
from prahari.research.figures import INK, MUTED, SERIES, _plt, _save
from prahari.research.figures_r2 import LABEL, STYLE

STRATEGIES = ["P2", "P2-med", "P2-medSCMR", "P2-factor", "P2-gate", "AR"]
SCENARIOS = [("H-sync", "synchronous"), ("H-mix", "mixed"), ("H-gain", "uneven gain"), ("H-patch", "narrow patch"),
             ("H-mix-gauss", "mixed,\nGaussian plume")]
BASE = REPO / "configs" / "experiments" / "golden.yaml"


def _note(fig, lines) -> None:
    fig.text(0.01, 0.005, "\n".join(lines), fontsize=5, color=MUTED, ha="left", va="bottom", linespacing=1.3)


def fig_strategies(plt, r2: dict) -> list[str]:
    """SIM, protocol R2 — detection at equal false alarms (R8, 10 a month) of every valid method in every haze
    scenario. Mei and Mei-med are left out: their settings alarm continuously (DECISIONS R2-D1)."""
    fig, ax = plt.subplots(figsize=(3.5, 3.3))
    n = len(STRATEGIES)
    for i, m in enumerate(STRATEGIES):
        c, ls = STYLE[m]
        xs, ys = [], []
        for k, (sc, _) in enumerate(SCENARIOS):
            v = r2["scenarios"][sc]["methods"][m]["det_at_equal_fa"]["10"]
            xs.append(k + (i - (n - 1) / 2) * 0.11)
            ys.append(v)
        mk = "s" if m == "AR" else "o"
        ax.plot(xs, ys, ls="none", marker=mk, ms=3.6, color=c, mec="white", mew=0.5, label=LABEL[m])
    ax.set_xticks(range(len(SCENARIOS)), [lab for _, lab in SCENARIOS], fontsize=6)
    ax.set_xlim(-0.5, len(SCENARIOS) - 0.5)
    ax.set_ylim(0, 1)
    ax.set_ylabel("fires confirmed within 3 h")
    ax.grid(axis="x", visible=False)
    ax.legend(fontsize=5.2, loc="lower left", ncol=2, handletextpad=0.3, columnspacing=0.8)
    fig.subplots_adjust(left=0.15, bottom=0.33, right=0.98, top=0.97)
    seeds = {sc: r2["scenarios"][sc]["seeds"] for sc, _ in SCENARIOS}
    hm = seeds["H-mix"]
    others = sorted(s for sc, v in seeds.items() if sc != "H-mix" for s in v)
    _note(fig, [f"SIMULATION · PRAHARI-SIM, protocol R2 · H-mix seeds {hm[0]}–{hm[-1]} ({len(hm)});",
                f"other scenarios {len(seeds['H-sync'])} seeds each ({others[0]}–{others[-1]})",
                "detection at equal false alarms (R8), 10 false incidents a month, on each",
                "scenario's own curve · Mei and Mei-med omitted: invalid (DECISIONS R2-D1)"])
    return _save(fig, "paper_strategies")


def fig_realdata(plt, n5: dict, st: dict, india: dict) -> list[str]:
    """REAL — (a) node candidates per node per 30 d against the node layer's target; (b) network-wide common-mode
    events per day against the simulator's H-mix rate and R4's ×0.3 dose point (both from the configuration)."""
    cfg = load_config(BASE)
    target = float(cfg["params"]["cusum"]["target_per_node_30d"])
    h = cfg["params"]["haze"]
    hmix = float(h["base_rate_per_10d"]) * float(h["crop_burning_multiplier"]) / 10.0
    c0 = SERIES[0]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 3.0))
    node = [("N5 BC", n5["clusters"]["BC"], False), ("N5 VC", n5["clusters"]["VC"], False),
            ("N5 RC", n5["clusters"]["RC"], False), ("Stuttgart", st["cluster"], False),
            ("Delhi DL15", india["clusters"]["DL15-2025"], False), ("N5 WR", n5["clusters"]["WR"], True)]
    for i, (lab, c, special) in enumerate(node):
        v = c["node_replay"]["candidates_per_node_30d"]
        a1.bar(i, v, color=c0, alpha=0.45 if special else 1.0, hatch="////" if special else None, edgecolor="white",
               linewidth=0.8, width=0.62)
        a1.text(i, v + 0.12, f"{v:.2f}", ha="center", va="bottom", fontsize=5.5, color=INK)
    a1.axhline(target, color=MUTED, lw=0.7, ls=(0, (3, 3)))
    a1.text(len(node) - 0.55, target + 0.12, "target", fontsize=5.5, color=MUTED, ha="right", va="bottom")
    a1.set_xticks(range(len(node)), [lab for lab, _, _ in node], fontsize=6)
    a1.set_ylabel("candidates per node per 30 d")
    a1.grid(axis="x", visible=False)
    ev = [("N5 BC", n5["clusters"]["BC"]["events_per_day"], False), ("N5 VC", n5["clusters"]["VC"]["events_per_day"], False),
          ("N5 RC", n5["clusters"]["RC"]["events_per_day"], False), ("N5 WR", n5["clusters"]["WR"]["events_per_day"], True),
          ("Stuttgart", st["cluster"]["events_per_day"], True)]
    ev += [(f"India {k}", v["events_per_day"], False) for k, v in india["pooled"].items()]
    for i, (lab, v, special) in enumerate(ev):
        a2.bar(i, v, color=c0, alpha=0.45 if special else 1.0, hatch="////" if special else None, edgecolor="white",
               linewidth=0.8, width=0.62)
        a2.text(i, v + 0.004, f"{v:.3f}", ha="center", va="bottom", fontsize=5.2, color=INK, zorder=4,
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.4})          # reference lines pass behind
    for y, lab, ls in ((hmix, "simulator H-mix rate (×1)", (0, (3, 3))), (0.3 * hmix, "R4 dose point (×0.3)", ":")):
        a2.axhline(y, color=MUTED, lw=0.7, ls=ls, label=lab)
    a2.set_ylim(0, 1.35 * max(v for _, v, _ in ev))                              # headroom: the legend clears the bars
    a2.legend(fontsize=5.5, loc="upper right")
    a2.set_xticks(range(len(ev)), [lab for lab, _, _ in ev], fontsize=5.6, rotation=30, ha="right")
    a2.set_ylabel("network-wide events per day")
    a2.grid(axis="x", visible=False)
    for ax, t in ((a1, "(a)"), (a2, "(b)")):
        ax.text(0.01, 0.98, t, transform=ax.transAxes, fontsize=7, color=INK, va="top")
    fig.subplots_adjust(left=0.07, bottom=0.36, right=0.99, top=0.97, wspace=0.22)
    _note(fig, ["REAL · N5: Thompson et al. 2026 (MIT), April 2024 · Stuttgart: Sensor.Community (ODbL 1.0), October 2024",
                "NW India, October–November, pooled per cluster: Aakash (CC BY-NC-ND 4.0) 2022–2024, Princeton CPCB "
                "(CC BY 4.0) 2017–2019, CPCB via OpenAQ (no licence listed) 2025",
                "hatched: N5 WR (near recorded fires) and Stuttgart (urban PM) · the target and the simulator rates "
                "come from the configuration"])
    return _save(fig, "paper_realdata")


def write_figures_paper(out: Path) -> list[str]:
    load = lambda n: json.loads((Path(out) / n).read_text(encoding="utf-8"))     # noqa: E731
    plt = _plt()
    paths = fig_strategies(plt, load("r2_analysis.json"))
    paths += fig_realdata(plt, load("real_thompson2026.json"), load("real_sensorcommunity_stuttgart.json"),
                          load("real_india.json"))
    plt.close("all")
    return paths
