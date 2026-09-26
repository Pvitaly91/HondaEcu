# M2m — native DATA0158 fuel-factor production and consumption

Read-only software research on the privately bound unchanged P28-304 original.
Operation `fuelFactorProductionChain`, runner **0.21.0**, pinned Rust **1.85.1**.
The new scenario has no supplied `factor0158`; it cannot reuse M2l's legacy
factor setter. Historical M2k/M2l standalone inputs and stop boundaries remain
compatible. Strict M2i remains **Blocked on47 81**;45 81 and disputed SUBB forms
are not admitted by analogy. Public fixtures contain invented programs/data,
not OEM routines, ROM identities, maps or native traces.

## Recovered producer and explicit schedule

Backward data/control slicing from the word store7A99 establishes **entry1F43,
stop-before1FB7**. The former leads1F8E/1FB2 are not valid closed entries:
they consume er0 formed by earlier selection, byte multipliers, narrowing and
saturation.1F43 replaces inherited A and constructs er0 from a selected source;
no ready accumulator, register pair or carry is supplied by the host.

The supported test schedule is fixed for every event:

```text
closed raw/source snapshots
  → native fuel axes/selection/lookup → word0140 at134E, stop1350
  → scripted same-machine entry1F43
  → continuous native factor producer, actual detour/store/return → stop1FB7
  → scripted same-machine entry2194
  → continuous M2l correction → M2k scaling → XCHG/VCAL4/helper/RT
  → software stores03A2/03B4, stop-before2204
```

The two scripted seams are1350→1F43 and1FB7→2194, not recovered main-loop
continuation. Native12FC..1350, producer1F43..1FB7 and2194..2204 are individually
continuous. No enter/reset occurs at internal21DB or21F2; no old standalone task
is launched on a second CPU/RAM. One machine persists per image/sequence/scratch
00/55/AA, with one initialization. Each in-memory B starts independently from
the original; divergent histories are never repaired or aligned by host.

Both scripted transitions write exactly LRB0020, PSW0101 and USP0280. The
canonical PSW is0DC9. They preserve A, register-bank bytes, X1/X2/DP, SSP and RAM.
These ABI choices are recovered separately for the producer and the additive
caller, not inferred from their reuse of bank20.

At1FB4, the executed absolute `J` enters7A99. The actual word
`MOV off0158,er1` replaces both bytes0158/0159. Post-store7A9C..7AA5 performs a
byte hysteresis update, then actual `J` at7AA8 returns to1FB7. This is a jump
detour, **not CAL/RT**; it does not push a stack frame. Stopping at7A99 would miss
the store and side effect; stopping immediately after the store would omit the
closed detour return. There is no hold/bypass path in this supported producer.

## Unified ownership and source widths

All names denote raw software storage, not temperature, pressure, battery,
injector constants, fuel percentages or physical units. Upstream writers below
are static leads outside the closed1F43 scope; their sensor acquisition, earlier
gates and own arithmetic are **NotRun**. Storage-width test domains do not prove
that every combination is produced by the excluded upstream ECU program.

