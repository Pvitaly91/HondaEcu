# M2cn — умовна програмна реконструкція Flag та Mode/Shadow

Реалізовано чисті високорівневі функції для двох bounded source fragments:
Flag producer та перемикання/перевірка software masks. Вони приймають явні
значення або unknown, обчислюють доведені conditional effects і повертають
ordered journal та стан. Вони не читають ROM, не створюють CPU/Bus і не
відтворюють апаратну периферію.

Прийнята база — M2cm `bd00992a55d89be84ea797b12d38223996dcb999`.
Гілка — `codex/p28-word0196-conditional-flag-mode-shadow-m2cn`.
Final SHA — commit, який містить цей документ і reviewed package. Exact commit,
normal push, фактичні QA/CI counts та canonical comparison належать completed
delivery receipts і фінальному українському звіту; цей source документ не
оголошує майбутні перевірки виконаними і не містить самопосилального final hash.

`EXECUTION_BLOCKED`; `FirmwareReady=false`. Нові CPU/ROM/IRQ/RTI executions,
instruction retirements, hardware/GUI experiments і firmware outputs — 0.
Успішна перевірка цих функцій не встановлює actual ECU silicon, native owners,
RX acknowledgement, safe stack/frame або actual foreground return.

## Вихідні джерела та їхня застосовність

