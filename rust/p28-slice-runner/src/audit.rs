//! Opt-in bounded production memory/execution observations.
use crate::{audit_bus::AuditBus, bus::Bus, cpu::Cpu, decoder::Fields, exec};
use serde::{Deserialize, Serialize};

#[path = "audit_composite.rs"]
pub(crate) mod composite;
pub use composite::{
    ClosedCompositeProgram, CompositeEmissionMetadata, CompositeForm, CompositeNodeIdentity,
    CompositeOperand, CompositePath, CompositeReport, CompositeSeeds, CompositeStepOutcome,
};

#[path = "audit_transfer.rs"]
pub(crate) mod transfer;
pub use transfer::{
    ClosedSyntheticTransferProgram, TransferCommitRecord, TransferJournalBoundary,
    TransferProgramMetadata, TransferRecord, TransferReport, TransferSegmentClaim,
    TransferSegmentId, TransferStage, TransferStepRecord, TransferTicket,
};

#[cfg(feature = "p28-word0196-original-rom")]
#[path = "audit_original_rom.rs"]
pub(crate) mod original_rom;
#[cfg(feature = "p28-word0196-original-rom")]
pub use original_rom::{
    ClosedOriginalRomProgram, OriginalRomReport, OriginalRomSeeds, OriginalRomSourceBinding,
    OriginalRomStep, ORIGINAL_ROM_BASE_COMMIT, ORIGINAL_ROM_CONTRACT_SHA256,
};

#[cfg(feature = "p28-word0196-entry-continuity")]
#[path = "audit_entry_continuity.rs"]
mod entry_continuity;
#[cfg(feature = "p28-word0196-entry-continuity")]
pub use entry_continuity::{
    ClosedEntryContinuityProgram, EntryContinuityPath, EntryContinuityReport, EntryContinuitySeeds,
    EntryContinuitySession,
};

pub type Result<T> = std::result::Result<T, AuditError>;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AuditError {
    pub code: String,
    pub address: Option<i64>,
    pub detail: String,
}
impl AuditError {
    pub(crate) fn new(code: &str, address: Option<i64>, detail: impl Into<String>) -> Self {
        Self {
            code: code.into(),
            address,
            detail: detail.into(),
        }
    }
}

pub fn validate_psw(full_psw: u16) -> Result<()> {
    if full_psw & 0x0cc8 != 0x0cc8 {
        return Err(AuditError::new(
            "IncompatiblePsw",
            None,
            "canonical reads-one bits must already be present",
        ));
    }
    Ok(())
}

