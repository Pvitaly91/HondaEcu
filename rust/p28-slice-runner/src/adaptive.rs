//! Bounded adaptive producer + existing limiter on one CPU/RAM per sequence.
use crate::{
    acquisition::enter,
    bus::Bus,
    cpu::Cpu,
    decoder::Decoded,
    exec::{read_data_u16, read_data_u8, write_data_u16, write_data_u8},
    full_decoder::FULL_OPCODES,
    instruction_forms::FormAdmission,
    limiter,
    protocol::{CaseResult, Request, Response},
    runner::{execute_in_state_observed, seed_machine, SliceContract},
};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct State {
    pub limiter: limiter::State,
    pub timer: u8,
    pub counter: u8,
    pub ie: u16,
    pub restore_ie: u16,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Call {
    pub limiter: limiter::Call,
    pub raw00ce: u16,
    pub bank1: bool,
    pub reset217: bool,
    pub reset214: bool,
    pub mode212: bool,
    pub enable223: bool,
    pub raw_d9: u8,
    pub timer_ticks: u8,
    pub counter_ticks: u8,
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
pub struct Stage {
    pub result: CaseResult,
    pub writes: Vec<[u32; 3]>,
    pub events: Vec<[u32; 8]>,
    pub ssp_after: u16,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Tick {
    pub address: u16,
    pub stage: Stage,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Checkpoint {
    pub index: u32,
    pub status: i32,
    pub state_before: State,
    pub state_after_producer: Option<State>,
    pub state_after: State,
    pub ticks: Vec<Tick>,
    pub producer: Option<Stage>,
    pub limiter: Option<limiter::Checkpoint>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Sequence {
    pub scratch_pattern: u8,
    pub checkpoints: Vec<Checkpoint>,
}
pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .adaptive_limiter
        .as_ref()
        .ok_or("adaptive stimulus required")?;
    if s.format_version != 1
        || s.calls.is_empty()
        || s.calls.len() > 64
        || r.images.len() != 1
        || r.images[0].id != "baseline"
        || r.images[0].rom.len() != 32768
        || r.scratch_patterns != [0, 85, 170]
        || !r.allow_assumptions.is_empty()
        || r.synthetic.is_some()
        || r.producer_cases.is_some()
        || s.calls.iter().enumerate().any(|(i, c)| {
            c.limiter.index as usize != i
                || c.limiter.channel_mask & 0xF0 != 0xF0
                || c.timer_ticks as u16 + c.counter_ticks as u16 > 32
        })
    {
        return Err("invalid bounded adaptive contract".into());
    }
    Ok(())
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({
        "id":"adaptiveLimiter","producerEntry":0x487B,"producerExit":0x48F5,"codeRanges":[[0x487B,0x48F5],[0x5AB8,0x5AE6]],"tableRange":[0x6493,0x64AB],
        "tickEntry":0x5BD0,"tickExit":0x5BD9,"tickTargets":[0x1D5,0x1CE],"producerPsw":0x1101,"tickPsw":1,"lrb":0x41,"scb":1,"usp":0x180,"ssp":0x7FE,"stackRange":[0x7FE,0x800],"producerBudget":160,"tickBudget":3,
        "dataRanges":producer_ranges(),"limiterDecisionEntry":0x1966,"limiterDecisionExit":0x1A38,"consumerEntry":0x5585,"consumerExit":0x5596,
        "stop":"BeforeInstruction","ie":"Word-only software storage; no IRQ delivery","state":"Once-only thresholds/counters; native stores thereafter","ticks":"Explicit native single-element service schedule, not elapsed time","physicalRpmAvailable":false,"assumptions":[]
    })]
}
fn producer_ranges() -> Vec<[u16; 2]> {
    vec![
        [0, 8],
        [0x1A, 0x1C],
        [0x88, 0x90],
        [0xCE, 0xD0],
        [0xD9, 0xDA],
        [0xF8, 0xFA],
        [0x124, 0x125],
        [0x12A, 0x12C],
        [0x18F, 0x190],
        [0x1A4, 0x1A8],
        [0x1CE, 0x1CF],
        [0x1D5, 0x1D6],
        [0x1D7, 0x1D8],
        [0x208, 0x210],
        [0x212, 0x213],
        [0x214, 0x215],
        [0x217, 0x218],
        [0x21F, 0x220],
        [0x223, 0x224],
        [0x7FE, 0x800],
    ]
}
fn contract(tick: bool) -> SliceContract {
    SliceContract {
        entry_pc: if tick { 0x5BD0 } else { 0x487B },
        exit_pcs: vec![if tick { 0x5BD9 } else { 0x48F5 }],
        code_ranges: if tick {
            vec![[0x5BD0, 0x5BD9]]
        } else {
            vec![[0x487B, 0x48F5], [0x5AB8, 0x5AE6]]
        },
        psw: if tick { 1 } else { 0x1101 },
        lrb: 0x41,
        usp: 0x180,
        instruction_budget: if tick { 3 } else { 160 },
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    }
}
fn state(cpu: &Cpu, bus: &mut Bus) -> State {
    State {
        limiter: limiter::state(cpu, bus),
        timer: read_data_u8(cpu, bus, 0x1D5),
        counter: read_data_u8(cpu, bus, 0x1CE),
        ie: bus.adaptive_ie().expect("seeded"),
        restore_ie: read_data_u16(cpu, bus, 0xF8),
    }
}
fn execute(cpu: &mut Cpu, bus: &mut Bus, c: &SliceContract) -> Stage {
    bus.begin_write_journal();
    bus.start_decision_observer();
    let result = execute_in_state_observed(cpu, bus, c, &[], true, Some(admission), true);
    Stage {
        result,
        writes: bus.end_write_journal(),
        events: bus.finish_decision_observer(),
        ssp_after: cpu.ssp,
    }
}
pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r.adaptive_limiter.as_ref().expect("validated");
    let mut sequences = vec![];
    for &pattern in &r.scratch_patterns {
        let pc = contract(false);
        let tc = contract(true);
        let (mut cpu, mut bus) = seed_machine(&r.images[0].rom, &pc, pattern);
        cpu.ssp = 0x7FE;
        let initial = &s.initial_state;
        let l = &initial.limiter;
        for (a, v) in [
            (0x124, l.data0124),
            (0x12B, l.data012b),
            (0x12A, l.data012a),
            (0x18F, l.data018f),
            (0x1D7, l.data01d7),
            (0x121, 128),
            (0x1D5, initial.timer),
            (0x1CE, initial.counter),
        ] {
            write_data_u8(&mut cpu, &mut bus, a, v);
        }
        for (a, v) in [
            (0x1A4, l.ram_cut),
            (0x1A6, l.ram_resume),
            (0xF8, initial.restore_ie),
        ] {
            write_data_u16(&mut cpu, &mut bus, a, v);
        }
        bus.set_adaptive_ie(Some(initial.ie));
        let mut stopped = false;
        let mut checkpoints = vec![];
        for call in &s.calls {
            bus.configure_scoped_access(producer_ranges(), 256);
            let before = state(&cpu, &mut bus);
            let mut row = Checkpoint {
                index: call.limiter.index,
                status: 4,
                state_before: before.clone(),
                state_after_producer: None,
                state_after: before,
                ticks: vec![],
                producer: None,
                limiter: None,
            };
            if !stopped {
                bus.set_program_data_ranges(vec![]);
                for (address, count) in [(0x1D5, call.timer_ticks), (0x1CE, call.counter_ticks)] {
                    for _ in 0..count {
                        if stopped {
                            break;
                        }
                        // X1 is an explicit single-element caller argument, not a counter store.
                        enter(&mut cpu, &mut bus, &tc);
                        write_data_u16(&mut cpu, &mut bus, 0x88, address);
                        bus.configure_scoped_access(
                            vec![[0, 8], [0x88, 0x90], [address, address + 1]],
                            256,
                        );
                        let stage = execute(&mut cpu, &mut bus, &tc);
                        row.status = stage.result.status;
                        stopped = row.status != 0;
                        row.ticks.push(Tick { address, stage });
                        bus.configure_scoped_access(producer_ranges(), 256);
                    }
                }
                if !stopped {
                    for (a, v) in [
                        (0x21F, if call.bank1 { 2 } else { 0 }),
                        (0x217, if call.reset217 { 32 } else { 0 }),
                        (0x214, if call.reset214 { 1 } else { 0 }),
                        (0x212, if call.mode212 { 32 } else { 0 }),
                        (0x223, if call.enable223 { 4 } else { 0 }),
                        (0xD9, call.raw_d9),
                    ] {
                        write_data_u8(&mut cpu, &mut bus, a, v);
                    }
                    write_data_u16(&mut cpu, &mut bus, 0xCE, call.raw00ce);
                    bus.set_program_data_ranges(vec![[0x6493, 0x64AB]]);
                    enter(&mut cpu, &mut bus, &pc);
                    let p = execute(&mut cpu, &mut bus, &pc);
                    row.status = p.result.status;
                    stopped = row.status != 0;
                    row.producer = Some(p);
                    row.state_after_producer = Some(state(&cpu, &mut bus));
                }
                if !stopped {
                    bus.set_program_data_ranges(vec![]);
                    bus.configure_scoped_access(
                        vec![
                            [0, 8],
                            [0x2C, 0x2D],
                            [0x88, 0x98],
                            [0xC4, 0xC6],
                            [0x11B, 0x11C],
                            [0x121, 0x122],
                            [0x124, 0x125],
                            [0x12A, 0x12C],
                            [0x18F, 0x190],
                            [0x1A4, 0x1A8],
                            [0x1D7, 0x1D8],
                        ],
                        256,
                    );
                    let l = limiter::execute_call(&mut cpu, &mut bus, &call.limiter, true);
                    row.status = l.status;
                    stopped = row.status != 0;
                    row.limiter = Some(l);
                }
                bus.configure_scoped_access(producer_ranges(), 256);
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
    response.adaptive_sequences = Some(sequences);
    Ok(response)
}
pub fn admission(d: &Decoded) -> FormAdmission {
    if limiter::admission(d) == FormAdmission::Allowed
        || crate::instruction_forms::acquisition_form_admission(d) == FormAdmission::Allowed
    {
        return FormAdmission::Allowed;
    }
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    match (p.mnemonic, p.dd_mode, p.bytes_pat) {
        ("MOV X2, #N16", 'U', ["61", "NL", "NH"])
        | ("MOV DP, A", 'U', ["52"])
        | ("MOV X1, X2", 'U', ["91", "78"])
        | ("MOV er0, A", 'U', ["44", "8A"])
        | ("LC A, N16[X2]", 'U', ["91", "A9", "NL", "NH"])
        | ("MOVB S8[USP], #N8", 'U', ["C3", "S8", "98", "N8"])
        | ("LB A, S8[USP]", 'R', ["F3", "S8"])
        | ("L A, S8[USP]", 'S', ["E3", "S8"])
        | ("ST A, S8[USP]", '1', ["D3", "S8"])
        | ("ST A, er0", '1', ["88"])
        | ("L A, er0", 'S', ["34"])
        | ("CLR er1", 'U', ["45", "15"])
        | ("SUB A, #N16", '1', ["A6", "NL", "NH"])
        | ("SUB A, er0", '1', ["28"])
        | ("ADD A, #N16", '1', ["86", "NL", "NH"])
        | ("ADD A, er1", '1', ["09"])
        | ("CMP A, er0", '1', ["48"])
        | ("CMP A, er3", '1', ["4B"])
        | ("MUL", 'U', ["90", "35"])
        | ("AND N8, #N16", 'U', ["B5", "N8", "D0", "NL", "NH"])
        | ("ANDB PSWH, #N8", 'U', ["A2", "D0", "N8"])
        | ("ORB PSWH, #N8", 'U', ["A2", "E0", "N8"]) => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}
