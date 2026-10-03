//! Invented composition, not an OEM instruction sequence or scheduler.
use crate::{bus::Bus, cpu::Cpu, data0136_handoff::retained_word, exec::step};

fn execute(cpu: &mut Cpu, bus: &mut Bus, count: usize) {
    bus.begin_native_accesses();
    for _ in 0..count {
        bus.set_native_pc(cpu.pc);
        step(cpu, bus).unwrap();
        assert!(bus.take_fault().is_none());
    }
    bus.end_native_accesses();
}
#[test]
fn invented_one_machine_scheduled_positive_and_zero_transfer() {
    for value in [0u16, 321] {
        // Invented producer at0 and consumer at16. The intervening code is skipped explicitly.
        let mut program = vec![0u8; 26];
        program[..7].copy_from_slice(&[0x62, 0, 3, 0x67, value as u8, (value >> 8) as u8, 0xD2]);
        program[16..26].copy_from_slice(&[0xE2, 0x46, 0x8A, 0x44, 0x15, 0x67, 2, 4, 0x90, 0x37]);
        let mut cpu = Cpu::new();
        cpu.lrb = 0x43;
        let mut bus = Bus::new(program, 0x55);
        let identity = (&cpu as *const Cpu, &bus as *const Bus);
        bus.begin_continuity();
        execute(&mut cpu, &mut bus, 3);
        assert_eq!(cpu.pc, 7);
        cpu.pc = 16; // Disclosed PC-only harness ABI transition; RAM unchanged.
        execute(&mut cpu, &mut bus, 4);
        assert_eq!(cpu.pc, 24);
        if value > 0 {
            execute(&mut cpu, &mut bus, 1);
            assert_eq!(cpu.a, 3);
        } // Zero: stop BEFORE DIV.
        assert_eq!(identity, (&cpu as *const Cpu, &bus as *const Bus));
        let journal = bus.end_continuity();
        let writer = journal
            .iter()
            .position(|a| *a == [1, 6, 0x300, 16, 1, u32::from(value)])
            .unwrap();
        let reader = journal
            .iter()
            .position(|a| *a == [1, 16, 0x300, 16, 0, u32::from(value)])
            .unwrap();
        assert!(retained_word(&journal, writer, reader, 0x300));
        assert!(journal.contains(&[1, 17, 0x21C, 16, 1, u32::from(value)]));
        assert_eq!(
            journal.contains(&[1, 24, 0x21C, 16, 0, u32::from(value)]),
            value > 0
        );
        assert_eq!(bus.read_data_u8(0x350), 0x55);
    }
}
#[test]
fn invented_equal_value_new_store_invalidates_old_generation_and_hidden_reseed() {
    let mut cpu = Cpu::new();
    let mut bus = Bus::new(vec![0x62, 0, 3, 0x67, 65, 1, 0xD2, 0xD2, 0xE2], 0);
    bus.begin_continuity();
    execute(&mut cpu, &mut bus, 5);
    let journal = bus.end_continuity();
    let first = journal
        .iter()
        .position(|a| a[1] == 6 && a[4] == 1 && a[2] == 0x300)
        .unwrap();
    let second = journal
        .iter()
        .position(|a| a[1] == 7 && a[4] == 1 && a[2] == 0x300)
        .unwrap();
    let read = journal
        .iter()
        .position(|a| a[1] == 8 && a[4] == 0 && a[2] == 0x300)
        .unwrap();
    assert!(!retained_word(&journal, first, read, 0x300));
    assert!(retained_word(&journal, second, read, 0x300));
    for (address, width) in [(0x300, 8), (0x301, 8), (0x300, 16), (0x2FF, 16)] {
        let mut forged = journal.clone();
        forged.insert(read, [0, 65536, address, width, 1, 321]);
        assert!(!retained_word(&forged, second, read + 1, 0x300));
    }
}
#[test]
fn invented_second_machine_copy_is_not_same_machine_evidence() {
    let mut cpu = Cpu::new();
    let mut bus = Bus::new(vec![0x62, 0, 3, 0x67, 65, 1, 0xD2], 0);
    bus.begin_continuity();
    execute(&mut cpu, &mut bus, 3);
    let producer = bus.end_continuity();
    let mut other_cpu = Cpu::new();
    let mut other_bus = Bus::new(vec![0x62, 0, 3, 0xE2], 0);
    other_bus.begin_continuity();
    other_bus.write_data_u16(0x300, 321);
    execute(&mut other_cpu, &mut other_bus, 2);
    let consumer = other_bus.end_continuity();
    assert_ne!(
        (&cpu as *const Cpu, &bus as *const Bus),
        (&other_cpu as *const Cpu, &other_bus as *const Bus)
    );
    assert!(producer
        .iter()
        .any(|a| a[0] == 1 && a[2] == 0x300 && a[4] == 1));
    assert!(!consumer
        .iter()
        .any(|a| a[0] == 1 && a[2] == 0x300 && a[4] == 1));
    assert!(consumer
        .iter()
        .any(|a| a[0] == 0 && a[2] == 0x300 && a[4] == 1));
}
