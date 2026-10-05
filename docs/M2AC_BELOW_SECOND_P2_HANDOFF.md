# M2ac — Below-path ROLB A and second-P2 architectural handoff

Base `acaa05c784500d50bd46088a1f1ee42bbae882b6` on
`codex/p28-post-p2-control-handoff-m2ab`; target
`codex/p28-below-second-p2-handoff-m2ac`. This is a separate bounded research
operation, not expansion of the historical M2ab operation.

## Primary ISA authority and narrow correction

The complete manufacturer ROLB A page, printed3-119 (PDF renderer172),
establishes opcode33 in DD0: AL rotates through incoming CF; outgoing CF is
old AL bit7; AH, ZF, HC, DD and every other PSW bit are retained. ROL A/DD1
(3-117) and ROLB object (3-120) were visually cross-checked, not promoted by
analogy. Decoder recognition is not the admission authority.

An invented decoded regression failed BEFORE the fix: AL00/CF0/DD0/ZF0
incorrectly set ZF (full PSW6FFD versus expected2FFD). The minimal exact
accumulator-byte correction has its own identity
`byte-rol-a-through-carry-preserves-noncarry-flags`. The M2z off-page identity
is unchanged; no mnemonic-wide rotate correction, DD1 change, RORB promotion,
disputed4781/4581 or M2t JGT admission was made. Invented opcode33 tests compare
DD0/DD1 across AL00/7F/80/FF, CF0/1, prior ZF0/1 and a nonzero AH canary.

All newly admitted exact forms have independently reviewed full manufacturer
pages: ROLB A3-119; STB3-155; RB3-114; L3-69; SJ3-140; ST3-154; J3-62;
JNE3-66; LB3-70; ORB A,object3-107; ANDB A,immediate3-24;
ORB object,A3-108. Object RB is DD-independent and changes only ZF to the
inverse old target bit. L/LB set ZF and DD1/DD0 respectively; byte LB preserves
AH. Logical byte operations change ZF only. J/SJ/JNE and stores retain flags.
The decoder's DD-neutral annotation for one byte ORB form is not a permission:
the exact admitted predecessor establishes DD0 and the independent model
checks it. No other form inherits these admissions.

## Actual continuous control flow

One Cpu/Bus carries M2r quartet → native05EB G0196 →54FA read →5578 compare
→557D below →55C5 P2 G1 →55C8 TCON0 →55CB LB018E →55CD XORFF →55CF MB C
→55D2. Incoming A/AH/CF/full PSW come from these actual preceding instructions;
no host seed, PC55D2 shortcut, second machine or extra scheduler seam exists.
The old technical PC54F5 transition remains `ExplicitHarnessSchedule`, not a
recovered ECU scheduler.

Native path (18 instructions; the final RT is NOT executed):

```text
55D2 ROLB A →55D3 STB0116 →55D5 RB TCON0.2 →55D8 L #1
→55DB SJ562C →562C ST0110 →562E L #1 →5631 ST0112
→5633 J565D →565D ST0114 →565F L0110 →5661 JNE5671 TAKEN
→5671 LB0116 →5673 SJ567E →567E ORB018F →5680 ANDB #0F
→5682 ORB P2,A →5685 RB012A.7 →5688 STOP BEFORE RT
```

Code ranges are `[55D2,55DD)`, `[562C,5636)`, `[565D,5663)`,
`[5671,5675)`, `[567E,5688)`. Trace, instruction extents, complete CPU boundary,
SSP continuity, ordered RAM/control/P2 accesses and writes are checked.
No CAL/SCAL/VCAL occurs on this path; no return frame is created or supplied.
`ReturnFrame=NotEstablished/NotNeededForBoundedResult`; RT5688NotRun.

Alternative static branches through5663/5665/5667/SRLB and5675/5677/5679/RORB
or5689/568B cannot be selected here: the native562C writer makes0110=1, so
5661 is necessarily taken. They are static-only, not admitted dynamic ranges.
Other entry paths reach TMR0 at55DE/5619/5636/5694; none lies on this path.
The not-below M2ab branch still stops559D; TM0/TMR0 accesses stay NotRun.

## Software ownership and retained architectural state

| Address | Width | Owner before reader | Reader / persistence |
|---|---:|---|---|
| 0116 | 8 | native55D3 ROL result | 5671; not scratch |
| 0110 | 16 | native562C stores1 | 565F→JNE taken |
| 0112 | 16 | native5631 stores1 | alternate5663 static-only |
| 0114 | 16 | native565D stores1 | alternate5675 static-only |
| 018F | 8 | native55C3 stores0F | 567E |
| 012A | 8 | inherited M2x owned software history | 5685 clears bit7; other bits retained for next event |

