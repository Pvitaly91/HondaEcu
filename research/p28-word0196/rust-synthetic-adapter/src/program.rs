use crate::{
    admission::FormId, sha256, AdapterError, Result, INVENTED_PROVENANCE, UPSTREAM_DIGEST,
    UPSTREAM_SOURCE,
};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SegmentDescriptor {
    pub base: u32,
    pub end_exclusive: u32,
    pub length: usize,
    pub source_identity: String,
    pub immutable_content_identity: String,
    pub addressing: String,
    pub padding: usize,
}
pub struct SyntheticProgramSegment {
    descriptor: SegmentDescriptor,
    cells: [String; 51],
}
impl SyntheticProgramSegment {
    /// Only opaque strings enter this fifty-one-cell mapping component.
    pub fn new(descriptor: SegmentDescriptor, cells: [String; 51]) -> Result<Self> {
        if descriptor.base != 0x1000
            || descriptor.end_exclusive != 0x1033
            || descriptor.length != 51
            || descriptor.source_identity != UPSTREAM_SOURCE
            || descriptor.immutable_content_identity != UPSTREAM_DIGEST
            || descriptor.addressing != "SubtractBase_NoModulo_NoPadding"
            || descriptor.padding != 0
            || cells
                .iter()
                .enumerate()
                .any(|(n, s)| s != &format!("InventedOpaqueOffsetIdentity-{n}"))
        {
            return Err(AdapterError::new(
                "SegmentIdentityMismatch",
                "fixed geometry, source and opaque canaries required",
            ));
        }
        Ok(Self { descriptor, cells })
    }
    pub fn translate(&self, requested: u32) -> Result<usize> {
        if requested < self.descriptor.base || requested >= self.descriptor.end_exclusive {
            return Err(AdapterError::new(
                "ProgramOutOfRange",
                format!("{requested:X}"),
            ));
        }
        Ok((requested - self.descriptor.base) as usize)
    }
    pub fn read_opaque(&self, requested: u32) -> Result<&str> {
        Ok(&self.cells[self.translate(requested)?])
    }
}

#[derive(Debug, Clone)]
pub struct MicroProgram {
    case_id: String,
    form: FormId,
    bytes: Vec<u8>,
    instruction_len: usize,
    digest: String,
}
impl MicroProgram {
    pub fn new(
        case_id: &str,
        form: FormId,
        instruction: &[u8],
        guards: &[u8],
        claimed_digest: &str,
        provenance: &str,
    ) -> Result<Self> {
        // Reject by shape before accepting content; no full-stream digesting.
        if instruction.is_empty()
            || instruction.len() + guards.len() > 6
            || instruction.len() == 51
            || provenance != INVENTED_PROVENANCE
            || claimed_digest == UPSTREAM_DIGEST
        {
            return Err(AdapterError::new(
                "ForbiddenProgramInput",
                "invented one-instruction fixture, at most six total bytes",
            ));
        }
        let (expected_form, expected) = fixture(case_id).ok_or_else(|| {
            AdapterError::new("UnknownMicrofixture", "sealed invented fixture ID required")
        })?;
        if form != expected_form
            || instruction != expected
            || guards
                .iter()
                .enumerate()
                .any(|(n, &b)| b != if n % 2 == 0 { 0xa5 } else { 0x5a })
        {
            return Err(AdapterError::new(
                "MicrofixtureBindingMismatch",
                "exact sealed bytes/form and explicit alternating opaque guards",
            ));
        }
        let mut bytes = instruction.to_vec();
        bytes.extend_from_slice(guards);
        let digest = sha256::digest(&bytes);
        if digest != claimed_digest {
            return Err(AdapterError::new(
                "WrongContentDigest",
                "immutable actual invented content SHA256",
            ));
        }
        Ok(Self {
            case_id: case_id.into(),
            form,
            bytes,
            instruction_len: instruction.len(),
            digest,
        })
    }
    pub(crate) fn read(&self, pc: u32) -> Result<u8> {
        let end = 0x1000u32
            .checked_add(self.bytes.len() as u32)
            .ok_or_else(|| AdapterError::new("ProgramOverflow", "segment extent"))?;
        if !(0x1000..end).contains(&pc) {
            return Err(AdapterError::new("ProgramOutOfRange", format!("{pc:X}")));
        }
        Ok(self.bytes[(pc - 0x1000) as usize])
    }
    /// Immutable receipt metadata copy, never a functional PROGRAM fetch.
    /// The only functional accessor is crate-private and called by the observer.
    pub fn content(&self) -> &[u8] {
        &self.bytes
    }
    pub fn instruction_len(&self) -> usize {
        self.instruction_len
    }
    pub fn form(&self) -> FormId {
        self.form
    }
    pub fn case_id(&self) -> &str {
        &self.case_id
    }
    pub fn digest(&self) -> &str {
        &self.digest
    }
    /// Deliberately incomplete invented decoder acquisition fixture. This test
    /// constructor is absent from normal builds and cannot enter run_microprobe.
    #[cfg(test)]
    pub(crate) fn truncated_decoder_probe_fixture() -> Self {
        Self {
            case_id: "TruncatedInventedDecoderObservationOnly".into(),
            form: FormId::RolbPage,
            bytes: vec![0xc4],
            instruction_len: 3,
            digest: sha256::digest(&[0xc4]),
        }
    }
}

