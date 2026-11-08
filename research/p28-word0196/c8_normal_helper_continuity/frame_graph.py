"""Bound frame lifetimes and preserve the first unproved cold-to-mode edge."""
from enclosing_caller_return.state import input_class, label, need, number, shape, tri
from cold_return_c8_writer_proof.cold_source_join import (
    cold_caller_mode_source_join, cold_return_path_obligations,
)

from .wire import result

COMPLETE = 'CompleteConditional'
UNKNOWN = 'IndeterminateObligation'
OUTSIDE = 'OutsideVerifiedScope'
CLAIMS = ('ConditionalOnly', 'NativeReturn', 'NativeModeReach', 'ActualHardware')
FRAME_SCOPE = (0x276A, 0x276D, 0x2777, 0x277A, 0x5CB9, 0x5CCB, 0x5CCD, 0x5CF9)
PHASES = ('IndexedLive', 'BetweenCalls', 'HelperLive')
BOUNDARIES = ('STOP_BEFORE_RT_5CCD', 'STOP_BEFORE_CAL_2777', 'STOP_BEFORE_RT_5CF9')
FRAME_GAPS = ('NoNativeIeAuthority', 'NoNativeCallOrReturn')
WINDOW_REFUSALS = ('FrameWritePhaseOrderMismatch', 'CompetingFrameWriteUnqualified',
                   'FrameWindowGenerationReused', 'FrameWindowControlAlias',
                   'HelperLiveFrameAddressUnknown', 'LiveFrameGenerationOverwritten')
GRAPH_GAPS = ('C8SourceConflictRetained', 'NormalFullEntryHelperUnbound', 'Native60ccUnbound')
GRAPH_SITES = (0x276A, 0x276D, 0x2771, 0x2777, 0x277A, 0x27B2, 0x27D0, 0x5CB4,
               0x5CB7, 0x5CB9, 0x5CCB, 0x5CCD, 0x5CD9, 0x5CDF, 0x5CF9, 0x5F45, 0x60CC)


