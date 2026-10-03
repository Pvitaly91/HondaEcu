//! M2s Part A: same-machine local continuation, not a recovered quartet consumer.
//! Part B consumers require an unestablished asynchronous caller and remain NotRun.
use crate::{
    adaptive::Stage,
    bus::Bus,
    cpu::Cpu,
    decoder::Decoded,
    exec::{read_data_u16, read_data_u8, write_data_u16, write_data_u8},
    full_decoder::FULL_OPCODES,
    instruction_forms::FormAdmission,
    post_selection_critical,
    post_store::{self, Suffix},
    protocol::{Request, Response},
    runner::{execute_in_state_observed, SliceContract},
    vtec_fuel::boundary,
};
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct SoftwareSources {
    pub word011a_mask1034: u16,
    pub bit011f5: bool,
    #[serde(rename = "bit0120_0")]
    pub bit0120_0: bool,
    pub byte00be: u8,
    #[serde(rename = "bit00b7_0")]
    pub bit00b7_0: bool,
    pub word0136: u16,
    pub history013b: u8,
    pub history013d: u8,
}
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Initial {
    pub prefix: post_store::Initial,
    pub software_sources: SoftwareSources,
}
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Stimulus {
    pub format_version: u32,
    pub initial_state: Initial,
    pub calls: Vec<post_store::Call>,
    pub trace_call_indexes: Vec<u32>,
}
#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct State {
    pub prefix: post_selection_critical::State,
    pub mode012b: u8,
    pub word011a: u16,
    pub byte011f: u8,
    pub byte0120: u8,
    pub byte00be: u8,
    pub byte00b7: u8,
    pub word0136: u16,
    pub byte013b: u8,
    pub byte013d: u8,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Checkpoint {
    pub index: u32,
    pub status: i32,
    pub prefix: post_selection_critical::Checkpoint,
    pub state_before: State,
    pub state_at_entry: Option<State>,
    pub state_after: State,
    pub common_consumer: Option<Suffix>,
    pub software_result13b: Option<u8>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Sequence {
    pub scratch_pattern: u8,
    pub checkpoints: Vec<Checkpoint>,
}
pub fn validate_request(r: &Request) -> Result<(), String> {
    if r.fuel_division_decision_chain.is_some() {
        return Err("M2t stimulus is unavailable to historical M2s".into());
    }
    validate_parts(
        r,
        r.fuel_common_result_consumer_chain
            .as_ref()
            .ok_or("M2s stimulus required")?,
    )
}
pub(crate) fn validate_parts(r: &Request, s: &Stimulus) -> Result<(), String> {
    if [
        r.synthetic.is_some(),
        r.producer_cases.is_some(),
        r.acquisition_sequence.is_some(),
        r.stateful_vtec.is_some(),
        r.integrated_chain.is_some(),
        r.limiter_sequence.is_some(),
        r.adaptive_limiter.is_some(),
        r.idle_target.is_some(),
        r.idle_contexts.is_some(),
        r.fuel_map_lookup.is_some(),
        r.fuel_calculation_chain.is_some(),
        r.fuel_additive_correction_chain.is_some(),
        r.fuel_factor_production_chain.is_some(),
        r.limiter_fuel_gate_chain.is_some(),
        r.adaptive_limiter_fuel_gate_chain.is_some(),
        r.fuel_post_store_chain.is_some(),
        r.fuel_post_store_consumer_chain.is_some(),
        r.fuel_post_selection_critical_chain.is_some(),
        r.vtec_fuel_chain.is_some(),
        r.ignition_map_lookup.is_some(),
        r.ignition_selector_chain.is_some(),
        r.ignition_correction_chain.is_some(),
        r.shared_calibration_chain.is_some(),
    ]
    .into_iter()
    .any(|p| p)
    {
        return Err("M2s accepts only its own closed stimulus".into());
    }
    if s.initial_state.software_sources.word011a_mask1034 & !0x1034 != 0 {
        return Err("M2s011A source permits only mask1034; neighboring owners are retained".into());
    }
    post_store::validate_parts(
        r,
        s.format_version,
        &s.initial_state.prefix,
        &s.calls,
        &s.trace_call_indexes,
    )
}
pub fn contract() -> SliceContract {
    SliceContract {
        entry_pc: 0x22B1,
        exit_pcs: vec![0x236C],
        code_ranges: vec![[0x22B1, 0x233C], [0x2369, 0x236C], [0x5991, 0x59A6]],
        psw: 0x0101,
        lrb: 0x20,
        usp: 0x280,
        instruction_budget: 192,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: Some([0x6106, 0x610C]),
    }
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({
        "id":"fuelCommonResultConsumerChain","formatVersion":1,
        "prefixContract":post_selection_critical::entry_contracts()[0],
        "nativeContinuation":[0x22B1,0x236C],
        "codeRanges":[[0x22B1,0x233C],[0x2369,0x236C],[0x5991,0x59A6]],
        "instructionBudget":192,"programDataRange":[0x6106,0x610C],
        "sourcePolicy":"OnceInitialSoftwareSnapshot;NoEventOrBoundaryReseed",
        "sourceMasks":[[0x11A,0x1034],[0x11F,32],[0x120,1],[0xB7,1]],
        "sourceWords":[0x136],"sourceBytes":[0xBE],"initialHistoryBytes":[0x13B,0x13D],
        "nativeOutput":[0x236A,0x13B,8],"nativeCounterWriter":[0x2321,0x13D,8],
        "quartetWriters":[[0x22A5,0x3B6,16],[0x22A8,0x3B8,16],[0x22AB,0x3BA,16],[0x22AE,0x3BC,16]],
        "dynamicQuartetReaders":[],"scriptedConsumerEntry":"NotEstablished;NotRun",
        "overallConsumerChain":"Partial;StaticConsumersNotRun",
        "unresolvedBoundaries":[[0x2333,"ZeroDivisorUndefined"],[0x233A,"PrimaryJgtConditionConflict"]],
        "laterStaticBoundaries":[[0x2394,"Unknown0F00"],[0x239E,"P1AccessNotRun"],[0x06A5,"IRQDependentRtiNotRun"]],
        "irqDelivery":"NotInjected","pendingInterrupt":"NoneInjected;NotModeled","elapsedTime":"None",
        "p2":"NotRun","physicalRpmAvailable":false,"assumptions":[],"stop":"BeforeInstruction236C"
    })]
}
pub fn admission(d: &Decoded) -> FormAdmission {
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    match (p.mnemonic, p.dd_mode, p.bytes_pat) {
        ("MOV er2, off N8", 'U', ["B4", "N8", "4A"]) if d.fields.n8 == 0x36 => {
            FormAdmission::Allowed
        }
        ("AND A, #N16", '1', ["D6", "NL", "NH"]) if d.fields.n16 == 0x1034 => {
            FormAdmission::Allowed
        }
        ("LCB A, N16[DP]", 'U', ["92", "AB", "NL", "NH"]) if d.fields.n16 == 0x6106 => {
            FormAdmission::Allowed
        }
        ("CAL addr16", 'U', ["32", "addrl", "addrh"]) if d.fields.addr16 == 0x5991 => {
            FormAdmission::Allowed
        }
        ("LB A, #N8", 'R', ["77", "N8"])
        | ("LB A, off N8", 'R', ["F4", "N8"])
        | ("LB A, N8", 'R', ["F5", "N8"])
        | ("L A, off N8", 'S', ["E4", "N8"])
        | ("L A, [DP]", 'S', ["E2"])
        | ("L A, #N16", 'S', ["67", "NL", "NH"])
        | ("STB A, off N8", '0', ["D4", "N8"])
        | ("STB A, r6", '0', ["8E"])
        | ("CMPB A, off N8", '0', ["C7", "N8"])
        | ("CMPB A, #N8", '0', ["C6", "N8"])
        | ("CMPB N'8, #N8", 'U', ["C5", "N'8", "C0", "N8"])
        | ("CMPB N8, A", 'U', ["C5", "N8", "C1"])
        | ("CMP A, #N16", '1', ["C6", "NL", "NH"])
        | ("JBS off N8.0, rel8", 'U', ["E8", "N8", "rel8"])
        | ("JBS off N8.1, rel8", 'U', ["E9", "N8", "rel8"])
        | ("JBS off N8.2, rel8", 'U', ["EA", "N8", "rel8"])
        | ("JBS off N8.4, rel8", 'U', ["EC", "N8", "rel8"])
        | ("JBS off N8.5, rel8", 'U', ["ED", "N8", "rel8"])
        | ("JBR off N8.1, rel8", 'U', ["D9", "N8", "rel8"])
        | ("MB off N8.0, C", 'U', ["C4", "N8", "38"])
        | ("MB off N8.1, C", 'U', ["C4", "N8", "39"])
        | ("MB off N8.2, C", 'U', ["C4", "N8", "3A"])
        | ("MB C, N8.0", 'U', ["C5", "N8", "28"])
        | ("JNE rel8", 'U', ["CE", "rel8"])
        | ("JEQ rel8", 'U', ["C9", "rel8"])
        | ("JGE rel8", 'U', ["CD", "rel8"])
        | ("JLT rel8", 'U', ["CA", "rel8"])
        | ("SJ rel8", 'U', ["CB", "rel8"])
        | ("MOVB r6, #N8", 'U', ["9E", "N8"])
        | ("MOV DP, #N16", 'U', ["62", "NL", "NH"])
        | ("CLR DP", 'U', ["92", "15"])
        | ("CLR er0", 'U', ["44", "15"])
        | ("INC DP", 'U', ["72"])
        | ("ADD DP, #N16", 'U', ["92", "80", "NL", "NH"])
        | ("SUBB A, #N8", '0', ["A6", "N8"])
        | ("CLRB A", 'R', ["FA"])
        | ("DIV", 'U', ["90", "37"])
        | ("MOV er0, #N16", 'U', ["44", "98", "NL", "NH"])
        | ("MUL", 'U', ["90", "35"])
        | ("SRL er1", 'U', ["45", "E7"])
        | ("ROR A", '1', ["43"])
        | ("CMPB r2, #N8", 'U', ["22", "C0", "N8"])
        | ("RT", 'U', ["01"]) => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}
fn ranges() -> Vec<[u16; 2]> {
    vec![
        [0, 8],
        [0x88, 0x90],
        [0xB7, 0xB8],
        [0xBE, 0xBF],
        [0xD9, 0xDA],
        [0x100, 0x108],
        [0x11A, 0x11C],
        [0x11F, 0x120],
        [0x120, 0x121],
        [0x125, 0x126],
        [0x12B, 0x12D],
        [0x133, 0x134],
        [0x136, 0x138],
        [0x13B, 0x13C],
        [0x13D, 0x13E],
        [0x3B4, 0x3B6],
        [0x7FE, 0x800],
    ]
}
fn state(cpu: &Cpu, bus: &mut Bus) -> State {
    let prefix = post_selection_critical::state(cpu, bus);
    bus.configure_scoped_access(ranges(), 4096);
    State {
        prefix,
        mode012b: read_data_u8(cpu, bus, 0x12B),
        word011a: read_data_u16(cpu, bus, 0x11A),
        byte011f: read_data_u8(cpu, bus, 0x11F),
        byte0120: read_data_u8(cpu, bus, 0x120),
        byte00be: read_data_u8(cpu, bus, 0xBE),
        byte00b7: read_data_u8(cpu, bus, 0xB7),
        word0136: read_data_u16(cpu, bus, 0x136),
        byte013b: read_data_u8(cpu, bus, 0x13B),
        byte013d: read_data_u8(cpu, bus, 0x13D),
    }
}
fn initialize(rom: &[u8], pattern: u8, initial: &Initial) -> (Cpu, Bus) {
    let (mut cpu, mut bus) = post_store::initialize(rom, pattern, &initial.prefix);
    bus.configure_scoped_access(ranges(), 4096);
    let s = &initial.software_sources;
    let prior = read_data_u16(&cpu, &mut bus, 0x11A);
    write_data_u16(
        &mut cpu,
        &mut bus,
        0x11A,
        (prior & !0x1034) | s.word011a_mask1034,
    );
    for (address, mask, on) in [
        (0x11F, 32, s.bit011f5),
        (0x120, 1, s.bit0120_0),
        (0xB7, 1, s.bit00b7_0),
    ] {
        let prior = read_data_u8(&cpu, &mut bus, address);
        write_data_u8(
            &mut cpu,
            &mut bus,
            address,
            (prior & !mask) | if on { mask } else { 0 },
        );
    }
    write_data_u8(&mut cpu, &mut bus, 0xBE, s.byte00be);
    write_data_u16(&mut cpu, &mut bus, 0x136, s.word0136);
    write_data_u8(&mut cpu, &mut bus, 0x13B, s.history013b);
    write_data_u8(&mut cpu, &mut bus, 0x13D, s.history013d);
    (cpu, bus)
}
pub(crate) fn execute_suffix(cpu: &mut Cpu, bus: &mut Bus) -> Suffix {
    // Configuration only at22B1. No enter/PC/register/RAM writes or source application.
    bus.configure_scoped_access(ranges(), 4096);
    bus.set_program_data_ranges(vec![[0x6106, 0x610C]]);
    bus.clear_program_reads();
    let mut c = contract();
    // This immutable-in-suffix source is the only admitted MOV er2 operand.
    // Strict stop precedes undefined DIV, rather than accepting retained old operands.
    let zero_divisor = read_data_u16(cpu, bus, 0x136) == 0;
    if zero_divisor {
        c.exit_pcs.push(0x2333);
    }
    let entry = boundary(cpu, bus);
    bus.begin_native_accesses();
    bus.begin_write_journal();
    bus.start_decision_observer();
    let mut result = execute_in_state_observed(cpu, bus, &c, &[], true, Some(admission), true);
    if result.status == 0 && zero_divisor && result.stop_pc == 0x2333 {
        result.status = 1;
        result.error = Some("unresolved DIV zero divisor: primary result undefined".into());
    }
    let accesses = bus.end_native_accesses();
    let stage = Stage {
        result,
        writes: bus.end_write_journal(),
        events: bus.finish_decision_observer(),
        ssp_after: cpu.ssp,
    };
    let exit = boundary(cpu, bus);
    Suffix {
        entry,
        exit,
        stage,
        accesses,
    }
}
pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r
        .fuel_common_result_consumer_chain
        .as_ref()
        .expect("validated");
    response.entry_contracts = entry_contracts();
    response.common_result_sequences =
        Some(run_sequences(&r.images[0].rom, &r.scratch_patterns, s));
    Ok(response)
}
pub(crate) fn run_sequences(rom: &[u8], patterns: &[u8], s: &Stimulus) -> Vec<Sequence> {
    let mut sequences = vec![];
    for &pattern in patterns {
        let (mut cpu, mut bus) = initialize(rom, pattern, &s.initial_state);
        let mut stopped = false;
        let mut checkpoints = vec![];
        for c in &s.calls {
            let before = state(&cpu, &mut bus);
            let mut row = Checkpoint {
                index: c.adaptive.fuel.index,
                status: 4,
                prefix: post_selection_critical::checkpoint(&cpu, &mut bus, c),
                state_before: before.clone(),
                state_at_entry: None,
                state_after: before,
                common_consumer: None,
                software_result13b: None,
            };
            if !stopped {
                post_selection_critical::execute_checkpoint(&mut cpu, &mut bus, c, &mut row.prefix);
                row.status = row.prefix.status;
                if row.status == 0 {
                    row.state_at_entry = Some(state(&cpu, &mut bus));
                    let suffix = execute_suffix(&mut cpu, &mut bus);
                    row.status = suffix.stage.result.status;
                    row.common_consumer = Some(suffix);
                }
                row.state_after = state(&cpu, &mut bus);
                if row.status == 0 {
                    row.software_result13b = Some(row.state_after.byte013b);
                }
                stopped = row.status != 0;
            }
            checkpoints.push(row);
        }
        sequences.push(Sequence {
            scratch_pattern: pattern,
            checkpoints,
        });
    }
    sequences
}

