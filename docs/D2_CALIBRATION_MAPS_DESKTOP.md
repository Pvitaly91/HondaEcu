# D2 — unified calibration maps Desktop workspace

D2 starts from M2e commit `246354d4e14014945603945daffb5cc5eac0a380`.
It extends the existing Ukrainian WPF application, not a second editor or an
ECU emulator. The six D1 basic groups and four map groups use one exact
original, one document/session gate and one M2e settings snapshot. The D1
basic panel is the authoritative editor for `basic.vtec`, `basic.fixed`,
`basic.bank0`, `basic.bank1`, `basic.baseTable` and `basic.lateTable`; D2 reads
that same draft, not a second editable basic form.

The D2 groups are `fuel.map_0`, `fuel.map_1`, `ignition.ignition_map_0` and
`ignition.ignition_map_1`. These are neutral software IDs, not physical modes.
Each grid is 20×10. Identity and offsets come from `P28FuelMapContract` or
`P28IgnitionMapContract`, never a WPF address formula. Original cells, axes
and fuel column multipliers come from the admitted original. The last axis
byte 0 is displayed as “256 — кінцева межа; збережений byte 0”; it is not
another node zero or a ROM edit. Row 19/column 9 remains an editable upper
corner. Axis, multiplier, original and offset displays are read-only.
Ignition has no fuel multipliers; raw ignition cells are not confirmed
physical degrees. Physical RPM is unavailable; units remain raw.

## Draft and closed settings

Every group has explicit inclusion. No bank/map synchronization, auto-tuning,
smoothing, percentage/degree transform or implicit inclusion occurs. The old
D1 M1t-only action is labelled “Зберегти тільки базові налаштування”; to keep
map edits use “Перевірити та зберегти всі вибрані зміни — PC-only”.

One cell accepts decimal raw u8 `0..255`; text is retained separately from
the parsed number. Empty/invalid text in an included map blocks snapshot,
even when that map is hidden. An excluded map serializes as `null`, ignoring
its local draft; re-inclusion revalidates the whole map. Included with no
explicit cells serializes as `[]`. An explicit unchanged entry stays
requested provenance, distinct from a byte change. Manual reset to original
intentionally **clears** explicit provenance for the reset cells; switching
map, previewing and saving do not.

Paste reads the system clipboard only after explicit Paste. Input is plain
numeric rectangular TSV: no headers, formulae, offsets or executable
content. All values and target bounds are validated before one atomic
operation; one bad/empty field rejects the entire paste, never truncates it.
Fill and reset apply to a selected rectangle or whole map. The unified-draft
undo/redo history includes basic edits, map edits and one atomic import entry;
it is bounded to 100 snapshots and belongs to the current original. New
edits after undo clear redo, and document switch starts new history.
Public tests can inject clipboard/dialog providers without OS input.

Import parses the entire closed Core `explicit-p28-calibration-set` document
with all ten required group keys before replacing the draft. Settings export
writes a new file, not firmware; no workspace database is added. Imported
settings are protected input snapshots for later publication.

## Preview, probe and native gate

The main preview calls `P28UnifiedCalibrationEditor.Preview` for current
settings and displays ten group summaries, exact diff, A/B/C residues and
one compensation. Arithmetic-domain audit is **not** native execution.
Draft/input changes invalidate preview; stale/no-op preview cannot save.

Heatmap modes are Original, Requested and Delta. Original/Requested share a
raw `0..255` color scale; Delta zero is neutral. Color is no safety judgment
and numbers remain visible. A 2D plot shows the selected row's raw cells,
not a final fuel surface or physical angle. The lightweight model-only probe
calls Core `P28FuelMapModel.ProjectNumeric` or
`P28IgnitionMapModel.ProjectNumeric`, plus ignition `Consume`. It displays
interval indices, four corners, Q16 fractions, interpolation intermediates
and lookup. Fuel shows separate column multipliers. Ignition factor `0..255`
is probe-only: zero bypasses; nonzero returns highByte(lookup×factor). It
does not enter settings, execute ROM, establish native selector/cache history
or claim physical units. An excluded map uses original bytes for effective
requested model and is visibly marked not included.

Save requires bound original/profile/exact binding/reviewed compensation
definition, runner, current non-no-op preview, three distinct new
BIN/plan/receipt paths and explicit PC-only confirmation. The Desktop
service calls `P28UnifiedCalibrationEditor.Reproduce`, then **fresh**
`P28UnifiedCalibrationExecution.ValidateAsync`, then
`P28UnifiedCalibrationWriter.Save`. Publication accepts only the typed live
capability, never receipt JSON. Desktop does not use CLI or family exporters
as backend and never writes BIN directly. Core owns domain policy, evidence,
compensation, protected-path checks, rollback and independent readback.
Progress displays only real `P28UnifiedCalibrationStage` values. The shared
D1 job gate prevents conflicting tabs/document switching. Cancellation
before publication stops validation; once publication starts, Core
readback/rollback must finish and late Cancel cannot turn success into a
false “nothing saved” message.

Fresh native validation, publication and readback are shown separately.
Historical verification returned by Save has `FreshExecution=NotRun` by
contract; the separate fresh result of that job is retained. Suite counts
keep their units (VTEC cases; limiter/idle/fuel/ignition calls; checksum
invocations), never an invented ECU count. M2e's real receipt is 51,586,904
bytes: settings/plan/receipt reads use Core bounds 256 KiB/4 MiB/256 MiB by
explicit file role. Large JSON is not bound to a TextBox. Desktop retains
one local plan snapshot for presentation and one evidence summary snapshot
instead of binding defensive getters repeatedly.

“Відкрити M2e child” requires child plus exact original, profile, binding,
location, plan and receipt; only Core `InspectDerived`/`Verify` establishes
historical consistency. Child is read-only, never a new original. “Редагувати
налаштування цього плану” restores draft over the original; another save
again requires fresh validation. Older M1t/M2b/M2d tuples retain their
formats. M2e verification's legacy `D2Status="NotStarted"` describes that
historical document, not current Desktop delivery/build status.

## Acceptance and safety boundary

Synthetic demo has four asymmetric invented maps/axes and is labelled
“Вигадані дані; не прошивка Honda”; it cannot publish or claim native Pass.
Public tests use invented data/programs. Offscreen STA/XAML checks measure
bindings and logical viewports without `Show`, `ShowDialog`, focus, OS
keyboard/mouse or desktop automation. Those are not real DPI changes or
interactive acceptance. A separate private headless service workflow may
exercise an actual original/runner without showing a window. GUI r3 remains
paused/NotRun; D1 and D2 interactive acceptance are NotRun. Hardware, full
boot, ECU write, physical RPM/degrees and flash readiness remain unavailable
or NotRun. Every result stays `PcInspectionOnly / NotFlashReady`.

Build a new portable folder with
`./scripts/publish-desktop.ps1 -OutputPath artifacts/desktop/win-x64-d2-verified`.
`./scripts/test-desktop-portable.ps1` copies it outside the repository to a
Ukrainian/spaces path, changes CWD, excludes SDK/Cargo/Git on PATH and runs
only a no-window diagnostic. It checks the bundled runner's M2e operation
inventory; actual export still validates each native operation/response.
This is not normal startup or a GUI smoke test.
