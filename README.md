# HondaEcu

The [D1 basic-calibration desktop workspace](docs/D1_BASIC_CALIBRATION_DESKTOP.md)
integrates the completed M1t six-group workflow into the Ukrainian WPF application:
explicit original inputs, raw draft/settings, preview/diff/graphs, fresh validation
and one PC-only copy, followed by read-only M1t child inspection. Legacy tools
remain available. Headless/offscreen checks are not interactive GUI acceptance;
D1 GUI acceptance remains NotRun and outputs remain NotFlashReady.

HondaEcu is a cross-platform, profile-driven ROM inspection and controlled-editing toolkit. Milestone M0 establishes a safety-first core and desktop validation harness for one explicitly scoped target: the 32 KiB P28-304 Honda OBD1 ROM revision. M0.1 hardens how the oracle harness distinguishes observations, fitted hypotheses, and independent validation before any real P28-304 definition can advance toward M1.

M2a adds [read-only fuel-map inspection and native lookup validation](docs/M2A_FUEL_MAP_VALIDATION.md)
through `research p28-fuel maps-inspect|lookup-check`. M2b adds the separate
[checksum-preserving fuel-map cell export](docs/M2B_FUEL_MAP_EXPORT.md) through
`research p28-fuel export plan|apply|verify|inspect`: explicit u8 cells from one
exact original, unchanged axes/multipliers/gates, full per-map arithmetic audit,
fresh strict A/B/C lookup/checksum execution, and one private BIN/plan/receipt
with readback. Physical units, ignition maps, hardware/full boot and GUI work
remain outside M2b; M2 is not complete.

The project starts with P28-304 because public research material names `304stock.bin` as the basis of the available P28 map, making revision scope explicit enough for reproducible investigation. Published offsets remain research leads, not universal P28 facts. P07 main-CPU research is the next major family direction after the P28/P30/P72 workflow is proven; no P28 offsets will be assumed compatible with P07.

## M0 and M0.1 status

M0 provides:

- an immutable in-memory ROM model with SHA-256 and CRC32;
- declarative, versioned ROM profiles and controlled encodings;
- inspection, profile validation, read, diff, patch, round-trip, and verification commands;
- JSON diff and patch reports with exact changed offsets;
- Crome and Honda Tuning Suite golden-file/oracle analysis;
- conservative checksum and flash-readiness reporting;
- deterministic synthetic-ROM tests on Windows and Linux.

The included P28-304 definition is explicitly experimental. Public documentation alone does not make a parameter safe to write. This project does **not** yet produce ROMs validated for use in a vehicle.

M0.1 adds stricter evidence accounting:

- requested editor values, values displayed after reopening, and raw ROM bytes remain distinct observations;
- repeated and quantized observations retain provenance, while only independent points count toward fitting;
- fitting cases and holdout cases have separate error reporting, so an exact three-point fit is not treated as confirmation;
- rounding policies are compared by behavior over an explicit domain, including negative values and midpoint cases where applicable;
- actual changed bytes, candidate-hypothesis coverage, verified-definition coverage, checksum changes, no-op transformations, and unexplained bytes are reported separately;
- repeated independent no-op saves and re-saves can be checked for determinism and stabilization;
- editor version, edition/variant, options, and file hashes are provenance declared by the user, not proof that a named editor produced a file;
- `oracle preflight` reports whether the private collection is ready for analysis without modifying a ROM.

No real Crome or HTS golden files are present in the repository; the tracked `private/` directories contain only `.gitkeep` placeholders. M1 still awaits real editor observations. In M1a, one archive baseline candidate was obtained privately and a partial VTEC static investigation was performed; native revision identity and editor import/no-op behavior remain unverified. See [M1a real-ROM findings](docs/M1A_REAL_ROM_FINDINGS.md). Synthetic tests exercise analyzer rules only; they do not prove editor or ECU behavior. Neither M0.1 nor M1a completes M1 or implements an emulator.

