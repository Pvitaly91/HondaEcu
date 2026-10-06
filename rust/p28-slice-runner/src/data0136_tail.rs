//! Separate post-NoWrite prefix. Unowned scratch bits cannot become branch sources.
use crate::{
    adaptive::Stage,
    bus::Bus,
    cal_rt_roundtrip::Frame,
    cpu::Cpu,
    decoder::Decoded,
    exec::{read_data_u16, read_data_u8},
    full_decoder::FULL_OPCODES,
    instruction_forms::FormAdmission,
    post_store::Suffix,
    protocol::{Request, Response},
    runner::{execute_in_state_observed, SliceContract},
    vtec_fuel::boundary,
};
use serde::Serialize;
pub const OPERATION: &str = "data0136TailToTimerBoundary";
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Output {
    pub suffix: Suffix,
    pub pending_frame: Frame,
    pub frame_word_before: u16,
    pub frame_word_after: u16,
    pub retained0136_before: u16,
    pub retained0136_after: u16,
    pub diagnostic019b: u8,
    pub live_in_classification: &'static str,
    pub disposition: &'static str,
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({"id":OPERATION,"formatVersion":1,
        "reusedBodyReference":crate::fallthrough_data0136::entry_contracts()[0],
        "entry":0x5719,"entrySource":"NativeContinuationFromM2ag;NoHostStateChange",
        "codeRanges":[[0x5719,0x571F]],"instructionBudget":2,
        "exits":[0x5722,0x571F],"liveInBoundary":[0x5722,0x19B,2],
        "ownership":"RB05D5OwnsBit0Only;ScratchBit2NotSemanticSource;NoNewFields",
        "goalBoundary":0x5793,"timerBoundary":"TM3At5793;NotReached",
        "fresh0136":"None;RetainedHistory;ReadersNotRun",
        "frame":"Native0664FramePending;NoPopRewriteOrSSPRepair",
        "newPeripheralSources":[],"tailPeripheralReads":0,
        "sequenceTerminal":"AllBoundaries;LaterEventsNotRunNoInputsApplied",
        "jle":"PrimaryLE_CF_OR_ZF;StaticOnlyPastLiveInBoundary",
        "jgt233a":"BlockedUnchanged","timerEvolution":"NotModeled",
        "irqDelivery":"NotInjected","elapsedTime":"None","physicalRpmAvailable":false})]
}
pub(crate) fn admission(d: &Decoded) -> FormAdmission {
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    let allowed = match (p.mnemonic, p.dd_mode, p.bytes_pat) {
        ("CMPB N'8, #N8", 'U', ["C5", "N'8", "C0", "N8"]) => {
            d.fields.n8_alt == 0xA2 && d.fields.n8 == 5
        }
        ("JNE rel8", 'U', ["CE", "rel8"]) => d.fields.rel8 == 3,
        _ => false,
    };
    if allowed {
        FormAdmission::Allowed
    } else {
        FormAdmission::Unsupported
    }
}
pub(crate) fn execute(cpu: &mut Cpu, bus: &mut Bus, frame: &Frame) -> Result<Output, String> {
    if cpu.pc != 0x5719
        || cpu.lrb != 0x21
        || cpu.scb() != 2
        || !cpu.dd
        || cpu.sf
        || frame.writer_pc != 0x0664
        || frame.width != 16
        || frame.return_pc != 0x0667
        || frame.stack_address < 0x700
        || frame.stack_address > 0x7FE
        || frame.stack_address & 1 != 0
        || u32::from(cpu.ssp) + 2 != frame.stack_address
    {
        return Err("Detached post-NoWrite entry or repaired pending frame".into());
    }
    let address = frame.stack_address as u16;
    bus.configure_scoped_access(
        vec![
            [0, 8],
            [0x90, 0x98],
            [0xA2, 0xA3],
            [0x108, 0x110],
            [0x136, 0x138],
            [0x19B, 0x19C],
            [address, address + 2],
        ],
        4096,
    );
    let frame_word_before = read_data_u16(cpu, bus, address);
    if frame_word_before != 0x0667 || read_data_u8(cpu, bus, 0xA2) != 0 {
        return Err("Invalid retained frame/slot; no repair allowed".into());
    }
    let retained0136_before = read_data_u16(cpu, bus, 0x136);
    // Inspection is NOT an executed JBS read or an admitted branch stimulus.
    let diagnostic019b = read_data_u8(cpu, bus, 0x19B);
    bus.observe_capture(None);
    bus.set_program_data_ranges(vec![]);
    bus.clear_program_reads();
    let entry = boundary(cpu, bus);
    bus.begin_native_accesses();
    bus.begin_write_journal();
    bus.start_decision_observer();
    let contract = SliceContract {
        entry_pc: 0x5719,
        exit_pcs: vec![0x5722, 0x571F],
        code_ranges: vec![[0x5719, 0x571F]],
        psw: 0,
        lrb: 0,
        usp: 0,
        instruction_budget: 2,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    };
    let result = execute_in_state_observed(cpu, bus, &contract, &[], true, Some(admission), true);
    let accesses = bus.end_native_accesses();
    let writes = bus.end_write_journal();
    let events = bus.finish_decision_observer();
    let disposition = if result.status == 0 && cpu.pc == 0x5722 {
        "TailLiveInBlocked"
    } else {
        "TailExecutionPartial"
    };
    let suffix = Suffix {
        entry,
        exit: boundary(cpu, bus),
        stage: Stage {
            result,
            writes,
            events,
            ssp_after: cpu.ssp,
        },
        accesses,
    };
    let frame_word_after = read_data_u16(cpu, bus, address);
    let retained0136_after = read_data_u16(cpu, bus, 0x136);
    Ok(Output {
        suffix,
        pending_frame: frame.clone(),
        frame_word_before,
        frame_word_after,
        retained0136_before,
        retained0136_after,
        diagnostic019b,
        live_in_classification: "019BBit2Unowned;DiagnosticScratchOnly;STOPBefore5722",
        disposition,
    })
}
pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .data0136_tail_to_timer_boundary
        .as_ref()
        .ok_or("M2ah stimulus required")?;
    crate::fallthrough_data0136::validate_parts(r, s)
}
pub fn run(r: Request, response: Response) -> Result<Response, String> {
    let s = r
        .data0136_tail_to_timer_boundary
        .as_ref()
        .expect("validated");
    crate::p2_latch::run_chain(
        &r,
        &s.initial_state,
        &s.body_calls(),
        s.p2_output_latch,
        response,
        Some(crate::post_p2_control::Config {
            tcon0: s.tcon0_architectural_snapshot,
            trnsit_flags: s.trnsit_architectural_flags,
        }),
        true,
        true,
        Some(s.initial_selector013c),
        Some(s),
    )
}
