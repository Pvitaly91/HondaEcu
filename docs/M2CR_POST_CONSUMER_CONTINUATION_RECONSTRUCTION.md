# M2cr: програмна continuation після DATA03F4 consumer до STBUF2995

M2cr додає чотири research-only інтерфейси: локальне перетворення стану від
PROGRAM2980, його композицію з незміненим consumer M2cq, перевірку збереження
двох DATA slots і формальні вимоги до невиконаної інструкції STBUF2995.
Це pure software reconstruction: жоден інтерфейс не виконує ROM, CPU, Bus,
IRQ, RTI або peripheral I/O.

Практичний результат continuation:

```text
DATA0356.6 := 1
DATA03F5   := 2
H          := DATA03F1
AL         := H & 1F
DATA03F6   := AL
DP         := 03F6
STOP_BEFORE_STBUF_2995
```

CF і HC зберігаються; DD стає 0, а кінцевий ZF описує нульовість `H & 1F`.
У цьому вікні немає читання або перезапису DATA03F2 чи DATA03F4. Значення
`G+3`, записане попереднім consumer у DATA03F2, не є джерелом нового AL.
Фізичне призначення цих байтів, native reaching definition від026C і робота
передавача залишаються окремими невстановленими питаннями.

Постійні межі результату:

```text
EXECUTION_BLOCKED
ActualHardwareObservation = null
CpuInstructionRetirements = 0
FirmwareReady = false
```

## 1. Прийнята база M2cq

База: `ac4086aec3cea32d0e76d6732d9998cbd75bbb28`, прийнятий M2cq
`CONDITIONAL_PAYLOAD_CONSUMER_AND_TAIL_EQUIVALENCE_ESTABLISHED / EXECUTION_BLOCKED`.
Його шість consumer sites і frozen typed state використовуються без зміни.
Попередні 1060 canonical records і 96 static tests належать M2cq, а не є
новими результатами M2cr.

Новий пакет:
`research/p28-word0196/post_consumer_continuation/`.
Публічний validator:
`research/p28-word0196/validate_post_consumer_continuation.py`.
Production CPU/Bus/decoder/Exec і старі research packages не змінюються.

## 2. Джерела й область їхньої застосовності

Instruction effects встановлено за OKI MSM66201 Instruction Manual,
First Edition, September1991, SHA-256
`f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271`.
Розглянуті повні сторінки: MOV DP3-86, SB3-127, LB3-70, ANDB3-24,
STB3-155, ST3-154 та правила zero-page/word access1-18,1-20.

Точні PC, межі інструкцій і operands походять із незмінених retained listing
та decoded extents. Їхні identities зберігаються у source receipts; OEM opcode
bytes не включено до цього документа або нових public fixtures.

Два незалежні source dossiers мають SHA-256:

| Область | SHA-256 |
| --- | --- |
| Continuation2980–2994, CFG і залежності | `c9bccc09dc1fa95bc3f1ea4c7e382a1b74982214bacbe905b45a6a8e5ca65379` |
| STBUF2995, primary pages і frozen M2cq handoff | `f436ca49a8e0491e78ac307425cb28893095a4dda8b0d8837c689ca7050d732c` |

Source-qualified ISA не доводить, що конкретний ECU має певну customer mask,
SFR revision або підтвердженого owner периферійного стану. Ці обмеження
успадковано з M2cl/M2cm.

Combined inventory містить49 inherited entries і11 нових entries, разом60:
десять software sites та окрему formal-only boundary2995. Це інвентар
source effects, а не60 нових виконаних інструкцій.

## 3. Exact instruction inventory2980–2995

`U` означає descriptor-independent форму, `R` — інструкцію, що встановлює
descriptor для свого розміру, `0` — форму з передумовою DD0.
Всі наведені DATA addresses — адреси окремого DATA space.

