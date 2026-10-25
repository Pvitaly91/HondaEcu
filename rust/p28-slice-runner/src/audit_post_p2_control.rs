//! M2bw closed continuation of M2bv on its retained production CPU/Bus.
//! No arithmetic interpreter, timer evolution, PC setter or post-start seed API.
use super::{
    original_rom::OriginalNode, p2_handoff::*, Access, AuditError, InstructionIdentity,
    OriginalRomSourceBinding, OriginalRomStep, Permissions, ProgramSegment, Result, Session,
    WriteAccess,
};
use crate::{cpu::Cpu, decoder::Fields};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PostP2ControlPath {
    A,
    B,
    C,
    D,
}
impl PostP2ControlPath {
    pub fn budget(self) -> u8 {
        match self {
            Self::A => 21,
            Self::B => 20,
            Self::C => 21,
            Self::D => 23,
        }
    }
    fn prefix(self) -> P2HandoffPath {
        match self {
            Self::A => P2HandoffPath::A,
            Self::B => P2HandoffPath::B,
            Self::C => P2HandoffPath::C,
            Self::D => P2HandoffPath::D,
        }
    }
}
pub(super) struct PostP2Budget(u8);
impl PostP2Budget {
    pub(super) fn retirements(&self) -> u8 {
        self.0
    }
}
fn budget(p: PostP2ControlPath) -> u8 {
    p.budget()
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ControlSnapshot {
    pub tcon0: u8,
    pub trnsit_implemented_flags: u8,
    pub provenance: String,
}
impl ControlSnapshot {
    fn validate(&self) -> Result<()> {
        if !matches!(self.tcon0, 0x83 | 0x87 | 0x8b | 0x8f)
            || self.trnsit_implemented_flags > 15
            || self.provenance != "TechnicalArchitecturalControlSnapshot_NoNativeWriterGeneration"
        {
            return Err(AuditError::new(
                "PostP2ControlSnapshotRejected",
                None,
                "stopped83/87/8B/8F TCON0 and implemented TRNSIT0..15 technical snapshot only",
            ));
        }
        Ok(())
    }
}
pub struct ClosedPostP2ControlProgram {
    segment: ProgramSegment,
    p2: ClosedP2HandoffProgram,
}
impl ClosedPostP2ControlProgram {
    pub fn admit_host_verified_segment(
        base: u32,
        bytes: Vec<u8>,
        digest: &str,
        binding: OriginalRomSourceBinding,
    ) -> Result<Self> {
        if base != 0x54f5 || bytes.len() != 221 {
            return Err(AuditError::new(
                "PostP2SegmentRejected",
                Some(i64::from(base)),
                "unchanged221-byte[54F5,55D2) segment only",
            ));
        }
        let segment = ProgramSegment::new(base, bytes, digest)?;
        let prefix = segment.bytes[..211].to_vec();
        let prefix_digest = crate::audit_sha256::digest(&prefix);
        let p2 = ClosedP2HandoffProgram::admit_host_verified_segment(
            base,
            prefix,
            &prefix_digest,
            binding,
        )?;
        Ok(Self { segment, p2 })
    }
    pub fn explicit_invented_public_fixture() -> Self {
        let p2 = ClosedP2HandoffProgram::explicit_invented_public_fixture();
        let mut bytes = p2.segment.bytes.to_vec();
        bytes.extend([0xa5; 10]);
        // Independently invented fixture, same documented instruction forms;
        // invented DATA0192 is the public predecessor fixture's byte source.
        for (offset, code) in [
            (0x5599 - 0x54f5, vec![0xc5, 0x46, 0xd0, 0xfb]),
            (0x55c8 - 0x54f5, vec![0xc5, 0x40, 0x1a]),
            (0x55cb - 0x54f5, vec![0xf4, 0x92]),
            (0x55cd - 0x54f5, vec![0xf6, 0xff]),
            (0x55cf - 0x54f5, vec![0xc5, 0x06, 0x2f]),
        ] {
            bytes[offset..offset + code.len()].copy_from_slice(&code);
        }
        let digest = crate::audit_sha256::digest(&bytes);
        Self {
            segment: ProgramSegment::new(0x6400, bytes, &digest)
                .expect("fixed invented control fixture"),
            p2,
        }
    }
    pub fn entry_pc(&self) -> u16 {
        self.segment.base as u16
    }
    pub fn program_sha256(&self) -> &str {
        self.segment.sha256()
    }
    pub fn classification(&self) -> &'static str {
        if self.p2.native {
            "OriginalRomBytes_TechnicalPostP2ControlExecution"
        } else {
            "ExplicitInventedPublicPostP2ControlFixture"
        }
    }
    fn pc(&self, native: u16) -> u16 {
        self.p2.pc(native)
    }
    fn terminal(&self, path: PostP2ControlPath) -> u16 {
        self.pc(if path == PostP2ControlPath::A {
            0x55d2
        } else {
            0x559d
        })
    }
    fn parts(&self, path: PostP2ControlPath) -> (Vec<OriginalNode>, Vec<u16>, Vec<u16>) {
        let (mut nodes, inventory, mut pcs) = self.p2.parts(path.prefix());
        let lb = if self.p2.native { 0x8e } else { 0x92 };
        for (pc, index, len, name, fields, after, reads, writes) in [
            (
                0x5599,
                382,
                4,
                "ANDB N'8, #N8",
                Fields {
                    n8: 0xfb,
                    n8_alt: 0x46,
                    ..Fields::default()
                },
                None,
                vec![Access {
                    address: 0x46,
                    width: 8,
                }],
                vec![WriteAccess {
                    access: Access {
                        address: 0x46,
                        width: 8,
                    },
                    rmw_required: true,
                }],
            ),
            (
                0x55c8,
                1994,
                3,
                "SB N8.2",
                Fields {
                    n8: 0x40,
                    ..Fields::default()
                },
                None,
                vec![Access {
                    address: 0x40,
                    width: 8,
                }],
                vec![WriteAccess {
                    access: Access {
                        address: 0x40,
                        width: 8,
                    },
                    rmw_required: true,
                }],
            ),
            (
                0x55cb,
                747,
                2,
                "LB A, off N8",
                Fields {
                    n8: lb,
                    ..Fields::default()
                },
                Some(false),
                vec![Access {
                    address: 0x100 + u16::from(lb),
                    width: 8,
                }],
                vec![],
            ),
            (
                0x55cd,
                2557,
                2,
                "XORB A, #N8",
                Fields {
                    n8: 0xff,
                    ..Fields::default()
                },
                None,
                vec![],
                vec![],
            ),
            (
                0x55cf,
                894,
                3,
                "MB C, N8.7",
                Fields {
                    n8: 6,
                    ..Fields::default()
                },
                None,
                vec![Access {
                    address: 6,
                    width: 8,
                }],
                vec![],
            ),
        ] {
            nodes.push(OriginalNode {
                pc: self.pc(pc),
                identity: InstructionIdentity {
                    index,
                    len,
                    mnemonic: name.into(),
                    dd_before: false,
                    dd_after: after,
                    fields,
                },
                reachable_dd: vec![false],
                successors: vec![self.pc(pc + len as u16)],
                reads,
                writes,
            });
        }
        if path == PostP2ControlPath::A {
            pcs.extend([0x55c8, 0x55cb, 0x55cd, 0x55cf].map(|p| self.pc(p)));
        } else {
            pcs.push(self.pc(0x5599));
        }
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
pub struct PostP2ControlSeeds(P2HandoffSeeds);
impl PostP2ControlSeeds {
    pub fn new(
        program: &ClosedPostP2ControlProgram,
        data: BTreeMap<u16, u8>,
        pointing: [[u16; 4]; 8],
        r: [u8; 8],
        er: [u16; 4],
    ) -> Result<Self> {
        P2HandoffSeeds::new(&program.p2, data, pointing, r, er).map(Self)
    }
}
#[derive(Debug, Clone, Serialize)]
pub struct ControlStepSnapshot {
    pub index: u64,
    pub before: [u8; 2],
    pub after: [u8; 2],
}
#[derive(Debug, Clone, Serialize)]
pub struct PostP2ControlReport {
    #[serde(flatten)]
    pub p2: P2HandoffReport,
    pub control_snapshot: ControlSnapshot,
    pub control_initial: [u8; 2],
    pub control_final: [u8; 2],
    pub control_instruction_retirements: u64,
    pub peripheral_control_journal: Vec<P2PeripheralEvent>,
    pub control_generation: Option<P2Generation>,
    pub control_step_snapshots: Vec<ControlStepSnapshot>,
}
pub struct PostP2ControlSession {
    inner: P2HandoffSession,
    initial: ControlSnapshot,
    last_control: [u8; 2],
    control_steps: Vec<ControlStepSnapshot>,
    native_control: Vec<(u64, [u32; 5])>,
    classification: String,
}
impl PostP2ControlSession {
    pub fn new(
        program: &ClosedPostP2ControlProgram,
        cpu: Cpu,
        full_psw: u16,
        seeds: PostP2ControlSeeds,
        path: PostP2ControlPath,
        requested_budget: u8,
        p2_snapshot: P2Snapshot,
        control: ControlSnapshot,
    ) -> Result<Self> {
        control.validate()?;
        p2_snapshot.validate()?;
        let (nodes, inventory, pcs) = program.parts(path);
        if requested_budget != budget(path)
            || cpu.pc != program.entry_pc()
            || cpu.lrb != 0x21
            || cpu.instructions != 0
            || cpu.cycles != 0
            || pcs.len() != usize::from(requested_budget)
        {
            return Err(AuditError::new(
                "PostP2EntryRejected",
                Some(i64::from(cpu.pc)),
                "fresh54F5-equivalent technical entry; closed21/20/21/23 budget",
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
            .filter(|w| w.access.address >= 0x80)
            .collect();
        writes.sort_by_key(|w| w.access);
        writes.dedup_by_key(|w| w.access);
        let inner = Session::new_post_p2_control_admitted(
            program.segment_copy(),
            cpu,
            full_psw,
            Permissions::new(reads, writes)?,
            PostP2Budget(requested_budget),
        )?;
        let values = [control.tcon0, control.trnsit_implemented_flags];
        let inner = P2HandoffSession::from_admitted(
            &program.p2,
            inner,
            seeds.0,
            path.prefix(),
            p2_snapshot,
            nodes,
            inventory,
            pcs,
            program.terminal(path),
            Some(values),
        )?;
        Ok(Self {
            inner,
            initial: control,
            last_control: values,
            control_steps: vec![],
            native_control: vec![],
            classification: program.classification().into(),
        })
    }
    fn verify_control(&self) -> Result<()> {
        if self.inner.inner.bus.post_p2_control() != Some(self.last_control) {
            return Err(AuditError::new(
                "PostP2LiveControlChanged",
                None,
                "no host mutation or boundary reseed after entry",
            ));
        }
        Ok(())
    }
    pub fn step(&mut self) -> Result<OriginalRomStep> {
        self.verify_control()?;
        let before = self.last_control;
        let outcome = self.inner.step();
        self.last_control = self
            .inner
            .inner
            .bus
            .post_p2_control()
            .expect("once initialized");
        if let Ok(step) = &outcome {
            for row in self.inner.inner.bus.control_accesses() {
                self.native_control.push((step.index, row));
            }
            self.control_steps.push(ControlStepSnapshot {
                index: step.index,
                before,
                after: self.last_control,
            });
        }
        outcome
    }
    pub fn report(&mut self) -> Result<PostP2ControlReport> {
        self.verify_control()?;
        let mut p2 = self.inner.report()?;
        p2.classification = self.classification.clone();
        let mut journal = vec![];
        let mut native_cursor = 0;
        for step in &p2.steps {
            for event in &p2.audit.data_events[step.logical_span[0]..step.logical_span[1]] {
                if !matches!(event.address, 0x40 | 0x46) || !event.serviced {
                    continue;
                }
                let (retired, row) = self.native_control.get(native_cursor).ok_or_else(|| {
                    AuditError::new(
                        "PostP2NativeServiceMissing",
                        None,
                        "actual native control service",
                    )
                })?;
                let raw: Vec<_> = p2
                    .audit
                    .raw_data_events
                    .iter()
                    .filter(|e| e.logical_ordinal == event.ordinal)
                    .collect();
                if *retired != step.index
                    || row[0] != u32::from(step.outcome.pc_before)
                    || row[1] != u32::from(event.address)
                    || row[2] != 8
                    || row[3] != u32::from(event.operation == "Write")
                    || event.value != Some(row[4] as u16)
                    || raw.len() != 1
                    || !raw[0].serviced
                    || raw[0].value != Some(row[4] as u8)
                {
                    return Err(AuditError::new(
                        "PostP2ServiceAuditMismatch",
                        Some(i64::from(event.address)),
                        "native/logical/raw control services must agree exactly",
                    ));
                }
                let native_write_ordinal = event
                    .write_ordinal
                    .map(|n| {
                        n.checked_sub(48).ok_or_else(|| {
                            AuditError::new(
                                "PostP2NativeWriteOrdinalUnderflow",
                                None,
                                "technical seeds are not native writes",
                            )
                        })
                    })
                    .transpose()?;
                journal.push(P2PeripheralEvent {
                    ordinal: native_cursor as u64,
                    pc: step.outcome.pc_before,
                    address: event.address,
                    width: 8,
                    operation: event.operation.clone(),
                    value: row[4] as u8,
                    logical_ordinal: event.ordinal,
                    raw_ordinal: raw[0].ordinal,
                    write_ordinal: event.write_ordinal,
                    native_write_ordinal,
                    same_value: event.same_value,
                    space: "PeripheralControl".into(),
                });
                native_cursor += 1;
            }
        }
        if native_cursor != self.native_control.len() {
            return Err(AuditError::new(
                "PostP2UnlinkedNativeService",
                None,
                "no service duplication or omission",
            ));
        }
        if p2.completed
            && (journal.len() != if p2.path == P2HandoffPath::A { 3 } else { 2 }
                || journal.iter().filter(|e| e.operation == "Write").count() != 1)
        {
            return Err(AuditError::new(
                "PostP2JournalCardinalityRejected",
                None,
                "one ordered actual control RMW only",
            ));
        }
        let control_instruction_retirements = p2
            .steps
            .iter()
            .filter(|s| {
                p2.p2_generation
                    .as_ref()
                    .is_some_and(|g| s.index > g.retired_instruction)
            })
            .count() as u64;
        let generation = journal.iter().find(|e| e.operation == "Write").map(|e| {
            let raw = &p2.audit.raw_data_events[e.raw_ordinal as usize];
            P2Generation {
                machine_id: 1,
                writer_pc: e.pc,
                retired_instruction: p2
                    .steps
                    .iter()
                    .find(|s| s.outcome.pc_before == e.pc)
                    .expect("actual writer")
                    .index,
                generation_ordinal: 1,
                native_write_ordinal: e.native_write_ordinal.expect("write"),
                logical_write_ordinal: e.write_ordinal.expect("write"),
                raw_write_ordinal: raw.write_ordinal.expect("write"),
                value: if e.address == 0x46 {
                    e.value & 15
                } else {
                    e.value
                },
            }
        });
        Ok(PostP2ControlReport {
            p2,
            control_snapshot: self.initial.clone(),
            control_initial: [self.initial.tcon0, self.initial.trnsit_implemented_flags],
            control_final: self.last_control,
            control_instruction_retirements,
            peripheral_control_journal: journal,
            control_generation: generation,
            control_step_snapshots: self.control_steps.clone(),
        })
    }
}
#[cfg(test)]
#[path = "audit_post_p2_control_tests.rs"]
mod tests;
