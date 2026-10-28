# M2ca — Native Branch064C source provenance / Research-Only

M2ca extends the accepted M2bz research question, exact base
`f77d2cc1468fe128ba4ad393c3e0a1a5dab423fc`. The source-provenance preflight
blocks original-ROM branch execution before its first reader. No new Rust
feature, executable, CPU/Bus capability, original-ROM runtime or firmware
payload is added. `FirmwareReady=false`.

## Source decision

| Original DATA | Width | Proposed reader | Existing source |
|---|---:|---|---|
|011F|8|064C JBS bit3|UnownedTechnicalBusCanary_NotBranchAuthority|
|011B|8|064F JBS bit7|UnownedTechnicalBusCanary_NotBranchAuthority|
|012A|8|0652 RB bit0;065F RB bit3|ExistingAuthorizedTechnicalSource; retained low bits|

The accepted M2bz schema has23 ordinary DATA bytes, two explicit old-stack
canary bytes and a separate once-only selector snapshot. It does not initialize
011B/011F. The audit session constructs RAM with technical fillA5. A diagnostic
snapshot of that fill is not a DATA operand read, source owner or native writer.
No byte/word access in its49-step prefix overlaps either missing branch byte,
and neither reader is admitted by its permissions. Evaluating A5 bit3/bit7 to
choose a verified branch would promote a canary into unsupported authority.

LRB0021 resolves off-page operands in0100; r0..r7 occupy0108..010F. SCB selects
the pointing register bank, not another off-page byte. Potential word aliases
011A/011B and011E/011F are included in the overlap audit. Historical caller-buffer
writers0408/5C35 to word011E/011F and M2ag adaptive fixedSource ownership of011B.7
are distinct historical sources, not generations of the accepted M2bz machine.

M2bz initializes012A to00 or80. Native5685, retirement40, reads that byte and
clears only bit7, writing00 in every accepted case; eight same-value writes per
domain still retain actual writer identity. Bits0/3 remain their explicitly
technical initial0. RT and the selector suffix do not overwrite012A. These
facts establish neither a physical initial owner nor a new M2ca generation;
old generation objects are not imported into a new machine.

The existing public fixture maps original0117 to literal public011B and
original012A to public012D. Its literal011B is written by the mapped55C1 site;
that is semantic0117 ownership, not branch011B ownership. Literal address
coincidence cannot replace source-matched provenance.

The private local Stage0 receipt authenticates the accepted seal and reads the
already saved16 private+16 public records without rerunning them. Public CI
does not consume private records or a ROM. Its source-domain checks and invented
vectors are independently labeled. Historical scratch00/55/AA, fixedSource
history or host gate booleans are never transferred into the new domain.

## Reviewed conditional forms

| PC | Form | Length | Static successor |
|---|---|---:|---|
|064C|JBS off011F.3,rel8|3|064F or065F|
|064F|JBS off011B.7,rel8|3|0652 or065F|
|0652|RB off012A.0|3|0655|
|0655|JEQ rel8|2|0657 or065F|
|065F|RB off012A.3|3|0662|
|0662|JNE rel8|2|0664 or0667|

JBS preserves architectural flags/DD. RB derives ZF from the old selected bit
before clearing it; a same-value clear is still an expected write. JEQ/JNE use
that ZF, not the already cleared byte. A/CF/HC/DD/OtherPSW/LRB/SCB/SSP and
unwritten neighbors are retained by these reviewed forms. Primary references
remain JBS printed3-65, RB3-114 and JEQ/JNE3-66, as reviewed in M2af/M2ag.
Decoder recognition is not substituted for manufacturer semantics.

The conditional paths are A:064C→065F→0662→0667, B:064C→064F→065F→0662→0664,
C:064C→064F→0652→0655→065F→0662→0664, and
D:064C→064F→0652→0655→0657. Their reference-only totals52/53/55/53 include
the accepted49-step prefix. Four illustrative invented vectors sum to213
reference instructions; that number is not an observed retirement count.
All four original-ROM routes remain unadmitted because011F lacks a source.
Fallthrough also lacks011B; the current012A domain cannot satisfy A's oldbit3=1
or D's oldbit0=1. B/C remain conditional CFG descriptions, not executions.

Potential future windows `[063B,0664)`41B and `[54F5,5689)`404B would contain
445 source bytes and65 reviewed sites. Private read-only source review checks
the six new instruction extents against the unchanged ROM, frozen listing and
primary encoding rules. This grants neither CPU admission nor an observed CPU
fetch from the expanded window. Windows do not authorize gap instructions.
0657/TRNSIT,0664/CAL56BE and0667 continuation are never executed here.

## Public evidence and delivery qualification

The source guard compares all1119 accepted raw Git inputs, allowing only the
deterministic workflow projection and14 finite new research files. Local reuse
of three already recorded physical XML representations is explicit; CI uses raw
Git bytes. Frozen historical guards are not invoked against the changed tree.
No historical source, contract, oracle or production Rust semantics are changed.

Two independent pure calculations compare complete invented per-PC states,
PSW, expected reads/writes, ordering, same-value effects, paths and terminals.
Those expected architectural effects are not production logical/raw journals.
Thirty-three negative requirement categories distinguish invented metadata and
fabricated expected-trace refusals from production CPU or private ROM proofs.
Static canonical bytes are compared in full across local/Ubuntu/Windows.
Original-ROM runtime canonical comparison is NotApplicable_NoAdmittedCorpus.

The workflow retains all17 historical checks behind a conservative full-QA
lane. Only the exact reviewed blocked-research source projection may select a
router plus two static OS jobs; any other source change or routing error selects
the inherited full-QA lane. Deliberately unrun historical jobs in the research
lane are not reported as fresh17/17 historical QA. No Cargo build is required
for this blocked milestone.

Preservation retains the inherited generated-runner exception separately from
the explicitly authorized external Python tooling exception: one each, total2.
Old expected bindings and M2bz seal remain unchanged; strict historical
preservation is false and new unauthorized differences must remain0. Private
receipts retain the original pending observation and later direct human
authorization; the cause of the external tooling change remains unresolved.

Qualified research verdict after all available delivery gates:
`M2ca RESEARCH_COMPLETED / EXECUTION_BLOCKED — Branch Source Provenance Not Established`.
This is not accepted executable continuity. The next missing evidence is an
authorized full-byte011F owner, plus011B.7 ownership for a reached fallthrough,
with correct write generations and no intervening overlaps in one machine.

ActualHardwareEcuExecutionNotObserved; RecoveredFullEcuSchedulerNotEstablished;
EnclosingIRQFrameNotEstablished; PhysicalNativeStackSafetyNotEstablished;
InitialDATA011FNativeOwnerNotEstablished; InitialDATA011BNativeOwnerNotEstablished;
TimerEvolutionNotModeled; IRQDeliveryNotInjected; PhysicalTimingEquivalenceNotEstablished;
ElectricalOutputNotObserved; TRNSIT0657NotExecuted; CAL0664NotExecuted;
Producer56BENotExecutedInM2ca; Return0667NotExecuted;
NativeNextEventSelectorHandoffNotEstablished; FullNativeDownstreamRejoinNotEstablished;
TargetProgramEquivalenceNotEstablished; FirmwareIntegrationNotEstablished;
FirmwareReady=false. Stop after delivery; no M2cb, GUI, hardware or firmware work.
