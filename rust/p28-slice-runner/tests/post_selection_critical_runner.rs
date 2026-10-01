//! Invented full-machine process probes. No OEM routine, table or helper bytes.
use p28_slice_runner::runner::run_request;
use serde_json::{json, Value};
use std::{
    io::Write,
    process::{Command, Stdio},
};

fn emit(rom: &mut [u8], pc: usize, bytes: &[u8]) {
    rom[pc..pc + bytes.len()].copy_from_slice(bytes);
}
fn jge(rom: &mut [u8], start: usize, exit: usize) {
    let mut pc = start;
    while exit - pc > 129 {
        emit(rom, pc, &[0xCD, 126]);
        pc += 128;
    }
    emit(rom, pc, &[0xCD, (exit - pc - 2) as u8]);
}
fn request(partial: bool) -> Value {
    let mut rom = vec![0u8; 32768];
    // Hollow stage bridges plus a different immediate/store producer, not the OEM bodies.
    for (start, exit) in [
        (0x487B, 0x48F5),
        (0x1966, 0x19AC),
        (0x19AC, 0x1A1E),
        (0x1A1E, 0x1A38),
        (0xA0C, 0xA45),
        (0xA62, 0xA77),
        (0x12FC, 0x1340),
        (0x1340, 0x1347),
    ] {
        jge(&mut rom, start, exit);
    }
    emit(&mut rom, 0x1347, &[0x67, 9, 3, 0xD4, 0x40]);
    jge(&mut rom, 0x134C, 0x1350);
    emit(
        &mut rom,
        0x1F43,
        &[0x44, 0x98, 2, 0, 0xE4, 0x5A, 0x90, 0x35, 0x03, 0x99, 0x7A],
    );
    emit(&mut rom, 0x7A99, &[0x45, 0x7C, 0x58, 0x03, 0xB7, 0x1F]);
    emit(&mut rom, 0x217A, &[0xDC, 0x24, 0x17]);
    emit(&mut rom, 0x2194, &[0x67, 5, 0, 0x8B]);
    jge(&mut rom, 0x2198, 0x21DB);
    emit(&mut rom, 0x21DB, &[0x67, 0, 0, 0xC9, 0x12]);
    emit(
        &mut rom,
        0x21F2,
        &[0x67, 0xBC, 2, 0x8B, 0x62, 0xB4, 3, 0xD2],
    );
    jge(&mut rom, 0x21FA, 0x2204);
    emit(&mut rom, 0x2204, &[0x67, 0x41, 1, 0xD4, 0x50]);
    jge(&mut rom, 0x2209, 0x223B);
    emit(&mut rom, 0x223B, &[0xE4, 0x50, 0x50]);
    jge(&mut rom, 0x223E, 0x2259);
    // Rearranged019x and quartet store order, with an invented multiply-by3 helper.
    for (pc, bytes) in [
        (0x2259, vec![0x90, 0x7C, 0x94]),
        (0x225C, vec![0xB5, 0x1A, 0xD0, 0xA0, 2]),
        (0x2261, vec![0xD4, 0x90]),
        (0x2263, vec![0xA2, 0xD0, 0xFE]),
        (0x2266, vec![0xD4, 0x92]),
        (0x2268, vec![0xE5, 0xF8]),
        (0x226A, vec![0xD5, 0x1A]),
        (0x226C, vec![0xA2, 0xE0, 1]),
        (0x226F, vec![0x90, 0x9D, 0xF8, 0x60]),
        (0x2273, vec![0xC9, 0x2A]),
        (0x229F, vec![0x90, 0x15]),
        (0x22A1, vec![0xE2]),
        (0x22A2, vec![0x32, 0x98, 0x59]),
        (0x22A5, vec![0xD0, 0xBC, 3]),
        (0x22A8, vec![0xD0, 0xB6, 3]),
        (0x22AB, vec![0xD0, 0xBA, 3]),
        (0x22AE, vec![0xD0, 0xB8, 3]),
        (0x5998, vec![0x44, 0x98, 3, 0, 0x90, 0x35, 1]),
    ] {
        emit(&mut rom, pc, &bytes);
    }
    if partial {
        emit(&mut rom, 0x2263, &[0x47, 0x81]);
    }
    let sources = json!({"source015a":20,"source015c":65535,"source015e":255,"source0160":65535,"source0162":65535,"source0164":255,"source0165":200,"source0166":0,"source0167":0,"source0168":255,"source0133":107,"source0142":0,"source0144":0,"source0146":0,"source0148":0,"source0149":0,"source014a":0,"source014c":0,"counter00f2":0});
    let call = |i| json!({"adaptive":{"fuel":{"index":i,"rawPeriod":99,"rawLoad":1,"rawMap0Rpm":2,"rawMap1Rpm":3,"sources":sources},"raw00ce":1100,"rawD9":0,"bank1":false,"reset217":false,"reset214":false,"mode212":false,"enable223":true,"fixedSource":false,"timerTicks":0,"counterTicks":0},"disable125":false,"disable12e":false});
    json!({"protocolVersion":1,"operation":"fuelPostSelectionCriticalChain","images":[{"id":"baseline","rom":rom}],"scratchPatterns":[0,85,170],"allowAssumptions":[],"fuelPostSelectionCriticalChain":{
        "formatVersion":1,"initialState":{"adaptive":{"joint":{"fuel":{"loadIndex":0,"map0RpmIndex":0,"map1RpmIndex":0,"loadFraction":0,"map0RpmFraction":0,"map1RpmFraction":0,"selector0127":165,"consumerFactor013f":0,"consumerOutput0140":0},"data0124":225,"data012b":173,"data01d7":7,"producerMode012c":149,"producerSelector012f":128,"hysteresis0130":165},"ramCut":100,"ramResume":110,"timer":7,"counter":5,"ie":47768,"restoreIe":23205},"previous03b4":321},"traceCallIndexes":[0],"calls":[call(0),call(1)]}})
}
fn process(request: &Value) -> Value {
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
        .write_all(&serde_json::to_vec(request).unwrap())
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
fn real_process_invented_producer_carriers_ie_pswh_ram_configuration_and_result_no_reset() {
    let r = process(&request(false));
    assert_eq!(r["runnerVersion"], env!("CARGO_PKG_VERSION"));
    assert!(r.get("consumerSequences").is_none());
    for seq in r["criticalSequences"].as_array().unwrap() {
        for (i, row) in seq["checkpoints"].as_array().unwrap().iter().enumerate() {
            assert_eq!(row["status"], 0, "{row}");
            assert_eq!(row["critical"]["entry"], row["prefix"]["consumer"]["exit"]);
            assert_eq!(row["critical"]["exit"]["pc"], 0x22B1);
            assert_eq!(row["prefix"]["selectedScaledWordX1"], 321);
            assert_eq!(row["words019x"], json!([321, 321, 321]));
            assert_eq!(row["commonWords03b6"], json!([2100, 2100, 2100, 2100]));
            assert_eq!(
                row["stateBefore"]["ie"],
                if i == 0 { json!(0xBA98) } else { json!(0x5AA5) }
            );
            assert_eq!(row["stateAtEntry"]["ie"], row["stateBefore"]["ie"]);
            assert_eq!(row["stateAfter"]["ie"], 0x5AA5);
            let access = row["critical"]["accesses"].as_array().unwrap();
            assert!(access.contains(&json!([
                0x225C,
                0x1A,
                16,
                1,
                if i == 0 { 0x0280 } else { 0x02A0 }
            ])));
            assert_eq!(
                row["critical"]["stage"]["result"]["programReads"],
                json!([0x60F8])
            );
            assert!(
                !row["critical"]["stage"]["result"]["executedInstructionBytes"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .any(|a| a.as_u64() == Some(0x227A))
            );
            if i == 0 {
                let canary = seq["scratchPattern"].as_u64().unwrap() * 257;
                assert_eq!(
                    row["stateBefore"]["words019x"],
                    json!([canary, canary, canary])
                );
            } else {
                let first = &seq["checkpoints"][0];
                assert_eq!(row["stateBefore"], first["stateAfter"]);
                assert_eq!(
                    row["prefix"]["prefix"]["prefix"]["producer"]["before"],
                    first["critical"]["exit"]
                );
                assert!(access.contains(&json!([0x2261, 0x190, 16, 1, 321])));
            }
        }
    }
}
#[test]
fn real_process_partial_ie_and_ram_writes_retained_whole_result_null_later_events_terminal() {
    let r = process(&request(true));
    for seq in r["criticalSequences"].as_array().unwrap() {
        let a = &seq["checkpoints"][0];
        let b = &seq["checkpoints"][1];
        assert_eq!(a["prefix"]["status"], 0);
        assert_eq!(a["status"], 1);
        assert_eq!(a["critical"]["stage"]["result"]["stopPc"], 0x2263);
        assert!(a["words019x"].is_null());
        assert!(a["commonWords03b6"].is_null());
        assert_eq!(a["stateAfter"]["ie"], 0x0280);
        assert_eq!(a["stateAfter"]["words019x"][0], 321);
        assert_eq!(b["status"], 4);
        assert_eq!(b["prefix"]["status"], 4);
        assert!(b["critical"].is_null());
        assert!(b["stateAtEntry"].is_null());
        assert_eq!(b["stateBefore"], a["stateAfter"]);
        assert_eq!(b["stateAfter"], b["stateBefore"]);
        assert_eq!(b["prefix"]["prefix"]["snapshotWrites"], json!([]));
        assert_eq!(b["prefix"]["prefix"]["prefix"]["ticks"], json!([]));
    }
}
#[test]
fn new_task_refuses_foreign_old_task_ready_carriers_ie_overrides_and_configuration_mutation() {
    let key = "fuelPostSelectionCriticalChain";
    for n in 0..14 {
        let mut r = request(false);
        match n {
            0 => r["operation"] = json!("fuelPostStoreConsumerChain"),
            1 => r["fuelPostStoreConsumerChain"] = r[key].clone(),
            2 => r[key]["calls"][0]["ie"] = json!(0),
            3 => r[key]["calls"][0]["pswh"] = json!(0),
            4 => r[key]["calls"][0]["x1"] = json!(9),
            5 => r[key]["calls"][0]["words019x"] = json!([1, 2, 3]),
            6 => r[key]["initialState"]["word0190"] = json!(1),
            7 => r[key]["calls"][0]["branchChoice"] = json!(true),
            8 => r[key]["calls"][0]["word0150"] = json!(1),
            9 => r["images"][0]["rom"][0x60F8] = json!(1),
            10 => r[key]["formatVersion"] = json!(2),
            11 => r["protocolVersion"] = json!(2),
            12 => r[key]["calls"][0]["adaptive"]["timerTicks"] = json!(33),
            _ => r["allowAssumptions"] = json!(["oki.add-er3-a"]),
        }
        if let Ok(parsed) = serde_json::from_value(r) {
            assert!(run_request(parsed).is_err(), "case{n}");
        }
    }
}

fn generic_request(rom: Vec<u8>, exit: usize, seeds: Value, outputs: Value) -> Value {
    let size = rom.len();
    json!({"protocolVersion":1,"operation":"synthetic","images":[{"id":"invented","rom":rom}],
        "scratchPatterns":[170],"allowAssumptions":[],"synthetic":{"entryPc":0,"exitPcs":[exit],
        "allowedCodeRanges":[[0,size]],"psw":0x3301,"lrb":0x20,"usp":0x280,"instructionBudget":64,
        "dataSeeds":seeds,"outputAddresses":outputs}})
}

#[test]
fn real_generic_process_both_configuration_directions_complete_invented_software_mask_and_ram_chain(
) {
    for (config, optional) in [(0, 17), (1, 99)] {
        // Independent low-PC program. RAM00F0 is analogous diagnostic mask storage,
        // deliberately NOT actual IE001A, and ROM0050 is NOT actual60F8 evidence.
        let mut rom = vec![0; 81];
        emit(
            &mut rom,
            0,
            &[
                0x67, 0x41, 1, 0x50, 0xD4, 0xA0, 0xB5, 0xF0, 0xD0, 0xA0, 2, 0xE5, 0xF0, 0xD4, 0xAA,
                0xA2, 0xD0, 0xFE, 0xE4, 0xA2, 0xD4, 0xA4, 0x90, 0x7C, 0xA2, 0xE5, 0xF8, 0xD5, 0xF0,
                0xA2, 0xE0, 1, 0x90, 0x9D, 0x50, 0, 0xC9, 5, 0x67, 99, 0, 0xCD, 3, 0x67, 17, 0,
                0xD4, 0xA6,
            ],
        );
        rom[80] = config;
        let r = process(&generic_request(
            rom,
            48,
            json!([
                [0xF0, 0x98],
                [0xF1, 0xBA],
                [0xF8, 0xA5],
                [0xF9, 0x5A],
                [0x1A2, 7],
                [0x1A3, 0]
            ]),
            json!([
                0xF0, 0xF1, 0x1AA, 0x1AB, 0x1A0, 0x1A1, 0x1A2, 0x1A3, 0x1A4, 0x1A5, 0x1A6, 0x1A7
            ]),
        ));
        let result = &r["syntheticResult"];
        assert_eq!(result["status"], 0, "{result}");
        assert_eq!(
            result["outputs"],
            json!([0xA5, 0x5A, 0x80, 2, 0x41, 1, 0x41, 1, 7, 0, optional, 0])
        );
        assert_eq!(result["programReads"], json!([80]));
        let trace = result["trace"].as_array().unwrap();
        let clear = trace.iter().find(|e| e["pc"] == 15).unwrap();
        let set = trace.iter().find(|e| e["pc"] == 29).unwrap();
        assert_eq!(clear["psw"].as_u64().unwrap() & 0x100, 0);
        assert_eq!(set["psw"].as_u64().unwrap() & 0x100, 0x100);
        let branch = trace.iter().find(|e| e["pc"] == 36).unwrap();
        assert_eq!(
            branch["nextPc"],
            if config == 0 { json!(43) } else { json!(38) }
        );
        assert_eq!(trace.iter().any(|e| e["pc"] == 38), config != 0);
    }
}

#[test]
fn exact_generic_supplement_rejects_wrong_mask_address_width_status_bit_and_disputed_forms() {
    for bytes in [
        vec![0xB5, 0xF0, 0xD0, 0xA1, 2],
        vec![0xB5, 0xF2, 0xD0, 0xA0, 2],
        vec![0xB5, 0x1A, 0xD0, 0xA0, 2],
        vec![0xC5, 0xF0, 0xD0, 0xA0],
        vec![0xA2, 0xD0, 0xFD],
        vec![0xA2, 0xE0, 2],
        vec![0x47, 0x81],
        vec![0x45, 0x81],
        vec![0xA7, 0x90],
    ] {
        let end = bytes.len();
        let r = process(&generic_request(bytes, end, json!([]), json!([])));
        assert_ne!(r["syntheticResult"]["status"], 0);
        assert_eq!(r["syntheticResult"]["steps"], 0);
        assert_eq!(r["syntheticResult"]["usedAssumptions"], json!([]));
    }
}

fn common_request(partial: bool) -> Value {
    let mut r = request(false);
    let mut s = r
        .as_object_mut()
        .unwrap()
        .remove("fuelPostSelectionCriticalChain")
        .unwrap();
    let prefix = s["initialState"].take();
    s["initialState"] = json!({"prefix":prefix,"softwareSources":{
        "word011aMask1034":0x1034,"bit011f5":true,"bit0120_0":true,
        "byte00be":73,"bit00b7_0":true,"word0136":17,"history013b":19,"history013d":23
    }});
    r["operation"] = json!("fuelCommonResultConsumerChain");
    r["fuelCommonResultConsumerChain"] = s;
    let rom = r["images"][0]["rom"].as_array_mut().unwrap();
    let mut put = |pc: usize, bytes: &[u8]| {
        for (i, b) in bytes.iter().enumerate() {
            rom[pc + i] = json!(*b);
        }
    };
    // Invented native byte history copy, mode RMW and spaced jumps, not OEM source math.
    put(
        0x22B1,
        &[0xF4, 0x3D, 0xD4, 0x3B, 0xC4, 0x2B, 0x3A, 0xCB, 0x6B],
    );
    put(0x2325, if partial { &[0xC8, 0] } else { &[0xCB, 0x43] });
    put(0x236A, &[0xD4, 0x3B]);
    r
}

#[test]
fn real_common_process_native_prefix_stop_matches_continuation_entry_without_reseed() {
    let r = process(&common_request(false));
    assert!(r.get("criticalSequences").is_none());
    assert_eq!(r["entryContracts"][0]["dynamicQuartetReaders"], json!([]));
    assert_eq!(
        r["entryContracts"][0]["overallConsumerChain"],
        "Partial;StaticConsumersNotRun"
    );
    for seq in r["commonResultSequences"].as_array().unwrap() {
        let rows = seq["checkpoints"].as_array().unwrap();
        for (i, row) in rows.iter().enumerate() {
            assert_eq!(row["status"], 0, "{row}");
            assert_eq!(row["prefix"]["critical"]["exit"]["pc"], 0x22B1);
            assert_eq!(
                row["commonConsumer"]["entry"],
                row["prefix"]["critical"]["exit"]
            );
            assert_eq!(row["commonConsumer"]["exit"]["pc"], 0x236C);
            assert_eq!(row["softwareResult13b"], 23);
            assert_eq!(
                row["stateAtEntry"]["byte013b"],
                if i == 0 { json!(19) } else { json!(23) }
            );
            assert_eq!(row["stateAfter"]["byte013d"], 23);
            assert_eq!(row["stateAfter"]["word0136"], 17);
            assert_eq!(row["stateAfter"]["byte00be"], 73);
            assert_eq!(
                row["stateAfter"]["word011a"].as_u64().unwrap() & 0x1034,
                0x1034
            );
            assert_eq!(
                row["stateAfter"]["prefix"]["commonWords03b6"],
                json!([2100, 2100, 2100, 2100])
            );
            let accesses = row["commonConsumer"]["accesses"].as_array().unwrap();
            assert!(accesses.contains(&json!([0x22B1, 0x13D, 8, 0, 23])));
            assert!(accesses.contains(&json!([0x236A, 0x13B, 8, 1, 23])));
            assert!(accesses
                .iter()
                .all(|a| !(0x3B6..0x3BE).contains(&a[1].as_u64().unwrap())));
            if i > 0 {
                assert_eq!(row["stateBefore"], rows[i - 1]["stateAfter"]);
                assert_eq!(
                    row["prefix"]["prefix"]["prefix"]["prefix"]["producer"]["before"],
                    rows[i - 1]["commonConsumer"]["exit"]
                );
            }
        }
    }
}

#[test]
fn real_common_process_partial_keeps_native_output_history_but_later_event_is_not_run() {
    let r = process(&common_request(true));
    for seq in r["commonResultSequences"].as_array().unwrap() {
        let a = &seq["checkpoints"][0];
        let b = &seq["checkpoints"][1];
        assert_eq!(a["prefix"]["status"], 0);
        assert_eq!(a["status"], 1);
        assert_eq!(a["commonConsumer"]["stage"]["result"]["stopPc"], 0x2325);
        assert!(a["softwareResult13b"].is_null());
        assert_eq!(a["stateAfter"]["byte013b"], 23);
        assert!(a["commonConsumer"]["accesses"]
            .as_array()
            .unwrap()
            .contains(&json!([0x22B3, 0x13B, 8, 1, 23])));
        assert_eq!(b["status"], 4);
        assert_eq!(b["prefix"]["status"], 4);
        assert!(b["commonConsumer"].is_null());
        assert!(b["stateAtEntry"].is_null());
        assert_eq!(b["stateBefore"], a["stateAfter"]);
        assert_eq!(b["stateAfter"], b["stateBefore"]);
        assert_eq!(b["prefix"]["prefix"]["prefix"]["snapshotWrites"], json!([]));
        assert_eq!(
            b["prefix"]["prefix"]["prefix"]["prefix"]["ticks"],
            json!([])
        );
    }
}

#[test]
fn common_schema_rejects_ready_results_per_event_sources_branch_flags_and_foreign_stimuli() {
    for n in 0..13 {
        let mut r = common_request(false);
        let key = "fuelCommonResultConsumerChain";
        match n {
            0 => r[key]["calls"][0]["softwareResult13b"] = json!(7),
            1 => {
                r[key]["calls"][0]["softwareSources"] =
                    r[key]["initialState"]["softwareSources"].clone()
            }
            2 => r[key]["calls"][0]["branchChoice"] = json!(true),
            3 => r[key]["calls"][0]["a"] = json!(7),
            4 => r[key]["calls"][0]["cf"] = json!(true),
            5 => r[key]["calls"][0]["pc"] = json!(0x22B1),
            6 => r[key]["initialState"]["commonWords03b6"] = json!([7, 7, 7, 7]),
            7 => r[key]["initialState"]["softwareSources"]["word011aMask1034"] = json!(0x8000),
            8 => r["fuelPostSelectionCriticalChain"] = json!({}),
            9 => r["operation"] = json!("fuelPostSelectionCriticalChain"),
            10 => r[key]["calls"] = json!([]),
            11 => r[key]["initialState"]["softwareSources"]["irqDelivery"] = json!(true),
            _ => r["allowAssumptions"] = json!(["oki.add-er3-a"]),
        }
        if let Ok(parsed) = serde_json::from_value(r) {
            assert!(run_request(parsed).is_err(), "case{n}");
        }
    }
}

#[test]
fn real_process_four_native_slots_are_loop_read_and_accumulated_before_fake_peripheral() {
    for words in [[7u16; 4], [3, 11, 29, 47]] {
        let mut rom = vec![0; 54];
        let mut pc = 0usize;
        let mut put = |bytes: &[u8]| {
            emit(&mut rom, pc, bytes);
            pc += bytes.len();
        };
        put(&[0x60, 0, 0]);
        for (i, word) in words.iter().enumerate() {
            put(&[
                0x67,
                *word as u8,
                (*word >> 8) as u8,
                0xD0,
                (i * 2) as u8,
                3,
            ]);
        }
        put(&[0x44, 0x98, 0, 0]);
        // Native X1 progression and native back-edge, not four unrolled host reads.
        put(&[
            0xE0, 0, 3, 0x08, 0x88, 0x90, 0x80, 2, 0, 0x90, 0xC0, 8, 0, 0xCA, 0xF1,
        ]);
        put(&[0x60, 0, 0, 0xD0, 0x40, 3]);
        put(&[0xF5, 0x24]); // fake peripheral-like access must not execute.
        assert_eq!(pc, 54);
        let r = process(&generic_request(rom, 52, json!([]), json!([0x340, 0x341])));
        let result = &r["syntheticResult"];
        assert_eq!(result["status"], 0, "{result}");
        assert_eq!(result["stopPc"], 52);
        let sum = words.iter().copied().sum::<u16>();
        assert_eq!(result["outputs"], json!([sum as u8, (sum >> 8) as u8]));
        let trace = result["trace"].as_array().unwrap();
        assert_eq!(trace.iter().filter(|e| e["pc"] == 31).count(), 4);
        assert_eq!(
            trace
                .iter()
                .filter(|e| e["pc"] == 44 && e["nextPc"] == 31)
                .count(),
            3
        );
        assert!(!trace.iter().any(|e| e["pc"] == 52));
        assert_eq!(result["usedAssumptions"], json!([]));
    }
}
