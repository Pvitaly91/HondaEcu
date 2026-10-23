//! M2bt closed source admission/lifecycle. No CPU instruction semantics live here.
//! The native source is supplied unchanged by the independently verifying host.
//! Its claims do not establish historical DATA ownership or physical SF semantics.
use super::{
    Access, AuditError, AuditReport, CompositePath, InstructionIdentity, Permissions,
    ProgramSegment, Result, Session, Snapshot, StepOutcome, WriteAccess,
};
use crate::{cpu::Cpu, decoder::Fields};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

pub const ORIGINAL_ROM_BASE_COMMIT: &str = "4196153c6bcda3da5b164db752a8be4011c4e598";
pub const ORIGINAL_ROM_CONTRACT_SHA256: &str =
    "b8a1a482dfa8f48f310db89d291014d1f4ebf83f51022cf7f70fb1dea0c1da30";

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct OriginalRomSourceBinding {
    pub base_commit: String,
    pub contract_sha256: String,
    pub whole_rom_sha256: String,
    pub source_admission: String,
}
impl OriginalRomSourceBinding {
    fn validate(&self) -> Result<()> {
        if self.base_commit != ORIGINAL_ROM_BASE_COMMIT
            || self.contract_sha256 != ORIGINAL_ROM_CONTRACT_SHA256
            || self.source_admission != "M2bsHostVerifiedOriginalRom"
            || self.whole_rom_sha256.len() != 64
            || !self
                .whole_rom_sha256
                .bytes()
                .all(|v| v.is_ascii_digit() || (b'a'..=b'f').contains(&v))
        {
            return Err(AuditError::new("OriginalSourceBindingRejected", None,
                "exact frozen M2bs source binding and explicit host verification claim required; no native DATA authority"));
        }
        Ok(())
    }
}

#[derive(Debug, Clone)]
pub(crate) struct OriginalNode {
    pub(crate) pc: u16,
    pub(crate) identity: InstructionIdentity,
    pub(crate) reachable_dd: Vec<bool>,
    pub(crate) successors: Vec<u16>,
    pub(crate) reads: Vec<Access>,
    pub(crate) writes: Vec<WriteAccess>,
}
impl OriginalNode {
    pub(crate) fn instruction(&self, dd: bool) -> InstructionIdentity {
        let mut identity = self.identity.clone();
        identity.dd_before = dd;
        identity
    }
}

#[derive(Clone, Copy)]
struct Layout {
    base: u16,
    a: u16,
    b: u16,
    word: u16,
    output: u16,
    flag7: u16,
    flag5: u16,
}
impl Layout {
    fn native() -> Self {
        Self {
            base: 0x556f,
            a: 0x18e,
            b: 0x18f,
            word: 0x196,
            output: 0x117,
            flag7: 0x12a,
            flag5: 0x124,
        }
    }
    fn invented() -> Self {
        Self {
            base: 0x6000,
            a: 0x192,
            b: 0x193,
            word: 0x19a,
            output: 0x11b,
            flag7: 0x12d,
            flag5: 0x12e,
        }
    }
    fn pc(self, offset: u16) -> u16 {
        self.base + offset
    }
    fn inventory(self) -> Vec<u16> {
        let mut result: Vec<u16> = (0x108..=0x10f).collect();
        result.extend([
            self.output,
            self.flag5,
            0x128,
            self.flag7,
            self.a,
            self.b,
            self.word,
            self.word + 1,
        ]);
        result.sort_unstable();
        result
    }
}

