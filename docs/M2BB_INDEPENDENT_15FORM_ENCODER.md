# M2bb — independent typed 15-form instruction encoder

Result: **M2bb Independent 15-Form Synthetic Encoding Verified** applies only to
the reviewed forms and invented input domain. Actual target execution is NOT
observed. This is not a general assembler, C compiler, native fragment, firmware
or FirmwareReady result. Exact base: `4f8ee4cd2c4988ef868d5f51d570a6bb96f57a1e`.
Branch: `codex/p28-independent-15form-encoder-m2bb`.

## Sources and independence

Classification: `PrimaryManualDerivedIndependentImplementation`. All new code
was authored for HondaEcu using manufacturer functional facts, independently
reviewed M2ay primary expectations and a new own typed model. No ASM662/Doc
table, grammar, lexer, generator, emitted code, DASM output, Rust FULL_OPCODES,
C# output or other project's generated table is an implementation/expectation
source. Prior third-party source exposure is disclosed; no legal clean-room
certification is claimed. Historical ASM662 rights/build status stays blocked.

The main agent re-reviewed complete relevant pages of the *MSM66201 Instruction
Manual*, September1991. Manual SHA256:
`f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271`.
Independent M2ay expectation ledger SHA256:
`a268815a0c04a4e2f0fccb64021ead26e1cbdaa02c1cc435d816f7d35fa2ab44`.
[M2ba design](M2BA_DOC_OPCODE_RIGHTS_AND_ENCODER_ROUTE.md) remains byte-identical
and its historical verdict is not rewritten as an implemented encoder.

## Pure typed API and atomic errors

`research/p28-word0196/independent_encoder.py` supplies `FormId`, `ErrorCode`,
ten frozen/slotted operand classes, `EncoderRequest`, `EncodedInstruction` and
`ExplicitError`. Python3 standard library only; no third-party dependencies.

```python
from independent_encoder import (
    AccumulatorA, EncoderRequest, FormId, PageOffset8, encode_instruction,
)

request = EncoderRequest(FormId.LB_A_PAGE, (AccumulatorA(), PageOffset8(0x37)), 0, 0x0100)
result = encode_instruction(request)  # SyntheticInstructionEncodingOnly; in-memory F4 37.
```

There is no CLI for assembly or output files. The function accepts one exact
request, never dictionaries/text mnemonics/raw opcode bytes. Result audit fields
retain form, immutable bytes, exact length, origin, typed operands and incoming
DD. It carries no CPU execution, generation-owner or hardware-readiness metadata.
Error contains **only an enum code**, no partial bytes/warnings/length/output.

Validation precedes byte construction: exact request slots/form identity, typed
DD, origin/span, exact immutable operand tuple/count, exact operand classes,
complete slots, numeric ranges/fixed identities, even-word profile and rel8.
Operand error selection is deterministic left-to-right, not an undocumented
global ranking between unrelated errors. Unknown fields/duplicates are refused
by fixed constructors/closed enums/exact typed shapes. No coercion accepts bool,
float, numeric text, null, integer subclasses, negatives or overflow.

The thirteen codes are RequestShape, UnsupportedForm, IncomingDDInvalid,
WrongDD, OriginInvalid, OriginSpanOutsideProfile, OperandCount, OperandKind,
OperandShape, OperandRange, FixedOperandMismatch, OddWordOffsetOutsideProfile
and Rel8OutOfRange. An internal exact-length assertion is not input validation
or zero padding. No target instruction is executed; no RAM/context is mutated.

## Exact supported domain

| Closed FormId value | Form | Primary PDF / printed | Length | DD |
|---|---|---|---:|---|
| lb-a-page | LB A,off N8 |124 /3-70|2|Either; native LB sets0|
| sllb-a | SLLB A |197 /3-144|1|Requires0|
| rolb-page | ROLB off N8 |173 /3-120|3|Independent|
| lb-a-r0 | LB A,r0 |124 /3-70|1|Either; native LB sets0|
| andb-a-page | ANDB A,off N8 |76 /3-24|2|Requires0|
| cmp-page-imm16 | CMP off N8,#N16 |90 /3-38|5|Independent|
| jlt-rel8 | JLT rel8 |120-121 /3-66-67|2|Independent|
| movb-r1-page | MOVB r1,off N8 |153 /3-99|3|Independent|
| andb-page-a | ANDB off N8,A |77 /3-25|3|Independent|
| jbs-page-bit7 | JBS off N8.7,rel8 |119 /3-65|3|Independent|
| jbs-page-bit5 | JBS off N8.5,rel8 |119 /3-65|3|Independent|
| orb-page-imm8 | ORB off N'8,#N8 |163 /3-110|4|Independent|
| orb-a-imm8 | ORB A,#N8 |160 /3-107|2|Requires0|
| lb-a-imm8 | LB A,#N8 |124 /3-70|2|Either; native LB sets0|
| stb-a-page | STB A,off N8 |208 /3-155|2|Requires0|

Only fixed r0/r1 and JBS bit7/bit5 are supported, not general register/bit forms.
JGT C8, ADDer3,A, other shifts/rotates/DEC/INC, CAL/RT, reset, P2/IRQ/timer
forms are unsupported. ROLB's word-long description typo remains explicit;
byte heading/diagram/code table determine the reviewed encoding. The prime in
ORB N'8 denotes a distinct operand variable, not another addressing mode.

PageOffset8 is a raw0..255 offset, not a DATA16 address or inferred LRB page.
Immediate8 is0..255; Immediate16 and TargetPC16 are0..65535. CMP requires
EvenPageOffset8 (even0..254). That is a conservative encoder restriction:
PDF22/printed1-18 describes CPU word align-down, not ISA-illegal odd operands.

