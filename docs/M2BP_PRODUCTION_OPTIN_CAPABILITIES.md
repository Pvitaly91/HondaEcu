# M2bp — Narrow opt-in production Bus/Exec capabilities

This document specifies the closed interface and its required proof gates.
It is not itself runtime evidence or an acceptance receipt. Source-bound CI
canonical artifacts and the separate last-written private delivery report
establish which gates actually passed.

## Scope and evidence boundary

The exact historical base is
`1ceec589ee8586727fb16a39fd15875444d6feab`. The active branch is
`codex/p28-word0196-optin-production-bus-exec-m2bp`.

The production crate keeps version `0.43.0`, protocol 1, its 38 ordered semantic
fix identities, and an empty default feature set. The new
`p28-word0196-audit` feature exposes a bounded opt-in `audit::Session` interface.
It is not enabled by the CLI or Desktop. The research executable accepts only
source-bound invented cases; it has no file, ROM, BIN or HEX loader.

The new interface uses the real production `Cpu`, `Bus`, shared decoder matching
kernel and the same post-decode instruction implementation as legacy
`exec::step`. There is no copied instruction dispatcher. Source transition
checks must compare the complete preexisting `Exec` semantic body and
post-decode execution tail with the immutable baseline, in addition to actual
default-mode behavioral comparison. Source equality alone does not establish
runtime compatibility.

This milestone does not execute the full M2bj 51-byte stream through the new
production interface. Its identity remains
`91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1`.
The separate 51-byte PROGRAM mapping canary contains invented opaque `A5`
bytes, is not M2bj, and is never decoded or stepped.

## Three independent QA scopes

| Scope | Source tree | Required evidence |
| --- | --- | --- |
| `HistoricalPinnedBaselineQA` | Separate checkout at exact M2bo base | Actual unchanged historical validators, contracts and source pins |
| `ActiveTreeDefaultModeQA` | Actual active production sources, feature off | Full existing gates plus compiled baseline-versus-active differential |
| `ActiveTreeOptInCapabilityQA` | Actual active production sources, feature on | Closed inputs, frozen independent expectations and actual Bus/Exec observations |

Old validators derive their root from their own file paths. Changing only the
working directory does not redirect their source bindings. CI therefore invokes
the unchanged historical files in the separate exact-base checkout. No old
source pin is replaced, suppressed or reassigned to the active source tree.

Expected old-source-pin differences are classified as
`OldSourcePinConflictExpectedAfterVersionTransition`, never reported as a
historical validator passing on the active tree. The new source manifest records
each authorized old/new identity, reason, changed functions and semantic impact.
All unrelated historical sources must remain byte-identical.

The source manifest distinguishes committed Git-blob identities from the
pre-existing protected local filesystem identities. Exactly three unrelated
XML project files had different CR-before-LF bytes in the Git-clean local tree:
`src/HondaEcu.Cli/HondaEcu.Cli.csproj`,
`src/HondaEcu.Core/HondaEcu.Core.csproj`, and
`tests/HondaEcu.Cli.Tests/HondaEcu.Cli.Tests.csproj`. Both immutable identities
and the exact CR insertion positions are recorded. Only those closed raw-byte
identities are admitted; there is no general source normalization or mutable
hash alias. Historical validators still use the exact committed checkout.
Local preservation must retain the original filesystem bytes, not replace them
with the committed representation. Neither tree nor any old source pin is
rewritten. This representation proof is not itself behavioral QA: the actual
effective MSBuild-property and compiled .NET controls remain required.

## PROGRAM mapping and decoder observations

`ProgramSegment` owns immutable bytes, verifies their actual SHA-256, checks the
nonempty 16-bit address extent and translates only by `address - base`.
Microfixtures have physical and logical PC `0x1000`; no PC relocation, 4096-byte
prefix, padding or continuation stub is used. Bounds failures latch a typed
fault before servicing the byte.

The checked decoder and legacy decoder share one matching kernel. The legacy
callback is infallible; the opt-in callback propagates the first typed PROGRAM
failure. Missing bytes do not become zero. No panic catch is used to mask
unrelated failures.

PROGRAM events preserve acquisition order and the purpose at acquisition:

- `DecoderProbe` is the actual callback attempt.
- Post-selection `SelectedExtent` or `DecoderLookahead` is an association on
  that existing event, not a newly claimed historical callback.
