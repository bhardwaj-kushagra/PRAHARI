"""Paper package (charter rule 10: the agent supplies tables, numbers, figures and outlines; the authors write the
prose). Generated from committed files only and written to docs/research/paper/ by `python -m prahari.research paper`:

- T1 — model parameters with their provenance (inputs: the golden configuration and R2's M20b block, not results);
- T2 — every registered confirmatory comparison of R1–R4 (from the round analyses), whatever its outcome;
- T3 — the real-data summary (REAL);
- the evidence map — per contribution of docs/research/direction.md, its status, headline numbers and caveats.

Tables are written as Markdown and as LaTeX (booktabs, ASCII only). No prose paragraphs are produced."""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from prahari.cli import REPO
from prahari.core.config import load_config
from prahari.record.writer import write_text_atomic

OUT_DIR = REPO / "docs" / "research" / "paper"
RESULTS = REPO / "results" / "research"
BASE = REPO / "configs" / "experiments" / "golden.yaml"
NAMES = {"P0": "P0 fixed threshold", "P1": "P1 v1 as written", "P1t": "P1t v1 replay-tuned", "AR": "AR(1) residual chart",
         "P2": "P2 (SCMR)", "P2-SCMR": "P2 without SCMR", "P2-Q2": "P2, fixed quorum 2", "P2-Q3": "P2, fixed quorum 3",
         "P2-med": "median subtraction", "P2-QCC": "P2, Gaussian z (no QCC)", "P2-TTC": "P2, slow z (no TTC)",
         "P2-medSCMR": "median + SCMR", "P2-factor": "one-factor reference", "P2-gate": "evidence gate",
         "Mei": "Mei (raw)", "Mei-med": "Mei (median)"}

# T1 — curated parameters of the effective (golden) configuration: (group, key, equation, meaning)
T1_PARAMS = [
    ("world", "n_nodes", "—", "nodes"), ("world", "spacing_m", "—", "grid spacing (m)"),
    ("world", "radius_factor", "M30", "neighbourhood radius R / spacing"),
    ("sensor", "ar_phi", "M19", "noise memory φ"), ("sensor", "sigma_e", "M19", "noise level σ (su)"),
    ("sensor", "het_extra", "M19", "daytime noise factor"), ("sensor", "drift_step_sd", "M18", "drift per minute (su)"),
    ("sensor", "tail_df", "M18", "heavy-tail degrees of freedom"),
    ("nuisance", "rate_roadside_per_day", "M20", "roadside nuisance events per day"),
    ("nuisance", "rate_other_per_day", "M20", "other nuisance events per day"),
    ("haze", "base_rate_per_10d", "M20", "haze episodes per 10 days"),
    ("haze", "duration_range", "M20", "episode duration (min)"), ("haze", "amp_range", "M20", "episode amplitude (su)"),
    ("ttc", "slow_tau_min", "M24", "slow baseline time constant (min)"), ("ttc", "freeze_z", "M24", "freeze threshold"),
    ("qcc", "bins", "M26", "conformal time-of-day bins"), ("qcc", "cal_days", "M26", "calibration days"),
    ("cusum", "k_node", "M28", "CUSUM reference value (−ln p scale)"),
    ("cusum", "target_per_node_30d", "M28", "default node target r (per node per 30 d)"),
    ("cusum", "cm_frac", "M28", "common-mode share of nodes"), ("cluster", "window_min", "M30", "cluster window W (min)"),
    ("scmr", "ratio_min", "M31", "default SCMR ratio ρ (R2–R4: a knob)"),
]
TAGS = ("LIT", "VEN", "DER", "ASM", "TGT", "DATA")
_TAGGED = re.compile(r"^\s+([A-Za-z_][\w]*):\s*(.+?)\s+#\s*(" + "|".join(TAGS) + r")\b\s*[—–-]?\s*(.*)$")


def parse_tagged_block(text: str, block: str) -> list[tuple]:
    """The `key: value  # TAG — note` lines of a top-level YAML block, as (key, value text, tag, note)."""
    out, inside = [], False
    for line in text.splitlines():
        if re.match(r"^\S", line):
            inside = line.startswith(f"{block}:")
            continue
        if inside:
            m = _TAGGED.match(line)
            if m:
                out.append((m.group(1), m.group(2).strip(), m.group(3), m.group(4).strip()))
    return out


