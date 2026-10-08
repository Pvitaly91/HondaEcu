# M2ap — Native SSP, CAL276A frame and ADC pending-factor provenance

## Result and scope

**Research/Blocked.** New bounded code/primary evidence narrows the first
CAL276A→5C86 obligations: an independent native SSP source and its exact
restoration/call chain, plus native ADC scan configuration and the difference
between pending storage and CPU delivery. Actual SSP at276A, fresh postclear
pending event, matching nativeRT5CCD and same-machine owner remain unestablished.
The strict DATA019B frontier stays **after CLR2758, before ST IE2759**.

Exact base: `codex/p28-postinit-019b-preservation-m2ao`,
`57a59fdfe823b0f0e7b979afb8bd7158d5d00c2e`.
Branch: `codex/p28-ssp-adc-pending-provenance-m2ap`.
Runner0.41.0/protocol1 and
`byte-sll-off-page-preserves-noncarry-flags` unchanged. Static research only:
actual-ROM0, no CPU/Bus integration, operation, CLI/schema, runtime admission,
executor, GUI, hardware, binaries or PID/START/READY changes.

References: [M2ao](M2AO_RESET_TAIL_019B_PRESERVATION.md),
[M2ak](M2AK_DATA019B1_BOOTSTRAP_PROVENANCE.md),
[M2al](M2AL_JGT2714_PRIMARY_SEMANTICS.md),
[M2am](M2AM_C8_EQUALITY_EVIDENCE.md),
[M2an](M2AN_SLLB_OFFPAGE_SEMANTIC_FIX.md),
[M2ai](M2AI_DATA019B2_OWNER_PROVENANCE.md),
[M2aj](M2AJ_PRE063B_CALLER_PROVENANCE.md),
[M2ad](M2AD_CAL_RT_ROUNDTRIP.md),
[M2ag](M2AG_FALLTHROUGH_DATA0136_CALLER.md).

## Independent SSP source inventory

The sealed11,499 listed-instruction inventory/CFG is reused, not rebuilt as
whole-firmware execution. Fresh narrow checks cover274 startup/frame extents
and53 ADC-related extents; those sets overlap. OEM bytes/listing remain private.

| Candidate | Code-derived value/effect | Preservation and first barrier |
|---|---|---|
| MOV SSP,#N16 at24F8 | Independent immediate047E if genuinely reached | Early successful selftest/context/peripheral history; not actual276A SSP |
| XCHG A,SSP2531/2533 | Native word5555 temporarily replacesSSP, second adjacent exchange restores old047E lineage | DD1/non-stack A; same A/SSP/context and no asynchronous mutation between pair |
| XCHG A,SSP254D/254F | Native wordAAAA then adjacent restoration047E | Same obligations; fresh register generation, not an unchanged register |
| CAL2689/268D with RT5C80 | Conditional047E→047C→047E per genuine matched call | Exact current frame/restoration, pattern/control flow and native return |
| Other stack/data/context domains | CAL/SCAL/VCAL, RT/RTI, PUSHS/POPS, indirect/local/SFR, implicit IRQ/reset | No blanket absence or unchanged-SSP claim; unknown history blocks continuity |

There are five explicit named SSP writers in the listed inventory (one MOV,
four XCHG); CMP SSP3F47 is a reader. This is not a global exclusion of memory
aliases, unlisted/computed code or implicit hardware writers. Architectural
reset SSPFFFF is a documented reset reference, not observed reset or startup
authority; technical M2ad/M2ag SSP07FE is not used.

24F8 structurally dominates276A only in the bounded24ED-entry graph; call
fallthrough edges alone are unproved return summaries, not native completion.
Other entries cannot borrow that dominance or its source identity.

SSP0000/1 is separate from LRB0002/3 and SCB-selected pointing registers.
Temporary LRB1555/0AAA produce local basesAAA8/5550 and pagesAA/55; no off/local
writer occurs while those test contexts are active. DirectIE/F8/FA accesses are
zero-page. Adjacent PSWL byte exchanges2572/2574 and257C/257E temporarily select
SCB5/2 but have no intervening pointing-register instruction; exact restoration
is required. Fixed selected destinations do not aliasSSP0000/1. DP countdown
reads are not indirect stores; unknownDP loaded2682 is not the helper write pointer.

## Correlated RAM-test frame and SSP history

With code-derived X1=03FA..0000 by2, indexed words0084+X1 cover047E..0084:
510 conditional iterations, two distinct CAL/RT pairs each, not1020 observations.
CAL2689 returns268C; CAL268D returns2690. Each stores its own word at047E/F
and leaves SSP047C in the independently retained047E domain.

