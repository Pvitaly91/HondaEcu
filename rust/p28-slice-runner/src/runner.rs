use crate::bus::Bus;
use crate::cpu::Cpu;
use crate::decoder::decode;
use crate::exec::{read_data_u8, step, write_data_u16, write_data_u8};
use crate::protocol::{
    CaseResult, Diagnostic, Request, Response, SyntheticContract, TraceEntry, ADD_ASSUMPTION,
    PRODUCER_ADD_ASSUMPTION, PROTOCOL_VERSION,
};

const MAX_TRACE: usize = 128;
const MAX_DIAGNOSTICS: usize = 40;
const MAX_SYNTHETIC_STEPS: u32 = 10_000;

/// A success boundary is checked BEFORE fetching the next instruction. It is
/// never represented by a replacement RET or any modification of the image.
#[derive(Clone)]
pub struct SliceContract {
    pub entry_pc: u16,
    pub exit_pcs: Vec<u16>,
    pub code_ranges: Vec<[u32; 2]>,
    pub psw: u16,
    pub lrb: u16,
    pub usp: u16,
    pub instruction_budget: u32,
    pub data_seeds: Vec<[u16; 2]>,
    pub output_addresses: Vec<u16>,
    pub program_read_range: Option<[u32; 2]>,
}

impl From<&SyntheticContract> for SliceContract {
    fn from(value: &SyntheticContract) -> Self {
        Self {
            entry_pc: value.entry_pc,
            exit_pcs: value.exit_pcs.clone(),
            code_ranges: value.allowed_code_ranges.clone(),
            psw: value.psw,
            lrb: value.lrb,
            usp: value.usp,
            instruction_budget: value.instruction_budget,
            data_seeds: value.data_seeds.clone(),
            output_addresses: value.output_addresses.clone(),
            program_read_range: None,
        }
    }
}

fn inside_instruction_range(pc: u16, len: usize, ranges: &[[u32; 2]]) -> bool {
    let start = pc as u32;
    let end = start + len as u32;
    ranges
        .iter()
        .any(|range| start >= range[0] && end <= range[1])
}

/// Explicitly bounded operation subset. Other decoded operations are not NOPs:
/// they stop with an error even when an unrelated assumption was permitted.
fn supported_operation(mnemonic: &str) -> bool {
    matches!(
        mnemonic.split_whitespace().next().unwrap_or(""),
        "L" | "LB"
            | "LC"
            | "LCB"
            | "ST"
            | "STB"
            | "MOV"
            | "MOVB"
            | "CMP"
            | "CMPB"
            | "MB"
            | "SB"
            | "RB"
            | "DIV"
            | "SRL"
            | "ROR"
            | "ADD"
            | "INC"
            | "CLR"
            | "CLRB"
            | "JLT"
            | "JGE"
            | "JNE"
            | "JEQ"
            | "JBS"
            | "JBR"
            | "SJ"
    )
}

/// Run unchanged program bytes from a new deterministic state. No model result
/// or expected output is supplied to the executor.
pub fn execute_case(
    rom: &[u8],
    contract: &SliceContract,
    scratch: u8,
    allow_add: bool,
    capture_trace: bool,
) -> CaseResult {
    let (mut cpu, mut bus) = seed_machine(rom, contract, scratch);
    let assumptions = if allow_add {
        vec![ADD_ASSUMPTION]
    } else {
        vec![]
    };
    execute_in_state(
        &mut cpu,
        &mut bus,
        contract,
        &assumptions,
        capture_trace,
        false,
    )
}

