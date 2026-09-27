//! Invented task requests/program fragments only, never OEM coverage.
use p28_slice_runner::runner::run_request;
use serde_json::{json, Value};
fn request() -> Value {
    let mut rom = vec![0u8; 32768];
    rom[0x1966..0x196E].copy_from_slice(&[0x62, 129, 0, 0x67, 90, 0, 0x47, 0x81]);
    let sources = json!({"source015a":20,"source015c":65535,"source015e":255,"source0160":65535,"source0162":65535,"source0164":255,"source0165":200,"source0166":0,"source0167":0,"source0168":255,"source0133":107,"source0142":0,"source0144":0,"source0146":0,"source0148":0,"source0149":0,"source014a":0,"source014c":0,"counter00f2":0});
    json!({"protocolVersion":1,"operation":"limiterFuelGateChain","images":[{"id":"baseline","rom":rom}],"scratchPatterns":[0,85,170],"allowAssumptions":[],"limiterFuelGateChain":{
        "formatVersion":1,"initialState":{"fuel":{"loadIndex":0,"map0RpmIndex":0,"map1RpmIndex":0,"loadFraction":0,"map0RpmFraction":0,"map1RpmFraction":0,"selector0127":165,"consumerFactor013f":0,"consumerOutput0140":0},"data0124":241,"data012b":173,"data01d7":7,"producerMode012c":16,"producerSelector012f":128,"hysteresis0130":165},"traceCallIndexes":[0],
        "calls":[{"index":0,"rawPeriod":89,"rawLoad":1,"rawMap0Rpm":2,"rawMap1Rpm":3,"sources":sources},{"index":1,"rawPeriod":129,"rawLoad":255,"rawMap0Rpm":255,"rawMap1Rpm":255,"sources":sources}]}})
}
#[test]
fn partial_decision_keeps_native_prefix_without_applying_next_event_or_mask_consumer() {
    let response =
        serde_json::to_value(run_request(serde_json::from_value(request()).unwrap()).unwrap())
            .unwrap();
    assert_eq!(response["runnerVersion"], env!("CARGO_PKG_VERSION"));
    for s in response["limiterFuelSequences"].as_array().unwrap() {
        let r = &s["checkpoints"];
        assert_eq!(r[0]["status"], 1);
        assert_eq!(r[0]["decision"]["result"]["steps"], 2);
        assert_eq!(r[0]["stateAfterDecision"]["data0124"], 241);
        assert_eq!(r[0]["stateAfterDecision"]["data012b"], 173);
        assert_eq!(
            r[0]["transitionToDecisionWrites"],
            json!([[2, 16, 32], [4, 16, 257], [142, 16, 640]])
        );
        assert_eq!(r[0]["inputWrites"].as_array().unwrap().len(), 23);
        assert_eq!(r[0]["fuel"]["status"], 4);
        assert_eq!(r[0]["fuel"]["factorProvenance"], "NotRun");
        assert!(r[0]["fuel"]["store03a2"].is_null());
        assert_eq!(r[1]["status"], 4);
        assert!(r[1]["input"].is_null());
        assert_eq!(r[1]["inputWrites"], json!([]));
        assert_eq!(r[1]["fuel"]["sourcesBefore"], r[1]["fuel"]["sourcesAfter"]);
        assert_eq!(r[0]["stateAfter"], r[1]["stateAfter"]);
        for access in r[0]["decisionAccesses"].as_array().unwrap() {
            assert_ne!(access[1], json!(0x18F));
            assert_ne!(access[1], json!(0x12A));
        }
    }
}
#[test]
fn closed_task_refuses_host_gates_ready_results_adaptive_inputs_and_disputed_permissions() {
    for i in 0..12 {
        let mut r = request();
        match i {
            0 => r["limiterFuelGateChain"]["calls"][0]["callerGate0124"] = json!(0),
            1 => r["limiterFuelGateChain"]["calls"][0]["channelMask"] = json!(255),
            2 => r["limiterFuelGateChain"]["calls"][0]["ramCut"] = json!(90),
            3 => r["limiterFuelGateChain"]["calls"][0]["sources"]["factor0158"] = json!(512),
            4 => r["limiterFuelGateChain"]["calls"][0]["sources"]["source0144"] = json!(256),
            5 => r["limiterFuelGateChain"]["initialState"]["data0121"] = json!(128),
            6 => r["limiterFuelGateChain"]["calls"][1]["index"] = json!(0),
            7 => r["allowAssumptions"] = json!(["oki.add-er3-a"]),
            8 => r["operation"] = json!("fuelFactorProductionChain"),
            9 => r["limiterFuelGateChain"]["traceCallIndexes"] = json!([0, 0]),
            10 => r["limiterFuelGateChain"]["formatVersion"] = json!(2),
            _ => r["limiterFuelGateChain"]["calls"][0]["p4Bit0"] = json!(true),
        }
        if let Ok(r) = serde_json::from_value(r) {
            assert!(run_request(r).is_err(), "case{i}");
        }
    }
}
