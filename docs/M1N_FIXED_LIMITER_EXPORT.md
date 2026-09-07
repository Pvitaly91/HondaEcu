# M1n — Fixed-context limiter checksum-preserving export

Base: `6cac3fc1f1e2a07ea80a11e818a88fb6f12aa96e`, explicitly fetched from
`origin/codex/p28-adaptive-limiter-thresholds-m1m`. Delivery branch:
`codex/p28-fixed-limiter-export-m1n`. M1l and M1m remain completed.

This is scoped original-parent PC research export, not a generic offset editor,
factory authentication, physical RPM conversion or hardware authorization.
**Fixed context only; adaptive tables unchanged.**

## Operand contract and pair policy

| Field | Exact operand footprint | Baseline raw | Selection |
| --- | --- | --- | --- |
| `fixed-context-cut` | `196A`, `196B` | 536 | Previous `0124.5` clear |
| `fixed-context-resume` | `1967`, `1968` | 552 | Previous `0124.5` set |

Both are unsigned little-endian word immediates. Inspector, planner, model and
verifier share the inspector's code-owned field mapping. The actual listing
boundaries and all three bytes of each instruction were checked against the
preserved baseline. `1966` is MOV DP,#word; `1969` is L A,#word.
**Opcode `1969` is not writable**: this is not one contiguous five-byte range.
JSON cannot choose a new offset, width, field or encoding.

P4.0 OR `011B.7` selects the fixed pair. Otherwise the limiter selects current
RAM `01A4/01A6`. Request iff unsigned rawPeriod is below the selected word;
equality clears this path's request. Previous request determines cut/resume.
The software consumer stops before `5596`, without a P2 access. Independent
`012A.7` can inhibit a mask update even after overspeed clears.

The exporter requires explicit integer final values satisfying
`0 < cutRaw < resumeRaw < 65535`. This is exporter policy, **not factory bounds
or an engine-safety guarantee**. No rounding, clamp, swap, RPM conversion or
automatic synchronization occurs. For a one-field edit, supply the unchanged
other value explicitly. No-op has a valid zero-diff preview but cannot publish
a firmware BIN. Equal/reversed/sentinel observations remain valid M1l research;
this new exporter simply declines to publish such pairs.

Adaptive tables, their coefficients, selector flags, VTEC fields, native checksum
code/gate and every other ROM byte remain unchanged except the admitted tail byte.
RAM addresses are not reinterpreted as editable ROM offsets.

## Two distinct admission grounds

The versioned `p28-fixed-limiter-operands-v1` edit contract is separate from the
unchanged signed `VerifiedCompensationLocation`. The old M1c/M1g formats retain
their strict VTEC semantics; no fictitious VTEC slot or child is used.

The existing location verifier still requires its pinned signature and exact
original hash/profile/binding/old byte, recognized enabled checksum code and
zero original residue. No new key, issuer, definition, offset or trust import
is introduced. A self-created binding cannot manufacture location authority.

The M1g location audit is applicable under its original bounded software scope:

- Both outcomes of conditional branches were already included in its conservative
  control-flow review. Numeric limiter operands change comparisons, not encoded
  branch targets, vector words, instruction widths or the graph's target set.
- Resume is loaded into DP as a **numeric comparison value**, not a program
  pointer; `197C/197D` consume it as the selected threshold. The limiter has no
  program-data read. Subsequent A is overwritten at `1A38`; the later direct DP
  use has a new literal at `1B5E`. Intervening `5839` calls use freshly assigned
  X1 table origins, not the threshold DP value.
- Pointer-origin literals, scanner zero-key barriers, calibration strides and
  software-clamped axis-cache bounds used by the location audit are unchanged.
  The audit included both software mode alternatives, not one threshold outcome.
- M1m's producer reads remain in its original table banks; numerical cut/resume
  operands do not change those pointer constructions or table contents.

M1g's final VTEC-specific non-interference statement is **not** a blanket code-edit
permission. The new operand-value-flow review above supplies the missing edit
applicability argument. It preserves the original exclusions: ordinary initialized
RAM/register banks and valid stacks, no arbitrary corruption/PC, no external-code
mode, hardware-map validation, full DD-flow proof or full ECU execution.
Dynamic non-observation of the compensation byte supplements, not replaces, this
static argument. The location is not called globally unused or factory storage.

## A/B/C arithmetic and lineage

A is the unchanged admitted original; B applies only requested operands in memory;
C applies the reviewed compensation to B. The existing M1f sum8 implementation
calculates the full image residue. Compensation uses the existing pure M1g formula:

`newByte = (oldByte - residueB) mod 256`.

