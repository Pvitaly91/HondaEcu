// Minimal memory-only replacement for the pinned upstream Bus.
// Old tasks remain memory-only. Acquisition alone can opt into three frozen,
// read-only peripheral observations; this is not a peripheral/IRQ simulator.
use std::cell::RefCell;

pub const RAM_SIZE: usize = 4096;

#[derive(Clone, Copy)]
pub(crate) struct CaptureObservation {
    pub tmr2: u16,
    pub irqh: u8,
    pub tcon2: u8,
}

#[cfg(test)]
mod capture_bus_tests {
    use super::*;
    use crate::cpu::Cpu;
    use crate::exec::{read_data_u16, read_data_u8, write_data_u16, write_data_u8};

    #[test]
    fn old_bus_has_no_peripheral_observations_and_word_width_is_preserved() {
        let cpu = Cpu::new();
        let mut bus = Bus::new(vec![], 0xAA);
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x3A), 0);
        assert!(bus.take_fault().is_some());
        bus.observe_capture(Some(CaptureObservation {
            tmr2: 0xFEDC,
            irqh: 0x81,
            tcon2: 4,
        }));
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x3A), 0xFEDC);
        assert_eq!(read_data_u8(&cpu, &mut bus, 0x19), 0x81);
        assert_eq!(read_data_u8(&cpu, &mut bus, 0x42), 4);
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x3A), 0xFEDC);
        assert_eq!(
            bus.peripheral_accesses(),
            [
                [0x3A, 16, 0, 0xFEDC],
                [0x19, 8, 0, 0x81],
                [0x42, 8, 0, 4],
                [0x3A, 16, 0, 0xFEDC]
            ]
        );
        assert!(bus.take_fault().is_none());
        bus.observe_capture(None);
        read_data_u8(&cpu, &mut bus, 0x19);
        assert!(bus.take_fault().is_some());
    }

    #[test]
    fn frozen_observations_reject_wrong_width_unknown_sfr_and_all_writes() {
        let mut cpu = Cpu::new();
        let mut bus = Bus::new(vec![], 0);
        bus.observe_capture(Some(CaptureObservation {
            tmr2: 0x1234,
            irqh: 1,
            tcon2: 4,
        }));
        for address in [0x3A, 0x3B, 0x18, 0x43] {
            read_data_u8(&cpu, &mut bus, address);
            assert!(bus.take_fault().is_some());
        }
        for address in [0x19, 0x42, 0x38] {
            read_data_u16(&cpu, &mut bus, address);
            assert!(bus.take_fault().is_some());
        }
        write_data_u8(&mut cpu, &mut bus, 0x42, 0);
        assert!(bus.take_fault().is_some());
        write_data_u16(&mut cpu, &mut bus, 0x3A, 0);
        assert!(bus.take_fault().is_some());
        assert_eq!(
            bus.peripheral_accesses(),
            [[0x42, 8, 1, 0], [0x3A, 16, 1, 0]]
        );
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x3A), 0x1234);
        assert_eq!(read_data_u8(&cpu, &mut bus, 0x42), 4);
    }

    #[test]
    fn native_journal_retains_same_value_and_partial_stores_without_harness_seeds() {
        let mut cpu = Cpu::new();
        let mut bus = Bus::new(vec![], 0xAA);
        write_data_u16(&mut cpu, &mut bus, 0x360, 0xBEEF);
        bus.begin_write_journal();
        write_data_u16(&mut cpu, &mut bus, 0x360, 0xBEEF);
        write_data_u8(&mut cpu, &mut bus, 0x363, 0xAA);
        write_data_u16(&mut cpu, &mut bus, 0xFFF, 0xCAFE);
        assert!(bus.take_fault().is_some());
        assert_eq!(
            bus.end_write_journal(),
            [[0x360, 16, 0xBEEF], [0x363, 8, 0xAA], [0xFFF, 8, 0xFE]]
        );
        assert!(bus.end_write_journal().is_empty());
    }

    #[test]
    fn p1_is_explicit_byte_output_data_only_and_never_a_generic_sfr_stub() {
        let mut cpu = Cpu::new();
        let mut bus = Bus::new(vec![], 0);
        read_data_u8(&cpu, &mut bus, 0x22);
        assert!(bus.take_fault().is_some());
        bus.set_p1_output_latch(Some(0xA4));
        assert_eq!(read_data_u8(&cpu, &mut bus, 0x22), 0xA4);
        bus.begin_write_journal();
        write_data_u8(&mut cpu, &mut bus, 0x22, 0xA4);
        assert_eq!(bus.end_write_journal(), [[0x22, 8, 0xA4]]);
        write_data_u16(&mut cpu, &mut bus, 0x22, 0xFFFF);
        assert!(bus.take_fault().is_some());
        assert_eq!(bus.p1_output_latch(), Some(0xA4));
        for address in [0x22, 0x23, 0x24] {
            read_data_u16(&cpu, &mut bus, address);
            assert!(bus.take_fault().is_some());
        }
        write_data_u8(&mut cpu, &mut bus, 0x23, 0xFF);
        assert!(bus.take_fault().is_some());
        bus.set_p1_output_latch(None);
        read_data_u8(&cpu, &mut bus, 0x22);
        assert!(bus.take_fault().is_some());
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AccessFault {
    pub space: &'static str,
    pub address: u32,
    pub operation: &'static str,
}

impl std::fmt::Display for AccessFault {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "{} {} outside modeled memory at {:#06X}",
            self.space, self.operation, self.address
        )
    }
}

