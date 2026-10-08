# M2al - primary JGT2714 semantics and RAM-clear termination

**PrimaryConflictUnresolved / Research-Blocked.** Exact M2ak parent:
`428847347f83d1264c16bffc5d652d44e72d1101`. Runner remains **0.40.0**.
No production/executor/admission/CLI/scenario/version change; actual-ROM executions0.
The equality outcome and native loop termination are not resolved by choosing
the convenient predicate. A new, narrower **JGT-independent conditional target
reach proof** is separated from termination and runtime source ownership.

## Primary search and evidence independence

The complete relevant pages of the OKI MSM66201 Instruction Manual, first
edition September1991, were visually reviewed again: CMP3-35/3-37/3-38,
JC3-66/3-67, PR/LRB addressing, CLR/MOV/DEC/ST and supporting borrow/PSW rules.
Its exact JC GT form has manufacturer opcode C8 and signed rel8, with printed
predicate **ZF0 OR CF0**. The public archive PDF fetched during M2al is
byte-identical to the existing local original and M1c copy: one documentary
lineage, not three independent confirmations.

Targeted public searches covered MSM66201/nX-8/200 instruction revisions,
OKI/Rohm/LAPIS errata/notices and assembler/core material. A new independent,
applicable vendor document was obtained: [OKI OLMS-66K Series Instruction List,
E2E1025-27-Y2, January1998](https://datasheet.datasheetarchive.com/originals/library/Datasheets-UEA1/DSAFRAZ0014344.pdf).
All five pages were reviewed. It explicitly includes MSM66201/66207 and lists
JC, but supplies no exact GT boolean predicate or C8 flag-condition correction.
It is **not decisive primary clarification**.

Existing MAC66K third-edition November1993 material lists GT/JGT without a runtime
predicate. The separate [nX-8/500S second-edition June1999 manual](https://downloads.laboratoryb.org/insight/documents/OKI/nx_800.500S_core.pdf)
has AND and opcodeF0. Its basic assembler-level upward-compatibility statement
was checked, but does not establish exact C8 behavior on nX-8/200. That override
is rejected. Font-glyph loss in a Poppler render was addressed with a complete
PDFium-page review, not by treating extracted symbols as sole authority.

No applicable decisive erratum/revision or independently obtained compatible
silicon observation was found **in the reviewed sources and targeted search**.
This is not a claim that none can exist elsewhere. Emulators, third-party opcode
tables, ROM intent, instruction names and other ISAs are not silicon proof.
Only public-document GETs were made; no private ROM/dump/trace/material uploaded.
All downloaded PDFs, exact hashes, full-page renders and search diagnostics stay private.

## Exact flags and the conflict

CMP2711 is **word DP minus current-page off0086 word**, independent of the
listing label. It updates CF/ZF, preserves HC/DD and both operands; there is no
listed instruction between it and JGT2714. Borrow semantics and the zero-result
rule yield CF1 iff unsignedDP<USP and ZF1 iff DP=USP in the declared context.
This is not a transfer of x86/ARM behavior. JGT changes no flags and is not
DD-dependent; signedrel origin is PC+2.

| CF | ZF | Printed OR hypothesis | Existing AND hypothesis | Ordinary word-CMP state |
|---|---|---|---|---|
|0|0|Taken|Taken|Greater|
|0|1|Taken|Not taken|Equal|
|1|0|Taken|Not taken|Less|
|1|1|Not taken|Not taken|Unreachable from this ordinary unsignedCMP|

CF1/ZF1 remains a valid *four-state table input*, not a fabricated loop exit:
equality implies no borrow. Thus OR is true for **all three CMP-produced states**.
At equality the primary OR conflicts with EQ/LE logical labels; at less it
overlaps LT/LE. AND would complement the printed LE predicate, but consistency
is not independent primary validation. OR is not declared a verified vendor typo.
**Actual DP=USP outcome = NotEstablished. PrimaryValidated predicate = none.**

## Instruction-level bounded CFG2706..272A

Fresh integrity checking compares matching original/listing bytes and exact
decoded extents for these15 instructions/36bytes, not a repeated general inventory.
OEM windows stay private. The mathematical model is authored independently from
the executor and never creates Cpu/Bus or an operation.

| PC | Abstract exact form | Static next / target |
|---|---|---|
|2706|CLR A|2707;code-owned word0,DD1|
|2707|MOV USP,#N16|270B;native0356|
|270B|MOV DP,#N16|270E;native0480|
|270E|DEC DP|270F|
|270F|DEC DP|2710|
|2710|ST A,[DP]|2711;word store underDD1|
|2711|CMP DP,offN8|2714;wordDP-minusoff0086|
|2714|JGT rel8|Taken270E;fallthrough2716|
|2716|CMP DP,#N16|271A;wordDP-minus0098|
|271A|JLE rel8|Taken272A;fallthrough271C|
|271C|MOV USP,#N16|2720;native0098|
|2720|CMPB r3,#N8|2723;byte savedmarker-minus47;DD retained|
|2723|JNE rel8|Taken270E;fallthrough2725|
|2725|MOV DP,#N16|2728;native0300|
|2728|SJ rel8|270E|

Explicit context: genuine entry2706; LRB0010/currentpage0, SCB0, non-stack
accumulator, stable/asynchronous-free context and valid data-word storage.
CLR establishes A0/DD1; remaining forms preserve those values. The active USP
slot is0080+8*SCB+6, hence0086 only atSCB0. Current-page off0086 reaches0086
under native LRB0010. Unknown LRB/SCB or a different page cannot borrow that
identity. Native MOV2707/271C supplies the comparison source; it is not a host USP.
Savedr3 source at2703 needs its own retained startup history; a cold46 candidate
from24ED is not an actual completed reset or a new input. Possible aliases/context
changes and storage validity remain explicit proof gates.

## Conditional termination and store ordering

| Hypothesis / marker | First pass | Overall modeled result |019A store |
|---|---|---|---|
|HypotheticalExecutorAND /non47|Exit at0356 after149stores;equalCF0/ZF1 not taken|Second0354..0098,351stores;conditional272A exit,total500|371st overall /221 zero-based insecond|
|HypotheticalExecutorAND /47|Same149-store first pass|NativeDP0300 then02FE..0098,308stores;conditional exit,total457|328th overall /178 zero-based insecond|
|HypotheticalPrintedOR /either|Equality149 is taken;no first-pass exit under ordinaryCMP flags|No2714 fallthrough in stable domain;stop BEFORE activeUSP alias0086 after508stores|371st;occurs beforealias boundary|

AND termination follows an even-address rank `(DPhead-USP)/2`, reduced by1 per
iteration until the equal store. Second-pass gates are separately modeled.
M2ak's149/351/308 figures are confirmed **only as AND-hypothesis conditional
domains**, not rewritten or relabeled as native completions.

OR has no ordinaryCMP state producing a false GT. That rejects a claimed
first-pass equality exit **within that hypothesis**, not all real ECU histories.
The stable prefix stops before0086: a later zero store there would overwrite
activeUSP. A further word store0084 would overwrite activeDP itself. In an
explicit register-backed *hypothetical extension*, DP then becomes0 and two
decrements yieldFFFF/FFFE for proposedstore511. Ignoring those aliases gives a
wrong scalar-counter/wrap chronology. No physical/native execution past those
boundaries or unconditional whole-firmware infinite-loop claim is made.

## New result: cold target reach without selecting any JGT predicate

For **owned retained r3!=47**, DP>0098 and the explicit stable context above,
both opaque JGT edges return to270E:

```text
JGT taken ->270E
JGT not taken ->CMP DP,#0098 ->JLE not taken
              ->MOV USP,#0098 ->CMPB r3,#47 ->JNE taken ->270E
```

Neither path changes DP except the next two DEC instructions; A remains code0.
Before target019A there is no activePR/local-marker overlap. A universal symbolic
state propagation considers **both** outcomes, not merely OR/AND, at every JGT.
Rank `(DPhead-019A)/2` decreases by1 to the target: exactly371 word stores from
047E through019A, independent of the opaque JGT decision. This is a new
**ConditionalStaticProof of local zero-store reach**, with no JGT hypothesis
chosen and no actual branch/flag injection. Store count is not a native global
write ordinal or a same-machine event witness.

This does not prove first-pass segmentation or termination: JGT taken at0098
can bypass the exit. For retained47, a hypothetical not-taken JGT at02FE repeats
the native DP0300 path, so no analogous universal target-reach theorem is claimed.
Unknown r3 source/context/alias invalidates the cold proof; no host marker seed.

Therefore semantic ambiguity can be made irrelevant to this **narrow conditional
local target prefix**, but not to native completion or source-to-first5722.
Initialization remains a candidate for actual M2ah ownership. Required loop exit,
startup-to-IRQ/caller history, source retention/aliases and same-machine identity
are still NotEstablished; no source is imported into the retained slot0 M2ah.

## Impact, tests and STOP

JGT233A has the same generic branch form but a different immediate flag producer,
CMP A,#11 at2337. Its exact extents were checked for impact only; no2714
conditional result is transferred as actual truth. M2t stays Blocked/Unresolved;
DIV/JGT continuation0. M2ak SLLB off-object ZF defect stays separate and unfixed.
No proposed executor implementation is authorized by unresolved evidence.

Invented-only tests cover all flags/CMP relations, equality, both hypotheses,
target ordering/pass gates/DP0300, wrap and pointer self-alias, unknown context/
sources/aliases, opaque cold/warm paths, model-to-actual promotion, duplicate
manual/cross-family/secondary evidence and closed-scenario injections. Actual
counts/QA/CI are recorded in the new private report; no old tests are weakened.

M2ak first-reader Research/Blocked;M2ah STOPbefore5722/ownerNotEstablished;
5722/5725/5733 DynamicNotRun;M2ag/M2af unchanged;strictM2iBlocked;
RT5801/newreturns/IRQ/timer/fullboot/hardware/GUI NotRun/NotInjected;
TimerEvolutionNotModeled;EnclosingIRQFrame/RecoveredEcuSchedulerNotEstablished;
PcInspectionOnly/NotFlashReady;physicalRpmAvailablefalse;physical fuel/time/degrees
unavailable;GUIr3paused;D1/D2interactiveNotRun;FirmwareBIN0.

Next evidence-only step: obtain a vendor clarification or independently recorded
compatible-silicon C8 equality result with verified CMP/flag provenance. Do not
perform a new hardware experiment here. Save the private final report last after
QA/preservation/exact-SHA CI, then STOP; no M2am, executor fix or runtime bootstrap.
