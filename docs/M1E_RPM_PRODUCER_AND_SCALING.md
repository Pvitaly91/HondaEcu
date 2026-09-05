# M1e - RPM producer execution and explicit physical scaling

Date: 2026-09-05. Base: `origin/codex/p28-bytecode-slice-validation-m1d`,
`7752addb98db9aa1ad749e013b374eb9a161d8df`. Work branch:
`codex/p28-rpm-producer-scaling-m1e`.

`producer-check` executes the existing candidate's RAM-only producer, then its
compact-code computation and a separately seeded threshold fragment. Rust runs
unchanged bytes; an independent C# integer model supplies comparisons. This is
not full ECU execution, a measured RPM conversion, or M1 completion. Oracle v2,
production PatchEngine, public profile identities/writability and M1c one-step
lineage remain unchanged. Everything remains PcInspectionOnly / NotFlashReady.

## Reused evidence and limits

The original candidate, working copy, M1b listing/binding, M1a dossiers, M1c
child/plan/report and M1d execution reports were reused. No new BIN was obtained.
All eight preserved inputs match the pre-M1d hashes. A fresh private check
matched every one of 32768 listing bytes to the unchanged baseline, with no
overlap or gap, including 11499 instruction lines. This verifies byte
correspondence, not every decode or whole-program reachability. Existing
evidence was not overwritten; all populated reports, hashes, listings, traces
and manuals remain ignored/private. Public tests use invented instructions and
integer vectors, not an OEM-derived fixture corpus.

The writer census below includes banked, indexed, bulk and restoration writes.
It is a bounded static analysis, **not a proof of all arbitrary indirect targets
or corrupt-state execution**. In particular, one recovery bitmap helper's input
domain remains unresolved. That uncertainty does not enter the explicitly seeded
RAM-only G contract; it prevents claims about every way a running ECU could
reach the input state.

## Where the six words come from

The words at DATA `0360,0362,0364,0366,0368,036A` are little-endian unsigned
**interval-derived estimates, not absolute timestamps**. Acquisition helper
`56BE..5719` is statically inspected but not executed in this stage:

1. Read the current capture TMR2, or saved TM2 observation DATA00F0 when
   DATA011F.2 is set. INT1-path PC03AC/03AE reads TM2 and saves that observation.
   Save the selected timestamp in local er3; DATA00EE holds the previous one.
2. Correct pending timer overflow using IRQH.0, DATA010F.7, counter DATA00AE
   and the duplicate-accounting guard DATA00B6.0.
3. Setting DATA0128.3 tests its old value: a first observation skips all sample
   writes, but updates previous timestamp 00EE and clears overflow count 00AE.
4. Otherwise subtract previous 00EE from the current timestamp, modulo 65536.
   With DATA011F.2 clear, TCON2.2 (TCERR) forces zero when set. Save the result
   via DATA0136 into `0360 + 2*DATA00A2` at PC5710.
5. With DATA011F.2 set, form high byte `(00AE - subtractionBorrow) mod 256`,
   with the next byte zero, and divide the extended unsigned difference by six.
   A nonzero high quotient byte gives a zero sentinel. Save the resulting word
   to every slot, descending offsets `10,8,6,4,2,0`, at PC56FA.
6. Update previous timestamp 00EE and clear 00AE. The byte overflow counter can
   itself wrap; this is not unlimited overflow tracking or verified IRQ timing.

The normal index is 00A2, generally cycling 0..5: PC03B0/043B clear it, 0424
increments it, 047C clears the containing word, 04F6 resynchronizes it using a
remainder modulo six, and 409B initializes it to two. For this established
domain the slot order is 0..5, with resynchronization branches; no unconditional
global monotonic ordering is claimed. The actual byte doubling before EXTND
does not validate arbitrary corrupt indices. Overflow handler PC0302 writes
**banked r6 = DATA00AE** under LRB0015, not a separate unrelated register.

Equal stored intervals are a meaningful steady software vector. In the
divide-six acquisition mode, equal words are six copies of one normalized
multi-event estimate, not six independently measured captures. Event geometry,
interrupt races and the physical reachability of arbitrary vectors are not
established. Acquisition retains history in 00EE, 00AE, the slots and flags.

Three bits must not be conflated:

| Bit | Meaning within the inspected code |
|---|---|
| DATA011F.2 | Acquisition selection above; copied from DATA0217.2 through the 0216-to-011E word snapshot |
| DATA0217.7 | G alternative sample-update mode; written at PC7B13 from conditions involving 0212.3, 01B5 and 021C.6 |
| DATA0217.4 | S, the context consumed by compact F; preserved on G's early zero and cleared after full summation |

