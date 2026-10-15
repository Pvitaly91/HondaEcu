# M2bm: isolated Rust synthetic adapter capabilities

This milestone implements research infrastructure, not an ECU program. Its base
is `7c37185a104348685d7604b74bf885057a95149d`; delivery belongs only to
`codex/p28-word0196-rust-synthetic-adapter-m2bm`.

The M2bj identity remains 51 bytes, 20 nodes, 16 forms and SHA-256
`91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1`.
That digest is an upstream identity, not a payload or permission to execute it.
The adapter never loads those bytes or an original ROM. Its twenty-node table
contains reviewed metadata only and has no byte-emission interface.

## Architecture and authority

The separate, unpublished Rust library uses a path dependency on the unchanged
`p28-slice-runner` 0.43.0. Actual production `Cpu` state and `decoder::decode`
are reused. A new, narrow research executor implements exactly the sixteen
reviewed forms. It does not call production `exec::step`, use production `Bus`,
invoke the runner, or introduce a production operation. Protocol 1 and all 38
runner identities remain unchanged.

This is the authorized architecture B. A simple Bus wrapper cannot satisfy the
requirements: production execution requires its concrete Bus, uses zero-based
PROGRAM storage, and has crate-private observation APIs. Byte-identical source
reuse alone is not evidence of equivalent execution through a different bus.

The executable boundary accepts only an allowlisted invented microfixture ID,
its exact literal bytes and form, an actual content digest, an explicit complete
entry, and one-instruction budget. Selected instructions are 1-5 bytes; the
entire microsegment is at most 6 bytes. Explicit alternating invented guard
bytes may support decoder lookahead, but are never selected or retired. No
generic stream loader, composite execution loop, arbitrary operation fallback,
original-ROM input or external-anchor stub is provided.

## Six separately evidenced capabilities

| Capability | Compiled component | Runtime proof obligation | Integration boundary |
| --- | --- | --- | --- |
| A: PROGRAM mapping | `SyntheticProgramSegment`, `MicroProgram` | All 51 opaque cells; real short-program base subtraction; bounds and identity refusals | Opaque mapping is not CPU execution; short-program accesses reach the real decoder |
| B: closed admission | `ClosedFormAdmission`, `FormId` | Exact twenty-node metadata policy and sixteen-form decoder/operand checks | Microprobe form gate integrated; twenty composite positions never executed |
| C: entry state | `SyntheticCpuEntrySnapshot` | All eight selectors, all 32 pointing values, aliases and retained state | Actual `Cpu` plus research DATA; physical SF remains unknown |
| D: DATA isolation | `IndependentDataAccessPolicy` | Separate read/write rights, LE16, real raw/logical accesses and fresh writes | New research DATA interface, not production Bus integration |
| E: fetch and exit | `OrderedProgramFetchObserver`, `SyntheticExternalExitTrap` | Actual decoder probes, selected reads, one real J and no subsequent fetch | Actual production decoder plus new one-instruction executor, not native ROM handoff |
| F: PSW bridge | `CanonicalPswBridge`, `OpaqueSfBoundary` | All 65,536 actual PSW round trips and paired internal-SF microprobes | Current canonical `Cpu` representation only; full lossless input scope retained separately |

For each row, delivery evidence distinguishes `ModelVerified`,
`RustImplementationCompiled`, `RustUnitTestsPassed`, `MicroprobeRuntimeObserved`,
`ProductionCpuIntegrated` and `FullCompositeExecutionObserved`. The final level
is always `NotRun`. A qualified CPU integration result means
`CpuStateAndProductionDecoderWithResearch16FormExecutor`, not production
Bus/exec/runner integration and not `FullSyntheticCpuIntegrationVerified`.

## Independent expectations

Instruction expectations are literal, sealed before runtime observations, and
derive from the September 1991 MSM66201 instruction manual (SHA-256
`f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271`),
M2av C11/IR semantics, M2bd dataflow and M2bk/M2bl obligations. The public
fixture is a value-preserving, public-safe projection of those independent
seals. Neither the new executor nor its output determines expected results.

The corpus specifies 39 instruction/control contexts and 12 additional DD
contexts, each with two separately seeded internal-SF variants. These are 102
planned one-instruction observations, not 102 composite executions. Four
DD0-only forms have explicit DD1 refusal controls. Actual counts and the first
mismatch come from the compiled tests, not these planned totals.

The checks compare complete entry/terminal state, every DATA byte, ordered
logical and raw DATA effects, same-value writes, exact decoded identity and
operands, selected bytes, PC, branches, exit identity and all raw PROGRAM
observations. Manufacturer pattern evidence is independent of the production
decoder table. Passing round trips alone does not establish instruction truth.

## Entry, DATA and observation rules

