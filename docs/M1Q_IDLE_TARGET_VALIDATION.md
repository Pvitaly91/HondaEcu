# M1q — Scoped idle-target inspection and byte-executed validation

M1q establishes one raw-context idle speed-control reference in the privately
bound P28-304 research image: ROM calibration → native target word → native
current-minus-target error/sign/clamp. It adds read-only `research p28-idle
inspect` and `target-check`, one narrow Rust task and an independent C# model.
It does not add an idle editor or export framework. M1p and earlier completed
stages keep their existing semantics.

The explicit base is `9d01653ef09fd9abe39bd6566a494e1e585badbc` on
`origin/codex/p28-combined-limiter-export-m1p`; the delivery branch is
`codex/p28-idle-target-validation-m1q`. No implicit main/origin-HEAD base is used.
The private binding is an exact research-parent identity, not factory ROM
authentication. No ROM, binding, identity, native routine fixture, trace or
private report is published with this document.

## Why this is a target, not a similarly named threshold

Discovery followed two directions in the matching private listing, with all
11,499 listed instruction rows byte-checked against the unchanged original:

- Current representation: G writes the period-like word at DATA00C4/00C5;
  compact F writes DATA0133 and exchanges a byte into DATA0238. Read-site
  tracing distinguishes the C4 comparison at 09DC from fixed hysteresis at
  10EE/4BF1, the multiply/lookup/classification path around 4796..47B4, and
  other proportional references around 3B3A/3BE5. Shared current-speed data
  does not establish those other parameters as an idle target.
- Regulation: DATA00CA is multiplied by ROM gains at 359F/35A4/35A6, its sign
  in DATA021A.4 controls the signed correction at 35A9, and 35B0..35E5 feeds
  accumulated controller state DATA0288/028C. Tracing CA backward reaches
  09DC..09F4: current C4 minus reference DATA025C. Tracing that reference
  backward reaches the packed lookup at 68CB and its producer at 2FD1.

DATA025C is therefore the desired **speed-period reference** in this software
regulator, not the current measurement, a Boolean mode-entry threshold, a
standalone anti-stall threshold or an actuator duty. Further software produces
a distinct command at DATA0260 (3770), then a lookup result at DATA025E (3778).
The gain-selection path at 34C7/34D7 also reads target 025C separately from
current error CA. This functional linkage supports the scoped idle-target
identification; it does not establish an electrical IACV/EACV pin or a plant.

Other warm-up/start, load correction, dashpot/deceleration, anti-stall and
ignition paths have **not** been assigned physical names from raw flag values.
In particular, DATA021A.2 is not labelled “closed throttle” merely from its
nearby speed/CC hysteresis writer. Alternate target paths are not promoted to
confirmed physical operating modes. No upstream emulator EngineState/IACV
telemetry or guessed 750/800/850 number is evidence here.

## Selected producer and exact calibration

The supported context is raw DATA00D9 in **52..255**, persistent DATA021A.0 set,
and fixed caller snapshot DATA0216.3 clear. No temperature, A/C or transmission
meaning is inferred for these inputs. DATA00D9 is an explicit unsigned byte
software input. DATA00C4 is an explicit unsigned 16-bit period-like snapshot,
not host-computed RPM and not a substituted G/F result in M1k.

Entry is 2FD1; success stops **before** 30AB. The selected path loads X1=68CB,
passes through 7D8A..7D98, bypasses low-domain immediate overrides, and calls
the interpolation helper through actual VCAL 0/vector 0028..0029 at 306F.
The helper is 5894..58D3. Its returned target is forwarded through DP. The
separate component DATA027A is explicitly written zero at 309A. DATA021A.0
selects the branch directly to 30A9, which stores the **final target word** at
025C/025D. DD is actually 1 here; the heuristic listing's byte-store label is
not authoritative. No filter, target timer, hold or accumulated target
correction participates in this selected path.

The table occupies 21 bytes from 68CB: seven packed records, each an unsigned
byte axis followed by an unsigned **little-endian 16-bit value**. These are raw
period words, not RPM, duty or VTEC compact codes.

| Cell | Raw axis | Value offset | Raw word | Selected execution |
| --- | ---: | --- | ---: | --- |
| 0 | 255 | 68CC | 1250 | Supported |
| 1 | 161 | 68CF | 1339 | Supported |
| 2 | 135 | 68D2 | 1442 | Supported |
| 3 | 110 | 68D5 | 1563 | Supported |
| 4 | 52 | 68D8 | 2315 | Supported lower endpoint |
| 5 | 40 | 68DB | 3024 | Static inspection; NotEvaluated |
| 6 | 0 | 68DE | 3024 | Static inspection; NotEvaluated |

Helper selection walks descending records until `x >= lowerAxis`. Overlapping
word reads at `record`, `record+4` and `record+2`, word SWAP and byte-register
exchanges construct the numerator, denominator and two values. Reads must not
be misinterpreted as aligned non-overlapping table words. The native MUL/DIV
sequence gives exactly:

