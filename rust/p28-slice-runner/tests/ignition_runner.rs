use p28_slice_runner::runner::run_request;
use serde_json::{json, Value};
use std::io::Write;
use std::process::{Command, Stdio};

fn request() -> Value {
    json!({
        "protocolVersion":1,"operation":"ignitionMapLookup","images":[{"id":"baseline","rom":vec![0u8;32768]}],
        "scratchPatterns":[0,85,170],"allowAssumptions":[],
        "ignitionMapLookup":{"formatVersion":1,
            "initialState":{"loadIndex":0,"map0RpmIndex":0,"map1RpmIndex":0,"loadFraction":0,
                "map0RpmFraction":0,"map1RpmFraction":0,"selector0227":0,
                "consumerFactor0247":0,"consumerOutput0248":123},
            "calls":[
                {"index":0,"mapId":"ignition_map_0","rawLoad":1,"rawMap0Rpm":2,"rawMap1Rpm":3},
                {"index":1,"mapId":"ignition_map_1","rawLoad":4,"rawMap0Rpm":5,"rawMap1Rpm":6}
            ]}
    })
}

fn run(value: Value) -> Value {
    serde_json::to_value(run_request(serde_json::from_value(value).unwrap()).unwrap()).unwrap()
}

#[test]
fn real_process_completes_newly_composed_selection_lookup_and_consumer_flow() {
    // This is an invented stage program, not copied OEM code: short jumps
    // replace axis work, source selection sets a pointer, lookup returns 0x80,
    // and the consumer computes high-byte(0x80*0x80) into DATA0248.
    let mut rom = vec![0u8; 32768];
    rom[0x0A0C..0x0A0E].copy_from_slice(&[0xCB, 0x54]); // SJ 0A62
    rom[0x0B64..0x0B69].copy_from_slice(&[0x60, 0xE4, 0x72, 0xCB, 0x46]); // X1=72E4; SJ 0BAF
    rom[0x0BAF..0x0BB4].copy_from_slice(&[0x98, 0x80, 0x78, 0x00, 0x00]); // invented lookup byte
    rom[0x0BB4..0x0BC3].copy_from_slice(&[
        0x20, 0x8A, // MOVB r0,A
        0x99, 0x80, // MOVB r1,#80
        0x79, // LB A,r1
        0xA2, 0x34, // MULB
        0xC5, 0x07, 0x48, // MOVB r0,ACCH
        0x78, // LB A,r0
        0xD4, 0x48, // STB A,DATA0248
        0xCB, 0x11, // SJ 0BD4
    ]);
    let value = json!({
        "protocolVersion":1,"operation":"ignitionMapLookup","images":[{"id":"baseline","rom":rom}],
        "scratchPatterns":[0,85,170],"allowAssumptions":[],
        "ignitionMapLookup":{"formatVersion":1,
            "initialState":{"loadIndex":0,"map0RpmIndex":0,"map1RpmIndex":0,"loadFraction":0,
                "map0RpmFraction":0,"map1RpmFraction":0,"selector0227":0,
                "consumerFactor0247":0,"consumerOutput0248":123},
            "calls":[{"index":0,"mapId":"ignition_map_0","rawLoad":1,"rawMap0Rpm":2,"rawMap1Rpm":3}]}
    });
    let mut child = Command::new(env!("CARGO_BIN_EXE_p28-slice-runner"))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(value.to_string().as_bytes())
        .unwrap();
    let output = child.wait_with_output().unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let response: Value = serde_json::from_slice(&output.stdout).unwrap();
    for sequence in response["ignitionMapSequences"].as_array().unwrap() {
        let row = &sequence["checkpoints"][0];
        assert_eq!(row["status"], 0, "{row:#}");
        assert_eq!(row["selectedOrigin"], 0x72E4);
        assert_eq!(row["lookupResult"], 0x80);
        assert_eq!(row["consumerOutput"], 0x40);
    }
}

#[test]
fn bounded_zero_program_stops_and_leaves_suffix_null() {
    let response = run(request());
    assert_eq!(response["runnerVersion"], env!("CARGO_PKG_VERSION"));
    for sequence in response["ignitionMapSequences"].as_array().unwrap() {
        assert_eq!(sequence["checkpoints"][0]["status"], 3);
        assert!(!sequence["checkpoints"][0]["selection"].is_null());
        assert!(sequence["checkpoints"][0]["lookup"].is_null());
        assert!(sequence["checkpoints"][0]["lookupResult"].is_null());
        assert_eq!(sequence["checkpoints"][1]["status"], 4);
        assert!(sequence["checkpoints"][1]["stateAfterInputs"].is_null());
        assert!(sequence["checkpoints"][1]["consumerOutput"].is_null());
    }
}

#[test]
fn request_is_closed_to_offsets_state_injection_and_permissions() {
    for case in 0..8 {
        let mut value = request();
        match case {
            0 => value["ignitionMapLookup"]["calls"][0]["offset"] = json!(0x72E4),
            1 => value["ignitionMapLookup"]["calls"][0]["mapId"] = json!("map_0"),
            2 => value["ignitionMapLookup"]["calls"][0]["index"] = json!(9),
            3 => value["ignitionMapLookup"]["initialState"]["loadIndex"] = json!(9),
            4 => value["ignitionMapLookup"]["initialState"]["ram"] = json!({"arbitrary":1}),
            5 => value["allowAssumptions"] = json!(["oki.add-er3-a"]),
            6 => value["scratchPatterns"] = json!([0]),
            _ => value["operation"] = json!("fuelMapLookup"),
        }
        if let Ok(request) = serde_json::from_value(value) {
            assert!(run_request(request).is_err());
        }
    }
}