pub(crate) fn seed_machine(rom: &[u8], contract: &SliceContract, scratch: u8) -> (Cpu, Bus) {
    let mut cpu = Cpu::new();
    let mut bus = Bus::new(rom.to_vec(), scratch);
    cpu.pc = contract.entry_pc;
    write_data_u16(&mut cpu, &mut bus, 2, contract.lrb);
    write_data_u16(&mut cpu, &mut bus, 4, contract.psw);
    write_data_u16(
        &mut cpu,
        &mut bus,
        6,
        u16::from_le_bytes([scratch, scratch]),
    );
    let usp_address = 0x80 + cpu.scb() * 8 + 6;
    write_data_u16(&mut cpu, &mut bus, usp_address, contract.usp);
    for [address, value] in &contract.data_seeds {
        write_data_u8(&mut cpu, &mut bus, *address, *value as u8);
    }
    (cpu, bus)
}

pub(crate) fn execute_in_state(
    cpu: &mut Cpu,
    bus: &mut Bus,
    contract: &SliceContract,
    assumptions: &[&str],
    capture_trace: bool,
    producer_policy: bool,
) -> CaseResult {
    execute_in_state_with_policy(
        cpu,
        bus,
        contract,
        assumptions,
        capture_trace,
        if producer_policy {
            Some(crate::instruction_forms::producer_form_admission)
        } else {
            None
        },
    )
}

pub(crate) fn execute_in_state_with_policy(
    cpu: &mut Cpu,
    bus: &mut Bus,
    contract: &SliceContract,
    assumptions: &[&str],
    capture_trace: bool,
    form_policy: Option<fn(&crate::decoder::Decoded) -> crate::instruction_forms::FormAdmission>,
) -> CaseResult {
    execute_in_state_observed(
        cpu,
        bus,
        contract,
        assumptions,
        capture_trace,
        form_policy,
        false,
    )
}

