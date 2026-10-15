//! Independently authored integration harness. Expected instruction effects are
//! literal projections of the three sealed pre-result oracle documents.
//! This file has not been compiled or executed by its independent author.

use p28_research_synthetic_adapter::{
    data::DataPath,
    entry::{PointingBank, SyntheticCpuEntrySnapshot},
    psw::CanonicalPswBridge,
    run_microprobe,
    sf::OpaqueSfBoundary,
    sha256, FormId, ProbeRequest, INVENTED_PROVENANCE,
};
use p28_slice_runner::{cpu::Cpu, full_decoder::FULL_OPCODES};
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};

const FIXTURE: &str = include_str!("fixtures/microprobe_expectations.json");

fn h(value: &Value) -> u16 {
    u16::from_str_radix(value.as_str().expect("literal hexadecimal string"), 16)
        .expect("literal u16 hexadecimal")
}

fn form(value: &str) -> FormId {
    match value {
        "lb-a-page" => FormId::LbAPage,
        "sllb-a" => FormId::SllbA,
        "rolb-page" => FormId::RolbPage,
        "lb-a-r0" => FormId::LbAR0,
        "andb-a-page" => FormId::AndbAPage,
        "cmp-page-imm16" => FormId::CmpPageImm16,
        "jlt-rel8" => FormId::JltRel8,
        "movb-r1-page" => FormId::MovbR1Page,
        "andb-page-a" => FormId::AndbPageA,
        "jbs-page-bit7" => FormId::JbsPageBit7,
        "jbs-page-bit5" => FormId::JbsPageBit5,
        "orb-page-imm8" => FormId::OrbPageImm8,
        "orb-a-imm8" => FormId::OrbAImm8,
        "lb-a-imm8" => FormId::LbAImm8,
        "stb-a-page" => FormId::StbAPage,
        "j-address" => FormId::JAddress,
        other => panic!("unreviewed fixture form {other}"),
    }
}

