//! Narrow independent effect implementation. Production Cpu and decoder are
//! reused unchanged; production Bus/exec::step/runner are never called.
use crate::{
    admission::FormId,
    data::{
        AuxiliaryDataEvent, DataEvent, DataPath, IndependentDataAccessPolicy, RawDataEvent,
        WriteKind,
    },
    entry::SyntheticCpuEntrySnapshot,
    exit::{RetirementEvent, SyntheticExternalExitTrap},
    fetch::{OrderedProgramFetchObserver, ProgramEvent},
    program::MicroProgram,
    source::{verify_source_bindings, SourceBinding},
    AdapterError, Result,
};
use p28_slice_runner::{
    cpu::Cpu,
    decoder::{Decoded, Fields},
};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ProbeRequest {
    pub case_id: String,
    pub form: FormId,
    pub bytes: Vec<u8>,
    pub guards: Vec<u8>,
    pub content_digest: String,
    pub entry: SyntheticCpuEntrySnapshot,
    pub data: BTreeMap<u16, u8>,
    pub path: DataPath,
    pub internal_sf: bool,
    pub budget: u8,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
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
    pub addr16: u16,
    pub rel8: i8,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MicroObservation {
    pub case_id: String,
    pub provenance: String,
    pub scope: String,
    pub before: SyntheticCpuEntrySnapshot,
    pub after: SyntheticCpuEntrySnapshot,
    pub before_data: BTreeMap<u16, u8>,
    pub after_data: BTreeMap<u16, u8>,
    pub decode: DecodeObservation,
    pub all_program_bytes: Vec<u8>,
    pub immutable_content_digest: String,
    pub selected_bytes: Vec<u8>,
    pub raw_program: Vec<ProgramEvent>,
    pub data_journal: Vec<DataEvent>,
    pub raw_data_journal: Vec<RawDataEvent>,
    pub seed_journal: Vec<AuxiliaryDataEvent>,
    pub diagnostic_journal: Vec<AuxiliaryDataEvent>,
    pub retired_instructions: u32,
    pub cpu_instances: u32,
    pub retirements: Vec<RetirementEvent>,
    pub external_transfer: Option<u16>,
    pub branch_taken: Option<bool>,
    pub internal_sf_before: bool,
    pub internal_sf_after: bool,
    pub cycles: u64,
    pub instructions: u64,
    pub source_bindings: Vec<SourceBinding>,
    pub production_exec_integrated: bool,
    pub m2bj_composite_executions: u32,
    pub original_rom_executions: u32,
    pub first_mismatch: Option<String>,
}

pub fn run_microprobe(request: &ProbeRequest) -> Result<MicroObservation> {
    request.entry.validate(&request.data)?;
    let mut trap = SyntheticExternalExitTrap::new(request.entry.pc, request.budget)?;
    if request.form.spec().dd == '0' && request.entry.dd {
        return Err(AdapterError::new(
            "WrongDdAdmission",
            "DD0-only exact form refused before runtime mutation",
        ));
    }
    let program = MicroProgram::new(
        &request.case_id,
        request.form,
        &request.bytes,
        &request.guards,
        &request.content_digest,
        &request.entry.provenance,
    )?;
    let source_bindings = verify_source_bindings()?;
    let mut data = IndependentDataAccessPolicy::new(request.path, &request.data)?;
    request.entry.seed_banks(&mut data)?;
    let mut cpu = request.entry.seed_cpu(request.internal_sf)?;
    let before = request.entry.snapshot(&cpu, &mut data)?;
    let before_data = data.inventory_snapshot()?;
    let internal_sf_before = cpu.sf;
    trap.before_fetch()?;
    let observer = OrderedProgramFetchObserver::new();
    // Actual unchanged production decoder reads actual immutable invented bytes.
    let decoded = observer.decode_checked(&program, cpu.dd)?;
    request.form.validate_decoded(&decoded, cpu.dd)?;
    observer.classify_decoder_lookahead(decoded.len)?;
    let selected_bytes = observer.read_selected(&program, decoded.len)?;
    validate_selected_fields(request.form, &decoded, &selected_bytes)?;
    if selected_bytes != request.bytes {
        return Err(AdapterError::new(
            "SelectedBytesMismatch",
            "bound invented fixture",
        ));
    }
    data.begin_functional()?;
    let branch_taken = execute_one(&mut cpu, &mut data, request.form, &decoded)?;
    trap.record_retirement(before.pc, cpu.pc, request.form)?;
    // No next-PC read occurs. Both mechanisms independently prohibit a later read.
    observer.seal_after_retirement();
    if request.form == FormId::JAddress {
        trap.require_external_exit(decoded.fields.addr16)?;
    }
    let after = request.entry.snapshot(&cpu, &mut data)?;
    let after_data = data.inventory_snapshot()?;
    data.validate_journals()?;
    let d = &decoded.fields;
    Ok(MicroObservation {
        case_id: request.case_id.clone(),
        provenance: request.entry.provenance.clone(),
        scope: "MicroprobeScope_NotCompositePathReachability".into(),
        before,
        after,
        before_data,
        after_data,
        decode: DecodeObservation {
            form: request.form,
            mnemonic: decoded.mnemonic.into(),
            index: decoded.index,
            len: decoded.len,
            dd_before: request.entry.dd,
            dd_after: cpu.dd,
            n8: d.n8,
            n8_alt: d.n8_alt,
            n16: d.n16,
            addr16: d.addr16,
            rel8: d.rel8,
        },
        all_program_bytes: program.content().to_vec(),
        immutable_content_digest: program.digest().into(),
        selected_bytes,
        raw_program: observer.events(),
        data_journal: data.journal,
        raw_data_journal: data.raw_journal,
        seed_journal: data.seed_journal,
        diagnostic_journal: data.diagnostic_journal,
        retired_instructions: trap.retirements().len() as u32,
        cpu_instances: 1,
        retirements: trap.retirements().to_vec(),
        external_transfer: trap.terminal(),
        branch_taken,
        internal_sf_before,
        internal_sf_after: cpu.sf,
        cycles: cpu.cycles,
        instructions: cpu.instructions,
        source_bindings,
        production_exec_integrated: false,
        m2bj_composite_executions: 0,
        original_rom_executions: 0,
        first_mismatch: None,
    })
}

pub fn validate_selected_fields(form: FormId, decoded: &Decoded, bytes: &[u8]) -> Result<()> {
    let spec = form.spec();
    if bytes.len() != spec.pattern.len() {
        return Err(AdapterError::new(
            "WrongInstructionLength",
            "selected literal extent",
        ));
    }
    let mut expected = Fields::default();
    for (token, &byte) in spec.pattern.iter().zip(bytes) {
        match *token {
            "N8" => expected.n8 = byte,
            "N'8" => expected.n8_alt = byte,
            "NL" => expected.n16 = (expected.n16 & 0xff00) | byte as u16,
            "NH" => expected.n16 = (expected.n16 & 255) | ((byte as u16) << 8),
            "addrl" => expected.addr16 = (expected.addr16 & 0xff00) | byte as u16,
            "addrh" => expected.addr16 = (expected.addr16 & 255) | ((byte as u16) << 8),
            "rel8" => expected.rel8 = byte as i8,
            fixed => {
                if u8::from_str_radix(fixed, 16).ok() != Some(byte) {
                    return Err(AdapterError::new(
                        "WrongPrimaryPattern",
                        "selected literal fixed field",
                    ));
                }
            }
        }
    }
    let actual = decoded.fields;
    if (
        actual.n8,
        actual.n8_alt,
        actual.n16,
        actual.n16_alt,
        actual.addr16,
        actual.rel8,
        actual.s8,
    ) != (
        expected.n8,
        expected.n8_alt,
        expected.n16,
        expected.n16_alt,
        expected.addr16,
        expected.rel8,
        expected.s8,
    ) {
        return Err(AdapterError::new(
            "WrongTypedOperand",
            "actual decoded fields disagree with independently bound selected byte positions",
        ));
    }
    Ok(())
}

/// One approved effect only. No public generic execution loop is exposed.
fn execute_one(
    cpu: &mut Cpu,
    data: &mut IndependentDataAccessPolicy,
    form: FormId,
    d: &Decoded,
) -> Result<Option<bool>> {
    use FormId::*;
    let pc = cpu.pc;
    let mut next = pc
        .checked_add(u16::try_from(d.len).map_err(|_| AdapterError::new("PcOverflow", "length"))?)
        .ok_or_else(|| AdapterError::new("PcOverflow", "next instruction"))?;
    let mut branch = None;
    let f = d.fields;
    match form {
        LbAPage | LbAR0 | LbAImm8 => {
            let value = match form {
                LbAPage => data.read(pc, cpu.off_page(f.n8), 8)? as u8,
                LbAR0 => data.read(pc, cpu.bank_base(), 8)? as u8,
                _ => f.n8,
            };
            cpu.set_al(value);
            cpu.zf = value == 0;
        }
        SllbA => {
            let value = cpu.al();
            cpu.set_al(value.wrapping_shl(1));
            cpu.cf = value & 0x80 != 0;
        }
        RolbPage => {
            let address = cpu.off_page(f.n8);
            let value = data.read(pc, address, 8)? as u8;
            let result = value.wrapping_shl(1) | u8::from(cpu.cf);
            data.write(pc, address, 8, result as u16, WriteKind::RMW)?;
            cpu.cf = value & 0x80 != 0;
        }
        AndbAPage => {
            let value = data.read(pc, cpu.off_page(f.n8), 8)? as u8;
            let result = cpu.al() & value;
            cpu.set_al(result);
            cpu.zf = result == 0;
        }
        CmpPageImm16 => {
            let address = cpu.off_page(f.n8);
            if address & 1 != 0 {
                return Err(AdapterError::new(
                    "WrongWidthOrAlignment",
                    "reviewed even LE16 compare",
                ));
            }
            let value = data.read(pc, address, 16)?;
            cpu.cf = value < f.n16;
            cpu.zf = value == f.n16;
        }
        JltRel8 => {
            let taken = cpu.cf;
            branch = Some(taken);
            if taken {
                next = relative(next, f.rel8)?;
            }
        }
        MovbR1Page => {
            let value = data.read(pc, cpu.off_page(f.n8), 8)?;
            data.write(
                pc,
                cpu.bank_base() + 1,
                8,
                value,
                WriteKind::LocalRegisterStore,
            )?;
        }
        AndbPageA => {
            let address = cpu.off_page(f.n8);
            let value = data.read(pc, address, 8)? as u8;
            let result = value & cpu.al();
            data.write(pc, address, 8, result as u16, WriteKind::RMW)?;
            cpu.zf = result == 0;
        }
        JbsPageBit7 | JbsPageBit5 => {
            let value = data.read(pc, cpu.off_page(f.n8), 8)? as u8;
            let bit = if form == JbsPageBit7 { 7 } else { 5 };
            let taken = value & (1 << bit) != 0;
            branch = Some(taken);
            if taken {
                next = relative(next, f.rel8)?;
            }
        }
        OrbPageImm8 => {
            let address = cpu.off_page(f.n8_alt);
            let value = data.read(pc, address, 8)? as u8;
            let result = value | f.n8;
            data.write(pc, address, 8, result as u16, WriteKind::RMW)?;
            cpu.zf = result == 0;
        }
        OrbAImm8 => {
            let result = cpu.al() | f.n8;
            cpu.set_al(result);
            cpu.zf = result == 0;
        }
        StbAPage => {
            data.write(pc, cpu.off_page(f.n8), 8, cpu.al() as u16, WriteKind::Store)?;
        }
        JAddress => {
            if !matches!(f.addr16, 0x5596 | 0x55c5) {
                return Err(AdapterError::new(
                    "WrongExternalTarget",
                    "reviewed invented anchors only",
                ));
            }
            next = f.addr16;
        }
    }
    cpu.pc = next;
    if let Some(dd) = d.dd_after {
        cpu.dd = dd;
    }
    cpu.instructions += 1;
    cpu.cycles += u64::from(d.cycles) + if branch == Some(true) { 4 } else { 0 };
    Ok(branch)
}
fn relative(next: u16, rel: i8) -> Result<u16> {
    u16::try_from(i32::from(next) + i32::from(rel))
        .map_err(|_| AdapterError::new("PcOverflow", "signed relative branch"))
}
