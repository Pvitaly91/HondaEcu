use crate::{
    data::IndependentDataAccessPolicy, psw::CanonicalPswBridge, sf::OpaqueSfBoundary, AdapterError,
    Result, INVENTED_PROVENANCE,
};
use p28_slice_runner::cpu::Cpu;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PointingBank {
    pub x1: u16,
    pub x2: u16,
    pub dp: u16,
    pub usp: u16,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SyntheticCpuEntrySnapshot {
    pub pc: u16,
    pub a: u16,
    pub al: u8,
    pub ah: u8,
    pub psw: u16,
    pub cf: bool,
    pub zf: bool,
    pub hc: bool,
    pub dd: bool,
    pub other_psw: u16,
    pub lrb: u16,
    pub scb: u16,
    pub ssp: u16,
    pub pointing_banks: [PointingBank; 8],
    pub local_r: [u8; 8],
    pub local_er: [u16; 4],
    pub halted: bool,
    pub provenance: String,
    pub sf: OpaqueSfBoundary,
}
impl SyntheticCpuEntrySnapshot {
    pub fn validate(&self, data: &BTreeMap<u16, u8>) -> Result<()> {
        self.sf.validate()?;
        if self.pc != 0x1000
            || self.lrb != 0x21
            || self.halted
            || self.provenance != INVENTED_PROVENANCE
        {
            return Err(AdapterError::new(
                "InvalidEntryScope",
                "explicit PC1000/LRB0021/nonhalted/invented snapshot required",
            ));
        }
        if self.a != u16::from_le_bytes([self.al, self.ah])
            || self.other_psw != self.psw & 0xfff
            || self.scb != self.psw & 7
            || self.cf != (self.psw & 0x8000 != 0)
            || self.zf != (self.psw & 0x4000 != 0)
            || self.hc != (self.psw & 0x2000 != 0)
            || self.dd != (self.psw & 0x1000 != 0)
        {
            return Err(AdapterError::new(
                "ConflictingCpuAliases",
                "A/PSW/named flags/OtherPSW/SCB",
            ));
        }
        if !CanonicalPswBridge::is_representable(self.psw) {
            return Err(AdapterError::new(
                "NotRepresentableByCurrentCanonicalRustCpu",
                format!("preserve expected {:04X}", self.psw),
            ));
        }
        for n in 0..8 {
            if data.get(&(0x108 + n as u16)) != Some(&self.local_r[n]) {
                return Err(AdapterError::new(
                    "ConflictingLocalAliases",
                    "rN and DATA0108..010F",
                ));
            }
        }
        for n in 0..4 {
            if self.local_er[n]
                != u16::from_le_bytes([self.local_r[2 * n], self.local_r[2 * n + 1]])
            {
                return Err(AdapterError::new(
                    "ConflictingLocalAliases",
                    "erN and r pair",
                ));
            }
        }
        Ok(())
    }
    pub(crate) fn seed_cpu(&self, internal_sf: bool) -> Result<Cpu> {
        // Every Cpu field is explicit. The internal test boolean is not an
        // architectural SF value and never enters the opaque oracle descriptor.
        let mut cpu = Cpu {
            pc: self.pc,
            a: self.a,
            ssp: self.ssp,
            lrb: self.lrb,
            zf: self.zf,
            cf: self.cf,
            hc: self.hc,
            dd: self.dd,
            sf: internal_sf,
            psw_other: self.other_psw,
            cycles: 0,
            instructions: 0,
            halted: self.halted,
        };
        CanonicalPswBridge::set_checked(&mut cpu, self.psw)?;
        Ok(cpu)
    }
    pub fn seed_banks(&self, data: &mut IndependentDataAccessPolicy) -> Result<()> {
        for (bank, values) in self.pointing_banks.iter().enumerate() {
            for (slot, value) in [values.x1, values.x2, values.dp, values.usp]
                .into_iter()
                .enumerate()
            {
                data.seed_word(pointing_address(bank, slot)?, value)?;
            }
        }
        Ok(())
    }
    pub fn snapshot(&self, cpu: &Cpu, data: &mut IndependentDataAccessPolicy) -> Result<Self> {
        let mut result = self.clone();
        result.pc = cpu.pc;
        result.a = cpu.a;
        result.al = cpu.al();
        result.ah = cpu.ah();
        result.psw = cpu.psw_u16();
        result.cf = cpu.cf;
        result.zf = cpu.zf;
        result.hc = cpu.hc;
        result.dd = cpu.dd;
        result.other_psw = cpu.psw_u16() & 0xfff;
        result.lrb = cpu.lrb;
        result.scb = cpu.scb();
        result.ssp = cpu.ssp;
        result.halted = cpu.halted;
        for bank in 0..8 {
            result.pointing_banks[bank] = PointingBank {
                x1: data.diagnostic_word(pointing_address(bank, 0)?)?,
                x2: data.diagnostic_word(pointing_address(bank, 1)?)?,
                dp: data.diagnostic_word(pointing_address(bank, 2)?)?,
                usp: data.diagnostic_word(pointing_address(bank, 3)?)?,
            };
        }
        for n in 0..8 {
            result.local_r[n] = data.diagnostic_byte(cpu.bank_base() + n as u16)?;
        }
        for n in 0..4 {
            result.local_er[n] =
                u16::from_le_bytes([result.local_r[2 * n], result.local_r[2 * n + 1]]);
        }
        Ok(result)
    }
}
pub fn pointing_address(bank: usize, slot: usize) -> Result<u16> {
    if bank >= 8 || slot >= 4 {
        return Err(AdapterError::new(
            "InvalidPointingRegister",
            "eight banks, four words each",
        ));
    }
    Ok(0x80 + bank as u16 * 8 + slot as u16 * 2)
}
