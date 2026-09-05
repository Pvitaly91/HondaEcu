# M1h - Conditional RPM preview and inverse threshold selection

Base: `origin/codex/p28-checksum-preserving-export-m1g`,
`625dc20ca42626514a429fd9749146e91a9126f7`.
Work branch: `codex/p28-conditional-rpm-planner-m1h`.

M1h adds a conditional mathematical query over the existing scaling, producer G,
compact F and selected one-step threshold predicate. It does not establish a
physical RPM codec, promote either word-ADD hypothesis, or complete M1/M3.
`physicalRpmAvailable` remains false and all work remains
**PcInspectionOnly / NotFlashReady**.

## Scenario and evidence boundaries

The supported scenario is **uniform steady normal intervals**. All clock,
timer-divisor, event-geometry and events-per-sample quantities must be explicit,
with exact units and provenance. There are no default hardware coefficients.
Missing scaling keeps the raw inspector usable but makes numerical RPM
unavailable, with missing quantities listed. A source or measurement label in an
analyst document is an unverified claim, not authenticated hardware evidence.
In particular, a timer divisor different from the source-derived CLK/32 selector
describes a counterfactual calculation, not this baseline's configuration.

Initialization/zero sentinels, capture overflow/TCERR, aggregate acquisition with
division by six, alternative G mode, mixed or stale histories and unknown
physical modes are outside automatic selection. A representable T alone is not
enough: G disposition, fallback flag and actual output S remain part of the
forward chain. S is not the selected threshold context or its prior-state bit.

The M1e floor/ceiling sample envelope is conservative. It is not a probability
distribution or a proof that every six-sample combination can arise from
successive capture events. Integral ideal ticks have a singleton rounding
envelope. Invalid, fallback and unresolved outcomes remain visible; they are not
silently discarded to manufacture a normal selection candidate.

## Query provenance and CLI

The existing version-1 scaling JSON, including `quantities.rpm`, remains readable.
Its quantities use positive decimal rational components and exact units as in
[M1e scaling](M1E_RPM_PRODUCER_AND_SCALING.md). A new target RPM is a separate
query snapshot; it does not modify the source scenario or silently replace its
recorded RPM. Scenario quantities, requested value, provenance, allowed
assumptions and assumptions actually used remain distinguishable.

```shell
hondaecu research p28-vtec rpm-preview private/oracle/p28-304/base.bin --profile p28-304 --confirm-profile --baseline-binding private/reports/m1b/baseline-binding.json --slot context_0.pair_0.state_0_threshold --scaling private/reports/m1h/analyst-scenario.json --rpm 3000/1 --rpm-provenance "Explicit analyst query, not measured engine speed" --allow-assumption oki.add-er1-a --allow-assumption oki.add-er3-a --output private/reports/m1h/rpm-selection.json
```

The number in this example is a query, not a recommended calibration. `--rpm`
accepts an exact positive integer or `N/D`; an override requires its own
`--rpm-provenance`. Without an override, the query uses the scenario's recorded
RPM and provenance. Neither input file is rewritten. The output must be a new
path distinct from the baseline, binding, profile and scaling file.

Strict model mode is the default. Conditional mode requires separate
`--allow-assumption oki.add-er1-a` and `--allow-assumption oki.add-er3-a`
permissions as needed. A permission is not evidence that an instruction was
reached, the Rust process ran or hardware was measured. There is no allow-all,
arbitrary offset, compensation-definition, runner or BIN-output option on this
read-only command.

The bound private JSON report contains the full Core planning result plus
`BestCandidateForwardPreviews`: one old/new forward view for **every** best raw
candidate. This does not select the first member of a tie. Exit 0 means that an
eligible mathematical best-candidate set exists. Exit 3 writes the explanatory
report but reports unavailable, unresolved or ineligible selection; it is not a
passing hardware or instruction check. Malformed inputs and input/output
protection failures do not publish a report.

## Forward results, intervals and selection policy

The report follows exact scaling to a sample envelope, then existing G, existing
F using G's output S, and `compactCode > selectedThreshold` (false at equality).
It exposes ideal/floor/ceiling ticks, sample configurations, G dispositions,
T/S, Code/ExtraBit, old/new predicates, used assumptions and refusal reasons.

All 256 raw thresholds are considered. Their domains distinguish AllFalse,
AllTrue, Mixed and Unknown/Invalid; Mixed is not a measured probability. Exact
rational endpoints retain open/closed boundaries. No coarse RPM grid or rounded
display value is used to choose a winner, and global monotonicity is not assumed.

