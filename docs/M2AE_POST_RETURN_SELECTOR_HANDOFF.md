# M2ae — native post-return selector013C producer and scheduled handoff

Exact base is `70be14d042fecf45c813f3975475932d0eaa8f14`, M2ad branch
`codex/p28-cal-rt-roundtrip-m2ad`. Its immutable commit subsequently reached
CI3/3 success in run37366414569/attempt3; its historical private final report
was intentionally not rewritten during that external delivery closure.
M2ae is a separate runner0.38.0 operation `postReturnSelectorHandoff`.

## Native entry and exact software boundary

One persistent Cpu/Bus carries the existing M2r quartet/M2x0196, disclosed
PC-only05ED→063B harness schedule, native CAL063B, complete validated below
callee, second P2 and same-frame RT5688. Only the new operation continues
the **actual RT exit063E**. No host PC063E/064A/0584 shortcut or state copy.
Historical M2ad still stops before063E; all older contracts remain bounded.

Fresh private ROM/listing audit verifies every exact form and the first next
branch. Complete manufacturer pages were visually inspected with the PDF skill.
No OEM byte windows are published. The new native range is `[063E,064C)`,
eight instructions/fourteen bytes, budget8; stop BEFORE executing064C.

| PC | Exact form | Effective software effect | Flags / primary page |
|---|---|---|---|
|063E|LB A,off013C|Read old byte013C into AL; AH retained|ZF from byte; DD0; CF/HC/other PSW retained;3-70|
|0640|STB A,r0|Write old selector to local0108|No flags; DD0;3-155|
|0641|ANDB A,#1|AL becomes oldSelector&1|ZF only; DD0 required;3-24|
|0643|SBR off0128|Set bit indexed by AL[2:0], hence bit0 or1 of0128|ZF=inverse old bit; other flags/A retained;3-136|
|0646|INCB r0|Native byte0108+1|ZF/HC updated; CF/DD/A retained;3-61|
|0647|LB A,r0|Load incremented byte0108 into AL|ZF/DD0; AH and other flags retained;3-70|
|0648|ANDB A,#3|Mask AL to0..3|ZF only; DD0;3-24|
|064A|STB A,off013C|Native byte selector store|No flags; DD0;3-155|

LRB remains0021, current off-page0100 and local bank0108. Incoming r0 is
fully overwritten at0640 before its increment/read; no host r0 source.
Final r0 is oldSelector+1 (thus4 for old3), while final AL/013C is masked0.
The independently derived formula is `((oldSelector+1)&255)&3` in the admitted
once-initial0..3 domain:0→1,1→2,2→3,3→0. No global whole-ROM domain claim.

Primary3-136 has an apparent print inconsistency: its Function line prints
bit←0, whereas SET heading and detailed description explicitly say set to1.
The paired primary RBR3-115 is RESET with a different operation encoding.
The narrow SBR admission follows the explicit SET description and paired form;
the inconsistency is disclosed, not presented as a manufacturer-issued erratum.

INCB r0 exposed stale HC in the generic executor. An invented decoded test
failed before correction, including oldHC1/value00 requiring HC0. The minimal
fix touches only compact `INCB r0`, with identity `byte-incb-r0-half-carry`;
all bytes/prior flags/banks are tested. No other INCB/rN, SUBB, rotate, disputed
4781/4581 or JGT form is promoted. RTI and CAL/RT semantics are unchanged.

## Once-only source, native generations and next event

The new closed scenario has `initialSelector013c` exactly once per machine.
Classification:`RawSoftwareSnapshot0..3;OnceOnly;InitialGenerationNone`.
New calls contain ONLY the required `prefix`, never `selector013c`.
Unknown per-event selector/expected result/slot/address/PC/branch fields are
rejected, not ignored. Historical M2x still accepts its per-event snapshots.
Internal historical input-schema reuse does not supply the M2ae selector model:
expected values come from the independently owned retained RAM history.

After initialization the opt-in guard uses actual RAM013C and allows only the
reviewed native byte writer064A. Host reseed, another PC, repeated initializer
and overlapping word stores are refused; older operations do not enable it.
The sequence records one initialization write; event selector source writes=0.

Native generation is `(writerPC064A,eventIndex,zeroBasedAllNativeEventWriteOrder,
value)`, counting RAM, system-stack, P2 and control writes together. Correct
numbers with stale/wrong identities fail. C# owns old selector, r0,0128,
arithmetic/flags, new generation and slot/address derivation independently.
Rust selector observations never become expected operands.

