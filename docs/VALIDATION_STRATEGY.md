# Validation strategy

## Principle

Every conclusion is narrower than the evidence that supports it. HondaEcu separates byte facts, format hypotheses, editor observations, static code evidence, emulation, and physical validation. A green test suite proves the software contract against its fixtures; it does not prove an undocumented P28-304 offset or make a ROM safe to flash.

M0.1 uses the following terms deliberately:

- an **observation** is a measured fact with provenance: requested value, displayed value after reopening, raw bytes, file hash, and collection role;
- a **candidate hypothesis** is one possible offset/width/endian/conversion/rounding interpretation that fits some observations;
- a **fit score** summarizes agreement with fitting data; it is not a probability that the hypothesis is correct;
- a **holdout result** tests frozen, training-compatible hypotheses against independent cases that were not used to fit coefficients; it may rule out contradicted alternatives without refitting them;
- a **selected definition** may record an explicit review choice or the sole definition surviving every algorithmic gate; a manual choice itself contributes no new evidence and the rationale remains visible;
- a **verified definition** has passed the declared domain, independent holdout, exact encoded-byte, ambiguity, provenance, and diff-accounting gates;
- **cross-editor evidence** compares independently collected observations from two different editors using the same baseline. It does not prove ECU behavior.

These categories cannot be collapsed. A changed byte is actual even if no hypothesis explains it; a candidate may cover that byte without explaining it; and a manually selected candidate is not verified merely because it was selected.

## Validation levels

The exact profile/report vocabulary is:

| Level | Required evidence | Does not establish |
|---|---|---|
| `public-documentation` | A traceable public source makes the claim | That the claim is correct, revision-specific, or writable |
| `oracle-observed` | Oracle analysis finds a reproducible candidate against a controlled no-op parent while preserving the measured no-op transformation | Which editor-specific/cross-editor level applies, or that the candidate is correct; this is a candidate/report label |
| `crome-observed` | Reproducible isolated Crome cases with exact version/options and hashes | HTS agreement or ECU behavior |
| `hts-observed` | Reproducible isolated HTS cases with exact version/options and hashes | Crome agreement or ECU behavior |
| `cross-editor-confirmed` | Two different editors use the same baseline and independently validate the same unique definition, or the same proved behavior-equivalent definition class, including holdout bytes and all residual changes | Static or physical behavior; authenticity beyond user-declared provenance |
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

M0.1 regression coverage additionally exercises behaviorally equivalent and genuinely ambiguous rounding, positive and negative midpoint behavior, identical and contradictory repeats, quantized requests, train/holdout separation, inverse overfit, u8/u16 ambiguity, multiple common candidates, correlated side bytes, same-tool rejection in Core, non-finite metadata, stale digests, no-op instability, unexplained code-base transformations, incomplete preflight, and partial aggregate results.

Fixtures are created in code and are explicitly synthetic. Naming a fixture “Crome” or “HTS” tests provenance rules only; it does not turn that object into evidence about either real editor. No OEM or editor-generated ROM is required by CI.

### 2. Private PC/oracle validation

Crome and HTS cases remain under `private/oracle/`; reports remain under `private/reports/`. Each series binds the user-declared reference tool, exact version, edition/variant, optional plugins, plugins-disabled state, profile, baseline/no-op/case hashes, manifest/profile digests, analyzer version, collection role, notes, timestamps, and byte ranges. The editor name is provenance supplied by the collector; JSON cannot prove which executable created a file.

Every case preserves three separate values:

1. the engineering value requested in the editor;
2. the engineering value displayed after the saved file is reopened;
3. the exact raw bytes measured in that file.

Repeated observations are retained with their individual paths, hashes, timestamps, and notes. Identical repeats are useful evidence of repeatability but do not increase the number of independent fitting points. Different requested values may legitimately collapse to one raw/displayed value because of quantization. The same requested value producing different raw bytes is an explicit conflict; it is never silently averaged or deduplicated away.

Analysis must:

