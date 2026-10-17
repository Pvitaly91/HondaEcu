//! Pure pre-execution boundary. No Cpu or Bus is constructed here.
use crate::{ProductionProbeRequest, Result, LOGICAL_PC, PHYSICAL_PC, SCRATCH};
use p28_research_synthetic_adapter::{
    data::INVENTORY, executor::validate_selected_fields, program::MicroProgram,
    psw::CanonicalPswBridge, sha256, AdapterError,
};
use p28_slice_runner::decoder::{decode, Decoded};
use serde::Serialize;
use std::cell::Cell;

pub struct AdmittedProbe {
    pub program: Vec<u8>,
    pub preflight: Decoded,
}

pub fn admit(request: &ProductionProbeRequest) -> Result<AdmittedProbe> {
    if request.case_id.is_empty()
        || request.case_id.len() > 160
        || request.family.is_empty()
        || request.family.len() > 96
        || !request
            .case_id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"-_.:/".contains(&b))
        || !request
            .family
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"-_".contains(&b))
    {
        return Err(AdapterError::new(
            "InvalidCaseIdentity",
            "bounded invented case/family",
        ));
    }
    if request.physical_entry_pc != PHYSICAL_PC
        || request.entry.pc != LOGICAL_PC
        || request.scratch != SCRATCH
        || request.budget != 1
    {
        return Err(AdapterError::new(
            "WrongOneStepScope",
            "physical PC0/logical PC1000/explicit A5 scratch/exact budget1",
        ));
    }
    if request.data.len() != INVENTORY.len()
        || INVENTORY
            .iter()
            .any(|address| !request.data.contains_key(address))
    {
        return Err(AdapterError::new(
            "IncompleteDataInventory",
            "exact sixteen DATA bytes",
        ));
    }
    request.entry.validate(&request.data)?;
    if request.form.spec().dd == '0' && request.entry.dd {
        return Err(AdapterError::new("WrongDdAdmission", "DD0-only exact form"));
    }
    if request.bytes.len() + request.guards.len() != 6 {
        return Err(AdapterError::new(
            "WrongGuardGeometry",
            "one sealed instruction plus explicit guards totals six bytes",
        ));
    }
    // This unchanged M2bm helper binds only literal invented fixtures and guards.
    // No old research executor or its instruction effects are called.
    let program = MicroProgram::new(
        &request.fixture_id,
        request.form,
        &request.bytes,
        &request.guards,
        &request.content_digest,
        &request.entry.provenance,
    )?;
    let content = program.content().to_vec();
    let outside = Cell::new(None);
    // Separate strict preflight, NOT an observation of callbacks inside step.
    let preflight = decode(request.entry.dd, |offset| match content.get(offset) {
        Some(value) => *value,
        None => {
            outside.set(Some(offset));
            0
        }
    });
    if let Some(offset) = outside.get() {
        return Err(AdapterError::new(
            "PreflightProbeOutOfBounds",
            offset.to_string(),
        ));
    }
    let preflight =
        preflight.ok_or_else(|| AdapterError::new("PreflightUndefined", "sealed exact form"))?;
    request
        .form
        .validate_decoded(&preflight, request.entry.dd)?;
    validate_selected_fields(request.form, &preflight, &request.bytes)?;
    if preflight.len != request.bytes.len() || preflight.len != request.expected_length {
        return Err(AdapterError::new(
            "WrongInstructionLength",
            "selected sealed extent",
        ));
    }
    if preflight.index != request.expected_decoded_index {
        return Err(AdapterError::new(
            "WrongExpectedDecodedIndex",
            "independently frozen form identity",
        ));
    }
    Ok(AdmittedProbe {
        program: content,
        preflight,
    })
}

#[derive(Debug, Serialize)]
pub struct AdmissionSummary {
    pub kind: &'static str,
    pub inputs: u64,
    pub representable: u64,
    pub incompatible: u64,
    pub low12_representable: u64,
    pub low12_incompatible: u64,
    pub classification_record_encoding: &'static str,
    pub classification_sha256: String,
    pub cpu_instances: u64,
    pub bus_instances: u64,
    pub production_step_calls: u64,
    pub caller_request_unchanged: bool,
}

pub fn admission_sweep(template: &ProductionProbeRequest) -> Result<AdmissionSummary> {
    admit(template)?;
    let before = serde_json::to_vec(template)
        .map_err(|e| AdapterError::new("SerializeRequest", e.to_string()))?;
    let mut records = Vec::with_capacity(65536 * 3);
    let mut representable = 0;
    let mut low12_representable = 0;
    for input in 0_u32..=65535 {
        let input = input as u16;
        let mut request = template.clone();
        request.entry.psw = input;
        request.entry.cf = input & 0x8000 != 0;
        request.entry.zf = input & 0x4000 != 0;
        request.entry.hc = input & 0x2000 != 0;
        request.entry.dd = input & 0x1000 != 0;
        request.entry.other_psw = input & 0x0fff;
        request.entry.scb = input & 7;
        // Scope-neutral admission fixture accepts both DD values. The full
        // admission function, not merely the mathematical mask, is exercised.
        let observed = admit(&request);
        let expected = CanonicalPswBridge::is_representable(input);
        match observed {
            Ok(_) if expected => {}
            Err(error)
                if !expected && error.code == "NotRepresentableByCurrentCanonicalRustCpu" => {}
            other => {
                return Err(AdapterError::new(
                    "AdmissionSweepMismatch",
                    format!(
                        "{input:04X}: {}",
                        match other {
                            Ok(_) => "unexpected admission".into(),
                            Err(e) => e.to_string(),
                        }
                    ),
                ))
            }
        }
        representable += u64::from(expected);
        if input < 4096 {
            low12_representable += u64::from(expected);
        }
        records.extend_from_slice(&input.to_le_bytes());
        records.push(u8::from(expected));
    }
    let after = serde_json::to_vec(template)
        .map_err(|e| AdapterError::new("SerializeRequest", e.to_string()))?;
    if before != after || representable != 2048 || low12_representable != 128 {
        return Err(AdapterError::new(
            "AdmissionSweepInvariant",
            "complete classification/caller identity",
        ));
    }
    Ok(AdmissionSummary {
        kind: "admission_summary",
        inputs: 65536,
        representable,
        incompatible: 65536 - representable,
        low12_representable,
        low12_incompatible: 4096 - low12_representable,
        classification_record_encoding:
            "ForU16Ascending_ThreeBytes_LittleEndianInputThenAdmitted0or1",
        classification_sha256: sha256::digest(&records),
        cpu_instances: 0,
        bus_instances: 0,
        production_step_calls: 0,
        caller_request_unchanged: true,
    })
}
