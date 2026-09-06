//! All instruction programs in this file are newly composed synthetic probes.
//! They are not bytes copied from an OEM ROM or an OEM-derived fixture.
use std::io::Write;
use std::process::{Command, Stdio};

use p28_slice_runner::protocol::{Image, Request, SyntheticContract, ADD_ASSUMPTION};
use p28_slice_runner::runner::run_request;
use serde_json::{json, Value};

fn contract(exit: u16) -> SyntheticContract {
    SyntheticContract {
        entry_pc: 0,
        exit_pcs: vec![exit],
        allowed_code_ranges: vec![[0, exit as u32]],
        psw: 0x0101,
        lrb: 0x40,
        usp: 0x180,
        instruction_budget: 16,
        data_seeds: vec![],
        output_addresses: vec![0xC4],
    }
}

fn request(rom: Vec<u8>, synthetic: SyntheticContract) -> Request {
    Request {
        protocol_version: 1,
        operation: "synthetic".into(),
        images: vec![Image {
            id: "synthetic".into(),
            rom,
        }],
        allow_assumptions: vec![],
        scratch_patterns: vec![0],
        synthetic: Some(synthetic),
        producer_cases: None,
        acquisition_sequence: None,
        stateful_vtec: None,
        integrated_chain: None,
    }
}

fn actual_process(rom: &[u8], contract: &SyntheticContract) -> Value {
    let request = json!({"protocolVersion":1,"operation":"synthetic", "images":[{"id":"synthetic","rom":rom}],
        "allowAssumptions":[],"scratchPatterns":[0],"synthetic":contract});
    let mut child = Command::new(env!("CARGO_BIN_EXE_p28-slice-runner"))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(request.to_string().as_bytes())
        .unwrap();
    let output = child.wait_with_output().unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    serde_json::from_slice(&output.stdout).unwrap()
}

#[test]
fn real_process_executed_opcode_change_changes_status() {
    let original = actual_process(&[0x77, 42, 0xD5, 0xC4], &contract(4));
    assert_eq!(original["syntheticResult"]["status"], 0);
    assert_eq!(original["syntheticResult"]["outputs"], json!([42]));
    // E5 changes the first operation from immediate LB to a word data load
    // from unmodeled SFR 0x002A. This is not an altered expected value.
    let changed = actual_process(&[0xE5, 42, 0xD5, 0xC4], &contract(4));
    assert_eq!(changed["syntheticResult"]["status"], 2);
    assert!(changed["syntheticResult"]["error"]
        .as_str()
        .unwrap()
        .contains("data"));
}

#[test]
fn real_process_program_constant_change_changes_output_not_ram() {
    let mut rom = vec![0; 0x102];
    rom[..7].copy_from_slice(&[0x62, 0, 1, 0x92, 0xA8, 0xD5, 0xC4]);
    rom[0x100] = 42;
    let mut c = contract(7);
    c.data_seeds = vec![[0x100, 99], [0x101, 88]];
    let first = actual_process(&rom, &c);
    assert_eq!(first["syntheticResult"]["status"], 0);
    assert_eq!(first["syntheticResult"]["outputs"], json!([42]));
    assert_eq!(first["syntheticResult"]["programReads"], json!([256, 257]));
    rom[0x100] = 43;
    let second = actual_process(&rom, &c);
    assert_eq!(second["syntheticResult"]["outputs"], json!([43]));
    assert_eq!(second["syntheticResult"]["status"], 0);
}

#[test]
fn strict_stops_before_add_and_conditional_records_actual_reach() {
    let mut c = contract(2);
    c.psw = 0x1101;
    c.data_seeds = vec![[6, 1], [7, 0], [0x206, 2], [0x207, 0]];
    c.output_addresses = vec![0x206, 0x207];
    let strict = run_request(request(vec![0x47, 0x81], c.clone()))
        .unwrap()
        .synthetic_result
        .unwrap();
    assert_eq!((strict.status, strict.stop_pc, strict.steps), (1, 0, 0));
    assert_eq!(strict.outputs, [2, 0]);
    assert!(strict.used_assumptions.is_empty());
    let mut r = request(vec![0x47, 0x81], c);
    r.allow_assumptions.push(ADD_ASSUMPTION.into());
    let conditional = run_request(r).unwrap().synthetic_result.unwrap();
    assert_eq!(
        (conditional.status, conditional.stop_pc, conditional.steps),
        (0, 2, 1)
    );
    assert_eq!(conditional.outputs, [3, 0]);
    assert_eq!(conditional.used_assumptions, [ADD_ASSUMPTION]);
}

