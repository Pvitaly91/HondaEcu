# M2r post-selection synchronous software state and original-configuration chain

Read-only research, runner0.26.0, operation `fuelPostSelectionCriticalChain`.
PcInspectionOnly / NotFlashReady; physical RPM/fuel/time/degrees unavailable.
Strict M2i remains Blocked on47 81. GUI r3 paused/NotRun; D1/D2 interactive
acceptance, hardware and full boot NotRun. No firmware BIN, exporter, writable
calibration, compensation, binding, receipt or token is created.

## Separate operation and continuous entry

Historical M2o, M2p and M2q retain stop-before2204,223B and2259 respectively.
M2r reuses their execute-in-state components, then continues the successful M2q
machine from2259 to stop-before22B1. It does not change their old operation,
schema or stop. Runner0.25.0 cannot execute the new operation.

One CPU/RAM is initialized once per image/scratch sequence. The entire M2q exit
boundary is the M2r entry boundary, including A, X1/X2, er0..er3, DP, LRB, USP,
SSP, PSW/DD and the shared RAM/IE histories. There is no enter/reset, register
restore, new machine, repeated consumer suffix or JSON-to-RAM transfer at2259.
Access/observation range changes grant no machine-state writes. Earlier ABI
entries remain explicitly scripted software tests, not a recovered scheduler.

## IE/PSWH sequence and exact neutral interpretation

2259 applies word AND to the existing shared software IE storage at001A with
immediate mask02A0. This is the same Bus storage used by native ticks/adaptive
production, not a second fuel IE. Old/new values and word access width are
mandatory proof. Its synchronous storage transition is `IE & 02A0`; it does
not itself rewrite the separate CPU MIE field. ZF is updated from the word
result; DD and the other flags are retained.

225E applies ANDB to PSWH withFE: PSWH bit0, whole PSW bit8/MIE, is cleared.
2268 applies ORB to PSWH with01 and sets that bit. Other PSWH bits, the separate
low PSW byte and DD are retained by these exact edits. Their names do not imply
priority arbitration, physically disabled IRQs or absence of pending requests.

226B loads the existing word restore-source00F8 into A.226D natively stores A
back into software IE. This is a paired local mask/restore sequence, but the
restored value is the declared/persistent00F8 word, not necessarily the value
that2259 read. When initial IE differs from00F8, equality is not fabricated.
No host IE/MIE setter or caller restoration runs between events; the next
event observes the actual native final storage and CPU state before its
disclosed scripted ABI.

IRQ delivery: NotInjected. Pending interrupt: NoneInjected / NotModeled.
Elapsed time: None. No synthetic IRQ, preemption, peripheral event, wall-clock
cadence or priority acknowledge is inserted into this synchronous fragment.
The bounded model does not prove real ECU interrupt behavior or engine safety.

## X1/A lifetime and ordered019x generations

The audited directions are transfers, not loads or min/max operations:

| Native PC | Source | Native destination | Width / order |
| --- | --- | --- | --- |
|2261 | M2q X1 |0194 | word, first019x store |
|2264 | M2q retained-or-zero A |0190 | word, second019x store |
|2266 | same A |0192 | word, third019x store |

All words are little-endian. These instructions preserve the numeric carriers
until their consumers. The entire2259..22B1 suffix has no019x reader, so no
new user-supplied019x history is required. Once-only scratch canaries are
diagnostic InitialHistory, not software source parameters. Same-value stores
are still Written generations with their exact PC/order; unchanged numbers
never imply Held. Partial execution retains any already-written generation,
while unexecuted stores are NotRun. No partial write is rolled back.

A is subsequently clobbered by00F8 restoration, then by the program byte60F8
and the229F read through DP. At22A3 native CLR X1 clobbers X1 tozero without
changing flags/DD. The M2q numeric result therefore influences019x, but cannot
be attributed to the later common quartet after these clobbers.0190/0192/0194
are neutral software words, not established injector channels, pulse widths,
fuel quantities, AFR or dead time.

## Original configuration and nearest coherent result

226F reads the actual ROM byte60F8 with LCB. The low byte of A is replaced;
the high byte and DD are retained, and ZF reflects the loaded byte.2273 takes
the zero branch to229F. The validator requires the actual program-data address,
value0, exact flag transition/branch target, instruction-byte extent and absence
of227A execution. A matching final number cannot replace that provenance.
The original60E5/60F8 bytes remain unchanged. Actual-ROM dynamic witness counts
and raw evidence are delivered separately under `private/reports/m2r/`.

