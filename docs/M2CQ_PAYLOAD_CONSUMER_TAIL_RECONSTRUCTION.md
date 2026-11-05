# M2cq — Payload consumer, pre-RTI tail і формальні return obligations

Новий research-only пакет `research/p28-word0196/payload_consumer_tail/` визначає
п'ять evaluated pure operations: `payload_consumer`, `post_checksum_tail`,
`parser_step_with_tail`, `last_writer_at_conditional_boundary` та
`rti_obligations`. Окремий `consumer_search` фіксує закритий source inventory
та CFG qualifications; це не runtime пошук або новий ROM decoder.

Встановлений локальний consumer читає DATA03F4, додає code-owned immediate3
modulo256 і записує результат у DATA03F2. Це не доводить, що саме writer026C
сформував прочитане значення: його reaching definition залишається
**ConditionalCandidate**. Окремий tail копіює software F8 word у IE після
MIE clear і зупиняється перед RTI029C. RTI представлено формальними obligations,
без CPU stack execution.

Для всіх outputs: `EXECUTION_BLOCKED`, `FirmwareReady=false`,
actualHardwareObservation=null і cpuInstructionRetirements=0. Source PC,
logical ordinals, pointer dependencies та hypothetical frame reads не є
фактичними instruction retirements або hardware observations.

## 1. Прийнята база

База — M2cp `a6f765ee2a3ac180d1a4c9687238db5aa923956c`. Його прийняті результати:
82 static tests, 2017 canonical records, 75842754 bytes і повний
expected/local/Ubuntu/Windows збіг. Це історичний результат M2cp, а не QA M2cq.

M2cn/M2co/M2cp разом надали19 pure functions. Їхні implementations, contracts,
reference oracles, expected streams та source fingerprints збережено. Новий
пакет використовує frozen adapters; старий parser не переписується для
розширення scope або нової snapshot representation.

## 2. Source inventory і межа пошуку

Source audit повторно використовує збережений listing, 11499 decoded extents,
прийняті banking/alias contracts і primary manufacturer instruction semantics.
Жодного нового ROM read/decode або execution немає. Private source receipts
містять exact SHA-256 locators і вузькі before/after fences; OEM bytes та
документи не публікуються.

Bounded search знайшов155 r4/er2 source rows,16 zero-page F4/F5 operand rows,
три off-page F4/F5 rows,16 nearby03F0..03FF pointer seeds і один явний DP03F4
seed. Серед155 local rows тільки026C має listing bank annotation03F0; annotation
не є actual LRB observation. Zero-page00F4 не тотожний DATA03F4.

Розширена bracket-syntax перевірка містить710 rows. Початкові698 охоплюють
DP/USP/X1/X2 syntax, ще12 — N16[N8] forms. Останні12 є LC/LCB **PROGRAM table
loads**, а не прямими DATA03F4 reads. Ці числа рахують source candidates,
не actual consumers, accesses або executions. Невстановлені pointer values,
bank/page contexts і addressing effects не замінюються припущеннями.

Класифікація розрізняє:

- підтверджений локальний source operand DATA03F4 на28DB;
- conditional026C producer candidate, чия конкретна generation не доведена;
- unresolved indirect/word candidates та можливі intervening writers;
- відсутність глобального доказу, що інших consumers немає.

## 3. Встановлений local consumer і downstream CFG

Закритий body має шість source sites:

| PC | Reviewed operation | Ефект |
|---|---|---|
| 28D8 | MOV DP,#03F4 | Word write selected DP-bank storage |
| 28DB | LB A,[DP] | DP dependency, byte DATA03F4→AL, DD0 |
| 28DC | ADDB A,#3 | AL=(G+3) modulo256; CF/ZF/HC |
| 28DE | J297C | Source control transfer без stack write |
| 297C | MOV DP,#03F2 | Другий word write того самого DP slot |
| 297F | STB A,[DP] | Byte AL→DATA03F2 |