```text
distance = x - lowerAxis
denominator = upperAxis - lowerAxis
delta = floor(abs(upperValue - lowerValue) * distance / denominator)
target = lowerValue + (upperValue < lowerValue ? -delta : delta)
```

This is directional integer truncation, not double arithmetic or nearest
rounding. Strictly descending axes ensure a nonzero denominator; the product
uses the native double-word result and bounded unsigned division. Exact nodes
return their numeric values. The code/model also test ascending and flat
invented values and full-word arithmetic extremes without publishing OEM code.

Although the table itself spans every byte value, **rawD9 < 52 is refused** by
this task: actual upstream branches select other overrides before this path.
It is not reported as a clamped lookup result. DATA021A.0 clear and table 68E0
are also NotEvaluated. No extrapolation beyond the supported context is claimed.

## Immediate native consumer

On the **same CPU/RAM**, stage 09DC stops before 09F4. At 09DE the ROM subtracts
the actual target 025C from actual current C4 as unsigned words. Borrow is
stored at DATA021A.4. For borrow, actual VCAL 7/vector 0036..0037 reaches the
word-negation helper at 59A6; otherwise the difference is already positive.
Native compare/branch/store computes:

```text
borrow = currentPeriod < targetPeriod
differenceWord = (currentPeriod - targetPeriod) modulo 65536
errorMagnitude = min(abs(currentPeriod - targetPeriod), 768)
DATA021A.4 = borrow
DATA00CA/00CB = errorMagnitude
```

Equality gives borrow=false and zero error. There is **no deadband at this
boundary**; clamping starts at magnitude 768. This is not the conventional
host expression `targetRpm-currentRpm`. Raw zero and FFFF are separately tested
software sentinel/fallback inputs, not measured engine speeds. The downstream
regulator consumes magnitude/sign, but its accumulation, command, electrical
output and actual engine stabilization are not byte-executed in M1q.

## State ownership and runner contract

| Field | Writer → reader | Initialization and per-call ownership |
| --- | --- | --- |
| D9 byte | harness → producer | Explicit per-call external raw snapshot |
| C4/C5 word | harness → consumer | Explicit per-call external period snapshot |
| 0216 byte | harness → producer selector | Fixed zero caller snapshot each live call; no user override |
| 025C/025D target | producer 30A9 → consumer 09DE | Seed once; only native writes thereafter |
| 027A/027B component | producer 309A → subsequent software | Seed once; native zero on each selected call |
| 00CA/00CB error | consumer 09F2 → regulator | Seed once; native overwrite thereafter |
| 021A byte | consumer 09E0 writes bit 4; producer reads bit 0 | Seed once with bit 0 set; other bits preserved |
| Registers/stack | native instructions/helpers | Per-stage ABI entry context; scratch persists, stack balances |

One CPU/RAM is created for each sequence/image/scratch pattern. Initial internal
state is installed only once. Repeating a call does not reseed target, error or
021A. No counter service or hidden host decrement exists in this scope. The
harness explicitly stages producer then consumer; it does not emulate the
intervening scheduler, IRQs or a measured elapsed period.

PSW write=1101 (readback=1DC9 because unimplemented bits read as one;
DD=1, SCB=1), USP=0180, initial SSP=07FE; producer LRB=0041 (local
0208), consumer LRB=0040 (local 0200). Native VCAL stores its return at SSP then
decrements SSP by two; RT restores it. Each stage must finish with SSP=07FE.
Success is checked before the exit instruction, without ROM instrumentation.

Half-open executable ranges are:

```text
producer: [2FD1,2FE0) [2FEC,2FEF) [306E,3076) [309A,30A0)
          [30A9,30AB) [7D8A,7D98) [5894,58D3)
consumer: [09DC,09F4) [59A6,59AD)
program data: producer [0028,002A) [68CB,68E0); consumer [0036,0038)
DATA: [0000,0008) [0088,0090) [00C4,00C6) [00CA,00CC) [00D9,00DA)
      [0200,0210) [0216,0217) [021A,021B) [025C,025E) [027A,027C) [07FE,0800)
```

Budgets are 128 instructions per stage, bounded journals and 1..64 calls per
request. Scratch patterns are 00/55/AA. Existing Bus access controls apply; no
new SFR is treated as RAM. Exact DD/opcode-form admission remains strict. Old
conditional ADD/SUBB permissions are neither expanded nor accepted by idleTarget.
An unresolved/error/budget stop is terminal: unavailable target/error is null,
remaining calls NotRun, not fabricated zeroes. Other contexts are NotEvaluated.

Rust 0.9.0 reuses the existing CPU/decoder/executor/Bus and process protocol.
The narrow fix `idle-exact-arithmetic-half-carry` corrects HC updates for seven
exact ADD/SUB forms, after a decoded regression first failed on ADD A,er3 with
0+0 and an initially set HC. Previously retained HC contradicted the primary
OKI Chapter 3 ADD/SUB flag tables. Generic ISA probes exercise both prior HC
states and carry/borrow boundaries; DD/store/SWAP/register aliases/vector stack
are independently tested. No opcode table or old assumption policy was changed.
Existing 0.8.0 evidence remains accepted for its old operations, not idleTarget.

