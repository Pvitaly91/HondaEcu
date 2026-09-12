# M2d checksum-preserving primary ignition-map cell export

M2d adds a PC-only controlled export for explicit raw cells in the two primary
P28-304 ignition-related maps established by M2c. It composes every result from
the one exact original, performs fresh native lookup/consumer/checksum
validation, and publishes only through a typed capability. It does not add
physical timing units, alternate-map editing, a GUI, hardware authority or
flash readiness.

## Closed edit contract

The new contract ID is `p28-primary-ignition-map-numeric-cells-v1`. It does not
change the public P28-304 profile digest or make any profile entry writable.
The only selectable regions are:

| Settings key | Exact cells | Geometry | Encoding |
| --- | --- | --- | --- |
| `ignition_map_0` | `72E4..73AB` | 20×10 row-major | unsigned raw byte |
| `ignition_map_1` | `73AC..7473` | 20×10 row-major | unsigned raw byte |

Each key is required and is either `null` or an array. An array may contain at
most 200 unique `{row,column,rawValue}` objects; the total is at most 400.
Coordinates and values are unsigned decimal integers, `rawValue` is `0..255`,
and the parser rejects duplicate coordinates, unknown properties, offsets,
units, percentages, clamping and force modes. Cells are canonicalized by
map, row, then column. `null` and an explicit empty array stay distinct.

The M2c source audit is rechecked against every instruction byte in the exact
M1b listing. It establishes direct numeric operands of the shared interpolation
helper, not pointers, axes, lengths, selector/gate state, metadata, code or
encoded destinations. The load axis `7000..7009`, RPM axes `7014..703B`,
candidate `700A`, selector/read/producer/consumer code, checksum code, selector
writer and its `60EA` gate are immutable. The separate alternate 11-row targets
`7474..74E1` and `74E2..754F` are also immutable and outside this contract.

## A/B/C composition and finite audits

Composition is always:

1. A — the unchanged exact bound original.
2. B — all requested primary-map cells applied to one copy of A.
3. C — B plus exactly one computed write to the existing signed and reviewed
   checksum compensation location `7FFF`.

There are no sequential child chains. Every preview, apply, verify and inspect
reproduces from A and reruns M2c layout admission plus M1f checksum code/gate
checks. The M1g signed compensation definition and M2b grouped new-path
publication/readback machinery are reused without creating a new signing root
or compensation candidate.

For each map, A and B are compared over all `256×256 = 65,536` raw RPM/load
pairs using the same directional Q16 integer primitive as the independent M2c
model. The audit records result ranges and increased/decreased/equal counts,
checks every interpolation result against its four unsigned cells, proves the
terminal-zero-as-256 rule and bounds all wide intermediate products. Separately,
the immediate consumer is audited over all 65,536 lookup/factor combinations:
factor zero bypasses scaling; nonzero factors return the unsigned product high
byte. This is raw software behavior, not degrees, timing advance or RPM.

## Mandatory fresh native evidence

`apply` cannot accept a caller-supplied scenario. It internally builds the
factor-zero corpus covering every one of the 342 map rectangles, all 400 cells,
axis boundaries and near-boundaries, repeated calls, reversals and alternating
map history. The unchanged M2c Rust operation runs A, B and C from scratch
patterns `00`, `55` and `AA`; every checkpoint must strictly match the
independent stateful model. B and C must be identical apart from checksum
behavior, while A/C axis positions, caches, selector/context and histories must
remain identical.

Five additional internal scenarios seed `DATA0247` once in initial state with
`1`, `127`, `128`, `173` and `255`. They never write the factor per call. Each
scenario executes A/B/C under all three scratch patterns and preserves examples
where lookup effects survive the consumer or are masked when such inputs exist.
Per-cell evidence records reads, isolated lookup effects and combined-image
effects. A separate native checksum batch must show A=`0`, C=`0`, and the actual
B residue. The runner executable is hashed before and after validation.

Only `P28VerifiedIgnitionMapExport`, whose constructor is not public, can reach
the grouped writer. The capability contains the exact plan plus bounded,
defensively serialized native evidence; the writer re-derives the corpus,
model outcomes, cell effects, witnesses and checksum observations before using
it. Receipt evidence is historical consistency only after publication; verify
and inspect do not claim a new native run.

## CLI

The closed workflow is:

```text
research p28-ignition export plan    <original.bin> ... --settings <settings.json> --output <new-plan.json>
research p28-ignition export apply   <original.bin> ... --plan <plan.json> --runner <runner> --confirm-pc-only --output <new.bin> --saved-plan <new-plan.json> --report <new-receipt.json>
research p28-ignition export verify  <child.bin> --baseline <original.bin> ... --plan <plan.json> --report <receipt.json> --output <new-verification.json>
research p28-ignition export inspect <child.bin> --baseline <original.bin> ... --plan <plan.json> --report <receipt.json> --output <new-inspection.json>
```

The omitted common arguments are `--profile p28-304`,
`--baseline-binding <exact-binding.json>` and
`--compensation-definition <signed-location.json>`; plan/apply also require
`--confirm-profile`. Destinations must be distinct new paths. Apply snapshots
all inputs, rejects aliases and no-op plans, rechecks them before publication,
stages the BIN/plan/receipt as a group and verifies their complete readback.

## Boundary

Every M2d result is `PcInspectionOnly / NotFlashReady`. Physical RPM and degree
conversion are unavailable. GUI r3 remains paused/NotRun, D1 interactive GUI
acceptance is NotRun, and hardware/full-boot validation is NotRun. M2a, M2b,
M2c and all M1 contracts remain closed and unchanged. M2d does not complete all
of M2 and does not authorize flashing a vehicle ECU.
