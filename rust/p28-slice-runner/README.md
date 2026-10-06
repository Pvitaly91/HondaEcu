# Bounded P28 research runner

Runner **0.40.0**, wire protocol **1**, pinned Rust **1.85.1**. The original
upstream CPU provenance and license are retained in
[the third-party notices](../../THIRD_PARTY_NOTICES.md). No OEM image or native
program fixture is distributed here.

M2ah adds `data0136TailToTimerBoundary`: native post-NoWrite CMP/JNE prefix,
STOP BEFORE5722/unowned019B.2. Not timer-boundary completion; no source/ABI repair,
fresh0136, time/IRQ or return. [M2ah](../../docs/M2AH_DATA0136_SOFTWARE_TAIL.md).
Historical M2ag still stops5719; no executor fix or JGT/global policy change.

M2ag adds `fallthroughData0136CallerHandoff`: retained064C fallthrough, native
CAL0664 and bounded NoWrite to stop5719. No ABI/slot/gate seed; pending0667 frame
terminalizes later events. No fresh0136,time/IRQ/GUI/BIN. See
[M2ag](../../docs/M2AG_FALLTHROUGH_DATA0136_CALLER.md); old boundaries/fixes unchanged.

Build and test from the repository root:

```text
cargo +1.85.1 build --release --locked --manifest-path rust/p28-slice-runner/Cargo.toml
cargo +1.85.1 test --release --locked --manifest-path rust/p28-slice-runner/Cargo.toml
cargo +1.85.1 fmt --check --manifest-path rust/p28-slice-runner/Cargo.toml
```

One bounded JSON request is read from stdin; one JSON response is written to
stdout. Stdin remains limited to 16 MiB. Caller-side timeout, cancellation,
output limits and protocol validation belong to the existing C# process adapter.
A successful process exit is not an execution match or a hardware result.

## Operations and state lifetime

| Operation | Scope |
|---|---|
| `postReturnSelectorHandoff` | M2ae: actual RT063E exit→native064A selector producer; once initial source, retained next0584/05DF generation; stop before064C; no repair or recovered scheduler |
| `calRtRoundTripHandoff` | M2ad: PC-only schedule063B; native CAL54F5, retained M2ac below path and same-frame RT5688→063E; balanced SSP, stop before063E; no enclosing caller/IRQ recovery |
| `p28Batch` | Existing compact/threshold seeded cases |
| `producerBatch` | Existing G and staged F cases, with threshold comparisons |
| `checksumBatch` | Existing 512-call checksum state, exact ordered read coverage |
| `synthetic`, `checksumSynthetic` | Bounded invented-program instruction/process probes |
| `acquisitionSequence` | Frozen capture observations and optional scheduled G/F/threshold, one persistent CPU/RAM per image and scratch pattern |
| `fuelCalculationChain` | Historical M2k strict word0140 reader/scaling; stop-before21F2 |
| `fuelAdditiveCorrectionChain` | M2l strict native correction producer→scaling→XCHG/VCAL4/return→first software stores; one continuous tail2194..2204 |
| `fuelFactorProductionChain` | M2m strict native0158 producer and actual word handoff to21DD, followed by the shared continuous M2l tail; no ready factor input |
| `limiterFuelGateChain` | M2n decision-only fixed1966..1A38, same-state M2m bodies, actual217A/21F5 gates and03A2/03B4; no request/factor setter or5585/P2 |
| `adaptiveLimiterFuelGateChain` | M2o native5BD0 ticks and487B/helpers→RAM01A4/01A6→decision-only1966→same-state M2n fuel tail; one masked snapshot, native writer/hold provenance, no5585/P2 or supplied thresholds/request/factor |
| `belowSecondP2Handoff` | M2ac actual below-path55CF→55D2 ROLB A and continuous owned-RAM branches; retained TCON0/P2 architecture; second P2 generation; stop-before RT5688 |

The separate [M2ac contract](../../docs/M2AC_BELOW_SECOND_P2_HANDOFF.md)
requires0.36.0; historical0.35 refuses its payload. Old operations do not
inherit new code ranges or P2 capabilities. Peripherals/time/IRQ/pins are not
advanced. The reviewed byte-accumulator rotate fix is a separate identity
from the historical off-page rotate and DD1 word-accumulator semantics.

The acquisition guide below describes its existing operation, not all later
milestones. The closed M2l sources, lifetime, exact-form evidence and read-only
CLI are documented in [M2l](../../docs/M2L_ADDITIVE_FUEL_CORRECTION_CHAIN.md).
The factor-free input contract, native1F43→7A99→1FB7 detour, separate0140/0158
generations and disclosed same-machine scripted schedule are documented in
[M2m](../../docs/M2M_NATIVE_FUEL_FACTOR_CHAIN.md). This producer does not recover
physical units, source acquisition, boot or the ECU scheduler. Historical M2k/M2l
operations retain their isolated factor-snapshot contracts. Exact word ROL er0
and SLL A fixes are disclosed in the semantic-fix inventory; disputed47 81/45 81
and SUBB permissions are not inherited by M2m.

Old task entry contracts and optional response-field shapes are unchanged.
Every old operation rejects an acquisition payload. `Bus::new` remains
memory-only: non-CPU SFR access is an error until the acquisition stage alone
activates its narrow, read-only observation capability. That capability is
removed before G, F or threshold execution.

All operations use the same decoded `step` executor and bounded execution loop.
There is no host acquisition or G/F/checksum formula inside this runner. Supplied
ROM bytes are not replaced with NOP/RET or expected outputs. Old independent
`oki.add-er1-a` / `oki.add-er3-a` permissions remain explicit; acquisition and
threshold admit neither permission.