Межа — **stop before2980**. Подальші status/counter changes, STBUF write і
інший restore block не застосовуються. Зокрема later2997 читає FA, що є іншою
source history, ніж F8 restore0295. Збіг префікса адрес29xx не є CFG edge між
consumer і checksum tail.

Direct entry28D8 не доводить весь foreground path. Відомі upstream gates
28AE..28BD і28C2..28D7 мають власні inputs/word-copy effects; їх не додають
мовчки до шести-site body. Source annotation LRB0041 не встановлює actual
entry owner. У direct consumer немає page/local operand, який вимагав би
LRB007E: full DATA addresses задаються через DP.

Високорівнева transformation:

```text
require known SCB and conditional context
DP = 03F4
G = read_byte(DATA[DP])                 // ordinary-byte premise checked here
AL = G; DD = 0
AL = (G + 3) modulo256
CF = G+3 >255
ZF = AL==0
HC = (G &0F)+3 >0F
source jump to297C
DP = 03F2
write_byte(DATA[DP], AL)
stop before2980
```

Immediate3 є code-owned operand, не DATA read і не доведений physical command
meaning. AH, MIE, OtherPSW, LRB/SCB/USP/SSP retained; AL/CF/ZF/HC змінюються
за byte arithmetic, DD0. Для partial G модель розглядає сумісні byte values
(щонайбільше256) і повертає exact consensus values/bits/flags, без floating
point або default-zero. Наприклад G=FD дає AL00/CF1/ZF1/HC1; G=FF дає
AL02/CF1/ZF0/HC1. Це source equations, не виконані test results.

## 4. DP banks, aliases і ordered effects

SCB повинен бути відомим0..7 до першого DP write. Selected physical alias у
conditional DATA map:

```text
DP low byte  = 0084 +8*SCB
DP high byte = 0085 +8*SCB
```

Body має **три ordered writes**, а не один final assignment:
28D8 DP=03F4 →297C DP=03F2 →297F DATA03F2=AL. Обидва DP writes є word16;
297F залишається byte8 і не перезаписує DATA03F3. Pointer-before/after values,
bits і generations походять із тих самих DATA bytes, а не з незалежної копії
покажчика.

SCB6 aliases DP до00B4/00B5. Це включає00B4, який уже присутній у frozen state
і має інші source roles у mode analysis. Його previous bits/generation повинні
бути коректно замінені DP word stores. Не можна зберігати старий00B4.0 поруч
із новим whole pointer byte або приховувати цю alias effect.

28DB і297F мають explicit `ARCHITECTURAL_ADDRESS_DEPENDENCY` reads з роллю
`PointingRegisterAlias`; тільки28DB має functional byte DATA read. Store-before
value для journal — bookkeeping, не вигаданий functional read destination.
`pointerState` та `afterPointerState` — derived views, а не додаткові memory
accesses. SCB unknown відхиляється до effects; невстановлена ordinary-byte
premise на28DB зберігає вже виконаний умовний DP write28D8.

## 5. DATA03F4 writers і reaching definitions

Reviewed026C при LRB007E/DD0 пише AL у DATA03F4. Наступний Generic store
перезаписує той самий slot, з новим logical writer навіть за однакового value.
DATA03F3 — окремий Flag byte, а DATA03F6 — accumulator; вони не підміняють G.
Після consumer результат записується у03F2, що при LRB007E також є local r2.
Цей alias не доводить нову protocol Length semantics або native parser handoff.

Окремий Flag consumer2914/2917/2918/2919 працює з03F3 і його shift/carry
predicate. Він не є DATA03F4 consumer лише через подібну адресу або parity
міркування. У новому шести-site G+3 body немає такого Flag predicate.

Інші source candidates залишаються обмеженими:

- 02B7 word L A,[DP] може охоплювати03F4/03F5 лише за доведеного pointer value;
  його source/reachability не встановлено цим body;
- 2710 boot clear-loop writer може торкатися03F4 за відповідного DP/loop
  admission; нового boot execution proof немає;
- CAL2689/5C5C indirect writer scope має окремі невстановлені pointer table,
  generation та callee requirements.

