# D1 — Ukrainian basic-calibration desktop workspace

D1 integrates the completed M1t Core workflow into the existing WPF application.
It is not another editor engine, a new firmware format or an ECU emulator. D0,
legacy one-slot Save, M1d/M1e checks, M1g export and the separate M1h conditional
RPM workspace remain available. Every result stays `PcInspectionOnly /
NotFlashReady`; `physicalRpmAvailable=false`.

## Start with the demonstration

Choose «Демонстраційний режим», then «Базові налаштування». The independent
draft has six initially excluded groups. The demonstration contains invented
values, is labelled «Не прошивка Honda», and provides editable tables, settings
roundtrip and educational lookup/predicate graphs. It creates no trusted binding,
reviewed location, firmware BIN or fabricated native Pass. It has no production
export path. This documentation describes user operation; interactive GUI
acceptance for D1 is **NotRun**.

## Explicit original inputs

Use the shared «Відкрити BIN» and «Обрати binding» actions to select an original,
research profile and its existing exact-original binding, acknowledging the
research scope. Select the existing signed reviewed compensation definition in
the new workspace. No private files are discovered automatically, and no key,
signature or child binding is generated. Unknown files remain raw-only; size or
a checkbox cannot enable revision-specific fields. A missing definition does
not prevent read-only inspection, but prevents a production M1t preview/export.

The prerequisite area shows document mode/name, profile, binding, definition,
runner availability and refusal reasons. An incompatible mapping cannot inherit
permission merely because legacy threshold inspection was admitted.

The default runner is `AppContext.BaseDirectory/tools/p28-slice-runner.exe`.
Choose an explicitly trusted local runner through the shared runner action if
needed; no PATH/CWD/private-build search or network download takes place.

## Six independent raw groups

| Section | Groups | Units and limits |
| --- | --- | --- |
| VTEC | One selected code-owned slot out of eight | Raw threshold code, 0..255; context/pair/prior are shown, not physical ON/OFF labels |
| Limiter | fixed, bank0, bank1 | Raw fixed cut/resume periods; independent adaptive base words used by the producer to form RAM thresholds |
| Idle | baseTable, lateTable | Seven raw target-period values per table; original raw axes are read-only |

Each group has its own inclusion and reset action. Excluded groups become null,
even if their local text was previously changed. Included groups supply complete
pairs/tables. Switching VTEC slots discards the previous slot's local requested
value rather than accumulating a second edit. New drafts start from original
values with all groups excluded; old pending VTEC edits are not imported.

The Core settings parser and current pair/full-domain policies remain authoritative.
No silent clamp, rounding, pair swap, bank synchronization, table copying or
invented cross-family RPM constraint is added. Empty/invalid text is retained
as text, not converted to zero or the previous successful number. Requested cells
use directly bound text editors; the view explicitly updates bindings and commits
DataGrid cell/row before snapshot, rejecting validation errors.

«Імпорт settings JSON» parses and validates the complete M1t document before
atomically swapping the draft. Invalid input cannot partially populate it.
«Зберегти settings JSON» creates a new file in the unchanged six-required-key
M1t format, not a project/database format. Previously imported files remain
protected snapshot inputs for later export.

## Preview, validate/save, reopen

«Переглянути зміни» calls `P28BasicCalibrationEditor.Preview` asynchronously.
It shows requested/unchanged/effectively-changed groups, individual old/new raw
values, unchanged context, domain results, one compensation byte, actual complete
diff and actual A/B/C residues. No example diff count or checksum residue is
hard-coded. Preview creates no firmware file; checksum arithmetic is not a native
execution Pass. A full no-op can be previewed but cannot publish a BIN.

VTEC graphs use `P28ThresholdLogic.Evaluate`. Idle graphs use the Core projection
extracted from the existing integer-domain helper, with rawD9 X, raw target-period
Y and original/requested knots. Integer samples are drawn as steps, not smoothed.
The label is «Lookup-модель, не фактичні RPM». Base lookup may be replaced by an
override/late lookup; DATA027A is not an addition to target within the established
contract. A graph is not the final target for all histories/contexts. No adaptive
threshold-history graph or physical units are invented.

