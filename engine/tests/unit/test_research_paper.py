"""Paper package (charter rule 10): the T1 provenance parser and rows, the T2/T3 row builders on synthetic analyses
(reference strings), the ASCII LaTeX escape, regeneration from the committed result files (byte-identical, and equal
to the committed package), and the two paper figures."""
from pathlib import Path

import pytest

from prahari.research import figures
from prahari.research.paper import (BASE, TAGS, hmix_rate_per_day, md_table, parse_tagged_block, t1_rows, t2_rows,
                                    t3_rows, tex_escape, tex_table, write_paper)

from ..conftest import REPO

YAML = """\
round: r2
m20b:
  gain_sd: 0.3                 # DATA — N5 amplitude CV
  gain_clip: [0.3, 2.0]        # ASM
  night_window: [1200, 480]    # DER - 20:00-08:00 local
  untagged: 5                  # a plain comment
grids:
  node: [0.1, 0.2]             # M28 — target r
"""


def test_parse_tagged_block_reference_values():
    assert parse_tagged_block(YAML, "m20b") == [("gain_sd", "0.3", "DATA", "N5 amplitude CV"),
                                                ("gain_clip", "[0.3, 2.0]", "ASM", ""),
                                                ("night_window", "[1200, 480]", "DER", "20:00-08:00 local")]
    assert parse_tagged_block(YAML, "grids") == []          # an equation id (M28) is not a provenance tag
    assert parse_tagged_block(YAML, "absent") == []


def test_t1_rows_carry_provenance():
    rows = t1_rows(BASE, REPO / "configs" / "research" / "r2.yaml")
    keys = {r[2]: r for r in rows}
    assert keys["scmr.ratio_min"][0] == "M31" and keys["scmr.ratio_min"][3] == "3"
    assert keys["world.n_nodes"][3] == "100" and keys["cusum.target_per_node_30d"][3] == "1"
    assert keys["m20b.gain_sd"][3:] == ["0.3", "DATA; N5 unattributed events, amplitude CV 0.25–0.34 "
                                                "(real_thompson2026.json)"]
    assert sum(r[0] == "M20b" for r in rows) == 14
    for r in rows:                                          # charter rule 6: every input has a source tag
        assert any(t in r[4].replace(";", " ").split() for t in TAGS), r


def test_hmix_rate_from_configuration():
    assert hmix_rate_per_day(BASE) == pytest.approx(0.1)


def _c(mean, lo, hi, p, wins, losses):
    return {"reachable": True, "mean_diff": mean, "ci95": [lo, hi], "p_holm": p, "wins": wins, "losses": losses}


def test_t2_rows_reference_strings():
    off = {"reachable": False}
    r1 = {"comparisons": {
        "1": {"A": {"P0": off, "AR": off}},
        "3": {"A": {"P0": off, "AR": off}},
        "10": {"A": {"P0": _c(0.368, 0.319, 0.417, 1.2e-15, 92, 7), "P1": off},
               "B": {"P2-med": _c(-0.088, -0.117, -0.062, 2.6e-12, 11, 75)}}}}
    r2 = {"b_star": 10, "scenarios": {"H-mix": {"families": {
        "D": {"P2-gate": _c(-0.015, -0.02, -0.009, 1.4e-5, 17, 58), "Mei": _c(0.096, 0.086, 0.106, 3.4e-17, 99, 0)},
        "F": {"P2-gate": _c(-0.40, -0.61, -0.19, 0.00044, 6, 34)}}}}}
    r3 = {"b_star": 1, "scenarios": {"H-mix": {"head_to_head": {
        "H1_detection_at_b_star": _c(-0.087, -0.148, -0.028, 0.012, 45, 54),
        "H2_floor": _c(0.45, 0.24, 0.67, 0.00028, 33, 6)}}}}
    r4 = {"primary_budget": 1, "family_P": {"P2": _c(0.221, 0.175, 0.27, 1.2e-17, 99, 0)}}
    unreach = "P2 cannot reach this budget (its floor at ρ = 3)"
    assert t2_rows(r1, r2, r3, r4) == [
        ["R1", "family A", "P2 − each of: P0 fixed threshold; AR(1) residual chart", "1/month", "not reachable", "—",
         "—", unreach],
        ["R1", "family A", "P2 − each of: P0 fixed threshold; AR(1) residual chart", "3/month", "not reachable", "—",
         "—", unreach],
        ["R1", "family A", "P2 − P0 fixed threshold", "10/month", "+36.8 points (+31.9 to +41.7)", "1.2e-15", "92 / 7",
         ""],
        ["R1", "family A", "P2 − P1 v1 as written", "10/month", "not reachable", "—", "—",
         "the baseline does not reach this budget"],
        ["R1", "family B", "P2 − median subtraction", "10/month", "-8.8 points (-11.7 to -6.2)", "2.6e-12", "11 / 75", ""],
        ["R2", "family D", "evidence gate − P2", "B* = 10/month", "-1.5 points (-2.0 to -0.9)", "1.4e-05", "17 / 58", ""],
        ["R2", "family D", "Mei (raw) − P2", "B* = 10/month", "+9.6 points (+8.6 to +10.6)", "3.4e-17", "99 / 0",
         "invalid: continuous alarming (DECISIONS R2-D1)"],
        ["R2", "family F", "evidence gate − P2", "floor", "-0.40 FA/month (-0.61 to -0.19)", "0.00044", "6 / 34", ""],
        ["R3", "H1", "median + SCMR − evidence gate", "B* = 1/month", "-8.7 points (-14.8 to -2.8)", "0.012", "45 / 54",
         ""],
        ["R3", "H2", "median + SCMR − evidence gate", "floor", "+0.45 FA/month (+0.24 to +0.67)", "0.00028", "33 / 6", ""],
        ["R4", "family P", "P2 (SCMR): no haze − H-mix haze", "1/month", "+22.1 points (+17.5 to +27.0)", "1.2e-17",
         "99 / 0", ""],
    ]


