# M1j — Stateful VTEC software decision validation

M1j adds `research p28-vtec state-check` and one `statefulVtec` task to the
existing Rust runner. Each image/scratch sequence owns one CPU/RAM lifetime.
The independent C# model owns a separate history; neither history is realigned
to the other or to the baseline after a changed-child transition.

Base: `origin/codex/p28-capture-sequence-validation-m1i` at
`e5637e6baabb6d83c0fd6ad29abec91648aae6bd`; working branch:
`codex/p28-stateful-vtec-decision-m1j`. No implicit main/HEAD base is used.

This is a finite software experiment, not full ECU logic or physical VTEC
activation. `physicalRpmAvailable=false`, `PcInspectionOnly / NotFlashReady`.
GUI r3 stays **paused/NotRun**. No GUI, BIN, repair, definition, signing key,
compensation location or export workflow is created or changed.

## Evidence and exact boundary

The unchanged private baseline/listing and existing verified M1g child were
used. A private audit checked 176 listed instructions against actual ROM bytes,
including decision/helper bodies and selected initialization/external writers.
Static reference searches include direct, off-page, USP-relative and indexed
producer leads; they are not a proof excluding every arbitrary pointer write.

| Contract | Entry | Stop before | Context and bound |
| --- | --- | --- | --- |
| Software decision | `122C` | `12FC` | Code `[122C,12FC)` and helper `[5839,586E)`; budget 512 |
| Byte decrement body | `5BD0` | `5BD9` | Explicit X1 target; budget 4; no surrounding interrupt-control sequence |
| Saturating increment body | `3CEB` | `3CF3` | DATA00F3; budget 4 |

The decision starts with PSW `0101`, LRB `0020`, SCB 1, r0..r7 at
DATA0100..0107, off-page DATA0100 and USP `0280`. SSP `07FE` is a technical
initial seed for the bounded helper call, not a recovered live caller stack.
Only PC, PSW, LRB, USP and explicit software inputs are reset at each entry;
the stack and persistent fields are not reseeded. No inserted RET/NOP/jump is
used. The helper runs actual table lookup, byte multiplication/division and RT.
Execution stops on exact-form refusal, access fault, unexpected escape or
budget exhaustion; all later calls are NotRun, without applying their inputs.

P1 is reached before DATA0127.2 on both output paths. The existing manufacturer
user-manual scan, printed pages 66–69, establishes P1 as an 8-bit data register,
P1IO as its direction register, and direction-dependent reads/RMW. Startup at
`25A8/25AC` writes the output data and all-output direction. The narrow runner
therefore explicitly assumes this initialized **all-output, no-external-bus
mode** and models only the output-data register at DATA0022. Byte reads return
the output data, not a fabricated input pin. Wrong widths, P1IO writes and
other unknown SFRs fail. There is no pin, load, ASIC, feedback, interrupt or
solenoid model, and no claim that full startup was executed.

## State ownership

The RAM-clear loop at `2706..2728` is an initialization writer for the fields
below; startup routes and unrelated retained-memory behavior are outside the
executed contract. An explicit initial software state is seeded once instead
of claiming that the harness reproduced a boot.

