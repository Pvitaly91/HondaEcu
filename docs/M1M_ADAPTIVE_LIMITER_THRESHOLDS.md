# M1m — Adaptive limiter threshold production and validation

M1m closes the missing software producer before the completed M1l limiter.
Actual bound-image instructions produce RAM words, and the same CPU/RAM then
executes the existing limiter decision and mask consumer. This is not a new
emulator, a firmware export feature, physical RPM evidence or full M1 completion.

Base: `a2172fee2f30a07c38dd843e03a9ab492ad75727`, explicitly fetched from
`origin/codex/p28-rev-limiter-validation-m1l`. Delivery branch:
`codex/p28-adaptive-limiter-thresholds-m1m`. M1l remains closed and its reports
and large domain corpus are preserved, not rerun as new discovery.

## Recovered producer

The private listing audit verifies 81 instruction boundaries against the
unchanged bound baseline: producer, both helpers, selected counter body and two
counter caller fragments. Twelve actual table words are checked separately.
These addresses describe this candidate only, not all P28 revisions.

| Bank selected by `021F.1` | Resume triple (origin, base, coefficient) | Cut triple (origin, base, coefficient) |
| --- | --- | --- |
| Clear | `6493/6495/6497`: 11038, 257, 334 | `6499/649B/649D`: 11038, 253, 258 |
| Set | `649F/64A1/64A3`: 11038, 257, 334 | `64A5/64A7/64A9`: 11038, 253, 258 |

All are little-endian program words. The last coefficient crosses a listing
table label: `64A9` is genuinely read as the third word of the cut triple.
The two banks have different addresses but identical data in this image.
Program reads are not rounded to even addresses; data-word accesses retain the
CPU's established alignment rule. None of these raw values has established
physical units. A base table word is **not** necessarily the current RAM threshold.

The decision order is:

1. `487B..4890` selects pointers and loads base resume into DP and base cut into A.
2. `0217.5` set resets counter `01CE` to 12 and writes both base words, even if
   `0214.0` is also set or the timer is nonzero.
3. Otherwise `0214.0` set writes both base words, leaving counter/timer unchanged.
4. Otherwise nonzero byte `01D5` exits at `48F5` without threshold stores.
   This hold still performs the initial pointer stores and base table reads.
5. With timer zero, native code sets `01D5=20`. If `0212.5` is clear and raw
   byte `00D9 >= 68`, or the subsequent `0223.2` gate is clear, it sets
   `01CE=12` and takes the decreasing helper. Otherwise nonzero `01CE` takes
   that same helper without resetting the counter. `0212.5` bypasses only
   the `00D9` comparison; it does not bypass the `0223.2` gate.
6. Counter zero takes the adaptive bound helper. Resume is computed first,
   cut second; both are committed by native stores at `48E9/48EC`.

For previous word `p`, base `b`, coefficient `k`, origin `o`, raw `x=DATA00CE`:

- `5AB8`: return `b` on borrow from `p-37`; otherwise return `max(p-37,b)`.
  The subtraction is **37**, not the increment constant 24.
- `5AC2`: bound = `min(p+24,65535)`. If `x<o`, high product is zero; otherwise
  high = `floor((x-o)*k/65536)`, obtained by native unsigned MUL into `(er1,A)`.
  Target = `(b+high) mod 65536`. Return `min(target,bound)`.
  Native ADD before CMP is not a saturating target addition. There is no DIV
  instruction on this path; the relevant quotient boundaries are MUL high-word
  transitions. Public invented tables test wrap; this image's coefficients
  cannot overflow `b+high` over the full unsigned raw domain.

The second helper can move a previous word downward immediately when its raw
target decreases. It is not an unconditional monotonic increase or guaranteed
hysteresis constructor. Equal/reversed initial pairs are neither normalized
nor rejected. RAM words retain exactly the observed ROM behavior.

## State ownership and execution contract

| Field | Producer / consumer | Harness ownership |
| --- | --- | --- |
| `01A4/01A6` | Adaptive producer writes; limiter reads current cut/resume | Seed once only; no per-call override |
| `01D5` | Producer sets 20; native counter body decrements nonzero byte | Initial byte and explicit service-call count only |
| `01CE` | Producer sets 12; native counter body decrements nonzero byte | Initial byte and explicit service-call count only |
| `0124/012B/01D7` | Existing limiter state and stores | Once-only initial state; `01D7` service remains outside this schedule |
| `012A/018F` | Independent inhibit and persistent mask consumer | Seed once; no per-call reset/enable injection |
| `00CE`, `00D9`, bits `021F.1/0217.5/0214.0/0212.5/0223.2` | Producer snapshots | Explicit raw call inputs, not acquired sensor values |
| `00C4`, P4.0, `011B.7`, channel accumulator | Existing isolated limiter/consumer inputs | Explicit raw/software snapshots; high-nibble-F channel mask |
| IE, saved word `00F8` | Native IE mask then restore; hold preserves IE | Initial software IE storage and once-only restore word |
| PC/PSW/LRB/USP, X1 tick argument | Scoped caller context | Entry resets only; no hidden persistent-state writes |

