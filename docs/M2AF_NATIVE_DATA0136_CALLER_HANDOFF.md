# M2af — native DATA0136 caller boundary

M2af is **Research / Blocked for the primary native caller handoff**. The exact
base is `f5f457988b9f380dc048d9e77acd9a141b6c9dfb`, branch
`codex/p28-post-return-selector-m2ae`. The research branch is
`codex/p28-native-data0136-caller-m2af`.

The retained state that makes 064C take its primary branch also makes 0662 skip
CAL0664. The authorized existing source contract supplies no independent owner
that can clear 012A.3 while preserving that taken 064C condition. This is a
specific obstruction to **064C taken → native CAL0664 →56BE**, not a claim that
every static route to CAL0664 is impossible.

There is no new runnable operation, scenario or CLI. Runner remains **0.38.0**;
the suggested `nativeData0136CallerHandoff` operation is unsupported by that
historical runner. No producer caller capability, instruction admission or
semantic fix is added. Existing [M2ae](M2AE_POST_RETURN_SELECTOR_HANDOFF.md)
continues to stop before 064C, and [M2v](M2V_DATA0136_NATIVE_TECHNICAL_SLICE.md)
retains its historical `TechnicalSeededEntry56BE` classification.

## Exact caller forms and primary condition

The matching private original/listing and manufacturer instruction pages establish
the exact forms below. Decoder recognition and listing labels alone confer no
dynamic admission. OEM bytes, ROM/listing windows, manual pages and private source
hashes remain private.

| PC | Length | Exact form | Effect and next PC | Primary ISA page |
|---|---:|---|---|---|
|064C|3|JBS off011F.3,rel8|Read the retained byte011F; bit3 set takes065F, clear falls through064F; flags retained|3-65|
|065F|3|RB off012A.3|Read old bit3, clear that bit, set ZF to its inverse; A, CF, HC, DD and other PSW bits retained; next0662|3-114|
|0662|2|JNE rel8|ZF clear takes0667; ZF set falls through0664; flags retained|3-66|
|0664|3|CAL addr16|Code-owned target56BE; returnPC0667; word return store at oldSSP, thenSSP−2, thenPC56BE|3-29|

Actual validated M2ae exit establishes DD0, LRB0021, off-page0100 and local
bank0108. The primary caller forms above retain DD until the producer's first
word load, if that load is reached. The listing's DD1 annotation at 065F is not
a recovered incoming value and does not authorize a host PSW change.

RB tests the **old** bit while resetting it. Therefore old012A.3=1 yields
ZF0 and JNE0662 taken to 0667, skipping CAL. Old012A.3=0 yields ZF1 and the
fallthrough CAL. A post-RB cleared bit cannot be substituted for the old bit in
this decision. Incoming M2ae ZF is overwritten by RB; incoming CF does not select
the JNE. No local register, 013C or 0128 operand supplies this primary gate.

These are static semantics and independently derived control predictions.
M2af does not execute 064C, 065F, 0662 or 0664 and records no native caller write.

## Retained ownership closes the primary route

The M2ae machine starts from the established 00/55/AA technical scratch histories.
Its closed initial schema has no explicit 011F field. The existing full-byte011F
owner is retained scratch-backed software history; it is not split into new
caller-bit3 and producer-bit2 booleans. No bounded upstream writer in the audited
chain changes that byte, and no per-event011F source is introduced.

The independent C# owner in
[P28QuartetHandoffValidator](../src/HondaEcu.Core/P28QuartetHandoffValidator.cs)
initializes 012A as `(scratch & ~2) | (bit012a1 ? 2 : 0)`. The existing scenario
source owns only bit1. M2x reads that bit without clearing bit3. On the completed
below route, native5685 clears only 012A.7; the independently specified effect is
`old012A & ~128` in
[P28BelowSecondP2Model](../src/HondaEcu.Core/P28BelowSecondP2Model.cs).
M2ae063E..064A writes local0108, 0128 bits0/1 and selector013C, preserving 012A.

