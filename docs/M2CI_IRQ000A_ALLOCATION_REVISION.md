# M2ci: IRQ000A table transcription correction and silicon applicability

Research-Only: **PriorTranscriptionErrorCorrected / ECU_APPLICABILITY_BLOCKED**.
No CPU, original-ROM, IRQ or RTI execution, peripheral model, GUI, hardware or
firmware output is introduced. FirmwareReady=false.

## Primary finding

Independent complete-image review of the two existing manufacturer tables
corrects the premise inherited from M2ch. Their three serial rows **agree**:

| PROGRAM vector | Instruction Table1-1 | User Table17-1 | User IRQ/IE word bit | Request / enable symbols |
|---|---|---|---:|---|
|000A|Receive ready|Receive ready|1|RQSRRDY / IESRRDY|
|000C|Transmit ready|Transmit ready|2|RQSTRDY / IESTRDY|
|000E|Receive BRG|Receive-ready BRG overflow|3|RQSRGEN / IESRGEN|

These are hexadecimal PROGRAM byte addresses of 16-bit vector words, not DATA
register addresses, instruction PCs, IRQ bit numbers or physical events. The
Instruction table does not independently supply the User table's register-bit
or assembler-symbol allocation. Those fields remain unknown for that source.

The Instruction Manual is OKI's first edition, September1991, Table1-1 printed
1-5 (PDF9). Its table explicitly covers standard MSM66201 and permits different
customer ASIC vector allocations with a shared CPU. The retained User scan's
Table17-1 is printed166; its adjacent section names MSM66201/207. The complete
table and headings are legible. Title, edition and revision leaves are missing.
The historical ZIP has seven CRC-failing members; the reviewed166 image is a
CRC-verifying member. No archive was repaired or declared a complete manual.

Manufacturer-body sources: [Instruction Manual](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/Oki_66201_Instruction_Manual.pdf)
and [incomplete User scan archive](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/66207usersmanual_incomplete.zip).
Mirrors of these same documents are not independent confirmations.

## Explicit correction of inherited statements

M2ch incorrectly transcribed User000A as TX-ready, User000C as transmission
error, and bit1 as RQSTRDY/IESTRDY. The original page actually says receive-ready
at000A and transmit-ready at000C. No transmission-error row occupies000C.
Consequently the supposed printed RX/TX conflict is withdrawn in this new
interpretation. No manufacturer erratum or silicon revision change is needed
to explain that earlier transcription error.

M2ch's frozen sources, oracle, canonical results, approval, reports and CI stay
unchanged as historical evidence. Their static consistency PASS did not verify
the mistaken table transcription. The old TX profile is not current applicable
manufacturer authority. The frame geometry, software read sites and conditional
packet algebra are separate statements, not evidence of a physical IRQ source.

## Existing source inventory and chronology

| Existing document | Identity and scope | Allocation relevance |
|---|---|---|
|MSM66201 Instruction Manual|First Edition September1991; 266 PDF pages|Table1-1 gives the three source roles; customer ASIC qualification|
|MSM66201/207 User scan|66 JPEG members; no authenticated title/edition leaf|Table17-1 agrees and gives source-specific bits/symbols; full-document integrity not established|
|E2E1027-27-Y4|January1998, previous November1996; 30 manufacturer pages|Standard device and SFR context; no independent three-vector allocation table|
|Microcontroller Data Book|Fifth Edition June1990; target sections preliminary|Standard201/207 specification sections, not a revision bridge or full User Manual|
|E2E1025-27-Y2 Instruction List|January1998, previous November1996; five pages|Instruction functions, not IRQ/peripheral allocation|

The new result is a corrected reading of existing primary evidence, not a newly
acquired document. Bounded targeted search found no new applicable title/edition,
erratum or exact ECU silicon bridge. That search does not prove no such source
exists. PDF creation dates and third-party attachment dates are not manufacturer
revision dates. No A-to-B revision succession or allocation change is established.
No nX-8/500S peripheral mapping is imported.

## Software consistency and conditional masks

