//! M2o: explicit native adaptive/tick fragments followed by the shared M2n continuation.
use crate::{
    acquisition::enter_with_observer,
    adaptive,
    bus::Bus,
    cpu::Cpu,
    exec::{read_data_u16, read_data_u8, write_data_u16, write_data_u8},
    fuel_factor, limiter, limiter_fuel,
    protocol::{Request, Response},
    runner::seed_machine,
    vtec_fuel::{boundary, CpuBoundary},
};
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Initial {
    pub joint: limiter_fuel::Initial,
    pub ram_cut: u16,
    pub ram_resume: u16,
    pub timer: u8,
    pub counter: u8,
    pub ie: u16,
    pub restore_ie: u16,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Call {
    pub fuel: limiter_fuel::Call,
    pub raw00ce: u16,
    pub raw_d9: u8,
    pub bank1: bool,
    pub reset217: bool,
    pub reset214: bool,
    pub mode212: bool,
    pub enable223: bool,
    pub fixed_source: bool,
    pub timer_ticks: u8,
    pub counter_ticks: u8,
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
    pub ram_cut: u16,
    pub ram_resume: u16,
    pub timer: u8,
    pub counter: u8,
    pub ie: u16,
    pub restore_ie: u16,
    pub sources: [u8; 6],
}
fn state(cpu: &Cpu, bus: &mut Bus) -> State {
    State {
        ram_cut: read_data_u16(cpu, bus, 0x1A4),
        ram_resume: read_data_u16(cpu, bus, 0x1A6),
        timer: read_data_u8(cpu, bus, 0x1D5),
        counter: read_data_u8(cpu, bus, 0x1CE),
        ie: bus.adaptive_ie().expect("once-only IE"),
        restore_ie: read_data_u16(cpu, bus, 0xF8),
        sources: [0x21F, 0x217, 0x214, 0x212, 0x223, 0x11B].map(|a| read_data_u8(cpu, bus, a)),
    }
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Fragment {
    pub before: CpuBoundary,
    pub entry: CpuBoundary,
    pub exit: CpuBoundary,
    pub transition_writes: Vec<[u32; 3]>,
    pub stage: adaptive::Stage,
    pub accesses: Vec<[u32; 5]>,
    pub tick_target: Option<u16>,
}
fn fragment(cpu: &mut Cpu, bus: &mut Bus, tick: Option<u16>) -> Fragment {
    let c = adaptive::contract(tick.is_some());
    // Observation of an incoming composition ABI; actual execution still uses historical ranges.
    let mut observation_ranges = ranges();
    observation_ranges.extend([
        [cpu.bank_base(), cpu.bank_base() + 8],
        [0x80 + cpu.scb() * 8, 0x88 + cpu.scb() * 8],
    ]);
    bus.configure_scoped_access(observation_ranges, 4096);
    let before = boundary(cpu, bus);
    bus.configure_scoped_access(ranges(), 4096);
    let mut writes = vec![];
    enter_with_observer(cpu, bus, &c, |w| writes.push(w));
    if let Some(address) = tick {
        write_data_u16(cpu, bus, 0x88, address);
        writes.push([0x88, 16, u32::from(address)]);
    }
    bus.set_program_data_ranges(if tick.is_some() {
        vec![]
    } else {
        vec![[0x6493, 0x64AB]]
    });
    let entry = boundary(cpu, bus);
    bus.begin_native_accesses();
    let stage = if tick.is_some() {
        adaptive::execute_tick_in_state(cpu, bus)
    } else {
        adaptive::execute_producer_in_state(cpu, bus)
    };
    let accesses = bus.end_native_accesses();
    let exit = boundary(cpu, bus);
    Fragment {
        before,
        entry,
        exit,
        transition_writes: writes,
        stage,
        accesses,
        tick_target: tick,
    }
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Checkpoint {
    pub index: u32,
    pub status: i32,
    pub input: Option<Call>,
    pub snapshot_writes: Vec<[u32; 3]>,
    pub state_before: State,
    pub state_after_producer: Option<State>,
    pub state_after: State,
    pub ticks: Vec<Fragment>,
    pub producer: Option<Fragment>,
    pub joint: limiter_fuel::Checkpoint,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Sequence {
    pub scratch_pattern: u8,
    pub checkpoints: Vec<Checkpoint>,
}
pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .adaptive_limiter_fuel_gate_chain
        .as_ref()
        .ok_or("M2o stimulus required")?;
    validate_stimulus(r, s)
}
pub(crate) fn validate_stimulus(r: &Request, s: &Stimulus) -> Result<(), String> {
    let f = &s.initial_state.joint.fuel;
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
        || s.calls.iter().enumerate().any(|(i, c)| {
            c.fuel.index as usize != i
                || c.fuel.sources.source0144 > 255
                || u16::from(c.timer_ticks) + u16::from(c.counter_ticks) > 32
        })
        || f.load_index > 8
        || f.map0_rpm_index > 18
        || f.map1_rpm_index > 18
        || f.consumer_output0140 != 0
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
        return Err("invalid bounded strict M2o contract".into());
    }
    Ok(())
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![
        serde_json::json!({"id":"adaptiveLimiterFuelGateChain","formatVersion":1,
        "adaptiveContract":adaptive::entry_contracts()[0],"continuationContract":limiter_fuel::entry_contracts()[0],
        "sourceMasks":[[0x21F,2],[0x217,32],[0x214,1],[0x212,32],[0x223,4],[0x11B,128]],
        "context":"Frozen P4.0=0; masked011B.7 selects fixed/RAM;0121=80 once",
        "schedule":"Snapshots->ticks01D5->ticks01CE->487B..48F5->1966..1A38->lookup0140->factor0158->217A->21F5->03A2/03B4; scripted ABI, not ECU scheduler",
        "ownership":"One CPU/RAM; thresholds native Written or retained InitialHistory/Held; no mask5585/P2",
        "assumptions":[],"physicalRpmAvailable":false,"stop":"BeforeInstruction2204"}),
    ]
}
fn ranges() -> Vec<[u16; 2]> {
    let mut r = limiter_fuel::data_ranges();
    r.extend(adaptive::producer_ranges());
    r
}
pub(crate) fn initialize(rom: &[u8], pattern: u8, initial: &Initial) -> (Cpu, Bus) {
    let (mut cpu, mut bus) = seed_machine(rom, &limiter::contract(false), pattern);
    cpu.ssp = 0x7FE;
    limiter_fuel::initialize(&mut cpu, &mut bus, &initial.joint, 0);
    for (a, v) in [
        (0x1A4, initial.ram_cut),
        (0x1A6, initial.ram_resume),
        (0xF8, initial.restore_ie),
    ] {
        write_data_u16(&mut cpu, &mut bus, a, v);
    }
    for (a, v) in [(0x1D5, initial.timer), (0x1CE, initial.counter)] {
        write_data_u8(&mut cpu, &mut bus, a, v);
    }
    bus.set_adaptive_ie(Some(initial.ie));
    (cpu, bus)
}
pub(crate) fn checkpoint(cpu: &Cpu, bus: &mut Bus, c: &Call) -> Checkpoint {
    bus.configure_scoped_access(ranges(), 4096);
    let before = state(cpu, bus);
    let row = Checkpoint {
        index: c.fuel.index,
        status: 4,
        input: None,
        snapshot_writes: vec![],
        state_before: before.clone(),
        state_after_producer: None,
        state_after: before,
        ticks: vec![],
        producer: None,
        joint: limiter_fuel::checkpoint(cpu, bus, &c.fuel),
    };
    row
}
pub(crate) fn execute_checkpoint(cpu: &mut Cpu, bus: &mut Bus, c: &Call, row: &mut Checkpoint) {
    bus.configure_scoped_access(ranges(), 4096);
    let mut stopped = false;
    row.input = Some(c.clone());
    limiter_fuel::apply_inputs(cpu, bus, &c.fuel, &mut row.joint);
    bus.begin_write_journal();
    for (a, mask, on) in [
        (0x21F, 2, c.bank1),
        (0x217, 32, c.reset217),
        (0x214, 1, c.reset214),
        (0x212, 32, c.mode212),
        (0x223, 4, c.enable223),
        (0x11B, 128, c.fixed_source),
    ] {
        let v = read_data_u8(cpu, bus, a);
        write_data_u8(cpu, bus, a, (v & !mask) | if on { mask } else { 0 });
    }
    write_data_u16(cpu, bus, 0xCE, c.raw00ce);
    write_data_u8(cpu, bus, 0xD9, c.raw_d9);
    row.snapshot_writes = bus.end_write_journal();
    for (a, n) in [(0x1D5, c.timer_ticks), (0x1CE, c.counter_ticks)] {
        for _ in 0..n {
            if stopped {
                break;
            }
            let f = fragment(cpu, bus, Some(a));
            row.status = f.stage.result.status;
            stopped = row.status != 0;
            row.ticks.push(f);
        }
    }
    if !stopped {
        let f = fragment(cpu, bus, None);
        row.status = f.stage.result.status;
        stopped = row.status != 0;
        row.producer = Some(f);
        row.state_after_producer = Some(state(cpu, bus));
    }
    if !stopped {
        limiter_fuel::execute_checkpoint(cpu, bus, &mut row.joint);
        row.status = row.joint.status;
    } else {
        row.joint.input = None;
        row.joint.fuel.input = None;
        row.joint.fuel.prefix.state_after_inputs = None;
        fuel_factor::finish_checkpoint(cpu, bus, &mut row.joint.fuel);
    }
    bus.configure_scoped_access(ranges(), 4096);
    row.state_after = state(cpu, bus);
}
pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r
        .adaptive_limiter_fuel_gate_chain
        .as_ref()
        .expect("validated");
    let mut sequences = vec![];
    for &pattern in &r.scratch_patterns {
        let (mut cpu, mut bus) = initialize(&r.images[0].rom, pattern, &s.initial_state);
        let mut stopped = false;
        let mut checkpoints = vec![];
        for c in &s.calls {
            let mut row = checkpoint(&cpu, &mut bus, c);
            if !stopped {
                execute_checkpoint(&mut cpu, &mut bus, c, &mut row);
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
    response.adaptive_fuel_sequences = Some(sequences);
    Ok(response)
}
