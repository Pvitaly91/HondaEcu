//! Independently composed single-instruction probes, not an OEM program.
use p28_slice_runner::{
    bus::Bus,
    cpu::Cpu,
    exec::{read_data_u16, read_data_u8, step, write_data_u16, write_data_u8},
};

fn machine(program: &[u8], psw: u16) -> (Cpu, Bus) {
    let mut cpu = Cpu::new();
    cpu.lrb = 0x123;
    cpu.set_psw_u16(psw);
    (cpu, Bus::new(program.to_vec(), 0xA5))
}

#[test]
fn decoded_byte_add_accumulator_high_alias_sets_half_carry_without_carry_input() {
    // ADDB A,direct byte: ACCH is the architectural byte alias at DATA0007.
    let (mut cpu, mut bus) = machine(&[0xC5, 7, 0x82], 0x8330);
    cpu.a = 0x01FF;
    let keep = cpu.psw_u16() & !(Cpu::PSW_CF_BIT | Cpu::PSW_ZF_BIT | Cpu::PSW_HC_BIT);
    step(&mut cpu, &mut bus).unwrap();
    assert_eq!(cpu.a, 0x0100);
    assert!(cpu.cf);
    assert!(cpu.zf);
    assert!(cpu.hc);
    assert_eq!(
        cpu.psw_u16() & !(Cpu::PSW_CF_BIT | Cpu::PSW_ZF_BIT | Cpu::PSW_HC_BIT),
        keep
    );
}

#[test]
fn decoded_byte_add_r0_is_byte_under_both_descriptors_and_sets_half_carry() {
    for dd in [false, true] {
        let (mut cpu, mut bus) = machine(&[0x20, 0x81], 0x8335);
        cpu.dd = dd;
        cpu.a = 0xCA01;
        let bank = cpu.bank_base();
        write_data_u8(&mut cpu, &mut bus, bank, 0xFF);
        let keep = cpu.psw_u16() & !(Cpu::PSW_CF_BIT | Cpu::PSW_ZF_BIT | Cpu::PSW_HC_BIT);
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(read_data_u8(&cpu, &mut bus, bank), 0);
        assert_eq!(read_data_u8(&cpu, &mut bus, bank + 1), 0xA5);
        assert_eq!(cpu.a, 0xCA01);
        assert!(cpu.cf);
        assert!(cpu.zf);
        assert!(cpu.hc);
        assert_eq!(
            cpu.psw_u16() & !(Cpu::PSW_CF_BIT | Cpu::PSW_ZF_BIT | Cpu::PSW_HC_BIT),
            keep
        );
    }
}

#[test]
fn decoded_increment_indexed_word_sets_half_carry_preserving_carry_and_descriptor() {
    let (mut cpu, mut bus) = machine(&[0xB1, 0xA0, 3, 0x16], 0x8332);
    let x2 = 0x80 + cpu.scb() * 8 + 2;
    write_data_u16(&mut cpu, &mut bus, x2, 4);
    write_data_u16(&mut cpu, &mut bus, 0x3A4, 0xFFFF);
    let keep = cpu.psw_u16() & !(Cpu::PSW_ZF_BIT | Cpu::PSW_HC_BIT);
    step(&mut cpu, &mut bus).unwrap();
    assert_eq!(read_data_u16(&cpu, &mut bus, 0x3A4), 0);
    assert!(cpu.zf);
    assert!(cpu.hc);
    assert_eq!(cpu.psw_u16() & !(Cpu::PSW_ZF_BIT | Cpu::PSW_HC_BIT), keep);
}

#[test]
fn decoded_multiply_is_unsigned_word_and_preserves_nonzero_flags_and_er0() {
    for dd in [false, true] {
        let (mut cpu, mut bus) = machine(&[0x90, 0x35], 0xE330);
        cpu.dd = dd;
        cpu.a = 0xFFFF;
        let bank = cpu.bank_base();
        write_data_u16(&mut cpu, &mut bus, bank, 0xFFFF);
        let keep = cpu.psw_u16() & !Cpu::PSW_ZF_BIT;
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(cpu.a, 1);
        assert_eq!(read_data_u16(&cpu, &mut bus, bank + 2), 0xFFFE);
        assert_eq!(read_data_u16(&cpu, &mut bus, bank), 0xFFFF);
        assert!(!cpu.zf);
        assert_eq!(cpu.psw_u16() & !Cpu::PSW_ZF_BIT, keep);
    }
}

