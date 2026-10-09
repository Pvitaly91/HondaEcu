# M2av - bounded word0196 structured IR and host C11 equivalence

This is an independently reconstructed source-level research representation of
the reviewed M2z software fragment, not original Honda source or firmware.
Entry556F; stop BEFORE5596 or55C5. No P2, timer, IRQ, ROM replacement, ECU ABI,
physical timing or recovered scheduler is implemented. New actual-ROM runs=0.
Runner0.43.0/protocol1 and all38 fix identities remain unchanged.

Exact base: `90333289144854387880de22fdf3346717d18de9`.
Branch: `codex/p28-word0196-structured-c-equivalence-m2av`.

## Native scope and independently reconstructed algorithm

Historical M2z established native05EB word0196 production, native54FA read,
actual JNE5501 entry556F, and word CMP5578/JLT557D on one retained machine.
The earlier05ED->54F5 transition remains ExplicitHarnessSchedule. M2av does not
execute that chain again, enter a Rust machine at556F, seed it from C state,
or introduce a new native scenario/operation. The C entry is offline replay only.

| PCs | Typed instruction effects | Successor / boundary |
| --- | --- | --- |
|556F /5571 /5572|LB018E into AL; byte SLL AL; byte ROL018E through CF|5575|
|5575 /5576|LB localr0; byte AND AL with018E|5578|
|5578|Unsigned16 LE word0196 vs code-owned immediate00C0; CF/ZF only|557D|
|557D|CF1 selects below; CF0 selects equal/above|55BF /557F|
|55BF /55C1 /55C3|AL=0F; store0117 then018F|STOP before55C5|
|557F /5582|Copy original0117 to localr1, then0117 AND AL|5585|
|5585|Test012A.7; flags unchanged|true5592, false5588|
|5588|Test0124.5; flags unchanged|true5592, false558B|
|558B /558E|Only both gates false:018F AND AL, then012A OR1|5592|
|5592 /5594|LB018F; AL ORF0|STOP before5596|

The source-level C function uses genuine `if` branches, including short-circuit
bit gates. Gate0124 is not even read when gate012A.7 already branches. It is not
a switch-PC emulator or a copied C# implementation. The explicit per-PC trace
is an observation aid around the structured algorithm, not its control engine.

All18 instruction sites,15 distinct pinned forms, lengths/DD modes/operands and
three relative branch targets were independently matched to protected original
and listing extents. Neither literal OEM instruction bytes nor native report
fixtures appear in Git. Original/listing/binding/evidence identities stay private.

## Primary semantics and IR-to-C mapping

The MSM66201 Instruction Manual, first edition September1991, was visually
reviewed as full relevant pages. Exact references: ANDB3-24/25, CMPobj/#word3-38,
JBS3-65, JLT3-66/67, LB3-70, MOVB rN,obj3-99, ORB3-107/110, ROLBobj3-120,
SLLB A3-144, STB3-155. LE words are specified at1-5; LRB/page/local bank at
1-10/12/13/14; DD control at1-21..24. The ROLB object description's "word long"
printing is inconsistent with its byte heading/diagram/exact row; byte width is
independently established. MOVB r1's exact reference is3-99, not the earlier
historical search/planning row3-94. No C8/JGT predicate is promoted.

OKI E2E1027-27-Y4 January1998, cover and complete registers page9, independently
confirms CY/CF15, ZF14, HC13, DD12 and SCB2..0. It is used only for register layout,
not MIP/MIE interpretation, reset, watchdog, clock or peripheral claims.

`research/p28-word0196/word0196_ir.json` is typed machine-processable IR, with
canonical UTF-8/LF/two-space serialization and a closed standard-library validator.
Each site carries pinned form identity, typed locations/widths/address selectors,
inputs/outputs, flags read/written/preserved, effects, branch predicate, successors,
incoming context and primary/native-to-C statement tags. No raw byte arrays exist.
Types distinguish u8/u16/bool/pc16, byte truncation, LE words, DD-controlled width
and AH preservation. No sign extension occurs in this fragment.

