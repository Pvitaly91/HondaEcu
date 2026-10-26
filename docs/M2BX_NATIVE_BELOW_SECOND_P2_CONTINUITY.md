# M2bx - bounded native Below continuation and second-P2 continuity

This document specifies a new research-only acceptance protocol. It is not an
execution receipt. Current M2bx runtime and delivery results must come from the
separate source-bound private report; a contract, old observation or static
instruction table cannot establish a new execution.

Accepted base is M2bw `4d99ebcf02016df3dfa0a6d035bb01def4b170cd`, on
`codex/p28-word0196-post-p2-control-continuity-m2bw`. The new branch is
`codex/p28-word0196-below-second-p2-continuity-m2bx`. The new default-off feature
`p28-word0196-below-second-p2-continuity` depends on
`p28-word0196-post-p2-control`; normal runner operations and the old M2bu/M2bv/
M2bw constructors, budgets and contracts retain their existing meanings.

## Independent sources and proof levels

The manufacturer instruction authority is the OKI MSM66201 Instruction Manual,
first edition September1991, SHA-256
`f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271`.
Full relevant pages were visually reviewed: ROLB A3-119, STB3-155, RB3-114,
L3-69, SJ3-140, ST3-154, J3-62, JC/NE3-66, LB3-70, ORB A,obj3-107,
ANDB A,obj3-24 and ORB obj,A3-108. Exact forms and addressing modes matter;
one form's admission does not admit every instruction with the same mnemonic.
The JC/NE page supplies the NE predicate and cycles; it does not resolve the
separate historical C8/JGT question.

The matching retained peripheral scans supply P2/P2IO/P2SF Table5-2/Fig5-8/
Table5-3 and TCON0 Table9-1/Fig9-2/realtime-output section. Their named standard
device applicability does not identify a customer ECU ASIC or establish the
physical machine's current port or timer configuration.

Source expectations compose the unchanged [M2bu predecessor model](M2BU_NATIVE_ENTRY_CONTINUITY.md),
[M2bv first-P2 model](M2BV_NATIVE_P2_OWNERSHIP_HANDOFF.md),
[M2bw control model](M2BW_NATIVE_POST_P2_CONTROL_CONTINUITY.md),
M2av reviewed IR/C11 for the original algorithm, and the separately reviewed
[M2ac continuation](M2AC_BELOW_SECOND_P2_HANDOFF.md). M2ac observations remain
historical observations on their original machine; they are not new M2bx
records, source owners or generation identities. New expected states are
computed independently before production Rust execution and never derived from
its output. The host C11 prefix proof alone is not a target-instruction proof.

## One retained production machine and closed source

Each new positive case starts at54F5 and retains one production Cpu, one Bus
and one immutable PROGRAM source through predecessor, original algorithm,
first P2, first TCON0, Below continuation, second TCON0 and second P2. Production
decoder and Exec obtain every successor. There is no second machine, host PC
setter after entry, JSON state handoff or mid-execution seed. Recording prefix
observations is not permission to reconstruct a continuation machine.

Private admission must reuse M2bs whole-image/profile/listing verification,
authenticate all selected extents, and fence the exact selected source before
and after runtime. The common native segment is `[54F5,5688)`,403 unchanged
bytes at their original addresses, without relocation or padding. The closed
source inventory contains31 M2bw sites plus18 distinct downstream sites:49 in
total. Segment membership grants no execution permission to gap bytes.

Only the selected39-instruction Below path succeeds in M2bx. The31-site
identity inventory also retains old branch metadata; it does not permit new
execution of M2bw B/C/D paths or their PSWH/MIE continuation. Their unchanged
regression gates still stop559D. New downstream executable regions are
`[55D2,55DD)`, `[562C,5636)`, `[565D,5663)`, `[5671,5675)`, `[567E,5688)`.
Unselected5663/5675 alternatives and RT5688 are not retired. PROGRAM decoder
probes, selected instruction fetches and functional DATA accesses remain
separate observations.

