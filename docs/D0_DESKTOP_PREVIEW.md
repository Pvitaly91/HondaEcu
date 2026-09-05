# D0 — Windows Desktop Research Preview

Base: `origin/codex/p28-rpm-producer-scaling-m1e`,
`43a6e60d3a8ddf33caee44af6683d766ef6a9ab0`, including M1d
`7752addb98db9aa1ad749e013b374eb9a161d8df`.
Work branch: `codex/hondaecu-desktop-preview-d0`.

D0 exposes the existing scoped research workflow in a Ukrainian Windows WPF
window. It is not a finished tuning editor, M1 completion, a new emulator or an
ECU connection tool. Production PatchEngine, Oracle v2, original research binding,
M1c one-parent lineage and the two independent unresolved ADD gates retain their
existing meaning. Public RPM definitions remain non-writable. Every result is
`PcInspectionOnly / NotFlashReady`; checksum status remains `Unknown`.

## Launch and synthetic demonstration

For a published build, double-click `HondaEcu.Desktop.exe` in its portable folder.
Do not separate it from its DLLs, runtime, `definitions/`, `tools/` and notices.
No .NET SDK, Rust compiler, Cargo, Git or source repository is needed on the
Windows x64 machine running the application. No executable is downloaded by it.

The initial window offers «Відкрити BIN» and «Демонстраційний режим». No private
ROM/binding discovery occurs on launch. Choose the demonstration to exercise
the interface without private material. It is explicitly marked
«Синтетичний приклад — не прошивка Honda» and uses invented bytes in memory.
Select a slot, enter a decimal integer from 0 to 255, choose «Переглянути зміну»,
inspect the exact diff and step graph, then choose «Скасувати зміну».
Demo creates no trusted P28 binding, cannot save a Honda firmware, and cannot
present its model as original-ROM execution.

The graph is «Модель порогового порівняння». Its 256 inputs and old/new Boolean
outputs come from the existing Core predicate `compactCode > threshold`.
Equality is false. The selected prior state and changed-result codes remain
visible. The drawing is stepped, not smoothed; it does not depict RPM, a sensor,
AFR, physical VTEC activation or an executed ROM result.

## File states and controlled changes

| State | Available scope | Gate that remains closed |
|---|---|---|
| Unknown / raw-only | File name, size, technical hash, neutral hex preview | No threshold interpretation, edit or revision-specific execution |
| Bound baseline | Scoped slot inspection and one-slot planning | Requires explicit existing private binding, selected research profile and Core verification |
| Verified derived | Original-parent-linked inspection and checks | Requires original parent, binding, plan and patch report; not a new baseline or arbitrary patch chain |
| Synthetic demo | Table, pending raw value, in-memory diff and graph | No Honda firmware save or real execution |

To use an original file, select it with «Відкрити BIN», then «Обрати binding».
Select the research profile (the bundled definition is
`definitions/p28/p28-304.experimental.json`) and your current private original
binding, and acknowledge the research scope. A checkbox or the 32768-byte size
alone cannot make unknown bytes a verified baseline. A mismatch remains a refusal.
Do not generate a fresh binding merely to bypass this gate.

For an existing M1c child, «Відкрити похідний файл» requests the child, original
parent, original profile/binding, plan and patch report. Core verifies the complete
one-step lineage before exposing scoped interpretation. The original binding is
not replaced with the child's hash.

Only one pending slot is supported. Input is unambiguous decimal integer 0–255:
no RPM, fractional value, signs, inverse selection, arbitrary offset, pair repair,
mirrored edits or hidden multi-slot changes. Choose «Переглянути зміну» to create
an in-memory plan. Old/new bytes, offset and full diff remain visible; equal
old/new values form an explicit no-op with zero changed bytes.

«Зберегти PC-only копію» requires new BIN, plan and patch-report paths, followed
by explicit confirmation of the slot, old/new value, diff, `Checksum Unknown`
and `NotFlashReady`. The existing Core plan/apply rules and shared publication
helper are used; the original and existing inputs/reports cannot be overwritten.
After publication the files are independently re-read and verified. Staging and
best-effort rollback are retained; there is no promised cross-file transaction
under power loss. A failed verification is an error, not a successful save.
No checksum repair or bypass occurs.

## Execution and result categories

The «Перевірки» tab provides file verification, M1d
«Виконати фрагменти прошивки» and M1e
«Перевірити розрахунок внутрішніх обертів», plus structured results for the
current job. Core APIs are called directly; human-readable CLI stdout is never
parsed as an API. Rust runs only through the existing bounded process adapter.

