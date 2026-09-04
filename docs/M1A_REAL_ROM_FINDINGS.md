# M1a - Real baseline and VTEC investigation

Investigation date: 2026-09-05 Europe/Kyiv (acquisition occurred on 2026-09-04 UTC).
Base: `origin/codex/oracle-validation-hardening-m0-1`, commit `c8c0507d845ede38c57e2dc89c405d1774b5569f`.
Working branch: `codex/p28-304-real-rom-baseline-m1a`.

This records work actually performed, not completion of M1. No Core/CLI implementation, profile identity, encoding, writable parameter, checksum policy, or emulator was added or changed.

## Results at a glance

| Question | Observed result |
|---|---|
| Baseline obtained | **Yes:** a real 32768-byte archive payload, stored only locally |
| Provenance confidence | Archive-byte continuity established; original ECU custody/authenticity **low/unresolved** |
| Native revision identified | **Unresolved:** source calls it `304stock.bin`; neither filename nor length proves factory revision |
| Crome import | **Not tested**; no installed target found by bounded inventory |
| HTS import | **Not tested**; not classified as unsupported without an import attempt |
| Editor no-op behavior | **Not tested** for both; no editor-produced no-op files |
| VTEC static analysis | **Partial, real-ROM-backed:** contextual threshold pairs and their software consumers traced |
| Real oracle cases | **0**; no training, repeat, holdout, or displayed value was invented |
| M1 / cross-editor confirmation | **Incomplete / not established** |
| Flash readiness | **Not flash-ready** |

## Baseline acquisition and provenance

The actual local `private/roms/`, `private/oracle/`, and `private/reports/` directories were inspected first. They contained only their three `.gitkeep` files at task start. No personal directories were recursively searched, and no existing private file was modified or removed.

