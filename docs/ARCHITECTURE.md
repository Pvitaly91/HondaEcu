# HondaEcu architecture

## Scope

M0 is a cross-platform .NET 8 library and command-line validation harness for raw 32 KiB Honda OBD1 ROM images. Its first research target is the specific community-labelled **P28-304** code base. The design deliberately separates byte handling, identity, calibration definitions, validation evidence, and user interfaces so later P28/P30/P72-family work—and eventually P07 research—does not spread revision-specific offsets through application code.

M0 is not a complete calibration editor, a flasher, an ECU emulator, or a claim that any generated image is safe for a vehicle.

## Components and dependency direction

| Component | Responsibility | May depend on |
|---|---|---|
| `HondaEcu.Core` | Immutable ROM loading, hashes, profiles, controlled encodings, diffs, patch planning/reporting, verification, and oracle analysis | .NET base class libraries and `System.Text.Json` |
| `HondaEcu.Cli` | Parse commands, resolve explicit paths/profiles, print previews and warnings, and serialize reports | `HondaEcu.Core` |
| `definitions/` | Versioned JSON Schema and declarative ROM profiles | No executable code |
| `private/` | Local ROMs, editor-produced oracle files, and generated reports | Never public source input |
| `tests/` | Deterministic synthetic fixtures and contract tests | Public production projects |
| A future desktop UI | Tables, graphs, undo/redo, and patch preview | `HondaEcu.Core`; never a second implementation of ROM logic |

The intended flow is:

```text
input path -> RomImage -> identity/profile gate -> decode or PatchPlan
          -> changed copy -> DiffReport + PatchReport -> verify -> new output path

baseline/no-op/cases -> OracleManifest -> normalized byte diffs
                     -> candidate hypotheses -> explicit human review/export
```

Dependencies point inward toward `HondaEcu.Core`. The core does not depend on a console, a desktop framework, Crome, Honda Tuning Suite (HTS), or proprietary ROM data.

## Core model boundaries

- `RomImage` owns an immutable snapshot of input bytes and its size, SHA-256, and CRC32. Mutation produces a distinct byte sequence. Saving requires an explicit output path.
- `RomHash`, `RomIdentity`, and `RomSignature` keep identity evidence separate from the 32 KiB format rule. File size alone never selects P28.
- `RomProfile` describes one explicitly scoped ROM revision and contains scalar/table definitions, identity rules, sources, and checksum metadata.
- `ScalarParameterDefinition` and `TableParameterDefinition` describe where bytes are and how they may be interpreted. They do not execute expressions from JSON.
- `ParameterEncoding` selects a controlled implementation such as raw integer, linear, inverse, lookup-table, or unsupported. Every enabled encoding must have focused round-trip and boundary tests.
- `ParameterValue` records both raw and engineering representations so UI formatting cannot silently alter stored bytes.
- `ParameterChange` and `PatchPlan` make intended changes explicit before any output is written.
- `DiffRange` and `DiffReport` are byte-level facts independent of parameter interpretation.
- `PatchReport` records input/output identity, every declared byte change, checksum state, and flash-readiness state.
- `EvidenceReference` and `ValidationLevel` make provenance part of a definition rather than an informal comment.
- `ChecksumDefinition` and `ChecksumStatus` isolate checksum evidence from calibration parameters.

Public-documentation leads that cannot yet be decoded safely remain unsupported or read-only. A definition being parseable is not evidence that its meaning is correct.

## Profile contract

Profiles are data, not scripts. A profile declares:

- a schema/profile version and stable profile ID;
- raw-file constraints (P28-304 is exactly 32,768 bytes, with no header, padding, or truncation);
- revision scope and identity evidence;
- source references pinned where possible;
- scalar/table definitions with offsets, widths, endian, encoding, ranges, rounding, write status, evidence level, and notes;
- checksum-region evidence separately from calibration parameters.

JSON profile loading must reject unknown or malformed encodings. It must never use `eval`, reflection-based method names, dynamic compilation, or another path by which profile text can execute code.

## Identity and revision gates

Raw length answers only “can this file fit this format?” It does not answer “which ROM is this?” Identity proceeds in this order:

1. Match a known cryptographic hash when one has been independently established and may be distributed as metadata.
2. Otherwise evaluate documented multi-byte signatures that are sufficiently revision-specific.
3. Otherwise require an explicit profile override/confirmation and preserve the unknown identity in reports.

The experimental profile intentionally does not invent a stock hash. An explicit override permits PC research; it does not convert an unknown image into a verified P28-304 or make output flash-ready.

## Read, patch, and verify transactions

Read and diff operations have no write side effects. Patch follows a transaction-like sequence:

1. Load and fingerprint the input snapshot.
2. Enforce size, identity, validation-level, writable, and range gates.
3. Decode old values and encode proposed values using a controlled encoding.
4. Build a `PatchPlan` and preview exact old/new bytes.
5. Apply the plan to a copy in memory.
6. Evaluate checksum status without silently bypassing it.
7. Stage both the output and JSON patch report as temporary files.
8. Publish the report first and the ROM last; if the ROM publish fails, remove the report so an error never leaves a partial or unreported ROM output.
9. Independently verify report claims against the baseline and output bytes with `hondaecu verify`.

Failure must not leave a partial output. Input and output resolving to the same file are rejected.

## Oracle subsystem

Crome and HTS are independent observation tools, not specifications. Each oracle manifest binds the exact editor version and options to hashes for one baseline, its no-op save, and isolated cases. M0 requires plugins to be recorded as disabled because it has no trustworthy plugin-region map. Analysis separates no-op normalization and declared checksum changes, then reports all candidate offsets and supported encoding hypotheses with error and confidence. It never promotes a candidate directly into a production profile.

`cross-editor-confirmed` requires Crome and HTS cases made from the same baseline bytes and compatible observations of offset, width, endian, conversion, and rounding. Agreement can strengthen a claim but cannot establish physical ECU behavior.

## Checksum and flash-readiness boundary

Checksum behavior remains `Unknown` until a specific algorithm and covered/stored byte regions are supported by sufficient evidence and automated fixtures. The published checksum-jump patch is evidence of a routine location, not evidence for the checksum algorithm and not permission to bypass it.

M0 outputs are at most `PcInspectionOnly` or `CrossEditorValidated`. The software must not automatically assign `BenchCandidate`, `BenchValidated`, or `VehicleValidated`. See [ROM_HANDLING_POLICY.md](ROM_HANDLING_POLICY.md) and [VALIDATION_STRATEGY.md](VALIDATION_STRATEGY.md).

## Extension strategy

Additional revisions receive separate profiles and identity rules. Shared encoding implementations may be reused only when their mathematics is independently supported; offsets and revision claims are never inherited implicitly. P07 work starts with structural/static comparison and P07-specific definitions, not copied P28 offsets.