def test_t3_rows_reference_strings():
    nr = lambda c, e, s: {"candidates_per_node_30d": c, "exceedance_outside_cm_at_1pct": e, "share_in_cm_mask": s}  # noqa: E731
    n5 = {"clusters": {
        "WR": {"stations": 10, "spacing_km": {"median": 5.28}, "days_with_share": 30.0, "events_per_day": 0.0333,
               "node_replay": nr(6.38, 0.012, 0.706)},
        "RC": {"stations": 6, "spacing_km": {"median": 1.72}, "days_with_share": 19.25, "events_per_day": 0.052,
               "node_replay": nr(0.0, 0.011, None)}}}
    st = {"cluster": {"stations": 9, "spacing_km": {"median": 1.7}, "days_with_share": 31.0, "events_per_day": 0.2258,
                      "node_replay": nr(0.0, 0.013, None)}}
    india = {"clusters": {
        "AK-2022": {"analysed": True, "stations": 23, "spacing_km": {"median": 157.15}, "days_with_share": 61.0,
                    "held_out": {"events_per_day": 0.0, "rate_multiplier_vs_h_mix": None}},
        "DL-2017": {"analysed": False},
        "DL15-2025": {"analysed": True, "stations": 45, "spacing_km": None, "days_with_share": 57.24,
                      "held_out": {"events_per_day": 0.017, "rate_multiplier_vs_h_mix": 0.17},
                      "node_replay": nr(1.41, 0.016, 0.031)}}}
    assert t3_rows(n5, st, india) == [
        ["N5 WR", "Thompson et al. 2026 (MIT)", "10", "5.28", "30", "0.033", "6.38", "1.2%", "70.6%",
         "its one event is attributed to a fire; the candidates fall near recorded fires"],
        ["N5 RC", "Thompson et al. 2026 (MIT)", "6", "1.72", "19.25", "0.052", "0.00", "1.1%", "—", ""],
        ["Stuttgart", "Sensor.Community (ODbL 1.0)", "9", "1.7", "31", "0.226", "0.00", "1.3%", "—", "urban PM"],
        ["NW India AK-2022", "Aakash, RIHN (CC BY-NC-ND 4.0)", "23", "157.15", "61", "0.000", "—", "—", "—", ""],
        ["NW India DL15-2025", "CPCB via OpenAQ (no licence listed)", "45", "—", "57.24", "0.017 (×0.17)", "1.41",
         "1.6%", "3.1%", "15-minute cadence (node replay possible)"],
    ]


def test_tex_escape_is_ascii_and_maps_symbols():
    assert tex_escape("-3.1 points (-5.5 to -1.0); 1.2e-15; DL15-2025; replay-tuned") == \
        "$-$3.1 points ($-$5.5 to $-$1.0); 1.2e-15; DL15-2025; replay-tuned"
    assert tex_escape(r"a \ b {c} & 100% #1 $x ~ ^ _") == \
        r"a \textbackslash{} b \{c\} \& 100\% \#1 \$x \textasciitilde{} \textasciicircum{} \_"
    assert tex_escape("ρ ≥ 0.5 × 10 — PM₂.₅ é") == r"$\rho$ $\geq$ 0.5 $\times$ 10 --- PM$_2$.$_5$ "
    assert tex_escape("P2 − P0 · r1–r4") == r"P2 $-$ P0 $\cdot$ r1--r4"


def test_md_and_tex_tables():
    assert md_table(["a", "b"], [["x|y", 1]]) == "| a | b |\n| --- | --- |\n| x\\|y | 1 |\n"
    tex = tex_table(["Δ", "p"], [["−0.40 FA/month", "0.00044"]], "ll", "Caption — SIM", "tab:x")
    assert tex.isascii()
    assert r"$\Delta$ & p \\" in tex and r"$-$0.40 FA/month & 0.00044 \\" in tex
    assert [ln for ln in tex.splitlines() if ln.endswith("rule")] == [r"\toprule", r"\midrule", r"\bottomrule"]


def test_paper_package_regenerates_byte_identically(tmp_path):
    a, b = write_paper(tmp_path / "a"), write_paper(tmp_path / "b")
    names = [Path(p).relative_to(tmp_path / "a").as_posix() for p in a]
    assert names == [Path(p).relative_to(tmp_path / "b").as_posix() for p in b] and len(names) == 7
    committed = REPO / "docs" / "research" / "paper"
    for n in names:
        new = (tmp_path / "a" / n).read_bytes()
        assert new == (tmp_path / "b" / n).read_bytes(), n
        assert new == (committed / n).read_bytes(), f"{n} is stale: run python -m prahari.research paper"
        if n.endswith(".tex"):
            assert new.decode("utf-8").isascii(), n


def test_paper_figures_build_deterministically(tmp_path, monkeypatch):
    pytest.importorskip("matplotlib")
    from prahari.research.figures_paper import write_figures_paper

    out = []
    for run in ("a", "b"):
        monkeypatch.setattr(figures, "FIG_DIR", tmp_path / run)
        out.append(write_figures_paper(REPO / "results" / "research"))
    assert [Path(p).name for p in out[0]] == ["paper_strategies.pdf", "paper_strategies.png", "paper_realdata.pdf",
                                              "paper_realdata.png"]
    for p, q in zip(*out):
        data = open(p, "rb").read()
        assert data and data == open(q, "rb").read(), p
        if p.endswith(".pdf"):
            assert b"/CreationDate" not in data
