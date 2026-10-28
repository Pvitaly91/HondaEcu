# M2ce: rooted SSP047E and first RAM-test source obligations

Classification: **Research-Only / static obligations**.

Result: **CONDITIONAL_ROOT_TO_FIRST_CAL_OBLIGATIONS_REFINED / EXECUTION_BLOCKED**.
No CPU, original ROM, peripheral, GUI or hardware experiment is performed.
FirmwareReady remains false. Static agreement is not an execution observation.

## Baseline and novelty

The accepted base is M2cd, commit
`9e136ccc53712e5b51d623af174abdd5c84763cc`, with 1181 raw source bindings,
fingerprint `b78812b18ccacaae8c9c74f8c461541baf2ff53516e8e66414725b47644f9e54`.

Stage 0 compared M2ap/M2aq/M2ar/M2as/M2cd before new analysis or tests.
The SSP writer, paired exchanges, exact 20-instruction first-call contract,
frame generations, 510 rank and DATA4700 numeric noninterference are inherited.
They are not new M2ce discoveries or newly executed historical regressions.
No new primary acquisition establishes WDT3C, device identity, a reset event,
native SSP ownership or a native frame read.

Two bounded refinements are new:

1. Decode the retained PWM/port configuration against already acquired standard
   device documentation, narrowing the sources of later port samples and the
   permitted fresh overflow factor.
2. Join source histories and aliases: distinguish the old047E value retained in
   DP from the later CAL frame, and distinguish numeric value elimination from
   outstanding control/bus effects. Curated contradictions exercise this join.

## Reset and earliest control frontier

PROGRAM vector0000 targets24ED for external reset. Vector0002 targets24F4 for
BRK;0004 targets24DC for WDT/opcode trap;0006 targets003C for NMI;0010 targets
24D6 for Timer0 overflow. These causes cannot borrow each other's predecessor
writers. Static vector contents do not establish an actual reset transition.

Standard reset SSPFFFF and ACC0000, PSW read-one rules and undefined LRB/pointers
are not equivalent to `Cpu::new()` defaults. Actual ECU silicon and SF remain
unknown. The earliest unknown DATA operand is B7.1 read at24F1; its transient
flag effect is later killed. The first unknown external DATA byte is4700 at251C.

WDT24F4 writes command3C after the cold marker/24F1 clear and before SSP24F8.
Write-only/reset-stopped rules do not explain3C. Its command decode, acceptance,
immediate/deferred effects and applicability to the actual ECU are missing.
Lexical nextPC24F8 is not proof of hardware-safe progress.

## Conditional SSP and external access

If legitimately reached,24F8 is the code-owned 16-bit SSP047E writer. The pairs
2531/2533 and254D/254F numerically replace/restore it via5555 andAAAA. Restoration
requires the matching accumulator, DD1 and no unaccounted asynchronous effect;
equal numbers do not imply an unchanged storage generation.

DP2519 selects DATA4700, read at251C. Its numeric value is noninterfering with
the selected return proof, as already established in M2ar. Completion, mapping,
physical side effects and same-history ownership remain prerequisites. PROGRAM
4700 or an invented zero cannot replace this functional DATA read.

## New conditional P4/PWM source narrowing

The reviewed standard hardware manual, printed74/75 Table5-5 and printed98–101
PWM chapter/Fig10-2, distinguishes ordinary port reads from RMW. The instruction
manual MBR rule transfers a selected object bit into carry without a DATA write.

Code-owned configuration is PWMCON0=3E, PWMCON1=7E, PWMC/PWMR0/1=FF00,
P4IO=0D and P4SF=FC. Under accepted and retained standard-device semantics:

- Both channels select 12-bit PWM, RUN and low-active mode.
- PWM0 overflow interrupt enable is0; PWM1 enable is1.
- P4.2/P4.3 have IO=1 and SF=1. Later ordinary MBR reads select PWM0/PWM1
  output data, rather than the external pin-read category.
- Early P4.1 JBR2528 precedes that configuration and remains a separate unknown
  external gate: zero continues252E; one branches through252B to003C.

For each selector2 then3, MBR readers2629/2634/263F must observe LOW/HIGH/LOW
in order at distinct observations. DEC bounds0177/0177/00B2 limit software
iterations; they are not physical milliseconds or evidence of a waveform.

