//! M2m: native0158 production and same-machine downstream consumption.
use crate::{
    acquisition::enter_with_observer,
    adaptive::Stage,
    bus::Bus,
    cpu::Cpu,
    decoder::Decoded,
    exec::{read_data_u16, read_data_u8, write_data_u16, write_data_u8},
    fuel, fuel_additive, fuel_calculation,
    full_decoder::FULL_OPCODES,
    instruction_forms::FormAdmission,
    protocol::{Request, Response},
    runner::{execute_in_state_observed, seed_machine, SliceContract},
    vtec_fuel::{boundary, CpuBoundary},
};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Sources {
    pub source015a: u16,
    pub source015c: u16,
    pub source015e: u8,
    pub source0160: u16,
    pub source0162: u16,
    pub source0164: u8,
    pub source0165: u8,
    pub source0166: u8,
    pub source0167: u8,
    pub source0168: u8,
    pub source0133: u8,
    pub source0142: u16,
    pub source0144: u16,
    pub source0146: u16,
    pub source0148: u8,
    pub source0149: u8,
    pub source014a: u16,
    pub source014c: u16,
    pub counter00f2: u8,
}
impl Sources {
    fn correction(&self) -> fuel_additive::CorrectionSources {
        fuel_additive::CorrectionSources {
            words: [
                self.source0142,
                self.source0144,
                self.source0146,
                self.source014a,
                self.source014c,
            ],
            bytes: [self.source0148, self.source0149, self.counter00f2],
        }
    }
    pub(crate) fn zero() -> Self {
        Self {
            source015a: 0,
            source015c: 0,
            source015e: 0,
            source0160: 0,
            source0162: 0,
            source0164: 0,
            source0165: 0,
            source0166: 0,
            source0167: 0,
            source0168: 0,
            source0133: 0,
            source0142: 0,
            source0144: 0,
            source0146: 0,
            source0148: 0,
            source0149: 0,
            source014a: 0,
            source014c: 0,
            counter00f2: 0,
        }
    }
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Call {
    pub index: u32,
    pub raw_load: u8,
    pub raw_map0_rpm: u8,
    pub raw_map1_rpm: u8,
    pub sources: Sources,
}
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Stimulus {
    pub format_version: u32,
    pub initial_state: fuel::State,
    pub caller_gate0124: u8,
    pub mode012b: u8,
    pub producer_mode012c: u8,
    pub producer_selector012f: u8,
    pub hysteresis0130: u8,
    pub calls: Vec<Call>,
    pub trace_call_indexes: Vec<u32>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Checkpoint {
    pub index: u32,
    pub status: i32,
    pub input: Option<Call>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub caller_gate: Option<Stage>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub caller_entry: Option<CpuBoundary>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub caller_exit: Option<CpuBoundary>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub prefix_transitions: Option<Vec<fuel_calculation::PrefixTransition>>,
    pub prefix: fuel::Checkpoint,
    pub tail_boundaries: Vec<CpuBoundary>,
    pub handoff1350: Option<CpuBoundary>,
    pub factor_entry: Option<CpuBoundary>,
    pub factor_stage: Option<Stage>,
    pub factor_exit: Option<CpuBoundary>,
    pub transition_to_factor_writes: Vec<[u32; 3]>,
    pub transition_to_additive_writes: Vec<[u32; 3]>,
    pub boundaries: Vec<CpuBoundary>,
    pub stages: Vec<Stage>,
    pub accesses: Vec<[u32; 5]>,
    pub input_writes: Vec<[u32; 3]>,
    pub sources_before: Sources,
    pub sources_after: Sources,
    pub factor0158_before: u16,
    pub factor0158_after: u16,
    pub native_factor0158: Option<u16>,
    pub factor_provenance: &'static str,
    pub mode_before: u8,
    pub mode_after: u8,
    pub hysteresis_before: u8,
    pub hysteresis_after: u8,
    pub stores_before: [u16; 2],
    pub stores_after: [u16; 2],
    pub correction: Option<u16>,
    pub component: Option<u16>,
    pub corrected: Option<u16>,
    pub store03a2: Option<u16>,
    pub store03b4: Option<u16>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Sequence {
    pub scratch_pattern: u8,
    pub caller_gate0124: u8,
    pub producer_mode012c: u8,
    pub producer_selector012f: u8,
    pub checkpoints: Vec<Checkpoint>,
}
pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .fuel_factor_production_chain
        .as_ref()
        .ok_or("M2m stimulus required")?;
    if s.format_version != 1
        || s.calls.is_empty()
        || s.calls.len() > 64
        || s.trace_call_indexes.len() > 8
        || s.trace_call_indexes
            .iter()
            .any(|i| *i as usize >= s.calls.len())
        || s.trace_call_indexes
            .iter()
            .collect::<std::collections::HashSet<_>>()
            .len()
            != s.trace_call_indexes.len()
        || s.calls
            .iter()
            .enumerate()
            .any(|(i, c)| c.index as usize != i || c.sources.source0144 > 255)
        || s.initial_state.load_index > 8
        || s.initial_state.map0_rpm_index > 18
        || s.initial_state.map1_rpm_index > 18
        || s.initial_state.consumer_output0140 != 0
        || s.caller_gate0124 & 0x10 != 0
        || r.images.len() != 1
        || r.images[0].id != "baseline"
        || r.images[0].rom.len() != 32768
        || r.images[0].rom[0x60E5] != 0
        || r.images[0].rom[0x60F8] != 0
        || r.scratch_patterns != [0, 85, 170]
        || !r.allow_assumptions.is_empty()
        || r.synthetic.is_some()
        || r.producer_cases.is_some()
    {
        return Err("invalid bounded strict M2m request".into());
    }
    Ok(())
}
pub fn contract() -> SliceContract {
    SliceContract {
        entry_pc: 0x1F43,
        exit_pcs: vec![0x1FB7],
        code_ranges: vec![[0x1F43, 0x1FB7], [0x7A99, 0x7AAB]],
        psw: 0x0101,
        lrb: 0x20,
        usp: 0x280,
        instruction_budget: 128,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    }
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({
        "id":"fuelFactorProductionChain","formatVersion":1,"prefixEntries":[0x0A0C,0x0A62,0x12FC],
        "continuousFuelTail":[0x12FC,0x1350],"scriptedHandoffs":[[0x1350,0x1F43],[0x1FB7,0x2194]],
        "nativeFactorTail":[0x1F43,0x1FB7],"factorCodeRanges":[[0x1F43,0x1FB7],[0x7A99,0x7AAB]],
        "factorDetours":[[0x1FB4,0x7A99],[0x7AA8,0x1FB7]],"factorBudget":128,
        "nativeAdditiveTail":[0x2194,0x2204],"checkpoints":[0x21DB,0x21F2],
        "lrb":0x20,"psw":0x0101,"usp":0x280,"ssp":0x7FE,
        "hostTransitionWrites":[[2,16,0x20],[4,16,0x0101],[0x8E,16,0x280]],
        "factorSourceWords":[0x15A,0x15C,0x160,0x162],
        "factorSourceBytes":[0x15E,0x164,0x165,0x166,0x167,0x168,0x133],
        "upper015f":"CodeOwnedZeroOnce; no recovered high-byte producer",
        "initial0158":"CodeOwnedDiagnosticScratchWord; never an input or produced value",
        "producerModeMask":[0x12C,16],"producerSelectorMask":[0x12F,128],"nativeHysteresisMask":[0x130,64],
        "source0144Mask":255,"upper0145":"CodeOwnedZero; no recovered high-byte producer",
        "nativeModeMask":[0x12B,8],"gate217A":"StaticPrecondition; bypass NotEvaluated",
        "nativeSources":[[0x134E,0x140,16],[0x7A99,0x158,16]],
        "nativeReaders":[[0x21DB,0x140,16],[0x21DD,0x158,16]],
        "softwareStores":[0x3A2,0x3B4],"helpers":[[0x596C,0x5991],[0x5958,0x596B]],
        "vector4":[0x30,0x5958,0x21F5],"stackRange":[0x7FE,0x800],
        "initialSelectorOnly":true,"holdPaths":"None in supported closed producer",
        "traceLimit":8,"assumptions":[],"units":"raw; physical units unknown"})]
}
pub fn admission(d: &Decoded) -> FormAdmission {
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    match (p.mnemonic, p.dd_mode, p.bytes_pat) {
        ("LB A, off N8", 'R', ["F4", "N8"])
        | ("JBS off N8.7, rel8", 'U', ["EF", "N8", "rel8"])
        | ("STB A, r1", '0', ["89"])
        | ("CLRB r0", 'U', ["20", "15"])
        | ("SRL er0", 'U', ["44", "E7"])
        | ("JEQ rel8", 'U', ["C9", "rel8"])
        | ("CLRB A", 'R', ["FA"])
        | ("MUL", 'U', ["90", "35"])
        | ("MOV er0, er1", 'U', ["45", "48"])
        | ("MOVB r1, r2", 'U', ["22", "49"])
        | ("L A, off N8", 'S', ["E4", "N8"])
        | ("SRL er1", 'U', ["45", "E7"])
        | ("ROR A", '1', ["43"])
        | ("LB A, r3", 'R', ["7B"])
        | ("MOV er0, #N16", 'U', ["44", "98", "NL", "NH"])
        | ("JBR off N8.4, rel8", 'U', ["DC", "N8", "rel8"])
        | ("SLL A", '1', ["53"])
        | ("ROL er0", 'U', ["44", "B7"])
        | ("JLT rel8", 'U', ["CA", "rel8"])
        | ("JGE rel8", 'U', ["CD", "rel8"])
        | ("J addr16", 'U', ["03", "addrl", "addrh"])
        | ("MOV off N8, er1", 'U', ["45", "7C", "N8"])
        | ("LB A, #N8", 'R', ["77", "N8"])
        | ("JBS off N8.6, rel8", 'U', ["EE", "N8", "rel8"])
        | ("CMPB A, off N8", '0', ["C7", "N8"])
        | ("MB off N8.6, C", 'U', ["C4", "N8", "3E"]) => FormAdmission::Allowed,
        ("STB A, N8", '0', ["D5", "N8"]) if d.fields.n8 == 7 => FormAdmission::Allowed,
        ("MOVB N'8, #N8", 'U', ["C5", "N'8", "98", "N8"]) if d.fields.n8_alt == 7 => {
            FormAdmission::Allowed
        }
        ("MOVB r0, N8", 'U', ["C5", "N8", "48"]) if d.fields.n8 == 7 => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}
pub(crate) fn set_sources(cpu: &mut Cpu, bus: &mut Bus, s: &Sources) {
    for (a, v) in [
        (0x15A, s.source015a),
        (0x15C, s.source015c),
        (0x160, s.source0160),
        (0x162, s.source0162),
    ] {
        write_data_u16(cpu, bus, a, v);
    }
    for (a, v) in [
        (0x15E, s.source015e),
        (0x164, s.source0164),
        (0x165, s.source0165),
        (0x166, s.source0166),
        (0x167, s.source0167),
        (0x168, s.source0168),
        (0x133, s.source0133),
    ] {
        write_data_u8(cpu, bus, a, v);
    }
    fuel_additive::set_correction_sources(cpu, bus, &s.correction());
}
fn sources(cpu: &Cpu, bus: &mut Bus) -> Sources {
    Sources {
        source015a: read_data_u16(cpu, bus, 0x15A),
        source015c: read_data_u16(cpu, bus, 0x15C),
        source015e: read_data_u8(cpu, bus, 0x15E),
        source0160: read_data_u16(cpu, bus, 0x160),
        source0162: read_data_u16(cpu, bus, 0x162),
        source0164: read_data_u8(cpu, bus, 0x164),
        source0165: read_data_u8(cpu, bus, 0x165),
        source0166: read_data_u8(cpu, bus, 0x166),
        source0167: read_data_u8(cpu, bus, 0x167),
        source0168: read_data_u8(cpu, bus, 0x168),
        source0133: read_data_u8(cpu, bus, 0x133),
        source0142: read_data_u16(cpu, bus, 0x142),
        source0144: read_data_u16(cpu, bus, 0x144),
        source0146: read_data_u16(cpu, bus, 0x146),
        source0148: read_data_u8(cpu, bus, 0x148),
        source0149: read_data_u8(cpu, bus, 0x149),
        source014a: read_data_u16(cpu, bus, 0x14A),
        source014c: read_data_u16(cpu, bus, 0x14C),
        counter00f2: read_data_u8(cpu, bus, 0xF2),
    }
}
fn stores(cpu: &Cpu, bus: &mut Bus) -> [u16; 2] {
    [
        read_data_u16(cpu, bus, 0x3A2),
        read_data_u16(cpu, bus, 0x3B4),
    ]
}
pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r.fuel_factor_production_chain.as_ref().expect("validated");
    let mut sequences = vec![];
    for &pattern in &r.scratch_patterns {
        let (mut cpu, mut bus) =
            seed_machine(&r.images[0].rom, &fuel::contract("rpmAxes"), pattern);
        cpu.ssp = 0x7FE;
        fuel::seed_state(&mut cpu, &mut bus, &s.initial_state);
        for (a, v) in [
            (0x124, s.caller_gate0124),
            (0x12B, s.mode012b),
            (0x12C, s.producer_mode012c),
            (0x12F, s.producer_selector012f),
            (0x130, s.hysteresis0130),
            (0x15F, 0),
        ] {
            write_data_u8(&mut cpu, &mut bus, a, v);
        }
        // 0158 is deliberately untouched: its scratch word is diagnostic, never a ready factor.
        set_sources(&mut cpu, &mut bus, &Sources::zero());
        let mut ranges = fuel::data_ranges();
        ranges.extend([
            [0x124, 0x125],
            [0x12B, 0x12D],
            [0x12F, 0x131],
            [0x133, 0x134],
            [0x142, 0x14E],
            [0x158, 0x169],
            [0xF2, 0xF3],
            [0x3A2, 0x3A4],
            [0x3B4, 0x3B6],
        ]);
        let mut stopped = false;
        let mut checkpoints = vec![];
        for c in &s.calls {
            bus.configure_scoped_access(ranges.clone(), 4096);
            let mut row = checkpoint(&cpu, &mut bus, c);
            if !stopped {
                apply_inputs(&mut cpu, &mut bus, c, &mut row);
                execute_checkpoint(&mut cpu, &mut bus, &mut row, false);
                finish_checkpoint(&cpu, &mut bus, &mut row);
                stopped = row.status != 0;
            }
            checkpoints.push(row);
        }
        sequences.push(Sequence {
            scratch_pattern: pattern,
            caller_gate0124: s.caller_gate0124,
            producer_mode012c: s.producer_mode012c,
            producer_selector012f: s.producer_selector012f,
            checkpoints,
        });
    }
    response.entry_contracts = entry_contracts();
    response.fuel_factor_sequences = Some(sequences);
    Ok(response)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn native_factor_word_store_high_byte_fault_preserves_only_completed_low_byte() {
        // One independent instruction, not a copied OEM producer program.
        let mut rom = vec![0u8; 32768];
        rom[0x7A99..0x7A9C].copy_from_slice(&[0x45, 0x7C, 0x58]);
        let mut bus = Bus::new(rom, 0xA5);
        let mut cpu = Cpu::new();
        cpu.pc = 0x7A99;
        cpu.lrb = 0x20;
        write_data_u16(&mut cpu, &mut bus, 0x102, 0xBEEF);
        bus.configure_scoped_access(vec![[0x102, 0x104], [0x158, 0x159]], 128);
        bus.begin_native_accesses();
        bus.begin_write_journal();
        bus.start_decision_observer();
        let result = execute_in_state_observed(
            &mut cpu,
            &mut bus,
            &contract(),
            &[],
            true,
            Some(admission),
            true,
        );
        assert_eq!(result.status, 2);
        assert_eq!(bus.end_write_journal(), vec![[0x158, 8, 0xEF]]);
        let accesses = bus.end_native_accesses();
        assert!(accesses.contains(&[0x7A99, 0x158, 8, 1, 0xEF]));
        assert!(!accesses
            .iter()
            .any(|a| a[1] == 0x158 && a[2] == 16 && a[3] == 1));
        bus.configure_scoped_access(vec![[0x158, 0x15A]], 128);
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x158), 0xA5EF);
        assert!(bus
            .finish_decision_observer()
            .iter()
            .all(|e| e[0] != 0x21DD));
    }

    #[test]
    fn actual_entry_observer_records_cpu_alias_writer_values_and_dynamic_usp_address() {
        let mut cpu = Cpu::new();
        let mut bus = Bus::new(vec![], 0xA5);
        let mut c = contract();
        c.psw = 0x0102;
        c.lrb = 0x41;
        c.usp = 0x345;
        let mut writes = vec![];
        enter_with_observer(&mut cpu, &mut bus, &c, |w| writes.push(w));
        assert_eq!(
            writes,
            vec![[2, 16, 0x41], [4, 16, 0x0102], [0x96, 16, 0x345]]
        );
        assert_eq!(cpu.lrb, 0x41);
        assert_eq!(cpu.scb(), 2);
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x96), 0x345);
    }
}

