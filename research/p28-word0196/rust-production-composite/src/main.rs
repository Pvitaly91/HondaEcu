//! M2bq source draft: closed continuous production execution, no ISA copy.
#![forbid(unsafe_code)]

// An immutable hashing utility only, not the old research effects interpreter.
mod capabilities;
#[path = "../../rust-synthetic-adapter/src/sha256.rs"]
mod sha256;

use p28_slice_runner::{
    audit::{self, ClosedCompositeProgram, CompositeEmissionMetadata, CompositeSeeds, Session},
    cpu::Cpu,
};
use serde::Deserialize;
use serde_json::{json, Value};
use std::{
    collections::BTreeMap,
    io::{self, BufRead, Read, Write},
    sync::OnceLock,
};

const COMPOSITE: &str = "91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1";
const POSITIVES: usize = 5470;

#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct PointingBank {
    x1: u16,
    x2: u16,
    dp: u16,
    usp: u16,
}

#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct Entry {
    pc: u16,
    a: u16,
    al: u8,
    ah: u8,
    psw: u16,
    cf: bool,
    zf: bool,
    hc: bool,
    dd: bool,
    other_psw: u16,
    lrb: u16,
    scb: u8,
    ssp: u16,
    pointing_banks: [PointingBank; 8],
    local_r: [u8; 8],
    local_er: [u16; 4],
    halted: bool,
    provenance: String,
    sf: Value,
}

#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct Case {
    kind: String,
    case_id: String,
    family: String,
    entry: Entry,
    data: BTreeMap<u16, u8>,
    path: String,
    internal_sf: bool,
    budget: u8,
}

#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct ProgramCommand {
    kind: String,
    dd0_bytes: Vec<u8>,
    dd1_bytes: Vec<u8>,
    metadata: CompositeEmissionMetadata,
}

fn closed_inputs() -> &'static [Value] {
    static INPUTS: OnceLock<Vec<Value>> = OnceLock::new();
    INPUTS.get_or_init(|| {
        serde_json::from_slice(include_bytes!("../closed_inputs.json"))
            .expect("pre-runtime source-bound immutable5470seed inputs")
    })
}

fn emit(output: &mut impl Write, record: &Value) -> io::Result<()> {
    serde_json::to_writer(&mut *output, record)?;
    output.write_all(b"\n")?;
    output.flush()
}

fn seed_cpu(entry: &Entry, sf: bool) -> Result<Cpu, Box<dyn std::error::Error>> {
    audit::validate_psw(entry.psw).map_err(|e| format!("{}:{}", e.code, e.detail))?;
    if entry.pc != 0x1000
        || entry.lrb != 0x0021
        || entry.scb != (entry.psw & 7) as u8
        || entry.a != (u16::from(entry.al) | (u16::from(entry.ah) << 8))
        || entry.other_psw != (entry.psw & 0x0fff)
        || entry.halted
        || entry.cf != (entry.psw & 0x8000 != 0)
        || entry.zf != (entry.psw & 0x4000 != 0)
        || entry.hc != (entry.psw & 0x2000 != 0)
        || entry.dd != (entry.psw & 0x1000 != 0)
        || entry.provenance != "InventedOnly_NoNativeGenerationOwner"
        || entry.sf
            != json!({"status":"SFMeaningStorageNotEstablished", "value":null,
            "meaning":null,"storage":null,"width_bits":null})
    {
        return Err("Closed canonical entry context rejected before Cpu construction".into());
    }
    // Exactly one actual Cpu value is created, after seed/context admission.
    // Every field is explicit; there is no copied instruction interpreter.
    Ok(Cpu {
        pc: entry.pc,
        a: entry.a,
        ssp: entry.ssp,
        lrb: entry.lrb,
        zf: entry.zf,
        cf: entry.cf,
        hc: entry.hc,
        dd: entry.dd,
        sf,
        psw_other: entry.psw & 0x0337,
        cycles: 0,
        instructions: 0,
        halted: entry.halted,
    })
}

