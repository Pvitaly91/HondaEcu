use p28_slice_runner::{
    bus::Bus,
    cpu::Cpu,
    exec::{read_data_u16, step, write_data_u16},
};

#[test]
fn decoded_word_rol_uses_incoming_carry_and_preserves_other_flags() {
    // MSM66201 printed 3-117: 33/DD1 rotates through C, not circularly.
    for a in [0u16, 1, 0x7fff, 0x8000, 0xffff] {
        for cf in [false, true] {
            for zf in [false, true] {
                let mut cpu = Cpu::new();
                let mut bus = Bus::new(vec![0x33], 0xA5);
                cpu.set_psw_u16(0x3331);
                cpu.a = a;
                cpu.cf = cf;
                cpu.zf = zf;
                let preserved = cpu.psw_u16() & !Cpu::PSW_CF_BIT;
                assert_eq!(step(&mut cpu, &mut bus).unwrap().mnemonic, "ROL A");
                assert_eq!(cpu.a, a.wrapping_mul(2) | u16::from(cf));
                assert_eq!(cpu.cf, a & 0x8000 != 0);
                assert_eq!(cpu.psw_u16() & !Cpu::PSW_CF_BIT, preserved);
            }
        }
    }
}

#[test]
fn decoded_word_add_er0_and_offpage_update_half_carry_without_carry_in() {
    // Independent single instructions, not a copied firmware routine.
    for bytes in [vec![0x08], vec![0x87, 0x70]] {
        for (a, b) in [
            (15u16, 1u16),
            (16, 1),
            (0xffff, 1),
            (0x7fff, 0x8001),
            (0, 0),
        ] {
            for hc in [false, true] {
                let mut cpu = Cpu::new();
                let mut bus = Bus::new(bytes.clone(), 0xA5);
                cpu.set_psw_u16(0x9331);
                cpu.lrb = 0x20;
                cpu.a = a;
                cpu.hc = hc;
                write_data_u16(&mut cpu, &mut bus, 0x100, b);
                write_data_u16(&mut cpu, &mut bus, 0x170, b);
                step(&mut cpu, &mut bus).unwrap();
                assert_eq!(cpu.a, a.wrapping_add(b));
                assert_eq!(cpu.cf, (a as u32 + b as u32) > 65535);
                assert_eq!(cpu.zf, a.wrapping_add(b) == 0);
                assert_eq!(cpu.hc, (a & 15) + (b & 15) > 15);
                assert_eq!(read_data_u16(&cpu, &mut bus, 0x100), b);
                assert_eq!(cpu.lrb, 0x20);
                assert!(cpu.dd);
            }
        }
    }
}
