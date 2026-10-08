# M2an - exact SLLB off-page semantic correction

**Narrow ISA fix, not runtime admission.** Exact M2am parent:
`26dcb26be4387b9831aacfef5336ede0b2d26dd8`.
Runner **0.41.0**, protocol **1**. Sole added fix identity:
`byte-sll-off-page-preserves-noncarry-flags`.
M2ah still STOPs before5722; M2ak/M2al/M2am blockers remain independent.

## Primary form and independently reproduced defect

OKI MSM66201 Instruction Manual,first edition September1991,printed **3-145**
(PDF page198) was freshly rendered and reviewed in full: function diagram,
description,flag matrix and opcode table. Exact off-object form is
**SLLB off N8 / C4 N8 D7 / three bytes / DD-neutral U**.
It shifts the byte left, inserts0 atbit0, puts oldbit7 inCF and preserves ZF/HC/DD.
The incoming CF is not a shifted-in bit.

The base executor's shared ROL/ROR/SLL/SRL/SRA path already computed correct
SLL result/CF, but the existing ZF exceptions did not include this exact
off-page byte form. It therefore called `set_zf(result,byte)`.

| Counterexample | Base0.40 | Corrected0.41 |
|---|---|---|
|Old01,incomingZF1|Result02,CF0,incorrectZF0|Result02,CF0,ZF1 retained|
|Old00,incomingZF0|Result00,incorrectZF1|Result00,ZF0 retained|
|Old80,incomingZF0|Result00,CF1,incorrectZF1|Result00,CF1,ZF0 retained|

An independent unchanged Rust probe using real `step()` on invented C4 B6 D7
failed with the expected ZF assertion against the unmodified0.40 library before
any fix,then passed against0.41. Compiler success and actual test failure were
recorded separately; the same probe source/hash and expectations were retained.
No OEM bytes, actual571F execution or second-executor expected output.

## Minimal implementation and state contract

Only a form-specific ZF exception was added. Its predicate requires:
baseSLL,byte operation,decoded mnemonic SLLB off N8,length3,
exact pattern C4/N8/D7,pattern DD-mode U,dd_after=None and
`Arg::Mem(Mem::OffPage)`. It works with both incoming DD states.
The existing shift/CF formula and memory-write path are untouched.

Independent specification:

```text
newByte = (oldByte * 2) mod 256
newCF   = oldByte >= 128
newZF   = oldZF
newHC   = oldHC
newDD   = oldDD
newPSW  = (oldPSW & ~0x8000) | (newCF ? 0x8000 : 0)
```

Tests use ordinary non-aliased invented RAM destinations in two established
page contexts,not ECU caller provenance. They check A,SSP,LRB,SF,psw_other,
all local registers,all pointing-register sets,neighbors,other-page/low-page
same-offset and stack canaries. The native data journal must be exactly one
8-bit read and one8-bit write at the independently supplied target.
No new special-register alias behavior or hardware validity is claimed.

Known independent accounting limit: this primary form's INT table lists7,
while the unchanged decoder reports6 from generic2*length. M2an does not fix
timing/cycles or claim measured elapsed time. The control only checks that
historical accounting did not change.

## Invented exact-form coverage

Five new Rust tests use real decode/step:
256 bytes × CF/ZF/HC/DD combinations16 × two pages = **8,192 vectors**;
five explicit corner bytes ×16 flags ×two pages =160 controls;
24 non-target form/DD combinations ×five values ×eight CF/ZF/HC combinations
=960 controls; plus the counterexample and DD0/DD1 rejection by three unchanged
strict admissions.

Addresses and byte values below are hexadecimal; vector counts are decimal.
Invented C4 B6 D7 atPC20 advances to23. LRB0063 targets03B6/localbank0318;
LRB0143 targets0AB6/localbank0A18. Expected addresses and arithmetic are supplied
independently,not obtained from the executor's address/result helpers.
Full PSW excluding CF must match byte-for-byte,including ZF for zero/nonzero
results and both incoming carry values. Operand width,pattern,length,DD neutrality
and PC advancement are checked.

