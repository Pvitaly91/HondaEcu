//! Invented production-executor probes only; no original ROM bytes or owners.
use super::*;

fn program() -> ClosedP2HandoffProgram {
    ClosedP2HandoffProgram::explicit_invented_public_fixture()
}
fn cpu(p: &ClosedP2HandoffProgram, dd: bool, sf: bool) -> Cpu {
    Cpu {
        pc: p.entry_pc(),
        a: 0xbe31,
        ssp: 0x4567,
        lrb: 0x21,
        zf: true,
        cf: true,
        hc: true,
        dd,
        sf,
        psw_other: 0x137,
        cycles: 0,
        instructions: 0,
        halted: false,
    }
}
fn seeds(p: &ClosedP2HandoffProgram, path: P2HandoffPath) -> P2HandoffSeeds {
    let (_, inventory, _) = p.parts(path);
    let mut data: BTreeMap<_, _> = inventory
        .into_iter()
        .map(|address| (address, 0xa5))
        .collect();
    let word = if path == P2HandoffPath::A {
        0x00bfu16
    } else {
        0xffc0u16
    };
    data.insert(0x19a, word as u8);
    data.insert(0x19b, (word >> 8) as u8);
    data.insert(0x130, 4);
    data.insert(0x11b, 0x37);
    data.insert(0x12d, if path == P2HandoffPath::B { 0x80 } else { 0 });
    data.insert(0x12e, if path == P2HandoffPath::C { 0x20 } else { 0 });
    data.insert(0x192, 0x81);
    data.insert(0x193, 0x83);
    data.insert(0x108, 0xff);
    let r = std::array::from_fn(|n| data[&(0x108 + n as u16)]);
    let er = std::array::from_fn(|n| u16::from_le_bytes([r[n * 2], r[n * 2 + 1]]));
    P2HandoffSeeds::new(p, data, [[0x1234; 4]; 8], r, er).unwrap()
}
fn snapshot(value: u8) -> P2Snapshot {
    P2Snapshot {
        value,
        p2io: 0xff,
        p2sf: 7,
        provenance: "TechnicalArchitecturalP2LatchSnapshot_NoNativeWriterGeneration".into(),
    }
}
fn session(path: P2HandoffPath, old: u8, dd: bool, sf: bool) -> P2HandoffSession {
    let p = program();
    let c = cpu(&p, dd, sf);
    let psw = c.psw_u16();
    P2HandoffSession::new(
        &p,
        c,
        psw,
        seeds(&p, path),
        path,
        path.budget(),
        snapshot(old),
    )
    .unwrap()
}
fn finish(s: &mut P2HandoffSession, budget: u8) -> P2HandoffReport {
    for _ in 0..budget {
        s.step().unwrap();
    }
    s.report().unwrap()
}

#[test]
fn closed_invented_program_has26_nodes211_bytes_and_exact_new_budgets() {
    let p = program();
    assert_eq!((p.segment.base, p.segment.end), (0x6400, 0x64d3));
    // Independently typed host encoder/recognizer identity, frozen before the
    // first Rust run; never taken from this emitter's actual runtime output.
    assert_eq!(
        p.program_sha256(),
        "0cf726dff81de822b45efbb2f565a790132d307b1586f7f075e08f16a8e716e4"
    );
    for (path, n, target) in [
        (P2HandoffPath::A, 17, 0x64d0),
        (P2HandoffPath::B, 19, 0x64a1),
        (P2HandoffPath::C, 20, 0x64a1),
        (P2HandoffPath::D, 22, 0x64a1),
    ] {
        let (nodes, inventory, pcs) = p.parts(path);
        assert_eq!(nodes.len(), 26);
        assert_eq!(inventory.len(), 16);
        assert_eq!(pcs.len(), n as usize);
        assert_eq!(pcs.last(), Some(&target));
        assert_eq!(path.budget(), n);
        assert!(!inventory.contains(&0x24));
    }
}

