# M1t — unified basic-calibration research export

M1t combines established numeric fields into one original-parent BIN. It does
not integrate an entire ECU: VTEC prefix, limiter/adaptive and idle are three
independent seeded software suites on the same complete composition images.
No suite's output is injected as another suite's physical feedback. Upstream
writers, main-loop scheduling, IRQs, regulator feedback and hardware are outside
the established contracts. `physicalRpmAvailable=false`, `PcInspectionOnly /
NotFlashReady`; GUI r3 remains paused/NotRun. M1s and previous stages stay closed.

## Fields and policies

Every settings group is explicit and complete, or `null` (retain original).
All 63 nonempty selections are supported. Requested but unchanged groups remain
explicit no-ops. All-null/full no-op has a preview but cannot publish a BIN.

| Group | Code-owned mapping | Existing exporter policy |
| --- | --- | --- |
| `vtec` | One of `P28ThresholdLogic.GetSlots()`; one byte in its eight-byte block | Exact slot ID, integer 0..255; no other slot or RPM conversion |
| `fixed` | `P28LimiterInspector`: cut196A/196B, resume1967/1968 | `0 < cutRaw < resumeRaw < 65535` |
| `bank0` | Existing adaptive mapping: cut649B/649C, resume6495/6496 | Pair policy and all65536 raw00CE values, no target wrap and strict target order |
| `bank1` | Existing adaptive mapping: cut64A7/64A8, resume64A1/64A2 | Same independent policy with that bank's unchanged origins/coefficients |
| `baseTable` | `P28IdleTableFields`: 68CC+3*i, i0..6 | Seven values1..65534, original axes, all256 rawD9 interpolation inputs |
| `lateTable` | `P28IdleTableFields`: 68E1+3*i, i0..6 | Same packed integer policy, no table copying |

These are research-export policies, not factory limits or engine-safety advice.
VTEC comparison codes, fixed period thresholds, adaptive bases and idle periods
remain distinct numbers. There is no invented inter-group ordering or sync.
Shared pure descriptions/validators perform encoding and domain checks; the
new exporter has no independent offset map or arbitrary-offset interface.

Maximum footprint: 1+12+28 numeric bytes and one reviewed compensation =42
distinct offsets, not a writable range or expected actual diff. Opcode1969,
idle axes (including68DA/68F2), adaptive origins/coefficients, pointer literals,
overrides, peaks, flags, vectors, code, checksum routine/gate and all remaining
bytes are protected by whole-image reproduction.

## Combined edit audit and admission

M1g's original program-data/control-flow review, M1p's fixed/adaptive numeric
closure and M1s's interpolation/downstream audit apply jointly. Thresholds feed
comparisons without replacing independently selected table pointers; fixed
immediates stay numeric; adaptive bases are reset/floor/target terms; idle words
are reconstructed numerical interpolation outputs, not axes or scanner keys.
Overlapping reads retain original axis parts. Downstream numeric comparisons
and fixed-origin gain lookups do not convert outputs into program pointers.
Original zero-key bounds, strides, widths, vectors and encoded destinations
remain intact for the permitted numeric domains.

Disjoint addresses alone do not establish behavioral independence. Numeric
edits may change branches and histories; those source-listed alternatives are
inside the existing conservative scope. Ordinary initialized/intact RAM and
register banks and valid call/interrupt stacks remain explicit conditions.
This is not an arbitrary-PC, corrupt-state, global DD-flow or full-boot proof.
The private M1t audit records the joint argument and rechecks listing bytes and
relevant bounds. No new admission-affecting consumer was identified there.

The existing `VerifiedCompensationLocation` retains its signature, exact
original/profile/binding, offset7FFF, original byte and original software scope.
No issuer key, new signature, location, child binding or certification system is
introduced. The new versioned `p28-basic-calibration-composition-v1` contract
does not impersonate an M1g/M1n/M1o/M1p/M1s plan or receipt. Old formats and
admission remain strict; the combined child is not accepted as an old child.

## Composition, plans and evidence

A is the exact original. B is one copy containing all requested numeric edits.
C applies exactly one compensation to B:
`(originalCompensation - actualByteSum8(B)) modulo256`.
No chained exporters, merged BINs, word-delta approximation or copied previous
compensation is used. Meaningful cross-family cancellation can leave7FFF
unchanged. Family-only compatibility compares complete bytes, not plan formats.

The closed plan carries six groups in VTEC/fixed/bank0/bank1/base/late order,
requested/effectively-changed flags, original/new fields and encoded bytes,
unchanged context and domain results, original/profile/binding/location
identities, A/B/C hashes/residues, exact diff and separate suite scopes.
VTEC retains all eight original/new context bytes but at most one selected slot.
Settings are bounded at4KiB, plan128KiB, receipt128MiB. Old format bounds stay
unchanged. Unknown, duplicate, missing and contradictory selections are refused;
apply reproduces all metadata and every output byte from the admitted original.
Serialized offsets, domains, hashes and success-looking values grant no authority.

The receipt has separate VTEC, limiter/adaptive, idle and checksum evidence
sections. Native full state/write/trace observations are checked against each
image's independent model before compact complete observations/digests are
recorded. Mandatory run identities, exact coverage, model histories, relations,
checksum states and witnesses are rederived, not accepted from summary counts.
It contains no duplicated full trace bodies from older receipts.

