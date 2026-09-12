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

### M1a–M1t research progress (not M1 completion)

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
software inputs; composed acquisition-to-stateful execution was NotRun in M1j.
The boundary does not establish physical switching, complete M1 or resume GUI r3.

M1k completes the bounded [integrated capture-to-VTEC chain](M1K_INTEGRATED_CAPTURE_TO_VTEC.md):
actual acquisition → G → F → persistent VTEC decision on one CPU/RAM/P1 lifetime,
with explicit native counter-body scheduling and independent full-chain model
history. The headless command checks A/original, B/threshold-only in memory and
C/verified M1g child, including state and side effects. Permission-local and
cumulative outcomes, terminal suffixes and partial non-comparable pairs remain
separate. Physical RPM, hardware/full boot and GUI r3 acceptance remain NotRun;
no new export, calibration, emulator framework or scheduler claim is added.

M1l completes the isolated [rev-limiter discovery and cut/resume validation](M1L_REV_LIMITER_VALIDATION.md):
the exact period-word decision path, fixed/RAM threshold structure and native
channel-mask consumer before P2 are established. Read-only inspection, persistent
byte execution, independent C# history and single-word in-memory A/B mutations
are delivered separately from the completed M1k chain. Earlier combined gates,
adaptive threshold production, full scheduling and electrical pulses remain
outside this execution contract. Limiter export is not enabled; M1, physical RPM,
cross-editor/hardware verification and GUI r3 acceptance remain incomplete.

M1m completes the bounded [adaptive limiter producer integration](M1M_ADAPTIVE_LIMITER_THRESHOLDS.md):
actual threshold production and selected native counter iterations precede the
existing limiter/consumer on one persistent CPU/RAM. Separate C# histories check
actual table words, gates, ordered stores, threshold selection and downstream
mask updates. Both table banks and all recovered reset/update/hold paths have
targeted private evidence. M1l remains closed; no acquisition integration,
physical period, full scheduler, limiter export, GUI or hardware claim is added.

See [M1b contract and limitations](M1B_RPM_CODEC_AND_VTEC_INSPECTOR.md). Missing
ADD semantics, independent editor evidence and hardware validation remain gates.

M1n adds [fixed-context limiter export](M1N_FIXED_LIMITER_EXPORT.md): separate
versioned operand admission plus the unchanged reviewed compensation definition,
actual-byte sum8 compensation, mandatory independent A/B/C native histories,
RAM-only adaptive controls, three-file publication and original-parent readback.
No adaptive editing, new signing authority, physical RPM, GUI or hardware acceptance.
M1l/M1m remain completed; this does not complete overall M1.

M1o adds [single-bank adaptive base-pair export](M1O_ADAPTIVE_BASE_EXPORT.md):
code-owned disjoint words, finite no-wrap/target-order checks, separate numeric
edit audit, unchanged compensation authority, mandatory stateful native A/B/C
producer/limiter/consumer and checksum, protected publication and derived readback.
Origins/coefficients, other bank and fixed pair remain unchanged. Base words are
not constant current RAM thresholds or physical RPM. M1m/M1n remain completed;
hardware, full boot and GUI are explicitly excluded from this software stage.

M1p adds [combined limiter-group export](M1P_COMBINED_LIMITER_EXPORT.md): all seven
explicit nonempty selections of fixed/bank0/bank1, unchanged per-group arithmetic
policy and one compensation computed from combined bytes of one original parent.
Mandatory M1l/M1m/M1f A/B/C execution includes persistent context switches,
dependency-aware controls and a decision witness for every effectively changed
group. Publication requires fresh capability, new BIN/plan/receipt and independent
readback. M1m/M1n/M1o remain closed; old formats and location authority unchanged.
No GUI, hardware, physical RPM, coefficients or wider calibration scope is added.

M1q adds [idle-target discovery and byte-executed validation](M1Q_IDLE_TARGET_VALIDATION.md):
one exact raw-context packed-table producer, actual target-to-period-error
consumer, independent stateful C# model and read-only inspection/check CLI.
The private 858-checkpoint strict series includes the full supported byte-axis
domain, history/clamp boundaries and a local one-cell in-memory A/B witness.
No idle editing, BIN, checksum repair or export authority is added. M1p remains
closed; physical RPM, hardware, full boot and GUI acceptance are not implied.

M1r adds [idle-target contexts and overrides](M1R_IDLE_TARGET_CONTEXTS.md):
separate native source selection, two packed tables, low-domain immediate
overrides, persistent counter/history gates and independently stored027A.
The final025C feeds the unchanged error/sign consumer on shared native RAM.
104094 new-task checkpoints match; 612 fresh M1q subset pairs also match full
observations. Two understood but unreachable3099 branch arms are not counted
as dynamically covered. Selector updates are masked upstream software inputs,
not native physical mode transitions; counter expiration and scheduler remain
outside scope. No idle editor, export, BIN or GUI changes are added.