def cold_frame_generation_chain(query):
    """Check additional supplied writers over two distinct frame lifetimes."""
    shape(query, ('inputClass', 'frameQuery', 'ie5cb9', 'ie5ccb', 'writes', 'claim'),
          'ClosedColdFrameGenerationChainRequired')
    input_class(query['inputClass'])
    need(query['claim'] in CLAIMS and tri(query['ie5cb9']) and tri(query['ie5ccb']), 'TypedIeFramePremisesRequired')
    nested = query['frameQuery']
    need(type(nested) is dict and nested.get('inputClass') == query['inputClass'], 'MatchingFrameChainInputRequired')
    events = query['writes']
    need(type(events) is list and len(events) <= 24, 'BoundedFrameWriteWindowRequired')
    for event in events:
        shape(event, ('stage', 'address', 'widthBits', 'generation', 'pathEstablished'), 'ClosedFrameWriteRequired')
        need(event['stage'] in PHASES and number(event['address'], 0xFFFF)
             and type(event['widthBits']) is int and event['widthBits'] in (8, 16)
             and label(event['generation']) and tri(event['pathEstablished']), 'TypedFrameWindowWriteRequired')

    child = None
    checked = []
    state = {'formalIndexedPc': None, 'formalHelperPc': None, 'sameAlignedAddress': None,
             'indexedAddress': None, 'helperAddress': None, 'nativeContinuity': None}

    def finish(status, reason, boundary):
        return result(status, source_scope=FRAME_SCOPE, caller=0x276A, state=state, stop=boundary,
                      evidence_class='StaticFormalSourceObligation', intermediate=checked,
                      generations=None if child is None else child['generations'],
                      obligations=() if child is None else child['formalObligations'],
                      unresolved=FRAME_GAPS if status == COMPLETE else (*FRAME_GAPS, reason),
                      reason=reason, frozenFrameResult=child)

    if query['claim'] != 'ConditionalOnly':
        return finish(OUTSIDE, 'NonConditionalFrameChainClaim', 'STOP_BEFORE_CAL_276A')
    if query['ie5cb9'] is not True:
        return finish(UNKNOWN, 'FirstIeSoftwareHandoffUnestablished', 'STOP_BEFORE_IE_WRITE_5CB9')
    if query['ie5ccb'] is not True:
        return finish(UNKNOWN, 'SecondIeSoftwareHandoffUnestablished', 'STOP_BEFORE_IE_WRITE_5CCB')
    child = cold_return_path_obligations(nested)
    if child['state']['formalIndexedPc'] != 0x276D:
        return finish(child['status'], child['reason'], child['stopBoundary'])

    # Candidate addresses originate from the two formal CAL intents.
    calls = {event['pc']: event['address'] for event in child['formalObligations']
             if event['kind'] == 'FormalCalWordStore'}
    indexed, helper = calls[0x276A], calls.get(0x2777)
    state.update(indexedAddress=indexed, helperAddress=helper,
                 sameAlignedAddress=None if helper is None else indexed == helper)
    used = set(child['generations'].values())
    prior_phase = 0
    for event in events:
        phase = PHASES.index(event['stage'])
        if phase < prior_phase:
            return finish(OUTSIDE, 'FrameWritePhaseOrderMismatch', BOUNDARIES[prior_phase])
        prior_phase = phase
        if phase > 0:
            state['formalIndexedPc'] = 0x276D
        if event['pathEstablished'] is False:
            continue
        if event['pathEstablished'] is not True or event['address'] is None or event['generation'] is None:
            return finish(UNKNOWN, 'CompetingFrameWriteUnqualified', BOUNDARIES[phase])
        generation = event['generation']
        if generation in used:
            return finish(OUTSIDE, 'FrameWindowGenerationReused', BOUNDARIES[phase])
        used.add(generation)
        address, width = event['address'], event['widthBits']
        address = address & 0xFFFE if width == 16 else address
        end = address + width // 8
        live = indexed if phase == 0 else helper if phase == 2 else None
        if address < 8 or address < 0xC0 and end > 0x80 or address == 0x4700:
            return finish(OUTSIDE, 'FrameWindowControlAlias', BOUNDARIES[phase])
        if phase == 2 and helper is None:
            return finish(UNKNOWN, 'HelperLiveFrameAddressUnknown', BOUNDARIES[phase])
        if live is not None and address < live + 2 and end > live:
            return finish(OUTSIDE, 'LiveFrameGenerationOverwritten', BOUNDARIES[phase])
        checked.append({'stage': event['stage'], 'alignedAddress': address, 'widthBits': width,
                        'generation': generation, 'liveFrameOverlap': False})
    state['formalIndexedPc'] = 0x276D
    if child['status'] != COMPLETE:
        return finish(child['status'], child['reason'], child['stopBoundary'])
    state['formalHelperPc'] = 0x277A
    return finish(COMPLETE, 'SeparateFrameGenerationsRetained', 'STOP_BEFORE_RT_5CF9')


def _edge(start, end, classification, predicate, old, new, frame, interference, missing, stop):
    return {'from': start, 'to': end, 'evidenceClass': classification, 'predicate': predicate,
            'inputGeneration': old, 'outputGeneration': new, 'frameRequirement': frame,
            'noInterference': interference, 'missingProof': missing, 'stopBoundary': stop}


