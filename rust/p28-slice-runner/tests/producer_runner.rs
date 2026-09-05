//! Newly composed probes. These are not an OEM producer translation or fixture.
use serde_json::{json, Value};
use std::io::Write;
use std::process::{Command, Stdio};

fn custom_program(producer_add: bool, compact_add: bool) -> Vec<u8> {
    let mut rom = vec![0; 32768];
    // Clear A/X1, load one independent input word, optionally exercise the
    // producer assumption, exchange into T and jump to the explicit G exit.
    let mut g = vec![0xF9, 0x50, 0xE0, 0x60, 0x03];
    if producer_add {
        g.extend([0x45, 0x81]);
    }
    g.extend([0xB5, 0xC4, 0x10, 0x03, 0xA5, 0x07]);
    rom[0x0772..0x0772 + g.len()].copy_from_slice(&g);
    // F reads actual RAM left by G, with no reseeding. This intentionally tiny
    // probe is not the production compact arithmetic sequence.
    let mut f = vec![];
    if compact_add {
        f.extend([0x47, 0x81]);
    }
    f.extend([
        0xF5,
        0xC4,
        0xD3,
        0xB3,
        0xCB,
        if compact_add { 0x53 } else { 0x55 },
    ]);
    rom[0x07C7..0x07C7 + f.len()].copy_from_slice(&f);
    rom[0x122C..0x122E].copy_from_slice(&[0xCB, 0x3F]);
    rom
}

fn run(rom: Vec<u8>, cases: Vec<[u32; 14]>, assumptions: &[&str]) -> Value {
    let request = json!({"protocolVersion":1,"operation":"producerBatch",
        "images":[{"id":"baseline","rom":rom}],"allowAssumptions":assumptions,
        "scratchPatterns":[0,85,170],"producerCases":cases});
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

fn input(value: u32) -> [u32; 14] {
    [0, 0, value, 2, 3, 4, 5, 6, 123, 0, 0, 0, 0, 0]
}

#[test]
fn real_subprocess_composition_consumes_producer_written_ram_without_reseeding() {
    let result = run(custom_program(false, false), vec![input(42)], &[]);
    let row = &result["producerRows"][0];
    assert_eq!(row[2], 0);
    assert_eq!(row[5], 42);
    assert_eq!(row[21], 123);
    assert_eq!(row[15], 0);
    assert_eq!(row[18], 42);
    assert_eq!(row[20], 0);
    let changed = run(custom_program(false, false), vec![input(43)], &[]);
    assert_eq!(changed["producerRows"][0][5], 43);
    assert_eq!(changed["producerRows"][0][18], 43);
}

#[test]
fn real_subprocess_assumptions_are_distinct_and_accumulate_across_stages() {
    let strict = run(custom_program(true, true), vec![input(42)], &[]);
    assert_eq!(strict["producerRows"][0][2], 1);
    assert_eq!(strict["producerRows"][0][15], 4);
    assert_eq!(strict["producerThresholdRows"][0][2], 4);
    let unrelated = run(
        custom_program(true, true),
        vec![input(42)],
        &["oki.add-er3-a"],
    );
    assert_eq!(unrelated["producerRows"][0][2], 1);
    let only_g = run(
        custom_program(true, true),
        vec![input(42)],
        &["oki.add-er1-a"],
    );
    assert_eq!(only_g["producerRows"][0][2], 0);
    assert_eq!(only_g["producerRows"][0][14], 1);
    assert_eq!(only_g["producerRows"][0][15], 1);
    assert_eq!(only_g["producerRows"][0][20], 1);
    let both = run(
        custom_program(true, true),
        vec![input(42)],
        &["oki.add-er1-a", "oki.add-er3-a"],
    );
    assert_eq!(both["producerRows"][0][2], 0);
    assert_eq!(both["producerRows"][0][15], 0);
    assert_eq!(both["producerRows"][0][20], 3);
    assert_eq!(both["producerThresholdRows"][0][8], 3);
}

#[test]
fn real_subprocess_unknown_producer_form_is_not_allowed_by_same_mnemonic() {
    let mut rom = custom_program(false, false);
    // CLR er3 is a different form from the audited CLR A / CLR X1.
    rom[0x0772..0x0774].copy_from_slice(&[0x47, 0x15]);
    let result = run(rom, vec![input(42)], &["oki.add-er1-a", "oki.add-er3-a"]);
    assert_eq!(result["producerRows"][0][2], 1);
    assert_eq!(result["producerRows"][0][4], 0);
    assert_eq!(result["producerRows"][0][15], 4);
}

#[test]
fn real_subprocess_fresh_cases_do_not_retain_previous_outputs() {
    let mut next = input(7);
    next[0] = 1;
    next[1] = 170;
    next[8] = 456;
    let result = run(custom_program(false, false), vec![input(42), next], &[]);
    assert_eq!(result["producerRows"][0][18], 42);
    assert_eq!(result["producerRows"][1][18], 7);
    assert_eq!(result["producerRows"][1][21], 456);
}

#[test]
fn producer_protocol_rejects_noncontiguous_cases_and_out_of_domain_inputs() {
    use p28_slice_runner::{protocol::Request, runner::run_request};
    let base = json!({"protocolVersion":1,"operation":"producerBatch",
        "images":[{"id":"baseline","rom":custom_program(false,false)}],"allowAssumptions":[],
        "scratchPatterns":[0,85,170],"producerCases":[input(42)]});
    for (column, invalid) in [
        (0, 1),
        (1, 1),
        (2, 65536),
        (8, 65536),
        (9, 256),
        (10, 256),
        (11, 2),
        (12, 4),
        (13, 2),
    ] {
        let mut malformed = base.clone();
        malformed["producerCases"][0][column] = json!(invalid);
        let request: Request = serde_json::from_value(malformed).unwrap();
        assert!(
            run_request(request).is_err(),
            "column {column} was incorrectly admitted"
        );
    }
    let mut absent = base.clone();
    absent.as_object_mut().unwrap().remove("producerCases");
    assert!(run_request(serde_json::from_value(absent).unwrap()).is_err());
    let mut unknown = base;
    unknown["allowAssumptions"] = json!(["allow-all"]);
    assert!(run_request(serde_json::from_value(unknown).unwrap()).is_err());
}
