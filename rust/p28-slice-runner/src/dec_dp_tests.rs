//! Invented decoded DEC DP probes. No firmware bytes, reset state, or admission.
use crate::{
    bus::Bus,
    cpu::Cpu,
    decoder::decode,
    exec::{read_data_u16, read_data_u8, step, write_data_u16, write_data_u8},
    full_decoder::FULL_OPCODES,
    instruction_forms::{
        acquisition_form_admission, checksum_form_admission, producer_form_admission, FormAdmission,
    },
    operand::{table, Arg, Reg},
};

const START: u16 = 0x20;
// Independently supplied pointing/local-bank addresses; neither bank aliases PR.
const CONTEXTS: [(u16, u16, u16, u16); 2] =
    [(1, 0x008C, 0x0063, 0x0318), (5, 0x00AC, 0x0143, 0x0A18)];

fn independently_decrement(old: u16) -> (u16, bool, bool) {
    // Integer modulo arithmetic and nibble borrowing, not executor helpers.
    let result = ((u32::from(old) + 65535) % 65536) as u16;
    (result, result == 0, u32::from(old) % 16 < 1)
}

fn setup(context: (u16, u16, u16, u16)) -> (Cpu, Bus, Vec<(u16, u8)>) {
    let (scb, dp, lrb, bank) = context;
    let mut program = vec![0xFF; START as usize];
    program.push(0x82);
    let mut cpu = Cpu::new();
    cpu.set_psw_u16(0x0330 | scb);
    cpu.pc = START;
    cpu.a = 0xBE42;
    cpu.ssp = 0x07FC;
    cpu.lrb = lrb;
    cpu.sf = true;
    cpu.cycles = 41;
    cpu.instructions = 17;
    let mut bus = Bus::new(program, 0xA5);
    let mut canaries = vec![];
    // Every pointing-register set: X1/X2/USP and all nonselected DP slots.
    for address in 0x0080..0x00C0 {
        if address != dp && address != dp + 1 {
            canaries.push((address, ((address - 0x80) * 3 + 0x17) as u8));
        }
    }
    for offset in 0..8 {
        canaries.push((bank + offset, (offset * 17 + 0x19) as u8));
    }
    for offset in 0..6 {
        canaries.push((0x07FA + offset, (offset * 19 + 0xA1) as u8));
    }
    canaries.extend([(0x00C0, 0x6D), (0x05D3, 0xE9), (0x0FFE, 0x72)]);
    for &(address, value) in &canaries {
        assert_ne!(address, dp);
        assert_ne!(address, dp + 1);
        write_data_u8(&mut cpu, &mut bus, address, value);
    }
    assert_eq!(cpu.scb(), scb);
    assert_eq!(cpu.bank_base(), bank);
    assert!(bus.take_fault().is_none());
    (cpu, bus, canaries)
}

