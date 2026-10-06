//! Invented low-address programs and narrow bus guards, never OEM windows.
use crate::{
    bus::{Bus, CaptureObservation},
    cpu::Cpu,
    exec::{read_data_u16, read_data_u8, step, write_data_u16, write_data_u8},
    fallthrough_data0136 as caller,
};

#[test]
fn invented_native_call_no_write_keeps_the_frame_and_live_nonmaterial_abi() {
    let mut rom = vec![0xFF; 128];
    rom[0x12..0x15].copy_from_slice(&[0xEB, 0xD7, 32]); // invented source, taken path unused
    rom[0x15..0x18].copy_from_slice(&[0xC4, 0xD9, 8]);
    rom[0x18..0x1A].copy_from_slice(&[0xC9, 8]);
    rom[0x22..0x25].copy_from_slice(&[0x32, 0x60, 0]);
    // Differently composed invented producer; no mode/index/writer path.
    rom[0x60..0x66].copy_from_slice(&[0xE5, 0x3A, 0x8A, 0xC4, 0xD8, 0x1B]);
    rom[0x66..0x68].copy_from_slice(&[0xC9, 3]);
    rom[0x6B..0x71].copy_from_slice(&[0x36, 0xD5, 0xCE, 0xC5, 0xD1, 0x15]);
    let mut cpu = Cpu::new();
    cpu.pc = 0x12;
    cpu.ssp = 0x7E6;
    cpu.lrb = 0x21;
    cpu.set_psw_u16(0x8DCA);
    cpu.a = 0xBEEF;
    let mut bus = Bus::new(rom, 0);
    write_data_u16(&mut cpu, &mut bus, 0x96, 0x1345);
    write_data_u16(&mut cpu, &mut bus, 0x136, 0x6B29);
    let identity = (&cpu as *const Cpu, &bus as *const Bus);
    bus.observe_capture(Some(CaptureObservation {
        tmr2: 0xF234,
        irqh: 0x55,
        tcon2: 0xAA,
    }));
    bus.begin_native_accesses();
    bus.begin_all_native();
    bus.begin_write_journal();
    let mut pcs = vec![];
    while cpu.pc != 0x71 {
        let pc = cpu.pc;
        bus.set_native_pc(pc);
        step(&mut cpu, &mut bus).unwrap();
        pcs.push(pc);
        assert!(pcs.len() < 20);
    }
    let accesses = bus.end_native_accesses();
    let writes = bus.end_write_journal();
    assert_eq!(identity, (&cpu as *const Cpu, &bus as *const Bus));
    assert_eq!(cpu.ssp, 0x7E4);
    assert_eq!(read_data_u16(&cpu, &mut bus, 0x7E6), 0x25);
    assert_eq!(read_data_u16(&cpu, &mut bus, 0x96), 0x1345);
    assert_eq!(cpu.a, 0xF234);
    assert_eq!(read_data_u16(&cpu, &mut bus, 0xCE), 0xF234);
    assert_eq!(read_data_u16(&cpu, &mut bus, 0x136), 0x6B29);
    assert!(writes.contains(&[0x7E6, 16, 0x25]));
    assert!(!accesses
        .iter()
        .any(|a| a[1] == 0x136 || a[1] == 0x42 || a[1] == 0x19));
    assert_eq!(bus.peripheral_accesses(), [[0x3A, 16, 0, 0xF234]]);
    assert!(!pcs.contains(&0x68));
    assert!(bus.take_fault().is_none());
}

#[test]
fn narrow_caller_capture_has_real_pc_width_and_conditional_irq_source() {
    let cpu = Cpu::new();
    let mut bus = Bus::new(vec![], 0xAA);
    for (timer, irq) in [(0x8123, None), (123, Some(0)), (456, Some(1))] {
        bus.observe_no_write_capture(timer, irq);
        bus.configure_scoped_access(vec![[0x19, 0x1A], [0x3A, 0x3C]], 32);
        bus.begin_native_accesses();
        bus.begin_all_native();
        bus.set_native_pc(0x56BE);
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x3A), timer);
        if let Some(v) = irq {
            bus.set_native_pc(0x56C9);
            assert_eq!(read_data_u8(&cpu, &mut bus, 0x19), v);
        }
        let all = bus.end_all_native();
        assert_eq!(all[0], [3, 0x56BE, 0x3A, 16, 0, timer as u32]);
        assert_eq!(all.len(), if irq.is_some() { 2 } else { 1 });
        bus.end_native_accesses();
        assert!(bus.take_fault().is_none());
    }
}

