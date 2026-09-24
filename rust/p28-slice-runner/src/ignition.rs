//! M2c: bounded raw axes -> ROM-owned primary ignition-map selection/lookup -> DATA0248 consumer.
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
    pub selector0227: u8,
    pub consumer_factor0247: u8,
    pub consumer_output0248: u8,
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
    pub axes: Option<crate::adaptive::Stage>,
    pub selection: Option<crate::adaptive::Stage>,
    pub lookup: Option<crate::adaptive::Stage>,
    pub consumer: Option<crate::adaptive::Stage>,
    pub selected_origin: Option<u16>,
    pub position: Option<Position>,
    pub lookup_result: Option<u8>,
    pub consumer_output: Option<u8>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Sequence {
    pub scratch_pattern: u8,
    pub checkpoints: Vec<Checkpoint>,
}

pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .ignition_map_lookup
        .as_ref()
        .ok_or("ignition-map stimulus required")?;
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
        || s.calls.iter().enumerate().any(|(i, c)| {
            c.index as usize != i || (c.map_id != "ignition_map_0" && c.map_id != "ignition_map_1")
        })
    {
        return Err("invalid bounded ignition-map request".into());
    }
    Ok(())
}

pub(crate) fn data_ranges() -> Vec<[u16; 2]> {
    vec![
        [0, 8],
        [0x88, 0x90],
        [0xB8, 0xB9],
        [0xBC, 0xBD],
        [0xBF, 0xC0],
        [0xC2, 0xC3],
        [0x1BB, 0x1C8],
        [0x200, 0x208],
        [0x212, 0x220],
        [0x227, 0x228],
        [0x238, 0x239],
        [0x247, 0x249],
        [0x7E0, 0x800],
    ]
}

pub(crate) fn code(stage: &str) -> Vec<[u32; 2]> {
    match stage {
        "axes" => vec![[0x0A0C, 0x0A62], [0x59B2, 0x59E4]],
        "selection" => vec![[0x0B64, 0x0BAF]],
        "lookup" => vec![[0x0BAF, 0x0BB4], [0x59E4, 0x5A46]],
        "consumer" => vec![[0x0BB4, 0x0BD4]],
        _ => unreachable!(),
    }
}

pub(crate) fn program(stage: &str) -> Vec<[u16; 2]> {
    match stage {
        "axes" => vec![[0x7000, 0x700A], [0x7014, 0x703C]],
        "lookup" => vec![[0x72E4, 0x7474]],
        _ => vec![],
    }
}

pub(crate) fn contract(stage: &str) -> SliceContract {
    let (entry, exit, budget) = match stage {
        "axes" => (0x0A0C, 0x0A62, 576),
        "selection" => (0x0B64, 0x0BAF, 64),
        "lookup" => (0x0BAF, 0x0BB4, 192),
        "consumer" => (0x0BB4, 0x0BD4, 32),
        _ => unreachable!(),
    };
    SliceContract {
        entry_pc: entry,
        exit_pcs: vec![exit],
        code_ranges: code(stage),
        psw: 0x0101,
        lrb: 0x40,
        usp: 0x180,
        instruction_budget: budget,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    }
}

pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({
        "id":"ignitionMapLookup","stages":[
            {"id":"axes","entry":0x0A0C,"exit":0x0A62,"code":code("axes"),"programData":program("axes"),"lrb":0x40,"usp":0x180,"budget":576},
            {"id":"selection","entry":0x0B64,"exit":0x0BAF,"code":code("selection"),"programData":program("selection"),"lrb":0x40,"usp":0x180,"budget":64},
            {"id":"lookup","entry":0x0BAF,"exit":0x0BB4,"code":code("lookup"),"programData":program("lookup"),"lrb":0x40,"usp":0x180,"budget":192},
            {"id":"consumer","entry":0x0BB4,"exit":0x0BD4,"code":code("consumer"),"programData":program("consumer"),"lrb":0x40,"usp":0x180,"budget":32}
        ],
        "dataRanges":data_ranges(),"psw":0x0101,"scb":1,"ssp":0x7FE,"tracePrefix":128,"stop":"BeforeInstruction",
        "fixedCallerState":{"data00b8Mask18":0,"data0212Bits2And4":false,"data021dBit4":false,"data0214Bit5":false,"data0218Bit5":false,"data021fBit1":false,"data0219Bit6":false},
        "scriptedPerCall":["DATA0238 raw primary RPM input","DATA00C2 secondary RPM input (natively shadowed by DATA0238 in context 1)","DATA00BF raw ignition load input","DATA0227.5 software map selector (masked)"],
        "state":"Seed once; native caches/fraction words/DATA0248 persist; stages are a scripted direct-caller schedule, not the ECU main loop",
        "physicalUnitsAvailable":false,"assumptions":[]
    })]
}

