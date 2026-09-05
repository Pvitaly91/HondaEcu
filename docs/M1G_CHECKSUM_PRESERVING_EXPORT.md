# M1g - Checksum-preserving PC-only export

Base: `origin/codex/p28-native-checksum-validation-m1f`,
`8915207ea6e2b8bd9473067ea9654246c0146239`.
Work branch: `codex/p28-checksum-preserving-export-m1g`.

M1g adds a separate research composition: **original baseline -> one existing
raw-threshold edit + one computed compensation byte -> new PC-only output**.
The native checksum remains enabled and unchanged. Zero residue is not evidence
of behavioral equivalence, factory provenance or vehicle safety. All plans,
reports and outputs remain **PcInspectionOnly / NotFlashReady**.

## Reviewed location and non-interference scope

The selected CompensationLocation is program byte **0x7FFF**, for the exact
privately reviewed baseline/profile/binding only. It is not called
FactoryChecksumStorage. No location is inferred from size, an FF value, a hash,
a checkbox, a successful checksum or absence from seeded slices.

The historical [CheckSum](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/bin/view/Library/CheckSum.html)
and [ManualChecksum](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/bin/view/Library/ManualChecksum.html)
pages describe byte-sum compensation and examples using apparently unused space.
They are general leads, not a writable definition for this revision. M1g's
location comes from two separate private source audits:

| Access class | Reviewed exclusion or use |
|---|---|
| Instruction fetch and operands | The live helper at `0x7FF0` ends with an unconditional jump at `0x7FFB`, whose final operand ends at `0x7FFD`. It does not fall through into the last word. |
| Direct and indirect control | All 28 actual reset/interrupt/VCAL vector words and the existing 11,499 instruction rows were surveyed. All 3,321 encoded branch targets match their labels; the 14,282-edge conservative graph has no edge into data or the candidate. Normal RT/RTI saved continuations are separate from arbitrary corrupted-stack targets. |
| Program-data reads | All 155 LC/LCB/CMPC/CMPCB sites were classified: 62 fixed and 93 indirect/indexed. Caller pointers, index bounds, word overlap, finite copies and forward walkers were inspected. No identified non-checksum reader reaches the candidate in this scope. |
| Calibration walkers/matrices | Literal or bounded forwarded table pointers, unchanged stopping keys and initialized/bounded cached axes prevent their reads reaching the last word. A table value moved into a register was not automatically treated as another program pointer. |
| Serial/diagnostic modes | The program address-table read is bounded; its following access and raw monitor are DATA-space reads. Reviewed command/reset handlers perform fixed RAM operations and bounded ROM copies, not an arbitrary program-memory dump. |
| Native checksum | The final word read intentionally includes `0x7FFE`/`0x7FFF`. This is permitted contribution coverage, not proof of non-interference by itself. |

The scope is the source-listed reset, interrupt, VCAL and normal direct-call
paths, their register-bank/addressing conventions, initialized bounded cached
indices, and ordinary intact RAM/call/interrupt-stack operation. Both sides of
known software mode branches, including serial and retained-RAM restart paths,
were considered. The review is not a global DD-flow proof, arbitrary-PC or
corrupt-state proof, hardware memory-map validation, external-code-mode analysis
or full ECU boot. No concrete unresolved non-checksum access that can reach the
candidate remains within the recorded scope. Those qualifications remain part
of the definition and every composition; the region is not called globally unused.

The other byte of the final word also passed these bounded exclusion checks,
but the implemented policy selects exactly one fixed location. There is no
arbitrary offset argument, force switch, public issuer import or generic
repair-any-ROM operation.

## Definition identity and authority

The reviewed definition is a private, versioned document binding the exact
original ROM hash, profile/binding digests, location/original byte, candidate
contract, consumer audit, evidence identity and limitations. Its signature is
verified using one pinned public review key. Production code contains verification
only; no private issuer key or signing/import workflow is shipped.

The signature authenticates which audit was reviewed. **It does not prove that
the audit is true**; the source/control-flow and consumer arguments above supply
the justification. A digest identifies an input/document, not a conclusion.
Signed identity data, audit notes and original hashes remain private; the public
profile gains no factory identity or generic writable parameter.

Missing, unsigned, altered, stale, ineligible or wrong-contract definitions are
explicit refusals. Rebinding an arbitrary ROM cannot manufacture this authority.
Applications do not discover private material automatically. Without an eligible
definition, preview/export for that real input remains blocked with a reason.

## Arithmetic and composed plan

The existing M1f unsigned sum8 contract is reused, not rediscovered. The original
must have zero residue and recognized, enabled, unaltered native code. Existing
M1c planning creates exactly one requested threshold edit in memory. If its
intermediate residue is R and the admitted compensation byte is B:

```text
B_new = (B - R) modulo 256
```

