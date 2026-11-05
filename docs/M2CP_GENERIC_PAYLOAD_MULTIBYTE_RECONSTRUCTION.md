# M2cp — Generic Payload і умовна багатобайтова реконструкція parser

M2cp додає шість pure functions у
`research/p28-word0196/generic_payload_multibyte/`: `generic_payload_body`,
`data_body`, `dispatch`, `parser_step`, `counter_route` та `compose`. Новий
source-qualified ефект 026C записує **AL у local r4**, після чого застосовується
перевірений arithmetic join. Новий composer зберігає історію довших явних
послідовностей Header/Length/Flag/Generic/Checksum.

Це умовна реконструкція програмних transformations. `steps`, source PC і
counter iterations не є actual instruction retirements. PROGRAM не
завантажується; CPU/Bus, decoder, IRQ, RTI, receiver або ECU не запускаються.
Для всіх результатів: `EXECUTION_BLOCKED`, `FirmwareReady=false`.

## 1. Прийнята база та незмінна історія

База — M2co `caf5552e4fc20e9b120726c7aa7822e75ab33aff`. Прийнятий M2co мав
шість нових functions, 86 static tests, 2034 canonical records і 41225964 bytes
з повним expected/local/Ubuntu/Windows збігом. Це історичні результати M2co,
а не результати QA нового M2cp.

Сім functions M2cn та шість functions M2co, їхні contracts, inputs, oracles і
source bindings збережено. M2cp не розширює старі registries, max-four-stage
M2co contract або його історичний `OutsideVerifiedScope` на026C. Новий пакет
повторно використовує frozen state/Effects, source transforms Header/Length/
Checksum, arithmetic join та dispatch selection через окремі адаптери.

## 2. Source audit і точна інструкція 026C

Перевірено listing/decoded extents та первинні правила OKI MSM66201 Instruction
Manual September1991. Новий закритий inventory містить **38 source sites**:
37 прийнятих M2co sites плюс026C. Локальна група:

```text
0262 LB A, DATA0055       → 0264
0264 CMPB r5, #2         → 0267
0267 JNE                 → 026C або0269
0269 STB A, r3           → 026A
026A SJ                  → 026D
026C STB A, r4           → 026D
026D ADDB r6, A          → 026F
026F INCB r5             → 0270
0270 MOVB r7, #2         → 0272
```

Source operands відображено за прийнятим `LRB=007E`, page0300 і local
DATA03F0..03F7. Opcode bytes приватного ROM не публікуються. Відношення форм,
довжин, successors і первинних сторінок зафіксовано в `contract.json`.

На026C форма **STB A,r4 має довжину1 та потребує incoming DD0**. Первинна
сторінка STB —3-155; word ST — окрема форма на3-154. Direct entry з DD1 не
можна мовчки перетворити на byte store: інша descriptor-dependent форма могла
б торкнутися paired03F4/03F5 і змінити counter. Новий direct body за DD1 або
unknown DD повертає `OutsideVerifiedScope / ByteStoreDdContextNotEstablished`
на026C до будь-якого DATA effect.

Сам STB026C не читає DATA0055, не змінює AL/AH/flags/DD і не просуває pointer.
Він створює один byte write DATA03F4=AL. Значення AL є explicit conditional
input, без native SRBUF ownership claim. Усі наступні Generic stores знову
пишуть **ту саму DATA03F4**; RAM array, address03F4+index або збереження всього
payload у сусідніх bytes з цього не випливає.

## 3. Flag і Generic — різні записи, спільний join

`data_body(snapshot)` починає на0262. Досягнутий LB читає explicit DATA0055,
встановлює AL, DD0 та ZF. CMPB0264 порівнює **r5 з2**, а не F, AL або parity.

```text
AL = DATA0055                         // ordinary-byte premise checked here
compare_unsigned(r5, 2)
if r5 != 2:
    r4 = AL                           // Generic026C
else:
    r3 = AL                           // Flag0269
    jump to026D
apply shared arithmetic join
stop before0272
```

Unknown r5 дає `IndeterminateBranch` на0267 після LB/CMP prefix, без запису r3
або r4. Невідомий F не обов'язково блокує selected path: за відомого r5 вибір
Flag/Generic встановлений; store/sum можуть залишатися unknown, а відомий
counter усе ще коректно збільшується. Unknown не підміняється нулем.

