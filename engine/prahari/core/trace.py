"""Evidence trace records (SPEC §4.7, P9).

Every candidate and every edge decision writes a record holding every
intermediate value. The explanation is filled from a template, never free text.
"""
from __future__ import annotations

EXPLANATION = ("{n} node(s) {nodes} raised candidates within {window} min; "
               "SCMR ratio {ratio} ({scmr}); {combine} p {p_cluster:.2g} across {n} node(s); {rule} "
               "(prior odds {odds:.2g}, {day}; {quorum} agreeing node(s) needed).")
RULE_BAYES = "posterior odds {posterior:.2g} {verdict} the {threshold:.2g} threshold"
RULE_QUORUM = ("fixed quorum of {quorum} {verdict} (stub RAQ; posterior odds {posterior:.2g} "
               "against {threshold:.2g} shown for reference only)")


def candidate_record(t: int, node: int, p: float, G: float, h: float, health: float) -> dict:
    return {"trace_id": f"c-{node}-{t}", "t": t, "type": "candidate", "node": int(node),
            "p": float(p), "cusum": float(G), "h": float(h), "health": float(health)}


def decision_record(t: int, seq: int, level: str, members, p_nodes, G, h: float, health,
                    scmr: dict, fisher: dict, prior: dict, bayes: dict, window_min: int) -> dict:
    per_node = [{"node": int(i), "p_channels": [float(p)], "health": [float(health[i])],
                 "cusum": float(G[i]), "h": float(h)} for i, p in zip(members, p_nodes)]
    ratio = scmr["ratio"]
    rule = RULE_BAYES if bayes.get("method", "bayes") == "bayes" else RULE_QUORUM
    explanation = EXPLANATION.format(
        n=len(members), nodes=list(map(int, members)), window=window_min,
        ratio=f"{ratio:.3g}" if scmr.get("modelled", True) else "not modelled (stub)",
        scmr="pass" if scmr["pass"] else "fail",
        combine="Fisher" if fisher.get("method", "fisher") == "fisher" else "Bonferroni",
        p_cluster=fisher["p_cluster"],
        rule=rule.format(posterior=bayes["posterior_odds"], threshold=bayes["threshold"], quorum=bayes["quorum"],
                         verdict="met" if bayes["decision"] else "not met" if rule is RULE_QUORUM else "did not meet"),
        odds=prior["odds"], day=prior["day_type"].replace("_", ", "), quorum=bayes["quorum"])
    return {"trace_id": f"d-{t}-{seq}", "t": t, "type": "decision", "level": level,
            "cluster": [int(i) for i in members], "per_node": per_node,
            "scmr": scmr, "fisher": fisher, "prior": prior, "bayes": bayes,
            "explanation": explanation}
