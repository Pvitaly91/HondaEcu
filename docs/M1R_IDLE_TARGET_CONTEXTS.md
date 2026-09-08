# M1r - Idle-target context, override and component validation

M1r extends the isolated target producer, not the complete idle controller.
The explicit base is `codex/p28-idle-target-validation-m1q` at
`c845df6cde8f49bb49c7672d5e543c09364b2481`; work belongs only to
`codex/p28-idle-context-validation-m1r`. M1q and its 858 historical checkpoints
remain closed. Its scenario v1, `idleTarget`, guards and reports are unchanged.

The new `idleContexts` task and `contexts-check` execute actual source selection,
target production and the existing error consumer on one CPU/RAM history.
There are no conditional instruction permissions. Physical reachability of the
explicit software snapshots is unknown; rawD9 is not a temperature conversion,
and selector bits are not named A/C, transmission or warm/cold engine modes.

## Established order and sources

All 11499 instruction rows in the existing private listing were freshly matched
to the unchanged original bytes. Pointer operands, native vectors and both
packed footprints were independently checked. No other ROM was acquired.

The order is:

1. `2FD1` captures rawD9, loads X1 with68CB and enters the7D8A hook.
2. The hook inspects0216.3; it does not choose a different initial table here.
   Its two r2 constants are identical in the bound original.
3. Raw-domain and history gates choose a base lookup or an immediate candidate.
   A candidate may itself be superseded by another candidate or by base lookup.
4. `3072` preserves the base result in DP. `3073..309A` computes/stores a
   **separate** word 027A; it is not added to or subtracted from025C here.
5. `309D` tests021A.0. Set retains the base result. Clear runs a late lookup
   from68E0, replacing the base result but preserving the computed027A.
6. `30A9` stores final025C as a word (live DD=1, despite the listing's byte
   heuristic). Stop before30AB. Every completed supported path writes a target;
   no retained/hold-target outcome exists in this boundary.
7. Consumer09DC..09F4 reads actual025C, subtracts it from unsigned current C4,
   stores borrow in021A.4 and min(abs(current-target),768) inCA. Equality gives
   sign=false/error0. The consumer is unchanged from M1q.

| Source | Exact footprint / construction | Interpretation and readers |
| --- | --- | --- |
| Base packed table | `[68CB,68E0)`; X1 operand2FD5..2FD6 | Seven triples: unsigned byte axis followed by unsigned u16LE target. Base VCAL0 at306F, helper5894 |
| Late packed table | `[68E0,68F5)`; X1 operand30A3..30A4 | Independently verified seven triples, same ABI/helper through VCAL0 at30A5, different numeric words |
| Initial immediate | Word operand2FE3..2FE4 at2FE2 | Candidate base target; 7D98 may replace it with the next immediate |
| Hook immediate | Word7D9C..7D9D at7D9B | Replaces the initial immediate when0216.3 is clear |
| Second immediate | Word300E..300F at300D | Base candidate selected by low-domain/history gates |
| Third immediate | Word3055..3056 at3054 | Retained only when0211.5 is set; otherwise the later candidate/gates execute |
| Fourth immediate | Word3065..3066 at3064 | Retained only when0225.1 is set; otherwise306E base lookup replaces it |
| Component peaks | u16LE operands2FE7..2FE8,7DA0..7DA1,3012..3013,3059..305A,3069..306A | Immediate stores to er3; cleared at3070 after base lookup; used by3073 and3081 |
| Component lower axis | Byte68DA, from X1 operand3077..3078 plus displacement307B..307C | Program-byte reader3079; the base table's40 knot |

Immediate instruction operands are decoded values, **not program-data reads**.
Reports separate candidate `sources`, performed `lookups`, their arithmetic,
and `finalContribution`; an absent lookup is an empty observation collection,
not a zero lookup value. `componentCalculation` is null when3074 skips it,
while the actually written component zero remains an observed zero.

Both actual axis lists are255,161,135,110,52,40,0. Each table spans the byte
domain, but caller gates determine whether its helper is reached. The shared
helper selects the first lower knot <= input and computes
`lowerY +/- floor(abs(upperY-lowerY)*(x-lowerX)/(upperX-lowerX))`.
Program-word reads are not aligned: ordered overlapping reads at X1, X1+4
and X1+2 plus byte exchanges reconstruct the packed fields. Multiplication
is16x16->32, division uses the full product, and signed direction is applied
after nonnegative truncation. C# reuses this established integer algebra in a
separate contexts model; no second instruction interpreter is introduced.

Base lookup can genuinely reach the40-to0 segment for rawD9 values22..39
when the low-domain gates fall through. In this original the segment's target
words are equal: node 0 is read as the lower record, not directly sampled by
an artificial helper call. For rawD9<22 the producer always takes the first
immediate instead of base lookup. The late table can be looked up for every
rawD9 including0. Any base lookup may subsequently be replaced by the late one.
X2 values68F5/6911 are forwarded for code after30AB, not additional target
tables read inside this boundary.

