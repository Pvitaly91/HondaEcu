//! M2t evidence hardening. Primary JGT conflict is NOT resolved by a version bump.
use crate::{
    common_result_consumer as common,
    protocol::{Request, Response},
};

pub fn validate_request(r: &Request) -> Result<(), String> {
    if r.fuel_common_result_consumer_chain.is_some() {
        return Err("Historical M2s stimulus cannot be relabeled M2t".into());
    }
    common::validate_parts(
        r,
        r.fuel_division_decision_chain
            .as_ref()
            .ok_or("M2t stimulus required")?,
    )
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    let mut c = common::entry_contracts();
    c[0]["id"] = serde_json::json!("fuelDivisionDecisionChain");
    c[0]["isaClosure"] = serde_json::json!("Blocked;PrimaryJgtConditionConflict;StopBefore233A");
    c[0]["jgtPredicate"] = serde_json::Value::Null;
    c[0]["positiveDivisorPolicy"] =
        serde_json::json!("NativeDIVAndCMPOnly;NoJgtDecisionOrFreshCalculationOutput");
    c
}
pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r.fuel_division_decision_chain.as_ref().expect("validated");
    // Shared execution primitive, not M2s JSON->RAM. One CPU/RAM, literal22B1,
    // once-only sources and same terminal policy; no new host entry or admission.
    response.division_decision_sequences = Some(common::run_sequences(
        &r.images[0].rom,
        &r.scratch_patterns,
        s,
    ));
    response.entry_contracts = entry_contracts();
    Ok(response)
}
