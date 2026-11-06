# M2ct — TX ACK, configuration reader і походження DATA0356.1

## 1. Прийнята база M2cs

База — `659b236a82bbea92d32666df7a1042106c5bb603`, прийнятий результат
`CONDITIONAL_STCON_CONFIGURATION_AND_TX_SOURCE_ESTABLISHED / EXECUTION_BLOCKED`.
Пакети M2cn–M2cs, їхні contracts, reference oracles, source identities та
історичні результати залишаються незмінними. Новий пакет —
`research/p28-word0196/tx_ack_configuration_provenance/`.

M2ct розширює source-qualified software reconstruction: повний bounded
configuration reader, два producer prefixes, умовні reaching definitions та
документальні ACK obligations. Це не CPU або peripheral execution.
Фактичні QA/CI/canonical/delivery результати встановлюються окремими receipts
і фінальним звітом; цей документ не засвідчує заплановані перевірки як PASS.

## 2. Manufacturer source inventory

Успадковано source-qualified OKI Instruction Manual, intact частини
MSM66201/207 User Manual та специфікації `E2E1027-27-Y4` і
`J2E1027-27-Y3`. Сім раніше перевірених User photo members112,118,120,124,
126,128,130 мають accepted CRC/visual qualification. M2ct не називає
17 прийнятих TX фактів новими відкриттями.

Новий bounded пошук отримав інший image-only PDF: попередня специфікація
`MSM66201/66P201`, 644783 bytes,
SHA-256 `4c3e2751e19d31f04ad550d90f55653ac235fa19030a002e407e4d752182f666`.
Він містить34 manufacturer pages і окремий commercial appendix, разом35
PDF pages. Повні сторінки1,10,11,18,19,34 візуально перевірено. Це
manufacturer-branded Preliminary specification із невстановленими exact
document ID, edition/date та криптографічною автентичністю. Library stamp
не використано як manufacturer revision.

Printed19 лише підтверджує вже відомі SFR addresses/access/reset; printed10–11
є електричними timing tables/diagrams. Вони не відновлюють operation-level
ACK rules або STCON allocation. Перенесення цієї попередньої редакції на
MSM66207 чи конкретний ECU не доведено. Commercial appendix не є semantic
authority. Нову hardware semantics із цього документа не введено.

## 3. STCON allocation recovery

Нове повне allocation table не отримано. Accepted intact prose встановлює
bit0 normal/multiprocessor, bit1 UART/synchronous, normal length code у
bits3:2, multiprocessor data/address bit2 та ignored bit3, UART stop-length
code або synchronous master/slave у bit4. Bit5/6 мають parity-related roles,
але повні polarity/encoding невстановлені. Значення bit7 лишається unknown.

Регістр STCON — DATA0050, 8-bit R/W, standard documentary reset80. STBUF —
DATA0051, 8-bit write-only, undefined reset descriptor. Ці властивості не
підставляють current state і не встановлюють TX enable. Таблиця SRCON не
використовується для заповнення прогалин STCON.

## 4. Unknown encodings та межі негативного пошуку

`stcon_allocation.UNKNOWN_ENCODINGS` явно зберігає невідомі character-length
mapping, UART stop-length mapping, parity presence polarity, odd/even polarity,
bit7, TX permission та safe active-mode change. Успадковані15 unknown IDs
не вилучаються через отримання іншої specification sheet.

Пошук обмежено12 новими цільовими queries: successor manufacturer,
японські назви, exact-family errata, технічні бібліотеки й точні TX terms.
Виконано8 web candidate opens і4 bounded direct HTTP requests для конкретних
document locators. Відомий пошкоджений16MB ZIP не завантажувався повторно;
нових applicable errata/full operation chapters не отримано. Доступ до
конкретного1988 data book повернув403; його semantics не оцінювалася.

Це негативний результат визначеного пошуку, а не доказ глобальної
відсутності документації. CRC-failed printed114/115,116/117,122/123 та їхні
видимі фрагменти залишаються excluded. Зміст missing132–147 не припускається.

## 5. TX ACK, reassertion та collision rules

`ACK_RULES` є closed alias до14 source-qualified `RULES`. Кожен рядок має
окрему classification і qualified relationship, без застосування події.

