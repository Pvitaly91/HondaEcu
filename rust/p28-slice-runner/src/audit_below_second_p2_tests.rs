//! Small invented execution/negative probes; not the final private/public corpus.
use super::*;
fn program() -> ClosedBelowSecondP2Program {
    ClosedBelowSecondP2Program::explicit_invented_public_fixture()
}
fn cpu(p: &ClosedBelowSecondP2Program) -> Cpu {
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
fn data(p: &ClosedBelowSecondP2Program, source: u8, flag: u8) -> BTreeMap<u16, u8> {
    let (_, inventory, _) = p.parts();
    let mut d: BTreeMap<_, _> = inventory.into_iter().map(|a| (a, 0xa5)).collect();
    for (a, v) in [
        (0x19a, 0xbf),
        (0x19b, 0),
        (0x130, 4),
        (0x11b, 0x37),
        (0x12d, flag),
        (0x12e, 0x20),
        (0x192, source),
        (0x193, 0x83),
        (0x108, 0xff),
    ] {
        d.insert(a, v);
    }
    d
}
fn seeds(p: &ClosedBelowSecondP2Program, source: u8, flag: u8) -> BelowSecondP2Seeds {
    let d = data(p, source, flag);
    let r = std::array::from_fn(|n| d[&(0x108 + n as u16)]);
    let er = std::array::from_fn(|n| u16::from_le_bytes([r[2 * n], r[2 * n + 1]]));
    BelowSecondP2Seeds::new(p, d, [[0x1234; 4]; 8], r, er).unwrap()
}
fn p2() -> P2Snapshot {
    P2Snapshot {
        value: 0xa5,
        p2io: 0xff,
        p2sf: 7,
        provenance: "TechnicalArchitecturalP2LatchSnapshot_NoNativeWriterGeneration".into(),
    }
}
fn control(tcon0: u8) -> ControlSnapshot {
    ControlSnapshot {
        tcon0,
        trnsit_implemented_flags: 11,
        provenance: "TechnicalArchitecturalControlSnapshot_NoNativeWriterGeneration".into(),
    }
}
fn session(source: u8, tcon: u8, flag: u8) -> BelowSecondP2Session {
    let p = program();
    let c = cpu(&p);
    let psw = c.psw_u16();
    BelowSecondP2Session::new(
        &p,
        c,
        psw,
        seeds(&p, source, flag),
        PostP2ControlPath::A,
        39,
        p2(),
        control(tcon),
    )
    .unwrap()
}
fn pc(n: u16) -> u16 {
    0x6400 + (n - 0x54f5)
}

#[test]
fn closed403_byte49_site_program_has_only39_below_retirements() {
    let p = program();
    let (nodes, inventory, pcs) = p.parts();
    assert_eq!((p.segment.base, p.segment.end), (0x6400, 0x6593));
    assert_eq!((nodes.len(), inventory.len(), pcs.len()), (49, 23, 39));
    assert_eq!(
        tail_nodes(false)
            .iter()
            .map(|n| n.identity.len)
            .sum::<usize>(),
        41
    );
    assert_eq!(
        pcs[21..],
        tail_nodes(false).iter().map(|n| n.pc).collect::<Vec<_>>()
    );
    assert!(!pcs.contains(&pc(0x5663)) && !pcs.contains(&pc(0x5675)) && !pcs.contains(&pc(0x5688)));
    assert_eq!(
        nodes
            .iter()
            .find(|n| n.pc == pc(0x5633))
            .unwrap()
            .identity
            .fields
            .addr16,
        pc(0x565d)
    );
}

#[test]
fn real39_step_flow_retains_first_generations_and_creates_same_value_second_p2() {
    for (source, tcon, flag) in [
        (0, 0x83, 0),
        (0x7f, 0x87, 0x80),
        (0x80, 0x8b, 0),
        (0xff, 0x8f, 0x80),
    ] {
        let mut s = session(source, tcon, flag);
        for _ in 0..39 {
            s.step().unwrap();
        }
        let r = s.report().unwrap();
        let p = &r.prefix.p2;
        assert!(p.completed && p.positive_completed && p.actual_handoff_observed);
        assert_eq!(p.steps.len(), 39);
        assert_eq!(p.audit.successful_retirements, 39);
        assert_eq!(
            (
                p.native_predecessor_retirements,
                p.algorithm_retirements,
                p.p2_instruction_retirements
            ),
            (6, 10, 2)
        );
        assert_eq!(
            (
                r.prefix.control_instruction_retirements,
                r.below_instruction_retirements
            ),
            (4, 18)
        );
        assert_eq!(p.stop_before_pc, Some(pc(0x5688)));
        assert_eq!(
            (
                p.peripheral_p2_journal.len(),
                r.prefix.peripheral_control_journal.len()
            ),
            (4, 6)
        );
        assert_eq!(
            (r.p2_generations.len(), r.control_generations.len()),
            (2, 2)
        );
        for (g, expected_pc, native_order, retired) in [
            (&r.p2_generations[0], 0x55c5, 5, 17),
            (&r.p2_generations[1], 0x5682, 12, 38),
            (&r.control_generations[0], 0x55c8, 6, 18),
            (&r.control_generations[1], 0x55d5, 8, 24),
        ] {
            assert_eq!(g.machine_id, 1);
            assert_eq!(g.writer_pc, pc(expected_pc));
            assert_eq!(g.native_write_ordinal, native_order);
            assert_eq!(g.retired_instruction, retired);
            assert_eq!(g.logical_write_ordinal, native_order + 55);
        }
        assert_eq!(p.p2_generation.as_ref().unwrap().writer_pc, pc(0x55c5));
        assert_eq!(
            r.prefix.control_generation.as_ref().unwrap().writer_pc,
            pc(0x55c8)
        );
        assert_eq!(r.p2_generations[0].value, 0xaf);
        assert_eq!(r.p2_generations[1].value, 0xaf);
        assert_eq!(r.p2_generations[1].generation_ordinal, 2);
        assert_eq!(r.control_generations[1].generation_ordinal, 2);
        assert_eq!(p.peripheral_p2_journal[3].same_value, Some(true));
        assert_eq!(r.prefix.control_final, [tcon & !4, 11]);
        assert_eq!(p.current.cpu.ssp, 0x4567);
        assert_eq!(p.current.cpu.lrb, 0x21);
        for address in [0x110u16, 0x112, 0x114] {
            let at = usize::from(address - 0x80);
            assert_eq!(&p.current.ram[at..at + 2], &[1, 0]);
            let writes: Vec<_> = p
                .audit
                .data_events
                .iter()
                .filter(|e| e.address == address && e.width == 16 && e.operation == "Write")
                .collect();
            assert_eq!(writes.len(), 1);
            let raw: Vec<_> = p
                .audit
                .raw_data_events
                .iter()
                .filter(|e| e.logical_ordinal == writes[0].ordinal)
                .collect();
            assert_eq!(raw.len(), 2);
            assert_eq!((raw[0].value, raw[1].value), (Some(1), Some(0)));
        }
        let jne = &p.steps[32];
        assert_eq!(
            (jne.outcome.pc_before, jne.outcome.pc_after),
            (pc(0x5661), pc(0x5671))
        );
        assert!(!jne.before.cpu.zf);
        assert_eq!(p.current.ram[0x12dusize - 0x80] & 0x80, 0);
        assert_eq!(p.current.cpu.zf, flag & 0x80 == 0);
        let count = s.inner.inner.inner.cpu.instructions;
        assert!(s.step().is_err());
        assert_eq!(s.inner.inner.inner.cpu.instructions, count);
    }
}

#[test]
fn actual_rol_uses_incoming_mb_carry_and_retains_full_noncarry_psw() {
    for source in [0, 0x7f, 0x80, 0xff] {
        let mut s = session(source, 0x83, 0);
        for _ in 0..22 {
            s.step().unwrap();
        }
        let r = s.report().unwrap();
        let mb = &r.prefix.p2.steps[20];
        let rol = &r.prefix.p2.steps[21];
        assert_eq!(rol.before, mb.after);
        let t = !(source.rotate_left(1));
        assert_eq!(rol.before.cpu.a as u8, t);
        assert_eq!(rol.before.cpu.cf, t & 0x80 != 0);
        assert_eq!(rol.after.cpu.a as u8, t.rotate_left(1));
        assert_eq!(rol.after.cpu.cf, t & 0x80 != 0);
        assert_eq!(rol.after.cpu.a & 0xff00, rol.before.cpu.a & 0xff00);
        assert_eq!(rol.full_psw_after & 0x7fff, rol.full_psw_before & 0x7fff);
        assert_eq!(rol.after.cpu.ssp, rol.before.cpu.ssp);
    }
}

#[test]
fn separate_invented_rol_probe_preserves_nonzero_ah_and_zf_not_reachable_from_below() {
    for (al, carry, zf) in [
        (0u8, false, false),
        (0x80, true, true),
        (0x7f, false, true),
        (0xff, true, false),
    ] {
        let bytes = vec![0x33];
        let digest = crate::audit_sha256::digest(&bytes);
        let mut c = cpu(&program());
        c.pc = 0x1000;
        c.a = 0xa500 | u16::from(al);
        c.dd = false;
        c.cf = carry;
        c.zf = zf;
        let full = c.psw_u16();
        let mut s = Session::new(
            ProgramSegment::new(0x1000, bytes, &digest).unwrap(),
            c,
            full,
            Permissions::new(vec![], vec![]).unwrap(),
            1,
        )
        .unwrap();
        s.begin_functional().unwrap();
        let expected = InstructionIdentity {
            index: 1851,
            len: 1,
            mnemonic: "ROLB A".into(),
            dd_before: false,
            dd_after: None,
            fields: Fields::default(),
        };
        s.step(&expected).unwrap();
        let a = s.diagnostic_snapshot().unwrap();
        assert_eq!(a.cpu.a, 0xa500 | u16::from((al << 1) | u8::from(carry)));
        assert_eq!(a.cpu.cf, al & 0x80 != 0);
        assert_eq!(a.cpu.zf, zf);
        assert!(a.cpu.hc);
        assert!(!a.cpu.dd);
        assert_eq!(s.cpu.psw_u16() & 0x7fff, full & 0x7fff);
    }
}

#[test]
fn tcon_second_generation_reads_actual_first_bit_and_keeps_first_identity() {
    for tcon in [0x83, 0x87, 0x8b, 0x8f] {
        let mut s = session(0x80, tcon, 0);
        for _ in 0..24 {
            s.step().unwrap();
        }
        let r = s.report().unwrap();
        let step = &r.prefix.p2.steps[23];
        assert!(!step.after.cpu.zf);
        assert_eq!(step.after.cpu.cf, step.before.cpu.cf);
        assert_eq!(step.after.cpu.a, step.before.cpu.a);
        assert_eq!(
            step.full_psw_after & !0x4000,
            step.full_psw_before & !0x4000
        );
        assert_eq!(r.control_generations[0].value, tcon | 4);
        assert_eq!(r.control_generations[1].value, tcon & !4);
        assert_eq!(r.prefix.peripheral_control_journal[3].value, tcon | 4);
        assert_eq!(r.prefix.peripheral_control_journal[4].value, tcon | 4);
        assert_eq!(
            r.prefix
                .control_generation
                .as_ref()
                .unwrap()
                .generation_ordinal,
            1
        );
        assert_eq!(r.second_control_generation.unwrap().generation_ordinal, 2);
    }
}

#[test]
fn wrong_budget_entry_other_path_and_ready_canaries_are_refused_before_execution() {
    for budget in [0, 16, 21, 38, 40, 255] {
        let p = program();
        let c = cpu(&p);
        let full = c.psw_u16();
        assert!(BelowSecondP2Session::new(
            &p,
            c,
            full,
            seeds(&p, 0, 0),
            PostP2ControlPath::A,
            budget,
            p2(),
            control(0x83)
        )
        .is_err());
    }
    for path in [
        PostP2ControlPath::B,
        PostP2ControlPath::C,
        PostP2ControlPath::D,
    ] {
        let p = program();
        let c = cpu(&p);
        let full = c.psw_u16();
        assert!(BelowSecondP2Session::new(
            &p,
            c,
            full,
            seeds(&p, 0, 0),
            path,
            39,
            p2(),
            control(0x83)
        )
        .is_err());
    }
    for entry in [pc(0x55d2), pc(0x5682), 0x55d2, 0x5682] {
        let p = program();
        let mut c = cpu(&p);
        c.pc = entry;
        let full = c.psw_u16();
        assert!(BelowSecondP2Session::new(
            &p,
            c,
            full,
            seeds(&p, 0, 0),
            PostP2ControlPath::A,
            39,
            p2(),
            control(0x83)
        )
        .is_err());
    }
    let p = program();
    let mut d = data(&p, 0, 0);
    d.insert(0x110, 1);
    let r = std::array::from_fn(|n| d[&(0x108 + n as u16)]);
    let er = std::array::from_fn(|n| u16::from_le_bytes([r[n * 2], r[n * 2 + 1]]));
    assert_eq!(
        BelowSecondP2Seeds::new(&p, d, [[0; 4]; 8], r, er)
            .err()
            .unwrap()
            .code,
        "BelowSecondCanarySeedsRejected"
    );
}

#[test]
fn changed_rol_or_jne_operand_is_refused_before_that_instruction_retires() {
    for (site, offset, value, before) in [(0x55d2, 0, 0x43, 21), (0x5661, 1, 0, 32)] {
        let mut p = program();
        let at = usize::from(p.pc(site) - p.entry_pc()) + offset;
        p.segment.bytes[at] = value;
        p.segment.digest = crate::audit_sha256::digest(&p.segment.bytes);
        let c = cpu(&p);
        let full = c.psw_u16();
        let mut s = BelowSecondP2Session::new(
            &p,
            c,
            full,
            seeds(&p, 0, 0),
            PostP2ControlPath::A,
            39,
            p2(),
            control(0x83),
        )
        .unwrap();
        for _ in 0..before {
            s.step().unwrap();
        }
        let instructions = s.inner.inner.inner.cpu.instructions;
        assert_eq!(s.step().unwrap_err().code, "SelectedInstructionMismatch");
        assert_eq!(s.inner.inner.inner.cpu.instructions, instructions);
        assert_eq!(s.inner.inner.inner.bus.p2_accesses().len(), 2);
    }
}

#[test]
fn post_start_ram_al_dd_and_second_machine_mutations_are_not_handoffs() {
    for mutation in [0, 1] {
        let mut s = session(0, 0x83, 0);
        for _ in 0..21 {
            s.step().unwrap();
        }
        if mutation == 0 {
            s.inner.inner.inner.cpu.a ^= 1;
        } else {
            s.inner.inner.inner.cpu.dd = true;
        }
        assert_eq!(s.step().unwrap_err().code, "P2LiveStateChanged");
        assert_eq!(s.inner.inner.inner.cpu.instructions, 21);
    }
    let mut s = session(0, 0x83, 0);
    s.step().unwrap();
    let before = s.inner.inner.inner.diagnostic_snapshot().unwrap();
    s.inner.inner.inner.bus.write_data_u16(0x110, 1);
    assert_eq!(
        s.inner.inner.inner.current_fault().unwrap_err().code,
        "OriginalDataOutsideInstruction"
    );
    assert_eq!(s.inner.inner.inner.diagnostic_snapshot().unwrap(), before);
    let mut a = session(0, 0x83, 0);
    let mut b = session(0, 0x83, 0);
    a.step().unwrap();
    b.step().unwrap();
    a.inner.inner.inner = b.inner.inner.inner;
    assert_eq!(a.step().unwrap_err().code, "P2MachineSubstitutionRejected");
}

#[test]
fn second_boundary_reinitialization_and_host_sfr_attempts_leave_storage_unchanged() {
    for steps in [23, 37] {
        let mut s = session(0, 0x8f, 0);
        for _ in 0..steps {
            s.step().unwrap();
        }
        let bus = &mut s.inner.inner.inner.bus;
        let p2 = bus.p2_output_latch();
        let control = bus.post_p2_control();
        assert!(bus.initialize_p2_output_latch(0).is_err());
        assert!(bus.initialize_post_p2_control(0x83, 0).is_err());
        assert_eq!(bus.p2_output_latch(), p2);
        assert_eq!(bus.post_p2_control(), control);
        bus.write_data_u8(if steps == 23 { 0x40 } else { 0x24 }, 0);
        assert_eq!(
            s.inner.inner.inner.current_fault().unwrap_err().code,
            "OriginalDataOutsideInstruction"
        );
        assert_eq!(s.inner.inner.inner.bus.p2_output_latch(), p2);
        assert_eq!(s.inner.inner.inner.bus.post_p2_control(), control);
    }
}

#[test]
fn second_sfr_word_or_cross_pc_requests_cannot_create_services() {
    for (address, width) in [(0x24, 16), (0x40, 16), (0x41, 8), (0x46, 8), (0x47, 8)] {
        let mut s = session(0, 0x83, 0);
        s.step().unwrap();
        let old = s.inner.inner.inner.bus.post_p2_control();
        s.inner.inner.inner.bus.set_native_pc(pc(0x5682));
        s.inner.inner.inner.bus.set_p2_access_pc(Some(pc(0x5682)));
        assert!(s.inner.inner.inner.data_read(address, width).is_err());
        assert_eq!(s.inner.inner.inner.bus.post_p2_control(), old);
        assert!(s.inner.inner.inner.bus.p2_accesses().is_empty());
    }
}

#[test]
fn executing_second_capabilities_reject_wrong_pc_and_word_access_after_real_prefix() {
    for (retired, selected_pc, wrong_pc, index, address, second_p2) in [
        (23, pc(0x55d5), pc(0x55d3), 1779, 0x40, false),
        (37, pc(0x5682), pc(0x5680), 1647, 0x24, true),
    ] {
        for (wrong_site, writing) in [(false, false), (false, true), (true, false), (true, true)] {
            let mut s = session(0, 0x8f, 0);
            for _ in 0..retired {
                s.step().unwrap();
            }
            let machine = &mut s.inner.inner.inner;
            let before = machine.diagnostic_snapshot().unwrap();
            let old_p2 = machine.bus.p2_output_latch();
            let old_control = machine.bus.post_p2_control();
            let old_p2_services = machine.bus.p2_accesses();
            let old_audit = machine.report();
            let audit = machine.bus.audit.as_ref().unwrap();
            // Deliberately enter the private audit permission seam, rather
            // than the generic host API's earlier Functional-phase refusal.
            // This is not an observed decoded instruction or retirement.
            let attempted_pc = if wrong_site { wrong_pc } else { selected_pc };
            audit.begin_step(attempted_pc).unwrap();
            audit.set_instruction(index);
            if second_p2 {
                assert_eq!(audit.p2_handoff_selected(attempted_pc, index), !wrong_site);
                assert!(!audit.p2_handoff_selected(wrong_pc, index));
                assert!(!audit.p2_handoff_selected(selected_pc, index ^ 1));
            } else {
                assert_eq!(
                    audit.post_p2_control_selected(attempted_pc, index),
                    (!wrong_site).then_some((address, selected_pc))
                );
                assert_eq!(audit.post_p2_control_selected(wrong_pc, index), None);
                assert_eq!(audit.post_p2_control_selected(selected_pc, index ^ 1), None);
            }
            assert_eq!(machine.report().phase, "Executing");
            machine.bus.set_native_pc(attempted_pc);
            // Even a forged storage-side enable cannot overrule the closed
            // selected-site DATA permission or turn a byte right into a word.
            if second_p2 {
                machine.bus.set_p2_access_pc(Some(attempted_pc));
            } else {
                machine
                    .bus
                    .set_control_access(Some((address, attempted_pc)));
            }
            let width = if wrong_site { 8 } else { 16 };
            match (writing, width) {
                (false, 8) => {
                    machine.bus.read_data_u8(address);
                }
                (false, 16) => {
                    machine.bus.read_data_u16(address);
                }
                (true, 8) => machine.bus.write_data_u8(address, 0),
                (true, 16) => machine.bus.write_data_u16(address, 0),
                _ => unreachable!(),
            }
            let fault = machine.current_fault().unwrap_err();
            assert_eq!(
                fault.code,
                if wrong_site {
                    "OriginalDataOutsideInstruction"
                } else if writing {
                    "OriginalLogicalWriteDenied"
                } else {
                    "OriginalLogicalReadDenied"
                }
            );
            assert_eq!(machine.diagnostic_snapshot().unwrap(), before);
            assert_eq!(machine.bus.p2_output_latch(), old_p2);
            assert_eq!(machine.bus.post_p2_control(), old_control);
            assert_eq!(machine.bus.p2_accesses(), old_p2_services);
            assert!(machine.bus.control_accesses().is_empty());
            let after = machine.report();
            assert_eq!(after.successful_retirements, retired);
            assert_eq!(after.execution_calls, retired);
            assert_eq!(after.raw_data_events, old_audit.raw_data_events);
            assert_eq!(after.data_events.len(), old_audit.data_events.len() + 1);
            let refused = after.data_events.last().unwrap();
            assert_eq!(refused.pc, Some(attempted_pc));
            assert_eq!(refused.instruction_index, Some(index));
            assert_eq!((refused.address, refused.width), (address, width));
            assert!(!refused.serviced);
            assert_eq!(refused.value, None);
            assert_eq!(refused.write_ordinal, None);
            assert_eq!(refused.refusal.as_ref().unwrap(), &fault);
        }
    }
}

#[test]
fn observed_ssp_and_attempted_synthetic_return_frame_cannot_cross_bounded_stop() {
    for retired in [37, 39] {
        let mut s = session(0, 0x83, 0);
        for _ in 0..retired {
            s.step().unwrap();
        }
        let before = s.inner.inner.inner.diagnostic_snapshot().unwrap();
        let events = s.inner.inner.inner.report();
        // The observed architectural SSP itself changes; no JSON ownership
        // label is involved. Neither next-P2 nor sealed RT boundary admits it.
        s.inner.inner.inner.cpu.ssp = before.cpu.ssp.wrapping_sub(2);
        assert_eq!(s.report().unwrap_err().code, "P2LiveStateChanged");
        assert_eq!(s.step().unwrap_err().code, "P2LiveStateChanged");
        let after = s.inner.inner.inner.diagnostic_snapshot().unwrap();
        assert_eq!(after.cpu.ssp, before.cpu.ssp.wrapping_sub(2));
        assert_eq!(after.cpu.instructions, retired);
        assert_eq!(after.cpu.pc, before.cpu.pc);
        assert_eq!(after.ram, before.ram);
        assert_eq!(s.inner.inner.inner.report().data_events, events.data_events);
    }
    let mut s = session(0, 0x83, 0);
    for _ in 0..38 {
        s.step().unwrap();
    }
    let machine = &mut s.inner.inner.inner;
    let before = machine.diagnostic_snapshot().unwrap();
    let events = machine.report();
    let proposed_frame = before.cpu.ssp.wrapping_sub(2);
    // Actual production Bus attempt to supply a return PC at a fabricated
    // stack slot after G2. It must not publish any raw byte or native writer.
    machine.bus.write_data_u16(proposed_frame, pc(0x5688));
    let fault = machine.current_fault().unwrap_err();
    assert_eq!(fault.code, "OriginalDataOutsideInstruction");
    assert_eq!(fault.address, Some(i64::from(proposed_frame)));
    assert_eq!(machine.diagnostic_snapshot().unwrap(), before);
    let after = machine.report();
    assert_eq!(after.successful_retirements, 38);
    assert_eq!(after.raw_data_events, events.raw_data_events);
    assert_eq!(after.data_events.len(), events.data_events.len() + 1);
    let refused = after.data_events.last().unwrap();
    assert_eq!(refused.requested_value, Some(pc(0x5688)));
    assert!(!refused.serviced);
    assert_eq!(refused.write_ordinal, None);
}
