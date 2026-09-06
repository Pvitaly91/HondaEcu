//! Actual-byte, once-seeded VTEC software decisions. No threshold/gate formula.
use crate::{
    bus::Bus,
    cpu::Cpu,
    exec::{read_data_u8, write_data_u16, write_data_u8},
    protocol::{CaseResult, Request, Response},
    runner::{execute_in_state_observed, seed_machine, SliceContract},
    stateful_forms,
};
use serde::{Deserialize, Serialize};

pub const STATE_ADDRESSES: [u16; 8] = [0x131, 0x127, 0x198, 0x1D8, 0x1D9, 0x1DF, 0xF3, 0x22];
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct State {
    pub data0131: u8,
    pub data0127: u8,
    pub data0198: u8,
    #[serde(rename = "data01D8")]
    pub data01d8: u8,
    #[serde(rename = "data01D9")]
    pub data01d9: u8,
    #[serde(rename = "data01DF")]
    pub data01df: u8,
    #[serde(rename = "data00F3")]
    pub data00f3: u8,
    pub p1_output_data: u8,
}
impl State {
    fn bytes(&self) -> [u8; 8] {
        [
            self.data0131,
            self.data0127,
            self.data0198,
            self.data01d8,
            self.data01d9,
            self.data01df,
            self.data00f3,
            self.p1_output_data,
        ]
    }
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Call {
    pub index: u32,
    pub compact_code: u8,
    pub context: u8,
    pub enabled: bool,
    #[serde(rename = "raw00CC")]
    pub raw00cc: u8,
    #[serde(rename = "raw00D9")]
    pub raw00d9: u8,
    #[serde(rename = "snapshot011A")]
    pub snapshot011a: u16,
    #[serde(rename = "snapshot011C")]
    pub snapshot011c: u8,
    pub snapshot0119: u8,
    pub raw0132: u8,
    pub raw0199: u8,
    pub fast_ticks: u8,
    pub slow_ticks: u8,
}
#[derive(Clone, Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Stimulus {
    pub format_version: u32,
    pub initial_state: State,
    pub calls: Vec<Call>,
    pub trace_call_indexes: Vec<u32>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Checkpoint {
    pub index: u32,
    pub status: i32,
    pub input: Call,
    pub state_before: State,
    pub state_at_entry: State,
    pub state_after: State,
    pub software_request: Option<bool>,
    pub selection_status: Option<bool>,
    pub tick_runs: Vec<[u32; 5]>,
    pub tick_writes: Vec<[u32; 3]>,
    pub decision_writes: Vec<[u32; 3]>,
    /// [pc,nextPc,accumulatorBefore,accumulatorAfter,pswBefore,pswAfter,lhs,rhs].
    /// Non-comparisons use 65536 for both operand slots.
    /// Only actually executed main decision comparisons/branches, not helper trace.
    pub gate_events: Vec<[u32; 8]>,
    pub execution: Option<CaseResult>,
    pub tick_failure: Option<CaseResult>,
    pub cumulative_assumptions: Vec<String>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SequenceResult {
    pub image_index: usize,
    pub scratch_pattern: u8,
    pub checkpoints: Vec<Checkpoint>,
    pub completed_calls: u32,
    pub stop_call_index: i32,
    pub remaining_not_run: u32,
}

pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({
        "id":"statefulVtec","entryPc":0x122C,"exitPc":0x12FC,"stop":"BeforeInstruction",
        "codeRanges":[[0x122C,0x12FC],[0x5839,0x586E]],"psw":0x0101,"lrb":0x20,"usp":0x280,"ssp":0x7FE,
        "instructionBudget":512,"initialState":"OncePerImageAndScratchSequence","callEntryReset":["PC","PSW","LRB","USP"],
        "compactCode":"ExplicitRawSoftwareInput","p1Mode":"AllOutputDataRegisterOnlyNoExternalBus",
        "physicalRpmAvailable":false,"fullBoot":"NotRun","interrupts":"NotInjected",
        "decrementBody":[0x5BD0,0x5BD9],"incrementBody":[0x3CEB,0x3CF3],
        "fastTickTargets":[0x1D8,0x1D9],"slowTickTargets":[0x1DF,0xF3],"tickUnits":"ExplicitNativeBodyCallsNotMilliseconds",
        "stateAddresses":STATE_ADDRESSES,"gateEventPcs":GATE_PCS,"traceLimit":128,"allowedAssumptions":[stateful_forms::SUBB_OFF_ASSUMPTION]
    })]
}

