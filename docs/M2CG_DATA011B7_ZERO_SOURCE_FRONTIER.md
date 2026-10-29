# M2cg: DATA011B.7 zero-producer source frontier

Research-Only result:
**CONDITIONAL_DATA011B7_ZERO_PRODUCER_ESTABLISHED / EXECUTION_BLOCKED**.
No original-ROM CPU/Bus execution, IRQ delivery, peripheral model or firmware
output is introduced. FirmwareReady remains false. Static source constraints
are separate from current-machine writers and preserved native generations.

The Git base is accepted M2ce commit
`bb781647d553ee321ae9ac75732e06736fb01fbb`,1195 raw source files with fingerprint
`00f593f888b7b8eee8e4d5b4ba22e87d3692f945b806b64cd7c639c8266f3a5b`.
M2cf is a completed private NO_NEW research record, with no additional Git base.
Its WDT result is unchanged; no M2cf web search is resumed here.

## What is inherited and what is new

M2cb already established CLR291B and the four word-store candidates, source0213
to target011B copies, little-endian mapping, same-value generations, the328-node
conditional receiver graph, aliases and the SBR direction conflict. Those are
reused facts, not new M2cg discoveries. The private source audit reuses the
accepted11499 listed extents; no full disassembly or historical runtime is repeated.

New source relationships narrow M2cb's `OwnedDP03F3AndReadValue` obligation:

- DATA03F1 command and DATA03F3 flag have specific conditional writers0279 and
  0269 from separate DATA0055 reads under code-owned LRB007E.
- A finite four-invocation packet constraint explains compatible local state
  positions, checksum and ready0356.7. Its hardware history remains unknown.
- The command21 path supplies a C8-free predicate chain to CLR291B, including
  mode0356.1, ready0356.7 and the current DATA03F3.bit0.
- Joining whole-word zero with receiver predicates and copy dominance exposes
  additional retention and IRQ-input conditions, rather than merely listing writers.

The existing original ROM/listing/source identities are verified privately.
Public calculations consume semantic projections and invented constraints only;
private exact-extent checks at public CI invocation remain zero.

## Source handler and four distinct reads

The standard architectural vector000A refers to serial **transmitting-ready**
IRQL.1/wordbit1 and the verified vector target is0213. Reading SRBUF in this
handler does not rename its interrupt cause to serial receiving-ready.
Actual pending, IE/MIE/priority, entry dispatch and safe IRQ frames are unobserved.

Reached0217 writes the PSW literal0102, conditionally selecting SCB2; this is
not an observed full PSW readback with reserved bits. Reached021C writes
LRB007E, selecting local03F0. Under this retained context r1=DATA03F1,
r3=DATA03F3, r5=DATA03F5, r6=DATA03F6 and r7=DATA03F7.
The standard SFR map names DATA0055 SRBUF, read-only byte8, reset content undefined.
Actual ASIC applicability, buffer contents, read completion and side effects
remain separate obligations. DATA03F1/03F3 are external under the standard201
RAM map and internal under207; neither map identifies the ECU.

One bounded, explicitly hypothetical software-compatible packet has header
H=21h, length L=4, an odd flag byte F, and checksum K such that
`(H+L+F+K) mod256 =0`:

| Distinct invocation/read | Conditional local effect |
| --- | --- |
| Header0277 | With incoming r7=0, store0279 writes r1;027A saves checksum accumulator r6;027B sets r5=1;0270 makes r7=2. |
| Length027F | At r5=1, store0281 writes r2=L; the0282/026D path updates r6 and026F gives r5=2. |
| Flag0262 | At r5=2 and r2=4, branch0260 does not select checksum; CMP0264/JNE0267 permits0269 to write r3=F. The sum and position advance. |
| Checksum0284 | At r5=3, r5+1 equals r2=4. ADDB0286 must give zero and0287 must not reject; saved header class20 permits0290 to set0356.7 and0293 to clear r7. |

