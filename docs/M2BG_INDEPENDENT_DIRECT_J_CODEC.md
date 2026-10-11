# M2bg - independent one-form direct-J synthetic codec

Result: **M2bg Independent Direct-J Synthetic Encode/Decode Verified** within
the closed research domain only. SingleInstructionOnly; actual target execution
is not observed. NativeExitIsolationNotEstablished, ActualDownstreamRejoinNotEstablished,
TargetProgramCodeGenerationNotReady and FirmwareIntegrationNotEstablished remain.

Exact base: `3c76b6a54ac1e298470e1452a433090f34c49e1c` (M2bf).
Branch: `codex/p28-independent-direct-j-codec-m2bg`.
The old15-form encoder/decoder,18-site IR/C11/C#/context/lowering/layout/continuation
contracts and production/admissions/Windows stabilization remain byte-identical.
Runner0.43.0/protocol1/38 identities unchanged.

## Primary proof before persisted implementation

The OKI MSM66201 Instruction Manual, first edition September1991, SHA256
`f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271`,
is the new header's source. The main agent freshly reviewed complete relevant
pages using preserved private renderings, including a new full-page J rendering.
Printed3-62, physical116/index115, independently shows three code cells:
**03, adrL, adrH**. The note explicitly orders lower8 then upper8 bits.
The Function replacesPC by a16-bit PROGRAM address0000..FFFF. Summary3-210,
physical263, separately corroborates length3 and the PC-address operation;
it is another section of the same manual, not a second independent source.
Jobj3-63/physical117 and SJ3-140/physical193 remain distinct unsupported forms.
Jump/call summaries3-210..212/physical263..265 were checked in full.
Program/DATA distinction and PC rules1-1..5/1-7, byte order1-5, DATA word alignment1-18,
and DD1-21..24 were also reviewed. Cover and contents are separate review pages.
Printed versus physical coordinates are explicit; no guessed global offset.
Primary PDFs/page images/native windows are not published.

Root, oracle author and separate reviewer independently read the relevant code
table. Private API/error-order specification and exact primary literals were
sealed before any persisted encoder/decoder module or codec execution.
Temporary root source text prepared in memory was not an expectation source;
the separate oracle author received no candidate implementation. Honest module
absence is recorded with calls0, not a fabricated RED or defective old encoder.
Primary literal values are never obtained from encoder/decoder output.
Preparation diagnostics, if any, remain explicit with original snapshots.

The implementations were authored from manufacturer facts, not ASM662,
Doc66207.op, a generated opcode table, Rust decoder or C# output.
Historical third-party exposure remains disclosed. This is not legal
clean-room certification or a new third-party rights grant.

## Closed typed APIs and validation order

`direct_j_types.py` contains only own frozen/slotted public types and enums,
not shared opcode tables. ProgramTarget16 wraps an exact int; constructors
do not coerce inputs. Exact API classes and complete slots are checked by
the codec functions. Metadata defaults are init=False, not caller-promotable
CPU/stack/firmware result fields.

```text
encode_direct_j(DirectJEncodeRequest(ProgramTarget16(value), origin_pc, incoming_dd))
    -> EncodedDirectJ | DirectJEncodeError
decode_direct_j(DirectJDecodeRequest(exact_three_bytes, origin_pc, incoming_dd))
    -> DecodedDirectJ | DirectJDecodeError
```

Encoder: request shape -> exact target class/value type -> target range ->
DD -> origin -> extent -> construct exactly3 immutable bytes.
Its six explicit codes are RequestShape, TargetTypeInvalid, TargetOutOfRange,
IncomingDDInvalid, OriginInvalid and OriginSpanOutsideProfile.

Decoder: request shape -> exact bytes type -> exact length -> DD -> origin ->
extent -> exact header -> construct typed target and immutable result.
Empty input returns EncodedLengthInvalid;1/2 bytes TruncatedEncoding;
more than3 bytes TrailingBytes. These checks precede DD/origin/header.
The other six codes are RequestShape, EncodedBytesInvalid, IncomingDDInvalid,
OriginInvalid, OriginSpanOutsideProfile and UnsupportedEncoding.
Unsupported means outside this single-form profile, not universally illegal ISA.

