# M2h — one shared axis pass for VTEC, fuel and ignition software paths

M2h composes the previously separate M2f and M2g read-only research paths on
**one CPU/RAM lifetime per image/scratch sequence**. The exact bound original
completed a native selector producer, one continuous axis pass and both
software lookup/consumer tails. This is a bounded, explicitly scripted test
schedule, **not** a recovered main loop, IRQ cadence or engine cycle. The
earlier M2f/M2g contracts and M2e/D2 strict-only publication gates are not
expanded. No firmware BIN, export ability or GUI behavior is added.

## State ownership and admission

The table distinguishes initialization from a subsequent event. A word lists
its full byte footprint; no two initializers are chained. In particular, the
old M2f seed that cleared `0227` is not invoked after the M2h seed.

| Address / width | Native writer → reader / lifetime | Harness input |
| --- | --- | --- |
| `01C6`, `01C7` bytes; `01C2–01C3`, `01C4–01C5` Q16 words | Single `0A0C..0A45` RPM-axis execution → both lookups; persistent across events | Once-only indices/fractions; raw `0238` and distinct `00C2` each event |
| `01BB` byte / `01BE–01BF` word | Ignition load axis → ignition lookup; persistent | Once-only cache, common raw `00BF` per event |
| `01BC` byte / `01C0–01C1` word | Fuel load axis → fuel lookup; persistent, separate from ignition load | Once-only cache, the **same** raw `00BF` per event |
| `0227` whole byte, bit 5 | Native `5FAC` carry-to-bit store → axis `0A32` and ignition `0B71`; other bits retained | Whole byte once; no event selector/map override |
| `0127` whole byte, bits 1 / 2 | Native VTEC decision and reader `131A`; bit 1 is fuel selection, bit 2 mirrors request | Whole byte once; no event selector/P1 override |
| `0131`, `0198` bytes | VTEC decision/helper → later VTEC gates | Once-only persistent values |
| `01D8`, `01D9`, `01DF`, `00F3` bytes | Native decision and native tick bodies → subsequent timer gates | Once-only state; bounded tick-body counts, not time |
| P1 output-data latch | Native decision → software request observation | Once-only output latch; no pins or physical actuation model |
| `013F` byte / `0140–0141` word | Once-only factor / native fuel consumer store | Once-only factor and retained output; never tuned per event |
| `0247`, `0248` bytes | Once-only factor / native ignition consumer store | Once-only factor and retained output; never tuned per event |
| `03C7`, `0238`, `00C2`, `00BF`, `0133`, `00CC`, `00D9`, `0119`, `011A–011B`, `011C`, `0132`, `0199`, masked `011E` | Unscheduled upstream software → producer, axes and VTEC decision | Explicit raw snapshots per event; compact VTEC code is not physically tied to axes |
| `00B8.3/.4`, `0212.2/.4`, `021D.4`, `0214.5`, `0218.5`, `021F.1`, `0219.6`, `0120.5`, `0121.6` | Direct-path caller gates → native axis/ignition/fuel readers | Fixed-clear once; later incompatible gates stop, never host-repaired |
| PC, PSW/DD, LRB, banked registers, DP/X1/X2, USP, SSP/stack | Actual stage machine; retained within each continuous fragment and event sequence | Explicit entry ABI only at disclosed scripted jumps; no boundary reseed |

The separate words `01BE–01BF`, `01C0–01C1`, `01C2–01C3` and
`01C4–01C5` do not overlap one another or the index bytes. Both lookups
reference the **same** `01C6/01C7/01C2/01C4` RPM storage, not copied models.
One independent C# combined model owns its own ROM and one axis state; it
produces positions once per event and passes those results to both pure
lookup calculations. Rust checkpoints never become expected model state.

## Scripted schedule and native boundaries

1. Apply the admitted raw software snapshots; execute the existing native
   counter bodies with their explicit `0088` target ABI.
2. Enter `5F93` in byte mode, SCB1, `LRB=0041`, `USP=0180`, `SSP=07FE`;
   stop before `5FAF`. This is the installed M2g producer, not a host
   formula. On the exact original, its actual reads of `60FB`, `60EA` and
   the zero configuration force carry clear, then `5FAC` clears only
   `0227.5`. Initial `0227.5=1` is admitted and processed **before** the
   joint consumer gate check. `0127.1` and `0227.5` are independent.
3. Script the entry to `0A0C`; run once to stop-before `0A77`, including
   native internal PCs `0A45` and `0A62` and helper `59B2..59E4`.
   Matching bytes/branch paths show these boundaries lie on the continuous
   fragment. There is no host enter/reset or prepared-cache injection there.