#[test]
fn no_unprovided_tcon2_irq_wrong_width_detached_source_or_peripheral_write() {
    let mut cpu = Cpu::new();
    let mut bus = Bus::new(vec![], 0xAA);
    bus.observe_no_write_capture(0x8123, None);
    bus.configure_scoped_access(vec![[0x19, 0x1A], [0x3A, 0x3C], [0x42, 0x43]], 64);
    bus.begin_native_accesses();
    bus.set_native_pc(0x56BE);
    read_data_u8(&cpu, &mut bus, 0x3A);
    assert!(bus.take_fault().is_some());
    read_data_u16(&cpu, &mut bus, 0x19);
    assert!(bus.take_fault().is_some());
    read_data_u8(&cpu, &mut bus, 0x42);
    assert!(bus.take_fault().is_some());
    bus.set_native_pc(0x56C9);
    read_data_u8(&cpu, &mut bus, 0x19);
    assert!(bus.take_fault().is_some());
    bus.set_native_pc(0x65);
    read_data_u16(&cpu, &mut bus, 0x3A);
    assert!(bus.take_fault().is_some());
    write_data_u16(&mut cpu, &mut bus, 0x3A, 99);
    assert!(bus.take_fault().is_some());
    write_data_u8(&mut cpu, &mut bus, 0x19, 1);
    assert!(bus.take_fault().is_some());
    assert!(bus.all_native_snapshot().is_empty());
    // Historical capture diagnostics retain rejected write attempts, never as
    // successful effects. No unprovided read was logged and storage is frozen.
    assert!(bus.peripheral_accesses().iter().all(|a| a[2] == 1));
    bus.set_native_pc(0x56BE);
    assert_eq!(read_data_u16(&cpu, &mut bus, 0x3A), 0x8123);
    assert!(bus.take_fault().is_none());
}

#[test]
fn in_state_helper_refuses_bad_entry_mode_slot_or_existing_fresh_gate_without_repair() {
    for fault in 0..4 {
        let mut cpu = Cpu::new();
        cpu.pc = 0x56BE;
        cpu.lrb = 0x21;
        cpu.set_psw_u16(0xCDCA);
        cpu.ssp = 0x7FC;
        let mut bus = Bus::new(vec![], 0);
        match fault {
            0 => cpu.pc = 0x64C,
            1 => write_data_u8(&mut cpu, &mut bus, 0x11F, 4),
            2 => write_data_u8(&mut cpu, &mut bus, 0xA2, 0x55),
            _ => write_data_u8(&mut cpu, &mut bus, 0x128, 8),
        };
        let before = (cpu.pc, cpu.a, cpu.psw_u16(), cpu.lrb, cpu.ssp);
        assert!(caller::execute_no_write_body(
            &mut cpu,
            &mut bus,
            &caller::Observation {
                tmr2: 0x8000,
                irqh: None
            }
        )
        .is_err());
        assert_eq!(before, (cpu.pc, cpu.a, cpu.psw_u16(), cpu.lrb, cpu.ssp));
        assert!(bus.end_native_accesses().is_empty());
        assert!(bus.peripheral_accesses().is_empty());
    }
}

#[test]
fn invented_jeq_old_zero_bit_and_jne_clear_bit_flags_not_host_branches() {
    for old in [0u8, 1, 8, 9] {
        let mut cpu = Cpu::new();
        cpu.lrb = 0x21;
        cpu.set_psw_u16(0x8DCA);
        let mut bus = Bus::new(vec![0xC4, 0xD7, 8, 0xC9, 2], 0);
        write_data_u8(&mut cpu, &mut bus, 0x1D7, old);
        bus.begin_native_accesses();
        bus.set_native_pc(0);
        step(&mut cpu, &mut bus).unwrap();
        bus.set_native_pc(3);
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(cpu.pc, if old & 1 == 0 { 7 } else { 5 });
        assert_eq!(read_data_u8(&cpu, &mut bus, 0x1D7), old & !1);
        assert!(bus.take_fault().is_none());
    }
}
