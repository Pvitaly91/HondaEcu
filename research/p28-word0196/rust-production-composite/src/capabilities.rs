//! M2bq closed negative controls. No copied instruction effects or caller loader.
use super::*;
use p28_slice_runner::audit::{AuditError, CompositeForm, CompositeOperand, InstructionIdentity};
use p28_slice_runner::decoder::Fields;

fn closed_case(path: &str) -> Result<Case, Box<dyn std::error::Error>> {
    let value = closed_inputs()
        .iter()
        .find(|row| row["path"] == path)
        .ok_or("Frozen path control is missing")?;
    // Preserve numeric JSON DATA-key decoding; never use serde_json::from_value.
    Ok(serde_json::from_slice(&serde_json::to_vec(value)?)?)
}
fn seeds(request: &Case) -> audit::Result<CompositeSeeds> {
    let banks = std::array::from_fn(|index| {
        let bank = &request.entry.pointing_banks[index];
        [bank.x1, bank.x2, bank.dp, bank.usp]
    });
    CompositeSeeds::new(
        request.data.clone(),
        banks,
        request.entry.local_r,
        request.entry.local_er,
    )
}
fn admission<T>(
    id: &str,
    class: &str,
    result: audit::Result<T>,
    cpu: u64,
    metadata_only: bool,
) -> Value {
    json!({"kind":"negative_admission","id":id,"classification":class,
        "accepted":result.is_ok(),"error":result.err(),"metadata_only":metadata_only,
        "cpu_instances":cpu,"bus_instances":0,"actual_step_calls":0,
        "positive_composite_executions":0,"negative_control_composite_executions":0,
        "original_rom_executions":0,"firmware_ready":false})
}
fn program_controls(command: &ProgramCommand) -> Vec<Value> {
    let mut records = Vec::new();
    for id in [
        "program-wrong-digest-label",
        "program-content-changed",
        "program-wrong-base",
        "program-wrong-end",
        "program-short-stream",
        "program-dd1-changed",
        "program-node-count",
        "program-node-form",
        "program-node-operand",
        "program-node-successor",
        "program-node-dd",
        "program-provenance",
    ] {
        let mut changed = command.clone();
        match id {
            "program-wrong-digest-label" => changed.metadata.content_digest = "0".repeat(64),
            "program-content-changed" => {
                changed.dd0_bytes[0] ^= 1;
                changed.dd1_bytes[0] ^= 1;
            }
            "program-wrong-base" => changed.metadata.base = 0x1001,
            "program-wrong-end" => changed.metadata.end_exclusive = 0x1034,
            "program-short-stream" => {
                changed.dd0_bytes.pop();
            }
            "program-dd1-changed" => changed.dd1_bytes[0] ^= 1,
            "program-node-count" => {
                changed.metadata.nodes.pop();
            }
            "program-node-form" => changed.metadata.nodes[0].form = CompositeForm::SllbA,
            "program-node-operand" => {
                changed.metadata.nodes[0].operands[1] = CompositeOperand::Page(0x8f)
            }
            "program-node-successor" => changed.metadata.nodes[0].successors = vec![0x1003],
            "program-node-dd" => changed.metadata.nodes[1].reachable_dd = vec![true],
            "program-provenance" => changed.metadata.provenance = "NotInvented".into(),
            _ => unreachable!("closed literal inventory"),
        }
        let result = ClosedCompositeProgram::admit_emission(
            changed.dd0_bytes,
            changed.dd1_bytes,
            changed.metadata,
        );
        records.push(admission(
            id,
            "ActualClosedProgramAdmission",
            result,
            0,
            matches!(id, "program-wrong-digest-label" | "program-provenance"),
        ));
    }
    records
}
fn operation<T>(name: &str, result: audit::Result<T>) -> Value {
    json!({"operation":name,"accepted":result.is_ok(),"error":result.err()})
}
fn legacy_identity(dd: bool) -> InstructionIdentity {
    let mut fields = Fields::default();
    fields.n8 = 0x8e;
    InstructionIdentity {
        index: 747,
        len: 2,
        mnemonic: "LB A, off N8".into(),
        dd_before: dd,
        dd_after: Some(false),
        fields,
    }
}
fn session_control(
    program: &ClosedCompositeProgram,
    id: &str,
    request: &Case,
    budget: u8,
    prefix: usize,
) -> Result<Value, Box<dyn std::error::Error>> {
    let mut session = session_for_case(program, request, budget)?;
    let mut actual_prefix = 0_usize;
    let mut completed = false;
    let mut prefix_error: Option<AuditError> = None;
    for _ in 0..prefix {
        match session.step_composite() {
            Ok(step) => {
                actual_prefix += 1;
                completed = step.outcome.external_exit.is_some();
            }
            Err(error) => {
                prefix_error = Some(error);
                break;
            }
        }
    }
    let mut operations = Vec::new();
    if prefix_error.is_none() {
        match id {
            "functional-read-outside-step" => operations.push(operation(
                "data-read-word0196",
                session.data_read(0x196, 16),
            )),
            "functional-write-readonly-low" => operations.push(operation(
                "data-write-word0196-low",
                session.data_write(0x196, 8, 0x55),
            )),
            "functional-write-readonly-high" => operations.push(operation(
                "data-write-word0196-high",
                session.data_write(0x197, 8, 0x55),
            )),
            "functional-write-gate-B" | "functional-write-gate-C" => operations.push(operation(
                "data-write-gate012a",
                session.data_write(0x12a, 8, 0x55),
            )),
            "functional-reseed" => operations.push(operation(
                "seed-after-functional",
                session.seed_byte(0x117, 0x55),
            )),
            "functional-second-transition" => operations.push(operation(
                "second-functional-transition",
                session.begin_functional(),
            )),
            "functional-legacy-step" => operations.push(operation(
                "caller-selected-legacy-step",
                session.step(&legacy_identity(request.entry.dd)),
            )),
            "functional-program-probe" => operations.push(operation(
                "program-probe-in-functional",
                session.program_probe(0x1000),
            )),
            "budget-one-exhaustion" => {
                operations.push(operation("step-after-budget", session.step_composite()));
                operations.push(operation(
                    "step-after-first-fault",
                    session.step_composite(),
                ));
                operations.push(operation(
                    "program-after-first-fault",
                    session.program_probe(0x1002),
                ));
            }
            "terminal-seal-A" | "terminal-seal-D" => {
                let target = if request.path == "A" { 0x55c5 } else { 0x5596 };
                operations.push(operation(
                    "extra-step-after-direct-j",
                    session.step_composite(),
                ));
                operations.push(operation(
                    "external-program-probe-after-j",
                    session.program_probe(target),
                ));
                operations.push(operation("data-read-after-j", session.data_read(0x196, 16)));
                operations.push(operation(
                    "data-write-after-j",
                    session.data_write(0x117, 8, 0x55),
                ));
                operations.push(operation("reseed-after-j", session.seed_byte(0x117, 0x55)));
                operations.push(operation("functional-after-j", session.begin_functional()));
            }
            _ => return Err("Unknown fixed negative session control".into()),
        }
    }
    let report = session
        .composite_report()
        .map_err(|e| format!("{}:{}", e.code, e.detail))?;
    Ok(json!({"kind":"negative_session","id":id,
        "classification":"ActualClosedCompositeSessionCapability",
        "source_case_id":request.case_id,"source_internal_sf":request.internal_sf,
        "actual_successful_prefix_steps":actual_prefix,
        "completed_before_negative_operation":completed,"prefix_error":prefix_error,
        "operations":operations,"report":report,"metadata_only":false,
        "cpu_instances":1,"bus_instances":1,"data_initializations":1,"functional_transitions":1,
        "positive_composite_executions":0,
        "negative_control_composite_executions":u64::from(completed),
        "original_rom_executions":0,"firmware_ready":false}))
}
pub(super) fn observe(
    program: &ClosedCompositeProgram,
    command: &ProgramCommand,
) -> Result<Vec<Value>, Box<dyn std::error::Error>> {
    let mut records = program_controls(command);
    let control = closed_case("D")?;
    for id in [
        "seed-missing-byte",
        "seed-extra-byte",
        "seed-r-alias",
        "seed-er-alias",
    ] {
        let mut changed = control.clone();
        match id {
            "seed-missing-byte" => {
                changed.data.remove(&0x117);
            }
            "seed-extra-byte" => {
                changed.data.insert(0x200, 0x55);
            }
            "seed-r-alias" => changed.entry.local_r[0] ^= 1,
            "seed-er-alias" => changed.entry.local_er[0] ^= 1,
            _ => unreachable!("closed seed controls"),
        }
        records.push(admission(
            id,
            "ActualClosedSeedAdmission",
            seeds(&changed),
            0,
            false,
        ));
    }
    records.push(admission(
        "psw-incompatible-admission",
        "ActualAdmissionOnlyNoCpu",
        audit::validate_psw(control.entry.psw & !0x0008),
        0,
        false,
    ));
    for id in [
        "budget-zero",
        "budget-seventeen",
        "entry-wrong-pc",
        "entry-wrong-lrb",
    ] {
        let seed = seeds(&control).map_err(|e| format!("{}:{}", e.code, e.detail))?;
        let mut cpu = seed_cpu(&control.entry, control.internal_sf)?;
        let budget = match id {
            "budget-zero" => 0,
            "budget-seventeen" => 17,
            _ => 16,
        };
        match id {
            "entry-wrong-pc" => cpu.pc = 0x1001,
            "entry-wrong-lrb" => cpu.lrb = 0x20,
            _ => {}
        }
        let result = Session::new_closed_composite(program, cpu, control.entry.psw, seed, budget);
        records.push(admission(
            id,
            "ActualConstructorRefusalAfterOneCpuBeforeBus",
            result,
            1,
            false,
        ));
    }
    for (id, path, budget, prefix) in [
        ("functional-read-outside-step", "D", 16, 0),
        ("functional-write-readonly-low", "D", 16, 0),
        ("functional-write-readonly-high", "D", 16, 0),
        ("functional-write-gate-B", "B", 16, 0),
        ("functional-write-gate-C", "C", 16, 0),
        ("functional-reseed", "D", 16, 0),
        ("functional-second-transition", "D", 16, 0),
        ("functional-legacy-step", "D", 16, 0),
        ("functional-program-probe", "D", 16, 0),
        ("budget-one-exhaustion", "D", 1, 1),
        ("terminal-seal-A", "A", 16, 11),
        ("terminal-seal-D", "D", 16, 16),
    ] {
        let request = closed_case(path)?;
        let record = session_control(program, id, &request, budget, prefix)?;
        let unexpected_prefix_fault = !record["prefix_error"].is_null();
        records.push(record);
        if unexpected_prefix_fault {
            break;
        } // Preserve partial actual report; never retry or finish controls.
    }
    Ok(records)
}
