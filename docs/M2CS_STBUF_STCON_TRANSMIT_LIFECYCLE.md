# M2cs — STBUF/STCON: програмна конфігурація та документальні TX obligations

## 1. Прийнята база M2cr

База — `312a0b48542330a782c71d517d07f23480caf158`, прийнятий M2cr
`CONDITIONAL_POST_CONSUMER_CONTINUATION_EQUIVALENCE_ESTABLISHED / EXECUTION_BLOCKED`.
Новий пакет `research/p28-word0196/stbuf_stcon_transmit_source/` додає п'ять
чистих інтерфейсів. Прийняті пакети M2cn–M2cr залишаються незмінними.

Цей документ описує встановлені джерела, реалізовані перетворення й межі
доказів. Фактичні результати нового QA, exact-SHA CI, canonical comparison та
delivery seal фіксуються окремими завершеними receipts і фінальним звітом.
Наведений нижче опис сам собою не засвідчує проходження цих gates.

## 2. Точна програмна межа STBUF2995

M2cr реконструює десять сайтів `2980..2994`: установлює `DATA0356.6`, записує
`DATA03F5=2`, обчислює `AL=DATA03F1 & 1F`, записує його в `DATA03F6` і залишає
`DP=03F6`, `DD=0`. CF/HC зберігаються; невідомий header не стає нулем.

На `2995` перевірено descriptor-sensitive форму `STB A,N8`, `N8=0051`.
DD0 означає byte operand; DD1 означав би іншу word-операцію з вирівнюванням
до `0050/0051`. M2cs не виконує жодної з них. Спільна межа:
`STOP_BEFORE_STBUF_2995`. Власне конфігураційний prefix додатково зупиняється
перед `288E`, щоб не торкатися наступного `DATA4700`.

## 3. Manufacturer SFR inventory

Повні таблиці SFR специфікацій `E2E1027-27-Y4`, сторінка 11/30, та
`J2E1027-27-Y3`, сторінка 11/30, узгоджуються щодо наведених регістрів.
Усі мають ширину 8 біт. Reset — документальна властивість стандартного
сімейства, а не відомий поточний стан конкретного ECU.

| DATA | Регістр | Доступ | Документальний reset | Роль |
|---|---|---|---|---|
| 0048 | STTM | R/W | 00 | Лічильник передавального BRG |
| 0049 | STTMR | R/W | 00 | Reload передавального BRG |
| 004A | STTMC | R/W | 0C | Керування передавальним/спільним BRG |
| 004C | SRTM | R/W | 00 | Лічильник приймального BRG |
| 004D | SRTMR | R/W | 00 | Reload приймального BRG |
| 004E | SRTMC | R/W | 0E | Керування приймальним BRG |
| 0050 | STCON | R/W | 80 | Режим передавання |
| 0051 | STBUF | W | Undefined | Передавальний буфер |
| 0054 | SRCON | R/W | 00 | Режим приймання |
| 0055 | SRBUF | R | Undefined | Приймальний буфер |
| 0056 | SRSTAT | R/W | F0 | Приймальні помилки |

Ці відомості зберігаються в `REGISTER_INVENTORY`; функція
`documentary_rules()` повертає глибоку копію каталогів.

## 4. Перевірені й невстановлені поля STCON

Інтактний текст User Manual, printed124 та printed131, установлює частину
полів. Повна allocation table на printed123 пошкоджена; її видимі фрагменти
не використовуються як semantic authority.

| Поле STCON | Підтверджена документальна залежність |
|---|---|
| bit0 | 0 — normal, 1 — multiprocessor |
| bit1 | 0 — UART, 1 — synchronous |
| bits3:2, normal | Код довжини; відповідність конкретній кількості бітів невідома |
| bit2, multiprocessor | 0 — data, 1 — address |
| bit3, multiprocessor | Ігнорується |
| bit4, UART | Код stop length; точне кодування невідоме |
| bit4, synchronous | 0 — slave, 1 — master |
| bit5 | Вибір наявності parity; точна полярність presence тут не встановлена |
| bit6 | Вибір odd/even із невідомою полярністю; ігнорується за bit5=0 |
| bit7 | Значення невідоме; reset80 не доводить TX enable або STFREE |