Named C tags map directly to native sites or explicitly grouped adjacent sites.
Normal effects use the newly computed AL/WriteResult for ZF. The specifically
named CarryFromOldBit reads the immutable pre-instruction operand; its dependency
is not a read of the already shifted byte. `validate_ir.py` checks18 sites,
four complete CFG paths of10/12/13/15 instructions and10 malformed IR refusals.

## Formal compact input/output contract

The standalone C11 function requires a valid, distinct/non-overlapping state,
context and output object. PC556F, LRB0021, halted=false; any incoming DD is
allowed because the first LB establishes DD0. Other local/page alias contexts
are refused, not generalized from the listing. No uninitialized field is read.

State contains A/fullPSW/PC/LRB/X1/X2/DP/USP/SSP/SF/halted, eight local bytes
0108..010F and bytes0117/0124/0128/012A/018E/018F/0196/0197. Words use explicit
low/high assembly, not host-endian loads or pointer casts. Integer operations
are unsigned and truncations/masks explicit; AL updates retain AH. No signed
overflow, implementation-defined signed shift or arbitrary alias is required.

Outputs include final declared state, compare operands/flags, branch/stop,
every per-PC A/PSW/nextPC, ordered reads/writes, and writer PC/width/old/new.
Maximum bounds are15 steps,17 accesses and5 writes. Invalid entry/context/ordinal
overflow/arguments are refused without mutating state. Other RAM, unknown aliases,
cycles, absolute instruction counters and peripheral evolution are not modeled.

LB changes ZF/DD0; SLL/ROL change CF only; byte AND/OR change ZF only;
word CMP sets CF=(0196<00C0), ZF=(0196==00C0), preserving A/HC/DD.
MOVB/STB/JBS/JLT do not alter flags. Full remaining PSW is retained as a snapshot,
not reset/canonicalized. DATA0196 is neutral word storage, not RPM or time.

## Ordered writes and provenance restrictions

Common5572 writes018E even when unchanged. Below then writes0117 at55C1 and018F
at55C3. Not-below writes localr1 at557F before0117 at5582; only both bit gates
false add018F at558B and012A at558E. These are observable ordered RMW effects,
not optimized-away stores. Same-value writes retain separate ordinal annotations.

Event index/ordinal-base are offline annotations, NOT native generation authority.
Historical native proof comes from the protected event-wide journals and current
05EB generation, both same-generation54FA/5578 readers and overlap exclusion.
The evidence verifier distinguishes NativeOwnedInput, HistoricalHarnessInput,
OfflineReplaySnapshot, IndependentModelValue and ActualRuntimeSourceNotEstablished.
Host-generated owner identities never become a native proof source.

0117 retains once-initial/native-write history;018E/018F retain scratch initial
and persistent native-write history;012A retains neighboring bits;0124 remains
upstream owned;0128.2 remains once-initial masked history. None is assigned a
new physical mode. Repeated C calls are offline replay, not recovered scheduling.

## Evidence and independent equivalence checks

C/IR and the independent primary specification were sealed before C# comparison.
The original C# `P28Word0196AlternateModel.Build` is invoked from the existing Core
assembly by a separate reflection adapter; its implementation is not translated
into C. The C function itself has no Rust/.NET dependency.

| Evidence domain | Actual comparison |
| --- | --- |
| Independent invented C specification |398658 vectors, including320 repeated calls;16 argument/context refusals|
| C vs unchanged C# oracle |81920 invented vectors;1044721 per-PC snapshots;283346 ordered writes;0 mismatches|
| Historical original A |36 completed observations:33 quartet-derived,3 gate controls;below/equal/above9/3/24;144 writes|
| Historical one-cell in-memory B |6 observations, separately classified;all not-below;26 writes|
| All available completed native observations |42;552 per-PC snapshots;170 ordered writes;0 mismatches|
| Incomplete historical cases |27=12Partial+3NoFresh+12NotRun;not passed as complete equivalence|

