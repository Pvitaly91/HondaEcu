# M2cc — PROGRAM60EC to DATA011F.3 bridge provenance

M2cc is static Research-Only work over exact accepted M2cb commit
`8c4d573c7b745a4021d7da4c2b318ac07c800633`. It investigates a longer conditional
source history without appending invented earlier generations to the accepted
M2bz session that starts at063B. No CPU/Bus execution, IRQ injection, Rust
feature, firmware output or hardware/GUI operation is introduced.
`FirmwareReady=false`.

The research classification is
`CONDITIONAL_BRIDGE_FEASIBILITY_ESTABLISHED / EXECUTION_BLOCKED`.
This describes conditional instruction/CFG/frame obligations and the external
transition frontier. It does not establish actual5F6B generation, copy execution
or an operand read at064C. Final delivery separately requires source/QA gates,
exact-SHA research CI, complete static canonical comparison and evidence seal.

## Exact producer and helper

| PC | Form | Length | Reviewed effect |
|---|---|---:|---|
|5F45|CLRB A|1|AL0,AH retained,ZF1,DD0;CF/HC retained|
|5F66|LCB A,N16|4|AL=PROGRAM60EC,AH retained,ZF updated;CF/HC/DD retained|
|5F6A|SLLB A|1|DD0;AL shifted left,CF=oldAL.bit7;ZF/HC/DD/AH retained|
|5F6B|MB off0217.3,C|3|Replace0217.3 withCF; retain other DATA bits and architectural flags|

The original PROGRAM byte is authenticated privately from the immutable ROM and
listing. Public code describes its bit transformation without publishing the
OEM byte. PROGRAM60EC is distinct from DATA60EC. Invented tests use independently
chosen bytes and invented source identities, never private extracted fixtures.

The selected helper has226 exact listed nodes:182 core and44 out-of-line nodes,
253 edges, no nested call sites and one normal RT at60E4. The graph is acyclic.
The writer5F6B is instruction14 of the mandatory entry prefix and dominates
normal return. No reviewed entry-to-return bypass of5F6B exists. Trio edges
5F66→5F6A→5F6B are sequential; alternative asynchronous/unlisted entries are not
silently admitted. Syntactic entry-to-RT path lengths129..193 are graph counts,
not actual retirements or physical time.

The prefix establishes DD0 independently of incoming callerDD. Immediately
before5F66, AL is the shifted PROGRAM60EB byte, CF its oldbit7, and ZF reflects
the preceding LCB's zero result. AH is retained from entry. The model keeps
this separate source byte invented/unknown as appropriate; it does not invent
private60EB state or pretend to replay every helper instruction.

Later6039 writes DATA0217.6 and also dominates return. Under owned page0200
and no interfering alias, selected0217.3 still derives from5F6B, while the
whole-byte storage generation now belongs to6039. Same-value RMW remains a new
storage generation. No other literal selected helper writer replaces0217.3.

Within reviewed addressing, local byte writers are r0/r1/r2; their low offsets
cannot equal0217's offset7 in an eight-aligned local bank. Explicit DP assignments
conditionally resolve DATA0356 and0382/0383 writes. This narrows helper-only
alias risk without granting a full native LRB/SCB/SSP/STACK or IRQ history.

## Two producer callers and exact return obligations

| Route | Exact call | Target | Conditional return PC | Earlier context |
|---|---|---|---|---|
|P|CAL27D0,length3|5F45|27D3|Startup-region local prefix; full native state not observed|
|Q|CAL4069,length3|5F45|406C|VCAL4068 to28AE must first return; its state cannot be borrowed fromP|

For each CAL, the return word is PC+3 at even(oldSSP), followed by SSP−2.
Matching RT60E4 first incrementsSSP then reads that same correctly retained
frame. The two callers never share an invented frame identity. Ordinary PSW
flags are retained by CAL/RT; unresolved physical SF mapping is not invented.

P's reviewed conditional local prefix27BC..27CE derives a privately bound A
value and CF1/ZF0/DD0 if it completes. Q's A/flags after VCAL4068 remain
separately unowned. Listed page0200,
local0208 and USP0180 annotations are conditional context evidence, not proof
of fullPSW/SCB2 or an observed safe SSP. Producer SCB must not be copied from
receiver setupPSW0102.

