# M2au - exact DEC DP / off-page SLLB INT accounting

**M2au exact INT cycle accounting complete - two forms only.**
Exact M2at base: `d142d6feeb5d9b939ffb6fab25d1ace592e0c193`.
Branch: `codex/p28-exact-int-cycle-accounting-m2au`.
Runner **0.43.0**, protocol **1**. New identities:
`word-dec-dp-int-cycle-count` and `byte-sll-offpage-int-cycle-count`.
M2an SLLB semantics and M2at DEC DP half-borrow identities remain separate.
Actual-ROM executions M2au=**0**; tests use invented bytes/state only.

## Independently reviewed primary costs

OKI MSM66201 Instruction Manual, First Edition September1991, was freshly
rendered and reviewed as complete relevant pages, including tables/footnotes,
not only OCR or copied earlier milestone counts. Raw originals/renders and
SHA/edition/review ledger remain private.

| Exact form | Detailed primary | Independent Instruction List | Internal cost | External operand entry |
| --- | --- | --- | --- | --- |
| Word DEC DP /82 /one byte /U | Printed3-55, PDF108, DP row | Table3-11, printed3-189/PDF242 | **3** | Dash; not a proved zero external cost |
| Byte SLLB off N8 /C4 N8 D7 /three bytes /U | Printed3-145, PDF198, off row | Table3-9, printed3-187/PDF240 | **7** | **12**, separately listed |

Both are DD-neutral: neither changes DD nor depends on DD to select its width.
Instruction List headers distinguish Int*1/Int*2, Int*1/Ext*2,
Ext*1/Int*2 and Ext*1/Ext*2; footnotes identify *1 as first operand and *2 as
second operand. These are instruction-total entries under operand-location
categories, not additional per-read/write charges or clock periods. No invented
phase breakdown is claimed, and no data-access surcharge is double-counted.

Printed1-7/PDF11 separates PC instruction access/byte-length PC advance from
explicit program-data access;1-3 and1-8/1-9 distinguish program/data spaces.
Those pages do not establish this ECU's external instruction-fetch wait timing,
READY behavior, oscillator frequency or cycles-to-clock relationship.
The implementation corrects only the decoder's INT model. It does not choose
an actual board's internal/external mapping from an invented RAM address.

No value/flag/DD-dependent cycle exception is specified for these two rows;
neither is a conditional branch. The existing taken-branch penalty is untouched.
Source caveats retained: DEC's plus-one function/summary printing conflicts
with its decrement description; existing arithmetic semantics are not reopened.
The SLLB summary page reference146 differs from detailed printed145. Exact
opcode and costs7/12 agree across the reviewed tables; no numeric INT conflict.

## Genuine RED and unchanged-source GREEN

Before any decoder correction, the unchanged0.42 production modules were
compiled in a private real decode/step test crate. Compiler exit0 is separate
from four genuine cycle assertions, each exit101. Both DD0 andDD1 are observed:

| Probe | Base0.42 | Primary expectation / corrected |
| --- | --- | --- |
| DEC DP decoded cycles |2 /2 |3 /3 |
| DEC DP accumulated step delta |2 /2 |3 /3 |
| SLLB off decoded cycles |6 /6 |7 /7 |
| SLLB off accumulated step delta |6 /6 |7 /7 |

Main independently rebuilt and reproduced all four failures. The same sealed
probe/harness bytes and expectations then passed against the0.43 decoder:
13 GREEN probes, plus two new exact-membership/negative predicate tests.
These are model instruction statistics, not elapsed time or an OEM trace.

## Narrow implementation

The matched-pattern decoder calls an exact INT override before the unchanged
generic `int_cycles(mnemonic,len)` fallback. It requires DD-modeU and the
existing operand parser's exact identity:

- DEC DP, exact[82] (therefore length1), parsedDEC/word/RegDp ->3.
- SLLB off N8, exact[C4,N8,D7] (therefore length3), parsedSLLB/byte/MemOffPage ->7.

Any missing/mismatched parsed form, operand, width, mnemonic, pattern or mode
falls back unchanged. U still implies dd_afterNone through the original decoder
mapping. No opcode-table, match ordering, fetched fields, length, DD metadata or
other cycle helper change. The existing cached operand table has no decoder
recursion; it provides the same form identity already used by the executor.

`exec.rs`, Cpu/Bus, operand parser, constructor and all admission tables remain
byte-identical. `step()` still adds the decoded cost once, and still adds4 only
for a taken conditional branch. Only four old cycle-expectation literals and
their now-stale comments change in the M2an/M2at exhaustive regression files;
all arithmetic, flags, addressing, journals and canary assertions are retained.

## Full-state preservation and cycle-focused coverage

Four complete before/after raw ledgers have identical SHA-256 after permitted
normalization, not merely matching printed FNV values:

| Ledger | Actual domain | Compared state |
| --- | --- | --- |
| Target snapshots |448 states, two contexts, corner values/all flags | Full Cpu/PSW/SCB/LRB/SF/PC, decode metadata, RAM0080..0FFF, native/all-write/continuity journals; only Decoded.cycles/Cpu.cycles normalized |
| Non-target snapshots |29 forms /3,840 states | All the above **including cycles**; both targets excluded |
| Pinned pattern decode snapshots |All2,623 candidates;4,844 DD-valid self selections;4 target decodes | Every selected identity/length/field/mode and non-target cost; only exact target cycles normalized |
| Sequential snapshots |10 streams | Complete per-step state/journals and unchanged instruction/PC outcomes; cumulative cycles and exact target costs normalized |