/// Independently sealed literal fixture bytes only. No composite emitter,
/// concatenation, original-ROM input, file loader or arbitrary opcode interface.
pub fn fixture(id: &str) -> Option<(FormId, &'static [u8])> {
    use FormId::*;
    Some(match id {
        "lb-page-nonzero" | "lb-page-zero-dd1" | "dd1-lb-page" => (LbAPage, &[0xf4, 0x17]),
        "sllb-a-preserve-zf" | "sllb-zero-result-zf-retained-clear" | "sllb-clears-carry" => {
            (SllbA, &[0x53])
        }
        "rolb-page-through-carry"
        | "rolb-no-incoming-carry"
        | "rolb-zero-result-preserves-zf-clear"
        | "rolb-same-value-fresh-write"
        | "dd1-rolb-page" => (RolbPage, &[0xc4, 0x8e, 0xb7]),
        "lb-r0-nonzero" | "lb-r0-zero-dd1" | "dd1-lb-r0" => (LbAR0, &[0x78]),
        "andb-a-page-nonzero" | "andb-a-page-zero-sets-zf" => (AndbAPage, &[0xd7, 0x17]),
        "cmp-page-borrow" | "dd1-cmp-page" => (CmpPageImm16, &[0xb4, 0x96, 0xc0, 0x35, 0x12]),
        "cmp-page-equal" => (CmpPageImm16, &[0xb4, 0x96, 0xc0, 0x34, 0x12]),
        "cmp-page-greater" => (CmpPageImm16, &[0xb4, 0x96, 0xc0, 0x33, 0x12]),
        "jlt-carry-taken" | "jlt-zf-set-carry-clear-dd1" | "dd1-jlt" => (JltRel8, &[0xca, 0xfe]),
        "movb-r1-high-er0" | "movb-same-value-fresh-write" | "dd1-movb-r1" => {
            (MovbR1Page, &[0xc4, 0x17, 0x49])
        }
        "andb-page-a-nonzero"
        | "andb-page-a-zero-sets-zf"
        | "andb-page-a-same-value-fresh-write"
        | "dd1-andb-page-a" => (AndbPageA, &[0xc4, 0x17, 0xd1]),
        "jbs-bit7-taken" | "jbs-bit7-clear" | "dd1-jbs7" => (JbsPageBit7, &[0xef, 0x2a, 0xfd]),
        "jbs-bit5-taken" | "jbs-bit5-clear" | "dd1-jbs5" => (JbsPageBit5, &[0xed, 0x24, 0xfd]),
        "orb-page-imm-nonzero" | "dd1-orb-page" => (OrbPageImm8, &[0xc4, 0x2a, 0xe0, 0x04]),
        "orb-page-zero-sets-zf-same-write" | "orb-page-nonzero-same-write" => {
            (OrbPageImm8, &[0xc4, 0x2a, 0xe0, 0x00])
        }
        "orb-a-imm-nonzero" => (OrbAImm8, &[0xe6, 0x12]),
        "orb-a-zero-sets-zf" => (OrbAImm8, &[0xe6, 0x00]),
        "orb-a-clear-zf" => (OrbAImm8, &[0xe6, 0x04]),
        "lb-imm-zero-dd1" | "dd0-lb-imm" => (LbAImm8, &[0x77, 0x00]),
        "lb-imm-nonzero-dd1" => (LbAImm8, &[0x77, 0x5a]),
        "stb-same-value-fresh-write" => (StbAPage, &[0xd4, 0x8f]),
        "stb-different-byte" => (StbAPage, &[0xd4, 0x17]),
        "direct-j-55c5" | "dd1-j-address" => (JAddress, &[0x03, 0xc5, 0x55]),
        "direct-j-5596-dd1" => (JAddress, &[0x03, 0x96, 0x55]),
        _ => return None,
    })
}
