# M2cb — DATA011F / DATA011B source ownership recovery

M2cb is static Research-Only work over accepted M2ca commit
`2e327d2ade8d419180f1088cb277a306accbab4f`. No new original-ROM execution,
CPU/Bus session, IRQ delivery, timer evolution, Rust feature or executable is
introduced. `FirmwareReady=false`.

The qualified research classification is
`CONDITIONAL_SOURCE_LINEAGE_ESTABLISHED / EXECUTION_BLOCKED`.
Exact transformations and conditional graph relations advance the source
question; current-machine generations and their preservation are not established.
Delivery still requires the separate QA, exact-SHA CI, full static canonical
comparison and private evidence seal. This document is not runtime admission.

## Five separate levels

A static writer, a conditionally reachable writer, a value transformation under
explicit preconditions, an actual same-machine writer event, and preserved
generation at the reader are distinct facts. No successful static calculation
promotes one level to the next.

The accepted M2bz technical entry starts at063B and stops before064C. Original
DATA011F and011B are unowned A5 canaries in that scope; neither was initialized,
functionally accessed or owned by a prefix writer. M2ca's source classifications
remain unchanged. DATA012A was technically seeded00/80; old actual5685 clears
bit7 to00, leaving bits0/3 clear. Those old observations are reference evidence,
not imported generations in a new machine. Public fixture literal011B is mapped
original0117, not an owner of original branch011B.

## Exact copy candidates

| Load | Store | Conditional source word | Destination word |
|---|---|---|---|
|03FE|0400|0212/0213|011A/011B|
|0402|0404|0214/0215|011C/011D|
|0406|0408|0216/0217|011E/011F|
|5C2B|5C2D|0212/0213|011A/011B|
|5C2F|5C31|0214/0215|011C/011D|
|5C33|5C35|0216/0217|011E/011F|

Each pair is L A,S8[USP] followed by ST A,offN8. DD1, owned USP0280,
page0100/LRB0021 or a proven equivalent, SCB-selected pointing context and
uninterrupted load/store completion are required. Signed displacements are
-6E/-6C/-6A. Little-endian low bytes map0212→011A,0216→011E and high bytes
0213→011B,0217→011F. The selected relationships preserve0213.7→011B.7 and
0217.3→011F.3 exactly. A word copy does not manufacture ownership of its source.

The three copies are linear within each selected entry/helper; their execution
is conditional on reaching that context. Do not assume all copies execute on
every firmware invocation or combine one root's generation with another root.

Private source audit reuses the verified11,499 listed instruction extents and
6,479 operand accesses; it checks exact bytes/lengths against the unchanged image
and frozen listing, without new disassembly or target execution. The public
table is a semantic projection, not a fresh private-ROM check in CI. Its28
concrete target/neighbor accesses, two indexed bitmap candidates and four
memory-context hazards are reported separately from unknown indirect contexts.

## Upstream sources and first missing edges

For0217.3 a concrete conditional code-bit chain exists:
`5F66 LCB A,PROGRAM60EC →5F6A SLLB A →5F6B MB off0217.3,C`.
LCB supplies AL, the shift supplies oldAL.bit7 to CF, and MB replaces only the
selected DATA bit. The private original PROGRAM source is authenticated; its
raw byte is not published. This establishes a conditional bit relationship,
not ownership of the other buffer bits or an actual generation. The first
missing bridge is a genuine same-machine path through this helper and retention
of its0217 generation until0408 or5C35, followed by preservation to064C.
The conditional helper callers27D0/4069 do not by themselves establish scheduling
or ordering with either interrupt-entry copy root.

For011B.7 there are separate code-zero and indexed candidates. After CLR291B,
conditional ST291C can write zero to011A/011B with USP0180 and signed displacement
-66; ST2920 can write zero to0212/0213 on page0200. The DP03F3 read, preceding
comparison/carry predicate and actual caller history remain obligations.
Neither a known zero formula nor a matching final number is an observed writer.

Bitmap helper5B7E..5B8E uses SUBB on AL with retained AH, code divisor8,16-bit
DIVB quotient, X1 addressing and the remainder-selected bit. Incoming invented
context must already have DD0; SUBB retains DD and does not establish DD0.
An invented
word0010 selects byte index1/bit7, hence011B.7 or0213.7. Invented002C selects
index5/bit3, hence011F.3 or0217.3. The ordinary reviewed PROGRAM6F55 table domain
does not provide the002C input; arbitrary host selection is not allowed.
Other callers and incoming A/r6/table ownership still need their own history.

Primary SBR has an editorial conflict: description says SET1 while the Function
row indicates bit←0. Address selection, AL[2:0] bit selection and old-bit ZF
are separate reviewed facts. The historical software OR/set interpretation is
not independent primary closure of write direction. No new native source is
established through that ambiguity, and no production semantics are corrected.

Startup word-clear2710 is a conditional zero source only with the bounded
DP walker and initial call context. RAM-test exchanges5C68/5C6C and NMI0048
restoration are possible source/preservation hazards with pointer and saved-value
obligations. They are not silently treated as benign or as actual overwrites.
Explicit DAGs retain first missing obligations for all these source families.

Historical limiter inputs remain `HistoricalTechnicalInputOnly_NotNativeProducer`.
M1l/M1m snapshots, M2n initial fixed-source application, M2o control masks and
M2ag historical generation are not actual writers in the current063B machine.

## Bounded caller reachability and dominance

The reused M2aj graph has317 nodes. It summarizes CAL038A as a returning call;
the missing helper body is not evidence of unreachability. Expanding only the
11 exact helper sites5C2B..5C3F produces a328-node conservative graph with a
conditional matching RT5C3F→038D. Unknown callees/returns remain explicit.

