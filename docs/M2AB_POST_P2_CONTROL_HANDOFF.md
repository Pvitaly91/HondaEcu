# M2ab — bounded post-P2 control-register handoff

M2ab adds runner0.35.0 operation `postP2ControlHandoff`. It validates CPU-visible
architectural storage under narrow explicit preconditions, not time, pins,
injector identification, IRQ scheduling or actual prior ECU boot state.

Exact base is `5dd31749b10be95c6af37fc1d2f5aa868f2f673e`,
`codex/p28-p2-output-latch-m2aa`. Delivery branch is
`codex/p28-post-p2-control-handoff-m2ab`. No PR, merge or default-branch change.
Historical M2aa operation remains stop-before5599/55C8; M2z/y/x/w and P1
retain their existing contracts. Compatibility normalizes only runnerVersion.

## Three independent admission authorities

Primary ISA full-page visual review establishes ANDB direct/immediate
(printed3-27), SB direct.bit (3-127), LB (3-70), XORB (3-175) and MB C,byte.bit
(3-77). Matching manufacturer MSM66201/207 user/peripheral scans establish
register semantics: Table3-1 at42, timer0 Table9-1/Fig9-2 and realtime-output
section82–95, TRNSIT Fig14-1 at160, PSW32–33 and interrupts162–169.
Exact private ROM/listing byte comparison establishes configuration and CFG;
listing names alone are not semantic authority. Original sources remain private.

| Path | Exact instruction and architectural effect | Next stop |
| --- | --- | --- |
| Equal/Above, native557D not taken | 5599 `ANDB TRNSIT,#FB`, byte0046 RMW. ISA form `C5 N'8 D0 N8`. Clear implemented flag2; ZF from byte result, CF/HC/DD/A preserved. | 559D before PSWH0005/MIE bit0 RMW |
| Below, native557D taken | 55C8 `SB TCON0.2`, byte0040 RMW. ISA form `C5 N8 1A`. Set bit2; ZF reflects OLD bit2, CF/HC/DD/A preserved. | After native55CB LB018E,55CD XORB AL,FF,55CF MB C,ACC006.7:55D2 before unadmitted exact ROLB A form |

The branches are separate CFGs. No host PC5599/55C8 entry or serialization
handoff: ONE Cpu/Bus per image/scratch sequence continues actual M2r quartet
→M2x05DF/05EB native0196→M2y54FA→native5501→M2z5578/557D→M2aa P2 RMW
→M2ab control. Existing technical harness scheduling to54F5 remains disclosed,
not a recovered0196 scheduler. No state copy, second machine or ready0196.

## TRNSIT — readable/writable flags, not command/strobe

TRNSIT0046 is byte `ReadWriteStorage`; this instruction performs RMW.
Implemented bits0..3 are TRNSF0..3. Bits4..7 do not exist and read1. Hardware
falling edges can set flags; no edges are injected here. The matching R/W table
and transition section do not define read-clear or W1C behavior for TRNSIT.
It is not write-only command storage or an IRQ-pending register.
Reset flags0 is a reference, not implicit initial state. Once-initial
`trnsitArchitecturalFlags` admits only0..15. CPU read is F0|flags; native write
is that byte AND FB, with nonexistent bits ignored in retained storage. ZF is
therefore0 even when all implemented flags are cleared. Command invocations=0;
no fake command latch/invocation identity is invented.

## TCON0 — only stopped realtime-output storage

TCON00040 is byte R/W, reset00 reference only, all8 bits implemented.
Mode bits0..1=11 select realtime output: bit2=TR0OUT,bit3=TR0BUF; bit4=RUN;
bits5..7 select clock. Capture-mode bit2 has different event/error behavior.
The manual explicitly warns at93 that RMW immediately before buffer-to-output
transfer can be unsafe. Thus arbitrary or running-timer snapshots are refused.

Once-initial `tcon0ArchitecturalSnapshot` admits only83/87/8B/8F: mode11,
clock100, RUN0, output/buffer variable. Stopped clock and no counter/compare
execution bound this storage-only operation. Native SB changes only output bit2;
mode, RUN, clock and buffer writes fault. This is an explicit raw architectural
test precondition, NOT recovered current running configuration. No ticks,
TM0/TMR0 snapshot, timer phase or hardware transfer is supplied or simulated.
The existing bit executor reads the old bit and re-reads the byte for RMW:
two actual byte reads and one write are independently checked; these are not
claimed physical bus-cycle counts.

