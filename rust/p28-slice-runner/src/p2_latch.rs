//! M2aa: bounded architectural output DATA register. No pins/time/hardware.
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
    vtec_fuel::boundary,
    word0196_alternate as alternate, word0196_handoff as handoff,
};
use serde::{Deserialize, Serialize};
pub const OPERATION: &str = "p2OutputLatchHandoff";
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Stimulus {
    pub format_version: u32,
    pub initial_state: handoff::Initial,
    pub calls: Vec<prefix::Call>,
    pub trace_event_indexes: Vec<u32>,
    pub p2_output_latch: u8,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Output {
    pub suffix: Suffix,
    /// Separate peripheral journal [pc,address,width,write,value]; not RAM.
    pub peripheral_accesses: Vec<[u32; 5]>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Event {
    #[serde(flatten)]
    pub software: alternate::Event,
    pub p2: Option<Output>,
    pub p2_before: u8,
    pub p2_after: u8,
    pub incoming_p2_generation: Option<prefix::Generation>,
    pub p2_generation: Option<prefix::Generation>,
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
        "prefixContract":alternate::entry_contracts()[0],
        "p2Address":0x24,"width":8,"p2InstructionPcs":[0x5596,0x55C5],
        "stopBefore":[0x5599,0x55C8],"budget":1,
        "mode":"ReviewedStartupPrecondition;P2IO=FF;P2SFImplementedBits=0",
        "initialLatch":"RawArchitecturalP2LatchSnapshot;StartupProducerNotRun;OnceOnly",
        "journal":"SeparatePeripheral;PC,address,width,write,value;ReadBeforeWrite",
        "generation":"writerPC,eventIndex,zeroBasedAllNativeEventWriteOrder,value;SameValueFresh",
        "electricalPins":"NotModeled","physicalOutput":"NotRun","timerContinuation":"NotRun"})]
}
pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .p2_output_latch_handoff
        .as_ref()
        .ok_or("M2aa stimulus required")?;
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
        ("ANDB N8, A", 'U', ["C5", "N8", "D1"]) | ("ORB N8, A", 'U', ["C5", "N8", "E1"]) => {
            FormAdmission::Allowed
        }
        _ => FormAdmission::Unsupported,
    }
}
pub(crate) fn execute_p2(cpu: &mut Cpu, bus: &mut Bus) -> Output {
    bus.configure_scoped_access(
        vec![[0, 8], [0x24, 0x25], [0x90, 0x98], [0x108, 0x110]],
        4096,
    );
    bus.set_program_data_ranges(vec![]);
    bus.clear_program_reads();
    let entry = boundary(cpu, bus);
    bus.begin_native_accesses();
    bus.begin_write_journal();
    bus.start_decision_observer();
    bus.begin_p2_accesses();
    bus.set_p2_access(true);
    let contract = SliceContract {
        entry_pc: cpu.pc,
        exit_pcs: vec![0x5599, 0x55C8],
        code_ranges: vec![[0x5596, 0x5599], [0x55C5, 0x55C8]],
        psw: 0,
        lrb: 0,
        usp: 0,
        instruction_budget: 1,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    };
    let result = execute_in_state_observed(cpu, bus, &contract, &[], true, Some(admission), true);
    bus.set_p2_access(false);
    let peripheral_accesses = bus.p2_accesses();
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
    }
}
pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r.p2_output_latch_handoff.as_ref().expect("validated");
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
        bus.initialize_p2_output_latch(s.p2_output_latch)?;
        let mut retained_generation = None;
        let mut terminal = false;
        let mut checkpoints = vec![];
        for (i, call) in s.calls.iter().enumerate() {
            let before = alternate::state(&cpu, &mut bus);
            let mut p = prefix::checkpoint(&cpu, &mut bus, call, i as u32, pattern);
            let p2_before = bus.p2_output_latch().expect("initial snapshot");
            let incoming_p2_generation = retained_generation.clone();
            let mut p2 = None;
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
                        let next = alternate::execute_alternate(&mut cpu, &mut bus);
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
                    if disposition.ends_with("AlternateStrict") {
                        let output = execute_p2(&mut cpu, &mut bus);
                        disposition = if output.suffix.stage.result.status == 0 {
                            let order = bus
                                .continuity_snapshot()
                                .iter()
                                .filter(|a| a[0] == 1 && a[4] == 1)
                                .count() as u32;
                            retained_generation = Some(prefix::Generation {
                                writer_pc: output.suffix.entry.pc as u32,
                                event_index: i as u32,
                                write_order: order,
                                value: bus.p2_output_latch().unwrap() as u32,
                            });
                            if provenance == "QuartetDerived0196" {
                                "QuartetDerivedP2LatchStrict"
                            } else {
                                "GateBypassP2LatchControl"
                            }
                        } else {
                            match output.suffix.stage.result.status {
                                3 => "BudgetExceeded",
                                2 => "ExecutionError",
                                _ => "P2InstructionPartial",
                            }
                        };
                        p2 = Some(output);
                    } else if disposition == "0196AlternatePartial" {
                        disposition = "UpstreamPartial";
                    }
                    consumer = Some(c);
                } else {
                    disposition = "NoFresh0196";
                }
                terminal = !matches!(
                    disposition,
                    "QuartetDerivedP2LatchStrict" | "GateBypassP2LatchControl"
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
            let state_after = alternate::state(&cpu, &mut bus);
            bus.configure_scoped_access(vec![[0x300, 0x301], [0x350, 0x351], [0x3E0, 0x3E1]], 4096);
            let canaries = [0x300, 0x350, 0x3E0].map(|a| read_data_u8(&cpu, &mut bus, a));
            assert_eq!(identity, (&cpu as *const Cpu, &bus as *const Bus));
            checkpoints.push(Event {
                p2,
                p2_before,
                p2_after: bus.p2_output_latch().unwrap(),
                incoming_p2_generation,
                p2_generation: retained_generation.clone(),
                software: alternate::Event {
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
                },
            });
        }
        sequences.push(Sequence {
            scratch_pattern: pattern,
            machine_instances: 1,
            checkpoints,
        });
    }
    response.entry_contracts = entry_contracts();
    response.p2_latch_sequences = Some(sequences);
    Ok(response)
}
