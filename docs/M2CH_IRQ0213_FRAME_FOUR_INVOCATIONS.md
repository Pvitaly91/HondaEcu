# M2ch: IRQ0213 frame and four-invocation source continuity

Research-Only, static conditional relationships:
**CONDITIONAL_FOUR_INVOCATION_STATE_CONTINUITY_ESTABLISHED / EXECUTION_BLOCKED**.
No CPU/Bus stepping, original-ROM execution, IRQ delivery/injection, peripheral
model, reset/fullboot, GUI, hardware or firmware output is introduced.
FirmwareReady=false. Source compatibility is separate from native observation.

The exact accepted M2cg base is
`57f153815d61a44d6c3ce9efdc14c5937e5c4c31`,1209 raw Git source files with
fingerprint `71cf40802f7cccaa06f49eac58287d84eb6bef31d78130546ed747692f9eff05`.
Historical contracts, sources, oracles, reports and workflow approvals remain
unchanged. Exact ROM/listing checks stay private and do not run in public CI.

## Inherited facts and new proof scope

M2cg already established the four distinct H/L/F/K read sites, selected paths,
conditional checksum/ready relation, LRB007E local bank, parser predicate and
CLR291B zero stores. M2ao already had generic eight-byte IRQ geometry. Those
facts are reused rather than counted as new M2ch evidence.

New joins are the exact saved-word/RTI source roles, their coupled overlap with
the persistent parser bank, per-invocation IE/MIE/shadow generations, old-header
write0275, repeated status RMW0222, partial-ready consumption and the separation
of restoration from persistent RAM. A manufacturer vector-allocation conflict
is explicitly retained. Stage0 novelty and independent preservation reviews
preceded new models and tests.

## Exact vector, conflicting source profiles

The privately checked PROGRAM word000A targets0213. PROGRAM000A/000B is not
DATA000A, and a verified vector target does not establish a pending interrupt.

| Manufacturer source |000A|000C|000E|
|---|---|---|---|
| September1991 instruction manual Table1-1, printed1-5 | Serial receiving-ready | Serial transmitting-ready | BRG for receive |
| Retained MSM66201/207 user-manual Table17-1, printed166 | Serial transmitting-ready | Transmission error | Receive-ready/BRG overflow |

The user-manual profile assigns000A to IRQL.1/wordbit1, RQSTRDY/IESTRDY.
M2cg's selected user-table qualification is preserved. The instruction table's
alternative cannot be erased, and its customer-ASIC variation note does not
identify which profile applies to this ECU. Actual cause, chip and revision
remain unknown: SourceAllocationConflictOrRevisionApplicabilityUnknown.
Neither a DATA0055 read nor a successful invented constraint selects a profile.
No nX-8/500S peripheral rules are imported.

Under the separately selected user profile, a maskable entry requires pending,
its IE bit, MIE, legal boundary/priority and safe storage. The primary description
clears serviced IRQ and MIE, retaining IE. Simultaneous maskable factors have
IRQ0 highest and IRQ15 lowest priority. NMI is separate and is not excluded by
IE0/MIE0. Actual pending, delivery, nesting and priority state remain unknown.
Re-entry needs a pending factor after acknowledgement; that does not by itself
require or prove a fresh physical transmit completion. Reassertion mechanisms
and serial timing remain unestablished.

## Four-word frame and matching RTI

Full user Fig17-1 and instruction RTI printed3-126 establish these word roles
for symbolic incoming SSP S, with16-bit wrap and aligned effective addresses:

| Entry word role | Word address | Matching RTI read order |
|---|---|---:|
| PC | even(S) |4|
| A/ACC | even(S-2) |3|
| LRB | even(S-4) |2|
| PSW | even(S-6) |1|

Entry leaves SSP=S-8. RTI increments SSP by2 before each read, restoring
PSW→LRB→A→PC and finally SSP=S. Word contents use low byte at the lower even
address and high byte next. This layout and word-operation order do not establish
physical bus byte timing/order. Actual saved values are unknown.

Fig17-1 explicitly illustrates odd S=027F, post-entry0277: PC at027E/F, A at027C/D,
LRB at027A/B and PSW at0278/9. Alignment applies to effective word addresses;
SSP arithmetic retains parity. Other word-basis text assumes the low SSP bit0.
The algebra does not grant physical admission for an odd or wrapping stack.

