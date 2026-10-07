# M2aj - pre-063B caller and DATA019B shift-history provenance

**Research/Blocked; static feasibility/provenance only.** Exact M2ai parent:
`cffc10b5aa731928b221e69616b38a844d853798`, delivered with CI37548213432,
3/3 success attempt1. Runner remains **0.40.0**; new operation/CLI/version none.
No new actual-ROM calls, shifts, branch choices, returns, IRQs or timer evolution.
The separate Windows PID/START/READY stabilization commit remains in ancestry
and its source files are unchanged. M2ai/M2ah results are not promoted.

## Bounded caller CFG and real order

The verified M2ai11,499 decoded extents were reused against the same matching
original/listing: every stored extent byte/length still matches. A317-node bounded
enclosing CFG starts at INT10379 and serial RX BRG03ED and stops at0667. It includes
literal out-of-line jumps, joins and loop edges. CALL fallthrough edges are
**conditional native-return summaries**, not executed continuations. Indirect
entries, nested IRQs and unlisted destinations remain Unknown.

| Site | Exact form / length | Target / return | Static incoming requirements |
|---|---|---|---|
|0611|CAL addr16 /3|56BE /0614|TBR05F2 selected0117 bit clear; JNE05F5 not taken;0128/timer/IRQ route to060E|
|0635|CAL addr16 /3|56BE /0638|TBR selected bit set; wrapped(TMR0-TM0) between5 and31 through061F/0624 comparisons|
|063B|CAL addr16 /3|54F5 /063E|Join from completed earlier call or no-earlier-call0629; historical technical seam is separate|
|0664|CAL addr16 /3|56BE /0667|Old012A.3 clear at RB065F; JNE0662 not taken; historical M2ag domain separate|

05ED loads selector013C; TBR05F2 tests **0117[AL&7]**, not a literal fixed bit.
JNE05F5 splits the earlier-call alternatives. On the clear route, JBR05F7 can
bypass timer work; otherwise TM0/TMR0 reads, IRQ.5, addition carry and optional
TMR0 write precede0611. The set route reads TMR0/TM0 before the two code-owned
threshold comparisons. These are software projections, not elapsed-time claims.

Within this bounded **one non-reentrant invocation**,0611 and0635 are mutually
exclusive. After genuine return0614, SB012A.3 and J0617 go directly to063B;
after genuine return0638, SB012A.3 falls through063B. Neither continuation
reaches the other early CALL. This is not a global assertion about multiple IRQ
invocations or all whole-firmware re-entry/indirect paths.

## The additional012A.3 later-call gate

Both earlier-return sites set012A.3. Under the independently validated historical
below063B->RT5688->M2ae path, bit3 survives: RB5685 clears onlybit7, and the selector
continuation does not overwrite012A.3. Then RB065F observes **oldbit3=1**, clears
it and setsZF0; JNE0662 skipsCAL0664. The post-RB numeric0 cannot select the CAL.

Thus an earlier completed call plus CAL0664 is not automatically a two-producer
sequence. On that bounded preserved-bit3 path the second CAL is skipped. Other
callee/alias contexts remain separately Unknown; no new gate clear is supplied.
The no-earlier-call0629 path instead explicitly clears bit3 before063B, but does
not create a prior DATA019B shift history.

## Call frames and return barriers

Each ordinary CAL stores its own PC+3 word at even(oldSSP), then decrementsSSP
by2. A matching RT incrementsSSP first and reads that exact current frame. Frame
identity is writerPC,eventIndex,stackAddress,width16,returnPC and global native
write ordinal. Earlier0611/0635 have **no new actual frame observations**: incoming
SSP/IRQ saved context/event/ordinal remain Unknown, not copied from technical07FE
or the historical pending0667 frame.

| Caller | Required native return instruction | Status in M2aj |
|---|---|---|
|0611 ->0614|RT5801 after complete56BE tail|NotRun; completion not established|
|0635 ->0638|RT5801 after complete56BE tail|NotRun; completion not established|
|063B ->063E|RT5688|Historical bounded proof unchanged, not a new enclosing-caller proof|
|0664 ->0667|RT5801|Historical pending frame retained; returnNotRun|

