# M1f checksum runner audit

Runner 0.3.0 retains protocol version 1 and the ten preceding semantic-fix IDs.
The upstream provenance remains the pinned commit in `protocol.rs`; no new
dependency, engine/peripheral model, general checksum framework, ROM writer,
or checksum-repair operation was introduced.

## Scope and evidence boundary

`checksumBatch` is a fixed seeded instruction-execution task. It executes the
unchanged supplied image, retains the same CPU and RAM between invocations,
and stages only PC back to the audited entry. It does not sum ROM bytes in host
code. The accumulated byte is observed from actual banked r0; the independent
arithmetic model belongs to C#.

The machine-readable entry contract in `src/checksum.rs` is authoritative for
the bounds. It includes SCB0, LRB0041, startup-grounded counter/sum/status zero,
USP0180 and SSP047E, 512 invocations of at most 256 instructions each, and
explicit allowed data and program-data ranges. The stack is not used by any
admitted checksum form. Initialization is a seeded snapshot, not executed reset.
Interrupts and peripherals are not injected. No scheduler or full boot is run.

Ordinary and failure boundaries stop before the next instruction, without
replacing instructions with RET/NOP. A completed pass requires all 512 native
returns, each exact 64-byte ordered contribution-read block, actual block-index
progression/reset, and the actual final decision path. Returning early is not
completion. The nonzero path's extra configuration-byte read is reported as a
control read, not another arithmetic contribution. Neither cleared final sum
RAM nor an ordinary exit alone is treated as a zero-residue result.

Read runs preserve ordered addresses and repetitions. Unique coverage is also
reported separately. A 65-byte per-invocation read-log cap fails explicitly;
overflow is never silently presented as complete coverage. Instruction fetches
are distinct from program-data reads. CPU data aliases pass through the same
scoped data-access check as RAM. Case traces contain at most the first 128
instructions of the final attempted invocation, not a complete execution trace.

## Exact instruction-form admission

The manufacturer instruction manual was visually reviewed during M1f static
analysis. The table below gives printed page locators, not a contiguous firmware
listing. The registry in `src/instruction_forms.rs` matches opcode-table form,
DD kind and mnemonic together. Literal operands, branches and initialization
are additionally checked by the C# native-contract recognizer and the runner's
runtime state/read/boundary contract. A decoded mnemonic by itself is not proof.

| Admitted form(s) | Width / DD / flags | Printed manual page |
|---|---|---|
| CLR X2; CLR N16[X2] | word; DD-independent; no flags | 3-32 |
| MOV er0,N16[X2] | word; DD-independent; no flags | 3-83 |
| CLR A | word; sets DD and ZF | 3-31 |
| LB A,#N8; LB A,r0 | byte; clears DD; updates ZF only | 3-70 |
| MUL | unsigned word product into er1:A; preserves er0/DD; ZF only | 3-100 |
| MOV X1,A | word; DD-independent; no flags | 3-91 |
| MOV DP,#N16 | word; DD-independent; no flags | 3-86 |
| MOVB r0,N16[X2] | byte; DD-independent; no flags | 3-99 |
| LC A,[X1] | word program-data read even with DD0; preserves DD; ZF only | 3-72 |
| ADDB A,N8 | byte; requires DD0; updates CF/ZF/HC, no carry input | 3-16 |
| ADDB r0,A | byte; DD-independent; updates CF/ZF/HC, no carry input | 3-17 |
| INC X1; INC N16[X2] | word; DD-independent; updates ZF/HC, preserves CF | 3-60 |
| JRNZ DP,rel8 | decrements/tests DPL only; preserves DPH and flags | 3-68 |
| STB A,N16[X2] | byte; requires DD0; no flags | 3-155 |
| CMP N'16[X2],#N16 | word; separate displacement/immediate; ZF/CF only | 3-38 |
| JNE rel8; JEQ rel8 | tests ZF; no flags changed | 3-66 / 3-67 |
| CLRB N16[X2] | byte; DD-independent; no flags | 3-34 |
| LCB A,N16 | program byte into AL; preserves AH/DD; ZF only | 3-74 |
| MOVB N'8,#N8 | byte; DD-independent; no flags | 3-96 |
| J addr16 | absolute branch; no flags changed | 3-62 |

There are exactly 24 admitted forms. No word object ADD form is admitted.
`oki.add-er1-a` and `oki.add-er3-a` are both rejected by this task, including
when supplied as unused permissions. Unreviewed forms stop unresolved; unknown
or truncated opcodes, invalid access, unexpected exits and contract violations
remain errors. Budget exhaustion is separate and cannot become a pass.

## Decoded before / after regressions

Five new, independent single-instruction probes were run before any M1f CPU
change. The two byte-add probes and indexed-X2 word-increment probe failed their
HC assertion; their preceding data/CF/ZF assertions passed. MUL and LC-under-DD0
already passed and received no speculative arithmetic fix. The failing outcomes
were recorded privately before applying these three exact semantic corrections:

- `byte-add-direct-accumulator-half-carry`
- `byte-add-r0-accumulator-half-carry`
- `inc-indexed-x2-half-carry`

HC is carry out of bit 3, including for the word increment (manufacturer user
manual printed page 33). The changes are restricted to these reviewed forms;
they do not promote other ADD/INC addressing modes. All initial probes pass
afterward. Additional decoded tests cover byte/word indexed MOV, separate CMP
displacement, CLR/CLRB neighbor preservation, LCB high-byte/DD preservation,
and byte ST. Existing M1d/M1e tests remain in the full suite.

## Public tests versus private native evidence

The public test programs are newly authored toys, not reconstructed native
checksum code or byte fixtures. A 15-byte toy uses the shared re-entry helper
through calls 511 and 512 to prove that CPU/RAM state is not reset per call.
That toy reads one unrelated constant word repeatedly; it does not prove native
coverage or native checksum validity.

`checksumSynthetic` is a bounded custom-program probe using the existing
synthetic contract/result shapes and the checksum form registry. Real subprocess
tests read distinct ROM/RAM values, change only a program-data constant and
observe the changed output, reject a different addressing form, and reject old
ADD assumptions. A separate three-byte early-exit toy sent to `checksumBatch`
fails full-pass checks. Instruction-budget and repeated-read-limit tests also
remain incomplete/error, never valid.

The complete native 512-block result is established separately by private actual
BIN execution and independent C# checkpoint comparison. No private path, BIN
bytes, checksum-routine fixture, or OEM instruction trace is required by these
public tests. A matching checksum establishes this bounded consistency property
only: it does not establish authenticity, safe calibration, ECU/hardware behavior,
or flash readiness, and does not authorize repair or bypass.
