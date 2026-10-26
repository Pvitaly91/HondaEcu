//! M2bv closed P2 extension of the existing production checked-step lifecycle.
//! No opcode arithmetic, pins, scheduler, downstream execution or mutable API.
use super::{
    original_rom::{OriginalNode, OriginalState},
    Access, AuditError, AuditReport, ClosedEntryContinuityProgram, EntryContinuityPath,
    EntryContinuitySeeds, InstructionIdentity, OriginalRomSourceBinding, OriginalRomStep,
    Permissions, ProgramSegment, Result, Session, Snapshot, WriteAccess,
};
use crate::{cpu::Cpu, decoder::Fields};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum P2HandoffPath {
    A,
    B,
    C,
    D,
}
impl P2HandoffPath {
    pub fn budget(self) -> u8 {
        match self {
            Self::A => 17,
            Self::B => 19,
            Self::C => 20,
            Self::D => 22,
        }
    }
    fn prefix(self) -> EntryContinuityPath {
        match self {
            Self::A => EntryContinuityPath::A,
            Self::B => EntryContinuityPath::B,
            Self::C => EntryContinuityPath::C,
            Self::D => EntryContinuityPath::D,
        }
    }
    fn algorithm_path(self) -> super::CompositePath {
        match self {
            Self::A => super::CompositePath::A,
            Self::B => super::CompositePath::B,
            Self::C => super::CompositePath::C,
            Self::D => super::CompositePath::D,
        }
    }
}
// Private field and constructor: no host integer can widen an admission.
pub(super) struct P2Budget {
    count: u8,
}
impl P2Budget {
    fn for_path(path: P2HandoffPath) -> Self {
        Self {
            count: path.budget(),
        }
    }
    pub(super) fn retirements(&self) -> u8 {
        self.count
    }
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct P2Snapshot {
    pub value: u8,
    pub p2io: u8,
    pub p2sf: u8,
    pub provenance: String,
}
impl P2Snapshot {
    pub(super) fn validate(&self) -> Result<()> {
        if self.p2io != 0xff
            || self.p2sf != 0x07
            || self.provenance != "TechnicalArchitecturalP2LatchSnapshot_NoNativeWriterGeneration"
        {
            return Err(AuditError::new("P2PrimaryOutputModeRequired",Some(0x24),
                "reviewed P2IO=FF/P2SF=07 snapshot only; no native startup/physical ownership claim"));
        }
        Ok(())
    }
}

pub struct ClosedP2HandoffProgram {
    pub(super) segment: ProgramSegment,
    prefix: ClosedEntryContinuityProgram,
    pub(super) native: bool,
    pub(super) source_binding: Option<OriginalRomSourceBinding>,
}
impl ClosedP2HandoffProgram {
    pub fn admit_host_verified_segment(
        base: u32,
        bytes: Vec<u8>,
        digest: &str,
        binding: OriginalRomSourceBinding,
    ) -> Result<Self> {
        if base != 0x54f5 || bytes.len() != 211 {
            return Err(AuditError::new(
                "P2HandoffSegmentRejected",
                Some(i64::from(base)),
                "unchanged211-byte original[54F5,55C8) only; no padding/relocation",
            ));
        }
        let segment = ProgramSegment::new(base, bytes, digest)?;
        let prefix_bytes = segment.bytes[..208].to_vec();
        let prefix_digest = crate::audit_sha256::digest(&prefix_bytes);
        let prefix = ClosedEntryContinuityProgram::admit_host_verified_segment(
            base,
            prefix_bytes,
            &prefix_digest,
            binding.clone(),
        )?;
        Ok(Self {
            segment,
            prefix,
            native: true,
            source_binding: Some(binding),
        })
    }
    pub fn explicit_invented_public_fixture() -> Self {
        let prefix = ClosedEntryContinuityProgram::explicit_invented_public_fixture();
        let (invented, _, _, _) = prefix.p2_extension_metadata(EntryContinuityPath::A);
        // Reuse ONLY the existing independently invented public prefix bytes.
        // All its PROGRAM targets are relative; changing6200 to6400 preserves
        // those operands. No private original bytes are copied into a fixture.
        let mut bytes = invented.bytes.to_vec();
        bytes.extend([0xa5; 3]);
        for (offset, op) in [(0x5596 - 0x54f5, 0xd1), (0x55c5 - 0x54f5, 0xe1)] {
            bytes[offset..offset + 3].copy_from_slice(&[0xc5, 0x24, op]);
        }
        let digest = crate::audit_sha256::digest(&bytes);
        Self {
            segment: ProgramSegment::new(0x6400, bytes, &digest)
                .expect("fixed invented P2 fixture"),
            prefix,
            native: false,
            source_binding: None,
        }
    }
    pub fn entry_pc(&self) -> u16 {
        self.segment.base as u16
    }
    pub fn program_sha256(&self) -> &str {
        self.segment.sha256()
    }
    pub fn classification(&self) -> &'static str {
        if self.native {
            "OriginalRomBytes_TechnicalP2HandoffExecution"
        } else {
            "ExplicitInventedPublicP2HandoffFixture"
        }
    }
    pub(super) fn pc(&self, native: u16) -> u16 {
        self.entry_pc() + (native - 0x54f5)
    }
    pub(super) fn p2_pc(&self, path: P2HandoffPath) -> u16 {
        self.pc(if path == P2HandoffPath::A {
            0x55c5
        } else {
            0x5596
        })
    }
    pub(super) fn parts(&self, path: P2HandoffPath) -> (Vec<OriginalNode>, Vec<u16>, Vec<u16>) {
        let (_, mut nodes, inventory, mut pcs) = self.prefix.p2_extension_metadata(path.prefix());
        if !self.native {
            for node in &mut nodes {
                node.pc += 0x200;
                for pc in &mut node.successors {
                    *pc += 0x200;
                }
            }
            for pc in &mut pcs {
                *pc += 0x200;
            }
        }
        for (pc, index, mnemonic) in [(0x5596, 350, "ANDB N8, A"), (0x55c5, 1647, "ORB N8, A")] {
            nodes.push(OriginalNode {
                pc: self.pc(pc),
                identity: InstructionIdentity {
                    index,
                    len: 3,
                    mnemonic: mnemonic.into(),
                    dd_before: false,
                    dd_after: None,
                    fields: Fields {
                        n8: 0x24,
                        ..Fields::default()
                    },
                },
                reachable_dd: vec![false],
                successors: vec![self.pc(pc + 3)],
                reads: vec![Access {
                    address: 0x24,
                    width: 8,
                }],
                writes: vec![WriteAccess {
                    access: Access {
                        address: 0x24,
                        width: 8,
                    },
                    rmw_required: true,
                }],
            });
        }
        pcs.push(self.p2_pc(path));
        assert_eq!(nodes.len(), 26);
        (nodes, inventory, pcs)
    }
    pub(super) fn segment_copy(&self) -> ProgramSegment {
        ProgramSegment {
            base: self.segment.base,
            end: self.segment.end,
            bytes: self.segment.bytes.clone(),
            digest: self.segment.digest.clone(),
        }
    }
}