## Acquisition sequence wire contract

The exact closed request/result types and machine-readable entry contracts are
in [src/acquisition.rs](src/acquisition.rs). A request has one sequence of
1–1024 densely indexed observations, one original image and optionally one
derived image, exact scratch patterns `[0,85,170]`, and at most eight selected
trace observation indexes. Each image executes the **whole** sequence on its
own CPU/RAM, including its own G/F code bytes.

Initial state contains previous timestamp, six samples, initialization and
overflow/service fields, previous producer T/status and DATA0136. Each stimulus
declares TMR2, IRQH, TCON2, caller slot 0–5, whether to compose, and threshold
context/prior/enabled values. It contains no independent DATA010F flag: that
byte is the high half of the captured er3 word in the selected bank.

The acquisition slice uses PC56BE, code ranges `[56BE,56DF)` and `[5701,5719)`,
and stops before5719. LRB0021, PSW1102 and USP0280 are explicit call-entry
context. SSP07FE is a technical unused seed, not a recovered caller stack.
The alternative DATA011F.2 mode refuses before fetch.

The bus exposes only a 16-bit TMR2 read at003A, byte IRQH read at0019, and byte
TCON2 read at0042. These frozen observations are nondestructive in the stated
no-new-event/no-interrupt scope. Unsupported widths, unknown SFRs and all SFR
writes fail. No instruction-cycle clock, interrupt entry or IRQ scheduler runs.

Checkpoints retain actual peripheral accesses, actual sample store events
(including same-value writes), state before/after scheduled composition,
per-slot write counts, cumulative assumptions and local stage results. Unwritten
old samples are never inferred to be new measurements. Store widths are **bits**;
peripheral operation codes are 0 read and 1 write. Instruction extents contain
unique sorted bytes of admitted instructions actually passed to `step`, not
speculative decoder reads; program-data reads are separate.

Only explicit call-entry registers, caller slot and scheduled threshold fields
are reset between calls. G uses actual acquired samples; F uses actual G state;
threshold uses actual F code. DATA00CC=0 / DATA0131bit0=0 are initial-only
preconditions; subsequent prefix effects and unrelated bits are preserved.
The skipped producer history bridge is stated explicitly, not called a full
ECU routine. Any unresolved/error/budget/unsupported outcome terminates the
sequence: later observations have explicit NotRun checkpoints and retained
partial state. An acquisition-only run is independent, not a continuation of
a stopped composed run.

Traces are bounded to128 instructions per selected stage and the first local
failure. Failure replay starts from the original initial state and the preceding
observation schedule, never from an observed Rust intermediate snapshot. The C#
validator independently advances its own model history and can request the same
bounded prefix replay for a mismatch. A non-read of the compensation location
in these logs is a bounded observation, not a new global unused-location proof.

See [the M1i instruction/SFR audit](M1I_ACQUISITION_AUDIT.md) and
[the existing M1f audit](M1F_CHECKSUM_AUDIT.md). Public tests use invented probes;
actual native-image comparisons remain separate private evidence. Everything
remains **PcInspectionOnly / NotFlashReady**; physical RPM, full boot, hardware
capture races and GUI acceptance are not established here.

## Integrated capture-to-VTEC task (0.6.0)

`integratedCaptureVtec` uses a closed version-1 `integratedChain` object with one
initial state, 1–256 dense events and at most eight selected trace indexes.
The event contains frozen TMR2/IRQH/TCON2, caller slot/context/enabled, explicit
raw/software snapshots, bounded fast/slow body counts and one `runDecision`
Boolean. It never accepts per-event samples, T, compact Code or prior/request.
Images are either one baseline or exactly ordered baseline/intermediate/derived;
each image/scratch pair gets its own CPU/RAM and retained P1 latch.

The fixed order is inputs → acquisition → native counter bodies → scheduled
G → F → decision. Only acquisition can read capture snapshots; only decision
can access P1 output-data, and disabling access does not erase the latch.
The command reuses existing in-state execution and exact-form policies, not
isolated runner initialization. `chain_forms` admits the already audited
compact forms without broad mnemonic or unknown-form fallback. Permissions
er1/er3/SUBB are stage-local and cumulatively taint later history.

Every stage reports shared state and CPU/bank/SCB/stack boundaries, native
writes, instruction extents, data reads, gates, body counts and bounded traces.
The first terminal stage stops all later stages, events and input application.
Its decoded-but-refused instruction is not an executed extent. Native counter
traces aggregate at most 128 instructions per stage, including selected replay.
Runner 0.6.0 retains the 0.5.0 semantic-fix inventory; the DIVB refusal extent
correction is diagnostic accounting, not new ISA semantics. Old tasks keep
their contracts. See [M1k scope, schema and actual results](../../docs/M1K_INTEGRATED_CAPTURE_TO_VTEC.md).

## Adaptive limiter task (0.8.0)

`adaptiveLimiter` consumes a closed `adaptiveLimiter` stimulus: version 1,
once-only initial state and 1..64 calls with at most 32 selected native counter
iterations per call. It executes producer, existing limiter and consumer on the
same CPU/RAM, never injecting produced words per call. Program table reads,
stack, data/SFR ranges and instruction forms are bounded. No ADD/SUBB hypothesis
permission is accepted. A terminal stop leaves downstream/suffix stages null.

Version 0.8.0 adds `adaptive-exact-word-add-sub-half-carry` to the semantic-fix
inventory. Older version/operation inventories remain explicitly recognized.
The `limiterSequence` task keeps its original initial-RAM-snapshot contract.
See [M1m contract, instruction audit and private results](../../docs/M1M_ADAPTIVE_LIMITER_THRESHOLDS.md).
