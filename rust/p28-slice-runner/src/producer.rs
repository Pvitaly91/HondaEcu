//! Narrow RAM-snapshot producer and explicit staged composition. No G formula.
use crate::protocol::{
    CaseResult, Diagnostic, Request, Response, ADD_ASSUMPTION, PRODUCER_ADD_ASSUMPTION,
};
use crate::runner::{
    compact_contract, execute_case, execute_in_state, seed_machine, threshold_contract,
    SliceContract,
};

const MAX_CASES: usize = 200_000;
const MAX_DIAGNOSTICS: usize = 40;

pub fn validate_producer_request(request: &Request) -> Result<(), String> {
    let cases = request
        .producer_cases
        .as_ref()
        .ok_or("producer cases required")?;
    if cases.is_empty()
        || cases.len() > MAX_CASES
        || request.synthetic.is_some()
        || request.scratch_patterns != [0, 85, 170]
        || request.images[0].id != "baseline"
        || request.images.iter().any(|image| image.rom.len() != 32768)
        || request
            .images
            .get(1)
            .is_some_and(|image| image.id != "derived")
    {
        return Err("invalid producer batch contract".into());
    }
    for (index, row) in cases.iter().enumerate() {
        if row[0] != index as u32
            || ![0, 85, 170].contains(&row[1])
            || row[2..9].iter().any(|v| *v > 65535)
            || row[9] > 255
            || row[10] > 255
            || row[11] > 1
            || row[12] > 3
            || row[13] > 1
        {
            return Err("invalid or non-contiguous producer input case".into());
        }
    }
    Ok(())
}

pub fn producer_contract(row: &[u32; 14]) -> SliceContract {
    let mut seeds = vec![
        [0xC4, (row[8] & 255) as u16],
        [0xC5, (row[8] >> 8) as u16],
        [0x217, row[9] as u16],
        [0x231, row[10] as u16],
    ];
    for sample in 0..6 {
        seeds.push([0x360 + sample as u16 * 2, (row[2 + sample] & 255) as u16]);
        seeds.push([0x361 + sample as u16 * 2, (row[2 + sample] >> 8) as u16]);
    }
    let mut outputs = vec![0xC4, 0xC5, 0x217, 0x231];
    outputs.extend(0x360..0x36C);
    SliceContract {
        entry_pc: 0x0772,
        exit_pcs: vec![0x07A5],
        code_ranges: vec![[0x0772, 0x07A5], [0x7AEC, 0x7AFE]],
        psw: 0x1101,
        lrb: 0x40,
        usp: 0x180,
        instruction_budget: 192,
        data_seeds: seeds,
        output_addresses: outputs,
        program_read_range: Some([0, 0]),
    }
}

pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![
        serde_json::json!({"id":"producer","entryPc":0x0772,"exitPcs":[0x07A5],"stop":"BeforeInstruction",
        "allowedCodeRanges":[[0x0772,0x07A5],[0x7AEC,0x7AFE]],"psw":0x1101,"lrb":0x40,"usp":0x180,
        "instructionBudget":192,"sampleAddresses":[0x360,0x362,0x364,0x366,0x368,0x36A],
        "previousTAddress":0xC4,"statusAddresses":[0x217,0x231],"codeDataSpacesSeparate":true,
        "interrupts":"NotInjected","peripherals":"Frozen","admission":"ExactInstructionForms"}),
        serde_json::json!({"id":"producerToCompact","composition":"StagedControlFlowSameCpuRam",
            "fromPc":0x07A5,"toPc":0x07C7,"exitPc":0x0822,"instructionBudget":128,
            "reseedsCpuOrRam":false,"skippedRange":[0x07A5,0x07C7],"continuousWholeRoutine":false,
            "transferredInputs":["actual DATA00C4","actual DATA0217.4"],"assumptions":"Cumulative"}),
        serde_json::json!({"id":"composedThreshold","composition":"StagedFreshThresholdSeed",
            "entryPc":0x122C,"exitPcs":[0x126D,0x1281],"allowedCodeRanges":[[0x122C,0x126D]],
            "psw":0x0101,"lrb":0x20,"usp":0x280,"instructionBudget":128,
            "codeInput":"ActualCompactExecutionOutput","contextPriorEnabled":"ExplicitPerCaseInputs",
            "allowedAssumptions":[],"cumulativeAssumptionsRetained":true}),
    ]
}

fn mask(result: &CaseResult) -> i32 {
    i32::from(
        result
            .used_assumptions
            .iter()
            .any(|s| s == PRODUCER_ADD_ASSUMPTION),
    ) | (i32::from(result.used_assumptions.iter().any(|s| s == ADD_ASSUMPTION)) << 1)
}

