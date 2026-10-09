//! Invented decoded ISA probes only; no firmware window or native ECU admission.
use crate::{
    bus::Bus,
    cpu::Cpu,
    decoder::decode,
    exec::{read_data_u8, step, write_data_u16, write_data_u8},
    full_decoder::FULL_OPCODES,
    instruction_forms::{acquisition_form_admission, FormAdmission},
    operand::{table, Arg, Mem},
};

const START: u16 = 0x20;
const OFFSET: u8 = 0xB6;
// Literal, independently supplied address expectations: two valid invented pages.
const CONTEXTS: [(u16, u16, u16); 2] = [(0x0063, 0x03B6, 0x0318), (0x0143, 0x0AB6, 0x0A18)];

fn flag_state(cpu: &mut Cpu, combination: u8) {
    cpu.set_psw_u16(0x0335);
    cpu.cf = combination & 1 != 0;
    cpu.zf = combination & 2 != 0;
    cpu.hc = combination & 4 != 0;
    cpu.dd = combination & 8 != 0;
}

fn off_machine(
    lrb: u16,
    address: u16,
    bank: u16,
    input: u8,
    flags: u8,
) -> (Cpu, Bus, Vec<(u16, u8)>) {
    let mut program = vec![0xFF; START as usize];
    program.extend_from_slice(&[0xC4, OFFSET, 0xD7]);
    let mut bus = Bus::new(program, 0xA5);
    let mut cpu = Cpu::new();
    flag_state(&mut cpu, flags);
    cpu.pc = START;
    cpu.lrb = lrb;
    cpu.a = 0xBE42;
    cpu.ssp = 0x07FC;
    cpu.sf = true;
    cpu.cycles = 41;
    cpu.instructions = 17;

    let mut canaries = vec![(address - 1, 0x72), (address + 1, 0xC9), (0x00B6, 0xE9)];
    // All pointing-register sets, not just the selected SCB5 set. Skip the
    // separately named same-offset/low-page canary to avoid duplicate seeds.
    for address in 0x0080u16..0x00C0 {
        if address != 0x00B6 {
            canaries.push((address, ((address - 0x80) * 3 + 0x17) as u8));
        }
    }
    for (offset, value) in [0x19, 0x2A, 0x3B, 0x4C, 0x5D, 0x6E, 0x7F, 0x90]
        .into_iter()
        .enumerate()
    {
        canaries.push((bank + offset as u16, value));
    }
    for (offset, value) in [0xD1, 0xE2, 0xF3, 0x14, 0x25, 0x36].into_iter().enumerate() {
        canaries.push((0x07FA + offset as u16, value));
    }
    let other_page = if address == 0x03B6 { 0x0AB6 } else { 0x03B6 };
    canaries.push((other_page, 0x6D));
    for &(canary_address, value) in &canaries {
        assert_ne!(canary_address, address);
        write_data_u8(&mut cpu, &mut bus, canary_address, value);
    }
    write_data_u8(&mut cpu, &mut bus, address, input);
    (cpu, bus, canaries)
}

