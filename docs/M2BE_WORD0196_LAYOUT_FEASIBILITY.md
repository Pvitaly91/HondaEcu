# M2be - invented-only layout geometry and branch feasibility

Result: **M2be Synthetic Layout/Branch Feasibility Established**, for the closed
invented integer domain only. InstructionSpanGeometryVerified,
SyntheticInternalBranchReachVerified and StaticContextPreservationObligationsVerified
remain distinct from **NativeExitIsolationNotEstablished**,
PhysicalROMPlacementNotEstablished, TargetProgramEquivalenceNotEstablished and
FirmwareIntegrationNotEstablished. Every accepted layout is execution-blocked.
No executable program, assembled stream, instruction bytes or firmware exists.

Exact base: `c83ebf31c118e6af552d9029d305a9b37bcce0f4` (M2bd).
Branch: `codex/p28-word0196-layout-feasibility-m2be`.
All previous IR/C11/C#/M2aw/M2ba/M2bb/M2bc/M2bd components, production ISA/admission
and Windows stabilization remain byte-identical. Runner0.43.0/protocol1/38 identities.

## Inherited evidence and independently recomputed geometry

LogicalSiteId is a historical reviewed PC identity, NOT a new placement address.
SyntheticAssignedPC is a separate invented mathematical integer. Even when
numbers coincide in the original-shaped reference, no physical ROM claim follows.
M2bd contract SHA256:
`6f62c23e99f72e7df51a0117b7c5ff600d892f2a8d3e4c4231a383e1d96c6bf4`.
M2av IR SHA256:
`4fdbd6b7dbdd8f48d5a43e123ca93a33a003c22556a0c40b5296d5f409e085c4`.

Own mathematical model and separately authored literal-position oracle use the
same established18 sites/15 forms, not ASM662/Doc tables, encoder output, Rust
FULL_OPCODES or CPU execution. Static inherited obligations are reused, not
reinterpreted as target runtime proof. No new manufacturer semantic correction.

| Logical block | Original half-open interval (hex) | Sites | Sum of lengths |
|---|---|---:|---:|
|Common|556F..557F|7|16|
|NotBelow|557F..5596|8|23|
|Below|55BF..55C5|3|6|

18 unique sites;16+23+6=45 instruction-length bytes. Outer envelope55C5-556F=86;
excluded region55BF-5596=41. **5596..55BF is unmodeled, NOT padding, NOPs, free
ROM or overwrite permission.** It is not read/copied/filled.45 is not firmware size
or a runnable45-byte program. Per-site exact lengths/forms remain immutable.

## Closed mathematical API and input profile

`layout_feasibility_analysis.py` supplies pure:

```text
evaluate_layout(upstream_m2bd_contract, request) -> static records | LayoutError
instruction_span(start, length) -> interval arithmetic | LayoutError
branch_geometry(start, length, target) -> signed integer arithmetic | LayoutError
```

Request has only syntheticBase, blockOrder, gaps, optional siteAssignments and
classification=InventedOnlySymbolicLayout. Gaps are two exact nonnegative integers,
with no arbitrary candidate cap; large gaps reach actual span bounds. No fill,
hole behavior, target permission, label, symbol or opcode fields are accepted.

This narrow entry/base profile requires Common as the first block, explicitly a
profile restriction, not an ISA theorem. Both permutations of remaining blocks
are syntactically valid candidates; Common->Below->NotBelow reaches a **real JLT
false-edge adjacency failure**, not a generic metadata-only order rejection.
Below->Common->NotBelow is refused by the separately stated Common-first policy;
mathematical internal feasibility alone would not prove its terminal safety.

Optional full18-site assignments are checked for identity/uniqueness, spans,
overlap, real fallthrough and branch distances BEFORE block-plan consistency.
They cannot silently alter semantic ordering or introduce hidden instructions.
Invented negative-distance controls are separately classified: passing scalar
arithmetic is not permission to rearrange the18-site program.

## Instruction spans, NoWrap and analytical markers

Every span is [assignedPC, assignedPC+exactLength). Start must be exact int0..FFFF;
endExclusive<=10000; no split, overlap, missing/duplicate identity or modulo wrap.
Bool, floats, numeric strings and implicit casts are not addresses/lengths.
Nonbranch last byteFFFF is permitted. A terminal **end-exclusive marker10000**
is also permitted analytically, but is NOT an instruction PC16, native continuation
address, STOP opcode, RT/HALT/BRK or C return. No marker is inserted into code.

