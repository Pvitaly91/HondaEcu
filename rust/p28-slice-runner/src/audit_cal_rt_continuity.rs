//! M2by: closed CAL -> unchanged M2bx body -> actual RT, one production CPU/Bus.
//! No instruction semantics, generic stack authority, or scheduler claim lives here.
use super::{
    below_second_p2::*, original_rom::OriginalNode, p2_handoff::*, post_p2_control::*, Access,
    AuditError, DataEvent, InstructionIdentity, OriginalRomSourceBinding, OriginalRomStep,
    Permissions, ProgramSegment, Result, Session, WriteAccess,
};
use crate::{cpu::Cpu, decoder::Fields};
use serde::Serialize;
use std::collections::BTreeMap;

#[derive(Clone, Copy)]
pub(crate) struct CalRtBudget {
    caller: u16,
    body: u16,
    frame: u16,
}
impl CalRtBudget {
    pub(crate) fn caller_pc(self) -> u16 {
        self.caller
    }
    pub(crate) fn body_pc(self) -> u16 {
        self.body
    }
    pub(crate) fn frame_address(self) -> u16 {
        self.frame
    }
    pub(crate) fn return_pc(self) -> u16 {
        self.caller + 3
    }
    pub(crate) fn rt_pc(self) -> u16 {
        self.body + (0x5688 - 0x54f5)
    }
}

