# ROM handling policy

This policy applies to the library, CLI, tests, documentation, CI, and all future user interfaces. HondaEcu is an inspection and research tool at M0; it is not a flasher and does not certify an image for an ECU or vehicle.

## Non-negotiable safety rules

1. **Never modify an input ROM in place.** Loading creates an immutable snapshot. Input and output paths that resolve to the same file are rejected, including path aliases where the platform can resolve them.
2. **Always write a result to a new, explicitly supplied path.** No implicit save, padding, truncation, container conversion, or fallback overwrite is permitted. Output is written atomically so failure does not leave a partial image.
3. **Always create a JSON patch report for a patched result.** It records input/output hashes, profile ID, exact old/new bytes and offsets, checksum state, evidence level, and flash-readiness status.
4. **Never identify a ROM as P28 merely because it is 32,768 bytes.** Many unrelated images have that length. Size is a format constraint, not an identity.
5. **Select a profile by verified hash, sufficiently specific signatures, or explicit user confirmation.** An override must remain visible in the report and does not turn an unidentified ROM into a verified revision.
6. **Treat every image validated only on a PC as not flash-ready.** Successful parsing, round-trip, byte diff, Crome/HTS display, checksum calculation, static analysis, or emulation is not bench or vehicle validation.
7. **Do not implement or recommend automatic checksum disabling.** A published checksum-bypass patch is a research lead only. Unknown checksum state produces `ChecksumStatus.Unknown` and `PcInspectionOnly`/not-flash-ready output.
8. **Do not raise the rev limiter for a first hardware test.** Initial future bench validation must use a conservative, separately reviewed plan; hardware authorization and procedures are outside M0.
9. **Never put OEM code or editor-generated ROMs in public Git.** This includes stock Honda ROMs, modified Crome/HTS BINs, a complete OEM disassembly/decompilation, or a Ghidra project/database.

## Public/private boundary

Only metadata, source citations, profiles, schemas, code, and deterministic synthetic fixtures belong in the public repository. These patterns are ignored:

```text
private/roms/*
private/oracle/*
private/reports/*
*.bin
*.rom
*.hex
*.eep
*.dump
*.gzf
*.rep
*.gpr
*.gpr.bak
*.db
*.trace
```

Only the directory-preserving `.gitkeep` files may be tracked below `private/`. Before every release or push, inspect the staged file list as well as the working tree; extension filters do not replace a content review.

Do not commit installers for Crome or HTS, and do not automatically download or run third-party executables. Do not copy third-party source code unless its license has been checked and the reuse is deliberate and documented.

## Safe local workflow

1. Put a personally obtained baseline under `private/roms/` or `private/oracle/`.
2. Record its SHA-256 before opening it in any editor.
3. Work from copies; keep the baseline read-only where practical.
4. Use `inspect`, `diff`, `roundtrip`, and oracle analysis before any patch.
5. Patch to a new path and require the patch report.
6. Run `verify` against the original input, output, profile, and report.
7. Label the result with its actual validation state and keep it private.

## Flash-readiness states

| State | Meaning |
|---|---|
| `PcInspectionOnly` | Byte-level and/or software-only checks; not flash-ready |
| `CrossEditorValidated` | Matching observations from both editors using the same baseline; still not flash-ready |
| `StaticAnalysisValidated` | Relevant behavior confirmed in code flow; still not hardware validation |
| `BenchCandidate` | Deliberately approved for a controlled bench plan; never assigned automatically in M0 |
| `BenchValidated` | Observed on an instrumented ECU bench under a recorded procedure |
| `VehicleValidated` | Observed under a separately reviewed vehicle test plan |

M0 may report only the first two states automatically. No accumulation of PC-only evidence silently crosses the hardware boundary.

## Checksum failure policy

Checksum storage bytes and covered regions are not ordinary calibration parameters. If the selected profile lacks a verified checksum algorithm, the CLI reports `Unknown`, preserves the bytes unless a separately reviewed explicit change says otherwise, and marks the output not flash-ready. A checksum-bypass patch is not a substitute for algorithm evidence.
