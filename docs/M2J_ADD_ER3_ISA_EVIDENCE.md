# M2j — exact 47 81 evidence dossier

Research/code delivery is complete. Exact instruction proof is **partial**;
full strict M2i closure is **Blocked**. Neither the old 96 conditional matches
nor new software probes establish the physical CPU instruction. No exact-form
admission, decoder or executor semantics has been promoted or changed.

## Question and source independence

The disputed original bytes are `47 81`, reached at `0FEC` in M2i and at `07F8`
in the older compact slice. We need both an independent encoding/length proof
and the live architectural effects of the decoded instruction. `45 81`, SUBB
and other word-object forms are separate evidence boundaries.

Previously exhausted sources remain the same sources, not new evidence:

| Source | Edition / previously reviewed material | Limitation |
| --- | --- | --- |
| [OKI MSM66201 Instruction Manual](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/Oki_66201_Instruction_Manual.pdf) | First edition, September 1991; printed 1-21–1-23, ADD 3-13–3-17, summary Tables 3-14/15 on 3-192/193 | Documented word ADD forms do not supply the missing word object/accumulator suffix rule |
| [66207Chapter3.zip](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/66207Chapter3.zip) | Body identifies MSM66201; Page_12–16.TIF and summary pages; no independent title/edition imprint | ZIP name is not processor identification; a separate scan is not a new ISA edition |
| [66207usersmanual_incomplete.zip](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/66207usersmanual_incomplete.zip) | Incomplete MSM66201/207 body; printed 30–41, aliases, PSW and register banks | Architecture evidence, not an opcode map |
| asm662/dasm662 | Pinned source 94612d1; 66207.op RCS 1.9 and generated op.c RCS 1.15 | Derived `44+N,81` and `U`; generated files/forks are not independent vendor evidence |

The M1b/M1c/M1d/M1e trails were read before targeted search. Hashes, scan
members and provenance are retained privately. No old scan was downloaded
again under a new name. The project's decoder/executor and C# model share
the hypothesis; matching their outputs cannot close this proof chain.

## Targeted A/B/C research

A: The existing 1991 manual was visually rechecked for general DD and operand
rules (1-21–1-23, 2-2 and surrounding addressing chapter), and ADD code tables
3-13–3-15. The word register prefix `44+N` is supported for other documented
word ADD forms. The missing link is permission to combine that prefix with
suffix `81` as word `obj ← obj + A`. The byte `obj,A` table does not supply it.
This is a bounded finding about checked pages, not a claim that no such
specification exists anywhere.

