//! Invented decoded probes only; no OEM instruction window.
use crate::{bus::Bus, cpu::Cpu, exec::step};

#[test]
fn p2_invented_native_producer_compare_branch_mask_and_output_data_chain() {
    use crate::{
        instruction_forms::FormAdmission,
        runner::{execute_in_state_observed, SliceContract},
    };
    for value in [0x122u16, 0x123, 0x124] {
        // Newly composed low-address program and unrelated software word.
        let code = vec![
            0x67,
            value as u8,
            (value >> 8) as u8,
            0xD4,
            0x66,
            0xB4,
            0x66,
            0xC0,
            0x23,
            0x01,
            0xCA,
            8,
            0x77,
            0xA0,
            0xC5,
            0x24,
            0xD1,
            0xFF,
            0xFF,
            0xFF,
            0x77,
            0x0F,
            0xC5,
            0x24,
            0xE1,
        ];
        let mut bus = Bus::new(code, 0x55);
        let mut cpu = Cpu::new();
        cpu.lrb = 0x40;
        bus.configure_scoped_access(vec![[0, 8], [0x24, 0x25], [0x266, 0x268]], 4096);
        bus.initialize_p2_output_latch(0x81).unwrap();
        bus.set_p2_access(true);
        bus.begin_native_accesses();
        bus.begin_continuity();
        let c = SliceContract {
            entry_pc: 0,
            exit_pcs: vec![17, 25],
            code_ranges: vec![[0, 17], [20, 25]],
            psw: 0,
            lrb: 0,
            usp: 0,
            instruction_budget: 8,
            data_seeds: vec![],
            output_addresses: vec![],
            program_read_range: None,
        };
        let r = execute_in_state_observed(
            &mut cpu,
            &mut bus,
            &c,
            &[],
            true,
            Some(|_| FormAdmission::Allowed),
            true,
        );
        assert_eq!(r.status, 0);
        assert_eq!(cpu.pc, if value < 0x123 { 25 } else { 17 });
        let old = bus.p2_accesses()[0];
        let new = bus.p2_accesses()[1];
        assert_eq!(old[4], 0x81);
        assert_eq!(new[4], if value < 0x123 { 0x8F } else { 0x80 });
        assert_eq!(old[0], if value < 0x123 { 22 } else { 14 });
        let j = bus.continuity_snapshot();
        assert!(j.iter().any(|a| a[1] == 3 && a[2] == 0x266 && a[4] == 1));
        assert!(j.iter().any(|a| a[1] == 5 && a[2] == 0x266 && a[4] == 0));
    }
}

#[test]
fn p2_native_byte_rmw_preserves_a_cf_hc_dd_and_journals_old_then_new() {
    for op in [0xD1, 0xE1] {
        for dd in [false, true] {
            for old in [0, 0xA5, 0xFF] {
                let mut bus = Bus::new(vec![0xC5, 0x24, op], 0x55);
                let mut cpu = Cpu::new();
                cpu.a = 0xBE69;
                cpu.cf = true;
                cpu.hc = true;
                cpu.dd = dd;
                bus.initialize_p2_output_latch(old).unwrap();
                bus.set_p2_access(true);
                bus.begin_native_accesses();
                bus.begin_p2_accesses();
                bus.set_native_pc(0);
                step(&mut cpu, &mut bus).unwrap();
                let expected = if op == 0xD1 { old & 0x69 } else { old | 0x69 };
                assert_eq!(bus.p2_output_latch(), Some(expected));
                assert_eq!(cpu.a, 0xBE69);
                assert_eq!(cpu.zf, expected == 0);
                assert!(cpu.cf && cpu.hc);
                assert_eq!(cpu.dd, dd);
                assert_eq!(
                    bus.p2_accesses(),
                    vec![
                        [0, 0x24, 8, 0, old as u32],
                        [0, 0x24, 8, 1, expected as u32]
                    ]
                );
                assert!(!bus.end_native_accesses().iter().any(|a| a[1] == 0x24));
            }
        }
    }
}
#[test]
fn p2_latch_is_retained_without_host_reseed_and_same_value_native_write_is_real() {
    let mut bus = Bus::new(vec![0xC5, 0x24, 0xE1, 0xC5, 0x24, 0xD1], 0);
    let mut cpu = Cpu::new();
    cpu.a = 0x20;
    bus.initialize_p2_output_latch(0xA1).unwrap();
    bus.set_p2_access(true);
    bus.begin_native_accesses();
    bus.set_native_pc(0);
    step(&mut cpu, &mut bus).unwrap();
    bus.end_native_accesses();
    bus.set_p2_access(false);
    assert_eq!(bus.p2_output_latch(), Some(0xA1));
    assert!(bus.initialize_p2_output_latch(0xA1).is_err());
    bus.set_p2_access(true);
    bus.begin_native_accesses();
    bus.set_native_pc(3);
    cpu.a = 0xF0;
    step(&mut cpu, &mut bus).unwrap();
    assert_eq!(bus.p2_output_latch(), Some(0xA0));
    assert_eq!(bus.p2_accesses()[2], [3, 0x24, 8, 0, 0xA1]);
    assert_eq!(bus.p2_accesses().len(), 4);
}
#[test]
fn p2_disabled_host_overwrite_wrong_width_neighbors_direction_and_unknown_sfr_fail() {
    let mut bus = Bus::new(vec![], 0xFF);
    bus.initialize_p2_output_latch(0x5A).unwrap();
    bus.write_data_u8(0x24, 0xFF);
    assert!(bus.take_fault().is_some());
    assert_eq!(bus.p2_output_latch(), Some(0x5A));
    bus.set_p2_access(true);
    bus.write_data_u8(0x24, 0);
    assert!(bus.take_fault().is_some());
    bus.begin_native_accesses();
    for address in [0x25, 0x26, 0x27, 0x31] {
        bus.read_data_u8(address);
        assert!(bus.take_fault().is_some());
        bus.write_data_u8(address, 1);
        assert!(bus.take_fault().is_some());
    }
    bus.read_data_u16(0x24);
    assert!(bus.take_fault().is_some());
    bus.write_data_u16(0x24, 0);
    assert!(bus.take_fault().is_some());
    assert_eq!(bus.p2_output_latch(), Some(0x5A));
    bus.set_p2_access(false);
    bus.read_data_u8(0x24);
    assert!(bus.take_fault().is_some());
}
#[test]
fn p2_second_machine_does_not_inherit_capability_or_latch_and_p1_is_separate() {
    let mut first = Bus::new(vec![], 0);
    first.initialize_p2_output_latch(0xA5).unwrap();
    first.set_p1_output_latch(Some(0x7B));
    first.set_p2_access(false);
    assert_eq!(first.read_data_u8(0x22), 0x7B);
    assert!(first.take_fault().is_none());
    assert_eq!(first.p2_output_latch(), Some(0xA5));
    let mut second = Bus::new(vec![], 0xA5);
    second.set_p2_access(true);
    second.begin_native_accesses();
    second.read_data_u8(0x24);
    assert!(second.take_fault().is_some());
    assert_eq!(second.p2_output_latch(), None);
}