Точне кодування SRCON з intact126/127 не переноситься на STCON. Обмеження
зміни TX mode під час активного передавання також залишаються невстановленими.

## 5. Inventory програмних сайтів

Новий `source_inventory.inventory()` містить 31 reviewed static site:
16 конфігураційних та 15 сайтів умовної перевірки readback. Разом із
прийнятим M2cr inventory із 60 сайтів це 91 позиція. Inventory містить
PC, форму, довжину, successors, первинну сторінку ISA й evidence class,
без ROM byte stream або приватного listing.

Конфігурація:
`286D,286F,2871,2873,2876,2878,287A,287C,287E,2880,2882,2884,2888,2889,288B,288C`.

Reader:
`3FD4,3FD7,3FD9,3FDB,3FDD,3FDF,3FE1,3FE3,3FE5,3FE7,3FE9,3FEB,3FEF,3FF1,3FF5`.

ISA правила перевірено за повними сторінками: MOVB rN — 3-99, MOVB obj —
3-96, LB — 3-70, MOV DP — 3-86, MB C,bit — 3-77, умовні переходи — 3-66,
STB — 3-155, ANDB — 3-24, CMPB A — 3-39, CMPB obj — 3-42.

## 6. Direct writer та непрямі candidates

`2889 STB A,N8(50)` — підтверджений direct byte write **intent** STCON за
DD0, установленого до цього LB. Його source operand походить із r0 через
`2888 LB A,r0`. У тому самому prefix є intents STTM, STTMR, STTMC та SRCON.

Статичний пошук відрізняє direct reference від можливого word overlap та
непрямого pointer access. Сам текстовий збіг або назва символу не доводять
effective address, DD, виконання чи reaching generation. Непідтверджений
непрямий writer залишається `ConditionalCandidate`.

Для входу `DATA0356.1` знайдено вузький source candidate: після `60D2 DP=0356`
сайт `60D5 MB [DP].1,C` копіює CF. Походження цього CF і його актуальна
generation тут не закриті. Записи інших бітів `0356` не є власниками bit1.

## 7. Дві умовні configuration histories

Вхідний supported context — точний `LRB=0041`, тобто local bank `0208..020F`.
Модель записує r0/r1 як DATA0208/0209. Первинний LRB — 13-бітний; довільні
ненульові старші біти не оголошуються фізично представними через mask.

| Частина | Спільна або умовна дія |
|---|---|
| 286D/286F | r0=1C, r1=8C |
| 2871 | AL=DF, DD0, ZF0 |
| 2873 | DP=0356 у selected pointing-register RAM bank |
| 2876/2878 | CF=old DATA0356.1; JLT бере гілку за CF1 |
| 287A/287C/287E, лише bit1=0 | r0=31, r1=A1, AL=FB |
| 2880/2882 | Intents STTM/STTMR із AL |
| 2884 | STTMC intent12 |
| 2888/2889 | r0 → AL → STCON intent |
| 288B/288C | r1 → AL → SRCON intent |

За bit1=1 маємо 13 source steps, 3 DATA writes і 5 SFR intents; кінцевий
AL=8C, CF1. За bit1=0 — 16 steps, 5 DATA writes і 5 intents; AL=A1, CF0.
В обох завершених шляхах DD0/ZF0, AH під ordinary-byte premise та HC/MIE/
OtherPSW зберігаються. Усі counts — властивості software relation, не CPU
retirements або фізичний час.

Невідомий bit1 завершує prefix на `2878` без вибору гілки: збережено
default locals, DP write, read та branch record, але SFR intents ще немає.
Невідомий SCB блокує саме DP write на `2873`, залишаючи ранній prefix.
Відсутня ordinary-byte premise блокує перший LB на `2871` після двох local
writes. Prefix не відкочується й не подається як атомарна конфігурація.

## 8. Writer generations та alias relations

`stcon_writer_lineage(query)` приймає 1..32 явно заявлені події:
`ConfigIntent`, `AlternateIntent`, `UnknownWriter`, `Boundary`. Це умовна
software history, не журнал апаратних записів. ConfigIntent допускає лише
1C для `Bit1Set` або 31 для `Bit1Clear` і DD0.

