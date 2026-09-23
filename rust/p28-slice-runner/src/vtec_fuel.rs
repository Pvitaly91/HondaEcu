//! M2f: one CPU/RAM lifetime, with an unbroken decision -> fuel tail.
//! Only the pre-decision caller fragments are scripted. No selector or map
//! pointer is supplied by the host after the once-only initial state.
use crate::{
    adaptive::Stage,
    bus::Bus,
    cpu::Cpu,
    exec::{read_data_u16, read_data_u8, write_data_u16, write_data_u8},
    fuel,
    protocol::{CaseResult, Request, Response},
    runner::{execute_in_state_observed, seed_machine},
    stateful, stateful_forms,
};
use serde::{Deserialize, Serialize};

const NOT_RUN: i32 = 4;

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct FuelInitial {
    pub load_index: u8,
    pub map0_rpm_index: u8,
    pub map1_rpm_index: u8,
    pub load_fraction: u16,
    pub map0_rpm_fraction: u16,
    pub map1_rpm_fraction: u16,
    pub consumer_factor013f: u8,
    pub consumer_output0140: u16,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Call {
    pub index: u32,
    pub raw_load: u8,
    pub raw_map0_rpm: u8,
    pub raw_map1_rpm: u8,
    pub decision: stateful::Call,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Stimulus {
    pub format_version: u32,
    pub initial_vtec: stateful::State,
    pub initial_fuel: FuelInitial,
    pub calls: Vec<Call>,
    pub trace_call_indexes: Vec<u32>,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct CpuBoundary {
    pub pc: u16,
    pub accumulator: u16,
    pub psw: u16,
    pub dd: bool,
    pub lrb: u16,
    pub x1: u16,
    pub x2: u16,
    pub dp: u16,
    pub usp: u16,
    pub ssp: u16,
    pub registers: [u8; 8],
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Checkpoint {
    pub index: u32,
    pub status: i32,
    pub conditional_dependency: bool,
    pub input: Option<Call>,
    pub vtec_before: stateful::State,
    pub vtec_after: stateful::State,
    pub fuel_before: fuel::State,
    pub fuel_after: fuel::State,
    pub tick_runs: Vec<[u32; 5]>,
    pub tick_writes: Vec<[u32; 3]>,
    pub rpm_axes: Option<Stage>,
    pub load_axis: Option<Stage>,
    pub decision: Option<Stage>,
    pub boundary12fc: Option<CpuBoundary>,
    pub selection_entry: Option<CpuBoundary>,
    pub selector_before_reader131a: Option<u8>,
    pub selection: Option<Stage>,
    pub selected_origin: Option<u16>,
    pub lookup: Option<Stage>,
    pub lookup_result: Option<u16>,
    pub consumer: Option<Stage>,
    pub consumer_output0140: Option<u16>,
    pub request_p1: Option<bool>,
    pub request_mirror0127: Option<bool>,
    pub selector0127: Option<bool>,
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
        .vtec_fuel_chain
        .as_ref()
        .ok_or("VTEC-fuel stimulus required")?;
    if s.format_version != 1
        || s.calls.is_empty()
        || s.calls.len() > 256
        || s.trace_call_indexes.len() > 8
        || s.trace_call_indexes
            .iter()
            .any(|i| *i as usize >= s.calls.len())
        || s.trace_call_indexes
            .iter()
            .collect::<std::collections::HashSet<_>>()
            .len()
            != s.trace_call_indexes.len()
        || s.initial_fuel.load_index > 8
        || s.initial_fuel.map0_rpm_index > 18
        || s.initial_fuel.map1_rpm_index > 18
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
        return Err("invalid bounded VTEC-fuel shared-state contract".into());
    }
    Ok(())
}

pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({
        "id":"vtecFuelChain", "formatVersion":1, "state":"OneCpuRamPerImageScratchSequence",
        "scriptedBeforeDecision":["native counter bodies","native RPM axes","native load axis"],
        "unbrokenTail":[[0x122C,0x12FC],[0x12FC,0x1340],[0x1340,0x1347],[0x1347,0x1350]],
        "helperRanges":[[0x5839,0x586E],[0x59E4,0x5A46],[0x5A55,0x5A72]],
        "hostWritesAfterDecisionEntry":[], "perCallMapId":false,
        "data0127":"Full shared byte seeded once; only native instructions write thereafter",
        "fixedCallerGates":{"data00B8Mask18":0,"data0227Bit5":false,"data0120Bit5":false,"data0121Bit6":false,"snapshot011CBit5":false},
        "tickUnits":"Native body calls, not time", "physicalRpmAvailable":false,
        "allowedAssumptions":[stateful_forms::SUBB_OFF_ASSUMPTION]
    })]
}

fn ranges() -> Vec<[u16; 2]> {
    let mut ranges = fuel::data_ranges();
    ranges.extend([
        [0x22, 0x23],
        [0xCC, 0xCD],
        [0xD9, 0xDA],
        [0xF3, 0xF4],
        [0x119, 0x11F],
        [0x131, 0x134],
        [0x198, 0x19A],
        [0x1D8, 0x1DA],
        [0x1DF, 0x1E0],
    ]);
    ranges
}

fn boundary(cpu: &Cpu, bus: &mut Bus) -> CpuBoundary {
    let base = cpu.bank_base();
    let pointing = 0x80 + cpu.scb() * 8;
    let mut registers = [0; 8];
    for (i, register) in registers.iter_mut().enumerate() {
        *register = read_data_u8(cpu, bus, base + i as u16);
    }
    CpuBoundary {
        pc: cpu.pc,
        accumulator: cpu.a,
        psw: cpu.psw_u16(),
        dd: cpu.dd,
        lrb: cpu.lrb,
        x1: read_data_u16(cpu, bus, pointing),
        x2: read_data_u16(cpu, bus, pointing + 2),
        dp: read_data_u16(cpu, bus, pointing + 4),
        usp: read_data_u16(cpu, bus, pointing + 6),
        ssp: cpu.ssp,
        registers,
    }
}

fn seed(cpu: &mut Cpu, bus: &mut Bus, s: &Stimulus) {
    cpu.ssp = 0x7FE;
    bus.set_p1_output_latch(Some(s.initial_vtec.p1_output_data));
    for (address, value) in stateful::STATE_ADDRESSES
        .into_iter()
        .zip(s.initial_vtec.bytes())
    {
        if address != 0x22 {
            write_data_u8(cpu, bus, address, value);
        }
    }
    for (address, value) in [
        (0x1C0, s.initial_fuel.load_fraction),
        (0x1C2, s.initial_fuel.map0_rpm_fraction),
        (0x1C4, s.initial_fuel.map1_rpm_fraction),
        (0x140, s.initial_fuel.consumer_output0140),
    ] {
        write_data_u16(cpu, bus, address, value);
    }
    for (address, value) in [
        (0x1BC, s.initial_fuel.load_index),
        (0x1C6, s.initial_fuel.map0_rpm_index),
        (0x1C7, s.initial_fuel.map1_rpm_index),
        (0x13F, s.initial_fuel.consumer_factor013f),
    ] {
        write_data_u8(cpu, bus, address, value);
    }
    // These are explicit fixed caller assumptions, seeded once. If native code
    // changes them later the next event is refused, never host-clamped.
    for address in [0xB8, 0x11E, 0x120, 0x121, 0x227] {
        write_data_u8(cpu, bus, address, 0);
    }
}

fn supported_caller(cpu: &Cpu, bus: &mut Bus) -> bool {
    read_data_u8(cpu, bus, 0xB8) & 0x18 == 0
        && read_data_u8(cpu, bus, 0x227) & 0x20 == 0
        && read_data_u8(cpu, bus, 0x120) & 0x20 == 0
        && read_data_u8(cpu, bus, 0x121) & 0x40 == 0
        && read_data_u8(cpu, bus, 0x11C) & 0x20 == 0
}

fn stage(cpu: &mut Cpu, bus: &mut Bus, name: &str, enter_stage: bool, trace: bool) -> Stage {
    let contract = fuel::contract(name);
    if enter_stage {
        crate::acquisition::enter(cpu, bus, &contract);
    } else {
        bus.clear_program_reads();
    }
    bus.set_program_data_ranges(fuel::program(name));
    bus.begin_write_journal();
    bus.start_decision_observer();
    let result =
        execute_in_state_observed(cpu, bus, &contract, &[], trace, Some(fuel::admission), true);
    Stage {
        result,
        writes: bus.end_write_journal(),
        events: bus.finish_decision_observer(),
        ssp_after: cpu.ssp,
    }
}

fn sequence(
    rom: &[u8],
    image_index: usize,
    scratch_pattern: u8,
    s: &Stimulus,
    allowed: &[&str],
) -> Sequence {
    let decision_contract = stateful::contract(0x122C, 0x12FC);
    let (mut cpu, mut bus) = seed_machine(rom, &decision_contract, scratch_pattern);
    seed(&mut cpu, &mut bus, s);
    bus.configure_scoped_access(ranges(), 8192);
    let mut sequence = Sequence {
        image_index,
        scratch_pattern,
        checkpoints: Vec::with_capacity(s.calls.len()),
        completed_calls: 0,
        stop_call_index: -1,
    };
    let mut conditional_dependency = false;
    for input in &s.calls {
        let vtec_before = stateful::snapshot(&cpu, &mut bus);
        let fuel_before = fuel::state(&cpu, &mut bus);
        let mut cp = Checkpoint {
            index: input.index,
            status: NOT_RUN,
            conditional_dependency,
            input: None,
            vtec_before: vtec_before.clone(),
            vtec_after: vtec_before,
            fuel_before: fuel_before.clone(),
            fuel_after: fuel_before,
            tick_runs: vec![],
            tick_writes: vec![],
            rpm_axes: None,
            load_axis: None,
            decision: None,
            boundary12fc: None,
            selection_entry: None,
            selector_before_reader131a: None,
            selection: None,
            selected_origin: None,
            lookup: None,
            lookup_result: None,
            consumer: None,
            consumer_output0140: None,
            request_p1: None,
            request_mirror0127: None,
            selector0127: None,
            used_assumptions: vec![],
            error: None,
        };
        if sequence.stop_call_index >= 0 {
            sequence.checkpoints.push(cp);
            continue;
        }
        cp.input = Some(input.clone());
        let d = &input.decision;
        for (address, value) in [
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
                if d.context == 0 { 8 } else { 0 } | if d.enabled { 16 } else { 0 },
            ),
        ] {
            write_data_u8(&mut cpu, &mut bus, address, value);
        }
        write_data_u16(&mut cpu, &mut bus, 0x11A, d.snapshot011a);
        if !supported_caller(&cpu, &mut bus) {
            cp.status = 1;
            cp.error = Some("unsupported shared direct caller gates".into());
        }
        if cp.status == NOT_RUN {
            bus.set_program_data_ranges(vec![]);
            for (entry, exit, target) in stateful::tick_schedule(d.fast_ticks, d.slow_ticks) {
                let tick = stateful::contract(entry, exit);
                stateful::enter(&mut cpu, &mut bus, &tick);
                write_data_u16(&mut cpu, &mut bus, 0x88, target);
                bus.begin_write_journal();
                let result = execute_in_state_observed(
                    &mut cpu,
                    &mut bus,
                    &tick,
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
        }
        let trace = s.trace_call_indexes.contains(&input.index);
        if cp.status == NOT_RUN {
            let rpm = stage(&mut cpu, &mut bus, "rpmAxes", true, trace);
            cp.status = rpm.result.status;
            cp.error = rpm.result.error.clone();
            cp.rpm_axes = Some(rpm);
        }
        if cp.status == 0 {
            let load = stage(&mut cpu, &mut bus, "loadAxis", true, trace);
            cp.status = load.result.status;
            cp.error = load.result.error.clone();
            cp.load_axis = Some(load);
        }
        if cp.status == 0 {
            stateful::enter(&mut cpu, &mut bus, &decision_contract);
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
            cp.used_assumptions = result.used_assumptions.clone();
            conditional_dependency |= !cp.used_assumptions.is_empty();
            cp.conditional_dependency = conditional_dependency;
            cp.status = result.status;
            cp.error = result.error.clone();
            cp.decision = Some(Stage {
                result,
                writes: bus.end_write_journal(),
                events: bus.finish_decision_observer(),
                ssp_after: cpu.ssp,
            });
        }
        if cp.status == 0 {
            cp.boundary12fc = Some(boundary(&cpu, &mut bus));
            cp.selector_before_reader131a = Some(read_data_u8(&cpu, &mut bus, 0x127));
            if cpu.pc != 0x12FC || !supported_caller(&cpu, &mut bus) {
                cp.status = 1;
                cp.error =
                    Some("decision did not reach supported continuous fuel caller boundary".into());
            }
        }
        // No CPU/RAM/stack/port/register write by this task between the
        // completed decision and these three continuations. Only observation
        // journals and scoped code/program-data admission are changed.
        if cp.status == 0 {
            cp.selection_entry = Some(boundary(&cpu, &mut bus));
            let selection = stage(&mut cpu, &mut bus, "selection", false, trace);
            cp.status = selection.result.status;
            cp.error = selection.result.error.clone();
            cp.selection = Some(selection);
        }
        if cp.status == 0 {
            cp.selected_origin = Some(read_data_u16(&cpu, &mut bus, 0x88));
            let lookup = stage(&mut cpu, &mut bus, "lookup", false, trace);
            cp.status = lookup.result.status;
            cp.error = lookup.result.error.clone();
            cp.lookup = Some(lookup);
        }
        if cp.status == 0 {
            cp.lookup_result = Some(read_data_u16(&cpu, &mut bus, 0x104));
            let consumer = stage(&mut cpu, &mut bus, "consumer", false, trace);
            cp.status = consumer.result.status;
            cp.error = consumer.result.error.clone();
            cp.consumer = Some(consumer);
        }
        cp.vtec_after = stateful::snapshot(&cpu, &mut bus);
        cp.fuel_after = fuel::state(&cpu, &mut bus);
        if cp.status == 0 {
            cp.consumer_output0140 = Some(read_data_u16(&cpu, &mut bus, 0x140));
            cp.request_p1 = Some(cp.vtec_after.p1_output_data & 1 != 0);
            cp.request_mirror0127 = Some(cp.vtec_after.data0127 & 4 != 0);
            cp.selector0127 = Some(cp.vtec_after.data0127 & 2 != 0);
            sequence.completed_calls += 1;
        } else {
            sequence.stop_call_index = input.index as i32;
        }
        sequence.checkpoints.push(cp);
    }
    sequence
}

pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let stimulus = r
        .vtec_fuel_chain
        .as_ref()
        .ok_or("missing VTEC-fuel stimulus")?;
    let allowed: Vec<_> = r.allow_assumptions.iter().map(String::as_str).collect();
    response.entry_contracts = entry_contracts();
    response.vtec_fuel_sequences = Some(
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::runner::SliceContract;

    fn seam_contract(entry: u16, exit: u16) -> SliceContract {
        SliceContract {
            entry_pc: entry,
            exit_pcs: vec![exit],
            code_ranges: vec![[entry as u32, exit as u32]],
            psw: 0x0101,
            lrb: 0x20,
            usp: 0x280,
            instruction_budget: 8,
            data_seeds: vec![],
            output_addresses: vec![],
            program_read_range: None,
        }
    }
    fn toy() -> (Cpu, Bus) {
        let mut rom = vec![0; 32768];
        // Entirely invented two-fragment program: write shared off-page byte,
        // leave ZF set, then a later fragment reads it and stores an output.
        // This is not copied from any OEM procedure.
        rom[0x100..0x10A].copy_from_slice(&[
            0x77, 0x02, // LB A,#2
            0xD4, 0x27, // STB A,off 27 -> DATA0127 in LRB=0020
            0x77, 0x00, // LB A,#0; ZF differs from the entry initializer
            0xF4, 0x27, // LB A,off 27
            0xD4, 0x40, // STB A,off 40 -> DATA0140
        ]);
        let (cpu, mut bus) = seed_machine(&rom, &seam_contract(0x100, 0x106), 0);
        bus.configure_scoped_access(
            vec![
                [0, 8],
                [0x88, 0x90],
                [0x100, 0x108],
                [0x127, 0x128],
                [0x140, 0x141],
            ],
            64,
        );
        (cpu, bus)
    }

    #[test]
    fn invented_writer_to_reader_uses_one_machine_without_host_selector_injection() {
        let (mut cpu, mut bus) = toy();
        let first = execute_in_state_observed(
            &mut cpu,
            &mut bus,
            &seam_contract(0x100, 0x106),
            &[],
            true,
            None,
            true,
        );
        assert_eq!(first.status, 0, "{:?}", first.error);
        let before = boundary(&cpu, &mut bus);
        assert_eq!(before.pc, 0x106);
        assert_ne!(before.psw & Cpu::PSW_ZF_BIT, 0);
        assert_eq!(read_data_u8(&cpu, &mut bus, 0x127), 2);
        let entry = boundary(&cpu, &mut bus);
        assert_eq!(before, entry);
        let second = execute_in_state_observed(
            &mut cpu,
            &mut bus,
            &seam_contract(0x106, 0x10A),
            &[],
            true,
            None,
            true,
        );
        assert_eq!(second.status, 0, "{:?}", second.error);
        assert_eq!(read_data_u8(&cpu, &mut bus, 0x140), 2);
    }

    #[test]
    fn boundary_guard_catches_reinitialization_even_when_final_number_matches() {
        let (mut cpu, mut bus) = toy();
        let first = execute_in_state_observed(
            &mut cpu,
            &mut bus,
            &seam_contract(0x100, 0x106),
            &[],
            false,
            None,
            true,
        );
        assert_eq!(first.status, 0);
        let producer_boundary = boundary(&cpu, &mut bus);
        // Deliberate bad host initializer, as in an accidental second task.
        stateful::enter(&mut cpu, &mut bus, &seam_contract(0x106, 0x10A));
        let consumer_entry = boundary(&cpu, &mut bus);
        assert_ne!(producer_boundary, consumer_entry);
        assert_eq!(read_data_u8(&cpu, &mut bus, 0x127), 2);
        let second = execute_in_state_observed(
            &mut cpu,
            &mut bus,
            &seam_contract(0x106, 0x10A),
            &[],
            false,
            None,
            true,
        );
        assert_eq!(second.status, 0);
        assert_eq!(read_data_u8(&cpu, &mut bus, 0x140), 2);
    }
}
