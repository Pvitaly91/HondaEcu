# M2y: native consumerWord0196 scheduled software handoff

Part A validates native M2x05EB generation to an actual54FA word read and bounded
software continuation on the **same Cpu/Bus**. Part B timer continuation is NotRun.
This is PC inspection, not a recovered ECU scheduler, measured timing or physical output.
Base: M2x6f5b8f5e545b26f7bb5ddfc3c434db683137fdfb. Separate operation
`word0196ConsumerHandoff`, runner0.32.0, scenario version1/purpose
`word0196-scheduled-consumer-test`. Historical `quartetConsumerHandoff` retains
technical0584, native05EB store and stop-before05ED; no old operation gains scope.

## Source, entry and live-ins

The unchanged matching private ROM/listing and primary MSM66201 ISA were rechecked
before implementation. Explicit0196 word writers:05EB and1553. Explicit readers:
157E(word L),54FA(word L),5578(word CMP).0197 is the high-byte overlap. No explicit
0197 byte operand was found, but indirect/indexed/stack/reset aliases remain
unresolved outside admitted ranges: this is NOT a global uniqueness assertion.
off96 addresses0196 only for the established0100 current page, not all LRB values.

Call063B genuinely targets54F5 (LRB0021/local0108); call1582 genuinely targets
secondary54F8 (LRB0020/local0100). Their earlier timer/IRQ paths do not run.
Choose earliest coherent54F5. Harness transition journals **PC only**05ED→54F5.
A,PSW/CF/ZF/HC/DD/SCB2,LRB0021,X1/X2/DP/USP,SSP7FE and all RAM are retained.
Native MOVB establishesr0; word L establishesA/DD1/ZF; ST establisheser1;
CMPB establishesCF/ZF while preservingHC/DD; JNE consumesZF. No pointer seed,
fake CAL/RT frame, return PC or IRQ frame. `TechnicalEntryDoesNotClaimCallFrame`.

| PC | Exact admitted form | Software effect |
| --- | --- | --- |
| 54F5 | JBR off N8.2,rel8 | byte gate0128.2; flags unchanged |
| 54F8 | MOVB r0,#N8 | native byte0108=FF; flags unchanged |
| 54FA | L A,off N8 | actual16-bit0196 read; DD1/ZF |
| 54FC | ST A,er1 | actual16-bit010A/B store; flags unchanged |
| 54FD | CMPB off N'8,#N8 | byte0117 vs immediate0F; CF/ZF only |
| 5501 | JNE rel8 | ZF0 branch; flags unchanged |

Primary visual ISA review covers each encoding, width, addressing, DD and flags;
no mnemonic-wide permission, semantic fix,4781/4581,JGT or unrelated SUBB promotion.
Code range54F5..5503 exclusive, budget6.0128.2=true and0117=0F reaches strict
stop-before5503. Gatefalse stops at5533 before unadmitted pure alternate;0117!=0F
stops at556F before unadmitted pure continuation. Both are terminalPartial,
NOT hardware-boundary completion. No admitted postread pure instruction is skipped.

## Source ownership, machine and generations

Scenario reuses M2x sources/calls. ONLY new sources: once-initial masked software
bit0128.2 (neighbor bits retained) and raw software byte0117. Existing prefix has
no overlapping owner. Earlier software writers are static-only:0128 bit operations
and masked writes including03D9/0524/0541/056B/0643/7AC4, USP-relative overlap411E;
0117 TRB05F2, USP-relative STB27F5/423F, later5582/55C1. No per-event source reseed.
No ready0196,54FAvalue,expected flags/branch,arbitraryRAM,timer,00C0,P2 or formula.

M2x execute-in-state is reused, not run as a subprocess. Initialization happens
once per scratch sequence; no second machine, JSON execution transfer, host0196
copy or intermediate setter. Journals cover all native M2r quartet stores,
M2x05DF/05E2/05EB and M2y software accesses. Canaries and persistent SCB/local
histories are checked, including native r0/er1 across events. Diagnostic reads
observe both incoming SCB banks after partial prefixes; this is not a native ABI write.

G0196=(writerPC05EB,eventIndex,zero-based ordinal among ALL native event writes,value).
Strict requires actual word writer, NO overlapping0196/0197 writer before54FA,
actual word read0196 with the current sameG. Equal values do not merge identities.
`QuartetDerived0196` requires independently proved05DF selected quartet read.
`ConsumerGateBypass0196` proves consumer mechanics only, not quartet-derived causality.
C# independently executes the existing M2x model/history and derives the expected
0196 value/generation before validating downstream events, flags, RAM and full journal.
Rust's result is never an expected numeric source. Validation JSON projections are
not execution handoffs. Partial is terminal; subsequent input/source applications are NotRun.

