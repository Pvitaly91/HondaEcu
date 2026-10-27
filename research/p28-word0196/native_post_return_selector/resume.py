"""Closed M2bz49 policy over the unchanged, authenticated M2by resume machinery."""
from collections import Counter
from hashlib import sha256
from native_cal_rt_continuity import resume as previous
from .checkpoint import read_checkpoint
from . import corpus
from .oracle import CYCLE_ACCOUNTING

BASE='82c34c0465a5d92ce5cc30f2daf47f24174a10d5'
BRANCH='codex/p28-word0196-post-return-selector-continuity-m2bz'
UNRESOLVED=tuple(v for v in previous.UNRESOLVED if v!='PostReturn063ECodeNotExecutedInM2by')+(
    'InitialDATA013CNativeOwnerNotEstablished','Branch064CNotExecuted','NativeNextEventSelectorHandoffNotEstablished')
ResumeError,PauseRequested=previous.ResumeError,previous.PauseRequested
require,digest,read_json=previous.require,previous.digest,previous.read_json
file_binding,process_identity=previous.file_binding,previous.process_identity


def check_source_join(value):
    fingerprint=previous.shared.transport_api.check_source_join(value)
    require(value.get('milestone')=='M2bz' and value.get('exactBase')==BASE
        and value.get('firmwareReady',False) is False,'ExactCurrentM2bzSourceWithoutFirmwareAuthorityRequired')
    return fingerprint


def verify_ack(ack,identity,public):
    fields={'kind','schemaVersion','classification','program_sha256','entry_pc','body_pc','return_pc',
        'stop_before_pc','selector_address','program_node_count','program_windows','native_generation_ownership',
        'physical_sf_known','hardware_validated'}
    require(type(ack) is dict and set(ack)==fields,'ClosedM2bzProgramAcknowledgementRequired')
    numeric=('schemaVersion','entry_pc','body_pc','return_pc','stop_before_pc','selector_address','program_node_count')
    require(all(type(ack[key]) is int for key in numeric),'TypedIntegerM2bzAcknowledgementFieldsRequired')
    expected={'kind':'program_admitted','schemaVersion':1,
        'classification':'ExplicitInventedPublicPostReturnSelectorFixture' if public else corpus.MODE,
        'program_sha256':identity['program_sha256'],'entry_pc':0x2000 if public else 0x063B,
        'body_pc':0x6400 if public else 0x54F5,'return_pc':0x2003 if public else 0x063E,
        'stop_before_pc':0x2011 if public else 0x064C,'selector_address':0x0140 if public else 0x013C,
        'program_node_count':59,'program_windows':identity['program_windows'],
        'native_generation_ownership':False,'physical_sf_known':False,'hardware_validated':False}
    require(ack==expected and all(ack[k] is False for k in ('native_generation_ownership','physical_sf_known','hardware_validated')),
        'ExactTwoWindow59SiteOnceSelectorTechnicalAdmissionRequired')