pub const GATE_PCS: [u16; 32] = [
    0x122C, 0x1233, 0x123A, 0x123E, 0x124A, 0x1257, 0x125C, 0x1263, 0x1268, 0x1279, 0x127F, 0x1289,
    0x128D, 0x128F, 0x1293, 0x1299, 0x129B, 0x129E, 0x12A1, 0x12A4, 0x12A7, 0x12B6, 0x12B8, 0x12BD,
    0x12C0, 0x12C2, 0x12C4, 0x12C9, 0x12D4, 0x12D9, 0x12EE, 0x12F3,
];

pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .stateful_vtec
        .as_ref()
        .ok_or("stateful stimulus required")?;
    if r.synthetic.is_some()
        || r.producer_cases.is_some()
        || r.acquisition_sequence.is_some()
        || r.scratch_patterns != [0, 85, 170]
        || r.images[0].id != "baseline"
        || r.images.iter().any(|i| i.rom.len() != 32768)
        || r.images.get(1).is_some_and(|i| i.id != "derived")
        || r.allow_assumptions
            .iter()
            .any(|a| a != stateful_forms::SUBB_OFF_ASSUMPTION)
        || s.format_version != 1
        || s.calls.is_empty()
        || s.calls.len() > 256
        || s.trace_call_indexes.len() > 8
        || s.calls.iter().enumerate().any(|(i, c)| {
            c.index as usize != i || c.context > 1 || c.fast_ticks > 32 || c.slow_ticks > 32
        })
        || s.trace_call_indexes
            .iter()
            .any(|i| *i as usize >= s.calls.len())
        || s.trace_call_indexes
            .iter()
            .collect::<std::collections::HashSet<_>>()
            .len()
            != s.trace_call_indexes.len()
    {
        return Err("invalid bounded stateful VTEC contract".into());
    }
    Ok(())
}
fn contract(entry: u16, exit: u16) -> SliceContract {
    SliceContract {
        entry_pc: entry,
        exit_pcs: vec![exit],
        code_ranges: if entry == 0x122C {
            vec![[0x122C, 0x12FC], [0x5839, 0x586E]]
        } else {
            vec![[entry as u32, exit as u32]]
        },
        psw: 0x0101,
        lrb: 0x20,
        usp: 0x280,
        instruction_budget: if entry == 0x122C { 512 } else { 4 },
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    }
}
fn enter(cpu: &mut Cpu, bus: &mut Bus, c: &SliceContract) {
    cpu.pc = c.entry_pc;
    write_data_u16(cpu, bus, 2, c.lrb);
    write_data_u16(cpu, bus, 4, c.psw);
    write_data_u16(cpu, bus, 0x8E, c.usp);
    bus.clear_program_reads();
}
fn snapshot(cpu: &Cpu, bus: &mut Bus) -> State {
    State {
        data0131: read_data_u8(cpu, bus, 0x131),
        data0127: read_data_u8(cpu, bus, 0x127),
        data0198: read_data_u8(cpu, bus, 0x198),
        data01d8: read_data_u8(cpu, bus, 0x1D8),
        data01d9: read_data_u8(cpu, bus, 0x1D9),
        data01df: read_data_u8(cpu, bus, 0x1DF),
        data00f3: read_data_u8(cpu, bus, 0xF3),
        p1_output_data: bus.p1_output_latch().expect("fixed output mode"),
    }
}
fn persistent(writes: Vec<[u32; 3]>) -> Vec<[u32; 3]> {
    writes
        .into_iter()
        .filter(|w| STATE_ADDRESSES.contains(&(w[0] as u16)))
        .collect()
}

