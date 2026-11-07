"""Prove a caller-specific DATA00FA/00FB definition within the reviewed cold route."""
from copy import deepcopy
from types import MappingProxyType

from enclosing_caller_return.call_return_obligations import frame_alias
from enclosing_caller_return.state import input_class, label, need, number, shape, slot, tri

from .wire import result


BINDING = 'M2cyShadowSourceReviewV1'
SOURCE_SCOPE = (0x2566, 0x256B, 0x2706, 0x2710, 0x2714, 0x271A, 0x272A, 0x2759,
                0x2763, 0x2768, 0x276A, 0x2B61, 0x2B64, 0x3F18, 0x3F2C, 0x3FF7,
                0x54DD, 0x5C86, 0x5CA0, 0x5CA3, 0x5CA5, 0x5CB4, 0x5CB7)
WORDS = MappingProxyType({0x256B: 0, 0x2710: 0, 0x3F18: 0x02A0, 0x3F2C: 0x00A0, 0x54DD: 0x02A0})
ORIGINS = MappingProxyType({0x276A: 'Cold276A', 0x2B64: 'Independent2B64'})
PREMISES = ('ownedColdNon47Entry', 'stableClearContext', 'firstExitBeforeActivePointerAlias',
            'ie2759SymbolicHandoff', 'indexedRouteQualified', 'noAsynchronousInterference')
FRAME_FIELDS = ('callerPc', 'incomingSsp', 'generation', 'memoryApplicable', 'integrity')
EVENT_FIELDS = ('kind', 'writerPc', 'address', 'widthBits', 'generation', 'value', 'reached')
EVENT_KINDS = ('DirectStore', 'IndirectStore', 'FrameStore', 'UnknownWriter')
CLAIMS = ('ConditionalOnly', 'NativeOwner', 'ActualHardware', 'RuntimeAdmission')
OBLIGATIONS = ('ReviewedColdEntryAndRamClear', 'QualifiedPreAliasLoopExit',
               'IndependentIeAndPendingFactorHandoff', 'DisjointOrdinaryCalFrame',
               'SourceOwnedIndexedPath', 'NoShadowInterference')
UNRESOLVED = ('CurrentNativeOwnerUnestablished', 'SharedSlotOnlyWithConfigurationReader3FF7',
              'ActualColdExitAndIndexedEntryUnestablished')


def _validate(query):
    shape(query, ('inputClass', 'callerPc', 'consumerPc', 'sourceBinding', 'context', 'initialPair',
                  'writer', 'requestedGeneration', 'premises', 'exit', 'frame', 'events', 'claim'),
          'ClosedShadowReachingQueryRequired')
    input_class(query['inputClass'])
    need(number(query['callerPc'], 0xFFFF) and number(query['consumerPc'], 0xFFFF)
         and label(query['sourceBinding']) and label(query['requestedGeneration'])
         and type(query['claim']) is str and query['claim'] in CLAIMS, 'TypedShadowReachingQueryRequired')
    context, pair, writer, exit_state, frame, premises = (
        query[key] for key in ('context', 'initialPair', 'writer', 'exit', 'frame', 'premises'))
    shape(context, ('origin', 'lrb', 'scb', 'usp', 'data0230Bit3', 'oldIrqh4'), 'ClosedShadowCallerContextRequired')
    need(label(context['origin']) and number(context['lrb'], 0xFFFF) and number(context['scb'], 7)
         and number(context['usp'], 0xFFFF) and all(number(context[k], 1) for k in ('data0230Bit3', 'oldIrqh4')),
         'TypedShadowCallerContextRequired')
    shape(pair, ('address', 'wordGeneration', 'low', 'high'), 'ClosedShadowPairRequired')
    need(number(pair['address'], 0xFFFF) and label(pair['wordGeneration']), 'TypedShadowPairRequired')
    slot(pair['low'])
    slot(pair['high'])
    shape(writer, ('pc', 'address', 'dd'), 'ClosedShadowWriterRequired')
    need(number(writer['pc'], 0xFFFF) and number(writer['address'], 0xFFFF) and number(writer['dd'], 1),
         'TypedShadowWriterRequired')
    shape(exit_state, ('dp', 'usp'), 'ClosedClearExitRequired')
    need(all(number(value, 0xFFFF) for value in exit_state.values()), 'TypedClearExitRequired')
    shape(frame, FRAME_FIELDS, 'ClosedShadowFrameRequired')
    need(number(frame['callerPc'], 0xFFFF) and number(frame['incomingSsp'], 0xFFFF) and label(frame['generation'])
         and tri(frame['memoryApplicable']) and tri(frame['integrity']), 'TypedShadowFrameRequired')
    shape(premises, PREMISES, 'ClosedShadowPremisesRequired')
    need(all(tri(value) for value in premises.values()), 'TypedShadowPremisesRequired')
    events = query['events']
    need(type(events) is list and len(events) <= 32, 'BoundedShadowEventsRequired')
    for event in events:
        shape(event, EVENT_FIELDS, 'ClosedShadowEventRequired')
        kind, width = event['kind'], event['widthBits']
        need(type(kind) is str and kind in EVENT_KINDS and type(width) is int and width in (8, 16)
             and number(event['writerPc'], 0xFFFF) and number(event['address'], 0xFFFF)
             and label(event['generation']) and number(event['value'], (1 << width) - 1)
             and tri(event['reached']), 'TypedShadowEventRequired')
        if kind == 'FrameStore':
            need(width == 16, 'OrdinaryFrameMustBeWord')
        if kind == 'UnknownWriter':
            need(event['address'] is None and event['value'] is None, 'UnknownWriterCannotOwnAddressOrValue')


