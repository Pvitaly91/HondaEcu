# M2z - native word0196 software-alternate comparison chain

M2z validates the bounded software path in the separate
`word0196SoftwareAlternateChain` operation, runner **0.33.0**.
It is not timer recovery, physical output validation or a recovered ECU schedule.

## Historical boundary and native continuation

[Historical M2y](M2Y_WORD0196_CONSUMER_HANDOFF.md) remains unchanged:
`word0196ConsumerHandoff`, first supported version0.32.0, stops before5503;
its alternate556F and gatefalse5533 remain terminal Partial.
M2z reuses the six-form software prefix without expanding that old operation.

One Cpu and one Bus per scratch sequence retain native M2r quartet production,
M2x selected-word05DF consumption and05EB word0196 generation. The sole M2y
inter-stage transition is a disclosed PC-only `ExplicitHarnessSchedule`
from05ED to54F5. Native54FA reads current0196;54FC stores er1;54FD compares the
once-initial byte0117 with15;actual JNE5501 TAKEN reaches556F.
There is **no host PC556F entry**, second machine or JSON-to-RAM handoff.

New suffix ranges are [556F,5596) and [55BF,55C5), budget18 instructions.
The maximum admitted path executes15 instructions. Each exact decoded form
has a scoped admission entry; mnemonic-wide admission is not used.

## Software CFG, comparison and boundaries

The common suffix reads018E, shifts AL, rotates byte018E through incoming CF,
loads native r0, ANDs AL with018E, then executes5578 and557D.

| Native decision | Software continuation | First excluded instruction |
| --- | --- | --- |
| JLT557D taken: CF=1 |55BF loads15;55C1 stores0117;55C3 stores018F |55C5 P2 byte read/modify/write |
| JLT557D not taken: CF=0 |557F copies0117 to r1;5582 ANDs0117 with AL;5585 tests012A.7,5588 tests0124.5;both false execute558B AND018F and558E OR012A bit0;5592 loads018F;5594 ORs AL withF0 |5596 P2 byte read/modify/write |

At5578 the left operand is **RAM word0196**, width16, independent of DD.
The right operand is **immediate00C0**, encoded as the low/high immediate bytes
of the exact word-object CMP form. It is a code-owned constant, not RAM00C0,
calibration, an editor field or a physical threshold. CMP leaves A unchanged,
sets CF for unsigned borrow (left<192), ZF for equality, and preserves HC/DD.
JLT557D tests that CF; no intervening flag writer exists. Both DD-independent
forms were checked against the primary ISA. JGT233A is unrelated and remains
Blocked/Unresolved.

No timer or other SFR is accessed in the new software stages. Stop occurs
**before** P2 at5596 or55C5. The excluded5503 TM0 read and5508 TMR0 write never
execute. Gatefalse54F5 stops before5533;its later RT553F frame is not fabricated.
Consumer157E remains StaticOther0196Consumer/NotRun.

Post-boundary P2/TRNSIT/TCON0/TM0/TMR0/PSWH/returns and later software readers
are private static preparation only. No subsequent milestone starts automatically.

## Generation and independent ownership

The generation identity is (writerPC05EB,eventIndex,zero-based ALL-native-write
ordinal,value). Both54FA and5578 must read that same current identity, with no
overlapping0196/0197 writer. Equal numeric values do not permit stale generations.
One event-wide journal covers the old prefix, both readers and software stores;
host writes are separate and independently checked.

The C# validator owns upstream history, selected quartet generations, native0196,
the M2y prefix, suffix operands/flags/branches and persistent software RAM.
Rust compare observations never become expected input. The validation-only
projection of nested historical evidence does not create an execution machine.
A scoped continuation callback returns independently modeled012A bit0 history
to the next M2x checkpoint;historical callers leave this callback absent.

0117 is once-initial raw input, then native5582/55C1 history.0128.2 is a
once-initial masked snapshot, not a per-event toggle.018E/018F start as automatic
scratch-pattern InitialHistory, with native5572/558B/55C3 ownership thereafter;
they are not external scenario sources or real-ECU-state claims.012A retains
inherited bit1 and neighbors while558E natively sets bit0.0124 remains upstream
owned. No boundary reseed or repair is allowed.