| Relationship | Класифікація у визначеному scope |
|---|---|
| UART TX READY at start | Inherited `ManufacturerDocumented` |
| Generic qualified interrupt-entry clear | `SourceQualifiedConditional` |
| Described previous transfer + one buffered next item | Inherited `ManufacturerDocumented` |
| Standard reset descriptors | `ManufacturerDocumented`, не current state |
| STBUF-write ACK / request-read ACK | `Unknown` |
| Automatic reassertion без нових eligible data | `Unknown` |
| Third write за зайнятого holding buffer | `Unknown` |
| Hardware-set/software-clear priority | `Unknown` |
| Safe mid-TX mode/clock/reload changes | `Unknown` |
| Окремий TX-complete IRQ | `Unknown` |
| Current native ready/reset/applicability | `Unknown` |
| IE polarity | `SourceConflict` |

Generic serviced-factor clearing не перетворюється на TX-specific
ACK-by-write/read. Описані holding buffer та окремий shift register не
встановлюють FIFO, третю стадію, queue arbitration або automatic retries.

## 6. Manufacturer contradictions

Printed165/168/169 описують set1 enable/gating, а printed167 має суперечливу
IE0 entry condition. Нова придатна errata, яка це розв'язує, не отримана.
`iePolarityResolution=null`; жодна гіпотеза не стає фізичною полярністю
невідомого customer-mask MCU.

Також не встановлено порядок implicit ZF update проти explicit byte write,
коли destination XORB є самим PSWH. Це окрема ISA self-destination ambiguity,
яка впливає на producer нижче; її не вирішують output нового emulator або
бажаний результат source model.

## 7. TX READY000C та окремі джерела

Прийнята manufacturer allocation не змінена:

| Source | Vector | IRQ/IE word bit | Ідентичність |
|---|---|---|---|
| TX READY | 000C | 2 | RQSTRDY / IESTRDY |
| TX BRG overflow | 0024 | 14 | RQSTGEN / IESTGEN |
| RX READY | 000A | 1 | Окреме RX джерело |

TX READY виникає на початку описаного UART normal transmit cycle. Це не
загальне TX COMPLETE. У M2ct немає interrupt delivery, request generation,
acknowledge event або buffer transmission; vector/bit лишаються documentary
source identities.

## 8. Повний bounded reader CFG3FD4–3FF5

Reader має15 reviewed sites і exact stop-before targets3FB1/3FF7:

```text
3FD4 DP=0356
3FD7 CF=old DATA0356.1
3FD9 if CF==0: stop before3FF7
3FDB AL=supplied readback4A
3FDD AL &= F3
3FDF compare AL,12
3FE1 if not equal: stop before3FB1
3FE3 AL=supplied readback50
3FE5 AL &= 7F
3FE7 compare AL,1C
3FE9 if not equal: stop before3FB1
3FEB compare supplied readback54,8C
3FEF if not equal: stop before3FB1
3FF1 compare supplied readback49,DF
3FF5 if not equal: stop before3FB1; else stop before3FF7
```

Known SCB0..7 потрібний перед першим DP word write. Немає LRB0041 або
USP0180 gate: ці selected forms використовують absolute DP/zero-page operands.
Physical aliases selected DP word усе одно враховуються. Зупинні інструкції
на3FB1/3FF7 не виконуються; ці boundaries не означають actual ROM rejoin.

## 9. Short circuit, flags та partial states

Guard bypass має3 source steps і не споживає SFR readbacks. Перший/другий/
третій/четвертий mismatch має7/11/13/15 steps; повний match —15. Це counts
source transformation, не retired instructions або фізичний час.

JGE залежить від CF0; JNE — від ZF0. Невідомий predicate зупиняє саме reached
branch як `IndeterminateBranch`, зберігаючи prefix, branch record і next=null.
Пізніші readbacks не читаються speculative. Ordinary-byte premise потрібна
лише перед reached LB3FDB/3FE3, до споживання відповідного readback.

LB установлює DD0/ZF за byte possibilities та змінює AL; ANDB змінює AL/ZF,
зберігає CF/HC/DD/AH. CMPB окремо визначає unsigned-borrow CF і equality ZF
за consensus усіх допустимих bytes. Відомий mismatch може мати ZF0 навіть
за unknown CF. Direct CMPB54/49 не змінює AL/DD. За повного match:
AL=1C, CF0/ZF1/DD0; за guard bypass AL/ZF/DD зберігаються від входу.

