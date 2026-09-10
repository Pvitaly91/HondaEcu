use p28_slice_runner::{
    bus::Bus,
    cpu::Cpu,
    exec::{read_data_u16, step, write_data_u16},
    fuel::admission,
    instruction_forms::FormAdmission,
};

#[test]
fn shared_signed_usp_store_obeys_live_dd_width() {
    // Invented isolated D3 form. DIV leaves DD=1 in the recovered caller, so
    // the same opcode is a full Q16 store; the following LB restores DD=0.
    for word in [false, true] {
        let mut bus = Bus::new(vec![0xD3, 0x42], 0xA5);
        let mut cpu = Cpu::new();
        cpu.set_psw_u16(if word { 0x1101 } else { 0x0101 });
        cpu.a = 0x9237;
        write_data_u16(&mut cpu, &mut bus, 0x8E, 0x180);
        let decoded = step(&mut cpu, &mut bus).unwrap();
        assert_eq!(admission(&decoded), FormAdmission::Allowed);
        assert_eq!(
            read_data_u16(&cpu, &mut bus, 0x1C2),
            if word { 0x9237 } else { 0xA537 }
        );
    }
}

#[test]
fn nearby_unreviewed_form_is_not_admitted() {
    let mut bus = Bus::new(vec![0xD3, 0x42, 0x81], 0);
    let mut cpu = Cpu::new();
    cpu.set_psw_u16(0x1101);
    write_data_u16(&mut cpu, &mut bus, 0x8E, 0x180);
    let first = step(&mut cpu, &mut bus).unwrap();
    assert_eq!(admission(&first), FormAdmission::Allowed);
    let second = step(&mut cpu, &mut bus).unwrap();
    assert_eq!(admission(&second), FormAdmission::Unsupported);
}