// These manufacturer-reviewed pattern/mnemonic facts are independently literal;
// neither FormId::spec nor a decoder result supplies expected identities.
fn primary_identity(id: &str) -> (&'static str, &'static [&'static str], char) {
    match id {
        "lb-a-page" => ("LB A, off N8", &["F4", "N8"], 'R'),
        "sllb-a" => ("SLLB A", &["53"], '0'),
        "rolb-page" => ("ROLB off N8", &["C4", "N8", "B7"], 'U'),
        "lb-a-r0" => ("LB A, r0", &["78"], 'R'),
        "andb-a-page" => ("ANDB A, off N8", &["D7", "N8"], '0'),
        "cmp-page-imm16" => ("CMP off N8, #N16", &["B4", "N8", "C0", "NL", "NH"], 'U'),
        "jlt-rel8" => ("JLT rel8", &["CA", "rel8"], 'U'),
        "movb-r1-page" => ("MOVB r1, off N8", &["C4", "N8", "49"], 'U'),
        "andb-page-a" => ("ANDB off N8, A", &["C4", "N8", "D1"], 'U'),
        "jbs-page-bit7" => ("JBS off N8.7, rel8", &["EF", "N8", "rel8"], 'U'),
        "jbs-page-bit5" => ("JBS off N8.5, rel8", &["ED", "N8", "rel8"], 'U'),
        "orb-page-imm8" => ("ORB off N'8, #N8", &["C4", "N'8", "E0", "N8"], 'U'),
        "orb-a-imm8" => ("ORB A, #N8", &["E6", "N8"], '0'),
        "lb-a-imm8" => ("LB A, #N8", &["77", "N8"], 'R'),
        "stb-a-page" => ("STB A, off N8", &["D4", "N8"], '0'),
        "j-address" => ("J addr16", &["03", "addrl", "addrh"], 'U'),
        other => panic!("unreviewed identity {other}"),
    }
}

fn apply_state_owners(entry: &mut SyntheticCpuEntrySnapshot, a: u16, psw: u16) {
    entry.a = a;
    entry.al = (a & 255) as u8;
    entry.ah = (a >> 8) as u8;
    entry.psw = psw;
    entry.cf = psw & 0x8000 != 0;
    entry.zf = psw & 0x4000 != 0;
    entry.hc = psw & 0x2000 != 0;
    entry.dd = psw & 0x1000 != 0;
    entry.other_psw = psw & 0x0fff;
    entry.scb = psw & 7;
}

fn apply_local_aliases(entry: &mut SyntheticCpuEntrySnapshot, data: &BTreeMap<u16, u8>) {
    for n in 0..8 {
        entry.local_r[n] = data[&(0x0108 + n as u16)];
    }
    for n in 0..4 {
        entry.local_er[n] = entry.local_r[2 * n] as u16 + 256 * entry.local_r[2 * n + 1] as u16;
    }
}

fn request(fixture: &Value, case: &Value, internal_sf: bool) -> ProbeRequest {
    let common = &fixture["common_entry"];
    let mut data: BTreeMap<u16, u8> = fixture["common_data"]
        .as_object()
        .unwrap()
        .iter()
        .map(|(address, value)| (u16::from_str_radix(address, 16).unwrap(), h(value) as u8))
        .collect();
    for (address, value) in case["dataOverride"].as_object().unwrap() {
        data.insert(u16::from_str_radix(address, 16).unwrap(), h(value) as u8);
    }
    let banks = common["pointingBanks"].as_array().unwrap();
    let mut entry = SyntheticCpuEntrySnapshot {
        pc: h(&common["pc"]),
        a: h(&common["a"]),
        al: h(&common["al"]) as u8,
        ah: h(&common["ah"]) as u8,
        psw: h(&common["psw"]),
        cf: true,
        zf: true,
        hc: true,
        dd: false,
        other_psw: h(&common["otherPsw"]),
        lrb: h(&common["lrb"]),
        scb: common["scb"].as_u64().unwrap() as u16,
        ssp: h(&common["ssp"]),
        pointing_banks: std::array::from_fn(|n| PointingBank {
            x1: h(&banks[n]["X1"]),
            x2: h(&banks[n]["X2"]),
            dp: h(&banks[n]["DP"]),
            usp: h(&banks[n]["USP"]),
        }),
        local_r: [0; 8],
        local_er: [0; 4],
        halted: false,
        provenance: INVENTED_PROVENANCE.into(),
        sf: OpaqueSfBoundary {
            status: "SFMeaningStorageNotEstablished".into(),
            value: None,
            meaning: None,
            storage: None,
            width_bits: None,
        },
    };
    let a = case["entryOverride"].get("a").map(h).unwrap_or(entry.a);
    let psw = case["entryOverride"].get("psw").map(h).unwrap_or(entry.psw);
    apply_state_owners(&mut entry, a, psw);
    apply_local_aliases(&mut entry, &data);
    let bytes: Vec<u8> = case["bytesHex"]
        .as_array()
        .unwrap()
        .iter()
        .map(|v| h(v) as u8)
        .collect();
    assert_eq!(bytes.len(), case["length"].as_u64().unwrap() as usize);
    assert!((1..=5).contains(&bytes.len()));
    let guards: Vec<u8> = (0..6 - bytes.len())
        .map(|n| if n % 2 == 0 { 0xa5 } else { 0x5a })
        .collect();
    let mut content = bytes.clone();
    content.extend_from_slice(&guards);
    let content_digest = sha256::digest(&content);
    ProbeRequest {
        case_id: case["id"].as_str().unwrap().into(),
        form: form(case["form"].as_str().unwrap()),
        bytes,
        guards,
        content_digest,
        entry,
        data,
        path: if form(case["form"].as_str().unwrap()) == FormId::StbAPage {
            DataPath::A
        } else {
            DataPath::D
        },
        internal_sf,
        budget: 1,
    }
}

fn expanded_cases(fixture: &Value) -> Vec<Value> {
    let mut cases: Vec<Value> = fixture["main_cases"]
        .as_array()
        .unwrap()
        .iter()
        .cloned()
        .chain(fixture["control_cases"].as_array().unwrap().iter().cloned())
        .collect();
    for dd in fixture["dd_cases"].as_array().unwrap() {
        let mut case = fixture["main_cases"]
            .as_array()
            .unwrap()
            .iter()
            .find(|base| base["id"] == dd["baseCase"])
            .unwrap()
            .clone();
        case["id"] = dd["id"].clone();
        case["entryOverride"]["psw"] = dd["beforePsw"].clone();
        case["expected"]["psw"] = dd["afterPsw"].clone();
        cases.push(case);
    }
    assert_eq!(cases.len(), 51);
    assert_eq!(
        cases
            .iter()
            .map(|c| c["id"].as_str().unwrap())
            .collect::<BTreeSet<_>>()
            .len(),
        51
    );
    assert_eq!(
        cases
            .iter()
            .map(|c| c["form"].as_str().unwrap())
            .collect::<BTreeSet<_>>()
            .len(),
        16
    );
    cases
}

fn expected_journals(case: &Value) -> (Value, Value) {
    let mut logical = Vec::new();
    let mut raw = Vec::new();
    for read in case["expected"]["reads"].as_array().unwrap() {
        let address = h(&read[0]);
        let constituents: Vec<u8> = read[3]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| h(v) as u8)
            .collect();
        let ordinal = logical.len() + 1;
        for (delta, &value) in constituents.iter().enumerate() {
            raw.push(json!({"ordinal":raw.len()+1,"logical_ordinal":ordinal,
                "address":address+delta as u16,"operation":"Read","value":value}));
        }
        logical.push(
            json!({"ordinal":ordinal,"phase":"ExecutedFunctionalDataAccess",
            "pc":0x1000,"address":address,"width":read[1],"operation":"Read",
            "value":h(&read[2]),"old_value":null,"write_ordinal":null,"kind":null,
            "same_value":false,"constituents":constituents}),
        );
    }
    for write in case["expected"]["writes"].as_array().unwrap() {
        let address = h(&write[0]);
        let value = h(&write[2]);
        let ordinal = logical.len() + 1;
        raw.push(json!({"ordinal":raw.len()+1,"logical_ordinal":ordinal,
            "address":address,"operation":"Write","value":value}));
        logical.push(
            json!({"ordinal":ordinal,"phase":"ExecutedFunctionalDataAccess",
            "pc":0x1000,"address":address,"width":8,"operation":"Write",
            "value":value,"old_value":h(&write[1]),"write_ordinal":write[3],"kind":write[4],
            "same_value":write[5],"constituents":[value]}),
        );
    }
    (json!(logical), json!(raw))
}

