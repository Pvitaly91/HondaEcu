//! Invented programs only. These exercise transport and shared-memory wiring,
//! not OEM formulas or an actual-ROM validation pass.
use serde_json::{json, Value};
use std::{
    io::Write,
    process::{Command, Stdio},
};

fn process(request: &Value) -> std::process::Output {
    let mut p = Command::new(env!("CARGO_BIN_EXE_p28-slice-runner"))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    p.stdin
        .take()
        .unwrap()
        .write_all(request.to_string().as_bytes())
        .unwrap();
    p.wait_with_output().unwrap()
}
fn run(request: &Value) -> Value {
    let r = process(request);
    assert!(r.status.success(), "{}", String::from_utf8_lossy(&r.stderr));
    serde_json::from_slice(&r.stdout).unwrap()
}
fn put(rom: &mut [u8], pc: usize, bytes: &[u8]) {
    rom[pc..pc + bytes.len()].copy_from_slice(bytes);
}
fn jump_to_exit(rom: &mut [u8], pc: usize, exit: usize, conditional: bool) {
    put(
        rom,
        pc,
        &[if conditional { 0xC9 } else { 0xCB }, (exit - pc - 2) as u8],
    );
}
fn program(code: u8) -> Vec<u8> {
    let mut rom = vec![0xFF; 32768];
    // Toy acquisition copies a frozen word to the caller-selected slot.
    put(
        &mut rom,
        0x56BE,
        &[
            0xF5, 0xA2, 0x53, 0xF8, 0x50, 0xE5, 0x3A, 0xD0, 0x60, 0x03, 0xF9,
        ],
    );
    jump_to_exit(&mut rom, 0x56C9, 0x5719, true);
    // Toy G copies slot zero to T through native XCHG (not division by five).
    put(
        &mut rom,
        0x0772,
        &[
            0x90, 0x15, 0xE0, 0x60, 0x03, 0xB5, 0xC4, 0x10, 0x03, 0xA5, 0x07,
        ],
    );
    // Toy F creates a deliberately non-firmware byte; decision must consume it.
    put(&mut rom, 0x07C7, &[0x77, code, 0xD3, 0xB3]);
    jump_to_exit(&mut rom, 0x07CB, 0x0822, false);
    // Toy decision copies native Code to persistent prior storage, increments
    // the output-data latch, and sets a mirror bit without any host reseeding.
    put(
        &mut rom,
        0x122C,
        &[
            0xF4, 0x33, 0xD4, 0x31, 0xF5, 0x22, 0x86, 1, 0xD5, 0x22, 0xC4, 0x27, 0x1A, 0x03, 0xFC,
            0x12,
        ],
    );
    rom
}
fn stimulus() -> Value {
    let raw = json!({"raw00CC":31,"raw00D9":9,"snapshot0119":2,"snapshot011A":0x1020,"snapshot011C":64,"raw0132":73,"raw0199":5});
    json!({"formatVersion":1,"initialState":{
        "acquisition":{"previousTimestamp":15,"samples":[9,8,7,6,5,4],"data0128":0,"data00AE":2,"data00B6":0xA0,"data011F":0xA0,
            "previousT":0x3412,"data0217":0xA0,"data0231":0x40,"data0136":0x9876},
        "decision":{"data0131":0xA6,"data0127":0x80,"data0198":44,"data01D8":7,"data01D9":8,"data01DF":9,"data00F3":50,"p1OutputData":0xA4},
        "data011E":0xA1,"data00B8":0xB5,"code":0xEE,"raw":raw},
        "events":(0..3).map(|i|json!({"index":i,"tmr2":0x1234+i,"irqh":0,"tcon2":0,"slot":0,"runDecision":true,"context":i%2,"enabled":true,"raw":raw,"fastTicks":0,"slowTicks":0})).collect::<Vec<_>>(),
        "traceEventIndexes":[0]})
}
fn request(rom: Vec<u8>) -> Value {
    json!({"protocolVersion":1,"operation":"integratedCaptureVtec","images":[{"id":"baseline","rom":rom}],"scratchPatterns":[0,85,170],"allowAssumptions":[],"integratedChain":stimulus()})
}

