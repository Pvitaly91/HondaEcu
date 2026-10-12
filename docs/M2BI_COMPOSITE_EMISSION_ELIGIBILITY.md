# M2bi — Composite emission eligibility (no emission)

Exact base: `4ef211bf8f7d582d3d71c02083ebbdb336ae019d` (M2bh).
Branch: `codex/p28-word0196-composite-emission-eligibility-m2bi`.
Closed scope: `word0196SoftwareAlternate18PlusTwoDirectJ`.

## Evidence levels and authority

A: preserved M2av bounded host C11/source equivalence. B: preserved M2bb
15-form and M2bg one-form single-instruction encoding evidence. C: preserved
M2bd/M2be/M2bf/M2bh typed, CFG, layout and continuation obligations. D: this
static eligibility review. E: actual composite emission **NotRun**. F: actual
target execution/integration **NotEstablished**. Compatibility is not CPU proof.

The decision is `SyntheticCompositeEmissionEligibleForSeparateMilestone` only
when every checked property closes. It authorizes neither emission in M2bi nor
ECU execution. `FirmwareReady=false`; no safe PROGRAM mapping, free ROM,
physical placement, native handoff or downstream rejoin is inferred.

## Pure preflight API and immutable inputs

`prepare_composite_emission_plan(original_ir, composition_contract,
eligibility_contract, request)` returns only JSON-compatible mathematical
identities, typed constructor descriptors and obligations. `EligibilityError`
has only `code` and `location`, with no partial plan. The third model argument
allows actual recipe/policy mutation tests; it does not grant permissions.

The request has exactly `syntheticBase`, `gap`, `initialDD`, `nodeAssignments`
and `classification=InventedOnlyCompositeEmissionEligibility`. Initial domains
are `[0]`, `[1]` or `[0,1]`. Assignments may be omitted or explicitly supplied
as the same canonical node/PC mapping; list order is not instruction order.

Immutable upstream file hashes cover the IR, typed lowering, layout,
continuation, direct-J and static-composition contracts, old codec sources and
independent primary fixtures. The validator recomputes public-source identities;
private primary receipt hashes are identities, not CI claims of access to PDFs.
The unchanged pure M2bh evaluator computes inherited semantic/geometry checks;
the new independent oracle may reuse only the unchanged old mathematical
oracle for inherited expectations, with its own literal novel typed projection.
No new planner, codec output, ASM662, DASM662, `66207.op` or Rust decoding is an
independent expected-byte source.

## Closed 20-node typed mapping

All PCs/values below use documentary hexadecimal notation. They are not an
encoded program listing. Synthetic origins differ from OEM logical identities.
`A` has zero constructor slots; fixed r0/r1 use their exact public types.

| Logical node | Synthetic origin | Exact form | Planned operand types/values | Length | Route |
|---|---:|---|---|---:|---|
| 556F | 1000 | lb-a-page | A, PageOffset8(8E) | 2 | A |
| 5571 | 1002 | sllb-a | A | 1 | A |
| 5572 | 1003 | rolb-page | PageOffset8(8E) | 3 | A |
| 5575 | 1006 | lb-a-r0 | A, Register0(0) | 1 | A |
| 5576 | 1007 | andb-a-page | A, PageOffset8(8E) | 2 | A |
| 5578 | 1009 | cmp-page-imm16 | EvenPageOffset8(96), Immediate16(00C0) | 5 | A |
| 557D | 100E | jlt-rel8 | TargetPC16(102A), logical Below55BF | 2 | A |
| 557F | 1010 | movb-r1-page | Register1(1), PageOffset8(17) | 3 | A |
| 5582 | 1013 | andb-page-a | PageOffset8(17), A | 3 | A |
| 5585 | 1016 | jbs-page-bit7 | PageBit7(offset2A,bit7), TargetPC16(1023) | 3 | A |
| 5588 | 1019 | jbs-page-bit5 | PageBit5(offset24,bit5), TargetPC16(1023) | 3 | A |
| 558B | 101C | andb-page-a | PageOffset8(8F), A | 3 | A |
| 558E | 101F | orb-page-imm8 | PageOffset8(2A), Immediate8(01) | 4 | A |
| 5592 | 1023 | lb-a-page | A, PageOffset8(8F) | 2 | A |
| 5594 | 1025 | orb-a-imm8 | A, Immediate8(F0) | 2 | A |
| DirectJ_NotBelow | 1027 | j-address | ProgramTarget16(5596) | 3 | B |
| 55BF | 102A | lb-a-imm8 | A, Immediate8(0F) | 2 | A |
| 55C1 | 102C | stb-a-page | A, PageOffset8(17) | 2 | A |
| 55C3 | 102E | stb-a-page | A, PageOffset8(8F) | 2 | A |
| DirectJ_Below | 1030 | j-address | ProgramTarget16(55C5) | 3 | B |

