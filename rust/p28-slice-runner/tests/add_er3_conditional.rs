//! Invented probes of the current 47 81 HYPOTHESIS, not primary ISA evidence.
//! HC preservation and DD0 execution below describe software only. They are not
//! asserted to be CPU-specified. No admission or executor policy is promoted.
use p28_slice_runner::{
    bus::Bus,
    chain_forms::compact_admission,
    cpu::Cpu,
    decoder::decode,
    exec::{read_data_u16, read_data_u8, step, write_data_u16},
    instruction_forms::FormAdmission,
    protocol::ADD_ASSUMPTION,
    runner::{execute_case, SliceContract},
};

#[test]
fn conditional_decoded_hypothesis_separates_direction_carry_width_wrap_and_bank() {
    let pairs = [
        (0, 0),
        (0, 0xffff),
        (0xffff, 1),
        (0x7fff, 1),
        (0x8000, 0x8000),
        (0x000f, 1),
        (0x00ff, 1),
        (0x0fff, 1),
        (0x12fe, 0x3403),
    ];
    for (er3, a) in pairs {
        for flags in 0..8u16 {
            for dd in [false, true] {
                for lrb in [0x40, 0x41, 0x143] {
                    for scratch in [0, 0x55, 0xaa] {
                        let mut cpu = Cpu::new();
                        cpu.lrb = lrb;
                        cpu.ssp = 0x180;
                        cpu.set_psw_u16(0x0355 | (flags << 13) | if dd { 0x1000 } else { 0 });
                        let mut bus = Bus::new(vec![0x47, 0x81], scratch);
                        let addr = cpu.bank_base() + 6;
                        write_data_u16(&mut cpu, &mut bus, addr, er3);
                        cpu.a = a;
                        let canaries = [
                            addr - 4,
                            addr - 2,
                            addr + 2,
                            addr + 4,
                            0xa8,
                            0xaa,
                            0xac,
                            0xae,
                            0x180,
                        ];
                        for (i, c) in canaries.iter().enumerate() {
                            write_data_u16(&mut cpu, &mut bus, *c, 0xa501 + i as u16);
                        }
                        let before = cpu.psw_u16();
                        let d = decode(dd, |i| [0x47, 0x81].get(i).copied().unwrap_or(0)).unwrap();
                        assert_eq!((d.mnemonic, d.len, d.dd_after), ("ADD er3, A", 2, None));
                        assert_eq!(
                            compact_admission(&d),
                            FormAdmission::Assumption(ADD_ASSUMPTION)
                        );
                        step(&mut cpu, &mut bus).unwrap();
                        // Literal arithmetic hypothesis; no executor/decoder helper computes expected.
                        let sum = er3 as u32 + a as u32;
                        assert_eq!(read_data_u16(&cpu, &mut bus, addr), sum as u16);
                        assert_eq!(read_data_u8(&cpu, &mut bus, addr), sum as u8);
                        assert_eq!(read_data_u8(&cpu, &mut bus, addr + 1), (sum >> 8) as u8);
                        assert_eq!(cpu.a, a);
                        assert_eq!(cpu.cf, sum > 65535);
                        assert_eq!(cpu.zf, sum as u16 == 0);
                        assert_eq!(cpu.psw_u16() & 0x3fff, before & 0x3fff); // current HC/DD/etc hypothesis
                        assert_eq!((cpu.pc, cpu.lrb, cpu.ssp), (2, lrb, 0x180));
                        for (i, c) in canaries.iter().enumerate() {
                            assert_eq!(read_data_u16(&cpu, &mut bus, *c), 0xa501 + i as u16);
                        }
                    }
                }
            }
        }
    }
}

#[test]
fn conditional_zero_er3_signed_byte_domain_is_not_a_proof() {
    for raw in 0..=255u16 {
        let a = raw as u8 as i8 as i16 as u16;
        let mut cpu = Cpu::new();
        cpu.lrb = 0x40;
        cpu.dd = true;
        let mut bus = Bus::new(vec![0x47, 0x81], 0x55);
        write_data_u16(&mut cpu, &mut bus, 0x206, 0);
        cpu.a = a;
        cpu.cf = true; // separates ADD hypothesis from ADC even with er3=0
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x206), a);
        assert_eq!(cpu.a, a);
        assert!(!cpu.cf);
    }
}

#[test]
fn conditional_bank_zero_alias_reads_both_operands_before_write() {
    let mut cpu = Cpu::new();
    cpu.a = 0x8081;
    cpu.lrb = 0; // er3 is accumulator DATA0006/0007, not an independent operand
    let mut bus = Bus::new(vec![0x47, 0x81], 0xaa);
    step(&mut cpu, &mut bus).unwrap();
    assert_eq!(cpu.a, 0x0102);
    assert_eq!(read_data_u16(&cpu, &mut bus, 6), 0x0102);
    assert!(cpu.cf);
}

#[test]
fn strict_stop_retains_bytes_and_permission_does_not_cover_neighbors() {
    for dd in [false, true] {
        let c = SliceContract {
            entry_pc: 0,
            exit_pcs: vec![2],
            code_ranges: vec![[0, 2]],
            psw: if dd { 0x1335 } else { 0x0335 },
            lrb: 0x40,
            usp: 0x180,
            instruction_budget: 1,
            data_seeds: vec![[0x206, 0xfe], [0x207, 0x12]],
            output_addresses: vec![0x206, 0x207],
            program_read_range: None,
        };
        let refused = execute_case(&[0x47, 0x81], &c, 0x55, false, true);
        assert_eq!((refused.status, refused.stop_pc, refused.steps), (1, 0, 0));
        assert!(refused.used_assumptions.is_empty());
        assert_eq!(refused.outputs, [0xfe, 0x12]);
        let permitted = execute_case(&[0x47, 0x81], &c, 0x55, true, true);
        assert_eq!(permitted.status, 0);
        assert_eq!(permitted.used_assumptions, [ADD_ASSUMPTION]);
        for prefix in [0x44, 0x45, 0x46] {
            let neighbor = execute_case(&[prefix, 0x81], &c, 0x55, true, true);
            assert_eq!(
                (neighbor.status, neighbor.stop_pc, neighbor.steps),
                (1, 0, 0)
            );
        }
    }
}