def _pair_value(pair):
    bits = {}
    for offset, name in ((0, 'low'), (8, 'high')):
        byte = pair[name]
        known = byte['knownBits'] if byte['value'] is None else {
            str(i): (byte['value'] >> i) & 1 for i in range(8)}
        bits.update({str(offset + int(i)): value for i, value in known.items()})
    word = sum(value << int(i) for i, value in bits.items()) if len(bits) == 16 else None
    return word, bits, 0 if 1 in bits.values() else 1 if word == 0 else None


def _frame_address(query):
    frame = query['frame']
    return None if frame['incomingSsp'] is None else frame['incomingSsp'] & 0xFFFE


def _predecessor_alias(query):
    usp = query['context']['usp']
    if query['callerPc'] != 0x2B64 or query['context']['origin'] != ORIGINS[0x2B64] or usp is None:
        return None
    return (usp - 0x56) & 0xFFFF


def _admission(query, word, bits, frame_address, predecessor_address):
    caller, pair, writer = (query[key] for key in ('callerPc', 'initialPair', 'writer'))
    context, frame, exit_state = (query[key] for key in ('context', 'frame', 'exit'))
    generation = pair['wordGeneration']
    if query['claim'] != 'ConditionalOnly':
        return 'OutsideVerifiedScope', 'UnadmittedNativeShadowClaim'
    if query['consumerPc'] != 0x5CB7 or pair['address'] != 0x00FA:
        return 'OutsideVerifiedScope', 'WrongShadowConsumerOrSlot'
    if caller not in ORIGINS or context['origin'] != ORIGINS[caller]:
        return 'OutsideVerifiedScope', 'CallerContextMismatch'
    if query['sourceBinding'] != BINDING:
        return 'OutsideVerifiedScope', 'SourceConflict'
    if None in (writer['pc'], writer['address'], generation, pair['low']['generation'],
                pair['high']['generation'], query['requestedGeneration']):
        return 'IndeterminateObligation', 'MissingShadowGeneration'
    if writer['pc'] not in WORDS or writer['address'] != 0x00FA or (
            writer['pc'] in (0x256B, 0x2710) and writer['dd'] != 1):
        return 'OutsideVerifiedScope', 'SourceConflict'
    if pair['low']['generation'] != pair['high']['generation']:
        return 'OutsideVerifiedScope', 'MixedByteGenerations'
    if pair['low']['generation'] != generation or generation != query['requestedGeneration']:
        return 'OutsideVerifiedScope', 'StaleShadowGeneration'
    writer_word = WORDS[writer['pc']]
    if any((writer_word >> int(i)) & 1 != value for i, value in bits.items()):
        return 'OutsideVerifiedScope', 'SourceConflict'
    if caller == 0x2B64:
        return 'IndeterminateObligation', ('CompetingShadowWriter' if predecessor_address in (0x00FA, 0x00FB)
                                           else 'CallerSpecificProvenanceUnresolved')
    if writer['pc'] not in (0x256B, 0x2710):
        return 'IndeterminateObligation', 'ReachingPathUnestablished'
    if (context['lrb'], context['scb'], context['usp'], context['data0230Bit3'], context['oldIrqh4']) != (
            0x0041, 0, 0x0180, 0, 1):
        return 'IndeterminateObligation', 'ReachingPathUnestablished'
    if (any(query['premises'][name] is not True for name in PREMISES[:-1])
            or exit_state['dp'] not in range(0x0088, 0x009A, 2) or exit_state['usp'] not in (0x0098, 0x0356)):
        return 'IndeterminateObligation', 'ReachingPathUnestablished'
    if writer['pc'] == 0x256B:
        return 'OutsideVerifiedScope', 'StaleShadowGeneration'
    if query['premises']['noAsynchronousInterference'] is not True:
        return 'IndeterminateObligation', 'UnexcludedInterference'
    if frame_address is None or frame['generation'] is None or frame['callerPc'] is None:
        return 'IndeterminateObligation', 'UnknownStackOverlap'
    if frame['callerPc'] != caller or frame['memoryApplicable'] is not True or frame['integrity'] is not True:
        return 'IndeterminateObligation', 'ShadowFrameObligationsUnmet'
    if frame['generation'] == generation:
        return 'OutsideVerifiedScope', 'ShadowGenerationReused'
    if frame_address == 0x00FA:
        return 'IndeterminateObligation', 'CompetingShadowWriter'
    if frame_alias(frame_address, False) != 'OrdinaryDataCandidate' or 0x0208 <= frame_address <= 0x020E:
        return 'IndeterminateObligation', 'ShadowFrameObligationsUnmet'
    if word is None:
        return 'IndeterminateObligation', 'ShadowWordValueUnestablished'
    return None


