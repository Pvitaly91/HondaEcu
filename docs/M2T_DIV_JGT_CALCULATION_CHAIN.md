# M2t — DIV evidence and unresolved JGT calculation path

Delivered status: **Blocked / Partial**, not strict positive-divisor calculation
closure. Historical [M2s](M2S_COMMON_RESULT_CONSUMER_CHAIN.md) remains Partial:
`ZeroDivisorUndefined` before2333 and `PrimaryJgtConditionConflict` before233A
are not erased. Quartet consumers remain NotRun.

## Separate read-only operation

Runner0.28.0 adds `fuelDivisionDecisionChain` and a separate report. Runner0.27.0
is not admitted for this operation. The command is:

```text
hondaecu research p28-fuel division-decision-check <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --runner <runner-0.28.0> --scenario <m2t-scenario.json>
  --output <new-private-report.json>
```

The closed/version1 scenario reuses M2s sources under the distinct purpose
`division-decision-native-software-test`. DATA0136 has one once-initial storage
source; no per-event rewrite or second divisor field exists. PC, RAM, registers,
dividend, quotient, remainder, flags, branch targets and ready results are not
scenario inputs. One-field A/B mutations are in-memory only, never firmware
outputs. A blocked report returns verification failure, not success.

M2r continues into literal22B1 on the same CPU/RAM. Execution primitives and the
independent C# history/journal oracle are reused, not old report observations or
a JSON-to-RAM handoff. Historical operation, schema, contracts and old reports
are unchanged. New M2t report categories distinguish JgtEvidenceBlocked,
ZeroDivisorUnresolved, ExecutionError, BudgetExceeded and NotRun. Counter/disable
software bypasses are separately SoftwareBypassNotCalculation; an incomplete
upstream prefix is PrefixUnresolved. There are no StrictMatchPositiveDivisor
events in this delivery.

## Primary instruction review

The existing MSM66201 Instruction Manual was visually reviewed in full-page
renders, retained privately. Printed3-57 specifies the exact word DIV form:
unsigned32-bit dividend with upper word er0 and lower word A, unsigned16-bit
divisor er2, quotient upper er0/lower A, remainder er1. It is independent of DD.
For positive divisors CF clears and ZF reflects the entire quotient being zero;
other PSW flags, including HC and DD, are preserved. INT47/EXT63 are instruction
accounting, not measured elapsed time. Existing executor positive-DIV behavior
matches this specification. No executor semantic fix or new fix identity was
justified; DIVB and unrelated forms were not changed.

At divisor0 the manual defines CF but leaves quotient/remainder undetermined.
The strict chain stops **before2333**. It neither executes DIV nor invents numeric
outputs/flags for continuation. Completed prior writes remain; fresh calculation
output is null, retained013B is not a fresh result, and later inputs/ticks are
not applied after the terminal stop.

Printed3-66 JC condition/address table specifies JGT as `(ZF=0) OR (CF=0)` while
labeling it greater-than. Its LE row specifies `(ZF=1) OR (CF=1)` and labels it
less-or-equal. CMP A,obj printed3-35 and SUB printed3-157/159 establish subtraction
direction and borrow; with equality CF0/ZF1, or below CF1/ZF0, that printed OR
makes both GT and LE true. No footnote resolves this conflict. PSW/flag definitions
and DD context were reviewed too. This is an erratum candidate, not a verified
erratum or permission to choose the conventional predicate.

| CF | ZF | Printed MSM66201 OR | Existing executor AND | M2t admission |
|---|---|---|---|---|
| 0 | 0 | true | true | Blocked |
| 0 | 1 | true | false | Blocked |
| 1 | 0 | true | false | Blocked |
| 1 | 1 | false | false | Blocked |

The local MAC66K primary material lists the mnemonic without a runtime predicate.
The local nX8/500S core manual specifies unsigned AND for a different core and
encoding; it cannot override MSM66201. The byte-identical duplicate MSM66201 PDF
is not independent confirmation. No uncontrolled web discovery was performed.

Existing executor predicate before/after is `!CF && !ZF`, unchanged. **Final
strict M2t predicate: unresolved.** Neither OR nor AND is promoted into admission
or the independent model; no assumption, heuristic or ROM-intent interpretation
is used. JGT/JLE and unrelated global branch semantics remain unchanged.

