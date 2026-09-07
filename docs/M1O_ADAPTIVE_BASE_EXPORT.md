# M1o — Adaptive-bank base-pair checksum-preserving export

Base: `11a0e0294126682a4b8c1d831fffe00ad4ae07a3`, explicitly fetched from
`origin/codex/p28-fixed-limiter-export-m1n`. Delivery branch:
`codex/p28-adaptive-base-export-m1o`. M1m and M1n remain completed.

## Scope and independent contracts

The new workflow edits exactly two unsigned little-endian **program** words of
one explicitly selected bank. It is not a generic calibration or offset editor.

| Selector DATA021F.1 | Export field | Writable bytes |
| --- | --- | --- |
| clear / bank 0 | adaptive-bank-0-base-cut | 649B, 649C |
| clear / bank 0 | adaptive-bank-0-base-resume | 6495, 6496 |
| set / bank 1 | adaptive-bank-1-base-cut | 64A7, 64A8 |
| set / bank 1 | adaptive-bank-1-base-resume | 64A1, 64A2 |

These are four disjoint bytes, not the intervening writable range. In particular
coefficient word 64A9/64AA is not part of baseCut. Odd program-word addresses are
not rounded to data-space alignment. The inspector owns the single mapping used
by inspection, description, encoding, admission and full-diff verification.
Established read-only inspector field IDs remain compatible; the new export
uses the explicit adaptive-bank-N-base-cut/resume IDs above.

Only `original -> adaptive-base child` is admitted. Fixed/VTEC/adaptive children
cannot become new originals, and there is no combined or chained editing.
The closed version-1 purpose and `p28-single-adaptive-bank-base-pair-v1` contract
are separate from M1g/M1n formats. JSON cannot choose offsets, widths, mapping,
signature authority or a different compensation location.

Origins, coefficients, every word of the other bank, fixed-context immediates,
selector flags, decrease/increase/timer constants, VTEC, vectors, machine code,
branch targets and checksum code/gate remain unchanged. Only the already admitted
compensation byte may additionally change.

## Bases versus stateful thresholds

M1m's firmware model is unchanged. Reset stores the selected base words. Hold
reads them but leaves previous RAM words untouched. The decreasing helper floors
its previous-minus-37 result at base. The adaptive helper uses origin, raw00CE,
MUL high word and the previous-plus-24 bound, with the established modulo target
addition. The limiter consumes the resulting current RAM01A4/01A6, not always
literal table bases. Changing banks never normalizes or reseeds previous words.

The exporter requires explicit integer final values for both words (including
the unchanged one for a single-field edit):

`0 < baseCutRaw < baseResumeRaw < 65535`.

For each immutable origin/coefficient triple it enumerates all 65,536 raw00CE
values and calculates in wide integers:

`target(x) = base + floor(max(0, x-origin) * coefficient / 65536)`.

It rejects target overflow above 65535 or any cut target >= resume target.
The plan records domain, count, maxima and minimum target gap, independently
recomputed on reproduction/readback. This is an exporter arithmetic policy,
not factory bounds, an engine-safety guarantee or proof of all RAM histories.
Research equal/reversed/wrap models remain valid and unchanged. No force, clamp,
swap, rounding, RPM conversion or bank synchronization is offered.

## Edit audit and compensation applicability

The new private source review checks actual program-data readers, overlapping
words/bytes, numeric value flow, downstream RAM consumers and possible use as
pointers, lengths, stopping keys or destinations. It uses the earlier full
program-reader census and source closure, not merely a successful producer test.
Actual listing-byte checks and detailed source-audit results stay private.

Within the original ordinary initialized-state/source-listed software scope,
these bases are numeric reset values, floors and targets. The new edit argument
preserves pointer-origin literals, table strides, scanner stopping keys, axis
bounds, encoded control destinations and intact-stack/register-bank restrictions
used by the existing compensation audit. Its signed location verifier, exact
original/profile/binding admission and enabled-checksum requirements are reused
unchanged. No offset, key, issuer, review signature or certification system is
created. Bounded native non-reading of compensation is supplementary evidence.
This is not a global arbitrary-state, DD-flow, external-code, IRQ or full-boot proof.

