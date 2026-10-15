# M2bl - independent synthetic adapter design and feasibility

Exact base: `c52dccad5416e87be07b775998e29ebb7daed13b` (M2bk).
Branch: `codex/p28-word0196-synthetic-adapter-feasibility-m2bl`.

This milestone specifies and checks research-only mathematical adapter relations.
It does not implement a Rust adapter, interpret opcodes, execute the M2bj stream,
load original ROM, generate a target executable, or change production admission.
`RustAdapterNotImplemented` and `ActualSyntheticExecutionBlocked` remain.

## Evidence levels and immutable upstream contract

Only `ExistingRustSourceCapability`, `ManufacturerArchitectureFact` and
`IndependentSyntheticAdapterModel` are available here. The later levels
`FutureRustAdapterImplementation`, `FutureSyntheticCPUExecution` and
`ActualECUExecution` are NotRun. Python PASS or JSON success fields cannot promote
any later level or grant execution permission.

M2bk remains byte-identical: PROGRAM `[1000,1033)`, entry1000, length51,
18 original logical sites plus two abstract direct-J slots,20 boundaries,
DD0/DD1,LRB0021/page0100/local0108..010F, four paths11/13/14/16,
ordered writes3/3/3/5, one J per path and anchors5596/55C5. All documentary
addresses in this document are hexadecimal unless an explicit decimal count.

M2bj's verified in-memory identity remains
`91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1`.
The models never receive its executable bytes. Unchanged emitter regressions
are a separate in-memory encoding check, never an executor input.

## A. Checked PROGRAM segment mapping

`SyntheticProgramSegment` has basePc16,endExclusive,exactLength,sourceIdentity,
immutableContentDigest,programAddressingMode and externalAnchorExclusion, plus
closed model-only provenance and opaque-cell fields. The only admitted identity
is base1000/end1033/length51, with last valid byte1032. Address translation is
integer `requestedPc-basePc16`, only after `base<=requestedPc<endExclusive`.
Extent arithmetic is checked without wrap before narrowing to a PC16.

There is no modulo repair,4096-byte prefix, relocation to0000, DATA indexing,
overlapping segment or arbitrary ROM input. The51 control identities are opaque
strings, not bytes or an encoded program. The SHA field pins the upstream result;
it is explicitly NOT a measured digest of these invented opaque strings.

Mapping tests cover all51 offsets, claimed-offset subtraction, end/last-byte
boundaries, underflow/overflow, source/digest mismatch, overlap and fake padding.
Neither5596 nor55C5 may be fetched. Model success is
`SyntheticSegmentAddressTranslationModelVerified`; runtime mapping remains
`RustSegmentMappingNotImplemented`.

## B. Exact20-position,16-form admission

`ClosedSynthetic20NodeAdmissionPolicy` binds each syntheticPC, logical/AbstractJ
node identity, exact manufacturer FormId, length, typed operands, DD domain,
successors/targets, primary pattern evidence and M2bj source/digest identity.
The contract contains all20 positions. Primary pattern components are symbolic
manufacturer code-column roles, never instantiated into instruction bytes.

The public nodes are upstream metadata, not request objects. Their explicit
projection maps nodeId to nodeIdentity, documentedIncomingDD to architecturalDd,
plannedIncomingDD to reachableDd, and primaryEvidence to primaryPatternEvidence.
Nested typed-operand fields are flattened (PageBit offset becomes value, bit
retained); symbolic manufacturer-column aliases are specified in the contract.
The canonical segment mode is exactly SubtractBase_NoModulo_NoPadding.

The15 original forms and two occurrences of the16th direct-J form are closed.
Architectural DD restrictions are distinct from reachable DD: only the first LB
receives either incoming DD; every later planned node receives DD0. Familiar
mnemonics, generic SupportedOperation, J-object, SJ, CAL, RT, extra/missing nodes
or a valid form at the wrong position cannot authorize a step.

