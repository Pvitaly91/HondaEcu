//! Bounded streaming harness. stdin only, no ROM/filename/target-payload interface.
use p28_research_synthetic_adapter::{
    psw::CanonicalPswBridge, source::verify_source_bindings, UPSTREAM_DIGEST,
};
use p28_research_synthetic_composite::{
    component_checks::run_component_checks,
    execution::{admit_case, execute_composite, CaseRequest},
    program::{EmissionRequest, VerifiedComposite},
    verify_effect_copy,
};
use serde_json::{json, Value};
use std::{
    io::{self, BufRead, Write},
    process::ExitCode,
};

fn write_record(out: &mut impl Write, record: &impl serde::Serialize) -> Result<(), String> {
    serde_json::to_writer(&mut *out, record).map_err(|e| e.to_string())?;
    out.write_all(b"\n").map_err(|e| e.to_string())?;
    out.flush().map_err(|e| e.to_string())
}
fn run() -> Result<(), String> {
    if std::env::args_os().count() != 1 {
        return Err("No CLI arguments or filename interfaces are admitted".into());
    }
    verify_effect_copy().map_err(|e| e.to_string())?;
    let bindings = verify_source_bindings().map_err(|e| e.to_string())?;
    let stdin = io::stdin();
    let mut input = stdin.lock();
    let stdout = io::stdout();
    let mut output = io::BufWriter::new(stdout.lock());
    let mut line = String::new();
    let mut program: Option<VerifiedComposite> = None;
    let mut emission: Option<EmissionRequest> = None;
    let mut cases = 0u64;
    let mut cpu_instances = 0u64;
    let mut retired = 0u64;
    let mut accepted = 0u64;
    let mut refused = 0u64;
    let mut sweeps = 0u64;
    let mut finished = false;
    loop {
        line.clear();
        if input.read_line(&mut line).map_err(|e| e.to_string())? == 0 {
            break;
        }
        if line.len() > 262_144 {
            return Err("Bounded request line exceeds 256 KiB".into());
        }
        let value: Value = serde_json::from_str(&line).map_err(|e| e.to_string())?;
        let kind = value
            .get("kind")
            .and_then(Value::as_str)
            .ok_or("explicit kind required")?;
        match kind {
            "program" => {
                if program.is_some() || cases != 0 || sweeps != 0 {
                    return Err("Program can be admitted exactly once before execution".into());
                }
                let request: EmissionRequest =
                    serde_json::from_value(value).map_err(|e| e.to_string())?;
                let checked = VerifiedComposite::admit_verified_m2bj_emission(&request)
                    .map_err(|e| e.to_string())?;
                program = Some(checked);
                emission = Some(request);
                write_record(
                    &mut output,
                    &json!({"kind":"program_admitted", "base":4096,
                    "end_exclusive":4147, "length":51, "nodes":20, "forms":16,
                    "actual_content_sha256":UPSTREAM_DIGEST, "full_bytes_verified_in_memory":true,
                    "program_byte_values_persisted":false, "effect_body_identical":true,
                    "source_bindings":bindings}),
                )?;
            }
            "case" => {
                let checked = program
                    .as_ref()
                    .ok_or("M2bj program must be admitted first")?;
                let request: CaseRequest =
                    serde_json::from_value(value).map_err(|e| e.to_string())?;
                cases += 1;
                match execute_composite(checked, &request) {
                    Ok(observation) => {
                        cpu_instances += u64::from(observation.cpu_instances);
                        retired += u64::from(observation.retired_instructions);
                        if observation.accepted {
                            accepted += 1;
                        } else {
                            refused += 1;
                        }
                        write_record(&mut output, &observation)?;
                    }
                    Err(error) => {
                        refused += 1;
                        write_record(
                            &mut output,
                            &json!({"kind":"refusal", "case_id":request.case_id,
                            "classification":"AdmissionRefusal", "error":error,
                            "cpu_instances":0, "instruction_retirements":0,
                            "functional_data_writes":0, "program_execution_fetches":0}),
                        )?;
                    }
                }
            }
            "admission_sweep" => {
                if sweeps != 0 || cases != 0 || program.is_none() {
                    return Err("One admission sweep before cases".into());
                }
                let template: CaseRequest = serde_json::from_value(
                    value
                        .get("template")
                        .cloned()
                        .ok_or("explicit template required")?,
                )
                .map_err(|e| e.to_string())?;
                admit_case(&template).map_err(|e| e.to_string())?;
                let mut compatible = 0u32;
                for candidate in 0..=u16::MAX {
                    let mut request = template.clone();
                    request.entry.psw = candidate;
                    request.entry.other_psw = candidate & 0xfff;
                    request.entry.scb = candidate & 7;
                    request.entry.cf = candidate & 0x8000 != 0;
                    request.entry.zf = candidate & 0x4000 != 0;
                    request.entry.hc = candidate & 0x2000 != 0;
                    request.entry.dd = candidate & 0x1000 != 0;
                    // No Cpu is constructed and no memory execution API is called.
                    let result = admit_case(&request);
                    let admitted = result.is_ok();
                    if admitted != CanonicalPswBridge::is_representable(candidate) {
                        return Err(format!("Admission classification mismatch {candidate:04X}"));
                    }
                    if admitted {
                        compatible += 1;
                    }
                    write_record(
                        &mut output,
                        &json!({"kind":"admission", "psw":candidate,
                        "admitted":admitted, "error":result.err(), "cpu_instances":0,
                        "instruction_retirements":0, "functional_data_writes":0,
                        "program_execution_fetches":0}),
                    )?;
                }
                sweeps += 1;
                write_record(
                    &mut output,
                    &json!({"kind":"admission_summary", "candidates":65536,
                    "representable":compatible, "incompatible":65536-compatible,
                    "low12_representable":compatible/16, "low12_incompatible":4096-compatible/16,
                    "cpu_instances":0, "instruction_retirements":0,
                    "functional_data_writes":0, "program_execution_fetches":0}),
                )?;
            }
            "component_checks" => {
                let checked = program.as_ref().ok_or("M2bj program first")?;
                let request: CaseRequest = serde_json::from_value(
                    value
                        .get("template")
                        .cloned()
                        .ok_or("explicit template required")?,
                )
                .map_err(|e| e.to_string())?;
                let original = emission.as_ref().ok_or("original emission admission")?;
                let receipt =
                    run_component_checks(checked, original, &request).map_err(|e| e.to_string())?;
                write_record(&mut output, &receipt)?;
            }
            "finish" => {
                if program.is_none() || cases == 0 || sweeps != 1 {
                    return Err(
                        "Actual program/admission sweep/cases required before finish".into(),
                    );
                }
                write_record(
                    &mut output,
                    &json!({"kind":"run_summary", "cases":cases,
                    "accepted":accepted, "refused":refused, "cpu_instances":cpu_instances,
                    "retired_instructions":retired, "admission_sweeps":sweeps,
                    "actual_rom_executions":0, "native_downstream_executions":0,
                    "production_exec_integrated":false, "firmware_ready":false}),
                )?;
                finished = true;
                break;
            }
            _ => return Err(format!("Unknown bounded harness command {kind}")),
        }
    }
    if !finished {
        return Err("Missing explicit finish command".into());
    }
    Ok(())
}
fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("M2bn harness refused: {error}");
            ExitCode::FAILURE
        }
    }
}