Rust runner 0.8.0 adds one `adaptiveLimiter` task. It reuses CPU, Bus, decoder,
executor, journals and the extracted M1l `execute_call`, rather than reseeding a
limiter instance. One machine per scratch pattern (0, 85, 170) lives for the
entire sequence. Order: timer ticks, counter ticks, producer, limiter, consumer.

- Producer entry `487B`, exit `48F5` before instruction; code half-open
  `[487B,48F5)`, `[5AB8,5AE6)`. Program data only `[6493,64AB)`.
- PSW `1101`, SCB 1, LRB `41` (local register base `0208`, off-page `0200`),
  USP `0180`; X1/X2/DP/USP live at `0088/008A/008C/008E`.
  PSWH.0 is MIE, not SCB or USP selection. Clearing it does not change USP.
- SSP is seeded once to `07FE`; CAL stores its return word at `07FE..07FF`,
  then decrements SSP to `07FC`. RT restores it to `07FE`. Only one nested
  return slot `[07FE,0800)` is permitted; no sentinel return address or ROM
  instrumentation is inserted. Producer exits are not synthetic RT patches.
- Producer budget 160 instructions. Data ranges are closed explicitly in the
  task/report: CPU aliases `[0000,0008)`, IE `[001A,001C)`, PR `[0088,0090)`,
  raw `[00CE,00D0)`, `[00D9,00DA)`, saved IE `[00F8,00FA)`, persistent limiter
  bytes/words above, local registers `[0208,0210)`, the five snapshot bytes,
  and the one return slot. No generic SFR fallback is available.
- Native critical section ANDs IE, clears MIE, stores cut then resume, sets
  MIE and restores IE from `00F8`. IE is an explicit **word-only software
  storage capability**. This does not model hardware IE reserved-bit behavior,
  interrupts, preemption or elapsed time. CPU MIE transitions are observed.
  Arithmetic flags after logical operations on PSWH are not claimed as
  hardware-defined; no scoped predicate consumes them before caller reset.
- Each selected tick executes `[5BD0,5BD9)` with a three-instruction budget,
  PSW `0001`, LRB `41`, USP `0180`, X1 exactly `01D5` or `01CE`. It reads the
  byte and skips DECB at zero. Only that target and caller PR/CPU aliases are
  accessible. No host decrement/reset occurs.
- Actual callers `2A02..2A0B` service the `01D3` eight-byte group (including
  `01D5`); `3DFA..3E03` service `01CD` and `01CE` via `5BC9`.
  The harness schedules a selected inner iteration only. It does not execute
  surrounding group loops, IE wrappers or the scheduler that determines cadence.
  A count of 20 calls is not claimed to mean 20 milliseconds.
- Limiter/consumer contracts stay M1l: decision `1966` → `1A38`, consumer
  `5585` → `5596` **before P2**; budgets 96 each. RAM context reads actual
  produced words. P4.0 or `011B.7` selects fixed immediates instead. Prior
  `0124.5` selects cut/resume; unsigned raw < selected word requests overspeed.

Independent `012A.7` can keep the mask update inhibited after overspeed clears.
Skipping `AND 018F,A` does not undo previously retained mask bits and does not
prove physical shutdown of all injectors. Electrical polarity/pulses are NotRun.

## Instruction evidence and independent checks

Exact admission compares mnemonic, decoder template, DD and width. Existing
forms are inherited only as `Allowed`; the old er1/er3 ADD and byte SUBB
permissions are neither accepted nor expanded. No conditional permission is
needed by this producer; unknown forms stop strictly, with a terminal suffix.

New reviewed forms cover X2 immediate and pointer moves, LC indexed by X2,
signed-USP byte/word loads/stores, register-word stores/clear, accumulator word
ADD/SUB/CMP, MUL, direct-word AND and PSWH byte AND/OR. The previously preserved
manufacturer chapter identifies MSM66201; its archive filename is not proof of
a different 66207 edition. Relevant printed pages: 3-13, 3-23, 3-29, 3-32,
3-69/70, 3-72/73, 3-85/86, 3-96, 3-100 and 3-156; established M1l bit/mask
forms and M1j native DECB/CAL/RT regressions are retained. Register context is
cross-checked against the MSM66201/207 user-manual register definitions.

A decoded regression first failed because word `ADD A,#imm16` retained stale
HC. The same audit identified the other needed exact accumulator forms.
Manual word ADD/SUB flag tables require HC updates. The minimal correction
covers DD=1 opcodes `86 imm16`, `09`, `A6 imm16`, `28` only. It does not promote
the unrelated `45 81` / `47 81` object-destination hypotheses. Version 0.8.0 adds
one semantic-fix identity and preserves historical runner-version inventories.
CAL itself was correct; a private probe caught and corrected an initially
too-narrow **harness stack range**, not an ISA bug.

