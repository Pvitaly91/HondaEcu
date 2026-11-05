"""Conditional writer timeline at STCON; declared intent does not establish native ownership."""
from copy import deepcopy
from .source_inventory import binding_reason
from .state import formal, input_class, label, need, number, slot


def stcon_writer_lineage(query):
    need(type(query) is dict and set(query) == {'inputClass', 'sourceBinding', 'initial', 'events',
        'noInterference', 'claim'}, 'ClosedConfigurationTimelineRequired')
    input_class(query['inputClass'])
    slot(query['initial'])
    need(query['sourceBinding'] is None or type(query['sourceBinding']) is dict, 'TypedSourceBindingRequired')
    need(query['noInterference'] is None or type(query['noInterference']) is bool, 'TypedInterferencePremiseRequired')
    need(type(query['claim']) is str and query['claim'] in {'ConditionalOnly', 'NativeOwner', 'ActualTx',
        'ResetOwner', 'Rx000ATx'}, 'ClosedConfigurationClaimRequired')
    events = query['events']
    need(type(events) is list and 1 <= len(events) <= 32, 'BoundedConfigurationTimelineRequired')
    shapes = {'ConfigIntent': {'kind', 'id', 'path', 'value', 'generation', 'dd'},
        'AlternateIntent': {'kind', 'id', 'address', 'widthBits', 'value', 'generation', 'dd'},
        'UnknownWriter': {'kind', 'id'}, 'Boundary': {'kind', 'id', 'requestedGeneration'}}
    seen = set()
    for event in events:
        need(type(event) is dict and type(event.get('kind')) is str and event['kind'] in shapes
             and set(event) == shapes[event['kind']] and type(event['id']) is str and bool(event['id'])
             and event['id'] not in seen, 'TypedUniqueConfigurationEventRequired')
        seen.add(event['id'])
        kind = event['kind']
        if kind == 'ConfigIntent':
            need(type(event['path']) is str and event['path'] in ('Bit1Set', 'Bit1Clear')
                 and number(event['value'], 255) and label(event['generation']) and number(event['dd'], 1),
                 'TypedReviewedConfigurationIntentRequired')
        elif kind == 'AlternateIntent':
            need(type(event['address']) is int and event['address'] in (0x4F, 0x50, 0x51, 0x52, 0x54)
                 and type(event['widthBits']) is int and event['widthBits'] in (8, 16)
                 and number(event['value'], (1 << event['widthBits']) - 1) and label(event['generation'])
                 and number(event['dd'], 1), 'TypedAliasIntentRequired')
        elif kind == 'Boundary':
            need(label(event['requestedGeneration']), 'TypedRequestedGenerationRequired')
    state = {'lastSlot': deepcopy(query['initial']), 'lastKind': 'InitialUnbound'}
    journal, history, checks = [], [], []
    used = set() if query['initial']['generation'] is None else {query['initial']['generation']}
    status, reason, boundary = 'CompleteConditional', 'ConditionalConfigurationTimelineOnly', None
    source_error = binding_reason(query['sourceBinding'])
    if query['claim'] != 'ConditionalOnly':
        status, reason = 'OutsideVerifiedScope', 'UnestablishedConfigurationOwnershipClaim'
    elif source_error:
        status, reason = 'OutsideVerifiedScope', source_error
    else:
        for index, event in enumerate(events):
            kind = event['kind']
            if kind == 'ConfigIntent' and event['value'] != (0x1C if event['path'] == 'Bit1Set' else 0x31):
                status, reason, boundary = 'OutsideVerifiedScope', 'ConfigurationSourceValueMismatch', index
                break
            if kind in ('ConfigIntent', 'AlternateIntent'):
                width = 8 if kind == 'ConfigIntent' else event['widthBits']
                if event['dd'] != (0 if width == 8 else 1):
                    status, reason, boundary = 'OutsideVerifiedScope', 'ByteDescriptorNotEstablished', index
                    break
                generation = event['generation']
                if generation is not None and generation in used:
                    status, reason, boundary = 'OutsideVerifiedScope', 'WriterGenerationReused', index
                    break
                if generation is not None:
                    used.add(generation)
            if kind == 'Boundary':
                current = state['lastSlot']['generation']
                relation = ('InterferenceNotExcluded' if query['noInterference'] is not True else
                    'UnknownInterveningWriter' if state['lastKind'] == 'UnknownWriter' else
                    'MissingConfigurationGeneration' if current is None else
                    'StaleRequestedGeneration' if event['requestedGeneration'] != current else
                    'AlternateWriterNotReviewedConfiguration' if state['lastKind'] != 'ConfigIntent' else
                    'ConditionalConfigurationWriterAtBoundary')
                checks.append({'eventId': event['id'], 'address': 0x50, 'widthBits': 8,
                    'currentSlot': deepcopy(state['lastSlot']), 'requestedGeneration': event['requestedGeneration'],
                    'relation': relation})
            else:
                before = deepcopy(state['lastSlot'])
                if kind == 'UnknownWriter':
                    address = width = value = overlap = None
                    state.update(lastSlot={'value': None, 'knownBits': {}, 'generation': None}, lastKind=kind)
                else:
                    address = 0x50 if kind == 'ConfigIntent' else event['address']
                    address = address & 0xFFFE if width == 16 else address
                    value = event['value']
                    overlap = address <= 0x50 < address + width // 8
                    if overlap:
                        byte = None if value is None else value >> (8 * (0x50 - address)) & 255
                        state.update(lastSlot={'value': byte, 'knownBits': {}, 'generation': event['generation']}, lastKind=kind)
                after = deepcopy(state['lastSlot'])
                same = before['value'] == after['value'] if overlap and before['value'] is not None and after['value'] is not None else None
                journal.append({'ordinal': len(journal) + 1, 'eventId': event['id'], 'kind': kind,
                    'sourcePc': 0x2889 if kind == 'ConfigIntent' else None, 'address': address,
                    'widthBits': width, 'declaredValue': value, 'beforeSlot': before, 'afterSlot': after,
                    'targetOverlap': overlap, 'sameDeclaredValue': same,
                    'effectClass': 'ConditionalConfigurationTimeline_NotPeripheralObservations'})
            history.append({'eventId': event['id'], 'eventIndex': index, 'state': deepcopy(state)})
    return formal('stcon_writer_lineage', query, state, (0x2889, 0x2995), status, reason,
        ('NativeStconOwnerNotEstablished', 'OnlyDeclaredConfigurationHistory'),
        'ConditionalConfigurationTimeline_NotPeripheralObservations', boundary, journal, history,
        configurationChecks=checks)