The public program is independently invented, with base6400 and403-byte range
ending6593; it cannot be substituted for private original-byte admission.
No original image, OEM byte window, private trace or modified firmware payload
belongs in public source or CI artifacts.

## Eighteen new instruction boundaries

The following is an independent expected path, not a fabricated actual trace.
The18 extents occupy41 instruction bytes and14 exact forms. Each boundary must
be observed through the retained production machine and checked independently.

| PC | Exact scoped operation | Bytes | Expected successor | Manufacturer INT |
|---|---|---:|---|---:|
|55D2|DD0 ROLB A through incoming CF|1|55D3|2|
|55D3|DD0 STB A,current-page0116|2|55D5|4|
|55D5|RB direct TCON0.2|3|55D8|9|
|55D8|L A,immediate word1|3|55DB|6|
|55DB|SJ from nextPC55DD, displacement+4F|2|562C|8|
|562C|DD1 ST A,current-page0110|2|562E|4|
|562E|L A,immediate word1|3|5631|6|
|5631|DD1 ST A,current-page0112|2|5633|4|
|5633|Direct J to565D|3|565D|7|
|565D|DD1 ST A,current-page0114|2|565F|4|
|565F|L A,current-page word0110|2|5661|4|
|5661|JNE, ZF0, nextPC5663 plus0E|2|5671|8 taken|
|5671|LB A,current-page0116|2|5673|4|
|5673|SJ from nextPC5675, displacement+09|2|567E|8|
|567E|DD0 ORB A,current-page018F|2|5680|4|
|5680|DD0 ANDB A,immediate0F|2|5682|4|
|5682|Byte ORB P2,A|3|5685|7|
|5685|RB current-page012A.7|3|5688|9|

The budget is exactly21 previous Below instructions plus18 new instructions,
giving39. Stage counters are hierarchical:6 predecessor +10 algorithm +1
first-P2 +4 previous post-P2-prefix +18 new tail =39. An aggregate P2 count2
overlaps the tail and must not be added again. The previous four-instruction
post-P2-prefix counter is not a count of TCON0 SFR operations. The full case
has two P2 RMW instructions and two TCON0 RMW instructions.

## Reachable ROLB state and full PSW

Let `x` be the explicit technical initial DATA018E byte. The independently
reviewed original prefix makes `v=rotl8(x)` at5572: the preceding5571 shift
supplies old `x.7` as carry. Below's55C1 stores AL into0117; it does not OR F0
into018E. Thus55CB/55CD produce `t=(~v)&FF`, and actual55CF copies `t.7` into
CF. The55D2 input is the coupled pair `(AL=t, CF=t.7)`, not a Cartesian AL/CF
input domain. Both carry values are reachable. Its result is
`AL=((t<<1)|incomingCF)&FF=rotl8(t)`, with outgoingCF=old `t.7`.

Manufacturer ROLB A/DD0 writes only AL and CF; AH, ZF, HC, DD and every other
PSW bit are retained. ZF is not recomputed from the rotated result. The scoped
incoming relation means ZF1 at55D2 implies AL0/CF0. Moreover54FA has loaded a
Below word smaller than00C0, so AH is0 there in a completed new positive path.
Nonzero-AH preservation belongs to a separate invented instruction regression,
not a false whole-path coverage claim. DD1 word ROL is a separate form.

## Actual RAM writers and mandatory taken JNE

The seven new DATA bytes0110..0116 begin as explicit technical A5 canaries
before54F5. They are not ready continuation values or native source owners.
The new DATA inventory is23 bytes. With the retained32 pointing-word setup
writes, setup has55 logical DATA writes and87 constituent raw byte writes;
historical48/80 setup contracts remain unchanged for older sessions.

