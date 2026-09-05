//! Seeded incremental native checksum execution. This module does not sum ROM
//! bytes on the host. Computed bytes are observed from actual banked r0, while
//! the host checks execution bounds, state progression and lossless read order.
use serde::Serialize;

use crate::exec::{read_data_u16, read_data_u8};
use crate::instruction_forms::checksum_form_admission;
use crate::protocol::{Request, Response, TraceEntry};
use crate::runner::{execute_in_state_with_policy, seed_machine, SliceContract};

const ENTRY: u16 = 0x2B70;
const ORDINARY_EXIT: u16 = 0x2BB6;
const FAILURE_EXIT: u16 = 0x24E9;
const INVOCATIONS: u32 = 512;
const INSTRUCTION_BUDGET: u32 = 256;
const BLOCK_BYTES: usize = 64;
const ROM_SIZE: usize = 32768;
const CONTROL_BYTE: u16 = 0x60FB;
const COUNTER: u16 = 0x396;
const SUM: u16 = 0x398;
const R0: u16 = 0x208;
const STATUS: u16 = 0xF5;
const DATA_RANGES: [[u16; 2]; 5] = [
    [6, 8],
    [0x80, 0x88],
    [0xF5, 0xF6],
    [0x208, 0x20C],
    [0x396, 0x399],
];

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ChecksumCheckpoint {
    pub invocation: u32,
    pub counter_before: u16,
    pub counter_after: u16,
    pub sum_before: u8,
    pub sum_after: u8,
    pub computed_byte: u8,
    pub exit_pc: u16,
    pub steps: u32,
    pub program_read_count: usize,
    /// [start,length]; exact ordered byte-read stream, including repeat reads.
    pub program_read_runs: Vec<[u32; 2]>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ChecksumCase {
    pub image_index: usize,
    pub scratch_pattern: u8,
    /// 0 complete,1 unresolved form,2 execution/contract error,3 exhausted budget.
    pub status: i32,
    pub completed: bool,
    pub decision: &'static str,
    pub invocations: u32,
    pub steps: u32,
    pub stop_pc: u16,
    pub residue: i32,
    pub counter: u16,
    pub accumulated_byte: u8,
    pub status_byte: u8,
    pub program_read_count: usize,
    pub program_read_runs: Vec<[u32; 2]>,
    /// [start,endExclusive]; all distinct observed program-data byte addresses.
    pub coverage_ranges: Vec<[u32; 2]>,
    pub used_assumptions: Vec<String>,
    pub checkpoints: Vec<ChecksumCheckpoint>,
    /// Bounded first128 instructions from the last attempted invocation.
    pub trace: Vec<TraceEntry>,
    pub error: Option<String>,
}

pub fn entry_contract() -> serde_json::Value {
    serde_json::json!({
        "id":"checksum","entryPc":ENTRY,"exitPcs":[ORDINARY_EXIT,FAILURE_EXIT],"stop":"BeforeInstruction",
        "allowedCodeRanges":[[ENTRY,ORDINARY_EXIT]],"psw":0x0100,"lrb":0x0041,"usp":0x0180,"ssp":0x047E,
        "initialState":{"counterAddress":COUNTER,"counter":0,"sumAddress":SUM,"sum":0,"statusAddress":STATUS,"status":0},
        "allowedDataRanges":DATA_RANGES,"allowedProgramDataReads":[0,ROM_SIZE],
        "instructionBudgetPerInvocation":INSTRUCTION_BUDGET,"maximumInvocations":INVOCATIONS,
        "maximumTotalInstructions":INSTRUCTION_BUDGET*INVOCATIONS,"bytesPerInvocation":BLOCK_BYTES,
        "programReadOrder":"AscendingBytesWithinLittleEndianWords","readRuns":"StartAndLengthIncludingRepeats",
        "controlReadAddress":CONTROL_BYTE,"completion":"512 completed invocations, exact scan coverage and actual counter reset",
        "statePreservedAcrossInvocations":true,"reentry":"Only PC is staged to entry; no RAM or register reseeding",
        "initialization":"Seeded snapshot grounded in startup clear, not executed reset",
        "codeDataSpacesSeparate":true,"interrupts":"NotInjected","peripherals":"Frozen","permittedAssumptions":[]
    })
}

pub fn validate_request(request: &Request) -> Result<(), String> {
    let mut ids = std::collections::HashSet::new();
    if request.synthetic.is_some()
        || request.producer_cases.is_some()
        || !request.allow_assumptions.is_empty()
        || request.scratch_patterns != [0, 85, 170]
        || request.images.iter().any(|image| {
            image.rom.len() != ROM_SIZE
                || image.id.is_empty()
                || image.id.len() > 64
                || !image
                    .id
                    .chars()
                    .all(|c| c.is_ascii_alphanumeric() || "-_.".contains(c))
                || !ids.insert(&image.id)
        })
    {
        return Err("invalid fixed native checksum batch contract".into());
    }
    Ok(())
}

fn contract(budget: u32) -> SliceContract {
    SliceContract {
        entry_pc: ENTRY,
        exit_pcs: vec![ORDINARY_EXIT, FAILURE_EXIT],
        code_ranges: vec![[ENTRY as u32, ORDINARY_EXIT as u32]],
        psw: 0x0100,
        lrb: 0x0041,
        usp: 0x0180,
        instruction_budget: budget,
        data_seeds: vec![[COUNTER, 0], [COUNTER + 1, 0], [SUM, 0], [STATUS, 0]],
        output_addresses: vec![],
        program_read_range: Some([0, ROM_SIZE as u32]),
    }
}

fn append_read(runs: &mut Vec<[u32; 2]>, address: u16) {
    if let Some(last) = runs.last_mut() {
        if last[0] + last[1] == address as u32 {
            last[1] += 1;
            return;
        }
    }
    runs.push([address as u32, 1]);
}

fn compress(reads: &[u16]) -> Vec<[u32; 2]> {
    let mut runs = vec![];
    for &address in reads {
        append_read(&mut runs, address);
    }
    runs
}

fn coverage(reads: &[bool]) -> Vec<[u32; 2]> {
    let mut result = vec![];
    let mut cursor = 0;
    while cursor < reads.len() {
        if !reads[cursor] {
            cursor += 1;
            continue;
        }
        let start = cursor;
        while cursor < reads.len() && reads[cursor] {
            cursor += 1;
        }
        result.push([start as u32, cursor as u32]);
    }
    result
}

fn reenter(
    cpu: &mut crate::cpu::Cpu,
    bus: &mut crate::bus::Bus,
    contract: &SliceContract,
) -> crate::protocol::CaseResult {
    // Re-enter only this fragment. Actual persistent RAM and CPU registers
    // survive every invocation; the enclosing ECU routine is not emulated.
    cpu.pc = contract.entry_pc;
    bus.clear_program_reads();
    execute_in_state_with_policy(cpu, bus, contract, &[], true, Some(checksum_form_admission))
}

fn execute(
    rom: &[u8],
    image_index: usize,
    pattern: u8,
    maximum_invocations: u32,
    budget: u32,
) -> ChecksumCase {
    let contract = contract(budget);
    let (mut cpu, mut bus) = seed_machine(rom, &contract, pattern);
    cpu.ssp = 0x047E;
    bus.configure_scoped_access(DATA_RANGES.to_vec(), BLOCK_BYTES + 1);
    let mut result = ChecksumCase {
        image_index,
        scratch_pattern: pattern,
        status: 0,
        completed: false,
        decision: "NotCompleted",
        invocations: 0,
        steps: 0,
        stop_pc: ENTRY,
        residue: -1,
        counter: 0,
        accumulated_byte: 0,
        status_byte: 0,
        program_read_count: 0,
        program_read_runs: vec![],
        coverage_ranges: vec![],
        used_assumptions: vec![],
        checkpoints: vec![],
        trace: vec![],
        error: None,
    };
    let mut seen = vec![false; ROM_SIZE];
    for block in 0..maximum_invocations.min(INVOCATIONS) {
        let counter_before = read_data_u16(&cpu, &mut bus, COUNTER);
        let sum_before = read_data_u8(&cpu, &mut bus, SUM);
        let invocation = reenter(&mut cpu, &mut bus, &contract);
        result.invocations += 1;
        result.steps += invocation.steps;
        result.stop_pc = invocation.stop_pc;
        result.counter = read_data_u16(&cpu, &mut bus, COUNTER);
        result.accumulated_byte = read_data_u8(&cpu, &mut bus, SUM);
        result.status_byte = read_data_u8(&cpu, &mut bus, STATUS);
        let computed = read_data_u8(&cpu, &mut bus, R0);
        result.trace = invocation.trace;
        result.program_read_count += invocation.program_reads.len();
        for &address in &invocation.program_reads {
            append_read(&mut result.program_read_runs, address);
            if let Some(item) = seen.get_mut(address as usize) {
                *item = true;
            }
        }
        if invocation.status != 0 {
            result.status = invocation.status;
            result.error = invocation.error;
            break;
        }
        result.checkpoints.push(ChecksumCheckpoint {
            invocation: block + 1,
            counter_before,
            counter_after: result.counter,
            sum_before,
            sum_after: result.accumulated_byte,
            computed_byte: computed,
            exit_pc: result.stop_pc,
            steps: invocation.steps,
            program_read_count: invocation.program_reads.len(),
            program_read_runs: compress(&invocation.program_reads),
        });
        let final_block = block + 1 == INVOCATIONS;
        let scan_reads_match = invocation.program_reads.len() >= BLOCK_BYTES
            && invocation.program_reads[..BLOCK_BYTES]
                .iter()
                .enumerate()
                .all(|(offset, &address)| {
                    address as usize == block as usize * BLOCK_BYTES + offset
                });
        let extra_reads_match = if final_block && computed != 0 {
            invocation.program_reads.get(BLOCK_BYTES..) == Some(&[CONTROL_BYTE][..])
        } else {
            invocation.program_reads.len() == BLOCK_BYTES
        };
        let state_matches = counter_before == block as u16
            && result.counter == if final_block { 0 } else { block as u16 + 1 }
            && result.accumulated_byte == if final_block { 0 } else { computed };
        let exit_matches = if !final_block || computed == 0 {
            result.stop_pc == ORDINARY_EXIT && result.status_byte == 0
        } else {
            (result.stop_pc == FAILURE_EXIT && result.status_byte == 0x48)
                || (result.stop_pc == ORDINARY_EXIT && result.status_byte == 0)
        };
        if !scan_reads_match || !extra_reads_match || !state_matches || !exit_matches {
            result.status = 2;
            result.error = Some("native checksum state/read/completion contract mismatch".into());
            break;
        }
        if final_block {
            result.completed = true;
            result.residue = computed as i32;
            result.decision = if computed == 0 {
                "ResidueZero"
            } else if result.stop_pc == FAILURE_EXIT {
                "NonzeroResidueFailure"
            } else {
                "NonzeroResidueBypassed"
            };
        }
    }
    result.coverage_ranges = coverage(&seen);
    if result.status == 0 && !result.completed {
        result.status = 3;
        result.error =
            Some("incremental checksum invocation budget exhausted before full completion".into());
    }
    if let Some(fault) = bus.take_fault() {
        result.status = 2;
        result.completed = false;
        result.decision = "NotCompleted";
        result.residue = -1;
        result.error = Some(fault.to_string());
    }
    result
}

pub fn run_batch(request: &Request, mut response: Response) -> Result<Response, String> {
    response.entry_contracts = vec![entry_contract()];
    let mut cases = vec![];
    for (index, image) in request.images.iter().enumerate() {
        for &pattern in &request.scratch_patterns {
            cases.push(execute(
                &image.rom,
                index,
                pattern,
                INVOCATIONS,
                INSTRUCTION_BUDGET,
            ));
        }
    }
    response.checksum_cases = Some(cases);
    Ok(response)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ordered_compression_preserves_repeated_control_reads_and_holes() {
        assert_eq!(compress(&[2, 3, 4, 3, 4, 8]), vec![[2, 3], [3, 2], [8, 1]]);
        assert_eq!(
            coverage(&[false, true, true, false, true]),
            vec![[1, 3], [4, 5]]
        );
    }

    #[test]
    fn empty_invocation_budget_does_not_claim_a_zero_residue_pass() {
        let result = execute(&vec![0; ROM_SIZE], 0, 85, 0, 256);
        assert!(!result.completed);
        assert_eq!(result.status, 3);
        assert_eq!(result.residue, -1);
        assert_eq!(result.invocations, 0);
        assert!(result.coverage_ranges.is_empty());
    }

    #[test]
    fn synthetic_early_jump_to_success_is_not_full_checksum_completion() {
        let mut program = vec![0; ROM_SIZE];
        // Independent three-byte toy: go straight to the declared ordinary
        // exit. It must fail coverage/state, never pass because it returned.
        program[ENTRY as usize..ENTRY as usize + 3].copy_from_slice(&[3, 0xB6, 0x2B]);
        let result = execute(&program, 0, 0, 512, 256);
        assert_eq!(result.status, 2);
        assert!(!result.completed);
        assert_eq!(result.invocations, 1);
        assert_eq!(result.program_read_count, 0);
    }

    #[test]
    fn partial_instruction_budget_and_read_log_exhaustion_never_report_completion() {
        let mut program = vec![0; ROM_SIZE];
        program[ENTRY as usize..ENTRY as usize + 2].copy_from_slice(&[0x91, 0x15]);
        let partial = execute(&program, 0, 0, 512, 1);
        assert_eq!((partial.status, partial.steps, partial.residue), (3, 1, -1));
        assert!(!partial.completed);
        assert!(partial.checkpoints.is_empty());
        // Independent looping toy reads one address repeatedly. The log cap
        // must fault rather than silently deduplicate or truncate a success.
        program[ENTRY as usize..ENTRY as usize + 5].copy_from_slice(&[0x90, 0xA8, 3, 0x70, 0x2B]);
        let repeated = execute(&program, 0, 0, 512, 256);
        assert_eq!(repeated.status, 2);
        assert!(!repeated.completed);
        assert_eq!(repeated.program_read_count, 65);
        assert!(repeated.error.unwrap().contains("read-log-limit"));
    }

    #[test]
    fn invented_incremental_program_preserves_state_through_511_and_512_reentries() {
        // This unrelated 15-byte toy repeatedly reads a single constant word,
        // updates banked r0 and increments a RAM word. It is not the native
        // scan, decision procedure, address layout, or native validity proof.
        let mut rom = vec![0; 64];
        rom[..15].copy_from_slice(&[
            0x90, 0xA8, 0xC5, 7, 0x82, 0x20, 0x81, 0x78, 0xD1, 0xA0, 3, 0xB1, 0xA2, 3, 0x16,
        ]);
        rom[32..34].copy_from_slice(&[1, 2]);
        let toy = SliceContract {
            entry_pc: 0,
            exit_pcs: vec![15],
            code_ranges: vec![[0, 15]],
            psw: 0x100,
            lrb: 0x41,
            usp: 0x180,
            instruction_budget: 16,
            data_seeds: vec![
                [0x80, 32],
                [0x81, 0],
                [0x82, 0],
                [0x83, 0],
                [0x208, 5],
                [0x3A0, 0],
                [0x3A2, 0],
                [0x3A3, 0],
            ],
            output_addresses: vec![0x208, 0x3A0, 0x3A2, 0x3A3],
            program_read_range: Some([32, 34]),
        };
        for pattern in [0, 85, 170] {
            let (mut cpu, mut bus) = seed_machine(&rom, &toy, pattern);
            for call in 1..=511 {
                let result = reenter(&mut cpu, &mut bus, &toy);
                assert_eq!(result.status, 0);
                assert_eq!(result.program_reads, [32, 33]);
                assert_eq!(read_data_u16(&cpu, &mut bus, 0x3A2), call);
            }
            // A complete native pass requires 512 completed invocations;
            // 511 is explicitly incomplete even if a residue happens zero.
            assert_ne!(read_data_u16(&cpu, &mut bus, 0x3A2), INVOCATIONS as u16);
            assert_eq!(read_data_u8(&cpu, &mut bus, 0x208), 2);
            let final_call = reenter(&mut cpu, &mut bus, &toy);
            assert_eq!(final_call.status, 0);
            assert_eq!(final_call.outputs, [5, 5, 0, 2]);
            assert_eq!(read_data_u16(&cpu, &mut bus, 0x3A2), 512);
        }
    }
}