4. Script the entry to `0B64`; selection `0B64..0BAF`, lookup
   `0BAF..0BB4` and consumer `0BB4..0BD4` continue without a host reset.
   The exact original selects `ignition_map_0`; alternate map 1 is not
   forced. Native ignition lookup has `PSWL.5` clear (unity cells, no
   column-metadata read).
5. Script the entry to `122C`; decision `122C..12FC` continues at that
   **same** machine boundary through fuel selection `12FC..1340`, lookup
   `1340..1347` and consumer `1347..1350`. Native fuel code sets its
   lookup mode and reads actual column multipliers. Neither axes nor
   selectors are copied/recomputed between the ignition and fuel tails.

Scripted entries are disclosed ABI actions; they are not evidence of one
unbroken path from `5F93` to `1350`. The matching listing, actual original
and ordered native journals support only the named continuous fragments.
The runner records before/after states, ordered program reads and stores,
PC path, full register/stack boundaries, selected origins, lookup values,
consumer stores and local instruction status. The validator requires
byte-identical selection→lookup→consumer boundaries and the `12FC` seam;
equal final outputs cannot hide a host register reset.

## Status and exact-original observations

Only `oki.subb-a-off-n8-encoding` can be optionally permitted. Merely
supplying it does not make ignition or a nonusing event conditional. Actual
use makes that event and dependent later shared-machine history conditional.
With no permission, a VTEC stop can occur after completed ignition: its
ignition value remains an executed result, the whole event is `Unresolved`,
fuel stages/results are `NotRun`, and later events apply no inputs. A retained
RAM output is not a new consumer result. M2e/D2 exports remain strict-only.

The bounded private exact-original scenarios produced these M2h-only counts
over scratch `00/55/AA` (not recycled M2f/M2g counts):

| Scenario | Full strict | Full conditional | Partial / later NotRun | Distinct observation |
| --- | ---: | ---: | ---: | --- |
| Disabled `0227.5=1` witness | 3 | 0 | 0 / 0 | Native `A5→85`, both tails complete |
| Once-seeded nonzero ignition factor 173 retention | 12 | 0 | 0 / 0 | Lookup and `0248` differ by factor |
| Conditional transition (permission supplied) | 30 | 15 | 0 / 0 | Request differs from map selection; dependency retained |
| Same transition, strict (no permission) | 30 | 0 | 3 / 12 | Event 10 completes ignition then stops VTEC; events 11–14 NotRun in each pattern |
| Fuel-selector transition series | 0 | 24 | 0 / 0 | `0→1` and `1→0` occur; ignition stays map 0 |

The exact-original A/B comparisons each derive B independently from A with
**one in-memory, code-owned byte** and no firmware/checksum repair:

| B byte | Comparable events | Native changed-byte read/effect | Controlled path |
| --- | ---: | ---: | --- |
| One VTEC threshold | 24 | 21 | Ignition origin/lookup/`0248` unchanged |
| One `map_0` fuel cell | 45 | 15 | Producer, VTEC state and ignition unchanged |
| One `ignition_map_0` cell | 45 | 15 | Producer, VTEC state and fuel unchanged |

Unselected-cell events are `ByteNotRead`, not failed edits. Factor or Q16
weighting may legitimately yield `ReadNoEffectOrMasked`. All three A/B
series had zero control failures. Full actual-ROM evidence, hashes and
scenario details remain ignored under `private/reports/m2h/`; public CI runs
invented data only.

## Narrow CLI and remaining limits

```text
hondaecu research p28-calibration shared-chain-check <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --runner <runner-0.16.0> --scenario <m2h-scenario.json>
  --output <new-private-report.json>
  [--allow-assumption oki.subb-a-off-n8-encoding]
```

The closed version-1 scenario has provenance, one initial state, 1..64 dense
events, bounded native tick counts, at most eight trace indexes and optional
single-field threshold/fuel/primary-ignition mutation. There are no event
map IDs, selector/P1 writes, prepared axes, caller PCs or expected outputs.
The command reuses exact-binding admission, input snapshot/recheck,
new-output/alias guards and bounded child process cancellation. The runner
operation is `vtecFuelIgnitionChain` in version 0.16.0; older 0.14/0.15
operations retain their historical meanings and cannot claim M2h support.

`physicalRpmAvailable=false`; units are raw, physical degrees unavailable.
No physical RPM/MAP/AFR, VTEC→ignition causal link, downstream ignition
correction, injector/coil output, upstream acquisition/G/F, complete boot,
ECU scheduler, engine cycle, firmware export or flash readiness is established.
Every result is `PcInspectionOnly / NotFlashReady`. GUI r3 is paused/NotRun,
D1/D2 interactive acceptance is NotRun, and hardware/full boot is NotRun.