| Field / role | Set or written by | Readers | Persistence / clear | Remaining unknowns |
| --- | --- | --- | --- | --- |
| DATA0131.0, persistent prefix predicate | `1241` | `1233`, `129B` | Recomputed only on enabled path; disabled preserves it | Raw DATA00CC physical interpretation |
| DATA0131.1/.2, persistent pair predicates | `125E`, `126A` | Prior selection `1257/1263`; downstream `12A4/12C4` | Updated by ROM, once-seeded prior; disabled preserves both | Not physical ON/OFF flags |
| Other DATA0131 bits | Other prefix/table procedures, e.g. `1110/111C`, `23DC..23F5` | Their own consumers | Preserved by this contract | Those producers are not scheduled here |
| DATA0198, derived byte | Helper result stored at `1272` | `12B2` | Retained on disabled path; overwritten on enabled path | No physical unit established |
| DATA0127.2, persistent request mirror | `12EB`; clear `12AD/12D1` | `12B8` | Changes with executed P1.0 request branches; external clear at `410C` | External reset path not scheduled |
| P1.0, software output-data request | `12E8`; clear `12AA/12CE` | `51D1` and port snapshots | Output data survives calls; external clear `4108`; startup initializes register | Electrical/actuator effect unestablished |
| P1.1, preliminary software permission output | `1286`; clear `1281` | Port snapshots | Separate from request; may remain set while request is clear | Not physical enable confirmation |
| DATA0127.1, persistent selection status | `12F9`; clear `12DF` | `12A7`, `131A`, `17AE`, `185D` | Depends on feedback snapshot and D8/D9 counters, not request alone; external clear `410C` | Feedback source meaning and downstream physical effect |
| DATA01D8 | Reload at `12DB`; scheduled native decrement | `12F1` | No hidden host decrement; zero suppresses decrement store | Actual scheduling period |
| DATA01D9 | Reload at `12F5`; scheduled native decrement | `12D7` | Retained until native decrement/initialization | Actual scheduling period |
| DATA01DF | Reload `12E4`, clear `12CB`; scheduled decrement | `12C7` | Disabled/early-block path does **not** automatically clear this hold counter | Whole-loop interactions |
| DATA00F3 | Saturating producer `3CEB..3CF3`; external clear `4159/415A` | `1289` and other procedures | Persistent counter, not a per-call stimulus; saturation skips store | Upstream conditions of external clear are not emulated |
| DATA011E.3/.4, caller configuration snapshots | Word copy DATA0216→011E at `5C33/5C35` | Context/enable branches | Only these two explicitly scripted bits supplied at entry | Whole configuration producer not executed |
| ROM60E6, ROM configuration lead | Read at `5F46`, shifted into DATA0216.4 at `5F4B` | Subsequently copied enable snapshot | ROM unchanged | Not an independent Boolean at every cited ROM address |
| DATA0216.3 upstream context state | `7B45` from prior carry | Snapshot copy and other consumers | Upstream software producer excluded | No physical context label inferred |
| ROM60FA, configuration gate | Read at `1295` | Branch `1299` | Each image reads its own unchanged byte | Opposite configuration branch has synthetic coverage only |
| DATA0119, DATA011A word, DATA011C byte | Software producers/snapshot copy (`2896`, `2DD0`, `5C2B..5C31`) | Downstream masks/branches | Explicit scripted software snapshots, not resets of modeled latched faults | No oil-pressure/TPS/MAP/DTC labels asserted |
| DATA00CC, DATA00D9, DATA0132, DATA0199 | Unexecuted upstream calculation/snapshot writers | Prefix, raw limit and adjusted comparison | Explicit raw software inputs only | Sensor units, timing and complete producer contract |
| DATA0133 | Raw compact-code stimulus in VTEC-only mode | Thresholds and interpolation | Explicit input per call | Not confirmed physical RPM |

The external reset at `4108/410C` and external F3 clear at `415A` are recorded,
not silently simulated. To study such upstream paths requires their own
entry/state/admission contract. No arbitrary host reset/decrement is called
firmware behavior, and unmodeled latched faults are not cleared by the harness.

## Gates and interpretation

The complete gate registry reports actual branch outcomes and actual comparison
operands, plus a separate execution-order list. `True` means that particular
branch was taken (or the comparison produced borrow), **not** generally that
VTEC is allowed. A skipped gate is `NotEvaluated`, never a listed blocker.

1. DATA011E.4 clear selects disabled output handling and preserves threshold
   state. Enabled processing first updates the raw DATA00CC prefix predicate.
2. DATA011E.3 selects neutral context 0 when set, context 1 when clear.
   Each pair selects the even byte when its own old state is set and the odd
   byte when clear. `compactCode > selectedThreshold` sets its new bit;
   equality clears it. The two prior states are never supplied per call.
3. Helper `5839` interpolates a descending raw key/value table selected with
   the context and stores DATA0198. This is not a sensor conversion. Table
   reads are bounded; an actual DIVB zero divisor is an unresolved boundary,
   not a manufactured numerical result.
4. DATA011A word mask and DATA011C byte mask precede P1.1. Subsequent ordered
   checks use DATA00F3, raw DATA00D9, ROM60FA, DATA0131.0, context and
   DATA0119.5. `1292` is the immediate byte of the comparison starting at
   `128F`; it is **not** a standalone Boolean enable.
5. Pair 0 admits the adjusted DATA0198-minus-DATA0199 path. Existing request
   state selects an additional raw margin; borrow paths clamp the byte to
   zero. Comparison with raw DATA0132, then pair 1, may reload the hold counter
   and set the request. Otherwise the existing hold counter can retain it.
6. DATA0119.1 is a scripted software snapshot bit used on feedback-related
   branches; its physical meaning is unestablished. Together with D8/D9
   it controls DATA0127.1. Request, this selection status, and actual mechanical
   movement are distinct. The next unrelated procedure starts at `12FC`.