| Scratch history | Retained full byte011F |064C condition| Retained012A after completed below/M2ae path | Primary gate prediction |
|---|---|---|---|---|
|00|00: bit3=0,bit2=0|Fallthrough064F|00 or02; bit3=0|Primary taken route not selected|
|55|55: bit3=0,bit2=1|Fallthrough064F|55 or57; bit3=0|Primary taken route not selected|
|AA|AA: bit3=1,bit2=0|Taken065F|28 or2A; bit3=1|RB setsZF0; JNE takes0667;CAL skipped|

The table includes both allowed initial012A.1 values. Neither selector013C0..3,
the existing 0128.2 source, nor the upstream 011B.7 source changes 012A.3 on the
completed primary below route. Partial upstream paths do not establish actual
M2ae entry064C and cannot supply a replacement caller state. Historical next
events encounter retained0117 and do not manufacture a new completed M2ae state
with the missing gate owner.

Adding a new initial011F byte, initial012A.3 field, per-event gate toggle or
whole-byte initializer would expand the closed source contract. These sources
are not introduced. No host PC064C/0664/56BE shortcut,
second machine, serialization handoff or ABI repair supplies a witness.

## Fallthrough is a separate static route

Mandatory fallthrough audit identifies 064F JBS011B.7→065F, otherwise 0652
RB012A.0→0655 JEQ→065F. If that JEQ is not taken, 0657 first accesses TRNSIT.2,
followed by 065A JNE and 065C SB00B4.6 before 065F.

Existing upstream inputs can select 011B.7. Consequently a branch-not-taken064C
control can have a static route to 065F with old012A.3 clear, and potentially
CAL0664. That alternative is **static only** in this milestone; it does not
satisfy the required primary064C-taken handoff. No optional fallthrough execution
or TRNSIT effect is added. The narrow architectural storage model from
[M2ab](M2AB_POST_P2_CONTROL_HANDOFF.md) does not imply timer, edge or IRQ recovery.

## Producer entry, slot and peripheral evidence

The established chain remains one retained Cpu/Bus through M2r/M2x, the explicit
PC-only05ED→063B harness seam, native CAL063B, the validated below body,
native RT5688→063E, and M2ae063E..064A→stop-before064C. Those are historical
upstream claims, not new M2af caller or producer executions.

A validated AA M2ae exit has PC064C, LRB0021, SCB2 and SSP07FE; DP/USP retain AAAA
scratch history, local r0 reflects the native selector increment, and A/PSW/X1/X2
come from the actual upstream path. This is an **entry064C observation**, not
an actual native56BE entry or an inferred instruction-by-instruction producer
trace.

Historical M2v enters 56BE using LRB0021, SCB2, USP0280, technical PSW1102 and
SSP07FE. Incoming A and DD/ZF are overwritten by the first load, and its bounded
producer path has no material incoming USP/DP/X2 use. These historical live-in
facts do not establish a new caller entry. The full actual56BE boundary and
field-by-field ABI comparison remain NotRun because CAL0664 is not executed.
No technical initializer, `acquisition::enter`, PC assignment or pointer/stack
normalization supplies a producer entry.

The audited upstream bounded chain has no native00A2 writer establishing a
producer sample slot. Retained AA would supply 00A2=AA, outside the reviewed 0..5
writer-index domain. A once-initial RawSoftwareSnapshot00A2 would address that
separate ownership requirement only after a permitted caller route exists.
It is **not applied** while the primary pre-call gate is blocked. There is no
per-producer slot rewrite or optional 00F0 mode1 source.

TMR2/003A word is still the mandatory first producer read under M2v, with
conditional IRQH/0019 byte and TCON2/0042 byte observations. M2af applies no frozen
observations and executes no new producer peripheral read or write. Their proposed
semantics remain ExplicitReadOnly, NoTimeAdvance, NoNewEvent and NoInterruptDelivery; wrong
widths and writes receive no new permission. TimerEvolutionNotModeled,
IRQDeliveryNotInjected andPhysicalTimestampNotEstablished remain explicit.

## No new frame or DATA0136 generation

CAL0664 would create a separate frame identity
`(writerPC0664,eventIndex,stackAddress,width16,returnPC0667,allNativeWriteOrder)`
using the retained SSP after M2ad's successful RT. That frame is distinct from the
historical063B→063E frame. No0664 frame is created in M2af, so pending-return,
SSP−2 and same-frame preservation are not claimed as actual observations.

