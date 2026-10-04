//! Invented differentiated words; deliberately not OEM bytes/routine reachability.
use crate::{
    bus::Bus,
    cpu::Cpu,
    data0136_handoff::retained_word,
    exec::{step, write_data_u16, write_data_u8},
};
#[test]
fn invented_four_native_generations_and_indexed_companions_all_slots() {
    for equal in [false, true] {
        for selector in 0u8..4 {
            for pattern in [0, 85, 170] {
                let values = if equal {
                    [321u16; 4]
                } else {
                    [17, 258, 4097, 65530]
                };
                let companions = [0u16, 15, 4096, 99];
                let mut program = vec![0; 96];
                program[..2].copy_from_slice(&[0x90, 0x15]);
                let mut p = 2;
                for (i, value) in values.iter().enumerate() {
                    let address = 0x300u16 + 2 * i as u16;
                    program[p..p + 6].copy_from_slice(&[
                        0x67,
                        *value as u8,
                        (*value >> 8) as u8,
                        0xD0,
                        address as u8,
                        (address >> 8) as u8,
                    ]);
                    p += 6;
                }
                // A different source address/layout, no OEM instruction window.
                program[64..79].copy_from_slice(&[
                    0xF5, 0xF0, 0x53, 0xF8, 0x50, 0xE0, 0, 3, 0xB0, 0x10, 3, 0x82, 0xD4, 0xFE, 0xFF,
                ]);
                let mut cpu = Cpu::new();
                cpu.lrb = 0x20;
                cpu.set_psw_u16(0x1DC9);
                let mut bus = Bus::new(program, pattern);
                write_data_u8(&mut cpu, &mut bus, 0xF0, selector);
                for (i, value) in companions.iter().enumerate() {
                    write_data_u16(&mut cpu, &mut bus, 0x310 + 2 * i as u16, *value);
                }
                let identity = (&cpu as *const Cpu, &bus as *const Bus);
                bus.begin_continuity();
                bus.begin_native_accesses();
                for _ in 0..9 {
                    bus.set_native_pc(cpu.pc);
                    step(&mut cpu, &mut bus).unwrap();
                }
                assert_eq!(cpu.pc, 26);
                cpu.pc = 64; // ONLY disclosed PC scheduling, all RAM retained.
                for _ in 0..7 {
                    bus.set_native_pc(cpu.pc);
                    step(&mut cpu, &mut bus).unwrap();
                }
                assert_eq!(
                    cpu.a,
                    values[selector as usize].wrapping_add(companions[selector as usize])
                );
                assert_eq!(
                    cpu.hc,
                    (values[selector as usize] & 15) + (companions[selector as usize] & 15) > 15
                );
                assert_eq!(identity, (&cpu as *const Cpu, &bus as *const Bus));
                let journal = bus.end_continuity();
                let address = 0x300 + u32::from(selector) * 2;
                let w = journal
                    .iter()
                    .position(|a| a[0] == 1 && a[2] == address && a[4] == 1)
                    .unwrap();
                let read = journal
                    .iter()
                    .position(|a| a[0] == 1 && a[1] == 69 && a[2] == address && a[4] == 0)
                    .unwrap();
                assert!(retained_word(&journal, w, read, address));
                assert_eq!(
                    journal
                        .iter()
                        .filter(|a| a[0] == 1 && a[1] == 69 && a[2] >= 0x300 && a[2] < 0x308)
                        .count(),
                    1
                );
            }
        }
    }
}
#[test]
fn invented_signed_extension_boundary_and_pointer_overflow_refuse() {
    let mut cpu = Cpu::new();
    cpu.set_psw_u16(0x1DC9);
    let mut bus = Bus::new(vec![0xF5, 0xF0, 0x53, 0xF8, 0x50, 0xE0, 0, 3], 0);
    write_data_u8(&mut cpu, &mut bus, 0xF0, 0x40);
    for _ in 0..4 {
        step(&mut cpu, &mut bus).unwrap();
    }
    assert_eq!(cpu.a, 0xFF80);
    assert!(step(&mut cpu, &mut bus).is_err()); // native checked effective address, no wrapping ROM/RAM alias
}
#[test]
fn exact_registry_never_promotes_irq_jgt_or_object_assumptions() {
    for bytes in [
        vec![0x47, 0x81],
        vec![0x45, 0x81],
        vec![0xC8, 0],
        vec![0x02],
        vec![0xA7, 0x12],
    ] {
        let d = crate::decoder::decode(true, |i| *bytes.get(i).unwrap_or(&0)).unwrap();
        assert!(matches!(
            crate::quartet_handoff::admission(&d),
            crate::instruction_forms::FormAdmission::Unsupported
        ));
    }
}
