# M2ah — DATA0136 post-NoWrite software tail

Delivered scope: **Research / Blocked at the first unowned live-in**, not
ValidatedToTimerBoundary. Exact M2ag base is
`3f2ab98d06b7afeef91831b4ff96bb863f795394`, delivered with CI3/3 in
run37506118310. New runner0.40.0 operation `data0136TailToTimerBoundary`
and read-only `research p28-fuel data0136-tail-check` use the exact M2ag
scenario fields under purpose `native-data0136-tail-to-timer-test`.
There are **zero new semantic inputs**.

## Native entry and actual ownership boundary

One retained Cpu/Bus carries M2r/M2x, disclosed PC-only05ED→063B harness seam,
native CAL063B/callee/RT5688, M2ae and M2ag caller/CAL0664/FirstObservationNoWrite.
Only M2ah continues the actual producer exit5719. There is no host PC5719,
second machine, serialization/RAM-copy handoff, ABI/PSW/pointer/stack/slot seed.

Exact CMP5719 reads the retained byte00A2=0 and compares it with code-owned5.
ZF0/CF1, HC/DD and the operand/A/registers are preserved; JNE571D naturally
takes5722. These are the only two newly admitted forms:
`CMPB N'8,#N8` with direct00A2/immediate5, and `JNE rel8` with audited
displacement3. Code range[5719,571F), budget2; STOP before5722, not a NOP or
host-selected branch.

**5722 JBS off019B.2 is not admitted.** Existing M2x RB05D5 clears only019B.0.
Its byte RMW generation preserves bit2 from scratch-backed canary history;
it does not establish a semantic owner of that bit. The inherited closed source
contract has no once-initial019B.2 source. Diagnostic value0 is not permission
to choose the JBS outcome. New initial019b2/tailBranch/ready result fields are
refused; no gate repair manufactures the desired timer-boundary path.
M2ag's explicitly authorized retained slot0 is not a blanket semantic permission
for unrelated scratch neighbors.

Later live-ins include00B8.0/.1,00A0 and RAM pointed to by nativeDP0358/035E.
They remain separate ownership gates, not new sources. DP would be overwritten
by native MOV before pointer use, but that alone does not own its pointed RAM.
Incoming X1/X2/DP/USP/local registers are not consumed by the two-instruction
prefix; no M2v technical ABI is applied.

## Primary ISA review and static-only forms

Complete manufacturer pages were visually reviewed privately using the PDF skill.
CMPB obj,#N8 printed3-42 confirms byte subtraction/borrow/equality and preservation
of HC/DD/operand. Exact JNE printed3-66 tests ZF0, signed displacement fromPC+2,
with flags preserved. Existing executor behavior matches; no semantic fix or new
fix identity is justified.

JLE is reviewed independently: printed3-66 **LE = CF1 OR ZF1**. The exactCF/rel8
forms574A and5750 both statically target572F, matching the existing executor's
`CF || ZF`. Public invented probes test all four CF/ZF states. This does NOT
resolve the contradictory GT row: M2t JGT233A remains Blocked/Unresolved and
its shared admission still rejects JGT after the JLE tests. JLE is **StaticOnly /
NotRun past the earlier live-in blocker**, not dynamically admitted by M2ah.

MULB printed3-101: AL×r0→wordA, ZF from full product; CF/HC/DD retained.
MUL printed3-100: A×er0→32-bit er1:A, ZF from full product; CF/HC/DD retained.
Invented numeric tests exercise these existing operations, not actual tail MUL
execution. No MUL/MULB arithmetic model or admission is used to bypass the
unowned branch. Unreached pointer/shift/decrement variants retain their own
future exact-form evidence gates rather than borrowing a mnemonic-wide fix.

5739 is specifically **MB PSWL.4,C** (CF→user PSWL bit4), not DD assignment;
575C is **MB C,PSWL.4** (that bit→CF). Manufacturer3-78/3-77 defines those
opposite byte-bit transfers. The first preserves arithmetic flags while writing
the user bit; the second changes CF only. Other user/SCB bits are retained.
Both remain NotRun, as do the later MB012A.5,C and all other tail effects.

## Complete static CFG5719..5793

Fresh private audit checks matching original/listing bytes, lengths and decode/DD
contexts, including all11499 listing extents. Below are the60 software instruction
extents before5793. This is a **static map, not executed coverage**; abstract
forms/PCs are published, never OEM byte windows. Per-instruction widths, symbolic
effective addresses, flags/register effects, live-in status and primary gates
remain in the private audit.

