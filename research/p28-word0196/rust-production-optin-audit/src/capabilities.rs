//! Finite literal capability experiments, never a caller-selected program.
use super::*;

fn text_error(error: AuditError) -> String {
    format!("{}:{}", error.code, error.detail)
}
fn template(form: FormId) -> &'static ClosedInput {
    corpus()
        .iter()
        .find(|row| row.request.form == form && row.expected_admission == "Accepted")
        .expect("frozen positive representative")
}
fn live(form: FormId, permissions: Permissions) -> std::result::Result<Session, String> {
    session(template(form), permissions).map_err(|e| format!("{}:{}", e.code, e.detail))
}
fn rights(reads: &[(u16, u8)], writes: &[(u16, u8, bool)]) -> Permissions {
    Permissions::new(
        reads
            .iter()
            .map(|&(address, width)| Access { address, width })
            .collect(),
        writes
            .iter()
            .map(|&(address, width, rmw_required)| WriteAccess {
                access: Access { address, width },
                rmw_required,
            })
            .collect(),
    )
    .expect("literal bounded rights")
}
fn capture(
    id: &str,
    mut machine: Session,
    operation: impl FnOnce(&mut Session) -> audit::Result<Value>,
) -> std::result::Result<Value, String> {
    let before = machine.diagnostic_snapshot().map_err(text_error)?;
    let result = operation(&mut machine);
    let after = machine.diagnostic_snapshot().map_err(text_error)?;
    Ok(
        json!({"id":id,"classification":"ActualProductionInterfaceCapabilityObservation",
        "before":before,"after":after,"result":result.as_ref().ok(),"error":result.as_ref().err(),
        "audit":machine.report(),"cpu_instances":1,"bus_instances":1,
        "production_composite_executions":0,"original_rom_executions":0}),
    )
}
fn program_machine(bytes: Vec<u8>) -> std::result::Result<Session, String> {
    let r = &template(FormId::LbAPage).request;
    let segment =
        ProgramSegment::new(4096, bytes.clone(), &sha256::digest(&bytes)).map_err(text_error)?;
    Session::new(
        segment,
        seed_cpu(&r.entry, BASE, r.internal_sf),
        r.entry.psw,
        rights(&[], &[]),
        1,
    )
    .map_err(text_error)
}
fn construct_record<T>(id: &str, result: audit::Result<T>) -> Value {
    json!({"id":id,"classification":"ActualProductionConstructorAdmission",
        "accepted":result.is_ok(),"error":result.err(),"cpu_instances":0,"bus_instances":0,"actual_step_calls":0})
}

