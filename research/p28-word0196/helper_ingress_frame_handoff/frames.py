"""Formal ordinary CAL/RT lifetimes, never a stack executor or ingress proof.

The accepted CAL/RT equations and alias exclusions are reused unchanged. New
work is the ordered lifetime algebra: a live word has one creator/generation,
nested formal frames are LIFO, every write is a new generation even at equal
value, and a dead slot may be reused only after an independently qualified
formal close. Supplied event/source predicates remain explicit hypotheses.
No function reads memory, pops an actual frame, retires an instruction, or
turns a detached RT frontier into a path from the full helper entry.
"""
from copy import deepcopy

from enclosing_caller_return.call_return_obligations import FRAME_SOURCE, frame_alias
from enclosing_caller_return.state import input_class, label, need, number, shape, tri
from indexed_suffix_ie_provenance.return_obligations import SUFFIX_ALIAS_WORDS
from shadow_cold_reacquisition.helper_5cd9 import FRAME_ALIASES, FRAME_SOURCE as HELPER_FRAME_SOURCE

COMPLETE = 'CompleteConditional'
UNKNOWN = 'IndeterminateObligation'
OUTSIDE = 'OutsideVerifiedScope'
CLASSIFICATION = 'FormalCalRtLifetimeOnly_NotSourceIngressOrNativeReturn'
CALLS = {
    0x276A: (0x5C86, 0x5CCD, FRAME_SOURCE),
    0x2777: (0x5CD9, 0x5CF9, HELPER_FRAME_SOURCE),
    0x27D0: (0x5F45, 0x60E4, FRAME_SOURCE),
}
CLAIMS = ('ConditionalOnly', 'NativeReturn', 'ActualExecution', 'ActualHardware')
BOUNDARIES = ('Unestablished', 'ConditionalSourceFrontier', 'DetachedNormalFrontier',
              'FaultFrontier', 'HostSelected')
FIELDS = ('inputClass', 'sourceBinding', 'callerPc', 'declaredTarget', 'returnSitePc',
          'incomingSsp', 'sspBeforeReturn', 'frame', 'returnEvidence', 'boundary',
          'premises', 'ieHandoffs', 'events', 'claim')
PREMISES = ('stackMemoryApplicable', 'noAsyncInterference', 'windowComplete')
EVENT_FIELDS = {
    'Write': ('kind', 'address', 'widthBits', 'value', 'generation', 'sourceQualified'),
    'NestedCall': ('kind', 'creatorPc', 'targetPc', 'generation', 'memoryApplicable', 'sourceQualified'),
    'NestedReturn': ('kind', 'creatorPc', 'generation', 'savedReturnWord', 'sourceQualified'),
    'SspMutation': ('kind', 'ssp', 'sourceQualified'),
}
GAPS = ('NativeFrameOwnerUnestablished', 'ActualCallReturnAndFramePopNotPerformed',
        'DeviceMemoryAndPhysicalSfApplicabilityRemainConditional',
        'SourceIngressAndHardwareInterferenceNotProvedByFormalEvents')


