# M1p — Combined limiter-group checksum-preserving export

Base: `be2de5f29e1e39314f727116e95efe2765eb773e`, explicitly fetched from
`origin/codex/p28-adaptive-base-export-m1o`. Delivery branch:
`codex/p28-combined-limiter-export-m1p`. M1m/M1n/M1o remain completed.

## One original, three explicit groups

The new closed contract `p28-combined-limiter-groups-v1` composes numeric fields
from the inspector's existing code-owned mapping. It is separate from the
unchanged M1n fixed-only, M1o single-bank and M1g VTEC formats/admission.

| Group | Cut word bytes | Resume word bytes |
| --- | --- | --- |
| fixed | 196A/196B | 1967/1968 |
| bank0 | 649B/649C | 6495/6496 |
| bank1 | 64A7/64A8 | 64A1/64A2 |

Words are unsigned little-endian; odd program addresses are never aligned down.
The maximum is twelve disjoint numeric bytes plus the already reviewed single
compensation byte, not contiguous writable ranges. Opcode 1969, origins,
coefficients (including 64A9/64AA), other table words, selector flags, VTEC,
timer/increase/decrease constants, vectors, encoded destinations, checksum code
and gate are protected by exact original-parent reproduction and full byte diff.

All seven nonempty selections are supported: fixed; bank0; bank1; fixed+bank0;
fixed+bank1; bank0+bank1; all three. Every group is explicitly a complete final
pair or `null` (unchanged). Requested values equal to original remain an explicit
requested group no-op. Whole-request no-op preview is allowed, but publication
is refused. No bank synchronization, automatic pair copying, offset/width request,
clamp, swap, rounding, force, or physical RPM conversion is available.

Only `original -> combined child` is admitted. All requested words are encoded
into one memory copy B of original A. Existing full-image sum8 is calculated
from B's actual bytes, followed by exactly one compensation:

`newCompensation = (originalCompensation - residueB) mod 256`.

C's entire sum is independently recalculated; A/C require zero residue. B may
have zero or nonzero residue. Cross-group byte-sum cancellation can leave the
compensation unchanged despite meaningful numeric edits. Word deltas and old
receipt compensation values are never summed. No sequential apply to children,
merged BINs, child binding, mixed old-type lineage or patch chain is supported.

## Reused policy and admission

Every requested pair reuses `0 < cutRaw < resumeRaw < 65535`. Each requested
adaptive bank also reuses M1o's independent wide-integer enumeration of all
65,536 raw00CE values using its unchanged original origins/coefficients:

`target(x) = base + floor(max(0,x-origin) * coefficient / 65536)`.

No target may overflow 65535 and cut target must remain below resume target.
Recorded maxima/minimum gap/count are reproduced, not trusted. These are exporter
arithmetic policies, not factory bounds, an engine-safety claim or proof of all
persistent RAM histories. The firmware research model retains its real modulo
target addition. No invented ordering rule relates fixed thresholds to bases.

The simultaneous edit audit joins the M1n numeric comparison argument and M1o
numeric reset/floor/target argument. Fixed DP/A values are consumed numerically,
or replaced by RAM selection, then overwritten before later program-pointer use.
Adaptive LC +2 values flow through numeric arithmetic and RAM threshold stores;
literal X1/X2 pointers and +0/+4 origin/coefficient reads remain unchanged.
Context switches change which threshold/history is consumed; they do not turn
these numeric values into program pointers. Byte disjointness alone is **not**
a behavioral independence proof.

The existing whole-reader/caller review remains applicable simultaneously:
pointer literals, table strides, scanner stopping keys, software index bounds,
instruction widths, vectors, encoded destinations and intact-stack/register-bank
conditions are unchanged. Both branch/mode outcomes already belong to the
original conservative source-listed review. The private listing was rechecked
against actual original bytes; detailed value-flow/caller notes stay private.

The existing signed VerifiedCompensationLocation payload, pinned verifier and
exact original/profile/binding checks are reused unchanged. No new key, issuer,
signature, location or certification system is created. The scope remains
ordinary initialized/intact RAM and stacks on reviewed source-listed software
paths, not arbitrary PC/corruption, global DD-flow, external code, IRQ or full boot.
The tail byte is reviewed compensation, not factory storage or globally unused.
Bounded native non-reading is supplementary, never the whole audit.

## Deterministic plan and native validation

The closed version-1 plan records original size/hash, profile/binding digests,
fixed/bank0/bank1 in that order, requested/effectively-changed flags, both old/new
words and encoded bytes (cut then resume), both banks' immutable context, requested
domain results, location identity/scope/digest, edit scope, one compensation,
A/B/C hashes/residues, exact changed-byte diff and PC-only readiness. Unrequested
groups explicitly retain old values. Unknown, duplicate, missing, stale or
contradictory fields and bank-ID substitutions are refused. Semantically equal
settings property orders yield the same plan. Apply reproduces every field and
byte from the exact original and current code-owned admission.

