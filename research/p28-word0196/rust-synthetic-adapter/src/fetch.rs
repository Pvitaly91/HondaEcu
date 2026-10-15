use crate::{program::MicroProgram, AdapterError, Result};
use p28_slice_runner::decoder::{decode, Decoded};
use serde::{Deserialize, Serialize};
use std::{
    cell::RefCell,
    panic::{catch_unwind, panic_any, resume_unwind, AssertUnwindSafe},
};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ProgramEvent {
    pub ordinal: u32,
    pub address: u32,
    pub offset: usize,
    pub acquired_purpose: String,
    pub purpose: String,
    pub value: Option<u8>,
    pub fault: Option<AdapterError>,
}
#[derive(Default)]
struct FetchState {
    events: Vec<ProgramEvent>,
    sealed: bool,
    fault: Option<AdapterError>,
    selected_length: Option<usize>,
    selected_count: usize,
}
#[derive(Default)]
pub struct OrderedProgramFetchObserver {
    state: RefCell<FetchState>,
}
#[derive(Debug)]
struct FetchAbort(AdapterError);
impl OrderedProgramFetchObserver {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn read(&self, program: &MicroProgram, address: u32, purpose: &str) -> Result<u8> {
        if !matches!(
            purpose,
            "DecoderProbe" | "ArchitecturalSelectedFetch" | "DiagnosticProgramProbe"
        ) {
            return Err(AdapterError::new(
                "WrongProgramPurpose",
                "explicit read phase required",
            ));
        }
        let mut state = self.state.borrow_mut();
        let offset = address
            .checked_sub(0x1000)
            .map(|n| n as usize)
            .unwrap_or(usize::MAX);
        let ordinal = state.events.len() as u32 + 1;
        // The attempted read is acquired before touching immutable content.
        state.events.push(ProgramEvent {
            ordinal,
            address,
            offset,
            acquired_purpose: purpose.into(),
            purpose: purpose.into(),
            value: None,
            fault: None,
        });
        let read = if state.sealed {
            Err(AdapterError::new(
                "FetchAfterRetirement",
                "no next instruction/anchor fetch authorized",
            ))
        } else if let Some(error) = &state.fault {
            Err(error.clone())
        } else if purpose == "DecoderProbe" && state.selected_length.is_some() {
            Err(AdapterError::new(
                "DecoderAfterSelection",
                "phase is already selected",
            ))
        } else if purpose == "ArchitecturalSelectedFetch"
            && (state.selected_length.is_none()
                || state.selected_count != offset
                || state.selected_length.is_some_and(|len| offset >= len))
        {
            Err(AdapterError::new(
                "SelectedReadOrder",
                "each selected byte exactly once in order",
            ))
        } else {
            program.read(address)
        };
        match read {
            Ok(value) => {
                state.events.last_mut().expect("recorded attempt").value = Some(value);
                if purpose == "ArchitecturalSelectedFetch" {
                    state.selected_count += 1;
                }
                Ok(value)
            }
            Err(error) => {
                state.events.last_mut().expect("recorded attempt").fault = Some(error.clone());
                if state.fault.is_none() {
                    state.fault = Some(error.clone());
                }
                Err(error)
            }
        }
    }
    pub fn decode_checked(&self, program: &MicroProgram, dd: bool) -> Result<Decoded> {
        let result = catch_unwind(AssertUnwindSafe(|| {
            decode(dd, |offset| {
                let address = 0x1000u32
                    .checked_add(u32::try_from(offset).unwrap_or(u32::MAX))
                    .unwrap_or(u32::MAX);
                match self.read(program, address, "DecoderProbe") {
                    Ok(byte) => byte,
                    Err(error) => panic_any(FetchAbort(error)),
                }
            })
        }));
        match result {
            Ok(Some(decoded)) => Ok(decoded),
            Ok(None) => Err(AdapterError::new(
                "UndefinedOpcode",
                "no production pattern matched",
            )),
            Err(payload) => match payload.downcast::<FetchAbort>() {
                Ok(abort) => Err(abort.0),
                Err(unexpected) => resume_unwind(unexpected),
            },
        }
    }
    pub fn classify_decoder_lookahead(&self, selected_length: usize) -> Result<()> {
        let mut state = self.state.borrow_mut();
        if selected_length == 0
            || selected_length > 6
            || state.selected_length.is_some()
            || state.events.is_empty()
            || state
                .events
                .iter()
                .any(|e| e.acquired_purpose != "DecoderProbe" || e.fault.is_some())
        {
            return Err(AdapterError::new(
                "ObserverPhaseOrder",
                "classify immediately after decoder before selected reads",
            ));
        }
        for event in &mut state.events {
            if event.offset >= selected_length {
                event.purpose = "DecoderLookahead".into();
            }
        }
        state.selected_length = Some(selected_length);
        Ok(())
    }
    pub fn read_selected(&self, program: &MicroProgram, length: usize) -> Result<Vec<u8>> {
        if length != program.instruction_len()
            || self.state.borrow().selected_length != Some(length)
            || self.state.borrow().selected_count != 0
        {
            return Err(AdapterError::new(
                "WrongSelectedExtent",
                "literal instruction length, selected once after decode",
            ));
        }
        (0..length)
            .map(|off| self.read(program, 0x1000 + off as u32, "ArchitecturalSelectedFetch"))
            .collect()
    }
    pub fn seal_after_retirement(&self) {
        self.state.borrow_mut().sealed = true;
    }
    pub fn events(&self) -> Vec<ProgramEvent> {
        self.state.borrow().events.clone()
    }
    pub fn fault(&self) -> Option<AdapterError> {
        self.state.borrow().fault.clone()
    }
}
