//! Entirely invented control-flow probes; no OEM bytes or private ROM are included.
use p28_slice_runner::runner::run_request;
use serde_json::{json, Value};
use std::io::Write;
use std::process::{Command, Stdio};

fn request(rom: Vec<u8>) -> Value {
    json!({
        "protocolVersion":1,"operation":"vtecFuelIgnitionChain",
        "images":[{"id":"baseline","rom":rom}],
        "scratchPatterns":[0,85,170],"allowAssumptions":[],
        "sharedCalibrationChain":{
            "formatVersion":1,
            "initial":{
                "vtec":{"data0131":0,"data0127":128,"data0198":0,
                    "data01D8":0,"data01D9":0,"data01DF":0,"data00F3":0,"p1OutputData":68},
                "axes":{"ignitionLoadIndex":0,"fuelLoadIndex":0,"map0RpmIndex":0,
                    "map1RpmIndex":0,"ignitionLoadFraction":0,"fuelLoadFraction":0,
                    "map0RpmFraction":0,"map1RpmFraction":0},
                "selector0227":165,"factor0247":0,"output0248":90,
                "factor013f":0,"output0140":123,"source03c7":0
            },
            "calls":[
                {"index":0,"source03c7":0,"rawLoad":1,"rawMap0Rpm":2,"rawMap1Rpm":3,
                    "decision":{"index":0,"compactCode":0,"context":0,"enabled":false,
                        "raw00CC":0,"raw00D9":0,"snapshot011A":0,"snapshot011C":0,
                        "snapshot0119":0,"raw0132":0,"raw0199":0,"fastTicks":0,"slowTicks":0}},
                {"index":1,"source03c7":0,"rawLoad":4,"rawMap0Rpm":5,"rawMap1Rpm":6,
                    "decision":{"index":1,"compactCode":0,"context":0,"enabled":false,
                        "raw00CC":0,"raw00D9":0,"snapshot011A":0,"snapshot011C":0,
                        "snapshot0119":0,"raw0132":0,"raw0199":0,"fastTicks":0,"slowTicks":0}}
            ],"traceCallIndexes":[0]
        }
    })
}

fn invented() -> Vec<u8> {
    let mut rom = vec![0u8; 32768];
    // Off-page bit store from entry carry=0, then branch to producer exit.
    rom[0x5F93..0x5F98].copy_from_slice(&[0xC4, 0x27, 0x3D, 0xCB, 0x17]);
    // Single axis pass with 0A45 and 0A62 in its actual native PC path.
    rom[0x0A0C..0x0A0E].copy_from_slice(&[0xCB, 0x37]);
    rom[0x0A45..0x0A47].copy_from_slice(&[0xCB, 0x1B]);
    rom[0x0A62..0x0A64].copy_from_slice(&[0xCB, 0x13]);
    // Invented no-op tails retain pre-seeded output values; boundaries are native.
    for (at, displacement) in [
        (0x0B64, 0x49),
        (0x0BAF, 0x03),
        (0x0BB4, 0x1E),
        (0x122C, 0x7F),
        (0x12AD, 0x4D),
    ] {
        rom[at..at + 2].copy_from_slice(&[0xCB, displacement]);
    }
    // The fuel inventory deliberately does not admit SJ. CLR A followed by
    // JEQ uses admitted native forms and keeps each tail boundary continuous.
    rom[0x12FC..0x12FF].copy_from_slice(&[0xF9, 0xC9, 0x41]);
    rom[0x1340..0x1343].copy_from_slice(&[0xF9, 0xC9, 0x04]);
    rom[0x1347..0x134A].copy_from_slice(&[0xF9, 0xC9, 0x06]);
    rom
}

#[test]
fn invented_real_subprocess_keeps_one_history_and_producer_precedes_gate() {
    let value = request(invented());
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
    assert_eq!(response["runnerVersion"], env!("CARGO_PKG_VERSION"));
    for sequence in response["sharedCalibrationSequences"].as_array().unwrap() {
        let checkpoints = sequence["checkpoints"].as_array().unwrap();
        let first = &checkpoints[0];
        assert_eq!(first["stateBefore"]["selector0227"], 165);
        assert_eq!(first["stateAfterProducer"]["selector0227"], 133);
        assert_eq!(first["status"], 0, "{first:#}");
        assert_eq!(first["axisEntry"]["pc"], 0x0A0C);
        assert_eq!(first["axis"]["result"]["stopPc"], 0x0A77);
        assert_eq!(checkpoints[1]["stateBefore"], first["stateAfter"]);
        assert_eq!(checkpoints[1]["stateAfterInputs"]["selector0227"], 133);
    }
}

#[test]
fn shared_request_rejects_foreign_permissions_and_host_cache_injection() {
    for case in 0..6 {
        let mut value = request(invented());
        match case {
            0 => value["sharedCalibrationChain"]["calls"][0]["mapId"] = json!("map_1"),
            1 => value["sharedCalibrationChain"]["calls"][0]["preparedRpmIndex"] = json!(7),
            2 => value["sharedCalibrationChain"]["initial"]["axes"]["map0RpmIndex"] = json!(19),
            3 => value["allowAssumptions"] = json!(["oki.add-er3-a"]),
            4 => value["scratchPatterns"] = json!([0]),
            _ => value["operation"] = json!("ignitionSelectorChain"),
        }
        if let Ok(request) = serde_json::from_value(value) {
            assert!(run_request(request).is_err());
        }
    }
}
