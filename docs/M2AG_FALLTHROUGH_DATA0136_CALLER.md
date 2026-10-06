# M2ag — native fallthrough DATA0136 caller entry

Exact base `7fe1b78be1f1499c531750abea572258e647899b` is M2af,
`codex/p28-native-data0136-caller-m2af`, delivered with CI3/3 success.
Separate runner0.39.0 operation: `fallthroughData0136CallerHandoff`.
M2af's primary064C-taken route remains Research/Blocked; M2ag does not repair it.

## Exact native caller

ONE retained Cpu/Bus carries M2r/M2x, PC-only05ED→063B harness seam, native
CAL063B/validated below body/RT5688→063E, and M2ae063E..064A→actual064C.
Only M2ag continues that exit. No host PC064C/065F/0664/56BE, second machine,
intermediate serialization, RAM/result copy or hidden ABI reset.

Fresh matching ROM/listing audit and complete manufacturer pages visually
reviewed with PDF skill establish exact forms; decoder recognition is not
semantic admission. OEM bytes/windows, manuals and actual reports remain private.

| PC | Exact form | Effect / nextPC | Primary page |
|---|---|---|---|
|064C|JBS off011F.3,rel8|Current bit3: set065F,clear064F; flags/DD retained|3-65|
|064F|JBS off011B.7,rel8|Existing upstream bit7: set065F,clear0652|3-65|
|0652|RB off012A.0|ZF=inverse OLD bit0; byte RMW clearbit0; neighbors/CF/HC/DD/A retained|3-114|
|0655|JEQ rel8|ZF1→065F,otherwise0657; flags retained|3-66|
|065F|RB off012A.3|ZF=inverse OLD bit3; clearbit3; other state retained|3-114|
|0662|JNE rel8|ZF0→0667 skipCAL;ZF1→0664|3-66|
|0664|CAL addr16|Length3,target56BE,return0667; word at OLD SSP,SSP−2,internalSF0;PSW retained|3-29|

Caller ranges `[064C,0657)`, `[065F,0667)`, budget7; exits56BE/0657/0667.
Stop BEFORE0657/TRNSIT or0667 continuation. No new peripheral capability there.
Listing DD1 at065F is not a seed: actual DD0 persists until first L56BE.

## Retained sources choose the route

One full-byte011F owns caller bit3 AND producer modebit2. No new011F/012A.0/.3,
011B.7,slot,branch/mode/PC/SSP/return/ready-result source exists.012A initializer
owns onlybit1,5685 clearsbit7 and M2ae preservesbits0/3. Scratch00 has012A00/02,
oldbits0/3 clear. Integrated limiter initialization owns011B low7=0; historical
adaptive `fixedSource` masked application ownsbit7. No caller-stage rewrite.

Actual00 routes, counted separately:

- `FallthroughVia012A0`:064C→064F→0652 oldbit0=0→0655 taken065F.
- `FallthroughDirectVia011B7`:064C→064F taken065F when existing upstream
  ownership actually leavesbit7 set.

Both reach065F oldbit3=0,0662 NOT taken and native CAL0664.
55 without direct011B.7 stops-before0657; with it can CAL but retained mode/slot55
block producer before observations. AA executes taken/oldbit3=1/cal-skipped
control, never strict success. No gate/ABI repair or second invocation changes it.

## New pending frame and actual ABI

Frame identity is `(writerPC0664,eventIndex,stackAddress,width16,returnPC0667,
zeroBasedAllNativeEventWriteOrder)`. Previous063B/063E frame was consumed;
reusing its RAM slot creates a distinct generation. Actual SSP7FE stores0667 at
7FE/7FF and becomes7FC. C# derives word/address/order and verifies no overlap
through5719. Correct0667 in stale RAM is insufficient.

At56BE the helper does NOT call `acquisition::enter`, `seed_machine`, M2v
initializer or slot/00F0 setter; no PC/PSW/LRB/SCB/pointer/USP/SSP/register/RAM
assignment. It only configures narrow guards/frozen sources and executes.
Historical M2v technical wrapper remains unchanged.

Actual00 differs from technical M2v: DD0,USP0,SSP7FC rather than technical
word entry/USP0280/unusedSSP7FE; A is native M2ae result. L56BE overwrites A
and establishes DD/ZF. Incoming USP/DP/X2/X1 are not consumed on NoWrite. CF
may remain observed on high/no-IRQ paths or be overwritten by MB before JGE.
Differences are retained/compared, not normalized. Full CPU boundaries include
A/fullPSW/DD/LRB/SCB-selected pointers/SSP/r0..r7. Slot00A2 is retained history0;
HostSlotWrites0. NoWrite never executes the later slot/index load.

## First-observation NoWrite is core success

```text
56BE wordTMR2 →56C0 mode0 →56C5 er3 →56C6 high-bit test
→ optional56C9 IRQH/56CC/56CE counter/56D1 guard
→56D4 SB0128.3 old-clear →56D7 JEQ5713
→5713 Ler3 →5714 previous00EE store →5716 counter00AE clear
→ STOP BEFORE5719
```