| DATA | Width | Required actual writer | Required consumer / retention |
|---|---:|---|---|
|0116|8|STB55D3 stores actual ROLB result|LB5671 reads that writer's byte|
|0110/0111|16 LE|ST562C stores actual word1|L565F observes the same word; JNE5661 consumes its ZF0|
|0112/0113|16 LE|ST5631 stores actual word1|Retained terminal state|
|0114/0115|16 LE|ST565D stores actual word1|Retained terminal state|
|018F|8|Existing native55C3 stores0F|ORB567E consumes it|
|012A|8|Explicit retained prior state|RB5685 clears only bit7|

L immediate1 sets A=1, ZF0 and DD1. Stores and jumps retain flags. The actual
word store to0110 followed by the actual word load proves ZF0 for JNE5661;
the native conditional branch must select5671 without a host repair. Word
stores must each retain one logical16-bit writer and the two ordered raw
little-endian byte writes. LB5671 sets DD0, loads only AL and preserves AH.
ORB567E and ANDB5680 derive AL0F from the native byte history. No host supplies
the ROL result, ready words, branch result or second-P2 accumulator value.

## TCON0 T1 to T2 and P2 G1 to G2

One technical stopped TCON0 snapshot83/87/8B/8F is supplied before54F5:
mode11, RUN0, clock bits100. These are test preconditions, not recovered native
configuration. Actual55C8 SB makes bit2=1 and creates T1. Actual55D5 RB must
read this retained storage, set ZF to the inverse OLD bit2, clear bit2 and
create fresh T2. Hence its scoped old bit2 is always1, its ZF is0, and terminal
TCON0 is `initial & FB` (83 or8B). CF/HC/DD/A/otherPSW and all other implemented
TCON0 bits are retained. Both bit operations have two decoded-executor byte
reads followed by one write; these are software journal events, not physical
bus-cycle measurements. TRNSIT is untouched in this new Below path.

One initial P2 latch snapshot is likewise technical only, under the reviewed
all-output primary-port precondition P2IOFF and implemented P2SF bits clear.
Actual55C5 creates G1 from `initialP2|0F`. Exact5682 must read G1's retained
latch on that same machine and let production Exec compute `oldP2|AL`.
Native018F/0116/ORB/AND history has already made AL0F, so G1's low nibble makes
every scoped G2 a same-value write. This numerical equality must not suppress
the new native writer, generation ordinal, write ordinal or journal record.
The result is nonzero, so the second ORB sets ZF0 and preserves A/CF/HC/DD/
otherPSW. Its actual successor is5685.

Generation identity includes the case's retained machine, exact native writer
PC, order and value. First and second generation ordinals are1 then2 per
register. Zero-based all-native logical write ordinals are independently
derived as follows; raw constituent word writes remain separate.

| Native writer | Native ordinal | With55 logical setup writes | Raw write ordinal |
|---|---:|---:|---:|
|55C5 P2 G1|5|60|93|
|55C8 TCON0 T1|6|61|94|
|55D3 DATA0116|7|62|95|
|55D5 TCON0 T2|8|63|96|
|562C DATA0110 word|9|64|97,98|
|5631 DATA0112 word|10|65|99,100|
|565D DATA0114 word|11|66|101,102|
|5682 P2 G2|12|67|103|
|5685 DATA012A bit7|13|68|104|

The first capabilities and first-generation observations remain intact.
Separate sealed second-operation capabilities require the exact PC, byte
width, expected instruction order and prior actual generation. They cannot
reopen the first writer or grant generic SFR access. Host reseed, alternate
PC/width/neighbor, stale G1 substituted for G2, second CPU and unknown-SFR
fallback must refuse. Diagnostic storage inspection is not a functional read.

## Final boundary and observations

After5682 only the allowed RB012A.7 is executed. It sets ZF to the inverse old
bit7, clears that bit, retains the other byte bits and preserves CF/HC/DD/A/
otherPSW. The resulting PC must be5688. RT is not retired; no synthetic return
address, CAL, SSP allocation or interrupt frame is created. SSP and all
retained bank/pointer/context obligations must be checked rather than inferred
from a presumed native ABI or stack capacity.

