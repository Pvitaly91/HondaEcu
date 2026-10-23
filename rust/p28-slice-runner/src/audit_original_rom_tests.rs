//! Only the explicitly invented relocated fixture executes here. Native source
//! binding checks use opaque non-executed bytes, never a reconstructed OEM slice.
use super::*;

fn cpu(program: &ClosedOriginalRomProgram, dd: bool, sf: bool) -> Cpu {
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
fn seeds(program: &ClosedOriginalRomProgram, path: CompositePath) -> OriginalRomSeeds {
    let l = program.layout;
    let mut data: BTreeMap<_, _> = l
        .inventory()
        .into_iter()
        .map(|a| (a, (a as u8) ^ 0x59))
        .collect();
    let word = if path == CompositePath::A {
        191u16
    } else {
        192u16
    };
    data.insert(l.word, word as u8);
    data.insert(l.word + 1, (word >> 8) as u8);
    data.insert(l.flag7, if path == CompositePath::B { 0x80 } else { 0 });
    data.insert(l.flag5, if path == CompositePath::C { 0x20 } else { 0 });
    let r = std::array::from_fn(|n| data[&(0x108 + n as u16)]);
    let er = std::array::from_fn(|n| u16::from_le_bytes([r[2 * n], r[2 * n + 1]]));
    let banks =
        std::array::from_fn(|n| std::array::from_fn(|k| 0x2000 + n as u16 * 31 + k as u16 * 7));
    OriginalRomSeeds::new(program, data, banks, r, er).unwrap()
}
fn session(path: CompositePath, dd: bool, sf: bool) -> Session {
    let program = ClosedOriginalRomProgram::explicit_invented_public_fixture();
    let cpu = cpu(&program, dd, sf);
    let psw = cpu.psw_u16();
    let seeds = seeds(&program, path);
    let budget = program.path_pcs(path).len() as u8;
    Session::new_closed_original_rom(&program, cpu, psw, seeds, path, budget).unwrap()
}
fn binding() -> OriginalRomSourceBinding {
    OriginalRomSourceBinding {
        base_commit: ORIGINAL_ROM_BASE_COMMIT.into(),
        contract_sha256: ORIGINAL_ROM_CONTRACT_SHA256.into(),
        whole_rom_sha256: "0".repeat(64),
        source_admission: "M2bsHostVerifiedOriginalRom".into(),
    }
}

#[test]
fn invented_four_paths_retire_exactly_and_stop_before_with_both_dd_and_sf_values() {
    for (path, count, terminal) in [
        (CompositePath::A, 10, 0x6056),
        (CompositePath::B, 12, 0x6027),
        (CompositePath::C, 13, 0x6027),
        (CompositePath::D, 15, 0x6027),
    ] {
        for dd in [false, true] {
            for sf in [false, true] {
                let mut s = session(path, dd, sf);
                for _ in 0..count {
                    s.step_original_rom().unwrap();
                }
                let report = s.original_rom_report().unwrap();
                assert!(report.completed);
                assert_eq!(report.stop_before_pc, Some(terminal));
                assert_eq!(report.steps.len(), count);
                assert_eq!(report.audit.successful_retirements, count as u64);
                assert_eq!(report.audit.execution_calls, count as u64);
                assert_eq!(report.current.cpu.instructions, count as u64);
                assert_eq!(report.audit.external_exit, None);
                assert_eq!(report.current.cpu.sf, sf);
                assert!(report.source_binding.is_none());
                assert_eq!(report.classification, "ExplicitInventedPublicFixture");
                assert_eq!(report.entry.ram_range, [0x80, 0x1000]);
                assert_eq!(
                    report
                        .audit
                        .data_events
                        .iter()
                        .filter(|e| e.phase == "Seed")
                        .count(),
                    48
                );
                assert_eq!(
                    report
                        .audit
                        .raw_data_events
                        .iter()
                        .filter(|e| e.logical_ordinal < 48)
                        .count(),
                    80
                );
                assert!(report
                    .audit
                    .program_events
                    .iter()
                    .all(|e| e.serviced && e.address < 0x6056));
                assert!(report
                    .audit
                    .program_events
                    .iter()
                    .filter(|e| e.acquired_purpose == "ArchitecturalSelectedFetch")
                    .all(|e| e.pc != Some(terminal)));
                for step in &report.steps {
                    assert_eq!(step.full_psw_before & 0xcc8, 0xcc8);
                    assert_eq!(step.full_psw_after & 0xcc8, 0xcc8);
                    assert!(step.outcome.retired);
                    assert_eq!(step.outcome.external_exit, None);
                }
                let writes = report
                    .audit
                    .data_events
                    .iter()
                    .filter(|e| e.phase == "Functional" && e.operation == "Write")
                    .count();
                assert_eq!(
                    writes,
                    if path == CompositePath::A {
                        3
                    } else if path == CompositePath::D {
                        5
                    } else {
                        3
                    }
                );
                let program_events = report.audit.program_events.len();
                let data_events = report.audit.data_events.len();
                assert_eq!(s.step_original_rom().unwrap_err().code, "SessionSealed");
                assert_eq!(s.report().execution_calls, count as u64);
                assert_eq!(s.report().program_events.len(), program_events);
                assert_eq!(s.report().data_events.len(), data_events);
            }
        }
    }
}
#[test]
fn original_binding_and_extent_refusals_precede_execution() {
    let bytes = vec![0xa5; 86];
    let digest = crate::audit_sha256::digest(&bytes);
    let mut bad = binding();
    bad.base_commit = "f".repeat(40);
    assert_eq!(
        ClosedOriginalRomProgram::admit_host_verified_segment(0x556f, bytes.clone(), &digest, bad)
            .err()
            .unwrap()
            .code,
        "OriginalSourceBindingRejected"
    );
    let mut bad = binding();
    bad.contract_sha256 = "f".repeat(64);
    assert!(ClosedOriginalRomProgram::admit_host_verified_segment(
        0x556f,
        bytes.clone(),
        &digest,
        bad
    )
    .is_err());
    assert!(ClosedOriginalRomProgram::admit_host_verified_segment(
        0x556e,
        bytes.clone(),
        &digest,
        binding()
    )
    .is_err());
    assert!(ClosedOriginalRomProgram::admit_host_verified_segment(
        0x556f,
        bytes[..85].to_vec(),
        &digest,
        binding()
    )
    .is_err());
    assert!(ClosedOriginalRomProgram::admit_host_verified_segment(
        0x556f,
        bytes,
        &"f".repeat(64),
        binding()
    )
    .is_err());
}
#[test]
fn changed_invented_operand_is_decoded_but_not_executed() {
    let mut program = ClosedOriginalRomProgram::explicit_invented_public_fixture();
    program.segment.bytes[1] = 0x94;
    program.segment.digest = crate::audit_sha256::digest(&program.segment.bytes);
    let c = cpu(&program, false, false);
    let psw = c.psw_u16();
    let seed = seeds(&program, CompositePath::A);
    let mut s =
        Session::new_closed_original_rom(&program, c, psw, seed, CompositePath::A, 10).unwrap();
    assert!(s.step_original_rom().is_err());
    assert_eq!(s.report().execution_calls, 0);
    assert_eq!(s.report().successful_retirements, 0);
    assert_eq!(
        s.report()
            .data_events
            .iter()
            .filter(|e| e.phase == "Functional")
            .count(),
        0
    );
}
#[test]
fn declared_path_cannot_assign_or_repair_actual_successor() {
    let program = ClosedOriginalRomProgram::explicit_invented_public_fixture();
    let c = cpu(&program, false, false);
    let psw = c.psw_u16();
    let mut s = Session::new_closed_original_rom(
        &program,
        c,
        psw,
        seeds(&program, CompositePath::A),
        CompositePath::D,
        15,
    )
    .unwrap();
    for _ in 0..6 {
        s.step_original_rom().unwrap();
    }
    assert_eq!(
        s.step_original_rom().unwrap_err().code,
        "OriginalSuccessorRejected"
    );
    let report = s.original_rom_report().unwrap();
    assert!(!report.completed);
    assert_eq!(report.current.cpu.pc, 0x6050);
    assert_eq!(report.audit.execution_calls, 7);
    assert_eq!(report.audit.successful_retirements, 6);
}
#[test]
fn generic_step_host_data_and_program_probes_cannot_bypass_closed_mode() {
    let mut s = session(CompositePath::A, false, false);
    let identity = nodes(Layout::invented())[0].instruction(false);
    assert_eq!(s.step(&identity).unwrap_err().code, "WrongOriginalApi");
    assert_eq!(s.report().execution_calls, 0);
    let mut s = session(CompositePath::A, false, false);
    assert_eq!(
        s.data_read(0x192, 8).unwrap_err().code,
        "OriginalCapabilityDataDenied"
    );
    assert_eq!(s.report().data_admission_refusals.len(), 1);
    let mut s = session(CompositePath::A, false, false);
    assert_eq!(
        s.data_write(0x192, 8, 0).unwrap_err().code,
        "OriginalCapabilityDataDenied"
    );
    let mut s = session(CompositePath::A, false, false);
    assert_eq!(
        s.program_probe(0x6000).unwrap_err().code,
        "ProgramPurposeOrPhaseDenied"
    );
}
#[test]
fn no_seed_after_functional_or_second_mode_or_wrong_initial_context() {
    let mut s = session(CompositePath::A, false, false);
    assert_eq!(s.seed_byte(0x192, 7).unwrap_err().code, "SeedOutsideSetup");
    let program = ClosedOriginalRomProgram::explicit_invented_public_fixture();
    for wrong in [0x6001, 0x6027, 0x6056] {
        let mut c = cpu(&program, false, false);
        c.pc = wrong;
        let psw = c.psw_u16();
        assert!(Session::new_closed_original_rom(
            &program,
            c,
            psw,
            seeds(&program, CompositePath::A),
            CompositePath::A,
            10
        )
        .is_err());
    }
    let c = cpu(&program, false, false);
    let psw = c.psw_u16();
    assert!(Session::new_closed_original_rom(
        &program,
        c,
        psw ^ 0x400,
        seeds(&program, CompositePath::A),
        CompositePath::A,
        10
    )
    .is_err());
    let c = cpu(&program, false, false);
    let psw = c.psw_u16();
    // A representable but contradictory full word is rejected, without removing reads-one bits.
    assert!(Session::new_closed_original_rom(
        &program,
        c,
        psw ^ 0x8000,
        seeds(&program, CompositePath::A),
        CompositePath::A,
        10
    )
    .is_err());
    let c = cpu(&program, false, false);
    let psw = c.psw_u16();
    assert!(Session::new_closed_original_rom(
        &program,
        c,
        psw,
        seeds(&program, CompositePath::A),
        CompositePath::A,
        11
    )
    .is_err());
}
#[test]
fn closed_site_metadata_is_eighteen_and_data_rights_are_exact() {
    let mut s = session(CompositePath::D, false, false);
    // This is a guard unit probe, not a forged native execution observation.
    let node = s
        .bus
        .audit
        .as_ref()
        .unwrap()
        .original_node(0x6000, false)
        .unwrap();
    assert_eq!(
        node.reads,
        [Access {
            address: 0x192,
            width: 8
        }]
    );
    assert!(s
        .bus
        .audit
        .as_ref()
        .unwrap()
        .original_node(0x6001, false)
        .is_err());
    s.step_original_rom().unwrap();
    assert!(s
        .bus
        .audit
        .as_ref()
        .unwrap()
        .original_node(0x6002, true)
        .is_err());
    let ns = nodes(Layout::native());
    assert_eq!(ns.len(), 18);
    assert!(ns.iter().all(|n| n.pc != 0x5596 && n.pc != 0x55c5));
    assert!(ns.iter().all(|n| n
        .reads
        .iter()
        .chain(n.writes.iter().map(|w| &w.access))
        .all(|a| (0x100..0x200).contains(&a.address))));
}
#[test]
fn same_value_writes_remain_real_events_and_independent_sessions_do_not_share_state() {
    let program = ClosedOriginalRomProgram::explicit_invented_public_fixture();
    let mut seed = seeds(&program, CompositePath::A);
    seed.data.insert(program.layout.output, 15);
    seed.data.insert(program.layout.b, 15);
    let c = cpu(&program, false, false);
    let psw = c.psw_u16();
    let mut first =
        Session::new_closed_original_rom(&program, c, psw, seed, CompositePath::A, 10).unwrap();
    let mut second = session(CompositePath::D, true, true);
    for _ in 0..10 {
        first.step_original_rom().unwrap();
    }
    let r = first.original_rom_report().unwrap();
    let writes: Vec<_> = r
        .audit
        .data_events
        .iter()
        .filter(|e| e.phase == "Functional" && e.operation == "Write" && e.same_value == Some(true))
        .collect();
    assert!(writes.len() >= 2);
    assert!(writes.iter().all(|e| e.write_ordinal.is_some()));
    assert_eq!(
        second
            .original_rom_report()
            .unwrap()
            .current
            .cpu
            .instructions,
        0
    );
    second.step_original_rom().unwrap();
    assert_eq!(first.report().execution_calls, 10);
}

#[test]
fn per_instruction_permission_guard_refuses_sfr_wrong_width_and_unowned_writes() {
    let mut s = session(CompositePath::D, false, false);
    let fixture = ClosedOriginalRomProgram::explicit_invented_public_fixture();
    let state = OriginalState {
        nodes: fixture.nodes.clone(),
        pcs: fixture.path_pcs(CompositePath::D),
        inventory: fixture.layout.inventory(),
        terminal: fixture.terminal(CompositePath::D),
        path: CompositePath::D,
        entry: s.diagnostic_snapshot().unwrap(),
        classification: "ExplicitInventedPublicFixture".into(),
        source_binding: None,
        steps: vec![],
    };
    assert!(state
        .data_right(
            0x6000,
            747,
            Access {
                address: 0x192,
                width: 8
            },
            false
        )
        .is_ok());
    assert!(state
        .data_right(
            0x6000,
            747,
            Access {
                address: 0x19,
                width: 8
            },
            false
        )
        .is_err());
    assert!(state
        .data_right(
            0x6000,
            747,
            Access {
                address: 0x192,
                width: 16
            },
            false
        )
        .is_err());
    assert!(state
        .data_right(
            0x6000,
            747,
            Access {
                address: 0x192,
                width: 8
            },
            true
        )
        .is_err());
    assert!(state
        .data_right(
            0x6000,
            747,
            Access {
                address: 0x193,
                width: 8
            },
            false
        )
        .is_err());
    assert!(state
        .data_right(
            0x6000,
            738,
            Access {
                address: 0x192,
                width: 8
            },
            false
        )
        .is_err());
}
