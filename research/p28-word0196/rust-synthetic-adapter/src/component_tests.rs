//! Component runtime tests, never additional instruction-execution probes.
//! Only entry/PSW tests construct Cpu; all tests retire zero instructions.
use super::*;
use admission::{ClosedFormAdmission, TypedOperand};
use data::{IndependentDataAccessPolicy, WriteKind, INVENTORY};
use exit::SyntheticExternalExitTrap;
use fetch::OrderedProgramFetchObserver;
use p28_slice_runner::{
    decoder::{Decoded, Fields},
    full_decoder::FULL_OPCODES,
};
use program::{MicroProgram, SegmentDescriptor, SyntheticProgramSegment};
use std::collections::BTreeMap;

fn seeds() -> BTreeMap<u16, u8> {
    INVENTORY
        .into_iter()
        .map(|a| (a, (a & 255) as u8))
        .collect()
}
fn policy(path: DataPath) -> IndependentDataAccessPolicy {
    let mut result = IndependentDataAccessPolicy::new(path, &seeds()).unwrap();
    result.begin_functional().unwrap();
    result
}
fn descriptor() -> SegmentDescriptor {
    SegmentDescriptor {
        base: 0x1000,
        end_exclusive: 0x1033,
        length: 51,
        source_identity: UPSTREAM_SOURCE.into(),
        immutable_content_identity: UPSTREAM_DIGEST.into(),
        addressing: "SubtractBase_NoModulo_NoPadding".into(),
        padding: 0,
    }
}
fn cells() -> [String; 51] {
    std::array::from_fn(|n| format!("InventedOpaqueOffsetIdentity-{n}"))
}
fn micro() -> MicroProgram {
    let bytes = [0x53, 0xa5, 0x5a, 0xa5, 0x5a, 0xa5];
    MicroProgram::new(
        "sllb-a-preserve-zf",
        FormId::SllbA,
        &bytes[..1],
        &bytes[1..],
        &sha256::digest(&bytes),
        INVENTED_PROVENANCE,
    )
    .unwrap()
}
fn entry_fixture() -> SyntheticCpuEntrySnapshot {
    let data = seeds();
    let local_r = std::array::from_fn(|n| data[&(0x108 + n as u16)]);
    SyntheticCpuEntrySnapshot {
        pc: 0x1000,
        a: 0xa581,
        al: 0x81,
        ah: 0xa5,
        psw: 0xeccb,
        cf: true,
        zf: true,
        hc: true,
        dd: false,
        other_psw: 0xccb,
        lrb: 0x21,
        scb: 3,
        ssp: 0x37a1,
        pointing_banks: std::array::from_fn(|n| PointingBank {
            x1: 0x1001 + n as u16 * 0x100,
            x2: 0x1002 + n as u16 * 0x100,
            dp: 0x1003 + n as u16 * 0x100,
            usp: 0x1004 + n as u16 * 0x100,
        }),
        local_r,
        local_er: std::array::from_fn(|n| u16::from_le_bytes([local_r[2 * n], local_r[2 * n + 1]])),
        halted: false,
        provenance: INVENTED_PROVENANCE.into(),
        sf: sf::OpaqueSfBoundary {
            status: "SFMeaningStorageNotEstablished".into(),
            value: None,
            meaning: None,
            storage: None,
            width_bits: None,
        },
    }
}

