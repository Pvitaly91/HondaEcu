//! M2ac: exact below continuation on the retained machine; stop before RT.
use crate::{
    adaptive::Stage,
    bus::Bus,
    cpu::Cpu,
    decoder::Decoded,
    full_decoder::FULL_OPCODES,
    instruction_forms::FormAdmission,
    post_store::Suffix,
    protocol::{Request, Response},
    quartet_handoff as prefix,
    runner::{execute_in_state_observed, SliceContract},
    vtec_fuel::boundary,
};
use serde::Serialize;
pub const OPERATION: &str = "belowSecondP2Handoff";
pub type Stimulus = crate::post_p2_control::Stimulus;
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Output {
    pub suffix: Suffix,
    pub peripheral_accesses: Vec<[u32; 5]>,
    pub control_accesses: Vec<[u32; 5]>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Event {
    #[serde(flatten)]
    pub upstream: crate::post_p2_control::Event,
    pub below: Option<Output>,
    pub second_p2_after: u8,
    pub second_p2_generation: Option<prefix::Generation>,
    pub final_tcon0: u8,
    pub final_tcon0_generation: Option<prefix::Generation>,
    /// [space:0 RAM/1 P2/2 control, pc,address,width,write,value]. Native only.
    pub all_native_journal: Vec<[u32; 6]>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Sequence {
    pub scratch_pattern: u8,
    pub machine_instances: u32,
    pub checkpoints: Vec<Event>,
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({"id":OPERATION,"formatVersion":1,
        "prefixContract":crate::post_p2_control::entry_contracts()[0],
        "entry":"Actual55CFNext55D2;NoHostJump","stopBefore":0x5688,"budget":18,
        "codeRanges":[[0x55D2,0x55DD],[0x562C,0x5636],[0x565D,0x5663],[0x5671,0x5675],[0x567E,0x5688]],
        "rolbA":"33/DD0;AL=(AL<<1)|incomingCF;AHretained;CF=oldAL7;OtherPSWRetained",
        "p2InstructionPc":0x5682,"tcon0InstructionPc":0x55D5,"newExternalSources":0,
        "belowContinuation":"NativeContinuousControlFlow","returnFrame":"NotEstablished;RTNotRun",
        "chronology":"0RAM/1P2/2Control,PC,address,width,write,value;NativeOnly;AllWritesOrdinal",
        "timerEvolution":"NotModeled","timerContinuation":"NotRun","irqDelivery":"NotInjected","elapsedTime":"None","physicalOutput":"NotRun"})]
}
pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .below_second_p2_handoff
        .as_ref()
        .ok_or("M2ac stimulus required")?;
    if s.tcon0_architectural_snapshot & !12 != 0x83 || s.trnsit_architectural_flags > 15 {
        return Err("Unadmitted control domain".into());
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
        ("ROLB A", '0', ["33"])
        | ("STB A, off N8", '0', ["D4", "N8"])
        | ("RB N8.2", 'U', ["C5", "N8", "0A"])
        | ("L A, #N16", 'S', ["67", "NL", "NH"])
        | ("SJ rel8", 'U', ["CB", "rel8"])
        | ("ST A, off N8", '1', ["D4", "N8"])
        | ("J addr16", 'U', ["03", "addrl", "addrh"])
        | ("L A, off N8", 'S', ["E4", "N8"])
        | ("JNE rel8", 'U', ["CE", "rel8"])
        | ("LB A, off N8", 'R', ["F4", "N8"])
        | ("ORB A, off N8", 'U', ["E7", "N8"])
        | ("ANDB A, #N8", '0', ["D6", "N8"])
        | ("ORB N8, A", 'U', ["C5", "N8", "E1"])
        | ("RB off N8.7", 'U', ["C4", "N8", "0F"]) => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}
pub(crate) fn execute(cpu: &mut Cpu, bus: &mut Bus) -> Output {
    bus.configure_scoped_access(
        vec![
            [0, 8],
            [0x24, 0x25],
            [0x40, 0x41],
            [0x90, 0x98],
            [0x108, 0x118],
            [0x12A, 0x12B],
            [0x18F, 0x190],
        ],
        4096,
    );
    bus.set_program_data_ranges(vec![]);
    bus.clear_program_reads();
    let entry = boundary(cpu, bus);
    bus.begin_native_accesses();
    bus.begin_write_journal();
    bus.start_decision_observer();
    bus.begin_p2_accesses();
    bus.set_p2_access_pc(Some(0x5682));
    bus.set_control_access(Some((0x40, 0x55D5)));
    let contract = SliceContract {
        entry_pc: cpu.pc,
        exit_pcs: vec![0x5688],
        code_ranges: vec![
            [0x55D2, 0x55DD],
            [0x562C, 0x5636],
            [0x565D, 0x5663],
            [0x5671, 0x5675],
            [0x567E, 0x5688],
        ],
        psw: 0,
        lrb: 0,
        usp: 0,
        instruction_budget: 18,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    };
    let result = execute_in_state_observed(cpu, bus, &contract, &[], true, Some(admission), true);
    let peripheral_accesses = bus.p2_accesses();
    let control_accesses = bus.control_accesses();
    bus.set_p2_access_pc(None);
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
        peripheral_accesses,
        control_accesses,
    }
}
pub fn run(r: Request, response: Response) -> Result<Response, String> {
    let s = r.below_second_p2_handoff.as_ref().expect("validated");
    crate::p2_latch::run_chain(
        &r,
        &s.initial_state,
        &s.calls,
        s.p2_output_latch,
        response,
        Some(crate::post_p2_control::Config {
            tcon0: s.tcon0_architectural_snapshot,
            trnsit_flags: s.trnsit_architectural_flags,
        }),
        true,
    )
}
