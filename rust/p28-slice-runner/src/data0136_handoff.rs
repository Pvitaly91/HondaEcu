//! M2w: one machine, explicit harness schedule. Never a recovered ECU scheduler.
use crate::{
    bus::Bus,
    common_result_consumer as common,
    cpu::Cpu,
    data0136_technical as producer,
    exec::{read_data_u16, read_data_u8, write_data_u16, write_data_u8},
    post_selection_critical as prefix, post_store,
    protocol::{Request, Response},
    vtec_fuel::boundary,
};
use serde::{Deserialize, Serialize};
pub const OPERATION: &str = "data0136DivisionHandoff";
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct ProducerInitial {
    pub previous00ee: u16,
    pub counter00ae: u8,
    pub data00b6: u8,
    pub data0128: u8,
    pub samples: [u16; 6],
}
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Sources {
    pub word011a_mask1034: u16,
    #[serde(rename = "bit0120_0")]
    pub bit0120_0: bool,
    pub byte00be: u8,
    #[serde(rename = "bit00b7_0")]
    pub bit00b7_0: bool,
    pub history013b: u8,
    pub history013d: u8,
}
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Initial {
    pub producer: ProducerInitial,
    pub data011f: u8,
    pub fuel_prefix: post_store::Initial,
    pub software_sources: Sources,
}
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Stimulus {
    pub format_version: u32,
    pub unified_initial_state: Initial,
    pub producer_observations: Vec<producer::Observation>,
    pub fuel_calls: Vec<post_store::Call>,
    pub trace_event_indexes: Vec<u32>,
}
#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct Generation {
    pub writer_pc: u32,
    pub event_index: u32,
    pub write_order: u32,
    pub value: u32,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Event {
    pub index: u32,
    pub machine_id: u32,
    pub producer: Option<producer::Checkpoint>,
    pub fuel_prefix: Option<prefix::Checkpoint>,
    pub calculation: Option<post_store::Suffix>,
    pub producer_generation: Option<Generation>,
    pub consumer_generation: Option<Generation>,
    pub disposition: &'static str,
    pub before: crate::vtec_fuel::CpuBoundary,
    pub after: crate::vtec_fuel::CpuBoundary,
    pub state_before: common::State,
    pub state_at_fuel_entry: Option<common::State>,
    pub state_at_calculation_entry: Option<common::State>,
    pub state_after: common::State,
    pub producer_ram_after_schedule: Vec<u8>,
    pub continuity_journal: Vec<[u32; 6]>,
    pub canaries: [u8; 3],
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
    "producerContract":producer::entry_contracts()[0],"fuelPrefixContract":prefix::entry_contracts()[0],"calculationContract":common::entry_contracts()[0],
    "initialization":"OnceBeforeSequence;0136CanaryFromScratch;OneAuthoritative011FByte",
    "state":"OneCpuBusPerSequence;NoSerializationHandoff","pairing":"ProducerObservation[N]->FreshNativeGeneration->FuelCall[N]",
    "interStageScheduling":"ExplicitHarnessSchedule","skippedCode":"NotExecuted","mainLoopRecovery":"NotEstablished",
    "producerTo2330SchedulerSeam":"HarnessScheduled / NotRecovered","recoveredEcuScheduler":"NotEstablished",
    "positiveStopBefore":0x233A,"zeroStopBefore":0x2333,"generation":"writerPC,eventIndex,writeOrder,value",
    "continuityJournal":"native,pc,address,width,write,value;hostPc65536;CPU_ABI_fields_in_nested_boundaries",
    "noFreshGeneration":"DownstreamNotRun;ContinueIfProducerComplete","partial":"Terminal;RetainCompletedStores",
    "handoffBoundary":"MayContinueNextEvent;NotStrictCalculationCompletion","canaryAddresses":[0x300,0x350,0x3E0],
    "irqDelivery":"NotInjected","elapsedTime":"None","quartetConsumer":"NotRun","physicalRpmAvailable":false})]
}
pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .data0136_division_handoff
        .as_ref()
        .ok_or("M2w stimulus required")?;
    let mode = s.unified_initial_state.data011f & 4 != 0;
    if s.format_version != 1
        || s.fuel_calls.is_empty()
        || s.fuel_calls.len() > 64
        || s.producer_observations.len() != s.fuel_calls.len()
        || s.unified_initial_state.software_sources.word011a_mask1034 & !0x1034 != 0
        || s.producer_observations
            .iter()
            .enumerate()
            .any(|(i, o)| o.index as usize != i || o.slot > 5 || o.source00f0.is_some() != mode)
    {
        return Err("invalid M2w pairing/ownership/producer sources".into());
    }
    post_store::validate_parts(
        r,
        s.format_version,
        &s.unified_initial_state.fuel_prefix,
        &s.fuel_calls,
        &s.trace_event_indexes,
    )
}
fn initialize(rom: &[u8], pattern: u8, s: &Initial) -> (Cpu, Bus) {
    // Exactly one machine. All initialization precedes every producer instruction.
    let (mut cpu, mut bus) = post_store::initialize(rom, pattern, &s.fuel_prefix);
    bus.configure_scoped_access(vec![[0, 4096]], 4096);
    let sources = &s.software_sources;
    let old = read_data_u16(&cpu, &mut bus, 0x11A);
    write_data_u16(
        &mut cpu,
        &mut bus,
        0x11A,
        (old & !0x1034) | sources.word011a_mask1034,
    );
    for (a, mask, on) in [(0x120, 1, sources.bit0120_0), (0xB7, 1, sources.bit00b7_0)] {
        let old = read_data_u8(&cpu, &mut bus, a);
        write_data_u8(
            &mut cpu,
            &mut bus,
            a,
            (old & !mask) | if on { mask } else { 0 },
        );
    }
    for (a, v) in [
        (0xBE, sources.byte00be),
        (0x13B, sources.history013b),
        (0x13D, sources.history013d),
    ] {
        write_data_u8(&mut cpu, &mut bus, a, v);
    }
    producer::initialize_data(
        &mut cpu,
        &mut bus,
        &producer::InitialState {
            previous00ee: s.producer.previous00ee,
            counter00ae: s.producer.counter00ae,
            data00b6: s.producer.data00b6,
            data011f: s.data011f,
            data0128: s.producer.data0128,
            history0136: u16::from(pattern) * 257,
            samples: s.producer.samples,
        },
    );
    crate::acquisition::enter(&mut cpu, &mut bus, &producer::contract());
    (cpu, bus)
}
pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r.data0136_division_handoff.as_ref().expect("validated");
    let mut sequences = vec![];
    response.entry_contracts = entry_contracts();
    for &pattern in &r.scratch_patterns {
        let (mut cpu, mut bus) = initialize(&r.images[0].rom, pattern, &s.unified_initial_state);
        // Object addresses used only internally, never serialized. Same references for every phase.
        let identity = (&cpu as *const Cpu, &bus as *const Bus);
        let mut terminal = false;
        let mut generation = None;
        let mut checkpoints = vec![];
        for (o, call) in s.producer_observations.iter().zip(&s.fuel_calls) {
            bus.configure_scoped_access(vec![[0, 4096]], 4096);
            let before = boundary(&cpu, &mut bus);
            let state_before = common::state(&cpu, &mut bus);
            let mut event = Event {
                index: o.index,
                machine_id: 1,
                producer: None,
                fuel_prefix: None,
                calculation: None,
                producer_generation: None,
                consumer_generation: None,
                disposition: "NotRun",
                after: before.clone(),
                before,
                state_before: state_before.clone(),
                state_at_fuel_entry: None,
                state_at_calculation_entry: None,
                state_after: state_before,
                producer_ram_after_schedule: vec![],
                continuity_journal: vec![],
                canaries: [pattern; 3],
            };
            if !terminal {
                bus.begin_continuity();
                let produced = producer::execute_in_state(&mut cpu, &mut bus, o);
                let result = produced.result.as_ref().expect("executed");
                let mut fresh = false;
                let mut write_order = 0;
                for a in &produced.accesses {
                    if a[3] == 1 {
                        if a[1] == 0x136 && a[2] == 16 && (a[0] == 0x56F3 || a[0] == 0x5707) {
                            generation = Some(Generation {
                                writer_pc: a[0],
                                event_index: o.index,
                                write_order,
                                value: a[4],
                            });
                            fresh = true;
                        }
                        write_order += 1;
                    }
                }
                event.producer_generation = if fresh { generation.clone() } else { None };
                if result.status != 0 {
                    event.disposition = "ProducerPartial";
                    terminal = true;
                } else if !fresh {
                    event.disposition = "NoFreshProducerGeneration";
                } else {
                    event.state_at_fuel_entry = Some(common::state(&cpu, &mut bus));
                    let mut fuel = prefix::checkpoint(&cpu, &mut bus, call);
                    prefix::execute_checkpoint(&mut cpu, &mut bus, call, &mut fuel);
                    if fuel.status != 0 {
                        event.disposition = "FuelPrefixPartial";
                        terminal = true;
                    } else {
                        event.state_at_calculation_entry = Some(common::state(&cpu, &mut bus));
                        let suffix = common::execute_suffix(&mut cpu, &mut bus);
                        let read = suffix
                            .accesses
                            .iter()
                            .find(|a| a[0] == 0x2330 && a[1] == 0x136 && a[2] == 16 && a[3] == 0);
                        if read.is_some_and(|a| Some(a[4]) == generation.as_ref().map(|g| g.value))
                        {
                            event.consumer_generation = generation.clone();
                            event.disposition = if suffix.stage.result.stop_pc == 0x233A {
                                "NativeProducerPositiveToJgtBlock"
                            } else if suffix.stage.result.stop_pc == 0x2333 {
                                "NativeProducerZeroToDivBoundary"
                            } else {
                                "ExecutionError"
                            };
                        } else {
                            event.disposition = if suffix.stage.result.status == 0 {
                                "CalculationBypassNotHandoff"
                            } else {
                                "ExecutionError"
                            };
                        }
                        terminal = !matches!(
                            event.disposition,
                            "NativeProducerPositiveToJgtBlock" | "NativeProducerZeroToDivBoundary"
                        );
                        event.calculation = Some(suffix);
                    }
                    event.fuel_prefix = Some(fuel);
                }
                event.producer = Some(produced);
                event.continuity_journal = bus.end_continuity();
                if let Some(g) = &event.producer_generation {
                    let writer = event
                        .continuity_journal
                        .iter()
                        .position(|a| {
                            a[0] == 1
                                && a[1] == g.writer_pc
                                && a[2] == 0x136
                                && a[3] == 16
                                && a[4] == 1
                                && a[5] == g.value
                        })
                        .expect("native writer recorded");
                    let read = event.continuity_journal.iter().position(|a| {
                        a[0] == 1 && a[1] == 0x2330 && a[2] == 0x136 && a[3] == 16 && a[4] == 0
                    });
                    if !retained_word(
                        &event.continuity_journal,
                        writer,
                        read.unwrap_or(event.continuity_journal.len()),
                        0x136,
                    ) {
                        event.consumer_generation = None;
                        event.disposition = "GenerationOverwritten";
                        terminal = true;
                    }
                }
            }
            assert_eq!(identity, (&cpu as *const Cpu, &bus as *const Bus));
            bus.configure_scoped_access(vec![[0, 4096]], 4096);
            event.after = boundary(&cpu, &mut bus);
            event.state_after = common::state(&cpu, &mut bus);
            producer::configure(&mut bus);
            event.producer_ram_after_schedule = producer::ram(&cpu, &mut bus);
            bus.configure_scoped_access(vec![[0x300, 0x301], [0x350, 0x351], [0x3E0, 0x3E1]], 4096);
            event.canaries = [0x300, 0x350, 0x3E0].map(|a| read_data_u8(&cpu, &mut bus, a));
            checkpoints.push(event);
        }
        sequences.push(Sequence {
            scratch_pattern: pattern,
            machine_instances: 1,
            checkpoints,
        });
    }
    response.data0136_handoff_sequences = Some(sequences);
    Ok(response)
}
// Full-width overlap proof shared with invented composition tests; value equality alone is insufficient.
pub(crate) fn retained_word(
    journal: &[[u32; 6]],
    writer: usize,
    reader: usize,
    address: u32,
) -> bool {
    writer < reader
        && reader <= journal.len()
        && !journal[writer + 1..reader]
            .iter()
            .any(|a| a[4] == 1 && a[2] < address + 2 && a[2] + a[3] / 8 > address)
}
