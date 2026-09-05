// Adapted from VIRUXE/hondaecu-cli @ 85b30752473ca9979e4ad9b307ea05a30c0b3d1e.
// Third-party terms and local modifications: THIRD_PARTY_NOTICES.md.
// OKI 66207 executor.
//
// Instructions are decoded by `decoder` into a FULL_OPCODES index, and the
// operand text for that index is parsed by `operand` into an Arg tree. This
// module evaluates that tree, so each mnemonic is implemented once regardless
// of how many addressing-mode encodings it has.
//
// Conventions taken from the ISA and confirmed against dasm662's listings:
//   * Word ops act on the full 16-bit accumulator; byte ops (mnemonic ending
//     in B) act on its low half.
//   * CF is set on *borrow* by SUB/SBC/CMP, so the unsigned conditions are
//     JLT = CF, JGE = !CF, JGT = !CF && !ZF, JLE = CF || ZF.
//   * `LC`/`CMPC` read code space; everything else reads data space.

use crate::bus::{AccessFault, Bus};
use crate::cpu::Cpu;
use crate::decoder::{decode, Decoded};
use crate::operand::{table, Arg, Mem, Parsed, Reg};

/// One coherent data-space API for CPU SFR aliases, register-bank operands,
/// instruction memory accesses and caller seeding. No RAM shadow of 0..7 exists.
pub fn read_data_u8(cpu: &Cpu, bus: &mut Bus, address: u16) -> u8 {
    if !bus.check_data_access(address, "read") {
        return 0;
    }
    let value = match address / 2 {
        0 => cpu.ssp,
        1 => cpu.lrb,
        2 => cpu.psw_u16(),
        3 => cpu.a,
        _ => return bus.read_data_u8(address),
    };
    if address & 1 == 0 {
        value as u8
    } else {
        (value >> 8) as u8
    }
}

pub fn read_data_u16(cpu: &Cpu, bus: &mut Bus, address: u16) -> u16 {
    let Some(high) = address.checked_add(1) else {
        bus.record_fault("data", 65536, "read");
        return 0;
    };
    u16::from_le_bytes([
        read_data_u8(cpu, bus, address),
        read_data_u8(cpu, bus, high),
    ])
}

pub fn write_data_u8(cpu: &mut Cpu, bus: &mut Bus, address: u16, value: u8) {
    if !bus.check_data_access(address, "write") {
        return;
    }
    if address > 7 {
        bus.write_data_u8(address, value);
        return;
    }
    let old = read_data_u16(cpu, bus, address & !1);
    let next = if address & 1 == 0 {
        (old & 0xFF00) | value as u16
    } else {
        (old & 0xFF) | ((value as u16) << 8)
    };
    match address / 2 {
        0 => cpu.ssp = next,
        1 => cpu.lrb = next,
        2 => cpu.set_psw_u16(next),
        3 => cpu.a = next,
        _ => unreachable!(),
    }
}

pub fn write_data_u16(cpu: &mut Cpu, bus: &mut Bus, address: u16, value: u16) {
    let Some(high) = address.checked_add(1) else {
        bus.record_fault("data", 65536, "write");
        return;
    };
    let bytes = value.to_le_bytes();
    write_data_u8(cpu, bus, address, bytes[0]);
    write_data_u8(cpu, bus, high, bytes[1]);
}

#[derive(Debug)]
pub enum ExecError {
    MemoryAccess(AccessFault),
    /// No FULL_OPCODES pattern matched the bytes at PC.
    UndefinedOpcode {
        pc: u16,
        byte: u8,
    },
    /// Decoded fine, but this module has no semantics for it yet.
    Unimplemented {
        pc: u16,
        mnemonic: &'static str,
    },
}

impl std::fmt::Display for ExecError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ExecError::MemoryAccess(fault) => write!(f, "{fault}"),
            ExecError::UndefinedOpcode { pc, byte } => {
                write!(f, "undefined opcode {byte:#04X} at {pc:#06X}")
            }
            ExecError::Unimplemented { pc, mnemonic } => {
                write!(f, "unimplemented instruction `{mnemonic}` at {pc:#06X}")
            }
        }
    }
}

pub struct Exec<'a> {
    pub cpu: &'a mut Cpu,
    pub bus: &'a mut Bus,
    d: Decoded,
    /// Set when a *conditional* branch (Jcc / JBS / JBR / JRNZ) actually
    /// transfers control. The manual charges four extra INT cycles for a taken
    /// conditional branch over the not-taken cost stored in `Decoded::cycles`;
    /// `step` reads this to add them.
    branch_taken: bool,
}

impl<'a> Exec<'a> {
    // ---- operand address / value plumbing -------------------------------

    /// X1/X2/DP/USP are not CPU registers: they live in RAM at 0x0080 in the
    /// pointing-register set selected by PSW's SCB field (manual Fig. 1-5).
    fn preg_addr(&self, r: Reg) -> Option<u16> {
        let slot = match r {
            Reg::X1 => 0,
            Reg::X2 => 2,
            Reg::Dp => 4,
            Reg::Usp => 6,
            _ => return None,
        };
        Some(0x0080 + self.cpu.scb() * 8 + slot)
    }

    fn reg(&mut self, r: Reg) -> u16 {
        if let Some(a) = self.preg_addr(r) {
            return self.load(a, false);
        }
        match r {
            Reg::A => self.cpu.a,
            Reg::Ssp => self.cpu.ssp,
            Reg::Lrb => self.cpu.lrb,
            Reg::Psw => self.cpu.psw_u16(),
            Reg::PswL => self.cpu.psw_u16() & 0xFF,
            Reg::PswH => self.cpu.psw_u16() >> 8,
            _ => unreachable!("pointing registers handled above"),
        }
    }

    fn set_reg(&mut self, r: Reg, v: u16) {
        if let Some(a) = self.preg_addr(r) {
            self.store(a, false, v);
            return;
        }
        match r {
            Reg::A => self.cpu.a = v,
            Reg::Ssp => self.cpu.ssp = v,
            Reg::Lrb => self.cpu.lrb = v,
            Reg::Psw => self.cpu.set_psw_u16(v),
            Reg::PswL => {
                let p = self.cpu.psw_u16();
                self.cpu.set_psw_u16((p & 0xFF00) | (v & 0xFF));
            }
            Reg::PswH => {
                let p = self.cpu.psw_u16();
                self.cpu.set_psw_u16((p & 0x00FF) | (v << 8));
            }
            _ => unreachable!("pointing registers handled above"),
        }
    }

    fn load(&mut self, address: u16, byte: bool) -> u16 {
        if byte {
            read_data_u8(self.cpu, self.bus, address) as u16
        } else {
            // Architectural word boundary, not address-space wrapping:
            // effective-address overflow is checked before reaching here.
            // Manual Fig.1-8/Table1-3-1 (1-20); ROM/user-stack are exceptions.
            read_data_u16(self.cpu, self.bus, address & !1)
        }
    }