#[test]
fn four_paths_preserve_real_cpu_state_except_documented_p2_zf_and_pc() {
    for path in [
        P2HandoffPath::A,
        P2HandoffPath::B,
        P2HandoffPath::C,
        P2HandoffPath::D,
    ] {
        for old in [0, 0xff, 0xa5, 0x0f, 0xf0] {
            for dd in [false, true] {
                for sf in [false, true] {
                    let mut s = session(path, old, dd, sf);
                    let r = finish(&mut s, path.budget());
                    let last = r.steps.last().unwrap();
                    let al = last.before.cpu.a as u8;
                    // A focused architectural RMW rule, not the independent full-path
                    // oracle: it must consume the AL already on this actual machine.
                    let value = if path == P2HandoffPath::A {
                        old | al
                    } else {
                        old & al
                    };
                    assert!(
                        r.completed
                            && r.positive_completed
                            && r.actual_handoff_observed
                            && !r.boundary_only
                    );
                    assert_eq!(r.p2_initial, old);
                    assert_eq!(r.p2_final, value);
                    assert_eq!(last.after.cpu.a, last.before.cpu.a);
                    assert_eq!(
                        last.full_psw_after,
                        (last.full_psw_before & !0x4000) | if value == 0 { 0x4000 } else { 0 }
                    );
                    assert_eq!(last.after.cpu.ssp, last.before.cpu.ssp);
                    assert_eq!(last.after.cpu.lrb, last.before.cpu.lrb);
                    assert_eq!(last.after.cpu.sf, sf);
                    assert_eq!(last.after.ram, last.before.ram);
                    assert_eq!(last.after.cpu.pc, last.before.cpu.pc + 3);
                    assert_eq!(r.native_predecessor_retirements, 6);
                    assert_eq!(r.algorithm_retirements, u64::from(path.budget() - 7));
                    assert_eq!(r.p2_instruction_retirements, 1);
                    assert_eq!(r.audit.successful_retirements, u64::from(path.budget()));
                    assert_eq!(
                        r.audit.diagnostic_events.len(),
                        4 * usize::from(path.budget()) + 4
                    );
                    assert_eq!(r.p2_step_snapshots.len(), usize::from(path.budget()));
                    assert!(r.p2_step_snapshots[..usize::from(path.budget() - 1)]
                        .iter()
                        .all(|e| e.before == old && e.after == old));
                    assert_eq!(r.peripheral_p2_journal.len(), 2);
                    assert_eq!(r.peripheral_p2_journal[0].operation, "Read");
                    assert_eq!(r.peripheral_p2_journal[0].value, old);
                    assert_eq!(r.peripheral_p2_journal[1].operation, "Write");
                    assert_eq!(r.peripheral_p2_journal[1].value, value);
                    assert!(r.audit.permissions.reads.iter().all(|e| e.address >= 0x80));
                    assert!(r
                        .audit
                        .permissions
                        .writes
                        .iter()
                        .all(|e| e.access.address >= 0x80));
                }
            }
        }
    }
}

#[test]
fn p2_initial_snapshot_is_not_a_ram_seed_or_native_generation() {
    let mut s = session(P2HandoffPath::D, 0, false, false);
    for _ in 0..21 {
        s.step().unwrap();
    }
    let r = s.report().unwrap();
    assert!(!r.completed);
    assert_eq!(r.current.cpu.pc, 0x64a1);
    assert_eq!(r.p2_initial, 0);
    assert_eq!(r.p2_final, 0);
    assert!(r.p2_generation.is_none());
    assert!(r.peripheral_p2_journal.is_empty());
    assert_eq!(
        r.audit
            .data_events
            .iter()
            .filter(|e| e.phase == "Seed")
            .count(),
        48
    );
    assert!(r.audit.data_events.iter().all(|e| e.address != 0x24));
    assert_eq!(r.ownership["P2InitialNativeOwner"], "NotEstablished");
    assert_eq!(r.ownership["P2FinalGeneration"], "NotEstablished");
}

#[test]
fn same_value_store_has_fresh_linked_generation_and_actual_latch_old_metadata() {
    for (path, old) in [(P2HandoffPath::A, 0xff), (P2HandoffPath::D, 0xf0)] {
        let mut s = session(path, old, false, true);
        let r = finish(&mut s, path.budget());
        assert_eq!(r.p2_final, old);
        let event = &r.peripheral_p2_journal[1];
        let g = r.p2_generation.as_ref().unwrap();
        let logical = &r.audit.data_events[event.logical_ordinal as usize];
        let raw = &r.audit.raw_data_events[event.raw_ordinal as usize];
        assert_eq!(event.same_value, Some(true));
        assert_eq!(logical.old_value, Some(u16::from(old)));
        assert_eq!(raw.old_value, Some(old));
        assert_eq!(g.generation_ordinal, 1);
        assert_eq!(g.machine_id, 1);
        assert_eq!(
            g.native_write_ordinal,
            if path == P2HandoffPath::D { 7 } else { 5 }
        );
        assert_eq!(
            g.logical_write_ordinal,
            if path == P2HandoffPath::D { 55 } else { 53 }
        );
        assert_eq!(
            g.raw_write_ordinal,
            if path == P2HandoffPath::D { 88 } else { 86 }
        );
        assert_eq!(
            r.ownership["P2FinalGeneration"],
            "VerifiedWithinTechnicalSession"
        );
        assert_eq!(r.ownership["PhysicalP2Owner"], "NotEstablished");
    }
}