Unchanged Rust decoder/exec source contains all16 forms. Generic synthetic
admission still lacks sllb-a,rolb-page,andb-a-page,andb-page-a,orb-a-imm8,
orb-page-imm8,j-address. The original word0196 route remains at556F with15 forms
and no new direct J. Neither existing route is widened.

## C. Complete typed entry and retained context

`SyntheticCpuEntrySnapshot` supplies PC,A16/AL/AH aliases,incomingPSW16,
CF/ZF/HC/DD,OtherPSW,LRB,SCB,SSP,all8 pointing banks,localDATA/r/er aliases,
halted state,unknownSF and invented provenance. All banks explicitly contain
X1/X2/DP/USP u16 values, including unselected banks. No Cpu::new default is an
independent expected seed. Entry PC1000,LRB0021,SCB=incomingPSW&7.

AL+256*AH must equal A; each er pair aliases consecutive little-endian local
bytes. DATA0109 is r1 and er0's high byte, not an independent host variable.
AH,HC,OtherPSW,LRB,SCB,SSP,all8banks,halted and opaqueSF are retained. r0/r2..r7
are retained; r1 may change only through the separate reviewed DATA obligation.
SF meaning/storage/width/value remain unknown/null, never false by default.

The snapshot model checks representation and context retention, not an opcode's
AL/CF/ZF/DD transformation or the terminal CFG. A coherent after-PC may be any
u16 in this area; the separate fetch/exit model validates terminal/path claims.
Future implementation must join these areas with the unchanged M2bk functional
reference on one input/trace, not mistake separate area checks for CPU proof.
Any concrete SF bridge still needs an explicit representational decision and
proof that admitted forms neither consult nor alter the unknown native state.
No compiler ABI, stack frame or scheduler is inferred.

## D. Independent DATA read/write policy and aliases

The controlled16 bytes remain0108..010F,0117,0124,0128,012A,018E,018F,0196/0197.
Per-path readPermissions and writePermissions are independently supplied and
compared against reviewed M2bk sets. Neither permission implies the other.
SeedInitializationAccess and DiagnosticSnapshotRead are outside the functional
journal. ExecutedFunctionalDATAAccess exists here only as an invented expected
claim, not an actual observation.

The model validates exact ordered access topology, logical width, old/read/new
values against earlier claimed stores, fresh write ordinals, same-value writes,
RMW ordering and final RAM/alias coherence. It intentionally does not calculate
ROL/CMP/AND or other instruction arithmetic. The reviewed path is an obligation
label, not a branch inferred by executing invented RAM.

DATA0196 is an even readonly LE16 word: raw low0196 then high0197, exact weighted
value, no reversed constituents or extra writer. Immediate00C0 is never a DATA
read. DATA0124 is unread on B and readable on C/D after first-gate suppression;
DATA012A writes only on D. Localr1 copies initial0117 on B/C/D, altering er0's
high byte while retaining r0. Same-value018E stores remain fresh writes.
Expected path writes remain3/3/3/5; logical reads5/9/10/12.

## E. Ordered raw probes, selected extents and external trap

The future trace distinguishes instruction entry, selected length/architectural
PROGRAM extent, every raw byte-fetch/probe, decoder lookahead, decoded identity,
nextPC, branch decision, external transfer and read purpose. Current Rust
program_reads observes PROGRAM-as-DATA, not a complete instruction-fetch journal.

Invented per-step raw reads must exactly flatten to a separately supplied global
rawProgramObservationLedger. ArchitecturalSelectedFetch must cover the selected
extent exactly. DecoderLookahead and DiagnosticProgramProbe remain explicit,
ordered and inside the segment, without increasing the retired-instruction
count. Neither duplicate probes nor extra reads may be silently deduplicated.
The model cannot prove the completeness of a future physical observer: its
unbypassable acquisition/interception is a separate Rust implementation proof.
An out-of-segment attempted probe must fail, not return an invented zero byte.

