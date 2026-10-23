# M2bt - bounded original-ROM production execution, research only

M2bt adds a default-off, closed research execution interface, not a firmware
loader, replacement CPU, patcher, original downstream runner or hardware tool.
Its immutable parent is M2bs4196153c6bcda3da5b164db752a8be4011c4e598.
Historical M2br and M2bs sources, contracts, oracles and receipts are not rewritten.

## Two explicitly different evidence domains

`LocalOriginalRomExecution` reads an explicitly selected private local image
through the unchanged M2bs source verifier. The size, whole-image digest,
historical source binding, provenance dossier, frozen listing and27selected
extents must agree. Actual PROGRAM bytes come only from that immutable image,
at original addresses, never from the M2bj emitter, a manually copied byte list,
an invented fixture, a download or an alternate candidate selected by filename.

The private PROGRAM segment is the unchanged86-byte slice556F..55C5exclusive.
Non-instruction gap bytes retain their original values. A separate closed
18-site allowlist, not presence in the segment, determines execution authority.
Before/after source-byte and file-identity fences remain mandatory. No private
PROGRAM payload is written as a BIN, object, HEX or public fixture.

The narrower accepted execution classification can be
`OriginalRomBytes_TechnicalSeededExecution`: real original bytes executed using
explicit technical CPU/DATA inputs. This does not establish a native firmware
scheduler, initial-value generation, stack frame, physical SF or ECU execution.
An independently verified historical value is not a new native generation when
copied into a newly initialized host session.

`PublicSyntheticExecutionRegression` uses a separately invented, closed fixture
at6000 with different DATA roles. It tests production machinery and permissions
without OEM bytes, historical register snapshots or private ROM identity.
Public CI cannot claim that the original ROM was executed there.

## Production machinery and the third closed lifecycle

The opt-in Cargo feature `p28-word0196-original-rom` depends on the existing
`p28-word0196-audit` feature. Both remain defaultOFF. The separate research
binary is `m2bt-original-rom`; ordinary runner version/protocol/operations and
default admissions are not extended with a generic stepping interface.

Execution uses the existing production Cpu, Bus, decode_checked and
execute_decoded through audit::Session. New code contains source admission,
closed control-flow authority and observation, not alternative opcode arithmetic.
The existing single-step/composite/transfer lifecycles remain separate: an
original stop-before fallthrough is not fabricated as a synthetic direct-J exit.

One case owns one CPU and one Bus with one immutable PROGRAM source. Entry is
set once; subsequent PCs come only from production instruction execution. Seeds
are permitted only before functional execution. No mid-execution register edit,
second-machine transfer, reseed or host-applied algorithm formula is admitted.
Before each instruction, currentPC/DD and exact decoded identity must match
the closed inventory. Ordered PROGRAM, logical DATA and raw DATA journals are
retained independently of diagnostic snapshots.

## Closed original paths and peripheral stop

| Path | Predicate | Exact retirements | Stop before | Ordered DATA writers |
|---|---|---:|---|---|
| A | word0196 below00C0 | 10 | 55C5 | 5572,55C1,55C3 |
| B | NotBelow;012A.7 set | 12 | 5596 | 5572,557F,5582 |
| C | NotBelow;first gate clear,0124.5 set | 13 | 5596 | 5572,557F,5582 |
| D | NotBelow;both gates clear | 15 | 5596 | 5572,557F,5582,558B,558E |

Little-endian word0196/0197 is compared against a code-owned immediate00C0,
not RAM00C0. CF is unsigned borrow; DD is cleared by the first LB. AH, HC,
OtherPSW, SCB, LRB, SSP and all unaffected declared aliases are retained.
The production representable-PSW predicate is not widened for more passing cases.

M2bs established the original P2-related instructions at5596 and55C5. They are
not retired by M2bt. The session stops when actual CPU PC reaches its expected
boundary, before calling production Exec for the terminal instruction.
Decoder probes, selected instruction fetch and functional DATA accesses remain
distinct observations. P2 functional reads/writes and hardware interactions must
be0. No invented P2 latch, timer, IRQ, fullboot or downstream execution is allowed.