| Властивість | Flag | Generic |
|---|---|---|
| Predicate у data body | r5==2 | r5!=2 |
| Спеціальний store | 0269: DATA03F3=AL | 026C: DATA03F4=AL |
| Інший DATA byte | r4 retained | r3 retained |
| Join | SJ026A→026D | fall-through026C→026D |
| Body write order | 0269→026D→026F→0270 | 026C→026D→026F→0270 |
| Body writes | 4 | 4 |
| З parser status0222 | 5 | 5 |

`generic_payload_body(snapshot)` є окремим **direct entry026C**: він не
доводить, що dispatch обрав Generic, і не вимагає r5!=2. Будь-який typed r5
дозволений у його локальній arithmetic domain, включно з2, FF або unknown.
Його джерело — incoming AL; він не виконує LB і не потребує
`ordinaryByteSemantics` для неіснуючого читання. `data_body` натомість приймає
будь-який incoming DD, бо його власний досягнутий LB встановлює DD0.

## 4. Arithmetic, flags і aliases

Спільний join повторно використано без зміни:

```text
r6 = (old r6 + AL) modulo256           // ADDB object destination026D
r5 = (old r5 + 1) modulo256            // INCB026F
r7 = 2                               // MOVB0270
```

AL зберігається: ADDB026D має destination r6, не accumulator. CF є carry з
bit7 sum. INCB перезаписує ZF/HC після ADD, але зберігає його CF:

```text
final CF = unsigned(old r6 + AL) >255
final ZF = ((old r5+1) modulo256)==0
final HC = (old r5 &0F)==0F
```

AH, DD, MIE, OtherPSW, LRB/SCB/USP/SSP retained у локальному body. Невідомі
AL/r6 дають unknown sum/CF; невідомий r5 дає unknown increment/ZF/HC, а не1.

Формули banking залишаються frozen:

```text
page = ((LRB &1FE0)<<3) &FFFF =0300
local base = ((LRB &1FFF)<<3) &FFFF =03F0
r0..r7 = DATA03F0..DATA03F7
```

r4/r5 є low/high bytes er2; byte store026C не перезаписує counter03F5.
r6/r7 також є сусідніми bytes одного word alias, але два source stores не
зливаються у word write. AL/AH — architectural accumulator, окремий від r0/r1.
У selected local sites немає PR/SSP access; вони залишаються незалежними
explicit retained inputs без вигаданого stack frame.

## 5. Dispatch priority і status prefix

`dispatch` зберігає accepted M2co selection з0255. Колишній outcome
`FlagSelected` перейменовано на **DataSelected** на0262: це вибір block entry,
а не доказ запису кожного byte у r3.

```text
if r7==0: Header at0275
else if r5==1: Length at027F
else if (r5+1) modulo256 == r2: Checksum at0284
else: Data at0262
```

Dispatch-only не читає DATA0055 і не змінює persistent DATA. Unknown predicate
зупиняє його з prefix; наступний block не вгадується. Counter increment025D
змінює AL для compare, а не збережений r5.

`parser_step` додає accepted prefix:

```text
if DATA0356.bit1==0: outside at029D
clear DATA0356.bit6 at0222; ZF=NOT its old bit6
if old bit6!=0: outside at0227
apply dispatch priority and only the verified selected body
```

JBR021F має taken target029D. Unknown old bit6 зберігає вже зроблений clear і
partial knowledge, але не дозволяє вибір branch0225. Status write0222 — окремий
event навіть за same value. Заявлений stage role не встановлює PC: спочатку
перевіряється dispatch, а для Flag/Generic — також LB/CMP/JNE0267. Невірний
subtype повертає `DeclaredRoleDoesNotMatchDataSelection` перед store0269/026C,
зі збереженням досягнутого prefix.

Зовнішні boundaries лишаються stop-before0272 та0295. M2cp не застосовує
direct jump0272, tail0295–029C або RTI. Actual native edge0272→021F не
встановлено.

## 6. Counter/Length: точна кількість data transformations

За умовного завершення Header і Length, збереження relevant state і
фіксованого L: r7=2, r5=2, r2=L. Нехай c є r5 перед наступним dispatch.
Пріоритет **c==1 → Length** перевіряється раніше за checksum equality.
Кожна Flag/Generic transformation збільшує c рівно один раз modulo256.

Для **L!=2**:

```text
d = (L-3) modulo256
Flag count = 1 if d>0, otherwise0
Generic count = max(d-1,0)
total Header/Length/data/Checksum transformations = d+3
```

Checksum candidate c=(L-1) modulo256 досягається раніше за Length-priority
counter1. Для **L=2** після255 data transformations досягається c=1, але
наступний dispatch вибирає Length, а не Checksum. Рівність modulo сама по
собі не доводить завершення fixed-L2 sequence.

| L, decimal | Flag | Generic | Frontier counter | Frontier | Total through Checksum |
|---:|---:|---:|---:|---|---:|
| 0 | 1 | 252 | 255 | Checksum | 256 |
| 1 | 1 | 253 | 0 | Checksum | 257 |
| 2 | 1 | 254 | 1 | Length reentry | Не встановлено |
| 3 | 0 | 0 | 2 | Checksum | 3 |
| 4 | 1 | 0 | 3 | Checksum | 4 |
| 5 | 1 | 1 | 4 | Checksum | 5 |
| 6 | 1 | 2 | 5 | Checksum | 6 |
| 7 | 1 | 3 | 6 | Checksum | 7 |
| 8 | 1 | 4 | 7 | Checksum | 8 |
| 255 (FF) | 1 | 251 | 254 | Checksum | 255 |

Для L2 завершений prefix містить257 transformations разом із Header/Length;
наступна stage258 може бути явно заданим **новим Length input**, який змінить
L. Це не доводить native receive cycle або допустимість fixed-L2 packet.
Зокрема загальне правило total=L неправильне для L0/1/2.

`counter_route({length,maxDataStages})` реалізує саме цю mathematical relation.
Length — byte або `null`; maxDataStages — integer0..512, bool відхиляється.
Воно повертає counterHistory/stageOrder/counts/frontier без DATA reads/writes.
Unknown L дає `IndeterminateBranch / UnknownLengthPredicate` на comparison0260
до data history. Terminal selection перевіряється **перед** resource bound:
L3 з limit0 усе ще вибирає Checksum. Resource refusal означає
`SyntheticResourceBound_NotProtocolLimit`, а не обмеження ECU protocol.

## 7. Формування r6 і локальна checksum перевірка

Header встановлює r6=H. Length додає L. Кожний selected Flag **і** Generic byte
додається до retained r6 за тим самим source026D:

```text
r6 = (H + L + sum(source-processed Flag/Generic bytes)) modulo256
```

Це відношення потребує explicit qualified handoffs і порядку stages. Пізніший
Generic може перезаписати r4, але попередній byte уже врахований у sum. Checksum
не читає r4 як історію payload: він використовує retained r6 і header r1.

Accepted M2co Checksum transform не змінено:

```text
K = explicit DATA0055
AL = (K+r6) modulo256
if AL!=0: r7=2; ChecksumRejected at0272
else:
    AL = r1 &E0
    if AL!=20: r7=2; ChecksumRejected at0272
    else:
        set DATA0356.bit7 at0290; ZF=NOT old ready bit7
        clear r7 at0293 without changing flags
        ChecksumAccepted at0295
```

r6 і r5 retained у checksum block. Ненульовий sum short-circuits header/ready
reads. Success має AL20, CF0 від CMP, HC від sum, DD0; terminal ZF належить
**старому ready bit7**, а не zero sum. Невідомий old ready дає unknown ZF,
зберігаючи forced ready bit7=1. Rejection не очищує stale ready автоматично і
не доводить завершення або скидання фізичного receiver.

Повна формула тут обмежена явно переданими, source-processed bytes. Вона не
встановлює framing, допустимі physical lengths, native source ownership або
тотожність serial checksum з ROM-wide checksum M1f.

## 8. Короткий приклад L=6

Це **conditional synthetic software model, не запис serial traffic ECU**.
Таблицю виведено з source equations; вона не є новим execution trace.
Усі byte values нижче — hex.

Явно задано H=21, L=06, Flag=01, Generic bytes02/03, K=D3. Початкові r7=0,
r5=0, r6=00 та old r1=7A — synthetic choices, а не reset/native defaults.
DATA0356=02 явно задає mode bit1=1, error bit6=0 і old ready bit7=0. Для
кожної stage independently provided architectural inputs мають DD0 і
LRB007E; це не RTI restore inference. Невказані в прикладі fields залишаються
явними symbolic/unknown inputs повного snapshot, без прихованих нулів.

