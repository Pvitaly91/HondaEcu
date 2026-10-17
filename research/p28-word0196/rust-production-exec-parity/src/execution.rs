//! Production-side execution calls only the unchanged public exec::step.
use crate::{
    admission::admit,
    state::{ram_snapshot, seed_cpu, seed_data, snapshot, CpuRecord},
    ProductionProbeRequest, Result, RuntimeTotals, LOGICAL_PC, PHYSICAL_PC, RAM_END, RAM_START,
};
use p28_research_synthetic_adapter::{entry::SyntheticCpuEntrySnapshot, FormId};
use p28_slice_runner::{
    bus::Bus,
    decoder::Decoded,
    exec::{self, ExecError},
};
use serde::Serialize;

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct ProductionError {
    pub kind: &'static str,
    pub space: Option<String>,
    pub address: Option<u32>,
    pub operation: Option<String>,
    pub pc: Option<u16>,
    pub byte: Option<u8>,
    pub mnemonic: Option<String>,
}
impl From<&ExecError> for ProductionError {
    fn from(error: &ExecError) -> Self {
        let mut result = Self {
            kind: "",
            space: None,
            address: None,
            operation: None,
            pc: None,
            byte: None,
            mnemonic: None,
        };
        match error {
            ExecError::MemoryAccess(fault) => {
                result.kind = "MemoryAccess";
                result.space = Some(fault.space.into());
                result.address = Some(fault.address);
                result.operation = Some(fault.operation.into());
            }
            ExecError::UndefinedOpcode { pc, byte } => {
                result.kind = "UndefinedOpcode";
                result.pc = Some(*pc);
                result.byte = Some(*byte);
            }
            ExecError::Unimplemented { pc, mnemonic } => {
                result.kind = "Unimplemented";
                result.pc = Some(*pc);
                result.mnemonic = Some((*mnemonic).into());
            }
        }
        result
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct DecodeObservation {
    pub form: FormId,
    pub mnemonic: String,
    pub index: usize,
    pub len: usize,
    pub dd_before: bool,
    pub dd_after: bool,
    pub n8: u8,
    pub n8_alt: u8,
    pub n16: u16,
    pub n16_alt: u16,
    pub s8: i8,
    pub addr16: u16,
    pub rel8: i8,
    pub dd_after_option: Option<bool>,
    pub cycles: u16,
}
impl DecodeObservation {
    pub fn actual(form: FormId, decoded: &Decoded, dd_before: bool, dd_after: bool) -> Self {
        Self {
            form,
            mnemonic: decoded.mnemonic.into(),
            index: decoded.index,
            len: decoded.len,
            dd_before,
            dd_after,
            n8: decoded.fields.n8,
            n8_alt: decoded.fields.n8_alt,
            n16: decoded.fields.n16,
            n16_alt: decoded.fields.n16_alt,
            s8: decoded.fields.s8,
            addr16: decoded.fields.addr16,
            rel8: decoded.fields.rel8,
            dd_after_option: decoded.dd_after,
            cycles: decoded.cycles,
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct ObservationCapabilities {
    pub decoder_callbacks: &'static str,
    pub ordered_data_journal: &'static str,
    pub raw_data_journal: &'static str,
    pub same_value_write_occurrence: &'static str,
    pub program_instruction_fetch_journal: &'static str,
    pub data_final_state: &'static str,
    pub data_permissions: &'static str,
}
pub fn observation_capabilities() -> ObservationCapabilities {
    ObservationCapabilities {
        decoder_callbacks: "ObservationNotAvailable",
        ordered_data_journal: "ObservationNotAvailable",
        raw_data_journal: "ObservationNotAvailable",
        same_value_write_occurrence: "ObservationNotAvailable",
        program_instruction_fetch_journal: "ObservationNotAvailable",
        data_final_state: "ObservedByPublicDiagnosticReads",
        data_permissions: "ProductionDefaultRam_NotIndependentReadWritePolicy",
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct PcRelocation {
    pub physical_base: u16,
    pub logical_base: u16,
    pub relative_and_fallthrough: &'static str,
    pub absolute_direct_j: &'static str,
}

#[derive(Debug, Clone, Serialize)]
pub struct ProductionObservation {
    pub kind: &'static str,
    pub accepted: bool,
    pub error: Option<ProductionError>,
    pub case_id: String,
    pub fixture_id: String,
    pub family: String,
    pub form: FormId,
    pub provenance: String,
    pub scope: &'static str,
    pub before: SyntheticCpuEntrySnapshot,
    pub after: SyntheticCpuEntrySnapshot,
    pub before_ram: Vec<u8>,
    pub after_ram: Vec<u8>,
    pub ram_range: [u16; 2],
    pub cpu_before: CpuRecord,
    pub cpu_after: CpuRecord,
    pub decode: Option<DecodeObservation>,
    pub physical_entry_pc: u16,
    pub logical_entry_pc: u16,
    pub pc_relocation: PcRelocation,
    pub step_calls: u64,
    pub successful_step_calls: u64,
    pub failed_step_calls: u64,
    pub cpu_instances: u64,
    pub bus_instances: u64,
    pub internal_sf_before: bool,
    pub internal_sf_after: bool,
    pub branch_taken: Option<bool>,
    pub branch_observation: &'static str,
    pub external_transfer: Option<u16>,
    pub production_program_data_reads: Vec<u16>,
    pub observation_capabilities: ObservationCapabilities,
    pub production_exec_runtime_observed: bool,
    pub production_bus_composite_integration: &'static str,
    pub original_rom_executions: u64,
    pub production_composite_executions: u64,
    pub firmware_ready: bool,
}

pub fn execute(
    request: &ProductionProbeRequest,
    totals: &mut RuntimeTotals,
) -> Result<ProductionObservation> {
    let admitted = admit(request)?;
    let mut cpu = seed_cpu(&request.entry, PHYSICAL_PC, request.internal_sf);
    totals.positive_cpu_instances += 1;
    let mut bus = Bus::new(admitted.program, request.scratch);
    totals.positive_bus_instances += 1;
    seed_data(&mut bus, request)?;
    let before_ram = ram_snapshot(&mut bus)?;
    let before = snapshot(&request.entry, &cpu, &mut bus, &before_ram)?;
    let cpu_before = CpuRecord::from(&cpu);
    totals.positive_cases += 1;
    totals.positive_step_calls += 1;
    // The ONLY positive execution mechanism. No research effects, Exec::run
    // copy, reseeding, target-PC substitution, loop, or second step exists.
    let actual = exec::step(&mut cpu, &mut bus);
    let succeeded = actual.is_ok();
    totals.positive_successful_step_calls += u64::from(succeeded);
    totals.positive_failed_step_calls += u64::from(!succeeded);
    totals.positive_instruction_counter_delta += cpu.instructions - cpu_before.instructions;
    if let Ok(decoded) = &actual {
        *totals
            .observed_decoded_forms
            .entry(decoded.mnemonic.into())
            .or_default() += 1;
    }
    // Decoder probes and functional DATA accesses are NOT reconstructed here.
    // These diagnostics run only after the one production call has returned.
    let after_ram = ram_snapshot(&mut bus)?;
    let after = snapshot(&request.entry, &cpu, &mut bus, &after_ram)?;
    let cpu_after = CpuRecord::from(&cpu);
    let conditional = matches!(
        request.form,
        FormId::JltRel8 | FormId::JbsPageBit7 | FormId::JbsPageBit5
    );
    let branch_taken = if conditional && succeeded {
        Some(cpu.pc != PHYSICAL_PC + admitted.preflight.len as u16)
    } else {
        None
    };
    let decode = actual
        .as_ref()
        .ok()
        .map(|decoded| DecodeObservation::actual(request.form, decoded, before.dd, after.dd));
    let error = actual.as_ref().err().map(ProductionError::from);
    Ok(ProductionObservation {
        kind: "production_observation",
        accepted: succeeded,
        error,
        case_id: request.case_id.clone(),
        fixture_id: request.fixture_id.clone(),
        family: request.family.clone(),
        form: request.form,
        provenance: request.entry.provenance.clone(),
        scope: "MicroprobeScope_NotCompositePathReachability",
        before,
        after,
        before_ram,
        after_ram,
        ram_range: [RAM_START, RAM_END],
        cpu_before,
        cpu_after,
        decode,
        physical_entry_pc: PHYSICAL_PC,
        logical_entry_pc: LOGICAL_PC,
        pc_relocation: PcRelocation {
            physical_base: PHYSICAL_PC,
            logical_base: LOGICAL_PC,
            relative_and_fallthrough: "AddLogicalBase",
            absolute_direct_j: "PreserveActualAbsoluteTarget",
        },
        step_calls: 1,
        successful_step_calls: u64::from(succeeded),
        failed_step_calls: u64::from(!succeeded),
        cpu_instances: 1,
        bus_instances: 1,
        internal_sf_before: request.internal_sf,
        internal_sf_after: cpu.sf,
        branch_taken,
        branch_observation: if conditional {
            "DerivedFromObservedPc"
        } else {
            "NotApplicable"
        },
        external_transfer: if request.form == FormId::JAddress && succeeded {
            Some(cpu.pc)
        } else {
            None
        },
        production_program_data_reads: bus.program_reads(),
        observation_capabilities: observation_capabilities(),
        production_exec_runtime_observed: true,
        production_bus_composite_integration: "NotEstablished",
        original_rom_executions: 0,
        production_composite_executions: 0,
        firmware_ready: false,
    })
}
