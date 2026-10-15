# M2bk bounded synthetic execution protocol

## Scope and evidence levels

M2bk specifies and statically checks a future isolated experiment. It does not
execute the M2bj composite, load it into a CPU, execute original ROM, or establish
target-program equivalence. JSON cannot confer execution authority.

The exact M2bj base is `be7ed4a72dc5f8758bfa4293db0f881ba9bb7536`.
The independently verified in-memory encoding identity is:

`91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1`

This identifies 51 bytes, 18 reviewed original sites and two abstract direct-J
sites, with 20 boundaries. M2bj primary/decode comparisons were 20/20 in both
incoming DD contexts; their streams were identical. Relocated JLT/JBS deltas are
+26/+10/+7. M2bk consumes source identities and reviewed IR, never those bytes.
The unchanged M2bj emitter regression remains a separate in-memory encoding
check, not an input to any executor.

Three evidence levels remain distinct:

1. `ManufacturerInstructionSemantics`: September 1991 OKI MSM66201 manual,
   SHA-256 `f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271`.
2. `ReferenceSourceSemantics`: M2av reviewed structured IR/bounded C11, M2aw
   architecture, M2bd dataflow, M2bh composition and M2bj encoding obligations.
3. `SyntheticExecutorObservations`: **NotRun**. Historical original-ROM bounded
   observations are a fourth, separately classified corpus, not new experiments.

Host C11 equality is not by itself proof of target instruction semantics. Rust
decoder tables are not primary manufacturer evidence. Future CPU output must
never define the reference expectations it is being compared against.

## Closed PROGRAM experiment

The future segment is half-open `[0x1000,0x1033)`, last byte `0x1032`. Entry PC is
`0x1000`. Only the existing verified M2bj emitter may supply its content.
Original ROM, arbitrary instructions, executable/HEX/firmware output and implicit
4096-byte padding are forbidden. PROGRAM and DATA are distinct address spaces.
Absolute indexing of a zero-based ROM vector is not a segment-base capability.

The closed 20-node inventory is in
`research/p28-word0196/synthetic_execution_protocol_contract.json`. Each node
binds its logical identity, synthetic PC, exact form/length, successor PCs,
flag dependencies and primary page. The reviewed graph has 23 edges, four
acyclic paths and exactly one terminal direct J on each path.

| Original identity | Synthetic PC | Form | Length |
| --- | --- | --- | --- |
| 556F | 1000 | LB A,page | 2 |
| 5571 | 1002 | SLLB A | 1 |
| 5572 | 1003 | ROLB page | 3 |
| 5575 | 1006 | LB A,r0 | 1 |
| 5576 | 1007 | ANDB A,page | 2 |
| 5578 | 1009 | CMP page,imm16 | 5 |
| 557D | 100E | JLT rel8 | 2 |
| 557F | 1010 | MOVB r1,page | 3 |
| 5582 | 1013 | ANDB page,A | 3 |
| 5585 | 1016 | JBS page.7 | 3 |
| 5588 | 1019 | JBS page.5 | 3 |
| 558B | 101C | ANDB page,A | 3 |
| 558E | 101F | ORB page,imm8 | 4 |
| 5592 | 1023 | LB A,page | 2 |
| 5594 | 1025 | ORB A,imm8 | 2 |
| AbstractJ NotBelow | 1027 | J address5596 | 3 |
| 55BF | 102A | LB A,imm8 | 2 |
| 55C1 | 102C | STB A,page | 2 |
| 55C3 | 102E | STB A,page | 2 |
| AbstractJ Below | 1030 | J address55C5 | 3 |

## Typed entry and retained context

Every scenario is explicitly `InventedOnly_NoNativeGenerationOwner`. A closed
snapshot supplies PC/u16, A/u16 with AL/AH/u8 aliases, PSW/u16, CF/ZF/HC/DD bits,
OtherPSW/low12, LRB/u16, SCB/low3, SSP/u16, all eight banks of four pointing
registers X1/X2/DP/USP/u16, a non-halted state and the unknown SF descriptor.
Unknown SF meaning/storage/width remain null, not zero or an invented C boolean.