AlternateIntent описує bounded byte/word alias query; word address
вирівнюється до парної адреси. Наприклад, запит word0051 перекриває0050;
byte0051 не перекриває0050. Такі queries не засвідчують існування відповідних
ROM writers. Після відомого overlap зберігається нова generation, навіть
коли declared byte не змінився. Повторне використання ненульової generation
відхиляється до offending event, включно з non-overlap store.

Boundary окремо перевіряє no-interference, unknown writer, missing generation,
stale requested generation та alternate writer. Лише останній reviewed
ConfigIntent з узгодженою generation дає
`ConditionalConfigurationWriterAtBoundary`. Це не native owner.

## 9. Mode, clock та permission relationships

Intact printed112/113 задають STTMC:

| bits1:0 | Документальний режим |
|---|---|
| 00 | Auto-reload timer |
| 01 | Transmission baud generator |
| 10 або 11 | Transmission/receiving baud generator |

Bit4: 0 stopped, 1 operating. Коди bits7:5 вибирають divisors
`[2,4,8,16,32,128,512,512]`. Bits2/3 не реалізовані й документально читаються
як1. Тому source intent12 означає combined TX/RX BRG, run bit1, clock code0
із divisor2. Він не означає physical readback12 або спостережене running.

Константи prefix: default `48/49=DF,4A=12,50=1C,54=8C`; alternate
`48/49=FB,4A=12,50=31,54=A1`. Рівність declared counter/reload не є
спостереженням їхнього фізичного стану. SRCON bit7 документує receiving
permission; це не доказ TX permission у STCON bit7.

## 10. Документально встановлений TX lifecycle

Каталог `DOCUMENTED_FACTS` містить 17 фактів із printed locators. Основні
TX джерела — intact124/125 та130/131. Документація описує налаштування
mode/baud перед STBUF write, holding buffer, окремий shift register, idle
start, один buffered-next-data випадок і UART normal start/frame sequence.

Це `ManufacturerDocumented` для кваліфікованого standard profile. Каталог
не є transmitter state machine: він не рухає clock, queue, latch, IRQ або TXD.
Сім ситуацій — `IdleWrite`, `BusyWrite`, `Completion`, `ModeChange`,
`Acknowledge`, `Reassertion`, `Collision` — повертають тільки впорядковані
ідентифікатори підтверджених правил і окремих unknown.

## 11. Передумови приймання STBUF write

STBUF0051 документовано як 8-бітний write-only buffer, bit0 передається
першим у вибраній довжині. Printed125 вимагає попереднього налаштування baud
generation та transmission mode. Reset не змінює STBUF contents, тому
невідоме значення не замінюється 0.

Окремий повний TX-enable field, актуальні buffer/shift state, чинний clock,
прийнятність конкретного write та ECU applicability не встановлені.
Тому відомий prospective AL разом із DD0 не означає прийнятий peripheral
write. DD1 або unknown DD також не можуть бути непомітно нормалізовані до DD0.

## 12. Holding buffer та shift register

Printed125 описує дві стадії: STBUF holding buffer та окремий transmission
shift register. Software не може прямо читати чи записувати shift register.
Це не доводить довільну FIFO depth.

Коли попереднього передавання немає, кваліфікований STBUF write запускає
описану послідовність. Для write під час попереднього transfer текст
зберігає стару передачу й описує початок наступних buffered data після її
завершення. Третій write за вже зайнятого holding buffer тут не визначений.
Жоден із цих documentary cases не створює buffer state у моделі M2cs.

## 13. TX READY, frame completion та IRQ allocation

Intact131 описує UART normal: BRG clock ділиться на16 для STCLK; WSTBUF
запускає LSTSF; перенесення у shift register пов'язане з falling edge.
TXREADY синхронізується з M1ST і встановлює IRQ word bit2 **на початку**
описаної передачі. STFREE описано як внутрішній progress signal, без
доведеного DATA address/bit mapping. Після data LSB first і вибраної parity
stop bit завершує frame; окремий TX-complete IRQ не встановлений.

| Джерело | Vector | Word bit | Назви request/enable |
|---|---|---|---|
| TX READY | 000C | 2 | RQSTRDY / IESTRDY |
| TX BRG overflow | 0024 | 14 | RQSTGEN / IESTGEN |
| RX READY | 000A | 1 | Окреме приймальне джерело |