    fn store(&mut self, address: u16, byte: bool, value: u16) {
        if byte {
            write_data_u8(self.cpu, self.bus, address, value as u8);
        } else {
            write_data_u16(self.cpu, self.bus, address & !1, value);
        }
    }

    fn checked_address(&self, base: u16, offset: i32, space: &'static str) -> u16 {
        let address = base as i32 + offset;
        if !(0..=65535).contains(&address) {
            self.bus
                .record_fault(space, address.max(0) as u32, "address-overflow");
            return 0;
        }
        address as u16
    }

    /// Effective address of a memory operand.
    fn ea(&mut self, m: Mem) -> u16 {
        let f = self.d.fields;
        match m {
            Mem::Direct => f.n8 as u16,
            Mem::DirectAlt => f.n8_alt as u16,
            Mem::OffPage => self.cpu.off_page(f.n8),
            Mem::OffPageAlt => self.cpu.off_page(f.n8_alt),
            Mem::AtReg(r) => self.reg(r),
            Mem::AtEr(n) => {
                let a = self.checked_address(self.cpu.bank_base(), n as i32 * 2, "data");
                self.load(a, false)
            }
            Mem::IdxUsp => {
                let u = self.reg(Reg::Usp);
                self.checked_address(u, f.s8 as i32, "data")
            }
            Mem::IdxReg(r) => {
                let value = self.reg(r);
                self.checked_address(value, f.n16 as i32, "data")
            }
            Mem::IdxRegAlt(r) => {
                let value = self.reg(r);
                self.checked_address(value, f.n16_alt as i32, "data")
            }
            Mem::IdxMemN8 => {
                let base = self.load(f.n8 as u16, false);
                self.checked_address(base, f.n16 as i32, "data")
            }
            Mem::IdxMemOff => {
                let a = self.cpu.off_page(f.n8);
                let base = self.load(a, false);
                self.checked_address(base, f.n16 as i32, "data")
            }
            Mem::Abs16 => f.n16,
        }
    }

    /// Read an operand as a value. `code` selects code space for LC/CMPC.
    fn read(&mut self, a: &Arg, byte: bool, code: bool) -> u16 {
        let f = self.d.fields;
        match a {
            Arg::Reg(Reg::A) if byte => self.cpu.a & 0xFF,
            Arg::Reg(r) => self.reg(*r),
            Arg::Er(n) => {
                let addr = self.checked_address(self.cpu.bank_base(), *n as i32 * 2, "data");
                self.load(addr, false)
            }
            Arg::R(n) => {
                let addr = self.checked_address(self.cpu.bank_base(), *n as i32, "data");
                self.load(addr, true) as u8 as u16
            }
            Arg::Carry => self.cpu.cf as u16,
            Arg::ImmN8 => f.n8 as u16,
            Arg::ImmN16 => f.n16,
            Arg::ImmN8Alt => f.n8_alt as u16,
            Arg::ImmN16Alt => f.n16_alt,
            Arg::Mem(m) => {
                let addr = self.ea(*m);
                match (byte, code) {
                    (true, true) => self.bus.read_code_u8(addr) as u16,
                    (false, true) => self.bus.read_code_u16(addr),
                    (b, false) => self.load(addr, b),
                }
            }
            // Bit operands select one byte regardless of DD or mnemonic suffix
            // (MB obj.bit,C, manual printed 3-78).
            Arg::Bit(inner, n) => (self.read(inner, true, code) >> n) & 1,
            Arg::Addr16 => f.addr16,
            Arg::Rel8 => f.rel8 as u16,
            Arg::Lit(n) => *n as u16,
        }
    }

    fn write(&mut self, a: &Arg, byte: bool, v: u16) {
        match a {
            Arg::Reg(Reg::A) if byte => self.cpu.a = (self.cpu.a & 0xFF00) | (v & 0xFF),
            Arg::Reg(r) => self.set_reg(*r, v),
            Arg::Er(n) => {
                let addr = self.checked_address(self.cpu.bank_base(), *n as i32 * 2, "data");
                self.store(addr, false, v);
            }
            Arg::R(n) => {
                let addr = self.checked_address(self.cpu.bank_base(), *n as i32, "data");
                self.store(addr, true, v as u8 as u16);
            }
            Arg::Carry => self.cpu.cf = v & 1 != 0,
            Arg::Mem(m) => {
                let addr = self.ea(*m);
                self.store(addr, byte, v);
            }
            Arg::Bit(inner, n) => {
                let cur = self.read(inner, true, false);
                let next = if v & 1 != 0 {
                    cur | (1 << n)
                } else {
                    cur & !(1 << n)
                };
                self.write(inner, true, next);
            }
            // Immediates and branch targets are never write destinations.
            _ => {}
        }
    }

    // ---- flag helpers ----------------------------------------------------

    fn set_zf(&mut self, v: u16, byte: bool) {
        self.cpu.zf = if byte { v & 0xFF == 0 } else { v == 0 };
    }

    fn mask(v: u16, byte: bool) -> u16 {
        if byte {
            v & 0xFF
        } else {
            v
        }
    }

    // ---- stack -----------------------------------------------------------

    fn push_sys(&mut self, v: u16) {
        let a = self.cpu.ssp;
        self.store(a, false, v);
        self.cpu.ssp = self.checked_address(self.cpu.ssp, -2, "data");
    }

    fn pop_sys(&mut self) -> u16 {
        self.cpu.ssp = self.checked_address(self.cpu.ssp, 2, "data");
        self.load(self.cpu.ssp, false)
    }

    // ---- main dispatch ---------------------------------------------------