Let `K = 60 * (clockHz / timerClockDivisor) * eventsPerSample / eventsPerCrankRev`.
This is the explicit scenario's **sample-tick × RPM** product, not an inverse
formula for T or a fitted Honda constant. The complete normal envelope is admitted
only for ideal sample ticks in `[1, 54613]`, corresponding to RPM
`[K/54613, K]`, with both endpoints included. These bounds come from normal
capture/zero handling and G's integer quotient width: at 54613 exact ticks all
six terms produce valid T=65535 with no fallback; just above this point the
floor/ceiling envelope mixes valid and overflow dispositions. A valid T=65535 is
not silently merged with the identical numeric fallback value.

The inverse partitions every integral tick into a singleton RPM point `K/n`
and every gap into an open interval `(K/(n+1), K/n)`. Every such point and gap is
evaluated. The implementation checks the ordering of resolved compact outputs
over this complete finite partition before permitting the simple policy. It
groups equal-state neighboring atoms without losing endpoint inclusion. For
positive normal histories, permutation-equivalent six-word sums let seven
high-count representatives cover the 64 floor/ceiling vectors during inversion;
the forward preview still exposes all 64 ordered configurations, or exactly one
for integral ticks. This is a computational reduction, not a phase model.

The first policy minimizes the greatest absolute distance from the requested
RPM to the two endpoints of an eligible finite transition band, using exact
rational comparisons. The candidate's `TransitionBand` is the **closed hull** of
its single Mixed region for scoring; the original `Regions` retain the exact
open/closed membership of AllFalse, Mixed and AllTrue, including equality cases.
All equal-scoring candidates are retained. Always-true,
always-false, absent, disconnected or unresolved transitions retain their full
regions and an explanation instead of one invented switching RPM. The policy
is a mathematical approximation for one selected prior-state predicate, not a
claim about complete hysteresis, all VTEC gates or solenoid activation.

An invalid/fallback envelope at the requested RPM also blocks automatic
selection, even if a nearby valid transition exists. The inverse regions remain
visible for diagnosis. Strict unresolved arithmetic is not replaced by a
conditional answer, and granting only er1 does not grant F's er3 assumption.

## Selection to existing M1g plan

A preview does not edit a ROM. An explicit confirmed raw-candidate selection
must pass the original baseline and current-scenario/model/slot checks, then
call existing M1g planning. Its versioned selection provenance links target,
scenario digest, G/F versions, slot/context/prior state, policy, candidate,
interval/error and used assumptions to the resulting plan digest.

This adds no writer or compensation authority. The existing reviewed location,
complete diff, original-parent lineage and strict native execution gate remain
mandatory for any M1g export. A strict checksum pass and conditional RPM choice
are separate statuses. Earlier M1c plans, M1g plans and saved children are not
rebound or modified. Changing query, scenario, slot or model invalidates the
previous selection preview.

The Desktop's **M1h · умовні RPM** tab loads an explicitly chosen scenario;
its two mathematical ADD checkboxes are separate from byte-execution permissions.
The candidate table initially has no selected row. A user explicitly chooses a
member of the complete Best set, confirms its raw byte, and uses
**«Використати цей raw-кандидат у плані»** with a bound original and an admitted
reviewed CompensationLocation. The saved selection document separately records
the open Mixed region and closed policy hull. Save that new provenance JSON
before using the existing M1g BIN-export button: even a strict checksum pass
cannot bypass missing or changed conditional provenance. Scenario, definition,
query, plan and protected paths are immutable job snapshots; stale results and
cancellation do not create export authority. Demo has an explicitly requested
invented scenario, never defaults for a real BIN, and cannot authorize export.

## Validation and remaining physical dependencies

Mathematical unit tests, actual byte-execution/model agreement, native checksum
verification and hardware observations are separate evidence categories.

One actual private example explicitly reused the **invented M1e scenario**:
clock 1,000,000 Hz, divisor 32, three events per crank revolution and one event
per sample, with requested RPM `3000/1`. These are not defaults, measurements or
a tuning recommendation. The derived ideal ticks are `625/3`, the envelope is
208/209 ticks, and G gives T=249 or T=250 with S=false and no fallback. Both
values give Code=248, ExtraBit=false under the two separately permitted ADD
hypotheses. The neutral slot remains
`context_0.pair_0.state_0_threshold`, without a physical ON/OFF label.

