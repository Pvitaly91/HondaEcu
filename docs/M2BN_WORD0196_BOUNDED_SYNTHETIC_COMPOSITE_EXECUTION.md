# M2bn: bounded synthetic composite execution

This is a separately authorized research-only successor to M2bm, based on
`b9e580f7cd554dd44676a5829444ece265bb517c`. Historical M2bk/M2bl/M2bm APIs,
fixtures, oracles and NotRun classifications remain unchanged. There is no
production Bus/exec/runner modification, original-ROM execution or firmware.

## Exact executable scope

Only the unchanged M2bj emitter supplies the in-memory 51-byte PROGRAM segment
`1000..1033`, digest
`91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1`.
Both scalar-DD emissions must be byte-identical. Admission checks the actual
bytes, source/provenance, all twenty identities, exact forms/operands/lengths,
successors and direct-J targets. There is no file/ROM/padding/stub interface.

The new unpublished Rust crate reuses unchanged production Cpu and decoder and
unchanged M2bm entry, DATA, admission and PSW components. Because M2bm's effect
function is private, its small execute_one/relative semantic bodies are copied
into the new effects.rs, with a frozen original source SHA and exact full-tail
comparison before execution. Only imports and visibility are adapted. Source
identity is not by itself behavioral equivalence: every observed instruction
and complete case is independently compared with the frozen M2bk source oracle.

Each case has one Cpu, one DATA/pointing initialization, one functional phase,
one lifecycle, and cumulative observed journals. No state is reseeded between
steps. PC comes from actual decoded execution, not from a preselected path.
Entry predicates only select the exact DATA permission profile; a forged caller
path cannot widen it. No Cpu defaults complete absent snapshot fields.

## Explicit representable-PSW and opaque SF scope

Route A requires `(fullPSW & 0x0CC8) == 0x0CC8`, with exact fullPSW/named flag/
OtherPSW/SCB aliases. All 65,536 candidates go through the new admission boundary;
incompatible inputs are refused before Cpu construction, PROGRAM execution fetch
or functional DATA writes. Counts are 128/3968 for low12 and 2048/63488 for the
full word. This is a limitation of canonical Rust representation, not a law of
hardware. Independent lossless Route B and the historical M2bk domain remain.

SF value/meaning/storage/width remain unknown. Every positive case has separate
internal false/true runs; all declared architectural effects and journals must
match and the internal field must retain its seed. This establishes no physical
boolean interpretation of SF. All eight pointing banks and all32 words are
explicit and checked, including unselected-bank retention and r1/high(er0).

## Frozen corpus and independent comparison

Ten bounded coverage families contain2735base cases /5470SF-paired executions:
2048representable PSW words distributed among four paths;64path/DD/flag cases;
40word/gate boundaries;256DATA018E and256AH sweeps;20representative data cases;
8SCB/pointing contexts;7same-value writers;4short-circuit controls;32carry cases.
This is not exhaustive PSW-times-path-times-DATA coverage.

Before the first new CPU observation, the validator freezes generator/oracle/
source identities and complete ordered case/expectation stream hashes. Expected
architectural state comes from unchanged M2bk, reviewed M2av C11/IR and M2bd
dataflow, never this executor or production decoder output. The separately
labelled decoder callback topology model checks observation integrity only.

Every before/after snapshot, step, flags, aliases, DATA byte, logical/raw access,
same-value writer, retained context, branch and retirement is compared strictly.
The unchanged host C11 implementation separately checks the compact state and
original instruction/access/write order on the same5470 inputs. Its compact
state is not claimed to contain all32 pointing words; the full comparator does.
Controlled corruptions must produce a real structured first mismatch.

| Path | Instructions including J | Logical DATA reads | Writes | Terminal PC |
|---|---:|---:|---:|---|
| A |11|5|3|55C5|
| B |13|9|3|5596|
| C |14|10|3|5596|
| D |16|12|5|5596|

The hard budget is16. One real direct J changes Cpu.pc, then independent
lifecycle and PROGRAM observer guards seal execution. No extra confirmation
step or external fetch occurs. Negative access attempts, partial budget-failure
execution and metadata-only refusals are counted separately from positive runs.
Cpu.cycles and counters are synthetic accounting, not physical timing/IRQ proof.

## Reproducible execution and public-safe evidence

```text
python -B research/p28-word0196/validate_synthetic_composite_execution.py
```

The validator builds/tests the actual Rust crate with pinned1.85.1/jobs1,
compiles the unchanged host C11 driver and runs the finite experiment. It uses
new M2bn-owned output directories, refuses evidence overwrites and retains
failures. `--freeze-only` performs reference-only preparation, not execution.

The predetermined canonical JSONL projection includes every observation field,
ordered actual PROGRAM addresses/purposes/extent digests/serviced/refused state,
and full architectural/DATA journals. PROGRAM byte values and complete payload
dumps are never persisted. Raw byte-level identity/operand checks happen only
in memory; a semantic projection is not represented as a raw payload dump.

Large canonical streams are streamed through gzip into allowlisted public-safe
CI artifacts, not Actions console dumps. Local/Ubuntu/Windows full decompressed
bytes must be compared incrementally; matching hashes/counts alone are not an
acceptance proof. Host paths, timestamps, compilation logs and process metadata
remain outside the semantic stream. No architectural field is filtered later.

Production321/Core2947/CLI959/Desktop183, unchanged M2bm35+1, C11398658,
C/C#81920,14historical suites, M2bj primary/decode/hash/88atomic refusals,
format/privacy/diff/portable and full protected hashes remain delivery gates.
Desktop keeps30seconds,56original/64assertions, real WPF/RPM and100/125/150%
viewports; no Option B extension or manual GUI/hardware work is authorized.

## Result boundaries

Only actual successful observations can establish
`ActualSyntheticCompositeExecutionObserved` and the tested finite representable
corpus. Even success remains
`CpuStateAndProductionDecoderWithResearch16FormExecutor`,
`TestedPswDomainRestricted`, `ProductionBusExecIntegrationNotEstablished`,
`SFMeaningStorageNotEstablished`, `ActualDownstreamRejoinNotEstablished`,
`PhysicalROMPlacementNotEstablished`, `TargetProgramEquivalenceNotEstablished`,
`FirmwareIntegrationNotEstablished`, `FirmwareReady=false`.
Actual-ROM/native-downstream executions and new target BIN/object/HEX/FirmwareBIN
remain zero. Host research binaries are not target firmware. No M2bo follows.
