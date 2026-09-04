# Validation strategy

## Principle

Every conclusion is narrower than the evidence that supports it. HondaEcu separates byte facts, format hypotheses, editor observations, static code evidence, emulation, and physical validation. A green test suite proves the software contract against its fixtures; it does not prove an undocumented P28-304 offset or make a ROM safe to flash.

## Validation levels

The exact profile/report vocabulary is:

| Level | Required evidence | Does not establish |
|---|---|---|
| `public-documentation` | A traceable public source makes the claim | That the claim is correct, revision-specific, or writable |
| `oracle-observed` | Oracle analysis finds a reproducible candidate after no-op normalization | Which editor-specific/cross-editor level applies, or that the candidate is correct; this is a candidate/report label |
| `crome-observed` | Reproducible isolated Crome cases with exact version/options and hashes | HTS agreement or ECU behavior |
| `hts-observed` | Reproducible isolated HTS cases with exact version/options and hashes | Crome agreement or ECU behavior |
| `cross-editor-confirmed` | Both editors use the same baseline and agree on offset, width, endian, conversion, and rounding after no-op normalization | Static or physical behavior |
| `static-analysis-confirmed` | Relevant reads/writes and code flow are demonstrated with pinned tooling and reproducible notes | Timing, peripherals, or physical behavior |
| `emulator-observed` | A pinned emulator produces the observation under recorded stimuli | A cycle-/board-accurate ECU response |
| `bench-confirmed` | Instrumented bench observation under a recorded procedure | Vehicle behavior outside that procedure |
| `vehicle-confirmed` | Controlled vehicle observation under a reviewed test plan | Universality across revisions/vehicles |
| `disproved` | Reproducible evidence contradicts the claim | Other revisions or differently scoped claims |

These labels are evidence categories, not a simple automatic numeric ladder. Promotion is an explicit reviewed profile change with source references.

`oracle-observed` is deliberately narrow: it is the generic candidate/report label required for analyzer output. When the manifest provenance is known and reviewed, a profile claim should use the corresponding `crome-observed` or `hts-observed` label. Generic oracle output is never `bench-confirmed`.

## Three layers of validation

### 1. Software invariants with synthetic data

Public automated tests create deterministic 32,768-byte synthetic images and a synthetic profile that does not claim to be Honda/P28. Required coverage includes:

- SHA-256, CRC32, exact raw-size validation, immutable input, overwrite refusal, and atomic output;
- profile parsing and JSON Schema validation;
- unknown-ROM refusal and an explicit-profile override that remains visible;
- u8, signed byte, u16 little-/big-endian, linear, inverse, rounding, and out-of-range behavior;
- byte-identical no-op round-trip;
- exact changed offsets, contiguous range merging, and JSON diff/patch reports;
- verification of declared changes and rejection of undeclared changes;
- oracle no-op normalization, three-value linear and inverse cases, checksum-region exclusion, cross-editor conflict, and successful cross-editor agreement.

No OEM or editor-generated ROM is required by CI.

### 2. Private PC/oracle validation

Crome and HTS cases remain under `private/oracle/`; reports remain under `private/reports/`. Each series binds exact tool version, optional plugins, plugins-disabled state, profile, baseline/no-op/case hashes, one parameter/value per case, notes, timestamps, and byte ranges.

Analysis must:

1. subtract no-op normalization from parameter-specific changes;
2. keep checksum/plugin regions separate from calibration candidates;
3. use at least three distinct values for a parameter;
4. test all supported interpretations (u8, signed byte, u16 LE/BE, simple linear, inverse/period, and rounding);
5. report all candidates with residual error/confidence rather than only the most attractive one;
6. require an explicit export step for a candidate fragment;
7. never mutate the production profile automatically.

M0 refuses candidate inference unless `pluginsDisabled` is true, because a manifest does not describe plugin-owned byte regions well enough to exclude them safely. `AdditionalChangedRanges` contains only case-specific residual bytes left after subtracting candidate bytes and declared checksum regions from no-op-to-case diffs. No-op normalization and observed checksum changes remain visible in their own report fields rather than being duplicated as unexplained parameter changes.

Cross-editor comparison is valid only when both manifests identify the identical baseline SHA-256. See [CROME_ORACLE_WORKFLOW.md](CROME_ORACLE_WORKFLOW.md) and [HTS_ORACLE_WORKFLOW.md](HTS_ORACLE_WORKFLOW.md).

### 3. Static, bench, and vehicle validation

Future static work should pin the exact `asm662`/`dasm662` and Ghidra module revisions, start from separately obtained private ROM bytes, and retain only derived notes permissible for publication—not a complete OEM disassembly. The analyst must show code references that consume the candidate bytes and the exact conversion/branch semantics.

Emulator observations require a pinned emulator revision, command/stimulus, initial ROM hash, output trace hash, and known-model limitations. Emulation and static analysis remain PC-only.

Bench and vehicle levels require separate authorization, hardware procedures, rollback/recovery provisions, logging, conservative limits, and human review. They are out of scope for M0; the application never promotes an M0 result to `BenchCandidate` or above.

## Parameter admission gates

A definition may be documented as a read-only candidate when a public source provides a plausible address but interpretation is incomplete. It becomes writable only when all are true:

1. the offset and width are unambiguous for the exact revision scope;
2. endian and conversion/encoding are known, including rounding;
3. deterministic encode/decode round-trip and boundary tests pass;
4. the profile explicitly marks the definition experimental and a reviewer deliberately enables it.

`public-documentation` alone never satisfies these gates. Conflicting formulas remain `Unsupported` and read-only until resolved.

## Checksum strategy

The PGMFI page identifies a six-byte “Checksum Jump Routine” region at `0x2BAD` and describes a bypass patch. That is not an algorithm description. Until static evidence identifies covered ranges, stored bytes, arithmetic, exclusions, and acceptance behavior—and fixture tests confirm them—the profile uses `ChecksumStatus.Unknown`. HondaEcu neither invents a formula nor disables the routine. Any output with unknown checksum is not flash-ready.

## M0 acceptance evidence

M0 is complete at the software level when Release build/tests and format verification pass on Windows and Linux, public tests are synthetic, profiles validate against the checked-in schema, unsafe writes are refused, reports account for every changed byte, and the evidence ledger accurately marks unresolved P28-304 claims as candidates. Local Crome/HTS golden files are follow-up evidence, not public artifacts and not prerequisites for the public build.
