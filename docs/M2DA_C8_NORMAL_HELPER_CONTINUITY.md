# M2da C8 evidence, helper continuity and the DATA03CB mode read

M2da starts at accepted M2cz commit `9d0547a312162a9d2509bf3db1a23a018c5cc008`.
The baseline supplied an unresolved C8 interpretation pair, a detached
`5CE1` fragment and a conditional writer exclusion window. This milestone
adds a bounded primary evidence decision, exact private operand feasibility
and direct-ingress checks, a detached `5CE9` transformation, ordered live
frame validation, and a separately admitted mode path to the actual
`60CC` read in the frozen software model. [Accepted M2cz CI](https://github.com/Pvitaly91/HondaEcu/actions/runs/42427254844)

```text
5CB4 index5 ── ReachingDefinitionCandidate ──> 5CB7 DATA03CB generation
    IE5CB9 and IE5CCB ... FormalFrameObligation ... RT5CCD → candidate276D
    276D–2771 ── ConditionalBranch ──> 2773 → CAL2777 → 5CD9
    5CDC DATA03D1 → 5CDD CMPB → 5CDF C8 [PrimarySourceConflict]
         taken → 5CED marker and qualified F7 fault → stop before BRK5CF8
         fallthrough ... DetachedConditionalEntry 5CE1 → JGE5CE3 → RT5CF9 stop
                             not taken → 5CE5 → 5CE7 C8 [PrimarySourceConflict]
                     fallthrough ... DetachedConditionalEntry 5CE9
                                             → JGE5CEB → RT5CF9 stop
    RT5CF9 ... FormalFrameObligation ... candidate277A
    separate 277A premise → 279E → 7C0B → 7C11 → 27A2 → 27B2
                           → 27CE → CAL27D0 → 5F45 → 60CC → RT60E4 stop
    full 5CD9 → 277A → mode read [NativeContinuityBlocked]
```

Encoded targets are `ConfirmedStaticCFG`. Dotted handoffs remain separate
premises. The local fault and normal outcomes are bounded software
projections, with a distinct stop and generation proof for each stage.

## Primary C8 evidence and source-specific flags

The September 1991 OKI MSM66201 Instruction Manual prints the C8/JGT OR
predicate on page 3-66. The same condition table calls the comparison
greater and lists JLE as CF1 OR ZF1. Printed JGT overlaps that JLE on the
equal and lower unsigned compare cases. The comparative AND predicate
avoids the overlap. The related nX-8/500S manual documents AND under a
different opcode. A mirror of the same edition or software emulation adds
no independent manufacturer authority for C8. The targeted search did not
authenticate a revision-specific correction. The adjudication retains both
readings and distinguishes same-edition mirrors, related variants and
unsupported claims. The seven reviewed document identities include an
archival Chapter 3 scan with the same wording and no edition leaf, the
MAC66K mnemonic listing, a 1998 instruction list without the GT predicate
and a Japanese device specification limited to device scope.
[MSM66201 Instruction Manual](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/Oki_66201_Instruction_Manual.pdf)
· [nX-8/500S Instruction Manual](https://downloads.laboratoryb.org/insight/documents/OKI/nx_800.500S_core.pdf)

| CF | ZF | Printed OR | Comparative AND | Unsigned CMP provenance |
| --- | --- | --- | --- | --- |
| 0 | 0 | taken | taken | greater |
| 0 | 1 | taken | fallthrough | equal |
| 1 | 0 | taken | fallthrough | lower |
| 1 | 1 | fallthrough | fallthrough | impossible |

C8 reads CF and ZF, writes no flags and branches by signed rel8 from PC
plus two. Exact private operands were analyzed over all 256 possible bytes
without publishing those operands. At `5CDF` the source-specific domain
contains only equal and lower. Printed OR takes the first edge for both
cases, so the full OR route reaches neither later C8 nor either JGE. The
comparative path has separate later domains. Generic consensus for greater
does not prove a consensus on this entry. The source feasibility contract
keeps full-entry and detached domains separate and refuses out-of-domain
flags and wrong displacement.

## Helper CFG, DATA03D1 and detached JGE

The 17-site helper audit binds the original compare extents, widths, flag
inputs and branches without disclosing raw operands. The `5CDC` DATA read
requires the matching `5CAF` index-3 generation in the frozen helper state.
Independent search over 11,499 retained extents found only the encoded
fallthrough from `5CDF` to `5CE1` and from `5CE7` to `5CE9`. The audit did
not establish an independent indirect, call or return ingress to either
location. A separate hypothetical branch premise is required for each
detached continuation. Its state comes from the exact frozen prefix.

JGE is `CD rel8` and reads CF only. It takes the branch when CF is zero,
retains flags and uses PC plus two with a signed displacement. Both `5CE3`
and `5CEB` target `5CF9` on taken. The preceding CMPB writes CF for unsigned
lower and ZF for equality. The `5CE9` model narrows the carried AL domain
under the explicitly hypothesized comparative fallthrough at `5CE7`,
updates CF/ZF for its separate compare and reports either an RT frontier, an
error-marker frontier or an unresolved predicate. It keeps the original
helper entry unconnected. No source condition proves normal execution from
`5CD9` through the disputed first C8.

The M2cz fault remains bounded to its source-qualified F7 generation from
`2773`. The accepted DECB decrement projects one to zero and reaches the
fallthrough of `5CF4` and the marker on `5CF6`. The manual still has contrary
increment notation in the function box on page 3-56. The mnemonic, prose
and summary support the qualified decrement. The model preserves this
qualification and stops before `BRK5CF8`. Unknown, stale or substituted
counter state cannot supply that path. A fault frontier cannot satisfy an
ordinary `RT5CF9` obligation.

## Ordinary frame lifetimes and the two IE gates

`CAL276A` and `CAL2777` have return candidates `276D` and `277A` under
separate ordinary frame premises. The prospective CAL word starts at
`incomingSSP & FFFE`. It subtracts two modulo 65536, and the formal RT
read uses `(preRtSSP + 2) & FFFE`. All 65,536 incoming SSP values were
checked for that arithmetic relationship. The frame owner, bytes, memory
mapping, nesting and integrity are independently required. An RTI frame
does not have the required ordinary geometry.

The new chain splits the write window into indexed-live, between-calls and
helper-live phases. A byte at the high half or a word aligned across the
active word invalidates the live generation. A dead slot can be reused
only with a new generation and matching owner. Potential control or
pointing-bank interference remains refused. Relevant stack word aliases
include F6/F7, 03D0/03D1 and 03CA/03CB. The two formal IE handoffs are checked
separately before `RT5CCD`. Neither grants a hardware IE state or interrupt
authority. Frame obligations are kept out of the DATA write journal.

## Detached cold corridor and mode consumer

The new review joined 49 exact extents in the `277A→27D0` window. Three
acyclic branches converge at `27CE`, with one `27B2` each. Under the accepted
mapping, 27 other local write footprints are disjoint from DATA03CB and
from the required control and USP slots. The separate proof preserves the
supplied USP generation across the admitted path and excludes or records
the byte store at `(USP - 0x4E) mod 65536`. `USP=0419` overlaps DATA03CB.
Unknown USP gives no exclusion. The `27AE` immediate supplies AL across
`27B0`. No native initial USP is supplied by this proof.

A later index 5 or an aligned frame word at `03CA` replaces the DATA03CB
generation, even for the same byte. Index 3 selects the distinct DATA03D1
slot. A non-overlapping `CAL27D0` needs a new ordinary frame generation.
The conditional mode proof passes the exact snapshot and verifies the
carried generation at `60CC`, which the taken `60C0` edge reaches via the
DP setup at `60C9`. It consumes the unchanged frozen mode model's reads,
register state and writer journal, and preserves the stop before `RT60E4`.
The proof binds the carried slot and applicable context to the unchanged
supplied mode-entry snapshot. Other entry registers remain supplied premises.
The detached `277A` premise and applicable path/mapping remain explicit.
The full-entry cold graph still stops at its first unproved boundary and
does not import that detached result as native continuity.

## Models and pseudocode

`c8_primary_evidence_adjudication` distinguishes document identities and
refuses evidence promotion. `c8_source_feasibility` compares each branch
against its actual bounded flag domain. `helper_normal_entry_provenance`
identifies the retained direct predecessors. `helper_normal_continuation`
can project both detached compare/JGE stages without choosing the full
entry. `cold_frame_generation_chain` checks both formal frames and ordered
competing writes. `cold_normal_mode_source_join` binds the actual frozen
index-5 generation and exact audited indexed frame to the earliest source
frontier. `cold_to_mode_intervening_writes` qualifies the post-helper
window. `data03cb_to_60cc_source_proof` verifies the read in a separate
conditional mode invocation.

```text
check_exact_target_source_and_revision()
flag_domain = source_specific_compare_domain(branch, interpretation, entry)
retain_only_qualified_flags(flag_domain, supplied_flags)
require_bound_direct_predecessor_or_explicit_detached_entry()
carry_frozen_state(); narrow_AL(); apply_CMPB_and_JGE(); stop_before_RT()

for each explicit write in source order:
    check_current_frame_lifetime_and_word_alignment()
    withhold_frame_if_live_word_or_control_alias_is_unbound_or_overwritten()

admit_detached_277A(); check_USP_writer_and_new_mode_frame()
carry_exact_DATA03CB_generation_into_frozen_mode_query()
verify_typed_60CC_read_and_disjoint_journal(); stop_before_RT_60E4()
```

## Verification and next scope

The independent oracle freezes complete expected records before the first
actual comparison. The corpus retains refusals, ambiguous predicates,
live-frame conflicts, unknown aliases and both detached and full entries.
The first comparison matched all 224 records, including 85 complete
conditional results, 4 ambiguous branches, 104 unresolved obligations and
31 refusals. The 12,281,061-byte stream has SHA-256
`6581dec8d208617854a96dcffd28d2c523f8916ed08effbf36e8d1862a36e94b`.
No fields were excluded.
The finite CI overlay preserves historical fallback routing. Privacy checks
cover the staged and committed diff, diagnostic policy, CI logs, artifacts
and final report. Preservation keeps the seven inherited exceptions
separate from new differences.

The recommended M2db scope is a primary adjudication of C8 or independent
source proof for a normal ingress, followed by a review of the handoff from
the helper's formal return into the already verified detached mode window.
The research gates remain `EXECUTION_BLOCKED`, `FirmwareReady=false` and
`STOP_BEFORE_STBUF_2995`.
