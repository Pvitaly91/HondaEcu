# M2ad — native CAL/RT caller-frame round-trip

M2ad extends the bounded M2ac below path with a genuine call and normal return
on the **same retained Cpu/Bus**. It does not recover the enclosing caller,
interrupt delivery or ECU scheduler. No GUI, keyboard, mouse or hardware test.

## Entry and exact boundary

The disclosed technical scheduler seam changes **only PC**, after the M2r/M2x
prefix exits at05ED:05ED→063B. No accumulator, PSW, LRB, SCB, pointer, SSP,
register bank, RAM, peripheral or return word is seeded there.

CAL addr16 at063B has length3, target54F5, and return address063B+3=063E.
The manufacturer instruction manual printed3-29 specifies a word store of the
return PC at **old SSP**, followed by SSP−2, then the target PC. Word accesses
are even-aligned and little-endian (1-5,1-17,1-20). In the retained technical
machine SSP7FE therefore stores the word at7FE/7FF and becomes7FC.

The exact reused native callee path is:

```text
063B CAL →54F5→54FA→5501→556F→5578→557D Below
→55C5 first P2→55C8 TCON0→55D2 ROLB A
→562C→565D→5671→567E→5682 second P2→5685→5688 RT→063E STOP
```

RT at5688 has length1. Printed3-125 specifies **SSP+2 first**, then word PC
read at that incremented SSP. It reads the frame created by CAL063B,
restores SSP7FE and sets PC063E. Stop **before executing063E**.

CAL/RT leave all PSW bits, including CF/ZF/HC/DD, unchanged. They clear SF,
the internal nX-8/300 STACK/A operand-mode flag, **not a PSW reserved bit**
(MAC66K assembler manual4-73). RT retains callee-produced A and LRB; it does
not restore an interrupt snapshot. RTI is unchanged and not executed here.
The executor models this narrowly for exact CAL addr16 and RT; this is not a
claim of complete STACK-mode emulation. Two invented regressions failed before
the minimal SF fix; identity `cal-addr16-rt-clears-internal-stack-flag` records it.

## Frame and independent ownership

The typed frame identity is writerPC063B,eventIndex,stackAddress,width16,
returnPC063E and zero-based **all-native event write ordinal**. Stack is RAM
in the tagged event chronology; a separate native stack journal classifies the
CAL store and RT read. Read-only diagnostic inspection is never a native read.

Upstream native helpers can have used the same stack word **before** CAL063B.
Those writes remain in the full chronology. The new CAL overwrites the word;
neither scratch bytes nor earlier helper return values determine this return.
Only the interval **from this new writer through RT5688** defines same-frame
proof: exact address/width, no overlapping write, then the native RT read.
Correct063E in an initial/stale/neighbor word is insufficient.

C# derives returnPC from callPC+length and owns SSP arithmetic, frame identity,
the unchanged interval, and complete CPU state after RT independently. It also
retains the existing independent quartet/G0196/54FA/5578, RAM, G1/G2 P2,
TCON0/TRNSIT and ROL models. A Rust stack observation is never an expected
model input. Frame storage is constrained to the retained even technical
stack domain700..7FE, separate from admitted software RAM/peripherals/banks.
Wrap, collision, odd pointers, missing writer, wrong width, wrong target,
hidden host schedule54F5 and accidental RTI restoration are refused.

Strict round-trips require quartet-derived current G0196 below00C0.
Gate-bypass mechanics controls are counted separately. Other domains can
create a CAL frame but do not receive an invented return: `CallerFramePartial`
retains the native SSP and side effects and terminates later events asNotRun.
No stack repair or state reseed is performed. Completed returns retain RAM,
second-P2 G2, cleared TCON0 generation and012A history into the next event.

## Static enclosing context — not executed

The matching private ROM/listing was re-audited, including both exact forms.
063B lies in shared interrupt-domain code reached from INT1 and serial RX BRG
entries. Their setup includes IE, PSW0102/SCB2, LRB0021/local0108, USP0280;
timer/IRQ reads and writes and helper calls precede063B. These are static
facts, not replayed live-ins or proof of a delivered IRQ frame. CAL itself
needs only its retained SSP and code-owned target; the existing callee live-ins
remain the independently checked same-machine state.

Static063E..064A manipulates selector013C, localr0 and0128. First subsequent
branch is064C. This is a preparation boundary only: execution remains stopped
at063E. No preceding caller, following continuation, RTI or timer path runs.

## Protocol and read-only CLI

Runner0.37.0, protocol1, pinned Rust1.85.1, repository.NET8.
New operation `calRtRoundTripHandoff`; response `calRtRoundTripSequences`.
Historical0.36 refuses the new operation. Existing serialized operations,
admission ranges and old direct PC54F5 schedules retain their contracts.
Compatibility normalization removes only runnerVersion and the single appended
SF fix identity; historical response contents otherwise remain identical.

Scenario formatVersion1, purpose`native-cal-rt-roundtrip-test`, reuses all M2ac
sources and fields. There is no new caller/frame/return/SSP/target source.
All input/schema/alias/overwrite/cancellation/profile/binding protections remain.

```text
hondaecu research p28-fuel cal-rt-roundtrip-check <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --runner <runner-0.37.0> --scenario <m2ad-scenario.json>
  --output <new-private-report.json>
```

No OEM bytes, ROM, private listing windows or binaries are distributed.
CI uses invented public programs only; Desktop tests are headless only.

## Claims that remain excluded

`InterStageScheduleTo063B=ExplicitHarnessSchedule`;
`DirectTechnical54F5Schedule=NotUsedInM2ad`;
`Entry=TechnicalSeededRealCallsiteEntry`;
`EnclosingCallerPath=NotRun`;`EnclosingIRQFrame=NotEstablished`;
`RecoveredCallerScheduler/Recovered0196Scheduler/RecoveredEcuScheduler=NotEstablished`.
TimerEvolutionNotModeled;TimerContinuationNotRun;IRQDeliveryNotInjected;
ElapsedTimeNone. P2ElectricalPinsNotModeled;PhysicalOutput/HardwareNotRun;
PhysicalP2Role/Polarity/ChannelAssignmentUnknown. M2tJgtBlocked/Unresolved.
FirmwareBIN/binding/compensation/exportplan/receipt/token0;
PcInspectionOnly/NotFlashReady;physicalRpmAvailablefalse;physical fuel/time/degrees
unavailable;strict M2iBlocked;GUI r3paused/NotRun;D1/D2 interactiveNotRun;
hardware/fullbootNotRun. Prior M2ac..M2w claims remain in their bounded domains.