For this unchanged original configuration and admitted caller state, the
optional2275..229F per-channel path is NotReachableInOriginalScope. This does
not mean globally dead code, unused functionality or a factory-disabled feature.
No PC227A entry, alternate ROM60F8, configuration A/B or editable configuration
field is admitted. Public invented alternate-direction branch tests are
synthetic coverage, never actual-ROM proof. The integrated invented process
probe uses ordinary RAM00F0 as a diagnostic software-mask word, unrelated
program byte0050 and low instruction addresses for both branch directions;
00F0 is not the shared IE001A storage or an interrupt controller. Its tiny
synthetic-only admission permits only the audited word-mask02A0 and PSWH
FE/01 exact forms, not generic logical mnemonics or new hardware capabilities.

229F loads current native03B4 through retained DP.22A0 performs an actual
CAL5991 and balanced RT return22A3, computing
`min(floor(current03B4 * 5 / 4), 65535)` with the established integer helper.
22A3 clears X1.22A5/22A8/22AB/22AE then store the same result to words
03B6/03B8/03BA/03BC through indexed X1. This ordered quartet is the nearest
completed common-path software result; its physical role remains unknown.

The selected exit is stop-before22B1, after that quartet and the local IE/MIE
sequence. Later control work beginning22B1 and downstream hardware/IRQ consumers
are not evaluated. The exit is not229F merely because that address was an old
static lead. No elapsed execution-time or electrical output is inferred.

## Unified ownership and independent validation

| Storage/carrier | Single owner / M2r interaction |
| --- | --- |
|IE001A | shared word-only Bus software storage; native2259 mask,226D restore |
|PSWH/MIE | CPU architectural state; native225E clear,2268 set; no IRQ delivery |
|0190..0195 | native stores2261/2264/2266; persistent generation history |
|X1/A | actual M2q carriers, native transfers then declared clobbers |
|012C | one shared byte; factor reads bit4, native223F owns bit5; M2r no setter |
|0150 | native2239 generation; M2q readers; M2r does not overwrite it |
|0144/014C | same established per-event software source snapshot, no duplicate owner |
|03B4 | native2203 current generation, read229F; no host downstream replacement |
|03B6..03BD | native ordered common-path stores; no produced-value inputs |
|60F8 | unchanged program byte, independently read by Rust and C# ROM owners |
|adaptive RAM/counters | existing native Written/Held/InitialHistory contracts |

C# independently owns original/B ROM, adaptive/limiter/fuel histories,
previous03B4,0150,012C, M2q projections, IE/PSWH and the new word histories.
Rust IE/X1/A/019x/config results are observations only, never model inputs.
Per-PC evidence proves the complete entry boundary, exact IE width/mask,
PSWH bit changes, transfers, restore source/order, configuration read/branch,
helper stack/register effects, indexed stores and final boundary. Forged
same-result traces, wrong bit/width/branch, missing restore/read or injected227A
execution are refused.47 81,45 81 and disputed SUBB remain unpromoted.

If M2q completes but the new suffix fails, its prefix observations remain
completed. M2r reports Partial/Unresolved/Error with null new completed outputs,
preserving actual IE/PSWH and earlier native word writes. Later events are
terminal NotRun and apply no snapshots or ticks. A retained old number is not
a new successful result. Only a completed mandatory suffix is StrictMatch.

## Closed CLI, scenario and causal controls

```text
hondaecu research p28-fuel post-selection-critical-check <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --runner <runner-0.26.0> --scenario <m2r-scenario.json>
  --output <new-private-report.json>
```

Version1 purpose `post-selection-critical-native-software-test` reuses one
authoritative M2q initialState,1..64 dense existing calls, at most32 combined
native ticks/event and8 trace indexes. No new input is needed. IE per-stage
override, PSWH outcome, X1/A,019x produced values,0150, bit5,60F8 override,
branch choice, arbitrary RAM/PC and formulas are refused. Exact binding,
immutable snapshots/rechecks, fresh-output alias guards and bounded process
cancellation/timeout are retained.

One-field B remains one primary raw-u8 fuel cell with nonzero delta at most8,
or one existing adaptive bank cut/resume word within the historical narrow
guard. B starts independently from original; no combined mutation, code,
config/60F8, IE ROM configuration or019x-history edit exists. Checksum is
diagnostic arithmetic only and firmware publication is0.

Fuel-cell A/B follows0140→03B4→0150→M2q X1/A→019x and independently follows
03B4→common quartet. Adaptive-base A/B may alter thresholds/request/03A2;
the new suffix does not read gated03A2, so no effect without a data dependency
is required. Masks, clamps, integer truncation and unread controls are reported
as such, not normalized away. Native scenarios, software-source/model-only
sweeps, synthetic tests and old compatibility counts remain separate.

Compatibility proves old M2q2259, M2p223B and M2o2204 scopes independently.
Historical IE/numeric/export publication contracts remain unchanged. QA uses
Rust1.85.1 and the repository .NET8 SDK; Desktop tests are headless, not GUI
acceptance. Privacy, preservation and exact-final-SHA CI are separate evidence.
No next stage, GUI or hardware is started automatically.
