# M2at - exact DEC DP half-carry semantic correction

**M2at ISA semantic fix complete - exact instruction semantics only.**
Base `7bc125a2cb8ae5bc41853f6a17bd834ece51574d` (M2as).
Branch `codex/p28-dec-dp-halfcarry-fix-m2at`.
Runner **0.42.0**, protocol **1**. Sole new identity:
`word-decrement-dp-half-borrow`. No runtime/admission/startup capability added.
Actual-ROM executions M2at=**0**; all execution tests use invented instruction
bytes and synthetic register state, not a copied OEM window or reset history.

## Primary source and independent arithmetic

OKI MSM66201 Instruction Manual, First Edition September1991, complete printed
**3-55 / PDF108** was freshly rendered and visually reviewed: word DEC heading,
function, description, flag matrix, DP opcode82 row, length and cycle columns.
Description specifies subtract1; ZF/HC are affected, CF/DD are not. The
DD-affecting cell is blank. Printed1-12 Figure1-5 defines the SCB-selected
pointing-register sets;1-21..1-24 separates DD-gated accumulator operations.
Printed3-54/PDF107 explicitly identifies half-borrow from bit3 after subtraction.
January1998 E2E1027-27-Y4 specification page9 confirms PSW CF15/ZF14/HC13/DD12.
The raw scans/hashes/full-page review ledger remain private, not in Git.

Source caveat retained: the scanned3-55 and3-56 function lines print **plus1**,
contradicting their decrement headings and descriptions specifying **subtract1**.
They are not silently treated as an alternative increment rule. M2aq already
reported this inconsistency. No CRC-failed user-archive member is needed as new
authority: current proof uses the intact instruction PDF and explicit bit3
subtraction example, independently checked against nibble arithmetic.

Independent specification, not Rust helper/output:

```text
newDP  = (oldDP + 65535) mod 65536
newZF  = (newDP == 0)
newHC  = (oldDP mod 16 == 0)
newCF  = oldCF
newDD  = oldDD
newPSW = (oldPSW & ~0x6000) | (newZF ? 0x4000 : 0) | (newHC ? 0x2000 : 0)
```

Subtracting1 from low nibble n requires a borrow beyond bit3 exactly when n=0.
A separate integer bit-ripple subtraction model independently checked all65,536
words and the262,144 word/DD/HC combinations, without constructing a Cpu/Bus.

## Genuine RED before any executor change

M2aq's source-only discrepancy was reproduced using real decode/`step()` in a
private Rust test crate importing the unchanged0.41 production modules. Compiler
success was recorded separately from the two actual HC assertion failures
(exit101). Main independently rebuilt and reproduced both failures too.

| Old DP / incoming HC | Correct DP | RED actual HC / PSW | GREEN HC / PSW |
| --- | --- | --- | --- |
| 0010 /0, incoming PSW0FF9 | 000F | 0 /0FF9 instead of2FF9 | 1 /2FF9 |
| 0011 /1, incoming PSW2FF9 | 0010 | 1 /2FF9 instead of0FF9 | 0 /0FF9 |

Those witnesses have CF0/DD0. Independent exhaustive/corner checks include both
DD and CF values. The exact same test source and expectations were retained
from RED to GREEN and copied byte-identically into the public Rust test module.
The private implementation GREEN preceded the package metadata bump; that is
not a rebuilt/relabelled historical0.41 executable. Final0.42 package verification
and full delivery QA are recorded separately in the private closure artifacts.

## Minimal exact-form executor predicate

Only a separate HC assignment was added to the existing INC/DEC arm, requiring
all of: baseDEC, word operation, operands exactly `[Arg::Reg(Reg::Dp)]`, decoded
mnemonic `DEC DP`, length1, exact pattern `["82"]`, pattern DD-mode `U`, and
`dd_after=None`. It assigns `HC=(oldDP & 15)==0`.

The old decrement result, ZF computation, DP write path, PC advance and DEC X1
branch remain byte-identical. No general word-register DEC expansion, decoder,
opcode table, operand mapping, CPU constructor or bus/peripheral change.
The exact word form executes with either incoming DD and preserves that DD.

Accounting caveat: primary INT column lists3, while the unchanged generic
decoder accounts2 for a one-byte form. This milestone corrects HC only, not
cycle accounting or physical timing. No elapsed-time claim is made.

## Invented exhaustive and full-state tests

Six isolated new Rust tests use real decoded step: all65,536 oldDP values ×
DD0/1 × incomingHC0/1 = **262,144 vectors per context**, independently exercised
in two contexts, **524,288 total**. Incoming CF/ZF also vary across these words.
Nine explicit corners ×16 CF/ZF/HC/DD combinations ×two contexts =**288**,
covering both CF values, zero/wraparound, nibble borrow and HC overwrite in both
directions. Corners:0000,0001,000F,0010,0011,0100,1000,8000,FFFF.

