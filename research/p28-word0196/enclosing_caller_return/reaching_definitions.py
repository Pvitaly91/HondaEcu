"""Conditional reaching definitions across two statically identified calls."""
from mode_caller_continuity.reaching_definitions import data03cb_reaching_definitions

from .call_return_obligations import call_return_obligations, frame_alias
from .state import formal_result, input_class, label, need, number, shape, tri

INDEXED_SOURCE = 'b46b8fd1a40c084195f779d17fa8ce701f728f05d153fa2ce545c85f1ae7be62'
SCOPE = (0x276A, 0x276D, 0x27D0, 0x2B64, 0x4069, 0x5C86, 0x5CB4, 0x5CB7,
         0x5CCD, 0x5F45, 0x60CC, 0x60E4, 0x2869)
PREMISES = ('coldPathPredicates', 'indexedSuffixToReturn', 'modeEntryToRead',
            'explicitHandoff', 'interveningWritersExcluded')


def indexed_to_mode_reaching_definitions(query):
    shape(query, ('inputClass', 'sourceBinding', 'indexedCallerPc', 'modeCallerPc', 'localLineage',
                  'indexedReturn', 'modeIncomingSsp', 'premises', 'claim'), 'ClosedCrossCallLineageQueryRequired')
    input_class(query['inputClass'])
    need(label(query['sourceBinding']), 'TypedLineageSourceBindingRequired')
    need(all(number(query[key], 0xFFFF) for key in ('indexedCallerPc', 'modeCallerPc', 'modeIncomingSsp')),
         'TypedCrossCallAddressRequired')
    shape(query['premises'], PREMISES, 'ClosedLineagePremisesRequired')
    need(all(tri(value) for value in query['premises'].values()), 'TypedLineagePremisesRequired')
    need(type(query['claim']) is str and query['claim'] in
         ('ConditionalOnly', 'NativeOwner', 'ActualHardware', 'RuntimeAdmission'), 'ClosedLineageClaimRequired')
    local = data03cb_reaching_definitions(query['localLineage'])
    frame = call_return_obligations(query['indexedReturn'])
    need(local['inputClass'] == frame['inputClass'] == query['inputClass'], 'SameQualifiedInputClassRequired')
    indexed, mode = query['indexedCallerPc'], query['modeCallerPc']
    pair_known = indexed in (0x276A, 0x2B64) and mode in (0x27D0, 0x4069)
    cold_pair = (indexed, mode) == (0x276A, 0x27D0)
    ssp = query['modeIncomingSsp']
    mode_address = None if ssp is None else ssp & 0xFFFE
    candidate = local['state']['lastSlot']['generation']
    state = {'candidateGeneration': candidate, 'retainedGeneration': None, 'modeFrameAddress': mode_address,
             'actualNativeData03cbOwner': None, 'nativeContinuityEstablished': False}
    edges = []
    if pair_known and query['sourceBinding'] == INDEXED_SOURCE:
        edges.extend((
            {'from': indexed, 'to': 0x5C86, 'class': 'ConfirmedCallTarget'},
            {'from': mode, 'to': 0x5F45, 'class': 'ConfirmedCallTarget'},
            {'from': 0x5CB7, 'to': 0x5CCD, 'class': 'SourceUnbound'},
        ))
        if cold_pair:
            edges.append({'from': 0x276D, 'to': 0x27D0, 'class': 'ReturnFrameDependent',
                          'via': [0x276F, 0x2771, 0x2777, 0x279E, 0x7C0B, 0x7C11, 0x27A2, 0x27B2, 0x27C3]})
        edges.extend((
            {'from': 0x5CB4, 'to': 0x60CC, 'class': 'ReachingDefinitionCandidate'},
            {'from': 0x60E4, 'to': 0x2869, 'class': 'SourceUnbound'},
        ))
    missing = [key for key in PREMISES if query['premises'][key] is not True]
    outside, obligation = 'OutsideVerifiedScope', 'IndeterminateObligation'
    boundary = None
    if query['claim'] != 'ConditionalOnly':
        status, reason = outside, 'NonConditionalLineageClaim'
    elif not pair_known:
        status, reason = outside, 'UnreviewedCallerPair'
    elif query['sourceBinding'] is None:
        status, reason = obligation, 'LineageSourceBindingMissing'
    elif query['sourceBinding'] != INDEXED_SOURCE:
        status, reason = outside, 'LineageSourceBindingMismatch'
    else:
        boundary = 0x5CB7
        if local['status'] != 'CompleteConditional':
            status, reason = local['status'], 'LocalWriterNotRetained'
        elif query['indexedReturn']['callerPc'] != indexed:
            status, reason = outside, 'IndexedFrameCallerMismatch'
        elif frame['status'] != 'CompleteConditional':
            status, reason = obligation, 'IndexedReturnUnestablished'
        elif not cold_pair:
            status, reason = obligation, 'CommonCallerPathUnestablished'
        elif mode_address is None:
            status, reason = obligation, 'ModeFrameAddressUnknown'
        elif frame_alias(mode_address, mode=True) != 'OrdinaryDataCandidate':
            status, reason = outside, 'ModeFrameAliasRequiresProof'
        elif missing:
            status, reason = obligation, 'LineagePremisesNotEstablished'
        else:
            boundary = 0x60CC
            status, reason = 'CompleteConditional', 'ConditionalColdWriterGeneration'
            state['retainedGeneration'] = candidate
    if status == 'CompleteConditional':
        unresolved = ['ActualNativeData03cbOwnerUnestablished', 'NativeCallOrderUnobserved']
    else:
        unresolved = missing if reason == 'LineagePremisesNotEstablished' else [reason]
    return formal_result('indexed_to_mode_reaching_definitions', query['inputClass'], SCOPE, status, reason,
                         boundary, state, children=(local, frame), missing=unresolved, edges=edges)
