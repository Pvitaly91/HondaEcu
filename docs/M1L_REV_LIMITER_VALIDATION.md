# M1l — Scoped rev-limiter discovery and stateful validation

M1l establishes a second **research parameter**, the exact-bound candidate's
period-word overspeed cut/resume path, and its native software mask consumer.
It does not complete M1, authenticate a factory image, or enable limiter export.
M1k remains completed and unchanged in meaning.

Base: `62491535b33d7b0f48092101cf69adf758f21354`, branch
`codex/p28-integrated-vtec-chain-m1k`. Delivery branch:
`codex/p28-rev-limiter-validation-m1l`. No main/PR/merge workflow is involved.

## Discovery and evidence ledger

Addresses below refer only to the privately bound 32 KiB research image.
Public code/tests contain ISA forms and independently invented data/programs,
not an OEM function fixture. The private listing-byte audit verifies the actual
listing against the preserved baseline, not just disassembler labels.

| Claim | Code references | Established scope / remaining dependency |
| --- | --- | --- |
| Limiter input is unsigned 16-bit period, not compact VTEC Code | G stores `00C4/00C5` at `07A2`; `197D` compares direct `00C4` against A | Little-endian, smaller normal period means faster interval-derived speed. Existing G derivation remains separately conditional; isolated execution receives raw explicitly, no physical RPM. |
| Two active threshold sources | `1966/1969`, `196C/1971`, `1974/1977` | P4.0 or `011B.7` selects fixed immediates; otherwise RAM `01A4/01A6`. P4 is a frozen bit observation, not pin emulation. |
| Previous overspeed state selects cut versus resume | `1979/197C`; word compare `197D`, borrow branch `1980` | Previous `0124.5=0` selects cut, set selects resume. Request iff unsigned raw < threshold. Equality clears request. |
| Overspeed contributes to shared cut state | `19AC`, `1A1E`, `1A21..1A35` | `0124.2` and `.5` set on this route. `.5` is not globally exclusive to overspeed: earlier gates can also reach `19AC`. |
| Decision reaches an engine-control software consumer | `5585`, `5588`, `558B`, `558E`, `5592..5596` | `.5` skips `AND 018F,A`; independent `012A.7` also skips. Same CPU/RAM executes consumer, stopping **before** `5596` writes P2. |
| Adaptive thresholds are not just another fixed pair | `487B..48F5`, helpers `5AB8`, `5AC2` | Two program-table banks feed RAM words; timer, mode, prior-word and `00CE` dependencies. Statically traced, producer/counter servicing NotRun here. |
| Deceleration is a different contribution | `1985..1A1C`, `.4` consumer `05D9..05EB` | This route uses additional counters/gates and zeroes a pulse-width intermediate; not the isolated overspeed predicate. |
| Compact-Code flags alone do not identify this limiter | `2373/237F`, `0124.0/.1`, consumer `0725` | Throttle software calculation cadence, not the established overspeed mask branch. |

Other period comparisons (`10E5..10F1`, `06B2`, `3980/399A`, `4BF1`) were
distinguished by their consumers. They do not establish this limiter merely by
using a speed-related word. Vehicle-related `00CE` contributes to adaptive
threshold production, but is not substituted for the direct engine period input.
Startup/no-sync shared-bit writers such as `0516`, independent cut via `1937`
(`012D.4`), and sensor/gating routes before `1966` are outside this execution
contract. This avoids equating every shared fuel-cut indication with overspeed.

## Threshold structure and semantics

| Source | Cut while prior `.5=0` | Resume while prior `.5=1` |
| --- | --- | --- |
| Fixed context: P4.0 OR `011B.7` | Word immediate at `196A..196B`: raw 536 | Word immediate at `1967..1968`: raw 552 |
| Other context | Current RAM word `01A4` | Current RAM word `01A6` |
| Adaptive bank 0 base program data | Word `649B`: raw 253 | Word `6495`: raw 257 |
| Adaptive bank 1 base program data | Word `64A7`: raw 253 | Word `64A1`: raw 257 |

All fields above are little-endian unsigned words. Table bases are **not** always
the current RAM thresholds and are not exposed as mutation targets. `4882`
selects banks through `021F.1`; `4894/489D` select reset paths, `48A2` gates on a
timer, and `48E9/48EC` write the RAM words. `5AB8` decreases toward a floor;
`5AC2` uses `00CE`, table coefficients and a prior-word bound. Physical units and
all timed/context trajectories of this adaptive producer remain unestablished.

For the fixed pair, descending raw crosses into cut below 536. Once cut, values
536..551 retain it; ascending raw 552 restores this path's permission. No RPM
conversion is involved. Equal pairs eliminate that band; reversed synthetic
pairs may alternate state at constant raw. The implementation neither normalizes
nor claims safety for such pairs. Raw 0 and `FFFF` are separately labelled
sentinel/fallback observations, not physical operating points.

## Isolated execution contract

