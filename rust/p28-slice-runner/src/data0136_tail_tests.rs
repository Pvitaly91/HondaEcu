//! Invented ISA programs only. No OEM routine/window or actual-tail completion.
use crate::{
    bus::Bus,
    cpu::Cpu,
    decoder::{Decoded, Fields},
    exec::{read_data_u16, step, write_data_u16, write_data_u8},
    full_decoder::FULL_OPCODES,
    instruction_forms::FormAdmission,
};

fn decoded(name: &'static str, fields: Fields) -> Decoded {
    let index = FULL_OPCODES
        .iter()
        .position(|p| p.mnemonic == name)
        .unwrap();
    Decoded {
        index,
        mnemonic: name,
        len: FULL_OPCODES[index].bytes_pat.len(),
        fields,
        dd_after: None,
        cycles: 0,
    }
}
#[test]
fn exact_tail_admission_refuses_unowned_branch_jle_mul_timer_and_repaired_operands() {
    let compare = decoded(
        "CMPB N'8, #N8",
        Fields {
            n8_alt: 0xA2,
            n8: 5,
            ..Fields::default()
        },
    );
    assert_eq!(
        crate::data0136_tail::admission(&compare),
        FormAdmission::Allowed
    );
    let mut wrong = compare.clone();
    wrong.fields.n8_alt = 0xC8;
    assert_eq!(
        crate::data0136_tail::admission(&wrong),
        FormAdmission::Unsupported
    );
    wrong = compare.clone();
    wrong.fields.n8 = 6;
    assert_eq!(
        crate::data0136_tail::admission(&wrong),
        FormAdmission::Unsupported
    );
    for name in [
        "JBS off N8.2, rel8",
        "JLE rel8",
        "JGT rel8",
        "MULB",
        "MUL",
        "L A, N8",
    ] {
        assert_eq!(
            crate::data0136_tail::admission(&decoded(name, Fields::default())),
            FormAdmission::Unsupported
        );
    }
}
#[test]
fn invented_byte_memory_compare_preserves_a_hc_dd_neighbors_and_pending_word() {
    for value in 0..=255u16 {
        for dd in [false, true] {
            for hc in [false, true] {
                let mut bus = Bus::new(vec![0xC5, 0xD2, 0xC0, 7], 0x52);
                let mut cpu = Cpu::new();
                cpu.set_psw_u16(0xC032 | if dd { 0x1000 } else { 0 } | if hc { 0x2000 } else { 0 });
                cpu.lrb = 0x21;
                cpu.a = 0xBEEF;
                cpu.ssp = 0x7FC;
                write_data_u8(&mut cpu, &mut bus, 0xD2, value as u8);
                write_data_u16(&mut cpu, &mut bus, 0x7FE, 0x1234);
                let old = cpu.psw_u16();
                step(&mut cpu, &mut bus).unwrap();
                assert_eq!((cpu.cf, cpu.zf), (value < 7, value == 7));
                assert_eq!(cpu.psw_u16() & !0xC000, old & !0xC000);
                assert_eq!((cpu.a, cpu.ssp), (0xBEEF, 0x7FC));
                assert_eq!(read_data_u16(&cpu, &mut bus, 0x7FE), 0x1234);
            }
        }
    }
}
#[test]
fn independently_reviewed_jle_matrix_is_or_but_m2t_jgt_stays_rejected() {
    for cf in [false, true] {
        for zf in [false, true] {
            let mut bus = Bus::new(vec![0xCF, 5, 0, 0, 0, 0, 0, 0], 0);
            let mut cpu = Cpu::new();
            cpu.set_psw_u16(0x3032 | if cf { 0x8000 } else { 0 } | if zf { 0x4000 } else { 0 });
            let old = cpu.psw_u16();
            step(&mut cpu, &mut bus).unwrap();
            assert_eq!(cpu.pc, if cf || zf { 7 } else { 2 });
            assert_eq!(cpu.psw_u16(), old);
            assert_eq!(
                crate::common_result_consumer::admission(&decoded(
                    "JGT rel8",
                    Fields {
                        rel8: 7,
                        ..Fields::default()
                    }
                )),
                FormAdmission::Unsupported
            );
        }
    }
}
#[test]
fn invented_mul_byte_and_word_results_keep_cf_hc_dd_and_full_zero_semantics() {
    for byte in [false, true] {
        for dd in [false, true] {
            for (a, r) in [(0u16, 17u16), (19, 23), (255, 255), (4095, 4095)] {
                let mut bus = Bus::new(
                    if byte {
                        vec![0xA2, 0x34]
                    } else {
                        vec![0x90, 0x35]
                    },
                    0,
                );
                let mut cpu = Cpu::new();
                cpu.lrb = 0x21;
                cpu.set_psw_u16(0xA032 | if dd { 0x1000 } else { 0 });
                cpu.a = a;
                write_data_u16(&mut cpu, &mut bus, 0x108, r);
                let old = cpu.psw_u16();
                let product = if byte {
                    u32::from(a & 255) * u32::from(r & 255)
                } else {
                    u32::from(a) * u32::from(r)
                };
                step(&mut cpu, &mut bus).unwrap();
                assert_eq!(cpu.a, product as u16);
                assert_eq!(cpu.zf, product == 0);
                assert_eq!(cpu.psw_u16() & !0x4000, old & !0x4000);
                if !byte {
                    assert_eq!(read_data_u16(&cpu, &mut bus, 0x10A), (product >> 16) as u16);
                }
            }
        }
    }
}
#[test]
fn invented_pswl4_directional_bit_moves_preserve_neighbors_and_other_flags() {
    for cf in [false, true] {
        let mut bus = Bus::new(vec![0xA3, 0x3C, 0, 0xA3, 0x2C], 0);
        let mut cpu = Cpu::new();
        cpu.set_psw_u16(0x7032 | if cf { 0x8000 } else { 0 });
        let old = cpu.psw_u16();
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!((cpu.psw_u16() & 16) != 0, cf);
        assert_eq!(cpu.psw_u16() & !16, old & !16);
        cpu.pc = 3;
        cpu.cf = !cf;
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(cpu.cf, cf);
        assert_eq!(cpu.psw_u16(), if cf { old | 16 } else { old & !16 });
    }
}
#[test]
fn invented_native_call_prefix_stops_before_unprovided_timer_and_keeps_new_frame() {
    let mut rom = vec![0; 0x84];
    rom[0..3].copy_from_slice(&[0x32, 0x40, 0]);
    rom[0x40..0x46].copy_from_slice(&[0xC5, 0xC8, 0xC0, 7, 0xCE, 0x3A]);
    rom[0x80..0x82].copy_from_slice(&[0xE5, 0x3C]);
    let mut bus = Bus::new(rom, 0);
    let mut cpu = Cpu::new();
    cpu.lrb = 0x21;
    cpu.set_psw_u16(0x1102);
    write_data_u8(&mut cpu, &mut bus, 0xC8, 0);
    bus.begin_all_native();
    bus.begin_native_accesses();
    let contract = crate::runner::SliceContract {
        entry_pc: 0,
        exit_pcs: vec![0x80],
        code_ranges: vec![[0, 3], [0x40, 0x46]],
        psw: 0,
        lrb: 0,
        usp: 0,
        instruction_budget: 3,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    };
    let result = crate::runner::execute_in_state_observed(
        &mut cpu,
        &mut bus,
        &contract,
        &[],
        true,
        None,
        true,
    );
    assert_eq!(result.status, 0);
    assert_eq!((cpu.pc, cpu.ssp), (0x80, 0x7FC));
    assert!(!result
        .executed_instruction_bytes
        .as_ref()
        .unwrap()
        .contains(&0x80));
    let all = bus.end_all_native();
    let writes: Vec<_> = all.iter().filter(|v| v[4] == 1).collect();
    assert_eq!(writes, vec![&[0, 0, 0x7FE, 16, 1, 3]]);
    bus.end_native_accesses();
    assert_eq!(read_data_u16(&cpu, &mut bus, 0x7FE), 3);
    assert!(step(&mut cpu, &mut bus).is_err()); // invented guard-negative only, never OEM timer execution
    assert_eq!(read_data_u16(&cpu, &mut bus, 0x7FE), 3);
}
#[test]
fn detached_actual_boundary_helper_refuses_without_repair_or_native_execution() {
    let mut cpu = Cpu::new();
    let mut bus = Bus::new(vec![0; 32], 0);
    let frame = crate::cal_rt_roundtrip::Frame {
        writer_pc: 0x0664,
        event_index: 0,
        stack_address: 0x7FE,
        width: 16,
        return_pc: 0x0667,
        write_order: 9,
    };
    let before = (cpu.pc, cpu.psw_u16(), cpu.ssp, cpu.a);
    assert!(crate::data0136_tail::execute(&mut cpu, &mut bus, &frame).is_err());
    assert_eq!((cpu.pc, cpu.psw_u16(), cpu.ssp, cpu.a), before);
    assert_eq!(cpu.instructions, 0);
}