Producer forms reuse reviewed M2v semantics under narrower operands/ranges:
L3-69,ST3-154,JBR3-64,JBS3-65,MB3-77,JGE/JEQ3-66,INCB3-61,SB3-127,CLRB3-34.
Ranges `[56BE,56C3)`, `[56C5,56D9)`, `[5713,5719)`, budget128. No executor fix.
Mode1/fresh-gate arithmetic/writers,5719 and tail are excluded. Unexpected
mode/slot/gate blocks entry, never repaired. M2ae sets0128 bits0/1, preservesbit3.

Native NoWrite writes er3,sets0128.3 from OLD bit,updates00EE,clears00AE. Low
sample plusIRQH.0=1 also increments00AE/sets00B6.0. Neighbors,0136 and six samples
persist. Same-value history stores still have ordered IDs.5707/56F3/570E NotRun;
retained0136 is not fresh. Caller success does NOT require a0136 writer.

## Frozen sources, chronology and terminal policy

Observation schema: mandatory `tmr2` word, `irqh` byte ONLY if samplebit15 clear.
High samples omitIRQH. No tcon2 field: disabled, not default-zero; internal
placeholders are not source permissions. Native PCs/widths:56BE/003A/16 and
56C9/0019/8. Wrong PC/width,missing source,unknown SFR and writes fault. Old
diagnostic rejected write attempts are not successful effects.

Matching MSM66201/207 evidence supports frozen nondestructive read-only only:
NoTimeAdvance,NoNewEvent,NoInterruptDelivery. IRQH.0 is not an injected IRQ or
physical overflow proof. PhysicalTimestampNotEstablished;TCON2Reads0;
CoreStrictTrnsitAccesses0.

C# owns caller flags/gates,both frames,retained histories,NoWrite effects and
full boundaries independently. Rust values never become expected numerical
inputs; M2v initializers do not adapt observed RAM. Event-wide native journal:
`[space0RAM/1P2/2Control/3FrozenCapture,PC,address,width,write,value]`.
ALL writes,including stack/P2/control,share global ordinal; captures do not
increment it. Leaf/host journals,trace,exact instruction extents are checked.

At5719 frame0667 is EstablishedPendingReturn: no pop,SSP balance or rollback.
Every new caller boundary terminalizes sequence,including controls/partials;
later events NotRun without fuel/frozen inputs. Held frame word/identity persist.
RT5801/return0667/second producer/2330 scheduling NotRun/NotEstablished.

## Closed read-only interface and compatibility

FormatVersion1,purpose`native-fallthrough-data0136-caller-test`; existing M2ae
initial/upstream/selector/P2/control contract. Calls add only `producerObservation`
to `prefix`. Unknown gate/mode/slot/PC/SSP/expected/ready/writer/arbitraryRAM,
timer evolution and IRQ-trigger fields are refused, not ignored.

```text
hondaecu research p28-fuel fallthrough-data0136-caller-check <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --runner <runner-0.39.0> --scenario <m2ag-scenario.json>
  --output <new-private-report.json>
```

Exact original/binding/profile,bounded JSON/process,cancellation/input snapshots,
alias/no-overwrite/no-firmware-output guards remain.0.38 refuses M2ag;0.39 adds
no fix inventory. M2ae still stops064C,M2ad063E,M2v remains technical,M1i/RTI
unchanged. Compatibility normalizes runnerVersion ONLY; static M2af/M2u evidence
is protected,not fake runnable coverage. Public tests/CI are invented fixtures;
actual corpus/counts/negatives/QA/privacy/preservation/CI are private and separate.

## Static future boundary and exclusions

5719 is CMPB00A2,#5,not RT. Refreshed static tail includes5782/5787 readers,
earliestTM3 at5793,laterTMR2/TMR3/TCON3/P1 andRT5801/return0667:allNotRun.
No writer/tail/physical/scheduler permission follows from native entry.
M2afPrimaryBlockedUnchanged;strictNoWriteValidated;fresh0136NotCreated;
TechnicalSeedNotUsed;TimerEvolutionNotModeled;IRQDeliveryNotInjected;ElapsedTimeNone;
RecoveredCaller/0196/EcuSchedulerNotEstablished;EnclosingIRQFrameNotEstablished;
ProducerTo2330SchedulerSeamNotEstablished;M2tJgtBlocked/Unresolved;
PcInspectionOnly/NotFlashReady;physicalRpmAvailablefalse;physical fuel/time/degrees
unavailable;strictM2iBlocked;GUIr3paused/NotRun;D1/D2interactive/hardware/fullbootNotRun;
FirmwareBIN/newbinding/compensation/exportplan/receipt/token0. No automaticM2ah,
5719/tail/RT5801/return0667/second producer/2330/time/IRQ/JGT/GUI/hardware.
