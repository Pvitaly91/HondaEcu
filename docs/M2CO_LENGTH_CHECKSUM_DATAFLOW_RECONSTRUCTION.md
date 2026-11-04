# M2co — умовна реконструкція Length/Checksum dispatch і передачі стану

M2co додає шість чистих програмних функцій у
`research/p28-word0196/length_checksum_dataflow/`: `header_body`, `length_body`,
`checksum_body`, `dispatch`, `parser_step` та `compose`. Вони перетворюють явно
заданий типізований стан за перевіреними ефектами інструкцій. Це високорівневі
алгоритми та журнали умовних ефектів, а не CPU emulator або serial receiver.

База — прийнятий M2cn `eb4fed49ccea39e8b08ea116d84aafa8da026956`,
`CONDITIONAL_FLAG_AND_MASK_EQUIVALENCE_ESTABLISHED / EXECUTION_BLOCKED`.
Його сім функцій, state contract, oracle, корпус 1744 випадків і source bindings
залишаються незмінними. M2co повторно використовує frozen `Effects`, `validate`
та selected Flag body через нові адаптери. Новий validator та CI guard мають
окремі source identities.

Статус виконання всіх нових функцій — `EXECUTION_BLOCKED`;
`FirmwareReady=false`. Чисте обчислення не створює PROGRAM fetch, instruction
retirement, CPU/Bus instance, IRQ, RTI чи hardware observation.

## 1. Джерела та межі доказу

Новий `contract.json` є закритим переліком source-qualified відношень. Його
`instructionEvidence` зв'язує **37 source sites** з reviewed instruction forms,
довжинами, первинними сторінками ISA та локально перевіреними listing/extent
identities. JSON фіксує походження; сам по собі він не надає runtime authority.

Використано вже прийняті M2cj/M2ck parser/context facts, M2cn Flag/status
relationships, M2aw banking/alias rules і OKI MSM66201 Instruction Manual
September 1991. Первинні правила нових форм включають ADDB accumulator/object
(3-16/3-17), ANDB accumulator (3-24), CLRB (3-34), CMPB (3-39), conditional
jumps (3-66), MOVB (3-99) і SB (3-127). Формули очікувань не походять з output
нової моделі або production CPU.

| Група | Source sites |
|---|---|
| Status і dispatch | 021F, 0222, 0225, 0255, 0256, 0258, 0259, 025B, 025D, 025F, 0260 |
| Frozen Flag prefix/body | 0262, 0264, 0267, 0269, 026A |
| Спільний join | 026D, 026F, 0270 |
| Header | 0275, 0277, 0279, 027A, 027B, 027D |
| Length | 027F, 0281, 0282 |
| Checksum-related block | 0284, 0286, 0287, 0289, 028A, 028C, 028E, 0290, 0293 |

`steps` називають ці source sites як математичні witnesses. Це не actual CPU
trace. PROGRAM і DATA address spaces не об'єднуються; у пакет не завантажується
ROM image, opcode stream або emulator decoder.

Закриті stop-before boundaries: **0227, 026C, 0272, 0295, 029D**. На 0272
розташований зовнішній direct jump; він не застосовується новою моделлю. Tail
0295–029C, включно з RTI, не є частиною M2co transformations. Історичне знання
про tail не створює нового права його виконувати.

## 2. Типи стану та контекст

Snapshot має рівно frozen M2cn fields:

```text
inputClass, memory, knownBits, registers, generations, assumptions
```

Байт — ціле 0..255 або `null`; word — два окремі little-endian bytes з
незалежним knowledge. `bool` не приймається замість integer. `knownBits`
зберігає доведені біти невідомого цілого байта. `null` ніколи не замінюється
нулем. Generation — `null` або непорожня логічна мітка; вона не є native
ownership evidence.

Класи входів: `SyntheticTestInput`, `SymbolicInput`,
`ManufacturerSourceQualifiedState`. Останній позначає джерело умовного опису,
а не фактичне спостереження ECU.

Для цих source addresses потрібен `LRB=007E`:

```text
current page = ((LRB & 1FE0) << 3) & FFFF = 0300
local base  = ((LRB & 1FFF) << 3) & FFFF = 03F0
r0..r7      = DATA03F0..DATA03F7
```

У вибраних 37 sites немає pointing-register або stack access. SCB, USP, SSP і
непов'язані регістри зберігаються як explicit input obligations, без створення
frame. A/AL/AH відокремлені від local rN. `er0` містить r0/r1, `er1` — r2/r3,
`er2` — r4/r5, `er3` — r6/r7. Сусідні byte stores не перетворюються на word store.

Frozen DATA scope має 31 byte; нові функції фактично використовують DATA0055,
DATA0356 та DATA03F0..03F7. Інші inventoried bytes залишаються у snapshot і
frame conditions. Модель не доводить фізичну RAM/SFR applicability цих доступів.
`ordinaryByteSemantics` та `noInterference` — явні умовні premises. Вимога до
ordinary byte перевіряється на досягнутому LB, тому вже встановлений prefix
не втрачається за відмови пізніше.

## 3. Dispatch CFG і порядок predicates

`dispatch(snapshot)` починає лише з 0255 та повертає selected role і boundary.
Воно не читає DATA0055 і не виконує selected body.

```text
AL = r7                         // LB0255, DD=0
if AL == 0: return HeaderSelected at 0275

AL = r5                         // LB0258
compare_unsigned(AL, 1)          // CMPB0259
if equal: return LengthSelected at 027F

AL = (AL + 1) modulo 256         // ADDB025D, no r5 store
compare_unsigned(AL, r2)         // CMPB025F
if equal: return ChecksumSelected at 0284
return FlagSelected at 0262
```

`r2` є байтом, записаним Length; `r5` є явно збереженим counter, а `r7` бере
участь у zero/nonzero gate. Dispatch не вимагає, щоб будь-яке ненульове r7
дорівнювало 2. Вираз `(r5+1)` обмежений 8 bits: FF переходить у 00. Це зміна AL,
а не прихований запис counter.

`parser_step(snapshot)` додає status prefix з 021F перед тим самим dispatch:

```text
if DATA0356.bit1 == 0: OutsideVerifiedScope at 029D
oldBit6 = DATA0356.bit6
DATA0356.bit6 = 0                 // separate RMW0222; ZF = NOT oldBit6
if oldBit6 != 0: OutsideVerifiedScope at 0227
select role through dispatch
apply only its verified source transformation
```

Правильний taken target JBR021F — **029D**: following PC 0222 плюс signed
displacement 7B. Status clear0222 — окремий persistent event навіть за
незмінного цілого байта. Якщо old bit6 невідомий, запис відбувається, але
подальший predicate0225 є `IndeterminateBranch`; модель не вибирає шлях.

За Flag selection застосовується frozen M2cn body: 0262 читає F, CMPB0264
порівнює **r5 з 2**, JNE0267 веде до 026C за нерівності. Parity F не визначає
store0269. За r5=2: r3=F, r6+=F modulo256, r5=3, r7=2; selected parser path має
п'ять persistent writes разом зі status0222. Generic payload store026C не
реконструюється.

## 4. Header: старий r1 перед новим байтом

`header_body(snapshot)` є direct-entry transformation 0275, без status gates
або доказу, що dispatch уже обрав цей role.

```text
r0 = old r1                     // 0275, before the next LB
H = explicit DATA0055            // LB0277
r1 = H                          // 0279
r6 = H                          // 027A
r5 = 1                          // 027B
r7 = 2                          // 027D joins 0270
return HeaderWritten, stop before 0272
```

Це п'ять окремих ordered writes. Старе r1 читається до перезапису. Невідомий H
не робить r5/r7 невідомими; вони є literal stores. Якщо premise для LB0277
не встановлена, вже застосований запис r0 зберігається у результаті prefix.
Після успішного body AL=H, DD0, ZF=(H==0), CF/HC retained, AH retained за
ordinary-byte premise. r2/r3 не змінюються.