One `limiterSequence` task in the existing Rust runner v0.7.0 reuses the CPU,
decoder, Bus, exact-form admission, executor, trace and C# bounded process adapter.

- Decision entry `1966`, exit `1A38` before instruction. Allowed half-open ranges:
  `[1966,1985)`, `[19AC,19B0)`, `[19C2,19CB)`, `[1A1E,1A38)`.
- Consumer entry `5585`, exit `5596` before instruction; range `[5585,5596)`.
- Decision PSW `0101`, LRB `20`; consumer PSW `0102`, LRB `21`; SCB 1, USP `0280`.
  Both off-page bases resolve to `0100`; DP is the SCB-1 word at `008C`.
  Technical stack seed is unused on the established paths; no IRQ/time injection.
- Each stage has a 96-instruction budget. Unknown SFR access is an error. Only
  a frozen **byte read** of P4 bit0 is added; no P4 writes, word read or P2 access.
- Once-only seeds: `0124`, `012B`, `012A`, `018F`, `01D7`, RAM cut/resume words;
  `0121.7=1` routes the non-overspeed case through `19C2`. Earlier gates are
  assumed to have selected entry `1966`; PSWL.4/.5 are clear at each entry.
- Caller actions per call: reset entry PC/PSW/LRB/USP; supply raw `00C4` word,
  `011B.7` snapshot and frozen P4.0; supply the consumer's caller accumulator
  channel mask with high nibble F. The mask is an explicit upstream scheduler
  input, **not** a per-call store into persistent `018F`.
  High nibble F is a harness restriction, not a recovered assertion about every
  caller accumulator. Only the four low channel bits are interpreted; native
  `5594` forces the outgoing accumulator high nibble to F in either case.
- Internal bits, masks, counter `01D7` and thresholds are never reseeded per call.
  Non-overspeed native code writes `01D7=20`; no hidden host decrement exists.
  RAM threshold updates/timer servicing are not scheduled by this task.

The independent C# state machine owns its entire history. Each completed call
compares active context/prior selection, actual CMP operands and CF/ZF, old/new
state, counter, ordered architectural stores (including equal-value writes),
consumer branch/accumulator and exit PCs. Native immediate fetch extents and
loads establish operand use; these are not mislabelled program-data LC reads.
Decision failure makes request null and consumer NotEvaluated; terminal suffix
does not execute. Consumer failure retains any observed decision but leaves its
own inhibit output null. Unevaluated expected steps remain null.

### What is actually inhibited

`5588` prevents the new channel-mask AND at `558B`. `5585` provides an independent
inhibit that can remain active after overspeed clears. On the non-inhibited
route, native code updates `018F` and sets `012A.0`, then builds an accumulator
mask at `5592/5594`. It would next apply that mask to P2 at `5596`.
The static upstream link is `54FA/54FC` loading the `0196` width intermediate,
`5558/5561/5569` calling channel helper `5699`, `5575/5576` combining r0 and
rotating `018E`, and `5578/557D` selecting the short-width alternative. These
upstream scheduling operations are not silently simulated by the harness.

Independent `012A.7` set/clear writers (`05A3`, `5685`) are outside the slice;
the independent inhibit is seeded once, not toggled by a hidden per-call host action.
Skipping this update does **not** undo earlier enables already retained in
`018F`. Surrounding scheduler initialization/reset (`55BF..55C5`), timer/IRQ
events, P2 polarity and electrical pulses are not executed. Consequently this
is a proved software scheduling-mask boundary, not proof that every injector
is off, nor of actual fuel delivery or ignition pulses. No host
`injectorActive = !flag` substitute exists.

No independent limiter enable switch is established within the isolated slice.
Disabled/re-enabled main-loop behavior is NotEvaluated, not invented. Changing
P4/fault context selects thresholds; it is not labelled a bypass switch.

## Instruction audit

The whitelist matches mnemonic **and** exact decoder byte template and DD mode;
reviewed older forms are reused only when already `Allowed`. None of the three
older ADD/SUBB assumptions is permitted in this task, locally or cumulatively.

New forms include word immediate/load-DP, MOV DP/off-page, CMP direct-word/A,
P4/PSWL carry-bit moves, PSWL.5 set, off-page bit3/4/5 writes, bit7 reset,
bit7-set/bit5-clear branches, byte AND/OR and SC/RC. Manufacturer instruction
pages reviewed include printed 3-25, 3-36, 3-69/70, 3-77/78, 3-86, 3-114,
3-116 and 3-127 in the previously preserved instruction chapter. Generic
decoded probes cover width, endian, bit-neighbor preservation, CF/ZF and HC.
In particular **CMP preserves HC**, unlike SUB; an initially incorrect test
expectation was corrected against page 3-36. No CPU semantic fix or expanded
assumption was needed. Exact-field fixtures and the private execution corpus
are distinct evidence, not independent physical-CPU verification.

## Read-only CLI and scenario

