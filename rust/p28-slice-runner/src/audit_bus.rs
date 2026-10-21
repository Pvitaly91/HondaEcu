//! Opt-in state owned by the production Bus. No instruction semantics live here.
use crate::audit::composite::{
    ClosedState, CompositeNodeIdentity, CompositeReport, CompositeStepOutcome, COMPOSITE_SHA256,
    INVENTORY,
};
use crate::audit::transfer::{
    self, Pending, TransferCommitRecord, TransferCounters, TransferJournalBoundary, TransferRecord,
    TransferRefusal, TransferReport, TransferRetirement, TransferStage, TransferState,
    TransferStepRecord, TransferTicket,
};
use crate::audit::{
    Access, AuditError, AuditReport, DataAdmissionRefusal, DataEvent, DiagnosticEvent, Permissions,
    ProgramEvent, ProgramSegment, RawDataEvent, Result,
};
use crate::audit::{Snapshot, StepOutcome};
use std::cell::RefCell;
use std::sync::Arc;

#[cfg(test)]
#[path = "audit_composite_tests.rs"]
mod composite_tests;

#[cfg(test)]
#[path = "audit_transfer_tests.rs"]
mod transfer_tests;

#[derive(Clone, Copy)]
pub(crate) struct DataToken {
    index: usize,
    root: bool,
}
#[derive(Clone, Copy)]
pub(crate) struct RawToken {
    index: usize,
}
struct State {
    entry_pc: u16,
    current_pc: u16,
    phase: &'static str,
    pc: Option<u16>,
    instruction: Option<usize>,
    selected_len: Option<usize>,
    selected_reads: usize,
    program_start: usize,
    data_start: usize,
    raw_start: usize,
    composite: Option<ClosedState>,
    transfer: Option<TransferState>,
    program: Vec<ProgramEvent>,
    data: Vec<DataEvent>,
    raw: Vec<RawDataEvent>,
    diagnostics: Vec<DiagnosticEvent>,
    data_admission_refusals: Vec<DataAdmissionRefusal>,
    active_data: Option<usize>,
    seeded: Vec<u16>,
    pending_seed: Option<Access>,
    budget: u8,
    step_calls: u64,
    execution_calls: u64,
    retirements: u64,
    write_ordinal: u64,
    raw_write_ordinal: u64,
    sealed: bool,
    terminal_reason: Option<String>,
    external_exit: Option<u16>,
    fault: Option<AuditError>,
}
pub(crate) struct AuditBus {
    segment: ProgramSegment,
    permissions: Permissions,
    state: RefCell<State>,
}
impl AuditBus {
    pub(crate) fn new(
        segment: ProgramSegment,
        permissions: Permissions,
        entry: u16,
        budget: u8,
    ) -> Self {
        Self {
            segment,
            permissions,
            state: RefCell::new(State {
                entry_pc: entry,
                current_pc: entry,
                phase: "Setup",
                pc: Some(entry),
                instruction: None,
                selected_len: None,
                selected_reads: 0,
                program_start: 0,
                data_start: 0,
                raw_start: 0,
                composite: None,
                transfer: None,
                program: vec![],
                data: vec![],
                raw: vec![],
                diagnostics: vec![],
                data_admission_refusals: vec![],
                active_data: None,
                seeded: vec![],
                pending_seed: None,
                budget,
                step_calls: 0,
                execution_calls: 0,
                retirements: 0,
                write_ordinal: 0,
                raw_write_ordinal: 0,
                sealed: false,
                terminal_reason: None,
                external_exit: None,
                fault: None,
            }),
        }
    }
    pub(crate) fn install_closed(&self, closed: ClosedState) -> Result<()> {
        let mut state = self.state.borrow_mut();
        let result = (|| {
            Self::readiness(&state)?;
            let mut expected = INVENTORY.to_vec();
            expected.extend(0x80..0xc0);
            expected.sort_unstable();
            let mut actual = state.seeded.clone();
            actual.sort_unstable();
            if state.phase != "Setup"
                || state.composite.is_some()
                || state.transfer.is_some()
                || state.pending_seed.is_some()
                || state.active_data.is_some()
                || self.segment.base != 0x1000
                || self.segment.end != 0x1033
                || self.segment.digest != COMPOSITE_SHA256
                || actual != expected
                || state.step_calls != 0
                || state.execution_calls != 0
                || state.retirements != 0
            {
                return Err(AuditError::new(
                    "InvalidCompositeInstallation",
                    None,
                    "closed segment and exactly one complete DATA initialization before Functional",
                ));
            }
            state.composite = Some(closed);
            Ok(())
        })();
        result.map_err(|error| Self::latch(&mut state, error))
    }
    pub(crate) fn require_closed(&self) -> Result<()> {
        if self.state.borrow().composite.is_none() {
            return Err(AuditError::new(
                "WrongCompositeApi",
                None,
                "explicit closed constructor required",
            ));
        }
        Ok(())
    }
    pub(crate) fn install_transfer(&self, mut transfer: TransferState) -> Result<()> {
        let mut state = self.state.borrow_mut();
        let result = (|| {
            Self::readiness(&state)?;
            let mut expected = INVENTORY.to_vec();
            expected.extend(0x80..0xc0);
            expected.sort_unstable();
            let mut actual = state.seeded.clone();
            actual.sort_unstable();
            if state.phase != "Setup"
                || state.composite.is_some()
                || state.transfer.is_some()
                || state.pending_seed.is_some()
                || state.active_data.is_some()
                || self.segment.base != 0x0ff0
                || self.segment.end != 0x0ff3
                || actual != expected
                || !state.program.is_empty()
                || state.step_calls != 0
                || state.execution_calls != 0
                || state.retirements != 0
                || state.data.len() != 48
                || state.raw.len() != 80
                || state
                    .data
                    .iter()
                    .any(|event| event.phase != "Seed" || !event.serviced)
                || state.raw.iter().any(|event| !event.serviced)
            {
                return Err(AuditError::new(
                    "InvalidTransferInstallation",
                    None,
                    "one complete actual DATA initialization; no PROGRAM acquisition or execution",
                ));
            }
            // These are parallel attribution rows for already-retained real Setup
            // events. They neither acquire bytes nor manufacture service events.
            transfer.stages.logical = state
                .data
                .iter()
                .map(|event| transfer.stamp(event.ordinal, "Setup"))
                .collect();
            transfer.stages.raw = state
                .raw
                .iter()
                .map(|event| transfer.stamp(event.ordinal, "Setup"))
                .collect();
            transfer.stages.diagnostic = state
                .diagnostics
                .iter()
                .map(|event| transfer.stamp(event.ordinal, "Setup"))
                .collect();
            state.transfer = Some(transfer);
            Ok(())
        })();
        result.map_err(|error| Self::latch(&mut state, error))
    }
    pub(crate) fn require_transfer(&self) -> Result<()> {
        if self.state.borrow().transfer.is_none() {
            return Err(AuditError::new(
                "WrongTransferApi",
                None,
                "explicit closed transfer constructor required",
            ));
        }
        Ok(())
    }
    pub(crate) fn transfer_node(&self, pc: u16, dd: bool) -> Result<CompositeNodeIdentity> {
        let state = self.state.borrow();
        Self::readiness(&state)?;
        state
            .transfer
            .as_ref()
            .ok_or_else(|| {
                AuditError::new(
                    "WrongTransferApi",
                    None,
                    "explicit closed transfer constructor required",
                )
            })?
            .node(pc, dd, state.retirements)
    }
    fn transfer_boundary(state: &State) -> TransferJournalBoundary {
        TransferJournalBoundary {
            program: state.program.len(),
            logical: state.data.len(),
            raw: state.raw.len(),
            logical_writes: state.write_ordinal,
            raw_writes: state.raw_write_ordinal,
        }
    }
    fn transfer_counters(state: &State, snapshot: &Snapshot) -> TransferCounters {
        TransferCounters {
            successful_retirements: state.retirements,
            step_calls: state.step_calls,
            shared_execution_calls: state.execution_calls,
            cpu_instructions: snapshot.cpu.instructions,
            cpu_cycles: snapshot.cpu.cycles,
        }
    }
    pub(crate) fn record_transfer_step(
        &self,
        node: CompositeNodeIdentity,
        before: Snapshot,
        after: Snapshot,
        outcome: StepOutcome,
    ) -> Result<TransferStepRecord> {
        let mut state = self.state.borrow_mut();
        let boundary = Self::transfer_boundary(&state);
        let counters = Self::transfer_counters(&state, &after);
        let program_span = [state.program_start, state.program.len()];
        let logical_span = [state.data_start, state.data.len()];
        let raw_span = [state.raw_start, state.raw.len()];
        let retired = state.retirements;
        let result = (|| {
            if let Some(error) = &state.fault {
                return Err(error.clone());
            }
            let t = state.transfer.as_mut().ok_or_else(|| {
                AuditError::new("WrongTransferApi", None, "actual transfer record required")
            })?;
            if t.steps.len() as u64 + 1 != retired
                || !outcome.retired
                || after.cpu.instructions != retired
            {
                return Err(AuditError::new(
                    "TransferRecordOrderMismatch",
                    None,
                    "one actual record per real retirement",
                ));
            }
            let stage_entry = if t.stage == TransferStage::Caller {
                &t.entry
            } else {
                &t.commits
                    .last()
                    .ok_or_else(|| {
                        AuditError::new(
                            "TransferCommitMissing",
                            None,
                            "actual committed stage prefix",
                        )
                    })?
                    .observed
            };
            let stage_relative_instructions = after
                .cpu
                .instructions
                .checked_sub(stage_entry.cpu.instructions)
                .ok_or_else(|| {
                    AuditError::new(
                        "TransferCounterMismatch",
                        None,
                        "monotone CPU instruction prefix",
                    )
                })?;
            let stage_relative_cycles = after
                .cpu
                .cycles
                .checked_sub(stage_entry.cpu.cycles)
                .ok_or_else(|| {
                    AuditError::new(
                        "TransferCounterMismatch",
                        None,
                        "monotone CPU source cycle prefix",
                    )
                })?;
            let record = TransferStepRecord {
                index: retired,
                stage: t.stage,
                stage_index: stage_relative_instructions,
                segment: t.active,
                node_identity: node.node_identity,
                form: node.form,
                before,
                after: after.clone(),
                outcome: outcome.clone(),
                program_span,
                logical_span,
                raw_span,
                stage_relative_instructions,
                stage_relative_cycles,
            };
            if t.pending.is_some() {
                if outcome.decoded_index != 684
                    || outcome.len != 3
                    || outcome.external_exit != Some(after.cpu.pc)
                    || outcome.pc_after != after.cpu.pc
                    || t.pending.as_ref().expect("pending").record.is_some()
                {
                    return Err(AuditError::new(
                        "TransferTicketRequiresActualJ",
                        None,
                        "only the just-retired actual direct J mints authority",
                    ));
                }
                let destination = t.pending.as_ref().expect("pending").destination;
                let ticket = TransferRecord {
                    transition_ordinal: t.tickets.len() as u64,
                    source: t.identity(t.active),
                    destination: t.identity(destination),
                    source_instruction_pc: outcome.pc_before,
                    retired_instruction: outcome,
                    actual_target_pc: after.cpu.pc,
                    architecture_sha256: transfer::architecture_digest(&after.cpu),
                    data_sha256: transfer::data_digest(&after)?,
                    journal: boundary,
                    counters,
                    provenance: "InventedOnly_NoNativeGenerationOwner".into(),
                    classification: "ResearchOnly_ActualDirectJRetired_TransferPending".into(),
                };
                t.pending.as_mut().expect("pending").record = Some(ticket.clone());
                t.tickets.push(ticket);
            }
            t.steps.push(record.clone());
            Ok(record)
        })();
        result.map_err(|error| Self::latch(&mut state, error))
    }
    fn transfer_refusal(state: &mut State, operation: &str, error: AuditError) -> AuditError {
        let error = Self::latch(state, error);
        if let Some(t) = state.transfer.as_mut() {
            t.refusals.push(TransferRefusal {
                ordinal: t.refusals.len() as u64,
                operation: operation.into(),
                error: error.clone(),
            });
        }
        error
    }
    pub(crate) fn take_transfer_ticket(&self) -> Result<TransferTicket> {
        let mut state = self.state.borrow_mut();
        let result = (|| {
            if let Some(error) = &state.fault {
                return Err(error.clone());
            }
            if state.sealed {
                return Err(AuditError::new(
                    "SessionSealed",
                    None,
                    "no authority after terminal seal",
                ));
            }
            if state.phase != "TransferPending" {
                return Err(AuditError::new(
                    "TransferNotPending",
                    None,
                    "actual direct J must retire first",
                ));
            }
            let t = state.transfer.as_mut().ok_or_else(|| {
                AuditError::new(
                    "WrongTransferApi",
                    None,
                    "closed transfer constructor required",
                )
            })?;
            let pending = t.pending.as_mut().ok_or_else(|| {
                AuditError::new(
                    "TransferNotPending",
                    None,
                    "actual direct J must retire first",
                )
            })?;
            if pending.issued {
                return Err(AuditError::new(
                    "TransferTicketAlreadyIssued",
                    None,
                    "one opaque handle for each pending edge",
                ));
            }
            let record = pending.record.clone().ok_or_else(|| {
                AuditError::new(
                    "TransferRecordMissing",
                    None,
                    "actual J report must complete",
                )
            })?;
            pending.issued = true;
            t.issued += 1;
            Ok(TransferTicket {
                owner: Arc::clone(&t.owner),
                record,
            })
        })();
        result.map_err(|error| Self::transfer_refusal(&mut state, "TakeTicket", error))
    }
    pub(crate) fn commit_transfer(
        &self,
        ticket: &TransferTicket,
        claim: &TransferRecord,
        observed: Snapshot,
    ) -> Result<TransferCommitRecord> {
        let mut state = self.state.borrow_mut();
        let boundary = Self::transfer_boundary(&state);
        let counters = Self::transfer_counters(&state, &observed);
        let diagnostic_span = [
            state.diagnostics.len().saturating_sub(1),
            state.diagnostics.len(),
        ];
        let result = (|| {
            if let Some(error) = &state.fault {
                return Err(error.clone());
            }
            let sealed = state.sealed;
            let phase = state.phase;
            let t = state.transfer.as_mut().ok_or_else(|| {
                AuditError::new(
                    "WrongTransferApi",
                    None,
                    "closed transfer constructor required",
                )
            })?;
            if !Arc::ptr_eq(&ticket.owner, &t.owner) {
                return Err(AuditError::new(
                    "CrossSessionTransferTicket",
                    None,
                    "opaque owner authority never comes from a serialized claim",
                ));
            }
            if ticket.record.transition_ordinal < t.consumed {
                return Err(AuditError::new(
                    "TransferTicketAlreadyConsumed",
                    None,
                    "single-use pending authority",
                ));
            }
            if sealed {
                return Err(AuditError::new(
                    "SessionSealed",
                    None,
                    "no authority after terminal seal",
                ));
            }
            if phase != "TransferPending" {
                return Err(AuditError::new(
                    "TransferNotPending",
                    None,
                    "actual direct J must retire first",
                ));
            }
            let pending = t.pending.as_ref().ok_or_else(|| {
                AuditError::new(
                    "TransferNotPending",
                    None,
                    "actual direct J must retire first",
                )
            })?;
            let record = pending.record.as_ref().ok_or_else(|| {
                AuditError::new(
                    "TransferRecordMissing",
                    None,
                    "actual J report must complete",
                )
            })?;
            if !pending.issued {
                return Err(AuditError::new(
                    "TransferTicketNotIssued",
                    None,
                    "take the opaque pending handle before commit",
                ));
            }
            if !transfer::same_record(&ticket.record, record)
                || !transfer::same_record(claim, record)
            {
                return Err(AuditError::new(
                    "TransferClaimMismatch",
                    None,
                    "all immutable owner-bound actual J/state/journal/counter fields must agree",
                ));
            }
            if transfer::architecture_digest(&observed.cpu) != record.architecture_sha256
                || transfer::data_digest(&observed)? != record.data_sha256
                || boundary != record.journal
                || counters != record.counters
                || observed.cpu.pc != record.actual_target_pc
                || record.destination.base != u32::from(observed.cpu.pc)
            {
                return Err(AuditError::new("TransferLiveStateMismatch",None,"commit observes the identical live CPU/RAM/counters/functional journal boundary"));
            }
            let transition = record.clone();
            let destination = pending.destination;
            // Select only the already-admitted immutable mapping. PC and CPU,
            // RAM, execution counters, flags and journals are never assigned.
            t.active = destination;
            t.stage = if destination == crate::audit::transfer::TransferSegmentId::Composite {
                TransferStage::Composite
            } else {
                TransferStage::Continuation
            };
            if t.stage == TransferStage::Composite {
                t.closed.entry = observed.clone();
            }
            t.pending = None;
            t.consumed += 1;
            let result = TransferCommitRecord {
                transition,
                observed,
                committed: true,
                diagnostic_span,
            };
            t.commits.push(result.clone());
            state.phase = "Functional";
            state.external_exit = None;
            state.terminal_reason = None;
            Ok(result)
        })();
        result.map_err(|error| Self::transfer_refusal(&mut state, "CommitTicket", error))
    }
    pub(crate) fn transfer_report(&self, current: Snapshot) -> Result<TransferReport> {
        let audit = self.report();
        let state = self.state.borrow();
        let t = state.transfer.as_ref().ok_or_else(|| {
            AuditError::new("WrongTransferApi", None, "closed transfer report required")
        })?;
        Ok(TransferReport {
            mode: "ClosedInventedCallerCompositeContinuation".into(),
            path: t.closed.path,
            programs: t
                .segments
                .iter()
                .map(|(identity, _)| identity.clone())
                .collect(),
            stage: t.stage,
            entry: t.entry.clone(),
            current,
            steps: t.steps.clone(),
            tickets: t.tickets.clone(),
            commits: t.commits.clone(),
            pending: t.pending.as_ref().and_then(|p| p.record.clone()),
            tickets_issued: t.issued,
            tickets_consumed: t.consumed,
            tickets_refused: t.refusals.len() as u64,
            ticket_refusals: t.refusals.clone(),
            checkpoint: t.checkpoint,
            completed: state.sealed
                && state.fault.is_none()
                && t.checkpoint.is_some()
                && t.consumed == 2
                && t.closed.direct_j_count == 1
                && state.retirements == t.closed.path.pcs().len() as u64 + 2
                && t.steps.len() as u64 == state.retirements,
            composite_direct_j_count: t.closed.direct_j_count,
            journal_stages: t.stages.clone(),
            audit,
        })
    }
    pub(crate) fn admit_legacy_step(&self) -> Result<()> {
        if self.state.borrow().transfer.is_some() {
            return Err(self.reject_step_attempt(AuditError::new(
                "WrongTransferApi",
                None,
                "old one-step API cannot enter a closed transfer",
            )));
        }
        let closed_mode = self.state.borrow().composite.is_some();
        if closed_mode {
            return Err(self.reject_step_attempt(AuditError::new(
                "WrongCompositeApi",
                None,
                "caller-selected one-step API cannot enter a closed composite",
            )));
        }
        Ok(())
    }
    pub(crate) fn reject_step_attempt(&self, error: AuditError) -> AuditError {
        let mut state = self.state.borrow_mut();
        state.step_calls += 1;
        Self::latch(&mut state, error)
    }
    pub(crate) fn closed_node(&self, pc: u16, dd: bool) -> Result<CompositeNodeIdentity> {
        let state = self.state.borrow();
        Self::readiness(&state)?;
        state
            .composite
            .as_ref()
            .ok_or_else(|| {
                AuditError::new(
                    "WrongCompositeApi",
                    None,
                    "explicit closed constructor required",
                )
            })?
            .node(pc, dd, state.retirements)
    }
    pub(crate) fn record_closed_step(
        &self,
        node: CompositeNodeIdentity,
        before: Snapshot,
        after: Snapshot,
        outcome: StepOutcome,
    ) -> Result<CompositeStepOutcome> {
        let mut state = self.state.borrow_mut();
        let record = CompositeStepOutcome {
            index: state.retirements,
            node_identity: node.node_identity,
            form: node.form,
            before,
            after,
            outcome,
            program_span: [state.program_start, state.program.len()],
            logical_span: [state.data_start, state.data.len()],
            raw_span: [state.raw_start, state.raw.len()],
        };
        let retired = state.retirements;
        let closed = state.composite.as_mut().ok_or_else(|| {
            AuditError::new(
                "WrongCompositeApi",
                None,
                "closed record requires explicit mode",
            )
        })?;
        if closed.steps.len() as u64 + 1 != retired {
            return Err(Self::latch(
                &mut state,
                AuditError::new(
                    "CompositeRecordOrderMismatch",
                    None,
                    "one actual successful record per retirement",
                ),
            ));
        }
        closed.steps.push(record.clone());
        Ok(record)
    }
    pub(crate) fn closed_report(&self, current: Snapshot) -> Result<CompositeReport> {
        let audit = self.report();
        let state = self.state.borrow();
        let closed = state.composite.as_ref().ok_or_else(|| {
            AuditError::new(
                "WrongCompositeApi",
                None,
                "closed report requires explicit mode",
            )
        })?;
        Ok(CompositeReport {
            mode: "ClosedM2bjComposite".into(),
            program_node_count: closed.nodes.len(),
            path: closed.path,
            entry: closed.entry.clone(),
            current,
            steps: closed.steps.clone(),
            direct_j_count: closed.direct_j_count,
            completed: state.sealed
                && state.fault.is_none()
                && closed.direct_j_count == 1
                && state.external_exit == Some(closed.path.terminal())
                && state.retirements as usize == closed.path.pcs().len()
                && closed.steps.len() as u64 == state.retirements,
            audit,
        })
    }
    fn latch(state: &mut State, error: AuditError) -> AuditError {
        if state.fault.is_none() {
            state.fault = Some(error);
        }
        state.fault.clone().expect("latched")
    }
    fn readiness(state: &State) -> Result<()> {
        if let Some(error) = &state.fault {
            return Err(error.clone());
        }
        if state.phase == "TransferPending" {
            return Err(AuditError::new(
                "TransferPending",
                None,
                "PROGRAM/DATA/execution/reseed denied before ticket commit",
            ));
        }
        if state.sealed {
            return Err(AuditError::new(
                "SessionSealed",
                None,
                "no functional or PROGRAM access after terminal seal",
            ));
        }
        Ok(())
    }
    pub(crate) fn fault(&self) -> Option<AuditError> {
        self.state.borrow().fault.clone()
    }
    pub(crate) fn external_target(&self, pc: u16) -> Option<u16> {
        if let Some(transfer) = &self.state.borrow().transfer {
            return (!transfer.segment().contains_address(pc)).then_some(pc);
        }
        (!self.segment.contains_address(pc)).then_some(pc)
    }
    pub(crate) fn latch_fault(&self, error: AuditError) -> AuditError {
        Self::latch(&mut self.state.borrow_mut(), error)
    }
    pub(crate) fn production_fault(&self, space: &str, address: u32, operation: &str) {
        self.latch_fault(AuditError::new(
            "ProductionMemoryFault",
            Some(i64::from(address)),
            format!("{space}: {operation}"),
        ));
    }
    pub(crate) fn admit_seed(&self, address: u16, width: u8) -> Result<()> {
        let mut state = self.state.borrow_mut();
        let access = Access { address, width };
        let result = (|| {
            Self::readiness(&state)?;
            if state.phase != "Setup" || state.pending_seed.is_some() {
                return Err(AuditError::new(
                    "SeedOutsideSetup",
                    Some(i64::from(address)),
                    "single initialization phase only",
                ));
            }
            let bytes = access.addresses()?;
            if bytes
                .iter()
                .any(|a| !(0x80..0x1000).contains(a) || state.seeded.contains(a))
            {
                return Err(AuditError::new(
                    "InvalidOrRepeatedSeed",
                    Some(i64::from(address)),
                    "RAM only, each constituent initialized at most once",
                ));
            }
            state.seeded.extend(bytes);
            state.pending_seed = Some(access);
            Ok(())
        })();
        result.map_err(|error| Self::latch(&mut state, error))
    }
    pub(crate) fn begin_functional(&self) -> Result<()> {
        let mut state = self.state.borrow_mut();
        let result = (|| {
            Self::readiness(&state)?;
            if state.phase != "Setup" || state.pending_seed.is_some() || state.active_data.is_some()
            {
                return Err(AuditError::new(
                    "InvalidPhaseTransition",
                    None,
                    "Setup to Functional occurs exactly once",
                ));
            }
            state.phase = "Functional";
            Ok(())
        })();
        result.map_err(|error| Self::latch(&mut state, error))
    }
    pub(crate) fn begin_capability(
        &self,
        address: u16,
        width: u8,
        write: bool,
        value: Option<u16>,
    ) -> Result<()> {
        let mut state = self.state.borrow_mut();
        let result = Self::readiness(&state).and_then(|()| {
            if state.phase != "Functional" {
                return Err(AuditError::new(
                    "DataOutsideFunctionalPhase",
                    None,
                    "explicit capability DATA call",
                ));
            }
            if state.transfer.is_some() {
                return Err(AuditError::new("TransferCapabilityDataDenied", Some(i64::from(address)), "only actual stage instructions may access DATA"));
            }
            if state.composite.is_some() {
                return Err(AuditError::new(
                    "CompositeCapabilityDataDenied", Some(i64::from(address)),
                    "closed DATA access must arise only from the actual selected production instruction",
                ));
            }
            if !matches!(width, 8 | 16)
                || write && (value.is_none() || width == 8 && value.is_some_and(|v| v > 255))
            {
                return Err(AuditError::new(
                    if write {
                        "InvalidDataWidthOrValue"
                    } else {
                        "InvalidDataWidth"
                    },
                    Some(i64::from(address)),
                    if write {
                        "capability write"
                    } else {
                        "capability read"
                    },
                ));
            }
            Ok(())
        });
        if let Err(error) = result {
            let error = Self::latch(&mut state, error);
            let ordinal = state.data_admission_refusals.len() as u64;
            let phase = state.phase.into();
            let pc = state.current_pc;
            state.data_admission_refusals.push(DataAdmissionRefusal {
                ordinal,
                classification: "PreBusApiAdmissionRefusal".into(),
                phase,
                pc,
                address,
                width,
                operation: if write { "Write" } else { "Read" }.into(),
                requested_value: value,
                production_bus_called: false,
                serviced: false,
                refusal: error.clone(),
            });
            return Err(error);
        }
        Ok(())
    }
    pub(crate) fn begin_step(&self, pc: u16) -> Result<()> {
        let mut state = self.state.borrow_mut();
        state.step_calls += 1;
        let result = (|| {
            Self::readiness(&state)?;
            if state.phase != "Functional" || state.active_data.is_some() {
                return Err(AuditError::new(
                    "StepOutsideFunctionalPhase",
                    Some(i64::from(pc)),
                    "no reentrant step or setup execution",
                ));
            }
            if state.retirements >= u64::from(state.budget) {
                return Err(AuditError::new(
                    "InstructionBudgetExceeded",
                    Some(i64::from(pc)),
                    "bounded before decoder invocation",
                ));
            }
            let segment = state
                .transfer
                .as_ref()
                .map_or(&self.segment, |t| t.segment());
            if u32::from(pc) < segment.base || u32::from(pc) >= segment.end {
                return Err(AuditError::new(
                    "EntryOutsideSegment",
                    Some(i64::from(pc)),
                    "no fetch before checked entry",
                ));
            }
            state.program_start = state.program.len();
            state.data_start = state.data.len();
            state.raw_start = state.raw.len();
            state.phase = "Executing";
            state.pc = Some(pc);
            state.current_pc = pc;
            state.instruction = None;
            state.selected_len = None;
            state.selected_reads = 0;
            Ok(())
        })();
        result.map_err(|error| Self::latch(&mut state, error))
    }
    pub(crate) fn program_read(&self, address: i64, purpose: &str) -> Result<u8> {
        let mut state = self.state.borrow_mut();
        let (base, end) = state
            .transfer
            .as_ref()
            .map_or((self.segment.base, self.segment.end), |t| {
                (t.segment().base, t.segment().end)
            });
        let offset = u32::try_from(address)
            .ok()
            .filter(|a| *a >= base && *a < end)
            .map(|a| a - base);
        let instruction_offset = state
            .pc
            .and_then(|pc| address.checked_sub(i64::from(pc)))
            .and_then(|v| u32::try_from(v).ok());
        // Append the real attempt before validating/acquiring a byte. Completion
        // annotates this same event; acquisition purpose is never rewritten.
        let event_index = state.program.len();
        let pc = Some(state.current_pc);
        let selected_length = state.selected_len;
        state.program.push(ProgramEvent {
            ordinal: event_index as u64,
            pc,
            address,
            segment_offset: offset,
            instruction_offset,
            acquired_purpose: purpose.into(),
            selection_association: None,
            selected_length,
            serviced: false,
            refusal: None,
        });
        let phase = state.phase;
        if let Some(t) = state.transfer.as_mut() {
            let stamp = t.stamp(event_index as u64, phase);
            t.stages.program.push(stamp);
        }
        let result = (|| {
            Self::readiness(&state)?;
            match purpose {
                "DiagnosticProgramProbe"
                    if state.composite.is_none()
                        && state.transfer.is_none()
                        && matches!(state.phase, "Setup" | "Functional") => {}
                "DecoderProbe" if state.phase == "Executing" && state.selected_len.is_none() => {}
                "ArchitecturalSelectedFetch"
                    if state.phase == "Executing"
                        && state
                            .selected_len
                            .is_some_and(|len| state.selected_reads < len)
                        && instruction_offset == Some(state.selected_reads as u32) => {}
                _ => {
                    return Err(AuditError::new(
                        "ProgramPurposeOrPhaseDenied",
                        Some(address),
                        "actual callback purpose and lifecycle must agree",
                    ))
                }
            }
            let offset = offset.ok_or_else(|| {
                AuditError::new(
                    "ProgramOutsideSegment",
                    Some(address),
                    "strict immutable segment has no zero fallback or prefix",
                )
            })?;
            Ok(state
                .transfer
                .as_ref()
                .map_or(&self.segment, |t| t.segment())
                .bytes[offset as usize])
        })();
        let refusal = result
            .as_ref()
            .err()
            .map(|error| Self::latch(&mut state, error.clone()));
        state.program[event_index].serviced = result.is_ok();
        state.program[event_index].refusal = refusal;
        if result.is_ok() && purpose == "ArchitecturalSelectedFetch" {
            state.selected_reads += 1;
        }
        result
    }
    pub(crate) fn associate_selection(&self, len: usize) -> Result<()> {
        let mut state = self.state.borrow_mut();
        let result = (|| {
            Self::readiness(&state)?;
            if state.phase != "Executing" || state.selected_len.is_some() || len == 0 {
                return Err(AuditError::new(
                    "InvalidDecoderSelection",
                    None,
                    "one actual successful selection per step",
                ));
            }
            state.selected_len = Some(len);
            let start = if state.composite.is_some() || state.transfer.is_some() {
                state.program_start
            } else {
                0
            };
            for event in &mut state.program[start..] {
                if event.acquired_purpose == "DecoderProbe" {
                    event.selected_length = Some(len);
                    event.selection_association = Some(
                        if event.instruction_offset.is_some_and(|o| (o as usize) < len) {
                            "SelectedExtent"
                        } else {
                            "DecoderLookahead"
                        }
                        .into(),
                    );
                }
            }
            Ok(())
        })();
        result.map_err(|error| Self::latch(&mut state, error))
    }
    pub(crate) fn set_instruction(&self, index: usize) {
        self.state.borrow_mut().instruction = Some(index);
    }
    pub(crate) fn set_current_pc(&self, pc: u16) {
        self.state.borrow_mut().current_pc = pc;
    }
    pub(crate) fn before_execute(&self) {
        self.state.borrow_mut().execution_calls += 1;
    }
    pub(crate) fn retire(&self, pc: u16, external: Option<u16>) -> Result<()> {
        let mut state = self.state.borrow_mut();
        let result = (|| {
            Self::readiness(&state)?;
            if state.phase != "Executing"
                || state.execution_calls != state.retirements + 1
                || state.selected_len != Some(state.selected_reads)
                || state.active_data.is_some()
            {
                return Err(AuditError::new(
                    "InvalidRetirement",
                    Some(i64::from(pc)),
                    "all selected fetches and the real execution must complete",
                ));
            }
            if state.transfer.is_some() {
                let origin = state.pc.expect("actual selected source PC");
                let retired = state.retirements;
                let selected_index = state.instruction.ok_or_else(|| {
                    AuditError::new(
                        "TransferRetirementFormMissing",
                        None,
                        "actual selected form required",
                    )
                })?;
                let disposition = state.transfer.as_mut().expect("transfer").retirement(
                    origin,
                    pc,
                    retired,
                    external,
                    selected_index,
                )?;
                state.retirements += 1;
                match disposition {
                    TransferRetirement::Continue => {
                        state.phase = "Functional";
                        state.external_exit = None;
                        state.terminal_reason = None;
                    }
                    TransferRetirement::Pending(destination) => {
                        state.transfer.as_mut().expect("transfer").pending = Some(Pending {
                            destination,
                            record: None,
                            issued: false,
                        });
                        state.phase = "TransferPending";
                        state.external_exit = external;
                        state.terminal_reason = Some("ActualDirectJTransferPending".into());
                    }
                    TransferRetirement::Checkpoint => {
                        state.sealed = true;
                        state.phase = "Sealed";
                        state.external_exit = None;
                        state.terminal_reason = Some("InventedContinuationCheckpoint".into());
                    }
                    TransferRetirement::NoContinuation => {
                        state.sealed = true;
                        state.phase = "Sealed";
                        state.external_exit = external;
                        state.terminal_reason = Some("ActualDirectJCompleted".into());
                    }
                }
                return Ok(());
            }
            if let Some(closed) = state.composite.as_ref() {
                let origin = state.pc.expect("selected execution origin");
                let terminal = closed.successor(origin, pc, state.retirements)?;
                if external != terminal.then_some(pc) {
                    return Err(AuditError::new(
                        "CompositeExternalTransferMismatch", Some(i64::from(pc)),
                        "terminal authority requires the actual selected direct J and exact external target",
                    ));
                }
                state.retirements += 1;
                if terminal {
                    state.composite.as_mut().expect("closed").direct_j_count += 1;
                    state.sealed = true;
                    state.phase = "Sealed";
                    state.external_exit = external;
                    state.terminal_reason = Some("ActualDirectJCompleted".into());
                } else {
                    state.phase = "Functional";
                    state.external_exit = None;
                    state.terminal_reason = None;
                }
                return Ok(());
            }
            state.retirements += 1;
            state.sealed = true;
            state.phase = "Sealed";
            state.external_exit = external;
            state.terminal_reason = Some(
                if external.is_some() {
                    "ActualDirectJCompleted"
                } else {
                    "OneStepComplete"
                }
                .into(),
            );
            Ok(())
        })();
        result.map_err(|error| Self::latch(&mut state, error))
    }
    pub(crate) fn begin_data(
        &self,
        address: u16,
        width: u8,
        write: bool,
        value: Option<u16>,
        old: Option<u16>,
    ) -> Result<DataToken> {
        let mut state = self.state.borrow_mut();
        if let Some(index) = state.active_data {
            return Ok(DataToken { index, root: false });
        }
        let access = Access { address, width };
        let operation = if write { "Write" } else { "Read" };
        let result = (|| {
            Self::readiness(&state)?;
            access.addresses()?;
            if state.phase == "Setup" {
                if write && state.pending_seed == Some(access) {
                    return Ok(());
                }
                return Err(AuditError::new(
                    "UnadmittedSeedOrSetupRead",
                    Some(i64::from(address)),
                    "seed events must have an explicit once-only admission",
                ));
            }
            if !matches!(state.phase, "Functional" | "Executing") {
                return Err(AuditError::new(
                    "DataOutsideFunctionalPhase",
                    Some(i64::from(address)),
                    "functional DATA lifecycle",
                ));
            }
            let closed_rmw = if let Some(t) = &state.transfer {
                if state.phase != "Executing" || t.stage != TransferStage::Composite {
                    return Err(AuditError::new(
                        "TransferLogicalDataDenied",
                        Some(i64::from(address)),
                        "no caller/continuation DATA rights or host access between steps",
                    ));
                }
                Some(t.closed.data_right(
                    state.pc.expect("executing PC"),
                    state.instruction.ok_or_else(|| {
                        AuditError::new(
                            "TransferDataInstructionMissing",
                            None,
                            "actual selected instruction",
                        )
                    })?,
                    access,
                    write,
                )?)
            } else if let Some(closed) = &state.composite {
                if state.phase != "Executing" {
                    return Err(AuditError::new(
                        "CompositeDataOutsideInstruction",
                        Some(i64::from(address)),
                        "no host DATA access between closed steps",
                    ));
                }
                Some(closed.data_right(
                    state.pc.ok_or_else(|| {
                        AuditError::new(
                            "CompositeDataOutsideInstruction",
                            None,
                            "actual instruction PC missing",
                        )
                    })?,
                    state.instruction.ok_or_else(|| {
                        AuditError::new(
                            "CompositeDataOutsideInstruction",
                            None,
                            "actual selected instruction missing",
                        )
                    })?,
                    access,
                    write,
                )?)
            } else {
                None
            };
            if write {
                let permissions = state
                    .transfer
                    .as_ref()
                    .map_or(&self.permissions, |t| t.permissions());
                let right = permissions
                    .writes
                    .iter()
                    .find(|row| row.access == access)
                    .ok_or_else(|| {
                        AuditError::new(
                            "LogicalWriteDenied",
                            Some(i64::from(address)),
                            "independent exact logical width/address write right",
                        )
                    })?;
                let rmw_required = closed_rmw.unwrap_or(right.rmw_required);
                let start = if state.composite.is_some() || state.transfer.is_some() {
                    state.data_start
                } else {
                    0
                };
                if rmw_required
                    && !state.data[start..].iter().any(|event| {
                        event.phase == "Functional"
                            && event.pc == state.pc
                            && event.instruction_index == state.instruction
                            && event.operation == "Read"
                            && event.serviced
                            && event.address == address
                            && event.width == width
                    })
                {
                    return Err(AuditError::new(
                        "RmwReadMissing",
                        Some(i64::from(address)),
                        "actual earlier functional read required, not a diagnostic or seed",
                    ));
                }
            } else if !state
                .transfer
                .as_ref()
                .map_or(&self.permissions, |t| t.permissions())
                .reads
                .contains(&access)
            {
                return Err(AuditError::new(
                    "LogicalReadDenied",
                    Some(i64::from(address)),
                    "independent exact logical width/address read right",
                ));
            }
            Ok(())
        })();
        let refusal = result
            .as_ref()
            .err()
            .map(|error| Self::latch(&mut state, error.clone()));
        let index = state.data.len();
        let phase = if state.phase == "Setup" {
            "Seed"
        } else {
            "Functional"
        };
        let pc = state.pc;
        let instruction_index = state.instruction;
        state.data.push(DataEvent {
            ordinal: index as u64,
            phase: phase.into(),
            pc,
            instruction_index,
            address,
            width,
            operation: operation.into(),
            requested_value: value,
            value: None,
            old_value: if result.is_ok() { old } else { None },
            write_ordinal: None,
            same_value: None,
            serviced: false,
            refusal,
        });
        let stamp_phase = state.phase;
        if let Some(t) = state.transfer.as_mut() {
            let stamp = t.stamp(index as u64, stamp_phase);
            t.stages.logical.push(stamp);
        }
        result.map(|()| {
            state.active_data = Some(index);
            DataToken { index, root: true }
        })
    }
    pub(crate) fn end_data(&self, token: DataToken, value: Option<u16>) {
        if !token.root {
            return;
        }
        let mut state = self.state.borrow_mut();
        let fault = state.fault.clone();
        let write_ordinal = if fault.is_none() && state.data[token.index].operation == "Write" {
            let ordinal = state.write_ordinal;
            state.write_ordinal += 1;
            Some(ordinal)
        } else {
            None
        };
        let event = &mut state.data[token.index];
        event.serviced = fault.is_none();
        event.refusal = fault;
        if event.serviced {
            event.value = value;
            event.write_ordinal = write_ordinal;
            if event.operation == "Write" {
                event.same_value = Some(event.old_value == value);
            }
        }
        state.active_data = None;
        state.pending_seed = None;
    }
    pub(crate) fn begin_raw(
        &self,
        address: u16,
        write: bool,
        value: Option<u8>,
        old: Option<u8>,
    ) -> Result<RawToken> {
        let mut state = self.state.borrow_mut();
        let operation = if write { "Write" } else { "Read" };
        let logical = state.active_data;
        let result = (|| {
            Self::readiness(&state)?;
            let logical = logical.ok_or_else(|| {
                AuditError::new(
                    "RawWithoutLogicalOperation",
                    Some(i64::from(address)),
                    "raw service must have a real logical parent",
                )
            })?;
            let parent = &state.data[logical];
            let parent_access = Access {
                address: parent.address,
                width: parent.width,
            };
            if !parent_access.addresses()?.contains(&address) || parent.operation != operation {
                return Err(AuditError::new(
                    "RawLogicalMismatch",
                    Some(i64::from(address)),
                    "actual constituent address and direction",
                ));
            }
            let allowed = if state.phase == "Setup" {
                state.pending_seed.is_some_and(|seed| {
                    seed.addresses().is_ok_and(|bytes| bytes.contains(&address))
                })
            } else if write {
                state
                    .transfer
                    .as_ref()
                    .map_or(&self.permissions, |t| t.permissions())
                    .raw_writes
                    .contains(&address)
            } else {
                state
                    .transfer
                    .as_ref()
                    .map_or(&self.permissions, |t| t.permissions())
                    .raw_reads
                    .contains(&address)
            };
            if !allowed {
                return Err(AuditError::new(
                    if write {
                        "RawWriteDenied"
                    } else {
                        "RawReadDenied"
                    },
                    Some(i64::from(address)),
                    "independent constituent right checked before service",
                ));
            }
            Ok(())
        })();
        let refusal = result
            .as_ref()
            .err()
            .map(|error| Self::latch(&mut state, error.clone()));
        let index = state.raw.len();
        state.raw.push(RawDataEvent {
            ordinal: index as u64,
            logical_ordinal: logical.map_or(u64::MAX, |n| n as u64),
            address,
            operation: operation.into(),
            requested_value: value,
            value: None,
            old_value: if result.is_ok() { old } else { None },
            write_ordinal: None,
            same_value: None,
            serviced: false,
            refusal,
        });
        let stamp_phase = state.phase;
        if let Some(t) = state.transfer.as_mut() {
            let stamp = t.stamp(index as u64, stamp_phase);
            t.stages.raw.push(stamp);
        }
        result.map(|()| RawToken { index })
    }
    pub(crate) fn end_raw(&self, token: RawToken, value: u8) {
        let mut state = self.state.borrow_mut();
        let fault = state.fault.clone();
        let write_ordinal = if fault.is_none() && state.raw[token.index].operation == "Write" {
            let ordinal = state.raw_write_ordinal;
            state.raw_write_ordinal += 1;
            Some(ordinal)
        } else {
            None
        };
        let event = &mut state.raw[token.index];
        event.serviced = fault.is_none();
        event.refusal = fault;
        if event.serviced {
            event.value = Some(value);
            event.write_ordinal = write_ordinal;
            if event.operation == "Write" {
                event.same_value = Some(event.old_value == Some(value));
            }
        }
    }
    pub(crate) fn diagnostic_ram(&self) {
        let mut state = self.state.borrow_mut();
        let ordinal = state.diagnostics.len() as u64;
        state.diagnostics.push(DiagnosticEvent {
            ordinal,
            kind: "RawRamSnapshot".into(),
            range: [0x80, 0x1000],
            byte_count: 3968,
        });
        let phase = state.phase;
        if let Some(t) = state.transfer.as_mut() {
            let stamp = t.stamp(ordinal, phase);
            t.stages.diagnostic.push(stamp);
        }
    }
    pub(crate) fn report(&self) -> AuditReport {
        let state = self.state.borrow();
        let segment = state
            .transfer
            .as_ref()
            .map_or(&self.segment, |t| t.segment());
        AuditReport {
            entry_pc: state.entry_pc,
            current_pc: state.current_pc,
            program_base: segment.base,
            program_end_exclusive: segment.end,
            program_sha256: segment.digest.clone(),
            program_events: state.program.clone(),
            data_events: state.data.clone(),
            raw_data_events: state.raw.clone(),
            diagnostic_events: state.diagnostics.clone(),
            data_admission_refusals: state.data_admission_refusals.clone(),
            permissions: state
                .transfer
                .as_ref()
                .map_or(&self.permissions, |t| t.permissions())
                .clone(),
            phase: state.phase.into(),
            budget: state.budget,
            successful_retirements: state.retirements,
            step_calls: state.step_calls,
            execution_calls: state.execution_calls,
            sealed: state.sealed,
            shared_execution_calls: state.execution_calls,
            terminal_reason: state.terminal_reason.clone(),
            external_exit: state.external_exit,
            first_fault: state.fault.clone(),
        }
    }
}
