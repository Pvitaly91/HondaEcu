# M1i — Stateful capture-sequence validation

Bounded seeded ROM execution, not an ECU emulator, timer simulator, new GUI,
hardware measurement or physical RPM validation. `physicalRpmAvailable=false`
and `PcInspectionOnly / NotFlashReady` remain mandatory. GUI r3 stays paused /
NotRun. No new BIN is created.

Base: `origin/codex/p28-conditional-rpm-planner-m1h`, commit
`b254803f41c02acc2a4b13974267bec25f8b09ba`. Work branch:
`codex/p28-capture-sequence-validation-m1i`.

## Source-reviewed normal acquisition

Existing private original/listing correspondence: 56 selected instructions,
140 bytes, zero discrepancies, including caller anchors. This is not factory
identity or whole-program reachability. ROM bytes, listing, binding and traces
remain private.

Entry `56BE`; stop **before** `5719`. That address is not RT; the enclosing
routine continues to return at `5801`. Allowed ranges are `[56BE,56DF)` and
`[5701,5719)`. Normal requires `DATA011F.2=0`, including the first-observation
path. Alternative acquisition/divide-six is UnsupportedMode before fetch.
The mode/range guard is separate from the exact-form whitelist.

Entry context: LRB `0021`, SCB 2, USP `0280`, explicit PSW `1102`, budget 128.
Caller anchors establish bank/stack context, not constant incoming arithmetic
flags. SSP `07FE` is a technical unused seed, not a recovered caller stack.
This slice neither calls nor returns. Instruction counts do not advance time.

`Acquire(observation, previousState)`:

1. Read TMR2; save to er3. At LRB `0021`, er3 aliases `010E/010F`, so `010F.7`
   is the **new timestamp's bit15**, not an independent overflow stimulus.
2. If bit15 is clear, read IRQH.0; when set, increment byte `00AE` and set
   `00B6.0`. Do not synthesize IRQ from low-word wrap.
3. Set `0128.3`, testing the old bit. If previously clear, preserve samples and
   staging `0136`; do not read TCON2 or write a sample.
4. Otherwise compute `(TMR2 - previous00EE) mod65536`; read TCON2.2/TCERR and
   replace with zero if set. Store to `0136` and word `0360 + 2*DATA00A2`.
   Only explicit indexes 0..5 are admitted.
5. Save capture to `00EE`, clear `00AE`, retain guard/unrelated bits and every
   unwritten sample slot.

Dispositions: FirstObservationNoWrite, IntervalWrite, InvalidZeroWrite,
UnsupportedMode, UnresolvedInstruction, ExecutionError, BudgetExceeded, NotRun.
Both TCERR and zero difference write a zero sentinel; supplied/read observations
distinguish their causes. Same-value executed stores still count as new writes.
Six captures from uninitialized history produce five writes, not six samples.

C# evolves its own expected history, never from Rust checkpoints. Every event
compares disposition, ordered peripheral reads, actual stores/widths/addresses,
previous timestamp, flags, staging, six slots, selected timestamp/index and PC.
Reports retain expected states, per-slot write counts and warm-up (all slots
actually written and currently nonzero).

## Frozen SFR semantics and exact ISA fixes

| Read | Address | Width | When |
|---|---:|---:|---|
| TMR2 | `003A` | 16 bits | Every admitted capture |
| IRQH | `0019` | 8 bits | New timestamp bit15 clear |
| TCON2 | `0042` | 8 bits | Already initialized |

Unknown non-CPU SFR accesses, wrong widths and all peripheral writes fault.
SFRs are not RAM. Snapshots are enabled only for acquisition, never silently for
old tasks or downstream G/F/threshold. Reads do not advance time/change values.

Primary user-manual printed pp41–43 establish widths; pp84–85 and 90–91 describe
capture; pp164–167 identify IRQ bits and reset at interrupt entry. IRQH.0 is
Timer2 overflow, not capture interrupt. No read-clear/latch-release is documented
for these frozen reads without new events/reset/interrupt entry. The TCON
read-modify-write race warning does not authorize writes in this slice.
TCERR's mode-C long boundary is FFFF ticks or more. No IRQ races are modeled.

The existing [OKI instruction manual](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/Oki_66201_Instruction_Manual.pdf)
and private user pages support a whitelist of 23 exact forms, not mnemonic-wide
admission. EXTND sign-extends AL and sets DD=1; valid doubled indexes have clear
sign bits. SB sets ZF from the old bit. Three decoded tests failed before fixes
and passed afterward:

