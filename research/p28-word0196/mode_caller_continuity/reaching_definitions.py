"""Typed declared DATA03CB effects; a local writer never supplies native continuity."""
from copy import deepcopy
from stbuf_stcon_transmit_source.state import formal, slot_values
from .primary_sources import binding_reason
from .state import input_class, need, number, slot, label, SHARED

PATHS = ('WriterLocalEffect', 'WriterWindowRetention', 'WriterTo60C9', 'Caller276ATo27D0', 'ResetTo60C9')
SCOPE = (0x5CB4, 0x60C9, 0x60CC, 0x276A, 0x27D0, 0x2710)


def data03cb_reaching_definitions(query):
    need(type(query) is dict and set(query) == {'inputClass', 'sourceBinding', 'initial', 'events', 'path',
        'entryGeneration', 'requestedGeneration', 'noInterference', 'claim'}, 'ClosedData03cbReachingQueryRequired')
    input_class(query['inputClass'])
    need(query['sourceBinding'] is None or type(query['sourceBinding']) is dict, 'TypedSourceBindingRequired')
    slot(query['initial'])
    need(type(query['path']) is str and query['path'] in PATHS, 'ClosedData03cbPathRequired')
    need(label(query['entryGeneration']) and label(query['requestedGeneration']), 'TypedGenerationLabelsRequired')
    need(query['noInterference'] is None or type(query['noInterference']) is bool, 'TypedInterferencePremiseRequired')
    need(type(query['claim']) is str and query['claim'] in {'ConditionalOnly', 'NativeOwner', 'ActualHardware', 'RuntimeAdmission'},
         'ClosedSourceClaimRequired')
    events = query['events']
    need(type(events) is list and len(events) <= 32, 'BoundedData03cbEventsRequired')
    shapes = {'IndexedWriter': {'kind', 'id', 'sourcePc', 'p2', 'adcr0h', 'generation', 'scb'},
              'AlternateStore': {'kind', 'id', 'address', 'widthBits', 'value', 'generation'},
              'UnknownWriter': {'kind', 'id'}}
    ids = set()
    for event in events:
        need(type(event) is dict and type(event.get('kind')) is str and event['kind'] in shapes
             and set(event) == shapes[event['kind']] and type(event['id']) is str and bool(event['id'])
             and event['id'] not in ids, 'TypedUniqueData03cbEventRequired')
        ids.add(event['id'])
        if event['kind'] == 'IndexedWriter':
            need(number(event['sourcePc'], 65535) and number(event['scb'], 7) and label(event['generation']), 'TypedIndexedWriterRequired')
            slot(event['p2']); slot(event['adcr0h'])
        elif event['kind'] == 'AlternateStore':
            need(number(event['address'], 65535) and type(event['widthBits']) is int and event['widthBits'] in (8, 16)
                 and number(event['value'], (1 << event['widthBits']) - 1) and label(event['generation']), 'TypedAlternateStoreRequired')
    state = {'lastSlot': deepcopy(query['initial']), 'lastKind': 'InitialUnbound'}
    journal, history = [], []
    used = set() if query['initial']['generation'] is None else {query['initial']['generation']}
    status, reason, relation, boundary = 'CompleteConditional', 'ReviewedIndexedWriterRelation', 'ConfirmedLocalWriterRelation', None
    error = binding_reason(query['sourceBinding'])
    if query['claim'] != 'ConditionalOnly':
        status, reason, relation = 'OutsideVerifiedScope', 'NativeOwnershipClaimNotEstablished', 'SourceConflict'
    elif error:
        status, reason, relation = 'OutsideVerifiedScope', error, 'SourceConflict'
    else:
        for index, event in enumerate(events):
            kind = event['kind']
            if kind == 'IndexedWriter' and (event['sourcePc'] != 0x5CB4 or event['scb'] is None):
                status, reason, relation, boundary = ('OutsideVerifiedScope',
                    'UnreviewedIndexedWriter' if event['sourcePc'] != 0x5CB4 else 'SelectedX1BankNotEstablished', 'SourceConflict', index)
                break
            generation = event.get('generation')
            if generation is not None and generation in used:
                status, reason, relation, boundary = 'OutsideVerifiedScope', 'WriterGenerationReused', 'SourceConflict', index
                break
            if generation is not None:
                used.add(generation)
            before = deepcopy(state['lastSlot'])
            if kind == 'IndexedWriter':
                indices = {(v >> 5) & 7 for v in slot_values(event['p2'])}
                selected = next(iter(indices)) if len(indices) == 1 else None
                address, width, value = (None if selected is None else 0x3C6 + selected), 8, event['adcr0h']['value']
                overlap = None if selected is None else selected == 5
                if selected is None:
                    state.update(lastSlot={'value': None, 'knownBits': {}, 'generation': None}, lastKind='UnknownIndexedWriter')
                elif overlap:
                    state.update(lastSlot={**deepcopy(event['adcr0h']), 'generation': generation}, lastKind='ReviewedIndexedWriter')
            elif kind == 'AlternateStore':
                width, value, address = event['widthBits'], event['value'], event['address']
                if address is not None and width == 16:
                    address &= 0xFFFE
                overlap = None if address is None else address <= 0x3CB < address + width // 8
                if address is None:
                    state.update(lastSlot={'value': None, 'knownBits': {}, 'generation': None}, lastKind='UnknownWriter')
                elif overlap:
                    byte = None if value is None else value >> (8 * (0x3CB - address)) & 255
                    state.update(lastSlot={'value': byte, 'knownBits': {}, 'generation': generation}, lastKind='AlternateStore')
            else:
                address = width = value = overlap = None
                state.update(lastSlot={'value': None, 'knownBits': {}, 'generation': None}, lastKind='UnknownWriter')
            after = deepcopy(state['lastSlot'])
            journal.append({'ordinal': len(journal) + 1, 'eventId': event['id'], 'kind': kind,
                'sourcePc': 0x5CB4 if kind == 'IndexedWriter' else None, 'address': address,
                'widthBits': width, 'declaredValue': value, 'beforeSlot': before, 'afterSlot': after,
                'targetOverlap': overlap, 'sameDeclaredValue': before['value'] == after['value']
                    if overlap is True and before['value'] is not None and after['value'] is not None else None,
                'effectClass': 'DeclaredSourceEffects_NotRuntimeObservations'})
            history.append({'eventId': event['id'], 'eventIndex': index, 'state': deepcopy(state)})
        if status != 'OutsideVerifiedScope':
            current, kind = state['lastSlot']['generation'], state['lastKind']
            status = 'IndeterminateObligation'
            if query['noInterference'] is not True or kind in ('UnknownWriter', 'UnknownIndexedWriter'):
                relation, reason = 'UnknownInterference', 'InterferenceNotExcluded'
            elif kind == 'InitialUnbound':
                relation, reason = 'MissingGeneration', 'NoReviewedWriterGeneration'
            elif kind != 'ReviewedIndexedWriter':
                relation, reason = 'CompetingWriter', 'CompetingData03cbWriter'
            elif None in (current, query['entryGeneration'], query['requestedGeneration']):
                relation, reason = 'MissingGeneration', 'GenerationObligationMissing'
            elif current != query['entryGeneration']:
                relation, reason = 'CompetingWriter', 'EntryGenerationReplaced'
            elif query['requestedGeneration'] != current:
                relation, reason = 'StaleGeneration', 'StaleRequestedGeneration'
            elif query['path'] not in ('WriterLocalEffect', 'WriterWindowRetention'):
                relation, reason = 'ReachingPathUnestablished', 'SourcePathTo60ccNotEstablished'
            else:
                status = 'CompleteConditional'
                relation, reason = (('ConfirmedLocalWriterRelation', 'ReviewedIndexedWriterRelation')
                    if query['path'] == 'WriterLocalEffect' else ('ConditionalWriterRetained', 'ConditionalLocalWriterRetained'))
    state.update(reachingDefinitions={'path': query['path'], 'entryGeneration': query['entryGeneration'],
        'requestedGeneration': query['requestedGeneration'], 'currentGeneration': state['lastSlot']['generation'],
        'relation': relation}, actualNativeData03cbOwner=None)
    return formal('data03cb_reaching_definitions', query, state, SCOPE, status, reason,
        (*SHARED, 'NativeData03cbOwnerNotEstablished', 'SourceReachingPathBeyondLocalWindowUnestablished'),
        'ConditionalData03cbReachingDefinitions', boundary, journal, history)
