//! M2v technical entry only. Sources are applied before native journaling.
//! No recovered caller, scheduler, time, or IRQ delivery.
use crate::bus::{Bus, CaptureObservation};
use crate::cpu::Cpu;
use crate::decoder::Decoded;
use crate::exec::{read_data_u8, write_data_u16, write_data_u8};
use crate::full_decoder::FULL_OPCODES;
use crate::instruction_forms::{acquisition_form_admission, FormAdmission};
use crate::protocol::{CaseResult, Request, Response};
use crate::runner::{execute_in_state_observed, seed_machine, SliceContract};
use serde::{Deserialize, Serialize};

pub const OPERATION: &str = "data0136TechnicalProducer";

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct InitialState {
    pub previous00ee: u16,
    pub counter00ae: u8,
    pub data00b6: u8,
    pub data011f: u8,
    pub data0128: u8,
    pub history0136: u16,
    pub samples: [u16; 6],
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Observation {
    pub index: u32,
    pub tmr2: u16,
    pub irqh: u8,
    pub tcon2: u8,
    pub slot: u8,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub source00f0: Option<u16>,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Stimulus {
    pub format_version: u32,
    pub initial_state: InitialState,
    pub observations: Vec<Observation>,
    pub trace_observation_indexes: Vec<u32>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Checkpoint {
    pub index: u32,
    pub result: Option<CaseResult>,
    /// [address,width,value]. Explicit host applications, never NativeWritten.
    pub source_applications: Vec<[u32; 3]>,
    pub entry: Option<crate::vtec_fuel::CpuBoundary>,
    pub exit: Option<crate::vtec_fuel::CpuBoundary>,
    pub ram_before: Vec<u8>,
    pub ram_after: Vec<u8>,
    pub events: Vec<[u32; 8]>,
    pub accesses: Vec<[u32; 5]>,
    pub writes: Vec<[u32; 3]>,
    pub peripheral_accesses: Vec<[u32; 4]>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Sequence {
    pub image_index: usize,
    pub scratch_pattern: u8,
    pub completed_observations: u32,
    pub checkpoints: Vec<Checkpoint>,
}

pub fn form_admission(d: &Decoded) -> FormAdmission {
    if acquisition_form_admission(d) == FormAdmission::Allowed {
        return FormAdmission::Allowed;
    }
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    match (p.mnemonic, p.dd_mode, p.bytes_pat) {
        ("CLRB r1", 'U', ["21", "15"])
        | ("MOVB r0, N8", 'U', ["C5", "N8", "48"])
        | ("SBCB r0, #N8", 'U', ["20", "B0", "N8"])
        | ("MOV er2, #N16", 'U', ["46", "98", "NL", "NH"])
        | ("DIV", 'U', ["90", "37"])
        | ("CMPB r0, #N8", 'U', ["20", "C0", "N8"])
        | ("MOV X1, #N16", 'U', ["60", "NL", "NH"])
        | ("DEC X1", 'U', ["80"])
        | ("JNE rel8", 'U', ["CE", "rel8"])
        | ("SJ rel8", 'U', ["CB", "rel8"]) => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![
        serde_json::json!({"id":OPERATION,"entryClassification":"TechnicalSeededEntry56BE",
        "entryPc":0x56BE,"exitPcs":[0x5719],"stop":"BeforeInstruction",
        "allowedCodeRanges":[[0x56BE,0x5719]],"psw":0x1102,"lrb":0x21,
        "scb":2,"usp":0x280,"ssp":0x7FE,"instructionBudget":128,
        "mandatoryFirstRead":[0x3A,16],"conditionalPeripheralReads":[[0x19,8],[0x42,8]],
        "peripheralWrites":[],"readEffects":"NondestructiveFrozenSnapshotNoNewEventNoInterrupt",
        "mode":"OnceInitialDATA011F.2","source00f0":"WordRawSoftwareSnapshotUpstreamProducerNotRun",
        "generation":"writerPC,eventIndex,writeOrder,value","programDataReads":[],
        "state":"OneCpuRamPerSequence","irqDelivery":"NotInjected","elapsedTime":"None",
        "producerTo2330SchedulerSeam":"NotEstablished","physicalRpmAvailable":false}),
    ]
}
pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .data0136_technical_producer
        .as_ref()
        .ok_or("M2v stimulus required")?;
    let divided = s.initial_state.data011f & 4 != 0;
    if s.format_version != 1
        || s.observations.is_empty()
        || s.observations.len() > 256
        || s.trace_observation_indexes.len() > 8
        || s.trace_observation_indexes
            .iter()
            .any(|i| *i as usize >= s.observations.len())
        || s.trace_observation_indexes
            .iter()
            .collect::<std::collections::HashSet<_>>()
            .len()
            != s.trace_observation_indexes.len()
        || s.observations
            .iter()
            .enumerate()
            .any(|(i, o)| o.index as usize != i || o.slot > 5 || o.source00f0.is_some() != divided)
        || r.images.len() != 1
        || r.images[0].id != "baseline"
        || r.images[0].rom.len() != 32768
        || r.scratch_patterns != [0, 85, 170]
        || !r.allow_assumptions.is_empty()
        || r.synthetic.is_some()
        || r.producer_cases.is_some()
    {
        return Err("invalid closed M2v technical producer contract".into());
    }
    Ok(())
}
pub(crate) fn contract() -> SliceContract {
    SliceContract {
        entry_pc: 0x56BE,
        exit_pcs: vec![0x5719],
        code_ranges: vec![[0x56BE, 0x5719]],
        psw: 0x1102,
        lrb: 0x21,
        usp: 0x280,
        instruction_budget: 128,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: Some([0, 0]),
    }
}
pub fn ram_addresses() -> Vec<u16> {
    [
        (0x90, 0x98),
        (0xA2, 0xA3),
        (0xAE, 0xAF),
        (0xB6, 0xB7),
        (0xEE, 0xF2),
        (0x108, 0x110),
        (0x11F, 0x120),
        (0x128, 0x129),
        (0x136, 0x138),
        (0x360, 0x36C),
    ]
    .into_iter()
    .flat_map(|(a, b)| a..b)
    .collect()
}
pub(crate) fn ram(cpu: &Cpu, bus: &mut Bus) -> Vec<u8> {
    ram_addresses()
        .into_iter()
        .map(|a| read_data_u8(cpu, bus, a))
        .collect()
}
pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r.data0136_technical_producer.as_ref().expect("validated");
    response.entry_contracts = entry_contracts();
    let mut sequences = vec![];
    for &pattern in &r.scratch_patterns {
        let (mut cpu, mut bus) = seed_machine(&r.images[0].rom, &contract(), pattern);
        cpu.ssp = 0x7FE; // Explicit unused technical SSP, NOT a recovered caller frame.
        initialize_data(&mut cpu, &mut bus, &s.initial_state);
        let mut terminal = false;
        let mut completed = 0;
        let mut checkpoints = vec![];
        for o in &s.observations {
            let before = ram(&cpu, &mut bus);
            if terminal {
                checkpoints.push(Checkpoint {
                    index: o.index,
                    result: None,
                    source_applications: vec![],
                    entry: None,
                    exit: None,
                    ram_before: before.clone(),
                    ram_after: before,
                    events: vec![],
                    accesses: vec![],
                    writes: vec![],
                    peripheral_accesses: vec![],
                });
                continue;
            }
            let row = execute_in_state(&mut cpu, &mut bus, o);
            if row.result.as_ref().expect("executed").status == 0 {
                completed += 1;
            } else {
                terminal = true;
            }
            checkpoints.push(row);
        }
        sequences.push(Sequence {
            image_index: 0,
            scratch_pattern: pattern,
            completed_observations: completed,
            checkpoints,
        });
    }
    response.data0136_sequences = Some(sequences);
    Ok(response)
}
pub(crate) fn configure(bus: &mut Bus) {
    bus.configure_scoped_access(
        vec![
            [0, 8],
            [0x19, 0x1A],
            [0x3A, 0x3C],
            [0x42, 0x43],
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
        128,
    );
}
/// Once-only RAM initialization; never called by execute_in_state.
pub(crate) fn initialize_data(cpu: &mut Cpu, bus: &mut Bus, init: &InitialState) {
    configure(bus);
    write_data_u16(cpu, bus, 0xEE, init.previous00ee);
    write_data_u16(cpu, bus, 0x136, init.history0136);
    for (i, v) in init.samples.iter().enumerate() {
        write_data_u16(cpu, bus, 0x360 + i as u16 * 2, *v);
    }
    for (a, v) in [
        (0xAE, init.counter00ae),
        (0xB6, init.data00b6),
        (0x11F, init.data011f),
        (0x128, init.data0128),
    ] {
        write_data_u8(cpu, bus, a, v);
    }
}
/// Applies ONLY the historical technical ABI and disclosed observation sources.
pub(crate) fn execute_in_state(cpu: &mut Cpu, bus: &mut Bus, o: &Observation) -> Checkpoint {
    configure(bus);
    let before = ram(cpu, bus);
    crate::acquisition::enter(cpu, bus, &contract());
    let mut applications = vec![[0xA2, 8, u32::from(o.slot)]];
    write_data_u8(cpu, bus, 0xA2, o.slot);
    if let Some(source) = o.source00f0 {
        applications.push([0xF0, 16, u32::from(source)]);
        write_data_u16(cpu, bus, 0xF0, source);
    }
    let entry = crate::vtec_fuel::boundary(cpu, bus);
    bus.observe_capture(Some(CaptureObservation {
        tmr2: o.tmr2,
        irqh: o.irqh,
        tcon2: o.tcon2,
    }));
    bus.begin_write_journal();
    bus.begin_native_accesses();
    bus.start_decision_observer();
    let result =
        execute_in_state_observed(cpu, bus, &contract(), &[], true, Some(form_admission), true);
    let events = bus.finish_decision_observer();
    let accesses = bus.end_native_accesses();
    let writes = bus.end_write_journal();
    let peripheral_accesses = bus.peripheral_accesses();
    bus.observe_capture(None);
    let exit = crate::vtec_fuel::boundary(cpu, bus);
    let after = ram(cpu, bus);
    Checkpoint {
        index: o.index,
        result: Some(result),
        source_applications: applications,
        entry: Some(entry),
        exit: Some(exit),
        ram_before: before,
        ram_after: after,
        events,
        accesses,
        writes,
        peripheral_accesses,
    }
}
