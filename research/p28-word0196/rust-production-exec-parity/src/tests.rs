//! Pure model/admission tests only. No Cpu, Bus or production step is constructed.
use p28_research_synthetic_adapter::{
    program::{fixture, MicroProgram},
    psw::CanonicalPswBridge,
    sha256, FormId, INVENTED_PROVENANCE,
};

#[test]
fn representable_psw_full_domain_is_pure_classification() {
    let mut count = 0;
    for input in 0_u32..=65535 {
        let input = input as u16;
        assert_eq!(
            CanonicalPswBridge::is_representable(input),
            input & 0x0cc8 == 0x0cc8
        );
        count += usize::from(CanonicalPswBridge::is_representable(input));
    }
    assert_eq!(count, 2048);
}

#[test]
fn frozen_microfixture_rejects_opcode_mutation_without_execution() {
    let guards = [0xa5, 0x5a, 0xa5, 0x5a];
    let bytes = [0xf5, 0x17];
    let content = [0xf5, 0x17, 0xa5, 0x5a, 0xa5, 0x5a];
    let error = MicroProgram::new(
        "lb-page-nonzero",
        FormId::LbAPage,
        &bytes,
        &guards,
        &sha256::digest(&content),
        INVENTED_PROVENANCE,
    )
    .unwrap_err();
    assert_eq!(error.code, "MicrofixtureBindingMismatch");
}

#[test]
fn guards_are_explicit_invented_microfixture_content_not_rom_padding() {
    let (form, instruction) = fixture("direct-j-55c5").unwrap();
    let guards = [0xa5, 0x5a, 0xa5];
    let content = [0x03, 0xc5, 0x55, 0xa5, 0x5a, 0xa5];
    let program = MicroProgram::new(
        "direct-j-55c5",
        form,
        instruction,
        &guards,
        &sha256::digest(&content),
        INVENTED_PROVENANCE,
    )
    .unwrap();
    assert_eq!(program.content(), content);
    assert_eq!(program.instruction_len(), 3);
}

#[test]
fn direct_jump_and_relative_normalization_remain_distinct() {
    let (_, direct) = fixture("direct-j-55c5").unwrap();
    assert_eq!(u16::from_le_bytes([direct[1], direct[2]]), 0x55c5);
    let (_, relative) = fixture("jlt-carry-taken").unwrap();
    let physical = 2_i32 + i32::from(relative[1] as i8);
    assert_eq!(physical, 0);
    assert_eq!(physical + 0x1000, 0x1000);
}