Повторно використано source-qualified результати
[M2cj](https://github.com/Pvitaly91/HondaEcu/blob/bd00992a55d89be84ea797b12d38223996dcb999/docs/M2CJ_RXREADY_IRQ000A_SINGLE_INVOCATION.md),
[M2ck](https://github.com/Pvitaly91/HondaEcu/blob/bd00992a55d89be84ea797b12d38223996dcb999/docs/M2CK_RXREADY_ACKNOWLEDGEMENT_REASSERTION.md),
[M2cl](https://github.com/Pvitaly91/HondaEcu/blob/bd00992a55d89be84ea797b12d38223996dcb999/docs/M2CL_ACTUAL_ECU_SILICON_APPLICABILITY.md)
і [M2cm](https://github.com/Pvitaly91/HondaEcu/blob/bd00992a55d89be84ea797b12d38223996dcb999/docs/M2CM_ECU_ROM_PROVENANCE_BRIDGE.md).
Retained listing і existing decoded extents зіставлено статично, без нового
CPU execution. Ідентичності приватних джерел залишаються у private receipts;
OEM opcode bytes, ROM names/fingerprints/download paths не публікуються.

Первинна ISA — MSM66201 Instruction Manual, First Edition September1991,
SHA-256 `f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271`.
Повні relevant primary pages перевірено в їхньому source scope. Вони не
встановлюють застосовність customer-specific peripherals до невідомого ECU.

| Ефект моделі | Manufacturer printed locator | Межа |
|---|---|---|
| LB A,obj |3-70| AL byte, DD0, ZF від zero; ordinary byte-load qualification для AH/SF |
| L A,obj |3-69| Повний word у A, DD1, ZF від word zero |
| ST/STB |3-154/155| Word за DD1 / byte за DD0, flags не змінюються |
| MOV obj,#word; MOV X1,obj |3-86/91| Literal word / selected X1 write, flags і DD збережено |
| MOVB rN,obj / immediate byte |3-99/96| Byte writes без зміни flags |
| CMP A,obj; CMPB obj,#byte |3-35/42| Unsigned subtraction relation; CF/ZF, operands retained |
| ADDB obj,A; INCB obj |3-17/61| Modulo256; у ADD CF/ZF/HC, у INC ZF/HC із retained CF |
| RB/SB direct bit |3-114/127| ZF від старого біта; потім RMW clear/set, інші flags retained |
| ANDB/ORB obj,#byte |3-27/110| PSWH допускається як operand; ZF affected, self-destination precedence окремо unknown |
| CLR/CLRB |3-32/34| Окремий clear destination; A/flags збережено для reviewed non-A targets |
| JBR/JBS, conditional branch, SJ/J |3-64/65/66/140/62| Source predicates, signed relative displacement або explicit transfer; flags retained |

Numeric retirement counts не конвертуються у фізичний час. Невирішений JGT C8
predicate не використано в жодному selected M2cn branch; його conflict збережено.

## Контракт вхідного стану

Пакет `research/p28-word0196/conditional_flag_mode_shadow/` відокремлений від
production executor. Public functions:

- `flag.status_clear(snapshot)` — окремий RMW0222, stop-before0225.
- `flag.flag_body(snapshot)` — entry0262, selected Flag branch, stop-before0272.
- `flag.flag_path(snapshot)` — entry021F із selected dispatch/status/body guards.
- `mode.initial_pair(snapshot)` —54DD..54F0, stop-before54F2.
- `mode.mode_switch(snapshot)` — один closed3EEA..3F45 pass, stop-before3F47.
- `mode.consistency_check(snapshot)` —3E81 checks, stop-before3EA7 або24E0.
- `mode.mask_hypotheses(snapshot)` — лише source-qualified Set1/Set0 bit interpretation.

Snapshot має `inputClass`, closed byte `memory`, sparse `knownBits`, explicit
`registers`, per-byte input `generations` і `assumptions`. Числа typed: bool не
вважається integer; byte/word/bit domains перевіряються; missing або extra
authority fields відхиляються. `None` означає unknown, ніколи прихований zero.

Розрізняються `SyntheticTestInput`, `SymbolicInput`,
`ManufacturerSourceQualifiedState`, `ConditionalRomEffect` та actual observation.
Перші класи — заявлений scope математичного input. Вони не створюють actual
hardware observation чи physical ownership; result завжди має
`actualHardwareObservation=null`.

Formal preconditions:

| Умова | Область |
|---|---|
| `noInterference=true` | Closed pure transformations; це premise, не доказ відсутності IRQ/NMI |
| `dataMapping=ConditionalByteArray` | Абстрактні DATA accesses; не actual writable RAM/SFR/map proof |
| LRB007E | Flag: page0300, local03F0..03F7 |
| LRB0040, SCB0 | Mode/check: page0200, local0200..0207; selected PR0080..0087 |
| USP0180 | Лише коли досягнуто3F05 або3F34; no-switch short circuit може не вимагати його |
| `ordinaryByteSemantics=true` при LB | Звичайний readable byte з AL update та retained AH; physical SF mapping не задається |

`currentPage=((LRB&1FE0)<<3)&FFFF`,
`localBase=((LRB&1FFF)<<3)&FFFF`; PR base=`0080+8*SCB` із offsets0/2/4/6 для
X1/X2/DP/USP. Обрані contexts є явними technical/symbolic premises, не native ABI.
Непідтриманий/null context повертає `OutsideVerifiedScope` до effects на entry.
Непідтверджений USP зупиняє лише досягнутий dependent site зі збереженим prefix.

Вхідний `otherPsw` не може дублювати named flags/MIE/SCB. Unknown retained state,
генерації або SSP не заповнюються нулями. Missing prior generation не заважає
чистій literal value transformation, але не дозволяє заявити native lineage.

## Flag producer: CFG, трансформація та flags

`0262` читає F з DATA0055 у AL. `0264` порівнює **r5 з2**, не F з2. JNE0267
при r5≠2 виходить у026C поза selected Flag scope. Unknown r5 зупиняється на
predicate; LB/CMP prefix зберігається, persistent Flag stores не вигадуються.

При r5=2 наступний closed source path:

```text
0262 LB F →0264 CMP r5,2 →0267 JNE not-taken
→0269 STB r3,F →026A SJ026D →026D ADDB r6,F
→026F INCB r5 →0270 MOVB r7,2 →STOP before0272
```

Високорівневий псевдокод body:

```text
require Flag context and ordinary LB semantics
AL = read8(DATA0055); DD = 0; ZF = is_zero(AL)
CF,ZF = compare_unsigned8(read8(DATA03F5), 2)
if r5 is unknown: return IndeterminateBranch at0267
if r5 != 2: return OutsideVerifiedScope at026C with known prefix
write8(0269, DATA03F3, AL)              // preserve same-value event
r6_before = read8(DATA03F6)
sum = r6_before + AL
CF = carry8(sum); ZF = is_zero(sum mod256)
HC = ((r6_before & 15) + (AL & 15) > 15)
write8(026D, DATA03F6, sum mod256)
write8(026F, DATA03F5, 3); ZF = 0; HC = 0
write8(0270, DATA03F7, 2)               // no dedup even when already2
return selected state, stop-before0272
```

| Write order у body | Адреса / ширина | Ефект |
|---|---|---|
|0269|DATA03F3 /8| F |
|026D|DATA03F6 /8 RMW| `(r6_before+F) mod256` |
|026F|DATA03F5 /8 RMW|2→3|
|0270|DATA03F7 /8|2|

Парність F не визначає reach0269. Всі256 bytes можуть бути independent software
inputs у selected domain. Overflow carry належить ADD026D; INCB026F зберігає CF,
але перезаписує ZF/HC. Тому final ZF=0 і HC=0 навіть коли ADD result дорівнював0
або мав nibble carry. Final AL=F, AH retained за ordinary LB premise, DD0.
При unknown F/r6 final r6/CF можуть лишитися unknown, але selected r5=2 усе одно
визначає final r5=3/r7=2/ZF0/HC0. Incoming AL не помилково зберігається як F.

Інші local bytes, SSP/LRB/SCB, pointing banks та non-written PSW components
retained у цьому closed projected scope. Це не доказ physical memory/frame safety.

## Окреме status clear та dispatch

`status_clear` завжди представляє власний source effect:

```text
old = read8(DATA0356)
ZF = (old.bit6 == 0)
write8(0222, DATA0356, old with bit6 cleared)
stop-before0225
```

Unknown raw status з known bit6 дає відомий branch flag і примусово known bit6=0,
зберігаючи unknown neighbors. Ready bit7 не встановлюється; retained input bit7
не стає новим producer observation. Same-value clear залишається write event.

Повний selected `flag_path` додає guards:

```text
if DATA0356.bit1 == 0: outside selected scope at029D
clear status bit6 at0222
if old status.bit6 != 0: outside selected scope at0227
AL = r7; if r7 == 0: outside at0275
AL = r5; if r5 == 1: outside at027F
AL = (r5+1) mod256
if AL == r2: outside at0284
then evaluate flag_body beginning0262
```

Кожна unknown predicate зупиняє відтворення з відомим prefix, не вибирає branch
довільно. Наприклад r5=3/r2=4 виходить на0284 **до F read**, а direct entry0262
із r5≠2 виконує LB/CMP prefix і зупиняється на026C. Ці entry contracts не змішані.

Нове source-qualified уточнення M2cn: JBR021F з retained rel8=7B має target
`021F+3+7B=029D`. Tail0295 є іншим існуючим source site, а не цим branch target.
Історичні contracts/reports не переписуються; жоден target не виконується тут.

Якщо selected dispatch і body завершені, persistent journal містить
`0222→0269→026D→026F→0270`: п'ять окремих byte writes. Body alone містить чотири.

## Initial mask pair

Повна reviewed initial sequence містить більше, ніж два shadow stores:

```text
write16(54DD, FA00FA, 02A0)            // MOV immediate word; incoming DD independent
A = 2BAB at54E2; DD=1; ZF=0
write16(54E5, F800F8, A)
write8 (54E7, TRNSIT0046, 0)
write16(54EA, IRQ0018, 0)
reset_bit(54ED, TCON0_0040, 2)        // ZF from old bit2
write16(54F0, IE001A, A)
stop-before54F2
```

MOV54DD є explicit word instruction з retained DD, не ST A і не DD1 precondition.
L54E2 встановлює DD1 до word ST54E5/54F0. При incoming DD0/1/unknown перший MOV
не змінює його; далі DD1 відомий. Word IRQ clear і CLRB TRNSIT не знищують A2BAB.
Final ZF залежить від старого TCON0.2 після RB54ED; він не оголошений retained.
CF/HC retained. Software mode0217.2 ця closed sequence не записує.

IRQ clear — умовний software effect із власним ordinal/generation. Він не
доводить hardware ACK, set/clear race winner або actual pending state.
Для consistency після окремого переходу54F2→3E81 pairA відповідає mode0; actual
mode/history не підставляються. Модель initial зупиняється перед54F2.

## Один Mode/Shadow pass

Початок завжди читає поточний FA і записує його в IE до branch selection.
Подальша операція PSWH clear задає MIE0. Це вже non-atomic ordered history.

```text
A = read16(FA); DD=1; ZF=is_zero(A)
write16(3EEC, IE, A)
PSWH_AND_FE(3EEE)                    // MIE0; overlapping ZF remains unknown

if DATA0212.bit3 == 1:
    choose_B_gate                    // threshold read is skipped
else:
    if DATA0217.bit2 == 0:
        old = read_bit(IRQH0019,7)
        reset_bit(3EF7, IRQH0019,7)
        if old == 1:
            set_bit(3EFC, DATA00B6,7)
            set_bit(3EFF, DATA00B4,0)
    PSWH_OR_01(3F02)
    require reached USP0180
    CF,ZF = compare8(read8(USP+2D),29)
    PSWH_AND_FE(3F09)                // CF retained, ZF unknown
    choose_B_gate if CF==1 else choose_A_gate

choose_A_gate:
    if mode0217.2 == 1: pair_A()
    else: no core pair switch
choose_B_gate:
    if mode0217.2 == 0: pair_B()
    else: no core pair switch

PSWH_OR_01(3F40)                     // MIE1 before read/IE commit
A = read16(F8) at3F43; DD=1; ZF=is_zero(A)
write16(3F45, IE, A)
stop-before3F47
```

Pair cores та всі додаткові effects:

| Pair | Точний порядок |
|---|---|
|A|L3F11 A2BAB; IE3F14=2BAB; F83F16=2BAB; FA3F18=02A0; RB3F1D mode0217.2=0; SJ3F20→3F40|
|B|L3F25 AA9A3; IE3F28=A9A3; F83F2A=A9A3; FA3F2C=00A0; SB3F31 mode0217.2=1; RB3F34 DATA0125.7; RB3F37 DATA021D.7; SB3F3A TCON3_0043.3; SB3F3D TCON3_0043.2|

Threshold3F05 є `USP+signed2D=01AD` тільки за USP0180. PairB tail3F34 є
`USP+signedA5=0125`; A5 означає−91. Wrong/unknown USP зупиняє саме досягнуту
dependent операцію, зберігаючи вже доведені writes. При early gate до no-switch
деякі paths не читають threshold і не потребують USP. Unknown mode не стає0.

Вибір PairA/B взаємовиключний лише в одному pass за незмінних relevant inputs.
Це не глобальна взаємовиключність різних loop iterations. NoSwitch усе одно
містить prelude IE/PSWH і tail PSWH/IE writes. Direct pair IE store передує
F8/FA і mode commit; проміжні snapshots можуть бути inconsistent.

CF після CMP3F05 доходить до JLT3F0C через ANDB3F09; ZF при цьому не preserved.
При skipped threshold incoming CF збережений. Tail L3F43 незалежно встановлює
DD1 і ZF за F8; завершені new pairA/B мають nonzero F8 і final ZF0. Якщо F8 word
частково unknown, відомий nonzero byte достатній для ZF0, два zero bytes —ZF1,
інакше ZF unknown. Final A зберігає low/high bytes окремо.

00B4/00B6 належать PR RAM, а не безумовно unrelated scratch. Під SCB0 вони є
inactive bank6 bytes, але їхні writes залишаються у journal. Під SCB6 вони могли
б alias active DP/USP; такий context тут відхиляється. Mode0217/021D також
можуть alias інших local banks; LRB0040 є обмеженою явною передумовою, а не
загальним твердженням про фактичний LRB.

## Consistency: коротке замикання та failure effect

```text
A = 2BAB; DD=1; ZF=0
write16(3E84, selected_X1_at0080,02A0)
if mode0217.2 == 1:
    A = A9A3; DD=1; ZF=0
    write16(3E8D, selected_X1_at0080,00A0)
if compare16(A,F8) is not equal: failure
if compare16(A,IE) is not equal: failure
A = read16(X1); DD=1; ZF=is_zero(A)
if compare16(A,FA) is equal: success stop-before3EA7
failure:
    write8(3EA0,DATA00F5,4F)
    symbolic transfer3EA4→24E0; stop-before24E0
```

Mode1 має **два X1 writes**, не один final assignment. Вони відображені як
word DATA0080/0081 events під SCB0; pointing-register RAM не ігнорується.
F8 comparison failure не читає IE/FA; IE failure не читає FA. Unknown comparison
зупиняє conditional branch із prefix і не вигадує failure4F чи success.

Final CF/ZF походять від останнього виконаного software comparison. HC retained,
DD1; X1 містить expected FA. При early F8/IE failure A має expected F8; на FA
comparison A має expected FA. MIE й non-written PSW components retained.
Success не виконує3EA7; failure не виконує24E0.

Frame conditions mode procedures в обраних contexts:

| Procedure | Змінені architectural fields | Retained fields |
|---|---|---|
|Initial|A, DD, ZF|CF, HC, MIE, otherPsw, LRB, SCB, USP, SSP; mode byte не записано|
|Switch|A, DD, ZF, MIE; CF тільки за reached CMP3F05|HC, otherPsw, LRB, SCB, USP, SSP; active SCB0 PR bank не записано|
|Consistency|A, DD, CF, ZF; selected X1 DATA0080/81|HC, MIE, otherPsw, LRB, SCB, USP, SSP; інші selected pointing words|

Усі DATA bytes поза explicit journal retained лише в abstract byte-array domain
за no-interference premise. Inactive bank6 B4/B6 writes і selected X1 changes
залишаються explicit; цей frame contract не доводить physical alias або native
storage safety.

## PSWH overlap та межі flags

Manufacturer ANDB/ORB pages допускають PSWH operand і позначають ZF affected,
але перевірені сторінки не задають explicit precedence між write destination
byte та ZF update, коли ZF лежить усередині цього самого byte. Модель не обирає
порядок із production emulator output. Одразу після AND/OR PSWH ZF стає unknown.

MIE bit0 є explicit clear/set, CF/HC/DD і решта non-written bits збережені.
При maskFE/OR01 ці властивості узгоджуються з обома overlap orderings; ZF — ні.
Наступний незалежний L або CMP може знову встановити ZF. Тому непідтверджена
проміжна деталь не перетворюється ні на вигаданий zero, ні на причину ігнорувати
доведений CF branch relation.

Physical SF, safe SSP, actual stack aliases, interrupt acceptance subcycles,
native receive/frame generations та peripheral set/clear priority залишаються
поза моделями. Snapshot не вводить приховане SF=0.

## Ordered journal та unknown

Кожен DATA store/RMW, word PointerStore і PSWH REGISTER mask має окремий
ordinal, source PC, space, address, width, before/after bytes, value source,
same-value classification та conditional generation label. Word подається
одним16-bit event із двома LE bytes, не атомарним об'єднанням різних instructions.
Для A/flags є source relation steps і intermediate register state.

`ConditionalEffect:<procedure>:<PC>:<ordinal>` — deterministic logical label,
не actual native event ordinal або machine-owner identity. Equal numeric value
не видаляє store й не зберігає попередній writer generation. Missing generations
лишено null; вони не створюються як native evidence.

Raw unknown byte із known selected bits зберігає цей partial knowledge.
RB/SB встановлює відомий selected bit, не встановлює невідомі сусідні біти.
Звичайний whole-byte store замінює попередню bit knowledge новим value/unknown.
Word load/store зберігає partial low/high bytes. CMPword із неповним word
консервативно залишає CF/ZF unknown; short circuit не виконує непідтверджені paths.

Results розрізняють `CompleteConditional`, `OutsideVerifiedScope` і
`IndeterminateBranch`, містять boundary/reason, state, reads, journal,
steps та intermediateStates. Steps — математичні source relation witnesses,
не fabricated ROM trace або CPU retirements. Повний canonical output зберігає
unknown і всі journal events, без field exclusions.

## IE polarity hypotheses

`mask_hypotheses` окремо інтерпретує low-byte RX bit1 в IE/FA/F8 під Set1 і Set0.
Current IE/MIE/IRQ не заповнюються із constants. Для pair masks FA bit1=0,
F8 bit1=1; це source values, не actual enable state. Unknown word high byte
не знищує відомий low-byte bit, але missing low byte не стає відомим bit.

Mask gate використовує three-valued AND із MIE: відомий0 дає0, два1 дають1,
інакше unknown. Навіть gate1 не є IRQ delivery: `actualIrqDelivery=null`.
M2ck IE wording conflict, RX ACK/reassertion і hardware arbitration залишаються
джерельно кваліфікованими невідомостями.

## Незалежна перевірка, QA та delivery receipts

Reference має окремо виводити expected results із reviewed ISA/source contracts,
не викликаючи functions чи semantic helpers моделі. Corpus і expected stream
freeze відбуваються до першого model comparison; жодні expectations не
коригуються за model output. Спільний source specification не видається другою
manufacturer acquisition або actual hardware observation.

Обов'язкове coverage включає всі F00..FF із deterministic boundary r6 inputs,
even/odd, overflow/nibble carry, r5 alternatives, same-value writes, bank/context
refusals, partial/unknown states, AH retention, PairA/B/initial/no-switch,
short circuit, X1/failure stores, missing generation labels, mask mismatches,
intermediate non-atomic states та Set1/Set0 hypotheses. Negative controls мають
виявляти втрату stores/unknown/flags або недопустиме розширення scope.

Фактичні test counts, firstMismatch, canonical records/bytes/hash, local↔Ubuntu↔
Windows byte equality, exact CI SHA/run/attempt та job statuses зберігаються
в completed QA/CI receipts і `private/reports/m2cn/FINAL_REPORT_UK.md`.
На preparation цього source документа майбутні PASS/CI результати не заявлені.
Позитивний equivalence verdict можливий тільки разом із source-to-model proof
та незалежним comparison у зазначеному abstract scope.

Historical17 і Desktop залишаються NotRun, якщо їх фактично не запускали.
Public CI не потребує private ROM/NAS і не публікує raw evidence. Результати
M2cj/M2ck/M2cl/M2cm, contracts/oracles/fingerprints/manifests не переписуються.
Три inherited preservation exceptions відокремлені від одного окремо
user-authorized нового Python tooling exception; strict historical preservation
не оголошується PASS. Scoped baseline має7883 bindings; new unauthorized
differences повинні залишатися0, а сторонні files — збереженими.

## Подальше перенесення та наступний bounded scope

Для C++/Rust придатні окремі value types `UnknownOr<Byte/Word/Bit>`, closed input
struct, explicit context/precondition checks, чисті procedure functions і ordered
effect records. Byte arithmetic виконується з явним modulo256; signed USP offset
має бути sign-extended окремо, LE word bytes не залежать від host endian.

Варто зберегти procedures як structured branches, а не будувати новий CPU
interpreter. Journal і unknown algebra мають залишатися частиною контракту:
порівняння лише final masks або r3 не виявляє втраченого RMW, incorrect read order,
wrong AH/CF чи atomicity error. Native ownership не є наслідком перенесення мови.

Рекомендований наступний bounded software-only етап — окремі typed contracts
для вже відомих Length/Checksum dispatch alternatives027F/0284 та їхніх
міжблокових input/output obligations, із попереднім source review і незалежним
oracle. Це рекомендація, не запуск M2co й не розширення поточного scope.

Actual silicon/memory/peripheral applicability, safe native frame/SSP, current
DATA03F3/RX generations і actual downstream return залишаються недоведеними.
`EXECUTION_BLOCKED`; `FirmwareReady=false`.