The C# producer state machine owns its history and hands only its own modeled
words to the independent existing limiter model. Rust intermediate state is
never an expected input. Every completed call compares old/new state, table
bank, actual ordered LC addresses and loaded words, all producer conditional
branches, tick zero gates, ordered stores (including equal-value stores), IE,
MIE critical-section order, balanced stack, limiter CMP operands/CF/ZF,
threshold context/prior state, request, consumer accumulator/masks and exits.

## CLI and scenario

```text
hondaecu research p28-limiter adaptive-check <baseline.bin>
  --profile p28-304 --confirm-profile --baseline-binding <private-binding.json>
  --runner <rust-runner> --scenario <private-adaptive-scenario.json>
  --output <new-private-report.json>
```

The same exact-parent admission, bounded JSON parsing, immutable input snapshots,
timeout/cancellation process adapter and new-path report writer are reused.
Scenario v1 is closed, depth <=8, <=1 MiB, 1..64 densely indexed calls, and at
most 32 combined native ticks per call. It has no permissions, mutation,
derived image, produced-word input or per-call internal state fields.

```json
{
  "formatVersion": 1,
  "purpose": "adaptive-limiter-software-test",
  "provenance": "Invented raw software scenario; not measured ECU state",
  "initialState": {
    "limiter": { "data0124": 0, "data012B": 0, "data012A": 0,
      "data018F": 255, "data01D7": 7, "ramCut": 100, "ramResume": 110 },
    "timer": 0, "counter": 0, "ie": 0, "restoreIe": 0
  },
  "calls": [{
    "limiter": { "index": 0, "rawPeriod": 300, "p4Bit0": false,
      "snapshot011bBit7": false, "channelMask": 254 },
    "raw00ce": 50000, "bank1": false, "reset217": false,
    "reset214": false, "mode212": false, "enable223": true,
    "rawD9": 0, "timerTicks": 0, "counterTicks": 0
  }]
}
```

Reports include bound image/profile identity, scenario digest, raw inputs,
observed bank/table reads/path, partial native states and traces, selected
threshold source/value, overspeed, independent inhibit and mask-update skip.
Unexecuted interpretations are null, not false. Terminal failure prevents later
inputs, ticks and stages from running; expected rows are null when incomplete.
Partial writes remain observations, not completed threshold-production claims.

## Actual private evidence

48 targeted experiments, 510 logical calls across three independent scratch
instances: **1,530 requested/completed strict matches**, zero conditional,
unresolved, unsupported, NotRun, mismatch or execution error. All have actual
producer → RAM → limiter → consumer evidence. This is targeted validation,
not an exhaustive raw/state cross-product. The initial successful 24-call probe
and failed harness-range probe are preserved separately and excluded from that
total. All reports, actual traces, listing bytes and source scans remain private.

- Four 60-call histories cover both initial overspeed states and independent
  inhibit clear/set; native service, repeated holds/updates, bank changes,
  every recovered path, raw changes and fixed → RAM → fixed selection.
- Both banks separately exercise reset priority despite a nonzero timer,
  counter retention, native expiry and mode bypass. Both banks separately test
  subtraction borrow, floor/equality/neighbors, previous-word saturation
  boundary 65511/65512, multiplication high-word transitions and raw endpoints.
- Equal/reversed initial pairs retain their actual behavior through timer holds.
  The reversed pair alternates requests at constant raw; no normalization hides it.
- In history with initial inhibit clear, zero-based call 13 has cut 292 and no
  request at raw 300. Call 15 produces cut 316 and requests overspeed at the
  same raw. Call 24 resets to 253/257 and clears request. With independent
  inhibit set, that release still skips the downstream mask update.
- At raw `00CE=50000`, the native trajectory reaches cut 406/resume 455 rather
  than base 253/257. A later raw reduction can return directly to base words.

Public tests contain only invented data/programs. They include independent
model histories, native RAM handoff without reseeding, exact-form refusal,
null suffixes, malformed/tampered responses, raw integer boundaries, fixed
selection, actual Rust subprocess/CLI E2E and input immutability. Successful
invented execution deliberately mismatches the recovered model; it cannot be
mislabelled actual-ROM proof.

## Delivery boundaries

Verification uses both explicit Release .NET solutions, pinned Rust 1.85.1
build/test, solution/Rust formatting, privacy guard, whitespace checks and
preservation of 3,933 earlier private materials. Local/CI results are reported
against the delivered commit. No large M1l corpus rerun inflates M1m totals.
Local regression totals: 541 Core, 164 CLI, 81 Desktop headless and 121 Rust
tests. Both explicit solutions build without warnings; Desktop tests are
non-interactive and do not resume GUI r3.

`physicalRpmAvailable=false`; `PcInspectionOnly / NotFlashReady`.
GUI r3 remains paused/NotRun; Computer Use is not used. Hardware/full boot are
NotRun and excluded from software-stage completion. Acquisition/G integration,
physical timing, other scheduler paths, earlier combined limiter gates and
electrical outputs remain unexecuted dependencies. No firmware BIN, checksum
repair, limiter export, writable RPM definition, M1g authority/receipt change,
editor installation or signing framework is introduced. No next stage starts
automatically.