/// One executor loop for old tasks and stateful acquisition stages. Extents
/// contain only admitted instructions actually passed to step, never decoder
/// lookahead or a presumed whole routine range.
pub(crate) fn execute_in_state_observed(
    cpu: &mut Cpu,
    bus: &mut Bus,
    contract: &SliceContract,
    assumptions: &[&str],
    capture_trace: bool,
    form_policy: Option<fn(&crate::decoder::Decoded) -> crate::instruction_forms::FormAdmission>,
    record_extents: bool,
) -> CaseResult {
    let mut result = CaseResult {
        status: 0,
        used_assumptions: vec![],
        steps: 0,
        stop_pc: cpu.pc,
        outputs: vec![],
        program_reads: vec![],
        trace: vec![],
        error: None,
        executed_instruction_bytes: None,
    };
    let mut extents = std::collections::BTreeSet::new();
    if let Some(fault) = bus.take_fault() {
        result.status = 2;
        result.error = Some(format!("invalid entry state: {fault}"));
    } else {
        loop {
            if contract.exit_pcs.contains(&cpu.pc) {
                break;
            }
            if result.steps >= contract.instruction_budget {
                result.status = 3;
                result.error = Some("instruction budget exceeded".into());
                break;
            }
            if !inside_instruction_range(cpu.pc, 1, &contract.code_ranges) {
                result.status = 2;
                result.error = Some("unexpected escape from allowed code ranges".into());
                break;
            }
            let pc = cpu.pc;
            // Matching probes longer candidate encodings speculatively. A peek
            // may be absent; only the selected instruction's complete actual
            // extent is admitted below, before any byte is executed.
            let decoded = decode(cpu.dd, |offset| {
                bus.peek_code_u8(pc as usize + offset).unwrap_or(0)
            });
            let Some(decoded) = decoded else {
                result.status = 2;
                result.error = Some(format!("undefined opcode at {pc:#06X}"));
                break;
            };
            if pc as usize + decoded.len > bus.rom_len()
                || !inside_instruction_range(pc, decoded.len, &contract.code_ranges)
            {
                result.status = 2;
                result.error = Some("instruction crosses allowed code boundary".into());
                break;
            }
            let mut required_assumption = None;
            let admitted = if let Some(policy) = form_policy {
                match policy(&decoded) {
                    crate::instruction_forms::FormAdmission::Allowed => true,
                    crate::instruction_forms::FormAdmission::Assumption(id) => {
                        required_assumption = Some(id);
                        true
                    }
                    crate::instruction_forms::FormAdmission::Unsupported => false,
                }
            } else {
                supported_operation(decoded.mnemonic)
            };
            if !admitted {
                // A decoded producer form outside the audited registry is an
                // unresolved evidence boundary, not an implicitly admitted
                // instruction merely because its mnemonic is familiar.
                result.status = if form_policy.is_some() { 1 } else { 2 };
                result.error = Some(format!(
                    "unimplemented in reviewed slice subset: {}",
                    decoded.mnemonic
                ));
                break;
            }
            // This word object form is DD-independent in the upstream table.
            // Never allow DD=0 to bypass the research assumption gate.
            if decoded.len == 2 && bus.fetch_code_u8(pc + 1) == 0x81 {
                match bus.fetch_code_u8(pc) {
                    0x47 => required_assumption = Some(ADD_ASSUMPTION),
                    0x45 => required_assumption = Some(PRODUCER_ADD_ASSUMPTION),
                    0x44 | 0x46 => {
                        result.status = 1;
                        result.error = Some(
                            "word object ADD form not established and no defined permission exists"
                                .into(),
                        );
                        break;
                    }
                    _ => {}
                }
            }
            if let Some(id) = required_assumption {
                if !assumptions.contains(&id) {
                    result.status = 1;
                    result.error = Some(format!("unresolved instruction: {id}"));
                    break;
                }
                if !result.used_assumptions.iter().any(|used| used == id) {
                    result.used_assumptions.push(id.into());
                }
            }
            if bus.decision_observing()
                && decoded.mnemonic == "DIVB"
                && read_data_u8(cpu, bus, cpu.bank_base()) == 0
            {
                result.status = 1;
                result.error =
                    Some("unresolved DIVB zero divisor: primary result undefined".into());
                break;
            }
            // A semantic precondition refusal is decoded, but was never stepped.
            if record_extents {
                extents.extend((pc as u32..pc as u32 + decoded.len as u32).map(|a| a as u16));
            }
            let accumulator_before = cpu.a;
            let psw_before = cpu.psw_u16();
            bus.clear_comparison_operands();
            let execution = step(cpu, bus);
            bus.observe_instruction([
                pc as u32,
                cpu.pc as u32,
                accumulator_before as u32,
                cpu.a as u32,
                psw_before as u32,
                cpu.psw_u16() as u32,
            ]);
            result.steps += 1;
            if capture_trace && result.trace.len() < MAX_TRACE {
                result.trace.push(TraceEntry {
                    pc,
                    next_pc: cpu.pc,
                    instruction: decoded.mnemonic.into(),
                    psw: cpu.psw_u16(),
                    accumulator: cpu.a,
                });
            }
            if let Err(error) = execution {
                result.status = 2;
                result.error = Some(error.to_string());
                break;
            }
            if let Some(range) = contract.program_read_range {
                if !bus.program_reads_within(range) {
                    result.status = 2;
                    result.error = Some("program-data read outside slice contract".into());
                    break;
                }
            }
        }
    }
    result.stop_pc = cpu.pc;
    result.outputs = contract
        .output_addresses
        .iter()
        .map(|address| read_data_u8(cpu, bus, *address) as i32)
        .collect();
    result.program_reads = bus.program_reads();
    if record_extents {
        result.executed_instruction_bytes = Some(extents.into_iter().collect());
    }
    if let Some(fault) = bus.take_fault() {
        result.status = 2;
        result.error = Some(fault.to_string());
    }
    result
}

pub(crate) fn compact_contract(raw: u16, s: bool) -> SliceContract {
    SliceContract {
        entry_pc: 0x07C7,
        exit_pcs: vec![0x0822],
        code_ranges: vec![[0x07C7, 0x0822]],
        psw: 0x1101,
        lrb: 0x0040,
        usp: 0x0180,
        instruction_budget: 128,
        data_seeds: vec![
            [0xC4, raw & 255],
            [0xC5, raw >> 8],
            [0x217, if s { 16 } else { 0 }],
        ],
        output_addresses: vec![0x133, 0xB8],
        // This compact slice has no program-data reads.
        program_read_range: Some([0, 0]),
    }
}

