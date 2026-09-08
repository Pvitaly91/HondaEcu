use p28_slice_runner::{
    bus::Bus,
    cpu::Cpu,
    exec::{read_data_u16, read_data_u8, step, write_data_u16, write_data_u8},
    idle::admission,
    instruction_forms::FormAdmission,
};

#[test]
fn idle_exact_arithmetic_flags_decoded_regression() {
    // Invented single instructions/operands. Manual 3-13/15, 3-156/157/161.
    for form in 0..7 {
        for lhs in [0u16, 15, 16, 255, 256, 0x8000, 0xFFFF] {
            for rhs in [0u16, 1, 15, 16, 255, 0x8000, 0xFFFF] {
                for prior in [false, true] {
                    let bytes = match form {
                        0 => vec![0x0B],
                        1 => vec![0x29],
                        2 => vec![0x2B],
                        3 => vec![0xA7, 0x52],
                        4 => vec![0x47, 0xA1],
                        5 => vec![0x24, 0xA1],
                        _ => vec![0x90, 0x80, rhs as u8, (rhs >> 8) as u8],
                    };
                    let mut bus = Bus::new(bytes, 0xA5);
                    let mut cpu = Cpu::new();
                    cpu.lrb = 0x41;
                    cpu.set_psw_u16(0x1101);
                    cpu.hc = prior;
                    cpu.a = lhs;
                    let address = match form {
                        1 => 0x20A,
                        3 => 0x252,
                        5 => 0x20C,
                        6 => 0x88,
                        _ => 0x20E,
                    };
                    write_data_u16(
                        &mut cpu,
                        &mut bus,
                        address,
                        if form >= 4 { lhs } else { rhs },
                    );
                    if form == 4 || form == 5 {
                        cpu.a = rhs;
                    }
                    let before =
                        cpu.psw_u16() & !(Cpu::PSW_CF_BIT | Cpu::PSW_ZF_BIT | Cpu::PSW_HC_BIT);
                    let decoded = step(&mut cpu, &mut bus).unwrap();
                    assert_eq!(admission(&decoded), FormAdmission::Allowed);
                    let (a, b) = if form == 5 {
                        (lhs & 255, rhs & 255)
                    } else {
                        (lhs, rhs)
                    };
                    let add = form == 0 || form == 6;
                    let mask = if form == 5 { 255u32 } else { 65535 };
                    let result = if add {
                        (a as u32 + b as u32) & mask
                    } else {
                        (a as u32).wrapping_sub(b as u32) & mask
                    };
                    let actual = if form == 5 {
                        read_data_u8(&cpu, &mut bus, address) as u16
                    } else if form >= 4 {
                        read_data_u16(&cpu, &mut bus, address)
                    } else {
                        cpu.a
                    };
                    assert_eq!(actual as u32, result, "form {form}");
                    assert_eq!(
                        cpu.cf,
                        if add {
                            a as u32 + b as u32 > mask
                        } else {
                            a < b
                        }
                    );
                    assert_eq!(cpu.zf, result == 0);
                    assert_eq!(
                        cpu.hc,
                        if add {
                            (a & 15) + (b & 15) > 15
                        } else {
                            (a & 15) < (b & 15)
                        },
                        "form {form}, {a}-{b}, prior {prior}"
                    );
                    assert_eq!(
                        cpu.psw_u16() & !(Cpu::PSW_CF_BIT | Cpu::PSW_ZF_BIT | Cpu::PSW_HC_BIT),
                        before
                    );
                    if form == 5 {
                        assert_eq!(read_data_u8(&cpu, &mut bus, address + 1), (lhs >> 8) as u8);
                    }
                }
            }
        }
    }
}