class VerificationRun(previous.VerificationRun):
    MILESTONE,BASE,BRANCH='M2bz',BASE,BRANCH
    BUDGETS={'A':49}
    PUBLIC_MODE,PRIVATE_MODE=corpus.PUBLIC_MODE,corpus.MODE
    LOCK_NAME='.m2bz-runtime.lock.json'
    check_source_join=staticmethod(check_source_join)
    read_checkpoint=staticmethod(read_checkpoint)
    verify_ack=staticmethod(verify_ack)

    def validate_program_domain(self,identity,public):
        require(type(public) is bool,'ExplicitM2bzProgramDomainRequired')
        caller,body=(0x2000,0x6400) if public else (0x063B,0x54F5)
        windows=identity.get('program_windows')
        require(identity.get('program_base')==body and identity.get('program_end_exclusive')==body+404
            and type(windows) is list and len(windows)==2
            and [(w.get('base'),w.get('end_exclusive'),w.get('byte_count'),w.get('role')) for w in windows]
                ==[(caller,caller+17,17,'CallerCALAndPostReturn'),(body,body+404,404,'CalleeBodyAndRT')],
            'TwoExact17And404WindowsWithoutGapPaddingRequired')

    def validate_actual_record(self,index,record):
        actual=record['actual'];outer=actual.get('report',{});prefix=outer.get('prefix',{})
        terminal=0x2011 if self.public else 0x064C
        require(actual.get('kind')=='post_return_selector_observation' and actual.get('accepted') is True
            and actual.get('actual_successful_step_returns')==49 and outer.get('completed') is True
            and outer.get('post_return_instruction_retirements')==8 and outer.get('total_instruction_retirements')==49
            and outer.get('native_next_event_handoff_verified') is False and outer.get('branch064c_retired') is False
            and prefix.get('completed') is True and prefix.get('cpu_bus_instances')==1
            and prefix.get('post_return_instruction_retirements')==8
            and prefix.get('body',{}).get('stop_before_pc')==terminal,
            'ActualSameMachineCalBodyRtPlusEightSelectorStepsRequired')
        frame,returned=prefix.get('stack_frame'),prefix.get('stack_return');generation=outer.get('selector_generation')
        require(type(frame) is dict and type(returned) is dict and type(generation) is dict
            and frame.get('machine_id')==returned.get('machine_id')==generation.get('machine_id')==1
            and frame.get('retired_instruction')==1 and returned.get('retired_instruction')==41
            and frame.get('logical_write_ordinal')==returned.get('consumed_logical_write_ordinal')==58
            and generation.get('retired_instruction')==49 and generation.get('native_write_ordinal')==18
            and generation.get('logical_write_ordinal')==76 and generation.get('raw_write_ordinal')==113
            and outer.get('initial_selector_generation') is None,'FreshRetainedFrameAndCurrentNativeSelectorGenerationRequired')

    def build_summary(self,raw):
        require(len(self.records)==16 and sum(r['actual']['actual_successful_step_returns'] for r in self.records)==784,
            'ExactlySixteenActual49StepCasesAnd784RetirementsRequired')
        reports=[r['actual']['report'] for r in self.records];prefixes=[r['prefix'] for r in reports]
        bodies=[p['body'] for p in prefixes]
        p2=[e for b in bodies for e in b['peripheral_p2_journal']];control=[e for b in bodies for e in b['peripheral_control_journal']]
        kind='public_fixture' if self.public else 'private'
        from .oracle import _pc
        post_pcs={_pc(pc,kind) for pc in corpus.POST_PCS}
        post=[e for b in bodies for e in b['audit']['data_events'] if e['phase']=='Functional' and e['pc'] in post_pcs]
        raw_native=sum(e['operation']=='Write' and b['audit']['data_events'][e['logical_ordinal']]['phase']=='Functional'
            for b in bodies for e in b['audit']['raw_data_events'])
        initials=Counter(str(r['selector_initial']) for r in reports)
        transitions=Counter(f"{r['selector_initial']}->{r['selector_final']}" for r in reports)
        return {'schemaVersion':1,'milestone':'M2bz','passed':True,'classification':self.mode,'corpusKind':self.corpus_kind,
            'sourceFingerprintSha256':self.fingerprint,'corpusSha256':self.corpus_digest,'cases':16,'positiveCases':16,'paths':{'A':16},
            'retiredInstructions':784,'calRetirements':16,'bodyRetirements':624,'rtRetirements':16,'postReturnRetirements':128,
            'cpuBusInstances':16,'freshCalFrameWriters':16,'rtSameMachineFrameConsumptions':16,
            'sameValueCalWrites':sum(p['stack_frame']['same_value'] for p in prefixes),'stackSspSlots':sorted({p['stack_frame']['old_ssp'] for p in prefixes}),
            'stackLogicalWrites':16,'stackLogicalReads':16,'stackRawByteWrites':32,'stackRawByteReads':32,
            'p2Retirements':32,'functionalPeripheralP2Reads':32,'functionalPeripheralP2Writes':32,
            'sameValueP2Writes':sum(e['same_value'] for e in p2 if e['operation']=='Write'),
            'controlRetirements':64,'functionalPeripheralControlReads':64,'functionalPeripheralControlWrites':32,
            'sameValueControlWrites':sum(e['same_value'] for e in control if e['operation']=='Write'),
            'p2Generations':32,'controlGenerations':32,'sameValueSecondP2Writes':16,'belowRetirements':288,
            'selectorSnapshotInitializations':16,'selectorReads':sum(r['selector_read'] is not None for r in reports),
            'selectorWrites':sum(r['selector_generation'] is not None for r in reports),'freshNativeSelectorWriters':16,
            'selectorGenerations':16,'selectorWraps':sum(r['selector_initial']==3 and r['selector_final']==0 for r in reports),
            'historyRmwReads':sum(e['operation']=='Read' for r in reports for e in r['history0128_rmw']),
            'historyRmwWrites':sum(e['operation']=='Write' for r in reports for e in r['history0128_rmw']),
            'sameValueHistoryWrites':sum(e['same_value'] for r in reports for e in r['history0128_rmw'] if e['operation']=='Write'),
            'historyGenerations':16,'localR0Reads':sum(e['address']==0x0108 and e['operation']=='Read' for e in post),
            'localR0Writes':sum(e['address']==0x0108 and e['operation']=='Write' for e in post),'localR0Increments':16,
            'postReturnDataReads':sum(e['operation']=='Read' for e in post),'postReturnDataWrites':sum(e['operation']=='Write' for e in post),
            'allNativeWrites':sum(row[4]==1 for p in prefixes for row in p['all_native_journal']),'rawNativeByteWrites':raw_native,
            'selectorInitialCounts':dict(initials),'selectorTransitions':dict(transitions),
            'firstMismatch':None,'independentOracle':'PASS','canonicalDecompressedBytes':len(raw),'canonicalSha256':sha256(raw).hexdigest(),
            'expectedSha256':digest(self.expected),'fullActualObservationsRetained':True,'canonicalFieldExclusions':[],
            'TechnicalCalRtFrameContinuityVerified':True,'OriginalRomCalRtObserved':not self.public,'PublicEquivalentCalRtVerified':self.public,
            'TechnicalPostReturnSelectorContinuityVerified':True,'OriginalRomPostReturnSelectorObserved':not self.public,
            'PublicEquivalentPostReturnSelectorVerified':self.public,'initialDATA0196Owner':corpus.DATA0196_OWNER,
            'initialDATA013COwner':corpus.SELECTOR_CLASSIFICATION,'initialDATA013CNativeGeneration':None,
            'selectorFinalSource':'CurrentExecutionNativeSelectorWriter064A','DATA013CGenerationAvailableForFutureReader':True,
            'branch064cRetired':False,'nativeNextEventHandoffVerified':False,'nativeCallerSchedulerEstablished':False,
            'physicalNativeStackSafetyEstablished':False,'physicalSfKnown':False,'strictHistoricalPreservationPass':False,
            'inheritedAuthorizedPreservationExceptions':1,'cycleAccounting':dict(CYCLE_ACCOUNTING),'unresolvedStatuses':list(UNRESOLVED),'firmwareReady':False}
