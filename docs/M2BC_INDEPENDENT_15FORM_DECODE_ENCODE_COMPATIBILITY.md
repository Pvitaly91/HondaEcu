# M2bc - independent 15-form decode/encode compatibility

Result: **M2bc Independent 15-Form Decode/Encode Compatibility Verified**, only
for the closed manufacturer-reviewed synthetic profile. This is not a general
disassembler, assembler, execution engine, native fragment or firmware result.
Exact base: `106e66e54bc07340dd62e3f8d206c96ee419d7ed` (M2bb).
Branch: `codex/p28-independent-15form-decode-encode-m2bc`.

## Independent primary evidence and implementation

The main agent freshly reviewed 15 complete relevant pages of the September1991
MSM66201 Instruction Manual: PDF9,22,76,77,90,119,120,121,124,153,160,163,173,
197,208. Manual SHA256:
`f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271`.
M2ay independent expectation ledger SHA256:
`a268815a0c04a4e2f0fccb64021ead26e1cbdaa02c1cc435d816f7d35fa2ab44`.
The [M2ba design](M2BA_DOC_OPCODE_RIGHTS_AND_ENCODER_ROUTE.md) and
[M2bb encoder](M2BB_INDEPENDENT_15FORM_ENCODER.md) remain unchanged.

Classification: `PrimaryManualDerivedIndependentImplementation`, not legally
certified clean-room. New code was authored for HondaEcu from functional
manufacturer facts. No ASM662/DASM/Doc tables or grammar/generators, Rust
FULL_OPCODES or other disassembler implementation is an inverse-decoding source.
Historical third-party source exposure is disclosed; rights remain blocked.

`research/p28-word0196/independent_decoder.py` defines pure
`decode_instruction(DecoderRequest) -> DecodedInstruction | ExplicitDecodeError`.
Only eleven public M2bb type symbols (FormId and ten immutable operand classes)
are imported. Importing those definitions loads the M2bb module; this is NOT a
claim that the module was never imported. The decoder does not reference/call
the encoder function, its internal shape/emission tables or an expected oracle.
Its own explicit header conditions are independently authored code-column
recognition, not a reversed shared emitter or shortest-prefix registry.

## Closed exact grammar

| FormId | Complete structure | Length | PDF / printed | DD |
|---|---|---:|---|---|
|lb-a-page|F4 offset8|2|124 /3-70|Both; native LB sets0|
|sllb-a|53|1|197 /3-144|Requires0|
|rolb-page|C4 offset8 B7|3|173 /3-120|Independent|
|lb-a-r0|78|1|124 /3-70|Both; native LB sets0|
|andb-a-page|D7 offset8|2|76 /3-24|Requires0|
|cmp-page-imm16|B4 offset8 C0 low high|5|90 /3-38|Independent|
|jlt-rel8|CA displacement8|2|120-121 /3-66-67|Independent|
|movb-r1-page|C4 offset8 49|3|153 /3-99|Independent|
|andb-page-a|C4 offset8 D1|3|77 /3-25|Independent|
|jbs-page-bit7|EF offset8 displacement8|3|119 /3-65|Independent|
|jbs-page-bit5|ED offset8 displacement8|3|119 /3-65|Independent|
|orb-page-imm8|C4 offset8 E0 immediate8|4|163 /3-110|Independent|
|orb-a-imm8|E6 immediate8|2|160 /3-107|Requires0|
|lb-a-imm8|77 immediate8|2|124 /3-70|Both; native LB sets0|
|stb-a-page|D4 offset8|2|208 /3-155|Requires0|

No JGT C8, ADDer3,A, other registers/bits/shift/rotate forms, CAL/RT, P2, IRQ,
timer/reset/WDT or generic2623-pattern decoder is added. UnsupportedEncoding
means outside this profile, NOT a universally invalid CPU instruction.
ROLB's printed word-long description typo remains distinct from its byte heading,
diagram and exact code row. ORB's primed N denotes a separate operand variable.

C4 requires a complete third-byte suffix: B7/49/D1 select distinct3-byte forms;
E0 selects4-byte ORB. Unknown suffix is unsupported, never guessed. C4 or C4+off
is truncated; C4+off+E0 is truncated. B4 needs third-byte C0 before selecting
5-byte CMP; a different third byte is unsupported. All fifteen header conditions
are disjoint in this closed profile; no global nX-8/200 ISA uniqueness is claimed.

## Typed output, context and profile boundaries

