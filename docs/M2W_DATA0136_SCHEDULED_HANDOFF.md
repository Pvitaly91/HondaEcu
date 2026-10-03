# M2w — Scheduled native DATA0136 producer-to-DIV handoff

`data0136DivisionHandoff`, runner **0.30.0**, is a separate bounded operation.
Under an explicit harness schedule, a native M2v DATA0136 generation survives
on the same CPU/RAM and is consumed by2330. This establishes a technical
scheduled handoff, not a recovered ECU scheduler or a physical period/fuel relation.

## One machine and explicit boundaries

Each scratch sequence creates one `Cpu` and one `Bus` before its first event.
The reusable M2v execute-in-existing-state primitive does not initialize RAM.
Historical `data0136TechnicalProducer` retains its own contract and stop-before5719;
its `ProducerTo2330SchedulerSeam` remains `NotEstablished`.

The new event pairs one declared producer observation with one fuel call:

```text
technical entry56BE -> native56F3(mode1) /5707(mode0) -> generation G
  -> explicit historical harness ABI schedule (skipped code NotExecuted)
  -> existing adaptive/fuel, M2p, M2q, M2r prefix ->22B1
  ->2327 ->232A current03B4 ->CAL5991 ->232E er0=0
  ->2330 word0136 read ->word er2 write
  -> positive:2333 word DIV ->2335 ->2337 CMP ->stop-before233A
  -> zero:stop-before2333; DIVNotRun /ZeroDivisorUnresolved
```

There is no continuous recovered ROM path from5719 to the fuel caller.
`InterStageScheduling=ExplicitHarnessSchedule`, `MainLoopRecovery=NotEstablished`.
Nested historical contracts and boundaries disclose PC, PSW, LRB and SCB-selected
USP entry assignments, plus tick X1 targets. A is retained, not assigned from an
observed producer output. SSP7FE is initialized once. PSW selects pointer storage:
producer SCB2 and fuel SCB1 do not require equal X1/X2/DP values when the selected
bank changes. The validator independently replays persistent SCB1 stores and
checks entry pointers; it never copies the SCB2 pointers into SCB1.

## Initial ownership and provenance

The closed version1 scenario purpose is `data0136-scheduled-division-handoff-test`.
It contains `unifiedInitialState`, paired dense `producerObservations`/`fuelCalls`
(1..64), provenance and `traceEventIndexes`. Observations use frozen TMR2/IRQH/
TCON2, a technical slot and mode1-only raw software `source00f0`. Mode is once initial.
These sources are not engine measurements; IRQ delivery is not injected and elapsed
time is None. Initial0136 is only the automatic scratch*257 diagnostic canary.

| Storage | Authoritative initial owner | Subsequent policy |
|---|---|---|
|00EE/00AE/00B6/0128/0360..036B|producer initial fields|native producer histories retained|
|00A2/00F0|declared observation slot/mode1 snapshot|applied only before an executed producer|
|011F|one full initial `data011f` byte|bit2 producer mode, bit5 common source, neighbors preserved; no later rewrite|
|0136/0137|internal scratch canary, never a JSON numerical input|native56F3/5707 store, downstream read-only|
|SCB2 pointers/local bank108|scratch and disclosed technical ABI|producer only; distinct from SCB1/banks100/200/208|
|SCB1 pointers/fuel histories|existing `fuelPrefix` initial state|historical native writes and disclosed ABI transitions|
|011A/0120/00B7/00BE/013B/013D|narrow established `softwareSources`|historical masked/native ownership; no ready divisor|
|0140/0158/0150/019x/03A2/03B4/quartet|existing code-owned canaries/history|native prefix/calculation writes; quartet consumer NotRun|

The old common-result initializer with a word0136 setter is never invoked in M2w.
All initialization precedes producer execution. The alias audit covers every
admitted prefix stage and pointer/bank/stack write domain; it is not a whole-ROM
alias exclusion. Dynamic proof uses an independent event-wide continuity journal
of all native data accesses and host RAM writes, with exact native stage order.
Historical leaf journals are independently checked, not replaced by final values.
CPU alias assignments are disclosed by their nested ABI boundary contracts.