#[test]
fn idle_new_data_forms_decode_width_aliases_and_flags_without_oem_programs() {
    // Independent single-form probes, never a reconstruction of the native helper.
    for (bytes, name) in [
        (vec![0x9A, 0x35], "MOVB r2, #N8"),
        (vec![0x4A], "CMPB A, r2"),
        (vec![0x47, 0x15], "CLR er3"),
        (vec![0x42], "L A, DP"),
        (vec![0x89], "ST A, er1"),
        (vec![0x8B], "ST A, er3"),
        (vec![0x83], "SWAP"),
        (vec![0x45, 0x48], "MOV er0, er1"),
        (vec![0xC4, 0x34, 0x3C], "MB off N8.4, C"),
        (vec![0xF6, 0xFF, 0xFF], "XOR A, #N16"),
        (vec![0xD5, 0xCA], "ST A, N8"),
    ] {
        let mut bus = Bus::new(bytes, 0xA5);
        let mut cpu = Cpu::new();
        cpu.lrb = 0x41;
        cpu.set_psw_u16(0xD501);
        cpu.a = 0x1234;
        write_data_u16(&mut cpu, &mut bus, 0x20A, 0x3456);
        write_data_u16(&mut cpu, &mut bus, 0x20E, 0xCDEF);
        write_data_u16(&mut cpu, &mut bus, 0x8C, 0x5678);
        if name == "CMPB A, r2" {
            cpu.dd = false;
            write_data_u8(&mut cpu, &mut bus, 0x20A, 0x35);
        }
        let before = cpu.psw_u16();
        let d = step(&mut cpu, &mut bus).unwrap();
        assert_eq!(d.mnemonic, name);
        assert_eq!(admission(&d), FormAdmission::Allowed);
        let mut affected = 0;
        match name {
            "MOVB r2, #N8" => assert_eq!(read_data_u16(&cpu, &mut bus, 0x20A), 0x3435),
            "CMPB A, r2" => {
                assert!(cpu.cf);
                assert!(!cpu.zf);
                affected = Cpu::PSW_CF_BIT | Cpu::PSW_ZF_BIT;
            }
            "CLR er3" => {
                assert_eq!(read_data_u16(&cpu, &mut bus, 0x20E), 0);
                assert!(cpu.zf);
                affected = Cpu::PSW_ZF_BIT;
            }
            "L A, DP" => {
                assert_eq!(cpu.a, 0x5678);
                assert!(!cpu.zf);
                assert!(cpu.dd);
                affected = Cpu::PSW_ZF_BIT | Cpu::PSW_DD_BIT;
            }
            "ST A, er1" => assert_eq!(read_data_u16(&cpu, &mut bus, 0x20A), 0x1234),
            "ST A, er3" => assert_eq!(read_data_u16(&cpu, &mut bus, 0x20E), 0x1234),
            "SWAP" => assert_eq!(cpu.a, 0x3412),
            "MOV er0, er1" => assert_eq!(read_data_u16(&cpu, &mut bus, 0x208), 0x3456),
            "MB off N8.4, C" => assert_eq!(read_data_u8(&cpu, &mut bus, 0x234), 0xB5),
            "XOR A, #N16" => {
                assert_eq!(cpu.a, 0xEDCB);
                assert!(!cpu.zf);
                affected = Cpu::PSW_ZF_BIT;
            }
            "ST A, N8" => assert_eq!(read_data_u16(&cpu, &mut bus, 0xCA), 0x1234),
            _ => unreachable!(),
        }
        assert_eq!(cpu.psw_u16() & !affected, before & !affected, "{name}");
    }
}

#[test]
fn idle_native_vector_calls_fetch_actual_vector_and_balance_same_stack() {
    for (opcode, vector) in [(0x10, 0x28), (0x17, 0x36)] {
        let mut bytes = vec![0; 0x81];
        bytes[0] = opcode;
        bytes[vector] = 0x80;
        bytes[0x80] = 0x01; // invented single RT target
        let mut bus = Bus::new(bytes, 0xA5);
        let mut cpu = Cpu::new();
        cpu.set_psw_u16(0xD501);
        cpu.ssp = 0x7FE;
        let before = cpu.psw_u16();
        let d = step(&mut cpu, &mut bus).unwrap();
        assert_eq!(admission(&d), FormAdmission::Allowed);
        assert_eq!(cpu.pc, 0x80);
        assert_eq!(cpu.ssp, 0x7FC);
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x7FE), 1);
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(cpu.pc, 1);
        assert_eq!(cpu.ssp, 0x7FE);
        assert_eq!(cpu.psw_u16(), before);
    }
}
#[test]
fn idle_word_store_dd_and_byte_exchange_are_distinct() {
    for dd in [false, true] {
        let mut bus = Bus::new(vec![0xD4, 0x52], 0xA5);
        let mut cpu = Cpu::new();
        cpu.lrb = 0x41;
        cpu.set_psw_u16(0x1101);
        cpu.dd = dd;
        cpu.a = 0x12EF;
        let before = cpu.psw_u16();
        let d = step(&mut cpu, &mut bus).unwrap();
        assert_eq!(
            d.mnemonic,
            if dd { "ST A, off N8" } else { "STB A, off N8" }
        );
        assert_eq!(
            read_data_u16(&cpu, &mut bus, 0x252),
            if dd { 0x12EF } else { 0xA5EF }
        );
        assert_eq!(cpu.psw_u16(), before);
    }
    let mut bus = Bus::new(vec![0x25, 0x10], 0xA5);
    let mut cpu = Cpu::new();
    cpu.lrb = 0x41;
    cpu.set_psw_u16(0x8101);
    cpu.a = 0xAB12;
    write_data_u8(&mut cpu, &mut bus, 0x20D, 0x34);
    let before = cpu.psw_u16();
    let d = step(&mut cpu, &mut bus).unwrap();
    assert_eq!(admission(&d), FormAdmission::Allowed);
    assert_eq!(cpu.a, 0xAB34);
    assert_eq!(read_data_u8(&cpu, &mut bus, 0x20D), 0x12);
    assert_eq!(cpu.psw_u16(), before);
}
