# M2ay - ASM662 source recovery and safe-build verification

## Result

`M2ay ASM662 Build/Encoding ResearchBlocked`.
First gate: applicable rights for the complete historical source set are not
established. Separately, cached generated heads disagree with current generator
inputs, and unrestricted PRELOAD file access blocks unmodified host execution.
`BuildPreflightBlocked`; source builds0, assembler runs0, synthetic outputs0.
This does not assert that no future lawful/safe route exists.

Exact parent: `e5564b24579a71c6a32ca0f71ee48fb0fd8ef548`.
[M2ax](M2AX_MAC66K_V4_DCL_PROVENANCE.md),
[M2aw](M2AW_NX8_200_TARGET_ABI_CONTRACT.md) and
[M2av](M2AV_WORD0196_STRUCTURED_C_EQUIVALENCE.md) remain intact.
No ECU firmware, original-ROM input, full native fragment, lowering or trampoline.

## Source identity, reconstruction and rights

[VIRUXE/asm662](https://github.com/VIRUXE/asm662/tree/94612d10370eb4ddf97d4f349168298e1a3da8a0)
is pinned to `94612d10370eb4ddf97d4f349168298e1a3da8a0`, root tree
`991770bbfeb8f515df5cc3d986aecfc42a3b2a5b`. Private receipts bind exact history,
tree, text-file inventory, lengths, Git blob SHA1 and SHA256. No Attic binary
is fetched/executed. RCS containers are not directly compilable checkouts.

A bounded head parser is independently tested with invented fixtures and a
separately implemented extractor. It reads unique trunk-head full text, unescapes
`@@` and records metadata/delta dependencies. No embedded source execution,
arbitrary old-revision reconstruction, CVS keyword expansion or standard-co claim.
39 RCS trunk heads are materialized. Text and original notices stay private;
old M2ax blobs unchanged. This count is not a coherent release/build claim.

The included generated heads are not a coherent verified build snapshot:
opcode head1.9 (2006) changes TRB to TBR, while parser/lexer/header heads (2004)
and disassembler op.c retain TRB. A complete generator-input dependency closure
does not verify cached generated code. `CoherentSourceReconstructionBlocked`;
no regeneration is run to conceal this mismatch. Private manifests identify
required files, revisions, missing dependencies and the generation pipeline.

The [original author/project page](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/bin/view/Library/ASM662.html)
states BSD lineage/Andy Sloane attribution and historical PGMFI/SourceForge context.
The mirror's Unlicense is not proof that all historical contributors authorized
relicensing. Modified Doc opcode-table lineage and generated flex/yacc artifacts
require component-specific rights. OriginalSourceLicenseEvidence,
MirrorLicenseClaim, ThirdPartyComponentRights, LocalResearchUseStatus and
RedistributionStatus remain separate. Complete-set licensing is unresolved;
no public third-party reuse, license-header rewrite or local build.

## Static safety and dependencies

Actual lexer -> grammar -> C paths were reviewed. Quoted PRELOAD strings reach
unrestricted `fopen(...,"rb")` without path confinement: a confirmed static
unsafe access path, not an observed execution. PC/output arithmetic and expression
division/shift/overflow checks, diagnostics/exit status, overlaps, branch ranges,
symbols, DD and output I/O are assessed separately in the private defect inventory.
Negative decimal ORG is not accepted just because expression unary-minus exists;
conditional lower-buffer corruption is not mislabeled an executed exploit.

The historical Makefile uses Perl to generate lexer/tokens/instructions,
concatenates lexer/grammar fragments, invokes flex/yacc, compiles C/C++ and links.
Installed trusted MSVC/Perl do not replace absent verified flex/yacc dependencies,
license, coherence or safety gates. Build recipes/tools/compatibility and generated
correspondence are inventoried without blind make/clean or running generators.

Unmodified upstream is retained. A separate mitigation proposal covers checked
bounds/arithmetic/expressions, confined/disabled preload, fatal diagnostics,
atomic output, overlaps, branches/DD and reviewed isolated recipes. It is not an
implemented fork or a build PASS. No executable hash, second-build reproducibility
or runtime/compilation log is invented when no build occurred.

## Independent manufacturer expectations

Complete relevant pages of the [MSM66201 Instruction Manual, September1991](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/Oki_66201_Instruction_Manual.pdf)
were visually reviewed by the main agent, independently of ASM662 tables,
FULL_OPCODES, Rust, DASM and C# oracle. A private ledger was sealed before any
potential assembler run, using separate invented operands, not a native program.

| Form | Primary printed page | Length | DD |
| --- | --- | --- | --- |
| LB A, off N8 | 3-70 | 2 | Either; sets0 |
| SLLB A | 3-144 | 1 | Requires0 |
| ROLB off N8 | 3-120 | 3 | Independent |
| LB A, r0 | 3-70 | 1 | Either; sets0 |
| ANDB A, off N8 | 3-24 | 2 | Requires0 |
| CMP off N8, #N16 | 3-38 | 5 | Independent |
| JLT rel8 | 3-66/67 | 2 | Independent |
| MOVB r1, off N8 | 3-99 | 3 | Independent |
| ANDB off N8, A | 3-25 | 3 | Independent |
| JBS off N8.7, rel8 | 3-65 | 3 | Independent |
| JBS off N8.5, rel8 | 3-65 | 3 | Independent |
| ORB off N'8, #N8 | 3-110 | 4 | Independent |
| ORB A, #N8 | 3-107 | 2 | Requires0 |
| LB A, #N8 | 3-70 | 2 | Either; sets0 |
| STB A, off N8 | 3-155 | 2 | Requires0 |

Each row records exact bytes, operand ordering/width, immediate low/high order,
signed8 branch displacement/origin, length and source-page hashes privately.
15 PrimaryEncodingExpectationEstablished rows are **not**15 generated matches.
Generated exact forms0; unresolved generated mismatches unknown/not evaluated,
not a zero-mismatch success. Neither simple nor broader assembly smoke ran:
preflight was blocked before either test.
NativeExecutionNotObserved. ROLB's printed description typo and JGT/C8 remain distinct.

## Closed policy and invented tests

[Contract](../research/p28-word0196/asm662_source_verification.json),
[validator](../research/p28-word0196/validate_asm662_source.py) and
[tests](../research/p28-word0196/asm662_source_tests.py) are new own-code only.
The reviewed profile separates provenance, license, RCS, integrity, dependencies,
safety, build, synthetic verification, primary expectations, actual runtime and
firmware. Changing JSON claims cannot grant execution or authenticate artifacts.
Future actual evidence requires a new reviewed policy, not flipping statuses.

Separate InventedPolicyModel tests cover gate algebra, bounded writes/overlaps,
checked expressions and hypothetical synthetic receipts. Even complete models
return no execution/build/runtime proof. Diagnostics with exit0, wrong bytes,
unused bytes, lengths, DD, dependent expectations, unsafe/preload accesses and
forged operational statuses fail. These models do not execute or patch upstream.

```text
python -B research/p28-word0196/validate_asm662_source.py
python -B research/p28-word0196/asm662_source_tests.py
```

CI adds only own static/model tests: no third-party download/execution. Existing
M2ax/M2aw/M2av C11/C# steps and Rust/Core/CLI/Desktop/format/privacy remain.
Private historical replay is offline, not a new ROM execution. Delivery receipts
bind actual counts, protected hashes,18 stabilization sources,12 old runners and
the exact pushed SHA's Ubuntu/Windows/Desktop jobs.

## Preservation and STOP

Runner0.43.0/protocol1/38 identities,17 original research files, production
executor/decoder/admission/Cpu/Bus/scenarios/oracle and all old private evidence
are unchanged. MAC66K acquisition blocked; C ABI not established; target code
generation NotReady. WDT3C/JGT C8 unresolved; CAL2689/RT5C80NotRun;
reset/fullboot blocked; DATA019B.2 ownerNotEstablished; M2ah STOPbefore5722;
schedulerNotEstablished; IRQNotInjected; TimerEvolutionNotModeled;
physical fuel/time/degrees unavailable; PcInspectionOnly/NotFlashReady.
GUI/hardwareNotRun; Actual-ROM0; SyntheticAssemblerOutput0; productionobjects/BIN0.
No inquiries or ECU action. Unrelated user PNG is not touched/staged.

One next evidence-driven step, **not performed**: obtain component-specific
original rights/provenance for the historical source set, including Doc's opcode
contribution and generated-code terms, before a separately reviewed security
mitigation/isolated-build proposal. STOP: no M2az, lowering, ROM reassembly,
linking/firmware, ECU runtime integration, WDT/C8/reset/fullboot, GUI or hardware.
