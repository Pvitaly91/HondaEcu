//! Targeted invented-state probes for the opt-in continuation machinery.
//! No OEM ROM bytes, physical peripherals, or final-source corpus attestation.
use super::*;
fn program() -> ClosedPostP2ControlProgram {
    ClosedPostP2ControlProgram::explicit_invented_public_fixture()
}
fn cpu(p: &ClosedPostP2ControlProgram) -> Cpu {
    Cpu {
        pc: p.entry_pc(),
        a: 0xbe31,
        ssp: 0x4567,
        lrb: 0x21,
        zf: true,
        cf: true,
        hc: true,
        dd: true,
        sf: true,
        psw_other: 0x137,
        cycles: 0,
        instructions: 0,
        halted: false,
    }
}
fn seeds(p: &ClosedPostP2ControlProgram, path: PostP2ControlPath) -> PostP2ControlSeeds {
    let (_, inventory, _) = p.parts(path);
    let mut data: BTreeMap<_, _> = inventory.into_iter().map(|a| (a, 0xa5)).collect();
    let word = if path == PostP2ControlPath::A {
        0x00bfu16
    } else {
        0xffc0
    };
    data.insert(0x19a, word as u8);
    data.insert(0x19b, (word >> 8) as u8);
    for (a, v) in [
        (0x130, 4),
        (0x11b, 0x37),
        (
            0x12d,
            if path == PostP2ControlPath::B {
                0x80
            } else {
                0
            },
        ),
        (
            0x12e,
            if path == PostP2ControlPath::C {
                0x20
            } else {
                0
            },
        ),
        (0x192, 0x81),
        (0x193, 0x83),
        (0x108, 0xff),
    ] {
        data.insert(a, v);
    }
    let r = std::array::from_fn(|n| data[&(0x108 + n as u16)]);
    let er = std::array::from_fn(|n| u16::from_le_bytes([r[2 * n], r[2 * n + 1]]));
    PostP2ControlSeeds::new(p, data, [[0x1234; 4]; 8], r, er).unwrap()
}
fn p2() -> P2Snapshot {
    P2Snapshot {
        value: 0xa5,
        p2io: 255,
        p2sf: 7,
        provenance: "TechnicalArchitecturalP2LatchSnapshot_NoNativeWriterGeneration".into(),
    }
}
fn control(tcon0: u8, flags: u8) -> ControlSnapshot {
    ControlSnapshot {
        tcon0,
        trnsit_implemented_flags: flags,
        provenance: "TechnicalArchitecturalControlSnapshot_NoNativeWriterGeneration".into(),
    }
}
fn session(path: PostP2ControlPath, tcon0: u8, flags: u8) -> PostP2ControlSession {
    let p = program();
    let c = cpu(&p);
    let psw = c.psw_u16();
    PostP2ControlSession::new(
        &p,
        c,
        psw,
        seeds(&p, path),
        path,
        path.budget(),
        p2(),
        control(tcon0, flags),
    )
    .unwrap()
}
#[test]
fn sealed31_node221_byte_paths_have_exact_instruction_budgets() {
    let p = program();
    assert_eq!((p.segment.base, p.segment.end), (0x6400, 0x64dd));
    for (path, n, stop) in [
        (PostP2ControlPath::A, 21, 0x64dd),
        (PostP2ControlPath::B, 20, 0x64a8),
        (PostP2ControlPath::C, 21, 0x64a8),
        (PostP2ControlPath::D, 23, 0x64a8),
    ] {
        let (nodes, inventory, pcs) = p.parts(path);
        assert_eq!(nodes.len(), 31);
        assert_eq!(inventory.len(), 16);
        assert_eq!(pcs.len(), n);
        assert_eq!(usize::from(path.budget()), n);
        assert_eq!(p.terminal(path), stop);
        assert!(nodes
            .iter()
            .flat_map(|n| n.reads.iter())
            .any(|a| a.address == 6));
    }
    assert_eq!((0x55d2 - 0x54f5), 221);
}
#[test]
fn bounded_four_path_execution_uses_actual_control_reads_writes_and_same_cpu() {
    for (path, tcon, flags) in [
        (PostP2ControlPath::A, 0x83, 0),
        (PostP2ControlPath::A, 0x87, 15),
        (PostP2ControlPath::A, 0x8b, 5),
        (PostP2ControlPath::A, 0x8f, 10),
        (PostP2ControlPath::B, 0x83, 0),
        (PostP2ControlPath::B, 0x87, 15),
        (PostP2ControlPath::C, 0x8b, 5),
        (PostP2ControlPath::D, 0x8f, 10),
    ] {
        let mut s = session(path, tcon, flags);
        for _ in 0..path.budget() {
            s.step().unwrap();
        }
        let r = s.report().unwrap();
        assert!(r.p2.completed && r.p2.positive_completed);
        assert_eq!(r.p2.audit.successful_retirements, u64::from(path.budget()));
        assert_eq!(r.p2.program_node_count, 31);
        assert_eq!(r.control_initial, [tcon, flags]);
        assert_eq!(r.control_step_snapshots.len(), usize::from(path.budget()));
        assert_eq!(
            r.p2.audit.diagnostic_events.len(),
            4 * usize::from(path.budget()) + 4
        );
        let g = r.control_generation.as_ref().unwrap();
        assert_eq!(g.generation_ordinal, 1);
        assert_eq!(g.machine_id, 1);
        assert_eq!(
            g.native_write_ordinal,
            if path == PostP2ControlPath::D { 8 } else { 6 }
        );
        assert_eq!(
            r.p2.p2_generation.as_ref().unwrap().retired_instruction,
            u64::from(path.prefix().budget())
        );
        if path == PostP2ControlPath::A {
            assert_eq!(r.control_final, [tcon | 4, flags]);
            assert_eq!(r.control_instruction_retirements, 4);
            assert_eq!(r.peripheral_control_journal.len(), 3);
            let first = &r.p2.steps[17];
            assert_eq!(first.after.cpu.zf, tcon & 4 == 0);
            assert_eq!(first.after.cpu.cf, first.before.cpu.cf);
            assert_eq!(first.after.cpu.hc, first.before.cpu.hc);
            assert_eq!(first.after.cpu.a, first.before.cpu.a);
            let lb = &r.p2.steps[18];
            assert!(!lb.after.cpu.dd);
            assert_eq!(lb.after.cpu.a & 0xff00, lb.before.cpu.a & 0xff00);
            let xor = &r.p2.steps[19];
            assert_eq!(xor.after.cpu.a as u8, (xor.before.cpu.a as u8) ^ 255);
            let mb = &r.p2.steps[20];
            assert_eq!(mb.after.cpu.cf, mb.before.cpu.a & 128 != 0);
            assert_eq!(mb.after.cpu.zf, mb.before.cpu.zf);
            assert_eq!(mb.raw_span[0], mb.raw_span[1]);
            assert_eq!(mb.logical_span[1] - mb.logical_span[0], 1);
            assert_eq!(r.p2.stop_before_pc, Some(0x64dd));
        } else {
            assert_eq!(r.control_final, [tcon, flags & !4]);
            assert_eq!(r.control_instruction_retirements, 1);
            assert_eq!(r.peripheral_control_journal.len(), 2);
            let step = r.p2.steps.last().unwrap();
            assert_eq!(step.after.cpu.a, step.before.cpu.a);
            assert!(!step.after.cpu.zf);
            assert_eq!(step.after.cpu.cf, step.before.cpu.cf);
            assert_eq!(step.after.cpu.hc, step.before.cpu.hc);
            assert_eq!(step.after.cpu.dd, step.before.cpu.dd);
            assert_eq!(r.p2.stop_before_pc, Some(0x64a8));
            assert_eq!(r.peripheral_control_journal[0].value, 0xf0 | flags);
        }
        let instructions = s.inner.inner.cpu.instructions;
        assert!(s.step().is_err());
        assert_eq!(s.inner.inner.cpu.instructions, instructions);
    }
}
#[test]
fn same_value_control_store_creates_fresh_generation_and_live_storage_old_metadata() {
    for path in [PostP2ControlPath::A, PostP2ControlPath::D] {
        let mut s = session(path, 0x87, 0);
        for _ in 0..path.budget() {
            s.step().unwrap();
        }
        let r = s.report().unwrap();
        let event = r.peripheral_control_journal.last().unwrap();
        assert_eq!(event.same_value, Some(true));
        assert!(r.control_generation.is_some());
        let logical = &r.p2.audit.data_events[event.logical_ordinal as usize];
        assert_eq!(logical.old_value, logical.value);
        assert_eq!(event.space, "PeripheralControl");
    }
}
#[test]
fn invalid_entry_budget_control_mode_and_forged_ownership_refuse_before_cpu_step() {
    for budget in [0, 1, 16, 17, 19, 20, 22, 255] {
        let p = program();
        let c = cpu(&p);
        let psw = c.psw_u16();
        assert!(PostP2ControlSession::new(
            &p,
            c,
            psw,
            seeds(&p, PostP2ControlPath::A),
            PostP2ControlPath::A,
            budget,
            p2(),
            control(0x83, 0)
        )
        .is_err());
    }
    for snapshot in [
        control(0x93, 0),
        control(0x03, 0),
        control(0x82, 0),
        control(0x83, 16),
        ControlSnapshot {
            provenance: "NativeStartupObserved".into(),
            ..control(0x83, 0)
        },
    ] {
        let p = program();
        let c = cpu(&p);
        let psw = c.psw_u16();
        assert_eq!(
            PostP2ControlSession::new(
                &p,
                c,
                psw,
                seeds(&p, PostP2ControlPath::A),
                PostP2ControlPath::A,
                21,
                p2(),
                snapshot
            )
            .err()
            .unwrap()
            .code,
            "PostP2ControlSnapshotRejected"
        );
    }
    for pc in [0x64a4, 0x64d3, 0x5599, 0x55c8] {
        let p = program();
        let mut c = cpu(&p);
        c.pc = pc;
        let psw = c.psw_u16();
        assert!(PostP2ControlSession::new(
            &p,
            c,
            psw,
            seeds(&p, PostP2ControlPath::A),
            PostP2ControlPath::A,
            21,
            p2(),
            control(0x83, 0)
        )
        .is_err());
    }
}
#[test]
fn host_post_start_control_reseed_register_mutation_and_second_machine_are_refused() {
    let mut s = session(PostP2ControlPath::A, 0x83, 0);
    s.step().unwrap();
    assert!(s
        .inner
        .inner
        .bus
        .initialize_post_p2_control(0x83, 0)
        .is_err());
    s.last_control[0] ^= 4;
    assert_eq!(s.step().unwrap_err().code, "PostP2LiveControlChanged");
    assert_eq!(s.inner.inner.cpu.instructions, 1);
    let mut a = session(PostP2ControlPath::D, 0x83, 0);
    let mut b = session(PostP2ControlPath::D, 0x83, 0);
    a.step().unwrap();
    b.step().unwrap();
    a.inner.inner = b.inner.inner;
    assert_eq!(a.step().unwrap_err().code, "P2MachineSubstitutionRejected");
}
#[test]
fn unauthorized_sfr_width_host_and_cross_path_access_cannot_open_capability() {
    for (address, width, write) in [
        (0x40, 8, false),
        (0x40, 8, true),
        (0x46, 8, false),
        (0x46, 16, true),
        (0x559d, 8, false),
        (0x24, 8, true),
        (0x26, 8, true),
        (6, 8, false),
    ] {
        let mut s = session(PostP2ControlPath::D, 0x83, 0);
        s.inner.inner.bus.set_native_pc(0x64a4);
        s.inner.inner.bus.set_control_access(Some((0x40, 0x64a4)));
        if write {
            assert!(s.inner.inner.data_write(address, width, 1).is_err());
        } else {
            assert!(s.inner.inner.data_read(address, width).is_err());
        }
        assert_eq!(s.inner.inner.bus.post_p2_control(), Some([0x83, 0]));
        assert!(s.inner.inner.bus.control_accesses().is_empty());
    }
}
#[test]
fn altered_actual_control_form_is_refused_before_native_sfr_service() {
    let mut p = program();
    let at = usize::from(p.pc(0x5599) - p.entry_pc());
    p.segment.bytes[at + 1] = 0x40;
    p.segment.digest = crate::audit_sha256::digest(&p.segment.bytes);
    let c = cpu(&p);
    let psw = c.psw_u16();
    let mut s = PostP2ControlSession::new(
        &p,
        c,
        psw,
        seeds(&p, PostP2ControlPath::D),
        PostP2ControlPath::D,
        23,
        p2(),
        control(0x83, 0),
    )
    .unwrap();
    for _ in 0..22 {
        s.step().unwrap();
    }
    assert_eq!(s.step().unwrap_err().code, "SelectedInstructionMismatch");
    assert!(s.native_control.is_empty());
    assert_eq!(s.inner.inner.bus.post_p2_control(), Some([0x83, 0]));
}