Route A describes future `independent_encoder.encode_instruction` requests:
exact `EncoderRequest(reviewed_form_id,typed_operands,incoming_dd,origin_pc)`,
15 unchanged `FormId` values, exact tuple of exact immutable operand classes.
Route B describes `direct_j_encoder.encode_direct_j` with separate
`DirectJEncodeRequest(target,origin_pc,incoming_dd)` and `ProgramTarget16`.
`j-address` is documentary, not a new M2bb FormId/request field. There is no
fallback, DATA dereference, pointer initialization, stack frame or rel8 restriction.
The two abstract slots have no OEM PC and are not added to original IR.

## Geometry, relocation and DD

Only invented `base1000/gap0` is emission-eligible for a separately authorized
milestone. Components are Common[1000,1010), NotBelow[1010,1027),
J_NotBelow[1027,102A), Below[102A,1030), J_Below[1030,1033).
Original lengths45 plus transfers6 equal planned extent51; no actual emission
length was measured. There is no fill, executable gap, linker or modulo repair.

The actual span/overlap/fallthrough/rel8/anchor checks precede the new allowlist.
DenseFFCD and gap101/FF68 are mathematically valid but policy-ineligible;
FFCE overflows; gap102 yields real JLT delta128 refusal. Collisions with5596/55C5
are refused. Other mathematically valid bases/gaps do not prove free ROM.

JLT at100E has next1010, target102A and signed integer delta26 (not old64).
JBS at1016/1019 have next1019/101C, target1023 and deltas10/7. The plan resolves
the logical target to synthetic `TargetPC16.value` before future constructor
projection. It creates no displacement octet. Absolute targets5596/55C5 remain
fixed external continuation identities, independent of invented J origins.

First LB accepts incomingDD0 or1 and establishes0 when executed; all19 later
nodes require derived incoming0. `[0,1]` produces two separate scalar request
variants at entry, not a list-valued codec DD. Metadata never executes LB or
mutates PSW. These are alternative context variants, never a 21-instruction
program. The evaluator checks must/may flows for all three domains.

## Flags, context and ordered effects

Retain CF dependencies5571→5572 and5578→557D. No inserted CF/ZF/HC/OtherPSW
writer, AH clobber, DD mutation, SCB/LRB rewrite, SSP frame or syntheticSF is
allowed. Below terminal AL0F/CF1/ZF0/DD0; NotBelow finalDATA018F ORF0/CF0/ZF0/DD0.
AH/HC/OtherPSW and retained bank/pointer/stack context remain obligations.

Four paths have11/13/14/16 composed nodes and exactly one external J; ordered
writes remain3/3/3/5. Preserve018E RMW,0117 store/RMW,018F branch effects,
conditional012A bit0 update, localr1 write, same-value fresh ordinals and skipped
stores. Path B must not read0124; gates keep their original order. J adds zero
listed functional DATA reads/RAM/SSP writes in reviewed standard-core Function,
not global ASIC/bus noninterference. Original13-step path has zero native witnesses.

## Future verification and transactional rejection

This is a design requirement, not an implemented composer or verifier of bytes.
Every future instruction must match independently sealed manufacturer exact form,
fixed code columns, operand order, width, little-endian cells, mathematical rel8
and exact length. The generic per-form rules reference primary fixtures; no
20-node expected51-byte payload is serialized here.

A future separate decoder check must use M2bc for the18 original nodes and M2bg
for the two Js, at exact20 boundaries, comparing form, operand classes/values,
scalar DD, origin, conditional and absolute targets, and refusing missing/extra
instructions/trailing octets. Encode/decode agreement is compatibility only.
Ordered reads/writes must be checked separately from byte identity; no invented
native journal or host-seeded owner generation is accepted.

A complete future in-memory result may be published transactionally only after
all preflight, all20 codec results, exact per-form lengths/sum51, independent
primary and decoding checks pass. Any error, including instruction13 failure
after12 tentative instructions, must publish no partial composite result. No
trial partial buffer, padding, branch relaxation, inversion, trampoline, assembler,
labels outside closedCFG, symbols, macro/optimizer/runtime-helper or linker is
implemented by M2bi.

## Refusal categories and test meaning

