# M2ar - Reset state, WDT24F4 and external DATA4700 provenance

## Result and new evidence

**Research/Blocked / RootedNativeExecutionPreflightBlocked.** New dated primary
evidence defines a narrow standard-device reset state; a new bounded numeric
noninterference proof removes DATA4700 as a value-decision gate for the audited
prefix. Exact ECU applicability, actual reset/history, WDT command3C and external
read effects remain unestablished. M2ar actual-ROM executions=0; no Cpu/Bus,
synthetic reset execution, operation, admission or host input was created.

Exact base `4e684bfb25743d2311552b7151c9ee34b0b9bbf2`,
`codex/p28-first-ramtest-native-frame-m2aq`.
Branch `codex/p28-reset-wdt-external4700-m2ar`.
Runner0.41.0/protocol1 and M2an identity
`byte-sll-off-page-preserves-noncarry-flags` remain unchanged.
The earlier CAL/XCHG/RT findings are retained, not repeated as M2ar's main result.

## Primary documents and applicability

The complete30-page [OKI MSM66201/66P201/66207/66P207 specification,
E2E1027-27-Y4](https://files.boostednw.com/HONDA/66207.pdf) explicitly states
Jan1998, previous Nov1996, and nX-8/200. Complete original pages1,9,10 and17,
relevant pin/clock/bus pages and all SFR reset columns/notes were visually
reviewed. The fragmented HTML reset table was not used to assign columns.
This is a **specification sheet**, not the complete hardware user's manual.

M2am already recorded the [Manualslib lead](https://www.manualslib.com/manual/113785/Oki-Msm66201.html)
as index/device linkage, not acquired reset clarification. M2ar's complete local
PDF acquisition and independently reviewed reset table are new; the revision
itself was already discoverable. Manualslib/Manualsdump/other copies are not
independent manufacturer revisions. Private manifests record hashes, provenance,
reviewed complete pages, failed accesses and documentary lineage.

A separate older [Preliminary MSM66201/66P201 scan](https://www.datasheetarchive.com/datasheet/MSM66201/OKI-Electronic-Components?term=msm66201&version=2) was acquired:34 manufacturer
pages plus an unrelated distributor advertisement. Its electrical page says
First Edition Nov1990 and an archival stamp says Feb1991; neither establishes
the edition of every section or a particular ECU mask. Its reset table agrees
on SSP/ACC/PSW/WDT, but SBYCON saysF8 orF0 rather than Jan1998'sF8. Those
source-domain/revision limits remain explicit; an old preliminary table is not
an automatic override or proof of compatibility with every produced revision.

The existing September1991 MSM66201 Instruction Manual and incomplete
manufacturer MSM66201/207 user scans were reviewed for exact forms, vector,
reset/flag, standby and NMI rules. The user archive lacks verified cover/edition/
revision and omits hardware Chapter4 pages58..65. The similarly named Chapter3
ZIP contains instruction pages, not those missing hardware pages. No reviewed
document supplies WDT3C command decoding. No other MCU or nX-8/500S semantics
were substituted.

The new sheet expressly applies to standard MSM66201/66207 and their named OTP
variants; applicability to the concrete ECU remains **DeviceApplicabilityConditional**.
Reviewed legitimate manifests/binding identify ROM/profile, not verified chip
marking, package, mask revision or board decode. Neither image length32768,
P28 naming nor SSP047E identifies a66207. Customer-specific ASIC I/O/vector
variation is explicitly possible in the instruction reference. New physical
identification/board tracing is ExternalEvidenceNeeded, not performed.

## Reset causes, initial PC and wake separation

PROGRAM and DATA are independent spaces. DATA0000 is SSP storage, not the reset
vector. Standard vector words are little-endian and structural bound-ROM facts,
not observed hardware events or an assigned host PC.

| Event | Standard PC source / bound target | State and residual prerequisites |
| --- | --- | --- |
|Power-on | Autonomous POR detector/vector semantics not established; a qualifying RES sequence would use PROGRAM0000 ->24ED | Supply, oscillator, reset circuit/pulse/release and memory selection are external; supply rise alone is not proven RES |
|External RES | PROGRAM0000/1 ->24ED | Proper active-low reset processing before first instruction; actual transition/timing/device applicability missing |
|BRK | System reset, then PROGRAM0002/3 ->24F4 | Does not read0000 for its reset target; bypasses24ED marker and24F1 bit-clear sources |
|WDT reset | PROGRAM0004/5 ->24DC | Counter/command/clock/overflow/reset history not established |
|Opcode trap | PROGRAM0004/5 ->24DC | Trap enable/reset chronology remains separate; not an ordinary RES entry |
|NMI | PROGRAM0006/7 ->003C | Falling-edge interrupt, not reset; saves context/changes interrupt control, not universal reset defaults |
|HALT exit | Interrupt processing/resumption, or corresponding RES/WDT reset | CPU clock stopped; oscillator/TBC/WDT/timers/serial can continue; wake is not automatically reset |
|HOLD exit | Normally next instruction after HOLD H-to-L, or pending interrupt | CPU stopped; oscillator/peripherals can continue; a reset is a distinct cause |
|STOP exit | Interrupt resumption/processing or RES reset | Oscillator/TBC/WDT/timers/serial stopped; clock/wake history required; do not assign0000 to every wake |

PROGRAM0010 ->24D6 is Timer0 overflow, **not reset**. Qualified architecture
does not establish ActualResetEntryEstablished or RootedSoftwarePrefixEstablished.
ActualResetTransitionNotObserved and ActualMachineStateNotObserved remain.

## Exact narrow reset-state matrix

Values below are manufacturer architectural fields under their documented
standard-device reset domain, **not observed ECU state**, frozen future values,
or native producers for CAL2689. RES/WDT/OPTRP/BRK qualification is explicit in
the existing user text for ACC and writable PSW. Power-on/ASIC applicability
and detailed reset-release conditions cannot be filled from a constructor.

| Field | Architectural finding | Classification / limitation |
| --- | --- | --- |
|PC | Selected cause's PROGRAM vector word; not generic PC0000 | ManufacturerDefinedResetValue as vector-derived PC; actual cause/mapping unobserved |
|SSP0000/1 |FFFF | ManufacturerDefinedResetValue;047E requires genuinely reached MOV24F8 |
|ACC0006/7 |0000 | ManufacturerDefinedResetValue, not undefined; does not itself recompute ZF |
|PSWL / PSWH | ReadbackC8/0C | Writable fields0; reserved read-one bits are not physically writable ones |
|CF/ZF/HC/DD |0/0/0/0 | ManufacturerDefinedResetValue independently of ACC0 |
|SCB | Three bits2..0=0, PR0 selected | Does not initialize PR contents |
|PSW bit8 | Reset0 | Jan1998 page9 calls it MIP, user text calls MIE; the real naming discrepancy is retained, not a semantic/priority revision |
|User flags4/5/9 |0 | ManufacturerDefinedResetValue; page9 also duplicates the MIP label for user flags |
|LRB | Reset table says undefined | UndefinedAfterReset numerical value; user text says not affected at Reset, so known prior13-bit LRB preservation is conditional, not LRB0 |
|SF | Separate internal state; no reset value established in reviewed sources | InitialInternalStateNotSpecified / NotSpecified; CLR/reset PSW is not proof of SF0 |
|X1/X2/DP/USP, PR banks, internal RAM | Reset contents not supplied in reviewed tables | NotSpecified; no default-zero promise |
|External DATA | Board-dependent mapping/content/effects | ExternalHardwareDependent, no numeric reset value |
|WDT0011 | Write-only byte, reset00/stopped | ManufacturerDefinedResetValue for reset; not readback00 or command3C meaning |
|IRQ/IE |0000 at reset | Not proof of later pending/delivery or frozen peripheral values |
|PRPHF/SBYCON/EXICON | Jan1998 FD/F8/FC | Defined in that domain; older SBYCONF8/F0 source caveat retained |
|P0..P4 data, TRNSIT, serial buffers, ADCRs | Explicitly undefined | UndefinedAfterReset where stated; P5 input/dash does not promise0 |
|Port modes/secondary controls | IO00, P2SF07, P3SF/P4SF00 | Register defaults, not observed pin samples |
|Listed timer/PWM fields | Reset00 entries in SFR tables | No timer evolution, elapsed time or IRQ generation follows |

PSW writable maskF337 and read-one mask0CC8 are distinct. LRB has13 implemented
bits; conditional preservation cannot retain invented nonexistent upper bits.
The reset table and the user LRB-retention statement have separate value/effect
domains; complete cause/revision reconciliation remains missing. Generic
Cpu::new numbers are technical initialization, not manufacturer reset authority.

## WDT24F4 and the first SSP source

Exact static sequence, freshly matched against the private original:

| PC | Exact form / source | CPU/control distinction |
| --- | --- | --- |
|24ED | MOVB zero-page00F5,#46 | Byte immediate marker; no initial ACC/LRB/SSP/SCB operand; lexical next24F1 |
|24F1 | RB zero-page00B7.1 | Clears only bit1, ZF=!OLDbit1; neighbors unknown; next24F4 |
|24F4 | MOVB zero-page0011,#3C | Byte WDT command, not RAM echo or SBYCON0010; generic MOVB flags retained |
|24F8 | MOV SSP,#047E | Native immediate would own SSP if genuinely reached; next24FC |

These exact forms are DD-independent. There is no branch/call/stack access
before24F8 and no consumer of the old-bit ZF as PC source. Undefined initial
LRB/ACC/SSP/SF do not choose this **minimal numeric software succession**;
valid memory/bus and no asynchronous/control transition remain conditions.
This is not an actual reset-to-writer record.

WDT0011 is write-only byte control. Reset-stopped does **not** tell whether3C
starts, stops, reloads, requires a sequence or causes an immediate/conditional
reset. Both acquired specification sheets lack that decoding, divisor, overflow
interval and reset latency. `WdtCommandMeaningNotEstablished` therefore remains;
`WdtCommandArchitecturallySpecified` is not granted. Even delayed-only behavior
or guaranteed immediate continuation cannot be assumed. Software lexical24F8
is conditional on accepted write/no-control-transition, not HardwareSafeReaching.

OSC/RES/EA/FLT/READY and external-bus tables establish dependencies, not this
board's pin/clock/reset history. HALT/HOLD may allow WDT operation while CPU is
stopped; STOP stops its clock domain in the user reference. No instruction-count
to elapsed-time conversion, host timer, frozen WDT or guessed readback is used.

## DATA4700: mapping and exact load

Standard66201 DATA internal RAM ends027F, external starts0280. Standard66207
ends047F, external starts0480. DATA047E/F is external for66201 and internal for
66207; DATA4700 is external for both. PROGRAM4700 belongs to a separate program
space, with its own variant/EA-controlled mapping; its ROM byte is never used
as the DATA read. External addressing uses P0/P1, ALE/RD/WR and READY; those
signals do not establish board chip-select/decode, connected device or effects.

Native MOV DP2519 owns4700 under the retained native SCB0 domain. LB251C through
that DP loads **AL only**, retaining AH, setsDD0/ZF=(b==0), preservesCF/HC.
Successful nonstack/SF0 loads are a separate condition, not inferred from
CLRPSW24FF. The first such earlier source-context obligation is LB2502.
Architectural effective address/width is known; actual read value/decode/effects
and read history are unknown. No RAM/ROM/latch/open-bus/peripheral choice is made.

## New bounded numeric noninterference proof

Let b be **any mathematical byte**, u any prior00B7 byte and h any priorAH.
No b/u/h is assigned to runtime, and unknown b is never replaced with0.

| Step | Numeric dependency and native producer |
| --- | --- |
|RB24F1 | B7.1=0; all other old bits remain unknown |
|LB251C | AL=b, AH=h, DD0, ZF=(b==0) |
|SRLB251D | AL=b>>1; CF=b.bit0; ZF/HC/DD/AH retained, not recomputed from shifted AL |
|MB251E | Only B7.0=CF; current-page0 byte is same00B7 under retained LRB0010 |
|JBS2521 | Reads B7.1, not bit0/CF/ZF; false for every b, next2524 |
|MOVB2524 / JBR2528 | NativeF6=20; independent P4.1 at002C chooses252E or252B->003C |
|L252E#5555 | If legitimately reached in nonstack domain, kills AL/AH/ZF/DD taint; retains taintedCF |
|XCHG2531/2533 / CMP2535 | Exchanges retainCF; independent equal pattern CMP ownsCF0/ZF1 before JNE2538 |

Independent identity: `B7_after_MB=(u & FC)|(b & 01)`. Hence bit1 is0 for all
256 b and all256 u. For b=1, shiftedAL=0 but retainedZF=0; an ordinary
result-zero rule would be incorrect for this exact SRLB. Complete algebra
enumeration also checks AH retention, with262,144 assertions in the private
audit; those are mathematical checks, not machine events, instruction counts
or hardware samples.

Fresh167 bounded extents were checked for later consumers/aliases. B7.0 remains
tainted but is not read again before firstCAL2689. SCB0, temporary adjacent
SCB5/2 PSWL pairs without pointer accesses, local bases and explicit/indirect
footprints do not alias it in this domain. Subsequent flags/patterns/countdowns,
P4 samples and fresh PWM pending have their own producers, not b. Under retained
mapping/nonstack/no-hidden-mutation context and identical remaining legitimate
external histories, **ValueNoninterferenceProvenWithinDomain** reaches the
first-CAL boundary; it does not prove those other gates pass or CAL executes.

The regression fixture deliberately seals the narrow JBS2521->2524 policy and
conditional native flag kills, not a complete runtime-prefix journal. The
broader conditional static consumer audit is separate. Later26F3 reads B7.0
and26F6 saves it into r0.0 **after** the first calls/loop, limiting the theorem.
Do not claim global firmware/value irrelevance or create DATA019B ownership.

Numeric independence does not establish bus completion or absence of effects:
ExternalAddressArchitecturallyEstablished / ExternalDataAddressEstablished;
BoardDecodeNotEstablished; ReadValueNotEstablished / ExternalReadValueUnknown;
ReadSideEffectsNotEstablished / ExternalReadSideEffectsUnknown;
RuntimeReadNotObserved. ValueIndependentWithinAuditedCFG and
SideEffectsStillUnknown coexist. A hidden alias/context mutation remains outside
the domain, not falsely proved absent. P4.1 is the next genuine external **value**
predicate, not removed by this theorem.

## Revised frontier and impact

| Ordered obligation | M2ar architectural/static impact | Residual actual dependency |
| --- | --- | --- |
|Exact device/revision and qualified reset entry | Standard dated reset/vector specification found; selected fields defined | Concrete ECU applicability, RES/clock/memory history NotEstablished - earliest actual-history blocker |
|24F4 WDT | Write-only byte/reset-stopped confirmed | Exact3C meaning/sequence/control timing absent - first command gate even if entry supplied |
|2502 and later L/LB context | Minimal prefix toSSP does not need initial SF/LRB numbers | Successful nonstack/SF0 source not specified by PSW clear |
|251C DATA4700 | Address/width established; numeric control decision gate discharged in audited domain | Board decode, read side effects/completion and actual observation unknown |
|2528 P4.1 | Not a consumer of b | Genuine value/mode/read history missing |
|IE selftests / SFR setup | Independently code-owned commands, not echo guarantees | Applicable readback/control effects missing |
|P4.2/P4.3 and IRQH.5 | LOW/HIGH/LOW / fresh PWM factor remain independent | No actual samples/factor; cannot inject favorable history |
|Later pointer/ISA/frame requirements | Numerical producers and historical frame contracts retained | Actual history, exact admission/DEC DP fidelity/same machine/frame still absent |

Unknown DATA4700 **numeric value** is no longer listed as a value-decision
blocker for2524/first-CAL domain. Unknown read **effects** remain a mandatory
external boundary. Thus specific obligations are narrowed, not a falsely
counted aggregate preflight success. Initial reset defaults do not establish
runtime-initialized RAM, a recovered scheduler or a rooted native execution.

DEC DP/HC remains the unchanged M2aq static discrepancy, not fixed here.
It is later than the minimal reset/early numeric proof; pulsewait control uses
DEC'sZF and MBR'sCF, not HC. Full-state fidelity remains a separate ISA gate.
C8 PrimaryConflictUnresolved and M2an SLLB fix remain unchanged.

## Delivery, preserved boundaries and STOP

Only this research document, two invented-only Core files and minimal
README/ROADMAP links are public. Private primary/applicability/reset/SFR/WDT/
taint/frontier/impact manifests and final report remain under m2ar. Expected
model values are independent of Rust output; tests never instantiate Cpu/Bus,
seed reset/data/P4/IRQ/frame, grant admission or claim actual events.
Full Rust/Core/CLI/Desktop headless, new and relevant M2ap/M2aq tests, formatting,
privacy/diff, full protected SHA-256 and stabilization/historical runner checks
plus new exact-SHA Ubuntu/Windows/Desktop CI are required before the private
final report is saved last. Their results cannot promote research.

Any future read-only reset runner requires a separate approved design with
applicable reset/WDT/bus/SF sources, narrow exact-form admission, retained one
machine and stop-before-unknown. No such operation/version/schema/executor
implementation is included here; architecture defaults are not host seed fields.

M2aq remains Research/Blocked, CAL2689/RT5C80 NotRun, actual frameNotObserved,
restoredSSP047E NotEstablished; M2ap SSP/ADC Research/Blocked; M2ao frontier
afterCLR2758/beforeSTIE2759; M2ak source-to5722 Research/Blocked; M2al/M2am C8
unresolved; M2an complete; M2ah STOPbefore5722,019B.2 actual ownerNotEstablished,
5722/5725/5733 DynamicNotRun. M2tJGT233A, M2ag/M2af, strictM2i unchanged.
IRQNotInjected, TimerEvolutionNotModeled, EnclosingIRQFrame/RecoveredEcuScheduler
NotEstablished, ElapsedTimeNone, PcInspectionOnly/NotFlashReady;
physicalRpmAvailable=false; physical fuel/time/degrees unavailable.
GUIr3 paused/NotRun, D1/D2 interactive NotRun, hardware/fullboot NotRun,
FirmwareBIN=0; InquiryDraftReady/NotSent. Older reports are not rewritten.

One next evidence step, **not performed**: acquire the complete applicable
MSM66201/207 hardware user's Chapter4 Reset/WDT pages, including exact3C command,
reset-release/cause rules and verifiable edition/revision. This is not permission
for hardware/vendor/runtime work. STOP after delivery: no M2as, DEC fix, native
reset/CAL2689, full RAM loop, IRQ/timer/JGT/5722, GUI or hardware continuation.
