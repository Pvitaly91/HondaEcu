//! Invented-only INT statistics probes, not physical timing or ROM admission.
use crate::{
    bus::Bus,
    cpu::Cpu,
    decoder::{decode, Decoded},
    exec::{read_data_u16, read_data_u8, step, write_data_u16, write_data_u8},
    full_decoder::FULL_OPCODES,
};

const START: u16 = 0x20;
const DEC: &[u8] = &[0x82];
const SLLB: &[u8] = &[0xC4, 0xB6, 0xD7];
// Primary3-55/3-145 literals, never derived from the decoder's helper.
const DEC_INT: u16 = 3;
const SLLB_INT: u16 = 7;
const CONTEXTS: [(u16, u16, u16); 2] = [(0x0063, 0x03B6, 0x0318), (0x0143, 0x0AB6, 0x0A18)];

fn machine(bytes: &[u8], flags: u8, context: usize, value: u16) -> (Cpu, Bus) {
    let (lrb, off, bank) = CONTEXTS[context];
    let mut cpu = Cpu::new();
    cpu.set_psw_u16(0x0331);
    cpu.cf = flags & 1 != 0;
    cpu.zf = flags & 2 != 0;
    cpu.hc = flags & 4 != 0;
    cpu.dd = flags & 8 != 0;
    cpu.pc = START;
    cpu.a = 0xBE42;
    cpu.ssp = 0x07FC;
    cpu.lrb = lrb;
    cpu.sf = true;
    cpu.cycles = 41;
    cpu.instructions = 17;
    let mut program = vec![0xFF; START as usize];
    program.extend_from_slice(bytes);
    program.resize(0x100, 0xFF);
    let mut bus = Bus::new(program, 0xA5);
    for address in 0x80u16..0x1000 {
        write_data_u8(&mut cpu, &mut bus, address, address as u8 ^ 0x5A);
    }
    for (address, pointer) in [
        (0x88, 0x0400),
        (0x8A, 0x0500),
        (0x8C, value),
        (0x8E, 0x0600),
    ] {
        write_data_u16(&mut cpu, &mut bus, address, pointer);
    }
    for address in [0x00D2, 0x0400, 0x0500, 0x0600, bank] {
        write_data_u16(&mut cpu, &mut bus, address, value);
    }
    write_data_u8(&mut cpu, &mut bus, off, value as u8);
    write_data_u8(&mut cpu, &mut bus, 0x00B6, value as u8 ^ 0x5A);
    // RT's explicit invented return address; no constructor/rooted history.
    write_data_u16(&mut cpu, &mut bus, 0x07FC, 0x0060);
    assert!(bus.take_fault().is_none());
    (cpu, bus)
}

fn identity(d: &Decoded, expected: &str, pattern: &[&str], len: usize) {
    let p = &FULL_OPCODES[d.index];
    assert_eq!((d.mnemonic, d.len), (expected, len));
    assert_eq!(p.bytes_pat, pattern);
    assert_eq!(p.dd_mode, 'U');
    assert_eq!(d.dd_after, None);
}

fn dec_state(cpu: &Cpu, bus: &mut Bus, before: &Cpu, old: u16) {
    let expected = ((u32::from(old) + 65535) % 65536) as u16;
    let expected_psw = (before.psw_u16() & !0x6000)
        | if expected == 0 { 0x4000 } else { 0 }
        | if old % 16 == 0 { 0x2000 } else { 0 };
    assert_eq!(read_data_u16(cpu, bus, 0x8C), expected);
    assert_eq!(cpu.psw_u16(), expected_psw);
    assert_eq!((cpu.cf, cpu.dd), (before.cf, before.dd));
    assert_eq!(
        (cpu.a, cpu.ssp, cpu.lrb, cpu.psw_other, cpu.sf, cpu.halted),
        (
            before.a,
            before.ssp,
            before.lrb,
            before.psw_other,
            before.sf,
            before.halted
        )
    );
    assert_eq!(cpu.pc, START + 1);
    assert_eq!(cpu.instructions, before.instructions + 1);
    assert_eq!(cpu.scb(), before.scb());
}