Private read-only source-bound verification identifies PROGRAM000A's target0213.
The handler's DATA0055 reads are consistent with documented RX-ready allocation,
but cannot establish which physical ASIC is fitted. Handler names, ROM size,
opcodes and checksum compatibility cannot select a hardware variant.

Under the **User-table RX profile**, wordbit1 is receive-ready. Conditional
FA=02A0/F8=2BAB and FA=00A0/F8=A9A3 masks clear that bit in the body and enable it
in the tail. Wordbit2 is TX-ready and is clear in all four masks. These are
literal-mask relationships, not actual current IE or source-generation evidence.
Enable polarity here is explicitly scoped to User section17.2(2), printed165,
which says set1 enables and reset0 disables, and Fig17-2 on printed168. The
entry paragraph on printed167 instead says corresponding IE set0. That internal
prose discrepancy is retained; no manufacturer erratum or silently repaired
wording is asserted. The standard-table source roles agree independently of it.
The alternative asserted TX000A/bit1 profile is a rejected prior transcription,
not a second equally supported manufacturer profile.

For the Instruction table alone, the source role is RX but no source-specific
IRQ/IE bit or symbol can be borrowed from the User table without qualification.
For an unidentified custom ECU part, both standard-device applicability and
actual source-specific enable/pending behavior remain unestablished.

In an applicable User architecture, entry still needs pending, the corresponding
IE enable, MIE, boundary/priority eligibility and safe frame storage. Source
acknowledgement, SRBUF read effects, reassertion and clock/BRG conditions require
their own peripheral authority. Four distinct0055 reads do not prove four receive
completions, four native invocations, or four physical bytes. A TX-ready event
does not acquire an inferred relationship to SRBUF merely from this program.

The four-word frame remains PC at even(S), A at even(S-2), LRB at even(S-4), PSW
at even(S-6), postSSP=S-8. Matching RTI restores PSW,LRB,A,PC;029C is its
instruction PC, not the saved foreground PC. The03F0..03F7 overlap counterexample,
unknown physical SSP/SF/RAM, nested IRQ/NMI, ready/mode owners and foreground
return obligations remain. No parser28AE, CLR291B,064C or064F execution is claimed.

## What is still needed

The actual ECU manufacturer part/custom code, package marking, mask revision and
PCB applicability are unestablished. Standard MSM66201 coverage does not identify
that silicon. A usable next item is a manufacturer/OEM cross-reference tying the
actual package's full part/mask code to the applicable vector000A/000C/000E and
IRQ/IE table. A marking photograph alone is not that cross-reference.

An unsent legacy-support inquiry requests the authenticated User Manual title,
document number, edition and Table17-1; applicable symbols, peripheral receive
acknowledgement and customer-mask variations. It correctly states that the
reviewed tables agree, and asks no vendor to explain a fictitious contradiction.
No message, ticket, hardware inspection or private upload has been performed.

## Verification and delivery scope

The small verifier checks documentary relations and authority limits against
separately frozen reference expectations. Its canonical records are static
findings, never actual CPU/peripheral observations. Local/Ubuntu/Windows compare
the complete same records. A finite eight-file source addition and a separately
reviewed workflow overlay preserve all1223 accepted sources except the overlay;
unknown/runtime/unreviewed changes require full historical QA. Historical17 is
NotRun in the bounded lane, not a new PASS.

Inherited authorized preservation exceptions remain three: generated runner,
external Python and external CMD. New exceptions are zero;
StrictHistoricalPreservationPass=false. Source/privacy and scoped preservation
remain independent delivery gates. ActualCpuExecutions=0;
ActualOriginalRomExecutions=0; ActualIRQDeliveries=0; ActualRTIExecutions=0.
ActualHardwareEcuExecutionNotObserved; ActualResetEntryNotEstablished;
WdtCommand3CMeaningNotEstablished; NativeSchedulerNotEstablished;
FirmwareIntegrationNotEstablished; FirmwareReady=false.

Stop after M2ci. No M2cj, IRQ/RTI runtime or physical action is authorized here.
