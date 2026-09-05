# M1f - Native ROM checksum analysis and verification

Base: `origin/codex/hondaecu-desktop-preview-d0`,
`0228f3b104f17ec36832a86409ce8f2629b9201c`.
Work branch: `codex/p28-native-checksum-validation-m1f`.

This is a read-only, exact-research-binding-scoped integrity check of the existing
archive candidate. It is not a universal P28 checksum, factory authentication,
checksum repair, full ECU boot or physical hardware validation. All results,
including a scoped Valid, remain **PcInspectionOnly / NotFlashReady**. Existing
generic ChecksumEngine, experimental profile, production PatchEngine, M1c lineage,
D0 save and the two unresolved word-ADD permissions retain their prior semantics.

## Actual procedure and entry contract

The community lead near `2BAD` is a conditional branch in the failure path,
not the routine entry, a checksum-storage offset or proof of an algorithm.
The existing private listing and unchanged baseline establish this narrower flow:

- The checksum fragment is inline in the periodic `VCAL 3` path. Vector `002E`
  selects `28AE`; the `009E` countdown and subtraction by five at `299E..29AD`
  select the periodic work. Main-loop callers invoke this service at several
  sites; no fixed physical period is inferred from software instruction counts.
- Entry `2B70` clears X2 and loads the saved word block index at DATA `0396`.
  Actual MUL by 64 supplies X1, and DP is initialized to 32. The saved byte
  accumulator is at DATA `0398`.
- Each invocation executes 32 **word** LC program-memory reads, even though DD
  is zero. AL and AH are added modulo 256, then added to the saved byte sum.
  X1 increments twice. JRNZ decrements/tests DPL, not the whole word DP.
- After each 64-byte block, the sum is saved and the word block index increments.
  Values below 512 exit before `2BB6` with an incomplete running state.
- After block 512, the code clears the index and tests the actual r0 residue.
  Zero takes the ordinary exit. Nonzero clears the saved accumulator and reads
  program byte `60FB`: nonzero suppresses the failure path; zero writes software
  status DATA `00F5=48` and jumps to `24E9`. The seeded task stops there, before
  the later failure handler and BRK; it does not execute a reset or ECU recovery.

The actual baseline has the gate enabled. The published bypass is not applied.
Recognizing the examined fragment is evidence for this software contract, not
proof that every byte in an archive is a factory original or every whole-program
entry path is reachable.

| Contract field | Established scope |
|---|---|
| Operation | Unsigned byte addition modulo 256; no carry-in between additions |
| Initial state | Block index 0, accumulated byte 0; not a precomputed expected result |
| Initialization evidence | Startup word clear covers `0356..047F`, including `0396..0399`; status F5 is cleared at `28A8` |
| Coverage | `[0000,8000)`, every byte, ascending; 512 blocks of 64 bytes |
| Program read order | Word starts `0000,0002,...,7FFE`, low byte then high byte |
| Final comparison | Fixed residue 0; no additional transformation |
| Exclusions / stored checksum | None established / no separate field established |
| Native gate | Program `60FB`, also included in the summation; not checksum storage |
| Entry / exits | `2B70` / ordinary before `2BB6`; failure before `24E9` |
| CPU context | LRB `0041` (r0 at DATA `0208`), SCB0, USP `0180`, SSP `047E`, entry PSW `0100`; interrupts/peripherals frozen |
| Stateful execution | Same CPU/RAM retained between invocations; only PC stages back to the inline entry |

The startup and omitted scheduler are **not executed**. Their documented initial
state is supplied once, not reset after every chunk. Completion requires the
entire stateful sequence and exact read coverage; merely reaching an ordinary
exit is not a full checksum pass. Bounded static writer/recovery analysis does
not establish arbitrary corrupted RAM, asynchronous interrupt or peripheral behavior.

## Independent arithmetic, interpreter and evidence

