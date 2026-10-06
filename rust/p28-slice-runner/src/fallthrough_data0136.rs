//! Separate native caller continuation. No entry ABI, slot, history or stack seed.
use crate::{
    adaptive::Stage,
    bus::Bus,
    cpu::Cpu,
    decoder::Decoded,
    exec::{read_data_u16, read_data_u8},
    full_decoder::FULL_OPCODES,
    instruction_forms::FormAdmission,
    post_store::{self, Suffix},
    protocol::{Request, Response},
    quartet_handoff as prefix,
    runner::{execute_in_state_observed, SliceContract},
    vtec_fuel::boundary,
};
use serde::{Deserialize, Serialize};
pub const OPERATION: &str = "fallthroughData0136CallerHandoff";
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Observation {
    pub tmr2: u16,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub irqh: Option<u8>,
}
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Call {
    pub prefix: post_store::Call,
    pub producer_observation: Observation,
}
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Stimulus {
    pub format_version: u32,
    pub initial_state: crate::word0196_handoff::Initial,
    pub initial_selector013c: u8,
    pub calls: Vec<Call>,
    pub trace_event_indexes: Vec<u32>,
    pub p2_output_latch: u8,
    pub tcon0_architectural_snapshot: u8,
    pub trnsit_architectural_flags: u8,
}
impl Stimulus {
    fn body_calls(&self) -> Vec<prefix::Call> {
        self.calls
            .iter()
            .map(|c| prefix::Call {
                prefix: post_store::Call {
                    adaptive: c.prefix.adaptive.clone(),
                    disable125: c.prefix.disable125,
                    disable12e: c.prefix.disable12e,
                },
                selector013c: 0,
            })
            .collect()
    }
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Producer {
    pub suffix: Suffix,
    pub ram_before: Vec<u8>,
    pub ram_after: Vec<u8>,
    pub peripheral_accesses: Vec<[u32; 5]>,
    pub frozen_observation: Observation,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Event {
    #[serde(flatten)]
    pub selector: crate::post_return_selector::Event,
    pub caller: Option<crate::cal_rt_roundtrip::Output>,
    pub producer: Option<Producer>,
    pub producer_call_frame: Option<crate::cal_rt_roundtrip::Frame>,
    pub pending_return_word: Option<u16>,
    pub caller_route: &'static str,
    pub producer_admission: &'static str,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Sequence {
    pub scratch_pattern: u8,
    pub machine_instances: u32,
    pub selector_initialization_writes: Vec<[u32; 3]>,
    pub checkpoints: Vec<Event>,
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({"id":OPERATION,"formatVersion":1,
      "reusedBodyReference":crate::post_return_selector::entry_contracts()[0],
      "entry":0x064C,"entrySource":"NativeContinuationFromM2ae;NoHostPcOrABIWrite",
      "callerCodeRanges":[[0x064C,0x0657],[0x065F,0x0667]],"callerBudget":7,
      "callerExits":[0x56BE,0x0657,0x0667],"cal":[0x0664,3,0x56BE,0x0667],
      "callerGates":"OneRetained011FByte;Existing011B7;Old012A0/3ZF;NoRepair",
      "producerCodeRanges":[[0x56BE,0x56C3],[0x56C5,0x56D9],[0x5713,0x5719]],
      "producerBudget":128,"stopBefore":0x5719,
      "producerAdmission":"Mode0;RetainedSlot0;Old0128Bit3Clear;NoTechnicalEntry",
      "frozenSources":"TMR2WordAlways;IRQHByteIffTMR2Bit15Clear;TCON2Unavailable",
      "chronology":"0RAM/1P2/2Control/3FrozenCapture,PC,address,width,write,value;AllNativeWritesOrdinal",
      "frame":"Native0664AtOldSSP;Return0667;PendingAt5719;NoPopOrReseed",
      "sequenceTerminal":"AfterCallerBoundary;LaterEventsNotRunNoInputsApplied",
      "m2afPrimaryTakenRoute":"BlockedUnchanged;AAControlNotCallerSuccess",
      "timerEvolution":"NotModeled","irqDelivery":"NotInjected","elapsedTime":"None",
      "producerTo2330SchedulerSeam":"NotEstablished","physicalRpmAvailable":false})]
}
pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .fallthrough_data0136_caller_handoff
        .as_ref()
        .ok_or("M2ag stimulus required")?;
    if s.initial_selector013c > 3
        || s.tcon0_architectural_snapshot & !12 != 0x83
        || s.trnsit_architectural_flags > 15
        || s.calls.iter().any(|c| {
            c.producer_observation.irqh.is_some() != (c.producer_observation.tmr2 & 0x8000 == 0)
        })
    {
        return Err("Closed M2ag selector/control/frozen observation domain".into());
    }
    prefix::validate_parts(
        r,
        s.format_version,
        &s.initial_state.quartet_prefix,
        &s.body_calls(),
        &s.trace_event_indexes,
    )
}
fn caller_admission(d: &Decoded) -> FormAdmission {
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    let yes = match (p.mnemonic, p.dd_mode, p.bytes_pat) {
        ("JBS off N8.3, rel8", 'U', ["EB", "N8", "rel8"]) => {
            d.fields.n8 == 0x1F && d.fields.rel8 == 16
        }
        ("JBS off N8.7, rel8", 'U', ["EF", "N8", "rel8"]) => {
            d.fields.n8 == 0x1B && d.fields.rel8 == 13
        }
        ("RB off N8.0", 'U', ["C4", "N8", "08"]) | ("RB off N8.3", 'U', ["C4", "N8", "0B"]) => {
            d.fields.n8 == 0x2A
        }
        ("JEQ rel8", 'U', ["C9", "rel8"]) => d.fields.rel8 == 8,
        ("JNE rel8", 'U', ["CE", "rel8"]) => d.fields.rel8 == 3,
        ("CAL addr16", 'U', ["32", "addrl", "addrh"]) => d.fields.addr16 == 0x56BE,
        _ => false,
    };
    if yes {
        FormAdmission::Allowed
    } else {
        FormAdmission::Unsupported
    }
}
pub(crate) fn execute_caller(
    cpu: &mut Cpu,
    bus: &mut Bus,
) -> Result<crate::cal_rt_roundtrip::Output, String> {
    if cpu.pc != 0x064C
        || cpu.lrb != 0x21
        || cpu.scb() != 2
        || cpu.dd
        || cpu.sf
        || cpu.ssp & 1 != 0
        || !(0x700..=0x7FE).contains(&cpu.ssp)
    {
        return Err("Detached/unsafe native M2ae caller boundary".into());
    }
    bus.configure_scoped_access(
        vec![
            [0, 8],
            [0x90, 0x98],
            [0x108, 0x110],
            [0x11B, 0x11C],
            [0x11F, 0x120],
            [0x12A, 0x12B],
            [cpu.ssp, cpu.ssp + 2],
        ],
        4096,
    );
    bus.set_program_data_ranges(vec![]);
    bus.clear_program_reads();
    let entry = boundary(cpu, bus);
    let sf_before = cpu.sf;
    bus.begin_native_accesses();
    bus.begin_write_journal();
    bus.start_decision_observer();
    let c = SliceContract {
        entry_pc: 0x064C,
        exit_pcs: vec![0x56BE, 0x0657, 0x0667],
        code_ranges: vec![[0x064C, 0x0657], [0x065F, 0x0667]],
        psw: 0,
        lrb: 0,
        usp: 0,
        instruction_budget: 7,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    };
    let result = execute_in_state_observed(cpu, bus, &c, &[], true, Some(caller_admission), true);
    let accesses = bus.end_native_accesses();
    let writes = bus.end_write_journal();
    let events = bus.finish_decision_observer();
    Ok(crate::cal_rt_roundtrip::Output {
        suffix: Suffix {
            entry,
            exit: boundary(cpu, bus),
            stage: Stage {
                result,
                writes,
                events,
                ssp_after: cpu.ssp,
            },
            accesses,
        },
        sf_before,
        sf_after: cpu.sf,
    })
}
fn no_write_admission(d: &Decoded) -> FormAdmission {
    if crate::data0136_technical::form_admission(d) != FormAdmission::Allowed {
        return FormAdmission::Unsupported;
    }
    let p = &FULL_OPCODES[d.index];
    let yes = match (p.mnemonic, p.dd_mode, p.bytes_pat) {
        ("L A, N8", 'S', ["E5", "N8"]) => d.fields.n8 == 0x3A,
        ("L A, er3", 'S', ["37"]) | ("ST A, er3", '1', ["8B"]) => true,
        ("JBR off N8.2, rel8", 'U', ["DA", "N8", "rel8"]) => {
            d.fields.n8 == 0x1F && d.fields.rel8 == 2
        }
        ("JBS off N8.7, rel8", 'U', ["EF", "N8", "rel8"]) => {
            d.fields.n8 == 0x0F && d.fields.rel8 == 11
        }
        ("MB C, N8.0", 'U', ["C5", "N8", "28"]) => d.fields.n8 == 0x19,
        ("JGE rel8", 'U', ["CD", "rel8"]) => d.fields.rel8 == 6,
        ("INCB N8", 'U', ["C5", "N8", "16"]) | ("CLRB N8", 'U', ["C5", "N8", "15"]) => {
            d.fields.n8 == 0xAE
        }
        ("SB N8.0", 'U', ["C5", "N8", "18"]) => d.fields.n8 == 0xB6,
        ("SB off N8.3", 'U', ["C4", "N8", "1B"]) => d.fields.n8 == 0x28,
        ("JEQ rel8", 'U', ["C9", "rel8"]) => d.fields.rel8 == 58,
        ("ST A, N8", '1', ["D5", "N8"]) => d.fields.n8 == 0xEE,
        _ => false,
    };
    if yes {
        FormAdmission::Allowed
    } else {
        FormAdmission::Unsupported
    }
}
pub(crate) fn producer_admission(cpu: &Cpu, bus: &mut Bus) -> &'static str {
    crate::data0136_technical::configure(bus);
    if cpu.pc != 0x56BE || cpu.lrb != 0x21 || cpu.scb() != 2 {
        return "ProducerEntryAbiBlocked";
    }
    if read_data_u8(cpu, bus, 0x11F) & 4 != 0 || read_data_u8(cpu, bus, 0xA2) != 0 {
        return "ProducerEntryModeSlotBlockedControl";
    }
    if read_data_u8(cpu, bus, 0x128) & 8 != 0 {
        return "ProducerEntryFreshGateBlocked";
    }
    "Mode0RetainedSlot0FirstObservation"
}
/// Actual current machine only. Unlike historical execute_in_state, no enter,
/// RAM initializer, slot/00F0 application, PC/PSW/bank/pointer/SSP assignment.
pub(crate) fn execute_no_write_body(
    cpu: &mut Cpu,
    bus: &mut Bus,
    o: &Observation,
) -> Result<Producer, String> {
    if producer_admission(cpu, bus) != "Mode0RetainedSlot0FirstObservation" {
        return Err("Unadmitted retained no-write producer state".into());
    }
    let before = crate::data0136_technical::ram(cpu, bus);
    bus.configure_scoped_access(
        vec![
            [0, 8],
            [0x19, 0x1A],
            [0x3A, 0x3C],
            [0x90, 0x98],
            [0xA2, 0xA3],
            [0xAE, 0xAF],
            [0xB6, 0xB7],
            [0xEE, 0xF2],
            [0x108, 0x110],
            [0x11F, 0x120],
            [0x128, 0x129],
            [0x136, 0x138],
            [0x360, 0x36C],
        ],
        4096,
    );
    bus.set_program_data_ranges(vec![]);
    bus.clear_program_reads();
    let entry = boundary(cpu, bus);
    bus.observe_no_write_capture(o.tmr2, o.irqh);
    bus.begin_native_accesses();
    bus.begin_write_journal();
    bus.start_decision_observer();
    let c = SliceContract {
        entry_pc: 0x56BE,
        exit_pcs: vec![0x5719],
        code_ranges: vec![[0x56BE, 0x56C3], [0x56C5, 0x56D9], [0x5713, 0x5719]],
        psw: 0,
        lrb: 0,
        usp: 0,
        instruction_budget: 128,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    };
    let result = execute_in_state_observed(cpu, bus, &c, &[], true, Some(no_write_admission), true);
    let accesses = bus.end_native_accesses();
    let writes = bus.end_write_journal();
    let events = bus.finish_decision_observer();
    let peripheral_accesses = bus
        .all_native_snapshot()
        .iter()
        .filter(|a| a[0] == 3)
        .map(|a| [a[1], a[2], a[3], a[4], a[5]])
        .collect();
    bus.observe_capture(None);
    let exit = boundary(cpu, bus);
    crate::data0136_technical::configure(bus);
    let after = crate::data0136_technical::ram(cpu, bus);
    Ok(Producer {
        suffix: Suffix {
            entry,
            exit,
            stage: Stage {
                result,
                writes,
                events,
                ssp_after: cpu.ssp,
            },
            accesses,
        },
        ram_before: before,
        ram_after: after,
        peripheral_accesses,
        frozen_observation: o.clone(),
    })
}
pub(crate) fn pending_word(cpu: &Cpu, bus: &mut Bus, address: u16) -> u16 {
    bus.configure_scoped_access(vec![[address, address + 2]], 4096);
    read_data_u16(cpu, bus, address)
}
pub fn run(r: Request, response: Response) -> Result<Response, String> {
    let s = r
        .fallthrough_data0136_caller_handoff
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
