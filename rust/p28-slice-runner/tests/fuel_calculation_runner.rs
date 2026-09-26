//! Newly composed programs only; no OEM routine fixture.
use p28_slice_runner::{
    bus::Bus,
    cpu::Cpu,
    decoder::decode,
    exec::{read_data_u16, step, write_data_u16},
    fuel_calculation::admission,
    instruction_forms::FormAdmission,
    runner::run_request,
};
use serde_json::{json, Value};
use std::{
    io::Write,
    process::{Command, Stdio},
};

fn request() -> Value {
    json!({"protocolVersion":1,"operation":"fuelCalculationChain","images":[{"id":"baseline","rom":vec![0u8;32768]}],
    "scratchPatterns":[0,85,170],"allowAssumptions":[],"fuelCalculationChain":{"formatVersion":1,"initialState":{
        "loadIndex":0,"map0RpmIndex":0,"map1RpmIndex":0,"loadFraction":0,"map0RpmFraction":0,"map1RpmFraction":0,
        "selector0127":165,"consumerFactor013f":0,"consumerOutput0140":0},"calls":[
            {"index":0,"rawLoad":1,"rawMap0Rpm":2,"rawMap1Rpm":3,"factor0158":513},
            {"index":1,"rawLoad":255,"rawMap0Rpm":255,"rawMap1Rpm":255,"factor0158":65535}],"traceCallIndexes":[0]}})
}

#[test]
fn closed_strict_operation_rejects_hidden_inputs_and_old_task() {
    for case in 0..10 {
        let mut r = request();
        match case {
            0 => r["fuelCalculationChain"]["calls"][0]["selector0127"] = json!(2),
            1 => r["fuelCalculationChain"]["calls"][0]["data0140"] = json!(32),
            2 => r["fuelCalculationChain"]["calls"][0]["expectedProduct"] = json!(42),
            3 => r["fuelCalculationChain"]["calls"][0]["index"] = json!(9),
            4 => r["fuelCalculationChain"]["initialState"]["consumerOutput0140"] = json!(8),
            5 => r["allowAssumptions"] = json!(["oki.add-er3-a"]),
            6 => r["operation"] = json!("fuelMapLookup"),
            7 => r["fuelCalculationChain"]["traceCallIndexes"] = json!([0, 0]),
            8 => r["fuelCalculationChain"]["initialState"]["loadIndex"] = json!(9),
            _ => r["fuelCalculationChain"]["formatVersion"] = json!(2),
        }
        if let Ok(r) = serde_json::from_value(r) {
            assert!(run_request(r).is_err());
        }
    }
}
#[test]
fn terminal_suffix_does_not_apply_factor_selector_or_claim_retained_result() {
    let r = serde_json::to_value(run_request(serde_json::from_value(request()).unwrap()).unwrap())
        .unwrap();
    for s in r["fuelCalculationSequences"].as_array().unwrap() {
        let rows = &s["checkpoints"];
        assert_eq!(rows[0]["status"], 1);
        assert_eq!(rows[0]["factor0158After"], 513);
        assert_eq!(rows[1]["status"], 4);
        assert!(rows[1]["input"].is_null());
        assert!(rows[1]["output"].is_null());
        assert_eq!(rows[1]["factor0158After"], 513);
        assert_eq!(rows[1]["prefix"]["stateAfter"]["selector0127"], 165);
        assert_eq!(rows[1]["accesses"], json!([]));
    }
}
#[test]
fn primary_exact_forms_dd_and_unrelated_assumptions_stay_separate() {
    for (bytes, dd, allowed) in [
        (&[0x45, 0xE7][..], false, true),
        (&[0x45, 0xE7][..], true, true),
        (&[0xE5, 6][..], false, true),
        (&[0xE5, 7][..], true, false),
        (&[0x83][..], true, true),
        (&[0x83][..], false, false),
        (&[0x47, 0x81][..], true, false),
        (&[0x45, 0x81][..], true, false),
        (&[0xC4, 0x45, 0xA2][..], false, false),
    ] {
        let d = decode(dd, |i| bytes.get(i).copied().unwrap_or(0));
        assert_eq!(
            d.as_ref()
                .is_some_and(|d| admission(d) == FormAdmission::Allowed),
            allowed
        );
    }
}
#[test]
fn decoded_mul_and_word_shift_preserve_bank_canaries_and_have_32_bit_layout() {
    for a in [0u16, 1, 511, 512, 0x7FFF, 0x8000, 0xFFFF] {
        for b in [0u16, 1, 513, 0x8000, 0xFFFF] {
            for bank in [0x20u16, 0x40, 0x41] {
                let mut cpu = Cpu::new();
                cpu.lrb = bank;
                cpu.dd = true;
                cpu.cf = true;
                cpu.zf = true;
                cpu.hc = true;
                let mut bus = Bus::new(vec![0x90, 0x35, 0x45, 0xE7], 0xA5);
                cpu.a = a;
                let base = cpu.bank_base();
                write_data_u16(&mut cpu, &mut bus, base, b);
                step(&mut cpu, &mut bus).unwrap();
                let product = u32::from(a) * u32::from(b);
                assert_eq!(cpu.a, product as u16);
                assert_eq!(
                    read_data_u16(&cpu, &mut bus, base + 2),
                    (product >> 16) as u16
                );
                assert!(cpu.cf && cpu.hc && cpu.dd);
                assert_eq!(cpu.zf, product == 0);
                step(&mut cpu, &mut bus).unwrap();
                assert_eq!(
                    read_data_u16(&cpu, &mut bus, base + 2),
                    (product >> 17) as u16
                );
                assert_eq!(cpu.cf, (product >> 16) & 1 != 0);
                assert_eq!(read_data_u16(&cpu, &mut bus, base + 4), 0xA5A5);
            }
        }
    }
}

