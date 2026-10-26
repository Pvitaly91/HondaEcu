//! Bounded invented fixtures only. These are not private ROM/native witnesses.
use super::*;
fn program() -> ClosedCalRtContinuityProgram {
    ClosedCalRtContinuityProgram::explicit_invented_public_fixture()
}
fn cpu(p: &ClosedCalRtContinuityProgram, ssp: u16, sf: bool) -> Cpu {
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
fn data(p: &ClosedCalRtContinuityProgram, ssp: u16, canary: u16) -> BTreeMap<u16, u8> {
    let (_, inventory, _) = p.parts(ssp);
    let mut d: BTreeMap<_, _> = inventory.into_iter().map(|a| (a, 0xa5)).collect();
    for (a, v) in [
        (0x19a, 0xbf),
        (0x19b, 0),
        (0x130, 4),
        (0x11b, 0x37),
        (0x12d, 0x80),
        (0x12e, 0x20),
        (0x192, 0x7f),
        (0x193, 0x83),
        (0x108, 0xff),
        (ssp, canary as u8),
        (ssp + 1, (canary >> 8) as u8),
    ] {
        d.insert(a, v);
    }
    d
}
fn seeds(p: &ClosedCalRtContinuityProgram, ssp: u16, canary: u16) -> CalRtContinuitySeeds {
    let d = data(p, ssp, canary);
    let r = std::array::from_fn(|n| d[&(0x108 + n as u16)]);
    let er = std::array::from_fn(|n| u16::from_le_bytes([r[2 * n], r[2 * n + 1]]));
    CalRtContinuitySeeds::new(p, d, [[0x1234; 4]; 8], r, er, ssp).unwrap()
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
fn session(ssp: u16, canary: u16, sf: bool) -> CalRtContinuitySession {
    let p = program();
    session_program(&p, ssp, canary, sf)
}
fn session_program(
    p: &ClosedCalRtContinuityProgram,
    ssp: u16,
    canary: u16,
    sf: bool,
) -> CalRtContinuitySession {
    let c = cpu(p, ssp, sf);
    let psw = c.psw_u16();
    CalRtContinuitySession::new(
        p,
        c,
        psw,
        seeds(p, ssp, canary),
        PostP2ControlPath::A,
        41,
        p2(),
        control(),
    )
    .unwrap()
}
#[test]
fn altered_invented_cal_target_is_rejected_before_exec_or_frame_write() {
    let mut p = program();
    // Private unit mutation of the invented fixture only, never OEM input.
    p.caller.bytes[1] ^= 1;
    let mut s = session_program(&p, 0x0702, 0x2003, true);
    assert_eq!(s.step().unwrap_err().code, "SelectedInstructionMismatch");
    let r = s.report().unwrap();
    assert_eq!(r.body.prefix.p2.audit.successful_retirements, 0);
    assert!(r.stack_frame.is_none() && r.stack_journal.is_empty() && !r.completed);
}
#[test]
fn altered_invented_rt_and_rti_substitution_are_rejected_before_any_stack_pop() {
    for opcode in [0x00, 0x02] {
        let mut p = program();
        p.segment.bytes[403] = opcode;
        let mut s = session_program(&p, 0x0702, 0x2003, true);
        for _ in 0..40 {
            s.step().unwrap();
        }
        let before = s.session().diagnostic_snapshot().unwrap();
        assert_eq!(s.step().unwrap_err().code, "SelectedInstructionMismatch");
        let after = s.session().diagnostic_snapshot().unwrap();
        assert_eq!(before, after);
        let r = s.report().unwrap();
        assert_eq!(r.body.prefix.p2.audit.successful_retirements, 40);
        assert_eq!(r.frame_status, "CallerFrameEstablishedPendingReturn");
        assert_eq!(r.stack_journal.len(), 1);
        assert!(r.stack_frame.is_some() && r.stack_return.is_none() && !r.completed);
    }
}

#[test]
fn two_windows_have51_nodes_and41_ordered_instructions_without_padding() {
    let p = program();
    let (nodes, inventory, pcs) = p.parts(0x0702);
    assert_eq!((nodes.len(), inventory.len(), pcs.len()), (51, 25, 41));
    assert_eq!((pcs[0], pcs[1], pcs[40]), (0x2000, 0x6400, 0x6593));
    assert_eq!(p.return_pc(), 0x2003);
    assert!(!pcs.contains(&p.return_pc()));
    let windows = p.program_windows();
    assert_eq!(
        (
            windows[0].base,
            windows[0].end_exclusive,
            windows[0].byte_count
        ),
        (0x2000, 0x2003, 3)
    );
    assert_eq!(
        (
            windows[1].base,
            windows[1].end_exclusive,
            windows[1].byte_count
        ),
        (0x6400, 0x6594, 404)
    );
}
#[test]
fn actual_cal_body_rt_consumes_fresh_frame_for_all_four_reviewed_slots() {
    for ssp in [0x0702, 0x0720, 0x07fc, 0x07fe] {
        let mut s = session(ssp, 0xa55a, true);
        for _ in 0..41 {
            s.step().unwrap();
        }
        let r = s.report().unwrap();
        let body = &r.body.prefix.p2;
        assert!(r.completed && body.completed && body.positive_completed);
        assert_eq!(
            (
                r.cal_instruction_retirements,
                r.body_instruction_retirements,
                r.rt_instruction_retirements
            ),
            (1, 39, 1)
        );
        assert_eq!(r.post_return_instruction_retirements, 0);
        assert_eq!(body.audit.successful_retirements, 41);
        assert_eq!(body.stop_before_pc, Some(0x2003));
        assert_eq!(body.current.cpu.ssp, ssp);
        assert_eq!(
            (
                body.native_predecessor_retirements,
                body.algorithm_retirements,
                r.body.prefix.control_instruction_retirements,
                r.body.below_instruction_retirements
            ),
            (6, 10, 4, 18)
        );
        assert_eq!(
            (
                r.body.p2_generations.len(),
                r.body.control_generations.len()
            ),
            (2, 2)
        );
        assert_eq!(r.body.p2_generations[0].retired_instruction, 18);
        assert_eq!(r.body.p2_generations[1].retired_instruction, 39);
        assert_eq!(r.body.control_generations[1].retired_instruction, 25);
        let f = r.stack_frame.as_ref().unwrap();
        let ret = r.stack_return.as_ref().unwrap();
        assert_eq!(
            (
                f.native_write_ordinal,
                f.logical_write_ordinal,
                f.raw_write_ordinals
            ),
            (0, 57, [89, 90])
        );
        assert_eq!(
            (f.writer_pc, f.retired_instruction, f.return_pc),
            (0x2000, 1, 0x2003)
        );
        assert_eq!(
            (ret.consumer_pc, ret.retired_instruction, ret.return_pc),
            (0x6593, 41, 0x2003)
        );
        assert_eq!(ret.consumed_logical_write_ordinal, f.logical_write_ordinal);
        assert_eq!(r.stack_journal.len(), 2);
        assert_eq!(r.cpu_bus_instances, 1);
        assert!(body.audit.program_events.iter().all(|e| e.serviced
            && r.program_windows
                .iter()
                .any(|w| e.address >= i64::from(w.base)
                    && e.address < i64::from(w.end_exclusive)
                    && e.segment_offset == Some((e.address - i64::from(w.base)) as u32))));
        assert!(!body
            .audit
            .program_events
            .iter()
            .any(|e| e.address == 0x2003 || e.address == 0x6594));
        let cal = &body.steps[0];
        let rt = &body.steps[40];
        assert_eq!(
            (cal.outcome.decoded.cycles, rt.outcome.decoded.cycles),
            (9, 7)
        );
        assert_eq!(cal.full_psw_before, cal.full_psw_after);
        assert_eq!(rt.full_psw_before, rt.full_psw_after);
        assert_eq!(
            (rt.before.cpu.a, rt.before.cpu.lrb),
            (rt.after.cpu.a, rt.after.cpu.lrb)
        );
        assert!(!cal.after.cpu.sf && !rt.after.cpu.sf);
    }
}
#[test]
fn equal_preexisting_canary_is_not_a_frame_but_actual_same_value_cal_creates_one() {
    let mut s = session(0x0702, 0x2003, false);
    assert!(s.report().unwrap().stack_frame.is_none());
    s.step().unwrap();
    let r = s.report().unwrap();
    let f = r.stack_frame.unwrap();
    assert!(f.same_value);
    assert_eq!(f.source_generation, "CurrentExecutionCAL");
    assert_eq!(
        r.initial_canary_classification,
        "TechnicalPreexistingCanaryNotFrame"
    );
    assert_eq!(r.frame_status, "CallerFrameEstablishedPendingReturn");
    assert!(!r.completed && r.stack_return.is_none());
}
#[test]
fn denied_post_cal_reseed_preserves_real_frame_and_partial_actual_evidence() {
    let mut s = session(0x0720, 0x2003, true);
    s.step().unwrap();
    let before = s.session().bus.audit.as_ref().unwrap().report();
    assert_eq!(
        s.session().seed_byte(0x0720, 0).unwrap_err().code,
        "SeedOutsideSetup"
    );
    let r = s.report().unwrap();
    assert!(!r.completed);
    assert_eq!(r.frame_status, "CallerFrameEstablishedPendingReturn");
    assert_eq!(r.body.prefix.p2.steps.len(), 1);
    assert_eq!(r.body.prefix.p2.current.cpu.ssp, 0x071e);
    assert_eq!(r.body.prefix.p2.audit.data_events, before.data_events);
    assert_eq!(
        r.body.prefix.p2.audit.raw_data_events,
        before.raw_data_events
    );
    assert!(r.stack_return.is_none());
}
#[test]
fn forged_jump_to_rt_cannot_bypass39_body_retirements() {
    let mut s = session(0x0702, 0x2003, true);
    s.step().unwrap();
    s.session().cpu.pc = 0x6593;
    assert_eq!(s.step().unwrap_err().code, "P2LiveStateChanged");
    let audit = s.session().bus.audit.as_ref().unwrap().report();
    assert_eq!(audit.successful_retirements, 1);
    assert_eq!(
        audit
            .data_events
            .iter()
            .filter(|e| e.phase == "Functional" && e.serviced && e.operation == "Write")
            .count(),
        1
    );
}
#[test]
fn forged_ssp_change_is_rejected_without_host_repair() {
    let mut s = session(0x0702, 0x2003, true);
    s.step().unwrap();
    s.session().cpu.ssp = 0x0702;
    assert_eq!(
        s.step().unwrap_err().code,
        "CalRtStackPointerContinuityRejected"
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
fn forged_frame_byte_change_is_detected_before_the_next_instruction() {
    let mut s = session(0x0702, 0x2003, true);
    s.step().unwrap();
    // Deliberately bypass the audited API in this private unit fixture only:
    // the retained machine snapshot must still detect host corruption.
    let machine = s.session();
    let audit = machine.bus.audit.take();
    crate::exec::write_data_u8(&mut machine.cpu, &mut machine.bus, 0x0702, 0);
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
fn same_value_host_overwrite_is_a_new_generation_and_cannot_hide_behind_equal_bytes() {
    let mut s = session(0x0702, 0x2003, true);
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
fn missing_or_stale_frame_metadata_cannot_replace_the_actual_current_writer() {
    let mut missing = session(0x0702, 0x2003, true);
    missing.step().unwrap();
    missing.frame = None;
    assert_eq!(missing.step().unwrap_err().code, "CalRtFreshFrameRequired");
    let mut stale = session(0x0702, 0x2003, true);
    stale.step().unwrap();
    stale.frame.as_mut().unwrap().logical_write_ordinal -= 1;
    assert_eq!(
        stale.step().unwrap_err().code,
        "CalRtFrameWriterGenerationChanged"
    );
}
#[test]
fn a_second_cpu_bus_cannot_be_substituted_for_the_retained_machine() {
    let mut first = session(0x0702, 0x2003, true);
    first.step().unwrap();
    let mut second = session(0x0702, 0x2003, true);
    std::mem::swap(
        &mut first.inner.inner.inner.inner,
        &mut second.inner.inner.inner.inner,
    );
    assert_eq!(
        first.step().unwrap_err().code,
        "P2MachineSubstitutionRejected"
    );
}
#[test]
fn stack_slots_reject_odd_wrap_underflow_overflow_and_nonreviewed_addresses() {
    let p = program();
    for ssp in [0, 1, 2, 0x0700, 0x0703, 0x0800, 0xfffe, 0xffff] {
        assert_eq!(
            CalRtContinuitySeeds::new(&p, BTreeMap::new(), [[0; 4]; 8], [0; 8], [0; 4], ssp)
                .err()
                .unwrap()
                .code,
            "CalRtStackSlotRejected"
        );
    }
}
#[test]
fn wrong_entry_budget_and_path_do_not_create_a_caller_frame() {
    for (entry, budget, path) in [
        (0x6400, 41, PostP2ControlPath::A),
        (0x6593, 41, PostP2ControlPath::A),
        (0x2000, 40, PostP2ControlPath::A),
        (0x2000, 42, PostP2ControlPath::A),
        (0x2000, 41, PostP2ControlPath::B),
    ] {
        let p = program();
        let mut c = cpu(&p, 0x0702, true);
        c.pc = entry;
        let psw = c.psw_u16();
        assert_eq!(
            CalRtContinuitySession::new(
                &p,
                c,
                psw,
                seeds(&p, 0x0702, 0xa5a5),
                path,
                budget,
                p2(),
                control()
            )
            .err()
            .unwrap()
            .code,
            "CalRtEntryRejected"
        );
    }
}
#[test]
fn missing_frame_canary_or_alias_conflict_is_refused_before_execution() {
    let p = program();
    let mut d = data(&p, 0x0702, 0x2003);
    d.remove(&0x0703);
    assert_eq!(
        CalRtContinuitySeeds::new(&p, d, [[0; 4]; 8], [0; 8], [0; 4], 0x0702)
            .err()
            .unwrap()
            .code,
        "CalRtSeedInventoryRejected"
    );
    let d = data(&p, 0x0702, 0x2003);
    let mut r = std::array::from_fn(|n| d[&(0x108 + n as u16)]);
    let er = std::array::from_fn(|n| u16::from_le_bytes([r[2 * n], r[2 * n + 1]]));
    r[0] ^= 1;
    assert_eq!(
        CalRtContinuitySeeds::new(&p, d, [[0; 4]; 8], r, er, 0x0702)
            .err()
            .unwrap()
            .code,
        "ConflictingEntryContinuityAliases"
    );
}
#[test]
fn extra_step_after_actual_rt_is_refused_before_any_return_pc_decode() {
    let mut s = session(0x0702, 0x2003, true);
    for _ in 0..41 {
        s.step().unwrap();
    }
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
    assert_eq!(audit.program_events.len(), before);
    assert_eq!(audit.successful_retirements, 41);
}
#[test]
fn generic_legacy_constructor_still_refuses_budget41() {
    let bytes = vec![0x01];
    let digest = crate::audit_sha256::digest(&bytes);
    let segment = ProgramSegment::new(0x2000, bytes, &digest).unwrap();
    let p = program();
    let c = cpu(&p, 0x0702, false);
    let psw = c.psw_u16();
    assert!(Session::new(
        segment,
        c,
        psw,
        Permissions::new(vec![], vec![]).unwrap(),
        41
    )
    .is_err());
}
#[test]
fn legacy_rejected_program_probe_keeps_active_segment_diagnostics() {
    let bytes = vec![0x01];
    let digest = crate::audit_sha256::digest(&bytes);
    let segment = ProgramSegment::new(0x2000, bytes, &digest).unwrap();
    let c = cpu(&program(), 0x0702, false);
    let psw = c.psw_u16();
    let mut s = Session::new(
        segment,
        c,
        psw,
        Permissions::new(vec![], vec![]).unwrap(),
        1,
    )
    .unwrap();
    assert_eq!(
        s.program_probe(0x2003).unwrap_err().code,
        "ProgramOutsideSegment"
    );
    let r = s.bus.audit.as_ref().unwrap().report();
    assert_eq!((r.program_base, r.program_end_exclusive), (0x2000, 0x2001));
    assert_eq!(r.program_sha256, digest);
    assert_eq!(r.program_events.len(), 1);
    assert_eq!(r.program_events[0].address, 0x2003);
    assert_eq!(r.program_events[0].segment_offset, None);
    assert!(!r.program_events[0].serviced);
    assert_eq!(
        r.program_events[0].refusal.as_ref().unwrap().code,
        "ProgramOutsideSegment"
    );
}
#[test]
fn rt_production_semantics_clear_true_host_sf_without_rti_restore() {
    // Separate invented one-instruction unit probe, never a main-route reseed.
    let mut c = cpu(&program(), 0x0700, true);
    c.pc = 0x3000;
    let before_psw = c.psw_u16();
    let mut bus = crate::bus::Bus::new(vec![0xa5; 32768], 0xa5);
    crate::exec::write_data_u16(&mut c, &mut bus, 0x0702, 0x3456);
    let decoded = crate::decoder::decode_checked(c.dd, |offset| {
        if offset == 0 {
            Ok::<u8, AuditError>(0x01)
        } else {
            Err(AuditError::new("UnexpectedProbe", None, "RT length1"))
        }
    })
    .unwrap()
    .unwrap();
    crate::exec::execute_decoded(&mut c, &mut bus, 0x3000, decoded).unwrap();
    assert_eq!(
        (c.pc, c.ssp, c.a, c.lrb, c.psw_u16()),
        (0x3456, 0x0702, 0xbe31, 0x21, before_psw)
    );
    assert!(!c.sf);
}
