"""Keep indexed and helper return authorities distinct in a cold source join."""
from enclosing_caller_return.state import STATE_FIELDS, input_class, need, shape, tri
from indexed_suffix_ie_provenance.return_obligations import indexed_return_obligations
from shadow_cold_reacquisition.cold_reacquisition import cold_reacquisition_step, projected_generations
from shadow_cold_reacquisition.helper_5cd9 import rt5cf9_obligations

from .c8_helper import helper_5cd9_extended
from .wire import result

OUTSIDE = 'OutsideVerifiedScope'
UNKNOWN = 'IndeterminateObligation'
COMPLETE = 'CompleteConditional'
CLAIMS = ('ConditionalOnly', 'NativeReturn', 'NativeModeReach', 'ActualHardware')
FRAME_SCOPE = (0x276A, 0x276D, 0x2777, 0x277A, 0x5CB9, 0x5CCB, 0x5CCD, 0x5CF9)
JOIN_SCOPE = (0x276A, 0x276D, 0x276F, 0x2771, 0x2773, 0x2777, 0x277A, 0x27B2, 0x27D0,
              0x5C86, 0x5CB9, 0x5CCB, 0x5CCD, 0x5CD9, 0x5CF8, 0x5CF9, 0x5F45, 0x60CC)
FRAME_GAPS = ('IePolicyAndNativeStackUnbound', 'NativeColdContinuityUnobserved')
JOIN_GAPS = ('NativeIndexedReturnUnobserved', 'NativeHelperReturnUnobserved', 'NativeModeRead60ccUnbound')


def cold_return_path_obligations(query):
    """Check two hypothetical ordinary frames without admitting either source path."""
    shape(query, ('inputClass', 'indexedFrame', 'helperFrame', 'indexedIeBoundary', 'helperNormalBoundary',
                  'stackContinuity', 'claim'), 'ClosedColdReturnObligationsRequired')
    input_class(query['inputClass'])
    need(query['claim'] in CLAIMS and all(tri(query[key]) for key in (
        'indexedIeBoundary', 'helperNormalBoundary', 'stackContinuity')), 'TypedColdReturnObligationsRequired')
    indexed_query, helper_query = query['indexedFrame'], query['helperFrame']
    need(type(indexed_query) is dict and type(helper_query) is dict
         and indexed_query.get('inputClass') == helper_query.get('inputClass') == query['inputClass'],
         'MatchingColdReturnInputClassRequired')
    indexed = indexed_return_obligations(indexed_query)
    helper = rt5cf9_obligations(helper_query)
    indexed_input, helper_input = indexed_query['frameQuery'], helper_query['frameQuery']
    first, second = indexed_input['incomingSsp'], helper_input['incomingSsp']
    ip, hp = indexed['state']['formalReturnedPc'], helper['state']['formalReturnedPc']
    indexed_admitted = query['claim'] == 'ConditionalOnly' and query['indexedIeBoundary'] is True and ip == 0x276D
    state = {'formalIndexedPc': 0x276D if indexed_admitted else None, 'formalHelperPc': None,
             'sspBetweenCalls': None, 'nativeContinuity': None}
    boundary = 'STOP_BEFORE_RT_5CCD'
    if query['claim'] != 'ConditionalOnly':
        status, reason = OUTSIDE, 'NonConditionalReturnClaim'
    elif indexed_input['callerPc'] != 0x276A:
        status, reason = OUTSIDE, 'ColdIndexedCallerMismatch'
    elif query['indexedIeBoundary'] is not True:
        status, reason = UNKNOWN, 'IndexedIeHandoffUnestablished'
    elif ip != 0x276D:
        status, reason = UNKNOWN, 'IndexedFrameUnestablished'
    else:
        boundary = 'STOP_BEFORE_RT_5CF9'
        if helper_query['helperBoundary'] == 0x5CF8:
            status, reason, boundary = OUTSIDE, 'FaultCannotReturn', 'STOP_BEFORE_BRK_5CF8'
        elif query['helperNormalBoundary'] is not True or hp != 0x277A:
            status, reason = UNKNOWN, 'HelperNormalFrameUnestablished'
        elif query['stackContinuity'] is not True:
            status, reason = UNKNOWN, 'IntercallStackContinuityUnestablished'
        elif first != second:
            status, reason = OUTSIDE, 'IntercallStackPointerMismatch'
        elif indexed_input['frame']['generation'] == helper_input['frame']['generation']:
            status, reason = OUTSIDE, 'ColdFrameGenerationReused'
        else:
            status, reason = COMPLETE, 'MatchingHypotheticalColdFrames'
            state.update(formalHelperPc=0x277A, sspBetweenCalls=first)
    return result(status, source_scope=FRAME_SCOPE, evidence_class='StaticFormalSourceObligation', caller=0x276A,
                  state=state, stop=boundary, obligations=indexed['formalObligations'] + helper['formalObligations'],
                  unresolved=FRAME_GAPS if status == COMPLETE else (*FRAME_GAPS, reason),
                  generations={'indexedFrame': indexed_input['frame']['generation'],
                               'helperFrame': helper_input['frame']['generation']},
                  reason=reason, indexedFrameResult=indexed, helperFrameResult=helper)


