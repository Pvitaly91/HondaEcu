use p28_slice_runner::{
    bus::Bus,
    cpu::Cpu,
    exec::{read_data_u16, read_data_u8, step, write_data_u16, write_data_u8},
    idle_contexts::admission,
    instruction_forms::FormAdmission,
};

#[test]
fn exact_cmp_forms_preserve_accumulator_hc_dd_and_observe_unsigned_operands() {
    // Primary chapter3 printed3-38/39/42. Invented isolated decoded instructions.
    for form in 0..3 {
        for lhs in [0u16, 1, 127, 128, 255, 256, 32768, 65535] {
            for rhs in [0u16, 1, 128, 255, 256, 65535] {
                for dd in [false, true] {
                    if form == 0 && dd {
                        continue;
                    }
                    let bytes = match form {
                        0 => vec![0x49],
                        1 => vec![0xB4, 0x74, 0xC0, rhs as u8, (rhs >> 8) as u8],
                        _ => vec![0xC4, 0xE8, 0xC0, rhs as u8],
                    };
                    let mut bus = Bus::new(bytes, 0xA5);
                    let mut cpu = Cpu::new();
                    cpu.lrb = 0x41;
                    cpu.set_psw_u16(if dd { 0x3101 } else { 0x2101 });
                    cpu.a = 0xBEEF;
                    match form {
                        0 => {
                            cpu.a = 0xAB00 | (lhs & 255);
                            write_data_u8(&mut cpu, &mut bus, 0x209, rhs as u8);
                        }
                        1 => write_data_u16(&mut cpu, &mut bus, 0x274, lhs),
                        _ => write_data_u8(&mut cpu, &mut bus, 0x2E8, lhs as u8),
                    }
                    let acc = cpu.a;
                    let flags = cpu.psw_u16() & !(Cpu::PSW_CF_BIT | Cpu::PSW_ZF_BIT);
                    let decoded = step(&mut cpu, &mut bus).unwrap();
                    assert_eq!(admission(&decoded), FormAdmission::Allowed);
                    let (a, b) = if form == 1 {
                        (lhs, rhs)
                    } else {
                        (lhs & 255, rhs & 255)
                    };
                    assert_eq!(cpu.cf, a < b);
                    assert_eq!(cpu.zf, a == b);
                    assert_eq!(cpu.a, acc);
                    assert_eq!(cpu.psw_u16() & !(Cpu::PSW_CF_BIT | Cpu::PSW_ZF_BIT), flags);
                }
            }
        }
    }
}

#[test]
fn jle_and_bit_branches_preserve_flags_and_take_both_directions() {
    // Printed3-64/65/66: signed relative displacement, no flag writes; LE = CF || ZF.
    for cf in [false, true] {
        for zf in [false, true] {
            let mut bus = Bus::new(vec![0xCF, 0xFE], 0);
            let mut cpu = Cpu::new();
            cpu.cf = cf;
            cpu.zf = zf;
            let flags = cpu.psw_u16();
            assert_eq!(
                admission(&step(&mut cpu, &mut bus).unwrap()),
                FormAdmission::Allowed
            );
            assert_eq!(cpu.pc, if cf || zf { 0 } else { 2 });
            assert_eq!(cpu.psw_u16(), flags);
        }
    }
    for (opcode, mask, set) in [(0xEE, 64, true), (0xDD, 32, false)] {
        for value in [0u8, 32, 64, 255] {
            let mut bus = Bus::new(vec![opcode, 0x25, 0xFD], 0);
            let mut cpu = Cpu::new();
            cpu.lrb = 0x41;
            cpu.set_psw_u16(0xF101);
            write_data_u8(&mut cpu, &mut bus, 0x225, value);
            let flags = cpu.psw_u16();
            assert_eq!(
                admission(&step(&mut cpu, &mut bus).unwrap()),
                FormAdmission::Allowed
            );
            assert_eq!(cpu.pc, if ((value & mask) != 0) == set { 0 } else { 3 });
            assert_eq!(cpu.psw_u16(), flags);
        }
    }
}

#[test]
fn exact_moves_lcb_and_exchange_width_bank_alias_and_dd_contracts() {
    for dd in [false, true] {
        for form in 0..8 {
            if form >= 5 && dd {
                continue;
            }
            let bytes = match form {
                0 => vec![0x22, 0x49],
                1 => vec![0x99, 0x3D],
                2 => vec![0x47, 0x98, 0x34, 0x92],
                3 => vec![0x90, 0xAB, 3, 0],
                4 => vec![0x24, 0x8A],
                5 => vec![0x8D],
                6 => vec![0x21, 0x10],
                _ => vec![0x24, 0x10],
            };
            let mut rom = vec![0; 128];
            rom[..bytes.len()].copy_from_slice(&bytes);
            rom[67] = 0x73;
            let mut bus = Bus::new(rom, 0xA5);
            let mut cpu = Cpu::new();
            cpu.lrb = 0x41;
            cpu.set_psw_u16(if dd { 0xF101 } else { 0xE101 });
            cpu.a = 0xCA42;
            write_data_u16(&mut cpu, &mut bus, 0x88, 64);
            write_data_u8(&mut cpu, &mut bus, 0x20A, 0x27);
            let flags = cpu.psw_u16();
            assert_eq!(
                admission(&step(&mut cpu, &mut bus).unwrap()),
                FormAdmission::Allowed
            );
            match form {
                0 => assert_eq!(read_data_u8(&cpu, &mut bus, 0x209), 0x27),
                1 => assert_eq!(read_data_u8(&cpu, &mut bus, 0x209), 0x3D),
                2 => assert_eq!(read_data_u16(&cpu, &mut bus, 0x20E), 0x9234),
                3 => {
                    assert_eq!(cpu.a, 0xCA73);
                    assert!(!cpu.zf);
                }
                4 => assert_eq!(read_data_u8(&cpu, &mut bus, 0x20C), 0x42),
                5 => assert_eq!(read_data_u8(&cpu, &mut bus, 0x20D), 0x42),
                _ => {
                    assert_eq!(cpu.a, 0xCAA5);
                    assert_eq!(
                        read_data_u8(&cpu, &mut bus, if form == 6 { 0x209 } else { 0x20C }),
                        0x42
                    );
                }
            }
            assert_eq!(
                cpu.psw_u16(),
                if form == 3 {
                    flags & !Cpu::PSW_ZF_BIT
                } else {
                    flags
                }
            );
        }
    }
}
