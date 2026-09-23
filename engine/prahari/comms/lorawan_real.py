"""Communications — real implementation (SPEC §5.12, M38–M40, Phase 8).

Every minute: candidate frames (confirmed uplinks) and hourly heartbeats (unconfirmed) start at random moments in
the minute on one of `channels` channels, at the node's spreading factor, for their LoRa time on air (M39). Frames
that overlap on the same channel and SF collide unless one is at least `capture_db` stronger (M40); lost candidate
frames retry up to `retries` times after U(backoff) seconds. A node without a direct gateway link sends through its
TS011 relay, which forwards one hop later. When a node's gateway is out (`outages`) and no other gateway closes, its
candidate frames wait in a queue (store-and-forward) and go out when the gateway returns. A candidate reaches the edge
in the minute its last hop finishes. Nodes whose energy mode is "off" do not transmit.

Assumptions (ASM): frames that spill past the minute, retries that start after it and relay second hops are resolved
with the next minute's frames; all frames share one collision domain (one gateway in the scenarios).
"""
from __future__ import annotations

import numpy as np

from prahari.comms.lora import collide, time_on_air
from prahari.core.contracts import Candidates, Delivered
from prahari.core.registry import Stage, register

SFS = (7, 8, 9, 10, 11, 12)


@register("comms", kind="real")
class CommsReal(Stage):
    equation = "M38–M40, TS011"
    tag = "VEN"
    description = "LoRa uplinks: time on air, ALOHA collisions with capture, retries, relays, store-and-forward"

    def reset(self, ctx) -> None:
        p, n = self.params, ctx.n_nodes
        self._gw = [g["id"] for g in ctx.gateways]
        L = ctx.links
        if L is not None and L.sf_all is not None:
            self._sf_all, self._prx_all = np.asarray(L.sf_all), np.asarray(L.prx_all, dtype=float)
        else:                                                    # no radio model: nearest gateway at SF7
            g = np.array([[gw["x"], gw["y"]] for gw in ctx.gateways], dtype=float).reshape(-1, 2)
            d = np.hypot(ctx.xy[:, None, 0] - g[None, :, 0], ctx.xy[:, None, 1] - g[None, :, 1])
            near = d == d.min(axis=1, keepdims=True)
            self._sf_all, self._prx_all = np.where(near, 7, 0), np.where(near, 0.0, -np.inf)
        none = np.full(n, -1)
        self._relay = none if L is None or L.relay is None else np.asarray(L.relay)
        self._relay_sf = np.zeros(n, int) if L is None or L.relay_sf is None else np.asarray(L.relay_sf)
        self._relay_prx = np.zeros(n) if L is None or L.relay_prx is None else np.asarray(L.relay_prx)
        self._toa = {sf: time_on_air(int(p["payload_b"]), sf, float(p["bw_hz"]), int(p["cr"])) for sf in SFS}
        self._hb = self.rng.integers(0, int(p["heartbeat_min"]), n)   # each node's heartbeat minute in the hour
        self._queue: list[list] = [[] for _ in range(n)]
        self._pending: list[dict] = []                           # frames resolved in a later minute
        self._late: list[tuple] = []                             # (minute, node, p) delivered later
        ids = {g: j for j, g in enumerate(self._gw)}
        self._outages = [(ids[o["gateway"]], int(o["t_min"]), int(o["t_min"]) + int(o["duration_min"]))
                         for o in p["outages"]]

    def _up(self, t: int) -> np.ndarray:
        up = np.ones(len(self._gw), dtype=bool)
        for j, a, b in self._outages:
            if a <= t < b:
                up[j] = False
        return up

    def _direct(self, i: int, up):
        """Best gateway that is up and closes for node i: (gateway index, SF, received power) or None."""
        ok = up & (self._sf_all[i] > 0)
        if not ok.any():
            return None
        g = int(np.where(ok, self._prx_all[i], -np.inf).argmax())
        return g, int(self._sf_all[i, g]), float(self._prx_all[i, g])

    def _frame(self, i: int, p: float, kind: str, t: int, up, start: float):
        """First-hop frame from node i, or None when no route exists now."""
        d = self._direct(i, up)
        if d is not None:
            g, sf, prx = d
            return {"node": i, "tx": i, "p": p, "kind": kind, "hop": "gw", "g": g, "sf": sf, "prx": prx,
                    "to": self._gw[g], "relay": None, "start": start, "retry": 0, "t0": t}
        r = int(self._relay[i])
        if r >= 0 and self._direct(r, up) is not None:
            return {"node": i, "tx": i, "p": p, "kind": kind, "hop": "relay", "g": -1, "sf": int(self._relay_sf[i]),
                    "prx": float(self._relay_prx[i]), "to": f"n{r}", "relay": r, "start": start, "retry": 0, "t0": t}
        return None

    def step(self, cand: Candidates, ctx) -> Delivered:
        p, t, n = self.params, ctx.t, ctx.n_nodes
        now, end = 60.0 * t, 60.0 * (t + 1)
        up = self._up(t)
        mode = getattr(ctx, "energy_mode", None)
        alive = np.ones(n, dtype=bool) if mode is None else np.asarray(mode) != 2
        rng, packets = self.rng, []
        air = [f for f in self._pending if f["start"] < end]
        self._pending = [f for f in self._pending if f["start"] >= end]
        waiting = np.array([bool(q) for q in self._queue]) & alive
        for i in np.flatnonzero(waiting):                        # store-and-forward: send the queue when a route exists
            kept = []
            for pv, t0 in self._queue[i]:
                f = self._frame(int(i), pv, "candidate", t, up, now + rng.uniform(0.0, 60.0))
                if f is None:
                    kept.append((pv, t0))
                else:
                    air.append(dict(f, t0=t0))
            self._queue[i] = kept
        for i, pv in zip(cand.nodes, cand.p):
            if not alive[i]:
                continue
            f = self._frame(int(i), float(pv), "candidate", t, up, now + rng.uniform(0.0, 60.0))
            if f is not None:
                air.append(f)
            elif len(self._queue[i]) < int(p["queue_max"]):
                self._queue[i].append((float(pv), t))
                packets.append({"from": int(i), "to": None, "ok": False, "sf": None, "kind": "candidate",
                                "queued": True, "retry": 0, "toa_ms": 0.0, "relay": None})
        hb = np.flatnonzero((t % int(p["heartbeat_min"]) == self._hb) & alive)
        for i in hb:
            f = self._frame(int(i), 1.0, "heartbeat", t, up, now + rng.uniform(0.0, 60.0))
            if f is None:
                packets.append({"from": int(i), "to": None, "ok": False, "sf": None, "kind": "heartbeat",
                                "queued": False, "retry": 0, "toa_ms": 0.0, "relay": None})
            else:
                air.append(f)
        delivered = [(i, pv) for (tt, i, pv) in self._late if tt <= t]
        self._late = [x for x in self._late if x[0] > t]
        lost = self._resolve(air, end)
        for f, bad in zip(air, lost):
            packets.append({"from": int(f["tx"]), "to": f["to"], "ok": not bad, "sf": f["sf"], "kind": f["kind"],
                            "queued": False, "retry": f["retry"], "toa_ms": round(self._toa[f["sf"]] * 1e3, 1),
                            "relay": f["relay"]})
            if bad:
                continue
            fin = f["start"] + self._toa[f["sf"]]
            if f["hop"] == "relay":                              # TS011: the relay forwards one hop later
                r = f["relay"]
                d = self._direct(r, self._up(int(fin // 60)))
                if d is not None:
                    g, sf, prx = d
                    self._pending.append(dict(f, tx=r, hop="gw", g=g, sf=sf, prx=prx, to=self._gw[g], retry=0,
                                              start=fin + float(p["relay_delay_s"])))
            elif f["kind"] == "candidate":
                tt = int(fin // 60)
                if tt <= t:
                    delivered.append((f["node"], f["p"]))
                else:
                    self._late.append((tt, f["node"], f["p"]))
        queue = np.array([len(q) for q in self._queue], dtype=float)
        return Delivered(nodes=tuple(int(i) for i, _ in delivered), p=tuple(float(v) for _, v in delivered),
                         packets=tuple(packets), queue=queue, down=tuple(g for g, u in zip(self._gw, up) if not u))

    def _resolve(self, air: list, end: float) -> list:
        """M40 — collisions among this minute's frames; lost candidate frames retry (appended to `air`) until no
        new retry starts inside the minute. Retries that start later wait in `_pending`. Returns lost flags."""
        p, handled = self.params, set()
        lo, hi = (float(v) for v in p["backoff_s"])
        if not air:
            return []

        def lost_now():
            for f in air:
                if "ch" not in f:                                # each transmission picks its channel once
                    f["ch"] = int(self.rng.integers(0, int(p["channels"])))
            return collide([f["start"] for f in air], [self._toa[f["sf"]] for f in air], [f["ch"] for f in air],
                           [f["sf"] for f in air], [f["prx"] for f in air], float(p["capture_db"]))

        for _ in range(4 * int(p["retries"]) + 4):
            lost = lost_now()
            new = False
            for k in np.flatnonzero(lost):
                f = air[k]
                if k in handled or f["kind"] != "candidate" or f["retry"] >= int(p["retries"]):
                    continue
                handled.add(k)
                r = dict(f, retry=f["retry"] + 1, start=f["start"] + self._toa[f["sf"]] + self.rng.uniform(lo, hi))
                r.pop("ch", None)
                if r["start"] < end:
                    air.append(r)
                    new = True
                else:
                    self._pending.append(r)
            if not new:
                return lost.tolist()
        return lost_now().tolist()                               # iteration cap: flags for every frame in `air`

    def snapshot(self) -> dict:
        return {"channels": self.params["channels"], "toa_ms": {sf: round(v * 1e3, 1) for sf, v in self._toa.items()},
                "relayed_nodes": int((self._relay >= 0).sum()), "outages": len(self._outages)}