pub struct ClosedCalRtContinuityProgram {
    caller: ProgramSegment,
    segment: ProgramSegment,
    body: ClosedBelowSecondP2Program,
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
impl ClosedCalRtContinuityProgram {
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
            || caller_bytes.len() != 3
            || body_base != 0x54f5
            || body_bytes.len() != 404
        {
            return Err(AuditError::new(
                "CalRtProgramWindowsRejected",
                None,
                "exact unchanged [063B,063E) and [54F5,5689) windows, no relocation or padding",
            ));
        }
        let caller = ProgramSegment::new(caller_base, caller_bytes, caller_sha256)?;
        let segment = ProgramSegment::new(body_base, body_bytes, body_sha256)?;
        let cal = crate::decoder::decode_checked(false, |offset| {
            caller.bytes.get(offset).copied().ok_or_else(|| {
                AuditError::new(
                    "CalRtAdmissionProbeOutsideWindow",
                    None,
                    "strict caller window",
                )
            })
        })?;
        let ret = crate::decoder::decode_checked(false, |offset| {
            segment.bytes.get(403 + offset).copied().ok_or_else(|| {
                AuditError::new("CalRtAdmissionProbeOutsideWindow", None, "strict RT window")
            })
        })?;
        if !cal.is_some_and(|d| {
            d.index == 388
                && d.len == 3
                && d.mnemonic == "CAL addr16"
                && d.fields.addr16 == body_base as u16
        }) || !ret.is_some_and(|d| d.index == 1902 && d.len == 1 && d.mnemonic == "RT")
        {
            return Err(AuditError::new(
                "CalRtBoundaryFormRejected",
                None,
                "primary CAL addr16 and RT only",
            ));
        }
        let prefix = segment.bytes[..403].to_vec();
        let digest = crate::audit_sha256::digest(&prefix);
        let body = ClosedBelowSecondP2Program::admit_host_verified_segment(
            body_base, prefix, &digest, binding,
        )?;
        Ok(Self::assemble(caller, segment, body))
    }
    fn assemble(
        caller: ProgramSegment,
        segment: ProgramSegment,
        body: ClosedBelowSecondP2Program,
    ) -> Self {
        let mut ordered = caller.bytes.to_vec();
        ordered.extend_from_slice(&segment.bytes);
        let identity = crate::audit_sha256::digest(&ordered);
        Self {
            caller,
            segment,
            body,
            identity,
        }
    }
    pub fn explicit_invented_public_fixture() -> Self {
        let body = ClosedBelowSecondP2Program::explicit_invented_public_fixture();
        let caller = vec![0x32, 0x00, 0x64];
        let caller = ProgramSegment::new(
            0x2000,
            caller.clone(),
            &crate::audit_sha256::digest(&caller),
        )
        .expect("invented CAL");
        let mut bytes = body.segment.bytes.to_vec();
        bytes.push(0x01);
        let segment =
            ProgramSegment::new(0x6400, bytes.clone(), &crate::audit_sha256::digest(&bytes))
                .expect("invented body/RT");
        Self::assemble(caller, segment, body)
    }
    pub fn entry_pc(&self) -> u16 {
        self.caller.base as u16
    }
    pub fn body_pc(&self) -> u16 {
        self.segment.base as u16
    }
    pub fn return_pc(&self) -> u16 {
        self.entry_pc() + 3
    }
    pub fn rt_pc(&self) -> u16 {
        self.body.pc(0x5688)
    }
    pub fn program_sha256(&self) -> &str {
        &self.identity
    }
    pub fn classification(&self) -> &'static str {
        if self.body.prefix.p2.native {
            "OriginalRomBytes_TechnicalCalRtFrameContinuity"
        } else {
            "ExplicitInventedPublicCalRtFrameContinuityFixture"
        }
    }
    pub fn program_windows(&self) -> Vec<ProgramWindow> {
        [
            (&self.caller, "CallerCAL"),
            (&self.segment, "CalleeBodyAndRT"),
        ]
        .into_iter()
        .map(|(s, role)| ProgramWindow {
            base: s.base,
            end_exclusive: s.end,
            sha256: s.digest.clone(),
            byte_count: s.bytes.len(),
            role: role.into(),
        })
        .collect()
    }
    fn parts(&self, frame: u16) -> (Vec<OriginalNode>, Vec<u16>, Vec<u16>) {
        let (mut nodes, mut inventory, mut pcs) = self.body.parts();
        let stack = Access {
            address: frame,
            width: 16,
        };
        nodes.push(OriginalNode {
            pc: self.entry_pc(),
            identity: InstructionIdentity {
                index: 388,
                len: 3,
                mnemonic: "CAL addr16".into(),
                dd_before: false,
                dd_after: None,
                fields: Fields {
                    addr16: self.body_pc(),
                    ..Fields::default()
                },
            },
            reachable_dd: vec![false, true],
            successors: vec![self.body_pc()],
            reads: vec![],
            writes: vec![WriteAccess {
                access: stack,
                rmw_required: false,
            }],
        });
        nodes.push(OriginalNode {
            pc: self.rt_pc(),
            identity: InstructionIdentity {
                index: 1902,
                len: 1,
                mnemonic: "RT".into(),
                dd_before: false,
                dd_after: None,
                fields: Fields::default(),
            },
            reachable_dd: vec![false],
            successors: vec![self.return_pc()],
            reads: vec![stack],
            writes: vec![],
        });
        inventory.extend([frame, frame + 1]);
        inventory.sort_unstable();
        pcs.insert(0, self.entry_pc());
        pcs.push(self.rt_pc());
        (nodes, inventory, pcs)
    }
}