    fn run(&mut self, p: &Parsed) -> Result<(), ExecError> {
        let byte = p.byte_width;
        let args = &p.args;
        // Base name with any byte-width suffix removed, so ADD/ADDB share an arm.
        let base = if byte { &p.op[..p.op.len() - 1] } else { p.op };

        match base {
            "NOP" => {}

            // ---- data movement -------------------------------------------
            // L/LB load the accumulator; ST/STB store it; MOV/MOVB are general.
            "L" | "MOV" => {
                let v = self.read(&args[1], byte, false);
                self.write(&args[0], byte, v);
                // L/LB set ZF; MOV does not (manual printed 3-69/3-70).
                if base == "L" {
                    self.set_zf(v, byte);
                }
            }
            "ST" => {
                let v = self.read(&args[0], byte, false);
                self.write(&args[1], byte, v);
            }
            // Load from code (ROM) space -- table lookups.
            "LC" => {
                let v = self.read(&args[1], byte, true);
                self.write(&args[0], byte, v);
                // LC changes ZF but not DD (manual printed 3-72).
                self.set_zf(v, byte);
            }
            "XCHG" => {
                let x = self.read(&args[0], byte, false);
                let y = self.read(&args[1], byte, false);
                self.write(&args[0], byte, y);
                self.write(&args[1], byte, x);
            }
            "CLR" => {
                self.write(&args[0], byte, 0);
                // CLR A F9 is equivalent to L A,#0, unlike CLR obj.
                // Manual printed 3-31: ZF=1; decoder establishes DD=1.
                if !byte && args[0] == Arg::Reg(Reg::A) {
                    self.cpu.zf = true;
                }
            }

            // ---- arithmetic / logic --------------------------------------
            "ADD" | "ADC" | "SUB" | "SBC" | "CMP" | "CMPC" => {
                // CMP/CMPC discard the result and only set flags. CMPC's source
                // is code space.
                let code = base == "CMPC";
                let lhs = self.read(&args[0], byte, false);
                let rhs = self.read(&args[1], byte, code);
                let carry_in = match base {
                    "ADC" | "SBC" => self.cpu.cf as u32,
                    _ => 0,
                };
                let (a, b) = (lhs as u32, rhs as u32);
                let width_mask: u32 = if byte { 0xFF } else { 0xFFFF };
                let (res, carry) = match base {
                    "ADD" | "ADC" => {
                        let r = (a & width_mask) + (b & width_mask) + carry_in;
                        (r & width_mask, r > width_mask)
                    }
                    _ => {
                        let r = (a & width_mask)
                            .wrapping_sub(b & width_mask)
                            .wrapping_sub(carry_in);
                        (
                            (r & width_mask),
                            (a & width_mask) < (b & width_mask) + carry_in,
                        )
                    }
                };
                self.cpu.cf = carry;
                self.set_zf(res as u16, byte);
                // Narrow newly audited producer form: ADCB r0,#N8.
                // Manual 3-12 and user manual 33: half carry is bit3 carry.
                if base == "ADC" && byte && args[0] == Arg::R(0) && args[1] == Arg::ImmN8 {
                    self.cpu.hc = (a & 15) + (b & 15) + carry_in > 15;
                }
                // M1f exact byte forms, manual printed 3-16/3-17:
                // ADDB A,N8 (C5 N8 82), ADDB r0,A (20 81). No carry-in.
                if base == "ADD"
                    && byte
                    && ((args[0] == Arg::Reg(Reg::A) && args[1] == Arg::Mem(Mem::Direct))
                        || (args[0] == Arg::R(0) && args[1] == Arg::Reg(Reg::A)))
                {
                    self.cpu.hc = (a & 15) + (b & 15) > 15;
                }
                if !matches!(base, "CMP" | "CMPC") {
                    self.write(&args[0], byte, res as u16);
                }
            }
            "AND" | "OR" | "XOR" => {
                let lhs = self.read(&args[0], byte, false);
                let rhs = self.read(&args[1], byte, false);
                let res = match base {
                    "AND" => lhs & rhs,
                    "OR" => lhs | rhs,
                    _ => lhs ^ rhs,
                };
                let res = Self::mask(res, byte);
                self.set_zf(res, byte);
                self.write(&args[0], byte, res);
            }
            "INC" | "DEC" => {
                let v = self.read(&args[0], byte, false);
                let res = if base == "INC" {
                    v.wrapping_add(1)
                } else {
                    v.wrapping_sub(1)
                };
                let res = Self::mask(res, byte);
                self.set_zf(res, byte);
                // INC X1 (70), manual 3-60: CF/DD unchanged, ZF/HC updated.
                if base == "INC"
                    && !byte
                    && (args[0] == Arg::Reg(Reg::X1) || args[0] == Arg::Mem(Mem::IdxReg(Reg::X2)))
                {
                    self.cpu.hc = v & 15 == 15;
                }
                self.write(&args[0], byte, res);
            }
            "MUL" => {
                // MUL/MULB have no source operands in their mnemonics. The
                // operands and destinations are fixed by the ISA:
                //
                //   MUL   (er1, A) <- A * er0
                //   MULB  A        <- AL * r0
                //
                // See the MSM66201 Instruction Manual, chapter 3, pp. 3-100
                // and 3-101. Treating these as ordinary two-operand
                // instructions used to index an empty argument list as soon
                // as the OEM ROM reached its first fuel calculation.
                if byte {
                    let product = self
                        .read(&Arg::Reg(Reg::A), true, false)
                        .wrapping_mul(self.read(&Arg::R(0), true, false));
                    self.cpu.a = product;
                    self.set_zf(product, false);
                } else {
                    let product =
                        (self.cpu.a as u32)
                            .wrapping_mul(self.read(&Arg::Er(0), false, false) as u32);
                    self.cpu.a = product as u16;
                    self.write(&Arg::Er(1), false, (product >> 16) as u16);
                    self.cpu.zf = product == 0;
                }
            }
            "DIV" => {
                // DIV/DIVB likewise use fixed registers:
                //
                //   DIV   (er0, A) <- (er0, A) / er2; er1 <- remainder
                //   DIVB  A        <- A / r0;         r1  <- remainder
                //
                // Divide-by-zero results are undefined on the chip; only CF=1
                // is specified. Preserve the operands in that case.
                if byte {
                    let divisor = self.read(&Arg::R(0), true, false);
                    if divisor == 0 {
                        self.cpu.cf = true;
                    } else {
                        let dividend = self.cpu.a;
                        let quotient = dividend / divisor;
                        let remainder = dividend % divisor;
                        self.cpu.a = quotient;
                        self.write(&Arg::R(1), true, remainder);
                        self.cpu.cf = false;
                        self.set_zf(quotient, false);
                    }
                } else {
                    let divisor = self.read(&Arg::Er(2), false, false) as u32;
                    if divisor == 0 {
                        self.cpu.cf = true;
                    } else {
                        let dividend = ((self.read(&Arg::Er(0), false, false) as u32) << 16)
                            | self.cpu.a as u32;
                        let quotient = dividend / divisor;
                        let remainder = dividend % divisor;
                        self.write(&Arg::Er(0), false, (quotient >> 16) as u16);
                        self.cpu.a = quotient as u16;
                        self.write(&Arg::Er(1), false, remainder as u16);
                        self.cpu.cf = false;
                        self.cpu.zf = quotient == 0;
                    }
                }
            }
            "EXTND" => {
                // Sign-extend the low byte across the accumulator.
                let lo = (self.cpu.a & 0xFF) as u8;
                self.cpu.a = lo as i8 as i16 as u16;
            }
            // SWAP/SWAPB take no operand: they act on the accumulator,
            // exchanging its two bytes (word) or its two nibbles (byte).
            "SWAP" => {
                let a = self.cpu.a;
                self.cpu.a = if byte {
                    (a & 0xFF00) | ((a & 0x0F) << 4) | ((a >> 4) & 0x0F)
                } else {
                    a.rotate_right(8)
                };
            }

            // ---- shifts and rotates --------------------------------------
            "ROL" | "ROR" | "SLL" | "SRL" | "SRA" => {
                let v = self.read(&args[0], byte, false);
                let bits = if byte { 8 } else { 16 };
                let msb = 1u32 << (bits - 1);
                let v32 = v as u32 & (msb * 2 - 1);
                let (res, carry) = match base {
                    "ROL" => (
                        ((v32 << 1) | (v32 >> (bits - 1))) & (msb * 2 - 1),
                        v32 & msb != 0,
                    ),
                    "ROR" => ((v32 >> 1) | if self.cpu.cf { msb } else { 0 }, v32 & 1 != 0),
                    "SLL" => ((v32 << 1) & (msb * 2 - 1), v32 & msb != 0),
                    "SRL" => (v32 >> 1, v32 & 1 != 0),
                    // Arithmetic right shift keeps the sign bit.
                    _ => ((v32 >> 1) | (v32 & msb), v32 & 1 != 0),
                };
                self.cpu.cf = carry;
                // Reviewed word ROR and SRL forms change only CF (manual
                // printed 3-122, 3-150 and 3-151).
                if !matches!(base, "ROR" | "SRL") {
                    self.set_zf(res as u16, byte);
                }
                self.write(&args[0], byte, res as u16);
            }

            // ---- carry and bit operations --------------------------------
            "SC" => self.cpu.cf = true,
            "RC" => self.cpu.cf = false,
            // Bit set/reset are test-and-modify. ZF follows the normal zero
            // convention: it is one when the bit's previous value was zero.
            // MSM66201 Instruction Manual pp. 3-114, 3-115 and 3-127.
            "SB" | "RB" => {
                let old = self.read(&args[0], byte, false) & 1;
                self.cpu.zf = old == 0;
                self.write(&args[0], byte, (base == "SB") as u16);
            }
            // MB moves a bit; whichever side is C decides the direction. It
            // does not affect ZF (manual pp. 3-77 and 3-78).
            "MB" => {
                if args[0] == Arg::Carry {
                    let v = self.read(&args[1], byte, false) & 1;
                    self.cpu.cf = v != 0;
                } else {
                    let v = self.cpu.cf as u16;
                    self.write(&args[0], byte, v);
                }
            }
            // Same move, with the bit selected indirectly by A[0:2]. MBR also
            // leaves ZF unchanged (manual pp. 3-79 and 3-80).
            "MBR" => {
                let mask = 1u16 << (self.cpu.a & 0x07);
                if args[0] == Arg::Carry {
                    let v = self.read(&args[1], true, false);
                    let b = (v & mask != 0) as u16;
                    self.cpu.cf = b != 0;
                } else {
                    let b = self.cpu.cf as u16;
                    let v = self.read(&args[0], true, false);
                    let next = if b != 0 { v | mask } else { v & !mask };
                    self.write(&args[0], true, next);
                }
            }
            // "Register Indirect Bit Addressing": these carry no bit index in
            // the encoding; the manual (ch.2 sec.3) specifies the bit location
            // as "the bits from 0 to 2 of the accumulator".
            "SBR" | "RBR" | "TBR" => {
                let mask = 1u16 << (self.cpu.a & 0x07);
                let v = self.read(&args[0], true, false);
                self.cpu.zf = v & mask == 0;
                match base {
                    "SBR" => self.write(&args[0], true, v | mask),
                    "RBR" => self.write(&args[0], true, v & !mask),
                    // TBR tests only.
                    _ => {}
                }
            }

            // ---- stack ---------------------------------------------------
            "PUSHS" => {
                let v = self.read(&args[0], byte, false);
                self.push_sys(v);
            }
            "POPS" => {
                let v = self.pop_sys();
                self.write(&args[0], byte, v);
            }
            "PUSHU" => {
                let v = self.read(&args[0], byte, false);
                let old = self.reg(Reg::Usp);
                let u = self.checked_address(old, -2, "data");
                self.set_reg(Reg::Usp, u);
                // User-stack accesses do not word-align (manual 1-20).
                write_data_u16(self.cpu, self.bus, u, v);
            }

            // ---- control flow --------------------------------------------
            "J" => {
                // `J addr16` is absolute; `J [reg]` takes the operand's value.
                self.cpu.pc = self.read(&args[0], false, false);
            }
            "SJ" => {
                let off = self.d.fields.rel8 as i16;
                self.cpu.pc = self.checked_address(self.cpu.pc, off as i32, "code");
            }
            "CAL" => {
                let target = self.read(&args[0], false, false);
                let ret = self.cpu.pc;
                self.push_sys(ret);
                self.cpu.pc = target;
            }
            "SCAL" => {
                let off = self.d.fields.rel8 as i16;
                let ret = self.cpu.pc;
                self.push_sys(ret);
                self.cpu.pc = self.checked_address(self.cpu.pc, off as i32, "code");
            }
            "VCAL" => {
                // Vector call through the table at 0x0028.
                let n = self.read(&args[0], false, false);
                let ret = self.cpu.pc;
                self.push_sys(ret);
                self.cpu.pc = self.bus.read_code_u16(0x0028 + n * 2);
            }
            "RT" => self.cpu.pc = self.pop_sys(),
            "RTI" => {
                // MSM66201 instruction manual, RTI (3-126): hardware restores
                // PSW, LRB, A and PC in that order and advances SSP by eight.
                let psw = self.pop_sys();
                let lrb = self.pop_sys();
                let a = self.pop_sys();
                let pc = self.pop_sys();
                self.cpu.set_psw_u16(psw);
                self.cpu.lrb = lrb;
                self.cpu.a = a;
                self.cpu.pc = pc;
            }
            "JEQ" | "JNE" | "JLT" | "JGE" | "JGT" | "JLE" => {
                let (z, c) = (self.cpu.zf, self.cpu.cf);
                let take = match base {
                    "JEQ" => z,
                    "JNE" => !z,
                    "JLT" => c,
                    "JGE" => !c,
                    "JGT" => !c && !z,
                    _ => c || z,
                };
                if take {
                    let off = self.d.fields.rel8 as i16;
                    self.cpu.pc = self.checked_address(self.cpu.pc, off as i32, "code");
                    self.branch_taken = true;
                }
            }
            "JBS" | "JBR" => {
                let bit = self.read(&args[0], byte, false) & 1;
                let take = if base == "JBS" { bit == 1 } else { bit == 0 };
                if take {
                    let off = self.d.fields.rel8 as i16;
                    self.cpu.pc = self.checked_address(self.cpu.pc, off as i32, "code");
                    self.branch_taken = true;
                }
            }
            "JRNZ" => {
                // JRNZ DP decrements/tests DPL only; DPH and every flag remain
                // intact. Manual printed 3-68, opcode 30 rel8.
                let old = self.read(&args[0], false, false);
                let low = (old as u8).wrapping_sub(1);
                self.write(&args[0], false, (old & 0xFF00) | low as u16);
                if low != 0 {
                    let off = self.d.fields.rel8 as i16;
                    self.cpu.pc = self.checked_address(self.cpu.pc, off as i32, "code");
                    self.branch_taken = true;
                }
            }
            "BRK" => {
                let ret = self.cpu.pc;
                let psw = self.cpu.psw_u16();
                self.push_sys(psw);
                self.push_sys(ret);
                self.cpu.pc = self.bus.read_code_u16(0x0002);
            }

            // ---- misc ----------------------------------------------------
            "DAA" | "DAS" => {
                // Decimal adjust after add/subtract, on the low byte.
                let mut v = (self.cpu.a & 0xFF) as u16;
                let adjust = if (v & 0x0F) > 9 || self.cpu.hc { 6 } else { 0 };
                v = if base == "DAA" {
                    v.wrapping_add(adjust)
                } else {
                    v.wrapping_sub(adjust)
                };
                let adjust_hi = if (v >> 4) > 9 || self.cpu.cf { 0x60 } else { 0 };
                v = if base == "DAA" {
                    v.wrapping_add(adjust_hi)
                } else {
                    v.wrapping_sub(adjust_hi)
                };
                self.cpu.cf = v > 0xFF;
                self.cpu.a = (self.cpu.a & 0xFF00) | (v & 0xFF);
                self.set_zf(v, true);
            }
            "XNBL" => {
                // Exchange the nibbles of the accumulator low byte with memory.
                let m = self.read(&args[0], true, false);
                let a = self.cpu.a & 0xFF;
                self.write(&args[0], true, (m & 0xF0) | (a & 0x0F));
                self.cpu.a = (self.cpu.a & 0xFF00) | ((a & 0xF0) | (m & 0x0F));
            }
            "SMOVI" => {
                // Block move [DP] -> [X1], post-incrementing both.
                let (src, dst) = (self.reg(Reg::Dp), self.reg(Reg::X1));
                let v = self.load(src, true) as u8;
                self.store(dst, true, v as u16);
                let next_src = self.checked_address(src, 1, "data");
                let next_dst = self.checked_address(dst, 1, "data");
                self.set_reg(Reg::Dp, next_src);
                self.set_reg(Reg::X1, next_dst);
            }

            _ => {
                return Err(ExecError::Unimplemented {
                    pc: self.cpu.pc,
                    mnemonic: self.d.mnemonic,
                });
            }
        }
        Ok(())
    }
}