Error objects hold only their direction-specific enum code: no partial bytes,
guessed target, success classification or warning-only success.
Bool/float/string/null/subclasses/spoofed/missing-slot requests are refused
without numeric conversion or mutable-buffer acceptance.
Wrong fixed headers are refused; every low/high pair under correct03 is valid.
Operand mutation may legitimately decode to another target; there is no blanket
refusal of changed operand bytes. Reversed cells represent a different valid
target, not an invalid encoding or automatic endianness repair.

Both exact incomingDD0/1 are accepted. Target/origin are0..FFFF, with
origin+3<=65536. OriginFFFD is legal, FFFE/FFFF refuse.
EndExclusive10000 is analytical extent, not sequentialPC16/fallthrough authority.
No signed-rel8 restriction, alignment filter, physical-ROM filter, modulo wrap,
host-endian cast, target execution or DATA[target] read exists.

Encoder and decoder import only their distinct allowed public-type symbols.
They independently transcribe the primary header and implement their own logic;
neither imports/calls the other, a common generated table or the oracle.
Only the test harness connects them as compatibility controls.

## Documentary effects are not runtime observations

The J Function and flag tables list no A/AL/AH/LRB/SCB/pointing/SSP or RAM writer,
no functional DATA operand read and no CAL/RT frame. ZF/CF/HC/DD effect cells and
affectingDD cell are blank. Results carry DocumentedPCReplacement,
DocumentedDDPreservedWhenExecuted and ManufacturerFunctionAndFlagTablesOnly_NoRuntimeEvidence.
This is scoped documentary absence/noninterference, not measurement of all
CPU, peripheral, timing or bus state. Program fetch is not a DATA operand read.
No CPU state, register snapshot, RAM writer identity, stack frame or trace is made.

SF interpretation, customer ECU ASIC applicability, PROGRAM mapping, external
bus/destination fetch, downstream live-in, compiler ABI and integration remain unknown.
Numerical target representability is not physical fetchability or placement permission.
Standard66201's internalROM limit does not reject an encodable external target.

## Independent literal and exhaustive proof domains

The pure oracle has24 independently authored literal cases:12 targets x2DD.
They cover0000/0001/00FF/0100/5596/55C5/7FFF/8000/FFFF and asymmetric extra
operands at origins0/1000/FFFD. Exact private expected bytes and their independent
review/seals predate persisted codec implementation. Expected arithmetic uses
positional base256, not implementation output.

The exhaustive main domain is65536targets x2DD x3origins =393216 distinct contexts.
Proof directions are reported separately:

- A: primary specification -> encoder -> exact3cells and metadata.
- B: independent primary bytes -> decoder -> exact typed target and metadata.
- C1: typed request -> encode -> decode; compatibility only.
- C2: independent primary bytes -> decode -> encode; compatibility only.

Actual first suite:31.976seconds, failures/skips0, firstMismatch=null.
A/B/C1/C2 each393240 comparisons,393216 unique positive contexts and24 overlapping
literal labels. Negatives45encoder/1581decoder labels,90/3162 deterministic
refusal calls; all6encoder/all9decoder error codes reached. Operand mutation12312
attempts,10688 distinct accepted inputs, all already within the main positive domain.
Actual encoderCalls786570/decoderCalls800330 =1586900 API calls. Successful
single-instruction emissions786480 sequences/2359440 octets; decodedResults797168;
immutability1746checks. These counts describe one observed suite, not cumulative
local/review/CI repeats, target binaries or concatenated instruction streams.

