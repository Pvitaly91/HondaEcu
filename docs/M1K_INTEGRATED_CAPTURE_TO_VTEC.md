# M1k — Integrated capture-to-VTEC software execution

Base: `origin/codex/p28-stateful-vtec-decision-m1j`,
`0b40799fb52ff59e0f75f2784e2f20d78d44d1d5`. Working branch:
`codex/p28-integrated-vtec-chain-m1k`.

This is a bounded test schedule on one CPU/RAM per image/scratch sequence,
not recovered ECU scheduling, hardware timing or full boot. It joins actual
acquisition, G, F and persistent VTEC decision bytes; it does not feed expected
samples, T, Code or prior/request state into execution. Physical RPM remains
unavailable; `PcInspectionOnly / NotFlashReady`. GUI r3 is paused/NotRun.

## Shared-state compatibility audit (before integration)

| Field / bits | Producer and permitted writers | Consumers | Harness input / persistence |
| --- | --- | --- | --- |
| DATA0360..036A, six words | Acquisition writes selected slot; G alternative path can replace slots with one | G | Initial state only; never per-event sample injection |
| DATA00EE, 0128.3, 00AE, 00B6.0, 0136 word | Acquisition history/staging, including same-value stores | Later acquisition | Initial state only; preserve all unmodified bits |
| DATA00C4 word (T) | G XCHG at 07A2 | F at 07C7; later G exchanges old T | Initial state only; F consumes actual G RAM |
| DATA0217.4 (S), .7 (alternative G mode), DATA0231.5 | G may clear S and change fallback; .7 retained in this scope | G, F | Initial state only; model preserves full bytes |
| DATA0133 (Code) | F byte STB at 0820, USP-relative with USP0180 | Stateful decision | Initial state only; no post-F host assignment |
| DATA00B8.4 (ExtraBit) | F byte MB at 081D | Later software outside this scope | Other bits retained; report full byte |
| DATA011E / DATA011F | Explicit context/enable update to 011E.3/.4 only; 011F initialized once | Decision / acquisition mode check | Masked byte update must preserve 011E unrelated bits and adjacent 011F |
| DATA0131, 0127, 0198 | Persistent M1j decision predicates/request/status/derived result | Next decision and downstream gates | Once-seeded, never realigned to baseline or model |
| DATA01D8/01D9/01DF/00F3 | Decision plus the existing scheduled native counter bodies | Decision | Once-seeded; no host decrement or invented reset |
| P1 output-data at 0022 | Decision byte writes under all-output/no-external-bus precondition | Decision byte reads; report latch | Persistent latch independent of stage access permission; no pin/plant model |
| DATA00CC/00D9/0132/0199, 0119/011A word/011C | Declared raw software snapshots from omitted upstream producers | Decision | Explicit external event inputs; no inferred physical units or automatic request-to-feedback connection |
| Acquisition local bank 0108..010F | Acquisition, er3 overlaps 010E/010F | Acquisition timestamp/bit15 tests | Not independent DATA010F stimulus; not the decision bank |
| Decision bank 0100..0107; G/F bank 0200..0207 | Native stage instructions | That stage's aliases | Shared RAM retained; banks not cleared between stages |
| SCB1 pointing set 0088..008F, SCB2 0090..0097 | Native instructions and declared entry USP/X1 actions | Register aliases | Acquisition SCB2; G/F/decision/counters SCB1; inactive set retained |
| SSP and helper stack | Decision's native CAL/RT | CPU helper return | SSP07FE seeded once; balance checked, no per-stage repair |

Overlapping writes are checked by byte extent, not just equal starting address.
F's Code store is a byte at 0133, not a word overwriting adjacent raw0132.
Decision reads 011A as a word and 011C as a byte; acquisition reads 011F.2.
Caller updates must not use a word write to 011E or wipe its whole byte.

## Fixed test schedule and omitted caller

Each live event applies its declared raw/software snapshots, then executes:
acquisition → scheduled native counter bodies → optional complete G→F→decision.
The optional item is one Boolean schedule point, not a workflow language.
No later stage/event runs after a terminal stop. Snapshot application is also
suppressed for the NotRun suffix. Previously latched output remains visible
as architectural state, but a non-executed decision's request is null.

