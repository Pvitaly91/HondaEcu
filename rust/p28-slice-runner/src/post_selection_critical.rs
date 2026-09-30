//! M2r synchronous software IE/PSWH, RAM handoff and unchanged configuration bypass.
//! One persistent machine; no IRQ delivery, elapsed time, host restore or ready results.
use crate::{
    adaptive::Stage,
    bus::Bus,
    cpu::Cpu,
    decoder::Decoded,
    exec::{read_data_u16, read_data_u8},
    full_decoder::FULL_OPCODES,
    instruction_forms::FormAdmission,
    post_store::{self, Suffix},
    post_store_consumer,
    protocol::{Request, Response},
    runner::{execute_in_state_observed, SliceContract},
    vtec_fuel::boundary,
};
use serde::Serialize;

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct State {
    pub ie: u16,
    pub restore_ie: u16,
    /// Ordered software words0190,0192,0194.
    pub words019x: [u16; 3],
    pub word03b4: u16,
    /// Ordered software words03B6,03B8,03BA,03BC.
    pub common_words03b6: [u16; 4],
    pub mode012c: u8,
    pub word0150: u16,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Checkpoint {
    pub index: u32,
    pub status: i32,
    pub prefix: post_store_consumer::Checkpoint,
    pub state_before: State,
    pub state_at_entry: Option<State>,
    pub state_after: State,
    pub critical: Option<Suffix>,
    pub words019x: Option<[u16; 3]>,
    pub common_words03b6: Option<[u16; 4]>,
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
        r.fuel_post_store_consumer_chain.is_some(),
        r.vtec_fuel_chain.is_some(),
        r.ignition_map_lookup.is_some(),
        r.ignition_selector_chain.is_some(),
        r.ignition_correction_chain.is_some(),
        r.shared_calibration_chain.is_some(),
    ]
    .into_iter()
    .any(|present| present)
    {
        return Err("M2r accepts only its own closed stimulus".into());
    }
    post_store::validate_stimulus(
        r,
        r.fuel_post_selection_critical_chain
            .as_ref()
            .ok_or("M2r stimulus required")?,
    )
}
pub fn contract() -> SliceContract {
    SliceContract {
        entry_pc: 0x2259,
        exit_pcs: vec![0x22B1],
        code_ranges: vec![[0x2259, 0x2275], [0x229F, 0x22B1], [0x5991, 0x59A6]],
        psw: 0x0101,
        lrb: 0x20,
        usp: 0x280,
        instruction_budget: 48,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: Some([0x60F8, 0x60F9]),
    }
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({
        "id":"fuelPostSelectionCriticalChain","formatVersion":1,
        "prefixContract":post_store_consumer::entry_contracts()[0],
        "nativeContinuation":[0x2259,0x22B1],
        "codeRanges":[[0x2259,0x2275],[0x229F,0x22B1],[0x5991,0x59A6]],
        "helperRange":[0x5991,0x59A6],
        "softwareIe":{"address":0x1A,"width":16,"mask":0x02A0,"maskPc":0x2259,"restoreSource":0xF8,"restorePc":0x226D},
        "pswh":{"clear":[0x225E,1],"set":[0x2268,1]},
        "nativeStores":[[0x2261,0x194,16],[0x2264,0x190,16],[0x2266,0x192,16],
            [0x22A5,0x3B6,16],[0x22A8,0x3B8,16],[0x22AB,0x3BA,16],[0x22AE,0x3BC,16]],
        "configurationRead":[0x226F,0x60F8,8],"bypass":[0x2273,0x229F],
        "excludedOptionalCode":[0x2275,0x229F],"irqDelivery":"NotInjected",
        "pendingInterrupt":"NoneInjected;NotModeled","elapsedTime":"None",
        "initialHistory":"DiagnosticScratchOnce;NoSourceInputs",
        "physicalRpmAvailable":false,"assumptions":[],"stop":"BeforeInstruction22B1"
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
        ("AND N8, #N16", 'U', ["B5", "N8", "D0", "NL", "NH"])
            if d.fields.n8 == 0x1A && d.fields.n16 == 0x02A0 =>
        {
            FormAdmission::Allowed
        }
        ("ANDB PSWH, #N8", 'U', ["A2", "D0", "N8"]) if d.fields.n8 == 0xFE => {
            FormAdmission::Allowed
        }
        ("ORB PSWH, #N8", 'U', ["A2", "E0", "N8"]) if d.fields.n8 == 1 => FormAdmission::Allowed,
        ("L A, N8", 'S', ["E5", "N8"]) if d.fields.n8 == 0xF8 => FormAdmission::Allowed,
        ("ST A, N8", '1', ["D5", "N8"]) if d.fields.n8 == 0x1A => FormAdmission::Allowed,
        ("LCB A, N16", 'U', ["90", "9D", "NL", "NH"]) if d.fields.n16 == 0x60F8 => {
            FormAdmission::Allowed
        }
        ("MOV off N8, X1", 'U', ["90", "7C", "N8"])
        | ("ST A, off N8", '1', ["D4", "N8"])
        | ("JEQ rel8", 'U', ["C9", "rel8"])
        | ("L A, [DP]", 'S', ["E2"])
        | ("CAL addr16", 'U', ["32", "addrl", "addrh"])
        | ("CLR X1", 'U', ["90", "15"])
        | ("ST A, N16[X1]", '1', ["D0", "NL", "NH"])
        | ("MOV er0, #N16", 'U', ["44", "98", "NL", "NH"])
        | ("MUL", 'U', ["90", "35"])
        | ("SRL er1", 'U', ["45", "E7"])
        | ("ROR A", '1', ["43"])
        | ("CMPB r2, #N8", 'U', ["22", "C0", "N8"])
        | ("L A, #N16", 'S', ["67", "NL", "NH"])
        | ("RT", 'U', ["01"]) => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}
fn ranges() -> Vec<[u16; 2]> {
    vec![
        [0, 8],
        [0x1A, 0x1C],
        [0x88, 0x90],
        [0xF8, 0xFA],
        [0x100, 0x108],
        [0x12C, 0x12D],
        [0x150, 0x152],
        [0x190, 0x196],
        [0x3B4, 0x3BE],
        [0x7FE, 0x800],
    ]
}
fn state(cpu: &Cpu, bus: &mut Bus) -> State {
    bus.configure_scoped_access(ranges(), 4096);
    State {
        ie: bus.adaptive_ie().expect("once-only shared IE"),
        restore_ie: read_data_u16(cpu, bus, 0xF8),
        words019x: [0x190, 0x192, 0x194].map(|a| read_data_u16(cpu, bus, a)),
        word03b4: read_data_u16(cpu, bus, 0x3B4),
        common_words03b6: [0x3B6, 0x3B8, 0x3BA, 0x3BC].map(|a| read_data_u16(cpu, bus, a)),
        mode012c: read_data_u8(cpu, bus, 0x12C),
        word0150: read_data_u16(cpu, bus, 0x150),
    }
}
pub(crate) fn execute_suffix(cpu: &mut Cpu, bus: &mut Bus) -> Suffix {
    // Capability/observations only. Deliberately no entry/reset/register or IE setter.
    bus.configure_scoped_access(ranges(), 4096);
    bus.set_program_data_ranges(vec![[0x60F8, 0x60F9]]);
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
pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r
        .fuel_post_selection_critical_chain
        .as_ref()
        .expect("validated");
    let mut sequences = vec![];
    for &pattern in &r.scratch_patterns {
        let (mut cpu, mut bus) =
            post_store::initialize(&r.images[0].rom, pattern, &s.initial_state);
        let mut stopped = false;
        let mut checkpoints = vec![];
        for c in &s.calls {
            let before = state(&cpu, &mut bus);
            let mut row = Checkpoint {
                index: c.adaptive.fuel.index,
                status: 4,
                prefix: post_store_consumer::checkpoint(&cpu, &mut bus, c),
                state_before: before.clone(),
                state_at_entry: None,
                state_after: before,
                critical: None,
                words019x: None,
                common_words03b6: None,
            };
            if !stopped {
                post_store_consumer::execute_checkpoint(&mut cpu, &mut bus, c, &mut row.prefix);
                row.status = row.prefix.status;
                if row.status == 0 {
                    row.state_at_entry = Some(state(&cpu, &mut bus));
                    let suffix = execute_suffix(&mut cpu, &mut bus);
                    row.status = suffix.stage.result.status;
                    row.critical = Some(suffix);
                }
                row.state_after = state(&cpu, &mut bus);
                if row.status == 0 {
                    row.words019x = Some(row.state_after.words019x);
                    row.common_words03b6 = Some(row.state_after.common_words03b6);
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
    response.entry_contracts = entry_contracts();
    response.critical_sequences = Some(sequences);
    Ok(response)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::exec::{step, write_data_u16};

    fn toy(config: u8, partial: bool) -> (Cpu, Bus) {
        let mut rom = vec![0; 32768];
        // Invented producer and rearranged transfers; not an OEM routine or helper.
        for (pc, bytes) in [
            (0x2259, vec![0x90, 0x7C, 0x94]),
            (0x225C, vec![0xB5, 0x1A, 0xD0, 0xA0, 2]),
            (0x2261, vec![0xD4, 0x90]),
            (0x2263, vec![0xA2, 0xD0, 0xFE]),
            (0x2266, vec![0xD4, 0x92]),
            (0x2268, vec![0xE5, 0xF8]),
            (0x226A, vec![0xD5, 0x1A]),
            (0x226C, vec![0xA2, 0xE0, 1]),
            (0x226F, vec![0x90, 0x9D, 0xF8, 0x60]),
            (0x2273, vec![0xC9, 0x2A]),
            (0x229F, vec![0x90, 0x15]),
            (0x22A1, vec![0xE2]),
            (0x22A2, vec![0x32, 0x98, 0x59]),
            (0x22A5, vec![0xD0, 0xBC, 3]),
            (0x22A8, vec![0xD0, 0xB6, 3]),
            (0x22AB, vec![0xD0, 0xBA, 3]),
            (0x22AE, vec![0xD0, 0xB8, 3]),
            (0x5998, vec![0x44, 0x98, 3, 0, 0x90, 0x35, 1]),
        ] {
            rom[pc..pc + bytes.len()].copy_from_slice(&bytes);
        }
        rom[0x60F8] = config;
        if partial {
            rom[0x2263..0x2265].copy_from_slice(&[0x47, 0x81]);
        }
        let (mut cpu, mut bus) = crate::runner::seed_machine(&rom, &contract(), 0xA5);
        cpu.a = 321;
        cpu.set_psw_u16(0xB701);
        bus.set_adaptive_ie(Some(0xBA98));
        write_data_u16(&mut cpu, &mut bus, 0xF8, 0x5AA5);
        write_data_u16(&mut cpu, &mut bus, 0x88, 123);
        write_data_u16(&mut cpu, &mut bus, 0x8C, 0x3B4);
        write_data_u16(&mut cpu, &mut bus, 0x3B4, 700);
        (cpu, bus)
    }
    #[test]
    fn synchronous_shared_ie_mask_and_pswh_edits_preserve_unrelated_cpu_bits_without_irq() {
        let (mut cpu, mut bus) = toy(0, false);
        let entry = boundary(&cpu, &mut bus);
        let suffix = execute_suffix(&mut cpu, &mut bus);
        assert_eq!(suffix.entry, entry);
        assert_eq!(
            suffix.stage.result.status, 0,
            "{:?}",
            suffix.stage.result.error
        );
        assert!(suffix.accesses.contains(&[0x225C, 0x1A, 16, 0, 0xBA98]));
        assert!(suffix.accesses.contains(&[0x225C, 0x1A, 16, 1, 0x0280]));
        assert!(suffix.accesses.contains(&[0x2268, 0xF8, 16, 0, 0x5AA5]));
        assert!(suffix.accesses.contains(&[0x226A, 0x1A, 16, 1, 0x5AA5]));
        let mask = suffix.stage.events.iter().find(|e| e[0] == 0x225C).unwrap();
        assert_eq!(mask[4] & 0x100, mask[5] & 0x100);
        for (pc, on) in [(0x2263, false), (0x226C, true)] {
            let e = suffix.stage.events.iter().find(|e| e[0] == pc).unwrap();
            assert_eq!(e[4] & !0x100, e[5] & !0x100);
            assert_eq!(e[5] & 0x100 != 0, on);
        }
        assert_eq!(bus.adaptive_ie(), Some(0x5AA5));
        assert_eq!(suffix.exit.pc, 0x22B1);
    }
    #[test]
    fn ordered_ram_handoff_and_common_reload_clobber_old_carrier_with_native_helper_result() {
        let (mut cpu, mut bus) = toy(0, false);
        let suffix = execute_suffix(&mut cpu, &mut bus);
        assert_eq!(suffix.stage.result.status, 0);
        assert!(suffix.accesses.contains(&[0x2261, 0x190, 16, 1, 321]));
        assert!(suffix.accesses.contains(&[0x2259, 0x88, 16, 0, 123]));
        assert!(suffix.accesses.contains(&[0x2259, 0x194, 16, 1, 123]));
        assert!(suffix.accesses.contains(&[0x2266, 0x192, 16, 1, 321]));
        assert!(suffix.accesses.contains(&[0x22A1, 0x3B4, 16, 0, 700]));
        assert!(suffix.accesses.contains(&[0x22A2, 0x7FE, 16, 1, 0x22A5]));
        assert!(suffix.accesses.contains(&[0x599E, 0x7FE, 16, 0, 0x22A5]));
        assert_eq!(state(&cpu, &mut bus).common_words03b6, [2100; 4]);
        assert_eq!(suffix.exit.x1, 0);
        assert_eq!(suffix.exit.accumulator, 2100);
        assert_eq!(suffix.exit.ssp, suffix.entry.ssp);
        assert_eq!(suffix.exit.dp, suffix.entry.dp);
    }
    #[test]
    fn byte_configuration_zero_sets_byte_zero_flag_retains_high_accumulator_and_skips_optional_extent(
    ) {
        let (mut cpu, mut bus) = toy(0, false);
        let suffix = execute_suffix(&mut cpu, &mut bus);
        assert_eq!(suffix.stage.result.program_reads, vec![0x60F8]);
        let load = suffix.stage.events.iter().find(|e| e[0] == 0x226F).unwrap();
        assert_eq!([load[2], load[3]], [0x5AA5, 0x5A00]);
        assert_eq!(load[5] & 0x4000, 0x4000);
        assert_eq!(load[4] & 0x1000, load[5] & 0x1000);
        assert!(suffix
            .stage
            .events
            .iter()
            .any(|e| e[0] == 0x2273 && e[1] == 0x229F));
        assert!(!suffix
            .stage
            .result
            .executed_instruction_bytes
            .as_ref()
            .unwrap()
            .iter()
            .any(|pc| (0x2275..0x229F).contains(pc)));
    }
    #[test]
    fn partial_native_stores_and_mask_survive_unresolved_instruction_without_completed_result() {
        let (mut cpu, mut bus) = toy(0, true);
        let suffix = execute_suffix(&mut cpu, &mut bus);
        assert_eq!(suffix.stage.result.status, 1);
        assert_eq!(suffix.stage.result.stop_pc, 0x2263);
        assert_eq!(
            suffix.stage.writes,
            vec![[0x194, 16, 123], [0x1A, 16, 0x0280], [0x190, 16, 321]]
        );
        let retained = state(&cpu, &mut bus);
        assert_eq!(retained.ie, 0x0280);
        assert_eq!(retained.words019x, [321, 0xA5A5, 123]);
        assert!(cpu.mie());
    }
    #[test]
    fn exact_admission_refuses_other_ie_width_address_mask_and_pswh_bit() {
        for (bytes, dd) in [
            (&[0xC5, 0x1A, 0xD0, 0xA0][..], true),
            (&[0xB5, 0x1C, 0xD0, 0xA0, 2][..], true),
            (&[0xB5, 0x1A, 0xD0, 0xA1, 2][..], true),
            (&[0xA2, 0xD0, 0xFD][..], true),
            (&[0xA2, 0xE0, 2][..], true),
            (&[0xD5, 0x1A][..], false),
            (&[0xE5, 6][..], true),
            (&[0x90, 0x9D, 0xF9, 0x60][..], true),
            (&[0x47, 0x81][..], true),
            (&[0x45, 0x81][..], true),
        ] {
            let d = crate::decoder::decode(dd, |i| bytes.get(i).copied().unwrap_or(0)).unwrap();
            assert_eq!(admission(&d), FormAdmission::Unsupported, "{}", d.mnemonic);
        }
        assert_eq!(post_store_consumer::contract().exit_pcs, vec![0x2259]);
        assert_eq!(post_store::contract().exit_pcs, vec![0x223B]);
    }
    #[test]
    fn invented_ram_read_can_clobber_x1_and_a_without_preserving_old_numeric_influence() {
        let mut rom = vec![0; 5];
        rom[..3].copy_from_slice(&[0xE4, 0x90, 0x50]);
        let mut cpu = Cpu::new();
        cpu.lrb = 0x20;
        cpu.set_psw_u16(0x1101);
        cpu.a = 321;
        let mut bus = Bus::new(rom, 0);
        write_data_u16(&mut cpu, &mut bus, 0x190, 777);
        write_data_u16(&mut cpu, &mut bus, 0x88, 123);
        step(&mut cpu, &mut bus).unwrap();
        step(&mut cpu, &mut bus).unwrap();
        assert_eq!(cpu.a, 777);
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x88), 777);
    }
    #[test]
    fn invented_configuration_alternate_direction_is_only_a_local_instruction_test() {
        // Different-address synthetic branch body. It is not actual-ROM/M2r alternate admission.
        for (config, target) in [(0, 9), (1, 6)] {
            let mut rom = vec![0; 20];
            rom[..6].copy_from_slice(&[0x90, 0x9D, 0x10, 0, 0xC9, 3]);
            rom[16] = config;
            let mut cpu = Cpu::new();
            cpu.a = 0x5500;
            cpu.set_psw_u16(0x1101);
            let mut bus = Bus::new(rom, 0);
            step(&mut cpu, &mut bus).unwrap();
            step(&mut cpu, &mut bus).unwrap();
            assert_eq!(cpu.pc, target);
            assert_eq!(cpu.a, 0x5500 | config as u16);
        }
    }
}