## Conditions, equality and dependencies

Addresses below identify the branch; parenthesized addresses identify CMP
operands when applicable. All comparisons are unsigned. Branch targets are
true/false respectively; equality is included only by >=, <= or ==.
`x` means rawD9, `t` the current r1 threshold, `P` the current component peak.

| Branch | Tested condition and operand provenance | True / false next PC |
| --- | --- | --- |
|7D8F|0216.3 set|7D95 /7D92; both continue toward2FDC, latter sets r2 again|
|2FDE|x>=22 (CMP2FDC, byte2FDD)|2FEC /2FE0|
|7D98|0216.3 set, after first immediate|7DA2 /7D9B|
|2FED|x>=r2=52 (CMP2FEC; r2 operands7D8E or2FDB)|306E /2FEF|
|2FF1|0217.6 set|3016 /2FF4|
|2FF9|0274>=8000h (CMP2FF4, word2FF7)|300A /2FFB|
|3000|0216.3 set, after CMP2FFB with word2FFE=0D00h|3008 /3003; latter repeats CMP with word3006|
|3008|0274>=0D00h from selected CMP|2FE0 /300A; together these gates select interval[3328,32768)|
|300B|x>=t=49 (CMP300A; r1 byte2FF0)|306E /300D|
|3016|022A.4 clear|3023 /3019; latter sets E8=30/E9=90 then first immediate|
|3023|0225.1 clear|302C /3026|
|302A|E8!=0 (CMP3026, byte3029)|2FE0 /302C|
|302D|x>=49 (CMP302C)|306E /302F|
|3031|027C==0 after word load302F|3037 /3033; latter sets E5=30|
|3039|E5!=0 after byte load3037|300D /303B|
|303B|022A.5 clear|3044 /303E; latter sets E9=90 then second immediate|
|3044|0225.1 clear|304B /3047|
|3049|E9!=0 after byte load3047|300D /304B|
|304B|0216.3 clear|305E /304E|
|3052|x>=47 (CMP3051; threshold byte304F)|306E /3054|
|305B|0211.5 set, after third immediate|3072 /305E|
|3062|x>=46 (CMP3061; threshold byte305F)|306E /3064|
|306B|0225.1 set, after fourth immediate|3072 /306E|
|3074|P==0 after word load3073|309A /3076|
|3082|CF or ZF, after SUBB r0,A at307F then L A,er3 at3081|309A /3084; for positive P this is x<40, **not x<=40**|
|308B|t<=x (CMP3088 againstD9)|3099 /308D|
|3091|t<=40 after SUBB r4,A at308F|3099 /3093|
|309D|021A.0 set|30A9 /30A0|
|5898|x>=next axis (CMPCB5894)|58A1 /589A; false advances pointer by3 and repeats|
|58BB|upperY<lowerY, or0<P for component helper entry58BA|58BD /58CA|

The0300 consumer clamp and its equality behavior remain M1q's established
consumer contract. Both outcomes at09E7 and09EF are covered in M1r inputs.

For nonzero P the component is P below40. From40 up to its selected threshold
it is `P-floor(P*(x-40)/(t-40))`. P/t are1280/52,896/49,640/47 or512/46
in this original; first/hook peak operands agree. The underflowed byte
`(x-40) mod256` is still an observed register store for x<40, but is not used
as an interpolation distance on that branch. There is no signed component or
word-wrap sum into target. At a threshold the caller selects base lookup and
clears er3/component; it does not traverse the helper's zero-clamp branch.

All 30 conditional branch sites and 58 distinct outcomes were observed. The two
arms `308B->3099` and `3091->3099` were **not executed**: selected immediate
paths require x<t, and all admitted original thresholds exceed40. These are
code-understood but unreachable arms under this exact image/software contract,
not counted as dynamic coverage and not forced by changing axes or opcodes.

## Ownership and schedule

All schema fields are required. Initial bytes/words are explicit software
snapshots, not reconstructed power-on values. Target/component/error/history
are seeded once for each sequence/image/scratch and never overwritten per call.