| Stage | Entry → stop before | Entry context / scope |
| --- | --- | --- |
| Acquisition | 56BE → 5719 | LRB0021, PSW1102, SCB2, USP0280; explicit slot DATA00A2; only frozen capture interface |
| Counter decrement | 5BD0 → 5BD9 | LRB0020, PSW0101, SCB1, USP0280; X1 explicit D8/D9/DF target |
| F3 increment | 3CEB → 3CF3 | Same counter context; saturation is native behavior |
| G | 0772 → 07A5, helper 7AEC..7AFE | LRB0040, PSW1101, SCB1, USP0180; reads actual samples |
| F | 07C7 → 0822 | Same declared G/F entry context; actual T/S; no capture/P1 interface |
| Decision | 122C → 12FC, helper 5839..586E | LRB0020, PSW0101, SCB1, USP0280; actual F Code; P1 output-data access only here |

PC/PSW/LRB/active USP are explicit stage entry actions, not a claim to have
executed omitted caller instructions. Native instructions initialize their
own working registers. Skipped G→F block 07A5..07C7 updates other history/delta
state and is not executed or simulated. Upstream snapshot producers, actual
IRQ interleaving, external reset paths and scheduler frequency are omitted.
Counter groups are ordered D8/D9, then DF/F3; counts are native body calls,
not milliseconds. The schedule deliberately extends the already documented
M1i stage boundaries and M1j counter schedule, not the firmware scheduler.

## Implementation and independent checking

Runner 0.6.0 adds one domain-specific task to the existing audited executor;
it does not create another emulator. `seed_machine` and shared-field seeding
run once per image/scratch sequence. The existing in-state executor executes
every stage from that image. No isolated acquisition/stateful task is invoked
between stages. The old M1i initial prefix overrides and M1j per-call Code
seeding are absent from this mode. Bus capability changes preserve P1 storage.

The C# composition owns a separate initial snapshot and persistent history.
It reuses acquisition, producer, compact and stateful models; native counter
expectations reuse the existing counter model. G's partial alternate-mode
sample stores, zero fallback/status effects and the byte F stores are compared
explicitly. Every actual checkpoint is compared with this independent history,
never used as the input to its next event. Whole shared-state comparisons and
ordered same-value/byte/word journals detect overlapping writes and reseeding.
Architecture checks cover inactive banks/SCB/USP, native helper return address
and balanced SSP without repair. Actual gate order, comparison operands and
NotEvaluated gates are checked separately from the final request.

The byte audit verified that 273 selected listing instructions in acquisition/G/F/
decision/helper/counter ranges and bounded caller anchors matched the existing
private baseline bytes. This is local byte correspondence, not full caller or
dynamic alias coverage. Native instructions, private ROM identities, receipts,
signatures and disassembly remain private. No additional ISA documentation
search or new instruction semantic fix was needed. A regression first exposed
that refused DIVB was incorrectly included in executed extents; moving extent
accounting after the existing refusal fixes diagnostics, not DIVB semantics.
Selected counter traces now retain up to 128 actual instructions in total.

## Command and closed scenario

```shell
hondaecu research p28-vtec chain-check <baseline.bin> \
  --profile p28-304 --confirm-profile \
  --baseline-binding <binding.json> --runner <rust-runner> \
  --scenario <chain-scenario.json> --output <new-private-report.json> \
  --derived <existing-m1g-child.bin> --plan <existing-m1g-plan.json> \
  --export-report <existing-m1g-receipt.json> \
  --compensation-definition <existing-reviewed-location.json> \
  --allow-assumption oki.add-er1-a \
  --allow-assumption oki.add-er3-a \
  --allow-assumption oki.subb-a-off-n8-encoding
```

Omit all four child arguments for baseline-only execution. Partial tuples and
unadmitted children are refused. B is a local memory copy containing the one
threshold change from the already verified M1g plan; it is neither an export
nor a new trusted baseline. C must pass the existing full M1g lineage admission.
There is no new plan, location, receipt, key, writer or checksum repair path.

The JSON object requires `formatVersion: 1`,
`purpose: "explicit-integrated-capture-vtec-test-schedule"`, `provenance`,
`initialState`, `events`, and `traceEventIndexes`. The exact typed fields are
in [P28ChainScenario.cs](../src/HondaEcu.Core/P28ChainScenario.cs):

- Initial state: acquisition history/six samples, decision's eight persistent
  bytes, shared `data011E`, `data00B8`, `code`, and raw snapshots; all once-only.
- Each event: dense `index`, `tmr2`, `irqh`, `tcon2`, `slot`, `runDecision`,
  `context`, `enabled`, `raw`, `fastTicks`, `slowTicks`.
- Raw object: `raw00CC`, `raw00D9`, `snapshot0119`, `snapshot011A` (word),
  `snapshot011C`, `raw0132`, `raw0199`. Feedback is independent of P1 request.
- 1–256 events, slots 0–5, contexts 0/1, each tick count 0–32, at most eight
  unique selected trace events. Unknown/duplicate/missing/null fields and
  per-event produced-value/prior overrides are rejected; input limit 1 MiB.