The C# model has its **own image and history**. Actual Rust state is never used
as the model's next expected state. Every successful call compares selection,
ordered program reads, integer target components, all owned states, ordered
stores including same-value/register/stack stores, branches, operand/result
flags, exits and stack balance. Invented subprocess programs demonstrate native
producer-to-consumer handoff and persistent state, but deliberately do not
masquerade as the recovered OEM model.

## Actual private validation and one in-memory mutation

The final 0.9.0 private series contains **858 StrictMatch checkpoints**, zero
mismatches/unresolved/conditional checkpoints: all 204 supported raw-axis values
in four bounded schedules, 21 current-boundary calls, 27 repeat/reverse-history
calls, six separate sentinel calls, and 14 A/B calls. Each image runs three
independent scratch sequences. This is enumeration of one byte field in one
context, not all ECU states. Both confirmed and unconfirmed inspections were
also exercised; the latter contains only general image data.

The sole mutation is code-owned `context-21a0-table-cell-2`, word at 68D2..68D3,
**1442 → 1458**. Only 68D2 actually changes; its high byte stays unchanged.
Every other byte, including axes, selectors, pointers and opcodes, is checked
identical. B receives no child binding and exists only in memory. Each model
reads its own image and A/B have separate CPU/RAM histories with equal inputs.

| rawD9 / current | A target / error / borrow | B target / error / borrow | Observation |
| --- | --- | --- | --- |
| 135 / 1450 | 1442 / 8 / false | 1458 / 8 / true | Actual mutated-cell read changes native sign |
| 120 / 1450 | 1515 / 65 / true | 1521 / 71 / true | Interpolated target and magnitude change |
| 145 / 1450 | 1403 / 47 / false | 1413 / 37 / false | Other adjacent interval changes |
| 111 / 1450 | 1559 / 109 / true | 1559 / 109 / true | Cell read, but truncation hides the small effect |
| 110 / 1450 | 1563 / 113 / true | 1563 / 113 / true | Lower endpoint control, despite cell read |
| 161 / 1450 | 1339 / 111 / false | 1339 / 111 / false | Upper endpoint control |
| 255 / 1450 | 1250 / 200 / false | 1250 / 200 / false | Outside-interval control |

There are 21 actual read → changed-target → changed-error/sign witnesses across
the three scratch histories. Potential influence is local to the adjacent
intervals 110 < rawD9 < 161; integer truncation may leave some interior outputs
unchanged. This is not a global idle adjustment or a valve-opening prediction.

The established full-image modulo-256 byte-sum arithmetic is reported separately:
A residue=0, B residue=16. B is not checksum-valid. No checksum repair, bypass,
native-checksum acceptance claim, firmware BIN, plan, receipt, compensation
definition, signing key or export capability was created. A and the 4,262
inventoried prior private inputs/reports/portable files are checked unchanged.

## Read-only CLI and delivery checks

```text
hondaecu research p28-idle inspect <baseline.bin> --profile p28-304
  --confirm-profile --baseline-binding <binding.json> --output <new-private.json>
hondaecu research p28-idle target-check <baseline.bin> --profile p28-304
  --confirm-profile --baseline-binding <binding.json> --runner <rust-runner>
  --scenario <private-scenario.json> --output <new-private-validation.json>
```

Scenario v1 requires `purpose: idle-target-raw-context-test`, bounded provenance,
once-only `initialState` (`target`, `raw027a`, `errorMagnitude`, `data021a`),
`calls` with dense `index`, `rawD9`, `rawPeriod`, and a required nullable
`mutation` (`field`, `value`). Maximum size is 1 MiB and depth 8. Missing,
duplicate, unknown or per-call produced-target/expected-output fields are
rejected. JSON cannot supply an arbitrary mutation offset or caller flag.

The CLI reuses exact admission, timeout/cancellation and protected new-report
publication, with baseline/profile/binding/runner/scenario snapshot rechecks.
An unknown BIN receives general information only; confirmation alone grants
no revision-specific interpretation. No `--set-idle-rpm`, export or live write
exists. Public tests contain invented data/instructions only. Pre-commit checks
cover both explicit .NET solutions, pinned Rust 1.85.1 build/test, affected ISA
and old export regressions, formatting, privacy, diff whitespace and prior-file
preservation. Public clean CI artifacts are not GUI acceptance.

## Boundaries and future work

This completes the selected **software target/error boundary**, not full ECU
behavior or milestone M1 cross-editor/hardware acceptance. To support future
idle editing, establish the remaining context selectors and correction paths,
physical input/period scaling, scheduling and operating validity; then define
separate reviewed field policy and suitable checksum/export authority. No such
authority or future stage is started here.

Always: `physicalRpmAvailable=false`, `PcInspectionOnly / NotFlashReady`.
GUI r3 is **paused/NotRun**; hardware, full boot, downstream native regulator
and electrical/PWM output are **NotRun**, intentionally outside M1q. No GUI
code, interactive WPF window or Computer Use is involved.
