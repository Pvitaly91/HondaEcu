//! Closed M2bj composite admission and observation; no instruction semantics.
use super::{
    Access, AuditError, AuditReport, InstructionIdentity, Permissions, ProgramSegment, Result,
    Session, Snapshot, StepOutcome, WriteAccess,
};
use crate::{cpu::Cpu, decoder::Fields};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

pub const COMPOSITE_SHA256: &str =
    "91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1";
const SOURCE: &str = "M2bjVerifiedSyntheticComposite_20Nodes_51Bytes";
const PROVENANCE: &str = "InventedOnly_NoNativeGenerationOwner";
const MANUAL_SHA: &str = "f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271";
pub(crate) const INVENTORY: [u16; 16] = [
    0x108, 0x109, 0x10a, 0x10b, 0x10c, 0x10d, 0x10e, 0x10f, 0x117, 0x124, 0x128, 0x12a, 0x18e,
    0x18f, 0x196, 0x197,
];

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum CompositeForm {
    LbAPage,
    SllbA,
    RolbPage,
    LbAR0,
    AndbAPage,
    CmpPageImm16,
    JltRel8,
    MovbR1Page,
    AndbPageA,
    JbsPageBit7,
    JbsPageBit5,
    OrbPageImm8,
    OrbAImm8,
    LbAImm8,
    StbAPage,
    JAddress,
}
impl CompositeForm {
    fn spec(self) -> (&'static str, &'static [&'static str], char, u16, usize) {
        use CompositeForm::*;
        match self {
            LbAPage => ("LB A, off N8", &["F4", "N8"], 'R', 124, 747),
            SllbA => ("SLLB A", &["53"], '0', 197, 2198),
            RolbPage => ("ROLB off N8", &["C4", "N8", "B7"], 'U', 173, 1862),
            LbAR0 => ("LB A, r0", &["78"], 'R', 124, 739),
            AndbAPage => ("ANDB A, off N8", &["D7", "N8"], '0', 76, 333),
            CmpPageImm16 => (
                "CMP off N8, #N16",
                &["B4", "N8", "C0", "NL", "NH"],
                'U',
                90,
                498,
            ),
            JltRel8 => ("JLT rel8", &["CA", "rel8"], 'U', 120, 719),
            MovbR1Page => ("MOVB r1, off N8", &["C4", "N8", "49"], 'U', 153, 1504),
            AndbPageA => ("ANDB off N8, A", &["C4", "N8", "D1"], 'U', 77, 349),
            JbsPageBit7 => ("JBS off N8.7, rel8", &["EF", "N8", "rel8"], 'U', 119, 716),
            JbsPageBit5 => ("JBS off N8.5, rel8", &["ED", "N8", "rel8"], 'U', 119, 714),
            OrbPageImm8 => (
                "ORB off N'8, #N8",
                &["C4", "N'8", "E0", "N8"],
                'U',
                163,
                1678,
            ),
            OrbAImm8 => ("ORB A, #N8", &["E6", "N8"], '0', 160, 1619),
            LbAImm8 => ("LB A, #N8", &["77", "N8"], 'R', 124, 738),
            StbAPage => ("STB A, off N8", &["D4", "N8"], '0', 208, 2301),
            JAddress => ("J addr16", &["03", "addrl", "addrh"], 'U', 116, 684),
        }
    }
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", content = "value", deny_unknown_fields)]
pub enum CompositeOperand {
    Accumulator,
    LocalRegister(u8),
    Page(u8),
    EvenPage(u8),
    Immediate8(u8),
    Immediate16(u16),
    PageBit { offset: u8, bit: u8 },
    Target(u16),
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CompositeNodeIdentity {
    pub pc: u16,
    pub node_identity: String,
    pub form: CompositeForm,
    pub length: usize,
    pub architectural_dd: Vec<bool>,
    pub reachable_dd: Vec<bool>,
    pub operands: Vec<CompositeOperand>,
    pub successors: Vec<u16>,
    pub primary_pdf_page: u16,
    pub primary_pattern: Vec<String>,
    pub manual_sha256: String,
    pub source_identity: String,
    pub source_sha256: String,
}
impl CompositeNodeIdentity {
    pub(crate) fn instruction(&self, dd: bool) -> InstructionIdentity {
        let mut fields = Fields::default();
        for operand in &self.operands {
            match operand {
                CompositeOperand::Page(n) | CompositeOperand::EvenPage(n) => {
                    if self.form == CompositeForm::OrbPageImm8 {
                        fields.n8_alt = *n;
                    } else {
                        fields.n8 = *n;
                    }
                }
                CompositeOperand::Immediate8(n) => fields.n8 = *n,
                CompositeOperand::Immediate16(n) => fields.n16 = *n,
                CompositeOperand::PageBit { offset, .. } => fields.n8 = *offset,
                CompositeOperand::Target(target) => {
                    if self.form == CompositeForm::JAddress {
                        fields.addr16 = *target;
                    } else {
                        fields.rel8 = i8::try_from(
                            i32::from(*target) - i32::from(self.pc) - self.length as i32,
                        )
                        .expect("fixed reviewed rel8 reach");
                    }
                }
                CompositeOperand::Accumulator | CompositeOperand::LocalRegister(_) => {}
            }
        }
        let (mnemonic, _, mode, _, index) = self.form.spec();
        InstructionIdentity {
            index,
            len: self.length,
            mnemonic: mnemonic.into(),
            dd_before: dd,
            dd_after: (mode == 'R').then_some(false),
            fields,
        }
    }
}

/// Closed typed metadata, not evidence promotion and never a PROGRAM payload.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CompositeEmissionMetadata {
    pub kind: String,
    pub base: u16,
    pub end_exclusive: u16,
    pub source: String,
    pub provenance: String,
    pub content_digest: String,
    pub nodes: Vec<CompositeNodeIdentity>,
}

/// The single accepted PROGRAM content remains private, immutable, and unexported.
pub struct ClosedCompositeProgram {
    segment: ProgramSegment,
    nodes: Vec<CompositeNodeIdentity>,
}
impl ClosedCompositeProgram {
    pub fn admit_emission(
        dd0: Vec<u8>,
        dd1: Vec<u8>,
        metadata: CompositeEmissionMetadata,
    ) -> Result<Self> {
        if metadata.kind != "program"
            || metadata.source != SOURCE
            || metadata.provenance != PROVENANCE
        {
            return Err(AuditError::new(
                "WrongEmissionProvenance",
                None,
                "verified invented M2bj emission only",
            ));
        }
        if metadata.base != 0x1000 || metadata.end_exclusive != 0x1033 {
            return Err(AuditError::new(
                "WrongCompositeMapping",
                None,
                "exact 1000..1033",
            ));
        }
        if dd0.len() != 51 || dd1.len() != 51 {
            return Err(AuditError::new(
                "WrongCompositeLength",
                None,
                "both actual streams must be exactly51 bytes",
            ));
        }
        if metadata.content_digest != COMPOSITE_SHA256
            || crate::audit_sha256::digest(&dd0) != COMPOSITE_SHA256
            || crate::audit_sha256::digest(&dd1) != COMPOSITE_SHA256
        {
            return Err(AuditError::new(
                "WrongCompositeDigest",
                None,
                "actual both-DD content, never a caller label",
            ));
        }
        if dd0 != dd1 {
            return Err(AuditError::new(
                "CompositeDdStreamsDiffer",
                None,
                "full byte equality, not just equal labels",
            ));
        }
        if metadata.nodes != Self::node_inventory() {
            return Err(AuditError::new(
                "CompositeInventoryMismatch",
                None,
                "all20 ordered identities, forms, operands, DD and successors",
            ));
        }
        validate_extents(&dd0, &metadata.nodes)?;
        Ok(Self {
            segment: ProgramSegment::new(0x1000, dd0, COMPOSITE_SHA256)?,
            nodes: metadata.nodes,
        })
    }

    /// Metadata-only fixed inventory. This never emits or returns target bytes.
    pub fn node_inventory() -> Vec<CompositeNodeIdentity> {
        use CompositeForm::*;
        use CompositeOperand::*;
        let rows: Vec<(u16, &str, CompositeForm, Vec<CompositeOperand>, Vec<u16>)> = vec![
            (
                0x1000,
                "556F",
                LbAPage,
                vec![Accumulator, Page(0x8e)],
                vec![0x1002],
            ),
            (0x1002, "5571", SllbA, vec![Accumulator], vec![0x1003]),
            (0x1003, "5572", RolbPage, vec![Page(0x8e)], vec![0x1006]),
            (
                0x1006,
                "5575",
                LbAR0,
                vec![Accumulator, LocalRegister(0)],
                vec![0x1007],
            ),
            (
                0x1007,
                "5576",
                AndbAPage,
                vec![Accumulator, Page(0x8e)],
                vec![0x1009],
            ),
            (
                0x1009,
                "5578",
                CmpPageImm16,
                vec![EvenPage(0x96), Immediate16(0xc0)],
                vec![0x100e],
            ),
            (
                0x100e,
                "557D",
                JltRel8,
                vec![Target(0x102a)],
                vec![0x102a, 0x1010],
            ),
            (
                0x1010,
                "557F",
                MovbR1Page,
                vec![LocalRegister(1), Page(0x17)],
                vec![0x1013],
            ),
            (
                0x1013,
                "5582",
                AndbPageA,
                vec![Page(0x17), Accumulator],
                vec![0x1016],
            ),
            (
                0x1016,
                "5585",
                JbsPageBit7,
                vec![
                    PageBit {
                        offset: 0x2a,
                        bit: 7,
                    },
                    Target(0x1023),
                ],
                vec![0x1023, 0x1019],
            ),
            (
                0x1019,
                "5588",
                JbsPageBit5,
                vec![
                    PageBit {
                        offset: 0x24,
                        bit: 5,
                    },
                    Target(0x1023),
                ],
                vec![0x1023, 0x101c],
            ),
            (
                0x101c,
                "558B",
                AndbPageA,
                vec![Page(0x8f), Accumulator],
                vec![0x101f],
            ),
            (
                0x101f,
                "558E",
                OrbPageImm8,
                vec![Page(0x2a), Immediate8(1)],
                vec![0x1023],
            ),
            (
                0x1023,
                "5592",
                LbAPage,
                vec![Accumulator, Page(0x8f)],
                vec![0x1025],
            ),
            (
                0x1025,
                "5594",
                OrbAImm8,
                vec![Accumulator, Immediate8(0xf0)],
                vec![0x1027],
            ),
            (
                0x1027,
                "DirectJ_NotBelow",
                JAddress,
                vec![Target(0x5596)],
                vec![0x5596],
            ),
            (
                0x102a,
                "55BF",
                LbAImm8,
                vec![Accumulator, Immediate8(0x0f)],
                vec![0x102c],
            ),
            (
                0x102c,
                "55C1",
                StbAPage,
                vec![Accumulator, Page(0x17)],
                vec![0x102e],
            ),
            (
                0x102e,
                "55C3",
                StbAPage,
                vec![Accumulator, Page(0x8f)],
                vec![0x1030],
            ),
            (
                0x1030,
                "DirectJ_Below",
                JAddress,
                vec![Target(0x55c5)],
                vec![0x55c5],
            ),
        ];

        rows.into_iter()
            .map(|(pc, id, form, operands, successors)| {
                let (_, pattern, dd, page, _) = form.spec();
                CompositeNodeIdentity {
                    pc,
                    node_identity: id.into(),
                    form,
                    length: pattern.len(),
                    architectural_dd: if dd == '0' {
                        vec![false]
                    } else {
                        vec![false, true]
                    },
                    reachable_dd: if pc == 0x1000 {
                        vec![false, true]
                    } else {
                        vec![false]
                    },
                    operands,
                    successors,
                    primary_pdf_page: page,
                    primary_pattern: pattern.iter().map(|s| s.to_string()).collect(),
                    manual_sha256: MANUAL_SHA.into(),
                    source_identity: SOURCE.into(),
                    source_sha256: COMPOSITE_SHA256.into(),
                }
            })
            .collect()
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

fn validate_extents(bytes: &[u8], nodes: &[CompositeNodeIdentity]) -> Result<()> {
    let mut cursor = 0usize;
    for node in nodes {
        if usize::from(node.pc - 0x1000) != cursor {
            return Err(AuditError::new(
                "CompositeExtentMismatch",
                Some(i64::from(node.pc)),
                "no gaps or overlap",
            ));
        }
        let identity = node.instruction(false);
        for token in node.form.spec().1 {
            let f = identity.fields;
            let expected = match *token {
                "N8" => f.n8,
                "N'8" => f.n8_alt,
                "NL" => f.n16 as u8,
                "NH" => (f.n16 >> 8) as u8,
                "addrl" => f.addr16 as u8,
                "addrh" => (f.addr16 >> 8) as u8,
                "rel8" => f.rel8 as u8,
                fixed => u8::from_str_radix(fixed, 16).expect("fixed primary token"),
            };
            if bytes.get(cursor) != Some(&expected) {
                return Err(AuditError::new(
                    "CompositeTypedExtentMismatch",
                    Some(i64::from(node.pc)),
                    "actual byte versus frozen primary token/typed operand",
                ));
            }
            cursor += 1;
        }
    }
    if cursor != 51 {
        return Err(AuditError::new(
            "CompositeExtentMismatch",
            None,
            "all51 actual bytes checked",
        ));
    }
    Ok(())
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CompositePath {
    A,
    B,
    C,
    D,
}
impl CompositePath {
    pub(crate) fn pcs(self) -> &'static [u16] {
        match self {
            Self::A => &[
                0x1000, 0x1002, 0x1003, 0x1006, 0x1007, 0x1009, 0x100e, 0x102a, 0x102c, 0x102e,
                0x1030,
            ],
            Self::B => &[
                0x1000, 0x1002, 0x1003, 0x1006, 0x1007, 0x1009, 0x100e, 0x1010, 0x1013, 0x1016,
                0x1023, 0x1025, 0x1027,
            ],
            Self::C => &[
                0x1000, 0x1002, 0x1003, 0x1006, 0x1007, 0x1009, 0x100e, 0x1010, 0x1013, 0x1016,
                0x1019, 0x1023, 0x1025, 0x1027,
            ],
            Self::D => &[
                0x1000, 0x1002, 0x1003, 0x1006, 0x1007, 0x1009, 0x100e, 0x1010, 0x1013, 0x1016,
                0x1019, 0x101c, 0x101f, 0x1023, 0x1025, 0x1027,
            ],
        }
    }
    pub(crate) fn terminal(self) -> u16 {
        if self == Self::A {
            0x55c5
        } else {
            0x5596
        }
    }
}
/// No caller permission object/profile can enter the composite constructor.
#[derive(Debug, Clone)]
pub struct CompositeSeeds {
    data: BTreeMap<u16, u8>,
    pointing: [[u16; 4]; 8],
    path: CompositePath,
}
impl CompositeSeeds {
    pub fn new(
        data: BTreeMap<u16, u8>,
        pointing_banks: [[u16; 4]; 8],
        local_r: [u8; 8],
        local_er: [u16; 4],
    ) -> Result<Self> {
        if data.len() != INVENTORY.len() || INVENTORY.iter().any(|a| !data.contains_key(a)) {
            return Err(AuditError::new(
                "IncompleteCompositeSeeds",
                None,
                "exact sixteen inventoried bytes",
            ));
        }
        if (0..8).any(|n| data[&(0x108 + n as u16)] != local_r[n])
            || (0..4)
                .any(|n| local_er[n] != u16::from_le_bytes([local_r[2 * n], local_r[2 * n + 1]]))
        {
            return Err(AuditError::new(
                "ConflictingCompositeAliases",
                None,
                "explicit r/er aliases must match actual seed bytes",
            ));
        }
        let word = u16::from_le_bytes([data[&0x196], data[&0x197]]);
        let path = if word < 0xc0 {
            CompositePath::A
        } else if data[&0x12a] & 0x80 != 0 {
            CompositePath::B
        } else if data[&0x124] & 0x20 != 0 {
            CompositePath::C
        } else {
            CompositePath::D
        };
        Ok(Self {
            data,
            pointing: pointing_banks,
            path,
        })
    }
    pub fn path(&self) -> CompositePath {
        self.path
    }
    fn permissions(&self) -> Result<Permissions> {
        let read = |address, width| Access { address, width };
        let write = |address, rmw_required| WriteAccess {
            access: read(address, 8),
            rmw_required,
        };
        let mut reads = vec![read(0x108, 8), read(0x18e, 8), read(0x196, 16)];
        let mut writes = vec![
            write(0x18e, true),
            write(0x117, self.path != CompositePath::A),
        ];
        if self.path == CompositePath::A {
            writes.push(write(0x18f, false));
        } else {
            reads.extend([read(0x117, 8), read(0x12a, 8), read(0x18f, 8)]);
            writes.push(write(0x109, false));
            if matches!(self.path, CompositePath::C | CompositePath::D) {
                reads.push(read(0x124, 8));
            }
            if self.path == CompositePath::D {
                writes.extend([write(0x18f, true), write(0x12a, true)]);
            }
        }
        Permissions::new(reads, writes)
    }
}
#[derive(Debug, Clone, Serialize)]
pub struct CompositeStepOutcome {
    pub index: u64,
    pub node_identity: String,
    pub form: CompositeForm,
    pub before: Snapshot,
    pub after: Snapshot,
    pub outcome: StepOutcome,
    pub program_span: [usize; 2],
    pub logical_span: [usize; 2],
    pub raw_span: [usize; 2],
}
#[derive(Debug, Clone, Serialize)]
pub struct CompositeReport {
    pub mode: String,
    pub program_node_count: usize,
    pub path: CompositePath,
    pub entry: Snapshot,
    pub current: Snapshot,
    pub steps: Vec<CompositeStepOutcome>,
    pub direct_j_count: u64,
    pub completed: bool,
    pub audit: AuditReport,
}

pub(crate) struct ClosedState {
    pub(crate) nodes: Vec<CompositeNodeIdentity>,
    pub(crate) path: CompositePath,
    pub(crate) entry: Snapshot,
    pub(crate) steps: Vec<CompositeStepOutcome>,
    pub(crate) direct_j_count: u64,
}
impl ClosedState {
    pub(crate) fn node(&self, pc: u16, dd: bool, retired: u64) -> Result<CompositeNodeIdentity> {
        if self.path.pcs().get(retired as usize) != Some(&pc) {
            return Err(AuditError::new(
                "UnknownCompositeNode",
                Some(i64::from(pc)),
                "actual PC must be the next closed path boundary; no mid-instruction or host jump",
            ));
        }
        let node = self
            .nodes
            .iter()
            .find(|node| node.pc == pc)
            .ok_or_else(|| {
                AuditError::new(
                    "UnknownCompositeNode",
                    Some(i64::from(pc)),
                    "closed20 inventory",
                )
            })?;
        if !node.reachable_dd.contains(&dd) {
            return Err(AuditError::new(
                "WrongIncomingDd",
                Some(i64::from(pc)),
                "actual DD must satisfy the reviewed reachable context",
            ));
        }
        Ok(node.clone())
    }
    pub(crate) fn successor(&self, pc: u16, after: u16, retired: u64) -> Result<bool> {
        let node = self
            .nodes
            .iter()
            .find(|node| node.pc == pc)
            .ok_or_else(|| {
                AuditError::new(
                    "UnknownCompositeNode",
                    Some(i64::from(pc)),
                    "retirement origin",
                )
            })?;
        let terminal = node.form == CompositeForm::JAddress;
        let next = self
            .path
            .pcs()
            .get(retired as usize + 1)
            .copied()
            .unwrap_or(self.path.terminal());
        if self.path.pcs().get(retired as usize) != Some(&pc)
            || !node.successors.contains(&after)
            || after != next
        {
            return Err(AuditError::new(
                "UnknownCompositeSuccessor",
                Some(i64::from(after)),
                "validate actual successor; never assign expected PC",
            ));
        }
        if terminal && (after != self.path.terminal() || self.direct_j_count != 0) {
            return Err(AuditError::new(
                "InvalidCompositeTerminalJ",
                Some(i64::from(after)),
                "one exact actual direct J only",
            ));
        }
        if !terminal && !(0x1000..0x1033).contains(&after) {
            return Err(AuditError::new(
                "NonJCompositeExternalTransfer",
                Some(i64::from(after)),
                "PC alone is not terminal authority",
            ));
        }
        Ok(terminal)
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
            .find(|node| node.pc == pc)
            .ok_or_else(|| {
                AuditError::new(
                    "CompositeDataOutsideInstruction",
                    Some(i64::from(pc)),
                    "closed node",
                )
            })?;
        if !self.path.pcs().contains(&pc) || node.instruction(false).index != index {
            return Err(AuditError::new(
                "CompositeDataInstructionMismatch",
                Some(i64::from(pc)),
                "actual PC and selected form must agree",
            ));
        }
        let (reads, writes, rmw): (&[(u16, u8)], &[(u16, u8)], bool) = match pc {
            0x1000 => (&[(0x18e, 8)], &[], false),
            0x1003 => (&[(0x18e, 8)], &[(0x18e, 8)], true),
            0x1006 => (&[(0x108, 8)], &[], false),
            0x1007 => (&[(0x18e, 8)], &[], false),
            0x1009 => (&[(0x196, 16)], &[], false),
            0x1010 => (&[(0x117, 8)], &[(0x109, 8)], false),
            0x1013 => (&[(0x117, 8)], &[(0x117, 8)], true),
            0x1016 => (&[(0x12a, 8)], &[], false),
            0x1019 => (&[(0x124, 8)], &[], false),
            0x101c => (&[(0x18f, 8)], &[(0x18f, 8)], true),
            0x101f => (&[(0x12a, 8)], &[(0x12a, 8)], true),
            0x1023 => (&[(0x18f, 8)], &[], false),
            0x102c => (&[], &[(0x117, 8)], false),
            0x102e => (&[], &[(0x18f, 8)], false),
            _ => (&[], &[], false),
        };
        if !(if write { writes } else { reads }).contains(&(access.address, access.width)) {
            return Err(AuditError::new(
                if write {
                    "CompositeLogicalWriteDenied"
                } else {
                    "CompositeLogicalReadDenied"
                },
                Some(i64::from(access.address)),
                "closed path/PC/form/width/direction obligation",
            ));
        }
        Ok(write && rmw)
    }
}
impl Session {
    pub fn new_closed_composite(
        program: &ClosedCompositeProgram,
        cpu: Cpu,
        full_psw: u16,
        seeds: CompositeSeeds,
        budget: u8,
    ) -> Result<Self> {
        if cpu.pc != 0x1000 || cpu.lrb != 0x21 || cpu.cycles != 0 || cpu.instructions != 0 {
            return Err(AuditError::new(
                "InvalidCompositeEntry",
                Some(i64::from(cpu.pc)),
                "exact invented PC/LRB and fresh counters; no PC relocation",
            ));
        }
        let permissions = seeds.permissions()?;
        let mut session = Self::new(program.segment_copy(), cpu, full_psw, permissions, budget)?;
        // Exactly one real Bus initialization. Every seed is served once by production DATA.
        for (address, value) in &seeds.data {
            session.seed_byte(*address, *value)?;
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
            .install_closed(ClosedState {
                nodes: program.nodes.clone(),
                path: seeds.path,
                entry,
                steps: vec![],
                direct_j_count: 0,
            })?;
        session.begin_functional()?;
        Ok(session)
    }
    pub fn step_composite(&mut self) -> Result<CompositeStepOutcome> {
        let node = match self
            .bus
            .audit
            .as_ref()
            .expect("installed")
            .closed_node(self.cpu.pc, self.cpu.dd)
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
        let actual = self.checked_step(&node.instruction(self.cpu.dd))?;
        let after = self.diagnostic_snapshot()?;
        self.bus
            .audit
            .as_ref()
            .expect("installed")
            .record_closed_step(node, before, after, actual)
    }
    /// One honest diagnostic snapshot is taken even after a partial fault/exit.
    pub fn composite_report(&mut self) -> Result<CompositeReport> {
        self.bus
            .audit
            .as_ref()
            .expect("installed")
            .require_closed()?;
        let current = self.diagnostic_snapshot()?;
        self.bus
            .audit
            .as_ref()
            .expect("installed")
            .closed_report(current)
    }
}