fn check_case(
    cpu: &mut Cpu,
    bus: &mut Bus,
    canaries: &[(u16, u8)],
    dp: u16,
    old: u16,
    flags: u8,
    print_witness: bool,
) {
    cpu.pc = START;
    cpu.cf = flags & 1 != 0;
    cpu.zf = flags & 2 != 0;
    cpu.hc = flags & 4 != 0;
    cpu.dd = flags & 8 != 0;
    write_data_u16(cpu, bus, dp, old);
    let before = cpu.clone();
    let psw_before = cpu.psw_u16();
    let (result, zero, half_borrow) = independently_decrement(old);
    let expected_psw = (psw_before & !0x6000)
        | if zero { 0x4000 } else { 0 }
        | if half_borrow { 0x2000 } else { 0 };
    bus.begin_write_journal();
    bus.begin_native_accesses();
    bus.set_native_pc(START);
    let decoded = step(cpu, bus).unwrap();
    let pattern = &FULL_OPCODES[decoded.index];
    let parsed = table()[decoded.index].as_ref().unwrap();
    assert_eq!((decoded.mnemonic, decoded.len), ("DEC DP", 1));
    assert_eq!(pattern.bytes_pat, ["82"]);
    assert_eq!(pattern.dd_mode, 'U');
    assert_eq!(decoded.dd_after, None);
    assert_eq!(parsed.op, "DEC");
    assert!(!parsed.byte_width);
    assert_eq!(parsed.args, [Arg::Reg(Reg::Dp)]);
    assert_eq!(
        bus.end_native_accesses(),
        [
            [u32::from(START), u32::from(dp), 16, 0, u32::from(old)],
            [u32::from(START), u32::from(dp), 16, 1, u32::from(result)],
        ]
    );
    assert_eq!(
        bus.end_write_journal(),
        [[u32::from(dp), 16, u32::from(result)]]
    );
    let observed = read_data_u16(cpu, bus, dp);
    if print_witness {
        println!(
            "DEC_DP_WITNESS oldDP={old:04X} oldPSW={psw_before:04X} incomingHC={} \
             resultDP={observed:04X} expectedHC={} actualHC={} expectedPSW={expected_psw:04X} actualPSW={:04X}",
            u8::from(before.hc), u8::from(half_borrow), u8::from(cpu.hc), cpu.psw_u16()
        );
    }
    assert_eq!(observed, result, "oldDP={old:04X}; flags={flags:X}");
    assert_eq!(cpu.zf, zero, "oldDP={old:04X}; flags={flags:X}");
    assert_eq!(
        cpu.hc, half_borrow,
        "primary3-55 DEC DP half-borrow oldDP={old:04X}; incomingHC={}; expectedHC={}; actualHC={}; oldPSW={psw_before:04X}; expectedPSW={expected_psw:04X}; actualPSW={:04X}",
        u8::from(before.hc), u8::from(half_borrow), u8::from(cpu.hc), cpu.psw_u16()
    );
    assert_eq!((cpu.cf, cpu.dd), (before.cf, before.dd));
    assert_eq!(cpu.psw_u16(), expected_psw);
    assert_eq!(cpu.psw_u16() & !0x6000, psw_before & !0x6000);
    assert_eq!(cpu.psw_other, before.psw_other);
    assert_eq!(
        (cpu.a, cpu.ssp, cpu.lrb),
        (before.a, before.ssp, before.lrb)
    );
    assert_eq!((cpu.sf, cpu.halted), (before.sf, before.halted));
    assert_eq!(cpu.pc, START + 1);
    assert_eq!(cpu.instructions, before.instructions + 1);
    // M2au exact INT accounting, primary3-55; not measured physical time.
    assert_eq!(decoded.cycles, 3);
    assert_eq!(cpu.cycles, before.cycles + 3);
    for &(address, expected) in canaries {
        assert_eq!(
            read_data_u8(cpu, bus, address),
            expected,
            "canary={address:04X}"
        );
    }
    assert!(bus.take_fault().is_none());
    assert!(bus.program_reads().is_empty());
    assert!(bus.peripheral_accesses().is_empty());
}

#[test]
fn m2at_dec_dp_counterexample_sets_half_borrow_from_incoming_zero() {
    let (mut cpu, mut bus, canaries) = setup(CONTEXTS[0]);
    check_case(&mut cpu, &mut bus, &canaries, 0x008C, 0x0010, 0, true);
}

#[test]
fn m2at_dec_dp_counterexample_clears_half_borrow_from_incoming_one() {
    let (mut cpu, mut bus, canaries) = setup(CONTEXTS[0]);
    check_case(&mut cpu, &mut bus, &canaries, 0x008C, 0x0011, 4, true);
}

#[test]
fn m2at_dec_dp_exhaustive_all_words_dd_hc_two_nonaliased_contexts() {
    let mut checked = 0u32;
    for context in CONTEXTS {
        let (mut cpu, mut bus, canaries) = setup(context);
        for old in 0..=u16::MAX {
            for dd in [0u8, 8] {
                for hc in [0u8, 4] {
                    // Both CF and incoming ZF vary across the exhaustive words.
                    let flags = dd | hc | (old as u8 & 1) | ((old as u8 & 2) ^ 2);
                    check_case(&mut cpu, &mut bus, &canaries, context.1, old, flags, false);
                    checked += 1;
                }
            }
        }
    }
    assert_eq!(checked, 524288);
    println!("DEC_DP_EXHAUSTIVE vectors={checked} per_context=262144 contexts=2");
}

#[test]
fn m2at_dec_dp_explicit_corners_all_cf_zf_hc_dd_values() {
    let corners = [
        (0x0000, 0xFFFF, true, false),
        (0x0001, 0x0000, false, true),
        (0x000F, 0x000E, false, false),
        (0x0010, 0x000F, true, false),
        (0x0011, 0x0010, false, false),
        (0x0100, 0x00FF, true, false),
        (0x1000, 0x0FFF, true, false),
        (0x8000, 0x7FFF, true, false),
        (0xFFFF, 0xFFFE, false, false),
    ];
    let mut checked = 0;
    for context in CONTEXTS {
        let (mut cpu, mut bus, canaries) = setup(context);
        for (old, expected, hc, zf) in corners {
            assert_eq!(independently_decrement(old), (expected, zf, hc));
            for flags in 0..16 {
                check_case(&mut cpu, &mut bus, &canaries, context.1, old, flags, false);
                checked += 1;
            }
        }
    }
    assert_eq!(checked, 288);
    println!("DEC_DP_CORNERS vectors={checked} includes_both_incoming_cf_zf_hc_dd=true");
}

