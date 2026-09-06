//! Invented persistence probes, not the OEM decision procedure.
use p28_slice_runner::{
    decoder::decode,
    instruction_forms::FormAdmission,
    protocol::Request,
    runner::run_request,
    stateful_forms::{admission, SUBB_OFF_ASSUMPTION},
};
use serde_json::{json, Value};
use std::{
    io::Write,
    process::{Command, Stdio},
};

fn toy(increment: u8) -> Vec<u8> {
    let mut rom = vec![0; 32768];
    // Increment a whole persistent byte; deliberately not a VTEC algorithm.
    let p = [0xF4, 0x31, 0x86, increment, 0xD4, 0x31, 0x03, 0xFC, 0x12];
    rom[0x122C..0x122C + p.len()].copy_from_slice(&p);
    rom
}
fn request(program: Vec<u8>) -> Value {
    json!({"protocolVersion":1,"operation":"statefulVtec","images":[{"id":"baseline","rom":program}],
    "scratchPatterns":[0,85,170],"allowAssumptions":[],"statefulVtec":{"formatVersion":1,
    "initialState":{"data0131":4,"data0127":6,"data0198":79,"data01D8":3,"data01D9":7,"data01DF":19,"data00F3":254,"p1OutputData":69},
    "calls":(0..4).map(|i|json!({"index":i,"compactCode":80+i,"context":i%2,"enabled":i!=1,"raw00CC":0,"raw00D9":0,
        "snapshot011A":0,"snapshot011C":0,"snapshot0119":0,"raw0132":0,"raw0199":0,"fastTicks":0,"slowTicks":0})).collect::<Vec<_>>(),"traceCallIndexes":[1]}})
}
fn run(v: Value) -> Value {
    let mut p = Command::new(env!("CARGO_BIN_EXE_p28-slice-runner"))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    p.stdin
        .take()
        .unwrap()
        .write_all(v.to_string().as_bytes())
        .unwrap();
    let output = p.wait_with_output().unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    serde_json::from_slice(&output.stdout).unwrap()
}
#[test]
fn real_subprocess_retains_state_and_independent_child_diverges_without_reseeding() {
    let mut input = request(toy(1));
    input["images"]
        .as_array_mut()
        .unwrap()
        .push(json!({"id":"derived","rom":toy(2)}));
    let saved = input.clone();
    let output = run(input.clone());
    assert_eq!(input, saved);
    for sequence in output["statefulSequences"].as_array().unwrap() {
        let increment = sequence["imageIndex"].as_u64().unwrap() + 1;
        for (i, cp) in sequence["checkpoints"]
            .as_array()
            .unwrap()
            .iter()
            .enumerate()
        {
            assert_eq!(cp["status"], 0);
            assert_eq!(cp["stateBefore"]["data0131"], 4 + i as u64 * increment);
            assert_eq!(cp["stateAfter"]["data0131"], 4 + (i + 1) as u64 * increment);
            for name in [
                "data0127",
                "data0198",
                "data01D8",
                "data01D9",
                "data01DF",
                "data00F3",
                "p1OutputData",
            ] {
                assert_eq!(
                    cp["stateAfter"][name],
                    saved["statefulVtec"]["initialState"][name]
                );
            }
            assert_eq!(
                cp["decisionWrites"],
                json!([[0x131, 8, 4 + (i + 1) as u64 * increment]])
            );
            assert_eq!(
                cp["execution"]["trace"].as_array().unwrap().is_empty(),
                i != 1
            );
        }
    }
}
#[test]
fn every_initial_pair_combination_and_context_preserves_native_previous_value() {
    for prior in 0..4 {
        for context in 0..2 {
            let mut r = request(toy(1));
            r["statefulVtec"]["initialState"]["data0131"] = json!(prior * 2);
            for call in r["statefulVtec"]["calls"].as_array_mut().unwrap() {
                call["context"] = json!(context);
            }
            let output = run(r);
            let cp = &output["statefulSequences"][0]["checkpoints"];
            assert_eq!(cp[3]["stateAfter"]["data0131"], prior * 2 + 4);
        }
    }
}
#[test]
fn exact_form_refusal_is_terminal_and_unavailable_request_is_null_not_false() {
    for program in [
        &[0xA7, 0x99][..],
        &[0x0F][..],
        &[0x45, 0x81][..],
        &[0x47, 0x81][..],
    ] {
        let mut rom = toy(1);
        rom[0x122C..0x122C + program.len()].copy_from_slice(program);
        let output = run(request(rom));
        let seq = &output["statefulSequences"][0];
        assert_eq!(seq["checkpoints"][0]["status"], 1);
        assert!(seq["checkpoints"][0]["softwareRequest"].is_null());
        for i in 1..4 {
            assert_eq!(seq["checkpoints"][i]["status"], 4);
            assert!(seq["checkpoints"][i]["execution"].is_null());
        }
    }
    for (bytes, dd, expected) in [
        (&[0x0E][..], false, FormAdmission::Allowed),
        (&[0x0E][..], true, FormAdmission::Unsupported),
        (
            &[0xA7, 9][..],
            false,
            FormAdmission::Assumption(SUBB_OFF_ASSUMPTION),
        ),
        (&[0xA7, 9][..], true, FormAdmission::Unsupported),
        (&[0xC0, 0, 0, 0x17][..], true, FormAdmission::Allowed),
        (&[0xC1, 0, 0, 0x17][..], true, FormAdmission::Unsupported),
    ] {
        assert_eq!(
            decode(dd, |i| bytes.get(i).copied().unwrap_or(0))
                .map(|d| admission(&d))
                .unwrap_or(FormAdmission::Unsupported),
            expected
        );
    }
}
#[test]
fn conditional_permission_is_narrow_and_accumulates_through_later_calls() {
    let mut rom = toy(1);
    let p = [0xF4, 0x31, 0xA7, 0x99, 0xD4, 0x31, 0x03, 0xFC, 0x12];
    rom[0x122C..0x1235].copy_from_slice(&p);
    let mut r = request(rom);
    r["allowAssumptions"] = json!([SUBB_OFF_ASSUMPTION]);
    let output = run(r);
    for cp in output["statefulSequences"][0]["checkpoints"]
        .as_array()
        .unwrap()
    {
        assert_eq!(cp["status"], 0);
        assert_eq!(cp["cumulativeAssumptions"], json!([SUBB_OFF_ASSUMPTION]));
    }
}
#[test]
fn malformed_stimulus_and_legacy_permission_leakage_are_rejected() {
    for (name, value) in [
        ("context", json!(2)),
        ("fastTicks", json!(33)),
        ("slowTicks", json!(33)),
        ("index", json!(2)),
        ("compactCode", json!(256)),
        ("thresholdPriorBits", json!(0)),
    ] {
        let mut r = request(toy(1));
        r["statefulVtec"]["calls"][0][name] = value;
        match serde_json::from_value::<Request>(r) {
            Ok(r) => assert!(run_request(r).is_err()),
            Err(_) => {}
        }
    }
    for permission in ["all", "oki.add-er1-a", "oki.add-er3-a"] {
        let mut r = request(toy(1));
        r["allowAssumptions"] = json!([permission]);
        assert!(run_request(serde_json::from_value(r).unwrap()).is_err());
    }
    let mut r = request(toy(1));
    r["operation"] = json!("p28Batch");
    assert!(run_request(serde_json::from_value(r).unwrap()).is_err());
}
#[test]
fn native_tick_probe_writes_are_measured_not_host_decrements() {
    let mut rom = toy(1);
    // Different, invented counter body: store a constant instead of decrement.
    let p = [0x77, 41, 0xD4, 0xD8, 0x03, 0xD9, 0x5B];
    rom[0x5BD0..0x5BD7].copy_from_slice(&p);
    let mut r = request(rom);
    r["statefulVtec"]["calls"][0]["fastTicks"] = json!(1);
    let output = run(r);
    let first = &output["statefulSequences"][0]["checkpoints"][0];
    assert_eq!(first["stateAtEntry"]["data01D8"], 41);
    assert_eq!(first["stateAtEntry"]["data01D9"], 7);
    assert_eq!(first["tickWrites"], json!([[0x1D8, 8, 41], [0x1D8, 8, 41]]));
}

