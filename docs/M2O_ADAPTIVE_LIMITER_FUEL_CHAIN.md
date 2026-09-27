# M2o — native adaptive thresholds to fuel-store gate

M2o is bounded read-only software research. Runner **0.23.0**, protocol1,
pinned Rust1.85.1, adds `adaptiveLimiterFuelGateChain` and:

```text
hondaecu research p28-fuel adaptive-limiter-chain-check <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --runner <runner-0.23.0> --scenario <m2o-scenario.json>
  --output <new-private-report.json>
```

The original and binding must already match. Outputs are immutable private
JSON evidence, never a firmware image or export authority. Historical M1m,
M2n and M2m commands retain their contracts; their results are not inputs to M2o.

## One machine and three native dependencies

One CPU/RAM is initialized once per image/scratch sequence. This explicit test
schedule is **not** a recovered ECU main loop or continuous flow between routines:

1. Apply the single raw/source snapshot.
2. Call native5BD0..5BD9 for01D5, then01CE, with the owned X1 arguments.
3. Execute adaptive487B..48F5, including native5AB8/5AC2 helpers.
4. Execute decision-only1966..1A38 with frozen P4.0=0.
5. Execute established native axes/selection/lookup0140 and factor0158.
6. Continue through actual217A, correction/scaling/application,21F5 and
   software stores03A2/03B4; stop before2204.

No inputs are applied between producer and consumers. Existing execute-in-state
components are reused, not old top-level tasks on a second machine. The old
5585..5596 mask consumer is not executed or modeled;018F/012A/P2 are out of scope.

| Storage | Ownership and dependency |
| --- | --- |
| RAM01A4/01A6 | Native producer stores, then actual limiter word reads1977/1974 |
|0124 | Previous request history; native decision clearsbit4 and writesbit5; actual217A/21F5 read it |
|012B | Limiterbit7 plus additivebit3 share one persistent byte |
|01D5/01CE | Native counter service and producer; no host decrement |
|01D7 | Existing limiter side effects only; no added tick |
|0130.6 | Independent native factor history, retained across bank/source changes |
|0140/0158 | Native stores actually read at21DB/21DD before numeric application |
|03A2/03B4 | Separately validated final software stores |

03A2 can be zero due to a gate or due to arithmetic. A zero alone is not a
limiter witness.03B4 remains the positive numeric control in the gate A/B
witnesses; neither store proves electrical injector operation.

## Base, current RAM and compared threshold

Program base words, current RAM pair and selected comparison operand are
distinct. Bank021F.1 changes actual table addresses, even when original values
match. Reset217 has priority over reset214 and a live timer. Reset214 preserves
counters. Nonzero01D5 holds RAM; bank switching during hold retains the prior
bank's generation rather than replacing it with new bases.

Decrease uses borrow on previous−37 and otherwise floors at the base.
Adaptive uses saturated previous+24 as a bound, unsigned high-word multiplication,
and **modulo65536** base+high target; `min(target,bound)` can decrease RAM.
No saturation substitutes for target addition.

Every actual pair store, including a same-value store, is `Written` and creates
an event generation. A no-store hold is `Held` with its retained writer index.
A hold before any native writer is `InitialHistory`, not production evidence.
Incomplete production is `NotRun` provenance, never completed Held; downstream
request/stores are null/NotRun and all later events are terminal without inputs.

The main source is masked011B.7=0 (RAM). Fixed011B.7=1 is an explicit control,
not a second map/context input. Fixed immediates are fetched on the RAM path,
but fetch is not comparison provenance. Prior0124.5 selects cut versus resume.
Fixed source can coexist with native RAM updates; those updates are not erased.

## Snapshots, ABI and strict evidence