/// Closed source and typed-site contract, never a generic ROM admission mechanism.
pub struct ClosedOriginalRomProgram {
    segment: ProgramSegment,
    layout: Layout,
    nodes: Vec<OriginalNode>,
    source_binding: Option<OriginalRomSourceBinding>,
}
impl ClosedOriginalRomProgram {
    pub fn admit_host_verified_segment(
        base: u32,
        bytes: Vec<u8>,
        sha256: &str,
        binding: OriginalRomSourceBinding,
    ) -> Result<Self> {
        binding.validate()?;
        if base != 0x556f || bytes.len() != 0x56 {
            return Err(AuditError::new(
                "OriginalSegmentExtentRejected",
                Some(i64::from(base)),
                "one unchanged contiguous original segment [556F,55C5); no padding or relocation",
            ));
        }
        let segment = ProgramSegment::new(base, bytes, sha256)?;
        let layout = Layout::native();
        Ok(Self {
            segment,
            layout,
            nodes: nodes(layout),
            source_binding: Some(binding),
        })
    }
    /// A separate hard-closed, explicitly invented public regression. This emitter
    /// cannot accept a caller layout or produce the native source.
    pub fn explicit_invented_public_fixture() -> Self {
        let layout = Layout::invented();
        let nodes = nodes(layout);
        let mut bytes = vec![0xa5; 0x56];
        for node in &nodes {
            let f = node.identity.fields;
            let encoded: Vec<u8> = match node.identity.index {
                747 => vec![0xf4, f.n8],
                2198 => vec![0x53],
                1862 => vec![0xc4, f.n8, 0xb7],
                739 => vec![0x78],
                333 => vec![0xd7, f.n8],
                498 => vec![0xb4, f.n8, 0xc0, f.n16 as u8, (f.n16 >> 8) as u8],
                719 => vec![0xca, f.rel8 as u8],
                1504 => vec![0xc4, f.n8, 0x49],
                349 => vec![0xc4, f.n8, 0xd1],
                716 => vec![0xef, f.n8, f.rel8 as u8],
                714 => vec![0xed, f.n8, f.rel8 as u8],
                1678 => vec![0xc4, f.n8_alt, 0xe0, f.n8],
                1619 => vec![0xe6, f.n8],
                738 => vec![0x77, f.n8],
                2301 => vec![0xd4, f.n8],
                _ => unreachable!("closed invented forms"),
            };
            let start = usize::from(node.pc - layout.base);
            bytes[start..start + encoded.len()].copy_from_slice(&encoded);
        }
        let digest = crate::audit_sha256::digest(&bytes);
        Self {
            segment: ProgramSegment::new(u32::from(layout.base), bytes, &digest)
                .expect("fixed fixture"),
            layout,
            nodes,
            source_binding: None,
        }
    }
    pub fn entry_pc(&self) -> u16 {
        self.layout.base
    }
    pub fn program_sha256(&self) -> &str {
        &self.segment.digest
    }
    pub fn classification(&self) -> &'static str {
        if self.source_binding.is_some() {
            "OriginalRomBytes_TechnicalSeededExecution"
        } else {
            "ExplicitInventedPublicFixture"
        }
    }
    fn segment_copy(&self) -> ProgramSegment {
        ProgramSegment {
            base: self.segment.base,
            end: self.segment.end,
            bytes: self.segment.bytes.clone(),
            digest: self.segment.digest.clone(),
        }
    }
    fn path_pcs(&self, path: CompositePath) -> Vec<u16> {
        let mut offsets = vec![0, 2, 3, 6, 7, 9, 14];
        match path {
            CompositePath::A => offsets.extend([80, 82, 84]),
            CompositePath::B => offsets.extend([16, 19, 22, 35, 37]),
            CompositePath::C => offsets.extend([16, 19, 22, 25, 35, 37]),
            CompositePath::D => offsets.extend([16, 19, 22, 25, 28, 31, 35, 37]),
        }
        offsets.into_iter().map(|v| self.layout.pc(v)).collect()
    }
    fn terminal(&self, path: CompositePath) -> u16 {
        self.layout
            .pc(if path == CompositePath::A { 86 } else { 39 })
    }
}