#[test]
fn actual_subprocess_keeps_one_history_native_code_and_latch_across_capture_scope() {
    let input = request(program(77));
    let saved = input.clone();
    let r = run(&input);
    for s in r["chainSequences"].as_array().unwrap() {
        assert_eq!(s["completedDecisions"], 3);
        for i in 0..3 {
            let c = &s["checkpoints"][i];
            let stages = &c["stages"];
            assert_eq!(
                stages[0]["stateAfter"]["acquisition"]["samples"][0],
                0x1234 + i
            );
            assert_eq!(
                stages[2]["stateAfter"]["acquisition"]["previousT"],
                0x1234 + i
            );
            assert_eq!(stages[3]["stateAfter"]["code"], 77);
            assert_eq!(stages[4]["stateBefore"]["code"], 77);
            assert_eq!(stages[4]["stateAtEntry"]["code"], 77);
            assert_eq!(c["stateAfter"]["decision"]["data0131"], 77);
            assert_eq!(
                stages[0]["stateAfter"]["decision"]["p1OutputData"],
                0xA4 + i
            );
            assert_eq!(c["stateAfter"]["decision"]["p1OutputData"], 0xA5 + i);
            assert_eq!(c["stateAfter"]["decision"]["data01D8"], 7);
            assert_eq!(c["stateAfter"]["raw"]["raw0132"], 73); // adjacent byte not overwritten by F
            assert_eq!(c["stateAfter"]["acquisition"]["data011F"], 0xA0);
            assert_eq!(c["stateAfter"]["data011E"].as_u64().unwrap() & !24, 0xA1);
            assert_eq!(stages[0]["architectureAtEntry"]["lrb"], 0x21);
            assert_eq!(stages[2]["architectureAtEntry"]["lrb"], 0x40);
            assert_eq!(stages[4]["architectureAtEntry"]["lrb"], 0x20);
            for stage in stages.as_array().unwrap() {
                assert_eq!(stage["architectureAfter"]["ssp"], 0x7FE);
            }
            if i > 0 {
                assert_eq!(stages[0]["stateBefore"]["decision"]["data0131"], 77);
            }
        }
    }
    assert_eq!(input, saved);
}
#[test]
fn all_three_images_execute_their_own_early_stage_bytes_and_never_align_histories() {
    let mut q = request(program(17));
    q["images"]
        .as_array_mut()
        .unwrap()
        .push(json!({"id":"intermediate","rom":program(91)}));
    q["images"]
        .as_array_mut()
        .unwrap()
        .push(json!({"id":"derived","rom":program(91)}));
    let r = run(&q);
    for s in r["chainSequences"].as_array().unwrap() {
        let code = if s["imageIndex"] == 0 { 17 } else { 91 };
        assert_eq!(
            s["checkpoints"][2]["stateAfter"]["decision"]["data0131"],
            code
        );
        assert_eq!(s["checkpoints"][1]["stateBefore"]["code"], code);
    }
    for pattern in [0, 85, 170] {
        let sequences = r["chainSequences"].as_array().unwrap();
        let b = sequences
            .iter()
            .find(|s| s["imageIndex"] == 1 && s["scratchPattern"] == pattern)
            .unwrap();
        let c = sequences
            .iter()
            .find(|s| s["imageIndex"] == 2 && s["scratchPattern"] == pattern)
            .unwrap();
        assert_eq!(b["checkpoints"], c["checkpoints"]); // All boundaries, architecture and native side effects, not request alone.
    }
}
#[test]
fn captures_are_unavailable_to_f_and_p1_is_unavailable_to_acquisition_without_erasing_latch() {
    for (entry, bytes, position) in [(0x56BE, vec![0xF5, 0x22], 0), (0x07C7, vec![0xE5, 0x3A], 3)] {
        let mut rom = program(17);
        put(&mut rom, entry, &bytes);
        let r = run(&request(rom));
        for s in r["chainSequences"].as_array().unwrap() {
            assert_eq!(s["stopEventIndex"], 0);
            let c = &s["checkpoints"][0];
            assert_eq!(c["stages"][position]["status"], 2);
            assert_eq!(c["stateAfter"]["decision"]["p1OutputData"], 0xA4);
            assert!(c["softwareRequest"].is_null());
            assert_eq!(
                s["checkpoints"][1]["stateAfterInputs"],
                s["checkpoints"][0]["stateAfter"]
            );
            assert!(s["checkpoints"][1]["callerWrites"]
                .as_array()
                .unwrap()
                .is_empty());
        }
    }
}
#[test]
fn permissions_are_stage_specific_cumulative_and_terminal_suffix_never_resumes() {
    let mut rom = program(17);
    // Sparse invented probes at the reviewed permission PCs, not OEM blocks.
    put(&mut rom, 0x0772, &[0x03, 0x7E, 0x07]);
    put(&mut rom, 0x077E, &[0x45, 0x81, 0x03, 0xA5, 0x07]);
    jump_to_exit(&mut rom, 0x07C7, 0x07F8, false);
    put(&mut rom, 0x07F8, &[0x47, 0x81]);
    jump_to_exit(&mut rom, 0x07FA, 0x0822, false);
    put(&mut rom, 0x122C, &[0x03, 0xB4, 0x12]);
    put(&mut rom, 0x12B4, &[0xA7, 0x99, 0x03, 0xFC, 0x12]);
    let permissions = [
        "oki.add-er1-a",
        "oki.add-er3-a",
        "oki.subb-a-off-n8-encoding",
    ];
    for count in 0..=3 {
        let mut q = request(rom.clone());
        q["allowAssumptions"] = json!(&permissions[..count]);
        let r = run(&q);
        for s in r["chainSequences"].as_array().unwrap() {
            let stages = &s["checkpoints"][0]["stages"];
            if count < 3 {
                assert_eq!(stages[count + 2]["status"], 1);
                assert_eq!(s["stopEventIndex"], 0);
                assert!(s["checkpoints"][1]["softwareRequest"].is_null());
            } else {
                assert_eq!(s["completedDecisions"], 3);
                assert_eq!(
                    s["checkpoints"][2]["cumulativeAssumptions"]
                        .as_array()
                        .unwrap()
                        .len(),
                    3
                );
            }
            assert_eq!(
                s["checkpoints"][0]["cumulativeAssumptions"]
                    .as_array()
                    .unwrap()
                    .len(),
                count
            );
        }
    }
    // er3 permission must not authorize G's er1 form.
    let mut q = request(rom);
    q["allowAssumptions"] = json!([permissions[1], permissions[2]]);
    assert_eq!(
        run(&q)["chainSequences"][0]["checkpoints"][0]["stages"][2]["status"],
        1
    );
}
#[test]
fn unknown_exact_form_and_unsupported_mode_leave_partial_state_and_null_outputs() {
    let mut rom = program(17);
    put(&mut rom, 0x07C7, &[0xF5, 0xCC]); // byte direct load is not an admitted F form
    let r = run(&request(rom));
    assert_eq!(
        r["chainSequences"][0]["checkpoints"][0]["stages"][3]["status"],
        5
    );
    assert!(r["chainSequences"][0]["checkpoints"][0]["softwareRequest"].is_null());
    let mut q = request(program(17));
    q["integratedChain"]["initialState"]["acquisition"]["data011F"] = json!(4);
    let r = run(&q);
    let first = &r["chainSequences"][0]["checkpoints"][0];
    assert_eq!(first["stages"][0]["status"], 5);
    assert!(first["stages"][0]["execution"].is_null());
    assert_eq!(
        r["chainSequences"][0]["checkpoints"][1]["stages"][0]["status"],
        4
    );
}
#[test]
fn bounded_schema_rejects_produced_value_overrides_and_foreign_task_stimuli() {
    for field in [
        "compactCode",
        "code",
        "samples",
        "T",
        "thresholdPriorBits",
        "data0131",
    ] {
        let mut q = request(program(17));
        q["integratedChain"]["events"][0][field] = json!(0);
        assert!(!process(&q).status.success());
    }
    for (field, value) in [
        ("slot", json!(6)),
        ("fastTicks", json!(33)),
        ("context", json!(2)),
        ("index", json!(1)),
        ("raw", Value::Null),
    ] {
        let mut q = request(program(17));
        q["integratedChain"]["events"][0][field] = value;
        assert!(!process(&q).status.success());
    }
    let mut q = request(program(17));
    q["allowAssumptions"] = json!(["allow-all-unknown"]);
    assert!(!process(&q).status.success());
    let mut q = request(program(17));
    q["integratedChain"]["traceEventIndexes"] = json!([0, 0]);
    assert!(!process(&q).status.success());
}

