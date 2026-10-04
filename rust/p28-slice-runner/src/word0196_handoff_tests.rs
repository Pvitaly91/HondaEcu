//! Invented producer/consumer program. No OEM instruction window or whole-ROM claim.
use crate::{
    bus::Bus,
    cpu::Cpu,
    decoder::decode,
    exec::{step, write_data_u16},
    instruction_forms::FormAdmission,
    quartet_handoff::Generation,
    word0196_handoff::{admission, reader_generation},
};
fn toy() -> (Cpu, Bus) {
    let mut program = vec![0; 64];
    // Changed addresses/order and no Honda branch or peripheral fixture.
    program[..5].copy_from_slice(&[0x67, 0x41, 1, 0xD4, 0x68]);
    program[32..40].copy_from_slice(&[0xE4, 0x68, 0x89, 0xC4, 0x75, 0xC0, 3, 0xFF]);
    let mut cpu = Cpu::new();
    cpu.lrb = 0x40;
    cpu.set_psw_u16(0x1DCA);
    (cpu, Bus::new(program, 85))
}
fn native(cpu: &mut Cpu, bus: &mut Bus, n: usize) {
    bus.begin_native_accesses();
    for _ in 0..n {
        bus.set_native_pc(cpu.pc);
        step(cpu, bus).unwrap();
    }
    bus.end_native_accesses();
}
#[test]
fn invented_native_word_handoff_same_value_fresh_generations_retains_machine() {
    let (mut cpu, mut bus) = toy();
    let identity = (&cpu as *const Cpu, &bus as *const Bus);
    for event in 0..2 {
        cpu.pc = 0;
        bus.begin_continuity();
        native(&mut cpu, &mut bus, 2);
        let g = Generation {
            writer_pc: 3,
            event_index: event,
            write_order: 0,
            value: 321,
        };
        cpu.pc = 32;
        native(&mut cpu, &mut bus, 3);
        let j = bus.end_continuity();
        assert_eq!(cpu.pc, 39);
        assert_eq!(cpu.a, 321);
        assert_eq!(reader_generation(&j, &g, event, 0x268, 32), Some(g.clone()));
        assert_eq!(reader_generation(&j, &g, event + 1, 0x268, 32), None);
        assert_eq!(identity, (&cpu as *const Cpu, &bus as *const Bus));
        assert!(!j.iter().any(|a| a[2] < 0x80));
    }
}
#[test]
fn invented_generation_rejects_overlap_width_address_value_order_host_copy_and_second_machine() {
    let g = Generation {
        writer_pc: 3,
        event_index: 2,
        write_order: 0,
        value: 321,
    };
    let good = vec![[1, 3, 0x268, 16, 1, 321], [1, 32, 0x268, 16, 0, 321]];
    assert_eq!(reader_generation(&good, &g, 2, 0x268, 32), Some(g.clone()));
    for changed in [
        vec![[1, 32, 0x268, 16, 0, 321]],
        vec![
            [1, 3, 0x268, 16, 1, 321],
            [0, 65536, 0x268, 16, 1, 321],
            [1, 32, 0x268, 16, 0, 321],
        ],
        vec![
            [1, 3, 0x268, 16, 1, 321],
            [1, 15, 0x269, 8, 1, 1],
            [1, 32, 0x268, 16, 0, 321],
        ],
        vec![[1, 3, 0x268, 16, 1, 321], [1, 32, 0x268, 8, 0, 65]],
        vec![[1, 3, 0x268, 16, 1, 321], [1, 32, 0x26A, 16, 0, 321]],
        vec![[1, 3, 0x268, 16, 1, 321], [1, 32, 0x268, 16, 0, 320]],
    ] {
        assert_eq!(reader_generation(&changed, &g, 2, 0x268, 32), None);
    }
    let mut wrong = g.clone();
    wrong.write_order = 1;
    assert_eq!(reader_generation(&good, &wrong, 2, 0x268, 32), None);
    let (mut second, mut bus) = toy();
    write_data_u16(&mut second, &mut bus, 0x268, 321);
    second.pc = 32;
    bus.begin_continuity();
    native(&mut second, &mut bus, 1);
    assert_eq!(
        reader_generation(&bus.end_continuity(), &g, 2, 0x268, 32),
        None
    );
}
#[test]
fn exact_form_admission_does_not_admit_other_register_timer_port_or_compare_forms() {
    for (bytes, allowed) in [
        (vec![0x98, 3], true),
        (vec![0x89], true),
        (vec![0xDA, 0x75, 0], true),
        (vec![0xC4, 0x75, 0xC0, 3], true),
        (vec![0xE4, 0x68], true),
        (vec![0xCE, 0], true),
        (vec![0x99, 3], false),
        (vec![0x88], false),
        (vec![0xE5, 0x30], false),
        (vec![0xD5, 0x32], false),
        (vec![0xC5, 0x24, 0xD1], false),
        (vec![0xB4, 0x68, 0xC0, 3, 0], false),
        (vec![0x47, 0x81], false),
        (vec![0x45, 0x81], false),
    ] {
        let mut p = bytes;
        p.extend([0; 8]);
        let d = decode(true, |i| p[i]).unwrap();
        assert_eq!(admission(&d) == FormAdmission::Allowed, allowed);
    }
}
#[test]
fn invented_partial_and_stop_before_peripheral_do_not_execute_barrier() {
    use crate::runner::{execute_in_state_observed, SliceContract};
    let mut p = vec![0; 64];
    p[..4].copy_from_slice(&[0x98, 3, 0xE5, 0x30]);
    let mut cpu = Cpu::new();
    let mut bus = Bus::new(p, 85);
    let mut c = SliceContract {
        entry_pc: 0,
        exit_pcs: vec![2],
        code_ranges: vec![[0, 4]],
        psw: 0,
        lrb: 0,
        usp: 0,
        instruction_budget: 4,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    };
    bus.begin_native_accesses();
    let r = execute_in_state_observed(&mut cpu, &mut bus, &c, &[], true, Some(admission), true);
    let accesses = bus.end_native_accesses();
    assert_eq!(r.status, 0);
    assert_eq!(r.stop_pc, 2);
    assert_eq!(r.steps, 1);
    assert!(!accesses.iter().any(|a| a[1] == 0x30));
    c.exit_pcs = vec![4];
    bus.begin_native_accesses();
    let r = execute_in_state_observed(&mut cpu, &mut bus, &c, &[], true, Some(admission), true);
    assert_eq!(r.status, 1);
    assert_eq!(r.stop_pc, 2);
    assert!(bus.end_native_accesses().is_empty());
}