#[test]
fn m2at_dec_dp_recognition_does_not_grant_historical_form_admission() {
    for dd in [false, true] {
        let decoded = decode(dd, |offset| if offset == 0 { 0x82 } else { 0 }).unwrap();
        assert_eq!(decoded.mnemonic, "DEC DP");
        assert_eq!(FULL_OPCODES[decoded.index].bytes_pat, ["82"]);
        assert_eq!(
            acquisition_form_admission(&decoded),
            FormAdmission::Unsupported
        );
        assert_eq!(
            checksum_form_admission(&decoded),
            FormAdmission::Unsupported
        );
        assert_eq!(
            producer_form_admission(&decoded),
            FormAdmission::Unsupported
        );
        assert_eq!(
            crate::stateful_forms::admission(&decoded),
            FormAdmission::Unsupported
        );
    }
}

fn fingerprint_word(hash: &mut u64, word: u64) {
    // Stable explicit FNV-1a byte order, not DefaultHasher/platform output.
    for byte in word.to_le_bytes() {
        *hash = (*hash ^ u64::from(byte)).wrapping_mul(0x100000001B3);
    }
}

#[test]
fn m2at_non_target_pre_post_full_state_fingerprint() {
    // Baseline-comparison probes, not additional primary ISA confirmation.
    // Every word DEC form except the target, byte/direct/indexed controls,
    // ordinary CMP/SUB, and previous exact SLLB/rotate/shift behaviors.
    let controls: &[(&[u8], &str)] = &[
        (&[0x80], "DEC X1"),
        (&[0x81], "DEC X2"),
        (&[0xA1, 0x17], "DEC USP"),
        (&[0xA0, 0x17], "DEC SSP"),
        (&[0xFE], "DEC LRB"),
        (&[0x44, 0x17], "DEC er0"),
        (&[0x45, 0x17], "DEC er1"),
        (&[0x46, 0x17], "DEC er2"),
        (&[0x47, 0x17], "DEC er3"),
        (&[0xB4, 0xD3, 0x17], "DEC off N8"),
        (&[0xB5, 0xD3, 0x17], "DEC N8"),
        (&[0xB2, 0x17], "DEC [DP]"),
        (&[0xB3, 0x01, 0x17], "DEC S8[USP]"),
        (&[0xB0, 0x00, 0x01, 0x17], "DEC N16[X1]"),
        (&[0xB1, 0x00, 0x01, 0x17], "DEC N16[X2]"),
        (&[0xC0, 0x00, 0x01, 0x17], "DECB N16[X1]"),
        (&[0xC5, 0xD3, 0x17], "DECB N8"),
        (&[0xC4, 0xD3, 0x17], "DECB off N8"),
        (&[0xB8], "DECB r0"),
        (&[0x72], "INC DP"),
        (&[0x70], "INC X1"),
        (&[0xB1, 0x00, 0x01, 0x16], "INC N16[X2]"),
        (&[0xC5, 0xD3, 0x16], "INCB N8"),
        (&[0xA8], "INCB r0"),
        (&[0xB5, 0xD2, 0xC2], "CMP A, N8"),
        (&[0xB5, 0xD2, 0xA2], "SUB A, N8"),
        (&[0xC5, 0xD3, 0xC2], "CMPB A, N8"),
        (&[0xC5, 0xD3, 0xA2], "SUBB A, N8"),
        (&[0xC4, 0xB6, 0xD7], "SLLB off N8"),
        (&[0x33], "ROL"),
        (&[0x43], "ROR"),
        (&[0x63], "SRL"),
        (&[0x73], "SRA"),
    ];
    let mut hash = 0xCBF29CE484222325u64;
    let mut checked = 0;
    for (context_number, context) in CONTEXTS.into_iter().enumerate() {
        for (form_number, &(bytes, mnemonic)) in controls.iter().enumerate() {
            for value in [0x0000u16, 0x0001, 0x0010, 0x8000, 0xFFFF] {
                for flags in 0u8..16 {
                    // The CMP/SUB accumulator encodings are genuinely DD-gated;
                    // never ask their word/byte forms to decode in the other DD.
                    if (matches!(mnemonic, "CMP A, N8" | "SUB A, N8") && flags & 8 == 0)
                        || (matches!(mnemonic, "CMPB A, N8" | "SUBB A, N8") && flags & 8 != 0)
                    {
                        continue;
                    }
                    let (mut cpu, _, _) = setup(context);
                    cpu.pc = 0;
                    cpu.cf = flags & 1 != 0;
                    cpu.zf = flags & 2 != 0;
                    cpu.hc = flags & 4 != 0;
                    cpu.dd = flags & 8 != 0;
                    cpu.a = value;
                    let mut bus = Bus::new(bytes.to_vec(), 0xA5);
                    // Seed all modeled RAM first, then nonoverlapping pointers,
                    // then named destinations. Snapshot is after all seeds.
                    for address in 0x80u16..0x1000 {
                        write_data_u8(&mut cpu, &mut bus, address, address as u8 ^ 0x5A);
                    }
                    let pr = context.1 - 4;
                    for (address, pointer) in [
                        (pr, 0x0400),
                        (pr + 2, 0x0500),
                        (pr + 4, 0x0600),
                        (pr + 6, 0x0700),
                    ] {
                        write_data_u16(&mut cpu, &mut bus, address, pointer);
                    }
                    for address in [context.3, 0x00D2, 0x0500, 0x0600, 0x0700] {
                        write_data_u16(&mut cpu, &mut bus, address, value);
                    }
                    let off_word = cpu.off_page(0xD2);
                    let off_byte = cpu.off_page(0xB6);
                    write_data_u16(&mut cpu, &mut bus, off_word, value);
                    write_data_u8(&mut cpu, &mut bus, off_byte, value as u8);
                    if mnemonic == "DEC S8[USP]" {
                        write_data_u16(&mut cpu, &mut bus, 0x0700, value);
                    }
                    let incoming_psw = cpu.psw_u16();
                    bus.begin_write_journal();
                    bus.begin_native_accesses();
                    bus.set_native_pc(0);
                    let decoded = step(&mut cpu, &mut bus).unwrap();
                    if matches!(mnemonic, "ROL" | "ROR" | "SRL" | "SRA") {
                        assert!(decoded.mnemonic.starts_with(mnemonic));
                    } else {
                        assert_eq!(decoded.mnemonic, mnemonic);
                    }
                    assert_ne!(decoded.mnemonic, "DEC DP");
                    assert_eq!(cpu.pc, bytes.len() as u16);
                    fingerprint_word(&mut hash, context_number as u64);
                    fingerprint_word(&mut hash, form_number as u64);
                    fingerprint_word(&mut hash, u64::from(value));
                    fingerprint_word(&mut hash, u64::from(flags));
                    fingerprint_word(&mut hash, u64::from(incoming_psw));
                    fingerprint_word(&mut hash, decoded.index as u64);
                    fingerprint_word(&mut hash, decoded.len as u64);
                    fingerprint_word(&mut hash, u64::from(decoded.cycles));
                    for word in [
                        cpu.pc,
                        cpu.a,
                        cpu.ssp,
                        cpu.lrb,
                        cpu.psw_u16(),
                        cpu.psw_other,
                    ] {
                        fingerprint_word(&mut hash, u64::from(word));
                    }
                    for bit in [cpu.zf, cpu.cf, cpu.hc, cpu.dd, cpu.sf, cpu.halted] {
                        fingerprint_word(&mut hash, u64::from(bit));
                    }
                    fingerprint_word(&mut hash, cpu.cycles);
                    fingerprint_word(&mut hash, cpu.instructions);
                    for row in bus.end_native_accesses() {
                        for column in row {
                            fingerprint_word(&mut hash, u64::from(column));
                        }
                    }
                    fingerprint_word(&mut hash, u64::MAX);
                    for row in bus.end_write_journal() {
                        for column in row {
                            fingerprint_word(&mut hash, u64::from(column));
                        }
                    }
                    fingerprint_word(&mut hash, u64::MAX - 1);
                    // Includes every modeled ordinary-RAM byte, not just target.
                    for address in 0x80u16..0x1000 {
                        fingerprint_word(
                            &mut hash,
                            u64::from(read_data_u8(&cpu, &mut bus, address)),
                        );
                    }
                    assert!(bus.take_fault().is_none());
                    assert!(bus.program_reads().is_empty());
                    assert!(bus.peripheral_accesses().is_empty());
                    checked += 1;
                }
            }
        }
    }
    assert_eq!(checked, 4960);
    println!(
        "DEC_DP_NON_TARGET_FINGERPRINT vectors={checked} forms=33 contexts=2 fnv1a64={hash:016X}"
    );
}