#[test]
fn program_maps_all51_opaque_offsets_without_padding() {
    let segment = SyntheticProgramSegment::new(descriptor(), cells()).unwrap();
    for n in 0..51 {
        assert_eq!(segment.translate(0x1000 + n).unwrap(), n as usize);
        assert_eq!(
            segment.read_opaque(0x1000 + n).unwrap(),
            format!("InventedOpaqueOffsetIdentity-{n}")
        );
    }
    assert_eq!(segment.translate(0x1000).unwrap(), 0);
    assert_eq!(segment.translate(0x1032).unwrap(), 50);
}
#[test]
fn program_refuses_underflow_end_anchors_overflow_data_confusion() {
    let segment = SyntheticProgramSegment::new(descriptor(), cells()).unwrap();
    for address in [
        0,
        0x108,
        0x196,
        0xfff,
        0x1033,
        0x5596,
        0x55c5,
        0xffff,
        u32::MAX,
    ] {
        assert!(segment.translate(address).is_err());
    }
}
#[test]
fn program_refuses_fake_padding_base_length_content_and_source() {
    let valid = descriptor();
    for mut bad in [
        valid.clone(),
        valid.clone(),
        valid.clone(),
        valid.clone(),
        valid.clone(),
        valid.clone(),
    ]
    .into_iter()
    .enumerate()
    {
        match bad.0 {
            0 => bad.1.padding = 4096,
            1 => bad.1.base = 0,
            2 => bad.1.length = 50,
            3 => bad.1.end_exclusive = 0x1034,
            4 => bad.1.source_identity = "ROM".into(),
            _ => bad.1.immutable_content_identity.clear(),
        }
        assert!(SyntheticProgramSegment::new(bad.1, cells()).is_err());
    }
    let mut altered = cells();
    altered[50] = "changed".into();
    assert!(SyntheticProgramSegment::new(valid, altered).is_err());
}
#[test]
fn microprogram_refuses_full51_shape_originalrom_and_wronghash() {
    let invented51 = [0xa5; 51];
    assert!(MicroProgram::new(
        "sllb-a-preserve-zf",
        FormId::SllbA,
        &invented51,
        &[],
        UPSTREAM_DIGEST,
        INVENTED_PROVENANCE
    )
    .is_err());
    assert!(MicroProgram::new(
        "ROM",
        FormId::SllbA,
        &[0x53],
        &[],
        &sha256::digest(&[0x53]),
        "OriginalROM"
    )
    .is_err());
    assert!(MicroProgram::new(
        "sllb-a-preserve-zf",
        FormId::SllbA,
        &[0x53],
        &[],
        "wrong",
        INVENTED_PROVENANCE
    )
    .is_err());
}
#[test]
fn microprogram_refuses_unknown_fixture_form_swapped_j_and_stub() {
    for (id, form, bytes) in [
        ("unknown", FormId::SllbA, vec![0x53]),
        ("sllb-a-preserve-zf", FormId::StbAPage, vec![0x53]),
        ("direct-j-55c5", FormId::JAddress, vec![3, 0x96, 0x55]),
        ("direct-j-55c5", FormId::JAddress, vec![0]),
        ("sllb-a-preserve-zf", FormId::SllbA, vec![0x53, 0]),
    ] {
        assert!(MicroProgram::new(
            id,
            form,
            &bytes,
            &[],
            &sha256::digest(&bytes),
            INVENTED_PROVENANCE
        )
        .is_err());
    }
}
#[test]
fn microprogram_refuses_guard_padding_or_nonopaque_guard() {
    assert!(MicroProgram::new(
        "sllb-a-preserve-zf",
        FormId::SllbA,
        &[0x53],
        &[0; 5],
        "wrong",
        INVENTED_PROVENANCE
    )
    .is_err());
    assert!(MicroProgram::new(
        "sllb-a-preserve-zf",
        FormId::SllbA,
        &[0x53],
        &[0xa5; 6],
        "wrong",
        INVENTED_PROVENANCE
    )
    .is_err());
}
#[test]
fn admission_checks_exact20_and_all16_forms_as_metadata_only() {
    let nodes = ClosedFormAdmission::inventory();
    assert_eq!(nodes.len(), 20);
    ClosedFormAdmission::validate_inventory(&nodes).unwrap();
    let distinct: std::collections::BTreeSet<_> = nodes
        .iter()
        .map(|n| serde_json::to_string(&n.form).unwrap())
        .collect();
    assert_eq!(distinct.len(), 16);
    for node in nodes {
        ClosedFormAdmission::admit(&node, false).unwrap();
        assert_eq!(
            ClosedFormAdmission::admit(&node, true).is_ok(),
            node.pc == 0x1000
        );
    }
}
#[test]
fn admission_refuses_missing_duplicate_extra_and_reordered_nodes() {
    let nodes = ClosedFormAdmission::inventory();
    let mut missing = nodes.clone();
    missing.pop();
    assert!(ClosedFormAdmission::validate_inventory(&missing).is_err());
    let mut duplicate = nodes.clone();
    duplicate[1] = duplicate[0].clone();
    assert!(ClosedFormAdmission::validate_inventory(&duplicate).is_err());
    let mut extra = nodes.clone();
    extra.push(extra[0].clone());
    assert!(ClosedFormAdmission::validate_inventory(&extra).is_err());
    let mut reordered = nodes;
    reordered.swap(1, 2);
    assert!(ClosedFormAdmission::validate_inventory(&reordered).is_err());
}
#[test]
fn admission_refuses_pc_node_form_operand_length_target_and_primary_source_mutations() {
    let original = ClosedFormAdmission::inventory()[0].clone();
    for mutation in 0..9 {
        let mut node = original.clone();
        match mutation {
            0 => node.pc += 1,
            1 => node.node_identity = "fake".into(),
            2 => node.form = FormId::StbAPage,
            3 => node.operands[1] = TypedOperand::Page(0x17),
            4 => node.length += 1,
            5 => node.successors = vec![0x5596],
            6 => node.primary_pattern[0] = "NOP".into(),
            7 => node.source_sha256 = "wrong".into(),
            _ => node.manual_sha256 = "wrong".into(),
        }
        assert!(ClosedFormAdmission::admit(&node, false).is_err());
    }
}
#[test]
fn exact_form_gate_refuses_wrong_index_fields_dd_and_mnemonic() {
    let index = FULL_OPCODES
        .iter()
        .position(|p| p.mnemonic == "SLLB A")
        .unwrap();
    let original = Decoded {
        index,
        mnemonic: "SLLB A",
        len: 1,
        fields: Fields::default(),
        dd_after: None,
        cycles: 2,
    };
    FormId::SllbA.validate_decoded(&original, false).unwrap();
    assert!(FormId::SllbA.validate_decoded(&original, true).is_err());
    assert!(FormId::StbAPage.validate_decoded(&original, false).is_err());
    for mutation in 0..4 {
        let mut bad = original.clone();
        match mutation {
            0 => bad.index = usize::MAX,
            1 => bad.mnemonic = "CAL addr16",
            2 => bad.len = 3,
            _ => bad.dd_after = Some(true),
        };
        assert!(FormId::SllbA.validate_decoded(&bad, false).is_err());
    }
    let mut bad = original;
    bad.fields.n8 = 1;
    assert!(executor::validate_selected_fields(FormId::SllbA, &bad, &[0x53]).is_err());
}
#[test]
fn entry_requires_every_field_and_all8_banks() {
    let valid = entry_fixture();
    let object = serde_json::to_value(&valid).unwrap();
    for name in object.as_object().unwrap().keys() {
        let mut bad = object.clone();
        bad.as_object_mut().unwrap().remove(name);
        assert!(
            serde_json::from_value::<SyntheticCpuEntrySnapshot>(bad).is_err(),
            "{name}"
        );
    }
    let mut bad = object;
    bad["pointing_banks"].as_array_mut().unwrap().pop();
    assert!(serde_json::from_value::<SyntheticCpuEntrySnapshot>(bad).is_err());
}
#[test]
fn sf_requires_explicit_null_fields_and_rejects_boolean_default() {
    let opaque = serde_json::to_value(entry_fixture().sf).unwrap();
    for name in ["value", "meaning", "storage", "width_bits", "status"] {
        let mut bad = opaque.clone();
        bad.as_object_mut().unwrap().remove(name);
        assert!(
            serde_json::from_value::<sf::OpaqueSfBoundary>(bad).is_err(),
            "{name}"
        );
    }
    let mut bad = entry_fixture().sf;
    bad.value = Some(false);
    assert!(bad.validate().is_err());
}
#[test]
fn entry_refuses_conflicting_accumulator_flags_scb_and_local_aliases() {
    for mutation in 0..8 {
        let mut bad = entry_fixture();
        match mutation {
            0 => bad.al ^= 1,
            1 => bad.ah ^= 1,
            2 => bad.cf = !bad.cf,
            3 => bad.other_psw |= 0x8000,
            4 => bad.scb = 0,
            5 => bad.local_r[1] ^= 1,
            6 => bad.local_er[0] ^= 1,
            _ => bad.lrb = 0,
        };
        assert!(bad.validate(&seeds()).is_err());
    }
}
#[test]
fn entry_roundtrips_all8_scb_and32_pointing_canaries_without_functional_effects() {
    for scb in 0..8 {
        let mut entry = entry_fixture();
        entry.scb = scb;
        entry.psw = (entry.psw & !7) | scb;
        entry.other_psw = entry.psw & 0xfff;
        entry.validate(&seeds()).unwrap();
        let cpu = entry.seed_cpu(true).unwrap();
        assert_eq!(cpu.scb(), scb);
        assert_eq!(cpu.bank_base(), 0x108);
        assert_eq!(cpu.off_page(0x96), 0x196);
        let mut data = IndependentDataAccessPolicy::new(DataPath::D, &seeds()).unwrap();
        entry.seed_banks(&mut data).unwrap();
        assert_eq!(entry.snapshot(&cpu, &mut data).unwrap(), entry);
        assert!(data.journal.is_empty());
        assert!(data.raw_journal.is_empty());
        assert_eq!(data.seed_journal.len(), 48);
        assert_eq!(cpu.instructions, 0);
        assert!(cpu.sf);
    }
}
#[test]
fn pointing_register_address_boundaries_and_aliases_are_checked() {
    for bank in 0..8 {
        for slot in 0..4 {
            assert_eq!(
                entry::pointing_address(bank, slot).unwrap(),
                0x80 + bank as u16 * 8 + slot as u16 * 2
            );
        }
    }
    assert!(entry::pointing_address(8, 0).is_err());
    assert!(entry::pointing_address(0, 4).is_err());
    let entry = entry_fixture();
    assert_eq!(
        entry.local_er[0],
        u16::from_le_bytes([entry.local_r[0], entry.local_r[1]])
    );
}
#[test]
fn data_permissions_are_independent_and_path_specific() {
    assert!(IndependentDataAccessPolicy::read_permission(
        DataPath::B,
        0x196,
        16
    ));
    assert!(!IndependentDataAccessPolicy::write_permission(
        DataPath::B,
        0x196,
        16
    ));
    assert!(!IndependentDataAccessPolicy::read_permission(
        DataPath::B,
        0x109,
        8
    ));
    assert!(IndependentDataAccessPolicy::write_permission(
        DataPath::B,
        0x109,
        8
    ));
    assert!(!IndependentDataAccessPolicy::read_permission(
        DataPath::B,
        0x124,
        8
    ));
    assert!(IndependentDataAccessPolicy::read_permission(
        DataPath::C,
        0x124,
        8
    ));
    assert!(!IndependentDataAccessPolicy::write_permission(
        DataPath::C,
        0x12a,
        8
    ));
    assert!(IndependentDataAccessPolicy::write_permission(
        DataPath::D,
        0x12a,
        8
    ));
}
#[test]
fn data_refuses_readonly_write_writeonly_read_unknown_and_immediate_address() {
    for (address, width) in [
        (0x196, 8),
        (0x197, 8),
        (0x196, 16),
        (0xc0, 8),
        (0x128, 8),
        (0x10a, 8),
    ] {
        assert!(policy(DataPath::D)
            .write(0x1000, address, width, 1, WriteKind::Store)
            .is_err());
    }
    for address in [0x109, 0xc0, 0x128, 0x10a, 0xfff] {
        assert!(policy(DataPath::D).read(0x1000, address, 8).is_err());
    }
}
#[test]
fn data_refuses_wrong_width_overlap_and_reversed_le_constituents() {
    for (address, width) in [
        (0x195, 16),
        (0x197, 16),
        (0x196, 8),
        (0x197, 8),
        (0x18e, 16),
        (0x117, 0),
        (0x117, 32),
    ] {
        assert!(policy(DataPath::D).read(0x1000, address, width).is_err());
    }
    let mut data = policy(DataPath::D);
    assert_eq!(data.read(0x1000, 0x196, 16).unwrap(), 0x9796);
    assert_eq!(
        data.raw_journal
            .iter()
            .map(|e| e.address)
            .collect::<Vec<_>>(),
        [0x196, 0x197]
    );
    assert_eq!(data.journal[0].constituents, [0x96, 0x97]);
    assert_ne!(data.journal[0].value, u16::from_be_bytes([0x96, 0x97]));
}
#[test]
fn data_same_value_writes_keep_fresh_ordinals_without_functional_old_reads() {
    let mut data = policy(DataPath::A);
    for _ in 0..2 {
        data.write(0x1000, 0x18f, 8, 0x8f, WriteKind::Store)
            .unwrap();
    }
    assert_eq!(data.journal.len(), 2);
    assert!(data
        .journal
        .iter()
        .all(|e| e.same_value && e.operation == "Write"));
    assert_eq!(
        data.journal
            .iter()
            .map(|e| e.write_ordinal)
            .collect::<Vec<_>>(),
        [Some(1), Some(2)]
    );
    assert_eq!(data.diagnostic_journal.len(), 2);
    assert_eq!(data.raw_journal.len(), 2);
}
#[test]
fn journal_tampered_word_address_overflow_is_a_controlled_refusal() {
    let mut data = policy(DataPath::D);
    data.read(0x1000, 0x196, 16).unwrap();
    data.journal[0].address = u16::MAX;
    data.raw_journal[0].address = u16::MAX;
    assert_eq!(
        data.validate_journals().unwrap_err().code,
        "FunctionalJournalMismatch"
    );
}
#[test]
fn rmw_first_write_without_read_is_refused_and_fault_latches() {
    let mut data = policy(DataPath::D);
    let before = data.inventory_snapshot().unwrap();
    assert_eq!(
        data.write(0x1000, 0x18e, 8, 3, WriteKind::RMW)
            .unwrap_err()
            .code,
        "RmwReadRequired"
    );
    assert!(data.journal.is_empty());
    assert!(data.raw_journal.is_empty());
    assert!(data.read(0x1000, 0x18e, 8).is_err());
    assert!(data.write(0x1000, 0x18f, 8, 4, WriteKind::Store).is_err());
    assert_eq!(data.inventory_snapshot().unwrap(), before);
    assert!(data.journal.is_empty());
}
#[test]
fn typed_store_cannot_bypass_address_path_rmw_or_local_register_requirements() {
    for (path, address) in [
        (DataPath::A, 0x18e),
        (DataPath::D, 0x18e),
        (DataPath::D, 0x117),
        (DataPath::D, 0x12a),
        (DataPath::D, 0x18f),
        (DataPath::B, 0x109),
    ] {
        let mut data = policy(path);
        let before = data.inventory_snapshot().unwrap();
        assert_eq!(
            data.write(0x1000, address, 8, 0, WriteKind::Store)
                .unwrap_err()
                .code,
            "WrongDataAccessKind"
        );
        assert_eq!(data.inventory_snapshot().unwrap(), before);
        assert!(data.journal.is_empty());
        assert!(data.raw_journal.is_empty());
    }
}
#[test]
fn rmw_requires_same_address_and_actual_last_read_then_records_both_effects() {
    let mut wrong = policy(DataPath::D);
    wrong.read(0x1000, 0x117, 8).unwrap();
    assert!(wrong.write(0x1000, 0x18e, 8, 0, WriteKind::RMW).is_err());
    assert_eq!(wrong.journal.len(), 1);
    let mut data = policy(DataPath::D);
    let old = data.read(0x1000, 0x18e, 8).unwrap();
    data.write(0x1000, 0x18e, 8, old, WriteKind::RMW).unwrap();
    assert_eq!(
        data.journal
            .iter()
            .map(|e| e.operation.as_str())
            .collect::<Vec<_>>(),
        ["Read", "Write"]
    );
    assert!(data.journal[1].same_value);
}
#[test]
fn local_store_changes_high_er0_but_diagnostic_snapshot_does_not_pollute_journal() {
    let mut data = policy(DataPath::D);
    let low = data.diagnostic_byte(0x108).unwrap();
    data.write(0x1000, 0x109, 8, 0xa6, WriteKind::LocalRegisterStore)
        .unwrap();
    assert_eq!(
        data.diagnostic_word(0x108).unwrap(),
        u16::from_le_bytes([low, 0xa6])
    );
    assert_eq!(data.journal.len(), 1);
    assert!(data
        .write(0x1000, 0x117, 8, 1, WriteKind::LocalRegisterStore)
        .is_err());
}
#[test]
fn setup_is_once_only_and_separate_from_functional_journal() {
    let mut data = IndependentDataAccessPolicy::new(DataPath::D, &seeds()).unwrap();
    data.seed_word(0x80, 0x1234).unwrap();
    assert!(data.journal.is_empty());
    assert!(data.raw_journal.is_empty());
    assert!(data.seed_word(0x80, 0x1234).is_err());
    let mut data = policy(DataPath::D);
    assert!(data.seed_word(0x80, 0x1234).is_err());
    let mut missing = seeds();
    missing.remove(&0x108);
    assert!(IndependentDataAccessPolicy::new(DataPath::D, &missing).is_err());
}
#[test]
fn raw_program_reads_record_duplicates_before_selected_real_reads() {
    let program = micro();
    let observer = OrderedProgramFetchObserver::new();
    observer.read(&program, 0x1000, "DecoderProbe").unwrap();
    observer.read(&program, 0x1000, "DecoderProbe").unwrap();
    observer.read(&program, 0x1001, "DecoderProbe").unwrap();
    observer.classify_decoder_lookahead(1).unwrap();
    assert_eq!(observer.read_selected(&program, 1).unwrap(), [0x53]);
    let events = observer.events();
    assert_eq!(events.len(), 4);
    assert_eq!(
        events.iter().map(|e| e.ordinal).collect::<Vec<_>>(),
        [1, 2, 3, 4]
    );
    assert_eq!(events[2].acquired_purpose, "DecoderProbe");
    assert_eq!(events[2].purpose, "DecoderLookahead");
    assert_eq!(events[3].purpose, "ArchitecturalSelectedFetch");
}
#[test]
fn out_of_range_probe_records_fault_never_zero_and_faults_latch() {
    let program = micro();
    let observer = OrderedProgramFetchObserver::new();
    assert!(observer.read(&program, 0x1006, "DecoderProbe").is_err());
    assert!(observer.read(&program, 0x1000, "DecoderProbe").is_err());
    assert!(observer
        .events()
        .iter()
        .all(|e| e.value.is_none() && e.fault.is_some()));
}
#[test]
fn selected_lookahead_diagnostic_and_retirement_phases_cannot_be_mixed() {
    let program = micro();
    let observer = OrderedProgramFetchObserver::new();
    observer
        .read(&program, 0x1000, "DiagnosticProgramProbe")
        .unwrap();
    assert!(observer.classify_decoder_lookahead(1).is_err());
    let observer = OrderedProgramFetchObserver::new();
    assert!(observer.read_selected(&program, 1).is_err());
    let observer = OrderedProgramFetchObserver::new();
    observer.read(&program, 0x1000, "DecoderProbe").unwrap();
    observer.classify_decoder_lookahead(1).unwrap();
    observer.read_selected(&program, 1).unwrap();
    assert!(observer.read_selected(&program, 1).is_err());
    observer.seal_after_retirement();
    assert!(observer.read(&program, 0x1000, "DecoderProbe").is_err());
}
#[test]
fn exit_refuses_zero_steps_anchor_entry_fake_stop_and_wrong_target() {
    for entry in [0x5596, 0x55c5, 0] {
        assert!(SyntheticExternalExitTrap::new(entry, 1).is_err());
    }
    assert!(SyntheticExternalExitTrap::new(0x1000, 0).is_err());
    assert!(SyntheticExternalExitTrap::new(0x1000, 2).is_err());
    let mut trap = SyntheticExternalExitTrap::new(0x1000, 1).unwrap();
    assert!(trap.require_external_exit(0x55c5).is_err());
    assert!(trap
        .record_retirement(0x1000, 0x1003, FormId::JAddress)
        .is_err());
    assert!(trap.require_external_exit(0x1003).is_err());
}
#[test]
fn exit_requires_one_direct_j_then_blocks_fetch_extra_instruction_and_two_transfers() {
    let mut trap = SyntheticExternalExitTrap::new(0x1000, 1).unwrap();
    trap.before_fetch().unwrap();
    trap.record_retirement(0x1000, 0x55c5, FormId::JAddress)
        .unwrap();
    trap.require_external_exit(0x55c5).unwrap();
    assert!(trap.before_fetch().is_err());
    assert!(trap.require_external_exit(0x5596).is_err());
    assert!(trap
        .record_retirement(0x1000, 0x55c5, FormId::JAddress)
        .is_err());
    assert!(trap.require_external_exit(0x55c5).is_err());
    let mut fake = SyntheticExternalExitTrap::new(0x1000, 1).unwrap();
    assert!(fake
        .record_retirement(0x1000, 0x55c5, FormId::LbAImm8)
        .is_err());
}
#[test]
fn incompatible_psw_is_refused_before_cpu_mutation_and_expected_is_lossless() {
    let entry = entry_fixture();
    let mut cpu = entry.seed_cpu(false).unwrap();
    let before = format!("{cpu:?}");
    assert!(psw::CanonicalPswBridge::set_checked(&mut cpu, 0).is_err());
    assert_eq!(format!("{cpu:?}"), before);
    let actual = psw::CanonicalPswBridge::observe_raw(&mut cpu, 0x8000);
    assert_eq!(actual.original_expected, 0x8000);
    assert_eq!(actual.canonical_observed, 0x8cc8);
    assert!(!actual.representable);
    assert!(cpu.cf);
    assert!(!cpu.dd);
    assert_eq!(cpu.scb(), 0);
}
#[test]
fn compiled_actual_source_bindings_are_hashed_and_mutation_refused() {
    let actual = source::verify_source_bindings().unwrap();
    assert_eq!(actual.len(), 11);
    assert_eq!(actual[0].bytes, 5281);
    assert!(source::verify_binding("cpu.rs", "changed", SOURCE_BINDINGS[0].1).is_err());
}
#[test]
fn metadata_refuses_firmware_promotion_and_unknown_fields() {
    let mut entry = serde_json::to_value(entry_fixture()).unwrap();
    entry["firmware_ready"] = serde_json::Value::Bool(true);
    assert!(serde_json::from_value::<SyntheticCpuEntrySnapshot>(entry).is_err());
}

