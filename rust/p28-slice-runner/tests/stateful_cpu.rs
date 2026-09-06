//! Independently invented decoded single-instruction probes; no ROM fixture.
use p28_slice_runner::{
    bus::Bus,
    cpu::Cpu,
    exec::{read_data_u8, step, write_data_u16, write_data_u8},
};

fn machine(bytes: &[u8], flags: bool) -> (Cpu, Bus) {
    let mut cpu = Cpu::new();
    cpu.lrb = 0x23;
    cpu.set_psw_u16(0x0101);
    cpu.cf = flags;
    cpu.hc = flags;
    cpu.zf = flags;
    (cpu, Bus::new(bytes.to_vec(), 0xA5))
}

#[test]
fn clrb_accumulator_sets_zero_preserves_high_carry_halfcarry_and_clears_dd() {
    for flags in [false, true] {
        let (mut cpu, mut bus) = machine(&[0xFA], flags);
        cpu.dd = true;
        cpu.a = 0xD37A;
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(cpu.a, 0xD300);
        assert!(!cpu.dd);
        assert!(cpu.zf);
        assert_eq!((cpu.cf, cpu.hc), (flags, flags));
    }
}

#[test]
fn increment_dp_and_decrement_indexed_byte_update_halfcarry_only_audited_forms() {
    let mut failures = vec![];
    for flags in [false, true] {
        for value in [0u16, 1, 15, 16, 255] {
            for dd in [false, true] {
                let (mut cpu, mut bus) = machine(&[0x72], flags);
                cpu.dd = dd;
                let dp = 0x80 + cpu.scb() * 8 + 4;
                write_data_u16(&mut cpu, &mut bus, dp, value);
                step(&mut cpu, &mut bus).unwrap();
                if cpu.hc != (value & 15 == 15) {
                    failures.push(format!("INC DP value={value} incomingHC={flags} DD={dd}"));
                }
                assert_eq!((cpu.cf, cpu.dd), (flags, dd));
                let (mut cpu, mut bus) = machine(&[0xC0, 0xA0, 2, 0x17], flags);
                cpu.dd = dd;
                let x1 = 0x80 + cpu.scb() * 8;
                write_data_u16(&mut cpu, &mut bus, x1, 4);
                write_data_u8(&mut cpu, &mut bus, 0x2A4, value as u8);
                step(&mut cpu, &mut bus).unwrap();
                assert_eq!(
                    read_data_u8(&cpu, &mut bus, 0x2A4),
                    (value as u8).wrapping_sub(1)
                );
                assert_eq!(read_data_u8(&cpu, &mut bus, 0x2A5), 0xA5);
                if cpu.hc != (value & 15 == 0) {
                    failures.push(format!(
                        "DECB indexed X1 value={value} incomingHC={flags} DD={dd}"
                    ));
                }
                assert_eq!(cpu.zf, value == 1);
                assert_eq!((cpu.cf, cpu.dd), (flags, dd));
            }
        }
    }
    assert!(failures.is_empty(), "{failures:?}");
}

#[test]
fn byte_sub_accumulator_and_banked_destinations_update_halfborrow() {
    let mut failures = vec![];
    // The off-page byte A7 encoding is tested as a CONDITIONAL inference,
    // not thereby admitted as primary-established by the runner registry.
    for program in [
        &[0x29][..],
        &[0x2E][..],
        &[0x2F][..],
        &[0xA6, 1][..],
        &[0xA7, 0xB0][..],
        &[0x20, 0xA1][..],
        &[0x26, 0xA1][..],
    ] {
        for flags in [false, true] {
            let (mut cpu, mut bus) = machine(program, flags);
            let bank = cpu.bank_base();
            let dest = program.len() == 2 && program[1] == 0xA1;
            cpu.a = if dest { 0xD301 } else { 0xD310 };
            for r in [0, 1, 6, 7] {
                write_data_u8(&mut cpu, &mut bus, bank + r, if dest { 16 } else { 1 });
            }
            write_data_u8(&mut cpu, &mut bus, 0x1B0, 1);
            step(&mut cpu, &mut bus).unwrap();
            if !cpu.hc {
                failures.push(format!("{program:02X?} incomingHC={flags}"));
            }
            assert!(!cpu.cf);
            assert!(!cpu.zf);
            if dest {
                assert_eq!(cpu.a, 0xD301);
                assert_eq!(
                    read_data_u8(&cpu, &mut bus, bank + (program[0] - 0x20) as u16),
                    15
                );
            } else {
                assert_eq!(cpu.a, 0xD30F);
            }
        }
    }
    assert!(failures.is_empty(), "{failures:?}");
}

