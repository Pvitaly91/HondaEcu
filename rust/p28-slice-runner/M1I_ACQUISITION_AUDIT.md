# M1i acquisition runner audit

Runner0.4.0 keeps protocol1 and the13 preceding semantic-fix IDs, appending the
three exact corrections below. Upstream commit, opcode table, dependency set
and pinned Rust toolchain are unchanged. This adds one scoped operation to the
existing executor, not a parallel CPU or general peripheral framework.

## Instruction evidence and regressions

The acquisition registry matches exactly23 opcode-table forms, including DD
requirements; familiar mnemonics do not admit neighboring forms. The exact list
is in `acquisition_form_admission` in `src/instruction_forms.rs`. Its generic ISA
patterns are not a contiguous native program. Runtime code boundaries, SFR
width/permission checks, explicit bank/stack context and the independent C#
checkpoint model additionally constrain the execution result.

Three independently authored decoded-opcode probes failed before their fixes.
The failing observations were retained privately before changing semantics:

| Exact form | Correction / retained behavior | Manufacturer instruction manual |
|---|---|---|
| `SUB A,N8`, word DD1 | HC records low-nibble borrow; CF/ZF retain subtraction semantics; unrelated flags unchanged |3-156; user manual33 for HC|
| `INCB N8` | HC records low-nibble carry; ZF updates; CF, DD and adjacent byte unchanged |3-61|
| `SLLB A`, DD0 | CF updates from outgoing bit; ZF, HC, DD and accumulator high byte are preserved |3-144|

The corresponding appended IDs are:

- `word-sub-direct-updates-half-borrow`
- `byte-inc-direct-updates-half-carry`
- `byte-sll-accumulator-preserves-noncarry-flags`

Additional decoded tests cover every input byte for sign-extending `EXTND`
(3-59), old-bit-to-ZF test-and-set behavior for direct/off-page `SB` (3-127),
and coherent full-LRB er3 / SCB2 X1 aliases (user manual30/34). The registry also
uses the documented load/store, move, clear, branch and MB forms identified in
its comments. DIV, SBCB, ADD, opposite-DD variants and neighboring addressing
or bit forms are not promoted by this new registry. Existing ADD permissions
cannot admit an unresolved acquisition instruction.

## Narrow SFR observation semantics

The manufacturer user manual register-access tables (41–42) and Timer2 capture
and control descriptions (84,90) establish the used widths: TMR2 at003A is one
architectural word read; TCON2 at0042 is a byte; MB reads IRQH byte0019. User
manual164 and166–167 describe IRQ factor setting and reset on interrupt entry
or reset. These ordinary reads do not specify a read-clear/latch-release effect.
The implementation therefore uses stable nondestructive snapshots **only under
the explicit no-new-event/no-interrupt observation scope**. It does not infer
capture races, time progression, IRQ processing or write effects.

Coherent word dispatch occurs before byte splitting, preserving a single16-bit
TMR2 observation. The default bus still rejects non-CPU SFRs. Activation is
internal to acquisition; it is removed before the following G/F/threshold stage.
Wrong widths, neighboring unknown addresses and all peripheral writes fail.
Attempted writes are logged as writes, not applied to the frozen snapshot.

Native sample stores are journaled independently of value differences. A
successful word store is one16-bit event; same-value writes remain visible.
Partial stores retain actual byte events and cannot masquerade as a fresh sample
word. Explicit caller seeding happens before the acquisition journal begins.
Per-slot freshness counts describe acquisition writes, not later producer
alternative-mode overwrites.

## State lifetime and evidence limits

The machine-readable metadata in `src/acquisition.rs` defines bounds and caller
actions. Initial state is applied once per image/scratch sequence. No host
formula rewrites acquired samples or expected T. Each full child sequence uses
the child's own instruction/data bytes and independent CPU/RAM.

The initial-only threshold prefix seeds do not imply a new native scheduler or
hysteresis model. Caller-supplied slot and composition/context schedule remain
test stimulus. A stage failure aborts the remaining sequence with explicit
NotRun entries. Cumulative assumptions cannot become unconditional matches.

Selected witnesses and the first local failure retain bounded instruction
traces. A replay starts with the original initial state and preceding schedule.
Executed-instruction extents are added after admission and before `step`; they
exclude speculative decoder lookahead. They are separate from program-data
reads, allowing bounded read/fetch comparisons without claiming global unused
code or data coverage.

The initial M1i pinned Release suite passed78 tests:39 unit tests,6 acquisition
process/schema tests and33 preceding integration tests. New public sequence
programs intentionally copy a captured word rather than implement native
acquisition; they prove process/state/bus wiring, not the native algorithm.
Actual acquisition/model and original/verified-child evidence is reported
separately in the M1i research document. No GUI window or hardware test is part
of these results.
