//! Invented partial fragments and software-only admission probes, no OEM routine bytes.
use p28_slice_runner::runner::run_request;
use serde_json::{json, Value};

fn request() -> Value {
    let mut rom = vec![0u8; 32768];
    // Invented threshold store followed by a deliberate strict blocker.
    rom[0x487B..0x4882].copy_from_slice(&[0x67, 88, 0, 0xD3, 0x24, 0x47, 0x81]);
    let sources = json!({"source015a":20,"source015c":65535,"source015e":255,"source0160":65535,"source0162":65535,"source0164":255,"source0165":200,"source0166":0,"source0167":0,"source0168":255,"source0133":107,"source0142":0,"source0144":0,"source0146":0,"source0148":0,"source0149":0,"source014a":0,"source014c":0,"counter00f2":0});
    let call = |i| json!({"adaptive":{"fuel":{"index":i,"rawPeriod":99,"rawLoad":1,"rawMap0Rpm":2,"rawMap1Rpm":3,"sources":sources},"raw00ce":1100,"rawD9":0,"bank1":false,"reset217":true,"reset214":true,"mode212":false,"enable223":true,"fixedSource":false,"timerTicks":0,"counterTicks":0},"disable125":false,"disable12e":false});
    json!({"protocolVersion":1,"operation":"fuelPostStoreConsumerChain","images":[{"id":"baseline","rom":rom}],"scratchPatterns":[0,85,170],"allowAssumptions":[],"fuelPostStoreConsumerChain":{
        "formatVersion":1,"initialState":{"adaptive":{"joint":{"fuel":{"loadIndex":0,"map0RpmIndex":0,"map1RpmIndex":0,"loadFraction":0,"map0RpmFraction":0,"map1RpmFraction":0,"selector0127":165,"consumerFactor013f":0,"consumerOutput0140":0},"data0124":241,"data012b":173,"data01d7":7,"producerMode012c":149,"producerSelector012f":128,"hysteresis0130":165},"ramCut":100,"ramResume":110,"timer":7,"counter":5,"ie":42330,"restoreIe":23205},"previous03b4":321},"traceCallIndexes":[0],"calls":[call(0),call(1)]}})
}

#[test]
fn incomplete_prefix_is_preserved_and_consumer_and_later_events_are_terminal_not_run() {
    let r = serde_json::to_value(run_request(serde_json::from_value(request()).unwrap()).unwrap())
        .unwrap();
    assert_eq!(r["runnerVersion"], env!("CARGO_PKG_VERSION"));
    assert!(r.get("postStoreSequences").is_none());
    for s in r["consumerSequences"].as_array().unwrap() {
        let a = &s["checkpoints"][0];
        let b = &s["checkpoints"][1];
        assert_eq!(a["status"], 1);
        assert_eq!(a["prefix"]["status"], 1);
        assert_eq!(a["prefix"]["prefix"]["stateAfter"]["ramCut"], 88);
        assert!(a["consumer"].is_null());
        assert!(a["selectedScaledWordX1"].is_null());
        assert!(a["retainedOrZeroA"].is_null());
        assert_eq!(a["mode012cBefore"], 149);
        assert_eq!(a["mode012cAfter"], 149);
        assert_eq!(a["word0150Before"], 0);
        assert_eq!(a["word0150After"], 0);
        assert_eq!(b["status"], 4);
        assert_eq!(b["prefix"]["status"], 4);
        assert_eq!(b["prefix"]["snapshotWrites"], json!([]));
        assert_eq!(b["prefix"]["prefix"]["snapshotWrites"], json!([]));
        assert!(b["consumer"].is_null());
        assert!(b["selectedScaledWordX1"].is_null());
        assert!(b["retainedOrZeroA"].is_null());
        assert_eq!(b["mode012cBefore"], a["mode012cAfter"]);
        assert_eq!(b["mode012cBefore"], b["mode012cAfter"]);
        assert_eq!(b["word0150Before"], a["word0150After"]);
        assert_eq!(b["word0150Before"], b["word0150After"]);
    }
}

#[test]
fn consumer_task_rejects_foreign_stimulus_and_ready_outputs_and_out_of_bounds_events() {
    for i in 0..13 {
        let mut r = request();
        let s = "fuelPostStoreConsumerChain";
        match i {
            0 => r["fuelPostStoreChain"] = r[s].clone(),
            1 => r[s]["calls"][0]["word0150"] = json!(500),
            2 => r[s]["calls"][0]["mode012cBit5"] = json!(true),
            3 => r[s]["calls"][0]["selectedScaledWordX1"] = json!(500),
            4 => r[s]["calls"][0]["helperResult"] = json!(500),
            5 => r[s]["calls"][0]["branchChoice"] = json!(true),
            6 => r[s]["calls"][0]["adaptive"]["timerTicks"] = json!(33),
            7 => r[s]["calls"][1]["adaptive"]["fuel"]["index"] = json!(0),
            8 => r[s]["formatVersion"] = json!(2),
            9 => r["operation"] = json!("fuelPostStoreChain"),
            10 => r["images"][0]["rom"][0x60F8] = json!(1),
            11 => r["allowAssumptions"] = json!(["oki.add-er3-a"]),
            _ => r[s]["traceCallIndexes"] = json!([0, 0]),
        }
        if let Ok(r) = serde_json::from_value(r) {
            assert!(run_request(r).is_err(), "case{i}");
        }
    }
}