HC та ordinary AH зберігаються. Nullable raw і explicit bit knowledge не
змішуються: unknown не заповнюється нулем. Усі49 DATA bytes лишаються
незмінними, окрім selected DP word; alias local RAM не оголошується окремо
збереженим, якщо перекриває цей word.

## 10. STTMC read-as та software write intent

Прийнятий M2cs software intent12 не є physical readback12. Standard STTMC
bits2/3 документально read-one; reader maskF3 відкидає ці позиції. Наприклад,
**явно заданий symbolic**1E задовольняє `(1E & F3)==12`. Модель не генерує1E,
не підміняє supplied raw12 і не стверджує actual read-as event.

Сумісність mask із read-one описом не доводить історичну авторську мету ROM.
Зберігаються окремі types для desired intent, documentary read-as,
supplied symbolic readback і actual hardware observation. Перші три можуть
брати участь у conditional reasoning; четвертий лишається null.

## 11. DATA0356.1 writer candidates

Підтверджений локальний writer — `60D5 MB [DP].1,C` після `60D2 DP=0356`.
Це bit RMW: byte прочитано для збереження сусідніх бітів; bit1 замінюється
CF; store зберігається навіть за same value. MB не створює ZF з old bit і
не змінює жодного flag.

Інші whole-byte/word/bit writers потребують current address/generation
qualification. Запис bit0 або bit6 не є writer bit1. Reset-loop candidate
не встановлює current native generation. Локальна наявність60D5 не доводить,
що цей writer досягнуто перед configuration2876 або reader3FD7.

## 12. Два source-qualified producer variants

`mode_bit1_producer(snapshot)` має два closed entry variants:

```text
SymbolicCarryTail:
    60D2 DP=0356
    60D5 DATA0356.bit1=incoming CF
    stop before60D7

Compare3cb:
    60C9 DP=03CB
    60CC CMPB [DP],80
    60CF XORB PSWH,80
    60D2 DP=0356
    60D5 DATA0356.bit1=CF
    stop before60D7
```

Tail залишає CF symbolic, із nullable input; він не вигадує його owner.
Compare дає CF=`DATA03CB < 80` після CMP, потім CF інвертується explicit
PSWHbit7 destination write. Отже новий bit1 дорівнює source03CB.bit7 за
встановленої відповідної bit knowledge. Відомий bit7 достатній для CF навіть
коли решта source byte невідома; compare ZF має окрему equality dependency.

Після XORB ZF завжди unknown у цьому bounded contract: implicit ZF effect і
explicit PSWH destination перекриваються, precedence не встановлено.
Наступні MOV/MB зберігають цей unknown. Tail не виконує XOR і зберігає
incoming ZF. AL/AH/HC/DD/MIE/OtherPSW у визначених source effects збережено;
physical SF не призначається. Усі object forms DD-independent: DD0, DD1 та
unknown DD не змінюють byte/bit width цих конкретних інструкцій.

SCB потрібний перед першим selected DP write; немає local/page/USP gate.
Tail має2 source steps/2 journal writes. Compare має5 steps/4 writes:
DP03CB, architectural REGISTER PSWH XOR, DP0356, DATA0356 RMW. PSWH read/
write не маскуються під TX SFR operation. Unknown CF робить target bit1
unknown, але зберігає всі інші відомі біти, а не stale old-bit1 knowledge.

Entry60C9 сам не доводить попередній r0-zero branch або native DATA03CB owner.
Після60D7 є інший source prefix і пізніший RT60E4 з невстановленим caller
frame; M2ct їх не виконує й не використовує для вигаданого scheduler return.

## 13. Успадковані configuration writers286D–288C

M2cs зберігає дві ordered software configurations:

| Selector DATA0356.1 | STTM48 | STTMR49 | STTMC4A | STCON50 | SRCON54 |
|---|---|---|---|---|---|
| 1 | DF | DF | 12 | 1C | 8C |
| 0 | FB | FB | 12 | 31 | A1 |

Це intents, не current SFR values. Configuration prefix зупиняється перед
288E/DATA4700. STTMC12 означає documentary combined TX/RX BRG code2,
run bit1, clock code0/divisor2; не спостережене running. General baud formula
зі failed117 не використовується. Новий reader не змінює старий prefix,
його bank requirements, journals або contract.

## 14. Writer/reader generation relations

`tx_configuration_reaching_definitions(query)` зберігає незмінний full result
старої M2cs declared timeline і класифікує окрему relation. Пріоритети
розрізняють source conflict/claim refusal, unknown interference, competing
writer, missing generation, replaced entry generation, stale request та
відсутній CFG path.

