# M2bv — native exit, P2 ownership and one controlled RMW

M2bv is a new research-only requirement and opt-in lifecycle based on accepted
M2bu `df55bc5d86f85906813a8241608dac542ab4c302`. This document and
`research/p28-word0196/native_p2_handoff/ownership_contract.json` are not runtime
receipts. Current M2bv execution is **NotRun**. An instruction listing, contract
or old observation cannot establish a new machine's current P2 owner.

The proposed bounded chain is original `54F5 → 5501 → 556F → 5596/55C5 → P2` on
one production CPU and Bus. One original P2 instruction is added to the accepted
M2bu prefix/algorithm, then execution stops. Existing M2aa, M2ab, M2ac and M2bu
contracts, ordinary runner admissions and historical observations remain intact.

## Three separate authorities

The OKI MSM66201 Instruction Manual, first edition September 1991, SHA-256
`f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271`, establishes
ANDB obj,A at printed 3-25 and ORB obj,A at 3-108. Preserved full-page renderer
pages are 77 and 161; printed labels control, not a presumed universal offset.
Both operate on the byte object and AL, leave A unchanged, and change ZF from
the byte result. CF, HC, DD and other PSW bits are retained; DD does not select
a different form. Production Rust output is not this semantic authority.

The two timing/accounting authorities remain separate. The manufacturer's
zero-page N8 rows for these ANDB/ORB forms print **INT=7**. The existing software
fallback accounts for two diagnostic cycles per instruction byte, giving **6**
for this three-byte form. The user explicitly approved retaining that software
diagnostic accounting in M2bv without changing decoder/Exec or expected values.
It is not an independent ISA timing proof and is not ECU elapsed time.

Cycle fields remain present in the actual record and the complete cross-platform
canonical comparison; no semantic or diagnostic field is discarded to obtain
agreement. Manufacturer/software timing equivalence and physical time remain
`DiagnosticCycleTimingEquivalenceNotEstablished` / `TimingEquivalenceNotEstablished`.
This qualification does not change the independently reviewed AL, flags, storage,
ordered-write or instruction-retirement requirements.

Matching manufacturer MSM66201/207 peripheral scans establish the addressed
storage. Their preserved package `66207usersmanual_incomplete.zip`, SHA-256
`f061cb5bcbd1804699fb60b543c425646fbb15b939c9bc51b24edbb4da4c6ddf`, contains
the actual named chip headings at printed 12–13. Table 5-2 at 66 identifies the
registers; section 5.5 at 69–71, Fig 5-8 and Table 5-3 establish P2 read/write
selection. Full relevant spreads were reviewed, including footnotes.

The frozen M2aa ROM/listing audit supplies static instruction identities and
candidate writers. It does not establish that startup ran before a selected
M2bv case. Customer ASIC/revision, board wiring and physical applicability are
still conditional. No manufacturer scan, OEM window or private trace is copied
into this public component.

## Exact technical mode

P2 DATA is byte SFR `0024`; P2IO is `0025`; P2SF is `0026`. Each P2IO direction
bit selects output when 1 and input when 0. All-output therefore requires P2IO=FF.
Implemented P2SF bits are **3..7**, mask F8, selecting clock/HOLD/serial secondary
functions. Bits 0..2 do not exist and read one. Canonical primary-mode metadata
is **P2IO=FF, P2SF=07**, with `(P2SF & F8)==0`; 07 does not enable alternatives.

In this all-output primary mode, reads return the DATA register rather than
pins. In other direction/mux configurations they may return pins or secondary
function state. The documented arithmetic RMW rule reads the selected source,
then writes the port DATA register; it is not an unconditional latch-read rule.
P2 DATA reset is undefined, P2IO reset is 00 and P2SF reset is 07. Reset cannot
provide the missing initial output-data value or prove the current mode.

This is `ReviewedPrimaryOutputModePrecondition`, the old M2aa
`ReviewedStartupPrecondition`, not executed startup or measured vehicle state.
The existing dedicated P2 output-data latch is not ordinary RAM. P2IO/P2SF
remain non-writable technical preconditions, without a general input/pin/mux
emulator, external pin transitions, hardware bus effects or dynamic switching.

## P2 provenance matrix

| Field | Documented reset | Listed direct writers/readers | Current ownership |
|---|---|---|---|
| P2 DATA0024, 8-bit | Undefined | 12 writers; 13 readers, including 10 RMW sites | Native initial owner not established; explicit once-initial technical latch required |
| P2IO0025, 8-bit | 00, input | 25B2 writer; 3F6F comparison reader | FF is a reviewed technical precondition, not observed prior configuration |
| P2SF0026, implemented F8 | 07, low three nonexistent bits read one | 25B4 writer; 3F75 comparison reader | Implemented bits clear is a technical precondition, not physical mode proof |

P2 direct writer PCs are 0055,00D1,0111,0764,0B4F,25AE,4243,5596,55C5,5682,
5BF0,5CBE. Pure P2 read PCs are 0754,276D,5CA5; the ten RMW PCs are the writer
set excluding the two immediate stores at 0055 and 25AE. These are frozen
listing leads, not whole-ROM execution coverage or an exhaustive dynamic proof.

Static startup has AL=FF at25A0, P2←1F at25AE, P2IO←FF at25B2, and implemented
P2SF cleared at25B4. Intervening reviewed MOVB/STB forms retain AL. This is
`StaticStartupWriterIdentified`, separately from `StartupExecutionObserved` and
`CurrentP2ValueOwned`. Startup execution is not observed in the selected new
machine. No default latch1F, automatic boot or invented prior generation follows.