The two incoming DD contexts are 0 and 1. First LB establishes DD0; every
subsequent DD0-only form must see it. LRB is `0021`, current page `0100`, local
bank `[0108,0110)`, SCB is incoming PSW low3. CF/ZF/HC/DD occupy bits15/14/13/12.
r0 is low(er0), r1 high(er0). Local bytes are physical DATA aliases, not separate
unrelated host registers. MOVB changes r1/er0 on NotBelow paths, so preserving
the whole er0 would be an incorrect obligation.

AH, HC, OtherPSW, LRB, SCB, SSP and every selected/unselected pointing bank are
retained at every expected step. All corresponding invented canaries are
explicit. No compiler ABI, C function frame, stack allocation or native SF
representation is inferred. The compact C reference's selected pointer fields
do not alone demonstrate preservation of every unselected target bank.

## Controlled DATA scope

All entries below are explicit invented initial bytes. No native ECU generation
owner or physical RPM/timer/peripheral/scheduler meaning is assigned. Permissions
are functional accesses, not permission for diagnostic snapshot reads to pollute
an active access journal. Bytes outside this closed inventory must not be touched.

| DATA | Read paths | Write paths | Alias/preservation |
| --- | --- | --- | --- |
| 0108 r0 | A/B/C/D | none | low(er0), retained |
| 0109 r1 | none | B/C/D | high(er0), copies initial0117 |
| 010A..010F | none | none | remaining local byte/LE word aliases retained |
| 0117 | B/C/D | A/B/C/D | independent page byte; RMW on B/C/D |
| 0124 | C/D | none | bit5 gate, retained, unread on B |
| 0128 | none | none | retained canary, no invented access |
| 012A | B/C/D | D | bit7 gate, D RMW OR1 |
| 018E | A/B/C/D | A/B/C/D | rotate-through-carry RMW |
| 018F | B/C/D | A/D | A store0F, D RMW AND |
| 0196/0197 | A/B/C/D | none | even LE16 word, retained |

`00C0` is a code-owned 16-bit immediate, never a DATA read. The logical R16
comparison read must match consecutive raw DATA0196-low/DATA0197-high reads in
a future raw journal; normalization must not hide, reorder or fabricate accesses.

## Four independent path obligations

Let `w=DATA0196+256*DATA0197`, `x=initialDATA018E`,
`q=(2*x+(x>>7)) mod256`, `m=initialr0 AND q`, `s=initialDATA0117`,
and `f=initialDATA018F`. Common prefix writes DATA018E=q. The carry output from
SLLB at5571 is the input of ROLB at5572, regardless of incoming entry CF.
Unsigned CMP at5578 produces borrow CF; JLT557D uses CF, not ZF or signed order.

| Path | Predicate | Instructions original/composed | Reads | Writes | Exit PC |
| --- | --- | --- | --- | --- | --- |
| A | w<00C0 | 10/11 | 5 | 3 | 55C5 |
| B | w>=00C0 and012A.7 | 12/13 | 9 | 3 | 5596 |
| C | w>=00C0 and not012A.7 and0124.5 | 13/14 | 10 | 3 | 5596 |
| D | w>=00C0 and both gates clear | 15/16 | 12 | 5 | 5596 |

Boundary controls are `0000/00BF/00C0/00C1/00FF/0100/FFFF`, both DD contexts.
Gate API inputs are complete bytes, not booleans:012A.7 mask128 and0124.5 mask32.
Earlier RMW destinations018E/0117 and local r1 do not alias012A/0124 for fixed
LRB0021; therefore all NotBelow gates are feasible within this invented scope.
This is not a claim of native reachability. Path C has no historical original-ROM
native witness and remains `StaticPrimaryAndInventedCoverage`.

Ordered writer identities are:

- A: `5572 -> 55C1 -> 55C3` (018E=q,0117=0F,018F=0F).
- B/C: `5572 -> 557F -> 5582` (018E=q,r1=s,0117=s AND m).
- D: `5572 -> 557F -> 5582 -> 558B -> 558E`, adding018F=f AND m
  and012A=initial012A OR1.

