# M2l — native additive fuel-correction production and application

Read-only software evidence on the privately bound P28-304 original. Operation
`fuelAdditiveCorrectionChain`, runner **0.20.0**, pinned Rust **1.85.1**.
This does not change the historical M2k stop-before21F2 contract or its result
format. Strict M2i remains **Blocked on47 81**. No disputed ADD/SUBB permissions
are admitted here. No OEM program, maps, identities or traces are published.

## Established execution boundary

The reused native axes/selection/lookup prefix writes the actual word0140 at134E
and stops before1350. One disclosed **scripted same-machine entry1350→2194**
follows. This is not recovered ECU caller continuation or scheduler execution.
After2194, producer→scaling→application runs without enter/reset at21DB or21F2.

| Fragment | Entry / stop-before | Additional native code | Result |
| --- | --- | --- | --- |
| Correction producer | 2194 /21DB | signed-add helper596C..5990, twice | signed word in er3 and the same word in X2 |
| Unchanged M2k scaling | 21DB /21F2 | none | separately limited component in A and er2 |
| Application / first stores | 21F2 /2204 | VCAL4 helper5958..596A | corrected A/er3; stores03A2 and03B4 |

2194 is closed: its first word load replaces inherited A. Each consumed carry
is locally produced; er0, er3 and X2 are written natively before consumption.
Inherited registers are only retained canaries, not ready correction operands.
Gate217A/0124.4 remains a **static caller precondition**, bit4 must be clear.
The bypass/clear path217D..2193 is **NotEvaluated**, not an executed masked gate.

Scripted ABI writes are exactly LRB0020, PSW0101 and USP0280 (canonical PSW0DC9).
A, bank bytes, X1/X2/DP and SSP survive the transition. Native12FC..1350 and
native2194..2204 each have continuous state checkpoints and access journals.
One CPU/RAM persists per image/sequence/scratch00/55/AA. Each in-memory B starts
independently from the original; divergent histories are never aligned by host.

## Source ownership and widths

All addresses are software storage, not physical sensor names or units.
Inputs are applied once before an event's native stages, never between producer,
scaling and application. Closed schema prohibits pointers, flags, PC/RAM scripts,
ready er3/X2,0140, scaled/final outputs or per-event selector/map IDs.

| Footprint | Established writer → reader | Policy |
| --- | --- | --- |
| 0140..0141 word |134E native lookup store →21DB | Native-owned; code-owned initial zero; no input override or intervening byte write |
| 0158..0159 word |7A99 / upstream calculation →21DD | Explicit raw-u16 snapshot; producer NotRun |
| 0142..0143 word |14C8; zero142D →2194 | Explicit raw-u16 software snapshot; upstream NotRun |
| 0144 low byte;0145 high byte |4A53 byte writer →21A5 **word** read | Input restricted0..255; upper0145 code-owned zero, no claimed recovered high-byte producer |
| 0146..0147 word |200A →21B8 | Raw-u16 snapshot, interpreted signed by native helper; upstream NotRun |
| 0148 byte |208A →21B5 | Raw-byte snapshot, native EXTND |
| 0149 byte |49B1 →21BE | Raw-byte snapshot, native EXTND |
| 014A..014B word |20F0 →21A9 | Explicit raw-u16 snapshot; upstream feedback/clamp NotRun |
| 014C..014D word |2172 →21AD | Explicit raw-u16 snapshot; upstream NotRun |
| 00F2 byte |3E12/415C →2199 | Explicit raw-byte counter snapshot, not a physical timer |
| 012B byte, bit3 | static160E; native219D →2196 | Once-only mode byte; native updates bit3 and retains neighbours/history |
| 0124 byte, bits4/5 | static1A28/1A23 → caller precondition /21F5 | Once-only software gate, bit4 clear; native bit5 read controls03A2 |
| 0127 byte, bit1 | once-only caller → native selection | Native pointer selection; not VTEC/cam-state production |
| Axis caches/fractions,013F | reused M2k ownership | Once initial, then native-owned; optional helper60E5=0 unchanged |
| 0238/00C2/00BF bytes | external raw snapshots → axes | Per-event at the same input point; physical RPM unavailable |