#[test]
fn scratch_ram0024_never_supplies_p2_old_value_or_read_result() {
    for old in [0, 0xff] {
        let mut s = session(P2HandoffPath::B, old, false, false);
        let r = finish(&mut s, 19);
        let row = &r.peripheral_p2_journal[1];
        let data = &r.audit.data_events[row.logical_ordinal as usize];
        let raw = &r.audit.raw_data_events[row.raw_ordinal as usize];
        assert_eq!(data.old_value, Some(u16::from(old)));
        assert_eq!(raw.old_value, Some(old));
        assert_eq!(r.peripheral_p2_journal[0].value, old);
    }
}

#[test]
fn wrong_mode_direction_mux_and_fabricated_ownership_are_refused_before_execution() {
    for change in 0..5 {
        let p = program();
        let c = cpu(&p, false, false);
        let psw = c.psw_u16();
        let mut snap = snapshot(0xa5);
        match change {
            0 => snap.p2io = 0,
            1 => snap.p2io = 0xfe,
            2 => snap.p2sf = 0x87,
            3 => snap.p2sf = 0,
            _ => snap.provenance = "StartupExecutionObserved_CurrentNativeOwner".into(),
        }
        assert_eq!(
            P2HandoffSession::new(
                &p,
                c,
                psw,
                seeds(&p, P2HandoffPath::D),
                P2HandoffPath::D,
                22,
                snap
            )
            .err()
            .unwrap()
            .code,
            "P2PrimaryOutputModeRequired"
        );
    }
    assert!(serde_json::from_str::<P2Snapshot>(
        r#"{"value":1,"p2io":255,"p2sf":7,"provenance":"x","native_owner":true}"#
    )
    .is_err());
}

#[test]
fn closed_budget_and_original_entry_cannot_be_host_widened_or_replaced_by_p2_entry() {
    for budget in [0, 1, 16, 18, 19, 20, 21, 23, 255] {
        let p = program();
        let c = cpu(&p, false, false);
        let psw = c.psw_u16();
        assert_eq!(
            P2HandoffSession::new(
                &p,
                c,
                psw,
                seeds(&p, P2HandoffPath::D),
                P2HandoffPath::D,
                budget,
                snapshot(0)
            )
            .err()
            .unwrap()
            .code,
            "P2HandoffEntryRejected"
        );
    }
    let p = program();
    let mut c = cpu(&p, false, false);
    c.pc = 0x64a1;
    let psw = c.psw_u16();
    assert_eq!(
        P2HandoffSession::new(
            &p,
            c,
            psw,
            seeds(&p, P2HandoffPath::D),
            P2HandoffPath::D,
            22,
            snapshot(0)
        )
        .err()
        .unwrap()
        .code,
        "P2HandoffEntryRejected"
    );
}

#[test]
fn legacy16_and_m2bu21_budget_contracts_are_unchanged() {
    let p = program();
    let c = cpu(&p, false, false);
    let psw = c.psw_u16();
    assert_eq!(
        Session::new(
            p.segment_copy(),
            c,
            psw,
            Permissions::new(vec![], vec![]).unwrap(),
            17
        )
        .err()
        .unwrap()
        .code,
        "InvalidEntryState"
    );
    let old = ClosedEntryContinuityProgram::explicit_invented_public_fixture();
    let (_, _, inventory, _) = old.p2_extension_metadata(EntryContinuityPath::D);
    let data: BTreeMap<_, _> = inventory.into_iter().map(|a| (a, 0)).collect();
    let seeds = EntryContinuitySeeds::new(&old, data, [[0; 4]; 8], [0; 8], [0; 4]).unwrap();
    let mut c = cpu(&p, false, false);
    c.pc = old.entry_pc();
    let psw = c.psw_u16();
    assert_eq!(
        super::super::EntryContinuitySession::new(&old, c, psw, seeds, EntryContinuityPath::D, 22)
            .err()
            .unwrap()
            .code,
        "EntryContinuityEntryRejected"
    );
    assert_eq!(EntryContinuityPath::D.budget(), 21);
    assert!(Permissions::new(
        vec![Access {
            address: 0x24,
            width: 8
        }],
        vec![]
    )
    .is_err());
}

#[test]
fn host_register_latch_and_second_machine_substitutions_are_rejected() {
    for change in 0..4 {
        let mut s = session(P2HandoffPath::D, 0xa5, false, false);
        s.step().unwrap();
        match change {
            0 => s.inner.cpu.pc = 0x64a1,
            1 => s.inner.cpu.a ^= 1,
            2 => s.inner.cpu.dd = !s.inner.cpu.dd,
            _ => s.last_p2 ^= 1,
        }
        assert_eq!(s.step().unwrap_err().code, "P2LiveStateChanged");
        assert_eq!(s.inner.cpu.instructions, 1);
    }
    let mut a = session(P2HandoffPath::D, 0xa5, false, false);
    let mut b = session(P2HandoffPath::D, 0xa5, false, false);
    for _ in 0..6 {
        a.step().unwrap();
        b.step().unwrap();
    }
    a.inner = b.inner;
    assert_eq!(a.step().unwrap_err().code, "P2MachineSubstitutionRejected");
}

