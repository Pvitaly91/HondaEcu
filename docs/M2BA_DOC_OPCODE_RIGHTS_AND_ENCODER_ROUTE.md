# M2ba — Doc opcode rights and independent encoder route

Result: **M2ba Independent Encoder Route Specified / Historical ASM662 Blocked**.
Exact base: `5c819e0f5675850050c5bc3a8e6301a66d448136` (M2az).
Branch: `codex/p28-doc-opcode-rights-encoder-route-m2ba`.
This is documentary provenance plus a primary-manual specification, not an
encoder, source license grant, assembler/compiler or FirmwareReady result.

## Newly reviewed author source

The independently acquired [a1k0n/asm662 repository](https://github.com/a1k0n/asm662)
is distinct from VIRUXE's mirror. Its GitHub profile names Andy Sloane, links his
author site, and the archived [PGMFI Andy profile](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/bin/view/Home/AndySloane.html)
identifies the same alias/domain and assembler project. Source documentation
and imported commit attribution agree. This is documentary project attribution,
not authenticated legal-person identification or authority over Doc's work.
GitHub creation is `2015-06-10T15:32:37Z`; imported 2003/2006 CVS dates are NOT
GitHub publication dates. Private receipts retain URLs, retrieval time, exact
content sizes/hashes, full trees, notices, relevant patches and bounded history.

The original SourceForge 0.9 archive is unchanged, SHA-256
`2471660d08fe827af9ed1582354804eb7c16e82775bb8b6e5190317a253e5444`.
The following correspondence is file-by-file, not filename/date inference:

| Author commit | Original non-CVS files compared | Identical / changed | Git-only files | Meaning |
|---|---:|---:|---:|---|
| `6143051a30b1c35f55c92a2c83bbd5e247a464cc` initial | 36 | 35 / 1 | 7 | Closest reviewed source state; not a byte-identical whole release tree |
| `8901c411dcd54ff2f56d533f59af976cdffd8a08` Doc report | 36 | 19 / 17 | 0 | Later modified source, not original0.9 |
| `ff1f58e673c3de52473402fc7d4b03c83ddded94` TRB to TBR | 36 | 14 / 22 | 14 | Still later table/generated/dependency state |

Original CVS metadata is separately retained (12 archive files); it is not
counted as Git source equality. Initial scanner difference is an expanded RCS
revision string, not a new generated-source coherence proof. Subsequent Doc bug
feedback, table fixes and later contributors are retained as distinct layers.
No later source or generated file is silently mixed into the original release.

## Doc and component rights

Original DASM documentation identifies the original filename **66207.op** and
attributes the table to Doc's disassembler. Original disassembler distribution,
specific original revision, publication date, legal owner and positive license
or permission were NOT established. The modified ASM662 table is available;
that is not recovery of the original Doc package. Bounded searches covered the
author Git history, original0.9 notices, exact PGMFI resources/posts/attachments
and targeted SourceForge paths. Redirected index pages, unavailable forum pages
and a whole-project CVS snapshot not acquired are recorded as limits, not grants.
Doc's opcode alias is not equated with ROM-reader hardware authorship or the
separately documented Pelegri Didier 66507 disassembler.

| Component | Attribution / claim | Verified scope | Remaining issue |
|---|---|---|---|
| Andy's own ASM662 source | Andy Sloane; historical BSD statement | Project/own-code statement and documentary author connection | Exact BSD variant/component scope; no inferred third-party permission |
| Original Doc 66207.op | Doc alias; unknown license | Original filename and attribution | Original package, copyright, owner and permission |
| Modified table | Doc plus Andy/later layers | Exact revisions and changes | Underlying grant and combined-work scope |
| Original Bison 1.75 output | FSF skeleton; explicit generated-output exception | Exact archived header/exception retained | Notice retention; exception does not license user grammar/table |
| Historical Flex/byacc output | Version-specific notices | Original Flex banner/family notices; later byacc separately reviewed | Exact modified skeleton correspondence; no tool-family blanket inference |
| VIRUXE modifications | Separate history; Unlicense claim | Claim observed | Relicensing authority over historical contributors not established |

`OriginalProjectBSDStatementVerified` does not mean `AllComponentsRightsVerified`.
`DocContributionRightsNotEstablished` remains the first rights prerequisite.
No complete historical snapshot is accepted for local build or redistribution
under the project's evidence contract. This is absence of a positive verified
basis, **not proof that every lawful use is prohibited** or comprehensive legal
advice. A private inquiry is `InquiryDraftReady / NotSent`; no contact was made.

## PrimaryManualDerivedIndependentEncoderRoute

Recommended route B uses manufacturer functional facts and the sealed,
independently reviewed M2ay primary expectations. The main agent reviewed full
manufacturer pages again for M2ba. Manual: *MSM66201/66207 Instruction Manual*,
September 1991, `Oki_66201_Instruction_Manual.pdf`, SHA-256
`f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271`.
M2ay expectation ledger SHA-256:
`a268815a0c04a4e2f0fccb64021ead26e1cbdaa02c1cc435d816f7d35fa2ab44`.
No ASM662 source, grammar, generator, derived table arrangement, Rust decoder
output or C# executor output is an implementation input. Prior exposure to
third-party source is disclosed; **no legal clean-room claim** is made.

Conceptual ONLY:

```text
EncodeInstruction(reviewedFormId, typedOperands, incomingDD, originPC)
    -> EncodedInstruction | ExplicitError
```

The public contract supplies typed operands, exact references/components,
DD restrictions, length, invented examples and negative cases for every form.
These are static expected examples, **not generated target output**:

| Exact form | PDF / printed page | Length | DD | Components / invented static expected bytes |
|---|---|---:|---|---|
| LB A,off N8 | 124 / 3-70 | 2 | Either; executed LB sets 0 | F4,offset8 / F4 37 |
| SLLB A | 197 / 3-144 | 1 | 0 required | 53 |
| ROLB off N8 | 173 / 3-120 | 3 | Independent | C4,offset8,B7 / C4 37 B7 |
| LB A,r0 | 124 / 3-70 | 1 | Either; executed LB sets 0 | 78 |
| ANDB A,off N8 | 76 / 3-24 | 2 | 0 required | D7,offset8 / D7 37 |
| CMP off N8,#N16 | 90 / 3-38 | 5 | Independent | B4,offset8,C0,low,high / B4 36 C0 5A A5 |
| JLT rel8 | 120-121 / 3-66-67 | 2 | Independent | CA,delta / CA 07 (0100 to 0109) |
| MOVB r1,off N8 | 153 / 3-99 | 3 | Independent | C4,offset8,49 / C4 37 49 |
| ANDB off N8,A | 77 / 3-25 | 3 | Independent | C4,offset8,D1 / C4 37 D1 |
| JBS off N8.7,rel8 | 119 / 3-65 | 3 | Independent | EF,offset8,delta / EF 37 F9 (0200 to 01FC) |
| JBS off N8.5,rel8 | 119 / 3-65 | 3 | Independent | ED,offset8,delta / ED 37 07 (0300 to 030A) |
| ORB off N'8,#N8 | 163 / 3-110 | 4 | Independent | C4,offset8,E0,imm8 / C4 37 E0 A6 |
| ORB A,#N8 | 160 / 3-107 | 2 | 0 required | E6,imm8 / E6 A6 |
| LB A,#N8 | 124 / 3-70 | 2 | Either; executed LB sets 0 | 77,imm8 / 77 A6 |
| STB A,off N8 | 208 / 3-155 | 2 | 0 required | D4,offset8 / D4 37 |

All 15 exact primary encodings are specified. ROLB's word-long description typo
is retained explicitly; byte heading/table determine this form. JLT evidence
does not settle the unrelated JGT C8 conflict. Other registers, bits, forms and
ADDer3,A are unsupported and rejected; the prime in ORB N'8 marks a separate
operand variable, not another addressing mode.

Typed integers reject bools, floats, strings, nulls, overflow and implicit casts.
Immediate16 is 0..65535, low byte first (also PDF9/printed1-5). Page operands
are raw 0..255 offsets, not full DATA addresses; no LRB/address mapping is inferred.
CMP accepts even offsets only in this narrow profile. PDF22/printed1-18 states
that CPU word reads align odd addresses down; refusal is **our design restriction**,
not a claim that odd instruction operands are ISA-illegal.

Rel8 is `targetPC - (originPC + instructionLength)`, signed -128..127, using
two's-complement8 only after range validation. Origin and target are typed
0..65535. The conservative NoWrap profile rejects a branch nextPC beyond FFFF
and any instruction span beyond the address space; it does not silently apply
modulo arithmetic or claim universal CPU wrap semantics. No automatic labels,
placement, padding, truncation, default bytes or derived-source fallback exist.
Encoding does not execute LB or mutate DD/context. No preload, file/ROM input,
linker, memory placement, C ABI assumption, native replacement or firmware output.

## Decision and future gate

| Route | New result | Prerequisites before first verified invented output |
|---|---|---|
| Historical ASM662 | Better author/0.9 correspondence; rights still blocked | Positive component rights, coherent generated source, security mitigation, trusted dependencies, reproducible build and primary-vector comparisons |
| Own 15-form encoder | Exact primary specification established; implementation NOT started | Original implementation, independent review and invented-only byte/length/error tests |

Route B is the shortest evidence-backed route to a first verified synthetic
encoding without the unresolved Doc-derived implementation dependency. It is
not a ready general assembler/compiler. One proposed NEXT implementation milestone
is an own typed 15-form instruction encoder plus invented-only primary-vector
tests, explicit error/no-output behavior and boundary/DD/LE16/rel8 coverage.
That milestone requires separate authorization and is **not started here**.
Replacing native PC556F still separately requires flags, CPU context, register
allocation, RAM writes, control flow and actual target-execution equivalence.

## QA and retained boundaries

Own static validators and invented policy tests run on both public CI OSes;
CI downloads no ASM662/proprietary package and creates no target code. Tests
check closed evidence profiles and hypothetical request metadata/errors only.
They do not implement an encoder or prove its future emitted bytes. Full Rust,
Core, CLI, Desktop headless, unchanged M2av C11/IR/C# and M2aw-M2az regressions,
formatting, privacy, full protected hashes, all 18 stabilization sources and all
historical runner binaries are independently audited. Private final QA/CI
receipts and the last-written final report carry actual counts and exact SHA.

Runner0.43.0/protocol1/38 identities and production/admission/C11 source remain
unchanged. M2av bounded source equivalence and M2aw target context remain
established; M2ax acquisition, M2ay build/encoding and M2az complete-set rights
remain blocked. Target C compiler/ABI NotEstablished; TargetCodeGenerationNotReady.
WDT3C and JGT C8 unresolved; M2aq CAL2689/RT5C80 NotRun; M2ah STOP before5722;
DATA019B.2 owner and recovered scheduler NotEstablished; IRQNotInjected;
TimerEvolutionNotModeled; GUI/hardware/fullboot NotRun. Actual-ROM, ASM662,
generators and target assembly/object/BIN outputs in M2ba are all zero.

STOP after delivery: no M2bb, actual encoder, source patch/build, lowering,
firmware/ROM replacement, WDT/C8/reset/fullboot, GUI, hardware or inquiry sending.