def _fmt_value(v) -> str:
    if isinstance(v, list):
        return "[" + ", ".join(_fmt_value(x) for x in v) + "]"
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def t1_rows(base: Path, r2_yaml: Path) -> list[list[str]]:
    """T1 — curated parameters of the golden configuration with the group's `source` string, then the M20b haze
    keys of protocol R2 with their own inline provenance tags."""
    cfg = load_config(base)
    rows = []
    for group, key, eq, meaning in T1_PARAMS:
        sect = cfg["world"] if group == "world" else cfg["params"][group]
        src = (cfg["world"].get("source") if group == "world" else sect.get("source")) or "—"
        rows.append([eq, meaning, f"{group}.{key}", _fmt_value(sect[key]), src])
    for key, val, tag, note in parse_tagged_block(r2_yaml.read_text(encoding="utf-8"), "m20b"):
        rows.append(["M20b", key.replace("_", " "), f"m20b.{key}", val, f"{tag}; {note}" if note else tag])
    return rows


def _pts(v: float) -> str:
    return f"{100 * v:+.1f}"


def _ci_pts(c) -> str:
    return f"{100 * c[0]:+.1f} to {100 * c[1]:+.1f}"


def _row_cmp(rnd, family, comparison, budget, c, unit="points", note="") -> list[str]:
    if not c.get("reachable", True):
        return [rnd, family, comparison, budget, "not reachable", "—", "—", note]
    if unit == "points":
        est = f"{_pts(c['mean_diff'])} points ({_ci_pts(c['ci95'])})"
    else:
        est = f"{c['mean_diff']:+.2f} {unit} ({c['ci95'][0]:+.2f} to {c['ci95'][1]:+.2f})"
    holm = f"{c['p_holm']:.2g}" if "p_holm" in c else "—"
    return [rnd, family, comparison, budget, est, holm, f"{c['wins']} / {c['losses']}", note]


def t2_rows(r1: dict, r2: dict, r3: dict, r4: dict) -> list[list[str]]:
    """T2 — every registered confirmatory comparison (difference, 95% seed-bootstrap CI, Holm p, seeds higher/lower)."""
    rows = []
    for b in ("1", "3", "10"):
        for fam, d in r1["comparisons"][b].items():
            if not any(c.get("reachable") for c in d.values()):         # a whole family unreachable: one row
                rows.append(["R1", f"family {fam}", "P2 − each of: " + "; ".join(NAMES.get(x, x) for x in d), f"{b}/month",
                             "not reachable", "—", "—", "P2 cannot reach this budget (its floor at ρ = 3)"])
                continue
            for x, c in d.items():
                rows.append(_row_cmp("R1", f"family {fam}", f"P2 − {NAMES.get(x, x)}", f"{b}/month", c,
                                     note="" if c.get("reachable") else "the baseline does not reach this budget"))
    h = r2["scenarios"]["H-mix"]["families"]
    for x, c in h["D"].items():
        note = "invalid: continuous alarming (DECISIONS R2-D1)" if x.startswith("Mei") else ""
        rows.append(_row_cmp("R2", "family D", f"{NAMES.get(x, x)} − P2", f"B* = {r2['b_star']}/month", c, note=note))
    for x, c in h["F"].items():
        rows.append(_row_cmp("R2", "family F", f"{NAMES.get(x, x)} − P2", "floor", c, unit="FA/month"))
    hh = r3["scenarios"]["H-mix"]["head_to_head"]
    rows.append(_row_cmp("R3", "H1", "median + SCMR − evidence gate", f"B* = {r3['b_star']}/month",
                         hh["H1_detection_at_b_star"]))
    rows.append(_row_cmp("R3", "H2", "median + SCMR − evidence gate", "floor", hh["H2_floor"], unit="FA/month"))
    for x, c in r4["family_P"].items():
        rows.append(_row_cmp("R4", "family P", f"{NAMES.get(x, x)}: no haze − H-mix haze",
                             f"{r4['primary_budget']}/month", c))
    return rows