Non-target controls retain SLLB A53/DD0,SLL A53/DD1,ROLB A33/DD0,ROL A33/DD1,
ROLB offC4/N8/B7,ROR/SRL accumulator/off-page and historical SRA behavior.
Direct C5/N8/D7,DP,USP and local-register SLLB retain their existing generic
behavior. Those unreviewed controls are not new primary confirmation/admission.
Historical shift/rotate test assertions are unchanged.

## Version-specific compatibility,not new operations

Cargo package/lock version0.40 ->0.41;exactly one identity appended.
No PROTOCOL_VERSION,Request/Response field,operation,scenario schema,CLI parameter
or exact-form admission registry changes.

Core retains explicit historical TailVersion0.40,its34 identities and every
historical inventory.0.41 requires exactly35,including the new identity.
The shared historical CurrentFixes base remains20 entries.
97 new Core cases cover41 existing operations ×two versions,wrong/missing/
duplicate/unknown inventories,wire/upstream/version guards,historical0.39 tail
refusal and one actual0.41 subprocess refusal of an invented C4 probe.
The generic synthetic policy still refuses off-SLLB before any step:status2,
steps0,PC0,unchanged byte/PSW/canaries and empty trace. It is not an execution
route for the new ISA fix;direct Rust step() supplies that isolated coverage.
Identity compatibility is not permission to execute a firmware instruction.

Real current subprocess version assertions in Core/CLI/Desktop now expect0.41.
Historical mock metadata and semantic expectations remain unchanged.
The user explicitly authorized version-only edits in the two files included
in the18-source Windows stabilization guard;PID/START/READY/cancellation logic
and all historical stabilization artifacts remain unchanged and audited.
Five CLI test path resolvers now honor the existing HONDAECU_SLICE_RUNNER override,
retaining default CI paths and mandatory-file checks,without skips.
Local builds use dedicated new target directories so the previous0.40 executable
and historical distributions are not overwritten.

## No runtime continuation or retrospective research promotion

Exact off-SLLB remains Unsupported in acquisition,M2ah-tail and alternate-word
strict admissions. Recognition by decoder/executor does not grant permission.
Retained M2ah00A2=0 still skips571F throughCMP5719/JNE571D and STOPs beforeJBS5722,
because DATA019B.2 actual semantic owner is NotEstablished.
No initialslot5,019B.1/.2 owner,host flags,forced branch or bit-model runtime
handoff.5722/5725/5733 DynamicNotRun;5782/5787,TM3/later accesses NotRun.

M2am PrimaryConflictUnresolved,equalityCF0/ZF1 andlessCF1/ZF0 NotEstablished;
vendor inquiry DraftReady/NotSent;compatible-silicon protocol NotExecuted.
JGT2714/JGT233A/JLE,conditions,startup termination and source classifications unchanged.
No source-to5722 or RAM-clear completion proof follows from this fix.

M2ak first-reader Research/Blocked;M2al JGT Research/Blocked;M2ag/M2af unchanged;
M2tJGT233A Blocked/Unresolved;strictM2iBlocked.
RT5801/returns0614/0638/0667 NotRun in new scope;historicalframe0667 pending.
IRQNotInjected;TimerEvolutionNotModeled;EnclosingIRQFrame/RecoveredEcuScheduler
NotEstablished;ElapsedTimeNone;PcInspectionOnly/NotFlashReady;
physicalRpmAvailable=false;physical fuel/time/degrees unavailable;
GUIr3paused/NotRun;D1/D2interactive,hardware/fullbootNotRun;FirmwareBIN0.
**M2an actual-ROM executions=0.**

Full Rust/Core/CLI/Desktop headless QA,formatting,staged privacy/source-scope audit,
full protected SHA-256 comparison and exact-SHA Ubuntu/Windows/Desktop CI precede
the new private final report,saved last. Historical reports are not rewritten.
Next evidence-driven step: obtain explicitly authorized applicable manufacturer
C8 equality/less clarification;not performed here.
STOP after final report:no M2ao,runtime571F,first5722,JGTfix,IRQ/timer,GUI/hardware.

## Complete factored byte/CF/ZF truth table

Every row applies to **both incoming CF values**. The ZF columns cover both
incoming ZF states;HC/DD and other PSW bits retain their incoming values.
This enumerates all256 byte inputs without substituting result-zero for ZF.
The table is an independent arithmetic specification,not executor output.

