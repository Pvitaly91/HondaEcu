# M2ak - independent DATA019B bootstrap provenance

**Static research / Research-Blocked for first-reader continuity and actual
ownership.** Exact M2aj parent: `cbfd1692ea0026b514ddc6edd115409027c17529`.
Runner remains **0.40.0**; new operation, CLI, scenario inputs and actual-ROM
integration **none**. This milestone identifies independent local source
candidates; it does not repeat a two-call bootstrap or unblock M2ah.

## Separate first-reader obligations

| Route | Required independent semantic source | Current result |
|---|---|---|
|A:571D ->5722, no shift|Existing019B.2 plus source-to-reader preservation|CandidateWithUnresolvedDependencies; no integrated owner|
|B:571D ->571F ->5722|OLD019B.1, legitimate slot5/CMP equality, then transferred NEW019B.2|CandidateWithUnresolvedDependencies; no integrated owner|
|Actual retained M2ah|Its own same-machine source/history, not a reset reference or another model|NotEstablished; retained00A2=0 takesA and still stops BEFORE5722|

Known bit0 alone does not solve either obligation. A first shift creates bit1
from oldbit0, but bit2 from **oldbit1**. A previous serial invocation cannot be
declared completed without its first5722 and native RT5801. Static root candidates
below do not require that algebraic circular bootstrap; their reach and retention
are separate, unresolved obligations.

## New result: conditional native zero initialization at2710

The exact startup sequence includes CLR A2706, native USP0356 at2707 and DP0480
at270B. Two DEC DP instructions precede each word ST A,[DP]2710. Under the
explicit **LRB0010/current-page0, SCB0, DD1, non-stack accumulator, no asynchronous
context/alias change** domain, CMP DP,off0086 at2711 reads the active **USP**
word: PR0 is0080..0087 and USP occupies0086/0087. This is code-derived pointer
storage, not an invented RAM threshold. Listing annotations alone do not prove
those conditions for every caller.

If a target iteration is genuinely reached, A is still code-owned zero and the
word store at019A writes019A/019B. It therefore supplies independently defined
zero for019B.1 and019B.2 (word masks0200/0400), regardless of the previous byte.
This is **ProvenNativeInitializationCandidate / ProvenWithinExplicitStaticDomain
at that store**, not a proof that the loop reached or finished it.

The following exact ranges are **conditional address arithmetic**, not an
executed loop or an adopted GT predicate:

| Pass / condition | First word ->last word / step | Words | Target019A |
|---|---|---:|---|
|Initial USP0356|047E ->0356 /-2|149|Not covered|
|Then USP0098, savedr3!=47|0354 ->0098 /-2|351|Second-pass index221, combined index370|
|Then USP0098, savedr3==47, native DP0300|02FE ->0098 /-2|308|Second-pass index178, combined index327|

After a justified first exit, CMP2716/JLE271A checks DP against0098. If above,
271C changes USP to0098; CMPB2720/JNE2723 either resumes from currentDP or
2725 setsDP0300 before the next descent. The47 variant leaves0300..0355 outside
this conditional clear domain. Direct cold startup sets its marker to46; the47
alternative has additional patch/helper/hardware preconditions, not a new mode.

**JGT2714 remains unresolved.** Every descent/exit, particularly equality
DP=USP, needs independently validated GT semantics. The primary condition table
prints an OR predicate inconsistent with conventional greater-than; it is not
replaced with AND or borrowed from JLE. No endpoint, native loop completion or
reset-to-runtime continuity is claimed without that gate. Earlier startup
selftests, current frames and peripheral/context conditions are also unexecuted.

## RAM-test exchanges are not a retained bootstrap

Under the startup caller domain,267C setsLRB0040 and267F setsX1=03FA. Indexed
word0084+X1 descends047E..0084 by2, conditionally510 iterations;019A occurs at
X1=0116, index370. Calls2689/268D enter5C5C with distinct return268C/2690 frames.
Native code supplies5555 and, after the first genuine return, SLL268C suppliesAAAA.

| Site | Word effect | Independent final source? |
|---|---|---|
|5C68 first exchange|RAM receives known pattern; A receives prior word/source|Temporary only; rejected as first-reader bootstrap|
|5C6C second exchange|RAM receives that prior word/source; A receives pattern|Unknown prior stays Unknown; not made owned by the pattern|
|Later2710, if reached|Fresh native zero store overwrites the old/test history|Independent initialization candidate, with the separate loop/path gates above|

There is no listed instruction between the two exchanges. MIE is disabled
across the pair, but NMI/other asynchronous hardware contexts are not recovered.
Restoration precedes the normal helper RT5C80 and any following reader. Failed
pattern checks lead to BRK; neither failure nor a conditional return edge is
treated as successful execution. A same-value restoration is a fresh storage
write, not ownership laundering.

The first test address047E can overlap the native startup CAL frame at the
code-established SSP047E. Exact restoration and matching RT are required; this
is a frame hazard, **not** permission to choose SSP019A as a bootstrap source.
No frame is manually injected, popped or transferred from0667.

## New result: constant-copy bits at3174, conditional on real page context