fn session_for_case(
    program: &ClosedCompositeProgram,
    request: &Case,
    budget: u8,
) -> Result<Session, Box<dyn std::error::Error>> {
    let banks = std::array::from_fn(|index| {
        let bank = &request.entry.pointing_banks[index];
        [bank.x1, bank.x2, bank.dp, bank.usp]
    });
    let seeds = CompositeSeeds::new(
        request.data.clone(),
        banks,
        request.entry.local_r,
        request.entry.local_er,
    )
    .map_err(|e| format!("{}:{}", e.code, e.detail))?;
    let cpu = seed_cpu(&request.entry, request.internal_sf)?;
    Session::new_closed_composite(program, cpu, request.entry.psw, seeds, budget)
        .map_err(|e| format!("{}:{}", e.code, e.detail).into())
}

fn execute(
    program: &ClosedCompositeProgram,
    request: &Case,
) -> Result<Value, Box<dyn std::error::Error>> {
    if request.kind != "case" || request.budget != 16 {
        return Err("Closed positive case with exact16budget required".into());
    }
    let mut session = session_for_case(program, request, 16)?;
    let mut outcomes = 0_u64;
    let mut failure = None;
    let mut completed = false;
    for _ in 0..16 {
        match session.step_composite() {
            Ok(step) => {
                outcomes += 1;
                if step.outcome.external_exit.is_some() {
                    completed = true;
                    break;
                }
            }
            Err(error) => {
                failure = Some(error);
                break;
            }
        }
    }
    // Exactly one report call: its actual current diagnostic is part of the
    // frozen expected observation protocol. No additional snapshot calls.
    let report = session
        .composite_report()
        .map_err(|e| format!("{}:{}", e.code, e.detail))?;
    let full_completed = completed && report.completed;
    Ok(
        json!({"kind":"composite_observation","case_id":request.case_id,
        "family":request.family,"internal_sf":request.internal_sf,
        "accepted":failure.is_none() && completed && report.completed,
        "error":failure,"report":report,"actual_successful_step_returns":outcomes,
        "cpu_instances":1,"bus_instances":1,"data_initializations":1,
        "functional_transitions":1,"composite_execution_attempts":1,
        "full_production_composite_executions":u64::from(full_completed),
        "original_rom_executions":0,"firmware_ready":false}),
    )
}