```text
hondaecu research p28-limiter inspect <baseline.bin> --profile p28-304
  --confirm-profile --baseline-binding <private-binding.json>
  --output <new-private-inspection.json>

hondaecu research p28-limiter check <baseline.bin> --profile p28-304
  --confirm-profile --baseline-binding <private-binding.json>
  --runner <rust-runner> --scenario <private-scenario.json>
  --output <new-private-validation.json>
```

Without matching binding AND confirmation, inspect returns only general size /
hash information and no revision fields. Check requires exact-parent admission.
All inputs, including runner/profile, are snapshotted and rechecked; existing
output paths and input aliases are refused. The existing bounded, cancellable,
timeout-aware process adapter handles execution. `HasFailure` includes any
incomplete requested call, not excluded GUI/hardware dependencies.

Scenario v1 is a closed, <=1 MiB schema, depth <=8, 1..256 densely indexed calls:

```json
{
  "formatVersion": 1,
  "purpose": "isolated-period-limiter-software-test",
  "provenance": "Invented software example; not RPM or measured ECU state",
  "initialState": {
    "data0124": 0, "data012B": 0, "data012A": 0, "data018F": 255,
    "data01D7": 7, "ramCut": 100, "ramResume": 110
  },
  "calls": [
    { "index": 0, "rawPeriod": 99, "p4Bit0": false,
      "snapshot011bBit7": false, "channelMask": 254 }
  ],
  "mutation": null
}
```

Optional mutation is exactly `{ "field": "fixed-context-cut", "value": 540 }`
or a `fixed-context-resume` word. It constructs an immutable in-memory child,
checks the complete two-byte footprint and **every other byte**, rejects no-op,
opcode/branch/extra-field edits, and never creates a binding for the child.
This is not an arbitrary-offset API and not an extension of signed M1g export.

## Actual private results

Preserved evidence is under `private/reports/m1l/`; it is not published.

- Twelve persistent CLI experiments: 128 calls each; both initial `.5` states,
  independent inhibit clear/set, unchanged parent and separate cut/resume B
  experiments. Every sequence cycles fixed-P4, fixed-fault, RAM snapshot, fixed
  context, with descending/ascending boundaries, equality, repetition and
  alternation. Across image/scratch instances: **7,680 requested/completed strict
  matches**, zero conditional/unresolved/unsupported/NotRun/mismatch/error;
  downstream comparison available for all 7,680.
- Separate one-step domain: every raw `0000..FFFF`, fixed and RAM-snapshot
  context, both prior states, three scratch patterns. A fresh CPU/RAM and fresh
  C# model for **each independent case**: **786,432 strict matches**, zero
  mismatch/error. 786,408 normal-raw rows and 24 endpoint/fallback rows are
  separately counted. This is one field's domain, not all ECU states and not a
  stateful sweep disguised as independent one-step testing.
- In-memory cut 536→540 first changes request at call **6** (raw 539); resume
  552→556 first changes request at call **16** (raw 552). Actual and expected
  first divergence agree for every scratch/prior/independent-inhibit experiment;
  subsequent persistent states/writes also agree. Each experiment changes one
  established word field only. With independent inhibit set, request divergence
  does not imply downstream permission.
- Baseline checksum arithmetic residue 0; both +4 mutations residue 4 (Invalid
  under the established sum contract). No compensation or bypass was applied.
  No mutated BIN, compensation definition, key or receipt was created.

The exhaustive private driver links the same Rust task and streams measured
rows to a separate C# model auditor; row identity/order/cardinality and SHA-256
are recorded. Stateful proofs use the real CLI/subprocess with complete traces.
Public tests instead use invented programs/data and include successful native
consumer execution that is deliberately rejected as a limiter-model mismatch,
strict stops/null suffixes, malformed responses, mutation guards and immutability.

## Verification

Both explicit Release solutions build without warnings. Local regression totals:
513 Core, 152 CLI, 81 Desktop headless tests; pinned Rust 1.85.1 passes 113 tests.
These include affected M1d–M1k regressions. Full solution formatting, Rust formatting,
privacy guard, whitespace checks and preservation of 3,674 protected earlier
inputs/reports/portable files are required before commit. The unchanged standard
CI runs Linux/Windows synthetic tests and Windows no-window portable diagnostics;
its portable artifact is not GUI acceptance. CI status is reported against the
actual pushed commit, not assumed from local tests.

## Delivery boundaries and next prerequisites

`physicalRpmAvailable=false`; `PcInspectionOnly / NotFlashReady`.
GUI r3 remains paused/NotRun. Hardware, full boot and electrical behavior are
NotRun and excluded from M1l completion. Adaptive producer and earlier combined
cut gates are explicit dependencies, not claimed as executed.

Before controlled limiter saving can be added later, define a separate reviewed
operand-edit contract and lineage/report format, preserve all non-operand bytes,
validate checksum-preserving composition for that exact edit, specify supported
threshold contexts/ordering, and repeat native A/B validation. Existing M1g
authority must not be repurposed. Independent editor and hardware verification
remain separate gates; no such next stage starts automatically.
