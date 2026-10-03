//! Invented ISA/process probes only. No OEM sequence or copied firmware fixture.
use crate::{
    bus::{Bus, CaptureObservation},
    cpu::Cpu,
    data0136_technical::form_admission,
    decoder::decode,
    exec::{step, write_data_u16},
    instruction_forms::{acquisition_form_admission, FormAdmission},
    protocol::Request,
    runner::run_request,
};
use serde_json::json;

#[test]
fn exact_new_registry_keeps_historical_and_disputed_forms_closed() {
    for (bytes, expected) in [
        (vec![0x21, 0x15], true),
        (vec![0x20, 0xB0, 7], true),
        (vec![0x80], true),
        (vec![0xC5, 0xD0, 0x48], true),
        (vec![0x46, 0x98, 11, 0], true),
        (vec![0x90, 0x37], true),
        (vec![0x20, 0xC0, 7], true),
        (vec![0x60, 0x42, 0], true),
        (vec![0xCB, 0], true),
        (vec![0xCE, 0], true),
        (vec![0x21, 0xB0, 7], false),
        (vec![0x81], false),
        (vec![0x47, 0x81], false),
        (vec![0x45, 0x81], false),
    ] {
        let d = decode(true, |i| bytes.get(i).copied().unwrap_or(0)).unwrap();
        assert_eq!(form_admission(&d) == FormAdmission::Allowed, expected);
        assert_ne!(acquisition_form_admission(&d), FormAdmission::Allowed);
    }
}

#[test]
fn invented_divide_has_alternative_writers_overflow_clear_and_same_generation_read() {
    // Tiny unrelated program: DIV; branch on high quotient; choose different
    // direct-[DP] store sites. Divisor11 and data0300 are invented, not OEM6/0136.
    let code = vec![
        0x90, 0x37, 0x20, 0xC0, 0, 0xC9, 4, 0xF9, 0xD2, 0xCB, 1, 0xD2, 0xE2,
    ];
    for (high, low, expected, writer) in [(0u16, 121u16, 11u16, 11u32), (12, 0, 0, 8)] {
        let mut cpu = Cpu::new();
        cpu.lrb = 0x30;
        cpu.set_psw_u16(0x1102);
        cpu.a = low;
        let mut bus = Bus::new(code.clone(), 0);
        write_data_u16(&mut cpu, &mut bus, 0x180, high);
        write_data_u16(&mut cpu, &mut bus, 0x184, 11);
        write_data_u16(&mut cpu, &mut bus, 0x94, 0x300);
        bus.begin_native_accesses();
        while cpu.pc < 13 {
            bus.set_native_pc(cpu.pc);
            step(&mut cpu, &mut bus).unwrap();
        }
        let accesses = bus.end_native_accesses();
        let writes: Vec<_> = accesses
            .iter()
            .filter(|a| a[1] == 0x300 && a[3] == 1)
            .collect();
        assert_eq!(writes, vec![&[writer, 0x300, 16, 1, u32::from(expected)]]);
        assert!(accesses.contains(&[12, 0x300, 16, 0, u32::from(expected)]));
        assert_eq!(cpu.a, expected);
    }
}

#[test]
fn invented_frozen_read_wrong_width_unknown_access_and_no_snapshot_evolution() {
    let mut cpu = Cpu::new();
    let mut bus = Bus::new(vec![0xE5, 0x3A, 0xE5, 0x3A], 0);
    bus.observe_capture(Some(CaptureObservation {
        tmr2: 123,
        irqh: 7,
        tcon2: 4,
    }));
    step(&mut cpu, &mut bus).unwrap();
    step(&mut cpu, &mut bus).unwrap();
    assert_eq!(cpu.a, 123);
    assert_eq!(
        bus.peripheral_accesses(),
        vec![[0x3A, 16, 0, 123], [0x3A, 16, 0, 123]]
    );
    bus.read_data_u8(0x3A);
    assert!(bus.take_fault().is_some());
    bus.read_data_u8(0x23);
    assert!(bus.take_fault().is_some());
}

fn request() -> serde_json::Value {
    json!({"protocolVersion":1,"operation":"data0136TechnicalProducer","images":[{"id":"baseline","rom":vec![0;32768]}],"scratchPatterns":[0,85,170],"allowAssumptions":[],
        "data0136TechnicalProducer":{"formatVersion":1,"initialState":{"previous00ee":7,"counter00ae":9,"data00b6":0,"data011f":0,"data0128":8,"history0136":321,"samples":[1,2,3,4,5,6]},
        "observations":[{"index":0,"tmr2":10,"irqh":0,"tcon2":0,"slot":0},{"index":1,"tmr2":20,"irqh":0,"tcon2":0,"slot":1}],"traceObservationIndexes":[0]}})
}

#[test]
fn invented_unadmitted_entry_aborts_and_never_applies_next_source() {
    let response =
        serde_json::to_value(run_request(serde_json::from_value(request()).unwrap()).unwrap())
            .unwrap();
    for s in response["data0136Sequences"].as_array().unwrap() {
        assert_eq!(s["completedObservations"], 0);
        let c = &s["checkpoints"];
        assert_eq!(c[0]["result"]["status"], 1);
        assert!(c[0]["writes"].as_array().unwrap().is_empty());
        assert!(c[1]["result"].is_null());
        assert!(c[1]["sourceApplications"].as_array().unwrap().is_empty());
        assert_eq!(c[1]["ramBefore"], c[1]["ramAfter"]);
    }
}

#[test]
fn closed_request_rejects_ready_output_mode_mismatch_and_foreign_operation() {
    let mut r = request();
    r["data0136TechnicalProducer"]["observations"][0]["quotient"] = 1.into();
    assert!(serde_json::from_value::<Request>(r).is_err());
    let mut r = request();
    r["data0136TechnicalProducer"]["initialState"]["data011f"] = 4.into();
    assert!(run_request(serde_json::from_value(r).unwrap()).is_err());
    let mut r = request();
    r["operation"] = "acquisitionSequence".into();
    assert!(run_request(serde_json::from_value(r).unwrap()).is_err());
}
