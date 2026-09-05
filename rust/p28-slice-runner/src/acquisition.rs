//! Frozen peripheral observations and explicitly scheduled, same-state slices.
//! There is no acquisition formula here: every write/output comes from step().
use crate::bus::{Bus, CaptureObservation};
use crate::cpu::Cpu;
use crate::exec::{read_data_u16, read_data_u8, write_data_u16, write_data_u8};
use crate::instruction_forms::{acquisition_form_admission, producer_form_admission};
use crate::protocol::{CaseResult, Request, Response, TraceEntry};
use crate::runner::{
    compact_contract, execute_in_state_observed, seed_machine, threshold_contract, SliceContract,
};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct PersistentState {
    pub previous_timestamp: u16,
    pub samples: [u16; 6],
    pub data0128: u8,
    #[serde(rename = "data00AE")]
    pub data00ae: u8,
    #[serde(rename = "data00B6")]
    pub data00b6: u8,
    #[serde(rename = "data011F")]
    pub data011f: u8,
    pub previous_t: u16,
    pub data0217: u8,
    pub data0231: u8,
    pub data0136: u16,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Observation {
    pub index: u32,
    pub tmr2: u16,
    pub irqh: u8,
    pub tcon2: u8,
    pub slot: u8,
    pub compose: bool,
    pub threshold_context: u8,
    pub threshold_prior_bits: u8,
    pub threshold_enabled: bool,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct SequenceRequest {
    pub format_version: u32,
    pub composition: String,
    pub initial_state: PersistentState,
    pub observations: Vec<Observation>,
    pub trace_observation_indexes: Vec<u32>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct AcquisitionResult {
    pub status: i32,
    pub disposition: &'static str,
    pub steps: u32,
    pub stop_pc: u16,
    /// [address, width in bits, 0 read / 1 write, observed value].
    pub peripheral_accesses: Vec<[u32; 4]>,
    /// Native stores, not a before/after diff. Same-value stores are retained.
    pub sample_writes: Vec<[u32; 3]>,
    pub state_after: PersistentState,
    pub program_reads: Vec<u16>,
    pub used_assumptions: Vec<String>,
    pub executed_instruction_bytes: Vec<u16>,
    pub trace: Vec<TraceEntry>,
    pub error: Option<String>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Checkpoint {
    pub observation_index: u32,
    pub selected_timestamp: Option<u16>,
    pub slot_index: Option<u8>,
    pub acquisition: AcquisitionResult,
    pub g: Option<CaseResult>,
    pub f: Option<CaseResult>,
    pub threshold: Option<CaseResult>,
    pub state_after_composition: PersistentState,
    pub cumulative_assumptions: Vec<String>,
    pub ever_written_mask: u8,
    pub slot_write_counts: [u32; 6],
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SequenceResult {
    pub image_index: usize,
    pub scratch_pattern: u8,
    pub stop_observation_index: i32,
    pub completed_observations: u32,
    pub remaining_not_run: u32,
    pub checkpoints: Vec<Checkpoint>,
}

pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![
        serde_json::json!({"id":"acquisition","entryPc":0x56BE,"exitPcs":[0x5719],
            "stop":"BeforeInstruction","allowedCodeRanges":[[0x56BE,0x56DF],[0x5701,0x5719]],
            "psw":0x1102,"lrb":0x21,"usp":0x280,"ssp":0x7FE,"instructionBudget":128,
            "sspQualification":"TechnicalSeedUnusedBySliceNotRecoveredCallerStack",
            "mode":"DATA011F.2ClearOnly","unsupportedMode":"RefuseBeforeFetch",
            "peripheralReads":[[0x3A,16],[0x19,8],[0x42,8]],"peripheralWrites":[],
            "readEffects":"NondestructiveFrozenSnapshotNoNewEventNoInterrupt",
            "programDataReads":[],"admission":"ExactInstructionForms",
            "sampleAddresses":[0x360,0x362,0x364,0x366,0x368,0x36A],
            "slotIndex":"ExplicitCallerInputDATA00A2","selectedTimestampAddress":0x10E,
            "independentData010FStimulus":false,"stateReset":"OncePerImageAndScratchSequence",
            "callEntryReset":["PC","PSW","LRB","USP","DATA00A2"],
            "sampleWriteJournal":"ActualArchitecturalStoresIncludingSameValue",
            "instructionExtents":"AdmittedExecutedInstructionsOnly",
            "interrupts":"NotInjected","timeAdvancement":"None"}),
        serde_json::json!({"id":"acquisitionToProducer","composition":"ScheduledSameCpuRam",
            "entryPc":0x0772,"exitPcs":[0x07A5],"allowedCodeRanges":[[0x0772,0x07A5],[0x7AEC,0x7AFE]],
            "psw":0x1101,"lrb":0x40,"usp":0x180,"instructionBudget":192,
            "callEntryReset":["PC","PSW","LRB","USP"],"sampleAndHistoryReseeding":false,
            "peripheralObservations":"Unavailable","allowedAssumptions":["oki.add-er1-a"],
            "interrupts":"NotInjected"}),
        serde_json::json!({"id":"sequenceProducerToCompact","composition":"ScheduledSameCpuRam",
            "fromPc":0x07A5,"entryPc":0x07C7,"exitPcs":[0x0822],"allowedCodeRanges":[[0x07C7,0x0822]],
            "psw":0x1101,"lrb":0x40,"usp":0x180,"instructionBudget":128,
            "callEntryReset":["PC","PSW","LRB","USP"],"skippedRange":[0x07A5,0x07C7],
            "continuousWholeRoutine":false,"inputs":"ActualGState",
            "peripheralObservations":"Unavailable","allowedAssumptions":["oki.add-er3-a"]}),
        serde_json::json!({"id":"sequenceThreshold","composition":"ScheduledSameCpuRam",
            "entryPc":0x122C,"exitPcs":[0x126D,0x1281],"allowedCodeRanges":[[0x122C,0x126D]],
            "psw":0x0101,"lrb":0x20,"usp":0x280,"instructionBudget":128,
            "callEntryReset":["PC","PSW","LRB","USP","DATA011E.3/.4","DATA0131.1/.2"],
            "initialOnlyPreconditions":{"DATA00CC":0,"DATA0131bit0":0},
            "laterThresholdCalls":"PreservePrefixSideEffectsAndUnrelatedBits",
            "codeInput":"ActualFStateDATA0133","allowedProgramDataReads":[0x6542,0x654A],
            "allowedAssumptions":[],"peripheralObservations":"Unavailable",
            "contextSchedule":"HarnessDeclaredNotMeasuredMainLoopOrHysteresis",
            "assumptions":"CumulativeAcrossStagesAndObservations","failure":"AbortRemainingSequence"}),
    ]
}

pub fn validate_request(request: &Request) -> Result<(), String> {
    let sequence = request
        .acquisition_sequence
        .as_ref()
        .ok_or("acquisition sequence required")?;
    if request.synthetic.is_some()
        || request.producer_cases.is_some()
        || request.scratch_patterns != [0, 85, 170]
        || request.images[0].id != "baseline"
        || request.images.iter().any(|image| image.rom.len() != 32768)
        || request
            .images
            .get(1)
            .is_some_and(|image| image.id != "derived")
        || sequence.format_version != 1
        || !["acquisition-only", "scheduled-g-f-threshold"].contains(&sequence.composition.as_str())
        || sequence.observations.is_empty()
        || sequence.observations.len() > 1024
        || sequence.trace_observation_indexes.len() > 8
    {
        return Err("invalid fixed acquisition sequence contract".into());
    }
    if sequence
        .observations
        .iter()
        .enumerate()
        .any(|(index, observation)| {
            observation.index as usize != index
                || observation.slot > 5
                || observation.threshold_context > 1
                || observation.threshold_prior_bits > 3
                || (sequence.composition == "acquisition-only" && observation.compose)
        })
    {
        return Err("invalid or non-contiguous acquisition observations".into());
    }
    let traces: std::collections::HashSet<_> = sequence.trace_observation_indexes.iter().collect();
    if traces.len() != sequence.trace_observation_indexes.len()
        || traces
            .iter()
            .any(|index| **index as usize >= sequence.observations.len())
    {
        return Err("invalid acquisition trace witness indexes".into());
    }
    Ok(())
}

fn acquisition_contract() -> SliceContract {
    SliceContract {
        entry_pc: 0x56BE,
        exit_pcs: vec![0x5719],
        code_ranges: vec![[0x56BE, 0x56DF], [0x5701, 0x5719]],
        psw: 0x1102,
        lrb: 0x21,
        usp: 0x280,
        instruction_budget: 128,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: Some([0, 0]),
    }
}

fn seed_state(cpu: &mut Cpu, bus: &mut Bus, state: &PersistentState) {
    for (address, value) in [
        (0xEE, state.previous_timestamp),
        (0xC4, state.previous_t),
        (0x136, state.data0136),
    ] {
        write_data_u16(cpu, bus, address, value);
    }
    for (index, value) in state.samples.iter().enumerate() {
        write_data_u16(cpu, bus, 0x360 + index as u16 * 2, *value);
    }
    for (address, value) in [
        (0x128, state.data0128),
        (0xAE, state.data00ae),
        (0xB6, state.data00b6),
        (0x11F, state.data011f),
        (0x217, state.data0217),
        (0x231, state.data0231),
    ] {
        write_data_u8(cpu, bus, address, value);
    }
    // Existing threshold prefix preconditions, seeded once. These are not
    // observations of a complete ECU main loop or persistent hysteresis.
    write_data_u8(cpu, bus, 0xCC, 0);
    let prior = read_data_u8(cpu, bus, 0x131);
    write_data_u8(cpu, bus, 0x131, prior & !1);
}

fn snapshot(cpu: &Cpu, bus: &mut Bus) -> PersistentState {
    PersistentState {
        previous_timestamp: read_data_u16(cpu, bus, 0xEE),
        samples: std::array::from_fn(|index| read_data_u16(cpu, bus, 0x360 + index as u16 * 2)),
        data0128: read_data_u8(cpu, bus, 0x128),
        data00ae: read_data_u8(cpu, bus, 0xAE),
        data00b6: read_data_u8(cpu, bus, 0xB6),
        data011f: read_data_u8(cpu, bus, 0x11F),
        previous_t: read_data_u16(cpu, bus, 0xC4),
        data0217: read_data_u8(cpu, bus, 0x217),
        data0231: read_data_u8(cpu, bus, 0x231),
        data0136: read_data_u16(cpu, bus, 0x136),
    }
}

fn enter(cpu: &mut Cpu, bus: &mut Bus, contract: &SliceContract) {
    cpu.pc = contract.entry_pc;
    write_data_u16(cpu, bus, 2, contract.lrb);
    write_data_u16(cpu, bus, 4, contract.psw);
    write_data_u16(cpu, bus, 0x80 + cpu.scb() * 8 + 6, contract.usp);
    bus.clear_program_reads();
}

fn retain_assumptions(cumulative: &mut Vec<String>, result: &CaseResult) {
    for assumption in &result.used_assumptions {
        if !cumulative.contains(assumption) {
            cumulative.push(assumption.clone());
        }
    }
}

fn not_run(
    index: u32,
    state: &PersistentState,
    stop_pc: u16,
    unsupported: bool,
    cumulative: &[String],
    mask: u8,
    counts: [u32; 6],
) -> Checkpoint {
    Checkpoint {
        observation_index: index,
        selected_timestamp: None,
        slot_index: None,
        acquisition: AcquisitionResult {
            status: 4,
            disposition: if unsupported {
                "UnsupportedMode"
            } else {
                "NotRun"
            },
            steps: 0,
            stop_pc,
            peripheral_accesses: vec![],
            sample_writes: vec![],
            state_after: state.clone(),
            program_reads: vec![],
            used_assumptions: vec![],
            executed_instruction_bytes: vec![],
            trace: vec![],
            error: if unsupported {
                Some("DATA011F.2 alternate acquisition mode is not admitted".into())
            } else {
                None
            },
        },
        g: None,
        f: None,
        threshold: None,
        state_after_composition: state.clone(),
        cumulative_assumptions: cumulative.to_vec(),
        ever_written_mask: mask,
        slot_write_counts: counts,
    }
}

fn execute_sequence(
    rom: &[u8],
    image_index: usize,
    pattern: u8,
    sequence: &SequenceRequest,
    assumptions: &[&str],
    extra_trace: Option<u32>,
) -> SequenceResult {
    let contract = acquisition_contract();
    let (mut cpu, mut bus) = seed_machine(rom, &contract, pattern);
    seed_state(&mut cpu, &mut bus, &sequence.initial_state);
    let mut state = sequence.initial_state.clone();
    let mut result = SequenceResult {
        image_index,
        scratch_pattern: pattern,
        stop_observation_index: -1,
        completed_observations: 0,
        remaining_not_run: 0,
        checkpoints: Vec::with_capacity(sequence.observations.len()),
    };
    let mut cumulative = vec![];
    let mut mask = 0u8;
    let mut counts = [0u32; 6];
    for observation in &sequence.observations {
        if result.stop_observation_index >= 0 {
            result.checkpoints.push(not_run(
                observation.index,
                &state,
                cpu.pc,
                false,
                &cumulative,
                mask,
                counts,
            ));
            result.remaining_not_run += 1;
            continue;
        }
        if state.data011f & 4 != 0 {
            result.stop_observation_index = observation.index as i32;
            cpu.pc = contract.entry_pc;
            result.checkpoints.push(not_run(
                observation.index,
                &state,
                cpu.pc,
                true,
                &cumulative,
                mask,
                counts,
            ));
            continue;
        }
        let selected = sequence
            .trace_observation_indexes
            .contains(&observation.index)
            || extra_trace == Some(observation.index);
        enter(&mut cpu, &mut bus, &contract);
        write_data_u8(&mut cpu, &mut bus, 0xA2, observation.slot);
        bus.observe_capture(Some(CaptureObservation {
            tmr2: observation.tmr2,
            irqh: observation.irqh,
            tcon2: observation.tcon2,
        }));
        bus.begin_write_journal();
        let mut acquisition = execute_in_state_observed(
            &mut cpu,
            &mut bus,
            &contract,
            &[],
            selected,
            Some(acquisition_form_admission),
            true,
        );
        let writes: Vec<_> = bus
            .end_write_journal()
            .into_iter()
            .filter(|write| write[0] < 0x36C && write[0] + write[1] / 8 > 0x360)
            .collect();
        let peripherals = bus.peripheral_accesses();
        bus.observe_capture(None);
        // Never promote unexpected partial/byte stores to a fresh sample word.
        for write in &writes {
            if write[1] != 16 || write[0] & 1 != 0 || !(0x360..0x36C).contains(&write[0]) {
                acquisition.status = 2;
                acquisition.error = Some("unexpected sample store width or alignment".into());
            } else {
                let slot = ((write[0] - 0x360) / 2) as usize;
                counts[slot] += 1;
                mask |= 1 << slot;
            }
        }
        let disposition = match acquisition.status {
            0 if state.data0128 & 8 == 0 => "FirstObservationNoWrite",
            0 if writes.iter().any(|write| write[1] == 16 && write[2] == 0) => "InvalidZeroWrite",
            0 => "IntervalWrite",
            1 => "UnresolvedInstruction",
            3 => "BudgetExceeded",
            _ => "ExecutionError",
        };
        let selected_timestamp = read_data_u16(&cpu, &mut bus, 0x10E);
        let slot_index = read_data_u8(&cpu, &mut bus, 0xA2);
        state = snapshot(&cpu, &mut bus);
        let mut checkpoint = Checkpoint {
            observation_index: observation.index,
            selected_timestamp: Some(selected_timestamp),
            slot_index: Some(slot_index),
            acquisition: AcquisitionResult {
                status: acquisition.status,
                disposition,
                steps: acquisition.steps,
                stop_pc: acquisition.stop_pc,
                peripheral_accesses: peripherals,
                sample_writes: writes,
                state_after: state.clone(),
                program_reads: acquisition.program_reads,
                used_assumptions: acquisition.used_assumptions,
                executed_instruction_bytes: acquisition
                    .executed_instruction_bytes
                    .unwrap_or_default(),
                trace: acquisition.trace,
                error: acquisition.error,
            },
            g: None,
            f: None,
            threshold: None,
            state_after_composition: state.clone(),
            cumulative_assumptions: cumulative.clone(),
            ever_written_mask: mask,
            slot_write_counts: counts,
        };
        let mut completed = checkpoint.acquisition.status == 0;
        if completed && observation.compose {
            let g_contract = crate::producer::producer_contract(&[0; 14]);
            enter(&mut cpu, &mut bus, &g_contract);
            let g = execute_in_state_observed(
                &mut cpu,
                &mut bus,
                &g_contract,
                assumptions,
                selected,
                Some(producer_form_admission),
                true,
            );
            retain_assumptions(&mut cumulative, &g);
            completed = g.status == 0;
            checkpoint.g = Some(g);
            if completed {
                let f_contract = compact_contract(0, false);
                enter(&mut cpu, &mut bus, &f_contract);
                let f_permissions: Vec<_> = assumptions
                    .iter()
                    .copied()
                    .filter(|id| *id == crate::protocol::ADD_ASSUMPTION)
                    .collect();
                let f = execute_in_state_observed(
                    &mut cpu,
                    &mut bus,
                    &f_contract,
                    &f_permissions,
                    selected,
                    None,
                    true,
                );
                retain_assumptions(&mut cumulative, &f);
                completed = f.status == 0;
                checkpoint.f = Some(f);
            }
            if completed {
                let threshold = threshold_contract(
                    0,
                    observation.threshold_context,
                    observation.threshold_prior_bits,
                    observation.threshold_enabled,
                );
                enter(&mut cpu, &mut bus, &threshold);
                let flags = read_data_u8(&cpu, &mut bus, 0x11E);
                let context = if observation.threshold_context == 0 {
                    8
                } else {
                    0
                };
                write_data_u8(
                    &mut cpu,
                    &mut bus,
                    0x11E,
                    (flags & !24) | context | if observation.threshold_enabled { 16 } else { 0 },
                );
                let flags = read_data_u8(&cpu, &mut bus, 0x131);
                write_data_u8(
                    &mut cpu,
                    &mut bus,
                    0x131,
                    (flags & !6) | (observation.threshold_prior_bits << 1),
                );
                let threshold_result = execute_in_state_observed(
                    &mut cpu,
                    &mut bus,
                    &threshold,
                    &[],
                    selected,
                    None,
                    true,
                );
                completed = threshold_result.status == 0;
                checkpoint.threshold = Some(threshold_result);
            }
            state = snapshot(&cpu, &mut bus);
        }
        checkpoint.state_after_composition = state.clone();
        checkpoint.cumulative_assumptions = cumulative.clone();
        if completed {
            result.completed_observations += 1;
        } else {
            result.stop_observation_index = observation.index as i32;
        }
        result.checkpoints.push(checkpoint);
    }
    result
}

pub fn run_sequence_request(request: &Request, mut response: Response) -> Result<Response, String> {
    let sequence = request
        .acquisition_sequence
        .as_ref()
        .ok_or("acquisition sequence required")?;
    let assumptions: Vec<_> = request
        .allow_assumptions
        .iter()
        .map(String::as_str)
        .collect();
    response.entry_contracts = entry_contracts();
    let mut sequences = vec![];
    for (image_index, image) in request.images.iter().enumerate() {
        for &pattern in &request.scratch_patterns {
            let mut result = execute_sequence(
                &image.rom,
                image_index,
                pattern,
                sequence,
                &assumptions,
                None,
            );
            if result.stop_observation_index >= 0 {
                let index = result.stop_observation_index as u32;
                // Replay the identical initial state and entire preceding
                // schedule, never seed a failing case from the observed state.
                if !sequence.trace_observation_indexes.contains(&index)
                    && result.checkpoints[index as usize].acquisition.disposition
                        != "UnsupportedMode"
                {
                    result = execute_sequence(
                        &image.rom,
                        image_index,
                        pattern,
                        sequence,
                        &assumptions,
                        Some(index),
                    );
                }
            }
            sequences.push(result);
        }
    }
    response.acquisition_sequences = Some(sequences);
    Ok(response)
}