pub struct Bus {
    rom: Vec<u8>,
    ram: [u8; RAM_SIZE],
    fault: RefCell<Option<AccessFault>>,
    program_reads: RefCell<Vec<u16>>,
    ordered_reads: bool,
    read_limit: usize,
    data_ranges: Option<Vec<[u16; 2]>>,
    capture: Option<CaptureObservation>,
    peripheral_accesses: Vec<[u32; 4]>,
    journal_writes: bool,
    data_writes: Vec<[u32; 3]>,
    p1_output_latch: Option<u8>,
    decision_events: Option<Vec<[u32; 8]>>,
    comparison_operands: [u32; 2],
    program_data_ranges: Option<Vec<[u16; 2]>>,
}

impl Bus {
    pub fn new(rom: Vec<u8>, scratch: u8) -> Self {
        Self {
            rom,
            ram: [scratch; RAM_SIZE],
            fault: RefCell::new(None),
            program_reads: RefCell::new(Vec::new()),
            ordered_reads: false,
            read_limit: 256,
            data_ranges: None,
            capture: None,
            peripheral_accesses: vec![],
            journal_writes: false,
            data_writes: vec![],
            p1_output_latch: None,
            decision_events: None,
            comparison_operands: [65536; 2],
            program_data_ranges: None,
        }
    }

    pub fn record_fault(&self, space: &'static str, address: u32, operation: &'static str) {
        let mut fault = self.fault.borrow_mut();
        if fault.is_none() {
            *fault = Some(AccessFault {
                space,
                address,
                operation,
            });
        }
    }

    pub fn take_fault(&self) -> Option<AccessFault> {
        self.fault.borrow_mut().take()
    }
    pub fn program_reads(&self) -> Vec<u16> {
        self.program_reads.borrow().clone()
    }
    pub fn clear_program_reads(&self) {
        self.program_reads.borrow_mut().clear();
    }
    /// M1j only: P1IO=FF, output-data-register reads, external bus disabled.
    /// This models no pins, loads, feedback, interrupts or peripheral time.
    pub(crate) fn set_p1_output_latch(&mut self, value: Option<u8>) {
        self.p1_output_latch = value;
    }
    pub(crate) fn p1_output_latch(&self) -> Option<u8> {
        self.p1_output_latch
    }
    pub(crate) fn start_decision_observer(&mut self) {
        self.decision_events = Some(vec![]);
    }
    pub(crate) fn decision_observing(&self) -> bool {
        self.decision_events.is_some()
    }
    pub(crate) fn clear_comparison_operands(&mut self) {
        self.comparison_operands = [65536; 2];
    }
    pub(crate) fn observe_comparison(&mut self, lhs: u16, rhs: u16) {
        self.comparison_operands = [lhs as u32, rhs as u32];
    }
    pub(crate) fn observe_instruction(&mut self, event: [u32; 6]) {
        if let Some(events) = self.decision_events.as_mut() {
            if events.len() < 512 {
                events.push([
                    event[0],
                    event[1],
                    event[2],
                    event[3],
                    event[4],
                    event[5],
                    self.comparison_operands[0],
                    self.comparison_operands[1],
                ]);
            }
        }
    }
    pub(crate) fn finish_decision_observer(&mut self) -> Vec<[u32; 8]> {
        self.decision_events.take().unwrap_or_default()
    }
    pub(crate) fn set_program_data_ranges(&mut self, ranges: Vec<[u16; 2]>) {
        self.program_data_ranges = Some(ranges);
    }
    pub(crate) fn observe_capture(&mut self, observation: Option<CaptureObservation>) {
        self.capture = observation;
        self.peripheral_accesses.clear();
    }
    pub(crate) fn begin_write_journal(&mut self) {
        self.data_writes.clear();
        self.journal_writes = true;
    }
    pub(crate) fn end_write_journal(&mut self) -> Vec<[u32; 3]> {
        self.journal_writes = false;
        std::mem::take(&mut self.data_writes)
    }
    pub(crate) fn peripheral_accesses(&self) -> Vec<[u32; 4]> {
        self.peripheral_accesses.clone()
    }
    /// Opt-in for incremental checksum calls; old slice logging is unchanged.
    pub fn configure_scoped_access(&mut self, data_ranges: Vec<[u16; 2]>, read_limit: usize) {
        self.data_ranges = Some(data_ranges);
        self.ordered_reads = true;
        self.read_limit = read_limit;
    }
    pub fn check_data_access(&self, address: u16, operation: &'static str) -> bool {
        if self
            .data_ranges
            .as_ref()
            .is_some_and(|ranges| !ranges.iter().any(|r| address >= r[0] && address < r[1]))
        {
            self.record_fault("data", address as u32, operation);
            false
        } else {
            true
        }
    }
    pub fn program_reads_within(&self, range: [u32; 2]) -> bool {
        self.program_reads
            .borrow()
            .iter()
            .all(|a| (*a as u32) >= range[0] && (*a as u32) < range[1])
    }
    pub fn rom_len(&self) -> usize {
        self.rom.len()
    }
    pub fn peek_code_u8(&self, address: usize) -> Option<u8> {
        self.rom.get(address).copied()
    }

