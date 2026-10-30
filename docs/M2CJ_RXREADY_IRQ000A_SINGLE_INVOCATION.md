# M2cj: RX-ready pending and one Flag-invocation source frontier

Research-Only: **CONDITIONAL_RXREADY_FLAG_INVOCATION_FEASIBILITY_ESTABLISHED /
EXECUTION_BLOCKED**. The new result joins documented receive prerequisites and
specific software-clear/mask histories to one previously reviewed Flag path.
It establishes no actual received byte, IRQ, frame, instruction retirement or
current native RAM owner. FirmwareReady=false.

The exact accepted M2ci base is `08df0e3c9e8e90a7b97fc99280b4cb5a5559ca43`:
1231 raw Git sources, fingerprint
`ca67f7adb19582af62b286684d9296b9396c6b0b66c569b65f676564e69b8944`.
Old M2ci/M2ch/M2cg contracts, oracles, reports and approval pins remain frozen.
Their erroneous historical TX000A descriptions are not current authority.

## New versus inherited evidence

| Evidence | Inherited result | New M2cj relationship |
|---|---|---|
|Allocation|M2ci corrected RX000A/bit1, RQSRRDY/IESRRDY|Used with the same User body's receive-generation text; actual ASIC still unknown|
|IE polarity|165/168 support set1;167 says set0|167 is an acceptance condition, not a post-entry description;169 depicts pending before later enables|
|Serial source|SRBUF0055 is a read-only byte; actual source unknown|Eligible receive completion transfers data and creates a request; receiver permission and multiprocessor filtering matter|
|Retention|No observed current SRBUF owner|Unread content can be replaced on overrun; ignored MPC data does not replace it|
|Masks|Literal FA/F8 pairs known|54EA IRQ clear precedes54F0 IE; mode0217.2, current IE and both shadows must agree at3E81 checks|
|Flag/frame|Exact Flag path, five writes, frame/RTI roles already reviewed|Those facts are joined to the newly constrained receive/pending predecessors, not rerun or rediscovered|

The novelty preflight and independent primary review preceded the new verifier.
All documents were already local; no new manufacturer edition was acquired.
The manufacturer body is the retained incomplete MSM66201/207 User scan archive,
SHA-256 `f061cb5bcbd1804699fb60b543c425646fbb15b939c9bc51b24edbb4da4c6ddf`.
The selected original images pass their historical member CRC and current SHA
checks. Seven other ZIP members fail CRC; the archive is not repaired or promoted
to a complete, edition-authenticated manual. Printed132..147 is absent locally;
the sought receive-operation text is not acquired and its exact allocation
within that gap is unknown. Damaged122/123 is not substituted.

## A. IE polarity and pending versus delivery

Complete printed164..169 were visually reviewed. Section17.2(2) on165 explicitly
describes IE1 enabling and IE0 disabling a corresponding factor. Fig17-2 on168
uses non-inverting IRQ/IE gating, priority selection and MIE. Examples2/3 on169
illustrate a request preceding later IE/MIE enable, with transition afterwards.
They support separation of pending generation and interrupt delivery; they do
not establish an unlimited latch lifetime or an observed receive history.

Printed167's opening paragraph nevertheless says corresponding IE0 in the
condition for starting maskable processing. Its placement and subsequent steps
do not explain it as post-entry IE clearing: the list clears serviced IRQ and
MIE, while165 explicitly retains IE. No negation, other interrupt class or local
exception resolves that wording. No erratum is asserted.

The result remains **IEPolarityEvidenceFavorsSet1ButConflictRetained** and
ApplicableEcuIEPolarityNotEstablished. Both polarity hypotheses are retained in
invented mask controls. Neither firmware mask convenience nor one isolated
sentence establishes physical polarity. User Table17-1 supplies bit1 symbols;
the Instruction Manual's allocation table is not assigned those fields alone.

## B. New receive-generation and retention restrictions

The retained User body, printed126..131, supplies these qualified rules:

- SRCON at DATA0054 has receiver permit SRREN bit7. It resets0 and mode changes
  require reception disabled. Synchronous-master reception clears permission
  after one frame; other modes retain it. A reset value is not current ownership.
- Section12.1(5)/(6), printed128: a completed receiving operation transfers the
  shift-register data to SRBUF and generates RX READY. The shift register is not
  software-accessible; no host-supplied F substitutes for that transfer.