The first iteration's indexed word is the current CAL frame. XCHG5C68
temporarily overwrites it; adjacent XCHG5C6C restores the prior CAL-derived
word from A. Original storage generation is **interrupted**. Legitimate
restoration creates a fresh generation retaining that exact CAL's semantic
lineage, not merely the same numeric return address. Distinct calls—even at
the same PC—must not share creator/storage generation authority.

The conditional software pattern route uses native5555/AAAA, stable X1/X2,
the restored accumulator pattern and localer3. Matching RT requires reached
successful pattern comparison and intact current restored word; later indexed
addresses are below047E. No listed nested CAL/SCAL/VCAL/PUSHS/POPS is in the
bounded helper. SSP+2 before RT's read conditionally restores047E; incomplete
call, damaged exchange, fault/BRK or unproved return stops continuity.

The successful comparison is not an arbitrary branch assumption within that
exact software domain: MOVX2 owns the current pattern, the adjacent exchange
pair restores A to that pattern, STer3 then Ler3 retain it, and CMP A,X2 derives
CF0/ZF1, so JNE5C7E falls through toRT5C80. X1/X2 storage0080..83 is below
every indexed word. At indexedEA0206 the later STer3 overwrites the restored
RAM word with the pattern; do not claim every tested RAM word stays unchanged.
It still does not alter frame047E or the A/X2 equality proof. At finalEA0084,
temporary DP self-alias does not change X1-based exchange addressing.
SUBX1,#2/JGE uses current borrowCF: decreasing even rank ends after510
conditional iterations at X1=FFFE. This rank proof does not use unresolvedC8.
All IE/MIE/context/noasync/RAM-validity gates remain explicit; actual exchanges,
RT5C80, complete initialization and ensuing276A entry are still unobserved.

New cold narrowing: retained direct00F5!=47 makes JNE269D reach26F0, excluding
all seven optional calls26A7/26AF/26B2/26B5/26D3/26DC/26E9 and unknown-DP
store26BA. The alternate47/79AD path is not assigned the cold SSP proof.

Thus047E is independently code-derived beforeCAL2689 in the successful
non-stack/noasync domain. Extending it toCAL276A requires the complete matched
RAM-test history, cold edge, one M2ao correlated bounded exit and continuing
no asynchronous/context/control-induced mutation. M2ao clear stores at or
above0084 do not writeSSP; proposedFFFE is excluded, not assumed mapped.
Actual reachingSSP276A is NotEstablished. This is SSPContinuityConditional,
not a newly selected C8 outcome, runtime seed or recovered full boot.

## Exact CAL276A frame and alias matrix

Primary CALaddr16 is three bytes: word returnPC276D at even(oldSSP), then
SSP-=2, SF=0, target5C86. RT5CCD, if genuinely reached, performs SSP+=2 then
word PC read, SF=0. Ordinary CF/ZF/HC/DD remain unchanged; RT retains callee A/LRB,
not an IRQ snapshot. SF is internal operand mode, not a PSW reserved bit.
Data/system-stack words align down; user-stack/program forms are not assigned
this rule. Actual frame events/global ordinals are absent.

| oldSSP/domain | Aligned frame / postSSP | Source/effect classification | Missing authority |
|---|---|---|---|
| Conditional24F8 chain047E |047E/F /047C|DisjointProvenWithinDomain for019A/B,0230/31,025A/B|Actual chain/frame/MatchingNativeReturnNotEstablished|
| Hypothetical019A or019B |019A/B /nativeSSP−2|KnownFrameOverwrite only if that CAL is legitimately reached/written|No cold reaching SSP definition; old zero lineage invalidated|
| Hypothetical0230 or0231 |0230/31 /nativeSSP−2|Target-disjoint, auxiliary H overwritten|FrameSourceNotEstablished in actual history; H0 cannot be reused|
| Hypothetical025A or025B |025A/B /nativeSSP−2|Target/H-disjoint, threshold overwritten|Same source/history gate; no invented TM2 sample|
| Unknown |Unknown|PossibleAliasUnresolved /FrameSourceNotEstablished|No selected safe SSP or native return|
| SFR/control footprints |Geometry only|Context/effect gate, not safe helper/frame authority|SSP/LRB/PSW/IRQ/control side effects unresolved|

