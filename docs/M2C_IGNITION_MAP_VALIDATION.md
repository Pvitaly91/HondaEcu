# M2c ignition-map structure and native lookup validation

M2c establishes a revision-bound, read-only raw lookup contract for the two
primary ignition-related tables in the privately bound P28-304 original. It
does not add ignition editing, a firmware writer, checksum compensation,
physical timing units, a scheduler, GUI work, or hardware authority.

## Evidence boundary

The work starts from exact commit
`b2fb894d487f90b617abdde771a98312c0008017`. The private original, its exact
binding and the matching M1b listing are unchanged. The source audit reuses the
established census of 11,499 listing instructions and 155 program-data reader
sites and verifies every listing instruction byte against the original. The
new guards then check only the required M2c pointers, dimensions, selector,
helper entry, consumer and axes.

Without the exact binding plus `--confirm-profile`, the inspector returns
general image identity only. It never decodes the candidate tables.

## Confirmed layout

| ID | Cells | Geometry | Encoding and order | RPM axis | Load axis |
| --- | --- | --- | --- | --- | --- |
| `ignition_map_0` | `72E4..73AB` | 20 rows × 10 columns | unsigned byte, row-major | `7014..7027` | `7000..7009` |
| `ignition_map_1` | `73AC..7473` | 20 rows × 10 columns | unsigned byte, row-major | `7028..703B` | `7000..7009` |

The cell formula is `origin + row*10 + column`. At `0B67/0B69` the caller
loads 10 columns and 20 rows. The shared helper uses `row*10`, reads adjacent
program bytes for the current row, then advances by ten bytes and reads the
next row. This establishes geometry, storage order and unsigned one-byte cells;
the visual shape of the table was not used as proof.

The public leads `72E4..73AB` and `73AC..7473` are therefore confirmed for
this exact original. The second region begins immediately after the first and
is not metadata. `7474` and `74E2` are separate pointers used by a statically
identified alternate 11-row path. They are excluded from the two primary maps
and are not interpreted as column multipliers.

All three axes are unsigned ascending raw-byte tables. The last zero is a
terminal sentinel: byte subtraction makes it the 256 endpoint for the final
interval. It is not supplied as an ordinary terminal knot. The load axis is
ROM-shared with fuel, but the ignition caller owns a distinct persistent
`DATA01BB` index and `DATA01BE` fraction. The two RPM positions use
`DATA01C6/DATA01C2` and `DATA01C7/DATA01C4`.

## Native source selection and caller scope

The native stage executes `0B64..0BAE`; the harness does not inject `X1`.
`DATA0227.5` clear selects `ignition_map_0` at `72E4`, and set selects
`ignition_map_1` at `73AC`. The scenario names only one of those two
code-owned contexts. The runner updates mask `20` and preserves other bits.

The selected direct primary path fixes these code-derived gates clear:
`DATA021D.4`, `DATA0214.5`, `DATA021F.1`, and `DATA0219.6`.
`DATA0218.5` is also fixed clear although it is bypassed when
`DATA0214.5` is clear. These choices exclude the override and alternate-map
paths; they are not claims about normal ECU scheduling.

The upstream writer at `5FA0..5FAC` derives and writes `DATA0227.5`;
the exact original's program gate at `60EA` is zero. M2c does not execute that
writer. Its selector is therefore an explicitly scripted software input, not a
physical VTEC/cam state.

The native axis producer executes `0A0C..0A61` and helper
`59B2..59E3`. Per call the harness supplies raw `DATA0238`, `DATA00C2`
and `DATA00BF`. With context 1 selected, firmware at `0A32..0A38`
substitutes `DATA0238` for the second RPM-axis input. Thus the selected
context always uses `DATA0238`; `DATA00C2` remains an observed scripted
input and is natively shadowed for context 1.

## Exact raw arithmetic

For each axis, firmware searches from its persistent cached index. With lower
and upper program bytes, it computes:

`denominator = byte(upper - lower)`

`numerator = byte(raw - lower)`

`fraction = floor((numerator << 16) / denominator)`

The final zero sentinel makes the final denominator `256 - lower` by byte
subtraction. No host clamp or endpoint replacement is used.

Lookup executes caller `0BAF..0BB3` and helper `59E4..5A45`. Fuel enters
the same helper with `PSWL.5` set and reads column metadata. Ignition clears
`PSWL.5`; the helper retains constant `0101`, so the four unsigned cells
are multiplied by unity and no metadata byte is read.

Define directional interpolation as:

