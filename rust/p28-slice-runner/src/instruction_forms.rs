//! Exact instruction-form admission for the narrow M1e RAM producer.
//! Matching a mnemonic alone is deliberately insufficient. These are opcode
//! patterns, not firmware bytes or a corpus. The decoder already enforces DD.
use crate::decoder::Decoded;
use crate::full_decoder::FULL_OPCODES;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FormAdmission {
    Allowed,
    Assumption(&'static str),
    Unsupported,
}

pub const PRODUCER_ADD_ASSUMPTION: &str = "oki.add-er1-a";

/// Exact M1f forms. Literal operands are checked separately by the scoped
/// execution boundaries/state/read contract; no word object ADD is admitted.
pub fn checksum_form_admission(decoded: &Decoded) -> FormAdmission {
    let Some(p) = FULL_OPCODES.get(decoded.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != decoded.mnemonic || p.bytes_pat.len() != decoded.len {
        return FormAdmission::Unsupported;
    }
    match (p.mnemonic, p.dd_mode, p.bytes_pat) {
        ("CLR X2", 'U', ["91", "15"])
        | ("MOV er0, N16[X2]", 'U', ["B1", "NL", "NH", "48"])
        | ("CLR A", 'S', ["F9"])
        | ("LB A, #N8", 'R', ["77", "N8"])
        | ("MUL", 'U', ["90", "35"])
        | ("MOV X1, A", 'U', ["50"])
        | ("MOV DP, #N16", 'U', ["62", "NL", "NH"])
        | ("MOVB r0, N16[X2]", 'U', ["C1", "NL", "NH", "48"])
        | ("LC A, [X1]", 'U', ["90", "A8"])
        | ("ADDB A, N8", '0', ["C5", "N8", "82"])
        | ("ADDB r0, A", 'U', ["20", "81"])
        | ("INC X1", 'U', ["70"])
        | ("JRNZ DP, rel8", 'U', ["30", "rel8"])
        | ("LB A, r0", 'R', ["78"])
        | ("STB A, N16[X2]", '0', ["D1", "NL", "NH"])
        | ("INC N16[X2]", 'U', ["B1", "NL", "NH", "16"])
        | ("CMP N'16[X2], #N16", 'U', ["B1", "N'L", "N'H", "C0", "NL", "NH"])
        | ("JNE rel8", 'U', ["CE", "rel8"])
        | ("CLR N16[X2]", 'U', ["B1", "NL", "NH", "15"])
        | ("JEQ rel8", 'U', ["C9", "rel8"])
        | ("CLRB N16[X2]", 'U', ["C1", "NL", "NH", "15"])
        | ("LCB A, N16", 'U', ["90", "9D", "NL", "NH"])
        | ("MOVB N'8, #N8", 'U', ["C5", "N'8", "98", "N8"])
        | ("J addr16", 'U', ["03", "addrl", "addrh"]) => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}

pub fn producer_form_admission(decoded: &Decoded) -> FormAdmission {
    let Some(pattern) = FULL_OPCODES.get(decoded.index) else {
        return FormAdmission::Unsupported;
    };
    if pattern.mnemonic != decoded.mnemonic || pattern.bytes_pat.len() != decoded.len {
        return FormAdmission::Unsupported;
    }
    match (pattern.mnemonic, pattern.dd_mode, pattern.bytes_pat) {
        // Same missing primary word obj,A family as M1d, but a DISTINCT form
        // and permission. No er3 permission is inherited here.
        ("ADD er1, A", 'U', ["45", "81"]) => FormAdmission::Assumption(PRODUCER_ADD_ASSUMPTION),
        // Manual printed 3-86, 3-31, 3-85, 3-154.
        ("MOV DP, #N16", 'U', ["62", "NL", "NH"])
        | ("CLR A", 'S', ["F9"])
        | ("MOV X1, A", 'U', ["50"])
        | ("ST A, er0", '1', ["88"])
        | ("ST A, er1", '1', ["89"])
        // Manual printed 3-62, 3-65, 3-66/67, 3-68.
        | ("J addr16", 'U', ["03", "addrl", "addrh"])
        | ("JBS off N8.7, rel8", 'U', ["EF", "N8", "rel8"])
        | ("JEQ rel8", 'U', ["C9", "rel8"])
        | ("JRNZ DP, rel8", 'U', ["30", "rel8"])
        // Manual printed 3-69, 3-12, 3-60, 3-86.
        | ("L A, N16[X1]", 'S', ["E0", "NL", "NH"])
        | ("ADCB r0, #N8", 'U', ["20", "90", "N8"])
        | ("INC X1", 'U', ["70"])
        | ("MOV N'16[X1], #N16", 'U', ["B0", "N'L", "N'H", "98", "NL", "NH"])
        // Manual bit forms 3-114/115, 3-127; their immediate address is
        // off-page data, never a code-space lookup.
        | ("RB off N8.4", 'U', ["C4", "N8", "0C"])
        | ("RB off N8.5", 'U', ["C4", "N8", "0D"])
        | ("SB off N8.5", 'U', ["C4", "N8", "1D"])
        // Manual printed 3-69, 3-86, 3-57, 3-42, 3-32, 3-168.
        | ("L A, er1", 'S', ["35"])
        | ("MOV er2, #N16", 'U', ["46", "98", "NL", "NH"])
        | ("DIV", 'U', ["90", "37"])
        | ("CMPB r0, #N8", 'U', ["20", "C0", "N8"])
        | ("L A, #N16", 'S', ["67", "NL", "NH"])
        | ("CLR X1", 'U', ["90", "15"])
        | ("XCHG A, N8", '1', ["B5", "N8", "10"]) => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::decoder::decode;

    fn admission(bytes: &[u8], dd: bool) -> FormAdmission {
        producer_form_admission(&decode(dd, |i| bytes.get(i).copied().unwrap_or(0)).unwrap())
    }

    #[test]
    fn exact_forms_do_not_admit_other_add_adc_or_width_variants() {
        assert_eq!(
            admission(&[0x45, 0x81], true),
            FormAdmission::Assumption(PRODUCER_ADD_ASSUMPTION)
        );
        assert_eq!(admission(&[0x47, 0x81], true), FormAdmission::Unsupported);
        assert_eq!(admission(&[0x44, 0x81], true), FormAdmission::Unsupported);
        assert_eq!(admission(&[0x20, 0x90, 0], true), FormAdmission::Allowed);
        assert_eq!(
            admission(&[0x21, 0x90, 0], true),
            FormAdmission::Unsupported
        );
        assert_eq!(admission(&[0x20, 0x91], true), FormAdmission::Unsupported);
        assert_eq!(admission(&[0x88], true), FormAdmission::Allowed);
        assert_eq!(admission(&[0x88], false), FormAdmission::Unsupported);
        assert_eq!(admission(&[0xF9], false), FormAdmission::Allowed);
        assert_eq!(admission(&[0xFA], false), FormAdmission::Unsupported);
    }

    #[test]
    fn checksum_registry_has_only_twenty_four_reviewed_exact_forms() {
        let admitted: Vec<_> = FULL_OPCODES
            .iter()
            .enumerate()
            .filter(|(index, pattern)| {
                let decoded = Decoded {
                    index: *index,
                    len: pattern.bytes_pat.len(),
                    mnemonic: pattern.mnemonic,
                    fields: Default::default(),
                    dd_after: None,
                    cycles: 0,
                };
                checksum_form_admission(&decoded) == FormAdmission::Allowed
            })
            .collect();
        assert_eq!(admitted.len(), 24);
        for (bytes, dd, expected) in [
            (&[0x90, 0xA8][..], false, FormAdmission::Allowed),
            (&[0x90, 0xA8][..], true, FormAdmission::Allowed),
            (&[0x92, 0xA8][..], false, FormAdmission::Unsupported),
            (&[0xC5, 7, 0x82][..], false, FormAdmission::Allowed),
            (&[0xC5, 7, 0x82][..], true, FormAdmission::Unsupported),
            (&[0x20, 0x81][..], true, FormAdmission::Allowed),
            (&[0x21, 0x81][..], false, FormAdmission::Unsupported),
            (&[0x45, 0x81][..], false, FormAdmission::Unsupported),
            (&[0x47, 0x81][..], true, FormAdmission::Unsupported),
            (&[0xB1, 0xA2, 3, 0x16][..], true, FormAdmission::Allowed),
            (&[0xB0, 0xA2, 3, 0x16][..], true, FormAdmission::Unsupported),
            (&[0xD1, 0xA0, 3][..], false, FormAdmission::Allowed),
            (&[0xD1, 0xA0, 3][..], true, FormAdmission::Unsupported),
        ] {
            let found = decode(dd, |i| bytes.get(i).copied().unwrap_or(0))
                .map(|decoded| checksum_form_admission(&decoded))
                .unwrap_or(FormAdmission::Unsupported);
            assert_eq!(found, expected, "{:02X?} DD={dd}", bytes);
        }
    }
}
