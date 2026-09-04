# M1c - Targeted ADD investigation and PC-only raw threshold editing

Date: 2026-09-05. Actual base: `origin/codex/p28-rpm-codec-vtec-inspector-m1b`,
`e5057ddbc0925fee2679f5bab544b939252f8173`. Working branch:
`codex/p28-raw-threshold-editor-m1c`.

This stage adds one-slot raw-byte research planning, application to a new private
file, independent full-file verification, and lineage-gated derived inspection.
It does not establish physical RPM, factory provenance, checksum validity or
ECU behavior, complete M1, or make public profile parameters writable.

## Targeted ADD result

Classification: **tool-documented hypothesis; required live semantics unresolved**.
`P28CompactModel.ModelId` remains `p28-compact-v1`; `Evaluate` and
`EvaluateHypothesis` are unchanged. Inputs 234..3749 remain explicitly unresolved
in the established API. No new arithmetic implementation was used to manufacture
instruction evidence.

The unchanged private baseline actually contains `47 81` at `0x07F8`. The preceding
word load, DIV, SRL and two-byte bit-copy boundary chain reaches exactly `0x07F8`;
the next decoded byte load starts at `0x07FA`. DD is 1 at the questioned operation.
The enclosing routine sets actual `LRB=0x0040` and `USP=0x0180`. Register-manual
figures establish local-register base `0x0200`, with er3 in r6/r7 at DATA
`0x0206/0x0207`; the direct-page base is also `0x0200`. The disassembler's display
field is not itself the LRB register value.

