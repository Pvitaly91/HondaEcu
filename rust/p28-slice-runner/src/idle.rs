//! One exact raw-context target path and its immediate period-error consumer.
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

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct State {
    pub target: u16,
    pub raw027a: u16,
    pub error_magnitude: u16,
    pub data021a: u8,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Call {
    pub index: u32,
    pub raw_d9: u8,
    pub raw_period: u16,
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
pub struct Checkpoint {
    pub index: u32,
    pub status: i32,
    pub state_before: State,
    pub state_after_producer: Option<State>,
    pub state_after: State,
    pub producer: Option<crate::adaptive::Stage>,
    pub consumer: Option<crate::adaptive::Stage>,
    pub actual_target: Option<u16>,
    pub actual_error: Option<u16>,
    pub current_below_target: Option<bool>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Sequence {
    pub scratch_pattern: u8,
    pub checkpoints: Vec<Checkpoint>,
}
pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r.idle_target.as_ref().ok_or("idle stimulus required")?;
    if s.format_version != 1
        || s.calls.is_empty()
        || s.calls.len() > 64
        || s.initial_state.data021a & 1 == 0
        || r.images.len() != 1
        || r.images[0].id != "baseline"
        || r.images[0].rom.len() != 32768
        || r.scratch_patterns != [0, 85, 170]
        || !r.allow_assumptions.is_empty()
        || r.synthetic.is_some()
        || r.producer_cases.is_some()
        || s.calls
            .iter()
            .enumerate()
            .any(|(i, c)| c.index as usize != i || c.raw_d9 < 52)
    {
        return Err("invalid bounded idle context (rawD9 >= 52; initial 021A.0 set)".into());
    }
    Ok(())
}
pub fn code_ranges(consumer: bool) -> Vec<[u32; 2]> {
    if consumer {
        vec![[0x9DC, 0x9F4], [0x59A6, 0x59AD]]
    } else {
        vec![
            [0x2FD1, 0x2FE0],
            [0x2FEC, 0x2FEF],
            [0x306E, 0x3076],
            [0x309A, 0x30A0],
            [0x30A9, 0x30AB],
            [0x7D8A, 0x7D98],
            [0x5894, 0x58D3],
        ]
    }
}
pub fn ranges() -> Vec<[u16; 2]> {
    vec![
        [0, 8],
        [0x88, 0x90],
        [0xC4, 0xC6],
        [0xCA, 0xCC],
        [0xD9, 0xDA],
        [0x200, 0x210],
        [0x216, 0x217],
        [0x21A, 0x21B],
        [0x25C, 0x25E],
        [0x27A, 0x27C],
        [0x7FE, 0x800],
    ]
}
fn contract(consumer: bool) -> SliceContract {
    SliceContract {
        entry_pc: if consumer { 0x9DC } else { 0x2FD1 },
        exit_pcs: vec![if consumer { 0x9F4 } else { 0x30AB }],
        code_ranges: code_ranges(consumer),
        psw: 0x1101,
        lrb: if consumer { 0x40 } else { 0x41 },
        usp: 0x180,
        instruction_budget: 128,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    }
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({
        "id":"idleTarget","producerEntry":0x2FD1,"producerExit":0x30AB,"consumerEntry":0x9DC,"consumerExit":0x9F4,
        "producerCode":code_ranges(false),"consumerCode":code_ranges(true),"dataRanges":ranges(),
        "producerProgramData":[[0x28,0x2A],[0x68CB,0x68E0]],"consumerProgramData":[[0x36,0x38]],
        "psw":0x1101,"producerLrb":0x41,"consumerLrb":0x40,"scb":1,"usp":0x180,"ssp":0x7FE,"budget":128,
        "stop":"BeforeInstruction","context":"rawD9 >= 52; persistent 021A.0 set; caller snapshot 0216.3 clear",
        "state":"Seed once; native target/correction/error/sign stores; no counter/filter in this selected target path",
        "physicalRpmAvailable":false,"assumptions":[]
    })]
}
fn state(cpu: &Cpu, bus: &mut Bus) -> State {
    State {
        target: read_data_u16(cpu, bus, 0x25C),
        raw027a: read_data_u16(cpu, bus, 0x27A),
        error_magnitude: read_data_u16(cpu, bus, 0xCA),
        data021a: read_data_u8(cpu, bus, 0x21A),
    }
}
fn execute(cpu: &mut Cpu, bus: &mut Bus, consumer: bool) -> crate::adaptive::Stage {
    let c = contract(consumer);
    enter(cpu, bus, &c);
    bus.clear_program_reads();
    bus.set_program_data_ranges(if consumer {
        vec![[0x36, 0x38]]
    } else {
        vec![[0x28, 0x2A], [0x68CB, 0x68E0]]
    });
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
pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r.idle_target.as_ref().expect("validated");
    let mut sequences = vec![];
    for &pattern in &r.scratch_patterns {
        let (mut cpu, mut bus) = seed_machine(&r.images[0].rom, &contract(false), pattern);
        cpu.ssp = 0x7FE;
        for (a, v) in [
            (0x25C, s.initial_state.target),
            (0x27A, s.initial_state.raw027a),
            (0xCA, s.initial_state.error_magnitude),
        ] {
            write_data_u16(&mut cpu, &mut bus, a, v);
        }
        write_data_u8(&mut cpu, &mut bus, 0x21A, s.initial_state.data021a);
        bus.configure_scoped_access(ranges(), 512);
        let mut stopped = false;
        let mut checkpoints = vec![];
        for call in &s.calls {
            let before = state(&cpu, &mut bus);
            let mut row = Checkpoint {
                index: call.index,
                status: 4,
                state_before: before.clone(),
                state_after: before,
                state_after_producer: None,
                producer: None,
                consumer: None,
                actual_target: None,
                actual_error: None,
                current_below_target: None,
            };
            if !stopped {
                write_data_u8(&mut cpu, &mut bus, 0xD9, call.raw_d9);
                write_data_u16(&mut cpu, &mut bus, 0xC4, call.raw_period);
                // Explicit fixed caller snapshot; never overwrite target or 021A history.
                write_data_u8(&mut cpu, &mut bus, 0x216, 0);
                let p = execute(&mut cpu, &mut bus, false);
                row.status = p.result.status;
                row.producer = Some(p);
                let produced = state(&cpu, &mut bus);
                row.state_after_producer = Some(produced.clone());
                if row.status == 0 {
                    row.actual_target = Some(produced.target);
                    let c = execute(&mut cpu, &mut bus, true);
                    row.status = c.result.status;
                    row.consumer = Some(c);
                    if row.status == 0 {
                        let after = state(&cpu, &mut bus);
                        row.actual_error = Some(after.error_magnitude);
                        row.current_below_target = Some(after.data021a & 16 != 0);
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
    response.idle_sequences = Some(sequences);
    Ok(response)
}
pub fn admission(d: &Decoded) -> FormAdmission {
    if crate::adaptive::admission(d) == FormAdmission::Allowed
        || crate::stateful_forms::admission(d) == FormAdmission::Allowed
        || crate::chain_forms::compact_admission(d) == FormAdmission::Allowed
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
        ("MOVB r2, #N8", 'U', ["9A", "N8"])
        | ("CMPB A, r2", '0', ["4A"])
        | ("CLR er3", 'U', ["47", "15"])
        | ("L A, DP", 'S', ["42"])
        | ("ST A, off N8", '1', ["D4", "N8"])
        | ("ST A, er1", '1', ["89"])
        | ("ST A, er3", '1', ["8B"])
        | ("ADD X1, #N16", 'U', ["90", "80", "NL", "NH"])
        | ("SWAP", '1', ["83"])
        | ("SUBB r4, A", 'U', ["24", "A1"])
        | ("XCHGB A, r5", '0', ["25", "10"])
        | ("SUB A, er3", '1', ["2B"])
        | ("SUB A, er1", '1', ["29"])
        | ("SUB er3, A", 'U', ["47", "A1"])
        | ("MOV er0, er1", 'U', ["45", "48"])
        | ("ADD A, er3", '1', ["0B"])
        | ("SUB A, off N8", '1', ["A7", "N8"])
        | ("MB off N8.4, C", 'U', ["C4", "N8", "3C"])
        | ("XOR A, #N16", '1', ["F6", "NL", "NH"])
        | ("ST A, N8", '1', ["D5", "N8"])
        | ("VCAL 0", 'U', ["10"])
        | ("VCAL 7", 'U', ["17"]) => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}
