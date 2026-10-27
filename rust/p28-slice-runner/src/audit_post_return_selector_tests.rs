//! Small invented route/admission controls, not private-ROM execution evidence.
use super::*;
fn program() -> ClosedPostReturnSelectorProgram {
    ClosedPostReturnSelectorProgram::explicit_invented_public_fixture()
}
fn cpu(p: &ClosedPostReturnSelectorProgram, ssp: u16, sf: bool) -> Cpu {
    Cpu {
        pc: p.entry_pc(),
        a: 0xbe31,
        ssp,
        lrb: 0x21,
        zf: true,
        cf: true,
        hc: true,
        dd: true,
        sf,
        psw_other: 0x137,
        cycles: 0,
        instructions: 0,
        halted: false,
    }
}
fn data(p: &ClosedPostReturnSelectorProgram, ssp: u16) -> BTreeMap<u16, u8> {
    let (_, inventory, _) = p.parent.parts(ssp);
    let mut data: BTreeMap<_, _> = inventory.into_iter().map(|a| (a, 0xa5)).collect();
    for (address, value) in [
        (0x19a, 0xbf),
        (0x19b, 0),
        (0x130, 5),
        (0x11b, 0x37),
        (0x12d, 0x80),
        (0x12e, 0x20),
        (0x192, 0x7f),
        (0x193, 0x83),
        (0x108, 0xff),
        (ssp, p.return_pc() as u8),
        (ssp + 1, (p.return_pc() >> 8) as u8),
    ] {
        data.insert(address, value);
    }
    data
}
fn snapshot(value: u8) -> SelectorSnapshot {
    SelectorSnapshot {
        value,
        classification: SELECTOR_SNAPSHOT_CLASSIFICATION.into(),
    }
}
fn p2() -> P2Snapshot {
    P2Snapshot {
        value: 0xa5,
        p2io: 0xff,
        p2sf: 7,
        provenance: "TechnicalArchitecturalP2LatchSnapshot_NoNativeWriterGeneration".into(),
    }
}
fn control() -> ControlSnapshot {
    ControlSnapshot {
        tcon0: 0x87,
        trnsit_implemented_flags: 11,
        provenance: "TechnicalArchitecturalControlSnapshot_NoNativeWriterGeneration".into(),
    }
}
fn seeds(p: &ClosedPostReturnSelectorProgram, ssp: u16, value: u8) -> PostReturnSelectorSeeds {
    let d = data(p, ssp);
    let r = std::array::from_fn(|n| d[&(0x108 + n as u16)]);
    let er = std::array::from_fn(|n| u16::from_le_bytes([r[2 * n], r[2 * n + 1]]));
    PostReturnSelectorSeeds::new(p, d, [[0x1234; 4]; 8], r, er, ssp, snapshot(value)).unwrap()
}
fn session_program(
    p: &ClosedPostReturnSelectorProgram,
    ssp: u16,
    value: u8,
    sf: bool,
) -> PostReturnSelectorSession {
    let c = cpu(p, ssp, sf);
    let psw = c.psw_u16();
    PostReturnSelectorSession::new(
        p,
        c,
        psw,
        seeds(p, ssp, value),
        PostP2ControlPath::A,
        49,
        p2(),
        control(),
    )
    .unwrap()
}
fn session(value: u8) -> PostReturnSelectorSession {
    session_program(&program(), 0x0702, value, true)
}
fn advance(s: &mut PostReturnSelectorSession, count: usize) {
    for _ in 0..count {
        s.step().unwrap();
    }
}