Frame019A writes low6D/high27: both019B.1/.2 become1 from a **new conditional
CAL-derived generation**, not retained CLR2706 zero ownership and not M2ah input.
Frame0230 low6D sets0230.3/H to1. Frame025A sets threshold276D; for a separately
owned H1, d=(TM2−276D) mod65536<00C8 corresponds toTM2 in276D..2834.
H0 does not read TM2/threshold at all. One aligned two-byte frame cannot
overlap both auxiliary words; independent H1 and threshold changes cannot be
assembled from mutually exclusive frame addresses.

## New primary ADC configuration and pending source

Manufacturer user chapter13/Table13-1 maps ADSCAN0058/ADSEL0059. Its body
explicitly names MSM66201/207; the incomplete archive lacks exact cover/edition/
revision provenance: **MissingPrimaryEvidence** for those identity details.
It is architectural reference, not silicon observation or C8 clarification.
Peripheral conclusions use the documented standard MSM66201/207 layout;
actual device/revision or customer-specific ASIC peripheral applicability is
not established merely by a ROM listing. The instruction manual's vector
allocation note explicitly allows customer-specific I/O variations.

In a separately reached continuation, native CLRBADSEL275C writes command00:
implemented select mode stopped, channel0, clock selector0. Native MOVBADSCAN275F
writes command10: scan channels0..7, RUN1, INTSN0 (subsequent conversion after
completion), SNEX0 (restart from head after rotation), initialSCNC0.
These are code-owned commands, not raw readback assertions: nonexistent ADSEL
bits read1. RUN initiates head-channel conversion according to section13.2.
Complete scan rotation setsSCNC and generates ADC request. Select-channel
conversion completion is another architectural factor, not this derived setup.

Table17-1 identifies IRQH0019.4/wordbit12, RQADC/IEADC, vector0020.
Timer2 overflow is wordbit8/vector0018, not this flag. Table3-1 specifies IRQ
R/W8/16. Factor occurrence storesIRQ; IE/MIE/priority gate CPU delivery.
Fig17-2/page169 Example3 explicitly separates pending request from delivery
while MIE=0. Disabling delivery does not itself prevent ADC pending storage.

Clock selector0 means320 original clocks in the configuration table. The note
prescribes frequency-dependent selection; actual oscillator/basic-clock
applicability, conversion progress, scan completion and postclear event are
not established. No instruction-count/cycle/elapsed-time argument is used.
Available pages do not resolve simultaneous hardware-set/software-clear
priority. A documented set condition is not HardwareEventObserved.

## Exact RB2763→RB5CA0 history

Conditional RB2763 reads oldbit, setsZF=!oldbit and clears bit4; CF/HC/DD
retained. Pre-clear pending1 is stale after the clear. MB2766 writes local0208.0;
JRNZ2768 changesDPL only, retaining flags. CAL writes its separately validated
frame. In the retained H0 route JBR5C86 goes directly5CA0: no other literal
IRQ writer, IE writer, indexed/indirect data write beyond the frame or nested
call lies in this interval. IE remains code-owned0000 from CLR2758/ST2759
in that separately reached, noasync/noalias domain. **Polling fresh pending
does not require delivered ISR.** NMI/context effects remain independent gates.

Twelve literal direct IRQ references were checked in the reused inventory:
word clears and selected-bit RMW/readers, but no direct literal IRQ4 setter.
This is not a global absence claim for page aliases, indirect or asynchronous
paths. Hypothetical frame0018 writes276D/bit12=0 under pure storage arithmetic;
it does not supply desired pending1 and has unresolved SFR/context effects.

Fresh factor must belong to the **exact clear interval**, same path/machine,
remain pending until RB5CA0 and survive intervening acknowledgement/effects.
Architecture alone or a frozen pre-clear value cannot establish that reader.
Separate statuses: SoftwareClearEstablished, HardwareSetSpecifiedArchitecturally,
HardwareEventObserved, PendingStateAtReaderEstablished, InterruptDelivered.
Only the first two have conditional/software or architectural support here;
actual event, established actual reader state and delivery remain absent.

## Correlated helper decision matrix

Each row uses separate SSP/frame, auxiliary H/threshold and pending identities.
S denotes the24F8 SSP lineage; F this CAL's creator/current frame generation;
H/T independent auxiliary sources; C the exactRB2763 clear; P a separately
supplied conditional post-C ADC factor. None is an executable scenario field.

