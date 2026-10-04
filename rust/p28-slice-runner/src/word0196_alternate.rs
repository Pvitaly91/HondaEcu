//! M2z: native software alternate; no timer/P2 capability or PC556F entry.
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
    word0196_handoff as handoff,
};
use serde::{Deserialize, Serialize};
pub const OPERATION: &str = "word0196SoftwareAlternateChain";
pub type Initial = handoff::Initial;
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
    pub byte018e: u8,
    pub byte018f: u8,
    pub byte012a: u8,
    pub byte0124: u8,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Event {
    pub index: u32,
    pub machine_id: u32,
    pub prefix: prefix::Event,
    pub consumer: Option<Suffix>,
    pub alternate: Option<Suffix>,
    pub disposition: &'static str,
    pub provenance: &'static str,
    pub producer_generation0196: Option<prefix::Generation>,
    pub reader_generation0196: Option<prefix::Generation>,
    pub compare_generation0196: Option<prefix::Generation>,
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
        entry_pc: 0x556F,
        exit_pcs: vec![0x5596, 0x55C5],
        code_ranges: vec![[0x556F, 0x5596], [0x55BF, 0x55C5]],
        psw: 0,
        lrb: 0,
        usp: 0,
        instruction_budget: 18,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    }
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({"id":OPERATION,"formatVersion":1,
    "prefixContract":handoff::entry_contracts()[0],
    "entryPc":0x54F5,"alternateEntry":"ActualJNE5501Taken;NoHostPC556F",
    "suffixRanges":[[0x556F,0x5596],[0x55BF,0x55C5]],"suffixBudget":18,
    "stopBefore":[0x5596,0x55C5],"excludedStops":[0x5503,0x5533],
    "secondReader":[0x5578,0x196,16],"rightOperand":"Immediate00C0;CodeOwnedConstant",
    "compareFlags":"CF=unsignedBorrow;ZF=equality;HC/DDretained",
    "branch":[0x557D,0x55BF,0x557F],"branchPredicate":"CF1;Producer5578;NoInterveningFlagWriter",
    "initial018E018F":"AutomaticScratchInitialHistory;NativePersistentOwnership;NoExternalSource",
    "native0117":"5582And/55C1Store;RetainedNextEvent",
    "interStageScheduleTo54F5":"ExplicitHarnessSchedule","softwareAlternate5501To556F":"NativeContinuousControlFlow",
    "machine":"OneCpuOneBusPerSequence;NoSerializationHandoff","timerContinuation":"NotRun","p2":"NotRun",
    "partial":"Terminal;RetainPriorNativeWrites;LaterNotRun;NoSourceApplication",
    "recovered0196Scheduler":"NotEstablished","irqDelivery":"NotInjected","elapsedTime":"None","physical0196Role":"Unknown"})]
}
pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .word0196_software_alternate_chain
        .as_ref()
        .ok_or("M2z stimulus required")?;
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
            [0x124, 0x125],
            [0x128, 0x129],
            [0x12A, 0x12B],
            [0x18E, 0x190],
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
        byte018e: read_data_u8(cpu, bus, 0x18E),
        byte018f: read_data_u8(cpu, bus, 0x18F),
        byte012a: read_data_u8(cpu, bus, 0x12A),
        byte0124: read_data_u8(cpu, bus, 0x124),
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
        | ("ROLB off N8", 'U', ["C4", "N8", "B7"])
        | ("LB A, r0", 'R', ["78"])
        | ("ANDB A, off N8", '0', ["D7", "N8"])
        | ("CMP off N8, #N16", 'U', ["B4", "N8", "C0", "NL", "NH"])
        | ("JLT rel8", 'U', ["CA", "rel8"])
        | ("MOVB r1, off N8", 'U', ["C4", "N8", "49"])
        | ("ANDB off N8, A", 'U', ["C4", "N8", "D1"])
        | ("JBS off N8.7, rel8", 'U', ["EF", "N8", "rel8"])
        | ("JBS off N8.5, rel8", 'U', ["ED", "N8", "rel8"])
        | ("ORB off N'8, #N8", 'U', ["C4", "N'8", "E0", "N8"])
        | ("ORB A, #N8", '0', ["E6", "N8"])
        | ("LB A, #N8", 'R', ["77", "N8"])
        | ("STB A, off N8", '0', ["D4", "N8"]) => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}
pub(crate) fn execute_alternate(cpu: &mut Cpu, bus: &mut Bus) -> Suffix {
    configure(bus);
    bus.clear_program_reads();
    let entry = boundary(cpu, bus);
    bus.begin_native_accesses();
    bus.begin_write_journal();
    bus.start_decision_observer();
    let result = execute_in_state_observed(cpu, bus, &contract(), &[], true, Some(admission), true);
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
pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r
        .word0196_software_alternate_chain
        .as_ref()
        .expect("validated");
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
            let mut alternate = None;
            let mut compare_generation = None;
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
                    let c = handoff::execute_prefix(&mut cpu, &mut bus);
                    if c.stage.result.status == 0 && cpu.pc == 0x556F {
                        let next = execute_alternate(&mut cpu, &mut bus);
                        compare_generation = handoff::reader_generation(
                            &bus.continuity_snapshot(),
                            g,
                            i as u32,
                            0x196,
                            0x5578,
                        );
                        alternate = Some(next);
                    }
                    generation = handoff::reader_generation(
                        &bus.continuity_snapshot(),
                        g,
                        i as u32,
                        0x196,
                        0x54FA,
                    );
                    disposition = if alternate
                        .as_ref()
                        .is_some_and(|a| a.stage.result.status == 0)
                        && generation.is_some()
                        && compare_generation.is_some()
                    {
                        if provenance == "QuartetDerived0196" {
                            "QuartetDerived0196AlternateStrict"
                        } else {
                            "GateBypass0196AlternateStrict"
                        }
                    } else {
                        match alternate
                            .as_ref()
                            .map_or(c.stage.result.status, |a| a.stage.result.status)
                        {
                            3 => "BudgetExceeded",
                            2 => "ExecutionError",
                            _ => "0196AlternatePartial",
                        }
                    };
                    consumer = Some(c);
                } else {
                    disposition = "NoFresh0196";
                }
                terminal = !matches!(
                    disposition,
                    "QuartetDerived0196AlternateStrict" | "GateBypass0196AlternateStrict"
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
                compare_generation0196: compare_generation,
                prefix: p,
                consumer,
                alternate,
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
    response.word0196_alternate_sequences = Some(sequences);
    Ok(response)
}
