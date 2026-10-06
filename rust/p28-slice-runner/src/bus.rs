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
    fn opt_in_access_journal_keeps_word_width_pc_order_and_faults() {
        let mut bus = Bus::new(vec![], 0xA5);
        bus.write_data_u16(0x140, 0x1234);
        assert!(bus.end_native_accesses().is_empty());
        bus.begin_native_accesses();
        bus.set_native_pc(42);
        assert_eq!(bus.read_data_u16(0x140), 0x1234);
        bus.write_data_u16(0x158, 0x5678);
        bus.set_native_pc(44);
        bus.write_data_u16(0xFFF, 0xBEEF);
        assert!(bus.take_fault().is_some());
        assert_eq!(
            bus.end_native_accesses(),
            [
                [42, 0x140, 16, 0, 0x1234],
                [42, 0x158, 16, 1, 0x5678],
                [44, 0xFFF, 8, 1, 0xEF]
            ]
        );
        assert!(bus.end_native_accesses().is_empty());
        bus.write_data_u16(0xFFF, 0xCAFE);
        assert!(bus.take_fault().is_some()); // observation never consumes a fault
    }

    #[test]
    fn adaptive_ie_is_opt_in_word_only_scoped_storage_with_same_value_journal() {
        let mut cpu = Cpu::new();
        let mut bus = Bus::new(vec![], 0);
        read_data_u16(&cpu, &mut bus, 0x1A);
        assert!(bus.take_fault().is_some());
        bus.set_adaptive_ie(Some(0xA55A));
        bus.configure_scoped_access(vec![[0x1A, 0x1C]], 8);
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x1A), 0xA55A);
        bus.begin_write_journal();
        write_data_u16(&mut cpu, &mut bus, 0x1A, 0xA55A);
        assert_eq!(bus.end_write_journal(), [[0x1A, 16, 0xA55A]]);
        for a in [0x1A, 0x1B] {
            read_data_u8(&cpu, &mut bus, a);
            assert!(bus.take_fault().is_some());
            write_data_u8(&mut cpu, &mut bus, a, 0);
            assert!(bus.take_fault().is_some());
        }
        read_data_u16(&cpu, &mut bus, 0x1C);
        assert!(bus.take_fault().is_some());
        assert_eq!(bus.adaptive_ie(), Some(0xA55A));
        bus.configure_scoped_access(vec![], 8);
        write_data_u16(&mut cpu, &mut bus, 0x1A, 0);
        assert!(bus.take_fault().is_some());
        assert_eq!(bus.adaptive_ie(), Some(0xA55A));
        bus.set_adaptive_ie(None);
        read_data_u16(&cpu, &mut bus, 0x1A);
        assert!(bus.take_fault().is_some());
    }

    #[test]
    fn adaptive_ie_native_ledger_is_word_only_and_access_changes_preserve_storage() {
        let mut bus = Bus::new(vec![], 0xA5);
        bus.set_adaptive_ie(Some(0xBA98));
        bus.configure_scoped_access(
            vec![[0x1A, 0x1C], [0x1A4, 0x1A8], [0x1D5, 0x1D6], [0x7FE, 0x800]],
            32,
        );
        bus.write_data_u16(0x1A4, 1234);
        bus.write_data_u16(0x1A6, 1278);
        bus.write_data_u8(0x1D5, 7);
        bus.write_data_u16(0x7FE, 4321);
        bus.begin_native_accesses();
        bus.set_native_pc(123);
        assert_eq!(bus.read_data_u16(0x1A), 0xBA98);
        bus.write_data_u16(0x1A, 0xBA98);
        assert_eq!(
            bus.end_native_accesses(),
            [[123, 0x1A, 16, 0, 0xBA98], [123, 0x1A, 16, 1, 0xBA98]]
        );
        bus.configure_scoped_access(vec![], 32);
        bus.configure_scoped_access(vec![[0x1A4, 0x1A8], [0x1D5, 0x1D6], [0x7FE, 0x800]], 32);
        assert_eq!(bus.adaptive_ie(), Some(0xBA98));
        assert_eq!(bus.read_data_u16(0x1A4), 1234);
        assert_eq!(bus.read_data_u16(0x1A6), 1278);
        assert_eq!(bus.read_data_u8(0x1D5), 7);
        assert_eq!(bus.read_data_u16(0x7FE), 4321);
        assert!(bus.take_fault().is_none());
    }

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

    #[test]
    fn p1_stage_capability_switch_preserves_latch_and_denies_reads_and_writes() {
        let mut cpu = Cpu::new();
        let mut bus = Bus::new(vec![], 0);
        bus.set_p1_output_latch(Some(0xB5));
        bus.set_p1_access(false);
        read_data_u8(&cpu, &mut bus, 0x22);
        assert!(bus.take_fault().is_some());
        write_data_u8(&mut cpu, &mut bus, 0x22, 0);
        assert!(bus.take_fault().is_some());
        assert_eq!(bus.p1_output_latch(), Some(0xB5));
        bus.observe_capture(Some(CaptureObservation {
            tmr2: 99,
            irqh: 0,
            tcon2: 0,
        }));
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x3A), 99);
        bus.observe_capture(None);
        bus.set_p1_access(true);
        assert_eq!(read_data_u8(&cpu, &mut bus, 0x22), 0xB5);
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
    p1_access: bool,
    p2_output_latch: Option<u8>,
    p2_access: bool,
    p2_access_pc: Option<u16>,
    all_native: Option<Vec<[u32; 6]>>,
    p2_accesses: Vec<[u32; 5]>,
    // M2ab only: stopped realtime-output control and transition flag storage.
    // No clock, pin edges, command register, pending IRQ or generic SFR map.
    post_p2_control: Option<[u8; 2]>,
    control_access: Option<(u16, u16)>, // exact address and native instruction PC
    control_accesses: Vec<[u32; 5]>,
    limiter_p4: Option<u8>,
    adaptive_ie: Option<u16>,
    decision_events: Option<Vec<[u32; 8]>>,
    comparison_operands: [u32; 2],
    program_data_ranges: Option<Vec<[u16; 2]>>,
    // Opt-in M2k data-space observation. Never active during host snapshots.
    native_accesses: Option<Vec<[u32; 5]>>,
    native_pc: u16,
    // M2w opt-in, independent of nested historical journals. [native,pc,address,width,write,value].
    continuity: Option<Vec<[u32; 6]>>,
    // M2ae only: actual RAM013C, initialized once then writable only by064A.
    retained_selector: bool,
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
            p1_access: false,
            p2_output_latch: None,
            p2_access: false,
            p2_access_pc: None,
            all_native: None,
            p2_accesses: vec![],
            post_p2_control: None,
            control_access: None,
            control_accesses: vec![],
            limiter_p4: None,
            adaptive_ie: None,
            decision_events: None,
            comparison_operands: [65536; 2],
            program_data_ranges: None,
            native_accesses: None,
            native_pc: 0,
            continuity: None,
            retained_selector: false,
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
    /// Isolated limiter only: frozen software read of P4 bit0, no output/pins.
    pub(crate) fn observe_limiter_p4(&mut self, value: Option<u8>) {
        self.limiter_p4 = value.map(|v| v & 1);
    }

    pub fn take_fault(&self) -> Option<AccessFault> {
        self.fault.borrow_mut().take()
    }
    pub(crate) fn initialize_post_p2_control(
        &mut self,
        tcon0: u8,
        trnsit_flags: u8,
    ) -> Result<(), String> {
        if self.post_p2_control.is_some() || tcon0 & !0x0C != 0x83 || trnsit_flags > 15 {
            return Err(
                "M2ab requires once-only stopped realtime-output TCON0 and four TRNSIT flags"
                    .into(),
            );
        }
        self.post_p2_control = Some([tcon0, trnsit_flags]);
        Ok(())
    }
    pub(crate) fn post_p2_control(&self) -> Option<[u8; 2]> {
        self.post_p2_control
    }
    pub(crate) fn set_control_access(&mut self, capability: Option<(u16, u16)>) {
        self.control_access = capability;
        self.control_accesses.clear();
    }
    pub(crate) fn control_accesses(&self) -> Vec<[u32; 5]> {
        self.control_accesses.clone()
    }
    fn control_enabled(&self, address: u16) -> bool {
        self.post_p2_control.is_some()
            && self.native_accesses.is_some()
            && self.control_access == Some((address, self.native_pc))
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
        self.p1_access = value.is_some();
    }
    /// Stage capability only: disabling access must never erase the latch.
    pub(crate) fn set_p1_access(&mut self, enabled: bool) {
        self.p1_access = enabled;
    }
    pub(crate) fn p1_output_latch(&self) -> Option<u8> {
        self.p1_output_latch
    }
    /// M2aa only. Primary MSM66201/207 section5.5/Table5-3: P2IO=FF,
    /// P2SF implemented bits=0. This is output DATA, never pins or RAM.
    /// Reset data is undefined; a reviewed once-initial architectural snapshot
    /// is required. A second initialization is refused, including equal values.
    pub(crate) fn initialize_p2_output_latch(&mut self, value: u8) -> Result<(), String> {
        if self.p2_output_latch.is_some() {
            return Err("P2 architectural snapshot may only be initialized once".into());
        }
        self.p2_output_latch = Some(value);
        Ok(())
    }
    pub(crate) fn set_p2_access(&mut self, enabled: bool) {
        self.p2_access = enabled;
    }
    pub(crate) fn set_p2_access_pc(&mut self, pc: Option<u16>) {
        self.p2_access_pc = pc;
    }
    fn p2_enabled(&self) -> bool {
        self.native_accesses.is_some()
            && (self.p2_access || self.p2_access_pc == Some(self.native_pc))
    }
    pub(crate) fn begin_all_native(&mut self) {
        self.all_native = Some(vec![]);
    }
    pub(crate) fn all_native_snapshot(&self) -> Vec<[u32; 6]> {
        self.all_native.clone().unwrap_or_default()
    }
    pub(crate) fn end_all_native(&mut self) -> Vec<[u32; 6]> {
        self.all_native.take().unwrap_or_default()
    }
    fn observe_all(&mut self, space: u32, address: u16, width: u32, write: u32, value: u16) {
        if self.native_accesses.is_some() {
            if let Some(v) = self.all_native.as_mut() {
                v.push([
                    space,
                    self.native_pc as u32,
                    address as u32,
                    width,
                    write,
                    value as u32,
                ]);
            }
        }
    }
    /// Non-native diagnostic inspection; never a readback proof.
    pub(crate) fn p2_output_latch(&self) -> Option<u8> {
        self.p2_output_latch
    }
    pub(crate) fn begin_p2_accesses(&mut self) {
        self.p2_accesses.clear();
    }
    pub(crate) fn p2_accesses(&self) -> Vec<[u32; 5]> {
        self.p2_accesses.clone()
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
    pub(crate) fn begin_native_accesses(&mut self) {
        self.native_accesses = Some(vec![]);
    }
    pub(crate) fn end_native_accesses(&mut self) -> Vec<[u32; 5]> {
        self.native_accesses.take().unwrap_or_default()
    }
    pub(crate) fn set_native_pc(&mut self, pc: u16) {
        self.native_pc = pc;
    }
    fn native_access(&mut self, address: u16, width: u32, write: u32, value: u16) {
        self.observe_all(0, address, width, write, value);
        let native = self.native_accesses.is_some();
        if native || write == 1 {
            if let Some(rows) = self.continuity.as_mut() {
                if rows.len() < 32768 {
                    rows.push([
                        u32::from(native),
                        if native {
                            u32::from(self.native_pc)
                        } else {
                            65536
                        },
                        u32::from(address),
                        width,
                        write,
                        u32::from(value),
                    ]);
                } else {
                    self.record_fault("data", address as u32, "continuity observation limit");
                }
            }
        }
        if let Some(rows) = self.native_accesses.as_mut() {
            if rows.len() < 4096 {
                rows.push([
                    self.native_pc as u32,
                    address as u32,
                    width,
                    write,
                    value as u32,
                ]);
            } else {
                self.record_fault("data", address as u32, "native observation limit");
            }
        }
    }
    pub(crate) fn begin_continuity(&mut self) {
        self.continuity = Some(vec![]);
    }
    pub(crate) fn end_continuity(&mut self) -> Vec<[u32; 6]> {
        self.continuity.take().unwrap_or_default()
    }
    pub(crate) fn continuity_snapshot(&self) -> Vec<[u32; 6]> {
        self.continuity.clone().unwrap_or_default()
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
        if self.retained_selector
            && address == 0x13C
            && operation == "write"
            && (self.native_accesses.is_none() || self.native_pc != 0x064A)
        {
            self.record_fault("data", address as u32, "selector-host-or-unreviewed-writer");
            return false;
        }
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
            if matches!(address, 0x40 | 0x46) && self.control_enabled(address) {
                let state = self.post_p2_control.unwrap();
                let value = if address == 0x40 {
                    state[0]
                } else {
                    state[1] | 0xF0
                };
                self.control_accesses.push([
                    self.native_pc as u32,
                    address as u32,
                    8,
                    0,
                    value as u32,
                ]);
                self.observe_all(2, address, 8, 0, value as u16);
                return value;
            }
            if address == 0x24 && self.p2_enabled() {
                if let Some(value) = self.p2_output_latch {
                    self.p2_accesses
                        .push([self.native_pc as u32, 0x24, 8, 0, value as u32]);
                    self.observe_all(1, address, 8, 0, value as u16);
                    return value;
                }
            }
            if address == 0x2C {
                if let Some(value) = self.limiter_p4 {
                    return value;
                }
            }
            if address == 0x22 && self.p1_access {
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
        let value = self.ram[address as usize];
        self.native_access(address, 8, 0, value as u16);
        value
    }
    pub fn read_data_u16(&mut self, address: u16) -> u16 {
        if address == 0x1A
            && self.adaptive_ie.is_some()
            && self.check_data_access(address, "read")
            && self.check_data_access(address + 1, "read")
        {
            let value = self.adaptive_ie.unwrap();
            self.native_access(address, 16, 0, value);
            return value;
        }
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
        let before = self.native_accesses.as_ref().map_or(0, Vec::len);
        let continuity_before = self.continuity.as_ref().map_or(0, Vec::len);
        let all_before = self.all_native.as_ref().map_or(0, Vec::len);
        let value = u16::from_le_bytes([self.read_data_u8(address), self.read_data_u8(high)]);
        if let Some(rows) = self.native_accesses.as_mut() {
            rows.truncate(before);
        }
        if let Some(rows) = self.continuity.as_mut() {
            rows.truncate(continuity_before);
        }
        if let Some(rows) = self.all_native.as_mut() {
            rows.truncate(all_before);
        }
        self.native_access(address, 16, 0, value);
        value
    }
    pub fn write_data_u8(&mut self, address: u16, value: u8) {
        if !self.check_data_access(address, "write") {
            return;
        }
        if !(0x80..RAM_SIZE).contains(&(address as usize)) {
            if matches!(address, 0x40 | 0x46) && self.control_enabled(address) {
                let state = self.post_p2_control.as_mut().unwrap();
                if address == 0x40 {
                    // Only the reviewed TR0OUT bit may change. RUN/mode/clock/buffer
                    // changes would need separate primary evidence and admission.
                    if value & !4 != state[0] & !4 {
                        self.record_fault("data", address as u32, "unadmitted-control-side-effect");
                        return;
                    }
                    state[0] = value;
                } else {
                    state[1] = value & 15;
                } // nonexistent bits always read as 1
                self.control_accesses.push([
                    self.native_pc as u32,
                    address as u32,
                    8,
                    1,
                    value as u32,
                ]);
                self.observe_all(2, address, 8, 1, value as u16);
                if self.journal_writes {
                    self.data_writes.push([address as u32, 8, value as u32]);
                }
                return;
            }
            if address == 0x24 && self.p2_enabled() && self.p2_output_latch.is_some() {
                self.p2_output_latch = Some(value);
                self.p2_accesses
                    .push([self.native_pc as u32, 0x24, 8, 1, value as u32]);
                self.observe_all(1, address, 8, 1, value as u16);
                if self.journal_writes {
                    self.data_writes.push([0x24, 8, value as u32]);
                }
                return;
            }
            if address == 0x22 && self.p1_access && self.p1_output_latch.is_some() {
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
        self.native_access(address, 8, 1, value as u16);
        if self.journal_writes {
            self.data_writes.push([address as u32, 8, value as u32]);
        }
    }
    pub fn write_data_u16(&mut self, address: u16, value: u16) {
        if self.retained_selector && u32::from(address) <= 0x13C && u32::from(address) + 2 > 0x13C {
            self.record_fault("data", address as u32, "selector-word-overlap");
            return;
        }
        if address == 0x1A
            && self.adaptive_ie.is_some()
            && self.check_data_access(address, "write")
            && self.check_data_access(address + 1, "write")
        {
            self.adaptive_ie = Some(value);
            self.native_access(address, 16, 1, value);
            if self.journal_writes {
                self.data_writes.push([address as u32, 16, value as u32]);
            }
            return;
        }
        if address < 0x80 && self.post_p2_control.is_some() {
            self.record_fault("data", address as u32, "write-word-control");
            return;
        }
        if address < 0x80
            && (self.capture.is_some()
                || self.p1_output_latch.is_some()
                || self.p2_output_latch.is_some())
        {
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
        let access_before = self.native_accesses.as_ref().map_or(0, Vec::len);
        let continuity_before = self.continuity.as_ref().map_or(0, Vec::len);
        let all_before = self.all_native.as_ref().map_or(0, Vec::len);
        self.write_data_u8(address, bytes[0]);
        self.write_data_u8(high, bytes[1]);
        if self.fault.borrow().is_none() {
            if let Some(rows) = self.continuity.as_mut() {
                rows.truncate(continuity_before);
            }
            if let Some(rows) = self.all_native.as_mut() {
                rows.truncate(all_before);
            }
            if let Some(rows) = self.native_accesses.as_mut() {
                rows.truncate(access_before);
            }
            self.native_access(address, 16, 1, value);
        }
        // A successful architectural word store is one journal event, even
        // when the stored value was already present. Partial stores retain
        // their actual byte events instead of claiming a completed word write.
        if self.journal_writes && self.data_writes.len() == before + 2 {
            self.data_writes.truncate(before);
            self.data_writes.push([address as u32, 16, value as u32]);
        }
    }
    // Explicit word-only software IE storage; no interrupt delivery or time.
    pub(crate) fn set_adaptive_ie(&mut self, value: Option<u16>) {
        self.adaptive_ie = value;
    }
    pub(crate) fn adaptive_ie(&self) -> Option<u16> {
        self.adaptive_ie
    }
    pub(crate) fn initialize_retained_selector(&mut self, value: u8) -> Result<(), String> {
        if self.retained_selector
            || value > 3
            || self.native_accesses.is_some()
            || self.continuity.is_some()
        {
            return Err("M2ae selector is a once-only initial0..3 snapshot".into());
        }
        self.ram[0x13C] = value;
        self.retained_selector = true;
        Ok(())
    }
}