- `ArchitecturalSelectedFetch` is a separate actual selected-byte acquisition.
- Diagnostic PROGRAM probes remain distinct.

Events retain attempted address, checked segment/instruction offsets, selected
length, serviced status and exact refusal. Selected index, form, operand fields,
DD mode and extent must match the frozen instruction identity before execution.
No full instruction stream is serialized in canonical observation records.

## Independent DATA permissions

The research admission boundary validates the entire entry snapshot and its
inventoried DATA bytes before deriving the profile. It does not grant rights
from the caller's profile string. A mismatching declared profile is refused
before constructing the execution session.

| Profile | Validated entry predicate | Logical reads | Byte writes |
| --- | --- | --- | --- |
| A | LE16 DATA0196 < 00C0 | 0108, 018E, 0196/0197 word | 018E, 0117, 018F |
| B | NotBelow and DATA012A.7 set | A reads plus 0117, 012A, 018F | 018E, 0109, 0117 |
| C | NotBelow, first gate clear, DATA0124.5 set | B reads plus 0124 | B writes |
| D | NotBelow and both gates clear | C reads | B writes plus 012A, 018F |

All listed reads except DATA0196 are 8-bit. DATA0196 is exactly a read-only
16-bit little-endian access; its `00C0` comparison immediate is not a RAM read.
Logical widths and raw constituent rights are checked independently. Unsupported
SFR and out-of-inventory rights are not inferred from a shared DATA range.

RMW writes require an actual earlier functional read with matching PC,
instruction identity, address and width. Seed and diagnostic operations cannot
satisfy this obligation. Same-value writes remain real writes with fresh logical
and raw write ordinals.

An addressed public DATA request refused before reaching the production Bus
has a separate `data_admission_refusals` entry: actual phase/PC, address, width,
direction and requested value, with `production_bus_called=false`. This records
the real API attempt without fabricating a functional or raw memory access.

## Closed corpus and independent expectations

All original 468 M2bo input requests remain unchanged and separately identifiable.
The stricter predicate-derived policy classifies 84 of them as incompatible
microcontexts. Those are explicit expected admission refusals, not hidden skips.
The remaining 384 are compatible. There are 84 separately named D-compatible
invented controls, preserving the original instruction bytes, flags, aliases and
register contexts while explicitly selecting a compatible DATA predicate.

The closed input inventory therefore has 552 rows: 468 positive microsteps and
84 retained old-context refusal controls. All 16 exact forms and 234 paired
internal-SF positive contexts are covered. These are isolated microprobes; this
does not assert that every microcontext is reachable on an M2bj composite path.

There are also 25 finite malformed/admission inputs. Their expected codes and
details are frozen according to actual validation precedence. Two metadata-only
inputs are counted separately from 23 substantive input changes. They are not
counted as additional instruction executions. Mutation IDs and ordered positions
remain distinct even when the underlying request case ID is intentionally reused.

Architectural expectations use the unchanged independently sealed M2bo
manufacturer/IR reference, first reproduced against all 51 sealed literals.
The new observation-topology oracle is separately source-bound and frozen. It
predicts event schemas/order, not instruction semantics or actual observations.
Expected output is never substituted for actual Rust output.

Every positive comparison includes all decoded fields, all public CPU fields,
all 3968 RAM bytes before/after, exact ordered PROGRAM/logical/raw/diagnostic
events, permissions, faults, counters, retirement and terminal fields. There are
no platform exclusions or omitted canonical fields.

## Lifecycle and honest partial-state errors

`Session` admits coherent canonical entry PSW/PC, budget 1..16 and nonhalted state.
The current M2bp API intentionally seals after one successful retirement. A
budget greater than one is a safety ceiling, not evidence of multi-instruction
session support. The future full-production composite remains a separate
milestone and admission decision.

A direct-J case must actually execute the production instruction body, update
the CPU PC and retire before the terminal seal is set. Later PROGRAM access,
DATA access and step attempts are refused. No external continuation is fetched.
Host-side assignment of a target PC is not execution evidence.
Only a direct-J target outside the checked segment is classified as an external
exit. An internal J target is not mislabeled as external; the one-step seal
still applies. Bounds/classification component regressions cover both cases.

