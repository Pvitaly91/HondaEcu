"""Closed M2by policy over the shared atomic M2bx evidence controller."""
from collections import Counter
from hashlib import sha256
from native_below_second_p2 import resume as shared
from .checkpoint import read_checkpoint
from . import corpus
from .oracle import CYCLE_ACCOUNTING

BASE = '832b7c382076a8a441e48d2d19917aa43118eb37'
BRANCH = 'codex/p28-word0196-cal-rt-frame-continuity-m2by'
UNRESOLVED = tuple(value for value in shared.UNRESOLVED
                   if value not in ('RT5688NotExecuted','ReturnFrameNotEstablished')) + (
    'FullNativeCallerSchedulerNotEstablished','PhysicalNativeStackSafetyNotEstablished',
    'NativeDATA0196GenerationOwnerNotEstablished','EnclosingIRQFrameNotEstablished','PostReturn063ECodeNotExecutedInM2by')
ResumeError, PauseRequested = shared.ResumeError, shared.PauseRequested
require, digest, read_json = shared.require, shared.digest, shared.read_json
file_binding, process_identity = shared.file_binding, shared.process_identity


def check_source_join(value):
    fingerprint = shared.transport_api.check_source_join(value)
    require(value.get('milestone') == 'M2by' and value.get('exactBase') == BASE
            and value.get('firmwareReady',False) is False,'ExactM2bySourceWithoutFirmwareAuthorityRequired')
    return fingerprint


def verify_ack(ack,identity,public):
    fields={'kind','schemaVersion','classification','program_sha256','entry_pc','body_pc','return_pc',
            'program_node_count','program_windows','native_generation_ownership','physical_sf_known','hardware_validated'}
    require(type(ack) is dict and set(ack)==fields,'ClosedM2byProgramAcknowledgementRequired')
    expected={'kind':'program_admitted','schemaVersion':1,
        'classification':'ExplicitInventedPublicCalRtFrameContinuityFixture' if public else corpus.MODE,
        'program_sha256':identity['program_sha256'],'entry_pc':corpus.PUBLIC_CALLER if public else corpus.ENTRY_PC,
        'body_pc':corpus.PUBLIC_BASE if public else corpus.BODY_BASE,
        'return_pc':corpus.PUBLIC_RETURN if public else corpus.RETURN_PC,
        'program_node_count':51,'program_windows':identity['program_windows'],
        'native_generation_ownership':False,'physical_sf_known':False,'hardware_validated':False}
    require(ack==expected,'ExactTwoWindowFiftyOneSiteTechnicalAdmissionRequired')


