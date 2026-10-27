# M2bz - native post-return selector013C continuity

This document specifies a bounded research experiment and its independent
instruction obligations. It is not an execution receipt or a delivery verdict.
Actual observations, QA, exact-SHA CI and the final preservation-qualified
verdict belong to the separate source-bound private report.

The accepted base is M2by `82c34c0465a5d92ce5cc30f2daf47f24174a10d5`,
branch `codex/p28-word0196-cal-rt-frame-continuity-m2by`. M2bz uses
`codex/p28-word0196-post-return-selector-continuity-m2bz`. Its new default-off
feature `p28-word0196-post-return-selector-continuity` depends on the existing
CAL/RT feature. Existing constructors, budgets, source manifests and historical
runtime contracts retain their meanings.

## Independent evidence and the exact extension

The manufacturer authority is the MSM66201 Instruction Manual, first edition
September1991, SHA-256
`f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271`.
Complete existing local page images were visually reviewed for LB3-70,
STB3-155, ANDB3-24, SBR3-136, paired RBR3-115 and INCB3-61, together with
local-register/current-page addressing1-11..1-14 and DD selection1-23..1-24.
No new download, render or copy of a primary document is needed. Raw pages and
private source bindings remain private; this document contains no ROM byte
window or opcode stream.

[M2ae](M2AE_POST_RETURN_SELECTOR_HANDOFF.md) supplies the independently reviewed
eight-instruction selector semantics and the exact historical
`byte-incb-r0-half-carry` correction. Its historical runtime is reference
evidence, not a new M2bz observation. [M2by](M2BY_NATIVE_CAL_RT_FRAME_CONTINUITY.md)
supplies the current-machine CAL frame and matching RT consumption;
[M2bx](M2BX_NATIVE_BELOW_SECOND_P2_CONTINUITY.md) supplies the retained39-step
Below body and second-P2 obligations.
[M2ad](M2AD_CAL_RT_ROUNDTRIP.md),
[M2af](M2AF_NATIVE_DATA0136_CALLER_HANDOFF.md),
[M2ag](M2AG_FALLTHROUGH_DATA0136_CALLER.md),
[M2aj](M2AJ_PRE063B_CALLER_PROVENANCE.md) and
[M2aw](M2AW_NX8_200_TARGET_ABI_CONTRACT.md) retain their exact historical
scope, caller restrictions, source classifications and unresolved architecture
questions. Decoder-table recognition alone is not manufacturer evidence.

One production CPU and one Bus execute the following complete expected route:

```text
063B CAL
54F5 54F8 54FA 54FC 54FD 5501
556F 5571 5572 5575 5576 5578 557D 55BF 55C1 55C3
55C5 55C8 55CB 55CD 55CF
55D2 55D3 55D5 55D8 55DB 562C 562E 5631 5633
565D 565F 5661 5671 5673 567E 5680 5682 5685
5688 RT
063E 0640 0641 0643 0646 0647 0648 064A
064C STOP BEFORE instruction acquisition, decode or execution
```

The independent composition is1 CAL +39 body instructions +1 RT +8 selector
instructions =49 retirements. Retirement41 is RT5688, retirement42 is LB063E
and retirement49 is STB064A. The closed executable inventory grows from51
reviewed sites to59; inventory size is distinct from the selected49-step route.
The old M2by41-step admission continues to stop at its old boundary.

Private PROGRAM consists of two immutable, unchanged original-image windows:
`[063B,064C)`17 bytes and `[54F5,5689)`404 bytes, total421 bytes. The caller
window contains the three-byte CAL and the14-byte post-return suffix. Both
windows come from the same verified private image at their original PCs.
Window membership does not admit intervening gap instructions. There is no
relocation, padding, patch, hand-written replacement or writable code segment.
Public CI uses a separately invented program with a distinct source identity;
it is not an original-ROM execution witness.

## Eight exact instruction obligations

Let `s` be the single admitted initial DATA013C byte and `b` the actual retained
DATA0128 byte at the RT exit. Let `h` be the retained AH and `c` the retained CF.
The strict selector domain is exactly `s in {0,1,2,3}`. The following table gives
expected after-states derived from the primary semantics, not CPU output.

