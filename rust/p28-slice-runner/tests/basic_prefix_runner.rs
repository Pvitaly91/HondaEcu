//! Invented programs only; task separation is not OEM or export admission.
use p28_slice_runner::{protocol::Request, runner::run_request};
use serde_json::{json, Value};

fn request(operation: &str) -> Value {
    // Invented absolute jump is outside the legacy M1d execution subset.
    // It must be reported as failure, not widen that subset for the new task.
    let mut rom = vec![0u8; 32768];
    rom[0x122c..0x122f].copy_from_slice(&[0x03, 0x6d, 0x12]);
    // Unresolved G/F instruction: it must never be executed by prefix tasks.
    rom[0x07c7] = 0x09;
    json!({"protocolVersion":1,"operation":operation,
        "images":[{"id":"A","rom":rom},{"id":"B","rom":rom},{"id":"C","rom":rom}],
        "scratchPatterns":[0,85,170],"allowAssumptions":[]})
}

#[test]
fn strict_prefix_and_control_have_separate_bounded_coverage_without_compact_execution() {
    for (op, count) in [
        ("vtecThresholdPrefix", 36864),
        ("vtecThresholdControl", 432),
    ] {
        let response = run_request(serde_json::from_value(request(op)).unwrap()).unwrap();
        assert_eq!(response.operation, op);
        assert!(response.compact_rows.is_empty());
        assert_eq!(response.entry_contracts.len(), 1);
        assert_eq!(response.entry_contracts[0]["id"], "threshold");
        assert_eq!(response.threshold_rows.len(), count);
        assert!(response.threshold_rows.iter().all(|r| r[6] == 2));
        // Missing reads are visible, not promoted to complete comparison proof by the runner.
        assert!(response.threshold_rows.iter().all(|r| r[8..] == [-1; 4]));
        assert!(response.diagnostics.iter().all(|d| d.slice == "threshold"));
    }
}

#[test]
fn prefix_contract_rejects_legacy_images_permissions_and_foreign_stimuli() {
    let mutations: Vec<fn(&mut Value)> = vec![
        |v| v["images"][0]["id"] = json!("baseline"),
        |v| {
            v["images"].as_array_mut().unwrap().pop();
        },
        |v| v["allowAssumptions"] = json!(["oki.add-er3-a"]),
        |v| v["scratchPatterns"] = json!([0]),
        |v| v["producerCases"] = json!([]),
        |v| v["protocolVersion"] = json!(2),
    ];
    for mutate in mutations {
        let mut v = request("vtecThresholdPrefix");
        mutate(&mut v);
        let r: Request = serde_json::from_value(v).unwrap();
        assert!(run_request(r).is_err());
    }
}
