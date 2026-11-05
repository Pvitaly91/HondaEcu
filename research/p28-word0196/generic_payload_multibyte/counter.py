"""A bounded mathematical counter/priority relation, not a parser execution loop."""
from length_checksum_dataflow.state import require

from .payload import CONSTRAINTS

MAX_DATA_STAGES = 512


def counter_route(request):
    require(type(request) is dict and set(request) == {'length', 'maxDataStages'}, 'ClosedCounterRelationRequired')
    length, limit = request['length'], request['maxDataStages']
    require(length is None or type(length) is int and 0 <= length <= 255, 'TypedLengthByteOrUnknownRequired')
    require(type(limit) is int and 0 <= limit <= MAX_DATA_STAGES, 'SyntheticCounterResourceLimit512_NotProtocolBound')
    counter, history = 2, []
    order = ['Header', 'Length']
    constraints = list(CONSTRAINTS)
    while True:
        if counter == 1:
            status, reason, outcome, boundary, reachable = ('CompleteConditional', 'VerifiedCounterPriorityRelation',
                'LengthReentrySelected', 0x27F, False)
            constraints.append('FixedLengthCompletionBlockedByLengthPriority')
            break
        if length is None:
            status, reason, outcome, boundary, reachable = ('IndeterminateBranch', 'UnknownLengthPredicate',
                'IndeterminateLength', 0x260, None)
            constraints.append(reason)
            break
        if (counter + 1) & 255 == length:
            status, reason, outcome, boundary, reachable = ('CompleteConditional', 'VerifiedCounterPriorityRelation',
                'ChecksumSelected', 0x284, True)
            order.append('Checksum')
            break
        if len(history) == limit:
            status, reason, outcome, boundary, reachable = ('OutsideVerifiedScope', 'SyntheticResourceBound_NotProtocolLimit',
                'SyntheticResourceBoundReached', 0x262, None)
            constraints.append(reason)
            break
        role = 'Flag' if counter == 2 else 'Generic'
        following = (counter + 1) & 255
        history.append({'ordinal': len(history) + 1, 'counterBefore': counter,
                        'counterAfter': following, 'role': role})
        order.append(role)
        counter = following
    flag_count = sum(row['role'] == 'Flag' for row in history)
    return {'procedure': 'counter_route', 'status': status, 'reason': reason, 'outcome': outcome,
        'length': length, 'maxDataStages': limit, 'initialCounter': 2, 'r7': 2,
        'counterHistory': history, 'stageOrder': order, 'dataStageCount': len(history),
        'flagStageCount': flag_count, 'genericStageCount': len(history) - flag_count,
        'totalStageCount': len(order), 'checksumReachable': reachable,
        'boundary': {'counter': counter, 'sourcePC': boundary}, 'reads': [], 'journal': [],
        'unresolvedConstraints': constraints, 'effectClass': 'ConditionalCounterLengthRelation_NotInstructionExecution',
        'actualHardwareObservation': None, 'cpuInstructionRetirements': 0,
        'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False}
