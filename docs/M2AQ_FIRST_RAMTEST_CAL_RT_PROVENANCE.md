# M2aq - First RAM-test CAL/RT provenance

## Result and evidence boundary

**Research/Blocked - ExecutionPreflightBlocked.** The first genuine
`CAL2689 -> 5C5C -> XCHG restore -> RT5C80 -> 268C` roundtrip on one
Cpu/Bus is **not established**. `ActualRomExecutions=0`; no technical
synthetic ROM execution or private direct-Cpu bypass was performed either.
The independent invented tests are specification algebra, not an OEM trace,
execution permission or positive native verdict.

Base: `c66f4ef880dc3a81046d83d6c015120d2f4da8d4` on
`codex/p28-ssp-adc-pending-provenance-m2ap`.
Delivery branch: `codex/p28-first-ramtest-native-frame-m2aq`.
Runner0.41.0, protocol1 and M2an identity
`byte-sll-off-page-preserves-noncarry-flags` remain unchanged.
No executor, operation, wire schema, admission, GUI or hardware change.

The earliest missing prerequisite is applicable reset/reaching context and
native state/history before24ED. The structural reset vector is known;
an observed reset-to-entry transition is not. Even treating24ED as a
conditional research entry leaves mandatory external control/read gates.
No actual execution is started when any preflight obligation is missing.

## Independent input and primary-source audit

Private baseline binding, original image and fresh selected instruction bytes
were checked read-only, separately from listing/CFG annotations. The root audit
matches167 selected extents; the selftest/first-call audit matches186 selected
extents, including the full20-instruction contract below. These overlapping
selection counts are not dynamic instruction/event counts. Exact bytes,
digests, manifests, complete per-gate metadata and source images remain private.
This document contains reduced instruction/provenance metadata, not ROM dumps.

Complete relevant MSM66201 Instruction Manual pages were visually reviewed:
vector/little-endian, PR/SCB/LRB, stack/alignment, MOV SSP, word/byte XCHG,
CAL/RT, load/store, CMP/CMPB, JNE/JEQ/JLT/JGE, bit moves, MBR, SB/RB,
PSW clear/logical operations, shifts and DEC. Relevant MSM66201/66207 user
scans establish documented register/read-one rules and standard memory/SFR/
interrupt maps. Incomplete archive cover, edition/revision and custom-ASIC
applicability are explicit limitations; no nX-8/500S semantics were imported.
The C8/JGT primary conflict is unchanged and is not required for this first
target. Primary effects and runtime admission are separate obligations.

## Root identity and bounded caller CFG

PROGRAM0000 is the reset-input vector and contains24ED. PROGRAM0002 is the
BRK-reset vector24F4;0004 is WDT/opcode-trap24DC;0006 is NMI003C.
PROGRAM0010 is the Timer0-overflow vector24D6, **not** reset entry.
No listed direct software edge into24ED was found. Hardware/vector origin is
not a software caller edge, and a vector word alone is not actual history.

| Entry class | M2aq finding |
| --- | --- |
| ActualResetEntryEstablished | NotEstablished; applicable reset state/transition absent |
| RootedSoftwarePrefixEstablished | NotEstablished; no retained rooted Cpu/Bus record |
| ConditionalCallerEntry |24ED cold-path candidate, subject to every gate below |
| TechnicalHarnessEntry | Existing host entry/state seeding would be technical, not a substitute |
| NotEstablished | Actual first-call entry and machine identities |

Conditional cold flow is24ED ->24F4 ->24F8 ->2506(taken250E) ->
2510(taken2516) ->251C external read ->2521(fallthrough2524) ->
2528(taken252E only for P4.1=0) -> register/PSW selftests ->259D SFR setup ->
2623 pulse waits ->264E(taken2655 only for fresh applicable factor) ->
pointer selftests ->2675(taken267C) ->267F ->2682 ->2686 ->2689.
Every edge is conditional metadata, **not a traversed native prefix**.

24ED owns marker46 at DATA00F5.24F1 clears only DATA00B7.1, an ordinary
RAM bit in the PR6 USP high byte, not P4/peripheral state. Unknown neighbor
bits are preserved; the old-bit ZF is not the later branch producer.
24F8 writes SSP047E.24FC sets LRB0010 (page0/local0080);24FF clears
writable PSW fields, establishing SCB0/DD0/MIE0 with reserved read-one
readback0CC8. Clearing PSW does **not** initialize the separate internal SF.
SF/context continuity cannot be supplied by favorable host initialization.