Pinned source identity and request shape are followed by real unchanged M2bh
semantic/geometry checks, then layout allowlist, closed inventory, route, form,
length, typed shape/kind/range/fixed/value checks, origin/DD/CFG/primary projection
and pinned verification/atomicity/runtime policies. A late closed metadata guard
cannot manufacture a semantic proof. Errors are deterministic and fail closed.
Typed, branch, geometry, DD/context/flags/effect-order and policy-only refusals
are accounted separately; a metadata refusal is not evidence for a branch bug.
The independent oracle is sealed before the new analyzer is authored. Tests are
authored separately from the frozen API/own expectations without reading the
new analyzer or its output; their seal is later, not misreported as preimplementation.

The formal decision matrix requires source identity, closed inventory, complete
typed projection, routes, dense51 length, all20 spans, three relative/two absolute
targets, DD, CFG, flags, ordered effects, no anchor collision, independent future
verification, atomicity and no unexpected dependencies. Any missing property
blocks eligibility. Editable metadata never changes emission/runtime authority.

## Historical and runtime exclusions

Runner0.43.0/protocol1/38 identities, original IR/C11, Rust/Core/CLI/Desktop and
all18 Windows stabilization sources stay unchanged. M2bh composition, M2bg codec,
M2bf continuations, M2be geometry, M2bd lowering, M2bc decoding, M2bb encoding,
M2ba design, M2aw context and M2av host equivalence are retained. M2az rights,
M2ay build, M2ax acquisition remain blocked. M2au/M2at/M2an fixes unchanged.

WDT3C/JGT_C8 unresolved; M2aq CAL2689/RT5C80 NotRun; M2ap SSP/ADC blocked;
M2ao DATA019B frontier unchanged; M2ah STOP before5722; DATA019B.2 owner
NotEstablished; M2t/JGT233A and strictM2i blocked; scheduler/target C ABI/ASIC
identity/PROGRAM mapping/SF-stack-interrupt context/peripheral timing/whole-ROM
integration unresolved. IRQ not injected; timer evolution not modeled.

Always ActualCompositeEmissionNotRun, CompositeMachineCodeNotGenerated,
ActualTargetExecutionNotObserved, NativeExitIsolationNotEstablished,
ActualDownstreamRejoinNotEstablished, PhysicalROMPlacementNotEstablished,
TargetProgramEquivalenceNotEstablished, FirmwareIntegrationNotEstablished.
FirmwareReadyfalse. Assembly/target objects/HEX/FirmwareBIN/ROM patch0;
GUI/hardware/fullbootNotRun; all manufacturer/contributor inquiriesNotSent.

## QA, delivery and next proposal

Observed static result: **M2bi Synthetic Composite Emission Eligibility Established**.
`20NodeTypedEmissionPlanValidated`, `CodecRoutingValidated`,
`SyntheticLayoutValidated`, `StaticBranchAndContextObligationsValidated` and
`IndependentEmissionVerificationPlanEstablished` apply only to this closed scope.
No unresolved typed-request mapping remains; future verification is not performed.

| Fresh local check | Observed result (per run, not cumulative) |
|---|---|
| Independent full static suite | 9 positive requests; 107 distinct negative inputs (50 mandatory +57 controls), 214 deterministic refusal calls; 38 refusal codes; 0 failed/skipped |
| Full projection comparisons | 180 node plans; 183 scalar request variants; 19 independently certified geometry first errors |
| Closed-source validator | 41 upstream/3 new source identities; 9 positive/6 negative static controls; 15 plan calls |
| Independent bounded review | 9 full projections/66 refusals; 75 plan calls, separately accounted |
| Closed metadata leaf audit | 1826 leaf mutants/3652 refusals; metadata-only, not operand/branch proof |
| Rust/Core/CLI/Desktop | 321/2932/959/183 passed; focused historical regressions429 passed |
| Host C11/C# | 398658 invented C11 vectors/81920 C# vectors; 42 unchanged offline historical rows,552 snapshots/170 ordered writes |
| Historical research | 13 unchanged suites PASS; new-fragment codec/stream/CPU/actual-ROM calls0 |

New validator and static suite require actual source-bound receipts, not JSON
success flags. Historical single-instruction codecs run separately unchanged;
their old byte counts never count as new plan emission. Required delivery also
includes all historical research suites, Rust/Core/CLI/Desktop headless, C11/C#,
formatting, diff/privacy, full protected SHA comparison, unchanged stabilization
and old runner binaries, and exact-SHA Ubuntu/Windows/Desktop CI. One additive
research-only CI step leaves the previous14 and Desktop portable checks intact.
Private `private/reports/m2bi/FINAL_REPORT_UK.md` is saved LAST after delivery.

NEXT proposal, **not performed**: separately authorized atomic synthetic-only
51-byte emission with primary per-instruction and independent decode acceptance.
STOP: no M2bj, emission, IR-to-assembly, native trampoline, ROM placement,
FirmwareBIN, WDT/C8/reset/fullboot work, GUI or hardware.