fn sllb_state(cpu: &Cpu, bus: &mut Bus, before: &Cpu, input: u8, context: usize) {
    let off = CONTEXTS[context].1;
    let result = (u16::from(input) * 2 % 256) as u8;
    let expected_psw =
        (before.psw_u16() & !Cpu::PSW_CF_BIT) | if input >= 128 { Cpu::PSW_CF_BIT } else { 0 };
    assert_eq!(read_data_u8(cpu, bus, off), result);
    assert_eq!(cpu.psw_u16(), expected_psw);
    assert_eq!((cpu.zf, cpu.hc, cpu.dd), (before.zf, before.hc, before.dd));
    assert_eq!(
        (cpu.a, cpu.ssp, cpu.lrb, cpu.psw_other, cpu.sf, cpu.halted),
        (
            before.a,
            before.ssp,
            before.lrb,
            before.psw_other,
            before.sf,
            before.halted
        )
    );
    assert_eq!(cpu.pc, START + 3);
    assert_eq!(cpu.instructions, before.instructions + 1);
    assert_eq!(cpu.scb(), before.scb());
}

#[test]
fn m2au_dec_dp_decoded_int_is_three_dd0_dd1() {
    let mut observations = vec![];
    for dd in [false, true] {
        let d = decode(dd, |i| DEC.get(i).copied().unwrap_or(0)).unwrap();
        identity(&d, "DEC DP", &["82"], 1);
        observations.push(d.cycles);
        println!(
            "DEC_DP_DECODE dd={dd} actual={} expected={DEC_INT}",
            d.cycles
        );
    }
    assert_eq!(
        observations,
        [DEC_INT, DEC_INT],
        "primary3-55 DEC DP INT cycles"
    );
}

#[test]
fn m2au_dec_dp_step_accumulates_three_dd0_dd1() {
    let mut observations = vec![];
    for dd in [0, 8] {
        let (mut cpu, mut bus) = machine(DEC, dd | 5, 0, 0x0010);
        let before = cpu.clone();
        let d = step(&mut cpu, &mut bus).unwrap();
        identity(&d, "DEC DP", &["82"], 1);
        dec_state(&cpu, &mut bus, &before, 0x0010);
        observations.push(cpu.cycles - before.cycles);
        println!(
            "DEC_DP_STEP dd={} actual_delta={} expected={DEC_INT}",
            cpu.dd,
            cpu.cycles - before.cycles
        );
    }
    assert_eq!(
        observations,
        [u64::from(DEC_INT); 2],
        "primary3-55 accumulated DEC DP INT cycles"
    );
}

#[test]
fn m2au_sllb_offpage_decoded_int_is_seven_dd0_dd1() {
    let mut observations = vec![];
    for dd in [false, true] {
        let d = decode(dd, |i| SLLB.get(i).copied().unwrap_or(0)).unwrap();
        identity(&d, "SLLB off N8", &["C4", "N8", "D7"], 3);
        assert_eq!(d.fields.n8, 0xB6);
        observations.push(d.cycles);
        println!(
            "SLLB_OFFPAGE_DECODE dd={dd} actual={} expected={SLLB_INT}",
            d.cycles
        );
    }
    assert_eq!(
        observations,
        [SLLB_INT, SLLB_INT],
        "primary3-145 SLLB off N8 INT cycles"
    );
}

#[test]
fn m2au_sllb_offpage_step_accumulates_seven_dd0_dd1() {
    let mut observations = vec![];
    for dd in [0, 8] {
        let (mut cpu, mut bus) = machine(SLLB, dd | 7, 1, 0x0081);
        let before = cpu.clone();
        let d = step(&mut cpu, &mut bus).unwrap();
        identity(&d, "SLLB off N8", &["C4", "N8", "D7"], 3);
        sllb_state(&cpu, &mut bus, &before, 0x81, 1);
        observations.push(cpu.cycles - before.cycles);
        println!(
            "SLLB_OFFPAGE_STEP dd={} actual_delta={} expected={SLLB_INT}",
            cpu.dd,
            cpu.cycles - before.cycles
        );
    }
    assert_eq!(
        observations,
        [u64::from(SLLB_INT); 2],
        "primary3-145 accumulated SLLB off N8 INT cycles"
    );
}

