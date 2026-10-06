//! M2ae: native RT exit -> bounded RAM producer, then retained next-event reader.
use crate::{
    adaptive::Stage,
    bus::Bus,
    cpu::Cpu,
    decoder::Decoded,
    full_decoder::FULL_OPCODES,
    instruction_forms::FormAdmission,
    post_store::{self, Suffix},
    protocol::{Request, Response},
    quartet_handoff as prefix,
    runner::{execute_in_state_observed, SliceContract},
    vtec_fuel::boundary,
};
use serde::{Deserialize, Serialize};
pub const OPERATION: &str = "postReturnSelectorHandoff";
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Call {
    pub prefix: post_store::Call,
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
pub struct Event {
    #[serde(flatten)]
    pub round_trip: crate::cal_rt_roundtrip::Event,
    pub post_return: Option<Suffix>,
    pub selector_before: u8,
    pub selector_after: u8,
    pub incoming_selector_generation: Option<prefix::Generation>,
    pub reader0584_generation: Option<prefix::Generation>,
    pub reader063e_generation: Option<prefix::Generation>,
    pub selector_generation: Option<prefix::Generation>,
    pub selector_handoff: &'static str,
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
    vec![serde_json::json!({
     "id":OPERATION,"formatVersion":1,"reusedBodyReference":crate::cal_rt_roundtrip::entry_contracts()[0],
     "selectorPolicyOverridesHistoricalM2xSourceOnly":"Initial0..3Once;NoPerEventSelector;NoHost013CAfterInit",
     "entry":0x063E,"entrySource":"ActualRT5688;NoHostPcWrite","stopBefore":0x064C,"budget":8,
     "codeRanges":[[0x063E,0x064C]],"pcs":[0x063E,0x0640,0x0641,0x0643,0x0646,0x0647,0x0648,0x064A],
     "selector":"RAM013CByte;Read063E;Write064A;Next0584Read;InitialGenerationNone",
     "formula":"((old+1)&255)&3;domain0..3","localR0":"LRB0021/0108;Overwritten0640BeforeUse;FinalOldPlus1",
     "history0128":"OldOR(1<<(oldSelector&1));Bit2AndNeighborsRetained;NoRepair",
     "generation":"writerPC,eventIndex,zeroBasedAllNativeEventWriteOrder,value;IncludesRAMStackP2Control",
     "interEventScheduling":"ExplicitHarnessSchedule;RAMProvenanceNotFirmwarePcContinuity",
     "partial":"RetainAllNativeWrites;LaterInputsNotRun;No0117Or0128Repair",
     "branch064C":"NotRun","otherSelectorWriters":"03D7/0551/15A0NotRun;GenericAliasesUnknown",
     "timerEvolution":"NotModeled","timerContinuation":"NotRun","irqDelivery":"NotInjected","elapsedTime":"None"
    })]
}
pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .post_return_selector_handoff
        .as_ref()
        .ok_or("M2ae stimulus required")?;
    if s.initial_selector013c > 3
        || s.tcon0_architectural_snapshot & !12 != 0x83
        || s.trnsit_architectural_flags > 15
    {
        return Err("Unadmitted M2ae initial selector/control domain".into());
    }
    prefix::validate_parts(
        r,
        s.format_version,
        &s.initial_state.quartet_prefix,
        &s.body_calls(),
        &s.trace_event_indexes,
    )
}
fn admission(d: &Decoded) -> FormAdmission {
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    match (p.mnemonic, p.dd_mode, p.bytes_pat) {
        ("LB A, off N8", 'R', ["F4", "N8"]) if d.fields.n8 == 0x3C => FormAdmission::Allowed,
        ("STB A, r0", '0', ["88"]) | ("INCB r0", 'U', ["A8"]) | ("LB A, r0", 'R', ["78"]) => {
            FormAdmission::Allowed
        }
        ("ANDB A, #N8", '0', ["D6", "N8"]) if matches!(d.fields.n8, 1 | 3) => {
            FormAdmission::Allowed
        }
        ("SBR off N8", 'U', ["C4", "N8", "11"]) if d.fields.n8 == 0x28 => FormAdmission::Allowed,
        ("STB A, off N8", '0', ["D4", "N8"]) if d.fields.n8 == 0x3C => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}
pub(crate) fn execute(cpu: &mut Cpu, bus: &mut Bus) -> Result<Suffix, String> {
    if cpu.pc != 0x063E || cpu.lrb != 0x21 || cpu.scb() != 2 || cpu.dd {
        return Err("Post-return requires retained native RT exit, not a PC/bank seed".into());
    }
    bus.configure_scoped_access(
        vec![
            [0, 8],
            [0x90, 0x98],
            [0x108, 0x110],
            [0x128, 0x129],
            [0x13C, 0x13D],
        ],
        4096,
    );
    bus.set_program_data_ranges(vec![]);
    bus.clear_program_reads();
    let entry = boundary(cpu, bus);
    bus.begin_native_accesses();
    bus.begin_write_journal();
    bus.start_decision_observer();
    let c = SliceContract {
        entry_pc: 0x063E,
        exit_pcs: vec![0x064C],
        code_ranges: vec![[0x063E, 0x064C]],
        psw: 0,
        lrb: 0,
        usp: 0,
        instruction_budget: 8,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    };
    let result = execute_in_state_observed(cpu, bus, &c, &[], true, Some(admission), true);
    let accesses = bus.end_native_accesses();
    let stage = Stage {
        result,
        writes: bus.end_write_journal(),
        events: bus.finish_decision_observer(),
        ssp_after: cpu.ssp,
    };
    Ok(Suffix {
        entry,
        exit: boundary(cpu, bus),
        stage,
        accesses,
    })
}
pub(crate) fn reader(
    journal: &[[u32; 6]],
    g: &Option<prefix::Generation>,
    pc: u32,
) -> Option<prefix::Generation> {
    let generation = g.as_ref()?;
    let at = journal
        .iter()
        .position(|a| *a == [0, pc, 0x13C, 8, 0, generation.value])?;
    if journal[..at]
        .iter()
        .any(|a| a[0] == 0 && a[4] == 1 && a[2] < 0x13D && a[2] + a[3] / 8 > 0x13C)
    {
        return None;
    }
    Some(generation.clone())
}
pub fn run(r: Request, response: Response) -> Result<Response, String> {
    let s = r.post_return_selector_handoff.as_ref().expect("validated");
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
        None,
    )
}