It does not use numeric word deltas. `00FF → 0100` changes the word by one but
the byte sum by two modulo 256. A nontrivial edit may have residue B zero; then
compensation remains unchanged. Full C arithmetic is recalculated independently.
The maximum footprint is four operand bytes plus one compensation byte, while
the actual diff contains only changed bytes. No exact fixed diff count is imposed.
An extra equal-and-opposite byte pair is rejected even if the checksum is zero.

The closed version-1 plan records purpose, contract, original size/hash,
profile/binding identities, requested pair, old/new encoded words, location
identity/scope, compensation, A/B/C residues, exact diff and PC-only limits.
Reproduction derives every byte and field again from original and trusted code;
serialized offsets, old bytes, residues and output hash do not authorize themselves.
Unknown/duplicate/missing fields and stale or contradictory metadata are refused.

Only `original -> limiter child` is admitted. Neither an M1c/M1g VTEC child nor a
previous limiter child may become the parent. Another pair requires another plan
from the original. Derived inspection verifies the full original/plan/receipt tuple
without creating a child baseline binding or pretending it matches the original.

## Mandatory native validation

Apply always generates deterministic corpus
`fixed-limiter-abc-boundaries-and-adaptive-controls-v1`; an external scenario
cannot replace or shrink it. No instruction permissions are enabled or widened.
Runner version 0.8.0, CPU/Bus/executor and M1l/M1m tasks are reused unchanged.

- Sixteen limiter scenarios: both prior states, independent inhibit clear/set,
  fixed-P4, fixed-011B, RAM-only and fixed/RAM/fixed histories. Sorted unique
  old/new equality and neighboring values are traversed descending then ascending;
  endpoint construction uses bounded integers without ushort overflow.
- Eight M1m control scenarios: both prior states/inhibits, RAM-only and fixed-to-RAM
  sequences, both banks, native ticks, hold/update/reset and raw00CE changes.
- Each scenario executes A, B and C separately with three scratch patterns. Each
  image retains its own CPU/RAM and independent model history. No state alignment
  is performed after deliberate fixed-context divergence.
- M1l/M1m parsers compare actual operands, branches, state, ordered stores,
  exits and native table reads with independent C# models. Every limiter call must
  show actual immediate-fetch coverage of all four operand bytes. All slice
  code/data ranges exclude the compensation byte.
- B/C full observation digests and outcomes must agree. RAM-only A/B/C persistent
  state digests and outcomes must agree, including adaptive words and counters.
  Incidental immediate-load register values can differ before being overwritten
  by RAM selection; they are not falsely required to be identical across A/C.
- M1f runs all A/B/C images for 512 invocations per scratch pattern. The existing
  parser checks every intermediate state, ordered full-ROM coverage, instruction
  accounting and actual residue/exit. A/C require ordinary zero-residue pass.
  B is checked against its actual residue, including either zero or nonzero.

Missing runner, mismatch, unresolved/conditional result, incomplete coverage,
execution/budget failure, cancellation or changed inputs cannot yield a publication
capability. The internal typed token binds exact images, plan and live evidence;
JSON claiming Pass cannot construct it. Plan/evidence collections are defensively
copied on exposure. Receipt interpretation never creates this capability.

## Publication and readback

`ResearchOutputGroup` is a narrow extraction from the old M1g writer. Both writers
reuse existing atomic staging/new-path and best-effort rollback helpers; M1g
admission remains unchanged. BIN, saved plan and receipt require three different
new paths and cannot overwrite inputs or existing destinations. CLI snapshots all
inputs, including runner/profile, and rechecks them after asynchronous execution.
Core additionally rechecks original/profile and protected files before publication.

Cancellation is honored before publication; once the group starts, rollback and
readback finish rather than abandoning it halfway. Multi-file power-loss atomicity
is **not** promised. Publication failure rolls back the newly created plan where
possible. Readback failure throws, retains diagnostic artifacts and is not success.

Readback reloads all three files and repeats exact original-parent reproduction,
size/hash, pair encoding, full diff, sum8, plan/location/binding identity and receipt
accounting. Replacing every changed byte by its original value must reproduce the
entire original byte-for-byte. Receipt outcomes/states are independently rederived
from the deterministic corpus too. This checks consistency, **not authentication
that historical execution occurred**. Fresh execution is explicitly NotRun during
verify/inspect; a new apply must execute again.

## CLI workflow

These raw values are a PC test, not RPM or a vehicle recommendation. Paths are
explicit private examples; every destination must be new.

