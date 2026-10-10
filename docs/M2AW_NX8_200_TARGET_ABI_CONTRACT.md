# M2aw — nX-8/200 target context and memory-layout contract

## Result and scope

`M2aw Target Architecture/Context Contract Established` applies only to the
confirmed standard-device architecture and the bounded M2av software fragment
`556F -> STOP before5596/55C5`. `TargetCodeGenerationNotReady` remains.
This is research metadata, not an original Honda ABI, a generated target program,
or permission to execute, replace or flash firmware.

The immutable parent is M2av commit
`6b524c0e244444f0d98901ef853e42056f2b1127`:
[source-level equivalence](M2AV_WORD0196_STRUCTURED_C_EQUIVALENCE.md),
[historical native scope](M2Z_WORD0196_SOFTWARE_ALTERNATE.md),
[scheduled handoff](M2Y_WORD0196_CONSUMER_HANDOFF.md),
[CAL/RT research](M2AD_CAL_RT_ROUNDTRIP.md), and
[source independence](M2J_ADD_ER3_ISA_EVIDENCE.md) remain unchanged.
18 instruction sites/15 forms are not enlarged. Runner0.43.0, protocol1 and
38 semantic/accounting identities remain unchanged. Actual-ROM executions0;
target tool executions0; target object/BIN0; hardware/GUI0.

## Three evidence levels

| Level | Established within scope | Conditional or missing |
| --- | --- | --- |
| Architecture | Standard MSM66201/66207 nX-8/200 identity; registers, address spaces, selectors, byte/word rules and documented CAL/RT | Customer ECU ASIC identity/revision; complete SF interpretation; exact reviewed MSM66207 RAM interval |
| Compiler ABI | No nX-8/200 C ABI established | Compiler/version/target proof, types/pointers/structs, arguments/returns, saved registers, frames, helpers and symbol conventions |
| Firmware integration | Historical branch entry556F, two software continuation boundaries, exact bounded flags and ordered RAM effects | Real upstream scheduling/physical ownership, adapter, stack capacity, downstream integration, code placement, whole-ROM and bench validation |

Architecture facts do not determine compiler ABI. Host C11 compilation does not
establish target compilation. A proposed convention is not an OEM convention.

## Primary sources and exact applicability

Full relevant PDF pages were visually reviewed; raw PDFs and historical native
records remain private. Page references below are printed pages unless stated
as PDF page numbers. These are manufacturer documents hosted by third parties.

