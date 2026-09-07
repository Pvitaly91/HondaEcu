//! Independent ISA probes and invented programs only, never OEM fixtures.
use p28_slice_runner::{
    adaptive::admission, decoder::decode, instruction_forms::FormAdmission, runner::run_request,
};
use p28_slice_runner::{
    bus::Bus,
    cpu::Cpu,
    exec::{step, write_data_u16},
};
use serde_json::{json, Value};

fn toy() -> Vec<u8> {
    let mut r = vec![0; 32768];
    // Invented accumulator update; not the native producer implementation.
    r[0x487B..0x4885].copy_from_slice(&[0xE3, 0x24, 0x86, 0x10, 0, 0xD3, 0x24, 0x03, 0xF5, 0x48]);
    r[0x1966..0x196D].copy_from_slice(&[0xF4, 0xA4, 0xD4, 0x24, 0x03, 0x38, 0x1A]);
    r[0x5585..0x558C].copy_from_slice(&[0xF4, 0x24, 0xD4, 0x8F, 0x03, 0x96, 0x55]);
    // Deliberately unconditional native decrement, not the ROM zero gate.
    r[0x5BD0..0x5BD7].copy_from_slice(&[0xC0, 0, 0, 0x17, 0x03, 0xD9, 0x5B]);
    r
}
fn request() -> Value {
    json!({"protocolVersion":1,"operation":"adaptiveLimiter","images":[{"id":"baseline","rom":toy()}],"allowAssumptions":[],"scratchPatterns":[0,85,170],"adaptiveLimiter":{"formatVersion":1,"initialState":{"limiter":{"data0124":0,"data012B":0,"data012A":0,"data018F":255,"data01D7":7,"ramCut":100,"ramResume":200},"timer":3,"counter":4,"ie":65535,"restoreIe":65535},"calls":(0..3).map(|i|json!({"limiter":{"index":i,"rawPeriod":90,"p4Bit0":false,"snapshot011bBit7":false,"channelMask":254},"raw00ce":900,"bank1":false,"reset217":false,"reset214":false,"mode212":false,"enable223":true,"rawD9":0,"timerTicks":1,"counterTicks":1})).collect::<Vec<_>>()}})
}
fn run(v: Value) -> Value {
    serde_json::to_value(run_request(serde_json::from_value(v).unwrap()).unwrap()).unwrap()
}
#[test]
fn direct_native_ram_handoff_and_persistent_ticks_without_reseeding() {
    let r = run(request());
    for s in r["adaptiveSequences"].as_array().unwrap() {
        for (i, c) in s["checkpoints"].as_array().unwrap().iter().enumerate() {
            assert_eq!(c["status"], 0);
            let cut = 116 + 16 * i;
            assert_eq!(c["stateAfterProducer"]["limiter"]["ramCut"], cut);
            assert_eq!(c["limiter"]["stateBefore"]["ramCut"], cut);
            assert_eq!(c["stateAfter"]["limiter"]["ramResume"], 200);
            assert_eq!(c["stateAfter"]["limiter"]["data018F"], cut);
            assert_eq!(c["stateAfter"]["limiter"]["data0124"], cut);
            assert_eq!(c["stateAfter"]["timer"], 2 - i);
            assert_eq!(c["stateAfter"]["counter"], 3 - i);
        }
    }
}
#[test]
fn strict_stop_does_not_execute_suffix_or_invent_outputs() {
    let mut v = request();
    v["images"][0]["rom"][0x487B] = json!(0x45);
    v["images"][0]["rom"][0x487C] = json!(0x81);
    let r = run(v);
    for s in r["adaptiveSequences"].as_array().unwrap() {
        let a = &s["checkpoints"][0];
        assert_eq!(a["status"], 1);
        assert!(a["limiter"].is_null());
        assert_eq!(s["checkpoints"][1]["status"], 4);
        assert!(s["checkpoints"][1]["producer"].is_null());
    }
}
#[test]
fn exact_forms_do_not_expand_prior_assumptions_or_dd() {
    for (bytes, dd, expected) in [
        (&[0x09][..], true, FormAdmission::Allowed),
        (&[0x09][..], false, FormAdmission::Unsupported),
        (&[0x45, 0x81][..], true, FormAdmission::Unsupported),
        (&[0x47, 0x81][..], true, FormAdmission::Unsupported),
        (&[0xA7, 1][..], false, FormAdmission::Unsupported),
        (&[0x0A][..], true, FormAdmission::Unsupported),
        (&[0xC3, 0x31, 0x98, 1][..], false, FormAdmission::Allowed),
    ] {
        assert_eq!(
            admission(&decode(dd, |i| bytes.get(i).copied().unwrap_or(0)).unwrap()),
            expected
        );
    }
}
#[test]
fn bounded_closed_requests_refuse_permissions_and_reseeds() {
    for k in 0..5 {
        let mut v = request();
        match k {
            0 => v["allowAssumptions"] = json!(["oki.add-er1-a"]),
            1 => v["adaptiveLimiter"]["calls"][0]["ramCut"] = json!(1),
            2 => v["adaptiveLimiter"]["calls"][0]["timerTicks"] = json!(33),
            3 => v["operation"] = json!("limiterSequence"),
            _ => v["adaptiveLimiter"]["calls"][0]["limiter"]["index"] = json!(4),
        }
        match serde_json::from_value(v) {
            Ok(r) => assert!(run_request(r).is_err()),
            Err(_) => {}
        }
    }
}
#[test]
fn unknown_sfr_is_not_opened_by_ie_storage() {
    let mut v = request();
    v["images"][0]["rom"][0x487B] = json!(0xE5);
    v["images"][0]["rom"][0x487C] = json!(0x24);
    assert_eq!(
        run(v)["adaptiveSequences"][0]["checkpoints"][0]["status"],
        2
    );
}
#[test]
fn multiplication_and_odd_program_table_word_preserve_width_and_order() {
    let mut rom = vec![0; 0x200];
    rom[0..4].copy_from_slice(&[0x91, 0xA9, 3, 0]);
    rom[0x103] = 0xCD;
    rom[0x104] = 0xAB;
    let mut cpu = Cpu::new();
    cpu.set_psw_u16(0xA001);
    let mut bus = Bus::new(rom, 0);
    write_data_u16(&mut cpu, &mut bus, 0x8A, 0x100);
    step(&mut cpu, &mut bus).unwrap();
    assert_eq!(cpu.a, 0xABCD);
    assert!(!cpu.dd);
    assert_eq!(bus.program_reads(), vec![0x103, 0x104]);
    for a in [0u16, 1, 255, 256, 65535] {
        for b in [0u16, 1, 257, 65535] {
            let mut cpu = Cpu::new();
            cpu.set_psw_u16(0xB101);
            cpu.a = a;
            cpu.lrb = 0x41;
            let mut bus = Bus::new(vec![0x90, 0x35], 0);
            write_data_u16(&mut cpu, &mut bus, 0x208, b);
            step(&mut cpu, &mut bus).unwrap();
            let product = a as u32 * b as u32;
            assert_eq!(cpu.a, product as u16);
            assert_eq!(
                p28_slice_runner::exec::read_data_u16(&cpu, &mut bus, 0x20A),
                (product >> 16) as u16
            );
            assert_eq!(cpu.zf, product == 0);
            assert!(cpu.cf && cpu.hc && cpu.dd);
        }
    }
}

