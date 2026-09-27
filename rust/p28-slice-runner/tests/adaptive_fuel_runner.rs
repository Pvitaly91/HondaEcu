//! Independently invented fragments, never an OEM adaptive helper fixture.
use p28_slice_runner::runner::run_request;
use serde_json::{json, Value};
fn request() -> Value {
    let mut rom = vec![0u8; 32768];
    // Only one threshold is written before an unresolved exact form.
    rom[0x487B..0x4882].copy_from_slice(&[0x67, 88, 0, 0xD3, 0x24, 0x47, 0x81]);
    let sources = json!({"source015a":20,"source015c":65535,"source015e":255,"source0160":65535,"source0162":65535,"source0164":255,"source0165":200,"source0166":0,"source0167":0,"source0168":255,"source0133":107,"source0142":0,"source0144":0,"source0146":0,"source0148":0,"source0149":0,"source014a":0,"source014c":0,"counter00f2":0});
    let call = |i, bank| json!({"fuel":{"index":i,"rawPeriod":99,"rawLoad":1,"rawMap0Rpm":2,"rawMap1Rpm":3,"sources":sources},"raw00ce":1100,"rawD9":0,"bank1":bank,"reset217":true,"reset214":true,"mode212":false,"enable223":true,"fixedSource":false,"timerTicks":0,"counterTicks":0});
    json!({"protocolVersion":1,"operation":"adaptiveLimiterFuelGateChain","images":[{"id":"baseline","rom":rom}],"scratchPatterns":[0,85,170],"allowAssumptions":[],"adaptiveLimiterFuelGateChain":{
        "formatVersion":1,"initialState":{"joint":{"fuel":{"loadIndex":0,"map0RpmIndex":0,"map1RpmIndex":0,"loadFraction":0,"map0RpmFraction":0,"map1RpmFraction":0,"selector0127":165,"consumerFactor013f":0,"consumerOutput0140":0},"data0124":241,"data012b":173,"data01d7":7,"producerMode012c":16,"producerSelector012f":128,"hysteresis0130":165},"ramCut":100,"ramResume":110,"timer":7,"counter":5,"ie":42330,"restoreIe":23205},"traceCallIndexes":[0],"calls":[call(0,true),call(1,false)]}})
}
#[test]
fn partial_threshold_pair_never_runs_decision_or_fuel_or_next_snapshots() {
    let r = serde_json::to_value(run_request(serde_json::from_value(request()).unwrap()).unwrap())
        .unwrap();
    assert_eq!(r["runnerVersion"], env!("CARGO_PKG_VERSION"));
    for seq in r["adaptiveFuelSequences"].as_array().unwrap() {
        let a = &seq["checkpoints"][0];
        let b = &seq["checkpoints"][1];
        assert_eq!(a["status"], 1);
        assert_eq!(a["stateAfter"]["ramCut"], 88);
        assert_eq!(a["stateAfter"]["ramResume"], 110);
        assert_eq!(a["stateAfter"]["ie"], 42330);
        assert_eq!(a["stateAfter"]["timer"], 7);
        assert!(a["joint"]["decision"].is_null());
        assert!(a["joint"]["fuel"]["store03a2"].is_null());
        assert_eq!(a["joint"]["transitionToDecisionWrites"], json!([]));
        assert_eq!(b["status"], 4);
        assert!(b["input"].is_null());
        assert_eq!(b["snapshotWrites"], json!([]));
        assert_eq!(b["stateBefore"], a["stateAfter"]);
        assert_eq!(b["stateBefore"], b["stateAfter"]);
        let before = a["stateBefore"]["sources"].as_array().unwrap();
        let after = a["stateAfter"]["sources"].as_array().unwrap();
        for (i, mask) in [2u64, 32, 1, 32, 4, 128].into_iter().enumerate() {
            assert_eq!(
                before[i].as_u64().unwrap() & !mask,
                after[i].as_u64().unwrap() & !mask
            );
        }
        assert_eq!(a["producer"]["entry"]["lrb"], 65);
        assert_eq!(a["producer"]["entry"]["usp"], 384);
        assert_eq!(a["producer"]["exit"]["ssp"], 2046);
    }
}
#[test]
fn first_tick_failure_stops_both_tick_targets_producer_and_fuel() {
    let mut req = request();
    req["images"][0]["rom"][0x5BD0] = json!(0x47);
    req["images"][0]["rom"][0x5BD1] = json!(0x81);
    req["adaptiveLimiterFuelGateChain"]["calls"][0]["timerTicks"] = json!(2);
    req["adaptiveLimiterFuelGateChain"]["calls"][0]["counterTicks"] = json!(3);
    let r =
        serde_json::to_value(run_request(serde_json::from_value(req).unwrap()).unwrap()).unwrap();
    for s in r["adaptiveFuelSequences"].as_array().unwrap() {
        let a = &s["checkpoints"][0];
        assert_eq!(a["status"], 1);
        assert_eq!(a["ticks"].as_array().unwrap().len(), 1);
        assert_eq!(a["ticks"][0]["tickTarget"], 0x1D5);
        assert!(a["producer"].is_null());
        assert!(a["stateAfterProducer"].is_null());
        assert_eq!(a["stateAfter"]["timer"], 7);
        assert_eq!(
            a["ticks"][0]["transitionWrites"],
            json!([[2, 16, 65], [4, 16, 1], [142, 16, 384], [136, 16, 469]])
        );
    }
}
#[test]
fn bounded_task_rejects_injections_versions_conflicting_domains_and_old_operations() {
    for i in 0..14 {
        let mut r = request();
        let s = "adaptiveLimiterFuelGateChain";
        match i {
            0 => r[s]["calls"][0]["ramCut"] = json!(100),
            1 => r[s]["calls"][0]["request"] = json!(true),
            2 => r[s]["calls"][0]["data021f"] = json!(2),
            3 => r[s]["calls"][0]["context"] = json!("RAM"),
            4 => r[s]["calls"][0]["fuel"]["sources"]["factor0158"] = json!(512),
            5 => r[s]["calls"][0]["timerTicks"] = json!(33),
            6 => {
                r[s]["calls"][0]["timerTicks"] = json!(20);
                r[s]["calls"][0]["counterTicks"] = json!(13);
            }
            7 => r[s]["calls"][0]["tickAddress"] = json!(0x1D7),
            8 => r[s]["calls"][1]["fuel"]["index"] = json!(0),
            9 => r[s]["formatVersion"] = json!(2),
            10 => r["operation"] = json!("adaptiveLimiter"),
            11 => r["allowAssumptions"] = json!(["oki.add-er1-a"]),
            12 => r[s]["traceCallIndexes"] = json!([0, 0]),
            _ => r[s]["calls"][0]["p4Bit0"] = json!(true),
        }
        if let Ok(r) = serde_json::from_value(r) {
            assert!(run_request(r).is_err(), "case{i}");
        }
    }
}