`StopAfterOneDirectJBeforeExternalFetch` requires entry1000, a complete reviewed
path, exactly one direct J, architectural nextPC5596/55C5 and the corresponding
exit identity, then zero next/probe/target reads. Counts are exactly11/13/14/16,
maximum16. Entry at an anchor, fake stop before J, wrong branch, secondJ,
return/trampoline, hidden stack return and any anchor stub/fetch are refused.
All records remain InventedAbstractTransitionRecords_NotCPUTrace.
`ExternalExitTrapContractStaticallyVerified` is not runtime exit isolation.

## F. PSW representation: two explicit routes

The preserved MSM66201/66207 hardware manual printed30/31, section3.2.2(1),
Figure3-5 explicitly says nonexistent bits3,6,7,10,11 read one. The exact
CRC-PASS member page_30.jpg has SHA256
`cc0376abbea029239224d015bd63d509540778addf0f23ffd1265f23bd9d1fbd`.
The incomplete archive has known failures in other members; those do not confer
authority on unread pages and are not hidden. This particular member was freshly
CRC/SHA checked and the complete spread visually reviewed. Standard-device
documentation is not proof of the exact ECU customer ASIC identity.

Writable OtherPSW bits9,8,5,4,2,1,0 yield STORAGE0337; the five reads-one bits
yield0CC8. Named flagsCF/ZF/HC/DD occupy15/14/13/12 and are kept separate.
Independent EncodeCpuPswState/DecodeCpuPswState/CheckPswRoundTrip mathematics:

`roundTripLow12=(OtherPSW & 0337) | 0CC8`

Lossless iff `(OtherPSW & 0CC8)==0CC8`:128 representable and3968 incompatible
values out of4096. All16 named-flag combinations give65536 full words:
2048 representable,63488 incompatible. Full returned records, not just counts,
are compared with the separately sealed oracle.

Route A admits only the explicitly manufacturer/source-representable standard
domain and refuses incompatible inputs before runtime state mutation. Applying
that restriction to the approved M2bk oracle requires a separate scope decision;
M2bl does not choose it or narrow that oracle.

Route B preserves every invented low12 input in a separate lossless research
snapshot. It does not make every such value representable by canonical Rust PSW
or physical hardware. No hidden normalization, expected-state replacement or
change to production masks is allowed. Thus PswRepresentableDomainEstablished
and FullInventedPswDomainRuntimeCompatibilityNotEstablished both remain true.

## Rust integration design and six-capability readiness

Public Cpu/decoder/operand primitives are available, but exec::step and Exec
use the concrete production Bus. Private ROM storage uses absolute zero-based
indexes; step also compares absolutePC with rom_len. Observer lifecycle helpers
are crate-private. A newtype Bus wrapper or constructor alone cannot solve these
barriers, and wrapping old output cannot reconstruct omitted raw observations.

| Capability | Existing Rust | Independent model | Actual adapter implementation | Blocker |
| --- | --- | --- | --- | --- |
| PROGRAM mapping | Absolute zero-based ROM Vec | Checked base subtraction/opaque cells | NotRun | Needs separate research segment Bus/exec integration |
| 16-form admission | Forms present; seven missing generic admissions | Closed20 positions/typed primary bindings | NotRun | No isolated exact-node runtime route |
| Entry snapshot | Partial seeding/concrete defaults | Complete8bank/alias/unknown context contract | NotRun | Complete coherent seed/snapshot and SF bridge unproved |
| DATA R/W policy | Shared ranges; conditional logical journals | Separate path R/W and ordered effects | NotRun | Independent enforcement/raw journal needed |
| Fetch journal/exit trap | Unordered extent union; pre-decode exit primitive | Complete raw/selected ledger and one-J trap | NotRun | Must intercept all probes/accesses and reject zero-step exits |
| PSW round-trip | STORAGE0337/READS_ONE0CC8 | Exhaustive representable-domain/RouteB model | NotRun | Separate domain decision; full invented domain not runtime-compatible |