#[test]
fn dd_zero_cannot_bypass_word_object_add_assumption_gate() {
    let mut c = contract(2);
    c.psw = 0x0101;
    c.output_addresses = vec![0x206, 0x207];
    c.data_seeds = vec![[6, 1], [7, 0], [0x206, 2], [0x207, 0]];
    let strict = run_request(request(vec![0x47, 0x81], c.clone()))
        .unwrap()
        .synthetic_result
        .unwrap();
    assert_eq!((strict.status, strict.stop_pc, strict.steps), (1, 0, 0));
    let mut r = request(vec![0x47, 0x81], c);
    r.allow_assumptions.push(ADD_ASSUMPTION.into());
    let conditional = run_request(r).unwrap().synthetic_result.unwrap();
    assert_eq!(conditional.status, 0);
    assert_eq!(conditional.outputs, [3, 0]);
    assert_eq!(conditional.used_assumptions, [ADD_ASSUMPTION]);
}

#[test]
fn irrelevant_flag_variants_do_not_leak_through_explicit_output_overwrite() {
    // Independently vary CF/ZF/HC and F0/F1/F2, preserving SCB/MIE/DD.
    for flags in [0, 0xE000, 0x0230, 0xE230] {
        let mut c = contract(4);
        c.psw = 0x0101 | flags;
        let result = run_request(request(vec![0x77, 42, 0xD5, 0xC4], c))
            .unwrap()
            .synthetic_result
            .unwrap();
        assert_eq!(result.status, 0);
        assert_eq!(result.outputs, [42]);
    }
}

#[test]
fn permitted_assumption_is_not_used_if_not_reached() {
    let mut r = request(vec![0x77, 5], contract(2));
    r.allow_assumptions.push(ADD_ASSUMPTION.into());
    let result = run_request(r).unwrap().synthetic_result.unwrap();
    assert_eq!(result.status, 0);
    assert!(result.used_assumptions.is_empty());
}

#[test]
fn assumption_does_not_hide_unimplemented_instruction() {
    let mut r = request(vec![0x00], contract(1)); // NOP outside reviewed slice subset.
    r.allow_assumptions.push(ADD_ASSUMPTION.into());
    let result = run_request(r).unwrap().synthetic_result.unwrap();
    assert_eq!(result.status, 2);
    assert!(result.error.unwrap().contains("unimplemented"));
    assert_eq!(result.steps, 0);
}

#[test]
fn invalid_opcode_and_truncated_instruction_are_explicit_errors() {
    let unknown = run_request(request(vec![0x47, 0xFF], contract(2)))
        .unwrap()
        .synthetic_result
        .unwrap();
    assert_eq!(unknown.status, 2);
    assert!(unknown.error.unwrap().contains("undefined opcode"));
    let truncated = run_request(request(vec![0x77], contract(1)))
        .unwrap()
        .synthetic_result
        .unwrap();
    assert_eq!(truncated.status, 2);
    assert_eq!(truncated.steps, 0);
}

#[test]
fn invalid_data_and_program_accesses_are_errors() {
    let data = run_request(request(vec![0xE5, 8], contract(2)))
        .unwrap()
        .synthetic_result
        .unwrap();
    assert_eq!(data.status, 2);
    assert!(data.error.unwrap().contains("data"));
    let code = run_request(request(vec![0x62, 0xFF, 0xFF, 0x92, 0xA8], contract(5)))
        .unwrap()
        .synthetic_result
        .unwrap();
    assert_eq!(code.status, 2);
    assert!(code.error.unwrap().contains("code"));
}