CLR IRQ261E must precede the applicable fresh enabled PWM1 overflow factor,
which must precede the actual RB264B IRQH.5 read/ack.264E is the branch, not
the reader. Wordbit13/highbit5 is distinct from ADCbit12/highbit4 and Timer2.
Pending is not ISR delivery. No pulse, clock history or pending event is observed.
These conclusions remain conditional on silicon applicability and control
acceptance; the configuration alone cannot establish successful startup.

## Source-consistent first CAL context

First-call LRB0040 at267C selects page0200/local0200, not M2cd's later0041.
SCB0 must have the same cold source history. X1=03FA at267F makes0084[X1]
address047E. At2682, MOV DP reads the old047E/F word, denoted q. CAL2689 has
not executed yet; the old read cannot consume its future frame.

L A,#5555 at2686 gives DD1 and ZF0. The inherited exact20 inventory covers
267C through5C80. CAL2689 targets5C5C, writes return268C at047E/F and reduces
SSP to047C. STOP remains before268C; no next RAM-test iteration is admitted.

The old q is killed in frame memory by CAL but remains in DP0084/85. Return
PC/SSP/pattern can be numerically q-independent; the whole terminal state is
not, because DP retains q. The original read's completion/effects also remain.

## Frame creator and control obligations

Generation A is the matching CAL2689 frame268C. XCHG5C68 makes temporary
generation B=5555 while A's return token is held in the accumulator. XCHG5C6C
writes a fresh generation C=268C linked to that same creator and history.
RT5C80 must read C, not pretend A was untouched or import a preexisting canary.
Every intervening write, including a same-value write, matters to lineage.

er3 at0206/7 saves5555. The saved IE word00F8 may be zero only through its
native CLR2566/ST2569 ownership chain and retention. Although5C7B replaces its
numeric contribution to A, IE/PSWH effects at5C60/65/71/76 are not eliminated.
Unknown asynchronous/NMI effects and applicable control semantics remain cuts.

CMP5C7C supplies CF0/ZF1, so JNE5C7E must be not taken to5C80. Logical PSWH
operations leave the primary CF/ZF/HC caveat; CMP reestablishes CF/ZF but does
not establish HC. Conditional terminal A=5555, DD1, MIE1 and DP=q do not imply
unchanged full PSW. SF and its physical mapping are not invented.

Software frame geometry is separate from physical memory applicability:
047E may be internal under the standard66207 map and external under66201.
Actual ASIC, writable/retained mapping, READY and native stack safety are unknown.

## Static verification and CI

The small invented corpus checks the new joined obligations, with independent
reference arithmetic and source relations. It is not a CPU instruction stream,
runtime journal or physical experiment. Actual machine/index/write ordinals
remain null and execution/retirement counters remain zero.

The separate M2ce projection permits exactly14 new text sources and one exact
workflow overlay. It binds the complete accepted1181-source base. New content
is frozen and independently reviewed before its literal approval is pinned.
Unknown, inherited or production changes require full historical QA. All17
historical logical checks and their exact pinned sources remain in that lane.

M2ceResearchCI is router + static Ubuntu + static Windows. HistoricalJobsRun=0,
HistoricalJobsNotRun=17, RuntimeJobsRun=0, OriginalRomExecutions=0 in this lane.
Local/Ubuntu/Windows comparison includes every decompressed canonical byte,
including all unknown/provenance fields; it excludes no fields to obtain equality.

The accepted historical generated-runner exception and external Python tooling
exception remain separate: AuthorizedPreservationExceptions=2 and
StrictHistoricalPreservationPass=false. No historical expected fingerprint is
rewritten. A source guard is not a whole-storage preservation claim.

## Minimum missing evidence and next step

Distinct cuts are applicable reset/silicon; WDT3C progress; readable retained DATA
and SFR control; DATA4700 completion plus early P4.1; native-configured PWM sample
and fresh pending chronology; SCB/LRB/SSP/old-frame source continuity; asynchronous
control safety; and matching CAL/saved-token/restored-generation/RT linkage.

The smallest next task is to acquire applicable primary evidence decoding the
exact WDT3C command at24F4 and its immediate/deferred effects before24F8. That
would address the earliest unknown hardware control, without launching fullboot
or inventing a scheduler. This milestone does not authorize that next task.

Actual reset, original CAL2689, RT5C80, SSP/frame generation, return268C,
physical clock/pulses/stack, native downstream rejoin, firmware integration and
target program equivalence remain unestablished. No M2cf is started.