pub(crate) fn state(cpu: &Cpu, bus: &mut Bus) -> State {
    State {
        load_index: read_data_u8(cpu, bus, 0x1BB),
        map0_rpm_index: read_data_u8(cpu, bus, 0x1C6),
        map1_rpm_index: read_data_u8(cpu, bus, 0x1C7),
        load_fraction: read_data_u16(cpu, bus, 0x1BE),
        map0_rpm_fraction: read_data_u16(cpu, bus, 0x1C2),
        map1_rpm_fraction: read_data_u16(cpu, bus, 0x1C4),
        selector0227: read_data_u8(cpu, bus, 0x227),
        consumer_factor0247: read_data_u8(cpu, bus, 0x247),
        consumer_output0248: read_data_u8(cpu, bus, 0x248),
    }
}

pub(crate) fn execute(cpu: &mut Cpu, bus: &mut Bus, stage: &str, enter_stage: bool) -> crate::adaptive::Stage {
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

pub(crate) fn seed_state(cpu: &mut Cpu, bus: &mut Bus, initial: &State) {
    for (address, value) in [
        (0x1BE, initial.load_fraction),
        (0x1C2, initial.map0_rpm_fraction),
        (0x1C4, initial.map1_rpm_fraction),
    ] {
        write_data_u16(cpu, bus, address, value);
    }
    for (address, value) in [
        (0x1BB, initial.load_index),
        (0x1C6, initial.map0_rpm_index),
        (0x1C7, initial.map1_rpm_index),
        (0x227, initial.selector0227),
        (0x247, initial.consumer_factor0247),
        (0x248, initial.consumer_output0248),
    ] {
        write_data_u8(cpu, bus, address, value);
    }
    // Fixed direct primary-map caller context. Only DATA0227.5 changes per call.
    for (address, value) in [
        (0xB8, 0),
        (0xBC, 0),
        (0x212, 0),
        (0x214, 0),
        (0x218, 0),
        (0x219, 0),
        (0x21D, 0),
        (0x21F, 0),
    ] {
        write_data_u8(cpu, bus, address, value);
    }
}

pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let stimulus = r.ignition_map_lookup.as_ref().expect("validated");
    let mut sequences = vec![];
    for &pattern in &r.scratch_patterns {
        let (mut cpu, mut bus) = seed_machine(&r.images[0].rom, &contract("axes"), pattern);
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
                axes: None,
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
                let selector = read_data_u8(&cpu, &mut bus, 0x227);
                write_data_u8(
                    &mut cpu,
                    &mut bus,
                    0x227,
                    (selector & !0x20)
                        | if call.map_id == "ignition_map_1" {
                            0x20
                        } else {
                            0
                        },
                );
                row.state_after_inputs = Some(state(&cpu, &mut bus));

                let axes = execute(&mut cpu, &mut bus, "axes", true);
                row.status = axes.result.status;
                row.axes = Some(axes);
                if row.status == 0 {
                    let selection = execute(&mut cpu, &mut bus, "selection", true);
                    row.status = selection.result.status;
                    row.selection = Some(selection);
                }
                if row.status == 0 {
                    let origin = read_data_u16(&cpu, &mut bus, 0x88);
                    let load_index = read_data_u8(&cpu, &mut bus, 0x1BB);
                    let load_fraction = read_data_u16(&cpu, &mut bus, 0x1BE);
                    let (rpm_index, rpm_fraction) = if call.map_id == "ignition_map_1" {
                        (
                            read_data_u8(&cpu, &mut bus, 0x1C7),
                            read_data_u16(&cpu, &mut bus, 0x1C4),
                        )
                    } else {
                        (
                            read_data_u8(&cpu, &mut bus, 0x1C6),
                            read_data_u16(&cpu, &mut bus, 0x1C2),
                        )
                    };
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
                    row.lookup_result = Some(cpu.a as u8);
                    let consumer = execute(&mut cpu, &mut bus, "consumer", false);
                    row.status = consumer.result.status;
                    row.consumer = Some(consumer);
                    if row.status == 0 {
                        row.consumer_output = Some(read_data_u8(&cpu, &mut bus, 0x248));
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
    response.ignition_map_sequences = Some(sequences);
    Ok(response)
}

/// Exact runtime instruction-form inventory for the four M2c stages and their two helpers.
pub fn admission(d: &Decoded) -> FormAdmission {
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    if crate::fuel::admission(d) == FormAdmission::Allowed
        || matches!(
            p.mnemonic,
            "MOV X2, S8[USP]"
                | "MOV er3, S8[USP]"
                | "MOVB r2, S8[USP]"
                | "MOVB r0, A"
                | "MOVB r0, N8"
                | "LB A, off N8"
                | "STB A, off N8"
                | "RB PSWL.5"
                | "NOP"
                | "SJ rel8"
                | "JBS off N8.2, rel8"
                | "JBS off N8.4, rel8"
                | "JBR off N8.1, rel8"
        )
    {
        FormAdmission::Allowed
    } else {
        FormAdmission::Unsupported
    }
}