These are four different read identities and four conditional handler
invocations, not one reused sample. Initial r7=0 needs its own owner: prior0293
or a conditional startup clear of03F6/03F7 is a candidate, not an observed source.
Length3 can select checksum before0269 and cannot manufacture a new flag owner.
The finite relation is not a full serial protocol, scheduler or CPU emulator.

Actual H/L/F/K values, event indices, machine IDs, native write ordinals and
IRQ frames remain unknown. An invented test vector is never a native owner.

## Exact predicate before the four zero stores

| PC or sequence | Required relationship |
| --- | --- |
|28AE DP0356,28B1 MB C,[DP].1,28B3 JLT|Current mode0356.1 must1; otherwise28B5 jumps2997. Its current owner is not supplied by a host flag. |
|28B8 DP0356,28BB RB bit7,28BD JNE|Current ready0356.7 must1; the read/clear creates a new status storage generation. Otherwise28BF jumps2997. |
|28C2 DP03F1,28C5 LB,28C6 CMPB#20,28C8 JNE|Command21 takes the unequal path to28E1. |
|28E1 CMPB#30,28E3 JLT|Command21 is below30 and reaches2910, bypassing the unresolved C8/JGT at28E7. No C8 semantics are selected or repaired. |
|2910 CMPB#21,2912 JNE|Equality is required; the unequal path returns through28BF. |
|2914 DP03F3,2917 LB,2918 SRLB|LB establishes DD0. SRLB moves the current byte's bit0 to CF; AH/ZF/HC/DD are retained by SRLB. |
|2919 JGE|GE uses CF0: even03F3 takes2963; odd03F3 falls through to291B. There is no comparison instruction at2918. |

Thus a retained startup zero03F3 would **bypass** CLR291B. It cannot serve as
the favorable source for this zero block. The odd source requires a later
independently owned writer/read generation, with0269 a concrete candidate.

Reached CLR291B creates word A=0, DD1 and ZF1, retaining CF/HC. It kills the
old AL/AH values. The four stores291C,291E,2920,2922 are sequential and have no
intervening listed control transfer or A/DD mutation. Under ordinary accumulator
mode, matching context and no asynchronous interference, all four receive that
same code-zero semantic source:

- 291C: USP0180−66h =011A; the full word writes011A/011B.
- 291E: USP0180−64h =011C; the full word writes011C/011D.
- 2920: page0200+12h =0212; the full word writes0212/0213.
- 2922: page0200+14h =0214; the full word writes0214/0215.

Each store creates a fresh storage generation for both bytes, including a
same-value store. Conditional code-zero ownership is not actual CLR/ST execution.
Cold producer SCB0/LRB0041/USP0180 candidates24FF/2744/2754 remain a separate
caller-history hypothesis. They are not borrowed from handler/receiver SCB2;
other equivalent contexts require their own proof. DD1 at stores comes from
CLR, not from a listing annotation or an assumed incoming DD value.

## Routes, latest storage writer and reader gate

Route A is291B→291C→011B→064F with uninterrupted target retention.
Route B is291B→2920→0213→03FE/0400 or5C2B/5C2D→011B→064F.
For either copy, USP0280, page0100/LRB0021, owned SCB-selected pointers,
completed word load/store and retention are separate conditions.

M2cb's conditional dominance has a stronger joined consequence: when a reached
064F belongs to the reviewed0379/03ED receiver route after291C, copy5C2D/0400
replaces the target storage generation. The latest storage writer cannot still
be291C. A same-zero copy can retain CLR's semantic owner only through an owned,
preserved2920 source word. This is not global impossibility of every unreviewed
direct route, nor permission to import a writer into the technical063B entry.

For INT1, copying the whole zero word also makes011A.7=0 and011A.3=0.
JBS0390 and0393 therefore fall through to RB0396 IRQH.1. JEQ0399 needs the
old IRQH.1 value0 to continue03A5/03A8; value1 bypasses the reader via069A.
This is wordbit9, Timer2 capture-event/real-time-output match, vector001A.
It is distinct from source IRQL.1/wordbit1, receiver INT1/wordbit15/vector0026
and serial RX/BRG/wordbit3/vector000E. None of these factors is injected.