Generation is literally `(writerPC,eventIndex,writeOrder,value)`. The independent
C# producer model computes the expected value and identity from declared sources;
its own state passes that expected generation into the historical calculation model.
No Rust output becomes a C# expected numerical input, and no serialization handoff,
second machine, ready0136 setter or downstream reseed is used in execution.

Strict witnesses require native word0136 store, no overlapping0136/0137 write of
any width before2330, actual word read2330, actual word0104/er2 write, and, for
positive values, actual word0104 divisor read2333 with no intervening overwrite.
Correct V with stale G is rejected. Same-value stores create new IDs.

## Fresh output and terminal semantics

Positive `NativeProducerPositiveToJgtBlock` and zero
`NativeProducerZeroToDivBoundary` may be Strict handoffs, never strict calculation
completion. They permit the next paired event on the same persistent machine.
No-writer completed producer events report `NoFreshProducerGeneration` and
`DownstreamNotRun`, preserving native effects; the next observation may continue.
Producer/prefix partial execution is terminal, retains completed stores, and leaves
all later events NotRun without applying their inputs. Overlapping generation
writes are refused, not hidden or attributed to the old generation.

## Evidence accounting

The original-only private corpus has11 scenarios/15 event designs, each with
scratch00/55/AA:45 producer events, **39 same-generation handoffs**.

| Category | Count |
|---|---:|
|mode0 /writer5707 ->2330|18 (12 positive,6 zero)|
|mode1 /writer56F3 ->2330|21 (12 positive,9 zero)|
|positive /stop-before233A|24|
|zero /stop-before2333|15|
|same-value new-generation second events|6|
|NoFreshProducerGeneration /downstream NotRun|6|
|intermediate0136 writers /producer partial /fuel-prefix partial|0 /0 /0|
|firmware A/B /new firmware child BIN|0 /0|

Mode0 covers delta/equality/control-zero/wrap/same-value and no-fresh-first.
Mode1 covers small positive/below-six/borrow clear/borrow set/overflow-zero/
same-value/no-fresh-first. Mode is never toggled; no gate clear manufactures Held.
These are storage-domain technical scenarios, not physical engine reachability.
Historical compatibility, fabricated guard/model tests and invented low-address
composition programs are separate categories and are not added to these counts.
Public CI fixtures contain invented programs and fabricated protocol guards only.

## Read-only CLI and compatibility

```text
hondaecu research p28-fuel data0136-handoff-check <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --runner <runner-0.30.0> --scenario <m2w-scenario.json>
  --output <new-private-report.json>
```

Old runner0.29.0 cannot claim M2w. The command refuses input aliases, existing output,
unknown fields/options and ready results. It writes only a fresh diagnostic report;
cancellation/timeout cannot publish an executed handoff or mutate inputs.
Reports separate producer/consumer generations, reader/er2/divisor values,
calculation disposition, final stop and schedule classification.

Old M2v, M2o/p/q/r/s/t and M1i mode0/mode1 outputs are checked against the retained
0.29.0 executable, byte-identical except the runnerVersion field. Historical M2u
static evidence/reports stay protected and ProducerNotRun. M2s remains Partial;
M2t remains Blocked/Partial, zero remains Unresolved and JGT semantics/admission
are unchanged. No JGT/JLE research or execution is added.

## Limits

`TechnicalScheduledHandoff=Validated`; `RecoveredEcuScheduler=NotEstablished`;
`ProducerTo2330SchedulerSeam=HarnessScheduled / NotRecovered`.
`IRQDelivery=NotInjected`; `ElapsedTime=None`; `M2tJgt=Blocked/Unresolved`;
`QuartetConsumer=NotRun`; `FirmwareBIN=0`.
PcInspectionOnly / NotFlashReady; physicalRpmAvailable=false; physical fuel/time/
degrees unavailable; strict M2i Blocked; GUI r3 paused/NotRun; D1/D2 interactive
acceptance NotRun; hardware/full boot NotRun. No05DF/1550/P1/P2/RTI extension,
binding/compensation/export plan/receipt/token, GUI or hardware work follows M2w.
