# M2ck: RX READY acknowledgement, reassertion and manufacturer sources

**RXREADY_SOURCE_CONFLICT_UNRESOLVED / EXECUTION_BLOCKED.**

Research-Only. The complete, applicable receive-operation source needed to settle
RQSRRDY acknowledgement and reassertion was not acquired. A Japanese manufacturer
specification was acquired and independently reviewed, but it supplies register
inventory and electrical timing, not the missing request-latch rules. This is a
bounded documentary result, not proof that no such documentation exists.

The accepted M2cj base is `b2f5331a077a25a2bf29331f38a6b6041792cd55`.
The M2ck branch is `codex/p28-word0196-rxready-acknowledgement-m2ck`.
The inherited [M2cj source frontier](M2CJ_RXREADY_IRQ000A_SINGLE_INVOCATION.md)
remains conditional. No production CPU, Bus, decoder, executor, peripheral,
admission or GUI behavior is changed by this documentary package.

## Acquired sources and authentication limits

| Source | Identity and pagination | Actual contribution |
|---|---|---|
| [Japanese OKI specification](https://datasheet.datasheetarchive.com/originals/library/Datasheets-DAV1/DSADA0015905.pdf) | `J2E1027-27-Y3`, cover creation January 1998, previous creation November 1996; 30 PDF pages, printed `1/30` through `30/30` | Newly acquired document identity; standard MSM66201/66P201/66207/66P207 device coverage, registers and external timing |
| [English OKI specification mirror](https://downloads.laboratoryb.org/insight/documents/OKI/MSM66201.pdf) | `E2E1027-27-Y4`, January 1998, previous November 1996; 30 PDF pages, printed `1/30` through `30/30` | Newly acquired raw PDF container of an already-known manufacturer edition; not another independent receive-operation authority |
| [Retained incomplete User scan](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/66207usersmanual_incomplete.zip) | MSM66201/207 manufacturer body; title leaf, document ID, edition and date not authenticated | Existing receive-generation text and interrupt-controller chapter, with the known IE conflict |
| [Instruction Manual](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/Oki_66201_Instruction_Manual.pdf) | MSM66201 Instruction Manual, First Edition, September 1991 | Existing instruction semantics and standard vector allocation; no newly acquired receive-latch rule |

The Japanese cover reads `MSM66201/66P201/66207/66P207`, with subtitle
`10ビットA/Dコンバータ内蔵16ビットマイクロコントローラ` and publisher
`OKI 電子デバイス`. Its original 602,102 bytes have SHA-256
`9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a`.
All 30 complete pages were rendered and visually reviewed independently of the
acquirer. PDF index and printed page numerator coincide; no extra advertisement
page is counted as a manufacturer page. The document is a specification sheet,
not a full hardware User Manual or an erratum.

The Japanese PDF opens normally without a password prompt, although its
encrypted flag is present. Its page renders are readable; a PDF parser reports
wrong-pointing-object warnings and its extracted font text contains encoding
errors. The original bytes were preserved. Successful rendering and a matched
acquisition hash do not establish perfect PDF conformance, an official
manufacturer hash or a signed chain of custody. Third-party PDF metadata dated
2011 is not the manufacturer publication date.

The English mirror is 583,437 bytes, SHA-256
`fe18068dc496a03f5b6bdefe5818741e572cb7626acfb3d1df427547f8b3264b`.
Its cover and complete relevant register pages were visually authenticated.
The different container hash is not a new manufacturer edition. Japanese Y3
and English Y4 have the same displayed month/year labels; the differing language
IDs do not establish a chronological revision bridge or an erratum for the
incomplete User body.

The retained User ZIP remains 16,203,609 bytes, SHA-256
`f061cb5bcbd1804699fb60b543c425646fbb15b939c9bc51b24edbb4da4c6ddf`.
A bounded integrity check again found 59 readable CRC-valid file members and
seven CRC failures. The archive was neither repaired nor promoted to a complete
edition-authenticated manual. Printed132-147 remain absent; damaged122/123 are
not substituted. The exact missing receive subsection and the page containing
any acknowledgement rule are unknown.

## What the new specification establishes

The Japanese specification has the following complete page boundaries:

- Pages1-2: overview, standard parts, interrupt counts and package availability.
- Pages3-8: block diagram, pinouts and pin descriptions.
- Page9: architectural register inventory, including PSW MIE bit11.
- Pages10-12: SFR inventory; no per-source acknowledgement description.
- Pages13-16: addressing modes; page17: standard memory maps.
- Pages18-21: electrical and external-memory timing requirements.
- Pages22-23: serial external clock/data setup and hold requirements.
- Pages24-26: A/D characteristics; pages27-30: package dimensions.

Page10 lists IRQ at DATA0018/0019 and IE at DATA001A/001B as 8/16-bit R/W
registers with reset bytes00. Page11 lists SRCON0054 as an 8-bit R/W register
reset00, SRBUF0055 as an 8-bit read-only register with undefined reset value,
and SRSTAT0056 as an 8-bit R/W register resetF0. These agree with the known
standard-part inventory. A read-only access designation neither establishes
nor excludes a read side effect on a separate interrupt-request register.

Serial pages22-23 describe SCK, SDOUT/TXD and SDIN/RXD electrical relationships.
They do not depict an RX READY latch, SRBUF-read acknowledgement or arbitration
between hardware request set and software clear. The document supplies no
RQSRRDY/IESRRDY bit1 allocation table, receive-operation narrative, IE-factor
polarity rule, or correction of the User body's printed167 wording.

Both specifications directly name the standard parts. Neither identifies the
actual ECU silicon, customer ASIC/mask or applicable peripheral revision. Their
standard memory maps cannot supply an actual SSP or safe native frame owner.

## Bounded search and rejected interpretations

The search included exact part numbers, receive/request symbols, manual titles,
Japanese document identifiers, manufacturer/successor documentation routes,
historical attachment locators, technical archives, data-book indexes and
Internet Archive catalog records. Acquired indexes and candidate PDFs were
retained with URL, response status, size and hash receipts.

One independent search lane recorded 28 web queries and 19 direct GET attempts,
including five initial restricted-network DNS failures and 14 successful GETs
after authorized access. Its archive queries found known specification mirrors,
older data books or unrelated catalog matches. A separate datasheet-source
search acquired the Japanese document above. These lane counts are not summed
into a claimed exhaustive survey. OCR locators for older data books are only
navigation aids; their unacquired scans are not new semantic authority.

An empty historical URL query is limited to that selector and snapshot. Network
errors, inaccessible hosts and distributor labels such as "User Manual" are
not evidence that an applicable manual does not exist. Search snippets,
cross-family instruction compatibility, third-party pseudocode and a new PDF
container are not manufacturer proof of this peripheral's behavior. No
manufacturer correspondence, new applicable erratum or complete authenticated
receive-operation chapter was acquired. No vendor message was sent.

## RX generation, content and acknowledgement

The following claims remain qualified by the retained User body and its
unresolved edition/applicability:

| Question | Documentary result | Limit |
|---|---|---|
| Receiver permission | Printed126-127: SRCON0054 bit7 SRREN permits reception when1; mode changes require reception disabled | Reset00 is not a current owner; receiver permission is distinct from IE/MIE |
| Receive completion | Printed128 sections12.1(5)/(6): completion transfers the receive shift register to SRBUF and generates RX READY | Actual configuration, receive completion, byte and current generation are unobserved |
| MPC filtering | UART/synchronous multiprocessor mode with SRMPC1 and received MPC0 ignores data: no SRBUF update and no request | Software DATA0217.2 is a different field; no actual mode is inferred |
| Unread prior SRBUF | Printed130: overrun can be raised while the new data nevertheless replaces SRBUF | Unread does not prove old-byte retention; sticky final SRSTAT needs its prior owner |
| Other errors | Printed129-130 describe sticky framing, parity and multiprocessor error bits and software clearing | Those descriptions do not settle RX-request suppression or acknowledgement for every error/filter combination |
| SRBUF read | No acquired applicable source establishes whether reading0055 clears RQSRRDY | Both read-clears and read-does-not-clear remain unproved; read-only is not an answer |
| Interrupt entry | Printed164/167 specify clearing the serviced IRQ during maskable processing, clearing MIE and retaining IE | Generic controller rule, conditionally joined to RXbit1; not a new observed RX acknowledgement |
| Reassertion | A later eligible receive can generate another request under the completion rule | Automatic reassertion without a new completion, and whether every re-entry requires a new completion, remain unknown |
| Competing operations | No applicable collision-priority rule was acquired | Hardware set, software IRQ clear, entry ACK, SRBUF read and a new completion have no invented total order |

SRBUF content and IRQ pending are separate state obligations. Buffer retention
until replacement is not proof that the request stays set until the buffer is
read. Conversely, generic serviced-factor clearing does not prove that unread
content cannot reassert a source. The normal-slave receive chart on printed148
does not resolve these missing relationships.

## IE contradiction and pending versus delivery

Complete printed164-169 were reviewed again. Printed165 section17.2(2) explicitly
supports IE1 enabling and IE0 disabling each factor, and retains IE during
maskable processing. Printed168 Figure17-2 depicts a non-inverting IRQ/IE AND,
priority selection and MIE gating. Printed169 examples2/3 depict request
occurrence before later IE1/MIE1 enables and subsequent interrupt transition.

Printed167 nevertheless says corresponding IE0 in the opening acceptance
condition for maskable processing. It is not a description of post-entry IE
clearing: the following processing list clears serviced IRQ and MIE, while165
retains IE. No acquired alternate edition or manufacturer erratum resolves the
literal contradiction.

The result is **IEPolarityEvidenceFavorsSet1ButConflictRetained**. The set1
interpretation has stronger support, but both hypotheses remain explicit.
Applicable physical ECU polarity is not established. Pending-before-enable is
source-supported feasibility, not unlimited pending lifetime or proof that an
already acknowledged request will be delivered again after an enable change.

## Firmware source relationships and the pending cut

The source chain below classifies each link separately. None is an actual new
execution trace.

| Link | Classification | Outstanding obligation |
|---|---|---|
| Configured receiver to eligible RX completion | Manufacturer-source-qualified | Actual silicon, SRCON owner, mode, clock and frame |
| Eligible completion to SRBUF content and RX request | Manufacturer-source-qualified, with MPC-ignore exception | Actual event/byte and intervening replacement history |
| Request to pending after software clear54EA | Conditional software effect; ordering unknown for collisions | Independently owned post-clear request or justified concurrent reassertion |
| Pending plus IE/MIE to IRQ000A acceptance | Manufacturer-source-qualified with IE contradiction | Current masks, priority, instruction boundary and applicable controller |
| IRQ000A to handler0213 | Standard vector allocation plus static ROM relationship | Actual delivery and safe source-owned eight-byte frame |
| Handler entry to selected0262 SRBUF read | Static ROM path, conditionally possible | Retained parser context, correct banks and actual read identity |
| Read0262 through comparison0264 to store0269 | Static ROM instruction effects | Correct current r5/AL context and no intervening mutation |
| Store0269 through tail to RTI029C | Static ROM path, conditionally possible | Intact matching frame, F8 generation, nesting and alias accounting |
| RTI to saved foreground execution | Requires actual native execution evidence | Saved foreground PC and retained architectural/RAM state |

The reviewed initial sequence clears IRQ word DATA0018/0019 at54EA before IE
write54F0. If this clear completes with the stated effect, an earlier request
generation alone cannot explain a later RX entry. A post-clear generation,
concurrent reassertion or another independently justified writer is required.
The new specifications do not determine the collision winner or establish that
this initial sequence belongs to the actual current history. Software clear is
not silently reclassified as hardware entry acknowledgement.

The inherited alternatives remain IE3F14=2BAB with F8=2BAB/FA=02A0 and mode0217.2
cleared, or IE3F28=A9A3 with F8=A9A3/FA=00A0 and mode0217.2 set. Initial54F0
uses2BAB without a mode writer in the closed initial fragment. The3E81 checks
compare mode, F8, IE and FA generations. Direct IE writes precede shadow writes;
these are not one atomic native update. MIE windows and competing IRQ/NMI,
foreground, indirect and frame aliases retain their separate obligations.

The applicable source allocation is RX READY at vector000A/bit1,
RQSRRDY/IESRRDY. Frozen historical TX000A transcriptions remain historical
errors; they are not current authority and are not rewritten retrospectively.

## What0262,0269 and029C still require

The inherited Flag path requires mode0356.1=1, old0356.6=0, retained r7=2/r5=2/
r2=4, and r6 from the separately reviewed Header/Length relationships. These
are conditional source obligations, not host-seeded native observations.

LB0262 reads8-bit DATA0055 into AL and selects DD0. CMPB0264 compares **r5 with2**,
not the received byte F, preserving AL/AH under the reviewed ordinary semantics.
Its selected r5 case permits JNE0267 to fall through to STB0269 at DATA03F3.
An even F can reach that store. Oddness belongs to the later consumer, which is
not executed here. Unknown physical SF remains qualified.

The five ordered persistent effects remain0222 status RMW,0269 r3=F,026D r6+=F,
026F r5=3 and0270 r7=2. Same-value stores are distinct storage generations.
This Flag path does not set ready0356.7. Absence of another selected-tail03F3
writer does not prove physical retention through nesting, aliases, foreground
activity or a subsequent packet.

Entry needs a physically writable and safe eight-byte frame owned by the
current SSP, with intact saved PC/A/LRB/PSW generations. Actual SSP, memory-map
applicability and native RAM owners remain unknown. Numeric non-overlap in an
invented control is not native stack safety. RTI029C must restore the actually
saved foreground PC;029C itself and host-selected28AE are not that PC. RTI does
not automatically restore IE or earlier pointing-register RAM contents.

## Verification, preservation and delivery interpretation

The isolated M2ck verifier may check source identities, documentary findings,
explicit hypothesis implications and refusals of unsupported claims. Invented
controls are labeled synthetic and establish only logical consistency. They
must not turn missing documentary authority into an event observation, a current
RAM generation or a hardware arbitration result. Independent expected findings
must be frozen before comparison with the research analysis.

At this document's preparation, the completed checks are the local six-source
identity audit, bounded User ZIP integrity check, full relevant User-page visual
review, new-source acquisition receipts and independent complete30-page Japanese
review. This source document does not assert a future test, cross-platform,
commit, CI or preservation PASS. Software QA and delivery are accepted only from
their actual exact-source receipts. Historical17 remains NotRun unless really
executed; unrelated Rust/Core/CLI/Desktop/C suites are not relabeled fresh PASS.

Historical contracts, oracles, manifests, reports and source fingerprints remain
frozen. The three inherited authorized preservation exceptions remain separate
from any new unauthorized difference; they do not become a strict historical
preservation PASS. Current changes require a scoped source/privacy/protected
comparison, preserving unrelated user files. No private document or ROM payload
belongs in Git or public CI artifacts.

The final SHA is the Git commit containing this document and the reviewed M2ck
package. Its normal-push identity, exact-SHA run, executed jobs, test counts and
full canonical-byte comparison are recorded by delivery receipts and the final
report after execution. This avoids an in-source self-referential commit hash or
a prospective green status. The accepted baseline's prior successful run is
[M2cj run41084712961](https://github.com/Pvitaly91/HondaEcu/actions/runs/41084712961);
it is not substituted for M2ck CI.

## Remaining evidence and final classification

The next most valuable documentary source is the complete authenticated
receive-operation subsection for an applicable MSM66201/207 User Manual, with
its title/document ID/date linkage, specifically defining RQSRRDY lifetime,
SRBUF-read side effects, request acknowledgement, reassertion after entry and
hardware-set/software-clear ordering. Printed132-147 are a known missing local
range, not a proven location of any particular rule. An applicable erratum or
independent edition is still needed to settle the IE165/167 contradiction.

Actual silicon applicability, current receiver/pending/IE/MIE owners, received
byte history, source-owned safe frame, retained parser context,0269 storage
generation, matching RTI and downstream foreground retention remain execution
blockers. No new reset/WDT, scheduler, IRQ, timer, physical SF, stack safety,
native handoff, target-equivalence or integration claim is established.

**RXREADY_SOURCE_CONFLICT_UNRESOLVED / EXECUTION_BLOCKED.** The ACK-specific
primary source is still unacquired. NewCpuExecutions=0;
NewOriginalRomExecutions=0; NewIRQDeliveries=0; NewRTIExecutions=0;
NewTargetRetirements=0. No IRQ/PC injection, receiver simulation presented as
hardware evidence, firmware output, GUI or hardware experiment is admitted.
FirmwareReady=false. Stop after M2ck; do not begin M2cl automatically.
