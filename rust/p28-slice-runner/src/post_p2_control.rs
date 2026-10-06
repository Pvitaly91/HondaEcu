//! M2ab: CPU-visible storage only; no timer/edge/IRQ/physical output evolution.
use crate::{
    adaptive::Stage,
    bus::Bus,
    cpu::Cpu,
    decoder::Decoded,
    full_decoder::FULL_OPCODES,
    instruction_forms::FormAdmission,
    p2_latch,
    post_store::Suffix,
    protocol::{Request, Response},
    quartet_handoff as prefix,
    runner::{execute_in_state_observed, SliceContract},
    vtec_fuel::boundary,
    word0196_handoff as handoff,
};
use serde::{Deserialize, Serialize};
pub const OPERATION: &str = "postP2ControlHandoff";
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Stimulus {
    pub format_version: u32,
    pub initial_state: handoff::Initial,
    pub calls: Vec<prefix::Call>,
    pub trace_event_indexes: Vec<u32>,
    pub p2_output_latch: u8,
    pub tcon0_architectural_snapshot: u8,
    pub trnsit_architectural_flags: u8,
}
#[derive(Clone, Copy)]
pub(crate) struct Config {
    pub tcon0: u8,
    pub trnsit_flags: u8,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Output {
    pub suffix: Suffix,
    pub control_accesses: Vec<[u32; 5]>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Event {
    #[serde(flatten)]
    pub p2: p2_latch::Event,
    pub control: Option<Output>,
    /// [TCON0 byte, TRNSIT implemented low nibble]; no hidden device phase.
    pub control_before: [u8; 2],
    pub control_after: [u8; 2],
    pub incoming_tcon0_generation: Option<prefix::Generation>,
    pub tcon0_generation: Option<prefix::Generation>,
    pub incoming_trnsit_generation: Option<prefix::Generation>,
    pub trnsit_generation: Option<prefix::Generation>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Sequence {
    pub scratch_pattern: u8,
    pub machine_instances: u32,
    pub checkpoints: Vec<Event>,
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![
        serde_json::json!({"id":OPERATION,"formatVersion":1,"prefixContract":p2_latch::entry_contracts()[0],
        "controlAddresses":[0x40,0x46],"width":8,"entryPcs":[0x5599,0x55C8],"stopBefore":[0x559D,0x55D2],"budget":4,
        "tcon0Domain":"83,87,8B,8F;RealtimeOutput;RUN0;Clock100;NoCompareTransfer",
        "trnsitDomain":"Flags0..15;NonexistentBitsRead1;NoExternalEdges",
        "initialSource":"RawArchitecturalSnapshot;OnceOnly;NotResetOrBoot",
        "scope":"ExactControlInstructionPCAndAddress;NativeOnly;NoHostWrite",
        "journal":"SeparateControl;PC,address,width,write,value;NotRAMOrP2",
        "generation":"writerPC,eventIndex,zeroBasedAllNativeEventWriteOrder,value;SameValueFresh",
        "timerEvolution":"NotModeled","timerContinuation":"NotRun","irqDelivery":"NotInjected","elapsedTime":"None","physicalOutput":"NotRun"}),
    ]
}
pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .post_p2_control_handoff
        .as_ref()
        .ok_or("M2ab stimulus required")?;
    if s.tcon0_architectural_snapshot & !0x0C != 0x83 || s.trnsit_architectural_flags > 15 {
        return Err("Unadmitted TCON0 running/mode/clock domain or TRNSIT reserved bits".into());
    }
    prefix::validate_parts(
        r,
        s.format_version,
        &s.initial_state.quartet_prefix,
        &s.calls,
        &s.trace_event_indexes,
    )
}
pub fn admission(d: &Decoded) -> FormAdmission {
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    match (p.mnemonic, p.dd_mode, p.bytes_pat) {
        ("ANDB N'8, #N8", 'U', ["C5", "N'8", "D0", "N8"])
        | ("SB N8.2", 'U', ["C5", "N8", "1A"])
        | ("LB A, off N8", 'R', ["F4", "N8"])
        | ("XORB A, #N8", '0', ["F6", "N8"])
        | ("MB C, N8.7", 'U', ["C5", "N8", "2F"]) => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}
pub(crate) fn execute_control(cpu: &mut Cpu, bus: &mut Bus) -> Output {
    let entry_pc = cpu.pc;
    let address = match entry_pc {
        0x5599 => 0x46,
        0x55C8 => 0x40,
        _ => 0xFFFF,
    };
    bus.configure_scoped_access(
        vec![
            [0, 8],
            [address, address.saturating_add(1)],
            [0x90, 0x98],
            [0x108, 0x110],
            [0x18E, 0x18F],
        ],
        4096,
    );
    bus.set_program_data_ranges(vec![]);
    bus.clear_program_reads();
    let entry = boundary(cpu, bus);
    bus.begin_native_accesses();
    bus.begin_write_journal();
    bus.start_decision_observer();
    bus.set_control_access(Some((address, entry_pc)));
    let contract = SliceContract {
        entry_pc,
        exit_pcs: vec![0x559D, 0x55D2],
        code_ranges: vec![[0x5599, 0x559D], [0x55C8, 0x55D2]],
        psw: 0,
        lrb: 0,
        usp: 0,
        instruction_budget: 4,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    };
    let result = execute_in_state_observed(cpu, bus, &contract, &[], true, Some(admission), true);
    let control_accesses = bus.control_accesses();
    bus.set_control_access(None);
    let accesses = bus.end_native_accesses();
    let stage = Stage {
        result,
        writes: bus.end_write_journal(),
        events: bus.finish_decision_observer(),
        ssp_after: cpu.ssp,
    };
    Output {
        suffix: Suffix {
            entry,
            exit: boundary(cpu, bus),
            stage,
            accesses,
        },
        control_accesses,
    }
}
pub fn run(r: Request, response: Response) -> Result<Response, String> {
    let s = r.post_p2_control_handoff.as_ref().expect("validated");
    p2_latch::run_chain(
        &r,
        &s.initial_state,
        &s.calls,
        s.p2_output_latch,
        response,
        Some(Config {
            tcon0: s.tcon0_architectural_snapshot,
            trnsit_flags: s.trnsit_architectural_flags,
        }),
        false,
        false,
        None,
        None,
    )
}
