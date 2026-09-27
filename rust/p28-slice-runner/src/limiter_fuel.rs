//! M2n fixed decision and native fuel gate on one CPU/RAM. No mask/pin consumer.
use crate::{
    acquisition::enter_with_observer,
    adaptive::Stage,
    bus::Bus,
    cpu::Cpu,
    exec::{read_data_u8, write_data_u16, write_data_u8},
    fuel, fuel_factor, limiter,
    protocol::{Request, Response},
    runner::seed_machine,
    vtec_fuel::{boundary, CpuBoundary},
};
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Initial {
    pub fuel: fuel::State,
    pub data0124: u8,
    #[serde(rename = "data012b")]
    pub data012b: u8,
    pub data01d7: u8,
    pub producer_mode012c: u8,
    pub producer_selector012f: u8,
    pub hysteresis0130: u8,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Call {
    pub index: u32,
    pub raw_period: u16,
    pub raw_load: u8,
    pub raw_map0_rpm: u8,
    pub raw_map1_rpm: u8,
    pub sources: fuel_factor::Sources,
}
impl Call {
    fn fuel(&self) -> fuel_factor::Call {
        fuel_factor::Call {
            index: self.index,
            raw_load: self.raw_load,
            raw_map0_rpm: self.raw_map0_rpm,
            raw_map1_rpm: self.raw_map1_rpm,
            sources: self.sources.clone(),
        }
    }
}
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Stimulus {
    pub format_version: u32,
    pub initial_state: Initial,
    pub calls: Vec<Call>,
    pub trace_call_indexes: Vec<u32>,
}
#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct State {
    pub data0124: u8,
    pub data012b: u8,
    pub data01d7: u8,
}
fn state(cpu: &Cpu, bus: &mut Bus) -> State {
    State {
        data0124: read_data_u8(cpu, bus, 0x124),
        data012b: read_data_u8(cpu, bus, 0x12B),
        data01d7: read_data_u8(cpu, bus, 0x1D7),
    }
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Checkpoint {
    pub index: u32,
    pub status: i32,
    pub input: Option<Call>,
    pub input_writes: Vec<[u32; 3]>,
    pub state_before: State,
    pub state_after_decision: State,
    pub state_after: State,
    pub decision_entry: Option<CpuBoundary>,
    pub decision_exit: Option<CpuBoundary>,
    pub transition_to_decision_writes: Vec<[u32; 3]>,
    pub handoff_to_decision: Option<CpuBoundary>,
    pub decision: Option<Stage>,
    pub decision_accesses: Vec<[u32; 5]>,
    pub fuel: fuel_factor::Checkpoint,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Sequence {
    pub scratch_pattern: u8,
    pub checkpoints: Vec<Checkpoint>,
}
pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .limiter_fuel_gate_chain
        .as_ref()
        .ok_or("M2n stimulus required")?;
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
        || s.initial_state.fuel.load_index > 8
        || s.initial_state.fuel.map0_rpm_index > 18
        || s.initial_state.fuel.map1_rpm_index > 18
        || s.initial_state.fuel.consumer_output0140 != 0
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
        return Err("invalid bounded strict M2n fixed-context contract".into());
    }
    Ok(())
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({
    "id":"limiterFuelGateChain", "formatVersion":1, "decisionEntry":0x1966,"decisionExit":0x1A38,"decisionBudget":96,
    "fixedContext":{"data011b":128,"data0121":128,"p4Bit0":false},"fixedOperands":[[0x1967,16],[0x196A,16]],
    "callerGate":[0x217A,0x2194],"gateReader":[0x21F5,0x124,5],"gateWriter":[0x1A23,0x124,5],"bit4Writer":0x1A28,
    "hostTransitionWrites":[[2,16,0x20],[4,16,0x0101],[0x8E,16,0x280]],
    "fuelContract":fuel_factor::entry_contracts()[0],"sharedState":[0x124,0x12B,0x1D7,0x130,0x140,0x158,0x3A2,0x3B4],
    "maskConsumer":"5585..5596 NotRun;018F/012A/P2 not accessed", "adaptive":"487B..48F5/ticks NotRun; RAM thresholds not inputs",
    "schedule":"Snapshots->decision->fuel prefix->factor->217A->2194..2204; scripted routine ABI, not recovered scheduler",
    "assumptions":[],"physicalRpmAvailable":false,"stop":"BeforeInstruction2204"})]
}
pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r.limiter_fuel_gate_chain.as_ref().expect("validated");
    let mut sequences = vec![];
    for &pattern in &r.scratch_patterns {
        let (mut cpu, mut bus) = seed_machine(&r.images[0].rom, &limiter::contract(false), pattern);
        cpu.ssp = 0x7FE;
        // 0121 initialized exactly once: limiter bit7 set, fuel bit6 clear.
        fuel::seed_state_with_0121(&mut cpu, &mut bus, &s.initial_state.fuel, 128);
        for (a, v) in [
            (0x124, s.initial_state.data0124),
            (0x12B, s.initial_state.data012b),
            (0x1D7, s.initial_state.data01d7),
            (0x12C, s.initial_state.producer_mode012c),
            (0x12F, s.initial_state.producer_selector012f),
            (0x130, s.initial_state.hysteresis0130),
            (0x11B, 128),
            (0x15F, 0),
        ] {
            write_data_u8(&mut cpu, &mut bus, a, v);
        }
        fuel_factor::set_sources(&mut cpu, &mut bus, &fuel_factor::Sources::zero());
        bus.observe_limiter_p4(Some(0));
        let mut ranges = fuel_factor::data_ranges();
        ranges.extend([[0x2C, 0x2D], [0x11B, 0x11C], [0x1D7, 0x1D8], [0xC4, 0xC6]]);
        let mut stopped = false;
        let mut checkpoints = vec![];
        for c in &s.calls {
            bus.configure_scoped_access(ranges.clone(), 4096);
            let before = state(&cpu, &mut bus);
            let f = fuel_factor::checkpoint(&cpu, &mut bus, &c.fuel());
            let mut row = Checkpoint {
                index: c.index,
                status: 4,
                input: None,
                input_writes: vec![],
                state_before: before.clone(),
                state_after_decision: before.clone(),
                state_after: before,
                decision_entry: None,
                decision_exit: None,
                transition_to_decision_writes: vec![],
                handoff_to_decision: None,
                decision: None,
                decision_accesses: vec![],
                fuel: f,
            };
            if !stopped {
                row.input = Some(c.clone());
                fuel_factor::apply_inputs(&mut cpu, &mut bus, &c.fuel(), &mut row.fuel);
                row.input_writes = row.fuel.input_writes.clone();
                bus.begin_write_journal();
                write_data_u16(&mut cpu, &mut bus, 0xC4, c.raw_period);
                row.input_writes.extend(bus.end_write_journal());
                row.handoff_to_decision = Some(boundary(&cpu, &mut bus));
                enter_with_observer(&mut cpu, &mut bus, &limiter::contract(false), |w| {
                    row.transition_to_decision_writes.push(w)
                });
                row.decision_entry = Some(boundary(&cpu, &mut bus));
                let (result, writes, events, accesses) =
                    limiter::execute_decision(&mut cpu, &mut bus);
                row.status = result.status;
                row.decision = Some(Stage {
                    result,
                    writes,
                    events,
                    ssp_after: cpu.ssp,
                });
                row.decision_accesses = accesses;
                row.decision_exit = Some(boundary(&cpu, &mut bus));
                row.state_after_decision = state(&cpu, &mut bus);
                // The fuel stage consumes the native combined byte; no host state repair.
                row.fuel.mode_before = row.state_after_decision.data012b;
                if row.status == 0 {
                    row.fuel.prefix_transitions = Some(vec![]);
                    fuel_factor::execute_checkpoint(&mut cpu, &mut bus, &mut row.fuel, true);
                    row.status = row.fuel.status;
                } else {
                    row.fuel.input = None;
                    row.fuel.prefix.state_after_inputs = None;
                }
                fuel_factor::finish_checkpoint(&cpu, &mut bus, &mut row.fuel);
                bus.configure_scoped_access(ranges.clone(), 4096);
                row.state_after = state(&cpu, &mut bus);
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
    response.limiter_fuel_sequences = Some(sequences);
    Ok(response)
}