The existing bounded process adapter supplies timeout, cancellation and strict
response parsing. Inputs are captured and rechecked before and after execution;
reports require a new destination, never an input alias. Mismatch replay uses
the original initial state and complete prefix, not observed intermediate RAM.
The first terminal event also receives a bounded witness. `execution.trace`
is selected evidence, not a complete instruction-by-instruction log of every
event; executed extents and side-effect journals are retained at every stage.

## Actual-ROM results (2026-09-06)

Eight small schedules were executed in four permission modes. Every combination
used A/original, B/threshold-only memory image and C/verified compensated child,
with separate histories for scratch patterns 00/55/AA. Thus each mode requests
1044 image/scratch events across 72 sequences. Counts below refer to events,
executed stages or completed decisions, never numbers of validated ECUs.

| Permissions allowed | Completed / requested events | Executed stages | Completed decisions (strict / conditional) | First reached unresolved form |
| --- | ---: | ---: | ---: | --- |
| None | 387 / 1044 | 945 | 9 (9 / 0) | G er1 at 077E: 72 sequences |
| er1 only | 432 / 1044 | 1242 | 54 (9 / 45) | F er3 at 07F8: 72 sequences |
| er1 + er3 | 660 / 1044 | 2319 | 282 (9 / 273) | Decision SUBB at 12B4: 45 sequences; 27 complete |
| All three | 1044 / 1044 | 4014 | 666 (9 / 657) | None |

There were zero mismatches, execution errors, budget failures or unsupported
outcomes in this actual-ROM set. Unsupported mode/forms are separate synthetic
regressions, not fabricated actual-ROM passes. `Executed` means a stage stepped
at least one instruction; a zero-instruction refusal is not counted as executed.
`CompletedEvents` requires all scheduled stages of that event to complete;
capture-only events do not count as decisions. For all three permissions, the
4014 executed stages are 1044 acquisition + 972 counter groups + 666 G + 666 F
+ 666 decisions. Other stage slots are explicitly NotRun.

An allowed permission is not necessarily used. In A-warmup, event 0 finishes
strictly through zero-sample fallback; first er1 is event 1 and first er3 is
event 6. In B–H, first G/F are scheduled at event 6. With er1+er3 only, the child
and intermediate stop at event 6 in A/B/E/F/G/H while baseline can continue;
in C-shortening-lengthening they stop at event 12 and baseline at event 13.
D-masked reaches no SUBB and all images complete with the two ADD permissions.
After each terminal stop, later events apply no inputs and decisions report
`softwareRequest=null`, not the retained latch or false. No stopped history is
continued in a different permission mode; each run starts at its own initial state.

Each stage reports its own `usedAssumptions` and the accumulated image history.
For example a later acquisition can be ConditionalMatch despite using no local
assumption because it retains state affected by earlier conditional execution.
StrictMatch, ConditionalMatch, Unresolved, Unsupported, NotRun, Mismatch,
ExecutionError and BudgetExceeded remain distinct report categories; differences
are retained even on a non-completed stage and make `hasFailure=true`.

### Scenario observations with all three permissions

Event indexes are zero-based. Counts in this table are **per single image/scratch
history**, not multiplied by nine. All timings are raw software observations.

| Scenario | Events / decisions | Observed result |
| --- | ---: | --- |
| A warm-up | 7 / 7 | Event 0 sets acquisition history but makes no sample store. Events 1–6 gradually replace all six slots. Partial histories remain visible; first A/C request difference is event 6. |
| B steady | 13 / 7 | Six 324-unit intervals produce T=388, Code=205. Events 6–12 keep A request false and B/C true; prior/request/counter histories are not reseeded. |
| C shortening then lengthening | 31 / 25 | Six intervals each at 400, then 324, then 260, then twelve at 450. B/C request sets at event 12, A at 13. Request equality returns at 13, but D8 differs through 20; shared state rejoins at 21, Code=198, without alignment. |
| D masked | 13 / 7 | The same threshold history splits at event 6, but snapshot011A=4 takes gate1279; all requests remain false. Later request gates, including SUBB, are NotEvaluated. |
| E hold/counters | 13 / 7 | B/C sets hold=20 at event 6. Explicit slow bodies make 20→19→1→0 at events 7–10; raw0132=0 prevents reload. Request clears at 10 while selection status remains true under independently scripted feedback. No host decrement/reset. |
| F disable/re-enable | 14 / 8 | Disable at events 7–8 clears the request through native code, preserves prior and ages hold; context switches to 1. Re-enable at 9 retains history and restores B/C request; context returns to 0 at 11. |
| G invalid/recovery | 16 / 10 | Zero interval at 7 and TCERR at 8 store zero. G falls back to T=65535, F gives Code=1; native decision clears child request but retains selection status. Fresh replacement of all invalid slots restores T=388/Code=205 at 14. No forced recovery. |
| H short wrap | 9 / 3 | TMR2 65324→112 at event 2 is a valid 324 low-word interval under explicit IRQH=0/TCERR=0. No long-gap validity or wrap interrupt is inferred. |