#[test]
fn exact_two_windows59_sites49_steps_and_eight_new_forms() {
    let p = program();
    let (nodes, inventory, pcs) = p.parts(0x0702);
    assert_eq!((nodes.len(), inventory.len(), pcs.len()), (59, 26, 49));
    assert_eq!(
        pcs[41..],
        [0x2003, 0x2005, 0x2006, 0x2008, 0x200b, 0x200c, 0x200d, 0x200f]
    );
    assert_eq!(
        post_nodes(0x2000, 0x0140, 0x0130)
            .iter()
            .map(|n| n.identity.len)
            .sum::<usize>(),
        14
    );
    assert_eq!(
        post_nodes(0x2000, 0x0140, 0x0130)
            .iter()
            .map(|n| n.identity.index)
            .collect::<Vec<_>>(),
        [747, 2293, 322, 2172, 668, 739, 322, 2301]
    );
    let w = p.program_windows();
    assert_eq!(
        (w[0].base, w[0].end_exclusive, w[0].byte_count),
        (0x2000, 0x2011, 17)
    );
    assert_eq!(
        (w[1].base, w[1].end_exclusive, w[1].byte_count),
        (0x6400, 0x6594, 404)
    );
    assert!(!pcs.contains(&0x2011) && !pcs.contains(&0x2014) && !pcs.contains(&0x2024));
}
#[test]
fn actual49_step_selector_cycle_preserves_frame_generations_and_neighboring_state() {
    for selector in 0u8..4 {
        for sf in [false, true] {
            let ssp = [0x0702, 0x0720, 0x07fc, 0x07fe][usize::from(selector)];
            let mut s = session_program(&program(), ssp, selector, sf);
            advance(&mut s, 49);
            let r = s.report().unwrap();
            let body = &r.prefix.body.prefix.p2;
            assert!(r.completed && r.prefix.completed && body.completed && body.positive_completed);
            assert_eq!(
                (
                    r.total_instruction_retirements,
                    r.post_return_instruction_retirements
                ),
                (49, 8)
            );
            assert_eq!(
                (
                    r.prefix.cal_instruction_retirements,
                    r.prefix.body_instruction_retirements,
                    r.prefix.rt_instruction_retirements,
                    r.prefix.post_return_instruction_retirements
                ),
                (1, 39, 1, 8)
            );
            assert_eq!(body.stop_before_pc, Some(0x2011));
            assert_eq!(
                (r.selector_initial, r.selector_final, r.local_r0_final),
                (selector, (selector + 1) & 3, selector + 1)
            );
            assert!(r.initial_selector_generation.is_none());
            let g = r.selector_generation.as_ref().unwrap();
            assert_eq!(
                (
                    g.machine_id,
                    g.event_index,
                    g.writer_pc,
                    g.retired_instruction,
                    g.generation_ordinal
                ),
                (1, 0, 0x200f, 49, 1)
            );
            assert_eq!(
                (
                    g.native_write_ordinal,
                    g.logical_write_ordinal,
                    g.raw_write_ordinal
                ),
                (18, 76, 113)
            );
            assert_eq!(
                g.source_generation,
                "CurrentExecutionNativeSelectorWriter064A"
            );
            assert_eq!(g.value, r.selector_final);
            let frame = r.prefix.stack_frame.as_ref().unwrap();
            let consumed = r.prefix.stack_return.as_ref().unwrap();
            assert_eq!(
                (frame.logical_write_ordinal, frame.raw_write_ordinals),
                (58, [90, 91])
            );
            assert_eq!(
                (frame.native_write_ordinal, consumed.retired_instruction),
                (0, 41)
            );
            assert_eq!(
                consumed.consumed_logical_write_ordinal,
                frame.logical_write_ordinal
            );
            assert_eq!(body.current.cpu.ssp, ssp);
            assert_eq!(
                (
                    r.prefix.body.p2_generations.len(),
                    r.prefix.body.control_generations.len()
                ),
                (2, 2)
            );
            assert_eq!(
                r.prefix
                    .body
                    .p2_generations
                    .iter()
                    .map(|g| g.native_write_ordinal)
                    .collect::<Vec<_>>(),
                [6, 13]
            );
            assert_eq!(
                r.prefix
                    .body
                    .control_generations
                    .iter()
                    .map(|g| g.native_write_ordinal)
                    .collect::<Vec<_>>(),
                [7, 9]
            );
            assert_eq!(r.history0128_before, Some(5));
            assert_eq!(r.history0128_after, Some(5 | (1 << (selector & 1))));
            assert_eq!(r.history0128_selected_bit, Some(selector & 1));
            assert_eq!(r.history0128_rmw.len(), 2);
            assert_eq!(r.history0128_rmw[1].same_value, Some(selector & 1 == 0));
            let h = r.history0128_generation.as_ref().unwrap();
            assert_eq!(
                (h.writer_pc, h.retired_instruction, h.native_write_ordinal),
                (0x2008, 45, 16)
            );
            let post = &body.steps[41..];
            assert_eq!(
                post.iter()
                    .map(|x| x.outcome.decoded.cycles)
                    .collect::<Vec<_>>(),
                [4, 2, 4, 9, 2, 2, 4, 4]
            );
            assert_eq!(post[0].after.cpu.zf, selector == 0);
            assert_eq!(post[2].after.cpu.zf, selector & 1 == 0);
            assert_eq!(post[3].after.cpu.zf, 5 & (1 << (selector & 1)) == 0);
            assert!(!post[4].after.cpu.zf && !post[4].after.cpu.hc);
            assert_eq!(post[6].after.cpu.zf, selector == 3);
            for step in post {
                assert_eq!(step.before.cpu.a & 0xff00, step.after.cpu.a & 0xff00);
                assert_eq!(step.before.cpu.cf, step.after.cpu.cf);
                assert_eq!(step.before.cpu.lrb, step.after.cpu.lrb);
                assert_eq!(step.before.cpu.ssp, step.after.cpu.ssp);
                assert_eq!(step.before.cpu.psw_other, step.after.cpu.psw_other);
                assert!(!step.after.cpu.dd);
            }
            assert!(r.selector_generation_available_for_future_reader);
            assert!(!r.native_next_event_handoff_verified && !r.branch064c_retired);
            assert!(body.audit.program_events.iter().all(|e| e.serviced
                && e.address != 0x2011
                && r.prefix
                    .program_windows
                    .iter()
                    .any(|w| e.address >= i64::from(w.base)
                        && e.address < i64::from(w.end_exclusive))));
            assert_eq!(body.audit.diagnostic_events.len(), 200);
        }
    }
}
#[test]
fn actual_rt_is_required_before_post_return_and_parent41_behavior_remains_unchanged() {
    let p = program();
    let c = cpu(&p, 0x0702, true);
    let psw = c.psw_u16();
    let d = data(&p, 0x0702);
    let r = std::array::from_fn(|n| d[&(0x108 + n as u16)]);
    let er = std::array::from_fn(|n| u16::from_le_bytes([r[n * 2], r[n * 2 + 1]]));
    let seeds = CalRtContinuitySeeds::new(&p.parent, d, [[0x1234; 4]; 8], r, er, 0x0702).unwrap();
    let mut old = CalRtContinuitySession::new(
        &p.parent,
        c,
        psw,
        seeds,
        PostP2ControlPath::A,
        41,
        p2(),
        control(),
    )
    .unwrap();
    for _ in 0..41 {
        old.step().unwrap();
    }
    let report = old.report().unwrap();
    assert!(report.completed);
    assert_eq!(
        (
            report.body.prefix.p2.audit.budget,
            report.body.prefix.p2.program_node_count
        ),
        (41, 51)
    );
    assert_eq!(report.body.prefix.p2.stop_before_pc, Some(0x2003));
    assert_eq!(report.post_return_instruction_retirements, 0);
    assert_eq!(report.stack_frame.unwrap().logical_write_ordinal, 57);
    assert_eq!(report.program_windows[0].byte_count, 3);
    let before = old
        .session()
        .bus
        .audit
        .as_ref()
        .unwrap()
        .report()
        .program_events
        .len();
    assert!(old.step().is_err());
    assert_eq!(
        old.session()
            .bus
            .audit
            .as_ref()
            .unwrap()
            .report()
            .program_events
            .len(),
        before
    );
}
#[test]
fn wrong_budget_entry_and_bank_cannot_create_a49_step_session() {
    for (pc, budget, lrb) in [
        (0x2003, 49, 0x21),
        (0x6400, 49, 0x21),
        (0x6593, 49, 0x21),
        (0x2000, 41, 0x21),
        (0x2000, 48, 0x21),
        (0x2000, 50, 0x21),
        (0x2000, 49, 0x20),
    ] {
        let p = program();
        let mut c = cpu(&p, 0x0702, true);
        c.pc = pc;
        c.lrb = lrb;
        let psw = c.psw_u16();
        assert_eq!(
            PostReturnSelectorSession::new(
                &p,
                c,
                psw,
                seeds(&p, 0x0702, 0),
                PostP2ControlPath::A,
                budget,
                p2(),
                control()
            )
            .err()
            .unwrap()
            .code,
            "PostReturnEntryRejected"
        );
    }
}
#[test]
fn initial_selector_outside_domain_or_fake_native_owner_is_refused_before_cal() {
    for mut snap in [
        snapshot(4),
        snapshot(255),
        SelectorSnapshot {
            value: 0,
            classification: "CurrentExecutionNativeSelectorWriter064A".into(),
        },
    ] {
        assert_eq!(
            snap.validate().unwrap_err().code,
            "PostReturnSelectorSnapshotRejected"
        );
        snap.value = 0;
    }
}
#[test]
fn selector_snapshot_requires_one_value_and_rejects_per_event_or_ready_result_fields() {
    for value in [
        serde_json::json!({}),
        serde_json::json!({"value":0}),
        serde_json::json!({"value":0,"classification":SELECTOR_SNAPSHOT_CLASSIFICATION,"expectedSelector":1}),
        serde_json::json!({"value":0,"classification":SELECTOR_SNAPSHOT_CLASSIFICATION,"incomingGeneration":1}),
    ] {
        assert!(serde_json::from_value::<SelectorSnapshot>(value).is_err());
    }
    assert!(serde_json::from_str::<SelectorSnapshot>(r#"{"value":0,"value":1,"classification":"RawSoftwareSnapshot0..3_OnceOnly_InitialGenerationNone"}"#).is_err());
}
#[test]
fn selector_cannot_be_supplied_twice_in_snapshot_and_data_map() {
    let p = program();
    let mut d = data(&p, 0x0702);
    d.insert(p.selector_address(), 1);
    let r = std::array::from_fn(|n| d[&(0x108 + n as u16)]);
    let er = std::array::from_fn(|n| u16::from_le_bytes([r[2 * n], r[2 * n + 1]]));
    assert!(
        PostReturnSelectorSeeds::new(&p, d, [[0x1234; 4]; 8], r, er, 0x0702, snapshot(0)).is_err()
    );
}
#[test]
fn repeated_initializer_and_post_cal_host_selector_seed_keep_actual_cal_evidence() {
    let mut s = session(0);
    s.step().unwrap();
    let before = s.session().bus.audit.as_ref().unwrap().report();
    assert_eq!(
        s.session().seed_byte(0x0140, 0).unwrap_err().code,
        "SeedOutsideSetup"
    );
    let r = s.report().unwrap();
    assert!(!r.completed && r.selector_generation.is_none());
    assert_eq!(r.prefix.frame_status, "CallerFrameEstablishedPendingReturn");
    assert_eq!(r.prefix.body.prefix.p2.steps.len(), 1);
    assert_eq!(
        r.prefix.body.prefix.p2.audit.data_events,
        before.data_events
    );
    assert_eq!(r.prefix.body.prefix.p2.current.cpu.ssp, 0x0700);
}
#[test]
fn post_rt_host_jump_and_excluded_branches_are_rejected_before_decode() {
    for destination in [0x2005, 0x2011, 0x2014, 0x2024] {
        let mut s = session(0);
        advance(&mut s, 41);
        let before = s
            .session()
            .bus
            .audit
            .as_ref()
            .unwrap()
            .report()
            .program_events
            .len();
        s.session().cpu.pc = destination;
        assert_eq!(s.step().unwrap_err().code, "P2LiveStateChanged");
        let audit = s.session().bus.audit.as_ref().unwrap().report();
        assert_eq!(audit.successful_retirements, 41);
        assert_eq!(audit.program_events.len(), before);
    }
}
#[test]
fn second_machine_after_rt_cannot_substitute_the_retained_cal_rt_machine() {
    let mut first = session(0);
    advance(&mut first, 41);
    let mut second = session(0);
    advance(&mut second, 41);
    // Both machines have equal state and values. Their retained pointer
    // witnesses still distinguish the actual privately owned Cpu/Bus pair.
    std::mem::swap(
        &mut first.parent.inner.inner.inner.inner,
        &mut second.parent.inner.inner.inner.inner,
    );
    assert_eq!(
        first.step().unwrap_err().code,
        "P2MachineSubstitutionRejected"
    );
}
#[test]
fn same_value_host_selector_write_after_rt_is_not_an_initial_snapshot_or_native064a_writer() {
    let mut s = session(0);
    advance(&mut s, 41);
    let machine = s.session();
    let audit = machine.bus.audit.take();
    crate::exec::write_data_u8(&mut machine.cpu, &mut machine.bus, 0x0140, 0);
    machine.bus.audit = audit;
    assert_eq!(
        s.step().unwrap_err().code,
        "PostReturnUnexpectedSelectorWriter"
    );
    assert_eq!(
        s.session()
            .bus
            .audit
            .as_ref()
            .unwrap()
            .report()
            .successful_retirements,
        41
    );
}
#[test]
fn missing_current_cal_frame_and_changed_stack_word_are_refused_before_return() {
    let mut s = session(0);
    s.step().unwrap();
    let machine = s.session();
    let audit = machine.bus.audit.take();
    crate::exec::write_data_u16(&mut machine.cpu, &mut machine.bus, 0x0702, 0x2003);
    machine.bus.audit = audit;
    assert_eq!(
        s.step().unwrap_err().code,
        "CalRtNativeFrameWriterGenerationChanged"
    );
    assert_eq!(
        s.session()
            .bus
            .audit
            .as_ref()
            .unwrap()
            .report()
            .successful_retirements,
        1
    );
}
#[test]
fn altered_invented_cal_opcode_refuses_before_exec_and_frame_write() {
    let mut p = program();
    p.caller.bytes[0] = 0x01;
    let mut s = session_program(&p, 0x0702, 0, true);
    assert_eq!(s.step().unwrap_err().code, "SelectedInstructionMismatch");
    let r = s.report().unwrap();
    assert!(!r.completed && r.prefix.stack_frame.is_none());
    assert_eq!(r.total_instruction_retirements, 0);
}
#[test]
fn altered_invented_rt_opcode_preserves_pending_current_frame() {
    let mut p = program();
    p.parent.segment.bytes[403] = 0x02;
    let mut s = session_program(&p, 0x0702, 0, true);
    advance(&mut s, 40);
    assert_eq!(s.step().unwrap_err().code, "SelectedInstructionMismatch");
    let r = s.report().unwrap();
    assert!(!r.completed && r.prefix.stack_return.is_none());
    assert_eq!(r.prefix.frame_status, "CallerFrameEstablishedPendingReturn");
    assert_eq!(r.total_instruction_retirements, 40);
}
#[test]
fn altered_invented_post_return_opcode_cannot_be_promoted_to_completed_selector() {
    let mut p = program();
    p.caller.bytes[3] = 0x00;
    let mut s = session_program(&p, 0x0702, 0, true);
    advance(&mut s, 41);
    assert_eq!(s.step().unwrap_err().code, "SelectedInstructionMismatch");
    let r = s.report().unwrap();
    assert!(!r.completed && r.selector_generation.is_none());
    assert_eq!(r.prefix.frame_status, "CallerFrameConsumedByActualRT");
    assert_eq!(
        (
            r.total_instruction_retirements,
            r.post_return_instruction_retirements
        ),
        (41, 0)
    );
    assert_eq!(r.prefix.body.prefix.p2.current.cpu.ssp, 0x0702);
}
#[test]
fn corrupted_source_windows_and_digests_are_refused_before_any_session() {
    let binding = OriginalRomSourceBinding {
        base_commit: crate::audit::ORIGINAL_ROM_BASE_COMMIT.into(),
        contract_sha256: crate::audit::ORIGINAL_ROM_CONTRACT_SHA256.into(),
        whole_rom_sha256: "f".repeat(64),
        source_admission: "M2bsHostVerifiedOriginalRom".into(),
    };
    let caller = vec![0xa5; 18];
    let body = vec![0xa5; 404];
    assert_eq!(
        ClosedPostReturnSelectorProgram::admit_host_verified_segments(
            0x063b,
            caller,
            "0",
            0x54f5,
            body,
            "0",
            binding.clone()
        )
        .err()
        .unwrap()
        .code,
        "PostReturnProgramWindowsRejected"
    );
    assert_eq!(
        ClosedPostReturnSelectorProgram::admit_host_verified_segments(
            0x063b,
            vec![0xa5; 17],
            &"0".repeat(64),
            0x54f5,
            vec![0xa5; 404],
            &"0".repeat(64),
            binding
        )
        .err()
        .unwrap()
        .code,
        "ProgramDigestMismatch"
    );
}
#[test]
fn selector_generation_cannot_claim_next_event_handoff_or_execute064c() {
    let mut s = session(3);
    advance(&mut s, 49);
    let r = s.report().unwrap();
    assert_eq!(r.selector_final, 0);
    assert!(!r.native_next_event_handoff_verified && !r.branch064c_retired);
    let before = s
        .session()
        .bus
        .audit
        .as_ref()
        .unwrap()
        .report()
        .program_events
        .len();
    assert!(s.step().is_err());
    let audit = s.session().bus.audit.as_ref().unwrap().report();
    assert_eq!(
        (audit.successful_retirements, audit.program_events.len()),
        (49, before)
    );
}
#[test]
fn generic_session_still_rejects49_and_parent_program_does_not_accept17_byte_window() {
    let p = program();
    let c = cpu(&p, 0x0702, true);
    let psw = c.psw_u16();
    let bytes = vec![0x01];
    let digest = crate::audit_sha256::digest(&bytes);
    assert!(Session::new(
        ProgramSegment::new(0x2000, bytes, &digest).unwrap(),
        c,
        psw,
        super::super::Permissions::new(vec![], vec![]).unwrap(),
        49
    )
    .is_err());
    let fake = OriginalRomSourceBinding {
        base_commit: crate::audit::ORIGINAL_ROM_BASE_COMMIT.into(),
        contract_sha256: crate::audit::ORIGINAL_ROM_CONTRACT_SHA256.into(),
        whole_rom_sha256: "f".repeat(64),
        source_admission: "M2bsHostVerifiedOriginalRom".into(),
    };
    assert_eq!(
        ClosedCalRtContinuityProgram::admit_host_verified_segments(
            0x063b,
            vec![0xa5; 17],
            "0",
            0x54f5,
            vec![0xa5; 404],
            "0",
            fake
        )
        .err()
        .unwrap()
        .code,
        "CalRtProgramWindowsRejected"
    );
}
