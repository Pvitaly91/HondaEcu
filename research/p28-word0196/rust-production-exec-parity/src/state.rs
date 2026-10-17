//! Public diagnostic state access, explicitly outside the functional step.
use crate::{ProductionProbeRequest, Result, RAM_END, RAM_START};
use p28_research_synthetic_adapter::{
    entry::{PointingBank, SyntheticCpuEntrySnapshot},
    psw::STORAGE,
    AdapterError,
};
use p28_slice_runner::{bus::Bus, cpu::Cpu, exec};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CpuRecord {
    pub pc: u16,
    pub a: u16,
    pub ssp: u16,
    pub lrb: u16,
    pub zf: bool,
    pub cf: bool,
    pub hc: bool,
    pub dd: bool,
    pub sf: bool,
    pub psw_other: u16,
    pub cycles: u64,
    pub instructions: u64,
    pub halted: bool,
}

impl From<&Cpu> for CpuRecord {
    fn from(cpu: &Cpu) -> Self {
        Self {
            pc: cpu.pc,
            a: cpu.a,
            ssp: cpu.ssp,
            lrb: cpu.lrb,
            zf: cpu.zf,
            cf: cpu.cf,
            hc: cpu.hc,
            dd: cpu.dd,
            sf: cpu.sf,
            psw_other: cpu.psw_other,
            cycles: cpu.cycles,
            instructions: cpu.instructions,
            halted: cpu.halted,
        }
    }
}

pub fn seed_cpu(entry: &SyntheticCpuEntrySnapshot, pc: u16, internal_sf: bool) -> Cpu {
    // Every production field is explicitly owned. No Cpu::new defaults.
    Cpu {
        pc,
        a: entry.a,
        ssp: entry.ssp,
        lrb: entry.lrb,
        zf: entry.zf,
        cf: entry.cf,
        hc: entry.hc,
        dd: entry.dd,
        sf: internal_sf,
        psw_other: entry.psw & STORAGE,
        cycles: 0,
        instructions: 0,
        halted: entry.halted,
    }
}

pub fn seed_data(bus: &mut Bus, request: &ProductionProbeRequest) -> Result<()> {
    for (&address, &value) in &request.data {
        bus.write_data_u8(address, value);
    }
    for (bank, values) in request.entry.pointing_banks.iter().enumerate() {
        for (slot, value) in [values.x1, values.x2, values.dp, values.usp]
            .into_iter()
            .enumerate()
        {
            bus.write_data_u16(0x80 + bank as u16 * 8 + slot as u16 * 2, value);
        }
    }
    if let Some(fault) = bus.take_fault() {
        return Err(AdapterError::new("PublicDataSeedFault", fault.to_string()));
    }
    Ok(())
}

pub fn ram_snapshot(bus: &mut Bus) -> Result<Vec<u8>> {
    let result: Vec<u8> = (RAM_START..RAM_END)
        .map(|address| bus.read_data_u8(address))
        .collect();
    if let Some(fault) = bus.take_fault() {
        return Err(AdapterError::new(
            "DiagnosticRamSnapshotFault",
            fault.to_string(),
        ));
    }
    Ok(result)
}

pub fn snapshot(
    template: &SyntheticCpuEntrySnapshot,
    cpu: &Cpu,
    bus: &mut Bus,
    ram: &[u8],
) -> Result<SyntheticCpuEntrySnapshot> {
    if ram.len() != usize::from(RAM_END - RAM_START) {
        return Err(AdapterError::new(
            "WrongDiagnosticRamLength",
            "closed 0080..0FFF",
        ));
    }
    let mut result = template.clone();
    result.pc = cpu.pc;
    result.a = cpu.a;
    result.al = cpu.al();
    result.ah = cpu.ah();
    result.psw = cpu.psw_u16();
    result.cf = cpu.cf;
    result.zf = cpu.zf;
    result.hc = cpu.hc;
    result.dd = cpu.dd;
    result.other_psw = cpu.psw_u16() & 0x0fff;
    result.scb = cpu.scb();
    result.lrb = cpu.lrb;
    result.ssp = cpu.ssp;
    result.halted = cpu.halted;
    let word = |address: u16| {
        let offset = usize::from(address - RAM_START);
        u16::from_le_bytes([ram[offset], ram[offset + 1]])
    };
    for bank in 0..8 {
        let base = 0x80 + bank as u16 * 8;
        result.pointing_banks[bank] = PointingBank {
            x1: word(base),
            x2: word(base + 2),
            dp: word(base + 4),
            usp: word(base + 6),
        };
    }
    // Real coherent public alias reads; these are diagnostic, not invented
    // functional DATA events. This also supports the isolated LRB0 fault audit.
    for n in 0..8 {
        result.local_r[n] = exec::read_data_u8(cpu, bus, cpu.bank_base() + n as u16);
    }
    for n in 0..4 {
        result.local_er[n] = u16::from_le_bytes([result.local_r[2 * n], result.local_r[2 * n + 1]]);
    }
    if let Some(fault) = bus.take_fault() {
        return Err(AdapterError::new(
            "DiagnosticAliasSnapshotFault",
            fault.to_string(),
        ));
    }
    Ok(result)
}