Relative branches additionally require nextPC<=FFFF and target0..FFFF. Branch at
FFFE/length2/targetFFFF has signed-1 but is still refused for nextPC10000. Span
overflow, invalid target and signed-range overflow remain separate constraints.
No delta&FF, displacement-byte construction, encoder call or wrap repair.

## Full CFG and fallthrough equations

Immutable21 edges:16 internal Fallthrough,3 ConditionalTaken,2 AnalyticalTerminal.
For all16 fallthrough edges: assignedSuccessor=assignedStart+exactLength, including
557D false->557F,5585 false->5588,5588 false->558B and join5592->5594.
These preserve the original short-circuit gates, predicates and within-block order.
No added/removed/inverted branch, folding, code duplication/merging, cycle or
undefined successor. A requested hidden JMP/RT/trampoline is unsupported future
scope, not an automatic repair. Analytical terminal edges check extent boundaries,
NOT an implemented transfer mechanism.

| Relative branch | Original reference distance | Canonical invented distance |
|---|---:|---:|
|JLT557D->55BF|+64|23+gap|
|JBS5585->5592|+10|+10|
|JBS5588->5592|+7|+7|

Arithmetic uses mathematical integers. Signed range-128..127 is checked directly;
reference distances do not establish new placement. Absolute base cancels from
relative differences; only relative positions/gaps and span bounds matter.

## Independent scenarios and native terminal hazard

| Scenario | Geometry / actual constraint | Native integration |
|---|---|---|
|Original-shaped base556F/gap41|deltas64/10/7;45 lengths within86 envelope|Reference only; hole behavior unknown|
|Dense invented base1000/gap0|deltas23/10/7; internal CFG feasible|NotBelow end immediately adjacent Below|
|gap104|JLT+127 accepted|Exit isolation still not established|
|gap105|JLT+128; actual Rel8OutOfRange, stageBranch|Refused; no relaxation|
|Relocated bases0/1000/2345/556F/8000/F000|same gap-dependent distances|No real ROM availability claim|
|NearFFFF densebaseFFD3|last nonbranch byteFFFF, terminal10000 allowed analytically|No executable continuation|
|densebaseFFD4|actual instruction span overflow|Refused, no modulo repair|
|baseFFAA/gap41;FF6B/gap104|last nonbranch byteFFFF with legal internal branches|Still execution-blocked|
|Common->Below->NotBelow|actual557D false-edge FallthroughMismatch|No hidden jump|

The model explicitly inspects both terminal boundaries. At dense NotBelow end,
Below starts at the physically next invented address: PotentialFallthroughIntoSyntheticBlock.
An abstract STOP does not prevent that native fallthrough. With a positive gap,
UnmodeledGapOrOutsideRegion means behavior UNKNOWN, not safe separation. Beyond
Below's last instruction, external continuation is also unimplemented/unknown.

Every marker records logical stop identity, assigned endExclusive, adjacent block,
hazard, required external continuation and nativeExitIsolation=Blocked. No runtime
proof follows from BranchGeometryFeasible/AllInternalCFGEdgesFeasible. Additional
transfer instructions, if needed, require independent scope beyond the15 forms.

## Static context, paths and ordered effects

Code-address geometry does not rebase DATA. Retain LRB0021/page0100/local bank
0108..010F; SCB incomingPSW&7, not fixed2. DATA0117/0124/0128/012A/018E/018F/
0196/0197 and raw page offsets unchanged. Word0196 is evenLE16;00C0 code-owned,
not RAM00C0 read, physical RPM or timer. r1 remains high byte of er0 at0109;
r0 low byte retained, not wholeer0 preservation on not-below.

Initial DD0/1; LB556F establishes0; CF5571->5572 and5578->557D; HC/OtherPSW/AH
retained; terminalCF1below/0not-below,ZF0,DD0. All intermediate flag effects remain
obligations, even value-dead. No adapter/prologue or new flag writer is inserted.
Potential word alias pairs0116/0117,0124/25,0128/29,012A/2B,018E/8F,0196/97 retained.
SSP/stack may alias registers/RAM/SFR; safe frame, SF meaning/storage and C ABI
remain unknown. No CPU emulator or actual native write journal is created.

| Logical path | Instruction count | Ordered writer identities | Writes |
|---|---:|---|---:|
|A below|10|5572,55C1,55C3|3|
|B first gate|12|5572,557F,5582|3|
|C second gate|13|5572,557F,5582|3|
|D both false|15|5572,557F,5582,558B,558E|5|