#[test]
fn component_evidence_receipt() {
    use serde_json::{json, Value};
    fn label(id: &str) -> &str {
        match id {
            "ProgramOutOfRange" => "PROGRAM out-of-range",
            "ProgramDataConfusion" => "PROGRAM/DATA confusion",
            "FakePadding" => "Fake padding",
            "WrongBase" => "Wrong base",
            "WrongSha" => "Wrong SHA",
            "WrongNodeIdentity" => "Wrong node identity",
            "WrongFormId" => "Wrong FormId",
            "UnsupportedMnemonic" => "Unsupported mnemonic admitted",
            "DirectJTargetSwapped" => "Direct J target swapped",
            "MissingEntryField" => "Missing entry field",
            "IncompletePointingBanks" => "Incomplete pointing banks",
            "WrongRegisterAlias" => "Wrong register alias",
            "UnauthorizedDataRead" => "Unauthorized DATA read",
            "UnauthorizedDataWrite" => "Unauthorized DATA write",
            "WrongWidth" => "Wrong width",
            "WrongLe16" => "Wrong LE16",
            "SameValueWriteDeduplication" => "Same-value write deduplication",
            "RmwWriteWithoutRead" => "RMW write without read",
            "DiagnosticReadMixedIntoFunctionalJournal" => {
                "Diagnostic read mixed into functional journal"
            }
            "DecoderLookaheadMislabeledAsRetired" => "Decoder lookahead mislabeled as retired",
            "OutOfRangePeekNotZero" => "Out-of-range peek returns zero",
            "ExtraProgramReadAfterExit" => "Extra PROGRAM read after exit",
            "ZeroStepExitAccepted" => "Zero-step exit accepted",
            "MultipleDirectJ" => "Multiple direct J",
            "IncompatiblePswSilentlyNormalized" => "Incompatible PSW silently normalized",
            "OtherPswOverwritesCf" => "OtherPSW overwrites CF",
            "WrongScb" => "Wrong SCB",
            "SfSilentlyDefaulted" => "SF silently defaulted",
            "MissingSfIndependenceEvidence" => "Missing SF independence evidence",
            "SourceMismatch" => "Source mismatch",
            "ActualM2bjStreamShapeAdmission" => "Actual M2bj bytes accidentally admitted",
            "OriginalRomAdmission" => "Original ROM admitted",
            "FirmwareReadyPromotion" => "FirmwareReady promotion",
            _ => id,
        }
    }
    fn refused<T>(
        cases: &mut Vec<Value>,
        category: &str,
        operation: &str,
        result: Result<T>,
        metadata: bool,
    ) {
        let error = result.err();
        cases.push(json!({"id":category,"category":label(category),"operation":operation,"input":operation,"kind":"NegativeRefusal",
            "evidence_level":if metadata {"MetadataPolicyRuntimeObserved"} else {"ComponentRuntimeObserved"},
            "passed":error.is_some(),"error":error,"observed":Value::Null}));
    }
    fn invariant(
        cases: &mut Vec<Value>,
        category: &str,
        operation: &str,
        passed: bool,
        observed: Value,
    ) {
        cases.push(json!({"id":category,"category":label(category),"operation":operation,"kind":"PositiveInvariant",
            "evidence_level":"ComponentRuntimeObserved","passed":passed,"error":Value::Null,"observed":observed}));
    }
    fn deserialize_entry(value: Value) -> Result<SyntheticCpuEntrySnapshot> {
        serde_json::from_value(value)
            .map_err(|e| AdapterError::new("MissingOrUnknownEntryField", e.to_string()))
    }
    let mut cases = vec![];
    let segment = SyntheticProgramSegment::new(descriptor(), cells()).unwrap();
    refused(
        &mut cases,
        "ProgramOutOfRange",
        "opaque translate1000-1",
        segment.translate(0xfff),
        false,
    );
    refused(
        &mut cases,
        "ProgramDataConfusion",
        "opaque PROGRAM read at DATA0196",
        segment.read_opaque(0x196),
        false,
    );
    let mut bad = descriptor();
    bad.padding = 4096;
    refused(
        &mut cases,
        "FakePadding",
        "segment construction with4096prefix",
        SyntheticProgramSegment::new(bad, cells()),
        true,
    );
    let mut bad = descriptor();
    bad.base = 0;
    refused(
        &mut cases,
        "WrongBase",
        "segment base0000",
        SyntheticProgramSegment::new(bad, cells()),
        true,
    );
    refused(
        &mut cases,
        "WrongSha",
        "invented microcontent wrongdigest",
        MicroProgram::new(
            "sllb-a-preserve-zf",
            FormId::SllbA,
            &[0x53],
            &[],
            "wrong",
            INVENTED_PROVENANCE,
        ),
        false,
    );
    let mut node = ClosedFormAdmission::inventory()[0].clone();
    node.node_identity = "fake".into();
    refused(
        &mut cases,
        "WrongNodeIdentity",
        "closed-node admission",
        ClosedFormAdmission::admit(&node, false),
        true,
    );
    refused(
        &mut cases,
        "WrongFormId",
        "invented fixture typedform substitution",
        MicroProgram::new(
            "sllb-a-preserve-zf",
            FormId::StbAPage,
            &[0x53],
            &[],
            &sha256::digest(&[0x53]),
            INVENTED_PROVENANCE,
        ),
        true,
    );
    let index = FULL_OPCODES
        .iter()
        .position(|p| p.mnemonic == "SLLB A")
        .unwrap();
    let decoded = Decoded {
        index,
        mnemonic: "RT",
        len: 1,
        fields: Fields::default(),
        dd_after: None,
        cycles: 2,
    };
    refused(
        &mut cases,
        "UnsupportedMnemonic",
        "typed decoded identity RT substitution",
        FormId::SllbA.validate_decoded(&decoded, false),
        true,
    );
    refused(
        &mut cases,
        "DirectJTargetSwapped",
        "bound invented directJ55C5 bytes changed to5596",
        MicroProgram::new(
            "direct-j-55c5",
            FormId::JAddress,
            &[3, 0x96, 0x55],
            &[],
            &sha256::digest(&[3, 0x96, 0x55]),
            INVENTED_PROVENANCE,
        ),
        false,
    );
    let mut value = serde_json::to_value(entry_fixture()).unwrap();
    value.as_object_mut().unwrap().remove("ssp");
    refused(
        &mut cases,
        "MissingEntryField",
        "deserialize missingSSP",
        deserialize_entry(value),
        true,
    );
    let mut value = serde_json::to_value(entry_fixture()).unwrap();
    value["pointing_banks"].as_array_mut().unwrap().pop();
    refused(
        &mut cases,
        "IncompletePointingBanks",
        "deserialize sevenbanks",
        deserialize_entry(value),
        true,
    );
    let mut entry = entry_fixture();
    entry.local_er[0] ^= 1;
    refused(
        &mut cases,
        "WrongRegisterAlias",
        "entry er0/r0/r1 coherence",
        entry.validate(&seeds()),
        true,
    );
    refused(
        &mut cases,
        "UnauthorizedDataRead",
        "pathB suppressed DATA0124",
        policy(DataPath::B).read(0x1000, 0x124, 8),
        false,
    );
    refused(
        &mut cases,
        "UnauthorizedDataWrite",
        "read-only DATA0196",
        policy(DataPath::D).write(0x1000, 0x196, 8, 1, WriteKind::Store),
        false,
    );
    refused(
        &mut cases,
        "WrongWidth",
        "overlapping word at0197",
        policy(DataPath::D).read(0x1000, 0x197, 16),
        false,
    );
    let mut data = policy(DataPath::D);
    data.read(0x1000, 0x196, 16).unwrap();
    data.raw_journal.swap(0, 1);
    refused(
        &mut cases,
        "WrongLe16",
        "validate tampered actualraw low/high acquisitionorder",
        data.validate_journals(),
        false,
    );
    let mut data = policy(DataPath::D);
    data.read(0x1000, 0x196, 16).unwrap();
    data.journal[0].address = u16::MAX;
    data.raw_journal[0].address = u16::MAX;
    refused(
        &mut cases,
        "DataJournalAddressOverflow",
        "tampered actual LE16 addressFFFF gives controlled refusal, not panic",
        data.validate_journals(),
        false,
    );
    let mut data = policy(DataPath::A);
    for _ in 0..2 {
        data.write(0x1000, 0x18f, 8, 0x8f, WriteKind::Store)
            .unwrap();
    }
    data.journal.pop();
    refused(
        &mut cases,
        "SameValueWriteDeduplication",
        "validate missing actualsamevaluewrite against writecounter/rawledger",
        data.validate_journals(),
        false,
    );
    refused(
        &mut cases,
        "RmwWriteWithoutRead",
        "RMW firstfunctionaloperation",
        policy(DataPath::D).write(0x1000, 0x18e, 8, 0, WriteKind::RMW),
        false,
    );
    let mut data = policy(DataPath::D);
    data.read(0x1000, 0x18e, 8).unwrap();
    data.journal[0].phase = "DiagnosticSnapshotRead".into();
    refused(
        &mut cases,
        "DiagnosticReadMixedIntoFunctionalJournal",
        "validate corruptedactualjournal phase",
        data.validate_journals(),
        false,
    );
    let program = micro();
    let observer = OrderedProgramFetchObserver::new();
    observer.read(&program, 0x1000, "DecoderProbe").unwrap();
    observer.read(&program, 0x1001, "DecoderProbe").unwrap();
    observer.classify_decoder_lookahead(1).unwrap();
    let events = observer.events();
    invariant(
        &mut cases,
        "DecoderLookaheadNotRetired",
        "actual probe beyondselectedextent retains acquisitionpurpose",
        events[1].purpose == "DecoderLookahead" && events[1].acquired_purpose == "DecoderProbe",
        json!(events),
    );
    let observer = OrderedProgramFetchObserver::new();
    observer.read(&program, 0x1000, "DecoderProbe").unwrap();
    observer.read(&program, 0x1001, "DecoderProbe").unwrap();
    observer.classify_decoder_lookahead(6).unwrap();
    refused(
        &mut cases,
        "DecoderLookaheadMislabeledAsRetired",
        "attempt expand selectedextent over explicitguard bytes",
        observer.read_selected(&program, 6),
        false,
    );
    let observer = OrderedProgramFetchObserver::new();
    let error = observer.read(&program, 0x1006, "DecoderProbe");
    refused(
        &mut cases,
        "OutOfRangePeekNotZero",
        "actual observer attempt nofallback",
        error,
        false,
    );
    invariant(
        &mut cases,
        "FaultAttemptHasNoSuccessfulByte",
        "inspect actual failedPROGRAMevent",
        observer.events()[0].value.is_none(),
        json!(observer.events()),
    );
    let truncated = MicroProgram::truncated_decoder_probe_fixture();
    let decoder_observer = OrderedProgramFetchObserver::new();
    let decoder_failure = decoder_observer.decode_checked(&truncated, false);
    refused(
        &mut cases,
        "ProductionDecoderOutOfRangeSentinel",
        "actual productiondecoder C4-only invented truncatedacquisition, noexecution",
        decoder_failure,
        false,
    );
    let decoder_events = decoder_observer.events();
    invariant(
        &mut cases,
        "ProductionDecoderFaultHasNoFallbackByte",
        "actual catch of typedcheckedfetchabort",
        decoder_events
            .last()
            .is_some_and(|e| e.fault.is_some() && e.value.is_none()),
        json!(decoder_events),
    );
    let observer = OrderedProgramFetchObserver::new();
    observer.seal_after_retirement();
    refused(
        &mut cases,
        "ExtraProgramReadAfterExit",
        "actual read attempt aftersealedretirement",
        observer.read(&program, 0x55c5, "DecoderProbe"),
        false,
    );
    let trap = SyntheticExternalExitTrap::new(0x1000, 1).unwrap();
    refused(
        &mut cases,
        "ZeroStepExitAccepted",
        "external exit claim beforeanyretirement",
        trap.require_external_exit(0x55c5),
        false,
    );
    let mut trap = SyntheticExternalExitTrap::new(0x1000, 1).unwrap();
    trap.record_retirement(0x1000, 0x55c5, FormId::JAddress)
        .unwrap();
    refused(
        &mut cases,
        "MultipleDirectJ",
        "second trapstate retirementtransition (noCPUinstruction)",
        trap.record_retirement(0x1000, 0x5596, FormId::JAddress),
        false,
    );
    let entry = entry_fixture();
    let mut cpu = entry.seed_cpu(false).unwrap();
    let cpu_before = format!("{cpu:?}");
    refused(
        &mut cases,
        "IncompatiblePswSilentlyNormalized",
        "actual canonicalbridge refuses0000",
        psw::CanonicalPswBridge::set_checked(&mut cpu, 0),
        false,
    );
    invariant(
        &mut cases,
        "IncompatiblePswRefusalIsAtomic",
        "actual unchangedCpu completeDebugstate",
        format!("{cpu:?}") == cpu_before,
        json!({"before":cpu_before,"after":format!("{cpu:?}")}),
    );
    let mut entry = entry_fixture();
    entry.other_psw |= 0x8000;
    refused(
        &mut cases,
        "OtherPswOverwritesCf",
        "entry namedflag separation",
        entry.validate(&seeds()),
        true,
    );
    let mut entry = entry_fixture();
    entry.scb = 0;
    refused(
        &mut cases,
        "WrongScb",
        "entry SCB/PSWlow3 coherence",
        entry.validate(&seeds()),
        true,
    );
    let mut sf = entry_fixture().sf;
    sf.value = Some(false);
    refused(
        &mut cases,
        "SfSilentlyDefaulted",
        "opaque architecturalSF boolean prohibited",
        sf.validate(),
        true,
    );
    refused(
        &mut cases,
        "MissingSfIndependenceEvidence",
        "empty actualobservedpair set",
        sf::require_observed_pairs(&[]),
        true,
    );
    refused(
        &mut cases,
        "SourceMismatch",
        "actualsha of changedsourcebytes vs fixedpin",
        source::verify_binding("cpu.rs", "changed", SOURCE_BINDINGS[0].1),
        false,
    );
    refused(
        &mut cases,
        "ActualM2bjStreamShapeAdmission",
        "all51-byte inputs refused beforecontenthash; inventedcanary witness",
        MicroProgram::new(
            "sllb-a-preserve-zf",
            FormId::SllbA,
            &[0xa5; 51],
            &[],
            UPSTREAM_DIGEST,
            INVENTED_PROVENANCE,
        ),
        false,
    );
    refused(
        &mut cases,
        "OriginalRomAdmission",
        "noROMprovenance orloader permitted",
        MicroProgram::new(
            "ROM",
            FormId::SllbA,
            &[0x53],
            &[],
            &sha256::digest(&[0x53]),
            "OriginalROM",
        ),
        true,
    );
    let mut value = serde_json::to_value(entry_fixture()).unwrap();
    value["firmware_ready"] = json!(true);
    refused(
        &mut cases,
        "FirmwareReadyPromotion",
        "denyunknown architecturalentry field",
        deserialize_entry(value),
        true,
    );
    let mut data = policy(DataPath::D);
    data.write(0x1000, 0x18e, 8, 0, WriteKind::RMW).unwrap_err();
    let count = data.journal.len();
    let after_fault = data.read(0x1000, 0x18e, 8);
    refused(
        &mut cases,
        "DataJournalAfterFault",
        "latchedfault blocks furtherfunctionalread",
        after_fault,
        false,
    );
    invariant(
        &mut cases,
        "FaultPreservesJournalPrefix",
        "journal unchanged afterlatchedfault",
        data.journal.len() == count,
        json!(data.journal),
    );
    let mut data = policy(DataPath::A);
    data.write(0x1000, 0x18f, 8, 0x8f, WriteKind::Store)
        .unwrap();
    data.write(0x1000, 0x18f, 8, 0x8f, WriteKind::Store)
        .unwrap();
    data.validate_journals().unwrap();
    invariant(
        &mut cases,
        "SameValueWritesHaveFreshOrdinals",
        "two actual componentwrites",
        data.journal
            .iter()
            .map(|e| e.write_ordinal)
            .collect::<Vec<_>>()
            == [Some(1), Some(2)],
        json!(data.journal),
    );
    let mapping:Vec<_>=(0..51).map(|n|json!({"pc":0x1000+n,"offset":segment.translate(0x1000+n).unwrap(),"opaque":segment.read_opaque(0x1000+n).unwrap()})).collect();
    let mut entry_snapshots = vec![];
    for scb in 0..8 {
        let mut entry = entry_fixture();
        entry.scb = scb;
        entry.psw = (entry.psw & !7) | scb;
        entry.other_psw = entry.psw & 0xfff;
        entry.validate(&seeds()).unwrap();
        let cpu = entry.seed_cpu(true).unwrap();
        let mut data = IndependentDataAccessPolicy::new(DataPath::D, &seeds()).unwrap();
        entry.seed_banks(&mut data).unwrap();
        let actual = entry.snapshot(&cpu, &mut data).unwrap();
        let preserved = actual == entry;
        entry_snapshots.push(json!({"scb":scb,"snapshot":actual,"preserved":preserved,"actual_cpu_instructions":cpu.instructions,"functional_events":data.journal.len()}));
        assert!(preserved);
    }
    let source_bindings = source::verify_source_bindings().unwrap();
    let admission_inventory = ClosedFormAdmission::inventory();
    ClosedFormAdmission::validate_inventory(&admission_inventory).unwrap();
    let mut permission_matrix = vec![];
    for path in [DataPath::A, DataPath::B, DataPath::C, DataPath::D] {
        for address in INVENTORY {
            for width in [8, 16] {
                permission_matrix.push(json!({"path":path,"address":address,"width":width,
                "read_allowed":IndependentDataAccessPolicy::read_permission(path,address,width),
                "write_allowed":IndependentDataAccessPolicy::write_permission(path,address,width),
                "write_kind":if width==8 {IndependentDataAccessPolicy::allowed_write_kind(path,address)}else{None}}));
            }
        }
    }
    let all_passed = cases.iter().all(|record| record["passed"] == json!(true));
    let receipt = json!({"schema_version":1,"classification":"ActualRustComponentRuntimeObserved_NoInstructionExecution",
        "cases":cases,"source_bindings":source_bindings,"mapping":mapping,"entry_snapshots":entry_snapshots,
        "admission_inventory":admission_inventory,"permission_matrix":permission_matrix,
        "instruction_executions":0,"component_cpu_instances":9,"decoder_only_calls":1,"m2bj_composite_executions":0,"original_rom_executions":0,"first_mismatch":if all_passed {Value::Null}else{json!("component case failure")}});
    println!(
        "\nM2BM_COMPONENT_JSON={}",
        serde_json::to_string(&receipt).unwrap()
    );
    assert!(all_passed, "component receipt contains failed real check");
}
