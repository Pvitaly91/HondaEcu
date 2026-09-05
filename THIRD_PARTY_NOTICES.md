# Third-party notices

No license is selected here for HondaEcu as a whole. The following notices apply
to the identified third-party components only; they do not license OEM firmware.

## OKI CPU implementation

Source: [VIRUXE/hondaecu-cli](https://github.com/VIRUXE/hondaecu-cli/tree/85b30752473ca9979e4ad9b307ea05a30c0b3d1e),
exact commit `85b30752473ca9979e4ad9b307ea05a30c0b3d1e`.
Upstream declares `Unlicense`; its complete LICENSE is retained at
`rust/p28-slice-runner/LICENSE.upstream`.

Only `src/cpu.rs`, `src/decoder.rs`, `src/full_decoder.rs`, `src/operand.rs`,
`src/exec.rs` and the bus interface needed by those files were audited for this
import. These six files have no separate copyright/license header and use only
Rust's standard library plus internal modules. Upstream Cargo.toml and Cargo.lock
contain no third-party package dependencies. The local bus is a new bounded,
frozen code/data-space implementation, not upstream's peripheral/engine model.

The imported table is an opcode-description table, not a ROM-derived program.
Upstream's table-coverage comments are not a claim that HondaEcu has validated
every instruction. Unused imports and all upstream embedded test modules were
excluded: in particular, the original decoder contains a firmware fixture test.
No upstream fixtures, corpora, board model, EngineState, telemetry, executables
or file-dependent tests are redistributed. Every local adaptation and semantic
fix is listed in [the M1d record](docs/M1D_BYTECODE_SLICE_VALIDATION.md).

### Opcode-table ancestry

`full_decoder.rs` identifies `66207.op` as its generation source. The related
[asm662 source](https://github.com/VIRUXE/asm662/tree/94612d10370eb4ddf97d4f349168298e1a3da8a0)
at `94612d10370eb4ddf97d4f349168298e1a3da8a0` retains an older BSD statement
and attribution. Its root Unlicense is not treated as erasing that history.
The exact original statement and attribution are preserved below; the checked
files do not supply an expanded BSD variant or copyright year, so neither is
invented here. This is a provenance/notice inventory, not a legal opinion.

From `DASM.txt`, original introduction and author notice:

> Full source is provided under the BSD license.  Feel free to make
> derivative projects.
>
> The code is ANSI C/C++.  The actual opcode disassembler back end is
> generated from perl out of the 66207.op file provided in Doc's
> disassembler, without which this would not be possible.  I corrected a few
> errors in that file, by the way, and perhaps introduced some of my own, but
> the output seems OK so far.
>
> dasm662 was written by Andy Sloane <andy@a1k0n.net>.

## JSON dependencies

The small runner adds only Serde JSON serialization dependencies. Exact versions
and registry checksums are locked in `rust/p28-slice-runner/Cargo.lock`.
The resolved crate manifests and complete distributed license texts were checked
locally. License texts are retained per exact package under the runner's
`third_party` directory (including memchr's COPYING and unicode-ident's additional
Unicode notice):

| Packages | Exact version | Declared license |
|---|---|---|
| serde, serde_derive | 1.0.219 | MIT OR Apache-2.0 |
| serde_json | 1.0.140 | MIT OR Apache-2.0 |
| itoa | 1.0.18 | MIT OR Apache-2.0 |
| memchr | 2.8.3 | Unlicense OR MIT |
| proc-macro2 | 1.0.107 | MIT OR Apache-2.0 |
| quote | 1.0.47 | MIT OR Apache-2.0 |
| ryu | 1.0.23 | Apache-2.0 OR BSL-1.0 |
| syn | 2.0.119 | MIT OR Apache-2.0 |
| unicode-ident | 1.0.24 | (MIT OR Apache-2.0) AND Unicode-3.0 |

These component licenses do not determine the license of HondaEcu's own code.
