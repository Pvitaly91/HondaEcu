//! Invented single-instruction parity probes of the unchanged production step.
//! This component is not a composite executor or a production admission change.
#![forbid(unsafe_code)]

pub mod admission;
pub mod capabilities;
pub mod execution;
pub mod source;
pub mod state;
#[cfg(test)]
mod tests;

use p28_research_synthetic_adapter::{entry::SyntheticCpuEntrySnapshot, AdapterError, FormId};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

pub type Result<T> = std::result::Result<T, AdapterError>;
pub const RAM_START: u16 = 0x0080;
pub const RAM_END: u16 = 0x1000;
pub const LOGICAL_PC: u16 = 0x1000;
pub const PHYSICAL_PC: u16 = 0;
pub const SCRATCH: u8 = 0xa5;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ProductionProbeRequest {
    pub case_id: String,
    pub fixture_id: String,
    pub family: String,
    pub form: FormId,
    pub bytes: Vec<u8>,
    pub guards: Vec<u8>,
    pub content_digest: String,
    pub expected_decoded_index: usize,
    pub expected_length: usize,
    pub entry: SyntheticCpuEntrySnapshot,
    pub data: BTreeMap<u16, u8>,
    pub internal_sf: bool,
    pub physical_entry_pc: u16,
    pub scratch: u8,
    pub budget: u8,
}

/// Counter values describe actual calls/instances, not contracts or expectations.
#[derive(Debug, Default, Clone, Serialize)]
pub struct RuntimeTotals {
    pub positive_cases: u64,
    pub positive_cpu_instances: u64,
    pub positive_bus_instances: u64,
    pub positive_step_calls: u64,
    pub positive_successful_step_calls: u64,
    pub positive_failed_step_calls: u64,
    pub positive_instruction_counter_delta: u64,
    pub capability_cases: u64,
    pub capability_cpu_instances: u64,
    pub capability_bus_instances: u64,
    pub capability_step_calls: u64,
    pub capability_successful_step_calls: u64,
    pub capability_failed_step_calls: u64,
    pub capability_instruction_counter_delta: u64,
    pub admission_refusals: u64,
    pub observed_decoded_forms: BTreeMap<String, u64>,
}