#[test]
fn native_counter_probe_and_bounded_trace_are_not_host_decrements() {
    let mut rom = program(17);
    // Invented body: same-value constant stores, intentionally NOT native decay.
    put(&mut rom, 0x5BD0, &[0x77, 41, 0xD4, 0xD8, 0x03, 0xD9, 0x5B]);
    let mut q = request(rom);
    q["integratedChain"]["events"][0]["fastTicks"] = json!(32);
    let r = run(&q);
    for s in r["chainSequences"].as_array().unwrap() {
        let t = &s["checkpoints"][0]["stages"][1];
        assert_eq!(t["status"], 0);
        assert_eq!(t["tickRuns"].as_array().unwrap().len(), 64);
        assert_eq!(t["nativeWrites"], json!(vec![[0x1D8, 8, 41]; 64]));
        assert_eq!(t["execution"]["steps"], 192);
        assert_eq!(t["execution"]["trace"].as_array().unwrap().len(), 128);
        assert_eq!(
            s["checkpoints"][2]["stateAfter"]["decision"]["data01D8"],
            41
        );
        assert_eq!(s["checkpoints"][2]["stateAfter"]["decision"]["data01D9"], 8);
    }
}

#[test]
fn refused_divide_by_zero_is_not_an_executed_instruction_extent() {
    let mut rom = program(17);
    // Standalone invented zero-divisor probe, not OEM helper bytes.
    put(
        &mut rom,
        0x122C,
        &[0x77, 0, 0xD4, 0x00, 0xA2, 0x36, 0x03, 0xFC, 0x12],
    );
    let r = run(&request(rom));
    let d = &r["chainSequences"][0]["checkpoints"][0]["stages"][4];
    assert_eq!(d["status"], 1);
    assert_eq!(d["execution"]["stopPc"], 0x1230);
    assert_eq!(d["execution"]["steps"], 2);
    assert_eq!(
        d["execution"]["executedInstructionBytes"],
        json!([0x122C, 0x122D, 0x122E, 0x122F])
    );
    assert_eq!(
        r["chainSequences"][0]["checkpoints"][1]["stages"][0]["status"],
        4
    );
}
