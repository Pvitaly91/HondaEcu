//! M2bx: one retained production CPU/Bus through a second native P2 store.
//! Closed Below-only continuation; no RT, state import or opcode implementation.
use super::{
    original_rom::OriginalNode, p2_handoff::*, post_p2_control::*, Access, AuditError,
    InstructionIdentity, OriginalRomSourceBinding, OriginalRomStep, Permissions, ProgramSegment,
    Result, Session, WriteAccess,
};
use crate::{cpu::Cpu, decoder::Fields};
use serde::Serialize;
use std::collections::BTreeMap;

pub(super) struct BelowSecondP2Budget(());
impl BelowSecondP2Budget {
    pub(super) fn retirements(&self) -> u8 {
        39
    }
}

pub struct ClosedBelowSecondP2Program {
    segment: ProgramSegment,
    prefix: ClosedPostP2ControlProgram,
}
impl ClosedBelowSecondP2Program {
    pub fn admit_host_verified_segment(
        base: u32,
        bytes: Vec<u8>,
        digest: &str,
        binding: OriginalRomSourceBinding,
    ) -> Result<Self> {
        if base != 0x54f5 || bytes.len() != 403 {
            return Err(AuditError::new(
                "BelowSecondSegmentRejected",
                Some(i64::from(base)),
                "unchanged403-byte[54F5,5688) source only; RT byte excluded",
            ));
        }
        let segment = ProgramSegment::new(base, bytes, digest)?;
        let bytes = segment.bytes[..221].to_vec();
        let prefix = ClosedPostP2ControlProgram::admit_host_verified_segment(
            base,
            bytes.clone(),
            &crate::audit_sha256::digest(&bytes),
            binding,
        )?;
        Ok(Self { segment, prefix })
    }
    pub fn explicit_invented_public_fixture() -> Self {
        let prefix = ClosedPostP2ControlProgram::explicit_invented_public_fixture();
        let mut bytes = prefix.segment.bytes.to_vec();
        bytes.resize(403, 0xa5);
        for node in tail_nodes(false) {
            let f = node.identity.fields;
            // Newly invented code cells from reviewed forms/operands. No
            // private image or native instruction window is read or copied.
            let encoded = match node.identity.index {
                1851 => vec![0x33],
                2301 | 2287 => vec![0xd4, f.n8],
                1779 => vec![0xc5, f.n8, 0x0a],
                724 => vec![0x67, f.n16 as u8, (f.n16 >> 8) as u8],
                2180 => vec![0xcb, f.rel8 as u8],
                684 => vec![0x03, f.addr16 as u8, (f.addr16 >> 8) as u8],
                732 => vec![0xe4, f.n8],
                718 => vec![0xce, f.rel8 as u8],
                747 => vec![0xf4, f.n8],
                1630 => vec![0xe7, f.n8],
                322 => vec![0xd6, f.n8],
                1647 => vec![0xc5, f.n8, 0xe1],
                1776 => vec![0xc4, f.n8, 0x0f],
                _ => unreachable!("closed invented downstream forms"),
            };
            let start = usize::from(node.pc - 0x6400);
            bytes[start..start + encoded.len()].copy_from_slice(&encoded);
        }
        let digest = crate::audit_sha256::digest(&bytes);
        Self {
            segment: ProgramSegment::new(0x6400, bytes, &digest).expect("invented403-byte fixture"),
            prefix,
        }
    }
    pub fn entry_pc(&self) -> u16 {
        self.segment.base as u16
    }
    pub fn program_sha256(&self) -> &str {
        self.segment.sha256()
    }
    pub fn classification(&self) -> &'static str {
        if self.prefix.p2.native {
            "OriginalRomBytes_TechnicalBelowSecondP2Execution"
        } else {
            "ExplicitInventedPublicBelowSecondP2Fixture"
        }
    }
    fn pc(&self, native: u16) -> u16 {
        self.entry_pc() + (native - 0x54f5)
    }
    fn parts(&self) -> (Vec<OriginalNode>, Vec<u16>, Vec<u16>) {
        let (mut nodes, mut inventory, mut pcs) = self.prefix.parts(PostP2ControlPath::A);
        let tail = tail_nodes(self.prefix.p2.native);
        pcs.extend(tail.iter().map(|node| node.pc));
        nodes.extend(tail);
        inventory.extend(0x110..=0x116);
        inventory.sort_unstable();
        assert_eq!((nodes.len(), inventory.len(), pcs.len()), (49, 23, 39));
        (nodes, inventory, pcs)
    }
    fn segment_copy(&self) -> ProgramSegment {
        ProgramSegment {
            base: self.segment.base,
            end: self.segment.end,
            bytes: self.segment.bytes.clone(),
            digest: self.segment.digest.clone(),
        }
    }
}