def cold_normal_mode_source_join(query):
    """Bind the genuine index-5 origin and identify the first unproved edge."""
    shape(query, ('inputClass', 'joinQuery', 'frameChain', 'requestedGeneration', 'claim'),
          'ClosedNormalModeSourceJoinRequired')
    input_class(query['inputClass'])
    need(query['claim'] in CLAIMS and label(query['requestedGeneration']), 'TypedNormalModeJoinRequired')
    join, frames = query['joinQuery'], query['frameChain']
    need(type(join) is dict and join.get('inputClass') == query['inputClass']
         and (frames is None or type(frames) is dict and frames.get('inputClass') == query['inputClass']),
         'MatchingModeJoinInputRequired')
    cold = chain = None
    generation = None
    frame_matched = False

    def finish(status, reason, stop, retain=False):
        carried = cold if retain else {}
        verified = generation if retain and generation == query['requestedGeneration'] else None
        edges = (
            _edge(0x5CB4, 0x5CB7, 'ReachingDefinitionCandidate', 'Index5Writer', None, generation,
                  None, None, None if generation else 'FrozenIndex5Writer', 'STOP_BEFORE_IE_WRITE_5CB9'),
            _edge(0x5CCD, 0x276D, 'FormalFrameObligation', 'TwoHypotheticalIeHandoffs', verified, verified,
                  'CAL276A', True if frame_matched else None, None if frame_matched else 'ExactIndexedFrame',
                  'STOP_BEFORE_RT_5CCD'),
            _edge(0x2777, 0x5CD9, 'ConfirmedStaticCFG', 'QualifiedColdExitAndEntry', None, None,
                  'CAL2777', None, 'ActualEntryOwner', 'STOP_BEFORE_JGT_5CDF'),
            _edge(0x5CDF, 0x5CF9, 'PrimarySourceConflict', 'IndependentNormalIngress', None, None,
                  None, None, 'SourceQualifiedNormalIngress', 'STOP_BEFORE_JGT_5CDF'),
            _edge(0x5CF9, 0x277A, 'FormalFrameObligation', 'NormalHelperFrontier', None, None,
                  'CAL2777', None, 'FullEntryNormalPath', 'STOP_BEFORE_RT_5CF9'),
            _edge(0x277A, 0x27B2, 'DetachedConditionalEntry', 'ColdCorridorAndUspOwner', None, None,
                  None, None, 'ConnectedHelperReturn', 'STOP_BEFORE_USP_STORE_27B2'),
            _edge(0x27D0, 0x5F45, 'ConfirmedStaticCFG', 'ModeCallTarget', None, None,
                  'CAL27D0', None, 'ConnectedColdCorridor', 'STOP_BEFORE_CAL_27D0'),
            _edge(0x5F45, 0x60CC, 'NativeContinuityBlocked', 'ModeBranchAndGeneration', None, None,
                  'CAL27D0', None, 'ConnectedModeEntry', 'STOP_BEFORE_UNBOUND_MODE_READ_60CC'),
        )
        return result(status, source_scope=GRAPH_SITES, caller=0x276A, state=carried.get('state'), stop=stop,
                      reads=carried.get('reads', ()), writes=carried.get('orderedWrites', ()),
                      generations=carried.get('generations'), intermediate=carried.get('intermediateStates', ()),
                      branches=carried.get('branchOutcome', ()), obligations=carried.get('formalObligations', ()),
                      iterations=carried.get('iterations', ()), unresolved=(*GRAPH_GAPS, reason),
                      reason=reason, sourceEdges=list(edges), localWriterGeneration=generation,
                      nativeModeOwner=None, connectedModeRead=False, frozenColdJoin=cold, frameChainResult=chain)

    if query['claim'] != 'ConditionalOnly':
        return finish(OUTSIDE, 'NonConditionalModeJoinClaim', 'STOP_BEFORE_CAL_276A')
    cold = cold_caller_mode_source_join(join)
    step = cold['frozenColdResult']
    prefix = None if not step or not step['frozenAcquisition'] else step['frozenAcquisition']['frozenPrefixResult']
    if prefix is None or prefix['conditionalData03cbWriterEstablished'] is not True:
        return finish(UNKNOWN, 'Index5WriterUnestablished', cold['stopBoundary'], True)
    generation = prefix['state']['generations']['03CB']
    if query['requestedGeneration'] != generation:
        return finish(UNKNOWN, 'RequestedColdGenerationUnlinked', 'STOP_BEFORE_INDEXED_CONTINUATION_5CB7')
    indexed = step['frozenIndexedFrame']
    if indexed is None or indexed['state']['formalReturnedPc'] != 0x276D:
        return finish(cold['status'], cold['reason'], cold['stopBoundary'], True)
    if frames is None:
        return finish(UNKNOWN, 'SeparateFrameWindowRequired', 'STOP_BEFORE_RT_5CCD')
    chain = cold_frame_generation_chain(frames)
    child = chain['frozenFrameResult']
    if chain['state']['formalIndexedPc'] != 0x276D:
        return finish(chain['status'], chain['reason'], chain['stopBoundary'])
    if child['indexedFrameResult'] != indexed:
        return finish(OUTSIDE, 'IndexedFrameGenerationOrGeometryMismatch', 'STOP_BEFORE_RT_5CCD')
    frame_matched = True
    if chain['reason'] in WINDOW_REFUSALS:
        stop = chain['stopBoundary']
        return finish(chain['status'], chain['reason'], cold['stopBoundary'] if stop == 'STOP_BEFORE_RT_5CF9' else stop)
    for write in chain['intermediateStates']:
        address = write['alignedAddress']
        if address <= 0x03CB < address + write['widthBits'] // 8:
            stop = BOUNDARIES[PHASES.index(write['stage'])]
            return finish(UNKNOWN, 'FrameWindowWriterReplacesData03cb',
                          cold['stopBoundary'] if stop == 'STOP_BEFORE_RT_5CF9' else stop)
    return finish(cold['status'], cold['reason'], cold['stopBoundary'], True)