The implementation uses exact byte/integer arithmetic, including negative
intermediate subtraction. The final full-ROM sum is recomputed independently.
For a genuine one-byte threshold change, exactly two distinct offsets change;
a no-op has zero changed bytes and no artificial compensation. Neither the gate,
checksum code, vectors nor another active threshold/calibration may be used.

The old M1c format remains strictly one-slot. The new composed-plan format 1.0
contains the original hash and digests, unchanged underlying M1c plan, reviewed
definition identity/digest, computed old/new compensation, exact complete diff,
baseline/intermediate/final residues, checksum contract and PC-only scope.
Unknown versions/fields, duplicates, malformed or stale metadata and substituted
offsets/values/formula are rejected. Applying reproduces the plan from original
bytes and authority; serialized expected values do not authorize themselves.

There is still one original parent. A verified existing M1c child can contribute
its complete original-parent/plan/report tuple; the same threshold operation is
recreated from the original. The child is not rebound or patched as a new parent.
Repeated application to the final output is refused.

## Execution gate, publication and readback

Planning is not native execution. A non-deserializable export capability is
created only after the existing Rust process adapter actually observes all
baseline/output scratch cases complete 512 native invocations, exact ordered
full-ROM coverage, zero residue and the ordinary pass path, without assumptions.
Missing runner, cancellation, conditional/unresolved execution, mismatch or
budget/error results cannot authorize publication.

The shared writer publishes BIN, a new composed-plan copy and an export receipt
using the existing staging/new-path and best-effort rollback helpers. Input paths,
existing destinations and aliases are protected; the CLI also checks protected
input snapshots after the asynchronous validation. Cancellation is checked before
publication. Once the file group begins, rollback/readback completes instead of
abandoning a partial group. Power-loss atomicity across three files is not promised.

Readback reloads BIN, plan and receipt; repeats complete diff, arithmetic and
original-parent lineage verification; and restores the two old bytes in memory
to reproduce the entire original. A readback failure is not a successful export.
The receipt records compact historical native observations, not a reusable export
capability. Its version, runner/fix identity and complete zero-path accounting
are checked. Reopening a receipt is **not fresh execution or authentication of
its historical claim**; a new export always requires the runner again.

The common composition admission is used by derived inspection and M1d/M1e/M1f
execution APIs. It does not weaken the old one-byte verifier by ignoring a second
byte, and mixed old/new lineage is rejected. Changed-file inspection retains the
original binding rather than fabricating a new baseline match.

## CLI

The following paths are explicit private workflow examples. Raw values are not
RPM recommendations. `--runner` needs `.exe` on Windows.

```shell
hondaecu research p28-vtec compensation-check private/oracle/p28-304/base.bin --profile p28-304 --confirm-profile --baseline-binding private/reports/m1b/baseline-binding.json --compensation-definition private/reports/m1g/compensation-location.json --output private/reports/m1g/availability.json
hondaecu research p28-vtec checksum-export-plan private/oracle/p28-304/base.bin --profile p28-304 --confirm-profile --baseline-binding private/reports/m1b/baseline-binding.json --compensation-definition private/reports/m1g/compensation-location.json --slot context_0.pair_0.state_0_threshold --raw-value 128 --output private/reports/m1g/composed-plan.json
hondaecu research p28-vtec checksum-export-apply private/oracle/p28-304/base.bin --baseline-binding private/reports/m1b/baseline-binding.json --compensation-definition private/reports/m1g/compensation-location.json --plan private/reports/m1g/composed-plan.json --runner rust/p28-slice-runner/target/release/p28-slice-runner --confirm-pc-only --output private/roms/p28-304/m1g-pc-only.bin --saved-plan private/reports/m1g/export-plan.json --report private/reports/m1g/export-receipt.json
hondaecu research p28-vtec checksum-export-verify private/roms/p28-304/m1g-pc-only.bin --baseline private/oracle/p28-304/base.bin --baseline-binding private/reports/m1b/baseline-binding.json --compensation-definition private/reports/m1g/compensation-location.json --plan private/reports/m1g/export-plan.json --report private/reports/m1g/export-receipt.json --output private/reports/m1g/export-verification.json
hondaecu research p28-vtec checksum-export-inspect private/roms/p28-304/m1g-pc-only.bin --baseline private/oracle/p28-304/base.bin --baseline-binding private/reports/m1b/baseline-binding.json --compensation-definition private/reports/m1g/compensation-location.json --plan private/reports/m1g/export-plan.json --report private/reports/m1g/export-receipt.json --output private/reports/m1g/export-inspection.json
```

To use the existing M1c child, replace `--slot`/`--raw-value` in the plan command
with all three `--derived <M1c-child> --plan <M1c-plan> --patch-report <M1c-report>`.
These routes are mutually exclusive. The positional input remains the original.
An unavailable compensation check returns a verification-failure exit, writes its
read-only availability report, and does not create a BIN. Legacy raw-save remains
separate and is never silently upgraded into checksum preservation.

## Actual A/B/C observations