## Writer census beyond literal addresses

| Writer | Targets and qualification |
|---|---|
| G PC07A2 | Exchanges the newly computed word into 00C4/00C5; old T is returned in A |
| Initialization PC40CD | Writes FFFF to T; helper 7FF0/7FF8 supplies FFFF after earlier zeroing |
| PC40AD..40BC | Clears all six sample slots with X1=0; PC4097 sets S |
| PC0787 | Clears S after all six additions, including quotient-overflow fallback |
| PC56FA / 5710 | Indexed acquisition fill-six / one-slot writes described above |
| PC7AF5 | G alternative mode writes one to the reached slot **after loading its old value** |
| Startup PC2710 | Bulk word clear includes T, 0216/0217, samples and capture state; optional retained 0300..0355 does not exclude these targets |
| RAM-test helper PC5C68 / 5C6C | Temporary test-pattern exchange and original-word restoration at 0084[X1], covering T/S/samples; startup and runtime walkers cover 0084..047E |
| NMI PC0048 | Restores the RAM-test target from saved DP when 0230.7 indicates an interrupted test |
| Bitmap helper PC5B8A | Indexed SBR at 0212+index can set S for input id 45; the normal table-driven domain excludes it, but the retained-state recovery caller PC26A7 is not fully reachability-proven |

The other explicit 0217 bit writers use byte operations preserving S. Reviewed
ordinary local-bank selections did not establish a C4 or 0217 rN/erN alias
writer. Computed pointers, corrupt retained state and data-as-code remain
outside a global proof. In particular, it would be incorrect to call 4097 and
0787 the *only globally possible* S writers. These bulk/test/recovery operations
are not additional steady RPM producers and are not silently run by G.

## Exact G contract

```text
G(six interval words, previousT, fullByte0217, fullByte0231)
    -> disposition, TWritten, T, fullByte0217, fullByte0231,
       updated six words, processed sample count, assumptions
```

Under the separately named `oki.add-er1-a` hypothesis:

- Normal mode (0217.7 clear): read slots in ascending order. Any zero immediately
  **writes T=FFFF**, preserves S and the other 0217 bits, sets 0231.5, and leaves
  the slots unchanged. It does **not** preserve previous T on this completed path.
- Otherwise sum all six old unsigned words. The low word is er1, the high byte
  is r0; r1 starts at zero. Each word ADD carry is consumed by the immediately
  following byte ADCB. Maximum sum is 393210: 19 significant bits in the
  register-pair representation, with no sum wrap over this domain.
- Clear S and 0231.5. Unsigned DIV by **five**, truncating toward zero, gives
  `q = floor(sum/5)`. If q exceeds 65535, write FFFF and set 0231.5; otherwise
  write q. A valid q=65535 and a saturated fallback share T but differ in status.
- Alternative G mode (0217.7 set): each slot is read, then overwritten with one;
  bypass the zero exit and add the **old** value, even zero. Complete the same
  division/status update. A subsequent invocation without fresh captures sees
  six ones and yields one. Six old zeros instead yield zero, not normal fallback.

All six incoming terms have equal coefficient one **in G**, but division by
five is not a six-sample arithmetic mean. Sample acquisition may have already
divided an aggregate measurement by six. Neither operation can be replaced by
an unexplained average coefficient.

Previous T does not affect a completed G's new T; it is observable in A after
XCHG. Previous S affects early fallback and thus F. Alternative mode changes
future samples, and acquisition history changes present samples. A universal,
history-free physical RPM(T) does not follow. In strict mode an unconfirmed ADD
stops **before** execution: T has not yet been written, and any earlier sample
overwrite is retained in the partial state. This is unresolved, not a passing
"preserved old T" producer result. Initialization seeds are tested, but actual
reset/initialization execution remains **not-run**.

### Narrow execution boundary

| Field | Value |
|---|---|
| Entry / exit | PC0772; stop **before** PC07A5, after the actual T exchange |
| Allowed code | [0772,07A5), helper [7AEC,7AFE) |
| State | PSW1101, LRB0040, SCB1, USP0180; SSP07FE; frozen peripherals/no injected IRQ |
| Input RAM | Six words 0360..036A; previous T00C4; full bytes0217 and0231 |
| Output RAM | T, both full status bytes, all six sample words; also retain actual old-T accumulator output |
| Bounds | G192 instructions; F128; threshold128; at most128 trace steps per selected diagnostic |