/// Bytes are never exposed through a mutable reference or serialized.
pub struct ProgramSegment {
    pub(crate) base: u32,
    pub(crate) end: u32,
    pub(crate) bytes: Box<[u8]>,
    pub(crate) digest: String,
}
impl ProgramSegment {
    pub fn new(base: u32, bytes: Vec<u8>, expected_sha256: &str) -> Result<Self> {
        let end = u32::try_from(bytes.len())
            .ok()
            .and_then(|n| base.checked_add(n));
        if bytes.is_empty() || base > 65535 || end.is_none_or(|n| n > 65536) {
            return Err(AuditError::new(
                "InvalidProgramSegment",
                Some(i64::from(base)),
                "nonempty checked 16-bit address space; no padding",
            ));
        }
        let digest = crate::audit_sha256::digest(&bytes);
        if expected_sha256.len() != 64 || digest != expected_sha256 {
            return Err(AuditError::new(
                "ProgramDigestMismatch",
                Some(i64::from(base)),
                "actual immutable bytes must match exact SHA-256",
            ));
        }
        Ok(Self {
            base,
            end: end.expect("checked end"),
            bytes: bytes.into_boxed_slice(),
            digest,
        })
    }
    pub fn base(&self) -> u32 {
        self.base
    }
    pub fn end_exclusive(&self) -> u32 {
        self.end
    }
    pub fn sha256(&self) -> &str {
        &self.digest
    }
    pub(crate) fn contains_address(&self, address: u16) -> bool {
        (self.base..self.end).contains(&u32::from(address))
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub struct Access {
    pub address: u16,
    pub width: u8,
}
impl Access {
    pub(crate) fn addresses(self) -> Result<Vec<u16>> {
        if !matches!(self.width, 8 | 16) {
            return Err(AuditError::new(
                "InvalidDataWidth",
                Some(i64::from(self.address)),
                "only exact 8/16-bit logical operations",
            ));
        }
        (0..self.width / 8)
            .map(|offset| {
                self.address.checked_add(u16::from(offset)).ok_or_else(|| {
                    AuditError::new(
                        "DataAddressOverflow",
                        Some(65536),
                        "checked constituent address",
                    )
                })
            })
            .collect()
    }
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct WriteAccess {
    pub access: Access,
    pub rmw_required: bool,
}
#[derive(Debug, Clone, Serialize)]
pub struct Permissions {
    pub(crate) reads: Vec<Access>,
    pub(crate) writes: Vec<WriteAccess>,
    pub(crate) raw_reads: Vec<u16>,
    pub(crate) raw_writes: Vec<u16>,
}
impl Permissions {
    pub fn new(mut reads: Vec<Access>, mut writes: Vec<WriteAccess>) -> Result<Self> {
        reads.sort();
        writes.sort_by_key(|row| row.access);
        if reads.windows(2).any(|pair| pair[0] == pair[1])
            || writes
                .windows(2)
                .any(|pair| pair[0].access == pair[1].access)
        {
            return Err(AuditError::new(
                "DuplicatePermission",
                None,
                "closed unique logical rights",
            ));
        }
        let mut raw_reads = Vec::new();
        let mut raw_writes = Vec::new();
        for access in &reads {
            raw_reads.extend(access.addresses()?);
        }
        for access in &writes {
            raw_writes.extend(access.access.addresses()?);
        }
        for address in raw_reads.iter().chain(raw_writes.iter()) {
            if !(0x80..0x1000).contains(address) {
                return Err(AuditError::new(
                    "UnsupportedDataPermission",
                    Some(i64::from(*address)),
                    "no SFR/CPU alias silently represented as RAM",
                ));
            }
        }
        raw_reads.sort();
        raw_reads.dedup();
        raw_writes.sort();
        raw_writes.dedup();
        Ok(Self {
            reads,
            writes,
            raw_reads,
            raw_writes,
        })
    }
    pub fn restrict_raw(mut self, mut reads: Vec<u16>, mut writes: Vec<u16>) -> Result<Self> {
        reads.sort();
        writes.sort();
        if reads.windows(2).any(|pair| pair[0] == pair[1])
            || writes.windows(2).any(|pair| pair[0] == pair[1])
            || reads
                .iter()
                .any(|address| !self.raw_reads.contains(address))
            || writes
                .iter()
                .any(|address| !self.raw_writes.contains(address))
        {
            return Err(AuditError::new(
                "RawPermissionWidening",
                None,
                "raw read/write rights may only be narrowed independently",
            ));
        }
        self.raw_reads = reads;
        self.raw_writes = writes;
        Ok(self)
    }
}

#[derive(Debug, Clone)]
pub struct InstructionIdentity {
    pub index: usize,
    pub len: usize,
    pub mnemonic: String,
    pub dd_before: bool,
    pub dd_after: Option<bool>,
    pub fields: Fields,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CpuState {
    pub pc: u16,
    pub a: u16,
    pub ssp: u16,
    pub lrb: u16,
    pub zf: bool,
    pub cf: bool,
    pub hc: bool,
    pub dd: bool,
    pub sf: bool,
    pub psw_other: u16,
    pub cycles: u64,
    pub instructions: u64,
    pub halted: bool,
}
impl From<&Cpu> for CpuState {
    fn from(cpu: &Cpu) -> Self {
        Self {
            pc: cpu.pc,
            a: cpu.a,
            ssp: cpu.ssp,
            lrb: cpu.lrb,
            zf: cpu.zf,
            cf: cpu.cf,
            hc: cpu.hc,
            dd: cpu.dd,
            sf: cpu.sf,
            psw_other: cpu.psw_other,
            cycles: cpu.cycles,
            instructions: cpu.instructions,
            halted: cpu.halted,
        }
    }
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Snapshot {
    pub cpu: CpuState,
    pub ram: Vec<u8>,
    pub ram_range: [u16; 2],
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProgramEvent {
    pub ordinal: u64,
    pub pc: Option<u16>,
    pub address: i64,
    pub segment_offset: Option<u32>,
    pub instruction_offset: Option<u32>,
    pub acquired_purpose: String,
    pub selection_association: Option<String>,
    pub selected_length: Option<usize>,
    pub serviced: bool,
    pub refusal: Option<AuditError>,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DataEvent {
    pub ordinal: u64,
    pub phase: String,
    pub pc: Option<u16>,
    pub instruction_index: Option<usize>,
    pub address: u16,
    pub width: u8,
    pub operation: String,
    pub requested_value: Option<u16>,
    pub value: Option<u16>,
    pub old_value: Option<u16>,
    pub write_ordinal: Option<u64>,
    pub same_value: Option<bool>,
    pub serviced: bool,
    pub refusal: Option<AuditError>,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RawDataEvent {
    pub ordinal: u64,
    pub logical_ordinal: u64,
    pub address: u16,
    pub operation: String,
    pub requested_value: Option<u8>,
    pub value: Option<u8>,
    pub old_value: Option<u8>,
    pub write_ordinal: Option<u64>,
    pub same_value: Option<bool>,
    pub serviced: bool,
    pub refusal: Option<AuditError>,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DiagnosticEvent {
    pub ordinal: u64,
    pub kind: String,
    pub range: [u16; 2],
    pub byte_count: usize,
}
/// An actual public API request refused before any production Bus operation.
/// This is not a fabricated functional logical/raw memory service event.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DataAdmissionRefusal {
    pub ordinal: u64,
    pub classification: String,
    pub phase: String,
    pub pc: u16,
    pub address: u16,
    pub width: u8,
    pub operation: String,
    pub requested_value: Option<u16>,
    pub production_bus_called: bool,
    pub serviced: bool,
    pub refusal: AuditError,
}
#[derive(Debug, Clone, Serialize)]
pub struct AuditReport {
    pub entry_pc: u16,
    pub current_pc: u16,
    pub program_base: u32,
    pub program_end_exclusive: u32,
    pub program_sha256: String,
    pub program_events: Vec<ProgramEvent>,
    pub data_events: Vec<DataEvent>,
    pub raw_data_events: Vec<RawDataEvent>,
    pub diagnostic_events: Vec<DiagnosticEvent>,
    pub data_admission_refusals: Vec<DataAdmissionRefusal>,
    pub permissions: Permissions,
    pub phase: String,
    pub budget: u8,
    pub successful_retirements: u64,
    pub step_calls: u64,
    pub execution_calls: u64,
    pub shared_execution_calls: u64,
    pub sealed: bool,
    pub terminal_reason: Option<String>,
    pub external_exit: Option<u16>,
    pub first_fault: Option<AuditError>,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecodedState {
    pub index: usize,
    pub mnemonic: String,
    pub len: usize,
    pub dd_before: bool,
    pub dd_after: bool,
    pub dd_after_option: Option<bool>,
    pub cycles: u16,
    pub n8: u8,
    pub n8_alt: u8,
    pub n16: u16,
    pub n16_alt: u16,
    pub s8: i8,
    pub rel8: i8,
    pub addr16: u16,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StepOutcome {
    pub pc_before: u16,
    pub pc_after: u16,
    pub decoded_index: usize,
    pub mnemonic: String,
    pub len: usize,
    pub decoded: DecodedState,
    pub selected_extent: [u32; 2],
    pub selected_extent_sha256: String,
    pub retired: bool,
    pub external_exit: Option<u16>,
}

pub struct Session {
    cpu: Cpu,
    bus: Bus,
}
impl Session {
    // Only the closed M2bu wrapper can construct this token. No public caller
    // can supply a maximum, a PC stream, or widen the legacy1..16 constructor.
    #[cfg(feature = "p28-word0196-entry-continuity")]
    fn new_entry_continuity_admitted(
        segment: ProgramSegment,
        cpu: Cpu,
        full_psw: u16,
        permissions: Permissions,
        admission: entry_continuity::EntryBudget,
    ) -> Result<Self> {
        validate_psw(full_psw)?;
        let permissions = Permissions::new(permissions.reads.clone(), permissions.writes.clone())?
            .restrict_raw(
                permissions.raw_reads.clone(),
                permissions.raw_writes.clone(),
            )?;
        let budget = admission.retirements();
        if cpu.psw_u16() != full_psw
            || cpu.psw_other & !0x0337 != 0
            || cpu.halted
            || u32::from(cpu.pc) != segment.base
            || !matches!(budget, 1 | 6 | 16 | 18 | 19 | 21)
        {
            return Err(AuditError::new(
                "InvalidEntryContinuityState",
                Some(i64::from(cpu.pc)),
                "coherent canonical technical entry and sealed closed-path retirement token",
            ));
        }
        let mut bus = Bus::new(Vec::new(), 0xa5);
        bus.audit = Some(AuditBus::new(segment, permissions, cpu.pc, budget));
        Ok(Self { cpu, bus })
    }
    pub fn new(
        segment: ProgramSegment,
        cpu: Cpu,
        full_psw: u16,
        permissions: Permissions,
        budget: u8,
    ) -> Result<Self> {
        validate_psw(full_psw)?;
        let permissions = Permissions::new(permissions.reads.clone(), permissions.writes.clone())?
            .restrict_raw(
                permissions.raw_reads.clone(),
                permissions.raw_writes.clone(),
            )?;
        if cpu.psw_u16() != full_psw
            || cpu.psw_other & !0x0337 != 0
            || cpu.halted
            || u32::from(cpu.pc) != segment.base
            || budget == 0
            || budget > 16
        {
            return Err(AuditError::new(
                "InvalidEntryState",
                Some(i64::from(cpu.pc)),
                "explicit canonical coherent PC/PSW; budget1..16; not halted",
            ));
        }
        let mut bus = Bus::new(Vec::new(), 0xa5);
        bus.audit = Some(AuditBus::new(segment, permissions, cpu.pc, budget));
        Ok(Self { cpu, bus })
    }
    pub fn seed_byte(&mut self, address: u16, value: u8) -> Result<()> {
        self.bus
            .audit
            .as_ref()
            .expect("installed")
            .admit_seed(address, 8)?;
        exec::write_data_u8(&mut self.cpu, &mut self.bus, address, value);
        self.current_fault()
    }
    pub fn seed_word(&mut self, address: u16, value: u16) -> Result<()> {
        self.bus
            .audit
            .as_ref()
            .expect("installed")
            .admit_seed(address, 16)?;
        exec::write_data_u16(&mut self.cpu, &mut self.bus, address, value);
        self.current_fault()
    }
    pub fn begin_functional(&mut self) -> Result<()> {
        self.bus
            .audit
            .as_ref()
            .expect("installed")
            .begin_functional()
    }
    pub fn diagnostic_snapshot(&mut self) -> Result<Snapshot> {
        let ram = self.bus.audit_snapshot_ram();
        Ok(Snapshot {
            cpu: CpuState::from(&self.cpu),
            ram,
            ram_range: [0x80, 0x1000],
        })
    }
    pub fn program_probe(&mut self, address: i64) -> Result<u8> {
        self.bus
            .audit_program_read(address, "DiagnosticProgramProbe")
    }
    pub fn data_read(&mut self, address: u16, width: u8) -> Result<u16> {
        self.bus
            .audit
            .as_ref()
            .expect("installed")
            .begin_capability(address, width, false, None)?;
        let value = match width {
            8 => u16::from(exec::read_data_u8(&self.cpu, &mut self.bus, address)),
            16 => exec::read_data_u16(&self.cpu, &mut self.bus, address),
            _ => {
                return Err(self.bus.audit_fault(AuditError::new(
                    "InvalidDataWidth",
                    Some(i64::from(address)),
                    "capability read",
                )))
            }
        };
        self.current_fault()?;
        Ok(value)
    }
    pub fn data_write(&mut self, address: u16, width: u8, value: u16) -> Result<()> {
        self.bus
            .audit
            .as_ref()
            .expect("installed")
            .begin_capability(address, width, true, Some(value))?;
        match width {
            8 if value <= 255 => {
                exec::write_data_u8(&mut self.cpu, &mut self.bus, address, value as u8)
            }
            16 => exec::write_data_u16(&mut self.cpu, &mut self.bus, address, value),
            _ => {
                return Err(self.bus.audit_fault(AuditError::new(
                    "InvalidDataWidthOrValue",
                    Some(i64::from(address)),
                    "capability write",
                )))
            }
        }
        self.current_fault()
    }
    fn current_fault(&self) -> Result<()> {
        self.bus
            .audit
            .as_ref()
            .expect("installed")
            .fault()
            .map_or(Ok(()), Err)
    }
    pub fn step(&mut self, expected: &InstructionIdentity) -> Result<StepOutcome> {
        self.bus
            .audit
            .as_ref()
            .expect("installed")
            .admit_legacy_step()?;
        self.checked_step(expected)
    }
    // One checked instruction implementation shared by both explicit audit modes.
    fn checked_step(&mut self, expected: &InstructionIdentity) -> Result<StepOutcome> {
        let pc = self.cpu.pc;
        let dd_before = self.cpu.dd;
        self.bus.audit.as_ref().expect("installed").begin_step(pc)?;
        let result = (|| {
            if expected.dd_before != self.cpu.dd {
                return Err(AuditError::new(
                    "WrongIncomingDd",
                    Some(i64::from(pc)),
                    "frozen instruction context",
                ));
            }
            let decoded = crate::decoder::decode_checked(self.cpu.dd, |offset| {
                let address = i64::from(pc)
                    .checked_add(i64::try_from(offset).map_err(|_| {
                        AuditError::new("ProgramAddressOverflow", None, "decoder offset")
                    })?)
                    .ok_or_else(|| {
                        AuditError::new("ProgramAddressOverflow", None, "decoder address")
                    })?;
                self.bus.audit_program_read(address, "DecoderProbe")
            })?
            .ok_or_else(|| {
                AuditError::new(
                    "UndefinedOpcode",
                    Some(i64::from(pc)),
                    "production decoder selected no form",
                )
            })?;
            self.bus
                .audit
                .as_ref()
                .expect("installed")
                .associate_selection(decoded.len)?;
            let mut selected = Vec::with_capacity(decoded.len);
            for offset in 0..decoded.len {
                selected.push(self.bus.audit_program_read(
                    i64::from(pc) + offset as i64,
                    "ArchitecturalSelectedFetch",
                )?);
            }
            let a = decoded.fields;
            let b = expected.fields;
            if decoded.index != expected.index
                || decoded.len != expected.len
                || decoded.mnemonic != expected.mnemonic
                || decoded.dd_after != expected.dd_after
                || a.n8 != b.n8
                || a.n8_alt != b.n8_alt
                || a.n16 != b.n16
                || a.n16_alt != b.n16_alt
                || a.s8 != b.s8
                || a.rel8 != b.rel8
                || a.addr16 != b.addr16
            {
                return Err(AuditError::new(
                    "SelectedInstructionMismatch",
                    Some(i64::from(pc)),
                    "actual production selection/operands differ from frozen exact identity",
                ));
            }
            if u32::from(pc) + decoded.len as u32 > 65535 {
                return Err(AuditError::new(
                    "SelectedPcOverflow",
                    Some(i64::from(pc)),
                    "retain production no-wrap PC advance",
                ));
            }
            self.bus
                .audit
                .as_ref()
                .expect("installed")
                .set_instruction(decoded.index);
            self.bus.audit.as_ref().expect("installed").before_execute();
            let actual = exec::execute_decoded(&mut self.cpu, &mut self.bus, pc, decoded).map_err(
                |error| {
                    self.bus
                        .audit
                        .as_ref()
                        .expect("installed")
                        .fault()
                        .unwrap_or_else(|| {
                            AuditError::new(
                                "ProductionExecutionError",
                                Some(i64::from(pc)),
                                error.to_string(),
                            )
                        })
                },
            )?;
            self.current_fault()?;
            let external = if actual.mnemonic == "J addr16" {
                self.bus
                    .audit
                    .as_ref()
                    .expect("installed")
                    .external_target(self.cpu.pc)
            } else {
                None
            };
            self.bus
                .audit
                .as_ref()
                .expect("installed")
                .retire(self.cpu.pc, external)?;
            let fields = actual.fields;
            let decoded = DecodedState {
                index: actual.index,
                mnemonic: actual.mnemonic.into(),
                len: actual.len,
                dd_before,
                dd_after: self.cpu.dd,
                dd_after_option: actual.dd_after,
                cycles: actual.cycles,
                n8: fields.n8,
                n8_alt: fields.n8_alt,
                n16: fields.n16,
                n16_alt: fields.n16_alt,
                s8: fields.s8,
                rel8: fields.rel8,
                addr16: fields.addr16,
            };
            Ok(StepOutcome {
                pc_before: pc,
                pc_after: self.cpu.pc,
                decoded_index: actual.index,
                mnemonic: actual.mnemonic.into(),
                len: actual.len,
                decoded,
                selected_extent: [u32::from(pc), u32::from(pc) + actual.len as u32],
                selected_extent_sha256: crate::audit_sha256::digest(&selected),
                retired: true,
                external_exit: external,
            })
        })();
        self.bus
            .audit
            .as_ref()
            .expect("installed")
            .set_current_pc(self.cpu.pc);
        if let Err(error) = &result {
            self.bus.audit_fault(error.clone());
        }
        result
    }
    pub fn report(&self) -> AuditReport {
        self.bus.audit.as_ref().expect("installed").report()
    }
}