Лише `ConfigurationSuffix` і `ReaderWindow` можуть повернути
`ConditionalWriterRetained` за узгоджених explicit generation та no-interference
premises. У reviewed suffix2889→288B→288C→288E немає ще одного0050 software
writer; reader window пише лише DP alias. Це bounded no-software-overwrite
relationship, не current hardware owner чи доведений шлях між blocks.

## 15. Possible intervening writes

Byte0050 і even-aligned word0050/0051 можуть змінити target. Alternate word
request0051 вирівнюється до0050 за reviewed ISA; byte0051 не є writer0050.
Repeated same-value store лишає окремий event/generation. Unknown writer або
no-interference=false/unknown не зберігають підтверджену retention.

Однаковий numeric byte не доводить ту саму generation. Одна source constant
або знайдений writer не виключає pointer aliases, інший software write,
peripheral reset чи unreviewed control flow. Timeline не стає memory trace
невиконаного hardware.

## 16. Configuration-to-STBUF dependency graph

```text
symbolic CF / conditional DATA03CB compare
                   │ reviewed local producer
               DATA0356.1 generation
                   │ missing reaching path / interference proof
             M2cs configuration intents
                   │ separate readback symbols, not automatic equality
               bounded reader predicates
                   │ missing foreground/call/IRQ/return context
        M2cr prospective AL=(DATA03F1 & 1F), DD0
                   │ actual owner/readiness/acceptance unknown
                  STOP BEFORE STBUF2995
```

`noInterference=true` є premise для вибраного source window. Воно не створює
відсутнє ребро CFG або physical applicability.

## 17. Встановлені й невстановлені CFG links

Встановлено локальні source fall-through60D5→60D7,2889→288B,288C→288E та
прийнятий297F→2980. Важливо: `28AB J3F47` є direct jump, **не** numeric
fall-through до foreground block28AE. На3F47 є SSP comparison047E і наступна
перевірка; це не доведений native frame.

Після288E перший external-data operand на2891 читає DATA4700 із невстановленими
owner/applicability. Producer caller/RT60E4 context, наступний verifier,
foreground dispatcher та можлива IRQ/RTI continuity не закриті. Відношення
producer→configuration, configuration→reader, configuration→2995 і
reader→2995 залишаються окремими missing source relationships.

## 18. П'ять нових pure functions

| API | Область результату |
|---|---|
| `tx_configuration_reader(snapshot)` | Fifteen-site reader effects, short circuit і stop targets |
| `mode_bit1_producer(snapshot)` | Symbolic carry tail або five-site compare/XOR/RMW prefix |
| `tx_configuration_reaching_definitions(query)` | Declared generation та bounded-window retention obligations |
| `tx_ack_documentary_obligations(query)` | Один із14 qualified documentary relationships |
| `stbuf2995_configuration_provenance(query)` | П'ять незмінених nested results і unresolved cross-block join |

Reader snapshot має9 closed fields: старі8 M2cs плюс `sfrReadbacks`; memory/
generations49 додають03CB до прийнятих48 bytes. Producer додає десяте поле
`entry`. Чотири readback slots0049/004A/0050/0054 відділено від п'яти старих
configurationIntent slots. Кожен slot має nullable byte, explicit knownBits і
nullable generation. Повні12 registers та registerKnownBits зберігаються.

## 19. High-level equivalent pseudocode

```text
reader(s):
    copy_and_validate(s); require no_interference and fresh_namespace
    require selected_SCB; write_DP(0356)
    CF = old_status_bit1
    if unknown(CF): stop_indeterminate_with_prefix(3FD9)
    if CF == 0: return guard_bypass_before3FF7
    require ordinary_byte before each reached LB
    AL = supplied_STTMC & F3; compare_unsigned(AL,12)
    if unknown(ZF): stop_indeterminate_with_prefix(3FE1)
    if ZF == 0: return mismatch_before3FB1
    AL = supplied_STCON & 7F; compare_unsigned(AL,1C)
    if unknown(ZF): stop_indeterminate_with_prefix(3FE9)
    if ZF == 0: return mismatch_before3FB1
    compare supplied_SRCON,8C; short_circuit on unknown/mismatch
    compare supplied_STTMR,DF; short_circuit on unknown/mismatch
    return all_checks_match_before3FF7

producer(s):
    if entry == Compare3cb:
        write_DP(03CB); compare_byte(DATA03CB,80)
        architectural_PSWH_XOR80; CF = nullable_not(CF); ZF = unknown
    write_DP(0356)
    ordered_RMW(DATA0356, bit1 = CF, preserve_known_neighbors)
    return before60D7

provenance(q):
    validate_all_nested_shapes_and_same_input_class
    retain_full(reader(q), producer(q), reaching(q), ack(q), frozen_stbuf(q))
    refuse unsupported authority or nested source failure
    preserve unresolved nested premises if present
    return IndeterminateObligation(ConfigurationTo2995PathNotEstablished)
```