| Correlated sources/conditions | Listed route and writes | Earliest unresolved dependency /static status |
|---|---|---|
| S/F safe; reset-derivedH0; C; no fresh update | RB5CA0old0/ZF1→JEQ→5CCE marker/BRK5CD2 | Actual entry/absence-of-event/control effects; ConditionalFaultRoute |
| Same H0; C→freshP retained at reader | RBold1/ZF0→P2/indexed ADC body→RT5CCD | P unobserved; P2/ADC/masks/currentframe/RT; ConditionalNormalReturn only |
| IndependentlyH1; ownedT; d<C8 | Timer/mask route→RT5CCD; IRQ reader bypassed | TM2/control/frame/return; pending not necessary on this route |
| H1; d>=C8; C→P old1 | ADC fallback body→RT5CCD | Additional timer/mask/ack history and P/RT; conditional only |
| H1; d>=C8; readerold0 | Fault marker/BRK, not normalRT | Same history/control gates; ConditionalFaultRoute |
| HypotheticalF019A | Old DATA zero invalidated; new CAL bits1/2=1 | FrameAliasBlocked for old owner; no M2ah shortcut |
| HypotheticalF0230 orF025A | H1 or threshold276D respectively, never both from one frame | Reaching SSP/independent other auxiliary source; timer/pending/RT unresolved |
| UnknownSSP/H/pending or mixed sources | No favorable route selected | FrameSourceNotEstablished /NativeReturnNotEstablished |

P2/indexed arithmetic remains bounded0..7; explicit ranges03CE..03D5 and
03C6..03CD are disjoint DATA target, but do not establish actual P2/ADC values,
peripheral effects, frame integrity or completed RT. JEQ5CA3 targets5CCE, not
precedingRT5CCD. BRK system-reset effects are not a forced return.

## Separate impact answers

| Question | Result |
|---|---|
| A: independent SSP source toCAL |24F8 root and exact conditional continuity chain; actual276A SSP not established |
| B: frame target non-alias |047E/F disjoint only under that complete domain; unknown SSP remains blocked |
| C: external effects afterIE narrowed |Native scan configuration and IE0 H0 polling semantics specified; actual ADC/event/async effects still unknown |
| D: conditional normal-return correctness |Exact frame/predicate/body obligations narrowed; no fake return |
| E: native firstRT without hardware history |NotEstablished/NotRun; documented possible factor is insufficient |
| F: same-machine owner toISR/caller |NotEstablished; no delivery/frame/context bridge |

The strict DATA019B frontier is not advanced by explicit-address disjointness.
SSP continuity and ADC pending evidence are independent obligations, neither
can supply the other. This milestone adds concrete source/context/configuration
facts, not just more tests or a repetition of M2ao.

## Verification, preserved statuses and STOP

Complete primary pages were visually reviewed for CAL/RT/SF, SSP layout,
word alignment, exchange, flags, arithmetic/indexing, RB, branches and BRK;
complete manufacturer ADC/IRQ tables, diagrams and notes were reviewed with
archive applicability limits retained. No new production ISA correction.
Unresolved C8 remains PrimaryConflictUnresolved; no OR/AND adopted.

Invented isolated regressions distinguish explicit SSP from auxiliary sources,
original CAL creator from fresh restored storage generation, exact clear
interval from stale pending, nullable unknowns, frame/IRQ widths and all
host/second-machine/forged-ordinal/actual-execution promotions. No numerical
expected values come from Rust observations. Full QA/protected/exact-SHA CI
results are sealed in the new private report saved last after delivery checks.

Historical M2an fix complete; M2am PrimaryConflictUnresolved; M2al/M2ak/M2ao
Research/Blocked; M2ao frontier unchanged; M2ah STOPbefore5722; DATA019B.2
actual owner NotEstablished;5722/5725/5733 DynamicNotRun; M2tJGT233A
Blocked/Unresolved; M2ag/M2af unchanged; strictM2iBlocked. IRQNotInjected,
TimerEvolutionNotModeled, EnclosingIRQFrame/RecoveredEcuScheduler NotEstablished,
ElapsedTimeNone; RT5CCD/RT5801/new caller returns NotRun in M2ap.
PcInspectionOnly/NotFlashReady; physicalRpmAvailable=false; physical fuel/time/
degrees unavailable; GUIr3 paused/NotRun; D1/D2 interactiveNotRun; hardware/
fullbootNotRun; FirmwareBIN0. Vendor InquiryDraftReady/NotSent.

Next evidence step: independently verify same-machine first RAM-test CAL2689
frame/exchange-restoration/RT5C80 history; no experiment is performed here.
STOP after final report: no M2aq,JGTfix,runtime reset,IRQ injection,first5722,
fullboot,GUI or hardware work.
