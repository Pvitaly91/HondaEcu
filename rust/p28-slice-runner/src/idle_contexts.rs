//! M1r: explicit upstream selector snapshots, native target/counter ownership.
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
    pub data0211: u8,
    pub data0216: u8,
    pub data0217: u8,
    pub data0225: u8,
    pub data022a: u8,
    pub raw0274: u16,
    pub raw027c: u16,
    pub counter02e5: u8,
    pub counter02e8: u8,
    pub counter02e9: u8,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Selectors {
    pub data021a_bit0: bool,
    pub data0211_bit5: bool,
    pub data0216_bit3: bool,
    pub data0217_bit6: bool,
    pub data0225_bit1: bool,
    pub data022a_bit4: bool,
    pub data022a_bit5: bool,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Call {
    pub index: u32,
    pub raw_d9: u8,
    pub raw_period: u16,
    #[serde(deserialize_with = "required_selectors")]
    pub selectors: Option<Selectors>,
}
fn required_selectors<'de, D: serde::Deserializer<'de>>(
    d: D,
) -> Result<Option<Selectors>, D::Error> {
    Option::<Selectors>::deserialize(d)
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
    pub state_after_inputs: Option<State>,
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
    let s = r
        .idle_contexts
        .as_ref()
        .ok_or("idle contexts stimulus required")?;
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
        || s.calls
            .iter()
            .enumerate()
            .any(|(i, c)| c.index as usize != i)
    {
        return Err("invalid bounded idle contexts request".into());
    }
    Ok(())
}
pub fn code(consumer: bool) -> Vec<[u32; 2]> {
    if consumer {
        crate::idle::code_ranges(true)
    } else {
        vec![[0x2FD1, 0x30AB], [0x7D8A, 0x7DA5], [0x5894, 0x58D3]]
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
        [0x211, 0x212],
        [0x216, 0x218],
        [0x21A, 0x21B],
        [0x225, 0x226],
        [0x22A, 0x22B],
        [0x25C, 0x25E],
        [0x274, 0x276],
        [0x27A, 0x27E],
        [0x2E5, 0x2E6],
        [0x2E8, 0x2EA],
        [0x7FE, 0x800],
    ]
}
pub fn program(consumer: bool) -> Vec<[u16; 2]> {
    if consumer {
        vec![[0x36, 0x38]]
    } else {
        vec![[0x28, 0x2A], [0x68CB, 0x68F5]]
    }
}
fn contract(consumer: bool) -> SliceContract {
    SliceContract {
        entry_pc: if consumer { 0x9DC } else { 0x2FD1 },
        exit_pcs: vec![if consumer { 0x9F4 } else { 0x30AB }],
        code_ranges: code(consumer),
        psw: 0x1101,
        lrb: if consumer { 0x40 } else { 0x41 },
        usp: 0x180,
        instruction_budget: 256,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    }
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({
    "id":"idleContexts","producerEntry":0x2FD1,"producerExit":0x30AB,"consumerEntry":0x9DC,"consumerExit":0x9F4,
    "producerCode":code(false),"consumerCode":code(true),"dataRanges":ranges(),"producerProgramData":program(false),"consumerProgramData":program(true),
    "psw":0x1101,"producerLrb":0x41,"consumerLrb":0x40,"scb":1,"usp":0x180,"ssp":0x7FE,"budget":256,"tracePrefix":128,"stop":"BeforeInstruction",
    "selectorMasks":[[0x21A,1],[0x211,32],[0x216,8],[0x217,64],[0x225,2],[0x22A,48]],
    "state":"Seed once; masked scripted upstream selector updates only; no counter service, scheduler or target/component reseed",
    "physicalRpmAvailable":false,"assumptions":[]})]
}
fn state(cpu: &Cpu, bus: &mut Bus) -> State {
    State {
        target: read_data_u16(cpu, bus, 0x25C),
        raw027a: read_data_u16(cpu, bus, 0x27A),
        error_magnitude: read_data_u16(cpu, bus, 0xCA),
        data021a: read_data_u8(cpu, bus, 0x21A),
        data0211: read_data_u8(cpu, bus, 0x211),
        data0216: read_data_u8(cpu, bus, 0x216),
        data0217: read_data_u8(cpu, bus, 0x217),
        data0225: read_data_u8(cpu, bus, 0x225),
        data022a: read_data_u8(cpu, bus, 0x22A),
        raw0274: read_data_u16(cpu, bus, 0x274),
        raw027c: read_data_u16(cpu, bus, 0x27C),
        counter02e5: read_data_u8(cpu, bus, 0x2E5),
        counter02e8: read_data_u8(cpu, bus, 0x2E8),
        counter02e9: read_data_u8(cpu, bus, 0x2E9),
    }
}
fn execute(cpu: &mut Cpu, bus: &mut Bus, consumer: bool) -> crate::adaptive::Stage {
    let c = contract(consumer);
    enter(cpu, bus, &c);
    bus.set_program_data_ranges(program(consumer));
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
    let s = r.idle_contexts.as_ref().expect("validated");
    let mut sequences = vec![];
    for &pattern in &r.scratch_patterns {
        let (mut cpu, mut bus) = seed_machine(&r.images[0].rom, &contract(false), pattern);
        cpu.ssp = 0x7FE;
        let initial = &s.initial_state;
        for (a, v) in [
            (0x25C, initial.target),
            (0x27A, initial.raw027a),
            (0xCA, initial.error_magnitude),
            (0x274, initial.raw0274),
            (0x27C, initial.raw027c),
        ] {
            write_data_u16(&mut cpu, &mut bus, a, v);
        }
        for (a, v) in [
            (0x21A, initial.data021a),
            (0x211, initial.data0211),
            (0x216, initial.data0216),
            (0x217, initial.data0217),
            (0x225, initial.data0225),
            (0x22A, initial.data022a),
            (0x2E5, initial.counter02e5),
            (0x2E8, initial.counter02e8),
            (0x2E9, initial.counter02e9),
        ] {
            write_data_u8(&mut cpu, &mut bus, a, v);
        }
        bus.configure_scoped_access(ranges(), 1024);
        let mut stopped = false;
        let mut checkpoints = vec![];
        for call in &s.calls {
            let before = state(&cpu, &mut bus);
            let mut row = Checkpoint {
                index: call.index,
                status: 4,
                state_before: before.clone(),
                state_after: before,
                state_after_inputs: None,
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
                if let Some(u) = &call.selectors {
                    for (a, mask, on) in [
                        (0x21A, 1, u.data021a_bit0),
                        (0x211, 32, u.data0211_bit5),
                        (0x216, 8, u.data0216_bit3),
                        (0x217, 64, u.data0217_bit6),
                        (0x225, 2, u.data0225_bit1),
                        (0x22A, 16, u.data022a_bit4),
                        (0x22A, 32, u.data022a_bit5),
                    ] {
                        let old = read_data_u8(&cpu, &mut bus, a);
                        write_data_u8(
                            &mut cpu,
                            &mut bus,
                            a,
                            (old & !mask) | if on { mask } else { 0 },
                        );
                    }
                }
                row.state_after_inputs = Some(state(&cpu, &mut bus));
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
    response.idle_context_sequences = Some(sequences);
    Ok(response)
}
pub fn admission(d: &Decoded) -> FormAdmission {
    if crate::idle::admission(d) == FormAdmission::Allowed {
        return FormAdmission::Allowed;
    }
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    match (p.mnemonic, p.dd_mode, p.bytes_pat) {
        ("MOVB r1, r2", 'U', ["22", "49"])
        | ("CMPB A, r1", '0', ["49"])
        | ("CMPB off N'8, #N8", 'U', ["C4", "N'8", "C0", "N8"])
        | ("MOVB r1, #N8", 'U', ["99", "N8"])
        | ("MOV er3, #N16", 'U', ["47", "98", "NL", "NH"])
        | ("CMP off N8, #N16", 'U', ["B4", "N8", "C0", "NL", "NH"])
        | ("JBS off N8.6, rel8", 'U', ["EE", "N8", "rel8"])
        | ("JBR off N8.5, rel8", 'U', ["DD", "N8", "rel8"])
        | ("JLE rel8", 'U', ["CF", "rel8"])
        | ("LCB A, N16[X1]", 'U', ["90", "AB", "NL", "NH"])
        | ("MOVB r4, A", 'U', ["24", "8A"])
        | ("STB A, r5", '0', ["8D"])
        | ("XCHGB A, r1", '0', ["21", "10"])
        | ("XCHGB A, r4", '0', ["24", "10"]) => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}