The general boot clear2710 is a static lead only. Its retained-RAM branches and
full boot are not executed or used to claim arbitrary0145 values. Restricting that
upper byte avoids inventing a missing producer. Other snapshots describe legal
storage-width test domains, not proof that every combination is produced by the
excluded upstream firmware or reachable in a physical ECU.

## Native production, scaling and application

The producer forms an unsigned base from0142, optional100,0144,014A and014C.
Unsigned overflow branches toFFFF, potentially skipping later positive adds.
When mode012B.3 was set on entry, the current event adds100 and updates the mode
bit to(counter00F2<4); later events use the retained bit, not an injected mode.

Two actual CALs enter596C. It adds signed EXTND0148 to signed0146, saturating to
[-32768,32767], then separately adds EXTND0149 with the same signed saturation.
The final native addition of unsigned base has an upper signed limit32767.
The resulting **two's-complement word** is written at21D9 to er3, then at21DA
to X2. X2 is not a separate sign/magnitude or physical-unit carrier on this path.

The independent arithmetic projection preserves these stages:

```text
u = min(0142 + conditional100 + 0144 + 014A + 014C, 65535)
s1 = clamp(int16(0146) + int8(0148), -32768, 32767)
s2 = clamp(s1 + int8(0149), -32768, 32767)
correction = min(s2 + u, 32767)
component = min((uint32(0140) * uint32(0158)) >> 9, 65535)
corrected = clamp(component + correction, 0, 65535)
```

This formula was derived after auditing native operations and branches. It is
not substituted for native code. Earlier M2k saturation must happen **before**
correction: a negative correction can lower a saturated component. Combining
the wide product and correction before saturation gives a different result.

LRB20 aliases are er0=0100, er1=0102, er2=0104, er3=0106 (each two bytes).
For SCB1, X1/X2/DP/USP are0088/008A/008C/008E. Scaling overwrites er0/er1/er2,
but not correction er3/X2. ST21F1 leaves the component live in both A and er2.
At21F2, actual XCHG changes A to correction and er3 to component, preserving
flags. Unequal operands and both correction signs are checked.

VCAL4 at21F4 reads vector0030..0031 →5958, pushes return21F5 at07FE..07FF,
and decrements SSP to07FC. Native RT increments SSP and reloads that word.
The producer's two near calls similarly push21BE/21C4 at the same slot, with
no nesting. Only this two-byte stack footprint is admitted; no sentinel,
host callback, manual return-PC or ROM patch is used. Far calls/returns are
outside this near-call-only contract.

Helper5958 uses native sign testing, ADD and carry branches. Negative underflow
produces0; positive overflow producesFFFF; equality follows the native carry
branch. The corrected word is returned in A/er3. Caller21F5 then reads0124.5:
if set, it clears A before03A2; corrected er3 survives.21FD reloads corrected
er3,2201 reads the previous03B4 word into er0, and2203 stores corrected A to03B4.
Stop-before2204 is therefore the first coherent store set, not helper-only proof.
er2 remains the scaled component even when A/er3 diverge from it.

## Exact-form admission and executor regressions

Primary source: existing OKI MSM66201 Instruction Manual, first edition
September1991. Visual PDF audit confirmed the new forms, widths and flag tables;
existing M2k exact-form evidence is reused for the scaling fragment.

| Exact forms admitted (operand variants are not interchangeable) | Primary printed pages / semantics |
| --- | --- |
| L/LB off-page, L immediate/er3; ST er0/er3/[DP] |3-69/70,3-154; L sets word DD/ZF, LB resets DD; stores preserve flags |
| ADD A, immediate/off-page/er0/er3 |3-13; DD1, unsigned CF and nibble HC, ZF; no carry-in |
| CMP A, immediate; CMPB direct, immediate |3-35,3-42; CF/ZF, **HC preserved** |
| JBR off-page bits3/5, JLT/JGE/SJ |3-64,3-66,3-140; exact bit/relative addressing and flag predicates |
| MB off-page bit3,C; MB C,r7.7 |3-78/77; byte access, neighbour retention; only read-to-C changes CF |
| EXTND F8 |3-59; signed low-byte extension, DD1, other flags preserved |
| ROL A33; ROR A43 |3-117/121; through incoming CF, only CF changes |
| MOV er3,off-page; MOV X2,A; MOV DP,immediate; MOV er0,[DP] |3-83/85/86; exact word widths, no arithmetic-flag effects |
| CAL32, RT01, VCAL4 opcode14 |3-29,3-125,3-167; actual near-call stack/vector/return |
| XCHG A,er3 47 10; CLR A F9 |3-168,3-31; word exchange preserves flags; CLR sets DD/ZF |
| Reused MUL er1/A, SRL er1, LB r2, L ACC, SWAP, ST er2 |M2k inventory, unchanged exact forms |