## Inputs, provenance and independent expectations

All technical inputs are explicit: A/AL/AH, full representablePSW and aliases,
LRB0021, SCB, SSP, eight pointing banks, localr0..r7/er0..er3, hostSF/halted and
the16 inventoried DATA bytes. Permissions are path-specific and fail closed on
unauthorized reads/writes, SFR or aliases. Setup seeds are not functional native
writes. Same-value writes keep their own writer ordinals and old/new values.

The closed small corpus has32base states with paired internal hostSF values,
covering A/B/C/D, DD0/1, HC/OtherPSW/SCB retention, word boundaries0000/00BF/
00C0/00C1/00FF/0100/FFFF, first/second bit gates and same-value writes.
The64public cases use only the independently invented fixture. The70private
cases add6historical-subset-aligned technical completions, separately classified;
their missing live-ins receive explicit technical completions, not native facts.
PathC has no selected historical native witness. Technical coverage does not
manufacture one.

Independent expected CPU/flags/DATA states derive from the unchanged M2av
structured C11/IR and M2bk reference semantics, not Rust CPU output. Mapping
synthetic reference coordinates to logical original sites is explicit; synthetic
direct-J retirement and branch relocation bytes are not original-ROM evidence.
PROGRAM acquisition topology is checked separately from state semantics.

Before the first final-source runtime the host publishes immutable source,
corpus, complete expected-state, stop-PC and oracle bindings. Every actual case
is compared to those frozen expectations. A mismatch preserves the first PC,
field, expected and actual values and blocks acceptance; expected outputs are
not regenerated from observations for a passing result.

## Atomic resume and bounded evidence

The mutable checkpoint is local and published atomically. Complete per-case
observations and their canonical hashes are immutable receipts. On resume the
host checks source/corpus/freeze identities, complete record content, IDs/order
and any active owned process before starting the next unfinished case. A valid
completed receipt is reused without repeating execution. Truncated/duplicate/
mismatched records never count as successful observations.

An interruption is not permission to start another runtime. Current process
identity, pending cases, CI run ID and next action are preserved. Checkpoint and
execution state live outside the four-file public artifact directory.
No recurring scheduler, background archive sync or extra automation is created.

## Local commands and CI source boundaries

All new local Cargo builds and tests require the reviewed build-routing guard
and the fixed task-owned target. A local controller authenticates its external
ownership receipt, checks the current protected-runner identities, rejects
configuration/environment overrides and junction/symlink/hardlink conflicts,
and fences protected inputs before/after the child process. It never adopts the
ordinary historical target. The public CI path-only preflight is explicitly not
a substitute for this stronger private local preservation fence.

After that local preflight, the opt-in research build has this routing:

```text
cargo +1.85.1 build --release --locked --offline --jobs 1
  --manifest-path rust/p28-slice-runner/Cargo.toml
  --target-dir .tmp/m2bt-owned/cargo-target
  --features p28-word0196-original-rom --bin m2bt-original-rom
```

`CARGO_TARGET_DIR` must also name the same absolute task-owned target. The
research runner is read from that target's `release/m2bt-original-rom` (plus
`.exe` on Windows), never from a historical runner directory. Full default,
old-audit and new-feature Rust test coverage remains required; `--lib` is not a
way to silently reduce final QA coverage.

The platform-neutral host CLI is
`research/p28-word0196/validate_original_rom_execution.py`.
Use `--rom <explicit-private-local-file> --profile <explicit-M2bs-profile>` for
private execution, or `--public` for invented regression, plus explicit
`--runner` and `--output` paths. The two modes are never silently substituted.