| Exact form | Minimal fix | Source |
|---|---|---|
| Word SUB A,N8 | HC on low-nibble borrow | instruction 3-156; user p33 |
| INCB N8 | HC on low-nibble carry; preserve CF | instruction 3-61; user p33 |
| Byte SLLB A | Preserve ZF/HC/DD; update CF only | instruction 3-144 |

Runner 0.4.0 adds those three to the prior 13 fixes. Historical 0.3.0 checksum
receipts retain their old compatibility inventory, not relabelled execution.
Acquisition requires 0.4.0. Neither ADD evidence/permission is broadened.

## Stateful composition and child admission

CPU/RAM initialize once per image/scratch pattern (`00`, `55`, `AA`). Baseline
and verified child execute their entire own images in independent instances.
Harness changes only snapshots, explicit index/context schedule, PC and declared
entry registers. G reads actual ROM-written samples, F actual G state, threshold
actual F code. C# never injects expected samples/T/code.

Boundaries: G `0772 → 07A5`; F `07C7 → 0822`; threshold `122C → 126D/1281`.
Skipped caller/main-loop ranges are not executed. Threshold enable/context/prior
bits are per-event stimulus, not recovered IRQ scheduling or full hysteresis.
Initial-only gate preconditions and entry resets are explicit report metadata.

Composition requires `scheduled-g-f-threshold` and selected `compose=true`
observations. Acquisition-only rejects compose points. Strict G stops at er1
ADD; F/threshold and remaining captures are NotRun. er1 does not authorize er3.
No stopped sequence resumes next capture. Separate acquisition-only runs are
independent evidence, not continuation. Stage-new and cumulative assumptions
remain visible; later fallback/no-composition cannot erase earlier dependencies.

Child uses existing M1g parent/binding/plan/export receipt/reviewed compensation
definition. No new binding/key/authority/BIN. Comparison checks acquisition/G/F
equality, exact expected changed predicates and selected executed instruction
extents plus program-data reads. Speculative decoder lookahead is not executed
evidence. Compensation non-access here is bounded, not a global unused proof.

## Exact source and unchanged M1h envelope

Tick-only scenarios need no clock/RPM inputs. Optional timeline specifies integer
origin, phase in `[0,1)` and one exact nonnegative rational per transition:
`capture[n] = floor(origin + phase + sum(period[0..n-1])) modulo65536`.
Uniform periods reduce to `floor(phase+n*p)` with explicit integer origin.
BigInteger arithmetic avoids double accumulation. Timeline must reproduce every
TMR2 word. Without extended stimulus, overflow counts are not inferred from low
words. Supplied TCERR/IRQ remain stimulus; inconsistent idealized flags are
forced/unverified, not physically reachable ECU claims.

Optional envelope comparison reuses unchanged M1h forward evaluation with explicit
scenario/query, retained provenance/digests and identical permissions. Every slot
needs an actual valid write from the same period before FreshUniformSteadyHistory.
Startup/stale/invalid/alternative/mixed-period transient histories are outside
scope. Compare samples and completed G/F; unresolved/NotRun comparisons are null,
not passed. Selected phases cannot narrow combinations, inverse intervals or
minimax policy. No hardware defaults are added.

## CLI and bounds

```text
hondaecu research p28-vtec acquisition-check <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <private-binding.json>
  --runner <rust-runner> --scenario <private-scenario.json>
  --output <new-private-report.json>
```

- `--composition acquisition-only|scheduled-g-f-threshold` (default acquisition-only).
- Separate `--allow-assumption oki.add-er1-a` and `oki.add-er3-a`.
- Complete child tuple: `--derived`, `--plan`, `--export-report`, `--compensation-definition`.
- Envelope: `--envelope-scaling`, `--envelope-slot`, optionally `--envelope-rpm`
  with `--envelope-rpm-provenance`.

Scenario formatVersion 1: purpose `explicit-capture-observation-stimulus`,
provenance, initialState, observations, traceObservationIndexes, optional timeline.
Untrusted stimulus, not a trusted profile. Bounds: 1 MiB strict UTF-8, depth12,
1..1024 dense observations, six sample words, indexes0..5, eight unique selected
trace witnesses, bounded rational components/denominator growth. Closed schema
rejects missing/unknown/duplicate/null fields.

Existing adapter retains strict JSON, response/log bounds, timeout, cancellation
and process-tree cleanup. Detailed traces only for selected witnesses and first
failure/mismatch. Diagnostics replay original state/full prefix, not observed
intermediate seeds. Publication uses new paths and input-change checks. Exit0
means no measured mismatch/error, not that conditional/unresolved/unsupported/
NotRun stages passed.

