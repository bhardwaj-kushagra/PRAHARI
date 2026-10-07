"""Audit of 7 Oct 2026 (docs/research/audit-2026-10-07.md): the strict-grid-edge flag, the lowest-cell rule, and the
audit rows of the number table, on hand-made analyses with reference values."""
from prahari.research.numbers import _lowest, rows_audit, strict_edges
from prahari.research.runner_r2 import load_r2

GRIDS = load_r2()["grids"]


def test_strict_edges_reference_values():
    assert strict_edges("target×rho", [0.1, 10.0], GRIDS) == ["target = 0.1", "rho = 10"]
    assert strict_edges("target×rho", [0.3, 10.0], GRIDS) == ["rho = 10"]
    assert strict_edges("target×rho", [4.3, 6.0], GRIDS) == []
    assert strict_edges("target×theta", [0.2, 0.05], GRIDS) == ["theta = 0.05"]
    assert strict_edges("target×theta", [6.0, None], GRIDS) == []           # off is a natural end, not an edge
    assert strict_edges("target", 0.1, GRIDS) == ["target = 0.1"]
    assert strict_edges("h_M", 1500.0, GRIDS) == ["h_M = 1500"] and strict_edges("h_M", 20.0, GRIDS) == []


def test_lowest_cell_ties_as_floor_index():
    cells = [{"fa_per_month": 1.0, "det": 0.5}, {"fa_per_month": 0.5, "det": 0.2}, {"fa_per_month": 0.5, "det": 0.4},
             {"fa_per_month": 0.5, "det": 0.4}]
    assert _lowest(cells)[0] == 2                                            # lowest rate, then higher det, then first


def _analysis():
    amoc = [{"cell": [0.1, 3.0], "fa_per_month": 5.0, "det": 0.55}, {"cell": [0.1, 10.0], "fa_per_month": 0.5,
            "det": 0.54}, {"cell": [0.2, 3.0], "fa_per_month": 6.0, "det": 0.6}]
    fl = {"decomposition": {"share_inside": 0.9}}
    return {"scenarios": {"H-x": {"methods": {"P2": {"amoc": amoc, "floor_at_selected_knob": fl}}}},
            "selection": {"methods": {"P2": {"knob": "target×rho",
                                             "floor": {"cell": [0.1, 10.0]},
                                             "operating": {"1": {"cell": [0.3, 10.0]}, "10": {"cell": [4.3, 6.0]}}}}}}


def test_audit_rows_reference_values():
    sweeps = {"sweeps": {"default": {"pipelines": {"P1": {"fa_at_first_knob": 141.8}}},
                         "haze=0": {"pipelines": {"P1": {"fa_at_first_knob": 144.9},
                                                  "P2": {b: {"det_at_equal_fa": v} for b, v in
                                                         (("1", 0.901), ("3", 0.923), ("10", 0.954))}}}}}
    r1 = {"test": {"P0": {"curve": [{"knob": 20.0, "fa_per_month": 0.88, "det": 0.21},
                                    {"knob": 30.0, "fa_per_month": 0.13, "det": 0.0915}]}}}
    rows = rows_audit(sweeps, {"R9": ("r9.json", _analysis())}, GRIDS, r1)
    val = {q: v for q, v, _, _ in rows}
    assert val["Audit R1 P0: at its strictest knob (its floor), false incidents/month; detection"] == "0.13 at k = 30; 9.2%"
    assert val["Audit R1 sweeps: P1 at the textbook threshold (h = 8.8), false incidents/month, range over points"] \
        == "141.8–144.9 (2 points)"
    assert val["Audit R1 sweep haze=0 P2: detection at equal FA (R8; 0 = not reachable) at 1 / 3 / 10 per month"] \
        == "90.1% / 92.3% / 95.4%"
    k = "Audit R9 H-x P2: lowest false incidents/month at ρ = 3 (R1's fixed ratio) vs at any ρ"
    assert val[k] == "5.00 at [0.1, 3.0] (detection 55.0%) vs 0.50 at [0.1, 10.0] (detection 54.0%)"
    assert val["Audit R9 P2: share of floor incidents inside haze, range over scenarios"] == "90.0%–90.0% (H-x 90.0%)"
    assert val["Audit R9 selection P2: floor setting on a strict grid edge"] == "[0.1, 10.0]: target = 0.1, rho = 10"
    assert val["Audit R9 selection P2: operating 1/month setting on a strict grid edge"] == "[0.3, 10.0]: rho = 10"
    assert not any("operating 10/month" in q for q in val)                   # interior setting: no row
    keys = {q: key for q, _, _, key in rows}
    assert keys["Audit R9 selection P2: operating 1/month setting on a strict grid edge"] == "selection.methods.P2.operating.1"
