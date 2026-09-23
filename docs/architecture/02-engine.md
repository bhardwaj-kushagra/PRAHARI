# Architecture 2 — the engine

The engine is the Python package `engine/prahari/` (NumPy, SciPy, PyYAML; pytest for tests). This page walks through
it from the outside in.

## Package layout

```text
engine/prahari/
├── cli.py                  `prahari run` and `prahari experiment`
├── stages.py               imports every stage module so they register themselves
├── core/                   the framework (no science in here)
│   ├── registry.py         Stage base class, @register(name, kind), lookup and build
│   ├── runner.py           Slot: the isolation wrapper around every stage call
│   ├── config.py           load, merge and validate YAML (unknown keys and untagged parameters are errors)
│   ├── rng.py              one NumPy Generator per module, spawned from the master seed
│   ├── clock.py            ticks, minutes, time of day
│   ├── context.py          RunContext: positions, distances, neighbours, current tick, shared per-tick values
│   ├── contracts*.py       stage output data classes and their validators
│   ├── pipeline.py         Simulation: setup, the tick, frames, events, traces, the run loop
│   ├── health.py, trace.py module health records; evidence-trace records
├── world/                  landscape (M2–M3), siting (M1, M4), geometry
├── env/                    weather (M5–M6), ffmc (M7)
├── fire/                   ignition (M3, M8), growth (M9), plume (M12 legacy), gaussian (M11, M14–M15)
├── sensors/                mox sensor (M17–M19), nuisance and haze (M20), faults (M21)
├── detect/baselines/       fixed (P0, M22), v1 (P1, M23), v1t (P1t)
├── detect/prahari/         ttc, qcc, score, cusum (stubs) and ttc_real, qcc_real, cusum_real, tuning (Phase 5);
│                           cluster, scmr, fisher, srp, learn, raq, escalate (stubs until Phase 6)
├── comms/                  pathloss (M38), lorawan (stub)
├── energy/, satellite/     stubs until Phases 8–9
├── record/                 writer and reader of recordings, frame helpers, world header sections
└── eval/                   stats (M44–M46), experiments (harness), node_metrics (Phase 5)
```

## Stages and the registry

A **stage** is a class with `reset(ctx)` (clear per-run state) and `step(inputs, ctx)` (one tick), plus metadata for
the model card: `equation` (M-numbers), `tag` (provenance), `description`, and `snapshot()` (small state shown as
notes). Each module name has up to three registered classes:

```python
@register("qcc", kind="stub")   # always present; simple, cannot fail
@register("qcc", kind="real")   # the full model
@register("qcc", kind="off")    # module switched out (where allowed)
```

Real implementations live in their own files where the stub file is from an accepted phase (for example
`qcc_real.py` beside `qcc.py`), so accepted code is not edited.

## Isolation: the Slot

Every stage call goes through a `Slot` (`core/runner.py`). It builds the fallback chain
**real → stub → off → hold last valid output → the contract's neutral output**. If the running implementation raises
an exception, or returns output that fails its contract check (NaN, wrong shape, out of range), the slot moves one step
down the chain for the rest of the run, marks the module `degraded`, records the error once and adds a `degraded` event
to the frame. The run never stops. Step times are measured here and written to `*.health.json`, not to the recording,
so recordings stay byte-identical.

## Configuration

`config.py` merges `configs/default.yaml` with a scenario or preset file. Rules enforced on load:

- every key in an override must exist in the defaults, with the same type;
- every block under `params` must carry `source:` starting with LIT, VEN, DER, ASM or TGT;
- every module has a state, `real`, `stub` or `off`.

Top-level sections: `run` (seed, start, days, tick), `scenario`, `record` (frame interval, grids, `from_day`),
`world` (map, nodes, interfaces, gateways), `modules` (states), `params` (per-module parameters), `experiment`.

## Randomness

`core/rng.py` spawns one `numpy.random.Generator` per stream from `SeedSequence(seed)`. The stream list is
append-only (weather, ignition, growth, plume, sensor, nuisance, haze, faults, comms, satellite, protocol), so adding a
module never changes the numbers other modules draw. Python's `random` and unseeded NumPy calls are not used.

## The tick

`Simulation` (`core/pipeline.py`) runs `prepare()` (setup stages, then `reset` on every tick stage) and then, for every
simulated minute:

1. `step_signals(t)`: weather → ffmc → ignition → growth → plume, nuisance, haze → sensor → faults.
2. `step_baselines(x)`: P0, P1 and P1t on the same readings.
3. `step_node(x)`: ttc → qcc → score → cusum. The TTC slow z is also put in `ctx.z_slow` for the common-mode rule.
4. The edge layer: comms → cluster → scmr → fisher → learn → raq → escalate; plus srp, energy, satellite.
5. Events (ignitions, candidates, alarms, haze start, degradations) and evidence traces are collected, node display
   states are computed, and a frame dictionary is built.

`run()` writes every `record.every_k_ticks`-th frame plus every frame that has an event or alert, and the last one.
With `record.from_day` set (warm start), everything is simulated from day 0 but frames and traces are written only
from that day on; the header is written after the first recorded tick so its model card shows, for example, the tuned
threshold.

Per-node state is held in NumPy arrays; there are no Python loops over nodes inside the tick (CLAUDE.md rule 8). The
node layer costs about 0.3 ms per tick (SIM timing on the development machine).

## The experiment harness

`eval/experiments.py` runs the M46 protocol headlessly, calling exactly the same `step_signals`, baseline and node
code but building no frames:

- per seed, a **quiet pass** (no fires) for false alarms, and a **fire pass** with protocol fires (every 6 hours in
  the test period, kept with probability 0.8 on dry days and 0.2 on wet days, drawn from the `protocol` stream);
- incidents and detections are counted with `eval/stats.py` (M44–M46);
- with `node_metrics`, `eval/node_metrics.py` also records QCC exceedance, node candidates and the tuned h;
- output: `results/<preset>_seed<N>.json` and `results/summary.json` (which also copies the report's reference
  values from `engine/tests/golden/report_reference.json`, the only place such numbers live).

## Adding a real module (the pattern used in every phase)

1. Write the maths as pure functions (arrays in, arrays out), each formula commented with its M-number.
2. Add a `real` class registered under the existing module name, in a new file if the stub's file is accepted.
3. Add its parameters to `configs/default.yaml` with a `source` tag; set the module state.
4. Import the file in `stages.py`.
5. Write unit tests with SPEC §9.2 values and, where the oracle has the same function, an identical-input
   cross-check.
6. Regenerate recordings, update the docs (CLAUDE.md rule 16).
