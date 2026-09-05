// Minimal memory-only replacement for the pinned upstream Bus.
// No peripheral, timer, interrupt, engine or scenario model is imported.
use std::cell::RefCell;

pub const RAM_SIZE: usize = 4096;

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
            self.record_fault("data", address as u32, "read");
            return 0;
        }
        self.ram[address as usize]
    }
    pub fn read_data_u16(&mut self, address: u16) -> u16 {
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
            self.record_fault("data", address as u32, "write");
            return;
        }
        self.ram[address as usize] = value;
    }
    pub fn write_data_u16(&mut self, address: u16, value: u16) {
        let Some(high) = address.checked_add(1) else {
            self.record_fault("data", 65536, "write");
            return;
        };
        let bytes = value.to_le_bytes();
        self.write_data_u8(address, bytes[0]);
        self.write_data_u8(high, bytes[1]);
    }
}