pub(crate) fn data_ranges() -> Vec<[u16; 2]> {
    let mut ranges = fuel::data_ranges();
    ranges.extend([
        [0x124, 0x125],
        [0x12B, 0x12D],
        [0x12F, 0x131],
        [0x133, 0x134],
        [0x142, 0x14E],
        [0x158, 0x169],
        [0xF2, 0xF3],
        [0x3A2, 0x3A4],
        [0x3B4, 0x3B6],
    ]);
    ranges
}
pub(crate) fn checkpoint(cpu: &Cpu, bus: &mut Bus, c: &Call) -> Checkpoint {
    let before = fuel::state(cpu, bus);
    let initial_sources = sources(cpu, bus);
    let factor = read_data_u16(cpu, bus, 0x158);
    let mode = read_data_u8(cpu, bus, 0x12B);
    let hysteresis = read_data_u8(cpu, bus, 0x130);
    let old_stores = stores(cpu, bus);
    let row = Checkpoint {
        index: c.index,
        status: 4,
        input: None,
        caller_gate: None,
        caller_entry: None,
        caller_exit: None,
        prefix_transitions: None,
        prefix: fuel::Checkpoint {
            index: c.index,
            status: 4,
            state_before: before.clone(),
            state_after_inputs: None,
            state_after: before,
            rpm_axes: None,
            load_axis: None,
            selection: None,
            lookup: None,
            consumer: None,
            selected_origin: None,
            position: None,
            lookup_result: None,
            consumer_output: None,
        },
        tail_boundaries: vec![],
        handoff1350: None,
        factor_entry: None,
        factor_stage: None,
        factor_exit: None,
        transition_to_factor_writes: vec![],
        transition_to_additive_writes: vec![],
        boundaries: vec![],
        stages: vec![],
        accesses: vec![],
        input_writes: vec![],
        sources_before: initial_sources.clone(),
        sources_after: initial_sources,
        factor0158_before: factor,
        factor0158_after: factor,
        native_factor0158: None,
        factor_provenance: "NotRun",
        mode_before: mode,
        mode_after: mode,
        hysteresis_before: hysteresis,
        hysteresis_after: hysteresis,
        stores_before: old_stores,
        stores_after: old_stores,
        correction: None,
        component: None,
        corrected: None,
        store03a2: None,
        store03b4: None,
    };

    row
}
pub(crate) fn apply_inputs(cpu: &mut Cpu, bus: &mut Bus, c: &Call, row: &mut Checkpoint) {
    row.input = Some(c.clone());
    bus.begin_write_journal();
    for (a, v) in [
        (0x238, c.raw_map0_rpm),
        (0xC2, c.raw_map1_rpm),
        (0xBF, c.raw_load),
    ] {
        write_data_u8(cpu, bus, a, v);
    }
    set_sources(cpu, bus, &c.sources);
    row.input_writes = bus.end_write_journal();
    row.prefix.state_after_inputs = Some(fuel::state(cpu, bus));
}
pub(crate) fn caller_contract() -> SliceContract {
    let mut c = fuel_additive::contract(0);
    c.entry_pc = 0x217A;
    c.exit_pcs = vec![0x2194];
    c.code_ranges = vec![[0x217A, 0x217D]];
    c.instruction_budget = 1;
    c
}
fn additive_entry(gate217a: bool) -> SliceContract {
    if gate217a {
        caller_contract()
    } else {
        fuel_additive::contract(0)
    }
}
/// Execute on the caller's one persistent machine. Does not initialize or apply sources.
pub(crate) fn execute_checkpoint(
    cpu: &mut Cpu,
    bus: &mut Bus,
    row: &mut Checkpoint,
    gate217a: bool,
) {
    fuel_calculation::execute_prefix_observed(
        cpu,
        bus,
        &mut row.prefix,
        &mut row.accesses,
        &mut row.tail_boundaries,
        row.prefix_transitions.as_mut(),
    );
    row.prefix.state_after = fuel::state(cpu, bus);
    row.status = row.prefix.status;
    if row.status == 0 {
        row.prefix.consumer_output = Some(read_data_u16(cpu, bus, 0x140));
        row.handoff1350 = Some(boundary(cpu, bus));
        enter_with_observer(cpu, bus, &contract(), |w| {
            row.transition_to_factor_writes.push(w)
        });
        bus.configure_scoped_access(
            vec![
                [0, 8],
                [0x88, 0x90],
                [0x100, 0x108],
                [0x12C, 0x12D],
                [0x12F, 0x131],
                [0x133, 0x134],
                [0x158, 0x169],
            ],
            4096,
        );
        row.factor_entry = Some(boundary(cpu, bus));
        bus.clear_program_reads();
        bus.set_program_data_ranges(vec![]);
        bus.begin_native_accesses();
        bus.begin_write_journal();
        bus.start_decision_observer();
        let mut result =
            execute_in_state_observed(cpu, bus, &contract(), &[], true, Some(admission), true);
        let factor_accesses = bus.end_native_accesses();
        let generation = factor_accesses
            .iter()
            .any(|a| a[0] == 0x7A99 && a[1] == 0x158 && a[2] == 16 && a[3] == 1);
        row.accesses.extend(factor_accesses);
        if result.status == 0 && !generation {
            result.status = 2;
            result.error =
                Some("closed producer reached exit without native word store7A99".into());
        }
        row.status = result.status;
        let writes = bus.end_write_journal();
        if writes
            .iter()
            .any(|w| w[0] < 0x15A && w[0] + w[1] / 8 > 0x158)
        {
            row.factor_provenance = "PartialWritten";
        }
        row.factor_stage = Some(Stage {
            result,
            writes,
            events: bus.finish_decision_observer(),
            ssp_after: cpu.ssp,
        });
        row.factor_exit = Some(boundary(cpu, bus));
        if row.status == 0 {
            row.native_factor0158 = Some(read_data_u16(cpu, bus, 0x158));
            row.factor_provenance = "Written";
            enter_with_observer(cpu, bus, &additive_entry(gate217a), |w| {
                row.transition_to_additive_writes.push(w)
            });
            if gate217a {
                bus.configure_scoped_access(data_ranges(), 4096);
                row.caller_entry = Some(boundary(cpu, bus));
                bus.clear_program_reads();
                bus.set_program_data_ranges(vec![]);
                bus.begin_native_accesses();
                bus.begin_write_journal();
                bus.start_decision_observer();
                let gate = execute_in_state_observed(
                    cpu,
                    bus,
                    &caller_contract(),
                    &[],
                    true,
                    Some(admission),
                    true,
                );
                row.accesses.extend(bus.end_native_accesses());
                row.status = gate.status;
                row.caller_gate = Some(Stage {
                    result: gate,
                    writes: bus.end_write_journal(),
                    events: bus.finish_decision_observer(),
                    ssp_after: cpu.ssp,
                });
                row.caller_exit = Some(boundary(cpu, bus));
            }
            if row.status != 0 {
                return;
            }
            let tail = fuel_additive::execute_tail(cpu, bus);
            row.accesses.extend(tail.accesses);
            row.status = tail.status;
            row.boundaries = tail.boundaries;
            row.stages = tail.stages;
            row.correction = tail.correction;
            row.component = tail.component;
            row.corrected = tail.corrected;
            row.store03a2 = tail.store03a2;
            row.store03b4 = tail.store03b4;
        }
    }
}
pub(crate) fn finish_checkpoint(cpu: &Cpu, bus: &mut Bus, row: &mut Checkpoint) {
    bus.configure_scoped_access(data_ranges(), 4096);
    row.sources_after = sources(cpu, bus);
    row.factor0158_after = read_data_u16(cpu, bus, 0x158);
    row.mode_after = read_data_u8(cpu, bus, 0x12B);
    row.hysteresis_after = read_data_u8(cpu, bus, 0x130);
    row.stores_after = stores(cpu, bus);
}