A concrete frame counterexample is known: incoming evenSSP0382 overlaps the
mandatory final60E3 word store to DATA0382/0383. Its0500/0700 value differs from
both27D3 and406C, preventing the matching return in that explicit owned context.
The frame at0006/0007 also aliases A: mandatory AL writes and final A0500/0700
cannot preserve either caller's return word. These are stronger than merely
reporting an unknown alias. Other unknown frame
and architectural STACK overlaps remain unresolved, not actual overwrites.

## Producer return to copy root: the first external gap

| Route | Reviewed post-return prefix | First unproved call/return boundary |
|---|---|---|
|P,from27D3|20 listed nodes|CAL2810→5BF5,requiredreturn2813|
|Q,from406C|110 listed nodes|VCAL4165→28AE,requiredreturn4166|

Neither prefix contains0379,03ED,0408,5C35 or063B. The frozen conservative
whole-listed CFG, including both callee and return-summary edges, has closures
of6289/6203 nodes fromP/Q return respectively; neither reaches those targets,
5C2B or alternate copy-helper caller10BE. This is
`NoPathWithinReviewedDirectCFG`, not global impossibility of computed, unlisted
or physical entry. No software edge is created from an IRQ vector reference.

Q4077 clearsMIE and4133 setsMIE;4133 dominates the reviewed prefix boundary4165.
Enabling MIE is not actual pending-factor generation, dispatch or frame proof.
Primary architectural reference associates INT1 with IRQ/IEbit15/vector0026
and serial receiving-ready/BRG-overflow withbit3/vector000E. Private vector-word
inspection matches entries0379/03ED. The incomplete archival hardware edition
qualification remains; this is architecture reference, not new C8 silicon or
electrical verification.

An external receiver transition needs the corresponding real pending factor,
IE, MIE, priority, entry selection, PC/ACC/LRB/PSW interrupt frame and its safe
SSP footprint. Those facts are not established for either candidate history.
Conditional helper completion itself still needs the right caller-created
frame. Unknown post-return calls and unknown computed contexts do not become
successful scheduling simply because a direct path is absent.

## Receiver and reader continuation reuse

The existing328-node M2cb receiver CFG and alias library are reused unchanged.

| Receiver | Copy sequence | Further obligation |
|---|---|---|
|0379 INT1|CAL038A→5C2B,load5C33/store5C35,RT5C3F→038D|Own helper frame plus reader-reaching predicates|
|03ED serial RX/BRG|load0406/store0408 after context setup|040E retained0128.3 gate; a path bypasses063B/064C toward065F|

Receiver setup gives LRB0021/page0100, SCB2 and USP0280 in the reviewed domain.
L A,S8[USP] setsDD1 and reads word0216/0217; ST word writes011E/011F.
Little-endian mapping preserves0217.3→011F.3. Each copy creates a fresh target
storage generation even for the same value. Copy completion alone guarantees
neither a valid helper return nor reaching064C.

The copy helper5C2B has two listed CAL callers,038A and10BE. The latter's
LRB0020/USP0280 setup and return10C1 form a separate context; it is not silently
renamed INT1. Neither producer return reaches it in the reviewed direct graph.

Conditional continuation includes CAL063B→54F5→RT5688→selector063E..064A→064C.
That accepted technical CAL frame does not prove enclosing producer/IRQ frames.
Earlier CAL0611 or0635 and their matching returns can establish012A.3=1 at
0614/0638; no-earlier-call062C can clear it. Both earlier calls cannot occur in
one reviewed bounded invocation. Source histories and selector generations may
not be spliced across machines. Technical M2bz DATA012A00 is not imported into
an earlier-caller history.

If an independently owned011F.3 is0,064F additionally needs its own011B.7 owner;
M2cb's blocker remains. If it is1, the taken boundary can be considered separately
with that bit's provenance and the source-consistent012A.3 context. Neither
branch is executed here;0657,0664/56BE and0667 remain outside execution authority.

## Bit provenance, storage and actual byte-read admission

Three separate results are retained:

- `SelectedBitSemanticLineageEstablished` as a conditional relationship.
- `WholeByteValueNotFullyOwned` when neighbors lack independent value/owners.
- `ActualByteReadNotAdmitted` for production Bus use.

Unknown neighbor bits do not invalidate a theoretical selected-bit relationship.
They cannot be defaulted to0/A5/FF to manufacture a byte journal. A later source
update after a completed copy need not destroy the already copied target token;
an update before the copy or an overlapping target write can invalidate it.
Unknown indexed/indirect writes, alternative LRB0023/0042, DP/USP contexts,
system-stack and nested IRQ footprints, startup2710, RAM-test5C68/5C6C, NMI0048
and bitmap5B86/5B8A remain qualified preservation hazards. A possible alias is
not asserted as an actual overwrite. The inherited primary SBR direction
conflict is not resolved by this milestone.