## Native prefix and boundary

Current03B4 is read at232A; actual CAL5991 and RT produce the helper result.
232E clears er0,2330 reads word0136 into er2,2333 executes exact word DIV, and
2335 consumes DIV CF. For the established positive-divisor path,2335 falls
through to2337. Word CMP A,#11 uses A minus11, setting borrow CF and equality ZF,
preserving HC and DD. It is the immediate flag producer for233A; no intervening
writer exists. DD1 is established natively, not imposed at a new host entry.

The source audit checks original bytes against the matching listing, including
the exact DIV and JGT forms. The static signed rel8 calculation gives target2369
and fallthrough233C at233A. **Neither continuation is dynamically selected.**
Positive-divisor execution stops before233A; candidate013B write236A/stop236C
is not claimed as a completed calculation output. No host PC2333/233A is used.

C# independently derives histories, helper/numerator, divisor, quotient,
remainder and DIV/CMP flags. Rust observations are checked against that oracle,
including ordered accesses/register writes, exact forms, widths, flag ownership,
stack/PC continuity and terminal state. Proof fields are derived only after
validation; correct retained/final013B cannot substitute for correct branch proof.

DATA0136's static upstream word writers can write zero and depend on timer/IRQ
state. Its producer remains NotRun; nonzero is not asserted as an engine invariant.
Separate scenarios exercise storage-domain0,1,2,37,60000,65535. These are software
storage inputs, not verified engine-reachable measurements.

## Targeted actual-ROM evidence

The sealed corpus has22 scenarios,81 scratch/image sequences and174 event rows:

| Category | Rows |
|---|---:|
| Strict positive calculation completion | 0 |
| Native positive DIV/CMP; JgtEvidenceBlocked | 78 |
| ZeroDivisorUnresolved | 3 |
| Completed software bypass, not calculation | 12 |
| Subsequent NotRun | 81 |

There are93 completed M2r prefixes. Actual quotient10/11/12 is reached in both
map contexts through native current03B4=8/9/10, helper10/11/12 and divisor1,
not a host A assignment. Separate history scenarios repeat inputs, persist013B/
013D, change current03B4, and stop later inputs/ticks after the blocker.

Thirty A/B comparisons comprise15 executed comparisons and15 subsequent NotRun:
6 fuel-cell quotient-divergence witnesses,6 DivisionTruncation cases,3 adaptive
numeric controls. The selected cell feeds0140/current03B4/helper/DIV; the adaptive
word changes threshold/request/gated03A2 while current03B4 and quotient stay the
same. Calculation reads current03B4, not gated03A2. No BranchSameSide decision is
claimed while JGT is unresolved. JGT/output witnesses=0, model-only actual rows=0.
Earlier exploratory scenarios and historical compatibility counts are excluded.

Invented ISA regressions cover256 positive generic DIV vectors, including nonzero
upper dividend, both DD/HC settings and register banks; zero asserts only defined
CF. All four flag states are refused by JGT admission. Invented CMP10/11/12->JGT
probes stop before JGT and both distinct downstream stores remain NotRun. CF1/ZF1
cannot come from ordinary unsigned CMP and is covered by a direct admission test.
Negative provenance tests reject the specified injections, forged widths/flags/
forms, register destinations, PC resets, assumptions and fake zero continuation.
Timeout and active cancellation are checked with an invented child process.

Independent actual compatibility checks preserve M2s/M2r/M2q/M2p/M2o boundaries
and M2s zero/JGT terminal behavior; they are not new M2t chain coverage. Public
CI uses invented fixtures only. Manual renders, OEM windows, exact source hashes,
native reports and before/after preservation evidence remain private.

## Limits

PcInspectionOnly / NotFlashReady; physicalRpmAvailable=false; physical fuel/time/
degrees unavailable. M2s Partial, quartet consumer NotRun, strict M2i Blocked,
GUI r3 paused/NotRun, D1/D2 interactive acceptance NotRun, hardware/full boot NotRun.
No05DF/1550 scheduler seam,2394/P1/P2/RTI/IRQ expansion or GUI use. New firmware
BIN, bindings, compensation, export plans/receipts/tokens all0. No next stage
starts automatically after the private final report.
