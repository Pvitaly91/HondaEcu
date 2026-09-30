//! M2p: same-machine continuation after the actual store2203. No entry/reset here.
#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        exec::write_data_u16,
        runner::{execute_in_state_observed, seed_machine},
    };
    fn toy(current: u16, old: u16, partial: bool) -> (Cpu, Bus) {
        let mut rom = vec![0u8; 32768];
        // Invented nine-byte producer with an immediate current value, not an OEM suffix.
        rom[0x21FB..0x2204].copy_from_slice(&[
            0x62,
            0xB4,
            3,
            0xB2,
            0x48,
            0x67,
            current as u8,
            (current >> 8) as u8,
            0xD2,
        ]);
        // Invented single subtraction/store/jump. It deliberately omits the OEM gates/clamp.
        rom[0x2204..0x2209].copy_from_slice(&[0x28, 0xD4, 0x50, 0xCB, 0x32]);
        if partial {
            rom[0x2204..0x2208].copy_from_slice(&[0xD4, 0x50, 0x47, 0x81]);
        }
        let mut c = contract();
        c.entry_pc = 0x21FB;
        c.exit_pcs = vec![0x2204];
        c.code_ranges = vec![[0x21FB, 0x2204]];
        let (mut cpu, mut bus) = seed_machine(&rom, &c, 170);
        cpu.ssp = 0x7FE;
        write_data_u16(&mut cpu, &mut bus, 0x3B4, old);
        bus.begin_native_accesses();
        bus.begin_write_journal();
        let result = execute_in_state_observed(
            &mut cpu,
            &mut bus,
            &c,
            &[],
            true,
            Some(crate::fuel_additive::admission),
            true,
        );
        assert_eq!(result.status, 0);
        let accesses = bus.end_native_accesses();
        let writes = bus.end_write_journal();
        assert!(accesses.contains(&[0x21FE, 0x3B4, 16, 0, old as u32]));
        assert!(accesses.contains(&[0x2203, 0x3B4, 16, 1, current as u32]));
        assert!(writes.contains(&[0x3B4, 16, current as u32]));
        (cpu, bus)
    }
    #[test]
    fn invented_native_producer_continues_without_enter_with_distinct_old_and_current() {
        for (current, old) in [(333, 111), (333, 333), (111, 333)] {
            let (mut cpu, mut bus) = toy(current, old, false);
            let prior = boundary(&cpu, &mut bus);
            assert_eq!(prior.pc, 0x2204);
            assert_eq!(prior.accumulator, current);
            assert_eq!(read_data_u16(&cpu, &mut bus, 0x100), old);
            assert_eq!(read_data_u16(&cpu, &mut bus, 0x3B4), current);
            let native = execute_suffix(&mut cpu, &mut bus);
            assert_eq!(native.entry, prior);
            assert_eq!(native.stage.result.status, 0);
            assert_eq!(
                read_data_u16(&cpu, &mut bus, 0x150),
                current.wrapping_sub(old)
            );
            assert!(native
                .accesses
                .contains(&[0x2204, 0x100, 16, 0, old as u32]));
            assert!(native.accesses.contains(&[
                0x2205,
                0x150,
                16,
                1,
                current.wrapping_sub(old) as u32
            ]));
            assert_eq!(native.exit.ssp, prior.ssp);
        }
    }
    #[test]
    fn same_value_native_store_is_not_skipped_and_next_native_load_sees_it() {
        let (mut cpu, mut bus) = toy(77, 77, false);
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x3B4), 77);
        let native = execute_suffix(&mut cpu, &mut bus);
        assert_eq!(native.exit.accumulator, 0);
        assert_eq!(native.stage.writes, vec![[0x150, 16, 0]]);
    }
    #[test]
    fn next_native_event_reads_previous_native_store_without_history_reseed() {
        let (mut cpu, mut bus) = toy(77, 17, false);
        let first = execute_suffix(&mut cpu, &mut bus);
        assert_eq!(first.exit.accumulator, 60);
        // Disclosed scripted caller re-entry before the prefix, never at2204.
        cpu.pc = 0x21FB;
        bus.configure_scoped_access(
            vec![[0, 8], [0x88, 0x90], [0x100, 0x108], [0x3B4, 0x3B6]],
            4096,
        );
        let mut c = contract();
        c.entry_pc = 0x21FB;
        c.exit_pcs = vec![0x2204];
        c.code_ranges = vec![[0x21FB, 0x2204]];
        bus.begin_native_accesses();
        let r = execute_in_state_observed(
            &mut cpu,
            &mut bus,
            &c,
            &[],
            true,
            Some(crate::fuel_additive::admission),
            true,
        );
        assert_eq!(r.status, 0);
        assert!(bus
            .end_native_accesses()
            .contains(&[0x21FE, 0x3B4, 16, 0, 77]));
        let second = execute_suffix(&mut cpu, &mut bus);
        assert_eq!(second.exit.accumulator, 0);
    }
    #[test]
    fn partial_suffix_keeps_native_stores_without_rollback_or_claimed_completion() {
        let (mut cpu, mut bus) = toy(333, 111, true);
        let native = execute_suffix(&mut cpu, &mut bus);
        assert_eq!(native.stage.result.status, 1);
        assert_eq!(native.stage.result.stop_pc, 0x2206);
        assert_eq!(native.stage.writes, vec![[0x150, 16, 333]]);
        assert_eq!(read_data_u16(&cpu, &mut bus, 0x150), 333);
        assert_eq!(native.entry.accumulator, 333);
        assert_eq!(native.entry.registers[0], 111);
    }
    #[test]
    fn new_form_registry_remains_exact_and_rejects_disputed_forms_and_non_acch_alias() {
        for bytes in [
            &[0x47, 0x81][..],
            &[0x45, 0x81][..],
            &[0xA6, 1][..],
            &[0xC5, 6, 0x98, 128][..],
        ] {
            if let Some(d) = crate::decoder::decode(true, |i| bytes.get(i).copied().unwrap_or(0)) {
                assert_eq!(admission(&d), FormAdmission::Unsupported);
            }
        }
        let bytes = [0xC5, 7, 0x98, 128];
        let d = crate::decoder::decode(true, |i| bytes.get(i).copied().unwrap_or(0)).unwrap();
        assert_eq!(admission(&d), FormAdmission::Allowed);
    }
}
use crate::{
    adaptive::Stage,
    adaptive_fuel,
    bus::Bus,
    cpu::Cpu,
    decoder::Decoded,
    exec::{read_data_u16, read_data_u8, write_data_u16, write_data_u8},
    full_decoder::FULL_OPCODES,
    instruction_forms::FormAdmission,
    protocol::{Request, Response},
    runner::{execute_in_state_observed, SliceContract},
    vtec_fuel::{boundary, CpuBoundary},
};
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Initial {
    pub adaptive: adaptive_fuel::Initial,
    pub previous03b4: u16,
}
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Call {
    pub adaptive: adaptive_fuel::Call,
    pub disable125: bool,
    pub disable12e: bool,
}
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Stimulus {
    pub format_version: u32,
    pub initial_state: Initial,
    pub calls: Vec<Call>,
    pub trace_call_indexes: Vec<u32>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Suffix {
    pub entry: CpuBoundary,
    pub exit: CpuBoundary,
    pub stage: Stage,
    pub accesses: Vec<[u32; 5]>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Checkpoint {
    pub index: u32,
    pub status: i32,
    pub prefix: adaptive_fuel::Checkpoint,
    pub source_bytes_before: [u8; 2],
    pub source_bytes_after: [u8; 2],
    pub snapshot_writes: Vec<[u32; 3]>,
    pub word0150_before: u16,
    pub word0150_after: u16,
    pub suffix: Option<Suffix>,
    pub post_store_word0150: Option<u16>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Sequence {
    pub scratch_pattern: u8,
    pub checkpoints: Vec<Checkpoint>,
}
pub fn validate_request(r: &Request) -> Result<(), String> {
    let s = r
        .fuel_post_store_chain
        .as_ref()
        .ok_or("M2p stimulus required")?;
    validate_stimulus(r, s)
}
pub(crate) fn validate_stimulus(r: &Request, s: &Stimulus) -> Result<(), String> {
    // Preserve all historical M2o admission without accepting its top-level stimulus.
    let old = serde_json::from_value::<adaptive_fuel::Stimulus>(serde_json::json!({
        "formatVersion":s.format_version, "initialState": {
            "joint": serde_json::to_value(&s.initial_state.adaptive.joint).map_err(|e|e.to_string())?,
            "ramCut":s.initial_state.adaptive.ram_cut, "ramResume":s.initial_state.adaptive.ram_resume,
            "timer":s.initial_state.adaptive.timer, "counter":s.initial_state.adaptive.counter,
            "ie":s.initial_state.adaptive.ie, "restoreIe":s.initial_state.adaptive.restore_ie
        }, "calls":s.calls.iter().map(|c| &c.adaptive).collect::<Vec<_>>(),
        "traceCallIndexes":s.trace_call_indexes
    })).map_err(|e|e.to_string())?;
    adaptive_fuel::validate_stimulus(r, &old)
}
pub fn contract() -> SliceContract {
    SliceContract {
        entry_pc: 0x2204,
        exit_pcs: vec![0x223B],
        code_ranges: vec![[0x2204, 0x223B]],
        psw: 0x0101,
        lrb: 0x20,
        usp: 0x280,
        instruction_budget: 48,
        data_seeds: vec![],
        output_addresses: vec![],
        program_read_range: None,
    }
}
pub fn entry_contracts() -> Vec<serde_json::Value> {
    vec![
        serde_json::json!({"id":"fuelPostStoreChain","formatVersion":1,
        "prefixContract":adaptive_fuel::entry_contracts()[0],
        "nativeContinuation":[0x2204,0x223B],"softwareOutput":[0x2239,0x150,16],
        "nextReader":[0x223D,0x150,16],"sourceMasks":[[0x125,16],[0x12E,16]],
        "initialHistory":"Declared previous03B4 once; subsequent history native store2203",
        "assumptions":[],"physicalRpmAvailable":false,"stop":"BeforeInstruction223B"}),
    ]
}
pub fn admission(d: &Decoded) -> FormAdmission {
    let Some(p) = FULL_OPCODES.get(d.index) else {
        return FormAdmission::Unsupported;
    };
    if p.mnemonic != d.mnemonic || p.bytes_pat.len() != d.len {
        return FormAdmission::Unsupported;
    }
    if p.mnemonic == "MOVB N'8, #N8" && d.fields.n8_alt != 7 {
        return FormAdmission::Unsupported;
    }
    match (p.mnemonic, p.dd_mode, p.bytes_pat) {
        ("JBS off N8.4, rel8", 'U', ["EC", "N8", "rel8"])
        | ("CMPB off N'8, #N8", 'U', ["C4", "N'8", "C0", "N8"])
        | ("CMP off N8, #N16", 'U', ["B4", "N8", "C0", "NL", "NH"])
        | ("SUB A, er0", '1', ["28"])
        | ("CMP A, er0", '1', ["48"])
        | ("MOV er0, #N16", 'U', ["44", "98", "NL", "NH"])
        | ("MOVB N'8, #N8", 'U', ["C5", "N'8", "98", "N8"])
        | ("SLL A", '1', ["53"])
        | ("L A, er1", 'S', ["35"])
        | ("MUL", 'U', ["90", "35"])
        | ("ROL A", '1', ["33"])
        | ("CLR A", 'S', ["F9"])
        | ("JGE rel8", 'U', ["CD", "rel8"])
        | ("JLT rel8", 'U', ["CA", "rel8"])
        | ("JNE rel8", 'U', ["CE", "rel8"])
        | ("SJ rel8", 'U', ["CB", "rel8"])
        | ("CMP A, #N16", '1', ["C6", "NL", "NH"])
        | ("L A, #N16", 'S', ["67", "NL", "NH"])
        | ("ST A, er0", '1', ["88"])
        | ("ST A, off N8", '1', ["D4", "N8"]) => FormAdmission::Allowed,
        _ => FormAdmission::Unsupported,
    }
}
pub(crate) fn execute_suffix(cpu: &mut Cpu, bus: &mut Bus) -> Suffix {
    // Observation/admission changes only; deliberately no enter/PC/register writes.
    bus.configure_scoped_access(
        vec![
            [0, 8],
            [0x88, 0x90],
            [0x100, 0x108],
            [0x125, 0x126],
            [0x12E, 0x12F],
            [0x133, 0x134],
            [0x14C, 0x14E],
            [0x150, 0x152],
        ],
        4096,
    );
    bus.set_program_data_ranges(vec![]);
    bus.clear_program_reads();
    let entry = boundary(cpu, bus);
    bus.begin_native_accesses();
    bus.begin_write_journal();
    bus.start_decision_observer();
    let result = execute_in_state_observed(cpu, bus, &contract(), &[], true, Some(admission), true);
    let accesses = bus.end_native_accesses();
    let stage = Stage {
        result,
        writes: bus.end_write_journal(),
        events: bus.finish_decision_observer(),
        ssp_after: cpu.ssp,
    };
    let exit = boundary(cpu, bus);
    Suffix {
        entry,
        exit,
        stage,
        accesses,
    }
}
pub(crate) fn initialize(rom: &[u8], pattern: u8, initial: &Initial) -> (Cpu, Bus) {
    let (mut cpu, mut bus) = adaptive_fuel::initialize(rom, pattern, &initial.adaptive);
    write_data_u16(&mut cpu, &mut bus, 0x3B4, initial.previous03b4);
    write_data_u16(&mut cpu, &mut bus, 0x150, 0);
    (cpu, bus)
}
pub(crate) fn checkpoint(cpu: &Cpu, bus: &mut Bus, c: &Call) -> Checkpoint {
    let prefix = adaptive_fuel::checkpoint(cpu, bus, &c.adaptive);
    bus.configure_scoped_access(vec![[0x125, 0x126], [0x12E, 0x12F], [0x150, 0x152]], 4096);
    let source_bytes_before = [0x125, 0x12E].map(|a| read_data_u8(cpu, bus, a));
    let word0150_before = read_data_u16(cpu, bus, 0x150);
    Checkpoint {
        index: c.adaptive.fuel.index,
        status: 4,
        prefix,
        source_bytes_before,
        source_bytes_after: source_bytes_before,
        snapshot_writes: vec![],
        word0150_before,
        word0150_after: word0150_before,
        suffix: None,
        post_store_word0150: None,
    }
}
/// Reused execution on one initialized machine; stops before223B as always.
pub(crate) fn execute_checkpoint(cpu: &mut Cpu, bus: &mut Bus, c: &Call, row: &mut Checkpoint) {
    bus.begin_write_journal();
    for (i, (a, on)) in [(0x125, c.disable125), (0x12E, c.disable12e)]
        .into_iter()
        .enumerate()
    {
        write_data_u8(
            cpu,
            bus,
            a,
            (row.source_bytes_before[i] & !16) | if on { 16 } else { 0 },
        );
    }
    row.snapshot_writes = bus.end_write_journal();
    adaptive_fuel::execute_checkpoint(cpu, bus, &c.adaptive, &mut row.prefix);
    row.status = row.prefix.status;
    if row.status == 0 {
        let suffix = execute_suffix(cpu, bus);
        row.status = suffix.stage.result.status;
        if row.status == 0 {
            row.post_store_word0150 = Some(read_data_u16(cpu, bus, 0x150));
        }
        row.suffix = Some(suffix);
    }
    bus.configure_scoped_access(vec![[0x125, 0x126], [0x12E, 0x12F], [0x150, 0x152]], 4096);
    row.source_bytes_after = [0x125, 0x12E].map(|a| read_data_u8(cpu, bus, a));
    row.word0150_after = read_data_u16(cpu, bus, 0x150);
}
pub fn run(r: Request, mut response: Response) -> Result<Response, String> {
    let s = r.fuel_post_store_chain.as_ref().expect("validated");
    let mut sequences = vec![];
    for &pattern in &r.scratch_patterns {
        let (mut cpu, mut bus) = initialize(&r.images[0].rom, pattern, &s.initial_state);
        let mut stopped = false;
        let mut checkpoints = vec![];
        for c in &s.calls {
            let mut row = checkpoint(&cpu, &mut bus, c);
            if !stopped {
                execute_checkpoint(&mut cpu, &mut bus, c, &mut row);
                stopped = row.status != 0;
            }
            checkpoints.push(row);
        }
        sequences.push(Sequence {
            scratch_pattern: pattern,
            checkpoints,
        });
    }
    response.entry_contracts = entry_contracts();
    response.post_store_sequences = Some(sequences);
    Ok(response)
}
