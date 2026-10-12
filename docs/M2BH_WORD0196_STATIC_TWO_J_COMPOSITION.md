# M2bh — static composition with two abstract direct-J continuations

Exact base: `bae6a4b12a9839738117bac805a485d38f92d18b` (M2bg).
Branch: `codex/p28-word0196-static-two-j-composition-m2bh`.
Scope: `ReviewedStatic20NodeCompositionSpecification`,
invented-only mathematical/static research. No target instruction stream is produced.

## Separate immutable evidence layers

The new contract pins 36 upstream file identities/SHA-256, including the unchanged
M2av original IR and C11, M2aw context, M2bb 15-form encoder, M2bc decoder,
M2bd typed lowering, M2be layout, M2bf continuations and M2bg direct-J codec.
The original 18 logical PC identities/15 forms/45 length bytes remain unchanged.
The two new string identities are `AbstractTransferSlot`, with
`originalLogicalSiteId=null`: not OEM sites or historical executed instructions.

Manufacturer instruction manual September1991, SHA-256
`f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271`,
physical116/printed3-62 plus263..265/3-210..212 and25..28/1-21..24:
direct J length3, immediate16 PROGRAM target, architectural PC replacement,
both DD selections accepted, no listed flag/DATA/RAM/SSP writer or CAL/RT frame.
PROGRAM operand fetch is not a functional DATA read.
No assertion about customer ASIC/bus/peripheral/global noninterference follows.
The private primary PDF/renders are not public artifacts.
M2bg single-instruction encoding remains a separate immutable result;
none of its codecs is called by the composition analyzer or oracle.

## Abstract geometry

All intervals are half-open, offsets from an invented base B, not ECU placement.

| Component | Nodes | Length | Offsets for gap g |
|---|---:|---:|---|
| Common | 7 original | 16 | [0,16) |
| NotBelow | 8 original | 23 | [16,39) |
| DirectJ_NotBelow | 1 abstract | 3 | [39,42) |
| unmodeled gap | 0 | g | [42,42+g) |
| Below | 3 original | 6 | [42+g,48+g) |
| DirectJ_Below | 1 abstract | 3 | [48+g,51+g) |

45 historical length bytes +6 hypothetical transfer length bytes =51 dense extent;
total extent 51+g. This is not the size of a runnable ECU program: entry handoff,
adapters, sections/linking, physical mapping and runtime integration are absent.
No padding, NOP, executable gap, hidden transfer, splitting or payload is created.

At B=1000, g=0: Common1000..1010, NotBelow1010..1027,
J_NotBelow1027..102A, Below102A..1030, J_Below1030..1033.
JLT557D is at100E, nextPC1010, Below102A: delta+26, not the old historical+64.
Internal JBS5585→5592 remains+10; JBS5588→5592 remains+7.
For g≥0, JLT delta26+g: g0/41/101 gives26/67/127; g102 gives128 and is refused.
Gap is permitted only after J_NotBelow and before Below; there is no arbitrary
gap cap replacing the actual span/rel8 checks. Original excluded41 is not free ROM.

Dense max base FFCD permits J_Below atFFFD with last analytical extent10000.
FFCE is refused. For g101 the maximum base is FF68.
End10000 is an extent, not an executable PC; no modulo wrap or relaxation.
Direct J has no signed8 restriction; the three conditional branches do.

Each assigned node span is independently checked against external identities
5596 and55C5. Actual intersection gives `SyntheticExternalAnchorCollision`.
End-exclusive contact is not intersection. An anchor solely in an unmodeled gap
is `UnknownGapAnchor_NotSafeFreeROM_NotPhysicalPlacement`, not a node collision.
For example B5540/g101 leaves both anchors in the unmodeled gap.
Every accepted scenario remains `PhysicalPlacementNotAuthorized`;
absence of these two collisions is not proof of any usable ROM region.

## Actual symbolic CFG and obligations

Original21 edge relations become23: replace two analytical terminals by
5594→J_NotBelow and55C3→J_Below fallthrough, then append external edges
J_NotBelow→5596 and J_Below→55C5. Derived counts:20 nodes, one entry,
18 fallthrough/3 conditional-taken/2 external edges; DAG and full reachability.

| Path | Original | Abstract J | Composed | Target | Ordered writes |
|---|---:|---:|---:|---|---:|
| A below | 10 | 1 | 11 | 55C5 | 3 |
| B first gate | 12 | 1 | 13 | 5596 | 3 |
| C second gate | 13 | 1 | 14 | 5596 | 3 |
| D both false | 15 | 1 | 16 | 5596 | 5 |

No path crosses NotBelow→Below or Below→NotBelow, no J has an internal
fallthrough, and every complete path traverses exactly one external J.
C retains StaticPrimaryAndInventedCoverage and zero historical native witnesses.
The composed counts do not supersede original M2av counts.

Forward DD must/may checks all three domains [0], [1], [0,1] structurally.
LB556F establishes0; sensitive sites and both abstract Js receive0.
Sixteen scalar flag reaching-writer/liveness obligations include
5571 SLLB→5572 ROL carry and5578 CMP→557D CF; neither new J adds a writer.
Below final AL15/CF1/ZF0/DD0, NotBelow final018F|F0/CF0/ZF0/DD0.
AH/HC/OtherPSW are preserved obligations. All original intermediate writers remain.
No unknown SF is set to0.

