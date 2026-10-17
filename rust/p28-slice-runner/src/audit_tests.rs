//! Frozen invented component fixtures. These tests execute no Cpu/step/run loop.
use crate::audit::{self, Access, Permissions, ProgramSegment, WriteAccess};
use crate::{audit_bus::AuditBus, audit_sha256::digest, bus::Bus, decoder};
use std::cell::RefCell;

fn segment(bytes: &[u8]) -> ProgramSegment {
    ProgramSegment::new(0x1000, bytes.to_vec(), &digest(bytes)).unwrap()
}
fn memory(permissions: Permissions) -> Bus {
    let mut bus = Bus::new(vec![], 0xa5);
    bus.audit = Some(AuditBus::new(
        segment(&[0x53, 0xa5, 0x5a, 0xa5, 0x5a, 0xa5]),
        permissions,
        0x1000,
        1,
    ));
    bus
}

#[test]
fn audit_canonical_psw_exhaustive_admission_without_cpu() {
    let mut admitted = 0;
    for psw in 0..=u16::MAX {
        let actual = audit::validate_psw(psw);
        assert_eq!(actual.is_ok(), psw & 0x0cc8 == 0x0cc8);
        admitted += usize::from(actual.is_ok());
    }
    assert_eq!(admitted, 2048);
}

#[test]
fn audit_segment_admission_is_checked_and_digest_bound() {
    assert!(ProgramSegment::new(0x1000, vec![], &digest(&[])).is_err());
    assert!(ProgramSegment::new(65536, vec![1], &digest(&[1])).is_err());
    assert!(ProgramSegment::new(65535, vec![1, 2], &digest(&[1, 2])).is_err());
    assert!(ProgramSegment::new(0x1000, vec![1], &digest(&[2])).is_err());
    let last = ProgramSegment::new(65535, vec![1], &digest(&[1])).unwrap();
    assert_eq!((last.base(), last.end_exclusive()), (65535, 65536));
    assert_eq!(last.sha256(), digest(&[1]));
    assert!(last.contains_address(65535));
    assert!(!last.contains_address(65534));
    let mapped = segment(&[0xa5; 51]);
    assert!(!mapped.contains_address(0x0fff));
    assert!(mapped.contains_address(0x1000));
    assert!(mapped.contains_address(0x1032));
    assert!(!mapped.contains_address(0x1033));
}

#[test]
fn audit_permissions_do_not_infer_direction_width_or_sfr() {
    let read = Access {
        address: 0x196,
        width: 16,
    };
    let store = WriteAccess {
        access: Access {
            address: 0x18f,
            width: 8,
        },
        rmw_required: false,
    };
    let rights = Permissions::new(vec![read], vec![store.clone()]).unwrap();
    assert_eq!(rights.raw_reads, [0x196, 0x197]);
    assert_eq!(rights.raw_writes, [0x18f]);
    assert!(!rights.reads.contains(&Access {
        address: 0x196,
        width: 8
    }));
    assert!(Permissions::new(vec![read, read], vec![]).is_err());
    assert!(Permissions::new(vec![], vec![store.clone(), store]).is_err());
    for address in [0, 7, 0x7f, 0x1000, 0xffff] {
        assert!(Permissions::new(vec![Access { address, width: 8 }], vec![]).is_err());
    }
    assert!(Permissions::new(
        vec![Access {
            address: 0x196,
            width: 32
        }],
        vec![]
    )
    .is_err());
    assert!(Permissions::new(
        vec![Access {
            address: 0xffff,
            width: 16
        }],
        vec![]
    )
    .is_err());
}

#[test]
fn audit_raw_rights_only_narrow_independent_constituents() {
    let access = Access {
        address: 0x108,
        width: 16,
    };
    let rights = Permissions::new(
        vec![access],
        vec![WriteAccess {
            access,
            rmw_required: false,
        }],
    )
    .unwrap();
    let narrowed = rights
        .clone()
        .restrict_raw(vec![0x108], vec![0x109])
        .unwrap();
    assert_eq!(narrowed.raw_reads, [0x108]);
    assert_eq!(narrowed.raw_writes, [0x109]);
    assert!(rights.clone().restrict_raw(vec![0x10a], vec![]).is_err());
    assert!(rights.restrict_raw(vec![], vec![0x108, 0x108]).is_err());
}

