# M2aa — bounded P2 output-data latch handoff

The separate runner0.34.0 operation `p2OutputLatchHandoff` validates a CPU-visible
P2 output-data-register effect, not electrical output. The retained native chain
is M2r quartet → M2x05DF/05EB0196 → M2y54FA → M2z5578/557D → software
mask/state preparation → one P2 byte instruction. One Cpu/Bus is retained per
image/scratch sequence. A/B images and different scenarios are separate machines.
Historical M2z and M1l still stop BEFORE P2; their operations are not extended.

## Three independent admission authorities

Matching manufacturer MSM66201/207 user/peripheral scans establish P2 semantics;
the package filename does not replace the actual chip identity in the scans.
Table5-2 (printed66), P2 section5.5 (69–71), Fig5-8 and Table5-3 establish:

- P2 byte data register0024, P2IO0025, P2SF0026.
- P2IO bit1 means output, bit0 means input; reset00 is NOT all-output.
- In primary-port output mode, reads return the port DATA register, not pins.
  Writes update that register. Arithmetic RMW reads according to direction/mux
  selection, then writes data; it is NOT an unconditional latch-read rule.
- P2SF implemented bits3..7 select clock/HOLD/serial secondary functions. Clearing
  them selects primary port mode. Bits0..2 do not exist and read1; reset07 does
  not mean those secondary functions are enabled. P2 reset DATA is undefined.
- The P0/P1 external address/data bus is distinct from P2's secondary-function
  mux. Input/mixed-direction/secondary-function and electrical behavior are excluded.

The independent static ROM/listing audit establishes the reviewed configuration:
startup25A0 loads AL=FF;25AE writes P2=1F;25B2 writes P2IO=FF;25B4 clears P2SF.
Earlier MOVB/STB instructions preserve that AL. Startup259D clears PRPHF.
Direct runtime configuration references are comparisons, not writers. Relevant
indirect/indexed/stack candidates were retained conservatively: arbitrary aliases
outside admitted ranges remain unresolved. DP=0026 at3CE2 is a helper count with
X1=02CB, not a P2SF write. No whole-ROM uniqueness or actual boot claim is made.

Configuration is `ReviewedStartupPrecondition`: P2IO=FF, implemented P2SF bits0.
All admitted upstream data ranges exclude0024..0026. Direction/mux registers are
not runnable inputs or writable conveniences. Startup is NOT executed here;
no claim establishes the physical ECU's current mode. Reset-undefined DATA and
other runtime data writers rule out a supposedly authoritative startup latch1F.

Separately, the primary ISA ANDB/ORB obj,A instruction descriptions establish
byte AL source, byte RMW, DD independence, unchanged A, and ZF-only changes
(CF/HC/DD and remaining PSW bits preserved). ROM/listing verifies each exact
instruction and next boundary; the private audit retains bytes, not public OEM windows.

| Native branch | Instruction | Independently derived AL | Latch effect | Stop |
| --- | --- | --- | --- | --- |
|557D taken / BelowImmediate|55C5 ORB P2,A|0F, after55BF/55C1/55C3|old OR AL|55C8, before TCON0|
|557D not taken / Equal or Above|5596 ANDB P2,A|native018F OR F0, after5592/5594|old AND AL|5599, before TRNSIT|

Neither next instruction, RT/RTI, timer path5503/5508 nor any downstream continuation
is executed. P2 is reached by native5578/557D/software flow, never hostPC5596/55C5.

## Narrow capability, snapshots and provenance

Bus holds a separate persistent `P2OutputDataLatch`, not scratch RAM/P1/pins.
Byte0024 access is enabled only for that one native instruction and active native
observation. Wrong width,0025/0026/neighbor/unknown SFR and disabled access fault;
there is no generic SFR fallback. Word refusal is atomic. Historical P1/capture
logs remain separate and compatible. Latch inspection outside execution is
diagnostic only, not native readback evidence.

Closed/version1 purpose `p2-output-latch-handoff-test` reuses the M2z software
scenario and admits only one new top-level byte `p2OutputLatch`. This is
`RawArchitecturalP2LatchSnapshot;StartupProducerNotRun;OnceOnly`, an architectural
test domain, NOT actual startup, measured pins or engine state. No per-event
reseed, mask/result/pins/mode/PC/branch/arbitrary-RAM/timer input is admitted.

