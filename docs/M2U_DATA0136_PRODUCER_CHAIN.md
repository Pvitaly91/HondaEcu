# M2u - DATA0136 producer provenance

Delivery: **Research / Partial / ProducerNotRun**. Static producer provenance is
established within the supplied decoded listing; dynamic integration is **NotRun**.
This is the expressly bounded static fallback, not a native producer validator.
Runner remains **0.28.0**. No new operation, runnable scenario, CLI, permission,
calibration, firmware output or version bump is justified.

Base: `origin/codex/p28-div-jgt-calculation-chain-m2t`, exact
`83e38bc0ffe75927c0200c450615adaf3962c7a0`. Target:
`codex/p28-data0136-producer-chain-m2u`. Old M2s/M2t artifacts and contracts stay
unchanged. M2s is Partial; M2t is Blocked/Partial; JGT predicate unresolved.

## Scope and source inventory

Use the neutral name **softwareWord0136**, or divisionSource0136 specifically at
the calculation reader. It is not globally a divisor parameter. All 11,499
decoded instructions were checked against the matching original, with zero byte
mismatches. Exact bytes, private source identities, all candidate accesses and
caller paths remain under ignored `private/reports/m2u/`, not in public fixtures.

The inventory includes word and byte effects, arithmetic read-modify-write,
both sides of exchange, bank aliases, direct-page/SFR distinction, signed USP
displacements, indexed/indirect domains and implicit stack effects. No listed
block/copy form or explicit byte store at0136/0137 was found. Word alignment can
make an odd address alias the containing word.

| Writer site | Source/control | Classification |
|---|---|---|
|56F3, full word|Mode011F.2 set; unsigned divided arithmetic, possible zero|IRQDependent / TimerDependent / PeripheralDependent; NotRun|
|5707, full word|Mode011F.2 clear; wrapped sample difference or control-selected zero|Same blocked caller context; NotRun|
|2710, indirect full word|Reset RAM-clear sweep can intersect0136|Reset-dependent static candidate; full boot NotRun|
|5C68 /5C6C, indexed word exchange|RAM-test helper can intersect0136; temporary pattern then restoration|Reset callers2689/268D and runtime callers3EB8/3EBC; pointer/schedule dependent; NotRun|

There are **587 conservative writer candidates**, not 587 proven writes: two
explicit runtime stores, 232 unresolved indirect/indexed domains (including the
conditional sites above), and 353 implicit SSP stores. The **333 reader
candidates** comprise four explicit reads, 242 unresolved pointer domains and
87 implicit stack reads. Unknown pointer/stack domains stay Unknown. Static
listing annotations are hypotheses, not recovered live bank/stack state. This
is not complete whole-ROM code/data recovery or a global alias exclusion proof.

Reset/test restoration is a new generation even when the final value equals
the old value. Similar encoded offsets in a different direct page are not0136.
Neither reset initialization nor RAM testing justifies an engine-state value.

## Caller and mandatory-access blocker

The runtime body begins56BE, with CAL callsites0611/0635/0664, returns0614/0638/
0667 and enclosing RT5801. Conservative graph paths reach the callsites from
INT1 entry0379 and serial receive entry03ED. These are static possible paths,
not feasible scheduler traces. No continuous path from established M2t22B1 is
established; no independent software-service caller is established.

Listed ABI: LRB0021, local bank0108, SCB2, USP0280. Incoming accumulator is
overwritten; DD becomes word at the first load. Pointing-register slots belong
to SCB2, not the local bank. Incoming X1 is later clobbered; X2/DP are not prefix
value sources. SSP/hardware interrupt frame and actual caller scheduling remain
Unknown. Ordinary CAL return handling is not evidence of an IRQ saved frame.

First instruction56BE unconditionally reads **hardware TMR2**, before mode
selection and before the no-write test. Mode1 later selects RAM00F0, but does not
skip that timer read. Software RAM00F0 itself is written from hardware capture;
00AE is a software byte counter whose timer-overflow writer is in IRQ context.
TCON2 and IRQH remain peripheral state, not default-zero RAM.

Historical [M1i acquisition](M1I_CAPTURE_SEQUENCE_VALIDATION.md) already has
explicit frozen, read-only TMR2/IRQH/TCON2 observations for the mode0 body. That
bounded technical slice resets PC/entry registers and seeds acquisition history;
it does **not** recover a software caller, scheduler or interrupt delivery. Its
initial state also contains ready0136. M2u cannot relabel that old diagnostic
entry as EstablishedScriptedSoftwareCaller merely because the body matches.
Neither its frozen observations nor caller address alone authorizes an IRQ entry
or a new producer-to-calculation seam. The mode1 divided path is outside its
admission. Existing software timer/counter-body scheduling is a different service.

Consequently M2u invokes no producer: **ProducerNotRun_IRQDependent**, additionally
timer/peripheral dependent. The research boundary is **before56BE**. No PC jump,
pending interrupt simulation, saved-frame seed, RTI proof, callback/NOP or new
frozen/default timer is introduced.

## Static arithmetic and source ownership

Independent C# research hypotheses take abstract raw inputs, never Rust actual
values. They are not admitted scenario inputs or executable expected values.
`P28Data0136ProducerModel.Current` always has NotRun status, null expected0136 and
zero native writes. No hypothetical number can be labeled NativeWritten.

Let S be the selected raw sample, P the prior RAM word00EE and C the byte00AE.
If S bit15 is clear and IRQH.0 is set, C increments modulo256. SB0128.3 sets ZF
from the **previous** bit: prior bit0 skips both writers; prior bit1 enables the
write path. Mandatory TMR2 access still occurs on a would-be Held path.

