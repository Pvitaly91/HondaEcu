# M2i — native ignition correction/clamp software handoff

M2i extends the **ignition-only** M2g test schedule on one CPU/RAM per image
and scratch pattern. It runs native selector `5F93→5FAF`, scripted ignition axes
`0A0C→0A62`, then the continuous `0B64→0BD4` selection/lookup/consumer tail.
The consumer itself writes `DATA0248` at `0BD2`. A disclosed **scripted caller
entry**, not a claimed ROM fallthrough, enters `0F85`; native execution then
continues to stop-before `1076`. The former static lead at `0FF4` is a byte
read of `DATA0248`, not a valid stand-alone entry. `0F85` first clears A and
stores zero into banked `er3`, and `0FE9..0FF3` prepares correction operands.

This is read-only raw software research on the exact bound original. It is not
a complete ignition controller, scheduler, dwell calculation, delivered spark
angle, crank reference, timer/coil/IRQ execution, or firmware publication.
M2h remains a separate completed task; M2i is **not** silently composed into
its VTEC/fuel schedule. M2g/M2c, M2e and D2 contracts are unchanged.

## Actual-byte and caller boundary

The matching private listing's 119 instruction encodings in `0F85..1076`
were compared with the exact original, with zero byte mismatches. The direct
path uses the once-only `DATA0212.5=1` software caller gate. This bypasses the
larger unexecuted correction predecessor `0F8A..0FE8` and a later alternate
branch reaching P4/`024B`; no ROM configuration byte is changed. M2g's direct
primary-map gates `0212.2/.4`, `021D.4`, `0214.5`, `0218.5`, `021F.1`,
`0219.6`, and `00B8.3/.4` remain clear. `0212.5` does not overlap them and
is never toggled between the prefix and correction. Its normal producer is
outside this schedule; it is an explicit once-only caller precondition.

The prefix→correction handoff records the actual `0BD2` write, the full
`0BD4` and `0F85` CPU boundaries (PSW/DD, LRB, register bank, pointing
registers, USP and SSP), and the actual `0FF4` read on the same machine.
No host write of `0248` occurs between them. The correction path has ordered
instruction events and RAM write journals. On strict refusal at `0FEC`, the
completed prefix `0248` remains visible, while corrected fields are null and
later events are `NotRun` without input application.

| Field / footprint | Writer and reader in this schedule | Ownership |
| --- | --- | --- |
| `03C7`, `0238`, `00C2`, `00BF` bytes | Raw software snapshots before producer; producer/axes/selection read them | Per-event inputs, not physical measurements |
| `0227.5`, axis caches/fractions `01BB`, `01BE–BF`, `01C2–C7` | Native producer and axes; selection/lookup read | Once initialized, then native-owned |
| `0247` byte | Earlier nonexecuted producer; M2g consumer reads | Once-only factor (`0` bypass, nonzero high-byte scaling) |
| `0248` byte | Native `0BD2` write; native `0FF4` read | Once initialized only for retained-state accounting; never per-event supplied |
| `0245`, `0246` bytes | Earlier nonexecuted writers; `0FE9`, `0FEF` read | Explicit per-event raw software snapshots before all native stages |
| `0212.5` | Earlier nonexecuted writer; `0F87`, `101B` test | Once-only direct-path caller gate, fixed true |
| `0207.7` / banked `r7` | Selection may write `er3`; **`0F85` clears `er3` and correction replaces it** before `0FFA` tests the bit | Native-owned alias, never a scenario input |
| `024C`, `0249` bytes | Earlier nonexecuted writers; `104A` and `106E` read | Once-only raw floor/bias snapshots |
| `0234.5`, `0217.1`, `0221.7` | Native correction reads/writes them | Once initialized, then native-owned persistent gates |
| `0217.0`, `021E.0` | Earlier nonexecuted writers; `1053`, `1061` read | Once-only explicit gate bits |
| `035B`, `024A` bytes | Native `1068/106D` and `1069/1074` stores | Retained initial bytes only; native results on completed events |

The register-bank word `er3` occupies `0206–0207` with `LRB=0040`; treating
`0207.7` as an independently injectable mode bit would overwrite a native
producer and was rejected during validation. No overlapping word footprint or
neighbor bit is resolved by last-write-wins. The result at `035B` is a native
software store; `024A` is the first clearly identified next-reader operand:
`1076 MOVB r2,off(024A)`. That next instruction and its `5802` helper are
**static-only**, beyond the stop. The lineage is the ignition-map `0248`
consumer through correction, not an independently executed dwell producer;
the eventual scheduling/physical meaning remains unknown.

