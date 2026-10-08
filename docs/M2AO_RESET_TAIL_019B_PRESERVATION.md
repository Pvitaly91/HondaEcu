# M2ao — Post-initialization DATA019B preservation frontier

## Result and scope

**Research/Blocked.** The new strict conditional software frontier is **after
CLR2758, before ST IE2759**, for an explicitly reached M2al cold/non47 source
and a correlated bounded first exit to272A. It is not a proved actual exit,
native execution, current runtime owner or same-machine transition to5722.

Base: `codex/p28-sllb-offpage-semantic-fix-m2an`,
`38d867f5adc0a5040bbe1180bf4e670375090804`.
Research branch: `codex/p28-postinit-019b-preservation-m2ao`.
Runner remains0.41.0/protocol1, including
`byte-sll-off-page-preserves-noncarry-flags`. No executor, admission, operation,
schema, GUI, distributable or PID/START/READY change. M2ao actual-ROM execution0.

Read alongside [M2ak](M2AK_DATA019B1_BOOTSTRAP_PROVENANCE.md),
[M2al](M2AL_JGT2714_PRIMARY_SEMANTICS.md),
[M2am](M2AM_C8_EQUALITY_EVIDENCE.md),
[M2an](M2AN_SLLB_OFFPAGE_SEMANTIC_FIX.md),
[M2ai](M2AI_DATA019B2_OWNER_PROVENANCE.md) and
[M2aj](M2AJ_PRE063B_CALLER_PROVENANCE.md).

## Explicit source domain

The inherited source is native CLR A2706 followed by word ST2710 at019A:
low/high bytes019A/019B, semantic high-byte bits1/2 (word bits9/10).
M2al's static prefix position371 is not an actual global native write ordinal.
The theorem requires its owned cold/non47 context, A=0, DD1, non-stack
accumulator, LRB0010/page0/local0080, SCB0, retained r3!=47, valid fixed
word-address mapping, and no asynchronous/context/unknown alias changes.
These are path conditions, not unconditional reset or retained M2ah state.

Each owner retains source PC, exact bit/address/width, independent CLR-to-store
lineage, path conditions and its known preservation interval. Actual event and
global native write ordinal remain absent. Numeric zero alone proves neither
reached source nor current runtime ownership. Same-value complete overwrites
invalidate the old owner; selected-bit RMW may retain other bit lineage while
creating a fresh storage generation. Possible alias is not observed overwrite.

## Frontier matrix

| Segment | New proved fact in the stated domain | Reaching/retention conditions | Earliest unresolved dependency; not proved |
|---|---|---|---|
| Target ST2710 | ConditionalCodeOwnedStore for019B.1/.2; inherited position371 | Genuine applicability of the M2al source domain | Actual source execution/history; no runtime owner |
| Post-store loop | Target retained through every known physical word store0198..0084; active pointer self-stores change compared values | Correlated DP/USP/flags/history, both opaque edges, fixed mapping | ProposedFFFE write after taken edge at DP=0; mapping/effects unverified, no infinite-loop claim |
| Conditional exit272A | Exactly20 distinct first-exit DP/USP pairs retain source and saved r0..r3 | Current opaque fallthrough, native CMP2716/JLE271A, no earlier exit | Actual C8 outcome and first-pass termination; no guaranteed reaching272A |
| Startup272A..2758 | Both AF branches have disjoint CPU storage footprints; no implicit stack store | Reached bounded exit; LRB/page/SCB/non-stack context retained | ST IE2759 external/control effects; no actual crossing |
| CAL276A/helper5C86 | Exact frame/return obligations, bounded indexed writes; correlated first-helper H0 needs fresh pending factor for normal-return route | Separately established control/peripheral effects, safe genuine frame and auxiliary lineage | Unknown SSP may alias; IRQ/peripheral history and intact native RT not established |
| Interrupt/caller | DATA0379 store is not PROG0379 entry; listed direct encoded CFG has no edge to0379/03ED | Real pending factor, masks/MIE/priority/delivery, correct implicit frame/context and stack domain | ExternalInterruptDeliveryRequired, FrameContextNotEstablished, no synthetic handoff |
| First5722 | Only requirements are narrowed, not admitted/executed | Independent retained bit2 or legitimate oldbit1/slot5/equality/shift on one machine | ActualSameMachineHistoryNotEstablished; runtime owner absent |