#[test]
fn decoded_word_mov_is_dd_independent_and_preserves_flags_and_bank_canaries() {
    for dd in [false, true] {
        for bank in [0x20u16, 0x40, 0x41] {
            let mut cpu = Cpu::new();
            cpu.lrb = bank;
            cpu.dd = dd;
            cpu.cf = true;
            cpu.hc = true;
            cpu.zf = false;
            let mut bus = Bus::new(vec![0xB4, 0x5A, 0x48], 0xA5);
            let address = cpu.off_page(0x5A);
            let base = cpu.bank_base();
            write_data_u16(&mut cpu, &mut bus, address, 0xBEEF);
            let flags = cpu.psw_u16();
            step(&mut cpu, &mut bus).unwrap();
            assert_eq!(read_data_u16(&cpu, &mut bus, base), 0xBEEF);
            assert_eq!(read_data_u16(&cpu, &mut bus, base + 2), 0xA5A5);
            assert_eq!(cpu.psw_u16(), flags);
            assert_eq!(cpu.pc, 3);
        }
    }
}
#[test]
fn real_subprocess_native_source_store_read_multiply_and_new_result() {
    // Independent little program: two immediate native stores, direct word
    // reloads, MUL and two destination stores; deliberately unlike the OEM tail.
    let rom = vec![
        0x67, 0x34, 0x12, 0xD5, 0xD0, 0x67, 0x78, 0x56, 0xD5, 0xD2, 0xE5, 0xD0, 0xB5, 0xD2, 0x48,
        0x90, 0x35, 0xD5, 0xD4, 0x35, 0xD5, 0xD6,
    ];
    let r = json!({"protocolVersion":1,"operation":"synthetic","images":[{"id":"synthetic","rom":rom}],"scratchPatterns":[170],"allowAssumptions":[],
        "synthetic":{"entryPc":0,"exitPcs":[22],"allowedCodeRanges":[[0,22]],"psw":0x0101,"lrb":0x40,"usp":0x180,
            "instructionBudget":16,"dataSeeds":[],"outputAddresses":[0xD0,0xD1,0xD4,0xD5,0xD6,0xD7]}});
    let mut child = Command::new(env!("CARGO_BIN_EXE_p28-slice-runner"))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(r.to_string().as_bytes())
        .unwrap();
    let out = child.wait_with_output().unwrap();
    assert!(out.status.success());
    let response: Value = serde_json::from_slice(&out.stdout).unwrap();
    let result = &response["syntheticResult"];
    assert_eq!(result["status"], 0);
    assert_eq!(result["outputs"], json!([0x34, 0x12, 0x60, 0, 0x26, 6]));
    assert_eq!(response["runnerVersion"], env!("CARGO_PKG_VERSION"));
}
