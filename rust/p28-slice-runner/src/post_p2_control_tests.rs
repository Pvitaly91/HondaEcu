//! Invented decoded probes only. No OEM routine window or table fixture.
use crate::{bus::Bus, cpu::Cpu, exec::step};
#[test]
fn control_native_and_has_four_flags_storage_nonexistent_high_bits_and_zf_only() {
    for flags in 0..16 {
        for dd in [false, true] {
            let mut cpu = Cpu::new();
            cpu.a = 0xBDCA;
            cpu.cf = true;
            cpu.hc = true;
            cpu.dd = dd;
            // A separately invented mask clears two flags, not the OEM mask.
            let mut bus = Bus::new(vec![0xC5, 0x46, 0xD0, 0xF3], 0xAA);
            bus.initialize_post_p2_control(0x8B, flags).unwrap();
            bus.begin_native_accesses();
            bus.begin_write_journal();
            bus.set_control_access(Some((0x46, 0)));
            bus.set_native_pc(0);
            step(&mut cpu, &mut bus).unwrap();
            assert_eq!(bus.post_p2_control(), Some([0x8B, flags & 3]));
            assert_eq!(
                bus.control_accesses(),
                [
                    [0, 0x46, 8, 0, 0xF0 | flags as u32],
                    [0, 0x46, 8, 1, 0xF0 | (flags & 3) as u32]
                ]
            );
            assert_eq!(
                bus.end_write_journal(),
                [[0x46, 8, 0xF0 | (flags & 3) as u32]]
            );
            assert!(bus.end_native_accesses().is_empty());
            assert!(!cpu.zf);
            assert!(cpu.cf && cpu.hc);
            assert_eq!(cpu.dd, dd);
            assert_eq!(cpu.a, 0xBDCA);
        }
    }
}
#[test]
fn stopped_realtime_sb_sets_output_bit_and_reports_old_bit_zf_without_clock_or_irq() {
    for prior in [0x83, 0x87, 0x8B, 0x8F] {
        let mut cpu = Cpu::new();
        cpu.a = 0xABCD;
        cpu.cf = true;
        cpu.hc = true;
        cpu.dd = true;
        let mut bus = Bus::new(vec![0xC5, 0x40, 0x1A], 0x55);
        bus.initialize_post_p2_control(prior, 6).unwrap();
        bus.begin_native_accesses();
        bus.begin_write_journal();
        bus.set_control_access(Some((0x40, 0)));
        bus.set_native_pc(0);
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(bus.post_p2_control(), Some([prior | 4, 6]));
        assert_eq!(cpu.zf, prior & 4 == 0);
        assert!(cpu.cf && cpu.hc && cpu.dd);
        assert_eq!(cpu.a, 0xABCD);
        assert_eq!(
            bus.control_accesses(),
            [
                [0, 0x40, 8, 0, prior as u32],
                [0, 0x40, 8, 0, prior as u32],
                [0, 0x40, 8, 1, (prior | 4) as u32]
            ]
        );
        assert_eq!(bus.end_write_journal(), [[0x40, 8, (prior | 4) as u32]]);
        assert!(bus.end_native_accesses().is_empty());
    }
}
#[test]
fn narrow_storage_does_not_accept_running_timer_modes_or_reserved_flag_snapshot() {
    for t in 0..=255 {
        let mut bus = Bus::new(vec![], 0);
        assert_eq!(
            bus.initialize_post_p2_control(t, 15).is_ok(),
            t & !0x0C == 0x83
        );
    }
    for flags in 16..=255 {
        assert!(Bus::new(vec![], 0)
            .initialize_post_p2_control(0x83, flags)
            .is_err());
    }
}
#[test]
fn disabled_host_wrong_pc_width_neighbor_timer_irq_and_unknown_command_fault_without_storage() {
    let mut bus = Bus::new(vec![], 0xAA);
    bus.initialize_post_p2_control(0x8B, 15).unwrap();
    bus.set_control_access(Some((0x46, 7)));
    bus.set_native_pc(7);
    bus.write_data_u8(0x46, 0);
    assert!(bus.take_fault().is_some());
    bus.begin_native_accesses();
    bus.set_native_pc(8);
    bus.write_data_u8(0x46, 0);
    assert!(bus.take_fault().is_some());
    bus.set_native_pc(7);
    for addr in [0x40, 0x41, 0x42, 0x45, 0x47, 0x30, 0x32, 0x18, 0x19, 0x7F] {
        bus.read_data_u8(addr);
        assert!(bus.take_fault().is_some());
        bus.write_data_u8(addr, 1);
        assert!(bus.take_fault().is_some());
    }
    for addr in [0x40, 0x46, 0x45] {
        bus.read_data_u16(addr);
        assert!(bus.take_fault().is_some());
        bus.write_data_u16(addr, 0);
        assert!(bus.take_fault().is_some());
    }
    assert_eq!(bus.post_p2_control(), Some([0x8B, 15]));
    assert!(bus.control_accesses().is_empty());
    bus.set_control_access(None);
    bus.read_data_u8(0x46);
    assert!(bus.take_fault().is_some());
    let mut second = Bus::new(vec![], 0);
    second.begin_native_accesses();
    second.set_control_access(Some((0x46, 7)));
    second.set_native_pc(7);
    second.write_data_u8(0x46, 0);
    assert!(second.take_fault().is_some());
    assert_eq!(second.post_p2_control(), None);
}
#[test]
fn same_value_writes_retained_across_scope_and_no_host_reinitialize_or_fake_command_latch() {
    let mut bus = Bus::new(vec![], 0);
    bus.initialize_post_p2_control(0x87, 3).unwrap();
    assert!(bus.initialize_post_p2_control(0x87, 3).is_err());
    for pc in [5, 9] {
        bus.begin_native_accesses();
        bus.begin_write_journal();
        bus.set_control_access(Some((0x46, pc)));
        bus.set_native_pc(pc);
        assert_eq!(bus.read_data_u8(0x46), 0xF3);
        bus.write_data_u8(0x46, 3);
        assert_eq!(bus.read_data_u8(0x46), 0xF3);
        assert_eq!(bus.end_write_journal(), [[0x46, 8, 3]]);
        assert!(bus.end_native_accesses().is_empty());
        bus.set_control_access(None);
        assert_eq!(bus.post_p2_control(), Some([0x87, 3]));
    }
}
#[test]
fn control_side_effect_requests_are_refused_but_existing_word_ie_capability_is_separate() {
    let mut bus = Bus::new(vec![], 0);
    bus.initialize_post_p2_control(0x8B, 0).unwrap();
    bus.begin_native_accesses();
    bus.set_control_access(Some((0x40, 0)));
    bus.set_native_pc(0);
    for value in [0x9B, 0x89, 0x83, 0x0B] {
        bus.write_data_u8(0x40, value);
        assert!(bus.take_fault().is_some());
        assert_eq!(bus.post_p2_control(), Some([0x8B, 0]));
    }
    bus.set_adaptive_ie(Some(0x4321));
    bus.write_data_u16(0x1A, 0x9876);
    assert!(bus.take_fault().is_none());
    assert_eq!(bus.adaptive_ie(), Some(0x9876));
}
#[test]
fn invented_native_producer_branch_p2_and_control_chain_stays_in_one_machine() {
    use crate::{
        instruction_forms::FormAdmission,
        runner::{execute_in_state_observed, SliceContract},
    };
    for value in [0x122u16, 0x123, 0x124] {
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
            1,
            0xCA,
            10,
            0x77,
            0xA0,
            0xC5,
            0x24,
            0xD1,
            0xC5,
            0x46,
            0xD0,
            0xF3,
            0xFF,
            0x77,
            0x0F,
            0xC5,
            0x24,
            0xE1,
            0xC5,
            0x40,
            0x1A,
        ];
        let mut cpu = Cpu::new();
        cpu.lrb = 0x40;
        let mut bus = Bus::new(code, 0x55);
        let identity = (&cpu as *const Cpu, &bus as *const Bus);
        bus.configure_scoped_access(
            vec![
                [0, 8],
                [0x24, 0x25],
                [0x40, 0x41],
                [0x46, 0x47],
                [0x266, 0x268],
            ],
            4096,
        );
        bus.initialize_p2_output_latch(0x81).unwrap();
        bus.initialize_post_p2_control(0x83, 15).unwrap();
        bus.set_p2_access(true);
        bus.begin_native_accesses();
        bus.begin_continuity();
        let c = SliceContract {
            entry_pc: 0,
            exit_pcs: vec![17, 27],
            code_ranges: vec![[0, 17], [22, 27]],
            psw: 0,
            lrb: 0,
            usp: 0,
            instruction_budget: 8,
            data_seeds: vec![],
            output_addresses: vec![],
            program_read_range: None,
        };
        assert_eq!(
            execute_in_state_observed(
                &mut cpu,
                &mut bus,
                &c,
                &[],
                true,
                Some(|_| FormAdmission::Allowed),
                true
            )
            .status,
            0
        );
        let pc = cpu.pc;
        bus.set_p2_access(false);
        bus.set_control_access(Some((if pc == 17 { 0x46 } else { 0x40 }, pc)));
        let next = SliceContract {
            entry_pc: pc,
            exit_pcs: vec![21, 30],
            code_ranges: vec![[17, 21], [27, 30]],
            instruction_budget: 1,
            ..c
        };
        assert_eq!(
            execute_in_state_observed(
                &mut cpu,
                &mut bus,
                &next,
                &[],
                true,
                Some(crate::post_p2_control::admission),
                true
            )
            .status,
            0
        );
        assert_eq!(identity, (&cpu as *const Cpu, &bus as *const Bus));
        assert_eq!(
            bus.p2_output_latch(),
            Some(if value < 0x123 { 0x8F } else { 0x80 })
        );
        assert_eq!(
            bus.post_p2_control(),
            Some(if value < 0x123 { [0x87, 15] } else { [0x83, 3] })
        );
        assert_eq!(bus.control_accesses().last().unwrap()[0], pc as u32);
        assert!(bus
            .continuity_snapshot()
            .iter()
            .any(|a| a[1] == 3 && a[2] == 0x266 && a[4] == 1));
    }
}
