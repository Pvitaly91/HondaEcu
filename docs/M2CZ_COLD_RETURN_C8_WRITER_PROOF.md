# M2cz cold returns, C8 and DATA03CB writer exclusion

M2cz starts from accepted M2cy `83ffa492a1565d15c4f8b32f180e34e884e431ac`,
whose verdict is `CONDITIONAL_SHADOW_AND_COLD_REACQUISITION_EQUIVALENCE_ESTABLISHED`.
M2cy already modeled the cold loop, the first helper fault, and ordinary
frame candidates. The new questions are which branch outcomes survive both
primary C8 readings, which detached helper continuations can be modeled,
and which exact writers can displace a generation before the mode reader.
The retained extent inventory and previous frame and helper receipts are
bound by digest. [Accepted M2cy CI](https://github.com/Pvitaly91/HondaEcu/actions/runs/42423940535)

```text
5CB4 index5 ── conditional DATA03CB writer ──> IE5CB9 / IE5CCB
                      peripheral and stack obligations :
                                          formal RT5CCD :
                                                       v
  276D → 276F → 2771 ── conditional exit ──> 2773 → CAL2777 → 5CD9
    5CDC DATA03D1 → 5CDF C8 ── consensus greater ──> fault path → BRK5CF8 stop
                            : conflicting fallthrough
                            v separate hypothetical 5CE1
                  5CE3 JGE ── conditional taken ──> RT5CF9 stop
                             otherwise → 5CE5 → 5CE7 C8
    RT5CF9 : hypothetical ordinary frame : candidate277A
         ... ADC and stack premises ... 27B2 possible overwrite
         ... cold path and mode frame ... 27D0 → CAL5F45 ... 60CC
```

Arrows from calls denote encoded targets. The colon lines mark hypothetical
state transfers. The later path retains separately qualified aliases and
unexcluded interference. No edge in this graph constitutes a native trace.

## C8 source conflict and exact branch edges

The full OKI MSM66201 Instruction Manual page 3-66 prints the OR predicate
for JGT. The comparative interpretation uses AND. The related-family
comparison has a different opcode and cannot establish the meaning of C8
on this device. No applicable manufacturer correction was authenticated.
The source review preserves the two readings rather than using emulator
behavior as an authority. C8 reads CF and ZF, writes no flags, and uses a
signed 8-bit displacement from PC plus two. The relevant compare preceding
each branch is unsigned byte comparison. [MSM66201 Instruction Manual](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/Oki_66201_Instruction_Manual.pdf)
· [nX-8/500S Instruction Manual](https://downloads.laboratoryb.org/insight/documents/OKI/nx_800.500S_core.pdf)

| CF | ZF | Printed OR | Comparative AND | Conditional result |
| --- | --- | --- | --- | --- |
| 0 | 0 | taken | taken | consensus taken |
| 0 | 1 | taken | fallthrough | disagreement |
| 1 | 0 | taken | fallthrough | disagreement |
| 1 | 1 | fallthrough | fallthrough | consensus on raw flags only |

An unsigned compare produces one of the first three rows. There is no
consensus fallthrough in that domain. Partial flags can produce a set of
candidate rows; the model classifies disagreement or unknown without
selecting an edge. At `5CDF` the target is `5CED` and fallthrough is
`5CE1`. At `5CE7` the target is `5CED` and fallthrough is `5CE9`.
An exhaustive static comparison over all 256 byte values with the
authenticated private comparands found no first-branch consensus and no
common full path, including the fault route. The greater-consensus fault
in public fixtures uses invented comparands. Equal terminal boundaries
under competing interpretations do not establish equal paths.

## Helper and conditional frame candidates

The full entry still carries the frozen M2cy state through the reviewed
17-node helper. `5CD9` sets the selected DP to the DATA03D1 slot, `5CDC`
requires the retained index-3 generation, and `5CDD` compares the byte.
The source comparison values are represented by invented parameters in
public fixtures. The first C8 remains the barrier to full normal return.

For a separately declared hypothetical `5CE1` entry, the model carries
the exact prefix snapshot into CMPB and the unconflicted `5CE3` JGE. A
taken JGE reaches the local frontier before `RT5CF9`. A false JGE reaches
`5CE5` and the second C8. Greater consensus there can reach the same
qualified fault suffix. The detached normal frontier grants no transfer
from the full helper entry. It remains inapplicable to the cold source
join, which invokes only the full-entry model.

The modeled error branch retains the marker writes at `5CEF` and `5CF6`.
It requires the matching generation of DATA00F7=1 from `2773` and excludes
intervening writes, including a CAL word aligned to F6. Under the
decrement reading of the DECB instruction, `5CF1` writes zero, sets ZF,
clears HC, and preserves CF. The manual's function box on page 3-56 has a
contrary increment notation. The instruction name, prose and summary
support the bounded decrement reading used by the accepted fault model.
The zero result takes the fallthrough at `5CF4` toward `BRK5CF8`, where
the model stops. A supplied zero, an unknown value or a stale generation
does not establish this fault route or a successful return.

For CAL at `276A` and `2777`, the three-byte instruction yields candidates
`276D` and `277A`. A qualified ordinary frame stores its word at incoming
SSP aligned down, then subtracts two from SSP modulo 65536. The formal
RT candidate adds two to pre-RT SSP and aligns the resulting read address.
Each frame needs its own creator, saved bytes, generation, memory
applicability, integrity, balanced nesting and alias exclusions. A shared
intercall SSP is a separate premise, with matching returned and incoming
values. Frame generations remain distinct when the address is reused.
`RT5CCD` additionally needs hypothetical clearance of the two IE
frontiers. A fault frontier cannot supply `RT5CF9`.

## Competing writes through the cold corridor

The local index-5 write at `5CB4` provides the candidate generation G.
Index 3 in a separate acquisition can supply DATA03D1 to `5CDC` without
writing DATA03CB. A later index-5 acquisition replaces G even when the
byte is equal. An aligned word at `03CA` writes DATA03CB as the high
byte. A frame with an odd supplied SSP at `03CB` still starts at `03CA`.
An unknown indirect or stack address cannot be excluded. Page, local-bank,
pointer, frame and async writes are assessed in the bounded source order.

The detached `277A` corridor enters `279E → 7C0B` and transfers via
`7C11 → 27A2`. The approved mapping and disjoint writer premises permit a
supplied USP generation to reach `27B2` through this window. The path
starts with ADC-related dependencies and does not recover a native USP
owner from initialization. The `27AE` immediate load supplies AL across
`27B0` to `27B2` under exact source premises. Public fixtures pass a symbolic
immediate. The
DD0 store uses `(USP - 0x4E) mod 65536` with byte width. USP0419 therefore
selects DATA03CB and a known disjoint address can exclude the write.
Unknown USP or unbound source context leaves overlap unresolved. The
review joined 61 retained extents. Under the qualified mapping, 27 local
software writes were disjoint from the tracked byte and the control and
USP slots. A further 238 inherited mode effects were disjoint from the
tracked byte in their reviewed scope.

`27D0` calls `5F45`, and the taken `60C0` edge via `60C9` locally leads to
the proposed mode consumer at `60CC`. The writer
proof distinguishes a verified local origin, conditional retention across
the assessed window, and the as-yet unbound source path to that reader.
DATA03D1 influences helper decisions. Its value and owner do not certify
anything about the later DATA03CB owner.

## Interfaces, verification and remaining scope

The pure contracts separate `c8_branch_consensus`, `helper_5cd9_extended`,
`cold_return_path_obligations`, `cold_caller_mode_source_join`,
`usp27b2_alias_proof`, `data03cb_competing_writer_exclusion`, and
`data03cb_to_mode_reaching_definitions`. The source join reuses the exact
cold child result, its counter generation, and the unchanged helper
prefix. The explicit hypothetical helper handoff includes a disjoint CAL
footprint and no intervening writes. Aligned frame words at F6 or 03D0
could invalidate the carried counter or DATA03D1 respectively. The join
stops at the first unresolved or fault boundary.

```text
outcomes = evaluate_both_C8_readings(source_bound_flags)
if outcomes disagree or vary: keep_state_and_stop_before_branch()
if separately_admitted_at_5CE1: apply_cmp_and_jge_to_carried_state()

check_each_ordinary_frame_without_pop()
for event in the bounded source window:
    require its source, order and address premises
    if overlap is known: apply the new writer generation
    if overlap is unknown: withhold retention
stop_at_first_unproved_handoff_before_mode_read()
```

The independent reference uses a separate implementation and is frozen
before the first actual model call. Full canonical records include refusals,
branch alternatives, candidate frames and ordered writes. The finite CI
overlay keeps the historical fallback for unknown changes. Privacy checks
cover source output policy, staged and committed diff, CI logs, complete
artifacts and final report. The preservation audit records the seven
inherited exceptions separately.

The first actual comparison matched all 169 records. The 9,824,684-byte
stream contains 26 complete conditional results, 37 indeterminate
branches, 74 indeterminate obligations and 32 refusals. SHA-256 is
`cfd16c992d04c1c2e8f85a15ce4097013be0b7dd6f626153a1fd246e8d5ae00a`.
The comparison excludes no fields.

The next bounded M2da scope is to obtain applicable primary C8 evidence
or qualify an independent normal helper entry and then resolve the
intervening call/frame dependencies before mode read `60CC`. The
research gates remain `EXECUTION_BLOCKED`, `FirmwareReady=false` and
`STOP_BEFORE_STBUF_2995`.
