//! Single-instruction primary ISA regressions, not OEM program fixtures.
use p28_slice_runner::{
    bus::Bus,
    cpu::Cpu,
    exec::{read_data_u16, step, write_data_u16},
};

#[test]
fn decoded_word_rol_er0_uses_incoming_carry_and_preserves_noncarry_flags() {
    // MSM66201 printed3-118: exact44 B7, word/DD-independent, onlyCF.
    for lrb in [0x20u16, 0x40, 0x41] {
        for value in [0u16, 1, 0x7fff, 0x8000, 0xffff] {
            for cf in [false, true] {
                for zf in [false, true] {
                    for dd in [false, true] {
                        let mut cpu = Cpu::new();
                        let mut bus = Bus::new(vec![0x44, 0xb7], 0xa5);
                        cpu.set_psw_u16(0x3331);
                        cpu.lrb = lrb;
                        cpu.dd = dd;
                        cpu.cf = cf;
                        cpu.zf = zf;
                        let address = cpu.bank_base();
                        write_data_u16(&mut cpu, &mut bus, address, value);
                        let flags = cpu.psw_u16() & !Cpu::PSW_CF_BIT;
                        assert_eq!(step(&mut cpu, &mut bus).unwrap().mnemonic, "ROL er0");
                        assert_eq!(
                            read_data_u16(&cpu, &mut bus, address),
                            value.wrapping_mul(2) | u16::from(cf)
                        );
                        assert_eq!(cpu.cf, value & 0x8000 != 0);
                        assert_eq!(cpu.psw_u16() & !Cpu::PSW_CF_BIT, flags);
                    }
                }
            }
        }
    }
}

#[test]
fn decoded_word_sll_a_preserves_noncarry_flags() {
    // MSM66201 printed3-142: exact53/DD1, CF only (notZF).
    for value in [0u16, 1, 0x7fff, 0x8000, 0xffff] {
        for cf in [false, true] {
            for zf in [false, true] {
                let mut cpu = Cpu::new();
                let mut bus = Bus::new(vec![0x53], 0xa5);
                cpu.set_psw_u16(0x3331);
                cpu.a = value;
                cpu.cf = cf;
                cpu.zf = zf;
                let flags = cpu.psw_u16() & !Cpu::PSW_CF_BIT;
                assert_eq!(step(&mut cpu, &mut bus).unwrap().mnemonic, "SLL A");
                assert_eq!(cpu.a, value.wrapping_mul(2));
                assert_eq!(cpu.cf, value & 0x8000 != 0);
                assert_eq!(cpu.psw_u16() & !Cpu::PSW_CF_BIT, flags);
            }
        }
    }
}