The exact predicate matches **only2 of2,623 patterns**;40 malformed/mode/width/
operand/identity lookalikes are refused. This is coverage/preservation, not a
claim that all pinned forms or their legacy generic costs are primary-verified.

New cycle-focused exhaustive tests cover **131,072 DEC vectors** (all65,536
old words, bothDD), **1,024 SLLB vectors** (all256 bytes, bothDD, two independent
pages), and160 complete incoming flag controls. Expected costs are primary
literals, not helper outputs. Expected result/PSW uses independent M2an/M2at
arithmetic. Existing524,288 DEC and8,192 SLLB semantic domains remain regressions;
they are not duplicated just to inflate the new cycle test count.

Non-target controls retain DEC X1/X2/USP/SSP, INC DP/X1, direct/indexed/off DECB,
SLLB accumulator/direct/local/[DP], off ROLB, SRL/ROR/SRA, CMP/JNE/JGT/JLE,
CAL/RT and other arithmetic. C8 predicates are preservation controls only.
Other known primary cycle residuals remain deliberately uncorrected.

## Sequential accumulation and impact audit

| Same invented executed stream | Base delta | Corrected delta |
| --- | --- | --- |
| One DEC +one off SLLB |8 |10 (+2) |
| Three DEC |6 |9 |
| Two off SLLB |12 |14 |
| Mixed DEC X1 /DEC DP /NOP /off SLLB |12 |14 |
| DEC DP +taken JNE |10 |11; taken penalty remains4 |

Per-step costs are independently supplied, monotonic and counted once.
Taken/not-taken JNE has unchanged4/8 cost and unchanged target. Equal-value
memory writes retain separate ordered native generations. Truncated forms
retain the same error disposition, PC/state and zero step accounting.

Repository-wide impact inspection finds production cycles only in zero
initialization, decoder metadata and step's additive statistics. Instruction
budgets use executed step counts; transport timeouts use wall-clock mechanisms,
not Cpu.cycles. No cycle-based scheduler, admission decision, SFR/peripheral
evolution or external hardware-state consumer was found. Counter tests stay
within representable u64 bounds; existing overflow policy is not modified.

No physical clock frequency, elapsed milliseconds, WDT overflow, PWM/ADC period,
P4 transition, READY wait state, external bus timing or ECU reset duration is
established. No cycles-to-ticks conversion or timer evolution is added.

## Release identity and unchanged permission

Historical inventories stay0.40/34,0.41/35 and0.42/36; only0.43 requires38,
including the two independently named accounting fixes. Neither replaces the
M2an flag fix or M2at half-borrow fix. New independent compatibility tests cover
41 existing operations, four inventories, all cross-version pairs, either cycle
ID individually, missing/duplicate/unknown identities, protocol/upstream/operation
guards and historical operation thresholds. Old mock fixtures remain intact.

Only necessary live disclosures are updated:24 ordinary version literals and
four metadata/name lines each in the existing DEC/SLLB subprocess probes.
Their invented requests and semantic before-step refusals remain unchanged;
new DD0/DD1 wire probes for both forms also require refusal before step.
Recognition/correct accounting does not grant execution permission.

18 stabilization files preserve PID/START/READY/cancellation/tree cleanup/
timeouts/escaping/streams behavior:16 exact, two authorized assertion literals
only. Eight historical0.40/0.41/0.42 binaries and all old reports remain protected.
Local builds use only a dedicated M2au target; protocol1/schema/CLI unchanged.

## Historical boundaries and STOP

M2at DEC HC complete; M2an SLLB semantics complete; M2as WDT3C and M2ar reset
Research/Blocked. M2aq ExecutionPreflightBlocked; CAL2689/RT5C80 NotRun;
frame268C NotObserved; restoredSSP047E NotEstablished. M2ap SSP/ADC blocked;
M2ao afterCLR2758/beforeSTIE2759; M2ak source-to5722 blocked;
M2al/M2am C8 PrimaryConflictUnresolved; M2ah STOPbefore5722;
DATA019B.2 owner NotEstablished;5722/5725/5733 DynamicNotRun;
M2tJGT233A unresolved; M2ag/M2af unchanged; strictM2iBlocked; IRQNotInjected;
TimerEvolutionNotModeled; EnclosingIRQFrame/RecoveredEcuScheduler NotEstablished;
ElapsedTimeNone; PcInspectionOnly/NotFlashReady;physicalRpmAvailable=false;
physical fuel/time/degrees unavailable. GUIr3 paused/NotRun; D1/D2 interactive,
hardware/fullboot NotRun; FirmwareBIN=0. C8/WDT inquiries ready/NotSent.

Full Rust/Core/CLI/Desktop headless, historical semantic/cycle/identity/admission
regressions, formatting/privacy/diff, full protected SHA-256, stabilization,
historical binaries and exact-SHA Ubuntu/Windows/Desktop CI precede the private
final report, saved last. No retrospective research promotion.
One next evidence step, not performed: separately authorized applicable WDT3C/
reset-release primary evidence. STOP after delivery: no M2av, WDT/C8 fix, native
reset/CAL/RAM loop/IRQ/timer/first5722/GUI/hardware work.
