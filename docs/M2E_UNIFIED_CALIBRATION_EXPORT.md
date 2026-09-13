# M2e unified known-calibration checksum-preserving export

M2e composes the ten established P28-304 calibration groups into one PC-only
original-parent workflow. One closed settings document produces one immutable
preview, one intermediate B image, one compensated C image, one fresh native
validation chain and, only after strict completion, one BIN/saved-plan/receipt
group. It is not an arbitrary-offset editor, a chained application of M1t/M2b/M2d
children, a common ECU main loop, a GUI feature or hardware authorization.

Every output remains PcInspectionOnly / NotFlashReady.
physicalRpmAvailable=false; fuel units, physical ignition degrees, hardware
execution and full boot are unavailable/NotRun.

## Closed settings and writable groups

The settings purpose is explicit-p28-calibration-set; all three family objects
and all ten keys are required:

~~~json
{
  "formatVersion": 1,
  "purpose": "explicit-p28-calibration-set",
  "basic": {
    "vtec": null,
    "fixed": null,
    "bank0": null,
    "bank1": null,
    "baseTable": null,
    "lateTable": null
  },
  "fuel": {
    "map_0": [],
    "map_1": null
  },
  "ignition": {
    "ignition_map_0": null,
    "ignition_map_1": []
  }
}
~~~

For basic groups, null retains the original and a non-null object/table is the
complete established M1t request. For maps, null means not requested, [] means
explicitly requested with no entries, and an array contains final raw u8 values
for unique row/column coordinates. Explicit unchanged entries retain their
requested provenance but do not become byte changes. Input property order and
map-entry order do not affect the canonical plan or firmware bytes.

| Group | Code-owned writable values |
| --- | --- |
| basic.vtec | one selected raw byte from the established eight-slot block |
| basic.fixed | cut/resume operands only; opcode at 1969 is immutable |
| basic.bank0, basic.bank1 | two established adaptive base words per bank |
| basic.baseTable, basic.lateTable | seven packed idle values per table |
| fuel.map_0, fuel.map_1 | 20×10 u8 cells at 7050..7117 and 7122..71E9 |
| ignition.ignition_map_0, ignition.ignition_map_1 | 20×10 u8 cells at 72E4..73AB and 73AC..7473 |

The maximum request contains 800 map coordinates. The maximum code-owned
firmware footprint is 842 different offsets: 41 basic numeric bytes, 800 map
cells and the one existing compensation byte. This is a bound, not an expected
diff count.

Unknown or duplicate properties, duplicate map coordinates, arbitrary offsets,
fractions, overflow, physical units, percentages, silent clamp/round/swap,
smoothing, synchronization and force modes are rejected. Seven unselected VTEC
bytes, axes/sentinels, fuel multipliers, adaptive origins/coefficients, idle
axes/overrides/peaks, alternate ignition maps, selectors/gates, pointers,
vectors, code and every other byte remain immutable.

## One original, one compensation and reproducible plan

The contract ID is p28-known-calibration-set-v1.

1. A is the unchanged exact original admitted by the existing profile, private
   exact binding and signed VerifiedCompensationLocation.
2. B applies all requested numerical edits once to one copy of A.
3. C changes B only at the established compensation location, using
   (originalCompensation - residueB) modulo 256.

The existing signature, location, original-byte check, profile/binding and
reviewed source scope are unchanged. M2e creates no issuer key, signature,
location or child binding. A meaningful multi-family edit may have residue B
zero; in that case the compensation byte remains unchanged.

The plan records all ten requested/no-op/byte-changed/behavior-changed groups,
original and requested values, encoded bytes, full map-domain audits, immutable
range digests, A/B/C identities and residues, one compensation, exact full diff
and the mandatory suite schedule. Apply reconstructs settings and the complete
plan from the exact original and code-owned mappings. Serialized offsets,
hashes, counts, audit rows or success-like text cannot authorize themselves.
The whole C image is compared byte-for-byte, so extra zero-sum edits are rejected.

## Reused arithmetic and distinct map semantics

M2e reuses the M1t fixed/adaptive and idle finite-domain policies without new
physical interpretations. Each fuel and ignition map is audited over all 65,536
raw selected-RPM/load pairs using the established sequential integer Q16 model.
This is model arithmetic, not 65,536 ROM executions.

Fuel cells are multiplied by their immutable per-column multipliers before the
two column and one row interpolation stages. Ignition primary cells are unity
scaled and have no fuel multipliers. Its separate immediate consumer preserves
factor zero as bypass and uses the high byte of the unsigned product for a
nonzero raw factor. That factor is an execution-model input, not a writable
calibration field; DATA0247 is never added to settings.

