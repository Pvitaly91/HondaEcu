# M2by - bounded native CAL/RT return-frame continuity

This document defines a research-only execution protocol, not an execution
receipt. New observations, source identities and delivery results belong to
the separate source-bound private report. Neither this specification nor the
historical M2ad observations can establish a new completed round trip.

The accepted base is M2bx commit
`832b7c382076a8a441e48d2d19917aa43118eb37`, on
`codex/p28-word0196-below-second-p2-continuity-m2bx`. The new branch is
`codex/p28-word0196-cal-rt-frame-continuity-m2by`. The new default-off feature
`p28-word0196-cal-rt-continuity` depends on
`p28-word0196-below-second-p2-continuity`. Existing runner operations, generic
Session admission and historical feature budgets keep their previous meanings.

## Independent authority and historical scope

The manufacturer instruction authority is the OKI MSM66201 Instruction Manual,
first edition September 1991, SHA-256
`f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271`.
Complete retained primary pages were visually reviewed: CAL address3-29,
RT3-125, system-stack1-17, word-boundary1-18..1-20, little-endian1-5 and
SSP-addressing2-3. Printed labels identify the pages. CAL and RT are exact
DD-independent forms; instruction recognition is not independent ISA evidence.

[M2ad](M2AD_CAL_RT_ROUNDTRIP.md) already established a bounded native CAL063B
and matching RT5688 on its historical machine. The new experiment reuses the
existing production CAL/RT implementation and its reviewed architectural
semantics; it does not invoke the old standalone operation as a replacement
for a current audited Session. The M2ad PC-only05ED-to063B harness seam remains
an explicitly disclosed scheduling assumption.
[M2ae](M2AE_POST_RETURN_SELECTOR_HANDOFF.md) separately records the later
exact-M2ad-commit CI closure, while the earlier private M2ad report remains
unchanged. Neither event proves an enclosing caller or physical ECU scheduler.

The independent callee expectation is the unchanged M2bx39-step mathematical
model, with [M2ac](M2AC_BELOW_SECOND_P2_HANDOFF.md) ISA review,
[M2aw](M2AW_NX8_200_TARGET_ABI_CONTRACT.md) context qualifications and the
[M2bs](M2BS_ORIGINAL_ROM_BOUNDARY_NATIVE_CONTEXT.md) whole-image/listing
admission. The [M2aj](M2AJ_PRE063B_CALLER_PROVENANCE.md) caller analysis and
[M2ap](M2AP_SSP_ADC_PENDING_PROVENANCE.md) alias analysis retain their unknowns.
Expected stack arithmetic, state and effects must be frozen before actual
production execution; observed Rust values must not supply expectations.

## One retained machine and two immutable PROGRAM windows

Each positive case initializes one production Cpu and one Bus before its first
functional instruction, then retains them through:

```text
063B CAL -> 54F5 -> complete M2bx39-step Below body -> 5688 RT
-> 063E STOP BEFORE instruction acquisition or execution
```

The private PROGRAM source is one verified, unchanged original image. Two
read-only windows retain their original addresses:

| Window | Length | Purpose |
|---|---:|---|
| [063B,063E) | 3 bytes | Original CAL instruction |
| [54F5,5689) | 404 bytes | Existing callee range plus original RT |

There is no relocation, padding, synthetic private CAL, replacement return
instruction or generic whole-ROM execution permission. Existing M2bs source,
profile and frozen listing bindings authenticate the selected original image;
all selected extents and the input fence must agree before and after runtime.
Window membership grants no permission to execute gap bytes or unselected CFG
nodes. The source inventory is49 retained M2bx sites plus CAL063B and RT5688,
giving51 unique sites. Only the closed41-instruction route is a successful case.

Production decoder selection and Exec produce every transition after entry.
Technical initial PC063B is allowed before the first instruction. Later host
PC writes, second-machine transfers, CPU/Bus reconstruction, state imports,
RAM rollback or mid-execution register/stack/peripheral repair are refused.
Public CI uses a separately invented two-window program and distinct program
identity. Original opcode windows and private stack observations stay private.

## Independently counted route

The following sequence is an expected structural obligation, not an actual
execution trace:

```text
063B
54F5 54F8 54FA 54FC 54FD 5501
556F 5571 5572 5575 5576 5578 557D 55BF 55C1 55C3
55C5 55C8 55CB 55CD 55CF
55D2 55D3 55D5 55D8 55DB 562C 562E 5631 5633
565D 565F 5661 5671 5673 567E 5680 5682 5685
5688 -> 063E STOP
```

The algorithm portion above includes the original Below operations and their
ordered boundaries. The authoritative closed route must contain exactly the
retained39 M2bx retirements, one initial CAL and one final RT:

| Component | Retirements |
|---|---:|
| CAL | 1 |
| Predecessor | 6 |
| Original Below algorithm | 10 |
| First P2 | 1 |
| Previous post-P2 prefix | 4 |
| Below continuation | 18 |
| RT | 1 |
| Total | 41 |