## Correlated opaque post-store loop

JGT2714 is opaque: both outcomes are explored without selecting OR or AND as
the actual silicon predicate. At the target, USP can be0356 (all previous
opaque edges taken) or0098 (a previous fallthrough above0098 caused native
MOV USP271C). While DP>0098, either outcome returns to270E in the owned r3!=47
domain. MOV DP2725 belongs to the alternative warm47 history, not this domain;
it is not declared globally impossible. Flags and history are never spliced
from mutually exclusive states.

There are140 target-inclusive known word footprints019A..0084: up to139
subsequent stores on the deepest audited continuation; earlier conditional
exits stop sooner. All subsequent bytes are strictly below019A. Writes0096..0088 affect
inactive pointing-register banks, not SSP or active SCB0. Store0086 clears
active USP; physical store0084 clears active DP itself. The following CMP then
compares DP=0 with USP=0 (CF0/ZF1); HC provenance remains the preceding DEC,
not an invented compare effect. Saved r0..r3 at0080..0083 survive this bound.

If the opaque edge after that self-store is taken, the next two DEC operations
proposeFFFE, **not0082**. Stop before that unverified write: no inferred wrap
mapping, overwrite, real termination or whole-CPU infinite loop.

Distinct conditional first-exit pairs are:

- DP in {0098,0096,0094,0092,0090,008E,008C,008A,0088}, each with USP0356
  or0098 and its own reaching history (18 pairs).
- DP0086/USP0000 after the physical USP self-store.
- DP0000/USP0000 after physical store0084, **not a store at0000**.

Each requires the current opaque fallthrough and the subsequent native JLE
edge. The pairs describe possible first exits within the bound, not20 actual
runs and not actual C8-dependent termination.

## Startup storage audit and external frontier

Fresh private extent comparison covers28 extents/67 bytes272A..CAL276A;
the address analysis below is metadata, not an execution trace or OEM window.

Before2759 the CPU writes are: active DP0084/85; byte0324; page0 bits00B7.0/.1;
copies to00AF/00F6/00F5; LRB SFR context; optional page2 byte02D1; page2
bit0230.5; active USP0086/87; accumulator/flag state. Each footprint is disjoint
from019A/019B for all20 reaching pairs and both saved-AF branches.
After LRB0041, local base is0208 and page2, but LB2748 uses **zero-page00AF**,
not02AF. MB2751 changes only bit5. MOV USP2754 changes the pointer to0180;
it is not PUSHU. No CAL/RT/PUSH/POP is listed in272A..2758; the non-stack
accumulator condition excludes implicit user-stack stores.

ST IE2759 explicitly writes word001A/001B, which is target-disjoint. Its
external/control effects are not supplied by the software theorem; therefore
the strict conditional preservation interval stops before it. Later control
writes0059/0058 and IRQ0019.4 RMW2763 cannot extend that interval merely because
their explicit addresses differ. RB2763 is the first downstream explicit
hardware-dependent read/acknowledgement. JRNZ2768 decrements/tests **DPL only**
and retains flags; its counts supply no elapsed-time or peripheral evolution.

Listed incoming edges are271A→272A and2771→2766. The latter follows a genuine
previous helper return and P2-dependent caller branch; it cannot borrow the
reset source history. Computed/unlisted/hardware entries remain unknown.

## CAL276A and narrowly gated helper summary

