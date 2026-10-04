# M2x — native quartet consumer and explicit scheduled handoff

`quartetConsumerHandoff`, runner0.31.0, is a separate bounded operation. It
executes the existing M2r-producing prefix and the consumer on ONE Cpu/Bus per
scratch sequence. QuartetTechnicalConsumer=Validated and
QuartetScheduledHandoff=Validated for the focused original/in-memory A/B corpus.
RecoveredQuartetScheduler=NotEstablished; InterStageScheduling=ExplicitHarnessSchedule;
SkippedCode=NotExecuted; IRQDelivery=NotInjected; PendingInterrupt=NotModeled;
ElapsedTime=None; PhysicalQuartetRole/PhysicalChannelRole=Unknown.

## Entry, sources and native storage

The coherent entry is0584, not05DF. Earlier callers belong to IRQ-domain paths
with ADCR/timer/port dependencies. M2x does not execute those callers or deliver
an IRQ. Classification: TechnicalSeededQuartetConsumerEntry. After the unchanged
M2r stop-before22B1, the harness journals ONLY PC0584, canonical PSW1DCA and
LRB0021. PSW fixed bits0CC8 are explicitly represented. No A/X1/X2/DP/erN/USP
seed, RAM reset, second execution machine, serialization handoff or IRQ frame.
SSP remains7FE and is unused; no CAL/RT/RTI in the admitted consumer.
SCB1 bank0088..008F and SCB2 bank0090..0097 are distinct retained storage, not
copied pointer registers. Local banks0100 and0108 also remain distinct.

The closed/version1 scenario contains the existing fuel initial state/calls,
one once-initial masked raw software history bit012A.1, and a per-event
`selector013c` byte restricted to0..3. The selector is applied once before an
executed consumer; SelectorProducer=NotRun, RawSoftwareSnapshot. There are no
ready quartet,0196, X1, address, selected value, sum, PC, branch or arbitrary
RAM inputs.0124 and0125 retain their historical prefix owners. A completed
admitted limiter prefix clears0124.4; its true consumer branch is model-only,
not a new source setter.012A neighbors are preserved.

Explicit013C writers are03D7 (zero),0551 (preceding bounded0/1/2 paths),064A and
15A0 (byte increment then AND3). Reads include0567,0573,0584,05ED,063E,159A and
USP-relative4212/4249. No explicit bit writer was found. Reset sweeps and generic
indirect/indexed/stack aliases elsewhere remain Unknown: no global uniqueness
or whole-ROM0..3 guarantee. The admitted domain is a safe technical snapshot
domain. The bounded consumer does not advance013C; updaters remain NotRun.

LB reads013C/DD0; one SLLB shifts AL; EXTND sign-extends shifted AL and setsDD1;
MOV X1 writes the actual SCB2 pointer. Word accesses are even/little-endian.

| selector013c | Native X1 | Selected quartet word | Indexed companion word |
| --- | --- | --- | --- |
| 0 | 0 | 03B6 | 03BE |
| 1 | 2 | 03B8 | 03C0 |
| 2 | 4 | 03BA | 03C2 |
| 3 | 6 | 03BC | 03C4 |

Outside-domain values are refused, not host-forced: raw40 would shift80 and
sign-extendFF80. No direct index input or unchecked pointer wrap is allowed.

M2r native writers22A5/22A8/22AB/22AE create four DISTINCT current-event
generations at03B6/03B8/03BA/03BC. Equal values never merge identities.
Each identity is `(writerPC,eventIndex,writeOrder,value)`: M2x writeOrder is the
zero-based ordinal among ALL event native writes, unlike the historical M2r
storage-only ordinal. Historical reports/contracts are unchanged.
Correct number from a wrong slot fails: actual equal quartet values cannot
numerically distinguish slots, so coverage uses effective ADDRESS provenance.

On the admitted false0125.4 branch, native CLR/MOV X2 establishes zero and FOUR
native stores058E/0591/0594/0597 reset companion words03BE/03C0/03C2/03C4.
That proves four entries, stride2 and same-index selection; no companion
snapshot is necessary.019D/019F are cleared and RB019B.0 preserves neighbors.
The alternate05D2 companion writer belongs to the excluded05AF path; other
whole-ROM aliases remain Unknown.

05DF reads ONE selected16-bit quartet word.05E2 performs unsigned16 ADD with
the same-index companion; CF is full carry, ZF is intermediate zero, HC is
bit3 carry.05E6 JGE uses CF0; overflow loadsFFFF at05E8 before native word store
05EB→0196. Native reset companions are zero in actual admitted executions, so
nonzero companions/saturation are invented/model-only coverage. `consumerWord0196`
is a neutral software result, not a physical quantity.

## Completion, histories and independent validation