| Field | Native writer; relevant reader | External input / persistence rule |
| --- | --- | --- |
|D9, C4|Upstream acquisition excluded; producer2FD1/30A0 and consumer09DC|Only per-call rawD9 byte and rawPeriod word are supplied|
|021A.0|2FCE bit move from carry, outside scope; read309D|Only mask01 may change per call|
|021A.4|09E1 native error-sign write; downstream reader outside scope|Never a scripted input; mask01 preserves sign and all other bits|
|0211.5|Whole-byte stores2894/2DCE from4700-based input; read305B|Only mask20 scripted; native upstream writer not run|
|0216.3|7B45 bit writer; read7D8F/7D98/3000/304B|Only mask08 scripted|
|0217.6|6039 bit writer from upstream flags; read2FF1|Only mask40 scripted|
|0225.1|2848/4D0C/4D9D set,4D8E reset; read3023/3044/306B|Only mask02 scripted|
|022A.4/.5|2F41/2F4D carry-to-bit writers from rawDC comparisons; read3016/303B|Only masks10/20 scripted; other bits retained|
|025C/025D|30A9 word store; read09DE|Seed once, then actual native producer->consumer handoff|
|027A/027B|309A word store; later readers outside boundary|Seed once; independent native component, not a host correction|
|CA/CB|09F2 word store; regulator readers outside boundary|Seed once; native error magnitude persists|
|0274/0275|36CB downstream word store; read2FF4/2FFB/3003|Seed once; writer not run, no per-call history substitution|
|027C/027D|32A3 word store; read302F|Seed once; writer not run|
|02E5|3033 set;3037 read|Seed once; native set persists, no host decrement|
|02E8|3019 set;3026 read|Seed once; native set persists, no host decrement|
|02E9|301D/303E set;3047 read|Seed once; native set persists, no host decrement|

A static additional counter writer was found: call3CE8 selects X1=02CB,
DP=26h and helper5BC9..5BE3 visits02CB..02F0. It conditionally decrements
nonzero bytes at5BD5, including E5/E8/E9, with IE/interrupt-state manipulation.
Neither that service nor its caller schedule is executed in this task.
Counter expiration is not claimed; zero/nonzero history is compared using
separate once-seeded sequences. Scripted selector changes do not masquerade as
native mode transitions. Included counter sets and sign writes remain native.

Entry actions change PC/LRB/PSW/USP only, separately from persistent RAM.
Producer LRB41, consumer LRB40; PSW1101, SCB1, USP0180, SSP07FE initially.
Native calls push a word at07FE then decrement SSP to07FC; returns balance it.
No SSP reseed between stages, ROM trampoline or replacement RET is used.

Producer code ranges are `[2FD1,30AB)`, `[7D8A,7DA5)`, `[5894,58D3)`.
Consumer ranges remain `[09DC,09F4)`, `[59A6,59AD)`. Program-data reads are
limited to vector28..29 and tables68CB..68F4 for producer, vector36..37 for
consumer. DATA ranges are exactly the aliases, inputs and state described in
the versioned entry contract, not an unrestricted SFR region. There are no
peripheral stubs, IRQs, capture/G integration or inferred milliseconds.

The new per-stage budget is256 instructions. Native decision events cover the
whole stage; the existing textual trace retains its first128 entries. Validation
checks that prefix against events and checks full event continuity, code
extents, journals, exit and balanced stack. The measured maximum is141 producer
instructions. This does not change M1q's128-instruction scope or evidence.

## Independent model, ISA and protocol evidence

C# owns an image copy and its own persistent history, never seeded from a prior
Rust checkpoint. Validation checks masked input state, ordered native stores
(including repeated identical values and register/stack aliases), ordered
program reads, every conditional branch, CMP operands, lookup/override/component
accumulator intermediates, producer state and actual consumer subtraction flags.
The expected target is never passed to Rust. Terminal unresolved/error/budget
stops make later stages/calls NotRun with null outputs, not a held old target.

Runner 0.10.0 explicitly adds `idleContexts`; the0.9.0 identity and old contracts
remain accepted for their own operations. No executor semantics changed in M1r.
Only exact additional admission templates were added: CMPB A,r1; CMPB off,#byte;
CMP off,#word; MOVB r1,r2 /r1,#byte /r4,A; MOV er3,#word; JBS off.6;
JBR off.5; JLE; indexed-displacement LCB; STB A,r5; XCHGB A,r1/r4.
Old er1/er3 ADD and conditional SUBB permissions are not promoted or inherited.

Existing primary instruction scans were reviewed visually: printed3-38/39/42
for CMP widths and CF/ZF-only effects;3-64/65/66 for bit/relative/LE branches;
3-76 for LCB low-byte transfer with unchanged DD;3-83/94/96/99 for MOV forms;
3-169 for byte exchanges; earlier3-155 evidence supplies STB/DD behavior.
Invented decoded-opcode regressions test aliases, widths, flags, equality and
both branch directions. No new broad instruction search or OEM program fixture
was needed. Preliminary strict refusal probes are retained privately, not
counted as successful final evidence.

## Actual private validation

Final new-task evidence contains 104094 StrictMatch checkpoints across 576
reports, with zero Conditional, Unresolved, NotRun, ExecutionError, BudgetExceeded
or Mismatch checkpoints. Breakdown (each includes all three scratch patterns):