If the bounded producer were reached, stop-before5719 would leave its0667
frame pending and terminate the sequence for further events. It would not
balance SSP, execute RT5801 or return0667. This is a future contract requirement,
not a performed host stack cleanup or new execution permission.

M2af has zero new native branch executions, CAL0664 executions, 56BE entries,
TMR2 reads, no-writer producer invocations, 5707/56F3 writes, native0136
generations or 570E generation reads. Native caller no-write and writer successes
are both NotRun. Same-value, zero/nonzero and multiple frozen TMR2 cases are also
NotRun; existing M2v/M2w counts are not imported as new caller evidence.
Fresh upstream M2ae revalidation is counted separately; exact corpus, partial
and NotRun totals are recorded in the private final report and do not contribute
to M2af native caller or producer counts.

No ready0136, expected0136, arithmetic result, writer, branch, returnPC, SSP or
arbitrary RAM input is added. Existing0128 history is preserved, including the M2ae
bit0/1 effects; producer0128.3 behavior does not run. The historical M2v model's
constructor/Run reset and per-observation slot application are not used as an
adapter from M2ae state. No production model/protocol change is made.

## Static future producer tail

5719 is CMPB00A2,#5, **not RT**. The static tail has further software gates and
pointer/live-in requirements, PSWL.4 transfer at5739/575C, MULB paths572D/572F,
JLE forms574A/5750 and later wordMUL forms. These require separate exact-form
and live-in review; historical JGT/JLE uncertainty is not promoted by a label.
Known0136 readers5782/5787 remain static, outside the bounded producer target.

The earliest identified timer access on that audited tail is 5793 word TM3,
followed by TMR2 reads/subtraction and later TMR3 writes. Control effects include
57AB RB TCON3.2 and later TCON3.3 changes. Port effects include 57F2 P1.7,
57F6 P1.3 and 57FE P1 read; further indirect data accesses require ownership
review. Full routine RT5801 and the hypothetical return0667 are static only.
All tail instructions, timer/control/port effects and producer return are NotRun.

## Status and preservation

`Branch064C=NotRun;StaticConditionTakenForScratchAA`;
`PostReturnTakenPath=PrimaryBlockedByRetained012A3`;
`NativeCal0664To56BE=NotRun;PrimaryTakenRouteSkipsCall`;
`ProducerEntry56BE=NotRun`;
`TechnicalSeededEntry56BE=NotUsedInM2af`;
`NativeProducerCallFrame=NotEstablished`;
`NativeProducerReturnTo0667=NotRun`;
`Data0136Mode0Producer/Data0136Generation5707/Data0136Reader570E=NotRun`;
`Mode1Producer=NotRun`;
`FrozenPeripheralObservations=NotRun;NoSourcesApplied`;
`TimerEvolution=NotModeled`; `IRQDelivery=NotInjected`; `ElapsedTime=None`;
`RecoveredCallerScheduler/Recovered0196Scheduler/RecoveredEcuScheduler=NotEstablished`;
`EnclosingIRQFrame=NotEstablished`; `ProducerTo2330SchedulerSeam=NotEstablished`.

Historical M2ae selector source, M2ad CAL/RT, M2ac second P2, M2v technical entry,
M1i acquisition and RTI contracts remain unchanged. No enclosing IRQ frame,
caller/0196/ECU scheduler, producer→2330 schedule, timer evolution or physical
units are established. M2tJgtBlocked/Unresolved; strictM2iBlocked.

FirmwareBIN/binding/compensation/exportplan/receipt/token0;
PcInspectionOnly/NotFlashReady;physicalRpmAvailablefalse; physical fuel/time/
degrees unavailable; GUIr3paused/NotRun; D1/D2interactive acceptance and
hardware/fullbootNotRun. Public CI uses invented fixtures only. Private original,
listing, manuals, scenarios, reports and source hashes are untracked; new private
artifacts stay under `private/reports/m2af/`. No automatic M2ag, 5719 continuation,
RT5801, return0667, scheduler/IRQ/timer recovery, GUI or hardware follows M2af.
