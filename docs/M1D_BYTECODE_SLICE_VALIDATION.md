# M1d - Byte-executed ROM slice validation

Base: `origin/codex/p28-raw-threshold-editor-m1c`,
`cc2c462147e5a116632e478c20db5f396d361a20`. Working branch:
`codex/p28-bytecode-slice-validation-m1d`.

This is `SeededRomSlice`: actual software decode/execute of unchanged input bytes
at their original program addresses. It is not a reset boot, full ECU emulator,
hardware experiment, engine start or physical VTEC-output validation. M1 remains
incomplete. Production PatchEngine, Oracle v2, public profile identity/writability
and the established/conditional compact model are not promoted by this work.

## Audited source and reproduced defect

The CPU stays in one Rust executable, based on
[hondaecu-cli at the pinned commit](https://github.com/VIRUXE/hondaecu-cli/tree/85b30752473ca9979e4ad9b307ea05a30c0b3d1e)
`85b30752473ca9979e4ad9b307ea05a30c0b3d1e`. Before import, its exact CPU,
decoder, full opcode table, operand parser, executor and bus files, LICENSE,
Cargo.toml and Cargo.lock were inspected. Upstream has no crate dependencies.
The local bus deliberately excludes upstream peripheral progression, engine
scenarios, telemetry and ROM-specific behavior. Upstream embedded tests were
excluded, including a firmware fixture. Only newly authored synthetic tests are
public. See [third-party notices](../THIRD_PARTY_NOTICES.md), including the older
opcode-table BSD attribution and exact JSON dependency license inventory.

The [OKI MSM66201 instruction manual](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/Oki_66201_Instruction_Manual.pdf)
was inspected visually at PDF page 175 (index 174), printed **3-122**. This is
word `ROR obj`, whose erN row is `44+N C7`: er3 is **47 C7**. Its diagram routes
old CF into bit 15 and bit 0 into CF. Only CF changes; ZF, HC, DD and user flags
remain intact. This is not an inference from a rotate helper or the C# model.

Before changing upstream ROR arithmetic, a locally compiled decoded-opcode test
failed (exit 101, one failed test). For operand `0000`, old CF=1, it produced
`0000` instead of `8000`, and also changed the non-carry PSW from `2EF9` to `6EF9`
by incorrectly setting ZF. The before-test harness used unchanged upstream
executor arithmetic and a minimal RAM bus; the source and compiler/test logs
are retained privately. No failing OEM fixture was used.

The minimal ROR arithmetic fix uses old carry instead of the operand's old bit 0
as the incoming high bit and omits ZF update for the checked word form. Regression
tests execute opcode bytes through the decoder/executor, check the three stated
examples and bank destinations, and compare every 16-bit operand with both old
carry states against the separate manual formula `(value >> 1) | (oldCF << 15)`.
Agreement validates this interpreter implementation, not actual silicon.

Three additional slice-needed defects were reproduced separately, not fitted to
the C# formula:

| Fix ID | Before / minimal correction | Visually checked manual form |
|---|---|---|
| `load-zero-flag-and-dd-contract` | Loading zero did not set ZF; L/LB now set it, retaining DD set/reset; LC sets ZF without changing DD | printed 3-69, 3-70, 3-72 |
| `word-srl-preserves-noncarry-flags` | SRL incorrectly cleared an existing ZF; only CF is now changed for the checked word shift | printed 3-150/151, PDF 203/204 |
| `bit-operands-use-byte-access` | MB at the last modeled RAM byte incorrectly read the next byte as a word; bit operands now access only their byte | printed 3-78, PDF 132; `MB obj.bit,C` explicitly says byte-long obj |

Pre-fix failing tests and post-fix results for these changes remain private.
New public tests additionally check CMP equality/borrow, MB flag preservation,
32-bit DIV quotient/remainder destinations, signed USP addressing, CPU aliases,
SCB switching, bank-zero accumulator aliasing and nontrivial high LRB bits.

### Complete local import adaptations

| Upstream file | Local adaptation |
|---|---|
| `cpu.rs` | Remove duplicate pointing-register fields/helpers; express full 13-bit LRB addressing; retain PSW behavior; source attribution |
| `decoder.rs` | Keep pattern/DD/cycle tables; reject unknown placeholder tokens; scope the source-description claim; remove embedded upstream tests |
| `full_decoder.rs` | Keep all 2623 patterns unchanged; remove three unused imports and misleading full-validation heading; source attribution |
| `operand.rs` | Keep operand-parser semantics; remove upstream tests; source attribution |
| `exec.rs` | Four fixes above; coherent byte/word alias access for operands/banks/stack; checked effective/branch/stack addresses and selected instruction extent; explicit memory faults; new synthetic tests; cycle-counter comments clarified as statistics only |
| `bus.rs` | Replace the board bus with only immutable code, private RAM, checked accesses, first-fault reporting and bounded LC address logging |

CPU/decoder/operand/executor files also have mechanical Rust formatting changes;
the large opcode table is not reformatted or regenerated. No upstream tests or
absolute machine paths were retained. The local JSON protocol, seeded contracts,
batch/comparison adapter and public synthetic probes are new HondaEcu code.

## Architecture and checked entry contracts

One versioned JSON request on stdin produces one JSON response on stdout;
stderr is diagnostics only. The C# process adapter uses no shell, passes arguments
with `ArgumentList`, bounds response/diagnostics, cancels/times out and kills the
child process tree. A nonzero process exit, invalid protocol and a measured test
mismatch are distinct failures. Exit zero alone never means the model matched.
The selected executable is analyst-controlled software, not an authenticated
hardware oracle; its self-reported version is not a cryptographic attestation.

| Contract | Compact | Threshold state update |
|---|---|---|
| Entry PC | `07C7` | `122C` |
| Successful stops, before instruction | `0822` | `126D` enabled; `1281` disabled |
| Allowed instruction bytes | `[07C7,0822)` | `[122C,126D)` |
| LRB / USP / incoming PSW | `0040` / `0180` / `1101` | `0020` / `0280` / `0101` |
| Inputs | DATA `00C4` unsigned LE word; `0217.4` | DATA `0133`, `011E.3/.4`, `0131.1/.2` |
| Outputs | DATA `0133`, `00B8.4` | DATA `0131.1/.2` |
| Helpers | None | None |

These boundaries were rechecked against the existing private listing and actual
input, not copied as an assumed call/return interface. `0820` begins the two-byte
store; stopping there would omit the output write. `126A` begins the three-byte
final bit copy. The later helper at `126F` and temperature/speed/timer/output
gates are outside this contract. A jump anywhere except an allowed instruction
range or one of the explicit before-exits is an error.

PSW writable flags and read-as-one bits follow the checked register specification.
SCB selects the pointing-register set in DATA `0080..00BF`; set 1 is `0088..008F`.
Local-register base uses the full 13-bit LRB shifted three bits, not only the low
bank bits. Off-page addressing clears LRB's low five bits before shifting. er3
in the compact contract is DATA `0206/0207` (r6/r7). A single coherent data API
handles SSP/LRB/PSW/ACC aliases and RAM-resident pointing/local registers; there
is no independent contradictory seed copy of the same register.

Only the modeled CPU aliases and RAM are admitted in data space; unmodeled SFR,
out-of-range and overflowing effective-address accesses stop explicitly. Code
fetch and LC program reads are separate from data RAM. No ROM masking, injected
threshold RAM, inserted RET/jump, reset vector run, interrupt, external event or
peripheral/time progression is used. Instruction budgets bound every case.
Scratch patterns 00/55/AA vary irrelevant initialized state while keeping real
preconditions fixed. Each input begins with fresh CPU/RAM, never the preceding
case's residual state. The threshold prefix also updates unrelated `0131.0`
using `00CC`; these do not replace or redefine the two checked output bits.

## Assumptions and batch accounting

`47 81 / ADD er3,A` remains **tool-documented hypothesis**. Strict execution stops
before that instruction as `UnresolvedInstruction`, never a pass. Conditional
execution requires precisely `oki.add-er3-a`; permission and actual reach are
recorded separately. Agreement after reaching it is `ConditionalMatch`, not
instruction-confirmed. That permission cannot bypass another unknown opcode,
unsupported instruction, memory error or exhausted budget.

C# compares observed compact outputs with unchanged `P28CompactModel.Evaluate`
on established paths, and only uses `EvaluateHypothesis` for actually reached,
explicitly permitted conditional execution. Batch results separately account for
completed matches without assumptions, unresolved instruction stops, conditional
matches, unresolved model results, mismatches, execution errors and budgets.
Counts are measured from execution, not forced to the previous 124040/7032 split.

The compact batch is all 65536 raw inputs under both S states and all three
scratch patterns (393216 cases). Threshold execution independently supplies each
compact code 0..255, both contexts, four prior-bit combinations, enabled/disabled
and three patterns (12288 cases per image). LC reads the supplied ROM's actual
bytes, with program addresses recorded and compared. Disabled cases must preserve
the two incoming bits and perform no threshold read.

Derived input is admitted only by the existing M1c original-parent binding and
complete plan/report verification. Baseline and derived outputs are compared
over the same one-step case set; the actual changed-result set must equal the
existing threshold predicate's expected changed set. Reading the changed program
byte is checked explicitly. No new derived-file baseline binding is created.

Packed result rows keep one process practical; full successful traces are not
retained. Bounded selected diagnostics and failure traces remain private. Public
tests use deliberately small invented instruction programs, not OEM-derived
disassembly or expected-value corpora. Changing an executed opcode or LC-read
constant must change an observed output/status in real Rust process tests;
separate mock subprocess tests cover transport only.

## Command

```shell
hondaecu research p28-vtec execute-check private/oracle/p28-304/base.bin --profile p28-304 --confirm-profile --baseline-binding private/reports/m1b/baseline-binding.json --runner rust/p28-slice-runner/target/release/p28-slice-runner --output private/reports/m1d/strict.json
```

On Windows use the `.exe` suffix. Add `--allow-assumption oki.add-er3-a` for
conditional mode. Add all of `--derived`, `--plan`, `--patch-report` to execute
the previously verified M1c child. Output must be a new private report path;
none of the inputs, profile or lineage files may be overwritten.

Reports contain protocol/runner/upstream identity, local fixes, input/profile/
binding/plan digests, entry contracts, allowed/used assumptions, separate result
categories and bounded diagnostics. Real hashes, thresholds, ROM bytes, local
paths and traces are not published in this document or public CI.

## Build and evidence limits

The toolchain is pinned to Rust **1.85.1**, with an actual resolved Cargo.lock;
this is a tested build choice, not a requirement copied from upstream README.
From the repository root:

```shell
cargo +1.85.1 build --release --locked --manifest-path rust/p28-slice-runner/Cargo.toml
cargo +1.85.1 test --release --locked --manifest-path rust/p28-slice-runner/Cargo.toml
dotnet test --configuration Release
```

The normal .NET integration suite requires the actual built Rust runner and fails
explicitly if absent. Windows/Linux CI builds it before .NET tests. Public CI
never loads the private corpus; a workspace without private materials must report
real-ROM execution as **not-run**, not silently pass or substitute synthetic data.

Actual local Release build with Rust 1.85.1 passed; **28 Rust tests** passed
(13 core tests, including the 131072-combination ROR loop, plus 15 runner tests).
Two Rust integration tests spawn the real executable. The full .NET Release
build had zero warnings/errors and **242 tests passed** (212 Core, 30 CLI), zero
skipped. Four .NET integration facts launch real Rust programs; separate mock
subprocess/batch tests check transport, complete accounting and refusal behavior,
not executor correctness. Full `dotnet format --verify-no-changes --no-restore`,
whitespace and private-artifact guards passed locally.

The two-OS public workflow runs the pinned Rust build/test and required real
synthetic end-to-end .NET tests after the unchanged forbidden-artifact guard.
No real-ROM output is inferred from CI. The actual push run is reported separately
at delivery so a planned workflow is not misrepresented as a completed CI run.

Every result remains **PcInspectionOnly / NotFlashReady**. Full ECU boot and
hardware execution were not performed; physical RPM is unavailable; checksum is
not tested and remains Unknown. A derived BIN may fail native ECU integrity
checks. No checksum repair/bypass, flashing, Crome/HTS installation or calibration
recommendation is included. Interpreter/model agreement is not independent proof
of the unresolved ADD semantics or factory authenticity.

## Actual private byte-execution results

The existing baseline, listing, dossier, original binding, and already verified
M1c output/plan/report were present and reused. No replacement BIN was sought.
Both modes actually ran one Rust batch each, covering all three scratch patterns:

| Compact category | Strict | Conditional |
|---|---:|---:|
| Total executions | 393216 | 393216 |
| Matches without assumptions | 372120 | 372120 |
| Stopped unresolved, **not passed** | 21096 | 0 |
| ConditionalMatch | 0 | 21096 |
| Unresolved model / mismatch / execution error / budget exceeded | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |

Per scratch pattern these measured counts are 124040 established matches and
7032 unresolved/conditional cases. They happen to agree with the earlier model
comparison split; they were not used as an execution oracle. The three patterns
agree on all outputs/statuses. Strict used no assumptions; conditional actually
reached only `oki.add-er3-a`. The established model remains unchanged.

Threshold execution in **each mode** completed 12288/12288 matches for the
baseline and 12288/12288 for the verified child, with zero unresolved/mismatch/
error/budget outcomes. Program-read checks passed for every case. For each image,
6144 disabled cases preserved both bits and did not read the threshold block.
The other 6144 cases executed the two LC word reads at the expected addresses.

Across 12288 paired baseline/child cases, the expected changed-result set and
actual changed-result set were exactly equal: **6 cases** (one compact code,
one context, the edited pair's prior state, both other-pair prior states, three
scratch patterns). The modified program byte was actually read in **3072 cases**;
a read alone does not imply selection of that byte or a changed predicate.
All other one-step cases were unchanged. These are software state bits, not a
physical solenoid observation. Original M1c parent/plan/report verification passed
before admitting the child; no new binding was created.

Each private execution report retains 20 bounded selected diagnostics, including
boundary inputs and enabled/disabled threshold paths. No mismatch required a
failure replay. The adapter can replay up to four mismatches against the same
unchanged image and seed to retain a bounded trace; these replays are not counted
as new full-domain cases or called synthetic-program evidence.

Before/after SHA-256 checks confirmed that the original, working copy, public
profile, original binding, M1c child/plan/report and listing all stayed unchanged.
Their identities and source bytes remain private. ROR correction, byte execution,
conditional model agreement, file lineage and hardware proof remain separate
evidence categories.

After independent review, the threshold batch was additionally hardened to run
with **no ADD permission**, even when compact mode is conditional. A public
invented jump-only batch and mutated threshold instruction confirm that this
cannot conceal a conditional execution inside a resolved threshold result. Both
private full-domain modes were rerun with the hardened executable; all counts and
threshold comparisons above remained identical. The earlier reports were retained,
not overwritten.
