//! M2bw line-JSON transport only; the closed wrapper reuses production execution.
//! Adds one explicit initial P2/control snapshot; no post-start state import.
//! Never opens a ROM, writes a file, or transfers state between CPU instances.
#![forbid(unsafe_code)]
use p28_slice_runner::{
    audit::{
        self, ClosedPostP2ControlProgram, ControlSnapshot, OriginalRomSourceBinding, P2Snapshot,
        PostP2ControlPath, PostP2ControlSeeds, PostP2ControlSession,
    },
    cpu::Cpu,
};
use serde::{Deserialize, Deserializer};
use serde_json::{json, Value};
use std::{
    collections::BTreeMap,
    io::{self, Read, Write},
};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct PointingBank {
    x1: u16,
    x2: u16,
    dp: u16,
    usp: u16,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct SfDescriptor {
    status: String,
    value: Value,
    meaning: Value,
    storage: Value,
    width_bits: Value,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Entry {
    pc: u16,
    a: u16,
    al: u8,
    ah: u8,
    psw: u16,
    cf: bool,
    zf: bool,
    hc: bool,
    dd: bool,
    other_psw: u16,
    lrb: u16,
    scb: u8,
    ssp: u16,
    pointing_banks: [PointingBank; 8],
    local_r: [u8; 8],
    local_er: [u16; 4],
    halted: bool,
    provenance: String,
    sf: SfDescriptor,
}
fn unique_data<'de, D: Deserializer<'de>>(deserializer: D) -> Result<BTreeMap<u16, u8>, D::Error> {
    struct Visitor;
    impl<'de> serde::de::Visitor<'de> for Visitor {
        type Value = BTreeMap<u16, u8>;
        fn expecting(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
            f.write_str("unique decimal DATA addresses")
        }
        fn visit_map<M: serde::de::MapAccess<'de>>(
            self,
            mut map: M,
        ) -> Result<Self::Value, M::Error> {
            let mut result = BTreeMap::new();
            while let Some((key, value)) = map.next_entry::<String, u8>()? {
                let address = key.parse::<u16>().map_err(serde::de::Error::custom)?;
                if key != address.to_string() || result.insert(address, value).is_some() {
                    return Err(serde::de::Error::custom(
                        "duplicate or noncanonical DATA address",
                    ));
                }
            }
            Ok(result)
        }
    }
    deserializer.deserialize_map(Visitor)
}
#[derive(Deserialize)]
#[serde(tag = "kind", deny_unknown_fields)]
enum Command {
    #[serde(rename = "program", rename_all = "camelCase")]
    Program {
        schema_version: u8,
        source_binding: OriginalRomSourceBinding,
        segment_base: u32,
        segment_bytes: Vec<u8>,
        segment_sha256: String,
    },
    #[serde(rename = "public_fixture", rename_all = "camelCase")]
    PublicFixture { schema_version: u8 },
    #[serde(rename = "case")]
    Case {
        case_id: String,
        family: String,
        entry: Entry,
        #[serde(deserialize_with = "unique_data")]
        data: BTreeMap<u16, u8>,
        path: PostP2ControlPath,
        internal_sf: bool,
        budget: u8,
        p2_snapshot: P2Snapshot,
        control_snapshot: ControlSnapshot,
    },
}
fn error(code: &str, detail: &str) -> audit::AuditError {
    audit::AuditError {
        code: code.into(),
        address: None,
        detail: detail.into(),
    }
}
fn seed_cpu(program: &ClosedPostP2ControlProgram, e: &Entry, sf: bool) -> audit::Result<Cpu> {
    audit::validate_psw(e.psw)?;
    if e.pc != program.entry_pc()
        || e.lrb != 0x21
        || e.scb != (e.psw & 7) as u8
        || e.a != u16::from_le_bytes([e.al, e.ah])
        || e.other_psw != e.psw & 0xfff
        || e.halted
        || e.cf != (e.psw & 0x8000 != 0)
        || e.zf != (e.psw & 0x4000 != 0)
        || e.hc != (e.psw & 0x2000 != 0)
        || e.dd != (e.psw & 0x1000 != 0)
        || e.provenance != "TechnicalSeeded_NoNativeGenerationOwner"
        || e.sf.status != "SFMeaningStorageNotEstablished"
        || !e.sf.value.is_null()
        || !e.sf.meaning.is_null()
        || !e.sf.storage.is_null()
        || !e.sf.width_bits.is_null()
    {
        return Err(error("OriginalCanonicalEntryRejected",
            "explicit canonical technical entry and unknown physical SF required; JSON cannot claim native ownership"));
    }
    Ok(Cpu {
        pc: e.pc,
        a: e.a,
        ssp: e.ssp,
        lrb: e.lrb,
        zf: e.zf,
        cf: e.cf,
        hc: e.hc,
        dd: e.dd,
        sf,
        psw_other: e.psw & 0x0337,
        cycles: 0,
        instructions: 0,
        halted: false,
    })
}
fn execute(program: &ClosedPostP2ControlProgram, command: Command) -> Value {
    let Command::Case {
        case_id,
        family,
        entry,
        data,
        path,
        internal_sf,
        budget,
        p2_snapshot,
        control_snapshot,
    } = command
    else {
        unreachable!()
    };
    let result = (|| {
        if case_id.is_empty() || case_id.len() > 160 || family.len() > 160 {
            return Err(error(
                "CaseIdentityRejected",
                "bounded nonempty case identity",
            ));
        }
        let cpu = seed_cpu(program, &entry, internal_sf)?;
        let banks = std::array::from_fn(|n| {
            let b = &entry.pointing_banks[n];
            [b.x1, b.x2, b.dp, b.usp]
        });
        let seeds = PostP2ControlSeeds::new(program, data, banks, entry.local_r, entry.local_er)?;
        PostP2ControlSession::new(
            program,
            cpu,
            entry.psw,
            seeds,
            path,
            budget,
            p2_snapshot,
            control_snapshot,
        )
    })();
    let mut session = match result {
        Ok(session) => session,
        Err(failure) => {
            return json!({"kind":"post_p2_control_observation","case_id":case_id,"family":family,
            "internal_sf":internal_sf,"accepted":false,"error":failure,"actual_successful_step_returns":0,"report":null})
        }
    };
    let mut successful = 0u64;
    let mut failure = None;
    for _ in 0..budget {
        match session.step() {
            Ok(_) => successful += 1,
            Err(e) => {
                failure = Some(e);
                break;
            }
        }
    }
    match session.report() {
        Ok(report) => {
            json!({"kind":"post_p2_control_observation","case_id":case_id,"family":family,
            "internal_sf":internal_sf,"accepted":failure.is_none()&&report.p2.completed,
            "error":failure,"actual_successful_step_returns":successful,"report":report})
        }
        Err(e) => json!({"kind":"post_p2_control_observation","case_id":case_id,"family":family,
            "internal_sf":internal_sf,"accepted":false,"error":e,"actual_successful_step_returns":successful,"report":null}),
    }
}
fn emit(output: &mut impl Write, record: &Value) -> io::Result<()> {
    serde_json::to_writer(&mut *output, record)?;
    output.write_all(b"\n")?;
    output.flush()
}
fn run() -> Result<(), Box<dyn std::error::Error>> {
    if std::env::args().len() != 1 {
        return Err("no arguments; bounded explicit line-JSON stdin only".into());
    }
    let mut bytes = Vec::new();
    io::stdin()
        .lock()
        .take(2 * 1024 * 1024 + 1)
        .read_to_end(&mut bytes)?;
    if bytes.len() > 2 * 1024 * 1024 {
        return Err("bounded input exceeded".into());
    }
    let input = std::str::from_utf8(&bytes)?;
    let lines: Vec<_> = input.lines().collect();
    if lines.is_empty() || lines.len() > 65 || lines.iter().any(|l| l.is_empty() || l.len() > 65536)
    {
        return Err("one source plus at most64 bounded nonempty case lines".into());
    }
    let mut output = io::stdout().lock();
    let mut program = None;
    let mut ids = std::collections::BTreeSet::new();
    for (ordinal, line) in lines.iter().enumerate() {
        let command: Command = serde_json::from_str(line)?;
        if ordinal == 0 {
            let admitted = match command {
                Command::Program {
                    schema_version: 1,
                    source_binding,
                    segment_base,
                    segment_bytes,
                    segment_sha256,
                } => ClosedPostP2ControlProgram::admit_host_verified_segment(
                    segment_base,
                    segment_bytes,
                    &segment_sha256,
                    source_binding,
                ),
                Command::PublicFixture { schema_version: 1 } => {
                    Ok(ClosedPostP2ControlProgram::explicit_invented_public_fixture())
                }
                _ => Err(error(
                    "OriginalSourceCommandRejected",
                    "one explicit version1 source command before cases",
                )),
            };
            match admitted {
                Ok(p) => {
                    emit(
                        &mut output,
                        &json!({"kind":"program_admitted","schemaVersion":1,
                    "classification":p.classification(),"program_sha256":p.program_sha256(),
                    "entry_pc":p.entry_pc(),"program_node_count":31,"native_generation_ownership":false,
                    "physical_sf_known":false,"hardware_validated":false}),
                    )?;
                    program = Some(p);
                }
                Err(e) => {
                    emit(&mut output, &json!({"kind":"program_refused","error":e}))?;
                    return Ok(());
                }
            }
        } else {
            let Command::Case { ref case_id, .. } = command else {
                return Err("source cannot be replaced midstream".into());
            };
            if !ids.insert(case_id.clone()) {
                return Err("duplicate case identity".into());
            }
            emit(
                &mut output,
                &execute(program.as_ref().expect("admitted source"), command),
            )?;
        }
    }
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("M2bw input/transport refusal: {e}");
        std::process::exit(2);
    }
}