#[test]
fn m2au_dec_dp_all_words_dd_context_cycle_accounting() {
    let (mut cpu, mut bus) = machine(DEC, 0, 0, 0);
    let mut checked = 0;
    for old in 0..=u16::MAX {
        for dd in [0, 8] {
            cpu.pc = START;
            cpu.cf = old & 1 != 0;
            cpu.zf = old & 2 == 0;
            cpu.hc = old & 4 != 0;
            cpu.dd = dd != 0;
            write_data_u16(&mut cpu, &mut bus, 0x8C, old);
            let before = cpu.clone();
            let d = step(&mut cpu, &mut bus).unwrap();
            identity(&d, "DEC DP", &["82"], 1);
            assert_eq!(d.cycles, DEC_INT);
            assert_eq!(cpu.cycles, before.cycles + u64::from(DEC_INT));
            dec_state(&cpu, &mut bus, &before, old);
            assert!(bus.take_fault().is_none());
            checked += 1;
        }
    }
    assert_eq!(checked, 131072);
    println!("M2AU_DEC_CYCLE_EXHAUSTIVE vectors={checked} words=65536 dd_contexts=2");
}

#[test]
fn m2au_sllb_offpage_all_bytes_dd_two_pages_and_flag_controls() {
    let mut checked = 0;
    for context in 0..2 {
        let (mut cpu, mut bus) = machine(SLLB, 0, context, 0);
        for input in 0u16..=255 {
            for dd in [0, 8] {
                // Complete incoming flag coverage is additionally explicit below.
                let flags = (input as u8 & 7) | dd;
                cpu.pc = START;
                cpu.cf = flags & 1 != 0;
                cpu.zf = flags & 2 != 0;
                cpu.hc = flags & 4 != 0;
                cpu.dd = flags & 8 != 0;
                write_data_u8(&mut cpu, &mut bus, CONTEXTS[context].1, input as u8);
                let before = cpu.clone();
                let d = step(&mut cpu, &mut bus).unwrap();
                identity(&d, "SLLB off N8", &["C4", "N8", "D7"], 3);
                assert_eq!(d.cycles, SLLB_INT);
                assert_eq!(cpu.cycles, before.cycles + u64::from(SLLB_INT));
                sllb_state(&cpu, &mut bus, &before, input as u8, context);
                assert!(bus.take_fault().is_none());
                checked += 1;
            }
        }
    }
    assert_eq!(checked, 1024);
    let mut controls = 0;
    for context in 0..2 {
        for value in [0u16, 1, 0x7F, 0x80, 0xFF] {
            for flags in 0..16 {
                let (mut cpu, mut bus) = machine(SLLB, flags, context, value);
                let before = cpu.clone();
                let d = step(&mut cpu, &mut bus).unwrap();
                assert_eq!(d.cycles, SLLB_INT);
                assert_eq!(cpu.cycles, before.cycles + u64::from(SLLB_INT));
                sllb_state(&cpu, &mut bus, &before, value as u8, context);
                controls += 1;
            }
        }
    }
    assert_eq!(controls, 160);
    println!("M2AU_SLLB_CYCLE_EXHAUSTIVE vectors={checked} byte_values=256 dd_contexts=2 pages=2 flag_controls={controls}");
}

fn fingerprint(hash: &mut u64, bytes: &[u8]) {
    for byte in bytes {
        *hash = (*hash ^ u64::from(*byte)).wrapping_mul(0x100000001B3);
    }
}