/// Fetch, decode and execute one instruction at PC.
pub fn step(cpu: &mut Cpu, bus: &mut Bus) -> Result<Decoded, ExecError> {
    let pc = cpu.pc;
    if let Some(fault) = bus.take_fault() {
        return Err(ExecError::MemoryAccess(fault));
    }
    let d = match decode(cpu.dd, |i| bus.peek_code_u8(pc as usize + i).unwrap_or(0)) {
        Some(d) => d,
        None => {
            return Err(ExecError::UndefinedOpcode {
                pc,
                byte: bus.fetch_code_u8(pc),
            });
        }
    };

    if pc as usize + d.len > bus.rom_len() || pc as usize + d.len > 65535 {
        return Err(ExecError::MemoryAccess(AccessFault {
            space: "code",
            address: pc as u32 + d.len as u32 - 1,
            operation: "fetch",
        }));
    }
    if let Some(fault) = bus.take_fault() {
        return Err(ExecError::MemoryAccess(fault));
    }

    // PC advances past the instruction before execution, so rel8 targets and
    // pushed return addresses are relative to the *next* instruction.
    cpu.pc = pc + d.len as u16;
    // Retain upstream instruction-cost statistics only. They do not advance
    // peripherals or elapsed time and are not a measured hardware clock model.
    cpu.cycles += d.cycles as u64;
    cpu.instructions += 1;

    let parsed = match &table()[d.index] {
        Some(p) => p,
        None => {
            return Err(ExecError::Unimplemented {
                pc,
                mnemonic: d.mnemonic,
            });
        }
    };

    let dd_after = d.dd_after;
    let mut ex = Exec {
        cpu,
        bus,
        d: d.clone(),
        branch_taken: false,
    };
    ex.run(parsed)?;
    if let Some(fault) = ex.bus.take_fault() {
        return Err(ExecError::MemoryAccess(fault));
    }
    // Read the flag before touching `cpu` again so the reborrow held by `ex`
    // ends cleanly.
    let branch_taken = ex.branch_taken;

    // L/LB-class instructions leave the word/byte mode set for what follows.
    if let Some(v) = dd_after {
        cpu.dd = v;
    }
    // A taken conditional branch costs four cycles more than the fall-through.
    if branch_taken {
        cpu.cycles += 4;
    }
    Ok(d)
}