The private in-memory comparison uses distinct original A, threshold-only B and
threshold-plus-compensation C images; it does not equate checksum success with
predicate behavior.

| Representative image | Native checksum | Threshold behavior |
|---|---|---|
| A: original |Valid, zero residue|Baseline predicate|
| B: one threshold edit |Invalid, nonzero residue|Exactly the expected changed-case set|
| C: threshold plus compensation |Valid, zero residue|Equals B throughout the checked M1d threshold domain|

Two actual M1f A/B and A/C batches produced 12 strict native sequences, counting
their repeated baseline separately. The full M1d threshold domain is 12,288 cases
per image: B and C agree throughout, and both A/B and A/C retain exactly 6 expected
changed cases. Recorded word-read addresses exclude the compensation byte,
including overlapping word reads. This is a bounded observation in addition to,
not a replacement for, the static consumer audit.

A representative matrix tested raw 0/raw 255 for each of the 8 slots. Its 33 images
(one original plus 16 intermediates and 16 compositions) produced 99 strict native
sequences. Together these are 111 completed 512-invocation checksum sequences,
with no conditional/unresolved/mismatch/error/budget outcomes. Counts describe
actual executions, not distinct ECUs or exhaustive threshold/producer histories.
The reused strict compact batch still separates 372,120 established matches from
21,096 unresolved cases; neither word-ADD hypothesis is promoted by checksum.

The actual CLI workflow then published exactly one new private PC-only BIN,
composed-plan copy and receipt, and passed readback, full-tuple verification and
derived inspection. Original inputs were preserved. Its native admission added
6 strict sequences. A headless Desktop/service workflow added another 12:
6 for export admission and 6 for the reopened child's native checksum check.
The recorded total is therefore 129 completed strict native sequences, without
counting synthetic tests or subsequent GUI activity.

The headless Desktop checks also exercised recreation from the existing M1c
parent tuple, exactly two changes and the expected residues, missing-runner
refusal, protected-original write refusal before publication, session
invalidation, shared derived readback and cancellation. They created no second
BIN. Public CLI regression tests use unrelated synthetic fixtures; all 59 CLI
tests passed at this checkpoint. Final solution/package totals are reported
separately with the task results.

Final follow-up checks added 6 strict native sequences to exercise actual-token
write failure/rollback and pre-publication cancellation: **135 total**. Zero-sum
altered-code/gate controls, a self-rebound unknown image, repeated application and
a tampered review scope were rejected; no additional BIN was published.

A bounded M1e follow-up used two strict batches of 12 selected cases. Per batch,
producer G had 6 matches and 6 unresolved cases; F and each threshold image had
6 matches and 6 not-run cases. The 6 completed B/C predicate pairs agreed; the
other 6 were not counted as passes. The 32 observed program-byte reads (16 word
reads) did not overlap the compensation byte. G/F execute the original image in
this existing staged protocol; this is not a claim that G executed C. No ADD
assumptions were enabled and no conditional/mismatch/error/budget result occurred.

Local verification passed 313 Core, 59 CLI, 68 Desktop and 62 Rust tests, with no
skips. The arithmetic test separately checked all 65,536 byte/residue pairs; the
new synthetic A/B/C execution test used real Rust subprocesses. Formatting,
new-path self-contained publication and outside-repository startup diagnostics
passed. Actual portable GUI smoke covered launch, separate M1g tab, missing
admission, demo no-op, raw-255 two-byte preview, stale-preview reset and disabled
demo execution/export. Private lineage dialogs and publication were not tested
through GUI; the actual CLI and headless Desktop checks above cover those paths.

## Desktop, packaging and remaining limits

The Desktop extension is a separate explicit checksum-preserving workflow, not
a modification of the legacy raw Save semantics. It requires a reviewed private
definition, shows the requested threshold and computed compensation separately,
and retains asynchronous cancellation/session freshness and original-parent
lineage. Missing definition displays a blocker; missing runner prevents verified
save. Synthetic demo can show arithmetic but cannot create Honda authority or
publish a synthetic result as an OEM-verified export.

GUI interaction outcomes are recorded separately in the task's final results and
private check log. Builds, offscreen layout tests, ViewModel/service tests and
no-window portable diagnostics are not GUI interaction and are not counted as
GUI passes. Previously interrupted checks are not assumed to have passed.

Publish into a new folder, preserving the D0 and M1f packages:

```powershell
./scripts/publish-desktop.ps1 -OutputPath artifacts/desktop/win-x64-m1g
```

The complete portable folder is required. Only application/runtime/public
definitions, documentation and notices are packaged; private ROMs, signatures,
plans, reports, hashes and traces are excluded. The public key is verification
code, not a private input identity or signing credential.

This stage does not complete M1/M3, establish physical RPM or ECU behavior, select
a root license, install editors, change other firmware families or authorize
flashing. Scoped checksum preservation is a PC research property, not a claim
that a calibration is safe for a vehicle.