Між усіма stages передано `ConditionalPersistentStateHandoff`,
noInterference=true, exact retained memory/bits/generations та окремий
symbolic sample DATA0055. Counter before/after позначає r5; sum — r6.

| Byte | Selected role | Counter | r6 | Ordered write PCs, включно зі status | Checksum outcome |
|---|---|---|---|---|---|
| 21 | Header | 0→1 | 00→21 | 0222→0275→0279→027A→027B→0270 | Не досягнуто |
| 06 | Length | 1→2 | 21→27 | 0222→0281→026D→026F→0270 | Не досягнуто |
| 01 | Flag | 2→3 | 27→28 | 0222→0269→026D→026F→0270 | Не досягнуто |
| 02 | Generic | 3→4 | 28→2A | 0222→026C→026D→026F→0270 | Не досягнуто |
| 03 | Generic | 4→5 | 2A→2D | 0222→026C→026D→026F→0270 | Не досягнуто |
| D3 | Checksum | 5→5 | 2D→2D | 0222→0290→0293 | Accepted; stop before0295 |

Header копіює old r1=7A у r0 перед записом H. Flag встановлює r3=01. Перший
Generic встановлює r4=02, другий перезаписує **r4=03**; r3 лишається01.
Перед K counter5 дає5+1=6, тому dispatch вибирає Checksum без Generic store.
2D+D3=100hex, його low byte00; header21&E0=20. Ready змінюється02→82, r7
очищається2→0, r5/r6 retained. За explicitly old ready0 terminal ZF1, CF0,
HC1, DD0 і AL20. За unknown old ready terminal ZF був би unknown.

Усього шість stages і **29 logical writes**: Header6, Length5, Flag5, два
Generic по5, Checksum3. Повторні status clear і r7=2 stores не видалено як
same-value events. Це logical effect count, не retired instruction count.

## 9. Типи, unknown і формальні контракти

Snapshot має рівно frozen fields `inputClass, memory, knownBits, registers,
generations, assumptions`. Memory містить31 explicit byte keys, кожний byte
0..255 або null. Partial-bit map зберігає known bits невідомого цілого byte.
Adjacent word aliases little-endian; незалежно невідомий byte не заповнюється
нулем. `bool` не є допустимим byte/word/counter integer.

Assumptions: `dataMapping=ConditionalByteArray`, explicit noInterference і
ordinaryByteSemantics. Ordinary-byte premise перевіряється на досягнутому LB;
раніше встановлені writes не стираються через пізнішу відмову. Generation
labels — logical writer identities, а не native provenance.

| Function | Inputs і preconditions | Source / postcondition | Boundary |
|---|---|---|---|
| `generic_payload_body` | Snapshot, LRB007E, noInterference, DD0 | direct026C; AL→r4, sum/counter/r7 join; GenericWritten | 0272 або prefix026C |
| `data_body` | Snapshot, context; byte premise на LB0262 | r5==2 selects Flag, інакше Generic; exact join | 0272 або unknown0267/prefix |
| `dispatch` | Snapshot, context | accepted0255 priority; DataSelected на0262 | selected entry або unknown predicate |
| `parser_step` | Snapshot; status/dispatch prerequisites evaluated in order | status0222 plus verified selected Header/Length/Flag/Generic/Checksum | 0227/029D/0272/0295 або prefix |
| `counter_route` | `{length,maxDataStages}`, typed byte/null та0..512 | fixed post-Header/Length counter-priority relation; no DATA events | counter/frontier027F/0284/0260/0262 |
| `compose` | Explicit stages/transfers,1..512, first Header | conditional state handoffs і full per-stage history | first unproved boundary або final stage stop |

Local results зберігають inherited status/reason/outcome/boundary/state,
functional reads, source steps, ordered journal та intermediateStates і додають
`unresolvedConstraints`. `CompleteConditional` означає завершення requested
source transformation; `ChecksumRejected` є окремим **outcome** завершеного
local reject path, а не автоматичним OutsideVerifiedScope. Unknown predicate
дає `IndeterminateBranch`; unsupported scope/context/DD дає
`OutsideVerifiedScope` з доведеним prefix. Malformed typed request є validation
error, а не вигаданий successful path.

Frame conditions зберігають усі неоголошені DATA bytes/bits/generations і
architectural context. Кожний byte store залишається width8, зі своїм ordinal,
PC, before/after values, writer generation і value source. RMW має functional
read; звичайний store не створює фіктивного read destination. Same-value writes
залишаються окремими events.