| PC | Форма | Bytes | DD | Програмний effect | Наступна межа | ISA page |
| --- | --- | ---: | --- | --- | --- | --- |
| 2980 | MOV DP,#N16 | 3 | U | DP=0356 | 2983 | 3-86 |
| 2983 | SB [DP].6 | 2 | U | DATA0356.6=1;ZF=!oldbit6 | 2985 | 3-127 |
| 2985 | MOV DP,#N16 | 3 | U | DP=03F5 | 2988 | 3-86 |
| 2988 | LB A,#N8 | 2 | R | AL=2;DD0;ZF0 | 298A | 3-70 |
| 298A | STB A,[DP] | 1 | 0 | DATA03F5=AL | 298B | 3-155 |
| 298B | MOV DP,#N16 | 3 | U | DP=03F1 | 298E | 3-86 |
| 298E | LB A,[DP] | 1 | R | AL=H=DATA03F1;DD0;ZF=isZero(H) | 298F | 3-70 |
| 298F | ANDB A,#N8 | 2 | 0 | AL=H&1F;ZF=isZero(AL) | 2991 | 3-24 |
| 2991 | MOV DP,#N16 | 3 | U | DP=03F6 | 2994 | 3-86 |
| 2994 | STB A,[DP] | 1 | 0 | DATA03F6=AL | 2995 | 3-155 |
| 2995 | STB A,N8 | 2 | 0 | Формальна межа DATA0051; effect не застосовано | STOP | 3-155 |

Нові software effects охоплюють рівно десять sites і 21 byte source span
до2995. Одинадцятий рядок описує instruction boundary, а не ще одну
застосовану операцію. Static site count не є CPU retirement count.

## 4. CFG: straight-line continuation

Повний переглянутий ланцюжок:

```text
2980 →2983 →2985 →2988 →298A →298B →298E →298F →2991 →2994 →[2995 STOP]
```

Кожен edge є fall-through за довжиною попередньої інструкції. У цих десяти
sites немає branch, call, return або indirect PROGRAM transfer. Старий status
bit6 не вибирає шлях; він впливає лише на проміжний ZF.

Невідомий H може дати невідомий AL/ZF, проте не створює
`IndeterminateBranch`: у цьому source window немає predicate, який би
зупинив straight-line обчислення. Refusal через непідтверджений input context
залишається окремим результатом із точним prefix і boundary.

## 5. Source edge297F→2980

Остання інструкція consumer M2cq — `STB A,[DP]` на297F довжиною один byte.
Її static successor —2980. Frozen consumer вже зберігає цей edge у власному
`steps`; композиція не додає його вдруге.

Це source-owned software edge, а не спостереження native CPU. Не потрібні
host assignment PC, додатковий transfer ticket, fake call/return або
повторний запис A/RAM між двома частинами. Приєднання дозволено тільки до
успішного frozen result `CompleteConditional` на boundary2980.

## 6. Чотири public pure functions

| Інтерфейс | Input | Результат |
| --- | --- | --- |
| `post_consumer_continuation(snapshot)` | Frozen six-field snapshot плюс explicit `registerKnownBits` | Десять software effects до2995 або збережений prefix refusal |
| `consumer_with_continuation(snapshot)` | Незмінний six-field input M2cq | Frozen consumer плюс continuation, без reseed |
| `continuation_lineage(query)` | Explicit before/after slots03F2/03F4, generations, source binding і premise | Conditional retention relation, не native reaching definition |
| `stbuf_boundary_obligations(query)` | Descriptor, prospective AL, source binding і declarative prerequisites | Формальні вимоги без peripheral operation |

Функції не змінюють caller input. Malformed closed shape або суперечлива
bit knowledge викликає `ValueError`. Семантично непідтверджені передумови
дають typed result, зберігаючи допустимий математичний prefix.

## 7. Typed snapshot і передумови

Успадковані поля snapshot:

```text
inputClass, memory, knownBits, registers, generations, assumptions
```

Це ті самі 46 byte slots і 46 generation labels M2cq. Register map містить
AL,AH,CF,ZF,HC,DD,MIE,OtherPSW,LRB,SCB,USP,SSP. `None` означає unknown.
`inputClass` залишається synthetic/symbolic/manufacturer-source-qualified
класифікацією; він не засвідчує actual hardware input.

