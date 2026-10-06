# M2ai - DATA019B.2 semantic-owner provenance boundary

M2ai is **static provenance research**, not a new runnable operation. The exact
delivery base is `73275d6cfcaa4b2149ae065627ffea2a985e980c`; its separate Windows
PID/START/READY stabilization commit remains in ancestry. The original M2ah
research SHA is `4261bf04e38877acffd7079fc62f3d048d6f99b3`.
Runner stays **0.40.0**. No runner/ISA/admission, scenario, CLI or operation
contract changes. No new actual-ROM execution, semantic input or firmware BIN.

## Result and remaining seam

The concrete static value-transformer candidate is **571F SLLB off019B**:
new bit2 is **old bit1**, not the bit0 just written by05D5 and not an owned
whole-byte storage generation. Native SB05A6/RB05D5 write **only bit0**.
The bit2 reader is **5722 JBS off019B.2**, with candidate outcomes5725/5733.
Physical meaning remains **Unknown**; no RPM/fuel/injector/VTEC/timer label.

The actual M2ah machine has00A2=0: CMP5719/JNE571D takes5722 and skips571F.
No integrated bit2 owner is thereby established. M2ai does not execute5722,
5725 or5733. Its status is **CandidateOnly / CurrentRuntimeOwnerNotEstablished**,
not a recovered scheduler or a validated native handoff.

The disclosed PC-only05ED->063B seam also skips enclosing native calls
**0611->56BE and0635->56BE**. Those earlier invocations could reach571F
conditionally and shift earlier bit history before the later CAL0664 invocation.
This is **OwnerCandidateInSkippedEnclosingCaller**, not an automatic source for
M2ah. Required evidence is an established earlier bit1 lineage,00A2==5 at a
legitimate invocation, caller reachability/chronology and exclusion of relevant
overwrites/aliases. No such same-machine handoff is dynamically established.

## Complete listed-extent inventory methodology

The fresh private audit verifies **all11,499 decoded instruction extents** in
the matching original/listing: every listed byte and every independently
selected opcode-pattern length matches. It considers all2,623 pinned opcode
patterns, exact DD forms/operands, encoded address fields and instruction widths.
Text labels alone do not select candidates. This is the complete *listed code*
inventory, not a proof that unlisted bytes, indirect entry points or every
runtime caller have been discovered. A decoded form is not execution admission.

Current-page addressing uses LRB bits12..5; local register base uses the13-bit
LRB shifted by3. The listing's `108` denotes **local bank base0108**, not LRB0108:
LRB0021 produces that bank and current page1. Listing bank/USP/DD annotations
are static context, not proof of live runtime ownership for every caller.
An alternative page context is retained as Unknown unless excluded independently.

Data/system-stack word accesses clear the effective-address low bit. A word
encoded019B therefore overlaps019A/019B, not019B/019C. User-stack and code-space
forms are not assigned this rule. Local-register aliases, X1/X2 displacement,
[DP], USP-relative, indirect pointers, exchange, RAM test/clear loops, implicit
system stack and possible accumulator STACK-mode domains are considered.
ROM LC/CMPC source reads are not falsely counted as RAM019B readers.

Each private candidate records PC/form/length, mode, symbolic/conditional EA,
width/mask, source, old/new effect, flags or an explicit evidence gate, callers,
preconditions, dependencies and classification. Primary PDF pages were reviewed
in full for the serious exact forms and address/word-boundary rules; no
mnemonic-wide permission follows. Exact OEM bytes and listing windows stay private.

## Concrete readers and writers under the listed page context

| PC | Exact abstract form | Semantic effect | Classification |
|---|---|---|---|
| 05A6 | SB off N8.0 | bit0=1; bit2 unchanged | PreservesBit2Only |
| 05D5 | RB off N8.0 | bit0=0; bit2 unchanged | PreservesBit2Only |
| 571F | SLLB off N8 | new bit2=old bit1; bit0=0 | FullBytePotentialWriter; source history required |
| 5722 | JBS off N8.2,rel8 | read bit2; static targets5725/5733 | StaticKnown; DynamicNotRun |

There are **0 concrete explicit bit2 SB/RB/MB writers**, **2 preserving bit0
operations**, **1 concrete whole-byte transformer**, and **0 concrete fixed
word-overlap writers** under the listed contexts. The4 concrete storage reader
sites comprise one explicit bit2 branch, one whole-byte shift read and two bit0
RMW storage reads; those last two are not semantic bit2 consumers/producers.
Absolute low-page byte forms cannot directly name019B.

Backward CFG has exactly two listed predecessors of5722: JNE571D and SLLB571F.
The latter has an immediate native fallthrough edge with no intervening listed
instruction, but an owned source bit1 and an actual legitimate invocation are
still required. The former is the actual M2ah route and performs no bit2 write.

## Indirect, context-dependent and reset candidates

