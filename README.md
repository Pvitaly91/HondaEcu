# HondaEcu

HondaEcu is a cross-platform, profile-driven ROM inspection and controlled-editing toolkit. Milestone M0 establishes a safety-first core and desktop validation harness for one explicitly scoped target: the 32 KiB P28-304 Honda OBD1 ROM revision. M0.1 hardens how the oracle harness distinguishes observations, fitted hypotheses, and independent validation before any real P28-304 definition can advance toward M1.

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

No real Crome or HTS golden files are present in the repository; the tracked `private/` directories contain only `.gitkeep` placeholders. The current M1 data status is **`AwaitingUserFiles`**. Synthetic tests exercise analyzer rules only; they do not prove Crome, HTS, P28-304, checksum, emulator, bench, or vehicle behavior. M0.1 does not implement M1 or emulator integration.

## Build and test

Install a .NET 8 SDK, then run:

```shell
dotnet restore
dotnet build --configuration Release --no-restore
dotnet test --configuration Release --no-build
dotnet format --verify-no-changes
```

Run the CLI from source with `dotnet run --project src/HondaEcu.Cli --`, or invoke the built `hondaecu` executable.

## CLI examples

```shell
hondaecu inspect private/roms/p28-304.bin
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
