//! M2l: native producer -> unchanged scaling -> XCHG/VCAL4 -> first software stores.
use crate::{
    acquisition::enter,
    adaptive::Stage,
    decoder::Decoded,
    exec::{read_data_u16, read_data_u8, write_data_u16, write_data_u8},
    fuel, fuel_calculation,
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
    pub factor0158: u16,
    pub source0142: u16,
    pub source0144: u16,
    pub source0146: u16,
    pub source0148: u8,
    pub source0149: u8,
    pub source014a: u16,
    pub source014c: u16,
    pub counter00f2: u8,
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
    pub calls: Vec<Call>,
    pub trace_call_indexes: Vec<u32>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Checkpoint {
    pub index: u32,
    pub status: i32,
    pub input: Option<Call>,
    pub prefix: fuel::Checkpoint,
    pub handoff1350: Option<CpuBoundary>,
    pub host_transition_writes: Vec<[u32; 3]>,
    pub tail_boundaries: Vec<CpuBoundary>,
    pub boundaries: Vec<CpuBoundary>,
    pub stages: Vec<Stage>,
    pub accesses: Vec<[u32; 5]>,
    pub sources_before: Sources,
    pub sources_after: Sources,
    pub mode_before: u8,
    pub mode_after: u8,
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
    pub checkpoints: Vec<Checkpoint>,
}

pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .fuel_additive_correction_chain
        .as_ref()
        .ok_or("M2l stimulus required")?;
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
        return Err("invalid bounded strict M2l request".into());
    }
    Ok(())
}
pub fn contract(stage: usize) -> SliceContract {
    let (entry, exit, code, budget) = match stage {
        0 => (0x2194, 0x21DB, vec![[0x2194, 0x21DB], [0x596C, 0x5991]], 96),
        1 => return fuel_calculation::contract(),
        2 => (0x21F2, 0x2204, vec![[0x21F2, 0x2204], [0x5958, 0x596B]], 48),
        _ => unreachable!(),
    };
    SliceContract {
        entry_pc: entry,
        exit_pcs: vec![exit],
        code_ranges: code,
        psw: 0x0101,
        lrb: 0x20,
        usp: 0x280,
        instruction_budget: budget,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    }
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({
    "id":"fuelAdditiveCorrectionChain","formatVersion":1,"prefixEntries":[0x0A0C,0x0A62,0x12FC],
    "continuousFuelTail":[0x12FC,0x1350],"scriptedHandoff":[0x1350,0x2194],
    "nativeTail":[0x2194,0x2204],"checkpoints":[0x21DB,0x21F2],"lrb":0x20,"psw":0x0101,"usp":0x280,"ssp":0x7FE,
    "hostTransitionWrites":[[2,16,0x20],[4,16,0x0101],[0x8E,16,0x280]],
    "helpers":[[0x596C,0x5991],[0x5958,0x596B]],"vector4":[0x30,0x5958,0x21F5],
    "stackRange":[0x7FE,0x800],"nativeSource":[0x134E,0x140,16],"nativeReader":[0x21DB,0x140,16],
    "softwareStores":[0x03A2,0x03B4],"initialSelectorOnly":true,"gate217A":"StaticPrecondition; bypass NotEvaluated",
    "sourceWords":[0x142,0x144,0x146,0x14A,0x14C,0x158],"sourceBytes":[0x148,0x149,0xF2],
    "source0144Mask":255,"upper0145":"CodeOwnedZero; no recovered high-byte producer",
    "nativeModeMask":[0x12B,8],"traceLimit":8,"assumptions":[],"units":"raw; physical units unknown"})]
}
pub fn admission(d: &Decoded) -> FormAdmission {
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    match (p.mnemonic, p.dd_mode, p.bytes_pat) {
        ("L A, off N8", 'S', ["E4", "N8"])
        | ("LB A, off N8", 'R', ["F4", "N8"])
        | ("JBR off N8.3, rel8", 'U', ["DB", "N8", "rel8"])
        | ("JBR off N8.5, rel8", 'U', ["DD", "N8", "rel8"])
        | ("CMPB N'8, #N8", 'U', ["C5", "N'8", "C0", "N8"])
        | ("MB off N8.3, C", 'U', ["C4", "N8", "3B"])
        | ("ADD A, #N16", '1', ["86", "NL", "NH"])
        | ("ADD A, off N8", '1', ["87", "N8"])
        | ("ADD A, er0", '1', ["08"])
        | ("ADD A, er3", '1', ["0B"])
        | ("JLT rel8", 'U', ["CA", "rel8"])
        | ("JGE rel8", 'U', ["CD", "rel8"])
        | ("SJ rel8", 'U', ["CB", "rel8"])
        | ("L A, #N16", 'S', ["67", "NL", "NH"])
        | ("ST A, er0", '1', ["88"])
        | ("ST A, er3", '1', ["8B"])
        | ("EXTND", 'S', ["F8"])
        | ("MOV er3, off N8", 'U', ["B4", "N8", "4B"])
        | ("CAL addr16", 'U', ["32", "addrl", "addrh"])
        | ("CMP A, #N16", '1', ["C6", "NL", "NH"])
        | ("MOV X2, A", 'U', ["51"])
        | ("ROL A", '1', ["33"])
        | ("ROR A", '1', ["43"])
        | ("MB C, r7.7", 'U', ["27", "2F"])
        | ("RT", 'U', ["01"])
        | ("XCHG A, er3", '1', ["47", "10"])
        | ("VCAL 4", 'U', ["14"])
        | ("CLR A", 'S', ["F9"])
        | ("MOV DP, #N16", 'U', ["62", "NL", "NH"])
        | ("ST A, [DP]", '1', ["D2"])
        | ("L A, er3", 'S', ["37"])
        | ("MOV er0, [DP]", 'U', ["B2", "48"]) => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}
fn sources(cpu: &crate::cpu::Cpu, bus: &mut crate::bus::Bus) -> Sources {
    Sources {
        factor0158: read_data_u16(cpu, bus, 0x158),
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
fn set_sources(cpu: &mut crate::cpu::Cpu, bus: &mut crate::bus::Bus, s: &Sources) {
    for (a, v) in [
        (0x158, s.factor0158),
        (0x142, s.source0142),
        (0x144, s.source0144),
        (0x146, s.source0146),
        (0x14A, s.source014a),
        (0x14C, s.source014c),
    ] {
        write_data_u16(cpu, bus, a, v)
    }
    for (a, v) in [
        (0x148, s.source0148),
        (0x149, s.source0149),
        (0xF2, s.counter00f2),
    ] {
        write_data_u8(cpu, bus, a, v)
    }
}
pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r
        .fuel_additive_correction_chain
        .as_ref()
        .expect("validated");
    let mut sequences = vec![];
    for &pattern in &r.scratch_patterns {
        let (mut cpu, mut bus) =
            seed_machine(&r.images[0].rom, &fuel::contract("rpmAxes"), pattern);
        cpu.ssp = 0x7FE;
        fuel::seed_state(&mut cpu, &mut bus, &s.initial_state);
        write_data_u8(&mut cpu, &mut bus, 0x124, s.caller_gate0124);
        write_data_u8(&mut cpu, &mut bus, 0x12B, s.mode012b);
        // Source snapshots start at a code-owned zero only; native carriers retain scratch canaries.
        let zero = Sources {
            factor0158: 0,
            source0142: 0,
            source0144: 0,
            source0146: 0,
            source0148: 0,
            source0149: 0,
            source014a: 0,
            source014c: 0,
            counter00f2: 0,
        };
        set_sources(&mut cpu, &mut bus, &zero);
        let mut prefix_ranges = fuel::data_ranges();
        prefix_ranges.extend([
            [0x124, 0x125],
            [0x12B, 0x12C],
            [0x142, 0x14E],
            [0x158, 0x15A],
            [0xF2, 0xF3],
            [0x3A2, 0x3A4],
            [0x3B4, 0x3B6],
        ]);
        bus.configure_scoped_access(prefix_ranges.clone(), 4096);
        let mut stopped = false;
        let mut checkpoints = vec![];
        for c in &s.calls {
            // Observation scope changes do not seed or reset machine state.
            bus.configure_scoped_access(prefix_ranges.clone(), 4096);
            let before = fuel::state(&cpu, &mut bus);
            let initial_sources = sources(&cpu, &mut bus);
            let mode = read_data_u8(&cpu, &mut bus, 0x12B);
            let stores = [
                read_data_u16(&cpu, &mut bus, 0x3A2),
                read_data_u16(&cpu, &mut bus, 0x3B4),
            ];
            let mut row = Checkpoint {
                index: c.index,
                status: 4,
                input: None,
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
                handoff1350: None,
                host_transition_writes: vec![],
                tail_boundaries: vec![],
                boundaries: vec![],
                stages: vec![],
                accesses: vec![],
                sources_before: initial_sources.clone(),
                sources_after: initial_sources,
                mode_before: mode,
                mode_after: mode,
                stores_before: stores,
                stores_after: stores,
                correction: None,
                component: None,
                corrected: None,
                store03a2: None,
                store03b4: None,
            };
            if !stopped {
                row.input = Some(c.clone());
                bus.configure_scoped_access(prefix_ranges.clone(), 4096);
                for (a, v) in [
                    (0x238, c.raw_map0_rpm),
                    (0xC2, c.raw_map1_rpm),
                    (0xBF, c.raw_load),
                ] {
                    write_data_u8(&mut cpu, &mut bus, a, v)
                }
                set_sources(&mut cpu, &mut bus, &c.sources);
                row.prefix.state_after_inputs = Some(fuel::state(&cpu, &mut bus));
                fuel_calculation::execute_prefix(
                    &mut cpu,
                    &mut bus,
                    &mut row.prefix,
                    &mut row.accesses,
                    &mut row.tail_boundaries,
                );
                row.prefix.state_after = fuel::state(&cpu, &mut bus);
                row.status = row.prefix.status;
                if row.status == 0 {
                    row.prefix.consumer_output = Some(read_data_u16(&cpu, &mut bus, 0x140));
                    row.handoff1350 = Some(boundary(&cpu, &mut bus));
                    // The sole downstream scripted entry. Never enter again at21DB or21F2.
                    enter(&mut cpu, &mut bus, &contract(0));
                    row.host_transition_writes =
                        vec![[2, 16, 0x20], [4, 16, 0x0101], [0x8E, 16, 0x280]];
                    // Tight tail-only footprint, especially the single two-byte native near-call stack slot.
                    bus.configure_scoped_access(
                        vec![
                            [0, 8],
                            [0x88, 0x90],
                            [0x100, 0x108],
                            [0x124, 0x125],
                            [0x12B, 0x12C],
                            [0xF2, 0xF3],
                            [0x140, 0x14E],
                            [0x158, 0x15A],
                            [0x3A2, 0x3A4],
                            [0x3B4, 0x3B6],
                            [0x7FE, 0x800],
                        ],
                        4096,
                    );
                    for n in 0..3 {
                        row.boundaries.push(boundary(&cpu, &mut bus));
                        bus.clear_program_reads();
                        bus.set_program_data_ranges(if n == 2 {
                            vec![[0x30, 0x32]]
                        } else {
                            vec![]
                        });
                        bus.begin_native_accesses();
                        bus.begin_write_journal();
                        bus.start_decision_observer();
                        let result = execute_in_state_observed(
                            &mut cpu,
                            &mut bus,
                            &contract(n),
                            &[],
                            true,
                            Some(if n == 1 {
                                fuel_calculation::admission
                            } else {
                                admission
                            }),
                            true,
                        );
                        row.accesses.extend(bus.end_native_accesses());
                        row.status = result.status;
                        row.stages.push(Stage {
                            result,
                            writes: bus.end_write_journal(),
                            events: bus.finish_decision_observer(),
                            ssp_after: cpu.ssp,
                        });
                        row.boundaries.push(boundary(&cpu, &mut bus));
                        if row.status != 0 {
                            break;
                        }
                        match n {
                            0 => row.correction = Some(read_data_u16(&cpu, &mut bus, 0x106)),
                            1 => row.component = Some(read_data_u16(&cpu, &mut bus, 0x104)),
                            _ => {
                                row.corrected = Some(read_data_u16(&cpu, &mut bus, 0x106));
                                row.store03a2 = Some(read_data_u16(&cpu, &mut bus, 0x3A2));
                                row.store03b4 = Some(read_data_u16(&cpu, &mut bus, 0x3B4));
                            }
                        }
                    }
                }
                row.sources_after = sources(&cpu, &mut bus);
                row.mode_after = read_data_u8(&cpu, &mut bus, 0x12B);
                row.stores_after = [
                    read_data_u16(&cpu, &mut bus, 0x3A2),
                    read_data_u16(&cpu, &mut bus, 0x3B4),
                ];
                stopped = row.status != 0;
            }
            checkpoints.push(row);
        }
        sequences.push(Sequence {
            scratch_pattern: pattern,
            caller_gate0124: s.caller_gate0124,
            checkpoints,
        });
    }
    response.entry_contracts = entry_contracts();
    response.fuel_additive_sequences = Some(sequences);
    Ok(response)
}
