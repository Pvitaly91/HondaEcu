//! M2g: the ROM writes DATA0227.5 before the scripted ignition caller.
//! The exact original has both configuration bytes clear, so this producer
//! clears the bit; an initially set bit is not a native map-1 witness.
use crate::{
    acquisition::enter,
    adaptive::Stage,
    bus::Bus,
    cpu::Cpu,
    decoder::Decoded,
    exec::{read_data_u16, read_data_u8, write_data_u8},
    full_decoder::FULL_OPCODES,
    ignition,
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
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Call {
    pub index: u32,
    pub source03c7: u8,
    pub raw_load: u8,
    pub raw_map0_rpm: u8,
    pub raw_map1_rpm: u8,
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
    pub input: Option<Call>,
    pub state_before: ignition::State,
    pub state_after_inputs: Option<ignition::State>,
    pub state_after: ignition::State,
    pub source_before: u8,
    pub source_after_inputs: Option<u8>,
    pub producer: Option<Stage>,
    pub producer_exit: Option<CpuBoundary>,
    pub axes_entry: Option<CpuBoundary>,
    pub axes: Option<Stage>,
    pub selection_entry: Option<CpuBoundary>,
    pub selection: Option<Stage>,
    pub selection_exit: Option<CpuBoundary>,
    pub selected_origin: Option<u16>,
    pub position: Option<ignition::Position>,
    pub lookup_entry: Option<CpuBoundary>,
    pub lookup: Option<Stage>,
    pub lookup_exit: Option<CpuBoundary>,
    pub lookup_result: Option<u8>,
    pub consumer_entry: Option<CpuBoundary>,
    pub consumer: Option<Stage>,
    pub consumer_output: Option<u8>,
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

pub(crate) fn producer_contract() -> SliceContract {
    SliceContract {
        entry_pc: 0x5F93,
        exit_pcs: vec![0x5FAF],
        code_ranges: vec![[0x5F93, 0x5FAF], [0x7DF4, 0x7E02]],
        psw: 0x0101,
        lrb: 0x41,
        usp: 0x180,
        instruction_budget: 32,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    }
}

pub(crate) fn data_ranges() -> Vec<[u16; 2]> {
    let mut ranges = ignition::data_ranges();
    ranges.extend([[0x208, 0x210], [0x3C7, 0x3C8]]);
    ranges
}

pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![serde_json::json!({
        "id":"ignitionSelectorChain", "formatVersion":1,
        "producer":{"entry":0x5F93,"exit":0x5FAF,"code":[[0x5F93,0x5FAF],[0x7DF4,0x7E02]],
        "programData":[[0x60EA,0x60EB],[0x60FB,0x60FC],[0x7E02,0x7E03]],"lrb":0x41,"usp":0x180,"budget":32},
        "scriptedStages":[[0x0A0C,0x0A62],[0x0B64,0x0BAF]],
        "unbrokenTail":[[0x0B64,0x0BAF],[0x0BAF,0x0BB4],[0x0BB4,0x0BD4]],
        "sourceInputs":["DATA03C7"], "perCallMapId":false,
        "data0227":"Full byte seeded once; after that only native instructions write selector bit",
        "fixedCallerGates":{"data00B8Mask18":0,"data0212Bits2And4":false,"data021dBit4":false,
            "data0214Bit5":false,"data0218Bit5":false,"data021fBit1":false,"data0219Bit6":false},
        "state":"OneCpuRamPerImageScratchSequence", "physicalRpmAvailable":false,"assumptions":[]
    })]
}

pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .ignition_selector_chain
        .as_ref()
        .ok_or("M2g stimulus required")?;
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
        || !r.allow_assumptions.is_empty()
        || r.synthetic.is_some()
        || r.producer_cases.is_some()
    {
        return Err("invalid bounded M2g selector-chain request".into());
    }
    Ok(())
}