Faults latch the first exact error and prevent subsequent retirement. The
production body can already have advanced PC/counters or changed AL/ZF before
an operand error is returned. Such cases preserve the observed partial state;
they are not described as atomic refusals. A low byte that was authorized and
serviced before a denied high-byte store remains written, with its own raw event.
The incomplete logical word write has no completed logical write ordinal.

The 35 finite capability records include seven mapping cases, eight constructor
refusals and twenty session cases. The session cases cover strict incomplete
decoder reads, selected-identity mismatch, forbidden DATA directions, read-only
word protection, RMW obligations, actual LE16 constituents, partial writes,
same-value writes, partial production errors, fault latch and post-J seal.

Source-derived expected capability counters are 27 constructed CPU/Bus sessions,
10 step API attempts, four shared instruction-body calls and three successful
direct-J retirements. These are not observed results until the complete frozen
records match actual runtime. The summary's 468 positive instance/step counters
exclude these separate capability sessions.

The finite complete canonical sequence has 583 records: header, 552 closed cases,
25 mutation refusals, one PSW sweep, one nested capability envelope, finish,
one feature-disabled API compile refusal and one arbitrary-operation process
refusal. The latter two are separately observed compiler/process records.
Its expected finish counters are 468 positive successes and 109 admission
refusals, with both one-shot gates observed. Nested capability errors do not
increment the closed-case admission-refusal counter.

## PSW, SF and retained context

All 65536 PSW words are classified admission-only by
`(word & 0x0CC8) == 0x0CC8`: 2048 representable and 63488 incompatible. There is
no silent normalization and no CPU execution for the sweep. Positive cases retain
all eight SCB selectors, all 32 pointing words, local r/er aliases, LRB, SSP, AH,
HC and unwritten state according to the independent expectation.

Internal Rust SF=false/true experiments are paired. The physical meaning,
storage, width and value of SF remain unknown and are not inferred from those
internal booleans.

## Default mode, CI and delivery gates

The default differential compiles byte-identical new thin-probe source twice:
once against the actual exact-base production crate and once against the active
production crate with the opt-in feature disabled. It compares actual full
records for all 468 unchanged M2bo microcases, the two historical capability
limitations and 22 current invented protocol fixtures. It also checks protocol 1
and all 38 ordered historical semantic-fix identities. The 38 strings are not a
claim to cover 38 runner operations; current production admission has a different
operation inventory.

The default comparison requires 493 complete canonical records, actual resolved
Cargo feature graphs and actual base/active binary receipts. A separate fixed
compile-only negative must demonstrate that importing the opt-in API while the
feature is disabled is refused; a manifest status field alone is insufficient.

Both default and opt-in freezes precede the first new runtime. Exact sources,
generator, seeds, expected records and projection rules are independently bound.
Local/Ubuntu/Windows comparisons must inspect every decompressed canonical byte,
with counts, chunks and first mismatch; hashes provide supplementary integrity,
not a replacement for full comparison.

The normal three CI jobs remain. The main checkout needs full ancestry for the
version-transition check; the historical checkout is pinned separately. The
Desktop job remains byte-identical, including its 30-second timeout, original
assertions, real WPF/RPM previews, viewports and cleanup. Option B is not extended.

Acceptance also requires active default Rust/Core/CLI/Desktop, historical
research validators, C11/C-C# equivalence, formatting, privacy, protected
comparison, diff checks and portable no-window diagnostics. Heavy local gates
run sequentially. Authorized production/new-M2bp changes and unauthorized
differences are reported separately; the latter must be zero. Eighteen
stabilization sources, 23 historical runners, old seals/final reports, OEM/private
sources and unrelated files remain unchanged.

This specification does not itself claim acceptance. Actual QA, exact pushed
SHA, CI run/attempt/jobs, cross-platform bytes and protected receipts must be
joined before the private final report is written last.

## Exclusions retained after successful capability delivery

- `FullProductionCompositeExecutionNotRun`
- `ProductionBusCompositeIntegrationNotEstablished`
- `OriginalRomExecutionNotObserved`
- `ActualDownstreamRejoinNotEstablished`
- `SFMeaningStorageNotEstablished`
- `PhysicalROMPlacementNotEstablished`
- `TargetProgramEquivalenceNotEstablished`
- `FirmwareIntegrationNotEstablished`
- `FirmwareReady=false`

New target BIN/object/HEX/FirmwareBIN count is zero. M2bq, new full-production
composite execution, original-ROM execution, firmware integration, GUI and
hardware are not admitted by this document.