1. measure every baseline-to-no-op and no-op-to-case relationship separately; never erase bytes by blindly subtracting a union of “normalization” offsets;
2. keep checksum/plugin regions separate from calibration candidates;
3. use at least three independent fitting values for a parameter and keep repeated measurements distinct;
4. test all supported interpretations (u8, signed byte, u16 LE/BE, simple linear, inverse/period, and rounding);
5. report all candidates with training and holdout error rather than only the most attractive one;
6. require an explicit export step for a candidate fragment;
7. never mutate the production profile automatically.

M0.1 refuses candidate inference unless `pluginsDisabled` is true, because a manifest does not describe plugin-owned byte regions well enough to exclude them safely. This flag is necessary but not sufficient: it does not prove the editor has no built-in code/layout transformations.

Cross-editor comparison is valid only when both manifests identify the identical baseline SHA-256, identify different normalized editor tools, pass required provenance/digest/range checks, and contain sufficient independent fit and holdout data. A common candidate means only that the hypothesis sets overlap. Confirmation requires one uniquely validated definition or a proved behavior-equivalent class; all alternatives and unresolved parameters remain visible in the report.

### Fitting and holdout discipline

The fitting set determines coefficient values and the training-compatible rounding-policy set. A holdout case must be declared before analysis and must not refit coefficients or widen the declared tolerance. It evaluates frozen hypotheses, may eliminate alternatives contradicted by its engineering result or exact bytes, and reports its own holdout-compatible rounding subset while preserving the full training-compatible set. For each candidate the report distinguishes:

- independent fitting-point count and free-coefficient count;
- training error;
- independent holdout count and holdout error;
- fitting/observed domain;
- whether a request is interpolation or extrapolation;
- exact expected and observed encoded bytes for every holdout.

Three points can create a three-coefficient inverse candidate with zero training error. That is interpolation, not confirmation. Without a holdout, the result remains a candidate. A holdout must match exact encoded bytes as well as the decoded engineering tolerance; tolerances are declared in advance and are not widened to make a test pass.

The original 6500/7000/7500 RPM and 4000/5000/5500 RPM series are discovery/fitting cases only. Separate holdouts and boundary cases are required. Boundary selection follows the frozen candidate formula, raw domain, rounding discontinuities, and values the editor permits; HondaEcu does not invent a universal numerical step.

### Rounding equivalence domain

HondaEcu retains every compatible rounding-policy name and separately asks whether those policies have identical behavior throughout an explicitly documented encoding-input domain. Agreement at three samples, or only at integer inputs, does not prove equivalence.

- `Floor` and `Truncate` are behaviorally equivalent for finite non-negative inputs, but diverge for negative fractional inputs.
- `Nearest` (midpoints away from zero) and `ToEven` can agree away from half steps yet differ exactly at positive or negative midpoints.
- `Exact` is a separate constraint and is not inferred from integer-only samples.

A read-only candidate may preserve an ambiguous set without choosing the first policy. A confirmed definition needs one rule or a proved behavior-equivalence class over the complete documented domain. If the domain or midpoint behavior is not established, rounding remains ambiguous.

### Byte-accounting model

Reports keep these sets separate:

1. **actual changed bytes** measured directly from the relevant files;
2. **candidate-hypothesis coverage** for every alternative that happens to span changed bytes;
3. **verified-definition coverage** explained by the selected definition after holdout and ambiguity gates;
4. **checksum storage changes** only where checksum identity/evidence is declared;
5. **no-op transformations** measured independently for that exact editor provenance;
6. **unexplained changes** left after verified explanations, not after the union of all candidates.

A correlated side byte therefore remains unexplained merely because some fitted candidate spans it. Likewise, a nearby constant byte may create both u8 and u16 hypotheses without proving width. A parameter may legitimately use multiple related storage locations, but their structure and update rules must be explicit and independently tested.

### Repeated no-op and re-save checks

For each exact editor version and edition/variant, collect at least two independent baseline-to-no-op saves plus a no-op-to-re-save chain. Compare hashes and exact ranges to answer two different questions:

- **determinism:** do independent saves from the same baseline produce identical bytes?
- **stabilization:** after the first transformation, does a further re-save stop changing bytes or enter a repeatable state?

A no-op diff is not automatically an error, checksum, or allowed normalization. Different no-op hashes remain visible. A stable unknown transformation remains unknown. If an editor changes runtime code or layout, document a distinct transformation profile; do not silently treat the native baseline and editor-modified code base as the same compatibility scope.