Fuel DATA0127.1 and ignition DATA0227.5 selectors, their fixed caller gates,
separate load caches/fractions and ignition DATA0238/DATA00C2 behavior remain
different software contracts. M2e does not invent one physically synchronized
selector snapshot.

## Fresh validation and typed capability

Each suite receives the same complete A/B/C images. Changed basic families use
their established full plan-dependent corpora; unchanged basic families receive
their deterministic source/state controls. Fuel uses the M2b rectangle/cell,
cache-history and DATA0140 consumer corpus. Ignition uses the M2d factor-zero
rectangle/cell corpus plus once-seeded factors 1, 127, 128, 173 and 255 through
DATA0248. B and C must match for all verified non-checksum observations.

These are separate seeded software suites. CPU/RAM lifetime is retained within
each suite sequence but is not shared across VTEC, limiter, idle, fuel and
ignition suites. No scheduler, IRQ model, feedback loop or full ECU execution
is claimed.

After all local suites, M2e performs exactly one native checksumBatch over
A/B/C × scratch 00/55/AA, with 512 ordered invocations per sequence and full-ROM
coverage. A and C must have residue zero; B follows its actual residue/path.
Runner identity and bytes are checked across the whole chain. Cancellation,
incomplete or mismatched observations, missing/wrong runner, changed inputs or
stale plan prevent capability creation.

P28VerifiedUnifiedCalibrationExport has no public constructor and is not
deserializable. Its defensive evidence snapshot is bound to the current plan
and full images. A receipt or family-only capability cannot mint it.

Publication reuses ResearchOutputGroup: three distinct new non-input paths,
input snapshots/rechecks, staged writes, best-effort rollback and independent
readback. The result is exactly one BIN, one saved plan and one receipt. Readback
checks complete bytes, lineage, requested values, immutable ranges, full diff,
checksum and reverse restoration. Group power-loss atomicity is not promised.

## CLI

~~~text
research p28-calibration combined-export plan <original.bin>
  --profile p28-304 --confirm-profile
  --baseline-binding <binding.json>
  --compensation-definition <reviewed-location.json>
  --settings <combined-settings.json> --output <new-plan.json>

research p28-calibration combined-export apply <original.bin>
  --profile p28-304 --confirm-profile
  --baseline-binding <binding.json>
  --compensation-definition <reviewed-location.json>
  --plan <plan.json> --runner <p28-slice-runner>
  --confirm-pc-only --output <new-child.bin>
  --saved-plan <new-saved-plan.json> --report <new-receipt.json>

research p28-calibration combined-export verify <child.bin>
  --baseline <original.bin> --profile p28-304
  --baseline-binding <binding.json>
  --compensation-definition <reviewed-location.json>
  --plan <saved-plan.json> --report <receipt.json>
  --output <new-verification.json>

research p28-calibration combined-export inspect <child.bin>
  --baseline <original.bin> --profile p28-304
  --baseline-binding <binding.json>
  --compensation-definition <reviewed-location.json>
  --plan <saved-plan.json> --report <receipt.json>
  --output <new-inspection.json>
~~~

The older research p28-calibration export, research p28-fuel export and
research p28-ignition export routes, formats and scopes remain unchanged.
For identical family-only settings, M2e produces firmware bytes identical to
the corresponding M1t, M2b or M2d result; plan and receipt formats are distinct.

verify and inspect establish bounded historical consistency. They do not rerun
native execution, authenticate the past event, turn the child into a new
original or issue a fresh publication capability.

## Validation record and limits

The private final workflow selected a small change in every one of the ten
groups. It requested and changed eight map cells. Its exact C diff contains 22
bytes, including one compensation change; residues A/B/C are 0/68/0.
Fresh strict observations completed for VTEC prefix, fixed/adaptive limiter,
idle, fuel, ignition factor-zero and all required nonzero factors. One checksum
batch completed nine A/B/C/scratch sequences. One private 32 KiB BIN, saved plan
and receipt passed independent readback and separate CLI verify/inspect; reverse
diff restored the exact original.

Public tests cover the 1,023 nonempty group selections at settings/encoding
level, all eight VTEC slots, all 800 map coordinates, null/empty/explicit
unchanged semantics, canonical order, maximum footprint, family-only byte
compatibility, closed-plan rejection, alias isolation and cancellation before
publication. Existing per-family Rust integration tests remain the independent
invented-program subprocess coverage.

This delivery adds no GUI code. GUI r3 remains paused/NotRun, D1 interactive GUI
acceptance remains NotRun, D2 remains NotStarted, and hardware/full boot remain
NotRun. M2e does not complete all of M2, the M1 oracle/physical gates, physical
tuning semantics or a full ECU emulator.