| Source | Reviewed evidence | Limit |
| --- | --- | --- |
| [MSM66201 Instruction Manual, first edition September1991](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/Oki_66201_Instruction_Manual.pdf) | 1-5, 1-7, 1-10..1-24; CAL3-29; RT3-125; M2av's independently reviewed instruction semantics | Applicable named standard architecture, not customer ASIC identity |
| [E2E1027-27-Y4, January1998](https://files.boostednw.com/HONDA/66207.pdf) | Cover; PDF8..16: register/SFR map, standard memory, independent program/data spaces | MSM66201 RAM512B/ROM16KiB; MSM66207 RAM1024B/ROM32KiB does not identify the ECU ASIC |
| [MAC66K third edition November1993, package v4.XX](https://datasheet.datasheetarchive.com/originals/library/Datasheets-UEA1/DSAFRAZ0014345.pdf) | 1-1/1-7; TYPE3-4; DCL3-32..33/4-23..24; segments4-163/168/174; USING4-194/208/210; linker5-1/4/16..19; converter7-3/5/8 | Documents nX-8/200 assembler support, not a working installation or C ABI |
| [CC665S v2.01, first edition March1999](https://datasheet.datasheetarchive.com/originals/library/Datasheets-A1/DSAUTAZ0012723.pdf) | User6..8/22/90/153..154: target options, output family, register and frame conventions | Explicit nX-8/500 and 500S only; never imported as 200 support |
| [OKI Microcontroller Data Book, fifth edition June1990](https://www.bitsavers.org/components/oki/_dataBooks/1990_OKI_Microcontroller_Data_Book.pdf) | Tool table printed14 | CC66K under-development lead in MSM66301 row, not a delivered nX-8/200 compiler |

## CPU context mapping

`word0196_state` is an offline logical snapshot, not a memory-mapped native
struct. SFR addresses below are CPU DATA addresses, never `offsetof` values.

| Host field | Native counterpart / width | Ownership and obligation |
| --- | --- | --- |
| `a`, low/high8 | A16 at DATA0006/7; AL8/AH8 | Reproduce AL effects; AH retained, no byte-load sign extension |
| `psw` | PSW16 at DATA0004/5 | CF15, ZF14, HC13, DD12, SCB2..0; retain all non-written bits |
| `pc` | Native instruction PC16 | Entry556F; branch-selected continuation, not C return address |
| `lrb` | LRB16 at DATA0002/3 | Retain0021; page0100 and local bank0108..010F |
| `x1/x2/dp/usp` | Four16-bit pointing registers selected by SCB | DATA base0080+8*SCB, offsets0/2/4/6; selected values and other banks must not be clobbered |
| `ssp` | SSP16 at DATA0000/1 | Preserve actual incoming value; no scoped stack access; historical07FE is technical context, not a free frame/reset proof |
| `local[0..7]` | Native r0..r7 bytes at0108..010F | r0 read; r1 written only on not-below path; r0/r2..r7 retained; er pairs alias consecutive LE bytes |
| Relevant RAM fields | DATA0117/0124/0128/012A/018E/018F/0196/0197 | Native source lineage and exact ordered effects, not host field addresses |
| `sf` | Conditional SF-clear symbol; native storage/width unresolved | Host replay field retained; no default0 and no invented PSW bit |
| `halted` | Host replay/testing metadata | Not an ordinary native register or runtime owner; host entry requiresfalse |

Current page = `(LRB & 1FE0) << 3`; local base = `(LRB & 1FFF) << 3`.
Equivalent16-bit truncated formulas are recorded in the contract. LRB0020 has
the same page0100 but local bank0100..0107; LRB0041 gives page0200/bank0208.
These are architecture alias examples, not admitted substitute entry contexts.
SCB is `PSW & 7`; historical SCB2 selects0090..0097, not a universal ABI value.

### SF and stack uncertainty

The applicable MSM66201 manual prints `SF <- 0` in CAL and RT Function sections.
MAC66K4-116 says stack flag is only on nX-8/300; its STACK/A/OPRT description is
300-specific. Both statements are retained as a primary ambiguity. Neither
absence of SF on200 nor the300 STACK/A interpretation is established. No scoped
M2av instruction writes SF. Historical records do not serialize actual SF.

Documented CALaddr16 stores nextPC at oldSSP, then decrementsSSP by2; RT first
incrementsSSP by2, then loadsPC. RTI instead restores PSW/LRB/A/PC from a different
frame and is not an ordinary RT. Branch entry556F creates no CAL frame; existence
and safety of earlier caller frames remain unknown. Actual SSP may alias RAM,
registers or SFR; technical07FE proves neither available stack nor safe prologue.

## Exact RAM map and aliases

Program and DATA are separate16-bit address spaces. Word storage is little-endian;
the CPU masks an odd word address's low bit to0 (manual1-18), rather than supplying
a generic alignment-fault guarantee. The bounded fragment uses even0196.

| DATA | Scoped mode/width | Native suffix reads | Native suffix writes | Ownership / physical role |
| --- | --- | --- | --- | --- |
| 0108..010F | LRB local bank; eight8-bit bytes | r0 at5575 | r1/0109 at557F only not-below | Earlier native local context; physical role unknown |
| 0117 | Current page8 | 557F,5582 | 5582 or55C1 | Historical once-initial input, then retained native suffix lineage; physical role unknown |
| 0124 | Current page8 | Second gate5588 only if first false | None | Retained upstream software gate; physical role unknown |
| 0128 | Retained boundary byte8 | None in suffix | None | Historical masked input; not runtime physical-owner proof |
| 012A | Current page8 | Gate5585 and RMW558E | Bit0 at558E only both gatesfalse | Neighbor bits retained; physical role unknown |
| 018E | Current page8 | 556F,5572,5576 | ROL5572 | Historical scratch followed by native history; physical role unknown |
| 018F | Current page8 | 558B,5592 | 558B or55C3 | Branch-specific scratch; physical role unknown |
| 0196/0197 | Current page16, LE | CMP5578 | None | Native05EB generation; historical54FA/5578 same-generation readers; not proven RPM/timer |

All listed bytes lie in standard MSM66201 internal RAM0080..027F (manual figure1-3).
MSM66207's1024-byte size is confirmed; a complete exact contiguous range was not
independently established from the reviewed primary pages and is not inferred
from size. Customer ASIC applicability remains conditional for both variants.

Potential byte/word overlaps include0116/0117,0124/0125,0128/0129,012A/012B,
018E/018F and0196/0197. A word reference0197 addresses the aligned0196 pair.
Other LRB banks, indirect/indexed accesses, pointing registers and stacks can
alias DATA; global absence of aliases is not proved. Alias documentation grants
no additional access/ISA admission. Compiler struct layout does not map these
addresses. A future implementation needs verified absolute-address mechanisms,
assembly constraints or placement controls; no host pointer cast is authorized.

## Entry and continuation contract

| Entry kind | Meaning | Status |
| --- | --- | --- |
| NativeBasicBlockEntry | Historical JNE5501 selects556F with retained CPU/Bus state | Identified; real firmware integration conditional |
| NativeSubroutineEntry | Entry supplied by native call with a documented return frame | Not established at556F |
| HostReplayFunctionEntry | M2av C function takes an offline snapshot | Host-only verified domain |
| ProposedTargetAdapterEntry | Future context-preserving implementation | Not implemented or verified |

Historical DATA0196 came from native05EB; the05ED->54F5 seam remains
`ExplicitHarnessSchedule`. No recovered ECU scheduler or new source owner is
claimed. Host annotations, equal stale words, reseeding at556F or second-machine
handoffs cannot establish native current-generation ownership.

A future adapter must preserve live context and RAM continuity without assuming
an ordinary C prologue, changing bank selectors, clearing unknown SF, allocating
an unproved stack frame or manufacturing input values. These are requirements,
not proof that such an adapter exists.

| Stop-before continuation | Final AL | CF/ZF/DD | Preserved context |
| --- | --- | --- | --- |
| 5596, not-below | Final DATA018F ORF0 | 0/0/0 | AH,HC,otherPSW,SCB,LRB,pointing registers,SSP and unaffected RAM/local bytes |
| 55C5, below | 0F | 1/0/0 | Same preservation; r1 is not written on this path |

Both are native CFG continuations before P2, not RT or safe C returns. The incoming
AL/PSW and peripheral boundary are identified; wider downstream liveness is not
established. A verified jump or trampoline is only a future static option.
No P2 execution, trampoline, call frame or ROM replacement was implemented.

## Semantic obligations beyond final RAM

LB writes onlyAL, setsZF from the byte and clearsDD; AH/CF/HC retained. FirstLB
clearsDD before byte-accumulator forms. SLL updatesCF from oldAL7 without changingZF;
ROL uses that carry and produces its ownCF. CMP uses unsigned16 DATA0196 vs00C0,
sets borrowCF/equalityZF, and retainsA/HC/DD. JLT usesCF; the012A.7 gate precedes
0124.5 and preserves flags. ANDB/ORB updateZF; STB/MOVB preserve flags.

Ordered DATA write sites are:

- Below:5572 ->55C1 ->55C3.
- Not-below, either gate taken:5572 ->557F ->5582.
- Not-below, both gatesfalse:5572 ->557F ->5582 ->558B ->558E.

Same-value stores remain separate writes; skipped stores must remain skipped.
A compiler could remove/reorder accesses, synthesize different flags, change
PSW/register banks or add stack writes. `volatile` alone proves neither native
flags nor bank, stack, ordering or continuation equivalence. Applicable compiler
documentation, explicit target semantics, generated-code inspection and future
bounded execution verification are separate gates. No unverified attributes added.

## Toolchain feasibility

| Candidate | Primary finding | Availability / boundary |
| --- | --- | --- |
| MAC66K v4 / RAS66K | nX-8/200 documented; exact `TYPE(M66201)` example; TYPE loads matching.DCL for device/space/form checks | No provenance-verified operational installation; missing/badDCL is fatal; exact MSM66207 DCL not acquired/verified |
| RAS66K sections/symbols | Absolute CSEG/DSEG AT and ORG; SEGMENT/RSEG relocatable CODE/DATA/BIT; PUBLIC/EXTRN | Documentation, not a generated object or safe ECU placement |
| RL66K | Resolves relocatable.OBJ into.ABS, maps public symbols/segments; /CODE and /DATA placement | No runtime/linker-map verification; v2/v4 object formats incompatible |
| OH66K | Absolute object to IntelHEX default or MotorolaS2 with /S | Not documented flatBIN production, ROM checksum or firmware readiness |
| CC665S v2.01 | /nX500 and /nX500S; output500/500S mnemonics and family-specific frames/register conventions | /T merely emits an unvalidated TYPE string; cannot create200 support or ABI |
| CC66K historical lead | Under-development catalog entry associated with MSM66301 | No delivered independent200 compiler or ABI established |
| asm662/dasm662 | Pinned derived source/opcode research lead | Neither manufacturer proof nor OEM ABI; no verified target assembler run in M2aw |

USING directives describe assembler assumptions and emit no initialization.
PAGE/DATA/PREG assumptions must match actual LRB/DD/SCB. USING LREG and AER/AR
aliases are500-only, not available for200; nX-8/500 register-bank formulas must
not be substituted. A successful assembler would still not prove instruction
semantics, current native ownership, continuation safety or whole-ROM integration.
No archival executable downloaded, installed or run; no license bypass or inquiry.

| Route | Found evidence | Blockers and next bounded experiment |
| --- | --- | --- |
| A: C -> target compiler -> object/linker | Host source and documented assembler package only | Blocked: independently applicable200 compiler, ABI/types/memory model/helpers/linker and exact output verification; first obtain applicable primary compiler/ABI proof |
| B: verified IR -> assembly -> assembler/linker | Independently reviewed IR and documented200 assembly route | Conditional/not-ready: operational tools, lowering, register allocation, flags/context/write order, encoding/branches/placement/continuations; review a bounded lowering contract only after tool verification |
| C: verified algorithm -> manually reviewed native fragment | Same exact semantic/context obligations and documentation | Conditional/not-ready: exact operational assembler, reviewed listing and bounded equivalence/placement; first small manual proof only after tool provenance/runtime gate |

RouteB removes the proprietary C ABI/type/helper dependency compared withA;
this is an engineering inference, not verified code generation. It replaces
those dependencies with explicit lowering and target inspection obligations.
No route is operationally verified. The smallest next evidence-driven step is
lawful acquisition/identity verification of a version-matched MAC66K v4 package
and applicable M66201 DCL, followed by separately authorized isolated runtime
verification. A later invented-only15-form listing experiment is not performed here.

## C type/ABI unknowns and firmware gates

`CompilerAbiNotEstablished`, `TargetCCompilerNotEstablished` (also
`NativeCCompilerNotEstablished`) and `TargetCTypeLayoutNotEstablished` remain.
CHAR_BIT; char/short/int/long sizes; pointer widths/address spaces; struct/union
alignment/packing; bool; integer promotions; uint8_t/uint16_t availability;
arguments/returns; caller/callee-save; frames/alignment; symbol names; runtime
helpers and memory/linker model are explicit unknowns, never default0.
Host sizeof/state pointer casts cannot answer these questions. This is not a
global assertion that a200 C compiler never existed.

Source-level equivalence is complete only in M2av's bounded domain. Target
context research is the next layer. Operational assembler/compiler verification,
generated instruction/flag/RAM equivalence, safe placement/linking, whole-ROM
integration, checksum/identity/flash restrictions and physical bench validation
remain subsequent gates; none follows automatically from the first two.
Current host C11 source cannot be asserted directly executable in the ECU.

## Machine-readable contract and regressions

The separate metadata layer is
[target_abi_contract.json](../research/p28-word0196/target_abi_contract.json),
with independent
[validator](../research/p28-word0196/validate_target_contract.py) and
[invented-only tests](../research/p28-word0196/target_contract_tests.py).
Existing IR/C/header/oracle/host pipeline remain byte-for-byte unchanged.
The closed schema distinguishes confirmed facts, historical observations,
cross-family/derived leads and unresolved fields; it fails closed on invented
permissions, ABI promotion, unsafe context/ownership and reordered effects.

Run with existing Python3 (no target tool involved):

```text
python -B research/p28-word0196/validate_target_contract.py
python -B research/p28-word0196/target_contract_tests.py
```

Both Ubuntu/Windows CI receive only this additive static/invented test step.
The original M2av host C11/equivalence step and all existing QA jobs are retained.
Local QA also repeats unchanged C/C# invented and historical replays; historical
replay is not a new ROM run.42 completed observations/552 snapshots/170 writes
remain separate from invented vectors; the13-step path still lacks a historical
native witness. Protected material, all18 stabilization sources and ten original
runner binaries are independently compared. Private receipts contain actual
counts, exact source bindings and final exact-SHA CI; no old report overwritten.

## Classification and retained boundaries

Confirmed within explicit scope: `TargetArchitectureVerifiedWithinScope`,
`NativeContextMapped`, `DataMemoryLayoutVerifiedWithinScope`,
`NativeExitContinuationIdentified`, `AssemblerTargetSupportDocumented`,
`SourceLevelEquivalencePreserved`. Entry remains `NativeEntryContractConditional`.
`AssemblerRuntimeNotVerified`, `TargetCodeGenerationNotRun`,
`CompilerAbiNotEstablished`, `TargetCCompilerNotEstablished`,
`FirmwareIntegrationNotEstablished`, `TargetMachineCodeEquivalenceNotEstablished`.
No FirmwareReady claim.

M2au accounting/M2at HC/M2an SLLB fixes retained. M2as WDT3C, M2ar reset, M2ap
SSP/ADC, M2ak source-to5722 and M2al/M2am C8 remain blocked/unresolved; M2aq
CAL2689/RT5C80NotRun; M2ao DATA019B frontier/M2ah STOPbefore5722 and missing
DATA019B.2 owner unchanged. M2t JGT233ABlocked, M2ag/M2af unchanged, strictM2iBlocked.
IRQNotInjected; TimerEvolutionNotModeled; RecoveredEcuSchedulerNotEstablished;
ElapsedTimeNone; PcInspectionOnly/NotFlashReady; physicalRpmAvailable=false;
physical fuel/time/degrees unavailable. GUIr3 paused/NotRun; D1/D2interactive,
hardware/fullbootNotRun. C8/WDT inquiriesNotSent. Actual-ROM0; FirmwareBIN0.
STOP after M2aw delivery: no M2ax, target assembly, linking/image, ROM replacement,
WDT/C8/reset/IRQ/fullboot, GUI or hardware continuation.