pub(crate) fn threshold_contract(code: u8, context: u8, prior: u8, enabled: bool) -> SliceContract {
    SliceContract {
        entry_pc: 0x122C,
        exit_pcs: vec![0x126D, 0x1281],
        code_ranges: vec![[0x122C, 0x126D]],
        psw: 0x0101,
        lrb: 0x0020,
        usp: 0x0280,
        instruction_budget: 128,
        // Prefix comparison only updates bit0, outside requested outputs. Fix
        // its inputs explicitly; do not let scratch patterns alter preconditions.
        data_seeds: vec![
            [0x133, code as u16],
            [0x131, (prior as u16) << 1],
            [0xCC, 0],
            [
                0x11E,
                (if context == 0 { 8 } else { 0 }) | (if enabled { 16 } else { 0 }),
            ],
        ],
        output_addresses: vec![0x131],
        program_read_range: Some([0x6542, 0x654A]),
    }
}

fn validate_request(request: &Request) -> Result<(), String> {
    if request.protocol_version != PROTOCOL_VERSION {
        return Err("unsupported protocol version".into());
    }
    if request.operation != "acquisitionSequence" && request.acquisition_sequence.is_some() {
        return Err("acquisition observations are unavailable to other operations".into());
    }
    if request.operation != "statefulVtec" && request.stateful_vtec.is_some() {
        return Err("stateful stimulus is unavailable to other operations".into());
    }
    if request.operation != "integratedCaptureVtec" && request.integrated_chain.is_some() {
        return Err("integrated stimulus is unavailable to other operations".into());
    }
    if request.allow_assumptions.len()
        > if request.operation == "integratedCaptureVtec" {
            3
        } else {
            2
        }
        || request.allow_assumptions.iter().any(|s| {
            s != ADD_ASSUMPTION
                && s != PRODUCER_ADD_ASSUMPTION
                && !((request.operation == "statefulVtec"
                    || request.operation == "integratedCaptureVtec")
                    && s == crate::stateful_forms::SUBB_OFF_ASSUMPTION)
        })
        || request
            .allow_assumptions
            .iter()
            .collect::<std::collections::HashSet<_>>()
            .len()
            != request.allow_assumptions.len()
    {
        return Err("unsupported or duplicate assumption".into());
    }
    if request.images.is_empty()
        || request.images.len()
            > if request.operation == "checksumBatch" {
                32
            } else if request.operation == "integratedCaptureVtec" {
                3
            } else {
                2
            }
        || request
            .images
            .iter()
            .any(|i| i.rom.is_empty() || i.rom.len() > 65536)
    {
        return Err("invalid image count or size".into());
    }
    match request.operation.as_str() {
        "p28Batch" => {
            if request.synthetic.is_some()
                || request.producer_cases.is_some()
                || request
                    .allow_assumptions
                    .iter()
                    .any(|s| s != ADD_ASSUMPTION)
                || request.scratch_patterns != [0, 85, 170]
                || request.images[0].id != "baseline"
                || request.images.iter().any(|i| i.rom.len() != 32768)
                || request.images.get(1).is_some_and(|i| i.id != "derived")
            {
                return Err("invalid fixed P28 batch contract".into());
            }
        }
        "synthetic" | "checksumSynthetic" => {
            if request.operation == "checksumSynthetic" && !request.allow_assumptions.is_empty() {
                return Err("checksum task permits no instruction assumptions".into());
            }
            if request.images.len() != 1
                || request.scratch_patterns.len() != 1
                || request.producer_cases.is_some()
            {
                return Err("synthetic request requires one image and one scratch pattern".into());
            }
            let c = request
                .synthetic
                .as_ref()
                .ok_or("synthetic contract required")?;
            if c.exit_pcs.is_empty()
                || c.exit_pcs.len() > 16
                || c.allowed_code_ranges.is_empty()
                || c.allowed_code_ranges.len() > 16
                || c.instruction_budget == 0
                || c.instruction_budget > MAX_SYNTHETIC_STEPS
                || c.output_addresses.len() > 32
                || c.data_seeds.len() > 4096
                || c.allowed_code_ranges
                    .iter()
                    .any(|r| r[0] >= r[1] || r[1] > 65536)
            {
                return Err("invalid synthetic bounds".into());
            }
            let usp_address = 0x80 + (c.psw & 7) * 8 + 6;
            let mut seen = std::collections::HashSet::new();
            if c.data_seeds.iter().any(|[a, v]| {
                *v > 255
                    || !seen.insert(*a)
                    || (2..6).contains(a)
                    || *a == usp_address
                    || *a == usp_address + 1
            }) {
                return Err("conflicting or invalid synthetic entry-state seeds".into());
            }
        }
        "producerBatch" => {
            crate::producer::validate_producer_request(request)?;
        }
        "checksumBatch" => crate::checksum::validate_request(request)?,
        "acquisitionSequence" => crate::acquisition::validate_request(request)?,
        "statefulVtec" => crate::stateful::validate_request(request)?,
        "integratedCaptureVtec" => crate::chain::validate_request(request)?,
        _ => return Err("unsupported operation".into()),
    }
    Ok(())
}

