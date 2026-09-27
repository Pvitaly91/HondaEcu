//! M2k: isolated strict fuel prefix, explicit same-machine numeric handoff.
use crate::{
    acquisition::{enter, enter_with_observer},
    adaptive::Stage,
    decoder::Decoded,
    exec::{read_data_u16, write_data_u16, write_data_u8},
    fuel,
    full_decoder::FULL_OPCODES,
    instruction_forms::FormAdmission,
    protocol::{Request, Response},
    runner::{execute_in_state_observed, seed_machine, SliceContract},
    vtec_fuel::{boundary, CpuBoundary},
};
use serde::{Deserialize, Serialize};

// Shared native prefix body only. No new host initialization; old M2k format and bounds remain unchanged.
pub(crate) fn execute_prefix(
    cpu: &mut crate::cpu::Cpu,
    bus: &mut crate::bus::Bus,
    prefix: &mut fuel::Checkpoint,
    accesses: &mut Vec<[u32; 5]>,
    tail_boundaries: &mut Vec<CpuBoundary>,
) {
    execute_prefix_observed(cpu, bus, prefix, accesses, tail_boundaries, None);
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct PrefixTransition {
    pub before: CpuBoundary,
    pub after: CpuBoundary,
    pub writes: Vec<[u32; 3]>,
}
pub(crate) fn execute_prefix_observed(
    cpu: &mut crate::cpu::Cpu,
    bus: &mut crate::bus::Bus,
    prefix: &mut fuel::Checkpoint,
    accesses: &mut Vec<[u32; 5]>,
    tail_boundaries: &mut Vec<CpuBoundary>,
    mut transitions: Option<&mut Vec<PrefixTransition>>,
) {
    // Never call the old top-level fuel task: no per-event selector write.
    for (name, scripted) in [
        ("rpmAxes", true),
        ("loadAxis", true),
        ("selection", true),
        ("lookup", false),
        ("consumer", false),
    ] {
        if !scripted {
            tail_boundaries.push(boundary(cpu, bus));
        }
        if name == "lookup" {
            prefix.selected_origin = Some(read_data_u16(cpu, bus, 0x88));
            prefix.position = Some(fuel::Position {
                load_index: crate::exec::read_data_u8(cpu, bus, 0x102),
                rpm_index: crate::exec::read_data_u8(cpu, bus, 0x103),
                load_fraction: read_data_u16(cpu, bus, 0x8A),
                rpm_fraction: read_data_u16(cpu, bus, 0x106),
            });
        }
        if name == "consumer" {
            prefix.lookup_result = Some(read_data_u16(cpu, bus, 0x104));
        }
        // Scripted ABI is applied before observation. Never filter a
        // native access out of the journal, including USP or aliases.
        if scripted {
            if let Some(ref mut list) = transitions {
                let before = boundary(cpu, bus);
                let mut writes = vec![];
                enter_with_observer(cpu, bus, &fuel::contract(name), |w| writes.push(w));
                list.push(PrefixTransition {
                    before,
                    after: boundary(cpu, bus),
                    writes,
                });
            } else {
                enter(cpu, bus, &fuel::contract(name));
            }
        }
        bus.begin_native_accesses();
        let stage = fuel::execute(cpu, bus, name, false);
        accesses.extend(bus.end_native_accesses());
        prefix.status = stage.result.status;
        if matches!(name, "selection" | "lookup" | "consumer") {
            tail_boundaries.push(boundary(cpu, bus));
        }
        match name {
            "rpmAxes" => prefix.rpm_axes = Some(stage),
            "loadAxis" => prefix.load_axis = Some(stage),
            "selection" => prefix.selection = Some(stage),
            "lookup" => prefix.lookup = Some(stage),
            _ => prefix.consumer = Some(stage),
        }
        if prefix.status != 0 {
            break;
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
    pub factor0158: u16,
}
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Stimulus {
    pub format_version: u32,
    pub initial_state: fuel::State,
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
    pub downstream_entry: Option<CpuBoundary>,
    pub downstream: Option<Stage>,
    pub downstream_exit: Option<CpuBoundary>,
    pub accesses: Vec<[u32; 5]>,
    pub host_transition_writes: Vec<[u32; 3]>,
    pub tail_boundaries: Vec<CpuBoundary>,
    pub factor0158_before: u16,
    pub factor0158_after: u16,
    pub output: Option<u16>,
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
        .fuel_calculation_chain
        .as_ref()
        .ok_or("fuel calculation stimulus required")?;
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
            .any(|(i, c)| c.index as usize != i)
        || s.initial_state.load_index > 8
        || s.initial_state.map0_rpm_index > 18
        || s.initial_state.map1_rpm_index > 18
        || s.initial_state.consumer_output0140 != 0
        || r.images.len() != 1
        || r.images[0].id != "baseline"
        || r.images[0].rom.len() != 32768
        || r.images[0].rom[0x60E5] != 0
        || r.scratch_patterns != [0, 85, 170]
        || !r.allow_assumptions.is_empty()
        || r.synthetic.is_some()
        || r.producer_cases.is_some()
    {
        return Err("invalid bounded strict fuel calculation request".into());
    }
    Ok(())
}
pub fn contract() -> SliceContract {
    SliceContract {
        entry_pc: 0x21DB,
        exit_pcs: vec![0x21F2],
        code_ranges: vec![[0x21DB, 0x21F2]],
        psw: 0x0101,
        lrb: 0x20,
        usp: 0x280,
        instruction_budget: 32,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    }
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![
        serde_json::json!({"id":"fuelCalculationChain","formatVersion":1,
        "prefixEntries":[0x0A0C,0x0A62,0x12FC],"continuousFuelTail":[0x12FC,0x1350],
        "scriptedHandoff":[0x1350,0x21DB],"downstreamExit":0x21F2,"lrb":0x20,"psw":0x0101,"usp":0x280,"ssp":0x7FE,
        "hostTransitionWrites":[[2,16,0x20],[4,16,0x0101],[0x8E,16,0x280]],
        "nativeSource":[0x134E,0x140,16],"nativeReader":[0x21DB,0x140,16],
        "externalOperand":[0x158,16],"nativeResult":[0x21F1,0x104,16],"staticReader":0x227A,
        "initialSelectorOnly":true,"fixedInitialCallerGate":{"address":0x124,"clearMask":0x10,"execution":"StaticCompatibilityOnly"},
        "perEventInputs":[0x238,0xC2,0xBF,0x158],"traceLimit":8,
        "assumptions":[],"state":"OneCpuRamPerImageScratchSequence","units":"raw; physical fuel/time units unknown"}),
    ]
}
pub fn admission(d: &Decoded) -> FormAdmission {
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    // MSM66201 printed 3-69,3-83,3-100,3-151,3-121,3-70,3-164,
    // 3-42,3-66,3-154. No word obj,A ADD or SUBB is admitted.
    match (p.mnemonic, p.dd_mode, p.bytes_pat) {
        ("L A, off N8", 'S', ["E4", "N8"])
        | ("MOV er0, off N8", 'U', ["B4", "N8", "48"])
        | ("MUL", 'U', ["90", "35"])
        | ("SRL er1", 'U', ["45", "E7"])
        | ("ROR A", '1', ["43"])
        | ("LB A, r2", 'R', ["7A"])
        | ("SWAP", '1', ["83"])
        | ("CMPB r3, #N8", 'U', ["23", "C0", "N8"])
        | ("JEQ rel8", 'U', ["C9", "rel8"])
        | ("L A, #N16", 'S', ["67", "NL", "NH"])
        | ("ST A, er2", '1', ["8A"]) => FormAdmission::Allowed,
        ("L A, N8", 'S', ["E5", "N8"]) if d.fields.n8 == 6 => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}
pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r.fuel_calculation_chain.as_ref().expect("validated");
    let mut sequences = vec![];
    for &pattern in &r.scratch_patterns {
        let (mut cpu, mut bus) =
            seed_machine(&r.images[0].rom, &fuel::contract("rpmAxes"), pattern);
        cpu.ssp = 0x7FE;
        fuel::seed_state(&mut cpu, &mut bus, &s.initial_state);
        write_data_u16(&mut cpu, &mut bus, 0x158, 0);
        // Static 217A caller compatibility only; the gate/2194 path is NOT run.
        let caller_gate0124 = crate::exec::read_data_u8(&cpu, &mut bus, 0x124) & !0x10;
        write_data_u8(&mut cpu, &mut bus, 0x124, caller_gate0124);
        let mut ranges = fuel::data_ranges();
        ranges.push([0x158, 0x15A]);
        bus.configure_scoped_access(ranges, 4096);
        let mut stopped = false;
        let mut checkpoints = vec![];
        for c in &s.calls {
            let before = fuel::state(&cpu, &mut bus);
            let factor_before = read_data_u16(&cpu, &mut bus, 0x158);
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
                downstream_entry: None,
                downstream: None,
                downstream_exit: None,
                accesses: vec![],
                host_transition_writes: vec![],
                tail_boundaries: vec![],
                factor0158_before: factor_before,
                factor0158_after: factor_before,
                output: None,
            };
            if !stopped {
                row.input = Some(c.clone());
                for (a, v) in [
                    (0x238, c.raw_map0_rpm),
                    (0xC2, c.raw_map1_rpm),
                    (0xBF, c.raw_load),
                ] {
                    write_data_u8(&mut cpu, &mut bus, a, v);
                }
                write_data_u16(&mut cpu, &mut bus, 0x158, c.factor0158);
                row.prefix.state_after_inputs = Some(fuel::state(&cpu, &mut bus));
                execute_prefix(
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
                    let contract = contract();
                    enter(&mut cpu, &mut bus, &contract);
                    row.host_transition_writes =
                        vec![[2, 16, 0x20], [4, 16, 0x0101], [0x8E, 16, 0x280]];
                    row.downstream_entry = Some(boundary(&cpu, &mut bus));
                    bus.set_program_data_ranges(vec![]);
                    bus.begin_native_accesses();
                    bus.begin_write_journal();
                    bus.start_decision_observer();
                    let result = execute_in_state_observed(
                        &mut cpu,
                        &mut bus,
                        &contract,
                        &[],
                        true,
                        Some(admission),
                        true,
                    );
                    row.accesses.extend(bus.end_native_accesses());
                    row.status = result.status;
                    row.downstream = Some(Stage {
                        result,
                        writes: bus.end_write_journal(),
                        events: bus.finish_decision_observer(),
                        ssp_after: cpu.ssp,
                    });
                    row.downstream_exit = Some(boundary(&cpu, &mut bus));
                    if row.status == 0 {
                        row.output = Some(read_data_u16(&cpu, &mut bus, 0x104));
                    }
                }
                row.factor0158_after = read_data_u16(&cpu, &mut bus, 0x158);
                stopped = row.status != 0;
            }
            checkpoints.push(row);
        }
        sequences.push(Sequence {
            scratch_pattern: pattern,
            caller_gate0124,
            checkpoints,
        });
    }
    response.entry_contracts = entry_contracts();
    response.fuel_calculation_sequences = Some(sequences);
    Ok(response)
}