fn assert_off_case(input: u8, flags: u8, lrb: u16, address: u16, bank: u16) {
    let (mut cpu, mut bus, canaries) = off_machine(lrb, address, bank, input, flags);
    let before = cpu.clone();
    let psw_before = cpu.psw_u16();
    // Independent arithmetic specification, not an executor helper or a second
    // executor invocation. The incoming CF is deliberately absent.
    let result = (u16::from(input) * 2 % 256) as u8;
    let carry = input >= 128;
    let expected_psw = (psw_before & !Cpu::PSW_CF_BIT) | if carry { Cpu::PSW_CF_BIT } else { 0 };
    bus.begin_native_accesses();
    bus.set_native_pc(START);
    let decoded = step(&mut cpu, &mut bus).unwrap();
    let pattern = &FULL_OPCODES[decoded.index];
    assert_eq!((decoded.mnemonic, decoded.len), ("SLLB off N8", 3));
    assert_eq!(pattern.bytes_pat, ["C4", "N8", "D7"]);
    assert_eq!(pattern.dd_mode, 'U');
    assert_eq!(decoded.dd_after, None);
    assert_eq!(decoded.fields.n8, OFFSET);
    let parsed = table()[decoded.index].as_ref().unwrap();
    assert!(parsed.byte_width);
    assert_eq!(parsed.args, [Arg::Mem(Mem::OffPage)]);
    assert_eq!(
        bus.end_native_accesses(),
        [
            [u32::from(START), u32::from(address), 8, 0, u32::from(input)],
            [
                u32::from(START),
                u32::from(address),
                8,
                1,
                u32::from(result)
            ],
        ],
        "LRB={lrb:04X}; byte={input:02X}; flags={flags:01X}"
    );
    assert_eq!(read_data_u8(&cpu, &mut bus, address), result);
    assert_eq!(cpu.cf, carry);
    assert_eq!(cpu.zf, before.zf, "old={input:02X}; flags={flags:01X}");
    assert_eq!((cpu.hc, cpu.dd), (before.hc, before.dd));
    assert_eq!(
        cpu.psw_u16(),
        expected_psw,
        "full PSW; old={input:02X}; flags={flags:01X}"
    );
    assert_eq!(
        cpu.psw_u16() & !Cpu::PSW_CF_BIT,
        psw_before & !Cpu::PSW_CF_BIT
    );
    assert_eq!(cpu.psw_other, before.psw_other);
    assert_eq!(
        (cpu.a, cpu.ssp, cpu.lrb),
        (before.a, before.ssp, before.lrb)
    );
    assert_eq!((cpu.sf, cpu.halted), (before.sf, before.halted));
    assert_eq!(cpu.pc, START + 3);
    assert_eq!(cpu.instructions, before.instructions + 1);
    // M2au exact INT accounting, primary3-145; not measured physical time.
    // This remains the unchanged M2an semantic regression; only cycle
    // expectations reflect the separately reviewed exact-form accounting fix.
    assert_eq!(decoded.cycles, 7);
    assert_eq!(cpu.cycles, before.cycles + 7);
    for (canary_address, expected) in canaries {
        assert_eq!(
            read_data_u8(&cpu, &mut bus, canary_address),
            expected,
            "canary={canary_address:04X}"
        );
    }
    assert!(bus.take_fault().is_none());
    assert!(bus.program_reads().is_empty());
}

#[test]
fn m2an_offpage_sllb_nonzero_result_keeps_incoming_zero_flag_counterexample() {
    // Red before the fix: old byte 01 / incoming ZF1 -> byte02 / old code ZF0.
    // This identical assertion remains the post-fix green regression.
    assert_off_case(0x01, 0b0010, 0x0063, 0x03B6, 0x0318);
}

#[test]
fn m2an_offpage_sllb_exhaustive_256_bytes_16_flags_two_pages() {
    let mut checked = 0;
    for (lrb, address, bank) in CONTEXTS {
        for input in 0u16..=255 {
            for flags in 0u8..16 {
                assert_off_case(input as u8, flags, lrb, address, bank);
                checked += 1;
            }
        }
    }
    assert_eq!(checked, 8192);
}

#[test]
fn m2an_offpage_sllb_explicit_corners_ignore_incoming_carry_and_keep_zero() {
    for (input, result, carry) in [
        (0, 0, false),
        (1, 2, false),
        (0x7F, 0xFE, false),
        (0x80, 0, true),
        (0xFF, 0xFE, true),
    ] {
        assert_eq!((u16::from(input) * 2 % 256) as u8, result);
        assert_eq!(input >= 128, carry);
        for (lrb, address, bank) in CONTEXTS {
            for flags in 0u8..16 {
                assert_off_case(input, flags, lrb, address, bank);
            }
        }
    }
}

#[derive(Clone, Copy)]
enum ControlDestination {
    Accumulator,
    OffPage,
    Direct,
    Dp,
    Usp,
    Register,
}