- In UART/synchronous multiprocessor mode, enabled filtering and received MPC0
  cause ignored data: neither a new SRBUF value nor a receiving request follows.
  SRCON bit2's mode-dependent role is separate from software DATA0217.2.
- SRBUF retains content until an eligible replacement. Printed130 says unread
  prior data can cause overrun while new data still enters SRBUF. Unread status
  therefore does not prove old-byte retention. Sticky SRSTAT error state remains
  unknown without its prior owner; a new overrun condition is not a cleared or
  final OERR bit. Ignored-MPC/error interaction is not invented.

These rules narrow the possible producer of the byte read at0262. They do not
observe such a producer. A qualifying transfer must precede that distinct read,
with no intervening accepted replacement if the earlier generation is claimed.
After a completed read, a later SRBUF replacement does not by itself rewrite AL;
an interrupt or alias effect still needs separate accounting.

Under the source-qualified interrupt chapter, entry acknowledges the serviced
factor and clears MIE while retaining IE. The bit1 join is conditional on that
same User profile. Reading0055 is not established as IRQ read-to-clear; automatic
reassertion and set/clear collision priority remain unknown. A later eligible
receive can generate another request according to the completion rule, but this
does not prove every re-entry needs a fresh receive or that unread data reasserts.

## C. Exact software shadow/mode histories

| Conditional chain | Direct IE writer | F8 writer | FA writer | Software mode effect |
|---|---|---|---|---|
|PairA switch|3F14:2BAB|3F16:2BAB|3F18:02A0|3F1D clears DATA0217.2|
|PairB switch|3F28:A9A3|3F2A:A9A3|3F2C:00A0|3F31 sets DATA0217.2|
|Initial pairA|54F0:2BAB|54E5:2BAB|54DD:02A0|No mode writer in this closed fragment|

One3EEA..3F45 pass selects mutually exclusive switch blocks, or makes no switch.
The threshold source at3F05 needs USP0180 and compares DATA01AD with29h. CF
survives ANDB PSWH,FE at3F09 and feeds JLT3F0C; ZF is affected and is not claimed
preserved. Off-page mode/flag operands need page0200 and owned pointing context.
Listing annotations are not observations of LRB/SCB/USP at those sites.

In the initial chain54DD..54F0, A retains2BAB across the word CLR IRQ at54EA.
This clear targets DATA0018/0019 before the later IE write. If that software
clear completes, an old pre-clear request generation alone cannot explain a
later RX entry: post-clear generation, concurrent reassertion or another
independently justified writer is needed. Hardware set-versus-clear priority is
unknown. This is not a hardware acknowledgement and does not prove that the
initial chain ran before the current handler.

54F2 branches to3E81, whose checks compare F8 at3E90, IE at3E95 and FA at3E9B
against the software mode selected at3E87. In a closed, uninterfered completion
of54DD, pairA agrees only with mode0217.2=0. This is a consistency obligation,
not a current native mode/mask generation. All actual owners remain unknown.

For the set1 hypothesis, both FA masks disable RXbit1 and both F8 masks enable
it; TXbit2 is0 in all four words. The set0 hypothesis reverses these enable
interpretations. Mode-switch direct IE writes precede shadow updates, so the
pair cannot be treated as one atomic native write. MIE windows at3F02..3F09 and
after3F40 before IE3F45 require separate pending/nesting proof. IE/MIE0 does not
exclude NMI. Indirect/local/stack aliases and intervening writers remain open.

## D. One frame and matching return

One invocation needs an independently owned SSP S and safe physical storage:
PC at even(S), A at even(S-2), LRB at even(S-4), PSW at even(S-6), postSSP=S-8.
RTI pops PSW,LRB,A,PC and restores numeric SSP. Its saved foreground PC is not
029C, which is the RTI instruction address, and is not host PC28AE.

The inherited even(S)=03F6 example overlaps the entire03F0..03F7 parser bank.
Numeric non-overlap in an invented control does not establish writable physical
RAM, source-owned SSP or frame integrity. Unknown S proves no safety. Four
actual saved word generations, nested IRQ/NMI, mapped-register and pointer-bank
aliases, physical SF and the actual memory map remain unknown.

