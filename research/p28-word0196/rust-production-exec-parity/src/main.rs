//! Bounded JSONL research protocol. No file/ROM/payload CLI interface exists.
use p28_research_production_exec_parity::{
    admission::{admission_sweep, admit},
    capabilities, execution, source, ProductionProbeRequest, RuntimeTotals,
};
use p28_research_synthetic_adapter::AdapterError;
use serde::Deserialize;
use serde_json::{json, Value};
use std::io::{self, BufRead, Read, Write};

enum Command {
    Case { request: ProductionProbeRequest },
    Admit { request: ProductionProbeRequest },
    AdmissionSweep { request: ProductionProbeRequest },
    Capabilities { request: ProductionProbeRequest },
    Finish,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct CommandEnvelope {
    kind: String,
    #[serde(default)]
    request: RequestField,
}

#[derive(Default)]
enum RequestField {
    #[default]
    Missing,
    Present(ProductionProbeRequest),
}

impl<'de> Deserialize<'de> for RequestField {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        // A present null is not an omitted request. Delegate directly to the
        // native JSON deserializer without materializing Value/Content.
        ProductionProbeRequest::deserialize(deserializer).map(Self::Present)
    }
}

fn parse_command(line: &[u8]) -> std::result::Result<Command, serde_json::Error> {
    // Avoid the old from_value -> internally tagged Command/Content route:
    // serde's Content buffer loses native numeric JSON object-key handling.
    // Value alone supports numeric keys and is not the sole cause. This plain
    // envelope delegates the request directly to the JSON deserializer; closed
    // kind dispatch never changes request fields or instruction semantics.
    let wire: CommandEnvelope = serde_json::from_slice(line)?;
    match (wire.kind.as_str(), wire.request) {
        ("case", RequestField::Present(request)) => Ok(Command::Case { request }),
        ("admit", RequestField::Present(request)) => Ok(Command::Admit { request }),
        ("admission_sweep", RequestField::Present(request)) => {
            Ok(Command::AdmissionSweep { request })
        }
        ("capabilities", RequestField::Present(request)) => Ok(Command::Capabilities { request }),
        ("finish", RequestField::Missing) => Ok(Command::Finish),
        _ => Err(<serde_json::Error as serde::de::Error>::custom(
            "closed command requires a request except finish, which forbids one",
        )),
    }
}

fn emit(value: &impl serde::Serialize, output: &mut impl Write) -> io::Result<()> {
    serde_json::to_writer(&mut *output, value)?;
    output.write_all(b"\n")?;
    output.flush()
}

fn refusal(case_id: Option<&str>, error: &AdapterError) -> Value {
    json!({"kind":"admission_refusal","case_id":case_id,"accepted":false,"error":error,
        "cpu_instances":0,"bus_instances":0,"production_step_calls":0,
        "production_exec_runtime_observed":false,
        "production_bus_composite_integration":"NotEstablished"})
}

fn run() -> std::result::Result<(), Box<dyn std::error::Error>> {
    if std::env::args_os().len() != 1 {
        return Err("No command-line payload/file/ROM arguments are allowed".into());
    }
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut input = stdin.lock();
    let mut output = io::BufWriter::new(stdout.lock());
    let header = source::header()?;
    emit(&header, &mut output)?;
    let mut totals = RuntimeTotals::default();
    let mut sweep_seen = false;
    let mut capabilities_seen = false;
    loop {
        let mut line = Vec::new();
        // At most128KiB per request, enforced while acquiring stdin bytes.
        let read = (&mut input).take(131073).read_until(b'\n', &mut line)?;
        if read == 0 {
            return Err("finish command required; truncated input".into());
        }
        if line.len() > 131072 {
            return Err("bounded request line exceeded128KiB".into());
        }
        let parsed: Value = match serde_json::from_slice(&line) {
            Ok(value) => value,
            Err(error) => {
                totals.admission_refusals += 1;
                emit(
                    &refusal(
                        None,
                        &AdapterError::new("MalformedRequest", error.to_string()),
                    ),
                    &mut output,
                )?;
                continue;
            }
        };
        let case_id = parsed
            .get("request")
            .and_then(|v| v.get("case_id"))
            .and_then(Value::as_str)
            .map(str::to_owned);
        let command = match parse_command(&line) {
            Ok(command) => command,
            Err(error) => {
                totals.admission_refusals += 1;
                emit(
                    &refusal(
                        case_id.as_deref(),
                        &AdapterError::new("MalformedRequest", error.to_string()),
                    ),
                    &mut output,
                )?;
                continue;
            }
        };
        match command {
            Command::Admit { request } => match admit(&request) {
                Ok(_) => emit(
                    &json!({"kind":"admission_result","case_id":request.case_id,"accepted":true,
                    "cpu_instances":0,"bus_instances":0,"production_step_calls":0,
                    "production_exec_runtime_observed":false}),
                    &mut output,
                )?,
                Err(error) => {
                    totals.admission_refusals += 1;
                    emit(&refusal(Some(&request.case_id), &error), &mut output)?;
                }
            },
            Command::AdmissionSweep { request } => {
                if sweep_seen {
                    return Err("admission sweep is one-shot".into());
                }
                let summary = admission_sweep(&request)?;
                sweep_seen = true;
                emit(&summary, &mut output)?;
            }
            Command::Capabilities { request } => {
                if capabilities_seen {
                    return Err("capability observations are one-shot".into());
                }
                let observations = capabilities::observe(&request, &mut totals)?;
                capabilities_seen = true;
                // One command => one reply. The two separately counted records
                // are preserved in full rather than flattened into status bits.
                emit(
                    &json!({"kind":"capability_observations","records":observations}),
                    &mut output,
                )?;
            }
            Command::Case { request } => match admit(&request) {
                Err(error) => {
                    totals.admission_refusals += 1;
                    emit(&refusal(Some(&request.case_id), &error), &mut output)?;
                }
                Ok(_) => {
                    let observation = execution::execute(&request, &mut totals)?;
                    let succeeded = observation.accepted;
                    emit(&observation, &mut output)?;
                    if !succeeded {
                        return Err("Unexpected positive production execution failure; actual state recorded".into());
                    }
                }
            },
            Command::Finish => {
                emit(
                    &json!({"kind":"production_run_summary","totals":totals,
                    "admission_sweep_observed":sweep_seen,"capabilities_observed":capabilities_seen,
                    "production_step_calls":totals.positive_step_calls+totals.capability_step_calls,
                    "cpu_instances":totals.positive_cpu_instances+totals.capability_cpu_instances,
                    "bus_instances":totals.positive_bus_instances+totals.capability_bus_instances,
                    "successful_step_calls":totals.positive_successful_step_calls+totals.capability_successful_step_calls,
                    "failed_step_calls":totals.positive_failed_step_calls+totals.capability_failed_step_calls,
                    "production_exec_architectural_parity":"RequiresIndependentComparator",
                    "production_bus_composite_integration":"NotEstablished",
                    "production_composite_executions":0,"original_rom_executions":0,"firmware_ready":false}),
                    &mut output,
                )?;
                break;
            }
        }
    }
    Ok(())
}