Nested outputs не передаються автоматично як input іншій функції. Це не
continuous execution і не прихований reseed/state handoff. Наприклад,
producer result сам не підміняє DATA0356 reader query.

## 20. Formal contracts, frame conditions та authority

Кожна функція має Inputs/Preconditions/SourceSites/BranchPredicates/
StateTransformation/OrderedEffects/Postconditions/FrameConditions/
UnknownSemantics/StopBoundary/Applicability/ExecutionAuthority. Source binding
містить accepted base та exact reader/producer/reaching/primary proof hashes.
Malformed closed shapes/types дають `ValueError`; unsupported relationships
повертають typed refusal або indeterminate result. Глобальна claim refusal
не приховує malformed nested input.

Selected DP word має DATA alias0084+8×SCB і наступний byte; SCB6 використовує
00B4/00B5. Не створюється окремий stale pointer shadow. Same-value writes,
REGISTER effects і їхні intermediate states зберігаються в source order.
SSP/USP не ініціалізуються; actual SF або return frame не вигадуються.

Усі результати зберігають шість actual-observation fields null, нульові
integer cpuInstructionRetirements/actualPeripheralOperations,
`executionStatus=EXECUTION_BLOCKED`, `firmwareReady=false` та
`stbufStopBoundary=STOP_BEFORE_STBUF_2995`. ACK query із Unknown relationship
може бути `CompleteConditional` як завершена документальна класифікація;
це ніколи не performed ACK. Generic IRQ-entry rule лишається conditional.

Натомість top-level provenance join не повертає Complete/native навіть за
всіх true synthetic premises: cross-block CFG залишається недоведеним,
`continuousCfgEstablished=false`, actual owner/readiness=null.

## 21. Independent reference oracle

Expected формуються незалежно з reviewed ISA, documentary facts і source
CFG. Reference не імпортує нові mathematical implementation functions та не
використовує їхні outputs для очікувань. Source/corpus/reference/test identities
та повний expected stream заморожуються до першого comparison.

Перевірка охоплює intermediate CF/ZF/DD, PSWH ambiguity, часткові values,
source read suppression, branch targets, physical DATA aliases, generations,
ordered same-value writes, nested results і authority. Збіг одного final
bit або status не є достатнім equivalence proof. Перший mismatch має бути
збережений, а його причина встановлена за джерелом.

## 22. Test coverage requirements

Source-bound coverage включає чотири reader mismatches, success/bypass,
unknown branch/readback, часткові bits, wrong SCB/context, reached LB gates,
short-circuit suppression та precise CF/ZF. Producer controls розрізняють
CF0/1/unknown,03CB bit7/equality, обидва entry variants, same-value RMW,
selected DP banks і збереження incoming DD.

Для generations перевіряються missing/stale/replaced/competing/unknown
writers, no-interference false, unproved CFG та відсутні foreground/return
obligations. Documentary controls зберігають unknown bit7/parity/stop,
reset80-versus-current, TX/RX/BRG separation і generic-versus-TX ACK.
Фактичні кількості та PASS/FAIL належать завершеним QA receipts, не плану.

## 23. Meaningful negative controls

Потрібні відмови на RX000A-as-TX, TXREADY-as-COMPLETE, bit7-as-enable,
reset-to-current, intent12-as-physical-readback, invented parity/stop coding,
ACK-by-write, automatic reassertion, full-buffer winner/FIFO і clock/TX events.

Окремо змінюються guard/context/generation/CFG relations: пропущений bit1
guard, stale requested generation, unknown interference, вигадане ребро до2995,
same-value deduplication, unknown→0 та actual owner promotion. Схожі numeric
values не замінюють reaching proof. Негативний control не повинен бути лише
перевіркою тексту статусу.

