"""Last declared slot writer across conditional boundaries, not a native trace."""
from copy import deepcopy
from length_checksum_dataflow.state import identifier
from .state import COMMON, inherited, need, number

EFFECT = 'ConditionalBoundaryTimeline_NotCpuObservations'


def label(value):
    return value is None or type(value) is str and bool(value)


def last_writer_at_conditional_boundary(query):
    need(type(query) is dict and set(query) == {'inputClass', 'initial', 'events', 'noInterference', 'claim'},
         'ClosedWriterTimelineRequired')
    need(type(query['inputClass']) is str and query['inputClass'] in inherited.INPUT_CLASSES,
         'ActualHardwareInputNotAdmitted')
    initial, events = query['initial'], query['events']
    need(type(initial) is dict and set(initial) == {'value', 'generation'}
         and number(initial['value'], 255) and label(initial['generation']), 'ExplicitInitialSlotRequired')
    need(query['noInterference'] is None or type(query['noInterference']) is bool,
         'ConditionalInterferencePremiseRequired')
    need(type(query['claim']) is str and query['claim'] in {
        'ConditionalOnly', 'Confirmed026CConsumer', 'PayloadArray', 'Fifo', 'ActualExecution'}, 'ClosedClaimRequired')
    need(type(events) is list and 1 <= len(events) <= 32, 'BoundedWriterTimelineRequired')
    seen_ids = set()
    shapes = {'GenericStore': {'kind', 'id', 'value', 'generation', 'lrb', 'dd'},
              'AlternateStore': {'kind', 'id', 'address', 'widthBits', 'value', 'generation'},
              'UnknownWriter': {'kind', 'id'}, 'ConsumerBoundary': {'kind', 'id', 'requestedGeneration'}}
    for event in events:
        need(type(event) is dict and type(event.get('kind')) is str and event['kind'] in shapes
             and set(event) == shapes[event['kind']] and identifier(event['id']) and event['id'] not in seen_ids,
             'TypedUniqueTimelineEventRequired')
        seen_ids.add(event['id'])
        kind = event['kind']
        if kind == 'GenericStore':
            need(number(event['value'], 255) and label(event['generation']) and number(event['lrb'], 65535)
                 and number(event['dd'], 1), 'TypedGenericWriterRequired')
        elif kind == 'AlternateStore':
            need(type(event['address']) is int and event['address'] in (0x3F3, 0x3F4, 0x3F5, 0x3F6)
                 and type(event['widthBits']) is int and event['widthBits'] in (8, 16)
                 and number(event['value'], (1 << event['widthBits']) - 1) and label(event['generation']),
                 'TypedAliasWriterRequired')
        elif kind == 'ConsumerBoundary':
            need(label(event['requestedGeneration']), 'TypedRequestedGenerationRequired')
    state = {'lastValue': initial['value'], 'lastGeneration': initial['generation'], 'lastKind': 'InitialUnbound'}
    journal, reads, history = [], [], []
    used = set() if initial['generation'] is None else {initial['generation']}
    status, reason, boundary = 'CompleteConditional', 'ConditionalTimelineOnly', None
    if query['claim'] != 'ConditionalOnly':
        status, reason = 'OutsideVerifiedScope', 'UnestablishedAuthorityClaim'
    else:
        for index, event in enumerate(events):
            kind = event['kind']
            if kind == 'GenericStore' and (event['lrb'] != 0x7E or event['dd'] != 0):
                status, reason, boundary = 'OutsideVerifiedScope', 'ProducerContextNotEstablished', index
                break
            if kind in ('GenericStore', 'AlternateStore'):
                generation = event['generation']
                if generation is not None and generation in used:
                    status, reason, boundary = 'OutsideVerifiedScope', 'WriterGenerationReused', index
                    break
                if generation is not None:
                    used.add(generation)
            if kind == 'ConsumerBoundary':
                current = state['lastGeneration']
                relation = ('InterferenceNotExcluded' if query['noInterference'] is not True else
                    'UnknownInterveningWriter' if state['lastKind'] == 'UnknownWriter' else
                    'MissingProducerGeneration' if current is None else
                    'StaleOrUnboundRequestedGeneration' if event['requestedGeneration'] != current else
                    'AlternateWriterNot026C' if state['lastKind'] != 'GenericStore' else
                    'ConditionalLastWriterAtBoundary')
                reads.append({'eventId': event['id'], 'sourcePc': 0x28DB, 'address': 0x3F4,
                    'widthBits': 8, 'value': state['lastValue'], 'generation': current,
                    'requestedGeneration': event['requestedGeneration'], 'relation': relation,
                    'effectClass': 'ConditionalBoundaryObservation_NotCpuRead'})
            else:
                before, before_gen = state['lastValue'], state['lastGeneration']
                if kind == 'UnknownWriter':
                    address = width = value = overlap = same = None
                    state.update(lastValue=None, lastGeneration=None, lastKind=kind)
                else:
                    width = 8 if kind == 'GenericStore' else event['widthBits']
                    address = 0x3F4 if kind == 'GenericStore' else event['address']
                    address = address & 0xFFFE if width == 16 else address
                    value = event['value']
                    overlap = address <= 0x3F4 < address + width // 8
                    if overlap:
                        tracked = None if value is None else value >> (8 * (0x3F4 - address)) & 255
                        state.update(lastValue=tracked, lastGeneration=event['generation'], lastKind=kind)
                    same = before == state['lastValue'] if overlap and before is not None and state['lastValue'] is not None else None
                journal.append({'ordinal': len(journal) + 1, 'eventId': event['id'], 'kind': kind,
                    'sourcePc': 0x26C if kind == 'GenericStore' else None, 'address': address,
                    'widthBits': width, 'declaredValue': value, 'beforeTrackedByte': before,
                    'afterTrackedByte': state['lastValue'], 'beforeGeneration': before_gen,
                    'afterGeneration': state['lastGeneration'], 'targetOverlap': overlap,
                    'sameTrackedByteValue': same, 'effectClass': EFFECT})
            history.append({'eventId': event['id'], 'eventIndex': index, 'state': deepcopy(state)})
    constraints = [*COMMON, 'NativeCfgEdge026CTo28DBNotEstablished', 'OnlyLastSlotModeled_NotArrayOrFifo']
    if status != 'CompleteConditional' and reason not in constraints:
        constraints.append(reason)
    return {'procedure': 'last_writer_at_conditional_boundary', 'status': status, 'reason': reason,
        'boundary': boundary, 'inputClass': query['inputClass'], 'sourceScope': [0x26C, 0x28DB],
        'state': state, 'journal': journal, 'reads': reads, 'intermediateStates': history,
        'unresolvedConstraints': constraints, 'effectClass': EFFECT, 'actualHardwareObservation': None,
        'cpuInstructionRetirements': 0, 'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False}