Each invocation needs its own creator, current four-word storage generations,
balanced SSP and matching RTI consumer.029C is the RTI instruction address,
not the restored return PC. Different invocations may restore different
foreground PCs. No host return address is supplied. The RTI function does not
assign SF; ordinary RT's SF0 rule is not imported, and physical SF remains unknown.

The frame restores PC/A/LRB/PSW, not IE or arbitrary pointing/parser RAM.
Restoring SCB selects the saved pointing bank; it does not restore its bytes.
Unknown/nested frames or writes can invalidate both saved state and parser data.

## Handler context and mask-source chronology

Entry0213 reads word00FA/FB;0215 writes IE001A/B.0217 writes PSW literal0102,
conditionally SCB2/MIE1, with reserved read-one fields distinguished from the
literal.021C writes LRB007E, page0300/local03F0 and pointing bank0090..0097.
MIE enabling is described as starting with the following instruction; no exact
acceptance subcycle or observed preemption is inferred.

The positive paths end with0295 reading word00F8/F9,0297 clearing PSWH bit0/MIE,
029A writing IE and029C RTI. Thus the active-MIE interval needs its own pending,
enable and nesting proof. Matching four-word restoration alone does not restore
the entry's IE source or prove that F8 and FA have one owner.

Conditional reviewed mask pairs include F8=2BAB/FA=02A0 and F8=A9A3/FA=00A0,
with distinct literal writers3F16/3F18,3F2A/3F2C and54E5/54DD. Both FA masks have
wordbit1 clear, both F8 masks have it set: a conditional self-mask/re-enable
relationship under the selected user allocation. These are value/source facts,
not current enables. The early2569/256B zero shadows do not enable that bit.
Current F8/FA generations, applicability and intervening control effects remain
separate obligations.

## Four conditional invocations and persistent RAM

LRB007E maps r0..r7 to DATA03F0..03F7. Architectural addresses do not establish
physical writable retained RAM: standard201 treats this range as external DATA,
207 as internal DATA; actual device applicability remains unknown.

Every selected invocation requires mode0356.1=1 and old error0356.6=0 at0222.
RB0222 writes status even when bit6 is already0, creating a fresh storage
generation while conditionally retaining neighbor-bit semantic owners.

| Stage/read | Required retained inputs | Selected new persistent effects after0222 |
|---|---|---|
| H/0277 | r7=0 |0275 saves **old** r1 into r0;0279 writes H to r1;027A writes H to r6;027B r5=1;0270 r7=2.|
| L/027F | r7=2,r5=1 |0281 writes L=4 to r2;026D accumulates H+L;026F r5=2;0270 rewrites r7=2.|
| F/0262 | r7=2,r5=2,r2=4 |0269 writes odd F to r3;026D accumulates H+L+F;026F r5=3;0270 rewrites r7=2.|
| K/0284 | r7=2,r5=3,r2=4 |0286 computes K+current r6; on accepted checksum/header class0290 sets ready7;0293 clears r7.|

Checksum is8-bit modular addition; length3 can select checksum before0269 and
cannot establish a fresh flag owner. K does not store its sum into r6. At F=DB,
retained r6=0 and K=0 give ZF1/CF0 at the checksum addition, distinguishing that
control from the usual zero sum with carry1. CF/ZF are not physical time.

The modeled persistent effects count is6/5/5/3, including the four0222 writes:
19 selected RAM writes. Frame and IE/PSW/LRB effects are inventoried separately;
this is not a CPU journal or an observed retirement count. Same-value r7/status
writes and fresh generations are retained.

SRBUF0055 is a standard read-only8-bit receiving-data buffer with undefined reset
content. Four read identities are not four demonstrated receive completions.
For H=21,L=4,F odd,K=-(H+L+F) mod256, parity alternates odd/even/odd/even, so
adjacent values differ. Under an explicitly conditional non-destructive current
buffer interpretation, each of the three inter-read gaps needs a content change.
Actual read completion, effects, storage generations, receive/transmit coupling
and events remain unknown. Invented bytes are not supplied to a peripheral.