The historical audit byte-checked 11499 listed instructions and retained 19
direct P2/P2IO/P2SF references, 725 conservative indirect/indexed/stack candidates
and 25 low-pointer leads. DP0026 at3CE2 is a reviewed count argument with X1=02CB
for helper5BC9, not a proven P2SF store. Other aliases remain unresolved.
Word0024 or odd0025 overlaps P2+P2IO; word0026 or odd0027 overlaps P2SF+neighbor.
Current-page forms require their actual page context. Neither symbolic naming
nor absence of another listed direct configuration writer proves global owner
uniqueness or absence of intervening writes.

Historical M2aa has 42 actual P2 RMW observations: 33 AND and 9 OR, within 69
events. Its 39 quartet-derived strict effects, three gate controls, 15 same-value
writes and 15 retained native reads belong to those earlier source machines.
Initial snapshots and later observed generations are distinct. M2bu stopped
before P2; its prior executions provide no new latch value or physical mode.
Historical generation IDs must never be imported into a new M2bv machine.

## Closed handoff and expected observations

Private PROGRAM is the unchanged original interval `[54F5,55C8)`, 211 bytes,
with the 24 accepted M2bu nodes plus two reviewed terminal P2 sites. Gaps do not
grant execution authority. Original image, listing/extents and source identities
remain separately checked. The public program must be independently invented;
no private opcode window, ROM identity or historical trace is public input.

| Path | M2bu steps | One new P2 operation | M2bv steps | Stop before |
|---|---:|---|---:|---|
| A | 16 | 55C5 ORB P2,A | 17 | 55C8, TCON0 |
| B | 18 | 5596 ANDB P2,A | 19 | 5599, TRNSIT |
| C | 19 | 5596 ANDB P2,A | 20 | 5599, TRNSIT |
| D | 21 | 5596 ANDB P2,A | 22 | 5599, TRNSIT |

The independent predecessor/M2av model derives expected AL; the actual P2
instruction consumes AL left by the actual retained CPU. Expected results are
old|AL for A and old&AL otherwise, modulo the byte width. ZF reflects that byte
result. A/AL/AH, CF/HC/DD/OtherPSW, selectors, pointers, SSP and unrelated DATA
retain their verified incoming values. No host-applied flag or result repair.

Only one technical latch snapshot may be set before the first functional
instruction at54F5, including 00/FF/A5 coverage and reachable same-value cases.
Its classification is `TechnicalArchitecturalP2LatchSnapshot_NoNativeWriterGeneration`.
No host write, PC jump, snapshot import, second CPU or reseed is allowed after
entry. Byte0024 is admitted only at the selected terminal PC, then the capability
closes. Word P2, IO/SF, neighbors, other ports and a second P2 instruction refuse.

Retain a separate functional peripheral read OLD then write NEW journal, complete
PROGRAM acquisition, logical/raw DATA observations and full architectural state.
Diagnostic readback is not functional evidence. Multiple journal views of the
same native write do not create extra semantic writes. Same-value writes still
create a fresh current-session generation. Its writer PC/machine/declared ordinal
must come from actual execution, never from the initial snapshot or old M2aa IDs.

Required result fields separate P2InitialSource=TechnicalArchitecturalSnapshot,
P2InitialNativeOwner=NotEstablished, P2RmwWriter=ActualProductionInstruction,
P2RmwWriterPC=5596/55C5 and P2FinalGeneration=VerifiedWithinTechnicalSession.
The latter runtime claims are unavailable until actual observations and the
independent comparison pass. PhysicalP2Owner remains NotEstablished and
PhysicalOutputEffect remains NotObserved.

## Delivery requirements and retained limits

The planned corpus is 32 private +32 public positive cases, eight per path:
624 retirements each, 1248 total, with exactly one P2 retirement each. Negatives
are separate. Expectations/source/corpus freeze precedes final-source runtime;
canonical records, cache/checkpoint hashes and owned process identities prevent
duplicate execution after interruption. Explicit PAUSE stops before the next
case; no background automation continues. New Cargo outputs belong only to
`.tmp/m2bv-owned/cargo-target`, in both environment and explicit target argument.

Current M2bv runtime, QA, CI, byte comparison and delivery are NotRun here.
Acceptance requires all authorized actual gates, full Local↔Ubuntu↔Windows
decompressed byte comparison, private source/privacy/preservation checks and a
seal before the Ukrainian FINAL. Existing historical/desktop/M2bu CI guarantees
remain mandatory. The single inherited historical runner exception stays visible:
AuthorizedPreservationExceptions=1, strictHistoricalPreservationPass=false,
22/23 runner roles exact, no new unauthorized differences or additional waiver.

Only the qualified verdict may follow actual success:
`M2bv ACCEPTED_WITH_HISTORICAL_PRESERVATION_EXCEPTION / Research-Only — Technical P2 Handoff Verified`,
with `NativeP2InitialOwnershipNotEstablished`. This document grants no acceptance.

ActualHardwareEcuExecutionNotObserved; RecoveredFullEcuSchedulerNotEstablished;
PhysicalSFNotEstablished; NativeStackSafetyNotEstablished;
CurrentNativeP2InitialOwnerNotEstablished; PhysicalP2ElectricalEffectNotEstablished;
PhysicalP2RoleAndPolarityNotEstablished; DownstreamTRNSITAndTCON0NotExecutedInM2bv;
ActualNativeDownstreamRejoinNotEstablished; SafeROMPlacementNotEstablished;
TargetProgramEquivalenceNotEstablished; FirmwareIntegrationNotEstablished;
FirmwareReady=false. A latch write does not identify injectors, ignition,
electrical polarity or any physical load. STOP after delivery: no M2bw,
TRNSIT/TCON0 continuation, firmware generation/patch/flash, GUI or hardware.
