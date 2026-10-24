# M2bu — bounded original-byte entry-to-exit continuity

M2bu is a default-off research extension of the production audit mechanism.
Its exact accepted M2bt base is `7eb26571d8ee1f849efe5ffa619b0201008b267c`.
This document describes requirements and interfaces, not an execution receipt.
No static contract, test fixture or JSON can establish actual execution or
authorize firmware placement, downstream peripherals, flashing or hardware.

## One retained production machine

An accepted positive case begins at54F5 and follows the six independently
reviewed original predecessor forms, then the18-site algorithm without a host
state transfer:

| PC | Documentary effect | Positive successor |
|---|---|---|
|54F5|JBR DATA0128.2, branch when clear; flags preserved|54F8 when bit set|
|54F8|MOVB localr0,#FF; flags preserved|54FA|
|54FA|Word L A,DATA0196/0197; DD1, ZF from whole word|54FC|
|54FC|Word ST A,er1; localr2/r3 at010A/B; flags preserved|54FD|
|54FD|CMPB DATA0117,#0F; unsigned CF/ZF only|5501|
|5501|JNE consumes ZF0; next5503 plus signed108|556F|

M2y, the unchanged M2bs contract and the reviewed OKI MSM66201 instruction
semantics establish these expectations independently of production Rust output.
M2av's unchanged structured IR/C11 establishes the following algorithm.
Incoming DD0 and DD1 are both allowed;54FA establishes DD1 before word ST.

Word L overwrites the entire A: final AH is retained from DATA0197 after54FA,
not from incoming54F5 AH. The predecessor writesr0=FF, actually read at5575.
ST er1 writesr2/r3 and that word is retained to exit; the following18-site
algorithm does **not** functionally read er1. No nonexistent read is fabricated.

Each case owns exactly one production Cpu/Bus and one immutable PROGRAM source.
Production decode_checked and execute_decoded are reused through the existing
checked-step implementation. There is no second CPU, JSON state handoff,
mid-execution seed, PC setter, C-derived execution engine or opcode-semantic fix.
The new opaque wrapper retains internal CPU/Bus identities and checks actual
snapshot continuity; host memory addresses are never semantic trace fields.

## Original source and closed paths

Private admission reuses the unchanged M2bs whole-image/source/listing verifier,
then takes exactly208 unchanged bytes at original PROGRAM54F5..55C5exclusive.
Intermediate bytes are retained, not repaired, relocated or treated as executable
merely because they lie in that segment. Only24 frozen instruction sites execute.
The source/profile/whole-image/selected-extents and before/after fences are explicit.

| Positive path | Predecessors | Algorithm | Total | Stop BEFORE |
|---|---:|---:|---:|---|
|A|6|10|16|55C5|
|B|6|12|18|5596|
|C|6|13|19|5596|
|D|6|15|21|5596|

These are exact frozen path budgets, not a caller-configurable maximum. The old
Session::new1..16 admission and old constructors remain unchanged. A private
sealed entry-budget token enables only these new closed routes; no generic
unrestricted21-step API is exposed. The new Cargo feature
`p28-word0196-entry-continuity` requires `p28-word0196-original-rom`, defaultOFF.
Its only binary is `m2bu-entry-continuity` with required-features admission.

Two separate bounded branch controls stop without entering forbidden code:
JBR bitclear reaches5533 after1 instruction; CMPB equality/JNE fallthrough
reaches5503 after6. Neither5533 nor5503 is executed. These observations are not
successful complete A/B/C/D algorithm executions. No TM0/P2 is read or mocked.

## DATA and architectural observations

DATA0196/0197 is an even little-endian word. The predecessor word read and later
5578 comparison must see the same selected technical pair, without an overlapping
writer in this case. The threshold00C0 is an immediate, not a DATA read.

All seeded inputs are explicit at54F5 only: full representable PSW, A, LRB0021,
SCB, SSP, all8 pointing banks, localr0..r7/er0..er3, inventoried DATA bytes and
technical hostSF. The representable-PSW predicate is unchanged; SF's physical
meaning/storage is Unknown. Pointing-register and stack values are technical
retained context, not proved firmware ownership or an invented stack frame.

For every instruction, independent comparison covers before/after CPU snapshots,
full PSW/CF/ZF/HC/DD/OtherPSW, local/pointing aliases, untouched RAM frame,
selected decode/PC successor, complete PROGRAM acquisition journal, logical DATA
events and constituent raw DATA events. Same-value stores retain separate
ordinals. ST er1 is one logical16-bit write and two ordered raw byte writes.

The prefix adds3 logical reads and2 logical writes. Positive A/B/C/D totals are
8/12/13/15 logical reads and5/5/5/7 logical writes respectively. Functional raw
write-byte counts are6/6/6/8. DATA0124 is not read on pathB. PositiveA requires
initial0117!=0F, so its later55C1 store0F cannot be a same-value write; other
reachable same-value controls coverr0, er1,018E,018F,localr1 and012A.

Host diagnostic/cycle counters are implementation observations, not physical ECU
time. PROGRAM decoder lookahead, selected instruction fetch and functional DATA
access remain distinct. A terminal PC is reached by actual production execution;
no terminal instruction is retired and no host jump repairs a successor.

## Independent expectations and small corpus

