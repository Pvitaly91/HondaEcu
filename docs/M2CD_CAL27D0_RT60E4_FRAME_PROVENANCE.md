# M2cd — CAL27D0 / RT60E4 frame provenance

M2cd is static Research-Only work over exact accepted M2cc commit
`d461861c8a8714d34d66d5933646e4158b6adbc4`. Its research classification is
`CONDITIONAL_FRAME_INTEGRITY_ESTABLISHED / EXECUTION_BLOCKED`.
Actual CAL27D0, RT60E4, frame generations and native return27D3 are not observed.
No CPU/Bus execution, new Rust feature, IRQ, full boot, firmware or GUI/hardware
operation is introduced. `FirmwareReady=false`.

References: [M2cc](M2CC_DATA0217_011F_SAME_MACHINE_BRIDGE.md),
[M2ap](M2AP_SSP_ADC_PENDING_PROVENANCE.md),
[M2aq](M2AQ_FIRST_RAMTEST_CAL_RT_PROVENANCE.md),
[M2ao](M2AO_RESET_TAIL_019B_PRESERVATION.md),
[M2ar](M2AR_RESET_WDT_EXTERNAL4700_PROVENANCE.md),
[M2as](M2AS_RESET_WDT_CHAPTER4_EVIDENCE.md),
[M2aw](M2AW_NX8_200_TARGET_ABI_CONTRACT.md).

## Exact frame geometry and its applicability

Reviewed manufacturer CAL addr16 has length3 at27D0 and encoded target5F45.
The next PC,27D3, is stored little-endian at aligned-even incomingSSP, then
SSP is decremented by2. Ordinary RT60E4 first incrementsSSP by2, then reads
PC from its aligned word address. With no unaccounted SSP mutation, it reads
the same frame and restores the incoming register value, including its parity.
The arithmetic is modulo65536. An odd SSP masks the word-address low bit;
M2by's strict even technical admission is not a global manufacturer ban.

These formulas do not override architectural aliases. SSP is DATA0000/1,
LRB0002/3, PSW0004/5 and A0006/7. A frame store toSSP can affect its own later
decrement; exact capture/update behavior is not silently assumed. A store to
LRB orPSW changes addressing/flags/SCB and has standard read-mask obligations.
Intrinsic CAL/RT flag retention does not undo an aliased PSW store. RT retains
callee A/LRB/PSW rather than restoring a caller snapshot; RTI is a different form.

For frame0006, CAL itself first setsA=27D3. CLRB5F45 then writesAL=0,
retainingAH, and later word loads replaceA. A correctly sized AL footprint
is a byte write, distinct from the resulting wholeA value.

The instruction manual prints SF-clear for CAL/RT while MAC66K assigns stack
flag discussion to nX-8/300. That primary applicability conflict remains.
PhysicalSF storage is not invented. Independently reviewed PSWLbit4 is the
standard user flagF0, not SF or a reserved default: native6019 must supply its
temporary value before6037 consumes it.

## SSP source and exact earlier returns

The nearest independent explicit candidate is MOVSSP24F8,#047E. Reaching that
writer requires genuine applicable cold/reset history; a reset vector alone
does not establish it. WDT24F4, DATA4700 read251C, P4 outcome2528,
P4 pulse gates262C/2637/2642 and fresh IRQH.5 after261E are distinct prior
control/effect obligations. Architectural resetSSPFFFF is not producer SSP.

The two adjacent exchange pairs2531/2533 and254D/254F temporarily replaceSSP
with the self-test patterns. Their saved-A identity and actual restoration,
DD1/non-stack context and absence of asynchronous/alias mutation are required.
Restoration is a new register generation, not an unchanged register.

| Caller | Required own return | Specific source/history obligation |
|---|---|---|
|2689 to5C5C|RT5C80 to268C|First current CAL frame; indexed5C68 overwrite and5C6C semantic restoration|
|268D to5C5C|RT5C80 to2690|A different invocation/frame after genuine2689 return|
|276A to5C86|RT5CCD to276D|Owned ADC/timer/pending/control body and intact own frame; may repeat|
|2777 to5CD9|RT5CF9 to277A|Owned DATA03D1 and independently justified comparison/branch predicates|
|27D0 to5F45|RT60E4 to27D3|All required earlier history plus current frame integrity|

The inherited RAM-test rank proof has510 conditional iterations, two distinct
calls each. Its first indexed word is the frame047E/F:5C68 and5C6C interrupt
storage generation, while exact saved semantic creator can be restored.
These are not1020 observed returns. Cold marker269D to26F0 excludes the
seven optional calls and unknown-pointer store26BA only in its original
retained cold domain. The alternate entry cannot borrow this lineage.
No balanced-call count substitutes for the actual source/return chain.