fn compare_observation(request: &ProbeRequest, case: &Value, actual: &Value) -> Result<(), String> {
    let check = |field: &str, expected: Value| -> Result<(), String> {
        if actual[field] == expected {
            Ok(())
        } else {
            Err(format!(
                "{} sf={}: field {} expected {} actual {}",
                request.case_id, request.internal_sf, field, expected, actual[field]
            ))
        }
    };
    check("before", json!(request.entry))?;
    check("before_data", json!(request.data))?;
    let mut expected_entry = request.entry.clone();
    apply_state_owners(
        &mut expected_entry,
        h(&case["expected"]["a"]),
        h(&case["expected"]["psw"]),
    );
    expected_entry.pc = h(&case["expected"]["pc"]);
    let mut expected_data = request.data.clone();
    for write in case["expected"]["writes"].as_array().unwrap() {
        expected_data.insert(h(&write[0]), h(&write[2]) as u8);
    }
    apply_local_aliases(&mut expected_entry, &expected_data);
    check("after", json!(expected_entry))?;
    check("after_data", json!(expected_data))?;
    let (logical, raw) = expected_journals(case);
    check("data_journal", logical)?;
    check("raw_data_journal", raw)?;
    check("selected_bytes", json!(request.bytes))?;
    check("case_id", json!(request.case_id))?;
    check("provenance", json!(INVENTED_PROVENANCE))?;
    check("retired_instructions", json!(1))?;
    check("cpu_instances", json!(1))?;
    check("instructions", json!(1))?;
    check("production_exec_integrated", json!(false))?;
    check("m2bj_composite_executions", json!(0))?;
    check("original_rom_executions", json!(0))?;
    check("first_mismatch", Value::Null)?;
    check("internal_sf_before", json!(request.internal_sf))?;
    check("internal_sf_after", json!(request.internal_sf))?;
    check("branch_taken", case["expected"]["branchTaken"].clone())?;
    check(
        "external_transfer",
        if case["expected"]["external"] == true {
            json!(h(&case["expected"]["pc"]))
        } else {
            Value::Null
        },
    )?;

    let (mnemonic, pattern, dd_mode) = primary_identity(case["form"].as_str().unwrap());
    let decode = &actual["decode"];
    if decode["form"] != case["form"]
        || decode["mnemonic"] != mnemonic
        || decode["len"] != request.bytes.len()
        || decode["dd_before"] != request.entry.dd
        || decode["dd_after"] != expected_entry.dd
    {
        return Err(format!(
            "{} exact decoded identity mismatch: {}",
            request.case_id, decode
        ));
    }
    let mut fields = json!({"n8":0,"n8_alt":0,"n16":0,"addr16":0,"rel8":0});
    let bytes = &request.bytes;
    match case["form"].as_str().unwrap() {
        "lb-a-page" | "andb-a-page" | "orb-a-imm8" | "lb-a-imm8" | "stb-a-page" | "rolb-page"
        | "movb-r1-page" | "andb-page-a" => fields["n8"] = json!(bytes[1]),
        "cmp-page-imm16" => {
            fields["n8"] = json!(bytes[1]);
            fields["n16"] = json!(bytes[3] as u16 + 256 * bytes[4] as u16);
        }
        "jlt-rel8" => fields["rel8"] = json!(bytes[1] as i8),
        "jbs-page-bit7" | "jbs-page-bit5" => {
            fields["n8"] = json!(bytes[1]);
            fields["rel8"] = json!(bytes[2] as i8);
        }
        "orb-page-imm8" => {
            fields["n8_alt"] = json!(bytes[1]);
            fields["n8"] = json!(bytes[3]);
        }
        "j-address" => fields["addr16"] = json!(bytes[1] as u16 + 256 * bytes[2] as u16),
        "sllb-a" | "lb-a-r0" => {}
        _ => unreachable!(),
    }
    for (name, value) in fields.as_object().unwrap() {
        if decode[name] != *value {
            return Err(format!(
                "{} decoded typed field {name} mismatch",
                request.case_id
            ));
        }
    }
    let index = decode["index"]
        .as_u64()
        .ok_or("missing actual decoder index")? as usize;
    let observed_pattern = FULL_OPCODES
        .get(index)
        .ok_or("actual decoder index out of bounds")?;
    if observed_pattern.mnemonic != mnemonic
        || observed_pattern.bytes_pat != pattern
        || observed_pattern.dd_mode != dd_mode
    {
        return Err(format!(
            "{} actual decoder index did not identify reviewed primary pattern",
            request.case_id
        ));
    }

    let mut content = request.bytes.clone();
    content.extend_from_slice(&request.guards);
    check("all_program_bytes", json!(content))?;
    check("immutable_content_digest", json!(request.content_digest))?;
    check(
        "retirements",
        json!([{"ordinal":1,"pc":0x1000,
        "next_pc":h(&case["expected"]["pc"]),"form":case["form"],
        "external_transfer":case["expected"]["external"]}]),
    )?;
    let probes = actual["raw_program"]
        .as_array()
        .ok_or("missing actual PROGRAM ledger")?;
    if probes.is_empty() {
        return Err("missing actual PROGRAM acquisitions".into());
    }
    let mut selected = Vec::new();
    let mut decoder_reads = 0;
    let mut reached_selected_phase = false;
    for (i, event) in probes.iter().enumerate() {
        let offset = event["offset"]
            .as_u64()
            .ok_or("missing actual PROGRAM offset")? as usize;
        if event["ordinal"] != i + 1
            || event["address"] != 0x1000 + offset
            || offset >= content.len()
            || event["value"] != content[offset]
            || !event["fault"].is_null()
        {
            return Err(format!(
                "{} PROGRAM translation/value/order/fault mismatch: {}",
                request.case_id, event
            ));
        }
        match event["acquired_purpose"].as_str() {
            Some("DecoderProbe") => {
                if reached_selected_phase {
                    return Err("decoder probe after selected acquisition phase".into());
                }
                let expected_purpose = if offset < request.bytes.len() {
                    "DecoderProbe"
                } else {
                    "DecoderLookahead"
                };
                if event["purpose"] != expected_purpose {
                    return Err("decoder/lookahead misclassification".into());
                }
                if decoder_reads == 0 && offset != 0 {
                    return Err("first decoder callback was not offset0".into());
                }
                decoder_reads += 1;
            }
            Some("ArchitecturalSelectedFetch") => {
                reached_selected_phase = true;
                if event["purpose"] != "ArchitecturalSelectedFetch" || offset >= request.bytes.len()
                {
                    return Err("architectural selected fetch classification mismatch".into());
                }
                selected.push(offset);
            }
            _ => return Err(format!("unexpected raw PROGRAM acquisition: {}", event)),
        }
    }
    if decoder_reads == 0 || selected != (0..request.bytes.len()).collect::<Vec<_>>() {
        return Err(format!(
            "{} missing/extra selected PROGRAM read or decoder probe",
            request.case_id
        ));
    }
    for (field, phase) in [
        ("seed_journal", "SeedInitializationAccess"),
        ("diagnostic_journal", "DiagnosticSnapshotRead"),
    ] {
        let journal = actual[field]
            .as_array()
            .ok_or_else(|| format!("missing {field}"))?;
        if journal.is_empty() || journal.iter().any(|event| event["phase"] != phase) {
            return Err(format!(
                "{} auxiliary phase mixing in {}",
                request.case_id, field
            ));
        }
    }
    let mut expected_seeds = Vec::new();
    for (&address, &value) in &request.data {
        expected_seeds.push(json!({"ordinal":expected_seeds.len()+1,
            "phase":"SeedInitializationAccess","address":address,"width":8,"value":value}));
    }
    for (bank, values) in request.entry.pointing_banks.iter().enumerate() {
        for (slot, value) in [values.x1, values.x2, values.dp, values.usp]
            .into_iter()
            .enumerate()
        {
            expected_seeds.push(json!({"ordinal":expected_seeds.len()+1,
                "phase":"SeedInitializationAccess","address":0x80+bank*8+slot*2,
                "width":16,"value":value}));
        }
    }
    check("seed_journal", json!(expected_seeds))?;
    let bindings = actual["source_bindings"]
        .as_array()
        .ok_or("missing observed source bindings")?;
    for binding in [
        json!({"path":"cpu.rs","bytes":5281,"sha256":"b12a0b3388a7d34201888a0a6f948263dcf1c7bebca1801056e176d871184d3b"}),
        json!({"path":"decoder.rs","bytes":9735,"sha256":"1120cc37cee9ec23f1f596c72ff8dd5bf372204495d2b5e00cc044dfe2ea3aa4"}),
        json!({"path":"full_decoder.rs","bytes":240468,"sha256":"77697d4b0e3c90372326156bf1a8544486d07f4aa8f93c67cf9e5f2af6c7eff1"}),
    ] {
        if !bindings.contains(&binding) {
            return Err("missing immutable upstream source identity".into());
        }
    }
    Ok(())
}

