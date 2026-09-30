//! M2q: native DATA0150 consumer, selection and near-call result on the same state.
//! No host result, mode-bit setter, entry/reset, or interrupt/peripheral expansion.
use crate::{
    adaptive::Stage,
    bus::Bus,
    cpu::Cpu,
    decoder::Decoded,
    exec::{read_data_u16, read_data_u8},
    full_decoder::FULL_OPCODES,
    instruction_forms::FormAdmission,
    post_store::{self, Suffix},
    protocol::{Request, Response},
    runner::{execute_in_state_observed, SliceContract},
    vtec_fuel::boundary,
};
use serde::Serialize;

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Checkpoint {
    pub index: u32,
    pub status: i32,
    pub prefix: post_store::Checkpoint,
    pub mode012c_before: u8,
    pub mode012c_after: u8,
    pub word0150_before: u16,
    pub word0150_after: u16,
    pub consumer: Option<Suffix>,
    pub selected_scaled_word_x1: Option<u16>,
    pub retained_or_zero_a: Option<u16>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Sequence {
    pub scratch_pattern: u8,
    pub checkpoints: Vec<Checkpoint>,
}
pub fn validate_request(r: &Request) -> Result<(), String> {
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
        r.vtec_fuel_chain.is_some(),
        r.ignition_map_lookup.is_some(),
        r.ignition_selector_chain.is_some(),
        r.ignition_correction_chain.is_some(),
        r.shared_calibration_chain.is_some(),
    ]
    .into_iter()
    .any(|present| present)
    {
        return Err("M2q accepts only its own closed stimulus".into());
    }
    let s = r
        .fuel_post_store_consumer_chain
        .as_ref()
        .ok_or("M2q stimulus required")?;
    post_store::validate_stimulus(r, s)
}
pub fn contract() -> SliceContract {
    SliceContract {
        entry_pc: 0x223B,
        exit_pcs: vec![0x2259],
        code_ranges: vec![[0x223B, 0x2259], [0x5991, 0x59A6]],
        psw: 0x0101,
        lrb: 0x20,
        usp: 0x280,
        instruction_budget: 48,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    }
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({
        "id":"fuelPostStoreConsumerChain","formatVersion":1,
        "prefixContract":post_store::entry_contracts()[0],
        "nativeContinuation":[0x223B,0x2259],"helperRange":[0x5991,0x59A6],
        "nativeGeneration":[0x2239,0x150,16],"comparison":[0x223D,0x14C,0x150,16],
        "nativeBitGeneration":[0x223F,0x12C,32],"softwareResult":[0x2254,0x88,16],
        "nextReaders":[0x2261,0x2264,0x2266],"assumptions":[],
        "physicalRpmAvailable":false,"stop":"BeforeInstruction2259",
        "configuration60f8":"UnchangedZero;NotReachedBefore2259"
    })]
}
pub fn admission(d: &Decoded) -> FormAdmission {
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    // This one direct-word read is the architectural ACC alias, not arbitrary RAM/SFR.
    if p.mnemonic == "L A, N8" && d.fields.n8 != 6 {
        return FormAdmission::Unsupported;
    }
    match (p.mnemonic, p.dd_mode, p.bytes_pat) {
        ("L A, off N8", 'S', ["E4", "N8"])
        | ("L A, N8", 'S', ["E5", "N8"])
        | ("CMP A, off N8", '1', ["C7", "N8"])
        | ("MB off N8.5, C", 'U', ["C4", "N8", "3D"])
        | ("JGE rel8", 'U', ["CD", "rel8"])
        | ("JEQ rel8", 'U', ["C9", "rel8"])
        | ("ADD A, off N8", '1', ["87", "N8"])
        | ("L A, #N16", 'S', ["67", "NL", "NH"])
        | ("CAL addr16", 'U', ["32", "addrl", "addrh"])
        | ("MOV er0, #N16", 'U', ["44", "98", "NL", "NH"])
        | ("MUL", 'U', ["90", "35"])
        | ("SRL er1", 'U', ["45", "E7"])
        | ("ROR A", '1', ["43"])
        | ("CMPB r2, #N8", 'U', ["22", "C0", "N8"])
        | ("MOV X1, A", 'U', ["50"])
        | ("JBR off N8.5, rel8", 'U', ["DD", "N8", "rel8"])
        | ("CLR A", 'S', ["F9"])
        | ("RT", 'U', ["01"]) => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}
pub(crate) fn execute_suffix(cpu: &mut Cpu, bus: &mut Bus) -> Suffix {
    // Only observation/access/admission configuration changes at223B. No machine-state write.
    bus.configure_scoped_access(
        vec![
            [0, 8],
            [0x88, 0x90],
            [0x100, 0x108],
            [0x12C, 0x12D],
            [0x144, 0x146],
            [0x14C, 0x14E],
            [0x150, 0x152],
            [0x7FE, 0x800],
        ],
        4096,
    );
    bus.set_program_data_ranges(vec![]);
    bus.clear_program_reads();
    let entry = boundary(cpu, bus);
    bus.begin_native_accesses();
    bus.begin_write_journal();
    bus.start_decision_observer();
    let result = execute_in_state_observed(cpu, bus, &contract(), &[], true, Some(admission), true);
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
fn observations(cpu: &Cpu, bus: &mut Bus) -> (u8, u16) {
    bus.configure_scoped_access(vec![[0x12C, 0x12D], [0x150, 0x152]], 4096);
    (
        read_data_u8(cpu, bus, 0x12C),
        read_data_u16(cpu, bus, 0x150),
    )
}
pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r
        .fuel_post_store_consumer_chain
        .as_ref()
        .expect("validated");
    let mut sequences = vec![];
    for &pattern in &r.scratch_patterns {
        let (mut cpu, mut bus) =
            post_store::initialize(&r.images[0].rom, pattern, &s.initial_state);
        let mut stopped = false;
        let mut checkpoints = vec![];
        for c in &s.calls {
            let (mode012c_before, word0150_before) = observations(&cpu, &mut bus);
            let prefix = post_store::checkpoint(&cpu, &mut bus, c);
            let mut row = Checkpoint {
                index: c.adaptive.fuel.index,
                status: 4,
                prefix,
                mode012c_before,
                mode012c_after: mode012c_before,
                word0150_before,
                word0150_after: word0150_before,
                consumer: None,
                selected_scaled_word_x1: None,
                retained_or_zero_a: None,
            };
            if !stopped {
                post_store::execute_checkpoint(&mut cpu, &mut bus, c, &mut row.prefix);
                row.status = row.prefix.status;
                if row.status == 0 {
                    let suffix = execute_suffix(&mut cpu, &mut bus);
                    row.status = suffix.stage.result.status;
                    if row.status == 0 {
                        row.selected_scaled_word_x1 = Some(suffix.exit.x1);
                        row.retained_or_zero_a = Some(cpu.a);
                    }
                    row.consumer = Some(suffix);
                }
                stopped = row.status != 0;
                (row.mode012c_after, row.word0150_after) = observations(&cpu, &mut bus);
            }
            checkpoints.push(row);
        }
        sequences.push(Sequence {
            scratch_pattern: pattern,
            checkpoints,
        });
    }
    response.entry_contracts = entry_contracts();
    response.consumer_sequences = Some(sequences);
    Ok(response)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        exec::{write_data_u16, write_data_u8},
        runner::seed_machine,
    };

    fn toy(generation: u16, operand: u16, old_storage: u16, partial: bool) -> (Cpu, Bus, Suffix) {
        let mut rom = vec![0; 32768];
        // Invented immediate producer and jump, not the OEM gate/subtract/clamp routine.
        rom[0x2204..0x220B].copy_from_slice(&[
            0x67,
            generation as u8,
            (generation >> 8) as u8,
            0xD4,
            0x50,
            0xCB,
            0x30,
        ]);
        // Invented equality-first selection. Its helper multiplies by3, with no OEM shifts/clamp.
        rom[0x223B..0x224F].copy_from_slice(&[
            0xE4, 0x4C, 0x50, 0xC7, 0x50, 0xC4, 0x2C, 0x3D, 0xC9, 0x11, 0x32, 0x91, 0x59, 0x50,
            0xDD, 0x2C, 0x0D, 0xF9, 0xC9, 0x0A,
        ]);
        rom[0x2256..0x2259].copy_from_slice(&[0x50, 0xC9, 0]);
        rom[0x5991..0x5998].copy_from_slice(&[0x44, 0x98, 3, 0, 0x90, 0x35, 1]);
        if partial {
            rom[0x2243..0x2245].copy_from_slice(&[0x47, 0x81]);
        }
        let (mut cpu, mut bus) = seed_machine(&rom, &post_store::contract(), 170);
        cpu.ssp = 0x7FE;
        write_data_u16(&mut cpu, &mut bus, 0x150, old_storage);
        write_data_u16(&mut cpu, &mut bus, 0x14C, operand);
        write_data_u8(&mut cpu, &mut bus, 0x12C, 0x95);
        let prefix = post_store::execute_suffix(&mut cpu, &mut bus);
        assert_eq!(prefix.stage.result.status, 0);
        assert_eq!(prefix.exit.pc, 0x223B);
        assert!(prefix
            .accesses
            .contains(&[0x2207, 0x150, 16, 1, generation as u32]));
        (cpu, bus, prefix)
    }

    #[test]
    fn invented_native_generation_flows_into_comparison_and_actual_near_call_without_reset() {
        for (operand, result_x1, result_a) in [(111, 333, 0), (321, 321, 321), (700, 2100, 2100)] {
            let (mut cpu, mut bus, prefix) = toy(321, operand, 9, false);
            let consumer = execute_suffix(&mut cpu, &mut bus);
            assert_eq!(consumer.entry, prefix.exit);
            assert_eq!(
                consumer.stage.result.status, 0,
                "{:?}",
                consumer.stage.result.error
            );
            assert_eq!(
                (consumer.exit.x1, consumer.exit.accumulator),
                (result_x1, result_a)
            );
            assert!(consumer
                .accesses
                .contains(&[0x223B, 0x14C, 16, 0, operand as u32]));
            assert!(consumer.accesses.contains(&[0x223E, 0x150, 16, 0, 321]));
            let compare = consumer
                .stage
                .events
                .iter()
                .find(|e| e[0] == 0x223E)
                .unwrap();
            assert_eq!([compare[6], compare[7]], [operand as u32, 321]);
            assert_eq!(compare[5] & 0x8000 != 0, operand < 321);
            assert_eq!(compare[5] & 0x4000 != 0, operand == 321);
            assert_eq!(consumer.exit.ssp, prefix.exit.ssp);
            assert_eq!(consumer.exit.lrb, prefix.exit.lrb);
            assert_eq!(consumer.exit.usp, prefix.exit.usp);
            for p in [0x2259, 0x226F, 0x2273, 0x227A, 0x229F] {
                assert!(!consumer
                    .stage
                    .result
                    .executed_instruction_bytes
                    .as_ref()
                    .unwrap()
                    .contains(&p));
            }
            if operand != 321 {
                assert!(consumer.accesses.contains(&[0x2245, 0x7FE, 16, 1, 0x2248]));
                assert!(consumer.accesses.contains(&[0x5997, 0x7FE, 16, 0, 0x2248]));
                assert!(consumer
                    .stage
                    .events
                    .iter()
                    .any(|e| e[0] == 0x5997 && e[1] == 0x2248));
            } else {
                assert!(!consumer
                    .stage
                    .events
                    .iter()
                    .any(|e| (0x5991..0x59A6).contains(&e[0])));
            }
        }
    }

    #[test]
    fn same_value_store_is_new_generation_and_native_bit_write_preserves_shared_neighbors() {
        let (mut cpu, mut bus, prefix) = toy(321, 111, 321, false);
        assert_eq!(prefix.stage.writes, vec![[0x150, 16, 321]]);
        let consumer = execute_suffix(&mut cpu, &mut bus);
        let next_mode = 0xB5;
        assert!(consumer.accesses.contains(&[0x2240, 0x12C, 8, 0, 0x95]));
        assert!(consumer
            .accesses
            .contains(&[0x2240, 0x12C, 8, 1, next_mode]));
        assert!(consumer
            .accesses
            .contains(&[0x2249, 0x12C, 8, 0, next_mode]));
        assert_eq!(observations(&cpu, &mut bus), (next_mode as u8, 321));
        assert_eq!(next_mode & !32, 0x95 & !32);
        assert!(!consumer
            .stage
            .writes
            .iter()
            .any(|w| w[0] < 0x152 && w[0] + w[1] / 8 > 0x150));
    }

    #[test]
    fn unresolved_consumer_keeps_native_bit_generation_and_rejects_partial_result() {
        let (mut cpu, mut bus, prefix) = toy(321, 111, 9, true);
        let consumer = execute_suffix(&mut cpu, &mut bus);
        assert_eq!(consumer.entry, prefix.exit);
        assert_eq!(consumer.stage.result.status, 1);
        assert_eq!(consumer.stage.result.stop_pc, 0x2243);
        assert_eq!(
            consumer.stage.writes,
            vec![[0x88, 16, 111], [0x12C, 8, 0xB5]]
        );
        assert_eq!(observations(&cpu, &mut bus), (0xB5, 321));
    }

    #[test]
    fn new_exact_registry_rejects_wrong_width_disputed_forms_and_other_direct_aliases() {
        for (bytes, dd) in [
            (&[0x47, 0x81][..], true),
            (&[0x45, 0x81][..], true),
            (&[0xF4, 0x50][..], true),
            (&[0xC7, 0x50][..], false),
            (&[0xE5, 7][..], true),
            (&[0xA6, 1][..], false),
        ] {
            let d = crate::decoder::decode(dd, |i| bytes.get(i).copied().unwrap_or(0)).unwrap();
            assert_eq!(admission(&d), FormAdmission::Unsupported);
        }
        let d = crate::decoder::decode(true, |i| [0xE5, 6].get(i).copied().unwrap_or(0)).unwrap();
        assert_eq!(admission(&d), FormAdmission::Allowed);
        assert_eq!(post_store::contract().exit_pcs, vec![0x223B]);
        assert_eq!(contract().exit_pcs, vec![0x2259]);
    }
}