pub(super) fn observe() -> std::result::Result<Value, Box<dyn std::error::Error>> {
    let mut records = Vec::new();
    // Immutable 51-byte opaque canary, NOT the M2bj stream. No decode/step.
    for (id, address) in [
        ("mapping-first", 4096_i64),
        ("mapping-last", 4146),
        ("mapping-before-base", 4095),
        ("mapping-end-exclusive", 4147),
        ("mapping-negative", -1),
        ("mapping-address-overflow", i64::MAX),
        ("mapping-outside-16-bit", 65536),
    ] {
        records.push(capture(id, program_machine(vec![0xa5; 51])?, |s| {
            s.program_probe(address).map(|v| json!(v))
        })?);
    }
    records.push(construct_record(
        "invalid-segment-base",
        ProgramSegment::new(u32::MAX, vec![0xa5], &sha256::digest(&[0xa5])),
    ));
    records.push(construct_record(
        "invalid-segment-overflow",
        ProgramSegment::new(65535, vec![0xa5; 2], &sha256::digest(&[0xa5; 2])),
    ));
    records.push(construct_record(
        "invalid-empty-segment",
        ProgramSegment::new(4096, vec![], &sha256::digest(&[])),
    ));
    records.push(construct_record(
        "wrong-actual-program-digest",
        ProgramSegment::new(4096, vec![0xa5], &"0".repeat(64)),
    ));
    records.push(construct_record(
        "unsupported-sfr-rights",
        Permissions::new(
            vec![Access {
                address: 0x17,
                width: 8,
            }],
            vec![],
        ),
    ));
    records.push(construct_record(
        "invalid-word-constituent-overflow",
        Permissions::new(
            vec![Access {
                address: 65535,
                width: 16,
            }],
            vec![],
        ),
    ));
    records.push(construct_record(
        "raw-read-widening",
        rights(&[(0x196, 16)], &[]).restrict_raw(vec![0x196, 0x197, 0x198], vec![]),
    ));
    records.push(construct_record(
        "raw-write-widening",
        rights(&[(0x196, 16)], &[]).restrict_raw(vec![0x196, 0x197], vec![0x196]),
    ));

    for (id, bytes, form) in [
        (
            "strict-decoder-out-of-range-probe",
            vec![0xc4],
            FormId::RolbPage,
        ),
        ("strict-missing-selected-byte", vec![0xf4], FormId::LbAPage),
    ] {
        let expected = identity(&template(form).request);
        records.push(capture(id, program_machine(bytes)?, move |s| {
            s.begin_functional()?;
            s.step(&expected).map(|v| json!(v))
        })?);
    }
    for (id, operand) in [
        ("wrong-selected-form-identity", false),
        ("wrong-selected-operand-identity", true),
    ] {
        let row = template(FormId::LbAPage);
        let permissions = admit(row).map_err(|e| format!("{}:{}", e.code, e.detail))?;
        let mut wrong = identity(&row.request);
        if operand {
            wrong.fields.n8 ^= 1;
        } else {
            wrong.index += 1;
        }
        records.push(capture(
            id,
            session(row, permissions).map_err(|e| format!("{}:{}", e.code, e.detail))?,
            move |s| {
                s.begin_functional()?;
                s.step(&wrong).map(|v| json!(v))
            },
        )?);
    }
    records.push(capture(
        "forbidden-data-read",
        live(FormId::LbAPage, rights(&[], &[]))?,
        |s| {
            s.begin_functional()?;
            s.data_read(0x117, 8).map(|v| json!(v))
        },
    )?);
    records.push(capture(
        "forbidden-data-write",
        live(FormId::LbAPage, rights(&[(0x117, 8)], &[]))?,
        |s| {
            s.begin_functional()?;
            s.data_write(0x117, 8, 0x55).map(|_| Value::Null)
        },
    )?);
    records.push(capture(
        "readonly-data0196-write",
        live(FormId::CmpPageImm16, rights(&[(0x196, 16)], &[]))?,
        |s| {
            s.begin_functional()?;
            s.data_write(0x196, 16, 0xbeef).map(|_| Value::Null)
        },
    )?);
    records.push(capture(
        "rmw-write-without-read",
        live(FormId::RolbPage, rights(&[(0x18e, 8)], &[(0x18e, 8, true)]))?,
        |s| {
            s.begin_functional()?;
            s.data_write(0x18e, 8, 0x33).map(|_| Value::Null)
        },
    )?);
    let reads = rights(&[(0x196, 16)], &[])
        .restrict_raw(vec![0x196], vec![])
        .map_err(text_error)?;
    records.push(capture(
        "word-high-read-refused",
        live(FormId::CmpPageImm16, reads)?,
        |s| {
            s.begin_functional()?;
            s.data_read(0x196, 16).map(|v| json!(v))
        },
    )?);
    // Deliberately partial invented local-register word, NOT read-only0196.
    let writes = rights(&[], &[(0x108, 16, false)])
        .restrict_raw(vec![], vec![0x108])
        .map_err(text_error)?;
    records.push(capture(
        "word-high-write-refused-partial-low",
        live(FormId::CmpPageImm16, writes)?,
        |s| {
            s.begin_functional()?;
            s.data_write(0x108, 16, 0xbeef).map(|_| Value::Null)
        },
    )?);
    records.push(capture(
        "same-value-fresh-store-ordinals",
        live(FormId::LbAPage, rights(&[(0x117, 8)], &[(0x117, 8, false)]))?,
        |s| {
            s.begin_functional()?;
            let value = s.data_read(0x117, 8)?;
            s.data_write(0x117, 8, value)?;
            s.data_write(0x117, 8, value)?;
            Ok(json!({"value":value}))
        },
    )?);
    records.push(capture(
        "actual-rmw-read-then-write",
        live(FormId::RolbPage, rights(&[(0x18e, 8)], &[(0x18e, 8, true)]))?,
        |s| {
            s.begin_functional()?;
            let old = s.data_read(0x18e, 8)?;
            s.data_write(0x18e, 8, old)?;
            Ok(json!({"old":old,"new":old}))
        },
    )?);
    records.push(capture(
        "actual-le16-logical-and-raw",
        live(FormId::CmpPageImm16, rights(&[(0x196, 16)], &[]))?,
        |s| {
            s.begin_functional()?;
            s.data_read(0x196, 16).map(|v| json!(v))
        },
    )?);
    records.push(capture(
        "partial-production-operand-error",
        live(FormId::LbAPage, rights(&[], &[]))?,
        |s| {
            s.begin_functional()?;
            s.step(&identity(&template(FormId::LbAPage).request))
                .map(|v| json!(v))
        },
    )?);
    records.push(capture(
        "execution-after-fault",
        live(FormId::LbAPage, rights(&[], &[]))?,
        |s| {
            s.begin_functional()?;
            let first = s.data_read(0x117, 8);
            let second = s.step(&identity(&template(FormId::LbAPage).request));
            Ok(json!({"first_error":first.err(),"second_error":second.err()}))
        },
    )?);
    for (id, operation) in [
        ("fetch-after-real-direct-j-seal", 0),
        ("extra-retirement-after-budget", 1),
        ("data-write-after-seal", 2),
    ] {
        let row = template(FormId::JAddress);
        let permissions = admit(row).map_err(|e| format!("{}:{}", e.code, e.detail))?;
        records.push(capture(id,session(row,permissions).map_err(|e|format!("{}:{}",e.code,e.detail))?,move|s|{
            s.begin_functional()?;let retired=s.step(&identity(&row.request))?;
            let refused=match operation {
                0=>s.program_probe(i64::from(retired.pc_after)).map(|v|json!(v)),
                1=>s.step(&identity(&row.request)).map(|v|json!(v)),
                _=>s.data_write(0x117,8,0x55).map(|_|Value::Null),
            };
            Ok(json!({"actual_retirement":retired,"later_result":refused.as_ref().ok(),"later_error":refused.as_ref().err()}))
        })?);
    }
    records.push(capture(
        "seed-after-functional-refused",
        live(FormId::LbAPage, rights(&[], &[]))?,
        |s| {
            s.begin_functional()?;
            s.seed_byte(0x117, 0x55).map(|_| Value::Null)
        },
    )?);
    records.push(capture(
        "diagnostic-not-rmw-read",
        live(FormId::RolbPage, rights(&[(0x18e, 8)], &[(0x18e, 8, true)]))?,
        |s| {
            s.begin_functional()?;
            s.diagnostic_snapshot()?;
            s.data_write(0x18e, 8, 0x55).map(|_| Value::Null)
        },
    )?);
    Ok(json!({"kind":"capability_observations","records":records,
        "opaque_51_byte_canary_is_m2bj":false,"opaque_canary_executions":0,
        "full_production_composite_executions":0,"original_rom_executions":0,"firmware_ready":false}))
}
