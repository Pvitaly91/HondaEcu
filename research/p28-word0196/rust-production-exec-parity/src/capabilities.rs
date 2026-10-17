//! Exactly two hardcoded, separately counted, intentionally failing steps.
//! Neither case accepts executable input or constitutes positive parity.
use crate::{
    admission::admit,
    execution::{observation_capabilities, ObservationCapabilities, ProductionError},
    state::{ram_snapshot, seed_cpu, seed_data, snapshot, CpuRecord},
    ProductionProbeRequest, Result, RuntimeTotals, RAM_END, RAM_START, SCRATCH,
};
use p28_research_synthetic_adapter::{entry::SyntheticCpuEntrySnapshot, program::fixture, sha256};
use p28_slice_runner::{bus::Bus, exec};
use serde::Serialize;

#[derive(Debug, Clone, Serialize)]
pub struct PublicPeek {
    pub address: usize,
    pub value: Option<u8>,
    pub phase: &'static str,
    pub observation: &'static str,
}

#[derive(Debug, Clone, Serialize)]
pub struct CapabilityProgram {
    pub identity: &'static str,
    pub zero_based_rom_length: usize,
    pub content_sha256: String,
    pub prefix_padding_bytes: usize,
    pub is_m2bj_composite: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct CapabilityObservation {
    pub kind: &'static str,
    pub capability_id: &'static str,
    pub classification: &'static str,
    pub positive_parity_case: bool,
    pub before: SyntheticCpuEntrySnapshot,
    pub after: SyntheticCpuEntrySnapshot,
    pub before_ram: Vec<u8>,
    pub after_ram: Vec<u8>,
    pub ram_range: [u16; 2],
    pub cpu_before: CpuRecord,
    pub cpu_after: CpuRecord,
    pub program: CapabilityProgram,
    pub public_peeks: Vec<PublicPeek>,
    pub error: Option<ProductionError>,
    pub step_calls: u64,
    pub successful_step_calls: u64,
    pub failed_step_calls: u64,
    pub cpu_instances: u64,
    pub bus_instances: u64,
    pub instruction_counter_delta: u64,
    pub successful_instruction_retirements: u64,
    pub production_program_data_reads: Vec<u16>,
    pub observation_capabilities: ObservationCapabilities,
    pub actual_decoder_returned: bool,
    pub atomic_refusal_claimed: bool,
    pub production_bus_composite_integration: &'static str,
    pub production_composite_executions: u64,
    pub original_rom_executions: u64,
    pub firmware_ready: bool,
}

pub fn observe(
    template: &ProductionProbeRequest,
    totals: &mut RuntimeTotals,
) -> Result<Vec<CapabilityObservation>> {
    // A fully admissible frozen seed snapshot, not arbitrary CPU/ROM inputs.
    admit(template)?;
    let mut records = Vec::new();
    for mapping in [true, false] {
        let mut entry = template.entry.clone();
        // Fixed reviewed capability entry: common M2bm scalar context.
        entry.pc = if mapping { 0x1000 } else { 0 };
        entry.a = 0xa581;
        entry.al = 0x81;
        entry.ah = 0xa5;
        entry.psw = if mapping { 0xeccb } else { 0xfccb };
        entry.cf = true;
        entry.zf = true;
        entry.hc = true;
        entry.dd = !mapping;
        entry.other_psw = 0x0ccb;
        entry.scb = 3;
        entry.lrb = if mapping { 0x21 } else { 0 };
        entry.ssp = 0x37a1;
        entry.halted = false;
        let mut cpu = seed_cpu(&entry, entry.pc, false);
        totals.capability_cpu_instances += 1;
        let content = if mapping {
            // Invented opaque data canaries. Never M2bj bytes, never padding.
            vec![SCRATCH; 51]
        } else {
            let mut bytes = fixture("lb-page-zero-dd1")
                .expect("frozen literal fixture")
                .1
                .to_vec();
            for n in 0..(6 - bytes.len()) {
                bytes.push(if n % 2 == 0 { 0xa5 } else { 0x5a });
            }
            bytes
        };
        let program = CapabilityProgram {
            identity: if mapping {
                "InventedOpaqueCanary51_NotM2bj"
            } else {
                "M2bmFrozenLbPage_F417_GuardsA55AA55A"
            },
            zero_based_rom_length: content.len(),
            content_sha256: sha256::digest(&content),
            prefix_padding_bytes: 0,
            is_m2bj_composite: false,
        };
        let mut bus = Bus::new(content, SCRATCH);
        totals.capability_bus_instances += 1;
        seed_data(&mut bus, template)?;
        let public_peeks = if mapping {
            [0, 50, 51, 0x1000]
                .into_iter()
                .map(|address| PublicPeek {
                    address,
                    value: bus.peek_code_u8(address),
                    phase: "ExplicitPublicInspectionBeforeStep",
                    observation: "NotProductionDecoderCallback",
                })
                .collect()
        } else {
            Vec::new()
        };
        let before_ram = ram_snapshot(&mut bus)?;
        let before = snapshot(&entry, &cpu, &mut bus, &before_ram)?;
        let cpu_before = CpuRecord::from(&cpu);
        totals.capability_cases += 1;
        totals.capability_step_calls += 1;
        // One actual attempted production step. Mapping fails before counters;
        // the LRB0 DATA fault may leave partial architectural changes.
        let actual = exec::step(&mut cpu, &mut bus);
        let succeeded = actual.is_ok();
        totals.capability_successful_step_calls += u64::from(succeeded);
        totals.capability_failed_step_calls += u64::from(!succeeded);
        let delta = cpu.instructions - cpu_before.instructions;
        totals.capability_instruction_counter_delta += delta;
        let after_ram = ram_snapshot(&mut bus)?;
        let after = snapshot(&entry, &cpu, &mut bus, &after_ram)?;
        records.push(CapabilityObservation {
            kind: "capability_observation",
            capability_id: if mapping {
                "zero-based-program-mapping"
            } else {
                "non-atomic-data-error"
            },
            classification: if mapping {
                "SyntheticProgramMappingCapabilityNotEstablished"
            } else {
                "ProductionErrorStateObserved_NotAtomicRefusal"
            },
            positive_parity_case: false,
            before,
            after,
            before_ram,
            after_ram,
            ram_range: [RAM_START, RAM_END],
            cpu_before,
            cpu_after: CpuRecord::from(&cpu),
            program,
            public_peeks,
            error: actual.as_ref().err().map(ProductionError::from),
            step_calls: 1,
            successful_step_calls: u64::from(succeeded),
            failed_step_calls: u64::from(!succeeded),
            cpu_instances: 1,
            bus_instances: 1,
            instruction_counter_delta: delta,
            successful_instruction_retirements: u64::from(succeeded),
            production_program_data_reads: bus.program_reads(),
            observation_capabilities: observation_capabilities(),
            actual_decoder_returned: succeeded,
            atomic_refusal_claimed: false,
            production_bus_composite_integration: "NotEstablished",
            production_composite_executions: 0,
            original_rom_executions: 0,
            firmware_ready: false,
        });
    }
    Ok(records)
}
