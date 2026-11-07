"""Track two distinct indexed DATA generations without running or returning a call."""
from copy import deepcopy

from enclosing_caller_return.state import input_class, label, need, number, shape, tri

from .wire import result

SOURCE = 'M2cyIndexedTimelineV1'
SLOTS = ('03CB', '03D1')
SCOPE = (0x276A, 0x276D, 0x2771, 0x2777, 0x27B2, 0x27D0, 0x5CAF, 0x5CB4, 0x5CB7, 0x5CDC, 0x60CC)
PREMISES = ('noInterference', 'loopExit', 'indexedReturn', 'helperEntry')
CALLERS = (0x276A, 0x2777, 0x27D0)
OBLIGATIONS = ('IndexedWritersBoundToOneP2SelectorPerIteration', 'RepeatRequiresQualifiedReturnAndBranch',
               'ExcludeCompetingDataAndAlignedFrames', 'UspRelative27B2RequiresCurrentUspGeneration',
               'NativeModeConsumer60ccUnbound')
EVENT_FIELDS = {
    'Acquisition': ('iterationId', 'p2', 'adcr1h', 'adcr0h', 'adcr1Generation', 'adcr0Generation',
                    'fromIteration', 'repeatBranch', 'return276d', 'prefixEstablished'),
    'Frame': ('callerPc', 'ssp', 'generation', 'pathEstablished'),
    'Store': ('address', 'widthBits', 'value', 'generation', 'pathEstablished'),
    'Usp27B2': ('usp', 'uspGeneration', 'dd', 'value', 'generation', 'pathEstablished'),
}


def validate(query):
    shape(query, ('inputClass', 'sourceBinding', 'initial', 'events', 'requested', 'premises', 'claim'),
          'ClosedAdcTimelineQueryRequired')
    input_class(query['inputClass'])
    need(label(query['sourceBinding']) and query['claim'] in (
        'ConditionalOnly', 'NativeOwner', 'ActualHardware', 'ModeConsumerReached', 'RuntimeAdmission'),
        'ClosedAdcTimelineClaimRequired')
    shape(query['initial'], SLOTS, 'BothDistinctTrackedDataSlotsRequired')
    shape(query['requested'], SLOTS, 'ClosedRequestedAdcGenerationsRequired')
    shape(query['premises'], PREMISES, 'ClosedAdcTimelinePremisesRequired')
    need(all(tri(v) for v in query['premises'].values()) and all(label(v) for v in query['requested'].values()),
         'TypedTimelinePremisesRequired')
    for slot in query['initial'].values():
        shape(slot, ('value', 'generation', 'iterationId'), 'ClosedTimelineSeedRequired')
        need(number(slot['value'], 255) and label(slot['generation']) and label(slot['iterationId']),
             'TypedTimelineSeedRequired')
    events = query['events']
    need(type(events) is list and len(events) <= 24, 'BoundedAdcTimelineEventsRequired')
    for event in events:
        need(type(event) is dict and type(event.get('kind')) is str and event['kind'] in EVENT_FIELDS,
             'ClosedAdcTimelineEventRequired')
        kind = event['kind']
        shape(event, ('kind', *EVENT_FIELDS[kind]), 'ClosedAdcTimelineEventRequired')
        if kind == 'Acquisition':
            need(all(number(event[k], 255) for k in ('p2', 'adcr1h', 'adcr0h'))
                 and all(label(event[k]) for k in ('iterationId', 'fromIteration', 'adcr1Generation', 'adcr0Generation'))
                 and all(tri(event[k]) for k in ('repeatBranch', 'return276d', 'prefixEstablished')),
                 'TypedIndexedIterationRequired')
        else:
            need(label(event['generation']) and tri(event['pathEstablished']), 'TypedAlternativeWriterRequired')
            if kind == 'Frame':
                need(number(event['callerPc'], 0xFFFF) and number(event['ssp'], 0xFFFF), 'TypedFrameEventRequired')
            elif kind == 'Store':
                need(type(event['widthBits']) is int and event['widthBits'] in (8, 16)
                     and number(event['address'], 0xFFFF) and number(event['value'], (1 << event['widthBits']) - 1),
                     'TypedStoreEventRequired')
            else:
                need(number(event['usp'], 0xFFFF) and label(event['uspGeneration']) and number(event['dd'], 1)
                     and number(event['value'], 255), 'TypedUspRelativeEventRequired')


