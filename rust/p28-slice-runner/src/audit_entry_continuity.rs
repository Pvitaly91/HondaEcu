//! M2bu hard-closed predecessor-to-exit admission. No instruction interpreter.
//! All functional operations use the existing Session checked-step and the
//! production CPU/Bus/decoder/Exec. The private wrapper cannot expose a generic
//! Session, replace its CPU/Bus, reseed it, or set its PC after entry.
use super::{
    original_rom::{OriginalNode, OriginalState},
    Access, AuditError, AuditReport, ClosedOriginalRomProgram, CompositePath, InstructionIdentity,
    OriginalRomSourceBinding, OriginalRomStep, Permissions, ProgramSegment, Result, Session,
    Snapshot, WriteAccess,
};
use crate::{cpu::Cpu, decoder::Fields};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum EntryContinuityPath {
    A,
    B,
    C,
    D,
    JbrAlternate,
    JneAlternate,
}
impl EntryContinuityPath {
    pub fn budget(self) -> u8 {
        match self {
            Self::A => 16,
            Self::B => 18,
            Self::C => 19,
            Self::D => 21,
            Self::JbrAlternate => 1,
            Self::JneAlternate => 6,
        }
    }
    pub fn boundary_only(self) -> bool {
        matches!(self, Self::JbrAlternate | Self::JneAlternate)
    }
    fn algorithm_path(self) -> CompositePath {
        match self {
            Self::A | Self::JbrAlternate | Self::JneAlternate => CompositePath::A,
            Self::B => CompositePath::B,
            Self::C => CompositePath::C,
            Self::D => CompositePath::D,
        }
    }
}

// Private fields: a host integer is not a constructor for a wider Session.
pub(super) struct EntryBudget {
    count: u8,
}
impl EntryBudget {
    fn for_path(path: EntryContinuityPath) -> Self {
        Self {
            count: path.budget(),
        }
    }
    pub(super) fn retirements(&self) -> u8 {
        self.count
    }
}

#[derive(Clone, Copy)]
enum Mapping {
    Native,
    Invented,
}
impl Mapping {
    fn base(self) -> u16 {
        match self {
            Self::Native => 0x54f5,
            Self::Invented => 0x6200,
        }
    }
    fn pc(self, native: u16) -> u16 {
        self.base() + (native - 0x54f5)
    }
    fn gate(self) -> u16 {
        match self {
            Self::Native => 0x128,
            Self::Invented => 0x130,
        }
    }
    fn word(self) -> u16 {
        match self {
            Self::Native => 0x196,
            Self::Invented => 0x19a,
        }
    }
    fn output(self) -> u16 {
        match self {
            Self::Native => 0x117,
            Self::Invented => 0x11b,
        }
    }
}