The historical42 branches are9 taken/33 not-taken, not42 new M2av ROM executions.
Historical path lengths are10 (9 rows),12 (11),15 (22). The13-step second-gate-taken
path has no witness in this historical corpus; its reconstruction is primary/static
and invented/C# differential coverage, not an additional native observation.
All251 historical sealed artifacts and four source identities were revalidated,
including exact original/raw-report equality for63 A events. Completed comparisons
cover entry/full observed CPU, eight local registers, relevant RAM, all per-PC
states/paths, word comparison, every ordered access, writer PC/old/new/width and
event-wide generation ordinal. Ten private provenance corruptions were rejected.

SF/halted/cycles/absolute instructions and memory outside the observed subset
were not serialized historically. SF/halted driver placeholders are explicitly
excluded from original comparisons, not fabricated observations. Their retention
is covered separately by invented tests. SCB is transparently derived from the
observed fullPSW low3 bits. No unresolved observed mismatch is hidden as unsupported.

## Host build and immutable production boundary

Run after the existing Release Core build, from the repository root:

```powershell
pwsh -NoProfile -File research/p28-word0196/run-host-tests.ps1 -RunTag local
```

The script discovers installed MSVC on Windows or cc on Linux, compiles C11 with
strict warnings, executes the independent C specification and typed IR checks,
then compares C with the unchanged C# oracle. Python standard library and .NET8
are test tools only. Outputs stay in a fresh ignored .tmp directory. Private
historical comparison is a separately authorized local argument pair, never a
public CI fixture. Ubuntu/Windows CI add only this host test step; existing Rust,
Core/CLI/Desktop/portable/format/privacy jobs and steps are not weakened.

Windows strict MSVC host checks pass locally. Linux host build proof and final
delivery are bound to the exact pushed SHA's mandatory CI jobs, recorded in the
private final report after actual success, not inferred from Windows compilation.

All Rust sources, decoder/executor/Cpu/Bus/admissions, Core/CLI/scenario schemas,
version assertions and18 stabilization sources remain byte-identical. Historical
0.40/0.41/0.42/0.43 binaries/reports are preserved; new builds use dedicated targets.

## Toolchain gap, historical boundaries and STOP

Host compilation does not establish nX-8/200 target toolchain, ABI/calling
conventions, memory/ROM placement/relocation, startup/linker, interrupt/context,
exact code generation, checksum, cycle-equivalent control flow or flash/hardware
validation. FirmwareBIN=0; ECU compilation suitability=NotEstablished.

M2au INT accounting, M2at DEC semantics and M2an SLLB semantics remain complete.
M2as WDT3C/M2ar reset/M2ap SSP-ADC/M2ak source-to5722 remain Research/Blocked;
M2aq preflight/CAL2689/RT5C80 remain blocked/NotRun. M2ao019B frontier unchanged;
M2al/M2am C8 PrimaryConflictUnresolved;M2ah STOPbefore5722;DATA019B.2 owner not
established;M2tJGT233A unresolved;M2ag/M2af unchanged;strictM2iBlocked.
IRQNotInjected;TimerEvolutionNotModeled;RecoveredEcuSchedulerNotEstablished;
ElapsedTimeNone;PcInspectionOnly/NotFlashReady;physicalRpmAvailable=false;
physical fuel/time/degrees unavailable. GUIr3 paused/NotRun;D1/D2 interactive,
hardware/fullboot NotRun. C8/WDT inquiries remain NotSent.

One next evidence step, NOT performed: independently establish the missing
target ABI/context/memory-layout contract before considering target code generation.
STOP after final delivery: no M2aw, firmware/BIN/ROM replacement, WDT/C8 fix,
reset/fullboot/IRQ/timer/GUI/hardware work.