fn snapshot(cpu: &mut Cpu, bus: &mut Bus, d: &Decoded, cycles_only: bool) -> String {
    use std::fmt::Write;
    let native = bus.end_native_accesses();
    let all_native = bus.end_all_native();
    let journal = bus.end_write_journal();
    let continuity = bus.end_continuity();
    let mut c = cpu.clone();
    let mut metadata = d.clone();
    if cycles_only {
        // The two allowed accounting fields, and ONLY those fields, normalized.
        c.cycles = 0;
        if matches!(d.mnemonic, "DEC DP" | "SLLB off N8") {
            metadata.cycles = 0;
        }
    }
    let mut s = format!("cpu={c:?};psw={:04X};scb={};decoded={metadata:?};pattern={:?};native={native:?};all_native={all_native:?};journal={journal:?};continuity={continuity:?};ram=", cpu.psw_u16(), cpu.scb(), FULL_OPCODES[d.index]);
    for address in 0x80u16..0x1000 {
        write!(&mut s, "{:02X}", read_data_u8(cpu, bus, address)).unwrap();
    }
    assert!(bus.take_fault().is_none());
    assert!(bus.program_reads().is_empty());
    assert!(bus.peripheral_accesses().is_empty());
    s.push_str(";fault=None;program_reads=[];peripheral_accesses=[];step=Ok\n");
    s
}

fn observed_step(cpu: &mut Cpu, bus: &mut Bus, cycles_only: bool) -> String {
    bus.begin_native_accesses();
    bus.begin_all_native();
    bus.begin_write_journal();
    bus.begin_continuity();
    bus.set_native_pc(cpu.pc);
    let d = step(cpu, bus).unwrap();
    snapshot(cpu, bus, &d, cycles_only)
}

#[test]
fn m2au_target_pre_post_cycles_only_full_snapshots() {
    let mut records = String::new();
    let mut checked = 0;
    for context in 0..2 {
        for (bytes, values) in [
            (
                DEC,
                &[0u16, 1, 0xF, 0x10, 0x11, 0x100, 0x1000, 0x8000, 0xFFFF][..],
            ),
            (SLLB, &[0u16, 1, 0x7F, 0x80, 0xFF][..]),
        ] {
            for &value in values {
                for flags in 0..16 {
                    let (mut cpu, mut bus) = machine(bytes, flags, context, value);
                    records.push_str(&format!(
                        "case={checked};context={context};input={value};flags={flags};"
                    ));
                    records.push_str(&observed_step(&mut cpu, &mut bus, true));
                    checked += 1;
                }
            }
        }
    }
    assert_eq!(checked, 448);
    let mut hash = 0xCBF29CE484222325;
    fingerprint(&mut hash, records.as_bytes());
    if let Ok(path) = std::env::var("HONDAECU_M2AU_TARGET_SNAPSHOT_PATH") {
        std::fs::write(path, &records).unwrap();
    }
    println!("M2AU_TARGET_FULL_SNAPSHOT vectors={checked} normalized_only=Decoded.cycles,Cpu.cycles fnv1a64={hash:016X}");
}

