# M2bd - typed word0196 lowering and dataflow obligations

Result: **M2bd Typed IR-to-Form Mapping and Dataflow Obligations Established**,
only for the retained18-site software fragment. Classification:
`ReviewedStaticTypedLoweringSpecification`, NOT `GeneratedNativeProgram` or
`TargetMachineCodeEquivalenceVerified`. Static validation is the final operation:
no encoder/decoder call on the original site inventory, concatenation, emitted
bytes, assembly, placement, symbols, linker, adapter, CPU or firmware execution.

Exact base: `8fe005d1ba5f7b18f8df391b3fdf09d6330fad8e` (M2bc).
Branch: `codex/p28-word0196-typed-lowering-contract-m2bd`.
Immutable M2av IR SHA256:
`4fdbd6b7dbdd8f48d5a43e123ca93a33a003c22556a0c40b5296d5f409e085c4`.
All prior IR/C11/C#/M2aw/M2ba/M2bb/M2bc implementations and expectations remain
byte-identical. Runner0.43.0/protocol1/38 identities and admission unchanged.

## Independent evidence layers

The September1991 MSM66201 Instruction Manual has SHA256
`f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271`.
M2ay manufacturer expectation ledger SHA256:
`a268815a0c04a4e2f0fccb64021ead26e1cbdaa02c1cc435d816f7d35fa2ab44`.
The main agent freshly reviewed25 complete preserved pages: PDF9,14..18,21..22,
25..28,76,77,90,119..121,124,153,160,163,173,197,208. Separate oracle author
reviewed the same complete pages independently. Original PDFs remain private.

Five layers are checked separately: immutable M2av structure, M2ba exact primary
form specification, M2aw context, independently authored path/dataflow oracle,
and the new lowering contract. These are not five independent manufacturer
documents. No ASM662/DASM/Doc66207/generated opcode table/Rust FULL_OPCODES or
encoder output is a lowering semantics/expectation source. No legal clean-room
certification is claimed; historical third-party exposure remains disclosed.

## Exact18-to15 mapping

Every PC is an audited identity/CFG reference, **not placement permission**.
These are typed obligations, not an assembly listing. Numeric values below are
hexadecimal; A names the accumulator whose scoped operation acts on AL8.

| Site | Exact FormId | Typed operand obligation | Length |
|---|---|---|---:|
|556F|lb-a-page|AccumulatorA,PageOffset8(8E)|2|
|5571|sllb-a|AccumulatorA|1|
|5572|rolb-page|PageOffset8(8E)|3|
|5575|lb-a-r0|AccumulatorA,Register0(0)|1|
|5576|andb-a-page|AccumulatorA,PageOffset8(8E)|2|
|5578|cmp-page-imm16|EvenPageOffset8(96),Immediate16(00C0)|5|
|557D|jlt-rel8|TargetPC16(55BF)|2|
|557F|movb-r1-page|Register1(1),PageOffset8(17)|3|
|5582|andb-page-a|PageOffset8(17),AccumulatorA|3|
|5585|jbs-page-bit7|PageBit7(2A,7),TargetPC16(5592)|3|
|5588|jbs-page-bit5|PageBit5(24,5),TargetPC16(5592)|3|
|558B|andb-page-a|PageOffset8(8F),AccumulatorA|3|
|558E|orb-page-imm8|PageOffset8(2A),Immediate8(01)|4|
|5592|lb-a-page|AccumulatorA,PageOffset8(8F)|2|
|5594|orb-a-imm8|AccumulatorA,Immediate8(F0)|2|
|55BF|lb-a-imm8|AccumulatorA,Immediate8(0F)|2|
|55C1|stb-a-page|AccumulatorA,PageOffset8(17)|2|
|55C3|stb-a-page|AccumulatorA,PageOffset8(8F)|2|

