//! Opt-in state owned by the production Bus. No instruction semantics live here.
use crate::audit::composite::{
    ClosedState, CompositeNodeIdentity, CompositeReport, CompositeStepOutcome, COMPOSITE_SHA256,
    INVENTORY,
};
#[cfg(feature = "p28-word0196-original-rom")]
use crate::audit::original_rom::{OriginalNode, OriginalRomReport, OriginalRomStep, OriginalState};
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
#[cfg(feature = "p28-word0196-p2-handoff")]
#[derive(Clone)]
pub(crate) struct P2AuditState {
    pub(crate) pc: u16,
    pub(crate) index: usize,
    pub(crate) read_ordinal: Option<u64>,
    pub(crate) write_ordinal: Option<u64>,
    pub(crate) retired: bool,
    pub(crate) retirement: u8,
}
#[cfg(feature = "p28-word0196-post-p2-control")]
#[derive(Clone)]
struct ControlAuditState {
    pc: u16,
    index: usize,
    address: u16,
    alias_pc: Option<u16>,
    reads: Vec<u64>,
    write: Option<u64>,
    retired: bool,
}
#[cfg(feature = "p28-word0196-below-second-p2-continuity")]
#[derive(Clone)]
struct BelowSecondAuditState {
    p2: P2AuditState,
    control: ControlAuditState,
}
struct State {
    #[cfg(feature = "p28-word0196-cal-rt-continuity")]
    cal_rt: Option<crate::audit::cal_rt_continuity::CalRtBudget>,
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
    #[cfg(feature = "p28-word0196-original-rom")]
    original: Option<OriginalState>,
    #[cfg(feature = "p28-word0196-p2-handoff")]
    p2_handoff: Option<P2AuditState>,
    #[cfg(feature = "p28-word0196-post-p2-control")]
    post_control: Option<ControlAuditState>,
    #[cfg(feature = "p28-word0196-below-second-p2-continuity")]
    below_second: Option<BelowSecondAuditState>,
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
impl State {
    fn original_active(&self) -> bool {
        #[cfg(feature = "p28-word0196-original-rom")]
        {
            self.original.is_some()
        }
        #[cfg(not(feature = "p28-word0196-original-rom"))]
        {
            false
        }
    }
}
pub(crate) struct AuditBus {
    segment: ProgramSegment,
    #[cfg(feature = "p28-word0196-cal-rt-continuity")]
    caller_segment: Option<ProgramSegment>,
    permissions: Permissions,
    state: RefCell<State>,
}
impl AuditBus {
    pub(crate) fn cal_rt_body_offset(&self) -> u64 {
        #[cfg(feature = "p28-word0196-cal-rt-continuity")]
        if self.state.borrow().cal_rt.is_some() {
            return 1;
        }
        0
    }
    fn body_offset(state: &State) -> u64 {
        #[cfg(feature = "p28-word0196-cal-rt-continuity")]
        if state.cal_rt.is_some() {
            return 1;
        }
        let _ = state;
        0
    }
    #[cfg(feature = "p28-word0196-cal-rt-continuity")]
    pub(crate) fn new_cal_rt(
        caller: ProgramSegment,
        body: ProgramSegment,
        permissions: Permissions,
        admission: crate::audit::cal_rt_continuity::CalRtBudget,
    ) -> Self {
        let mut result = Self::new(body, permissions, admission.caller_pc(), 41);
        result.caller_segment = Some(caller);
        result.state.get_mut().cal_rt = Some(admission);
        result
    }
    fn segment_for(&self, address: u32) -> Option<&ProgramSegment> {
        if (self.segment.base..self.segment.end).contains(&address) {
            return Some(&self.segment);
        }
        #[cfg(feature = "p28-word0196-cal-rt-continuity")]
        if let Some(caller) = &self.caller_segment {
            if (caller.base..caller.end).contains(&address) {
                return Some(caller);
            }
        }
        None
    }
    #[cfg(feature = "p28-word0196-p2-handoff")]
    pub(crate) fn install_p2_handoff(&self, pc: u16, index: usize) -> Result<()> {
        let mut state = self.state.borrow_mut();
        let result = (|| {
            Self::readiness(&state)?;
            let original = state.original.as_ref().ok_or_else(|| {
                AuditError::new(
                    "P2ClosedOriginalRequired",
                    None,
                    "one closed original source",
                )
            })?;
            if state.phase != "Setup"
                || state.p2_handoff.is_some()
                || !matches!(
                    (pc, index),
                    (0x5596, 350) | (0x55c5, 1647) | (0x64a1, 350) | (0x64d0, 1647)
                )
                || !matches!(state.budget, 17 | 19 | 20 | 22)
                || original.nodes.len() != 26
                || original.pcs.last() != Some(&pc)
                || original.terminal != pc + 3
                || state.step_calls != 0
                || state.execution_calls != 0
                || state.retirements != 0
            {
                return Err(AuditError::new(
                    "P2CapabilityInstallationRejected",
                    Some(i64::from(pc)),
                    "new closed26-site admission before the first functional instruction only",
                ));
            }
            state.p2_handoff = Some(P2AuditState {
                pc,
                index,
                read_ordinal: None,
                write_ordinal: None,
                retired: false,
                retirement: state.budget,
            });
            Ok(())
        })();
        result.map_err(|error| Self::latch(&mut state, error))
    }
    #[cfg(feature = "p28-word0196-post-p2-control")]
    pub(crate) fn install_post_p2_control(&self, p2_pc: u16, p2_index: usize) -> Result<()> {
        let mut state = self.state.borrow_mut();
        let result = (|| {
            Self::readiness(&state)?;
            #[cfg(feature = "p28-word0196-below-second-p2-continuity")]
            if state.budget == 39 || Self::body_offset(&state) == 1 {
                return Self::install_below_second_caps(&mut state, p2_pc, p2_index);
            }
            let original = state.original.as_ref().ok_or_else(|| {
                AuditError::new("PostP2OriginalRequired", None, "closed original source")
            })?;
            let below = matches!((p2_pc, p2_index), (0x55c5, 1647) | (0x64d0, 1647));
            let not_below = matches!((p2_pc, p2_index), (0x5596, 350) | (0x64a1, 350));
            let pc = p2_pc + 3;
            let index = if below { 1994 } else { 382 };
            let address = if below { 0x40 } else { 0x46 };
            let tail = if below { 4 } else { 1 };
            let alias_pc = below.then_some(pc + 7);
            if state.phase != "Setup"
                || state.p2_handoff.is_some()
                || state.post_control.is_some()
                || (!below && !not_below)
                || original.nodes.len() != 31
                || original.pcs.len() != usize::from(state.budget)
                || !matches!(state.budget, 20 | 21 | 23)
                || (below && state.budget != 21)
                || original.pcs.get(usize::from(state.budget - tail - 1)) != Some(&p2_pc)
                || original.pcs.last() != Some(&alias_pc.unwrap_or(pc))
                || original.terminal != if below { pc + 10 } else { pc + 4 }
                || state.step_calls != 0
                || state.execution_calls != 0
                || state.retirements != 0
            {
                return Err(AuditError::new(
                    "PostP2CapabilityInstallationRejected",
                    Some(i64::from(pc)),
                    "closed31-node control suffix before first instruction",
                ));
            }
            state.p2_handoff = Some(P2AuditState {
                pc: p2_pc,
                index: p2_index,
                read_ordinal: None,
                write_ordinal: None,
                retired: false,
                retirement: state.budget - tail,
            });
            state.post_control = Some(ControlAuditState {
                pc,
                index,
                address,
                alias_pc,
                reads: vec![],
                write: None,
                retired: false,
            });
            Ok(())
        })();
        result.map_err(|e| Self::latch(&mut state, e))
    }
    #[cfg(feature = "p28-word0196-below-second-p2-continuity")]
    fn install_below_second_caps(state: &mut State, p2_pc: u16, p2_index: usize) -> Result<()> {
        let original = state.original.as_ref().ok_or_else(|| {
            AuditError::new(
                "BelowSecondOriginalRequired",
                None,
                "closed original source",
            )
        })?;
        let offset = Self::body_offset(state) as usize;
        #[cfg(feature = "p28-word0196-cal-rt-continuity")]
        let base = state.cal_rt.map_or(state.entry_pc, |c| c.body_pc());
        #[cfg(not(feature = "p28-word0196-cal-rt-continuity"))]
        let base = state.entry_pc;
        let pc = |native: u16| base + (native - 0x54f5);
        if state.phase != "Setup"
            || state.p2_handoff.is_some()
            || state.post_control.is_some()
            || state.below_second.is_some()
            || state.budget != (if offset == 0 { 39 } else { 41 })
            || !matches!(base, 0x54f5 | 0x6400)
            || p2_pc != pc(0x55c5)
            || p2_index != 1647
            || original.nodes.len() != 49 + offset * 2
            || original.inventory.len() != 23 + offset * 2
            || original.pcs.len() != 39 + offset * 2
            || original.pcs.get(16 + offset) != Some(&p2_pc)
            || original.pcs.get(17 + offset) != Some(&pc(0x55c8))
            || original.pcs.get(20 + offset) != Some(&pc(0x55cf))
            || original.pcs.get(23 + offset) != Some(&pc(0x55d5))
            || original.pcs.get(37 + offset) != Some(&pc(0x5682))
            || original.pcs.get(38 + offset) != Some(&pc(0x5685))
            || (offset == 0 && original.terminal != pc(0x5688))
            || state.step_calls != 0
            || state.execution_calls != 0
            || state.retirements != 0
        {
            return Err(AuditError::new(
                "BelowSecondCapabilityInstallationRejected",
                Some(i64::from(p2_pc)),
                "closed49-node39-step Below source before first instruction only",
            ));
        }
        state.p2_handoff = Some(P2AuditState {
            pc: p2_pc,
            index: p2_index,
            read_ordinal: None,
            write_ordinal: None,
            retired: false,
            retirement: 17 + offset as u8,
        });
        state.post_control = Some(ControlAuditState {
            pc: pc(0x55c8),
            index: 1994,
            address: 0x40,
            alias_pc: Some(pc(0x55cf)),
            reads: vec![],
            write: None,
            retired: false,
        });
        state.below_second = Some(BelowSecondAuditState {
            p2: P2AuditState {
                pc: pc(0x5682),
                index: 1647,
                read_ordinal: None,
                write_ordinal: None,
                retired: false,
                retirement: 38 + offset as u8,
            },
            control: ControlAuditState {
                pc: pc(0x55d5),
                index: 1779,
                address: 0x40,
                alias_pc: None,
                reads: vec![],
                write: None,
                retired: false,
            },
        });
        Ok(())
    }
    #[cfg(feature = "p28-word0196-below-second-p2-continuity")]
    pub(crate) fn below_second_p2_active(&self) -> bool {
        self.state.borrow().below_second.is_some()
    }
    #[cfg(feature = "p28-word0196-post-p2-control")]
    pub(crate) fn post_p2_control_active(&self) -> bool {
        self.state.borrow().post_control.is_some()
    }
    #[cfg(feature = "p28-word0196-post-p2-control")]
    pub(crate) fn post_p2_control_selected(&self, pc: u16, index: usize) -> Option<(u16, u16)> {
        let s = self.state.borrow();
        let c = s.post_control.as_ref()?;
        let first = (s.phase == "Executing"
            && c.pc == pc
            && c.index == index
            && !c.retired
            && c.write.is_none())
        .then_some((c.address, pc));
        if first.is_some() {
            return first;
        }
        #[cfg(feature = "p28-word0196-below-second-p2-continuity")]
        if let Some(second) = s.below_second.as_ref() {
            let c2 = &second.control;
            if s.phase == "Executing"
                && c2.pc == pc
                && c2.index == index
                && !c2.retired
                && c2.write.is_none()
                && s.retirements + 1 == 24 + Self::body_offset(&s)
                && c.retired
                && s.p2_handoff.as_ref().is_some_and(|p| p.retired)
            {
                return Some((c2.address, pc));
            }
        }
        None
    }
    #[cfg(feature = "p28-word0196-post-p2-control")]
    fn control_logical_right(s: &State, address: u16, width: u8, write: bool) -> Result<bool> {
        let Some(c) = s.post_control.as_ref() else {
            return Ok(false);
        };
        if address >= 0x80 || address == 0x24 {
            return Ok(false);
        }
        #[cfg(feature = "p28-word0196-below-second-p2-continuity")]
        if let Some(second) = s.below_second.as_ref() {
            let c2 = &second.control;
            if s.pc == Some(c2.pc) {
                if address != 0x40
                    || width != 8
                    || s.phase != "Executing"
                    || s.instruction != Some(c2.index)
                    || s.retirements + 1 != 24 + Self::body_offset(s)
                    || !c.retired
                    || !s.p2_handoff.as_ref().is_some_and(|p| p.retired)
                    || c2.retired
                    || c2.write.is_some()
                    || (write && c2.reads.len() != 2)
                    || (!write && c2.reads.len() >= 2)
                {
                    return Err(AuditError::new(
                        "BelowSecondControlPermissionDenied",
                        Some(i64::from(address)),
                        "second exact byte RB after first native P2/control generations only",
                    ));
                }
                return Ok(true);
            }
        }
        if address == 6
            && width == 8
            && !write
            && s.phase == "Executing"
            && s.pc == c.alias_pc
            && s.instruction == Some(894)
            && c.retired
        {
            return Ok(true);
        }
        let expected_reads = if c.address == 0x40 { 2 } else { 1 };
        if address != c.address
            || width != 8
            || s.phase != "Executing"
            || s.pc != Some(c.pc)
            || s.instruction != Some(c.index)
            || c.retired
            || c.write.is_some()
            || !s.p2_handoff.as_ref().is_some_and(|p| p.retired)
            || (write && c.reads.len() != expected_reads)
            || (!write && c.reads.len() >= expected_reads)
        {
            return Err(AuditError::new(
                "PostP2OneShotPermissionDenied",
                Some(i64::from(address)),
                "exact control form/PC/byte/read-before-write, or final AL alias read only",
            ));
        }
        Ok(true)
    }
    #[cfg(feature = "p28-word0196-p2-handoff")]
    pub(crate) fn p2_handoff_active(&self) -> bool {
        self.state.borrow().p2_handoff.is_some()
    }
    #[cfg(feature = "p28-word0196-p2-handoff")]
    pub(crate) fn p2_handoff_selected(&self, pc: u16, index: usize) -> bool {
        let state = self.state.borrow();
        let first = state.phase == "Executing"
            && state.p2_handoff.as_ref().is_some_and(|p| {
                p.pc == pc && p.index == index && p.write_ordinal.is_none() && !p.retired
            });
        if first {
            return true;
        }
        #[cfg(feature = "p28-word0196-below-second-p2-continuity")]
        if let Some(second) = state.below_second.as_ref() {
            return state.phase == "Executing"
                && second.p2.pc == pc
                && second.p2.index == index
                && state.retirements + 1 == u64::from(second.p2.retirement)
                && second.control.retired
                && !second.p2.retired
                && second.p2.write_ordinal.is_none()
                && state.p2_handoff.as_ref().is_some_and(|p| p.retired);
        }
        false
    }
    #[cfg(feature = "p28-word0196-p2-handoff")]
    pub(crate) fn p2_handoff_state(&self) -> Option<P2AuditState> {
        self.state.borrow().p2_handoff.clone()
    }
    #[cfg(feature = "p28-word0196-p2-handoff")]
    fn p2_logical_right(state: &State, address: u16, width: u8, write: bool) -> Result<bool> {
        let Some(p2) = &state.p2_handoff else {
            return Ok(false);
        };
        if address >= 0x80 {
            return Ok(false);
        }
        #[cfg(feature = "p28-word0196-post-p2-control")]
        if state.post_control.is_some() && address != 0x24 {
            return Ok(false);
        }
        #[cfg(feature = "p28-word0196-below-second-p2-continuity")]
        if let Some(second) = state.below_second.as_ref() {
            let p = &second.p2;
            if state.pc == Some(p.pc) {
                if address != 0x24
                    || width != 8
                    || state.phase != "Executing"
                    || state.instruction != Some(p.index)
                    || state.retirements + 1 != u64::from(p.retirement)
                    || !p2.retired
                    || !second.control.retired
                    || p.retired
                    || p.write_ordinal.is_some()
                    || (write && p.read_ordinal.is_none())
                    || (!write && p.read_ordinal.is_some())
                {
                    return Err(AuditError::new(
                        "BelowSecondP2PermissionDenied",
                        Some(i64::from(address)),
                        "second exact byte ORB after retained G1 and second control only",
                    ));
                }
                return Ok(true);
            }
        }
        if address != 0x24
            || width != 8
            || state.phase != "Executing"
            || state.pc != Some(p2.pc)
            || state.instruction != Some(p2.index)
            || state.retirements + 1 != u64::from(p2.retirement)
            || p2.retired
            || p2.write_ordinal.is_some()
            || (write && p2.read_ordinal.is_none())
            || (!write && p2.read_ordinal.is_some())
        {
            return Err(AuditError::new(
                "P2OneShotPermissionDenied",
                Some(i64::from(address)),
                "one byte read-before-write at the actual last closed P2 instruction only",
            ));
        }
        Ok(true)
    }
    #[cfg(feature = "p28-word0196-original-rom")]
    pub(crate) fn install_original(&self, original: OriginalState) -> Result<()> {
        let mut state = self.state.borrow_mut();
        let result = (|| {
            Self::readiness(&state)?;
            let mut expected = original.inventory.clone();
            expected.extend(0x80..0xc0);
            expected.sort_unstable();
            let mut actual = state.seeded.clone();
            actual.sort_unstable();
            #[cfg(feature = "p28-word0196-below-second-p2-continuity")]
            let extended_seeds = state.budget == 39
                && original.nodes.len() == 49
                && original.inventory.len() == 23
                && original.pcs.len() == 39
                && self.segment.end - self.segment.base == 403
                && matches!(self.segment.base, 0x54f5 | 0x6400);
            #[cfg(not(feature = "p28-word0196-below-second-p2-continuity"))]
            let extended_seeds = false;
            #[cfg(feature = "p28-word0196-cal-rt-continuity")]
            let cal_rt_seeds = state.cal_rt.is_some_and(|c| {
                state.budget == 41
                    && original.nodes.len() == 51
                    && original.inventory.len() == 25
                    && original.pcs.len() == 41
                    && original.pcs.first() == Some(&c.caller_pc())
                    && original.pcs.last() == Some(&c.rt_pc())
                    && original.terminal == c.return_pc()
                    && self.segment.base == u32::from(c.body_pc())
                    && self.segment.end - self.segment.base == 404
                    && self
                        .caller_segment
                        .as_ref()
                        .is_some_and(|s| s.base == u32::from(c.caller_pc()) && s.end - s.base == 3)
            });
            #[cfg(not(feature = "p28-word0196-cal-rt-continuity"))]
            let cal_rt_seeds = false;
            let (logical_seeds, raw_seeds) = if cal_rt_seeds {
                (57, 89)
            } else if extended_seeds {
                (55, 87)
            } else {
                (48, 80)
            };
            if state.phase != "Setup"
                || state.composite.is_some()
                || state.transfer.is_some()
                || state.original_active()
                || state.pending_seed.is_some()
                || state.active_data.is_some()
                || actual != expected
                || !state.program.is_empty()
                || state.step_calls != 0
                || state.execution_calls != 0
                || state.retirements != 0
                || state.data.len() != logical_seeds
                || state.raw.len() != raw_seeds
                || state.data.iter().any(|e| e.phase != "Seed" || !e.serviced)
                || state.raw.iter().any(|e| !e.serviced)
                || original.pcs.first().copied() != Some(state.entry_pc)
                || usize::from(state.budget) != original.pcs.len()
            {
                return Err(AuditError::new("OriginalInstallationRejected",None,
                    "one complete DATA initialization and one immutable source before any execution"));
            }
            state.original = Some(original);
            Ok(())
        })();
        result.map_err(|error| Self::latch(&mut state, error))
    }
    #[cfg(feature = "p28-word0196-original-rom")]
    pub(crate) fn require_original(&self) -> Result<()> {
        if self.state.borrow().original.is_none() {
            return Err(AuditError::new(
                "WrongOriginalApi",
                None,
                "explicit original constructor required",
            ));
        }
        Ok(())
    }
    #[cfg(feature = "p28-word0196-original-rom")]
    pub(crate) fn original_node(&self, pc: u16, dd: bool) -> Result<OriginalNode> {
        let state = self.state.borrow();
        Self::readiness(&state)?;
        state
            .original
            .as_ref()
            .ok_or_else(|| {
                AuditError::new(
                    "WrongOriginalApi",
                    None,
                    "explicit original constructor required",
                )
            })?
            .node(pc, dd, state.retirements)
    }
    #[cfg(feature = "p28-word0196-original-rom")]
    pub(crate) fn record_original_step(
        &self,
        before: Snapshot,
        after: Snapshot,
        full_psw_before: u16,
        full_psw_after: u16,
        outcome: StepOutcome,
    ) -> Result<OriginalRomStep> {
        let mut state = self.state.borrow_mut();
        let result = (|| {
            if let Some(error) = state.fault.as_ref() {
                return Err(error.clone());
            }
            let record = OriginalRomStep {
                index: state.retirements,
                node_identity: format!("ClosedSite_{:04X}", outcome.pc_before),
                full_psw_before,
                full_psw_after,
                before,
                after,
                outcome,
                program_span: [state.program_start, state.program.len()],
                logical_span: [state.data_start, state.data.len()],
                raw_span: [state.raw_start, state.raw.len()],
            };
            let retired = state.retirements;
            let original = state
                .original
                .as_mut()
                .ok_or_else(|| AuditError::new("WrongOriginalApi", None, "closed actual record"))?;
            if original.steps.len() as u64 + 1 != retired
                || !record.outcome.retired
                || record.after.cpu.instructions != retired
            {
                return Err(AuditError::new(
                    "OriginalRecordOrderMismatch",
                    None,
                    "one real record per successful retirement",
                ));
            }
            original.steps.push(record.clone());
            Ok(record)
        })();
        result.map_err(|error| Self::latch(&mut state, error))
    }
    #[cfg(feature = "p28-word0196-original-rom")]
    pub(crate) fn original_report(
        &self,
        current: Snapshot,
        full_psw: u16,
    ) -> Result<OriginalRomReport> {
        let audit = self.report();
        let state = self.state.borrow();
        let original = state
            .original
            .as_ref()
            .ok_or_else(|| AuditError::new("WrongOriginalApi", None, "closed actual report"))?;
        let completed = state.sealed
            && state.fault.is_none()
            && state.terminal_reason.as_deref() == Some("OriginalStopBeforeReached")
            && current.cpu.pc == original.terminal
            && state.retirements as usize == original.pcs.len()
            && original.steps.len() as u64 == state.retirements;
        Ok(OriginalRomReport {
            classification: original.classification.clone(),
            source_binding: original.source_binding.clone(),
            program_node_count: original.nodes.len(),
            path: original.path,
            entry: original.entry.clone(),
            current,
            full_psw,
            steps: original.steps.clone(),
            completed,
            stop_before_pc: completed.then_some(original.terminal),
            audit,
        })
    }
    pub(crate) fn new(
        segment: ProgramSegment,
        permissions: Permissions,
        entry: u16,
        budget: u8,
    ) -> Self {
        Self {
            segment,
            #[cfg(feature = "p28-word0196-cal-rt-continuity")]
            caller_segment: None,
            permissions,
            state: RefCell::new(State {
                #[cfg(feature = "p28-word0196-cal-rt-continuity")]
                cal_rt: None,
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
                #[cfg(feature = "p28-word0196-original-rom")]
                original: None,
                #[cfg(feature = "p28-word0196-p2-handoff")]
                p2_handoff: None,
                #[cfg(feature = "p28-word0196-below-second-p2-continuity")]
                below_second: None,
                #[cfg(feature = "p28-word0196-post-p2-control")]
                post_control: None,
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
                || state.original_active()
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
                || state.original_active()
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
        if self.state.borrow().original_active() {
            return Err(self.reject_step_attempt(AuditError::new(
                "WrongOriginalApi",
                None,
                "caller-selected identities cannot enter a closed original session",
            )));
        }
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
            if state.original_active() {
                return Err(AuditError::new("OriginalCapabilityDataDenied", Some(i64::from(address)),
                    "only the actual closed instruction may access DATA; no host mutation/read between retirements"));
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
            let contained = state.transfer.as_ref().map_or_else(
                || self.segment_for(u32::from(pc)).is_some(),
                |t| t.segment().contains_address(pc),
            );
            if !contained {
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
        // Preserve historical denied-probe diagnostics against the active
        // segment. The second closed window only selects another real source;
        // an absent window never supplies padding or a zero-valued byte.
        let (base, end) = {
            let segment = state
                .transfer
                .as_ref()
                .map(|t| t.segment())
                .unwrap_or_else(|| {
                    u32::try_from(address)
                        .ok()
                        .and_then(|a| self.segment_for(a))
                        .unwrap_or(&self.segment)
                });
            (segment.base, segment.end)
        };
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
                        && !state.original_active()
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
            let segment = state
                .transfer
                .as_ref()
                .map(|t| t.segment())
                .unwrap_or_else(|| {
                    u32::try_from(address)
                        .ok()
                        .and_then(|a| self.segment_for(a))
                        .unwrap_or(&self.segment)
                });
            Ok(segment.bytes[offset as usize])
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
            let start =
                if state.composite.is_some() || state.transfer.is_some() || state.original_active()
                {
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
            #[cfg(feature = "p28-word0196-original-rom")]
            if let Some(original) = state.original.as_ref() {
                let terminal = original.successor(
                    state.pc.expect("actual origin"),
                    pc,
                    state.retirements,
                    state.instruction.ok_or_else(|| {
                        AuditError::new("OriginalInstructionMissing", None, "actual selected form")
                    })?,
                )?;
                if external.is_some() {
                    return Err(AuditError::new(
                        "OriginalUnexpectedDirectJ",
                        Some(i64::from(pc)),
                        "terminal fallthrough is not synthetic direct-J authority",
                    ));
                }
                #[cfg(feature = "p28-word0196-below-second-p2-continuity")]
                if state.below_second.is_some() {
                    let offset = Self::body_offset(&state);
                    let origin = state.pc.expect("actual origin");
                    let first_p2 = state.p2_handoff.as_ref().is_some_and(|p| p.retired);
                    let first_control = state.post_control.as_ref().is_some_and(|c| c.retired);
                    let retirement = state.retirements + 1;
                    let second = state.below_second.as_mut().expect("closed below admission");
                    if origin == second.control.pc {
                        if retirement != 24 + offset
                            || !first_p2
                            || !first_control
                            || second.control.retired
                            || second.control.reads.len() != 2
                            || second.control.write.is_none()
                        {
                            return Err(AuditError::new("BelowSecondControlRetirementIncomplete", Some(i64::from(origin)),
                            "second actual ordered control RMW after retained first generations"));
                        }
                        second.control.retired = true;
                    }
                    if origin == second.p2.pc {
                        if retirement != 38 + offset
                            || !first_p2
                            || !second.control.retired
                            || second.p2.retired
                            || second.p2.read_ordinal.is_none()
                            || second.p2.write_ordinal.is_none()
                        {
                            return Err(AuditError::new(
                                "BelowSecondP2RetirementIncomplete",
                                Some(i64::from(origin)),
                                "actual second P2 read/write creates a fresh generation",
                            ));
                        }
                        second.p2.retired = true;
                    }
                    if terminal
                        && (retirement != (if offset == 0 { 39 } else { 41 })
                            || !second.control.retired
                            || !second.p2.retired)
                    {
                        return Err(AuditError::new(
                            "BelowSecondTerminalIncomplete",
                            Some(i64::from(origin)),
                            "both second native operations must complete before RT boundary",
                        ));
                    }
                }
                #[cfg(feature = "p28-word0196-p2-handoff")]
                {
                    #[cfg(feature = "p28-word0196-post-p2-control")]
                    let post = state.post_control.is_some();
                    #[cfg(not(feature = "p28-word0196-post-p2-control"))]
                    let post = false;
                    if post {
                        let origin = state.pc.expect("actual origin");
                        let p2_retired = {
                            let p2 = state.p2_handoff.as_mut().expect("P2 admission");
                            if origin == p2.pc {
                                if p2.retired
                                    || p2.read_ordinal.is_none()
                                    || p2.write_ordinal.is_none()
                                {
                                    return Err(AuditError::new(
                                        "P2RetirementIncomplete",
                                        Some(i64::from(origin)),
                                        "actual one-shot native P2 RMW",
                                    ));
                                }
                                p2.retired = true;
                            }
                            p2.retired
                        };
                        #[cfg(feature = "p28-word0196-post-p2-control")]
                        {
                            let control = state.post_control.as_mut().expect("installed");
                            if origin == control.pc {
                                let expected_reads = if control.address == 0x40 { 2 } else { 1 };
                                if !p2_retired
                                    || control.retired
                                    || control.reads.len() != expected_reads
                                    || control.write.is_none()
                                {
                                    return Err(AuditError::new(
                                        "PostP2ControlRetirementIncomplete",
                                        Some(i64::from(origin)),
                                        "actual ordered control reads/write after P2",
                                    ));
                                }
                                control.retired = true;
                            }
                            if terminal && (!p2_retired || !control.retired) {
                                return Err(AuditError::new(
                                    "PostP2TerminalIncomplete",
                                    Some(i64::from(origin)),
                                    "P2 and control must retire before bounded stop",
                                ));
                            }
                        }
                    } else {
                        let origin = state.pc.expect("actual origin");
                        if let Some(p2) = state.p2_handoff.as_mut() {
                            if terminal {
                                if origin != p2.pc
                                    || p2.read_ordinal.is_none()
                                    || p2.write_ordinal.is_none()
                                    || p2.retired
                                {
                                    return Err(AuditError::new("P2RetirementIncomplete",Some(i64::from(origin)),
                                    "actual terminal P2 read/write must precede exactly one retirement"));
                                }
                                p2.retired = true;
                            } else if origin == p2.pc || p2.write_ordinal.is_some() {
                                return Err(AuditError::new(
                                    "P2PrematureOrRepeatedRetirement",
                                    Some(i64::from(origin)),
                                    "the P2 instruction is the only final extra retirement",
                                ));
                            }
                        }
                    }
                }
                state.retirements += 1;
                state.external_exit = None;
                if terminal {
                    state.sealed = true;
                    state.phase = "Sealed";
                    state.terminal_reason = Some("OriginalStopBeforeReached".into());
                } else {
                    state.phase = "Functional";
                    state.terminal_reason = None;
                }
                return Ok(());
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
            #[cfg(feature = "p28-word0196-cal-rt-continuity")]
            if let Some(c) = state.cal_rt {
                let overlaps = u32::from(address) < u32::from(c.frame_address()) + 2
                    && u32::from(address) + u32::from(width / 8) > u32::from(c.frame_address());
                if overlaps {
                    let call = write
                        && state.pc == Some(c.caller_pc())
                        && state.instruction == Some(388)
                        && state.retirements == 0
                        && value == Some(c.return_pc());
                    let ret = !write
                        && state.pc == Some(c.rt_pc())
                        && state.instruction == Some(1902)
                        && state.retirements == 40;
                    if state.phase != "Executing"
                        || address != c.frame_address()
                        || width != 16
                        || !(call || ret)
                        || state.data[state.data_start..]
                            .iter()
                            .any(|e| e.address == address)
                    {
                        return Err(AuditError::new(
                            "CalRtStackCapabilityDenied",
                            Some(i64::from(address)),
                            "one actual CAL word write and one actual final RT word read only",
                        ));
                    }
                    if ret {
                        let overlapping: Vec<_> = state
                            .data
                            .iter()
                            .filter(|e| {
                                e.phase == "Functional"
                                    && e.operation == "Write"
                                    && e.serviced
                                    && u32::from(e.address) < u32::from(address) + 2
                                    && u32::from(e.address) + u32::from(e.width / 8)
                                        > u32::from(address)
                            })
                            .collect();
                        if overlapping.len() != 1
                            || overlapping[0].pc != Some(c.caller_pc())
                            || overlapping[0].instruction_index != Some(388)
                            || overlapping[0].width != 16
                            || overlapping[0].value != Some(c.return_pc())
                        {
                            return Err(AuditError::new("CalRtFreshFrameRequired", Some(i64::from(address)),
                                "preexisting equal bytes do not establish the current CAL writer generation"));
                        }
                    }
                }
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
            #[cfg(feature = "p28-word0196-original-rom")]
            let closed_rmw = if let Some(original) = state.original.as_ref() {
                if state.phase != "Executing" {
                    return Err(AuditError::new(
                        "OriginalDataOutsideInstruction",
                        Some(i64::from(address)),
                        "no host DATA access between original instructions",
                    ));
                }
                Some(original.data_right(
                    state.pc.expect("actual PC"),
                    state.instruction.ok_or_else(|| {
                        AuditError::new("OriginalInstructionMissing", None, "actual selected form")
                    })?,
                    access,
                    write,
                )?)
            } else {
                closed_rmw
            };
            #[cfg(feature = "p28-word0196-p2-handoff")]
            if Self::p2_logical_right(&state, address, width, write)? {
                // Independent one-shot peripheral capability. Do not turn
                // SFR0024 into a member of the generic RAM permission lists.
                return Ok(());
            }
            #[cfg(feature = "p28-word0196-post-p2-control")]
            if Self::control_logical_right(&state, address, width, write)? {
                return Ok(());
            }
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
                let start = if state.composite.is_some()
                    || state.transfer.is_some()
                    || state.original_active()
                {
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
        #[cfg(feature = "p28-word0196-p2-handoff")]
        {
            let event = &state.data[token.index];
            let observed = (event.address == 0x24 && event.serviced)
                .then(|| (event.operation == "Write", event.ordinal, event.pc));
            #[cfg(feature = "p28-word0196-below-second-p2-continuity")]
            if let (Some(second), Some((write, ordinal, pc))) =
                (state.below_second.as_mut(), observed)
            {
                if pc == Some(second.p2.pc) {
                    if write {
                        second.p2.write_ordinal = Some(ordinal);
                    } else {
                        second.p2.read_ordinal = Some(ordinal);
                    }
                }
            }
            if let (Some(p2), Some((write, ordinal, pc))) = (state.p2_handoff.as_mut(), observed) {
                if pc != Some(p2.pc) { /* second capability never overwrites G1 metadata */
                } else if write {
                    p2.write_ordinal = Some(ordinal);
                } else {
                    p2.read_ordinal = Some(ordinal);
                }
            }
        }
        #[cfg(feature = "p28-word0196-post-p2-control")]
        {
            let event = &state.data[token.index];
            let value = (event.serviced && matches!(event.address, 0x40 | 0x46))
                .then(|| (event.operation == "Write", event.ordinal, event.pc));
            #[cfg(feature = "p28-word0196-below-second-p2-continuity")]
            if let (Some(second), Some((write, ordinal, pc))) = (state.below_second.as_mut(), value)
            {
                if pc == Some(second.control.pc) {
                    if write {
                        second.control.write = Some(ordinal);
                    } else {
                        second.control.reads.push(ordinal);
                    }
                }
            }
            if let (Some(control), Some((write, ordinal, pc))) =
                (state.post_control.as_mut(), value)
            {
                if pc != Some(control.pc) { /* preserve the first control generation */
                } else if write {
                    control.write = Some(ordinal);
                } else {
                    control.reads.push(ordinal);
                }
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
            #[cfg(feature = "p28-word0196-p2-handoff")]
            let p2_allowed = Self::p2_logical_right(&state, address, parent.width, write)?;
            #[cfg(not(feature = "p28-word0196-p2-handoff"))]
            let p2_allowed = false;
            #[cfg(feature = "p28-word0196-post-p2-control")]
            let control_allowed =
                Self::control_logical_right(&state, address, parent.width, write)?;
            #[cfg(not(feature = "p28-word0196-post-p2-control"))]
            let control_allowed = false;
            let allowed = if p2_allowed || control_allowed {
                true
            } else if state.phase == "Setup" {
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
