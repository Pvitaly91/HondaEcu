//! Unrelated, newly authored tiny programs. No OEM routine or ROM fixture.
use serde_json::{json, Value};
use std::io::Write;
use std::process::{Command, Output, Stdio};

fn process(request: &Value) -> Output {
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
        .write_all(request.to_string().as_bytes())
        .unwrap();
    child.wait_with_output().unwrap()
}

fn run(request: &Value) -> Value {
    let output = process(request);
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    serde_json::from_slice(&output.stdout).unwrap()
}

fn toy_request(program: &[u8], exit: usize) -> Value {
    json!({"protocolVersion":1,"operation":"checksumSynthetic",
        "images":[{"id":"toy","rom":program}],"allowAssumptions":[],"scratchPatterns":[170],
        "synthetic":{"entryPc":0,"exitPcs":[exit],"allowedCodeRanges":[[0,exit]],
            "psw":256,"lrb":65,"usp":384,"instructionBudget":16,
            "dataSeeds":[[128,32],[129,0],[130,0],[131,0],[520,5]],"outputAddresses":[520,928]}})
}

#[test]
fn actual_checksum_form_execution_reads_rom_and_changed_constant_changes_output() {
    // An 11-byte invented toy: fold one ROM word into r0, store its byte.
    // X1 and X2 are caller-seeded; there is no native checksum control flow.
    let mut program = vec![0; 0x122];
    program[..11].copy_from_slice(&[0x90, 0xA8, 0xC5, 7, 0x82, 0x20, 0x81, 0x78, 0xD1, 0xA0, 3]);
    program[0x120..0x122].copy_from_slice(&[1, 2]);
    let mut request = toy_request(&program, 11);
    // RAM at the same numeric address is deliberately different.
    request["synthetic"]["dataSeeds"][1] = json!([129, 1]);
    request["synthetic"]["dataSeeds"]
        .as_array_mut()
        .unwrap()
        .extend([json!([288, 99]), json!([289, 88])]);
    let first = run(&request);
    assert_eq!(first["syntheticResult"]["status"], 0);
    assert_eq!(first["syntheticResult"]["outputs"], json!([8, 8]));
    assert_eq!(first["syntheticResult"]["programReads"], json!([288, 289]));
    assert_eq!(first["syntheticResult"]["usedAssumptions"], json!([]));
    request["images"][0]["rom"][288] = json!(4);
    let changed = run(&request);
    assert_eq!(changed["syntheticResult"]["status"], 0);
    assert_eq!(changed["syntheticResult"]["outputs"], json!([11, 11]));
    assert_eq!(
        changed["syntheticResult"]["programReads"],
        json!([288, 289])
    );
}

#[test]
fn changed_addressing_form_is_unresolved_before_execution_and_permissions_rejected() {
    let mut request = toy_request(&[0x90, 0xA8], 2);
    request["images"][0]["rom"] = json!([0x92, 0xA8]); // LC [DP], not reviewed checksum LC [X1].
    let response = run(&request);
    assert_eq!(response["syntheticResult"]["status"], 1);
    assert_eq!(response["syntheticResult"]["steps"], 0);
    assert_eq!(response["syntheticResult"]["programReads"], json!([]));
    request["allowAssumptions"] = json!(["oki.add-er3-a"]);
    assert!(!process(&request).status.success());
    request["allowAssumptions"] = json!(["oki.add-er1-a"]);
    assert!(!process(&request).status.success());
}

#[test]
fn fixed_batch_rejects_false_completion_and_scoped_cpu_alias_access() {
    let mut program = vec![0; 32768];
    program[0x2B70..0x2B73].copy_from_slice(&[3, 0xB6, 0x2B]);
    let mut request = json!({"protocolVersion":1,"operation":"checksumBatch",
        "images":[{"id":"toy","rom":program}],"allowAssumptions":[],"scratchPatterns":[0,85,170]});
    let response = run(&request);
    assert_eq!(response["checksumCases"].as_array().unwrap().len(), 3);
    for case in response["checksumCases"].as_array().unwrap() {
        assert_eq!(case["status"], 2);
        assert_eq!(case["completed"], false);
        assert_eq!(case["decision"], "NotCompleted");
        assert_eq!(case["residue"], -1);
        assert_eq!(case["programReadCount"], 0);
    }
    // An admitted byte-add form aimed at PSW (not an allowed DATA alias).
    request["images"][0]["rom"][0x2B70] = json!(0xC5);
    request["images"][0]["rom"][0x2B71] = json!(4);
    request["images"][0]["rom"][0x2B72] = json!(0x82);
    let response = run(&request);
    for case in response["checksumCases"].as_array().unwrap() {
        assert_eq!(case["status"], 2);
        assert_eq!(case["completed"], false);
        assert!(case["error"].as_str().unwrap().contains("data"));
    }
}

#[test]
fn fixed_checksum_batch_requires_exact_request_bounds_and_empty_assumptions() {
    let valid = json!({"protocolVersion":1,"operation":"checksumBatch",
        "images":[{"id":"toy","rom":vec![0;32768]}],"allowAssumptions":[],"scratchPatterns":[0,85,170]});
    for (field, value) in [
        ("allowAssumptions", json!(["oki.add-er1-a"])),
        ("scratchPatterns", json!([0])),
        ("images", json!([])),
        ("images", json!([{"id":"toy","rom":[0]}])),
        ("images", json!([{"id":"../toy","rom":vec![0;32768]}])),
    ] {
        let mut request = valid.clone();
        request[field] = value;
        assert!(!process(&request).status.success());
    }
}
