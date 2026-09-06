//! Invented probes only. These programs are deliberately NOT the OEM limiter.
use p28_slice_runner::{
    bus::Bus,
    cpu::Cpu,
    decoder::{decode as native_decode, Decoded},
    exec::{read_data_u16, read_data_u8, step, write_data_u16, write_data_u8},
    instruction_forms::FormAdmission,
    limiter::admission,
    protocol::Request,
    runner::run_request,
};
use serde_json::{json, Value};
fn decode(bytes: &[u8], _pc: usize, dd: bool) -> Option<Decoded> {
    native_decode(dd, |i| bytes.get(i).copied().unwrap_or(0))
}
fn toy() -> Vec<u8> {
    let mut r = vec![0; 32768];
    // Two invented constants; accumulate into an internal byte, then exit.
    let p = [
        0x62, 0x34, 0x12, 0x67, 0x56, 0x34, 0xF4, 0x24, 0x86, 1, 0xD4, 0x24, 0x03, 0x38, 0x1A,
    ];
    r[0x1966..0x1966 + p.len()].copy_from_slice(&p);
    let c = [0xF4, 0x8F, 0x86, 2, 0xD4, 0x8F, 0x03, 0x96, 0x55];
    r[0x5585..0x5585 + c.len()].copy_from_slice(&c);
    r
}
fn request() -> Value {
    json!({"protocolVersion":1,"operation":"limiterSequence","images":[{"id":"baseline","rom":toy()}],"scratchPatterns":[0,85,170],"allowAssumptions":[],"limiterSequence":{"formatVersion":1,"initialState":{"data0124":3,"data012B":7,"data012A":9,"data018F":10,"data01D7":11,"ramCut":1234,"ramResume":2345},"calls":(0..3).map(|i|json!({"index":i,"rawPeriod":100+i,"p4Bit0":false,"snapshot011bBit7":false,"channelMask":254})).collect::<Vec<_>>()}})
}
fn run(v: Value) -> Value {
    serde_json::to_value(run_request(serde_json::from_value(v).unwrap()).unwrap()).unwrap()
}
#[test]
fn persistent_ram_and_actual_consumer_no_reseed() {
    let r = run(request());
    for s in r["limiterSequences"].as_array().unwrap() {
        for (i, c) in s["checkpoints"].as_array().unwrap().iter().enumerate() {
            assert_eq!(c["status"], 0);
            assert_eq!(c["stateBefore"]["data0124"], 3 + i);
            assert_eq!(c["stateAfter"]["data0124"], 4 + i);
            assert_eq!(c["stateAfter"]["data018F"], 12 + 2 * i);
            assert_eq!(c["stateAfter"]["data01D7"], 11);
            assert_eq!(c["consumerWrites"], json!([[0x18F, 8, 12 + 2 * i]]));
        }
    }
}
#[test]
fn strict_unreviewed_form_stops_before_fetch_and_suffix_is_null() {
    let mut v = request();
    v["images"][0]["rom"][0x1966] = json!(0x09);
    let r = run(v);
    for s in r["limiterSequences"].as_array().unwrap() {
        let c = &s["checkpoints"][0];
        assert_eq!(c["status"], 1);
        assert_eq!(c["decision"]["steps"], 0);
        assert!(c["overspeedRequest"].is_null());
        assert!(c["consumer"].is_null());
        assert_eq!(s["checkpoints"][1]["status"], 4);
        assert_eq!(s["checkpoints"][2]["stateAfter"], c["stateBefore"]);
    }
}
#[test]
fn frozen_p4_access_does_not_open_other_sfrs() {
    let mut v = request();
    v["images"][0]["rom"][0x1966] = json!(0xF5);
    v["images"][0]["rom"][0x1967] = json!(0x24);
    let r = run(v);
    assert_eq!(r["limiterSequences"][0]["checkpoints"][0]["status"], 2);
}
#[test]
fn bounded_schema_and_one_field_diff_only() {
    for mode in 0..6 {
        let mut v = request();
        match mode {
            0 => v["limiterSequence"]["calls"][0]["data0124"] = json!(3),
            1 => v["limiterSequence"]["calls"][0]["channelMask"] = json!(1),
            2 => v["allowAssumptions"] = json!(["oki.add-er1-a"]),
            3 => v["limiterSequence"]["formatVersion"] = json!(2),
            _ => {
                let mut b = toy();
                b[0x1967] ^= 1;
                if mode == 4 {
                    b[0x196A] ^= 1;
                } else {
                    b[0x1966] ^= 1;
                }
                v["images"]
                    .as_array_mut()
                    .unwrap()
                    .push(json!({"id":"operandMutation","rom":b}));
            }
        }
        let parsed = serde_json::from_value::<Request>(v);
        assert!(parsed.is_err() || run_request(parsed.unwrap()).is_err());
    }
}
#[test]
fn complete_word_mutation_independent_machine() {
    let mut v = request();
    let mut b = toy();
    b[0x1967] = 0x78;
    b[0x1968] = 0x56;
    v["images"]
        .as_array_mut()
        .unwrap()
        .push(json!({"id":"operandMutation","rom":b}));
    let r = run(v);
    assert_eq!(
        r["limiterSequences"][0]["checkpoints"][0]["decisionWrites"][0],
        json!([0x8C, 16, 0x1234])
    );
    assert_eq!(
        r["limiterSequences"][3]["checkpoints"][0]["decisionWrites"][0],
        json!([0x8C, 16, 0x5678])
    );
}
#[test]
fn exact_new_forms_and_neighbor_rejection() {
    for bytes in [
        vec![0x67, 0x34, 0x12],
        vec![0x42],
        vec![0xB4, 0xB0, 0x7A],
        vec![0xB5, 0xC0, 0xC1],
        vec![0xC5, 0x2C, 0x28],
        vec![0xA3, 0x2C],
        vec![0xA3, 0x2D],
        vec![0xA3, 0x1D],
        vec![0xC4, 0xB0, 0x3B],
        vec![0xC4, 0xB0, 0x3C],
        vec![0xC4, 0xB0, 0x3D],
        vec![0xC4, 0xB0, 0x0F],
        vec![0xEF, 0xB0, 3],
        vec![0xDD, 0xB0, 3],
        vec![0xC4, 0xB0, 0xD1],
        vec![0xC4, 0xB0, 0xE0, 4],
        vec![0xE6, 4],
        vec![0x85],
        vec![0x95],
    ] {
        for dd in [false, true] {
            let d = decode(&bytes, 0, dd).unwrap();
            if bytes[0] == 0xE6 && dd {
                continue;
            }
            assert_eq!(admission(&d), FormAdmission::Allowed, "{bytes:02X?} {dd}");
        }
    }
    assert_ne!(
        admission(&decode(&[0x09], 0, true).unwrap()),
        FormAdmission::Allowed
    );
    assert_ne!(
        admission(&decode(&[0xA7, 0xB0], 0, false).unwrap()),
        FormAdmission::Allowed
    );
}
#[test]
fn cmp_direct_word_unsigned_borrow_equality_preserves_operands() {
    for lhs in [0u16, 15, 16, 255, 256, 32767, 32768, 65535] {
        for rhs in [0u16, 15, 16, 255, 256, 32767, 32768, 65535] {
            let mut c = Cpu::new();
            c.a = rhs;
            c.dd = true;
            c.hc = lhs & 1 != 0;
            let mut b = Bus::new(vec![0xB5, 0xC0, 0xC1], 0xA5);
            write_data_u16(&mut c, &mut b, 0xC0, lhs);
            step(&mut c, &mut b).unwrap();
            assert_eq!(c.cf, lhs < rhs);
            assert_eq!(c.zf, lhs == rhs);
            // Manufacturer CMP obj,A (3-36) preserves HC; unlike SUB.
            assert_eq!(c.hc, lhs & 1 != 0);
            assert!(c.dd);
            assert_eq!(c.a, rhs);
            assert_eq!(read_data_u16(&c, &mut b, 0xC0), lhs);
        }
    }
}
#[test]
fn bit_moves_resets_and_set_flags_use_byte_width() {
    for old in [0u8, 128] {
        for flags in [false, true] {
            let mut c = Cpu::new();
            c.lrb = 0x20;
            c.dd = true;
            c.cf = flags;
            c.hc = flags;
            let mut b = Bus::new(vec![0xC4, 0xB0, 0x0F], 0xA5);
            write_data_u8(&mut c, &mut b, 0x1B0, old);
            step(&mut c, &mut b).unwrap();
            assert_eq!(c.zf, old == 0);
            assert_eq!((c.cf, c.hc, c.dd), (flags, flags, true));
            assert_eq!(read_data_u8(&c, &mut b, 0x1B0), 0);
            assert_eq!(read_data_u8(&c, &mut b, 0x1B1), 0xA5);
        }
    }
}

