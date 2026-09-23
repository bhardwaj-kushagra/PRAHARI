# Challenges and lessons

The problems that shaped the project, grouped by theme. Each links to the phase where it happened and the decision
entry that records it.

## 1. When a result misses the published number

**What happened.** P0 (Phase 4) and P1t (Phase 5) landed outside the report's 95% intervals on the five golden seeds;
P1 and the node-layer criteria landed inside.

**What we did.** First proved the code was the same (identical inputs → identical outputs against the report's own
simulation). Then measured the spread: the oracle's own results vary a lot from seed to seed because false alarms
arrive in bursts. Finally ran engine and oracle over the same 20 seeds and compared distributions: no detectable
difference (P0 Welch p = 0.58, P1 p = 0.40, P1t p = 0.58).

**Lesson.** A Poisson interval on a pooled count understates the uncertainty of bursty events. Compare distributions
over many seeds before suspecting the code, and never tune a model to hit a number (CLAUDE.md rule 10). →
[phase 4](phase-4-baselines.md), [phase 5](phase-5-node-layer.md), `DECISIONS.md` P4-6, P4-7, P5-11.

## 1b. Separating "same code" from "same world" (Phase 6)

**What happened.** P2's false alarms matched the report's simulation over 20 seeds, but its detection was 8 points
lower (74% vs 82%).

**What we did.** Ran our node and edge code on the report simulation's own signals: identical result (54/63 fires,
same tuned threshold). So the code was not the cause. Then swapped one ingredient at a time: our quiet background with
the report's injected fires recovered most of the gap. Counting haze episodes per seed showed our seeds had drawn more
haze in their calibration days (sampling), and the remaining difference traced to how smoke is carried (continuous
weather wind vs one random wind per fire).

**Lesson.** When results differ, swap inputs one at a time between the two implementations; it turns a vague
"something is off" into named, measurable causes. → [phase 6](phase-6-edge-layer.md), `DECISIONS.md` P6-11.

**Update (Phase 7).** The per-fire wind option was built and made no difference to detection (golden P2 246 → 231
of 324): a direct check showed the fires now lift the same number of nodes in both simulators, so the transport
explanation was withdrawn — the earlier swap difference was within sampling error. Measuring the quiet fast residual
itself showed where the gap sits: haze in the calibration days gives the engine's conformal reference set a much
heavier upper tail, so fires earn less extreme p-values. → [phase 7](phase-7-experiments.md), `DECISIONS.md` P7-9.

**Second lesson.** A plausible cause found by a swap is a hypothesis until an intervention confirms it; test the fix
before crediting the explanation.

**Closing the loop (Phase 7 follow-up).** A full 2 × 2 swap (two backgrounds × two fire sets, one chain) split the gap
into a background part (the engine seeds' haze-heavy calibration windows) and a fire-set part (the report seeds drew
fewer wet-day fires than expected). Checking each ingredient at the model level on fresh seeds found no model
difference, so the gap is recorded as sampling. → `DECISIONS.md` P7-14.

## 2. Stubs that are too naive to be useful

**What happened.** The Phase 0 CUSUM stub, fed realistic Phase 2 signals, raised about 2,000 false candidates a day;
the recording ballooned and the map lit up.

**What we did.** Kept the stub (it is v1's behaviour, and therefore a faithful picture of the report's P1 failure),
kept framework scenarios on clean stub signals, and let the real node layer (Phase 5) fix it through the registry.

**Lesson.** A stub's job is to be safe and simple, not good; its failures can be part of the story. → P0-7, P2-4.

## 3. Specifications have bugs too

**What happened.** Reference values and M-number citations in the SPEC had errors (E-1 to E-5); the FFMC constant was
off (E-6); one sign convention differed from the report's code (E-7).

**What we did.** Recomputed every reference value before coding, verified FFMC against published cffdrs outputs, and
logged each erratum with the SPEC version bump.

**Lesson.** Verify the reference values themselves before writing tests that depend on them. → `DECISIONS.md` errata.

## 4. Reproducing hindsight in a tick loop

**What happened.** The report's simulation computes some quantities using the whole first day (baseline
initialisation), the whole calibration period (conformal sets) or data both before and after a moment (the
common-mode mask). A minute-by-minute simulator cannot see the future.

**What we did.** Buffered the first day and replayed it (exact equality from the end of day 1); used online calibration
during the calibration days (identical p-values afterwards); documented the one place a causal loop must differ (the
60 minutes after the tuning window).

**Lesson.** Separate "same algorithm" from "same information"; where the information differs, measure the effect and
write it down. → P4-2, P5-3, P5-4.

## 5. A young network is not the designed network

**What happened.** Short demo recordings (1–3 days) show a network with little calibration data and a default
threshold. In `node_3day` only one node flagged the fire.

**What we did.** Added warm-start recording: simulate 31 days, record the last three. The mature network detected and
confirmed the same kind of fire.

**Lesson.** Demonstrate a system at its operating point, and say so on screen ("recorded from day 29"). → P5-14.

## 6. A weakness in the method itself

**What happened.** On seed 22, the rule that excludes network-wide events from threshold tuning missed a second haze
rise right after a long one, and tuning hit its cap.

**What we did.** Diagnosed it to the slow baseline's inflated spread after a long episode, confirmed the report's code
behaves the same, logged it in the improvement backlog with a proposal, and kept the report's method as the default.

**Lesson.** Faithful reproduction and improvement are different jobs; do the first, then the second, and keep the
finding visible. → P5-10, `KNOWN_ISSUES.md`.

## 7. Keeping accepted work stable

**What happened.** New phases kept needing small changes in files from accepted phases (the pipeline, configuration,
dashboard shell).

**What we did.** Real models went into new files beside their stubs; contracts only gained fields; each touch of an
accepted file was listed in the plan, approved and logged ("files touched" entries in `DECISIONS.md`). A Phase 0 test
that used `qcc` as an example of a stub-only module was updated when `qcc` gained a real version.

**Lesson.** Additive change plus an explicit list of touched files keeps a growing codebase reviewable.

## 7b. Optional fields and strict checks (Phase 6)

**What happened.** Adding an optional `incident` field to the escalation output made the runner's strict "one entry
per cluster" check reject the stub's empty field, silently degrading the module in every stub run.

**What we did.** Contracts now declare which additive fields may stay empty (`OPTIONAL`), and the check iterates only
real dataclass fields.

**Lesson.** Additive contracts need the validators to know what "additive" means; test every module state (the
contract test runs all-stub, all-off and all-real configurations, which is how this was caught).

## 8. Tooling surprises

| Problem | Resolution |
| --- | --- |
| vitest 4.1.x failed to install with npm 10; older versions carried a security advisory | vitest 5 (Dep-2) |
| echarts 5.x carried an XSS advisory | echarts 6.1 (Dep-5) |
| A week-long recording was 11 MB compressed | three-day scenarios; later, the real node layer cut event volume |
| A pattern-based `pkill` killed the shell running it (Phase 2, and again in Phase 8 with `pgrep -f`) | list processes in one command, then kill the exact process ID in another |
| Bars cannot be drawn on a log axis (the energy chart was empty) | lollipop stems from the axis minimum (Phase 8) |
| Browsers block module scripts from `file://` | serve the static build (`npm run preview`); offline `file://` planned for Phase 10 |
| Chart polish: default legend colours, misaligned axis labels, clipped labels | explicit series colours, custom axis values, wider margins |