| Footprint / mask | Static upstream writer → native reader | M2m policy |
| --- | --- | --- |
|0140..0141 word |134E →21DB | Native lookup-owned; initial diagnostic zero, no scenario override |
|0158..0159 word |7A99 →21DD | Native factor-owned; code-owned diagnostic initial scratch word, never an input |
|015A..015B word |1E52 →1FB0 | Per-event raw-u16 snapshot |
|015C..015D word |168A →1FAA | Per-event raw-u16 snapshot; read only when012C.4 is set |
|015E byte;015F high byte |4945 byte writer →1F8E **word** read | Raw-byte015E; upper015F code-owned zero once, no claimed recovered high-byte producer |
|0160..0161 word |1EF7 →1F78 | Per-event raw-u16 snapshot |
|0162..0163 word |498C →1F72 | Per-event raw-u16 snapshot |
|0164 byte |14DE/1892 →1F43 | Per-event raw-byte snapshot, chosen if012F.7 is set |
|0165 byte |14E6/1ED6 →1F48 | Per-event raw-byte snapshot, chosen if012F.7 is clear |
|0166 byte |1ADD →1F4F | Per-event raw-byte snapshot; zero skips this multiplier |
|0167 byte |14BA; zero14C2 →1F5A | Per-event raw-byte snapshot; zero skips this multiplier |
|0168 byte |1F41/7BFC →1F69 | Per-event raw-byte snapshot; predecessor writer excluded explicitly |
|0133 byte |0820/40D2 →7AA3 | Per-event raw-byte snapshot for the post-store comparison |
|012C byte, bit4 |15A2/1682 →1F94 | Once-only producer mode; unchanged in the producer |
|012F byte, bit7 |181C/188C →1F45 | Once-only producer selection; not a fuel-map ID |
|0130 byte, bit6 |native7AA5 →7A9E on the next event | Once-only initial byte, then native history; neighbouring bits retained |
|0127 byte, bit1 |once-only caller → native fuel selection | Once initial map context; not per-event/VTEC injection |
|Axis caches/fractions;013F |reused M2k native prefix | Once-only caller state, then native cache history;60E5=0 unchanged |
|0238/00C2/00BF bytes |closed raw inputs → fuel axes | Per-event byte snapshots before all native stages |
|0142..0143 word |14C8; zero142D →2194 | Per-event raw-u16 correction source |
|0144 low byte;0145 high byte |4A53 byte writer →21A5 word read | Input0..255; upper0145 code-owned zero, previous scope restriction retained |
|0146..0147 word |200A →21B8 | Per-event raw-u16 snapshot, interpreted signed by helper |
|0148 byte;0149 byte |208A/49B1 →21B5/21BE | Per-event bytes, native signed EXTND |
|014A..014B;014C..014D words |20F0/2172 →21A9/21AD | Per-event raw-u16 correction snapshots |
|00F2 byte |3E12/415C →2199 | Per-event raw-byte counter snapshot |
|012B byte, bit3 |static160E; native219D →2196 | Once-only initial byte, then native additive history |
|0124 byte, bits4/5 |static1A28/1A23 → caller precondition/21F5 | Once-only gate; bit4 clear, bit5 can clear03A2 only |
|er0/er1 at0100/0102 |factor arithmetic, later M2k | Native word aliases; no ready carriers or between-stage restoration |
|er2/er3 at0104/0106 |M2k component / M2l correction/application | Native-owned; er2 remains distinct from corrected A/er3 |
|X1/X2/DP at0088/008A/008C |prefix/native tail | Retained across scripted seams; correction writes X2 natively |
|SSP;07FE..07FF |M2l CAL/VCAL4/RT | Producer jump detour preserves SSP; established near-call stack remains balanced |

Byte/word overlaps are explicit: source015E cannot also supply015F, source0144
cannot supply an arbitrary0145, and no two fields assign different values to one
shared byte. Code-owned initial0158 is `(scratchPattern & 255) * 257`; it is a
diagnostic stale-word canary, **not recovered boot initialization or a produced
calibration**. Source setters and both scripted seams are logged with closed
address/width/value footprints, including refusal of either-byte0158 overwrite.
Producer side effect0130.6 is modeled, not restored by the host. The producer
does not write0140,0127,0124 or012B; it is compatible with the direct M2l caller.

## Ordered integer production, not a floating-point factor

Let `s` denote the selected raw byte0164/0165. All following operations are
unsigned integer stages, with their native truncation order retained:

```text
q = s << 7
if 0166 != 0: q = (q * 0166) >> 8
if 0167 != 0: q = (q * 0167) >> 8
q = (q * (256 + 0168)) >> 8
q = (q * 0162) >> 16
intermediateProduct = q * 0160
q = min(intermediateProduct >> 10, 65535)
intermediateProduct = q * word015E   // 015F is code-owned zero
if 012C.4 == 0:
    q = intermediateProduct >> 16
else:
    q = min((intermediateProduct << 3) >> 16, 65535)
    q = (q * 015C) >> 16
nativeFactor0158 = (q * 015A) >> 16
```

