//! One Cpu, one DATA initialization, one functional phase, one lifecycle.
use crate::{
    effects::execute_one,
    lifecycle::{Lifecycle, Retirement},
    observer::{ProgramEvent, ProgramObserver},
    program::VerifiedComposite,
    AdapterError, Result, HARD_BUDGET, SCOPE,
};
use p28_research_synthetic_adapter::{
    data::{
        AuxiliaryDataEvent, DataEvent, DataPath, IndependentDataAccessPolicy, RawDataEvent,
        INVENTORY,
    },
    entry::SyntheticCpuEntrySnapshot,
    executor::DecodeObservation,
    psw::CanonicalPswBridge,
    sha256,
    source::verify_source_bindings,
    FormId,
};
use p28_slice_runner::cpu::Cpu;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CaseRequest {
    pub kind: String,
    pub case_id: String,
    pub family: String,
    pub entry: SyntheticCpuEntrySnapshot,
    pub data: BTreeMap<u16, u8>,
    pub path: DataPath,
    pub internal_sf: bool,
    pub budget: u8,
}

/// Pre-execution only: no Cpu, PROGRAM observer or functional DATA phase exists.
pub fn admit_case(request: &CaseRequest) -> Result<DataPath> {
    if request.kind != "case"
        || request.case_id.is_empty()
        || request.case_id.len() > 96
        || !request.case_id.is_ascii()
        || request.family.is_empty()
        || request.family.len() > 96
    {
        return Err(AdapterError::new(
            "InvalidCaseIdentity",
            "closed invented case request",
        ));
    }
    if request.budget == 0 || request.budget > HARD_BUDGET {
        return Err(AdapterError::new(
            "InvalidExecutionBudgetOrEntry",
            "budget1..16 only",
        ));
    }
    request.entry.validate(&request.data)?;
    // Pure seed-shape validation: no DATA policy object or initialization exists
    // at admission. The real execution constructs and initializes DATA once.
    if request.data.len() != INVENTORY.len()
        || INVENTORY.iter().any(|a| !request.data.contains_key(a))
    {
        return Err(AdapterError::new(
            "IncompleteDataInventory",
            "exact sixteen explicit invented bytes required",
        ));
    }
    let word = u16::from_le_bytes([request.data[&0x196], request.data[&0x197]]);
    let path = if word < 0xc0 {
        DataPath::A
    } else if request.data[&0x12a] & 0x80 != 0 {
        DataPath::B
    } else if request.data[&0x124] & 0x20 != 0 {
        DataPath::C
    } else {
        DataPath::D
    };
    if path != request.path {
        return Err(AdapterError::new(
            "ForgedPermissionProfile",
            "entry predicate, never caller union",
        ));
    }
    Ok(path)
}