    pub fn fetch_code_u8(&self, address: u16) -> u8 {
        match self.rom.get(address as usize) {
            Some(byte) => *byte,
            None => {
                self.record_fault("code", address as u32, "fetch");
                0
            }
        }
    }

    pub fn read_code_u8(&self, address: u16) -> u8 {
        if self
            .program_data_ranges
            .as_ref()
            .is_some_and(|ranges| !ranges.iter().any(|r| address >= r[0] && address < r[1]))
        {
            self.record_fault("program-data", address as u32, "read");
            return 0;
        }
        let mut reads = self.program_reads.borrow_mut();
        // The runner has a bounded instruction budget; unique addresses avoid
        // a trace per successful repeated table read.
        if self.ordered_reads || !reads.contains(&address) {
            if reads.len() < self.read_limit {
                reads.push(address);
            } else {
                self.record_fault("code", address as u32, "read-log-limit");
            }
        }
        match self.rom.get(address as usize) {
            Some(byte) => *byte,
            None => {
                self.record_fault("code", address as u32, "read");
                0
            }
        }
    }

    pub fn read_code_u16(&self, address: u16) -> u16 {
        let Some(high) = address.checked_add(1) else {
            self.record_fault("code", 65536, "read");
            return 0;
        };
        u16::from_le_bytes([self.read_code_u8(address), self.read_code_u8(high)])
    }

    // CPU aliases 0..7 are handled only by exec's coherent state API. Other
    // SFRs 8..7F are deliberately unmodeled and fail, never masquerading as RAM.
    pub fn read_data_u8(&mut self, address: u16) -> u8 {
        if !self.check_data_access(address, "read") {
            return 0;
        }
        if !(0x80..RAM_SIZE).contains(&(address as usize)) {
            if address == 0x22 {
                if let Some(value) = self.p1_output_latch {
                    return value;
                }
            }
            if let Some(observation) = self.capture {
                let value = match address {
                    0x19 => Some(observation.irqh),
                    0x42 => Some(observation.tcon2),
                    _ => None,
                };
                if let Some(value) = value {
                    self.peripheral_accesses
                        .push([address as u32, 8, 0, value as u32]);
                    return value;
                }
            }
            self.record_fault("data", address as u32, "read");
            return 0;
        }
        self.ram[address as usize]
    }
    pub fn read_data_u16(&mut self, address: u16) -> u16 {
        if address < 0x80 {
            if self.check_data_access(address, "read")
                && self.check_data_access(address.saturating_add(1), "read")
                && address == 0x3A
            {
                if let Some(observation) = self.capture {
                    self.peripheral_accesses
                        .push([address as u32, 16, 0, observation.tmr2 as u32]);
                    return observation.tmr2;
                }
            }
            self.record_fault("data", address as u32, "read-word");
            return 0;
        }
        let Some(high) = address.checked_add(1) else {
            self.record_fault("data", 65536, "read");
            return 0;
        };
        u16::from_le_bytes([self.read_data_u8(address), self.read_data_u8(high)])
    }
    pub fn write_data_u8(&mut self, address: u16, value: u8) {
        if !self.check_data_access(address, "write") {
            return;
        }
        if !(0x80..RAM_SIZE).contains(&(address as usize)) {
            if address == 0x22 && self.p1_output_latch.is_some() {
                self.p1_output_latch = Some(value);
                if self.journal_writes {
                    self.data_writes.push([0x22, 8, value as u32]);
                }
                return;
            }
            if self.capture.is_some() {
                self.peripheral_accesses
                    .push([address as u32, 8, 1, value as u32]);
            }
            self.record_fault("data", address as u32, "write");
            return;
        }
        self.ram[address as usize] = value;
        if self.journal_writes {
            self.data_writes.push([address as u32, 8, value as u32]);
        }
    }
    pub fn write_data_u16(&mut self, address: u16, value: u16) {
        if address < 0x80 && (self.capture.is_some() || self.p1_output_latch.is_some()) {
            self.peripheral_accesses
                .push([address as u32, 16, 1, value as u32]);
            self.record_fault("data", address as u32, "write-word");
            return;
        }
        let Some(high) = address.checked_add(1) else {
            self.record_fault("data", 65536, "write");
            return;
        };
        let bytes = value.to_le_bytes();
        let before = self.data_writes.len();
        self.write_data_u8(address, bytes[0]);
        self.write_data_u8(high, bytes[1]);
        // A successful architectural word store is one journal event, even
        // when the stored value was already present. Partial stores retain
        // their actual byte events instead of claiming a completed word write.
        if self.journal_writes && self.data_writes.len() == before + 2 {
            self.data_writes.truncate(before);
            self.data_writes.push([address as u32, 16, value as u32]);
        }
    }
}
