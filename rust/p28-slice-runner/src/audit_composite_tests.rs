//! Source-frozen guard/component fixtures, never Cpu/execute/decoder/composite runs.
//! The opaque 0xa5 segment is NOT the M2bj program and is never executed. Private
//! state fixtures exercise real guard methods; they are not runtime observations.
use super::*;
use crate::audit::composite::{
    ClosedCompositeProgram, CompositeEmissionMetadata, CompositeForm, CompositePath, CompositeSeeds,
};
use crate::audit::{CpuState, WriteAccess};
use crate::audit_sha256::digest;
use std::collections::{BTreeMap, BTreeSet};

fn snapshot() -> Snapshot {
    Snapshot {
        cpu: CpuState {
            pc: 0x1000,
            a: 0x5aa5,
            ssp: 0x4567,
            lrb: 0x21,
            zf: false,
            cf: false,
            hc: true,
            dd: false,
            sf: true,
            psw_other: 0x137,
            cycles: 0,
            instructions: 0,
            halted: false,
        },
        ram: vec![0xa5; 3968],
        ram_range: [0x80, 0x1000],
    }
}
fn closed(path: CompositePath) -> ClosedState {
    ClosedState {
        nodes: ClosedCompositeProgram::node_inventory(),
        path,
        entry: snapshot(),
        steps: vec![],
        direct_j_count: 0,
    }
}
fn guard(path: CompositePath, budget: u8) -> AuditBus {
    let bytes = vec![0xa5; 51];
    // Deliberately broad aggregate rights prove the per-instruction closed guard
    // independently refuses wrong address, width, direction, and missing RMW.
    let mut reads: Vec<_> = INVENTORY
        .iter()
        .map(|a| Access {
            address: *a,
            width: 8,
        })
        .collect();
    reads.push(Access {
        address: 0x196,
        width: 16,
    });
    let writes = INVENTORY
        .iter()
        .map(|a| WriteAccess {
            access: Access {
                address: *a,
                width: 8,
            },
            rmw_required: false,
        })
        .collect();
    let bus = AuditBus::new(
        ProgramSegment::new(0x1000, bytes.clone(), &digest(&bytes)).unwrap(),
        Permissions::new(reads, writes).unwrap(),
        0x1000,
        budget,
    );
    let mut state = bus.state.borrow_mut();
    state.phase = "Functional";
    state.composite = Some(closed(path));
    drop(state);
    bus
}
fn read_event(
    pc: u16,
    index: usize,
    address: u16,
    width: u8,
    phase: &str,
    serviced: bool,
) -> DataEvent {
    DataEvent {
        ordinal: 0,
        phase: phase.into(),
        pc: Some(pc),
        instruction_index: Some(index),
        address,
        width,
        operation: "Read".into(),
        requested_value: None,
        value: Some(1),
        old_value: None,
        write_ordinal: None,
        same_value: None,
        serviced,
        refusal: None,
    }
}
fn retirement_fixture(bus: &AuditBus, pc: u16, index: usize, len: usize, retired: u64) {
    // Explicit component state, not a fabricated real execution/retirement log.
    let mut state = bus.state.borrow_mut();
    state.phase = "Executing";
    state.pc = Some(pc);
    state.instruction = Some(index);
    state.selected_len = Some(len);
    state.selected_reads = len;
    state.retirements = retired;
    state.execution_calls = retired + 1;
}

#[test]
fn composite_closed_inventory_and_all_four_path_boundaries_are_exact() {
    let nodes = ClosedCompositeProgram::node_inventory();
    assert_eq!(nodes.len(), 20);
    assert_eq!(nodes.iter().map(|n| n.length).sum::<usize>(), 51);
    assert_eq!(
        nodes
            .iter()
            .map(|n| format!("{:?}", n.form))
            .collect::<BTreeSet<_>>()
            .len(),
        16
    );
    assert_eq!(nodes.first().unwrap().pc, 0x1000);
    assert_eq!(
        nodes.last().unwrap().pc + nodes.last().unwrap().length as u16,
        0x1033
    );
    for (path, count, target) in [
        (CompositePath::A, 11, 0x55c5),
        (CompositePath::B, 13, 0x5596),
        (CompositePath::C, 14, 0x5596),
        (CompositePath::D, 16, 0x5596),
    ] {
        let state = closed(path);
        assert_eq!(path.pcs().len(), count);
        for (n, pc) in path.pcs().iter().enumerate() {
            let next = path.pcs().get(n + 1).copied().unwrap_or(target);
            assert_eq!(state.node(*pc, false, n as u64).unwrap().pc, *pc);
            assert_eq!(
                state.successor(*pc, next, n as u64).unwrap(),
                n + 1 == count
            );
        }
    }
}