// Reviewed ISA-form/operand/control-flow metadata, not an OEM byte fixture or
// a replacement interpreter. The existing decoder and Exec remain authoritative.
fn nodes(l: Layout) -> Vec<OriginalNode> {
    let read = |address, width| Access { address, width };
    let write = |address, rmw_required| WriteAccess {
        access: read(address, 8),
        rmw_required,
    };
    let f = |n8, n8_alt, n16, rel8| Fields {
        n8,
        n8_alt,
        n16,
        rel8,
        ..Fields::default()
    };
    let mut result = Vec::new();
    let mut add = |offset,
                   index,
                   len,
                   mnemonic: &str,
                   fields,
                   resets_dd: bool,
                   next: Vec<u16>,
                   reads: Vec<Access>,
                   writes: Vec<WriteAccess>| {
        result.push(OriginalNode {
            pc: l.pc(offset),
            identity: InstructionIdentity {
                index,
                len,
                mnemonic: mnemonic.into(),
                dd_before: false,
                dd_after: resets_dd.then_some(false),
                fields,
            },
            reachable_dd: if offset == 0 {
                vec![false, true]
            } else {
                vec![false]
            },
            successors: next.into_iter().map(|v| l.pc(v)).collect(),
            reads,
            writes,
        });
    };
    add(
        0,
        747,
        2,
        "LB A, off N8",
        f(l.a as u8, 0, 0, 0),
        true,
        vec![2],
        vec![read(l.a, 8)],
        vec![],
    );
    add(
        2,
        2198,
        1,
        "SLLB A",
        f(0, 0, 0, 0),
        false,
        vec![3],
        vec![],
        vec![],
    );
    add(
        3,
        1862,
        3,
        "ROLB off N8",
        f(l.a as u8, 0, 0, 0),
        false,
        vec![6],
        vec![read(l.a, 8)],
        vec![write(l.a, true)],
    );
    add(
        6,
        739,
        1,
        "LB A, r0",
        f(0, 0, 0, 0),
        true,
        vec![7],
        vec![read(0x108, 8)],
        vec![],
    );
    add(
        7,
        333,
        2,
        "ANDB A, off N8",
        f(l.a as u8, 0, 0, 0),
        false,
        vec![9],
        vec![read(l.a, 8)],
        vec![],
    );
    add(
        9,
        498,
        5,
        "CMP off N8, #N16",
        f(l.word as u8, 0, 0xc0, 0),
        false,
        vec![14],
        vec![read(l.word, 16)],
        vec![],
    );
    add(
        14,
        719,
        2,
        "JLT rel8",
        f(0, 0, 0, 64),
        false,
        vec![80, 16],
        vec![],
        vec![],
    );
    add(
        16,
        1504,
        3,
        "MOVB r1, off N8",
        f(l.output as u8, 0, 0, 0),
        false,
        vec![19],
        vec![read(l.output, 8)],
        vec![write(0x109, false)],
    );
    add(
        19,
        349,
        3,
        "ANDB off N8, A",
        f(l.output as u8, 0, 0, 0),
        false,
        vec![22],
        vec![read(l.output, 8)],
        vec![write(l.output, true)],
    );
    add(
        22,
        716,
        3,
        "JBS off N8.7, rel8",
        f(l.flag7 as u8, 0, 0, 10),
        false,
        vec![35, 25],
        vec![read(l.flag7, 8)],
        vec![],
    );
    add(
        25,
        714,
        3,
        "JBS off N8.5, rel8",
        f(l.flag5 as u8, 0, 0, 7),
        false,
        vec![35, 28],
        vec![read(l.flag5, 8)],
        vec![],
    );
    add(
        28,
        349,
        3,
        "ANDB off N8, A",
        f(l.b as u8, 0, 0, 0),
        false,
        vec![31],
        vec![read(l.b, 8)],
        vec![write(l.b, true)],
    );
    add(
        31,
        1678,
        4,
        "ORB off N'8, #N8",
        f(1, l.flag7 as u8, 0, 0),
        false,
        vec![35],
        vec![read(l.flag7, 8)],
        vec![write(l.flag7, true)],
    );
    add(
        35,
        747,
        2,
        "LB A, off N8",
        f(l.b as u8, 0, 0, 0),
        true,
        vec![37],
        vec![read(l.b, 8)],
        vec![],
    );
    add(
        37,
        1619,
        2,
        "ORB A, #N8",
        f(0xf0, 0, 0, 0),
        false,
        vec![39],
        vec![],
        vec![],
    );
    add(
        80,
        738,
        2,
        "LB A, #N8",
        f(0x0f, 0, 0, 0),
        true,
        vec![82],
        vec![],
        vec![],
    );
    add(
        82,
        2301,
        2,
        "STB A, off N8",
        f(l.output as u8, 0, 0, 0),
        false,
        vec![84],
        vec![],
        vec![write(l.output, false)],
    );
    add(
        84,
        2301,
        2,
        "STB A, off N8",
        f(l.b as u8, 0, 0, 0),
        false,
        vec![86],
        vec![],
        vec![write(l.b, false)],
    );
    result
}