Fresh, internally constructed, non-deserializable capability is issued only
after all mandatory strict suites and checksum finish. Input/runner snapshots
and rechecks, exact image membership and nested defensive copies are enforced.
No missing runner, permission, unresolved instruction, incomplete run, mismatch,
task/version error, cancellation or stale input can be promoted into capability.

Publication uses the existing `ResearchOutputGroup`: new distinct non-input BIN,
saved plan and receipt paths; staging, best-effort rollback and independent
readback. Oversized artifacts are refused before publication. Full child equality,
tuple/receipt identity, requested values, protected bytes, diff and sum8 are
rechecked; reversing the diff must restore the entire original. Readback failure
is not success (diagnostic files can remain). Group power-loss atomicity is not
promised. Verify/inspect are historical consistency only, not authentication of
past execution, a fresh native run or a new publication capability.

## Mandatory native coverage

The runner is0.11.0 with the same CPU/semantic-fix inventory, adding two bounded
threshold-only dispatches. Earlier runner versions remain compatible with their
established operations; only0.11.0 supports these new prefix operations.

- Changed VTEC: `basic-vtec-raw-prefix-all-codes-contexts-priors-enable-scratch-v1`
  (`vtecThresholdPrefix`), 256codes ×2contexts ×4prior combinations ×2enable
  paths ×3scratch =12288/image. The exact M1d entry122C and exits126D/1281,
  actual reads and predicate states are checked using the existing threshold
  model. Equality is strict `code > threshold`; disabled prior bits persist.
  Exact A/B/C changed-result sets and other-slot controls are checked. No G/F,
  ADD permission, M1k full chain, P1 request or physical output is run.
- Unchanged VTEC: `basic-vtec-unchanged-0-127-255-contexts-priors-enable-scratch-v1`
  (`vtecThresholdControl`), codes0/127/255 across all remaining axes,144/image.
- Changed limiter family: full existing
  `combined-limiter-groups-native-histories-v1`, including fixed old/new edges,
  both priors, P4/011B/RAM selection, independent inhibit, both adaptive banks,
  reset/update/hold/decrease/bounds, native counter bodies and persistent
  fixed→bank0→bank1→fixed histories. Each changed group needs a native
  source-read/fetch→threshold→request witness on the full combined images.
- Unchanged limiter family: `basic-unchanged-limiter-source-and-state-controls-v1`
  retains fixed equality/neighbors for all three fixed contexts, priors/inhibit,
  two bank source histories and all cross-context switch histories.
- Changed idle family: full existing
  `idle-table-abc-source-and-consumer-boundaries-v1`: reachable base low domain,
  late0..255, knots/neighbors, original overrides and late replacement,
  separate027A, history/selectors/counter boundaries, final target/error/sign/
  clamp and native changed-table witnesses. Existing cell-weight, truncation,
  joint masking and late-replacement summaries remain explicit. One-cell
  diagnostic images are model-only and never replace combined native execution.
- Unchanged idle: `basic-unchanged-idle-selectors-and-target-controls-v1`, one
  persistent24-call history: rawD9=0/40/135/255 and six selector combinations,
  covering base, late and immediate choices on each image/scratch.
- Checksum: exactly one M1f batch, A/B/C ×3scratch ×512invocations. Ordered
  full-ROM coverage and every intermediate state are verified. A/C follow
  ordinary zero-residue paths; B follows its actual residue and corresponding
  gate path, including cross-family zero-residue cancellation.

Compact unchanged-family controls are justified by the source-listed numeric
dependency/read boundaries, not claimed exhaustive for unknown ECU contexts.
Changed families never receive reduced corpora. Every suite receives all edits
in B/C. B/C complete established observations match; A/C comparisons follow
relevant dependencies and do not falsely equate intentionally divergent scratch
or inherited adaptive histories. Unchanged families' semantic outputs agree.
Full traces are checked against the model of their own image before reduction.

## CLI

All paths below are user-selected new private paths, not tracked fixtures:

```text
hondaecu research p28-calibration export plan <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --compensation-definition <reviewed-location.json>
  --settings <six-group-settings.json> --output <new-plan.json>

hondaecu research p28-calibration export apply <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --compensation-definition <reviewed-location.json> --plan <new-plan.json>
  --runner <runner> --confirm-pc-only --output <new-child.bin>
  --saved-plan <new-saved-plan.json> --report <new-receipt.json>

hondaecu research p28-calibration export verify <child.bin>
  --baseline <original.bin> --profile p28-304 --baseline-binding <binding.json>
  --compensation-definition <reviewed-location.json> --plan <saved-plan.json>
  --report <receipt.json> --output <new-verification.json>
```

`inspect` accepts the same tuple as `verify` and a separate new output path.
Settings purpose is `explicit-basic-calibration-selection`, formatVersion1;
all six keys are mandatory. `vtec` is `{slot,rawValue}`, `fixed` is
`{cutRaw,resumeRaw}`, banks are `{baseCutRaw,baseResumeRaw}`, and tables are
seven-element arrays. Each can be null, but objects cannot be partial. Offsets,
widths, fractions, exponents, extra keys and unknown slot IDs are rejected.
CLI prints requested/effective status, old/new values, one compensation/full
diff, separate fresh suite counts/witnesses and explicit downstream NotRun.

Public tests contain invented metadata/programs only. Private examples and
reports remain ignored. Standard CI artifacts are not GUI acceptance, hardware
validation or permission to flash an ECU.
