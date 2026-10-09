//! GREEN-only exact-cycle predicate audit; no new instruction admission.
use crate::{
    decoder::exact_form_int_cycles,
    full_decoder::{OpcodePattern, FULL_OPCODES},
    operand::{table, Arg, Mem, Reg},
};

#[test]
fn m2au_exact_cycle_override_membership_is_two_of_2623_pinned_patterns() {
    let mut matches = vec![];
    for (index, pattern) in FULL_OPCODES.iter().enumerate() {
        if let Some(cost) = exact_form_int_cycles(pattern, table()[index].as_ref()) {
            matches.push((pattern.mnemonic, pattern.bytes_pat, pattern.dd_mode, cost));
        }
    }
    assert_eq!(FULL_OPCODES.len(), 2623);
    assert_eq!(
        matches,
        [
            ("DEC DP", &["82"][..], 'U', 3),
            ("SLLB off N8", &["C4", "N8", "D7"][..], 'U', 7),
        ]
    );
    println!("M2AU_EXACT_OVERRIDE_MEMBERSHIP visited=2623 admitted_overrides=2 non_targets=2621 primary_verification_claim=false");
}

#[test]
fn m2au_exact_cycle_override_rejects_mode_width_operand_and_identity_lookalikes() {
    let mut rejected = 0;
    for (mnemonic, expected_cost) in [("DEC DP", 3), ("SLLB off N8", 7)] {
        let index = FULL_OPCODES
            .iter()
            .position(|p| p.mnemonic == mnemonic)
            .unwrap();
        let original = &FULL_OPCODES[index];
        let parsed = table()[index].as_ref().unwrap();
        assert_eq!(
            exact_form_int_cycles(original, Some(parsed)),
            Some(expected_cost)
        );
        assert_eq!(exact_form_int_cycles(original, None), None);
        rejected += 1;
        for mode in ['0', '1', 'S', 'R', '?'] {
            let mut p = original.clone();
            p.dd_mode = mode;
            assert_eq!(exact_form_int_cycles(&p, Some(parsed)), None);
            rejected += 1;
        }
        for wrong in [
            &["82", "N8"][..],
            &["C5", "N8", "D7"][..],
            &["80"][..],
            &[][..],
        ] {
            let p = OpcodePattern {
                mnemonic,
                dd_mode: 'U',
                bytes_pat: wrong,
            };
            assert_eq!(exact_form_int_cycles(&p, Some(parsed)), None);
            rejected += 1;
        }
        let mut p = original.clone();
        p.mnemonic = "OTHER DP";
        assert_eq!(exact_form_int_cycles(&p, Some(parsed)), None);
        rejected += 1;
        let mut wrong = parsed.clone();
        wrong.byte_width = !wrong.byte_width;
        assert_eq!(exact_form_int_cycles(original, Some(&wrong)), None);
        rejected += 1;
        wrong = parsed.clone();
        wrong.op = "OTHER";
        assert_eq!(exact_form_int_cycles(original, Some(&wrong)), None);
        rejected += 1;
        for args in [
            vec![],
            vec![Arg::Reg(Reg::X1)],
            vec![Arg::Mem(Mem::Direct)],
            vec![Arg::Mem(Mem::AtReg(Reg::Dp))],
            vec![Arg::R(0)],
            vec![Arg::Reg(Reg::Dp), Arg::ImmN8],
            vec![Arg::Mem(Mem::OffPage), Arg::ImmN8],
        ] {
            wrong = parsed.clone();
            wrong.args = args;
            assert_eq!(exact_form_int_cycles(original, Some(&wrong)), None);
            rejected += 1;
        }
    }
    assert_eq!(rejected, 40);
    println!("M2AU_EXACT_OVERRIDE_LOOKALIKE_REFUSALS vectors={rejected} fail_closed=true");
}