fn source_header() -> Value {
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
            "rust/p28-slice-runner/src/full_decoder.rs",
            include_bytes!("../../../../rust/p28-slice-runner/src/full_decoder.rs"),
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
            "rust/p28-slice-runner/src/audit_composite.rs",
            include_bytes!("../../../../rust/p28-slice-runner/src/audit_composite.rs"),
        ),
        (
            "rust/p28-slice-runner/src/audit_composite_tests.rs",
            include_bytes!("../../../../rust/p28-slice-runner/src/audit_composite_tests.rs"),
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
            "rust/p28-slice-runner/src/runner.rs",
            include_bytes!("../../../../rust/p28-slice-runner/src/runner.rs"),
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
            "rust/p28-slice-runner/Cargo.toml",
            include_bytes!("../../../../rust/p28-slice-runner/Cargo.toml"),
        ),
        (
            "rust/p28-slice-runner/Cargo.lock",
            include_bytes!("../../../../rust/p28-slice-runner/Cargo.lock"),
        ),
        (
            "research/p28-word0196/rust-production-composite/Cargo.toml",
            include_bytes!("../Cargo.toml"),
        ),
        (
            "research/p28-word0196/rust-production-composite/Cargo.lock",
            include_bytes!("../Cargo.lock"),
        ),
        (
            "research/p28-word0196/rust-production-composite/src/main.rs",
            include_bytes!("main.rs"),
        ),
        (
            "research/p28-word0196/rust-production-composite/src/capabilities.rs",
            include_bytes!("capabilities.rs"),
        ),
        (
            "research/p28-word0196/rust-production-composite/closed_inputs.json",
            include_bytes!("../closed_inputs.json"),
        ),
        (
            "research/p28-word0196/rust-synthetic-adapter/src/sha256.rs",
            include_bytes!("../../rust-synthetic-adapter/src/sha256.rs"),
        ),
    ];
    let bindings: Vec<_> = sources
        .iter()
        .map(|(path, content)| {
            json!({"path":path,
        "bytes":content.len(),"sha256":sha256::digest(content)})
        })
        .collect();
    json!({"kind":"composite_header","schema_version":1,"exact_m2bp_base":"ecc32ea7b65020075f8403a4d4c81cdce4d0f0ad",
        "source_bindings":bindings,"closed_inputs_sha256":sha256::digest(include_bytes!("../closed_inputs.json")),
        "mechanism":"ContinuousProductionCpuBusStrictDecoderSharedExec_ClosedM2bj51Only",
        "feature":"p28-word0196-audit","default_enabled":false,"program_base":4096,
        "program_end_exclusive":4147,"program_sha256":COMPOSITE,"closed_positive_inputs":POSITIVES,"closed_smoke_inputs":4,
        "cpu_instances":0,"bus_instances":0,"original_rom_executions":0,"firmware_ready":false})
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    if std::env::args_os().len() != 1 {
        return Err("No path/file/ROM/executor arguments".into());
    }
    let mut input = io::stdin().lock();
    let mut output = io::BufWriter::new(io::stdout().lock());
    emit(&mut output, &source_header())?;
    let mut program = None;
    let mut program_command = None;
    let mut seen_sweep = false;
    let mut seen_capabilities = false;
    let mut negative_records = 0_usize;
    let mut positive = 0_usize;
    let mut smoke = 0_usize;
    let mut smoke_retired = 0_u64;
    let mut total_retired = 0_u64;
    loop {
        let mut line = Vec::new();
        let count = (&mut input).take(262145).read_until(b'\n', &mut line)?;
        if count == 0 || line.len() > 262144 {
            return Err("Bounded complete input line and finish required".into());
        }
        let wire: Value = serde_json::from_slice(&line)?;
        match wire
            .get("kind")
            .and_then(Value::as_str)
            .ok_or("Closed operation kind required")?
        {
            "program" => {
                if program.is_some() || positive != 0 {
                    return Err("One immutable program admission before all cases".into());
                }
                let request: ProgramCommand = serde_json::from_slice(&line)?;
                if request.kind != "program" {
                    return Err("Closed program kind".into());
                }
                program = Some(
                    ClosedCompositeProgram::admit_emission(
                        request.dd0_bytes.clone(),
                        request.dd1_bytes.clone(),
                        request.metadata.clone(),
                    )
                    .map_err(|e| format!("{}:{}", e.code, e.detail))?,
                );
                program_command = Some(request);
                emit(
                    &mut output,
                    &json!({"kind":"program_admission","accepted":true,"base":4096,
                    "end_exclusive":4147,"length":51,"nodes":20,"forms":16,"dd_streams_identical":true,
                    "sha256":COMPOSITE,"cpu_instances":0,"bus_instances":0,"original_rom_executions":0}),
                )?;
            }
            "psw_sweep" => {
                if seen_sweep || positive != 0 || wire != json!({"kind":"psw_sweep"}) {
                    return Err(
                        "Closed one-shot admission-only sweep before Cpu construction".into(),
                    );
                }
                let mut values = Vec::with_capacity(65536 * 3);
                let mut accepted = 0_u64;
                for value in 0_u32..=65535 {
                    let psw = value as u16;
                    let result = audit::validate_psw(psw).is_ok();
                    values.extend_from_slice(&psw.to_le_bytes());
                    values.push(u8::from(result));
                    accepted += u64::from(result);
                }
                seen_sweep = true;
                emit(
                    &mut output,
                    &json!({"kind":"psw_sweep","inputs":65536,"representable":accepted,
                    "incompatible":65536-accepted,"classification_sha256":sha256::digest(&values),
                    "cpu_instances":0,"bus_instances":0,"step_calls":0}),
                )?;
            }
            "smoke" => {
                #[derive(Deserialize)]
                #[serde(deny_unknown_fields)]
                struct Smoke {
                    kind: String,
                    input: Case,
                }
                if smoke >= 4 || positive != 0 || !seen_sweep {
                    return Err(
                        "Exactly four initial closed A/B/C/D smoke sessions before corpus".into(),
                    );
                }
                let path = ["A", "B", "C", "D"][smoke];
                let known = closed_inputs()
                    .iter()
                    .find(|row| row["path"] == path && row["internal_sf"] == false)
                    .ok_or("Frozen smoke seed missing")?;
                if wire.get("input") != Some(known) {
                    return Err("Exact next original smoke seed required".into());
                }
                let request: Smoke = serde_json::from_slice(&line)?;
                if request.kind != "smoke" {
                    return Err("Closed smoke kind".into());
                }
                let mut actual = execute(
                    program.as_ref().ok_or("Program admission before smoke")?,
                    &request.input,
                )?;
                actual["kind"] = json!("composite_smoke_observation");
                actual["smoke_index"] = json!(smoke + 1);
                let accepted = actual["accepted"] == true;
                smoke_retired += actual["actual_successful_step_returns"]
                    .as_u64()
                    .ok_or("Smoke retirement count")?;
                emit(&mut output, &actual)?;
                if !accepted {
                    return Err("First smoke failure retained; no corpus or retries".into());
                }
                smoke += 1;
            }
            "case" => {
                if positive >= POSITIVES
                    || smoke != 4
                    || !seen_sweep
                    || closed_inputs().get(positive) != Some(&wire)
                {
                    return Err(
                        "Exact next frozen seed required; no arbitrary state/input stream".into(),
                    );
                }
                let request: Case = serde_json::from_slice(&line)?;
                let actual = execute(
                    program.as_ref().ok_or("Program must be admitted first")?,
                    &request,
                )?;
                let accepted = actual["accepted"] == true;
                total_retired += actual["actual_successful_step_returns"]
                    .as_u64()
                    .ok_or("Retirement count")?;
                emit(&mut output, &actual)?;
                if !accepted {
                    return Err("First positive failure retained; no retry/continue".into());
                }
                positive += 1;
            }
            "capabilities" => {
                if wire != json!({"kind":"capabilities"})
                    || positive != POSITIVES
                    || seen_capabilities
                {
                    return Err(
                        "Closed one-shot negative controls after complete positive corpus".into(),
                    );
                }
                let records = capabilities::observe(
                    program.as_ref().ok_or("Admitted program required")?,
                    program_command
                        .as_ref()
                        .ok_or("Original ephemeral admitted command required")?,
                )?;
                negative_records = records.len();
                for record in records {
                    emit(&mut output, &record)?;
                }
                if negative_records != 33 {
                    return Err(
                        "Exact frozen33negative records required; partial actual records emitted"
                            .into(),
                    );
                }
                seen_capabilities = true;
            }
            "finish" => {
                if wire != json!({"kind":"finish"})
                    || positive != POSITIVES
                    || smoke != 4
                    || !seen_sweep
                    || program.is_none()
                    || !seen_capabilities
                {
                    return Err("Exact corpus, admission and complete finish required".into());
                }
                emit(
                    &mut output,
                    &json!({"kind":"composite_summary","positive_composite_executions":positive,
                    "positive_cpu_instances":positive,"positive_bus_instances":positive,"data_initializations":positive,
                    "functional_transitions":positive,"successful_retirements":total_retired,"program_admissions":1,
                    "smoke_composite_executions":smoke,"smoke_cpu_instances":smoke,"smoke_bus_instances":smoke,
                    "smoke_successful_retirements":smoke_retired,
                    "psw_admission_sweep":true,"negative_capabilities_observed":seen_capabilities,
                    "negative_records":negative_records,"original_rom_executions":0,"firmware_ready":false}),
                )?;
                break;
            }
            _ => return Err("Unknown operation; arbitrary CPU/ROM loading is not admitted".into()),
        }
    }
    Ok(())
}

fn main() {
    if let Err(error) = run() {
        eprintln!("M2BQ_HARNESS_ERROR={error}");
        std::process::exit(1);
    }
}
