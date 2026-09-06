//! One CPU/Bus lifetime: native Acquire -> scheduled ticks -> G -> F -> decision.
//! This module has no samples/T/Code/threshold/request calculation.
use crate::{
    acquisition,
    bus::{Bus, CaptureObservation},
    cpu::Cpu,
    exec::{read_data_u16, read_data_u8, write_data_u16, write_data_u8},
    instruction_forms::{acquisition_form_admission, producer_form_admission, FormAdmission},
    protocol::{CaseResult, Request, Response, ADD_ASSUMPTION, PRODUCER_ADD_ASSUMPTION},
    runner::{compact_contract, execute_in_state_observed, seed_machine, SliceContract},
    stateful, stateful_forms,
};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct RawInputs {
    #[serde(rename = "raw00CC")]
    pub raw00cc: u8,
    #[serde(rename = "raw00D9")]
    pub raw00d9: u8,
    pub snapshot0119: u8,
    #[serde(rename = "snapshot011A")]
    pub snapshot011a: u16,
    #[serde(rename = "snapshot011C")]
    pub snapshot011c: u8,
    pub raw0132: u8,
    pub raw0199: u8,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct State {
    pub acquisition: acquisition::PersistentState,
    pub decision: stateful::State,
    #[serde(rename = "data011E")]
    pub data011e: u8,
    #[serde(rename = "data00B8")]
    pub data00b8: u8,
    pub code: u8,
    pub raw: RawInputs,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Event {
    pub index: u32,
    pub tmr2: u16,
    pub irqh: u8,
    pub tcon2: u8,
    pub slot: u8,
    pub run_decision: bool,
    pub context: u8,
    pub enabled: bool,
    pub raw: RawInputs,
    pub fast_ticks: u8,
    pub slow_ticks: u8,
}
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Stimulus {
    pub format_version: u32,
    pub initial_state: State,
    pub events: Vec<Event>,
    pub trace_event_indexes: Vec<u32>,
}
#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct Architecture {
    pub pc: u16,
    pub accumulator: u16,
    pub lrb: u16,
    pub psw: u16,
    pub ssp: u16,
    pub banks: Vec<u8>,
    pub pointing: Vec<u8>,
    pub stack_word: u16,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Stage {
    pub id: &'static str,
    pub status: i32,
    pub state_before: State,
    pub state_at_entry: State,
    pub state_after: State,
    pub architecture_before: Architecture,
    pub architecture_at_entry: Architecture,
    pub architecture_after: Architecture,
    pub execution: Option<CaseResult>,
    pub native_writes: Vec<[u32; 3]>,
    pub peripheral_accesses: Vec<[u32; 4]>,
    pub gate_events: Vec<[u32; 8]>,
    /// [entry,target,exit,status,steps,sspBefore,sspAfter] per native body.
    pub tick_runs: Vec<[u32; 7]>,
    pub cumulative_assumptions: Vec<String>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Checkpoint {
    pub index: u32,
    pub input: Event,
    pub state_before: State,
    pub state_after_inputs: State,
    pub caller_writes: Vec<[u32; 3]>,
    pub stages: Vec<Stage>,
    pub state_after: State,
    pub software_request: Option<bool>,
    pub request_mirror: Option<bool>,
    pub selection_status: Option<bool>,
    pub ever_written_mask: u8,
    pub slot_write_counts: [u32; 6],
    pub cumulative_assumptions: Vec<String>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Sequence {
    pub image_index: usize,
    pub scratch_pattern: u8,
    pub checkpoints: Vec<Checkpoint>,
    pub completed_events: u32,
    pub completed_decisions: u32,
    pub stop_event_index: i32,
}

pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .integrated_chain
        .as_ref()
        .ok_or("integrated stimulus required")?;
    if r.synthetic.is_some()
        || r.producer_cases.is_some()
        || r.acquisition_sequence.is_some()
        || r.stateful_vtec.is_some()
        || r.scratch_patterns != [0, 85, 170]
        || r.images[0].id != "baseline"
        || !(r.images.len() == 1
            || r.images.len() == 3
                && r.images[1].id == "intermediate"
                && r.images[2].id == "derived")
        || r.images.iter().any(|i| i.rom.len() != 32768)
        || s.format_version != 1
        || s.events.is_empty()
        || s.events.len() > 256
        || s.trace_event_indexes.len() > 8
        || s.events.iter().enumerate().any(|(i, e)| {
            e.index as usize != i
                || e.slot > 5
                || e.context > 1
                || e.fast_ticks > 32
                || e.slow_ticks > 32
        })
        || s.trace_event_indexes
            .iter()
            .any(|i| *i as usize >= s.events.len())
        || s.trace_event_indexes
            .iter()
            .collect::<std::collections::HashSet<_>>()
            .len()
            != s.trace_event_indexes.len()
    {
        return Err("invalid bounded integrated capture-to-decision contract".into());
    }
    Ok(())
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({
        "id":"integratedCaptureVtec","version":1,"initialState":"OncePerImageScratchSequence",
        "schedule":["ScriptedInputs","Acquisition","NativeCounterBodies","ScheduledG","ScheduledF","ScheduledDecision"],
        "boundaries":[[0x56BE,0x5719],[0x5BD0,0x5BD9],[0x3CEB,0x3CF3],[0x0772,0x07A5],[0x07C7,0x0822],[0x122C,0x12FC]],
        "budgets":[128,4,4,192,128,512],"entryLrb":[0x21,0x20,0x20,0x40,0x40,0x20],
        "entryPsw":[0x1102,0x0101,0x0101,0x1101,0x1101,0x0101],"entryUsp":[0x280,0x280,0x280,0x180,0x180,0x280],
        "sspInitial":0x7FE,"sspReseed":false,"data011EMask":24,
        "stageInputs":"NativeSamplesToGToTAndSToFToCodeToPersistentDecision",
        "captureScope":"AcquisitionOnly","p1Scope":"DecisionOnlyLatchAlwaysRetained",
        "p1Mode":"AllOutputDataRegisterOnlyNoExternalBus","tickUnits":"NativeBodyCallsNotMilliseconds",
        "permissions":[PRODUCER_ADD_ASSUMPTION,ADD_ASSUMPTION,stateful_forms::SUBB_OFF_ASSUMPTION],
        "terminalStop":"NoLaterStagesOrEventsOrInputs","traceLimit":128,"physicalRpmAvailable":false,
        "hardwareFullBoot":"NotRun","guiR3":"paused/NotRun"
    })]
}
fn raw_writes(raw: &RawInputs) -> Vec<[u32; 3]> {
    vec![
        [0xCC, 8, raw.raw00cc as u32],
        [0xD9, 8, raw.raw00d9 as u32],
        [0x119, 8, raw.snapshot0119 as u32],
        [0x11A, 16, raw.snapshot011a as u32],
        [0x11C, 8, raw.snapshot011c as u32],
        [0x132, 8, raw.raw0132 as u32],
        [0x199, 8, raw.raw0199 as u32],
    ]
}
fn apply_writes(cpu: &mut Cpu, bus: &mut Bus, writes: &[[u32; 3]]) {
    for w in writes {
        if w[1] == 16 {
            write_data_u16(cpu, bus, w[0] as u16, w[2] as u16);
        } else {
            write_data_u8(cpu, bus, w[0] as u16, w[2] as u8);
        }
    }
}
fn snapshot(cpu: &Cpu, bus: &mut Bus) -> State {
    State {
        acquisition: acquisition::snapshot(cpu, bus),
        decision: stateful::snapshot(cpu, bus),
        data011e: read_data_u8(cpu, bus, 0x11E),
        data00b8: read_data_u8(cpu, bus, 0xB8),
        code: read_data_u8(cpu, bus, 0x133),
        raw: RawInputs {
            raw00cc: read_data_u8(cpu, bus, 0xCC),
            raw00d9: read_data_u8(cpu, bus, 0xD9),
            snapshot0119: read_data_u8(cpu, bus, 0x119),
            snapshot011a: read_data_u16(cpu, bus, 0x11A),
            snapshot011c: read_data_u8(cpu, bus, 0x11C),
            raw0132: read_data_u8(cpu, bus, 0x132),
            raw0199: read_data_u8(cpu, bus, 0x199),
        },
    }
}
fn architecture(cpu: &Cpu, bus: &mut Bus) -> Architecture {
    Architecture {
        pc: cpu.pc,
        accumulator: cpu.a,
        lrb: cpu.lrb,
        psw: cpu.psw_u16(),
        ssp: cpu.ssp,
        banks: (0x100..0x110)
            .chain(0x200..0x208)
            .map(|a| read_data_u8(cpu, bus, a))
            .collect(),
        pointing: (0x88..0x98).map(|a| read_data_u8(cpu, bus, a)).collect(),
        stack_word: read_data_u16(cpu, bus, 0x7FE),
    }
}
fn empty_stage(id: &'static str, cpu: &Cpu, bus: &mut Bus, cumulative: &[String]) -> Stage {
    let state = snapshot(cpu, bus);
    let arch = architecture(cpu, bus);
    Stage {
        id,
        status: 4,
        state_before: state.clone(),
        state_at_entry: state.clone(),
        state_after: state,
        architecture_before: arch.clone(),
        architecture_at_entry: arch.clone(),
        architecture_after: arch,
        execution: None,
        native_writes: vec![],
        peripheral_accesses: vec![],
        gate_events: vec![],
        tick_runs: vec![],
        cumulative_assumptions: cumulative.to_vec(),
    }
}
fn disposition(run: &CaseResult) -> i32 {
    if run.status == 1
        && run
            .error
            .as_deref()
            .is_some_and(|e| e.starts_with("unimplemented in reviewed"))
    {
        5
    } else {
        run.status
    }
}
fn retain(cumulative: &mut Vec<String>, run: &CaseResult) {
    for a in &run.used_assumptions {
        if !cumulative.contains(a) {
            cumulative.push(a.clone());
        }
    }
    cumulative.sort();
}
fn execute_stage(
    id: &'static str,
    cpu: &mut Cpu,
    bus: &mut Bus,
    mut c: SliceContract,
    event: &Event,
    permissions: &[&str],
    selected: bool,
    policy: fn(&crate::decoder::Decoded) -> FormAdmission,
    cumulative: &mut Vec<String>,
) -> Stage {
    let mut stage = empty_stage(id, cpu, bus, cumulative);
    // Reuse execution boundaries only, NEVER isolated task seeds or output copies.
    c.data_seeds.clear();
    c.output_addresses.clear();
    acquisition::enter(cpu, bus, &c);
    bus.set_p1_access(id == "Decision");
    bus.set_program_data_ranges(if id == "Decision" {
        vec![[0x6542, 0x6566], [0x60FA, 0x60FB]]
    } else {
        vec![]
    });
    if id == "Acquisition" {
        write_data_u8(cpu, bus, 0xA2, event.slot);
        bus.observe_capture(Some(CaptureObservation {
            tmr2: event.tmr2,
            irqh: event.irqh,
            tcon2: event.tcon2,
        }));
    }
    if id == "Decision" {
        bus.start_decision_observer();
    }
    stage.architecture_at_entry = architecture(cpu, bus);
    stage.state_at_entry = snapshot(cpu, bus);
    bus.begin_write_journal();
    let run = execute_in_state_observed(cpu, bus, &c, permissions, selected, Some(policy), true);
    stage.native_writes = bus.end_write_journal();
    stage.peripheral_accesses = bus.peripheral_accesses();
    bus.observe_capture(None);
    if id == "Decision" {
        stage.gate_events = bus
            .finish_decision_observer()
            .into_iter()
            .filter(|e| stateful::GATE_PCS.contains(&(e[0] as u16)))
            .collect();
    }
    bus.set_p1_access(false);
    retain(cumulative, &run);
    stage.status = disposition(&run);
    stage.execution = Some(run);
    stage.state_after = snapshot(cpu, bus);
    stage.architecture_after = architecture(cpu, bus);
    stage.cumulative_assumptions = cumulative.clone();
    stage
}
fn ticks(
    cpu: &mut Cpu,
    bus: &mut Bus,
    event: &Event,
    selected: bool,
    cumulative: &[String],
) -> Stage {
    let mut stage = empty_stage("NativeCounterBodies", cpu, bus, cumulative);
    let schedule = stateful::tick_schedule(event.fast_ticks, event.slow_ticks);
    if schedule.is_empty() {
        return stage;
    }
    bus.set_p1_access(false);
    bus.set_program_data_ranges(vec![]);
    let mut aggregate = CaseResult {
        status: 0,
        used_assumptions: vec![],
        steps: 0,
        stop_pc: cpu.pc,
        outputs: vec![],
        program_reads: vec![],
        trace: vec![],
        error: None,
        executed_instruction_bytes: Some(vec![]),
    };
    let mut extents = std::collections::BTreeSet::new();
    for (entry, exit, target) in schedule {
        let c = stateful::contract(entry, exit);
        acquisition::enter(cpu, bus, &c);
        write_data_u16(cpu, bus, 0x88, target);
        if stage.tick_runs.is_empty() {
            stage.architecture_at_entry = architecture(cpu, bus);
        }
        let ssp = cpu.ssp;
        bus.begin_write_journal();
        let run = execute_in_state_observed(
            cpu,
            bus,
            &c,
            &[],
            selected,
            Some(stateful_forms::admission),
            true,
        );
        stage.native_writes.extend(bus.end_write_journal());
        stage.tick_runs.push([
            entry as u32,
            target as u32,
            run.stop_pc as u32,
            disposition(&run) as u32,
            run.steps,
            ssp as u32,
            cpu.ssp as u32,
        ]);
        extents.extend(run.executed_instruction_bytes.clone().unwrap_or_default());
        aggregate.steps += run.steps;
        aggregate.stop_pc = run.stop_pc;
        aggregate.status = run.status;
        aggregate.error = run.error.clone();
        let remaining = 128usize.saturating_sub(aggregate.trace.len());
        aggregate
            .trace
            .extend(run.trace.into_iter().take(remaining));
        if run.status != 0 {
            break;
        }
    }
    aggregate.executed_instruction_bytes = Some(extents.into_iter().collect());
    stage.status = disposition(&aggregate);
    stage.execution = Some(aggregate);
    stage.state_after = snapshot(cpu, bus);
    stage.architecture_after = architecture(cpu, bus);
    stage
}
fn sequence(
    rom: &[u8],
    image_index: usize,
    pattern: u8,
    s: &Stimulus,
    permissions: &[&str],
    extra_trace: Option<u32>,
) -> Sequence {
    let c = acquisition::acquisition_contract();
    let (mut cpu, mut bus) = seed_machine(rom, &c, pattern);
    cpu.ssp = 0x7FE;
    acquisition::seed_persistent_fields(&mut cpu, &mut bus, &s.initial_state.acquisition);
    for (a, v) in stateful::STATE_ADDRESSES
        .into_iter()
        .zip(s.initial_state.decision.bytes())
    {
        if a != 0x22 {
            write_data_u8(&mut cpu, &mut bus, a, v);
        }
    }
    bus.set_p1_output_latch(Some(s.initial_state.decision.p1_output_data));
    bus.set_p1_access(false);
    apply_writes(&mut cpu, &mut bus, &raw_writes(&s.initial_state.raw));
    for (a, v) in [
        (0x11E, s.initial_state.data011e),
        (0xB8, s.initial_state.data00b8),
        (0x133, s.initial_state.code),
    ] {
        write_data_u8(&mut cpu, &mut bus, a, v);
    }
    bus.configure_scoped_access(
        vec![
            [0, 8],
            [0x19, 0x1A],
            [0x22, 0x23],
            [0x3A, 0x3C],
            [0x42, 0x43],
            [0x88, 0x98],
            [0xA2, 0xA3],
            [0xAE, 0xAF],
            [0xB6, 0xB7],
            [0xB8, 0xB9],
            [0xC4, 0xC6],
            [0xCC, 0xCD],
            [0xD9, 0xDA],
            [0xEE, 0xF0],
            [0xF3, 0xF4],
            [0x100, 0x110],
            [0x119, 0x11F + 1],
            [0x127, 0x129],
            [0x131, 0x134],
            [0x136, 0x138],
            [0x198, 0x19A],
            [0x1D8, 0x1DA],
            [0x1DF, 0x1E0],
            [0x200, 0x208],
            [0x217, 0x218],
            [0x231, 0x232],
            [0x360, 0x36C],
            [0x7FE, 0x800],
        ],
        512,
    );
    let mut result = Sequence {
        image_index,
        scratch_pattern: pattern,
        checkpoints: vec![],
        completed_events: 0,
        completed_decisions: 0,
        stop_event_index: -1,
    };
    let mut cumulative = vec![];
    let mut mask = 0;
    let mut counts = [0; 6];
    for e in &s.events {
        let before = snapshot(&cpu, &mut bus);
        let active = result.stop_event_index < 0;
        let selected = s.trace_event_indexes.contains(&e.index) || extra_trace == Some(e.index);
        let mut caller = vec![];
        if active {
            caller = raw_writes(&e.raw);
            caller.push([
                0x11E,
                8,
                ((before.data011e & !24)
                    | if e.context == 0 { 8 } else { 0 }
                    | if e.enabled { 16 } else { 0 }) as u32,
            ]);
            apply_writes(&mut cpu, &mut bus, &caller);
        }
        let after_inputs = snapshot(&cpu, &mut bus);
        let mut stages = vec![];
        let mut live = active;
        for id in ["Acquisition", "NativeCounterBodies", "G", "F", "Decision"] {
            let scheduled = id == "Acquisition" || id == "NativeCounterBodies" || e.run_decision;
            let stage = if !live || !scheduled {
                empty_stage(id, &cpu, &mut bus, &cumulative)
            } else if id == "Acquisition" && after_inputs.acquisition.data011f & 4 != 0 {
                let mut x = empty_stage(id, &cpu, &mut bus, &cumulative);
                x.status = 5;
                x
            } else if id == "NativeCounterBodies" {
                ticks(&mut cpu, &mut bus, e, selected, &cumulative)
            } else {
                let (contract, permission, policy): (
                    SliceContract,
                    Option<&str>,
                    fn(&crate::decoder::Decoded) -> FormAdmission,
                ) = match id {
                    "Acquisition" => (
                        acquisition::acquisition_contract(),
                        None,
                        acquisition_form_admission,
                    ),
                    "G" => (
                        crate::producer::producer_contract(&[0; 14]),
                        Some(PRODUCER_ADD_ASSUMPTION),
                        producer_form_admission,
                    ),
                    "F" => (
                        compact_contract(0, false),
                        Some(ADD_ASSUMPTION),
                        crate::chain_forms::compact_admission,
                    ),
                    _ => (
                        stateful::contract(0x122C, 0x12FC),
                        Some(stateful_forms::SUBB_OFF_ASSUMPTION),
                        stateful_forms::admission,
                    ),
                };
                let allowed: Vec<_> = permission
                    .filter(|p| permissions.contains(p))
                    .into_iter()
                    .collect();
                execute_stage(
                    id,
                    &mut cpu,
                    &mut bus,
                    contract,
                    e,
                    &allowed,
                    selected,
                    policy,
                    &mut cumulative,
                )
            };
            if live
                && scheduled
                && stage.status != 0
                && !(id == "NativeCounterBodies" && stage.status == 4)
            {
                live = false;
                result.stop_event_index = e.index as i32;
            }
            if id == "Acquisition" {
                for w in &stage.native_writes {
                    if w[0] >= 0x360 && w[0] < 0x36C && w[1] == 16 && w[0] & 1 == 0 {
                        let slot = ((w[0] - 0x360) / 2) as usize;
                        counts[slot] += 1;
                        mask |= 1 << slot;
                    }
                }
            }
            stages.push(stage);
        }
        if live {
            result.completed_events += 1;
        }
        let complete = stages[4].status == 0;
        if complete {
            result.completed_decisions += 1;
        }
        let after = snapshot(&cpu, &mut bus);
        result.checkpoints.push(Checkpoint {
            index: e.index,
            input: e.clone(),
            state_before: before,
            state_after_inputs: after_inputs,
            caller_writes: caller,
            stages,
            software_request: complete.then_some(after.decision.p1_output_data & 1 != 0),
            request_mirror: complete.then_some(after.decision.data0127 & 4 != 0),
            selection_status: complete.then_some(after.decision.data0127 & 2 != 0),
            state_after: after,
            ever_written_mask: mask,
            slot_write_counts: counts,
            cumulative_assumptions: cumulative.clone(),
        });
    }
    result
}
pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r
        .integrated_chain
        .as_ref()
        .ok_or("integrated stimulus required")?;
    let permissions: Vec<_> = r.allow_assumptions.iter().map(String::as_str).collect();
    let mut sequences = vec![];
    for (i, image) in r.images.iter().enumerate() {
        for &pattern in &r.scratch_patterns {
            let mut run = sequence(&image.rom, i, pattern, s, &permissions, None);
            if run.stop_event_index >= 0
                && !s
                    .trace_event_indexes
                    .contains(&(run.stop_event_index as u32))
            {
                run = sequence(
                    &image.rom,
                    i,
                    pattern,
                    s,
                    &permissions,
                    Some(run.stop_event_index as u32),
                );
            }
            sequences.push(run);
        }
    }
    response.entry_contracts = entry_contracts();
    response.chain_sequences = Some(sequences);
    Ok(response)
}
