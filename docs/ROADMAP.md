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

### M1a–M1j research progress (not M1 completion)

- M1a privately obtained one unchanged archive candidate and traced contextual VTEC thresholds; factory identity and editor import/no-op remain unresolved/not tested.
- M1b delivers a read-only, private-binding-gated threshold inspector and a scoped raw/compact model. Established edge paths, an unresolved normal-path word-add instruction, and separately labelled conditional model agreement remain distinct.
- M1c adds one-slot raw research planning, PC-only copy editing, full-diff verification and parent/plan/report lineage inspection. Targeted manual/opcode checks did not establish the missing live ADD semantics; model status stays unchanged. See [M1c scope and commands](M1C_RAW_THRESHOLD_EDITING.md).
- M1d adds a minimal audited Rust bytecode slice runner, decoded-instruction regressions, strict/conditional execution categories, and lineage-gated baseline/derived threshold comparison. Seeded slices are distinct from full ECU boot or hardware proof. See [M1d scope and results](M1D_BYTECODE_SLICE_VALIDATION.md).
- M1e executes the RAM-only six-word interval producer, preserves its actual T/S into compact execution, and compares downstream baseline/child predicates. The 133978-case finite batch separates 98 strict from 133880 conditional matches, with zero mismatches. Exact instruction-form admission keeps the new er1 ADD permission separate from er3. Timer configuration is source-derived, physical frequency/event geometry remain unknown, and optional rational scaling has no implicit defaults. See [M1e producer, state and scaling evidence](M1E_RPM_PRODUCER_AND_SCALING.md).
- M1f adds a separate, read-only native checksum contract, independent C# calculation, incremental Rust byte execution and CLI/Desktop results. The exact research candidate uses a full-image modulo-256 byte sum with fixed zero residue; no storage offset, repair or bypass is invented. See [M1f scope and actual validation record](M1F_NATIVE_CHECKSUM_VALIDATION.md).
- M1g adds a separate two-change PC-only composition over M1c: one raw threshold plus one computed byte at a privately reviewed exact-baseline CompensationLocation. Static control-flow/data-consumer scope, A/B/C checksum and threshold comparisons, strict native execution before save, and verified original-parent readback remain separate evidence. Legacy raw Save and M1c v1 are unchanged; no generic repair or arbitrary offset is allowed. See [M1g scope, workflow and measured results](M1G_CHECKSUM_PRESERVING_EXPORT.md).
- M1h adds conditional RPM queries and all-256-raw inverse selection for explicit steady normal-interval scenarios. Exact open/closed transition domains, retained ties, separate G/F permissions and query provenance feed existing M1g planning only after explicit raw selection. No hardware defaults, measured RPM claim, new compensation authority or independent writer are added. See [M1h domain, policy and evidence](M1H_CONDITIONAL_RPM_SELECTION.md).
- Physical RPM, independent editor validation and hardware behavior remain unestablished. Scoped software checksum evidence does not authenticate a factory revision or make an image flash-ready. Public profiles remain non-writable; Oracle v2 evidence levels are not promoted by interpreter/model agreement.

M1i adds [stateful capture-sequence validation](M1I_CAPTURE_SEQUENCE_VALIDATION.md):
actual normal acquisition with frozen explicit SFR observations and persistent
per-image CPU/RAM, followed by explicitly scheduled G/F/threshold. An independent
model checks each write/state transition; exact synthetic phases are compared
against the unchanged M1h envelope only after valid fresh warm-up. Verified M1g
child execution uses its own entire image. No timer/IRQ scheduler, GUI change,
new BIN, physical RPM or full ECU boot is introduced.

M1j adds [stateful VTEC software-decision validation](M1J_STATEFUL_VTEC_DECISION.md):
once-seeded per-image CPU/RAM, independent model history, actual ordered gates,
native scheduled counter bodies and distinct request/selection-status outputs.
Strict mode retains a precise SUBB encoding boundary; its specific conditional
permission does not broaden G/F ADD permissions. VTEC-only is validated with raw
software inputs; composed acquisition-to-stateful execution remains NotRun.
The boundary does not establish physical switching, complete M1 or resume GUI r3.

See [M1b contract and limitations](M1B_RPM_CODEC_AND_VTEC_INSPECTOR.md). Missing
ADD semantics, independent editor evidence and hardware validation remain gates.

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

D0 is implemented as a Ukrainian Windows WPF research preview, including raw
table/step graph, one-slot preview/save/verification, M1d/M1e checks and asynchronous
cancellation. M1f extends that existing checks tab with read-only checksum results.
M1g adds explicit reviewed-location preview/export and composed-child lineage,
without silently changing legacy raw Save or promoting a checksum into ECU safety.
M1h adds a conditional RPM scenario/query section and explicit raw-candidate
transfer into the existing M1g plan; mathematical and execution statuses stay separate.
This is not completion of the entire M3 editor milestone or of M1.

## M4 — Additional OBD1 profiles

- additional P28/P30/P72-family profiles
- strict revision identification

Each revision receives explicit evidence and identity rules; similar size or family name is insufficient.

## M5 — P07 research

- P07 main-CPU research
- structural matching P07-303 against P28-304
- P07-specific definitions
- no automatic assumption of compatible offsets