| Retirement / PC | Exact form | DATA effect | AL / flags after execution |
| --- | --- | --- | --- |
|42 /063E|LB A,off013C|Read byte013C|AL=s; ZF=(s==0); DD=0; CF/HC retained|
|43 /0640|STB A,r0|Write byte0108=s|AL and all flags retained; DD0 required|
|44 /0641|ANDB A,#01|No DATA operand read; immediate1 is code-owned|AL=s&1; ZF=(AL==0); CF/HC/DD retained|
|45 /0643|SBR off0128|Byte RMW: b becomes b OR (1<<(s&1))|AL retained; ZF=inverse OLD selected bit; CF/HC/DD retained|
|46 /0646|INCB r0|Read old0108=s; write0108=s+1|AL retained; ZF=0; HC=0 in the strict domain; CF/DD retained|
|47 /0647|LB A,r0|Read the actual incremented byte0108|AL=s+1; ZF=0; DD=0; CF/HC retained|
|48 /0648|ANDB A,#03|No DATA operand read; immediate3 is code-owned|AL=(s+1)&3; ZF=(s==3); CF/HC/DD retained|
|49 /064A|STB A,off013C|Write the current AL to byte013C|AL and all flags retained; DD0 required|

AH remains `h` throughout all eight instructions; a byte load does not extend
into AH. CF remains `c`. OtherPSW, LRB, SCB, restored SSP, X1/X2/DP/USP and
unwritten RAM/bank bytes remain retained. The comparison must include complete
PSW and architectural snapshots at every boundary, not just final AL. Incoming
DD is the actual callee-produced RT state; LB063E establishes DD0 for both STB
forms and both ANDB forms. An assembler or listing DD annotation is not a seed.

LRB0021 gives current page0100 and local bank0108..010F. Therefore local r0
aliases DATA0108 and the low byte of er0, while r1/DATA0109 must be preserved.
SCB is retained from the actual PSW low3 bits and selects the inherited pointing
register bank. Neither LRB nor SCB is reinitialized at063E. Incoming r0 is
overwritten by0640 before INCB or LB reads it; it is not a selector producer.

The suffix has four functional byte DATA reads and four functional byte DATA
writes, in order: read013C; write0108; read0128/write0128; read0108/write0108;
read0108; write013C. Register/accumulator updates and PROGRAM/immediate reads
are distinct from these DATA events. Logical access, raw byte, write-only,
all-native and retirement ordinals remain separate fields. No read or write may
be deduplicated merely because the numerical value is unchanged.

## Selector source and fresh writer generation

Before the first CAL, one explicit technical byte snapshot admits DATA013C.
Its exact classification is
`RawSoftwareSnapshot0..3_OnceOnly_InitialGenerationNone`.
It does not claim a native upstream owner. After functional execution starts,
no host write, repeated initializer, per-event selector, result seed, partial
word overwrite or imported historical generation is permitted at013C.

The result follows independently from byte increment and masking:

```text
r0 = (s + 1) & 0xFF
newSelector = r0 & 0x03
0 -> 1; 1 -> 2; 2 -> 3; 3 -> 0
```

For old3, final r0 is4 while AL and DATA013C are0. The formula is an oracle
obligation; production execution must obtain it through the eight actual
instructions. The final byte write must create
`CurrentExecutionNativeSelectorWriter064A`, tied to the current machine/session,
PC064A, retirement49, actual address/width/value and independently checked
logical/raw/all-native write identities. Matching a value from an old machine
does not satisfy this obligation.

Historical direct writers03D7/0551/15A0 remain excluded. This closed experiment
does not make064A the sole writer in the whole firmware; generic aliases and
unreviewed contexts remain Unknown. The resulting generation is
`DATA013CGenerationAvailableForFutureReader` as a static availability statement.
There is no new0584 or05DF reader, next event, scheduler or whole-cycle proof.

## SBR ambiguity, retained0128 and INCB half-carry

Printed3-136 has a real internal inconsistency: its Function line assigns0 to
the selected bit, while its SET heading and description explicitly require1.
The paired RBR3-115 is the separately encoded RESET form and its Function
assigns0. M2bz retains the narrow M2ae interpretation based on SBR's explicit
SET description and the paired distinction. This is a disclosed source
qualification, not a manufacturer-issued erratum or general bit-operation
promotion. Both SBR descriptions of ZF refer to the target bit **before** the
write. Testing the final, already-set bit would incorrectly force ZF0.

Only bit0 or bit1 is selected after AND01. Bit2 and every other neighbor remain
unchanged. SBR emits a real read/write pair, including a same-value write with
a fresh current-execution identity. In the inherited closed corpus, retained
0128 is05: even selectors choose already-set bit0 and keep05, while odd
selectors choose clear bit1 and produce07. With four cases per selector this
requires eight same-value and eight changed-value SBR writes per domain.
This corpus fact does not widen the generic initial-state contract or authorize
a pre-SBR0128 repair.