## Plan and A/B/C validation

A is immutable original; B changes only the selected base pair in memory; C
adds the reviewed compensation. M1f full-byte arithmetic and M1g's pure formula
are reused: `newCompensation = (oldCompensation - residueB) mod 256`.
Word numerical deltas are not substituted for actual byte sums. A/C must have
zero residue. A nontrivial zero-residue B leaves compensation unchanged.
Actual diffs contain only changed bytes, at most five; no fixed diff count is
assumed. No-op preview is valid, but apply refuses to publish another BIN.

The plan binds original size/hash, profile/binding digests, bank, both field IDs,
old/new words and encoded bytes, immutable triple context, domain results,
location identity/scope, compensation, A/B/C residues/hashes and exact diff.
Every field is reproduced from original and code-owned admission, never trusted
just because the serialized plan claims it.

Mandatory corpus `single-bank-base-producer-limiter-abc-v1` is generated from the
plan; an external scenario cannot replace it. It includes:

- Both reset paths and priority despite a live timer, hold and native expiry.
- Decrease borrow/floor/equality/neighbors, previous-word boundaries and retention.
- Origin and MUL high-word transitions, previous-plus-24 bound and target decrease.
- Old/new base crossings after native reset and old/new target crossings after
  native adaptive updates, both prior states and independent inhibit clear/set.
- Both banks, edited-to-other bank histories, fixed-P4/fixed-011B and RAM selection.

Each image/scratch pattern has independent native CPU/RAM and C# model history.
The model reads its own image's tables. Only actual native stores hand producer
words to the native limiter; no threshold injection or state alignment occurs
after deliberate divergence. M1m compares LC addresses/loaded words, selected
bank, branches, before/after RAM, counters/native ticks, ordered stores,
limiter operands/request/consumer, exits, stack and critical section. No ADD/SUBB
permission is widened and no executor/runner change is introduced.

B/C full observation digests and modeled/verified outcomes must agree. A/B/C
must also agree in a never-edited-bank control with identical initial state.
After edited-bank history, other-bank RAM may legitimately differ until later
state-machine behavior converges. Fixed-only controls require identical fixed
selected threshold and limiter/request/consumer, **not identical adaptive RAM
or incidental producer registers**. This distinction is enforced in code.

Every admissible non-no-op batch must contain a representative verified witness:
new ROM base word actually read -> different produced RAM -> changed limiter
decision. Actual witness rows remain private. This is targeted execution coverage,
not a full raw/state cross-product; finite domain checks are reported separately.

Fresh M1f A/B/C checksum execution uses all 512 invocations and ordered complete
coverage for all three scratch patterns. A/C require ordinary zero pass, B its
actual expected residue/path. Conditional/unresolved, mismatch, missing runner,
incomplete coverage, budget/execution failure or cancellation cannot mint a token.

## Publication and independent readback

The internal non-deserializable capability snapshots plan and evidence, including
nested word/read/history collections. Receipt JSON cannot mint a capability.
The bounded process adapter, shared checksum parser/accounting, snapshot rechecks,
ResearchOutputGroup staging/new-path writer and rollback are reused. Fixed/VTEC
admission rules stay unchanged. The common closed JSON shape checker additionally
validates ushort history members with strict 0..65535 bounds.

BIN, saved plan and receipt must be three distinct new paths, separate from all
inputs. Cancellation is checked before publication; after publication starts,
rollback/readback finishes. Group atomicity on power loss is not promised.
Readback reloads all three files, compares bytes and exact identities, encoded
bank pair, unchanged fields, full diff, sum8 and recorded execution consistency.
Restoring old diff bytes in memory must recover the entire original byte-for-byte.
A readback failure is not success and retains diagnostic artifacts.