The separate C# verifier uses explicit integer arithmetic and returns the computed
byte, fixed residue decision, ranges and per-block state. It does not call Rust
to obtain expected values. The existing generic checksum definition cannot express
this stateful, fixed-residue contract without suggesting storage, so M1f adds a
small separate research model; old profile/report semantics are not reinterpreted.

Rust decodes and executes the supplied unchanged BIN bytes. There is no injected
RET, NOP, jump, instrumentation or host checksum substitute. The new task has
exact instruction-form admission, separate code/data ranges, bounded instruction
and invocation counts, program-read accounting and state checkpoints. Unknown
forms stop before execution. No M1d/M1e ADD permission is accepted for checksum.

The existing [OKI instruction manual](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/Oki_66201_Instruction_Manual.pdf)
was visually checked for the newly needed forms: byte ADDB A,direct byte and
ADDB r0,A (printed3-16/17), indexed word CMP with separate displacement/immediate
(3-38), indexed word INC (3-60), LC/LCB program reads (3-72/74), indexed MOV to
er0/r0 (3-83/99), and word MUL (3-100). MUL and LC under DD0 passed decoded
tests unchanged. Three decoded tests first failed on HC after correct data/CF/ZF
checks: the two exact byte-ADD forms and indexed-X2 word INC. Only those HC
effects were corrected; the unrelated unresolved word ADD forms remain gated.
Source locators and full exact-form admission are recorded with the Rust runner.

Agreement verifies this interpreter against an independently expressed contract,
not the physical OKI processor. The selected executable remains analyst-controlled
software, not an authenticated hardware oracle.

## Result meanings and interfaces

The report keeps arithmetic, code assessment and actual execution separate:

- Valid / Invalid apply only to the recognized, enabled checksum contract.
- Unsupported revision or unrecognized code cannot acquire an algorithm through
  ROM size, profile acknowledgement or a newly fabricated research binding.
- Disabled or altered code/gate is explicit and never promoted to Valid.
- Unresolved/conditional execution, errors, budget exhaustion and NotRun are
  distinct. A conditional observation never becomes unconditional Valid.
- Without a runner, available scoped arithmetic remains visible beside execution
  NotRun. A process exit of zero is not a checksum decision.

```shell
hondaecu research p28-vtec checksum-check private/oracle/p28-304/base.bin --profile p28-304 --confirm-profile --baseline-binding private/reports/m1b/baseline-binding.json --runner rust/p28-slice-runner/target/release/p28-slice-runner --output private/reports/m1f/checksum.json
```

On Windows use the runner's `.exe` suffix. The optional existing child requires
all three `--derived`, `--plan`, `--patch-report` arguments and unchanged M1c
verification. No child baseline binding or patch chain is created. Output is a
new private report, never an input or existing file. Placement under `p28-vtec`
is CLI compatibility only: this is ROM integrity checking, not a VTEC test.

The existing Desktop checks tab adds **«Перевірити штатну checksum»**. It displays
C# result, execution decision, complete/incomplete state, coverage, evidence,
assumptions, reasons and NotFlashReady separately. Match means C# and execution
agree; an Invalid checksum can therefore have a successful Match comparison.
Demo cannot present an invented checksum as native Honda evidence. Checksum
always runs strict and does not inherit the advanced M1d/M1e ADD checkboxes.
Cancellation and file/profile/binding/lineage/session freshness guards apply.

No checksum action saves, repairs, compensates or disables anything. Existing
M1c/D0 save continues to record its legacy checksum Unknown; a separate research
report does not silently change a reviewed plan or authorize repair during save.

## Verification record

The private original baseline and existing verified M1c child were actually run
with three scratch patterns (00/55/AA), with identical per-image outcomes:

| Image | Scoped checksum | Strict comparisons | Calls per run | Instructions per run | Program-data byte reads |
|---|---|---:|---:|---:|---:|
| Original baseline | Valid: zero residue | 3 | 512 | 104963 | 32768 |
| Existing M1c child | Invalid: nonzero residue | 3 | 512 | 104968 | 32769 |