Table17-1 printed166 та instruction-table allocation перевірені незалежно.
TX READY не називається COMPLETE; RX000A не перейменовується на TX.

## 14. ACK та reassertion

Generic interrupt-entry опис документує очищення serviced-factor IRQ у
своєму кваліфікованому scope. Це не доводить, що саме STBUF write очищує
TXREADY, що читання має ACK effect, або що request знову встановлюється без
нових eligible data/start conditions. STBUF write-only не отримує fake readback.

Printed165/168/169 використовують set1 enable/gating, а printed167 містить
суперечливу IE0 entry condition. `iePolarityResolution=null`; жодна
гіпотеза не перетворюється на фактичний IE polarity невідомого ECU.

## 15. Set/clear collisions та зміни під час TX

TX-specific hardware-set/software-clear priority не встановлена. Також
невідомий результат нового write, коли holding buffer уже зайнятий.
Немає придатного intact правила безпечної зміни TX mode/clock/reload під
час active transmission.

Printed127 вимагає SREN0 для зміни **receiver** mode. Це правило не
переноситься на STCON. Printed120 окремо встановлює, що write STTMR не
змінює STTM: для fixed start period обидва мають бути заздалегідь задані
однаковим значенням. Воно не є загальним дозволом змінювати clock під час TX.

## 16. Standard MSM66201/207 applicability та цілісність джерел

Специфікації Y4/Y3 називають standard family MSM66201/MSM66P201/MSM66207/
MSM66P207. Новий bounded пошук не знайшов нового повного User Manual або
авторитетної errata. Додатковий mirror повернув той самий incomplete archive;
він не є незалежною manufacturer authority.

Photo members112,118,120,124,126,128,130 пройшли CRC і збіг із локальними
байтами. Відповідні потрібні повні сторінки візуально перевірені. Members114,
116,122 мають CRC failure; **усі** їхні видимі фрагменти excluded як semantic
authority, включно з formula117 і STCON table123. Missing photos132..146
не встановлюють зміст printed132..147. Однойменна сторінка companion
instruction chapter є сторінкою RT, тому не ремонтує serial chapter.

Точна applicability label:
`StandardMsm66201_207_Documented_NotEcuApplicable`.

## 17. Physical ECU applicability gaps

Залишаються `HardwareApplicabilityUnknown` та
`ActualNativeObservationNotEstablished`. Немає same-unit silicon/customer-mask
bridge, чинного native configuration owner, buffer/shift readiness, clock
generation, фізичного SF чи TX pending generation. Manufacturer reset
table не заповнює ці live-in fields.

Завершений software prefix або всі true synthetic premises не усувають цих
прогалин. `actualEcuApplicability`, `actualConfigurationOwner`, `actualReady`,
`physicalApplicability`, `actualPendingGeneration` залишаються null у
відповідних формальних результатах.

## 18. Software-to-STBUF2995 dependency graph

```text
intact manufacturer pages → qualified standard-profile rules
                                     │ applicability still unknown
reviewed286D..288C → declared five-slot configuration intents
                                     │ generation / aliases / interference
conditional writer timeline → declared STCON at chosen boundary
                                     │ whole-path native continuity unknown
frozen M2cr prospective AL + DD0 at2995 → formal source join
                                     │ actual acceptance/readiness unknown
                           STOP BEFORE STBUF2995
```

Кожне ребро потребує окремої source identity та premise. Знайдений2889
writer не доводить відсутність інших writes/interrupts між288C і2995.
Source join зіставляє software relations; він не відтворює такий шлях і не
одержує runtime authority.

## 19. П'ять нових pure functions та типи стану

| Функція | Результат у підтриманому scope |
|---|---|
| `stcon_configuration(snapshot)` | Selected local DATA effects і ordered SFR write intents |
| `stcon_writer_lineage(query)` | Declared generation/overlap/boundary relationships |
| `transmit_configuration_hypotheses(query)` | Source-qualified bit/code consensus та explicit unknown |
| `tx_lifecycle_obligations(query)` | Факт/unknown catalog для однієї із семи ситуацій |
| `stbuf2995_source_join(query)` | Незмінені чотири nested results і conditional agreement |