Підтверджений local read28DB не є `Confirmed026CConsumer`: потрібні конкретна
retained026C generation, повний relevant writer set, no-interference, context
transitions, matching frame/foreground path і відсутність наступного packet
або indirect overwrite. Ці native edges не отримуються з рівності адрес.

## 6. Умовний last-writer timeline

`last_writer_at_conditional_boundary` приймає explicit initial value/generation,
1..32 declared events, noInterference і claim. Тільки `ConditionalOnly`
допускається; `Confirmed026CConsumer`, `PayloadArray`, `Fifo` та
`ActualExecution` відхиляються без застосування events.

Події:

- `GenericStore`: qualified026C effect лише за LRB007E/DD0;
- `AlternateStore`: byte/word declared alias write у03F3..03F6;
- `UnknownWriter`: втрата tracked value/generation через можливий unbound writer;
- `ConsumerBoundary`: logical observation03F4, не actual CPU read.

Word address нормалізується до even. Наприклад word write з адресою03F5
торкається03F4/03F5; byte write03F5 не торкається03F4. Для не-overlap event
tracked byte retained; це не доказ whole-word sameValue. Unknown other bytes
не реконструюються з одного tracked byte.

Кожний non-null writer generation label має бути новим відносно initial label
та всіх попередніх declared stores, включно з non-overlap. Reuse дає
`WriterGenerationReused` **до** offending store; earlier prefix зберігається.
Для GenericStore context guard перевіряється раніше. Null labels можуть
повторюватися, але не встановлюють writer ownership.

Boundary relation перевіряє у source-specified priority: noInterference,
UnknownWriter, missing current generation, requested-generation match і
останній kind GenericStore. Лише після цього можливий
`ConditionalLastWriterAtBoundary`. Known generation з unknown value не
перетворює value на0 і не є native observation.

Синтетичний приклад: два stores того самого20 з labels G1/G2 — два events.
Boundary, що просить G1, є stale; за умовного no-interference G2 може мати
conditional last-writer relation. Це не actual026C→28DB continuity. Після
AlternateStore навіть matching alternate label не стає026C owner; після
UnknownWriter обидва tracked fields unknown. Жодного payload array/FIFO з
такої timeline не виводять.

## 7. Post-checksum tail і його ingress

Точна pre-RTI послідовність:

```text
0295: L A,00F8          // word16, DD=1
0297: ANDB PSWH,#FE     // MIE=0; ZF precedence unknown
029A: ST A,IE           // word16 to001A/001B
stop before029C RTI
```

N8 operands тут zero-page absolute, незалежні від LRB/SCB/USP. Incoming DD може
бути0/1/unknown: L0295 встановлює DD1 перед descriptor-sensitive word store.
Tail не примушує LRB007E. F8 є software shadow00F8/00F9 з explicit nullable
values/bits/generation labels; це не встановлений поточний hardware IE owner.

Ingress source-qualified окремо:

| Prefix result | Перевірений edge | Qualification |
|---|---|---|
| ChecksumAccepted | 0290 SB ready→0293 CLRB r7→0295 | Fall-through після completed accepted prefix |
| ChecksumRejected | 0287/028E→0270 r7=2→0272 J0295 | Rejection також досягає tail за reviewed jump |
| Header/Length/Flag/Generic completed | stop0272, потім J0272→0295 | Новий explicit edge; old M2cp stop не переписано |
| Outside0227 | Інша послідовність0244/0246/0249/024B | Не примушується до0295 |
| Mode-zero021F | target029D; окремий downstream path | Не є straight0295/RTI path |
| Indeterminate branch | Збережений prefix | Downstream edge не вгадується |

`parser_step_with_tail` проектує snapshot до frozen parser, зберігає exact
prefix events і додає тільки reviewed J0272→0295 за completed boundary0272;
completed0295 входить у tail напряму. Outside/unknown propagates без tail.
Новий source step є математичним CFG witness, а не host PC injection або
retired J. Adapter ніколи не викликає нового consumer як уявне continuation.