The identified DATA0119 writers read DATA4700, XOR the byte with `1A`, then
copy it to DATA0211 and DATA0119 (`288E..2896`, `2DBD..2DD0`). That upstream
read/processing is not executed here. Naming a downstream branch
feedback-related does not establish what DATA4700 or a physical input means.

“Fast” and “slow” are schedule-group identifiers only. The recovered native
decrement callers cover D8/D9 (`2A02..2A08`) and DF (`3CD9..3CDF`); the latter
group also precedes the F3 producer. Each stimulus explicitly requests a count
of these narrow body executions. No call count is labelled milliseconds and
no main-loop frequency or interrupt interleaving is invented.

## Instruction evidence and compatibility

The existing [OKI instruction manual](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/Oki_66201_Instruction_Manual.pdf)
and its independently packaged chapter scan were inspected visually. Evidence
is per opcode pattern, DD, width, addressing and flags, not mnemonic membership.
`stateful_forms.rs` is the explicit registry; old task registries are unchanged.

| New/reused exact forms | Primary printed pages / qualification |
| --- | --- |
| LB/L, LC/LCB, STB, MOV/MOVB, DP/X1/register aliases | 3-69/70, 3-72/73, 3-85/86, 3-154/155; register-bank/pointing-set tables |
| CMPB direct immediate, accumulator off-page/direct; CMPCB indexed X1 | 3-41/42, 3-48; unsigned byte borrow/ZF, HC preserved |
| AND word immediate / ANDB byte immediate | 3-20 / 3-24; only ZF changes |
| CLRB A `FA` | 3-33: AL cleared, AH retained, DD cleared, ZF set; CF/HC preserved |
| INC DP `72`, DECB indexed X1 | 3-60 / 3-56; ZF/HC updated, CF/DD preserved |
| ADDB A,r6 and A,#byte | 3-16; no carry-in, byte carry and bit-3 half-carry |
| SUBB A,r1/r6/r7/#byte and r0/r6,A | 3-160/161; byte borrow/ZF/half-borrow; object,A byte regardless of DD |
| MULB `A2 34`, DIVB `A2 36` | 3-101 / 3-58; banked r0/r1 and word accumulator, DD preserved; zero-divisor result undefined |
| CAL/RT | 3-29 / 3-125; actual system-stack return; no consumed sequence-flag operation in this scope |
| Reviewed J/JBR/JBS/conditional branches, MB, SB/RB bit forms | 3-62..67, 3-77, 3-114/115, 3-127; byte RMW and old-bit ZF behavior |
| **SUBB A,off N8 `A7 N8`, DD=0** | **Conditional encoding inference only**, detailed below |

The word SUB A,off N8 row at printed 3-156 specifies `A7 N8`; the byte row at
3-160 instead prints an incomplete `C4 N8`. Both local scans show that
discrepancy. The listing/decoder's DD=0 interpretation is plausible but not
promoted to primary-established encoding. Strict execution stops before
`12B4`; conditional execution requires exactly
`oki.subb-a-off-n8-encoding`. Its assumed semantics are unsigned AL minus the
off-page byte, AH/DD preserved, CF/ZF/bit-3 half-borrow updated. No permission
extends to word SUB, other forms, either er1/er3 ADD, or unknown instructions.

Decoded tests were added and run **before** semantic fixes. Private failing
logs identify CLRB ZF and the exact INC/DECB/ADDB/SUBB half-flag defects. Minimal
fixes were followed by boundary, incoming-flag, alias, call/return and previous
affected regressions. The runner is version `0.5.0`; explicit historical
inventories `0.1.0`–`0.4.0` remain accepted for their former tasks, including
old M1g receipts. Version inventory is compatibility metadata, not executable
attestation or hardware validation.

## Command, stimulus and report

```text
hondaecu research p28-vtec state-check <baseline.bin>
  --profile p28-304 --confirm-profile
  --baseline-binding <private-binding.json>
  --runner <rust-runner>
  --scenario <private-state-scenario.json>
  --output <new-private-state-report.json>
  [--allow-assumption oki.subb-a-off-n8-encoding]
  [--derived <existing-child.bin> --plan <existing-plan.json>
   --export-report <existing-receipt.json>
   --compensation-definition <existing-reviewed-definition.json>]
```