Direct continuation додатково приймає `registerKnownBits` із ключами
`AL.0`..`AL.7` та `AH.0`..`AH.7`. Значення — тільки integer0/1; відомий scalar
не може суперечити explicit bits. Consistent subset не доповнюється автоматично
при entry. Наприклад, raw `AL=None` із вісьмома відомими bits лишається raw
`None` до instruction overwrite, хоча candidate set може бути singleton.

Для умовного перетворення потрібні `noInterference=true` і відомий SCB0..7
до першого DP write. LRB і USP не мають штучної вимоги007E/0180: selected
operands використовують повні DP addresses. Initial DD може бути0/1/unknown;
LB2988 встановлює DD0 перед першим STB у новому тілі.

## 8. Status і accumulator transformations

Позначимо `S=DATA0356` та `H=DATA03F1` на відповідних reads.

```text
2983: DATA0356 := S | 40
      ZF := not original(S.bit6)
2988: AL := 02; DD := 0; ZF := 0
298E: AL := H;  DD := 0; ZF := isZero(H)
298F: AL := H & 1F; ZF := isZero(AL)
```

SB зберігає сусідні bits; невідомий старий bit6 дає невідомий проміжний ZF.
Наступна LB immediate незалежно встановлює ZF0. `2` і `1F` — code-owned
immediates, а не приховані DATA reads.

Це програмні перетворення. Для DATA03F5 не встановлено фізичного значення
counter, а для DATA03F1/03F6 не встановлено виду ECU command.

## 9. CF/ZF/HC/DD, AH і PSWH

CF і HC не змінюються жодною з десяти нових інструкцій. У композиції вони
можуть зберігати результат попереднього `G+3`; direct input може лишити їх
невідомими. ANDB не слід замінювати host boolean operation, що довільно
очищує carry або half-carry.

AH зберігається під explicit ordinary-byte premise для LB. LRB,SCB,USP,SSP,
MIE та OtherPSW не перепризначаються. Physical SF не встановлено і не
підставляється як нуль.

Нова ділянка не записує PSWH. Невстановлений порядок ZF update проти
whole-byte PSWH destination write з M2cn/M2cq не розв'язується припущенням.
У новому тілі ZF задається конкретними SB/LB/ANDB effects; ANDB298F пише AL,
а не PSWH, тому старий self-destination ambiguity тут не застосовується.

## 10. DP і фізичні DATA aliases

Selected DP — word у DATA byte map:

```text
DP.low  = DATA[0084 + 8*SCB]
DP.high = DATA[0085 + 8*SCB]
```

Чотири MOV DP — чотири окремі 16-bit writes у вибраний slot. Не можна
зберігати незалежний scalar DP, який приховує ці DATA changes. SCB6 означає
спільні DATA00B4/00B5, включно з bits і generation labels; SCB unknown не
можна замінити bank0.

Word writes мають little-endian bytes. Фактичний порядок електричних byte
bus transactions тут не моделюється: ordered logical word write залишається
однією подією width16, а не двома довільними host stores.

## 11. Ordered journals і reads

Direct continuation має сім ordered writes:

| Ordinal | Source PC | Простір | Address | Width | After |
| ---: | --- | --- | --- | ---: | --- |
| 1 | 2980 | DP alias DATA | 0084+8*SCB | 16 | 0356 |
| 2 | 2983 | DATA RMW | 0356 | 8 | S із bit6=1 |
| 3 | 2985 | DP alias DATA | 0084+8*SCB | 16 | 03F5 |
| 4 | 298A | DATA | 03F5 | 8 | 02 |
| 5 | 298B | DP alias DATA | 0084+8*SCB | 16 | 03F1 |
| 6 | 2991 | DP alias DATA | 0084+8*SCB | 16 | 03F6 |
| 7 | 2994 | DATA | 03F6 | 8 | H&1F |

Функціональні byte reads — лише0356 і03F1. Чотири architectural pointer
dependencies на2983/298A/298E/2994 позначені окремим access role/space.
Immediate operands, journal `before` values і generation bookkeeping не
створюють додаткових функціональних DATA reads.