#[test]
fn invented_one_pair_program_preserves_hysteresis_equality_and_reversed_pair_oscillation() {
    // Independently arranged one-pair probe: test the prior through ANDB/JEQ,
    // then select a byte. It has none of the OEM prefix/helper/output logic.
    let program = [
        0x62, 0x42, 0x65, 0xF4, 0x31, 0xD6, 2, 0xC9, 4, 0x92, 0xA8, 0xCB, 4, 0x92, 0xA8, 0xF5, 7,
        0xC7, 0x33, 0xC4, 0x31, 0x39, 0x03, 0xFC, 0x12,
    ];
    for (set, clear) in [(30u8, 40u8), (40, 40), (40, 30)] {
        for initial in [false, true] {
            let mut rom = vec![0; 32768];
            rom[0x122C..0x122C + program.len()].copy_from_slice(&program);
            rom[0x6542] = set;
            rom[0x6543] = clear;
            let mut r = request(rom);
            r["statefulVtec"]["initialState"]["data0131"] =
                json!(0xA0 | if initial { 2 } else { 0 });
            for call in r["statefulVtec"]["calls"].as_array_mut().unwrap() {
                call["compactCode"] = json!(35);
            }
            let output = run(r);
            let mut prior = initial;
            for cp in output["statefulSequences"][0]["checkpoints"]
                .as_array()
                .unwrap()
            {
                assert_eq!(cp["status"], 0);
                assert_eq!(
                    cp["stateBefore"]["data0131"],
                    0xA0 | if prior { 2 } else { 0 }
                );
                prior = 35 > if prior { set } else { clear };
                assert_eq!(
                    cp["stateAfter"]["data0131"],
                    0xA0 | if prior { 2 } else { 0 }
                );
            }
            for code in [set - 1, set, set + 1, clear - 1, clear, clear + 1] {
                let mut rom = vec![0; 32768];
                rom[0x122C..0x122C + program.len()].copy_from_slice(&program);
                rom[0x6542] = set;
                rom[0x6543] = clear;
                let mut r = request(rom);
                r["statefulVtec"]["initialState"]["data0131"] = json!(if initial { 2 } else { 0 });
                for call in r["statefulVtec"]["calls"].as_array_mut().unwrap() {
                    call["compactCode"] = json!(code);
                }
                let output = run(r);
                let mut prior = initial;
                for cp in output["statefulSequences"][0]["checkpoints"]
                    .as_array()
                    .unwrap()
                {
                    prior = code > if prior { set } else { clear };
                    assert_eq!(cp["stateAfter"]["data0131"], if prior { 2 } else { 0 });
                }
            }
        }
    }
}