Event0 reader uses the initial snapshot and is `InitialSelectorControl`, not
native selector handoff. Completed native064A creates a generation. The next
explicitly scheduled event retains it without host013C write; actual0584
reads that generation and native arithmetic selects03B6/03B8/03BA/03BC,
with matching03BE/03C0/03C2/03C4 companion. Actual05DF must read the current
selected quartet generation; correct value from wrong address is insufficient.

This is RAM/provenance continuity across `ExplicitHarnessSchedule`, NOT
continuous firmware PC scheduling064A→0584 or recovered ECU/caller/IRQ loop.
Other explicit013C writers03D7/0551/15A0 are excluded; generic aliases outside
the bounded scope remain Unknown, not a sole-producer assertion.

## Retained0128,0117 and honest partials

0643 computes `old0128 OR (1 << (oldSelector&1))`: only bit0/1 may be set;
gate bit2 and every neighbor are retained. Existing once-initial masked bit2
and known technical canary neighbors remain independently owned history.
Intermediate SBR ZF depends on the known old bit, then later native operations
overwrite it; unknown scratch is not a selector/arithmetic input.
No0128 repair or whole-byte replacement is permitted.

The existing native below body stores0117=15 at55C1. In actual multi-event
proof, the next event can still perform the strict0584 selector-generation
handoff and05DF selected-word read, but its later callee takes5501→5503.
It stops BEFORE the excluded TM0 read; no timer instruction is executed.
Therefore a five-completed-event natural producer cycle is not reached under
this retained0117 history. It is not repaired, reseeded or silently skipped.

Part A completed producer, Part B next-event handoff, and whole-event completion
are reported separately. All four individual native transitions and wrap are
covered using independent once-initial0/1/2/3 scenarios. A five-event cycle is
invented/synthetic coverage only, not actual natural firmware scheduling.
Partial retains native RAM/generations, peripheral effects and actual SSP;
later events are NotRun without applying inputs or rollback. Gate-bypass
mechanics and initial controls do not count as strict quartet-derived handoffs.

## Read-only protocol, CLI and compatibility

Protocol1, pinned Rust1.85.1 and repository.NET8. Historical0.37 refuses M2ae.
Scenario formatVersion1,purpose`native-post-return-selector-handoff-test`
reuses established initial/upstream/P2/TCON/TRNSIT sources, removes only the
per-event selector and adds its once-initial counterpart. No timer/IRQ,
arbitrary RAM, ready0196, expected selector, selected slot or output BIN API.

```text
hondaecu research p28-fuel post-return-selector-check <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --runner <runner-0.38.0> --scenario <m2ae-scenario.json>
  --output <new-private-report.json>
```

Exact binding/profile, bounded input/process, cancellation, alias/no-overwrite
and unchanged-input guards remain. Mixed terminal sequences have exit3/Partial
even when their bounded Part A and Part B evidence is independently Validated.
Single-event producer-only success does not claim a next-event handoff.
Compatibility normalizes only runnerVersion and the one appended INCB identity;
old M2ad CAL/RT, M2ac ROLB, M2aa capability and M2x selector sources retain their
historical serialized behavior. M2u stays static-only, not fake dynamic coverage.
Public tests/CI use invented programs/model-only fixtures, no OEM windows.

## Static future boundary and exclusions

064C is JBS off011F.3: taken065F, fallthrough064F. Later branches inspect011B.7
and012A.0; fallthrough first touches TRNSIT at0657. Taken-path helper CAL0664
targets56BE. These and all code at/after064C are STATIC ONLY, not M2ae execution.

RecoveredQuartet/Caller/0196/EcuSchedulerNotEstablished; Branch064CNotRun;
TimerEvolutionNotModeled;TimerContinuationNotRun;IRQDeliveryNotInjected;
ElapsedTimeNone;P2ElectricalPinsNotModeled;PhysicalOutput/hardwareNotRun;
PhysicalP2Role/Polarity/ChannelAssignmentUnknown. M2tJgtBlocked/Unresolved;
PcInspectionOnly/NotFlashReady;physicalRpmAvailablefalse;physical fuel/time/degrees
unavailable;strictM2iBlocked;GUIr3paused/NotRun;D1/D2interactive/fullbootNotRun;
FirmwareBIN/newbinding/compensation/exportplan/receipt/token0.
No automatic M2af,064C,caller/IRQ/timer/RTI/JGT/GUI/hardware continuation.