#[test]
fn m2au_non_target_pre_post_cycles_and_full_state_fingerprint() {
    // Baseline preservation, NOT primary proof for these uncorrected forms.
    let controls: &[(&[u8], &str, &[bool])] = &[
        (&[0x80], "DEC X1", &[false, true]),
        (&[0x81], "DEC X2", &[false, true]),
        (&[0xA1, 0x17], "DEC USP", &[false, true]),
        (&[0xA0, 0x17], "DEC SSP", &[false, true]),
        (&[0x72], "INC DP", &[false, true]),
        (&[0x70], "INC X1", &[false, true]),
        (&[0xC5, 0xD2, 0x17], "DECB N8", &[false, true]),
        (&[0xC0, 0, 1, 0x17], "DECB N16[X1]", &[false, true]),
        (&[0xC4, 0xB6, 0x17], "DECB off N8", &[false, true]),
        (&[0x53], "SLLB A", &[false]),
        (&[0xC5, 0xD2, 0xD7], "SLLB N8", &[false, true]),
        (&[0x20, 0xD7], "SLLB r0", &[false, true]),
        (&[0xC2, 0xD7], "SLLB [DP]", &[false, true]),
        (&[0xC4, 0xB6, 0xB7], "ROLB off N8", &[false, true]),
        (&[0x63], "SRLB A", &[false]),
        (&[0x63], "SRL A", &[true]),
        (&[0x43], "RORB A", &[false]),
        (&[0x43], "ROR A", &[true]),
        (&[0x73], "SRAB A", &[false]),
        (&[0x73], "SRA A", &[true]),
        (&[0xC6, 0x42, 0xBE], "CMP A, #N16", &[true]),
        (&[0xCE, 4], "JNE rel8", &[false, true]),
        (&[0xC8, 4], "JGT rel8", &[false, true]),
        (&[0xCF, 4], "JLE rel8", &[false, true]),
        (&[0x32, 0x60, 0], "CAL addr16", &[false, true]),
        (&[0x01], "RT", &[false, true]),
        (&[0xB5, 0xD2, 0x92], "ADC A, N8", &[true]),
        (&[0xB5, 0xD2, 0xB2], "SBC A, N8", &[true]),
        (&[0x00], "NOP", &[false, true]),
    ];
    let mut records = String::new();
    let mut checked = 0;
    for (form, &(bytes, expected, modes)) in controls.iter().enumerate() {
        for context in 0..2 {
            for value in [0u16, 1, 0x10, 0x80, 0xFFFF] {
                for flags in 0u8..8 {
                    for &dd in modes {
                        // [DP] requires a valid invented RAM pointer, independent
                        // of the data/carry/zero control being seeded.
                        let (mut cpu, mut bus) =
                            machine(bytes, flags | if dd { 8 } else { 0 }, context, value);
                        if expected == "SLLB [DP]" {
                            write_data_u16(&mut cpu, &mut bus, 0x8C, 0x0600);
                        }
                        let d = decode(dd, |i| bytes.get(i).copied().unwrap_or(0)).unwrap();
                        assert_eq!(d.mnemonic, expected);
                        assert!(!matches!(d.mnemonic, "DEC DP" | "SLLB off N8"));
                        records.push_str(&format!("case={checked};form={form};context={context};value={value};flags={flags};dd={dd};"));
                        records.push_str(&observed_step(&mut cpu, &mut bus, false));
                        checked += 1;
                    }
                }
            }
        }
    }
    let mut hash = 0xCBF29CE484222325;
    fingerprint(&mut hash, records.as_bytes());
    if let Ok(path) = std::env::var("HONDAECU_M2AU_CONTROL_SNAPSHOT_PATH") {
        std::fs::write(path, &records).unwrap();
    }
    println!("M2AU_NON_TARGET_FULL_SNAPSHOT forms={} vectors={checked} include_cycles=true fnv1a64={hash:016X}", controls.len());
}

#[test]
fn m2au_all_2623_pattern_decode_metadata_non_target_cycle_fingerprint() {
    let mut hash = 0xCBF29CE484222325;
    let mut selected_self = 0;
    let mut target_decodes = 0;
    let mut records = String::new();
    for (i, p) in FULL_OPCODES.iter().enumerate() {
        let bytes: Vec<u8> = p
            .bytes_pat
            .iter()
            .map(|token| {
                u8::from_str_radix(token, 16).unwrap_or(match *token {
                    "N8" | "N'8" => 0xB6,
                    "NH" | "N'H" => 1,
                    "addrh" => 0,
                    "addrl" => 0x60,
                    "rel8" => 4,
                    _ => 0,
                })
            })
            .collect();
        for dd in [false, true] {
            if (p.dd_mode == '1' && !dd) || (p.dd_mode == '0' && dd) {
                continue;
            }
            let mut d = decode(dd, |off| bytes.get(off).copied().unwrap_or(0)).unwrap();
            if d.index == i {
                selected_self += 1;
            }
            if matches!(d.mnemonic, "DEC DP" | "SLLB off N8") {
                target_decodes += 1;
                d.cycles = 0;
            }
            records.push_str(&format!(
                "candidate={i};dd={dd};decoded={d:?};pattern={:?}\n",
                FULL_OPCODES[d.index]
            ));
        }
    }
    assert_eq!(FULL_OPCODES.len(), 2623);
    assert_eq!(target_decodes, 4);
    fingerprint(&mut hash, records.as_bytes());
    if let Ok(path) = std::env::var("HONDAECU_M2AU_PATTERN_SNAPSHOT_PATH") {
        std::fs::write(path, &records).unwrap();
    }
    println!("M2AU_PINNED_PATTERN_SNAPSHOT visited=2623 selected_self={selected_self} target_decodes={target_decodes} normalized_target_cycles_only=true fnv1a64={hash:016X}");
}