## 10. Composer з довшими bounded sequences

Новий `compose` приймає1..512 stages `{id,role,sampleId,snapshot}` і рівно
n−1 explicit transfers. Roles: Header, Length, Flag, Generic, Checksum.
Ідентифікатори bounded/унікальні; snapshots перевіряються upfront. Множина
дозволених declared edges:

```text
Header→Length
Length→Flag, Length→Checksum
Flag→Generic, Flag→Checksum
Generic→Generic, Generic→Checksum, Generic→Length
```

Ці edges є умовними програмними handoffs, не native CFG jumps. Кожний role
додатково проходить source predicates; декларація не примушує branch. Edge
Generic→Length дозволяє явно дослідити counter-wrap reentry з новим Length
sample, не проголошуючи fixed-L2 завершення.

Transfer має exact fields `from,to,relation,noInterference,retainedGenerations`.
Потрібні relation=`ConditionalPersistentStateHandoff`, noInterference=true,
точна30-byte generation map без0055 і exact retention persistent memory,
knownBits та generations. InputClass, assumptions і LRB повинні збігатися.
Різний writer із тим самим числовим value не є retained lineage.

Architectural registers кожної stage надано незалежно явно. Composer не
виконує RTI і не формує foreground A/PSW/PC або frame. Новий DATA0055 — явно
позначений boundary input/sample, не generated receive completion, host store
або peripheral observation. No-interference premise не є спостереженням
фактичної відсутності IRQ/NMI.

Результат зберігає:

- `stages`: full local outputs, включно з intermediateStates;
- `stageBoundaries` і всі source `branchDecisions`;
- accepted `transfers` та окремі `rejectedTransfers`;
- explicit `boundaryInputs`;
- flattened journal `{stageId,globalOrdinal,event}` із незміненими local events;
- `finalState`, `checksumOutcome` і ordered `unresolvedConstraints`.

Невдалий **handoff** додає rejected transfer і не оцінює наступну stage.
Коректний handoff з подальшим local role/predicate failure залишається accepted
state transfer; у stages додається failing local prefix. Ці два види відмов
не змішуються. Unique `parser_step@id` namespaces відокремлюють conditional
generation labels; initial namespace collision відхиляється.

Complete requested prefix, наприклад один Header, може мати
`CompleteConditional` з constraint `ChecksumNotReachedWithinRequestedSequence`.
Навіть `checksumOutcome=ChecksumAccepted` описує лише останню оцінену checksum
stage, а не actual packet/ECU completion. Resource cap512 є host synthetic
admission limit; це не protocol length, timer budget або hardware capability.

## 11. Незалежний oracle, corpus і source-to-model checks

Незалежний `reference_oracle.py` формує expected results з source-qualified
правил без виклику нових model/analysis functions. Інвентар, interface і
expected stream зафіксовано до new model calls. Історичні M2cn/M2co expected
streams не переписуються.

Definitive invented/symbolic corpus містить **2017 records**: direct Generic606,
data_body606, dispatch153, parser_step49, counter_route293, compose310.
Reference-only expected stream має75842754 bytes і SHA-256
`8c6dafbd4fce5f762fdcba42dee7883e26cad3910676c02b9ad9bf3289da9753`.
Це identity підготовлених незалежних очікувань, а не майбутній QA PASS.

Відокремлено63 domain tests і19 CI/publication controls. Coverage включає
повні byte sweeps, direct DD0/1/unknown, r5=2/3/4/FE/FF/unknown, modulo і
same-value stores, AL/AH/CF/ZF/HC/DD, partial knowledge, exact branch/source
ordering, long L0/1/2/FF controls, explicit L3..8 sequences, accepted/rejected
checksum, conflicting/missing generations, bank/role mismatch і handoff refusals.
Negative controls не дозволяють Generic писати r3, втратити sum/increment,
coalesce writes, підставити unknown або перетворити symbolic sample на IRQ/ROM
execution evidence. Фактичні результати QA засвідчуються завершеними receipts.

Наявність JSON contract або green tests сама по собі не доводить source mapping.
Окремий correspondence review має перевірити instruction forms, descriptor DD,
addresses, predicates, intermediate flags, aliases, exact prefix/stop і bounded
composition. `firstMismatch` належить independent full-output comparison gate;
expectations не коригуються за actual model output для отримання PASS.