M1b adds a [read-only VTEC threshold inspector and scoped compact-code research model](docs/M1B_RPM_CODEC_AND_VTEC_INSPECTOR.md). A private exact-byte/profile binding is required for candidate-specific interpretation; `--confirm-profile` alone cannot identify a baseline. Established raw edge paths are separated from an unresolved normal-path instruction and its explicitly conditional mathematical model. Physical RPM remains unavailable. This does not complete M1 or enable real P28 writes.

M1c adds [one-slot PC-only raw threshold plan/apply/verify and derived-file lineage inspection](docs/M1C_RAW_THRESHOLD_EDITING.md). The targeted ADD investigation did not promote the compact model. Research edits require the original private binding and create only new private files; they are not RPM settings, checksum-valid ROMs, or ECU-ready outputs. Public P28 definitions remain non-writable.

M1d adds [bounded byte-executed slice validation](docs/M1D_BYTECODE_SLICE_VALIDATION.md): one audited Rust CPU runner and a thin C# process adapter, with strict unresolved-instruction stops and explicitly conditional ADD results. It does not boot an ECU, prove hardware behavior, establish physical RPM, or complete M1. Third-party component licenses/notices are listed separately in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md); no root license is selected.

M1e adds [RPM producer execution and explicit scaling analysis](docs/M1E_RPM_PRODUCER_AND_SCALING.md) through `research p28-vtec producer-check`. Six interval-derived words feed actual G → compact F → threshold execution, checked against independent integer models. The private 133978-case batch has 98 strict matches and 133880 separately conditional matches, with no mismatches; strict mode stops the latter as unresolved. The source-derived timer selector is CLK/32, but board frequency/event geometry remain unknown. Optional rational preview requires explicit assumptions, never enables `physicalRpmAvailable`, and does not complete M1 or make a ROM flash-ready.

M1i adds [stateful capture-sequence validation](docs/M1I_CAPTURE_SEQUENCE_VALIDATION.md)
through the headless `research p28-vtec acquisition-check` command. Actual normal
capture code maintains its sample history, then optionally feeds actual G/F/
threshold execution. Explicit frozen peripheral snapshots and caller scheduling
are not a timer/IRQ simulator. Independent per-event comparison and unchanged
M1h steady-envelope checks preserve strict/conditional/NotRun distinctions.
Verified M1g child sequences execute the child's own bytes. No new BIN, physical
RPM claim or GUI acceptance is implied; GUI r3 remains paused.

M1j adds [stateful VTEC software-decision validation](docs/M1J_STATEFUL_VTEC_DECISION.md)
through `research p28-vtec state-check`. Prior predicates, counters and request/status
history persist across actual ROM calls; an independent C# model checks every
transition and executed gate. VTEC-only uses explicit raw compactCode. A specific
SUBB encoding discrepancy remains strict-unresolved or explicitly conditional.
The boundary is software output data, not physical VTEC; M1i/M1h semantics and
GUI r3 paused/NotRun are unchanged.

M1k adds the mandatory [integrated capture-to-VTEC software chain](docs/M1K_INTEGRATED_CAPTURE_TO_VTEC.md)
through headless `research p28-vtec chain-check`. Actual acquisition → G → F →
persistent decision share one CPU/RAM/P1 latch per image sequence; Code, samples,
T and prior/request state cannot be supplied per event. A separate C# history
checks every boundary, ordered byte/word store and native gate. Baseline A,
in-memory threshold-only B and fully admitted M1g child C execute their own bytes.
Three exact-form permissions retain cumulative conditional history and terminal
NotRun suffixes. This completes the bounded software integration, not full M1,
physical ECU validation or GUI acceptance; no new BIN/export is introduced.

M1l adds [exact-bound rev-limiter inspection and stateful validation](docs/M1L_REV_LIMITER_VALIDATION.md)
through separate headless `research p28-limiter inspect|check` commands. The
unsigned period-word cut/resume path executes together with its native channel
mask consumer; independent C# histories verify operands, branches and ordered
writes. Separate in-memory word mutations move actual boundaries. Adaptive RAM
threshold production and surrounding scheduling remain explicit dependencies.
M1k stays closed; this second research parameter does not complete M1, enable
limiter export, establish physical RPM or resume GUI r3. No new BIN is produced.