#[cfg(test)]
mod tests {
    use super::*;
    fn invented_loop(words: [u16; 4]) -> (Vec<u8>, SliceContract) {
        let mut rom = vec![];
        rom.extend_from_slice(&[0x60, 0, 0]);
        for (i, w) in words.iter().enumerate() {
            rom.extend_from_slice(&[0x67, *w as u8, (*w >> 8) as u8, 0xD0, (i * 2) as u8, 3]);
        }
        rom.extend_from_slice(&[0x44, 0x98, 0, 0]);
        rom.extend_from_slice(&[
            0xE0, 0, 3, 0x08, 0x88, 0x90, 0x80, 2, 0, 0x90, 0xC0, 8, 0, 0xCA, 0xF1,
        ]);
        rom.extend_from_slice(&[0x60, 0, 0, 0xD0, 0x40, 3, 0xF5, 0x24]);
        let c = SliceContract {
            entry_pc: 0,
            exit_pcs: vec![52],
            code_ranges: vec![[0, 54]],
            psw: 0x3301,
            lrb: 0x20,
            usp: 0x280,
            instruction_budget: 64,
            data_seeds: vec![],
            output_addresses: vec![],
            program_read_range: None,
        };
        (rom, c)
    }

    #[test]
    fn invented_native_loop_has_four_separate_store_and_read_generations_even_for_equal_values() {
        for words in [[7u16; 4], [3, 11, 29, 47]] {
            for partial in [false, true] {
                let (rom, mut c) = invented_loop(words);
                if partial {
                    c.instruction_budget = 22;
                }
                let (mut cpu, mut bus) = crate::runner::seed_machine(&rom, &c, 0xA5);
                bus.begin_native_accesses();
                bus.begin_write_journal();
                let result =
                    execute_in_state_observed(&mut cpu, &mut bus, &c, &[], true, None, true);
                let accesses = bus.end_native_accesses();
                let writes = bus.end_write_journal();
                assert_eq!(result.status, if partial { 3 } else { 0 });
                let slot_writes = accesses
                    .iter()
                    .filter(|a| a[3] == 1 && (0x300..0x308).contains(&a[1]))
                    .copied()
                    .collect::<Vec<_>>();
                let slot_reads = accesses
                    .iter()
                    .filter(|a| a[3] == 0 && (0x300..0x308).contains(&a[1]))
                    .copied()
                    .collect::<Vec<_>>();
                assert_eq!(slot_writes.len(), 4);
                for (i, w) in words.iter().enumerate() {
                    assert_eq!(
                        slot_writes[i],
                        [6 + i as u32 * 6, 0x300 + i as u32 * 2, 16, 1, u32::from(*w)]
                    );
                }
                assert_eq!(slot_reads.len(), if partial { 2 } else { 4 });
                for (i, a) in slot_reads.iter().enumerate() {
                    assert_eq!(*a, [31, 0x300 + i as u32 * 2, 16, 0, u32::from(words[i])]);
                    let writer_position =
                        accesses.iter().position(|a| a == &slot_writes[i]).unwrap();
                    let reader_position =
                        accesses.iter().position(|a| a == &slot_reads[i]).unwrap();
                    assert!(writer_position < reader_position);
                }
                assert!(accesses.iter().all(|a| a[1] != 0x24));
                if partial {
                    assert_eq!(result.stop_pc, 31);
                    assert!(!writes.iter().any(|w| w[0] == 0x340));
                } else {
                    let sum = words.iter().copied().sum::<u16>();
                    assert!(accesses.contains(&[49, 0x340, 16, 1, u32::from(sum)]));
                    assert_eq!(read_data_u16(&cpu, &mut bus, 0x340), sum);
                }
            }
        }
    }