DecoderRequest has only encoded_bytes, incoming_dd, origin_pc. Exactly immutable
bytes of length1..5 and exact integers DD0/1/origin0..FFFF are required. Booleans,
subclasses, floats, strings, null/mutable buffers/unknown fields are refused.
There is no file/ROM loader, requested mnemonic/form/register/bit reinterpretation
or stream API. A complete supported instruction plus trailing bytes is refused,
not sliced or padded. Oversized inputs (>5), including a5-byte CMP plus a byte,
are rejected by the length bound before grammar classification.

Success is frozen/slotted: exact shared FormId, exact typed immutable operands,
length, origin, unchanged incomingDD, optional reconstructed relative_target_pc,
documented_dd_effect, SyntheticInstructionDecodingOnly and ExactSupportedForm.
Raw page offsets stay raw8, without LRB or DATA16 expansion. Register0/Register1
and PageBit7/PageBit5 are reconstructed as their exact types, not positional ints.

LB metadata is SetsDD0WhenExecuted; other forms PreservesDDWhenExecuted.
This is documentation only: no instruction executes or changes DD/CPU/RAM/flags.
Exact53 under DD1 returns WrongDD for scoped SLLB, not invalid-ISA certification;
the manual describes a word SLL interpretation outside this profile.

CMP reconstructs low|(high<<8), explicitly little-endian. Odd raw word offsets
return OddWordOffsetOutsideProfile, never silently align or rewrite bytes.
PDF22/1-18 describes CPU word-address align-down; refusal is our stricter profile.

Signed rel8 is raw when<128, otherwise raw-256; target=origin+length+signed.
NoWrap requires origin+length<=65536, branch nextPC<=FFFF and target0..FFFF.
Nonbranch last byteFFFF is permitted; branch nextPC10000 or a target outside the
address space is refused without modulo repair/labels/relaxation/replacement.
A decoded target is a synthetic integer, not an executed destination.

## Frozen preimplementation error policy

Validation order was fixed and sealed BEFORE implementation: exact request/slots,
immutable bytes,1..5 bound, DD type, origin type, complete header, unique supported
match, exact selected length, requiredDD0, extent/branch-next, evenCMP, linear
relative target. Only after every check are typed result operands constructed.
Syntax length errors precede DD0-required context errors; malformed context types
precede recognition. No undocumented global priority is inferred beyond this.

ExplicitDecodeError is frozen/slotted and stores **only code**. Its computed
input_classification is a closed enum, not guessed form/operands or partial bytes.

| Code | Input classification |
|---|---|
|RequestShape / EncodedBytesInvalid / IncomingDDInvalid / OriginInvalid|MalformedRequest|
|EncodedLengthOutsideProfile / OriginSpanOutsideProfile / OddWordOffsetOutsideProfile / RelativeTargetOutsideProfile|ProfileRestrictionViolation|
|UnsupportedEncoding|UnsupportedEncodingWithinProfile|
|WrongDD|WrongDD|
|TruncatedEncoding|TruncatedEncoding|
|TrailingBytes|TrailingBytes|
|AmbiguousProfileMatch|AmbiguousProfileMatch|

Empty input is EncodedLengthOutsideProfile, not a guessed truncated form.
AmbiguousProfileMatch is a fail-closed defensive guard; the reviewed grammar
has no ambiguous match, so observed ambiguity0 is honest, not fabricated coverage
of all13 reachable error codes. Twelve error categories are actually reached.

## Primary oracle, preparation and three proof directions

`independent_decoder_primary_oracle.py` imports dataclasses only. Its separately
reviewed fixed-cell grammar and mathematical typed expectations are not produced
by M2bb encoder, the new decoder, Rust or C#. Thirty literal byte/typed fixtures
(15 prior primary +15 fresh M2bc values) were sealed while the decoder was absent.
Expected words use weighted octets; signed decoding uses independent arithmetic.

Preparation and actual absent observation explicitly report DecoderNotImplemented,
testsRun0/actualDecodeCalls0/inventedRedFailurefalse. No artificial wrong bytes,
stub or invented old-version RED. A one-final-LF formatting correction in the two
new fixture/test sources was audited BEFORE implementation: byte prefix/AST/
assertions/grammar/expectations unchanged, immutable prepared copies and original
seal preserved. Final preparation and current source bindings are separate.

Three directions remain distinct:

- A: independently prepared primary bytes -> decoder -> independently expected
  typed form/operands/length/DD/origin/target/effect. This is primary decode proof.
- B: original typed request -> unchanged M2bb encoder -> decoder -> original
  request. Compatibility ONLY, not independent ISA proof.