Literal contexts are SCB1/DP008C with LRB0063/local0318, and SCB5/DP00AC with
LRB0143/local0A18. They are invented nonaliased layouts, not actual reset state.
Snapshot follows fixture preparation. Every pointing set's other bytes, local
registers, stack neighbors and distant RAM canaries are retained. All Cpu fields
are checked: accumulator, SSP, LRB, SF, halted, flags and psw_other; only the
existing PC/instruction/cycle increments are allowed.
Native data accesses must be exactly one16-bit read(oldDP) and one16-bit
write(newDP) at the independently supplied DP slot; all-write journal must be
exactly that DP write. No extra data write, peripheral/program-data read or fault.
Full PSW outside ZF/HC matches the incoming word, including CF/DD.

## Non-target preservation controls

Before/after comparison covers33 form identities /4,960 valid-DD vectors in
two contexts. Its stable full-state fingerprint is identical before/after,
including every ordinary-RAM byte0080..0FFF, Cpu fields, decoded identity,
accounting, ordered native accesses and writes. This is a preservation control,
not newly confirmed ISA semantics for unreviewed forms.

Controls include DEC X1/80, X2, USP, SSP, LRB, local word/direct/indexed forms,
DECB indexedX1/direct/off/local, INC DP/X1/indexedX2, direct/compact INCB,
ordinary CMP/SUB, M2an off-page SLLB and word/byte ROL/ROR/SRL/SRA.
46 existing module regressions passed before/after with unchanged expectations,
including historical exhaustive DEC X1 and ROR. Full Rust suite remains required.

## Version-specific identity is not admission

Exactly one package/lock bump and one inventory addition:0.41 ->0.42.
Core explicitly retains historical0.40 with34 fixes and0.41 with35;
only0.42 requires36 including `word-decrement-dp-half-borrow`.
All earlier version-specific inventories and operation contracts remain intact.
Independent Core cases cover the41 existing operations across these three
inventories, cross-version/wrong/missing/duplicate/unknown identities and
protocol/upstream/operation/unknown-version refusal. Historical0.39 cannot claim
the M2ah tail. Existing M2an0.40/0.41 fixtures remain unchanged; only its live
current-runner disclosure probe is explicitly adapted to0.42's inventory.

Existing generic synthetic policy and all exact-form admission tables are
unchanged. Acquisition/checksum/producer/stateful form gates still reject82
for both DD states. Current0.42 subprocess tests also require wire refusal
before execution: status2, steps0, PC0, unchanged DP/PSW/canaries, empty trace.
No new operation, request/response field, scenario, CLI option, entryPC2626,
hostPC2689 or ECU HC/DP seeding is introduced. Recognized opcode is not permission.

25 live subprocess disclosures receive only the necessary current identity
update; PID/START/READY/cancellation/escaping/streams/timeouts/cleanup unchanged.
Of18 stabilization files,16 must remain exact and only the two previously
authorized FuelAdditive/FuelFactor assertion literals may change. Reverse byte
normalization is mandatory. All seven historical0.40/0.41 runner binaries and
older private reports remain protected; builds use a dedicated M2at target.

M2aq's proposed reset runner0.42 was proposal-only, not a released reset contract.
This0.42 release contains the DEC fix only. Any future reset capability needs
its own separately authorized milestone, version and admission review.

## Impact on static startup sites and retained blockers

At the inherited static2626/2631/263C sites, decrement result and ZF are unchanged;
HC fidelity improves, CF/DD remain unchanged. Wait branches primarily consume
ZF; later MBR independently produces CF. No original-ROM execution of these
sites, LOW/HIGH/LOW P4 samples, PWM IRQH.5 or physical time is supplied here.
Correct HC does not establish actual startup/reaching or resolve WDT/reset.

M2as WdtCommandMeaningNotEstablished / Research/Blocked and hardware-safe24F4->24F8
remain unresolved. M2ar reset-context Research/Blocked; M2aq ExecutionPreflightBlocked,
CAL2689/RT5C80 NotRun; actual frame268C NotObserved and restoredSSP047E
NotEstablished. M2ap SSP/ADC blocked; M2ao afterCLR2758/beforeSTIE2759;
M2ak source-to5722 blocked; M2al/M2am C8 PrimaryConflictUnresolved;
M2an SLLB fix complete; M2ah STOPbefore5722;019B.2 runtime owner NotEstablished;
5722/5725/5733 DynamicNotRun; M2tJGT233A unresolved; M2ag/M2af unchanged;
strictM2iBlocked; IRQNotInjected; TimerEvolutionNotModeled;
EnclosingIRQFrame/RecoveredEcuScheduler NotEstablished; ElapsedTimeNone.
PcInspectionOnly/NotFlashReady;physicalRpmAvailable=false; physical fuel/time/
degrees unavailable. GUIr3 paused/NotRun; D1/D2 interactive/hardware/fullboot
NotRun; FirmwareBIN=0. C8 and WDT inquiries ready/NotSent, no vendor contact.

Full Rust/Core/CLI/Desktop headless, version/subprocess/admission/relevant research
regressions, formatting/privacy/diff, full protected SHA-256 and exact-SHA
Ubuntu/Windows/Desktop CI precede the private final report, saved last.
No historical research finding is retrospectively promoted by this ISA fix.
One next evidence-driven step, not performed: obtain separately authorized
applicable WDT3C/reset-release primary evidence. STOP after delivery: no M2au,
WDT/JGT fix, native reset/CAL/RAM loop/IRQ/first5722/fullboot/GUI/hardware.
