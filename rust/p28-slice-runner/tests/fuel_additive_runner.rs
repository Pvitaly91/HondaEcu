//! Invented programs/data only. These are not OEM production-chain coverage.
use p28_slice_runner::{
    bus::Bus,
    cpu::Cpu,
    decoder::decode,
    exec::{read_data_u16, step, write_data_u16, write_data_u8},
    fuel_additive::admission,
    instruction_forms::FormAdmission,
    runner::run_request,
};
use serde_json::{json, Value};
fn request() -> Value {
    let sources = json!({"factor0158":513,"source0142":0,"source0144":0,"source0146":65436,"source0148":1,"source0149":255,"source014a":0,"source014c":0,"counter00f2":4});
    json!({"protocolVersion":1,"operation":"fuelAdditiveCorrectionChain","images":[{"id":"baseline","rom":vec![0u8;32768]}],"scratchPatterns":[0,85,170],"allowAssumptions":[],
      "fuelAdditiveCorrectionChain":{"formatVersion":1,"initialState":{"loadIndex":0,"map0RpmIndex":0,"map1RpmIndex":0,"loadFraction":0,"map0RpmFraction":0,"map1RpmFraction":0,"selector0127":165,"consumerFactor013f":0,"consumerOutput0140":0},
      "callerGate0124":0,"mode012b":8,"traceCallIndexes":[0],"calls":[{"index":0,"rawLoad":1,"rawMap0Rpm":2,"rawMap1Rpm":3,"sources":sources},{"index":1,"rawLoad":255,"rawMap0Rpm":255,"rawMap1Rpm":255,"sources":sources}]}})
}
#[test]
fn closed_operation_rejects_ready_correction_and_unverified_permissions() {
    for case in 0..11 {
        let mut r = request();
        match case {
            0 => r["fuelAdditiveCorrectionChain"]["calls"][0]["sources"]["er3"] = json!(3),
            1 => r["fuelAdditiveCorrectionChain"]["calls"][0]["sources"]["source0144"] = json!(256),
            2 => r["fuelAdditiveCorrectionChain"]["calls"][0]["sources"]["data0140"] = json!(3),
            3 => r["fuelAdditiveCorrectionChain"]["callerGate0124"] = json!(16),
            4 => r["fuelAdditiveCorrectionChain"]["calls"][0]["selector0127"] = json!(2),
            5 => r["fuelAdditiveCorrectionChain"]["calls"][0]["psw"] = json!(0),
            6 => r["fuelAdditiveCorrectionChain"]["formatVersion"] = json!(2),
            7 => r["allowAssumptions"] = json!(["oki.add-er3-a"]),
            8 => r["operation"] = json!("fuelCalculationChain"),
            9 => r["fuelAdditiveCorrectionChain"]["traceCallIndexes"] = json!([0, 0]),
            _ => r["fuelAdditiveCorrectionChain"]["calls"][1]["index"] = json!(0),
        }
        if let Ok(r) = serde_json::from_value(r) {
            assert!(run_request(r).is_err());
        }
    }
}
#[test]
fn partial_prefix_does_not_inject_or_run_correction_suffix() {
    let r = serde_json::to_value(run_request(serde_json::from_value(request()).unwrap()).unwrap())
        .unwrap();
    for s in r["fuelAdditiveSequences"].as_array().unwrap() {
        let rows = &s["checkpoints"];
        assert_eq!(rows[0]["status"], 1);
        assert_eq!(rows[0]["stages"], json!([]));
        assert!(rows[0]["correction"].is_null());
        assert_eq!(rows[1]["status"], 4);
        assert!(rows[1]["input"].is_null());
        assert!(rows[1]["corrected"].is_null());
        assert_eq!(rows[1]["sourcesAfter"], rows[0]["sourcesAfter"]);
        assert_eq!(rows[1]["modeAfter"], 8);
        assert_eq!(rows[1]["accesses"], json!([]));
    }
}
#[test]
fn exact_form_and_dd_policy_never_inherits_disputed_add_or_subb() {
    for (bytes, dd, allowed) in [
        (&[0x47, 0x10][..], true, true),
        (&[0x47, 0x10][..], false, false),
        (&[0x33][..], true, true),
        (&[0x33][..], false, false),
        (&[0x14][..], false, true),
        (&[0x32, 0x80, 0][..], false, true),
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
fn xchg_word_aliases_vcal_native_target_return_and_byte_overlap() {
    for bank in [0x20u16, 0x40, 0x41] {
        let mut rom = vec![0u8; 256];
        rom[0] = 0x47;
        rom[1] = 0x10;
        rom[2] = 0x14;
        rom[0x30] = 0x80;
        rom[0x80] = 1;
        let mut bus = Bus::new(rom, 0xA5);
        let mut cpu = Cpu::new();
        cpu.lrb = bank;
        cpu.a = 1234;
        cpu.set_psw_u16(0xB331);
        let base = cpu.bank_base();
        write_data_u16(&mut cpu, &mut bus, base + 6, 65436);
        write_data_u16(&mut cpu, &mut bus, base + 4, 1234);
        let flags = cpu.psw_u16();
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(cpu.a, 65436);
        assert_eq!(read_data_u16(&cpu, &mut bus, base + 6), 1234);
        assert_eq!(cpu.psw_u16(), flags);
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(cpu.pc, 0x80);
        assert_eq!(cpu.ssp, 0x7FC);
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x7FE), 3);
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(cpu.pc, 3);
        assert_eq!(cpu.ssp, 0x7FE);
        assert_eq!(cpu.a, 65436);
        assert_eq!(cpu.psw_u16(), flags);
        write_data_u8(&mut cpu, &mut bus, base + 7, 0x80);
        assert_eq!(read_data_u16(&cpu, &mut bus, base + 6), 0x80D2);
        assert_eq!(read_data_u16(&cpu, &mut bus, base + 4), 1234);
    }
}
