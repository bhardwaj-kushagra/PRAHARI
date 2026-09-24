"""Evidence-trace records carry every number and a template explanation that names the rule actually used."""
import numpy as np

from prahari.core.trace import decision_record

ARGS = dict(t=840, seq=1, level="CONFIRMED", members=(17, 18, 27), p_nodes=(6.9e-4,) * 3,
            G=np.full(30, 96.0), h=218.7, health=np.ones(30), window_min=30,
            scmr={"f_loc": 0.33, "f_net": 0.03, "ratio": 11.0, "pass": True},
            prior={"lambda": 3.1e-6, "p_s": 0.62, "odds": 1.9e-6, "day_type": "wet_quiet"})


def test_bayes_decision_explanation_matches_spec_example():
    # SPEC §4.7 (errata E-5): three nodes, Fisher p 8.6e-8, bound 2.6e5, posterior 0.50 >= 0.01
    rec = decision_record(**ARGS, fisher={"X": 43.7, "dof": 6, "p_cluster": 8.6e-8, "method": "fisher"},
                          bayes={"bf_bound": 2.6e5, "posterior_odds": 0.50, "threshold": 0.01, "quorum": 3,
                                 "decision": True, "method": "bayes"})
    assert rec["trace_id"] == "d-840-1" and rec["cluster"] == [17, 18, 27] and len(rec["per_node"]) == 3
    assert "Fisher p 8.6e-08" in rec["explanation"]
    assert "posterior odds 0.5 met the 0.01 threshold" in rec["explanation"]
    assert "SCMR ratio 11 (pass)" in rec["explanation"]


def test_stub_quorum_decision_does_not_claim_a_bayes_decision():
    rec = decision_record(**ARGS, fisher={"X": 0.0, "dof": 0, "p_cluster": 2e-3, "method": "bonferroni (stub)"},
                          bayes={"bf_bound": 20.0, "posterior_odds": 3.8e-5, "threshold": 0.01, "quorum": 2,
                                 "decision": True, "method": "fixed quorum (stub)"})
    e = rec["explanation"]
    assert "fixed quorum of 2 met (stub RAQ" in e and "shown for reference only" in e
    assert "Bonferroni p" in e and "met the 0.01 threshold" not in e
