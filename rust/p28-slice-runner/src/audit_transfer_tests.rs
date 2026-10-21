//! Private guard/component fixtures only. These tests never construct Cpu/Bus,
//! call the decoder/shared effects, or claim an actual execution observation.
//! Explicit private counters below are premises for exercising real guards.
use super::*;
use crate::audit::composite::{ClosedCompositeProgram, CompositePath, CompositeSeeds};
use crate::audit::transfer::{TransferJournalStages, TransferSegmentClaim, TransferSegmentId};
use crate::audit::{CompositeForm, CompositeOperand, CpuState, DecodedState};
use std::collections::BTreeMap;

fn snap(pc: u16, instructions: u64, cycles: u64) -> Snapshot {
    Snapshot {
        cpu: CpuState {
            pc,
            a: 0x5aa5,
            ssp: 0x4567,
            lrb: 0x21,
            zf: false,
            cf: false,
            hc: true,
            dd: false,
            sf: true,
            psw_other: 0x137,
            cycles,
            instructions,
            halted: false,
        },
        ram: vec![0xa5; 3968],
        ram_range: [0x80, 0x1000],
    }
}
fn segment(
    id: TransferSegmentId,
    base: u32,
    bytes: Vec<u8>,
) -> (TransferSegmentClaim, ProgramSegment) {
    let digest = crate::audit_sha256::digest(&bytes);
    (
        TransferSegmentClaim {
            id,
            base,
            end_exclusive: base + bytes.len() as u32,
            sha256: digest.clone(),
            provenance: "InventedOnly_NoNativeGenerationOwner".into(),
        },
        ProgramSegment::new(base, bytes, &digest).unwrap(),
    )
}
fn guard(path: CompositePath, budget: u8) -> AuditBus {
    let mut data: BTreeMap<_, _> = INVENTORY.into_iter().map(|address| (address, 0)).collect();
    data.insert(0x196, if path == CompositePath::A { 0 } else { 0xc0 });
    data.insert(0x12a, if path == CompositePath::B { 0x80 } else { 0 });
    data.insert(0x124, if path == CompositePath::C { 0x20 } else { 0 });
    let seeds = CompositeSeeds::new(data, [[0; 4]; 8], [0; 8], [0; 4]).unwrap();
    let caller = segment(TransferSegmentId::Caller, 0x0ff0, vec![3, 0, 16]);
    let bus = AuditBus::new(
        ProgramSegment::new(0x0ff0, vec![3, 0, 16], &caller.0.sha256).unwrap(),
        Permissions::new(vec![], vec![]).unwrap(),
        0x0ff0,
        budget,
    );
    let mut state = bus.state.borrow_mut();
    state.phase = "Functional";
    state.transfer = Some(TransferState {
        owner: Arc::new(()),
        segments: vec![
            caller,
            segment(TransferSegmentId::Composite, 0x1000, vec![0xa5; 51]),
            segment(TransferSegmentId::BelowContinuation, 0x55c5, vec![0x77, 0]),
            segment(
                TransferSegmentId::NotBelowContinuation,
                0x5596,
                vec![0x77, 0xa5],
            ),
        ],
        active: TransferSegmentId::Caller,
        stage: TransferStage::Caller,
        closed: ClosedState {
            nodes: ClosedCompositeProgram::node_inventory(),
            path,
            entry: snap(0x0ff0, 0, 0),
            steps: vec![],
            direct_j_count: 0,
        },
        composite_permissions: seeds.permissions().unwrap(),
        empty_permissions: Permissions::new(vec![], vec![]).unwrap(),
        entry: snap(0x0ff0, 0, 0),
        steps: vec![],
        pending: None,
        tickets: vec![],
        commits: vec![],
        issued: 0,
        consumed: 0,
        refusals: vec![],
        checkpoint: None,
        stages: TransferJournalStages {
            program: vec![],
            logical: vec![],
            raw: vec![],
            diagnostic: vec![],
        },
    });
    drop(state);
    bus
}
fn retirement_fixture(bus: &AuditBus, pc: u16, index: usize, len: usize, retired: u64) {
    let mut state = bus.state.borrow_mut();
    state.phase = "Executing";
    state.pc = Some(pc);
    state.instruction = Some(index);
    state.selected_len = Some(len);
    state.selected_reads = len;
    state.retirements = retired;
    state.execution_calls = retired + 1;
    state.step_calls = retired + 1;
}
fn caller_pending(bus: &AuditBus) -> Snapshot {
    let node = bus.transfer_node(0x0ff0, false).unwrap();
    retirement_fixture(bus, 0x0ff0, 684, 3, 0);
    bus.retire(0x1000, Some(0x1000)).unwrap();
    bus.set_current_pc(0x1000);
    let after = snap(0x1000, 1, 7);
    let outcome = StepOutcome {
        pc_before: 0x0ff0,
        pc_after: 0x1000,
        decoded_index: 684,
        mnemonic: "J addr16".into(),
        len: 3,
        decoded: DecodedState {
            index: 684,
            mnemonic: "J addr16".into(),
            len: 3,
            dd_before: false,
            dd_after: false,
            dd_after_option: None,
            cycles: 7,
            n8: 0,
            n8_alt: 0,
            n16: 0,
            n16_alt: 0,
            s8: 0,
            rel8: 0,
            addr16: 0x1000,
        },
        selected_extent: [0x0ff0, 0x0ff3],
        selected_extent_sha256: crate::audit_sha256::digest(&[3, 0, 16]),
        retired: true,
        external_exit: Some(0x1000),
    };
    bus.record_transfer_step(node, snap(0x0ff0, 0, 0), after.clone(), outcome)
        .unwrap();
    after
}
fn committed(bus: &AuditBus) -> TransferTicket {
    let after = caller_pending(bus);
    let ticket = bus.take_transfer_ticket().unwrap();
    bus.diagnostic_ram();
    bus.commit_transfer(&ticket, &ticket.claim(), after)
        .unwrap();
    ticket
}