Every same-value store keeps its fresh ordinal. There is no store deduplication.
RMW reads precede their writes; local-register RAM writes remain distinguishable.
Path B suppresses DATA0124 entirely; DATA012A is written only on D.
Direct J documents zero DATA/SSP writes, no flag change, and replaces PC.

Terminal A has AL=0F,CF1,ZF0,DD0. B/C/D have AL=finalDATA018F OR F0,
CF0,ZF0,DD0. AH/HC/OtherPSW and retained context remain unchanged. Intermediate
CF dependencies5571->5572 and5578->557D are compared, not merely terminal AL.

## Future stopping, trace and comparison contract

Execute the final direct J, then stop with architectural PC5596 or55C5 **before
any target fetch**. These remain abstract continuation anchors. Never install
NOP/RT/BRK/stubs there and never call this a native ROM return. Exactly one J and
the exact ordered PC sequence are required, with counts11/13/14/16, maximum16.
No extra instruction, alternate branch, cycle, second J or out-of-segment fetch
may pass under a larger safety allowance.

Each expected step records index, synthetic PC, logical original/AbstractJ ID,
form/length, complete before/after snapshots (including DD and PC), ordered DATA
reads/writes, branch decision, provenance and external-transfer classification.
Reads record address/width/value/LE constituents; writes add old value, ordinal,
same-value identity and RMW/Store/LocalRegisterStore kind. Expected selected
PROGRAM extents are separate from DATA accesses and explicitly **NotObserved**.
Decoder lookahead probes are not automatically architectural fetch observations.
Actual observations must have a separately bound future schema and authority;
they cannot relabel expected JSON. Diagnostic snapshots belong outside the
functional journal window.

Future acceptance requires all three levels:

1. Structural: exact PCs/forms/branches/DD/exit identity and no external fetch.
2. Observable state/effects: registers/PSW, ordered reads/writes, same-value events
   and preserved context, with explicit raw/logical access normalization.
3. Bounded functional equivalence: identical invented inputs compared against
   independently fixed C11/IR reference state and ordered effects.

None includes full boot, IRQ, timer evolution, WDT, peripheral timing, physical
fuel/ignition effects, safe placement, actual ROM handoff or whole-ROM integration.

## Manufacturer form coverage

All16 required forms have reviewed primary pages: ANDB A,obj76; ANDB obj,A77;
CMP word90; direct J116; JBS119; JLT120/121; three LB forms124; MOVB153;
ORB A,imm160; ORB obj,imm163; ROLB obj173; SLLB A197; STB208 (PDF page numbers).
The operation diagrams, flags and DD tables establish the needed bounded
software rules, byte/word widths and branch semantics. No new compiler ABI,
native SF, peripheral timing or physical claim follows. ROLB's printed
description says word-long while its byte heading/diagram/exact form are used;
that documented conflict is retained, not silently corrected. Unrelated C8 JGT
and historical hardware/boot uncertainties remain unresolved.

## Existing emulator capability audit: future execution blocked

Frozen Rust runner0.43.0/protocol1/38 identities remain unchanged. The audit reads
cpu/bus/decoder/full_decoder/exec/runner/word0196_alternate and its tests. Presence
of implementation forms is not an independent semantic certification.

Six concrete capability gaps remain:

1. `SyntheticProgramMappingCapabilityNotEstablished`: Bus uses absolute indexes
   into a zero-based ROM vector; Image has id/rom but no segment base. An exact
   51-byte vector cannot silently become PROGRAM1000. No padding workaround.
2. `Exact16FormIsolatedAdmissionNotEstablished`: all16 forms occur in decoder/exec
   source, but generic synthetic admission lacks SLLB,ROLB,both ANDB directions,
   both ORB forms and direct J. Native word0196 admission is fixed to original
   scope556F and15forms without the new J. Neither is an authorized new route.
3. `ClosedSyntheticEntrySnapshotCapabilityNotEstablished`: the existing synthetic
   request lacks full A/SSP/all-pointing-bank/unknown-SF input. CPU defaults are
   concrete implementation defaults, not independently owned invented seeds.