No hostPC0611/0635/571F, host return0614/0638, manual pop, fake IRQ frame, RTI or
JSON/RAM reconstruction substitutes for these obligations. Ordinary CAL is not
hardware interrupt entry.

## DATA00A2 native source inventory and slot5

All verified listed extents were classified afresh for00A2, including word00A2/
00A3, off-page/local-bank, indexed/indirect and SCB-selected pointer storage.
There are6 concrete listed-context writer sites and16 reader/RMW sites.
Unknown alternative banks, pointers, stack and IRQ domains remain conservative.
In particular00A2 can alias the low byte of **X2 in SCB4**; current caller setup
SCB2 does not establish every other caller's context.

| PC | Exact abstract writer | Source and limitation |
|---|---|---|
|03B0|MOVB N'8,#N8|Code-owned0 on the relevant INT1 path; notslot5|
|0424|INCB N8|After byteCMPslot,#5 not-taken JGE, prior owned4 could become5; prior history/reaching gates unproved|
|043B|CLRB N8|Low-byte0; previous0438 increments00A3 separately|
|047C|CLR N8,word|Clears both00A2/00A3 on an alternate RAM/peripheral-gated branch|
|04F6|STB A,N8|AL receives native DIVB remainder by code6 after CLR A/LB0134/ADDB3; range0..5, exact5 needs owned0134/reaching path|
|409B|MOVB N'8,#N8|Code-owned2 in another context, not automatically preceding the early callers|

Slot5 is **SatisfiableUnderAssumptions**, not established on an actual earlier
caller machine. In the serial route,0424 requires oldslot4;04F6 requires the
appropriate owned0134 arithmetic history and branches. IRQ entry/frame, caller
buffers, control histories and aliases are not supplied by those code constants.
The actual M2ag/M2ah retained slot0 remains unchanged. Historical M2v technical
slot0..5 is TechnicalOnly and is not reused as native caller authority.
No initial00a2=5,perCallSlot,producerIndex,hostPatch00A2 or force571F field exists.

## Bit0 ->bit1 ->bit2 and the first5722 problem

SB05A6/RB05D5 create only native bit0 when legitimately reached. The current
historical M2x proof has RB05D5 bit0, not a bit1/bit2 producer. Conditional
SLLB571F requires an owned00A2=5, native CMP equality and JNE not taken:

```text
owned bit0 --first SLLB--> owned bit1
old unknown bit1 --same first SLLB--> unknown bit2 --5722--> BLOCKED
```

The first shift cannot bootstrap the first reader from its newly written bit1:
bit2 depends on the **old** bit1. To execute a second legitimate call/shift in a
serial history, the previous call must first pass5722 and genuinely return5801.
This is a bootstrap dependency, not permission to force the first JBS branch.
Two algebraic hypothetical shifts can transfer an earlier bit0 owner to bit2,
but do not prove two completed firmware invocations. Same-value shifts are fresh
storage generations; an unknown source stays unknown. Global native ordinal
must not reset across events/calls.

An independently owned oldbit1/full-byte/word source could break that dependency,
but none is integrated on the actual M2ah machine. Reset/test candidates do not
establish current runtime ownership. Stack/indirect or nested IRQ alternatives
remain Unknown, so this is **not proof that every possible real ECU history is
impossible**. A CAL stack word could overlap019A/019B under an unproved SSP domain;
it is not manufactured into a code-owned bit source.

## Alias/path audit and whole-tail return dependencies

The317-node route has131 conservative M2ai alias records, carried with source
and caller-context obligations. Specific symbolic narrowings are conditional:
native CLR/MOV gives X2=0 for058E..0597; X1 derives from signed extension of the
doubled selector byte, bounding03B6/03BE-based accesses away from019B/00A2;
USP0280 plus exact signed offsets addresses0212/0214/0216 under literal setup.
These address facts do not own the buffers' contents. Incoming SSP, external
helper effects, alternative LRB/SCB/SF, reset/test and nested IRQ remain Unknown.
Encoded word019B means019A/019B, not019B/019C.