def _validate(query):
    shape(query, FIELDS, 'ClosedFrameLifetimeQueryRequired')
    input_class(query['inputClass'])
    need(label(query['sourceBinding']) and query['claim'] in CLAIMS, 'TypedFrameLifetimeClaimRequired')
    need(all(number(query[key], 0xFFFF) for key in (
        'callerPc', 'declaredTarget', 'returnSitePc', 'incomingSsp', 'sspBeforeReturn')),
        'TypedFrameLifetimeWordsRequired')
    frame = query['frame']
    shape(frame, ('kind', 'address', 'creatorPc', 'savedReturnWord', 'generation'), 'ClosedLifetimeFrameRequired')
    need(frame['kind'] in ('NormalCall', 'Interrupt') and label(frame['generation'])
         and all(number(frame[key], 0xFFFF) for key in ('address', 'creatorPc', 'savedReturnWord')),
         'TypedLifetimeFrameRequired')
    observed = query['returnEvidence']
    shape(observed, ('address', 'creatorPc', 'savedReturnWord', 'generation'), 'ClosedFormalReturnEvidenceRequired')
    need(label(observed['generation']) and all(number(observed[key], 0xFFFF)
         for key in ('address', 'creatorPc', 'savedReturnWord')), 'TypedFormalReturnEvidenceRequired')
    boundary = query['boundary']
    shape(boundary, ('kind', 'pc', 'sourceQualified', 'evidenceId'), 'ClosedFrameBoundaryRequired')
    need(boundary['kind'] in BOUNDARIES and number(boundary['pc'], 0xFFFF)
         and tri(boundary['sourceQualified']) and label(boundary['evidenceId']), 'TypedFrameBoundaryRequired')
    shape(query['premises'], PREMISES, 'ClosedLifetimePremisesRequired')
    need(all(tri(value) for value in query['premises'].values()), 'TypedLifetimePremisesRequired')
    shape(query['ieHandoffs'], ('first5cb9', 'second5ccb'), 'TwoSeparateIeHandoffsRequired')
    need(all(tri(value) for value in query['ieHandoffs'].values()), 'TypedSeparateIeHandoffsRequired')
    events = query['events']
    need(type(events) is list and len(events) <= 32, 'BoundedFormalLifetimeEventsRequired')
    for event in events:
        need(type(event) is dict and type(event.get('kind')) is str
             and event['kind'] in EVENT_FIELDS, 'ClosedFormalEventKindRequired')
        shape(event, EVENT_FIELDS[event['kind']], 'ClosedFormalLifetimeEventRequired')
        need(tri(event['sourceQualified']), 'TypedEventSourcePremiseRequired')
        if event['kind'] == 'Write':
            need(number(event['address'], 0xFFFF) and type(event['widthBits']) is int
                 and event['widthBits'] in (8, 16) and number(event['value'], (1 << event['widthBits']) - 1)
                 and label(event['generation']), 'TypedFormalWriterRequired')
        elif event['kind'] == 'NestedCall':
            need(number(event['creatorPc'], 0xFFFF) and number(event['targetPc'], 0xFFFF)
                 and label(event['generation']) and tri(event['memoryApplicable']), 'TypedNestedCallPremiseRequired')
        elif event['kind'] == 'NestedReturn':
            need(number(event['creatorPc'], 0xFFFF) and number(event['savedReturnWord'], 0xFFFF)
                 and label(event['generation']), 'TypedNestedReturnPremiseRequired')
        else:
            need(number(event['ssp'], 0xFFFF), 'TypedFormalSspMutationRequired')


