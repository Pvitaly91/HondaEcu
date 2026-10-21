//! Closed invented caller/composite/continuation authority. No ISA semantics.
use super::{
    composite::{ClosedState, COMPOSITE_SHA256},
    AuditError, AuditReport, CompositeForm, CompositeNodeIdentity, CompositeOperand, CompositePath,
    CompositeSeeds, CpuState, Permissions, ProgramSegment, Result, Session, Snapshot, StepOutcome,
};
use crate::{audit_bus::AuditBus, bus::Bus, cpu::Cpu};
use serde::{Deserialize, Serialize};
use std::sync::Arc;

const PROVENANCE: &str = "InventedOnly_NoNativeGenerationOwner";
const MANUAL: &str = "f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TransferStage {
    Caller,
    Composite,
    Continuation,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TransferSegmentId {
    Caller,
    Composite,
    BelowContinuation,
    NotBelowContinuation,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TransferSegmentClaim {
    pub id: TransferSegmentId,
    pub base: u32,
    pub end_exclusive: u32,
    pub sha256: String,
    pub provenance: String,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TransferProgramMetadata {
    pub caller: TransferSegmentClaim,
    pub below: Option<TransferSegmentClaim>,
    pub not_below: Option<TransferSegmentClaim>,
}

/// All bytes are immutable and private. This is not an arbitrary segment loader.
pub struct ClosedSyntheticTransferProgram {
    segments: Vec<(TransferSegmentClaim, ProgramSegment)>,
    composite_nodes: Vec<CompositeNodeIdentity>,
}
fn duplicate(segment: &ProgramSegment) -> ProgramSegment {
    ProgramSegment {
        base: segment.base,
        end: segment.end,
        bytes: segment.bytes.clone(),
        digest: segment.digest.clone(),
    }
}
impl ClosedSyntheticTransferProgram {
    pub fn admit_invented_profiles(
        composite: &super::ClosedCompositeProgram,
        caller: Vec<u8>,
        below: Option<Vec<u8>>,
        not_below: Option<Vec<u8>>,
        metadata: TransferProgramMetadata,
    ) -> Result<Self> {
        let admit = |id, base, actual: Vec<u8>, exact: &[u8], claim: TransferSegmentClaim| {
            let digest = crate::audit_sha256::digest(exact);
            let expected = TransferSegmentClaim {
                id,
                base,
                end_exclusive: base + exact.len() as u32,
                sha256: digest.clone(),
                provenance: PROVENANCE.into(),
            };
            if claim != expected || actual != exact {
                return Err(AuditError::new(
                    "TransferSegmentAdmissionMismatch",
                    Some(i64::from(base)),
                    "only exact independently frozen invented profile/base/end/content/provenance",
                ));
            }
            Ok((expected, ProgramSegment::new(base, actual, &digest)?))
        };
        let mut segments = vec![admit(
            TransferSegmentId::Caller,
            0x0ff0,
            caller,
            &[0x03, 0x00, 0x10],
            metadata.caller,
        )?];
        let composite_segment = composite.segment_copy();
        segments.push((
            TransferSegmentClaim {
                id: TransferSegmentId::Composite,
                base: 0x1000,
                end_exclusive: 0x1033,
                sha256: COMPOSITE_SHA256.into(),
                provenance: PROVENANCE.into(),
            },
            composite_segment,
        ));
        match (below, not_below, metadata.below, metadata.not_below) {
            (Some(b), Some(n), Some(bc), Some(nc)) => {
                segments.push(admit(
                    TransferSegmentId::BelowContinuation,
                    0x55c5,
                    b,
                    &[0x77, 0x00],
                    bc,
                )?);
                segments.push(admit(
                    TransferSegmentId::NotBelowContinuation,
                    0x5596,
                    n,
                    &[0x77, 0xa5],
                    nc,
                )?);
            }
            (None, None, None, None) => {}
            _ => {
                return Err(AuditError::new(
                    "IncompleteTransferProfiles",
                    None,
                    "both invented continuations or neither; no mutable replacement",
                ))
            }
        }
        for (index, (a, _)) in segments.iter().enumerate() {
            if segments[index + 1..]
                .iter()
                .any(|(b, _)| a.base < b.end_exclusive && b.base < a.end_exclusive)
            {
                return Err(AuditError::new(
                    "TransferSegmentOverlap",
                    None,
                    "disjoint checked extents only",
                ));
            }
        }
        Ok(Self {
            segments,
            composite_nodes: super::ClosedCompositeProgram::node_inventory(),
        })
    }
    pub fn profiles(&self) -> Vec<TransferSegmentClaim> {
        self.segments.iter().map(|(id, _)| id.clone()).collect()
    }
    pub(crate) fn caller_copy(&self) -> ProgramSegment {
        duplicate(&self.segments[0].1)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TransferJournalBoundary {
    pub program: usize,
    pub logical: usize,
    pub raw: usize,
    pub logical_writes: u64,
    pub raw_writes: u64,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TransferCounters {
    pub successful_retirements: u64,
    pub step_calls: u64,
    pub shared_execution_calls: u64,
    pub cpu_instructions: u64,
    pub cpu_cycles: u64,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TransferRecord {
    pub transition_ordinal: u64,
    pub source: TransferSegmentClaim,
    pub destination: TransferSegmentClaim,
    pub source_instruction_pc: u16,
    pub retired_instruction: StepOutcome,
    pub actual_target_pc: u16,
    pub architecture_sha256: String,
    pub data_sha256: String,
    pub journal: TransferJournalBoundary,
    pub counters: TransferCounters,
    pub provenance: String,
    pub classification: String,
}
/// Private owner identity is intentionally neither serialized nor reconstructed.
/// Borrowing the handle permits a genuine runtime reused-ticket refusal.
pub struct TransferTicket {
    pub(crate) owner: Arc<()>,
    pub(crate) record: TransferRecord,
}
impl TransferTicket {
    pub fn claim(&self) -> TransferRecord {
        self.record.clone()
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct TransferStepRecord {
    pub index: u64,
    pub stage: TransferStage,
    pub stage_index: u64,
    pub segment: TransferSegmentId,
    pub node_identity: String,
    pub form: CompositeForm,
    pub before: Snapshot,
    pub after: Snapshot,
    pub outcome: StepOutcome,
    pub program_span: [usize; 2],
    pub logical_span: [usize; 2],
    pub raw_span: [usize; 2],
    pub stage_relative_instructions: u64,
    pub stage_relative_cycles: u64,
}
#[derive(Debug, Clone, Serialize)]
pub struct TransferCommitRecord {
    pub transition: TransferRecord,
    pub observed: Snapshot,
    pub committed: bool,
    pub diagnostic_span: [usize; 2],
}
#[derive(Debug, Clone, Serialize)]
pub struct TransferStageStamp {
    pub ordinal: u64,
    pub stage: Option<TransferStage>,
    pub phase: String,
}
#[derive(Debug, Clone, Serialize)]
pub struct TransferJournalStages {
    pub program: Vec<TransferStageStamp>,
    pub logical: Vec<TransferStageStamp>,
    pub raw: Vec<TransferStageStamp>,
    pub diagnostic: Vec<TransferStageStamp>,
}
#[derive(Debug, Clone, Serialize)]
pub struct TransferRefusal {
    pub ordinal: u64,
    pub operation: String,
    pub error: AuditError,
}
#[derive(Debug, Clone, Serialize)]
pub struct TransferReport {
    pub mode: String,
    pub path: CompositePath,
    pub programs: Vec<TransferSegmentClaim>,
    pub stage: TransferStage,
    pub entry: Snapshot,
    pub current: Snapshot,
    pub steps: Vec<TransferStepRecord>,
    pub tickets: Vec<TransferRecord>,
    pub commits: Vec<TransferCommitRecord>,
    pub pending: Option<TransferRecord>,
    pub tickets_issued: u64,
    pub tickets_consumed: u64,
    pub tickets_refused: u64,
    pub ticket_refusals: Vec<TransferRefusal>,
    pub checkpoint: Option<u16>,
    pub completed: bool,
    pub composite_direct_j_count: u64,
    pub journal_stages: TransferJournalStages,
    pub audit: AuditReport,
}

pub(crate) fn architecture_digest(cpu: &CpuState) -> String {
    let psw = (cpu.psw_other & 0x0337)
        | 0x0cc8
        | ((cpu.dd as u16) << 12)
        | ((cpu.hc as u16) << 13)
        | ((cpu.zf as u16) << 14)
        | ((cpu.cf as u16) << 15);
    let mut bytes = b"M2brCpuStateV1\0".to_vec();
    for word in [cpu.pc, cpu.a, cpu.ssp, cpu.lrb, psw, cpu.psw_other] {
        bytes.extend_from_slice(&word.to_le_bytes());
    }
    bytes.extend([
        cpu.zf as u8,
        cpu.cf as u8,
        cpu.hc as u8,
        cpu.dd as u8,
        cpu.sf as u8,
        cpu.halted as u8,
    ]);
    bytes.extend_from_slice(&cpu.cycles.to_le_bytes());
    bytes.extend_from_slice(&cpu.instructions.to_le_bytes());
    crate::audit_sha256::digest(&bytes)
}
pub(crate) fn data_digest(snapshot: &Snapshot) -> Result<String> {
    if snapshot.ram_range != [0x80, 0x1000] || snapshot.ram.len() != 3968 {
        return Err(AuditError::new(
            "IncompleteTransferSnapshot",
            None,
            "all actual public RAM retained",
        ));
    }
    let mut bytes = b"M2brDataStateV1\0".to_vec();
    bytes.extend_from_slice(&0x80u16.to_le_bytes());
    bytes.extend_from_slice(&0x1000u16.to_le_bytes());
    bytes.extend_from_slice(&snapshot.ram);
    Ok(crate::audit_sha256::digest(&bytes))
}
pub(crate) fn same_record(a: &TransferRecord, b: &TransferRecord) -> bool {
    serde_json::to_vec(a).expect("closed serializable record")
        == serde_json::to_vec(b).expect("closed serializable record")
}

pub(crate) struct Pending {
    pub destination: TransferSegmentId,
    pub record: Option<TransferRecord>,
    pub issued: bool,
}
pub(crate) enum TransferRetirement {
    Continue,
    Pending(TransferSegmentId),
    Checkpoint,
    NoContinuation,
}
pub(crate) struct TransferState {
    pub owner: Arc<()>,
    pub segments: Vec<(TransferSegmentClaim, ProgramSegment)>,
    pub active: TransferSegmentId,
    pub stage: TransferStage,
    pub closed: ClosedState,
    pub composite_permissions: Permissions,
    pub empty_permissions: Permissions,
    pub entry: Snapshot,
    pub steps: Vec<TransferStepRecord>,
    pub pending: Option<Pending>,
    pub tickets: Vec<TransferRecord>,
    pub commits: Vec<TransferCommitRecord>,
    pub issued: u64,
    pub consumed: u64,
    pub refusals: Vec<TransferRefusal>,
    pub checkpoint: Option<u16>,
    pub stages: TransferJournalStages,
}
impl TransferState {
    pub(crate) fn new(
        program: &ClosedSyntheticTransferProgram,
        seeds: &CompositeSeeds,
        entry: Snapshot,
    ) -> Result<Self> {
        Ok(Self {
            owner: Arc::new(()),
            segments: program
                .segments
                .iter()
                .map(|(id, segment)| (id.clone(), duplicate(segment)))
                .collect(),
            active: TransferSegmentId::Caller,
            stage: TransferStage::Caller,
            closed: ClosedState {
                nodes: program.composite_nodes.clone(),
                path: seeds.path(),
                entry: entry.clone(),
                steps: vec![],
                direct_j_count: 0,
            },
            composite_permissions: seeds.permissions()?,
            empty_permissions: Permissions::new(vec![], vec![])?,
            entry,
            steps: vec![],
            pending: None,
            tickets: vec![],
            commits: vec![],
            issued: 0,
            consumed: 0,
            refusals: vec![],
            checkpoint: None,
            stages: TransferJournalStages {
                program: vec![],
                logical: vec![],
                raw: vec![],
                diagnostic: vec![],
            },
        })
    }
    pub(crate) fn segment(&self) -> &ProgramSegment {
        &self
            .segments
            .iter()
            .find(|(id, _)| id.id == self.active)
            .expect("admitted active segment")
            .1
    }
    pub(crate) fn identity(&self, id: TransferSegmentId) -> TransferSegmentClaim {
        self.segments
            .iter()
            .find(|(row, _)| row.id == id)
            .expect("admitted segment")
            .0
            .clone()
    }
    pub(crate) fn permissions(&self) -> &Permissions {
        if self.stage == TransferStage::Composite && self.pending.is_none() {
            &self.composite_permissions
        } else {
            &self.empty_permissions
        }
    }
    pub(crate) fn stamp(&self, ordinal: u64, phase: &str) -> TransferStageStamp {
        TransferStageStamp {
            ordinal,
            stage: (phase != "Setup").then_some(self.stage),
            phase: phase.into(),
        }
    }
    pub(crate) fn node(&self, pc: u16, dd: bool, retired: u64) -> Result<CompositeNodeIdentity> {
        if self.pending.is_some() {
            return Err(AuditError::new(
                "TransferPending",
                Some(i64::from(pc)),
                "no instruction before single-use ticket commit",
            ));
        }
        if self.stage == TransferStage::Composite {
            return self.closed.node(
                pc,
                dd,
                retired.checked_sub(1).ok_or_else(|| {
                    AuditError::new("TransferCounterMismatch", None, "caller prefix retained")
                })?,
            );
        }
        let (expected_pc, id, form, operand, next, page, pattern, index) =
            if self.stage == TransferStage::Caller {
                if retired != 0 {
                    return Err(AuditError::new(
                        "UnexpectedCallerRetirement",
                        None,
                        "one actual caller J",
                    ));
                }
                (
                    0x0ff0,
                    "InventedCaller_J1000",
                    CompositeForm::JAddress,
                    CompositeOperand::Target(0x1000),
                    0x1000,
                    116,
                    vec!["03", "addrl", "addrh"],
                    684,
                )
            } else {
                if retired != self.closed.path.pcs().len() as u64 + 1 || dd {
                    return Err(AuditError::new(
                        "WrongContinuationContext",
                        None,
                        "unchanged actual composite exit and DD0",
                    ));
                }
                let base = self.segment().base as u16;
                (
                    base,
                    if self.active == TransferSegmentId::BelowContinuation {
                        "InventedBelow_LB00"
                    } else {
                        "InventedNotBelow_LBA5"
                    },
                    CompositeForm::LbAImm8,
                    CompositeOperand::Immediate8(
                        if self.active == TransferSegmentId::BelowContinuation {
                            0
                        } else {
                            0xa5
                        },
                    ),
                    base + 2,
                    124,
                    vec!["77", "N8"],
                    738,
                )
            };
        if pc != expected_pc {
            return Err(AuditError::new(
                "UnknownTransferNode",
                Some(i64::from(pc)),
                "closed actual stage PC only",
            ));
        }
        let node = CompositeNodeIdentity {
            pc,
            node_identity: id.into(),
            form,
            length: pattern.len(),
            architectural_dd: vec![false, true],
            reachable_dd: if self.stage == TransferStage::Caller {
                vec![false, true]
            } else {
                vec![false]
            },
            operands: if form == CompositeForm::LbAImm8 {
                vec![CompositeOperand::Accumulator, operand]
            } else {
                vec![operand]
            },
            successors: vec![next],
            primary_pdf_page: page,
            primary_pattern: pattern.into_iter().map(str::to_string).collect(),
            manual_sha256: MANUAL.into(),
            source_identity: "M2brInventedOnlyPrimaryProfiles".into(),
            source_sha256: self.segment().sha256().into(),
        };
        debug_assert_eq!(node.instruction(dd).index, index);
        Ok(node)
    }
    pub(crate) fn retirement(
        &mut self,
        origin: u16,
        pc: u16,
        retired: u64,
        external: Option<u16>,
        selected_index: usize,
    ) -> Result<TransferRetirement> {
        let index = match self.stage {
            TransferStage::Caller => 684,
            TransferStage::Continuation => 738,
            TransferStage::Composite => {
                self.closed
                    .nodes
                    .iter()
                    .find(|node| node.pc == origin)
                    .ok_or_else(|| {
                        AuditError::new(
                            "UnknownTransferNode",
                            Some(i64::from(origin)),
                            "actual selected retirement origin",
                        )
                    })?
                    .instruction(false)
                    .index
            }
        };
        if selected_index != index {
            return Err(AuditError::new(
                "TransferRetirementFormMismatch",
                Some(i64::from(origin)),
                "actual selected form cannot be replaced by a target-PC match",
            ));
        }
        match self.stage {
            TransferStage::Caller
                if origin == 0x0ff0 && retired == 0 && pc == 0x1000 && external == Some(0x1000) =>
            {
                Ok(TransferRetirement::Pending(TransferSegmentId::Composite))
            }
            TransferStage::Composite => {
                let relative = retired.checked_sub(1).ok_or_else(|| {
                    AuditError::new("TransferCounterMismatch", None, "caller prefix")
                })?;
                let terminal = self.closed.successor(origin, pc, relative)?;
                if external != terminal.then_some(pc) {
                    return Err(AuditError::new(
                        "TransferJAuthorityMismatch",
                        Some(i64::from(pc)),
                        "actual terminal J only",
                    ));
                }
                if !terminal {
                    return Ok(TransferRetirement::Continue);
                }
                self.closed.direct_j_count += 1;
                let destination = if self.closed.path == CompositePath::A {
                    TransferSegmentId::BelowContinuation
                } else {
                    TransferSegmentId::NotBelowContinuation
                };
                if self.segments.iter().any(|(id, _)| id.id == destination) {
                    Ok(TransferRetirement::Pending(destination))
                } else {
                    Ok(TransferRetirement::NoContinuation)
                }
            }
            TransferStage::Continuation
                if origin == self.segment().base as u16
                    && pc == origin + 2
                    && external.is_none()
                    && retired == self.closed.path.pcs().len() as u64 + 1 =>
            {
                self.checkpoint = Some(pc);
                Ok(TransferRetirement::Checkpoint)
            }
            _ => Err(AuditError::new(
                "UnknownTransferSuccessor",
                Some(i64::from(pc)),
                "no non-J authority, extra step or caller target",
            )),
        }
    }
}

impl Session {
    pub fn new_closed_transfer(
        program: &ClosedSyntheticTransferProgram,
        cpu: Cpu,
        full_psw: u16,
        seeds: CompositeSeeds,
        budget: u8,
    ) -> Result<Self> {
        super::validate_psw(full_psw)?;
        if cpu.pc != 0x0ff0
            || cpu.lrb != 0x21
            || cpu.cycles != 0
            || cpu.instructions != 0
            || cpu.halted
            || cpu.psw_u16() != full_psw
            || cpu.psw_other & !0x0337 != 0
            || budget == 0
            || budget > 18
        {
            return Err(AuditError::new(
                "InvalidTransferEntry",
                Some(i64::from(cpu.pc)),
                "fresh invented caller PC/counters; exact representable context; budget1..18",
            ));
        }
        let mut bus = Bus::new(Vec::new(), 0xa5);
        bus.audit = Some(AuditBus::new(
            program.caller_copy(),
            Permissions::new(vec![], vec![])?,
            cpu.pc,
            budget,
        ));
        let mut session = Self { cpu, bus };
        for (address, value) in seeds.transfer_data() {
            session.seed_byte(*address, *value)?;
        }
        for (bank, words) in seeds.transfer_pointing().iter().enumerate() {
            for (slot, value) in words.iter().enumerate() {
                session.seed_word(0x80 + bank as u16 * 8 + slot as u16 * 2, *value)?;
            }
        }
        let entry = session.diagnostic_snapshot()?;
        session
            .bus
            .audit
            .as_ref()
            .expect("installed")
            .install_transfer(TransferState::new(program, &seeds, entry)?)?;
        session.begin_functional()?;
        Ok(session)
    }
    pub fn step_transfer(&mut self) -> Result<TransferStepRecord> {
        let audit = self.bus.audit.as_ref().expect("installed");
        let node = audit
            .transfer_node(self.cpu.pc, self.cpu.dd)
            .map_err(|e| audit.reject_step_attempt(e))?;
        let before = self.diagnostic_snapshot()?;
        let outcome = self.checked_step(&node.instruction(self.cpu.dd))?;
        let after = self.diagnostic_snapshot()?;
        self.bus
            .audit
            .as_ref()
            .expect("installed")
            .record_transfer_step(node, before, after, outcome)
    }
    pub fn take_transfer_ticket(&mut self) -> Result<TransferTicket> {
        self.bus
            .audit
            .as_ref()
            .expect("installed")
            .take_transfer_ticket()
    }
    pub fn commit_transfer(
        &mut self,
        ticket: &TransferTicket,
        claim: &TransferRecord,
    ) -> Result<TransferCommitRecord> {
        let observed = self.diagnostic_snapshot()?;
        self.bus
            .audit
            .as_ref()
            .expect("installed")
            .commit_transfer(ticket, claim, observed)
    }
    pub fn transfer_report(&mut self) -> Result<TransferReport> {
        self.bus
            .audit
            .as_ref()
            .expect("installed")
            .require_transfer()?;
        let current = self.diagnostic_snapshot()?;
        self.bus
            .audit
            .as_ref()
            .expect("installed")
            .transfer_report(current)
    }
}
