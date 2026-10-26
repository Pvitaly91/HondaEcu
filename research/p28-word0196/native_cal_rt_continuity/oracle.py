"""Independent CAL + reviewed39-step body + RT state/effect model.

No execution output establishes these expected values. PROGRAM sources are
independently invented code cells or immutable verified private ROM windows.
"""
from copy import deepcopy
from hashlib import sha256
import independent_encoder as encoder
from native_below_second_p2 import oracle as below
from . import corpus
_equal, _closed, BASE_ORACLE = below._equal, below._closed, below.BASE_ORACLE
CYCLE_ACCOUNTING = {**deepcopy(below.CYCLE_ACCOUNTING),
    'calSoftwareDiagnosticDelta': 9, 'rtSoftwareDiagnosticDelta': 7,
    'calManufacturerInt': 9, 'rtManufacturerInt': 7,
    'overallClassification': 'DiagnosticCycleTimingEquivalenceNotEstablished'}
FORM = {**below.FORM, 0x063B: (388, 'CAL addr16'), 0x5688: (1902, 'RT')}


def _pc(pc, kind):
    if kind not in ('private', 'public_fixture'):
        raise ValueError('ClosedM2byProgramKindRequired')
    if kind == 'private':
        return pc
    if pc == corpus.ENTRY_PC:
        return corpus.PUBLIC_CALLER
    if pc == corpus.RETURN_PC:
        return corpus.PUBLIC_RETURN
    return below._pc(pc, kind)


def diagnostic_snapshot_count(retirements):
    if type(retirements) is not int or retirements != 41:
        raise ValueError('ExactCalBodyRt41DiagnosticDomainRequired')
    return 4 * retirements + 4