The existing exact compact `INCB r0` correction
`byte-incb-r0-half-carry` remains unchanged. Primary3-61 requires byte increment
with updated ZF/HC, retaining CF/DD. Independent arithmetic gives
`HC=((oldR0 & 15)==15)` and `ZF=(((oldR0+1)&255)==0)`.
The strict selector domain0..3 therefore overwrites any incoming HC with0 and
sets ZF0. Broad byte/DD/CF/old-HC/bank controls belong to separate invented
decoded-form regressions; they do not widen DATA013C admission. M2ae's preserved
RED/GREEN receipts are historical proof of that correction, not new QA results.

## Retained frame, P2/control history and technical ownership

All first41 M2by obligations remain: one real CAL writer, an unmodified current
frame through the39-step Below body, matching RT consumption, restored SSP,
retained callee A/PSW, PROGRAM/DATA journals, first/second P2 generations and
TCON0 generations. RT does not restore caller A/PSW. The eight new instructions
neither create a second stack frame nor modify the consumed frame bytes, P2 or
TCON0; restored SSP remains unchanged through064A.

The inherited technical SSP slots0702/0720/07FC/07FE must remain even,
nonwrapping and disjoint from all owned RAM, selector013C, pointing banks,
CPU aliases and control registers. These are admission restrictions, not
physical stack-safety evidence. Unknown physical SF applicability remains;
technical host-SF variants do not become hardware observations.
`DATA0196Owner=TechnicalSeed_NoNativeProducerInThisSession` remains. No old
M2ad/M2ae native owner, scheduler or write generation is imported into this run.

## Diagnostic counters and manufacturer timing

| PC / form | Manufacturer INT | Retained software diagnostic delta |
| --- | ---: | ---: |
|063E LB off-page|4|4|
|0640 STB r0|2|2|
|0641 ANDB immediate|4|4|
|0643 SBR off-page|9|9|
|0646 INCB r0|3|2|
|0647 LB r0|2|2|
|0648 ANDB immediate|4|4|
|064A STB off-page|4|4|
|New eight-instruction total|32|31|

The INCB primary table explicitly lists INT3. The unchanged decoder's generic
one-byte fallback supplies diagnostic2; the half-carry fix did not change this
counter. Both values must be retained and compared in their separate roles.
Inherited first/second P2 software6 versus primary INT7 qualifications also
remain. No global timing patch is included. `DiagnosticCycleTimingEquivalenceNotEstablished`
and `PhysicalTimingEquivalenceNotEstablished` remain. Retirements, software
counters and primary internal-memory cycle entries are not elapsed ECU time,
external-memory timing or electrical peripheral behavior.

## Freeze, bounded acceptance and remaining limits

Before the first final positive runtime, freeze the exact source fingerprint,
both source windows, all input cases, independent oracle, all49 expected
boundaries, complete CPU/RAM/flags, DATA/PROGRAM journals, frame/selector writer
identities and diagnostic expectations. The closed corpus is16 private plus16
public cases,49 retirements each:784 per domain,1568 total. It must cover every
selector four times per domain, all four SSP slots, retained technical host-SF
variants and control/P2 histories, selector3 wrap and both reachable SBR old-bit
outcomes. No Cartesian stress expansion or old5470-case rerun is required.

Private execution and separately invented public regressions have distinct
authority. A passing contract or historical trace does not establish a new
runtime. Acceptance needs actual complete observations, an independent full
comparison, meaningful typed negative refusals, compatible unchanged historical
validators, required QA, exact-SHA CI and full decompressed public canonical
byte equality across local/Ubuntu/Windows. The expected CI matrix grows from15
retained jobs to17 through one new Ubuntu/Windows pair. Failed or skipped
mandatory gates cannot be reported as passed.

All Cargo output must use the milestone-owned isolated target and its preflight
guard. Historical runner fences, protected source/evidence and the inherited
single authorized generated-runner loss remain distinct from new changes.
Report `AuthorizedPreservationExceptions=1`, strict preservation false and
`OtherUnauthorizedProtectedDifferences=0` only after the corresponding audit.
The inherited exception is not ordinary zero-difference preservation.

STOP before064C is unconditional. Its JBS,064F/065F, a next event, timer/IRQ
evolution, scheduler recovery, downstream native handoff, target placement,
firmware generation/flashing, GUI and hardware remain outside this milestone.
`FirmwareReady=false`, physical SF and native stack safety unresolved, and
actual hardware ECU execution unobserved all remain. After M2bz delivery, STOP;
this document does not authorize M2ca.