|PC|Exact abstract form|Length|Next / candidate targets|
|---|---|---:|---|
|5719|CMPB N'8, #N8|4|571D|
|571D|JNE rel8|2|571F,5722|
|571F|SLLB off N8|3|5722|
|5722|JBS off N8.2, rel8|3|5725,5733|
|5725|MOV DP, #N16|3|5728|
|5728|MB C, N8.0|3|572B|
|572B|SJ rel8|2|5739|
|572D|MULB|2|572F|
|572F|MULB|2|5731|
|5731|SJ rel8|2|5761|
|5733|MOV DP, #N16|3|5736|
|5736|MB C, N8.1|3|5739|
|5739|MB PSWL.4, C|2|573B|
|573B|LB A, N8|2|573D|
|573D|CMPB A, #N8|2|573F|
|573F|JEQ rel8|2|5741,572D|
|5741|JGE rel8|2|5743,5755|
|5743|STB A, r0|1|5744|
|5744|INCB r0|1|5745|
|5745|LB A, N8|2|5747|
|5747|ADDB A, #N8|2|5749|
|5749|CMPB A, r0|1|574A|
|574A|JLE rel8|2|574C,572F|
|574C|LB A, [DP]|1|574D|
|574D|ADDB A, #N8|2|574F|
|574F|CMPB A, r0|1|5750|
|5750|JLE rel8|2|5752,572F|
|5752|JBR off N8.0, rel8|3|5755,572F|
|5755|L A, [DP]|1|5756|
|5756|ST A, N8|2|5758|
|5758|DEC DP|1|5759|
|5759|LB A, [DP]|1|575A|
|575A|STB A, N8|2|575C|
|575C|MB C, PSWL.4|2|575E|
|575E|MB off N8.5, C|3|5761|
|5761|CLR A|1|5762|
|5762|MOV er0, N8|3|5765|
|5765|ST A, er3|1|5766|
|5766|LB A, N8|2|5768|
|5768|ADDB A, #N8|2|576A|
|576A|CMPB A, r0|1|576B|
|576B|JEQ rel8|2|576D,5785|
|576D|CMPB A, #N8|2|576F|
|576F|JNE rel8|2|5771,5777|
|5771|LB A, r0|1|5772|
|5772|JEQ rel8|2|5774,5785|
|5774|SLLB A|1|5775|
|5775|JLT rel8|2|5777,5785|
|5777|CMPB N'8, #N8|4|577B|
|577B|JNE rel8|2|577D,57A3|
|577D|CMPB r0, #N8|3|5780|
|5780|JNE rel8|2|5782,57A3|
|5782|MOV er3, off N8|3|5785|
|5785|CLRB r0|2|5787|
|5787|L A, off N8|2|5789|
|5789|MUL|2|578B|
|578B|LB A, N8|2|578D|
|578D|SLLB A|1|578E|
|578E|JGE rel8|2|5790,57BE|
|5790|ANDB PSWH, #N8|3|5793|

The linear next hardware instruction5793 is wordTM3 at003C. Conditional paths
can instead bypass it to57A3 or57BE, so5793 is not asserted to be inevitable.
Those branches and their later hardware/indirect dependencies remain static.
Known future map includes5795TMR2,57ABTCON3,57B3TMR3,57F2P1.7,57F6P1.3,
57FEP1 andRT5801/return0667. No hardware source is supplied and none executes.

## Retained DATA0136 and open native frame

Entry0136 is M2ag retained history, no5707/56F3 generation. The prefix performs
no0136/0137 read or write and no sample write; inspection values are labeled
diagnostic, not reader evidence. 5782 MOVer3,off0136 (word independentDD) and5787
L A,off0136 remain NotRun; no RetainedHistoryRead or fresh-reader causality is
fabricated. Retained continuity across the executed prefix is checked separately.

Native CAL0664 frame (writerPC,eventIndex,address,width16,return0667,global
native write ordinal) remains pending at07FE/07FF, SSP07FC. C# independently
owns its identity and word via the M2ag model. New tail has zero stack/RAM writes,
no overlapping frame access, no pop/RT/SSP normalization. Its ordered00A2 read is
appended to the same event-wide RAM/P2/control/frozen-capture chronology; the
write ordinal is not reset. Full CPU boundaries, A/PSW/DD/LRB/SCB/pointers/SSP
and all local registers are independently compared. NotRun events retain
state/frame without applying their inputs or another producer observation.

## Separate implementation, read-only contract and evidence

C# encodes byte0−5, flag update and JNE independently from primary semantics.
It never replays Rust results as expected operands. Root identity/contract,
exact extents/trace, accesses, journals, frame/history inspections, partial state
and terminal behavior are closed and checked. Unknown/duplicate source fields,
forged fresh generations, host5719/5782/5787/5793, branch/PSW/pointer/frame
repair, TM3 snapshot, timer/IRQ/RT/second-machine/second-invocation evidence fail.

```text
hondaecu research p28-fuel data0136-tail-check <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --runner <runner-0.40.0> --scenario <m2ah-scenario.json>
  --output <new-private-report.json>
```

An independently validated live-in-blocked report exits3/verification failure;
it is not presented as completed timer-boundary success. Missing upstream entry
and gate controls are reported separately. Actual counts, negatives, exact
compatibility pairs, sealed QA totals, preservation/privacy and exact-SHA CI
are recorded only in the new private final report. Synthetic/model/compatibility
and historical M2ag counts are never imported as new actual tail completions.

Historical M2ag still stops-before5719, M2ae064C, M2ad063E. M2af primaryAA route
stays Blocked. M2v stays TechnicalSeededEntry56BE; M2w remains an explicit
technical harness schedule, not a recovered producer→2330 scheduler. M1i/RTI
and JGT/global branch policies are unchanged.0.39 refuses the new operation.

PcInspectionOnly/NotFlashReady; physicalRpmAvailablefalse; physical fuel/time/
degrees unavailable; strictM2iBlocked; GUIr3paused/NotRun; D1/D2 interactive
acceptance/hardware/fullbootNotRun. Tail frozen peripheral reads0, no timer
evolution/IRQ delivery/elapsed time/physical timestamp. FirmwareBIN/newbinding/
compensation/exportplan/receipt/token0. No automatic M2ai,5722/JLE/5793/TM3,
laterTMR2/TMR3/TCON3/P1/RT5801/return0667/second producer/2330/JGT/GUI/hardware.