The child's extra read is the control byte, not expanded summation coverage.
Both images' 512 block states and exact read streams match independent C#
calculations. Zero counter/saved-sum at the final stop is not used as a fake
zero residue: the child resets these too, while its observed r0 is nonzero.
There are **6 strict matches, 0 conditional, 0 unresolved, 0 mismatch, 0 execution
error, 0 budget exhaustion**. Invalid means a native residue failure, not a
C#/Rust discrepancy. No assumption that the baseline must pass was used.

Twelve additional images existed only as in-memory copies, each run with all
three scratch patterns: **36 strict matches** and no conditional/unresolved/
mismatch/error/budget outcomes. Five single-byte controls covered both bytes of
a known data word, the last threshold byte and both final covered bytes. Three
pair controls exercised byte-add carry/wrap, two maximum bytes and two zero
bytes. Three deterministic eight-byte controls also produced nonzero residues.
An equal-and-opposite two-byte control retained zero residue, as the recovered
sum8 operation predicts. It is a collision test, not repair or a selectable
compensation byte. Every actual control retained checksum code, gate and entry
state unchanged; none was saved as a BIN.

The first physical coverage byte is a reset vector, so it was observed in actual
LC coverage but **not mutated** in the real input controls. Synthetic tests cover
the true first/last boundaries. The last word is classified as data after the
reachable helper's final jump; this does not make it globally unused or a repair
target. There are no established excluded regions or stored-value fields to
mutate; such tests are not invented.

Private Desktop-service integration also opened/bound the real parent, compared
arithmetic without a runner, ran the actual parent, opened the original M1c
lineage, ran both images and verified original inputs unchanged. These are
service/process tests, not real-file GUI interaction.

Public tests use only invented data/programs, never a reconstruction of the
70-byte native fragment. The production structural guard describes its named
ISA forms, operands and branch targets plus sparse initialization/dispatch
anchors; it is not a public ROM identity database or global reachability proof.
Missing private material is explicit not-run, never pass. Real reports,
identities, traces and in-memory control observations remain ignored. No new
OEM-derived BIN is written in this stage, and the M1c child is not modified.

GUI interaction is separate from builds, ViewModel tests and portable no-window
startup checks. A stopped GUI test pauses that test; it is not retried without
permission and is not counted as passed. Independent checks can continue.

Local final verification: 276 Core, 39 CLI, 50 Windows/Desktop and 62 pinned
Rust release tests passed, including actual synthetic Rust subprocess tests.
Both solutions build; .NET formatting, Rust formatting and diff checks pass.
The 24 new Core, 7 CLI and 11 Desktop cases cover the new read-only path;
public fixtures do not embed the native checksum fragment.

Four actual legacy M1d/M1e batches on runner 0.3.0 retain their prior aggregate
counts and exact derived changed-case sets, with zero mismatch, execution error
or budget exhaustion. M1d strict compact evaluation has 372120 matches and
21096 unresolved; its conditional run converts only those 21096 to conditional
observations. Both threshold batches retain 12288 matches per image. M1e strict
G has 98 matches and 133880 unresolved, with downstream not-run preserved;
conditional G, G-to-F and each threshold evaluation have 98 strict and 133880
conditional observations. The earlier er1/er3 permissions are neither removed
nor widened by checksum work. Legacy checksum Unknown remains unchanged.

Preservation checks cover the original ROM, baseline, profile, binding, existing
M1c child/plan/report and listing, plus all 499 files in the prior D0 portable
folder. The M1f portable is published separately under
`artifacts/desktop/win-x64-m1f`; the complete folder is required. Its resource
check is a no-window diagnostic, not a substitute for interactive GUI evidence.
The existing CI publishes only clean application/runtime/resources/licenses,
without private ROMs, reports or traces.

D0 is already an implemented research Windows UI, but neither D0 nor this stage
completes M3 or M1. Physical RPM, independently controlled editor observations,
physical ECU behavior and flash readiness are still outside the established scope.