The first source is placed in r1 with r0 cleared, then SRL er0 forms `s<<7`.
The optional byte multipliers use ACCH and native MUL high/low result words;
MOVB r1,r2 and MOVB r0,ACCH establish the next narrowed operand. Multiplication
by0160 is shifted as an actual high-word SRL/low-word ROR pair twice; the native
high-byte test clamps a nonzero upper result toFFFF. Equality65535 remains an
ordinary non-clamped value. Mode-on scaling is three actual SLL A/ROL er0 pairs
with carry branches, then an optional015C multiplication; it is not the M2k
`>>9` formula transferred by analogy. The final MUL forms high word er1, and7A99
stores **that** word, not er0 or a host-calculated result.

After the store, threshold is102 if incoming0130.6 was set, otherwise106.
Native7AA3/7AA5 sets0130.6 exactly when raw0133 is greater than that threshold.
Equality clears the bit; other bits survive. This history affects the next
comparison but does not change0158 on this closed producer path. Every completed
path writes0158, even when the new word equals the prior word: same value is
**Written**, not Held. A producer never attempted after prefix failure is NotRun,
not a completed hold branch.
Post-store LB leaves AL equal to102/106 while retaining AH from the final
multiply's low word: full A is neither the factor nor merely the byte threshold.

## Two independently checked data generations and unchanged downstream

| Generation | Actual writer → reader | Required evidence |
| --- | --- | --- |
|Current-event lookup0140 |word134E/0140 →word21DB/0140 | Independent lookup value, order, width, PC and no overlapping intervening write, including producer accesses |
|Current-event factor0158 |word7A99/0158 →word21DD/0158 | Independent source arithmetic, both bytes replaced, current producer generation and no native/host overwrite |

The two inputs are validated separately: swapped/stale operands can give the
same final product and must still fail. Native factor is not fed into C# as its
expected operand. C# owns ROM/cache/source/mode/hysteresis history and produces
its own expected0158, then passes that independent projection to the pure
downstream analysis helper, not back into the executing machine.

M2k/M2l stages remain separate and unchanged:

```text
component = min((uint32(DATA0140) * uint32(DATA0158)) >> 9, 65535)
correction = independently modeled native M2l staged signed correction
corrected = clamp(component + correction, 0, 65535)
```

Native2194..21DB retains conditional100/current incoming012B.3 and its native
counter<4 update, signed-byte additions with sequential signed saturation, and
the final correction upper bound32767. X2 and er3 hold the same correction word.
At21F2 XCHG separates correction from component; VCAL4 reads actual vector0030
to5958, uses the established near stack, and returns natively.0124.5 can clear
03A2 while corrected03B4 and er2 remain distinct. Stop-before2204 is unchanged.
Negative correction after a saturated component keeps historical M2l semantics,
even where such saturation is unreachable in this narrower M2m original domain.

## Reachable domain, masking and evidence status

The source-domain projection is **not arbitrary raw-u16 factor freedom**.
With fixed maximum upstream snapshots, a finite model audit enumerates every
raw015A in both modes: **131072 scalar producer cases**, output domains0..253
(mode off) and0..2037 (mode on), no holes; plus512 model-only hysteresis cases.
Native count for this audit is **zero**. These are declared software-input
domains, not proof of physical acquisition or excluded upstream reachability.

Since word015E is limited to255 and the earlier narrowed result to65535,
its product is at most16711425; after three left shifts the high word is at
most2039. The mode-on x8 overflow/clamp branch is therefore **NotReachable** in
this caller scope, despite being decoded and covered by invented regressions.
The earlier0160 saturation is reachable and remains a distinct producer stage.
No hold path exists in the closed producer; Held cannot be inferred from an
unchanged value or an initial diagnostic word.

