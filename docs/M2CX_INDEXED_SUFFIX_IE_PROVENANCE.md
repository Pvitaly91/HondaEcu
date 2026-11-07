# M2cx: Indexed acquisition suffix and IE boundary

M2cx starts at accepted M2cw commit `e072dd9cf2ff68bacd3ea8353decae9ff55b7383`
([CI](https://github.com/Pvitaly91/HondaEcu/actions/runs/42417729118)).
It extends the source model after the indexed writer at `5CB4`. M2cv and
M2cu already establish the conditional ADC producer, and M2cw identified
the next sites without modeling their full effects. M2cx adds shadow
qualification, separate IE intents, the admitted part of the disconnected
suffix, generation retention, and hypothetical return obligations.

```text
5C86 --[conditional timer bypass and supplied IRQH old bit]--> 5CA5..5CB4
     --[confirmed next PC]--> 5CB7
     --[qualified DATA00FA/FB]--> STOP BEFORE IE5CB9
                                      :
                          explicit symbolic boundary only
                                      v
5CBB --[qualified operands and conditional SFR intents]--> 5CCB
     --[separate symbolic admission only]--> STOP BEFORE RT5CCD
RT5CCD -X-> no actual return; formal candidate 276D or 2B67
```

`5C89` (timer/IE route) and `5CD2` (BRK after the diagnostic write) remain
separate frozen stops. The source edge to the next address does not grant
permission to perform a peripheral access. The post-IE entry never consumes
a purported readback or IRQ result from the first intent.

## Source inventory and detached suffix

The instruction references below are printed pages of the September 1991
OKI MSM66201 Instruction Manual. The inventory binds instruction extents
and successor addresses without publishing private instruction bytes.

| PC | Form and length | Source-qualified effect | Next source PC |
| --- | --- | --- | --- |
| `5CB7` | `L A,N8`, 2, p. 3-69 | DATA00FA/FB → A, DD1, ZF; CF/HC retained | `5CB9` |
| `5CB9` | `ST A,N8`, 2, p. 3-154 | DD1 word intent, A → IE001A/1B | `5CBB` |
| `5CBB` | `ANDB PSWH,#N8`, 3, p. 3-27 | explicit MIE clear; implicit CF/ZF/HC unresolved | `5CBE` |
| `5CBE` | `ADDB N8,#N8`, 4, p. 3-19 | symbolic P2 byte RMW at 0024, `+20h`, CF/ZF from result, HC0 | `5CC2` |
| `5CC2` | `MOV off N8,N8`, 4, p. 3-87 | symbolic TM2 word 0038/39 → current page offsets 5A/5B; flags retained | `5CC6` |
| `5CC6` | `ORB PSWH,#N8`, 3, p. 3-110 | explicit MIE set; implicit CF/ZF/HC unresolved | `5CC9` |
| `5CC9` | `L A,N8`, 2, p. 3-69 | qualified DATA00F8/F9 → A, DD1, ZF | `5CCB` |
| `5CCB` | `ST A,N8`, 2, p. 3-154 | second DD1 word IE intent; separate blocked boundary | `5CCD` |
| `5CCD` | `RT`, 1, p. 3-125 | ordinary frame obligation; no actual pop | caller-specific, unobserved |

`5C9E` also has a static edge to `5CCD`; it belongs to the unmodeled
timer/IE route. The detached suffix admits only page `0200` and the
explicitly supplied destination pair DATA025A/025B. The 16-bit aligned
store is little-endian, retains flags and emits a new writer generation
even on an equal-value store. The word is supplied TM2 provenance, with
no claim of a timer latch or observed counter value. P2 intent is based
on a supplied byte and qualified source generation; it creates no port
latch update. Unknown bits remain unknown. For the explicit PSWH masks,
unresolved implicit CF/ZF/HC do not become guessed bits; the later ADDB
and word load establish only the flags they actually define.

## Pure interfaces and porting outline

`data00fa_shadow_lineage` checks the candidate little-endian byte pair and
its generation. `indexed_suffix_pre_ie` loads the qualified word;
`ie5cb9_boundary_obligations` validates its prospective store. The
`indexed_suffix_composition` interface consumes the exact frozen prefix and
advances only to the first IE boundary. `indexed_suffix_post_ie` uses an
independent hypothetical state. `data03cb_suffix_retention` checks writer
identity, and `indexed_return_obligations` checks the hypothetical frame.

```text
prefix = frozen_indexed_caller(caller, state)
if prefix reached 5CB7:
    shadow = qualify_word_pair(00FA, generation, mapping, intervening_events)
    A, DD, ZF = shadow.word_or_partial, 1, zero_consensus(shadow)
    return stop_before_IE(prefix, A)  // separate query can describe the intent

detached = require_hypothetical_post_IE_entry(supplied_state)
apply_explicit_MIE_clear(detached); mark_implicit_flags_unknown()
record_P2_intent_and_ADDB_flags(supplied_P2 + 0x20)
write_word(page_0200 + 0x5A, supplied_TM2)
apply_explicit_MIE_set(detached); mark_implicit_flags_unknown()
A, DD, ZF = qualify_and_load_F8_pair()
return stop_before_second_IE_or_formal_RT_frontier(A, explicit_premise)
```

## DATA00FA provenance and the shared reader

DATA00FA/00FB is one little-endian software word. Direct word producers
include `256B` (initialization clear), `54DD` (initial pair), `3F18` (pair A),
and `3F2C` (pair B). A separate DP-based RAM-clear path at `2710` can overlap
both pairs under its retained premises. Aliases via page-zero off addressing,
selected local banks, arbitrary pointing registers, USP, and an overlapping
CAL word are possible until their address and reaching path are excluded.
No reviewed caller path identifies the current native pair at `5CB7`.
The bounded source search joined 11,499 decoded extents and classified
direct, page-relative, indirect, local-bank, and implicit stack writers.
The candidate list is local source evidence; it is not a global proof of
which dynamic writer wins.

`3FF7` and `5CB7` load the same software word; both precede distinct IE
stores. This is a shared source dependency. It supplies no edge from `3FF7`
to `5CB7`, no common current generation, and no physical IE ownership.
DATA00F8/00F9 is a separate word. Equal values or a common producer block
do not make the slots interchangeable. The model requires a common byte-pair
generation, qualified mapping, and explicit no-interference; it rejects a
stale pair even when the bytes agree. Known bits can establish that the word
is nonzero without determining the complete word.

## IE5CB9 and device applicability

The word load sets DD1 and sets ZF from the word's zero test. CF and HC are
retained. `5CB9` is a DD1 word store of A to aligned DATA/SFR `001A` (IE),
with no implicit flag changes. The formal intent records its 16-bit source
and destination; it changes neither the physical IE register nor the
software shadow. DD0 byte-store substitution is outside this proof.

MCU revision, applicable IE behavior, current IE ownership, physical SF,
PSW/MIE, pending requests, and interrupt/frame safety remain unbound.
Manufacturer pages 165/168/169 support the set-one enable reading, while
page 167 gives a conflicting IE-zero condition. Both source readings remain
qualified hypotheses. A supplied MIE value cannot establish interrupt or
NMI exclusion, and no modeled effect creates a TX/RX request.

## DATA03CB and normal return

Index 5 is the frozen `5CB4` writer to DATA03CB. An equal-value rewrite is
still a new write and generation. The aligned page-relative `5CC2` word
store writes offsets `5A/5B`, disjoint from `03CB` for every qualified page.
The reviewed local footprint cannot overwrite that byte. Retention of a
particular generation also requires a matching generation and exclusion of
competing indirect stores, overlapping frame writes, asynchronous effects,
and repeated acquisitions. Local retention supplies no native reaching
definition.

The two callers keep separate contexts: `276A→5C86` (listed DD1, candidate
`276D`), and `2B64→5C86` (listed DD0, candidate `2B67`). The ordinary CAL
candidate stores `(caller + 3) mod 65536` at aligned incoming SSP and
subtracts two from SSP. For an ordinary RT candidate the matching pre-RT
SSP plus two selects the same aligned word. The saved bytes, creator, frame
generation, memory applicability, balance, integrity, and absence of
interfering aliases must agree. This does not apply to RTI frames. It
produces a formal candidate only; actual return and frame pop are null.

In the cold caller the `276D/276F/2771` corridor may revisit `276A`. Exit
through `2777→5CD9` requires its own `RT5CF9` frame proof before candidate
`277A`. Later aligned `03CA/03CB` frames and the `27B2` USP-relative store
can clobber DATA03CB. The source model cannot yet bind a unique definition
to the mode consumer across those frontiers.

## Equivalence, privacy and preservation

The validator publishes a deterministic, full-output canonical JSONL stream.
An independent reference uses primary ISA equations and the frozen reference
models for retained children. The expected bytes are frozen before the first
comparison. Tests compare every record and check the semantic refusals,
including missing and stale generations, unsupported aliases, wrong word
descriptors, and attempts to promote an intent to hardware authority.

The frozen corpus contains 151 records across all seven interfaces:
51 complete conditional results, 42 indeterminate obligations, 57 refusals,
and one indeterminate branch. Its complete 3,896,701-byte JSONL stream has
SHA-256 `11a05c3445e5593c295220c24d83ab7fb03427ff3bce3623c6b733d9491eaeed`.
The first local comparison matched every record, with no excluded fields.

The source guard admits only the finite reviewed M2cx overlay. Unknown
changes route to the inherited historical full QA. Public fixtures contain
invented typed operands, source addresses, and proof identities; neither
OEM instruction payloads, raw private inventories, ROM paths, nor archive
secrets are inputs to public CI. Delivery records the exact source bindings,
test counts, and decompressed comparison through EOF separately from the
seven inherited preservation exceptions.

The next bounded research candidate is a static reaching-definition proof
for the shadow bytes across each caller, followed by an analysis of the
cold-caller re-acquisition/`RT5CF9` dependencies. No later milestone is started
here. All results retain `EXECUTION_BLOCKED`, `FirmwareReady=false`, and
`STOP_BEFORE_STBUF_2995`.