A narrow reaching-definition analysis starts at312A and stops at3174. Every
writer-reaching path passes312D. With no intervening call or LRB change, r1
arrives as **00 or21** from explicit MOVB/CLRB definitions. Thus its bit1 andbit2
are both code-defined zero regardless of which audited predicate route reaches
the copy. Flags/RAM predicates, branch-specific writer identity and actual
chronology are not selected by this invariant.

3174 MOVB offN8,r1 addresses **029B** under an independently assumed LRB0041
domain, and cannot initialize019B there: **RejectedWithinAuditedDomain**.
Under page1 it could copy an independent bit1/bit2 source to019B:
**CandidateWithUnresolvedDependencies**. No legitimate page1 caller/context for
this routine, preserved source-to5722 path or actual writer identity is established.
It is not promoted using the listing's bank annotation or a host LRB seed.

31BE DECB needs an already owned prior byte; it is rejected **as an independent
root** in the audited domain. A proposed3174->31BE retained chain additionally
crosses CAL318D/8915, requiring a genuine return and callee alias proof.
r3/er1 can overlap019B at local base0198/LRB0033, but no listed immediate
MOV LRB,#0033 establishes that caller. Computed/restored/other-entry contexts
remain Unknown, not globally impossible. Canonical startup banks0080/0200/0208
and bounded caller bank0108 exclude that particular local alias by arithmetic.

## Source-to-reader preservation and dominance

The source2710 dominates its immediate2711 successor **inside the reached target
iteration**, not the entire firmware reader. After a hypothesized loop exit,
272A masks0324; saved B7/AF/F6/F5 are restored. Address-only projection of the
following literal stores excludes019B under the explicit contexts above.
It is not a complete hardware/interrupt preservation proof: ST IE2759 is a
control-effect gate, and CAL276A->5C86 has only a **conditional native-return
summary**. Helper paths require either word0038 (listingTM2) at5C90 or IRQ0019.4
at5CA0. No observations, default-zero sources or admitted side effects are supplied.

Further startup/main-loop-to-INT1/serial-RX transition is unestablished. The
bounded M2aj roots0379/03ED can enter the reader component without2710; therefore
global initialization dominance and absence of a bypass are **NotEstablished**.
That CFG fact is not proof that real hardware reset history omitted initialization.

Both routes also retain callee/indirect/page/bank/X1/X2/DP/USP/system-stack and
enclosing IRQ-frame obligations. A possible alias blocks strict preservation;
it is not an observed write. Encoded **data/system word019B** overlaps019A/019B,
not019B/019C; this rule is not assigned to user-stack or program-space forms.
Bit0-only SB/RB preserves already owned bits1/2 and does not create them from
Unknown. Copy/shift transfers only the corresponding independent source lineage.

## Confirmed static SLLB defect note - no fix/admission

Complete primary page3-145 lists SLLB off-object and CF as its only updated flag;
ZF/HC/DD are preserved. Existing generic executor source treats this byte
MemOffPage form differently from its reviewed accumulator exception and reaches
set_zf(result). Thus the M2aj possibility is now **ConfirmedStaticSemanticDiscrepancy**.
For example oldbyte01/incomingZF1 yields02: primary ZF1, generic path ZF0.

This is source/specification evidence, not actual571F execution. Only independent
invented specification tests and this defect note were added. No global executor
fix, new fix identity, permission, operation or version bump. Unresolved JGT and
historical JLE remain separate. Primary ST/DEC scan function-line inconsistencies
are disclosed privately; exact descriptions/tables are reviewed, not silently
converted into global ISA changes.

## Tests, retained boundaries and next evidence

Invented-only fixtures cover independent bit1/bit2 roots, no-shift/shift,
unknown-bit1 despite bit0, reset reference without continuity, restoration of
unknown prior words, initialization invalidation/freshness, bit0 preservation,
word/page/bank aliases, initialization bypass, concrete cyclic bootstrap,
wrong-machine/stale writer/event/global ordinal and unproved return summaries.
Static accepted witnesses always report actual executions0/runtime integrationfalse.
Historical scenario contracts still reject initialization/branch/handoff repair.
Final actual test/QA/CI counts are recorded in the new private final report.

M2ah Research/Blocked and STOP before5722;5722/5725/5733 DynamicNotRun;
5782/5787,5793/TM3/laterhardware,RT5801/returns0614/0638/0667 NotRun in new scope.
Historical frame0667 EstablishedPendingReturn;M2ag/M2af/M2tJgt unchanged.
IRQNotInjected;TimerEvolutionNotModeled;ElapsedTimeNone;EnclosingIRQFrame and
RecoveredEcuSchedulerNotEstablished;strictM2iBlocked;PcInspectionOnly/NotFlashReady;
physicalRpmAvailablefalse;physical fuel/time/degrees unavailable;GUIr3paused/NotRun;
D1/D2interactive/hardware/fullbootNotRun;FirmwareBIN0. No existing private report,
ROM/definitions/binding/distributable or PID/START/READY stabilization changes.

Next evidence-only step: obtain independent primary clarification for **JGT2714
at DP=USP equality**, sufficient to justify the sweep boundary. It is not carried
out here. Save the new private final report last after exact-SHA CI, then STOP;
no M2al, runtime bootstrap integration, tail, IRQ/timer/fullboot, GUI or hardware.
