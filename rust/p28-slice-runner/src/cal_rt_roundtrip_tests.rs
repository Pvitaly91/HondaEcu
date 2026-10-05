use crate::{bus::Bus, cpu::Cpu, exec::step};

#[test]
fn invented_nested_calls_overwrite_canaries_and_return_on_one_machine() {
    let mut program = vec![0xFF; 19];
    program[0..3].copy_from_slice(&[0x32, 8, 0]);
    program[8..12].copy_from_slice(&[0x32, 16, 0, 1]);
    program[16..19].copy_from_slice(&[0x77, 0x42, 1]);
    for pattern in [0, 0x55, 0xAA] {
        let mut cpu = Cpu::new();
        let mut bus = Bus::new(program.clone(), pattern);
        cpu.a = 0xA500;
        cpu.lrb = 0x21;
        cpu.set_psw_u16(0xA331);
        cpu.sf = true;
        bus.begin_native_accesses();
        bus.begin_all_native();
        let mut pcs = vec![];
        while cpu.pc != 3 {
            let pc = cpu.pc;
            bus.set_native_pc(pc);
            pcs.push(pc);
            let before = (cpu.a, cpu.psw_u16(), cpu.lrb);
            let d = step(&mut cpu, &mut bus).unwrap();
            if matches!(d.mnemonic, "CAL addr16" | "RT") {
                assert!(!cpu.sf);
                assert_eq!((cpu.a, cpu.psw_u16(), cpu.lrb), before);
            }
            assert!(pcs.len() <= 5);
        }
        assert_eq!(pcs, [0, 8, 16, 18, 11]);
        assert_eq!((cpu.pc, cpu.ssp, cpu.a, cpu.lrb), (3, 0x7FE, 0xA542, 0x21));
        let all = bus.end_all_native();
        assert_eq!(
            all,
            [
                [0, 0, 0x7FE, 16, 1, 3],
                [0, 8, 0x7FC, 16, 1, 11],
                [0, 18, 0x7FC, 16, 0, 11],
                [0, 11, 0x7FE, 16, 0, 3]
            ]
        );
    }
}

#[test]
fn exact_retained_stack_bounds_refuse_wrap_odd_overflow_and_field_collisions() {
    for ssp in [0, 1, 0x6FE, 0x701, 0x800, 0xFFFE] {
        let mut cpu = Cpu::new();
        cpu.pc = 0x063B;
        cpu.ssp = ssp;
        let mut bus = Bus::new(vec![], 0xAA);
        assert!(crate::cal_rt_roundtrip::execute(&mut cpu, &mut bus, true).is_err());
        assert_eq!(cpu.ssp, ssp);
    }
    let mut cpu = Cpu::new();
    cpu.pc = 0x5688;
    cpu.ssp = 0xFFFF;
    assert!(crate::cal_rt_roundtrip::execute(&mut cpu, &mut Bus::new(vec![], 0), false).is_err());
}