fn main() {
    if let Err(error) = run() {
        eprintln!("M2BO_HARNESS_ERROR={error}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod wire_tests {
    use super::{parse_command, refusal, Command};
    use p28_research_synthetic_adapter::{sha256, AdapterError};
    use serde_json::{json, Value};

    fn explicit_wire() -> Value {
        json!({
            "kind":"admit",
            "request":{
                "case_id":"pure-numeric-data-keys",
                "fixture_id":"lb-page-nonzero",
                "family":"PureWireRegression",
                "form":"lb-a-page",
                "bytes":[244,23],"guards":[165,90,165,90],
                "content_digest":sha256::digest(&[244,23,165,90,165,90]),
                "expected_decoded_index":747,"expected_length":2,
                "entry":{
                    "pc":4096,"a":42369,"al":129,"ah":165,
                    "psw":60619,"cf":true,"zf":true,"hc":true,"dd":false,
                    "other_psw":3275,"lrb":33,"scb":3,"ssp":14241,
                    "pointing_banks":vec![json!({"x1":0,"x2":0,"dp":0,"usp":0});8],
                    "local_r":[60,0,0,0,0,0,0,0],"local_er":[60,0,0,0],
                    "halted":false,"provenance":"InventedOnly_NoNativeGenerationOwner",
                    "sf":{"status":"SFMeaningStorageNotEstablished","value":null,
                        "meaning":null,"storage":null,"width_bits":null}
                },
                "data":{"264":60,"265":0,"266":0,"267":0,"268":0,"269":0,
                    "270":0,"271":0,"279":0,"292":0,"296":0,"298":0,
                    "398":0,"399":0,"406":0,"407":0},
                "internal_sf":false,"physical_entry_pc":0,"scratch":165,"budget":1
            }
        })
    }

    #[test]
    fn nested_numeric_data_keys_use_the_actual_direct_wire_parser() {
        // Pure typed transport/admission only: no Cpu, Bus or step construction.
        let wire = explicit_wire();
        let encoded = serde_json::to_vec(&wire).unwrap();
        match parse_command(&encoded).unwrap() {
            Command::Admit { request } => {
                assert_eq!(request.data.len(), 16);
                assert_eq!(request.data[&264], 60);
                assert_eq!(request.data[&407], 0);
                assert_eq!(request.entry.local_r[0], 60);
                super::admit(&request).unwrap();
            }
            _ => panic!("actual wire command changed"),
        }
        let mut unknown = wire.clone();
        unknown["kind"] = json!("unknown");
        assert!(parse_command(&serde_json::to_vec(&unknown).unwrap()).is_err());
        let mut extra = wire.clone();
        extra["unexpected"] = json!(true);
        assert!(parse_command(&serde_json::to_vec(&extra).unwrap()).is_err());
        let mut finish_with_request = wire;
        finish_with_request["kind"] = json!("finish");
        assert!(parse_command(&serde_json::to_vec(&finish_with_request).unwrap()).is_err());
        assert!(parse_command(br#"{"kind":"finish","request":null}"#).is_err());
        assert!(matches!(
            parse_command(br#"{"kind":"finish"}"#).unwrap(),
            Command::Finish
        ));
    }

    #[test]
    fn refusal_error_wire_uses_code_and_detail_not_message() {
        let actual = refusal(
            Some("pure-refusal-schema"),
            &AdapterError::new("WrongOneStepScope", "frozen detail"),
        );
        assert_eq!(
            actual["error"],
            json!({"code":"WrongOneStepScope","detail":"frozen detail"})
        );
        assert!(actual["error"].get("message").is_none());
        assert_eq!(actual["cpu_instances"], 0);
        assert_eq!(actual["bus_instances"], 0);
        assert_eq!(actual["production_step_calls"], 0);
        assert_eq!(actual["production_exec_runtime_observed"], false);
    }
}