Counters are hierarchical: the aggregate two-P2 count overlaps the callee
components and is not added again. The old M2bx budget remains39; this closed
composition does not enlarge an old constructor. Unexpected paths, extra
retirements, another CAL/RT or unselected successors cannot count as success.

## CAL creates the frame

At CAL063B, production Exec obtains its target from the admitted original
instruction and computes nextPC063E from the actual three-byte instruction.
For the explicit technical incoming SSP `s`, the documented operation is:

1. Write word063E at DATA addresses `s` and `s+1`, little-endian.
2. Set SSP to `s-2`.
3. Clear the existing internal host SF field.
4. Transfer to54F5.

The word store is one logical16-bit functional DATA write and two ordered raw
byte writes. It must be an actual production operation, not a diagnostic
readback or host-supplied frame. CAL preserves A, LRB, pointing/local context
and the architectural PSW, including CF/ZF/HC/DD and retained OtherPSW.

The corpus covers four even technical stack addresses:

| Incoming SSP / frame | Post-CAL SSP | Final SSP after matching RT |
|---|---|---|
| 0702 /0702..0703 | 0700 | 0702 |
| 0720 /0720..0721 | 071E | 0720 |
| 07FC /07FC..07FD | 07FA | 07FC |
| 07FE /07FE..07FF | 07FC | 07FE |

These frame pairs are disjoint from the admitted body RAM0108..0117,
0124/0128/012A/018E/018F/0196/0197, all pointing-bank storage0080..00BF,
CPU register aliases0000..0007, P20024 and control0040/0042. The selected body
has no admitted indirect access that creates another frame overlap. Evenness,
non-wrap and non-overlap are closed technical admission requirements, not a
claim about available physical ECU RAM or actual native stack ownership.

The primary manual masks the low address bit for ordinary DATA/system-stack
word access. Refusing an odd SSP in this experiment is a stricter research
domain; it does not establish a hardware alignment fault on odd addresses.

Two explicit technical canary bytes initialize the selected frame location
before execution. Different canaries, including a pre-existing word063E, must
not provide return authority. Even an equal-value CAL store must create a new
generation on the current machine.

## Fresh generation and matching RT consumption

The frame identity retains current machine ID, writer PC063B, native retirement
index, old SSP/address, width16, actual low/high byte values, returnPC063E,
logical event/write ordinals, raw event/write ordinals, all-native write
ordinal and source generation. Event positions and write-only counters are
different fields and cannot be substituted for one another.

With23 body DATA bytes, two stack-canary bytes and32 pointing-word seeds,
setup has57 logical writes and89 raw byte writes. The CAL is all-native write
ordinal0, logical write ordinal57, raw write ordinals89/90 and fresh frame
generation1. Relative to the unchanged M2bx body, native write ordinals shift
by1, logical write ordinals by3 and raw write ordinals by4. These are
independently derived expected counters; actual journals must verify them.
One semantic store is not counted twice merely because several journals
describe it.

Every intervening functional RAM write must be checked for byte overlap with
the newly created two-byte frame. Comparing only the terminal numeric PC is
insufficient. An equal-value intervening writer also breaks the required
uninterrupted CAL storage generation. Initial canary or older historical
frames must not replace this new writer.

After all39 callee instructions, actual PC must be5688 and SSP must still be
`s-2`. The actual original RT performs:

1. Set SSP to `s` before the functional read.
2. Read the word at `s` through production DATA services.
3. Verify that the read consumes the current CAL063B generation.
4. Set PC from that actual read and clear the internal host SF field.
5. Close the stack capability with PC063E and SSP restored to incoming `s`.

RT preserves the callee's A, LRB and architectural PSW. It does not restore
the initial caller's accumulator or flags, or pop an invented interrupt frame.
The callee legitimately changes state; the post-RT state must retain those
results. RTI is a separate instruction and is not admitted. No instruction
starting at063E may be decoded, selected or retired in M2by.

An incomplete route retains actual CAL writes, SSP and later observations,
without rollback or a manufactured return. Such a record may establish
`CallerFrameEstablishedPendingReturn`; it cannot count as a positive completed
round trip. A historical machine ID or a copied snapshot is not continuity.

## Callee effects and input ownership remain explicit

The two P2 generations G1/G2 and two stopped-control generations T1/T2 retain
their existing M2bx meanings and ordered journals. Same-value second-P2 writes
remain fresh generations. Native RAM0116,0110/0112/0114,018F and012A effects,
the coupled ROL/CF relation and the taken JNE5661 remain independently checked.
New stack permission cannot enlarge existing P2/control/SFR permissions.

Initial PC063B, SSP, RAM, P2/control snapshots and host SF are technical inputs.
The39-step body reads DATA0196 but does not execute its historical upstream
producer. Therefore:

`DATA0196Owner=TechnicalSeed_NoNativeProducerInThisSession`

The new CAL creates a genuine native frame generation inside this technical
machine. It does not convert technical DATA0196 into a native upstream owner,
import M2ad's G0196, recover05ED-to063B scheduling or prove an enclosing IRQ.

## SF and diagnostic timing qualification