## Validation record

The private harness completed ten reports, each with separate baseline/verified
M1g child and three scratch patterns (60 independent sequences, 1872 requested
observation checkpoints). Detailed scenarios, checkpoints and selected traces
remain under ignored M1i reports; counts below exclude diagnostic replays and
the separate CLI repetition.

- Acquisition-only normal runs: 46-event mechanics and 25-event integer steady
  sequences, 426 strict capture matches and 414 actual sample stores across
  both images/patterns. G/F/threshold are all NotRun. Initial captures do not
  write; slots become fully refreshed only at index 6, not index 5.
- Mechanics includes steady208 ticks, short wrap from origin65000, zero delta,
  shorter104/longer416, explicit70000-tick long interval with TCERR, a separately
  forced TCERR snapshot, step change, gradual120→208 periods and recovery.
  All indexes0..5 are exercised; supplied IRQ flags are not inferred races.
- Composed strict mechanics stops at G on index 6 in every image/pattern; the
  remaining 39 captures per sequence, F and threshold remain NotRun. er1-only
  instead completes G conditionally and stops at F; the same suffix is NotRun.
- Both permissions complete mechanics plus steady integer208, rational625/3
  at phases0 and 2/3, and a separate integer324 predicate witness. Each steady
  scenario has 25 observations/24 actual stores per image/pattern, with 19
  scheduled G/F/threshold evaluations after fill. No expected T/code is seeded.
- Alternative-mode refusal: six initial UnsupportedMode results, no native
  fetch/read/store, and 12 suffix observations NotRun.

Aggregate stage categories across all ten reports:

| Stage | No-assumption matches | Conditional matches | Unresolved | Unsupported | NotRun |
|---|---:|---:|---:|---:|---:|
| Acquisition | 720 | 666 | 0 | 6 | 480 |
| G | 0 | 702 | 6 | 0 | 1164 |
| F | 0 | 696 | 6 | 0 | 1170 |
| Threshold | 0 | 696 | 0 | 0 | 1176 |

All stages have zero mismatches, execution errors and budget failures. There
are 1332 actual sample stores and 1386 completed acquisition calls. Acquisition's
666 conditional classifications inherit previously used G/F assumptions through
the persistent history; the acquisition instructions themselves use no ADD
permission. They are not additional strict acquisition-only evidence.

Baseline/child acquisition and admitted G/F outputs match. There are 348 completed
paired threshold checkpoints (two predicates each); exactly 12 predicate changes
match the existing one-slot raw patch, including disabled/context/prior-state
controls. Compensation is absent from all observed instruction/data accesses;
this remains a bounded non-access observation, not a new global proof.

The preserved explicit M1h invented scenario is reused without changing its
provenance or hardware assumptions. Across five envelope comparisons, 528 fresh
steady checkpoints match samples and completed G/F; 348 startup/invalid/transient
checkpoints are outside scope. Integer and rational phases remain within the
unchanged conservative envelope. No intervals or minimax policy were narrowed.

Previous M1d–M1h models/policies and checksum/export authority are unchanged.
Preservation checks cover 3338 unique earlier inputs/reports/files, including all
three M1h portable folders and the existing M1g child. GUI r3 remains paused /
NotRun; headless/offscreen tests and CI packaging are not GUI acceptance.

Local Release validation: `HondaEcu.sln` builds with zero warnings/errors;
422 Core and 111 CLI tests pass. `HondaEcu.Windows.sln` builds with zero
warnings/errors; 81 Desktop headless tests pass. Pinned Rust 1.85.1 build/test
passes 78 tests (39 unit, 6 acquisition process, 33 prior integration). Both
explicit .NET solutions pass `dotnet format --verify-no-changes --no-restore`;
Rust passes `cargo fmt --check`. Public tests contain invented programs, not
firmware fixtures. The actual CLI was separately exercised in acquisition-only
and verified-child conditional modes, including optional envelope reporting.

The M1i privacy guard checks public candidate/staged/base diffs, private evidence
identities/paths, full ROM encodings and selected acquisition-byte windows,
repository ignores and protected previous algorithms. It passes; 3338-file
preservation passes. Existing CI runs Linux/Windows builds, Rust tests, actual
synthetic Rust-process .NET tests and clean Desktop publication. CI result for
the pushed SHA is reported separately; its artifact is not GUI acceptance.
One intermediate build collided with the read-only privacy process's assembly
lock; the sequential retry completed with zero warnings/errors.
