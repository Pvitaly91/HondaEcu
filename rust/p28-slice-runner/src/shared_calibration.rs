//! M2h: one CPU/RAM, one axis pass, two native lookup/consumer tails.
//! Entries between routines are disclosed scripted caller actions, not an ECU scheduler.
use crate::{
    acquisition::enter,
    adaptive::Stage,
    bus::Bus,
    cpu::Cpu,
    decoder::Decoded,
    exec::{read_data_u16, read_data_u8, write_data_u16, write_data_u8},
    fuel, ignition, ignition_selector,
    instruction_forms::FormAdmission,
    protocol::{Request, Response},
    runner::{execute_in_state_observed, seed_machine, SliceContract},
    stateful, stateful_forms, vtec_fuel,
    vtec_fuel::{boundary, CpuBoundary},
};
use serde::{Deserialize, Serialize};

const NOT_RUN: i32 = 4;

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Axes {
    pub ignition_load_index: u8,
    pub fuel_load_index: u8,
    pub map0_rpm_index: u8,
    pub map1_rpm_index: u8,
    pub ignition_load_fraction: u16,
    pub fuel_load_fraction: u16,
    pub map0_rpm_fraction: u16,
    pub map1_rpm_fraction: u16,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct State {
    pub vtec: stateful::State,
    pub axes: Axes,
    pub selector0227: u8,
    pub factor0247: u8,
    pub output0248: u8,
    pub factor013f: u8,
    pub output0140: u16,
    pub source03c7: u8,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Call {
    pub index: u32,
    pub source03c7: u8,
    pub raw_load: u8,
    pub raw_map0_rpm: u8,
    pub raw_map1_rpm: u8,
    pub decision: stateful::Call,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Stimulus {
    pub format_version: u32,
    pub initial: State,
    pub calls: Vec<Call>,
    pub trace_call_indexes: Vec<u32>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Checkpoint {
    pub index: u32,
    pub status: i32,
    pub conditional_dependency: bool,
    pub input: Option<Call>,
    pub state_before: State,
    pub state_after_inputs: Option<State>,
    pub state_after_ticks: Option<State>,
    pub state_after_producer: Option<State>,
    pub state_after_axis: Option<State>,
    pub state_after_ignition: Option<State>,
    pub state_after_decision: Option<State>,
    pub state_after: State,
    pub tick_runs: Vec<[u32; 5]>,
    pub tick_writes: Vec<[u32; 3]>,
    pub producer: Option<Stage>,
    pub producer_exit: Option<CpuBoundary>,
    pub axis_entry: Option<CpuBoundary>,
    pub axis: Option<Stage>,
    pub axis_exit: Option<CpuBoundary>,
    pub ignition_entry: Option<CpuBoundary>,
    pub ignition_selection: Option<Stage>,
    pub ignition_selection_exit: Option<CpuBoundary>,
    pub ignition_origin: Option<u16>,
    pub ignition_lookup_entry: Option<CpuBoundary>,
    pub ignition_lookup: Option<Stage>,
    pub ignition_lookup_exit: Option<CpuBoundary>,
    pub ignition_value: Option<u8>,
    pub ignition_consumer_entry: Option<CpuBoundary>,
    pub ignition_consumer: Option<Stage>,
    pub ignition_output: Option<u8>,
    pub ignition_completed: bool,
    pub decision_entry: Option<CpuBoundary>,
    pub decision: Option<Stage>,
    pub boundary12fc: Option<CpuBoundary>,
    pub fuel_selection_entry: Option<CpuBoundary>,
    pub fuel_selection: Option<Stage>,
    pub fuel_selection_exit: Option<CpuBoundary>,
    pub fuel_origin: Option<u16>,
    pub fuel_lookup_entry: Option<CpuBoundary>,
    pub fuel_lookup: Option<Stage>,
    pub fuel_lookup_exit: Option<CpuBoundary>,
    pub fuel_value: Option<u16>,
    pub fuel_consumer_entry: Option<CpuBoundary>,
    pub fuel_consumer: Option<Stage>,
    pub fuel_output: Option<u16>,
    pub request_p1: Option<bool>,
    pub request_mirror0127: Option<bool>,
    pub fuel_selector0127: Option<bool>,
    pub used_assumptions: Vec<String>,
    pub error: Option<String>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Sequence {
    pub image_index: usize,
    pub scratch_pattern: u8,
    pub checkpoints: Vec<Checkpoint>,
    pub completed_calls: u32,
    pub stop_call_index: i32,
}

pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .shared_calibration_chain
        .as_ref()
        .ok_or("M2h stimulus required")?;
    let a = &s.initial.axes;
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
        || a.ignition_load_index > 8
        || a.fuel_load_index > 8
        || a.map0_rpm_index > 18
        || a.map1_rpm_index > 18
        || s.calls.iter().enumerate().any(|(i, c)| {
            c.index as usize != i
                || c.decision.index != c.index
                || c.decision.context > 1
                || c.decision.fast_ticks > 32
                || c.decision.slow_ticks > 32
                || c.decision.snapshot011c & 0x20 != 0
        })
        || r.scratch_patterns != [0, 85, 170]
        || r.images.is_empty()
        || r.images.len() > 2
        || r.images[0].id != "baseline"
        || r.images.get(1).is_some_and(|i| i.id != "mutated")
        || r.images.iter().any(|i| i.rom.len() != 32768)
        || r.synthetic.is_some()
        || r.producer_cases.is_some()
        || r.allow_assumptions
            .iter()
            .any(|a| a != stateful_forms::SUBB_OFF_ASSUMPTION)
    {
        return Err("invalid bounded M2h shared-state contract".into());
    }
    Ok(())
}

pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({
        "id":"vtecFuelIgnitionChain", "formatVersion":1,
        "state":"OneCpuRamPerImageScratchSequence",
        "scriptedEntries":[0x5F93,0x0A0C,0x0B64,0x122C],
        "producer":[0x5F93,0x5FAF], "continuousAxis":[0x0A0C,0x0A77],
        "axisInternalBoundaries":[0x0A45,0x0A62],
        "ignitionTail":[0x0B64,0x0BD4], "fuelTail":[0x122C,0x1350],
        "hostWritesAfterInput":["native tick target 0088 only"],
        "sharedRpm":[0x1C6,0x1C7,0x1C2,0x1C4],
        "separateLoad":[0x1BB,0x1BE,0x1BC,0x1C0],
        "perCallMapId":false,"physicalRpmAvailable":false,
        "allowedAssumptions":[stateful_forms::SUBB_OFF_ASSUMPTION]
    })]
}

fn axes_contract() -> SliceContract {
    SliceContract {
        entry_pc: 0x0A0C,
        exit_pcs: vec![0x0A77],
        code_ranges: vec![[0x0A0C, 0x0A77], [0x59B2, 0x59E4]],
        psw: 0x0101,
        lrb: 0x40,
        usp: 0x180,
        instruction_budget: 768,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    }
}

fn axis_admission(d: &Decoded) -> FormAdmission {
    if ignition::admission(d) == FormAdmission::Allowed
        || fuel::admission(d) == FormAdmission::Allowed
    {
        FormAdmission::Allowed
    } else {
        FormAdmission::Unsupported
    }
}

fn axis(cpu: &mut Cpu, bus: &mut Bus, trace: bool) -> Stage {
    let c = axes_contract();
    bus.set_program_data_ranges(vec![[0x7000, 0x700A], [0x7014, 0x703C]]);
    bus.begin_write_journal();
    bus.start_decision_observer();
    let result = execute_in_state_observed(cpu, bus, &c, &[], trace, Some(axis_admission), true);
    Stage {
        result,
        writes: bus.end_write_journal(),
        events: bus.finish_decision_observer(),
        ssp_after: cpu.ssp,
    }
}

fn snapshot(cpu: &Cpu, bus: &mut Bus) -> State {
    State {
        vtec: stateful::snapshot(cpu, bus),
        axes: Axes {
            ignition_load_index: read_data_u8(cpu, bus, 0x1BB),
            fuel_load_index: read_data_u8(cpu, bus, 0x1BC),
            map0_rpm_index: read_data_u8(cpu, bus, 0x1C6),
            map1_rpm_index: read_data_u8(cpu, bus, 0x1C7),
            ignition_load_fraction: read_data_u16(cpu, bus, 0x1BE),
            fuel_load_fraction: read_data_u16(cpu, bus, 0x1C0),
            map0_rpm_fraction: read_data_u16(cpu, bus, 0x1C2),
            map1_rpm_fraction: read_data_u16(cpu, bus, 0x1C4),
        },
        selector0227: read_data_u8(cpu, bus, 0x227),
        factor0247: read_data_u8(cpu, bus, 0x247),
        output0248: read_data_u8(cpu, bus, 0x248),
        factor013f: read_data_u8(cpu, bus, 0x13F),
        output0140: read_data_u16(cpu, bus, 0x140),
        source03c7: read_data_u8(cpu, bus, 0x3C7),
    }
}

fn seed(cpu: &mut Cpu, bus: &mut Bus, s: &Stimulus) {
    cpu.ssp = 0x7FE;
    bus.set_p1_output_latch(Some(s.initial.vtec.p1_output_data));
    for (address, value) in stateful::STATE_ADDRESSES
        .into_iter()
        .zip(s.initial.vtec.bytes())
    {
        if address != 0x22 {
            write_data_u8(cpu, bus, address, value);
        }
    }
    let a = &s.initial.axes;
    for (address, value) in [
        (0x1BE, a.ignition_load_fraction),
        (0x1C0, a.fuel_load_fraction),
        (0x1C2, a.map0_rpm_fraction),
        (0x1C4, a.map1_rpm_fraction),
        (0x140, s.initial.output0140),
    ] {
        write_data_u16(cpu, bus, address, value);
    }
    for (address, value) in [
        (0x1BB, a.ignition_load_index),
        (0x1BC, a.fuel_load_index),
        (0x1C6, a.map0_rpm_index),
        (0x1C7, a.map1_rpm_index),
        (0x227, s.initial.selector0227),
        (0x247, s.initial.factor0247),
        (0x248, s.initial.output0248),
        (0x13F, s.initial.factor013f),
        (0x3C7, s.initial.source03c7),
    ] {
        write_data_u8(cpu, bus, address, value);
    }
    // Explicit fixed caller assumptions. Never re-applied after initial seed.
    for address in [
        0xB8, 0xBC, 0x11E, 0x120, 0x121, 0x212, 0x214, 0x218, 0x219, 0x21D, 0x21F,
    ] {
        write_data_u8(cpu, bus, address, 0);
    }
}

fn ranges() -> Vec<[u16; 2]> {
    let mut r = vtec_fuel::ranges();
    r.extend(ignition_selector::data_ranges());
    r
}

fn sequence(
    rom: &[u8],
    image_index: usize,
    pattern: u8,
    s: &Stimulus,
    allowed: &[&str],
) -> Sequence {
    let decision_contract = stateful::contract(0x122C, 0x12FC);
    let (mut cpu, mut bus) = seed_machine(rom, &decision_contract, pattern);
    seed(&mut cpu, &mut bus, s);
    bus.configure_scoped_access(ranges(), 8192);
    let mut seq = Sequence {
        image_index,
        scratch_pattern: pattern,
        checkpoints: Vec::with_capacity(s.calls.len()),
        completed_calls: 0,
        stop_call_index: -1,
    };
    let mut conditional = false;
    for input in &s.calls {
        let before = snapshot(&cpu, &mut bus);
        let mut cp = Checkpoint {
            index: input.index,
            status: NOT_RUN,
            conditional_dependency: conditional,
            input: None,
            state_before: before.clone(),
            state_after_inputs: None,
            state_after_ticks: None,
            state_after_producer: None,
            state_after_axis: None,
            state_after_ignition: None,
            state_after_decision: None,
            state_after: before,
            tick_runs: vec![],
            tick_writes: vec![],
            producer: None,
            producer_exit: None,
            axis_entry: None,
            axis: None,
            axis_exit: None,
            ignition_entry: None,
            ignition_selection: None,
            ignition_selection_exit: None,
            ignition_origin: None,
            ignition_lookup_entry: None,
            ignition_lookup: None,
            ignition_lookup_exit: None,
            ignition_value: None,
            ignition_consumer_entry: None,
            ignition_consumer: None,
            ignition_output: None,
            ignition_completed: false,
            decision_entry: None,
            decision: None,
            boundary12fc: None,
            fuel_selection_entry: None,
            fuel_selection: None,
            fuel_selection_exit: None,
            fuel_origin: None,
            fuel_lookup_entry: None,
            fuel_lookup: None,
            fuel_lookup_exit: None,
            fuel_value: None,
            fuel_consumer_entry: None,
            fuel_consumer: None,
            fuel_output: None,
            request_p1: None,
            request_mirror0127: None,
            fuel_selector0127: None,
            used_assumptions: vec![],
            error: None,
        };
        if seq.stop_call_index >= 0 {
            seq.checkpoints.push(cp);
            continue;
        }
        cp.input = Some(input.clone());
        let d = &input.decision;
        for (address, value) in [
            (0x3C7, input.source03c7),
            (0x238, input.raw_map0_rpm),
            (0xC2, input.raw_map1_rpm),
            (0xBF, input.raw_load),
            (0x133, d.compact_code),
            (0xCC, d.raw00cc),
            (0xD9, d.raw00d9),
            (0x11C, d.snapshot011c),
            (0x119, d.snapshot0119),
            (0x132, d.raw0132),
            (0x199, d.raw0199),
            (
                0x11E,
                (if d.context == 0 { 8 } else { 0 }) | (if d.enabled { 16 } else { 0 }),
            ),
        ] {
            write_data_u8(&mut cpu, &mut bus, address, value);
        }
        write_data_u16(&mut cpu, &mut bus, 0x11A, d.snapshot011a);
        cp.state_after_inputs = Some(snapshot(&cpu, &mut bus));
        let trace = s.trace_call_indexes.contains(&input.index);
        // Native counter bodies precede the selector and the sole axis pass.
        bus.set_program_data_ranges(vec![]);
        for (entry, exit, target) in stateful::tick_schedule(d.fast_ticks, d.slow_ticks) {
            let c = stateful::contract(entry, exit);
            stateful::enter(&mut cpu, &mut bus, &c);
            write_data_u16(&mut cpu, &mut bus, 0x88, target);
            bus.begin_write_journal();
            let result = execute_in_state_observed(
                &mut cpu,
                &mut bus,
                &c,
                &[],
                false,
                Some(stateful_forms::admission),
                true,
            );
            cp.tick_writes.extend(bus.end_write_journal());
            cp.tick_runs.push([
                entry as u32,
                target as u32,
                result.stop_pc as u32,
                result.status as u32,
                result.steps,
            ]);
            if result.status != 0 {
                cp.status = result.status;
                cp.error = result.error;
                break;
            }
        }
        if cp.status == NOT_RUN {
            cp.state_after_ticks = Some(snapshot(&cpu, &mut bus));
        }
        if cp.status == NOT_RUN {
            let p = ignition_selector::producer(&mut cpu, &mut bus, trace);
            cp.status = p.result.status;
            cp.error = p.result.error.clone();
            cp.producer = Some(p);
            cp.state_after_producer = Some(snapshot(&cpu, &mut bus));
        }
        if cp.status == 0 {
            cp.producer_exit = Some(boundary(&cpu, &mut bus));
            if !ignition_selector::supported_caller(&cpu, &mut bus)
                || !vtec_fuel::supported_caller(&cpu, &mut bus)
            {
                cp.status = 1;
                cp.error = Some("producer left unsupported joint direct caller gates".into());
            }
        }
        if cp.status == 0 {
            // One entry; 0A45 and 0A62 are observed inside this native pass.
            enter(&mut cpu, &mut bus, &axes_contract());
            cp.axis_entry = Some(boundary(&cpu, &mut bus));
            let a = axis(&mut cpu, &mut bus, trace);
            cp.status = a.result.status;
            cp.error = a.result.error.clone();
            cp.axis = Some(a);
            cp.state_after_axis = Some(snapshot(&cpu, &mut bus));
            if cp.status == 0 {
                cp.axis_exit = Some(boundary(&cpu, &mut bus));
            }
        }
        if cp.status == 0 {
            enter(&mut cpu, &mut bus, &ignition::contract("selection"));
            cp.ignition_entry = Some(boundary(&cpu, &mut bus));
            let x = ignition::execute(&mut cpu, &mut bus, "selection", false);
            cp.status = x.result.status;
            cp.error = x.result.error.clone();
            cp.ignition_selection = Some(x);
            if cp.status == 0 {
                cp.ignition_selection_exit = Some(boundary(&cpu, &mut bus));
            }
        }
        if cp.status == 0 {
            cp.ignition_origin = Some(read_data_u16(&cpu, &mut bus, 0x88));
            cp.ignition_lookup_entry = Some(boundary(&cpu, &mut bus));
            let x = ignition::execute(&mut cpu, &mut bus, "lookup", false);
            cp.status = x.result.status;
            cp.error = x.result.error.clone();
            cp.ignition_lookup = Some(x);
            if cp.status == 0 {
                cp.ignition_lookup_exit = Some(boundary(&cpu, &mut bus));
            }
        }
        if cp.status == 0 {
            cp.ignition_value = Some(cpu.a as u8);
            cp.ignition_consumer_entry = Some(boundary(&cpu, &mut bus));
            let x = ignition::execute(&mut cpu, &mut bus, "consumer", false);
            cp.status = x.result.status;
            cp.error = x.result.error.clone();
            cp.ignition_consumer = Some(x);
            if cp.status == 0 {
                cp.ignition_output = Some(read_data_u8(&cpu, &mut bus, 0x248));
                cp.ignition_completed = true;
                cp.state_after_ignition = Some(snapshot(&cpu, &mut bus));
            }
        }
        if cp.status == 0 {
            stateful::enter(&mut cpu, &mut bus, &decision_contract);
            cp.decision_entry = Some(boundary(&cpu, &mut bus));
            bus.set_program_data_ranges(vec![[0x6542, 0x6566], [0x60FA, 0x60FB]]);
            bus.begin_write_journal();
            bus.start_decision_observer();
            let result = execute_in_state_observed(
                &mut cpu,
                &mut bus,
                &decision_contract,
                allowed,
                trace,
                Some(stateful_forms::admission),
                true,
            );
            conditional |= !result.used_assumptions.is_empty();
            cp.conditional_dependency = conditional;
            cp.used_assumptions = result.used_assumptions.clone();
            cp.status = result.status;
            cp.error = result.error.clone();
            cp.decision = Some(Stage {
                result,
                writes: bus.end_write_journal(),
                events: bus.finish_decision_observer(),
                ssp_after: cpu.ssp,
            });
            cp.state_after_decision = Some(snapshot(&cpu, &mut bus));
        }
        if cp.status == 0 {
            cp.boundary12fc = Some(boundary(&cpu, &mut bus));
            if cpu.pc != 0x12FC || !vtec_fuel::supported_caller(&cpu, &mut bus) {
                cp.status = 1;
                cp.error =
                    Some("decision did not reach supported continuous fuel caller boundary".into());
            }
        }
        if cp.status == 0 {
            cp.fuel_selection_entry = Some(boundary(&cpu, &mut bus));
            let x = vtec_fuel::stage(&mut cpu, &mut bus, "selection", false, trace);
            cp.status = x.result.status;
            cp.error = x.result.error.clone();
            cp.fuel_selection = Some(x);
            if cp.status == 0 {
                cp.fuel_selection_exit = Some(boundary(&cpu, &mut bus));
            }
        }
        if cp.status == 0 {
            cp.fuel_origin = Some(read_data_u16(&cpu, &mut bus, 0x88));
            cp.fuel_lookup_entry = Some(boundary(&cpu, &mut bus));
            let x = vtec_fuel::stage(&mut cpu, &mut bus, "lookup", false, trace);
            cp.status = x.result.status;
            cp.error = x.result.error.clone();
            cp.fuel_lookup = Some(x);
            if cp.status == 0 {
                cp.fuel_lookup_exit = Some(boundary(&cpu, &mut bus));
            }
        }
        if cp.status == 0 {
            cp.fuel_value = Some(read_data_u16(&cpu, &mut bus, 0x104));
            cp.fuel_consumer_entry = Some(boundary(&cpu, &mut bus));
            let x = vtec_fuel::stage(&mut cpu, &mut bus, "consumer", false, trace);
            cp.status = x.result.status;
            cp.error = x.result.error.clone();
            cp.fuel_consumer = Some(x);
        }
        cp.state_after = snapshot(&cpu, &mut bus);
        if cp.status == 0 {
            cp.fuel_output = Some(cp.state_after.output0140);
            cp.request_p1 = Some(cp.state_after.vtec.p1_output_data & 1 != 0);
            cp.request_mirror0127 = Some(cp.state_after.vtec.data0127 & 4 != 0);
            cp.fuel_selector0127 = Some(cp.state_after.vtec.data0127 & 2 != 0);
            seq.completed_calls += 1;
        } else {
            seq.stop_call_index = input.index as i32;
        }
        seq.checkpoints.push(cp);
    }
    seq
}

pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let stimulus = r
        .shared_calibration_chain
        .as_ref()
        .ok_or("missing M2h stimulus")?;
    let allowed: Vec<_> = r.allow_assumptions.iter().map(String::as_str).collect();
    response.entry_contracts = entry_contracts();
    response.shared_calibration_sequences = Some(
        r.images
            .iter()
            .enumerate()
            .flat_map(|(index, image)| {
                r.scratch_patterns
                    .iter()
                    .map(|pattern| sequence(&image.rom, index, *pattern, stimulus, &allowed))
                    .collect::<Vec<_>>()
            })
            .collect(),
    );
    Ok(response)
}