No new external scenario source is needed. The actual018E writer5572 and
upstream software histories remain independently checked. Scratch patterns
00/55/AA are canaries, not unknown software live-in authority.

55D5 clears bit2 of the retained native55C8 TCON0 generation. Existing stopped
realtime-output snapshots83/87/8B/8F are the only initial domain; RUN stays0.
Primary matching peripheral Table9-1/Fig9-2 explains why no clock/buffer
transfer is performed; the RMW-near-transfer warning is bounded out by RUN0.
Two recorded reads and one write reflect the decoded executor's byte RMW,
not electrical bus-cycle counts. TRNSIT is untouched on below path.

## Second P2 and generations

Exact5682 is byte `ORB P2,A`, encoding `C5 24 E1`: read0024, write old|AL,
set ZF from the byte result, preserve A/CF/HC/DD/other PSW; next5685.
It is reviewed independently of the prior55C5 form. Matching manufacturer
P2/P2IO/P2SF evidence permits existing latch storage only under the inherited
`ReviewedStartupPrecondition`: P2IOFF, implemented P2SF bits0, all-output
primary port. This is not executed startup or generic GPIO/input/pin modeling.
Capability is native-only at the exact reviewed PC/address/width; wrong PC,
width, neighbor or disabled/host access faults. Old P2 capability PCs are unchanged.

G1 from55C5 is the second instruction's old latch. Generation identity is
`(writerPC,eventIndex,zeroBasedAllNativeEventWriteOrder,value)`. Native5682
creates fresh G2 even for equal old/new values; correct value with stale G1
fails. The mask from native55C3/567E/5680 makes AL0F, and G1 already has low
nibble0F, so this below corpus has same-value G2 writes, not value divergence.
G2 and the cleared TCON0 generation persist into the next event, including
upstream Partial and later NotRun. No per-event P2/TCON0 snapshot reapplication.

An event-wide native-only journal separates RAM0, P2 peripheral1 and control2;
the C# validator independently merges verified stage chronology and recomputes
all write ordinals. It independently owns upstream expected states, G0196,
selector/address generation, ROL semantics, software RAM/branches, G1/G2 and
TCON0 generations. Observed Rust values are not expected-model inputs.

Partial execution preserves completed writes/storage/generations without
rollback or claiming a completed second-P2 result; later events are NotRun.
Equal/Above controls are historical M2ab coverage, not new M2ac completions.

## Closed operation and read-only CLI

Runner0.36.0, operation `belowSecondP2Handoff`, protocol1. Historical0.35
refuses it. Version1 scenario purpose `below-second-p2-handoff-test` reuses the
entire closed M2ab source contract: no ready0196, ROL/CF/branch result, second
P2 result, PC shortcut, return address, timer, IRQ, pins or arbitrary RAM.

```text
hondaecu research p28-fuel below-second-p2-check <original.bin>
  --profile p28-304 --confirm-profile
  --baseline-binding <binding.json> --runner <runner-0.36.0>
  --scenario <m2ac-scenario.json> --output <new-private-report.json>
```

Exact original/profile/binding guards, bounded subprocess handling, no-overwrite
and alias guards remain. Optional fuel mutation is in-memory only; no BIN.
Public tests use differently composed invented low-address programs and
model-only/protocol guards, never OEM windows or private sources. Private
actual corpus, counts, negatives, full preservation, QA and exact-SHA CI are
recorded separately in the final private report.

## Scope remains bounded

`SecondP2ArchitecturalHandoff=Validated` means the strict subset only.
TimerEvolutionNotModeled; TimerContinuationNotRun; IRQDeliveryNotInjected;
ElapsedTimeNone; P2ElectricalPinsNotModeled; PhysicalOutput/HardwareValidationNotRun;
PhysicalP2Role/PhysicalPolarity/ChannelAssignmentUnknown. No recovered0196/ECU
scheduler; no physical RPM/fuel/time/degrees. M2ab/aa/z/y/x/w historical bounds
are unchanged; M2t JGTBlocked/Unresolved; strictM2iBlocked; GUIr3paused/NotRun;
D1/D2 interactive and hardware/fullbootNotRun. PcInspectionOnly/NotFlashReady;
FirmwareBIN/binding/compensation/exportplan/receipt/token0. No automatic M2ad,
RT5688, timer path, IRQ scheduler, pin mapping, JGT, GUI or hardware work.
