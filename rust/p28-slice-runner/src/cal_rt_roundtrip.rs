//! Exact real-callsite instruction and normal return, not enclosing IRQ recovery.
use crate::{
    adaptive::Stage,
    bus::Bus,
    cpu::Cpu,
    decoder::Decoded,
    full_decoder::FULL_OPCODES,
    instruction_forms::FormAdmission,
    post_store::Suffix,
    protocol::{Request, Response},
    runner::{execute_in_state_observed, SliceContract},
    vtec_fuel::boundary,
};
use serde::Serialize;
pub const OPERATION: &str = "calRtRoundTripHandoff";
pub type Stimulus = crate::below_second_p2::Stimulus;
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Output {
    pub suffix: Suffix,
    pub sf_before: bool,
    pub sf_after: bool,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Frame {
    pub writer_pc: u32,
    pub event_index: u32,
    pub stack_address: u32,
    pub width: u32,
    pub return_pc: u32,
    pub write_order: u32,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Event {
    #[serde(flatten)]
    pub below: crate::below_second_p2::Event,
    pub native_cal: Option<Output>,
    pub native_rt: Option<Output>,
    pub call_frame: Option<Frame>,
    /// [PC,address,width,write,value], native only; stack is RAM in allNativeJournal.
    pub stack_journal: Vec<[u32; 5]>,
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
      "prefixContract":crate::below_second_p2::entry_contracts()[0],
      "schedule":[0x05ED,0x063B],"scheduleKind":"ExplicitHarnessSchedule;PCOnly",
      "cal":[0x063B,3,0x54F5,0x063E],"rt":[0x5688,1,0x063E],
      "stack":"WordAtOldSSP;ThenSSPMinus2;RTPlus2ThenRead;Even;Retained;NoWrap",
      "frameSource":"NativeCAL063B","frameIdentity":"writerPC,eventIndex,stackAddress,width,returnPC,zeroBasedAllNativeEventWriteOrder",
      "flags":"CAL/RT:PSWUnchanged;SF0InternalAMode;NotPSW;RTDoesNotRestoreA/LRB",
      "stopBefore":0x063E,"budgetPerCallReturnInstruction":1,
      "entry":"TechnicalSeededRealCallsiteEntry","enclosingCallerPath":"NotRun",
      "enclosingIRQFrame":"NotEstablished","irqDelivery":"NotInjected",
      "recoveredCallerScheduler":"NotEstablished","directTechnical54F5Schedule":"NotUsedInM2ad"})]
}
pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .cal_rt_round_trip_handoff
        .as_ref()
        .ok_or("M2ad stimulus required")?;
    crate::quartet_handoff::validate_parts(
        r,
        s.format_version,
        &s.initial_state.quartet_prefix,
        &s.calls,
        &s.trace_event_indexes,
    )?;
    if s.tcon0_architectural_snapshot & !12 != 0x83 || s.trnsit_architectural_flags > 15 {
        return Err("Unadmitted control domain".into());
    }
    Ok(())
}
fn admission(d: &Decoded) -> FormAdmission {
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    match (p.mnemonic, p.dd_mode, p.bytes_pat) {
        ("CAL addr16", 'U', ["32", "addrl", "addrh"]) if d.fields.addr16 == 0x54F5 => {
            FormAdmission::Allowed
        }
        ("RT", 'U', ["01"]) => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}
pub(crate) fn execute(cpu: &mut Cpu, bus: &mut Bus, call: bool) -> Result<Output, String> {
    // Only the retained technical stack domain. No wrap, odd pointer, register,
    // software-field or peripheral collision; no alternate target/stack seed API.
    let address = if call {
        cpu.ssp
    } else {
        cpu.ssp.checked_add(2).ok_or("SSP wraps")?
    };
    if address & 1 != 0 || !(0x700..=0x7FE).contains(&address) || (call && cpu.ssp < 2) {
        return Err("Retained system stack outside reviewed even bounded domain".into());
    }
    let entry_pc = if call { 0x063B } else { 0x5688 };
    if cpu.pc != entry_pc {
        return Err("Detached native call/return entry".into());
    }
    bus.configure_scoped_access(
        vec![[0, 8], [0x90, 0x98], [0x108, 0x110], [address, address + 2]],
        4096,
    );
    bus.set_program_data_ranges(vec![]);
    bus.clear_program_reads();
    let entry = boundary(cpu, bus);
    let sf_before = cpu.sf;
    bus.begin_native_accesses();
    bus.begin_write_journal();
    bus.start_decision_observer();
    let contract = SliceContract {
        entry_pc,
        exit_pcs: vec![if call { 0x54F5 } else { 0x063E }],
        code_ranges: vec![[entry_pc as u32, entry_pc as u32 + if call { 3 } else { 1 }]],
        psw: 0,
        lrb: 0,
        usp: 0,
        instruction_budget: 1,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    };
    let result = execute_in_state_observed(cpu, bus, &contract, &[], true, Some(admission), true);
    let accesses = bus.end_native_accesses();
    let stage = Stage {
        result,
        writes: bus.end_write_journal(),
        events: bus.finish_decision_observer(),
        ssp_after: cpu.ssp,
    };
    Ok(Output {
        suffix: Suffix {
            entry,
            exit: boundary(cpu, bus),
            stage,
            accesses,
        },
        sf_before,
        sf_after: cpu.sf,
    })
}
pub fn run(r: Request, response: Response) -> Result<Response, String> {
    let s = r.cal_rt_round_trip_handoff.as_ref().expect("validated");
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
        true,
        None,
    )
}
