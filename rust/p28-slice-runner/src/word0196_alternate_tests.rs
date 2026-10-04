//! Newly composed decoded probes; never an OEM byte fixture.
use crate::{
    instruction_forms::FormAdmission,
    quartet_handoff::Generation,
    runner::{execute_in_state_observed, SliceContract},
    word0196_handoff::reader_generation,
};
fn invented(
    value: u16,
    immediate: u16,
    partial: bool,
    byte_compare: bool,
) -> (Cpu, Bus, crate::protocol::CaseResult) {
    let mut code = vec![
        0x67,
        value as u8,
        (value >> 8) as u8,
        0xD4,
        0x68,
        0xE4,
        0x68,
        0x77,
        0x13,
        0xC4,
        0x79,
        0xC0,
        0x14,
        0xCE,
        2,
        0xFF,
        0xFF,
        0xB4,
        0x68,
        0xC0,
        immediate as u8,
        (immediate >> 8) as u8,
        0xCA,
        4,
        0xC5,
        0x3A,
        0xE0,
        0xA6,
        0xC5,
        0x3A,
        0xD1,
    ]; // Newly composed low-address program; unrelated operands/branch offsets.
    if partial {
        code[17] = 0xFF;
    }
    if byte_compare {
        code[17] = 0xC4;
        code[21] = 0xFF;
    }
    let mut cpu = Cpu::new();
    cpu.lrb = 0x40;
    cpu.hc = true;
    let mut bus = Bus::new(code, 0x55);
    bus.configure_scoped_access(vec![[0x268, 0x26A], [0x279, 0x27A]], 4096);
    bus.begin_continuity();
    bus.begin_native_accesses();
    bus.start_decision_observer();
    let contract = SliceContract {
        entry_pc: 0,
        exit_pcs: vec![24, 28],
        code_ranges: vec![[0, 24]],
        psw: 0,
        lrb: 0,
        usp: 0,
        instruction_budget: 12,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    };
    fn probe(d: &crate::decoder::Decoded) -> FormAdmission {
        if d.mnemonic == "BRK" {
            FormAdmission::Unsupported
        } else {
            FormAdmission::Allowed
        }
    }
    let result =
        execute_in_state_observed(&mut cpu, &mut bus, &contract, &[], true, Some(probe), true);
    (cpu, bus, result)
}
#[test]
fn invented_native_double_reader_unsigned_compare_and_stop_before_fake_peripheral() {
    for value in [0x122, 0x123, 0x124] {
        let (cpu, mut bus, result) = invented(value, 0x123, false, false);
        assert_eq!(result.status, 0);
        assert_eq!(cpu.pc, if value < 0x123 { 28 } else { 24 });
        assert_eq!(cpu.cf, value < 0x123);
        assert_eq!(cpu.zf, value == 0x123);
        assert!(cpu.hc);
        assert!(!cpu.dd);
        let journal = bus.continuity_snapshot();
        let g = Generation {
            writer_pc: 3,
            event_index: 2,
            write_order: 0,
            value: value as u32,
        };
        assert_eq!(
            reader_generation(&journal, &g, 2, 0x268, 5),
            Some(g.clone())
        );
        assert_eq!(reader_generation(&journal, &g, 2, 0x268, 17), Some(g));
        assert!(!journal.iter().any(|a| a[2] < 128));
        let events = bus.finish_decision_observer();
        let cmp = events.iter().find(|e| e[0] == 17).unwrap();
        assert_eq!(cmp[6], value as u32);
        assert_eq!(cmp[7], 0x123);
        assert_eq!(
            events.iter().find(|e| e[0] == 22).unwrap()[1],
            cpu.pc as u32
        );
    }
}
#[test]
fn invented_same_value_fresh_generation_and_overlap_stale_second_machine_rejected() {
    let (_, bus, _) = invented(0x123, 0x123, false, false);
    let journal = bus.continuity_snapshot();
    let g = Generation {
        writer_pc: 3,
        event_index: 2,
        write_order: 0,
        value: 0x123,
    };
    assert!(reader_generation(&journal, &g, 2, 0x268, 17).is_some());
    assert!(reader_generation(
        &journal,
        &Generation {
            event_index: 1,
            ..g.clone()
        },
        2,
        0x268,
        17
    )
    .is_none());
    let mut overlap = journal.clone();
    let i = overlap.iter().position(|a| a[1] == 17).unwrap();
    overlap.insert(i, [1, 16, 0x269, 8, 1, 1]);
    assert!(reader_generation(&overlap, &g, 2, 0x268, 17).is_none());
    overlap[i] = [0, 65536, 0x268, 16, 1, 0x123];
    assert!(reader_generation(&overlap, &g, 2, 0x268, 17).is_none());
    let second = journal
        .into_iter()
        .filter(|a| a[1] != 3)
        .collect::<Vec<_>>();
    assert!(reader_generation(&second, &g, 2, 0x268, 17).is_none());
}
#[test]
fn invented_wrong_immediate_and_width_do_not_establish_expected_compare() {
    let (_, mut bus, r) = invented(0x123, 0x124, false, false);
    assert_eq!(r.status, 0);
    let e = bus.finish_decision_observer();
    assert_ne!(e.iter().find(|e| e[0] == 17).unwrap()[7], 0x123);
    let (_, bus, r) = invented(0x123, 0x123, false, true);
    assert_eq!(r.status, 1);
    let g = Generation {
        writer_pc: 3,
        event_index: 2,
        write_order: 0,
        value: 0x123,
    };
    assert!(reader_generation(&bus.continuity_snapshot(), &g, 2, 0x268, 17).is_none());
}
#[test]
fn invented_partial_retains_native_writer_and_first_reader_without_second_read() {
    let (_, bus, r) = invented(0x123, 0x123, true, false);
    assert_eq!(r.status, 1);
    assert_eq!(r.stop_pc, 17);
    let g = Generation {
        writer_pc: 3,
        event_index: 2,
        write_order: 0,
        value: 0x123,
    };
    assert!(reader_generation(&bus.continuity_snapshot(), &g, 2, 0x268, 5).is_some());
    assert!(reader_generation(&bus.continuity_snapshot(), &g, 2, 0x268, 17).is_none());
}
use crate::{
    bus::Bus,
    cpu::Cpu,
    exec::{read_data_u8, step, write_data_u8},
};
#[test]
fn exact_byte_rol_off_uses_incoming_carry_and_preserves_noncarry_flags() {
    for dd in [false, true] {
        for old in [0u8, 1, 0x80, 0xFF] {
            for cf in [false, true] {
                for zf in [false, true] {
                    let mut cpu = Cpu::new();
                    cpu.lrb = 0x40;
                    cpu.dd = dd;
                    cpu.cf = cf;
                    cpu.zf = zf;
                    cpu.hc = true;
                    let mut bus = Bus::new(vec![0xC4, 0x75, 0xB7, 0xFF], 85);
                    write_data_u8(&mut cpu, &mut bus, 0x275, old);
                    step(&mut cpu, &mut bus).unwrap();
                    assert_eq!(
                        read_data_u8(&cpu, &mut bus, 0x275),
                        old.wrapping_shl(1) | u8::from(cf)
                    );
                    assert_eq!(cpu.cf, old & 128 != 0);
                    assert_eq!(cpu.zf, zf);
                    assert!(cpu.hc);
                    assert_eq!(cpu.dd, dd);
                }
            }
        }
    }
}