#[test]
fn byte_add_accumulator_immediate_and_r6_update_halfcarry_without_carry_in() {
    let mut failures = vec![];
    for program in [&[0x86, 1][..], &[0x0E][..]] {
        for flags in [false, true] {
            let (mut cpu, mut bus) = machine(program, flags);
            cpu.a = 0xD3FF;
            let bank = cpu.bank_base();
            write_data_u8(&mut cpu, &mut bus, bank + 6, 1);
            step(&mut cpu, &mut bus).unwrap();
            assert_eq!(cpu.a, 0xD300);
            if !cpu.hc {
                failures.push(format!("{program:02X?} incomingHC={flags}"));
            }
            assert!(cpu.cf);
            assert!(cpu.zf);
        }
    }
    assert!(failures.is_empty(), "{failures:?}");
}

#[test]
fn byte_multiply_divide_use_banked_r0_r1_and_word_accumulator_preserving_dd() {
    for dd in [false, true] {
        let (mut cpu, mut bus) = machine(&[0xA2, 0x34, 0xA2, 0x36], true);
        cpu.dd = dd;
        cpu.a = 0xE811;
        let bank = cpu.bank_base();
        write_data_u8(&mut cpu, &mut bus, bank, 19);
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(cpu.a, 323);
        assert!(cpu.cf);
        assert!(cpu.hc);
        assert_eq!(cpu.dd, dd);
        write_data_u8(&mut cpu, &mut bus, bank, 7);
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(cpu.a, 46);
        assert_eq!(read_data_u8(&cpu, &mut bus, bank + 1), 1);
        assert!(!cpu.cf);
        assert!(cpu.hc);
        assert_eq!(cpu.dd, dd);
    }
}

#[test]
fn arithmetic_half_flags_are_cleared_as_well_as_set_and_all_byte_boundaries_are_unsigned() {
    for lhs in [0u8, 1, 15, 16, 127, 128, 254, 255] {
        for rhs in [0u8, 1, 15, 16, 127, 128, 254, 255] {
            for incoming in [false, true] {
                for opcode in [0x86, 0xA6] {
                    let (mut cpu, mut bus) = machine(&[opcode, rhs], incoming);
                    cpu.a = 0xA500 | lhs as u16;
                    step(&mut cpu, &mut bus).unwrap();
                    let add = opcode == 0x86;
                    let result = if add {
                        lhs.wrapping_add(rhs)
                    } else {
                        lhs.wrapping_sub(rhs)
                    };
                    assert_eq!(cpu.a, 0xA500 | result as u16);
                    assert_eq!(cpu.zf, result == 0);
                    assert_eq!(
                        cpu.cf,
                        if add {
                            lhs as u16 + rhs as u16 > 255
                        } else {
                            lhs < rhs
                        }
                    );
                    assert_eq!(
                        cpu.hc,
                        if add {
                            (lhs & 15) + (rhs & 15) > 15
                        } else {
                            (lhs & 15) < (rhs & 15)
                        }
                    );
                }
            }
        }
    }
}

#[test]
fn decoded_call_return_and_immediate_masks_preserve_the_nonzero_flags_and_stack() {
    let (mut cpu, mut bus) = machine(&[0x32, 5, 0, 0, 0, 0x01], true);
    cpu.ssp = 0x7FE;
    cpu.a = 0xD321;
    let flags = cpu.psw_u16();
    step(&mut cpu, &mut bus).unwrap();
    assert_eq!(cpu.pc, 5);
    assert_eq!(cpu.ssp, 0x7FC);
    step(&mut cpu, &mut bus).unwrap();
    assert_eq!(cpu.pc, 3);
    assert_eq!(cpu.ssp, 0x7FE);
    assert_eq!(cpu.psw_u16(), flags);
    assert_eq!(cpu.a, 0xD321);
    for dd in [false, true] {
        let (mut cpu, mut bus) = machine(&[0xD6, 0, 0], true);
        cpu.dd = dd;
        cpu.a = 0xA50F;
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(cpu.a, if dd { 0 } else { 0xA500 });
        assert!(cpu.zf);
        assert!(cpu.cf);
        assert!(cpu.hc);
        assert_eq!(cpu.dd, dd);
    }
}
