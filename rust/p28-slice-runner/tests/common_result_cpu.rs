//! Independent decoded ISA regression; invented operands, not an OEM sequence.
use p28_slice_runner::{
    bus::Bus,
    cpu::Cpu,
    exec::{read_data_u16, step, write_data_u16},
};

#[test]
fn decoded_word_add_dp_immediate_updates_halfcarry_for_both_dd_modes() {
    for dd in [false, true] {
        for incoming_hc in [false, true] {
            for (value, increment) in [(0u16, 3u16), (15, 1), (16, 1), (65535, 1)] {
                let mut cpu = Cpu::new();
                cpu.set_psw_u16(0x0101);
                cpu.dd = dd;
                cpu.hc = incoming_hc;
                cpu.a = 0xCAFE;
                let mut bus =
                    Bus::new(vec![0x92, 0x80, increment as u8, (increment >> 8) as u8], 0);
                write_data_u16(&mut cpu, &mut bus, 0x8C, value);
                step(&mut cpu, &mut bus).unwrap();
                let expected = value.wrapping_add(increment);
                assert_eq!(read_data_u16(&cpu, &mut bus, 0x8C), expected);
                assert_eq!(cpu.a, 0xCAFE);
                assert_eq!(cpu.dd, dd);
                assert_eq!(cpu.cf, u32::from(value) + u32::from(increment) > 65535);
                assert_eq!(cpu.zf, expected == 0);
                assert_eq!(
                    cpu.hc,
                    (value & 15) + (increment & 15) > 15,
                    "DP={value} increment={increment} incomingHC={incoming_hc} DD={dd}"
                );
            }
        }
    }
}
