# Decisions and trade-offs

The decisions that most shape the project, with the alternatives considered. Ids refer to `DECISIONS.md`.

## Architecture

| Decision | Alternatives | Pros | Cons | Ids |
| --- | --- | --- | --- | --- |
| Every module has real, stub and off versions chosen by configuration | one implementation per module; feature flags in code | phases can be added safely; a failure never breaks the demo; A/B comparisons are one line of YAML | more classes; stubs must be maintained | SPEC P1–P2, P0-1 |
| Failures fall back real → stub → off → hold → neutral | stop the run; retry | the demo always finishes; degradation is visible | a silent fallback could hide a bug — mitigated by `degraded` events and the health table | P0-1 |
| One random stream per module, append-only list | one global stream (as the report) | adding a module never changes other results | cannot reproduce the report's exact draws — compared by distribution instead | N-c, P4-3 |
| Live mode streams the recording's own line format | a separate live protocol | one parser, every view works live | a snapshot object per update | P6-8 |
| Replay-first dashboard reading files | a live server | works offline at a conference; deterministic | recordings must be regenerated after engine changes | P0-5, P0-10 |
| Additive contracts and frame fields | versioned breaking changes | old recordings still open | fields accumulate | CLAUDE.md rule 3 |
| Provenance tag on every parameter, enforced by the loader | free-form comments | honest, auditable; the model card can show sources | more verbose configuration | P0-3, rule 9 |

## Science and modelling

| Decision | Alternatives | Pros | Cons | Ids |
| --- | --- | --- | --- | --- |
| Legacy models (M9, M12) as defaults; advanced (M11) opt-in | always the most physical model | golden numbers reproducible | the default is not the most physical | P3a-1, P3b-1 |
| Signal model matched to the report's simulation | an independent sensor model | comparability | inherits the report's assumptions | P2-3 |
| Illustrative landscape, 1400 m, grid centred | a real place; the 700 m map | meaningful siting and radio comparisons; honest ASM tag | not a real location | P1-1, P1-2 |
| Static 14-day QCC calibration by default; sliding window optional | always sliding | matches the report | calibration does not adapt after day 14 unless enabled | P5-3 |
| Keep the report's common-mode rule despite the seed-22 finding | change the rule now | golden reproducible; finish the main build first | a known weakness stays until reviewed | P5-10 |

## Evaluation and honesty

| Decision | Alternatives | Pros | Cons | Ids |
| --- | --- | --- | --- | --- |
| Never tune to hit the report; investigate misses | adjust parameters until they fit | trustworthy results | visible misses in golden tests | rule 10, P4-6 |
| 20-seed engine-versus-oracle comparisons when a 5-seed result misses | accept or reject on 5 seeds | separates code errors from sampling | costs minutes of compute | P4-7, P5-11 |
| Report values stored only in `tests/golden/`, copied with a label | constants in code | no hard-coded results; clear provenance on screen | one indirection | P4-5 |
| Traces state which rule decided (stub or real) | a single explanation template | explanations never overclaim | longer traces | P0-9 |
| Legacy per-candidate edge by default; SPEC's component form as an option | only the SPEC's form | golden-comparable, exact match to the report's rule | two forms to explain | P6-2, N-b |
| Keep the accepted plume stub unchanged despite the P2 detection gap; propose a legacy per-fire wind option | change it now | rule 4 respected; the diagnosis is recorded | P2 detection stays below the report until approved | P6-11 |
| Warm-start recordings for the demo | show only young networks; shorten calibration | shows the designed operating point without touching the model | longer generation | P5-14 |
| Legacy per-fire wind for experiment presets (after approval) | keep weather wind everywhere | the report's fire model exactly; demos unchanged | did not close the detection gap (recorded) | P7-1 |
| Offline edge and dial replay from recorded node evidence | simulate every variant | one pair of passes per node configuration; tested equal to the live path | the harness no longer runs the edge live | P7-2, P7-4 |
| Both ablation forms: module stubs (default, the dashboard's switches) and the report simulation's legacy variants (the `ablation` preset) | one form only | the SPEC's meaning and a like-for-like comparison with the report | three extra parameters and two optional contract fields in accepted modules (approved) | P7-10, P7-12 |
| A 2 × 2 reverse swap before calling a gap "sampling" | stop at the fresh-seed check | separates background from fire-set effects; each then checked at model level | about an hour of compute | P7-14 |
| Radio and energy models real only in the Phase 8 scenarios | real everywhere | every earlier result and recording unchanged | the default demo shows perfect links | P8-1 |

## Process

| Decision | Alternatives | Pros | Cons |
| --- | --- | --- | --- |
| Plan → go → build → test → record → review for every phase | build freely | predictable, reviewable progress | overhead per phase |
| Escape hatch: park a module as a stub after about three failed attempts | keep trying | the project never blocks | parked work must be revisited (none parked so far) |
| Documentation as a deliverable of every phase (rule 16) | write docs at the end | the story is captured while it is fresh | time in every phase |