#[test]
fn direct_host_sfr_write_after_first_functional_instruction_is_unserviced() {
    for (path, address, requested) in [
        (PostP2ControlPath::A, 0x40, 0x87),
        (PostP2ControlPath::A, 0x46, 0xff),
        (PostP2ControlPath::D, 0x40, 0x87),
        (PostP2ControlPath::D, 0x46, 0xff),
    ] {
        let mut s = session(path, 0x83, 0);
        s.step().unwrap();
        let before_control = s.inner.inner.bus.post_p2_control();
        let before_p2 = s.inner.inner.bus.p2_output_latch();
        let before_cpu = (
            s.inner.inner.cpu.pc,
            s.inner.inner.cpu.a,
            s.inner.inner.cpu.psw_u16(),
            s.inner.inner.cpu.instructions,
            s.inner.inner.cpu.cycles,
        );
        let before_audit = s.inner.inner.report();
        // Actual production Bus write attempt after functional execution began.
        // No host capability or boundary PC is installed to make it possible.
        s.inner.inner.bus.write_data_u8(address, requested);
        let fault = s.inner.inner.current_fault().unwrap_err();
        assert_eq!(fault.code, "OriginalDataOutsideInstruction");
        assert_eq!(fault.address, Some(i64::from(address)));
        assert_eq!(s.inner.inner.bus.post_p2_control(), before_control);
        assert_eq!(s.inner.inner.bus.p2_output_latch(), before_p2);
        assert!(s.inner.inner.bus.control_accesses().is_empty());
        assert!(s.inner.inner.bus.p2_accesses().is_empty());
        assert_eq!(
            (
                s.inner.inner.cpu.pc,
                s.inner.inner.cpu.a,
                s.inner.inner.cpu.psw_u16(),
                s.inner.inner.cpu.instructions,
                s.inner.inner.cpu.cycles
            ),
            before_cpu
        );
        assert_eq!(s.inner.inner.cpu.instructions, 1);
        let after_audit = s.inner.inner.report();
        assert_eq!(
            after_audit.data_events.len(),
            before_audit.data_events.len() + 1
        );
        assert_eq!(
            after_audit.raw_data_events.len(),
            before_audit.raw_data_events.len()
        );
        let refused = after_audit.data_events.last().unwrap();
        assert_eq!(refused.phase, "Functional");
        assert_eq!(refused.operation, "Write");
        assert_eq!(refused.address, address);
        assert_eq!(refused.width, 8);
        assert_eq!(refused.requested_value, Some(u16::from(requested)));
        assert_eq!(refused.value, None);
        assert!(!refused.serviced);
        assert_eq!(
            refused.refusal.as_ref().unwrap().code,
            "OriginalDataOutsideInstruction"
        );
        assert_eq!(
            after_audit.first_fault.unwrap().code,
            "OriginalDataOutsideInstruction"
        );
    }
}