## 8. F8, MIE, IE і PSWH/ZF

L0295 один раз читає word00F8/00F9: low byte→AL, high→AH, DD1, ZF за word
knowledge, CF/HC retained. Known1 bit будь-де доводить nonzero/ZF0; усі16
known0 bits — ZF1; інакше ZF unknown. Partial bits переносяться в derived
AL/AH knowledge і далі в IE store без вигаданих нулів.

ANDB0297 є **whole-byte PSWH destination**, не RB bit instruction. Primary
ANDB page допускає PSWH і позначає ZF affected, але не задає precedence між
destination-byte write і flag update в цьому самому byte. Тому MIE0 встановлено,
CF/HC/DD/OtherPSW retained, AL/AH retained, а **ZF після0297 завжди unknown**
у цьому scope. Навіть математично nonzero PSWH&FE не усуває self-alias gap.
Emulator output не використовується як primary ISA oracle.

ST029A створює один word write IE001A/001B, зберігає A та flags/DD. Functional
read IE destination не додається. Є два ordered write events у tail: REGISTER
PSWH mask і DATA IE word store. Same-value IE store залишається окремою
generation. Missing F8/F9 generation додає `F8GenerationNotEstablished`, без
fabricated native owner і без default-zero data.

Tail зберігає abstract parser bytes03F0..03F7 та SSP, але не доводить physical
alias/frame safety. A після tail є F8-derived word, а не майбутній restored
foreground A. MIE clear і IE write — source software effects; exact interrupt
delivery, IE polarity applicability, pending factors, NMI та peripheral state
залишаються окремими невстановленими умовами.

## 9. RTI: formal order, а не виконаний return

Первинний RTI contract задає increment-first word order. Нехай T — numeric SSP
**перед RTI**, а S — SSP перед matching interrupt entry:

| Word ordinal | Numeric SSP after increment | Effective DATA word address | Restored role |
|---:|---|---|---|
| 1 | (T+2) modulo65536 | even16(T+2) | PSW |
| 2 | (T+4) modulo65536 | even16(T+4) | LRB |
| 3 | (T+6) modulo65536 | even16(T+6) | A |
| 4 | (T+8) modulo65536 | even16(T+8) | PC |

Для matching entry frame T=(S−8) modulo65536; saved PC/A/LRB/PSW лежать у
even16(S), even16(S−2), even16(S−4), even16(S−6). Усі чотири reads мають width16
незалежно від incoming або вже restored DD. Numeric SSP сам не округлюється;
even normalization стосується тільки effective address. Word byte layout
little-endian не встановлює physical byte-bus subcycle order.

`rti_obligations` **не читає stack** і не змінює snapshot/CPU registers. Воно
повертає `obligationReads` з kind=`Obligation_NotPerformedRead`, `reads=[]`,
`journal=[]` і `hypotheticalRestores`. Saved PC тут — явно заданий conditional/
synthetic frameWords.pc value: його може обрати synthetic fixture, але це не
доведений native foreground PC або адреса029C. API не приймає окремий бажаний
host return-PC field.
Unknown SSP/words/generations лишаються unknown, без історичного technical seed.

Query містить чотири nullable frame words/generations і окремі declared
premises: mappingQualified, readable, entryWritable, frameOwnerEstablished,
integrity, noControlAlias, nestingExcluded, nmiExcluded та matchingEntrySsp.
Вони позначають hypothetical conjunctions; навіть усіtrue не є actual frame
ownership, physical safety або return observation.

Return classifications розрізняють executionClaim refusal, S/T mismatch,
declared false premise, missing obligations та complete hypothetical
specification. За executionClaim=true усі hypothetical restores null і
obligationReads порожні. За інших failures можлива hypothetical geometry,
але вона не застосовується до CPU state.

RTI відновлює PSW/LRB/A/PC, **не IE**, не попередні pointing-register RAM bytes
і не rollback parser RAM. SCB зі saved PSW лише обирає bank. RTI page не має
окремого SF assignment; звичайний RT SF0 не переноситься на RTI. Невідомі
physical SF, real SSP/frame creator, saved foreground PC, memory mapping і
all-alias retention залишаються blocker categories. MIE0/IE0 не виключають NMI.