M1m adds [adaptive limiter threshold production and integration](docs/M1M_ADAPTIVE_LIMITER_THRESHOLDS.md)
through headless `research p28-limiter adaptive-check`. Actual adaptive producer,
native counter-body calls, limiter decision and mask consumer share persistent
CPU/RAM; the independently modeled words are never injected into native RAM.
Both banks, reset/update/hold paths and raw integer boundaries are covered by
1,530 strict private matches. M1l stays closed; physical RPM, full boot,
hardware and GUI remain outside scope. No limiter export or new BIN is enabled.

M1n adds [fixed-context checksum-preserving limiter export](docs/M1N_FIXED_LIMITER_EXPORT.md)
through headless `research p28-limiter export plan|apply|verify|inspect`.
Only the two established little-endian immediate operands and the separately
reviewed compensation location are admitted; adaptive tables remain unchanged.
Apply requires fresh strict A/B/C limiter, adaptive-control and native checksum
execution before new-path BIN/plan/receipt publication and independent readback.
This is PC-only original-parent research export, not physical RPM or flash readiness.
M1l/M1m remain closed and GUI r3 remains paused/NotRun.

M1o adds [single-bank adaptive-base export](docs/M1O_ADAPTIVE_BASE_EXPORT.md)
through `research p28-limiter adaptive-export plan|apply|verify|inspect`.
One explicit bank and its two numeric base words are admitted, not coefficients,
origins, both banks or a constant RPM limiter. Full unsigned-domain target checks
and fresh strict native producer/limiter/checksum A/B/C histories precede the
shared new-path writer and independent original-parent readback. M1m/M1n remain
completed; GUI r3 stays paused/NotRun and hardware remains outside scope.

M1p adds [combined limiter-group export](docs/M1P_COMBINED_LIMITER_EXPORT.md)
through `research p28-limiter combined-export plan|apply|verify|inspect`.
An explicit settings file selects any nonempty subset of fixed/bank0/bank1 pairs.
All words compose from one original with one final-byte-sum compensation, followed
by fresh combined native histories, per-changed-group witnesses, checksum and
independent three-file readback. No synchronization, child chains or RPM claims.
Old M1n/M1o/M1g contracts remain unchanged; GUI r3 stays paused/NotRun.

M1q adds [scoped idle-target inspection and native validation](docs/M1Q_IDLE_TARGET_VALIDATION.md)
through read-only `research p28-idle inspect|target-check`. One explicit raw
context executes a packed-table target producer and its immediate unsigned
period-error/sign/clamp consumer on the same CPU/RAM, checked against independent
per-image C# histories. Private testing gives 858 strict matching checkpoints
and a one-cell in-memory A/B effect. No firmware BIN or idle export is created;
physical RPM remains unavailable, M1p stays closed, and GUI r3 stays paused/NotRun.

M1r adds [idle-target context, override and component validation](docs/M1R_IDLE_TARGET_CONTEXTS.md)
through headless `research p28-idle contexts-inspect|contexts-check`. The native
producer selects between two packed sources and low-domain immediate overrides,
stores a separate component, and passes its actual final target to the existing
error/sign consumer. Independent model histories match 104094 private checkpoints;
612 fresh old/new pairs preserve every established M1q observation. Full selector
byte-domain sweeps are software snapshots, not physical mode claims. No BIN,
idle export, GUI change or physical RPM authority is introduced.

M1s adds [idle-target table checksum-preserving export](docs/M1S_IDLE_TABLE_EXPORT.md)
through `research p28-idle export plan|apply|verify|inspect`: explicit base/late/both
selection, fourteen code-owned numeric words, unchanged axes/overrides/peaks and
one existing compensation from combined bytes of one original. Fresh per-image
idleContexts/checksum execution and table witnesses gate new-path publication.
Readback and derived inspection preserve full original-parent lineage. This is raw
PC-only export, not physical RPM, a complete idle controller or ECU-write authority.
GUI r3 remains paused/NotRun; M1q/M1r and older export contracts are unchanged.