fn sequence(
    rom: &[u8],
    image: usize,
    scratch: u8,
    s: &Stimulus,
    allowed: &[&str],
) -> SequenceResult {
    let c = contract(0x122C, 0x12FC);
    let (mut cpu, mut bus) = seed_machine(rom, &c, scratch);
    cpu.ssp = 0x7FE;
    bus.set_p1_output_latch(Some(s.initial_state.p1_output_data));
    for (a, v) in STATE_ADDRESSES.into_iter().zip(s.initial_state.bytes()) {
        if a != 0x22 {
            write_data_u8(&mut cpu, &mut bus, a, v);
        }
    }
    // No uninitialized caller flags can leak from a scratch pattern.
    write_data_u8(&mut cpu, &mut bus, 0x11E, 0);
    bus.configure_scoped_access(
        vec![
            [0, 8],
            [0x22, 0x23],
            [0x88, 0x90],
            [0xCC, 0xCD],
            [0xD9, 0xDA],
            [0xF3, 0xF4],
            [0x100, 0x108],
            [0x119, 0x11F],
            [0x127, 0x128],
            [0x131, 0x134],
            [0x198, 0x19A],
            [0x1D8, 0x1DA],
            [0x1DF, 0x1E0],
            [0x7FE, 0x800],
        ],
        512,
    );
    let mut result = SequenceResult {
        image_index: image,
        scratch_pattern: scratch,
        checkpoints: vec![],
        completed_calls: 0,
        stop_call_index: -1,
        remaining_not_run: 0,
    };
    let mut cumulative = vec![];
    for input in &s.calls {
        let before = snapshot(&cpu, &mut bus);
        let mut cp = Checkpoint {
            index: input.index,
            status: 4,
            input: input.clone(),
            state_before: before.clone(),
            state_at_entry: before.clone(),
            state_after: before,
            software_request: None,
            selection_status: None,
            tick_runs: vec![],
            tick_writes: vec![],
            decision_writes: vec![],
            gate_events: vec![],
            execution: None,
            tick_failure: None,
            cumulative_assumptions: cumulative.clone(),
        };
        if result.stop_call_index >= 0 {
            result.remaining_not_run += 1;
            result.checkpoints.push(cp);
            continue;
        }
        let mut schedule = vec![];
        for _ in 0..input.fast_ticks {
            schedule.extend([(0x5BD0, 0x5BD9, 0x1D8), (0x5BD0, 0x5BD9, 0x1D9)]);
        }
        for _ in 0..input.slow_ticks {
            schedule.extend([(0x5BD0, 0x5BD9, 0x1DF), (0x3CEB, 0x3CF3, 0xF3)]);
        }
        bus.set_program_data_ranges(vec![]);
        for (entry, exit, target) in schedule {
            let tick = contract(entry, exit);
            enter(&mut cpu, &mut bus, &tick);
            write_data_u16(&mut cpu, &mut bus, 0x88, target);
            bus.begin_write_journal();
            let execution = execute_in_state_observed(
                &mut cpu,
                &mut bus,
                &tick,
                &[],
                false,
                Some(stateful_forms::admission),
                true,
            );
            cp.tick_writes.extend(persistent(bus.end_write_journal()));
            cp.tick_runs.push([
                entry as u32,
                target as u32,
                execution.stop_pc as u32,
                execution.status as u32,
                execution.steps,
            ]);
            if execution.status != 0 {
                cp.status = execution.status;
                cp.tick_failure = Some(execution);
                break;
            }
        }
        cp.state_at_entry = snapshot(&cpu, &mut bus);
        if cp.tick_failure.is_none() {
            enter(&mut cpu, &mut bus, &c);
            for (a, v) in [
                (0x133, input.compact_code),
                (0xCC, input.raw00cc),
                (0xD9, input.raw00d9),
                (0x11C, input.snapshot011c),
                (0x119, input.snapshot0119),
                (0x132, input.raw0132),
                (0x199, input.raw0199),
                (
                    0x11E,
                    if input.context == 0 { 8 } else { 0 } | if input.enabled { 16 } else { 0 },
                ),
            ] {
                write_data_u8(&mut cpu, &mut bus, a, v);
            }
            write_data_u16(&mut cpu, &mut bus, 0x11A, input.snapshot011a);
            bus.set_program_data_ranges(vec![[0x6542, 0x6566], [0x60FA, 0x60FB]]);
            bus.start_decision_observer();
            bus.begin_write_journal();
            let execution = execute_in_state_observed(
                &mut cpu,
                &mut bus,
                &c,
                allowed,
                s.trace_call_indexes.contains(&input.index),
                Some(stateful_forms::admission),
                true,
            );
            cp.decision_writes = persistent(bus.end_write_journal());
            cp.gate_events = bus
                .finish_decision_observer()
                .into_iter()
                .filter(|e| GATE_PCS.contains(&(e[0] as u16)))
                .collect();
            for a in &execution.used_assumptions {
                if !cumulative.contains(a) {
                    cumulative.push(a.clone());
                }
            }
            cp.status = execution.status;
            cp.execution = Some(execution);
        }
        cp.state_after = snapshot(&cpu, &mut bus);
        cp.cumulative_assumptions = cumulative.clone();
        if cp.status == 0 {
            cp.software_request = Some(cp.state_after.p1_output_data & 1 != 0);
            cp.selection_status = Some(cp.state_after.data0127 & 2 != 0);
            result.completed_calls += 1;
        } else {
            result.stop_call_index = input.index as i32;
        }
        result.checkpoints.push(cp);
    }
    result
}
pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let stimulus = r.stateful_vtec.as_ref().ok_or("missing stimulus")?;
    let allowed: Vec<_> = r.allow_assumptions.iter().map(String::as_str).collect();
    response.entry_contracts = entry_contracts();
    response.stateful_sequences = Some(
        r.images
            .iter()
            .enumerate()
            .flat_map(|(i, image)| {
                r.scratch_patterns
                    .iter()
                    .map(|p| sequence(&image.rom, i, *p, stimulus, &allowed))
                    .collect::<Vec<_>>()
            })
            .collect(),
    );
    Ok(response)
}