Configuration snapshot має рівно8 полів: прийняті7 M2cr плюс
`configurationIntents`. Memory/generations містять48 явних nullable bytes:
прийняті46 та0208/0209. Зберігаються12 register fields,
`registerKnownBits`, DATA `knownBits`, assumptions та inputClass.

П'ять intent slots `0048,0049,004A,0050,0054` мають тип
`{value: nullable byte, knownBits: bit map, generation: nullable label}`.
Вони живуть у просторі `SOFTWARE_SFR_INTENT`, окремо від DATA memory й
фізичних SFR. Unknown не заповнюється нулем; суперечливі raw/bit facts
відхиляються. Closed shape/type violation дає `ValueError`, unsupported
relation — explicit `OutsideVerifiedScope` або indeterminate result.

## 20. High-level equivalent pseudocode

```text
prepare_configuration(s):
    validate_closed_snapshot(s); copy(s)
    require noInterference and fresh effect namespace
    require exact LRB0041 before first local write
    write_local(r0,1C); write_local(r1,8C)
    require ordinary_byte; AL=DF; DD=0; ZF=0
    require known SCB now; write_selected_DP_word(0356)
    CF = old_bit(DATA0356,1)
    if CF unknown: return retained prefix at2878
    if CF == 0:
        write_local(r0,31); write_local(r1,A1)
        require ordinary_byte; AL=FB; DD=0; ZF=0
    declare_intent(STTM,AL); declare_intent(STTMR,AL)
    declare_intent(STTMC,12)
    require ordinary_byte; AL=read_local(r0); DD=0; update_ZF
    declare_intent(STCON,AL)
    require ordinary_byte; AL=read_local(r1); DD=0; update_ZF
    declare_intent(SRCON,AL)
    return conditional result before288E

configuration_hypotheses(slots):
    candidates = exact byte domains consistent with raw + known bits
    report only consensus of each reviewed mode/code relation
    preserve each original slot unchanged
    evaluate four conditional declared-slot predicates as metadata
    effectiveBaudRate = null; actual owner/readiness/applicability = null

source_join(q):
    produce and retain all four separately validated nested results
    reject unsupported claim or source binding
    reject any nested OutsideVerifiedScope
    require lineage.lastSlot == declared configuration slot0050 exactly
    require latest boundary relation == conditional reviewed writer
    require frozen M2cr formal STBUF result CompleteConditional
    return ConditionalSoftwareAndDocumentaryJoinOnly
```

Це structured high-level reconstruction, без CPU loop, opcode fetch або
мікропериферійної state machine. Join використовує configuration hypotheses,
lineage, documentary lifecycle та незмінену M2cr formal boundary function;
він не запускає configuration prefix повторно.

## 21. Формальні периферійні obligations та authority

Source binding має чотири exact typed strings: accepted base SHA і fingerprints
writer/primary/IRQ proofs. Відсутній чи неправильний binding не дає
дозволу на hardware claim. Перед typed refusal перевіряються всі closed
nested shapes; malformed input не приховується за claim rejection.

У кожному top-level результаті:

```text
actualHardwareObservation = null
actualBufferWrite = null
actualTransmission = null
actualTxCompletion = null
actualTxIrqDelivery = null
actualPeripheralClockEvent = null
cpuInstructionRetirements = 0
actualPeripheralOperations = 0
executionStatus = EXECUTION_BLOCKED
firmwareReady = false
stbufStopBoundary = STOP_BEFORE_STBUF_2995
```

Заявки ActualTx/NativeOwner/RuntimeAdmission, RX000A-as-TX, придуманий FIFO,
ACK-by-write або actual ECU applicability відхиляються у відповідних
закритих API. All-true formal prerequisites не створюють observation.

## 22. Source-to-model correspondence та frame conditions

Source contract зв'язує всі31 нові sites, прийняті60, п'ять функцій,
documentary fact IDs, exact proof hashes, unknown policy та authority.
Кожна функція має Inputs, Preconditions, SourceSites, ExactInstructionEffects,
BranchPredicates, RegisterDependencies, AddressSpace, MemoryAccessWidth,
PointerAliases, StateTransformation, OrderedEffects, Postconditions,
FrameConditions, UnknownSemantics, WriterGenerationLineage, StopBoundary,
Applicability та ExecutionAuthority. Contract JSON сам не підвищує evidence.

