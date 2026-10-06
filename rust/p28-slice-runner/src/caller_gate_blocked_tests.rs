//! Invented instruction probes for a blocked primary caller research path.
//! These are ISA/test-domain checks, never OEM caller or producer execution.
use crate::{
    bus::Bus,
    cpu::Cpu,
    exec::{read_data_u8, step, write_data_u8},
    protocol::Request,
    runner::run_request,
};

fn machine(program: Vec<u8>, dd: bool, flags: u16) -> (Cpu, Bus) {
    let mut cpu = Cpu::new();
    cpu.a = 0xBEEF;
    cpu.lrb = 0x43;
    cpu.set_psw_u16(0x0332 | flags | if dd { Cpu::PSW_DD_BIT } else { 0 });
    (cpu, Bus::new(program, 0xA5))
}

#[test]
fn invented_jbs_off_bit3_preserves_dd_flags_and_uses_the_lrb_page() {
    // The chosen page, source, displacement and low code addresses are invented.
    for source in 0u16..=255 {
        for dd in [false, true] {
            for flags in (0u16..8).map(|f| f << 13) {
                let (mut cpu, mut bus) = machine(vec![0xEB, 0xD7, 2], dd, flags);
                write_data_u8(&mut cpu, &mut bus, 0x2D7, source as u8);
                write_data_u8(&mut cpu, &mut bus, 0xD7, !(source as u8));
                let before = (cpu.a, cpu.psw_u16(), cpu.lrb, cpu.ssp);
                bus.configure_scoped_access(vec![[0x2D7, 0x2D8]], 8);
                bus.begin_native_accesses();
                bus.set_native_pc(0);
                let decoded = step(&mut cpu, &mut bus).unwrap();
                assert_eq!((decoded.mnemonic, decoded.len), ("JBS off N8.3, rel8", 3));
                assert_eq!(cpu.pc, if source & 8 != 0 { 5 } else { 3 });
                assert_eq!((cpu.a, cpu.psw_u16(), cpu.lrb, cpu.ssp), before);
                assert_eq!(cpu.dd, dd);
                assert_eq!(bus.end_native_accesses(), [[0, 0x2D7, 8, 0, source as u32]]);
                assert_eq!(read_data_u8(&cpu, &mut bus, 0x2D7), source as u8);
                assert!(bus.take_fault().is_none());
            }
        }
    }
}

#[test]
fn invented_rb_off_bit3_uses_the_old_bit_for_zf_and_preserves_neighbors() {
    for source in 0u16..=255 {
        for dd in [false, true] {
            for flags in (0u16..8).map(|f| f << 13) {
                let (mut cpu, mut bus) = machine(vec![0xC4, 0xD9, 0x0B], dd, flags);
                write_data_u8(&mut cpu, &mut bus, 0x2D9, source as u8);
                let before = (cpu.a, cpu.psw_u16(), cpu.lrb, cpu.ssp);
                bus.configure_scoped_access(vec![[0x2D8, 0x2DB]], 16);
                bus.begin_native_accesses();
                bus.begin_write_journal();
                bus.set_native_pc(0);
                let decoded = step(&mut cpu, &mut bus).unwrap();
                let after = source & !8;
                assert_eq!((decoded.mnemonic, decoded.len), ("RB off N8.3", 3));
                assert_eq!(cpu.pc, 3);
                assert_eq!(cpu.zf, source & 8 == 0);
                assert_eq!(
                    cpu.psw_u16() & !Cpu::PSW_ZF_BIT,
                    before.1 & !Cpu::PSW_ZF_BIT
                );
                assert_eq!(
                    (cpu.a, cpu.lrb, cpu.ssp, cpu.dd),
                    (before.0, before.2, before.3, dd)
                );
                assert_eq!(
                    bus.end_native_accesses(),
                    [
                        [0, 0x2D9, 8, 0, source as u32],
                        [0, 0x2D9, 8, 0, source as u32],
                        [0, 0x2D9, 8, 1, after as u32],
                    ]
                );
                assert_eq!(bus.end_write_journal(), [[0x2D9, 8, after as u32]]);
                assert_eq!(read_data_u8(&cpu, &mut bus, 0x2D9), after as u8);
                assert_eq!(read_data_u8(&cpu, &mut bus, 0x2D8), 0xA5);
                assert_eq!(read_data_u8(&cpu, &mut bus, 0x2DA), 0xA5);
                assert!(bus.take_fault().is_none());
            }
        }
    }
}