CMP emits low byte then high byte, explicitly after range validation, never
host byte order/pointer casts. A55A yields5A A5, while65536 is rejected rather
than truncated. DD is exact integer0/1. Encoding LB preserves request incomingDD;
it does not simulate native DD0 or plan a subsequent instruction's state.

Rel8 is `target - (origin + length)`, signed-128..127; only after validation is
two's-complement8 formed. Origin/target are exact0..FFFF; instruction extent is
origin+length<=65536. Branch nextPC must also be<=FFFF (NoWrapProfile).
A nonbranch's last byte atFFFF is legal within this profile; rel8 nextPC10000
is not. No modulo repair, relocation, labels, relaxation or extra instructions.

## Independent oracle, RED/GREEN and actual coverage

The test-only `independent_encoder_oracle.py` imports no encoder/decoder/executor.
Thirty primary literal examples (15 retained +15 new) and mathematical expected
rules were sealed BEFORE implementation. LE16 oracle uses divmod/recomposition;
rel8 oracle uses signed mathematical validation and modulo only afterward.
The implementation uses separately authored typed checks and bit operations.
Expected values are never generated with the encoder under test.

Genuine RED executed one module-presence assertion while the encoder was absent:
exit1/failed1, byteAssertionsRun0, primaryByteCasesNotRun15. No stub, artificial
wrong bytes or invented old0.43 encoder. Original preparation/RED seals remain
unchanged. A separately documented test-accounting correction changed counters
only, not expectations/assertions/coverage. Later EOF-only formatting of the
two fixture/test files is explicitly sealed against immutable pre-format copies;
their AST and expected values are unchanged. Original phase receipts stay intact.

First actual GREEN:272457 checked successful vectors,1190 negative cases,
30 oracle literal cases,13 error codes, failures/skips0, firstMismatch=null.
Coverage includes4352 allowed offset cases,256 odd-CMP refusals,1280 immediate8
cases,131072 immediate16 cases (65536x2DD),4608 rel8 cases (3formsx2DDx3originsx256)
and131072 crossed ORB offset/immediate pairs (256x256x2DD). Original/new example
assertions also cover all allowed DD contexts. Invalid widths/types/kinds/counts,
missing slots/fixed identities/unknown fields, wrong/unknown DD, span/rel8
boundaries, deterministic atomic errors and normal immutability are checked.

Accounting is separate from vector coverage:274839 actual encode calls,
272458 successful in-memory sequences,1208771 emitted in-memory octets in that
test run, including direct immutability probes and repeated error calls.
These are **not persistent binaries, target objects or firmware**. Counts are
per actual QA run, not a fabricated cumulative total across repeated local/CI runs.
The independently prepared oracle math self-check covers69638 cases without
typed encoder invocations. Later independent review/final regression/CI receipts
are bound separately; a matching decoder would only be compatibility control.

## Contract, CI and retained boundaries

`independent_encoder_contract.json` and its separate validator pin reviewed
metadata/source identity and reject runtime/firmware promotion. The validator
does not import the encoder/oracle to manufacture expected results. Per form:
PrimaryEncodingSpecified, EncoderImplemented, SyntheticBytesMatchPrimary,
NegativeBoundaryTestsPassed, IndependentReviewPassed; target execution remains
ActualTargetExecutionNotObserved. Source-bound documentary checks are not by
themselves a fresh byte test; actual commands/counters are separately audited.

```text
python -B research/p28-word0196/validate_independent_encoder_contract.py
python -B research/p28-word0196/independent_encoder_tests.py
```

CI adds one research-only validation/test step on Ubuntu/Windows, without
ASM662/proprietary/ROM downloads or binary-artifact publication. Existing jobs,
M2ba/M2az/M2ay/M2ax/M2aw and M2av host/IR/C# steps, Desktop portable checks and
format/privacy guards are retained. Full private QA repeats Rust/Core/CLI/Desktop
headless, exact new encoder coverage, unchanged C11 and offline historical rows.
Protected Before/After,18 stabilization sources and15 prior runners are audited.

M2av IR/C11/source equivalence, M2aw context and M2ba design remain unchanged.
Runner0.43.0/protocol1/38 identities; production decoder/executor/admissions,
Core/CLI/scenario/C# and GUI/stabilization unchanged. Single-instruction synthetic
encoding is performed; full native program/fragment and firmware generation are
NotRun/NotReady. Compiler ABI, register allocation, DD/LRB/SCB/flag/control-flow/
write ordering, stack/continuations, placement and actual native equivalence
remain separate gates. No full18-site M2av implementation is generated.

WDT3C/JGT C8 unresolved; M2aq CAL2689/RT5C80NotRun; M2ap SSP/ADC blocked;
M2ao019B frontier and M2ah STOPbefore5722 unchanged;019B.2 runtime owner,
scheduler and compiler ABI NotEstablished; M2t/strictM2i blocked;
IRQNotInjected;TimerEvolutionNotModeled;PcInspectionOnly/NotFlashReady;
physical fuel/time/degrees unavailable; all inquiriesNotSent.
Actual-ROM0;ASM6620;target assembly/object/HEX/FirmwareBIN0;GUI/hardware/fullbootNotRun.

One next evidence-driven proposal, NOT started: an invented-only independent
decode/encode compatibility review for these same15forms, keeping primary
expectations authoritative and never automatically changing production ISA.
STOP after delivery: no M2bc, full IR lowering/stream/linker/ROM replacement,
firmware, WDT/C8/reset/fullboot, GUI or hardware work.