pub struct ClosedEntryContinuityProgram {
    segment: ProgramSegment,
    mapping: Mapping,
    nodes: Vec<OriginalNode>,
    inventory: Vec<u16>,
    source_binding: Option<OriginalRomSourceBinding>,
}
impl ClosedEntryContinuityProgram {
    pub fn admit_host_verified_segment(
        base: u32,
        bytes: Vec<u8>,
        sha256: &str,
        binding: OriginalRomSourceBinding,
    ) -> Result<Self> {
        if base != 0x54f5 || bytes.len() != 208 {
            return Err(AuditError::new(
                "EntryContinuitySegmentRejected",
                Some(i64::from(base)),
                "only unchanged208-byte original[54F5,55C5), no padding/relocation",
            ));
        }
        let segment = ProgramSegment::new(base, bytes, sha256)?;
        // Reuse M2bt's unchanged binding admission and reviewed18-site metadata.
        // This temporary program is metadata only: no CPU or Bus is constructed.
        let suffix = segment.bytes[122..].to_vec();
        let digest = crate::audit_sha256::digest(&suffix);
        let original = ClosedOriginalRomProgram::admit_host_verified_segment(
            0x556f,
            suffix,
            &digest,
            binding.clone(),
        )?;
        let (nodes, inventory) = original.closed_metadata();
        Ok(Self::from_metadata(
            segment,
            Mapping::Native,
            nodes,
            inventory,
            Some(binding),
        ))
    }
    pub fn explicit_invented_public_fixture() -> Self {
        let original = ClosedOriginalRomProgram::explicit_invented_public_fixture();
        let (mut nodes, mut inventory) = original.closed_metadata();
        // Relocation applies ONLY to the invented public metadata, never ROM.
        for node in &mut nodes {
            node.pc = 0x627a + (node.pc - 0x6000);
            for next in &mut node.successors {
                *next = 0x627a + (*next - 0x6000);
            }
        }
        *inventory
            .iter_mut()
            .find(|address| **address == 0x128)
            .expect("closed unused gate role") = 0x130;
        inventory.sort_unstable();
        let mapping = Mapping::Invented;
        let mut all_nodes = predecessor_nodes(mapping);
        nodes[0].reachable_dd = vec![true];
        all_nodes.extend(nodes.clone());
        let mut bytes = vec![0xa5; 208];
        for node in &all_nodes {
            let encoded = invented_encoding(node);
            let start = usize::from(node.pc - mapping.base());
            bytes[start..start + encoded.len()].copy_from_slice(&encoded);
        }
        let digest = crate::audit_sha256::digest(&bytes);
        let segment = ProgramSegment::new(u32::from(mapping.base()), bytes, &digest)
            .expect("fixed invented source");
        Self::from_metadata(segment, mapping, nodes, inventory, None)
    }
    fn from_metadata(
        segment: ProgramSegment,
        mapping: Mapping,
        mut algorithm: Vec<OriginalNode>,
        inventory: Vec<u16>,
        source_binding: Option<OriginalRomSourceBinding>,
    ) -> Self {
        // The predecessor's actual word L supplies DD1 at the algorithm seam.
        algorithm[0].reachable_dd = vec![true];
        let mut nodes = predecessor_nodes(mapping);
        nodes.extend(algorithm);
        assert_eq!(nodes.len(), 24);
        Self {
            segment,
            mapping,
            nodes,
            inventory,
            source_binding,
        }
    }
    pub fn entry_pc(&self) -> u16 {
        self.mapping.base()
    }
    pub fn program_sha256(&self) -> &str {
        self.segment.sha256()
    }
    pub fn classification(&self) -> &'static str {
        if self.source_binding.is_some() {
            "OriginalRomBytes_TechnicalCallerToExitExecution"
        } else {
            "ExplicitInventedPublicEntryFixture"
        }
    }
    pub fn terminal(&self, path: EntryContinuityPath) -> u16 {
        self.mapping.pc(match path {
            EntryContinuityPath::A => 0x55c5,
            EntryContinuityPath::JbrAlternate => 0x5533,
            EntryContinuityPath::JneAlternate => 0x5503,
            _ => 0x5596,
        })
    }
    fn path_pcs(&self, path: EntryContinuityPath) -> Vec<u16> {
        let mut pcs = vec![0x54f5];
        if path != EntryContinuityPath::JbrAlternate {
            pcs.extend([0x54f8, 0x54fa, 0x54fc, 0x54fd, 0x5501]);
        }
        if !path.boundary_only() {
            pcs.extend([0x556f, 0x5571, 0x5572, 0x5575, 0x5576, 0x5578, 0x557d]);
            match path {
                EntryContinuityPath::A => pcs.extend([0x55bf, 0x55c1, 0x55c3]),
                EntryContinuityPath::B => pcs.extend([0x557f, 0x5582, 0x5585, 0x5592, 0x5594]),
                EntryContinuityPath::C => {
                    pcs.extend([0x557f, 0x5582, 0x5585, 0x5588, 0x5592, 0x5594])
                }
                EntryContinuityPath::D => pcs.extend([
                    0x557f, 0x5582, 0x5585, 0x5588, 0x558b, 0x558e, 0x5592, 0x5594,
                ]),
                _ => unreachable!("positive path"),
            }
        }
        pcs.into_iter().map(|pc| self.mapping.pc(pc)).collect()
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

fn predecessor_nodes(mapping: Mapping) -> Vec<OriginalNode> {
    let fields = |n8, n8_alt, rel8| Fields {
        n8,
        n8_alt,
        rel8,
        ..Fields::default()
    };
    let read = |address, width| Access { address, width };
    let mut nodes = Vec::new();
    let mut add = |pc,
                   index,
                   len,
                   mnemonic: &str,
                   f,
                   dd_after,
                   dd: Vec<bool>,
                   successors: Vec<u16>,
                   reads,
                   writes| {
        nodes.push(OriginalNode {
            pc: mapping.pc(pc),
            identity: InstructionIdentity {
                index,
                len,
                mnemonic: mnemonic.into(),
                dd_before: false,
                dd_after,
                fields: f,
            },
            reachable_dd: dd,
            successors: successors
                .into_iter()
                .map(|next| mapping.pc(next))
                .collect(),
            reads,
            writes,
        });
    };
    add(
        0x54f5,
        703,
        3,
        "JBR off N8.2, rel8",
        fields(mapping.gate() as u8, 0, 59),
        None,
        vec![false, true],
        vec![0x5533, 0x54f8],
        vec![read(mapping.gate(), 8)],
        vec![],
    );
    add(
        0x54f8,
        1375,
        2,
        "MOVB r0, #N8",
        fields(0xff, 0, 0),
        None,
        vec![false, true],
        vec![0x54fa],
        vec![],
        vec![WriteAccess {
            access: read(0x108, 8),
            rmw_required: false,
        }],
    );
    add(
        0x54fa,
        732,
        2,
        "L A, off N8",
        fields(mapping.word() as u8, 0, 0),
        Some(true),
        vec![false, true],
        vec![0x54fc],
        vec![read(mapping.word(), 16)],
        vec![],
    );
    add(
        0x54fc,
        2284,
        1,
        "ST A, er1",
        fields(0, 0, 0),
        None,
        vec![true],
        vec![0x54fd],
        vec![],
        vec![WriteAccess {
            access: read(0x10a, 16),
            rmw_required: false,
        }],
    );
    add(
        0x54fd,
        563,
        4,
        "CMPB off N'8, #N8",
        fields(0x0f, mapping.output() as u8, 0),
        None,
        vec![true],
        vec![0x5501],
        vec![read(mapping.output(), 8)],
        vec![],
    );
    add(
        0x5501,
        718,
        2,
        "JNE rel8",
        fields(0, 0, 108),
        None,
        vec![true],
        vec![0x556f, 0x5503],
        vec![],
        vec![],
    );
    nodes
}

// Closed invented instruction encoding only; not original ROM recovery and
// not an execution oracle. Host fixtures independently encode these forms.
fn invented_encoding(node: &OriginalNode) -> Vec<u8> {
    let f = node.identity.fields;
    match node.identity.index {
        703 => vec![0xda, f.n8, f.rel8 as u8],
        1375 => vec![0x98, f.n8],
        732 => vec![0xe4, f.n8],
        2284 => vec![0x89],
        563 => vec![0xc4, f.n8_alt, 0xc0, f.n8],
        718 => vec![0xce, f.rel8 as u8],
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
        _ => unreachable!("closed24-node invented forms"),
    }
}

pub struct EntryContinuitySeeds {
    data: BTreeMap<u16, u8>,
    pointing: [[u16; 4]; 8],
}
impl EntryContinuitySeeds {
    pub fn new(
        program: &ClosedEntryContinuityProgram,
        data: BTreeMap<u16, u8>,
        pointing: [[u16; 4]; 8],
        local_r: [u8; 8],
        local_er: [u16; 4],
    ) -> Result<Self> {
        if data.keys().copied().collect::<Vec<_>>() != program.inventory {
            return Err(AuditError::new(
                "IncompleteEntryContinuitySeeds",
                None,
                "exact16 closed DATA roles",
            ));
        }
        if (0..8).any(|n| data[&(0x108 + n as u16)] != local_r[n])
            || (0..4)
                .any(|n| local_er[n] != u16::from_le_bytes([local_r[n * 2], local_r[n * 2 + 1]]))
        {
            return Err(AuditError::new(
                "ConflictingEntryContinuityAliases",
                None,
                "initial r/er and DATA aliases must agree",
            ));
        }
        Ok(Self { data, pointing })
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct EntryContinuityReport {
    pub classification: String,
    pub source_binding: Option<OriginalRomSourceBinding>,
    pub program_node_count: usize,
    pub path: EntryContinuityPath,
    pub entry: Snapshot,
    pub current: Snapshot,
    pub full_psw: u16,
    pub steps: Vec<OriginalRomStep>,
    pub completed: bool,
    pub positive_completed: bool,
    pub boundary_only: bool,
    pub actual_handoff_observed: bool,
    pub native_predecessor_retirements: u64,
    pub algorithm_retirements: u64,
    pub stop_before_pc: Option<u16>,
    pub audit: AuditReport,
}

pub struct EntryContinuitySession {
    inner: Box<Session>,
    cpu_identity: usize,
    bus_identity: usize,
    last_actual: Snapshot,
    continuity_fault: Option<AuditError>,
    path: EntryContinuityPath,
    mapping: Mapping,
}
impl EntryContinuitySession {
    pub fn new(
        program: &ClosedEntryContinuityProgram,
        cpu: Cpu,
        full_psw: u16,
        seeds: EntryContinuitySeeds,
        path: EntryContinuityPath,
        budget: u8,
    ) -> Result<Self> {
        let pcs = program.path_pcs(path);
        if cpu.pc != program.entry_pc()
            || cpu.lrb != 0x21
            || cpu.cycles != 0
            || cpu.instructions != 0
            || budget != path.budget()
            || usize::from(budget) != pcs.len()
        {
            return Err(AuditError::new(
                "EntryContinuityEntryRejected",
                Some(i64::from(cpu.pc)),
                "closed entry/LRB, fresh counters and exact route budget; no host budget widening",
            ));
        }
        let active: Vec<_> = program
            .nodes
            .iter()
            .filter(|node| pcs.contains(&node.pc))
            .collect();
        let mut reads: Vec<_> = active.iter().flat_map(|node| node.reads.clone()).collect();
        reads.sort();
        reads.dedup();
        let mut writes: Vec<_> = active.iter().flat_map(|node| node.writes.clone()).collect();
        writes.sort_by_key(|right| right.access);
        writes.dedup_by_key(|right| right.access);
        let mut inner = Session::new_entry_continuity_admitted(
            program.segment_copy(),
            cpu,
            full_psw,
            Permissions::new(reads, writes)?,
            EntryBudget::for_path(path),
        )?;
        for (address, value) in seeds.data {
            inner.seed_byte(address, value)?;
        }
        for (bank, words) in seeds.pointing.iter().enumerate() {
            for (slot, value) in words.iter().enumerate() {
                inner.seed_word(0x80 + bank as u16 * 8 + slot as u16 * 2, *value)?;
            }
        }
        let entry = inner.diagnostic_snapshot()?;
        inner
            .bus
            .audit
            .as_ref()
            .expect("installed")
            .install_original(OriginalState {
                nodes: program.nodes.clone(),
                pcs,
                inventory: program.inventory.clone(),
                terminal: program.terminal(path),
                path: path.algorithm_path(),
                entry,
                classification: program.classification().into(),
                source_binding: program.source_binding.clone(),
                steps: vec![],
            })?;
        inner.begin_functional()?;
        let last_actual = inner.diagnostic_snapshot()?;
        let inner = Box::new(inner);
        // Addresses identify this owned heap allocation only, never native DATA
        // ownership; they are not serialized or compared across cases/platforms.
        let cpu_identity = std::ptr::from_ref(&inner.cpu) as usize;
        let bus_identity = std::ptr::from_ref(&inner.bus) as usize;
        Ok(Self {
            inner,
            cpu_identity,
            bus_identity,
            last_actual,
            continuity_fault: None,
            path,
            mapping: program.mapping,
        })
    }
    fn verify_continuity(&mut self) -> Result<()> {
        if let Some(error) = &self.continuity_fault {
            return Err(error.clone());
        }
        let error = if std::ptr::from_ref(&self.inner.cpu) as usize != self.cpu_identity
            || std::ptr::from_ref(&self.inner.bus) as usize != self.bus_identity
        {
            Some(AuditError::new(
                "EntryContinuityMachineSubstitutionRejected",
                None,
                "the same privately owned CPU and Bus allocation must continue",
            ))
        } else if self.inner.diagnostic_snapshot()? != self.last_actual {
            Some(AuditError::new(
                "EntryContinuityLiveStateChanged",
                None,
                "no host PC/register/RAM change between actual retired snapshots",
            ))
        } else {
            None
        };
        if let Some(error) = error {
            self.continuity_fault = Some(error.clone());
            return Err(error);
        }
        Ok(())
    }
    pub fn step(&mut self) -> Result<OriginalRomStep> {
        self.verify_continuity()?;
        let outcome = self.inner.step_original_rom();
        // Retain actual fault-side state too; never restore the previous state.
        self.last_actual = self.inner.diagnostic_snapshot()?;
        outcome
    }
    pub fn report(&mut self) -> Result<EntryContinuityReport> {
        self.verify_continuity()?;
        let report = self.inner.original_rom_report()?;
        let handoff = report.steps.iter().any(|step| {
            step.outcome.retired
                && step.outcome.pc_before == self.mapping.pc(0x5501)
                && step.outcome.pc_after == self.mapping.pc(0x556f)
        });
        let count = report.steps.len() as u64;
        Ok(EntryContinuityReport {
            classification: report.classification,
            source_binding: report.source_binding,
            program_node_count: report.program_node_count,
            path: self.path,
            entry: report.entry,
            current: report.current,
            full_psw: report.full_psw,
            steps: report.steps,
            completed: report.completed,
            positive_completed: report.completed && !self.path.boundary_only() && handoff,
            boundary_only: self.path.boundary_only(),
            actual_handoff_observed: handoff,
            native_predecessor_retirements: count.min(6),
            algorithm_retirements: count.saturating_sub(6),
            stop_before_pc: report.stop_before_pc,
            audit: report.audit,
        })
    }
}

#[cfg(test)]
#[path = "audit_entry_continuity_tests.rs"]
mod tests;