In [pinned asm662](https://github.com/VIRUXE/asm662/tree/94612d10370eb4ddf97d4f349168298e1a3da8a0),
`src/66207.op` RCS head 1.9 maps `ADD erN,A` to `44+N,81`. The older generated
`op.c` 1.15 used for the existing executable maps the same two bytes to the same
form and length. Reconstructing the preceding opcode-description revision 1.8
found only an unrelated mnemonic rename; this ADD interpretation did not change.
Neither table implements hardware arithmetic or provides an independent experiment.

The exact attachments in the [66kAssemblerDocs catalog](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/bin/view/Library/66kAssemblerDocs.html)
were fetched and their real contents examined, not inferred from their names:

| Attachment | Actual result | Evidence limit |
|---|---|---|
| `Oki_66201_Instruction_Manual.pdf` | HTTP 200; 4563117 bytes; same 266-page PDF as M1a | MSM66201 first edition, September 1991; no new exact-form evidence |
| `66207Chapter3.zip` | HTTP 200; 7140470 bytes; 211 TIFF pages and one directory | Heading is *Details of Instructions*, but body names MSM66201; chapter-only scan has no edition imprint |
| `66207usersmanual_incomplete.zip` | HTTP 200; 16203609 bytes; 66 JPG scans | Body names MSM66201/207; missing title/edition and gaps in printed pages |

ZIP magic, member inventory, normalized extraction targets, size bounds and
symlink/duplicate/path-escape rejection were checked before local extraction.
No downloaded program was executed and no previous material was overwritten.
Sources, scans and inventories remain private.

Chapter3's actual printed ADD pages 3-13..3-17 and summary Tables 3-14/3-15
(3-192/193) omit the needed word `obj,A` form, as does the existing PDF. The byte
analogue and numbering gap do not fill that omission. The incomplete user manual
adds useful register evidence (printed 30..39), not the missing opcode form.
Its Figure 3-5 identifies PSWL.4 as user flag **F0**, distinct from HC/CF/ZF.
No nX-8/500S binary-compatibility assumption or physical experiment was used.

| ADD property | Required for the selected Code/ExtraBit contract? | Status |
|---|---|---|
| Encoding and two-byte length | Yes | Actual bytes match both related tool descriptions; exact-form primary confirmation absent |
| er3 destination, A source; unsigned 16-bit modular addition without carry-in | Yes | Tool-described hypothesis, not newly established |
| Word wrap rather than saturation | Yes | Required by the hypothesis's bounded operands, still not independent instruction evidence |
| Result in er3/r6/r7 | Yes | Consumed by subsequent clamp/floor/code logic |
| Post-ADD A | No | Next byte load replaces AL; retained AH is not read before the final byte store |
| Post-ADD CF/ZF/HC/DD | No | Relevant flags are overwritten before use; HC is not read; explicit LB establishes DD=0 |
| Saved F0 and addressing context preservation | Yes | F0 supplies ExtraBit unless a clamp overrides it; unknown instruction effects cannot be assumed proven |
| Timing | No, for this coherent snapshot contract | Unmeasured; not used as a reason to block arithmetic promotion |

The missing evidence is the **live data effect**, not an unused flag or cycle
count. The bounded search ends here; raw editing below does not require promoting F.

## Raw bytes, compact codes, and RPM are different layers

A raw threshold is one stored unsigned byte. The examined enabled path compares
an unsigned compact code from DATA `0x0133` with the selected threshold:
`newState = compactCode > selectedThreshold`; equality produces false.
This does not measure RPM or physical solenoid activation. Later state gates,
timers and software/physical outputs remain separate.

The eight neutral slot IDs and their mapping are centralized in
`P28ThresholdLogic`; CLI code accepts IDs, never arbitrary offsets. See the
[M1b mapping and raw-input domains](M1B_RPM_CODEC_AND_VTEC_INSPECTOR.md).
Raw-input domains from F are a separate layer: unresolved intervals remain
unresolved after a perfectly measured byte change.

Each plan compares the old and new predicates for **all 256 compact codes**.
It includes the full truth table, changed-code set, selected prior state, all
eight slot-selection checks, and the prior-clear/prior-set pair values before
and after. The other seven selections have unchanged one-step results for the
same incoming state. Future multistep trajectories are not required to remain
identical after an intentional change.

Pair orientation is reported literally as equal, prior-clear greater than
prior-set, or prior-clear less than prior-set. Equal/reversed pairs are neither
silently normalized nor certified engine-safe.

## Commands and one-step lineage

Examples use private paths and an illustrative raw byte, **not an RPM setting**:

```shell
hondaecu research p28-vtec plan private/oracle/p28-304/base.bin --profile p28-304 --confirm-profile --baseline-binding private/reports/m1b/baseline-binding.json --slot context_0.pair_0.state_0_threshold --raw-value 128 --output private/reports/m1c/plan.json
hondaecu research p28-vtec apply private/oracle/p28-304/base.bin --plan private/reports/m1c/plan.json --baseline-binding private/reports/m1b/baseline-binding.json --confirm-pc-only --output private/roms/p28-304/m1c-pc-only.bin --report private/reports/m1c/patch-report.json
hondaecu research p28-vtec verify private/roms/p28-304/m1c-pc-only.bin --baseline private/oracle/p28-304/base.bin --baseline-binding private/reports/m1b/baseline-binding.json --plan private/reports/m1c/plan.json --report private/reports/m1c/patch-report.json --output private/reports/m1c/verification.json
hondaecu research p28-vtec inspect private/roms/p28-304/m1c-pc-only.bin --profile p28-304 --confirm-profile --baseline-binding private/reports/m1b/baseline-binding.json --baseline private/oracle/p28-304/base.bin --plan private/reports/m1c/plan.json --patch-report private/reports/m1c/patch-report.json --output private/reports/m1c/derived-inspection.json
```

`plan` changes no ROM. It requires explicit acknowledgement, matching original
research binding, correct size/profile digest and supported model. Exactly one
slot and decimal integer 0..255 are accepted: no signs, fractional values, RPM,
rounding, inverse choice, arbitrary offset, extra slots or mirrored changes.
No-op requests are explicit plans with an empty changed-offset set.

Plan format 1.0 records parent hash, size, canonical profile/binding digests,
model ID, slot/context/prior-state/offset, old/new byte, expected offsets, impact,
evidence limits, checksum Unknown and PC-only safety. Digests use deterministic
compact JSON of parsed objects, not raw JSON-file whitespace. Plans/reports are
integrity-linked research artifacts, **not signed authorization or factory
authentication**. No identity is added to the public profile.

`apply` requires the separate `--confirm-pc-only` acknowledgement, selects the
profile from the validated plan, reproduces the complete plan from the original parent and rejects stale
or altered metadata. It uses immutable ROM snapshots and the existing two-file
staging/publication helper, with revalidation immediately before writing. Input,
profile, binding and plan paths cannot be destinations; existing output/report
paths are refused. The pair publication has best-effort rollback, not a promised
cross-file filesystem transaction under power loss.

`verify` reloads the original parent and derived file, checks the binding, rebuilds
the plan, measures the entire 32768-byte diff and recomputes the report. It checks
old/new byte, mapping, parent/output hashes, unchanged size and every unplanned
byte. Restoring the recorded old byte **in memory** must reproduce the complete
baseline. Plan/report readers reject missing, unknown, duplicate, null, malformed
and unsupported fields; false/zero values do not excuse a missing property.

Derived `inspect` requires all of parent, plan and patch report together. It
shows derived contexts only after successful verification. The ordinary output
inspection retains the **original** binding and therefore reports Mismatched for
a changed file; it does not pretend that the baseline hash matches the output.
No new derived baseline binding or general patch chain is created. Without
lineage, the original raw-only unknown-file behavior remains available.

## Checksum and validation limits

Checksum status is always **Unknown** in this research workflow. No checksum
location or algorithm is guessed, no checksum repair is attempted, and no bypass
is applied. A derived file may fail the ECU's native integrity check. Every plan,
patch, verification and derived inspection remains **PcInspectionOnly /
NotFlashReady**, including a no-op or successful reverse restoration.

Public tests use synthetic thresholds, not OEM bytes or a private ROM-derived
corpus. Actual baseline/file checks, conditional model agreement, instruction
evidence, original BIN execution, editor checks and hardware checks are different
categories; none automatically promotes another. No Crome/HTS installation,
full emulator, GUI, Oracle v2 promotion or license declaration was added.

## Actual validation results

| Category | Actual result | Does not prove |
|---|---|---|
| Public synthetic algorithm/file tests | 211 passed: 185 Core, 26 CLI; zero failed/skipped | OEM firmware execution or engine safety |
| Real private file workflow | Bound inspection, repeatable plan, one-byte apply, verify, derived readback passed | Checksum validity or physical VTEC operation |
| Full-file difference | Exactly one byte in the selected slot; all other 32767 bytes unchanged; size 32768 | Engineering meaning of the requested byte |
| One-step predicate impact | All 256 codes checked; one code changed result; other seven slot selections unchanged | Identical future state trajectories |
| Reverse restoration | Old byte restored in memory reproduces the entire baseline | Permission to overwrite or flash the original |
| Conditional reference rerun | 131072 agreements, zero mismatches; 124040 established-path matches; 7032 unresolved **not passed** | Independent OKI instruction validation |
| Targeted instruction evidence | Actual bytes/boundary and related decoder versions agree; new register-manual evidence; live ADD semantics still unresolved | A complete raw/RPM codec |
| Original BIN execution / editor / hardware | **Not run / not run / not run** | No outcome in these categories is inferred |

For the real example, the low bit of one stored threshold was toggled, changing
its raw value by one. This was chosen solely to test a minimal one-byte PC file
change, not to raise/lower RPM or recommend an engine calibration. The old/new
values, input/output hashes and complete plans/reports stay private. The original
baseline, M1a working copy, public profile and M1b binding retained their initial
hashes. Repeated plans were byte-identical; direct inspection of the modified file
with only the original binding returned the expected mismatch/raw-only refusal.

Local restore, Release build (zero warnings/errors), tests, format verification,
privacy guard and whitespace checks passed. The
existing Windows/Linux CI runs only the public synthetic tests, never the private
ROM, translated reference, source snapshots or actual patch reports.

## Next evidence gate

RPM editing still needs both the missing live word-ADD semantics and the producer's
physical timer/clock/prescaler/capture/pulses-per-revolution scaling, followed by an
explicit many-to-one inverse selection policy. Exact file editing and compact-code
predicate comparison do not resolve those dependencies or authorize an ECU write.
