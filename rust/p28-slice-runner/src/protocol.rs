use serde::{Deserialize, Serialize};

pub const PROTOCOL_VERSION: u32 = 1;
pub const UPSTREAM_COMMIT: &str = "85b30752473ca9979e4ad9b307ea05a30c0b3d1e";
pub const ADD_ASSUMPTION: &str = "oki.add-er3-a";
pub const PRODUCER_ADD_ASSUMPTION: &str = "oki.add-er1-a";

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Request {
    pub protocol_version: u32,
    pub operation: String,
    pub images: Vec<Image>,
    pub allow_assumptions: Vec<String>,
    pub scratch_patterns: Vec<u8>,
    pub synthetic: Option<SyntheticContract>,
    pub producer_cases: Option<Vec<[u32; 14]>>,
    pub acquisition_sequence: Option<crate::acquisition::SequenceRequest>,
    pub stateful_vtec: Option<crate::stateful::Stimulus>,
    pub integrated_chain: Option<crate::chain::Stimulus>,
    pub limiter_sequence: Option<crate::limiter::Stimulus>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Image {
    pub id: String,
    pub rom: Vec<u8>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct SyntheticContract {
    pub entry_pc: u16,
    pub exit_pcs: Vec<u16>,
    pub allowed_code_ranges: Vec<[u32; 2]>,
    pub psw: u16,
    pub lrb: u16,
    pub usp: u16,
    pub instruction_budget: u32,
    pub data_seeds: Vec<[u16; 2]>,
    pub output_addresses: Vec<u16>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Response {
    pub protocol_version: u32,
    pub operation: String,
    pub runner_version: &'static str,
    pub upstream_commit: &'static str,
    pub local_semantic_fixes: Vec<&'static str>,
    pub entry_contracts: Vec<serde_json::Value>,
    /// [pattern, raw, S, status, code, extraBit, assumptionUsed].
    pub compact_rows: Vec<[i32; 7]>,
    /// [image, pattern, code, context, priorBits, enabled, status, outputBits,
    ///  read0, read1, read2, read3]. -1 means absent read/output.
    pub threshold_rows: Vec<[i32; 12]>,
    pub diagnostics: Vec<Diagnostic>,
    pub synthetic_result: Option<CaseResult>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub producer_rows: Option<Vec<[i32; 22]>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub producer_threshold_rows: Option<Vec<[i32; 9]>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub checksum_cases: Option<Vec<crate::checksum::ChecksumCase>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub acquisition_sequences: Option<Vec<crate::acquisition::SequenceResult>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub stateful_sequences: Option<Vec<crate::stateful::SequenceResult>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub chain_sequences: Option<Vec<crate::chain::Sequence>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub limiter_sequences: Option<Vec<crate::limiter::Sequence>>,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct TraceEntry {
    pub pc: u16,
    pub next_pc: u16,
    pub instruction: String,
    pub psw: u16,
    pub accumulator: u16,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CaseResult {
    /// 0 completed, 1 unresolved instruction, 2 execution error, 3 budget exceeded.
    pub status: i32,
    pub used_assumptions: Vec<String>,
    pub steps: u32,
    pub stop_pc: u16,
    pub outputs: Vec<i32>,
    pub program_reads: Vec<u16>,
    pub trace: Vec<TraceEntry>,
    pub error: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub executed_instruction_bytes: Option<Vec<u16>>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Diagnostic {
    pub slice: &'static str,
    pub image_index: usize,
    pub inputs: Vec<i32>,
    pub result: CaseResult,
}

impl Response {
    pub fn new(operation: String) -> Self {
        Self {
            protocol_version: PROTOCOL_VERSION,
            operation,
            runner_version: env!("CARGO_PKG_VERSION"),
            upstream_commit: UPSTREAM_COMMIT,
            local_semantic_fixes: vec![
                "word-ror-through-carry-preserves-noncarry-flags",
                "load-zero-flag-and-dd-contract",
                "word-srl-preserves-noncarry-flags",
                "bit-operands-use-byte-access",
                "clr-accumulator-zero-flag",
                "jrnz-dpl-byte-count",
                "adcb-r0-immediate-half-carry",
                "inc-x1-half-carry",
                "indexed-alternate-immediate-displacement",
                "word-data-access-alignment",
                "byte-add-direct-accumulator-half-carry",
                "byte-add-r0-accumulator-half-carry",
                "inc-indexed-x2-half-carry",
                "word-sub-direct-updates-half-borrow",
                "byte-inc-direct-updates-half-carry",
                "byte-sll-accumulator-preserves-noncarry-flags",
                "byte-clear-accumulator-zero-flag",
                "stateful-exact-byte-add-sub-half-carry",
                "increment-dp-half-carry",
                "decrement-indexed-x1-byte-half-borrow",
            ],
            entry_contracts: vec![],
            compact_rows: vec![],
            threshold_rows: vec![],
            diagnostics: vec![],
            synthetic_result: None,
            producer_rows: None,
            producer_threshold_rows: None,
            checksum_cases: None,
            acquisition_sequences: None,
            stateful_sequences: None,
            chain_sequences: None,
            limiter_sequences: None,
        }
    }
}
