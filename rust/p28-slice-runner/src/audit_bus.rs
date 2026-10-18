//! Opt-in state owned by the production Bus. No instruction semantics live here.
use crate::audit::composite::{
    ClosedState, CompositeNodeIdentity, CompositeReport, CompositeStepOutcome, COMPOSITE_SHA256,
    INVENTORY,
};
use crate::audit::{
    Access, AuditError, AuditReport, DataAdmissionRefusal, DataEvent, DiagnosticEvent, Permissions,
    ProgramEvent, ProgramSegment, RawDataEvent, Result,
};
use crate::audit::{Snapshot, StepOutcome};
use std::cell::RefCell;

#[cfg(test)]
#[path = "audit_composite_tests.rs"]
mod composite_tests;

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
    pub(crate) fn admit_legacy_step(&self) -> Result<()> {
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
            if u32::from(pc) < self.segment.base || u32::from(pc) >= self.segment.end {
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
        let offset = u32::try_from(address)
            .ok()
            .filter(|a| *a >= self.segment.base && *a < self.segment.end)
            .map(|a| a - self.segment.base);
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
        let result = (|| {
            Self::readiness(&state)?;
            match purpose {
                "DiagnosticProgramProbe"
                    if state.composite.is_none()
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
            Ok(self.segment.bytes[offset as usize])
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
            let start = if state.composite.is_some() {
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
            let closed_rmw = if let Some(closed) = &state.composite {
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
                let right = self
                    .permissions
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
                let start = if state.composite.is_some() {
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
            } else if !self.permissions.reads.contains(&access) {
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
                self.permissions.raw_writes.contains(&address)
            } else {
                self.permissions.raw_reads.contains(&address)
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
    }
    pub(crate) fn report(&self) -> AuditReport {
        let state = self.state.borrow();
        AuditReport {
            entry_pc: state.entry_pc,
            current_pc: state.current_pc,
            program_base: self.segment.base,
            program_end_exclusive: self.segment.end,
            program_sha256: self.segment.digest.clone(),
            program_events: state.program.clone(),
            data_events: state.data.clone(),
            raw_data_events: state.raw.clone(),
            diagnostic_events: state.diagnostics.clone(),
            data_admission_refusals: state.data_admission_refusals.clone(),
            permissions: self.permissions.clone(),
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
