# P28 word0196: bounded structured host replay

This research artifact reconstructs only the reviewed software fragment starting
at PC556F and stopping **before** either5596 or55C5. It is not original Honda
source code, a complete MSM66201 emulator, an ECU ABI, firmware-ready source,
physical timing, or a recovered scheduler. No ROM is accepted by the C driver.

## Native-to-IR-to-C provenance

`word0196_ir.json` is deterministic UTF-8 JSON (two-space indentation, LF,
trailing newline), ordered by native PC. Each instruction has its unique pinned
form index, mnemonic, byte length, DD mode, parsed operation, typed operands,
inputs/outputs, flags, effects, branch predicate, successors and primary page.
It contains metadata and typed semantics, **not OEM instruction bytes**.
`validate_ir.py` enforces the closed 18-instruction boundary and mapping to the
named C statement tags. The form index identifies the existing pinned table;
the typed operands/effects, not mnemonic text alone, determine semantics.

Effect records have `op`, `type` and named inputs/destinations. Types are `u8`,
`u16`, `bool` and `pc16`. A location's `widthBits`, `kind`, addressing selector
and required LRB distinguish accumulator low-byte, local registers, current-page
RAM and code-owned immediate. Width is never inferred from a physical field name.
`UnsignedCompare` sets unsigned-borrow CF and equality ZF; `ConditionalJump`
records both explicit successors. RMW effects retain ordered same-value writes.
`AssignCarryFromOldBit` explicitly reads the immutable pre-instruction operand
snapshot, not the already shifted value. Normal effects follow the declared
order: `AssignZeroFlag(value=AL)` reads the newly computed AL, and a memory-RMW
zero flag reads `WriteResult`. This distinction preserves both carry-out and
zero-result semantics without an ambiguous old-versus-new value dependency.

| Native PCs | IR / C statement tag | Reviewed effect |
| --- | --- | --- |
|556F|IR556F|Read018E into AL, DD0/ZF; AH retained|
|5571|IR5571|Byte logical shift AL, CF only|
|5572|IR5572|Byte018E ROL through incoming CF, CF only; ordered RMW|
|5575|IR5575|Load byte r0 at0108, DD0/ZF|
|5576|IR5576|AND AL with018E, ZF only|
|5578|IR5578|Word LE0196 compare immediate00C0, CF/ZF; A unchanged|
|557D|IR557D|CF branch to55BF or557F|
|557F /5582|IR557F /IR5582|0117 to r1 at0109, then0117 AND AL|
|5585 /5588|IR5585/5588|Short-circuit012A.7 then0124.5; either skips to5592|
|558B /558E|IR558B/558E|Only both gates false:018F AND AL, then012A OR1|
|5592 /5594|IR5592/5594|Load018F, then AL ORF0; stop-before5596|
|55BF /55C1 /55C3|IR55BF/55C1/55C3|AL=0F, store0117 then018F; stop-before55C5|

Primary reference is the MSM66201 Instruction Manual, first edition September
1991: byte LB3-70, SLLB A3-144, ROLB object3-120, ANDB3-24/25, word-object CMP
3-38, conditional jump3-66, MOVB rN3-99, JBS3-65, ORB3-107/110, STB3-155.
The rotate-object description accidentally says "word long" despite its 8-bit
heading, 8-bit diagram and byte encoding row; those independent details establish
the scoped byte operation. Little-endian words are specified at1-5; LRB bank/page
at1-10/13/14, DD at1-21..24, SCB as PSW low3 at1-12. C8/JGT is not used or resolved.

## Compact offline state contract

`word0196_state` stores A, full retained PSW, PC, LRB, X1/X2/DP/USP/SSP,
SF/halted, eight local bytes0108..010F, and eight relevant RAM bytes:
0117,0124,0128,012A,018E,018F,0196,0197. Native actual-runtime ownership of these
values is **not established by passing this structure**. The caller supplies a
complete offline snapshot; C does not authorize a native runner input/reseed.

PC must be556F, LRB must be0021 and halted must befalse. Any incoming DD is
allowed because the first LB explicitly clears it before a DD-sensitive form.
No other LRB/alias context is generalized. A byte update masks/truncates explicitly
and preserves AH; no sign extension appears. Word0196 is assembled from low/high
bytes without host-endian/pointer aliases. Named arithmetic flags are CF bit15,
ZF bit14, HC bit13 and DD bit12; all other PSW bits are retained as supplied.
This is retained snapshot storage, not arbitrary PSW reset/canonicalization.

All declared fields not written by a reviewed instruction are retained. Other
RAM, unmodeled aliases/peripherals, cycles and absolute instruction counters are
outside the compact representation. Per-PC steps count only this suffix, not an
unobserved native absolute counter. SF/halted were not serialized in historical
native evidence: retention is tested using invented state, not retrospectively
claimed as a native observation. SCB is transparently derived from PSW&7.

`state`, `context` and `result` must be distinct non-overlapping valid objects;
no arbitrary pointer alias or fake context is a supported replay contract.
Invalid entry/context/halted/ordinal overflow is refused without state mutation.
The maximum path has15 steps,17 RAM accesses and5 writes. P2, timer, IRQ, scheduler
and physical elapsed time do not run. Re-entering556F in a repeated host test is
explicit offline replay, never a newly recovered native schedule.

Each write records PC/address/widthBits/old/new and retains same-value stores.
Its event index and ordinal-base come only from imported **offline annotation**,
never native generation proof. The separate evidence verifier must establish
NativeOwnedInput versus HistoricalHarnessInput/OfflineReplaySnapshot/
IndependentModelValue and ActualRuntimeSourceNotEstablished before comparing
validated historical rows. Host-generated owner/generation IDs are not authority.

## Driver protocol and tests

`word0196_host_driver.c` accepts one whitespace-separated decimal line per row:

```text
id a psw pc lrb x1 x2 dp usp ssp sf halted writeOrdinalBase eventIndex r0 r1 r2 r3 r4 r5 r6 r7 ram0117 ram0124 ram0128 ram012A ram018E ram018F ram0196Lo ram0196Hi
```

Exactly29 numeric fields follow an alphanumeric/underscore/hyphen identifier.
Widths/ranges/column counts are checked; sf/halted are0/1. Output is one JSON
object per row: entry/final, compare, branchTaken,stopPc,steps,accesses,writes.
Access `width` is bits8/16. A step reports after-instruction A/PSW and nextPc;
its incoming state is entry or the previous step. No private row ships in Git.

`word0196_spec_tests.c` independently derives expected outputs from arithmetic,
bit placement and primary rules, not from Rust observations or C# outputs.
It covers every018E byte, all CF/ZF/HC/DD combinations, both bit gates, variedr0,
word edges0000/00BF/00C0/00C1/FFFF, the entire16-bit word domain, every AH,
same-value writes, ordered journals and persistent repeated offline calls.
It verifies all declared retained state, CF/ZF intermediates, path/skip counts
and exact stop boundaries. Negative tests refuse unsupported entry/P2 continuation,
unknown memory context, halted input, ordinal overflow and missing arguments.
Generation/binding forgery refusal is a separate provenance test, not a feature
silently entrusted to C's annotation fields. Invented vectors are not actual ROM.

Host compilers: C11 with strict warnings (GCC/Clang `-std=c11 -Wall -Wextra
-Wpedantic -Werror`; MSVC `/std:c11 /W4 /WX`). Build objects/executables belong
only in ignored temporary paths. Compiler success proves host buildability only;
target toolchain/ABI/layout/interrupts/placement/linker/checksum/flash/hardware
and cycle-equivalent ECU generation remain NotEstablished. FirmwareBIN=0.