No RET/NOP/jump is inserted into ROM. Unknown SFR accesses remain errors;
timer observations are not faked. Scratch patterns 00/55/AA exercise independent
RAM initialization. No scheduler, board boot or new framework is introduced.

## Instruction forms and fixes

G admission matches exact decoded opcode pattern, length and DD contract, not
only mnemonic. It contains **24 patterns: 23 primary-admitted and one conditional**.
The [OKI instruction manual](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/Oki_66201_Instruction_Manual.pdf)
was visually checked, together with the already obtained MSM66201/207 user
manual's HC/register/timer pages. This does not reclassify the missing word ADD
family; no new broad ADD-scan search was performed.

| New/reviewed form | Width, live state and primary locator |
|---|---|
| CLR A (F9) | Word, DD=1, ZF=1; CF/HC preserved; printed3-31 |
| JRNZ DP | Decrement/test DPL only, preserve DPH and flags;3-68 |
| ADCB r0,#N8 | Byte regardless of DD; old CF input, CF/ZF/HC output;3-12, user33 |
| INC X1 | Word, ZF/HC updated, CF/DD preserved;3-60, user33 |
| MOV indexed word,#word | Distinct displacement and immediate fields; flags preserved;3-86 |
| L A,indexed word | Word-aligned effective data address, DD1/ZF from loaded word;3-69,1-20 |
| MOV X1,A; CLR X1; XCHG A,direct word | Selected SCB aliases; flags preserved (unlike CLR A);3-85,3-32,3-168 |
| DIV; CMPB r0,#N8 | Unsigned32/16 quotient; byte comparison even under DD1;3-57,3-42 |
| ADD er1,A (45 81) | **Unresolved**; distinct `oki.add-er1-a`, never authorized by `oki.add-er3-a` |

The remaining admitted loads/stores/jumps/off-page bit forms have explicit
patterns in `instruction_forms.rs`. The CF from ADD is live at ADCB; hypothetical
ADD HC is not asserted and ADCB overwrites HC before any use. er0/r0/r1 resolve
to DATA0200/0201, er1 to0202/0203 and er2 to0204/0205 at this LRB. SCB1 selects
X1 at0088 and DP at008C. Synthetic tests also vary full LRB/SCB contexts.

Six **decoded execution tests failed before fixes**, then passed after minimal
primary-grounded corrections: CLR-A ZF; JRNZ low-byte counting; exact ADCB-r0
half-carry; INC-X1 half-carry; separate indexed displacement/immediate decoding;
ordinary word-data address alignment. Raw caller seeding and ROM byte addresses
are not aligned, and user-stack exceptions remain separate; overflow checks
precede architectural alignment. One old odd-USP synthetic expectation was
corrected to the documented even word boundary. Actual M1d operands were aligned
and all M1d real counts remained unchanged.

Runner version is 0.2.0, protocol remains1. Its ten explicit fix identities are
validated. M1d may still use version0.1.0 with exactly its old four fixes;
producer execution requires0.2.0 and the full audited set. There is no generic
allow-unknown switch, nor promotion through model agreement.

## Composition and actual case accounting

Actual G exits at07A5, then only PC is staged to07C7 **on the same CPU/RAM**.
The omitted07A5..07C7 bridge updates history036C/036E/0370, deltasC6/C8 and
021B.6/.7, but not T/S. F overwrites its needed scratch registers/flags before
using them. Those omitted side effects are not claimed to execute. This is
staged seeded composition, not continuous execution of the surrounding routine.

F's actual Code feeds a fresh M1d threshold snapshot with explicit per-case
context, prior pair bits and enable. C# never injects its expected T or Code in
place of actual G/F outputs. Assumptions accumulate across stages, including
through a threshold fragment that itself needs neither ADD hypothesis.

One process handles each batch. The deterministic **133978** input cases are:

| Group | Cases |
|---|---:|
| Every uniform interval word0..65535, normal G mode |65536|
| Every uniform interval word0..65535, alternative G mode |65536|
| Each zero position / prior T / status / scratch combinations |576|
| Initialization-like seeds, not reset execution |96|
| Change one sample at a time |108|
| Carry/division boundaries |32|
| Quotient-width boundaries |32|
| Alternating, steps, acceleration/deceleration ramps |14|
| Deterministic raw random inputs, seed42140897 |2048|

This is not exhaustive over the six-word domain. Physically unreachable inputs
may be included; reachability is explicitly NotEstablished. Seeded contexts are
distributed across both selectors, four prior states, enable/disable and three
scratch patterns, not a full Cartesian product of every factor.

Actual unchanged-ROM results (each G row has exactly one staged F opportunity):