M1t adds [unified basic-calibration research export](docs/M1T_BASIC_CALIBRATION_EXPORT.md)
through `research p28-calibration export plan|apply|verify|inspect`: six explicit
groups from one original, one actual-byte checksum compensation and a separate
closed contract. Fresh VTEC raw-prefix, limiter/adaptive and idle suites execute
the same full A/B/C images independently; one checksum batch and per-family
witnesses gate new BIN/plan/receipt publication. This is not a common ECU main
loop, physical RPM or flash readiness. Old formats remain unchanged; GUI r3,
VTEC full-chain/P1, hardware and full boot remain NotRun for this workflow.

## Windows Desktop Research Preview — D0

D0 adds a Ukrainian WPF window over the existing Core and Rust process adapter;
it is an implemented PC-only research preview, not a finished tuning editor or completion of M1 or M3.
The permanent status is «Дослідницький режим. Не для запису в ECU».

On Windows, build a portable folder with PowerShell 7:

```powershell
./scripts/publish-desktop.ps1
```

Double-click `artifacts/desktop/win-x64/HondaEcu.Desktop.exe`. Keep the entire
folder together: the self-contained .NET runtime, `definitions/`, `tools/` and
component notices are required. The target machine does not need .NET SDK, Rust,
Cargo, Git or the source repository. Publishing requires the .NET 8 SDK selected
by `global.json`, Rust 1.85.1 and MSVC x64 build tools. Existing publication folders
are refused; choose a new `-OutputPath artifacts/desktop/win-x64-next` for a later build.

For source development on Windows:

```powershell
dotnet restore HondaEcu.Windows.sln
dotnet build HondaEcu.Windows.sln --configuration Release --no-restore
dotnet test HondaEcu.Windows.sln --configuration Release --no-build
dotnet run --project src/HondaEcu.Desktop/HondaEcu.Desktop.csproj --configuration Release
```

Start with «Демонстраційний режим»: invented thresholds demonstrate one-slot raw
preview, exact in-memory diff, a step graph and cancel without an OEM ROM or a
fabricated binding. Demo cannot save a Honda firmware or execute real ROM slices.
«Відкрити BIN» opens an unknown file read-only. Explicitly select your current
private original binding and research profile to unlock scoped baseline work;
an existing child additionally needs original parent, plan and patch report.
No private files are searched for automatically.

The window provides one raw-byte plan (decimal integer 0–255), new PC-only
copy/plan/report publication with readback verification, M1d/M1e checks, cancellation
and structured current-job results. Strict execution is the default; permitted and
actually used ADD assumptions remain distinct. With no runner, reading/demo/diff
and preview still work; choose your built executable explicitly with «Обрати Rust
runner…». The packaged version uses `tools/p28-slice-runner.exe` beside the app.
M1f adds [read-only native checksum research](docs/M1F_NATIVE_CHECKSUM_VALIDATION.md)
and «Перевірити штатну checksum» in the existing checks tab. Scoped byte-sum
arithmetic, stateful original-byte execution, coverage and evidence are separate;
missing runner means execution NotRun, and demo has no native Honda checksum.
M1f does not repair/bypass the check or change checksum during legacy raw Save. Physical RPM and ECU/hardware behavior remain unconfirmed;
all copies are `PcInspectionOnly / NotFlashReady`.
See [D0 usage, packaging and validation limits](docs/D0_DESKTOP_PREVIEW.md).

M1g adds a separate [checksum-preserving PC-only research export](docs/M1G_CHECKSUM_PRESERVING_EXPORT.md):
one existing threshold edit plus one computed byte at the privately reviewed,
exact-baseline-scoped CompensationLocation. It retains the enabled native check,
requires strict complete byte execution before publication, and verifies the full
two-byte diff and original-parent lineage. Signed review identity does not replace
the static non-interference audit or prove ECU safety. Legacy raw Save stays
unchanged; no arbitrary-offset or repair-any-ROM command is added. Use a new
portable path such as `artifacts/desktop/win-x64-m1g`; never replace D0/M1f.

