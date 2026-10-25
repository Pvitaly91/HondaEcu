# M2bw - bounded native post-P2 control continuity

M2bw is a default-off research extension of accepted M2bv
`b67ea436870fe591f6ae4daca307341806d6f8eb`. This document defines requirements
and independently reviewed semantics. It is not a CPU execution receipt,
firmware admission, recovered scheduler or physical peripheral observation.
Actual delivery requires the source-bound runtime, oracle, CI, byte-comparison
and preservation receipts described below. `FirmwareReady=false` remains.

## One retained production machine

The native chain remains `54F5 -> 5501 -> 556F -> P2 -> control -> bounded stop`.
One Cpu, Bus and immutable PROGRAM source are retained for each case. The M2bv
P2 latch and its actual native writer generation are not copied into another
machine, imported from JSON or reseeded at a continuation PC. The initial
technical setup occurs once before the first functional instruction at54F5.

The separate feature `p28-word0196-post-p2-control` depends on the existing
`p28-word0196-p2-handoff` feature and is default OFF. It grants only the new
closed capability; historical Session1..16 admission, M2bu/M2bv budgets and
ordinary runner behavior are not widened. Production decode and Exec provide
the observations; an independent reference supplies the expectations.

| Path | M2bv instructions | Added instructions | Exact M2bw budget | Stop BEFORE |
| --- | ---: | ---: | ---: | --- |
| A, Below | 17 | 4 | 21 | 55D2, ROLB A |
| B, NotBelow and first gate | 19 | 1 | 20 | 559D, PSWH/MIE RMW |
| C, NotBelow and second gate | 20 | 1 | 21 | 559D, PSWH/MIE RMW |
| D, NotBelow and both gates false | 22 | 1 | 23 | 559D, PSWH/MIE RMW |

The 24 M2bu sites, two M2bv P2 sites and five new unique sites form a closed
31-site inventory. Private PROGRAM is exactly221 unchanged original bytes in
`[54F5,55D2)`, at their original addresses. Gaps and unselected instructions
remain non-executable. The unchanged M2bs verifier binds the private whole
image, profile, source/listing and selected extents before admission and checks
the immutable source again after execution. Public tests use an independently
invented program, never an OEM window or private original image.

## Independent primary instruction authority

The full relevant pages of the OKI MSM66201 Instruction Manual, first edition
September1991, SHA-256
`f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271`,
were visually reviewed, including function, flags, operand rows and cycle tables.
Printed page labels control; renderer page numbers are not a universal offset.
These rules agree with the frozen [M2ab contract](M2AB_POST_P2_CONTROL_HANDOFF.md).
Production Rust output is not their semantic authority.

| Exact new site | Reviewed manufacturer rule | Defined flag effects | Retained fields |
| --- | --- | --- | --- |
| 55C8, SB TCON0.2 ->55CB | Set addressed byte bit2; printed3-127 | ZF is1 iff the OLD bit2 was0 | A/AL/AH, CF, HC, DD and other PSW |
| 55CB, LB A,DATA018E ->55CD | Load the byte into AL; printed3-70 | ZF from loaded byte; DD=0 | AH, CF, HC and other PSW |
| 55CD, XORB AL,immediateFF ->55CF | Byte XOR in DD0; printed3-175 | ZF from the new AL | AH, CF, HC, DD and other PSW |
| 55CF, MB C,ACC006.7 ->55D2 | Copy the addressed byte bit7 into carry; printed3-77 | CF only | A/AL/AH, ZF, HC, DD and other PSW |
| 5599, ANDB TRNSIT,immediateFB ->559D | Byte AND RMW; printed3-27 | ZF from the complete byte result | A/AL/AH, CF, HC, DD and other PSW |

DATA0006 is the architectural AL alias, not a separate RAM byte. The MB operand
must therefore read AL after the actual preceding XORB. Its functional DATA
read is retained in the journal. LB does not sign-extend or replace AH; AH is
retained from the earlier native word load of DATA0196/0197 at54FA.

Checking terminal flags alone is insufficient. SB's old-bit ZF is subsequently
overwritten by LB and XORB. MB must retain the latter ZF while writing CF.
Full per-instruction PSW comparisons detect a wrong intermediate value even
when the final accumulator happens to match.