#[test]
fn composite_closed_node_refuses_mid_instruction_wrong_dd_and_wrong_path() {
    let state = closed(CompositePath::B);
    for pc in [0x1001, 0x1033, 0x5596, 0x55c5] {
        assert_eq!(
            state.node(pc, false, 0).unwrap_err().code,
            "UnknownCompositeNode"
        );
    }
    assert!(state.node(0x1000, true, 0).is_ok());
    assert_eq!(
        state.node(0x1002, true, 1).unwrap_err().code,
        "WrongIncomingDd"
    );
    assert_eq!(
        state.node(0x1019, false, 10).unwrap_err().code,
        "UnknownCompositeNode"
    );
    assert_eq!(
        state.successor(0x1016, 0x1019, 9).unwrap_err().code,
        "UnknownCompositeSuccessor"
    );
    assert_eq!(
        state.successor(0x1000, 0x1001, 0).unwrap_err().code,
        "UnknownCompositeSuccessor"
    );
}

#[test]
fn composite_closed_successor_requires_actual_j_and_prevents_second_j() {
    let mut state = closed(CompositePath::D);
    assert_eq!(
        state.successor(0x1027, 0x55c5, 15).unwrap_err().code,
        "UnknownCompositeSuccessor"
    );
    assert!(state.successor(0x1027, 0x5596, 15).unwrap());
    state.direct_j_count = 1;
    assert_eq!(
        state.successor(0x1027, 0x5596, 15).unwrap_err().code,
        "InvalidCompositeTerminalJ"
    );
    state.direct_j_count = 0;
    state
        .nodes
        .iter_mut()
        .find(|n| n.pc == 0x1000)
        .unwrap()
        .successors = vec![0x5596];
    assert_eq!(
        state.successor(0x1000, 0x5596, 0).unwrap_err().code,
        "UnknownCompositeSuccessor"
    );
    state
        .nodes
        .iter_mut()
        .find(|n| n.pc == 0x1000)
        .unwrap()
        .form = CompositeForm::JAddress;
    state
        .nodes
        .iter_mut()
        .find(|n| n.pc == 0x1000)
        .unwrap()
        .successors = vec![0x1002];
    assert_eq!(
        state.successor(0x1000, 0x1002, 0).unwrap_err().code,
        "InvalidCompositeTerminalJ"
    );
}

#[test]
fn composite_seed_inventory_aliases_and_derived_paths_are_closed() {
    let data: BTreeMap<_, _> = INVENTORY.iter().map(|a| (*a, 0u8)).collect();
    let r = [0u8; 8];
    let er = [0u16; 4];
    let pointing = [[0x1234u16; 4]; 8];
    for (word, gate7, gate5, path) in [
        (0xbf, 0, 0, CompositePath::A),
        (0xc0, 0x80, 0, CompositePath::B),
        (0x100, 0, 0x20, CompositePath::C),
        (0xffff, 0, 0, CompositePath::D),
    ] {
        let mut seed = data.clone();
        seed.insert(0x196, word as u8);
        seed.insert(0x197, (word >> 8) as u8);
        seed.insert(0x12a, gate7);
        seed.insert(0x124, gate5);
        assert_eq!(
            CompositeSeeds::new(seed, pointing, r, er).unwrap().path(),
            path
        );
    }
    let mut missing = data.clone();
    missing.remove(&0x197);
    assert_eq!(
        CompositeSeeds::new(missing, pointing, r, er)
            .unwrap_err()
            .code,
        "IncompleteCompositeSeeds"
    );
    let mut extra = data.clone();
    extra.insert(0x125, 0);
    assert_eq!(
        CompositeSeeds::new(extra, pointing, r, er)
            .unwrap_err()
            .code,
        "IncompleteCompositeSeeds"
    );
    assert_eq!(
        CompositeSeeds::new(data.clone(), pointing, [1; 8], er)
            .unwrap_err()
            .code,
        "ConflictingCompositeAliases"
    );
    assert_eq!(
        CompositeSeeds::new(data, pointing, r, [1; 4])
            .unwrap_err()
            .code,
        "ConflictingCompositeAliases"
    );
}