4. `IndependentDataReadWritePermissionsNotEstablished`: scoped access shares
   read/write ranges and is not configured by the generic route as required here.
5. `OrderedInstructionFetchObservationNotEstablished`: fetch/peek is not an ordered
   instruction-fetch journal; program_reads tracks PROGRAM-as-DATA. Unique byte
   sets and compact post-state traces cannot prove the required per-step schema.
6. `PswSnapshotRoundTripCapabilityNotEstablished`: CPU PSW storage mask0337 and
   reads-one mask0CC8 prevent arbitrary invented OtherPSW/low12 from round-tripping
   unchanged. Compatible subsets satisfy `(OtherPSW & 0x0CC8)==0x0CC8`. This is a
   snapshot-domain compatibility gap, not a demonstrated ISA defect. Do not
   normalize the independent oracle to fit CPU behavior; future adapter/domain
   evidence must explicitly resolve it.

Existing source primitives do separate PROGRAM/DATA, implement aliases/flags,
retain same-value writes when journaling is configured, and check exit PC before
decode/budget. Thus a future isolated exit trap has a plausible source primitive,
not an observed new-stream proof. No current production admission is expanded.

## Independent static gate and regression boundary

Run `python -B research/p28-word0196/validate_synthetic_execution_protocol.py`.
It checks the raw contract identity before consuming its147 frozen prior-source
bindings, pins all three new research modules, applies reviewed pure-source
guards, checks source capability anchors and invokes the independent oracle.
The analyzer derives a statically selected reviewed IR path, not opcode execution;
the separately authored oracle uses explicit structured source formulas and does
not read/import/call the analyzer, operational codecs, emitter or CPU.

The fixed test matrix has224 complete expected-case equalities (A64/B80/C40/D40),
plus8 carry/same-value controls. A separately named448-case extended domain
covers all8SCB selectors and HC0/1; the oracle also performs its own448-case
self-check. Domains overlap and are not summed as independent ISA proofs.
Before first comparison a fixture-only gate-byte API mismatch was corrected;
literal mathematics, oracle and original source/seals were retained unchanged.
No expected values were fitted to analyzer output.

All36 required refusal categories are represented:29 semantic/input/effect/CFG
mutations and7 authority/metadata refusals. Six further reviewed-IR corruptions
exercise AH, compare carry, JLT dependency, ROL carry and CFG/gate ordering.
Negative results require deterministic atomic refusals and unchanged inputs.
Source-policy malicious fixtures are parsed only, never executed. Guards are
defense in depth for hash-bound reviewed trusted source, not a Python sandbox.

CI adds one static research-only Ubuntu/Windows step. Existing M2bj emission and
all prior checks remain intact. Full Rust/Core/CLI/Desktop, C11/IR/C# differential,
historical research, formatting/privacy/protected gates remain delivery
requirements. Desktop retains its existing timeout/assertions: M2bj Option B
does not automatically apply to M2bk.

## Verdict and next admission

Passing the static gate establishes
`M2bk Bounded Synthetic Execution Protocol Established`, including independent
reference-state, four-path, external-trap and ordered state/effect obligations.
The emulator gaps above are explicit blockers for a future experiment, not
grounds to fabricate execution evidence.

Unchanged: `ActualSyntheticCompositeExecutionNotRun`,
`TargetCPUExecutionNotObserved`, `NativeExitIsolationNotEstablished`,
`ActualDownstreamRejoinNotEstablished`, `PhysicalROMPlacementNotEstablished`,
`TargetProgramEquivalenceNotEstablished`, `FirmwareIntegrationNotEstablished`,
`FirmwareReady=false`. Target objects/HEX/FirmwareBIN and new CPU/ROM executions
are zero. Historical stabilization sources/runners and all prior milestones
remain protected.

One proposed next evidence milestone is a separately authorized, synthetic-only
mapping/context/journal/exit-adapter design and independent semantic feasibility
proof resolving these six gaps. It is not started or admitted by this contract.
No M2bl, CPU execution, Rust change, placement, firmware, GUI or hardware action
is authorized by M2bk completion.