Two genuine executor defects were proven by failing decoded regressions before
fixing: word ROL A was circular and changed ZF; exact word ADD A,er0/off-page
did not update HC. The minimal corrections follow primary3-117/3-13. No CMP HC
change was made. The new version/fix inventory discloses these semantics; version
numbers or upstream decoder descriptions alone are not ISA evidence.

## Independent evidence, partial events and coverage

C# independently owns ROM/cache history and derives0140, correction, component,
application and stores. A separate instruction-path oracle compares every tail
event's pre/post A/PSW, comparisons, PC/extent, full data/register/stack accesses,
ordered writes, native word aliases, vector reads and exits. Actual Rust operands
are not expected arithmetic inputs. Initial unused register canaries are checked
for retention only. A same-result forged intermediate, XCHG or seam is rejected.

Unknown exact forms stop before execution. Completed stages remain visible;
later stages/outputs are absent/null, and future events are NotRun without input
application or history reseeding. Stage budgets96/32/48, events1..64, ≤8 selected
trace indexes, journals bounded4096. Nonselected instruction text traces are
removed explicitly from delivered reports; numeric evidence is not silently cut.

Local authoritative M2l coverage: **3678 StrictMatch native events**, both initial
map contexts, independent A/B images and three scratches; **1620 A/B comparisons**,
**207 unmasked witnesses**, all controls pass. There are distinct new lower/upper
application masking cases where components differ; zero factor, M2k truncation/
saturation and lookup masking are classified before application. Source-input
sweeps, signed-add boundaries, base overflows, mode history and03A2 gates are
separate from ROM-edit A/B. This does not add the old1566 M2k checkpoints.

Model-only checks are separate:131072 own-ROM raw-axis pairs and8257536 staged
projections, plus327680 public signed-word/byte cases. Native count for these
model audits is zero. Exploratory replays and M2k compatibility repeats are not
added to the authoritative M2l native total.

Public regressions use invented programs/data, including a real Rust subprocess
that natively produces7 and40×3, executes XCHG/VCAL/helper/RT and consumes127
while retaining er2=120. It does not copy an OEM routine.

## CLI and remaining dependencies

```text
hondaecu research p28-fuel additive-chain-check <original.bin>
  --profile p28-304 --confirm-profile
  --baseline-binding <binding.json> --runner <runner-0.20.0>
  --scenario <m2l-scenario.json> --output <new-private-report.json>
```

Exact binding, snapshots/rechecks, new-path/alias guards and bounded cancellable
subprocess transport are reused. Optional mutation is a code-owned single fuel
cell in memory only; axes, multipliers, code and configuration cannot be edited
by this command. No firmware BIN, binding, export plan/receipt/token is created.

Unchanged60E5=0 bypasses the old optional helper;60F8=0 bypasses the later227A
per-channel reload. No jump to that gated path or alternate14ED/14F0 generation
is claimed.0158 upstream, other correction-source producers, later controller
gates/helpers, per-channel tables, штатний scheduler, full boot and physical
injector pulse width remain outside scope. No G/F acquisition, VTEC/ignition/
shared-M2h integration, timer/IRQ/engine model, exporter or GUI feature is added.

**PcInspectionOnly / NotFlashReady**; `physicalRpmAvailable=false`; fuel/time
units/degrees unavailable; GUI r3 paused/NotRun; D1/D2 interactive acceptance,
hardware and full boot NotRun. These excluded checks do not leave M2l unfinished.
