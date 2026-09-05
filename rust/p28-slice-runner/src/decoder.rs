// Adapted from VIRUXE/hondaecu-cli @ 85b30752473ca9979e4ad9b307ea05a30c0b3d1e.
// Third-party terms and local modifications: THIRD_PARTY_NOTICES.md.
// OKI MSM66207 table-driven instruction decoder.
//
// The 66207 encodes the *addressing mode* in the first byte and the *operation*
// in a later byte (e.g. `C5 EB 98 46` is `MOVB 0ebh, #046h`, where C5 selects the
// direct-byte operand and 98 selects MOV-immediate). A flat match on the opcode
// byte therefore cannot decode this ISA -- patterns have to be matched whole.
//
// Patterns come from FULL_OPCODES (full_decoder.rs), generated from the
// tool-described 66207.op table; decoder coverage is not instruction proof.
//
// The DD flag (word/byte mode) is part of the decode context: some encodings are
// shared between a word form and a byte form and are told apart only by DD --
// 0x18 is `ADC A, er0` when DD=1 but `ADCB A, r0` when DD=0. Instructions marked
// 'S'/'R' in the table set/reset DD for the instructions that follow.

use std::sync::OnceLock;

use crate::full_decoder::FULL_OPCODES;

/// Longest encoding in the table, used to bound the fetch window.
pub const MAX_INSN_LEN: usize = 6;

/// Immediate/displacement values captured while matching a pattern.
#[derive(Debug, Clone, Copy, Default)]
pub struct Fields {
    pub n8: u8,
    pub n16: u16,
    pub s8: i8,
    pub rel8: i8,
    pub addr16: u16,
    /// Second immediate, for forms carrying two (`N'8`, `N'16`).
    pub n8_alt: u8,
    pub n16_alt: u16,
}

#[derive(Debug, Clone)]
pub struct Decoded {
    /// Index into FULL_OPCODES.
    pub index: usize,
    pub mnemonic: &'static str,
    pub len: usize,
    pub fields: Fields,
    /// DD after this instruction, when it forces a mode; None leaves it unchanged.
    pub dd_after: Option<bool>,
    /// INT (internal-memory) machine cycles for this encoding, per `int_cycles`.
    /// For conditional branches this is the *not-taken* cost; `exec` adds the
    /// taken penalty at run time.
    pub cycles: u16,
}

/// INT (internal-memory) machine-cycle count for one instruction, from the
/// MSM66201/66207 instruction manual's "Instruction List" cycle tables
/// (chapter 3 §3, the `Int*1 Int*2` column).
///
/// Across every operation class the all-internal-operand cost is **2 cycles per
/// instruction byte** plus a small per-operation adjustment. The large
/// multi-cycle operations (MUL/DIV/RTI/CAL/...) and the ROM-table reads
/// (LC/LCB/CMPC) carry the fixed extras below; a *taken* conditional branch adds
/// four more cycles, which `exec` applies at run time since only it knows the
/// branch was taken. Every value here is checked against the manual for a
/// representative encoding in the unit tests.
///
/// Known residual: the +1/+2 pointer-indirect data-access surcharges the manual
/// lists for `[DP]`/`[erN]` *data* operands are not modelled, so a handful of
/// indirect-addressing instructions run a cycle or two optimistic. This is far
/// below the old flat "two clocks per instruction" error and keeps the model a
/// pure function of the decoded mnemonic.
fn int_cycles(mnemonic: &str, len: usize) -> u16 {
    let base = 2 * len as u16;
    let op = mnemonic
        .split(|c| c == ' ' || c == ',')
        .next()
        .unwrap_or("");
    let extra = match op {
        // Multiply / divide (MSM66201 manual pp. 3-100/3-101, 3-57/3-58).
        "MUL" => 23,
        "MULB" => 15,
        "DIV" => 43,
        "DIVB" => 25,
        // Interrupt / subroutine return and software trap.
        "RTI" => 13,
        "BRK" => 11,
        "RT" => 5,
        "VCAL" => 9,
        // Decimal adjust.
        "DAA" | "DAS" => 4,
        // ROM (code-space) reads: table lookups.
        "LC" | "CMPC" => 7,
        "LCB" | "CMPCB" => 5,
        // Short call / short jump and the stack ops.
        "SCAL" => 5,
        "SJ" => 4,
        "PUSHS" | "PUSHU" => 1,
        "POPS" => 2,
        // Bit set/reset/test forms.
        "SB" | "RB" | "SBR" | "RBR" | "MBR" => 3,
        "TBR" => 1,
        // Decrement-and-branch carries a base surcharge even when not taken.
        "JRNZ" => 3,
        // Call / jump: indirect forms cost more than the absolute form.
        "CAL" => {
            if mnemonic.contains('[') {
                4
            } else {
                3
            }
        }
        "J" => {
            if mnemonic.contains('[') {
                2
            } else {
                1
            }
        }
        // Move-bit: reading a bit into carry is cheap; writing one back is not.
        "MB" => {
            if mnemonic.starts_with("MB C,") {
                1
            } else {
                6
            }
        }
        // Everything else (MOV/L/ST/ADD/ADC/SUB/SBC/CMP/AND/OR/XOR/INC/DEC/
        // shifts/rotates/CLR/XCHG/SWAP/EXTND/NOP/SC/RC/conditional branches ...)
        // is exactly two cycles per byte for internal operands.
        _ => 0,
    };
    base + extra
}