M1s adds [idle-target table export](M1S_IDLE_TABLE_EXPORT.md): base/late/both explicit
numeric selections, a separate closed fourteen-word contract and one existing
checksum compensation from a single original. Arithmetic domain checks and fresh
mandatory A/B/C idleContexts/checksum batches remain separate; combined-image
table witnesses and masking summaries gate typed publication capability. CLI
plan/apply/verify/inspect, one private BIN and independent readback are complete.
No axes/overrides/peaks, mixed VTEC/limiter lineage, new signing authority, physical
RPM, GUI or hardware scope is added. M1q/M1r and previous milestones stay closed.

M1t adds [unified basic-calibration export](M1T_BASIC_CALIBRATION_EXPORT.md): one
VTEC threshold, explicit fixed/adaptive pairs and base/late idle values compose
from one original with one checksum compensation. Separate strict local native
suites run the actual combined images, with per-family witnesses and one M1f
checksum batch. The closed original-parent plan/receipt, new-path publication
and historical verification do not integrate a full ECU scheduler or authorize
hardware use. M1s and earlier contracts remain closed and unchanged; physical
RPM and GUI r3 remain unavailable/NotRun.

## M2 — Calibration maps

- low/high-cam fuel maps
- low/high-cam ignition maps
- RPM/MAP axes
- one-cell and full-table validation

M2a adds [fuel-map structure and native lookup validation](M2A_FUEL_MAP_VALIDATION.md):
two exact-parent 20×10 unsigned row-major maps, a shared raw load axis, separate
raw RPM axes, per-column multipliers, native cached Q16 position production and
ROM-owned `DATA0127.1` selection. A bounded same-CPU/RAM runner and independent
C# history match 1,050 actual checkpoints and read all 400 cells. Separate
one-byte in-memory mutations for both contexts change the native lookup and its
`DATA0140` software consumer, with opposite-context controls. This is read-only
research: no BIN/export/checksum repair, physical units, ignition maps, hardware,
full boot, GUI change, or completion of all M2/M1 is implied.

M2b adds [fuel-map cell checksum-preserving export](M2B_FUEL_MAP_EXPORT.md): a
closed settings schema selects up to 400 code-owned numeric bytes from either
or both maps while axes, multipliers, selector/gates and every other byte remain
immutable except the existing reviewed compensation location. Each map gets a
65,536-input integer audit; mandatory A/B/C native lookup histories cover all
342 rectangles and 400 cells, followed by one full checksum batch. Typed
capability, new-path BIN/plan/receipt publication and original-parent readback
remain PC-only. M2a stays closed; ignition maps, physical units, GUI, hardware,
full boot and completion of all M2 remain outside scope.

M2c adds [ignition-map structure and native lookup validation](M2C_IGNITION_MAP_VALIDATION.md):
two exact-parent primary 20×10 unsigned row-major maps, the shared raw load
axis, separate raw RPM axes, ROM-owned `DATA0227.5` selection and the
no-column-metadata entry of the shared interpolation helper. Native axes,
source selection, direct cell reads and the immediate `DATA0248` consumer
match an independent persistent C# model for all 400 cells and every reachable
primary interval. Separate one-byte in-memory A/B children provide lookup and
consumer witnesses for both contexts. Physical degrees/RPM, alternate maps,
downstream corrections, ignition export, GUI, hardware and full boot remain
outside scope; completion of all M2 or independent M1 gates is not implied.

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

### D1 — Unified basic-calibration desktop workspace

[D1](D1_BASIC_CALIBRATION_DESKTOP.md) integrates completed M1t Core contracts into
the existing Ukrainian WPF window: six independent raw groups, settings import/
export, original-parent preview and exact diff, Core-generated model graphs,
fresh validation/publication/readback and read-only child inspection. It retains
legacy tools and the shared session/job/cancellation mechanism. Synthetic tests,
offscreen bindings/layout, real subprocess and private real-ROM service evidence
are distinct from interactive GUI acceptance (NotRun). No new calibration fields,
physical RPM proof, hardware writes or full-ECU integration are implied.

## M4 — Additional OBD1 profiles

- additional P28/P30/P72-family profiles
- strict revision identification

Each revision receives explicit evidence and identity rules; similar size or family name is insufficient.

## M5 — P07 research

- P07 main-CPU research
- structural matching P07-303 against P28-304
- P07-specific definitions
- no automatic assumption of compatible offsets
