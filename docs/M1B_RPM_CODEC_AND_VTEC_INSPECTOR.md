# M1b - Candidate compact-code model and read-only VTEC inspector

Date: 2026-09-05. Actual base: `origin/codex/p28-304-real-rom-baseline-m1a`,
`b87083c2dd4db7493bf80e9d0ea91723aa389efc`. Working branch:
`codex/p28-rpm-codec-vtec-inspector-m1b`.

This delivers a working read-only research command, a bounded raw-to-compact API,
a separately labelled conditional arithmetic model, and synthetic tests. It does
**not** complete M1, establish a full instruction-validated RPM codec, enable a
public P28 parameter for writing, or establish flash readiness.

## Reused real materials and scope

The existing M1a dossier supplied the exact source/copy/listing/tool paths; no new
baseline or editor search was performed. The same 32768-byte candidate and its
working copy match their recorded hashes. A fresh run of the existing pinned
`dasm662` produced a separate listing identical to M1a's. A private parser checked
all 32768 bytes represented by 11499 instruction records, 930 data records, and
28 vectors, with no byte mismatch or overlap. This is listing/input correspondence,
not proof that every opcode or code/data boundary was decoded correctly.

Tool source remains [asm662 commit 94612d1](https://github.com/VIRUXE/asm662/tree/94612d10370eb4ddf97d4f349168298e1a3da8a0),
with the M1a RCS extraction and installed MSVC build. Invocation still uses a new
private output path and table-discovery bounds `5465 7ff0`, not entrypoints. The
three DD heuristic corrections remain visible at `0x212D`, `0x333A`, `0x3C72`;
none is inside the two inspected slices. No Ghidra or original-BIN execution was
performed. The Ghidra module's shared opcode ancestry is not independent evidence.

Archive continuity does not authenticate an ECU. Native revision and original
provenance remain unresolved as recorded in [M1a findings](M1A_REAL_ROM_FINDINGS.md).
Real hashes, threshold bytes, listings, translated reference source, source/tool
binaries, and integration reports remain ignored and private.

## Formal contract and the unresolved instruction gate

The computation beginning at `0x07C7` and ending with the store at `0x0820` is a
**slice of a larger routine**, not a callable procedure ending in a return.

- `T`: coherent unsigned 16-bit little-endian snapshot at DATA `0x00C4`.
- `S`: Boolean DATA `0x0217.4`, required for the high-raw branch.
- Addressing context: off-page base `0x0200` (`LRB=0x0040`) and `USP=0x0180`.
- The first word load establishes DD=1. Incoming accumulator, carry, zero flag,
  and scratch register contents do not determine the selected outputs; relevant
  values are overwritten. Byte loads later establish DD=0.
- Outputs: byte `Code` at DATA `0x0133` and separate `ExtraBit` at DATA `0x00B8.4`.
  This API does not promise every other clobbered register/flag or runtime effect.
- The snapshot/entry contract excludes asynchronous interference, arbitrary
  computed entry into the middle, and unrelated initialization assignments.

The public `P28CompactModel.Evaluate(T,S)` returns established values only:

| Input | Code | ExtraBit | Resolution |
|---|---:|---|---|
| `0..186` | 255 | true | Established edge path; zero never reaches DIV |
| `187..233` | 254 | true | Established edge path |
| `234..3749` | null | null | **Unresolved instruction semantics**, not a pass |
| `3750..65535`, `S=false` | 1 | false | Established high-raw path |
| `3750..65535`, `S=true` | 0 | false | Established high-raw path |

The specific remaining instruction issue is at `0x07F8`, decoded as word
`ADD er3,A`. The pinned decoder describes that form, but the available
[OKI MSM66201 Instruction Manual](https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/Oki_66201_Instruction_Manual.pdf)
does not establish it: the detailed ADD pages and summary Tables 3-14/3-15 omit
this word form. The byte analogue, numbering gaps, and agreement with a derived
Ghidra opcode table do not fill that gap. Therefore the affected path is explicitly
unresolved even though its **conditional** arithmetic is reproducible.

Manufacturer pages were visually checked for word/byte loads, program/data-space
separation, comparison/borrow, LT/GE/EQ/NE conditions, word division, carry-linked
ROR, logical SRL, immediate word addition, and JRNZ. Key locators include printed
3-39, 3-57, 3-66, 3-68 to 3-72, 3-122, 3-150/151, and 3-156. Actual instruction
bytes and lengths were checked privately against the input. JRNZ decrements the
**low byte** of DP before its nonzero test. A scan typo in the unused GT condition
does not affect the checked LT/GE paths. Instruction confirmation is not board
or peripheral validation.

## Conditional mathematical model, not a guessed RPM formula

`P28CompactModel.EvaluateHypothesis(T,S)` implements a separate, explicitly named
research hypothesis: assume the pinned decoder's word-add interpretation at the
unresolved instruction. Edge paths are as above. On `234 <= T < 3750`, define:

| T interval (inclusive) | j |
|---|---:|
| 1875..3749 | 0 |
| 937..1874 | 1 |
| 468..936 | 2 |
| 234..467 | 3 |

Use unsigned integer division, never floating point:

```text
q = floor((480000 >> j) / T)
c = floor(q / 2) + 64*j - 64
if c >= 255: (Code, ExtraBit) = (254, true)
else if c == 0: (Code, ExtraBit) = (1, false)
else: (Code, ExtraBit) = (c, (q mod 2) != 0)
```

The repeated integer halvings of 1875 yield 937, 468, 234. The dividend is a
32-bit concatenation, division is unsigned 32-by-16, and the quotient fits in a
word on this bounded path. Modular word addition is algebraically represented by
the signed `-64` term; the resulting `c` is 0..256, so no unmodelled wrap is hidden.
The discarded quotient bit is separate, and clamping overrides it. This is a
mathematical implementation, not a published OEM instruction translation.

All 65536 bit patterns have a defined result in the conditional model for each
Boolean `S`; that does not make all patterns normal, physically reachable, or
instruction-validated. The API contains no nearest-value inverse encoder.

## Physical RPM remains unavailable

The upstream producer uses six timer-related sample words and a multiword sum,
followed by a division involving five. The normal loop, early zero-sample exit,
alternate sample-update mode, and context-bit changes are distinct paths; this is
not assumed to be an ordinary six-sample mean. Timer-related acquisition,
`TCON2` initialization and later control-bit changes were traced, but the exact
clock/prescaler, capture source, pulses per revolution, and full update/truncation
relationship are not established for this candidate/board.

An additional initialization path sets DATA `0x00C4` to its maximal word and writes
zero directly to DATA `0x0133`; it is outside the modelled slice. Neither a RAM
snapshot nor a threshold byte may silently be interpreted as a call to F.
No general OBD1 conversion constant was imported. Reports always say
`physicalRpmAvailable: false` and leave RPM intervals null.

## Threshold-state structure

Neutral context numbering follows ascending ROM addresses, **not** selector value:

| Context | DATA `0x011E.3` | Pair | Prior state 0 offset | Prior state 1 offset |
|---|---|---|---|---|
| context_0 | true | pair_0 | `0x6543` | `0x6542` |
| context_0 | true | pair_1 | `0x6545` | `0x6544` |
| context_1 | false | pair_0 | `0x6547` | `0x6546` |
| context_1 | false | pair_1 | `0x6549` | `0x6548` |

Two word program-space reads supply low/even and high/odd bytes. Each pair's own
prior bit selects a byte: set selects low, clear selects high. The unsigned byte
comparison is threshold minus compact code; its borrow becomes the new state.
Thus `newState = compactCode > selectedThreshold`, with **false at equality**.
Pair 0 updates DATA `0x0131.1`; pair 1 updates `.2`.

This update assumes the enabled path (DATA `0x011E.4` set), page base `0x0100`,
and DD=0 at the byte comparisons. The disabled path skips these comparisons; it
is not an implicit re-evaluation with zero. Additional conditions, timers and
software writes to `P1.0`/DATA `0x0127.2` are separate from these state transitions.
The command does not claim physical solenoid activation or label contexts as
low/high load, VTEC ON/OFF, economy/sport, or VTEC-E.

## Inverse sets and command

Every code 0..255 is reported under both compact entry contexts. Inclusive raw
ranges preserve branch boundaries. `exactInputs` means established inputs giving
exactly that code; `predicateInputs` means established inputs making the strict
comparison true. They are different sets. `unresolvedInputs` always exposes
234..3749; absent established preimages produce `reachable: null`, not an invented
unreachable verdict. Separately named `hypothesis*` fields describe the complete
conditional model, including its reachable/unreachable codes. They never become
established merely because models agree.

```shell
hondaecu research p28-vtec inspect private/oracle/p28-304/base.bin --profile p28-304 --confirm-profile --baseline-binding private/reports/m1b/baseline-binding.json --output private/reports/m1b/vtec-inspection.json
hondaecu research p28-vtec inspect private/roms/unknown.bin --profile p28-304 --confirm-profile --output private/reports/m1b/raw-only.json
```

The private binding contains format/model version, selected profile, exact size,
`RomHash` and a SHA-256 digest of the canonical profile serialization. Parsing
rejects missing, unknown, duplicate, malformed or unsupported fields. No embedded
path is followed. This is a small analyst-declared **research binding**, not a
trusted-ECU database, authenticity certificate, or automatic proof of code review.
Do not create one for arbitrary bytes merely to bypass the interpretation gate.
The existing public profile identities and Oracle v2 remain unchanged.

Matched binding **and** explicit acknowledgement permit the scoped interpretation.
Without either, only a warned neutral raw window is emitted. A supplied binding
mismatch writes a raw-only report and returns verification failure; confirmation
cannot override it. A malformed binding or incorrect ROM size is an error.
Reports contain private input hashes/bytes but no timestamps or machine paths;
identical input/options yield deterministic JSON. Output uses the existing atomic
new-path writer; stdout does not print the private hash or threshold block.

## Verification categories and remaining work

Public tests use hand-calculated integer boundaries and invented threshold blocks.
They cover unsigned predicates, all context/prior-state selections, equality,
reverse transitions, literal reversed/equal pairs, unresolved-value refusal,
domain accounting, binding refusal, JSON determinism, size/overwrite checks, and
input immutability. They contain no real ROM or OEM-derived expected-value corpus.

Local .NET 8 verification completed: restore; Release build with zero warnings
and errors; **191 passed tests** (169 Core, 22 CLI), zero failed/skipped; and
`dotnet format --verify-no-changes --no-restore`. The existing Windows/Linux CI
workflow runs only public synthetic tests, not the private integration/reference
corpus. Pre-commit privacy and whitespace checks passed; private evidence and
baseline identities were not added to the public tree.

The private reference is an instruction-oriented translation frozen before the
production implementation. It shares no result-calculation function with the
production model. Exhaustive comparison checks 65536 inputs under each of the two
entry contexts. This is **model agreement**, not original BIN execution or
independent ECU validation; the shared starting interpretation can still be wrong.
The 7032 context/input combinations reaching the unresolved instruction must be
reported separately and never counted as established-path passes.

Actual exhaustive run, with `S=false` and `S=true` each covering 65536 inputs:

| Check | Cases | Matches | Mismatches |
|---|---:|---:|---:|
| Conditional arithmetic agreement (including hypotheses) | 131072 | 131072 | 0 |
| Established-instruction paths only | 124040 | 124040 | 0 |
| Instruction-unresolved paths, **not passed** | 7032 | not applicable | not applicable |

The conditional reference had zero computationally unresolved/invalid inputs;
the production model had zero exceptions, and branch diagnostics agreed. This
does **not** classify operationally invalid/reserved engine states: those remain
unknown. Conditional reachable-code counts were 255 for `S=false` (code zero
unreachable in that hypothesis) and 256 for `S=true`. The established API does not
promote these conditional reachability claims.

Actual private integration used the unchanged real M1a candidate: two bound
inspections and one unbound/raw-only inspection all exited successfully. The two
bound JSON files were byte-identical; all eight threshold slots matched the
actual input bytes; both entry-context domain sets contained all 256 codes with
the unresolved interval disclosed. The original, working copy and public profile
remained unchanged; no public identity or physical RPM was inferred. These are
read-only byte/report checks, not execution of the ROM's machine instructions.

Original-BIN execution, external-editor validation, and hardware checks were
**not run**. Crome/HTS absence did not block raw-byte or threshold-state work. No
editor was searched for, installed, launched, or licensed during M1b. The M1a note
about Crome Pro's applicable terms/permission remains a separate concern; Free and
HTS terms are not considered reviewed by analogy.

The smallest next evidence step is to establish the missing word-add instruction
from a suitable primary specification or separately authorized controlled
instruction experiment, then rerun the frozen comparison and review admission of
the normal path. A later PC-only threshold edit still needs an explicit inverse
selection policy, parent/output binding and patch/diff review. No writable offset,
checksum bypass, ECU write, or automatic promotion is part of this stage.
