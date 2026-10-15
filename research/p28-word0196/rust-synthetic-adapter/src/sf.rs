use crate::{AdapterError, Result};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OpaqueSfBoundary {
    pub status: String,
    #[serde(deserialize_with = "required_nullable")]
    pub value: Option<bool>,
    #[serde(deserialize_with = "required_nullable")]
    pub meaning: Option<String>,
    #[serde(deserialize_with = "required_nullable")]
    pub storage: Option<String>,
    #[serde(deserialize_with = "required_nullable")]
    pub width_bits: Option<u16>,
}
fn required_nullable<'de, D, T>(deserializer: D) -> std::result::Result<Option<T>, D::Error>
where
    D: serde::Deserializer<'de>,
    T: Deserialize<'de>,
{
    Option::<T>::deserialize(deserializer)
}
/// Compare observed pairs without turning their internal test booleans into
/// native/architectural SF values. Empty/missing pairs cannot establish parity.
pub fn compare_microprobe_pair(
    left: &crate::executor::MicroObservation,
    right: &crate::executor::MicroObservation,
) -> Result<()> {
    if left.internal_sf_before
        || !right.internal_sf_before
        || left.internal_sf_after != left.internal_sf_before
        || right.internal_sf_after != right.internal_sf_before
        || left.retired_instructions != 1
        || right.retired_instructions != 1
    {
        return Err(AdapterError::new(
            "SfRuntimeCompatibilityNotEstablished",
            "explicit preserved false/true internal variants required",
        ));
    }
    let mut a = left.clone();
    let mut b = right.clone();
    a.internal_sf_before = false;
    a.internal_sf_after = false;
    b.internal_sf_before = false;
    b.internal_sf_after = false;
    if a != b {
        return Err(AdapterError::new(
            "SfRuntimeCompatibilityNotEstablished",
            "actual observed architecture/probes/DATA differ",
        ));
    }
    Ok(())
}
pub fn require_observed_pairs(
    pairs: &[(
        crate::executor::MicroObservation,
        crate::executor::MicroObservation,
    )],
) -> Result<()> {
    if pairs.is_empty() {
        return Err(AdapterError::new(
            "MissingSfIndependenceEvidence",
            "no runtime pairs supplied",
        ));
    }
    for (left, right) in pairs {
        compare_microprobe_pair(left, right)?;
    }
    Ok(())
}
impl OpaqueSfBoundary {
    pub fn validate(&self) -> Result<()> {
        if self.status != "SFMeaningStorageNotEstablished"
            || self.value.is_some()
            || self.meaning.is_some()
            || self.storage.is_some()
            || self.width_bits.is_some()
        {
            return Err(AdapterError::new(
                "SfUncertaintyRequired",
                "architectural SF remains opaque unknown",
            ));
        }
        Ok(())
    }
}