Same-value write не вилучається. Кожен write має ordinal,PC,width,before/after
bytes, partial knowledge, before generation і нову conditional generation.
Проміжні snapshots і `steps` зберігають точну різницю між станом після
write і завершенням відповідної програмної дії.

## 12. Writer generations

Успадкований формат:

```text
ConditionalEffect:<procedure>:<PC>:<ordinal>
```

Це logical label моделі, не спостережений native RAM owner. Для word write
обидва DATA bytes отримують одну generation відповідної word-події.
Store значення, яке вже було у slot, однаково створює нову writer identity.

Direct continuation використовує ordinals1..7. Компонований результат
зберігає три prefix writes M2cq із первинними labels `payload_consumer`,
а нові writes продовжують global ordinals4..10. Попередній read не
переприв'язується до пізнішої generation лише через збіг address/value.

## 13. DATA03F2, DATA03F4 і conditional lineage

M2cq умовно встановлює `DATA03F2=(G+3)%256` з explicit DATA03F4 input.
Selected continuation не читає і не записує жоден із цих двох bytes.
Їхні values, partial bits і generations мають лишитися в output state.
З цього не випливають parser Length, native owner026C або serial payload.

`continuation_lineage` приймає explicit slots `{value,knownBits,generation}`
before/after, requested generation для кожного slot і `noInterference`.
Він розрізняє disjoint values, змінену generation, missing label, stale request
та зміну raw representation/explicit knowledge без source access. Навіть
однакові numeric candidate sets не приховують різниці raw scalar чи bit map.

Aliases подано лише як `aliasesIfLocalBank03F0`: F2 відповідає r2/er1.low,
F4 — r4/er2.low за такого local bank. Query не має LRB і не встановлює,
що цей bank справді вибраний. Endpoint equality сама по собі не є runtime
read або reaching-definition observation; formal reads/journal лишаються порожніми.

## 14. Композиція з consumer M2cq

```text
Explicit conditional G at03F4
  → frozen byte load28DB
  → G+3 at28DC
  → frozen store03F2 at297F
  → existing fall-through2980
  → new status/F5/H-mask/F6 effects
  → STOP before2995
```

Композиція передає повний повернений state, включно з усіма46 bytes,
generation labels, memory knownBits, AL/AH `registerKnownBits`, unchanged
registers, pointer aliases та prefix history. Вона не перебудовує state
з початкового input і не повторює297F store.

Це особливо важливо для partial G: raw AL може бути `None`, але частина
його bits після `G+3` відома. Ці bits зберігаються через2980/2983/2985 до
LB2988. Успішне математичне приєднання не доводить actual edge026C→28DB.

## 15. Еквівалентний структурований псевдокод

Нижче `data`, `write_dp`, `load_byte` і `emit_write` працюють із локальним
conditional state та journal. Вони не означають memory-mapped hardware I/O.

```text
function post_consumer_continuation(input):
    state = deep_copy_and_validate(input)
    require_no_interference_and_known_scb_or_return_prefix()

    write_dp(0356)                          // ordered word effect
    original_bit6 = read_bit(data[0356], 6)
    set_bit_preserving_unknown_neighbors(data[0356], 6, 1)
    ZF = logical_not_or_unknown(original_bit6)

    write_dp(03F5)
    require_ordinary_byte_semantics_here_or_return_prefix(2988)
    AL = 2; DD = 0; ZF = 0
    emit_write(data[03F5], AL, width=8)

    write_dp(03F1)
    require_ordinary_byte_semantics_before_operand_reads(298E)
    AL = load_byte(data[03F1]); DD = 0
    ZF = exact_zero_consensus(AL)
    AL = exact_candidate_mask(AL, 1F)
    ZF = exact_zero_consensus(AL)

    write_dp(03F6)
    emit_write(data[03F6], AL, width=8, retain_proved_partial_bits=true)
    return software_complete_at(2995,
        stbufObligations=formal_requirements_with_unknown_hardware_premises())
```

Цей псевдокод навмисно не містить `STBUF = AL`, transmit callback, CPU step
або переходу до2997. Практичний порт має реалізувати також failure prefix,
explicit masks і ordered event format, а не лише кінцеві числові формули.

## 16. Unknown і partial-bit knowledge

