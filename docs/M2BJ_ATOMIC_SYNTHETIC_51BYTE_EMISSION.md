# M2bj — atomic synthetic composite encoding

M2bj implements a closed Python standard-library research API that emits one
immutable 51-byte synthetic fragment **in memory only**. It does not execute
instructions, consume an original ROM, produce a target object, or grant ECU
integration permission. Historical M2bi eligibility remains a separate result.

Exact base: `7585bfc164929c19fa044664c4d8173244a426fa`.
Branch: `codex/p28-word0196-atomic-synthetic-emission-m2bj`.

Local encoding/primary/decode/atomicity evidence is PASS. Delivery is incomplete:
the unchanged Desktop headless STA layout test timed out in both the full suite
and one isolated diagnostic. Its assertions/timeout/source remain unchanged;
there is no commit, push or M2bj CI verdict until this required gate is resolved.

## Closed API and transaction

`emit_synthetic_composite(reviewed_ir, reviewed_composition, reviewed_eligibility, request)`
returns a frozen `VerifiedSyntheticComposite` or a frozen byte-free
`ExplicitEmissionError`. Request keys are exactly `exactBase`, `scope`,
`syntheticBase`, `gap`, `initialDD`. Only scope
`word0196SoftwareAlternate18PlusTwoDirectJ`, base4096, gap0 and scalar integer
DD0 or DD1 are accepted; boolean/domain-array DD, FFCD layout, paths, callbacks,
alternate codecs and ROM/output/execution permission requests are refused.

The pure emitter has no filesystem/process/network/CPU interface. A separate
trusted fixed-path validator hashes 46 immutable upstream files before loading
the models. All three new emitter/oracle/test files are source-bound. Editable
contract metadata cannot establish a successful verdict or relax safety rules.

Frozen order: Identity → Request → actual M2bi Preflight → Plan → all
TypedRequests → Encoding → Primary → Assembly → Decoding → Structure →
FinalLength → FinalMetadata → single Publication. Each codec result is checked
before the next call. All20 real encodings precede all20 primary comparisons.
Every byte slice and complete concatenation must pass before publication.
Errors have a closed25-code enum, phase, logical identity when known and a fixed
safe diagnostic. Unexpected exceptions become explicit failure, never success;
no traceback, exception text, partial bytes, fallback, retry or skipped node
escapes the transaction. Test hooks are private monkeypatches, not API arguments.

The payload field is excluded from result repr. Callers must not serialize,
log, persist, emulate, flash or pass this result to a production ROM writer.
The API is a research boundary, not a sandbox or legal clean-room certification.

## Geometry and independent evidence

| Component | Synthetic half-open extent | Bytes |
|---|---|---:|
| Common | 1000–1010 | 16 |
| NotBelow | 1010–1027 | 23 |
| DirectJ_NotBelow | 1027–102A | 3 |
| Below | 102A–1030 | 6 |
| DirectJ_Below | 1030–1033 | 3 |

Addresses in this table are hexadecimal invented geometry, not physical ECU
PROGRAM-placement claims. The canonical20 boundaries cover51 octets exactly:
18 unchanged Route A requests (M2bb), two Route B requests (M2bg), 45+6 bytes,
no gaps, overlaps, padding, ignored trailing bytes or instruction splitting.

The primary oracle was prepared and sealed before emitter implementation.
It uses personally reviewed complete September1991 manufacturer manual pages
and unchanged M2ay/M2bb/M2bc/M2bg independent fixtures, not operational codec
output, Rust, ASM662, DASM662 or Doc66207.op. Its per-instruction arithmetic is
cross-checked against the separately authored primary decode-column grammar.
Only per-node digests, origins/targets/lengths and reference SHA are persisted;
the full expected reference is constructed exclusively inside the test oracle.

Both actual DD experiments match the independently fixed reference SHA-256:

`91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1`

SHA is reproducibility evidence, not a substitute for manufacturer comparisons.
The test independently checks individual encodings, complete concatenation and
exact-boundary decoding. Encoder/decoder agreement is compatibility only.
No full51-byte hex listing or binary artifact is included in source or logs.

JLT100E→102A has delta+26; JBS1016/1019→1023 have deltas+10/+7.
Direct J1027→5596 and1030→55C5 use the primary direct PROGRAM-target format,
not DATA pointers or relative relaxation. DD0/DD1 are separate calls; only the
first LB receives incomingDD1 in that experiment, then every site receivesDD0.
The streams and SHA are actually compared, not assumed equal.