Each instruction produces a separate peripheral journal
`[PC,address,width,write,value]`: native read OLD, then native write NEW.
P2 is not counted as RAM access. The fresh write identity is
`(writerPC,eventIndex,zeroBasedAllNativeEventWriteOrder,value)`, including
same-value stores; its ordinal follows all native RAM writes in that event.
Next events consume retained latch/generation, including terminalPartial/NotRun
preservation. Initial source has no native generation.

C# independently owns all M2z history,0196 generation,5578 operands/flags/branch,
software A, incoming latch, instruction effect, outgoing latch and P2 generation.
Rust results never become expected inputs. Full CPU boundaries, one-machine
continuity, exact trace/extent, native RAM chronology and separate P2 read/write
order are checked. Same0196 generation must be read at54FA AND5578; overlapping
writers, correct number/wrong slot or stale equal-value IDs are rejected.

## Focused actual corpus and exclusions

New M2aa coverage is69 events (63 original A,6 in-memory child B),42 architectural
reads and42 writes:33 executions5596,9 executions55C5.39 quartet-derived strict
events are separate from3 upstream gate-bypass P2 controls.15 same-value stores
and15 native cross-event retained-latch reads are witnessed. Compare domains:
Below9 (including3 controls), Equal3, Above30. All four quartet ADDRESS slots
have strict provenance:24/9/3/3 events respectively. Partial12, NoFresh0196=3,
laterNotRun=12 are separate and do not contribute P2 accesses.

Native0196=191/192/193 comes from raw upstream source changes, NOT ready0196.
Initial latch domain00/FF/A5 is architectural testing only. Six one-cell in-memory
fuel A/B comparisons change the native upstream chain/0196 but produce zero P2
latch divergences: same branch, same software AL masks the changed upstream value.
Reports disclose0196,PC,AL,old/new for BOTH images, not physical divergence.
Historical M2z42 comparisons are not imported as new evidence.

Five new Rust invented tests,46 Core and20 CLI tests cover decoded producer→word
compare→branch→mask→RMW, both byte operations/flags/DD, same-value/retained state,
disabled/width/address/mode/host-write/second-machine refusal, closed schema,
old runner refusal, independent model output/generation forgeries and partial
read-only transport. Public CI uses invented fixtures only, no OEM routine windows,
ROM/manual/private reports. Private actual-evidence forgeries are negative
validation, not native coverage. No executor defect/new semantic fix was required.

Exact-base reconstructed0.33.0 and0.34.0 responses match except runnerVersion in
21 historical comparisons: M2z/y/x/w/v/t/s/r/q/p/o, M1l, acquisition modes0/1,
M1j P1 and M1k integrated P1. Fix inventory is unchanged. M2u's static evidence is
preserved, not falsely represented as a runnable compatibility operation.

## Read-only command and final scope

```text
hondaecu research p28-fuel p2-latch-check <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --runner <runner-0.34.0> --scenario <m2aa-scenario.json>
  --output <new-private-report.json>
```

Inputs are checked and unchanged; existing output/alias/unknown fields are refused.
No firmware write or hardware access. Full strict positives are Validated; incomplete
or control-only corpora remain Partial (CLI exit3). No trusted export authority.

P2ArchitecturalSemantics=EstablishedForReviewedAllOutputPrimaryPortPrecondition;
P2ArchitecturalLatchHandoff=Validated in strict focused cases;
P2ElectricalPins=NotModeled; PhysicalOutput/HardwareValidation=NotRun;
PhysicalP2Role/PhysicalPolarity/ChannelAssignment=Unknown.
TimerContinuation=NotRun; Recovered0196Scheduler=NotEstablished;
IRQDelivery=NotInjected; ElapsedTime=None. M2z/y/x/w validated bounds unchanged;
M2tJgt=Blocked/Unresolved; strictM2i=Blocked. FirmwareBIN/binding/compensation/
exportplan/receipt/token0; PcInspectionOnly / NotFlashReady;
physicalRpmAvailable=false; physical fuel/time/degrees unavailable.
GUIr3 paused/NotRun, D1/D2 interactive acceptance and hardware/fullboot NotRun.
No automatic next milestone, pin mapping, injector identity, timer/IRQ/JGT or GUI.