fn tail_nodes(native: bool) -> Vec<OriginalNode> {
    let pc = |n| if native { n } else { 0x6400 + (n - 0x54f5) };
    let byte = |n8| Fields {
        n8,
        ..Fields::default()
    };
    let relative = |rel8| Fields {
        rel8,
        ..Fields::default()
    };
    let read = |address, width| Access { address, width };
    let write = |address, width, rmw_required| WriteAccess {
        access: Access { address, width },
        rmw_required,
    };
    let mut result = vec![];
    let mut add = |site, index, len, name: &str, fields, dd, after, next, reads, writes| {
        result.push(OriginalNode {
            pc: pc(site),
            identity: InstructionIdentity {
                index,
                len,
                mnemonic: name.into(),
                dd_before: dd,
                dd_after: after,
                fields,
            },
            reachable_dd: vec![dd],
            successors: vec![pc(next)],
            reads,
            writes,
        });
    };
    add(
        0x55d2,
        1851,
        1,
        "ROLB A",
        Fields::default(),
        false,
        None,
        0x55d3,
        vec![],
        vec![],
    );
    add(
        0x55d3,
        2301,
        2,
        "STB A, off N8",
        byte(0x16),
        false,
        None,
        0x55d5,
        vec![],
        vec![write(0x116, 8, false)],
    );
    add(
        0x55d5,
        1779,
        3,
        "RB N8.2",
        byte(0x40),
        false,
        None,
        0x55d8,
        vec![read(0x40, 8)],
        vec![write(0x40, 8, true)],
    );
    add(
        0x55d8,
        724,
        3,
        "L A, #N16",
        Fields {
            n16: 1,
            ..Fields::default()
        },
        false,
        Some(true),
        0x55db,
        vec![],
        vec![],
    );
    add(
        0x55db,
        2180,
        2,
        "SJ rel8",
        relative(0x4f),
        true,
        None,
        0x562c,
        vec![],
        vec![],
    );
    add(
        0x562c,
        2287,
        2,
        "ST A, off N8",
        byte(0x10),
        true,
        None,
        0x562e,
        vec![],
        vec![write(0x110, 16, false)],
    );
    add(
        0x562e,
        724,
        3,
        "L A, #N16",
        Fields {
            n16: 1,
            ..Fields::default()
        },
        true,
        Some(true),
        0x5631,
        vec![],
        vec![],
    );
    add(
        0x5631,
        2287,
        2,
        "ST A, off N8",
        byte(0x12),
        true,
        None,
        0x5633,
        vec![],
        vec![write(0x112, 16, false)],
    );
    add(
        0x5633,
        684,
        3,
        "J addr16",
        Fields {
            addr16: pc(0x565d),
            ..Fields::default()
        },
        true,
        None,
        0x565d,
        vec![],
        vec![],
    );
    add(
        0x565d,
        2287,
        2,
        "ST A, off N8",
        byte(0x14),
        true,
        None,
        0x565f,
        vec![],
        vec![write(0x114, 16, false)],
    );
    add(
        0x565f,
        732,
        2,
        "L A, off N8",
        byte(0x10),
        true,
        Some(true),
        0x5661,
        vec![read(0x110, 16)],
        vec![],
    );
    add(
        0x5661,
        718,
        2,
        "JNE rel8",
        relative(14),
        true,
        None,
        0x5671,
        vec![],
        vec![],
    );
    add(
        0x5671,
        747,
        2,
        "LB A, off N8",
        byte(0x16),
        true,
        Some(false),
        0x5673,
        vec![read(0x116, 8)],
        vec![],
    );
    add(
        0x5673,
        2180,
        2,
        "SJ rel8",
        relative(9),
        false,
        None,
        0x567e,
        vec![],
        vec![],
    );
    let source = if native { 0x18f } else { 0x193 };
    add(
        0x567e,
        1630,
        2,
        "ORB A, off N8",
        byte(source as u8),
        false,
        None,
        0x5680,
        vec![read(source, 8)],
        vec![],
    );
    add(
        0x5680,
        322,
        2,
        "ANDB A, #N8",
        byte(15),
        false,
        None,
        0x5682,
        vec![],
        vec![],
    );
    add(
        0x5682,
        1647,
        3,
        "ORB N8, A",
        byte(0x24),
        false,
        None,
        0x5685,
        vec![read(0x24, 8)],
        vec![write(0x24, 8, true)],
    );
    let flag = if native { 0x12a } else { 0x12d };
    add(
        0x5685,
        1776,
        3,
        "RB off N8.7",
        byte(flag as u8),
        false,
        None,
        0x5688,
        vec![read(flag, 8)],
        vec![write(flag, 8, true)],
    );
    result
}

