//! Exact forms already used by the audited M1b/M1d compact slice.
//! M1k narrows its integrated admission; old isolated task policy is unchanged.
use crate::{decoder::Decoded, full_decoder::FULL_OPCODES, instruction_forms::FormAdmission};
pub fn compact_admission(d: &Decoded) -> FormAdmission {
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    match (p.mnemonic, p.dd_mode, p.bytes_pat) {
        ("ADD er3, A", 'U', ["47", "81"]) => {
            FormAdmission::Assumption(crate::protocol::ADD_ASSUMPTION)
        }
        ("L A, N8", 'S', ["E5", "N8"])
        | ("CMP A, #N16", '1', ["C6", "NL", "NH"])
        | ("CMP A, er2", '1', ["4A"])
        | ("MOV er3, #N16", 'U', ["47", "98", "NL", "NH"])
        | ("MOV er0, #N16", 'U', ["44", "98", "NL", "NH"])
        | ("MOV er2, #N16", 'U', ["46", "98", "NL", "NH"])
        | ("MOV X1, #N16", 'U', ["60", "NL", "NH"])
        | ("SRL er0", 'U', ["44", "E7"])
        | ("ROR X1", 'U', ["90", "C7"])
        | ("ADD er3, #N16", 'U', ["47", "80", "NL", "NH"])
        | ("SRL er2", 'U', ["46", "E7"])
        | ("ST A, er2", '1', ["8A"])
        | ("L A, X1", 'S', ["40"])
        | ("DIV", 'U', ["90", "37"])
        | ("SRL A", '1', ["63"])
        | ("MB PSWL.4, C", 'U', ["A3", "3C"])
        | ("LB A, r7", 'R', ["7F"])
        | ("LB A, r6", 'R', ["7E"])
        | ("LB A, #N8", 'R', ["77", "N8"])
        | ("CMPB A, #N8", '0', ["C6", "N8"])
        | ("CLRB A", 'R', ["FA"])
        | ("SB PSWL.4", 'U', ["A3", "1C"])
        | ("RB PSWL.4", 'U', ["A3", "0C"])
        | ("MB C, PSWL.4", 'U', ["A3", "2C"])
        | ("MB N8.4, C", 'U', ["C5", "N8", "3C"])
        | ("STB A, S8[USP]", '0', ["D3", "S8"])
        | ("JBS off N8.4, rel8", 'U', ["EC", "N8", "rel8"])
        | ("JLT rel8", 'U', ["CA", "rel8"])
        | ("JGE rel8", 'U', ["CD", "rel8"])
        | ("JEQ rel8", 'U', ["C9", "rel8"])
        | ("JNE rel8", 'U', ["CE", "rel8"])
        | ("SJ rel8", 'U', ["CB", "rel8"]) => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}
