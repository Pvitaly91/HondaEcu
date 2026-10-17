//! Closed M2bp single-step probes. No ROM/file loader or composite operation.
#![forbid(unsafe_code)]

mod capabilities;
use p28_research_production_exec_parity::{state::seed_cpu, ProductionProbeRequest};
use p28_research_synthetic_adapter::{data::INVENTORY, program::MicroProgram, sha256, FormId};
use p28_slice_runner::{
    audit::{
        self, Access, AuditError, InstructionIdentity, Permissions, ProgramSegment, Session,
        WriteAccess,
    },
    decoder::Fields,
};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{
    io::{self, BufRead, Read, Write},
    sync::OnceLock,
};

const BASE: u16 = 0x1000;
const HISTORICAL: &str = "1ceec589ee8586727fb16a39fd15875444d6feab";

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct ClosedInput {
    request: ProductionProbeRequest,
    profile: String,
    source_family: String,
    source_case_id: String,
    expected_admission: String,
    denied_effects: Vec<Value>,
}

#[derive(Debug, Clone, Serialize)]
struct Refusal {
    code: String,
    detail: String,
}
impl Refusal {
    fn new(code: &str, detail: impl Into<String>) -> Self {
        Self {
            code: code.into(),
            detail: detail.into(),
        }
    }
}
impl From<AuditError> for Refusal {
    fn from(value: AuditError) -> Self {
        Self::new(&value.code, value.detail)
    }
}
type Result<T> = std::result::Result<T, Refusal>;

fn corpus() -> &'static [ClosedInput] {
    static INPUTS: OnceLock<Vec<ClosedInput>> = OnceLock::new();
    INPUTS.get_or_init(|| {
        serde_json::from_slice(include_bytes!("../closed_inputs.json"))
            .expect("source-bound closed inputs")
    })
}

fn derive_profile(request: &ProductionProbeRequest) -> Result<&'static str> {
    if request.data.len() != INVENTORY.len()
        || INVENTORY.iter().any(|a| !request.data.contains_key(a))
    {
        return Err(Refusal::new(
            "IncompleteDataInventory",
            "exact inventoried sixteen bytes",
        ));
    }
    let word = u16::from_le_bytes([request.data[&0x196], request.data[&0x197]]);
    Ok(if word < 0xc0 {
        "A"
    } else if request.data[&0x12a] & 0x80 != 0 {
        "B"
    } else if request.data[&0x124] & 0x20 != 0 {
        "C"
    } else {
        "D"
    })
}

fn profile_permissions(profile: &str, form: FormId) -> Result<Permissions> {
    let mut reads = vec![
        Access {
            address: 0x108,
            width: 8,
        },
        Access {
            address: 0x18e,
            width: 8,
        },
        Access {
            address: 0x196,
            width: 16,
        },
    ];
    let mut writes = vec![0x18e, 0x117];
    if profile == "A" {
        writes.push(0x18f);
    } else {
        reads.extend([0x117, 0x12a, 0x18f].map(|address| Access { address, width: 8 }));
        writes.push(0x109);
        if matches!(profile, "C" | "D") {
            reads.push(Access {
                address: 0x124,
                width: 8,
            });
        }
        if profile == "D" {
            writes.extend([0x12a, 0x18f]);
        }
    }
    let rmw = matches!(
        form,
        FormId::RolbPage | FormId::AndbPageA | FormId::OrbPageImm8
    );
    Permissions::new(
        reads,
        writes
            .into_iter()
            .map(|address| WriteAccess {
                access: Access { address, width: 8 },
                rmw_required: rmw,
            })
            .collect(),
    )
    .map_err(Into::into)
}

fn permitted_effect(profile: &str, request: &ProductionProbeRequest) -> bool {
    // Closed form access requirement, not an instruction implementation. This
    // only decides admission; all actual effects are shared production Exec.
    use FormId::*;
    match request.form {
        JbsPageBit5 => matches!(profile, "C" | "D"),
        OrbPageImm8 => profile == "D",
        StbAPage => request.bytes[1] != 0x8f || matches!(profile, "A" | "D"),
        LbAPage | AndbAPage | MovbR1Page | AndbPageA => profile != "A",
        _ => true,
    }
}