BRK entry24F4 bypasses the24ED marker and24F1 bit producers. Noncold marker
paths can bypass some reads but need their own reaching/source evidence;
they cannot borrow cold-path identity. The later2694 ->2682 loop backedge
requires actual first return and separate268D history; it cannot authorize
the first call. No CAL/RT instruction occurs before2689 in this bounded cold
prefix. This dominance statement is scoped CFG analysis, not global runtime.

## Early gates and alternatives

All actual reaching histories in this table are NotEstablished. A code-owned
implication means only that the branch follows **if** its native producers,
mapping and uninterrupted context are established. Full private gate records
include exact forms, source and alternative for30 early/helper dependencies.

| PCs | Source and required outcome | Actual prerequisite / alternative |
| --- | --- | --- |
|24F4 | MOVB WDT0011 command3C | Earliest external control/reset/clock-effect gate; not SBYCON0010 and not RAM echo |
|2506/2510 | LB2502 marker46; STB2504 retains flags; CMPB250E#46: ZF0 thenZF1 | Code-owned cold implication; alternate marker exits/rejoins do not supply cold identity |
|2514 | CMPB2512#47 on noncold path | Other marker goes2528; independently establish that alternative caller, never patch outcome |
|251C | LB A,[DP], DP from2519#4700 | First new explicit external DATA-space read; value/mapping/read behavior unknown, not PROGRAM4700 |
|2521 | JBS current00B7.1 clear from24F1; MB251E changed bit0 only | Fallthrough2524 conditional on retained byte; set bit takes2528 |
|2528 | JBR P4.1 at002C, need0 ->252E | Unknown external input/mode;1 ->252B J003C alternate |
|2538/2554 | CMP2535/2551 after SSP5555/AAAA adjacent exchange pairs | Equality conditional; failure ->2598 marker41/BRK259C |
|253F/255B | CMP253C/2558 IE after ST253A/2556 patterns5555/AAAA | Commands are native; applicable IE readback/effects required, not default RAM storage |
|2548/2564 | CMP2546/2562 LRB after native1555/0AAA writes | Conditional equality; temporary local/page bases differ, no intervening off/local writes |
|2578/2582 | CMPB2576#DD /2580#EA after PSWL byte exchanges |55 writable15 readsDD;AA writable22 readsEA due read-oneC8; failure ->2598 |
|258A/258C | SB2584 MIE; MB2586 CF=1; MB2588 ZF=1 | JGE notTaken and JNE notTaken; failure ->2598 |
|2594/2596 | RB258E MIE; MB2590 CF=0; MB2592 ZF=0 | JLT notTaken, JNE taken259D; other result ->2598 |
|259D..261E | Native port/mode/secondary-function/timer/IRQ configuration; CLR IRQ261E | Applicable effects/async domain required; commands do not prove waveforms or elapsed time |
|2627/2632/263D | DEC2626/2631/263C DP produces ZF; require nonzero | Finite ranks0177/0177/00B2; zero ->2650 marker4C/BRK2654 |
|262C/2637/2642 | MBR2629/2634/263F directly copies selected P4 bit toCF | For each bit2 then3 need LOW/HIGH/LOW; other sample follows DEC backedge, no invented transitions |
|2649 | INCB2644 AL, CMPB2647#4 | AL3 repeats2623;AL4 leaves264B only after both complete sampled histories |
|264E | RB264B IRQH.5 sets ZF=!oldbit and clears selected factor | Old1 ->2655; old0 ->2650 fault; factor must be fresh since261E |
|2665/266A/2670/2675 | Native5555/SLLAAAA X1/X2 stores and CMPs | Equal ->267C; failure ->2677 marker42/BRK267B; retained SCB0 required |

MBR means bit-position selection using AL&7, **not bit complement**. JLT
waits while CF1, JGE while CF0, then JLT while CF1: required samples are
LOW/HIGH/LOW for P4.2 and P4.3. Finite countdowns are not calibrated time.
Standard IRQ word13 (IRQH.5/vector0022) is PWM0/PWM1 overflow, not Timer3
(word10), ADC(word12) or Timer2(word8). Actual device/ASIC mapping and genuine
factor generation remain unproved. Clearing IRQ261E invalidates old pending.

Documented standard DATA4700 is external on both66201 and66207. DATA047E is
internal on66207 but external on66201; code using047E does not select device
or prove board mapping. DATA/PROGRAM spaces are distinct. No default-zero,
scratch canary, guessed RAM size or physical peripheral event is promoted.

## Exact first-call contract - static only

This is the entire ordered contract including caller setup, not a shortened
CAL/XCHG/RT diagram. Values are independently derived conditional predictions.
All actual event indices, global native ordinals, call identities and Cpu/Bus
identities are null; none of these instructions was executed in M2aq.