def t3_rows(n5: dict, st: dict, india: dict) -> list[list[str]]:
    """T3 — per real network: source, stations, median spacing, event days, network-wide events per day (with the multiple
    of the simulator's H-mix rate where the result file gives it), node candidates per node per 30 d, exceedance at a
    nominal 1%, the share in common mode, and a note."""
    def node(c):
        nr = c.get("node_replay") or {}
        if nr.get("candidates_per_node_30d") is None:
            return ["—", "—", "—"]
        sh = nr.get("share_in_cm_mask")
        return [f"{nr['candidates_per_node_30d']:.2f}", f"{100 * nr['exceedance_outside_cm_at_1pct']:.1f}%",
                "—" if sh is None else f"{100 * sh:.1f}%"]

    notes = {"WR": "its one event is attributed to a fire; the candidates fall near recorded fires",
             "Stuttgart": "urban PM", "DL15": "15-minute cadence (node replay possible)"}
    rows = []
    for cl, c in n5["clusters"].items():
        rows.append([f"N5 {cl}", "Thompson et al. 2026 (MIT)", str(c["stations"]), f"{c['spacing_km']['median']:g}",
                     f"{c['days_with_share']:g}", f"{c['events_per_day']:.3f}"] + node(c) + [notes.get(cl, "")])
    c = st["cluster"]
    rows.append(["Stuttgart", "Sensor.Community (ODbL 1.0)", str(c["stations"]), f"{c['spacing_km']['median']:g}",
                 f"{c['days_with_share']:g}", f"{c['events_per_day']:.3f}"] + node(c) + [notes["Stuttgart"]])
    lic = {"AK": "Aakash, RIHN (CC BY-NC-ND 4.0)", "DL": "Princeton CPCB (CC BY 4.0)",
           "DL15": "CPCB via OpenAQ (no licence listed)"}
    for key, c in india["clusters"].items():
        if not c.get("analysed"):
            continue
        sp = c.get("spacing_km")
        h = c["held_out"]
        rows.append([f"NW India {key}", lic[key.split("-")[0]], str(c["stations"]),
                     "—" if not sp else f"{sp['median']:g}", f"{c['days_with_share']:g}",
                     f"{h['events_per_day']:.3f}" + ("" if h.get("rate_multiplier_vs_h_mix") is None
                                                     else f" (×{h['rate_multiplier_vs_h_mix']:g})")] + node(c)
                    + [notes.get(key.split("-")[0], "")])
    return rows


_TEX = {"×": r"$\times$", "≥": r"$\geq$", "≤": r"$\leq$", "−": r"$-$", "–": "--", "—": "---", "ρ": r"$\rho$",
        "θ": r"$\theta$", "φ": r"$\phi$", "σ": r"$\sigma$", "λ": r"$\lambda$", "Δ": r"$\Delta$", "≈": r"$\approx$",
        "²": r"$^2$", "…": r"\ldots{}", "§": r"\S{}", "’": "'", "“": "``", "”": "''", "→": r"$\to$",
        "·": r"$\cdot$", "±": r"$\pm$", "ε": r"$\varepsilon$", "μ": r"$\mu$", "α": r"$\alpha$"}
_TEX.update({chr(0x2080 + d): f"$_{d}$" for d in range(10)})                  # subscript digits (PM₂.₅)