def _seed_events(case, kind):
    logical, raw, memory = [], [], {}
    seeds = sorted((int(a), 8, v) for a,v in corpus.wire_case(case, kind)['data'].items())
    for bank, words in enumerate(case['entry']['pointing_banks']):
        seeds.extend((0x80 + bank*8 + slot*2,16,words[name])
                     for slot,name in enumerate(('x1','x2','dp','usp')))
    for address,width,value in seeds:
        old = sum(memory.get(address+i,0xA5) << (8*i) for i in range(width//8))
        ordinal = len(logical)
        logical.append({'ordinal':ordinal,'phase':'Seed','pc':_pc(corpus.ENTRY_PC,kind),
            'instruction_index':None,'address':address,'width':width,'operation':'Write',
            'requested_value':value,'value':value,'old_value':old,'write_ordinal':ordinal,
            'same_value':value==old,'serviced':True,'refusal':None})
        for i in range(width//8):
            byte,old_byte = value >> (8*i) & 255,memory.get(address+i,0xA5)
            raw.append({'ordinal':len(raw),'logical_ordinal':ordinal,'address':address+i,
                'operation':'Write','requested_value':byte,'value':byte,'old_value':old_byte,
                'write_ordinal':len(raw),'same_value':byte==old_byte,'serviced':True,'refusal':None})
            memory[address+i]=byte
    _equal((len(logical),len(raw)),(57,89),'seed/closed57_89')
    return logical,raw


def _data_expected(case, expected, kind):
    logical,raw = _seed_events(case,kind)
    spans,raw_writes = [],len(raw)
    for step in expected['steps']:
        start=len(logical),len(raw)
        for event in step['data_events']:
            ordinal=len(logical)
            logical.append({'ordinal':ordinal,'phase':'Functional',**event,'serviced':True,'refusal':None})
            if step['native_site_identity']=='55CF' and event['address']==6:
                continue
            for offset in range(event['width']//8):
                writing=event['operation']=='Write'
                value=event['value'] >> (8*offset) & 255
                old=event['old_value'] >> (8*offset) & 255 if writing else None
                raw.append({'ordinal':len(raw),'logical_ordinal':ordinal,'address':event['address']+offset,
                    'operation':event['operation'],'requested_value':value if writing else None,'value':value,
                    'old_value':old,'write_ordinal':raw_writes if writing else None,
                    'same_value':old==value if writing else None,'serviced':True,'refusal':None})
                raw_writes+=int(writing)
        spans.append({'logical_span':[start[0],len(logical)],'raw_span':[start[1],len(raw)]})
    return logical,raw,spans


def expected_case(case, program_kind='private'):
    corpus.validate_case(case)
    expected=deepcopy(below.expected_case(corpus.body_case(case),program_kind))
    ssp,ret=case['entry']['ssp'],_pc(corpus.RETURN_PC,program_kind)
    wire=corpus.wire_case(case,program_kind)
    old=wire['data'][str(ssp)] | wire['data'][str(ssp+1)] << 8
    for step in expected['steps']:
        step['index']+=1
        for side in ('before','after'):
            snap=step[side]
            snap['cpu']['instructions']+=1; snap['cpu']['cycles']+=9
            snap['cpu']['sf']=False
            snap['owned_ram'].update({str(ssp):ret & 255,str(ssp+1):ret >> 8})
        for event in step['data_events']:
            if event['write_ordinal'] is not None:
                event['write_ordinal']+=3
    cal_after=deepcopy(expected['steps'][0]['before'])
    cal_before=deepcopy(cal_after)
    cal_before['cpu'].update(pc=_pc(corpus.ENTRY_PC,program_kind),ssp=ssp,
                            instructions=0,cycles=0,sf=case['internal_sf'])
    cal_before['owned_ram'].update({str(ssp):old & 255,str(ssp+1):old >> 8})
    cal_event={'pc':_pc(corpus.ENTRY_PC,program_kind),'instruction_index':388,'address':ssp,'width':16,
        'operation':'Write','requested_value':ret,'value':ret,'old_value':old,'write_ordinal':57,'same_value':old==ret}
    cal={'index':1,'native_site_identity':'063B','pc':_pc(corpus.ENTRY_PC,program_kind),
        'next_pc':_pc(corpus.BODY_BASE,program_kind),'form':'cal-direct16','decoded_index':388,
        'mnemonic':'CAL addr16','length':3,'branch_taken':None,'before':cal_before,'after':cal_after,'data_events':[cal_event]}
    rt_before=deepcopy(expected['steps'][-1]['after'])
    rt_after=deepcopy(rt_before)
    rt_after['cpu'].update(pc=ret,ssp=ssp,sf=False,instructions=41,cycles=rt_before['cpu']['cycles']+7)
    rt_event={'pc':_pc(0x5688,program_kind),'instruction_index':1902,'address':ssp,'width':16,
        'operation':'Read','requested_value':None,'value':ret,'old_value':None,'write_ordinal':None,'same_value':None}
    rt={'index':41,'native_site_identity':'5688','pc':_pc(0x5688,program_kind),'next_pc':ret,
        'form':'rt','decoded_index':1902,'mnemonic':'RT','length':1,'branch_taken':None,
        'before':rt_before,'after':rt_after,'data_events':[rt_event]}
    expected['steps']=[cal,*expected['steps'],rt]
    for name in ('control_step_snapshots','p2_step_snapshots'):
        rows=expected[name]
        for row in rows: row['index']+=1
        before=deepcopy(rows[0]['before']); after=deepcopy(rows[-1]['after'])
        expected[name]=[{'index':1,'before':before,'after':deepcopy(before)},*rows,
                        {'index':41,'before':after,'after':deepcopy(after)}]
    expected.update(classification='IndependentTechnicalCalRtFrameReference_NoCpuObservation',
        entry=cal_before,terminal=rt_after,instruction_count=41,stop_before_pc=ret,
        write_count=expected['write_count']+1,cycle_accounting=deepcopy(CYCLE_ACCOUNTING),
        initialDATA0196Owner=corpus.DATA0196_OWNER)
    expected['ordered_data_events']=[deepcopy(event) for step in expected['steps'] for event in step['data_events']]
    expected['logical_read_count']=sum(e['operation']=='Read' for e in expected['ordered_data_events'])
    expected['ram_logical_read_count']=sum(e['operation']=='Read' and e['address']>=128 for e in expected['ordered_data_events'])
    logical,raw,spans=_data_expected(case,expected,program_kind)
    for address,name,retired in ((36,'p2',(18,39)),(64,'control',(19,25))):
        journal,generations=[],[]
        for event in logical:
            if event['phase']!='Functional' or event['address']!=address: continue
            linked=[item for item in raw if item['logical_ordinal']==event['ordinal']]
            _equal(len(linked),1,'peripheral/exact_one_raw_link')
            journal.append({'ordinal':len(journal),'pc':event['pc'],'address':address,'width':8,
                'operation':event['operation'],'value':event['value'],'logical_ordinal':event['ordinal'],
                'raw_ordinal':linked[0]['ordinal'],'write_ordinal':event['write_ordinal'],
                'native_write_ordinal':event['write_ordinal']-57 if event['write_ordinal'] is not None else None,
                'same_value':event['same_value'],'space':'PeripheralP2' if name=='p2' else 'PeripheralControl'})
            if event['operation']=='Write':
                generations.append({'machine_id':1,'writer_pc':event['pc'],'retired_instruction':retired[len(generations)],
                    'generation_ordinal':len(generations)+1,'native_write_ordinal':event['write_ordinal']-57,
                    'logical_write_ordinal':event['write_ordinal'],'raw_write_ordinal':linked[0]['write_ordinal'],'value':event['value']})
        expected['peripheral_'+name+'_journal']=journal
        expected[name+'_generation'],expected['second_'+name+'_generation']=generations
        expected[name+'_generations']=generations
    cal_logical,rt_logical=logical[spans[0]['logical_span'][0]],logical[spans[-1]['logical_span'][0]]
    cal_raw=raw[spans[0]['raw_span'][0]:spans[0]['raw_span'][1]]
    rt_raw=raw[spans[-1]['raw_span'][0]:spans[-1]['raw_span'][1]]
    expected['stack_frame']={'machine_id':1,'writer_pc':cal['pc'],'retired_instruction':1,'old_ssp':ssp,
        'address':ssp,'width':16,'return_pc':ret,'logical_ordinal':cal_logical['ordinal'],
        'logical_write_ordinal':57,'raw_ordinals':[r['ordinal'] for r in cal_raw],
        'raw_write_ordinals':[r['write_ordinal'] for r in cal_raw],'native_write_ordinal':0,'generation_ordinal':1,
        'all_native_ordinal':0,'source_generation':'CurrentExecutionCAL','same_value':old==ret}
    expected['stack_return']={'machine_id':1,'consumer_pc':rt['pc'],'retired_instruction':41,
        'ssp_before':ssp-2,'ssp_after':ssp,'address':ssp,'width':16,'return_pc':ret,
        'logical_ordinal':rt_logical['ordinal'],'raw_ordinals':[r['ordinal'] for r in rt_raw],
        'consumed_writer_pc':cal['pc'],'consumed_retired_instruction':1,'consumed_logical_write_ordinal':57}
    expected['stack_journal']=[deepcopy(cal_logical),deepcopy(rt_logical)]
    expected['all_native_journal']=[[1 if e['address']==36 else 2 if e['address'] in (64,70) else 0,e['pc'],e['address'],e['width'],
        int(e['operation']=='Write'),e['value']] for e in expected['ordered_data_events'] if e['address']!=6]
    expected['stack_return']['all_native_ordinal']=len(expected['all_native_journal'])-1
    return expected


def _decoded(step,kind):
    if step['native_site_identity'] not in ('063B','5688'):
        return below._decoded(step,kind)
    return {'index':step['decoded_index'],'mnemonic':step['mnemonic'],'len':step['length'],
        'dd_before':step['before']['cpu']['dd'],'dd_after':step['after']['cpu']['dd'],'dd_after_option':None,
        'cycles':9 if step['native_site_identity']=='063B' else 7,'n8':0,'n8_alt':0,'n16':0,'n16_alt':0,
        's8':0,'rel8':0,'addr16':_pc(corpus.BODY_BASE,kind) if step['native_site_identity']=='063B' else 0}


def _permissions(expected):
    return below._permissions(expected)


def _public_body():
    """Independently composed403-byte invented segment; never read ROM bytes."""
    payload, hashes = bytearray([0xA5] * 403), {}
    for pc in below.previous.previous.previous.corpus.PREFIX:
        raw = below.previous.previous.previous._public_prefix_extent(pc)
        offset = pc - corpus.BODY_BASE
        payload[offset:offset + len(raw)] = raw
        hashes[str(_pc(pc, 'public_fixture'))] = sha256(raw).hexdigest()
    earlier = below.previous.previous.previous.previous
    for request in earlier._public_requests():
        pc = request.origin_pc - earlier.corpus.PUBLIC_PC_DELTA
        operands = tuple(encoder.TargetPC16(item.value - earlier.corpus.PUBLIC_PC_DELTA + corpus.PUBLIC_PC_DELTA)
            if type(item) is encoder.TargetPC16 else item for item in request.typed_operands)
        value = encoder.encode_instruction(encoder.EncoderRequest(request.reviewed_form_id, operands,
            request.incoming_dd, _pc(pc, 'public_fixture')))
        if type(value) is not encoder.EncodedInstruction:
            raise ValueError('IndependentPublicPrefixEncodingRefused')
        raw = value.encoded_bytes; offset = pc - corpus.BODY_BASE
        payload[offset:offset + len(raw)] = raw; hashes[str(_pc(pc, 'public_fixture'))] = sha256(raw).hexdigest()
    for pc in below.previous.previous.P2_FORM:
        raw = below.previous.previous._p2_encoding(pc); offset = pc - corpus.BODY_BASE
        payload[offset:offset + len(raw)] = raw; hashes[str(_pc(pc, 'public_fixture'))] = sha256(raw).hexdigest()
    for pc in below.previous.CONTROL_FORM:
        raw = below.previous.control_extent(pc, 'public_fixture'); offset = pc - corpus.BODY_BASE
        payload[offset:offset + len(raw)] = raw; hashes[str(_pc(pc, 'public_fixture'))] = sha256(raw).hexdigest()
    for pc in below.TAIL_FORM:
        raw = below.downstream_extent(pc, 'public_fixture'); offset = pc - corpus.BODY_BASE
        payload[offset:offset + len(raw)] = raw; hashes[str(_pc(pc, 'public_fixture'))] = sha256(raw).hexdigest()
    _equal(len(hashes), 49, 'public/closed49')
    return bytes(payload) + bytes((0x01,)), hashes


def public_program_identity():
    body,hashes=_public_body()
    caller=bytes((0x32,corpus.PUBLIC_BASE & 255,corpus.PUBLIC_BASE >> 8))
    hashes[str(corpus.PUBLIC_CALLER)]=sha256(caller).hexdigest()
    hashes[str(_pc(0x5688,'public_fixture'))]=sha256(bytes((1,))).hexdigest()
    return {'program_base':corpus.PUBLIC_BASE,'program_end_exclusive':corpus.PUBLIC_BASE+404,
        'program_sha256':sha256(caller+body).hexdigest(),'source_binding':None,'selected_extent_sha256':hashes,
        'program_windows':[{'base':base,'end_exclusive':base+len(raw),'sha256':sha256(raw).hexdigest(),
            'byte_count':len(raw),'role':role} for base,raw,role in (
                (corpus.PUBLIC_CALLER,caller,'CallerCAL'),(corpus.PUBLIC_BASE,body,'CalleeBodyAndRT'))]}


def _program_events(events,steps,identity):
    windows=identity['program_windows']
    cursor=0
    for actual,expected in steps:
        span=actual['program_span']
        if type(span) is not list or len(span)!=2 or span[0]!=cursor or not cursor<span[1]<=len(events):
            raise ValueError('TwoWindowProgramSpanClosedPartition')
        selected=[]; saw=False
        for event in events[span[0]:span[1]]:
            _closed(event,('ordinal','pc','address','segment_offset','instruction_offset','acquired_purpose',
                          'selection_association','selected_length','serviced','refusal'),'PROGRAM')
            _equal(event['ordinal'],cursor,'PROGRAM/ordinal'); _equal(event['pc'],expected['pc'],'PROGRAM/pc')
            matches=[w for w in windows if w['base']<=event['address']<w['end_exclusive']]
            _equal(len(matches),1,'PROGRAM/exact_window_not_gap_or_return')
            window=matches[0]
            _equal(event['segment_offset'],event['address']-window['base'],'PROGRAM/window_offset')
            _equal(event['instruction_offset'],event['address']-expected['pc'],'PROGRAM/instruction_offset')
            _equal(event['selected_length'],expected['length'],'PROGRAM/selected_length')
            _equal((event['serviced'],event['refusal']),(True,None),'PROGRAM/serviced')
            if event['acquired_purpose']=='ArchitecturalSelectedFetch':
                saw=True; _equal(event['selection_association'],None,'PROGRAM/association'); selected.append(event['address'])
            elif event['acquired_purpose']=='DecoderProbe' and not saw:
                _equal(event['selection_association'],'SelectedExtent' if event['address']-expected['pc']<expected['length']
                       else 'DecoderLookahead','PROGRAM/probe_association')
            else: raise ValueError('ProgramPurposeOrderOrUnexpectedProbe')
            cursor+=1
        _equal(selected,list(range(expected['pc'],expected['pc']+expected['length'])),'PROGRAM/exact_selected_extent')
    _equal(cursor,len(events),'PROGRAM/no_unassigned_or_post_return_fetch')


def compare_observation(case, actual, program_kind='private', program_identity=None):
    expected = expected_case(case, program_kind)
    if program_identity is None and program_kind == 'public_fixture':
        program_identity = public_program_identity()
    _closed(program_identity, ('program_base', 'program_end_exclusive', 'program_sha256', 'source_binding', 'selected_extent_sha256', 'program_windows'), 'program')
    _equal(program_identity['program_base'], _pc(corpus.BODY_BASE, program_kind), 'program/base')
    _equal(program_identity['program_end_exclusive'], _pc(0x5688, program_kind)+1, 'program/end')
    _equal(set(program_identity['selected_extent_sha256']), {str(_pc(pc, program_kind)) for pc in FORM}, 'program/closed51')
    for digest in [program_identity['program_sha256'], *program_identity['selected_extent_sha256'].values()]:
        if type(digest) is not str or BASE_ORACLE.SHA.fullmatch(digest) is None:
            raise ValueError('FrozenProgramShaRequired')
    if program_kind == 'public_fixture':
        _equal(program_identity, public_program_identity(), 'program/independent_public_encoding')
    _closed(actual, ('kind', 'case_id', 'family', 'internal_sf', 'accepted', 'error', 'actual_successful_step_returns', 'report'), 'observation')
    for key, value in {'kind': 'cal_rt_continuity_observation', 'case_id': case['case_id'], 'family': case['family'],
        'internal_sf': case['internal_sf'], 'accepted': True, 'error': None, 'actual_successful_step_returns': case['budget']}.items():
        _equal(actual[key], value, 'observation/' + key)
    outer = actual['report']
    _closed(outer, ('body','program_windows','program_identity','stack_frame','stack_return','stack_journal',
        'frame_status','initial_canary_classification','completed','cal_instruction_retirements',
        'body_instruction_retirements','rt_instruction_retirements','post_return_instruction_retirements','cpu_bus_instances','all_native_journal'),'report')
    for key,value in {'program_windows':program_identity['program_windows'],'program_identity':program_identity['program_sha256'],
        'stack_frame':expected['stack_frame'],'stack_return':expected['stack_return'],'stack_journal':expected['stack_journal'],
        'all_native_journal':expected['all_native_journal'],
        'frame_status':'CallerFrameConsumedByActualRT','initial_canary_classification':'TechnicalPreexistingCanaryNotFrame',
        'completed':True,'cal_instruction_retirements':1,'body_instruction_retirements':39,
        'rt_instruction_retirements':1,'post_return_instruction_retirements':0,'cpu_bus_instances':1}.items():
        _equal(outer[key],value,'report/'+key)
    report = outer['body']
    _closed(report, ('classification', 'source_binding', 'program_node_count', 'path', 'entry', 'current', 'full_psw', 'steps',
        'completed', 'positive_completed', 'boundary_only', 'actual_handoff_observed', 'native_predecessor_retirements',
        'algorithm_retirements', 'stop_before_pc', 'audit', 'p2_snapshot', 'p2_initial', 'p2_final',
        'p2_instruction_retirements', 'peripheral_p2_journal', 'p2_generation', 'ownership', 'p2_step_snapshots', 'control_snapshot', 'control_initial', 'control_final',
        'control_instruction_retirements', 'peripheral_control_journal', 'control_generation', 'control_step_snapshots', 'below_instruction_retirements',
        'p2_generations', 'control_generations', 'second_p2_generation', 'second_control_generation'), 'report')
    fixed = {'classification': corpus.MODE if program_kind == 'private' else 'ExplicitInventedPublicCalRtFrameContinuityFixture',
        'source_binding': program_identity['source_binding'], 'program_node_count': 51, 'path': case['path'],
        'full_psw': expected['terminal']['full_psw'], 'completed': True, 'positive_completed': True, 'boundary_only': False,
        'actual_handoff_observed': True, 'native_predecessor_retirements': 6,
        'algorithm_retirements': 10, 'stop_before_pc': expected['stop_before_pc'],
        'p2_snapshot': case['p2_snapshot'], 'p2_initial': expected['initial_p2'], 'p2_final': expected['final_p2'],
        'p2_instruction_retirements': 2, 'control_snapshot': case['control_snapshot'],
        **{key: expected[key] for key in ('control_initial', 'control_final', 'control_instruction_retirements',
            'peripheral_control_journal', 'control_generation', 'control_step_snapshots')},
        **{key: expected[key] for key in ('peripheral_p2_journal', 'p2_generation', 'ownership', 'p2_step_snapshots',
            'below_instruction_retirements', 'p2_generations', 'control_generations', 'second_p2_generation', 'second_control_generation')}}
    for key, value in fixed.items():
        _equal(report[key], value, 'report/' + key)
    if type(report['steps']) is not list or len(report['steps']) != case['budget']:
        raise ValueError('ExactP2HandoffStepRecordsRequired')
    # Explicit reviewed technical Bus canary, not actual output as an oracle.
    ram = [0xA5] * 3968
    for address, value in expected['entry']['owned_ram'].items():
        ram[int(address) - 128] = value
    for label, obligation in (('entry', expected['entry']), ('current', expected['terminal'])):
        BASE_ORACLE._snapshot(report[label], obligation, ram, label)
    logical, raw, spans = _data_expected(case, expected, program_kind)
    for index, (step, obligation) in enumerate(zip(report['steps'], expected['steps'])):
        _closed(step, ('index', 'node_identity', 'full_psw_before', 'full_psw_after', 'before', 'after', 'outcome',
                      'program_span', 'logical_span', 'raw_span'), 'step')
        _equal(step['index'], index + 1, 'step/index')
        _equal(step['node_identity'], f"ClosedSite_{obligation['pc']:04X}", 'step/node_identity')
        for which in ('before', 'after'):
            BASE_ORACLE._snapshot(step[which], obligation[which], ram, f'step/{index}/{which}')
            _equal(step['full_psw_' + which], obligation[which]['full_psw'], 'step/psw_' + which)
        for field in ('logical_span', 'raw_span'):
            _equal(step[field], spans[index][field], 'step/' + field)
        outcome = {'pc_before': obligation['pc'], 'pc_after': obligation['next_pc'], 'decoded_index': obligation['decoded_index'],
            'mnemonic': obligation['mnemonic'], 'len': obligation['length'], 'decoded': _decoded(obligation, program_kind),
            'selected_extent': [obligation['pc'], obligation['pc'] + obligation['length']],
            'selected_extent_sha256': program_identity['selected_extent_sha256'][str(obligation['pc'])], 'retired': True, 'external_exit': None}
        _equal(step['outcome'], outcome, 'step/outcome')
    audit = report['audit']
    _closed(audit, ('entry_pc', 'current_pc', 'program_base', 'program_end_exclusive', 'program_sha256', 'program_events',
        'data_events', 'raw_data_events', 'diagnostic_events', 'data_admission_refusals', 'permissions', 'phase', 'budget',
        'successful_retirements', 'step_calls', 'execution_calls', 'shared_execution_calls', 'sealed', 'terminal_reason', 'external_exit', 'first_fault'), 'audit')
    fields = {'entry_pc': _pc(corpus.ENTRY_PC, program_kind), 'current_pc': expected['stop_before_pc'],
        **{key: program_identity[key] for key in ('program_base', 'program_end_exclusive')},
        'program_sha256':program_identity['program_windows'][1]['sha256'],
        'data_events': logical, 'raw_data_events': raw, 'data_admission_refusals': [],
        'permissions': _permissions(expected), 'phase': 'Sealed', 'budget': case['budget'],
        'successful_retirements': case['budget'], 'step_calls': case['budget'], 'execution_calls': case['budget'],
        'shared_execution_calls': case['budget'], 'sealed': True, 'terminal_reason': 'OriginalStopBeforeReached',
        'external_exit': None, 'first_fault': None}
    for key, value in fields.items():
        _equal(audit[key], value, 'audit/' + key)
    _equal(audit['diagnostic_events'], [{'ordinal': i, 'kind': 'RawRamSnapshot', 'range': [128, 4096], 'byte_count': 3968}
        for i in range(diagnostic_snapshot_count(case['budget']))], 'audit/diagnostics')
    _program_events(audit['program_events'], list(zip(report['steps'], expected['steps'])), program_identity)
    return {'passed': True, 'expected': expected, 'comparison': {'classification': 'IndependentContinuousCalRtStateFrameAndOrderedGenerationsValidated',
        'firstMismatch': None, 'retirements': case['budget'], 'path': case['path'], 'p2Retirements': 2,
        'oldP2': expected['initial_p2'], 'newP2': expected['final_p2'], 'sameValueP2Write': expected['same_value_p2_write'],
        'finalP2Zf': expected['final_p2_zf'], 'controlRetirements': expected['control_instruction_retirements'], 'belowRetirements': 18,
        'sameValueSecondP2Write': expected['peripheral_p2_journal'][-1]['same_value'],
        'p2Generations': expected['p2_generations'], 'controlGenerations': expected['control_generations'],
        'oldControl': expected['control_initial'], 'newControl': expected['control_final'],
        'sameValueControlWrite': expected['peripheral_control_journal'][-1]['same_value'],
        'initialNativeP2OwnerEstablished': False, 'initialNativeControlOwnerEstablished': False,
        'physicalExecutionClaimed': False, 'omittedActualFields': []}}
