# M2s — common-result consumer audit and bounded software continuation

M2s is **Partial**, not a completed quartet-consumer chain. Runner0.27.0 adds the
read-only `research p28-fuel common-result-consumer-check` command. Its Part A
continues a completed M2r event on the same CPU/RAM from literal stop-before22B1.
Part B audits actual readers of the four native common-word generations; no
unestablished scheduler or interrupt entry is executed.

## What runs, and where it stops

Historical `fuelPostSelectionCriticalChain` still stops before22B1. The new
`fuelCommonResultConsumerChain` starts there without `enter`, register restoration,
RAM reseeding, a second machine, JSON-to-RAM transfer or a repeated M2r suffix.
Entry PC/A/PSW/LRB/registers/pointers/stack and the software IE/native RAM state
must equal the completed prefix exit. Observer/admission changes do not change
machine state.

The audited continuation updates persistent012B hysteresis bits and selects a
byte software result. The positive013D path natively decrements the prior counter
when B7.0 is clear, or writes4 when B7.0 is set, then writes013B=11. The
zero-counter disable125 path writes013B=5. Both stop before236C,
where a separate subsystem begins. This is a coherent **software boundary**, not
a claimed pre-peripheral boundary. Written013D is consumed by the next native
event; all native writes remain in shared history.

The calculation path instead reads current03B4, independently calls the established
helper, and uses software divisor0136. It does not read the quartet. A zero divisor
stops Unresolved before2333 because the primary manual leaves quotient/remainder
undetermined. A positive divisor reaches an unadmitted JGT before233A: the primary
condition table and existing executor disagree on its predicate. M2s neither
changes that predicate nor skips the instruction. Completed new result is null;
prior native writes and completed M2r observations remain. Later events are NotRun
without further input snapshots or ticks. No rollback is performed.

Later static paths have a raw-data read at2394 without an established bounded
software producer, or an IRQ-dependent RTI at06A5 after a bypass. These are audited
barriers, **not executed coverage**. P1/P2, timer state, IRQ delivery, asynchronous
scheduling and hardware output remain NotRun. No generic SFR/default-zero fallback
is added.

## Quartet generations and actual readers

Each completed M2r event creates four distinct word generations:
22A5→03B6,22A8→03B8,22AB→03BA,22AE→03BC. Equal numbers do not merge the generations.
The independent C# history computes its own current03B4 and common helper result;
Rust quartet observations never become expected operands.

| Static reader | Selection and result | Why it is NotRun in M2s |
|---|---|---|
|05DF|One word at03B6[X1]. Native byte013C is shifted and extended into X1; an indexed03BE word is added before0196 is written.|Established callers are IRQ-domain paths with earlier hardware dependencies. No bounded software caller/ABI is established.|
|1550|X1=0 selects slot0, followed by software019x writes and a timer read.|Its actual caller first replaces all four words at152C/152F/1532/1535. This is not consumption of the M2r writer generations.|

No quartet reader occurs in the audited continuous22B1 suffix. There is no proven
four-read OEM loop here. The first reader performs one selected word read per
asynchronous invocation; its counter advances modulo4 elsewhere. Its invocation
is not recreated by a PC jump. `ScriptedConsumerEntry` is NotEstablished/NotRun.
There are no jumps to a remembered P2 consumer, timer ISR or channel helper.

## Closed scenario and source ownership

The version1 scenario uses one authoritative `initialState` with `prefix` (the
existing M2r initial contract) and `softwareSources`. Calls reuse the closed M2r
call structure:1..64 dense indexes, at most32 native ticks/event and8 selected
traces. Only justified once-initial software sources are added:

- `word011aMask1034`: only mask1034, preserving the existing011B.7 owner;
- `bit011f5`, `bit0120_0`, `bit00b7_0`: masked snapshots preserving neighbors;
- `byte00be` and `word0136`: raw bounded software snapshots;
- `history013b`, `history013d`: initial history, then persistent native ownership.

Their upstream writers are statically recorded but NotRun in this scope. They
are not sensor values or physical time. Existing0133/rawD9/disable125 inputs are
reused, not duplicated. No event may supply quartet words,019x,0150,current03B4,
registers/index, PC, branch, formula or consumer result. Before the first native
writer the quartet is diagnostic scratch only. Each slot acquires a NativeWritten
generation only when its own native word store executes; a completed M2r quartet
has four such separate generations. Partial or held slots retain their prior provenance.

## Validation and evidence limits

The independent model owns ROM, all prefix histories, masked sources,012B/013D
persistence, instruction flags/accesses/branches, four separate generations and
the local software output. Validator checks full entry continuity, ordered writes,
native address/width/bank/index, operands, flags and terminal disposition. A retained
old byte013B is not a fresh output after failure.

Public invented storage/program tests exercise four native word stores, native
indexed loop reads, sum/store and stop-before an invented peripheral-like access.
Different synthetic slot values belong only to this domain, never actual-ROM
reachability. Forged slot, stale generation, byte width, order, overwrite/reseed,
loop count, missing/duplicate reads, branch, bank, scale and scheduler jumps must
be rejected even when the final number matches. Real Rust subprocess probes verify
plumbing, not Honda behavior.

One-field in-memory A/B retains the existing closed mutation choices. Fuel-cell
effects can propagate through0140/current03B4/helper into the equal native quartet.
No downstream quartet-consumer witness can be claimed without a reader. The local
counter/disable result may stay equal despite a changed quartet; classify this as
`NoQuartetReaderInContinuousPrefix`/`ConsumerChainNotRun`, not invented selection
masking or a peripheral effect. Adaptive threshold/request/03A2 effects remain
separate; absent ungated-quartet divergence is legitimate. Code and60F8 are immutable.

The exact ADD DP,#word half-carry defect is repaired only after a failing invented
decoded regression and primary-manual review. Runner0.27.0 discloses
`word-add-dp-immediate-half-carry`;0.26.0 cannot execute the new operation. Unknown
forms,47 81,45 81 and disputed SUBB encoding are not promoted; strict M2i stays Blocked.

Actual StrictMatch Part-A events, native ticks, new quartet-reader invocations,
A/B comparisons/witnesses, model/storage-only tests, public synthetic cases and
historical compatibility repetitions are reported separately in private M2s
artifacts. Old M2r counts are not new M2s coverage. Historical stops22B1/2259/223B/2204
and numeric, IE, exporter and D1/D2 headless contracts retain separate regressions.
Common-helper saturation65535 is model/storage-domain coverage, not claimed
actual-ROM reachability: the unchanged original lookup and allowed source ranges
bound current03B4 below the helper-clamp threshold. Representative high native
values and the separate upper-bound proof are retained without a host quartet edit.

## Command and unchanged safety status

```text
hondaecu research p28-fuel common-result-consumer-check <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --runner <runner-0.27.0> --scenario <m2s-scenario.json>
  --output <new-private-report.json>
```

Reports and source identities are private; CI uses invented public fixtures only.
No firmware BIN, binding, compensation definition, export plan/receipt/token or
writable calibration field is added. Old private materials and portable folders
are preserved by before/after inventories. PcInspectionOnly / NotFlashReady;
physicalRpmAvailable=false; fuel/time/degrees and physical quartet role unknown.
GUI r3 remains paused/NotRun; Desktop tests are headless contracts, D1/D2 interactive
acceptance and hardware/full boot remain NotRun. No next stage is started automatically.
