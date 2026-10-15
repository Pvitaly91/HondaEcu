//! Isolated invented one-instruction research probes. Never a composite runner.
#![forbid(unsafe_code)]

pub mod admission;
#[cfg(test)]
mod component_tests;
pub mod data;
pub mod entry;
pub mod executor;
pub mod exit;
pub mod fetch;
pub mod program;
pub mod psw;
pub mod sf;
pub mod sha256;
pub mod source;

pub use admission::FormId;
pub use data::DataPath;
pub use entry::{PointingBank, SyntheticCpuEntrySnapshot};
pub use executor::{run_microprobe, MicroObservation, ProbeRequest};
use serde::{Deserialize, Serialize};

pub const INVENTED_PROVENANCE: &str = "InventedOnly_NoNativeGenerationOwner";
pub const UPSTREAM_DIGEST: &str =
    "91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1";
pub const UPSTREAM_SOURCE: &str = "M2bjVerifiedSyntheticComposite_20Nodes_51Bytes";
pub const MANUAL_SHA: &str = "f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271";

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AdapterError {
    pub code: String,
    pub detail: String,
}
impl AdapterError {
    pub fn new(code: &str, detail: impl Into<String>) -> Self {
        Self {
            code: code.into(),
            detail: detail.into(),
        }
    }
}
impl std::fmt::Display for AdapterError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}: {}", self.code, self.detail)
    }
}
impl std::error::Error for AdapterError {}
pub type Result<T> = std::result::Result<T, AdapterError>;

/// Freshly checked source identities, not a claim of execution equivalence.
pub const SOURCE_BINDINGS: &[(&str, &str)] = &[
    (
        "cpu.rs",
        "b12a0b3388a7d34201888a0a6f948263dcf1c7bebca1801056e176d871184d3b",
    ),
    (
        "bus.rs",
        "556dceff088ecdfac7f05469a03251896c81fdb1979394bdbae4c59e1b30445a",
    ),
    (
        "decoder.rs",
        "1120cc37cee9ec23f1f596c72ff8dd5bf372204495d2b5e00cc044dfe2ea3aa4",
    ),
    (
        "full_decoder.rs",
        "77697d4b0e3c90372326156bf1a8544486d07f4aa8f93c67cf9e5f2af6c7eff1",
    ),
    (
        "exec.rs",
        "e7ef7d04fb28c838b20c52f352c89fc7ea8780d5a2e1d19f7178dec5109324aa",
    ),
    (
        "runner.rs",
        "c93026e5d1152bdb8196d9a67a6dc071fd704000351b13db668eab1bff255727",
    ),
    (
        "operand.rs",
        "c3e7b418b81b4fa0becfa2ec2be741a4b0929994831ebb89e829698d289bb48f",
    ),
    (
        "lib.rs",
        "80b141f1d2e17852ab4691515d645245881bd2fad30dd94a795f5d22aee3e376",
    ),
    (
        "Cargo.toml",
        "62a898777d81271760d1adb88b38cc021170b84872b14791a97028989fcb82ff",
    ),
    (
        "protocol.rs",
        "2be02025de40df2336e3c442a68924d98539ecc57147317b01808200c42a023c",
    ),
    (
        "main.rs",
        "be5a42edf56fa9cdd798b865b8cd81b8c602be329ca9fadc49f6865535ab561f",
    ),
];