Any incomplete upstream/suffix is terminal:completed writes remain, later
events are NotRun and their sources are not applied. A below-immediate first
event natively writes0117=15;its next event reaches the excluded5503 boundary,
becomes M2z Partial, and later events are NotRun without host repair.

## Focused actual coverage

These are **new M2z counts**, not historical M2y, compatibility, synthetic or
model-only counts. The focused corpus has69 events:63 original-image events
and6 separately identified one-cell in-memory B-image events.

- 54 native05EB generations;51 same-generation54FA reads;42 same-generation5578 reads.
- 39 quartet-derived strict completions (33 original-only,6 B);3 gate-bypass mechanics controls.
- CMP domains:9 BelowImmediate (including3 gate controls),3 EqualImmediate,30 AboveImmediate.
- JLT557D:9 taken,33 not taken.42 software completions:9 stop-before55C5,33 stop-before5596.
- Quartet-derived per-slot totals:slot0=24,slot1=9,slot2=3,slot3=3.
- 21 repeated fresh equal-value producer-generation pairs;15 such pairs reach both readers.
- 6 fuel-cell A/B witnesses:4291 vs4290,all `ValueDivergenceSameBranch`;0 threshold crossings.
- 170 native suffix byte writes with address,width,PC,old/new,generation and branch provenance.
- 12 alternate Partial,3 NoFresh0196,12 later NotRun are not strict successes.

The three storage-domain actual source sweeps use declared upstream sources:
source015A=0 and source0142=53/54/55 yield native0196=191/192/193, respectively,
in all three scratch patterns. They do not host-edit0196 or mutate the BIN.
Model-only domain tests and invented low-address programs are separate.

## Executor fix, tests and compatibility

An invented regression first failed for exact byte ROL off:the generic executor
used a circular rotate and changed ZF. Primary ISA review established rotation
through incoming CF with CF-only flag changes. The minimal exact-form fix is
`byte-rol-off-through-carry-preserves-noncarry-flags`, disclosed only by0.33.0;
other ROL forms/admission and historical fix identities are unchanged.

Public fixtures contain invented decoded programs or model-only observations,
not OEM routine byte windows. Tests reject ready0196,stale identity,wrong reader
width/address,RAM00C0 substitution,wrong immediate,forged CF/ZF,forced outcome,
PC shortcut,hidden seeds/frame,second machine,skipped instruction and peripheral
execution. Historical0.32.0 cannot claim M2z. Compatibility compares16 executions
covering M2y/M2x/M2w/M2v/M2t/M2s/M2r/M2q/M2p/M2o and relevant M1i;M2u remains
static-only with protected evidence unchanged.

## Read-only CLI and status

```text
hondaecu research p28-fuel word0196-alternate-check <original.bin>
  --profile p28-304 --confirm-profile
  --baseline-binding <binding.json> --runner <runner-0.33.0>
  --scenario <m2z-scenario.json> --output <new-private-report.json>
```

Closed version1 purpose:`word0196-software-alternate-test`;reuse M2y upstream
structure with no new external sources. No ready result,compare/flags,outcome,
immediate override,P2,timer,PC556F,arbitrary RAM or formula inputs. Input snapshots,
exact binding/profile confirmation,new-output and alias checks remain mandatory.

Word0196AlternateSoftwareChain=Validated and Cmp5578=Validated for the bounded
target corpus. InterStageScheduleTo54F5=ExplicitHarnessSchedule;
SoftwareAlternate5501To556F=NativeContinuousControlFlow;
TimerContinuation/P2/PhysicalOutput=NotRun;Recovered0196Scheduler=NotEstablished;
IRQDelivery=NotInjected;ElapsedTime=None;Physical0196Role=Unknown.
M2y/M2x/M2w established handoffs stay Validated;M2tJgt=Blocked/Unresolved.
FirmwareBIN/binding/compensation/export-plan/receipt/token outputs=0.
PcInspectionOnly / NotFlashReady;physicalRpmAvailable=false;physical fuel/time/
degrees unavailable;strict M2i Blocked;GUI r3 paused/NotRun;D1/D2 interactive
acceptance and hardware/full boot NotRun.
