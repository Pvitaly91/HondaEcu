//! M1j exact ISA forms, not firmware literals. See M1J instruction evidence.
use crate::{decoder::Decoded, full_decoder::FULL_OPCODES, instruction_forms::FormAdmission};
pub const SUBB_OFF_ASSUMPTION: &str = "oki.subb-a-off-n8-encoding";

pub fn admission(d: &Decoded) -> FormAdmission {
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    match (p.mnemonic, p.dd_mode, p.bytes_pat) {
        // Printed 3-156 gives A7 for word off-page; 3-160 byte row instead
        // prints incomplete C4 N8. DD=0 A7 is a documented inference ONLY.
        ("SUBB A, off N8", '0', ["A7", "N8"]) => FormAdmission::Assumption(SUBB_OFF_ASSUMPTION),
        ("LB A, #N8", 'R', ["77", "N8"])
        | ("LB A, r0", 'R', ["78"])
        | ("LB A, r6", 'R', ["7E"])
        | ("LB A, N8", 'R', ["F5", "N8"])
        | ("LB A, off N8", 'R', ["F4", "N8"])
        | ("LB A, N16[X1]", 'R', ["F0", "NL", "NH"])
        | ("L A, off N8", 'S', ["E4", "N8"])
        | ("MOVB r0, #N8", 'U', ["98", "N8"])
        | ("MOVB r0, r1", 'U', ["21", "48"])
        | ("MOVB r6, N8", 'U', ["C5", "N8", "4E"])
        | ("MOVB off N'8, #N8", 'U', ["C4", "N'8", "98", "N8"])
        | ("MOV DP, #N16", 'U', ["62", "NL", "NH"])
        | ("MOV X1, #N16", 'U', ["60", "NL", "NH"])
        | ("LC A, [DP]", 'U', ["92", "A8"])
        | ("LC A, [X1]", 'U', ["90", "A8"])
        | ("LC A, N16[X1]", 'U', ["90", "A9", "NL", "NH"])
        | ("LCB A, N16", 'U', ["90", "9D", "NL", "NH"])
        | ("STB A, off N8", '0', ["D4", "N8"])
        | ("STB A, N8", '0', ["D5", "N8"])
        | ("STB A, r0", '0', ["88"])
        | ("STB A, r1", '0', ["89"])
        | ("STB A, r6", '0', ["8E"])
        | ("STB A, r7", '0', ["8F"])
        | ("CMPB A, N8", '0', ["C5", "N8", "C2"])
        | ("CMPB A, off N8", '0', ["C7", "N8"])
        | ("CMPB N'8, #N8", 'U', ["C5", "N'8", "C0", "N8"])
        | ("CMPCB A, N16[X1]", 'U', ["90", "AF", "NL", "NH"])
        | ("AND A, #N16", '1', ["D6", "NL", "NH"])
        | ("ANDB A, #N8", '0', ["D6", "N8"])
        | ("CLRB A", 'R', ["FA"])
        | ("CLRB off N8", 'U', ["C4", "N8", "15"])
        | ("INC DP", 'U', ["72"])
        | ("INC X1", 'U', ["70"])
        | ("DECB N16[X1]", 'U', ["C0", "NL", "NH", "17"])
        | ("SUBB A, #N8", '0', ["A6", "N8"])
        | ("SUBB A, r1", '0', ["29"])
        | ("SUBB A, r6", '0', ["2E"])
        | ("SUBB A, r7", '0', ["2F"])
        | ("SUBB r0, A", 'U', ["20", "A1"])
        | ("SUBB r6, A", 'U', ["26", "A1"])
        | ("ADDB A, r6", '0', ["0E"])
        | ("ADDB A, #N8", '0', ["86", "N8"])
        | ("MULB", 'U', ["A2", "34"])
        | ("DIVB", 'U', ["A2", "36"])
        | ("CAL addr16", 'U', ["32", "addrl", "addrh"])
        | ("RT", 'U', ["01"])
        | ("J addr16", 'U', ["03", "addrl", "addrh"])
        | ("SJ rel8", 'U', ["CB", "rel8"])
        | ("JNE rel8", 'U', ["CE", "rel8"])
        | ("JEQ rel8", 'U', ["C9", "rel8"])
        | ("JLT rel8", 'U', ["CA", "rel8"])
        | ("JGE rel8", 'U', ["CD", "rel8"])
        | ("JBR off N8.0, rel8", 'U', ["D8", "N8", "rel8"])
        | ("JBR off N8.1, rel8", 'U', ["D9", "N8", "rel8"])
        | ("JBR off N8.2, rel8", 'U', ["DA", "N8", "rel8"])
        | ("JBR off N8.3, rel8", 'U', ["DB", "N8", "rel8"])
        | ("JBR off N8.4, rel8", 'U', ["DC", "N8", "rel8"])
        | ("JBS off N8.0, rel8", 'U', ["E8", "N8", "rel8"])
        | ("JBS off N8.1, rel8", 'U', ["E9", "N8", "rel8"])
        | ("JBS off N8.2, rel8", 'U', ["EA", "N8", "rel8"])
        | ("JBS off N8.3, rel8", 'U', ["EB", "N8", "rel8"])
        | ("JBS off N8.5, rel8", 'U', ["ED", "N8", "rel8"])
        | ("MB off N8.0, C", 'U', ["C4", "N8", "38"])
        | ("MB off N8.1, C", 'U', ["C4", "N8", "39"])
        | ("MB off N8.2, C", 'U', ["C4", "N8", "3A"])
        | ("RB N8.0", 'U', ["C5", "N8", "08"])
        | ("RB N8.1", 'U', ["C5", "N8", "09"])
        | ("SB N8.0", 'U', ["C5", "N8", "18"])
        | ("SB N8.1", 'U', ["C5", "N8", "19"])
        | ("RB off N8.1", 'U', ["C4", "N8", "09"])
        | ("RB off N8.2", 'U', ["C4", "N8", "0A"])
        | ("SB off N8.1", 'U', ["C4", "N8", "19"])
        | ("SB off N8.2", 'U', ["C4", "N8", "1A"]) => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}
