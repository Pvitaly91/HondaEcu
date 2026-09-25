use p28_slice_runner::runner::run_request;
use serde_json::{json, Value};
use std::io::Write;
use std::process::{Command, Stdio};

fn request(rom: Vec<u8>) -> Value {
    json!({
        "protocolVersion":1,"operation":"ignitionCorrectionChain",
        "images":[{"id":"baseline","rom":rom}],"scratchPatterns":[0,85,170],"allowAssumptions":[],
        "ignitionCorrectionChain":{"formatVersion":1,
            "initial":{"ignition":{"loadIndex":0,"map0RpmIndex":0,"map1RpmIndex":0,
                "loadFraction":0,"map0RpmFraction":0,"map1RpmFraction":0,"selector0227":0xA5,
                "consumerFactor0247":0,"consumerOutput0248":0x55},"source03c7":0,
                "floor024c":0,"bias0249":0,"retained035b":0x44,"retained024a":0x45,
                "gate0234Bit5":false,"gate0217Bit0":false,"gate021eBit0":false},
            "calls":[{"index":0,"source03c7":0,"rawLoad":0,"rawMap0Rpm":0,"rawMap1Rpm":0,
                "correction0245":0,"correction0246":0},
                {"index":1,"source03c7":0,"rawLoad":0,"rawMap0Rpm":0,"rawMap1Rpm":0,
                "correction0245":0,"correction0246":0}],"traceCallIndexes":[0]}
    })
}

#[test]
fn invented_process_stores_reads_bounds_and_hands_off_on_one_machine() {
    let mut rom = vec![0u8; 32768];
    // Invented programs at the contracted entry points; not the OEM routine.
    rom[0x5F93..0x5F9E].copy_from_slice(&[
        0x62, 0xC7, 0x03, 0xF2, 0x53, 0xC4, 0x27, 0x3D, 0x03, 0xAF, 0x5F,
    ]);
    rom[0x0A0C..0x0A0E].copy_from_slice(&[0xCB, 0x54]);
    rom[0x0B64..0x0B71].copy_from_slice(&[
        0xED, 0x27, 0x05, 0x60, 0xE4, 0x72, 0xCB, 0x43, 0x60, 0xAC, 0x73, 0xCB, 0x3E,
    ]);
    rom[0x0BAF..0x0BB3].copy_from_slice(&[0x90, 0xAA, 0xCB, 0x01]);
    rom[0x0BB4..0x0BB8].copy_from_slice(&[0xD4, 0x48, 0xCB, 0x1C]);
    rom[0x72E4] = 0x7F;
    rom[0x0F85..0x0F88].copy_from_slice(&[0x03, 0xF4, 0x0F]);
    // Native read, byte add, compare with invented bound, then two stores.
    rom[0x0FF4..0x1007].copy_from_slice(&[
        0xF4, 0x48, 0x86, 0x05, 0xC6, 0x80, 0xCA, 0x02, 0x77, 0x80, 0xD4, 0x4A, 0x62, 0x5B, 0x03,
        0xD2, 0x03, 0x76, 0x10,
    ]);
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
        .write_all(request(rom).to_string().as_bytes())
        .unwrap();
    let output = child.wait_with_output().unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let response: Value = serde_json::from_slice(&output.stdout).unwrap();
    for sequence in response["ignitionCorrectionSequences"].as_array().unwrap() {
        for cp in sequence["checkpoints"].as_array().unwrap() {
            assert_eq!(cp["status"], 0, "{cp:#}");
            assert_eq!(cp["lookupResult"], 0x7F);
            assert_eq!(cp["data0248"], 0x7F);
            assert_eq!(cp["nativeRead0248"], 0x7F);
            assert_eq!(cp["result024a"], 0x80);
            assert_eq!(cp["result035b"], 0x80);
            assert_eq!(cp["consumerExit"]["ssp"], cp["correctionEntry"]["ssp"]);
        }
    }
}

#[test]
fn new_request_rejects_foreign_permissions_and_0248_substitution() {
    let base = request(vec![0; 32768]);
    for change in 0..7 {
        let mut value = base.clone();
        match change {
            0 => value["ignitionCorrectionChain"]["calls"][0]["data0248"] = json!(11),
            1 => value["ignitionCorrectionChain"]["calls"][0]["mapId"] = json!("ignition_map_1"),
            2 => value["ignitionCorrectionChain"]["calls"][0]["index"] = json!(3),
            3 => value["ignitionCorrectionChain"]["initial"]["ram"] = json!({"offset":584}),
            4 => value["allowAssumptions"] = json!(["oki.subb-a-off-n8-encoding"]),
            5 => value["operation"] = json!("ignitionSelectorChain"),
            _ => value["scratchPatterns"] = json!([0]),
        }
        if let Ok(parsed) = serde_json::from_value(value) {
            assert!(run_request(parsed).is_err());
        }
    }
}

#[test]
fn invented_strict_form_refusal_keeps_native_base_and_terminal_suffix() {
    let mut rom = vec![0u8; 32768];
    rom[0x5F93..0x5F9E].copy_from_slice(&[
        0x62, 0xC7, 0x03, 0xF2, 0x53, 0xC4, 0x27, 0x3D, 0x03, 0xAF, 0x5F,
    ]);
    rom[0x0A0C..0x0A0E].copy_from_slice(&[0xCB, 0x54]);
    rom[0x0B64..0x0B71].copy_from_slice(&[
        0xED, 0x27, 0x05, 0x60, 0xE4, 0x72, 0xCB, 0x43, 0x60, 0xAC, 0x73, 0xCB, 0x3E,
    ]);
    rom[0x0BAF..0x0BB3].copy_from_slice(&[0x90, 0xAA, 0xCB, 0x01]);
    rom[0x0BB4..0x0BB8].copy_from_slice(&[0xD4, 0x48, 0xCB, 0x1C]);
    rom[0x72E4] = 0x33;
    // Invented compact sequence deliberately reaches exactly one unresolved form.
    rom[0x0F85..0x0F89].copy_from_slice(&[0xF9, 0x8B, 0x47, 0x81]);
    let response =
        serde_json::to_value(run_request(serde_json::from_value(request(rom)).unwrap()).unwrap())
            .unwrap();
    for sequence in response["ignitionCorrectionSequences"].as_array().unwrap() {
        let cps = sequence["checkpoints"].as_array().unwrap();
        assert_eq!(cps[0]["status"], 1);
        assert_eq!(cps[0]["data0248"], 0x33);
        assert_eq!(cps[0]["correction"]["result"]["stopPc"], 0x0F87);
        assert!(cps[0]["nativeRead0248"].is_null());
        assert!(cps[0]["result035b"].is_null());
        assert_eq!(cps[1]["status"], 4);
        assert!(cps[1]["input"].is_null());
        assert_eq!(cps[1]["retained035bBefore"], 0x44);
    }
}