M1h adds [conditional RPM preview and inverse threshold selection](docs/M1H_CONDITIONAL_RPM_SELECTION.md)
for an explicit uniform steady normal-interval scenario. It reuses scaling,
producer G, compact F and the selected one-step predicate; all 256 raw thresholds
are considered with exact rational transition endpoints and a documented minimax
policy that retains ties. No hardware quantities are defaulted, strict model mode
is the default, and er1/er3 permissions remain independent. A chosen raw requires
explicit confirmation and existing M1g planning/export admission; the RPM preview
itself writes only a new private report. Conditional calculations and strict
checksum results remain distinct, with `physicalRpmAvailable: false` and
`PcInspectionOnly / NotFlashReady` unchanged.

## Build and test

Install a .NET 8 SDK and Rust toolchain 1.85.1, then run (the .NET integration tests require the built Rust executable):

```shell
dotnet restore HondaEcu.sln
cargo +1.85.1 build --release --locked --manifest-path rust/p28-slice-runner/Cargo.toml
cargo +1.85.1 test --release --locked --manifest-path rust/p28-slice-runner/Cargo.toml
dotnet build HondaEcu.sln --configuration Release --no-restore
dotnet test HondaEcu.sln --configuration Release --no-build
dotnet format HondaEcu.sln --verify-no-changes --no-restore
```

Run the CLI from source with `dotnet run --project src/HondaEcu.Cli --`, or invoke the built `hondaecu` executable.

## CLI examples

```shell
hondaecu inspect private/roms/p28-304.bin
hondaecu research p28-vtec inspect private/oracle/p28-304/base.bin --profile p28-304 --confirm-profile --baseline-binding private/reports/m1b/baseline-binding.json --output private/reports/m1b/vtec-inspection.json
hondaecu diff base.bin modified.bin --output private/reports/diff.json --max-ranges 50
hondaecu profile list
hondaecu profile show p28-304
hondaecu profile validate definitions/p28/p28-304.experimental.json
hondaecu read private/roms/p28-304.bin --profile p28-304
hondaecu patch private/roms/input.bin --profile p28-304 --set PARAMETER=VALUE --output private/roms/output.bin --report private/reports/output.patch.json --confirm-profile --allow-unverified
hondaecu roundtrip input.bin --profile p28-304
hondaecu verify private/roms/output.bin --profile p28-304 --patch-report private/reports/output.patch.json --baseline private/roms/input.bin
```

Unknown ROMs are rejected for patching by default. An explicit profile selects the interpretation but does not silently turn a size-only match into a trusted identity. Candidate or otherwise unverified parameters also require `--allow-unverified`.

The patch line is a syntax template, not a runnable P28-304 edit. The M0 P28-304 profile intentionally has no writable entries and does not define `rev_limit_rpm`; that parameter remains blocked until M1 evidence supports an offset, conversion, and rounding rule.

## Crome and HTS oracle workflow

Crome and Honda Tuning Suite are independent reference oracles, not absolute sources of truth. Both editor collections must start from byte-identical copies of one unchanged baseline. For each exact editor version and edition/variant, make repeated independent no-op saves and a re-save of a no-op, record all hashes, and investigate whether any transformation is deterministic or stabilizes. A stable transformation remains an observation; it is not automatically a checksum change or an allowed code-base rewrite.

Create single-parameter discovery cases, repeated observations, independent holdout cases, and later boundary cases. The initial 6500/7000/7500 RPM and 4000/5000/5500 RPM series are discovery cases only. Holdouts must not participate in coefficient fitting, and boundary points depend on the candidate formula and values the editor actually permits—there is no universal Honda boundary step. Analyze the private collection locally:

```shell
hondaecu oracle create-manifest --tool Crome --tool-version VERSION --tool-edition EDITION_OR_VARIANT --profile p28-304 --baseline private/oracle/p28-304/base.bin --noop private/oracle/p28-304/crome-noop-a.bin --independent-noop private/oracle/p28-304/crome-noop-b.bin --resaved-noop private/oracle/p28-304/crome-noop-a-resave.bin --output private/reports/crome-oracle.json --plugins-disabled
hondaecu oracle add-case --manifest private/reports/crome-oracle.json --parameter rev_limit_rpm --value 6500 --displayed-value DISPLAYED_VALUE_AFTER_REOPEN --role training --observation-id crome-rev-6500-training-1 --rom private/oracle/p28-304/crome-rev-6500-training-1.bin
hondaecu oracle preflight --manifest private/reports/crome-oracle.json --output private/reports/crome-preflight.json
hondaecu oracle analyze --manifest private/reports/crome-oracle.json --output private/reports/crome-analysis.json
hondaecu oracle compare --crome private/reports/crome-oracle.json --hts private/reports/hts-oracle.json --output private/reports/cross-editor.json
```

See [the Crome workflow](docs/CROME_ORACLE_WORKFLOW.md), [the HTS workflow](docs/HTS_ORACLE_WORKFLOW.md), [the collection checklist](docs/M0_1_ORACLE_COLLECTION_CHECKLIST.md), [the unpopulated v2 manifest template](docs/templates/oracle-manifest.m0-1.json.template), and [the validation strategy](docs/VALIDATION_STRATEGY.md) before producing cases. A candidate is never promoted into a production profile automatically.

`--value` records what you requested in the editor; `--displayed-value` records what the same editor shows after reopening the saved file. Raw bytes are measured from the ROM and are not interchangeable with either value. Identical repeats do not create additional independent fitting points, quantized requested values may legitimately map to the same raw/displayed pair, and contradictory repeats remain explicit conflicts rather than being averaged away.

Use `--role holdout` for cases withheld from fitting. A repeatable `--rounding-domain PARAMETER=MINIMUM:MAXIMUM` plus `--domain-evidence TEXT` records a continuous **unrounded raw-input** interval; it is never inferred from the extrema of training samples. Optional `--transformation-profile ID` records a claimed editor transformation profile only—it does not authorize bytes or upgrade compatibility. Candidate selection options require a reason, preserve all alternatives, and contribute no new evidence.

## Private ROM policy

OEM ROMs and ROMs saved by Crome or HTS must never be committed. Store them only under ignored `private/` directories. The repository also ignores common ROM, disassembly, trace, and reverse-engineering database formats.

Safety invariants:

1. An input ROM is never modified in place.
2. Output always goes to a distinct new path and every patch produces a JSON report.
3. A 32,768-byte size alone never identifies a ROM as P28-304; use a hash, signatures, or explicit user confirmation.
4. A file checked only on a PC is not flash-ready.
5. Checksum bypass is never applied automatically.
6. Do not raise the rev limit for a first hardware test.
7. Public Git must not contain OEM code, complete ROM disassembly, or Crome/HTS-generated binaries.

The full policy is in [ROM_HANDLING_POLICY.md](docs/ROM_HANDLING_POLICY.md).

## Roadmap

- **M0:** core, CLI, profiles, diff/patch reports, and editor oracle harness.
- **M0.1:** behavioral rounding equivalence, repeat/quantization handling, train/holdout separation, candidate ambiguity, diff-accounting hardening, provenance binding, no-op stability checks, and private-data preflight.
- **M1:** cross-editor verification of P28-304 rev limiter and VTEC crossover, plus a verified checksum or an explicit blocked finding.
- **M2:** fuel/ignition tables and axes with one-cell and full-table validation.
- **M3:** desktop GUI using `HondaEcu.Core`, with table/graph views, undo/redo, and patch preview.
- **M4:** additional strictly identified P28/P30/P72-family profiles.
- **M5:** P07 research and P07-specific definitions without assumed offset compatibility.

See [ROADMAP.md](docs/ROADMAP.md) for milestone details and [P28_304_EVIDENCE.md](docs/P28_304_EVIDENCE.md) for source provenance and open questions.

No license has been selected. Licensing remains an explicit decision for the repository owner.

The D0 portable package can also be checked with
`./scripts/test-desktop-portable.ps1`. It runs an explicit no-window resource
diagnostic outside the repository with another working directory and no developer
tools on PATH; it is separate from the actual synthetic WPF GUI smoke recorded
in [the D0 validation report](docs/D0_DESKTOP_PREVIEW.md#validation-record-and-limits).
