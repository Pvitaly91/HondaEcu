//! M2x: native quartet generation and one bounded consumer on the same machine.
use crate::{
    adaptive::Stage,
    bus::Bus,
    cpu::Cpu,
    decoder::Decoded,
    exec::{read_data_u16, read_data_u8, write_data_u8},
    full_decoder::FULL_OPCODES,
    instruction_forms::FormAdmission,
    post_selection_critical as prefix, post_store,
    protocol::{Request, Response},
    runner::{execute_in_state_observed, SliceContract},
    vtec_fuel::{boundary, CpuBoundary},
};
use serde::{Deserialize, Serialize};
pub const OPERATION: &str = "quartetConsumerHandoff";
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Initial {
    pub fuel_prefix: post_store::Initial,
    pub bit012a1: bool,
}
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Call {
    pub prefix: post_store::Call,
    pub selector013c: u8,
}
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Stimulus {
    pub format_version: u32,
    pub initial_state: Initial,
    pub calls: Vec<Call>,
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
#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct State {
    pub selector013c: u8,
    pub byte012a: u8,
    pub byte0124: u8,
    pub byte0125: u8,
    pub word0196: u16,
    pub companions03be: [u16; 4],
    pub byte019b: u8,
    pub byte019d: u8,
    pub byte019f: u8,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Event {
    pub index: u32,
    pub machine_id: u32,
    pub fuel_prefix: prefix::Checkpoint,
    pub consumer: Option<post_store::Suffix>,
    pub disposition: &'static str,
    pub before: CpuBoundary,
    pub after: CpuBoundary,
    pub state_before: State,
    pub state_after: State,
    pub abi_writes: Vec<[u32; 3]>,
    pub source_writes: Vec<[u32; 3]>,
    pub quartet_generations: Vec<Generation>,
    pub selected_slot: Option<u32>,
    pub selected_address: Option<u32>,
    pub selected_generation: Option<Generation>,
    pub result_generation: Option<Generation>,
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
pub fn contract() -> SliceContract {
    SliceContract {
        entry_pc: 0x584,
        exit_pcs: vec![0x5ED, 0x5AF],
        code_ranges: vec![[0x584, 0x5A0], [0x5D5, 0x5ED], [0x7DEF, 0x7DF4]],
        psw: 0x1DCA,
        lrb: 0x21,
        usp: 0,
        instruction_budget: 40,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    }
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![
        serde_json::json!({"id":OPERATION,"formatVersion":1,"prefixContract":prefix::entry_contracts()[0],
    "entryPc":0x584,"stopBefore":0x5ED,"alternateStopBefore":0x5AF,"codeRanges":[[0x584,0x5A0],[0x5D5,0x5ED],[0x7DEF,0x7DF4]],"instructionBudget":40,
    "entryClassification":"TechnicalSeededQuartetConsumerEntry","abiWrites":"PC,PSW1DCA,LRB0021 only;USP/SSP/A/pointers/locals retained;no IRQ frame",
    "selectorSource":"RawSoftwareSnapshot0..3;OnceBeforeExecutedConsumer;SelectorProducerNotRun","companionSource":"NativeResetFourWords03BE/03C0/03C2/03C4;X2NativeZero",
    "reader":[0x5DF,16],"resultWriter":[0x5EB,0x196,16],"generation":"writerPC,eventIndex,zeroBasedAllNativeWriteOrder,value",
    "machine":"OneCpuOneBusPerSequence;NoSerializationHandoff","interStageScheduling":"ExplicitHarnessSchedule","recoveredQuartetScheduler":"NotEstablished",
    "skippedCode":"NotExecuted","irqDelivery":"NotInjected","pendingInterrupt":"NotModeled","elapsedTime":"None","physicalChannelRole":"Unknown",
    "canaryAddresses":[0x300,0x350,0x3E0],"initial012A":"MaskedBit1Once;NeighborsRetained;UpstreamNotRun","initial0196":"DiagnosticScratchOnly",
    "partial":"Terminal;RetainNativeStores;LaterNotRun","otherConsumer1550":"StaticOtherConsumer/NotRun","physicalRpmAvailable":false}),
    ]
}
pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .quartet_consumer_handoff
        .as_ref()
        .ok_or("M2x stimulus required")?;
    if s.calls.iter().any(|c| c.selector013c > 3) {
        return Err("unsafe selector013c outside0..3".into());
    }
    // Serialize only the already closed source structures, never execution results.
    let calls = s
        .calls
        .iter()
        .map(|c| post_store::Call {
            adaptive: c.prefix.adaptive.clone(),
            disable125: c.prefix.disable125,
            disable12e: c.prefix.disable12e,
        })
        .collect::<Vec<_>>();
    post_store::validate_parts(
        r,
        s.format_version,
        &s.initial_state.fuel_prefix,
        &calls,
        &s.trace_event_indexes,
    )
}
fn configure(bus: &mut Bus) {
    bus.configure_scoped_access(
        vec![
            [0, 8],
            [0x88, 0x98],
            [0x100, 0x110],
            [0x124, 0x126],
            [0x12A, 0x12B],
            [0x13C, 0x13D],
            [0x196, 0x198],
            [0x19B, 0x19C],
            [0x19D, 0x19E],
            [0x19F, 0x1A0],
            [0x3B6, 0x3C6],
        ],
        4096,
    );
    bus.set_program_data_ranges(vec![]);
}
fn state(cpu: &Cpu, bus: &mut Bus) -> State {
    configure(bus);
    State {
        selector013c: read_data_u8(cpu, bus, 0x13C),
        byte012a: read_data_u8(cpu, bus, 0x12A),
        byte0124: read_data_u8(cpu, bus, 0x124),
        byte0125: read_data_u8(cpu, bus, 0x125),
        word0196: read_data_u16(cpu, bus, 0x196),
        companions03be: [0x3BE, 0x3C0, 0x3C2, 0x3C4].map(|a| read_data_u16(cpu, bus, a)),
        byte019b: read_data_u8(cpu, bus, 0x19B),
        byte019d: read_data_u8(cpu, bus, 0x19D),
        byte019f: read_data_u8(cpu, bus, 0x19F),
    }
}
pub fn admission(d: &Decoded) -> FormAdmission {
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    match (p.mnemonic, p.dd_mode, p.bytes_pat) {
        ("LB A, off N8", 'R', ["F4", "N8"])
        | ("SLLB A", '0', ["53"])
        | ("EXTND", 'S', ["F8"])
        | ("MOV X1, A", 'U', ["50"])
        | ("MOV X2, A", 'U', ["51"])
        | ("CLR A", 'S', ["F9"])
        | ("CLRB A", 'R', ["FA"])
        | ("ST A, N16[X2]", '1', ["D1", "NL", "NH"])
        | ("STB A, off N8", '0', ["D4", "N8"])
        | ("J addr16", 'U', ["03", "addrl", "addrh"])
        | ("RB off N8.0", 'U', ["C4", "N8", "08"])
        | ("JBS off N8.4, rel8", 'U', ["EC", "N8", "rel8"])
        | ("JBS off N8.1, rel8", 'U', ["E9", "N8", "rel8"])
        | ("L A, N16[X1]", 'S', ["E0", "NL", "NH"])
        | ("ADD A, N16[X1]", '1', ["B0", "NL", "NH", "82"])
        | ("JGE rel8", 'U', ["CD", "rel8"])
        | ("L A, #N16", 'S', ["67", "NL", "NH"])
        | ("ST A, off N8", '1', ["D4", "N8"]) => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}
pub(crate) fn execute_consumer(cpu: &mut Cpu, bus: &mut Bus) -> post_store::Suffix {
    configure(bus);
    bus.clear_program_reads();
    let entry = boundary(cpu, bus);
    bus.begin_native_accesses();
    bus.begin_write_journal();
    bus.start_decision_observer();
    let mut result =
        execute_in_state_observed(cpu, bus, &contract(), &[], true, Some(admission), true);
    if result.status == 0 && result.stop_pc == 0x5AF {
        result.status = 1;
        result.error = Some("alternate companion path not admitted; JGT remains unresolved".into());
    }
    let accesses = bus.end_native_accesses();
    let stage = Stage {
        result,
        writes: bus.end_write_journal(),
        events: bus.finish_decision_observer(),
        ssp_after: cpu.ssp,
    };
    post_store::Suffix {
        entry,
        exit: boundary(cpu, bus),
        stage,
        accesses,
    }
}
pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r.quartet_consumer_handoff.as_ref().expect("validated");
    response.entry_contracts = entry_contracts();
    let mut sequences = vec![];
    for &pattern in &r.scratch_patterns {
        let (mut cpu, mut bus) =
            post_store::initialize(&r.images[0].rom, pattern, &s.initial_state.fuel_prefix);
        bus.configure_scoped_access(vec![[0, 4096]], 4096);
        let prior = read_data_u8(&cpu, &mut bus, 0x12A);
        write_data_u8(
            &mut cpu,
            &mut bus,
            0x12A,
            (prior & !2) | if s.initial_state.bit012a1 { 2 } else { 0 },
        );
        let identity = (&cpu as *const Cpu, &bus as *const Bus);
        let mut terminal = false;
        let mut checkpoints = vec![];
        for (index, call) in s.calls.iter().enumerate() {
            bus.configure_scoped_access(vec![[0, 4096]], 4096);
            let before = boundary(&cpu, &mut bus);
            let state_before = state(&cpu, &mut bus);
            let mut event = Event {
                index: index as u32,
                machine_id: 1,
                fuel_prefix: prefix::checkpoint(&cpu, &mut bus, &call.prefix),
                consumer: None,
                disposition: "NotRun",
                after: before.clone(),
                before,
                state_after: state_before.clone(),
                state_before,
                abi_writes: vec![],
                source_writes: vec![],
                quartet_generations: vec![],
                selected_slot: None,
                selected_address: None,
                selected_generation: None,
                result_generation: None,
                continuity_journal: vec![],
                canaries: [pattern; 3],
            };
            if !terminal {
                bus.begin_continuity();
                prefix::execute_checkpoint(
                    &mut cpu,
                    &mut bus,
                    &call.prefix,
                    &mut event.fuel_prefix,
                );
                if event.fuel_prefix.status != 0 {
                    event.disposition = "ConsumerNotRun";
                    terminal = true;
                } else {
                    configure(&mut bus);
                    write_data_u8(&mut cpu, &mut bus, 0x13C, call.selector013c);
                    event
                        .source_writes
                        .push([0x13C, 8, call.selector013c as u32]);
                    event.abi_writes = vec![
                        [0, cpu.pc as u32, 0x584],
                        [1, cpu.psw_u16() as u32, 0x1DCA],
                        [2, cpu.lrb as u32, 0x21],
                    ];
                    cpu.pc = 0x584;
                    cpu.set_psw_u16(0x1DCA);
                    cpu.lrb = 0x21;
                    let consumer = execute_consumer(&mut cpu, &mut bus);
                    if consumer.stage.result.status != 0 {
                        event.disposition = match consumer.stage.result.status {
                            3 => "BudgetExceeded",
                            2 => "ExecutionError",
                            _ => "ConsumerPartial",
                        };
                        terminal = true;
                    } else if consumer.accesses.iter().any(|a| {
                        a[0] == 0x5DF
                            && a[1] == 0x3B6 + 2 * call.selector013c as u32
                            && a[2] == 16
                            && a[3] == 0
                    }) {
                        event.disposition = "QuartetHandoffStrict";
                        event.selected_slot = Some(call.selector013c as u32);
                        event.selected_address = Some(0x3B6 + 2 * call.selector013c as u32);
                    } else {
                        event.disposition = "ConsumerGateBypassNotHandoff";
                    }
                    event.consumer = Some(consumer);
                }
                event.continuity_journal = bus.end_continuity();
                let mut order = 0;
                for a in &event.continuity_journal {
                    if a[0] == 1 && a[4] == 1 {
                        let g = Generation {
                            writer_pc: a[1],
                            event_index: index as u32,
                            write_order: order,
                            value: a[5],
                        };
                        if matches!(
                            (a[1], a[2], a[3]),
                            (0x22A5, 0x3B6, 16)
                                | (0x22A8, 0x3B8, 16)
                                | (0x22AB, 0x3BA, 16)
                                | (0x22AE, 0x3BC, 16)
                        ) {
                            event.quartet_generations.push(g.clone());
                        }
                        if (a[1], a[2], a[3]) == (0x5EB, 0x196, 16) {
                            event.result_generation = Some(g);
                        }
                        order += 1;
                    }
                }
                if let Some(slot) = event.selected_slot {
                    event.selected_generation =
                        event.quartet_generations.get(slot as usize).cloned();
                }
            }
            assert_eq!(identity, (&cpu as *const Cpu, &bus as *const Bus));
            bus.configure_scoped_access(vec![[0, 4096]], 4096);
            event.after = boundary(&cpu, &mut bus);
            event.state_after = state(&cpu, &mut bus);
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
    response.quartet_handoff_sequences = Some(sequences);
    Ok(response)
}