#[test]
fn word_load_and_banked_dp_move_have_distinct_flag_contracts() {
    for value in [0u16, 0xA17E] {
        for flags in [false, true] {
            let mut c = Cpu::new();
            c.set_psw_u16(0x0101);
            c.lrb = 0x20;
            c.cf = flags;
            c.hc = flags;
            c.zf = flags;
            let mut b = Bus::new(vec![0xB4, 0xB0, 0x7A, 0x42], 0xA5);
            write_data_u16(&mut c, &mut b, 0x1B0, value);
            step(&mut c, &mut b).unwrap();
            assert_eq!(read_data_u16(&c, &mut b, 0x8C), value);
            assert_eq!((c.cf, c.hc, c.zf, c.dd), (flags, flags, flags, false));
            step(&mut c, &mut b).unwrap();
            assert_eq!(c.a, value);
            assert_eq!(c.zf, value == 0);
            assert!(c.dd);
            assert_eq!((c.cf, c.hc), (flags, flags));
            let mut b = Bus::new(vec![0x67, value as u8, (value >> 8) as u8], 0);
            c.pc = 0;
            c.a = 0xFFFF;
            c.dd = false;
            step(&mut c, &mut b).unwrap();
            assert_eq!(c.a, value);
            assert_eq!(c.zf, value == 0);
            assert!(c.dd);
            assert_eq!((c.cf, c.hc), (flags, flags));
        }
    }
}