The complete minimax best set contains one mathematical raw candidate, **247**.
Its scoring hull is `[62500/21, 625000/209]` RPM and worst-endpoint error is
`500/21` RPM. Within the supported domain the predicate is AllFalse through the
lower endpoint, Mixed strictly between the endpoints, and AllTrue starting at
the upper endpoint. The analyst explicitly confirmed this sole candidate for
the local test; the original stored threshold and private input identities are
not published here. No display rounding influenced selection.

Actual byte witnesses came from `EvaluateForward` at both exact endpoints and
their exact rational midpoint. Each endpoint has one sample vector; the
non-integral midpoint has all 64 conservative ordered vectors. Each vector was
run under scratch patterns 00/55/AA: **198 inputs per batch**, without a new large
corpus or samples chosen independently of the displayed scenario.

| Actual permission mode | G | Same-state G → F | Each baseline/composed threshold image |
|---|---|---|---|
| Strict | 198 unresolved | 198 NotRun | 198 NotRun |
| er1 only | 198 ConditionalMatch | 198 unresolved | 198 NotRun |
| er1 and er3 | 198 ConditionalMatch | 198 ConditionalMatch | 198 ConditionalMatch |

All three batches had zero mismatch, execution error, budget exhaustion and
unresolved-model results. Only the both-permission batch completed predicate
comparisons: its actual and independently predicted changed-case sets both
contained 192 of 198 pairs. Unresolved/NotRun rows in the other batches are not
predicate passes. All 1,584 observed threshold program-byte reads excluded the
admitted compensation byte, including word overlap. The existing protocol runs
G and same-state F from the original, followed by separately seeded baseline
and composed-image threshold stages; it does not claim full G execution from
the derived image or actual acquisition/hardware timing.

The confirmed candidate passed existing M1g planning and composition admission
in memory, with versioned selection provenance linked to the exact plan. A
separate native-checksum validation completed **6 strict matches**, each with
512 invocations and full coverage, for the original and composed image across
three scratch patterns. This did not remove the conditional status of RPM.
Ten original inputs, including both earlier saved children, were preserved;
**no new BIN was written in M1h's local example**. Hardware and full ECU boot
were NotRun. Private plans, reports, hashes and traces remain ignored.

A separate real-baseline **headless Desktop/service** check completed the
explicit raw-247 transfer, two-byte plan, new provenance JSON/readback, refusal
to export before provenance was saved, protected-original write refusal,
stale-request invalidation and rejection of the earlier M1g child as a new RPM
baseline. It added six strict checksum sequences, bringing the M1h local total
to **12**, without writing a BIN. This was not GUI interaction.

The CLI suite passed **84 tests**, including 25 new M1h cases: explicit/missing
scaling, exact query override/provenance, independent permissions, invalid-target
refusal, preserved input files, new output paths, cancellation, and forward
old/new views for the complete best-candidate set. Public tests use invented
fixtures, not this OEM input or a reconstructed firmware procedure. Final
solution, Rust, packaging and GUI outcomes are recorded separately in the task
results; no pending category is inferred from these tests.

Both local .NET solutions built with zero warnings/errors: **349 Core, 84 CLI
and 81 Desktop tests** passed with no skips. The unchanged pinned Rust runner's
**62 tests** and Rust formatting also passed. Offscreen layout includes every
Desktop tab at the three existing equivalent viewports. These remain separate
from actual GUI smoke, portable startup and the pushed commit's public CI.
The populated candidate-table regression exercises strict and conditional
previews. Its read-only checkbox bindings explicitly use OneWay, fixing the
WPF exception found during the first M1h portable GUI attempt.

The real read-only CLI also ran successfully on the preserved original and this
explicit analyst scenario, producing a new conditional private JSON report with
the single best candidate and its old/new forward view. It retained the source
scenario and explicit query provenance separately and performed no additional
byte execution, checksum run, plan publication or BIN write.

Future physical confirmation requires matching board identity and clock
measurement/routing, capture-edge wiring and crank-event geometry, verified
acquisition mode/history and timing, plus independent evidence for the two
word-ADD forms. A successful interpreter comparison cannot confirm supplied
clock or sensor quantities. Hardware and full ECU boot remain not-run.

Portable publication must use a new folder such as
`artifacts/desktop/win-x64-m1h-r3`, preserving all earlier packages. GUI interaction,
offscreen layout, ViewModel/service tests and no-window diagnostics are reported
separately. A previously stopped GUI test is not retried without permission.
