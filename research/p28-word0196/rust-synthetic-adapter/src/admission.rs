use crate::{AdapterError, Result, MANUAL_SHA, UPSTREAM_DIGEST, UPSTREAM_SOURCE};
use p28_slice_runner::{
    decoder::Decoded,
    full_decoder::FULL_OPCODES,
    operand::{table, Arg, Mem, Reg},
};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum FormId {
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
pub struct FormSpec {
    pub mnemonic: &'static str,
    pub pattern: &'static [&'static str],
    pub dd: char,
    pub args: Vec<Arg>,
    pub pdf_page: u16,
}
impl FormId {
    pub fn spec(self) -> FormSpec {
        use Arg::{Mem as Mm, Reg as Rg};
        let (mnemonic, pattern, dd, args, pdf_page): (&str, &[&str], char, Vec<Arg>, u16) =
            match self {
                Self::LbAPage => (
                    "LB A, off N8",
                    &["F4", "N8"],
                    'R',
                    vec![Rg(Reg::A), Mm(Mem::OffPage)],
                    124,
                ),
                Self::SllbA => ("SLLB A", &["53"], '0', vec![Rg(Reg::A)], 197),
                Self::RolbPage => (
                    "ROLB off N8",
                    &["C4", "N8", "B7"],
                    'U',
                    vec![Mm(Mem::OffPage)],
                    173,
                ),
                Self::LbAR0 => ("LB A, r0", &["78"], 'R', vec![Rg(Reg::A), Arg::R(0)], 124),
                Self::AndbAPage => (
                    "ANDB A, off N8",
                    &["D7", "N8"],
                    '0',
                    vec![Rg(Reg::A), Mm(Mem::OffPage)],
                    76,
                ),
                Self::CmpPageImm16 => (
                    "CMP off N8, #N16",
                    &["B4", "N8", "C0", "NL", "NH"],
                    'U',
                    vec![Mm(Mem::OffPage), Arg::ImmN16],
                    90,
                ),
                Self::JltRel8 => ("JLT rel8", &["CA", "rel8"], 'U', vec![Arg::Rel8], 120),
                Self::MovbR1Page => (
                    "MOVB r1, off N8",
                    &["C4", "N8", "49"],
                    'U',
                    vec![Arg::R(1), Mm(Mem::OffPage)],
                    153,
                ),
                Self::AndbPageA => (
                    "ANDB off N8, A",
                    &["C4", "N8", "D1"],
                    'U',
                    vec![Mm(Mem::OffPage), Rg(Reg::A)],
                    77,
                ),
                Self::JbsPageBit7 => (
                    "JBS off N8.7, rel8",
                    &["EF", "N8", "rel8"],
                    'U',
                    vec![Arg::Bit(Box::new(Mm(Mem::OffPage)), 7), Arg::Rel8],
                    119,
                ),
                Self::JbsPageBit5 => (
                    "JBS off N8.5, rel8",
                    &["ED", "N8", "rel8"],
                    'U',
                    vec![Arg::Bit(Box::new(Mm(Mem::OffPage)), 5), Arg::Rel8],
                    119,
                ),
                Self::OrbPageImm8 => (
                    "ORB off N'8, #N8",
                    &["C4", "N'8", "E0", "N8"],
                    'U',
                    vec![Mm(Mem::OffPageAlt), Arg::ImmN8],
                    163,
                ),
                Self::OrbAImm8 => (
                    "ORB A, #N8",
                    &["E6", "N8"],
                    '0',
                    vec![Rg(Reg::A), Arg::ImmN8],
                    160,
                ),
                Self::LbAImm8 => (
                    "LB A, #N8",
                    &["77", "N8"],
                    'R',
                    vec![Rg(Reg::A), Arg::ImmN8],
                    124,
                ),
                Self::StbAPage => (
                    "STB A, off N8",
                    &["D4", "N8"],
                    '0',
                    vec![Rg(Reg::A), Mm(Mem::OffPage)],
                    208,
                ),
                Self::JAddress => (
                    "J addr16",
                    &["03", "addrl", "addrh"],
                    'U',
                    vec![Arg::Addr16],
                    116,
                ),
            };
        FormSpec {
            mnemonic,
            pattern,
            dd,
            args,
            pdf_page,
        }
    }
    pub fn validate_decoded(self, d: &Decoded, dd: bool) -> Result<()> {
        let expected = self.spec();
        let p = FULL_OPCODES
            .get(d.index)
            .ok_or_else(|| AdapterError::new("WrongPatternIndex", "outside pinned table"))?;
        let parsed = table()
            .get(d.index)
            .and_then(Option::as_ref)
            .ok_or_else(|| {
                AdapterError::new("UnparsedForm", "missing production typed operand identity")
            })?;
        let expected_byte = !matches!(
            self,
            Self::CmpPageImm16
                | Self::JltRel8
                | Self::JbsPageBit7
                | Self::JbsPageBit5
                | Self::JAddress
        );
        let expected_dd_after = if expected.dd == 'R' {
            Some(false)
        } else {
            None
        };
        if p.mnemonic != expected.mnemonic
            || d.mnemonic != p.mnemonic
            || p.bytes_pat != expected.pattern
            || p.dd_mode != expected.dd
            || d.len != expected.pattern.len()
            || parsed.args != expected.args
            || parsed.byte_width != expected_byte
            || d.dd_after != expected_dd_after
            || (expected.dd == '0' && dd)
        {
            return Err(AdapterError::new(
                "WrongExactForm",
                "pattern/index/length/DD/typed operands mismatch",
            ));
        }
        Ok(())
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", content = "value", deny_unknown_fields)]
pub enum TypedOperand {
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
pub struct NodeIdentity {
    pub pc: u16,
    pub node_identity: String,
    pub form: FormId,
    pub length: usize,
    pub architectural_dd: Vec<bool>,
    pub reachable_dd: Vec<bool>,
    pub operands: Vec<TypedOperand>,
    pub successors: Vec<u16>,
    pub primary_pdf_page: u16,
    pub primary_pattern: Vec<String>,
    pub manual_sha256: String,
    pub source_identity: String,
    pub source_sha256: String,
}
pub struct ClosedFormAdmission;
impl ClosedFormAdmission {
    /// Metadata only. This function never emits or joins executable bytes.
    pub fn inventory() -> Vec<NodeIdentity> {
        use FormId::*;
        use TypedOperand::*;
        let rows: Vec<(u16, &str, FormId, Vec<TypedOperand>, Vec<u16>)> = vec![
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
                let spec = form.spec();
                NodeIdentity {
                    pc,
                    node_identity: id.into(),
                    form,
                    length: spec.pattern.len(),
                    architectural_dd: if spec.dd == '0' {
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
                    primary_pdf_page: spec.pdf_page,
                    primary_pattern: spec.pattern.iter().map(|s| s.to_string()).collect(),
                    manual_sha256: MANUAL_SHA.into(),
                    source_identity: UPSTREAM_SOURCE.into(),
                    source_sha256: UPSTREAM_DIGEST.into(),
                }
            })
            .collect()
    }
    pub fn validate_inventory(nodes: &[NodeIdentity]) -> Result<()> {
        if nodes != Self::inventory() {
            return Err(AdapterError::new(
                "ClosedInventoryMismatch",
                "exact twenty ordered review-bound nodes required",
            ));
        }
        Ok(())
    }
    pub fn admit(node: &NodeIdentity, dd: bool) -> Result<()> {
        let expected = Self::inventory()
            .into_iter()
            .find(|n| n.pc == node.pc)
            .ok_or_else(|| AdapterError::new("UnknownSyntheticNode", "closed PC inventory"))?;
        if node != &expected || !expected.reachable_dd.contains(&dd) {
            return Err(AdapterError::new(
                "NodeIdentityMismatch",
                "PC/node/form/operands/length/DD/targets/primary/source",
            ));
        }
        Ok(())
    }
}