Legal model-derived witnesses with all other producer snapshots at maximum and
mode on include raw015A16464→factor511,16465/16466→512,16497→513,
65503→2036 and65504..65535→2037. Raw015A0..32 produces0. Plateaus are native
integer truncation candidates, not reasons to force a ready factor into RAM.
Their actual native execution is counted only in the separate local reports.

The unchanged-original own-ROM raw lookup audit has reachable maximum0140=2501,
giving reachable component at most9950 and corrected output at most42717.
Separately, convex Q16 interpolation gives a conservative original bound2510
from the largest scaled cell, hence component≤9986 and corrected≤42753. The
native axes overwrite incoming fractions each event; arbitrary initial fraction
canaries do not extend this domain. Even **any allowed one-cell B** keeps original
metadata maximum10: scaled cells≤2550, component≤10145 and corrected≤42912.
Thus M2k saturation and application upper clamp are NotReachable for both the
unchanged original and legal in-memory B; standalone M2l could reach them using
arbitrary factor snapshots. A/B producer controls and observed effects are still
checked independently; these bounds do not grant ROM editing/export authority.
Lower application clamp, zero factor, producer truncation,
lookup masking, scaling truncation and the03A2-only gate remain distinct.

Local actual coverage: **3228 StrictMatch native events**, all with fresh
native factor writes;2568 original A events and660 independently executed B
events, across24 scenarios/96 persistent sequences. Both once-only map contexts,
both producer modes/selectors, cache/repeated-input history, source sweeps,
post-store hysteresis, producer limits, lower application clamp and03A2-only
gate are exercised. **660 A/B comparisons** include96 unmasked03B4 witnesses;
producer controls remain separate from changed lookup/component/store outputs.
No old3678 M2l events or compatibility repeats are added to this total.

Model-only audits remain separate:131072 scalar cases establish the domains;
the separate141072-case C# model/path parity audit includes that scalar sweep
and additional representative source combinations. The512 hysteresis property
checks are separate; overlapping/repeated audits are not summed as native work.
All have nativeEvents=0. Public partial/terminal fixtures do not increase the
actual original coverage or turn a synthetic pass into ROM production evidence.

Local final QA passes pinned Rust Release build/**184 tests**/fmt and both .NET
Release solutions:Core910, CLI502, Desktop183 (**1595 .NET tests**), with both
formatting checks and `git diff --check`. Desktop tests are headless contracts,
not GUI smoke or normal WPF startup. Exact-final-commit remote SHA/CI is verified
separately at delivery, not inferred from local QA or a previous green run.

## Exact-form evidence, partial execution and CLI

Mandatory forms were inventoried before implementing the surrounding chain.
All64 static listing instruction boundaries in the two producer code ranges
matched actual original bytes; this byte audit is **not64 native events**.
Primary OKI evidence establishes exact word ROL er0 (`44 B7`, printed3-118)
and word SLL A (`53`, printed3-142): through-carry rotation / left shift affect
**CF only**, preserving ZF/HC and other flags. Failing decoded regressions
preceded the minimal executor fixes. Runner0.21 discloses
`word-rol-er0-through-carry-preserves-noncarry-flags` and
`word-sll-accumulator-preserves-noncarry-flags`; inherited M2l fixes remain.
Actual opcode, DD, addressing and word aliases matter. Matching Rust/C# values,
executable hashes and decoder names alone are not independent ISA proof.

