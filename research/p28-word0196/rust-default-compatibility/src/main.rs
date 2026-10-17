//! One frozen-input microprobe process; all effects stay in production exec::step.
//! This does not invoke historical source-pin validators on a changed source tree.
#![forbid(unsafe_code)]

use p28_research_production_exec_parity::{
    capabilities, execution, ProductionProbeRequest, RuntimeTotals,
};
use serde::Deserialize;
use std::io::{self, BufRead, Write};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Envelope {
    kind: String,
    request: Option<ProductionProbeRequest>,
}

fn emit(value: &impl serde::Serialize, output: &mut impl Write) -> io::Result<()> {
    serde_json::to_writer(&mut *output, value)?;
    output.write_all(b"\n")?;
    output.flush()
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut output = io::BufWriter::new(io::stdout().lock());
    // Actual compiled production identity constructor, not a supplied fixture result.
    emit(
        &serde_json::json!({
            "kind":"default_compatibility_identity",
            "mechanism":"UnchangedHistoricalProbeLibrary_CallsProductionExecStep",
            "identity":p28_slice_runner::protocol::Response::new("synthetic".into()),
            "cpu_instances":0,"production_step_calls":0,
            "historical_validator_pass_on_active_tree_claimed":false
        }),
        &mut output,
    )?;
    let mut totals = RuntimeTotals::default();
    for line in io::stdin().lock().lines() {
        let line = line?;
        if line.len() > 1024 * 1024 {
            return Err("bounded frozen request exceeded".into());
        }
        // Parse the numeric-key DATA map directly; no internally-tagged serde buffer.
        let command: Envelope = serde_json::from_str(&line)?;
        match (command.kind.as_str(), command.request) {
            ("micro", Some(request)) => {
                let result = execution::execute(&request, &mut totals)?;
                let succeeded = result.accepted;
                emit(&result, &mut output)?;
                if !succeeded {
                    return Err("frozen positive step failed; actual record emitted".into());
                }
            }
            ("capabilities", Some(request)) => {
                emit(
                    &serde_json::json!({"kind":"capability_observations",
                        "records":capabilities::observe(&request,&mut totals)?}),
                    &mut output,
                )?;
            }
            ("finish", None) => {
                emit(
                    &serde_json::json!({"kind":"default_compatibility_summary","totals":totals,
                        "production_composite_executions":0,"original_rom_executions":0,
                        "firmware_ready":false}),
                    &mut output,
                )?;
                return Ok(());
            }
            _ => return Err("closed micro/capabilities/finish command required".into()),
        }
    }
    Err("explicit finish required".into())
}

fn main() {
    if let Err(error) = run() {
        eprintln!("default compatibility probe failed: {error}");
        std::process::exit(2);
    }
}
