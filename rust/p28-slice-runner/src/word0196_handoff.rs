//! M2y Part A. Retained machine and PC-only technical schedule; no timer capability.
use crate::{
    adaptive::Stage,
    bus::Bus,
    cpu::Cpu,
    decoder::Decoded,
    exec::{read_data_u8, write_data_u8},
    full_decoder::FULL_OPCODES,
    instruction_forms::FormAdmission,
    post_store::Suffix,
    protocol::{Request, Response},
    quartet_handoff as prefix,
    runner::{execute_in_state_observed, SliceContract},
    vtec_fuel::{boundary, CpuBoundary},
};
use serde::{Deserialize, Serialize};
pub const OPERATION: &str = "word0196ConsumerHandoff";
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Initial {
    pub quartet_prefix: prefix::Initial,
    #[serde(rename = "bit0128_2")]
    pub bit0128_2: bool,
    pub byte0117: u8,
}
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Stimulus {
    pub format_version: u32,
    pub initial_state: Initial,
    pub calls: Vec<prefix::Call>,
    pub trace_event_indexes: Vec<u32>,
}
#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct State {
    pub byte0128: u8,
    pub byte0117: u8,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Event {
    pub index: u32,
    pub machine_id: u32,
    pub prefix: prefix::Event,
    pub consumer: Option<Suffix>,
    pub disposition: &'static str,
    pub provenance: &'static str,
    pub producer_generation0196: Option<prefix::Generation>,
    pub reader_generation0196: Option<prefix::Generation>,
    pub abi_writes: Vec<[u32; 3]>,
    pub after: CpuBoundary,
    pub state_before: State,
    pub state_after: State,
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
        entry_pc: 0x54F5,
        exit_pcs: vec![0x5503, 0x5533, 0x556F],
        code_ranges: vec![[0x54F5, 0x5503]],
        psw: 0,
        lrb: 0,
        usp: 0,
        instruction_budget: 6,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    }
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![
        serde_json::json!({"id":OPERATION,"formatVersion":1,"prefixContract":prefix::entry_contracts()[0],
        "entryPc":0x54F5,"stopBefore":0x5503,"alternateStopBefore":[0x5533,0x556F],"codeRanges":[[0x54F5,0x5503]],"instructionBudget":6,
        "entryClassification":"TechnicalSeeded0196ConsumerEntry","abiWrites":"PC only;A/PSW/LRB/SCB/pointers/USP/SSP/locals retained",
        "callFrame":"TechnicalEntryDoesNotClaimCallFrame","sourcePolicy":"OnceInitialSoftwareSnapshot;NoEventOrBoundaryReseed",
        "sourceMasks":[[0x128,4]],"sourceBytes":[0x117],"reader":[0x54FA,0x196,16],"nativeSoftwareStores":[[0x54F8,0x108,8],[0x54FC,0x10A,16]],
        "generation":"writerPC,eventIndex,zeroBasedAllNativeWriteOrder,value;NoOverlap0196/0197",
        "machine":"OneCpuOneBusPerSequence;NoSerializationHandoff","interStageScheduling":"ExplicitHarnessSchedule","recovered0196Scheduler":"NotEstablished",
        "firstHardwareAccess":[0x5503,0x30,16,0],"laterTimerWrite":[0x5508,0x32,16,1],"timerContinuation":"NotRun;PrimaryPeripheralEvidenceMissing;WriteNotReadOnly",
        "cmp5578":"StaticOnly;0196WordVsImmediate00C0;NotRAM00C0","p2":"NotRun","otherConsumer157E":"StaticOther0196Consumer/NotRun",
        "partial":"Terminal;UnadmittedPureAlternateNotHardwareBoundary;LaterNotRun","irqDelivery":"NotInjected","elapsedTime":"None","skippedCode":"NotExecuted",
        "physical0196Role":"Unknown","physicalRpmAvailable":false,"canaryAddresses":[0x300,0x350,0x3E0]}),
    ]
}
pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .word0196_consumer_handoff
        .as_ref()
        .ok_or("M2y stimulus required")?;
    prefix::validate_parts(
        r,
        s.format_version,
        &s.initial_state.quartet_prefix,
        &s.calls,
        &s.trace_event_indexes,
    )
}
fn configure(bus: &mut Bus) {
    bus.configure_scoped_access(
        vec![
            [0, 8],
            [0x90, 0x98],
            [0x108, 0x110],
            [0x117, 0x118],
            [0x128, 0x129],
            [0x196, 0x198],
        ],
        4096,
    );
    bus.set_program_data_ranges(vec![]);
}
fn state(cpu: &Cpu, bus: &mut Bus) -> State {
    configure(bus);
    State {
        byte0128: read_data_u8(cpu, bus, 0x128),
        byte0117: read_data_u8(cpu, bus, 0x117),
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
        ("JBR off N8.2, rel8", 'U', ["DA", "N8", "rel8"])
        | ("MOVB r0, #N8", 'U', ["98", "N8"])
        | ("L A, off N8", 'S', ["E4", "N8"])
        | ("ST A, er1", '1', ["89"])
        | ("CMPB off N'8, #N8", 'U', ["C4", "N'8", "C0", "N8"])
        | ("JNE rel8", 'U', ["CE", "rel8"]) => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}
pub(crate) fn execute_consumer(cpu: &mut Cpu, bus: &mut Bus) -> Suffix {
    configure(bus);
    bus.clear_program_reads();
    let entry = boundary(cpu, bus);
    bus.begin_native_accesses();
    bus.begin_write_journal();
    bus.start_decision_observer();
    let mut result =
        execute_in_state_observed(cpu, bus, &contract(), &[], true, Some(admission), true);
    if result.status == 0 && result.stop_pc != 0x5503 {
        result.status = 1;
        result.error = Some("unadmitted pure alternate continuation; not a timer boundary".into());
    }
    let accesses = bus.end_native_accesses();
    let stage = Stage {
        result,
        writes: bus.end_write_journal(),
        events: bus.finish_decision_observer(),
        ssp_after: cpu.ssp,
    };
    Suffix {
        entry,
        exit: boundary(cpu, bus),
        stage,
        accesses,
    }
}
/// Generation identity comes from a current native writer, not equality alone.
pub(crate) fn reader_generation(
    journal: &[[u32; 6]],
    g: &prefix::Generation,
    event: u32,
    address: u32,
    reader: u32,
) -> Option<prefix::Generation> {
    if g.event_index != event {
        return None;
    }
    let w = journal
        .iter()
        .position(|a| *a == [1, g.writer_pc, address, 16, 1, g.value])?;
    if journal[..w]
        .iter()
        .filter(|a| a[0] == 1 && a[4] == 1)
        .count()
        != g.write_order as usize
    {
        return None;
    }
    let r = journal
        .iter()
        .position(|a| *a == [1, reader, address, 16, 0, g.value])?;
    if r <= w
        || journal[w + 1..r]
            .iter()
            .any(|a| a[4] == 1 && a[2] < address + 2 && a[2] + a[3] / 8 > address)
    {
        return None;
    }
    Some(g.clone())
}
pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r.word0196_consumer_handoff.as_ref().expect("validated");
    let mut sequences = vec![];
    for &pattern in &r.scratch_patterns {
        let (mut cpu, mut bus) =
            prefix::initialize(&r.images[0].rom, pattern, &s.initial_state.quartet_prefix);
        bus.configure_scoped_access(vec![[0, 4096]], 4096);
        let prior = read_data_u8(&cpu, &mut bus, 0x128);
        write_data_u8(
            &mut cpu,
            &mut bus,
            0x128,
            (prior & !4) | if s.initial_state.bit0128_2 { 4 } else { 0 },
        );
        write_data_u8(&mut cpu, &mut bus, 0x117, s.initial_state.byte0117);
        let identity = (&cpu as *const Cpu, &bus as *const Bus);
        let mut terminal = false;
        let mut checkpoints = vec![];
        for (i, call) in s.calls.iter().enumerate() {
            let before = state(&cpu, &mut bus);
            let mut p = prefix::checkpoint(&cpu, &mut bus, call, i as u32, pattern);
            let mut consumer = None;
            let mut abi = vec![];
            let mut disposition = "NotRun";
            let mut provenance = "NoFresh0196";
            let mut generation = None;
            if !terminal {
                bus.begin_continuity();
                prefix::execute_checkpoint(&mut cpu, &mut bus, call, &mut p);
                if let Some(g) = &p.result_generation {
                    provenance = if p.selected_generation.is_some() {
                        "QuartetDerived0196"
                    } else {
                        "ConsumerGateBypass0196"
                    };
                    abi.push([0, cpu.pc as u32, 0x54F5]);
                    cpu.pc = 0x54F5;
                    let c = execute_consumer(&mut cpu, &mut bus);
                    generation =
                        reader_generation(&bus.continuity_snapshot(), g, i as u32, 0x196, 0x54FA);
                    disposition = if c.stage.result.status == 0 && generation.is_some() {
                        if provenance == "QuartetDerived0196" {
                            "QuartetDerived0196ConsumerStrict"
                        } else {
                            "GateBypass0196ConsumerStrict"
                        }
                    } else {
                        match c.stage.result.status {
                            3 => "BudgetExceeded",
                            2 => "ExecutionError",
                            _ => "0196ConsumerPartial",
                        }
                    };
                    consumer = Some(c);
                } else {
                    disposition = "NoFresh0196";
                }
                terminal = !matches!(
                    disposition,
                    "QuartetDerived0196ConsumerStrict" | "GateBypass0196ConsumerStrict"
                );
            }
            let journal = if disposition == "NotRun" {
                vec![]
            } else {
                bus.end_continuity()
            };
            // Read-only diagnostics must observe the actual incoming banks even
            // when the prefix stopped before entering M2x's local/SCB bank.
            bus.configure_scoped_access(vec![[0, 4096]], 4096);
            let after = boundary(&cpu, &mut bus);
            let state_after = state(&cpu, &mut bus);
            bus.configure_scoped_access(vec![[0x300, 0x301], [0x350, 0x351], [0x3E0, 0x3E1]], 4096);
            let canaries = [0x300, 0x350, 0x3E0].map(|a| read_data_u8(&cpu, &mut bus, a));
            assert_eq!(identity, (&cpu as *const Cpu, &bus as *const Bus));
            checkpoints.push(Event {
                index: i as u32,
                machine_id: 1,
                producer_generation0196: p.result_generation.clone(),
                reader_generation0196: generation,
                prefix: p,
                consumer,
                disposition,
                provenance,
                abi_writes: abi,
                after,
                state_before: before,
                state_after,
                continuity_journal: journal,
                canaries,
            });
        }
        sequences.push(Sequence {
            scratch_pattern: pattern,
            machine_instances: 1,
            checkpoints,
        });
    }
    response.entry_contracts = entry_contracts();
    response.word0196_handoff_sequences = Some(sequences);
    Ok(response)
}