Byte domain є точним: відомий scalar або множина значень0..255, сумісних із
explicit bits. Arithmetic і mask використовують цей bounded exact domain,
без approximate floating-point обчислень.

Для невідомого H після `&1F` bits5..7 AL завжди відомі як0. Нижні bits
залишаються невідомими, якщо input не дає точнішої інформації. ZF дорівнює0,
коли принаймні один masked bit гарантовано1; ZF1 — коли всі нижні bits
гарантовано0; інакше він unknown. Partial F6 store переносить саме ці masks.

Raw scalar, explicit knownBits і candidate-set meaning — різні частини
канонічного результату. Їх не нормалізують заднім числом лише заради equality.
Unknown old status зберігає невідомих сусідів, а missing generation не
перетворюється на вигаданий native writer.

## 17. Early exits і збережений prefix

Модель не пропускає перевірку context, але й не стирає вже доведені effects.

- Відсутній no-interference premise зупиняє direct continuation до першого write.
- Unknown SCB відхиляє перший DP access, не вибираючи bank0.
- `ordinaryByteSemantics` перевіряється перед досягнутими LB2988 і298E.
  Refusal на2988 залишає три попередні writes і їхні steps.
- Frozen consumer refusal повертається без зміни його state/history; додається
  лише `stbufObligations:null`, а continuation не починається.
- Новий malformed typed input відхиляється як malformed; unknown legitimate
  input зберігає unknown і не підмінюється нулем.

Для composed own namespace перевіряються також ORIGINAL input generations:
label `ConditionalEffect:consumer_with_continuation:` не може сховатися після
того, як frozen prefix перезаписав DP slot або F2. Refusal на2980 зберігає
весь уже завершений consumer prefix. Retained-current-state guard також
залишається. Ці перевірки захищають logical bookkeeping, не є новими ISA
instructions і не вводять fallback до випадково обраного source path.

## 18. Exact STBUF2995 boundary

Retained instruction на2995 — descriptor-sensitive `STB A,N8`, length2,
operand N8=0051. За DD0 source — AL byte, destination — absolute zero-page
DATA0051. LRB,SCB,USP не потрібні для цього N8 address. STB не встановлює
DD0: descriptor має вже дорівнювати0, а CF/ZF/HC/DD зберігаються.

За DD1 той самий encoding є `ST A,N8`, word operation від A. Word address
0051 вирівнюється до0050 і охоплює0050/0051. Це не безпечна byte fallback
і не є дозволеною операцією M2cr. Unknown DD не підставляється як0.

OKI E2E1027-27-Y4 і J2E1027-27-Y3, page11/30, для стандартної названої family
позначають0051 як STBUF, serial transmission data buffer register: W-only,
8-bit, reset undefined. Англійський retained container має SHA-256
`fe18068dc496a03f5b6bdefe5818741e572cb7626acfb3d1df427547f8b3264b`;
японський — `9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a`.
Це manufacturer-document qualification, а не ідентифікація конкретного ECU.
R/W column не задає actual readiness, acceptance, TX start/completion чи IRQ.

## 19. Формальні STBUF2995 obligations

Closed query містить `inputClass,sourceBinding,pc,dd,prospectiveAL,
softwareReached,softwareNoInterference,premises,claim`.
`prospectiveAL` — `{value,knownBits,generation}` із explicit nullable byte,
bits0..7 і conditional label. Source binding фіксує base, обидва source
dossiers, manual identity, десять sites і exact boundary form/length/address/DD.
Shape, recursive container/scalar types і values source binding порівнюються
точно: Python-equivalent `false/0` або `2.0/2` не підмінюють typed identity.

Declared hardware premises:

```text
deviceApplicability, physicalByteAccessAndSf, accessMapping,
peripheralOwnership, transmitterReady, clockResetStconGeneration,
serialConfiguration, peripheralInterferenceExcluded,
acceptanceSemantics, irqAckCollisionSemantics
```

