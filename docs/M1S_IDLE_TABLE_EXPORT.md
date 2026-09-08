# M1s — Idle-target table checksum-preserving export

M1s adds raw **PC-only** numeric editing of the two M1r idle-target tables.
It does not expose physical RPM, a complete idle controller or ECU-write authority.
M1q/M1r and previous exporters remain closed with their existing contracts.
`physicalRpmAvailable=false`; `PcInspectionOnly / NotFlashReady`.

## Closed fields and arithmetic policy

| Selection | Packed footprint | Writable u16LE value offsets, i = 0..6 |
| --- | --- | --- |
| Base table | `[0x68CB,0x68E0)` | `0x68CC + 3*i` |
| Late replacement table | `[0x68E0,0x68F5)` | `0x68E1 + 3*i` |

`P28IdleTableFields` owns the mapping, including the unchanged inspector IDs
`context-21a0-table-cell-i` and `context-late-68e0-table-cell-i`.
The footprint is 28 disjoint value bytes, not a contiguous writable range.
Axes (especially 68DA and 68F2), 68F5 onward, pointers, immediate overrides,
component peaks/thresholds, selectors, VTEC/limiter fields, code and checksum
gate/routine stay byte-identical. Odd word offsets and overlapping program reads
retain the existing M1r semantics. One existing reviewed compensation byte is
the only additional possible change; actual diff is at most 29 bytes.

Both `baseTable` and `lateTable` keys are required. `null` leaves that table alone;
an array specifies all seven final integer values, retaining original values for
cells not being changed. Selected-but-unchanged tables are explicit no-ops.
A whole-request no-op can be previewed but cannot publish another firmware BIN.
Unknown/duplicate/missing keys, arbitrary offsets, fractional/exponent tokens,
wrong lengths, zero and 65535 are rejected. The inclusive 1..65534 policy is not
a factory limit or an engine-safety guarantee. No clamp, rounding, conversion,
automatic table synchronization or required curve shape is added.

For each requested table, a separate arithmetic audit checks all 256 raw inputs,
strictly descending axes, nonzero denominators, bounded reads/indices, exact
nodes, unsigned full-width products and results between the participating nodes:

```text
lowerY +/- floor(abs(upperY-lowerY) * (x-lowerX) / (upperX-lowerX))
```

This checks the helper's finite domain, not producer reachability: the real base
producer uses an immediate override below 22. Rising, falling and flat value
segments are reported without normalization. Exact-form Rust regressions exercise
full-width MUL, DIV truncation/remainder and the already admitted `ADD A,er3`
direction. This is not the unresolved reverse operand form `ADD er3,A`.
Runner 0.10.0, its ISA permissions and old evidence versions are unchanged.

## Edit audit and compensation applicability

The separate versioned contract is `p28-idle-table-numeric-values-v1`.
The matching listing was checked against original instruction bytes (11499 rows)
and the established full-reader census (155 sites). The private edit dossier
extends, rather than replaces, the existing M1g reader/control-flow audit.

Idle lookup origins are literals 68CB/68E0. The axis scanner at 5894 advances by
three and stops at unchanged byte keys. Overlapping reads at 58A3/58A6/58AB use
byte exchanges to separate axes from reconstructed numeric values; values do not
become X1, a length, a stopping key or an encoded destination. The direct 3079
read sees only unchanged axis 68DA. Neighboring lower table origins terminate
before the editable words; higher origins begin at or beyond 68F5. Forwarded
origins retain the previously established caller bounds.

Base values may be saved numerically in DP, replaced by late lookup, then stored
to DATA025C. DATA027A remains separate. Significant downstream target readers
use numeric differences, filters and comparisons; selection at 30C4 chooses
among unchanged literal table origins, not target-derived program addresses.
Other target-as-key consumers at 326B/34C7/34D7 start at literal 6AFD/692D/6949/
6965; their unchanged zero-word stopping keys bound stride-four scans for any
unsigned target. This is a static bounds argument, not executed regulator proof.

Consequently pointer literals, strides, scanner keys, axis bounds, code/vector
destinations and stack operands retain the compensation audit's assumptions.
The old tail barrier and ordinary initialized/intact-state, valid-stack scope
remain explicit; arbitrary-PC/corrupt-state, global DD-flow and full ECU claims
are not added. Not observing the tail in a slice is only supplemental evidence.
The existing signed `VerifiedCompensationLocation`, original/profile/binding
checks, offset and original byte are reused without changing the definition or
signature. No issuer key is opened, new key created or location certified.

## One original, one composition

A is the exact unchanged original. B applies all requested numeric values in
memory. C makes one checksum compensation calculated from B's actual bytes:
`newByte = (originalByte - residueB) modulo 256`. Independent full-image sum8
requires A/C residue zero and an enabled recognized checksum. A meaningful
zero-residue edit leaves the compensation byte unchanged; word deltas are never
substituted for encoded-byte arithmetic.

The closed plan records version/purpose/contract, original identity/size,
profile/binding digests, requested and changed groups, every old/new cell and
axis, domain audit, compensation identity/scope/digest, A/B/C identities/residues
and exact diff. Apply reproduces the entire canonical plan from the original.
Serialized offsets or hashes do not authorize bytes. Full child comparison also
rejects foreign zero-sum byte pairs. A VTEC/limiter/idle child is not a new parent;
plans, children and receipts cannot be merged into a mixed lineage.

## Mandatory fresh execution and witnesses

Every apply generates its own plan-dependent corpus and executes actual A/B/C
bytes through existing `idleContexts`, plus the existing checksum runner. Each
image and scratch pattern (00/55/AA) has its own once-seeded native CPU/RAM and
independent C# history. The actual native DATA025C feeds the unchanged consumer;
expected targets, components and signs are not injected. Corpus chunks are
explicit separate sequences of at most 64 calls, not hidden history resets.