#[test]
fn independent_presealed_runtime_corpus_and_exhaustive_psw() {
    let fixture: Value = serde_json::from_str(FIXTURE).expect("closed presealed fixture JSON");
    let cases = expanded_cases(&fixture);
    let mut observations = Vec::new();
    let mut refusals = Vec::new();
    let mut psw_records = Vec::new();
    let mut first_mismatch: Option<String> = None;
    let mut positive_instances = 0_u64;
    let mut positive_retirements = 0_u64;

    'positive: for case in &cases {
        let mut sf_observations: Vec<Value> = Vec::new();
        for internal_sf in [false, true] {
            let request = request(&fixture, case, internal_sf);
            let request_before = serde_json::to_value(&request).unwrap();
            match run_microprobe(&request) {
                Ok(observation) => {
                    let actual = serde_json::to_value(&observation).unwrap();
                    positive_instances += actual["cpu_instances"].as_u64().unwrap_or(0);
                    positive_retirements += actual["retired_instructions"].as_u64().unwrap_or(0);
                    let comparison = compare_observation(&request, case, &actual);
                    observations.push(json!({"case_id":request.case_id,"internal_sf":internal_sf,
                        "request":request_before,"actual":actual,
                        "comparison":if comparison.is_ok(){"Pass"}else{"Mismatch"}}));
                    if request_before != serde_json::to_value(&request).unwrap() {
                        first_mismatch = Some("caller request mutated during microprobe".into());
                        break 'positive;
                    }
                    if let Err(error) = comparison {
                        first_mismatch = Some(error);
                        break 'positive;
                    }
                    sf_observations.push(serde_json::to_value(&observation).unwrap());
                }
                Err(error) => {
                    first_mismatch = Some(format!(
                        "{} sf={internal_sf} unexpected refusal {error}",
                        request.case_id
                    ));
                    observations.push(json!({"case_id":request.case_id,"internal_sf":internal_sf,
                        "request":request_before,"actual_error":error,"comparison":"Mismatch"}));
                    break 'positive;
                }
            }
        }
        for actual in &mut sf_observations {
            actual.as_object_mut().unwrap().remove("internal_sf_before");
            actual.as_object_mut().unwrap().remove("internal_sf_after");
        }
        if sf_observations[0] != sf_observations[1] {
            first_mismatch = Some(format!("{} behavior depends on internal SF", case["id"]));
            break;
        }
    }

    if first_mismatch.is_none() {
        for negative in fixture["dd_refusals"].as_array().unwrap() {
            let mut case = cases
                .iter()
                .find(|c| c["id"] == negative["baseCase"])
                .unwrap()
                .clone();
            case["entryOverride"]["psw"] = negative["beforePsw"].clone();
            let request = request(&fixture, &case, false);
            let before = serde_json::to_value(&request).unwrap();
            let result = run_microprobe(&request);
            let unchanged = before == serde_json::to_value(&request).unwrap();
            match result {
                Err(error) if error.code == "WrongDdAdmission" && unchanged => {
                    refusals.push(json!({
                    "base_case":negative["baseCase"],"request":before,"actual_refusal":error,
                    "caller_request_unchanged":unchanged,"comparison":"Pass"}))
                }
                other => {
                    first_mismatch = Some(format!("DD1 refusal failed: {other:?}"));
                    break;
                }
            }
        }
    }

    let mut representable_full = 0_u64;
    let mut representable_low12 = 0_u64;
    let mut psw_cpu_instances = 0_u64;
    let mut psw_observe_raw_calls = 0_u64;
    let mut psw_checked_calls = 0_u64;
    let mut psw_retired_instructions = 0_u64;
    if first_mismatch.is_none() {
        for input in 0_u32..=65535 {
            let input = input as u16;
            // Explicit fields; this PSW probe does not pretend Cpu::new defaults
            // are a complete independent architectural entry snapshot.
            let mut cpu = Cpu {
                pc: 0x1000,
                a: 0xa581,
                ssp: 0x37a1,
                lrb: 0x21,
                zf: true,
                cf: true,
                hc: true,
                dd: false,
                sf: true,
                psw_other: 0x0003,
                cycles: 17,
                instructions: 23,
                halted: false,
            };
            psw_cpu_instances += 1;
            let observed = CanonicalPswBridge::observe_raw(&mut cpu, input);
            psw_observe_raw_calls += 1;
            psw_retired_instructions += cpu.instructions.saturating_sub(23);
            let expected = (input & 0xf000) | (input & 0x0337) | 0x0cc8;
            let compatible = input & 0x0cc8 == 0x0cc8;
            let classification = if compatible {
                "Representable"
            } else {
                "NotRepresentableByCurrentCanonicalRustCpu"
            };
            psw_records.push(json!([input, observed.canonical_observed]));
            if observed.original_expected != input
                || observed.canonical_observed != expected
                || observed.representable != compatible
                || observed.classification != classification
                || cpu.cf != (input & 0x8000 != 0)
                || cpu.zf != (input & 0x4000 != 0)
                || cpu.hc != (input & 0x2000 != 0)
                || cpu.dd != (input & 0x1000 != 0)
                || cpu.psw_other != input & 0x0337
                || !cpu.sf
                || cpu.pc != 0x1000
                || cpu.a != 0xa581
                || cpu.ssp != 0x37a1
                || cpu.lrb != 0x21
                || cpu.cycles != 17
                || cpu.instructions != 23
                || cpu.halted
            {
                first_mismatch = Some(format!(
                    "PSW word {input:04X} independent round-trip mismatch"
                ));
                break;
            }
            representable_full += compatible as u64;
            if input < 4096 {
                representable_low12 += compatible as u64;
            }
            let before = format!("{cpu:?}");
            let checked = CanonicalPswBridge::set_checked(&mut cpu, input);
            psw_checked_calls += 1;
            if compatible {
                if checked.is_err() || cpu.psw_u16() != input {
                    first_mismatch =
                        Some(format!("PSW word {input:04X} compatible Route A refused"));
                    break;
                }
            } else if checked.is_ok() || format!("{cpu:?}") != before {
                first_mismatch = Some(format!(
                    "PSW word {input:04X} incompatible Route A mutated state"
                ));
                break;
            }
        }
    }
    if first_mismatch.is_none()
        && (positive_instances != 102
            || positive_retirements != 102
            || observations.len() != 102
            || refusals.len() != 4
            || psw_records.len() != 65536
            || representable_full != 2048
            || representable_low12 != 128
            || psw_cpu_instances != 65536
            || psw_observe_raw_calls != 65536
            || psw_checked_calls != 65536
            || psw_retired_instructions != 0)
    {
        first_mismatch = Some("independent runtime corpus accounting mismatch".into());
    }
    let receipt = json!({
        "schema_version":1,"classification":"IndependentPresealedRuntimeComparison",
        "oracle_seals":fixture["oracle_seals"],
        "oracle_fixture_sha256":sha256::digest(FIXTURE.as_bytes()),
        "positive_microprobe_contexts":cases.len(),"positive_cpu_instances":positive_instances,
        "positive_retired_instructions":positive_retirements,"microprobe_observations":observations,
        "wrong_dd_refusals":refusals,"psw_record_fields":["lossless_input_u16","actual_canonical_output_u16"],
        "psw_round_trip_records":psw_records,
        "psw_inputs_observed":psw_records.len(),"psw_cpu_instances":psw_cpu_instances,
        "psw_observe_raw_calls":psw_observe_raw_calls,"psw_checked_calls":psw_checked_calls,
        "psw_retired_instructions":psw_retired_instructions,"psw_representable_low12":representable_low12,
        "psw_incompatible_low12":if psw_records.len()>=4096 {4096-representable_low12}else{0},
        "psw_representable_full":representable_full,
        "psw_incompatible_full":psw_records.len() as u64-representable_full,
        "sf_status":"SFMeaningStorageNotEstablished",
        "sf_runtime_comparison":"PairedInternalBooleanVariantsOnly_NoNativeBooleanClaim",
        "m2bj_composite_executions":0,"original_rom_executions":0,"firmware_ready":false,
        "first_mismatch":first_mismatch
    });
    println!(
        "\nM2BM_RUNTIME_JSON={}",
        serde_json::to_string(&receipt).unwrap()
    );
    assert!(
        first_mismatch.is_none(),
        "{}",
        first_mismatch.unwrap_or_default()
    );
}