Strict mode is the default. The advanced permissions remain independent:

- `oki.add-er1-a` applies only to the M1e producer. It is not allowed for M1d.
- `oki.add-er3-a` permits the unresolved compact-F form only when actually reached.

Conditional execution requires separate confirmation. Permission does not mean
an assumption was used; results show both sets. Completed without assumptions,
conditional matches, unresolved, mismatch, execution error, budget exceeded and
not-run are separate counters. These are stage-execution counts, not counts of
independently validated ECUs or physical events. Zero mismatches is not a complete
success when any conditional/unresolved/not-run case remains. All interpreter
and model-agreement limits from M1d/M1e still apply.

No hardware-scaling assumption editor is added. M1e shows
«Фізичні оберти не підтверджені» and symbolic/unavailable status without supplying
invented board clock or event geometry.

The packaged default runner is resolved from
`AppContext.BaseDirectory/tools/p28-slice-runner.exe`, never the current directory
or PATH. If it is missing, the app still opens and reading/demo/diff/preview work.
Use «Обрати Rust runner…» to select an executable you explicitly trust. In a
source build it is normally `rust/p28-slice-runner/target/release/p28-slice-runner.exe`
after the build command below; it is not discovered automatically.

Long operations run asynchronously with indeterminate progress and «Скасувати».
Immutable input snapshots and session/job identities prevent a late result from
being attached to a different file, binding or selected slot. Closing cancels
and waits for the active process adapter; completed publication is not interrupted
halfway through the existing rollback/readback contract.

## Build from source on Windows

Use the .NET 8 SDK selected by `global.json` and PowerShell 7. Rust compilation
additionally needs pinned Rust 1.85.1, its `x86_64-pc-windows-msvc` target, and
Visual Studio / Build Tools with Desktop development with C++ and a Windows SDK.
These are build-machine requirements, not portable-app runtime requirements.

```powershell
rustup toolchain install 1.85.1 --profile minimal --component rustfmt
rustup target add x86_64-pc-windows-msvc --toolchain 1.85.1
cargo +1.85.1 build --release --locked --manifest-path rust/p28-slice-runner/Cargo.toml
dotnet restore HondaEcu.Windows.sln
dotnet build HondaEcu.Windows.sln --configuration Release --no-restore
dotnet test HondaEcu.Windows.sln --configuration Release --no-build
dotnet format HondaEcu.Windows.sln --verify-no-changes --no-restore
dotnet run --project src/HondaEcu.Desktop/HondaEcu.Desktop.csproj --configuration Release
```

`HondaEcu.Windows.sln` contains Core, Desktop and Desktop.Tests. The unchanged
cross-platform `HondaEcu.sln` remains the explicit Linux/Windows Core/CLI/Rust
test target. Do not use an implicit solution command now that two solutions exist.

## Reproducible portable publication

From the repository root in PowerShell 7:

```powershell
./scripts/publish-desktop.ps1
./scripts/test-desktop-portable.ps1
# A later publication must use a new directory:
./scripts/publish-desktop.ps1 -OutputPath artifacts/desktop/win-x64-next
```

From another current directory, invoke the script by its full path. Its input
and default output locations still resolve from the script's repository root.

Paths passed to `-OutputPath` are resolved relative to the repository root; only
new directories below `artifacts/desktop` are accepted. The script checks the
build tools, builds and tests the locked Rust dependency graph using Rust 1.85.1
and static MSVC CRT, then publishes WPF Release for `win-x64`, self-contained, without
trimming, Native AOT or single-file bundling. No caller-supplied Rust flags are
silently inherited. `global.json` selects the .NET 8 SDK; the exact selected SDK,
compiler and restored runtime-pack versions are recorded in the publication
manifest. This records build inputs; it is not a promise that compiler outputs
from different SDK/runtime patch versions are byte-identical.

```text
artifacts/desktop/win-x64/
  HondaEcu.Desktop.exe
  [self-contained .NET/WPF runtime and application files]
  definitions/p28/p28-304.experimental.json
  tools/p28-slice-runner.exe
  THIRD_PARTY_NOTICES.md
  licenses/p28-slice-runner/
  licenses/rust-1.85.1/
  licenses/dotnet/[exact runtime package versions]/
  docs/D0_DESKTOP_PREVIEW.md
  PUBLISH-MANIFEST.json
```

