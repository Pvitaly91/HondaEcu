//! Actual compiled source bytes, with immutable upstream verification.
use crate::Result;
use p28_research_synthetic_adapter::{
    sha256,
    source::{verify_source_bindings, SourceBinding},
};
use serde::Serialize;

const RESEARCH_SOURCES: &[(&str, &[u8])] = &[
    ("Cargo.toml", include_bytes!("../Cargo.toml")),
    ("Cargo.lock", include_bytes!("../Cargo.lock")),
    ("src/lib.rs", include_bytes!("lib.rs")),
    ("src/admission.rs", include_bytes!("admission.rs")),
    ("src/state.rs", include_bytes!("state.rs")),
    ("src/execution.rs", include_bytes!("execution.rs")),
    ("src/capabilities.rs", include_bytes!("capabilities.rs")),
    ("src/source.rs", include_bytes!("source.rs")),
    ("src/main.rs", include_bytes!("main.rs")),
    ("src/tests.rs", include_bytes!("tests.rs")),
];

#[derive(Debug, Serialize)]
pub struct SourceHeader {
    pub kind: &'static str,
    pub schema_version: u32,
    pub scope: &'static str,
    pub production_source_bindings: Vec<SourceBinding>,
    pub research_source_bindings: Vec<SourceBinding>,
    pub sealed_m2bm_fixture_sha256: String,
    pub production_execution: &'static str,
    pub research_effects_called: bool,
    pub cpu_instances: u64,
    pub bus_instances: u64,
    pub production_step_calls: u64,
    pub production_bus_composite_integration: &'static str,
    pub original_rom_executions: u64,
    pub firmware_ready: bool,
}

pub fn header() -> Result<SourceHeader> {
    Ok(SourceHeader {
        kind: "production_header",
        schema_version: 1,
        scope: "ResearchOnly_ProductionExecSingleStep_NotComposite",
        production_source_bindings: verify_source_bindings()?,
        research_source_bindings: RESEARCH_SOURCES
            .iter()
            .map(|(path, bytes)| SourceBinding {
                path: (*path).into(),
                bytes: bytes.len(),
                sha256: sha256::digest(bytes),
            })
            .collect(),
        sealed_m2bm_fixture_sha256: sha256::digest(include_bytes!(
            "../../rust-synthetic-adapter/tests/fixtures/microprobe_expectations.json"
        )),
        production_execution: "Unchanged_p28_slice_runner::exec::step",
        research_effects_called: false,
        cpu_instances: 0,
        bus_instances: 0,
        production_step_calls: 0,
        production_bus_composite_integration: "NotEstablished",
        original_rom_executions: 0,
        firmware_ready: false,
    })
}