Every apply regenerates mandatory corpus `combined-limiter-groups-native-histories-v1`:

- M1l fixed task: P4-only, 011B-only and both inputs, both prior request states,
  independent inhibit clear/set, old/new equality/neighbors, consecutive repeats,
  descending and ascending crossings.
- M1m producer -> native RAM -> limiter -> consumer: both banks' existing M1o
  generators cover reset priority, live-timer reset, hold/expiry, native counter
  updates, decrease/floor/borrow, adaptive bound, raw00CE endpoints/origin and
  multiplication high-word boundaries. Fixed and RAM source controls are included.
- New fixed -> bank0 -> bank1 -> fixed and reverse-bank-order histories retain
  thresholds, request, counters and persistent masks. Only the first producer
  operation resets; later holds/expiry/decrease evolve native state without reseeding.
- Every effectively changed group requires a source-isolated witness in the
  actual combined images: observed operand/base read -> changed selected threshold
  or native threshold production -> changed limiter request. No separate child
  image or one-group execution substitutes for the combined batch.

Each A/B/C image and scratch pattern has its own CPU/RAM and independent C# model
reading that image's bytes. Only actual native stores feed native RAM thresholds;
modeled values are never injected. M1l/M1m validate complete traces, branches,
operands, ordered stores, counters, stack, critical section, history and stops.
All fixed immediate bytes must appear in actual fetch coverage. No runner/ISA
permission, ADD/SUBB assumption or firmware model is changed.

B/C full non-checksum observation digests and histories must agree. A/C controls
compare dependencies, not blindly every temporary register: never-edited-bank
RAM-only histories must agree from a clean identical initial state, even if
incidental fixed immediate loads differ. Unedited fixed consumers must agree
even if adaptive producer RAM differs. After edited contexts, retained histories
may legitimately diverge across a bank switch; they are never normalized.
Reused subcorpus IDs retain their original generator-relative `edited/untouched`
labels inside a `basesN/` namespace; combined group flags and actual scenario
inputs, **not those labels**, determine whether a bank is truly unchanged.

M1f executes all 512 invocations per image/scratch, ordered full-ROM coverage and
every intermediate checksum state. A/C take the ordinary zero path; B follows
its actual zero/nonzero path. Conditional/unresolved, incomplete, mismatch,
execution/budget error, missing runner, cancellation or changed inputs cannot
create an export capability. Consumer stops before 5596/P2; request/mask behavior
does not establish physical injector shutdown, timing or RPM.

## Capability, publication and readback

The internal non-deserializable capability binds reproduced A/B/C, plan and fresh
evidence. Nested groups/bytes/read/history collections are defensively copied.
JSON cannot mint a capability. Narrow shared helpers reuse existing fixed/adaptive
process parsing, corpus construction, independent receipt history checks, bounded
process adapter, checksum parser, CLI input snapshots and ResearchOutputGroup;
old exporter admission and serialized contracts are unchanged.

BIN, saved plan and receipt require three distinct new paths, protected from input
aliases and overwrites. Snapshots are rechecked after async execution and before
publication. The shared staging writer honors cancellation before publication,
then finishes readback or best-effort rollback. No multi-file power-loss atomicity
is promised. A readback failure throws and retains diagnostic files, not success.

Independent readback reloads all three files, checks exact live plan/receipt,
original-parent identities, group encodings, every output byte/full diff and sum8.
Restoring old diff bytes must recover the entire original byte-for-byte. Separate
verify/inspect repeats tuple reproduction and independently rederives descriptive
receipt histories. Receipt is historical **consistency**, not authentication that
execution happened, fresh execution, or a reusable capability. Verify/inspect
explicitly report fresh execution NotRun. Compact receipts are bounded to 64 MiB;
an oversized receipt is refused before publication.

## CLI

Settings file example: explicit raw PC research inputs, **not RPM recommendations**.

```json
{"formatVersion":1,"purpose":"explicit-limiter-group-selection","fixed":{"cutRaw":540,"resumeRaw":556},"bank0":{"baseCutRaw":257,"baseResumeRaw":261},"bank1":{"baseCutRaw":261,"baseResumeRaw":265}}
```

Replace any complete group object with `null` to leave it unchanged; never omit
its name or a member of a requested pair.

