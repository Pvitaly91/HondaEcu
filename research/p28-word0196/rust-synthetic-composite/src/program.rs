//! The executable boundary admits only the frozen unchanged M2bj emission.
use crate::{AdapterError, Result, BASE, END_EXCLUSIVE};
use p28_research_synthetic_adapter::{
    admission::{ClosedFormAdmission, NodeIdentity, TypedOperand},
    executor::validate_selected_fields,
    sha256, INVENTED_PROVENANCE, UPSTREAM_DIGEST, UPSTREAM_SOURCE,
};
use p28_slice_runner::decoder::Decoded;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EmissionRequest {
    pub kind: String,
    pub base: u16,
    pub end_exclusive: u16,
    pub source: String,
    pub provenance: String,
    pub content_digest: String,
    pub nodes: Vec<NodeIdentity>,
    pub bytes: Vec<u8>,
}

/// Bytes stay private and immutable. There is no path/ROM/backing-memory API.
pub struct VerifiedComposite {
    content: Box<[u8; 51]>,
    nodes: Vec<NodeIdentity>,
}
impl VerifiedComposite {
    pub fn admit_verified_m2bj_emission(request: &EmissionRequest) -> Result<Self> {
        if request.kind != "program"
            || request.source != UPSTREAM_SOURCE
            || request.provenance != INVENTED_PROVENANCE
        {
            return Err(AdapterError::new(
                "WrongEmissionProvenance",
                "M2bj emission only",
            ));
        }
        if request.base != BASE || request.end_exclusive != END_EXCLUSIVE {
            return Err(AdapterError::new("WrongProgramMapping", "exact 1000..1033"));
        }
        if request.bytes.len() != 51 {
            return Err(AdapterError::new("WrongProgramLength", "exact 51 bytes"));
        }
        let actual = sha256::digest(&request.bytes);
        if request.content_digest != UPSTREAM_DIGEST || actual != UPSTREAM_DIGEST {
            return Err(AdapterError::new(
                "WrongCompositeSha",
                "actual bytes, not label",
            ));
        }
        ClosedFormAdmission::validate_inventory(&request.nodes)?;
        validate_all_twenty_extents(request)?;
        let content: [u8; 51] = request.bytes.as_slice().try_into().map_err(|_| {
            AdapterError::new("WrongProgramLength", "exact immutable array conversion")
        })?;
        Ok(Self {
            content: Box::new(content),
            nodes: request.nodes.clone(),
        })
    }
    pub fn read(&self, address: u32) -> Result<u8> {
        let offset = address.checked_sub(u32::from(BASE)).ok_or_else(|| {
            AdapterError::new("ProgramOutOfRange", format!("attempt {address:08X}"))
        })?;
        self.content
            .get(offset as usize)
            .copied()
            .ok_or_else(|| AdapterError::new("ProgramOutOfRange", format!("attempt {address:08X}")))
    }
    pub fn node(&self, pc: u16) -> Result<&NodeIdentity> {
        self.nodes
            .iter()
            .find(|n| n.pc == pc)
            .ok_or_else(|| AdapterError::new("UnknownInstructionBoundary", format!("PC {pc:04X}")))
    }
    pub fn validate_immutable(&self) -> Result<()> {
        if sha256::digest(self.content.as_slice()) != UPSTREAM_DIGEST {
            return Err(AdapterError::new(
                "ProgramChanged",
                "immutable content identity",
            ));
        }
        Ok(())
    }
    /// Full selected bytes are checked only in memory and never serialized.
    pub fn validate_selection(
        &self,
        node: &NodeIdentity,
        decoded: &Decoded,
        dd: bool,
        selected: &[u8],
    ) -> Result<()> {
        ClosedFormAdmission::admit(node, dd)?;
        node.form.validate_decoded(decoded, dd)?;
        validate_selected_fields(node.form, decoded, selected)?;
        if selected.len() != node.length || decoded.len != node.length {
            return Err(AdapterError::new("WrongNodeLength", &node.node_identity));
        }
        let f = decoded.fields;
        for operand in &node.operands {
            let valid = match operand {
                TypedOperand::Page(n) | TypedOperand::EvenPage(n) => {
                    if node.form == p28_research_synthetic_adapter::FormId::OrbPageImm8 {
                        f.n8_alt == *n
                    } else {
                        f.n8 == *n
                    }
                }
                TypedOperand::Immediate8(n) => f.n8 == *n,
                TypedOperand::Immediate16(n) => f.n16 == *n,
                TypedOperand::PageBit { offset, bit } => {
                    f.n8 == *offset
                        && ((*bit == 7
                            && node.form == p28_research_synthetic_adapter::FormId::JbsPageBit7)
                            || (*bit == 5
                                && node.form
                                    == p28_research_synthetic_adapter::FormId::JbsPageBit5))
                }
                TypedOperand::Target(target) => {
                    if node.form == p28_research_synthetic_adapter::FormId::JAddress {
                        f.addr16 == *target
                    } else {
                        i32::from(node.pc) + decoded.len as i32 + i32::from(f.rel8)
                            == i32::from(*target)
                    }
                }
                TypedOperand::Accumulator | TypedOperand::LocalRegister(_) => true,
            };
            if !valid {
                return Err(AdapterError::new(
                    "WrongTypedNodeOperand",
                    &node.node_identity,
                ));
            }
        }
        Ok(())
    }
}