## Bootstrap, mode, alternate paths and overlap cuts

Prior CLRB0293 needs an earlier accepted packet and is not an independent r7
bootstrap. CLR2706/ST2710 at independently reached DP03F6 is a conditional
startup word-zero candidate, with reaching and retention unresolved. Reset RAM
is not assumed zero. Existing helper60D5 can set0356.1 from its independently
owned bit source; its cold local r0 is0208, not handler0275's r0 at03F0.

Mode0 at JBR021F goes to029D, through separate status0056/extra SRBUF02AE and
possible DP/transmit-buffer effects toward RTI024B. Old error bit6=1 likewise
enters a different TX/status path ending024B. Neither alternative is silently
treated as a positive H/L/F/K path or emulated as a complete protocol.

RTI does not undo ordinary RAM writes. Conversely an entry with even(S)=03F6
overwrites **all**03F0..03F7 before the handler: PSW at03F0,LRB at03F2,A at03F4,
PC at03F6. Subsequent local writes may corrupt that same frame. This coupled
counterexample narrows the old generic alias warning; it is not an observed
overlap or a global impossibility proof. Frame overlap with0356,0055,0090..0097,
F8/FA or mapped architectural registers is separately unsafe/unresolved.

H/L/F retain prior ready7. A source-consistent packet history therefore needs
owned prior-ready conditions or no premature foreground consumption at28BB.
After K, another header, status writer, nested frame or foreground overwrite
cannot be silently omitted from retention. Value equality does not preserve
the old writer generation.

## Foreground handoff and remaining frontier

Each RTI must consume its matching saved foreground PC and context, not029C or
a host-assigned28AE. Reaching parser28AE then needs its genuine caller path,
SCB0/LRB0041/page0200/USP0180, current mode1/ready7, retained command/flag and
no stale consumption or intervening alias. Handler SCB2 cannot be imported.

Only under those conditions does current03F3.bit0=1 feed SRLB2918/CF1 and
fallthrough JGE2919 to CLR291B. Actual CLR/ST ownership, copy0400/5C2D,
DATA011B.7 retention and independently owned DATA011F.3=0 before064C remain
unestablished. No actual parser28AE, reader064C/064F or successor is executed.

The earliest missing source is the applicable interrupt allocation/silicon,
followed by genuine pending/enable/priority and one source-owned safe entry
frame. A next evidence task can bind one flag-producing0213→0262→0269→029C
invocation to its exact0055 read, entry SSP/frame generations, retained r7/r5/r2/r6
and restored foreground source. The other three invocations and each retention
interval still need separate proof; this document authorizes no new runtime.

## Static QA, delivery and preservation qualification

Two independently authored calculations compare the complete bounded invented
case results, source states, frames and ordered persistent effects. Coverage is
the frozen curated controls and reviewed mutations, not general external-input
admission. Actual machine IDs, frame creators, source owners, saved foreground
PCs, read values, event/write ordinals and native generations remain unknown;
modeled tokens are labeled separately. Canonical comparison retains all fields.

The new finite14-source projection and separately reviewed literal workflow pin
extend the complete1209-file accepted base. Inherited approvals remain frozen.
Unknown, runtime, old-source or routing-error changes require full historical
QA. The bounded lane has router plus Ubuntu/Windows static jobs; Historical17
is **NotRun** in that lane, never a fresh17/17 PASS. Private evidence is not in CI.

Independent reconciliation confirms three existing authorized preservation
exceptions: generated historical runner, external Python and external cmd.
M2cg's frozen public wording concerned two inherited roles before its separately
authorized delivery-time cmd observation; its private final total is three.
Both scopes and historical expected fingerprints remain intact. M2ch grants
no new exception; StrictHistoricalPreservationPass=false. Source/privacy and
scoped preservation gates remain mandatory for final delivery.

ActualCpuExecutions=0; ActualOriginalRomExecutions=0; ActualIRQDeliveries=0.
ActualRTI029CExecuted=false; ActualParser28AEExecuted=false;
ActualBranch064FExecuted=false. WDT3C/reset, physical SF/stack/RAM, current native
owners, full scheduler, timer evolution, downstream rejoin, target equivalence
and firmware integration remain unresolved. Stop after M2ch; no M2ci.