No P2 instruction at5596/55C5, extra forms/registers/bits, CAL/RT or new ISA
admission. Static branch differences are mathematical64/10/7, within signedrel8;
no displacement bytes, wrap repair, relaxation, trampoline or relocation.

## Page, local-bank and alias obligations

LRB0021 fixes page0100 and local bank0108..010F. DATA0117/0124/012A/018E/018F/
0196 map to raw17/24/2A/8E/8F/96 respectively. Page operands are not full DATA16
addresses. CMP uses even96 and a read-only LE16 word0196/0197; code-owned00C0
is NOT a read of RAM00C0, RPM, timer or physical unit.

Local r0/r1 are DATA0108/0109, not page offsets08/09. Consecutive LE pairs
er0..er3 alias r0/r1 through r6/r7. MOVB557F changes **high byte of er0**;
low r0 remains retained, but the whole er0 is NOT preserved on not-below paths.
AH is preserved by every scoped byte accumulator update. M2aw's aggregate
0108/count8 local-bank access row is not an assertion that557F writes0108.

CPU odd-word align-down is distinct from this stricter EvenPageOffset8 profile;
no silent alignment/rebase, host-pointer cast or new indirect/stack alias claim.
SCB is incomingPSW&7, not fixed2. All pointing banks and SSP retained. Wider
alias absence, native SF meaning/storage/width and stack safety remain unknown.

## DD forward must/may analysis

Initial domain{0}, {1}, or{0,1} is analyzed. First556F accepts either initial DD,
then AssignDataDescriptor establishes0. `ddMode=R` means transfer, NOT incoming
DD0 requirement. The abstract entry{0,1} is `IncomingDDUnknown`, not a conflict.
Singleton1 is KnownDD1; every later site has mustDD0/may{0}. Missing/reset-to1
effects fail at5571's real RequiresDD0 obligation.

RequiresDD0:5571,5576,5594,55C1,55C3. Other sites accept both as form restrictions.
Executed LB556F/5575/5592/55BF resets0; all other transfers preserve. Both edges
of557D retain0; both stop boundaries must0. No Cpu instance or codec performs
this transfer: it is static primary-semantic analysis over the actual IR graph.

## Flags, reaching writers and liveness

Per-site functional reads and form-selection reads are separate. ROL5572 and
JLT557D functionally read CF; the five DD0 forms select width through DD rather
than reading it as an arithmetic operand. LB writesZF/DD, SLL/ROL writeCF,
AND/OR writeZF, CMP writesCF/ZF. JLT/JBS/MOVB/STB write no flags.

| Dependency | Required reaching writer | Obligation |
|---|---|---|
|CF into ROL5572|SLL5571|Through incoming carry, not circular rotation|
|CF into JLT557D|CMP5578|Unsigned borrow; no intervening CF clobber|
|ZF into join5592|5582 or558E|Path-dependent, subsequently killed by LB|
|CF at both exits|CMP5578|Below1; not-below0|
|ZF at55C5 /5596|LB55BF /ORB5594|Both0; intermediate ZF effects still required|
|DD at55C5 /5596|LB55BF /LB5592|Both0|

Forward reaching-writer unions and backward liveness are computed over the DAG,
not read from an editable JSON verdict. Terminal snapshots seed all16 PSW bits:
CF15/ZF14/HC13/DD12 and retainedPSW0..11 (including SCB0..2). Functional entry
live flags are HC and the retained12 bits; initialCF/ZF/DD are killed before
their required consumers or exits. Initial AL is similarly overwritten.

Every site reports reads/writes/preserved bits, reaching writers in/out, initial
value-live and backward live-in/live-out. Separate register/RAM liveness includes
AL/AH, local bytes, page bytes, bank/pointing/stack retention. No future clobber
permission follows from a value-dead result: **all intermediate architectural
flag writes and ordered memory effects remain mandatory**. HC/otherPSW unchanged;
no native SF-to-host-bool inference. Wider downstream liveness is NotEstablished.

