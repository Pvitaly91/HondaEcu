//! Invented-only production-executor regressions. No OEM instruction stream.
use super::*;

fn cpu(program: &ClosedEntryContinuityProgram, dd: bool, sf: bool) -> Cpu {
    Cpu {
        pc: program.entry_pc(),
        a: 0x5a31,
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
fn seeds(
    program: &ClosedEntryContinuityProgram,
    path: EntryContinuityPath,
) -> EntryContinuitySeeds {
    let mut data: BTreeMap<_, _> = program
        .inventory
        .iter()
        .map(|address| (*address, 0xa5))
        .collect();
    let word = if path == EntryContinuityPath::A {
        0x00bfu16
    } else {
        0x00c0u16
    };
    data.insert(0x19a, word as u8);
    data.insert(0x19b, (word >> 8) as u8);
    data.insert(
        0x130,
        if path == EntryContinuityPath::JbrAlternate {
            0
        } else {
            4
        },
    );
    data.insert(
        0x11b,
        if path == EntryContinuityPath::JneAlternate {
            15
        } else {
            0x37
        },
    );
    data.insert(
        0x12d,
        if path == EntryContinuityPath::B {
            0x80
        } else {
            0
        },
    );
    data.insert(
        0x12e,
        if path == EntryContinuityPath::C {
            0x20
        } else {
            0
        },
    );
    data.insert(0x192, 0x81);
    data.insert(0x193, 0x83);
    // MOVB r0,#FF must retain even a same-value write.
    data.insert(0x108, 0xff);
    let r = std::array::from_fn(|n| data[&(0x108 + n as u16)]);
    let er = std::array::from_fn(|n| u16::from_le_bytes([r[2 * n], r[2 * n + 1]]));
    let banks =
        std::array::from_fn(|n| std::array::from_fn(|k| 0x2000 + n as u16 * 31 + k as u16 * 7));
    EntryContinuitySeeds::new(program, data, banks, r, er).unwrap()
}
fn session(path: EntryContinuityPath, dd: bool, sf: bool) -> EntryContinuitySession {
    let program = ClosedEntryContinuityProgram::explicit_invented_public_fixture();
    let cpu = cpu(&program, dd, sf);
    let psw = cpu.psw_u16();
    let seeds = seeds(&program, path);
    EntryContinuitySession::new(&program, cpu, psw, seeds, path, path.budget()).unwrap()
}
fn ram(snapshot: &Snapshot, address: u16) -> u8 {
    snapshot.ram[usize::from(address - snapshot.ram_range[0])]
}

#[test]
fn closed_entry_inventory_is24_nodes208_bytes_and_has_exact_route_budgets() {
    let p = ClosedEntryContinuityProgram::explicit_invented_public_fixture();
    assert_eq!(p.nodes.len(), 24);
    assert_eq!((p.segment.base, p.segment.end), (0x6200, 0x62d0));
    assert_eq!(p.inventory.len(), 16);
    assert!(p.inventory.contains(&0x130));
    assert!(!p.inventory.contains(&0x128));
    for (path, budget, terminal) in [
        (EntryContinuityPath::A, 16, 0x62d0),
        (EntryContinuityPath::B, 18, 0x62a1),
        (EntryContinuityPath::C, 19, 0x62a1),
        (EntryContinuityPath::D, 21, 0x62a1),
        (EntryContinuityPath::JbrAlternate, 1, 0x623e),
        (EntryContinuityPath::JneAlternate, 6, 0x620e),
    ] {
        assert_eq!(path.budget(), budget);
        assert_eq!(p.path_pcs(path).len(), usize::from(budget));
        assert_eq!(p.terminal(path), terminal);
    }
}

#[test]
fn invented_four_paths_use_actual_jne_handoff_on_one_continuous_machine() {
    for path in [
        EntryContinuityPath::A,
        EntryContinuityPath::B,
        EntryContinuityPath::C,
        EntryContinuityPath::D,
    ] {
        for dd in [false, true] {
            for sf in [false, true] {
                let mut s = session(path, dd, sf);
                for _ in 0..path.budget() {
                    s.step().unwrap();
                }
                let r = s.report().unwrap();
                assert!(
                    r.completed
                        && r.positive_completed
                        && r.actual_handoff_observed
                        && !r.boundary_only
                );
                assert_eq!(r.audit.successful_retirements, u64::from(path.budget()));
                assert_eq!(r.audit.execution_calls, u64::from(path.budget()));
                assert_eq!(r.current.cpu.instructions, u64::from(path.budget()));
                assert_eq!(r.native_predecessor_retirements, 6);
                assert_eq!(r.algorithm_retirements, u64::from(path.budget() - 6));
                assert_eq!(r.steps[5].outcome.pc_before, 0x620c);
                assert_eq!(r.steps[5].outcome.pc_after, 0x627a);
                assert_eq!(r.steps[6].before, r.steps[5].after);
                assert!(r.steps[6].before.cpu.dd);
                assert!(!r.steps[6].after.cpu.dd);
                assert_eq!(r.current.cpu.sf, sf);
                assert_eq!(r.current.cpu.ssp, 0x4567);
                assert_eq!(r.current.cpu.lrb, 0x21);
                assert!(r.current.cpu.hc);
                assert_eq!(ram(&r.current, 0x108), 0xff);
                assert_eq!(
                    ram(&r.current, 0x10a),
                    if path == EntryContinuityPath::A {
                        0xbf
                    } else {
                        0xc0
                    }
                );
                assert_eq!(ram(&r.current, 0x10b), 0);
                assert_eq!(r.current.cpu.a >> 8, 0);
                assert_eq!(
                    r.audit
                        .data_events
                        .iter()
                        .filter(|e| e.phase == "Seed")
                        .count(),
                    48
                );
                assert_eq!(
                    r.audit.diagnostic_events.len(),
                    4 * usize::from(path.budget()) + 4
                );
                assert!(r.source_binding.is_none());
                assert_eq!(r.classification, "ExplicitInventedPublicEntryFixture");
                assert!(r
                    .audit
                    .data_events
                    .iter()
                    .filter(|e| e.phase == "Functional")
                    .all(|e| e.address >= 0x108));
                assert!(r.steps.iter().all(
                    |step| ![0x620e, 0x623e, 0x62a1, 0x62d0].contains(&step.outcome.pc_before)
                ));
            }
        }
    }
}

#[test]
fn alternate_branches_stop_before_unadmitted_targets_without_algorithm_claim() {
    for (path, terminal) in [
        (EntryContinuityPath::JbrAlternate, 0x623e),
        (EntryContinuityPath::JneAlternate, 0x620e),
    ] {
        let mut s = session(path, true, true);
        for _ in 0..path.budget() {
            s.step().unwrap();
        }
        let r = s.report().unwrap();
        assert!(
            r.completed && r.boundary_only && !r.positive_completed && !r.actual_handoff_observed
        );
        assert_eq!(r.stop_before_pc, Some(terminal));
        assert_eq!(r.algorithm_retirements, 0);
        assert_eq!(r.steps.len(), usize::from(path.budget()));
        assert!(!r
            .steps
            .iter()
            .any(|step| step.outcome.pc_before == terminal));
        assert!(s.step().is_err());
    }
}

#[test]
fn predecessor_writes_remain_ordered_and_same_value_mov_is_not_dropped() {
    let mut s = session(EntryContinuityPath::D, false, false);
    for _ in 0..21 {
        s.step().unwrap();
    }
    let r = s.report().unwrap();
    let writes: Vec<_> = r
        .audit
        .data_events
        .iter()
        .filter(|e| e.phase == "Functional" && e.operation == "Write")
        .collect();
    assert_eq!(writes.len(), 7);
    assert_eq!(
        (writes[0].address, writes[0].width, writes[0].write_ordinal),
        (0x108, 8, Some(48))
    );
    assert_eq!(writes[0].same_value, Some(true));
    assert_eq!(
        (writes[1].address, writes[1].width, writes[1].write_ordinal),
        (0x10a, 16, Some(49))
    );
    assert_eq!(writes[1].value, Some(0xc0));
    assert_eq!(writes[2].write_ordinal, Some(50));
    let word_reads: Vec<_> = r
        .audit
        .data_events
        .iter()
        .filter(|e| e.phase == "Functional" && e.operation == "Read" && e.address == 0x19a)
        .collect();
    assert_eq!(word_reads.len(), 2);
    assert!(word_reads
        .iter()
        .all(|e| e.width == 16 && e.value == Some(0xc0)));
    assert!(!writes
        .iter()
        .any(|e| e.address == 0x19a || e.address == 0x19b));
}

#[test]
fn old_legacy_and_original_budget_policies_are_not_widened_by_new_feature() {
    let bytes = vec![0xa5; 208];
    let digest = crate::audit_sha256::digest(&bytes);
    let program = ClosedEntryContinuityProgram::explicit_invented_public_fixture();
    let c = cpu(&program, false, false);
    let psw = c.psw_u16();
    let denied = Session::new(
        ProgramSegment::new(0x6200, bytes, &digest).unwrap(),
        c,
        psw,
        Permissions::new(vec![], vec![]).unwrap(),
        17,
    );
    assert_eq!(denied.err().unwrap().code, "InvalidEntryState");
    let old = ClosedOriginalRomProgram::explicit_invented_public_fixture();
    let mut c = cpu(&program, false, false);
    c.pc = old.entry_pc();
    let psw = c.psw_u16();
    let (_, inventory) = old.closed_metadata();
    let data: BTreeMap<_, _> = inventory.into_iter().map(|address| (address, 0)).collect();
    let old_seeds =
        super::super::OriginalRomSeeds::new(&old, data, [[0; 4]; 8], [0; 8], [0; 4]).unwrap();
    assert_eq!(
        Session::new_closed_original_rom(&old, c, psw, old_seeds, CompositePath::D, 21)
            .err()
            .unwrap()
            .code,
        "OriginalEntryRejected"
    );
}

#[test]
fn exact_new_budgets_reject_host_supplied_widening_or_shortening() {
    let p = ClosedEntryContinuityProgram::explicit_invented_public_fixture();
    for budget in [0, 1, 6, 15, 16, 17, 18, 19, 20, 22, 255] {
        let c = cpu(&p, false, false);
        let psw = c.psw_u16();
        let result = EntryContinuitySession::new(
            &p,
            c,
            psw,
            seeds(&p, EntryContinuityPath::D),
            EntryContinuityPath::D,
            budget,
        );
        assert_eq!(result.err().unwrap().code, "EntryContinuityEntryRejected");
    }
}

#[test]
fn wrong_successor_latches_real_branch_fault_without_host_pc_repair() {
    let p = ClosedEntryContinuityProgram::explicit_invented_public_fixture();
    let c = cpu(&p, false, false);
    let psw = c.psw_u16();
    let mut s = EntryContinuitySession::new(
        &p,
        c,
        psw,
        seeds(&p, EntryContinuityPath::JbrAlternate),
        EntryContinuityPath::D,
        21,
    )
    .unwrap();
    assert_eq!(s.step().unwrap_err().code, "OriginalSuccessorRejected");
    let r = s.report().unwrap();
    assert!(!r.completed && !r.positive_completed);
    assert_eq!(r.current.cpu.pc, 0x623e);
    assert_eq!(r.current.cpu.instructions, 1);
    assert_eq!(r.audit.successful_retirements, 0);
    assert_eq!(
        r.audit.first_fault.unwrap().code,
        "OriginalSuccessorRejected"
    );
}

#[test]
fn missing_or_conflicting_seed_aliases_are_refused_before_initialization() {
    let p = ClosedEntryContinuityProgram::explicit_invented_public_fixture();
    let value = seeds(&p, EntryContinuityPath::D);
    let mut data = value.data.clone();
    data.insert(0x24, 0);
    assert_eq!(
        EntryContinuitySeeds::new(&p, data, value.pointing, [0xa5; 8], [0xa5a5; 4])
            .err()
            .unwrap()
            .code,
        "IncompleteEntryContinuitySeeds"
    );
    let value = seeds(&p, EntryContinuityPath::D);
    assert_eq!(
        EntryContinuitySeeds::new(&p, value.data, value.pointing, [0; 8], [0; 4])
            .err()
            .unwrap()
            .code,
        "ConflictingEntryContinuityAliases"
    );
}

#[test]
fn host_pc_register_and_dd_mutations_are_refused_without_another_retirement() {
    for field in 0..3 {
        let mut s = session(EntryContinuityPath::D, false, false);
        s.step().unwrap();
        match field {
            0 => s.inner.cpu.pc = 0x627a,
            1 => s.inner.cpu.a ^= 1,
            _ => s.inner.cpu.dd = !s.inner.cpu.dd,
        }
        assert_eq!(
            s.step().unwrap_err().code,
            "EntryContinuityLiveStateChanged"
        );
        assert_eq!(s.inner.cpu.instructions, 1);
    }
}

#[test]
fn substituted_second_cpu_bus_even_at_matching_logical_boundary_is_refused() {
    let mut first = session(EntryContinuityPath::D, false, false);
    let mut second = session(EntryContinuityPath::D, false, false);
    for _ in 0..6 {
        first.step().unwrap();
        second.step().unwrap();
    }
    assert_eq!(first.last_actual, second.last_actual);
    first.inner = second.inner;
    assert_eq!(
        first.step().unwrap_err().code,
        "EntryContinuityMachineSubstitutionRejected"
    );
    assert_eq!(first.inner.cpu.instructions, 6);
}

#[test]
fn reseeding_and_peripheral_capabilities_are_not_exposed_through_closed_mode() {
    let mut s = session(EntryContinuityPath::D, false, false);
    let before = s.inner.diagnostic_snapshot().unwrap();
    assert!(s.inner.seed_byte(0x130, 0).is_err());
    assert_eq!(s.inner.diagnostic_snapshot().unwrap(), before);
    let mut s = session(EntryContinuityPath::D, false, false);
    let events = s.inner.report().data_events.len();
    assert!(s.inner.data_read(0x24, 8).is_err());
    assert_eq!(s.inner.report().data_events.len(), events);
}

#[test]
fn opaque_native_admission_rejects_extent_and_digest_without_executing_bytes() {
    let binding = OriginalRomSourceBinding {
        base_commit: super::super::ORIGINAL_ROM_BASE_COMMIT.into(),
        contract_sha256: super::super::ORIGINAL_ROM_CONTRACT_SHA256.into(),
        whole_rom_sha256: "0".repeat(64),
        source_admission: "M2bsHostVerifiedOriginalRom".into(),
    };
    assert_eq!(
        ClosedEntryContinuityProgram::admit_host_verified_segment(
            0x54f5,
            vec![0xa5; 207],
            &"0".repeat(64),
            binding.clone()
        )
        .err()
        .unwrap()
        .code,
        "EntryContinuitySegmentRejected"
    );
    assert_eq!(
        ClosedEntryContinuityProgram::admit_host_verified_segment(
            0x54f5,
            vec![0xa5; 208],
            &"0".repeat(64),
            binding
        )
        .err()
        .unwrap()
        .code,
        "ProgramDigestMismatch"
    );
}