#[test]
fn composite_opaque_non_emitter_payload_is_never_admitted() {
    let metadata = CompositeEmissionMetadata {
        kind: "program".into(),
        base: 0x1000,
        end_exclusive: 0x1033,
        source: "M2bjVerifiedSyntheticComposite_20Nodes_51Bytes".into(),
        provenance: "InventedOnly_NoNativeGenerationOwner".into(),
        content_digest: COMPOSITE_SHA256.into(),
        nodes: ClosedCompositeProgram::node_inventory(),
    };
    let code = |m: CompositeEmissionMetadata, a: Vec<u8>, b: Vec<u8>| {
        ClosedCompositeProgram::admit_emission(a, b, m)
            .err()
            .unwrap()
            .code
    };
    assert_eq!(
        code(metadata.clone(), vec![0xa5; 51], vec![0xa5; 51]),
        "WrongCompositeDigest"
    );
    assert_eq!(
        code(metadata.clone(), vec![0xa5; 50], vec![0xa5; 51]),
        "WrongCompositeLength"
    );
    let mut changed = metadata.clone();
    changed.base = 0;
    assert_eq!(
        code(changed, vec![0xa5; 51], vec![0xa5; 51]),
        "WrongCompositeMapping"
    );
    let mut changed = metadata;
    changed.provenance = "OriginalRom".into();
    assert_eq!(
        code(changed, vec![0xa5; 51], vec![0xa5; 51]),
        "WrongEmissionProvenance"
    );
}

#[test]
fn composite_per_instruction_rights_refuse_index_form_path_width_and_direction() {
    let state = closed(CompositePath::B);
    let read = Access {
        address: 0x18e,
        width: 8,
    };
    assert!(state.data_right(0x1000, 747, read, false).is_ok());
    assert_eq!(
        state.data_right(0x1000, 739, read, false).unwrap_err().code,
        "CompositeDataInstructionMismatch"
    );
    assert_eq!(
        state.data_right(0x1000, 747, read, true).unwrap_err().code,
        "CompositeLogicalWriteDenied"
    );
    assert_eq!(
        state
            .data_right(
                0x1009,
                498,
                Access {
                    address: 0x196,
                    width: 8
                },
                false
            )
            .unwrap_err()
            .code,
        "CompositeLogicalReadDenied"
    );
    assert_eq!(
        state
            .data_right(
                0x1009,
                498,
                Access {
                    address: 0x196,
                    width: 16
                },
                true
            )
            .unwrap_err()
            .code,
        "CompositeLogicalWriteDenied"
    );
    assert_eq!(
        state
            .data_right(
                0x1019,
                714,
                Access {
                    address: 0x124,
                    width: 8
                },
                false
            )
            .unwrap_err()
            .code,
        "CompositeDataInstructionMismatch"
    );
    let mut changed = closed(CompositePath::D);
    changed
        .nodes
        .iter_mut()
        .find(|n| n.pc == 0x1003)
        .unwrap()
        .form = CompositeForm::StbAPage;
    assert_eq!(
        changed
            .data_right(0x1003, 1862, read, true)
            .unwrap_err()
            .code,
        "CompositeDataInstructionMismatch"
    );
}

#[test]
fn composite_rmw_requires_current_instruction_read_not_prior_seed_or_failed_event() {
    for (prior_step, phase, serviced, pc, index, address, width) in [
        (true, "Functional", true, 0x1003, 1862, 0x18e, 8),
        (false, "Seed", true, 0x1003, 1862, 0x18e, 8),
        (false, "Functional", false, 0x1003, 1862, 0x18e, 8),
        (false, "Functional", true, 0x1000, 1862, 0x18e, 8),
        (false, "Functional", true, 0x1003, 747, 0x18e, 8),
        (false, "Functional", true, 0x1003, 1862, 0x18f, 8),
        (false, "Functional", true, 0x1003, 1862, 0x18e, 16),
    ] {
        let bus = guard(CompositePath::D, 16);
        if prior_step {
            bus.state
                .borrow_mut()
                .data
                .push(read_event(pc, index, address, width, phase, serviced));
        }
        bus.begin_step(0x1003).unwrap();
        bus.set_instruction(1862);
        if !prior_step {
            bus.state
                .borrow_mut()
                .data
                .push(read_event(pc, index, address, width, phase, serviced));
        }
        assert_eq!(
            bus.begin_data(0x18e, 8, true, Some(1), Some(1))
                .err()
                .unwrap()
                .code,
            "RmwReadMissing"
        );
        assert_eq!(bus.report().raw_data_events.len(), 0);
        assert_eq!(bus.report().data_events.last().unwrap().serviced, false);
    }
    let bus = guard(CompositePath::D, 16);
    bus.begin_step(0x1003).unwrap();
    bus.set_instruction(1862);
    let read = bus.begin_data(0x18e, 8, false, None, None).unwrap();
    bus.end_data(read, Some(1));
    let write = bus.begin_data(0x18e, 8, true, Some(1), Some(1)).unwrap();
    bus.end_data(write, Some(1));
    let report = bus.report();
    assert_eq!(report.data_events[1].same_value, Some(true));
    assert_eq!(report.data_events[1].write_ordinal, Some(0));
}