## Complete CFG and four path obligations

Entry556F has a common seven-site prefix through557D. CF1 leads to55BF/55C1/55C3;
CF0 leads to557F/5582 then bit gates. True5585 skips5588 entirely; false5585
allows5588. Both false execute558B then558E. All18 sites are reachable; the
actual graph has21 edges, no cycles, undefined successor or additional terminal.
Neither stop boundary is executed or interpreted as RT.

| Path | Branch choices | Instructions | Stop before | Ordered writer sites | Memory accesses |
|---|---|---:|---|---|---:|
|A below|557D CF1|10|55C5|5572,55C1,55C3|8|
|B first gate|CF0;012A.7=1|12|5596|5572,557F,5582|12|
|C second gate|CF0;012A.7=0;0124.5=1|13|5596|5572,557F,5582|13|
|D both false|CF0;both bits0|15|5596|5572,557F,5582,558B,558E|17|

B must not read0124. Writes carry exact site/address/width/operation/order and
sameValueWrite=RetainFreshOrdinal. Conditional writes remain skipped; localr1,
scratch, RMW and numerically unchanged stores cannot be removed. In D,558E's
012A write cannot move before558B's018F write. A cannot acquire not-below effects,
nor can B/C/D acquire55C1/55C3. These are symbolic obligations, not a new native
generation journal. All intermediate flag-effect expressions also remain listed.

AL at A is0F. Other paths finish with their final018F ORF0, hence ZF0; CF is
constrained by the JLT path assumption. Symbolic expressions derive from reviewed
IR primitives; independent test-side mathematics checks them on invented scalars.
No emitted instruction sequence or concrete CPU state is accepted by the analyzer.

## Provenance, entry/exits and historical witness limit

DATA0196 retains native05EB writer generation with historical54FA/5578 same-
generation reads. 0117 retains once-initial/native history;018E/018F scratch/native
history;012A neighbors;0124 upstream ownership;0128.2 once-initial masked history.
These are obligations, NOT new runtime seeds/owners. No host identity, second
machine, reseed at556F, synthetic SSP frame or new event source is allowed.
05ED->54F5 remains ExplicitHarnessSchedule; reset/fullboot flow not recovered.

Entry is NativeBasicBlockEntry, not NativeCFunctionEntry or a proven CAL frame.
Exits before5596/55C5 retain A/AL/AH, PSW/SCB, LRB, all pointing banks, SSP, relevant
RAM, ordered effects and branch-selected continuation. No prologue/epilogue,
push/pop/adapter/implicit C return or target compiler flag-preservation assumption.

Historical42 observations/552 snapshots/170 writes remain unchanged. The13-step
path has0 historical native witnesses and is **StaticPrimaryAndInventedCoverage**,
not a newly validated43rd observation. Historical10/12/15 paths retain existing
witnesses only; this milestone creates no new original-ROM execution.

## Own static implementation and honest QA phases

`typed_lowering_contract.json` is a closed metadata layer. The pure
`typed_lowering_analysis.py` imports only standard-library JSON and public FormId,
with own independently reviewed18-site/form/effect constraints. It traverses the
supplied IR, propagates actual DD effects, computes reaching/liveness and symbolic
paths. It does NOT merely compare an IR digest or count18 sites. Strict recursive
typing distinguishes bool from int. Errors are deterministic code/path refusals.

`validate_typed_lowering_contract.py` pins every safety-bearing metadata field,
compares computed18-site/path obligations and separately checks seven immutable
upstream file identities. Its CLI accepts no external paths/ROM. The static AST
dependency guard is defense-in-depth source review, **not an arbitrary-Python
sandbox** or permission to run untrusted code. Pure APIs mutate neither input.

