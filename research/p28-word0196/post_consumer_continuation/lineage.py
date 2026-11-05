"""Source-window retention checks; endpoint equality is never a native observation."""
from copy import deepcopy
from .source_inventory import SITES, binding_matches
from .state import COMMON, SLOTS, frozen, label, need, slot, slot_values


def continuation_lineage(query):
    need(type(query) is dict and set(query) == {'inputClass', 'sourceBinding', 'before', 'after',
        'requestedGenerations', 'noInterference', 'claim'}, 'ClosedContinuationLineageQueryRequired')
    need(type(query['inputClass']) is str and query['inputClass'] in frozen.inherited.INPUT_CLASSES,
         'ActualHardwareInputNotAdmitted')
    need(query['sourceBinding'] is None or type(query['sourceBinding']) is dict, 'TypedSourceBindingRequired')
    for name in ('before', 'after'):
        need(type(query[name]) is dict and set(query[name]) == SLOTS, 'TwoExplicitRetentionSlotsRequired')
        for value in query[name].values():
            slot(value)
    requested = query['requestedGenerations']
    need(type(requested) is dict and set(requested) == SLOTS and all(label(v) for v in requested.values()),
         'TwoRequestedGenerationsRequired')
    need(query['noInterference'] is None or type(query['noInterference']) is bool, 'TypedRetentionPremiseRequired')
    need(type(query['claim']) is str and query['claim'] in {'ConditionalRetentionOnly', 'ParserLength',
        'ContinuationReadsF2', 'Native026COwner', 'ActualTransmit'}, 'ClosedLineageClaimRequired')
    relations = []
    for key in sorted(SLOTS):
        before, after = query['before'][key], query['after'][key]
        left, right = slot_values(before), slot_values(after)
        a, b, asked = before['generation'], after['generation'], requested[key]
        relation = ('InterferenceNotExcluded' if query['noInterference'] is not True else
            'ValueContradictsFrame' if not left & right else
            'GenerationChanged' if a is not None and b is not None and a != b else
            'GenerationNotEstablished' if a is None or b is None or asked is None else
            'StaleRequestedGeneration' if asked != b else
            'KnowledgeChangedWithoutObservation' if left != right or before['value'] != after['value']
            or before['knownBits'] != after['knownBits'] else 'ConditionalRetainedNotRead')
        relations.append({'address': int(key, 16), 'widthBits': 8,
            'aliasesIfLocalBank03F0': ['r2', 'er1.low'] if key == '03F2' else ['r4', 'er2.low'],
            'before': deepcopy(before), 'after': deepcopy(after), 'requestedGeneration': asked,
            'sourceWindowRead': False, 'sourceWindowWrite': False, 'relation': relation})
    status, reason = 'CompleteConditional', 'ConditionalSourceWindowRetentionOnly'
    if query['claim'] != 'ConditionalRetentionOnly':
        status, reason = 'OutsideVerifiedScope', 'UnestablishedLineageAuthorityClaim'
    elif query['sourceBinding'] is None:
        status, reason = 'OutsideVerifiedScope', 'SourceBindingMissing'
    elif not binding_matches(query['sourceBinding']):
        status, reason = 'OutsideVerifiedScope', 'SourceBindingMismatch'
    elif query['noInterference'] is not True:
        status, reason = 'IndeterminateLineage', 'InterferenceNotExcluded'
    elif any(r['relation'] in {'ValueContradictsFrame', 'GenerationChanged', 'StaleRequestedGeneration'} for r in relations):
        status, reason = 'OutsideVerifiedScope', 'FrameConditionViolated'
    elif any(r['relation'] != 'ConditionalRetainedNotRead' for r in relations):
        status, reason = 'IndeterminateLineage', 'RetentionObligationsNotEstablished'
    constraints = [*COMMON, 'EndpointEqualityAloneDoesNotProveLineage', 'No03F2Or03F4AccessInReviewedContinuation']
    if status != 'CompleteConditional' and reason not in constraints:
        constraints.append(reason)
    return {'procedure': 'continuation_lineage', 'status': status, 'reason': reason, 'boundary': 0x2995,
        'inputClass': query['inputClass'], 'sourceScope': list(SITES), 'state': {'relations': relations,
            'sourceWindowHasNoF2F4Access': True, 'endpointEqualityIsNotAnObservation': True,
            'native026CReachingDefinitionEstablished': False, 'parserLengthEstablished': False},
        'reads': [], 'journal': [], 'steps': [], 'intermediateStates': [], 'unresolvedConstraints': constraints,
        'effectClass': 'ConditionalSourceWindowRetention_NotNativeLineage', 'actualHardwareObservation': None,
        'cpuInstructionRetirements': 0, 'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False}
