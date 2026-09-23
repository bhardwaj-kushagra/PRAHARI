"""The tick loop (SPEC §4.5): builds every stage from configuration and runs it through a Slot."""
from __future__ import annotations

import numpy as np

import prahari.stages  # noqa: F401 — registers every stage implementation
from prahari.core import contracts as C
from prahari.core import trace as tr
from prahari.core.clock import Clock
from prahari.core.context import RunContext
from prahari.core.rng import make_rngs
from prahari.core.runner import Slot, expect_len
from prahari.record import frames as fr
from prahari.record import world as rw
from prahari.world.geometry import neighbourhood_radius
from prahari.world.siting import check_layout_inside, world_grid

OUTPUT = {
    "weather": C.Weather, "ffmc": C.FuelState, "ignition": C.Fires, "growth": C.Sources,
    "plume": C.Concentration, "nuisance": C.Additive, "haze": C.Additive, "sensor": C.Readings,
    "faults": C.Readings, "ttc": C.Residuals, "qcc": C.PValues, "score": C.Scores,
    "cusum": C.Candidates, "comms": C.Delivered, "srp": C.Prior, "cluster": C.Clusters,
    "scmr": C.Scmr, "fisher": C.Fisher, "learn": C.BayesFactors, "raq": C.Raq,
    "escalate": C.Decision, "energy": C.EnergyState, "satellite": C.SatelliteAlerts,
}
# Setup modules run once before the first tick (Phase 1): landscape → siting → links.
SETUP = {"landscape": C.Landscape, "siting": C.Layout, "links": C.Links}