Scenario version 1 has purpose `explicit-stateful-vtec-software-stimulus`,
provenance, the eight named initial persistent fields, 1..256 dense calls and
at most eight trace witness indexes. Each call supplies raw compactCode,
context/enable and the named raw/software snapshots in the ownership table,
plus 0..32 counts of each native tick group. Unknown/duplicate/null fields,
per-call persistent-state keys, out-of-range values and expanded permissions
are rejected. No signing or certification layer is added.

Reports compare before/entry/after state, actual selected thresholds, actual
ordered gate events/operands, native counter runs/writes, persistent decision
writes including same-value stores, software outputs and exit PC. Model history
is separate and retained on divergence. Detailed traces are bounded to 128
instructions for selected witnesses and original-initial-state prefix replay
of the first discrepancy; successful ordinary calls do not get full traces.
Request/status is null on unresolved/NotRun, not false. A zero process exit is
not itself a model match.

The existing bounded subprocess transport handles cancellation/timeout/stream
limits. CLI destinations must be new and cannot alias inputs; scenario,
baseline, profile, binding, runner and optional complete M1g tuple are checked
for mutation before report publication. The child is admitted only through
existing full M1g lineage. No BIN is written.

## Finite validation and child effects

Public tests contain only invented programs/data or explicitly labelled
comparator mocks. They cover both contexts/all four initial combinations,
ascending/descending/equality/adjacent values, repeated and alternating inputs,
normal/equal/reversed pairs (including oscillation), disabled/re-enabled state,
gate order/NotEvaluated, native counter scheduling, separate request/status,
strict stop, subprocess execution, mutation detection, malformed scenarios,
cancellation and input preservation. A toy executable that differs from the
model must produce a mismatch, never masquerade as an actual-ROM pass.

The private baseline and verified child were executed using their own bytes
and identical external schedules on scratch patterns 00/55/AA. The first
expected difference is the edited context-0/prior-clear pair-0 selection at
raw code 205. A later unchanged code may still see different prior bits and
choose different threshold bytes; that history is not realigned. Downstream
inputs can expose the change at the software request or mask it. Clearing the
feedback-related snapshot and executing explicit counter bodies provides a
separate convergence witness; this is not a hardware observation.

Actual executed instruction extents and program-data reads are checked against
the existing compensation offset. It is not accessed in these finite runs;
this is a scoped non-interference check, not an inference from zero checksum.
No new repair or B/C BIN is generated. Numeric batch/test/CI totals are recorded
separately from earlier development witnesses:

- Final actual-ROM batch: 16 scenarios, 532 supplied calls per image/pattern,
  96 independent sequences and **3192 checkpoints**; zero model mismatches.
- Complete decisions: **288 strict matches**, **2880 conditional matches**.
  **6 unresolved** strict stops at `12B4`; **18 subsequent NotRun** calls.
  Permissions remain cumulative after first use even if a later call takes a
  path that does not reach the conditional instruction.
- Stateful threshold/prefix state: 3102 enabled calls and 72 disabled
  preservation calls matched, including the threshold prefix before the six
  strict downstream stops. NotRun suffixes are not counted as validation.
- The ten-call request witness differs in persistent state on eight calls and
  in software request on four calls per pattern; all tracked state rejoins at
  zero-based call 8 after an explicit feedback-snapshot change. The masked
  witness has four state differences, no request differences and rejoins at
  call 4. Neither experiment demands the former M1i case-count result.
- ROM60FA remains unchanged, so its nonzero branch is **actual-ROM NotRun**;
  only an invented-data model test covers that alternative configuration.
- Local release checks: **452 Core**, **124 CLI**, **81 headless Desktop** and
  **93 pinned Rust** tests passed. Both explicit .NET solutions build with
  zero warnings/errors. These Desktop tests are not an interactive GUI pass.
- Preservation covers **3434** prior files, including previous reports,
  existing M1g child and protected portable folders. Public candidates and
  diffs are scanned for private bytes/hashes/paths/signatures. CI status is
  reported separately for the pushed commit, not assumed from local tests.

The mandatory VTEC-only check is independent of unresolved G/F ADD forms.
**Actual composed acquisition→G/F→stateful decision: NotRun in M1j.** A new
same-CPU/RAM cross-contract composition has not been added or validated; the
existing M1i composed task remains a separate scripted-prior one-step test.
It is not relabelled as this new stateful contract. M1h still selects one
one-step predicate under its unchanged minimax/scaling policy, not a complete
VTEC transition. A comparison boundary, a persistent software-state transition,
a downstream output-data request and physical switching are four different
claims. M1 is not complete.
