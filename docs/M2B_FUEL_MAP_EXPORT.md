# M2b fuel-map cell checksum-preserving export

M2b adds one exact-parent, PC-only export for explicit numeric cells in the two
M2a fuel maps. It does not turn the public profile or the entire region between
the maps into writable space. It does not edit axes, multipliers, selector or
caller gates, `ROM60E5`, checksum code/gate, VTEC, limiter, idle, ignition, or
any other calibration.

## Closed settings and edit contract

The new contract is `p28-fuel-map-numeric-cells-v1`. Its only writable fields
are unsigned bytes addressed through the existing code-owned mapping:

| Map | Cell range | Geometry | Offset |
|---|---:|---:|---|
| `map_0` | `0x7050..0x7117` | 20×10 u8, row-major | `0x7050 + row*10 + column` |
| `map_1` | `0x7122..0x71E9` | 20×10 u8, row-major | `0x7122 + row*10 + column` |

The required settings object has version 1, purpose
`explicit-fuel-map-cell-values`, and both `map_0` and `map_1` keys. `null`
means the map was not requested; an array is an explicit final-value selection;
an empty array means requested without changes. Coordinates must be unique and
inside row 0–19/column 0–9, with decimal integer `rawValue` in 0–255. A map has
at most 200 entries and both maps together at most 400. Unknown fields,
duplicate coordinates, offsets, widths, fractions, percentages, smoothing,
clamping and force modes are rejected. Entries are canonicalized by map, row
and column, so input order cannot change the reproduced plan or BIN.

Requested, byte-changed and behavior-changed remain separate facts. An empty or
full byte no-op can be planned and inspected but cannot mint a publication
capability or create a firmware BIN.

## Immutable data and edit/source audit

The actual listing/reader audit is separate from a successful lookup example.
It rechecks all listed instruction bytes and the established program-data reader
census, both map-pointer constructors, dimensions, selector reader, numeric
lookup and the `DATA0140` consumers. Cells enter the native lookup as unsigned
numeric operands; they are not pointer literals, dimensions, axes, strides,
scanner keys/sentinels or encoded destinations.

Every plan records immutable digests for vectors, selector, checksum code,
`ROM60E5`, shared load axis `7000..7009`, candidate `700A`, both RPM axes
`7014..703B`, and multipliers `7118..7121`/`71EA..71F3`. The full-image expected
diff permits only explicitly changed cells plus the existing compensation byte
at `7FFF`, at most 401 bytes. Full byte comparison also protects every other
location, including all M1 calibration groups and ignition data.

M2b reuses the existing signed `VerifiedCompensationLocation` without opening
the issuer key or changing its signature, identity, original-byte check, profile
or exact-parent binding. Cell edits preserve the pointer origins, strides, axis
stopping keys, cache bounds, code destinations, scanner barriers, checksum gate
and valid-stack assumptions on which that review depends. Its ordinary
initialized-state/source-listed scope is not broadened. The fact that the fuel
slice does not read `7FFF` is a bounded observation, not a global proof.

## Arithmetic audit

The exporter calls the same pure integer projection used by
`P28FuelMapModel`: each corner u8 is multiplied by its unchanged column u8,
then two directional column interpolations and one directional row interpolation
run sequentially with independent Q16 truncation. There is no floating-point
bilinear replacement.

For each map and each A/B plan, all 65,536 selected-raw-RPM × raw-load byte
combinations are checked. The audit verifies indices, nonzero denominators,
fractions, cell/multiplier bounds, scaled corners (maximum possible 65,025),
wide interpolation products, intermediate/final bounds and the terminal-zero
endpoint-256 rule. Intermediate products use 64-bit arithmetic because they can
exceed signed 32-bit range. Input 256 is never supplied or wrapped to zero;
row 19 and column 9 are reached as upper corners of the raw-255 sentinel
intervals. This exhaustive calculation is a model/arithmetic audit, not 65,536
native executions.

## A/B/C and native publication gate

- A is the exact unchanged original and must have recognized/enabled native
  checksum code with residue zero.
- B applies every requested cell once to one copy of A.
- C applies the one existing compensation calculation to B:
  `(originalCompensation - residueB) mod 256`.

A meaningful request may already give `residueB=0`; in that case the
compensation byte remains unchanged and no artificial diff is added. Apply
reproduces the complete serialized plan from the original, code-owned mapping
and signed inputs before doing any execution.

