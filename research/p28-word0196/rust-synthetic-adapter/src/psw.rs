use crate::{AdapterError, Result};
use p28_slice_runner::cpu::Cpu;
use serde::{Deserialize, Serialize};

pub const READS_ONE: u16 = 0x0cc8;
pub const STORAGE: u16 = 0x0337;
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PswClassification {
    pub original_expected: u16,
    pub canonical_observed: u16,
    pub representable: bool,
    pub classification: String,
}
pub struct CanonicalPswBridge;
impl CanonicalPswBridge {
    pub fn is_representable(input: u16) -> bool {
        input & READS_ONE == READS_ONE
    }
    pub fn set_checked(cpu: &mut Cpu, input: u16) -> Result<()> {
        if !Self::is_representable(input) {
            return Err(AdapterError::new(
                "NotRepresentableByCurrentCanonicalRustCpu",
                format!("lossless expected {input:04X}"),
            ));
        }
        cpu.set_psw_u16(input);
        if cpu.psw_u16() != input {
            return Err(AdapterError::new(
                "PswBridgeMismatch",
                "canonical round trip",
            ));
        }
        Ok(())
    }
    /// Calls the unchanged Cpu methods; this intentionally records normalization
    /// separately from the untouched expected descriptor for exhaustive QA.
    pub fn observe_raw(cpu: &mut Cpu, input: u16) -> PswClassification {
        cpu.set_psw_u16(input);
        let canonical_observed = cpu.psw_u16();
        let representable = canonical_observed == input;
        PswClassification {
            original_expected: input,
            canonical_observed,
            representable,
            classification: if representable {
                "Representable"
            } else {
                "NotRepresentableByCurrentCanonicalRustCpu"
            }
            .into(),
        }
    }
}