Жодне поле не є actual observation. Missing binding, wrong source identity,
wrong boundary, DD1, false declared premises і attempted actual write/TX/IRQ/CPU
claim мають окремі refusals. Unknown fields лишаються в ordered
`missingPremises`. Навіть all-true declarations і відомий AL можуть дати
лише `HypotheticalStbufObligationsSpecified`.

У всіх результатах `reads,journal,steps,intermediateStates` порожні;
`actualBufferWrite,actualAcceptance,actualTransmission,actualCompletion,
actualTxIrq` дорівнюють null. Немає DATA0051 latch, reset0, readback,
same-value peripheral event або software simulation передавача.

## 20. Source-qualified composition проти peripheral equivalence

Успішна continuation повертає `CompleteConditional` на2995 та nested STBUF
obligations із невідомими hardware premises. Їхня неповнота не скасовує
встановлені software effects, але й не дозволяє виконати наступну інструкцію.

AL на цій межі є prospective software value. Це не transmitted byte
observation. Native serial state, current STCON/clock/reset generations,
buffer ownership, physical SF, pending/ack/collision ordering, actual
acceptance і реакція зовнішньої лінії залишаються невстановленими.

M2cr не створює SSP/frame, не вибирає foreground return PC, не виконує RTI
і не продовжує за2995. Окрема physical-device застосовність не встановлюється
з однакових mnemonic або SFR address у двох документах.

## 21. Синтетичний приклад за source equations

Приклад є математичною ілюстрацією, а не runtime trace. Explicit premises:
SCB0, conditional DATA mapping, noInterference=true, ordinaryByteSemantics=true,
G=FD у03F4, H=21 у03F1, DATA0356=02, AH=A5. Решта необхідних slots і generations
мають бути явно задані в typed input; тут вони не замінюються прихованими нулями.

Consumer обчислює `FD+3=100`: F2=00,AL=00,CF1,HC1,ZF1,DD0 і DP03F2.
Source edge297F→2980 переносить саме цей state.

| Source дія | Програмний результат | Нові writes від2980 |
| --- | --- | ---: |
| 2980 | DP0356;AL00/AHA5 збережено | 1 |
| 2983 | status02→42;ZF1 зі старого bit6=0 | 2 |
| 2985/2988 | DP03F5;AL02;DD0;ZF0 | 3 |
| 298A | DATA03F5=02 | 4 |
| 298B/298E | DP03F1;AL21;ZF0 | 5 |
| 298F | AL01;ZF0;CF1/HC1 збережено | 5 |
| 2991/2994 | DP03F6;DATA03F6=01 | 7 |
| 2995 | STOP; prospective AL01; actual TX=null | 7 |

F2 лишається00, F4 —FD, AH —A5. Композиція має10 logical writes: три frozen
consumer writes плюс сім нових. Кінцевий byte01 походить із H, тоді як CF/HC
зберегли залежність від G+3. STBUF write не додається до таблиці подій.

## 22. Independent reference і semantic acceptance

Expected outputs мають походити від незалежного reference, який не викликає
нові model functions. Corpus, reference source bindings і full expected stream
заморожуються до першого порівняння з implementation.

Acceptance вимагає full equality стану, raw knowledge maps, sourceScope,
assumptions, ordered reads/writes, generations, проміжних snapshots,
boundaries, missing premises і authority exclusions. Однаковий final AL або
digest без побайтового comparison не є достатнім доказом.

При першій різниці зберігаються caseId, input, exact first difference і source
identities. Expected не переписується за implementation output для отримання
PASS. Source conflict і непідтверджена hardware semantics не маскуються.

## 23. Test coverage і negative controls

Domain acceptance охоплює G sweep і boundary controls, H mask/zero,
partial0356/H/AL/AH, incomingDD0/1/unknown, SCB0..7 і SCB6 alias,
same-value writes, retained CF/HC, wrong context, exact prefix on refusal,
conditional generations, no F2/F4 access, changed knowledge representation,
wrong source/descriptor/boundary і forbidden peripheral claims.

STBUF tests мають розрізняти відомий prospective operand і невідому actual
readiness/ownership; all-true premises не можуть створити actual observation.
У selected CFG немає branch, тому synthetic unknown predicate не додається
лише заради тесту. Повнота domain corpus і actual test counts установлюються
незалежними freeze/QA receipts, а не цим source document.