## Exact arithmetic and branches

All values remain raw. Native operations, in order:

1. `0F85` zeroes `er3`; `0245` is loaded as a byte and `EXTND` sign-extends
   it to 16 bits. `ADD er3,A` is 16-bit wrapping; `0246` is loaded as an
   unsigned byte and `SUB er3,A` is 16-bit wrapping. Let the resulting word
   be `correctionOperand`.
2. `0248` is byte-loaded; `L A,ACC` produces a word base; `ADD A,er3` yields
   16-bit `correctedRaw` and a carry. The test of `0207.7` is the high sign
   bit of the *new correction word*, because the register alias has already
   been overwritten. If set, `JLT` retains the low result byte on carry and
   otherwise clears it to zero. If clear, word `CMP A,#00FF` retains a result
   strictly below 255; equality or above uses byte 255. This is not a wide
   mathematical clamp applied after the fact.
3. `100B` stores `boundedRaw` into banked `r4`. `0234.5` selects the `0x40`
   or `0x4D` comparison with raw `0238`, and is updated natively. The direct
   `0212.5` branch bypasses the P4/`024B` alternate path. `104D` first reads
   `r4`; `104E..1051` retain it if `>=024C`, otherwise replace it with the
   once-only floor `024C` (equality retains).
4. `0217.0` and zero detection set `0217.1`; `021E.0` or `0217.1` clears both
   result bytes. Otherwise the post-floor byte is stored at `035B`; byte
   `ADDB A,0249` writes `024A`, saturating to 255 on carry, with equality
   retained. The native stop is before `1076`.

`ADD er3,A` at `0FEC` has an existing **exact-form conditional assumption**
`oki.add-er3-a`: the pinned decoder/derived opcode lineage interpret it, but
the checked manufacturer ADD pages do not establish this object/accumulator
form. Strict execution therefore stops before it (`Unresolved`, not Pass).
Only explicit permission allows the subsequent local `ConditionalMatch`,
and dependency remains visible. No VTEC `SUBB` permission is inherited.

## Evidence and A/B

The private `m2i` reports contain the exact-original runs, scenario provenance,
ordered events and independent C# comparisons. Rust runner `0.17.0` and C#
keep separate ROM copies and persistent histories. `scenario-direct-ab` uses
one in-memory code-owned `ignition_map_0` cell, row 5/column 5, changed by
one raw count `81→82`; it emits no BIN. At event 4, native lookup/`0248` and
`035B`/`024A` each change `81→82`. At event 10, the same base difference
reaches correction but its negative-word/zero branch masks both final bytes.
Events 2/3/5/7 read the cell without changing lookup because of weight or
integer truncation; other events do not read it. Controls on selector,
producer, axes, map origin and histories remain equal across A/B.

The bounded strict run has three prefix-complete `0248` stores, three
unresolved correction attempts at `0FEC`, and six later `NotRun` events across
scratch `00/55/AA`. Explicit permission yields 66/66 local
`ConditionalMatch` A/B events in the final direct scenario. Separate actual
runs cover repeated inputs, axis endpoints/interior, `0247=0` and once-only
`0247=173`, floor replacement, zero/retention, `254/255/256` comparison
neighbors and word/byte wrap. A 768-case C# finite model audit is **not**
768 native executions. Public fixtures use invented programs/data only.

Read-only CLI:

```text
hondaecu research p28-ignition timing-chain-check <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --runner <runner-0.17.0> --scenario <m2i-scenario.json>
  --output <new-private-report.json>
```

The scenario is closed, versioned, bounded to 1–64 dense events and eight
trace witnesses, with only named raw software fields and an optional single
map-0 cell mutation. The existing exact binding, snapshots, path/alias guards,
bounded process transport, timeout and cancellation are reused. No arbitrary
PC/RAM writes, expected result, per-event selector/map ID, export plan,
receipt, token or firmware BIN is accepted. Public CI receives no private
ROM/scenario/report. `physicalRpmAvailable=false`, units raw, physical degrees
unavailable, `PcInspectionOnly / NotFlashReady`; GUI r3 paused/NotRun,
D1/D2 interactive acceptance NotRun, and hardware/full boot NotRun.