def cold_caller_mode_source_join(query):
    """Carry frozen cold state under a hypothetical state-preserving CAL handoff."""
    shape(query, ('inputClass', 'coldQuery', 'helperArgs', 'helperHandoff', 'claim'), 'ClosedColdModeJoinRequired')
    input_class(query['inputClass'])
    need(query['claim'] in CLAIMS and tri(query['helperHandoff']), 'TypedColdModeJoinPremisesRequired')
    cold_query, args = query['coldQuery'], query['helperArgs']
    need(type(cold_query) is dict and cold_query.get('inputClass') == query['inputClass'],
         'MatchingColdModeJoinInputClassRequired')
    if args is not None:
        shape(args, ('invocationId', 'lineage', 'thresholds', 'errorByte'), 'ClosedColdHelperArgsRequired')

    cold = helper = None
    edges = [{'from': 0x276A, 'to': 0x5C86, 'class': 'ConfirmedStaticCFG'},
             {'from': 0x5CCD, 'to': 0x276D, 'class': 'FormalReturnCandidate'},
             {'from': 0x2777, 'to': 0x5CD9, 'class': 'ConfirmedStaticCFG'},
             {'from': 0x5CF9, 'to': 0x277A, 'class': 'FormalReturnCandidate'},
             {'from': 0x277A, 'to': 0x27D0, 'class': 'SourceUnbound'},
             {'from': 0x27D0, 'to': 0x5F45, 'class': 'ConfirmedStaticCFG'}]

    def finish(status, reason, stop):
        children = tuple(child for child in (cold, helper) if child is not None)
        last = children[-1] if children else {}
        carried = last.get('state')
        if helper is not None:
            # The helper's frozen snapshot excludes the cold off-page extension
            # and only reports a counter slot after an admitted counter write.
            carried = {**cold['state'], **helper['state']}
        joined = {name: [entry for child in children for entry in child[name]] for name in (
            'reads', 'orderedWrites', 'branchOutcome', 'intermediateStates', 'formalObligations')}
        sites = sorted({*JOIN_SCOPE, *(pc for child in children for pc in child['sourceScope'])})
        return result(status, source_scope=sites, caller=0x276A, state=carried, stop=stop,
                      reads=joined['reads'], writes=joined['orderedWrites'], branches=joined['branchOutcome'],
                      intermediate=joined['intermediateStates'], obligations=joined['formalObligations'],
                      generations=projected_generations(carried), iterations=() if cold is None else cold['iterations'],
                      unresolved=(*JOIN_GAPS, reason), reason=reason, sourceEdges=edges,
                      frozenColdResult=cold, helperResult=helper, modeConsumerReached=False)

    if query['claim'] != 'ConditionalOnly':
        return finish(OUTSIDE, 'NonConditionalModeJoinClaim', 'STOP_BEFORE_CAL_276A')
    cold = cold_reacquisition_step(cold_query)
    if cold['status'] != COMPLETE or cold['stopBoundary'] != 'STOP_BEFORE_CAL_2777':
        return finish(cold['status'], cold['reason'], cold['stopBoundary'])
    if query['helperHandoff'] is not True or args is None:
        return finish(UNKNOWN, 'HelperEntryHandoffUnestablished', cold['stopBoundary'])

    prior = cold['state']
    original = cold_query['prefixQuery']['snapshot']
    slot = prior['counterF7']
    snapshot = {name: prior[name] for name in STATE_FIELDS}
    snapshot.update(inputClass=query['inputClass'], assumptions=original['assumptions'])
    # The entry premise includes a disjoint prospective CAL frame and no
    # intervening writes. It is a separate hypothetical state transfer.
    counter = {'slot': slot, 'sourcePc': 0x2773, 'firstCall': True, 'noInterference': query['helperHandoff'],
               'expectedGeneration': slot['generation']}
    entry = {**args, 'inputClass': query['inputClass'], 'snapshot': snapshot,
             'entryEstablished': True, 'counterF7': counter}
    edges.append({'from': 0x2777, 'to': 0x5CD9, 'class': 'ConditionalStateHandoff'})
    helper = helper_5cd9_extended({'entry': 'Full', 'helperQuery': entry, 'detachedHandoff': None})
    return finish(helper['status'], helper['reason'], helper['stopBoundary'])