Назва Header випливає з цих source-qualified data-flow roles; історичний
коментар listing окремо не вважається доказом framing або packet validity.

## 5. Length: byte copy, sum і counter

`length_body(snapshot)` починає на 027F:

```text
L = explicit DATA0055            // LB027F
r2 = L                          // 0281
r6 = (old r6 + L) modulo 256     // 0282 joins ADDB026D
r5 = (old r5 + 1) modulo 256     // INCB026F
r7 = 2                          // 0270
return LengthWritten, stop before 0272
```

ADDB026D має **object destination r6**: AL залишається L. Його CF є carry з
bit7, а тимчасові ZF/HC належать sum. Наступний INCB026F змінює ZF за новим
r5 і HC за carry з його low nibble; CF від sum зберігається. Отже direct body
має фінальні:

```text
AL=L; DD=0; CF=(old r6+L > 255)
ZF=((old r5+1) modulo256 == 0)
HC=((old r5 & 15) == 15)
```

AH, OtherPSW, SCB та невикористані bytes retained. Чотири persistent writes
стосуються r2, r6, r5, r7; r3 не перезаписується через er1 alias. За dispatch
precondition r5=1 результат r5=2 і ZF0/HC0. Direct entry не має такого
precondition: воно правильно зберігає загальний modulo increment. Байт L=0
або FF є typed arithmetic input; це не твердження про допустиму довжину
реального protocol packet.

## 6. Checksum-related local algorithm

`checksum_body(snapshot)` починає на 0284. Встановлено конкретну локальну
modulo8 перевірку sum і class guard:

```text
K = explicit DATA0055            // LB0284
AL = (K + retained r6) modulo256 // accumulator destination ADDB0286
if AL != 0:                     // JNE0287
    r7 = 2                      // 0270
    return ChecksumRejected at 0272

AL = retained r1                 // LB0289
AL = AL & E0                    // ANDB028A
compare_unsigned(AL, 20)         // CMPB028C
if AL != 20:                    // JNE028E
    r7 = 2
    return ChecksumRejected at 0272

DATA0356.bit7 = 1                // SB0290, ZF = NOT old bit7
r7 = 0                          // CLRB0293, does not set ZF
return ChecksumAccepted, stop before 0295
```

**r6 не змінюється** в жодній гілці цього block. Збережений header class —
`(r1&E0)==20`, тобто bytes 20..3F; він не звужується до одного control H=21.
За ненульового sum читання r1 взагалі не досягається.

ADDB0286 встановлює CF/ZF/HC sum. ANDB028A змінює AL/ZF, але зберігає CF/HC.
CMPB028C встановлює CF/ZF unsigned compare, зберігає HC. У success result
AL=20, CF0, DD0; HC належить sum, а **terminal ZF дорівнює complement старого
ready bit7**, не ZF від checksum sum. Якщо old ready bit невідомий, terminal
ZF також невідомий. CLRB0293 зберігає flags; запис zero не означає ZF1.
Зокрема локальна acceptance не вимагає CF1 від sum: K=0 і r6=0 є zero sum
із carry0.

За unknown sum модель зупиняється на predicate0287 без header read і без
acceptance writes. За unknown header class вона зупиняється на028E з
підтвердженим попереднім prefix. Success має два writes: RMW0356 і byte
clear03F7. Rejection має один write03F7=2. Попередній ready bit не очищується
автоматично при Header, Length або rejection.

Локальна sum/class перевірка є встановленим checksum-related алгоритмом.
Загальна формула довільного serial packet, валідний packet length, framing,
Receive Completion і тотожність ROM-wide checksum M1f з цього не випливають.

## 7. Ordered effects і невідомі

| Transformation | Body write order | Body count | З parser status0222 |
|---|---|---:|---:|
| Header | 0275→0279→027A→027B→0270 | 5 | 6 |
| Length | 0281→026D→026F→0270 | 4 | 5 |
| Flag | 0269→026D→026F→0270 | 4 | 5 |
| Checksum rejected | 0270 | 1 | 2 |
| Checksum accepted | 0290→0293 | 2 | 3 |