#[test]
fn carry_bit_moves_and_pswl_set_preserve_the_relevant_flags() {
    for flag in [false, true] {
        for bit in [3u8, 4, 5] {
            let mut c = Cpu::new();
            c.lrb = 0x20;
            c.cf = flag;
            c.hc = true;
            c.zf = true;
            c.dd = true;
            let mut b = Bus::new(vec![0xC4, 0xB0, 0x38 + bit], 0xA5);
            step(&mut c, &mut b).unwrap();
            let expected = if flag {
                0xA5 | (1 << bit)
            } else {
                0xA5 & !(1 << bit)
            };
            assert_eq!(read_data_u8(&c, &mut b, 0x1B0), expected);
            assert_eq!(read_data_u8(&c, &mut b, 0x1B1), 0xA5);
            assert_eq!((c.cf, c.hc, c.zf, c.dd), (flag, true, true, true));
        }
    }
    for old in [false, true] {
        for bit in [4u8, 5] {
            let mut c = Cpu::new();
            c.set_psw_u16(0x0101 | if old { 1 << bit } else { 0 });
            c.cf = !old;
            c.hc = true;
            c.zf = true;
            c.dd = true;
            let mut b = Bus::new(vec![0xA3, 0x28 + bit], 0);
            step(&mut c, &mut b).unwrap();
            assert_eq!(c.cf, old);
            assert_eq!((c.hc, c.zf, c.dd), (true, true, true));
        }
        let mut c = Cpu::new();
        c.set_psw_u16(0x0101 | if old { 32 } else { 0 });
        c.cf = true;
        c.hc = true;
        c.dd = true;
        let mut b = Bus::new(vec![0xA3, 0x1D], 0);
        step(&mut c, &mut b).unwrap();
        assert_ne!(c.psw_u16() & 32, 0);
        assert_eq!(c.zf, !old);
        assert_eq!((c.cf, c.hc, c.dd), (true, true, true));
    }
}

#[test]
fn native_byte_masks_and_carry_controls_do_not_touch_adjacent_state() {
    for flags in [false, true] {
        let mut c = Cpu::new();
        c.lrb = 0x20;
        c.a = 0xAB05;
        c.cf = flags;
        c.hc = flags;
        c.dd = true;
        let mut b = Bus::new(
            vec![0xC4, 0xB0, 0xD1, 0xC4, 0xB0, 0xE0, 0x12, 0x85, 0x95],
            0xF0,
        );
        step(&mut c, &mut b).unwrap();
        assert_eq!(read_data_u8(&c, &mut b, 0x1B0), 0);
        assert!(c.zf);
        step(&mut c, &mut b).unwrap();
        assert_eq!(read_data_u8(&c, &mut b, 0x1B0), 0x12);
        assert!(!c.zf);
        assert_eq!(read_data_u8(&c, &mut b, 0x1B1), 0xF0);
        assert_eq!((c.cf, c.hc, c.dd), (flags, flags, true));
        step(&mut c, &mut b).unwrap();
        assert!(c.cf);
        assert_eq!((c.hc, c.zf, c.dd), (flags, false, true));
        step(&mut c, &mut b).unwrap();
        assert!(!c.cf);
        assert_eq!((c.hc, c.zf, c.dd), (flags, false, true));
        c.pc = 0;
        c.dd = false;
        let mut b = Bus::new(vec![0xE6, 0xA0], 0);
        step(&mut c, &mut b).unwrap();
        assert_eq!(c.a, 0xABA5);
        assert!(!c.zf);
        assert_eq!((c.cf, c.hc, c.dd), (false, flags, false));
    }
}