| Mode / stage | Strict matches | Conditional matches | Unresolved | Not-run | Mismatch/error/budget |
|---|---:|---:|---:|---:|---:|
| Strict G |98|0|133880|0|0|
| Strict G to F |98|0|0|133880|0|
| Only er1 permission, G to F |98|127662|6218|0|0|
| Both ADD permissions, G |98|133880|0|0|0|
| Both ADD permissions, G to F |98|133880|0|0|0|

The 98 first-zero paths never reach ADD. Later zero positions do reach ADD and
are therefore unresolved in strict execution. Conditional G dispositions:
345 zero fallbacks, 111762 new values, 21871 quotient-overflow fallbacks.
The report separately counts actual uses of each assumption; a conditional
downstream row need not have executed F's ADD itself. Actual use counts are
133880 for er1 and6218 for er3. A separate actual batch allowing only er1
stops those6218 F cases as unresolved and does not run their thresholds.

For **each** baseline and verified existing M1c child, the conditional threshold
stage has133978 comparisons:98 strict and133880 cumulatively conditional,
zero mismatches/errors/unresolved/budget. It verifies133978 program-read sets
and66989 disabled-state preservations per image. There are133978 paired results:
the edited slot is read33495 times, selected16748 times, and the final predicate
changes in exactly **two** cases, matching the independently expected changed
case set. Reading a word is not selecting its edited byte, and selecting it is
not sufficient to change a strict comparison. No new child or ROM output was made.

M1d regressions were actually rerun with the new CPU:393216 compact cases per
mode, strict372120 matches plus21096 unresolved; conditional372120 strict plus
21096 conditional matches. Baseline/child threshold results remain12288 matches
per image/mode. No mismatch, execution error or budget exhaustion occurred.
Selected diagnostics are bounded; at most four failing cases can be replayed
as diagnostics, never added to independent case counts.

## Physical evidence chain, not a fitted conversion

The already obtained manufacturer user manual, printed81-93 (timer chapter),
distinguishes TM2 counter0038, TMR2 capture register003A and TCON2 control0042.
The candidate initializes TCON2=82 at25CC and sets RUN bit4 at2615. The bounded
listing census finds no additional explicit mode write; later3FA3/5701 are
reads. TM2/TMR2 are initially zeroed. According to table/figure9-2 and capture
mode section9.2(3), these settings specify:

- Internal timer source selector100: TBC3, **CLK/32**, not CPU instruction speed.
  Timer2 has no external *timer-clock* input. CLK frequency itself remains unknown.
- Mode C capture, free-running counter and falling-edge event input
  TM2IO/P3.6; configured P3 secondary functions are distinct from board wiring.
- At an event, TM2 is captured into TMR2. TCON2.2 is TCERR, indicating the
  previous capture interval spans the manual's FFFF-or-more condition; normal
  acquisition uses it as an invalid/zero sentinel.
- Counter overflow sets IRQ bit8; the acquisition's separate overflow byte and
  saved TM2 path are software accounting, not emulator-generated elapsed time.

This derives register configuration using the MCU manual; it does not
authenticate that the archive candidate belongs to a particular physical board.
No matching-revision primary schematic, oscillator marking/measurement or sensor
to pin/edge-to-crank mapping has been established. Missing clock chapter scans
and a possible CLKOUT divider are not filled using an assumed oscillator. A
different P28 board's schematic is not substituted. Falling MCU pin edges need
not correspond one-for-one to unconditioned sensor pulses. Crank versus cam
revolutions, event accumulation and selected capture paths remain explicit
dependencies. The host runner's instruction counts have no physical-time meaning.

For a defined normal interval, let m be events per stored sample and E be events
per **crank** revolution. Dimensional reasoning gives:

```text
timerHz = CLK / 32                  (candidate's configured clock selector)
p_ideal = 60 * timerHz * m / (rpm * E)
sample ticks belong to floor/ceiling quantization, subject to valid acquisition
T = floor((s0+s1+s2+s3+s4+s5)/5), with documented zero/saturation branches
```

Only for equal, positive, unsaturated normal intervals, ignoring integer
quantization, does `rpm*T` approach `72*timerHz*m/E = 9*CLK*m/(4*E)`.
An exact inverse still has quantization intervals, and transient/mixed histories
and alternative modes invalidate a single memoryless conversion.

The [historical OBD1 16-bit RPM page](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/bin/view/Library/OBD1_16bitRPM.html)
publishes `RPM = 1875000/raw`. It is a comparison lead, not the primary hardware
derivation. Our independently derived symbolic coefficient cannot establish
that number without the missing CLK/m/E evidence. Matching it would require
`9*CLK*m/(4*E)=1875000`; **no clock, pulse count or divisor was chosen to make
that equality true**. No numerical source-backed RPM is claimed.

