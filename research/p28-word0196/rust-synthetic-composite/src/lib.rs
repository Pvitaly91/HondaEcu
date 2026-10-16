//! M2bn-only continuous invented composite experiment. Never production Bus/exec.
#![forbid(unsafe_code)]

pub mod component_checks;
mod effects;
pub mod execution;
pub mod lifecycle;
pub mod observer;
pub mod program;

pub use p28_research_synthetic_adapter::{AdapterError, Result};

pub const SCOPE: &str = "CpuStateAndProductionDecoderWithResearch16FormExecutor";
pub const BASE: u16 = 0x1000;
pub const END_EXCLUSIVE: u16 = 0x1033;
pub const HARD_BUDGET: u8 = 16;
pub const EFFECT_SOURCE_SHA256: &str =
    "a1bb8e708177598259087d53774f72fa656ca36e67ac7f16f532ca1baa2d10c3";

/// Compare both transplanted function bodies before any new composite execution.
pub fn verify_effect_copy() -> Result<()> {
    use p28_research_synthetic_adapter::sha256::digest;
    let original = include_str!("../../rust-synthetic-adapter/src/executor.rs");
    let copied = include_str!("effects.rs");
    if digest(original.as_bytes()) != EFFECT_SOURCE_SHA256 {
        return Err(AdapterError::new(
            "EffectSourceBindingMismatch",
            "frozen M2bm source",
        ));
    }
    let original_tail = original
        .split_once("fn execute_one(")
        .ok_or_else(|| AdapterError::new("MissingEffectBody", "source"))?
        .1;
    let copied_tail = copied
        .split_once("fn execute_one(")
        .ok_or_else(|| AdapterError::new("MissingEffectBody", "new research component"))?
        .1;
    if original_tail.trim_end() != copied_tail.trim_end() {
        return Err(AdapterError::new(
            "EffectSemanticBodyChanged",
            "execute_one and relative tails",
        ));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    #[test]
    fn frozen_semantic_effect_bodies_are_identical() {
        super::verify_effect_copy().unwrap();
    }
}
