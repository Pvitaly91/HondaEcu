//! Every actual production decoder callback is acquired before servicing it.
//! Public projection intentionally omits all PROGRAM byte values.
use crate::{program::VerifiedComposite, AdapterError, Result, BASE};
use p28_slice_runner::decoder::{decode, Decoded};
use serde::{Deserialize, Serialize};
use std::{
    cell::RefCell,
    panic::{catch_unwind, panic_any, resume_unwind, AssertUnwindSafe},
};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProgramEvent {
    pub ordinal: u32,
    pub step: u32,
    pub pc: u16,
    pub address: u32,
    pub offset: Option<u32>,
    pub instruction_offset: Option<u32>,
    pub acquired_purpose: String,
    pub purpose: String,
    pub selected_extent_length: Option<usize>,
    pub serviced: bool,
    pub refusal: Option<AdapterError>,
}
#[derive(Default)]
struct State {
    events: Vec<ProgramEvent>,
    sealed: bool,
    fault: Option<AdapterError>,
    pc: Option<u16>,
    step: u32,
    start_event: usize,
    selected_length: Option<usize>,
    selected_count: usize,
    open: bool,
}
#[derive(Default)]
pub struct ProgramObserver {
    state: RefCell<State>,
}
#[derive(Debug)]
struct FetchAbort(AdapterError);
impl ProgramObserver {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn begin_instruction(&self, pc: u16, step: u32) -> Result<()> {
        let mut state = self.state.borrow_mut();
        if state.sealed || state.fault.is_some() || state.open {
            return Err(AdapterError::new(
                "ProgramObserverNotLive",
                "sealed/faulted/unfinished phase",
            ));
        }
        state.pc = Some(pc);
        state.step = step;
        state.start_event = state.events.len();
        state.selected_length = None;
        state.selected_count = 0;
        state.open = true;
        Ok(())
    }
    pub fn read(&self, program: &VerifiedComposite, address: u32, purpose: &str) -> Result<u8> {
        let mut state = self.state.borrow_mut();
        let pc = state.pc.unwrap_or(BASE);
        let offset = address.checked_sub(u32::from(BASE));
        let instruction_offset = address.checked_sub(u32::from(pc));
        let ordinal = state.events.len() as u32 + 1;
        let event = ProgramEvent {
            ordinal,
            step: state.step,
            pc,
            address,
            offset,
            instruction_offset,
            acquired_purpose: purpose.into(),
            purpose: purpose.into(),
            selected_extent_length: state.selected_length,
            serviced: false,
            refusal: None,
        };
        state.events.push(event);
        let result = if state.sealed {
            Err(AdapterError::new(
                "ProgramAccessAfterExit",
                "observer independently seals after J",
            ))
        } else if let Some(fault) = &state.fault {
            Err(fault.clone())
        } else if !state.open {
            Err(AdapterError::new(
                "ProgramAccessOutsideInstruction",
                "explicit active phase required",
            ))
        } else if !matches!(
            purpose,
            "DecoderProbe" | "ArchitecturalSelectedFetch" | "DiagnosticProgramProbe"
        ) {
            Err(AdapterError::new(
                "WrongProgramPurpose",
                "closed acquisition purposes",
            ))
        } else if purpose == "DecoderProbe" && state.selected_length.is_some() {
            Err(AdapterError::new(
                "DecoderAfterSelection",
                "no decoder callbacks after selection",
            ))
        } else if purpose == "ArchitecturalSelectedFetch"
            && (state.selected_length.is_none()
                || instruction_offset != Some(state.selected_count as u32)
                || state
                    .selected_length
                    .is_some_and(|n| state.selected_count >= n))
        {
            Err(AdapterError::new(
                "SelectedReadOrder",
                "one in-order selected extent only",
            ))
        } else {
            program.read(address)
        };
        match result {
            Ok(value) => {
                state
                    .events
                    .last_mut()
                    .expect("actual acquired attempt")
                    .serviced = true;
                if purpose == "ArchitecturalSelectedFetch" {
                    state.selected_count += 1;
                }
                Ok(value)
            }
            Err(error) => {
                state
                    .events
                    .last_mut()
                    .expect("actual acquired attempt")
                    .refusal = Some(error.clone());
                if state.fault.is_none() {
                    state.fault = Some(error.clone());
                }
                Err(error)
            }
        }
    }
    pub fn decode_checked(&self, program: &VerifiedComposite, dd: bool) -> Result<Decoded> {
        let pc = self
            .state
            .borrow()
            .pc
            .ok_or_else(|| AdapterError::new("NoDecoderPc", "phase"))?;
        let result = catch_unwind(AssertUnwindSafe(|| {
            decode(dd, |offset| {
                let address = u32::try_from(offset)
                    .ok()
                    .and_then(|n| u32::from(pc).checked_add(n))
                    .unwrap_or(u32::MAX);
                match self.read(program, address, "DecoderProbe") {
                    Ok(value) => value,
                    Err(error) => panic_any(FetchAbort(error)),
                }
            })
        }));
        match result {
            Ok(Some(decoded)) => Ok(decoded),
            Ok(None) => Err(AdapterError::new(
                "UndefinedOpcode",
                "actual unchanged decoder",
            )),
            Err(payload) => match payload.downcast::<FetchAbort>() {
                Ok(abort) => Err(abort.0),
                Err(unexpected) => resume_unwind(unexpected),
            },
        }
    }
    pub fn associate_selection(&self, length: usize) -> Result<()> {
        let mut state = self.state.borrow_mut();
        if !state.open
            || state.selected_length.is_some()
            || length == 0
            || length > 5
            || state.fault.is_some()
            || state.events.len() == state.start_event
        {
            return Err(AdapterError::new(
                "ObserverPhaseOrder",
                "actual decode then association",
            ));
        }
        let start = state.start_event;
        for event in &mut state.events[start..] {
            if event.acquired_purpose != "DecoderProbe"
                || !event.serviced
                || event.refusal.is_some()
            {
                return Err(AdapterError::new(
                    "ObserverIntegrityFailure",
                    "nondecoder event before association",
                ));
            }
            event.selected_extent_length = Some(length);
            if event
                .instruction_offset
                .is_some_and(|n| n as usize >= length)
            {
                event.purpose = "DecoderLookahead".into();
            }
        }
        state.selected_length = Some(length);
        Ok(())
    }
    pub fn selected(&self, program: &VerifiedComposite, length: usize) -> Result<Vec<u8>> {
        let state = self.state.borrow();
        if state.selected_length != Some(length) || state.selected_count != 0 {
            return Err(AdapterError::new(
                "WrongSelectedExtent",
                "single post-selection acquisition",
            ));
        }
        let pc = state
            .pc
            .ok_or_else(|| AdapterError::new("NoSelectedPc", "phase"))?;
        drop(state);
        (0..length)
            .map(|offset| {
                let address = u32::from(pc)
                    .checked_add(offset as u32)
                    .ok_or_else(|| AdapterError::new("ProgramOverflow", "selected extent"))?;
                self.read(program, address, "ArchitecturalSelectedFetch")
            })
            .collect()
    }
    pub fn finish_retirement(&self, external: bool) -> Result<()> {
        let mut state = self.state.borrow_mut();
        if state.fault.is_some()
            || !state.open
            || state.selected_length != Some(state.selected_count)
        {
            return Err(AdapterError::new(
                "IncompleteProgramSelection",
                "all selected reads required",
            ));
        }
        state.open = false;
        if external {
            state.sealed = true;
        }
        Ok(())
    }
    pub fn mark_fault(&self, error: AdapterError) {
        let mut state = self.state.borrow_mut();
        if state.fault.is_none() {
            state.fault = Some(error);
        }
    }
    pub fn events(&self) -> Vec<ProgramEvent> {
        self.state.borrow().events.clone()
    }
    pub fn is_sealed(&self) -> bool {
        self.state.borrow().sealed
    }
}