The ordinary reviewed post-zero prefix reaches295A→79CC and the first
unproved CAL79D5→5EE3, requiring a matching RT5EF0→79D8. Its C8 site5EEE,
frame preservation and completion remain unknown. This is an ordinary-path
frontier, not proof that every possible IRQ transition must occur after that call.
Later LB2966 reads03F3 again; SRLB2967/2968 and JGE2969 concern bit1 of that
new read. They cannot reuse2917's byte, bit0 or read generation without retention proof.

Reader064F additionally requires an independently owned DATA011F.3=0 at064C.
The M2cc PROGRAM60EC→0217.3→011F.3 relationship remains conditional and
cannot be substituted with default zero, old A5 or the0213 source. DATA012A.3
must retain its own0611/0635-return or no-earlier-call062C history; the technical
M2bz value cannot be spliced into a different enclosing caller.

If conditionally read011B.7=0, JBS064F selects0652; a value1 selects065F. Neither
the reader nor these successor instructions executes in M2cg.

## Preservation and minimal missing frontier

Unknown DP/USP/X1/X2 aliases, LRB0023/0042 locals, CAL/four-word/nested IRQ
frames, startup2710, RAM-test exchanges, NMI0048, bitmap writers and accumulator
STACK applicability remain hazards. Unknown alias is not an observed overwrite,
but it does not discharge strict preservation. SBR's SET1/function-bit0 primary
conflict and C8's predicate conflict remain unchanged.

Route A first needs owned mode/ready/header/flag sources and the correct selected
USP, then the291C word generation and a reader history without an unaccounted
overlap. Through the known receiver roots, the dominating copy prevents an
untouched291C storage claim. Route B additionally needs preserved0212/0213,
a genuine chosen receiver transition/frame, completed copy and target retention.
Serial avoids the extra038A copy-helper CAL/RT, but that alone does not establish
a globally preferable native route. Both still need the separate011F.3 gate.

The smallest next source task is to bind one genuine0213 entry/return and its
DATA0055 reads, r7/r5/r2/r6 states and03F1/03F3/0356 generations to one retained
history before28AE. Frame and event evidence is required; this document grants
no new execution or IRQ experiment. M2cf WDT24F4 and reset applicability remain
independent unresolved earlier hardware constraints.

## Static verification and delivery scope

A small invented-only corpus and independently authored oracle compare complete
constraint, value/owner, generation and refusal results. No expected hardware
behavior is obtained from Rust. Full decompressed canonical comparison includes
all unknown/source fields and remains separate from CPU runtime comparison.
Case coverage is limited to the frozen37 invented fixtures and reviewed named
mutations. Source/effect metadata retains native owner/generation fields as
unknown and labels at-write modeled semantic tokens separately.

The separate M2cg source projection permits exactly14 new text files plus one
reviewed workflow overlay over the complete1195-file M2ce base. The accepted
M2ce approval modules remain immutable. Independent content approval precedes
the new literal pin. Unknown/runtime/old-source changes require full historical
QA; all17 logical historical checks remain in that protected lane.

The bounded lane consists of router, Ubuntu static and Windows static.
Historical17 is NotRun when that lane runs; it is not a new17/17 PASS.
Private ROM, listing, source verification and manufacturer pages remain local.
Two inherited preservation exceptions remain explicit and
StrictHistoricalPreservationPass=false; no historical expected SHA is rewritten.

ActualCpuExecutions=0; ActualOriginalRomExecutions=0; ActualIrqDeliveries=0;
ActualBranch064CExecuted=false; ActualBranch064FExecuted=false.
Native DATA011F.3/011B.7 current ownership, physical stack safety, recovered
scheduler, downstream rejoin, target equivalence and firmware integration remain
unestablished. Stop after delivery; no M2ch, GUI, firmware or hardware work.