pub struct OriginalRomSeeds {
    data: BTreeMap<u16, u8>,
    pointing: [[u16; 4]; 8],
}
impl OriginalRomSeeds {
    pub fn new(
        program: &ClosedOriginalRomProgram,
        data: BTreeMap<u16, u8>,
        pointing: [[u16; 4]; 8],
        local_r: [u8; 8],
        local_er: [u16; 4],
    ) -> Result<Self> {
        if data.keys().copied().collect::<Vec<_>>() != program.layout.inventory() {
            return Err(AuditError::new(
                "IncompleteOriginalSeeds",
                None,
                "exact sixteen source-specific DATA bytes",
            ));
        }
        if (0..8).any(|n| data[&(0x108 + n as u16)] != local_r[n])
            || (0..4)
                .any(|n| local_er[n] != u16::from_le_bytes([local_r[2 * n], local_r[2 * n + 1]]))
        {
            return Err(AuditError::new(
                "ConflictingOriginalAliases",
                None,
                "actual local aliases must agree before initialization",
            ));
        }
        Ok(Self { data, pointing })
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct OriginalRomStep {
    pub index: u64,
    pub node_identity: String,
    pub full_psw_before: u16,
    pub full_psw_after: u16,
    pub before: Snapshot,
    pub after: Snapshot,
    pub outcome: StepOutcome,
    pub program_span: [usize; 2],
    pub logical_span: [usize; 2],
    pub raw_span: [usize; 2],
}
#[derive(Debug, Clone, Serialize)]
pub struct OriginalRomReport {
    pub classification: String,
    pub source_binding: Option<OriginalRomSourceBinding>,
    pub program_node_count: usize,
    pub path: CompositePath,
    pub entry: Snapshot,
    pub current: Snapshot,
    pub full_psw: u16,
    pub steps: Vec<OriginalRomStep>,
    pub completed: bool,
    pub stop_before_pc: Option<u16>,
    pub audit: AuditReport,
}
pub(crate) struct OriginalState {
    pub(crate) nodes: Vec<OriginalNode>,
    pub(crate) pcs: Vec<u16>,
    pub(crate) inventory: Vec<u16>,
    pub(crate) terminal: u16,
    pub(crate) path: CompositePath,
    pub(crate) entry: Snapshot,
    pub(crate) classification: String,
    pub(crate) source_binding: Option<OriginalRomSourceBinding>,
    pub(crate) steps: Vec<OriginalRomStep>,
}
impl OriginalState {
    pub(crate) fn node(&self, pc: u16, dd: bool, retired: u64) -> Result<OriginalNode> {
        if self.pcs.get(retired as usize) != Some(&pc) {
            return Err(AuditError::new(
                "OriginalPcBoundaryRejected",
                Some(i64::from(pc)),
                "closed next instruction boundary; stop-before targets are never selected",
            ));
        }
        let node = self
            .nodes
            .iter()
            .find(|n| n.pc == pc)
            .expect("closed path node");
        if !node.reachable_dd.contains(&dd) {
            return Err(AuditError::new(
                "WrongIncomingDd",
                Some(i64::from(pc)),
                "closed reachable DD",
            ));
        }
        Ok(node.clone())
    }
    pub(crate) fn successor(
        &self,
        origin: u16,
        after: u16,
        retired: u64,
        index: usize,
    ) -> Result<bool> {
        let node = self.nodes.iter().find(|n| n.pc == origin).ok_or_else(|| {
            AuditError::new(
                "OriginalPcBoundaryRejected",
                Some(i64::from(origin)),
                "actual origin",
            )
        })?;
        let next = self
            .pcs
            .get(retired as usize + 1)
            .copied()
            .unwrap_or(self.terminal);
        if self.pcs.get(retired as usize) != Some(&origin)
            || after != next
            || !node.successors.contains(&after)
            || index != node.identity.index
        {
            return Err(AuditError::new("OriginalSuccessorRejected", Some(i64::from(after)),
                "actual selected form and actual successor must match closed obligation; no PC assignment"));
        }
        Ok(retired as usize + 1 == self.pcs.len())
    }
    pub(crate) fn data_right(
        &self,
        pc: u16,
        index: usize,
        access: Access,
        write: bool,
    ) -> Result<bool> {
        let node = self
            .nodes
            .iter()
            .find(|n| n.pc == pc && n.identity.index == index)
            .filter(|_| self.pcs.contains(&pc))
            .ok_or_else(|| {
                AuditError::new(
                    "OriginalDataOutsideInstruction",
                    Some(i64::from(pc)),
                    "actual closed selected instruction",
                )
            })?;
        if write {
            node.writes
                .iter()
                .find(|r| r.access == access)
                .map(|r| r.rmw_required)
        } else {
            node.reads.contains(&access).then_some(false)
        }
        .ok_or_else(|| {
            AuditError::new(
                if write {
                    "OriginalLogicalWriteDenied"
                } else {
                    "OriginalLogicalReadDenied"
                },
                Some(i64::from(access.address)),
                "closed PC/form/width/direction right",
            )
        })
    }
}

impl Session {
    pub fn new_closed_original_rom(
        program: &ClosedOriginalRomProgram,
        cpu: Cpu,
        full_psw: u16,
        seeds: OriginalRomSeeds,
        path: CompositePath,
        budget: u8,
    ) -> Result<Self> {
        let pcs = program.path_pcs(path);
        if cpu.pc != program.layout.base
            || cpu.lrb != 0x21
            || cpu.cycles != 0
            || cpu.instructions != 0
            || usize::from(budget) != pcs.len()
        {
            return Err(AuditError::new(
                "OriginalEntryRejected",
                Some(i64::from(cpu.pc)),
                "exact source entry/LRB, fresh counters and exact declared path budget",
            ));
        }
        let active: Vec<_> = program
            .nodes
            .iter()
            .filter(|n| pcs.contains(&n.pc))
            .collect();
        let mut reads: Vec<_> = active.iter().flat_map(|n| n.reads.clone()).collect();
        reads.sort();
        reads.dedup();
        let mut writes: Vec<_> = active.iter().flat_map(|n| n.writes.clone()).collect();
        writes.sort_by_key(|w| w.access);
        writes.dedup_by_key(|w| w.access);
        let mut session = Self::new(
            program.segment_copy(),
            cpu,
            full_psw,
            Permissions::new(reads, writes)?,
            budget,
        )?;
        for (address, value) in seeds.data {
            session.seed_byte(address, value)?;
        }
        for (bank, words) in seeds.pointing.iter().enumerate() {
            for (slot, value) in words.iter().enumerate() {
                session.seed_word(0x80 + bank as u16 * 8 + slot as u16 * 2, *value)?;
            }
        }
        let entry = session.diagnostic_snapshot()?;
        session
            .bus
            .audit
            .as_ref()
            .expect("installed")
            .install_original(OriginalState {
                nodes: program.nodes.clone(),
                pcs,
                inventory: program.layout.inventory(),
                terminal: program.terminal(path),
                path,
                entry,
                classification: program.classification().into(),
                source_binding: program.source_binding.clone(),
                steps: vec![],
            })?;
        session.begin_functional()?;
        Ok(session)
    }
    pub fn step_original_rom(&mut self) -> Result<OriginalRomStep> {
        let node = match self
            .bus
            .audit
            .as_ref()
            .expect("installed")
            .original_node(self.cpu.pc, self.cpu.dd)
        {
            Ok(node) => node,
            Err(error) => {
                return Err(self
                    .bus
                    .audit
                    .as_ref()
                    .expect("installed")
                    .reject_step_attempt(error))
            }
        };
        let before = self.diagnostic_snapshot()?;
        let full_psw_before = self.cpu.psw_u16();
        let outcome = self.checked_step(&node.instruction(self.cpu.dd))?;
        let full_psw_after = self.cpu.psw_u16();
        let after = self.diagnostic_snapshot()?;
        self.bus
            .audit
            .as_ref()
            .expect("installed")
            .record_original_step(before, after, full_psw_before, full_psw_after, outcome)
    }
    pub fn original_rom_report(&mut self) -> Result<OriginalRomReport> {
        self.bus
            .audit
            .as_ref()
            .expect("installed")
            .require_original()?;
        let current = self.diagnostic_snapshot()?;
        self.bus
            .audit
            .as_ref()
            .expect("installed")
            .original_report(current, self.cpu.psw_u16())
    }
}

#[cfg(test)]
#[path = "audit_original_rom_tests.rs"]
mod tests;
