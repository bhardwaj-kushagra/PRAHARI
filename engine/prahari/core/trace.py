"""Evidence trace records (SPEC §4.7, P9).

Every candidate and every edge decision writes a record holding every
intermediate value. The explanation is filled from a template, never free text.
"""
from __future__ import annotations

EXPLANATION = ("{n} node(s) {nodes} raised candidates within {window} min; "
               "SCMR ratio {ratio} ({scmr}); Fisher p {p_cluster:.2g} across {n} node(s); "
               "posterior odds {posterior:.2g} {verdict} the {threshold:.2g} threshold "
               "(prior odds {odds:.2g}, {day}; {quorum} agreeing node(s) needed).")


def candidate_record(t: int, node: int, p: float, G: float, h: float, health: float) -> dict:
    return {"trace_id": f"c-{node}-{t}", "t": t, "type": "candidate", "node": int(node),
            "p": float(p), "cusum": float(G), "h": float(h), "health": float(health)}


def decision_record(t: int, seq: int, level: str, members, p_nodes, G, h: float, health,
                    scmr: dict, fisher: dict, prior: dict, bayes: dict, window_min: int) -> dict:
    per_node = [{"node": int(i), "p_channels": [float(p)], "health": [float(health[i])],
                 "cusum": float(G[i]), "h": float(h)} for i, p in zip(members, p_nodes)]
    ratio = scmr["ratio"]
    explanation = EXPLANATION.format(
        n=len(members), nodes=list(map(int, members)), window=window_min,
        ratio=f"{ratio:.3g}" if scmr.get("modelled", True) else "not modelled (stub)",
        scmr="pass" if scmr["pass"] else "fail",
        p_cluster=fisher["p_cluster"], posterior=bayes["posterior_odds"],
        verdict="met" if bayes["decision"] else "did not meet", threshold=bayes["threshold"],
        odds=prior["odds"], day=prior["day_type"].replace("_", ", "), quorum=bayes["quorum"])
    return {"trace_id": f"d-{t}-{seq}", "t": t, "type": "decision", "level": level,
            "cluster": [int(i) for i in members], "per_node": per_node,
            "scmr": scmr, "fisher": fisher, "prior": prior, "bayes": bayes,
            "explanation": explanation}