#[test]
fn adaptive_exact_word_arithmetic_flags() {
    for (bytes, add, register) in [
        (vec![0x86, 1, 0], true, false),
        (vec![0x09], true, true),
        (vec![0xA6, 1, 0], false, false),
        (vec![0x28], false, true),
    ] {
        for lhs in [0u16, 15, 16, 255, 65535] {
            for prior in [false, true] {
                let mut cpu = Cpu::new();
                let mut bus = Bus::new(bytes.clone(), 0);
                cpu.set_psw_u16(0x1331);
                cpu.lrb = 0x41;
                cpu.a = lhs;
                cpu.hc = prior;
                if register {
                    write_data_u16(&mut cpu, &mut bus, if add { 0x20A } else { 0x208 }, 1);
                }
                let flags = cpu.psw_u16() & 0x1FFF;
                step(&mut cpu, &mut bus).unwrap();
                let result = if add {
                    lhs.wrapping_add(1)
                } else {
                    lhs.wrapping_sub(1)
                };
                assert_eq!(cpu.a, result);
                assert_eq!(cpu.zf, result == 0);
                assert_eq!(cpu.cf, if add { lhs == 65535 } else { lhs == 0 });
                assert_eq!(
                    cpu.hc,
                    if add { lhs & 15 == 15 } else { lhs & 15 == 0 },
                    "{bytes:X?} lhs={lhs} prior={prior}"
                );
                assert_eq!(cpu.psw_u16() & 0x1FFF, flags);
            }
        }
    }
}