The new independent oracle first derives the six predecessor states and ordered
events, then feeds only that **expected** derived state into the unchanged
structured reference. This is not transfer of an actual Rust CPU state.
Production output never determines expected flags, branches or result values.

The positive corpus has32 cases per mode,8 perA/B/C/D, expected592 retirements
per corpus:192 predecessor plus400 algorithm. It covers0000/00BF/00C0/00C1/00FF/
0100/FFFF, DD/HC/CF/ZF/SCB/OtherPSW, technicalSF variants, both gates, predecessor
effects and reachable same-value writes. Two branch controls have a separate
inventory, output and verdict; they are not added to32 positive completions.

Public fixtures are independently invented at6200, suffix627A, with changed
DATA roles. Their24 selected extents occupy59 bytes within an invented208-byte
segment. No OEM byte sequence, private image/hash, native snapshot or private
trace is committed or uploaded. Private and public original-byte admissions
cannot silently substitute for one another.

The complete source/corpus/wire/expected/program/runner identities are frozen
before the final runtime. Every actual record is checked against that immutable
freeze. First mismatch retains PC/field/expected/actual and blocks acceptance;
expectations are not edited after observing a mismatch.

## Source provenance and downstream live-ins

M2bs's qualified historical05EB producer→54FA read→5578 comparison remains an
old source-CPU observation in its actual scope. New M2bu cases do not execute05EB
and cannot inherit native ownership just by matching its numeric word. Their
classification is `OriginalRomBytes_TechnicalCallerToExitExecution`.

| Boundary live-in | M2bu status | Remaining dependency |
|---|---|---|
|PC5596/55C5|Actual stop-before boundary required|Does not establish downstream execution|
|AL|Actual terminal snapshot compared; below0F/not-below final018F ORF0|Physical output role unknown|
|CF/ZF/DD|Compared0/0/0 not-below,1/0/0 below|P2 instruction's laterZF change not executed|
|AH/HC/OtherPSW/LRB/SCB|Retained from defined predecessor/entry sources|No native scheduler ownership promotion|
|SSP and pointing banks|Technical input and exact retained aliases|Native frame/stack capacity/ABI unknown|
|P2 DATA/SFR0024|Unknown, no permission/value supplied|Existing peripheral value, RMW ownership and side effects missing|
|Timer/IRQ/peripheral/ASIC context|Outside admitted scope|No default0/FF, fake latch, RT/RTI frame or clock evolution|

At5596 the documented next instruction is ANDB P2,A; at55C5 it is ORB P2,A.
Neither executes. `NativeExitBoundaryReached` can describe actual positive
boundary reach, while `ActualNativeDownstreamRejoinNotEstablished` remains true.

## Owned builds, resume and delivery

All new local Cargo commands require BOTH CARGO_TARGET_DIR and --target-dir to
name `.tmp/m2bu-owned/cargo-target`, authenticated ownership and pre/post
protected-output fences. Historical targets, reparse/junction/symlink routes,
build-script overrides and cache copies are not permitted. The inherited single
M2bt generated-runner loss stays visible; it is not permission for another loss.

`private/reports/m2bu/RESUME_STATE.json` is atomic. Runtime state/cache is outside
the closed four-file artifact directory. The controller verifies complete record
hashes, source/corpus/freeze and actual process identity before continuing.
An orphan complete stdout/transport is checked and recovered before executing
another case; an ambiguous partial result blocks rather than silently reruns.
Completed cases are not repeated because a response or session was interrupted.
Private/public positive/boundary progress is kept separately. No background
automation continues after a user pause.

The research CLI is `research/p28-word0196/validate_native_entry_continuity.py`:
explicit --rom/--profile for private mode, or --public for invented mode, plus
--runner/--output. --branch-controls selects the separate two-case experiment.
It never builds a runner, searches for a ROM or contacts a NAS.

CI preserves historical2, M2bt2 and Desktop1 guarantees and adds M2bu2 matrix
jobs after both M2bt jobs. Frozen M2bt7eb workflow proof is explicitly historical;
its actual execution source remains7de. New current M2bu sources receive their
own closed source guard, old-admission/new-feature Rust tests and public32+2
execution. All7 actual jobs are required for new delivery. Public canonical
comparison reads every decompressed byte and field on local/Ubuntu/Windows;
platform executable metadata is not a reason to omit semantic fields.

The final private report is written last after QA, substantive normal commit/push,
exact-SHA CI, byte comparison, preservation/privacy and evidence seal. Only then
can `M2bu ACCEPTED_WITH_HISTORICAL_PRESERVATION_EXCEPTION / Research-Only` be used,
and only if no new unauthorized protected differences occurred. The historical
expected runner SHA and strict preservationFAIL remain unchanged.

ActualHardwareEcuExecutionNotObserved; RecoveredFullEcuSchedulerNotEstablished;
PhysicalSFNotEstablished; NativeStackSafetyNotEstablished;
PeripheralStateOwnershipNotEstablished; ActualNativeDownstreamRejoinNotEstablished;
SafeROMPlacementNotEstablished; TargetProgramEquivalenceNotEstablished;
FirmwareIntegrationNotEstablished; FirmwareReady=false remain.

STOP after delivery: no M2bv, P2/downstream execution, firmware BIN/HEX/patch/flash,
GUI or hardware.
