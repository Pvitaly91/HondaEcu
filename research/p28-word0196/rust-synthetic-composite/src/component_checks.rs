//! Actual boundary/component refusals, never pre-authored JSON pass flags.
//! Mutated bytes are admission negatives only and never reach Cpu execution.
use crate::{
    execution::{admit_case, execute_composite, CaseRequest},
    lifecycle::Lifecycle,
    observer::ProgramObserver,
    program::{EmissionRequest, VerifiedComposite},
    AdapterError, Result, BASE,
};
use p28_research_synthetic_adapter::{
    data::{DataPath, IndependentDataAccessPolicy, WriteKind},
    FormId,
};
use serde_json::{json, Value};

fn refused<T>(id: &str, class: &str, result: Result<T>, expected: &str) -> Result<Value> {
    match result {
        Err(error) if error.code == expected => Ok(json!({"id":id, "classification":class,
            "actual_error":error, "expected_error":expected, "passed":true})),
        Err(error) => Err(AdapterError::new(
            "NegativeCheckUnexpectedRefusal",
            format!("{id}: expected {expected}, actual {}", error.code),
        )),
        Ok(_) => Err(AdapterError::new("NegativeCheckUnexpectedAdmission", id)),
    }
}
fn data_context(template: &CaseRequest, path: DataPath) -> Result<IndependentDataAccessPolicy> {
    let mut data = IndependentDataAccessPolicy::new(path, &template.data)?;
    template.entry.seed_banks(&mut data)?;
    data.begin_functional()?;
    Ok(data)
}
pub fn run_component_checks(
    program: &VerifiedComposite,
    emission: &EmissionRequest,
    template: &CaseRequest,
) -> Result<Value> {
    admit_case(template)?;
    let mut results = Vec::new();
    let admission = "AdmissionRefusal";
    let access = "RuntimeAccessRefusal";
    macro_rules! program_negative {
        ($id:expr, $field:ident, $value:expr, $code:expr) => {{
            let mut request = emission.clone();
            request.$field = $value;
            results.push(refused(
                $id,
                admission,
                VerifiedComposite::admit_verified_m2bj_emission(&request),
                $code,
            )?);
        }};
    }
    program_negative!(
        "wrong-content-label",
        content_digest,
        "0".repeat(64),
        "WrongCompositeSha"
    );
    program_negative!("wrong-base", base, 0x1001, "WrongProgramMapping");
    program_negative!("wrong-end", end_exclusive, 0x1034, "WrongProgramMapping");
    program_negative!(
        "wrong-length",
        bytes,
        emission.bytes[..50].to_vec(),
        "WrongProgramLength"
    );
    program_negative!(
        "wrong-provenance",
        provenance,
        "HistoricalOriginalRomObservations".into(),
        "WrongEmissionProvenance"
    );
    program_negative!(
        "arbitrary-stream-source",
        source,
        "ArbitraryInstructionStream".into(),
        "WrongEmissionProvenance"
    );
    program_negative!(
        "original-rom-source",
        source,
        "OriginalROM".into(),
        "WrongEmissionProvenance"
    );
    let mut changed = emission.clone();
    changed.bytes[0] ^= 1;
    results.push(refused(
        "actual-content-byte-mutation",
        admission,
        VerifiedComposite::admit_verified_m2bj_emission(&changed),
        "WrongCompositeSha",
    )?);
    for (id, mutation) in ["node", "form", "operand", "successor", "swapped-J"]
        .into_iter()
        .enumerate()
    {
        let mut changed = emission.clone();
        match id {
            0 => changed.nodes[0].node_identity = "OtherNode".into(),
            1 => changed.nodes[0].form = FormId::LbAImm8,
            2 => changed.nodes[0].operands.pop().map(|_| ()).unwrap_or(()),
            3 => changed.nodes[0].successors = vec![0x1001],
            _ => changed.nodes[15].successors = vec![0x55c5],
        }
        results.push(refused(
            mutation,
            admission,
            VerifiedComposite::admit_verified_m2bj_emission(&changed),
            "ClosedInventoryMismatch",
        )?);
    }
    let mut incompatible = template.clone();
    incompatible.entry.psw &= !0x0008;
    incompatible.entry.other_psw &= !0x0008;
    results.push(refused(
        "unsupported-PSW",
        admission,
        admit_case(&incompatible),
        "NotRepresentableByCurrentCanonicalRustCpu",
    )?);
    for n in 0..5 {
        let mut changed = template.clone();
        match n {
            0 => changed.entry.cf = !changed.entry.cf,
            1 => changed.entry.other_psw ^= 1,
            2 => changed.entry.scb ^= 1,
            3 => changed.entry.ah ^= 1,
            _ => changed.entry.al ^= 1,
        }
        results.push(refused(
            &format!("conflicting-alias-{n}"),
            admission,
            admit_case(&changed),
            "ConflictingCpuAliases",
        )?);
    }
    let mut changed = template.clone();
    changed.entry.local_r[0] ^= 1;
    results.push(refused(
        "local-RAM-alias",
        admission,
        admit_case(&changed),
        "ConflictingLocalAliases",
    )?);
    let mut changed = template.clone();
    changed.entry.local_er[0] ^= 1;
    results.push(refused(
        "r-er-alias",
        admission,
        admit_case(&changed),
        "ConflictingLocalAliases",
    )?);
    let mut changed = template.clone();
    changed.path = match changed.path {
        DataPath::A => DataPath::D,
        _ => DataPath::A,
    };
    results.push(refused(
        "forged-path-profile",
        admission,
        admit_case(&changed),
        "ForgedPermissionProfile",
    )?);
    let mut changed = template.clone();
    changed.entry.sf.value = Some(false);
    results.push(refused(
        "invented-physical-SF",
        admission,
        admit_case(&changed),
        "SfUncertaintyRequired",
    )?);
    let mut changed = template.clone();
    changed.entry.pc = 0x1001;
    results.push(refused(
        "instruction-middle-entry",
        admission,
        admit_case(&changed),
        "InvalidEntryScope",
    )?);
    let mut changed = template.clone();
    changed.entry.pc = 0x5596;
    results.push(refused(
        "zero-step-external-exit",
        admission,
        admit_case(&changed),
        "InvalidEntryScope",
    )?);
    let mut changed = template.clone();
    changed.entry.lrb = 0x22;
    results.push(refused(
        "wrong-LRB",
        admission,
        admit_case(&changed),
        "InvalidEntryScope",
    )?);
    let mut changed = template.clone();
    changed.data.remove(&0x128);
    results.push(refused(
        "missing-DATA-byte",
        admission,
        admit_case(&changed),
        "IncompleteDataInventory",
    )?);
    // Missing fields are actual serde boundary failures, not status checks.
    for (id, container, field) in [
        ("missing-entry", "", "entry"),
        ("missing-pointing-bank", "entry", "pointing_banks"),
        ("missing-SF", "entry", "sf"),
    ] {
        let mut value = serde_json::to_value(template)
            .map_err(|e| AdapterError::new("Serialization", e.to_string()))?;
        if container.is_empty() {
            value.as_object_mut().expect("request").remove(field);
        } else {
            value
                .get_mut(container)
                .and_then(Value::as_object_mut)
                .expect("entry")
                .remove(field);
        }
        let actual = serde_json::from_value::<CaseRequest>(value);
        if actual.is_ok() {
            return Err(AdapterError::new("MissingFieldAccepted", id));
        }
        results.push(
            json!({"id":id, "classification":admission, "actual_error":"SerdeMissingField",
            "expected_error":"SerdeMissingField", "passed":true}),
        );
    }
    let mut data = data_context(template, DataPath::B)?;
    results.push(refused(
        "path-B-short-circuit-read-suppression",
        access,
        data.read(0x1019, 0x124, 8),
        "UnauthorizedDataRead",
    )?);
    let blocked = data.read(0x1000, 0x18e, 8);
    results.push(refused(
        "DATA-after-fault",
        access,
        blocked,
        "UnauthorizedDataRead",
    )?);
    if !data.journal.is_empty() || !data.raw_journal.is_empty() {
        return Err(AdapterError::new(
            "DataAccessAfterFaultObserved",
            "no serviced journal effects expected",
        ));
    }
    let mut data = data_context(template, DataPath::D)?;
    results.push(refused(
        "unknown-DATA-read",
        access,
        data.read(BASE, 0x120, 8),
        "UnauthorizedDataRead",
    )?);
    for address in [0x196, 0x197, 0x128] {
        let mut data = data_context(template, DataPath::D)?;
        results.push(refused(
            &format!("readonly-DATA-write-{address:04X}"),
            access,
            data.write(BASE, address, 8, 1, WriteKind::Store),
            "UnauthorizedDataWrite",
        )?);
    }
    let mut data = data_context(template, DataPath::D)?;
    results.push(refused(
        "RMW-without-preceding-read",
        access,
        data.write(0x1003, 0x18e, 8, 1, WriteKind::RMW),
        "RmwReadRequired",
    )?);
    let mut data = data_context(template, DataPath::D)?;
    results.push(refused(
        "RMW-store-kind-bypass",
        access,
        data.write(0x1003, 0x18e, 8, 1, WriteKind::Store),
        "WrongDataAccessKind",
    )?);
    let observer = ProgramObserver::new();
    observer.begin_instruction(0x1033, 1)?;
    results.push(refused(
        "actual-decoder-out-of-range-probe",
        access,
        observer.decode_checked(program, false),
        "ProgramOutOfRange",
    )?);
    let failed_probes = observer.events();
    if !failed_probes
        .iter()
        .any(|e| !e.serviced && e.address >= 0x1033)
    {
        return Err(AdapterError::new(
            "MissingRefusedProgramAttempt",
            "actual decoder callback",
        ));
    }
    let before = observer.events().iter().filter(|e| e.serviced).count();
    results.push(refused(
        "PROGRAM-after-fault",
        access,
        observer.read(program, 0x1000, "DecoderProbe"),
        "ProgramOutOfRange",
    )?);
    if observer.events().iter().filter(|e| e.serviced).count() != before {
        return Err(AdapterError::new(
            "ProgramServicedAfterFault",
            "fault guard",
        ));
    }
    // Independent lifecycle guard tests do not fetch or instantiate Cpu.
    let mut life = Lifecycle::new(BASE, 16)?;
    results.push(refused(
        "host-PC-assignment-not-J",
        "ObservationIntegrityFailure",
        life.retire(BASE, 0x5596, FormId::LbAPage),
        "UnretiredExternalExit",
    )?);
    results.push(refused(
        "zero-step-J-retirement",
        "ObservationIntegrityFailure",
        life.retire(0x1027, 0x5596, FormId::JAddress),
        "RetirementContinuityFailure",
    )?);
    for (before, after, form) in [
        (0x1000, 0x1002, FormId::LbAPage),
        (0x1002, 0x1003, FormId::SllbA),
        (0x1003, 0x1006, FormId::RolbPage),
        (0x1006, 0x1007, FormId::LbAR0),
        (0x1007, 0x1009, FormId::AndbAPage),
        (0x1009, 0x100e, FormId::CmpPageImm16),
        (0x100e, 0x102a, FormId::JltRel8),
        (0x102a, 0x102c, FormId::LbAImm8),
        (0x102c, 0x102e, FormId::StbAPage),
        (0x102e, 0x1030, FormId::StbAPage),
        (0x1030, 0x55c5, FormId::JAddress),
    ] {
        life.retire(before, after, form)?;
    }
    results.push(refused(
        "lifecycle-after-exit",
        access,
        life.before_fetch(),
        "ExecutionAfterExit",
    )?);
    results.push(refused(
        "second-direct-J",
        "ObservationIntegrityFailure",
        life.retire(0x1030, 0x55c5, FormId::JAddress),
        "ExecutionAfterExit",
    )?);
    let observer = ProgramObserver::new();
    observer.begin_instruction(0x1027, 1)?;
    let decoded = observer.decode_checked(program, false)?;
    observer.associate_selection(decoded.len)?;
    let selected = observer.selected(program, decoded.len)?;
    program.validate_selection(program.node(0x1027)?, &decoded, false, &selected)?;
    observer.finish_retirement(true)?;
    results.push(refused(
        "observer-after-exit-independent-of-lifecycle",
        access,
        observer.read(program, 0x5596, "DecoderProbe"),
        "ProgramAccessAfterExit",
    )?);
    let exit_attempts = observer.events();
    if exit_attempts
        .last()
        .is_none_or(|e| e.serviced || e.refusal.is_none())
    {
        return Err(AdapterError::new(
            "MissingPostExitRefusedAttempt",
            "observer boundary",
        ));
    }
    // One deliberately bounded actual Cpu run demonstrates runtime budget failure.
    let mut budget_case = template.clone();
    budget_case.budget = 1;
    budget_case.case_id = "negative-runtime-budget".into();
    let budget_observation = execute_composite(program, &budget_case)?;
    if budget_observation.accepted
        || budget_observation.retired_instructions != 1
        || budget_observation.instructions != 1
        || budget_observation.cpu_instances != 1
        || budget_observation
            .error
            .as_ref()
            .is_none_or(|e| e.code != "InstructionBudgetExhausted")
    {
        return Err(AdapterError::new(
            "BudgetNegativeFailed",
            "actual Cpu must stop after exactly one LB",
        ));
    }
    results.push(
        json!({"id":"actual-runtime-budget-exhaustion", "classification":"RuntimeAccessRefusal",
        "actual_error":budget_observation.error, "expected_error":"InstructionBudgetExhausted",
        "passed":true}),
    );
    Ok(
        json!({"kind":"component_checks", "passed":true, "checks":results,
        "component_cpu_instances":1, "component_composite_attempts":1,
        "component_instruction_retirements":1, "admission_cpu_instances":0,
        "out_of_range_decoder_events":failed_probes, "post_exit_observer_events":exit_attempts,
        "budget_observation":budget_observation, "actual_rom_executions":0,
        "native_downstream_executions":0, "firmware_ready":false}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn check_refusal_requires_actual_matching_error() {
        assert!(refused::<()>("x", "admission", Ok(()), "X").is_err());
        assert!(
            refused::<()>("x", "admission", Err(AdapterError::new("Y", "actual")), "X").is_err()
        );
        assert!(
            refused::<()>("x", "admission", Err(AdapterError::new("X", "actual")), "X").is_ok()
        );
    }
}