fn admit(input: &ClosedInput) -> Result<Permissions> {
    let r = &input.request;
    if r.entry.pc != BASE || r.physical_entry_pc != 0 || r.budget != 1 || r.scratch != 0xa5 {
        return Err(Refusal::new(
            "WrongOneStepScope",
            "historical input identity; actual opt-in PC1000/budget1/scratchA5",
        ));
    }
    let actual_profile = derive_profile(r)?;
    r.entry
        .validate(&r.data)
        .map_err(|e| Refusal::new(&e.code, e.detail))?;
    audit::validate_psw(r.entry.psw)?;
    if actual_profile != input.profile {
        return Err(Refusal::new(
            "ForgedPermissionProfile",
            "profile differs from validated entry predicate",
        ));
    }
    if r.form.spec().dd == '0' && r.entry.dd {
        return Err(Refusal::new("WrongDdAdmission", "exact form DD0"));
    }
    if r.bytes.len() + r.guards.len() != 6 || r.expected_length != r.bytes.len() {
        return Err(Refusal::new(
            "WrongInstructionLength",
            "one exact instruction plus explicit six-byte total guard extent",
        ));
    }
    MicroProgram::new(
        &r.fixture_id,
        r.form,
        &r.bytes,
        &r.guards,
        &r.content_digest,
        &r.entry.provenance,
    )
    .map_err(|e| Refusal::new(&e.code, e.detail))?;
    let known = corpus()
        .iter()
        .find(|k| k.request.case_id == r.case_id)
        .ok_or_else(|| {
            Refusal::new(
                "UnknownClosedCase",
                "no arbitrary instruction/ROM/input admission",
            )
        })?;
    if known != input {
        return Err(Refusal::new(
            "FrozenInputMismatch",
            "full typed input must match immutable allowlist",
        ));
    }
    if !permitted_effect(actual_profile, r) {
        return Err(Refusal::new(
            "StricterPermissionContextIncompatible",
            "unchanged M2bo microcontext outside its predicate-derived permissions",
        ));
    }
    profile_permissions(actual_profile, r.form)
}

fn identity(r: &ProductionProbeRequest) -> InstructionIdentity {
    let mut fields = Fields::default();
    for (token, &byte) in r.form.spec().pattern.iter().zip(&r.bytes) {
        match *token {
            "N8" => fields.n8 = byte,
            "N'8" => fields.n8_alt = byte,
            "NL" => fields.n16 = (fields.n16 & 0xff00) | u16::from(byte),
            "NH" => fields.n16 = (fields.n16 & 255) | (u16::from(byte) << 8),
            "addrl" => fields.addr16 = (fields.addr16 & 0xff00) | u16::from(byte),
            "addrh" => fields.addr16 = (fields.addr16 & 255) | (u16::from(byte) << 8),
            "rel8" => fields.rel8 = byte as i8,
            _ => {}
        }
    }
    InstructionIdentity {
        index: r.expected_decoded_index,
        len: r.expected_length,
        mnemonic: r.form.spec().mnemonic.into(),
        dd_before: r.entry.dd,
        dd_after: if r.form.spec().dd == 'R' {
            Some(false)
        } else {
            None
        },
        fields,
    }
}

fn session(input: &ClosedInput, permissions: Permissions) -> Result<Session> {
    let r = &input.request;
    let mut bytes = r.bytes.clone();
    bytes.extend_from_slice(&r.guards);
    let segment = ProgramSegment::new(u32::from(BASE), bytes, &r.content_digest)?;
    // Every real Cpu field is explicit. This call constructs one Cpu only after
    // full closed admission; old physical-PC0 metadata never drives execution.
    let cpu = seed_cpu(&r.entry, BASE, r.internal_sf);
    let mut result = Session::new(segment, cpu, r.entry.psw, permissions, 1)?;
    for (&address, &value) in &r.data {
        result.seed_byte(address, value)?;
    }
    for (bank, row) in r.entry.pointing_banks.iter().enumerate() {
        for (slot, value) in [row.x1, row.x2, row.dp, row.usp].into_iter().enumerate() {
            result.seed_word(0x80 + bank as u16 * 8 + slot as u16 * 2, value)?;
        }
    }
    Ok(result)
}

fn execute(input: &ClosedInput, permissions: Permissions) -> Result<Value> {
    let r = &input.request;
    let mut live = session(input, permissions)?;
    let before = live.diagnostic_snapshot()?;
    live.begin_functional()?;
    let actual = live.step(&identity(r));
    let after = live.diagnostic_snapshot()?;
    let report = live.report();
    let succeeded = actual.is_ok();
    let value = json!({"kind":"optin_observation","accepted":succeeded,
        "case_id":r.case_id,"source_case_id":input.source_case_id,"source_family":input.source_family,
        "family":r.family,"form":r.form,"permission_profile":input.profile,
        "provenance":r.entry.provenance,"physical_entry_pc":BASE,"logical_entry_pc":BASE,
        "historical_physical_pc_metadata":r.physical_entry_pc,"pc_relocated":false,
        "before":before,"after":after,"outcome":actual.as_ref().ok(),
        "error":actual.as_ref().err(),"audit":report,
        "actual_step_calls":1,"cpu_instances":1,"bus_instances":1,
        "scope":"ClosedInventedSingleStep_NotCompositePathReachability",
        "full_production_composite_executions":0,"original_rom_executions":0,"firmware_ready":false});
    Ok(value)
}