## 10. Typed state, partial bits і representation

Snapshot зберігає frozen six keys і12 named registers. DATA scope розширено
з31 до46 bytes: додано відсутні DP-bank bytes;00B4 уже існував. Memory і
generation maps вимагають усі46 keys. KnownBits допускає будь-який їхній bit,
узгоджений з whole byte. bool не стає byte/word integer; unknown не стає0.

Raw memory None з8 known bits **залишається raw None до source store**.
Load/arithmetic може вивести unique logical AL/AH value; це knowledge refinement,
не RAM write. Reads і journal.before values показують raw nullable memory;
explicit knownBits зберігаються окремо. SameValue використовує whole raw values
і може залишатисяNone навіть за більшій bit knowledge.

Whole-known store прибирає redundant target knownBits. Partial store замінює
target bits рівно proven output bits; unrelated knowledge retained. Новий
`state.registerKnownBits` має AL.n/AH.n, а pointer views — DP.n. У pointer
dependency read bits використовуються physical DATA keys, не DP.n aliases.

Frozen parser adapter свідомо вузький: unsupported partial bits на original31
bytes, крім F8/F9, дають `UnsupportedPartialParserKnowledge` до prefix.
Не можна мовчки викинути корисну knowledge або відновити stale bits після
store. Unused15 DP extras і F8 partial bits зберігаються при projection/expansion.
Inherited reads отримують generations відповідного source моменту, не final
generation, підставлену заднім числом.

## 11. Формальні контракти п'яти operations

| Operation | Inputs/preconditions | Transformation і frame conditions | Stop boundary |
|---|---|---|---|
| payload_consumer | Extended snapshot; known SCB; noInterference; byte premise на28DB | DP03F4, byte G+3, DP03F2, byte store; unrelated DATA/registers retained | 2980 або reached prefix |
| post_checksum_tail | Extended snapshot; noInterference; no bank gate | F8 word load, PSWH mask, IE word store; SSP retained | Before029C |
| parser_step_with_tail | Extended snapshot; compatible frozen partial knowledge | Exact frozen parser prefix і тільки reviewed tail ingress | 029C або inherited outside/unknown |
| last_writer_at_conditional_boundary | Explicit typed timeline/claim/lineage premises | One tracked slot і ordered declared events; no actual consumer read | First context/label refusal або logical boundaries |
| rti_obligations | Optional pre-RTI SSP, four frame words/labels, explicit premises | Hypothetical word-read geometry/restores only; no state pop | Formal029C |

Local outputs включають sourceScope, full state, reads/journal/steps,
intermediateStates, pointerState, unresolvedConstraints і optional
rtiObligations. Timeline sourceScope=[026C,28DB] є declared writer/read identity,
а не actual trace. Formal RTI output має sourceScope=[029C]. Invalid shapes
дають ValueError; source/premise refusals — typed status/reason з prefix.

Local equivalence, conditional writer timeline і actual ECU equivalence не
ототожнюються. Новий model-completeness status не встановлює native026C owner,
frame safety або foreground-to-consumer continuation.

## 12. Evidence-driven data-flow graph

```text
Declared026C Generic store → DATA03F4 last slot
    -- explicit conditional lineage/no-interference only --> local28DB read
    → +3 → DATA03F2 at297F → stop2980

Completed parser prefix → 0295 directly or via reviewed J0272
    → F8 word → MIE0 / ZFunknown → IE word → stop029C
    -- formal matching-frame obligations only --> saved foreground context
```

Немає підтвердженого native edge між цими двома chains. RTI obligations не
доводять подальший foreground read03F4; last-slot timeline не доводить IRQ
return або opcode execution. Consumer input generation, future foreground
path і intervening writers потрібно встановлювати окремо.

## 13. Independent oracle, tests і canonical publication