#[test]
fn audit_checked_decoder_propagates_typed_first_callback_failure() {
    let calls = RefCell::new(vec![]);
    let failure = audit::AuditError::new(
        "FrozenCallbackRefusal",
        Some(0x1001),
        "invented strict decoder boundary",
    );
    let actual = decoder::decode_checked(false, |offset| {
        calls.borrow_mut().push(offset);
        if offset == 0 {
            Ok(0xc4)
        } else {
            Err(failure.clone())
        }
    });
    assert_eq!(actual.unwrap_err(), failure);
    let log = calls.borrow();
    assert_eq!(log.last(), Some(&1));
    assert!(log[..log.len() - 1].iter().all(|offset| *offset == 0));
    assert!(log.len() >= 2);
}

#[test]
fn audit_legacy_and_checked_matching_share_exact_callbacks_and_fields() {
    // Sixteen independently sealed M2bm invented microforms, not a composite.
    let fixtures: &[&[u8]] = &[
        &[0xf4, 0x17],
        &[0x53],
        &[0xc4, 0x8e, 0xb7],
        &[0x78],
        &[0xd7, 0x17],
        &[0xb4, 0x96, 0xc0, 0x35, 0x12],
        &[0xca, 0xfe],
        &[0xc4, 0x17, 0x49],
        &[0xc4, 0x17, 0xd1],
        &[0xef, 0x2a, 0xfd],
        &[0xed, 0x24, 0xfd],
        &[0xc4, 0x2a, 0xe0, 0x04],
        &[0xe6, 0x12],
        &[0x77, 0x00],
        &[0xd4, 0x8f],
        &[0x03, 0xc5, 0x55],
    ];
    for instruction in fixtures {
        let mut bytes = instruction.to_vec();
        bytes.resize(6, 0xa5);
        for dd in [false, true] {
            let legacy_calls = RefCell::new(vec![]);
            let strict_calls = RefCell::new(vec![]);
            let legacy = decoder::decode(dd, |offset| {
                legacy_calls.borrow_mut().push(offset);
                bytes[offset]
            });
            let strict = decoder::decode_checked::<()>(dd, |offset| {
                strict_calls.borrow_mut().push(offset);
                Ok(bytes[offset])
            })
            .unwrap();
            assert_eq!(format!("{legacy:?}"), format!("{strict:?}"));
            assert_eq!(*legacy_calls.borrow(), *strict_calls.borrow());
        }
    }
}

#[test]
fn audit_real_bus_mapping_latches_bounds_without_prefix_fallback() {
    let bus = memory(Permissions::new(vec![], vec![]).unwrap());
    let audit = bus.audit.as_ref().unwrap();
    assert_eq!(audit.external_target(0x1000), None);
    assert_eq!(audit.external_target(0x1005), None);
    assert_eq!(audit.external_target(0x0fff), Some(0x0fff));
    assert_eq!(audit.external_target(0x1006), Some(0x1006));
    assert_eq!(audit.external_target(0x5596), Some(0x5596));
    assert_eq!(audit.external_target(0x55c5), Some(0x55c5));
    assert_eq!(
        bus.audit_program_read(0x1000, "DiagnosticProgramProbe")
            .unwrap(),
        0x53
    );
    assert_eq!(
        bus.audit_program_read(0x1005, "DiagnosticProgramProbe")
            .unwrap(),
        0xa5
    );
    assert_eq!(
        bus.audit_program_read(0x0fff, "DiagnosticProgramProbe")
            .unwrap_err()
            .code,
        "ProgramOutsideSegment"
    );
    assert!(bus.take_fault().is_some());
    assert!(bus
        .audit_program_read(0x1000, "DiagnosticProgramProbe")
        .is_err());
    let report = bus.audit.as_ref().unwrap().report();
    assert_eq!(report.program_events.len(), 4);
    assert!(report.program_events[..2]
        .iter()
        .all(|event| event.serviced));
    assert!(report.program_events[2..]
        .iter()
        .all(|event| !event.serviced));
    assert_eq!(report.program_events[2].address, 0x0fff);
    assert_eq!(report.execution_calls, 0);
}

