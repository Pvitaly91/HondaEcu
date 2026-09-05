# Roadmap

Progress through these milestones is evidence-gated. A later milestone does not weaken the ROM handling policy or allow offsets to be copied across revisions.

## M0 — P28-304 core and validation harness

- ROM core
- CLI
- profiles
- diff
- patch reports
- Crome/HTS oracle harness

## M0.1 — Oracle validation hardening and M1 data readiness

- preserve requested, reopened/displayed, and raw observations as separate facts;
- retain repeat provenance, detect contradictory repeats, and recognize quantization without inflating the independent sample count;
- separate fitting/training cases from independent holdout and later boundary cases;
- report model complexity, training error, holdout error, observed range, and extrapolation warnings;
- establish rounding by behavior over a documented domain rather than by requiring one policy name;
- retain alternative offset/width/endian/conversion hypotheses and require a selected, verified definition before bytes count as explained;
- separate actual changes, hypothesis coverage, verified-definition coverage, checksum storage, no-op transformations, and unexplained changes;
- bind analysis to manifest/profile digests, input hashes, analyzer version, selected definition, and user-declared editor provenance;
- evaluate repeated independent no-op saves and re-saves for determinism and stabilization without automatically allowing their transformations;
- provide a read-only oracle preflight and public collection templates while keeping all real ROMs and reports private.

M0.1 hardens the software evidence model. It does not establish any real Crome/HTS behavior, identify a writable P28-304 parameter, validate a checksum, integrate an emulator, or make a ROM flash-ready.

## M1 — First cross-editor-verified scalars

- data gate: `AwaitingUserFiles` until controlled private Crome and HTS collections exist for the exact same baseline;
- cross-editor verified P28-304 rev limiter
- cross-editor verified VTEC crossover
- verified checksum, or a clearly documented blocked status

The original 6500/7000/7500 RPM and 4000/5000/5500 RPM series remain discovery inputs. M1 also requires separate holdouts and formula-dependent boundary cases, stable and explained editor transformations, and an unambiguous or behaviorally equivalent verified definition. No discovery fit is promoted automatically.

### M1a / M1b / M1c / M1d research progress (not M1 completion)

- M1a privately obtained one unchanged archive candidate and traced contextual VTEC thresholds; factory identity and editor import/no-op remain unresolved/not tested.
- M1b delivers a read-only, private-binding-gated threshold inspector and a scoped raw/compact model. Established edge paths, an unresolved normal-path word-add instruction, and separately labelled conditional model agreement remain distinct.
- M1c adds one-slot raw research planning, PC-only copy editing, full-diff verification and parent/plan/report lineage inspection. Targeted manual/opcode checks did not establish the missing live ADD semantics; model status stays unchanged. See [M1c scope and commands](M1C_RAW_THRESHOLD_EDITING.md).
- M1d adds a minimal audited Rust bytecode slice runner, decoded-instruction regressions, strict/conditional execution categories, and lineage-gated baseline/derived threshold comparison. Seeded slices are distinct from full ECU boot or hardware proof. See [M1d scope and results](M1D_BYTECODE_SLICE_VALIDATION.md).
- Physical RPM, independent editor validation, checksum validation and hardware behavior remain unestablished. Public profiles remain non-writable; Oracle v2 evidence levels are not promoted by interpreter/model agreement.

See [M1b contract and limitations](M1B_RPM_CODEC_AND_VTEC_INSPECTOR.md). The next narrow research gate is the missing instruction semantics, not an editor installation or another preparation framework.

## M2 — Calibration maps

- low/high-cam fuel maps
- low/high-cam ignition maps
- RPM/MAP axes
- one-cell and full-table validation

## M3 — Desktop GUI

- desktop GUI
- table and graph views
- undo/redo
- patch preview

The GUI must use `HondaEcu.Core` and must not duplicate encoding, identity, patch, or verification logic.

## M4 — Additional OBD1 profiles

- additional P28/P30/P72-family profiles
- strict revision identification

Each revision receives explicit evidence and identity rules; similar size or family name is insufficient.

## M5 — P07 research

- P07 main-CPU research
- structural matching P07-303 against P28-304
- P07-specific definitions
- no automatic assumption of compatible offsets