fn admission(d: &Decoded) -> FormAdmission {
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    if crate::stateful_forms::admission(d) == FormAdmission::Allowed
        || matches!(
            p.mnemonic,
            "LB A, [DP]" | "RC" | "MB off N8.5, C" | "SLLB A" | "ANDB r1, #N8"
        )
    {
        FormAdmission::Allowed
    } else {
        FormAdmission::Unsupported
    }
}

pub(crate) fn producer(cpu: &mut Cpu, bus: &mut Bus, trace: bool) -> Stage {
    let c = producer_contract();
    enter(cpu, bus, &c);
    bus.set_program_data_ranges(vec![[0x60EA, 0x60EB], [0x60FB, 0x60FC], [0x7E02, 0x7E03]]);
    bus.begin_write_journal();
    bus.start_decision_observer();
    let result = execute_in_state_observed(cpu, bus, &c, &[], trace, Some(admission), true);
    Stage {
        result,
        writes: bus.end_write_journal(),
        events: bus.finish_decision_observer(),
        ssp_after: cpu.ssp,
    }
}

pub(crate) fn supported_caller(cpu: &Cpu, bus: &mut Bus) -> bool {
    read_data_u8(cpu, bus, 0xB8) & 0x18 == 0
        && read_data_u8(cpu, bus, 0x212) & 0x14 == 0
        && read_data_u8(cpu, bus, 0x21D) & 0x10 == 0
        && read_data_u8(cpu, bus, 0x214) & 0x20 == 0
        && read_data_u8(cpu, bus, 0x218) & 0x20 == 0
        && read_data_u8(cpu, bus, 0x21F) & 0x02 == 0
        && read_data_u8(cpu, bus, 0x219) & 0x40 == 0
}