New narrow source verification identifies CAL2777's17-node helper, normal
RT5CF9 and faultBRK5CF8. It reads DATA03D1 at5CDC. Candidate earlier source
is indexed ADC store5CAF with selector3 and owned ADCR1H/P2 history, not a host
byte. C8/JGT at5CDF and5CE7 remains PrimaryConflictUnresolved. In the separately
retained first-call domain,2773 ownsF7=1; the error route's5CF1 decrement gives0,
so5CF4 falls through5CF6 toBRK5CF8. It cannot quietly return by assuming a
different counter. Private comparison thresholds and raw bytes stay private.

Conditional cold context can now be traced to SCB0 from24FF with restored
PSWL exchanges, LRB0041 from2744, USP0180 from2754 and finalDP0373 through
27B6/27BA. This is not fullPSW or actual incoming SSP. CAL276A/2777, later ADC
reads277A/277E/27A4 and DATA03C6/03CD reads remain source/effect dependencies.
ProducerSCB0 lineage must not be replaced by receiverSCB2.
The complete conditional cold-source model requires that SCB0 context;
other-bank and unknown-bank footprint tests are separate invented-only software
domains and do not claim the cold source's native context.

## Helper writes, aliases and termination

The immutable M2cc graph is reused:226 nodes,253 edges,182 core plus44
out-of-line, acyclic, one normalRT60E4, no nested CAL/PUSH/POP/RTI and no
explicit SSP/LRB writes beforeRT. There are no X1/X2-indexed or USP-relative
operands in this helper. Seven DP accesses have explicit reaching definitions.

The new inventory has238 architectural footprints, including A/PSW/register
aliases as well as functional DATA stores. It is not an all-write native journal.
Exact destinations in the owned page0200/local0208 domain include20 off-page
RMW sites,7 local byte writers,7 selected-bankDP assignments, DATA0356 and
word0382/3. SCB-dependent pointer storage is enumerated over all8 banks.
A mandatory instruction that overlaps only some unknownSCB banks is may-overlap,
not a definite overwrite. Word high-byte intersections are retained.

All reviewed complete, defined, synchronous graph paths end atRT60E4.
Source-bound filtering of24 code-byte zero predicates and correlated carry/bit
relations narrows the129..193 syntactic envelope to4 conservative paths,
146..149 instructions. This aggregate is supported by a separate private proof;
it is neither actual retirements nor a complete CPU replay or physical time.
DATA03CF.7 supplies one correlated branch source. The post-XORB PSWH6016 CF
feeding6019/F0 and6039/609C is separately unknown: primary warnings leave
CF/ZF/HC undefined after logical PSW operations, so an exact complement of
DATA03C7.7 is not established. DATA03C7 is only a possible earlier input.
The4-path bound already leaves609C unconstrained and does not depend on that
rejected complement formula. Correct producer/consumer relations are required;
unknown values are not replaced with host-selected branch outcomes.
Defined memory reads, applicable accumulator mode, no context-changing alias
and no asynchronous/unlisted diversion remain conditions for termination.

Readable user-manual spreads32/33 and34/35 have historical source-ZIP CRC
failure qualifications from M2as. Their extracted images remain hash-bound
and were fully reviewed within that bounded reference scope; whole-archive
integrity is not PASS. Standard F0 bit identity has independent E2E1027-27-Y4
datasheet support. No archived image or expected CRC was repaired or rebased.

| Frame class | Synchronous reviewed result | Separate effect/remaining obligation |
|---|---|---|
|0000/1|Control self-alias blocked|Frame store affectsSSP; no ordinary postCAL architecture claim|
|0002/3|Control context alias blocked|LRB page/local/read-mask changes|
|0004/5|Control context alias blocked|PSW/SCB/flags/read-one bits change|
|0006/7|Mandatory clobber|CAL writesA; CLRB5F45 and finalA replaceframe|
|0382/3|Mandatory final60E3 clobber|Conditional final0500/0700 cannot equal27D3|
|047E/F|Disjoint from all reviewed synchronous helper writes|Still requires SSP lineage, physical map, writable retention and no asynchronous overlap|
|0216/7|Mandatory RMW destroys frame generation|CAL also replaces prior producer-buffer ownership|
|011E/F|Helper-disjoint in this context|CAL replaces copy-target ownership; later copy needs its own generation|
|0212/3 and011A/B|Helper-disjoint in this context|CAL changes other buffer ownership; no integrated copy/011B claim|
|Selected-bankDP storage|Must or may by exactSCB|DP assignments can overwriteframe; unknownSCB is not disjointness|
|Other SFR/pointing/unknown addresses|Context-specific or unresolved|Numeric address arithmetic is not memory permission|