/// Admission checks every actual byte against primary-pattern tokens and closed
/// typed operands. This is validation, not an emitter or a decoder substitute.
/// The executable bytes still come only from the supplied hash-checked M2bj
/// emission; no concatenated expected stream is built or returned.
fn validate_all_twenty_extents(request: &EmissionRequest) -> Result<()> {
    use p28_research_synthetic_adapter::FormId;
    let mut cursor = 0usize;
    for node in &request.nodes {
        if usize::from(node.pc - BASE) != cursor {
            return Err(AdapterError::new(
                "NodeExtentGapOrOverlap",
                &node.node_identity,
            ));
        }
        let page = node.operands.iter().find_map(|p| match p {
            TypedOperand::Page(n) | TypedOperand::EvenPage(n) => Some(*n),
            TypedOperand::PageBit { offset, .. } => Some(*offset),
            _ => None,
        });
        let immediate8 = node.operands.iter().find_map(|p| match p {
            TypedOperand::Immediate8(n) => Some(*n),
            _ => None,
        });
        let immediate16 = node.operands.iter().find_map(|p| match p {
            TypedOperand::Immediate16(n) => Some(*n),
            _ => None,
        });
        let target = node.operands.iter().find_map(|p| match p {
            TypedOperand::Target(n) => Some(*n),
            _ => None,
        });
        for token in node.form.spec().pattern {
            let missing = || AdapterError::new("MissingClosedTypedOperand", &node.node_identity);
            let expected = match *token {
                "N8" => {
                    if matches!(
                        node.form,
                        FormId::OrbPageImm8 | FormId::OrbAImm8 | FormId::LbAImm8
                    ) {
                        immediate8.ok_or_else(missing)?
                    } else {
                        page.ok_or_else(missing)?
                    }
                }
                "N'8" => page.ok_or_else(missing)?,
                "NL" => immediate16.ok_or_else(missing)? as u8,
                "NH" => (immediate16.ok_or_else(missing)? >> 8) as u8,
                "addrl" => target.ok_or_else(missing)? as u8,
                "addrh" => (target.ok_or_else(missing)? >> 8) as u8,
                "rel8" => {
                    let delta = i32::from(target.ok_or_else(missing)?)
                        - i32::from(node.pc)
                        - node.length as i32;
                    i8::try_from(delta)
                        .map_err(|_| AdapterError::new("BranchReach", &node.node_identity))?
                        as u8
                }
                fixed => u8::from_str_radix(fixed, 16)
                    .map_err(|_| AdapterError::new("UnknownPrimaryToken", fixed))?,
            };
            if request.bytes.get(cursor).copied() != Some(expected) {
                return Err(AdapterError::new(
                    "WrongPrimaryTypedExtent",
                    &node.node_identity,
                ));
            }
            cursor += 1;
        }
    }
    if cursor != 51 {
        return Err(AdapterError::new(
            "WrongClosedExtent",
            "all 51 bytes consumed",
        ));
    }
    Ok(())
}