### Reachable raw-patch witness and A/B/C comparison

The witness in B is acquired, not injected: first observation TMR2=1000 writes
no sample; observations 1–6 add 324 and fill six slots. Actual G sums/divides to
T=388; actual F stores Code=205 in DATA0133. At event 6, pair 0 with prior clear
selects threshold 205 in A and the existing raw-patched 204 in B/C. Strict
comparison is false for A and true for B/C. Actual downstream gates then leave
A request false and set B/C request true. The first divergence is the native
pair-0 comparison/store; acquisition/G/F states agree. The later native output
stores, hold and selection updates are recorded, not patched by the harness.
This witness needs both ADD permissions, and B/C also consumes SUBB permission.

D demonstrates that changed threshold predicates do not guarantee changed
request. C demonstrates both delayed request equality and later persistent-state
convergence: identical requests alone do not imply identical histories.

B/C had identical observed execution prefixes, shared and architectural stage
snapshots, ordered stores, gates, traces and requests in every mode. When any
image stops, later pair checkpoints are NotComparable with nullable values,
not a pass, false comparison or invented mismatch. Across the three image pairs
and three patterns, comparable events / decisions / completed stage boundaries
were respectively 387/9/873 (none), 432/54/1170 (er1), 549/171/1791 (er1+er3),
and 1044/666/4014 (all three). For the all-three B/C pair alone this is
348 comparable events, 222 decisions and 1338 completed stage boundaries.
Different pairs can refer to the same execution; these are comparison counts.

No executed instruction extent or program-data read touched the compensation
byte in this batch. This is a bounded observation only, not a new global proof
that the location is unused. Checksum execution is not substituted for decision
logic; M1f remains a separate command and M1g admission/policy is unchanged.

## Regression, preservation and remaining limits

Local explicit Release builds passed with zero warnings/errors:
`HondaEcu.sln` (497 Core + 140 CLI tests) and `HondaEcu.Windows.sln` (81 Desktop
contract tests, no interactive window). Pinned Rust 1.85.1 build/test passed
102 tests. Both .NET solution format checks and pinned Rust formatting are part
of the pre-push verification. The M1k additions include 45 Core, 16 CLI and
nine Rust regressions (eight real-subprocess integration probes plus latch-scope
unit coverage). The large old isolated corpora remain old-task regressions,
not additional integrated actual-ROM samples.

Public tests use invented programs or explicitly model-shaped comparator
fixtures. They cover native Code handoff, persistent prior/request/counters,
P1 scope retention, bank/SCB/stack and word/byte aliases, unknown terminal suffix,
independent C# history, missing same-value stores, wrong operands/gate order,
each image's own early bytes, stopped pair comparisons, actual Rust subprocess,
timeout/cancellation/bounds and stale input refusal. Deliberately different toy
programs produce Mismatch rather than being mislabeled actual-ROM agreement.

The private preservation inventory contains 3594 pre-existing measured files,
including previous ROMs/plans/receipts/definitions, evidence and portable trees.
The pre-push privacy guard checks these hashes, public/index diffs, private
identity/byte leakage and protected M1g/M1h/Desktop/model paths. No previous
private material is overwritten; no new BIN, key, receipt or portable tree is
created locally. The exact commit's CI result is reported with delivery; a clean
CI portable artifact/no-window diagnostic does not mean GUI acceptance.

The completed result is bounded **byte-execution/model agreement**, not two
independent proofs of physical ECU behavior. Both sides may share a mistaken
initial firmware interpretation. The unresolved exact ADD semantics and SUBB
encoding discrepancy retain their separate permissions. Other acquisition modes,
uncovered invalid/helper domains, omitted G-history bridge, asynchronous inputs,
interrupt delivery, caller stack provenance, real scheduler/interleaving, pin
electrical behavior, plant feedback and physical timer-to-RPM interpretation
remain outside this contract. No hardware defaults are inferred.

`physicalRpmAvailable=false`; `PcInspectionOnly / NotFlashReady`;
hardware/full boot **NotRun**; GUI r3 **paused/NotRun**. No Computer Use,
keyboard/mouse or interactive WPF execution was used for M1k.