def _reviewed_event_matches_source(event):
    writer = event['writerPc']
    if writer not in WORDS:
        return True
    if event['widthBits'] != 16 or event['value'] not in (None, WORDS[writer]):
        return False
    if writer == 0x2710:
        return event['kind'] == 'IndirectStore' and event['address'] % 2 == 0
    return event['kind'] == 'DirectStore' and event['address'] == 0x00FA


def _advance(pair, events, occupied):
    """Retain ordered supplied events until an alias or unknown reaches the pair."""
    writes = []
    for event in events:
        if event['reached'] is False:
            continue
        if event['reached'] is not True or event['address'] is None or event['generation'] is None:
            reason = 'UnknownStackOverlap' if event['kind'] == 'FrameStore' else 'UnexcludedInterference'
            return 'IndeterminateObligation', reason, writes
        if not _reviewed_event_matches_source(event):
            return 'OutsideVerifiedScope', 'SourceConflict', writes
        addr = event['address'] if event['widthBits'] == 8 else event['address'] & 0xFFFE
        generation = event['generation']
        if generation in occupied:
            return 'OutsideVerifiedScope', 'ShadowGenerationReused', writes
        occupied.add(generation)
        observed = []
        for offset, name in ((0, 'low'), (1, 'high')):
            distance = 0x00FA + offset - addr
            if not 0 <= distance < event['widthBits'] // 8:
                continue
            old_value = pair[name]['value']
            new_value = None if event['value'] is None else (event['value'] >> (8 * distance)) & 255
            same_value = None if old_value is None or new_value is None else old_value == new_value
            observed.append({'address': 0x00FA + offset, 'beforeGeneration': pair[name]['generation'],
                             'afterGeneration': generation, 'sameValue': same_value})
            pair[name] = {'value': new_value, 'knownBits': {}, 'generation': generation}
        writes.append({**event, 'alignedAddress': addr, 'shadowEffects': observed})
        if observed:
            pair['wordGeneration'] = generation if len(observed) == 2 else None
            return 'IndeterminateObligation', 'CompetingShadowWriter', writes
    return 'CompleteConditional', 'ConditionalShadowWriterRetained', writes


def data00fa_caller_reaching_definitions(query):
    """Project one bounded shadow writer across reviewed static and declared symbolic edges."""
    _validate(query)
    pair = deepcopy(query['initialPair'])
    initial_word, initial_bits, _ = _pair_value(pair)
    caller, writer, frame = (query[key] for key in ('callerPc', 'writer', 'frame'))
    frame_address, predecessor_address = _frame_address(query), _predecessor_alias(query)
    refusal = _admission(query, initial_word, initial_bits, frame_address, predecessor_address)
    if refusal:
        status, reason = refusal
        writes = []
    else:
        status, reason, writes = _advance(pair, query['events'], {pair['wordGeneration'], frame['generation']})
    word, bits, zf = _pair_value(pair)
    reached = status == 'CompleteConditional'
    structural_reach = caller == 0x276A and writer['pc'] == 0x2710
    branches = ({'pc': 0x5C86, 'nextPc': 0x5CA0, 'premise': 'Data0230Bit3Zero'},
                {'pc': 0x5CA3, 'nextPc': 0x5CA5, 'premise': 'OldIrqh4One'}) if reached else ()
    return result(status, source_scope=SOURCE_SCOPE, caller=caller, reason=reason,
                  stop='STOP_BEFORE_INDEXED_CONTINUATION_5CB7', writes=writes, branches=branches,
                  state={'pair': pair, 'word': word, 'knownBits': bits, 'zf': zf,
                         'sourceWriterExists': writer['pc'] in WORDS,
                         'writerReachableInReviewedCfg': structural_reach,
                         'callReturnSummariesNeededForCandidate': caller == 0x276A and writer['pc'] == 0x256B,
                         'conditionalLastWriterPc': writer['pc'] if reached else None,
                         'currentNativeOwner': None, 'predecessor2B61Address': predecessor_address,
                         'ordinaryCalFrameAddress': frame_address,
                         'formalReturnCandidatePc': caller + 3 if caller in ORIGINS else None},
                  generations={'conditionalRetained': pair['wordGeneration'] if reached else None,
                               'low': pair['low']['generation'], 'high': pair['high']['generation'],
                               'sharedWord': pair['wordGeneration'], 'frame': frame['generation']},
                  obligations=OBLIGATIONS, unresolved=UNRESOLVED if reached else (*UNRESOLVED, reason))