Raw IR effects generate ordered read/write obligations, not CPU state or a native
journal. Every write, including same-value RMW/store, retains a fresh *static*
one-based path ordinal. DATA018E RMW occurs on every path; pathB does not read0124;
012A write occurs only onD. r1 remains er0 high byte, r0 stays unchanged; no
additional functional DATA read, RAM/stack writer, local clobber or LRB/SCB rewrite.
DATA0196 provenance is unchanged; physical RPM/timer semantics are not inferred.

## Implementation and independent checks

`static_composition_analysis.py` exposes the pure
`evaluate_composition(original_ir, composition_contract, request)`.
It imports only JSON, accepts exact JSON primitive/container types and returns
static records or atomic `CompositionError(code,path,stage)`, without partial results.
It derives CFG relations, topological DD/flag propagation, backwards liveness,
symbolic effects and actual placement relations before a late closed-metadata check.
Editable success/permission fields are not evidence.

The independent oracle was prepared and sealed before analyzer authoring,
using separate positional literals, recursive DFS and path-enumerated dataflow.
The sealed tests compare the complete result projection, not just status strings.
The first comparison exposed one malformed negative-test placement: its intended
fallthrough violation also created an earlier overlap. Independent mathematical
review confirmed the analyzer's correct overlap refusal. Only that fixture's
Below component was moved by one address to remove the unintended overlap;
the prescribed fallthrough refusal, analyzer and oracle were unchanged by that repair. The
original sealed fixture, failed first outcome and post-seal correction are retained.
Separate review hardened malformed nested-input guards and three AST-policy
holes (input writes, encoded-data slicing and catch/pass), without changing
the composition mathematics or prescribed semantic expectations.
Source-policy AST checks are defense-in-depth for trusted source, not a Python sandbox;
hostile fixtures are parsed, never executed. See private preparation receipts for
actual phase/source hashes, first outcomes and any audited corrections.

Refusals exercise original/transfer inventory, direct-J effects, real CFG/branches,
DD/carry/memory/context/continuations, span/overlap/fallthrough/rel8/anchors and
component-plan equations separately from metadata-only authority promotions.
No skip, catch-and-pass, synthetic CPU execution or codec-derived expectation is used.

## QA and delivery evidence boundary

One research-only validator/test step is added to both existing OS matrix jobs;
all old research steps and Desktop checks remain unchanged.
Existing codec regression suites retain their own authorized single-instruction
synthetic bytes; these are never M2bh composite emission.

Fresh local Rust/Core/CLI/Desktop headless, formatting, C11/C# differential,
historical research, new suite/source-policy, privacy and full protected comparison
are recorded in private M2bh source-bound receipts. The initial sandbox .NET testhost
IPC refusal is retained separately from the corrected-environment run:
unchanged tests, no assertions skipped, no timeout or test-policy relaxation.
Local production/historical QA: Rust321, Core2932, CLI959, Desktop183;
focused429; C11 invented398658 and C# differential81920; offline42 rows,
552 historical per-PC snapshots and170 ordered writes reconciled. All passed with0 skipped.
Final source-bound M2bh validator:18 accepted/16 refusal controls,50 actual calls.
Independent suite:1866 positive calls/1851 unique geometry contexts/1857 unique
request inputs;131 model +26 geometry +612 anchor-collision labels checked twice
(1538 negative calls,757 unique negative inputs).0 failed/0 skipped;21 real refusal
codes observed. BranchNextOutsideProfile remains defensive/unreached, not fake coverage.
Separate malformed/type/depth/cycle review:47 refusal labels twice +1 valid control
(95 calls). Parse-only AST review:60 immutable attack labels twice +2 valid source
controls (122 checks); no hostile fixture execution. Initial failed outcomes retained.
Delivery formatting removed only one final blank LF from each new oracle/test file;
independent raw-prefix/AST equality and fresh source-bound QA confirmed identical
logic, assertions, expected projection hashes and actual validator/suite output.
Full protected SHA-256 comparison:26613 files/39918100301 bytes before and after;
deleted0/added0/changed0. Only the current private M2bh report root is excluded.
All18 stabilization sources and21 historical runner binaries are byte-identical;
the saved-last M2bg report, attestation and144 prior sealed artifacts are retained.
Exact final SHA/CI run/attempt/jobs are recorded only after the normal substantive
commit/push in the private FINAL_REPORT_UK.md; this document cannot self-pin its commit.

## Result boundaries and STOP

The allowed successful static result is
`M2bh Static 18-Site Plus Two-Direct-J Composition Established`,
only after actual source-bound checks. Architectural PC replacement and synthetic
internal CFG isolation do not establish native runtime exit isolation.

CompositeMachineCodeNotGenerated; NativeExitIsolationNotEstablished;
ActualDownstreamRejoinNotEstablished; PhysicalROMPlacementNotEstablished;
TargetProgramEquivalenceNotEstablished; FirmwareIntegrationNotEstablished.

Production runner0.43.0/protocol1/38 fix identities, all stabilization sources and
historical runners remain unchanged. Earlier research/blocked/NotRun boundaries
remain: WDT3C/C8, CAL2689/RT5C80, SSP/ADC, DATA019B/M2ah STOPBefore5722,
native019B.2 owner, StrictM2i/scheduler/IRQ/timer/ABI/ASIC/SF/stack and inquiriesNotSent.
No assembly, target objects/HEX/FirmwareBIN, CPU/ROM, GUI/hardware/fullboot.

One NEXT proposal: a separately authorized invented-only composite-emission
eligibility/evidence review that first resolves entry handoff, primary instruction
mapping, atomic generation rules and proof boundaries. Not started here.
STOP after delivery: no M2bi, actual18+2 emission, IR-to-assembly, linker/ROM placement,
firmware, WDT/C8 fixes, reset/fullboot, GUI or hardware.