Coverage includes the base-retained reachable domain including genuine 22..39
fallthrough, all 256 late inputs, knots/neighbors/truncation, all established
immediate override types, late replacement, zero/nonzero component, selectors,
history and counter boundaries, repeated calls, masked transitions, old/new
target neighborhoods and representable sign/clamp boundaries. The full old
104094-checkpoint M1r corpus is not rerun per apply. The two unreachable M1r
component arms remain unforced and uncounted.

Each full trace is checked against its own image model. B/C must match complete
non-checksum observation digests, states, reads/stores and model histories.
A/C compare only dependency-independent source/component/counter controls;
changed intermediate base scratch need not match after late replacement.
Each changed table needs a combined-image native read -> changed final target
-> changed error/sign witness. A combined result is not attributed to one cell.

Per-cell summaries distinguish lookup not executed, cell not read, zero weight,
integer truncation, multiple-cell masking, late replacement and consumer clamp.
They include representative lookup results, weights, targets and error/sign.
One-cell **model-only in-memory diagnostics** separate quantization from combined
masking; these are explicitly not native evidence and never replace B/C execution.

Checksum validation is fresh: 3 images x 3 scratch patterns x 512 invocations,
with ordered coverage and intermediate states. B follows its own actual residue;
A/C follow the normal zero-residue path. Conditional/unresolved, incomplete,
wrong identity, mismatch, budget/process errors, missing runner, cancellation or
changed inputs prevent publication. No old ADD/SUBB permission is expanded.

## Publication and CLI

Only a typed, non-deserializable capability from the current validation process
can publish. Plan/evidence copies isolate nested collections; immutable input
snapshots and asynchronous rechecks preserve exact source identities. The shared
bounded process adapter and `ResearchOutputGroup` provide staged new-path
BIN/plan/receipt publication, rollback and independent readback. All three paths
must be new and distinct. Readback failure is not success; group power-loss
atomicity is not promised. Settings/plan/receipt bounds are 4 KiB/64 KiB/64 MiB;
mandatory evidence is never silently truncated.

Example settings are a raw PC test, not an RPM recommendation. Original values
are checked from the actual bound file, not inferred from this example:

```json
{
  "formatVersion": 1,
  "purpose": "explicit-idle-table-values",
  "baseTable": [1250, 1339, 1458, 1563, 2315, 3024, 3024],
  "lateTable": null
}
```

```shell
hondaecu research p28-idle export plan <original.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --compensation-definition <reviewed-location.json> --settings <idle-values.json> --output <new-plan.json>
hondaecu research p28-idle export apply <original.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --compensation-definition <reviewed-location.json> --plan <new-plan.json> --runner <runner> --confirm-pc-only --output <new-child.bin> --saved-plan <saved-plan.json> --report <receipt.json>
hondaecu research p28-idle export verify <new-child.bin> --baseline <original.bin> --profile p28-304 --baseline-binding <binding.json> --compensation-definition <reviewed-location.json> --plan <saved-plan.json> --report <receipt.json> --output <new-verification.json>
hondaecu research p28-idle export inspect <new-child.bin> --baseline <original.bin> --profile p28-304 --baseline-binding <binding.json> --compensation-definition <reviewed-location.json> --plan <saved-plan.json> --report <receipt.json> --output <new-inspection.json>
```

Readback/verify/inspect check the complete reproduced C, axes and unchanged
fields, identities, exact diff, residue and full reverse restoration of original.
They check historical receipt consistency, not authenticity of an old run, and
report fresh execution NotRun. They never mint a publication capability.
`--confirm-profile` cannot authorize an unknown image. Existing idle inspection
and target/context-check commands keep their read-only meaning.

## Validation record and limits

Public tests contain invented data and instruction programs only. New tests cover
the 14 footprints, selections/no-op, policies/schema/refusals, both interpolation
directions/plateaus/extremes, overlap, error8/sign, word carry and zero-sum
composition, lineage/evidence tampering, defensive copies and actual Rust process
refusals. Existing export rollback/readback and ISA/refusal regressions run intact.
Release .NET results: Core 716, CLI 311, Desktop 81; Rust 1.85.1: 138 tests.
Both explicit solutions build cleanly and pass formatting; Rust build/fmt pass.

Private actual memory-only batches passed for base one-cell (26910 strict calls),
late one-cell (25641), representative combined (27720), and two-table extreme/
multi-cell (33417, maximum 29-byte diff), each with nine checksum sequences.
An additional late two-cell masking batch passed 25695 strict calls and nine
checksum sequences with A/B/C residues 0/0/0 and unchanged compensation. At equal
47/94 weights the combined lookup stayed 1250, while isolated model diagnostics
identified cancellation of the two edits rather than integer truncation.
Exactly one new private combined firmware BIN was published by the final CLI
workflow, with a fresh 27720-checkpoint A/B/C batch and nine checksum sequences.
Four changed cells produced five changed bytes, including compensation, with
A/B/C residues 0/32/0. Representative combined base target 3024->3016 produced
error 0->8; late target 1438->1439 produced error 0->1 and a sign change.
Independent readback and separate verify/inspect passed. Private identities,
complete listing, bindings, signatures, reports and receipts stay out of Git.

The result ends at final target/error under explicit software snapshots.
Upstream acquisition/selector writers, counter-decrement scheduler, downstream
feedback/regulator/PWM, engine modeling, physical RPM/temperature and full boot
remain outside scope. GUI r3 is paused/NotRun; hardware/full boot are NotRun,
not unfinished M1s acceptance requirements. GUI code and prior portable folders
are unchanged; a clean CI portable diagnostic is not GUI acceptance.