Кожний write має source PC, space, address, width, before/after bytes,
ordinal, kind, valueSource, before/after generation та conditional class.
Same-value write залишається окремим event і новою generation. RMW містить
окремий functional read. Звичайний store не створює фіктивний functional read
destination лише для побудови before-value у журналі.

Known bit forcing працює без вигаданого whole byte: clear/set зберігає
невідомі сусідні біти і фіксує лише target bit. Арифметика з unknown operand
консервативно дає unknown arithmetic result/flags. Unknown predicate повертає
`IndeterminateBranch` з точним досягнутим prefix; він не є дозволом обрати
зручну гілку.

У нових функціях немає PSWH destination. Frozen M2cn проблема precedence
ZF update проти запису в self-alias PSWH залишається невстановленою; M2co
її не вирішує. Physical SF, IE polarity conflict і RX READY ACK/reassertion
також збережено як unresolved.

## 8. Формальні контракти функцій

| Function | Preconditions і source entry | Transformation / postcondition | StopBoundary |
|---|---|---|---|
| `header_body` | Typed snapshot, LRB007E, noInterference; 0275 | old r1→r0, H→r1/r6, r5=1/r7=2; HeaderWritten | 0272 або досягнутий unknown/premise prefix |
| `length_body` | Typed snapshot, LRB007E; 027F; byte premise на LB | L→r2, modular sum та counter; LengthWritten | 0272 або prefix |
| `checksum_body` | Typed snapshot, LRB007E; 0284 | read-only r6 sum/class guard; accepted/rejected/unknown | 0295/0272/досягнутий predicate |
| `dispatch` | Typed snapshot, LRB007E; 0255 | only source-qualified role selection; no0055 read | 0275/027F/0284/0262 |
| `parser_step` | Typed snapshot, LRB007E; 021F | status, dispatch, selected verified body | 0227/029D/026C/0272/0295 або unknown predicate |
| `compose` | Closed stages/transfers; explicit qualified handoffs | ordered conditional transformations with retained persistent state | first unproved boundary або останній local stop |

Кожний local result містить status/reason/boundary/outcome, inputClass,
assumptions, state, reads, steps, ordered journal та intermediate states.
`CompleteConditional` означає завершення лише вибраної перевіреної
transformation. `OutsideVerifiedScope` зберігає доведений prefix.
Невірний typed input є validation error, а unknown branch є формальним
результатом. Жоден result не заявляє виконання tail або peripheral access.

FrameConditions: поза явно переліченими DATA writes snapshot bytes,
partial bits і generations retained. Register effects обмежені AL і
підтвердженими CF/ZF/HC/DD; AH та інші register/context values зберігаються
за явних умов. Direct entry та full parser entry мають різні prefix/flags
і не підміняють одне одного.

## 9. Умовні Header→Length→Flag→Checksum relationships

Header встановлює r7=2/r5=1, тому наступний **умовний** dispatch вибирає
Length за збереження relevant state. Після Length r5=2, r2=L:

```text
L == 3: next dispatch selects Checksum before any Flag read
L != 3: next dispatch reaches Flag; r5==2 permits store0269
```

Після Flag r5=3. Наступний dispatch вибере Checksum лише за r2=4. Тому
qualified чотиристадійний ланцюг має L=4 і накопичення r6=(H+L+F) modulo256.
У цьому обмеженому conditional composition локальна acceptance дорівнює:

```text
(H + 4 + F + K) modulo256 == 0  AND  (H & E0) == 20
```

Для L=3 існує окрема Header→Length→Checksum composition без Flag writer.
Для інших L зв'язок Flag→Checksum не підставляється автоматично. Типізовані
byte inputs не перетворюються на загальну специфікацію packet protocol.

Між stop0272 і новим parser entry021F **не встановлено native CFG edge**.
M2co описує окреме явне abstract handoff відношення; цілісність окремої
функції не доводить цілісність цього переходу.

## 10. `compose`: explicit state transfer