fn hex_byte(tok: &str) -> Option<u8> {
    let b = tok.as_bytes();
    if b.len() == 2 && b.iter().all(|c| c.is_ascii_hexdigit()) {
        u8::from_str_radix(tok, 16).ok()
    } else {
        None
    }
}

/// Number of fixed (non-wildcard) bytes in a pattern -- how specific it is.
fn specificity(pat: &[&str]) -> usize {
    pat.iter().filter(|t| hex_byte(t).is_some()).count()
}

struct Index {
    /// Pattern indices bucketed by leading opcode byte, most specific first.
    by_first: Vec<Vec<u32>>,
}

fn index() -> &'static Index {
    static INDEX: OnceLock<Index> = OnceLock::new();
    INDEX.get_or_init(|| {
        let mut by_first: Vec<Vec<u32>> = vec![Vec::new(); 256];
        for (i, p) in FULL_OPCODES.iter().enumerate() {
            if let Some(first) = p.bytes_pat.first().and_then(|t| hex_byte(t)) {
                by_first[first as usize].push(i as u32);
            }
        }
        // Match the most constrained pattern first so a shorter, less specific
        // encoding can never shadow a longer one that also fits.
        for bucket in by_first.iter_mut() {
            bucket.sort_by(|&a, &b| {
                let (pa, pb) = (&FULL_OPCODES[a as usize], &FULL_OPCODES[b as usize]);
                specificity(pb.bytes_pat)
                    .cmp(&specificity(pa.bytes_pat))
                    .then(pb.bytes_pat.len().cmp(&pa.bytes_pat.len()))
            });
        }
        Index { by_first }
    })
}

/// Decode one instruction. `fetch(i)` supplies the byte at offset `i` from the
/// instruction start. `dd` is the current word/byte mode.
pub fn decode(dd: bool, fetch: impl Fn(usize) -> u8) -> Option<Decoded> {
    let first = fetch(0);
    let idx = index();

    'pattern: for &pi in &idx.by_first[first as usize] {
        let p = &FULL_OPCODES[pi as usize];

        // DD gate: '1' and '0' forms exist only in their respective mode.
        match p.dd_mode {
            '1' if !dd => continue,
            '0' if dd => continue,
            _ => {}
        }

        let mut f = Fields::default();
        for (off, tok) in p.bytes_pat.iter().enumerate() {
            let b = fetch(off);
            if let Some(expect) = hex_byte(tok) {
                if b != expect {
                    continue 'pattern;
                }
                continue;
            }
            match *tok {
                "N8" => f.n8 = b,
                "NL" => f.n16 = (f.n16 & 0xFF00) | b as u16,
                "NH" => f.n16 = (f.n16 & 0x00FF) | ((b as u16) << 8),
                "S8" => f.s8 = b as i8,
                "rel8" => f.rel8 = b as i8,
                "addrl" => f.addr16 = (f.addr16 & 0xFF00) | b as u16,
                "addrh" => f.addr16 = (f.addr16 & 0x00FF) | ((b as u16) << 8),
                "N'8" => f.n8_alt = b,
                "N'L" => f.n16_alt = (f.n16_alt & 0xFF00) | b as u16,
                "N'H" => f.n16_alt = (f.n16_alt & 0x00FF) | ((b as u16) << 8),
                // Reject unfamiliar table tokens instead of widening a match.
                _ => continue 'pattern,
            }
        }

        return Some(Decoded {
            index: pi as usize,
            mnemonic: p.mnemonic,
            len: p.bytes_pat.len(),
            fields: f,
            dd_after: match p.dd_mode {
                'S' => Some(true),
                'R' => Some(false),
                _ => None,
            },
            cycles: int_cycles(p.mnemonic, p.bytes_pat.len()),
        });
    }

    None
}