fn sequence(rom: &[u8], image_index: usize, pattern: u8, s: &Stimulus) -> Sequence {
    let (mut cpu, mut bus) = seed_machine(rom, &producer_contract(), pattern);
    cpu.ssp = 0x7FE;
    ignition::seed_state(&mut cpu, &mut bus, &s.initial.ignition);
    write_data_u8(&mut cpu, &mut bus, 0x3C7, s.initial.source03c7);
    bus.configure_scoped_access(data_ranges(), 8192);
    let mut result = Sequence {
        image_index,
        scratch_pattern: pattern,
        checkpoints: Vec::with_capacity(s.calls.len()),
        completed_calls: 0,
        stop_call_index: -1,
    };
    for input in &s.calls {
        let before = ignition::state(&cpu, &mut bus);
        let source_before = read_data_u8(&cpu, &mut bus, 0x3C7);
        let mut cp = Checkpoint {
            index: input.index,
            status: NOT_RUN,
            input: None,
            state_before: before.clone(),
            state_after_inputs: None,
            state_after: before,
            source_before,
            source_after_inputs: None,
            producer: None,
            producer_exit: None,
            axes_entry: None,
            axes: None,
            selection_entry: None,
            selection: None,
            selection_exit: None,
            selected_origin: None,
            position: None,
            lookup_entry: None,
            lookup: None,
            lookup_exit: None,
            lookup_result: None,
            consumer_entry: None,
            consumer: None,
            consumer_output: None,
            error: None,
        };
        if result.stop_call_index >= 0 {
            result.checkpoints.push(cp);
            continue;
        }
        cp.input = Some(input.clone());
        for (address, value) in [
            (0x3C7, input.source03c7),
            (0x238, input.raw_map0_rpm),
            (0xC2, input.raw_map1_rpm),
            (0xBF, input.raw_load),
        ] {
            write_data_u8(&mut cpu, &mut bus, address, value);
        }
        cp.state_after_inputs = Some(ignition::state(&cpu, &mut bus));
        cp.source_after_inputs = Some(read_data_u8(&cpu, &mut bus, 0x3C7));
        let trace = s.trace_call_indexes.contains(&input.index);
        let p = producer(&mut cpu, &mut bus, trace);
        cp.status = p.result.status;
        cp.error = p.result.error.clone();
        cp.producer = Some(p);
        if cp.status == 0 {
            cp.producer_exit = Some(boundary(&cpu, &mut bus));
            if !supported_caller(&cpu, &mut bus) {
                cp.status = 1;
                cp.error = Some("producer left unsupported direct ignition caller gates".into());
            }
        }
        if cp.status == 0 {
            // Entry is a disclosed caller action; no RAM/cache/selector reset.
            enter(&mut cpu, &mut bus, &ignition::contract("axes"));
            cp.axes_entry = Some(boundary(&cpu, &mut bus));
            let a = ignition::execute(&mut cpu, &mut bus, "axes", false);
            cp.status = a.result.status;
            cp.error = a.result.error.clone();
            cp.axes = Some(a);
        }
        if cp.status == 0 {
            enter(&mut cpu, &mut bus, &ignition::contract("selection"));
            cp.selection_entry = Some(boundary(&cpu, &mut bus));
            let selection = ignition::execute(&mut cpu, &mut bus, "selection", false);
            cp.status = selection.result.status;
            cp.error = selection.result.error.clone();
            cp.selection = Some(selection);
            if cp.status == 0 {
                cp.selection_exit = Some(boundary(&cpu, &mut bus));
            }
        }
        if cp.status == 0 {
            let origin = read_data_u16(&cpu, &mut bus, 0x88);
            cp.selected_origin = Some(origin);
            let selected_one = origin == 0x73AC;
            cp.position = Some(ignition::Position {
                load_index: read_data_u8(&cpu, &mut bus, 0x1BB),
                load_fraction: read_data_u16(&cpu, &mut bus, 0x1BE),
                rpm_index: read_data_u8(&cpu, &mut bus, if selected_one { 0x1C7 } else { 0x1C6 }),
                rpm_fraction: read_data_u16(
                    &cpu,
                    &mut bus,
                    if selected_one { 0x1C4 } else { 0x1C2 },
                ),
            });
            cp.lookup_entry = Some(boundary(&cpu, &mut bus));
            let lookup = ignition::execute(&mut cpu, &mut bus, "lookup", false);
            cp.status = lookup.result.status;
            cp.error = lookup.result.error.clone();
            cp.lookup = Some(lookup);
            if cp.status == 0 {
                cp.lookup_exit = Some(boundary(&cpu, &mut bus));
            }
        }
        if cp.status == 0 {
            cp.lookup_result = Some(cpu.a as u8);
            cp.consumer_entry = Some(boundary(&cpu, &mut bus));
            let consumer = ignition::execute(&mut cpu, &mut bus, "consumer", false);
            cp.status = consumer.result.status;
            cp.error = consumer.result.error.clone();
            cp.consumer = Some(consumer);
            if cp.status == 0 {
                cp.consumer_output = Some(read_data_u8(&cpu, &mut bus, 0x248));
            }
        }
        cp.state_after = ignition::state(&cpu, &mut bus);
        if cp.status == 0 {
            result.completed_calls += 1;
        } else {
            result.stop_call_index = input.index as i32;
        }
        result.checkpoints.push(cp);
    }
    result
}

pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r
        .ignition_selector_chain
        .as_ref()
        .ok_or("missing M2g stimulus")?;
    response.entry_contracts = entry_contracts();
    response.ignition_selector_sequences = Some(
        r.images
            .iter()
            .enumerate()
            .flat_map(|(i, image)| {
                r.scratch_patterns
                    .iter()
                    .map(|pattern| sequence(&image.rom, i, *pattern, s))
                    .collect::<Vec<_>>()
            })
            .collect(),
    );
    Ok(response)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn invented(entry: u16, exit: u16) -> SliceContract {
        SliceContract {
            entry_pc: entry,
            exit_pcs: vec![exit],
            code_ranges: vec![[entry as u32, exit as u32]],
            psw: 0x0101,
            lrb: 0x20,
            usp: 0x180,
            instruction_budget: 16,
            data_seeds: vec![],
            output_addresses: vec![],
            program_read_range: None,
        }
    }

    #[test]
    fn invented_source_writer_to_reader_selects_data_without_host_map_input() {
        let mut rom = vec![0; 32768];
        // Invented program, not an OEM fragment: raw bit7 -> carry ->
        // off-page bit5, followed by an independent branch selecting a byte.
        rom[0x100..0x111].copy_from_slice(&[
            0xF5, 0xC0, 0x53, 0xC4, 0x27, 0x3D, // producer
            0xED, 0x27, 0x04, 0x77, 0x11, 0xCB, 0x02, 0x77, 0x22, 0xD4, 0x48, // reader
        ]);
        let (mut cpu, mut bus) = seed_machine(&rom, &invented(0x100, 0x106), 0);
        bus.configure_scoped_access(
            vec![
                [0, 8],
                [0xC0, 0xC1],
                [0x80, 0x90],
                [0x100, 0x108],
                [0x127, 0x128],
                [0x148, 0x149],
                [0x7E0, 0x800],
            ],
            64,
        );
        write_data_u8(&mut cpu, &mut bus, 0x127, 0x20);
        for (raw, expected_selector, expected_output) in [(0u8, 0u8, 0x11u8), (0x80, 0x20, 0x22)] {
            write_data_u8(&mut cpu, &mut bus, 0xC0, raw);
            enter(&mut cpu, &mut bus, &invented(0x100, 0x106));
            let p = execute_in_state_observed(
                &mut cpu,
                &mut bus,
                &invented(0x100, 0x106),
                &[],
                true,
                Some(admission),
                true,
            );
            assert_eq!(p.status, 0, "{:?}", p.error);
            assert_eq!(
                read_data_u8(&cpu, &mut bus, 0x127) & 0x20,
                expected_selector
            );
            let producer_exit = boundary(&cpu, &mut bus);
            let reader_entry = boundary(&cpu, &mut bus);
            assert_eq!(producer_exit, reader_entry);
            let r = execute_in_state_observed(
                &mut cpu,
                &mut bus,
                &invented(0x106, 0x111),
                &[],
                true,
                Some(admission),
                true,
            );
            assert_eq!(r.status, 0, "{:?}", r.error);
            assert_eq!(read_data_u8(&cpu, &mut bus, 0x148), expected_output);
        }
    }

    #[test]
    fn invented_equal_output_does_not_hide_bad_reinitializer() {
        let mut rom = vec![0; 32768];
        rom[0x100..0x111].copy_from_slice(&[
            0xF5, 0xC0, 0x53, 0xC4, 0x27, 0x3D, 0xED, 0x27, 0x04, 0x77, 0x11, 0xCB, 0x02, 0x77,
            0x22, 0xD4, 0x48,
        ]);
        let (mut cpu, mut bus) = seed_machine(&rom, &invented(0x100, 0x106), 0);
        bus.configure_scoped_access(
            vec![
                [0, 8],
                [0xC0, 0xC1],
                [0x80, 0x90],
                [0x100, 0x108],
                [0x127, 0x128],
                [0x148, 0x149],
                [0x7E0, 0x800],
            ],
            64,
        );
        write_data_u8(&mut cpu, &mut bus, 0xC0, 0x80);
        let p = execute_in_state_observed(
            &mut cpu,
            &mut bus,
            &invented(0x100, 0x106),
            &[],
            false,
            Some(admission),
            true,
        );
        assert_eq!(p.status, 0);
        let true_boundary = boundary(&cpu, &mut bus);
        enter(&mut cpu, &mut bus, &invented(0x106, 0x111)); // deliberate bad host reset
        let wrong_boundary = boundary(&cpu, &mut bus);
        assert_ne!(true_boundary, wrong_boundary);
        let r = execute_in_state_observed(
            &mut cpu,
            &mut bus,
            &invented(0x106, 0x111),
            &[],
            false,
            Some(admission),
            true,
        );
        assert_eq!(r.status, 0);
        assert_eq!(read_data_u8(&cpu, &mut bus, 0x148), 0x22); // same final number
    }
}