Literal24 labels overlap the full-domain contexts; coverage memberships/calls/
unique inputs/emitted single-instruction counts are not added as independent ISA
proofs. Both round trips supplement rather than replace A/B primary comparisons.
Error determinism/atomicity/immutability, wrong-header/truncation/trailing controls,
LE reversal/operand changes, target5596/55C5 at bothDD/allorigins, unknown/fake
runtime metadata and hostile subclasses are checked without CPU execution.
Actual source-bound receipts retain firstMismatch and any initial diagnostics;
no expected-byte change, skip, catch-pass or retry-until-pass stabilization.

## Contract validation and independent source audit

`direct_j_contract.json` pins manufacturer/header/oneform/length/API/LE/extent/DD/
errors/primary fixtures and historical immutable source identities.
`validate_direct_j_contract.py` checks safety-critical fields with its own
pinned rules. No editable verified=true field establishes a test result.
Observed receipts and exact source hashes are checked separately; the CI step
must also run the actual test suite. Retained NotRun preparation is not rewritten
as observed proof. Source-policy/closed-metadata mutation refusals are distinct
from primary byte-domain assertions.

The AST/static guard is trusted-source defense-in-depth, not a sandbox for
arbitrary Python. Attack fixtures are parsed only. The new pure codec has no IO,
network, subprocess, OEM loader, CPU/RAM integration, generic arbitrary-opcode API,
production export hook, instruction concatenation or persistent binary writer.
Single3-byte construction is allowed only in the encoder after complete validation.

```text
python -B research/p28-word0196/validate_direct_j_contract.py
python -B research/p28-word0196/direct_j_tests.py
```

## Preservation, delivery and unresolved boundaries

Exactly one additive Ubuntu/Windows research-only step; previous12 research steps
and Rust/Core/CLI/Desktop/format/privacy/portable checks remain unchanged.
CI downloads no ASM662, OEM ROM or proprietary toolchain and publishes no
single-instruction target payload artifact. Local full old research/C11/C#/offline
regressions, protectedSHA256 and all18stabilization/all20historical runners are
bound separately to actual private receipts and exact-SHA3jobCI.
The private final report is saved last after all workers freeze.

M2bf continuations5596/55C5 and paths10/12/13/15 are unchanged;13-step native
witness0 remains StaticPrimaryAndInventedCoverage. M2be18sites/15forms/45lengths,
Common16/NotBelow23/Below6, excluded41 and dense/gap/self-target hazards remain.
These new synthetic operand controls are not J sites after5594/55C3, a completed
18+2 program, a relocated fragment, safe native exit, original-ROM replacement
or permission to overwrite the historical PCs.

M2bd/M2bc/M2bb/M2ba/M2aw/M2av results retained. ASM rights/build and MAC66K
acquisition blocked; INT/DEC_HC/SLLB fixes retained; WDT3C/JGT C8 unresolved;
CAL2689/RT5C80NotRun; SSP/ADC blocked; DATA019B frontier/M2ahSTOPbefore5722/
019B.2 missing owner unchanged. M2t/StrictM2i blocked; ECU scheduler/targetC ABI/
physical placement/native isolation/rejoin/firmware integration unestablished;
IRQNotInjected;TimerEvolutionNotModeled;PcInspectionOnly/NotFlashReady.
Physical fuel/time/degrees unavailable; ASM/WDT/C8 inquiriesNotSent.
GUI/hardware/fullbootNotRun.

New single-instruction synthetic in-memory bytes are authorized and counted;
persistent target binaries/HEX/assembly/objects/streams/ROMpatch/FirmwareBIN0.
Actual-ROM/new-fragmentCPU/ASM662/MAC66K executions0.
Old M2bb/M2bc synthetic bytes and host QA executables are separate regression domains.

One proposed NEXT, NOT performed: an invented-only static composition proof for
the unchanged18-site obligations plus two abstract direct-J exits, preserving
branches, context and terminal isolation constraints, WITHOUT generating a
stream, placement, ROM patch or runtime proof. Separate authorization required.
STOP after final report: no M2bh/fullIRlowering/18-site assembly/native trampoline/
linker/ROM/firmware/WDT/C8/reset/fullboot/GUI/hardware work.