Indexed/indirect domains are **not declared harmless**. The final conservative
inventory has5,986 unknown-domain access records at5,277 instruction sites;
5,485 potential write records at5,099 sites. These are conservative records,
**not observed019B writes**. Of them4,602 are conditional accumulator STACK-mode
records, not4,602 demonstrated stack accesses. The remaining domains include
125 X1,13 X2,299 indirect,180 USP-relative,440 system-stack,321 local-bank and6
alternative-page records. Hardware interrupt-frame stores are a separate
unresolved implicit domain, not another decoded instruction or an injected IRQ.

For example3174 MOVB off N8,r1 and31BE DECB off N8 address029B in their listed
page2 context. They are not presented as actual019B writers. An alternative
LRB page1 would alias019B, so the audit retains a conditional alias/source gate
instead of assuming all caller contexts are fixed by a text annotation.
Likewise r3/er1 can overlap019B under a different8-byte local bank; their
whole-ROM LRB dominance is not established. Known disjoint low offsets are
excluded by address arithmetic rather than by labels.

Three serious indirect word sites have **reset/test-only** roles:

- 2710 ST A,[DP]: CLR A2706 supplies0; the descending DP sweep can overlap019A/019B
  if startup gates and USP/loop conditions permit that iteration. Fullboot NotRun.
- 5C68 XCHG A,N16[X1]: reset RAM-test caller2689/268D supplies5555/AAAA patterns;
 0084+X1 can overlap019A/019B during the descending test range.
- 5C6C XCHG A,N16[X1]: the second exchange restores the prior RAM word, whose
  semantic source is not made owned by the first pattern write. Same numeric
  restoration still creates storage writes and must not steal source provenance.

These are word-overlap candidates within the indirect inventory, not three
additional fixed-address writers. ResetValueReference is not
CurrentRuntimeSemanticOwner. JGT loop conditions retain the historical unresolved
primary gate; M2ai neither resolves JGT nor executes full boot to choose a value.

## Enclosing interrupt-domain relationship

INT1 entry0379 (vector0026) and serial RX BRG entry03ED (vector000E) share the
enclosing code. Setup and earlier flow involve IE, PSW/SCB, LRB/USP, TM0/TMR0/IRQ,
and helpers before063B. The two skipped CAL56BE sites belong to this context.
Bit0 stores themselves are software constants, but reaching the relevant shift
history depends on the unestablished enclosing invocation and source history.
Static reachability is not recovered ISR delivery, an enclosing IRQ frame or a
software-only scheduler proof. TimerEvolutionNotModeled; IRQDeliveryNotInjected.

## Independent per-bit model and invented-only regression coverage

The internal C# research model owns transitions independently; it has no CPU/RAM
write API, operation or accepted wire input. It separates a tracked storage
generation from each bit's semantic identity: machine identity, address/bit,
writerPC, eventIndex, monotonically increasing global write ordinal, value,
source kind and retained source lineage. Rust journal observations never become
expected ownership. No model result is inserted into the M2ah machine.

RB/SB update only the selected semantic bit; all others retain their owner through
RMW. A same-value selected-bit or whole-storage write is fresh. Whole-byte/word
transfers own a bit only from independently established code/retained sources;
unknown source invalidates it even if its numeric value is known. Shift transfers
old bit1 lineage into new bit2, rather than granting ownership from old bit0's
storage generation. Unresolved aliases invalidate strict reader proof without
inventing a proven new storage value/generation. Reset, timer/IRQ/peripheral and
technical/diagnostic numeric sources do not authorize a strict runtime reader.

Invented tests cover RB/SB bit0 preservation, RB/SB bit2 freshness, owned/unknown
byte sources, aligned word019A/019B overlap, same-value writes, shift source-bit
lineage, unknown aliases, stale/forged/equal-value wrong-writer identities and a
second machine. Static invented fixtures cover direct/current-page/local-bank,
word/indexed/DP/USP/stack and reset-sweep domains. Closed historical M2ah scenario
tests reject initial/per-event019b2, branch/expectedBranch, host byte/word writes,
fake owner/reset authority, PC5722/5725/5733 and serialized/second-machine handoff.

## Mandatory unchanged boundaries

M2ah remains **Research/Blocked**,6 strict prefixes+1 control; STOP before5722;
019B.2 semantic owner not established on its actual machine.5782/5787 NotRun;
5793/TM3 NotRun; frame0667 EstablishedPendingReturn, native return0667 NotRun.
M2ag CAL0664/FirstObservationNoWrite and M2af primaryAA Blocked remain unchanged.
M2tJgt Blocked/Unresolved; M2ah JLE static evidence unchanged.

Later00B8.0/.1,00A0 and pointed0358/035E are not new inputs and have no new dynamic
admission. No5725/5733, full tail, timers, P1, RT5801, second producer,2330/JGT,
GUI/hardware/fullboot or M2aj work. RecoveredCallerScheduler,
Recovered0196Scheduler, RecoveredEcuScheduler and EnclosingIRQFrame NotEstablished;
ElapsedTimeNone; PcInspectionOnly/NotFlashReady; physicalRpmAvailablefalse;
physical fuel/time/degrees unavailable; strictM2iBlocked; GUIr3paused/NotRun;
D1/D2 interactiveNotRun; FirmwareBIN0. Final delivery/QA/counts and exact-SHA CI
are recorded in the new private M2ai report; final report is saved last, then STOP.