#[test]
fn audit_real_word_service_retains_low_write_and_denies_high_then_latches() {
    let access = Access {
        address: 0x108,
        width: 16,
    };
    let rights = Permissions::new(
        vec![],
        vec![WriteAccess {
            access,
            rmw_required: false,
        }],
    )
    .unwrap()
    .restrict_raw(vec![], vec![0x108])
    .unwrap();
    let mut bus = memory(rights);
    bus.audit.as_ref().unwrap().admit_seed(0x108, 16).unwrap();
    bus.write_data_u16(0x108, 0x1234);
    bus.audit.as_ref().unwrap().begin_functional().unwrap();
    bus.write_data_u16(0x108, 0xabcd);
    assert!(bus.take_fault().is_some());
    bus.write_data_u16(0x108, 0xffff);
    let ram = bus.audit_snapshot_ram();
    assert_eq!(&ram[0x108 - 0x80..0x10a - 0x80], &[0xcd, 0x12]);
    let report = bus.audit.as_ref().unwrap().report();
    assert_eq!(report.data_events.len(), 3);
    assert_eq!(report.raw_data_events.len(), 4);
    assert!(report.data_events[0].serviced);
    assert!(!report.data_events[1].serviced);
    assert!(!report.data_events[2].serviced);
    assert!(report.raw_data_events[2].serviced);
    assert!(!report.raw_data_events[3].serviced);
    assert_eq!(report.first_fault.unwrap().code, "RawWriteDenied");
    assert_eq!(report.shared_execution_calls, 0);
}

#[test]
fn audit_seed_phase_is_once_only_and_diagnostic_is_not_functional_read() {
    let mut bus = memory(Permissions::new(vec![], vec![]).unwrap());
    bus.audit.as_ref().unwrap().admit_seed(0x117, 8).unwrap();
    bus.write_data_u8(0x117, 7);
    assert_eq!(bus.audit_snapshot_ram()[0x117 - 0x80], 7);
    bus.audit.as_ref().unwrap().begin_functional().unwrap();
    assert_eq!(
        bus.audit
            .as_ref()
            .unwrap()
            .admit_seed(0x118, 8)
            .unwrap_err()
            .code,
        "SeedOutsideSetup"
    );
    let report = bus.audit.as_ref().unwrap().report();
    assert_eq!(report.data_events.len(), 1);
    assert_eq!(report.data_events[0].phase, "Seed");
    assert_eq!(report.diagnostic_events.len(), 1);
    assert_eq!(report.diagnostic_events[0].byte_count, 3968);
}

#[test]
fn audit_rmw_requires_real_read_and_same_value_write_is_retained() {
    let access = Access {
        address: 0x12a,
        width: 8,
    };
    let rights = Permissions::new(
        vec![access],
        vec![WriteAccess {
            access,
            rmw_required: true,
        }],
    )
    .unwrap();
    let mut denied = memory(rights.clone());
    denied.audit.as_ref().unwrap().begin_functional().unwrap();
    denied.audit_snapshot_ram();
    denied.write_data_u8(0x12a, 0xa5);
    assert_eq!(
        denied
            .audit
            .as_ref()
            .unwrap()
            .report()
            .first_fault
            .unwrap()
            .code,
        "RmwReadMissing"
    );
    let mut accepted = memory(rights);
    accepted.audit.as_ref().unwrap().begin_functional().unwrap();
    let old = accepted.read_data_u8(0x12a);
    accepted.write_data_u8(0x12a, old);
    let report = accepted.audit.as_ref().unwrap().report();
    assert!(report.first_fault.is_none());
    assert_eq!(report.data_events.len(), 2);
    assert_eq!(report.data_events[1].same_value, Some(true));
    assert_eq!(report.data_events[1].write_ordinal, Some(0));
    assert_eq!(report.raw_data_events[1].same_value, Some(true));
    assert_eq!(report.raw_data_events[1].write_ordinal, Some(0));
}

#[test]
fn audit_prebus_admission_refusal_is_addressed_without_fake_bus_events() {
    let audit = AuditBus::new(
        segment(&[0x53]),
        Permissions::new(vec![], vec![]).unwrap(),
        0x1000,
        1,
    );
    audit.begin_functional().unwrap();
    let error = audit
        .begin_capability(0x117, 8, true, Some(256))
        .unwrap_err();
    assert_eq!(error.code, "InvalidDataWidthOrValue");
    let report = audit.report();
    assert_eq!(report.data_admission_refusals.len(), 1);
    let attempt = &report.data_admission_refusals[0];
    assert_eq!(attempt.classification, "PreBusApiAdmissionRefusal");
    assert_eq!(
        (attempt.pc, attempt.address, attempt.width),
        (0x1000, 0x117, 8)
    );
    assert_eq!(attempt.phase, "Functional");
    assert_eq!(attempt.requested_value, Some(256));
    assert_eq!(attempt.refusal, error);
    assert!(!attempt.production_bus_called && !attempt.serviced);
    assert!(report.data_events.is_empty() && report.raw_data_events.is_empty());
    assert_eq!(report.shared_execution_calls, 0);
}