### Preflight and collection readiness

`oracle preflight` is read-only. It checks local presence and hashes, independent fitting/holdout counts, repeats, reopened/displayed values, no-op determinism/stability, provenance, digests, candidate conflicts, and concrete blockers. Its readiness vocabulary is data-analysis only:

- `collection-incomplete`;
- `candidate-analysis-available`;
- `holdout-validation-available`;
- `cross-editor-comparison-available`.

None means flash-ready. With no private editor files in this repository, the M1 data status is `AwaitingUserFiles`. See [CROME_ORACLE_WORKFLOW.md](CROME_ORACLE_WORKFLOW.md), [HTS_ORACLE_WORKFLOW.md](HTS_ORACLE_WORKFLOW.md), and [M0_1_ORACLE_COLLECTION_CHECKLIST.md](M0_1_ORACLE_COLLECTION_CHECKLIST.md).

Manifest and analysis JSON use the v2 review contract. A stale manifest/profile/file binding blocks validation. Legacy v1 manifests load only with a migration warning and default their cases to `training`; candidate export requires reanalysis against current sources. Serialized `Confidence` remains a compatibility alias for `fitScore`, never a probability. No manifest, analysis, preflight, comparison, or exported review fragment is a production profile or write authorization.

### 3. Static, bench, and vehicle validation

Future static work should pin the exact `asm662`/`dasm662` and Ghidra module revisions, start from separately obtained private ROM bytes, and retain only derived notes permissible for publication—not a complete OEM disassembly. The analyst must show code references that consume the candidate bytes and the exact conversion/branch semantics.

Emulator observations require a pinned emulator revision, command/stimulus, initial ROM hash, output trace hash, and known-model limitations. Emulation and static analysis remain PC-only.

Bench and vehicle levels require separate authorization, hardware procedures, rollback/recovery provisions, logging, conservative limits, and human review. They are out of scope for M0; the application never promotes an M0 result to `BenchCandidate` or above.

## Parameter admission gates

A definition may be documented as a read-only candidate when a public source provides a plausible address but interpretation is incomplete. It becomes writable only when all are true:

1. the offset and width are unambiguous for the exact revision scope;
2. endian and conversion/encoding are known, including one rounding rule or a proved behavior-equivalence class over the entire declared domain;
3. independent editor holdouts match exact encoded bytes and remain within a predeclared tolerance;
4. every actual case change is explained by a verified definition, evidenced checksum storage, or separately scoped no-op transformation;
5. deterministic encode/decode round-trip and boundary tests pass;
6. the profile/manifest digests and all source hashes are current;
7. the profile explicitly marks the definition experimental and a reviewer deliberately enables it.

`public-documentation` alone never satisfies these gates. Conflicting formulas remain `Unsupported` and read-only until resolved.

## Checksum strategy

The PGMFI page identifies a six-byte “Checksum Jump Routine” region at `0x2BAD` and describes a bypass patch. That is not an algorithm description. Until static evidence identifies covered ranges, stored bytes, arithmetic, exclusions, and acceptance behavior—and fixture tests confirm them—the profile uses `ChecksumStatus.Unknown`. HondaEcu neither invents a formula nor disables the routine. Any output with unknown checksum is not flash-ready.

## M0/M0.1 acceptance evidence

M0 is complete at the software level when Release build/tests and format verification pass on Windows and Linux, public tests are synthetic, profiles validate against the checked-in schema, unsafe writes are refused, reports account for every changed byte, and the evidence ledger accurately marks unresolved P28-304 claims as candidates.

M0.1 is complete at the software-contract level when regression tests demonstrate the stricter rounding, repeat, train/holdout, ambiguity, provenance, diff-accounting, no-op, and preflight rules. This validates HondaEcu's behavior against synthetic fixtures only. Local Crome/HTS golden files are private follow-up evidence and are required before M1 can claim real cross-editor results. Until those files exist and pass review, M1 remains `AwaitingUserFiles`; no writable P28-304 scalar, checksum algorithm, emulator result, bench result, or vehicle result is implied.