Standard MSM66201 maps047E/F as external DATA; standard MSM66207 includes it
in documented internal RAM. The incomplete archival user-manual applicability
and actual customer ASIC/board mapping remain explicit. Code using047E does
not prove physically writable retained stack memory on the actual ECU.

5F6B still conditionally transfers PROGRAM60EC.bit7 throughCF to0217.3;
6039 retains that selected semantic producer while creating a new byte storage
generation. Unknown neighbors cannot be filled from this selected bit.
The new frame model records these effects with invented source IDs, without
replaying M2cc's old corpus or fabricating native writer ordinals.

## Independent model and evidence boundaries

The new bounded model and independently authored oracle compare full state,
aligned frame footprints, creator identity, source conditions, write generations,
control aliases and RT linkage. Same-value writes are fresh generations; a
numeric27D3 cannot restore semantic ownership. Mid-helper writes toSSP/LRB/PSW,
high-byte writes, unknown indirect/nestedIRQ events and host reseed invalidate
the corresponding intact-return claim. Unknown accumulator mode remains blocked.

Twelve curated invented cases and33 named negative requirements concern the
new frame problem. OddSSP and wrap arithmetic are separated from control-alias
realizability. Actual native instruction indexes/logical/raw-byte/all-write
ordinals are null. Model event IDs are never native events. CPU/ROM/retirements
remain0; actual frame-read admission isfalse.

Canonical data includes5 complete analyses plus12 invented results. All fields,
unknowns and provenance are retained for complete decompressed Local/Ubuntu/
Windows byte comparison. Private source verification, freeze, preservation
and final receipts are separate local evidence, not claims made by public CI.

M2cd has a finite16-file overlay over all1165 accepted raw M2cc sources.
The new additions are frozen before independent review and explicit literal
workflow approval; no validator can approve its own changed fingerprint.
The reviewed overlay changes only routing plus two static OS blocks. Unknown,
production or inherited changes and router errors retain full historical QA
fallback. If this research lane runs,17 historical logical checks are NotRun,
not fresh17/17 PASS. Final delivery still requires actual QA/CI/comparison/seal.

Two preservation exceptions remain inherited: generated historical runner loss
and authorized external Python tooling change. Strict preservation staysfalse,
old expected hashes/reports are not rewritten, and no third exception is allowed.

## Concrete minimum missing evidence and alternatives

Frame geometry is established independently of execution. Conditional047E
preservation is established inside the reviewed synchronous software domain;
0382 and0006 are exact negative classes. This does not establish that a native
CAL27D0 ever receives047E or that frame memory is physically applicable.

Alternative A,24F8 to27D0 source continuity, addresses the earliest source
authority gap: genuine reaching24ED, WDT24F4/external/pulse/freshIRQ gates and
the first owned CAL2689/exchange-restoration/RT5C80. Alternative B then requires
the specific276A and2777 returns; the new03D1/C8/error-frame analysis identifies
the latter's narrow missing predicates. Alternative C, helper047E preservation,
has narrowed the local overwrite question but cannot replace these earlier
sources, return histories or ASIC mapping.

The smallest next evidence is a rooted source-consistent frame/restoration proof
for2689 after the applicable cold-entry gates, followed by276A's own ADC/timer
return source and2777's03D1/branch source. The new17-node2777 region is a precise
independent later target, not a reason to skip earlier unresolved calls. Full
ECU emulation, arbitrary safeSSP snapshots and injected IRQ are not proposed as
the first action. Current-machine CAL27D0 generation, actual RT consumption,
native producer-to-receiver bridge,011F/011B ownership and downstream integration
remain unestablished even after a conditional local frame proof.

ActualHardwareEcuExecutionNotObserved; ActualCAL27D0NotExecuted;
ActualRT60E4NotExecuted; ActualFrameGenerationNotObserved;
NativeIncomingSSPNotEstablished; PhysicalNativeStackSafetyNotEstablished;
PhysicalSFNotEstablished; RecoveredFullEcuSchedulerNotEstablished;
EnclosingIRQFrameNotEstablished; IRQDeliveryNotInjected;
TimerEvolutionNotModeled; ActualProducerToReceiverBridgeNotEstablished;
DATA011F3CurrentNativeOwnerNotEstablished; DATA011B7CurrentNativeOwnerNotEstablished;
ActualBranch064CNotExecuted; TRNSIT0657NotExecuted; CAL0664NotExecuted;
Producer56BENotExecutedInM2cd; NativeNextEventSelectorHandoffNotEstablished;
FullNativeDownstreamRejoinNotEstablished; TargetProgramEquivalenceNotEstablished;
FirmwareIntegrationNotEstablished; FirmwareReady=false.
Stop after delivery; no M2ce, CAL/RT runtime, firmware, GUI or hardware.
