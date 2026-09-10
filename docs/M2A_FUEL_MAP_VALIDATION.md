# M2a fuel-map structure and native lookup validation

M2a is a revision-bound, read-only research extension for the one privately bound P28-304 input. It establishes two numeric map regions, their raw axes, native software selection, lookup arithmetic, and the first concrete downstream software boundary. It does not enable editing/export, complete all of M2, reopen M1/D1, establish physical units, or make an image flash-ready.

## Confirmed layout

Actual pointer construction and program-data reads establish the following layout:

| Object | Range | Encoding and role |
|---|---:|---|
| shared load axis | `0x7000..0x7009` | 10 unsigned raw bytes, 9 intervals |
| `map_0` RPM axis | `0x7014..0x7027` | 20 unsigned raw bytes, 19 intervals |
| `map_1` RPM axis | `0x7028..0x703B` | 20 unsigned raw bytes, 19 intervals |
| `map_0` cells | `0x7050..0x7117` | 20 rows × 10 columns, unsigned byte cells, row-major |
| `map_0` column metadata | `0x7118..0x7121` | one unsigned multiplier per column |
| `map_1` cells | `0x7122..0x71E9` | 20 rows × 10 columns, unsigned byte cells, row-major |
| `map_1` column metadata | `0x71EA..0x71F3` | one unsigned multiplier per column |

For either map, `cell[row,column] = origin + row*10 + column`. A cell has no endianness because it is one byte. The following 10 bytes are not padding: the lookup reads adjacent per-column multipliers from them. Word program reads at odd addresses remain odd; data-space alignment rules are not applied to code space.

All three axes begin at raw zero, increase strictly before their final zero byte, and use that terminal zero as the byte-wrapped 256 endpoint. The harness supplies the full raw byte domain without host clamping. The candidate region at `0x700A` is used by a different caller/table path and is not the `map_1` load axis in the recovered fuel path; both confirmed maps use `0x7000` here. Neutral names `map_0` and `map_1` are retained.

## Native positions, selection, and state

The axis caller executes `0x0A0C..0x0A44` for both RPM positions and `0x0A62..0x0A76` for the selected load input, calling `0x59B2..0x59E3`. Cached indices live at `DATA01C6`, `DATA01C7`, and `DATA01BC`; Q16 fractions live at `DATA01C2`, `DATA01C4`, and `DATA01C0`. The helper searches forward from a bounded cache and backtracks when input falls below the cached interval. Equality advances to the knot as the new lower endpoint. The final interval uses the 256 sentinel.

The full fraction word is native output, not a host reconstruction. `DIV` leaves DD=1, so the caller's shared D3 instruction stores a word; the following byte load returns DD to byte mode before the cache-index store. Repeated inputs and reverse cache movement are therefore verified from persistent RAM without reseeding produced indices or fractions.

`DATA0127.1` is the recovered software selector. Its clear writer is at `0x12DF`, its set writer at `0x12F9`, and its reader at `0x131A`: clear selects `map_0`, set retains `map_1`. The main-path table/pointer selection at `0x12FC..0x133F` is executed by ROM; the harness never injects X1. `DATA011C.5` and `DATA0121.6` are fixed clear for this direct path, while `DATA00B8.3/.4` and `DATA0227.5` are also fixed clear for the bounded axis caller. Their upstream physical reachability is not executed. In particular, `DATA0127.1` is not equated to a physical VTEC/cam state.

## Lookup arithmetic

At `0x59E4..0x5A45`, the selected 20×10 map consumes native load index/fraction and the selected context's native RPM index/fraction. Reads occur in this order:

1. two adjacent column-multiplier bytes;
2. two adjacent cells in the current row;
3. two adjacent cells in the next row.

Each corner cell is multiplied by its own column multiplier. The helper then performs two directional column interpolations and one directional row interpolation. For lower value `L`, upper value `U`, and unsigned Q16 weight `W`, it adds or subtracts `high16(abs(U-L) * W)`. That is integer truncation at every one-dimensional step; it is not one floating-point bilinear average. Exact knots have zero weight. Row 19 and column 9 participate as the upper neighbors of final intervals; raw 255 remains inside the sentinel interval.

