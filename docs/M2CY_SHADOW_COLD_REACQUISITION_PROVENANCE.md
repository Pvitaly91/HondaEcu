# M2cy: Shadow reaching definitions and cold ADC reacquisition

M2cy starts at M2cx `9786bdfe136741e3930e7d4088bdc28565ee7f08`
([accepted CI](https://github.com/Pvitaly91/HondaEcu/actions/runs/42421482587)).
M2cx identified four shadow word writers and froze the indexed model's IE
and RT boundaries. M2cy asks which writer can reach the consumer for each
caller, how the cold branch selects another acquisition, and whether the
resulting generations survive the next calls. The source review binds the
retained decoded extents and the manufacturer instruction forms. It does
not extract a dynamic trace from the listing.

```text
FA/FB writer candidates ... [conditional path and generation] ...
  CAL276A or CAL2B64 ──[static]──> 5C86
  5CAF / 5CB4 ──[conditional indexed stores]──> 5CB7 shadow read
  5CB7 ──[qualified software load]──> STOP BEFORE IE5CB9
  IE5CB9/5CCB and RT5CCD ──X── native execution

Separate hypothetical handoff at 276D:
  276D → 276F → 2771
                 ├─ nonzero selector → 2766 → 2768 → possible CAL276A
                 └─ zero selector → 2773 → CAL2777 → 5CD9
      DATA03D1 → 5CDC → 5CDF / 5CE7 [qualified or unresolved C8]
                 ├─ conditional fault → STOP BEFORE BRK5CF8
                 └─ conditional normal frontier → STOP BEFORE RT5CF9
                     ... [matching ordinary frame] ... candidate 277A
                     ... [later aliases and unresolved handoffs] ... 60CC
```

The graph separates encoded control edges, modeled predicates and
hypothetical handoffs. No blocked edge grants execution authority.

## Shadow producers and caller-specific scopes

`256B` stores the initialization clear to DATA00FA/FB. `54DD` stores the
initial shadow pair, `3F18` stores pair A, and `3F2C` stores pair B. These
are local writer candidates, not four observations of the current owner.
`2710` is a separate DP-based clearing store. Its aligned word write can
cover both FA and FB in one generation. A conditional cold corridor can
connect that clear to `276A`, subject to the qualified loop exit, skipped
or disjoint subsequent stores, frame safety and no outside interference.
No route through the old initialization writer alone establishes that it
is the last writer. Unknown native startup and asynchronous state remain
separate from the conditional proof.

Caller `276A` is entered from `2768` in the reviewed cold corridor. Caller
`2B64` is entered from `2B61`, after the `2B57` and `2B5D` source edges
merge at `2B5E`. The latter performs a zero-page bit write disjoint from
FA/FB. `2B61` has its own USP-relative bit
write: at USP0150 or USP0151 it can affect FA or FB, respectively. A
listing annotation for a local bank or USP is not a dynamic reaching
definition; a proof for `276A` cannot seed the second caller. Both shadow
readers `3FF7` and `5CB7` refer to the same DATA slot. There is no new
ordering edge or proof that both see one generation.

FA is the low byte and FB is the high byte. A same-value rewrite has its
own generation; two separately written bytes do not become a word
generation merely because their numeric word matches. An aligned frame
word, indirect DP/X1/X2 access, page-relative access, local-bank alias or
USP-relative write can interfere. A conditional proof needs exact
word/byte alignment and excludes unresolved aliases. Unknown bytes and
known bits are carried as such.

## Cold branch and indexed generations

`2766` writes the selected local r0 bit from carry. `2768` decrements DPL
modulo 256, tests it, and either takes the loop edge to `2766` or falls
through to `276A`. The control relation is bounded and preserves DPH and
the retained flags. It provides no actual iteration count. After a
separate conditional return to `276D`, a new supplied P2 read selects the
loop branch. `276F` masks the selector in AL; `2771` returns to `2766` on
nonzero and reaches `2773` on zero. This read is distinct from P2 at
acquisition entry. The next iteration may have a different P2 or supplied
ADC values. `2773` records an ordered generation for DATA00F7=1.

The frozen prefix writes `DATA[03CE+index]` from supplied ADCR1H at `5CAF`
and `DATA[03C6+index]` from supplied ADCR0H at `5CB4`. Index 3 is the
source of DATA03D1 and index 5 is the source of DATA03CB. These cannot be
the same iteration. The timeline records one selector and two distinct
write generations per admitted iteration, including same-value writes.
The next iteration needs a link to the prior iteration, a hypothetical
return, and the reviewed repeat outcome. Unknown predicates or inputs
keep the prefix and stop the timeline. The composed sequence carries the
exact frozen child state into the bounded DPL loop. It stops before the
next CAL276A instead of resetting state or reusing the frozen writer's
generation namespace. The separate timeline can check multiple declared
iterations without presenting them as a composed ECU trace.

## Helper, C8 and the return frame

`CAL2777→5CD9` has a reviewed 17-node source region. The DATA03D1 read at
`5CDC` needs the exact current index-3 generation from `5CAF`, a qualified
loop exit and helper entry. A matching numeric byte by itself is not
provenance. The two source readings of C8/JGT at `5CDF` and `5CE7` remain
in conflict. Modeling can follow a consensus branch, but a disagreement
or missing predicate stops before the disputed branch. The admitted first
branch can reach the modeled error path; no normal traversal of `5CE7`
is established by that model. Comparison
operands are supplied symbolically; no private ROM constants are
published. A conditioned error path decrements the matching `2773`
DATA00F7=1 generation at `5CF1` and reaches the separate `BRK5CF8`
frontier. It does not establish normal return.

An ordinary `CAL2777` has a three-byte extent and candidate return `277A`.
Its formal word is stored at `SSP & FFFE` and the candidate SSP is reduced
by two. `RT5CF9` would select the same aligned word from pre-RT SSP plus
two, under normal frame ownership, matching saved bytes and generation,
valid memory, balanced nesting and absence of intervening stores. An
interrupt frame cannot satisfy this contract. A numeric candidate never
constitutes an observed native return or stack pop.

## Competing writes and the mode reader

An aligned word at `03CA` overwrites DATA03CB as its high byte. At `27B2`,
the DD0 `STB` form addresses `(USP - 0x4E) mod 65536`; `USP0419` reaches
DATA03CB. The store is one byte and does not align down. The current USP
generation and path must be established; unknown USP does not prove
disjointness. A qualified later path includes the separate loop exit and
helper-return premises, and cannot reverse `2777`, `27B2`, and `27D0`.
A later index-5 acquisition also replaces the generation,
even with equal ADC values. An index-3 iteration instead changes DATA03D1
and can coexist with DATA03CB from a different iteration. The model keeps
those owners distinct. Neither an isolated alias analysis nor a formal
RT candidate proves that either generation reaches `60CC` on the ECU.

```text
qualify shadow producer, caller path, and byte-pair generation
if an alias or reaching edge is unproved: retain the known prefix

for each explicitly linked acquisition:
    index = supplied_p2 >> 5
    record store(03CE + index, supplied_adcr1h, generation1)
    record store(03C6 + index, supplied_adcr0h, generation0)
    next stage requires its own return and branch premises

if helper entry is qualified and DATA03D1 has the requested 5CAF owner:
    compare both source predicates
    if they differ or are unknown: stop at C8
    otherwise retain only the qualified software effects
check ordinary RT obligations separately; never pop the frame
```

## Validation and remaining scope

The public fixture corpus uses invented input and explicit source
premises. The independent reference does not import new implementations.
Full output, including refused and unknown cases, is frozen before model
comparison and compared through EOF. CI admits the finite reviewed source
overlay and retains the inherited full QA fallback for unknown changes.
The first actual comparison matched all 211 records across seven functions,
including 48 complete conditional results, 99 indeterminate obligations,
six indeterminate branches and 58 refusals. The full stream has 12,335,273
bytes and SHA-256 `e67d309b80c2282d5d1bc9c8adb46a226eea2216fff32b6bbb1fb6e25f10c5fd`.
No fields are excluded from the comparison.
Public logs report case identities, counts and digests, and omit private
retained source, bytes and operand inventories. The preservation ledger
keeps the seven prior exceptions separate from new unauthorized changes.

Next scope: qualify the remaining cold return/IE and C8 dependencies and
prove or exclude the competing writer paths before the mode consumer.
No M2cz work is started here. `EXECUTION_BLOCKED`, `FirmwareReady=false`,
and `STOP_BEFORE_STBUF_2995` remain in force.