#[test]
fn composite_current_step_selection_never_reassociates_prior_program_events() {
    let bus = guard(CompositePath::D, 16);
    bus.begin_step(0x1000).unwrap();
    bus.program_read(0x1000, "DecoderProbe").unwrap();
    bus.program_read(0x1003, "DecoderProbe").unwrap();
    bus.associate_selection(2).unwrap();
    bus.program_read(0x1000, "ArchitecturalSelectedFetch")
        .unwrap();
    bus.program_read(0x1001, "ArchitecturalSelectedFetch")
        .unwrap();
    let first = bus.report().program_events;
    {
        let mut state = bus.state.borrow_mut();
        state.phase = "Functional";
        state.retirements = 1;
    }
    bus.begin_step(0x1002).unwrap();
    bus.program_read(0x1002, "DecoderProbe").unwrap();
    bus.associate_selection(1).unwrap();
    let report = bus.report();
    assert_eq!(&report.program_events[..first.len()], first.as_slice());
    assert_eq!(
        report.program_events.last().unwrap().selected_length,
        Some(1)
    );
    assert_eq!(
        report.program_events[1].selection_association.as_deref(),
        Some("DecoderLookahead")
    );
    assert_eq!(report.program_events[2].selection_association, None);

    // An actual executing decoder callback reaches the strict address guard,
    // unlike a host diagnostic probe rejected by the separate purpose guard.
    let outside = guard(CompositePath::D, 16);
    outside.begin_step(0x1000).unwrap();
    assert_eq!(
        outside
            .program_read(0x1033, "DecoderProbe")
            .unwrap_err()
            .code,
        "ProgramOutsideSegment"
    );
    let refused = outside.report();
    assert_eq!(refused.phase, "Executing");
    assert_eq!(refused.program_events.len(), 1);
    assert_eq!(refused.program_events[0].acquired_purpose, "DecoderProbe");
    assert!(!refused.program_events[0].serviced);
    assert_eq!(refused.program_events[0].segment_offset, None);
    assert!(refused.data_events.is_empty());
    assert_eq!(refused.shared_execution_calls, 0);
    assert_eq!(refused.successful_retirements, 0);
}

#[test]
fn composite_budget_guard_faults_before_any_new_program_or_data_attempt() {
    let bus = guard(CompositePath::D, 1);
    bus.state.borrow_mut().retirements = 1;
    assert_eq!(
        bus.begin_step(0x1002).unwrap_err().code,
        "InstructionBudgetExceeded"
    );
    let report = bus.report();
    assert_eq!((report.step_calls, report.successful_retirements), (1, 1));
    assert!(report.program_events.is_empty());
    assert!(report.data_events.is_empty());
    assert_eq!(report.shared_execution_calls, 0);
}

#[test]
fn composite_legacy_budget16_still_seals_after_one_retirement() {
    let bytes = vec![0xa5; 51];
    let bus = AuditBus::new(
        ProgramSegment::new(0x1000, bytes.clone(), &digest(&bytes)).unwrap(),
        Permissions::new(vec![], vec![]).unwrap(),
        0x1000,
        16,
    );
    retirement_fixture(&bus, 0x1000, 747, 2, 0);
    bus.retire(0x1002, None).unwrap();
    let report = bus.report();
    assert!(report.sealed);
    assert_eq!(report.phase, "Sealed");
    assert_eq!(report.terminal_reason.as_deref(), Some("OneStepComplete"));
    assert_eq!(bus.begin_step(0x1002).unwrap_err().code, "SessionSealed");
    assert_eq!(bus.report().successful_retirements, 1);
}