#[test]
fn success_boundary_stops_before_next_store() {
    let mut c = contract(4);
    c.exit_pcs = vec![2];
    let result = run_request(request(vec![0x77, 42, 0xD5, 0xC4], c))
        .unwrap()
        .synthetic_result
        .unwrap();
    assert_eq!((result.status, result.stop_pc, result.steps), (0, 2, 1));
    assert_eq!(result.outputs, [0]);
}

#[test]
fn instruction_cannot_cross_allowed_boundary() {
    let mut c = contract(2);
    c.allowed_code_ranges = vec![[0, 1]];
    let result = run_request(request(vec![0x77, 42], c))
        .unwrap()
        .synthetic_result
        .unwrap();
    assert_eq!((result.status, result.steps), (2, 0));
}

#[test]
fn budget_and_unexpected_escape_are_not_success() {
    let mut c = contract(2);
    c.instruction_budget = 3;
    let repeated = run_request(request(vec![0xCB, 0xFE], c))
        .unwrap()
        .synthetic_result
        .unwrap();
    assert_eq!(
        (repeated.status, repeated.steps, repeated.stop_pc),
        (3, 3, 0)
    );
    let escape = run_request(request(vec![0xCB, 2], contract(2)))
        .unwrap()
        .synthetic_result
        .unwrap();
    assert_eq!((escape.status, escape.stop_pc), (2, 4));
}

#[test]
fn scratch_state_and_cases_are_reset_deterministically() {
    for scratch in [0, 85, 170] {
        let mut r = request(vec![0x77, 42, 0xD5, 0xC4], contract(4));
        r.scratch_patterns = vec![scratch];
        let first = run_request(r).unwrap().synthetic_result.unwrap();
        assert_eq!(first.outputs, [42]);
        let mut r = request(vec![0x77, 43, 0xD5, 0xC4], contract(4));
        r.scratch_patterns = vec![scratch];
        assert_eq!(
            run_request(r).unwrap().synthetic_result.unwrap().outputs,
            [43]
        );
    }
}

#[test]
fn contradictory_entry_state_and_unknown_permissions_are_rejected() {
    let mut c = contract(2);
    c.data_seeds = vec![[4, 0]];
    assert!(run_request(request(vec![0x77, 42], c)).is_err());
    let mut r = request(vec![0x77, 42], contract(2));
    r.allow_assumptions.push("allow-all".into());
    assert!(run_request(r).is_err());
}

#[test]
fn synthetic_batch_cannot_launder_threshold_add_through_compact_permission() {
    // Newly composed control-flow probes at the public contract locations, not
    // OEM instructions: jump directly to each external exit boundary.
    let mut baseline = vec![0; 32768];
    baseline[0x07C7..0x07C9].copy_from_slice(&[0xCB, 0x59]);
    baseline[0x122C..0x122E].copy_from_slice(&[0xCB, 0x3F]);
    let mut mutated = baseline.clone();
    mutated[0x122C..0x1230].copy_from_slice(&[0x47, 0x81, 0xCB, 0x3D]);
    let result = run_request(Request {
        protocol_version: 1,
        operation: "p28Batch".into(),
        images: vec![
            Image {
                id: "baseline".into(),
                rom: baseline,
            },
            Image {
                id: "derived".into(),
                rom: mutated,
            },
        ],
        allow_assumptions: vec![ADD_ASSUMPTION.into()],
        scratch_patterns: vec![0, 85, 170],
        synthetic: None,
        producer_cases: None,
        acquisition_sequence: None,
        stateful_vtec: None,
        integrated_chain: None,
    })
    .unwrap();
    assert_eq!(result.compact_rows.len(), 393216);
    assert!(result
        .compact_rows
        .iter()
        .all(|row| row[3] == 0 && row[6] == 0));
    assert_eq!(result.threshold_rows.len(), 24576);
    assert!(result
        .threshold_rows
        .iter()
        .filter(|row| row[0] == 0)
        .all(|row| row[6] == 0));
    assert!(result
        .threshold_rows
        .iter()
        .filter(|row| row[0] == 1)
        .all(|row| row[6] == 1 && row[7] == -1));
}
