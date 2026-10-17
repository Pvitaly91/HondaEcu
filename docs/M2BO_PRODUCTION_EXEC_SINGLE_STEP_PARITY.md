# M2bo — production exec single-step differential verification

This research-only experiment is based on commit
`50dfe6b0ee814caddb69eaaa9c01936d9894bed5`. It does not modify the production
runner, CPU, Bus, decoder, instruction semantics, or historical evidence.

The executable path is the unchanged `p28_slice_runner::exec::step` with an
actual production `Cpu`, `Bus`, decoder and operand execution. The independent
Python reference determines expectations before execution; neither the old
research executor nor new production observations generate those expectations.

## Experiment and admission

The finite corpus comprises all 51 sealed M2bm contexts, 128 co-varied flag/SCB
controls, 50 byte-edge controls and five word-boundary controls. Each of these
234 contexts has both internal Rust SF boolean values: 468 positive steps.
This is bounded coverage, not a claim of exhaustive instruction equivalence.

Each admitted request receives one explicit CPU literal, one zero-based Bus,
one DATA initialization, all eight pointing banks, and one production step.
There is no reseeding after execution. The physical SF descriptor stays unknown;
the Rust boolean pair only checks internal retention and noninterference.

The positive PSW domain is explicitly
`(fullPSW & 0x0CC8) == 0x0CC8`: 2048 representable and 63488 incompatible words.
Incompatible states are rejected before constructing an executing CPU. They are
not silently repaired or normalized.

Only the already invented M2bm microfixtures are used. Their reviewed small
guard geometry is explicit. Logical entry PC `0x1000` is relocated to physical
PC `0` because the unchanged Bus has a zero-based ROM vector. Relative PC
expectations are translated explicitly; absolute direct-J targets remain
`0x5596` and `0x55C5`. No 4096-byte prefix or complete composite is supplied to
production execution. A direct-J microprobe makes only one step; it does not
prove a general external-fetch guard.

## Comparison and observation limits

The pre-runtime freeze binds the corpus generator, exact requests, expected
decoded identity and architecture, source identities, relocation, and canonical
projection. Canonical records retain all compared observable fields; they omit
host metadata according to the predeclared projection, not after a discrepancy.

Comparison includes returned decoded index/mnemonic/length/fields/DD-after,
instruction-cost accounting, full CPU state, PSW aliases, local byte/word aliases,
all 32 pointing words, SSP/LRB/halted/internal SF, and diagnostic before/after
RAM snapshots. These are architectural final-state observations. They are not
an instruction-access journal.

The following unavailable properties must remain `ObservationNotAvailable`:

- Actual decoder callback probes inside production `exec::step`.
- Ordered logical/raw DATA accesses, RMW access order and same-value store
  occurrence through the external production Bus API.
- Separate path-specific read/write enforcement through `configure_scoped_access`.

`Bus.program_reads()` logs table-data PROGRAM reads, not instruction decoder
probes. An empty list is not proof of absent instruction fetches. Branch outcome
derived from observed PC is explicitly classified as derived. Expected static
effects are never relabeled as observed events.

## Production integration boundary

The separate capability audit binds concrete source lines and distinguishes
actual executable checks from source-level limitations:

| Capability | Unchanged production path | Remaining requirement |
|---|---|---|
| Single-step reviewed forms | Actual production step and architectural comparison | Finite-corpus scope only |
| PROGRAM mapping at `0x1000` | Zero-based vector; invented segment boundary negative | Checked nonzero-base segment mapping |
| Decoder fetches | Internal step callback using public `peek_code_u8(...).unwrap_or(0)` | Strict bounded observable decode reads |
| DATA permissions | One shared range set for reads and writes | Independent read/write policy without widening |
| DATA access journal | Relevant native/logical journals are crate-private | Phase-separated externally observable ordered effects |
| Entry/exit lifecycle | A research caller can call exactly one step | Reviewed bounded composite loop and stop-before-external-fetch |
| Error atomicity | Some operand errors occur after PC/counter advancement | Explicit partial-state failure contract, not invented atomicity |

An invented 51-byte canary segment, not the M2bj composite, demonstrates mapping
failure. A separately counted hardcoded DATA-error fixture demonstrates actual
partial-state behavior. Neither is a positive parity case or a composite run.

Two future architectures are assessed but not implemented here. A narrow,
opt-in production API would need checked mapping, strict decoder observation,
independent DATA permissions and public phase-aware journals, with a separately
authorized source-binding transition. A research-only source-bound fork would
need equivalent Bus coupling and proof that semantic bodies remain identical;
copying `step` alone cannot make the concrete private Bus observable. Neither
route is authorized by a successful M2bo microprobe result.

## QA and delivery boundaries

The M2bo validator compiles the actual research harness, executes the declared
corpus, compares against the independently frozen reference, runs real admission
negatives and semantic comparator mutations, and emits public-safe canonical
semantic records. Local, Ubuntu and Windows records require full byte equality,
not merely matching totals or digests. Full historical regression and existing
Desktop CI remain unchanged, including the 30-second budget and real WPF/RPM
checks. Option B is not expanded.

Acceptance requires all 16 forms, all declared cases, negative checks, complete
QA, exact-SHA CI 3/3, cross-platform byte equality and protected preservation.
The permitted verdict is
`M2bo Production Exec Single-Step Parity Verified / Research-Only`.

Regardless of parity, `ProductionBusCompositeIntegrationVerified` remains
`NotEstablished`. Original-ROM execution, native rejoin, target BIN/object/HEX,
firmware output, GUI and hardware remain absent. `FirmwareReady=false`.
The upstream M2bj 51-byte identity remains
`91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1`;
it is not production execution authority.

This document specifies the experiment, not a runtime PASS. The final private
report, written only after evidence sealing, records the actual outcome.
