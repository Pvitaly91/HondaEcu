//! Isolated period decision and the native new-channel-enable mask consumer.
//! RAM thresholds and independent inhibit are initial software snapshots, not
//! per-call overrides. Adaptive threshold production and P2 pins are excluded.
use crate::{
    acquisition::enter,
    bus::Bus,
    cpu::Cpu,
    decoder::Decoded,
    exec::{read_data_u16, read_data_u8, write_data_u16, write_data_u8},
    full_decoder::FULL_OPCODES,
    instruction_forms::FormAdmission,
    protocol::{CaseResult, Request, Response},
    runner::{execute_in_state_observed, seed_machine, SliceContract},
};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct State {
    pub data0124: u8,
    #[serde(rename = "data012B")]
    pub data012b: u8,
    #[serde(rename = "data012A")]
    pub data012a: u8,
    #[serde(rename = "data018F")]
    pub data018f: u8,
    #[serde(rename = "data01D7")]
    pub data01d7: u8,
    pub ram_cut: u16,
    pub ram_resume: u16,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Call {
    pub index: u32,
    pub raw_period: u16,
    pub p4_bit0: bool,
    pub snapshot011b_bit7: bool,
    pub channel_mask: u8,
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
    pub state_after: State,
    pub decision: Option<CaseResult>,
    pub consumer: Option<CaseResult>,
    pub decision_writes: Vec<[u32; 3]>,
    pub consumer_writes: Vec<[u32; 3]>,
    pub decision_events: Vec<[u32; 8]>,
    pub consumer_events: Vec<[u32; 8]>,
    pub overspeed_request: Option<bool>,
    pub inhibit_branch: Option<bool>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Sequence {
    pub image_index: usize,
    pub scratch_pattern: u8,
    pub checkpoints: Vec<Checkpoint>,
}
pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .limiter_sequence
        .as_ref()
        .ok_or("limiter stimulus required")?;
    if s.format_version != 1
        || s.calls.is_empty()
        || s.calls.len() > 256
        || !r.allow_assumptions.is_empty()
        || r.synthetic.is_some()
        || r.producer_cases.is_some()
        || r.scratch_patterns != [0, 85, 170]
        || r.images.iter().any(|i| i.rom.len() != 32768)
        || r.images[0].id != "baseline"
        || r.images.get(1).is_some_and(|i| i.id != "operandMutation")
        || s.calls
            .iter()
            .enumerate()
            .any(|(i, c)| c.index as usize != i || c.channel_mask & 0xF0 != 0xF0)
    {
        return Err("invalid bounded isolated limiter contract".into());
    }
    // The standalone executable is not an admission authority. Nevertheless B
    // must be exactly one complete established immediate operand field.
    if let Some(b) = r.images.get(1) {
        let a = &r.images[0].rom;
        let diffs: Vec<_> = a
            .iter()
            .zip(&b.rom)
            .enumerate()
            .filter(|(_, (x, y))| x != y)
            .map(|(i, _)| i)
            .collect();
        if diffs.is_empty()
            || ![0x1967usize, 0x196A]
                .iter()
                .any(|o| diffs.iter().all(|i| *i >= *o && *i < *o + 2))
        {
            return Err("B differs outside one established word immediate".into());
        }
        if a[0x1966] != 0x62 || a[0x1969] != 0x67 {
            return Err("missing established word immediate encodings".into());
        }
    }
    Ok(())
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({
        "id":"isolatedLimiter","decisionEntry":0x1966,"decisionExit":0x1A38,
        "consumerEntry":0x5585,"consumerExit":0x5596,"stop":"BeforeInstruction",
        "precondition":"Earlier decision gates have selected 1966; 0121.7=1; PSWL.4/5=0",
        "ramThresholds":"Initial software snapshot only; adaptive 487B..48F5 NotRun",
        "p4":"Frozen bit0 software observation; no pins","p2":"Not accessed",
        "state":"Initialized once; no per-call internal stores","budget":96,
        "physicalRpmAvailable":false,
        "decisionCodeRanges":[[0x1966,0x1985],[0x19AC,0x19B0],[0x19C2,0x19CB],[0x1A1E,0x1A38]],
        "consumerCodeRanges":[[0x5585,0x5596]],
        "dataRanges":[[0,8],[0x2C,0x2D],[0x88,0x98],[0xC4,0xC6],[0x11B,0x11C],[0x121,0x122],[0x124,0x125],[0x12A,0x12C],[0x18F,0x190],[0x1A4,0x1A8],[0x1D7,0x1D8]],
        "decisionPsw":0x0101,"consumerPsw":0x0102,"decisionLrb":0x20,"consumerLrb":0x21,"scb":1,"usp":0x280,
        "stack":"No stack instructions admitted on established path; technical SSP unused",
        "callerActions":["PC/PSW/LRB/USP entry reset","00C4 word","011B.7 snapshot","P4.0 frozen observation","consumer accumulator mask high nibble F"],
        "programDataReads":[],"assumptions":[],"interrupts":"NotInjected","timeAdvancement":"None"
    })]
}
fn contract(consumer: bool) -> SliceContract {
    SliceContract {
        entry_pc: if consumer { 0x5585 } else { 0x1966 },
        exit_pcs: vec![if consumer { 0x5596 } else { 0x1A38 }],
        code_ranges: if consumer {
            vec![[0x5585, 0x5596]]
        } else {
            vec![
                [0x1966, 0x1985],
                [0x19AC, 0x19B0],
                [0x19C2, 0x19CB],
                [0x1A1E, 0x1A38],
            ]
        },
        psw: if consumer { 0x0102 } else { 0x0101 },
        lrb: if consumer { 0x21 } else { 0x20 },
        usp: 0x280,
        instruction_budget: 96,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    }
}
fn state(cpu: &Cpu, bus: &mut Bus) -> State {
    State {
        data0124: read_data_u8(cpu, bus, 0x124),
        data012b: read_data_u8(cpu, bus, 0x12B),
        data012a: read_data_u8(cpu, bus, 0x12A),
        data018f: read_data_u8(cpu, bus, 0x18F),
        data01d7: read_data_u8(cpu, bus, 0x1D7),
        ram_cut: read_data_u16(cpu, bus, 0x1A4),
        ram_resume: read_data_u16(cpu, bus, 0x1A6),
    }
}
pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r.limiter_sequence.as_ref().expect("validated");
    let mut sequences = vec![];
    for (image_index, image) in r.images.iter().enumerate() {
        for &scratch_pattern in &r.scratch_patterns {
            let decision_contract = contract(false);
            let consumer_contract = contract(true);
            let (mut cpu, mut bus) = seed_machine(&image.rom, &decision_contract, scratch_pattern);
            for (a, v) in [
                (0x124, s.initial_state.data0124),
                (0x12B, s.initial_state.data012b),
                (0x12A, s.initial_state.data012a),
                (0x18F, s.initial_state.data018f),
                (0x1D7, s.initial_state.data01d7),
                (0x121, 128),
            ] {
                write_data_u8(&mut cpu, &mut bus, a, v);
            }
            write_data_u16(&mut cpu, &mut bus, 0x1A4, s.initial_state.ram_cut);
            write_data_u16(&mut cpu, &mut bus, 0x1A6, s.initial_state.ram_resume);
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
            let mut stopped = false;
            let mut checkpoints = vec![];
            for call in &s.calls {
                let before = state(&cpu, &mut bus);
                let mut row = Checkpoint {
                    index: call.index,
                    status: 4,
                    state_before: before.clone(),
                    state_after: before,
                    decision: None,
                    consumer: None,
                    decision_writes: vec![],
                    consumer_writes: vec![],
                    decision_events: vec![],
                    consumer_events: vec![],
                    overspeed_request: None,
                    inhibit_branch: None,
                };
                if !stopped {
                    write_data_u16(&mut cpu, &mut bus, 0xC4, call.raw_period);
                    write_data_u8(
                        &mut cpu,
                        &mut bus,
                        0x11B,
                        if call.snapshot011b_bit7 { 128 } else { 0 },
                    );
                    bus.observe_limiter_p4(Some(if call.p4_bit0 { 1 } else { 0 }));
                    enter(&mut cpu, &mut bus, &decision_contract);
                    bus.begin_write_journal();
                    bus.start_decision_observer();
                    let result = execute_in_state_observed(
                        &mut cpu,
                        &mut bus,
                        &decision_contract,
                        &[],
                        true,
                        Some(admission),
                        true,
                    );
                    row.decision_writes = bus.end_write_journal();
                    row.decision_events = bus.finish_decision_observer();
                    row.status = result.status;
                    if result.status == 0 {
                        row.overspeed_request = Some(read_data_u8(&cpu, &mut bus, 0x124) & 32 != 0);
                        enter(&mut cpu, &mut bus, &consumer_contract);
                        cpu.a = call.channel_mask as u16;
                        bus.observe_limiter_p4(None);
                        bus.begin_write_journal();
                        bus.start_decision_observer();
                        let c = execute_in_state_observed(
                            &mut cpu,
                            &mut bus,
                            &consumer_contract,
                            &[],
                            true,
                            Some(admission),
                            true,
                        );
                        row.consumer_writes = bus.end_write_journal();
                        row.consumer_events = bus.finish_decision_observer();
                        row.status = c.status;
                        if c.status == 0 {
                            row.inhibit_branch = Some(
                                row.consumer_events
                                    .iter()
                                    .any(|e| (e[0] == 0x5585 || e[0] == 0x5588) && e[1] == 0x5592),
                            );
                        }
                        row.consumer = Some(c);
                    }
                    row.decision = Some(result);
                    stopped = row.status != 0;
                    row.state_after = state(&cpu, &mut bus);
                }
                checkpoints.push(row);
            }
            sequences.push(Sequence {
                image_index,
                scratch_pattern,
                checkpoints,
            });
        }
    }
    response.entry_contracts = entry_contracts();
    response.limiter_sequences = Some(sequences);
    Ok(response)
}
pub fn admission(d: &Decoded) -> FormAdmission {
    if crate::stateful_forms::admission(d) == FormAdmission::Allowed {
        return FormAdmission::Allowed;
    }
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    match (p.mnemonic, p.dd_mode, p.bytes_pat) {
        ("L A, #N16", 'S', ["67", "NL", "NH"])
        | ("L A, DP", 'S', ["42"])
        | ("MOV DP, off N8", 'U', ["B4", "N8", "7A"])
        | ("CMP N8, A", 'U', ["B5", "N8", "C1"])
        | ("MB C, N8.0", 'U', ["C5", "N8", "28"])
        | ("MB C, PSWL.4", 'U', ["A3", "2C"])
        | ("MB C, PSWL.5", 'U', ["A3", "2D"])
        | ("SB PSWL.5", 'U', ["A3", "1D"])
        | ("MB off N8.3, C", 'U', ["C4", "N8", "3B"])
        | ("MB off N8.4, C", 'U', ["C4", "N8", "3C"])
        | ("MB off N8.5, C", 'U', ["C4", "N8", "3D"])
        | ("RB off N8.7", 'U', ["C4", "N8", "0F"])
        | ("JBS off N8.7, rel8", 'U', ["EF", "N8", "rel8"])
        | ("JBR off N8.5, rel8", 'U', ["DD", "N8", "rel8"])
        | ("ANDB off N8, A", 'U', ["C4", "N8", "D1"])
        | ("ORB off N'8, #N8", 'U', ["C4", "N'8", "E0", "N8"])
        | ("ORB A, #N8", '0', ["E6", "N8"])
        | ("SC", 'U', ["85"])
        | ("RC", 'U', ["95"]) => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}