pub fn run_request(request: Request) -> Result<Response, String> {
    validate_request(&request)?;
    let mut response = Response::new(request.operation.clone());
    if request.operation == "integratedCaptureVtec" {
        return crate::chain::run(request, response);
    }
    if request.operation == "statefulVtec" {
        return crate::stateful::run(request, response);
    }
    if request.operation == "acquisitionSequence" {
        return crate::acquisition::run_sequence_request(&request, response);
    }
    if request.operation == "producerBatch" {
        return crate::producer::run_producer_batch(&request, response);
    }
    if request.operation == "checksumBatch" {
        return crate::checksum::run_batch(&request, response);
    }
    let allow_add = request
        .allow_assumptions
        .iter()
        .any(|s| s == ADD_ASSUMPTION);
    if request.operation == "synthetic" || request.operation == "checksumSynthetic" {
        let c = request.synthetic.as_ref().expect("validated");
        response
            .entry_contracts
            .push(serde_json::to_value(c).map_err(|e| e.to_string())?);
        let contract = c.into();
        let (mut cpu, mut bus) = seed_machine(
            &request.images[0].rom,
            &contract,
            request.scratch_patterns[0],
        );
        let assumptions: Vec<_> = request
            .allow_assumptions
            .iter()
            .map(String::as_str)
            .collect();
        response.synthetic_result = Some(execute_in_state_with_policy(
            &mut cpu,
            &mut bus,
            &contract,
            &assumptions,
            true,
            if request.operation == "checksumSynthetic" {
                Some(crate::instruction_forms::checksum_form_admission)
            } else {
                None
            },
        ));
        return Ok(response);
    }
    response.entry_contracts = vec![
        serde_json::json!({"id":"compact","entryPc":0x07C7,"exitPcs":[0x0822],"stop":"BeforeInstruction",
            "allowedCodeRanges":[[0x07C7,0x0822]],"psw":0x1101,"lrb":0x40,"usp":0x180,"instructionBudget":128,
            "inputs":["DATA00C4 unsigned LE word","DATA0217.4"],"outputs":["DATA0133","DATA00B8.4"],
            "codeDataSpacesSeparate":true,"freshStatePerCase":true,"interrupts":"NotInjected","peripherals":"Frozen"}),
        serde_json::json!({"id":"threshold","entryPc":0x122C,"exitPcs":[0x126D,0x1281],"stop":"BeforeInstruction",
            "allowedCodeRanges":[[0x122C,0x126D]],"psw":0x0101,"lrb":0x20,"usp":0x280,"instructionBudget":128,
            "inputs":["DATA0133 code","DATA011E.3 context","DATA011E.4 enabled","DATA0131.1/.2 prior"],
            "outputs":["DATA0131.1/.2"],"fixedPreconditions":{"DATA00CC":0,"DATA0131bit0":0},
            "allowedProgramDataReads":[0x6542,0x654A],"codeDataSpacesSeparate":true,"freshStatePerCase":true,
            "interrupts":"NotInjected","peripherals":"Frozen"}),
    ];
    response
        .compact_rows
        .reserve(65536 * 2 * request.scratch_patterns.len());
    for &pattern in &request.scratch_patterns {
        for s in [false, true] {
            for raw in 0..=u16::MAX {
                let contract = compact_contract(raw, s);
                let result =
                    execute_case(&request.images[0].rom, &contract, pattern, allow_add, false);
                let completed = result.status == 0;
                response.compact_rows.push([
                    pattern as i32,
                    raw as i32,
                    i32::from(s),
                    result.status,
                    if completed { result.outputs[0] } else { -1 },
                    if completed {
                        (result.outputs[1] >> 4) & 1
                    } else {
                        -1
                    },
                    i32::from(!result.used_assumptions.is_empty()),
                ]);
                let selected = pattern == 0
                    && !s
                    && [
                        0, 233, 234, 467, 468, 936, 937, 1874, 1875, 3749, 3750, 65535,
                    ]
                    .contains(&raw);
                let failed = result.status >= 2;
                if (selected || failed) && response.diagnostics.len() < MAX_DIAGNOSTICS {
                    response.diagnostics.push(Diagnostic {
                        slice: "compact",
                        image_index: 0,
                        inputs: vec![pattern as i32, raw as i32, i32::from(s)],
                        result: execute_case(
                            &request.images[0].rom,
                            &contract,
                            pattern,
                            allow_add,
                            true,
                        ),
                    });
                }
            }
        }
    }
    response
        .threshold_rows
        .reserve(request.images.len() * request.scratch_patterns.len() * 4096);
    for (image_index, image) in request.images.iter().enumerate() {
        for &pattern in &request.scratch_patterns {
            for code in 0..=u8::MAX {
                for context in 0..2 {
                    for prior in 0..4 {
                        for enabled in [false, true] {
                            let contract = threshold_contract(code, context, prior, enabled);
                            // The ADD hypothesis belongs only to the compact
                            // conversion. Threshold validation has no permitted
                            // unresolved instruction, even in a conditional batch.
                            let result = execute_case(&image.rom, &contract, pattern, false, false);
                            let mut row = [
                                image_index as i32,
                                pattern as i32,
                                code as i32,
                                context as i32,
                                prior as i32,
                                i32::from(enabled),
                                result.status,
                                if result.status == 0 {
                                    (result.outputs[0] >> 1) & 3
                                } else {
                                    -1
                                },
                                -1,
                                -1,
                                -1,
                                -1,
                            ];
                            for (target, read) in row[8..].iter_mut().zip(&result.program_reads) {
                                *target = *read as i32;
                            }
                            // More than the declared two word reads is a contract failure, never silently truncated.
                            if result.program_reads.len() > 4 {
                                row[6] = 2;
                                row[7] = -1;
                            }
                            response.threshold_rows.push(row);
                            let selected = pattern == 0 && code == 0 && prior == 0;
                            if (selected || row[6] >= 2)
                                && response.diagnostics.len() < MAX_DIAGNOSTICS
                            {
                                response.diagnostics.push(Diagnostic {
                                    slice: "threshold",
                                    image_index,
                                    inputs: vec![
                                        pattern as i32,
                                        code as i32,
                                        context as i32,
                                        prior as i32,
                                        i32::from(enabled),
                                    ],
                                    result: execute_case(
                                        &image.rom, &contract, pattern, false, true,
                                    ),
                                });
                            }
                        }
                    }
                }
            }
        }
    }
    Ok(response)
}