Only public definitions, app/runtime resources, runner and component notices are
copied. Runtime-pack licenses come from the exact restored packs, not an unrelated
SDK license (.NETCore supplies its license and third-party notices; WindowsDesktop
8.0.30 supplies its MIT `LICENSE` without a separate notice file). The Rust
standard-library license/COPYRIGHT and all retained runner
crate texts are included. Missing required resources/notices or forbidden
ROM/private/debug artifacts fail publication. A failed build leaves its ignored
staging directory for diagnosis; it never replaces a prior publication.
No root license for HondaEcu is selected or implied by component redistribution.

The Windows desktop CI job builds/tests/formats the explicit Windows solution,
publishes the clean folder, runs the no-window portable startup diagnostic from
an outside-repository Ukrainian/spaces path with a different working directory,
and uploads only the clean published folder as
`HondaEcu-Desktop-Research-Preview-win-x64` with a 14-day retention period. The
existing two-OS job retains Rust tests and real synthetic process integration
tests. Neither CI job receives private ROMs or reports. No GitHub Release is
created. Executables, DLLs, ZIPs, PDBs and `artifacts/` are ignored and not committed.

## Validation record and limits

The local packaging preflight completed with .NET SDK 8.0.424, .NETCore and
WindowsDesktop runtime packs 8.0.30, and Rust 1.85.1. The fresh portable folder's
file hashes and forbidden-artifact checks passed. An actual packaged-runner
process executed an existing four-byte synthetic probe and returned the expected
byte without assumptions. All 43 existing Rust tests also passed under the exact
static-CRT publication configuration. PE import inspection showed only Windows system DLLs,
not an external VC runtime dependency. Re-publication into the existing folder
and a workspace-root destination were refused without changing the existing EXE;
output resolution was also checked from a different working directory. A second
complete publication from that unrelated working directory succeeded into a new
path containing spaces and Ukrainian letters.
These are package/process checks, not WPF interaction or OEM execution evidence.

Build, ViewModel/contract tests, portable resource tests and actual GUI interaction
are distinct evidence categories. A successful build or headless test is not a
GUI smoke test. The final delivery records actual local test counts, CI results,
portable-path launch checks and whether a real WPF window was exercised.
Actual local D0 verification:

- Release Core/CLI: **285 tests passed** (252 Core, 33 CLI), no failures/skips.
- Windows desktop: **39 tests passed** (38 ViewModel/service tests and one
  offscreen STA layout test), no failures/skips. The layout test measures
  100% / 125% / 150% equivalent logical viewports; it does not switch Windows DPI.
- Pinned Rust1.85.1: **43 tests passed**, also with the static-CRT portable build.
- Original/profile/binding/previous M1c lineage preservation, forbidden-artifact
  guard and formatting/whitespace checks passed. Existing Core/CLI/Rust safety
  implementations and public definitions remain unchanged.
- Private desktop-service integration actually opened the existing baseline,
  checked its binding, previewed one raw change, saved three new private files,
  independently re-read them, retained original-child lineage, ran strict M1d/M1e
  and separately conditional M1e, and checked cancellation/close. No source was
  modified. This is service/process validation, not a real-file GUI test; all
  populated reports and identities stay ignored/private.
- **Actual WPF GUI smoke passed** after explicit Computer Use permission:
  launched a portable folder outside the repository with a Ukrainian/spaces path,
  opened synthetic demo, entered 40→60 using keyboard input, previewed the exact
  one-byte diff and changed step graph, canceled back to40, checked that execution
  is disabled in demo, and closed using Alt+F4. The native screenshot is synthetic
  only and remains in ignored local artifacts, not the public Git tree or CI.
  The host's current scaling was used; actual OS DPI switching is **not-run**.
- The self-contained executable's explicit `--check-portable-resources` mode
  passed with no window, from another working directory, outside the repository,
  with Ukrainian/spaces paths, invalid DOTNET_ROOT and SDK/Cargo/Git removed from
  PATH. This checks the application host and app-relative bundled resources,
  **not GUI interaction**. Normal launch still works if the runner is absent;
  this diagnostic deliberately requires a complete published bundle.

The offscreen STA check exposed an idle-close reentrancy bug, fixed by deferring the
second Close until the first Closing event returns. The portable diagnostic also
exposed that WPF rejects assigning a null StartupUri; startup now creates the
main window explicitly only for normal launch. Both are covered by the distinct
layout/portable checks. Public CI results and the clean artifact link are reported
in the delivery after pushing this branch; no unrun CI result is inferred here.

Real-file UI validation is separate and remains private if run. No screen or
software check validates an ECU, native checksum, OEM provenance or physical RPM.
There is no flashing, OBD, COM-port connection, editor installation, full ECU boot,
new opcode permission, hardware test or writable RPM definition in D0.
