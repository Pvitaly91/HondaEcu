use crate::{
    bus::Bus,
    cpu::Cpu,
    exec::{read_data_u8, step, write_data_u8},
    quartet_handoff::Generation,
};

#[test]
fn invented_low_address_counter_retains_generations_through_explicit_schedules() {
    // Different five-instruction composition and local-register storage;
    // not the OEM eight-instruction post-return window or actual M2ae coverage.
    for initial in 0u8..4 {
        for pattern in [0, 0x55, 0xAA] {
            let mut cpu = Cpu::new();
            let mut bus = Bus::new(vec![0x78, 0xA8, 0x78, 0xD6, 3, 0x88], pattern);
            cpu.lrb = 0x43;
            cpu.a = 0xBE00;
            cpu.set_psw_u16(0xA333);
            write_data_u8(&mut cpu, &mut bus, 0x218, initial); // once only
            let identity = (&cpu as *const Cpu, &bus as *const Bus);
            let mut current = initial;
            let mut prior: Option<Generation> = None;
            let mut generations = vec![];
            for event in 0..5 {
                cpu.pc = 0; // explicitly disclosed toy event schedule, not host data
                bus.begin_native_accesses();
                bus.begin_all_native();
                bus.begin_continuity();
                while cpu.pc != 6 {
                    let pc = cpu.pc;
                    bus.set_native_pc(pc);
                    step(&mut cpu, &mut bus).unwrap();
                }
                let accesses = bus.end_native_accesses();
                let all = bus.end_all_native();
                let continuity = bus.end_continuity();
                assert_eq!(accesses[0], [0, 0x218, 8, 0, u32::from(current)]);
                assert!(continuity.iter().all(|a| a[0] == 1)); // no host source after init
                if let Some(g) = &prior {
                    assert_eq!(g.value, accesses[0][4]);
                    assert_eq!(g.event_index + 1, event);
                }
                current = (current + 1) % 4;
                let writes: Vec<_> = all.iter().filter(|a| a[4] == 1).collect();
                assert_eq!(writes.len(), 2);
                assert_eq!(*writes[1], [0, 5, 0x218, 8, 1, u32::from(current)]);
                let g = Generation {
                    writer_pc: 5,
                    event_index: event,
                    write_order: 1,
                    value: u32::from(current),
                };
                generations.push(g.clone());
                prior = Some(g);
                assert_eq!(read_data_u8(&cpu, &mut bus, 0x218), current);
                assert_eq!(read_data_u8(&cpu, &mut bus, 0x219), pattern);
                assert_eq!(cpu.a & 0xFF00, 0xBE00);
                assert_eq!(cpu.ssp, 0x7FE);
                assert_eq!(identity, (&cpu as *const Cpu, &bus as *const Bus));
            }
            assert_eq!(generations[0].value, generations[4].value);
            assert_ne!(generations[0], generations[4]); // numeric equality is not identity
        }
    }
}

#[test]
fn invented_sbr_off_page_uses_low_three_accumulator_bits_and_only_old_bit_zero_flag() {
    // Isolated generic form with invented page/address, not an OEM sequence.
    let mut cpu = Cpu::new();
    let mut bus = Bus::new(vec![0xC4, 0xD3, 0x11], 0xA5);
    for old in 0u16..=255 {
        for bit in 0u16..8 {
            for dd in [false, true] {
                cpu.pc = 0;
                cpu.lrb = 0x43;
                cpu.a = 0xBEF8 | bit;
                cpu.set_psw_u16(0xA333);
                cpu.dd = dd;
                let preserved = cpu.psw_u16() & !Cpu::PSW_ZF_BIT;
                write_data_u8(&mut cpu, &mut bus, 0x2D3, old as u8);
                bus.begin_native_accesses();
                bus.set_native_pc(0);
                let d = step(&mut cpu, &mut bus).unwrap();
                let next = old | (1 << bit);
                assert_eq!((d.mnemonic, d.len), ("SBR off N8", 3));
                assert_eq!(
                    bus.end_native_accesses(),
                    [
                        [0, 0x2D3, 8, 0, u32::from(old)],
                        [0, 0x2D3, 8, 1, u32::from(next)]
                    ]
                );
                assert_eq!(cpu.zf, old & (1 << bit) == 0);
                assert_eq!(cpu.psw_u16() & !Cpu::PSW_ZF_BIT, preserved);
                assert_eq!(cpu.a, 0xBEF8 | bit);
                assert_eq!(read_data_u8(&cpu, &mut bus, 0x2D4), 0xA5);
            }
        }
    }
}

#[test]
fn selector_ram_guard_refuses_reseed_wrong_pc_word_overlap_and_keeps_partial_storage() {
    // Capability-only probe; marking a native PC here is NOT execution proof.
    for initial in 0..4 {
        let mut bus = Bus::new(vec![], 0xA5);
        bus.initialize_retained_selector(initial).unwrap();
        assert!(bus.initialize_retained_selector(initial).is_err());
        bus.write_data_u8(0x13C, 3);
        assert!(bus.take_fault().is_some());
        assert_eq!(bus.read_data_u8(0x13C), initial);
        for address in [0x13B, 0x13C] {
            bus.write_data_u16(address, 0);
            assert!(bus.take_fault().is_some());
        }
        assert_eq!(bus.read_data_u8(0x13B), 0xA5);
        assert_eq!(bus.read_data_u8(0x13D), 0xA5);
        bus.begin_native_accesses();
        bus.set_native_pc(0x0648);
        bus.write_data_u8(0x13C, 2);
        assert!(bus.take_fault().is_some());
        assert!(bus.end_native_accesses().is_empty());
        bus.begin_native_accesses();
        bus.set_native_pc(0x064A);
        bus.write_data_u8(0x13C, 2);
        assert_eq!(bus.end_native_accesses(), [[0x064A, 0x13C, 8, 1, 2]]);
        assert_eq!(bus.read_data_u8(0x13C), 2); // stopping never rolls back native store
        bus.write_data_u8(0x13C, initial);
        assert!(bus.take_fault().is_some());
        assert_eq!(bus.read_data_u8(0x13C), 2);
    }
    let mut bus = Bus::new(vec![], 0);
    assert!(bus.initialize_retained_selector(4).is_err());
}