Незалежний reference oracle формує expected без new semantic model calls.
Corpus/domain counts визначаються independent freeze; цей документ не
підставляє число попереднього milestone і не оголошує майбутній PASS.
Scope включає consumer byte/partial-bit arithmetic, усі SCB aliases,
unknown/malformed/context refusals, multiple/same-value writers, alternate
word overlap, stale/reused/missing generations, tail F8/PSWH partial state,
parser ingress/early exits і formal RTI unsafe/missing-premise controls.

Потрібні окремі source-to-model і full expected-output comparisons. Test PASS
сам по собі не встановлює Confirmed026CConsumer або actual return. Root
implementation, independent expected source та all historical expected
streams мають окремі identities; expectations не підганяють за model output.

Canonical record — exact `{caseId,operation,input,output}`. Sorted-key compact
ASCII JSON, no NaN, LF і повний output: unknown, sourceScope, partial bits,
all journals/reads, formal obligations, generations, boundaries і constraints.
Жодних field exclusions або projections для отримання equality.

Validator публікує рівно `static-canonical.jsonl.gz`, `static-summary.json`,
`sourcejoin.json`; gzip mtime0, bounded size128MiB, source fence до/після
calculation/publication. Summary рахує тільки operation/status records і
source identities. Воно не змішує heterogeneous timeline reads, architectural
pointer dependencies або obligationReads з actual DATA/CPU activity. CLI не
сертифікує незалежний comparison або delivery.

Research-only CI overlay має16 new paths і1334 source bindings;1317 inherited
sources і historical workflow tail74904 bytes retained. Exact reviewed new
fingerprint потрібен для static lane; unknown/runtime/inherited/unapproved
change зберігає full-QA fallback. Output-overwrite controls використовують
isolated TemporaryDirectory, а malformed-source fixture — реально включений
consumer_model.py із membership assertion. Ambient private folders не є
передумовою clean CI.

Expected/local/Ubuntu/Windows порівнюються повністю decompressed byte-for-byte,
не тільки hashes. Exact final SHA, actual tests/jobs/steps, canonical sizes,
firstMismatch та completed verdict встановлюють delivery receipts і фінальний
український звіт. Historical17/Desktop є NotRun, якщо їх не запускали.

## 14. Preservation, C++/Rust readiness і remaining scope

П'ять existing preservation exceptions зберігають окремі категорії:3 inherited,
1 prior M2cn Python і1 prior M2cp Python. Нових exceptions цей scope не створює;
new unauthorized differences визначає actual scoped audit.
StrictHistoricalPreservationPass не підвищується доtrue. Production CPU/Bus/
decoder/Exec, runtime admission, ROM, firmware tools і GUI не змінюються.

Port може використовувати Option<u8>/optional byte, exact byte masks, nullable
words/generation labels, enum status/reason і ordered effect records. Для+3
використовуйте wider unsigned intermediate перед modulo8. Partial arithmetic
має повертати consensus над compatible inputs, а не approximate число.
DP має походити з unified bank DATA storage; independent pointer shadow
зламає SCB6 alias. Raw nullable values і inferred register bits залишайте
окремими, щоб knowledge refinement не виглядала store.

Реалізуйте local consumer і pre-RTI tail звичайними bounded functions. Формальні
RTI effects повертайте як typed obligations, без interpreter stack pop.
Writer timeline — окремий conditional analysis; воно не підміняє machine trace.
Зберігайте explicit stops2980/029C, event ordering, same-value generations,
unsafe-claim refusals і source-specific unresolved fields.

Remaining unknowns: actual silicon/memory/peripheral applicability, native026C
reaching generation, safe matching frame/SSP, actual saved foreground PC,
PSWH/ZF self-destination order, SF, IE polarity applicability, NMI/IRQ history,
foreground continuation і hardware equivalence. Доцільний наступний bounded
scope — source-qualified2980 continuation або upstream foreground reach28AE
з явними context/writer obligations. Це рекомендація M2cr, а не його запуск.
Runtime/ROM/IRQ/RTI/hardware/GUI і firmware залишаються заблокованими.
