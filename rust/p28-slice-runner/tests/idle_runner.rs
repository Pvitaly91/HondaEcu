use p28_slice_runner::runner::run_request;
use serde_json::{json, Value};
fn request() -> Value {
    let mut rom = vec![0u8; 32768];
    // Invented increment producer and copy consumer, not recovered firmware.
    rom[0x2FD1..0x2FDB].copy_from_slice(&[0xE4, 0x5C, 0x86, 1, 0, 0xD4, 0x5C, 0x03, 0xAB, 0x30]);
    rom[0x9DC..0x9E3].copy_from_slice(&[0xE4, 0x5C, 0xD5, 0xCA, 0x03, 0xF4, 0x09]);
    json!({"protocolVersion":1,"operation":"idleTarget","images":[{"id":"baseline","rom":rom}],"scratchPatterns":[0,85,170],"allowAssumptions":[],
    "idleTarget":{"formatVersion":1,"initialState":{"target":100,"raw027a":999,"errorMagnitude":77,"data021a":161},"calls":[{"index":0,"rawD9":52,"rawPeriod":1000},{"index":1,"rawD9":255,"rawPeriod":1000},{"index":2,"rawD9":100,"rawPeriod":1000}]}})
}
fn run(v: Value) -> Value {
    serde_json::to_value(run_request(serde_json::from_value(v).unwrap()).unwrap()).unwrap()
}
#[test]
fn native_target_handoff_and_history_on_one_machine() {
    let r = run(request());
    for s in r["idleSequences"].as_array().unwrap() {
        for (i, c) in s["checkpoints"].as_array().unwrap().iter().enumerate() {
            assert_eq!(c["status"], 0);
            assert_eq!(c["actualTarget"], 101 + i);
            assert_eq!(c["actualError"], 101 + i);
            assert_eq!(c["stateBefore"]["target"], 100 + i);
            assert_eq!(c["stateAfter"]["raw027a"], 999);
            assert_eq!(c["stateAfter"]["data021a"], 161);
        }
    }
}
#[test]
fn unsupported_and_budget_stops_have_no_suffix_outputs() {
    for loop_forever in [false, true] {
        let mut v = request();
        let bytes = if loop_forever {
            vec![0x03, 0xD1, 0x2F]
        } else {
            vec![0x45, 0x81, 0]
        };
        for (i, b) in bytes.iter().enumerate() {
            v["images"][0]["rom"][0x2FD1 + i] = json!(b);
        }
        let r = run(v);
        for s in r["idleSequences"].as_array().unwrap() {
            assert_eq!(
                s["checkpoints"][0]["status"],
                if loop_forever { 3 } else { 1 }
            );
            assert!(s["checkpoints"][0]["actualTarget"].is_null());
            assert!(s["checkpoints"][0]["consumer"].is_null());
            assert_eq!(s["checkpoints"][1]["status"], 4);
            assert!(s["checkpoints"][1]["actualError"].is_null());
        }
    }
}
#[test]
fn closed_context_never_accepts_per_call_internal_state_or_permissions() {
    for case in 0..7 {
        let mut v = request();
        match case {
            0 => v["idleTarget"]["calls"][0]["target"] = json!(1),
            1 => v["idleTarget"]["calls"][0]["rawD9"] = json!(51),
            2 => v["idleTarget"]["initialState"]["data021a"] = json!(0),
            3 => v["allowAssumptions"] = json!(["oki.add-er1-a"]),
            4 => v["idleTarget"]["calls"][0]["index"] = json!(9),
            5 => v["operation"] = json!("adaptiveLimiter"),
            _ => v["scratchPatterns"] = json!([0]),
        };
        if let Ok(r) = serde_json::from_value(v) {
            assert!(run_request(r).is_err());
        }
    }
}
