# M2v — bounded native DATA0136 technical producer

M2v adds `data0136TechnicalProducer`, runner **0.29.0**, and the read-only
`research p28-fuel data0136-producer-check` command. Both writer paths execute
actual admitted ROM instructions on one persistent CPU/RAM per scratch sequence.
C# independently owns initial RAM, declared sources, arithmetic, flags, instruction
control flow, ordered reads/writes, and generation history. Rust outputs never
become expected model inputs. This is software-storage/test-domain evidence,
not physical engine reachability or a recovered ECU service.

## Entry and natural boundary

`TechnicalSeededEntry56BE`: PC56BE, LRB0021/local bank0108, SCB2, USP0280,
technical PSW1102 and unused SSP07FE. Entry resets only that declared technical
ABI; accumulator, other pointing registers and native RAM persist. The first
word load establishes DD and ZF. CF is overwritten before each carry-dependent
producer decision/arithmetic; HC and MIE have no input-dependent use in this
bounded path. Incoming A is overwritten by the first instruction. These facts
justify the technical seed, **not** caller/ISR/scheduler recovery.

Both modes naturally reach **stop-before5719**. No replacement instruction,
forced continuation, full tail5801, CAL/RTI frame, timer evolution, or interrupt
delivery is introduced. ProducerTo2330SchedulerSeam = **NotEstablished**.

## Frozen sources and persistent state

Every invocation must actually read TMR2/003A as a word first, including no-write
and mode1 paths. IRQH/0019 byte is read only when the selected sample bit15 is
clear. TCON2/0042 byte is read only on the mode0 write path. Reads preserve their
frozen snapshots, advance no time, create no interrupt and imply no simultaneous
physical state. Wrong widths, unknown SFRs and peripheral writes fault; there
is no default-zero/generic SFR RAM.

Mode0 selects the actual TMR2 word. Mode1 subsequently selects explicit word
`source00f0`, classified **RawSoftwareSnapshot / UpstreamProducerNotRun**. Its
upstream hardware-capture producer is outside this stage. Each application is
reported separately from native RAM journals. Slot00A2 is explicit technical
caller input0..5. Mode011F.2 is chosen once initially, never switched per event.

Previous00EE, byte00AE,00B6,011F,0128,0136, sample words0360..036A and native
register/pointer writes persist. Initial `history0136` is canary/history only.
No event can supply ready0136, quotient, dividend, result, writer, branch, flags,
PC, arbitrary RAM or formula. A closed version1 scenario has purpose
`data0136-native-technical-producer-test`,1..256 dense observations and at most8
requested trace indexes. Bounded per-instruction evidence is always collected;
requested indexes do not suppress mandatory validation evidence.

## Native writer mechanics

Prior0128.3 clear: SB sets the bit and derives ZF from its **previous** value;
JEQ skips both writers, retains0136 and still updates previous00EE/clears00AE.
Prior0128.3 set admits the writer path. No code in this bounded slice clears
that gate. Therefore native writer-event N -> no-writer-event N+1 is
**NotReachableWithinBoundedSlice** under the admitted persistent contract.
There is no hidden gate reseed or invented service to manufacture that witness.
Generic invented journal tests cover writer->Held retention separately.

Let S be the selected word, P prior00EE, C the byte counter after conditional
IRQH.0 increment (modulo256, only S.bit15 clear). Native arithmetic and the own
model agree on these storage-domain projections:

| Mode | Writer | Projection and same-routine consumption |
|---|---|---|
|011F.2 clear|5707, word0136|Wrapped S-P unless TCON2.2 forces0. EqualDeltaZero and ControlForcedZero remain distinct. Native reader570E reads that same generation, then the selected sample slot is written.|
|011F.2 set|56F3, word0136|Upper byte=(C-borrow) modulo256; unsigned dividend=upper*65536+wrapped(S-P), divided by fixed immediate6. Fitting quotient retained; larger quotient explicitly cleared/stored0: **OverflowToZero**, not saturation. All six sample slots are filled, descending; SJ bypasses570E.|

Immediate6 is a **CodeOwnedConstant**, not calibration/table/editor/export data.
The two writer sites are mutually exclusive within one invocation, including
when their values happen to match. Reader5782/5787 and downstream2330 are **NotRun**.

Each validated writer records PC, exact instruction bytes/form, address0136,
width16, old/new word, event index, zero-based native write order and generation
tuple `(writerPC,eventIndex,writeOrder,value)`. Same-value stores create new
generations. A no-store invocation is Held, never a fresh produced word.
A terminal suffix retains completed stores as PartialNativeWritten; completed
producer result is null. Subsequent observations are NotRun and apply no sources.

## ISA and historical separation

New forms are separately admitted; historical acquisition admission is unchanged.
Failing invented decoded regressions and primary visual review established two
narrow HC fixes: `byte-sbc-r0-immediate-half-borrow` (r0/immediate only) and
`word-decrement-x1-half-borrow` (X1 only). No unrelated SBC/SUBB,47 81,45 81,
M2i or M2t JGT admission is implied. Identity validation accepts0.29.0 with its
exact inventory while preserving older version inventories/capabilities.

Historical M1i remains **mode0-only** and refuses mode1 before fetch. Equivalent
mode0 state/observations are compared explicitly against M1i for peripheral reads,
00EE/0136/sample stores, gate and counter history. Old protected reports remain
byte-identical. M2u remains historical Research/Partial/ProducerNotRun; M2s Partial;
M2t Blocked/Partial; JGT unresolved. No producer->forced PC22B1->2330 integration.

## CLI and readiness

```text
hondaecu research p28-fuel data0136-producer-check <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --runner <runner-0.29.0> --scenario <m2v-scenario.json>
  --output <new-private-report.json>
```

All inputs are snapshotted/checked before and after execution. Outputs must be
new and cannot alias an input. No firmware children, BIN, binding, compensation,
export plan/receipt/token or GUI/hardware action. Public regressions contain only
invented ISA/program probes, model-only boundaries and fabricated protocol guard
evidence, never OEM byte fixtures. Private native corpus is original-only.

PcInspectionOnly / NotFlashReady; physicalRpmAvailable=false; physical fuel/time/
degrees unavailable. Strict M2i Blocked; quartet consumer NotRun; GUI r3 paused/
NotRun; D1/D2 interactive acceptance NotRun; hardware/full boot NotRun. Headless
Desktop tests do not constitute GUI acceptance. M2w is not started automatically.