The mandatory internal corpus cannot be replaced by a caller scenario. It has
342 rectangle-knot calls covering all 19×9 rectangles in both maps, then axis
midpoints and representable upper neighbors, raw 0/255, final sentinel
intervals, forward/reverse cache movement, repeats, alternate-map histories and
a model-selected native witness input for every behavior-changing map. Every A,
B and C run has separate CPU/RAM and independent model state for scratch 00/55/AA.

The unchanged `fuelMapLookup` runner operation executes both RPM positions,
load position, ROM-owned selection, lookup and actual `DATA0140` store. The
validator compares indices/fractions, selected origin, ordered reads, four
cells, two multipliers, scaled intermediates, sequential result, consumer,
persistent history, extents, exits and stack. B and C must match for every
non-checksum observation; A and C must match for axis/cache/selector controls.
No ADD/SUBB assumption is available.

Per changed cell, the receipt retains corpus read count, combined lookup-change
count, isolated model-only lookup-change/masking counts and the first isolated
witness input. The plan separately retains its multiplier and old/new scaled
value. Isolated diagnostics explain zero weight or sequential truncation but do
not claim native one-cell causality. Each map whose full model domain predicts
a `DATA0140` difference must also have an end-to-end native A/C witness.

Finally, one existing M1f `checksumBatch` executes A/B/C × scratch 00/55/AA,
with 512 invocations, full ordered coverage and matching intermediate states per
sequence. A/C take the ordinary zero-residue path; B follows its actual residue.
Only strict completion constructs the non-deserializable
`P28VerifiedFuelMapExport` capability.

## CLI workflow and files

```text
hondaecu research p28-fuel export plan <original.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --compensation-definition <reviewed-location.json> --settings <fuel-cells.json> --output <new-plan.json>

hondaecu research p28-fuel export apply <original.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --compensation-definition <reviewed-location.json> --plan <plan.json> --runner <p28-slice-runner> --confirm-pc-only --output <new-child.bin> --saved-plan <new-plan-copy.json> --report <new-receipt.json>

hondaecu research p28-fuel export verify <child.bin> --baseline <original.bin> --profile p28-304 --baseline-binding <binding.json> --compensation-definition <reviewed-location.json> --plan <saved-plan.json> --report <receipt.json> --output <new-verification.json>

hondaecu research p28-fuel export inspect <child.bin> --baseline <original.bin> --profile p28-304 --baseline-binding <binding.json> --compensation-definition <reviewed-location.json> --plan <saved-plan.json> --report <receipt.json> --output <new-inspection.json>
```

Apply protects immutable input snapshots and requires three distinct new paths.
The shared grouped writer stages BIN/plan/receipt, rolls back a partial
publication where possible, rechecks inputs, and independently reads back the
size/hash, all cells, immutable ranges, full diff, residue, lineage and receipt.
Reverse diff must restore the entire original byte-for-byte. It does not promise
power-loss atomicity. Verify/inspect establish historical consistency only;
they run no fresh native execution and cannot create a capability.

The existing `maps-inspect` and `lookup-check` operations remain read-only and
their M2a contracts are unchanged.

## Actual bounded result and remaining limits

The final private demonstration selected three small numeric cells in each map,
including interior and final-row/final-column corners. Its 458-call corpus
completed 4,122/4,122 strict A/B/C image/scratch checkpoints. All six changed
cells were read; model-only per-cell diagnostics observed both effects and
weight/truncation masking. Native witnesses completed for both maps. All nine
checksum sequences completed; A/B/C residues were 0/0/0, so the existing
compensation byte correctly remained unchanged. The exact diff contained only
the six requested cell bytes. One private 32 KiB BIN plus saved plan/receipt was
published and passed independent readback, verify and inspect.

This result establishes only raw integer software behavior. Physical RPM/MAP,
fuel quantity/time/percent, AFR, selector reachability, scheduler/IRQ, electrical
injector output, engine response and hardware/full boot remain unknown/NotRun.
`ROM60E5=0` keeps its optional correction outside actual scope. Status remains
`physicalRpmAvailable=false` and `PcInspectionOnly / NotFlashReady`; GUI r3 is
`paused/NotRun`, D1 interactive GUI acceptance is `NotRun`, and hardware/full
boot is `NotRun`. M2a and older exports remain complete in their scopes. M2b
does not complete ignition-map work or all of M2.