DATA DP alias — little-endian word `0084+8*SCB`; SCB6 перекриває00B4/00B5.
Немає глобальної вимоги SCB0 або USP0180. USP/SSP не використовуються цим
prefix і зберігаються; register-bank access вимагає встановленого context.
DATA0356 і generation не змінюються від bit read.

Кожен source write зберігається в порядку, включно із same-value DATA write
та `sameDeclaredValue` SFR intent. Intermediate state фіксується після
оновлення відповідного intent slot. `before` означає попередній **declared**
slot, не hardware readback. Невдала подія timeline не включається до journal,
проте коректний prefix залишається.

Reader metadata з guard `DATA0356.1=1_NotObserved`:

| Compare PC | Declared address | Predicate |
|---|---|---|
| 3FDF | 004A | `(v & F3) == 12` |
| 3FE7 | 0050 | `(v & 7F) == 1C` |
| 3FEB | 0054 | `v == 8C` |
| 3FF1 | 0049 | `v == DF` |

Ці checks short-circuit у retained source: mismatch виходить на3FB1,
success або bit1=0 bypass — на3FF7. Pure hypotheses не виконує reader,
не додає його RAM/SFR reads і не оголошує actual register consistency.

## 23. Independent reference oracle

Очікувані значення мають походити з незалежної моделі reviewed source facts,
closed input corpus і catalog proofs. Reference не читає й не викликає нові
implementation functions; expected canonical stream заморожується до
першого model comparison. Нові source corrections до freeze зберігають
попередні drafts і мають окрему кваліфікацію.

Порівнюються повні результати: raw/null state, partial bits, flags,
generations, alias extraction, write order, prefix refusals, documentary IDs,
nested results та authority fields. Сам збіг final mode або digest без
повного byte comparison не є достатнім independent proof.

## 24. Тестове покриття

Область перевірок охоплює обидві configuration branches, невідомий bit1,
LRB/SCB та ordinary-byte prefix gates, exact local/DP aliases, same-value
intents, generation reuse/staleness, alternate/unknown writers і no-interference.
Hypotheses перевіряє partial-bit consensus, усі коди STTMC, зокрема однаковий
combined mode за невідомого code2/3 і divisor512 за невідомого code6/7.

Lifecycle coverage розділяє всі7 documentary situations. Source join
порівнює raw value, knownBits і generation без нормалізації чи підстановки
нового AL/DD у M2cr query. Кількість cases, tests і фактичний PASS/FAIL
публікуються лише після незалежного freeze та виконаного QA.

## 25. Meaningful negative controls

Потрібні відмови на неправильний binding; unknown/reset-to-zero substitution;
DD1-as-byte; втрату same-value/order; generation reuse або stale generation;
невідомий банк; невстановлений effective alias; суперечливі bit facts;
невалідний nested shape; mismatched inputClass/configuration lineage;
намагання визнати software intent native owner.

Окремі controls відрізняють RX000A від TX000C, TXREADY від TX COMPLETE,
STTMC intent12 від physical readback, SRCON permission від STCONbit7,
corrupt-page formula від перевіреного clock divisor, buffer/shift description
від вигаданої FIFO або busy-write collision rule. Metadata-only refusal не
замінює перевірки реальної зміни input relationship.

## 26. Canonical artifacts та CI comparison

Canonical record має рівно16 явних полів за вимогою user§16:

```text
caseId, operation, input, sourceScope, evidenceClass, applicability,
output, state, branchOutcome, reads, orderedWrites, generationLineage,
intermediateStates, unresolvedConstraints, stopBoundary, executionAuthority
```

Повні input/output та всі nested results зберігаються без скорочення.
SourceScope/state/reads/intermediateStates/unresolvedConstraints/stopBoundary
є точними глибокими копіями однойменних полів output; `orderedWrites`
копіює весь output journal, включно з software SFR intents. `branchOutcome`
проєктує лише source-ordered Branch records у `{pc,taken,next}`; повні steps
залишаються в output. `evidenceClass` розділяє `StaticRomSoftwareEffect`
для configuration, `ManufacturerDocumented` для lifecycle та
`ConditionalSoftwareRelationship` для решти трьох операцій. Applicability
має незмінну standard-profile label з розділу16.