| PC / length | Exact form and conditional effect |
| --- | --- |
|267C /3 | MOV LRB,#0040: page2/local0200; does not set SCB |
|267F /3 | MOV X1,#03FA: SCB0 PR0 storage0080/81 |
|2682 /4 | MOV DP,0084[X1]: reads prior word047E/F BEFORE CAL; prior value unknown, DP not helper EA source |
|2686 /3 | L A,#5555: DD1/ZF0; CF/HC retained |
|2689 /3 | CAL5C5C: writes nextPC268C to word[SSP047E], SSP047C, SF0; ordinary flags retained |
|5C5C /1 | MOV X2,A: pattern5555 at SCB0 storage0082/83 |
|5C5D /3 | SB off0230.7: sets selected bit7 to1, old-bit ZF; unknown neighbors retained |
|5C60 /5 | AND IE,#02A0 word: requires applicable IE source/effects; native2567 IE0 source only conditional |
|5C65 /3 | ANDB PSWH,#FE: clear MIE, retain DD and read-one bits; logical-on-PSW flag caveat |
|5C68 /4 | XCHG A,0084[X1] word: frame047E/F gets5555; A gets CAL-derived268C |
|5C6C /4 | Adjacent XCHG same EA/width: fresh frame generation gets native saved268C; A gets5555 |
|5C70 /1 | ST A,er3: local0206/7 gets5555, disjoint from frame/X1/X2 |
|5C71 /3 | ORB PSWH,#1: set MIE, retain DD; maskable delivery still needs IE, NMI not excluded |
|5C74 /2 | L A,00F8 word: zero only with native CLR2566/ST2569 retained source |
|5C76 /2 | ST A,IE: native value/control effects required, not guessed echo |
|5C78 /3 | RB off0230.7: known old selected1 ->ZF0, clear selected bit |
|5C7B /1 | L A,er3: current native5555 generation, DD1/ZF0 |
|5C7C /2 | CMP A,X2 word: independently owned5555 equality ->CF0/ZF1, A/HC/DD retained |
|5C7E /2 | JNE: consumes that exact ZF, notTaken ->5C80; failure ->5C81 marker/BRK5C85 |
|5C80 /1 | Ordinary RT: SSP+2 ->047E, read current restored word ->PC268C, SF0; no interrupt-frame restore |

Terminal requirement: STOP at268C **BEFORE executing268C**. No SLL268C,
CAL268D or loop continuation. Word access aligns to even address, little-endian;
`0084+03FA=047E`. SCB0, LRB0040, DD1 and no asynchronous mutation are
mandatory. Frame047E/F, X1_0080/81, X2_0082/83, local0206/7 and bit0230.7
are distinct. Every overlap, including high-byte writes, must be considered.
IE/PSW/SFR effects and unknown prior reads are obligations even if the final
pattern comparison would not depend numerically on their values.

Primary user PSW warnings make CF/HC/ZF after logical operations on PSW/PSWH
unsafe to infer as ordinary arithmetic flags. No positive JNE claim is based
on5C65/5C71; CMP5C7C independently replaces CF/ZF. DD-preserving raw-byte
MIE edits retain reserved read-one0C (the invented examples use1C/1D).

## Frame generations, readers and identities

| Generation / role | Creator/writer or reader | Address/value and source |
| --- | --- | --- |
| A - original frame | CAL2689, first invocation |047E/F=268C from native nextPC; prior RAM generation may be unknown |
| B - temporary overwrite | XCHG5C68, same invocation/machine |047E/F=5555; previous A; native A holds A's268C and lineage |
| C - restored frame | XCHG5C6C, same invocation/machine |047E/F=268C from saved native A; previous B; new generation, A's semantic CAL lineage |
| D - reader, not a write generation | RT5C80 | Reads current C at SSP-after-pop047E; matching CAL creator; returns268C |

An equal number alone proves nothing about creator, generation or machine.
Native global ordinals must be monotonic across the **complete ALL-write**
history, including nonframe writes, with CAL frame/SSP and each XCHG event
ordering. A restored generation is not A. A different invocation at2689,
different CPU/Bus/path, stale/host frame, imported state, flag patch or host
return cannot establish matching native RT.

The invented toy ledger tests this ordering/provenance algebra, including
nonframe writes and overlap/context negatives. Its `ModelOrdinal` is NOT an
actual native ordinal and its eight-write example is NOT a complete OEM
instruction journal. `SpecificationMatches` stays `InventedOnly` with actual
fields false/null and `ExecutionPermitted=false`.

CAL268D statically creates return2690, a distinct invocation/creator and new
generation/ordinal. It depends on genuine first return and intervening268C;
it cannot reuse the2689 frame. No second CALL execution is authorized here.

## New static discrepancy - note only

