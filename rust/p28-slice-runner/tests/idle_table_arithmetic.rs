//! M1s: invented single-form probes for the full exporter numeric range.
use p28_slice_runner::{
    bus::Bus,
    cpu::Cpu,
    exec::{read_data_u16, step, write_data_u16},
    idle_contexts::admission,
    instruction_forms::FormAdmission,
};

#[test]
fn edited_numeric_range_multiply_keeps_full_product_and_aliases() {
    // Existing manual3-100 word MUL admission; no new permission or program fixture.
    for magnitude in [0u16, 1, 255, 32768, 65533] {
        for distance in [0u16, 1, 39, 94, 255] {
            let mut cpu = Cpu::new();
            let mut bus = Bus::new(vec![0x90, 0x35], 0xA5);
            cpu.lrb = 0x41;
            cpu.set_psw_u16(0x9501);
            cpu.a = magnitude;
            write_data_u16(&mut cpu, &mut bus, 0x208, distance);
            let flags = cpu.psw_u16() & !Cpu::PSW_ZF_BIT;
            let d = step(&mut cpu, &mut bus).unwrap();
            assert_eq!(admission(&d), FormAdmission::Allowed);
            let expected = u32::from(magnitude) * u32::from(distance);
            assert_eq!(cpu.a, expected as u16);
            assert_eq!(
                read_data_u16(&cpu, &mut bus, 0x20A),
                (expected >> 16) as u16
            );
            assert_eq!(read_data_u16(&cpu, &mut bus, 0x208), distance);
            assert_eq!(cpu.zf, expected == 0);
            assert_eq!(cpu.psw_u16() & !Cpu::PSW_ZF_BIT, flags);
        }
    }
}

#[test]
fn edited_numeric_range_divide_truncates_full_double_word_without_overflow() {
    for denominator in [1u16, 12, 26, 40, 94, 255] {
        for distance in [0, denominator / 2, denominator] {
            let product = 65533u32 * u32::from(distance);
            let mut cpu = Cpu::new();
            let mut bus = Bus::new(vec![0x90, 0x37], 0xA5);
            cpu.lrb = 0x41;
            cpu.set_psw_u16(0x9501);
            cpu.a = product as u16;
            write_data_u16(&mut cpu, &mut bus, 0x208, (product >> 16) as u16);
            write_data_u16(&mut cpu, &mut bus, 0x20C, denominator);
            let flags = cpu.psw_u16() & !(Cpu::PSW_CF_BIT | Cpu::PSW_ZF_BIT);
            let d = step(&mut cpu, &mut bus).unwrap();
            assert_eq!(admission(&d), FormAdmission::Allowed);
            assert_eq!(cpu.a as u32, product / u32::from(denominator));
            assert_eq!(read_data_u16(&cpu, &mut bus, 0x208), 0);
            assert_eq!(
                read_data_u16(&cpu, &mut bus, 0x20A) as u32,
                product % u32::from(denominator)
            );
            assert!(!cpu.cf);
            assert_eq!(cpu.zf, cpu.a == 0);
            assert_eq!(cpu.psw_u16() & !(Cpu::PSW_CF_BIT | Cpu::PSW_ZF_BIT), flags);
        }
    }
}

#[test]
fn positive_interpolation_direction_uses_existing_accumulator_add_not_unresolved_destination_form()
{
    for (lower, delta, expected) in [
        (1u16, 65533u16, 65534u16),
        (300, 17, 317),
        (32768, 0, 32768),
    ] {
        let mut cpu = Cpu::new();
        let mut bus = Bus::new(vec![0x0B], 0xA5);
        cpu.lrb = 0x41;
        cpu.set_psw_u16(0x9501);
        cpu.a = delta;
        write_data_u16(&mut cpu, &mut bus, 0x20E, lower);
        let d = step(&mut cpu, &mut bus).unwrap();
        assert_eq!(d.mnemonic, "ADD A, er3");
        assert_eq!(admission(&d), FormAdmission::Allowed);
        assert_eq!(cpu.a, expected);
        assert!(!cpu.cf);
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x20E), lower);
    }
}
