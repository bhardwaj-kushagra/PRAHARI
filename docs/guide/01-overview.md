# 1. Overview — what this project is

## The problem

Forest fires in the Himalayan foothills and the Terai belt usually start small and close to people: along footpaths,
around villages, near roads and power lines. In the first hour a fire is only a few square metres of burning litter,
far too small for a satellite, and the smoke drifts through the trees at walking pace. If someone learns about it in
that hour, a few people with beaters can put it out. Two hours later it may need a crew and a helicopter.

Satellite fire products (for example VIIRS, with pixels about 375 m across) arrive after an overpass plus processing
time, and they only see fires that have grown hot and large. Camera towers need line of sight, which dense canopy
blocks. What remains is to put many cheap sensors inside the forest itself.

## The idea: FIRENET–PRAHARI

FIRENET–PRAHARI is a design for a network of small, solar-powered gas-sensing nodes spaced tens of metres apart in the
forest, reporting over LoRaWAN radio to a gateway. Each node carries a metal-oxide gas sensor that responds to the
volatile compounds in wood smoke.

The hard part is not sensing smoke; it is **not crying wolf**. A cheap gas sensor also responds to temperature and
humidity swings, to a passing vehicle, to cooking fires, and to regional haze from crop burning. A network of 100
nodes that each raise one false alarm a month produces three false alarms a day, and rangers stop answering. The
design therefore spends most of its effort on the statistics that decide when a reading is evidence of a fire:

1. **At each node** — separate the slow daily rhythm and drift from fast changes (two-timescale conditioning, TTC),
   turn the fast change into a calibrated probability-like score (quantile-calibrated conformal p-values, QCC), and
   accumulate evidence over minutes (a CUSUM with a threshold tuned on the node's own quiet history).
2. **At the edge (gateway)** — group nearby candidate nodes, reject events that light up the whole network at once
   (spatial common-mode rejection, SCMR, because haze is everywhere while a fire is local), combine the nodes'
   evidence (Fisher's method), and weigh it against how likely a fire is today given fuel dryness and human activity
   (a risk-adaptive quorum, RAQ).

The name PRAHARI means "sentinel" or "guard" in Hindi.

## What PRAHARI-SIM is

PRAHARI-SIM is the **simulator and dashboard** that demonstrate this design for the IEEE IAS Annual Meeting 2026
student poster competition. It generates a virtual forest with weather, fuel moisture, people-driven ignitions,
spreading smoke, realistic sensor signals and nuisance events, runs the detection pipeline on them minute by minute,
and records everything so a browser dashboard can replay it without any server.

It also runs the older approaches on exactly the same signals so they can be compared honestly:

| Pipeline | What it is |
| --- | --- |
| P0 | fixed threshold: alarm when a reading exceeds its first-day mean plus three standard deviations |
| P1 | "v1 as written": a slow baseline, a z-score CUSUM with a textbook threshold, two nodes must agree |
| P1t | P1 with its threshold tuned on replayed quiet data |
| P2 | PRAHARI: the full node and edge layers (node layer since Phase 5, edge layer from Phase 6) |

## What it is not

- It is **not field data**. Every number is simulator output and is labelled SIM on screen and in files.
- It is **not a digital twin of a real forest**. The landscape is illustrative (tagged ASM, "assumption").
- It is **not tuned to look good**. Parameters come from literature, vendor data, derivations, stated assumptions or
  design targets, each tagged in the configuration (LIT, VEN, DER, ASM, TGT). Where a result misses a target, the
  miss is reported with its cause (see [../results/validation.md](../results/validation.md)).

## How it is built

The engine is Python (NumPy, SciPy). Each part of the model is a **stage** with three interchangeable versions:
`real` (the full model), `stub` (a simple stand-in that always works) and `off`. Which one runs comes from a YAML
configuration, and a real stage that fails is automatically replaced by its stub for the rest of the run. This let
the project grow in phases, each ending with a working dashboard, and it means a broken module never breaks the demo.

The dashboard is React + TypeScript with ECharts for charts. It reads compressed recordings
(`recordings/*.prs.jsonl.gz`) and experiment summaries (`results/summary.json`).

Next: [02-background.md](02-background.md) explains the science, and the [journey](../journey/README.md) explains
how it was built.
