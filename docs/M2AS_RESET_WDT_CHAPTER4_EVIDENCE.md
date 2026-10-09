# M2as - Reset/WDT hardware-document acquisition

Result: **WdtCommandMeaningNotEstablished / Research/Blocked**.
No applicable command decoder or reset-release proof was recovered. ISA/hardware
uncertainty about reaching native SSP24F8 and CAL2689 has not decreased.
Actual-ROM executions: **0**; no synthetic ROM execution or Cpu/Bus construction.

## Scope and source identity

This bounded documentary milestone follows M2ar at exact base
`94632280a8a89ad1a7e6eb75c1efd591371dcb88`, on
`codex/p28-reset-wdt-chapter4-evidence-m2as`. It does not repeat M2ar's
bounded DATA4700 numeric noninterference proof or run the reset prefix.
Raw scans, archive inventories, retrieval receipts, hashes, visual-review
records, inquiry and delivery attestations remain private and are not in Git.

The systematic search covered historical PGMFI attachment paths and revision
history, pinned Honda archive trees and mirrors, Archive.org metadata/snapshots,
Bitsavers, datasheet indexes, and official OKI/ROHM/LAPIS legacy-document leads,
including Japanese reset/watchdog terms. Failed, blocked or rate-limited routes
are recorded, not treated as proof that no manual exists. No unknown downloader
was executed; no private firmware was transmitted. Repeated mirrors are not
independent manufacturer confirmations.