    fn toy(partial: bool) -> (Cpu, Bus) {
        let mut rom = vec![0; 32768];
        // Invented byte producer and spaced jumps, not the recovered source calculation.
        rom[0x22B1..0x22B9].copy_from_slice(&[0x77, 41, 0xD4, 0x3D, 0xC4, 0x2B, 0x3A, 0xCB]);
        rom[0x22B9] = 0x6B; // jump2325
        rom[0x2325..0x2327].copy_from_slice(&[0xCB, 0x43]);
        rom[0x236A..0x236C].copy_from_slice(&[0xD4, 0x3B]);
        if partial {
            rom[0x2325..0x2327].copy_from_slice(&[0xC8, 0]);
        }
        let (mut cpu, mut bus) = crate::runner::seed_machine(&rom, &contract(), 0xA5);
        cpu.a = 0xCAFE;
        cpu.ssp = 0x7FE;
        write_data_u16(&mut cpu, &mut bus, 0x136, 1);
        (cpu, bus)
    }
    #[test]
    fn local_native_store_preserves_entire_entry_without_reseed_and_partial_writes_survive() {
        for partial in [false, true] {
            let (mut cpu, mut bus) = toy(partial);
            let before = boundary(&cpu, &mut bus);
            let s = execute_suffix(&mut cpu, &mut bus);
            assert_eq!(s.entry, before);
            assert_eq!(s.stage.result.status, if partial { 1 } else { 0 });
            assert!(s.accesses.contains(&[0x22B3, 0x13D, 8, 1, 41]));
            assert_eq!(read_data_u8(&cpu, &mut bus, 0x13D), 41);
            if partial {
                assert!(!s.stage.writes.iter().any(|w| w[0] == 0x13B));
            } else {
                assert!(s.accesses.contains(&[0x236A, 0x13B, 8, 1, 41]));
                assert_eq!(s.exit.pc, 0x236C);
            }
            assert!(s.accesses.iter().all(|r| !(0x3B6..0x3BE).contains(&r[1])));
            assert_eq!(s.exit.lrb, s.entry.lrb);
            assert_eq!(s.exit.usp, s.entry.usp);
            assert_eq!(s.exit.ssp, s.entry.ssp);
        }
    }
    #[test]
    fn strict_admission_refuses_gt_disputed_byte_sub_and_wrong_divisor_source() {
        for (bytes, dd) in [
            (&[0xC8, 0][..], true),
            (&[0x47, 0x81][..], true),
            (&[0x45, 0x81][..], true),
            (&[0xA7, 0x3D][..], false),
            (&[0xB4, 0x38, 0x4A][..], true),
            (&[0x26, 0xA0, 1][..], true),
        ] {
            let d = crate::decoder::decode(dd, |i| bytes.get(i).copied().unwrap_or(0)).unwrap();
            assert_eq!(admission(&d), FormAdmission::Unsupported);
        }
        assert_eq!(post_selection_critical::contract().exit_pcs, vec![0x22B1]);
    }
    #[test]
    fn zero_divisor_stops_before_undefined_div_without_register_or_result_fabrication() {
        let (mut cpu, mut bus) = toy(false);
        cpu.pc = 0x2333;
        write_data_u16(&mut cpu, &mut bus, 0x136, 0);
        let before = boundary(&cpu, &mut bus);
        let s = execute_suffix(&mut cpu, &mut bus);
        assert_eq!(s.stage.result.status, 1);
        assert_eq!(s.stage.result.steps, 0);
        assert_eq!(s.exit, before);
        assert!(s.stage.writes.is_empty());
        assert!(s.accesses.is_empty());
    }
}
