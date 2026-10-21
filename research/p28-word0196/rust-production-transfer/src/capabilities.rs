//! Closed real admission/runtime controls. No effects implementation or CPU
//! mutation hook. Private-state fault injections live in production unit tests.
use super::*;
use p28_slice_runner::audit::{AuditError, CompositeOperand, InstructionIdentity};
use p28_slice_runner::decoder::Fields;

pub const NEGATIVE_RECORDS: usize = 58;
fn closed_case() -> Result<Case, Box<dyn std::error::Error>> {
    let value = closed_inputs()
        .iter()
        .find(|v| v["path"] == "A" && v["internal_sf"] == false)
        .ok_or("Closed A control missing")?;
    Ok(serde_json::from_slice(&serde_json::to_vec(value)?)?)
}
fn seeds(case: &Case) -> audit::Result<CompositeSeeds> {
    CompositeSeeds::new(
        case.data.clone(),
        std::array::from_fn(|i| {
            let b = &case.entry.pointing_banks[i];
            [b.x1, b.x2, b.dp, b.usp]
        }),
        case.entry.local_r,
        case.entry.local_er,
    )
}
fn admission<T>(id: &str, result: audit::Result<T>, cpu: u64, metadata_only: bool) -> Value {
    let bus_instances = u64::from(cpu != 0 && result.is_ok());
    json!({"kind":"transfer_negative_admission","id":id,"accepted":result.is_ok(),"error":result.err(),
        "classification":"ActualClosedAdmissionRefusal","metadata_only":metadata_only,"cpu_instances":cpu,"bus_instances":bus_instances,
        "actual_step_calls":0,"original_rom_executions":0,"firmware_ready":false})
}
fn program_controls(
    command: &ProgramCommand,
    output: &mut impl FnMut(Value) -> Result<(), Box<dyn std::error::Error>>,
) -> Result<(), Box<dyn std::error::Error>> {
    for id in [
        "caller-wrong-opcode",
        "caller-wrong-target",
        "composite-wrong-sha",
        "continuation-wrong-sha",
        "caller-wrong-base",
        "overlapping-continuation",
        "unauthorized-continuation-replacement",
        "partial-continuations",
        "composite-content-changed",
        "composite-dd1-changed",
        "composite-node-count",
        "composite-operand",
        "composite-dd-context",
        "caller-provenance",
        "caller-wrong-end",
        "continuation-wrong-end",
        "caller-short",
        "continuation-short",
    ] {
        let mut changed = command.clone();
        match id {
            "caller-wrong-opcode" => changed.caller_bytes[0] ^= 1,
            "caller-wrong-target" => changed.caller_bytes[1] ^= 1,
            "composite-wrong-sha" => changed.metadata.content_digest = "0".repeat(64),
            "continuation-wrong-sha" => {
                changed.transfer_metadata.below.as_mut().unwrap().sha256 = "0".repeat(64)
            }
            "caller-wrong-base" => changed.transfer_metadata.caller.base += 1,
            "overlapping-continuation" => {
                changed.transfer_metadata.below.as_mut().unwrap().base = 0x1000
            }
            "unauthorized-continuation-replacement" => {
                changed.below_bytes.as_mut().unwrap()[1] = 1;
                changed.transfer_metadata.below.as_mut().unwrap().sha256 =
                    sha256::digest(changed.below_bytes.as_ref().unwrap());
            }
            "partial-continuations" => {
                changed.below_bytes = None;
                changed.transfer_metadata.below = None;
            }
            "composite-content-changed" => {
                changed.dd0_bytes[0] ^= 1;
                changed.dd1_bytes[0] ^= 1;
            }
            "composite-dd1-changed" => changed.dd1_bytes[0] ^= 1,
            "composite-node-count" => {
                changed.metadata.nodes.pop();
            }
            "composite-operand" => {
                changed.metadata.nodes[0].operands[1] = CompositeOperand::Page(0x8f)
            }
            "composite-dd-context" => changed.metadata.nodes[1].reachable_dd = vec![true],
            "caller-provenance" => {
                changed.transfer_metadata.caller.provenance = "NativeUnproven".into()
            }
            "caller-wrong-end" => changed.transfer_metadata.caller.end_exclusive += 1,
            "continuation-wrong-end" => {
                changed
                    .transfer_metadata
                    .below
                    .as_mut()
                    .unwrap()
                    .end_exclusive += 1
            }
            "caller-short" => {
                changed.caller_bytes.pop();
            }
            "continuation-short" => {
                changed.below_bytes.as_mut().unwrap().pop();
            }
            _ => unreachable!(),
        }
        output(admission(
            id,
            admit_program(&changed),
            0,
            matches!(
                id,
                "caller-provenance" | "composite-wrong-sha" | "continuation-wrong-sha"
            ),
        ))?;
    }
    Ok(())
}
fn operation<T>(name: &str, result: audit::Result<T>) -> Value {
    json!({"operation":name,"accepted":result.is_ok(),"error":result.err()})
}
fn prefix(
    session: &mut Session,
    count: usize,
    commit_last: bool,
) -> Result<(), (&'static str, AuditError)> {
    for index in 0..count {
        let step = session.step_transfer().map_err(|e| ("PrefixStep", e))?;
        if step.outcome.external_exit.is_some() && (index + 1 < count || commit_last) {
            let ticket = session
                .take_transfer_ticket()
                .map_err(|e| ("PrefixTakeTicket", e))?;
            session
                .commit_transfer(&ticket, &ticket.claim())
                .map_err(|e| ("PrefixCommitTicket", e))?;
        }
    }
    Ok(())
}
// Only unexpected failures use this envelope. Normal control DTOs and their exact
// diagnostic snapshot protocol remain unchanged. Never includes PROGRAM bytes.
fn failure_record(
    id: &str,
    operation: &str,
    error: AuditError,
    session: &mut Session,
    other: Option<&mut Session>,
    instances: u64,
) -> Value {
    let retain = |session: &mut Session| match session.transfer_report() {
        Ok(report) => {
            json!({"report":report,"report_error":null,"snapshot_fallback":null,"audit_fallback":null})
        }
        Err(report_error) => json!({"report":null,"report_error":report_error,
            "snapshot_fallback":session.diagnostic_snapshot().ok(),"audit_fallback":session.report()}),
    };
    let partial = retain(session);
    let other_partial = other.map(retain);
    json!({"kind":"transfer_negative_harness_failure","id":id,"classification":"UnexpectedControlFailure_ActualPartialStateRetained",
        "operation":operation,"error":error,"partial":partial,"other_partial":other_partial,
        "cpu_instances":instances,"bus_instances":instances,"data_initializations":instances,"functional_transitions":instances,
        "positive_transfer_executions":0,"original_rom_executions":0,"firmware_ready":false})
}
fn runtime_control(
    program: &ClosedSyntheticTransferProgram,
    id: &str,
    case: &Case,
) -> Result<Value, Box<dyn std::error::Error>> {
    let budget = if id == "global-budget-exhaustion" {
        1
    } else {
        18
    };
    let mut session = session_for_case(program, case, budget)?;
    let (steps, commit_last) = if id == "claim-wrong-continuation-path" {
        (12, false)
    } else if id.starts_with("checkpoint-") {
        (13, true)
    } else if id.starts_with("functional-")
        || matches!(id, "between-stage-reseed" | "global-budget-exhaustion")
    {
        (1, true)
    } else if matches!(
        id,
        "premature-ticket" | "legacy-one-step-api" | "legacy-composite-api"
    ) {
        (0, false)
    } else {
        (1, false)
    };
    if let Err((operation, error)) = prefix(&mut session, steps, commit_last) {
        return Ok(failure_record(id, operation, error, &mut session, None, 1));
    }
    let mut operations = vec![];
    let mut other_report = None;
    let mut instances = 1_u64;
    match id {
        "premature-ticket" | "checkpoint-ticket" => {
            operations.push(operation("take-ticket", session.take_transfer_ticket()))
        }
        "pending-extra-step" | "checkpoint-extra-step" | "global-budget-exhaustion" => {
            operations.push(operation("step-transfer", session.step_transfer()))
        }
        "pending-fetch" | "checkpoint-fetch" => operations.push(operation(
            "program-probe",
            session.program_probe(if id == "pending-fetch" {
                0x1000
            } else {
                0x55c7
            }),
        )),
        "pending-write" | "functional-data-write" | "checkpoint-write" => {
            operations.push(operation("data-write", session.data_write(0x18e, 8, 0x42)))
        }
        "functional-data-read" => {
            operations.push(operation("data-read", session.data_read(0x196, 16)))
        }
        "functional-sfr-read" => {
            operations.push(operation("data-read-sfr", session.data_read(0x10, 8)))
        }
        "functional-program-gap" => operations.push(operation(
            "program-gap-probe",
            session.program_probe(0x2000),
        )),
        "pending-reseed" | "between-stage-reseed" | "checkpoint-reseed" => {
            operations.push(operation("reseed", session.seed_byte(0x196, 0)))
        }
        "duplicate-ticket" => {
            match session.take_transfer_ticket() {
                Ok(ticket) => {
                    operations.push(operation("take-ticket-first", Ok::<_, AuditError>(ticket)))
                }
                Err(error) => {
                    return Ok(failure_record(
                        id,
                        "ControlTakeTicket",
                        error,
                        &mut session,
                        None,
                        1,
                    ))
                }
            }
            operations.push(operation(
                "take-ticket-second",
                session.take_transfer_ticket(),
            ));
        }
        "claim-target" | "claim-source" | "claim-destination" | "claim-architecture"
        | "claim-data" | "claim-journal" | "claim-counters" | "claim-ordinal" => {
            let ticket = match session.take_transfer_ticket() {
                Ok(ticket) => ticket,
                Err(error) => {
                    return Ok(failure_record(
                        id,
                        "ControlTakeTicket",
                        error,
                        &mut session,
                        None,
                        1,
                    ))
                }
            };
            let mut claim = ticket.claim();
            match id {
                "claim-target" => claim.actual_target_pc += 1,
                "claim-source" => claim.source.sha256 = "0".repeat(64),
                "claim-destination" => claim.destination.base = 0x5596,
                "claim-architecture" => claim.architecture_sha256 = "0".repeat(64),
                "claim-data" => claim.data_sha256 = "0".repeat(64),
                "claim-journal" => claim.journal.raw += 1,
                "claim-counters" => claim.counters.cpu_cycles += 1,
                _ => claim.transition_ordinal += 1,
            }
            operations.push(operation(
                "commit-mutated-claim",
                session.commit_transfer(&ticket, &claim),
            ));
        }
        "cross-session-ticket" => {
            let mut other = match session_for_case(program, case, 18) {
                Ok(other) => other,
                Err(error) => {
                    return Ok(failure_record(
                        id,
                        "OtherSessionConstruction",
                        AuditError {
                            code: "HarnessSessionConstructionError".into(),
                            address: None,
                            detail: error.to_string(),
                        },
                        &mut session,
                        None,
                        1,
                    ))
                }
            };
            instances += 1;
            if let Err((operation, error)) = prefix(&mut other, 1, false) {
                return Ok(failure_record(
                    id,
                    operation,
                    error,
                    &mut session,
                    Some(&mut other),
                    instances,
                ));
            }
            let ticket = match other.take_transfer_ticket() {
                Ok(ticket) => ticket,
                Err(error) => {
                    return Ok(failure_record(
                        id,
                        "OtherControlTakeTicket",
                        error,
                        &mut session,
                        Some(&mut other),
                        instances,
                    ))
                }
            };
            operations.push(operation(
                "commit-other-session-ticket",
                session.commit_transfer(&ticket, &ticket.claim()),
            ));
            other_report = Some(match other.transfer_report() {
                Ok(report) => report,
                Err(error) => {
                    return Ok(failure_record(
                        id,
                        "OtherControlReport",
                        error,
                        &mut session,
                        Some(&mut other),
                        instances,
                    ))
                }
            });
        }
        "claim-wrong-continuation-path" => {
            let ticket = match session.take_transfer_ticket() {
                Ok(ticket) => ticket,
                Err(error) => {
                    return Ok(failure_record(
                        id,
                        "ControlTakeTicket",
                        error,
                        &mut session,
                        None,
                        1,
                    ))
                }
            };
            let mut claim = ticket.claim();
            claim.destination = program
                .profiles()
                .into_iter()
                .find(|profile| profile.id == audit::TransferSegmentId::NotBelowContinuation)
                .expect("admitted NotBelow profile");
            claim.actual_target_pc = 0x5596;
            operations.push(operation(
                "commit-wrong-continuation-path",
                session.commit_transfer(&ticket, &claim),
            ));
        }
        "reused-ticket" => {
            let ticket = match session.take_transfer_ticket() {
                Ok(ticket) => ticket,
                Err(error) => {
                    return Ok(failure_record(
                        id,
                        "ControlTakeTicket",
                        error,
                        &mut session,
                        None,
                        1,
                    ))
                }
            };
            match session.commit_transfer(&ticket, &ticket.claim()) {
                Ok(commit) => operations.push(operation(
                    "commit-ticket-first",
                    Ok::<_, AuditError>(commit),
                )),
                Err(error) => {
                    return Ok(failure_record(
                        id,
                        "ControlCommitTicket",
                        error,
                        &mut session,
                        None,
                        1,
                    ))
                }
            }
            operations.push(operation(
                "commit-ticket-second",
                session.commit_transfer(&ticket, &ticket.claim()),
            ));
        }
        "legacy-one-step-api" => {
            let identity = InstructionIdentity {
                index: 684,
                len: 3,
                mnemonic: "J addr16".into(),
                dd_before: case.entry.dd,
                dd_after: None,
                fields: Fields {
                    addr16: 0x1000,
                    ..Fields::default()
                },
            };
            operations.push(operation("legacy-step", session.step(&identity)));
        }
        "legacy-composite-api" => {
            operations.push(operation("legacy-composite-step", session.step_composite()))
        }
        "sticky-fault" => {
            operations.push(operation(
                "pending-program-fault",
                session.program_probe(0x1000),
            ));
            operations.push(operation("step-after-fault", session.step_transfer()));
            operations.push(operation(
                "write-after-fault",
                session.data_write(0x18e, 8, 0x42),
            ));
            operations.push(operation(
                "ticket-after-fault",
                session.take_transfer_ticket(),
            ));
        }
        _ => return Err("Unknown frozen runtime control".into()),
    }
    let report = match session.transfer_report() {
        Ok(report) => report,
        Err(error) => {
            return Ok(failure_record(
                id,
                "ControlReport",
                error,
                &mut session,
                None,
                instances,
            ))
        }
    };
    Ok(
        json!({"kind":"transfer_negative_runtime","id":id,"classification":"ActualPublicApiRuntimeRefusal",
        "operations":operations,"report":report,"other_session_report":other_report,
        "cpu_instances":instances,"bus_instances":instances,"data_initializations":instances,"functional_transitions":instances,
        "positive_transfer_executions":0,"original_rom_executions":0,"firmware_ready":false}),
    )
}
pub fn observe(
    program: &ClosedSyntheticTransferProgram,
    command: &ProgramCommand,
    output: &mut impl FnMut(&Value) -> Result<(), Box<dyn std::error::Error>>,
) -> Result<usize, Box<dyn std::error::Error>> {
    let mut count = 0_usize;
    let mut publish = |record: Value| -> Result<(), Box<dyn std::error::Error>> {
        let failed = record["kind"] == "transfer_negative_harness_failure";
        output(&record)?;
        count += 1;
        if failed {
            return Err(
                "Unexpected negative control failure retained; no next control or retry".into(),
            );
        }
        Ok(())
    };
    program_controls(command, &mut publish)?;
    let case = closed_case()?;
    for id in [
        "entry-budget-zero",
        "entry-budget-19",
        "entry-wrong-pc",
        "entry-wrong-lrb",
        "entry-nonzero-counters",
        "entry-incoherent-psw",
    ] {
        let mut cpu = seed_cpu(&case.entry, case.internal_sf)?;
        let mut budget = 18;
        match id {
            "entry-budget-zero" => budget = 0,
            "entry-budget-19" => budget = 19,
            "entry-wrong-pc" => cpu.pc = 0x1000,
            "entry-wrong-lrb" => cpu.lrb = 0x22,
            "entry-nonzero-counters" => {
                cpu.instructions = 1;
                cpu.cycles = 7;
            }
            _ => cpu.cf = !cpu.cf,
        }
        publish(admission(
            id,
            Session::new_closed_transfer(
                program,
                cpu,
                case.entry.psw,
                seeds(&case).map_err(|e| format!("{}:{}", e.code, e.detail))?,
                budget,
            ),
            1,
            false,
        ))?;
    }
    for id in ["seed-alias-conflict", "seed-extra-address"] {
        let mut changed = case.clone();
        if id == "seed-alias-conflict" {
            changed.entry.local_r[0] ^= 1;
        } else {
            changed.data.insert(0x198, 0);
        }
        publish(admission(id, seeds(&changed), 0, false))?;
    }
    for id in [
        "premature-ticket",
        "pending-extra-step",
        "pending-fetch",
        "pending-write",
        "pending-reseed",
        "duplicate-ticket",
        "claim-target",
        "claim-source",
        "claim-destination",
        "claim-architecture",
        "claim-data",
        "claim-journal",
        "claim-counters",
        "claim-ordinal",
        "cross-session-ticket",
        "reused-ticket",
        "legacy-one-step-api",
        "legacy-composite-api",
        "functional-data-read",
        "functional-data-write",
        "functional-sfr-read",
        "functional-program-gap",
        "between-stage-reseed",
        "global-budget-exhaustion",
        "checkpoint-extra-step",
        "checkpoint-fetch",
        "checkpoint-write",
        "checkpoint-reseed",
        "checkpoint-ticket",
        "sticky-fault",
        "claim-wrong-continuation-path",
    ] {
        publish(runtime_control(program, id, &case)?)?;
    }
    // Intentionally no invented continuation mapping: the actual terminal J
    // must preserve the legacy sealed external stop, not auto-admit a segment.
    let mut absent = command.clone();
    absent.below_bytes = None;
    absent.not_below_bytes = None;
    absent.transfer_metadata.below = None;
    absent.transfer_metadata.not_below = None;
    let absent_program = admit_program(&absent).map_err(|e| format!("{}:{}", e.code, e.detail))?;
    let mut session = session_for_case(&absent_program, &case, 18)?;
    for (steps, commit_last) in [(1, true), (11, false)] {
        if let Err((operation, error)) = prefix(&mut session, steps, commit_last) {
            publish(failure_record(
                "missing-continuations-sealed-stop",
                operation,
                error,
                &mut session,
                None,
                1,
            ))?;
            return Err("Unexpected absent-continuation prefix failure retained".into());
        }
    }
    let mut operations = vec![operation(
        "post-terminal-probe",
        session.program_probe(0x55c5),
    )];
    operations.push(operation("post-terminal-step", session.step_transfer()));
    let report = match session.transfer_report() {
        Ok(report) => report,
        Err(error) => {
            publish(failure_record(
                "missing-continuations-sealed-stop",
                "ControlReport",
                error,
                &mut session,
                None,
                1,
            ))?;
            return Err("Unexpected absent-continuation report failure retained".into());
        }
    };
    publish(
        json!({"kind":"transfer_negative_runtime","id":"missing-continuations-sealed-stop","classification":"ActualAbsentContinuationSealedStop",
        "operations":operations,"report":report,"other_session_report":null,"cpu_instances":1,"bus_instances":1,"data_initializations":1,"functional_transitions":1,
        "positive_transfer_executions":0,"original_rom_executions":0,"firmware_ready":false}),
    )?;
    if count != NEGATIVE_RECORDS {
        return Err("Frozen negative inventory cardinality differs from source literal".into());
    }
    Ok(count)
}