| Acquired source / locator | Identity and reviewed scope | Result and remaining boundary |
| --- | --- | --- |
| [OKI Microcontroller Data Book](https://bitsavers.trailing-edge.com/components/oki/_dataBooks/1990_OKI_Microcontroller_Data_Book.pdf) | Fifth Edition, June1990; 534 PDF pages. Complete target sections: MSM66201/66P201 printed363-383 (PDF368-388), MSM66207/66P207 printed384-404 (PDF389-409), marked Preliminary. Cover, title/edition, contents and all42 target pages visually reviewed; all534 PDF page objects parsed. | New actual manufacturer-book bytes, `PrimaryDocumentAcquiredButNonDecisive`. Its SFR tables at printed368/389 identify WDT0011 as write-only byte, reset00/stopped; they do not decode3C. These are short specification sections, not the missing Hardware/User Manual. Exact silicon/mask revision unspecified; `DeviceApplicabilityConditional`. |
| Four Internet Archive items titled user manuals: manualsbase230861/230868, manualsonline fadda4dd-82eb-44ad-acae-cd0172e30c62, manualzilla7001520 | Actual PDFs:31 pages each, four byte-identical containers. Manufacturer portion is the already-known E2E1027-27-Y4, January1998 (previous November1996),30 pages, plus a datasheetcatalog advertisement. Complete identity/SFR/end pages reviewed and edition/lineage compared. | Another container of the same specification edition, not four independent documents or full hardware manuals. `PrimaryDocumentAcquiredButNonDecisive`; no recovered WDT decoder. |
| Existing `66207usersmanual_incomplete.zip`, plus three freshly acquired byte-identical mirrors | 66 JPEG entries; manufacturer title leaf, edition leaf and table of contents absent. Known MSM66201/207 page headers. Exact readable boundary spreads below. | No new pages.59 entries verify CRC,7 do not. Whole-source integrity is not PASS; readable CRC-verified pages support only their bounded page association. |
| Existing `66207Chapter3.zip` | 211 TIFF entries, all CRC-verified; instruction pages, including printed3-59 EXTND and3-66 JC. | CPU instruction chapter, not Hardware Chapter4. No new hardware pages. |
| [Pinned PGMFI revision-history HTML](https://raw.githubusercontent.com/hondabase/hondabase.com/27e29ca84d110d45fd2d858eac153ce575acb9c3/tools/wiki-import/source/twiki/bin/rdiff/Library/66kAssemblerDocs.html) | Actual archived HTML acquired.26Feb2004 revision points an "OKI 66207 User's Manual" label to the different old path shown below.16Mar2004 change removes that link;1Oct2004 adds the incomplete/Chapter3 attachments. Dates belong to the topic, not the manufacturer edition. | Reliable new historical locator, **not** recovered manufacturer bytes or verified full-document identity. `ArchivalReferenceOnlyManualBytesNotAcquired`. Label66207 versus path66201 discrepancy retained. |

The old alternate locator is
`http://pgmfi.org/resources/documentation/MCU/66K/66201%20Manuals/Oki%2066201%20Manual.zip`.
Its bytes, edition, completeness and exact location of the missing applicable
hardware document were **not** established. Original and mirror-path probes did
not recover the ZIP; snapshot routes were unavailable/rate-limited and stopped.
This is a useful acquisition lead, not satisfaction of the decisive-source goal.
Cross-family manufacturer materials and third-party "service3C" examples remain
leads only: no verified WDT peripheral compatibility or applicable exact command.

## What printed pages are actually missing?

The earlier58-65 gap estimate is now explicitly bounded by complete,
CRC-verified spreads:

| Retained printed pages | Complete-page observation | Permitted conclusion |
| --- | --- | --- |
| 54/55 | Addressing ends on54;55 starts Chapter4 CPU CONTROL FUNCTIONS, introducing standby and reset.4.1/4.1.1 describe standby/SBYCON. | Chapter4 starts at55; this is not a WDT decoder. |
| 56/57 | 4.1.2 Standby Operations covers HALT/HOLD/STOP and refers to Table4-1, not present in these spreads. | The retained Chapter4 material is incomplete. |
| 66/67 | Already5.2 Port Control Registers. | Chapter5 has begun by66; its opening/5.1 is not recovered. |
| 68/69 | 5.3 P0, then5.4/5.5 ports. | Confirms the port-chapter boundary, not the content of the gap. |

Missing printed spreads are exactly **58/59,60/61,62/63,64/65**. They lie between
Chapter4 standby and Chapter5 section5.2, but their exact section allocation,
Reset/WDT titles, tables and diagrams remain unknown without contents/full pages.
It would be incorrect to label all eight pages as Chapter4 or WDT pages. The
archive also lacks its opening identity/contents pages and other ranges; it is
not a complete book. `RecoveredMissingHardwarePages` is false; no recovered page
is promoted even to `RecoveredPagesRevisionUnverified`.

Seven original ZIP members fail CRC: `page_32.jpg`, `page_34.jpg`, `page_38.jpg`,
`page_102.jpg`, `page_114.jpg`, `page_116.jpg`, `page_122.jpg`. Fresh mirrors have
the same raw-byte identity and discrepancies. This does not identify whether
payload or recorded CRC metadata caused the failure. No member was repaired,
repacked or credited as integrity-verified. Older source bytes/reports/statuses
remain unchanged; **preservation PASS is not whole-archive integrity PASS**.

## Exact WDT3C and execution boundaries

M2ar's static instruction sequence remains24ED ->24F1 ->24F4 ->24F8: a byte3C
write to WDT0011, followed lexically by the native SSP writer. No new instruction
trace, reset transition, hardware event or observation was created.

| Question | Evidence result | Remaining assumption / gate |
| --- | --- | --- |
| Full-byte versus selected-bit decoder; valid3C command | `WdtCommandMeaningNotEstablished` | Applicable exact peripheral command table, revision and conditions missing. |
| Start/stop/reload/clear/ack, previous-state dependence, sequence or latch | Not established | Reset-stopped state alone does not imply command behavior. Write-only RAM echo/readback cannot prove it. |
| Immediate effects, reset/trap or guarantee of next instruction | `HardwareSafeReachingNotEstablished` | Neither `CommandDecodedFromApplicablePrimary` nor `ImmediateEffectArchitecturallyDefined` established. |
| Delayed evolution/overflow, clock/prescaler | Not established | No `DelayedEffectArchitecturallyDefined`; clock history unknown. No physical-time conversion from cycles. |
| Reset pulse/startup/release and cause-specific retention | No new applicable rules | Existing architecture facts retained, not promoted to `ResetReleaseArchitecturallySpecified` or actual history. Supply rise is not a qualified RES proof; NMI is an interrupt, not a reset cause. |
| Standard201 versus207 / OTP / mask / ECU ASIC | `DeviceApplicabilityConditional` | Coverage of standard parts does not identify the actual ECU silicon, mask, board configuration or compatibility. |
| Actual reset and native SSP24F8/CAL2689 | `ActualHardwareHistoryNotEstablished` / `ActualNativeExecutionNotObserved` | Actual reset entry and a rooted single-machine prefix remain the first history gate. WDT24F4 is the earliest unresolved command along the inherited static prefix. |

Consequently local software continuation24F4 ->24F8 is not proved hardware-safe.
SpecificEcuHardwareContextVerified and ActualResetTransitionObserved remain false.
Required later external evidence includes exact part/mask identity, applicable
peripheral revision, reset waveform/oscillator/clock and board pin configuration;
no physical inspection or experiment is performed here. No constructor seed,
host-PC placement or code-owned invented external event fills those obligations.

## Inquiry and invented-only checks

An independent English WDT inquiry is **InquiryDraftReady / NotSent**; no ticket
or manufacturer response exists. It requests complete hardware material, wherever
Reset/WDT is located, exact3C decoder/state machine, reset/release conditions,
clock dependencies, mask exceptions/errata and separate201/207 applicability.
It includes no private ROM or personal data. Sending requires separate explicit
user authorization. The C8 inquiry is separate and remains NotSent.

31 isolated invented-only Core facts check documentary acceptance, byte/visual
deduplication and metadata conflict rejection, complete versus incomplete pages,
recovered-page lineage, unknown revision/family/type/origin, write-only and
reset-stopped nonproofs, RES/BRK/WDT/NMI separation, immediate versus delayed
evidence and refusal to promote clock/constructor/actual-history/CAL preflight.
Even favorable invented candidates return policy matches only, never real command
resolution or execution permission. No WDT state machine, Cpu/Bus, timer or
synthetic hardware event is modeled; expected results are independent of Rust.
Full QA and exact-SHA delivery results belong to the private closure report.

## Preservation and STOP

Runner0.41.0/protocol1 and `byte-sll-off-page-preserves-noncarry-flags` unchanged.
No production executor, WDT/SFR behavior, ISA admission, CLI/schema/scenario,
constructor/reset loader, ROM/binding/export, GUI/hardware tooling or Windows
PID/START/READY cancellation code changes. Historical binary/source guards and
all older private artifacts remain protected.

M2ar/M2ap Research/Blocked; M2aq ExecutionPreflightBlocked, CAL2689/RT5C80 NotRun;
frame268C NotObserved; actual restored SSP047E NotEstablished. M2ao remains
afterCLR2758/beforeSTIE2759; M2ak source-to5722 Research/Blocked; M2al/M2am C8
PrimaryConflictUnresolved; M2an SLLB fix complete; M2ah STOPbefore5722. DATA019B.2
runtime owner NotEstablished;5722/5725/5733 DynamicNotRun; M2tJGT233A unresolved;
M2ag/M2af unchanged; strictM2iBlocked; IRQNotInjected; TimerEvolutionNotModeled;
EnclosingIRQFrame/RecoveredEcuScheduler NotEstablished; ElapsedTimeNone.
PcInspectionOnly/NotFlashReady;physicalRpmAvailable=false; physical fuel/time/
degrees unavailable. GUIr3 paused/NotRun; D1/D2 interactive and hardware/fullboot
NotRun; FirmwareBIN=0. No historical status is promoted by documentary QA/CI.

One next evidence-driven step: obtain explicit authorization to send the prepared
WDT inquiry, requesting an identified applicable complete manual/command table.
STOP after delivery: no M2at, DEC DP/JGT fix, reset/CAL/loop execution, IRQ,
first5722 continuation, GUI or hardware work.