## Timer, comparison and later boundaries

5503 is16-bit **READ TM0 at SFR0030/0031**.5505 subtracts immediate1;
5508 is16-bit **WRITE TMR0 at SFR0032/0033**, not a second timer read.
Available primary instruction manual establishes encoding, not peripheral side effects.
No matching primary MSM66201 user/peripheral manual establishes latch/read-clear,
read order/same instant, reset or IRQ interaction. Those remain Unknown. Part BNotRun;
there are NO frozen timer observations, no clock advance, no default-zero hardware,
and no added timer write permission. A read-only snapshot would not justify5508write.

5578 compares LEFT RAMword0196 with RIGHT **immediate constant00C0**. It does NOT
read RAM00C0/00C1: no softwareWord00C0 source/producer is required or permitted.
It changesCF/ZF, preservesHC/DD;557D JLT consumesCF. Static-only/count0.
5501 can branch556F around the timer; therefore not every theoretical5578 path
requires5503. That software alternate is unadmitted, not automatic Part B evidence.

After5503, DP reads/writes0190/0192/0194 and helperCAL5699 precede later branches.
Gatefalse alternate reachesRT553F, requiring a real return frame outside this slice.
P2 first access is read-modify-write byte SFR0024 at5596 or55C5 on another branch;
laterTRNSIT/TCON0/TM0/TMR0/PSWH/IRQ/return dependencies remain static-only.
P2NotRun/PhysicalOutputNotRun: no frozenP2, mock port, zero default or write sink.
157E remains `StaticOther0196Consumer/NotRun`: replacement1553 generation,
TM0/IRQ1562/1567 and TMR0 dependencies; no PC157E jump.

## Focused actual coverage

51 A/B scratch checkpoints:45 originalA and6 one-cell in-memoryB; no firmware output.
39 fresh native05EB generations;36 same-generation54FA reads;27 quartet-derived
strict (A21/B6),6 gate-bypass strict;33 software completions/5503boundary stops.
Per-slot quartet-derived handoffs:slot0=12,slot1=9,slot2=3,slot3=3.
18 consecutive fresh equal-value generation pairs;6 fuel-cell→0140→03B4→quartet→
05DF→0196→54FA divergence witnesses. Native er1 store divergence separately6.
6 consumerPartial (3 gate/no read,3 alternate/read),3 NoFresh0196,9 NotRun.
Frozen timer/5578/P2 executions=0. Hardware timer evidence blocked; Part BNotRun.
Old M2x123 writes are NOT added. Compatibility and invented/model-only tests are separate.

Public tests contain invented decoded programs/model observations only. Negative
checks reject stale equal-value IDs, wrong address/width/value/ordinal, overlap,
host copy/second machine, hidden A/pointers/PSW/frame, skipped instructions,
unobserved/default/changed timer, P2 and fake physical-time fields. Actual evidence
forgeries stay private.13 historical execution comparisons against0.31.0 retain
identical output except disclosed version and identical semantic-fix inventory;
M2u has no executable operation and its static artifacts remain protected.

## Read-only CLI and classifications

```text
hondaecu research p28-fuel word0196-consumer-check <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --runner <runner-0.32.0> --scenario <m2y-scenario.json>
  --output <new-private-report.json>
```

Exact binding, closed inputs, protected new output and before/after input snapshots;
no export/firmware option. CLI success for strict software cases; exit3 for partial.
Word0196TechnicalConsumer/Word0196ScheduledHandoff=Validated in strict focused cases.
Gate-bypass technicalValidated/scheduledPartial. InterStageSchedulingExplicitHarnessSchedule;
Recovered0196SchedulerNotEstablished;SkippedCodeNotExecuted;IRQNotInjected;
ElapsedTimeNone;Physical0196RoleUnknown. M2x/M2w validated unchanged;M2tJGTBlocked;
strictM2iBlocked;physicalRpmfalse,physicalfuel/time/degrees unavailable;
GUIr3paused/NotRun,D1/D2interactive/hardware/fullbootNotRun;BIN0;
PcInspectionOnly/NotFlashReady. Do not start M2z/P2/157E/IRQ/JGT/GUI/hardware automatically.