The [historical PGMFI EcuDefinitionCodes record](https://github.com/hondabase/files-archive/blob/06d2eb0d9b37c6b1bd001254203790751457b4a7/pgmfiorg/twiki/bin/view/Library/EcuDefinitionCodes.html) lists an attachment named `304stock.bin`, 32768 bytes, uploaded by `blundar` on 19 February 2004 at 19:35. Its attachment note explicitly says **unknown origin**. The associated code table claims USDM, P28-A01, manual-transmission Civic EX/SOHC VTEC context; those are source assertions, not authenticated provenance for this file.

The old attachment link is not itself a usable download at the current pinned archive revision. The [archive deduplication commit](https://github.com/hondabase/files-archive/commit/0fcca91f1124672b7b756118d9fd5d701102eefc) links the former TWiki attachment and other duplicate paths to the current `ecu-roms/304stock.bin` through the same Git blob. A targeted GET of that file at archive commit `06d2eb0d9b37c6b1bd001254203790751457b4a7` actually returned HTTP 200, `application/octet-stream`, and 32768 bytes. The complete downloaded bytes matched the pinned Git blob identity, not merely an HTTP header or catalog size. This establishes preservation within the archive, not an independently sourced second factory dump.

Checks rejected the possibilities of an HTML error page, Git LFS pointer, ZIP signature, text-only hex representation, or truncated payload. No padding, truncation, byteswap, decompression, or header removal was applied. A byte-identical working copy was made; source and copy hashes remained unchanged through the CLI and disassembler runs.

The private dossier records SHA-256, independently checked CRC32, exact length, source URL/date/name, archive history, selection rationale, uncertainties, exact profile-file digest, HondaEcu analysis commit, commands, and before/after hashes. These private hashes, machine-specific paths, logs, and ROM bytes are intentionally omitted here. Trusted profile identities remain empty.

Source terms were checked: the archive has no repository license declaration; the preserved wiki footer identifies CC BY-NC-SA 1.0 for contributed material. Neither establishes permission to redistribute Honda firmware. The ROM, working copy, source snapshots, and generated listings remain ignored and local.

## Existing HondaEcu commands on the real image

Using the unchanged M0.1 CLI and experimental `p28-304` profile:

| Command | Actual result | What it does not establish |
|---|---|---|
| `inspect` | Exit 0; size and hashes recorded; no trusted profile match | Factory identity or revision |
| `profile validate` | Exit 0; profile structure valid | Correctness of its research leads |
| `read` | Exit 0; no safely decodable parameters | Any actual VTEC engineering value |
| `roundtrip` | Exit 0; byte-identical; **0 values decoded/encoded** | Encoding correctness or editor operation |

All **4 scalar definitions and 8 table definitions** were skipped as `Unsupported`; therefore there were **zero actual encoding checks**. The roundtrip success must not be described as a working real-ROM editor. Full command output is private. The source baseline was independently rehashed after these operations.

## Editor suitability and first no-op gate

Windows Computer Use initialized successfully, so GUI automation itself was available. The registered application/window inventory, Windows uninstall registrations, and PATH did not identify Crome, HTS, Ghidra, or an installed asm662/dasm662. This bounded inventory does not prove a portable copy is absent elsewhere; exact paths were requested instead of scanning personal directories. No editor was launched, installed, licensed, activated, or used to generate a file.

[Crome's official page](https://crome.io/) advertises stock OBD1/P28 editing and VTEC adjustment. [HTS opening documentation](https://help.hondatuningsuite.com/CreatingOpeningRom.html) describes BIN/ROM input and codebase identification for supported ROMs. Neither demonstrates acceptance, native revision identification, conversion behavior, or byte-preserving raw save for the acquired file. Website release numbers are not reported as locally installed versions.

The [HTS VTEC documentation](https://help.hondatuningsuite.com/VTECSettings.html) has separate low-load and high-load engagement controls, disengagement delay, and other enable/safety/output settings. These labels cannot be collapsed into one native scalar or equated with `0x6543`. [HTS basemap creation](https://help.hondatuningsuite.com/Creatingabasemap.html) explicitly chooses an HTS codebase. Creating such a basemap or converting maps would not test preservation of this native candidate.

The published [Crome Pro EULA, section 3(f)](https://crome.io/legal/crome-pro-license) restricts use in developing or testing similar software. Its applicability to the intended oracle work must be reviewed by the owner/licensor before a Pro-based comparison. This is not a legal determination and must not be generalized to an unreviewed Free or Dealer license. No terms were accepted or restrictions bypassed during this task.

Both editors' classifications remain **not tested**, not `byte-preserving`, `deterministic transformation`, `nondeterministic transformation`, or `import unsupported`. There are no real no-op outputs to diff. No manifests were fabricated and no HondaEcu-patched image was represented as editor output. `oracle create-manifest/add-case/analyze/compare` were not run without their required real editor evidence.

## Reproducible static-analysis tooling

Only the existing [asm662/dasm662 source](https://github.com/VIRUXE/asm662/tree/94612d10370eb4ddf97d4f349168298e1a3da8a0) at commit `94612d10370eb4ddf97d4f349168298e1a3da8a0` was acquired and compiled locally. Its root LICENSE is Unlicense, while original-source notices/README describe BSD provenance; both were retained privately. No third-party source or executable was added to HondaEcu's tracked tree.

The pinned files are RCS archives, not directly compilable working files. Current trunk-head text was extracted without changing opcode logic. The archived generated `op.c` was used, avoiding a new opcode generator or disassembler. It is an older generated snapshot than the repository opcode-description revision; this and the tool's heuristic decoding are limitations, not independent validation.

The installed Visual Studio 2022 C/C++ compiler built `dasm.cpp` and `dasmout.cpp` as C++, `op.c` as C, then linked `dasm662`. `/FIstring.h` supplied missing legacy declarations and `_CRT_SECURE_NO_WARNINGS` suppressed CRT deprecation diagnostics; source semantics were not patched. Exact commands and compiler output are in the private tooling dossier.

Invocation used:

```text
dasm662 <unchanged-private-bin> <private-listing.asm> 5465 7ff0
```

The final two arguments are the legacy tool's hexadecimal table-discovery bounds, **not entrypoint addresses**. Raw input maps from program address zero; the complete input was verified as 32768 bytes beforehand because the tool otherwise pre-fills its buffer and does not robustly reject short input. The run completed with three reported DD-mode heuristic corrections; a successful exit is not whole-ROM decoding proof. Full listing and diagnostics remain private.

The [Ghidra OKI module](https://github.com/VIRUXE/ghidra-oki66207/tree/fe88d013bb73922ddd38808d765fac2d3ebac9cc) at `fe88d013bb73922ddd38808d765fac2d3ebac9cc` was reviewed, **not executed**. It shares opcode ancestry with asm662, and its P28-specific validation/ABI assumptions are not a P28-304 guarantee. In particular, the actual candidate's VCAL routine behavior must be established before selecting a variant that overrides return-width behavior. No Ghidra database or emulator was created.

Key instruction semantics were checked visually against the [OKI MSM66201 Instruction Manual, first edition, September 1991](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/Oki_66201_Instruction_Manual.pdf): program/data-space separation (printed 1-7), DD/PSW behavior (1-21 to 1-23), byte load (3-70), indirect word ROM load (3-72), byte comparison (3-39), bit copy from carry (3-78), and 32-by-16 division (3-57). This supports the checked instructions in the shared core, not every MSM66207 peripheral or ECU-board behavior. No scanned manual pages are committed.

## VTEC crossover: observed structure versus hypotheses

The following are narrow static observations on the acquired candidate. Addresses in the DATA column are runtime data-space addresses, **not raw ROM offsets**. No listing or raw-byte dump is embedded here.

| Observed code location | Narrow finding |
|---|---|
| ROM `0x1244`, alternative `0x124D` | A data-state bit selects pointers to `0x6542` or `0x6546`, each a four-byte context |
| ROM `0x1253`, `0x1261` | `LC` reads a **word from program space**; the pointer advances by two between reads |
| ROM `0x1257..0x126A` | Prior DATA `0x0131.1` / `.2` state selects the loaded low byte or accumulator high byte; byte comparison results against DATA `0x0133` are copied from carry into those bits |
| ROM `0x07C7..0x0820` | DATA `0x0133` is produced from a word at DATA `0x00C4` through bounded arithmetic/division/shift paths, not by storing literal RPM |
| ROM `0x12A4`, `0x12C4` and following branches | The threshold-state bits feed additional conditions and timer/state logic on a path that sets/clears the software output `P1.0` and DATA `0x0127.2` |

This is evidence for **two selectable contexts, each with two state-dependent threshold pairs**, not evidence that only `0x6543` is active. The examined path can consume every byte in `0x6542..0x6549`. Hysteresis is a plausible interpretation of the previous-state-dependent selection; exact external calibration semantics and supported editor fields remain hypotheses.

The compact DATA `0x0133` quantity still needs a fully checked physical-RPM mapping, branch boundaries, integer arithmetic, saturation and inverse-encoding specification. The PGMFI RPM pages remain research leads, not substituted formulas. No Linear/Inverse codec was fitted to this structure, and no new codec was added.

VTEC enable, the threshold comparisons, temperature and speed conditions, pressure/error feedback, timers, and output control remain separate concepts. Tracing a software write to `P1.0` does not independently establish the physical solenoid wiring, actual switching behavior, or vehicle compatibility. No P07/VTEC-E interpretation was applied.

## Blockers and smallest next operation

1. Supply the exact path to an existing editor and review its applicable license for this research use. No system component, driver, paid feature, or installer is required by this report.
2. First test **one editor and no-op only**: record About/version/edition/plugins/options, open a disposable baseline copy, and record every ROM/codebase/conversion message. Do not silently approve a conversion or replace the native baseline.
3. If direct import succeeds, save `noop-a`; independently reopen a fresh baseline copy and save `noop-b`; reopen `noop-a` and save `noop-a-resave`. Preserve every output separately. Full-diff baseline-to-A, baseline-to-B, A-to-B, and A-to-resave with the existing CLI. Unknown changes remain unknown, even if stable.
4. Only after the no-op/codebase result is understood, choose the exact VTEC field and collect the first single-parameter case. The 4000/5000/5500 requests remain conditional discovery inputs; no accepted range, displayed value, or boundary step is assumed. A repeat and predeclared holdout follow, not a large up-front file matrix.

If HTS requires conversion, direct native comparison remains blocked while Crome/static work may continue; a converted codebase must be recorded separately. Until real independent editor evidence and the complete encoding are established, the profile stays read-only and M1 remains incomplete.

## Local delivery checks

Release build passed with zero warnings/errors. All 119 existing tests passed (103 Core, 16 CLI); `dotnet format --verify-no-changes --no-restore` and `git diff --check` passed. The existing tracked-artifact privacy guard passed, and an additional local check confirmed acquired artifacts are ignored and private baseline identities/paths do not occur in public files. These checks validate repository delivery, not editor compatibility or ECU behavior. No code defect was reproduced and no implementation or regression test was added.