CI module визначає19 source-routing/publication test methods: finite new paths,
mutation кожного нового файла, immutable M2cq–M2cn sources, exact parent pin,
historical tail, malformed approved text/JSON, workflow mutations, wrong head,
controlled fresh/existing output, traversal/reparse refusals, heterogeneous full
serialization, nested false peripheral observations і exact canonical encoding.
Кількість визначень не заявляється як кількість виконаних PASS tests.

## 24. Canonical artifacts, CI, preservation і delivery

Canonical record має закритий envelope `{caseId,operation,input,output}`.
Повний output містить sourceScope, state, reads, journal, generations,
intermediate states, unresolved constraints, boundary та execution authority.
Немає field exclusions або заміни missing observations expected values.
JSON використовує sorted keys, ASCII escaping, compact separators, LF і
заборону NaN. Gzip детермінований; decompressed stream обмежений128MiB.

Validator зберігає рівно три files: `static-canonical.jsonl.gz`,
`static-summary.json`, `sourcejoin.json`. Він рахує operations/statuses за
envelopes і не видає формальні obligations за DATA reads або CPU operations.
Nested actual peripheral observations відхиляються. Independent comparison
є окремим gate; CLI не сертифікує delivery самостійно.

Finite CI overlay має15 нових public paths поверх exact1334-source M2cq,
тобто prospective1349 raw source bindings. Решта1333 parent files зберігають
bytes; змінюється лише reviewed workflow overlay. Historical workflow tail
74904 bytes не переписується. Невідомий або unreviewed change повертає
full-QA fallback; глобальні historical jobs не вимикаються.

Delivery вимагає actual routing/Ubuntu/Windows results на exact final SHA,
actual required step statuses і full decompressed expected/local/Ubuntu/Windows
byte equality разом з усіма source bindings. Historical17/Desktop лишаються
NotRun, коли фактично skipped. На момент підготовки цього source document
нові QA/CI counts і final SHA ще pending; actual verdict зберігається окремо
після завершення delivery gates.

Зберігаються п'ять попередніх preservation exceptions:3 inherited,
1 M2cn Python tooling і1 M2cp Python tooling. Нові unauthorized differences
мають дорівнювати0. Scoped preservation не є whole-storage audit і не
дозволяє `StrictHistoricalPreservationPass=true`. Історичні source/oracles,
expected streams, ROM, manifests, final reports і protected binaries не
переписуються; public CI не потребує private NAS або OEM bytes.

## 25. C++/Rust-ready port, невідомі та наступний evidence scope

Порт має чітко розділити nullable scalar, explicit bit masks, conditional
generation labels, shared byte storage, register views і event journal.
Для logical byte/word values достатньо fixed-width integer types; unknown
потребує окремого типу, а не sentinel0. DP view завжди виводиться зі shared
DATA bank, word event лишається width16, partial stores і same-value writes
зберігаються. Structured functions відтворюють source algorithm без нового
CPU emulator, instruction dispatch loop або arbitrary stepping API.

Невстановленими лишаються конкретна026C generation на consumer read,
native scheduler/foreground path, SSP/frame/RTI, exact ECU silicon/SFR
applicability, physical SF, serial lifecycle/readiness/ownership, TX acceptance,
IRQ ordering, firmware placement/integration і physical engine meaning bytes.
Локальна software equivalence не є whole-target або hardware equivalence.

Найкорисніший окремий наступний evidence scope — source-qualified applicable
STBUF/STCON transmit lifecycle та provenance його конфігурації/ownership,
зі збереженням stop-before boundary, доки не існує окремих доказів і дозволу.
Ця рекомендація не запускає M2cs, peripheral experiment або ECU execution.

Найсильніша допустима research classification M2cr після всіх source,
independent-comparison і delivery gates:

```text
CONDITIONAL_POST_CONSUMER_CONTINUATION_EQUIVALENCE_ESTABLISHED
EXECUTION_BLOCKED
FirmwareReady=false
```

Це acceptance criterion, а не передчасна заява про QA/CI PASS.