```text
hondaecu research p28-limiter export plan private/oracle/p28-304/base.bin --profile p28-304 --confirm-profile --baseline-binding private/reports/m1b/baseline-binding.json --compensation-definition private/reports/m1g/compensation-location.json --cut-raw 540 --resume-raw 556 --output private/reports/m1n/paired-plan.json

hondaecu research p28-limiter export apply private/oracle/p28-304/base.bin --profile p28-304 --confirm-profile --baseline-binding private/reports/m1b/baseline-binding.json --compensation-definition private/reports/m1g/compensation-location.json --plan private/reports/m1n/paired-plan.json --runner rust/p28-slice-runner/target/release/p28-slice-runner.exe --confirm-pc-only --output private/roms/p28-304/m1n-fixed-limiter-pc-only.bin --saved-plan private/reports/m1n/saved-plan.json --report private/reports/m1n/export-receipt.json

hondaecu research p28-limiter export verify private/roms/p28-304/m1n-fixed-limiter-pc-only.bin --baseline private/oracle/p28-304/base.bin --profile p28-304 --baseline-binding private/reports/m1b/baseline-binding.json --compensation-definition private/reports/m1g/compensation-location.json --plan private/reports/m1n/saved-plan.json --report private/reports/m1n/export-receipt.json --output private/reports/m1n/verification.json

hondaecu research p28-limiter export inspect private/roms/p28-304/m1n-fixed-limiter-pc-only.bin --baseline private/oracle/p28-304/base.bin --profile p28-304 --baseline-binding private/reports/m1b/baseline-binding.json --compensation-definition private/reports/m1g/compensation-location.json --plan private/reports/m1n/saved-plan.json --report private/reports/m1n/export-receipt.json --output private/reports/m1n/inspection.json
```

On non-Windows hosts omit the runner's `.exe` suffix. Plan writes no firmware and
does not claim native execution. Apply validates before saving. Verify and inspect
are read-only with a separate new JSON result.

## Verification record and delivery limits

Private in-memory previews checked cut-only 536/552 → 540/552, resume-only
→ 536/556, paired → 540/556, and unchanged no-op. Their A/B/C residues were
respectively 0/4/0, 0/4/0, 0/8/0 and 0/0/0; actual diff counts 2, 2, 3 and 0.
The paired mandatory batch has **3,456 strict limiter calls, 720 strict adaptive
calls and nine strict 512-invocation checksum sequences**. No conditional,
unresolved, incomplete, mismatch or execution error was accepted. Repeated
development validation runs are not added to these per-batch coverage counts.

Cut-only and resume-only also each passed a complete in-memory mandatory batch:
2,592 strict limiter calls, 720 adaptive calls and nine checksum sequences.
The actual paired CLI apply repeated its complete validation and published exactly
one new private 32 KiB PC-only BIN. Only `1967`, `196A` and the admitted `7FFF`
changed; `1969` and all adaptive tables remained unchanged. Its saved plan and
receipt passed immediate independent readback, separate CLI verify and derived
inspection. No-op apply was refused without firmware publication. These are
actual execution/readback results, not synthetic stand-ins. CI status is reported
separately against the delivered commit.

For the paired fixed-P4 sequence (prior clear, inhibit clear, scratch zero), call
8 at raw539 has A threshold536/request false and B/C threshold540/request true.
On the ascending traversal, call19 at raw552 clears A at equality552 but B/C
retain request against556. B/C histories and consumer observations agree exactly.
Independent inhibit controls remain separate from that request change.
Public tests contain invented arithmetic data and small synthetic instructions,
not reconstructed OEM routines. They preserve old M1c/M1g/limiter/adaptive and
headless Desktop regressions, and cover refusal, raw integer arithmetic, exact
footprints, mandatory corpus, real subprocess strict stops, defensive aliases,
cancellation and shared writer rollback/readback failures.

Fifteen additional private negative checks rejected stale plans/receipts,
changed outcomes, incomplete checksum evidence, extra zero-sum diff, opcode edits,
VTEC/limiter child parents and missing runner. A live capability also passed alias
isolation, pre-publication cancellation and writer rollback checks without another
firmware BIN. Local regression totals are 560 Core, 196 CLI, 81 Desktop headless
and 121 pinned Rust tests; both explicit solutions and formatting are checked.

The stage preserves 4,076 previous private inputs/reports and portable files.
Private ROMs, identities, listing, signed documents, plans/receipts and actual
observations remain ignored and absent from Git and public artifacts. No existing
portable is republished. The standard clean CI portable is not GUI acceptance.

`physicalRpmAvailable=false`; `PcInspectionOnly / NotFlashReady`.
GUI r3 paused/NotRun; hardware/full boot NotRun, excluded from M1n completion.
No GUI code, Computer Use, programmer/ECU writing, physical clocks, upstream G
integration, scheduler/IRQ emulation, adaptive editing, signing infrastructure,
editor installation or other firmware family is introduced. Stop after this stage.