#[test]
fn invented_jne_depends_only_on_zf_and_preserves_dd_and_other_flags() {
    for dd in [false, true] {
        for flags in (0u16..8).map(|f| f << 13) {
            let (mut cpu, mut bus) = machine(vec![0xCE, 5], dd, flags);
            let before = (cpu.a, cpu.psw_u16(), cpu.lrb, cpu.ssp);
            bus.begin_native_accesses();
            bus.set_native_pc(0);
            let decoded = step(&mut cpu, &mut bus).unwrap();
            assert_eq!((decoded.mnemonic, decoded.len), ("JNE rel8", 2));
            assert_eq!(cpu.pc, if flags & Cpu::PSW_ZF_BIT == 0 { 7 } else { 2 });
            assert_eq!((cpu.a, cpu.psw_u16(), cpu.lrb, cpu.ssp), before);
            assert_eq!(cpu.dd, dd);
            assert!(bus.end_native_accesses().is_empty());
            assert!(bus.take_fault().is_none());
        }
    }
}

#[test]
fn invented_coupled_primary_gates_skip_the_call_for_all_scratch_patterns() {
    // Differently composed low-address control flow and ordinary RAM fields.
    // The primary taken branch is tested; this says nothing about OEM fallthrough.
    let mut program = vec![0xFF; 24];
    program[0..3].copy_from_slice(&[0xEB, 0xD7, 5]); // taken -> 8
    program[3..7].copy_from_slice(&[0x77, 0x43, 0xCB, 9]); // fallthrough -> stop16
    program[8..16].copy_from_slice(&[0xC4, 0xD9, 0x0B, 0xCE, 3, 0x32, 20, 0]);
    program[20..23].copy_from_slice(&[0x77, 0x37, 0x01]); // invented helper, never reached
    for pattern in [0u8, 0x55, 0xAA] {
        for bit1 in [false, true] {
            for dd in [false, true] {
                let (mut cpu, mut bus) = machine(program.clone(), dd, 0xE000);
                let control = (pattern & !2) | if bit1 { 2 } else { 0 };
                write_data_u8(&mut cpu, &mut bus, 0x2D7, pattern);
                write_data_u8(&mut cpu, &mut bus, 0x2D9, control);
                let identity = (&cpu as *const Cpu, &bus as *const Bus);
                bus.configure_scoped_access(vec![[0x2D7, 0x2DA]], 64);
                bus.begin_native_accesses();
                bus.begin_continuity();
                bus.begin_write_journal();
                let mut pcs = vec![];
                while cpu.pc != 16 {
                    let pc = cpu.pc;
                    bus.set_native_pc(pc);
                    step(&mut cpu, &mut bus).unwrap();
                    pcs.push(pc);
                    assert!(pcs.len() <= 3);
                }
                let accesses = bus.end_native_accesses();
                let writes = bus.end_write_journal();
                let continuity = bus.end_continuity();
                assert_eq!(
                    pcs,
                    if pattern == 0xAA {
                        vec![0, 8, 11]
                    } else {
                        vec![0, 3, 5]
                    }
                );
                assert!(!pcs.contains(&13)); // no native call/frame even for the taken primary gate
                assert!(!pcs.contains(&20));
                assert_eq!(cpu.ssp, 0x7FE);
                assert_eq!(identity, (&cpu as *const Cpu, &bus as *const Bus));
                assert!(accesses.iter().all(|a| a[1] < 0x700));
                assert!(continuity.iter().all(|a| a[0] == 1));
                assert_eq!(read_data_u8(&cpu, &mut bus, 0x2D7), pattern);
                if pattern == 0xAA {
                    assert!(!cpu.zf); // old bit was set although the stored bit is now clear
                    assert_eq!(writes, [[0x2D9, 8, (control & !8) as u32]]);
                    assert_eq!(read_data_u8(&cpu, &mut bus, 0x2D9), control & !8);
                } else {
                    assert!(writes.is_empty());
                    assert_eq!(read_data_u8(&cpu, &mut bus, 0x2D9), control);
                }
                assert!(bus.take_fault().is_none());
            }
        }
    }
}

#[test]
fn blocked_caller_research_does_not_register_a_new_runner_operation() {
    // The proposed operation remains unsupported: no new capability/version claim.
    let request: Request = serde_json::from_value(serde_json::json!({
        "protocolVersion": 1,
        "operation": "nativeData0136CallerHandoff",
        "images": [{"id": "invented", "rom": [0x77, 0x37]}],
        "allowAssumptions": [],
        "scratchPatterns": [0]
    }))
    .unwrap();
    assert_eq!(run_request(request).unwrap_err(), "unsupported operation");
}
