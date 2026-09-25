//! M2i: one-machine ignition prefix followed by a scripted entry to the
//! bounded, software-only correction path. No timer/coil/IRQ is executed.
use crate::{
    acquisition::enter,
    adaptive::Stage,
    bus::Bus,
    cpu::Cpu,
    decoder::Decoded,
    exec::{read_data_u16, read_data_u8, write_data_u8},
    full_decoder::FULL_OPCODES,
    ignition, ignition_selector,
    instruction_forms::FormAdmission,
    protocol::{Request, Response},
    runner::{execute_in_state_observed, seed_machine, SliceContract},
    vtec_fuel::{boundary, CpuBoundary},
};
use serde::{Deserialize, Serialize};

const NOT_RUN: i32 = 4;

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Initial {
    pub ignition: ignition::State,
    pub source03c7: u8,
    pub floor024c: u8,
    pub bias0249: u8,
    pub retained035b: u8,
    pub retained024a: u8,
    pub gate0234_bit5: bool,
    pub gate0217_bit0: bool,
    pub gate021e_bit0: bool,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Call {
    pub index: u32,
    pub source03c7: u8,
    pub raw_load: u8,
    pub raw_map0_rpm: u8,
    pub raw_map1_rpm: u8,
    pub correction0245: u8,
    pub correction0246: u8,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Stimulus {
    pub format_version: u32,
    pub initial: Initial,
    pub calls: Vec<Call>,
    pub trace_call_indexes: Vec<u32>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Checkpoint {
    pub index: u32,
    pub status: i32,
    pub conditional_dependency: bool,
    pub input: Option<Call>,
    pub state_before: ignition::State,
    pub state_after: ignition::State,
    pub retained035b_before: u8,
    pub retained024a_before: u8,
    pub producer: Option<Stage>,
    pub axes: Option<Stage>,
    pub selection: Option<Stage>,
    pub lookup: Option<Stage>,
    pub consumer: Option<Stage>,
    pub selected_origin: Option<u16>,
    pub lookup_result: Option<u8>,
    pub data0248: Option<u8>,
    pub correction_mode0207_bit7: Option<bool>,
    pub consumer_exit: Option<CpuBoundary>,
    pub correction_entry: Option<CpuBoundary>,
    pub correction: Option<Stage>,
    pub native_read0248: Option<u8>,
    pub corrected_raw: Option<u16>,
    pub bounded_raw: Option<u8>,
    pub result035b: Option<u8>,
    pub result024a: Option<u8>,
    pub error: Option<String>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Sequence {
    pub image_index: usize,
    pub scratch_pattern: u8,
    pub checkpoints: Vec<Checkpoint>,
    pub completed_calls: usize,
    pub stop_call_index: i32,
}

pub(crate) fn correction_contract() -> SliceContract {
    SliceContract {
        entry_pc: 0x0F85,
        exit_pcs: vec![0x1076],
        code_ranges: vec![[0x0F85, 0x1076]],
        psw: 0x0101,
        lrb: 0x40,
        usp: 0x180,
        instruction_budget: 128,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    }
}

pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({
        "id":"ignitionCorrectionChain", "formatVersion":1,
        "producer":{"entry":0x5F93,"exit":0x5FAF},
        "scriptedEntries":[0x0A0C,0x0B64,0x0F85],
        "unbrokenPrefix":[0x0B64,0x0BD4],
        "correction":{"entry":0x0F85,"exit":0x1076,"budget":128,
            "pathGate":"DATA0212.5=1, once-only; other M2g primary gates remain clear"},
        "nativeReader0248":0x0FF4,
        "nativeOutputs":[0x035B,0x024A],
        "units":"raw", "physicalRpmAvailable":false, "assumptions":[]
    })]
}

pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .ignition_correction_chain
        .as_ref()
        .ok_or("M2i stimulus required")?;
    if s.format_version != 1
        || s.calls.is_empty()
        || s.calls.len() > 64
        || s.trace_call_indexes.len() > 8
        || s.trace_call_indexes
            .iter()
            .any(|i| *i as usize >= s.calls.len())
        || s.trace_call_indexes
            .iter()
            .collect::<std::collections::HashSet<_>>()
            .len()
            != s.trace_call_indexes.len()
        || s.initial.ignition.load_index > 8
        || s.initial.ignition.map0_rpm_index > 18
        || s.initial.ignition.map1_rpm_index > 18
        || s.calls
            .iter()
            .enumerate()
            .any(|(i, c)| c.index as usize != i)
        || r.images.is_empty()
        || r.images.len() > 2
        || r.images[0].id != "baseline"
        || r.images.get(1).is_some_and(|i| i.id != "mutated")
        || r.images.iter().any(|i| i.rom.len() != 32768)
        || r.scratch_patterns != [0, 85, 170]
        || !(r.allow_assumptions.is_empty()
            || r.allow_assumptions.as_slice() == [crate::protocol::ADD_ASSUMPTION])
        || r.synthetic.is_some()
        || r.producer_cases.is_some()
    {
        return Err("invalid bounded M2i correction-chain request".into());
    }
    Ok(())
}

fn data_ranges() -> Vec<[u16; 2]> {
    let mut ranges = ignition_selector::data_ranges();
    ranges.extend([
        [0x221, 0x222],
        [0x234, 0x235],
        [0x245, 0x24D],
        [0x35B, 0x35C],
    ]);
    ranges
}

fn admission(d: &Decoded) -> FormAdmission {
    if d.mnemonic == "SUBB A, off N8" {
        return FormAdmission::Unsupported;
    }
    if crate::stateful_forms::admission(d)
        == FormAdmission::Assumption(crate::stateful_forms::SUBB_OFF_ASSUMPTION)
    {
        return FormAdmission::Unsupported;
    }
    if crate::chain_forms::compact_admission(d)
        == FormAdmission::Assumption(crate::protocol::ADD_ASSUMPTION)
    {
        return FormAdmission::Assumption(crate::protocol::ADD_ASSUMPTION);
    }
    if ignition::admission(d) == FormAdmission::Allowed
        || crate::stateful_forms::admission(d) == FormAdmission::Allowed
        || crate::idle::admission(d) == FormAdmission::Allowed
    {
        return FormAdmission::Allowed;
    }
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    if matches!(
        p.mnemonic,
        "CLR A"
            | "ST A, er3"
            | "EXTND"
            | "L A, ACC"
            | "ADD A, er3"
            | "CMP A, #N16"
            | "LB A, ACC"
            | "STB A, r4"
            | "MB off N8.5, C"
            | "SC"
            | "MB off N8.7, C"
            | "MOVB r3, off N8"
            | "LB A, r4"
            | "CMPB A, r3"
            | "LB A, r3"
            | "MB off N8.1, C"
            | "JBR off N8.7, rel8"
            | "JBS off N8.5, rel8"
            | "JBS off N8.0, rel8"
            | "STB A, [DP]"
            | "ADDB A, off N8"
            | "JBR off N8.1, rel8"
    ) {
        FormAdmission::Allowed
    } else {
        FormAdmission::Unsupported
    }
}

fn correction(cpu: &mut Cpu, bus: &mut Bus, trace: bool, assumptions: &[String]) -> Stage {
    let c = correction_contract();
    enter(cpu, bus, &c);
    bus.set_program_data_ranges(vec![]);
    bus.begin_write_journal();
    bus.start_decision_observer();
    let permissions: Vec<&str> = assumptions.iter().map(String::as_str).collect();
    let result =
        execute_in_state_observed(cpu, bus, &c, &permissions, trace, Some(admission), true);
    Stage {
        result,
        writes: bus.end_write_journal(),
        events: bus.finish_decision_observer(),
        ssp_after: cpu.ssp,
    }
}

fn seed(cpu: &mut Cpu, bus: &mut Bus, initial: &Initial) {
    ignition::seed_state_with_data0212(cpu, bus, &initial.ignition, 0x20);
    for (address, value) in [
        (0x3C7, initial.source03c7),
        (0x24C, initial.floor024c),
        (0x249, initial.bias0249),
        (0x35B, initial.retained035b),
        (0x24A, initial.retained024a),
        (0x234, if initial.gate0234_bit5 { 0x20 } else { 0 }),
        (0x217, if initial.gate0217_bit0 { 1 } else { 0 }),
        (0x21E, if initial.gate021e_bit0 { 1 } else { 0 }),
        (0x221, 0),
    ] {
        write_data_u8(cpu, bus, address, value);
    }
}

fn sequence(
    rom: &[u8],
    image_index: usize,
    pattern: u8,
    s: &Stimulus,
    assumptions: &[String],
) -> Sequence {
    let (mut cpu, mut bus) = seed_machine(rom, &ignition_selector::producer_contract(), pattern);
    cpu.ssp = 0x7FE;
    seed(&mut cpu, &mut bus, &s.initial);
    bus.configure_scoped_access(data_ranges(), 8192);
    let mut out = Sequence {
        image_index,
        scratch_pattern: pattern,
        checkpoints: Vec::with_capacity(s.calls.len()),
        completed_calls: 0,
        stop_call_index: -1,
    };
    let mut cumulative_conditional = false;
    for input in &s.calls {
        let before = ignition::state(&cpu, &mut bus);
        let mut cp = Checkpoint {
            index: input.index,
            status: NOT_RUN,
            conditional_dependency: cumulative_conditional,
            input: None,
            state_before: before.clone(),
            state_after: before,
            retained035b_before: read_data_u8(&cpu, &mut bus, 0x35B),
            retained024a_before: read_data_u8(&cpu, &mut bus, 0x24A),
            producer: None,
            axes: None,
            selection: None,
            lookup: None,
            consumer: None,
            selected_origin: None,
            lookup_result: None,
            data0248: None,
            correction_mode0207_bit7: None,
            consumer_exit: None,
            correction_entry: None,
            correction: None,
            native_read0248: None,
            corrected_raw: None,
            bounded_raw: None,
            result035b: None,
            result024a: None,
            error: None,
        };
        if out.stop_call_index >= 0 {
            out.checkpoints.push(cp);
            continue;
        }
        cp.input = Some(input.clone());
        // The sole per-event host-write boundary is BEFORE the producer.
        for (address, value) in [
            (0x3C7, input.source03c7),
            (0x238, input.raw_map0_rpm),
            (0xC2, input.raw_map1_rpm),
            (0xBF, input.raw_load),
            (0x245, input.correction0245),
            (0x246, input.correction0246),
        ] {
            write_data_u8(&mut cpu, &mut bus, address, value);
        }
        let trace = s.trace_call_indexes.contains(&input.index);
        let p = ignition_selector::producer(&mut cpu, &mut bus, trace);
        cp.status = p.result.status;
        cp.error = p.result.error.clone();
        cp.producer = Some(p);
        if cp.status == 0 && !ignition_selector::supported_caller(&cpu, &mut bus) {
            cp.status = 1;
            cp.error = Some("unsupported joint direct caller gates".into());
        }
        if cp.status == 0 {
            enter(&mut cpu, &mut bus, &ignition::contract("axes"));
            let a = ignition::execute(&mut cpu, &mut bus, "axes", false);
            cp.status = a.result.status;
            cp.error = a.result.error.clone();
            cp.axes = Some(a);
        }
        if cp.status == 0 {
            enter(&mut cpu, &mut bus, &ignition::contract("selection"));
            let a = ignition::execute(&mut cpu, &mut bus, "selection", false);
            cp.status = a.result.status;
            cp.error = a.result.error.clone();
            cp.selection = Some(a);
        }
        if cp.status == 0 {
            cp.selected_origin = Some(read_data_u16(&cpu, &mut bus, 0x88));
            let a = ignition::execute(&mut cpu, &mut bus, "lookup", false);
            cp.status = a.result.status;
            cp.error = a.result.error.clone();
            cp.lookup = Some(a);
        }
        if cp.status == 0 {
            cp.lookup_result = Some(cpu.a as u8);
            let a = ignition::execute(&mut cpu, &mut bus, "consumer", false);
            cp.status = a.result.status;
            cp.error = a.result.error.clone();
            cp.consumer = Some(a);
        }
        if cp.status == 0 {
            cp.data0248 = Some(read_data_u8(&cpu, &mut bus, 0x248));
            cp.consumer_exit = Some(boundary(&cpu, &mut bus));
            let c = correction_contract();
            enter(&mut cpu, &mut bus, &c);
            cp.correction_entry = Some(boundary(&cpu, &mut bus));
            let a = correction(&mut cpu, &mut bus, trace, assumptions);
            cp.status = a.result.status;
            cp.error = a.result.error.clone();
            cumulative_conditional |= !a.result.used_assumptions.is_empty();
            cp.conditional_dependency = cumulative_conditional;
            cp.native_read0248 = a.events.iter().find(|e| e[0] == 0x0FF4).map(|e| e[3] as u8);
            cp.corrected_raw = a
                .events
                .iter()
                .find(|e| e[0] == 0x0FF9)
                .map(|e| e[3] as u16);
            if a.events.iter().any(|e| e[0] == 0x0FFA) {
                cp.correction_mode0207_bit7 = Some(read_data_u8(&cpu, &mut bus, 0x207) & 0x80 != 0);
            }
            if cp.status == 0 {
                cp.bounded_raw = Some(read_data_u8(&cpu, &mut bus, cpu.bank_base() + 4));
                cp.result035b = Some(read_data_u8(&cpu, &mut bus, 0x35B));
                cp.result024a = Some(read_data_u8(&cpu, &mut bus, 0x24A));
            }
            cp.correction = Some(a);
        }
        cp.state_after = ignition::state(&cpu, &mut bus);
        if cp.status == 0 {
            out.completed_calls += 1;
        } else {
            out.stop_call_index = input.index as i32;
        }
        out.checkpoints.push(cp);
    }
    out
}

pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r
        .ignition_correction_chain
        .as_ref()
        .ok_or("missing M2i stimulus")?;
    response.entry_contracts = entry_contracts();
    response.ignition_correction_sequences = Some(
        r.images
            .iter()
            .enumerate()
            .flat_map(|(i, image)| {
                r.scratch_patterns
                    .iter()
                    .map(|pattern| sequence(&image.rom, i, *pattern, s, &r.allow_assumptions))
                    .collect::<Vec<_>>()
            })
            .collect(),
    );
    Ok(response)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::decoder::decode;

    #[test]
    fn correction_add_permission_is_exact_and_does_not_import_vtec_subb() {
        let add = [0x47, 0x81];
        let d = decode(true, |i| *add.get(i).unwrap_or(&0)).unwrap();
        assert_eq!(
            admission(&d),
            FormAdmission::Assumption(crate::protocol::ADD_ASSUMPTION)
        );
        let nearby = [0x47, 0x80, 0, 0];
        let d = decode(true, |i| *nearby.get(i).unwrap_or(&0)).unwrap();
        // Independently established immediate form stays Allowed; it does not
        // inherit or require the object/accumulator assumption.
        assert_eq!(admission(&d), FormAdmission::Allowed);
        let vtec_subb = [0xA7, 0x48];
        let d = decode(false, |i| *vtec_subb.get(i).unwrap_or(&0)).unwrap();
        assert_eq!(admission(&d), FormAdmission::Unsupported);
    }
}