## New constraint proof and delivery

Twelve small new invented constraint cases cover both callers, both roots,
PROGRAMbit0/1 and explicit blocked/unsatisfiable controls. Matching invented
CAL frames, late byte RMW, copy chronology, source tokens and storage ordinals
are compared against an independently written oracle. These relation indices
are not native event indexes or write ordinals; the corresponding native lists
remain empty. Register-effects records cover the reviewed prefix/trio formulas,
not a fabricated complete CPU trace through226 instructions.

The28 negative requirement categories include input, constraint, fabricated-effect
and historical-identity refusals. A wrong receiver root, stale/same-value frame,
source overwrite, wrong endian, imported history, invented full byte, fake IRQ
edge or fake execution claim cannot satisfy the closed proof. Old M2cb invented
corpus and original runtime are not replayed.

The relational timeline requires one receiver boundary after the matching return
and before the copy, and one reader relation after the copy. Reordered, missing
or repeated boundaries cannot supply a completed witness. Known architectural,
SCB-bank, page0200 local/data and DP0356 frame-alias domains cannot be hidden by
a disjointness Boolean; unresolved ones remain blocked rather than globally
unreachable.
These examples concern completed-helper-return histories. An interrupt before
the helper returns requires a separate nesting/frame/continuation proof and is
not declared globally impossible by rejection of a spliced example.

Canonical evidence includes four complete analyses (helper contracts/CFG,
bridges, preservation obligations, minimal frontier) plus12 constraint results.
Local/Ubuntu/Windows comparisons use every decompressed byte and provenance field.
New CPU/ROM executions and retired instructions stay0.

M2cc has a separate finite15-file projection over all1150 accepted M2cb raw blobs.
Its additions-only approval is provided after independent content review; no
guard can silently approve its changed fingerprint. Frozen M2cb/M2ca pins and
modules remain unchanged. Only the reviewed workflow overlay and finite source
additions select router plus two static OS jobs. Unknown, production/runtime or
inherited-source changes and router errors require full historical QA. If the
research lane runs, historical17 logical checks are NotRun, not fresh17/17 PASS.

Two preservation exceptions are inherited: generated historical runner loss and
authorized external Python tooling change. No third exception is allowed;
old expected hashes/seals/reports are unchanged and strict preservation staysfalse.
Current source, compact evidence and final Ukrainian report remain local; no
private ROM, OEM windows or raw source byte goes to CI or GitHub.

## Concrete next evidence frontier

First establish the selected producer caller's own frame and matching RT60E4
without pointer/STACK overlap. Then narrow P's2810 return or Q's4165 return and
the corresponding pending/IE/MIE/priority history before a genuine0026→0379 or
000E→03ED receiver transition. Bind the actual source generation through either
0406/0408 or5C33/5C35, including6039's retaining RMW and any intervening aliases,
then through the correctly returned063B/5688 and source-consistent selector path.

Serial0408 avoids the extra038A/5C3F copy-helper frame; INT1 has different IRQ
source and predicates. Neither has a proven integrated producer-to-reader
history, so no overall winner is invented. The task does not propose broad
whole-ECU emulation as the first step and does not implement interrupt delivery.

ActualHardwareEcuExecutionNotObserved; RecoveredFullEcuSchedulerNotEstablished;
EnclosingIRQFrameNotEstablished; PhysicalNativeStackSafetyNotEstablished;
Actual5F6BWriterGenerationNotObserved; Actual0217To011FCopyGenerationNotObserved;
ActualBranch064CNotExecuted; DATA011B7CurrentNativeOwnerNotEstablished;
IRQDeliveryNotInjected; TimerEvolutionNotModeled; PhysicalTimingEquivalenceNotEstablished;
ElectricalOutputNotObserved; TRNSIT0657NotExecuted; CAL0664NotExecuted;
Producer56BENotExecutedInM2cc; Return0667NotExecuted;
NativeNextEventSelectorHandoffNotEstablished; FullNativeDownstreamRejoinNotEstablished;
TargetProgramEquivalenceNotEstablished; FirmwareIntegrationNotEstablished;
FirmwareReady=false. Stop after delivery; no M2cd, firmware, GUI or hardware.
