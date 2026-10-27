//! M2bz: one retained audited CAL/body/RT machine through eight selector steps.
//! Instruction semantics remain exclusively in the existing production Exec.
use super::{
    cal_rt_continuity::{CalRtBudget, CalRtContinuityReport, ProgramWindow},
    original_rom::OriginalNode,
    Access, AuditError, CalRtContinuitySeeds, CalRtContinuitySession, ClosedCalRtContinuityProgram,
    ControlSnapshot, DataEvent, InstructionIdentity, OriginalRomSourceBinding, OriginalRomStep,
    P2Snapshot, PostP2ControlPath, ProgramSegment, Result, Session, WriteAccess,
};
use crate::{cpu::Cpu, decoder::Fields};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

pub const SELECTOR_SNAPSHOT_CLASSIFICATION: &str =
    "RawSoftwareSnapshot0..3_OnceOnly_InitialGenerationNone";
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SelectorSnapshot {
    pub value: u8,
    pub classification: String,
}
impl SelectorSnapshot {
    fn validate(&self) -> Result<()> {
        if self.value > 3 || self.classification != SELECTOR_SNAPSHOT_CLASSIFICATION {
            return Err(AuditError::new(
                "PostReturnSelectorSnapshotRejected",
                None,
                "one explicit technical selector0..3 snapshot without initial native generation",
            ));
        }
        Ok(())
    }
}
pub struct ClosedPostReturnSelectorProgram {
    caller: ProgramSegment,
    parent: ClosedCalRtContinuityProgram,
    identity: String,
}
fn copy(segment: &ProgramSegment) -> ProgramSegment {
    ProgramSegment {
        base: segment.base,
        end: segment.end,
        bytes: segment.bytes.clone(),
        digest: segment.digest.clone(),
    }
}
impl ClosedPostReturnSelectorProgram {
    pub fn admit_host_verified_segments(
        caller_base: u32,
        caller_bytes: Vec<u8>,
        caller_sha256: &str,
        body_base: u32,
        body_bytes: Vec<u8>,
        body_sha256: &str,
        binding: OriginalRomSourceBinding,
    ) -> Result<Self> {
        if caller_base != 0x063b
            || caller_bytes.len() != 17
            || body_base != 0x54f5
            || body_bytes.len() != 404
        {
            return Err(AuditError::new(
                "PostReturnProgramWindowsRejected",
                None,
                "unchanged17-byte caller/post-return and404-byte callee windows only",
            ));
        }
        let caller = ProgramSegment::new(caller_base, caller_bytes, caller_sha256)?;
        let prefix = caller.bytes[..3].to_vec();
        let digest = crate::audit_sha256::digest(&prefix);
        let parent = ClosedCalRtContinuityProgram::admit_host_verified_segments(
            caller_base,
            prefix,
            &digest,
            body_base,
            body_bytes,
            body_sha256,
            binding,
        )?;
        for node in post_nodes(0x063b, 0x013c, 0x0128) {
            let start = usize::from(node.pc - 0x063b);
            let decoded = crate::decoder::decode_checked(false, |offset| {
                caller.bytes.get(start + offset).copied().ok_or_else(|| {
                    AuditError::new(
                        "PostReturnAdmissionProbeOutsideWindow",
                        None,
                        "strict immutable caller window",
                    )
                })
            })?
            .ok_or_else(|| {
                AuditError::new(
                    "PostReturnFormRejected",
                    Some(i64::from(node.pc)),
                    "reviewed exact post-return form required",
                )
            })?;
            let f = decoded.fields;
            let e = node.identity.fields;
            if decoded.index != node.identity.index
                || decoded.len != node.identity.len
                || decoded.mnemonic != node.identity.mnemonic
                || decoded.dd_after != node.identity.dd_after
                || f.n8 != e.n8
                || f.n8_alt != e.n8_alt
                || f.n16 != e.n16
                || f.n16_alt != e.n16_alt
                || f.s8 != e.s8
                || f.rel8 != e.rel8
                || f.addr16 != e.addr16
            {
                return Err(AuditError::new(
                    "PostReturnFormRejected",
                    Some(i64::from(node.pc)),
                    "exact closed instruction/operand identity required",
                ));
            }
        }
        Ok(Self::assemble(caller, parent))
    }
    fn assemble(caller: ProgramSegment, parent: ClosedCalRtContinuityProgram) -> Self {
        let mut bytes = caller.bytes.to_vec();
        bytes.extend_from_slice(&parent.segment.bytes);
        Self {
            caller,
            parent,
            identity: crate::audit_sha256::digest(&bytes),
        }
    }
    pub fn explicit_invented_public_fixture() -> Self {
        let parent = ClosedCalRtContinuityProgram::explicit_invented_public_fixture();
        let mut bytes = parent.caller.bytes.to_vec();
        for node in post_nodes(0x2000, 0x0140, 0x0130) {
            let f = node.identity.fields;
            // Independently placed ISA cells at invented addresses, never an
            // OEM window copied from the private source.
            let encoded = match node.identity.index {
                747 => vec![0xf4, f.n8],
                2293 => vec![0x88],
                322 => vec![0xd6, f.n8],
                2172 => vec![0xc4, f.n8, 0x11],
                668 => vec![0xa8],
                739 => vec![0x78],
                2301 => vec![0xd4, f.n8],
                _ => unreachable!("eight closed selector forms"),
            };
            bytes.extend_from_slice(&encoded);
        }
        let digest = crate::audit_sha256::digest(&bytes);
        Self::assemble(
            ProgramSegment::new(0x2000, bytes, &digest).expect("invented17-byte caller"),
            parent,
        )
    }
    pub fn entry_pc(&self) -> u16 {
        self.caller.base as u16
    }
    pub fn body_pc(&self) -> u16 {
        self.parent.body_pc()
    }
    pub fn return_pc(&self) -> u16 {
        self.entry_pc() + 3
    }
    pub fn stop_before_pc(&self) -> u16 {
        self.entry_pc() + 17
    }
    pub fn selector_address(&self) -> u16 {
        if self.entry_pc() == 0x063b {
            0x013c
        } else {
            0x0140
        }
    }
    fn history_address(&self) -> u16 {
        if self.entry_pc() == 0x063b {
            0x0128
        } else {
            0x0130
        }
    }
    pub fn program_sha256(&self) -> &str {
        &self.identity
    }
    pub fn classification(&self) -> &'static str {
        if self.entry_pc() == 0x063b {
            "OriginalRomBytes_TechnicalPostReturnSelectorContinuity"
        } else {
            "ExplicitInventedPublicPostReturnSelectorFixture"
        }
    }
    pub fn program_windows(&self) -> Vec<ProgramWindow> {
        let body = &self.parent.segment;
        vec![
            ProgramWindow {
                base: self.caller.base,
                end_exclusive: self.caller.end,
                sha256: self.caller.digest.clone(),
                byte_count: 17,
                role: "CallerCALAndPostReturn".into(),
            },
            ProgramWindow {
                base: body.base,
                end_exclusive: body.end,
                sha256: body.digest.clone(),
                byte_count: 404,
                role: "CalleeBodyAndRT".into(),
            },
        ]
    }
    fn parts(&self, frame: u16) -> (Vec<OriginalNode>, Vec<u16>, Vec<u16>) {
        let (mut nodes, mut inventory, mut pcs) = self.parent.parts(frame);
        let tail = post_nodes(
            self.entry_pc(),
            self.selector_address(),
            self.history_address(),
        );
        pcs.extend(tail.iter().map(|node| node.pc));
        nodes.extend(tail);
        inventory.push(self.selector_address());
        inventory.sort_unstable();
        (nodes, inventory, pcs)
    }
}
fn post_nodes(caller: u16, selector: u16, history: u16) -> Vec<OriginalNode> {
    let pc = |native: u16| caller + (native - 0x063b);
    let read = |address| Access { address, width: 8 };
    let write = |address, rmw_required| WriteAccess {
        access: Access { address, width: 8 },
        rmw_required,
    };
    let mut result = vec![];
    let mut add = |site, index, len, name: &str, n8, after, next, reads, writes| {
        result.push(OriginalNode {
            pc: pc(site),
            identity: InstructionIdentity {
                index,
                len,
                mnemonic: name.into(),
                dd_before: false,
                dd_after: after,
                fields: Fields {
                    n8,
                    ..Fields::default()
                },
            },
            reachable_dd: vec![false],
            successors: vec![pc(next)],
            reads,
            writes,
        })
    };
    add(
        0x063e,
        747,
        2,
        "LB A, off N8",
        selector as u8,
        Some(false),
        0x0640,
        vec![read(selector)],
        vec![],
    );
    add(
        0x0640,
        2293,
        1,
        "STB A, r0",
        0,
        None,
        0x0641,
        vec![],
        vec![write(0x0108, false)],
    );
    add(
        0x0641,
        322,
        2,
        "ANDB A, #N8",
        1,
        None,
        0x0643,
        vec![],
        vec![],
    );
    add(
        0x0643,
        2172,
        3,
        "SBR off N8",
        history as u8,
        None,
        0x0646,
        vec![read(history)],
        vec![write(history, true)],
    );
    add(
        0x0646,
        668,
        1,
        "INCB r0",
        0,
        None,
        0x0647,
        vec![read(0x0108)],
        vec![write(0x0108, true)],
    );
    add(
        0x0647,
        739,
        1,
        "LB A, r0",
        0,
        Some(false),
        0x0648,
        vec![read(0x0108)],
        vec![],
    );
    add(
        0x0648,
        322,
        2,
        "ANDB A, #N8",
        3,
        None,
        0x064a,
        vec![],
        vec![],
    );
    add(
        0x064a,
        2301,
        2,
        "STB A, off N8",
        selector as u8,
        None,
        0x064c,
        vec![],
        vec![write(selector, false)],
    );
    result
}
pub struct PostReturnSelectorSeeds {
    parent: CalRtContinuitySeeds,
    snapshot: SelectorSnapshot,
}
impl PostReturnSelectorSeeds {
    pub fn new(
        program: &ClosedPostReturnSelectorProgram,
        data: BTreeMap<u16, u8>,
        pointing: [[u16; 4]; 8],
        r: [u8; 8],
        er: [u16; 4],
        ssp: u16,
        snapshot: SelectorSnapshot,
    ) -> Result<Self> {
        snapshot.validate()?;
        let mut parent = CalRtContinuitySeeds::new(&program.parent, data, pointing, r, er, ssp)?;
        if parent
            .seeds
            .data
            .insert(program.selector_address(), snapshot.value)
            .is_some()
        {
            return Err(AuditError::new(
                "PostReturnSelectorSeedCollision",
                None,
                "selector snapshot is initialized once, never duplicated in DATA",
            ));
        }
        Ok(Self { parent, snapshot })
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct SelectorRead {
    pub machine_id: u64,
    pub reader_pc: u16,
    pub retired_instruction: u64,
    pub address: u16,
    pub width: u8,
    pub value: u8,
    pub logical_ordinal: u64,
    pub raw_ordinal: u64,
    pub all_native_ordinal: u64,
    pub source_classification: String,
    pub native_generation: Option<SelectorGeneration>,
}
#[derive(Debug, Clone, Serialize)]
pub struct SelectorGeneration {
    pub machine_id: u64,
    pub event_index: u64,
    pub writer_pc: u16,
    pub retired_instruction: u64,
    pub generation_ordinal: u64,
    pub address: u16,
    pub width: u8,
    pub logical_ordinal: u64,
    pub logical_write_ordinal: u64,
    pub raw_ordinal: u64,
    pub raw_write_ordinal: u64,
    pub all_native_ordinal: u64,
    pub native_write_ordinal: u64,
    pub value: u8,
    pub source_generation: String,
}
#[derive(Debug, Clone, Serialize)]
pub struct PostReturnSelectorReport {
    pub prefix: CalRtContinuityReport,
    pub selector_snapshot: SelectorSnapshot,
    pub initial_selector_generation: Option<SelectorGeneration>,
    pub selector_initial: u8,
    pub selector_final: u8,
    pub selector_read: Option<SelectorRead>,
    pub selector_generation: Option<SelectorGeneration>,
    pub history0128_before: Option<u8>,
    pub history0128_after: Option<u8>,
    pub history0128_selected_bit: Option<u8>,
    pub history0128_rmw: Vec<DataEvent>,
    pub history0128_generation: Option<SelectorGeneration>,
    pub local_r0_before: Option<u8>,
    pub local_r0_final: u8,
    pub post_return_instruction_retirements: u64,
    pub total_instruction_retirements: u64,
    pub completed: bool,
    pub selector_generation_available_for_future_reader: bool,
    pub native_next_event_handoff_verified: bool,
    pub branch064c_retired: bool,
}
pub struct PostReturnSelectorSession {
    parent: CalRtContinuitySession,
    snapshot: SelectorSnapshot,
    caller: u16,
    selector: u16,
    history: u16,
    read: Option<SelectorRead>,
    generation: Option<SelectorGeneration>,
    history_generation: Option<SelectorGeneration>,
    history_rmw: Vec<DataEvent>,
    history_before: Option<u8>,
    history_after: Option<u8>,
    selected_bit: Option<u8>,
    r0_before: Option<u8>,
}
impl PostReturnSelectorSession {
    pub fn new(
        program: &ClosedPostReturnSelectorProgram,
        cpu: Cpu,
        full_psw: u16,
        seeds: PostReturnSelectorSeeds,
        path: PostP2ControlPath,
        budget: u8,
        p2: P2Snapshot,
        control: ControlSnapshot,
    ) -> Result<Self> {
        if path != PostP2ControlPath::A
            || budget != 49
            || cpu.pc != program.entry_pc()
            || cpu.ssp != seeds.parent.frame
            || cpu.lrb != 0x21
            || cpu.instructions != 0
            || cpu.cycles != 0
        {
            return Err(AuditError::new(
                "PostReturnEntryRejected",
                Some(i64::from(cpu.pc)),
                "one fresh caller entry and exact49-step selector route only",
            ));
        }
        let context = CalRtBudget::post_return(
            program.entry_pc(),
            program.body_pc(),
            seeds.parent.frame,
            program.selector_address(),
        )?;
        let parts = program.parts(seeds.parent.frame);
        let parent = CalRtContinuitySession::from_source(
            &program.parent,
            cpu,
            full_psw,
            seeds.parent,
            p2,
            control,
            copy(&program.caller),
            context,
            parts,
            program.program_windows(),
            program.identity.clone(),
            program.classification(),
        )?;
        Ok(Self {
            parent,
            snapshot: seeds.snapshot,
            caller: program.entry_pc(),
            selector: program.selector_address(),
            history: program.history_address(),
            read: None,
            generation: None,
            history_generation: None,
            history_rmw: vec![],
            history_before: None,
            history_after: None,
            selected_bit: None,
            r0_before: None,
        })
    }
    fn session(&mut self) -> &mut Session {
        self.parent.session()
    }
    fn check_selector_writer_history(&mut self) -> Result<()> {
        let native = self.session().bus.all_native_snapshot();
        let overlapping: Vec<_> = native
            .iter()
            .enumerate()
            .filter(|(_, r)| {
                r[0] == 0
                    && r[4] == 1
                    && r[2] < u32::from(self.selector) + 1
                    && r[2] + r[3] / 8 > u32::from(self.selector)
            })
            .collect();
        if let Some(g) = &self.generation {
            if overlapping.len() != 1
                || overlapping[0].0 as u64 != g.all_native_ordinal
                || *overlapping[0].1
                    != [
                        0,
                        u32::from(g.writer_pc),
                        u32::from(self.selector),
                        8,
                        1,
                        u32::from(g.value),
                    ]
            {
                return Err(self.parent.reject("PostReturnSelectorGenerationChanged","selector generation is the one actual final writer, including same-value writes"));
            }
        } else if !overlapping.is_empty() {
            return Err(self.parent.reject(
                "PostReturnUnexpectedSelectorWriter",
                "technical initial snapshot has no native writer before actual final STB",
            ));
        }
        Ok(())
    }
    fn generation(
        &mut self,
        step: &OriginalRomStep,
        address: u16,
        label: &str,
    ) -> Result<SelectorGeneration> {
        let audit = self
            .session()
            .bus
            .audit
            .as_ref()
            .expect("installed")
            .report();
        let events: Vec<_> = audit.data_events[step.logical_span[0]..step.logical_span[1]]
            .iter()
            .filter(|e| e.operation == "Write")
            .collect();
        if events.len() != 1
            || !events[0].serviced
            || events[0].address != address
            || events[0].width != 8
        {
            return Err(self.parent.reject(
                "PostReturnWriterEvidenceRejected",
                "one actual admitted byte writer required",
            ));
        }
        let e = events[0];
        let raw: Vec<_> = audit
            .raw_data_events
            .iter()
            .filter(|r| r.logical_ordinal == e.ordinal)
            .collect();
        if raw.len() != 1
            || !raw[0].serviced
            || raw[0].address != address
            || raw[0].value.map(u16::from) != e.value
        {
            return Err(self.parent.reject(
                "PostReturnWriterRawLinkRejected",
                "one raw byte must link to the actual logical write",
            ));
        }
        let native = self.session().bus.all_native_snapshot();
        let matches: Vec<_> = native
            .iter()
            .enumerate()
            .filter(|(_, r)| {
                **r == [
                    0,
                    u32::from(step.outcome.pc_before),
                    u32::from(address),
                    8,
                    1,
                    u32::from(e.value.expect("actual value")),
                ]
            })
            .collect();
        if matches.len() != 1 {
            return Err(self.parent.reject(
                "PostReturnWriterNativeLinkRejected",
                "actual all-native writer identity required",
            ));
        }
        let ordinal = matches[0].0;
        Ok(SelectorGeneration {
            machine_id: 1,
            event_index: 0,
            writer_pc: step.outcome.pc_before,
            retired_instruction: step.index,
            generation_ordinal: 1,
            address,
            width: 8,
            logical_ordinal: e.ordinal,
            logical_write_ordinal: e.write_ordinal.expect("write"),
            raw_ordinal: raw[0].ordinal,
            raw_write_ordinal: raw[0].write_ordinal.expect("raw write"),
            all_native_ordinal: ordinal as u64,
            native_write_ordinal: (native[..=ordinal].iter().filter(|r| r[4] == 1).count() - 1)
                as u64,
            value: e.value.expect("value") as u8,
            source_generation: label.into(),
        })
    }
    pub fn step(&mut self) -> Result<OriginalRomStep> {
        self.check_selector_writer_history()?;
        let step = self.parent.step()?;
        if step.index == 42 {
            let audit = self
                .session()
                .bus
                .audit
                .as_ref()
                .expect("installed")
                .report();
            let events = &audit.data_events[step.logical_span[0]..step.logical_span[1]];
            if events.len() != 1
                || events[0].operation != "Read"
                || events[0].address != self.selector
                || events[0].width != 8
                || !events[0].serviced
                || events[0].value != Some(u16::from(self.snapshot.value))
            {
                return Err(self.parent.reject("PostReturnInitialSelectorReadRejected","first post-RT LB reads the once-initial technical snapshot without imported generation"));
            }
            let e = &events[0];
            let raw: Vec<_> = audit
                .raw_data_events
                .iter()
                .filter(|r| r.logical_ordinal == e.ordinal)
                .collect();
            let native = self.session().bus.all_native_snapshot();
            if raw.len() != 1
                || !raw[0].serviced
                || raw[0].value != Some(self.snapshot.value)
                || native.last()
                    != Some(&[
                        0,
                        u32::from(self.caller + 3),
                        u32::from(self.selector),
                        8,
                        0,
                        u32::from(self.snapshot.value),
                    ])
            {
                return Err(self.parent.reject(
                    "PostReturnSelectorReadLinkRejected",
                    "actual logical/raw/all-native read agreement required",
                ));
            }
            self.r0_before = Some(step.before.ram[usize::from(0x0108 - step.before.ram_range[0])]);
            self.read = Some(SelectorRead {
                machine_id: 1,
                reader_pc: step.outcome.pc_before,
                retired_instruction: 42,
                address: self.selector,
                width: 8,
                value: self.snapshot.value,
                logical_ordinal: e.ordinal,
                raw_ordinal: raw[0].ordinal,
                all_native_ordinal: (native.len() - 1) as u64,
                source_classification: SELECTOR_SNAPSHOT_CLASSIFICATION.into(),
                native_generation: None,
            });
        }
        if step.index == 45 {
            let audit = self
                .session()
                .bus
                .audit
                .as_ref()
                .expect("installed")
                .report();
            let rows = &audit.data_events[step.logical_span[0]..step.logical_span[1]];
            if rows.len() != 2
                || rows[0].operation != "Read"
                || rows[1].operation != "Write"
                || rows
                    .iter()
                    .any(|e| !e.serviced || e.address != self.history || e.width != 8)
            {
                return Err(self.parent.reject(
                    "PostReturnHistoryRmwRejected",
                    "one actual ordered SBR byte read/write pair required",
                ));
            }
            self.history_before = rows[0].value.map(|v| v as u8);
            self.history_after = rows[1].value.map(|v| v as u8);
            self.selected_bit = Some((step.before.cpu.a & 7) as u8);
            self.history_rmw = rows.to_vec();
            self.history_generation = Some(self.generation(
                &step,
                self.history,
                "CurrentExecutionNativeHistoryWriter0643",
            )?);
        }
        if step.index == 49 {
            self.generation = Some(self.generation(
                &step,
                self.selector,
                "CurrentExecutionNativeSelectorWriter064A",
            )?);
        }
        self.check_selector_writer_history()?;
        Ok(step)
    }
    pub fn report(&mut self) -> Result<PostReturnSelectorReport> {
        self.check_selector_writer_history()?;
        let prefix = self.parent.report()?;
        let count = prefix.body.prefix.p2.steps.len() as u64;
        let current = &prefix.body.prefix.p2.current;
        let selector_final = current.ram[usize::from(self.selector - current.ram_range[0])];
        let local_r0_final = current.ram[usize::from(0x0108 - current.ram_range[0])];
        let completed = prefix.completed
            && count == 49
            && self.read.is_some()
            && self.generation.is_some()
            && self.history_generation.is_some();
        Ok(PostReturnSelectorReport {
            prefix,
            selector_snapshot: self.snapshot.clone(),
            initial_selector_generation: None,
            selector_initial: self.snapshot.value,
            selector_final,
            selector_read: self.read.clone(),
            selector_generation: self.generation.clone(),
            history0128_before: self.history_before,
            history0128_after: self.history_after,
            history0128_selected_bit: self.selected_bit,
            history0128_rmw: self.history_rmw.clone(),
            history0128_generation: self.history_generation.clone(),
            local_r0_before: self.r0_before,
            local_r0_final,
            post_return_instruction_retirements: count.saturating_sub(41).min(8),
            total_instruction_retirements: count,
            completed,
            selector_generation_available_for_future_reader: self.generation.is_some(),
            native_next_event_handoff_verified: false,
            branch064c_retired: false,
        })
    }
}

#[cfg(test)]
#[path = "audit_post_return_selector_tests.rs"]
mod tests;