#[cfg(test)]
mod producer_form_tests {
    use super::*;

    fn machine(bytes: &[u8]) -> (Cpu, Bus) {
        let mut cpu = Cpu::new();
        cpu.set_psw_u16(0x0331);
        cpu.lrb = 0x43;
        (cpu, Bus::new(bytes.to_vec(), 0xA5))
    }

    #[test]
    fn clr_accumulator_sets_zero_and_word_descriptor_only() {
        let (mut cpu, mut bus) = machine(&[0xF9]);
        cpu.a = 0xFFFF;
        cpu.cf = true;
        cpu.hc = true;
        let before = cpu.psw_u16() & !(Cpu::PSW_ZF_BIT | Cpu::PSW_DD_BIT);
        assert_eq!(step(&mut cpu, &mut bus).unwrap().mnemonic, "CLR A");
        assert_eq!(cpu.a, 0);
        assert!(cpu.zf);
        assert!(cpu.dd);
        assert_eq!(cpu.psw_u16() & !(Cpu::PSW_ZF_BIT | Cpu::PSW_DD_BIT), before);
    }

    #[test]
    fn jrnz_decrements_only_dpl_and_branches_on_only_dpl() {
        for (initial, expected, pc) in [
            (0x1201, 0x1200, 2),
            (0x1200, 0x12FF, 4),
            (0xFFFF, 0xFFFE, 4),
        ] {
            let (mut cpu, mut bus) = machine(&[0x30, 2, 0, 0, 0]);
            cpu.set_psw_u16(0xF331);
            write_data_u16(&mut cpu, &mut bus, 0x8C, initial);
            let before = cpu.psw_u16();
            assert_eq!(step(&mut cpu, &mut bus).unwrap().mnemonic, "JRNZ DP, rel8");
            assert_eq!(read_data_u16(&cpu, &mut bus, 0x8C), expected);
            assert_eq!(cpu.pc, pc);
            assert_eq!(cpu.psw_u16(), before);
        }
    }

