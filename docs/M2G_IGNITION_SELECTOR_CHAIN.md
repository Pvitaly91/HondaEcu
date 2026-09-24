# M2g — native ignition selector to primary lookup and DATA0248

This is a revision-bound, read-only PC research chain. It does not identify a
physical cam/VTEC state, physical RPM/MAP, degrees, delivered spark instant,
the ECU main loop, a shared fuel/ignition scheduler, full boot or flash safety.
The separate M2f VTEC/fuel task is **not** executed by this operation.

## Recovered selector producer

The matching listing and exact bound original establish the smallest
semantically closed selector subfragment at `5F93`, stopping **before** `5FAF`.
The entry is an explicit scripted call into the larger `5F45` configuration
routine, not a recovered ECU scheduler. It uses byte mode, SCB1, `LRB=0041`
(bank `0208..020F`, off-page `0200`), `USP=0180`, and `SSP=07FE`. `5F93` loads `DP=03C7`;
`5F96` reads that RAM byte; `5F97` saves it in banked `r1`; `5F98 RC`
clears live carry. `5F99` reads the program byte at `60FB`, and the jump
through `7DF4..7DF7` enters `5FA0` when that byte is zero. `5FA0` reads
`ROM60EA`; with zero, `5FA4 JEQ` skips `5FA6..5FAB` and `5FAC` writes
the live carry to `DATA0227.5`. Both original program bytes are zero.
Thus this exact scoped execution writes **zero**, even when the initial
selector bit was one. Other bits of `DATA0227` are preserved. `ROM60EA`
is an immutable configuration branch, not a named physical sensor.

For a different *static* configuration, nonzero `60FB` takes `7DFA` and
shifts `7E02` into carry; nonzero `60EA` enters the `r1` shifts. Neither
alternate configuration is a dynamic original-ROM witness, and this task
does not patch those bytes. `03C7` is read on the original path but its
value is masked by the zero configuration and the preceding `RC`. The
upstream indexed writer is `5CB4 STB A,03C6[X1]`, which can target
`03C7` when `X1=1`; `5CA5..5CAC` derive that index from P2 and `5CB2`
reads `ADCR0H`. That acquisition/IRQ path is identified statically but
not executed in M2g. Scenario `source03c7` is an explicit software/raw
snapshot, **not** a modeled physical input.

## Ownership and caller schedule

| Field | Producer | Reader | M2g harness policy |
| --- | --- | --- | --- |
| `03C7` | indexed `5CB4` upstream, not run | native `5F96` | only admitted per-event source snapshot |
| `0227` whole byte / bit 5 | once seed / native `5FAC` | `0A32`, `0B71` | no event map ID or selector write; neighbors preserved |
| `0238`, `00C2`, `00BF` | external software caller | native axes | bounded raw event inputs |
| `01C6/01C2`, `01C7/01C4`, `01BB/01BE` | native axes | native selection/lookup | seed once; persist without reseeding |
| `0247`, `0248` | once factor seed / native consumer | `0BB6`, later correction | factor never changes per event; output retained after a failed stage |
| `00B8`, `0212`, `021D`, `0214`, `0218`, `021F`, `0219` | unscheduled caller | axes/selection | fixed-clear direct-path gates; checked after producer, never repaired |
| PC/PSW/LRB/USP and banked registers | script at separate stage entry, then native | stages | boundary snapshots show entry actions; no reset in `0B64..0BD4` |

One CPU/RAM exists per image/scratch sequence. The harness seeds the full
`0227`, axis caches/fractions and `0247/0248` once. For each event it applies
only `03C7`, `0238`, `00C2`, `00BF`; executes `5F93..5FAF`; enters native
axes `0A0C..0A62` as a disclosed caller action; enters primary selection
`0B64`; and continues without CPU/RAM/stack reset through lookup and the
consumer, stopping before `0BD4`. The transitions into `5F93`, `0A0C`
and `0B64` do not assert contiguous firmware control flow. Stage journals
and full bank/pointing/stack boundary snapshots make that distinction visible.

The primary caller requires clear `00B8.3/.4`, `0212.2/.4`, `021D.4`,
`0214.5`, `0218.5`, `021F.1`, `0219.6`. `0218.5` is bypassed with
`0214.5` clear but fixed anyway. The native second RPM-axis fragment
shadows `00C2` with `0238` only if selector bit 5 is set. Under this
unchanged original producer, that context is unreachable: both initial
selector states are tested but both proceed with bit 5 clear. M2c's
host-selected map-1 lookup remains a separate isolated contract and must
not be counted as M2g dynamic reachability.

## Numeric and evidence policy

The independent C# model owns ROM bytes and persistent selector/cache/
consumer history. It never receives a Rust-selected map as its next expected
input. Shared M2c numeric helpers retain sentinel-zero endpoint 256,
unsigned Q16 fractions, separately truncated top and bottom columns and
then row interpolation. Ignition reads four unsigned cells at unity scale,
not fuel column multipliers. `0247=0` stores lookup; nonzero stores the high
byte of `lookup×factor` in `0248`. Raw cell, lookup and consumer output are
distinct quantities. Strict matching checks producer branch/read/store,
selector history, axis reads/caches, native pointer, four cells,
intermediates, consumer branch/product/store, ordered journals, exits and
stack. Unresolved/error/budget results leave downstream and later events
NotRun; retained `0248` is not an executed lookup result. M2f's conditional
SUBB permission is unavailable here.

Optional A/B changes exactly one code-owned primary-map cell in memory from
the same bound original. Producer and selector must remain controlled;
cell read, lookup effect and factor/weight masking are separate observations.
There is no child binding, compensation, checksum bypass, firmware BIN,
export plan, receipt or publication capability.

```text
hondaecu research p28-ignition selector-chain-check <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --runner <runner-0.15.0> --scenario <m2g-scenario.json>
  --output <new-private-report.json>
```

The closed scenario has version/provenance, once-only initial state, 1..64
dense raw events, at most eight trace indexes and optional one-cell mutation.
The old `ignitionMapLookup` schema retains its M2c meaning. The new runner
operation is `ignitionSelectorChain` in version `0.15.0`; historical task
inventories and receipts are not retroactively changed. Results remain
`physicalRpmAvailable=false`, raw units, `PcInspectionOnly / NotFlashReady`;
GUI r3 and D1/D2 interactive acceptance are paused/NotRun, and hardware,
full boot and downstream ignition corrections remain NotRun.