## Bounded control storage and technical initial state

The matching MSM66201/207 manufacturer peripheral scans establish register
semantics independently of the ISA. The preserved package SHA-256 is
`f061cb5bcbd1804699fb60b543c425646fbb15b939c9bc51b24edbb4da4c6ddf`.
The actual family heading at12, register table42, timer Table9-1 at83,
Fig9-2 at85, realtime-output section92-93 and TRNSIT Fig14-1 at160 were reviewed.
Standard-device applicability does not establish the customer ECU ASIC/revision,
board wiring or electrical role. The old M2ab storage contract is retained.

Initial P2 output-data latch, P2IO=FF, P2SF=07, TCON0 and TRNSIT are explicit
once-only technical snapshots before54F5. Their classification is
`TechnicalArchitecturalControlSnapshot_NoNativeWriterGeneration`. They do not
claim reset, startup execution or a current native initial owner. No historical
M2ab generation is transferred into the new session.

TCON0 is byte SFR0040. Only83/87/8B/8F are admitted: mode bits0..1=11,
RUN bit4=0, clock bits5..7=100, output bit2 and buffer bit3 variable. For PathA,
the native SB at55C8 reads old bit2 and sets only that bit. Thus83->87 and
8B->8F have intermediate ZF1;87->87 and8F->8F have intermediate ZF0.
Same-value writes remain actual new generations. Mode, clock, RUN and buffer
bits are retained, as are all unaddressed control state.

The current bit executor reads the old bit, re-reads the byte for modification,
then writes it: two native byte reads and one native byte write are expected.
These are software journal events, not physical bus-cycle counts. The control
generation is attached to that one actual write, not to each journal view.

The manufacturer warns at93 about TCON RMW immediately before buffer-to-output
transfer. The stopped RUN0 domain and exclusion of counter/compare execution
bound that hazard out of this software experiment. No timer phase, TM/TMR value,
tick, transfer, interrupt or output edge is invented. Capture-mode bit2 has
different semantics and is not admitted by analogy.

TRNSIT is byte SFR0046 with four implemented flags0..3. Nonexistent bits4..7
read1 and are not retained physical storage. For B/C/D the CPU reads
`F0 | implementedFlags`, ANDs withFB, and writes the resulting byte. Only
implemented flag2 is cleared; the other flags retain their values. ZF is0
because the high read-one bits make the full byte result nonzero, including
when every implemented flag is cleared. No W1C, read-clear, command/strobe,
external falling edge or IRQ semantics are invented for this storage register.
The actual write journal retains the complete CPU byte. Retained TRNSIT storage
and its generation value contain only the implemented low nibble; these two
representations must be compared separately, without inventing high storage bits.

Only the exact P2 instruction from M2bv, TCON0 at55C8/PathA, and TRNSIT at5599/
PathsB/C/D have native byte access. Cross-path access, wrong PC/width, IO/SF
writes, neighbors and other SFR refuse. The new control capability closes after
its one admitted control instruction. No host SFR write or reinitialization is
allowed after functional execution starts.

## Ordered observations and independent comparison

The reference extends independently derived M2bu/M2bv predecessor, algorithm and
P2 expectations using the primary rules above and the retained M2ab register
model. It does not consume actual Rust states as expected-state inputs. Freeze
the source/corpus/program/oracle identities, budgets, terminal PCs and complete
expected streams before the first final-source positive execution.

Compare every selected decode identity and operands, PC before/after, complete
A/AL/AH/PSW/CF/ZF/HC/DD/OtherPSW, LRB/SCB/SSP/pointing and local-bank aliases,
untouched DATA, PROGRAM acquisition, logical/raw DATA events and separate
ordered P2/control reads/writes. Keep same-value stores and distinct writer
ordinals. A native control write creates one current-session generation after
the retained P2 generation; initial snapshots create none. Multiple views of
one write do not become multiple semantic generations.