0217's PSW literal0102 is not automatically its full readback; it conditionally
selects SCB2/MIE1, while021C's LRB007E gives local03F0 and page0300. Restoring
SCB selects a pointing bank, not its earlier RAM contents. RTI does not restore
IE:0295 reads a distinct current F8 generation,0297 clears MIE,029A writes IE.
The active-MIE interval inside this handler therefore needs its own proof.

## E. Single Flag source transformation

The reviewed28-site conditional path is the inherited seven-site prefix followed
by the Flag dispatch, one0262 read,0269 byte store and029C RTI. It is not an
observed trace or a retirement count. Required mode0356.1=1, old0356.6=0,
r7=2/r5=2/r2=4 and r6 source derive only from separately inherited conditional
Header/Length relationships; those invocations are not executed or host-seeded.

LB0262 reads8-bit DATA0055 into AL, DD0, with ordinary AH retention qualified by
unknown physical SF. CMPB0264 compares **r5 with2**, preserving AL/AH; CF0/ZF1
make JNE0267 fall through. STB0269 writes AL to r3=DATA03F3, one byte. Even F
can reach this writer; oddness belongs only to the later2918/2919 consumer.

The five selected persistent effects remain separate and ordered:0222 status
RMW,0269 r3=F,026D r6+=F,026F r5=3,0270 r7=2. Same-value writes create fresh
storage generations. The Flag path does not set ready0356.7. The selected tail
has no further03F3 store, but actual retention requires an intact matching frame,
physical retained RAM and no nested, foreground, next-packet or alias overwrite.
No parser28AE, CLR291B, DATA011B/011F reader or064F branch is executed here.

## F. Missing evidence frontier and impact

The obligation DAG keeps manufacturer source, conditional software effects,
actual events and unknown native generations distinct. Its earliest actual gate
is still exact ECU silicon/peripheral applicability. Conditional on applicability,
one must bind receiver configuration and an eligible completion to a distinct
current SRBUF generation, plus pending after any relevant54EA clear, current
IE/MIE/priority, safe owned entry frame and the retained Header/Length context.
None of these actual owners is filled with zero or an invented observation.

One useful next documentary item is authenticated receive-operation text not
acquired from this User Manual, with printed132..147 still missing: specifically the rule
for RQSRRDYbit1 lifetime, acknowledgement by an SRBUF0055 read, reassertion after
entry, and software-clear/hardware-set ordering. Its exact subsection number
and manufacturer document ID are not known and are not fabricated. A title/
edition linkage is needed; no physical experiment or manufacturer message is
authorized by this request. A package-to-applicable-table OEM/manufacturer
cross-reference remains a separate prerequisite for physical ECU applicability.

New facts narrow RX producer/permit/retention and mask-generation dependencies.
They do not establish ready0356.7, actual03F3 ownership, CLR291B, DATA011B.7,
DATA011F.3 or064F. Historical results stay frozen; new projections supersede no
old source hashes. NewManufacturerDocuments=0; ActualCpuExecutions=0;
ActualOriginalRomExecutions=0; ActualIRQDeliveries=0; ActualRTIExecutions=0.

## Verification and delivery scope

The finite verifier compares complete documentary findings and19 invented
controls against a separately frozen reference:8 receive implications,4 polarity
hypotheses,4 pending-order controls and3 one-frame geometries. Together with4
source findings these form23 static canonical records. No serial receiver,
peripheral scheduler, CPU/Bus instance, host IRQ/PC injection or actual input
byte is constructed. The prescribed negative controls refuse unsupported
authority, context, ownership and runtime claims; they are not hardware tests.

The11-source addition plus independently reviewed workflow overlay preserves
the1231-source base and all historical execution steps. Unknown, runtime or
inherited-source changes require full historical QA. The bounded lane has three
actual research jobs; Historical17 is NotRun, never a new17/17 PASS. Full
canonical bytes, including all unknown/source fields, must match on both OSes.

InheritedAuthorizedExceptions=3; NewAuthorizedExceptions=0;
StrictHistoricalPreservationPass=false. Scoped preservation reuses authenticated
prior hashes with unchanged metadata and freshly hashes the selected new
dependencies; it is not a fresh whole-storage audit. Privacy and exact current
source identities remain separate gates. FirmwareReady=false.

Stop after M2cj. No M2ck, IRQ/RTI execution, reset/fullboot, serial simulation,
GUI, hardware, ROM modification, firmware compilation or flashing is admitted.