`typed_lowering_oracle.py` was independently sealed before the analyzer existed;
honest observation AnalyzerNotImplemented/calls0/fakeREDfalse. An independently
detected preparation label bug for singletonDD1 was corrected in one line before
analyzer comparison; original oracle/seal/expectations remain preserved, numeric
DD expectations unchanged. The current seal is honestly separate from the original.

An initial actual CLI invocation refused superclass __init__ under its own
reflection guard. Exception.args initialization repaired that new source without
weakening the guard or changing any semantic expectation. Initial test integration
compared analysis dictionaries despite three documented additive contract result
fields; its adapter now checks every shared field plus those exact three fields.
Both diagnostics remain private; no catch-and-pass or hidden semantic mismatch.

Independent source review found that the initial AST guard accepted three
built-in I/O/interactive call strings, although the actual pure source had none.
Four input/print/breakpoint/help names are now refused; one current-source
control plus four regression strings are parsed only, NEVER executed. Separate
76-case policy/malformed audit and293 presealed dataflow checks pass. A stale
private import-inventory check was narrowly corrected after an unused import
was removed; its original failure/snapshot remain preserved.

```text
python -B research/p28-word0196/validate_typed_lowering_contract.py
python -B research/p28-word0196/typed_lowering_tests.py
```

Tests independently check all18 mappings/15 forms, three DD domains,12 complete
path checks and54 flag-dataflow rows. Invented symbolic terminal/memory checks
include all65536 word values,256x256 rotate/r0 pairs, gate-neighbor/PSW domains
and same-value stores. Mutation tests alter real IR instructions, operands,
effects, dependencies and CFG, plus closed metadata/permissions/provenance;
duplicate labels/mutations and actual call counts are reported separately.
No semantic expectations are rewritten from analyzer output for PASS.

Actual per-run counts:135334 symbolic checks =135333 distinct full invented
input states +1 overlap;245 mutation labels =241 distinct mutated inputs +4
overlaps;490 deterministic refusal calls. Separate source-policy checks5.
All18 mappings/15 forms;3 initial DD domains;12 path checks;54 flag rows and54
data-liveness rows; failures/skips0 and firstMismatch=null. These counts are not
summed across local review/finalQA/CI repeats and are not new native observations.

Ubuntu/Windows receive only one additional research-only static step. Existing
Rust/Core/CLI/Desktop/format/privacy/portable and all9 older research steps remain.
Full local QA repeats unchanged M2bc/M2bb/M2ba/M2aw-M2az and M2av C11/IR/C#
invented/historical checks separately; their nonzero synthetic in-memory codec
bytes are NOT M2bd generation. Private exact-SHA QA/CI/preservation receipts and
the final last-written report contain actual counts and hashes.

## Unresolved boundaries and STOP

M2bc compatibility/M2bb encoder/M2ba route retained; M2az rights/M2ay build/
M2ax acquisition remain blocked. M2aw context and M2av source equivalence retained;
M2auINT/M2atDEC_HC/M2anSLLB complete. WDT3C/JGT C8 unresolved; CAL2689/RT5C80
NotRun; SSP/ADC blocked;019B frontier/M2ah STOPbefore5722 unchanged;019B.2 owner,
ECU scheduler/target compiler ABI/integration/native-program equivalence unknown.
IRQNotInjected/TimerEvolutionNotModeled/PcInspectionOnly/NotFlashReady; physical
fuel/time/degrees unavailable. Inquiries NotSent; GUI/hardware/fullboot NotRun.

Own M2bd actual-ROM/ASM662/assembler/codegen calls and target bytes/streams/
assembly/object/HEX/FirmwareBIN **all0**. No output grants native authority.
One proposed NEXT, NOT started: independently specify an invented-only relocated
layout feasibility contract (addresses/sizes/branch reach and preservation), with
no emission, original-ROM placement or runtime permission. Separate authorization
is required. STOP: no M2be/actual lowering/emission/stream/relocation/linker/ROM
replacement/firmware/WDT/C8/reset/fullboot/GUI/hardware continuation.