class Simulation:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        run, world = cfg["run"], cfg["world"]
        self.clock = Clock.from_run(run)
        try:
            xy = world_grid(world)                 # placeholder until the siting module runs in setup()
        except ValueError:
            xy = C.Layout.neutral(int(world["n_nodes"])).xy
        self.ctx = RunContext(clock=self.clock, xy=xy, spacing_m=float(world["spacing_m"]),
                              radius_m=neighbourhood_radius(world["spacing_m"], world["radius_factor"]),
                              gateways=list(world["gateways"]))
        rngs = make_rngs(int(run["seed"]))
        types = {**SETUP, **OUTPUT}
        missing = [m for m in types if m not in cfg["modules"]]
        if missing:
            raise ValueError(f"modules: missing states for {missing}")
        self.slots = {name: Slot(name, cfg["modules"][name], cfg["params"].get(name, {}), rngs.get(name), out)
                      for name, out in types.items()}
        self.landscape = self.layout = self.links = None
        n = self.ctx.n_nodes
        self._last_cand = np.full(n, -np.inf)
        self._last_conf = np.full(n, -np.inf)
        self._sat_done: set = set()
        self._seq = 0

    # -- helpers -----------------------------------------------------------
    def stage(self, name: str, inputs, check=None):
        return self.slots[name].run(inputs, self.ctx, check)

    def header(self) -> dict:
        cfg, xy = self.cfg, self.ctx.xy
        card = []
        for name, slot in self.slots.items():
            s = slot.chain[0]
            card.append({"model": name, "kind": s.kind, "equation": s.equation, "tag": s.tag,
                         "description": s.description, "version": s.version,
                         "source": cfg["params"].get(name, {}).get("source", "")})
        return {"schema": C.CONTRACT_VERSION, "label": "SIMULATION",
                "scenario": cfg["scenario"]["name"], "description": cfg["scenario"]["description"],
                "seed": int(cfg["run"]["seed"]), "start": cfg["run"]["start"], "days": float(cfg["run"]["days"]),
                "tick_minutes": self.clock.tick_minutes, "n_ticks": self.clock.n_ticks,
                "record_every": int(cfg["record"]["every_k_ticks"]),
                "map": {"width_m": float(cfg["world"]["width_m"]), "height_m": float(cfg["world"]["height_m"]),
                        "interfaces": rw.interfaces_list(cfg["world"]["interfaces"]),
                        "lambda_grid": rw.lambda_grid(self.landscape, cfg["record"]["lambda_cell_m"])},
                "layouts": rw.layouts_dict(self.layout),
                "links": rw.links_dict(self.links, self.ctx.gateways),
                "detection_radius_m": float(cfg["params"]["siting"]["detection_radius_m"]),
                "satellite_pixel_m": float(cfg["params"]["satellite"]["pixel_m"]),
                "spacing_m": self.ctx.spacing_m, "radius_m": self.ctx.radius_m,
                "nodes": [{"id": i, "x": float(x), "y": float(y), "type": "B"} for i, (x, y) in enumerate(xy.tolist())],
                "gateways": self.ctx.gateways,
                "modules": {k: v.health.requested for k, v in self.slots.items()},
                "model_card": card}

    def health_states(self) -> dict:
        return {k: v.health.status() for k, v in self.slots.items()}

    # -- one tick ----------------------------------------------------------
    def tick(self, t: int):
        ctx = self.ctx
        ctx.t = t
        env = self.stage("weather", t)
        fuel = self.stage("ffmc", env)
        fires = self.stage("ignition", (t, env, fuel))
        src = self.stage("growth", (t, fires, env))
        conc = self.stage("plume", (src, env))
        nuis = self.stage("nuisance", t)
        haze = self.stage("haze", t)
        x = self.stage("sensor", (t, conc, env, nuis, haze))
        x = self.stage("faults", x)
        res = self.stage("ttc", x)
        pv = self.stage("qcc", res)
        sc = self.stage("score", pv)
        cand = self.stage("cusum", sc)
        dl = self.stage("comms", cand)
        prior = self.stage("srp", (t, env, fuel))
        cl = self.stage("cluster", dl)
        k = len(cl.members)
        scmr = self.stage("scmr", cl, expect_len(k))
        fisher = self.stage("fisher", cl, expect_len(k))
        bf = self.stage("learn", fisher, expect_len(k))
        raq = self.stage("raq", (cl, scmr, bf, prior), expect_len(k))
        dec = self.stage("escalate", (cl, scmr, raq), expect_len(k))
        energy = self.stage("energy", t)
        sat = self.stage("satellite", fires)

        events, alerts, traces = [], [], []
        for fid in fires.new:
            f = next(f for f in fires.active if f.id == fid)
            events.append({"type": "ignition", "fire": int(fid), "x": f.x, "y": f.y})
        for i, p in zip(cand.nodes, cand.p):
            rec = tr.candidate_record(t, i, p, cand.G[i], cand.h, float(sc.c[i].min()))
            traces.append(rec)
            events.append({"type": "candidate", "node": int(i), "trace_id": rec["trace_id"]})
        self._last_cand[list(cand.nodes)] = t
        for j in range(k):
            traces.append(self._decision_trace(t, j, cl, scmr, fisher, bf, prior, raq, dec, cand, sc))
            if dec.levels[j] in ("CONFIRMED", "ESCALATED"):
                self._last_conf[list(cl.members[j])] = t
            if dec.new_alert[j]:
                alerts.append({"level": dec.levels[j], "cluster": list(cl.members[j]), "trace_id": traces[-1]["trace_id"]})
        for fid, ta in sat.alert_t:
            if fid not in self._sat_done and ta <= t:
                self._sat_done.add(fid)
                events.append({"type": "satellite_alert", "fire": int(fid)})
        for name, slot in self.slots.items():
            for err in slot.new_errors:
                events.append({"type": "degraded", "module": name, "error": err})
            slot.new_errors.clear()

        disp = self.cfg["params"]["display"]
        win = self.cfg["params"]["cluster"]["window_min"]
        states = fr.node_states(sc.p_node, self._last_cand > t - win, self._last_conf > t - disp["confirmed_hold_min"],
                                x.fault, energy.soc, disp["elevated_p"], disp["low_power_soc"])
        frame = {"t": t,
                 "weather": fr.weather_dict(env, fuel),
                 "prior": {"odds": float(f"{prior.odds:.4g}"), "quorum": int(raq.quorum), "day_type": prior.day_type},
                 "nodes": {"state": states.tolist(), "reading": fr.sig4(x.x[:, 0]), "residual": fr.sig4(res.r[:, 0]),
                           "p": fr.sig4(sc.p_node), "cusum": fr.sig4(cand.G), "health": fr.sig4(sc.c.min(axis=1)),
                           "soc": fr.sig4(energy.soc)},
                 "cusum_h": float(f"{cand.h:.4g}"),
                 "fires": fr.fires_list(src),
                 "packets": list(dl.packets), "events": events, "alerts": alerts,
                 "health": self.health_states()}
        return frame, traces

    def _decision_trace(self, t, j, cl, scmr, fisher, bf, prior, raq, dec, cand, sc) -> dict:
        self._seq += 1
        st = {k: self.slots[k].health.state for k in ("scmr", "fisher", "srp", "raq", "learn")}
        return tr.decision_record(
            t, self._seq, dec.levels[j], cl.members[j], cl.p[j], cand.G, cand.h, sc.c.min(axis=1),
            scmr={"f_loc": scmr.f_loc[j], "f_net": scmr.f_net[j], "ratio": scmr.ratio[j], "pass": bool(scmr.passed[j]),
                  "modelled": st["scmr"] == "real"},
            fisher={"X": fisher.X[j], "dof": int(fisher.dof[j]), "p_cluster": fisher.p_cluster[j],
                    "method": "fisher" if st["fisher"] == "real" else "bonferroni (stub)"},
            prior={"lambda": prior.lam, "p_s": prior.p_s, "odds": prior.odds, "day_type": prior.day_type},
            bayes={"bf_bound": bf.bf[j], "posterior_odds": raq.posterior_odds[j], "threshold": raq.threshold,
                   "quorum": int(raq.quorum), "decision": bool(raq.decide[j]),
                   "method": "bayes" if st["raq"] == "real" else "fixed quorum (stub)"},
            window_min=int(self.cfg["params"]["cluster"]["window_min"]))

    # -- setup and whole run -----------------------------------------------
    def setup(self) -> None:
        """Run the setup modules once, each through its isolation Slot, and place the nodes."""
        world = self.cfg["world"]
        for name in SETUP:
            self.slots[name].reset(self.ctx)
        self.landscape = self.stage("landscape", world)
        self.layout = self.stage("siting", (world, self.landscape),
                                 lambda lay: check_layout_inside(lay, self.landscape))
        self.ctx.xy = self.layout.xy.copy()
        self.links = self.stage("links", (self.ctx.xy, self.ctx.gateways))

    def run(self, writer) -> dict:
        self.setup()
        for name, slot in self.slots.items():
            if name not in SETUP:
                slot.reset(self.ctx)
        writer.header(self.header())
        every = int(self.cfg["record"]["every_k_ticks"])
        for tick, t in enumerate(self.clock.minutes()):
            self.ctx.tick = tick
            frame, traces = self.tick(t)
            if tick % every == 0 or frame["events"] or frame["alerts"] or tick == self.clock.n_ticks - 1:
                writer.frame(frame)
            for rec in traces:
                writer.trace(rec)
        footer = {"frames": writer.n_frames, "traces": writer.n_traces,
                  "health": {k: v.health.public() for k, v in self.slots.items()}}
        writer.close(footer)
        return {k: v.health.public(with_timing=True) for k, v in self.slots.items()}