fn emit(value: &Value, output: &mut impl Write) -> io::Result<()> {
    serde_json::to_writer(&mut *output, value)?;
    output.write_all(b"\n")?;
    output.flush()
}

fn header() -> Value {
    let sources: &[(&str, &[u8])] = &[
        (
            "rust/p28-slice-runner/src/cpu.rs",
            include_bytes!("../../../../rust/p28-slice-runner/src/cpu.rs"),
        ),
        (
            "rust/p28-slice-runner/src/bus.rs",
            include_bytes!("../../../../rust/p28-slice-runner/src/bus.rs"),
        ),
        (
            "rust/p28-slice-runner/src/decoder.rs",
            include_bytes!("../../../../rust/p28-slice-runner/src/decoder.rs"),
        ),
        (
            "rust/p28-slice-runner/src/exec.rs",
            include_bytes!("../../../../rust/p28-slice-runner/src/exec.rs"),
        ),
        (
            "rust/p28-slice-runner/src/audit.rs",
            include_bytes!("../../../../rust/p28-slice-runner/src/audit.rs"),
        ),
        (
            "rust/p28-slice-runner/src/audit_bus.rs",
            include_bytes!("../../../../rust/p28-slice-runner/src/audit_bus.rs"),
        ),
        (
            "rust/p28-slice-runner/src/audit_sha256.rs",
            include_bytes!("../../../../rust/p28-slice-runner/src/audit_sha256.rs"),
        ),
        (
            "rust/p28-slice-runner/src/audit_tests.rs",
            include_bytes!("../../../../rust/p28-slice-runner/src/audit_tests.rs"),
        ),
        (
            "rust/p28-slice-runner/src/lib.rs",
            include_bytes!("../../../../rust/p28-slice-runner/src/lib.rs"),
        ),
        (
            "rust/p28-slice-runner/src/operand.rs",
            include_bytes!("../../../../rust/p28-slice-runner/src/operand.rs"),
        ),
        (
            "rust/p28-slice-runner/src/full_decoder.rs",
            include_bytes!("../../../../rust/p28-slice-runner/src/full_decoder.rs"),
        ),
        (
            "rust/p28-slice-runner/src/runner.rs",
            include_bytes!("../../../../rust/p28-slice-runner/src/runner.rs"),
        ),
        (
            "rust/p28-slice-runner/Cargo.toml",
            include_bytes!("../../../../rust/p28-slice-runner/Cargo.toml"),
        ),
        (
            "rust/p28-slice-runner/Cargo.lock",
            include_bytes!("../../../../rust/p28-slice-runner/Cargo.lock"),
        ),
        (
            "rust/p28-slice-runner/src/protocol.rs",
            include_bytes!("../../../../rust/p28-slice-runner/src/protocol.rs"),
        ),
        (
            "rust/p28-slice-runner/src/main.rs",
            include_bytes!("../../../../rust/p28-slice-runner/src/main.rs"),
        ),
        (
            "research/p28-word0196/rust-production-optin-audit/Cargo.toml",
            include_bytes!("../Cargo.toml"),
        ),
        (
            "research/p28-word0196/rust-production-optin-audit/Cargo.lock",
            include_bytes!("../Cargo.lock"),
        ),
        (
            "research/p28-word0196/rust-production-optin-audit/src/main.rs",
            include_bytes!("main.rs"),
        ),
        (
            "research/p28-word0196/rust-production-optin-audit/src/capabilities.rs",
            include_bytes!("capabilities.rs"),
        ),
        (
            "research/p28-word0196/rust-production-optin-audit/closed_inputs.json",
            include_bytes!("../closed_inputs.json"),
        ),
    ];
    let bindings: Vec<_> = sources
        .iter()
        .map(
            |(path, bytes)| json!({"path":path,"bytes":bytes.len(),"sha256":sha256::digest(bytes)}),
        )
        .collect();
    json!({"kind":"optin_header","schema_version":1,"historical_exact_sha":HISTORICAL,
        "source_bindings":bindings,"closed_inputs_sha256":sha256::digest(include_bytes!("../closed_inputs.json")),
        "mechanism":"ProductionBusStrictDecoder_SharedExecuteDecoded_OneStepOnly",
        "feature":"p28-word0196-audit","default_enabled":false,
        "cpu_instances":0,"bus_instances":0,"actual_step_calls":0,
        "full_production_composite_executions":0,"original_rom_executions":0,"firmware_ready":false})
}

