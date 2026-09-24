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
    "baseline_p0": C.BaselineAlarms, "baseline_p1": C.BaselineAlarms, "baseline_p1t": C.BaselineAlarms,
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
        self._haze_prev = 0.0
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
                         "source": cfg["params"].get(name, {}).get("source", ""),
                         "notes": s.snapshot()})
        return {"schema": C.CONTRACT_VERSION, "label": "SIMULATION",
                "scenario": cfg["scenario"]["name"], "description": cfg["scenario"]["description"],
                "regime": {k: v for k, v in cfg["regime_card"].items() if k != "source"},   # Phase 9, SPEC §8.1
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

    def switch_module(self, name: str, state: str) -> None:
        """Live mode (Phase 6): rebuild one module's Slot in a new state between ticks. The new implementation starts
        from `reset`, so stateful modules (for example QCC's calibration) start afresh; the random stream continues."""
        old = self.slots[name]
        rng = getattr(old.chain[0], "_rng", None)
        slot = Slot(name, state, self.cfg["params"].get(name, {}), rng, old.out_type)
        slot.reset(self.ctx)
        self.slots[name] = slot
        self.cfg["modules"][name] = state

    def health_states(self) -> dict:
        return {k: v.health.status() for k, v in self.slots.items()}

    # -- one tick ----------------------------------------------------------
    def step_signals(self, t: int):
        """Weather → fires → plume → sensor signals for tick t (shared by `tick` and the headless experiments)."""
        self.ctx.t = t
        env = self.stage("weather", t)
        fuel = self.stage("ffmc", env)
        fires = self.stage("ignition", (t, env, fuel))
        src = self.stage("growth", (t, fires, env))
        conc = self.stage("plume", (src, env))
        nuis = self.stage("nuisance", t)
        haze = self.stage("haze", t)
        x = self.stage("sensor", (t, conc, env, nuis, haze))
        x = self.stage("faults", x)
        self.last_env = (env, fuel)                        # the edge layer's prior reads them (step_edge)
        return env, fuel, fires, src, conc, haze, x

    def step_baselines(self, x):
        """Baseline detectors P0 (M22), P1 (M23) and P1t (M23 with M28 tuning) on the same signals (SPEC §4.5)."""
        return self.stage("baseline_p0", x), self.stage("baseline_p1", x), self.stage("baseline_p1t", x)

    def step_node(self, x):
        """PRAHARI node layer: TTC → QCC → score → CUSUM (shared by `tick` and the headless experiments)."""
        res = self.stage("ttc", x)
        self.ctx.z_slow = res.z                            # M28 — common-mode exclusion reads the slow z
        pv = self.stage("qcc", res)
        sc = self.stage("score", (pv, x, res))            # M27; the real score adds M29 health weights (Phase 9)
        cand = self.stage("cusum", sc)
        return res, pv, sc, cand

    def step_edge(self, t: int, env, fuel, cand, c=None):
        """PRAHARI edge layer: comms → cluster → SCMR → Fisher → Bayes factor → RAQ → escalation (M30–M35)."""
        dl = self.stage("comms", cand)
        prior = self.stage("srp", (t, env, fuel))
        self.ctx.prior = prior                             # SCMR relaxes during a lightning storm (M31, Phase 9)
        cl = self.stage("cluster", dl)
        k = len(cl.members)
        scmr = self.stage("scmr", cl, expect_len(k))
        fisher = self.stage("fisher", cl, expect_len(k))
        bf = self.stage("learn", (fisher, cl, scmr, c), expect_len(k))   # M34 bound, or the M36 fit (Phase 9)
        raq = self.stage("raq", (cl, scmr, bf, prior), expect_len(k))
        dec = self.stage("escalate", (cl, scmr, raq), expect_len(k))
        return dl, prior, cl, scmr, fisher, bf, raq, dec

    def tick(self, t: int):
        env, fuel, fires, src, conc, haze, x = self.step_signals(t)
        base0, base1, base1t = self.step_baselines(x)
        res, pv, sc, cand = self.step_node(x)
        dl, prior, cl, scmr, fisher, bf, raq, dec = self.step_edge(t, env, fuel, cand, sc.c)
        k = len(cl.members)
        energy = self.stage("energy", (t, env, dl))          # M41–M43: harvest, draw, and this tick's frames
        self.ctx.energy_mode = energy.mode                 # comms skips nodes that are off (next tick)
        sat = self.stage("satellite", fires)

        events, alerts, traces = [], [], []
        causes = fires.new_causes if len(fires.new_causes) == len(fires.new) else ("scripted",) * len(fires.new)
        for fid, cause in zip(fires.new, causes):
            f = next(f for f in fires.active if f.id == fid)
            events.append({"type": "ignition", "fire": int(fid), "x": f.x, "y": f.y, "cause": cause})
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
                alerts.append({"level": dec.levels[j], "cluster": list(cl.members[j]), "trace_id": traces[-1]["trace_id"],
                               "incident": int(dec.incident[j]) if dec.incident else -1})
        for tf, i, kind in getattr(self.slots["faults"].stage, "started", ()):   # M21 ground truth (Phase 9)
            events.append({"type": "fault_start", "node": int(i), "kind": kind})
        if haze.level > 0 and self._haze_prev == 0:
            events.append({"type": "haze_start", "level": float(f"{haze.level:.4g}")})
        self._haze_prev = haze.level
        for i, _ in base0.alarms:
            events.append({"type": "p0_alarm", "node": int(i)})
        for i, members in base1.alarms:
            events.append({"type": "p1_alarm", "node": int(i), "members": list(members)})
        for i, members in base1t.alarms:
            events.append({"type": "p1t_alarm", "node": int(i), "members": list(members)})
        for pl in sat.plan:                                # M37 — the race timeline's satellite forecast (Phase 9)
            events.append({"type": "satellite_plan", "fire": pl["fire"], "overpass_t": pl["overpass_t"],
                           "platform": pl["platform"], "alert_t": None if pl["alert_t"] is None else round(pl["alert_t"], 1),
                           "missed": [q["t"] for q in pl["passes"] if not q["seen"]]})
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
        abstain = sc.c.min(axis=1) < float(disp["abstain_c"])  # M29 — "this sensor abstains" (the system's view)
        states = fr.node_states(sc.p_node, self._last_cand > t - win, self._last_conf > t - disp["confirmed_hold_min"],
                                abstain, energy.soc, disp["elevated_p"], disp["low_power_soc"])
        frame = {"t": t,
                 "weather": fr.weather_dict(env, fuel),
                 "prior": {"odds": float(f"{prior.odds:.4g}"), "quorum": int(raq.quorum), "day_type": prior.day_type},
                 "nodes": {"state": states.tolist(), "reading": fr.sig4(x.x[:, 0]), "residual": fr.sig4(res.r[:, 0]),
                           "p": fr.sig4(sc.p_node), "cusum": fr.sig4(cand.G), "health": fr.sig4(sc.c.min(axis=1)),
                           "soc": fr.sig4(energy.soc), "conc": fr.sig4(conc.c),
                           "baseline": fr.sig4(res.b[:, 0]), "n_cal": [int(v) for v in pv.n_cal],
                           **({"queue": [int(v) for v in dl.queue]} if dl.queue is not None else {}),
                           **({"mode": [int(v) for v in energy.mode]} if energy.mode is not None else {})},
                 "cusum_h": float(f"{cand.h:.4g}"),
                 "haze": float(f"{haze.level:.4g}"),
                 "fires": fr.fires_list(src),
                 "packets": list(dl.packets), "events": events, "alerts": alerts,
                 **({"gateways_down": list(dl.down)} if dl.queue is not None else {}),
                 "health": self.health_states()}
        grid = self._plume_grid(src, env)
        if grid is not None:
            frame["plume"] = grid
        return frame, traces

    def _plume_grid(self, src, env):
        """Display-only plume grid every `record.plume_every_ticks` while fires burn; never breaks the run."""
        rec = self.cfg["record"]
        stage = self.slots["plume"].stage
        if not src.ids or self.ctx.tick % int(rec["plume_every_ticks"]) or not hasattr(stage, "field"):
            return None
        try:
            w = self.cfg["world"]
            return fr.plume_grid(lambda pts: stage.field(pts, src, env), src.x, src.y, float(w["width_m"]),
                                 float(w["height_m"]), float(rec["plume_cell_m"]), float(rec["plume_margin_m"]))
        except Exception:                                  # noqa: BLE001 — display only
            return None

    def _decision_trace(self, t, j, cl, scmr, fisher, bf, prior, raq, dec, cand, sc) -> dict:
        self._seq += 1
        st = {k: self.slots[k].health.state for k in ("scmr", "fisher", "srp", "raq", "learn")}
        return tr.decision_record(
            t, self._seq, dec.levels[j], cl.members[j], cl.p[j], cand.G, cand.h, sc.c.min(axis=1),
            scmr={"f_loc": scmr.f_loc[j], "f_net": scmr.f_net[j], "ratio": scmr.ratio[j], "pass": bool(scmr.passed[j]),
                  "modelled": st["scmr"] == "real"},
            fisher={"X": fisher.X[j], "dof": int(fisher.dof[j]), "p_cluster": fisher.p_cluster[j],
                    "method": "fisher" if st["fisher"] == "real" else "bonferroni (stub)"},
            prior={"lambda": raq.lam_c[j] if raq.lam_c else prior.lam, "p_s": prior.p_s,
                   "odds": raq.odds_c[j] if raq.odds_c else prior.odds, "day_type": prior.day_type},
            bayes={"bf_bound": bf.bf[j], "posterior_odds": raq.posterior_odds[j], "threshold": raq.threshold,
                   "quorum": int(raq.quorum), "decision": bool(raq.decide[j]), "method": raq.method},
            window_min=int(self.cfg["params"]["cluster"]["window_min"]),
            extra={"incident": int(dec.incident[j]) if dec.incident else -1,
                   "anchor": int(cl.anchor[j]) if cl.anchor else -1})

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
        self.ctx.landscape = self.landscape
        self.links = self.stage("links", (self.ctx.xy, self.ctx.gateways))
        self.ctx.links = self.links                        # Phase 8: comms routes, re-routing and relays

    def prepare(self) -> None:
        """Setup modules, then reset every tick stage (used by `run` and the headless experiments)."""
        self.setup()
        for name, slot in self.slots.items():
            if name not in SETUP:
                slot.reset(self.ctx)

    def run(self, writer) -> dict:
        self.prepare()
        every = int(self.cfg["record"]["every_k_ticks"])
        start = int(round(float(self.cfg["record"]["from_day"]) * 1440))    # warm start: record from this minute
        if start >= self.clock.n_ticks * self.clock.tick_minutes:
            raise ValueError(f"record.from_day {self.cfg['record']['from_day']} is not inside the run")
        started = False
        carry: list = []                               # packets of skipped ticks, written with the next frame
        for tick, t in enumerate(self.clock.minutes()):
            self.ctx.tick = tick
            if not started and t >= start and start <= 0:
                writer.header(self.header())
                started = True
            frame, traces = self.tick(t)
            if t < start:
                continue
            first = not started
            if first:                                  # warm start: the model card shows the state (e.g. tuned h)
                head = self.header()                   # after the first recorded tick
                head["record_from_min"] = t
                writer.header(head)
                started = True
            if first or tick % every == 0 or frame["events"] or frame["alerts"] or tick == self.clock.n_ticks - 1:
                if carry:
                    frame["packets"] = carry + frame["packets"]
                    carry = []
                writer.frame(frame)
            elif frame["packets"]:                     # Phase 8: keep every packet; each carries its own minute
                carry += [dict(pk, t=t) for pk in frame["packets"]]
            for rec in traces:
                writer.trace(rec)
        footer = {"frames": writer.n_frames, "traces": writer.n_traces,
                  "health": {k: v.health.public() for k, v in self.slots.items()}}
        writer.close(footer)
        return {k: v.health.public(with_timing=True) for k, v in self.slots.items()}