#[test]
fn decoded_lc_x1_under_byte_descriptor_reads_both_program_bytes() {
    let (mut cpu, mut bus) = machine(&[0x90, 0xA8, 0xFF, 0x01], 0x2330);
    write_data_u16(&mut cpu, &mut bus, 0x80, 2);
    step(&mut cpu, &mut bus).unwrap();
    assert_eq!(cpu.a, 0x01FF);
    assert!(!cpu.dd);
    assert_eq!(bus.program_reads(), vec![2, 3]);
}

#[test]
fn decoded_indexed_moves_distinguish_word_and_byte_without_changing_flags() {
    for (program, expected) in [
        (&[0xB1, 0xA0, 3, 0x48][..], 0x1234),
        (&[0xC1, 0xA0, 3, 0x48][..], 0xA534),
    ] {
        for dd in [false, true] {
            let (mut cpu, mut bus) = machine(program, 0xE330);
            cpu.dd = dd;
            write_data_u16(&mut cpu, &mut bus, 0x82, 4);
            write_data_u16(&mut cpu, &mut bus, 0x3A4, 0x1234);
            let flags = cpu.psw_u16();
            step(&mut cpu, &mut bus).unwrap();
            assert_eq!(read_data_u16(&cpu, &mut bus, cpu.bank_base()), expected);
            assert_eq!(cpu.psw_u16(), flags);
        }
    }
}

#[test]
fn decoded_indexed_compare_uses_separate_displacement_and_immediate_preserves_halfcarry() {
    let (mut cpu, mut bus) = machine(&[0xB1, 0xA0, 3, 0xC0, 0x34, 0x12], 0xE330);
    write_data_u16(&mut cpu, &mut bus, 0x82, 4);
    write_data_u16(&mut cpu, &mut bus, 0x3A4, 0x1234);
    let keep = cpu.psw_u16() & !(Cpu::PSW_CF_BIT | Cpu::PSW_ZF_BIT);
    step(&mut cpu, &mut bus).unwrap();
    assert!(cpu.zf);
    assert!(!cpu.cf);
    assert_eq!(read_data_u16(&cpu, &mut bus, 0x3A4), 0x1234);
    assert_eq!(cpu.psw_u16() & !(Cpu::PSW_CF_BIT | Cpu::PSW_ZF_BIT), keep);
}

#[test]
fn decoded_indexed_clear_variants_preserve_flags_and_byte_clear_preserves_neighbor() {
    for (program, expected) in [
        (&[0xB1, 0xA0, 3, 0x15][..], 0),
        (&[0xC1, 0xA0, 3, 0x15][..], 0xA500),
    ] {
        let (mut cpu, mut bus) = machine(program, 0xE330);
        write_data_u16(&mut cpu, &mut bus, 0x82, 4);
        let flags = cpu.psw_u16();
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x3A4), expected);
        assert_eq!(cpu.psw_u16(), flags);
    }
    let (mut cpu, mut bus) = machine(&[0x91, 0x15], 0xE330);
    let flags = cpu.psw_u16();
    step(&mut cpu, &mut bus).unwrap();
    assert_eq!(read_data_u16(&cpu, &mut bus, 0x82), 0);
    assert_eq!(cpu.psw_u16(), flags);
}

#[test]
fn decoded_lcb_and_byte_store_preserve_high_byte_descriptor_and_nonzero_flags() {
    for dd in [false, true] {
        let (mut cpu, mut bus) = machine(&[0x90, 0x9D, 4, 0, 0], 0xA330);
        cpu.dd = dd;
        cpu.a = 0xCDFF;
        let keep = cpu.psw_u16() & !Cpu::PSW_ZF_BIT;
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(cpu.a, 0xCD00);
        assert!(cpu.zf);
        assert_eq!(cpu.psw_u16() & !Cpu::PSW_ZF_BIT, keep);
        assert_eq!(bus.program_reads(), [4]);
    }
    let (mut cpu, mut bus) = machine(&[0xD1, 0xA0, 3], 0xE330);
    write_data_u16(&mut cpu, &mut bus, 0x82, 4);
    cpu.a = 0xAB12;
    let flags = cpu.psw_u16();
    step(&mut cpu, &mut bus).unwrap();
    assert_eq!(read_data_u16(&cpu, &mut bus, 0x3A4), 0xA512);
    assert_eq!(cpu.psw_u16(), flags);
}
