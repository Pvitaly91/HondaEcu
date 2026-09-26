//! Invented programs/data only; this is never actual-ROM production coverage.
use p28_slice_runner::{
    decoder::decode, fuel_factor::admission, instruction_forms::FormAdmission, runner::run_request,
};
use serde_json::{json, Value};
fn request() -> Value {
    let sources = json!({"source015a":20,"source015c":65535,"source015e":255,"source0160":65535,"source0162":65535,
        "source0164":255,"source0165":200,"source0166":0,"source0167":0,"source0168":255,"source0133":107,
        "source0142":0,"source0144":0,"source0146":0,"source0148":0,"source0149":0,"source014a":0,"source014c":0,"counter00f2":0});
    json!({"protocolVersion":1,"operation":"fuelFactorProductionChain","images":[{"id":"baseline","rom":vec![0u8;32768]}],
        "scratchPatterns":[0,85,170],"allowAssumptions":[],"fuelFactorProductionChain":{
        "formatVersion":1,"initialState":{"loadIndex":0,"map0RpmIndex":0,"map1RpmIndex":0,"loadFraction":0,"map0RpmFraction":0,"map1RpmFraction":0,
        "selector0127":165,"consumerFactor013f":0,"consumerOutput0140":0},"callerGate0124":0,"mode012b":8,
        "producerMode012c":16,"producerSelector012f":128,"hysteresis0130":0,"traceCallIndexes":[0],
        "calls":[{"index":0,"rawLoad":1,"rawMap0Rpm":2,"rawMap1Rpm":3,"sources":sources},
        {"index":1,"rawLoad":255,"rawMap0Rpm":255,"rawMap1Rpm":255,"sources":sources}]}})
}
fn invoke(r: Value) -> Value {
    serde_json::to_value(run_request(serde_json::from_value(r).unwrap()).unwrap()).unwrap()
}
#[test]
fn closed_factor_contract_refuses_factor_ready_operands_permissions_and_old_task_payloads() {
    for i in 0..16 {
        let mut r = request();
        match i {
            0 => r["fuelFactorProductionChain"]["calls"][0]["sources"]["factor0158"] = json!(512),
            1 => r["fuelFactorProductionChain"]["calls"][0]["sources"]["source015e"] = json!(256),
            2 => r["fuelFactorProductionChain"]["calls"][0]["sources"]["source0144"] = json!(256),
            3 => r["fuelFactorProductionChain"]["calls"][0]["sources"]["source015f"] = json!(1),
            4 => r["fuelFactorProductionChain"]["calls"][0]["sources"]["er0"] = json!(1),
            5 => r["fuelFactorProductionChain"]["calls"][0]["sources"]["data0140"] = json!(1),
            6 => r["fuelFactorProductionChain"]["calls"][0]["selector0127"] = json!(2),
            7 => r["fuelFactorProductionChain"]["initialFactor0158"] = json!(1),
            8 => r["fuelFactorProductionChain"]["formatVersion"] = json!(2),
            9 => r["allowAssumptions"] = json!(["oki.add-er3-a"]),
            10 => r["operation"] = json!("fuelAdditiveCorrectionChain"),
            11 => r["fuelFactorProductionChain"]["traceCallIndexes"] = json!([0, 0]),
            12 => r["fuelFactorProductionChain"]["calls"][1]["index"] = json!(0),
            13 => r["fuelFactorProductionChain"]["callerGate0124"] = json!(16),
            14 => r["fuelFactorProductionChain"]["calls"][0]["producerMode012c"] = json!(0),
            _ => {
                r["fuelCalculationChain"] = json!({"formatVersion":1,"initialState":r["fuelFactorProductionChain"]["initialState"],"calls":[],"traceCallIndexes":[]})
            }
        }
        if let Ok(r) = serde_json::from_value(r) {
            assert!(run_request(r).is_err(), "case{i}");
        }
    }
}
#[test]
fn unresolved_prefix_preserves_diagnostic_factor_and_never_writes_it_as_input() {
    let r = invoke(request());
    for s in r["fuelFactorSequences"].as_array().unwrap() {
        let rows = &s["checkpoints"];
        let seed = s["scratchPattern"].as_u64().unwrap() * 257;
        assert_eq!(rows[0]["status"], 1);
        assert!(rows[0]["factorStage"].is_null());
        assert_eq!(rows[0]["factorProvenance"], "NotRun");
        assert_eq!(rows[0]["factor0158Before"], seed);
        assert_eq!(rows[0]["factor0158After"], seed);
        assert!(rows[0]["nativeFactor0158"].is_null());
        assert_eq!(rows[0]["stages"], json!([]));
        let writes = rows[0]["inputWrites"].as_array().unwrap();
        assert_eq!(writes.len(), 22);
        for w in writes {
            let a = w[0].as_u64().unwrap();
            let width = w[1].as_u64().unwrap();
            assert!(
                a >= 0x15A || a + width / 8 <= 0x158,
                "hidden oldfactor setter"
            );
            assert!(a != 0x15F, "upper015F is notper-eventinput");
        }
        assert_eq!(rows[1]["status"], 4);
        assert!(rows[1]["input"].is_null());
        assert_eq!(rows[1]["inputWrites"], json!([]));
        assert_eq!(rows[1]["sourcesAfter"], rows[0]["sourcesAfter"]);
        assert_eq!(rows[1]["hysteresisAfter"], rows[0]["hysteresisAfter"]);
        assert_eq!(rows[1]["factor0158After"], seed);
    }
}
#[test]
fn factor_exact_forms_close_dd_alias_and_forbidden_arithmetic_permissions() {
    for (bytes, dd, allowed) in [
        (&[0x44, 0xB7][..], false, true),
        (&[0x44, 0xB7][..], true, true),
        (&[0x45, 0xB7][..], true, false),
        (&[0x53][..], true, true),
        (&[0x53][..], false, false),
        (&[0xC5, 7, 0x98, 1][..], false, true),
        (&[0xC5, 8, 0x98, 1][..], false, false),
        (&[0xC5, 7, 0x48][..], false, true),
        (&[0xC5, 8, 0x48][..], true, false),
        (&[0xD5, 7][..], false, true),
        (&[0xD5, 7][..], true, false),
        (&[0xD5, 8][..], false, false),
        (&[0x47, 0x81][..], true, false),
        (&[0x45, 0x81][..], true, false),
        (&[0xA6, 1][..], false, false),
        (&[0x90, 0x35][..], false, true),
        (&[0x90, 0x35][..], true, true),
    ] {
        assert_eq!(
            decode(dd, |i| bytes.get(i).copied().unwrap_or(0))
                .as_ref()
                .is_some_and(|d| admission(d) == FormAdmission::Allowed),
            allowed,
            "{bytes:02x?} DD={dd}"
        );
    }
}
#[test]
fn invented_completed_prefix_and_partial_factor_store_never_runs_consumer_or_next_inputs() {
    let mut r = request();
    let mut rom = vec![0u8; 32768];
    // Independent tiny dummy bodies: locally makeZF and branch to each existingstageexit.
    // No OEM axis/interpolation or factorproducer routine is copied.
    for (entry, exit) in [
        (0x0A0C, 0x0A45),
        (0x0A62, 0x0A77),
        (0x12FC, 0x1340),
        (0x1340, 0x1347),
        (0x1347, 0x1350),
    ] {
        rom[entry] = 0xF9;
        rom[entry + 1] = 0xC9;
        rom[entry + 2] = (exit - entry - 3) as u8;
    }
    // Invented source→multiply→store, followedby a forbiddenform strictstop.
    // This intentionally cannot be certified as the recovered producerbyC# pathoracle.
    let program = [
        0xE4, 0x5A, 0x44, 0x98, 0, 0x80, 0x90, 0x35, 0x45, 0x7C, 0x58, 0x47, 0x81,
    ];
    rom[0x1F43..0x1F43 + program.len()].copy_from_slice(&program);
    r["images"][0]["rom"] = json!(rom);
    let r = invoke(r);
    for s in r["fuelFactorSequences"].as_array().unwrap() {
        let rows = &s["checkpoints"];
        assert_eq!(rows[0]["prefix"]["status"], 0);
        assert_eq!(rows[0]["status"], 1);
        assert_eq!(rows[0]["factor0158After"], 10);
        assert_eq!(rows[0]["factorProvenance"], "PartialWritten");
        assert!(rows[0]["nativeFactor0158"].is_null());
        assert_eq!(rows[0]["factorStage"]["result"]["stopPc"], 0x1F4E);
        assert_eq!(rows[0]["transitionToAdditiveWrites"], json!([]));
        assert_eq!(rows[0]["stages"], json!([]));
        assert!(rows[0]["component"].is_null());
        assert_eq!(rows[1]["status"], 4);
        assert!(rows[1]["input"].is_null());
        assert_eq!(rows[1]["inputWrites"], json!([]));
        assert_eq!(rows[1]["factor0158After"], 10);
    }
}
