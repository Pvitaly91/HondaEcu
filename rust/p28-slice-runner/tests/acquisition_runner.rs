//! Newly invented probes, deliberately not an OEM acquisition implementation.
//! These test the process, memory lifetime and observation boundary only.
use p28_slice_runner::protocol::Request;
use p28_slice_runner::runner::run_request;
use serde_json::{json, Value};
use std::io::Write;
use std::process::{Command, Stdio};

fn toy_program(g_add: bool, f_add: bool) -> Vec<u8> {
    let mut rom = vec![0; 32768];
    // Select the supplied slot FIRST, then copy a captured word verbatim to
    // the selected sample and EE. No interval, IRQ, init or overflow algorithm.
    let mut acquire = vec![
        0xF5, 0xA2, 0x53, 0xF8, 0x50, 0xE5, 0x3A, 0x8B, 0xD5, 0xEE, 0xD0, 0x60, 0x03, 0xF9, 0xC9,
    ];
    acquire.push((0x5719 - (0x56BE + acquire.len() + 1)) as u8);
    rom[0x56BE..0x56BE + acquire.len()].copy_from_slice(&acquire);
    // Independent tiny G/F probes from the public producer process tests.
    let mut g = vec![0xF9, 0x50, 0xE0, 0x60, 0x03];
    if g_add {
        g.extend([0x45, 0x81]);
    }
    g.extend([0xB5, 0xC4, 0x10, 0x03, 0xA5, 0x07]);
    rom[0x0772..0x0772 + g.len()].copy_from_slice(&g);
    let mut f = vec![];
    if f_add {
        f.extend([0x47, 0x81]);
    }
    f.extend([
        0xF5,
        0xC4,
        0xD3,
        0xB3,
        0xCB,
        if f_add { 0x53 } else { 0x55 },
    ]);
    rom[0x07C7..0x07C7 + f.len()].copy_from_slice(&f);
    rom[0x122C..0x122E].copy_from_slice(&[0xCB, 0x3F]);
    rom
}

fn request(rom: Vec<u8>, compose: bool) -> Value {
    json!({"protocolVersion":1,"operation":"acquisitionSequence",
        "images":[{"id":"baseline","rom":rom}],"allowAssumptions":[],"scratchPatterns":[0,85,170],
        "acquisitionSequence":{"formatVersion":1,
            "composition":if compose { "scheduled-g-f-threshold" } else { "acquisition-only" },
            "initialState":{"previousTimestamp":65000,"samples":[42,100,200,300,400,500],
                "data0128":8,"data00AE":7,"data00B6":32,"data011F":0,"previousT":321,
                "data0217":0,"data0231":0,"data0136":4321},
            "observations":[
                {"index":0,"tmr2":42,"irqh":1,"tcon2":4,"slot":0,"compose":compose,
                    "thresholdContext":0,"thresholdPriorBits":2,"thresholdEnabled":false},
                {"index":1,"tmr2":73,"irqh":0,"tcon2":0,"slot":4,"compose":compose,
                    "thresholdContext":1,"thresholdPriorBits":1,"thresholdEnabled":true}],
            "traceObservationIndexes":[0]}})
}

fn run(value: Value) -> Value {
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
    serde_json::from_slice(&output.stdout).unwrap()
}

#[test]
fn actual_process_observes_word_width_preserves_history_and_same_value_stores() {
    let output = run(request(toy_program(false, false), false));
    assert_eq!(output["runnerVersion"], "0.7.0");
    assert!(output["diagnostics"].as_array().unwrap().is_empty());
    for sequence in output["acquisitionSequences"].as_array().unwrap() {
        assert_eq!(sequence["completedObservations"], 2);
        assert_eq!(sequence["stopObservationIndex"], -1);
        let first = &sequence["checkpoints"][0];
        assert_eq!(
            first["acquisition"]["peripheralAccesses"],
            json!([[58, 16, 0, 42]])
        );
        assert_eq!(first["acquisition"]["sampleWrites"], json!([[864, 16, 42]]));
        assert_eq!(first["selectedTimestamp"], 42);
        assert_eq!(first["slotIndex"], 0);
        assert_eq!(first["everWrittenMask"], 1);
        let second = &sequence["checkpoints"][1];
        assert_eq!(
            second["acquisition"]["stateAfter"]["samples"],
            json!([42, 100, 200, 300, 73, 500])
        );
        assert_eq!(second["acquisition"]["stateAfter"]["previousTimestamp"], 73);
        assert_eq!(second["acquisition"]["stateAfter"]["data00AE"], 7);
        assert_eq!(second["everWrittenMask"], 17);
        assert_eq!(second["slotWriteCounts"], json!([1, 0, 0, 0, 1, 0]));
        assert_eq!(
            first["acquisition"]["executedInstructionBytes"],
            json!((0x56BE..0x56CE).collect::<Vec<_>>())
        );
        assert!(!first["acquisition"]["trace"].as_array().unwrap().is_empty());
        assert!(second["acquisition"]["trace"]
            .as_array()
            .unwrap()
            .is_empty());
    }
}