The MSM66201 instruction pages print SF-clear for CAL and RT. MAC66K third
edition November1993, SHA-256
`ab616efc40babc07d28f44e2e46f8fe53e6c0ddb4edbe948bb02c8ac098b4f2d`,
describes SF as specific to nX-8/300 at4-73 and4-116. M2aw retains this primary
applicability ambiguity. Both technical host-SF initial values are checked
against the existing software clear behavior; no physical SF storage, width,
PSW mapping, hardware value or target applicability is invented.

Primary CAL INT9/EXT13 and RT INT7/EXT11 are distinct documented costs. The
current software diagnostic deltas9 and7 agree with those two INT entries.
The inherited first/second P2 software6 versus manufacturer INT7 differences
remain, as do their actual diagnostic fields and complete comparisons.
`DiagnosticCycleTimingEquivalenceNotEstablished` and
`PhysicalTimingEquivalenceNotEstablished` remain. Retirement counts and
software counters are not physical elapsed time or electrical bus cycles.

## Frozen observations, bounded QA and delivery

Before the first final runtime, freeze complete source/corpus/oracle identities,
both original source windows, all41 expected boundaries, stack/SSP arithmetic,
instruction forms, full CPU/PSW/pointing/local/RAM expectations and ordered
PROGRAM/DATA/stack/P2/control journals. Decoder probes, architectural selected
fetches, diagnostic snapshots and functional accesses remain separate records.
Preserve the first case/PC/field/expected/actual mismatch without adapting
expectations to production output.

The corpus is16 new private original-byte cases and16 independently invented
public cases, all completed Below CAL/RT round trips. Each domain must contain
656 retirements; the combined local total is1312. Cover all four admitted SSP
values, varied and equal-value canaries, Below words, incoming DD/CF/HC/OtherPSW/
SCB, technical host-SF pairs, P2 initial00/FF/A5, all four stopped TCON0 values,
fresh generations, actual RT reads and retained full callee state. Historical
M2bt-through-M2bx private corpora and the5470-case corpus are not rerun merely
to create new observations.

Bounded negative tests must reject altered sources/forms, stale or absent CAL
writers, wrong frame addresses/endianness/ordinals, odd/out-of-domain/wrapping
SSP, overlapping post-CAL writes, fake RTI or A/PSW/LRB restoration, wrong SF,
host entry/PC jumps/reseeds, second machines, extra retirements, post-return
execution, corrupted/duplicate canonical records and unsafe Cargo outputs.
Incomplete cases cannot be promoted to complete records after resume.

Local Cargo commands require both CARGO_TARGET_DIR and --target-dir to name
`.tmp/m2by-owned/cargo-target`, with ownership, reparse, custom-output and
protected-path overlap guards plus pre/post preservation fences. No cache,
repository or historical worktree copies are required. The inherited generated
historical-runner loss remains exception1; strict historical preservation is
false. New unauthorized protected differences must be0; historical expected
hashes and validators are not rewritten.

Reuse atomic checkpoints and the existing complete-record resume controller.
Reconcile source/corpus hashes, owned process identity and saved observations
before continuing; do not duplicate a completed case or a running CI job.
Respect an explicit pause without background automation or unbounded polling.

Formatting and targeted QA precede final source freeze. Preserve all previous
required CI gates and add Ubuntu/Windows M2by jobs; the reviewed workflow is
expected to contain15 jobs. After normal commit/push, require success on the
exact final SHA and full decompressed public canonical byte equality across
local, Ubuntu and Windows, excluding no state, stack, execution or diagnostic
field. Private ROM data never goes to CI. Scoped source/privacy/preservation
verification and evidence sealing precede the private Ukrainian FINAL report,
which is written last.

## Classification and retained unknowns

Only all required execution, oracle, preservation, exact-SHA CI, full-byte
comparison and seal gates permit:

`M2by ACCEPTED_WITH_HISTORICAL_PRESERVATION_EXCEPTION / Research-Only - Technical Native CAL/RT Frame Continuity Verified`

`TechnicalNativeCallReturnRoundTripVerified` applies only to this bounded
technical machine. It does not establish the upstream scheduler, a physical
ECU call stack or native return into subsequently executed firmware.

Retain: ActualHardwareEcuExecutionNotObserved;
FullNativeCallerSchedulerNotEstablished; RecoveredFullEcuSchedulerNotEstablished;
EnclosingIRQFrameNotEstablished; PhysicalSFNotEstablished;
PhysicalNativeStackSafetyNotEstablished; InitialP2NativeOwnershipNotEstablished;
InitialTCON0NativeOwnershipNotEstablished; TimerEvolutionNotModeled;
IRQDeliveryNotInjected; ElectricalOutputNotObserved;
PostReturn063ECodeNotExecutedInM2by; FullNativeDownstreamRejoinNotEstablished;
SafeROMPlacementNotEstablished; TargetProgramEquivalenceNotEstablished;
FirmwareIntegrationNotEstablished; FirmwareReady=false.

After delivery, STOP. No M2bz, post-return063E execution, IRQ/timer research,
ROM patching/placement, firmware generation, flashing, GUI or hardware is
authorized by this milestone.
