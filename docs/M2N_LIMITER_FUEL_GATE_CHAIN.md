# M2n — native fixed-limiter decision to fuel-store gate chain

Read-only software research, operation `limiterFuelGateChain`, runner **0.22.0**,
pinned Rust **1.85.1**. One CPU/RAM per image/sequence/scratch carries a native
fixed-period decision into the established M2m numerical fuel chain. The native
writer and both gate readers are executed; the host never supplies a per-event
request, gate byte, factor, correction or output. Historical M1l/M1m and M2m
tasks retain their own scopes and admission rules.

## Exact caller scope and schedule

```text
closed raw/source snapshots
  → native1966..stop-before1A38: fixed decision and all addressed side effects
  → scripted axis/selection entries, native lookup/store0140 → stop1350
  → scripted1F43, native factor/detour/store0158/history → stop1FB7
  → scripted217A, actual JBR0124.4 →2194
  → continuous native correction/scaling/XCHG/VCAL4/helper/RT
  → actual21F5 reads0124.5 → software stores03A2/03B4 → stop-before2204
```

This is a disclosed **test schedule**, not recovered continuous ECU caller flow
or a штатний scheduler. There is no enter/reset at21DB/21F2, no second lookup,
no reload of computed correction, component or accumulator. Scripted entries
write only established LRB/PSW/USP aliases and PC; actual writer ledgers and
before/after carrier boundaries are checked. Same-bank registers, accumulator,
DP/X1/X2 and SSP are preserved across these transitions.

Fixed context is code owned: once011B.7=1, frozen read-only P4.0=0; one0121=80
initializer satisfies limiter .7=1 and fuel .6=0. P4 is a software caller
observation, not a physical-pin simulation or general SFR RAM. The first native
MOV loads the fixed resume operand1967..1968 into numeric DP; LA loads cut from
196A..196B. Incoming0124.5 selects cut versus resume. Direct-word CMP00C4,A
sets CF for rawPeriod<threshold; **equality releases** the request. Actual ROM
operands, not text examples, define boundaries. A repeated period inside the
hysteresis interval depends on prior state.

All isolated decision effects remain native:0124.2/.5/.4/.3,012B.7 and01D7.
Non-request writes01D7=20; request retains the counter.0124.3 reflects request
OR incoming012B.7. MB1A23 writes request bit5, MB1A28 clears bit4. Initialbit4=1
is therefore legal: it is observed and cleared natively before consumption,
not normalized by the host. No other incompatible gate is silently cleared.

Actual JBR217A reads byte0124.4 and branches directly to2194 with no incoming
numeric/register prerequisite, preserving carriers/flags. The producer-cleared
bit makes217D..2193 unreachable **within this joint path**; that bypass is not
forced or globally declared unreachable. Nested fuel-contract metadata describes
the inherited M2m body; the outer M2n contract replaces its historical scripted
2194 entry with this separately validated native217A gate.

## Ownership and generations

| State | One initialization / allowed input | Native producer and consumer |
| --- | --- | --- |
|0124 byte | one prior-history byte; no event override | decision writes incl1A23/.5 and1A28/.4; actual217A/.4,21F5/.5 reads |
|012B byte | one combined byte | limiter clears .7; additive reads/updates .3; next event retains combined byte |
|01D7 byte | one counter history | native decision only; no host decrement/timer |
|0130.6 | one factor-history byte | native7AA5 update; next factor consumes own prior history |
|0140 word | code-owned initial0, diagnostic | fresh lookup store134E → native read21DB |
|0158 word | diagnostic scratch, never scenario input | fresh factor store7A99 → native word read21DD |
|03A2/03B4 words | diagnostic scratch then previous native stores | native application; retained words are not new partial outputs |
|00C4 word | per-event rawPeriod snapshot | limiter only; not0238/00C2 RPM-axis bytes or fraction01C4 |
|M2m source snapshots | established width-identified raw sources and axes | native prefix/factor/additive bodies; upstream acquisition remains NotRun |

Raw source representations have no established physical relationship. Scenarios
are software stimuli, not physically consistent engine modes. Raw0/FFFF are
storage endpoints/sentinels, not working RPM. Source015E upper015F is code-owned
zero once; source0144 retains the established low-byte domain restriction.

The C# decision-only model reads its own ROM and own persistent prior state.
Its modeled012B byte is handed to the independent fuel models and their own
additive result returns to that same modeled byte. No observed Rust state is an
expected input. A/B histories are independently initialized and never realigned.
The Rust decision body executes on existing CPU/RAM without seeds/reset; the
old wrapper still runs its separate mask consumer. New C# `StepDecision` never
simulates018F/012A changes that native M2n did not execute.

## Gate result versus numerical result