Startup25BB writes8B,25EA/25ED toggles output,260F sets RUN; runtime4237 stops
RUN and425B restarts it around output writes. TRNSIT has multiple listed clear
writers, including54E7 and5599. P4SF bits4..7 enable transition inputs; startup
260B writesFC, but pins/boot are NotRun. All listed instructions were byte-checked,
direct references and conservative indirect/indexed leads retained privately.
Off-page symbols require bank context; unknown indirect aliases outside admitted
models prevent a whole-ROM exclusivity/actual prior-state claim.

## Storage, provenance and independent validator

Narrow Bus storage is separate from RAM/P2/P1. Access requires opt-in, native
observer, exact control-instruction PC and exact address; it is disabled after
the bounded stage. Host overwrite/reinitialization, wrong PC/width/neighbor,
generic SFR, timer/IRQ and unreviewed side-effect writes fault. Word0040 would
overlap TCON10041; word0046 covers0047: neither is accepted.

Separate control journal `[PC,address,width,write,value]` never disguises SFR
as RAM or P2. Retained generations use `(writerPC,eventIndex,zeroBasedAllNative
EventWriteOrder,value)`, following P2's native write; same-value write is fresh.
Initial raw snapshot is not a generation. Unwritten registers retain storage
and their prior generation. Reports retain selected-slot provenance, native
G0196 at05EB and its same-generation54FA/5578 reads, P2 latch/generation,
branch, full PSW/banks/pointers/frame, control reads/writes and next stop.

C# independently owns all upstream histories and generations, initial control
state, instruction effects and flags. Rust results are checked, not used as
expected-state input. Correct storage with incorrect flags fails. Partial keeps
only actual native effects; later NotRun applies no source/reseed. Gate-bypass
controls are separate from `PostP2ControlStrict` evidence.

Closed version1 purpose `post-p2-control-register-test` reuses M2aa and adds
only the two required once-initial fields. Timer/time/IRQ/pins, final results,
branch/PC/arbitraryRAM/ready0196 and per-event control state are forbidden.

```text
hondaecu research p28-fuel post-p2-control-check <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --runner <runner-0.35.0> --scenario <m2ab-scenario.json>
  --output <new-private-report.json>
```

Read-only guards require exact original binding and unchanged profile/source
snapshots; existing output and input aliases are refused. Optional one-cell fuel
mutation is in-memory only, no BIN. A/B equality/divergence is architectural,
never pulse/timing/hardware divergence. Historical0.34 refuses this operation.

## Remaining boundaries and verification

Not-below static downstream55A0 accesses TCON0;55A4 reads word TM00030,
later55B2 reads TMR00032. All NotRun. Below stops before55D2; static continuation
through55D5/562C/565F eventually additionalP2 at5682 and RT5688 is NotRun;
no timer access is claimed on that below route. No frame is fabricated.
Interrupt registers IRQ0018/19 and IE001A/1B, timer0 event5/overflow4, are not
newly injected or delivered. Historical CPU arithmetic semantics are not fixed
or expanded to silently admit the excluded ROLB A.

Public tests use invented decoded programs/model-only evidence. Actual private
corpus separately covers both PCs, Below/Equal/Above, all4 quartet slots,
retention, equal-value generations, in-memory A/B, Partial and NotRun. Private
forgeries reject detached entry/flags/storage/journals/provenance/machine and
closed-schema shortcuts. Pinned Rust1.85.1 and repository.NET8 Release builds,
tests, both solution formats, privacy guards and full protected hash comparison
are required; Desktop tests are headless, not GUI acceptance. CI uses invented
fixtures and must match the final pushed SHA with three required jobs success.

TimerEvolution=NotModeled;TimerContinuation=NotRun;IRQDelivery=NotInjected;
PendingInterrupt=NotModeled;ElapsedTime=None;P2ElectricalPins=NotModeled;
PhysicalOutput/HardwareValidation=NotRun;PhysicalP2Role/Polarity/ChannelAssignment
=Unknown;Recovered0196Scheduler=NotEstablished;M2tJgt=Blocked/Unresolved.
PcInspectionOnly / NotFlashReady;physicalRpmAvailable=false;physical fuel/time/
degrees unavailable;strictM2i Blocked;GUIr3 paused/NotRun;D1/D2 interactive
acceptance and hardware/full boot NotRun;FirmwareBIN/binding/compensation/
exportplan/receipt/token0. No next milestone starts automatically.