pub struct P2HandoffSeeds {
    pub(super) data: BTreeMap<u16, u8>,
    pub(super) pointing: [[u16; 4]; 8],
}
impl P2HandoffSeeds {
    pub fn new(
        program: &ClosedP2HandoffProgram,
        data: BTreeMap<u16, u8>,
        pointing: [[u16; 4]; 8],
        r: [u8; 8],
        er: [u16; 4],
    ) -> Result<Self> {
        // Reuse unchanged M2bu exact-inventory and r/er alias admission only.
        // This temporary value constructs no CPU/Bus and executes no code.
        EntryContinuitySeeds::new(&program.prefix, data.clone(), pointing, r, er)?;
        Ok(Self { data, pointing })
    }
}
#[derive(Debug, Clone, Serialize)]
pub struct P2StepSnapshot {
    pub index: u64,
    pub before: u8,
    pub after: u8,
}
#[derive(Debug, Clone, Serialize)]
pub struct P2PeripheralEvent {
    pub ordinal: u64,
    pub pc: u16,
    pub address: u16,
    pub width: u8,
    pub operation: String,
    pub value: u8,
    pub logical_ordinal: u64,
    pub raw_ordinal: u64,
    pub write_ordinal: Option<u64>,
    pub native_write_ordinal: Option<u64>,
    pub same_value: Option<bool>,
    pub space: String,
}
#[derive(Debug, Clone, Serialize)]
pub struct P2Generation {
    pub machine_id: u32,
    pub writer_pc: u16,
    pub retired_instruction: u64,
    pub generation_ordinal: u64,
    pub native_write_ordinal: u64,
    pub logical_write_ordinal: u64,
    pub raw_write_ordinal: u64,
    pub value: u8,
}
#[derive(Debug, Clone, Serialize)]
pub struct P2HandoffReport {
    pub classification: String,
    pub source_binding: Option<OriginalRomSourceBinding>,
    pub program_node_count: usize,
    pub path: P2HandoffPath,
    pub entry: Snapshot,
    pub current: Snapshot,
    pub full_psw: u16,
    pub steps: Vec<OriginalRomStep>,
    pub completed: bool,
    pub positive_completed: bool,
    pub boundary_only: bool,
    pub actual_handoff_observed: bool,
    pub native_predecessor_retirements: u64,
    pub algorithm_retirements: u64,
    pub p2_instruction_retirements: u64,
    pub stop_before_pc: Option<u16>,
    pub audit: AuditReport,
    pub p2_snapshot: P2Snapshot,
    pub p2_initial: u8,
    pub p2_final: u8,
    pub p2_step_snapshots: Vec<P2StepSnapshot>,
    pub peripheral_p2_journal: Vec<P2PeripheralEvent>,
    pub p2_generation: Option<P2Generation>,
    pub ownership: serde_json::Value,
}

