use crate::{admission::FormId, AdapterError, Result};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RetirementEvent {
    pub ordinal: u32,
    pub pc: u16,
    pub next_pc: u16,
    pub form: FormId,
    pub external_transfer: bool,
}
pub struct SyntheticExternalExitTrap {
    retired: Vec<RetirementEvent>,
    terminal: Option<u16>,
    fault: Option<AdapterError>,
}
impl SyntheticExternalExitTrap {
    pub fn new(entry: u16, budget: u8) -> Result<Self> {
        if entry != 0x1000 || budget != 1 {
            return Err(AdapterError::new(
                "InvalidOneStepScope",
                "entry1000 and budget1; external entry and zero-step exit forbidden",
            ));
        }
        Ok(Self {
            retired: vec![],
            terminal: None,
            fault: None,
        })
    }
    pub fn before_fetch(&self) -> Result<()> {
        if let Some(error) = &self.fault {
            return Err(error.clone());
        }
        if self.terminal.is_some() || !self.retired.is_empty() {
            return Err(AdapterError::new(
                "FetchAfterRetirement",
                "one selected instruction only",
            ));
        }
        Ok(())
    }
    /// Called only after a real effect has completed in the research executor.
    /// Direct component tests may exercise this state transition without CPU
    /// execution and must report that distinct evidence level.
    pub fn record_retirement(&mut self, pc: u16, next_pc: u16, form: FormId) -> Result<()> {
        if self.fault.is_some()
            || self.terminal.is_some()
            || !self.retired.is_empty()
            || pc != 0x1000
        {
            let error = AdapterError::new(
                "ExtraRetirementOrTransfer",
                "one real instruction/at most one direct J",
            );
            self.fault = Some(error.clone());
            return Err(error);
        }
        let external = form == FormId::JAddress;
        if external && !matches!(next_pc, 0x5596 | 0x55c5) {
            let error = AdapterError::new("WrongExternalTarget", format!("{next_pc:04X}"));
            self.fault = Some(error.clone());
            return Err(error);
        }
        if !external && matches!(next_pc, 0x5596 | 0x55c5) {
            let error = AdapterError::new(
                "HiddenExternalTransfer",
                "only admitted direct J can terminate externally",
            );
            self.fault = Some(error.clone());
            return Err(error);
        }
        self.retired.push(RetirementEvent {
            ordinal: 1,
            pc,
            next_pc,
            form,
            external_transfer: external,
        });
        if external {
            self.terminal = Some(next_pc);
        }
        Ok(())
    }
    pub fn require_external_exit(&self, expected: u16) -> Result<()> {
        if let Some(error) = &self.fault {
            return Err(error.clone());
        }
        if self.terminal != Some(expected)
            || self.retired.len() != 1
            || self.retired[0].form != FormId::JAddress
        {
            return Err(AdapterError::new(
                "UnprovedExternalExit",
                "actual retired direct J and exact target required",
            ));
        }
        Ok(())
    }
    pub fn terminal(&self) -> Option<u16> {
        self.terminal
    }
    pub fn retirements(&self) -> &[RetirementEvent] {
        &self.retired
    }
}