## Command and explicit conditional preview

```shell
hondaecu research p28-vtec producer-check private/oracle/p28-304/base.bin --profile p28-304 --confirm-profile --baseline-binding private/reports/m1b/baseline-binding.json --runner rust/p28-slice-runner/target/release/p28-slice-runner --output private/reports/m1e/producer-strict.json
```

On Windows add `.exe` to the runner. Conditional execution requires separate
options `--allow-assumption oki.add-er1-a` and, for F's unresolved path,
`--allow-assumption oki.add-er3-a`. Supplying only the latter does not admit G.
An optional existing child requires all three `--derived`, `--plan`,
`--patch-report` options, checked through unchanged M1c lineage. No set-rpm option
exists. Every output must be a new path, distinct from all inputs/profile/runner.

Without `--scaling`, the report is `unavailable-symbolic-only`, with no numerical
defaults. With it, a bounded64KiB JSON file must have exactly these properties:

```json
{
  "formatVersion": 1,
  "scope": "uniform-normal-intervals",
  "quantities": {
    "clockHz": {"numerator":"1000000","denominator":"1","unit":"Hz","provenance":"Invented example, NOT measured candidate hardware","evidence":"analyst-supplied"},
    "timerClockDivisor": {"numerator":"32","denominator":"1","unit":"1","provenance":"Explicit use of documented selector for this calculation","evidence":"source-derived-claim"},
    "eventsPerCrankRev": {"numerator":"3","denominator":"1","unit":"events/crank-revolution","provenance":"Invented example, NOT established sensor geometry","evidence":"analyst-supplied"},
    "eventsPerSample": {"numerator":"1","denominator":"1","unit":"events/sample","provenance":"Explicit normal interval assumption","evidence":"analyst-supplied"},
    "rpm": {"numerator":"3000","denominator":"1","unit":"crank-revolutions/minute","provenance":"Requested conditional preview input","evidence":"analyst-supplied"}
  }
}
```

These are **illustrative inputs, not hardware defaults or a public profile**.
Each rational component is a positive decimal string bounded at10^12; units
are exact, with no silent MHz-to-Hz or cam-to-crank conversion. Provenance is
required. Allowed evidence labels are analyst-supplied, source-derived-claim
and hardware-measurement-claim; even a supplied measurement claim is unverified
input here. A file can choose a different divisor only as its explicitly
recorded scenario, not as evidence that the candidate configures that divisor.

The preview returns exact reduced rational timerHz/ticks and a conservative
floor/ceiling phase envelope of G outputs, with assumptions beside the numbers.
It excludes aggregate-divide-six acquisition, mixed history and alternative G
mode. It does not assert every phase combination is dynamically reachable.
Intervals reaching normal capture's TCERR boundary (FFFF or more), including
the numerically representable word FFFF, produce no invented valid/wrap preview. The
arithmetic G hypothesis used by this calculation grants no byte-execution
permission. `physicalRpmAvailable` remains **false** everywhere.

The illustrative file above was actually passed through the command in the
er1-only batch: timerHz31250/1, ideal ticks625/3, integer envelope208..209,
G outputs249..250. These numbers demonstrate explicit rational calculation
only; the invented clock and event count are not measurements of this ECU.

## Verification and remaining gates

Pinned Rust1.85.1 Release build/test, .NET8 Release build/test, format, privacy,
whitespace and input-preservation checks passed: **43 Rust tests and278 .NET
tests (245 Core,33 CLI), zero failures/skips, zero build warnings/errors**.
Rust formatting preserves the pinned generated opcode table verbatim. The public
Windows/Linux CI builds Rust before .NET tests; real subprocess tests fail,
rather than skip, if the runner is missing. Public coverage includes decoded
forms, G state/carry/truncation, actual G-to-F transfer, cumulative assumptions,
protocol/binding refusal, no-default scaling, rational units, quantization and
malformed/oversized scaling JSON. Private real runs are separate from these
synthetic tests; not-run reset/capture/hardware stages are never reported as pass.

Remaining evidence gates: primary semantics for each of the two distinct word
ADD forms; matching hardware clock and edge/event geometry; acquisition timing
and reachability (including retained-state recovery); editor validation;
independent checksum correctness and physical ECU behavior. Software success
does not resolve any of these by itself. No editor installation, GUI, full
boot, checksum change/bypass, writable RPM definition or ECU write was made.