Widths/addresses/site identities/order/same-value obligations preserved exactly.
DATA0124 is not read on B. Gates retain skipped writes;558E cannot precede558B.
13-step path still lacks a historical native witness. Historical42 observations/
552 snapshots/170 writes are inherited, NOT new ROM runs or a43rd observation.

## Independent expectations, tests and source audit

Oracle uses independently authored literal within-block offsets, positional
equations and quadratic pairwise interval intersection, distinct from the
analyzer's cursor/sorted-span approach. It imports no analyzer/codec/CPU/IO.
Oracle/tests and61 mutation fingerprints/code-stage expectations were sealed
before implementation. Actual absence AnalyzerNotImplemented/calls0/fakeREDfalse;
no fabricated RED. First full suite and validator passed without altering any
sealed mathematical expectation or source.

Actual per-one-suite counts, not accumulated across local/CI repeats:

- 637 successful labels,634 distinct requests,633 assigned geometries.
- 61 unique full-model mutations,122 deterministic same-code/path/stage refusals.
- 1558 standalone branch controls:1540 accepted/18 refused.
- 61 span controls:32 accepted/29 refused,60 distinct inputs.
- 2378 actual public API calls across those distinct domains.
- 11466 instruction rows,13377 edge rows,1274 terminal markers,2548 path rows,
 8918 ordered-write obligations and628 unmodeled-hole records compared.

Negative domains explicitly distinguish actual Branch/Span/Fallthrough geometry
from metadata/context/policy refusals. Wrong metadata alone is never counted as
branch feasibility proof. Tests verify caller immutability and no partial error
output. NearFFFF scalar controls are not additional admitted CFG instructions.

`validate_layout_feasibility_contract.py` pins closed safety fields and14 immutable
upstream file identities, independently computes geometry/edges/reference distances
and exercises actual declared scenarios. JSON cannot promote ExecutableLayoutVerified
or FirmwareReady. CLI accepts no external-file/ROM arguments. Its AST dependency
guard is trusted-source defense-in-depth, NOT an arbitrary-code sandbox; attack
fixtures are parsed only, never executed. Metadata/pure APIs do not emit target code.

```text
python -B research/p28-word0196/validate_layout_feasibility_contract.py
python -B research/p28-word0196/layout_feasibility_tests.py
```

Preparation diagnostics remain explicit: an initial private oracle harness root
index pointed outside repo (FileNotFoundError); only its index was repaired before
analyzer tests. Main PowerShell inspection initially read array.Length counts
instead of projecting per-site lengths; independent exact JSON reduction corrected
that observation. One draft gap cap65535 was removed before implementation so huge
candidate gaps reach genuine span bounds. Original diagnostics/drafts/seals retained;
no primary/model expectations adjusted from analyzer output for PASS.

## QA, preservation, integration blockers and STOP

One additive research-only geometry step is added on Ubuntu/Windows. Existing
ten research steps, Rust/Core/CLI/Desktop/format/privacy and portable tests remain
unchanged. No OEM/ASM download, executable geometry artifact or target output.
Old M2bd/M2bc/M2bb/M2ba/M2aw-M2az regressions and M2av C11/C# host QA remain separate;
their host executables or nonzero single-instruction synthetic codec bytes are NOT
new M2be target artifacts. Private final receipts bind actual QA/counts/exact-SHA CI,
full protected hashes, all18 stabilization sources and18 historical runners.

M2bd obligations/M2bc compatibility/M2bb encoding/M2ba route retained. ASM662 rights/
build and MAC66K acquisition blocked; M2aw context/M2av source equivalence retained;
M2auINT/M2atDEC_HC/M2anSLLB complete. WDT3C/JGT C8 unresolved, CAL2689/RT5C80NotRun,
SSP/ADC blocked;019B frontier/M2ahSTOPbefore5722/019B.2 owner unchanged;M2t/StrictM2i
blocked; scheduler/compiler ABI/firmware integration unknown. IRQNotInjected;
TimerEvolutionNotModeled;PcInspectionOnly/NotFlashReady;physical fuel/time/degrees
unavailable; GUI/hardware/fullbootNotRun; ASM/WDT/C8 inquiriesNotSent.

M2be actual-ROM/ASM662/target byte streams/assembly/object/HEX/BIN/native journals0.
One NEXT proposal, NOT performed: independently specify the two native continuation
obligations and the least additional transfer forms/evidence needed, without coding,
tool execution, placement, source-owner invention or original-ROM replacement.
Separate authorization required. STOP after final report: no M2bf/real lowering/
emission/assembler/linker/ROM replacement/firmware/WDT/C8/reset/fullboot/GUI/hardware.