Entry explicitly supplies PC, A/AL/AH, PSW and named flags, OtherPSW, LRB,
SCB, SSP, halted state, provenance, eight pointing banks, local r/er aliases and
an opaque SF descriptor. Missing fields are errors, including required nullable
SF fields. No `Cpu::new()` defaults complete a missing architectural snapshot.
LRB is 0021, page is 0100, local bank is 0108-010F, and r1/DATA0109 is high(er0).
SCB derives from PSW low3. Pointing values occupy all eight reviewed banks in
DATA0080-00BF and are setup/diagnostic context, not extra functional permission.

The functional inventory is DATA0108-010F, 0117, 0124, 0128, 012A, 018E,
018F and 0196/0197. DATA0196 is read-only LE16; immediate 00C0 is not a DATA
read. The permission profile suppresses DATA0124 reads on B and permits
DATA012A writes only on D. A microprobe's permission-profile label does not
claim the corresponding composite path is reachable from its invented seed.
Isolated STB probes use profile A; the other sealed probes use profile D.
Address/path-required Store, LocalRegisterStore and RMW kinds cannot be
substituted by a caller to bypass the preceding-read requirement.

Functional reads/writes, constituent byte accesses, initialization and
diagnostics use separate journals. Every same-value store gets a new ordinal.
RMW requires an immediately preceding real same-address byte read. An invalid
functional access latches a fault; it cannot silently return zero and continue.

Every callback supplied to the actual production decoder acquires a PROGRAM
record, including repeated probes and rejected-pattern lookahead. The acquired
purpose is retained. Post-selection lookahead classification is explicitly an
association with the selected extent, not a fabricated historical byte read.
Separate selected reads are actual ordered reads, marked before acquisition.
No decoder callback is reconstructed from a later PC sequence.

The decoder's `Fn(usize) -> u8` interface has no fallible return channel. The
research bridge aborts an invalid probe with a typed sentinel, catches only that
sentinel locally, and propagates unrelated panics. It neither supplies a fallback
byte nor alters a global panic hook. A short-program bounds failure is explicit.

One independently invented direct J updates actual `Cpu.pc` to 5596 or 55C5,
then seals both retirement and PROGRAM observation. No target fetch, NOP/RT/BRK
stub, zero-step exit, second transfer or hidden return is permitted. This proves
only the bounded research mechanism, never native exit isolation or ROM rejoin.

## PSW and SF: preserved gaps

The unchanged CPU represents absent bits with `PSW_READS_ONE=0CC8` and stores
OtherPSW through `PSW_STORAGE=0337`. Route A accepts only compatible research
inputs, `(OtherPSW & 0CC8) == 0CC8`, before state mutation. Route B retains each
original lossless expected word; incompatible words are classified
`NotRepresentableByCurrentCanonicalRustCpu`, not normalized into expectations.

The independent M2bl oracle is compared against all 65,536 actual
`set_psw_u16`/`psw_u16` observations. Required classifications are 128/3968 in
low12 and 2048/63488 in the full word domain. M2bk's independent domain is not
narrowed. Future composite admission still needs a separate user scope decision
or separately authorized representation work for incompatible inputs.

Physical SF remains `SFMeaningStorageNotEstablished`: value, meaning, storage
and width are unknown. The exact sixteen allowed forms do not use stack/SF
operands; source audit and paired false/true *internal Rust field* experiments
must agree on all architectural results and preserve the seeded internal field.
This is not a claim that native SF is boolean or globally irrelevant.

## Reproducible research QA and CI

Run the research-only validator from the repository root:

```text
python -B research/p28-word0196/validate_synthetic_rust_adapter_contract.py
```

It verifies source bindings, builds the actual crate, runs its real tests and
checks independent runtime records. Rust test counts, component checks,
microprobe instances/instructions, PSW instances and metadata-only refusals are
reported separately. No JSON status alone grants runtime authority. Actual
Ubuntu and Windows receipts must each show compilation and execution; compare
their complete semantic records, not just matching green job statuses.

Production Rust321/Core2947/CLI959/Desktop183, historical suites, independent
C11/C# checks, formatting, privacy and full protected hashes remain separate
required delivery gates. Heavy jobs run sequentially. Desktop timeout and
acceptance are unchanged; M2bj Option B does not extend to M2bm.

## Unchanged exclusions and next evidence boundary

`ActualSyntheticCompositeExecutionNotRun`;
`TargetCPUExecutionNotObservedForNewComposite`;
`ActualDownstreamRejoinNotEstablished`;
`PhysicalROMPlacementNotEstablished`;
`TargetProgramEquivalenceNotEstablished`;
`FirmwareIntegrationNotEstablished`; `FirmwareReady=false`.

There is no original-ROM execution, target object/BIN/HEX, firmware writer,
linker/placement, ECU handoff, GUI smoke or hardware work. A possible next
milestone is a separately authorized bounded composite experiment only after
reviewing the retained PSW/SF and isolation obligations. It is not started or
authorized by M2bm.