#[test]
fn full_child_g_and_f_bytes_execute_with_actual_acquisition_ram() {
    let baseline = toy_program(false, false);
    let mut derived = baseline.clone();
    // Child G loads sample1 instead of sample0; no second baseline execution.
    derived[0x0775] = 0x62;
    let mut input = request(baseline, true);
    input["images"]
        .as_array_mut()
        .unwrap()
        .push(json!({"id":"derived","rom":derived}));
    let output = run(input);
    let rows = output["acquisitionSequences"].as_array().unwrap();
    assert_eq!(rows.len(), 6);
    assert_eq!(rows[0]["checkpoints"][0]["g"]["outputs"][0], 42);
    assert_eq!(rows[0]["checkpoints"][0]["f"]["outputs"][0], 42);
    assert_eq!(rows[3]["checkpoints"][0]["g"]["outputs"][0], 100);
    assert_eq!(rows[3]["checkpoints"][0]["f"]["outputs"][0], 100);
    assert_eq!(
        rows[0]["checkpoints"][0]["threshold"]["outputs"][0]
            .as_i64()
            .unwrap()
            & 6,
        4
    );
    assert!(rows[0]["checkpoints"][0]["threshold"]["programReads"]
        .as_array()
        .unwrap()
        .is_empty());
}

#[test]
fn strict_stop_aborts_all_later_observations_and_permissions_are_cumulative() {
    let input = request(toy_program(true, true), true);
    let strict = run(input.clone());
    let row = &strict["acquisitionSequences"][0];
    assert_eq!(row["completedObservations"], 0);
    assert_eq!(row["remainingNotRun"], 1);
    assert_eq!(row["checkpoints"][0]["g"]["status"], 1);
    assert!(row["checkpoints"][0]["f"].is_null());
    assert_eq!(row["checkpoints"][1]["acquisition"]["status"], 4);
    assert_eq!(
        row["checkpoints"][1]["acquisition"]["stateAfter"],
        row["checkpoints"][0]["stateAfterComposition"]
    );
    let mut conditional = input;
    conditional["allowAssumptions"] = json!(["oki.add-er1-a", "oki.add-er3-a"]);
    let output = run(conditional);
    assert_eq!(
        output["acquisitionSequences"][0]["completedObservations"],
        2
    );
    assert_eq!(
        output["acquisitionSequences"][0]["checkpoints"][1]["cumulativeAssumptions"],
        json!(["oki.add-er1-a", "oki.add-er3-a"])
    );
}

#[test]
fn unsupported_mode_refuses_before_fetch_and_unaudited_opcode_never_nops() {
    let mut unsupported = request(toy_program(false, false), false);
    unsupported["acquisitionSequence"]["initialState"]["data011F"] = json!(4);
    let output = run(unsupported.clone());
    let first = &output["acquisitionSequences"][0]["checkpoints"][0];
    assert_eq!(first["acquisition"]["disposition"], "UnsupportedMode");
    assert_eq!(first["acquisition"]["steps"], 0);
    assert!(first["selectedTimestamp"].is_null());
    assert_eq!(
        first["acquisition"]["stateAfter"],
        unsupported["acquisitionSequence"]["initialState"]
    );
    let mut rom = toy_program(false, false);
    rom[0x56BE..0x56C0].copy_from_slice(&[0x45, 0x81]);
    let output = run(request(rom, false));
    assert_eq!(
        output["acquisitionSequences"][0]["checkpoints"][0]["acquisition"]["status"],
        1
    );
    assert_eq!(
        output["acquisitionSequences"][0]["checkpoints"][0]["acquisition"]["steps"],
        0
    );
}

#[test]
fn sequence_schema_is_closed_bounded_and_cannot_enable_old_task_sfrs() {
    let valid = request(toy_program(false, false), false);
    for (key, value) in [
        ("formatVersion", json!(2)),
        ("traceObservationIndexes", json!([0, 0])),
    ] {
        let mut bad = valid.clone();
        bad["acquisitionSequence"][key] = value;
        assert!(run_request(serde_json::from_value::<Request>(bad).unwrap()).is_err());
    }
    let mut bad = valid.clone();
    bad["acquisitionSequence"]["initialState"]["data010F"] = json!(128);
    assert!(serde_json::from_value::<Request>(bad).is_err());
    let mut bad = valid.clone();
    bad["acquisitionSequence"]["observations"][1]["slot"] = json!(6);
    assert!(run_request(serde_json::from_value::<Request>(bad).unwrap()).is_err());
    let mut bad = valid;
    bad["operation"] = json!("p28Batch");
    assert!(run_request(serde_json::from_value::<Request>(bad).unwrap()).is_err());
}

#[test]
fn local_error_trace_replays_prefix_and_never_exposes_observations_to_g() {
    let mut rom = toy_program(false, false);
    // Independently invented G load of TMR2: its mnemonic is admitted but the
    // observation capability has ended, so this is a memory-access error.
    rom[0x0772..0x0777].copy_from_slice(&[0xF9, 0x50, 0xE0, 0x3A, 0]);
    let mut input = request(rom, true);
    input["acquisitionSequence"]["traceObservationIndexes"] = json!([]);
    input["acquisitionSequence"]["observations"][0]["compose"] = json!(false);
    let output = run(input);
    let row = &output["acquisitionSequences"][0];
    assert_eq!(row["completedObservations"], 1);
    assert_eq!(row["stopObservationIndex"], 1);
    assert_eq!(row["checkpoints"][1]["g"]["status"], 2);
    assert!(!row["checkpoints"][1]["g"]["trace"]
        .as_array()
        .unwrap()
        .is_empty());
    assert_eq!(
        row["checkpoints"][1]["acquisition"]["stateAfter"]["samples"],
        json!([42, 100, 200, 300, 73, 500])
    );
}