#[test]
fn m2an_non_target_shift_rotate_forms_keep_historical_result_and_flags() {
    // These are behavior-preservation controls. In particular, the unreviewed
    // SLLB direct/register/DP/USP and SRA forms gain no primary proof/admission.
    let controls: &[(&[u8], &str, bool, bool, ControlDestination, &str, bool)] = &[
        (
            &[0x53],
            "SLLB A",
            false,
            true,
            ControlDestination::Accumulator,
            "SLL",
            true,
        ),
        (
            &[0x53],
            "SLL A",
            true,
            false,
            ControlDestination::Accumulator,
            "SLL",
            true,
        ),
        (
            &[0x33],
            "ROLB A",
            false,
            true,
            ControlDestination::Accumulator,
            "ROL",
            true,
        ),
        (
            &[0x33],
            "ROL A",
            true,
            false,
            ControlDestination::Accumulator,
            "ROL",
            true,
        ),
        (
            &[0x43],
            "RORB A",
            false,
            true,
            ControlDestination::Accumulator,
            "ROR",
            true,
        ),
        (
            &[0x43],
            "ROR A",
            true,
            false,
            ControlDestination::Accumulator,
            "ROR",
            true,
        ),
        (
            &[0x63],
            "SRLB A",
            false,
            true,
            ControlDestination::Accumulator,
            "SRL",
            true,
        ),
        (
            &[0x63],
            "SRL A",
            true,
            false,
            ControlDestination::Accumulator,
            "SRL",
            true,
        ),
        (
            &[0x73],
            "SRAB A",
            false,
            true,
            ControlDestination::Accumulator,
            "SRA",
            false,
        ),
        (
            &[0x73],
            "SRA A",
            true,
            false,
            ControlDestination::Accumulator,
            "SRA",
            false,
        ),
        (
            &[0xC4, OFFSET, 0xB7],
            "ROLB off N8",
            false,
            true,
            ControlDestination::OffPage,
            "ROL",
            true,
        ),
        (
            &[0xC4, OFFSET, 0xB7],
            "ROLB off N8",
            true,
            true,
            ControlDestination::OffPage,
            "ROL",
            true,
        ),
        (
            &[0xC4, OFFSET, 0xC7],
            "RORB off N8",
            false,
            true,
            ControlDestination::OffPage,
            "ROR",
            true,
        ),
        (
            &[0xC4, OFFSET, 0xC7],
            "RORB off N8",
            true,
            true,
            ControlDestination::OffPage,
            "ROR",
            true,
        ),
        (
            &[0xC4, OFFSET, 0xE7],
            "SRLB off N8",
            false,
            true,
            ControlDestination::OffPage,
            "SRL",
            true,
        ),
        (
            &[0xC4, OFFSET, 0xE7],
            "SRLB off N8",
            true,
            true,
            ControlDestination::OffPage,
            "SRL",
            true,
        ),
        (
            &[0xC5, 0xD3, 0xD7],
            "SLLB N8",
            false,
            true,
            ControlDestination::Direct,
            "SLL",
            false,
        ),
        (
            &[0xC5, 0xD3, 0xD7],
            "SLLB N8",
            true,
            true,
            ControlDestination::Direct,
            "SLL",
            false,
        ),
        (
            &[0xC2, 0xD7],
            "SLLB [DP]",
            false,
            true,
            ControlDestination::Dp,
            "SLL",
            false,
        ),
        (
            &[0xC2, 0xD7],
            "SLLB [DP]",
            true,
            true,
            ControlDestination::Dp,
            "SLL",
            false,
        ),
        (
            &[0xC3, 0xFF, 0xD7],
            "SLLB S8[USP]",
            false,
            true,
            ControlDestination::Usp,
            "SLL",
            false,
        ),
        (
            &[0xC3, 0xFF, 0xD7],
            "SLLB S8[USP]",
            true,
            true,
            ControlDestination::Usp,
            "SLL",
            false,
        ),
        (
            &[0x20, 0xD7],
            "SLLB r0",
            false,
            true,
            ControlDestination::Register,
            "SLL",
            false,
        ),
        (
            &[0x20, 0xD7],
            "SLLB r0",
            true,
            true,
            ControlDestination::Register,
            "SLL",
            false,
        ),
    ];
    let mut checked = 0;
    for &(bytes, mnemonic, dd, byte, destination, operation, preserves_zf) in controls {
        let values: &[u16] = if byte {
            &[0, 1, 0x7F, 0x80, 0xFF]
        } else {
            &[0, 1, 0x7FFF, 0x8000, 0xFFFF]
        };
        for &input in values {
            for flags in 0u8..8 {
                let mut cpu = Cpu::new();
                flag_state(&mut cpu, flags);
                cpu.dd = dd;
                cpu.lrb = 0x0063;
                cpu.a = 0xBE42;
                let mut bus = Bus::new(bytes.to_vec(), 0xA5);
                let address = match destination {
                    ControlDestination::Accumulator => None,
                    ControlDestination::OffPage => Some(0x03B6),
                    ControlDestination::Direct => Some(0x00D3),
                    ControlDestination::Dp => {
                        write_data_u16(&mut cpu, &mut bus, 0x00AC, 0x05D3);
                        Some(0x05D3)
                    }
                    ControlDestination::Usp => {
                        write_data_u16(&mut cpu, &mut bus, 0x00AE, 0x05D4);
                        Some(0x05D3)
                    }
                    ControlDestination::Register => Some(0x0318),
                };
                if let Some(address) = address {
                    write_data_u8(&mut cpu, &mut bus, address, input as u8);
                    write_data_u8(&mut cpu, &mut bus, address - 1, 0x72);
                    write_data_u8(&mut cpu, &mut bus, address + 1, 0xC9);
                } else {
                    cpu.a = if byte { 0xBE00 | input } else { input };
                }
                let before = cpu.clone();
                let psw = cpu.psw_u16();
                let width = if byte { 8 } else { 16 };
                let half = 1u32 << (width - 1);
                let limit = half * 2;
                let operand = u32::from(input);
                let (expected, carry) = match operation {
                    "SLL" => (operand * 2 % limit, operand >= half),
                    "ROL" => (
                        (operand * 2 + u32::from(before.cf)) % limit,
                        operand >= half,
                    ),
                    "ROR" => (
                        operand / 2 + if before.cf { half } else { 0 },
                        operand % 2 == 1,
                    ),
                    "SRL" => (operand / 2, operand % 2 == 1),
                    "SRA" => (
                        operand / 2 + if operand >= half { half } else { 0 },
                        operand % 2 == 1,
                    ),
                    _ => unreachable!(),
                };
                let zf = if preserves_zf {
                    before.zf
                } else {
                    expected == 0
                };
                let expected_psw = (psw & !(Cpu::PSW_CF_BIT | Cpu::PSW_ZF_BIT))
                    | if carry { Cpu::PSW_CF_BIT } else { 0 }
                    | if zf { Cpu::PSW_ZF_BIT } else { 0 };
                let decoded = step(&mut cpu, &mut bus).unwrap();
                assert_eq!(decoded.mnemonic, mnemonic);
                assert_ne!(FULL_OPCODES[decoded.index].bytes_pat, ["C4", "N8", "D7"]);
                assert_eq!(
                    cpu.psw_u16(),
                    expected_psw,
                    "{mnemonic}; input={input:04X}; flags={flags}"
                );
                if let Some(address) = address {
                    assert_eq!(read_data_u8(&cpu, &mut bus, address), expected as u8);
                    assert_eq!(read_data_u8(&cpu, &mut bus, address - 1), 0x72);
                    assert_eq!(read_data_u8(&cpu, &mut bus, address + 1), 0xC9);
                    assert_eq!(cpu.a, before.a);
                } else {
                    let accumulator = if byte {
                        0xBE00 | expected as u16
                    } else {
                        expected as u16
                    };
                    assert_eq!(cpu.a, accumulator);
                }
                assert_eq!(
                    (cpu.lrb, cpu.ssp, cpu.sf),
                    (before.lrb, before.ssp, before.sf)
                );
                assert_eq!(cpu.pc, bytes.len() as u16);
                assert!(bus.take_fault().is_none());
                checked += 1;
            }
        }
    }
    assert_eq!(checked, 960);
}

#[test]
fn m2an_corrected_decoder_form_adds_no_acquisition_tail_or_alternate_admission() {
    for dd in [false, true] {
        let decoded = decode(dd, |i| [0xC4, OFFSET, 0xD7].get(i).copied().unwrap_or(0)).unwrap();
        assert_eq!(decoded.mnemonic, "SLLB off N8");
        assert_eq!(
            acquisition_form_admission(&decoded),
            FormAdmission::Unsupported
        );
        assert_eq!(
            crate::data0136_tail::admission(&decoded),
            FormAdmission::Unsupported
        );
        assert_eq!(
            crate::word0196_alternate::admission(&decoded),
            FormAdmission::Unsupported
        );
    }
}
