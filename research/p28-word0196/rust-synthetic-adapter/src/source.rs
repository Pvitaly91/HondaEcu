use crate::{sha256, AdapterError, Result, SOURCE_BINDINGS};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SourceBinding {
    pub path: String,
    pub bytes: usize,
    pub sha256: String,
}
const COMPILED_SOURCE: &[(&str, &str)] = &[
    (
        "cpu.rs",
        include_str!("../../../../rust/p28-slice-runner/src/cpu.rs"),
    ),
    (
        "bus.rs",
        include_str!("../../../../rust/p28-slice-runner/src/bus.rs"),
    ),
    (
        "decoder.rs",
        include_str!("../../../../rust/p28-slice-runner/src/decoder.rs"),
    ),
    (
        "full_decoder.rs",
        include_str!("../../../../rust/p28-slice-runner/src/full_decoder.rs"),
    ),
    (
        "exec.rs",
        include_str!("../../../../rust/p28-slice-runner/src/exec.rs"),
    ),
    (
        "runner.rs",
        include_str!("../../../../rust/p28-slice-runner/src/runner.rs"),
    ),
    (
        "operand.rs",
        include_str!("../../../../rust/p28-slice-runner/src/operand.rs"),
    ),
    (
        "lib.rs",
        include_str!("../../../../rust/p28-slice-runner/src/lib.rs"),
    ),
    (
        "Cargo.toml",
        include_str!("../../../../rust/p28-slice-runner/Cargo.toml"),
    ),
    (
        "protocol.rs",
        include_str!("../../../../rust/p28-slice-runner/src/protocol.rs"),
    ),
    (
        "main.rs",
        include_str!("../../../../rust/p28-slice-runner/src/main.rs"),
    ),
];
pub fn verify_binding(name: &str, text: &str, pin: &str) -> Result<SourceBinding> {
    let actual = sha256::digest(text.as_bytes());
    if actual != pin {
        return Err(AdapterError::new("SourceBindingMismatch", name));
    }
    Ok(SourceBinding {
        path: name.into(),
        bytes: text.len(),
        sha256: actual,
    })
}
pub fn verify_source_bindings() -> Result<Vec<SourceBinding>> {
    COMPILED_SOURCE
        .iter()
        .map(|(name, text)| {
            let pin = SOURCE_BINDINGS
                .iter()
                .find(|(n, _)| n == name)
                .ok_or_else(|| AdapterError::new("MissingSourceBinding", *name))?;
            verify_binding(name, text, pin.1)
        })
        .collect()
}