CAL addr16 is three bytes: return PC276D is stored at even(oldSSP), then SSP
decreases by2 and SF becomes0. If independently established oldSSP047E,
the frame is047E/047F and post-call SSP047C, not frame047C/047D. Unknown SSP
gives PossibleAliasUnresolved; even(oldSSP)=019A would overwrite the target.
A known conditional address alone does not establish real frame validity.
RT5CCD requires that same native frame's intact storage generation, writer
history and balanced SSP. No frame was constructed, popped or host-returned.

General helper domain: page2/local0208, SCB0, SF0, genuine entry and no unknown
external/context changes. Let H=0230.3 and d=(word0038-word025A) modulo65536.

| General correlated predicate | Listed outcome | Still required |
|---|---|---|
| H=1 and d<00C8 | Timer route toRT5CCD | Actual timer/control effects and real frame/return |
| H=0 or d>=00C8; oldIRQ0019.4=1 | P2/ADC indexed body thenRT5CCD | Genuine pending factor, peripheral effects and real return |
| H=0 or d>=00C8; oldIRQ0019.4=0 | Fault marker5CCE thenBRK5CD2 | Not normal RT; reset effects outside domain |

The JEQ relative target is5CA3+2+29h=5CCE, not the preceding RT5CCD. RB's ZF
reflects the **old** selected bit, not its cleared result. Primary BRK is system
reset, not a return. No listed nested CAL or helper loop is found.

Independent byte arithmetic for all256 P2 values gives X1=0..7 after
SWAPB/SRLB/AND7/EXTND. The two indexed byte-store ranges are03CE..03D5 and
03C6..03CD, disjoint019A/B. Other explicit helper writes affect IE001A/B,
IRQ0019.4, PSWH, X1_0080/81, P2_0024, threshold025A/B or fault marker00F5.
These bounded CPU footprints do not prove arbitrary peripheral/callee RAM
preservation or actual return.

### New source-specific auxiliary correlation

The same guaranteed conditional M2al prefix clears word0230 at static position296
and word025A at275, before target371. Known post-target stores do not touch them;
startup MB2751 changes0230.5, preserving0230.3=0. In a separately established
no-external/unknown-auxiliary-write domain with a genuine safe frame, the first
helper therefore has H=0: the timer-only return route is not feasible **there**.
General unknown-H callers retain all routes above.

Caller RB2763 clearsIRQ4; the intervening local write, DPL update and safe CAL
frame do not set it. With no fresh external update before RB5CA0, H0 follows
the fault/BRK route, notRT. A fresh pending-factor update after2763/before5CA0
is therefore **necessary, not sufficient**, for that first H0 normal-return
route. It is not IRQ delivery, a scheduler, elapsed time or frozen SFR evidence.

Architectural user Table17-1 associates IRQH0019.4 (word bit12/vector0020)
with ADC scan rotation/channel-change factor, not Timer2 overflow. Actual ADC
mode/completion and any resulting pending transition are not established here.

Target-disjoint frame alone is insufficient: even(oldSSP)=0230 writes return
276D whose low6D sets auxiliary bit3, changing the route. A frame at025A changes
the threshold but cannot enable the timer route while H0 survives. One word
frame cannot alias both auxiliary words. Unknown frame/context makes these
proof fields unknown, not false. No such frame was actually observed.

## Interrupt and caller dependency map

No listed literal/direct encoded software edge targets PROG0379 or03ED.
This excludes neither implicit hardware/vector nor computed/unlisted paths.
Startup's DP0379/STB metadata describes **DATA0379**, not an ISR jump.
After a conditional helper return, the caller may re-enter2766 or reach a later
ADC helper; none establishes a software-only reset-to-ISR bridge.

Architectural IRQ references associate INT1 with vector0026/bit15 and serial
RX/BRG with vector000E/bit3. A real pending source, IE/MIE/priority and delivery
are separate from known software CFG. The incomplete user-manual archive is
architecture reference, not independent C8 silicon evidence.