`generationLineage` містить stateGenerations, configurationIntentGenerations,
lastConfigurationSlot, configurationChecks та orderedWriterGenerations.
Відсутній відповідний source field стає null; conditional labels не
підвищуються до native ownership. `executionAuthority` точно копіює11
authority fields output: шість nullable actual observations, два нульові
integer counters, executionStatus, firmwareReady та stbufStopBoundary.
Validator відхиляє metadata, що не відповідає повному output. Null,
explicit unknown, prefixes і generations не вилучаються; field exclusions=[]
стосується повного stream, а не лише його metadata projection.

Validator і finite research CI повинні порівняти **повні decompressed bytes**
expected/local/Ubuntu/Windows, унікальні case IDs та всі raw source bindings.
Records/bytes/SHA/firstMismatch/field exclusions/exact SHA беруться з actual
receipts. Новий пакет не перетворює synthetic records на retired instructions.
Historical full-QA fallback зберігається; фактично skipped Historical17 і
Desktop звітуються як NotRun.

## 27. Preservation та privacy

Незмінними залишаються прийняті M2cn–M2cr contracts, oracles, streams,
manifests, reports, production CPU/Bus/Exec і runtime admissions. Public
пакет містить reviewed forms та source relationships без OEM opcode stream,
приватних listings, credentials або acquisition records.

Успадковано п'ять documented exceptions: три ранні та окремі дозволені
Python-tooling exceptions M2cn/M2cp. Вони не стають нулем через новий baseline.
Нові unauthorized differences мають бути0 у визначеному scoped audit;
`StrictHistoricalPreservationPass` залишається false. Scoped audit не є
перевіркою цілого storage. Новий exception потребував би окремого дозволу.

## 28. Готовність до перенесення на C++/Rust

Розділяйте `DataSnapshot`, `DeclaredSfrIntentSlot` і `DocumentaryObligation`.
Nullable values та bit knowledge мають бути окремими типами; unknown не
кодується нульовим byte. Для immutable outputs копіюйте вкладені maps/lists,
а serialization виконуйте детерміновано без зміни order journals.

Порт configuration — structured function із ранніми typed boundaries,
а не новий CPU interpreter. Передавайте selected bank/address dependencies,
preserved context і source-bound ordinary-byte premise явно. Word alias
вирівнюйте за reviewed addressing rule; generation labels не зводьте до
значень bytes. Виносьте documentary predicates в окремі дані; не реалізуйте
STBUF latch, queue, timing або IRQ delivery як приховані helper effects.

Після перенесення потрібна та сама full-output reference equivalence.
Навіть успішний host C++/Rust порт не встановлює target ABI, physical timing,
actual hardware compatibility, native continuation або FirmwareReady.

## 29. Залишкові blockers

Відкриті: same-unit silicon/peripheral applicability; native DATA0356.1 owner;
reaching configuration generation до2995; можливі intervening writers;
актуальний transmitter state/clock; STCON full length/stop/parity encodings
і bit7; physical SF; IE polarity conflict; TX-specific ACK/reassertion;
full-buffer collision/set-clear priority; mode/reload changes during TX;
окремий TX-complete interrupt і general baud formula.

Ці прогалини обмежують hardware execution. Вони не приховуються при
`CompleteConditional`: такий status означає завершені правила обмеженої
software/documentary relation. Остаточний research verdict обирається за
фактично пройденими delivery gates; runtime лишається `EXECUTION_BLOCKED`.

## 30. Наступний evidence-driven крок

Рекомендація — окремий bounded пошук інтактної allocation/operation
документації потрібної MCU revision для STCON і TX acknowledgement,
узгоджений із same-unit silicon applicability та static reaching-definition
proof configuration→2995. Заздалегідь визначити source requirements і
refusal conditions; не запускати peripheral execution як спосіб заповнення
відсутніх facts.

Це рекомендація для нового дозволу. M2cs не починає M2ct, CPU/ROM/IRQ/RTI,
STBUF write, GUI, hardware або firmware operations. Після власного delivery
етап завершується з `FirmwareReady=false`.