Every CAL56BE starts with mandatory wordTMR2 at56BE, even mode1/no-write; IRQH is
conditional, TCON2 is conditional on the writer path. Frozen technical snapshots
are not timer evolution/IRQ delivery and no default-zero source is introduced.
011F modebit2 has **one full-byte owner**: caller-buffer copies at0408/5C35 write
word011E/011F; their source0216/0217 is not an independently owned live mode.
0128.3 history likewise needs genuine previous invocation/return and no intervening
clear/mask; ANDB0524's table-derived mask cannot be assumed harmless to history.

After571F the first gate is019B.2 at5722. The false/true routes then first need
00B8.0 at5728 /00B8.1 at5736, code-owned DP0358/035E and later pointed RAM/00A0.
5793 TM3 is the linear first hardware access, **not universal**: branches can
bypass to57A3 or57BE. Later TMR2/TMR3/TCON3, P1, indirect data and native RT5801
still require independent ownership/side-effect admission. None executes here.
Branch joins do not prove ordered side effects or justify choosing an unowned
5722 branch. Other JGT sites, including05BB, retain unresolved-primary gates;
M2tJgt233A and separate M2ah JLE evidence are unchanged.

Primary complete pages were visually reviewed with PDF skill for CAL/RT,
CMPB direct00A2,#5, JNE/JLT/JGE, SLLB off-object, JBS, SB/RB, TBR and addressing.
Recognition by decoder/executor is not admission. Generic off-object SLLB source
has a possible ZF-update mismatch with the primary CF-only form; it receives no
dynamic admission or global fix in this static milestone.

## Feasibility matrix (hypotheses, not ECU modes)

| Timeline | CFG / current evidence | Exact blocker |
|---|---|---|
|A:05ED->063B only|Historical disclosed technical seam|Earlier gates/history skipped; retained slot0; M2ah stops5722|
|B:0611->0614->063B|Static possible under assumptions|Native entry/slot/history, TMR2, first5722 and fullRT5801 unproved|
|C:0635->0638->063B|Static possible under assumptions|Same, plus timer-difference predicate5..31|
|D:0611->0614->0635->0638->063B|UnsatisfiableWithinAuditedCFG|Earlier sites mutually exclusive; return0614 joins063B, not0635|
|Reverse0635 then0611|UnsatisfiableWithinAuditedCFG|Return0638 directly joins063B|
|E:multiple interrupt invocations|BlockedByIRQ /Unknown ordering|Separate entry/IRQ frames, prior native returns and retained source history absent|

No timeline has sufficient current RAM/slot5/bit1/bit2/return provenance for a
new strict native sequence. No runnable operation or optional native prefix is
justified. Public42 invented model/schema cases cover first-reader bootstrap,
second hypothetical transfer, same-value generations, alias/byte/word hazards,
wrong-machine binding, missing/stale frames, host returns, slot5 authority,
IRQ/timer gates, conflicting paths and post-return old-bit012A.3 behavior.
They are not actual-ROM executions; the existing M2ai per-bit model is unchanged.

## Unchanged statuses and STOP

M2ai static provenance unchanged; M2ah Research/Blocked, stop-before5722;
M2ag CAL0664/FirstObservationNoWrite and pending0667 unchanged; M2af primaryAA
Blocked; M2v TechnicalSeeded56BE; M2w harness-scheduled0136; M2tJgt Blocked/Unresolved;
strictM2iBlocked. No retroactive promotion. Reader5782/5787, TM3, RT5801,
return0614/0638/0667, IRQ/fullboot, GUI/hardware NotRun. IRQNotInjected;
TimerEvolutionNotModeled; ElapsedTimeNone; EnclosingIRQFrame and recovered ECU
scheduler NotEstablished. FirmwareBIN0; PcInspectionOnly/NotFlashReady;
physicalRpmAvailablefalse; physical fuel/time/degrees unavailable; GUIr3paused;
D1/D2 interactiveNotRun. New private artifacts only underprivate/reports/m2aj.
Final report is saved last after exact-SHA CI3/3 and full protected comparison,
then STOP; no automatic M2ak or tail/IRQ/timer/return/JGT/GUI/hardware work.