    #[test]
    fn adcb_r0_immediate_has_byte_carry_halfcarry_and_preserves_banked_neighbor() {
        for dd in [false, true] {
            for initial in 0..=u8::MAX {
                for immediate in [0, 1, 7, 15, 255] {
                    for carry in [false, true] {
                        let (mut cpu, mut bus) = machine(&[0x20, 0x90, immediate]);
                        cpu.dd = dd;
                        cpu.cf = carry;
                        cpu.hc = false;
                        write_data_u8(&mut cpu, &mut bus, 0x218, initial);
                        let before =
                            cpu.psw_u16() & !(Cpu::PSW_CF_BIT | Cpu::PSW_ZF_BIT | Cpu::PSW_HC_BIT);
                        let decoded = step(&mut cpu, &mut bus).unwrap();
                        let expected = initial as u16 + immediate as u16 + u16::from(carry);
                        assert_eq!(decoded.mnemonic, "ADCB r0, #N8");
                        assert_eq!(read_data_u8(&cpu, &mut bus, 0x218), expected as u8);
                        assert_eq!(read_data_u8(&cpu, &mut bus, 0x219), 0xA5);
                        assert_eq!(cpu.cf, expected > 255);
                        assert_eq!(cpu.zf, expected % 256 == 0);
                        assert_eq!(
                            cpu.hc,
                            (initial & 15) as u16 + (immediate & 15) as u16 + u16::from(carry) > 15
                        );
                        assert_eq!(
                            cpu.psw_u16() & !(Cpu::PSW_CF_BIT | Cpu::PSW_ZF_BIT | Cpu::PSW_HC_BIT),
                            before
                        );
                    }
                }
            }
        }
    }

    #[test]
    fn inc_x1_word_updates_zero_halfcarry_but_not_carry_or_dd() {
        for value in [0x000F, 0x00FF, 0xFFFF, 0x8000] {
            let (mut cpu, mut bus) = machine(&[0x70]);
            cpu.cf = true;
            cpu.hc = false;
            cpu.dd = true;
            write_data_u16(&mut cpu, &mut bus, 0x88, value);
            let before = cpu.psw_u16() & !(Cpu::PSW_ZF_BIT | Cpu::PSW_HC_BIT);
            assert_eq!(step(&mut cpu, &mut bus).unwrap().mnemonic, "INC X1");
            assert_eq!(read_data_u16(&cpu, &mut bus, 0x88), value.wrapping_add(1));
            assert_eq!(cpu.zf, value == 0xFFFF);
            assert_eq!(cpu.hc, value & 15 == 15);
            assert_eq!(cpu.psw_u16() & !(Cpu::PSW_ZF_BIT | Cpu::PSW_HC_BIT), before);
        }
    }