- C: independent primary bytes -> decoder -> unchanged encoder -> identical
  primary bytes, with no normalization/padding/trailing-data tolerance.

First actual GREEN:30 primary literal cases;280362 unique positive primary-decode
cases;280362 B round-trips;280362 C primary round-trips;11259 negative cases;
failures/skips0, firstMismatch=null. Positive vectors are deduplicated by exact
(payload,DD,origin).1117 overlapping positive attempts and2699 negative overlap
attempts are not added to unique totals. Coverage memberships are NOT disjoint
counts to sum or a cumulative total across later local/review/CI runs.

Coverage memberships:4096 byte-offset contexts;512 CMP even/odd contexts;
1280 immediate8;131072 immediate16 (65536x2DD);4608 signedrel8
(256x3formsx2DDx3origins);131072 ORB256x256x2DD;1536 C4 suffix/length/DD contexts;
768 B4 third-byte/length contexts;76 truncated-prefix attempts;90 trailing/stream
attempts;19380 one-octet mutations. Mutation outcomes9006 accepted/10374 refused
are attempts, not all unique vectors: supported operand/form changes are accepted
according to actual grammar, not blanket-refused. Independent header proof checks
65536 first/third-byte pairs:0ambiguities,4C4forms,partial prefix never guessed.

Natural actual accounting per run:583243 decoder calls/560725 decoded results;
560724 unchanged-encoder calls/in-memory sequences,2463890 in-memory octets.
Calls=2xpositive+2xnegative+1; successful decodes=2xpositive+1; emissions=2xpositive.
The raw negative-classification subcounter excludes10 separately tested RequestShape
cases; the negative total includes them. No fixture/assertion change hides this.
Persistent machine-code outputs remain0; these nonzero in-memory counts are NOT
target objects/firmware or decoder execution of the instructions.

## Contract, QA, preservation and historical statuses

`independent_decode_encode_contract.json` with its separate validator pins primary
identities, fixed profile/error policies, immutable oldM2bb hashes, current own
sources and observed proof references. JSON alone cannot grant NativeExecutionVerified
or runtime/admission permissions. AST source guards allow shared type symbols only,
not encoder calls/tables, inverse oracle imports, reflection or I/O/process aliases.
An initial DecoderNotImplemented contract snapshot is retained separately from
the source-bound observed final profile; a metadata check alone is not a byte test.

```text
python -B research/p28-word0196/validate_independent_decode_encode_contract.py
python -B research/p28-word0196/independent_decoder_tests.py
```

CI adds only one Python research step on Ubuntu/Windows; previous8research steps,
Rust/Core/CLI/Desktop/format/privacy and Desktop portable checks remain intact.
No ASM662/proprietary/ROM download or target-byte artifact publication.
Local full QA repeats unchanged M2bb/M2ba/M2az/M2ay/M2ax/M2aw and M2av IR/C11/C#
invented/offline historical checks. Delivery receipts bind exact counts, full
protected SHA256,18stabilization sources,16historical runners and exact pushed CI.

M2bb5public files and all prior private evidence unchanged. M2av18-site IR/C11/C#,
M2aw ABI, M2ba design and production Rust/C#/CLI/scenarios/admission unchanged.
Runner0.43.0/protocol1/38 identities. Secondary Rust compatibility **NotRun**:
no Match/Mismatch or absence-of-disagreement claim is manufactured.

Historical ASM662 rights/build and MAC66K acquisition blocked; WDT3C/JGT C8
unresolved; CAL2689/RT5C80NotRun; SSP/ADC blocked;019B frontier unchanged;
M2ah STOPbefore5722;019B.2 owner/scheduler/compiler ABI/integration NotEstablished;
M2t/StrictM2i blocked;IRQNotInjected;TimerEvolutionNotModeled;
PcInspectionOnly/NotFlashReady; physical fuel/time/degrees unavailable.
All inquiriesNotSent;actual-ROM0;ASM6620;target assembly/object/HEX/FirmwareBIN0;
GUI/hardware/fullbootNotRun. No full fragment/stream/layout/linker/ROM/patch/export.

One proposed NEXT evidence step, NOT started: an invented-only typed lowering
specification mapping the retained structured IR to the same15 reviewed instruction
requests, with explicit DD/flag/liveness/branch obligations and no emitted program,
stream placement or runtime authority. STOP after delivery: no M2bd/full lowering,
native fragment/linker/ROM/firmware/WDT/C8/reset/fullboot/GUI/hardware continuation.