Request має рівно `stages` і `transfers`. Від однієї до чотирьох stages
містять `{id,role,sampleId,snapshot}`; role — Header/Length/Flag/Checksum.
`id` і `sampleId` у своїх множинах унікальні, ASCII і bounded. Перша stage
повинна бути Header. Дозволені role edges:

```text
Header → Length
Length → Flag
Length → Checksum
Flag   → Checksum
```

Кожне edge додатково проходить справжні математичні dispatch predicates;
заявлений role не встановлює PC і не примушує source branch. За розходження
модель повертає `DeclaredRoleDoesNotMatchDispatch` перед selected body,
зберігаючи вже досягнуті status/dispatch effects.

Для кожного boundary потрібен explicit transfer:

```text
from, to,
relation = ConditionalPersistentStateHandoff,
noInterference = true,
retainedGenerations = exact prior map for the 30 DATA bytes except0055
```

Наступний snapshot повинен точно зберігати попередні persistent memory,
knownBits і generations, за винятком DATA0055/його bits. Мають збігатися
inputClass, assumptions і LRB. Наявність однакових числових values при
іншій generation не є успішним lineage match.

Architectural registers для кожної stage задаються окремо явно. `compose`
не виводить їх з уявного RTI, не створює stack frame й не видає локальні
AL/PSW mutations першої stage за справжній foreground context другої.
Ця відмінність потрібна, бо source-level persistent RAM handoff сам по собі
не доводить architectural restore.

Новий DATA0055 задається користувачем моделі в окремому labelled snapshot.
`boundaryInputs` класифікує його як
`ExplicitSymbolicBoundaryInput_NotPeripheralObservation`. Це не host store
у журналі інструкцій, не receive completion і не сформований моделлю serial
byte. Якщо boundary не прийнятий, наступний body не застосовується.

Compose result містить local stage results, accepted transfers, boundaryInputs,
finalState і flattened ordered journal. Wrapper `{stageId,globalOrdinal,event}`
зберігає event незмінним. Локальний ordinal залишається локальним;
globalOrdinal безперервно визначає порядок composition. Generation tokens
мають namespace `ConditionalEffect:parser_step@<stageId>:...`; вхідна
колізія такого namespace відхиляється.

Відсутній relation, невстановлений noInterference, overwritten memory,
втрата writer lineage або incompatible context дають `OutsideVerifiedScope`
на boundary без вигаданих downstream effects. Failure не видаляє вже
одержані stage results і journal prefix.

## 11. Незалежна перевірка і canonical records

`reference_oracle.py` та його explicit corpus є окремою реалізацією очікувань
із frozen source obligations. Oracle не повинен викликати model functions
для expected values. `source_tests.py` перевіряє domain semantics, source/CFG,
unknown propagation, aliases, ordered reads/writes і handoff refusals.
`ci_tests.py` перевіряє routing/publication controls на source maps і малих
invented publication fixtures, без CPU або historical suite runs.

Підготовлений незалежний invented/symbolic corpus містить **2034 records**:
Header 266, Length 547, Checksum 781, dispatch 96, parser_step 43, compose 301.
Це розмір закритої області перевірки, а не твердження про її PASS. Вона
охоплює byte boundaries і modulo overflow, відомі/невідомі branch inputs,
direct та parser-selected контексти, same-value effects, часткові bits,
accepted/rejected checksum paths і substantive handoff/lineage відмови.

Canonical record має `{caseId,operation,input,output}`. Serialization:
sorted keys, compact separators, ASCII escapes, no NaN, один newline на
record. Жодні unknown fields, state generations, intermediate states,
stop boundaries або journals не виключаються з порівняння. Actual static
records порівнюються з незалежним expected stream у повному обсязі;
`firstMismatch` належить окремому comparison gate.

Validator `validate_length_checksum_dataflow.py` публікує рівно:

- `static-canonical.jsonl.gz`, з gzip mtime=0;
- `static-summary.json`, із фактичними operation/status/effect і byte counts;
- `sourcejoin.json`, із повними source bindings.

