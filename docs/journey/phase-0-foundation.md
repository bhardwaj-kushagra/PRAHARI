# Phase 0 — Foundation and replay shell

## Goal

Build the skeleton that every later phase plugs into: a module framework where every stage can be real, stub or off;
failure isolation; deterministic recordings; and a dashboard that replays them. At the end, the whole pipeline had to
run on stubs alone.

## What was built

- `engine/prahari/core/`: registry, `Slot` isolation, configuration loader with provenance checks, random streams,
  clock, contracts, health, evidence traces, and the tick loop.
- A stub (and an `off` where allowed) for all 23 tick modules, each with its M-number.
- Gzipped JSON-lines recordings; `prahari run`; the `smoke` scenario (one day, one scripted fire).
- Dashboard: `FrameSource` interface and `RecordingSource`, Command Map, time controls with event markers, module
  health and model card, node readout, alerts with explanations, SIMULATION badge and footer.

## How it works

Configuration chooses each module's state; the pipeline wraps every call in a `Slot` that falls back
real → stub → off → hold last → neutral output on failure. A frame is written every few ticks and at every event.
The dashboard reads the file in the browser and scrubs through it. See
[../architecture/02-engine.md](../architecture/02-engine.md).

## Challenges and issues

1. **Specification errors.** Recomputing every reference value in SPEC §9.2 found five problems (E-1 to E-5): files in
   the wrong place, three equations cited by the wrong M-number, and an internally inconsistent trace example.
2. **The CUSUM stub flooded.** Applying the textbook threshold h = 8.8 to −ln p scores with k = 1.5 produced about 100
   false candidates a day, because h from the ARL formula is only valid on the z scale.
3. **Start-up artefacts.** In the first hour the baseline was still settling and produced about 11 spurious candidates.
4. **Files growing past 300 lines.** The contract data classes alone would have exceeded the size rule.
5. **Timings versus determinism.** Step timings are useful but differ run to run; storing them in the recording would
   break byte-identical output.
6. **Honest explanations with stub decisions.** Early alerts came from stub rules (fixed quorum), but a generated
   sentence could have implied a Bayes calculation.

## Decisions and trade-offs

| Decision | Why | Pros | Cons |
| --- | --- | --- | --- |
| Fix the SPEC errata first (E-1…E-5) and log them | later phases depend on correct references | one source of truth | a SPEC version bump before any code |
| CUSUM stub = the v1 CUSUM on z = Φ⁻¹(1 − p), k = 0.5 (P0-7) | the ARL-derived h is valid only there | a sane stub with no tuning | the stub is not M28; real M28 had to wait for Phase 5 |
| Stub warm-up: running-mean baseline, CUSUM held at 0 for 60 min (P0-8) | removes start-up candidates | readable smoke recording | one more parameter (`warmup_min`, tagged ASM) |
| Split contracts across files, re-exported (P0-6) | size rule | small files, same import path | readers must know the re-export |
| Timings in `*.health.json`, gzip with time 0 (P0-2) | determinism | same seed → same SHA-256 | timings are not inside the recording |
| Traces record which rule decided (P0-9) | scientific honesty | no explanation overclaims | longer trace records |
| Plain-Python config validation, no Pydantic (P0-3) | minimal dependencies | nothing extra to install | hand-written checks |

## Resolution

All six issues were fixed inside the phase; nothing was parked.

## Acceptance results

| Test | Result |
| --- | --- |
| `pytest engine/tests` | 52 passed |
| Smoke scenario, one simulated day | about 1.6 s (limit 5 s) |
| Same seed → identical recording | identical SHA-256; a different seed differs |
| Dashboard plays the recording | clock advances, 100 nodes, fire and confirmation shown, no console errors |
| Forced failure → degraded, run completes | tested for an exception, NaN output and a required module |

## What to show

`smoke` recording: play it, watch the scripted fire and the stub pipeline's confirmation; open *Health & model card*
to show every module, its state and equation.
