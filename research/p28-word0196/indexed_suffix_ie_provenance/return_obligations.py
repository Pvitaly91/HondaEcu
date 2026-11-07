"""Match the indexed CAL frame to the static RT frontier, without a pop."""
from enclosing_caller_return.call_return_obligations import call_return_obligations, validate
from enclosing_caller_return.state import input_class, label, need, number, shape, tri

from .wire import result

RT = 0x5CCD
CALLERS = (0x276A, 0x2B64)
FRAME_PREMISES = ('noInterveningFrameWrites', 'noSuffixFrameAlias')
# The page-qualified disconnected suffix uses page 0200; include both
# shadow loads as dependencies that a candidate CAL frame may not clobber.
SUFFIX_ALIAS_WORDS = frozenset((0x00F8, 0x00FA, 0x025A))


def indexed_return_obligations(query):
    shape(query, ('inputClass', 'frameQuery', 'postIeBoundary', 'expectedFrameGeneration',
                  'additionalPremises'), 'ClosedIndexedReturnQueryRequired')
    input_class(query['inputClass'])
    frame_query = query['frameQuery']
    validate(frame_query)
    need(frame_query['inputClass'] == query['inputClass'], 'MatchingFrameInputClassRequired')
    need(number(query['postIeBoundary'], 0xFFFF) and label(query['expectedFrameGeneration']),
         'TypedIndexedFrameContextRequired')
    premises = query['additionalPremises']
    shape(premises, FRAME_PREMISES, 'ClosedIndexedFramePremisesRequired')
    need(all(tri(premise) for premise in premises.values()), 'TypedIndexedFramePremisesRequired')

    caller = frame_query['callerPc']
    child = call_return_obligations(frame_query) if caller in CALLERS else None
    missing = [key for key in FRAME_PREMISES if premises[key] is not True]
    generation = frame_query['frame']['generation']
    expected = query['expectedFrameGeneration']
    alias = child is not None and child['state']['geometry']['frameAddress'] in SUFFIX_ALIAS_WORDS
    if child is None:
        status, reason = 'OutsideVerifiedScope', 'UnreviewedIndexedCaller'
    elif child['status'] != 'CompleteConditional':
        status, reason = child['status'], child['reason']
    elif query['postIeBoundary'] != RT:
        status, reason = 'IndeterminateObligation', 'HypotheticalPreRtBoundaryNotEstablished'
    elif alias:
        status, reason = 'OutsideVerifiedScope', 'IndexedSuffixFrameAlias'
    elif expected is None:
        status, reason = 'IndeterminateObligation', 'ExpectedFrameGenerationUnknown'
    elif expected != generation:
        status, reason = 'OutsideVerifiedScope', 'StaleFrameGeneration'
    elif missing:
        status, reason = 'IndeterminateObligation', 'IndexedFramePremisesNotEstablished'
    else:
        status, reason = 'CompleteConditional', 'MatchingHypotheticalIndexedFrame'
    complete = status == 'CompleteConditional'
    return result(status, source_scope=(*CALLERS, 0x5C86, RT), evidence_class='StaticFormalSourceObligation',
                  state={'callerPc': caller, 'candidateReturnPc': caller + 3 if caller in CALLERS else None,
                         'formalReturnedPc': caller + 3 if complete else None,
                         'nativeFrameOwnerEstablished': False, 'nativeReturnEstablished': False},
                  stop='STOP_BEFORE_RT_5CCD', reason=reason,
                  generations={'expectedFrame': expected, 'suppliedFrame': generation},
                  obligations=() if child is None else child['frameObligations'],
                  unresolved=(('ActualNativeFrameOwnershipUnestablished',) if complete else
                              missing if reason == 'IndexedFramePremisesNotEstablished' else (reason,)),
                  frozenFrameResult=child)