fn run() -> std::result::Result<(), Box<dyn std::error::Error>> {
    if std::env::args_os().len() != 1 {
        return Err("No payload/file/ROM arguments are allowed".into());
    }
    let mut input = io::stdin().lock();
    let mut output = io::BufWriter::new(io::stdout().lock());
    emit(&header(), &mut output)?;
    let mut positive = 0_u64;
    let mut refusals = 0_u64;
    let mut sweep = false;
    let mut caps = false;
    loop {
        let mut line = Vec::new();
        let n = (&mut input).take(131073).read_until(b'\n', &mut line)?;
        if n == 0 || line.len() > 131072 {
            return Err("Bounded complete input line/finish required".into());
        }
        let wire: Value = serde_json::from_slice(&line)?;
        let kind = wire
            .get("kind")
            .and_then(Value::as_str)
            .ok_or("Closed kind required")?;
        match kind {
            "case" | "admit" => {
                // Deserialize numeric DATA keys directly from native JSON;
                // never through serde's internally tagged Content buffer.
                #[derive(Deserialize)]
                #[serde(deny_unknown_fields)]
                struct Command {
                    kind: String,
                    input: ClosedInput,
                }
                let command: Command = match serde_json::from_slice(&line) {
                    Ok(command) => command,
                    Err(_schema_error) => {
                        refusals += 1;
                        emit(
                            &json!({"kind":"admission_refusal",
                            "case_id":wire.get("input").and_then(|v|v.get("request")).and_then(|v|v.get("case_id")).and_then(Value::as_str),
                            "accepted":false,"error":{"code":"MalformedRequest","detail":"closed typed input schema refused"},
                            "cpu_instances":0,"bus_instances":0,"actual_step_calls":0}),
                            &mut output,
                        )?;
                        continue;
                    }
                };
                let result = admit(&command.input);
                match result {
                    Err(error) => {
                        refusals += 1;
                        emit(
                            &json!({"kind":"admission_refusal","case_id":command.input.request.case_id,
                        "accepted":false,"error":error,"cpu_instances":0,"bus_instances":0,"actual_step_calls":0}),
                            &mut output,
                        )?;
                    }
                    Ok(permissions) if command.kind == "case" => {
                        let observed = execute(&command.input, permissions)
                            .map_err(|e| format!("{}:{}", e.code, e.detail))?;
                        let accepted = observed["accepted"] == true;
                        emit(&observed, &mut output)?;
                        if !accepted {
                            return Err(
                                "First unexpected positive failure recorded; stopping".into()
                            );
                        }
                        positive += 1;
                    }
                    Ok(_) => emit(
                        &json!({"kind":"admission_result","case_id":command.input.request.case_id,"accepted":true,
                        "cpu_instances":0,"bus_instances":0,"actual_step_calls":0}),
                        &mut output,
                    )?,
                }
            }
            "psw_sweep" => {
                if sweep || wire.as_object().map_or(0, |v| v.len()) != 1 {
                    return Err("One-shot closed PSW sweep".into());
                }
                let mut representable = 0;
                let mut bytes = Vec::new();
                for value in 0_u32..=65535 {
                    let full = value as u16;
                    let accepted = audit::validate_psw(full).is_ok();
                    if accepted != (full & 0x0cc8 == 0x0cc8) {
                        return Err("Admission mask disagreement".into());
                    }
                    representable += u64::from(accepted);
                    bytes.extend_from_slice(&full.to_le_bytes());
                    bytes.push(u8::from(accepted));
                }
                sweep = true;
                emit(
                    &json!({"kind":"psw_sweep","inputs":65536,"representable":representable,"incompatible":65536-representable,
                    "classification_sha256":sha256::digest(&bytes),"cpu_instances":0,"bus_instances":0,"actual_step_calls":0}),
                    &mut output,
                )?;
            }
            "capabilities" => {
                if caps || wire.as_object().map_or(0, |v| v.len()) != 1 {
                    return Err("One-shot closed capabilities".into());
                }
                emit(&capabilities::observe()?, &mut output)?;
                caps = true;
            }
            "finish" => {
                if wire.as_object().map_or(0, |v| v.len()) != 1 {
                    return Err("Finish forbids payload".into());
                }
                emit(
                    &json!({"kind":"optin_summary","positive_successful_steps":positive,"admission_refusals":refusals,
                    "positive_cpu_instances":positive,"positive_bus_instances":positive,"psw_sweep_observed":sweep,"capabilities_observed":caps,
                    "full_production_composite_executions":0,"original_rom_executions":0,"firmware_ready":false}),
                    &mut output,
                )?;
                break;
            }
            _ => {
                return Err("Unknown closed operation; arbitrary ROM/executor not admitted".into())
            }
        }
    }
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("M2BP_HARNESS_ERROR={error}");
        std::process::exit(1);
    }
}