pub struct P2HandoffSession {
    pub(super) inner: Box<Session>,
    cpu_identity: usize,
    bus_identity: usize,
    last_actual: Snapshot,
    last_p2: u8,
    fault: Option<AuditError>,
    path: P2HandoffPath,
    entry_pc: u16,
    p2_pc: u16,
    initial: P2Snapshot,
    p2_steps: Vec<P2StepSnapshot>,
}
impl P2HandoffSession {
    pub(super) fn is_below_second_p2(&self) -> bool {
        #[cfg(feature = "p28-word0196-below-second-p2-continuity")]
        {
            self.inner
                .bus
                .audit
                .as_ref()
                .expect("installed")
                .below_second_p2_active()
        }
        #[cfg(not(feature = "p28-word0196-below-second-p2-continuity"))]
        {
            false
        }
    }
    pub(super) fn native_seed_writes(&self) -> u64 {
        if self.is_below_second_p2() {
            55
        } else {
            48
        }
    }
    pub fn new(
        program: &ClosedP2HandoffProgram,
        cpu: Cpu,
        full_psw: u16,
        seeds: P2HandoffSeeds,
        path: P2HandoffPath,
        budget: u8,
        snapshot: P2Snapshot,
    ) -> Result<Self> {
        snapshot.validate()?;
        let (nodes, inventory, pcs) = program.parts(path);
        if cpu.pc != program.entry_pc()
            || cpu.lrb != 0x21
            || cpu.cycles != 0
            || cpu.instructions != 0
            || budget != path.budget()
            || usize::from(budget) != pcs.len()
        {
            return Err(AuditError::new(
                "P2HandoffEntryRejected",
                Some(i64::from(cpu.pc)),
                "fresh54F5-equivalent CPU, unchangedLRB21 and exact closed17/19/20/22 budget",
            ));
        }
        let active: Vec<_> = nodes.iter().filter(|n| pcs.contains(&n.pc)).collect();
        // Generic rights remain RAM-only. The SFR has a separate one-shot
        // capability, and is never inserted into these raw/logical RAM lists.
        let mut reads: Vec<_> = active
            .iter()
            .flat_map(|n| n.reads.clone())
            .filter(|r| r.address >= 0x80)
            .collect();
        reads.sort();
        reads.dedup();
        let mut writes: Vec<_> = active
            .iter()
            .flat_map(|n| n.writes.clone())
            .filter(|r| r.access.address >= 0x80)
            .collect();
        writes.sort_by_key(|w| w.access);
        writes.dedup_by_key(|w| w.access);
        let inner = Session::new_p2_handoff_admitted(
            program.segment_copy(),
            cpu,
            full_psw,
            Permissions::new(reads, writes)?,
            P2Budget::for_path(path),
        )?;
        Self::from_admitted(
            program,
            inner,
            seeds,
            path,
            snapshot,
            nodes,
            inventory,
            pcs,
            program.p2_pc(path) + 3,
            None,
        )
    }
    // Same M2bv setup: one admitted CPU/Bus; every seed precedes begin_functional.
    pub(super) fn from_admitted(
        program: &ClosedP2HandoffProgram,
        mut inner: Session,
        seeds: P2HandoffSeeds,
        path: P2HandoffPath,
        snapshot: P2Snapshot,
        nodes: Vec<OriginalNode>,
        inventory: Vec<u16>,
        pcs: Vec<u16>,
        terminal: u16,
        control: Option<[u8; 2]>,
    ) -> Result<Self> {
        for (address, value) in seeds.data {
            inner.seed_byte(address, value)?;
        }
        for (bank, words) in seeds.pointing.iter().enumerate() {
            for (slot, value) in words.iter().enumerate() {
                inner.seed_word(0x80 + bank as u16 * 8 + slot as u16 * 2, *value)?;
            }
        }
        inner
            .bus
            .initialize_p2_output_latch(snapshot.value)
            .map_err(|detail| AuditError::new("P2InitialSnapshotRejected", Some(0x24), detail))?;
        inner.bus.begin_native_accesses();
        inner.bus.begin_p2_accesses();
        let entry = inner.diagnostic_snapshot()?;
        let p2_pc = program.p2_pc(path);
        inner
            .bus
            .audit
            .as_ref()
            .expect("installed")
            .install_original(OriginalState {
                nodes,
                pcs,
                inventory,
                terminal,
                path: path.algorithm_path(),
                entry,
                classification: program.classification().into(),
                source_binding: program.source_binding.clone(),
                steps: vec![],
            })?;
        let p2_index = if path == P2HandoffPath::A { 1647 } else { 350 };
        if let Some(values) = control {
            inner
                .bus
                .initialize_post_p2_control(values[0], values[1])
                .map_err(|e| AuditError::new("PostP2InitialSnapshotRejected", None, e))?;
            #[cfg(feature = "p28-word0196-post-p2-control")]
            inner
                .bus
                .audit
                .as_ref()
                .expect("installed")
                .install_post_p2_control(p2_pc, p2_index)?;
            #[cfg(not(feature = "p28-word0196-post-p2-control"))]
            return Err(AuditError::new(
                "PostP2FeatureRequired",
                None,
                "default OFF",
            ));
        } else {
            inner
                .bus
                .audit
                .as_ref()
                .expect("installed")
                .install_p2_handoff(p2_pc, p2_index)?;
        }
        inner.begin_functional()?;
        let last_actual = inner.diagnostic_snapshot()?;
        let last_p2 = inner.bus.p2_output_latch().expect("once initialized");
        let inner = Box::new(inner);
        let cpu_identity = std::ptr::from_ref(&inner.cpu) as usize;
        let bus_identity = std::ptr::from_ref(&inner.bus) as usize;
        Ok(Self {
            inner,
            cpu_identity,
            bus_identity,
            last_actual,
            last_p2,
            fault: None,
            path,
            entry_pc: program.entry_pc(),
            p2_pc,
            initial: snapshot,
            p2_steps: vec![],
        })
    }
    fn verify_continuity(&mut self) -> Result<()> {
        if let Some(error) = &self.fault {
            return Err(error.clone());
        }
        let error = if std::ptr::from_ref(&self.inner.cpu) as usize != self.cpu_identity
            || std::ptr::from_ref(&self.inner.bus) as usize != self.bus_identity
        {
            Some(AuditError::new(
                "P2MachineSubstitutionRejected",
                None,
                "one retained privately owned CPU/Bus",
            ))
        } else if self.inner.diagnostic_snapshot()? != self.last_actual
            || self.inner.bus.p2_output_latch() != Some(self.last_p2)
        {
            Some(AuditError::new(
                "P2LiveStateChanged",
                None,
                "no host PC/register/RAM/latch mutation or terminal reseed",
            ))
        } else {
            None
        };
        if let Some(error) = error {
            self.fault = Some(error.clone());
            return Err(error);
        }
        Ok(())
    }
    pub fn step(&mut self) -> Result<OriginalRomStep> {
        self.verify_continuity()?;
        let before = self.last_p2;
        let outcome = self.inner.step_original_rom();
        self.last_actual = self.inner.diagnostic_snapshot()?;
        self.last_p2 = self.inner.bus.p2_output_latch().expect("retained latch");
        if let Ok(step) = &outcome {
            self.p2_steps.push(P2StepSnapshot {
                index: step.index,
                before,
                after: self.last_p2,
            });
        }
        outcome
    }
    pub fn report(&mut self) -> Result<P2HandoffReport> {
        self.verify_continuity()?;
        let report = self.inner.original_rom_report()?;
        let state = self
            .inner
            .bus
            .audit
            .as_ref()
            .expect("installed")
            .p2_handoff_state()
            .expect("closed capability");
        let all_service = self.inner.bus.p2_accesses();
        let below = self.is_below_second_p2();
        if all_service.len() > if below { 4 } else { 2 } {
            return Err(AuditError::new(
                "P2JournalCardinalityRejected",
                None,
                "one actual RMW service pair",
            ));
        }
        // The singular M2bv/M2bw projection remains G1. The separate M2bx
        // report verifies and exposes all four actual services and G2.
        let service = &all_service[..all_service.len().min(2)];
        let mut journal = Vec::new();
        for (index, row) in service.iter().enumerate() {
            let ordinal = if index == 0 {
                state.read_ordinal
            } else {
                state.write_ordinal
            }
            .ok_or_else(|| {
                AuditError::new(
                    "P2ServiceLinkMissing",
                    Some(0x24),
                    "actual peripheral service must link to logical audit",
                )
            })?;
            let logical = report
                .audit
                .data_events
                .get(ordinal as usize)
                .ok_or_else(|| {
                    AuditError::new(
                        "P2LogicalEventMissing",
                        Some(0x24),
                        "source-bound actual logical ordinal",
                    )
                })?;
            let raw: Vec<_> = report
                .audit
                .raw_data_events
                .iter()
                .filter(|e| e.logical_ordinal == ordinal)
                .collect();
            if row[0] != u32::from(self.p2_pc)
                || row[1] != 0x24
                || row[2] != 8
                || row[3] != index as u32
                || logical.pc != Some(self.p2_pc)
                || logical.address != 0x24
                || logical.width != 8
                || logical.value != Some(row[4] as u16)
                || !logical.serviced
                || raw.len() != 1
                || raw[0].value != Some(row[4] as u8)
                || !raw[0].serviced
            {
                return Err(AuditError::new(
                    "P2ServiceAuditMismatch",
                    Some(0x24),
                    "same actual service, never duplicate semantic writes",
                ));
            }
            let native_write = logical
                .write_ordinal
                .map(|n| {
                    n.checked_sub(self.native_seed_writes()).ok_or_else(|| {
                        AuditError::new(
                            "P2NativeWriteOrdinalUnderflow",
                            None,
                            "technical seeds are not native writes",
                        )
                    })
                })
                .transpose()?;
            journal.push(P2PeripheralEvent {
                ordinal: index as u64,
                pc: self.p2_pc,
                address: 0x24,
                width: 8,
                operation: logical.operation.clone(),
                value: row[4] as u8,
                logical_ordinal: ordinal,
                raw_ordinal: raw[0].ordinal,
                write_ordinal: logical.write_ordinal,
                native_write_ordinal: native_write,
                same_value: logical.same_value,
                space: "PeripheralP2".into(),
            });
        }
        let p2_count = u64::from(state.retired);
        let generation = if state.retired {
            let event = journal.get(1).ok_or_else(|| {
                AuditError::new("P2GenerationEventMissing", None, "actual native store")
            })?;
            let raw = &report.audit.raw_data_events[event.raw_ordinal as usize];
            Some(P2Generation {
                machine_id: 1,
                writer_pc: self.p2_pc,
                retired_instruction: report
                    .steps
                    .iter()
                    .find(|s| s.outcome.pc_before == self.p2_pc)
                    .expect("actual P2 retirement")
                    .index,
                generation_ordinal: 1,
                native_write_ordinal: event.native_write_ordinal.expect("actual write"),
                logical_write_ordinal: event.write_ordinal.expect("actual write"),
                raw_write_ordinal: raw.write_ordinal.expect("actual raw write"),
                value: event.value,
            })
        } else {
            None
        };
        let handoff = report.steps.iter().any(|step| {
            step.outcome.retired
                && step.outcome.pc_before == self.entry_pc + (0x5501 - 0x54f5)
                && step.outcome.pc_after == self.entry_pc + (0x556f - 0x54f5)
        });
        let completed = report.completed && state.retired && journal.len() == 2;
        let count = report.steps.len() as u64;
        let ownership = serde_json::json!({"P2InitialSource":"TechnicalArchitecturalSnapshot",
            "P2InitialNativeOwner":"NotEstablished","P2RmwWriter":if state.retired {"ActualProductionInstruction"}else{"NotObserved"},
            "P2RmwWriterPC":state.retired.then_some(self.p2_pc),"P2FinalGeneration":if completed {"VerifiedWithinTechnicalSession"}else{"NotEstablished"},
            "PhysicalP2Owner":"NotEstablished","PhysicalOutputEffect":"NotObserved"});
        Ok(P2HandoffReport {
            classification: report.classification,
            source_binding: report.source_binding,
            program_node_count: report.program_node_count,
            path: self.path,
            entry: report.entry,
            current: report.current,
            full_psw: report.full_psw,
            steps: report.steps,
            completed,
            positive_completed: completed && handoff,
            boundary_only: false,
            actual_handoff_observed: handoff,
            native_predecessor_retirements: count.min(6),
            algorithm_retirements: count
                .min(u64::from(self.path.budget()))
                .saturating_sub(6 + p2_count),
            p2_instruction_retirements: p2_count,
            stop_before_pc: report.stop_before_pc,
            audit: report.audit,
            p2_snapshot: self.initial.clone(),
            p2_initial: self.initial.value,
            p2_final: self.last_p2,
            p2_step_snapshots: self.p2_steps.clone(),
            peripheral_p2_journal: journal,
            p2_generation: generation,
            ownership,
        })
    }
}

#[cfg(test)]
#[path = "audit_p2_handoff_tests.rs"]
mod tests;
