use p28_slice_runner::{
    bus::Bus,
    cpu::Cpu,
    exec::{read_data_u8, step, write_data_u8},
    ignition::admission,
    instruction_forms::FormAdmission,
};

#[test]
fn decoded_movb_r0_direct_reads_real_acch_alias_as_one_byte() {
    // MSM66201 Instruction Manual, MOVB register/direct forms and the
    // architectural ACC/ACCH data aliases. Exact OEM opcode bytes are tested
    // here in isolation; no OEM routine is embedded.
    let mut bus = Bus::new(vec![0xC5, 0x07, 0x48], 0x55);
    let mut cpu = Cpu::new();
    cpu.set_psw_u16(0xA211);
    cpu.a = 0xA53C;
    cpu.lrb = 0x40;
    write_data_u8(&mut cpu, &mut bus, 0x201, 0x6B);
    let psw_before = cpu.psw_u16();
    let decoded = step(&mut cpu, &mut bus).unwrap();
    assert_eq!(decoded.mnemonic, "MOVB r0, N8");
    assert_eq!(admission(&decoded), FormAdmission::Allowed);
    assert_eq!(read_data_u8(&cpu, &mut bus, 0x200), 0xA5);
    assert_eq!(read_data_u8(&cpu, &mut bus, 0x201), 0x6B);
    assert_eq!(cpu.psw_u16(), psw_before);
}

#[test]
fn adjacent_destination_form_is_not_admitted() {
    let mut bus = Bus::new(vec![0xC5, 0x07, 0x49], 0);
    let mut cpu = Cpu::new();
    cpu.lrb = 0x40;
    let decoded = step(&mut cpu, &mut bus).unwrap();
    assert_eq!(decoded.mnemonic, "MOVB r1, N8");
    assert_eq!(admission(&decoded), FormAdmission::Unsupported);
}