## 12. Canonical publication і research-only CI

Canonical envelope — `{caseId,operation,input,output}`. Усі нові output fields,
unknown, reads, journals, generations, rejected transfers, intermediate states,
boundaries і unresolved constraints залишаються в serialization. Формат:
sorted keys, compact ASCII JSON, no NaN і один newline на record; жодних
canonical field exclusions.

`validate_generic_payload_multibyte.py` читає count з точного source-bound
contract, перевіряє source до/після calculations та publication і створює рівно
три artifacts: `static-canonical.jsonl.gz` з gzip mtime0,
`static-summary.json`, `sourcejoin.json`. Counter relation має пусті reads/
journal; composition flat journal рахується один раз, без повторного додавання
stage-local copies. CLI не сертифікує independent equivalence або delivery.
Canonical size cap128MiB — bounded publication policy.

Finite overlay допускає14 нових research/doc/validator files та exact workflow
router/static blocks. База1304 sources дає1318 bindings;1303 inherited files і
historical workflow tail74904 bytes залишаються незмінними. Approved literal
new-source fingerprint потрібен для static-only route. Runtime/inherited/
unknown/unapproved source або routing error зберігає full historical QA fallback.

CI output-overwrite tests використовують controlled TemporaryDirectory і
patched isolated ROOT: fresh owned path спочатку приймається, потім тест явно
створює його й перевіряє `FreshOutputRequired`. Жодна перевірка не залежить від
існування локального private planning directory у checkout.

Delivery порівнює **повні decompressed expected/local/Ubuntu/Windows canonical
bytes**, unique IDs, summary identities і всі1318 raw source bindings. Digest
не підміняє byte comparison. Actual test counts, exact final SHA, job/step
statuses, firstMismatch і verdict встановлюють completed receipts та фінальний
звіт. Historical17/Desktop залишаються NotRun, якщо їх фактично не запускали.

## 13. Preservation і unresolved authority

M2cp не змінює production CPU/Bus/decoder/Exec, runtime admissions, GUI,
firmware tools, приватний ROM або frozen research sources. Historical manifests,
old expected outputs і QA evidence не перебазовуються. Історичні три inherited
exceptions та попередній Python tooling exception обліковуються окремо;
поточні tooling/preservation decisions і будь-які нові exceptions потребують
окремої authority та фінальних audit receipts.

Кожний local result зберігає базові constraints:
`ActualEcuEquivalenceNotEstablished`, `NativeReentryEdgeNotEstablished`,
`PhysicalSFNotEstablished`, `PeripheralReceiveLifecycleNotEstablished`.
Failure reasons і unresolved checksum boundary додаються без приховування.
PSWH self-destination ZF precedence, IE polarity conflict, RX READY
ACK/reassertion, native ownership/frame safety, physical memory/SFR semantics,
ECU identity і firmware integration цим scope не закриваються.

## 14. C++/Rust readiness і наступний scope

Port може мати `Option<u8>` / `optional<uint8_t>`, explicit partial-bit map,
closed Role/Status/Outcome types і immutable typed Snapshot. Word aliases
представляйте little-endian byte pairs без default-zero для unknown. Carry і
half-carry обчислюйте у ширшому unsigned intermediate перед modulo8 звуженням.
Застосовуйте flags у source order: ADD → INCB; checksum ADD → mask/CMP → SB.

Високорівневий sequence processor може перебирати bounded explicit stages,
перевіряти transfer premises і викликати source-qualified pure transformations.
Він не повинен приховано створювати новий DATA0055, RTI context або while-loop
реального serial receiver. Зберігайте ordered same-value events, окремі local/
global ordinals, early prefix і різницю між rejected handoff та rejected checksum.

Майбутній bounded differential experiment міг би зіставляти reconstructed
functions з reviewed instruction sequence на однакових admitted states:
DD-dependent forms, intermediate registers/flags, functional accesses і writes,
exact stop boundaries. Для такого execution потрібна окрема authority; M2cp
її не надає.

Наступний evidence-driven scope — source-qualified реконструкція post-checksum
tail0295–029C та його context/return obligations або окремий аналіз споживачів
останнього r4 payload value. Це рекомендація для M2cq, а не початок нового
milestone. Actual ECU equivalence, runtime, GUI і hardware залишаються
невстановленими та заблокованими.
