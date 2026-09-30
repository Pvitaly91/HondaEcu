# M2p native post-store fuel continuation

Read-only software research, runner0.24.0, strict operation `fuelPostStoreChain`.
PcInspectionOnly / NotFlashReady. Physical RPM/fuel/time/degrees unavailable.
Strict M2i remains Blocked on47 81. GUI r3 paused/NotRun; D1/D2 interactive
acceptance, hardware and full boot NotRun. No firmware BIN, exporters, writable
calibrations, compensation, bindings, receipts or tokens are created.

## Smallest completed software result

M2o still ends before2204, after the actual2203 word store03B4. M2p continues
on that very CPU/RAM to stop-before223B. The completed result is the native word
store0150 at2239, neutrally named `postStoreWord0150`. The next static reader is
the word comparison223D, after223B loads014C. That downstream selection,012C.5,
helper5991 and interrupt/per-channel consumers are NotEvaluated here.

This is not an established pulse duration, physical injector command, AFR,
delivered fuel, acceleration sensor or feedback controller.

## Native flow and exact arithmetic

2204 tests0125.4;2207 tests012E.4. Either set bit selects the zero path221F.
220A compares unsigned byte0133 with160; greater/equal also selects zero.
2210 compares word014C with zero; nonzero selects zero. Only otherwise does
2217 subtract previous er0 from current A, unsigned16 with modulo65536 result,
CF on borrow, ZF and bit3 half-borrow HC.2218 consumes CF and selects zero
on a decrease.221A compares the remaining difference with250; values below250
produce zero, including repeated equal current/previous values.

For a difference at least250,2222 clobbers er0 with2000.2226/2227 compare;
2229 replaces er0 with the smaller difference.222A clears A;222B writes only
CPU ACCH alias0007 to80, producing A8000 without changing flags/DD.
222F performs unsigned16x16 MUL: er1 holds high16, A low16, ZF from full product.
2231 shifts A left once, changing only CF;2232 loads er1, sets DD/ZF and retains
CF;2233 rotates A left through carry, changing only CF. Together they reconstruct
`min(difference,2000)` exactly, including odd values, with no floating point.
2234's overflow branch to2236 is statically present but unreachable under the
native2000 bound; it is not claimed as dynamic coverage.2239 stores word0150.

Thus output is zero for any early gate, unsigned decrease, or rise below250;
otherwise it is the unsigned rise bounded at2000. Gate zero, numeric application
zero, difference zero and unexecuted/null result are separately reported.

## Lifetime and ownership

| Field/carrier | Writer and reader | Policy |
|---|---|---|
| RAM03B4 before2203 | prior native2203, then word load2201 | once-only declared InitialHistory for first event; native history thereafter |
| er0 at2204 | native2201; read2217 conditionally | previous generation, not current RAM; clobbered2222/2229 only after consumption |
| RAM03B4 after2203 | native2203 | current generation; no suffix read/write before223B; closest later static word reader229F excluded |
| A/er3 at2204 |21FD/current corrected carrier | A consumed by suffix; er3 retained, not read |
| er2/X2 | scaling/component and correction | retained, not consumed in this suffix |
| er1 | prefix MUL/scaling; suffix222F if reached | native high product clobber, not a reseed |
| DP/X1/USP/LRB/SSP | existing prefix | retained throughout suffix; no enter, copied bank or reset |
|03A2 |21F5 gate then native21FC | gated prefix result, not a suffix input |
|0124/012B/0130.6 | native limiter/additive/factor | existing shared persistent ownership; no new setter |
|01A4/01A6/counters/IE | adaptive/tick fragments | existing Written/Held/InitialHistory contract |
|0140/0158 | native lookup/factor producer | no per-event ready-value input |
|0125.4/012E.4 | external software upstream11FB/121E and18A5 | two masked snapshots before all ticks/prefix; neighboring bits retained |
|0133/014C | existing audited M2o software sources | same single snapshot, reused by prefix and suffix; not sensors |
|0150 | native2239 | code-owned zero initial storage once; native writes thereafter, no host refresh |

Equal old/current values still require the native load2201 and store2203.
Different er0/current RAM is not corruption. All exact PC/width/value reads,
ordered native writes, full2204 state and per-instruction suffix flags are checked.
The suffix creates no conflict with old M2o setters: it only newly owns0150.

## Execution, model and failure

One initialization, one CPU/RAM per image/sequence/scratch. Raw snapshots are
applied once before native ticks. Existing producer/decision/axis/factor entries
remain explicitly scripted software ABI entries, not a recovered ECU scheduler.
The217A to2194 to2204 to223B part is continuous: no enter/reset, A/register reload,
JSON state transfer or repeated stores at2204. Pure reusable execution components
serve both tasks; the historical M2o operation/schema/stop2204 are unchanged.

C# owns ROM bytes, adaptive state, caches, combined mode, factor/hysteresis,
corrected output and previous03B4 history independently for every A/B image.
Rust old/current values never become expected operands. Expected per-PC events
include borrow/carry/half-carry, ACCH alias, MUL high/low, shifts and ordered writes.
The model-only finite storage audit is not native reachability.

If suffix execution fails, successful prefix stores remain observations; partial
native writes are not rolled back. Completed suffix output is null, whole event
is not Pass, and later snapshots/ticks/events are NotRun. Selected traces are
limited to8; required proof journals remain bounded and are never silently cut.

Original60E5 and60F8 remain zero. The nearest local result completes before any
new IO/IRQ access. The later226F load/2273 branch bypasses optional per-channel
readers including227A when60F8=0; this is a static excluded path, not dynamic
execution or permission to set PC227A.

## CLI and narrow A/B

```text
hondaecu research p28-fuel post-store-chain-check <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --runner <runner-0.24.0> --scenario <m2p-scenario.json>
  --output <new-private-report.json>
```

Scenario version1/purpose `post-store-fuel-native-software-test`: bounded provenance,
one initialState containing the established adaptive initial state and declared
previous03B4,1..64 dense calls, at most32 combined native ticks/event and8 traces.
Each call nests the established adaptive call plus two boolean source masks.
No arbitrary PC/RAM, expressions, produced request, factor, correction or output.
Exact binding, immutable snapshots/rechecks, new-output/alias guards and existing
bounded subprocess cancellation are reused.

Optional closed one-field mutation is a primary fuel cell (small raw-u8 change
of at most8) or one existing adaptive base word (old narrow bounds, at most8).
Every B starts from its own original copy. Code/config/axes/metadata coefficients,
other bytes and combined cell+word mutations are refused. The old M2o word guard
is not relaxed.

Focused original experiments include both map contexts, repeated/rising/falling
native corrected values,249/250 and1999/2000/2001 boundaries, new gates, numeric
zero, cut/release, reset/update/hold and fixed/RAM transitions. Cell A/B has
unmasked0150 witnesses plus gate-masked and unread-cell controls. Adaptive base
A/B can change request/03A2 while leaving0150 unchanged because the suffix consumes
ungated corrected A, not03A2. No influence from unread er2/X2 is invented.

Separate old M2o controls compare the prefix boundary2204, not post-suffix state.
Old scratch initial03B4 differs from the newly declared initial history on55/AA
first events; all subsequent native generations can match without reseeding.
Old corpora, compatibility invocations and model-only counts are not added to
new native coverage. Primary ISA review, local/CI QA and preservation details
are recorded privately under `private/reports/m2p/`.