```text
hondaecu research p28-limiter combined-export plan <original.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --compensation-definition <reviewed-location.json> --settings <settings.json> --output <new-plan.json>
hondaecu research p28-limiter combined-export apply <original.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --compensation-definition <reviewed-location.json> --plan <new-plan.json> --runner <runner> --confirm-pc-only --output <new-child.bin> --saved-plan <new-saved-plan.json> --report <new-receipt.json>
hondaecu research p28-limiter combined-export verify <child.bin> --baseline <original.bin> --profile p28-304 --baseline-binding <binding.json> --compensation-definition <reviewed-location.json> --plan <saved-plan.json> --report <receipt.json> --output <new-verification.json>
hondaecu research p28-limiter combined-export inspect <child.bin> --baseline <original.bin> --profile p28-304 --baseline-binding <binding.json> --compensation-definition <reviewed-location.json> --plan <saved-plan.json> --report <receipt.json> --output <new-inspection.json>
```

Output title is “Combined limiter research edit”, with separate group selection,
effect, old/new fields, arithmetic domains, one compensation and exact diff.
Planning does not write firmware or claim native execution. No GUI is involved.

## Actual verification record

All seven private original-parent combinations were previewed in memory. The
three single-group results matched actual M1n/M1o workflow firmware bytes exactly.
Additional mandatory in-memory runs passed without publishing firmware:

| Selection | Logical adaptive calls | Strict adaptive image/scratch calls | Strict fixed calls |
| --- | ---: | ---: | ---: |
| fixed | 2560 | 23040 | 5184 |
| fixed + bank0 | 2818 | 25362 | 5184 |
| bank0 + bank1 | 2950 | 26550 | 2592 |

Each batch also has nine strict 512-invocation checksum sequences. Fixed logical
calls are 576 when fixed is changed, 288 when unchanged. Multiplication by nine
accounts for three images and three scratch patterns, not distinct logical inputs.

The actual all-three CLI apply freshly executed **3238 logical adaptive calls**
across 182 scenarios, giving **29142 strict image/scratch calls**, plus **576
logical fixed calls** across 12 scenarios, giving **5184 strict calls**. All nine
complete checksum sequences passed their own actual-byte expectations. B/C agree,
source-dependent controls pass and all three changed groups have verified witnesses.
The two requested bank domain checks each enumerate 65536 raw inputs; these
arithmetic evaluations are separate from native call counts.

Exactly one new private 32 KiB combined PC-only BIN was published. All three groups
changed, the actual diff has nine bytes, and arithmetic/native residues A/B/C are
0/34/0. One tail compensation is computed from the combined B bytes. Independent
readback, separate CLI verify and inspect passed. The receipt is about 29 MiB,
within its bound. Exact identities, trace rows and private artifacts remain ignored.

Each witness observes a changed threshold/request in a source-isolated combined
control; native base reads and stores connect the adaptive witnesses. Switch
controls preserve earlier produced RAM during timer holds even when the newly
selected bank's bases differ. This explains retained divergence without reseeding.
Independent inhibit remains a separate cause of consumer mask-update suppression.

Thirty-two additional actual refusal checks passed: forged/stale group/identity
metadata, changed historical outcomes, missing fixed/adaptive/checksum/witness
rows, extra zero-sum changes, protected opcodes/origins/coefficients/gate, mixed
child parents, no-op, missing runner, cancellation and publication rollback.
A fresh capability batch additionally checked nested alias isolation and failed
publication without another BIN. Repeated development/failure-check runs are not
added to the per-apply coverage totals above.

Public tests use invented data/programs only: all selections, no-op subsets, exact
thirteen-byte maximum, carry/cross-group cancellation, full-domain policies,
deterministic settings, malformed metadata, old-format refusal, independent
control/witness coverage, defensive copies and real Rust subprocess mismatch
refusal/native handoff. Existing shared writer tests retain cancellation, alias,
rollback and readback-failure coverage. Synthetic execution is not OEM proof.

Both explicit Release solutions build with zero warnings/errors. Local regressions
passed: 619 Core, 257 CLI, 81 Desktop headless and 121 Rust tests, without skips.
Pinned Rust 1.85.1 build/test/format, .NET formatting, privacy and whitespace checks
passed. Old M1n/M1o original-parent tuples also verify with their preserved receipts.
CI status is reported separately against the delivered commit.
All 4201 inventory materials, previous BINs, definitions, signatures and portable
folders remain unchanged. Clean CI portable artifacts are not GUI acceptance.

`physicalRpmAvailable=false`; `PcInspectionOnly / NotFlashReady`.
GUI r3 paused/NotRun; hardware/full boot NotRun and excluded from M1p completion.
No GUI/Computer Use, WPF changes, new calibration/coefficient/VTEC editing,
signing framework, editor installation, new firmware source, physical clocks,
acquisition/IRQ/full-ECU emulation or flashing. Stop after M1p; no automatic next stage.