`I(a,b,w) = a + floor((b-a)*w/65536)` when `b >= a`;

`I(a,b,w) = a - floor((a-b)*w/65536)` otherwise.

Firmware performs `top = I(topLeft,topRight,loadFraction)`, then
`bottom = I(bottomLeft,bottomRight,loadFraction)`, then
`lookup = I(top,bottom,rpmFraction)`. Each unsigned 16×16 multiplication
uses its high word, so every stage truncates independently. There is no assumed
bilinear floating-point equivalence, multiplier table, signed cell, bias,
saturation or physical-angle conversion.

The immediate same-CPU/RAM consumer executes `0BB4..0BD3`:

- if `DATA0247 == 0`, `DATA0248 = lookup`;
- otherwise `DATA0248 = highByte(lookup * DATA0247)`.

Both branches have strict actual-original evidence. `DATA0248` is read at
`0FF4` as the base operand of a later correction and unsigned clamp before
the scheduling calculation. That link is static-only in M2c. Consequently a
raw cell, the returned lookup byte, the corrected timing value, dwell and
driver transition timing remain distinct concepts. Physical degrees and
delivered spark timing are unavailable.

## State and execution ownership

For every image, scratch pattern and sequence the runner creates one CPU/RAM,
initializes it once, and preserves indices, Q16 fractions and `DATA0248`
across calls. The four stages are a scripted schedule, not the ECU main loop.
Produced positions, pointers, reads, lookup and consumer output cannot be
supplied by JSON. The schema accepts only bounded once-only state, raw inputs,
the two software context IDs, and an optional code-owned cell mutation.

The independent C# model copies its own ROM bytes and owns a separate history.
It recomputes axis searches, directional truncation, cell addresses, result
and consumer output. Rust checkpoints never seed later expected C# state.
The validator compares source origin, positions/fractions, ordered program
reads, four cell values, arithmetic intermediates, persistent state, writes,
stage exits and stack balance. No assumptions are permitted.

## Actual-original coverage and A/B

The final-source private run has:

- 350 logical calls × scratch `00/55/AA` = 1,050 strict checkpoints;
- both primary contexts, all 9 load intervals, both sets of 19 RPM intervals,
  all 200 cells of each map, exact knots, interior points, byte-domain minima
  and maxima, last intervals, repeats, forward/reverse cache motion and context
  switches;
- scratch-invariant origins, results and consumer outputs;
- 4 more logical calls × three scratches = 12 strict checkpoints through the
  nonzero `DATA0247` branch;
- zero conditional matches and zero mismatches in the final runs.

Two separate children were constructed from original A only in process memory.
For `ignition_map_0`, one byte at code-owned row 5/column 5 changed; for
`ignition_map_1`, one byte at row 12/column 7 changed. Each full-image diff
contained exactly that cell. Each A and B used independent Rust and C#
histories with identical inputs.

Across three scratches, each map produced 9 witnesses where the changed-cell
read changed native lookup and `DATA0248`. Each also produced 3 actual
changed-cell reads whose effect was masked by zero weight/truncation and 6
opposite-map or other-interval controls where the cell was not read. Interior
inputs are included for both maps. No numeric delta is interpreted as degrees,
advance, retard, power or engine behavior.

An exploratory nonzero-consumer run stopped strictly at previously unadmitted
`MOVB r0,N8` at `0BBC` and remains preserved privately. The exact decoded
opcode received a focused register-alias/width regression and a minimal
M2c-only admission change; a neighboring destination form remains rejected.
The final rerun is strict. A newly composed, non-OEM Rust subprocess program
also covers the relevant selection → lookup byte → multiply/high-byte →
`DATA0248` flow successfully.

## Read-only commands and status

```text
hondaecu research p28-ignition maps-inspect <baseline.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --output <new-private-inspection.json>

hondaecu research p28-ignition lookup-check <baseline.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --runner <rust-runner> --scenario <private-scenario.json>
  --output <new-private-validation.json>
```

Outputs are new private JSON reports. There is no output-BIN option and no
ignition export, axis editing, checksum repair/bypass, receipt, signing or
capability. Public profile digests and writable flags are unchanged.

M2a and M2b remain completed. M2c completes only the scoped primary raw
ignition-map structure/native lookup/nearest-consumer objective. All of M2 and
independent M1 gates are not declared complete. Status remains
`physicalRpmAvailable=false`, raw units, `PcInspectionOnly / NotFlashReady`,
GUI r3 `paused/NotRun`, D1 interactive GUI acceptance `NotRun`, and
hardware/full boot `NotRun`.