## 24. Canonical comparisons

Record має exact16 keys:

```text
caseId, operation, input, output, sourceScope, evidenceClass,
applicability, branchOutcome, state, reads, orderedWrites, generations,
intermediateStates, unresolvedConstraints, stopBoundary, executionAuthority
```

Повні input/output та nested results зберігаються. `generations` розділяє
DATA, software intents, supplied readbacks, ordered writer events та reaching
definitions. Branch projection не вилучає повні steps із output. Evidence
classes — StaticRomSoftwareEffect, ConditionalSoftwareRelationship або
ManufacturerDocumented; applicability лишається standard-profile qualification.

Потрібен повний expected/local/Ubuntu/Windows decompressed byte-for-byte
comparison, exact source bindings, unique IDs, records/bytes/SHA, firstMismatch
і canonicalFieldExclusions=[]. Null, refusal та unknown не вилучаються.
Source rows перевіряються з їхніми успадкованими explicit physical-representation
qualifications; whole auxiliary metadata equality не підміняє raw binding
equality. Synthetic records не називаються CPU traces.

## 25. Preservation та доставка

Прийняті source/contracts/oracles/manifests/expected/reports/seals/runners і
original ROM зберігаються. Production CPU/Bus/decoder/Exec, runtime admission
та GUI не змінюються. Public пакет не містить ROM bytes, приватних listings,
credentials або private acquisition records. Новий source proof не переписує
старі CRC failures або fingerprints.

Зберігаються п'ять попередніх exceptions:3 inherited,1 M2cn Python tooling,
1 M2cp Python tooling; StrictHistoricalPreservationPass=false. Нові unauthorized
differences мають бути0 у фактично визначеному scope. Scoped preservation не
є whole-storage audit. Чотири сторонні untracked files не включаються до
коміту й не видаляються. Finite research CI зберігає full-QA fallback;
фактично skipped Historical17/Desktop звітуються NotRun.

Commit/push/CI/seal/FINAL мають окремі actual gates. Фінальний український
звіт записується останнім після перевіреного exact SHA та evidence seal.

## 26. Actual ECU applicability та перенесення на C++/Rust

Для позитивного hardware claim потрібний same-unit donor/PCB/MCU marking/
mask/peripheral revision/ROM provenance/manufacturer applicability chain.
Generic document, package suffix або software intent цього не створює.
Зберігаються `ActualEcuSiliconUnbound` і
`PeripheralApplicabilityUnestablished`.

Для host C++/Rust порту використовуйте окремі immutable types для DATA,
intent slots, supplied readbacks і documentary obligations. Nullable scalar,
partial-bit set і generation label не зливайте. Зберігайте exact branch
prefixes, CF/ZF/DD rules, REGISTER PSWH event, DP aliases та same-value
writes. Unknown ZF після self-destination XORB є частиною контракту, а не
приводом вибрати зручний execution order. Не додавайте transmitter latch,
queue, timing або IRQ helper до pure software functions.

Успішний host equivalence не встановлює target ABI, firmware integration,
physical timing, native scheduler або hardware-safe placement.

## 27. Remaining blockers

Не закриті повна STCON allocation, TX-specific ACK/read-ACK/reassertion,
third-write/full-holding і set-clear priority, safe active mode/clock/reload
changes, окремий TX-complete source та IE polarity. Новий Preliminary scan
цих правил не встановив; це придбаний corroborative source, не recovered
missing operation manual.

Також лишаються actual DATA03CB/CF/0356.1 ownership, producer reaching path,
current configuration generation до2995, external DATA4700 applicability,
caller/verifier/foreground/IRQ/return continuity, actual transmitter state,
physical SF і same-unit silicon identity. Ці межі лишаються explicit навіть
за успішних локальних conditional transformations.

## 28. Рекомендований наступний scope M2cu

Окремий evidence-driven етап може цілитися в integrity-qualified повну
STCON/serial-operation chapter із manufacturer revision та в один bounded
caller/reaching-definition gap, установлений новими source proofs. Перед
реалізацією потрібні exact source identities і перевірювані stop/refusal
conditions. Негативний bounded search слід відрізняти від відсутності правила.

Це рекомендація, не початок M2cu. M2ct не виконує CPU/ROM/IRQ/RTI, STBUF,
GUI, hardware чи firmware operations. Після власного delivery — STOP;
`EXECUTION_BLOCKED`, `FirmwareReady=false`.