pub struct BelowSecondP2Seeds(P2HandoffSeeds);
impl BelowSecondP2Seeds {
    pub fn new(
        program: &ClosedBelowSecondP2Program,
        data: BTreeMap<u16, u8>,
        pointing: [[u16; 4]; 8],
        r: [u8; 8],
        er: [u16; 4],
    ) -> Result<Self> {
        let (_, inventory, _) = program.parts();
        if data.keys().copied().collect::<Vec<_>>() != inventory
            || (0x110..=0x116).any(|a| data[&a] != 0xa5)
        {
            return Err(AuditError::new(
                "BelowSecondCanarySeedsRejected",
                None,
                "exact23 DATA bytes, seven explicit A5 canaries before54F5 only",
            ));
        }
        let native = program.prefix.p2.native;
        let word = if native { 0x196 } else { 0x19a };
        let gate = if native { 0x128 } else { 0x130 };
        let output = if native { 0x117 } else { 0x11b };
        if u16::from_le_bytes([data[&word], data[&(word + 1)]]) >= 0xc0
            || data[&gate] & 4 == 0
            || data[&output] == 15
        {
            return Err(AuditError::new(
                "BelowSecondCaseDomainRejected",
                None,
                "actual predecessor/JLT Below route preconditions only",
            ));
        }
        let prefix_data = data
            .iter()
            .filter(|(a, _)| !(0x110u16..=0x116u16).contains(*a))
            .map(|(a, v)| (*a, *v))
            .collect();
        let mut prefix = P2HandoffSeeds::new(&program.prefix.p2, prefix_data, pointing, r, er)?;
        prefix.data = data;
        Ok(Self(prefix))
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct BelowSecondP2Report {
    #[serde(flatten)]
    pub prefix: PostP2ControlReport,
    pub below_instruction_retirements: u64,
    pub p2_generations: Vec<P2Generation>,
    pub control_generations: Vec<P2Generation>,
    pub second_p2_generation: Option<P2Generation>,
    pub second_control_generation: Option<P2Generation>,
}
pub struct BelowSecondP2Session {
    pub(super) inner: PostP2ControlSession,
}
impl BelowSecondP2Session {
    pub fn new(
        program: &ClosedBelowSecondP2Program,
        cpu: Cpu,
        full_psw: u16,
        seeds: BelowSecondP2Seeds,
        path: PostP2ControlPath,
        requested_budget: u8,
        p2_snapshot: P2Snapshot,
        control: ControlSnapshot,
    ) -> Result<Self> {
        control.validate()?;
        p2_snapshot.validate()?;
        let (nodes, inventory, pcs) = program.parts();
        if path != PostP2ControlPath::A
            || requested_budget != 39
            || cpu.pc != program.entry_pc()
            || cpu.lrb != 0x21
            || cpu.instructions != 0
            || cpu.cycles != 0
        {
            return Err(AuditError::new(
                "BelowSecondEntryRejected",
                Some(i64::from(cpu.pc)),
                "fresh54F5-equivalent entry and exact39-step Below only",
            ));
        }
        let active: Vec<_> = nodes.iter().filter(|n| pcs.contains(&n.pc)).collect();
        let mut reads: Vec<_> = active
            .iter()
            .flat_map(|n| n.reads.clone())
            .filter(|r| r.address >= 0x80)
            .collect();
        reads.sort();
        reads.dedup();
        let mut writes: Vec<_> = active
            .iter()
            .flat_map(|n| n.writes.clone())
            .filter(|r| r.access.address >= 0x80)
            .collect();
        writes.sort_by_key(|w| w.access);
        writes.dedup_by_key(|w| w.access);
        let inner = Session::new_below_second_p2_admitted(
            program.segment_copy(),
            cpu,
            full_psw,
            Permissions::new(reads, writes)?,
            BelowSecondP2Budget(()),
        )?;
        let values = [control.tcon0, control.trnsit_implemented_flags];
        let inner = P2HandoffSession::from_admitted(
            &program.prefix.p2,
            inner,
            seeds.0,
            P2HandoffPath::A,
            p2_snapshot,
            nodes,
            inventory,
            pcs,
            program.pc(0x5688),
            Some(values),
        )?;
        Ok(Self {
            inner: PostP2ControlSession {
                inner,
                initial: control,
                last_control: values,
                control_steps: vec![],
                native_control: vec![],
                classification: program.classification().into(),
            },
        })
    }
    pub fn step(&mut self) -> Result<OriginalRomStep> {
        self.inner.step()
    }
    pub fn report(&mut self) -> Result<BelowSecondP2Report> {
        let mut prefix = self.inner.report()?;
        let services = self.inner.inner.inner.bus.p2_accesses();
        let mut journal = vec![];
        for step in &prefix.p2.steps {
            for event in &prefix.p2.audit.data_events[step.logical_span[0]..step.logical_span[1]] {
                if event.address != 0x24 || !event.serviced {
                    continue;
                }
                let row = services.get(journal.len()).ok_or_else(|| {
                    AuditError::new(
                        "BelowSecondP2ServiceMissing",
                        None,
                        "actual full peripheral journal",
                    )
                })?;
                let raw: Vec<_> = prefix
                    .p2
                    .audit
                    .raw_data_events
                    .iter()
                    .filter(|r| r.logical_ordinal == event.ordinal)
                    .collect();
                if row[0] != u32::from(step.outcome.pc_before)
                    || row[1] != 0x24
                    || row[2] != 8
                    || row[3] != u32::from(event.operation == "Write")
                    || event.value != Some(row[4] as u16)
                    || raw.len() != 1
                    || !raw[0].serviced
                    || raw[0].value != Some(row[4] as u8)
                {
                    return Err(AuditError::new(
                        "BelowSecondP2ServiceMismatch",
                        None,
                        "native/logical/raw agreement",
                    ));
                }
                journal.push(P2PeripheralEvent {
                    ordinal: journal.len() as u64,
                    pc: step.outcome.pc_before,
                    address: 0x24,
                    width: 8,
                    operation: event.operation.clone(),
                    value: row[4] as u8,
                    logical_ordinal: event.ordinal,
                    raw_ordinal: raw[0].ordinal,
                    write_ordinal: event.write_ordinal,
                    native_write_ordinal: event
                        .write_ordinal
                        .map(|w| {
                            w.checked_sub(55).ok_or_else(|| {
                                AuditError::new(
                                    "BelowSecondNativeWriteOrdinalUnderflow",
                                    None,
                                    "seed writes are not native",
                                )
                            })
                        })
                        .transpose()?,
                    same_value: event.same_value,
                    space: "PeripheralP2".into(),
                });
            }
        }
        if journal.len() != services.len() || journal.len() > 4 {
            return Err(AuditError::new(
                "BelowSecondP2JournalCardinalityRejected",
                None,
                "two ordered actual RMWs only",
            ));
        }
        let p2_generations = generations(&prefix, &journal)?;
        let control_generations = generations(&prefix, &prefix.peripheral_control_journal)?;
        prefix.p2.peripheral_p2_journal = journal;
        prefix.p2.p2_instruction_retirements = p2_generations.len() as u64;
        let below_instruction_retirements = prefix.p2.steps.len().saturating_sub(21) as u64;
        if prefix.p2.completed
            && (prefix.p2.steps.len() != 39
                || p2_generations.len() != 2
                || control_generations.len() != 2
                || prefix.p2.peripheral_p2_journal.len() != 4
                || prefix.peripheral_control_journal.len() != 6)
        {
            return Err(AuditError::new(
                "BelowSecondCompletedStateRejected",
                None,
                "exact39 retirements and two generations per register",
            ));
        }
        Ok(BelowSecondP2Report {
            second_p2_generation: p2_generations.get(1).cloned(),
            second_control_generation: control_generations.get(1).cloned(),
            prefix,
            below_instruction_retirements,
            p2_generations,
            control_generations,
        })
    }
}
fn generations(
    report: &PostP2ControlReport,
    journal: &[P2PeripheralEvent],
) -> Result<Vec<P2Generation>> {
    let mut result = vec![];
    for event in journal.iter().filter(|e| e.operation == "Write") {
        let step = report
            .p2
            .steps
            .iter()
            .find(|s| s.outcome.pc_before == event.pc)
            .ok_or_else(|| {
                AuditError::new(
                    "BelowSecondGenerationRetirementMissing",
                    None,
                    "actual retired writer",
                )
            })?;
        let raw = &report.p2.audit.raw_data_events[event.raw_ordinal as usize];
        result.push(P2Generation {
            machine_id: 1,
            writer_pc: event.pc,
            retired_instruction: step.index,
            generation_ordinal: result.len() as u64 + 1,
            native_write_ordinal: event.native_write_ordinal.expect("write"),
            logical_write_ordinal: event.write_ordinal.expect("write"),
            raw_write_ordinal: raw.write_ordinal.expect("write"),
            value: event.value,
        });
    }
    Ok(result)
}

#[cfg(test)]
#[path = "audit_below_second_p2_tests.rs"]
mod tests;