Для composition summary враховує flattened journal лише один раз; stage-local
copies не додаються вдруге. Functional read counts обчислюються зі stage
results. CLI не оголошує незалежний oracle comparison або delivery PASS
самостійно. Достовірні test counts, byte counts, actual CI statuses та final
verdict фіксуються у завершених delivery receipts і приватному фінальному
звіті; їх не замінює наявність цього документа.

## 12. Research-only CI та preservation

M2co CI overlay дозволяє лише 16 нових research/doc/validator files і точну
заміну routing/static job blocks. База містить 1288 tracked sources;
1287 inherited files зберігаються byte-for-byte, а historical workflow tail
від `historical-pinned-qa` залишається незмінним. Весь прийнятий M2cn package
є inherited source; він не переписується заради нових checks.

Окремо перевірений literal new-source fingerprint потрібен для static lane.
Unknown path, inherited/runtime edit, unapproved new source, неправильна
workflow projection або routing error повертають full historical QA fallback.
Немає нового глобального Skip, Windows disable або заміни production tests.
Actual routing decision і exact-SHA success встановлюються лише run receipts.

Ubuntu/Windows static artifacts мають однакову closed membership. Delivery
порівнює **повні decompressed canonical bytes** expected/local/Ubuntu/Windows,
а також source bindings; збігу одного digest недостатньо. Historical17 і
Desktop обліковуються як NotRun, якщо їх не запускали у відповідному lane.

Три inherited preservation exceptions та окремий раніше дозволений Python
tooling exception залишаються окремими історичними категоріями. Новий guard
не створює нових tooling exceptions і не перебазовує старі protected hashes.
Фактичні unauthorized differences визначає scoped preservation audit.
Private ROM, proprietary manuals, raw dumps та sensitive local artifacts
не входять у public source або CI artifacts.

## 13. Перенесення на C++ або Rust

Port може бути звичайною pure library: `Byte = optional<uint8_t>` /
`Option<u8>`, окремі partial-bit maps і explicit generation labels. Word слід
представляти парою independently-known bytes; не можна втрачати частково
відоме слово через перетворення у host integer.

Рекомендовані типи: immutable `Snapshot`, closed `Role`, tagged `Status`,
`SourceBoundary`, `DataRead`, `WriteEvent`, `LocalResult`, `StageRequest`,
`TransferPremise`, `CompositionResult`. Використовуйте unsigned modulo8
arithmetic; CF/HC обчислюйте з ширшого unsigned intermediate перед звуженням.
ZF/HC після INCB і SB застосовуйте в source order. Native integer overflow,
signed comparisons, default zero для unknown і event deduplication змінюють
доведену semantics та не є допустимими port optimizations.

Не об'єднуйте r2/r3 або r6/r7 stores у word store; не ототожнюйте local r0/r1
із AL/AH. Окрема pure selection function і body functions зберігають різницю
між direct entry та parser-selected execution relation. При unknown
predicate повертайте prefix result, а не exception, що стирає effects.

Майбутній differential checker може звіряти ці source-qualified functions
з дозволеним bounded instruction experiment: exact initial state, CFG,
intermediate flags, reads, writes, generations і stops. Це окремий майбутній
evidence step з новою authority. M2co сам не виконує ROM і не встановлює
target-program або physical ECU equivalence.

## 14. Залишкові межі і наступний bounded scope

Не встановлено generic payload026C behavior, actual transition0272→021F,
packet framing/receive lifecycle, RX READY ACK/reassertion, native writer
ownership, IRQ/RTI/frame safety, physical SF, IE polarity, ECU silicon
applicability, physical SFR semantics або firmware integration. Нові чисті
функції не усувають цих blocker categories.

Обґрунтований наступний scope — окрема source-qualified реконструкція
generic payload branch026C та її counter/accumulator/length relationships,
з перевіркою ранніх exits і меж packet validity. Це рекомендація для M2cp,
а не автоматично розпочате завдання. Runtime, GUI, firmware і hardware
залишаються поза authority M2co.