def _alternative(event):
    kind = event['kind']
    if kind == 'Frame':
        pc, ssp = event['callerPc'], event['ssp']
        if pc not in CALLERS:
            return None, 'UnreviewedFrameWriter'
        if ssp is not None and ssp < 0x00C0:
            return None, 'FrameControlOrBankAlias'
        return (None if ssp is None else ssp & 0xFFFE, 16, pc + 3, pc), 'UnknownStackOverlap'
    if kind == 'Store':
        address, width = event['address'], event['widthBits']
        address = address & 0xFFFE if address is not None and width == 16 else address
        if address == 0x4700:
            return None, 'OutsideReviewedDataScope'
        return (address, width, event['value'], None), 'UnknownStoreOverlap'
    if event['dd'] == 1:
        return None, 'UspStoreDescriptorMismatch'
    if event['dd'] is None or event['usp'] is None or event['uspGeneration'] is None:
        return (None, 8, event['value'], 0x27B2), 'Usp27b2AddressOrDescriptorUnbound'
    return ((event['usp'] - 0x4E) & 0xFFFF, 8, event['value'], 0x27B2), None


def _run(query, helper):
    validate(query)
    state = {name: {**slot, 'writerPc': None} for name, slot in query['initial'].items()}
    reads, writes, states, iterations = [], [], [], []
    occupied = {slot['generation'] for slot in state.values() if slot['generation'] is not None}
    seen_iterations = set()
    previous = None
    late_phase = 0
    stop = 'STOP_BEFORE_INDEXED_CONTINUATION_5CB7'
    native_limits = ('NativeOwnershipUnestablished', 'ModeConsumer60ccUnbound')

    def finish(status, reason):
        owners = {name: slot['generation'] for name, slot in state.items()}
        requested = query['requested']
        matches = {name: (None if gen is None else owners[name] == gen) for name, gen in requested.items()}
        retention = {name: (None if status != 'CompleteConditional' else match) for name, match in matches.items()}
        cross = {slot['iterationId'] for slot in state.values() if slot['iterationId'] is not None}
        return result(status, source_scope=SCOPE, caller=0x276A, state={
            'lastSlots': state, 'requestedMatchesLastLocal': matches, 'requestedRetention': retention,
            'mixedIterationSource': len(cross) > 1, 'nativeOwner': None, 'modeReadEstablished': False,
        }, stop=stop, reads=reads, writes=writes, generations=owners, intermediate=states,
            obligations=OBLIGATIONS, unresolved=(*native_limits, *(() if status == 'CompleteConditional' else (reason,))),
            iterations=iterations, reason=reason)

    def write(kind, address, width, value, generation, writer_pc, iteration=None):
        occupied.add(generation)
        touched = {}
        for key in SLOTS:
            offset = int(key, 16) - address
            if 0 <= offset < width // 8:
                prior = state[key]
                byte = None if value is None else value >> (8 * offset) & 255
                touched[key] = {'priorGeneration': prior['generation'],
                                'sameValue': None if None in (byte, prior['value']) else byte == prior['value']}
                state[key] = {'value': byte, 'generation': generation, 'iterationId': iteration, 'writerPc': writer_pc}
        writes.append({'ordinal': len(writes) + 1, 'kind': kind, 'pc': writer_pc, 'address': address,
                       'widthBits': width, 'value': value, 'generation': generation,
                       'iterationId': iteration, 'trackedChanges': touched, 'actualHardwareObservation': None})

    outside, unknown = 'OutsideVerifiedScope', 'IndeterminateObligation'
    if query['claim'] != 'ConditionalOnly':
        return finish(outside, 'NonConditionalTimelineClaim')
    if query['sourceBinding'] != SOURCE:
        return finish(unknown if query['sourceBinding'] is None else outside, 'TimelineSourceBindingUnqualified')
    if len(occupied) != sum(slot['generation'] is not None for slot in state.values()):
        return finish(outside, 'DistinctInitialAdcGenerationsRequired')
    for event in query['events']:
        kind = event['kind']
        if late_phase and (kind == 'Acquisition' or kind == 'Frame' and event['callerPc'] == 0x276A
                           and event['pathEstablished'] is not False):
            return finish(outside, 'IndexedEventAfterLoopExit')
        if helper and event.get('pathEstablished') is not False and (
                kind == 'Usp27B2' or kind == 'Frame' and event['callerPc'] == 0x27D0):
            return finish(outside, 'WriterAfterHelperBoundary')
        if kind == 'Acquisition':
            identity = event['iterationId']
            if identity is None or identity in seen_iterations:
                return finish(outside, 'DistinctIterationIdentityRequired')
            if event['fromIteration'] != previous or (previous is None and
                    (event['repeatBranch'] is not None or event['return276d'] is not None)):
                return finish(outside, 'IterationLinkMismatch')
            if previous is not None and (event['repeatBranch'] is not True or event['return276d'] is not True):
                return finish(unknown, 'MissingIndexedReturnOrRepeatProof')
            if event['prefixEstablished'] is not True or event['p2'] is None:
                return finish(unknown, 'IndexedPrefixOrP2Unqualified')
            gen1, gen0 = event['adcr1Generation'], event['adcr0Generation']
            if gen1 is None or gen0 is None:
                return finish(unknown, 'IndexedWriterGenerationMissing')
            if gen1 == gen0 or gen1 in occupied or gen0 in occupied:
                return finish(outside, 'WriterGenerationReused')
            index = event['p2'] >> 5
            iterations.append({'iterationId': identity, 'fromIteration': previous, 'selectedIndex': index,
                               'suppliedP2': event['p2'], 'suppliedAdcr1h': event['adcr1h'],
                               'suppliedAdcr0h': event['adcr0h']})
            write(kind, 0x03CE + index, 8, event['adcr1h'], gen1, 0x5CAF, identity)
            write(kind, 0x03C6 + index, 8, event['adcr0h'], gen0, 0x5CB4, identity)
            previous = identity
            seen_iterations.add(identity)
        else:
            if event['pathEstablished'] is False:
                continue
            if event['pathEstablished'] is not True:
                return finish(unknown, 'AlternateWriterPathUnestablished')
            # An explicitly qualified late path includes all intervening
            # caller/return premises; the event order cannot reverse the
            # reviewed cold helper, USP store, and mode-call order.
            phase = (2 if kind == 'Usp27B2' else
                     {0x2777: 1, 0x27D0: 3}.get(event['callerPc']) if kind == 'Frame' else None)
            if phase is not None and phase < late_phase:
                return finish(outside, 'LateSourceEventOrderMismatch')
            effect, reason = _alternative(event)
            if effect is None:
                return finish(outside, reason)
            address, width, value, pc = effect
            if address is None:
                return finish(unknown, reason)
            if address == 0x4700:
                return finish(outside, 'OutsideReviewedDataScope')
            generation = event['generation']
            if generation is None:
                return finish(unknown, 'AlternateWriterGenerationMissing')
            if generation in occupied:
                return finish(outside, 'WriterGenerationReused')
            write(kind, address, width, value, generation, pc)
            if phase is not None:
                late_phase = phase
        states.append({'afterEvent': len(states) + 1, 'lastSlots': deepcopy(state)})

    if query['premises']['noInterference'] is not True:
        return finish(unknown, 'UnknownInterference')
    if any(gen is not None and gen != state[name]['generation'] for name, gen in query['requested'].items()):
        return finish(unknown, 'RequestedGenerationNotCurrent')
    if helper:
        slot = state['03D1']
        if query['requested']['03CB'] is not None or query['requested']['03D1'] is None or slot['writerPc'] != 0x5CAF:
            return finish(unknown, 'HelperData03d1IndexedGenerationUnestablished')
        if any(query['premises'][name] is not True for name in PREMISES[1:]):
            return finish(unknown, 'HelperEntryOrIndexedReturnUnestablished')
        stop = 'STOP_BEFORE_C8_5CDF'
        reads.append({'pc': 0x5CDC, 'address': 0x03D1, 'widthBits': 8, **slot})
        return finish('CompleteConditional', 'ConditionalIndexedGenerationAt5cdc')
    return finish('CompleteConditional', 'ConditionalLocalAdcTimeline')


def cold_adc_generation_timeline(query):
    return _run(query, False)


def data03d1_reaching_definitions(query):
    return _run(query, True)
