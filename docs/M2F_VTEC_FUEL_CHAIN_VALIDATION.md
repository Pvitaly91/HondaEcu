# M2f — native VTEC-decision to fuel-map selection chain

M2f starts at the exact completed D2 commit
`8270906c0d4bccac1906cf91e6dc6adf97bd003b`. It adds the read-only
`research p28-fuel vtec-chain-check` command and the single `vtecFuelChain`
runner operation. Older `statefulVtec` and `fuelMapLookup` tasks, M2e/D2
publication and their strict-only gates retain their meanings. No firmware,
binding, export plan, receipt or publication capability is produced.

## Shared ownership and schedule

| State | Writer | Reader | Harness policy |
| --- | --- | --- | --- |
| `DATA0127` whole byte | ROM decision at `12AD/12D1/12EB/12DF/12F9`; other unscheduled writers remain outside scope | decision and fuel reader `131A` | seeded **once**; no per-call selector/map input; other bits preserved |
| `DATA0131`, `DATA0198` | native decision/helper | subsequent decision gates | seeded once; persistent across events |
| `DATA01D8/01D9/01DF/00F3` | native decision reload and established decrement/increment bodies | decision timer gates | seeded once; only explicit native body counts, never host decrement or time |
| P1 output-data | native decision | software request observation | seeded once under all-output/no-external-bus assumption; no pins/ASIC/feedback model |
| `DATA0119`, `011A`, `011C`, `00CC`, `00D9`, `0132`, `0199`, `0133`, `011E` | upstream software not scheduled here | decision | explicit per-event raw snapshots/configuration; `011C.5` must remain clear for direct fuel path; feedback is **not** synthesized from P1 request |
| `DATA0238`, `00C2`, `00BF` | scripted raw caller inputs | native RPM/load axis fragments | explicit per event; compact-code and axes are independent software stimuli |
| `DATA01BC/01C6/01C7`, `01C0/01C2/01C4` | native axis fragments | selection/lookup | seeded once; no cache/index/fraction injection or reseeding |
| `DATA00B8.3/.4`, `0227.5`, `0120.5`, `0121.6` | unscheduled caller | direct axis/fuel path | fixed-clear initial caller assumption; if code changes it, later unsupported path is refused, never clamped |
| `DATA013F/0140` | initial raw consumer factor / native consumer output store | immediate consumer / report | factor/output seeded once; `0140` thereafter native |
| PC, PSW, LRB, USP, banked registers, SSP/stack | actual fragments | next fragment | scripted entry only for counter/axis/decision; **no reset after decision entry through `1350`** |

One CPU/RAM exists for each image and scratch `00/55/AA` sequence. An event
supplies raw inputs, then executes the installed counter bodies, both RPM axes
`0A0C..0A45`, load axis `0A62..0A77`, decision `122C..12FC` with helper
`5839..586E`, and **continues from the same machine at PC `12FC`** through
ROM selection `12FC..1340`, lookup `1340..1347` (helper `59E4..5A46`), and
consumer `1347..1350`, stop-before `1350`. Observation checkpoints and scoped
access/program-data admission may change; machine state does not. The
decision-to-selection boundary records all bank registers, accumulator,
DD/PSW/LRB/X1/X2/DP/USP/SSP, the full shared byte, last native writes, selector reader
and ROM-selected origin. A separate invented two-fragment program tests this
seam, including a negative reinitializer that leaves the final number equal
but changes the boundary context.

This is a **scripted caller schedule** for counter and axis entry, not a
recovered main-loop/IRQ schedule. Acquisition/G/F are not added; M1k remains
separate. Counts of native tick-body calls are not milliseconds. The fuel
direct path requires clear `DATA011C.5` and `0121.6`; the axis caller requires
clear `00B8.3/.4` and `0227.5`. The same `011C` byte reaches both decision and
fuel code. Unsupported caller paths stop rather than being repaired by host
state edits.

## Request, selector and conditional evidence