An implicit interrupt saves eight bytes of PC/ACC/LRB/PSW, not CAL's two-byte
frame: word footprints even(S),even(S-2),even(S-4),even(S-6), SSP=S-8.
One frame overlaps019A/B when even(S) is019A,019C,019E or01A0. An independently
native S047E gives0478..047F, but does not bound nested interrupts/calls.
IE0/MIE0 does not exclude NMI; re-enabling MIE can permit nesting. Saved context,
native restoration, stack bounds and buffer generations remain obligations.

After a genuine ISR entry, PSW0102 selectsSCB2, LRB0021 selects page1/local0108,
and USP0280 applies. Conditional serial buffer copies0212/14/16→011A/1C/1E
have disjoint target footprints; their values and same-machine history are not
owned by this theorem. Classifications remain SoftwarePathKnown (only inside
each bounded CFG), ExternalInterruptDeliveryRequired, FrameContextNotEstablished,
SourcePreservationConditional, ActualSameMachineHistoryNotEstablished.

## First5722 remains blocked

No-shift571D→5722 needs independent retained019B.2 on that same machine.
Shift571D→571F→5722 needs independent OLD019B.1, legitimate native slot5,
reached CMP equality, executed correct SLLB lineage and retention to the reader.
M2an fixes ISA semantics, not those preconditions. No oldbit0 substitution,
initial00A2=5, new strict571F admission or previous CALL56BE completion is used.
0611/0635 remain mutually exclusive in one bounded invocation; gate012A.3 may
skip0664, and RT5801/first5722 are not established.

## Verification and unchanged statuses

Primary full-page visual review covers pointing/local/word addressing and exact
CLR, CMP, DEC, conditional branches, MB, MOV/MOVB, SC/RC, JRNZ, CAL/RT, RB,
helper arithmetic/indexing and BRK forms. Complete photographed user sections
cover SFR mappings and IRQ frames/masks/context. SSP is0000/0001, LRB0002/0003;
SFR diagram endpoint cells do not locate those individual registers. Two early
audit interpretations (SSP endpoint and fault-as-RT target) were corrected in
new private artifacts before publication; no new production ISA defect found.
Private hashes, byte windows, disassembly and primary scans are not published.

Invented isolated regressions cover exact bit ownership/overlaps/same-value
generation, page/frame uncertainty, opaque outcomes/correlation/self-alias,
conditional exits, auxiliary frame aliases, blocked external/RT/IRQ continuity,
all16 handoff classifications and rejection of invented runtime identity/ordinal.
There is no CPU/Bus integration or new wire operation. Full repository QA,
privacy, protected hashes, stabilization preservation and exact-SHA CI results
are recorded in the private final report after delivery checks.

Historical M2an fix complete; M2am PrimaryConflictUnresolved; M2al/M2ak
Research/Blocked; M2ah STOP before5722; DATA019B.2 actual runtime owner
NotEstablished;5722/5725/5733 DynamicNotRun; M2tJGT233A Blocked/Unresolved;
M2ag/M2af unchanged; strictM2iBlocked. IRQNotInjected, TimerEvolutionNotModeled,
EnclosingIRQFrame/RecoveredEcuScheduler NotEstablished, ElapsedTimeNone;
RT5801/new caller returns NotRun. PcInspectionOnly/NotFlashReady;
physicalRpmAvailable=false; physical fuel/time/degrees unavailable.
GUI r3 paused/NotRun, D1/D2 interactive NotRun, hardware/fullboot NotRun,
FirmwareBIN=0. Vendor C8 InquiryDraftReady/NotSent.

Next evidence-driven step: independently establish the native SSP/frame and
the ADC pending-factor history across2763→5CA0 for this conditional first helper,
without supplying frozen SFR values or assuming IE/IRQ/return continuity.
This is a proposal, not authorization. STOP; no automatic M2ap or runtime work.