Minimal future research-only APIs include validate_segment/read_program_checked,
admit_exact_synthetic_node,validate_closed_entry/seed_exact_entry_unobserved,
snapshot_complete_unobserved,independent read_data_checked/write_data_checked,
phase-bounded raw/logical observers and check_expected_external_exit_before_fetch.
These are design signatures, not implemented functions or a production allowlist.

A separately authorized research Bus plus execution integration can be designed
without editing production source. Reusing unchanged modules via a separate
crate with an API-compatible research Bus is only a future integration option,
not compiled proof. Reimplementing the16 effects likewise needs independent
primary/reference regression proof. Generalizing production traits/hooks would
require separate authorization. No route is implemented or selected here.

## Independent oracle, tests, source boundaries and CI

The independent oracle, API, literal examples and expectation digests were sealed
before the analyzer or tests existed. It imports no analyzer, executor, codec or
emitter and derives no expected state from Rust output. The analyzer is authored
separately against the frozen JSON interface. Tests are sealed before their first
analyzer comparison and compare complete results plus explicit primary relations.

The public gate is:

`python -B research/p28-word0196/validate_synthetic_adapter_feasibility_contract.py`

The fixed-path validator pins its own contract before consuming153 immutable
upstream source bindings, pins the new modules before import, checks unchanged
Rust capability anchors and exact M2bk/M2bi node projections, then actually runs
the oracle and mathematical tests. Editable verified flags are not proof.
Source-policy attack fixtures are parsed only, never executed. AST guards are
defense in depth for trusted hash-bound reviewed source, not a Python sandbox.

Coverage includes all51 mappings,20 nodes/16 forms, both DDs/all8SCB/all banks,
separate R/W/LE16/aliases/same-value/path suppression, every reviewed abstract
path, selected versus lookahead/complete raw ledger, external trap and all65536
PSW combinations. Meaningful input/effect/CFG relations are counted separately
from source/digest identity refusals and authority-only metadata refusals.

One additive research-only Ubuntu/Windows CI step leaves all old steps and the
Desktop contract unchanged. Full Rust321/Core2947/CLI959/Desktop183, M2av C11
398658/C-CSharp81920, old research/M2bk protocol/M2bj actual encoding, formatting,
privacy, protectedSHA and exact pushed-SHA CI are independent delivery gates.
The M2bj Option B policy is not extended. Existing30s/56 STA assertions remain.
Actual receipts/counts, first failures if any, source identities and exact CI
run/attempt/job results belong in the private final report, written last.

## Verdict boundary and proposed next milestone

Only passing independent mathematical/static gates establishes
`M2bl Synthetic Adapter Design and Feasibility Established`, with verified
translation/admission/DATA/fetch-trap models, complete snapshot obligations and
PSW representable-domain classification. It does not establish
AllSixRustCapabilitiesImplemented. Actual adapter implementation remains NotRun;
all six current Rust gaps remain blockers for a future experiment.

Unchanged: ActualSyntheticCompositeExecutionNotRun,TargetCPUExecutionNotObserved,
NativeExitIsolationNotEstablished,ActualDownstreamRejoinNotEstablished,
PhysicalROMPlacementNotEstablished,TargetProgramEquivalenceNotEstablished,
FirmwareIntegrationNotEstablished,FirmwareReady=false. New composite CPU/actualROM
executions,target objects/HEX/FirmwareBIN,persistent executable payloads are zero.

Preserved runner0.43.0/protocol1/38 identities,18 stabilization sources, historical
runners and all upstream milestones are unchanged. WDT3C,JGT C8,CAL2689/RT5C80,
SSP/ADC,DATA019B.2 owner,scheduler,IRQ,timer evolution,SF,target compiler ABI,ASIC,
ROM placement,native handoff,downstream and whole-ROM integration remain unresolved.

One proposed next milestone, NOT started: separately authorize a research-only
Rust adapter implementation/build and isolated capability tests for these exact
APIs, with an explicit PSW/SF representation decision and without executing the
51-byte composite. Actual composite execution requires separate later approval.
STOP after M2bl final report: no M2bm, CPU/ROM execution, native handoff, linker,
firmware, GUI or hardware continuation.