    #[test]
    fn indexed_immediate_move_keeps_displacement_separate_from_value() {
        let (mut cpu, mut bus) = machine(&[0xB0, 0x00, 0x03, 0x98, 0x34, 0x12]);
        write_data_u16(&mut cpu, &mut bus, 0x88, 2);
        let before = cpu.psw_u16();
        assert_eq!(
            step(&mut cpu, &mut bus).unwrap().mnemonic,
            "MOV N'16[X1], #N16"
        );
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x302), 0x1234);
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x300), 0xA5A5);
        assert_eq!(cpu.psw_u16(), before);
    }

    #[test]
    fn indexed_word_load_uses_documented_word_boundary_not_adjacent_bytes() {
        let (mut cpu, mut bus) = machine(&[0xE0, 0x01, 0x03]);
        write_data_u16(&mut cpu, &mut bus, 0x88, 2);
        write_data_u16(&mut cpu, &mut bus, 0x302, 0x1234);
        write_data_u8(&mut cpu, &mut bus, 0x304, 0xAB);
        assert_eq!(step(&mut cpu, &mut bus).unwrap().mnemonic, "L A, N16[X1]");
        assert_eq!(cpu.a, 0x1234);
    }

    #[test]
    fn word_alignment_does_not_align_raw_seeding_byte_operands_or_rom_reads() {
        let (mut cpu, mut bus) = machine(&[0xB0, 0x01, 0x03, 0x98, 0x34, 0x12]);
        write_data_u16(&mut cpu, &mut bus, 0x88, 2);
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x302), 0x1234);
        assert_eq!(read_data_u8(&cpu, &mut bus, 0x304), 0xA5);
        // The raw snapshot API deliberately addresses consecutive bytes.
        write_data_u16(&mut cpu, &mut bus, 0x303, 0xFEDC);
        assert_eq!(read_data_u8(&cpu, &mut bus, 0x303), 0xDC);
        assert_eq!(read_data_u8(&cpu, &mut bus, 0x304), 0xFE);
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x303), 0xFEDC);
        // LC is ROM addressing, explicitly excluded from word alignment.
        let (mut cpu, mut bus) = machine(&[0x92, 0xA8, 0xAA, 0x34, 0x12]);
        write_data_u16(&mut cpu, &mut bus, 0x8C, 3);
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(cpu.a, 0x1234);
        assert_eq!(bus.program_reads(), vec![3, 4]);
    }

    #[test]
    fn conditional_add_er1_then_adcb_r0_accumulates_multiple_word_carries() {
        // This test is CONDITIONAL on oki.add-er1-a. It checks the implemented
        // software hypothesis, not primary evidence for the missing ADD form.
        for samples in [
            [0xFFFF; 6],
            [1, 0xFFFF, 1, 0xFFFF, 1, 0xFFFF],
            [0x8000, 0x8000, 0x7FFF, 1, 0, 0xFFFF],
            [0, 0, 0, 0, 0, 0],
        ] {
            let (mut cpu, mut bus) = machine(&[0x45, 0x81, 0x20, 0x90, 0]);
            cpu.lrb = 0x123; // Full LRB, not a hard-coded low-page bank.
            cpu.dd = true;
            let bank = 0x918;
            write_data_u16(&mut cpu, &mut bus, bank, 0);
            write_data_u16(&mut cpu, &mut bus, bank + 2, 0);
            let mut sum = 0u32;
            for sample in samples {
                cpu.pc = 0;
                cpu.a = sample;
                assert_eq!(step(&mut cpu, &mut bus).unwrap().mnemonic, "ADD er1, A");
                assert_eq!(step(&mut cpu, &mut bus).unwrap().mnemonic, "ADCB r0, #N8");
                sum += sample as u32;
                let actual = ((read_data_u16(&cpu, &mut bus, bank) as u32) << 16)
                    | read_data_u16(&cpu, &mut bus, bank + 2) as u32;
                assert_eq!(actual, sum);
                assert_eq!(read_data_u8(&cpu, &mut bus, bank + 1), 0);
                assert_eq!(read_data_u16(&cpu, &mut bus, 0x202), 0xA5A5);
            }
        }
    }

    #[test]
    fn producer_offpage_bit_forms_and_jbs_keep_the_required_flags_and_aliases() {
        for (opcode, bit, set) in [(0x0C, 4, false), (0x0D, 5, false), (0x1D, 5, true)] {
            for old_set in [false, true] {
                let (mut cpu, mut bus) = machine(&[0xC4, 0x17, opcode]);
                cpu.lrb = 0x123;
                let original = if old_set { 0x81 | (1 << bit) } else { 0x81 };
                write_data_u8(&mut cpu, &mut bus, 0x917, original);
                let before = cpu.psw_u16() & !Cpu::PSW_ZF_BIT;
                step(&mut cpu, &mut bus).unwrap();
                assert_eq!(cpu.zf, !old_set);
                assert_eq!(cpu.psw_u16() & !Cpu::PSW_ZF_BIT, before);
                assert_eq!(
                    read_data_u8(&cpu, &mut bus, 0x917),
                    if set {
                        original | (1 << bit)
                    } else {
                        original & !(1 << bit)
                    }
                );
                assert_eq!(read_data_u8(&cpu, &mut bus, 0x918), 0xA5);
            }
        }
        for set in [false, true] {
            let (mut cpu, mut bus) = machine(&[0xEF, 0x17, 2, 0, 0, 0]);
            cpu.lrb = 0x123;
            write_data_u8(&mut cpu, &mut bus, 0x917, if set { 0x80 } else { 0 });
            let before = cpu.psw_u16();
            assert_eq!(
                step(&mut cpu, &mut bus).unwrap().mnemonic,
                "JBS off N8.7, rel8"
            );
            assert_eq!(cpu.pc, if set { 5 } else { 3 });
            assert_eq!(cpu.psw_u16(), before);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn machine(bytes: &[u8]) -> (Cpu, Bus) {
        let mut cpu = Cpu::new();
        cpu.lrb = 0x43;
        (cpu, Bus::new(bytes.to_vec(), 0xA5))
    }

    #[test]
    fn decoded_ror_manual_examples_flags_and_selected_bank() {
        for dd in [false, true] {
            for (operand, carry, expected, expected_carry) in [
                (0, true, 0x8000, false),
                (1, false, 0, true),
                (0x8000, false, 0x4000, false),
            ] {
                let (mut cpu, mut bus) = machine(&[0x47, 0xC7]);
                cpu.set_psw_u16(0x6335 | if dd { 0x1000 } else { 0 });
                cpu.cf = carry;
                let before = cpu.psw_u16() & !Cpu::PSW_CF_BIT;
                write_data_u16(&mut cpu, &mut bus, 0x21E, operand);
                let d = step(&mut cpu, &mut bus).unwrap();
                assert_eq!((d.mnemonic, d.len), ("ROR er3", 2));
                assert_eq!(read_data_u16(&cpu, &mut bus, 0x21E), expected);
                assert_eq!(read_data_u8(&cpu, &mut bus, 0x21E), expected as u8);
                assert_eq!(read_data_u8(&cpu, &mut bus, 0x21F), (expected >> 8) as u8);
                assert_eq!(read_data_u16(&cpu, &mut bus, 0x206), 0xA5A5);
                assert_eq!(cpu.cf, expected_carry);
                assert_eq!(cpu.psw_u16() & !Cpu::PSW_CF_BIT, before);
            }
        }
    }

    #[test]
    fn decoded_ror_exhaustive_manual_formula() {
        let (mut cpu, mut bus) = machine(&[0x47, 0xC7]);
        for operand in 0..=u16::MAX {
            for carry in [false, true] {
                cpu.pc = 0;
                cpu.set_psw_u16(0x6335);
                cpu.cf = carry;
                write_data_u16(&mut cpu, &mut bus, 0x21E, operand);
                step(&mut cpu, &mut bus).unwrap();
                // Independent direct specification, not a production rotate helper.
                let expected = (operand / 2) + if carry { 32768 } else { 0 };
                assert_eq!(read_data_u16(&cpu, &mut bus, 0x21E), expected);
                assert_eq!(cpu.cf, operand % 2 == 1);
                assert_eq!(cpu.psw_u16() & !Cpu::PSW_CF_BIT, 0x6FFD);
            }
        }
    }

    #[test]
    fn decoded_loads_set_zero_and_width_but_preserve_carry_half_user_flags() {
        for (program, dd_before, dd_after) in [
            (vec![0xE5, 0xC4], false, true),  // L A,N8, printed 3-69.
            (vec![0x7F], true, false),        // LB A,r7, printed 3-70.
            (vec![0x92, 0xA8], false, false), // LC A,[DP], printed 3-72.
        ] {
            let (mut cpu, mut bus) = machine(&program);
            cpu.set_psw_u16(0xA231);
            cpu.dd = dd_before;
            cpu.zf = false;
            write_data_u16(&mut cpu, &mut bus, 0xC4, 0);
            write_data_u8(&mut cpu, &mut bus, 0x21F, 0);
            // LC reads two synthetic zero bytes after the instruction, from ROM.
            if program[0] == 0x92 {
                bus = Bus::new(vec![0x92, 0xA8, 0, 0], 0);
                write_data_u16(&mut cpu, &mut bus, 0x8C, 2);
            }
            let preserve = cpu.psw_u16() & !(Cpu::PSW_ZF_BIT | Cpu::PSW_DD_BIT);
            let d = step(&mut cpu, &mut bus).unwrap();
            assert!(cpu.zf, "{} must set ZF for zero", d.mnemonic);
            assert_eq!(cpu.dd, dd_after);
            assert_eq!(
                cpu.psw_u16() & !(Cpu::PSW_ZF_BIT | Cpu::PSW_DD_BIT),
                preserve
            );
        }
    }

    #[test]
    fn decoded_srl_preserves_zero_half_width_and_user_flags() {
        for program in [vec![0x63], vec![0x47, 0xE7]] {
            let (mut cpu, mut bus) = machine(&program);
            cpu.set_psw_u16(0x7335);
            cpu.a = 0x8001;
            write_data_u16(&mut cpu, &mut bus, 0x21E, 0x8001);
            let before = cpu.psw_u16() & !Cpu::PSW_CF_BIT;
            step(&mut cpu, &mut bus).unwrap();
            assert!(cpu.cf);
            assert_eq!(cpu.psw_u16() & !Cpu::PSW_CF_BIT, before);
        }
    }

    #[test]
    fn full_lrb_bank_and_off_page_do_not_alias_low_ram() {
        let (mut cpu, mut bus) = machine(&[0xF4, 0xA7]);
        cpu.lrb = 0x143;
        assert_eq!(cpu.bank_base(), 0xA18);
        assert_eq!(cpu.off_page(0xA7), 0xAA7);
        write_data_u8(&mut cpu, &mut bus, 0xAA7, 0x71);
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(cpu.al(), 0x71);
        cpu.pc = 0;
        cpu.lrb = 0x243;
        assert_eq!(cpu.bank_base(), 0x1218);
        assert!(matches!(
            step(&mut cpu, &mut bus),
            Err(ExecError::MemoryAccess(_))
        ));
    }

    #[test]
    fn register_bank_zero_uses_real_accumulator_alias() {
        let (mut cpu, mut bus) = machine(&[0x47, 0xC7]);
        cpu.lrb = 0;
        cpu.a = 1;
        cpu.cf = true;
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(cpu.a, 0x8000);
        assert!(cpu.cf);
        assert_eq!(read_data_u16(&cpu, &mut bus, 6), 0x8000);
    }

    #[test]
    fn aliases_and_scb_pointing_sets_have_only_one_storage_location() {
        let (mut cpu, mut bus) = machine(&[0x62, 0x34, 0x12, 0x40]);
        write_data_u16(&mut cpu, &mut bus, 2, 0x143);
        write_data_u16(&mut cpu, &mut bus, 4, 0x2337);
        assert_eq!(cpu.lrb, 0x143);
        assert_eq!(cpu.scb(), 7);
        write_data_u16(&mut cpu, &mut bus, 0xB8, 0x7654); // X1, SCB7.
        step(&mut cpu, &mut bus).unwrap(); // MOV DP,#1234.
        assert_eq!(read_data_u16(&cpu, &mut bus, 0xBC), 0x1234);
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x84), 0xA5A5);
        step(&mut cpu, &mut bus).unwrap(); // L A,X1.
        assert_eq!(read_data_u16(&cpu, &mut bus, 6), 0x7654);
        write_data_u8(&mut cpu, &mut bus, 7, 0x98);
        assert_eq!(cpu.a, 0x9854);
        write_data_u8(&mut cpu, &mut bus, 4, 0x10);
        assert_eq!(cpu.scb(), 0);
        assert_eq!(cpu.psw_u16() & 0x30, 0x10);
    }

    #[test]
    fn signed_usp_address_is_checked_without_wrapping() {
        let (mut cpu, mut bus) = machine(&[0xE3, 0xB3]); // L A,-77[USP].
        cpu.set_psw_u16(1);
        write_data_u16(&mut cpu, &mut bus, 0x8E, 0x180);
        // Effective address0133 is checked, then CPU word-aligned to0132
        // (manual1-20). Caller seed writes are raw consecutive bytes.
        write_data_u16(&mut cpu, &mut bus, 0x132, 0x1234);
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(cpu.a, 0x1234);
        cpu.pc = 0;
        write_data_u16(&mut cpu, &mut bus, 0x8E, 1);
        assert!(matches!(
            step(&mut cpu, &mut bus),
            Err(ExecError::MemoryAccess(_))
        ));
    }

    #[test]
    fn decoded_lc_reads_program_bytes_not_ram_and_keeps_dd() {
        let (mut cpu, mut bus) = machine(&[0x92, 0xA8, 0x34, 0x12]);
        cpu.set_psw_u16(1);
        write_data_u16(&mut cpu, &mut bus, 0x8C, 2);
        write_data_u16(&mut cpu, &mut bus, 2, 0xA143); // Data address 2 is LRB, not ROM.
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(cpu.a, 0x1234);
        assert!(!cpu.dd);
        assert_eq!(bus.program_reads(), vec![2, 3]);
    }

    #[test]
    fn decoded_cmp_mb_preserve_unrelated_state_and_equal_is_not_borrow() {
        for (threshold, code, expected) in [(17, 18, true), (17, 17, false), (17, 16, false)] {
            let (mut cpu, mut bus) = machine(&[0xC7, 0x33, 0xC4, 0x31, 0x39]);
            cpu.lrb = 0x20;
            cpu.set_psw_u16(0x2331);
            cpu.a = threshold;
            write_data_u8(&mut cpu, &mut bus, 0x133, code);
            write_data_u8(&mut cpu, &mut bus, 0x131, 0xA5);
            step(&mut cpu, &mut bus).unwrap();
            assert_eq!(cpu.cf, expected);
            assert_eq!(cpu.zf, threshold == code as u16);
            let before = cpu.psw_u16();
            step(&mut cpu, &mut bus).unwrap();
            assert_eq!(cpu.psw_u16(), before);
            assert_eq!(
                read_data_u8(&cpu, &mut bus, 0x131),
                0xA5 | if expected { 2 } else { 0 }
            );
        }
    }

    #[test]
    fn decoded_div_uses_32_bit_dividend_and_banked_quotient_remainder() {
        let (mut cpu, mut bus) = machine(&[0x90, 0x37]);
        cpu.a = 17;
        cpu.set_psw_u16(0xB335);
        write_data_u16(&mut cpu, &mut bus, 0x218, 2);
        write_data_u16(&mut cpu, &mut bus, 0x21C, 3);
        let preserve = cpu.psw_u16() & !(Cpu::PSW_CF_BIT | Cpu::PSW_ZF_BIT);
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(cpu.a, 43696);
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x218), 0);
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x21A), 1);
        assert!(!cpu.cf);
        assert!(!cpu.zf);
        assert_eq!(
            cpu.psw_u16() & !(Cpu::PSW_CF_BIT | Cpu::PSW_ZF_BIT),
            preserve
        );
    }

    #[test]
    fn memory_accesses_are_checked_and_unknown_opcode_is_an_error() {
        let (mut cpu, mut bus) = machine(&[0xF5, 0x08]);
        assert!(matches!(
            step(&mut cpu, &mut bus),
            Err(ExecError::MemoryAccess(_))
        ));
        let (mut cpu, mut bus) = machine(&[0x47]);
        assert!(step(&mut cpu, &mut bus).is_err());
        let (mut cpu, mut bus) = machine(&[0x47, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]);
        assert!(matches!(
            step(&mut cpu, &mut bus),
            Err(ExecError::UndefinedOpcode { .. })
        ));
        let mut bus = Bus::new(vec![1, 2], 0);
        assert_eq!(bus.read_code_u16(0), 513);
        bus.read_code_u16(1);
        assert!(bus.take_fault().is_some());
        bus.read_data_u16(0xFFF);
        assert!(bus.take_fault().is_some());
    }

    #[test]
    fn decoded_mb_only_accesses_the_selected_byte_at_ram_boundary() {
        let (mut cpu, mut bus) = machine(&[0xC2, 0x39]); // MB [DP].1,C.
        cpu.set_psw_u16(0xE331);
        write_data_u16(&mut cpu, &mut bus, 0x8C, 0xFFF);
        write_data_u8(&mut cpu, &mut bus, 0xFFF, 0xA5);
        let before = cpu.psw_u16();
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(read_data_u8(&cpu, &mut bus, 0xFFF), 0xA7);
        assert_eq!(cpu.psw_u16(), before);
    }
}