pub fn run_producer_batch(request: &Request, mut response: Response) -> Result<Response, String> {
    let cases = request
        .producer_cases
        .as_ref()
        .ok_or("producer cases required")?;
    let assumptions: Vec<_> = request
        .allow_assumptions
        .iter()
        .map(String::as_str)
        .collect();
    response.entry_contracts = entry_contracts();
    let mut rows = Vec::with_capacity(cases.len());
    let mut threshold_rows = Vec::with_capacity(cases.len() * request.images.len());
    for input in cases {
        let contract = producer_contract(input);
        let (mut cpu, mut bus) = seed_machine(&request.images[0].rom, &contract, input[1] as u8);
        // Bounded diagnostics span both uniform-series modes and a boundary,
        // plus the final supplied case. A one-case mismatch replay is selected.
        let selected = input[0] < 2
            || [65535, 65536, 65537, 131071, 131072].contains(&input[0])
            || input[0] as usize + 1 == cases.len();
        let g = execute_in_state(&mut cpu, &mut bus, &contract, &assumptions, selected, true);
        let mut row = [0i32; 22];
        row[0] = input[0] as i32;
        row[1] = input[1] as i32;
        row[2] = g.status;
        row[3] = g.stop_pc as i32;
        row[4] = g.steps as i32;
        row[5] = g.outputs[0] | (g.outputs[1] << 8);
        row[6] = g.outputs[2];
        row[7] = g.outputs[3];
        for sample in 0..6 {
            row[8 + sample] = g.outputs[4 + sample * 2] | (g.outputs[5 + sample * 2] << 8);
        }
        row[14] = mask(&g);
        row[15] = 4;
        row[16] = -1;
        row[17] = 0;
        row[18] = -1;
        row[19] = -1;
        row[20] = row[14];
        row[21] = cpu.a as i32;
        if (selected || g.status >= 2) && response.diagnostics.len() < MAX_DIAGNOSTICS {
            let trace = if selected {
                g.clone()
            } else {
                let (mut diagnostic_cpu, mut diagnostic_bus) =
                    seed_machine(&request.images[0].rom, &contract, input[1] as u8);
                execute_in_state(
                    &mut diagnostic_cpu,
                    &mut diagnostic_bus,
                    &contract,
                    &assumptions,
                    true,
                    true,
                )
            };
            response.diagnostics.push(Diagnostic {
                slice: "producer",
                image_index: 0,
                inputs: input.iter().map(|v| *v as i32).collect(),
                result: trace,
            });
        }
        if g.status == 0 {
            // Deliberate staged control-flow transfer, not a claim to have
            // executed the omitted history/delta block. No register/RAM seed is
            // replayed here: F consumes the state actually left by G.
            cpu.pc = 0x07C7;
            let f = execute_in_state(
                &mut cpu,
                &mut bus,
                &compact_contract(0, false),
                &assumptions,
                selected,
                false,
            );
            row[15] = f.status;
            row[16] = f.stop_pc as i32;
            row[17] = f.steps as i32;
            row[20] |= mask(&f);
            if f.status == 0 {
                row[18] = f.outputs[0];
                row[19] = (f.outputs[1] >> 4) & 1;
            }
            if (selected || f.status >= 2) && response.diagnostics.len() < MAX_DIAGNOSTICS {
                let trace = if selected {
                    f
                } else {
                    let (mut diagnostic_cpu, mut diagnostic_bus) =
                        seed_machine(&request.images[0].rom, &contract, input[1] as u8);
                    let replay_g = execute_in_state(
                        &mut diagnostic_cpu,
                        &mut diagnostic_bus,
                        &contract,
                        &assumptions,
                        false,
                        true,
                    );
                    if replay_g.status == 0 {
                        diagnostic_cpu.pc = 0x07C7;
                        execute_in_state(
                            &mut diagnostic_cpu,
                            &mut diagnostic_bus,
                            &compact_contract(0, false),
                            &assumptions,
                            true,
                            false,
                        )
                    } else {
                        replay_g
                    }
                };
                response.diagnostics.push(Diagnostic {
                    slice: "producer-compact",
                    image_index: 0,
                    inputs: vec![input[0] as i32, input[1] as i32],
                    result: trace,
                });
            }
        }
        for (image_index, image) in request.images.iter().enumerate() {
            let mut threshold = [
                input[0] as i32,
                image_index as i32,
                4,
                -1,
                -1,
                -1,
                -1,
                -1,
                row[20],
            ];
            if row[15] == 0 {
                let c = threshold_contract(
                    row[18] as u8,
                    input[11] as u8,
                    input[12] as u8,
                    input[13] != 0,
                );
                let result = execute_case(&image.rom, &c, input[1] as u8, false, selected);
                threshold[2] = result.status;
                if result.status == 0 {
                    threshold[3] = (result.outputs[0] >> 1) & 3;
                }
                for (slot, address) in threshold[4..8].iter_mut().zip(&result.program_reads) {
                    *slot = *address as i32;
                }
                if result.program_reads.len() > 4 {
                    threshold[2] = 2;
                    threshold[3] = -1;
                }
                if (selected || result.status >= 2) && response.diagnostics.len() < MAX_DIAGNOSTICS
                {
                    let trace = if selected {
                        result
                    } else {
                        execute_case(&image.rom, &c, input[1] as u8, false, true)
                    };
                    response.diagnostics.push(Diagnostic {
                        slice: "producer-threshold",
                        image_index,
                        inputs: vec![
                            input[0] as i32,
                            input[1] as i32,
                            input[11] as i32,
                            input[12] as i32,
                            input[13] as i32,
                        ],
                        result: trace,
                    });
                }
            }
            threshold_rows.push(threshold);
        }
        rows.push(row);
    }
    response.producer_rows = Some(rows);
    response.producer_threshold_rows = Some(threshold_rows);
    Ok(response)
}