class VerificationRun(shared.VerificationRun):
    MILESTONE,BASE,BRANCH = 'M2by',BASE,BRANCH
    BUDGETS={'A':41}
    PUBLIC_MODE,PRIVATE_MODE=corpus.PUBLIC_MODE,corpus.MODE
    LOCK_NAME='.m2by-runtime.lock.json'
    check_source_join=staticmethod(check_source_join)
    read_checkpoint=staticmethod(read_checkpoint)
    verify_ack=staticmethod(verify_ack)

    def validate_program_domain(self,identity,public):
        require(type(public) is bool,'ExplicitM2byProgramDomainRequired')
        caller,body,ret=(corpus.PUBLIC_CALLER,corpus.PUBLIC_BASE,corpus.PUBLIC_RETURN) if public else (
            corpus.ENTRY_PC,corpus.BODY_BASE,corpus.RETURN_PC)
        windows=identity.get('program_windows')
        require(identity.get('program_base')==body and identity.get('program_end_exclusive')==body+404
                and type(windows) is list and len(windows)==2
                and [(w.get('base'),w.get('end_exclusive'),w.get('byte_count'),w.get('role')) for w in windows]
                    == [(caller,ret,3,'CallerCAL'),(body,body+404,404,'CalleeBodyAndRT')],
                'TwoExactDisjointWindowsWithoutGapPaddingRequired')

    def validate_actual_record(self,index,record):
        actual=record['actual']; outer=actual.get('report',{}); body=outer.get('body',{})
        terminal=corpus.PUBLIC_RETURN if self.public else corpus.RETURN_PC
        require(actual.get('kind')=='cal_rt_continuity_observation' and actual.get('accepted') is True
                and actual.get('actual_successful_step_returns')==41 and outer.get('completed') is True
                and outer.get('cal_instruction_retirements')==1 and outer.get('body_instruction_retirements')==39
                and outer.get('rt_instruction_retirements')==1 and outer.get('post_return_instruction_retirements')==0
                and outer.get('cpu_bus_instances')==1 and body.get('stop_before_pc')==terminal,
                'ActualFreshCalBodyRt41AndStopBeforeReturnRequired')
        frame,consumed=outer.get('stack_frame'),outer.get('stack_return')
        require(type(frame) is dict and type(consumed) is dict and frame.get('retired_instruction')==1
                and frame.get('generation_ordinal')==1 and frame.get('native_write_ordinal')==0
                and consumed.get('retired_instruction')==41
                and consumed.get('consumed_logical_write_ordinal')==frame.get('logical_write_ordinal')
                and consumed.get('consumed_writer_pc')==frame.get('writer_pc')
                and consumed.get('machine_id')==frame.get('machine_id')==1,'FreshSameMachineCalWriterRequired')

    def build_summary(self,raw):
        require(len(self.records)==16 and sum(r['actual']['actual_successful_step_returns'] for r in self.records)==656,
                'ExactlySixteenActualCalRtCasesAnd656RetirementsRequired')
        bodies=[r['actual']['report']['body'] for r in self.records]
        reports=[r['actual']['report'] for r in self.records]
        p2=[e for b in bodies for e in b['peripheral_p2_journal']]
        control=[e for b in bodies for e in b['peripheral_control_journal']]
        return {'schemaVersion':1,'milestone':'M2by','passed':True,'classification':self.mode,
            'corpusKind':self.corpus_kind,'sourceFingerprintSha256':self.fingerprint,'corpusSha256':self.corpus_digest,
            'cases':16,'positiveCases':16,'paths':dict(Counter(c['path'] for c in self.cases)),
            'retiredInstructions':656,'calRetirements':16,'bodyRetirements':624,'rtRetirements':16,'postReturnRetirements':0,
            'cpuBusInstances':16,'freshCalFrameWriters':16,'rtSameMachineFrameConsumptions':16,
            'sameValueCalWrites':sum(r['stack_frame']['same_value'] for r in reports),
            'stackSspSlots':sorted({r['stack_frame']['old_ssp'] for r in reports}),
            'stackLogicalWrites':16,'stackLogicalReads':16,'stackRawByteWrites':32,'stackRawByteReads':32,
            'p2Retirements':32,'functionalPeripheralP2Reads':32,'functionalPeripheralP2Writes':32,
            'sameValueP2Writes':sum(e['same_value'] for e in p2 if e['operation']=='Write'),
            'controlRetirements':64,'functionalPeripheralControlReads':64,'functionalPeripheralControlWrites':32,
            'sameValueControlWrites':sum(e['same_value'] for e in control if e['operation']=='Write'),
            'p2Generations':32,'controlGenerations':32,'sameValueSecondP2Writes':16,'belowRetirements':288,
            'firstMismatch':None,'independentOracle':'PASS','canonicalDecompressedBytes':len(raw),
            'canonicalSha256':sha256(raw).hexdigest(),'expectedSha256':digest(self.expected),
            'fullActualObservationsRetained':True,'canonicalFieldExclusions':[],
            'TechnicalCalRtFrameContinuityVerified':True,'OriginalRomCalRtObserved':not self.public,
            'PublicEquivalentCalRtVerified':self.public,'initialDATA0196Owner':corpus.DATA0196_OWNER,
            'nativeCallerSchedulerEstablished':False,'physicalNativeStackSafetyEstablished':False,
            'physicalSfKnown':False,'strictHistoricalPreservationPass':False,
            'inheritedAuthorizedPreservationExceptions':1,'cycleAccounting':dict(CYCLE_ACCOUNTING),
            'unresolvedStatuses':list(UNRESOLVED),'firmwareReady':False}