#[test]
fn transfer_component_closed_stage_nodes_and_prefix_offsets() {
    for path in [
        CompositePath::A,
        CompositePath::B,
        CompositePath::C,
        CompositePath::D,
    ] {
        let bus = guard(path, 18);
        let caller = bus.transfer_node(0x0ff0, true).unwrap();
        assert_eq!(caller.form, CompositeForm::JAddress);
        assert_eq!(caller.operands, vec![CompositeOperand::Target(0x1000)]);
        assert_eq!(caller.instruction(true).index, 684);
        committed(&bus);
        let t = bus.state.borrow();
        let t = t.transfer.as_ref().unwrap();
        for (index, pc) in path.pcs().iter().enumerate() {
            assert_eq!(t.node(*pc, false, index as u64 + 1).unwrap().pc, *pc);
        }
        assert_eq!(
            t.node(0x1000, false, 0).unwrap_err().code,
            "TransferCounterMismatch"
        );
        assert_eq!(t.node(0x1003, true, 3).unwrap_err().code, "WrongIncomingDd");
    }
}
#[test]
fn transfer_component_caller_authority_requires_actual_direct_j_target() {
    for (pc, external) in [(0x1001, Some(0x1001)), (0x1000, None)] {
        let bus = guard(CompositePath::A, 18);
        retirement_fixture(&bus, 0x0ff0, 684, 3, 0);
        assert_eq!(
            bus.retire(pc, external).unwrap_err().code,
            "UnknownTransferSuccessor"
        );
        assert_eq!(bus.report().successful_retirements, 0);
        assert!(!bus.report().sealed);
    }
    let bus = guard(CompositePath::A, 18);
    retirement_fixture(&bus, 0x0ff0, 738, 3, 0);
    assert_eq!(
        bus.retire(0x1000, Some(0x1000)).unwrap_err().code,
        "TransferRetirementFormMismatch"
    );
    assert_eq!(bus.report().successful_retirements, 0);
    let bus = guard(CompositePath::A, 18);
    {
        let mut s = bus.state.borrow_mut();
        let t = s.transfer.as_mut().unwrap();
        t.stage = TransferStage::Composite;
        t.active = TransferSegmentId::Composite;
        t.closed.direct_j_count = 1;
    }
    retirement_fixture(&bus, 0x1030, 684, 3, 11);
    assert_eq!(
        bus.retire(0x55c5, Some(0x55c5)).unwrap_err().code,
        "InvalidCompositeTerminalJ"
    );
}
#[test]
fn transfer_component_pending_denies_execution_program_seed_and_data() {
    let bus = guard(CompositePath::A, 18);
    caller_pending(&bus);
    assert_eq!(bus.begin_step(0x1000).unwrap_err().code, "TransferPending");
    assert_eq!(bus.report().shared_execution_calls, 1);
    let bus = guard(CompositePath::A, 18);
    caller_pending(&bus);
    assert_eq!(
        bus.program_read(0x1000, "DecoderProbe").unwrap_err().code,
        "TransferPending"
    );
    assert!(!bus.report().program_events.last().unwrap().serviced);
    let bus = guard(CompositePath::A, 18);
    caller_pending(&bus);
    assert_eq!(
        bus.admit_seed(0x196, 8).unwrap_err().code,
        "TransferPending"
    );
    let bus = guard(CompositePath::A, 18);
    caller_pending(&bus);
    assert_eq!(
        bus.begin_capability(0x196, 16, false, None)
            .unwrap_err()
            .code,
        "TransferPending"
    );
    assert_eq!(bus.report().data_admission_refusals.len(), 1);
}
#[test]
fn transfer_component_claim_mutations_cannot_select_mapping() {
    for change in 0..4 {
        let bus = guard(CompositePath::A, 18);
        let after = caller_pending(&bus);
        let ticket = bus.take_transfer_ticket().unwrap();
        let mut claim = ticket.claim();
        match change {
            0 => claim.actual_target_pc = 0x1001,
            1 => claim.destination.base = 0x1001,
            2 => claim.architecture_sha256 = "0".repeat(64),
            _ => claim.counters.cpu_cycles += 1,
        }
        assert_eq!(
            bus.commit_transfer(&ticket, &claim, after)
                .unwrap_err()
                .code,
            "TransferClaimMismatch"
        );
        assert_eq!(
            bus.state.borrow().transfer.as_ref().unwrap().active,
            TransferSegmentId::Caller
        );
    }
}
#[test]
fn transfer_component_live_cpu_ram_and_journal_tampering_refused() {
    for change in 0..3 {
        let bus = guard(CompositePath::A, 18);
        let mut after = caller_pending(&bus);
        let ticket = bus.take_transfer_ticket().unwrap();
        match change {
            0 => after.cpu.a ^= 1,
            1 => after.ram[0] ^= 1,
            _ => bus.state.borrow_mut().raw_write_ordinal += 1,
        }
        assert_eq!(
            bus.commit_transfer(&ticket, &ticket.claim(), after)
                .unwrap_err()
                .code,
            "TransferLiveStateMismatch"
        );
        assert_eq!(bus.state.borrow().transfer.as_ref().unwrap().consumed, 0);
    }
}
#[test]
fn transfer_component_opaque_owner_prevents_cross_session_ticket() {
    let a = guard(CompositePath::A, 18);
    caller_pending(&a);
    let ticket = a.take_transfer_ticket().unwrap();
    let b = guard(CompositePath::A, 18);
    let after = caller_pending(&b);
    assert_eq!(
        b.commit_transfer(&ticket, &ticket.claim(), after)
            .unwrap_err()
            .code,
        "CrossSessionTransferTicket"
    );
    assert_eq!(b.state.borrow().transfer.as_ref().unwrap().consumed, 0);
}
#[test]
fn transfer_component_single_use_and_duplicate_handle_requests_refused() {
    let bus = guard(CompositePath::A, 18);
    let ticket = committed(&bus);
    assert_eq!(
        bus.commit_transfer(&ticket, &ticket.claim(), snap(0x1000, 1, 7))
            .unwrap_err()
            .code,
        "TransferTicketAlreadyConsumed"
    );
    let bus = guard(CompositePath::A, 18);
    caller_pending(&bus);
    bus.take_transfer_ticket().unwrap();
    assert_eq!(
        bus.take_transfer_ticket().err().unwrap().code,
        "TransferTicketAlreadyIssued"
    );
    assert_eq!(bus.state.borrow().transfer.as_ref().unwrap().issued, 1);
}
#[test]
fn transfer_component_pending_handle_claim_is_not_an_execution_permission() {
    let bus = guard(CompositePath::A, 18);
    caller_pending(&bus);
    let ticket = bus.take_transfer_ticket().unwrap();
    let claim = ticket.claim();
    assert_eq!(claim.source_instruction_pc, 0x0ff0);
    assert_eq!(claim.actual_target_pc, 0x1000);
    assert_eq!(
        bus.transfer_node(0x1000, false).unwrap_err().code,
        "TransferPending"
    );
    assert_eq!(bus.report().successful_retirements, 1);
    assert!(!bus.report().sealed);
}
#[test]
fn transfer_component_program_callback_bounds_and_selected_fetch_guard() {
    let bus = guard(CompositePath::A, 18);
    bus.begin_step(0x0ff0).unwrap();
    assert_eq!(
        bus.program_read(0x0ff3, "DecoderProbe").unwrap_err().code,
        "ProgramOutsideSegment"
    );
    let report = bus.report();
    assert!(!report.program_events[0].serviced);
    assert_eq!(report.shared_execution_calls, 0);
    let bus = guard(CompositePath::A, 18);
    retirement_fixture(&bus, 0x0ff0, 684, 3, 0);
    bus.state.borrow_mut().selected_reads = 2;
    assert_eq!(
        bus.retire(0x1000, Some(0x1000)).unwrap_err().code,
        "InvalidRetirement"
    );
}
#[test]
fn transfer_component_prior_stage_program_associations_are_immutable() {
    let bus = guard(CompositePath::A, 18);
    bus.begin_step(0x0ff0).unwrap();
    bus.program_read(0x0ff0, "DecoderProbe").unwrap();
    bus.associate_selection(3).unwrap();
    let prior = bus.report().program_events;
    {
        let mut s = bus.state.borrow_mut();
        s.phase = "Functional";
        s.transfer.as_mut().unwrap().active = TransferSegmentId::Composite;
        s.transfer.as_mut().unwrap().stage = TransferStage::Composite;
    }
    bus.begin_step(0x1000).unwrap();
    bus.program_read(0x1000, "DecoderProbe").unwrap();
    bus.associate_selection(2).unwrap();
    assert_eq!(
        &bus.report().program_events[..prior.len()],
        prior.as_slice()
    );
}
#[test]
fn transfer_component_stale_rmw_read_cannot_authorize_next_instruction() {
    let bus = guard(CompositePath::D, 18);
    committed(&bus);
    {
        let mut s = bus.state.borrow_mut();
        s.phase = "Executing";
        s.pc = Some(0x1003);
        s.instruction = Some(1862);
        s.data_start = 1;
        s.data.push(DataEvent {
            ordinal: 0,
            phase: "Functional".into(),
            pc: Some(0x1003),
            instruction_index: Some(1862),
            address: 0x18e,
            width: 8,
            operation: "Read".into(),
            requested_value: None,
            value: Some(1),
            old_value: None,
            write_ordinal: None,
            same_value: None,
            serviced: true,
            refusal: None,
        });
    }
    assert_eq!(
        bus.begin_data(0x18e, 8, true, Some(2), Some(1))
            .err()
            .unwrap()
            .code,
        "RmwReadMissing"
    );
}
#[test]
fn transfer_component_global_budget_and_counters_survive_commit() {
    let bus = guard(CompositePath::A, 1);
    committed(&bus);
    let before = bus.report();
    assert_eq!(before.successful_retirements, 1);
    assert_eq!(before.shared_execution_calls, 1);
    assert_eq!(
        bus.begin_step(0x1000).unwrap_err().code,
        "InstructionBudgetExceeded"
    );
    let after = bus.report();
    assert_eq!(after.step_calls, 2);
    assert_eq!(after.successful_retirements, 1);
    assert_eq!(after.shared_execution_calls, 1);
}
#[test]
fn transfer_component_continuation_checkpoint_seals_without_extra_fetch() {
    let bus = guard(CompositePath::A, 18);
    {
        let mut s = bus.state.borrow_mut();
        let t = s.transfer.as_mut().unwrap();
        t.stage = TransferStage::Continuation;
        t.active = TransferSegmentId::BelowContinuation;
    }
    retirement_fixture(&bus, 0x55c5, 738, 2, 12);
    bus.retire(0x55c7, None).unwrap();
    let report = bus.report();
    assert!(report.sealed);
    assert_eq!(
        report.terminal_reason.as_deref(),
        Some("InventedContinuationCheckpoint")
    );
    assert_eq!(
        bus.program_read(0x55c7, "DecoderProbe").unwrap_err().code,
        "SessionSealed"
    );
    assert!(!bus.report().program_events.last().unwrap().serviced);
}