#[test]
fn no_host_reseed_or_p2_access_from_another_pc_width_or_neighbor() {
    for (address, width, write) in [
        (0x24, 8, false),
        (0x24, 8, true),
        (0x24, 16, false),
        (0x24, 16, true),
        (0x25, 8, false),
        (0x25, 8, true),
        (0x26, 8, true),
        (0x23, 8, false),
        (0x22, 8, true),
        (0x2c, 8, true),
    ] {
        let mut s = session(P2HandoffPath::D, 0xa5, false, false);
        // Even an internally forged legacy broad-enable cannot bypass audit.
        s.inner.bus.set_p2_access(true);
        s.inner.bus.set_native_pc(s.p2_pc);
        if write {
            assert!(s.inner.data_write(address, width, 1).is_err());
        } else {
            assert!(s.inner.data_read(address, width).is_err());
        }
        assert_eq!(s.inner.bus.p2_output_latch(), Some(0xa5));
        assert!(s.inner.bus.p2_accesses().is_empty());
    }
    let mut s = session(P2HandoffPath::D, 0xa5, false, false);
    for _ in 0..21 {
        s.step().unwrap();
    }
    assert!(s.inner.bus.initialize_p2_output_latch(0xa5).is_err());
    assert!(s.inner.seed_byte(0x24, 0xff).is_err());
    assert_eq!(s.inner.bus.p2_output_latch(), Some(0xa5));
}

#[test]
fn second_p2_and_next_downstream_instructions_are_never_selected() {
    for path in [P2HandoffPath::A, P2HandoffPath::D] {
        let mut s = session(path, 0xa5, false, false);
        let r = finish(&mut s, path.budget());
        assert_eq!(
            r.stop_before_pc,
            Some(if path == P2HandoffPath::A {
                0x64d3
            } else {
                0x64a4
            })
        );
        assert!(s.step().is_err());
        assert_eq!(s.inner.cpu.instructions, u64::from(path.budget()));
        assert_eq!(s.inner.bus.p2_accesses().len(), 2);
        assert!(!s
            .inner
            .bus
            .audit
            .as_ref()
            .unwrap()
            .p2_handoff_selected(s.p2_pc, if path == P2HandoffPath::A { 1647 } else { 350 }));
    }
}

#[test]
fn wrong_decoded_terminal_form_refuses_before_peripheral_service() {
    let mut p = program();
    let offset = usize::from(p.p2_pc(P2HandoffPath::D) - p.entry_pc());
    p.segment.bytes[offset + 2] = 0xe1;
    p.segment.digest = crate::audit_sha256::digest(&p.segment.bytes);
    let c = cpu(&p, false, false);
    let psw = c.psw_u16();
    let mut s = P2HandoffSession::new(
        &p,
        c,
        psw,
        seeds(&p, P2HandoffPath::D),
        P2HandoffPath::D,
        22,
        snapshot(0xa5),
    )
    .unwrap();
    for _ in 0..21 {
        s.step().unwrap();
    }
    assert_eq!(s.step().unwrap_err().code, "SelectedInstructionMismatch");
    assert!(s.inner.bus.p2_accesses().is_empty());
    assert_eq!(s.inner.bus.p2_output_latch(), Some(0xa5));
}

#[test]
fn opaque_source_extent_digest_and_source_binding_refuse_without_cpu() {
    let binding = OriginalRomSourceBinding {
        base_commit: super::super::ORIGINAL_ROM_BASE_COMMIT.into(),
        contract_sha256: super::super::ORIGINAL_ROM_CONTRACT_SHA256.into(),
        whole_rom_sha256: "0".repeat(64),
        source_admission: "M2bsHostVerifiedOriginalRom".into(),
    };
    assert_eq!(
        ClosedP2HandoffProgram::admit_host_verified_segment(
            0x54f5,
            vec![0xa5; 210],
            &"0".repeat(64),
            binding.clone()
        )
        .err()
        .unwrap()
        .code,
        "P2HandoffSegmentRejected"
    );
    assert_eq!(
        ClosedP2HandoffProgram::admit_host_verified_segment(
            0x54f5,
            vec![0xa5; 211],
            &"0".repeat(64),
            binding.clone()
        )
        .err()
        .unwrap()
        .code,
        "ProgramDigestMismatch"
    );
    let bytes = vec![0xa5; 211];
    let digest = crate::audit_sha256::digest(&bytes);
    let mut wrong = binding;
    wrong.whole_rom_sha256 = "0".repeat(63);
    assert_eq!(
        ClosedP2HandoffProgram::admit_host_verified_segment(0x54f5, bytes, &digest, wrong)
            .err()
            .unwrap()
            .code,
        "OriginalSourceBindingRejected"
    );
}