Actual decoded boundaries reconstruct23 edges:18 fallthrough,3 taken,2 external.
All four structural paths have11/13/14/16 nodes, exactly one external J each;
no NotBelow→Below fallthrough or hidden call/return. These are static paths,
not CPU observations. Historical original path counts remain10/12/13/15.

## Static semantics are a separate proof level

Unchanged M2bd/M2bh/M2bi preflight retains CF5571→5572 and5578→557D, terminal
BelowCF1/NotBelowCF0, ZF0/DD0 and retainedAH/HC/OtherPSW. LRB0021/page0100,
local bank0108..010F, r1 as er0 high byte, even0196LE16 and code-owned00C0
remain static context obligations, not newly asserted CPU state.

Ordered writes3/3/3/5, DATA018E RMW, same-value writes, localr1 write,
short-circuit gate order, DATA0124 unread onB and DATA012A bit0 write only onD
are checked through the unchanged semantic preflight, separately from bytes.
Direct J adds no documentary DATA read/write, SSP/frame or flag writer.
There is no fabricated native RAM journal. Historical42 ROM observations,
552 snapshots/170 writes and missing original13-step-path native witness remain
unchanged; historical host regressions do not execute a new ROM or synthetic stream.

## Actual tests and delivery

Run `python -B research/p28-word0196/validate_synthetic_composite_contract.py`.
This invokes actual in-memory emission tests, not merely JSON validation.
The standalone `synthetic_composite_tests.py` runs the same suite.

One suite has two successful scalar-DD sequences,40 actual approved encoder
calls (36A/4B),40 decoder calls,40 primary comparisons,40 verified boundaries
and102 emitted octets. These are per-run counts, not unique counts summed
across local/CI reruns.75 negative mutations exercise distinct real semantic,
encoded-byte, assembly and decoder stages.13 closed fault cases include all
required early/late sites, primary/decode/final-length/final-metadata failures,
and unexpected exception.88 emitter refusals publish no partial success; eight
additional editable-contract mutations are refused. All25 error categories are
observed. First actual primary/decode mismatch is null; no assertions skipped.

Private evidence retains the first suite failure: two initial RAM-effect mutation
definitions reached earlier flag/metadata guards. They were corrected to remove
an actual store and reorder path write obligations, preserving the original
failure and unchanged primary fixture. No catch-and-pass or fixture fitting.

AST dependency/signature/publication audit plus instrumented filesystem/process
guards check the pure API. Source, preservation, privacy, full Rust/Core/CLI/
Desktop formatting and headless QA are separate delivery gates. CI adds exactly
one research-only step to both matrix OSes, preserving the prior15 research steps
and unchanged Desktop portable checks. Source-bound emitted SHA/counters must be
compared from actual Ubuntu and Windows CI output, not inferred from statuses.
Exact delivery SHA/run/attempt and gate receipts belong in the private final report.

## Remaining exclusions and STOP

`ActualTargetExecutionNotObserved`, `NativeExitIsolationNotEstablished`,
`ActualDownstreamRejoinNotEstablished`, `PhysicalROMPlacementNotEstablished`,
`TargetProgramEquivalenceNotEstablished`, `FirmwareIntegrationNotEstablished`,
`FirmwareReady=false`, `PcInspectionOnly / NotFlashReady`.

All historical blockers remain: WDT3C; C8 primary conflict; CAL2689/RT5C80 NotRun;
SSP/ADC; DATA019B frontier/019B.2 owner; STOP before5722; JGT233A; StrictM2i;
ECU scheduler; IRQ not injected; timer not modeled; target C ABI; customer ASIC;
stack/SF, native handoff, physical placement and downstream rejoin. Toolchain/
component-rights blockers and all NotSent inquiries remain unchanged. Runner
0.43.0/protocol1/38 identities and production/admission are byte-identical.

New CPU/original-ROM executions, target assembly/object/HEX/ROM patches and
FirmwareBIN are zero. GUI/hardware/fullboot are NotRun. No synthetic binary
CI artifact is published. STOP after final report. A possible next evidence-only
milestone is an independently specified bounded synthetic equivalence proof
protocol with state/context/effect obligations, requiring separate authorization;
do not begin M2bk, execution, linking/placement, firmware, WDT/C8 or hardware work.