Existing heavy historical CI gates retain their exact pinned2657source; the
unchanged M2bs guard and98tests execute at4196153. The same checkout then moves
to the active M2bt commit for its reviewed source join and current Rust default,
old-audit and new-feature tests/build. Desktop remains its ordinary active job.
Historical compiled QA is not claimed to execute the changed opt-in Rust delta.
All four new active CI Cargo build/test commands name the task-owned target
both through the environment and `--target-dir`; a fresh-public-CI preflight
checks ownership, non-overlap and reparse-free output routing before each one.
The exact pinned historical and Desktop command bodies remain unchanged.

`contract.json` is a closed requirement declaration, not a result receipt.
`contract_validation.validate_contract(source_bindings=...)` checks its complete
reviewed shape, three frozen public M2bs/IR/C11 source identities, actual64-case
mathematical corpus coverage and the supplied complete active source-binding
schema. The source guard independently verifies those supplied current bytes.
The full source fingerprint is frozen externally, so the declaration contains
no cyclic self-fingerprint or private ROM digest. Neither JSON nor a static
validation result can create CPU execution or preservation-exception authority.

Ubuntu/Windows upload only public canonical.jsonl.gz, summary.json,
pre-runtime-freeze.json and sourcejoin.json. No private input is available in CI.
Delivery compares complete decompressed canonical bytes, including all semantic
fields, record order and counts; hashes alone or platform-specific exclusions
do not replace byte equality. Freeze binary identities can differ by OS and are
separate metadata, not stripped fields of the semantic canonical stream.

## Preservation, remaining unknowns and STOP

Source joins pin raw historical Git identities plus the reviewed current delta.
Explicit previously sealed local XML representations are retained separately,
never normalized to manufacture a physical-byte comparison. Protected audits
use selected manifests/read dependencies rather than rehashing an entire archive.
The authorized AGENTS automatic-resume append is explicit in the new fingerprint,
not a change to old M2br/M2bs freezes. Old private reports and unique data remain.

One generated historical runner was overwritten during development by an
incorrect Cargo output route. Exact-byte recovery was attempted but did not
restore its historical identity. The original expected identity, actual current
identity, auxiliary alias loss, searches, incident and failed recovery remain in
private immutable evidence; no old manifest, validator or report is rebased.
This is not an original-ROM change or a replacement of recorded observations.

The user authorized one conditional local exception only after seven explicit
conditions, including selected source/ROM/unique-observation preservation, were
checked. The current delivery audit must keep the raw mismatch visible: one
selected protected runner difference, one authorized preservation exception,
and zero other unauthorized protected differences only when freshly verified.
Historical executable preservation is22/23 exact, not23/23. The strict raw
historical-byte predicate is not called PASS. Five separately authorized M2bt
source overlays are not counted as this one generated-runner exception. An
unavailable backup/archive is not evidence that no additional copy exists.

This document does not itself attest final technical delivery. With the recorded
exception, the only permitted successful delivery verdict is
`M2bt ACCEPTED_WITH_PRESERVATION_EXCEPTION / Research-Only`, after all remaining
runtime/oracle/QA/exact-SHA CI/canonical-byte/seal gates pass. It is not ordinary
unqualified `ACCEPTED`. Any indispensable frozen gate that cannot accommodate
the documented exception remains a real blocker; it is never skipped or
relabeled PASS.

ActualHardwareEcuExecutionNotObserved, NativeSchedulerNotEstablished,
PhysicalSFNotEstablished, NativeStackSafetyNotEstablished,
PeripheralStateOwnershipNotEstablished, ActualNativeDownstreamRejoinNotEstablished,
SafeROMPlacementNotEstablished, TargetProgramEquivalenceNotEstablished,
FirmwareIntegrationNotEstablished and FirmwareReady=false remain even after a
successful bounded technical execution. Retirement counts are not ECU time.

The private final Ukrainian report is written last, after QA, normal commit/push,
exact-SHA three-job CI, public canonical comparison and evidence seal.
After M2bt delivery STOP: no M2bu, original downstream, firmware, flashing,
GUI or hardware.
