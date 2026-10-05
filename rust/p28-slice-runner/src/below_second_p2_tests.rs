use crate::{
    bus::Bus,
    cpu::Cpu,
    decoder::decode,
    exec::{step, write_data_u8},
    instruction_forms::FormAdmission,
};

#[test]
fn invented_output_control_byte_rol_branch_second_output_stops_before_return() {
    // Differently composed invented low-address program, not an OEM window.
    // Initial byte source is ordinary RAM. Native branches, no host PC after start.
    let program = vec![
        0x77, 0x21, 0xC5, 0x24, 0xE1, 0xC5, 0x40, 0x1A, 0xF5, 0xC8, 0xF6, 0x80, 0xC5, 0x06, 0x2F,
        0x33, 0xCE, 2, 0x77, 0x99, 0xC5, 0x24, 0xD1, 0x01,
    ];
    for source in [0u8, 0x7F, 0x80, 0xFF] {
        let mut cpu = Cpu::new();
        cpu.a = 0xBEEF;
        cpu.set_psw_u16(0x2335);
        let mut bus = Bus::new(program.clone(), 0x55);
        write_data_u8(&mut cpu, &mut bus, 0xC8, source);
        bus.initialize_p2_output_latch(0xA4).unwrap();
        bus.initialize_post_p2_control(0x83, 15).unwrap();
        bus.begin_continuity();
        bus.begin_all_native();
        bus.begin_native_accesses();
        let mut pcs = vec![];
        let mut rol = None;
        while cpu.pc != 23 {
            let pc = cpu.pc;
            bus.set_native_pc(pc);
            bus.set_p2_access_pc(if matches!(pc, 2 | 20) { Some(pc) } else { None });
            bus.set_control_access(if pc == 5 { Some((0x40, 5)) } else { None });
            let before = (cpu.a, cpu.psw_u16());
            let d = step(&mut cpu, &mut bus).unwrap();
            pcs.push(pc);
            if pc == 15 {
                assert_eq!(d.mnemonic, "ROLB A");
                rol = Some((before, cpu.a, cpu.psw_u16()));
            }
            assert!(pcs.len() < 14);
        }
        let (before, a, p) = rol.unwrap();
        let al = source ^ 0x80;
        assert_eq!(
            a,
            0xBE00 | (((al as u16) * 2 + u16::from(al & 128 != 0)) & 255)
        );
        assert_eq!(p & !0x8000, before.1 & !0x8000);
        assert!(pcs.contains(&20));
        assert!(!pcs.contains(&23));
        assert_eq!(cpu.ssp, 0x7FE);
        let all = bus.end_all_native();
        let p2: Vec<_> = all.iter().filter(|v| v[0] == 1).collect();
        assert_eq!(p2.len(), 4);
        assert_eq!(p2[0][5], 0xA4);
        assert_eq!(p2[1][5], 0xA5);
        assert_eq!(p2[2][5], 0xA5);
        assert_eq!(
            all.iter()
                .filter(|v| v[4] == 1)
                .map(|v| v[1])
                .collect::<Vec<_>>(),
            [2, 5, 20]
        );
    }
}
#[test]
fn second_p2_exact_pc_width_neighbor_and_host_refusal_preserve_retained_value() {
    let mut bus = Bus::new(vec![], 0);
    bus.initialize_p2_output_latch(0xA5).unwrap();
    bus.set_p2_access_pc(Some(123));
    assert_eq!(bus.read_data_u8(0x24), 0);
    assert!(bus.take_fault().is_some());
    bus.begin_native_accesses();
    bus.set_native_pc(122);
    bus.write_data_u8(0x24, 0);
    assert!(bus.take_fault().is_some());
    bus.set_native_pc(123);
    assert_eq!(bus.read_data_u8(0x24), 0xA5);
    for address in [0x23, 0x25, 0x26, 0x30, 0x18] {
        bus.read_data_u8(address);
        assert!(bus.take_fault().is_some());
    }
    bus.write_data_u16(0x24, 0);
    assert!(bus.take_fault().is_some());
    assert_eq!(bus.p2_output_latch(), Some(0xA5));
    assert!(bus.initialize_p2_output_latch(0xA5).is_err());
}
#[test]
fn new_admission_is_exact_dd0_and_does_not_promote_related_rotations() {
    for (bytes, dd, allowed) in [
        (vec![0x33], false, true),
        (vec![0x33], true, false),
        (vec![0x43], false, false),
        (vec![0xC4, 0x10, 0xB7], false, false),
        (vec![0x47, 0x81], true, false),
        (vec![0x45, 0x81], true, false),
    ] {
        let d = decode(dd, |i| bytes.get(i).copied().unwrap_or(0)).unwrap();
        assert_eq!(
            crate::below_second_p2::admission(&d) == FormAdmission::Allowed,
            allowed
        );
    }
}
#[test]
fn merged_word_ram_journal_has_one_architectural_entry_not_shadow_byte_accesses() {
    let mut bus = Bus::new(vec![], 0);
    bus.begin_native_accesses();
    bus.begin_all_native();
    bus.set_native_pc(12);
    bus.write_data_u16(0x210, 0xABCD);
    assert_eq!(bus.read_data_u16(0x210), 0xABCD);
    assert_eq!(
        bus.end_all_native(),
        [[0, 12, 0x210, 16, 1, 0xABCD], [0, 12, 0x210, 16, 0, 0xABCD]]
    );
}