The C# model owns a separate image and cache history. Validation compares selected origin, native positions, ordered program reads, four cell addresses/values, two multipliers, all four scaled operands, final lookup return, persistent RAM, stage exits, instruction extents, stack balance, and consumer output. No existing ADD/SUBB permission is accepted by this task; every actual result is strict or stops.

## Consumer boundary

The map result returns in ER2, is moved to A at `0x1347`, and is stored as an unsigned word in `DATA0140` at `0x134E`. The exact original has a zero program byte at `0x60E5`; its load leaves ZF set, so `JEQ` bypasses optional correction helper `0x5A55`. Consequently the actual-original M2a consumer witness is the unchanged lookup value stored at `DATA0140`.

Static downstream code loads `DATA0140` as a word multiplication operand at `0x14ED/0x14F0` and again at `0x21DB/0x21E0`. This establishes a numeric role in the surrounding fuel-delivery software calculation. M2a stops there: it does not identify a scheduling command, electrical injector pulse, delivered fuel quantity, AFR, milliseconds, or a linear percent interpretation. The optional `0x5A55` multiplication/shift/saturation path is modeled for the recovered code but is not reported as executed for this original gate value.

## Commands and bounded harness

```text
hondaecu research p28-fuel maps-inspect <baseline.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --output <new-private-map-report.json>
hondaecu research p28-fuel lookup-check <baseline.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --runner <rust-runner> --scenario <private-scenario.json> --output <new-private-validation.json>
```

Inspection without a matching private binding returns only general identity data and no decoded maps. Outputs are new JSON files; neither command writes firmware.

Each image/scratch sequence has one CPU/RAM initialization. Per call, the harness may write only three raw software inputs and masked `DATA0127.1`. It schedules five bounded native stages on the same machine: both RPM axes, load axis, ROM selection, lookup, and consumer. Stage scheduling is not the ECU main loop. Unknown forms stop strict execution; remaining calls are null/`NotRun`.

## Actual coverage and one-cell A/B

The exact original completed 1,050/1,050 strict checkpoints: 350 calls under each of scratch `00`, `55`, and `AA`. The corpus alternates both contexts, covers all 9 load and both sets of 19 RPM intervals, reads all 400 map cells, includes exact knots, raw 0/255, interior points, reverse cache movement, repeats, and context switches. Scratch does not alter the explicitly owned state.

Two separate in-memory children were made from the original, never chained:

- one unsigned `map_0[0,0]` cell changed by +1;
- one unsigned `map_1[0,0]` cell changed by +1.

For each child, all 24 A/B checkpoints were strict. The two same-context exact-node calls across three scratch patterns produced 6 witnesses: actual changed-cell read → lookup result +1 → `DATA0140` +1. Six opposite-context/out-of-region controls did not read the changed byte and did not change either result. Exactly one byte differed in each child. The original arithmetic checksum residue was zero and each uncorrected child residue was one; no checksum repair, binding, BIN, receipt, capability, or export artifact was created.

## Residual unknowns and status

- Raw axis bytes have no established physical RPM or MAP units.
- Cell/multiplier encoding is established only as native integer arithmetic; fuel quantity, time, percent, and AFR scales are unknown.
- Physical reachability and meaning of the selector and fixed caller gates are unknown.
- Upstream scheduler/IRQ/full boot and downstream electrical actuation are not executed.
- Ignition maps and full-table editing/export are outside M2a.
- GUI r3 remains `paused/NotRun`; D1 interactive GUI acceptance remains `NotRun`; hardware/full boot remains `NotRun`.

Status remains `physicalRpmAvailable=false` and `PcInspectionOnly / NotFlashReady`. M2a does not complete M2 or the independent M1 oracle/physical gates.