The closed version1 scenario accepts one authoritative initialState,1..64 dense
calls, at most32 combined ticks per call, at most8 trace witnesses and bounded
provenance. Calls contain rawPeriod00C4,raw00CE,rawD9, existing M2m sources and
six Boolean masks:021F.1,0217.5,0214.0,0212.5,0223.2,011B.7. Neighbor bits are
preserved. No call can supply current thresholds, request, gate,0140,0158,
correction, result, channel mask, PC, arbitrary RAM or formulas.

00CE is not01CE;00C4 is not01C4;0212.5 is not012C.4;021F.1 is not0127.1.
These are raw software stimuli, without temperature/speed/RPM assignments.
Tick count means native calls, not milliseconds or ECU cadence.

Producer/tick use LRB0041, bank0208..020F and USP0180; limiter/fuel retain their
own ABIs. Register contents are never copied between banks. Access-capability
changes preserve RAM, IE and stack. The word-only software IE model validates
native mask/store/restore and MIE transitions, without IRQ/preemption or hardware
reserved-bit claims. Actual CAL/RT return PCs and alternating07FE stack accesses
are checked without helper stack reseeding.

C# keeps its own ROM bytes and persistent adaptive/decision/fuel history.
No Rust threshold or request is fed back as expected input. Validation covers
actual table reads (including odd word addresses), branches, arithmetic,
ordered writes, mask preservation, critical section, stack, RAM reads, comparison
operands/flags, both gates and both stores. Correct final numbers cannot replace
missing producer provenance. Partial native observations remain diagnostic.

The outer M2o contract defines the combined schedule/context. Embedded historical
M1m/M2n contracts identify reused body metadata; their standalone schedule and
fixed-only exclusions are not the outer operation's schedule. Strict assumptions
are empty.47 81,45 81 and SUBB permissions are not promoted by analogy.

## One-word A/B and coverage

Only four code-owned choices exist: bank0-cut/resume, bank1-cut/resume. Mapping
comes from the inspector:649B/649C,6495/6496,64A7/64A8,64A1/64A2. Each B is
independent of the exact original; a nonzero change of at most8 raw counts must
retain an ordered non-endpoint pair. Full image diff permits only that word.
Origins, coefficients (especially64A9/64AA), selector/code, fixed operands and
fuel cells are unchanged. There is no general-offset mutation API or exporter.

The native witness is changed base read → changed RAM generation → changed
comparison/request → actual21F5 branch →03A2 effect with unchanged positive03B4.
Unchanged-bank controls start independent clean histories. A bank used after an
edited bank may legitimately inherit different RAM; histories are not normalized.

Private delivery evidence covers both banks, both fuel maps, both prior requests,
reset priority, timer hold/expiry and zero ticks, decrease borrow/floor/equality,
adaptive bound overflow and target decrease, fixed↔RAM histories, initial hold,
numeric zero with clear gate, and cut-only/resume-only A/B. Native events, ticks,
A/B comparisons, witnesses, model-only audits and legacy compatibility are reported
separately in `private/reports/m2o/FINAL_REPORT_UK.md`; development reruns and old
corpora are excluded from delivery totals. Public fixtures use invented code/data,
including complete table→RAM→comparison→gate→two-store probes, partial-pair failure,
forged provenance and process cancellation/timeout tests; no OEM helpers are copied.

## Delivery limits

Release QA includes Rust build/test/fmt and both .NET solutions build/test/format,
privacy and previous private/definition/portable preservation. Exact-final-commit
CI is separate from local/private native evidence; no private ROM or trace goes
to CI. Firmware BIN, compensation, bindings, export plans/receipts/tokens: **0**.

PcInspectionOnly / NotFlashReady; physicalRpmAvailable=false. Physical fuel/time/
degrees, scheduler/IRQ/boot/engine, hardware, upstream acquisition/G/F, ignition/
VTEC/shared-M2h integration are not established. Strict M2i remains Blocked on
47 81. GUI r3 is paused/NotRun; D1/D2 interactive acceptance and hardware/full
boot remain NotRun. No GUI/Computer Use or next stage starts automatically.