#[test]
fn m2au_sequential_pre_post_cycles_only_full_snapshots() {
    let streams: &[(&[u8], usize, u16)] = &[
        (&[0x82, 0xC4, 0xB6, 0xD7], 2, 0x24),
        (&[0x82, 0x82, 0x82], 3, 0x23),
        (&[0xC4, 0xB6, 0xD7, 0xC4, 0xB6, 0xD7], 2, 0x26),
        (&[0x80, 0x82, 0x00, 0xC4, 0xB6, 0xD7], 4, 0x26),
        (&[0x82, 0xCE, 4], 2, 0x27),
    ];
    let mut records = String::new();
    let mut checked = 0;
    for dd in [0u8, 8] {
        for (id, &(bytes, count, end_pc)) in streams.iter().enumerate() {
            let (mut cpu, mut bus) = machine(bytes, dd | 2, 0, 0x10);
            let cycles_before = cpu.cycles;
            let mut targets = 0;
            for event in 0..count {
                let d = decode(cpu.dd, |i| {
                    bus.peek_code_u8(cpu.pc as usize + i).unwrap_or(0)
                })
                .unwrap();
                if matches!(d.mnemonic, "DEC DP" | "SLLB off N8") {
                    targets += 1;
                }
                records.push_str(&format!("stream={id};dd={dd};event={event};"));
                records.push_str(&observed_step(&mut cpu, &mut bus, true));
                assert_eq!(cpu.instructions, 17 + event as u64 + 1);
            }
            assert_eq!(cpu.pc, end_pc);
            println!("M2AU_SEQ_BASE_COMPARE id={id} dd={dd} delta={} targets={targets} steps={count} pc={end_pc}", cpu.cycles-cycles_before);
            checked += 1;
        }
    }
    assert_eq!(checked, 10);
    if let Ok(path) = std::env::var("HONDAECU_M2AU_SEQUENCE_SNAPSHOT_PATH") {
        std::fs::write(path, &records).unwrap();
    }
    let mut hash = 0xCBF29CE484222325;
    fingerprint(&mut hash, records.as_bytes());
    println!("M2AU_SEQUENCE_FULL_SNAPSHOT streams={checked} normalized_target_cycles_and_cumulative_only=true fnv1a64={hash:016X}");
}