The small positive corpus contains32 private original-byte cases and32 public
invented cases, eight per path in each mode. Independently computed retirement
totals are `8*(21+20+21+23)=680` per mode and1360 combined. Technical SF variants,
PSW retention, both old TCON0 bit2 values, TRNSIT flag2 set/clear, representative
low-nibble combinations and same-value control writes are required. Targeted
refusals are accounted separately; they never inflate positive counts.

First mismatch retains case/PC/field/expected/actual/source fingerprint and
blocks acceptance. A partial or ambiguous result is preserved, not repaired by
changing expectations, dropping fields or silently repeating completed cases.

## Diagnostic timing remains qualified

For the five new exact forms, the reviewed manufacturer INT rows are SB9,
LB4, XORB-immediate4, MB7 and ANDB-immediate8. The retained software counter
derives those respective diagnostic deltas from its existing static rules;
that correspondence is limited to these rows, not global timing correctness.
Actual counters must still be retained and compared in every canonical record.

The earlier three-byte P2 ANDB/ORB instruction retains the explicitly approved
software diagnostic delta6 against manufacturer INT7. M2bw changes no global
cycle rule to conceal it. `DiagnosticCycleTimingEquivalenceNotEstablished`
remains, and none of these counts establishes physical clocks, elapsed ECU
time, external-memory timing or hardware scheduling.

## Owned outputs, resume and delivery

Every local M2bw Cargo build/test requires both CARGO_TARGET_DIR and explicit
--target-dir to name `.tmp/m2bw-owned/cargo-target`, after ownership,
reparse/junction/symlink, custom-output and protected-path preflight. Preserve
historical runner identities before and after builds. Existing Cargo/NuGet
caches are reused without copying them or cloning the project.

The atomic checkpoint is `private/reports/m2bw/RESUME_STATE.json`. It binds
source/corpus/freeze, complete case IDs and canonical hashes, owned process
identity, QA phase, next action, final commit, CI run, comparison and seal state.
Resume reads actual receipts and checks existing processes before doing the
next unfinished step. Do not rerun complete cases or start another CI run just
because an answer/session was interrupted. Explicit user PAUSE remains binding;
the checkpoint does not run Codex or background automation by itself.

Private ROM execution remains local. CI preserves the prior nine required jobs,
including M2bu/M2bv at their pinned accepted source identities and the existing
Desktop checks, and adds only two current-source M2bw Ubuntu/Windows jobs.
The public artifact is the closed four-file canonical/summary/freeze/sourcejoin
set. Compare full decompressed public canonical bytes across local, Ubuntu and
Windows; no semantic or diagnostic fields are removed for platform equality.

Final delivery requires32+32 complete cases,1360 retirements, all independent
state/journal/generation comparisons, source fences, required exact-SHA CI,
cross-platform byte equality, scoped privacy/preservation and evidence seal.
The Ukrainian private FINAL report is written last. Static documentation grants
none of those observed PASS states.

The inherited generated historical-runner loss remains visible:
`AuthorizedPreservationExceptions=1`, `StrictHistoricalPreservationPass=false`.
New unauthorized differences must be0; no old expected fingerprint or
historical validator is rewritten. Only the qualified successful verdict is
permitted after all gates:
`M2bw ACCEPTED_WITH_HISTORICAL_PRESERVATION_EXCEPTION / Research-Only - Technical Post-P2 Control Continuity Verified`.

ActualHardwareEcuExecutionNotObserved; RecoveredFullEcuSchedulerNotEstablished;
PhysicalSFNotEstablished; NativeStackSafetyNotEstablished;
NativeP2InitialOwnershipNotEstablished; NativeTCON0InitialOwnershipNotEstablished;
NativeTRNSITInitialOwnershipNotEstablished; TimerEvolutionNotModeled;
IRQDeliveryNotInjected; PhysicalTimingEquivalenceNotEstablished;
ElectricalOutputNotObserved; ActualNativeDownstreamRejoinNotEstablished;
SafeROMPlacementNotEstablished; TargetProgramEquivalenceNotEstablished;
FirmwareIntegrationNotEstablished; FirmwareReady=false remain.

STOP after delivery. No M2bx, ROLB/second-P2/RT continuation, PSWH/MIE/timer/IRQ
execution, firmware/object/BIN/HEX generation, ROM patching, GUI or hardware.