| Series | New-task checkpoints | Scope |
| --- | ---: | --- |
|128 selector combinations x256 rawD9|98304|512 sequences of64 calls; once-seeded zero correction/counter history|
|0274/027C history boundaries|1428|0274 around3328/32768 and word extremes;027C=FFFF case|
|Counter/upstream-history cases|612|E5/E8/E9 and027C each0/1/255, without per-call reseeding|
|Scripted transitions/repeats|36|Native sign/counter retention across masked input changes|
|Consumer edges|2052|Four contexts,19 raw points, current below/equal/above and +/-767/768/769|
|A/B|1050|Seven contexts,25 inputs, two independent images/histories|
|M1q compatibility, new side|612|All204 supported raw inputs x3 scratch patterns|

The compatibility series additionally ran 612 old-task checkpoints. Each old/new
pair matches all established state fields, ordered reads/writes, complete events,
trace, executed byte extents, exits and stack. These fresh pairs do not reuse or
reclassify the 858 historical M1q checkpoints.

The full flag-domain sweep proves the explicit snapshot contract, not all ECU
states. Other raw/history inputs are boundary samples, not an exhaustive word
Cartesian product or a recovered scheduler. Dynamic coverage excludes the two
unreachable3099 arms noted above, all upstream selector/history writers, the
counter decrement service, downstream regulator/PWM and physical plant.

## A/B influence without a firmware file

Only existing field ID `context-21a0-table-cell-2`, word68D2..68D3, is admitted
for in-memory mutation. Original1442 was checked before choosing1458. Actual
diff is the low byte68D2 only; every other byte is guarded. The other table,
axes, pointer operands, selector tests and opcodes are unchanged. A/B have
independent CPU/RAM and independent model images. No B binding is fabricated.

At rawD9=135/current=1450 with the base retained, native targets are1442/1458,
error magnitudes8/8, sign=false/true. This is a meaningful consumer-input change
despite equal magnitudes. When021A.0 is clear the changed base lookup can be
read/calculated and then replaced by the68E0 result. Low immediate paths skip
the mutated base lookup. Adjacent interval effects stop at the unchanged knots;
raw 111 is a genuine truncation control, whereas raw 110 reads the changed cell
with zero interpolation weight and must not be called truncation.

Reports distinguish `BaseLookupNotExecuted`, `CellNotRead`, `CellReadZeroWeight`,
`IntegerTruncation`, `ReadThenLateSourceReplacement` and target/consumer changes.
Separate027A is identical across A/B: this mutation affects a high-domain cell,
where base lookup clears the component. In this boundary027A cannot numerically
mask or preserve a target difference because it is not applied to final025C.
No such additional correction effect is invented. Original/B arithmetic residues
are0/16; they are observations, never repaired. No firmware BIN was created.

## Headless use and remaining boundary

```text
hondaecu research p28-idle contexts-inspect <baseline.bin> --profile p28-304
  --confirm-profile --baseline-binding <binding.json> --output <new-private.json>
hondaecu research p28-idle contexts-check <baseline.bin> --profile p28-304
  --confirm-profile --baseline-binding <binding.json> --runner <rust-runner>
  --scenario <private-context-scenario.json> --output <new-private-report.json>
```

`contexts-inspect` is a separate read-only report contract; the old `inspect`
and `target-check` retain M1q meaning. Unknown images receive general data only.
Confirmation cannot replace exact binding. Scenario v1 requires purpose
`idle-target-contexts-software-test`, bounded provenance, all once-only state
fields,1..64 densely indexed calls with required rawD9/rawPeriod/selectors, and
nullable code-owned mutation. `selectors:null` preserves all selector bits;
an object requires all seven booleans and allows only their masks.
Arbitrary RAM writes, caller PCs and per-call produced/history values are refused.

The shared bounded process transport supplies timeout/cancellation; report
writing reuses input snapshots, alias/existing-output protection and atomic
new-file creation. CLI prints source/raw-range and disposition summaries.
Public tests contain invented metadata/programs only, including real Rust
subprocess tests for handoff/history, masks, strict refusal, budget termination,
malformed protocols and transport behavior. Both explicit .NET solutions and
pinned Rust 1.85.1 are checked, including old export/ISA regressions.
Local final suites pass: Core 684, CLI 283, Desktop headless 81, Rust 135;
.NET/Rust formatting and the privacy/preservation checks are required before
commit. Desktop headless tests and clean CI portable artifacts are not GUI acceptance.

Both numeric table families and the mapped immediate targets/component peaks
are candidates for a **future separately scoped** idle editor, not writable
definitions in M1r. No editor/export/admission/signing/compensation authority is
added, and no GUI code changes. `physicalRpmAvailable=false`;
`PcInspectionOnly / NotFlashReady`; GUI r3 paused/NotRun; hardware/full boot
NotRun. These excluded activities are not unfinished M1r requirements.