/// Same explicit Cpu initialization as M2bm's private seed_cpu; no defaults.
fn seed_cpu(entry: &SyntheticCpuEntrySnapshot, internal_sf: bool) -> Result<Cpu> {
    let mut cpu = Cpu {
        pc: entry.pc,
        a: entry.a,
        ssp: entry.ssp,
        lrb: entry.lrb,
        zf: entry.zf,
        cf: entry.cf,
        hc: entry.hc,
        dd: entry.dd,
        sf: internal_sf,
        psw_other: entry.other_psw,
        cycles: 0,
        instructions: 0,
        halted: entry.halted,
    };
    CanonicalPswBridge::set_checked(&mut cpu, entry.psw)?;
    Ok(cpu)
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct StepObservation {
    pub index: u32,
    pub node_identity: String,
    pub pc_before: u16,
    pub pc_after: u16,
    pub form: FormId,
    pub decode: DecodeObservation,
    pub before: SyntheticCpuEntrySnapshot,
    pub after: SyntheticCpuEntrySnapshot,
    pub branch_taken: Option<bool>,
    pub logical_start: usize,
    pub logical_end: usize,
    pub raw_start: usize,
    pub raw_end: usize,
    pub selected_extent_sha256: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CompositeObservation {
    pub kind: String,
    pub accepted: bool,
    pub case_id: String,
    pub family: String,
    pub scope: String,
    pub permission_path: DataPath,
    pub before: SyntheticCpuEntrySnapshot,
    pub after: SyntheticCpuEntrySnapshot,
    pub before_data: BTreeMap<u16, u8>,
    pub after_data: BTreeMap<u16, u8>,
    pub steps: Vec<StepObservation>,
    pub program_events: Vec<ProgramEvent>,
    pub data_journal: Vec<DataEvent>,
    pub raw_data_journal: Vec<RawDataEvent>,
    pub seed_journal: Vec<AuxiliaryDataEvent>,
    pub diagnostic_journal: Vec<AuxiliaryDataEvent>,
    pub retirements: Vec<Retirement>,
    pub retired_instructions: u32,
    pub cpu_instances: u32,
    pub direct_j_count: u32,
    pub external_transfer: Option<u16>,
    pub program_sealed: bool,
    pub lifecycle_sealed: bool,
    pub internal_sf_before: bool,
    pub internal_sf_after: bool,
    pub cycles: u64,
    pub instructions: u64,
    pub composite_executions: u32,
    pub production_exec_integrated: bool,
    pub original_rom_executions: u32,
    pub error: Option<AdapterError>,
}

pub fn execute_composite(
    program: &VerifiedComposite,
    request: &CaseRequest,
) -> Result<CompositeObservation> {
    let permission_path = admit_case(request)?;
    verify_source_bindings()?;
    program.validate_immutable()?;
    let mut lifecycle = Lifecycle::new(request.entry.pc, request.budget)?;
    let observer = ProgramObserver::new();
    let mut data = IndependentDataAccessPolicy::new(permission_path, &request.data)?;
    request.entry.seed_banks(&mut data)?;
    // This is the ONLY Cpu construction in a composite case.
    let mut cpu = seed_cpu(&request.entry, request.internal_sf)?;
    let before = request.entry.snapshot(&cpu, &mut data)?;
    let before_data = data.inventory_snapshot()?;
    let mut steps = Vec::new();
    data.begin_functional()?;
    let result = (|| -> Result<()> {
        loop {
            lifecycle.before_fetch()?;
            program.validate_immutable()?;
            // PC comes exclusively from current Cpu state, not an expected route.
            let node = program.node(cpu.pc)?;
            let before_step = request.entry.snapshot(&cpu, &mut data)?;
            let logical_start = data.journal.len();
            let raw_start = data.raw_journal.len();
            observer.begin_instruction(cpu.pc, steps.len() as u32 + 1)?;
            let decoded = observer.decode_checked(program, cpu.dd)?;
            observer.associate_selection(decoded.len)?;
            let selected = observer.selected(program, decoded.len)?;
            program.validate_selection(node, &decoded, cpu.dd, &selected)?;
            let pc_before = cpu.pc;
            let branch_taken = execute_one(&mut cpu, &mut data, node.form, &decoded)?;
            if !node.successors.contains(&cpu.pc) {
                return Err(AdapterError::new(
                    "UnknownSuccessor",
                    format!("actual {:04X}", cpu.pc),
                ));
            }
            lifecycle.retire(pc_before, cpu.pc, node.form)?;
            observer.finish_retirement(node.form == FormId::JAddress)?;
            let after_step = request.entry.snapshot(&cpu, &mut data)?;
            let fields = decoded.fields;
            steps.push(StepObservation {
                index: steps.len() as u32 + 1,
                node_identity: node.node_identity.clone(),
                pc_before,
                pc_after: cpu.pc,
                form: node.form,
                decode: DecodeObservation {
                    form: node.form,
                    mnemonic: decoded.mnemonic.into(),
                    index: decoded.index,
                    len: decoded.len,
                    dd_before: before_step.dd,
                    dd_after: cpu.dd,
                    n8: fields.n8,
                    n8_alt: fields.n8_alt,
                    n16: fields.n16,
                    addr16: fields.addr16,
                    rel8: fields.rel8,
                },
                before: before_step,
                after: after_step,
                branch_taken,
                logical_start,
                logical_end: data.journal.len(),
                raw_start,
                raw_end: data.raw_journal.len(),
                selected_extent_sha256: sha256::digest(&selected),
            });
            if let Some(terminal) = lifecycle.terminal() {
                if cpu.pc != terminal
                    || node.form != FormId::JAddress
                    || lifecycle.direct_j_count() != 1
                    || !observer.is_sealed()
                {
                    return Err(AdapterError::new(
                        "ExitIntegrityFailure",
                        "actual J retirement and both guards",
                    ));
                }
                // No next-PC decoder call or selected read is made.
                break;
            }
        }
        data.validate_journals()?;
        program.validate_immutable()?;
        Ok(())
    })();
    if let Err(error) = &result {
        lifecycle.mark_fault();
        observer.mark_fault(error.clone());
    }
    let after = request.entry.snapshot(&cpu, &mut data)?;
    let after_data = data.inventory_snapshot()?;
    Ok(CompositeObservation {
        kind: "observation".into(),
        accepted: result.is_ok(),
        case_id: request.case_id.clone(),
        family: request.family.clone(),
        scope: SCOPE.into(),
        permission_path,
        before,
        after,
        before_data,
        after_data,
        steps,
        program_events: observer.events(),
        data_journal: data.journal,
        raw_data_journal: data.raw_journal,
        seed_journal: data.seed_journal,
        diagnostic_journal: data.diagnostic_journal,
        retirements: lifecycle.retired().to_vec(),
        retired_instructions: lifecycle.retired().len() as u32,
        cpu_instances: 1,
        direct_j_count: lifecycle.direct_j_count(),
        external_transfer: lifecycle.terminal(),
        program_sealed: observer.is_sealed(),
        lifecycle_sealed: lifecycle.terminal().is_some(),
        internal_sf_before: request.internal_sf,
        internal_sf_after: cpu.sf,
        cycles: cpu.cycles,
        instructions: cpu.instructions,
        composite_executions: 1,
        production_exec_integrated: false,
        original_rom_executions: 0,
        error: result.err(),
    })
}
