//! M2a: bounded raw-axis -> native map selection/lookup -> immediate consumer.
use crate::{
    acquisition::enter,
    bus::Bus,
    cpu::Cpu,
    decoder::Decoded,
    exec::{read_data_u16, read_data_u8, write_data_u16, write_data_u8},
    full_decoder::FULL_OPCODES,
    instruction_forms::FormAdmission,
    protocol::{Request, Response},
    runner::{execute_in_state_observed, seed_machine, SliceContract},
};
use serde::{Deserialize, Serialize};

const NOT_RUN: i32 = 4;

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct State {
    pub load_index: u8,
    pub map0_rpm_index: u8,
    pub map1_rpm_index: u8,
    pub load_fraction: u16,
    pub map0_rpm_fraction: u16,
    pub map1_rpm_fraction: u16,
    pub selector0127: u8,
    pub consumer_factor013f: u8,
    pub consumer_output0140: u16,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Call {
    pub index: u32,
    pub map_id: String,
    pub raw_load: u8,
    pub raw_map0_rpm: u8,
    pub raw_map1_rpm: u8,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Stimulus {
    pub format_version: u32,
    pub initial_state: State,
    pub calls: Vec<Call>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Position {
    pub load_index: u8,
    pub load_fraction: u16,
    pub rpm_index: u8,
    pub rpm_fraction: u16,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Checkpoint {
    pub index: u32,
    pub status: i32,
    pub state_before: State,
    pub state_after_inputs: Option<State>,
    pub state_after: State,
    pub rpm_axes: Option<crate::adaptive::Stage>,
    pub load_axis: Option<crate::adaptive::Stage>,
    pub selection: Option<crate::adaptive::Stage>,
    pub lookup: Option<crate::adaptive::Stage>,
    pub consumer: Option<crate::adaptive::Stage>,
    pub selected_origin: Option<u16>,
    pub position: Option<Position>,
    pub lookup_result: Option<u16>,
    pub consumer_output: Option<u16>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Sequence {
    pub scratch_pattern: u8,
    pub checkpoints: Vec<Checkpoint>,
}

pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .fuel_map_lookup
        .as_ref()
        .ok_or("fuel-map stimulus required")?;
    if s.format_version != 1
        || s.calls.is_empty()
        || s.calls.len() > 512
        || r.images.len() != 1
        || r.images[0].id != "baseline"
        || r.images[0].rom.len() != 32768
        || r.scratch_patterns != [0, 85, 170]
        || !r.allow_assumptions.is_empty()
        || r.synthetic.is_some()
        || r.producer_cases.is_some()
        || s.initial_state.load_index > 8
        || s.initial_state.map0_rpm_index > 18
        || s.initial_state.map1_rpm_index > 18
        || s.initial_state.selector0127 & !2 != 0
        || s.calls
            .iter()
            .enumerate()
            .any(|(i, c)| c.index as usize != i || (c.map_id != "map_0" && c.map_id != "map_1"))
    {
        return Err("invalid bounded fuel-map request".into());
    }
    Ok(())
}

pub(crate) fn data_ranges() -> Vec<[u16; 2]> {
    vec![
        [0, 8],
        [0x88, 0x90],
        [0xB8, 0xB9],
        [0xBF, 0xC0],
        [0xC2, 0xC3],
        [0x100, 0x108],
        [0x11C, 0x11D],
        [0x120, 0x122],
        [0x127, 0x128],
        [0x13F, 0x142],
        [0x1BC, 0x1BD],
        [0x1C0, 0x1C8],
        [0x200, 0x208],
        [0x227, 0x228],
        [0x238, 0x239],
        [0x7E0, 0x800],
    ]
}

fn code(stage: &str) -> Vec<[u32; 2]> {
    match stage {
        "rpmAxes" => vec![[0x0A0C, 0x0A45], [0x59B2, 0x59E4]],
        "loadAxis" => vec![[0x0A62, 0x0A77], [0x59B2, 0x59E4]],
        "selection" => vec![[0x12FC, 0x1340]],
        "lookup" => vec![[0x1340, 0x1347], [0x59E4, 0x5A46]],
        "consumer" => vec![[0x1347, 0x1350], [0x5A55, 0x5A72]],
        _ => unreachable!(),
    }
}

pub(crate) fn program(stage: &str) -> Vec<[u16; 2]> {
    match stage {
        "rpmAxes" => vec![[0x7014, 0x703C]],
        "loadAxis" => vec![[0x7000, 0x700A]],
        "lookup" => vec![[0x60E5, 0x60E6], [0x7050, 0x71F4]],
        _ => vec![],
    }
}

pub(crate) fn contract(stage: &str) -> SliceContract {
    let (entry, exit, lrb, usp, budget) = match stage {
        "rpmAxes" => (0x0A0C, 0x0A45, 0x40, 0x180, 384),
        "loadAxis" => (0x0A62, 0x0A77, 0x40, 0x180, 192),
        "selection" => (0x12FC, 0x1340, 0x20, 0x280, 64),
        "lookup" => (0x1340, 0x1347, 0x20, 0x280, 192),
        "consumer" => (0x1347, 0x1350, 0x20, 0x280, 64),
        _ => unreachable!(),
    };
    SliceContract {
        entry_pc: entry,
        exit_pcs: vec![exit],
        code_ranges: code(stage),
        psw: 0x0101,
        lrb,
        usp,
        instruction_budget: budget,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    }
}

pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({
        "id":"fuelMapLookup","stages":[
            {"id":"rpmAxes","entry":0x0A0C,"exit":0x0A45,"code":code("rpmAxes"),"programData":program("rpmAxes"),"lrb":0x40,"usp":0x180,"budget":384},
            {"id":"loadAxis","entry":0x0A62,"exit":0x0A77,"code":code("loadAxis"),"programData":program("loadAxis"),"lrb":0x40,"usp":0x180,"budget":192},
            {"id":"selection","entry":0x12FC,"exit":0x1340,"code":code("selection"),"programData":program("selection"),"lrb":0x20,"usp":0x280,"budget":64},
            {"id":"lookup","entry":0x1340,"exit":0x1347,"code":code("lookup"),"programData":program("lookup"),"lrb":0x20,"usp":0x280,"budget":192},
            {"id":"consumer","entry":0x1347,"exit":0x1350,"code":code("consumer"),"programData":program("consumer"),"lrb":0x20,"usp":0x280,"budget":64}
        ],
        "dataRanges":data_ranges(),"psw":0x0101,"scb":1,"ssp":0x7FE,"tracePrefix":128,"stop":"BeforeInstruction",
        "fixedCallerState":{"data00b8Mask18":0,"data0227Bit5":false,"data011cBit5":false,"data0120Bit5":false,"data0121Bit6":false},
        "scriptedPerCall":["DATA0238 raw map_0 axis input","DATA00C2 raw map_1 axis input","DATA00BF raw load input","DATA0127.1 software map selector"],
        "state":"Seed once; native caches/fraction words/results persist; stages are a scripted schedule, not the ECU main loop",
        "physicalUnitsAvailable":false,"assumptions":[]
    })]
}

pub(crate) fn state(cpu: &Cpu, bus: &mut Bus) -> State {
    State {
        load_index: read_data_u8(cpu, bus, 0x1BC),
        map0_rpm_index: read_data_u8(cpu, bus, 0x1C6),
        map1_rpm_index: read_data_u8(cpu, bus, 0x1C7),
        load_fraction: read_data_u16(cpu, bus, 0x1C0),
        map0_rpm_fraction: read_data_u16(cpu, bus, 0x1C2),
        map1_rpm_fraction: read_data_u16(cpu, bus, 0x1C4),
        selector0127: read_data_u8(cpu, bus, 0x127),
        consumer_factor013f: read_data_u8(cpu, bus, 0x13F),
        consumer_output0140: read_data_u16(cpu, bus, 0x140),
    }
}

fn execute(cpu: &mut Cpu, bus: &mut Bus, stage: &str, enter_stage: bool) -> crate::adaptive::Stage {
    let c = contract(stage);
    if enter_stage {
        enter(cpu, bus, &c);
    } else {
        bus.clear_program_reads();
    }
    bus.set_program_data_ranges(program(stage));
    bus.begin_write_journal();
    bus.start_decision_observer();
    let result = execute_in_state_observed(cpu, bus, &c, &[], true, Some(admission), true);
    crate::adaptive::Stage {
        result,
        writes: bus.end_write_journal(),
        events: bus.finish_decision_observer(),
        ssp_after: cpu.ssp,
    }
}

fn seed_state(cpu: &mut Cpu, bus: &mut Bus, initial: &State) {
    for (address, value) in [
        (0x1C0, initial.load_fraction),
        (0x1C2, initial.map0_rpm_fraction),
        (0x1C4, initial.map1_rpm_fraction),
        (0x140, initial.consumer_output0140),
    ] {
        write_data_u16(cpu, bus, address, value);
    }
    for (address, value) in [
        (0x1BC, initial.load_index),
        (0x1C6, initial.map0_rpm_index),
        (0x1C7, initial.map1_rpm_index),
        (0x13F, initial.consumer_factor013f),
        (0x127, initial.selector0127),
    ] {
        write_data_u8(cpu, bus, address, value);
    }
    // Fixed, narrow caller context. Only DATA0127.1 is changed per call.
    for (address, value) in [(0xB8, 0), (0x227, 0), (0x11C, 0), (0x120, 0), (0x121, 0)] {
        write_data_u8(cpu, bus, address, value);
    }
}

pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let stimulus = r.fuel_map_lookup.as_ref().expect("validated");
    let mut sequences = vec![];
    for &pattern in &r.scratch_patterns {
        let (mut cpu, mut bus) = seed_machine(&r.images[0].rom, &contract("rpmAxes"), pattern);
        cpu.ssp = 0x7FE;
        seed_state(&mut cpu, &mut bus, &stimulus.initial_state);
        bus.configure_scoped_access(data_ranges(), 4096);
        let mut stopped = false;
        let mut checkpoints = vec![];
        for call in &stimulus.calls {
            let before = state(&cpu, &mut bus);
            let mut row = Checkpoint {
                index: call.index,
                status: NOT_RUN,
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
            };
            if !stopped {
                write_data_u8(&mut cpu, &mut bus, 0x238, call.raw_map0_rpm);
                write_data_u8(&mut cpu, &mut bus, 0xC2, call.raw_map1_rpm);
                write_data_u8(&mut cpu, &mut bus, 0xBF, call.raw_load);
                let selector = read_data_u8(&cpu, &mut bus, 0x127);
                write_data_u8(
                    &mut cpu,
                    &mut bus,
                    0x127,
                    (selector & !2) | if call.map_id == "map_1" { 2 } else { 0 },
                );
                row.state_after_inputs = Some(state(&cpu, &mut bus));

                let rpm = execute(&mut cpu, &mut bus, "rpmAxes", true);
                row.status = rpm.result.status;
                row.rpm_axes = Some(rpm);
                if row.status == 0 {
                    let load = execute(&mut cpu, &mut bus, "loadAxis", true);
                    row.status = load.result.status;
                    row.load_axis = Some(load);
                }
                if row.status == 0 {
                    let selection = execute(&mut cpu, &mut bus, "selection", true);
                    row.status = selection.result.status;
                    row.selection = Some(selection);
                }
                if row.status == 0 {
                    let origin = read_data_u16(&cpu, &mut bus, 0x88);
                    let load_index = read_data_u8(&cpu, &mut bus, 0x102);
                    let rpm_index = read_data_u8(&cpu, &mut bus, 0x103);
                    let load_fraction = read_data_u16(&cpu, &mut bus, 0x8A);
                    let rpm_fraction = read_data_u16(&cpu, &mut bus, 0x106);
                    row.selected_origin = Some(origin);
                    row.position = Some(Position {
                        load_index,
                        load_fraction,
                        rpm_index,
                        rpm_fraction,
                    });
                    let lookup = execute(&mut cpu, &mut bus, "lookup", false);
                    row.status = lookup.result.status;
                    row.lookup = Some(lookup);
                }
                if row.status == 0 {
                    row.lookup_result = Some(read_data_u16(&cpu, &mut bus, 0x104));
                    let consumer = execute(&mut cpu, &mut bus, "consumer", false);
                    row.status = consumer.result.status;
                    row.consumer = Some(consumer);
                    if row.status == 0 {
                        row.consumer_output = Some(read_data_u16(&cpu, &mut bus, 0x140));
                    }
                }
                stopped = row.status != 0;
                row.state_after = state(&cpu, &mut bus);
            }
            checkpoints.push(row);
        }
        sequences.push(Sequence {
            scratch_pattern: pattern,
            checkpoints,
        });
    }
    response.entry_contracts = entry_contracts();
    response.fuel_map_sequences = Some(sequences);
    Ok(response)
}

/// Exact instruction-form inventory for only the five M2a stages/helpers.
pub fn admission(d: &Decoded) -> FormAdmission {
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    if matches!(
        p.mnemonic,
        "MOV X1, #N16"
            | "MOV X2, off N8"
            | "MOV er3, off N8"
            | "MOV DP, #N16"
            | "MOV DP, X1"
            | "MOV DP, A"
            | "MOV X1, DP"
            | "MOV X1, A"
            | "MOV X1, er1"
            | "MOV er0, X2"
            | "MOV er0, er3"
            | "MOV er2, X1"
            | "MOV A, er2"
            | "MOVB r0, #N8"
            | "MOVB r1, #N8"
            | "MOVB r2, off N8"
            | "MOVB r2, N8"
            | "MOVB r3, off N8"
            | "MOVB r3, S8[USP]"
            | "MOVB r4, #N8"
            | "MOVB r6, #N8"
            | "MOVB r0, r4"
            | "MOVB r0, r5"
            | "MOVB r0, off N8"
            | "LB A, r0"
            | "LB A, r1"
            | "LB A, r2"
            | "LB A, r3"
            | "LB A, r4"
            | "LB A, r6"
            | "LB A, N8"
            | "L A, #N16"
            | "L A, DP"
            | "L A, X1"
            | "L A, er1"
            | "L A, er2"
            | "L A, ACC"
            | "LCB A, [X1]"
            | "LCB A, N16"
            | "LC A, [DP]"
            | "LC A, [X1]"
            | "ST A, er0"
            | "ST A, er1"
            | "ST A, er2"
            | "ST A, off N8"
            | "STB A, r0"
            | "STB A, r2"
            | "STB A, r4"
            | "STB A, r6"
            | "STB A, S8[USP]"
            | "ST A, S8[USP]"
            | "MB C, N8.3"
            | "MB C, N8.4"
            | "MB C, PSWL.4"
            | "MB C, PSWL.5"
            | "MB PSWL.4, C"
            | "RB PSWL.4"
            | "SB PSWL.5"
            | "CMPB A, r2"
            | "CMPB A, r3"
            | "CMPB A, r6"
            | "CMPB r0, #N8"
            | "CMPB r3, #N8"
            | "CMPCB A, [X1]"
            | "SUBB A, r4"
            | "SUB A, er1"
            | "SUB A, er2"
            | "SUB er2, A"
            | "ADD X1, A"
            | "ADD DP, A"
            | "ADD A, er2"
            | "INC X1"
            | "INCB r1"
            | "INCB r6"
            | "DEC X1"
            | "DECB r6"
            | "CLR A"
            | "MUL"
            | "MULB"
            | "DIV"
            | "ROL er0"
            | "SLL er2"
            | "SRLB r3"
            | "ROR A"
            | "SWAP"
            | "XCHG A, er2"
            | "CAL addr16"
            | "RT"
            | "JEQ rel8"
            | "JLT rel8"
            | "JGE rel8"
            | "JLE rel8"
            | "JGT rel8"
            | "JBS off N8.1, rel8"
            | "JBS off N8.5, rel8"
            | "JBR off N8.5, rel8"
            | "JBR off N8.6, rel8"
    ) {
        FormAdmission::Allowed
    } else {
        FormAdmission::Unsupported
    }
}