| Old byte | New byte | New CF | New ZF if old ZF0 | New ZF if old ZF1 |
|---|---|---|---|---|
|00|00|0|0|1|
|01|02|0|0|1|
|02|04|0|0|1|
|03|06|0|0|1|
|04|08|0|0|1|
|05|0A|0|0|1|
|06|0C|0|0|1|
|07|0E|0|0|1|
|08|10|0|0|1|
|09|12|0|0|1|
|0A|14|0|0|1|
|0B|16|0|0|1|
|0C|18|0|0|1|
|0D|1A|0|0|1|
|0E|1C|0|0|1|
|0F|1E|0|0|1|
|10|20|0|0|1|
|11|22|0|0|1|
|12|24|0|0|1|
|13|26|0|0|1|
|14|28|0|0|1|
|15|2A|0|0|1|
|16|2C|0|0|1|
|17|2E|0|0|1|
|18|30|0|0|1|
|19|32|0|0|1|
|1A|34|0|0|1|
|1B|36|0|0|1|
|1C|38|0|0|1|
|1D|3A|0|0|1|
|1E|3C|0|0|1|
|1F|3E|0|0|1|
|20|40|0|0|1|
|21|42|0|0|1|
|22|44|0|0|1|
|23|46|0|0|1|
|24|48|0|0|1|
|25|4A|0|0|1|
|26|4C|0|0|1|
|27|4E|0|0|1|
|28|50|0|0|1|
|29|52|0|0|1|
|2A|54|0|0|1|
|2B|56|0|0|1|
|2C|58|0|0|1|
|2D|5A|0|0|1|
|2E|5C|0|0|1|
|2F|5E|0|0|1|
|30|60|0|0|1|
|31|62|0|0|1|
|32|64|0|0|1|
|33|66|0|0|1|
|34|68|0|0|1|
|35|6A|0|0|1|
|36|6C|0|0|1|
|37|6E|0|0|1|
|38|70|0|0|1|
|39|72|0|0|1|
|3A|74|0|0|1|
|3B|76|0|0|1|
|3C|78|0|0|1|
|3D|7A|0|0|1|
|3E|7C|0|0|1|
|3F|7E|0|0|1|
|40|80|0|0|1|
|41|82|0|0|1|
|42|84|0|0|1|
|43|86|0|0|1|
|44|88|0|0|1|
|45|8A|0|0|1|
|46|8C|0|0|1|
|47|8E|0|0|1|
|48|90|0|0|1|
|49|92|0|0|1|
|4A|94|0|0|1|
|4B|96|0|0|1|
|4C|98|0|0|1|
|4D|9A|0|0|1|
|4E|9C|0|0|1|
|4F|9E|0|0|1|
|50|A0|0|0|1|
|51|A2|0|0|1|
|52|A4|0|0|1|
|53|A6|0|0|1|
|54|A8|0|0|1|
|55|AA|0|0|1|
|56|AC|0|0|1|
|57|AE|0|0|1|
|58|B0|0|0|1|
|59|B2|0|0|1|
|5A|B4|0|0|1|
|5B|B6|0|0|1|
|5C|B8|0|0|1|
|5D|BA|0|0|1|
|5E|BC|0|0|1|
|5F|BE|0|0|1|
|60|C0|0|0|1|
|61|C2|0|0|1|
|62|C4|0|0|1|
|63|C6|0|0|1|
|64|C8|0|0|1|
|65|CA|0|0|1|
|66|CC|0|0|1|
|67|CE|0|0|1|
|68|D0|0|0|1|
|69|D2|0|0|1|
|6A|D4|0|0|1|
|6B|D6|0|0|1|
|6C|D8|0|0|1|
|6D|DA|0|0|1|
|6E|DC|0|0|1|
|6F|DE|0|0|1|
|70|E0|0|0|1|
|71|E2|0|0|1|
|72|E4|0|0|1|
|73|E6|0|0|1|
|74|E8|0|0|1|
|75|EA|0|0|1|
|76|EC|0|0|1|
|77|EE|0|0|1|
|78|F0|0|0|1|
|79|F2|0|0|1|
|7A|F4|0|0|1|
|7B|F6|0|0|1|
|7C|F8|0|0|1|
|7D|FA|0|0|1|
|7E|FC|0|0|1|
|7F|FE|0|0|1|
|80|00|1|0|1|
|81|02|1|0|1|
|82|04|1|0|1|
|83|06|1|0|1|
|84|08|1|0|1|
|85|0A|1|0|1|
|86|0C|1|0|1|
|87|0E|1|0|1|
|88|10|1|0|1|
|89|12|1|0|1|
|8A|14|1|0|1|
|8B|16|1|0|1|
|8C|18|1|0|1|
|8D|1A|1|0|1|
|8E|1C|1|0|1|
|8F|1E|1|0|1|
|90|20|1|0|1|
|91|22|1|0|1|
|92|24|1|0|1|
|93|26|1|0|1|
|94|28|1|0|1|
|95|2A|1|0|1|
|96|2C|1|0|1|
|97|2E|1|0|1|
|98|30|1|0|1|
|99|32|1|0|1|
|9A|34|1|0|1|
|9B|36|1|0|1|
|9C|38|1|0|1|
|9D|3A|1|0|1|
|9E|3C|1|0|1|
|9F|3E|1|0|1|
|A0|40|1|0|1|
|A1|42|1|0|1|
|A2|44|1|0|1|
|A3|46|1|0|1|
|A4|48|1|0|1|
|A5|4A|1|0|1|
|A6|4C|1|0|1|
|A7|4E|1|0|1|
|A8|50|1|0|1|
|A9|52|1|0|1|
|AA|54|1|0|1|
|AB|56|1|0|1|
|AC|58|1|0|1|
|AD|5A|1|0|1|
|AE|5C|1|0|1|
|AF|5E|1|0|1|
|B0|60|1|0|1|
|B1|62|1|0|1|
|B2|64|1|0|1|
|B3|66|1|0|1|
|B4|68|1|0|1|
|B5|6A|1|0|1|
|B6|6C|1|0|1|
|B7|6E|1|0|1|
|B8|70|1|0|1|
|B9|72|1|0|1|
|BA|74|1|0|1|
|BB|76|1|0|1|
|BC|78|1|0|1|
|BD|7A|1|0|1|
|BE|7C|1|0|1|
|BF|7E|1|0|1|
|C0|80|1|0|1|
|C1|82|1|0|1|
|C2|84|1|0|1|
|C3|86|1|0|1|
|C4|88|1|0|1|
|C5|8A|1|0|1|
|C6|8C|1|0|1|
|C7|8E|1|0|1|
|C8|90|1|0|1|
|C9|92|1|0|1|
|CA|94|1|0|1|
|CB|96|1|0|1|
|CC|98|1|0|1|
|CD|9A|1|0|1|
|CE|9C|1|0|1|
|CF|9E|1|0|1|
|D0|A0|1|0|1|
|D1|A2|1|0|1|
|D2|A4|1|0|1|
|D3|A6|1|0|1|
|D4|A8|1|0|1|
|D5|AA|1|0|1|
|D6|AC|1|0|1|
|D7|AE|1|0|1|
|D8|B0|1|0|1|
|D9|B2|1|0|1|
|DA|B4|1|0|1|
|DB|B6|1|0|1|
|DC|B8|1|0|1|
|DD|BA|1|0|1|
|DE|BC|1|0|1|
|DF|BE|1|0|1|
|E0|C0|1|0|1|
|E1|C2|1|0|1|
|E2|C4|1|0|1|
|E3|C6|1|0|1|
|E4|C8|1|0|1|
|E5|CA|1|0|1|
|E6|CC|1|0|1|
|E7|CE|1|0|1|
|E8|D0|1|0|1|
|E9|D2|1|0|1|
|EA|D4|1|0|1|
|EB|D6|1|0|1|
|EC|D8|1|0|1|
|ED|DA|1|0|1|
|EE|DC|1|0|1|
|EF|DE|1|0|1|
|F0|E0|1|0|1|
|F1|E2|1|0|1|
|F2|E4|1|0|1|
|F3|E6|1|0|1|
|F4|E8|1|0|1|
|F5|EA|1|0|1|
|F6|EC|1|0|1|
|F7|EE|1|0|1|
|F8|F0|1|0|1|
|F9|F2|1|0|1|
|FA|F4|1|0|1|
|FB|F6|1|0|1|
|FC|F8|1|0|1|
|FD|FA|1|0|1|
|FE|FC|1|0|1|
|FF|FE|1|0|1|