#[test]
fn m2au_sequential_targets_repeat_mix_and_branch_penalty() {
    // Explicit expected costs, not a runtime sum from Decoded::cycles.
    let streams: &[(&[u8], &[u64], &[u16])] = &[
        (&[0x82, 0xC4, 0xB6, 0xD7], &[3, 7], &[0x21, 0x24]),
        (&[0x82, 0x82, 0x82], &[3, 3, 3], &[0x21, 0x22, 0x23]),
        (
            &[0xC4, 0xB6, 0xD7, 0xC4, 0xB6, 0xD7],
            &[7, 7],
            &[0x23, 0x26],
        ),
        (
            &[0x80, 0x82, 0x00, 0xC4, 0xB6, 0xD7],
            &[2, 3, 2, 7],
            &[0x21, 0x22, 0x23, 0x26],
        ),
    ];
    for dd in [0u8, 8] {
        for &(bytes, costs, pcs) in streams {
            let (mut cpu, mut bus) = machine(bytes, dd | 2, 0, 0x10);
            let mut expected = cpu.cycles;
            let instructions = cpu.instructions;
            for (i, (&cost, &pc)) in costs.iter().zip(pcs).enumerate() {
                let previous = cpu.cycles;
                step(&mut cpu, &mut bus).unwrap();
                expected += cost;
                assert_eq!(cpu.cycles, expected);
                assert!(cpu.cycles > previous);
                assert_eq!(cpu.instructions, instructions + i as u64 + 1);
                assert_eq!(cpu.pc, pc);
            }
        }
        // DEC10->0F sets ZF0: JNE taken+4 and lands at21+2+4=27.
        for (old, taken, expected_delta, end_pc) in [(0x10, true, 8, 0x27), (1, false, 4, 0x23)] {
            let (mut cpu, mut bus) = machine(&[0x82, 0xCE, 4], dd, 0, old);
            step(&mut cpu, &mut bus).unwrap();
            let before = cpu.cycles;
            let d = step(&mut cpu, &mut bus).unwrap();
            assert_eq!(d.mnemonic, "JNE rel8");
            assert_eq!(d.cycles, 4);
            assert_eq!(cpu.cycles - before, expected_delta);
            assert_eq!(cpu.pc, end_pc);
            assert_eq!(cpu.zf, !taken);
        }
    }
    println!("M2AU_SEQUENTIAL one_each_current=10 baseline=8 delta=2 repeats_and_mixed=true instruction_budget_unchanged=true branch_penalty=4");
}

#[test]
fn m2au_equal_value_writes_keep_separate_ordered_native_generations() {
    let bytes = [0xC4, 0xB6, 0xD7, 0xC4, 0xB6, 0xD7];
    let (mut cpu, mut bus) = machine(&bytes, 6, 0, 0);
    bus.begin_native_accesses();
    bus.begin_all_native();
    bus.begin_write_journal();
    bus.begin_continuity();
    for pc in [START, START + 3] {
        bus.set_native_pc(pc);
        let before = cpu.cycles;
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(cpu.cycles - before, u64::from(SLLB_INT));
    }
    let rows = bus.end_native_accesses();
    assert_eq!(
        rows,
        [
            [0x20, 0x3B6, 8, 0, 0],
            [0x20, 0x3B6, 8, 1, 0],
            [0x23, 0x3B6, 8, 0, 0],
            [0x23, 0x3B6, 8, 1, 0]
        ]
    );
    assert_eq!(bus.end_write_journal(), [[0x3B6, 8, 0], [0x3B6, 8, 0]]);
    let writes: Vec<_> = rows
        .iter()
        .enumerate()
        .filter(|(_, r)| r[3] == 1)
        .map(|(event, r)| (r[0], event, r[4]))
        .collect();
    assert_eq!(writes, [(0x20, 1, 0), (0x23, 3, 0)]);
    assert_ne!(writes[0], writes[1]);
    assert_eq!(bus.end_all_native().len(), 4);
    assert_eq!(bus.end_continuity().len(), 4);
}

#[test]
fn m2au_truncated_form_preserves_error_pc_and_zero_step_accounting() {
    for bytes in [&[0xC4][..], &[0xC4, 0xB6][..]] {
        let mut cpu = Cpu::new();
        cpu.cycles = 41;
        cpu.instructions = 17;
        let mut bus = Bus::new(bytes.to_vec(), 0xA5);
        let before = format!("{cpu:?}");
        let error = step(&mut cpu, &mut bus).unwrap_err().to_string();
        assert!(!error.is_empty());
        assert_eq!(format!("{cpu:?}"), before);
        assert!(bus.end_native_accesses().is_empty());
        assert!(bus.end_write_journal().is_empty());
        println!("M2AU_TRUNCATED_FORM bytes={bytes:?} error={error} state_unchanged=true");
    }
}