On the divided path, delta=(S-P) modulo65536 and borrow=(S<P). The upper byte
is (C-borrow) modulo256, with the next upper byte cleared. The unsigned dividend
is upperByte*65536+delta. Divide by the fixed immediate6, truncate; retain the
quotient if it fits a word, otherwise clear to0. This is **overflow-to-zero, not
saturation**. A dividend below6 also gives0. Counter underflow and increment
overflow wrap as bytes. No producer-prefix ROM data table or editable coefficient
is established; immediate6 is read-only code, not a calibration.

On the direct path, value=delta unless TCON2.2 is set, in which case value=0.
Equal selected/prior samples also give0. These are software/abstract conditions,
not evidence that zero is impossible on a running engine. Zero, minimum-positive,
interior and upper-word hypotheses are model-only, not reachable native outputs.
The subsequent byte-shift/index EXTND is **signed** extension, not zero extension;
arbitrary index/address wrap is not admitted.

The source ledger records writers of00EE,00F0,00AE,011F,0128,00A2 and the SFRs,
with exact widths and aliases. Multi-bit/word storage and unknown indirect
effects prevent simply declaring independent snapshot owners. No new snapshot
of those fields is admitted. Full producer tail5801 is not executed or closed.

## Readers, arbitration and generation

Known word readers: **2330** (native er2 transfer), **570E**, **5782**, **5787**.
MOV remains word even with listed DD0. The latter readers can consume within
the producer routine before any calculation invocation;2330 is not globally
first or sole. Possible intervening writes and subsequent consumers cannot be
ordered without an established scheduler. Same-generation2330 consumption is
**NotRun**, not inferred from equality.

Within one invocation,56F3 and5707 are mutually exclusive. Across invocations,
A-only/B-only/A->B/no-writer scheduling is unproved. One storage owns the lifetime,
not two independently supplied writer results. Generation identity is
`(writer PC, event index, write order, value)`, preserving same-value writes.

| Lifetime | Meaning in the research guard |
|---|---|
|InitialHistory|No native generation established; diagnostic history only|
|NativeWritten|Full-word native journal agrees with independently expected writes|
|Held|No write; retain the last generation, including its original identity|
|PartialNativeWritten|Completed stores retained before a terminal partial producer|
|NotRun|No accesses/inputs/consumption; retained history is not a fresh result|

Internal `SoftwareWordProvenance` guards invented journals against partial-byte
or neighboring overlap, host overwrite, wrong-width reader, stale identity,
missing/reordered word-read/register-write/divisor-read and post-partial execution.
It is **not wired to an OEM runner operation** and does not verify OEM instruction
forms by itself. Expected writes must come from an independent model. Toy tests
are scaffolding, not same-generation OEM evidence.

## Historical policy and downstream boundary

M2s/M2t still accept their one authoritative once-initial0136 storage snapshot.
It remains a bounded diagnostic/storage-domain input, not native-produced0136,
not a recovered engine value and not silently migrated into M2u. Actual historical
positive and zero reports/statuses are rechecked separately, not counted as new
producer coverage. Old acquisition diagnostics are not retroactively relabeled.

No new producer->2327/232A/5991/232E/2330 seam is introduced. Historical positive
DIV/CMP still stops **before233A**; zero still stops **before2333** without numeric
divide0 outputs. JGT/JLE/global executor, M2t admission, report semantics and old
JSON remain unchanged. Native0136PositiveToJgtBlock and ZeroToDivBoundary counts
are0 in M2u. Retained output is not fresh calculation completion.

## Coverage and verification

M2u native ProducerStrict/Zero/Positive/Held/Partial, writer invocations,2330
generation reads, PositiveToJgtBlock/ZeroToDivBoundary, A/B controls and source
sweeps: **all0**. ProducerNotRun is one static audit decision, not an executed
event. The old78 M2t positive prefixes are not added to M2u counts.

Fuel-cell and adaptive mutations do not appear in the audited producer-prefix
dataflow; equal-source hypotheses are unchanged, but no native A/B experiment or
DivisorSame_NumeratorChanged witness is claimed. Source variation is model-only,
not firmware mutation. No combined mutation or new0136 mutation is introduced.

New public regressions: four Rust invented memory-only programs/dispatch tests
and36 Core cases, including14 model-only hypothesis cases. They cover full-word
native store/read/er2/DIV transfer, same-value ordered writes, cross-event Held,
partial retention and terminal refusal, fifteen provenance forgeries, schema/
version refusal and cancellation/deadline non-publication. Existing real-process
timeout/cancellation and historical integration suites remain in full QA.

Required QA: pinned Rust1.85.1 release build/test locked/fmt; repository .NET8
Release build/headless test and format verification for both solutions; diff
check, privacy guard and full protected-file hash comparison. Exact final counts,
runner hash, compatibility, remote SHA and three CI jobs are recorded in the
private final report. CI uses only invented/public fixtures.

PcInspectionOnly / NotFlashReady; physicalRpmAvailable=false; physical fuel/time/
degrees unavailable. Quartet consumers NotRun; strict M2i Blocked; GUI r3 paused/
NotRun; D1/D2 interactive acceptance NotRun; hardware/full boot NotRun. Local
desktop tests are headless, not GUI acceptance. New firmware BIN, bindings,
compensation, export plans/receipts/tokens:0. No automatic M2v/JGT/quartet/GUI/
hardware work follows the final private report.