#[test]
fn composite_retirement_continues_only_closed_successor_then_seals_actual_j() {
    let bus = guard(CompositePath::D, 16);
    retirement_fixture(&bus, 0x1000, 747, 2, 0);
    bus.retire(0x1002, None).unwrap();
    assert_eq!(bus.report().phase, "Functional");
    assert!(!bus.report().sealed);
    assert_eq!(bus.report().terminal_reason, None);
    retirement_fixture(&bus, 0x1027, 684, 3, 15);
    bus.retire(0x5596, Some(0x5596)).unwrap();
    let report = bus.report();
    assert_eq!(report.successful_retirements, 16);
    assert!(report.sealed);
    assert_eq!(report.external_exit, Some(0x5596));
    assert_eq!(
        report.terminal_reason.as_deref(),
        Some("ActualDirectJCompleted")
    );
    assert_eq!(
        bus.state
            .borrow()
            .composite
            .as_ref()
            .unwrap()
            .direct_j_count,
        1
    );
    assert_eq!(
        bus.program_read(0x5596, "DecoderProbe").unwrap_err().code,
        "SessionSealed"
    );
    let after = bus.report();
    assert_eq!(after.program_events.len(), 1);
    assert!(!after.program_events[0].serviced);
    assert_eq!(
        after.program_events[0].refusal.as_ref().unwrap().code,
        "SessionSealed"
    );
    assert_eq!(after.shared_execution_calls, 16);
}

#[test]
fn composite_retirement_rejects_non_j_exit_or_wrong_external_authority() {
    for (origin, index, len, retired, after, external, code) in [
        (
            0x1000,
            747,
            2,
            0,
            0x5596,
            Some(0x5596),
            "UnknownCompositeSuccessor",
        ),
        (
            0x1000,
            747,
            2,
            0,
            0x1002,
            Some(0x1002),
            "CompositeExternalTransferMismatch",
        ),
        (
            0x1027,
            684,
            3,
            15,
            0x5596,
            None,
            "CompositeExternalTransferMismatch",
        ),
    ] {
        let bus = guard(CompositePath::D, 16);
        retirement_fixture(&bus, origin, index, len, retired);
        assert_eq!(bus.retire(after, external).unwrap_err().code, code);
        assert_eq!(bus.report().successful_retirements, retired);
        assert!(!bus.report().sealed);
    }

    // The selected fetch count is acquired by real program_read calls. Only
    // the execution-call counter is a private component fixture, not CPU work.
    let incomplete = guard(CompositePath::D, 16);
    incomplete.begin_step(0x1000).unwrap();
    incomplete.program_read(0x1000, "DecoderProbe").unwrap();
    incomplete.associate_selection(2).unwrap();
    incomplete
        .program_read(0x1000, "ArchitecturalSelectedFetch")
        .unwrap();
    incomplete.state.borrow_mut().execution_calls = 1;
    assert_eq!(
        incomplete.retire(0x1002, None).unwrap_err().code,
        "InvalidRetirement"
    );
    let refused = incomplete.report();
    assert_eq!(refused.program_events.len(), 2);
    assert_eq!(refused.successful_retirements, 0);
    assert!(!refused.sealed);
    assert_eq!(incomplete.state.borrow().selected_reads, 1);
    assert_eq!(incomplete.state.borrow().selected_len, Some(2));
}

#[test]
fn composite_host_api_escape_refusals_are_sticky_and_never_service_data() {
    let bus = guard(CompositePath::D, 16);
    assert_eq!(
        bus.begin_capability(0x18e, 8, true, Some(1))
            .unwrap_err()
            .code,
        "CompositeCapabilityDataDenied"
    );
    assert!(bus.report().data_events.is_empty());
    assert!(bus.report().raw_data_events.is_empty());
    assert_eq!(bus.report().data_admission_refusals.len(), 1);
    assert!(!bus.report().data_admission_refusals[0].production_bus_called);
    assert_eq!(
        bus.admit_seed(0x18e, 8).unwrap_err().code,
        "CompositeCapabilityDataDenied"
    );
    let bus = guard(CompositePath::D, 16);
    assert_eq!(
        bus.admit_legacy_step().unwrap_err().code,
        "WrongCompositeApi"
    );
    assert_eq!(bus.report().step_calls, 1);
    assert_eq!(
        bus.begin_step(0x1000).unwrap_err().code,
        "WrongCompositeApi"
    );
    assert!(bus.report().program_events.is_empty());
    let bus = guard(CompositePath::D, 16);
    assert_eq!(
        bus.program_read(0x1000, "DiagnosticProgramProbe")
            .unwrap_err()
            .code,
        "ProgramPurposeOrPhaseDenied"
    );
    assert!(!bus.report().program_events[0].serviced);
}