Verify/inspect independently regenerate mandatory histories and descriptive
outcomes. Receipt is historical consistency evidence, not authentication that
past execution happened or fresh execution. A new apply always runs again.

## CLI

Explicit private example; raw values are PC tests, not RPM recommendations:

```text
hondaecu research p28-limiter adaptive-export plan <original.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --compensation-definition <reviewed-location.json> --bank 0 --base-cut-raw 257 --base-resume-raw 261 --output <new-plan.json>
hondaecu research p28-limiter adaptive-export apply <original.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --compensation-definition <reviewed-location.json> --plan <new-plan.json> --runner <runner> --confirm-pc-only --output <new-child.bin> --saved-plan <new-saved-plan.json> --report <new-receipt.json>
hondaecu research p28-limiter adaptive-export verify <child.bin> --baseline <original.bin> --profile p28-304 --baseline-binding <binding.json> --compensation-definition <reviewed-location.json> --plan <saved-plan.json> --report <receipt.json> --output <new-verification.json>
hondaecu research p28-limiter adaptive-export inspect <child.bin> --baseline <original.bin> --profile p28-304 --baseline-binding <binding.json> --compensation-definition <reviewed-location.json> --plan <saved-plan.json> --report <receipt.json> --output <new-inspection.json>
```

Existing fixed-context `export` retains its previous meaning. These commands
run end-to-end without opening a GUI. Preview writes no firmware/native claim;
verify/inspect report fresh execution NotRun, not a synthetic replacement pass.

## Local verification record

Private in-memory cut-only, resume-only and paired variants for each bank passed
their mandatory native batches. Per bank, the respective strict producer/limiter/
consumer call counts are 9,270, 10,386 and 10,818, each with nine complete native
checksum sequences. B/C agree throughout; unchanged-bank and fixed-consumer
controls pass. Repeated development runs are not added to these coverage counts.

The actual CLI apply freshly repeated the paired batch and published exactly one
new private 32 KiB PC-only BIN. Independent readback, separate CLI verify and
derived inspection passed. The reset witness follows actual LC -> native RAM
stores -> changed limiter decision, not injected thresholds. Exact bytes, hashes,
witness rows and source-audit results remain in private reports, not this document.
No-op preview had no differences; apply refused without another BIN.

Eighteen additional actual negative checks passed, including forged/stale plans
and receipts, changed historical outcomes, missing checksum rows, zero-sum extra
diff, opcode changes, mixed child parents and missing runner. A freshly validated
capability passed nested alias isolation, cancellation and publication rollback
without another firmware image. The common writer's synthetic tests also retain
explicit readback failure checks. All 4,133 inventory materials and the prior M1n
BIN (rehashed against its preserved verification identity) remain unchanged;
old portable folders are not republished.

Local regressions: 587 Core, 229 CLI, 81 Desktop headless and 121 Rust tests passed.
Both explicit Release solutions build with zero warnings/errors; .NET formatting,
pinned Rust 1.85.1 build/test/format, privacy guard and diff checks are delivery gates.
CI status is reported separately against the delivered commit.

## Delivery limits

Public fixtures contain only invented data and programs. A real synthetic Rust
subprocess demonstrates odd-address LC and persistent native RAM stores while
intentionally failing the recovered model; it cannot masquerade as OEM proof.
Old limiter/adaptive/fixed/VTEC refusal regressions and shared writer failure
tests remain required. Actual private outcomes, traces, plans, receipts,
identities and source-audit details are excluded from Git/CI artifacts.

`physicalRpmAvailable=false`; `PcInspectionOnly / NotFlashReady`.
GUI r3 paused/NotRun; hardware/full boot NotRun, excluded from stage completion.
No GUI/Computer Use, coefficients/origins editing, combined edits, physical clock,
acquisition/IRQ/full-ECU integration, checksum bypass, signing infrastructure,
editor installation, hardware flashing or other repository is in scope.
Old portable folders are not replaced. Clean CI artifacts are not GUI acceptance.
Stop after this stage; do not automatically start the next one.
