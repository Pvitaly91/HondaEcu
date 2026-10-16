//! Independent lifecycle guard. Only actual retired direct J can seal success.
use crate::{AdapterError, Result, BASE, HARD_BUDGET};
use p28_research_synthetic_adapter::FormId;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Retirement {
    pub ordinal: u32,
    pub pc_before: u16,
    pub pc_after: u16,
    pub form: FormId,
}
pub struct Lifecycle {
    retired: Vec<Retirement>,
    direct_j_count: u32,
    terminal: Option<u16>,
    faulted: bool,
    budget: u8,
    next_pc: u16,
}
impl Lifecycle {
    pub fn new(pc: u16, budget: u8) -> Result<Self> {
        if pc != BASE || budget == 0 || budget > HARD_BUDGET {
            return Err(AdapterError::new(
                "InvalidExecutionBudgetOrEntry",
                "entry1000/budget1..16",
            ));
        }
        Ok(Self {
            retired: vec![],
            direct_j_count: 0,
            terminal: None,
            faulted: false,
            budget,
            next_pc: pc,
        })
    }
    pub fn before_fetch(&self) -> Result<()> {
        if self.faulted {
            return Err(AdapterError::new(
                "ExecutionAfterFault",
                "lifecycle fault is terminal",
            ));
        }
        if self.terminal.is_some() {
            return Err(AdapterError::new(
                "ExecutionAfterExit",
                "direct J already retired",
            ));
        }
        if self.retired.len() >= usize::from(self.budget) {
            return Err(AdapterError::new(
                "InstructionBudgetExhausted",
                "no extra step permitted",
            ));
        }
        Ok(())
    }
    pub fn retire(&mut self, before: u16, after: u16, form: FormId) -> Result<()> {
        self.before_fetch()?;
        if before != self.next_pc {
            return Err(AdapterError::new(
                "RetirementContinuityFailure",
                "no zero-step exit or host PC jump",
            ));
        }
        let node = p28_research_synthetic_adapter::admission::ClosedFormAdmission::inventory()
            .into_iter()
            .find(|n| n.pc == before)
            .ok_or_else(|| AdapterError::new("UnknownInstructionBoundary", "retirement origin"))?;
        if node.form != form || !node.successors.contains(&after) {
            return Err(AdapterError::new(
                "UnretiredExternalExit",
                "exact node form and successor required",
            ));
        }
        if form == FormId::JAddress {
            if !matches!(after, 0x5596 | 0x55c5) || self.direct_j_count != 0 {
                return Err(AdapterError::new(
                    "InvalidDirectJExit",
                    "one actual known-anchor J",
                ));
            }
            self.direct_j_count += 1;
            self.terminal = Some(after);
        } else if matches!(after, 0x5596 | 0x55c5) {
            return Err(AdapterError::new(
                "UnretiredExternalExit",
                "PC alone cannot prove J",
            ));
        }
        self.retired.push(Retirement {
            ordinal: self.retired.len() as u32 + 1,
            pc_before: before,
            pc_after: after,
            form,
        });
        self.next_pc = after;
        Ok(())
    }
    pub fn mark_fault(&mut self) {
        self.faulted = true;
    }
    pub fn terminal(&self) -> Option<u16> {
        self.terminal
    }
    pub fn retired(&self) -> &[Retirement] {
        &self.retired
    }
    pub fn direct_j_count(&self) -> u32 {
        self.direct_j_count
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn zero_step_exit_and_oversized_budget_are_refused() {
        assert!(Lifecycle::new(0x5596, 16).is_err());
        assert!(Lifecycle::new(BASE, 17).is_err());
        assert!(Lifecycle::new(BASE, 0).is_err());
    }
    #[test]
    fn hard_budget_and_fault_are_terminal_without_cpu() {
        let mut life = Lifecycle::new(BASE, 1).unwrap();
        life.retire(BASE, BASE + 2, FormId::LbAPage).unwrap();
        assert_eq!(
            life.before_fetch().unwrap_err().code,
            "InstructionBudgetExhausted"
        );
        life.mark_fault();
        assert_eq!(life.before_fetch().unwrap_err().code, "ExecutionAfterFault");
        assert_eq!(life.retired().len(), 1);
    }
    #[test]
    fn direct_j_seals_and_second_transfer_is_refused() {
        let mut life = Lifecycle::new(BASE, 16).unwrap();
        assert!(life.retire(BASE, 0x5596, FormId::LbAPage).is_err());
        for (before, after, form) in [
            (0x1000, 0x1002, FormId::LbAPage),
            (0x1002, 0x1003, FormId::SllbA),
            (0x1003, 0x1006, FormId::RolbPage),
            (0x1006, 0x1007, FormId::LbAR0),
            (0x1007, 0x1009, FormId::AndbAPage),
            (0x1009, 0x100e, FormId::CmpPageImm16),
            (0x100e, 0x102a, FormId::JltRel8),
            (0x102a, 0x102c, FormId::LbAImm8),
            (0x102c, 0x102e, FormId::StbAPage),
            (0x102e, 0x1030, FormId::StbAPage),
            (0x1030, 0x55c5, FormId::JAddress),
        ] {
            life.retire(before, after, form).unwrap();
        }
        assert_eq!(life.before_fetch().unwrap_err().code, "ExecutionAfterExit");
        assert!(life.retire(0x1030, 0x55c5, FormId::JAddress).is_err());
        assert_eq!(life.direct_j_count(), 1);
    }
}
