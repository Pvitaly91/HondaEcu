use p28_slice_runner::runner::run_request;
use serde_json::{json, Value};

fn request() -> Value {
    json!({
        "protocolVersion":1,"operation":"fuelMapLookup","images":[{"id":"baseline","rom":vec![0u8;32768]}],
        "scratchPatterns":[0,85,170],"allowAssumptions":[],
        "fuelMapLookup":{"formatVersion":1,
            "initialState":{"loadIndex":0,"map0RpmIndex":0,"map1RpmIndex":0,"loadFraction":0,"map0RpmFraction":0,
                "map1RpmFraction":0,"selector0127":0,"consumerFactor013f":17,"consumerOutput0140":1234},
            "calls":[
                {"index":0,"mapId":"map_0","rawLoad":1,"rawMap0Rpm":2,"rawMap1Rpm":3},
                {"index":1,"mapId":"map_1","rawLoad":4,"rawMap0Rpm":5,"rawMap1Rpm":6}
            ]}
    })
}

fn run(value: Value) -> Value {
    serde_json::to_value(run_request(serde_json::from_value(value).unwrap()).unwrap()).unwrap()
}

#[test]
fn unsupported_first_form_stops_sequence_and_leaves_suffix_null() {
    let response = run(request());
    assert_eq!(response["runnerVersion"], "0.15.0");
    for sequence in response["fuelMapSequences"].as_array().unwrap() {
        assert_eq!(sequence["checkpoints"][0]["status"], 1);
        assert!(sequence["checkpoints"][0]["loadAxis"].is_null());
        assert!(sequence["checkpoints"][0]["lookupResult"].is_null());
        assert_eq!(sequence["checkpoints"][1]["status"], 4);
        assert!(sequence["checkpoints"][1]["stateAfterInputs"].is_null());
        assert!(sequence["checkpoints"][1]["consumerOutput"].is_null());
    }
}

#[test]
fn request_is_closed_to_indices_ram_writes_and_permissions() {
    for case in 0..8 {
        let mut value = request();
        match case {
            0 => value["fuelMapLookup"]["calls"][0]["row"] = json!(1),
            1 => value["fuelMapLookup"]["calls"][0]["mapId"] = json!("map_2"),
            2 => value["fuelMapLookup"]["calls"][0]["index"] = json!(9),
            3 => value["fuelMapLookup"]["initialState"]["loadIndex"] = json!(9),
            4 => value["fuelMapLookup"]["initialState"]["selector0127"] = json!(128),
            5 => value["allowAssumptions"] = json!(["oki.add-er3-a"]),
            6 => value["scratchPatterns"] = json!([0]),
            _ => value["operation"] = json!("idleContexts"),
        }
        if let Ok(request) = serde_json::from_value(value) {
            assert!(run_request(request).is_err());
        }
    }
}