pub struct CalRtContinuitySeeds {
    seeds: P2HandoffSeeds,
    frame: u16,
}
impl CalRtContinuitySeeds {
    pub fn new(
        program: &ClosedCalRtContinuityProgram,
        mut data: BTreeMap<u16, u8>,
        pointing: [[u16; 4]; 8],
        r: [u8; 8],
        er: [u16; 4],
        ssp: u16,
    ) -> Result<Self> {
        if !matches!(ssp, 0x0702 | 0x0720 | 0x07fc | 0x07fe) {
            return Err(AuditError::new(
                "CalRtStackSlotRejected",
                Some(i64::from(ssp)),
                "four reviewed even, nonwrapping, disjoint technical stack slots only",
            ));
        }
        let (_, inventory, _) = program.parts(ssp);
        if data.keys().copied().collect::<Vec<_>>() != inventory {
            return Err(AuditError::new(
                "CalRtSeedInventoryRejected",
                None,
                "exact23 body bytes plus two explicit technical frame canaries",
            ));
        }
        let lo = data.remove(&ssp).expect("inventory");
        let hi = data.remove(&(ssp + 1)).expect("inventory");
        let mut seeds = BelowSecondP2Seeds::new(&program.body, data, pointing, r, er)?.0;
        seeds.data.insert(ssp, lo);
        seeds.data.insert(ssp + 1, hi);
        Ok(Self { seeds, frame: ssp })
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct ProgramWindow {
    pub base: u32,
    pub end_exclusive: u32,
    pub sha256: String,
    pub byte_count: usize,
    pub role: String,
}
#[derive(Debug, Clone, Serialize)]
pub struct CalFrame {
    pub machine_id: u64,
    pub writer_pc: u16,
    pub retired_instruction: u64,
    pub old_ssp: u16,
    pub address: u16,
    pub width: u8,
    pub return_pc: u16,
    pub logical_ordinal: u64,
    pub logical_write_ordinal: u64,
    pub raw_ordinals: [u64; 2],
    pub raw_write_ordinals: [u64; 2],
    pub native_write_ordinal: u64,
    pub all_native_ordinal: u64,
    pub generation_ordinal: u64,
    pub source_generation: String,
    pub same_value: bool,
}
#[derive(Debug, Clone, Serialize)]
pub struct RtConsumption {
    pub machine_id: u64,
    pub consumer_pc: u16,
    pub retired_instruction: u64,
    pub ssp_before: u16,
    pub ssp_after: u16,
    pub address: u16,
    pub width: u8,
    pub return_pc: u16,
    pub logical_ordinal: u64,
    pub raw_ordinals: [u64; 2],
    pub all_native_ordinal: u64,
    pub consumed_writer_pc: u16,
    pub consumed_retired_instruction: u64,
    pub consumed_logical_write_ordinal: u64,
}
#[derive(Debug, Clone, Serialize)]
pub struct CalRtContinuityReport {
    pub body: BelowSecondP2Report,
    pub program_windows: Vec<ProgramWindow>,
    pub program_identity: String,
    pub stack_frame: Option<CalFrame>,
    pub stack_return: Option<RtConsumption>,
    pub stack_journal: Vec<DataEvent>,
    pub frame_status: String,
    pub initial_canary_classification: String,
    pub completed: bool,
    pub cal_instruction_retirements: u64,
    pub body_instruction_retirements: u64,
    pub rt_instruction_retirements: u64,
    pub post_return_instruction_retirements: u64,
    pub cpu_bus_instances: u8,
    pub all_native_journal: Vec<[u32; 6]>,
}
pub struct CalRtContinuitySession {
    inner: BelowSecondP2Session,
    context: CalRtBudget,
    windows: Vec<ProgramWindow>,
    identity: String,
    frame: Option<CalFrame>,
    consumed: Option<RtConsumption>,
    fault: Option<AuditError>,
}
impl CalRtContinuitySession {
    pub fn new(
        program: &ClosedCalRtContinuityProgram,
        cpu: Cpu,
        full_psw: u16,
        seeds: CalRtContinuitySeeds,
        path: PostP2ControlPath,
        requested_budget: u8,
        p2_snapshot: P2Snapshot,
        control: ControlSnapshot,
    ) -> Result<Self> {
        control.validate()?;
        p2_snapshot.validate()?;
        if path != PostP2ControlPath::A
            || requested_budget != 41
            || cpu.pc != program.entry_pc()
            || cpu.ssp != seeds.frame
            || cpu.lrb != 0x21
            || cpu.instructions != 0
            || cpu.cycles != 0
        {
            return Err(AuditError::new(
                "CalRtEntryRejected",
                Some(i64::from(cpu.pc)),
                "fresh caller entry, exact41 Below route and reviewed SSP required",
            ));
        }
        let context = CalRtBudget {
            caller: program.entry_pc(),
            body: program.body_pc(),
            frame: seeds.frame,
        };
        let (nodes, inventory, pcs) = program.parts(seeds.frame);
        let mut reads: Vec<_> = nodes
            .iter()
            .filter(|n| pcs.contains(&n.pc))
            .flat_map(|n| n.reads.clone())
            .filter(|a| a.address >= 0x80)
            .collect();
        reads.sort();
        reads.dedup();
        let mut writes: Vec<_> = nodes
            .iter()
            .filter(|n| pcs.contains(&n.pc))
            .flat_map(|n| n.writes.clone())
            .filter(|a| a.access.address >= 0x80)
            .collect();
        writes.sort_by_key(|w| w.access);
        writes.dedup_by_key(|w| w.access);
        let inner = Session::new_cal_rt_admitted(
            copy(&program.caller),
            copy(&program.segment),
            cpu,
            full_psw,
            Permissions::new(reads, writes)?,
            context,
        )?;
        let values = [control.tcon0, control.trnsit_implemented_flags];
        let mut inner = P2HandoffSession::from_admitted(
            &program.body.prefix.p2,
            inner,
            seeds.seeds,
            P2HandoffPath::A,
            p2_snapshot,
            nodes,
            inventory,
            pcs,
            program.return_pc(),
            Some(values),
        )?;
        inner.inner.bus.begin_all_native();
        Ok(Self {
            inner: BelowSecondP2Session {
                inner: PostP2ControlSession {
                    inner,
                    initial: control,
                    last_control: values,
                    control_steps: vec![],
                    native_control: vec![],
                    classification: program.classification().into(),
                },
            },
            context,
            windows: program.program_windows(),
            identity: program.identity.clone(),
            frame: None,
            consumed: None,
            fault: None,
        })
    }
    fn session(&mut self) -> &mut Session {
        &mut self.inner.inner.inner.inner
    }
    fn reject(&mut self, code: &str, detail: &str) -> AuditError {
        let error = AuditError::new(code, None, detail);
        self.fault = Some(error.clone());
        self.session()
            .bus
            .audit
            .as_ref()
            .expect("installed")
            .latch_fault(error)
    }
    fn current_frame(&mut self) -> Result<()> {
        let frame = self.frame.clone().ok_or_else(|| {
            AuditError::new(
                "CalRtFreshFrameRequired",
                None,
                "actual current CAL writer missing",
            )
        })?;
        let audit = self
            .session()
            .bus
            .audit
            .as_ref()
            .expect("installed")
            .report();
        let overlapping: Vec<_> = audit
            .data_events
            .iter()
            .filter(|e| {
                e.phase == "Functional"
                    && e.serviced
                    && e.operation == "Write"
                    && u32::from(e.address) < u32::from(frame.address) + 2
                    && u32::from(e.address) + u32::from(e.width / 8) > u32::from(frame.address)
            })
            .collect();
        if overlapping.len() != 1
            || overlapping[0].ordinal != frame.logical_ordinal
            || overlapping[0].write_ordinal != Some(frame.logical_write_ordinal)
            || overlapping[0].value != Some(frame.return_pc)
            || overlapping[0].pc != Some(frame.writer_pc)
        {
            return Err(self.reject(
                "CalRtFrameWriterGenerationChanged",
                "no overlapping writer between current CAL and RT",
            ));
        }
        let native = self.session().bus.all_native_snapshot();
        let native_overlaps: Vec<_> = native
            .iter()
            .enumerate()
            .filter(|(_, row)| {
                row[0] == 0
                    && row[4] == 1
                    && row[2] < u32::from(frame.address) + 2
                    && row[2] + row[3] / 8 > u32::from(frame.address)
            })
            .collect();
        if native_overlaps.len() != 1
            || native_overlaps[0].0 as u64 != frame.all_native_ordinal
            || *native_overlaps[0].1
                != [
                    0,
                    u32::from(frame.writer_pc),
                    u32::from(frame.address),
                    16,
                    1,
                    u32::from(frame.return_pc),
                ]
        {
            return Err(self.reject("CalRtNativeFrameWriterGenerationChanged",
                "same-value or partial overlapping native writes create another generation and cannot be deduplicated"));
        }
        Ok(())
    }
    pub fn step(&mut self) -> Result<OriginalRomStep> {
        if let Some(e) = &self.fault {
            return Err(e.clone());
        }
        let count = self.session().cpu.instructions;
        if count > 0 && count <= 40 {
            if self.session().cpu.ssp != self.context.frame - 2 {
                return Err(self.reject(
                    "CalRtStackPointerContinuityRejected",
                    "retained decremented SSP until actual RT",
                ));
            }
            self.current_frame()?;
        }
        let step = self.inner.step()?;
        let audit = self
            .session()
            .bus
            .audit
            .as_ref()
            .expect("installed")
            .report();
        let native = self.session().bus.all_native_snapshot();
        if step.index == 1 {
            let events = &audit.data_events[step.logical_span[0]..step.logical_span[1]];
            let e = events.first().ok_or_else(|| {
                AuditError::new("CalRtFrameWriteMissing", None, "actual CAL write")
            })?;
            let raw: Vec<_> = audit
                .raw_data_events
                .iter()
                .filter(|r| r.logical_ordinal == e.ordinal)
                .collect();
            if events.len() != 1
                || e.operation != "Write"
                || !e.serviced
                || e.address != self.context.frame
                || e.width != 16
                || e.value != Some(self.context.return_pc())
                || e.write_ordinal != Some(57)
                || raw.len() != 2
                || raw.iter().any(|r| !r.serviced || r.operation != "Write")
                || raw[0].address != self.context.frame
                || raw[1].address != self.context.frame + 1
                || raw[0].value != Some(self.context.return_pc() as u8)
                || raw[1].value != Some((self.context.return_pc() >> 8) as u8)
                || step.before.cpu.ssp != self.context.frame
                || step.after.cpu.ssp != self.context.frame - 2
                || step.outcome.pc_before != self.context.caller
                || step.outcome.pc_after != self.context.body
                || step.full_psw_before != step.full_psw_after
                || step.after.cpu.sf
                || step.before.cpu.a != step.after.cpu.a
                || step.before.cpu.lrb != step.after.cpu.lrb
            {
                return Err(self.reject(
                    "CalRtFrameWriteMismatch",
                    "actual CAL state/word/LE/current writer evidence required",
                ));
            }
            if native.as_slice()
                != [[
                    0,
                    u32::from(self.context.caller),
                    u32::from(self.context.frame),
                    16,
                    1,
                    u32::from(self.context.return_pc()),
                ]]
            {
                return Err(self.reject(
                    "CalRtNativeFrameWriteMissing",
                    "same actual CAL word writer must exist in all-native observation",
                ));
            }
            self.frame = Some(CalFrame {
                machine_id: 1,
                writer_pc: self.context.caller,
                retired_instruction: 1,
                old_ssp: self.context.frame,
                address: self.context.frame,
                width: 16,
                return_pc: self.context.return_pc(),
                logical_ordinal: e.ordinal,
                logical_write_ordinal: 57,
                raw_ordinals: [raw[0].ordinal, raw[1].ordinal],
                raw_write_ordinals: [
                    raw[0].write_ordinal.expect("actual write"),
                    raw[1].write_ordinal.expect("actual write"),
                ],
                native_write_ordinal: (native.iter().filter(|row| row[4] == 1).count() - 1) as u64,
                all_native_ordinal: 0,
                generation_ordinal: 1,
                source_generation: "CurrentExecutionCAL".into(),
                same_value: e.same_value.expect("write"),
            });
        }
        if step.index == 41 {
            self.current_frame()?;
            let frame = self.frame.as_ref().expect("fresh generation");
            let events = &audit.data_events[step.logical_span[0]..step.logical_span[1]];
            let e = events
                .first()
                .ok_or_else(|| AuditError::new("CalRtReturnReadMissing", None, "actual RT read"))?;
            let raw: Vec<_> = audit
                .raw_data_events
                .iter()
                .filter(|r| r.logical_ordinal == e.ordinal)
                .collect();
            if events.len() != 1
                || e.operation != "Read"
                || !e.serviced
                || e.address != frame.address
                || e.width != 16
                || e.value != Some(frame.return_pc)
                || raw.len() != 2
                || raw.iter().any(|r| !r.serviced || r.operation != "Read")
                || raw[0].address != frame.address
                || raw[1].address != frame.address + 1
                || raw[0].value != Some(frame.return_pc as u8)
                || raw[1].value != Some((frame.return_pc >> 8) as u8)
                || step.before.cpu.ssp != frame.old_ssp - 2
                || step.after.cpu.ssp != frame.old_ssp
                || step.outcome.pc_before != self.context.rt_pc()
                || step.outcome.pc_after != frame.return_pc
                || step.full_psw_before != step.full_psw_after
                || step.after.cpu.sf
                || step.before.cpu.a != step.after.cpu.a
                || step.before.cpu.lrb != step.after.cpu.lrb
            {
                return Err(self.reject("CalRtReturnConsumptionMismatch","actual RT must consume current CAL frame, retain callee A/LRB/PSW and stop before return PC"));
            }
            if native.last()
                != Some(&[
                    0,
                    u32::from(self.context.rt_pc()),
                    u32::from(frame.address),
                    16,
                    0,
                    u32::from(frame.return_pc),
                ])
            {
                return Err(self.reject(
                    "CalRtNativeReturnReadMissing",
                    "actual RT word read must be the final all-native observation",
                ));
            }
            self.consumed = Some(RtConsumption {
                machine_id: 1,
                consumer_pc: self.context.rt_pc(),
                retired_instruction: 41,
                ssp_before: step.before.cpu.ssp,
                ssp_after: step.after.cpu.ssp,
                address: frame.address,
                width: 16,
                return_pc: frame.return_pc,
                logical_ordinal: e.ordinal,
                raw_ordinals: [raw[0].ordinal, raw[1].ordinal],
                all_native_ordinal: (native.len() - 1) as u64,
                consumed_writer_pc: frame.writer_pc,
                consumed_retired_instruction: frame.retired_instruction,
                consumed_logical_write_ordinal: frame.logical_write_ordinal,
            });
        }
        Ok(step)
    }
    pub fn report(&mut self) -> Result<CalRtContinuityReport> {
        let body = self.inner.report()?;
        let count = body.prefix.p2.steps.len() as u64;
        let stack_journal = body
            .prefix
            .p2
            .audit
            .data_events
            .iter()
            .filter(|e| e.phase == "Functional" && e.address == self.context.frame)
            .cloned()
            .collect::<Vec<_>>();
        let completed = body.prefix.p2.completed
            && self.frame.is_some()
            && self.consumed.is_some()
            && count == 41
            && self.fault.is_none()
            && stack_journal.len() == 2;
        let frame_status = if completed {
            "CallerFrameConsumedByActualRT"
        } else if self.frame.is_some() {
            "CallerFrameEstablishedPendingReturn"
        } else {
            "CallerFrameNotObserved"
        };
        let all_native_journal = self.session().bus.all_native_snapshot();
        Ok(CalRtContinuityReport {
            body,
            program_windows: self.windows.clone(),
            program_identity: self.identity.clone(),
            stack_frame: self.frame.clone(),
            stack_return: self.consumed.clone(),
            stack_journal,
            frame_status: frame_status.into(),
            initial_canary_classification: "TechnicalPreexistingCanaryNotFrame".into(),
            completed,
            cal_instruction_retirements: count.min(1),
            body_instruction_retirements: count.saturating_sub(1).min(39),
            rt_instruction_retirements: u64::from(count == 41),
            post_return_instruction_retirements: 0,
            cpu_bus_instances: 1,
            all_native_journal,
        })
    }
}

#[cfg(test)]
#[path = "audit_cal_rt_continuity_tests.rs"]
mod tests;