Exact word `DEC DP` is documented to update ZF and HC, retaining CF/DD.
Current executor word-DEC HC handling covers X1 but omits DP. Independent
witnesses: DP0010/HC0 ->000F should HC1; DP0011/HC1 ->0010 should HC0.
Source inspection leaves the old HC in those DP cases. The primary DEC
description and flag table establish decrement/HC; the inherited function
line's plus-one printing inconsistency is retained as a source caveat.
This is **ConfirmedStaticSemanticDiscrepancy**, not an executed probe or fix.
It affects exact2626/2631/263C full-state semantics; ZF drives their timeout
branches and later MBR replaces CF, but dead/use distinctions do not authorize
an incorrect full-state executor. No production/admission/version change.
PSWL read-one behavior is consistent with the reviewed primary evidence;
no new PSWL defect was found. M2an exact SLLB fix remains complete.

## Preflight and capability decision

Verified binding alone cannot pass execution preflight. Starting root/state,
native early history, RAM/SFR sources/effects, instruction/admission,
bounded runnable ranges/budget, one machine identity, continuous trace and
ALL-write frame/reader proof are missing or conditional. Terminal-before268C
is only a specification. Result: `ExecutionPreflightBlocked`, actual-ROM0.

Existing technical initializer/seeding is not a verified reset loader. M2ad's
063B/54F5/063E high-stack contract and M2ag's retained bounded fuel history
cannot authorize this startup/frame domain. Current safe transport has no
rooted first-RAM-test capability. No bypass/direct-Cpu experiment was used.

A private exact proposal separates prerequisites from implementation:
after applicable reset/WDT/memory/peripheral evidence, a separately authorized
runner0.42.0 read-only capability could add a verified reset-vector entry,
narrow exact-form/PC/bus admission and continuous identities/journals, with
typed stop-before-unknown and terminal-before268C. Protocol1 only if backward
compatible; any schema expansion needs separate review. This is **proposal
only**, not a new release, operation, admission or implementation. No arbitrary
PC, host SSP/pattern/frame repair, JSON reconstruction or global ISA fallback.
An explicit finite budget must follow validated paths/sources, not invented
timer/pin histories. Exact semantic fixes require their own approved scope.

## Regression and preservation scope

New public files are only the research document and two invented Core fixture/
test files, plus minimal README/ROADMAP links. Independent cases cover SSP
pairs/unknown/interruption, native-frame hypotheses and fresh lineage,
wrong creator/machine, stale/host return, all-write chronology, indexed and
high-byte aliases, DD/context/PSWH changes, comparison producers and every
fail-closed preflight input. No Rust output is copied into expected results.
Full Rust/Core/CLI/Desktop headless, relevant M2ad/M2ag/M2ak-M2ap regressions,
format/diff/privacy, full protected SHA-256, current18 stabilization hashes
and historical runners are mandatory delivery gates. Exact-SHA CI and final
private attestation/report record the actual results; QA cannot promote research.

## Historical limits and STOP

M2an semantic fix complete; M2am C8 PrimaryConflictUnresolved; M2al JGT2714,
M2ak DATA019B bootstrap and M2ap SSP/ADC remain Research/Blocked.
M2ao frontier stays afterCLR2758/beforeSTIE2759. M2ah stays STOP before5722;
DATA019B.2 actual owner NotEstablished;5722/5725/5733 DynamicNotRun;
M2t JGT233A Blocked/Unresolved; M2ag/M2af unchanged; strictM2iBlocked.
IRQNotInjected; TimerEvolutionNotModeled; EnclosingIRQFrame and
RecoveredEcuScheduler NotEstablished; ElapsedTimeNone; RT5CCD/RT5801/later
returns NotRun. PcInspectionOnly/NotFlashReady; physicalRpmAvailable=false;
physical fuel/time/degrees unavailable. GUIr3 paused/NotRun, D1/D2 interactive
NotRun, hardware/fullboot NotRun, FirmwareBIN=0.
Vendor inquiry stays InquiryDraftReady/NotSent.

Even a future genuine first return would not prove all510 iterations, native
initialization, JGT2714 exit272A, CAL276A frame/ADC pending/RT5CCD, retained
DATA019B-to5722 or recovered scheduler. Restoring previously unknown RAM or
temporary5555/AAAA does not create an initialization owner for019B bit1/bit2.

One next evidence step, **not executed**: obtain and validate applicable primary
reset-to24ED/reset-state/WDT evidence with identifiable device/edition/revision.
First establish that reaching context/control gate before proposing execution.
STOP after delivery: no M2ar, CAL268D, all510 loop, JGT fix, ADC/IRQ injection,
runtime5722, fullboot, GUI, hardware or vendor communication.