Native21F5 JBR reads the current produced0124.5. Set reaches CLR21F8 before the
03A2 store; er3's corrected value is separately reloaded and stored03B4. The
report separates raw comparison, software request, selected threshold, corrected
numeric value, gate-taken and both stores. Zero03A2 alone proves nothing about
gate: factor0/lower numeric clamp can produce zero with gate clear. This is not
physical deactivation of every injector, electrical polarity or pulse delivery.
0124.5 is not claimed globally exclusive to overspeed or all fuel-cut causes.

Final local actual coverage: **1548 StrictMatch events**, each with fresh
lookup/factor/bit generations and both actual gate readers; **264 A/B
comparisons**, **84 threshold/request/gate03A2 witnesses**, **24 fuel-cell03B4
witnesses** (12 gate-clear both-store effects,12 gate-set masked03A2 effects).
792 events show gate-zero with positive corrected value;42 show numeric zero
without gate. Both once-only map contexts, prior bit5 states, initialbit4 set,
equality/boundary neighbours, repeated hysteresis/cut-release histories, source
and0130.6 history changes are included. Separate model-only raw-domain audit:
131072 projections, **zero native events**. Separate historical compatibility:
12 M1l decision and12 M2m numerical controls,144 matched fields, no feedback;
those counts and exploratory/repeated runs are excluded from new actual coverage.

Cut-only/resume-only children independently start from exact original. Only
their existing two-byte operand window may differ; opcode1969 is protected and
actual changed bytes may number1 or2. Fuel-cell B changes one existing cell.
Threshold A/B holds lookup/factor/correction/component/corrected03B4 and source,
cache,012B/0130 history controls; fuel-cell A/B holds native limiter/gate and
factor/correction controls. First divergence and subsequent histories are
reported. No compensation, child binding, firmware save/export plan/receipt/token.
Checksum B is diagnostic arithmetic only. Old public guards do not admit extra
diffs; combined-image authority is narrow, internal and one-field-only.

## Closed CLI / evidence / strict stops

```text
hondaecu research p28-fuel limiter-chain-check <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --runner <runner-0.22.0> --scenario <m2n-scenario.json>
  --output <new-private-report.json>
```

Scenario version1/purpose `limiter-fuel-gate-native-software-test`, bounded
provenance, one authoritative initialState,1..64 dense events,≤8 selected trace
witness indexes. Per-PC journals needed for validation remain available for
every attempted event. InitialState owns fuel caches,0124/012B/01D7 and once-only
producer context/history. Calls contain rawPeriod,rawLoad,rawMap0Rpm,rawMap1Rpm
and the established M2m source fields only. No per-event map ID,context switching,
caller-gate/bit override,factor0158,0140,correction/output,channel mask,PC/RAM
scripting or formulas. Optional mutation is the closed enum fixed-cut,
fixed-resume or fuel-cell; Pascal-case enum input is also accepted. All mutation
fields kind/value/mapId/row/column are present; fixed edits require null cell
coordinates. Enum numeric values/arbitrary offsets/multiple edits are refused.

Report validates exact operation/current identity, contracts, immediate extents,
per-PC comparison/flags/read-write order, side effects, same-machine seams and
ordered current-generation readers. Strict Unresolved/error/budget preserves
completed prefix, marks suffix null/NotRun and applies no later event inputs.
A completed decision may expose request even if fuel later fails; whole event
is not Pass. Retained stores cannot be presented as new results. Public fixtures
are invented, including a real Rust subprocess compare→bit write→gate read→two
stores probe; malformed/schema/forgery/partial/generation/bank/transition and
cancellation/timeout regressions reuse the existing bounded process adapter.

No new CPU semantic fix or disputed permission is added. Primary OKI ISA width,
DD, flags and exact forms were visually checked; inherited limiter/fuel contracts
remain authoritative for their earlier scopes. Strict M2i **Blocked on47 81**;
45 81/disputed SUBB not admitted. Runner0.21.0 lacks the new operation and is
refused, while historical operation identities remain compatible.

PcInspectionOnly / NotFlashReady; physicalRpmAvailable=false, physical fuel/time/
degrees unavailable. Adaptive487B..48F5/native ticks/RAM threshold inputs,
mask5585/P2,timers/IRQ/electrical injector control,full scheduler/boot/engine,
upstream acquisition,VTEC/ignition/shared-M2h integration remain NotRun. No new
editable calibration/exporter/axis/multiplier/alternate-map editing or signing/
checksum bypass. GUI r3 paused/NotRun;D1/D2 interactive acceptance NotRun;
hardware/full boot NotRun. No Computer Use, keyboard/mouse, normal WPF startup,
GUI smoke or ECU/programmer write. New firmware BIN **0**. Stop after delivery;
no automatic next stage or GUI test.