Stop-before05ED is the coherent result boundary. The following subsystem has
timer/peripheral accesses; it is NotRun. Allowed code is0584..05A0,
05D5..05ED and7DEF..7DF4 (exclusive ends).0125.4=true reaches stop-before05AF
and ConsumerPartial, without admitting alternate JGT05BB. It terminates the
sequence; later events are NotRun without source application or rollback.
Incomplete M2r means ConsumerNotRun. Gate-bypass produces a fresh native0196
but is ConsumerGateBypassNotHandoff, never quartet-reader evidence.

One producer event pairs with one consumer invocation. Native same-value0196
stores are fresh Written generations; retained initial/partial0196 is not a
fresh result. The validator checks independent M2r histories/03B4/quartet,
selector transform/X1, exact selected and companion addresses/widths, every
instruction/flag/access/write, exit, global chronology, overlap exclusion,
bank storage replay, canaries, ABI/source journals and native0196 generations.
Rust quartet/result observations never become expected model operands.

Focused corpus:135 A/B/scratch checkpoints;126 completed M2r prefixes;
123 completed technical consumers/native0196 writes;108 same-machine quartet
handoffs (address counts45/21/21/21);15 native gate-bypasses;3 ConsumerPartial;
9 later NotRun. Original-only subset:105 checkpoints,78 handoffs,93 native0196
writes, address counts33/15/15/15. The in-memory B subset is separate, not
unchanged-original coverage. Both map contexts cover all four slots. Repeated
equal-value events require fresh distinct event identities.

One-cell in-memory fuel A/B yields30 downstream0196 divergence witnesses across
the two map contexts and scratch patterns: fuel cell→0140→03B4→M2r common word→
four equal quartet stores→selected05DF→0196. No combined mutation or BIN is
written. Raw-period cut control leaves this quartet/result unchanged; optional
adaptive-cell mutation was not run. Invented fixtures use differentiated words,
equal words, companion arithmetic, sign-extension/overflow refusal, partials,
same-value/stale generations, schema/host/second-machine/IRQ-frame forgeries and
timeout/cancellation. Invented instruction bytes are not OEM windows or proof
of actual-ROM reachability.

Indexed ADD exposed stale HC. A failing invented decoded test preceded visual
primary manual3-13 proof and the minimal exact fix
`word-add-a-indexed-x1-half-carry`; no other ADD/SUBB/JGT/JLE form was promoted.
All mandatory new forms were visually checked against the primary manual.
Historical0.30 inventory remains unchanged; it refuses the M2x operation.
Compatibility checks cover M2w/v/t/s/r/q/p/o and M1i modes0/1, with only explicit
runnerVersion and the single added fix-identity metadata normalized. M2u static
evidence and all old private reports are protected by full hash preservation.
Compatibility is not new native M2x coverage. CI uses invented fixtures only.

Final local QA: all ten required commands passed with pinned Rust1.85.1 and
repository .NET8 (resolved SDK8.0.425). Exact passing totals: Rust244
(93 library unit tests plus151 integration tests), Core1262, CLI731,
Desktop183 headless tests; zero failures/skips. Both solution formatting
checks and `git diff --check` passed. The new invented regressions contribute
4 Rust,52 Core and14 CLI tests. Separately,25 private actual-evidence forgeries
were rejected; these are negative validation, not native coverage.

## Static next-reader audit and exclusions

0196 readers:54FA word load in54F8 (call063B to54F5, gated0128.2; call1582 to
54F8),5578 word CMP with00C0 in the same routine (word width independent of
listed DD0), and157E word load in a loop in the other producer path.5503/5508
TM0/TMR0 may intervene before5578; P2 at5596 follows.157E's path already has
TM0/IRQ at1562/1567. These are STATIC only; downstream consumer NotRun.
1550 is StaticOtherConsumer/NotRun: its caller first replaces quartet with
152C/152F/1532/1535 writes, so it cannot prove M2r-generation consumption.

M2r stop22B1 unchanged; historical M2s remainsPartial/dynamic quartet readers0;
M2wTechnicalScheduledHandoff=Validated for DATA0136 only; M2tJgt=Blocked/Unresolved.
No DATA0136 scheduling changes, full ECU cycle, P1/P2, IRQ scheduler recovery,
GUI, hardware, downstream0196 execution or automatic M2y.

Read-only command:

```text
hondaecu research p28-fuel quartet-consumer-check <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --runner <runner-0.31.0> --scenario <m2x-scenario.json>
  --output <new-private-report.json>
```

Exact admission and bounded snapshots are checked; aliases/existing outputs are
refused and inputs must remain unchanged. FirmwareBIN=0; binding/compensation/
export plan/receipt/token=0. PcInspectionOnly / NotFlashReady;
physicalRpmAvailable=false, physical fuel/time/degrees unavailable;
strict M2i Blocked; GUI r3 paused/NotRun; D1/D2 interactive acceptance NotRun;
hardware/full boot NotRun. Desktop verification is headless only.