| Mandatory exact form group | Primary printed pages / relevant semantics |
| --- | --- |
|LB A,off/r3/immediate; L A,off |3-69/70; byte/word widths, ZF/DD |
|STB A,r1; STB A,ACCH |3-155; DD0 byte stores, flags unchanged |
|CLRB r0; CLRB A |3-34 /3-33; register form preserves flags/DD, accumulator form sets ZF/DD0 and retains AH |
|SRL er0/er1 |3-151; word/DD-independent, CF only |
|MOV er0,er1; MOV er0,immediate |3-83 /3-86; word/DD-independent, flags unchanged |
|MOVB r1,r2; MOVB r0,ACCH |3-99; exact byte aliases/DD-independent, flags unchanged |
|MOVB ACCH,immediate |3-96; direct address field0007, flags unchanged |
|MUL9035 |3-100; unsigned word/DD-independent, er1 high/A low, product ZF, CF/HC preserved |
|ROR A; SLL A; ROL er0 |3-121 /3-142 /3-118; word accumulator / word register variants, CF only |
|JBR off bit4; JBS off bits7/6; JEQ/JLT/JGE |3-64 /3-65 /3-66; byte bit reads and exact ZF/CF predicates |
|J addr16 |3-62; native absolute destination, flags unchanged |
|MOV off0158,er1 |3-87; exact word writer, DD-independent, flags unchanged |
|CMPB A,off0133; MB off0130.6,C |3-39 /3-78; CF/ZF compare preserves HC; byte RMW retains neighbours |

The producer's exact admission includes native LB/STB/CLRB byte carriers,
DD-independent word SRL/MOV/MUL, word L/ROR/SLL/ROL, concrete bit/conditional
branches, absolute J, word MOV off0158,er1 and post-store byte CMPB/MB. ACCH
direct-byte forms are narrowly admitted at address0007, not arbitrary RAM
scripts. Existing prefix and M2l form inventories remain applicable;47 81,
45 81 and disputed SUBB permissions remain unchanged.

A mandatory unresolved form stops before execution. Completed prefix, native
partial stores/accesses and actual before/after RAM are retained. Downstream
computed outputs are null/NotRun; later events apply no inputs or scripted
transitions. A partial store before a later fault is not reclassified as a
completed Written producer or a lawful Held branch. Producer budget128, existing
M2l budgets96/32/48,1..64 dense events and≤8 trace indexes remain bounded.

```text
hondaecu research p28-fuel factor-chain-check <original.bin>
  --profile p28-304 --confirm-profile
  --baseline-binding <binding.json> --runner <runner-0.21.0>
  --scenario <m2m-scenario.json> --output <new-private-report.json>
```

Closed version1 inputs allow only the established source snapshots, once-only
shared state and optional code-owned single fuel cell. Supplied factor0158,
0140, correction/scaled/final results, per-event map IDs, PC/RAM scripts,
formulas and arbitrary offsets are rejected. The CLI preserves exact binding,
bounded parsing, input snapshots/rechecks, new destination/alias protection,
and existing already-cancelled/timeout/active-child cancellation transport.
Console shows actual map/0140, actual source snapshots,0158 before/after and
provenance, separate prefix/producer/tail stops, component/correction/stores.

An optional B is a one-cell in-memory child of the original, never a chained
patch. Both images execute the producer independently; factor controls are
established by actual footprint/evidence, not different addresses alone.
Source-input experiments change an allowed upstream snapshot with an unchanged
map, not a ROM edit or physical-sensor experiment. Compatibility may supply
an independently produced factor to a separate old M2l control; it does not
feed that value back into M2m or prove production independently.

## Remaining exclusions

Original60E5/60F8 and all code/configuration bytes remain unchanged. Optional
helper5A55 and later227A/per-channel paths are not enabled. Other correction
producers, VTEC/ignition/shared-M2h integration, complete controller/main loop,
timer/IRQ/scheduler, full boot, engine model and physical pulse width/AFR are
outside scope. No editable calibration, alternate-map/axis/multiplier editing,
exporter, checksum bypass, signing key/location, firmware BIN, new binding,
export plan/receipt/token, GUI or hardware action is introduced.

**PcInspectionOnly / NotFlashReady**; `physicalRpmAvailable=false`; physical
fuel/time units/degrees unavailable; strict M2i Blocked; GUI r3 paused/NotRun;
D1/D2 interactive acceptance, hardware and full boot NotRun. Previous private
ROM/reports/bindings/receipts/definitions/scans/portable files are preserved.