B: A genuinely new primary document was obtained:
[OKI nX8/500S Core Instruction Manual, second edition, June 1999](https://downloads.laboratoryb.org/insight/documents/OKI/nx_800.500S_core.pdf).
Printed 1-1 states **basic assembler-level** upward compatibility; Chapter 1
page 43, section 1-10 describes composite instructions. Printed 3-A-7 actually encodes ERn with
`64+n` and accumulator ADD suffix `A4`. Thus it cannot establish the binary
meaning of `47 81` on nX8/200. Its flags must not be imported either.
Searches for another compatible edition, opcode map, addendum and errata
also led to short datasheets and the same old manual. The Bitsavers 1988/1990
databook URLs returned HTTP 403; another 1990 mirror timed out. Search snippets
from those books were not treated as reviewed primary evidence.

C: A new compatible vendor-tool lead was obtained and visually checked:
[OKI MAC66K Assembler Package User's Manual, third edition, November 1993](https://datasheet.datasheetarchive.com/originals/library/Datasheets-UEA1/DSAFRAZ0014345.pdf).
Printed 1-1/1-5/1-7 establish RAS66K provenance, target restrictions and
nX8/200 support; 4-235/236 explain byte listings; 4-242 identifies an MSM66201
target. The illustrated listing is for MSM66507, not an exact `47 81` listing
for MSM66201. Navigation through the examples and instruction-related text
did not produce such a listing. This manual documents the tool, not its
missing exact output or runtime semantics. No provenance-verified vendor
assembler distribution or simulator reference execution was obtained; no
unknown executable, activation bypass or administrative installation was used.

## Exact claim matrix

“Primary architecture” below describes registers if the hypothesized form is
valid; it does not prove that these bytes use them.

| Claim | Established evidence / applicability | Remaining unknown for 47 81 |
| --- | --- | --- |
| Decode and length | Derived table: `ADD er3,A`, two bytes | Independent exact encoding and valid suffix combination |
| Destination/source/width | Derived: er3 destination, A source, word | Exact operand direction and width are not primary-established |
| DD | Live pre-state is DD1; derived `U` accepts both DD states without changing DD; primary 1-21–1-23 distinguishes DD-sensitive accumulator forms | No primary exact-form DD precondition or preservation rule; these three facts are not interchangeable |
| Read/write order | Current executor reads both operands, then writes destination | Exact ordering/alias behavior on the CPU |
| Carry-in | Current ADD ignores CF; ADC is separate | Independent exclusion of carry-in |
| Arithmetic | Current hypothesis: `(er3+A) mod 65536` | Modulo versus saturation/other operation |
| er3 and byte aliases | Primary 2-2 plus user manual 30–31: LRB bank, er3=r6/r7, low byte first; live LRB selects DATA0206/0207 | Whether this opcode writes that word at all, and whether it has other writes |
| Accumulator | Current implementation preserves A in a nonoverlapping bank; bank zero aliases A | Exact post-A effects; A itself is dead after this site |
| CF/ZF | Current implementation sets carry-out and result-zero | Exact flag effects; both are dead before subsequent flag consumption |
| HC | Current implementation preserves incoming HC for this exact form | Not primary-established; tested preservation is explicitly conditional, not a fabricated ISA rule |
| F0 / other PSW bits | Architecture defines them; current implementation preserves them | Exact side effects are unknown; not waived as globally dead |
| LRB / pointing registers / stack | Current implementation preserves them except possible register-bank overlap in generalized contexts | Required addressing/control preservation not independently established |
| Timing | Not consumed by this bounded contract | Not a blocker for the narrow software contract; no cycle claim made |

## Live M2i state and liveness

The exact original and matching listing were checked privately; fresh journals
confirm the pre-state, not just the listing mnemonic. Native initialization
writes er3=0; byte correction input is sign-extended into A, and DD is 1 before
the disputed instruction. The actual LRB is 0040 (bank 0200). This gives a finite
256-value A domain, but does not establish that the instruction computes 0+A.

Under the current control-flow interpretation, the destination is live:
SUB er3,A reads it next, ADD A,er3 later consumes the corrected word, and the
high-byte sign alias affects bounding. A is overwritten by word CLR before
the next load; ZF is overwritten there and by loads. CF/HC are overwritten by
the following SUB before a conditional flag reader. DD is established by CLR,
then the byte load. These dead values do not justify assuming preservation of
LRB, SCB, stack, arbitrary RAM, PC or other architectural state. DP is explicitly
reloaded before its store, but SCB still determines its address. M2i stops
before 1076; no downstream liveness or scheduler claim is added.

## Implementation, probes and new executions

Runner **0.18.0** changes metadata only, not ISA execution/admission. M2i entry
contract v2 separates possible/allowed assumptions, request-accepted permission,
the exact reviewed form and its `DerivedOnly` / `Unestablished` evidence. The
validator rejects hidden permissions, a neighbor form or forged `Allowed`.
Report v2 retains that entry contract alongside actual used assumptions and
local/cumulative conditional status. Old 0.17.0 is not accepted as this new M2i
metadata contract; unaffected operations retain their old compatibility.

Invented Rust probes go through bytes → decoder → executor: 1,296 boundary,
flag, DD and bank combinations; all 256 signed-byte inputs with zero er3;
bank-zero accumulator overlap; DD0/DD1 strict refusal and neighbor isolation.
They separate ADD/ADC, operand direction, byte/word, wrap/saturation, bank and
word footprint. Half-carry boundaries are explored, but their expected flag
result is explicitly the current software hypothesis, not independent ISA
evidence. The strict admission gate remains active even for DD0.

Fresh local runs reuse unchanged M2i original/binding/scenarios and scratch
00/55/AA. Direct A/B: 66 ConditionalMatch; boundary: 12; floor/factor: 12;
clear-gates: 6. Strict-partial: 3 Unresolved and 6 NotRun, stop-before 0FEC,
no completed strict correction. All sequence histories/numbers match old M2i
reports; old reports retain their historical classification. These are
conditional regression / refusal checks, **not** full strict reruns.

## What would distinguish the remaining hypotheses

A verified RAS66K listing for `TYPE(M66201)` and `ADD ER3,A` would distinguish
encoding/length only. A compatible primary suffix map plus operation/flag
rules could establish runtime semantics. A provenance-verified compatible
vendor simulator could independently observe asymmetric operands, incoming
CF toggles, overflow, low-nibble carry, DD toggles, bank overlap and canaries.
The invented probes specify these discriminators; their local outputs do not
become the missing reference observations. No hardware experiment is authorized.

New firmware BIN: **0**. PcInspectionOnly / NotFlashReady; physical RPM and
degrees unavailable. GUI r3 paused/NotRun; D1/D2 interactive acceptance,
hardware and full boot NotRun. M2e/D2 export policies, writable fields, M2h,
portable folders and previous evidence remain unchanged.