| Selected root | Structurally dominating pair for reached064C/064F | Qualification |
|---|---|---|
|0379 INT1|5C2D,5C35|Genuine entry/frame, setup and helper return required|
|03ED serial RX/BRG|0400,0408|Genuine entry/frame and later predicates required|
|063B current M2bz|None|All earlier copy writers bypassed|

There is no individual writer that dominates across the union of these roots.
Structural dominance does not establish source values, actual writer events or
retention through unknown calls, frames and indirect writes. Reader reachability
is conditional: INT1 may exit through069A/RTI without reaching the reader;
serial040E may bypass063B/064C through065F. Root-specific branch predicates and
conservative paths are retained in canonical evidence. Syntactic graph edges
do not prove feasibility of every correlated predicate or actual IRQ delivery.

Earlier CAL0611 or0635 can return and set012A.3 at0614 or0638. These calls are
mutually exclusive in one bounded invocation. The no-earlier-call route through
062C clearsbit3. With a merely hypothetical owned011F.3=1, old012A.3=0 leads
to064C→065F→0662→STOP0664; oldbit3=1 leads toSTOP0667. The current M2bz low-bit
history cannot be substituted into an earlier-caller source history. Frozen
M2ca route definitions remain unchanged.

## Aliases, frame obligations and same-machine bridge

DATA and system-stack word addresses clear their low bit. Page and local-bank aliases, all eight SCB
pointing-register storage banks, USP displacements and unknown pointed values
are separate obligations. LRB0023 local RAM can overlap011A..011F; LRB0042 can
overlap0212..0217. A disjoint pointing-storage bank does not make its pointers
or indirect accesses disjoint.

CAL writes at even(oldSSP). The reviewed four-word interrupt-frame footprint
creates additional possible collisions with target or buffer words; nested
frames and actual incoming SSP remain unknown. The technical CAL063B frame at
SSP07FE is disjoint, but it does not establish an enclosing ISR frame. A helper
frame can itself overlap its destination/source words and invalidate its own
return obligation. Unknown accumulator STACK mode is not silently excluded.

Every same-value storage write has a new local generation. Bit RMW may retain
neighbor semantic lineage only if the old source was owned. A word overwrite,
indirect alias or unknown frame overlap can invalidate retention even when the
final numerical branch is unchanged. No old event index, write ordinal, machine
identity or generation is imported into the new scope.

The actual same-machine bridge remains blocked. The smallest useful evidence
frontier is: authenticate the selected source-producer event and inputs; choose
one genuine0379/03ED history with completed required returns; bind the matching
copy pair and exact page/pointers; establish SSP/frame safety and no intervening
overlap; retain the source-consistent012A context through CAL063B/RT5688 and the
selector suffix to064C, and to064F if reached. A full-ECU emulator is not the
first proposed action. None of these events is newly executed by M2cb.

## Static model, tests and delivery boundaries

Twelve curated invented ledgers track per-bit numeric knowledge, semantic source
tokens, write chronology and storage generations. An independently written
immutable bit-plane oracle compares complete states and effects. The model
does not obtain expected values from Rust output. Separately, fixed-point
dominators check the bounded graph, and alias arithmetic is checked independently.
Twenty-nine negative requirement categories distinguish input refusals from
fabricated expected-effect and contract-identity refusals; they are not
production CPU refusals. Static exact-ROM extents are counted only in private
local source receipts, not in public CI or invented case counts.

Canonical evidence contains the full source inventory, lineage DAGs, caller CFG,
alias obligations, missing-evidence frontier and all12 invented symbolic records.
Local/Ubuntu/Windows comparisons use complete decompressed bytes without dropping
provenance fields. Runtime canonical comparison is NotApplicable: actual new
CPU/ROM executions and retirements remain0.

M2cb has a separate17-file reviewed additions projection over all1,133 accepted
M2ca raw blobs. Frozen M2ca pins/modules are unchanged. One literal approval is
provided only after independent review; the guard cannot silently approve its
own changed payload. Only the exact workflow projection and finite additions
select the router plus two static OS jobs. Unknown/runtime/dependency/old-source
changes and routing errors require full historical QA. The17 historical logical
checks remain protected; when the research lane runs, they are NotRun and are
never called a new17/17 PASS. Private ROM/evidence is not required by CI.

Two documented preservation exceptions are inherited: historical generated-runner
loss and the separately authorized external Python tooling change. No third
exception is admitted. Old expected fingerprints/reports remain unchanged;
`StrictHistoricalPreservationPass=false`, new unauthorized differences must0.
Source and preservation receipts stay local, with the final Ukrainian report
written after CI/comparison/seal.

ActualHardwareEcuExecutionNotObserved; RecoveredFullEcuSchedulerNotEstablished;
EnclosingIRQFrameNotEstablished; PhysicalNativeStackSafetyNotEstablished;
InitialDATA011FNativeOwnerNotEstablished; InitialDATA011BNativeOwnerNotEstablished;
ActualNewBranch064CExecutionNotRun; IRQDeliveryNotInjected; TimerEvolutionNotModeled;
PhysicalTimingEquivalenceNotEstablished; ElectricalOutputNotObserved;
TRNSIT0657NotExecuted; CAL0664NotExecuted; Producer56BENotExecutedInM2cb;
Return0667NotExecuted; NativeNextEventSelectorHandoffNotEstablished;
FullNativeDownstreamRejoinNotEstablished; SafeROMPlacementNotEstablished;
TargetProgramEquivalenceNotEstablished; FirmwareIntegrationNotEstablished;
FirmwareReady=false. Stop after delivery; no M2cc, GUI, firmware or hardware.