_SPECIAL = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{",
            "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def tex_escape(s: str) -> str:
    """Plain text to ASCII LaTeX (booktabs tables), one character at a time; unknown non-ASCII characters are dropped,
    never passed through."""
    s = re.sub(r"(?<![\w.])-(?=\d)", "−", s)                                   # a signed number: a minus sign
    return "".join(_SPECIAL.get(ch) or _TEX.get(ch) or (ch if ord(ch) < 128 else "") for ch in s)


def md_table(header: list[str], rows: list[list[str]]) -> str:
    esc = lambda x: str(x).replace("|", "\\|")                                    # noqa: E731
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines += ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def tex_table(header: list[str], rows: list[list[str]], colspec: str, caption: str, label: str) -> str:
    lines = [r"% Generated by python -m prahari.research paper; do not edit.", r"\begin{table*}[t]", r"\centering",
             r"\footnotesize", rf"\caption{{{tex_escape(caption)}}}", rf"\label{{{label}}}",
             rf"\begin{{tabular}}{{{colspec}}}", r"\toprule", " & ".join(tex_escape(h) for h in header) + r" \\",
             r"\midrule"]
    lines += [" & ".join(tex_escape(str(c)) for c in r) + r" \\" for r in rows]
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    return "\n".join(lines) + "\n"


T1_HEAD = ["Eq.", "Meaning", "Key", "Value", "Provenance"]
T2_HEAD = ["Round", "Test", "Comparison", "Budget", "Difference (95% CI)", "Holm p", "Seeds higher / lower", "Note"]
T3_HEAD = ["Network", "Source (licence)", "Stations", "Median spacing (km)", "Event days", "Events per day (× H-mix)",
           "Node candidates / node / 30 d", "Exceedance at 1%", "Candidates in common mode", "Note"]


def _load(name: str) -> dict:
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def hmix_rate_per_day(base: Path) -> float:
    """The simulator's H-mix episode rate per day, from the configuration (M20 base rate × the crop multiplier)."""
    h = load_config(base)["params"]["haze"]
    return float(h["base_rate_per_10d"]) * float(h["crop_burning_multiplier"]) / 10.0


def write_tables(out: Path = OUT_DIR) -> list[str]:
    out = Path(out)
    t1 = t1_rows(BASE, REPO / "configs" / "research" / "r2.yaml")
    t2 = t2_rows(_load("r1_analysis.json"), _load("r2_analysis.json"), _load("r3_analysis.json"), _load("r4_analysis.json"))
    t3 = t3_rows(_load("real_thompson2026.json"), _load("real_sensorcommunity_stuttgart.json"), _load("real_india.json"))
    specs = {
        "T1_parameters": (T1_HEAD, t1, "llllp{6cm}", "Model parameters and their provenance (inputs, not results).",
                          "tab:parameters", "Source: `configs/experiments/golden.yaml` (with `configs/default.yaml`) "
                          "and the M20b block of `configs/research/r2.yaml`; provenance tags as in the charter."),
        "T2_main_results": (T2_HEAD, t2, "llp{4.2cm}lp{3.6cm}llp{3.2cm}",
                            "Every registered confirmatory comparison (SIM), whatever its outcome.", "tab:results",
                            "Source: `results/research/r1–r4_analysis.json`; detection differences in points, floors "
                            "in false incidents a month; 95% seed-bootstrap intervals; two-sided Wilcoxon, Holm within "
                            "each family."),
        "T3_real_data": (T3_HEAD, t3, "p{2.2cm}p{2.8cm}lllp{1.6cm}lllp{2.6cm}", "Real-data checks (REAL).",
                         "tab:realdata", "Source: `results/research/real_*.json`; the multiple of the simulator's H-mix "
                         "rate where the result file gives it; node replay only where the cadence allows it, over its own test "
                         "days (`node_replay.test_days` in numbers.md)."),
    }
    paths = []
    (out / "tables").mkdir(parents=True, exist_ok=True)
    for name, (head, rows, colspec, caption, label, source) in specs.items():
        md = f"# {name.replace('_', ' ')}\n\n{caption} {source}\n\n" + md_table(head, rows)
        write_text_atomic(out / "tables" / f"{name}.md", md)
        write_text_atomic(out / "tables" / f"{name}.tex", tex_table(head, rows, colspec, caption, label))
        paths += [str(out / "tables" / f"{name}.md"), str(out / "tables" / f"{name}.tex")]
    return paths


def _rng(vals, fmt) -> str:
    vals = [v for v in vals if v is not None]
    lo, hi = fmt(min(vals)), fmt(max(vals))
    return lo if lo == hi else f"{lo}–{hi}"


def evidence_map() -> str:
    """The evidence map: per contribution of direction.md, its status, headline numbers (each with its numbers.md
    key), figures, tables and caveats; then claims to avoid and the open decisions. Bullet points only."""
    r1, r2, r3, r4 = (_load(f"r{i}_analysis.json") for i in (1, 2, 3, 4))
    sw, hs = _load("r1_sweeps.json"), _load("r1_haze_split.json")
    n5, st, ind = _load("real_thompson2026.json"), _load("real_sensorcommunity_stuttgart.json"), _load("real_india.json")
    pct = lambda v: f"{100 * v:.1f}%"                                           # noqa: E731
    c10 = r1["comparisons"]["10"]["A"]
    p1 = [v["pipelines"]["P1"]["fa_at_first_knob"] for v in sw["sweeps"].values() if "P1" in v["pipelines"]]
    plume = sw["sweeps"]["plume=real"]["pipelines"]["P2"]["10"]["det_at_equal_fa"]
    dflt = sw["sweeps"]["default"]["pipelines"]["P2"]["10"]["det_at_equal_fa"]

    def p2_floor_amoc(a):
        """P2's lowest rate over every scenario of a round (R2/R3), as the audit rows read it."""
        return [min(c["fa_per_month"] for c in s["methods"]["P2"]["amoc"]) for s in a["scenarios"].values()]
    floors = p2_floor_amoc(r2) + p2_floor_amoc(r3)
    shares = ([hs["split"]["P2"]["inside_share"][0]] +
              [s["methods"]["P2"]["floor_at_selected_knob"]["decomposition"]["share_inside"] for s in r2["scenarios"].values()] +
              [s["methods"]["P2"]["floor_at_selected_knob"]["decomposition"]["share_inside"] for s in r3["scenarios"].values()])
    fp = r4["family_P"]
    s4 = r4["scenarios"]
    uf0 = [s4["H-none"]["floors"][m]["useful_floor"] for m in r4["methods"]]
    uf1 = [s4["H-mix"]["floors"][m]["useful_floor"] for m in r4["methods"]]
    sel4 = r4["selection"]["H-mix"]["methods"]
    same_uf = all(sel4[m]["useful_floor"]["cell"] == sel4[m]["useful_floor_r_ge_0.1"]["cell"] for m in r4["methods"])
    none_uf = [s4["H-none"]["floors"][m][k]["false_incidents"]["rate"] for m in r4["methods"]
               for k in ("useful_floor", "useful_floor_r_ge_0.1")]
    grid4 = yaml.safe_load((REPO / "configs" / "research" / "r4.yaml").read_text(encoding="utf-8"))["grids"]["node"]
    strict = " and ".join(f"{v:g}" for v in grid4 if v < 0.1)
    hm = r2["scenarios"]["H-mix"]["methods"]
    fam = r2["scenarios"]["H-mix"]["families"]
    hh = r3["scenarios"]["H-mix"]["head_to_head"]
    md1 = s4["H-mix"]["method_differences"]["1"]
    quiet = [n5["clusters"][c]["node_replay"] for c in ("BC", "VC", "RC")]
    wr = n5["clusters"]["WR"]["node_replay"]
    dl15 = ind["clusters"]["DL15-2025"]["node_replay"]
    pooled = [v["rate_multiplier_vs_h_mix"] for v in ind["pooled"].values()]
    r1_floor = min(c["fa_per_month"] for c in r1["test"]["P2"]["curve"])
    target = load_config(BASE)["params"]["cusum"]["target_per_node_30d"]
    n_ev = ([c["n_events"] for c in n5["clusters"].values()] + [st["cluster"]["n_events"]]
            + [c["n_events"] for c in ind["clusters"].values() if c.get("analysed")])
    L = []
    w = L.append
    w("# Evidence map for the paper (generated; do not edit)")
    w("")
    w("Generated by `python -m prahari.research paper` from the committed result files; every number below is in")
    w("[numbers.md](../numbers.md) under the key shown in brackets. **SIM** = simulator output; **REAL** = public data.")
    w("Bullet points only: the authors write the paper's prose (charter rule 10). The claim and title are the")
    w("developer's decision and are not changed here; where the evidence supports a claim only in a revised form, the")
    w("map says so.")
    w("")
    w("## Contribution 1 — a pre-registered, equal-false-alarm evaluation on an open, deterministic testbed")
    w("")
    w("- **Status: supported** (method).")
    w("- Four registered rounds (R1–R4) and a registered real-data plan; protocol commits precede every result file;")
    w("  one seed per round regenerates byte for byte ([audit-2026-10-07.md](../audit-2026-10-07.md) §1).")
    w(f"- SIM, R1 family A at 10 false incidents a month: P2 confirms {pct(r1['test']['P2']['at_budget']['10']['det'])} "
      f"of fires within 3 h [`test.P2.at_budget.10.det`];")
    reach = [x for x in c10 if c10[x].get("reachable")]
    unreach = [NAMES.get(x, x) for x in c10 if not c10[x].get("reachable")]
    w(f"  differences {', '.join(_pts(c10[x]['mean_diff']) for x in reach)} points against "
      f"{', '.join(NAMES.get(x, x) for x in reach)}, Holm p ≤ {max(c10[x]['p_holm'] for x in reach):.2g}"
      + (f"; {', '.join(unreach)} cannot reach the budget" if unreach else "") + " [`comparisons.10.A.*`].")
    w(f"- SIM, the textbook ARL threshold: {min(p1):.1f}–{max(p1):.1f} false incidents a month at every sweep point "
      f"[`sweeps.<point>.pipelines.P1.fa_at_first_knob`].")
    w("- Figure: `f2_operating_curves`. Table: T2 (R1 rows).")
    w(f"- Caveat: absolute detection is plume-conditional (P2 at 10 a month: {pct(dflt)} with the legacy plume, "
      f"{pct(plume)} with the Gaussian plume, R1 sweep seeds) [`sweeps.plume=real.pipelines.P2`].")
    w("")
    w("## Contribution 2 — the decomposition: node calibration meets its budget; regional smoke sets the floor")
    w("")
    w("- **(a) Node calibration meets its budget — supported.**")
    w(f"  - REAL, quiet N5 networks: {_rng([q['candidates_per_node_30d'] for q in quiet], lambda v: f'{v:.2f}')} node "
      f"candidates per node per 30 d against a target of {target:g} (configuration); exceedance "
      f"{_rng([q['exceedance_outside_cm_at_1pct'] for q in quiet], pct)} at a nominal 1% [`clusters.<BC|VC|RC>.node_replay`].")
    w(f"  - REAL, Delhi smoke season (DL15, 15 min): {dl15['candidates_per_node_30d']:.2f} per node per 30 d; "
      f"{pct(dl15['share_in_cm_mask'])} of candidates in common mode [`clusters.DL15-2025.node_replay`].")
    w("- **(b) \"Regional smoke sets a floor that node thresholds cannot move\" — not supported as an unmovable floor;**")
    w("  **supported in a revised form.**")
    w(f"  - SIM: R1's floor ({r1_floor:.2f} a month [`test.P2.curve`]) belonged to SCMR's fixed ratio ρ = 3. With ρ "
      f"free, P2's lowest rate is {_rng(floors, lambda v: f'{v:.2f}')} a month across R2 and R3 [audit rows \"lowest "
      f"false incidents/month at ρ = 3 vs at any ρ\"].")
    w(f"  - SIM: what remains is smoke: {_rng(shares, pct)} of P2's floor incidents start inside haze (R1–R3) "
      f"[`split.P2.inside_share`, `…floor_at_selected_knob.decomposition.share_inside`].")
    w(f"  - SIM, R4 family P (confirmatory): at 1 false incident a month, detection without haze minus with haze is "
      f"{', '.join(_pts(fp[m]['mean_diff']) for m in r4['methods'])} points (P2, median + SCMR, gate), Holm p ≤ "
      f"{max(fp[m]['p_holm'] for m in r4['methods']):.2g} [`family_P[*]`].")
    w(f"  - SIM, R4: useful floors {_rng([u['false_incidents']['rate'] for u in uf0], lambda v: f'{v:.2f}')} a month "
      f"without haze against {_rng([u['false_incidents']['rate'] for u in uf1], lambda v: f'{v:.2f}')} with haze "
      f"[`scenarios[*].floors[*]`].")
    w(f"  - SIM, R4: with haze, the stricter node targets ({strict}) "
      f"{'leave every useful-floor setting unchanged' if same_uf else 'change at least one useful-floor setting'}; "
      f"without haze, the useful floors are {_rng(none_uf, lambda v: f'{v:.2f}')} a month with or without them "
      f"[`selection.H-mix.methods.*[useful_floor*]`, `scenarios[H-none].floors[*][useful_floor*]`].")
    w("  - Candidate revised claim, for the developer to decide and the authors to word: smoke sets the detection")
    w("    price of strict false-alarm budgets, and stricter node thresholds did not lower the useful floor with haze (R4).")
    w("- Figures: `r4_price`, `r4_dose`, `r4_floors`, `paper_realdata` (a). Tables: T2 (R4 rows), T3.")
    w("- Caveats: SIM; H-mix's haze rate is a stress setting next to the real rates (contribution 4); SCMR's ratio")
    w("  cannot exceed N divided by the neighbourhood size (100/9 for interior clusters, DER), so floors are conditional")
    w("  on the network geometry.")
    w("")
    w("## Contribution 3 — common-mode strategies under synchronous and uneven haze, and where each breaks")
    w("")
    w("- **Status: supported.**")
    w(f"  - SIM, R1 (synchronous haze): median subtraction confirms {pct(r1['test']['P2-med']['at_budget']['10']['det'])} "
      f"at 10 a month, {_pts(-r1['comparisons']['10']['B']['P2-med']['mean_diff'])} points over P2 at ρ = 3 "
      f"[`test.P2-med.at_budget.10.det`, `comparisons.10.B.P2-med`].")
    w(f"  - SIM, R2 (uneven haze): median subtraction fails — floor "
      f"{hm['P2-med']['floor_at_selected_knob']['false_incidents']['rate']:.2f} a month, "
      f"{pct(hm['P2-med']['at_b_star']['det'])} at B* = {r2['b_star']} (family D {_pts(fam['D']['P2-med']['mean_diff'])} "
      f"points, Holm p {fam['D']['P2-med']['p_holm']:.2g}) [`scenarios.H-mix.methods.P2-med`, `…families.D.P2-med`].")
    best = max((m for m in hm if not m.startswith("Mei")), key=lambda m: hm[m]["at_b_star"]["det"])
    w(f"  - SIM, R2: among the valid methods, {NAMES.get(best, best)} detects most at B* "
      f"({pct(hm[best]['at_b_star']['det'])}); median + SCMR − P2 {_pts(fam['D']['P2-medSCMR']['mean_diff'])} points "
      f"(Holm p {fam['D']['P2-medSCMR']['p_holm']:.2g}); the gate has "
      f"the lowest floor ({hm['P2-gate']['floor_at_selected_knob']['false_incidents']['rate']:.2f} a month; family F "
      f"{fam['F']['P2-gate']['mean_diff']:+.2f} a month) at a near-silent setting "
      f"({pct(hm['P2-gate']['floor_at_selected_knob']['det'])} detection); Mei's network sum cannot hold any budget "
      f"(R2-D1).")
    w(f"  - SIM, R3 (head to head, B* = {r3['b_star']}): H1 {_pts(hh['H1_detection_at_b_star']['mean_diff'])} points "
      f"(median + SCMR − gate, Holm p {hh['H1_detection_at_b_star']['p_holm']:.2g}); H2 "
      f"{hh['H2_floor']['mean_diff']:+.2f} false incidents a month (Holm p {hh['H2_floor']['p_holm']:.2g}); the ranking "
      f"changes with the budget [`scenarios.H-mix.head_to_head`].")
    w(f"  - SIM, R4 (descriptive): with haze at 1 a month, P2 − median + SCMR "
      f"{_pts(md1['P2 − P2-medSCMR']['mean_diff'])} points and P2 − gate {_pts(md1['P2 − P2-gate']['mean_diff'])} "
      f"points; R3's H1 is not repeated (median + SCMR − gate {_pts(md1['P2-medSCMR − P2-gate']['mean_diff'])} points, "
      f"p {md1['P2-medSCMR − P2-gate']['p_wilcoxon']:.2g}) [`scenarios[H-mix].method_differences[1]`].")
    w("- Figures: `paper_strategies`, `r2_floor_H-mix`. Table: T2 (R2, R3 rows).")
    w("- Caveats: which haze scenario is realistic for a MOX network is open (real events are mostly more even than M20b);")
    w("  at ρ = 10, SCMR confirms an interior cluster only while the rest of the network is quiet.")
    w("")
    w("## Contribution 4 — real-data checks of common-mode events and of the node layer's quiet false-alarm rate")
    w("")
    w("- **Status: supported for the premises; the floor's size cannot be measured on real data.**")
    w(f"  - REAL: node calibration as in contribution 2 (a); near recorded fires (N5 WR) the node layer raised "
      f"{wr['candidates_per_node_30d']:.2f} candidates per node per 30 d, {pct(wr['share_in_cm_mask'])} of them in common "
      f"mode — at kilometre spacing a fire's own smoke looks common-mode [`clusters.WR.node_replay`].")
    w(f"  - REAL, NW India: network-wide events are rarer than the simulator's H-mix rate (pooled per cluster: "
      f"×{min(pooled):.2f}–×{max(pooled):.2f}) and mostly more even across stations than M20b's draws "
      f"[`pooled.*`, `clusters.*.held_out`].")
    w(f"  - REAL: Stuttgart (urban PM, {st['cluster']['stations']} sensors): {st['cluster']['events_per_day']:.3f} "
      f"events per day [`cluster.events_per_day`].")
    w("- Figure: `paper_realdata`. Table: T3.")
    w(f"- Caveats: PM₂.₅ and CO, not MOX; kilometre to regional spacing; {min(n_ev)}–{max(n_ev)} events per network or "
      f"cluster-year (descriptive only) [`clusters.*.n_events`, `cluster.n_events`, `clusters.*.held_out`]; DL15's")
    w("  licence is not listed by OpenAQ (the developer's decision, DECISIONS P-9); Aakash data are CC BY-NC-ND (no")
    w("  redistribution).")
    w("")
    w("## Claims to avoid")
    w("")
    w("- \"First\" or \"no one else\", unless the authors verify it against the literature.")
    w("- \"N× fewer false alarms\" at unequal detection; every comparison here is at equal false alarms.")
    w("- Field performance, real-world lead time, or a conformal guarantee under autocorrelation.")
    w(f"- An unmovable floor (the title's strong form): with ρ free, P2's floor is {_rng(floors, lambda v: f'{v:.2f}')} a"
      f" month (contribution 2).")
    w("- R3's H1 as a general advantage of the gate: R4 does not repeat it.")
    w("- Mei's registered R2 advantage: it is the continuous-alarm artefact (R2-D1).")
    w("- That the risk-adaptive quorum beats a fixed quorum: in R1 it does not beat a fixed quorum of 3.")
    w("- Absolute detection independent of the plume model (contribution 1 caveat).")
    w("")
    w("## Open decisions")
    w("")
    w("- **The developer:** the claim and title (contribution 2 (b)); the venue; the release tag and DOI.")
    w("- **The authors:** the novelty check against the literature; every reference read before citing; the similarity")
    w("  check; the AI disclosure (IEEE policy).")
    w("")
    w("## Package contents")
    w("")
    w("- Tables: [T1](tables/T1_parameters.md), [T2](tables/T2_main_results.md), [T3](tables/T3_real_data.md) (each also")
    w("  as `.tex`, booktabs).")
    w("- Figures (in `../figures/`): `f2_operating_curves`, `r4_price`, `r4_dose`, `r4_floors`, `r2_floor_H-mix`,")
    w("  `paper_strategies`, `paper_realdata`.")
    w("- Outline: [outline.md](outline.md).")
    return "\n".join(L) + "\n"


def write_paper(out: Path = OUT_DIR) -> list[str]:
    out = Path(out)
    paths = write_tables(out)
    write_text_atomic(out / "evidence-map.md", evidence_map())
    return paths + [str(out / "evidence-map.md")]