Draft/input changes invalidate previous preview/results. «Перевірити та зберегти
PC-only копію» requires a current non-no-op preview, three explicitly new,
different paths and a confirmation describing the changes and PC-only scope.
Every attempt calls `P28BasicCalibrationExecution.ValidateAsync` anew and passes
its non-deserializable capability directly to `P28BasicCalibrationWriter.Save`.
No CLI process, stdout parsing, direct ViewModel BIN write, receipt laundering or
capability caching is used. Existing ADD/SUBB assumptions do not enter M1t.

Original/profile/binding/location/runner/imported inputs are bounded snapshots,
rechecked before publication. Outputs cannot overwrite existing files, inputs or
each other, or traverse output links/junctions. The existing Core writer owns
staging, cancellation boundary, rollback and independent readback. Group
power-loss atomicity is not promised. Failure is not successful publication.

The common MainViewModel job/cancellation/close mechanism prevents new and legacy
native jobs running together. D1 jobs block document switching/editing. Late
results are checked against session/job identity. Long domain/native/receipt and
readback operations run off the UI thread. Progress reports actual stage names:
VTEC prefix, limiter/adaptive, idle, checksum, evidence verification, publication,
readback. There is no timer-derived percentage and no Pass at process start.
Cancellation before publication uses the bounded adapter/process-tree cleanup;
after publication begins, the writer finishes its readback/rollback contract.
A late Cancel must not relabel an already successful publication as canceled.

The result preserves separate fresh evidence counters/witnesses, publication,
readback and output paths. Fixed and adaptive counters are shown independently
inside the limiter evidence family; unlike counts are not summed into an ECU
count. Large receipts stay on disk; the UI binds only typed summaries, selected
details and the small plan presentation, never full receipt JSON.

«Відкрити M1t результат» explicitly selects child + original + profile/binding/
location + saved plan + receipt and calls the Core `InspectDerived`/`Verify`
path. The child is read-only. Historical consistency is neither fresh execution
nor authentication of past execution. «Взяти налаштування з плану» explicitly
restores settings over the original, never over child bytes; another save still
requires fresh validation. Previously opened tuple paths remain protected.

## Checks and portable distribution

Tests distinguish adapter/ViewModel/mocked job lifecycle, actual Rust subprocess,
offscreen STA layout/bindings and private real-ROM Desktop-service acceptance.
Public fixtures are invented only. The STA check never calls Show/ShowDialog or
uses desktop input: it measures logical viewports and enlarged text, inspects
runtime binding errors, readonly columns, actual text binding validation,
commands and scrolling. Logical viewport tests do not change Windows DPI.

The private acceptance route uses production MainViewModel/service with a
test-only dialog provider: original admission → M1t settings import → equivalent
preview → fresh validation → one new BIN/plan/receipt → independent readback →
separate child inspection. It compares the new BIN with an existing M1t result,
without another CLI BIN. This is headless service acceptance, not GUI smoke.

Publish a new folder without replacing previous portable releases:

```powershell
./scripts/publish-desktop.ps1 -OutputPath artifacts/desktop/win-x64-d1
./scripts/test-desktop-portable.ps1 -PortablePath artifacts/desktop/win-x64-d1
```

The package contains Desktop, compatible M1t runner, public definitions,
self-contained runtime, notices and D1/M1t documentation, never private inputs
or results. Standard public CI uses synthetic inputs only and uploads its clean
portable artifact. The no-window diagnostic runs outside the repository in a
Ukrainian/spaces path and different working directory; it is not normal startup
or interactive GUI acceptance.

## Boundaries

Fresh suites are independent local software executions on identical actual A/B/C,
not one ECU main loop. VtecFullChain/P1, joint ECU scheduling, hardware/full boot,
physical RPM and plant feedback remain NotRun/unavailable. GUI r3 remains paused;
D1 interactive GUI acceptance is NotRun. D1 changes no writable fields, signed
locations, emulator semantics, physical defaults, protocol hardware or firmware
formats. M1t and earlier stages remain completed within their existing scopes.
