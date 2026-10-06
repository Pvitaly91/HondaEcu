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
pub fn run(r: Request, response: Response) -> Result<Response, String> {
    let s = r.p2_output_latch_handoff.as_ref().expect("validated");
    run_chain(
        &r,
        &s.initial_state,
        &s.calls,
        s.p2_output_latch,
        response,
        None,
        false,
        false,
        None,
        None,
    )
}
pub(crate) fn run_chain(
    r: &Request,
    initial: &handoff::Initial,
    calls: &[prefix::Call],
    latch: u8,
    mut response: Response,
    control_config: Option<crate::post_p2_control::Config>,
    below_enabled: bool,
    cal_rt_enabled: bool,
    selector_initial: Option<u8>,
    caller_config: Option<&crate::fallthrough_data0136::Stimulus>,
) -> Result<Response, String> {
    let mut sequences = vec![];
    let mut control_sequences = vec![];
    let mut below_sequences = vec![];
    let mut roundtrip_sequences = vec![];
    let mut selector_sequences = vec![];
    let mut caller_sequences = vec![];
    for &pattern in &r.scratch_patterns {
        let (mut cpu, mut bus) =
            prefix::initialize(&r.images[0].rom, pattern, &initial.quartet_prefix);
        bus.configure_scoped_access(vec![[0, 4096]], 4096);
        let prior = read_data_u8(&cpu, &mut bus, 0x128);
        write_data_u8(
            &mut cpu,
            &mut bus,
            0x128,
            (prior & !4) | if initial.bit0128_2 { 4 } else { 0 },
        );
        write_data_u8(&mut cpu, &mut bus, 0x117, initial.byte0117);
        if let Some(value) = selector_initial {
            bus.initialize_retained_selector(value)?;
        }
        let identity = (&cpu as *const Cpu, &bus as *const Bus);
        bus.initialize_p2_output_latch(latch)?;
        if let Some(c) = control_config {
            bus.initialize_post_p2_control(c.tcon0, c.trnsit_flags)?;
        }
        let mut retained_generation = None;
        let mut tcon0_generation = None;
        let mut trnsit_generation = None;
        let mut selector_generation = None;
        let mut retained_producer_frame = None;
        let mut terminal = false;
        let mut checkpoints = vec![];
        let mut control_checkpoints = vec![];
        let mut below_checkpoints = vec![];
        let mut roundtrip_checkpoints = vec![];
        let mut selector_checkpoints = vec![];
        let mut caller_checkpoints = vec![];
        for (i, call) in calls.iter().enumerate() {
            let selector_before = if selector_initial.is_some() {
                bus.configure_scoped_access(vec![[0x13C, 0x13D]], 4096);
                read_data_u8(&cpu, &mut bus, 0x13C)
            } else {
                0
            };
            let incoming_selector_generation = selector_generation.clone();
            let before = alternate::state(&cpu, &mut bus);
            let mut p = prefix::checkpoint(&cpu, &mut bus, call, i as u32, pattern);
            let p2_before = bus.p2_output_latch().expect("initial snapshot");
            let incoming_p2_generation = retained_generation.clone();
            let control_before = bus.post_p2_control().unwrap_or([0, 0]);
            let incoming_tcon0_generation = tcon0_generation.clone();
            let incoming_trnsit_generation = trnsit_generation.clone();
            let mut control = None;
            let mut below = None;
            let mut first_p2_after = p2_before;
            let mut first_p2_generation = retained_generation.clone();
            let mut after_control = control_before;
            let mut after_tgen = tcon0_generation.clone();
            let mut after_rgen = trnsit_generation.clone();
            let mut p2 = None;
            let mut consumer = None;
            let mut alternate = None;
            let mut compare_generation = None;
            let mut abi = vec![];
            let mut disposition = "NotRun";
            let mut provenance = "NoFresh0196";
            let mut generation = None;
            let mut native_cal = None;
            let mut native_rt = None;
            let mut call_frame = None;
            let mut stack_journal = vec![];
            let mut post_return = None;
            let mut reader0584_generation = None;
            let mut reader063e_generation = None;
            let mut selector_handoff = "NotRun";
            let mut caller = None;
            let mut producer = None;
            let mut producer_call_frame = None;
            let mut pending_return_word = None;
            let mut caller_route = "NotRun";
            let mut producer_admission = "NotRun";
            let mut software_tail = None;
            if !terminal {
                bus.begin_continuity();
                if below_enabled {
                    bus.begin_all_native();
                }
                if selector_initial.is_some() {
                    prefix::execute_checkpoint_retained(&mut cpu, &mut bus, call, &mut p);
                    let all = bus.all_native_snapshot();
                    reader0584_generation = crate::post_return_selector::reader(
                        &all,
                        &incoming_selector_generation,
                        0x0584,
                    );
                    let read = all.iter().any(|a| {
                        a[0] == 0 && a[1] == 0x0584 && a[2] == 0x13C && a[3] == 8 && a[4] == 0
                    });
                    selector_handoff = if !read {
                        "NextEventSelectorNotReached"
                    } else if incoming_selector_generation.is_none() {
                        "InitialSelectorControl"
                    } else if reader0584_generation.is_some() && p.selected_generation.is_some() {
                        "NativeSelectorHandoffStrict"
                    } else {
                        "NativeSelectorReadWithoutQuartetHandoff"
                    };
                } else {
                    prefix::execute_checkpoint(&mut cpu, &mut bus, call, &mut p);
                }
                if let Some(g) = &p.result_generation {
                    provenance = if p.selected_generation.is_some() {
                        "QuartetDerived0196"
                    } else {
                        "ConsumerGateBypass0196"
                    };
                    if cal_rt_enabled {
                        abi.push([0, cpu.pc as u32, 0x063B]);
                        cpu.pc = 0x063B; // Sole disclosed PC-only scheduler seam.
                        let output = crate::cal_rt_roundtrip::execute(&mut cpu, &mut bus, true)?;
                        if output.suffix.stage.result.status != 0 {
                            return Err("Exact CAL063B instruction not established".into());
                        }
                        let all = bus.all_native_snapshot();
                        let write = all
                            .iter()
                            .filter(|a| a[4] == 1)
                            .enumerate()
                            .last()
                            .ok_or("CAL frame write missing")?;
                        call_frame = Some(crate::cal_rt_roundtrip::Frame {
                            writer_pc: 0x063B,
                            event_index: i as u32,
                            stack_address: output.suffix.entry.ssp as u32,
                            width: 16,
                            return_pc: 0x063B + 3,
                            write_order: write.0 as u32,
                        });
                        stack_journal.extend(output.suffix.accesses.iter().copied());
                        native_cal = Some(output);
                    } else {
                        abi.push([0, cpu.pc as u32, 0x54F5]);
                        cpu.pc = 0x54F5;
                    }
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
                        first_p2_after = bus.p2_output_latch().unwrap();
                        first_p2_generation = retained_generation.clone();
                        if control_config.is_some()
                            && matches!(
                                disposition,
                                "QuartetDerivedP2LatchStrict" | "GateBypassP2LatchControl"
                            )
                        {
                            // Actual native exit PC, actual retained CPU/Bus; no host jump or reseed.
                            let output =
                                crate::post_p2_control::execute_control(&mut cpu, &mut bus);
                            let order = bus
                                .continuity_snapshot()
                                .iter()
                                .filter(|a| a[0] == 1 && a[4] == 1)
                                .count() as u32
                                + 1;
                            for (n, w) in output
                                .control_accesses
                                .iter()
                                .filter(|a| a[3] == 1)
                                .enumerate()
                            {
                                let g = prefix::Generation {
                                    writer_pc: w[0],
                                    event_index: i as u32,
                                    write_order: order + n as u32,
                                    value: w[4],
                                };
                                if w[1] == 0x40 {
                                    tcon0_generation = Some(g);
                                } else {
                                    trnsit_generation = Some(g);
                                }
                            }
                            disposition = match output.suffix.stage.result.status {
                                0 => {
                                    if provenance == "QuartetDerived0196" {
                                        "PostP2ControlStrict"
                                    } else {
                                        "PostP2ControlGateBypass"
                                    }
                                }
                                3 => "BudgetExceeded",
                                2 => "ExecutionError",
                                _ => "ControlPartial",
                            };
                            control = Some(output);
                            after_control = bus.post_p2_control().unwrap();
                            after_tgen = tcon0_generation.clone();
                            after_rgen = trnsit_generation.clone();
                            if below_enabled
                                && cpu.pc == 0x55D2
                                && matches!(
                                    disposition,
                                    "PostP2ControlStrict" | "PostP2ControlGateBypass"
                                )
                            {
                                let output = crate::below_second_p2::execute(&mut cpu, &mut bus);
                                let all = bus.all_native_snapshot();
                                for (order, w) in all.iter().filter(|a| a[4] == 1).enumerate() {
                                    let g = prefix::Generation {
                                        writer_pc: w[1],
                                        event_index: i as u32,
                                        write_order: order as u32,
                                        value: w[5],
                                    };
                                    if w[0] == 1 && w[1] == 0x5682 {
                                        retained_generation = Some(g);
                                    } else if w[0] == 2 && w[1] == 0x55D5 {
                                        tcon0_generation = Some(g);
                                    }
                                }
                                disposition = match output.suffix.stage.result.status {
                                    0 => {
                                        if provenance == "QuartetDerived0196" {
                                            "BelowSecondP2Strict"
                                        } else {
                                            "BelowSecondP2GateBypass"
                                        }
                                    }
                                    3 => "BudgetExceeded",
                                    2 => "ExecutionError",
                                    _ => "BelowContinuationPartial",
                                };
                                below = Some(output);
                                if cal_rt_enabled
                                    && matches!(
                                        disposition,
                                        "BelowSecondP2Strict" | "BelowSecondP2GateBypass"
                                    )
                                {
                                    let output = crate::cal_rt_roundtrip::execute(
                                        &mut cpu, &mut bus, false,
                                    )?;
                                    disposition = if output.suffix.stage.result.status == 0 {
                                        if provenance == "QuartetDerived0196" {
                                            "CallReturnStrict"
                                        } else {
                                            "CallReturnGateBypass"
                                        }
                                    } else {
                                        "CallerFramePartial"
                                    };
                                    stack_journal.extend(output.suffix.accesses.iter().copied());
                                    native_rt = Some(output);
                                    if selector_initial.is_some()
                                        && matches!(
                                            disposition,
                                            "CallReturnStrict" | "CallReturnGateBypass"
                                        )
                                    {
                                        let output = crate::post_return_selector::execute(
                                            &mut cpu, &mut bus,
                                        )?;
                                        let all = bus.all_native_snapshot();
                                        reader063e_generation = crate::post_return_selector::reader(
                                            &all,
                                            &incoming_selector_generation,
                                            0x063E,
                                        );
                                        for (order, w) in
                                            all.iter().filter(|a| a[4] == 1).enumerate()
                                        {
                                            if *w == [0, 0x064A, 0x13C, 8, 1, w[5]] {
                                                selector_generation = Some(prefix::Generation {
                                                    writer_pc: 0x064A,
                                                    event_index: i as u32,
                                                    write_order: order as u32,
                                                    value: w[5],
                                                });
                                            }
                                        }
                                        disposition = if output.stage.result.status == 0 {
                                            if provenance == "QuartetDerived0196" {
                                                "PostReturnSelectorStrict"
                                            } else {
                                                "PostReturnSelectorGateBypass"
                                            }
                                        } else {
                                            "SelectorProducerPartial"
                                        };
                                        post_return = Some(output);
                                    }
                                }
                            }
                        }
                    } else if disposition == "0196AlternatePartial" {
                        disposition = "UpstreamPartial";
                    }
                    consumer = Some(c);
                    if cal_rt_enabled
                        && !matches!(
                            disposition,
                            "CallReturnStrict"
                                | "CallReturnGateBypass"
                                | "PostReturnSelectorStrict"
                                | "PostReturnSelectorGateBypass"
                                | "SelectorProducerPartial"
                        )
                    {
                        disposition = "CallerFramePartial";
                    }
                } else {
                    disposition = "NoFresh0196";
                }
                if let Some(config) = caller_config {
                    if matches!(
                        disposition,
                        "PostReturnSelectorStrict" | "PostReturnSelectorGateBypass"
                    ) {
                        let output =
                            crate::fallthrough_data0136::execute_caller(&mut cpu, &mut bus)?;
                        let events = &output.suffix.stage.events;
                        caller_route = if events.first().is_some_and(|e| e[1] == 0x065F) {
                            "PrimaryTakenCalSkippedControl"
                        } else if events.iter().any(|e| e[0] == 0x064F && e[1] == 0x065F) {
                            "FallthroughDirectVia011B7"
                        } else {
                            "FallthroughVia012A0"
                        };
                        disposition = if output.suffix.stage.result.status != 0 {
                            "CallerSuffixPartial"
                        } else if cpu.pc == 0x0657 {
                            "CallerTrnsitBoundaryControl"
                        } else if cpu.pc == 0x0667 {
                            "CallerCalSkippedControl"
                        } else {
                            "NativeProducerCallEstablished"
                        };
                        let all = bus.all_native_snapshot();
                        let address = output.suffix.entry.ssp;
                        for (order, w) in all.iter().filter(|a| a[4] == 1).enumerate() {
                            if *w == [0, 0x0664, address as u32, 16, 1, 0x0667] {
                                producer_call_frame = Some(crate::cal_rt_roundtrip::Frame {
                                    writer_pc: 0x0664,
                                    event_index: i as u32,
                                    stack_address: address as u32,
                                    width: 16,
                                    return_pc: 0x0667,
                                    write_order: order as u32,
                                });
                            }
                        }
                        if cpu.pc == 0x56BE && output.suffix.stage.result.status == 0 {
                            producer_admission =
                                crate::fallthrough_data0136::producer_admission(&cpu, &mut bus);
                            if producer_admission == "Mode0RetainedSlot0FirstObservation" {
                                let body = crate::fallthrough_data0136::execute_no_write_body(
                                    &mut cpu,
                                    &mut bus,
                                    &config.calls[i].producer_observation,
                                )?;
                                disposition = if body.suffix.stage.result.status == 0 {
                                    if provenance == "QuartetDerived0196" {
                                        "NativeFallthroughCallerProducerNoWriteStrict"
                                    } else {
                                        "GateBypassFallthroughProducerControl"
                                    }
                                } else {
                                    "ProducerBodyPartial"
                                };
                                if r.operation == crate::data0136_tail::OPERATION
                                    && body.suffix.stage.result.status == 0
                                {
                                    let frame = producer_call_frame
                                        .as_ref()
                                        .ok_or("Native0664 frame required for tail")?;
                                    let tail =
                                        crate::data0136_tail::execute(&mut cpu, &mut bus, frame)?;
                                    disposition = if tail.disposition == "TailLiveInBlocked" {
                                        if provenance == "QuartetDerived0196" {
                                            "TailLiveInBlocked"
                                        } else {
                                            "TailLiveInBlockedGateControl"
                                        }
                                    } else {
                                        "TailExecutionPartial"
                                    };
                                    software_tail = Some(tail);
                                }
                                producer = Some(body);
                            } else {
                                disposition = "ProducerEntryBlockedControl";
                            }
                        }
                        if producer_call_frame.is_some() {
                            pending_return_word = Some(crate::fallthrough_data0136::pending_word(
                                &cpu, &mut bus, address,
                            ));
                            retained_producer_frame = producer_call_frame.clone();
                        }
                        caller = Some(output);
                    }
                }
                // Every new caller boundary is terminal, including controls.
                // Never schedule another event with the native0664 frame open.
                terminal = caller_config.is_some()
                    || !matches!(
                        disposition,
                        "QuartetDerivedP2LatchStrict"
                            | "GateBypassP2LatchControl"
                            | "PostP2ControlStrict"
                            | "PostP2ControlGateBypass"
                            | "BelowSecondP2Strict"
                            | "BelowSecondP2GateBypass"
                            | "CallReturnStrict"
                            | "CallReturnGateBypass"
                            | "PostReturnSelectorStrict"
                            | "PostReturnSelectorGateBypass"
                    );
            }
            let journal = if disposition == "NotRun" {
                vec![]
            } else {
                bus.end_continuity()
            };
            let all_native_journal = if below_enabled {
                bus.end_all_native()
            } else {
                vec![]
            };
            if caller_config.is_some() && producer_call_frame.is_none() {
                producer_call_frame = retained_producer_frame.clone();
                if let Some(frame) = &producer_call_frame {
                    pending_return_word = Some(crate::fallthrough_data0136::pending_word(
                        &cpu,
                        &mut bus,
                        frame.stack_address as u16,
                    ));
                }
            }
            // Read-only diagnostics must observe the actual incoming banks even
            // when the prefix stopped before entering M2x's local/SCB bank.
            bus.configure_scoped_access(vec![[0, 4096]], 4096);
            let after = boundary(&cpu, &mut bus);
            let selector_after = if selector_initial.is_some() {
                read_data_u8(&cpu, &mut bus, 0x13C)
            } else {
                0
            };
            let state_after = alternate::state(&cpu, &mut bus);
            bus.configure_scoped_access(vec![[0x300, 0x301], [0x350, 0x351], [0x3E0, 0x3E1]], 4096);
            let canaries = [0x300, 0x350, 0x3E0].map(|a| read_data_u8(&cpu, &mut bus, a));
            assert_eq!(identity, (&cpu as *const Cpu, &bus as *const Bus));
            let event = Event {
                p2,
                p2_before,
                p2_after: if below_enabled {
                    first_p2_after
                } else {
                    bus.p2_output_latch().unwrap()
                },
                incoming_p2_generation,
                p2_generation: if below_enabled {
                    first_p2_generation
                } else {
                    retained_generation.clone()
                },
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
            };
            if control_config.is_some() {
                let upstream = crate::post_p2_control::Event {
                    p2: event,
                    control,
                    control_before,
                    control_after: if below_enabled {
                        after_control
                    } else {
                        bus.post_p2_control().unwrap()
                    },
                    incoming_tcon0_generation,
                    tcon0_generation: if below_enabled {
                        after_tgen
                    } else {
                        tcon0_generation.clone()
                    },
                    incoming_trnsit_generation,
                    trnsit_generation: if below_enabled {
                        after_rgen
                    } else {
                        trnsit_generation.clone()
                    },
                };
                if below_enabled {
                    let below_event = crate::below_second_p2::Event {
                        upstream,
                        below,
                        second_p2_after: bus.p2_output_latch().unwrap(),
                        second_p2_generation: retained_generation.clone(),
                        final_tcon0: bus.post_p2_control().unwrap()[0],
                        final_tcon0_generation: tcon0_generation.clone(),
                        all_native_journal,
                    };
                    if cal_rt_enabled {
                        let round_trip = crate::cal_rt_roundtrip::Event {
                            below: below_event,
                            native_cal,
                            native_rt,
                            call_frame,
                            stack_journal,
                        };
                        if selector_initial.is_some() {
                            let selector_event = crate::post_return_selector::Event {
                                round_trip,
                                post_return,
                                selector_before,
                                selector_after,
                                incoming_selector_generation,
                                reader0584_generation,
                                reader063e_generation,
                                selector_generation: selector_generation.clone(),
                                selector_handoff,
                            };
                            if caller_config.is_some() {
                                caller_checkpoints.push(crate::fallthrough_data0136::Event {
                                    selector: selector_event,
                                    caller,
                                    producer,
                                    producer_call_frame,
                                    pending_return_word,
                                    caller_route,
                                    producer_admission,
                                    software_tail,
                                });
                            } else {
                                selector_checkpoints.push(selector_event);
                            }
                        } else {
                            roundtrip_checkpoints.push(round_trip);
                        }
                    } else {
                        below_checkpoints.push(below_event);
                    }
                } else {
                    control_checkpoints.push(upstream);
                }
            } else {
                checkpoints.push(event);
            }
        }
        sequences.push(Sequence {
            scratch_pattern: pattern,
            machine_instances: 1,
            checkpoints,
        });
        if control_config.is_some() {
            control_sequences.push(crate::post_p2_control::Sequence {
                scratch_pattern: pattern,
                machine_instances: 1,
                checkpoints: control_checkpoints,
            });
        }
        if below_enabled {
            if let Some(value) = selector_initial {
                if caller_config.is_some() {
                    caller_sequences.push(crate::fallthrough_data0136::Sequence {
                        scratch_pattern: pattern,
                        machine_instances: 1,
                        selector_initialization_writes: vec![[0x13C, 8, u32::from(value)]],
                        checkpoints: caller_checkpoints,
                    });
                }
                selector_sequences.push(crate::post_return_selector::Sequence {
                    scratch_pattern: pattern,
                    machine_instances: 1,
                    selector_initialization_writes: vec![[0x13C, 8, u32::from(value)]],
                    checkpoints: selector_checkpoints,
                });
            }
            if cal_rt_enabled {
                roundtrip_sequences.push(crate::cal_rt_roundtrip::Sequence {
                    scratch_pattern: pattern,
                    machine_instances: 1,
                    checkpoints: roundtrip_checkpoints,
                });
            }
            below_sequences.push(crate::below_second_p2::Sequence {
                scratch_pattern: pattern,
                machine_instances: 1,
                checkpoints: below_checkpoints,
            });
        }
    }
    if caller_config.is_some() {
        if r.operation == crate::data0136_tail::OPERATION {
            response.entry_contracts = crate::data0136_tail::entry_contracts();
            response.data0136_tail_sequences = Some(caller_sequences);
        } else {
            response.entry_contracts = crate::fallthrough_data0136::entry_contracts();
            response.fallthrough_data0136_caller_sequences = Some(caller_sequences);
        }
    } else if selector_initial.is_some() {
        response.entry_contracts = crate::post_return_selector::entry_contracts();
        response.post_return_selector_sequences = Some(selector_sequences);
    } else if cal_rt_enabled {
        response.entry_contracts = crate::cal_rt_roundtrip::entry_contracts();
        response.cal_rt_round_trip_sequences = Some(roundtrip_sequences);
    } else if below_enabled {
        response.entry_contracts = crate::below_second_p2::entry_contracts();
        response.below_second_p2_sequences = Some(below_sequences);
    } else if control_config.is_some() {
        response.entry_contracts = crate::post_p2_control::entry_contracts();
        response.post_p2_control_sequences = Some(control_sequences);
    } else {
        response.entry_contracts = entry_contracts();
        response.p2_latch_sequences = Some(sequences);
    }
    Ok(response)
}