Before the first final runtime, freeze source, corpus, all expected39 boundary
states, instruction identities, branch decisions, full DATA/PROGRAM/P2/TCON0
journals, G1/G2/T1/T2 and stopPC. Compare every actual boundary, complete RAM
frame, logical/raw ordering, same-value writes, source generations and full
PSW. Preserve the first case/PC/field/expected/actual mismatch without changing
expectations from Rust output. Incomplete records never count as a completed
case. A branch table or static JSON cannot manufacture runtime authority.

## Corpus, QA and delivery obligations

The new closed corpus is16 private original-byte cases and16 independently
invented public cases, all Below:16*39=624 retirements per domain,1248 locally
combined. Cover all four stopped TCON0 values, P2 initial00/FF/A5 and other
representative values, distinct Below words, DD/CF/HC/OtherPSW/SCB and technical
SF variants, reachable ROL states, both original012A.7 values, actual RAM
writers/consumers and same-value G2. Preserve the old B/C/D regressions without
rerunning their full previous private corpus or the5470-case corpus locally.

New local Cargo commands require both CARGO_TARGET_DIR and --target-dir to
name `.tmp/m2bx-owned/cargo-target`, with ownership/reparse/output-overlap
checks and pre/post runner fences. Cache or repository copies are unnecessary.
The inherited historical generated-runner loss remains exception1;
strict historical preservation stays false. No new unauthorized loss is allowed.

Reuse the existing atomic checkpoint and complete-record recovery protocol.
Detect existing owned processes and reconcile source/corpus/record hashes
before resuming; do not duplicate verified cases, accept ambiguous partials or
start another CI run merely because a response was interrupted. Respect a user
pause; no background automation or unbounded polling is authorized.

Preserve the eleven previous required CI jobs and add the two M2bx OS jobs if
the reviewed workflow retains that structure, yielding13 required jobs.
Historical frozen identities are pinned, not rewritten. Public CI executes
invented fixtures only. After normal commit/push, require exact-final-SHA
success and full decompressed public canonical byte equality on local,
Ubuntu and Windows, with no excluded semantic or diagnostic fields. Source,
privacy and scoped protected readback plus evidence seal precede the final
private Ukrainian report, which is written last.

## Diagnostic accounting and limits

For the new18-instruction tail, retained software diagnostic deltas are
`2,4,9,6,8,4,6,4,7,4,4,8,4,8,4,4,6,9`, total101. Independently reviewed
manufacturer INT rows sum102. At JNE5661, true8 versus false4 is documented;
the retained decoder4 plus taken-branch executor4 agrees for the selected path.
The single new-tail difference is ORB P2,A at5682: software6 versus INT7.
The earlier55C5 P2 difference6 versus7 is also retained. No global cycle rule
is changed to obtain equality. All actual software counters remain observable
and compared; neither integer total is physical ECU elapsed time.
`DiagnosticCycleTimingEquivalenceNotEstablished` remains.

The following restrictions remain even after a completed technical39-step
experiment:
ActualHardwareEcuExecutionNotObserved; RecoveredFullEcuSchedulerNotEstablished;
PhysicalSFNotEstablished; NativeStackSafetyNotEstablished;
InitialP2NativeOwnershipNotEstablished; InitialTCON0NativeOwnershipNotEstablished;
TimerEvolutionNotModeled; IRQDeliveryNotInjected; PhysicalTimingEquivalenceNotEstablished;
ElectricalOutputNotObserved; RT5688NotExecuted; ReturnFrameNotEstablished;
ActualNativeDownstreamRejoinNotEstablished; SafeROMPlacementNotEstablished;
TargetProgramEquivalenceNotEstablished; FirmwareIntegrationNotEstablished.
FirmwareReady=false. After delivery, STOP: no M2by, RT/timer/IRQ continuation,
ROM placement/patch, target object/HEX/firmware BIN, flashing, GUI or hardware.