P1.0 is the software output-data request. `DATA0127.2` is a request mirror.
`DATA0127.1` is the persistent map-selection status. None of these establishes
physical cam/VTEC state. They may disagree: request does not directly select a
map. The map is identified only from the native origin selected after ROM
reader `131A`; the runner never injects X1 or per-event map ID. An unchanged
selector can be retained without a new store, but its prior/initial provenance
remains visible. Native selection0→1 and1→0, request-without-selection,
retention, counter delay, feedback changes, cache motion and same-axis/different
map cases are covered by bounded private scenarios when reachable under the
joint caller gates. A blocked desired transition is recorded as such, not
manufactured by a selector patch.

The independent C# decision model owns its own ROM, counters, request/selector
history. Its own decision result feeds an independent persistent fuel model;
no Rust checkpoint is copied into expected state. Validation compares ordered
decision gates/threshold reads/stores, axes and caches, shared byte, `12FC`
CPU boundary, `131A` reader, native origin, ordered cells/multipliers,
scaled intermediates, lookup and actual `DATA0140` store. A final numeric
coincidence without these links is a mismatch.

`oki.subb-a-off-n8-encoding` remains the **only** optional conditional
permission. Its local exact form is not promoted by this composition. Strict
execution stops unresolved before the instruction; the fuel suffix and all
following calls are `NotRun`, with no new inputs applied. A permission merely
supplied but unused remains strict. Once actually used, all subsequent
dependent checkpoints in that sequence remain conditional even if later fuel
instructions are locally established. A dependent fuel match is never
relabeled a whole-chain StrictMatch. The er1/er3 ADD assumptions are not
available to this task.

## Closed scenario, A/B and limits

The bounded version-1 scenario has provenance, one initial VTEC state (with
full `DATA0127`), one initial fuel cache/consumer state, 1..256 dense events,
and at most eight trace witness indexes. Events contain the established VTEC
raw software inputs, native tick counts and three fuel-axis raw inputs. They
contain no per-event map ID, selector, P1 override, expected output, PC/RAM
write, prepared axis index or fraction. Unknown/duplicate fields, unsupported
direct gates and widened assumptions are refused.

Optional B is an **in-memory** one-byte edit from exact A: one existing
code-owned VTEC threshold slot *or* one fuel cell identified by neutral map
ID, row and column. No arbitrary offset, patch chaining or child binding is
accepted. A/B uses separate CPU/RAM/model histories. Threshold edits can
change predicates/request and still be masked before selector; a cell edit
cannot legitimately change selector/counters under equal inputs and matters
only if native lookup reads that selected cell. Uncorrected B is not an ECU
image. Any checksum arithmetic is diagnostic, never compensation.

On the locally admitted exact original, the bounded headless witnesses found
four native selection transitions per `00/55/AA` sequence, including both
`0→1` and `1→0`. Request and selection disagree in both directions: a
no-request call can retain/select map 1, and a request call can select map 0.
The same zero raw axes selected distinct maps and gave distinct lookup and
`DATA0140` observations. A separate retention sequence completed four
strict calls per scratch pattern. A mixed sequence completed ten strict calls
before its first actually used SUBB permission and five dependent conditional
calls per pattern; without that permission, the corresponding three strict
sequences each stopped once and left four suffix calls `NotRun`.

The threshold A/B changed an accessed code-owned predicate and downstream
request/selector/map/consumer histories on fifteen comparable events across
three scratch patterns; other events were masked by gates/history. The fuel
cell A/B changed only one map-1 cell in memory. Its byte was read in three
completed comparable lookups; only those three lookup/consumer results
changed. Request, full VTEC state/counters, selector and selected origin
remained controlled, with zero control failures. These are software-snapshot
observations under the explicit caller/conditional scope, not physical
measurements. Detailed actual-ROM evidence and hashes stay in the ignored
private M2f report area and are never uploaded to public CI.

The report is bounded to event summaries plus selected traces/first
discrepancy. A process success code alone is not a model match. Input file
snapshots, new-path/alias protection, timeout/cancellation and exact
profile/binding admission are reused. The required compiled runner operation
is `vtecFuelChain` in version 0.14.0; the D2 0.13.0 runner is insufficient.

`physicalRpmAvailable=false`; units are raw. No physical RPM/MAP/AFR/fuel
quantity, VTEC actuation, common ignition/fuel scheduling, complete
capture→fuel chain, full boot, hardware flashing or flash readiness is
established. GUI r3 remains paused/NotRun, D1/D2 interactive acceptance
NotRun, and every result is `PcInspectionOnly / NotFlashReady`.
