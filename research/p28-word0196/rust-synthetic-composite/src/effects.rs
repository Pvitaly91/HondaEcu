//! Source-bound M2bm effect implementation. Semantic bodies below are exact.
//! Only imports and execute_one visibility differ from the frozen source.
//! Source: rust-synthetic-adapter/src/executor.rs
//! SHA256: a1bb8e708177598259087d53774f72fa656ca36e67ac7f16f532ca1baa2d10c3
use crate::{AdapterError, Result};
use p28_research_synthetic_adapter::{
    admission::FormId,
    data::{IndependentDataAccessPolicy, WriteKind},
};
use p28_slice_runner::{cpu::Cpu, decoder::Decoded};

pub(crate) fn execute_one(
    cpu: &mut Cpu,
    data: &mut IndependentDataAccessPolicy,
    form: FormId,
    d: &Decoded,
) -> Result<Option<bool>> {
    use FormId::*;
    let pc = cpu.pc;
    let mut next = pc
        .checked_add(u16::try_from(d.len).map_err(|_| AdapterError::new("PcOverflow", "length"))?)
        .ok_or_else(|| AdapterError::new("PcOverflow", "next instruction"))?;
    let mut branch = None;
    let f = d.fields;
    match form {
        LbAPage | LbAR0 | LbAImm8 => {
            let value = match form {
                LbAPage => data.read(pc, cpu.off_page(f.n8), 8)? as u8,
                LbAR0 => data.read(pc, cpu.bank_base(), 8)? as u8,
                _ => f.n8,
            };
            cpu.set_al(value);
            cpu.zf = value == 0;
        }
        SllbA => {
            let value = cpu.al();
            cpu.set_al(value.wrapping_shl(1));
            cpu.cf = value & 0x80 != 0;
        }
        RolbPage => {
            let address = cpu.off_page(f.n8);
            let value = data.read(pc, address, 8)? as u8;
            let result = value.wrapping_shl(1) | u8::from(cpu.cf);
            data.write(pc, address, 8, result as u16, WriteKind::RMW)?;
            cpu.cf = value & 0x80 != 0;
        }
        AndbAPage => {
            let value = data.read(pc, cpu.off_page(f.n8), 8)? as u8;
            let result = cpu.al() & value;
            cpu.set_al(result);
            cpu.zf = result == 0;
        }
        CmpPageImm16 => {
            let address = cpu.off_page(f.n8);
            if address & 1 != 0 {
                return Err(AdapterError::new(
                    "WrongWidthOrAlignment",
                    "reviewed even LE16 compare",
                ));
            }
            let value = data.read(pc, address, 16)?;
            cpu.cf = value < f.n16;
            cpu.zf = value == f.n16;
        }
        JltRel8 => {
            let taken = cpu.cf;
            branch = Some(taken);
            if taken {
                next = relative(next, f.rel8)?;
            }
        }
        MovbR1Page => {
            let value = data.read(pc, cpu.off_page(f.n8), 8)?;
            data.write(
                pc,
                cpu.bank_base() + 1,
                8,
                value,
                WriteKind::LocalRegisterStore,
            )?;
        }
        AndbPageA => {
            let address = cpu.off_page(f.n8);
            let value = data.read(pc, address, 8)? as u8;
            let result = value & cpu.al();
            data.write(pc, address, 8, result as u16, WriteKind::RMW)?;
            cpu.zf = result == 0;
        }
        JbsPageBit7 | JbsPageBit5 => {
            let value = data.read(pc, cpu.off_page(f.n8), 8)? as u8;
            let bit = if form == JbsPageBit7 { 7 } else { 5 };
            let taken = value & (1 << bit) != 0;
            branch = Some(taken);
            if taken {
                next = relative(next, f.rel8)?;
            }
        }
        OrbPageImm8 => {
            let address = cpu.off_page(f.n8_alt);
            let value = data.read(pc, address, 8)? as u8;
            let result = value | f.n8;
            data.write(pc, address, 8, result as u16, WriteKind::RMW)?;
            cpu.zf = result == 0;
        }
        OrbAImm8 => {
            let result = cpu.al() | f.n8;
            cpu.set_al(result);
            cpu.zf = result == 0;
        }
        StbAPage => {
            data.write(pc, cpu.off_page(f.n8), 8, cpu.al() as u16, WriteKind::Store)?;
        }
        JAddress => {
            if !matches!(f.addr16, 0x5596 | 0x55c5) {
                return Err(AdapterError::new(
                    "WrongExternalTarget",
                    "reviewed invented anchors only",
                ));
            }
            next = f.addr16;
        }
    }
    cpu.pc = next;
    if let Some(dd) = d.dd_after {
        cpu.dd = dd;
    }
    cpu.instructions += 1;
    cpu.cycles += u64::from(d.cycles) + if branch == Some(true) { 4 } else { 0 };
    Ok(branch)
}
fn relative(next: u16, rel: i8) -> Result<u16> {
    u16::try_from(i32::from(next) + i32::from(rel))
        .map_err(|_| AdapterError::new("PcOverflow", "signed relative branch"))
}