def _footprint(address, width):
    base = address & 0xFFFE if width == 16 else address
    return base, frozenset((base + offset) & 0xFFFF for offset in range(width // 8))


def _alias(address, caller):
    alias = frame_alias(address, caller == 0x27D0)
    if alias != 'OrdinaryDataCandidate':
        return alias
    if caller == 0x276A and address in SUFFIX_ALIAS_WORDS:
        return 'IndexedSuffixFrameAlias'
    if caller == 0x2777 and address in FRAME_ALIASES:
        return 'HelperInputOrFaultAlias'
    if address == 0x4700:
        return 'ExternalDataApplicabilityUnknown'
    return alias


def helper_rt_frame_lifetime(query):
    """Evaluate one closed formal event window, preserving all blocked edges.

NestedCall uses the ordinary three-byte CAL equation with a supplied creator
and target, not a decoded/new source edge. Its return must consume the newest
live generation; matching values from another/dead creator never suffice.
The result's sourcePathEstablished is always false, including a successful
local lifetime at an explicitly detached normal frontier.
"""
    _validate(query)
    caller, frame = query['callerPc'], query['frame']
    sites = CALLS.get(caller)
    target, rt = (None, None) if sites is None else sites[:2]
    candidate = None if sites is None else (caller + 3) & 0xFFFF
    incoming, pre_rt = query['incomingSsp'], query['sspBeforeReturn']
    address = None if incoming is None else incoming & 0xFFFE
    after_call = None if incoming is None else (incoming - 2) & 0xFFFF
    after_rt = None if pre_rt is None else (pre_rt + 2) & 0xFFFF
    geometry = {'incomingSsp': incoming, 'frameAddress': address, 'sspAfterCall': after_call,
                'sspBeforeReturn': pre_rt, 'returnReadAddress': None if after_rt is None else after_rt & 0xFFFE,
                'sspAfterReturn': after_rt, 'savedReturnWord': frame['savedReturnWord'],
                'candidateReturnPc': candidate}
    alias = None if address is None or sites is None else _alias(address, caller)
    state = {'symbolicSsp': after_call, 'liveFrameGenerations': [], 'frameGenerationRetained': None,
             'balancedNesting': None, 'formalReturnedPc': None, 'lifetimeClosedConditionally': False}
    journal, live = [], []
    stop = 'STOP_BEFORE_CAL_UNKNOWN' if sites is None else f'STOP_BEFORE_RT_{rt:04X}'

    def finish(status, reason, boundary=None):
        state['liveFrameGenerations'] = [item['generation'] for item in live]
        return deepcopy({'procedure': 'helper_rt_frame_lifetime', 'classification': CLASSIFICATION,
            'status': status, 'reason': reason, 'sourceBinding': query['sourceBinding'],
            'callerPc': caller, 'calleeEntryPc': target, 'returnSitePc': rt, 'geometry': geometry,
            'frameGeneration': frame['generation'], 'frameAlias': alias, 'state': state,
            'formalEvents': journal, 'boundary': query['boundary'], 'stopBoundary': boundary or stop,
            'unresolvedConstraints': list(GAPS) + ([] if status == COMPLETE else [reason]),
            'formalConstraintsSatisfied': status == COMPLETE, 'sourcePathEstablished': False,
            'sourceChainEstablished': False, 'nativeFrameOwnerEstablished': False, 'actualFramePop': None})

    if query['claim'] != 'ConditionalOnly':
        return finish(OUTSIDE, 'NonConditionalFrameLifetimeClaim')
    if sites is None:
        return finish(OUTSIDE, 'UnreviewedFrameCreator')
    if query['sourceBinding'] is None:
        return finish(UNKNOWN, 'FrameSourceBindingMissing')
    if query['sourceBinding'] != sites[2]:
        return finish(OUTSIDE, 'FrameSourceBindingMismatch')
    if None in (query['declaredTarget'], query['returnSitePc']):
        return finish(UNKNOWN, 'CallReturnSitesUnknown')
    if (query['declaredTarget'], query['returnSitePc']) != (target, rt):
        return finish(OUTSIDE, 'CallReturnSitesMismatch')
    if frame['kind'] != 'NormalCall':
        return finish(OUTSIDE, 'InterruptFrameIsNotOrdinaryCalRt')
    if incoming is None or pre_rt is None:
        return finish(UNKNOWN, 'StackPointerUnknown')
    if None in (frame['address'], frame['creatorPc'], frame['savedReturnWord'], frame['generation']):
        return finish(UNKNOWN, 'FrameCreatorWordOrGenerationUnknown')
    if frame['address'] != address:
        return finish(OUTSIDE, 'AlignedFrameAddressMismatch')
    if frame['creatorPc'] != caller or frame['savedReturnWord'] != candidate:
        return finish(OUTSIDE, 'FrameCreatorOrSavedWordMismatch')
    if alias != 'OrdinaryDataCandidate':
        return finish(OUTSIDE, 'FrameAliasNotExcluded')
    if caller != 0x276A and any(value is not None for value in query['ieHandoffs'].values()):
        return finish(OUTSIDE, 'IePremiseBelongsToDifferentFrame')
    for premise in PREMISES:
        if query['premises'][premise] is not True:
            return finish(UNKNOWN, 'LifetimePremiseUnestablished:' + premise)
    root = {'creatorPc': caller, 'address': address, 'savedReturnWord': candidate,
            'generation': frame['generation'], 'incomingSsp': incoming}
    live.append(root)
    used = {frame['generation']}
    state['frameGenerationRetained'] = True
    journal.append({'kind': 'FormalCalCreate', 'creatorPc': caller, 'address': address,
                    'savedReturnWord': candidate, 'generation': frame['generation'],
                    'sspBefore': incoming, 'sspAfter': after_call})
    for ordinal, event in enumerate(query['events']):
        kind = event['kind']
        if event['sourceQualified'] is False:
            journal.append({'kind': kind, 'ordinal': ordinal, 'effect': 'ExcludedBySourcePremise'})
            continue
        if event['sourceQualified'] is not True:
            state['frameGenerationRetained'] = None
            return finish(UNKNOWN, 'EventSourceQualificationUnknown')
        current = state['symbolicSsp']
        if kind in ('Write', 'NestedCall'):
            generation = event['generation']
            if generation is None:
                return finish(UNKNOWN, 'EventGenerationUnknown')
            if generation in used:
                return finish(OUTSIDE, 'FormalGenerationReused')
            used.add(generation)
        if kind == 'Write':
            if event['address'] is None:
                state['frameGenerationRetained'] = None
                return finish(UNKNOWN, 'WriterAddressUnknown')
            base, touched = _footprint(event['address'], event['widthBits'])
            overlaps = [item for item in live if touched & {item['address'], item['address'] + 1}]
            journal.append({'kind': 'FormalWrite', 'ordinal': ordinal, 'address': base,
                            'widthBits': event['widthBits'], 'generation': generation,
                            'overlappedGenerations': [item['generation'] for item in overlaps],
                            'equalValueDoesNotPreserveGeneration': True})
            if overlaps:
                state['frameGenerationRetained'] = False if root in overlaps else True
                return finish(OUTSIDE, 'LiveFrameGenerationOverwritten')
            if any(byte < 0xC0 or byte == 0x4700 for byte in touched):
                return finish(OUTSIDE, 'WriterControlOrPeripheralAlias')
        elif kind == 'NestedCall':
            if None in (event['creatorPc'], event['targetPc']) or event['memoryApplicable'] is not True:
                return finish(UNKNOWN, 'NestedCallPremisesUnestablished')
            nested_address, touched = _footprint(current, 16)
            if any(touched & {item['address'], item['address'] + 1} for item in live):
                return finish(OUTSIDE, 'NestedFrameOverlapsLiveFrame')
            if _alias(nested_address, caller) != 'OrdinaryDataCandidate':
                return finish(OUTSIDE, 'NestedFrameAliasNotExcluded')
            nested = {'creatorPc': event['creatorPc'], 'address': nested_address,
                      'savedReturnWord': (event['creatorPc'] + 3) & 0xFFFF,
                      'generation': generation, 'incomingSsp': current}
            live.append(nested)
            state['symbolicSsp'] = (current - 2) & 0xFFFF
            journal.append({'kind': 'FormalNestedCalCreate', 'ordinal': ordinal,
                            'creatorPc': nested['creatorPc'], 'targetPc': event['targetPc'],
                            'address': nested_address, 'savedReturnWord': nested['savedReturnWord'],
                            'generation': generation, 'sspBefore': current,
                            'sspAfter': state['symbolicSsp'], 'encodedSourceEdgeEstablished': False})
        elif kind == 'NestedReturn':
            if len(live) == 1:
                return finish(OUTSIDE, 'NestedReturnWithoutLiveNestedFrame')
            if None in (event['creatorPc'], event['generation'], event['savedReturnWord']):
                return finish(UNKNOWN, 'NestedReturnOwnerOrWordUnknown')
            nested = live[-1]
            if (event['creatorPc'], event['generation'], event['savedReturnWord']) != (
                    nested['creatorPc'], nested['generation'], nested['savedReturnWord']):
                return finish(OUTSIDE, 'NestedReturnLifoOwnerMismatch')
            returned = (current + 2) & 0xFFFF
            if returned != nested['incomingSsp'] or returned & 0xFFFE != nested['address']:
                return finish(OUTSIDE, 'NestedReturnStackGeometryMismatch')
            live.pop()  # Formal lifetime bookkeeping only; never a machine/frame pop.
            state['symbolicSsp'] = returned
            journal.append({'kind': 'FormalNestedLifetimeClose', 'ordinal': ordinal,
                            'generation': nested['generation'], 'address': nested['address'],
                            'candidateReturnPc': nested['savedReturnWord'], 'sspBefore': current,
                            'sspAfter': returned})
        else:
            if event['ssp'] is None:
                state['symbolicSsp'] = None
                return finish(UNKNOWN, 'SspMutationValueUnknown')
            state['symbolicSsp'] = event['ssp']
            journal.append({'kind': 'FormalSspMutation', 'ordinal': ordinal,
                            'sspBefore': current, 'sspAfter': event['ssp']})
    state['balancedNesting'] = len(live) == 1
    if len(live) != 1:
        return finish(OUTSIDE, 'UnclosedNestedFrame')
    if state['symbolicSsp'] != pre_rt or pre_rt != after_call:
        return finish(OUTSIDE, 'FinalStackPointerMismatch')
    observed = query['returnEvidence']
    if any(value is None for value in observed.values()):
        return finish(UNKNOWN, 'ReturnReadOwnerOrWordUnknown')
    if observed['address'] != geometry['returnReadAddress']:
        return finish(OUTSIDE, 'ReturnReadAlignmentMismatch')
    if (observed['creatorPc'], observed['generation'], observed['savedReturnWord']) != (
            caller, frame['generation'], candidate):
        return finish(OUTSIDE, 'ReturnReadCreatorWordOrGenerationMismatch')
    boundary = query['boundary']
    if boundary['kind'] == 'HostSelected':
        return finish(OUTSIDE, 'HostSelectedPcIsNotReturnFrontier')
    if boundary['kind'] == 'FaultFrontier' or boundary['pc'] == 0x5CF8:
        return finish(OUTSIDE, 'FaultFrontierCannotReturn', 'STOP_BEFORE_BRK_5CF8')
    if caller == 0x276A:
        if query['ieHandoffs']['first5cb9'] is not True:
            return finish(UNKNOWN, 'FirstIeSoftwareHandoffUnestablished', 'STOP_BEFORE_IE_WRITE_5CB9')
        if query['ieHandoffs']['second5ccb'] is not True:
            return finish(UNKNOWN, 'SecondIeSoftwareHandoffUnestablished', 'STOP_BEFORE_IE_WRITE_5CCB')
    if (boundary['kind'] == 'Unestablished' or boundary['pc'] is None
            or boundary['sourceQualified'] is not True or boundary['evidenceId'] is None):
        return finish(UNKNOWN, 'ExplicitReturnFrontierUnestablished')
    if boundary['pc'] != rt:
        return finish(OUTSIDE, 'ReturnFrontierSiteMismatch')
    if caller == 0x2777 and boundary['kind'] != 'DetachedNormalFrontier':
        return finish(UNKNOWN, 'FullHelperNormalIngressUnestablished', 'STOP_BEFORE_JGT_5CDF')
    if caller != 0x2777 and boundary['kind'] != 'ConditionalSourceFrontier':
        return finish(OUTSIDE, 'ReturnFrontierClassMismatch')
    journal.append({'kind': 'FormalLifetimeClose', 'generation': frame['generation'],
                    'address': address, 'candidateReturnPc': candidate,
                    'sspBefore': pre_rt, 'sspAfter': after_rt,
                    'frontierClass': boundary['kind'], 'actualFramePop': None})
    live.clear()
    state.update(symbolicSsp=after_rt, formalReturnedPc=candidate, lifetimeClosedConditionally=True)
    return finish(COMPLETE, 'FormalLifetimeConstraintsSatisfied')


def cold_multi_frame_chain(query):
    """Relate three separate formal lifetimes, without asserting an achieved chain.

All frames are evaluated independently so an unresolved helper ingress cannot
erase the independently useful indexed or mode-frame constraints. Pairwise
relations test SSP continuity and unique generations across dead-slot reuse.
The helper's detached frontier stays a mandatory missing source handoff even
when every supplied arithmetic/ownership premise is internally consistent.
"""
    shape(query, ('inputClass', 'frames', 'handoffs', 'claim'), 'ClosedMultiFrameChainRequired')
    input_class(query['inputClass'])
    need(query['claim'] in CLAIMS, 'TypedMultiFrameClaimRequired')
    frames, handoffs = query['frames'], query['handoffs']
    need(type(frames) is list and len(frames) == 3 and type(handoffs) is list and len(handoffs) == 2,
         'ExactlyThreeFramesAndTwoHandoffsRequired')
    for frame in frames:
        _validate(frame)
        need(frame['inputClass'] == query['inputClass'], 'MatchingMultiFrameInputClassRequired')
    for handoff in handoffs:
        shape(handoff, ('fromPc', 'toPc', 'stackContinuity', 'sourceQualified', 'evidenceId'),
              'ClosedIntercallHandoffRequired')
        need(number(handoff['fromPc'], 0xFFFF) and number(handoff['toPc'], 0xFFFF)
             and tri(handoff['stackContinuity']) and tri(handoff['sourceQualified'])
             and label(handoff['evidenceId']), 'TypedIntercallHandoffRequired')
    results = [helper_rt_frame_lifetime(frame) for frame in frames]
    relations = []
    status, reason = UNKNOWN, 'FullHelperIngressStillUnestablished'
    formal_complete = False
    missing = 'FullHelper5CD9ToDetachedRT5CF9'
    stop = 'STOP_BEFORE_CAL_276A'
    if query['claim'] != 'ConditionalOnly':
        status, reason = OUTSIDE, 'NonConditionalMultiFrameClaim'
    elif [frame['callerPc'] for frame in frames] != [0x276A, 0x2777, 0x27D0]:
        status, reason = OUTSIDE, 'SequentialFrameCreatorsMismatch'
    else:
        generations = [frame['frame']['generation'] for frame in frames]
        if None in generations:
            reason = 'MultiFrameGenerationUnknown'
        elif len(set(generations)) != 3:
            status, reason = OUTSIDE, 'SequentialFrameGenerationReused'
        else:
            first_bad = next((row for row in results if row['status'] != COMPLETE), None)
            if first_bad is not None:
                status, reason, missing = first_bad['status'], first_bad['reason'], first_bad['stopBoundary']
                stop = first_bad['stopBoundary']
            else:
                formal_complete = True
                stop = 'STOP_BEFORE_JGT_5CDF'
            created = set()
            for row in results:
                for event in row['formalEvents']:
                    if event['kind'] not in ('FormalCalCreate', 'FormalWrite', 'FormalNestedCalCreate'):
                        continue
                    generation = event['generation']
                    if generation in created and formal_complete:
                        status, reason = OUTSIDE, 'CrossLifetimeGenerationReused'
                        missing = 'DistinctGenerationForEveryFormalWriter'
                        stop = f"STOP_BEFORE_CAL_{row['callerPc']:04X}"
                        formal_complete = False
                    created.add(generation)
            for index, handoff in enumerate(handoffs):
                left, right = results[index:index + 2]
                from_pc, to_pc = ((0x276D, 0x2777), (0x277A, 0x27D0))[index]
                a, b = left['geometry']['frameAddress'], right['geometry']['frameAddress']
                relation = {'fromPc': from_pc, 'toPc': to_pc, 'sameAlignedSlot': None if a is None or b is None else a == b,
                            'oldGeneration': generations[index], 'newGeneration': generations[index + 1],
                            'priorLifetimeClosedConditionally': left['state']['lifetimeClosedConditionally'],
                            'stackPointerMatches': left['geometry']['sspAfterReturn'] == right['geometry']['incomingSsp']
                            if None not in (left['geometry']['sspAfterReturn'], right['geometry']['incomingSsp']) else None,
                            'suppliedHandoffQualified': handoff['sourceQualified'] is True
                            and handoff['stackContinuity'] is True and handoff['evidenceId'] is not None,
                            'sourceConnectionEstablished': False}
                relations.append(relation)
                failure = None
                if (handoff['fromPc'], handoff['toPc']) != (from_pc, to_pc):
                    failure = (OUTSIDE, 'IntercallSourceEndpointsMismatch')
                elif not relation['suppliedHandoffQualified']:
                    failure = (UNKNOWN, 'IntercallHandoffPremiseUnestablished')
                elif relation['stackPointerMatches'] is not True:
                    failure = (UNKNOWN if relation['stackPointerMatches'] is None else OUTSIDE, 'IntercallStackPointerMismatch')
                if failure is not None and formal_complete:
                    status, reason = failure
                    missing = f'Intercall_{from_pc:04X}_{to_pc:04X}'
                    # A later formal obligation does not advance the source entry.
                    stop = 'STOP_BEFORE_CAL_276A'
                    formal_complete = False
    return deepcopy({'procedure': 'cold_multi_frame_chain', 'classification': CLASSIFICATION,
        'status': status, 'reason': reason, 'frameResults': results, 'pairwiseRelations': relations,
        'formalSequenceConstraintsSatisfied': formal_complete, 'firstMissingHandoff': missing,
        'sourceChainEstablished': False, 'nativeFrameOwnerEstablished': False, 'actualFramePop': None,
        'unresolvedConstraints': ['C8PrimaryConflictUnresolved', 'FullHelperNormalIngressUnestablished', *GAPS],
        'stopBoundary': stop})
