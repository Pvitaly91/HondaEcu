"""Independent source equations for the M2cy canonical research cases."""

from copy import deepcopy
from itertools import product

from indexed_suffix_ie_provenance.reference_oracle import (
    AUTHORITY, SNAPSHOT_FIELDS, canonical,
    indexed_return_obligations as accepted_indexed_frame,
    indexed_suffix_composition as accepted_indexed,
    indexed_suffix_post_ie as accepted_post_ie,
)


BASE = '9786bdfe136741e3930e7d4088bdc28565ee7f08'
SOURCE_IDENTITIES = {
    'm2cxBase': BASE,
    'm2cxSourceBinding': 'ab376194f261c60a47ab4881849abed3cd2e25a4a680c603ef900012098e9ff7',
    'primaryIsa': 'f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271',
}
OUTPUT_FIELDS = (
    'sourceScope', 'sourceIdentities', 'evidenceClass', 'applicability', 'state', 'branchOutcome',
    'reads', 'orderedWrites', 'generations', 'intermediateStates', 'formalObligations',
    'unresolvedConstraints', 'stopBoundary', 'caller', 'iterations',
)


def _result(scope, status, *, caller=None, iterations=(), state=None, stop=None,
            evidence='ConditionalSourceModel', reads=(), writes=(), generations=None, states=(),
            obligations=(), unresolved=(), branches=(), **extra):
    return deepcopy({
        'status': status, 'sourceScope': list(scope), 'sourceIdentities': SOURCE_IDENTITIES,
        'evidenceClass': evidence, 'applicability': 'ConditionalSoftwareOnly_HardwareApplicabilityUnestablished',
        'state': state, 'branchOutcome': list(branches), 'reads': list(reads), 'orderedWrites': list(writes),
        'generations': generations, 'intermediateStates': list(states), 'formalObligations': list(obligations),
        'unresolvedConstraints': list(unresolved), 'stopBoundary': stop, 'caller': caller,
        'iterations': list(iterations), **AUTHORITY, **extra,
    })


def _bit(value, bit):
    return value // 2 ** bit % 2


def _domain(slot, width=8):
    raw = slot['value']
    if raw is not None:
        return (raw,)
    known = {int(position): digit for position, digit in slot['knownBits'].items()}
    missing = [position for position in range(width) if position not in known]
    base = sum(digit * 2 ** position for position, digit in known.items())
    return tuple(base + sum(digit * 2 ** position for position, digit in zip(missing, digits, strict=True))
                 for digits in product((0, 1), repeat=len(missing)))


def _agreed(values):
    options = set(values)
    return next(iter(options)) if len(options) == 1 else None


def _bits(values, width):
    return {str(position): common for position in range(width)
            if (common := _agreed(_bit(value, position) for value in values)) is not None}


def _record(case, output):
    return {'caseId': case['id'], 'operation': case['operation'], 'input': case['input'], 'output': output,
            **{key: output[key] for key in OUTPUT_FIELDS},
            'executionAuthority': {key: output[key] for key in AUTHORITY}}


OUTSIDE = 'OutsideVerifiedScope'
UNKNOWN = 'IndeterminateObligation'
COMPLETE = 'CompleteConditional'
TRACKED = {'03CB': 0x03CB, '03D1': 0x03D1}
ADC_SCOPE = (0x276A, 0x276D, 0x2771, 0x2777, 0x27B2, 0x27D0, 0x5CAF, 0x5CB4, 0x5CB7, 0x5CDC, 0x60CC)
ADC_OBLIGATIONS = (
    'IndexedWritersBoundToOneP2SelectorPerIteration', 'RepeatRequiresQualifiedReturnAndBranch',
    'ExcludeCompetingDataAndAlignedFrames', 'UspRelative27B2RequiresCurrentUspGeneration',
    'NativeModeConsumer60ccUnbound',
)


def _first_refusal(options):
    return next(((status, reason) for fails, status, reason in options if fails), None)


def _alternate_write(event):
    kind = event['kind']
    if kind == 'Frame':
        caller = event['callerPc']
        if caller not in (0x276A, 0x2777, 0x27D0):
            return OUTSIDE, 'UnreviewedFrameWriter'
        if event['ssp'] is None:
            return UNKNOWN, 'UnknownStackOverlap'
        address = event['ssp'] // 2 * 2
        if address < 0x00C0:
            return OUTSIDE, 'FrameControlOrBankAlias'
        if address == 0x4700:
            return OUTSIDE, 'OutsideReviewedDataScope'
        return (kind, caller, address, 16, caller + 3, event['generation'], None)
    if kind == 'Store':
        width, address = event['widthBits'], event['address']
        if address is None:
            return UNKNOWN, 'UnknownStoreOverlap'
        if width == 16:
            address = address // 2 * 2
        if address == 0x4700:
            return OUTSIDE, 'OutsideReviewedDataScope'
        return (kind, None, address, width, event['value'], event['generation'], None)
    if event['dd'] == 1:
        return OUTSIDE, 'UspStoreDescriptorMismatch'
    if any(event[name] is None for name in ('usp', 'uspGeneration', 'dd')):
        return UNKNOWN, 'Usp27b2AddressOrDescriptorUnbound'
    address = (event['usp'] - 78) % 65536
    if address == 0x4700:
        return OUTSIDE, 'OutsideReviewedDataScope'
    return (kind, 0x27B2, address, 8, event['value'], event['generation'], None)


def _indexed_writes(event, iterations, occupied):
    prior_id = iterations[-1]['iterationId'] if iterations else None
    current_id, p2 = event['iterationId'], event['p2']
    first, last = event['adcr1Generation'], event['adcr0Generation']
    supplied_link = event['fromIteration'], event['repeatBranch'], event['return276d']
    rejection = _first_refusal((
        (current_id is None or any(stage['iterationId'] == current_id for stage in iterations),
         OUTSIDE, 'DistinctIterationIdentityRequired'),
        (supplied_link[0] != prior_id or (not iterations and supplied_link != (None, None, None)),
         OUTSIDE, 'IterationLinkMismatch'),
        (bool(iterations) and supplied_link[1:] != (True, True), UNKNOWN, 'MissingIndexedReturnOrRepeatProof'),
        (event['prefixEstablished'] is not True or p2 is None, UNKNOWN, 'IndexedPrefixOrP2Unqualified'),
        (None in (first, last), UNKNOWN, 'IndexedWriterGenerationMissing'),
        (first == last or bool({first, last} & occupied), OUTSIDE, 'WriterGenerationReused'),
    ))
    if rejection:
        return rejection, None
    selector = p2 // 32
    stage = {'iterationId': current_id, 'fromIteration': prior_id, 'selectedIndex': selector,
             'suppliedP2': p2, 'suppliedAdcr1h': event['adcr1h'], 'suppliedAdcr0h': event['adcr0h']}
    stores = tuple(('Acquisition', pc, base + selector, 8, event[data], generation, current_id)
                   for pc, base, data, generation in (
                       (0x5CAF, 0x03CE, 'adcr1h', first), (0x5CB4, 0x03C6, 'adcr0h', last)))
    return stores, stage


def _apply_store(slots, store, ordinal):
    kind, pc, address, width, word, generation, iteration = store
    byte_count = width // 8
    selected_bytes = [None] * byte_count if word is None else list(word.to_bytes(byte_count, 'little'))
    changes = {}
    state = dict(slots)
    for name, offset in ((name, target - address) for name, target in TRACKED.items()):
        if offset not in range(byte_count):
            continue
        old, new = slots[name], selected_bytes[offset]
        changes[name] = {'priorGeneration': old['generation'],
                         'sameValue': old['value'] == new if None not in (old['value'], new) else None}
        state[name] = {'value': new, 'generation': generation, 'iterationId': iteration, 'writerPc': pc}
    write = {'ordinal': ordinal, 'kind': kind, 'pc': pc, 'address': address, 'widthBits': width,
             'value': word, 'generation': generation, 'iterationId': iteration,
             'trackedChanges': changes, 'actualHardwareObservation': None}
    return state, write


def _adc_timeline(query, helper):
    slots = {key: dict(seed, writerPc=None) for key, seed in query['initial'].items()}
    initial_gens = [slot['generation'] for slot in slots.values() if slot['generation'] is not None]
    occupied = set(initial_gens)
    writes, states, iterations = [], [], []
    exited_loop = False
    late_rank = 0
    requested = query['requested']
    precheck = _first_refusal((
        (query['claim'] != 'ConditionalOnly', OUTSIDE, 'NonConditionalTimelineClaim'),
        (query['sourceBinding'] != 'M2cyIndexedTimelineV1',
         UNKNOWN if query['sourceBinding'] is None else OUTSIDE, 'TimelineSourceBindingUnqualified'),
        (len(initial_gens) != len(occupied), OUTSIDE, 'DistinctInitialAdcGenerationsRequired'),
    ))
    rejection = precheck
    for event in query['events'] if rejection is None else ():
        active = event.get('pathEstablished') is not False
        phase = event['kind']
        frame_caller = event.get('callerPc')
        if exited_loop and (phase == 'Acquisition' or phase == 'Frame' and frame_caller == 0x276A and active):
            rejection = OUTSIDE, 'IndexedEventAfterLoopExit'
            break
        if event['kind'] == 'Acquisition':
            stores, stage = _indexed_writes(event, iterations, occupied)
            if stage is None:
                rejection = stores
                break
            iterations.append(stage)
        else:
            if event['pathEstablished'] is False:
                continue
            later = event['kind'] == 'Usp27B2' or (event['kind'] == 'Frame' and event['callerPc'] == 0x27D0)
            if helper and later:
                rejection = OUTSIDE, 'WriterAfterHelperBoundary'
                break
            if event['pathEstablished'] is not True:
                rejection = UNKNOWN, 'AlternateWriterPathUnestablished'
                break
            rank = 2 if phase == 'Usp27B2' else {0x2777: 1, 0x27D0: 3}.get(frame_caller, 0)
            if rank and rank < late_rank:
                rejection = OUTSIDE, 'LateSourceEventOrderMismatch'
                break
            store = _alternate_write(event)
            if len(store) == 2:
                rejection = store
                break
            generation = event['generation']
            if generation is None or generation in occupied:
                rejection = ((UNKNOWN, 'AlternateWriterGenerationMissing') if generation is None else
                             (OUTSIDE, 'WriterGenerationReused'))
                break
            stores = (store,)
            late_rank = max(late_rank, rank)
            exited_loop |= bool(rank)
        for store in stores:
            slots, write = _apply_store(slots, store, len(writes) + 1)
            occupied.add(write['generation'])
            writes.append(write)
        states.append({'afterEvent': len(states) + 1, 'lastSlots': slots})

    generations = {key: slot['generation'] for key, slot in slots.items()}
    matches = {key: None if generation is None else generations[key] == generation
               for key, generation in requested.items()}
    premise = query['premises']
    slot_d1 = slots['03D1']
    if rejection is None:
        rejection = _first_refusal((
            (premise['noInterference'] is not True, UNKNOWN, 'UnknownInterference'),
            (False in matches.values(), UNKNOWN, 'RequestedGenerationNotCurrent'),
            (helper and (requested['03CB'] is not None or requested['03D1'] is None or slot_d1['writerPc'] != 0x5CAF),
             UNKNOWN, 'HelperData03d1IndexedGenerationUnestablished'),
            (helper and not all(premise[name] is True for name in ('loopExit', 'indexedReturn', 'helperEntry')),
             UNKNOWN, 'HelperEntryOrIndexedReturnUnestablished'),
        ))
    accepted = rejection is None
    read_helper = helper and accepted
    status, reason = rejection or (COMPLETE, 'ConditionalIndexedGenerationAt5cdc' if helper else 'ConditionalLocalAdcTimeline')
    mixed = len({slot['iterationId'] for slot in slots.values()} - {None}) > 1
    state = {'lastSlots': slots, 'requestedMatchesLastLocal': matches,
             'requestedRetention': matches if accepted else dict.fromkeys(TRACKED),
             'mixedIterationSource': mixed, 'nativeOwner': None, 'modeReadEstablished': False}
    return _result(ADC_SCOPE, status, caller=0x276A, iterations=iterations, state=state,
                   stop='STOP_BEFORE_C8_5CDF' if read_helper else 'STOP_BEFORE_INDEXED_CONTINUATION_5CB7',
                   reads=({'pc': 0x5CDC, 'address': 0x03D1, 'widthBits': 8, **slot_d1},) if read_helper else (),
                   writes=writes, generations=generations, states=states, obligations=ADC_OBLIGATIONS,
                   unresolved=('NativeOwnershipUnestablished', 'ModeConsumer60ccUnbound',
                               *(() if accepted else (reason,))), reason=reason)


def cold_adc_generation_timeline(query):
    return _adc_timeline(query, False)


def data03d1_reaching_definitions(query):
    return _adc_timeline(query, True)


SHADOW_SCOPE = (
    0x2566, 0x256B, 0x2706, 0x2710, 0x2714, 0x271A, 0x272A, 0x2759, 0x2763, 0x2768, 0x276A,
    0x2B61, 0x2B64, 0x3F18, 0x3F2C, 0x3FF7, 0x54DD, 0x5C86, 0x5CA0, 0x5CA3, 0x5CA5, 0x5CB4, 0x5CB7,
)
SHADOW_WORDS = {0x256B: 0, 0x2710: 0, 0x3F18: 672, 0x3F2C: 160, 0x54DD: 672}
SHADOW_OBLIGATIONS = (
    'ReviewedColdEntryAndRamClear', 'QualifiedPreAliasLoopExit', 'IndependentIeAndPendingFactorHandoff',
    'DisjointOrdinaryCalFrame', 'SourceOwnedIndexedPath', 'NoShadowInterference',
)
SHADOW_GAPS = ('CurrentNativeOwnerUnestablished', 'SharedSlotOnlyWithConfigurationReader3FF7',
               'ActualColdExitAndIndexedEntryUnestablished')


def _shadow_word(pair):
    low, high = _domain(pair['low']), _domain(pair['high'])
    word = low[0] + high[0] * 256 if len(low) == len(high) == 1 else None
    knowledge = _bits(low, 8)
    knowledge.update({str(int(bit) + 8): digit for bit, digit in _bits(high, 8).items()})
    possible_zero = 0 in low and 0 in high
    zf = int(word == 0) if word is not None else (None if possible_zero else 0)
    return word, knowledge, zf


def _shadow_admission(query, pair, stack_address, predecessor):
    writer = query['writer']
    pc, address, dd = writer['pc'], writer['address'], writer['dd']
    word_gen = pair['wordGeneration']
    low_gen, high_gen = pair['low']['generation'], pair['high']['generation']
    caller, context, frame, exits = (query[key] for key in ('callerPc', 'context', 'frame', 'exit'))
    expected = SHADOW_WORDS.get(pc)
    code_origin = {0x276A: 'Cold276A', 0x2B64: 'Independent2B64'}.get(caller)
    partial = None in (pc, address, word_gen, low_gen, high_gen, query['requestedGeneration'])
    incompatible_pair = expected is not None and (expected % 256 not in _domain(pair['low']) or
                                                    expected // 256 not in _domain(pair['high']))
    premise = query['premises']
    cold_context = (context['lrb'], context['scb'], context['usp'], context['data0230Bit3'], context['oldIrqh4'])
    valid_exit = exits['dp'] in range(0x0098, 0x0087, -2) and exits['usp'] in {0x0098, 0x0356}
    fully_declared = all(premise[key] is True for key in (
        'ownedColdNon47Entry', 'stableClearContext', 'firstExitBeforeActivePointerAlias',
        'ie2759SymbolicHandoff', 'indexedRouteQualified',
    ))
    return _first_refusal((
        (query['claim'] != 'ConditionalOnly', OUTSIDE, 'UnadmittedNativeShadowClaim'),
        ((query['consumerPc'], pair['address']) != (0x5CB7, 0x00FA), OUTSIDE, 'WrongShadowConsumerOrSlot'),
        (code_origin is None or code_origin != context['origin'], OUTSIDE, 'CallerContextMismatch'),
        (query['sourceBinding'] != 'M2cyShadowSourceReviewV1', OUTSIDE, 'SourceConflict'),
        (partial, UNKNOWN, 'MissingShadowGeneration'),
        (expected is None or address != 0x00FA or (pc in {0x256B, 0x2710} and dd != 1), OUTSIDE, 'SourceConflict'),
        (low_gen != high_gen, OUTSIDE, 'MixedByteGenerations'),
        (not low_gen == word_gen == query['requestedGeneration'], OUTSIDE, 'StaleShadowGeneration'),
        (incompatible_pair, OUTSIDE, 'SourceConflict'),
        (caller == 0x2B64, UNKNOWN,
         'CompetingShadowWriter' if predecessor in (0x00FA, 0x00FB) else 'CallerSpecificProvenanceUnresolved'),
        (pc not in (0x256B, 0x2710) or cold_context != (0x41, 0, 0x0180, 0, 1) or not (valid_exit and fully_declared),
         UNKNOWN, 'ReachingPathUnestablished'),
        (pc == 0x256B, OUTSIDE, 'StaleShadowGeneration'),
        (premise['noAsynchronousInterference'] is not True, UNKNOWN, 'UnexcludedInterference'),
        (None in (stack_address, frame['generation'], frame['callerPc']), UNKNOWN, 'UnknownStackOverlap'),
        (frame['callerPc'] != caller or (frame['memoryApplicable'], frame['integrity']) != (True, True),
         UNKNOWN, 'ShadowFrameObligationsUnmet'),
        (frame['generation'] == word_gen, OUTSIDE, 'ShadowGenerationReused'),
        (stack_address == 0x00FA, UNKNOWN, 'CompetingShadowWriter'),
        (_ordinary_indexed_alias(stack_address) or stack_address in range(0x0208, 0x0210, 2),
         UNKNOWN, 'ShadowFrameObligationsUnmet'),
        (_shadow_word(pair)[0] is None, UNKNOWN, 'ShadowWordValueUnestablished'),
    ))


def data00fa_caller_reaching_definitions(query):
    pair = deepcopy(query['initialPair'])
    caller, frame, context = (query[key] for key in ('callerPc', 'frame', 'context'))
    usp = context['usp']
    predecessor = ((usp - 86) % 65536 if caller == 0x2B64 and context['origin'] == 'Independent2B64'
                   and usp is not None else None)
    stack_address = None if frame['incomingSsp'] is None else frame['incomingSsp'] // 2 * 2
    rejection = _shadow_admission(query, pair, stack_address, predecessor)
    occupied = {pair['wordGeneration'], frame['generation']}
    writes = []
    for event in query['events'] if rejection is None else ():
        reached = event['reached']
        if reached is False:
            continue
        address, generation, value = (event[key] for key in ('address', 'generation', 'value'))
        if reached is not True or address is None or generation is None:
            rejection = UNKNOWN, 'UnknownStackOverlap' if event['kind'] == 'FrameStore' else 'UnexcludedInterference'
            break
        source_pc = event['writerPc']
        if source_pc in SHADOW_WORDS:
            correct_site = ((event['kind'] == 'IndirectStore' and address % 2 == 0) if source_pc == 0x2710 else
                            (event['kind'] == 'DirectStore' and address == 0x00FA))
            if not correct_site or event['widthBits'] != 16 or value not in (None, SHADOW_WORDS[source_pc]):
                rejection = OUTSIDE, 'SourceConflict'
                break
        if generation in occupied:
            rejection = OUTSIDE, 'ShadowGenerationReused'
            break
        occupied.add(generation)
        size = event['widthBits'] // 8
        aligned = address // size * size
        bytes_written = [None] * size if value is None else list(value.to_bytes(size, 'little'))
        observed = []
        for destination in sorted(set(range(aligned, aligned + size)) & {0xFA, 0xFB}):
            field = 'low' if destination == 0xFA else 'high'
            before = pair[field]
            byte = bytes_written[destination - aligned]
            observed.append({'address': destination, 'beforeGeneration': before['generation'],
                             'afterGeneration': generation,
                             'sameValue': byte == before['value'] if None not in (byte, before['value']) else None})
            pair[field] = {'value': byte, 'knownBits': {}, 'generation': generation}
        writes.append(dict(event, alignedAddress=aligned, shadowEffects=observed))
        if observed:
            pair['wordGeneration'] = generation if len(observed) == 2 else None
            rejection = UNKNOWN, 'CompetingShadowWriter'
            break
    status, reason = rejection or (COMPLETE, 'ConditionalShadowWriterRetained')
    word, knowledge, zf = _shadow_word(pair)
    writer = query['writer']['pc']
    conditional_writer = writer if rejection is None else None
    state = {'pair': pair, 'word': word, 'knownBits': knowledge, 'zf': zf,
             'sourceWriterExists': writer in SHADOW_WORDS,
             'writerReachableInReviewedCfg': (caller, writer) == (0x276A, 0x2710),
             'callReturnSummariesNeededForCandidate': (caller, writer) == (0x276A, 0x256B),
             'conditionalLastWriterPc': conditional_writer, 'currentNativeOwner': None,
             'predecessor2B61Address': predecessor, 'ordinaryCalFrameAddress': stack_address,
             'formalReturnCandidatePc': caller + 3 if caller in (0x276A, 0x2B64) else None}
    generations = {'conditionalRetained': pair['wordGeneration'] if conditional_writer else None,
                   'low': pair['low']['generation'], 'high': pair['high']['generation'],
                   'sharedWord': pair['wordGeneration'], 'frame': frame['generation']}
    return _result(SHADOW_SCOPE, status, caller=caller, state=state, stop='STOP_BEFORE_INDEXED_CONTINUATION_5CB7',
                   writes=writes, generations=generations, obligations=SHADOW_OBLIGATIONS,
                   branches=() if rejection else ({'pc': 0x5C86, 'nextPc': 0x5CA0, 'premise': 'Data0230Bit3Zero'},
                                                  {'pc': 0x5CA3, 'nextPc': 0x5CA5, 'premise': 'OldIrqh4One'}),
                   unresolved=(*SHADOW_GAPS, *((reason,) if rejection else ())), reason=reason)


COLD_SCOPE = (0x2766, 0x2768, 0x276A, 0x276D, 0x276F, 0x2771, 0x2773, 0x2777)
COLD_GAPS = ('ActualIndexedReturnUnobserved', 'NativeP2AndAdcReadbacksUnestablished',
             'NativeIterationCountUnestablished')


def _slot(raw=None, generation=None, knowledge=None):
    return {'value': raw, 'knownBits': {} if knowledge is None else knowledge, 'generation': generation}


def _accumulate_low(state, possible, load):
    possible = set(possible)
    known = state['registerKnownBits']
    state['registerKnownBits'] = {name: digit for name, digit in known.items() if not name.startswith('AL.')}
    state['registerKnownBits'].update({f'AL.{bit}': digit for bit, digit in _bits(possible, 8).items()})
    state['registers'].update(al=_agreed(possible), zf=_agreed(int(value == 0) for value in possible))
    if load:
        state['registers']['dd'] = 0


def _effect(pc, address, before, after, kind):
    raw_before, raw_after = before['value'], after['value']
    return {'pc': pc, 'address': address, 'widthBits': 8, 'kind': kind, 'before': before, 'after': after,
            'sameValue': raw_before == raw_after if None not in (raw_before, raw_after) else None}


def _generation_projection(state):
    if state is None:
        return None
    result = dict(state['generations'])
    if 'counterF7' in state:
        result['00F7'] = state['counterF7']['generation']
    if 'data00af' in state:
        result['00AF'] = state['data00af']['generation']
    return result


def cold_reacquisition_step(query):
    prefix_query = query['prefixQuery']
    states, reads, writes, branches, obligations = [], [], [], [], []
    state = acquisition_result = post_result = frame = None
    scopes = set(COLD_SCOPE)
    selected = None
    identity = query['iterationId']

    def output(status, reason, stop):
        return _result(sorted(scopes), status, caller=0x276A, state=state, stop=stop, reads=reads, writes=writes,
                       generations=_generation_projection(state), states=states,
                       obligations=obligations, unresolved=(*COLD_GAPS, *((reason,) if status != COMPLETE else ())),
                       branches=branches, iterations=({'id': identity, 'selectedIndex': selected},), reason=reason,
                       frozenAcquisition=acquisition_result, frozenPostIe=post_result, frozenIndexedFrame=frame)

    def append_effects(stage):
        scopes.update(stage['sourceScope'])
        reads.extend(stage['reads'])
        writes.extend(stage['orderedWrites'])
        states.extend(stage['intermediateStates'])
        obligations.extend(stage['formalObligations'])

    if prefix_query['callerPc'] != 0x276A:
        return output(OUTSIDE, 'ColdCaller276ARequired', 'STOP_BEFORE_CAL_276A')
    acquisition_result = accepted_indexed({key: query[key] for key in ('inputClass', 'prefixQuery', 'shadow')})
    selected = acquisition_result['frozenPrefixResult']['selectedIndex']
    state = acquisition_result['state']
    append_effects(acquisition_result)
    branches.extend(acquisition_result['branchOutcome'])
    stop = acquisition_result['stopBoundary']
    if acquisition_result['status'] != COMPLETE or stop != 'STOP_BEFORE_IE_WRITE_5CB9':
        return output(acquisition_result['status'], acquisition_result['reason'], stop)
    if query['postIe'] is None:
        return output(UNKNOWN, 'ExplicitPostIeBoundaryRequired', stop)
    post_snapshot = dict((key, state[key]) for key in SNAPSHOT_FIELDS)
    post_snapshot.update(inputClass=query['inputClass'], assumptions=prefix_query['snapshot']['assumptions'])
    post_result = accepted_post_ie(dict(query['postIe'], inputClass=query['inputClass'], snapshot=post_snapshot))
    state = post_result['state']
    append_effects(post_result)
    stop = post_result['stopBoundary']
    if post_result['status'] != COMPLETE or stop != 'STOP_BEFORE_RT_5CCD':
        return output(post_result['status'], post_result['reason'], stop)
    if query['returnQuery'] is None:
        return output(UNKNOWN, 'IndexedReturnFrameRequired', stop)
    frame = accepted_indexed_frame(query['returnQuery'])
    scopes.update(frame['sourceScope'])
    obligations.extend(frame['formalObligations'])
    if frame['status'] != COMPLETE or frame['state']['formalReturnedPc'] != 0x276D:
        return output(UNKNOWN, 'ColdIndexedReturnUnestablished', stop)
    if query['returnHandoff'] is not True:
        return output(UNKNOWN, 'ExplicitIndexedReturnHandoffRequired', stop)
    p2 = query['callerP2']
    if p2 is None or p2['generation'] is None:
        return output(UNKNOWN, 'CallerP2ReadGenerationMissing', 'STOP_BEFORE_P2_READ_276D')

    state = deepcopy(state)
    reads.append({'pc': 0x276D, 'address': 0x0024, 'widthBits': 8, 'space': 'SuppliedSymbolicReadback', 'slot': p2})
    possible_port = _domain(p2)
    _accumulate_low(state, possible_port, True)
    states.append({'pc': 0x276D, 'state': deepcopy(state)})
    masked_port = {value // 32 * 32 for value in possible_port}
    _accumulate_low(state, masked_port, False)
    states.append({'pc': 0x276F, 'state': deepcopy(state)})
    taken = _agreed(value != 0 for value in masked_port)
    branches.append({'pc': 0x2771, 'taken': taken, 'next': {None: None, False: 0x2773, True: 0x2766}[taken]})
    if taken is None:
        return output('IndeterminateBranch', 'P2SelectorZeroPredicateUnknown', 'STOP_BEFORE_JNE_2771')
    if taken:
        return output(COMPLETE, 'ColdRepeatSelected', 'STOP_BEFORE_WAIT_2766')

    before = query['counterF7'] or _slot()
    generation = 'M2cy:2773:' + identity
    if generation in {before['generation'], *state['generations'].values()}:
        return output(OUTSIDE, 'CounterF7GenerationCollision', 'STOP_BEFORE_COUNTER_2773')
    state['counterF7'] = _slot(1, generation)
    writes.append(_effect(0x2773, 0x00F7, before, state['counterF7'], 'ColdFirstCallCounter'))
    states.append({'pc': 0x2773, 'state': deepcopy(state)})
    return output(COMPLETE, 'ColdLoopExitSelected', 'STOP_BEFORE_CAL_2777')


HELPER_SCOPE = (0x5CD9, 0x5CDC, 0x5CDD, 0x5CDF, 0x5CE1, 0x5CE3, 0x5CE5, 0x5CE7, 0x5CE9,
                0x5CEB, 0x5CED, 0x5CEF, 0x5CF1, 0x5CF4, 0x5CF6, 0x5CF8, 0x5CF9)
HELPER_GAPS = ('PrimaryC8PredicateUnresolved', 'NativeData03d1OwnershipUnestablished',
               'NativeHelperExecutionUnestablished')


def _data(state, address):
    name = f'{address:04X}'
    knowledge = {position[-1]: digit for position, digit in state['knownBits'].items()
                 if position.startswith(name + '.')}
    return _slot(state['memory'][name], state['generations'][name], knowledge)


def _replace_data(state, address, possible, generation):
    key = f'{address:04X}'
    state['memory'][key] = _agreed(possible)
    state['generations'][key] = generation
    knowledge = _bits(possible, 8)
    state['knownBits'] = {name: digit for name, digit in state['knownBits'].items() if not name.startswith(key + '.')}
    state['knownBits'].update({key + '.' + bit: digit for bit, digit in knowledge.items()})
    return _slot(state['memory'][key], generation, knowledge)


def cold_reacquisition_sequence(query):
    step = cold_reacquisition_step(query['step'])
    state = deepcopy(step['state'])
    reads, writes, stages, branches = (list(step[key]) for key in (
        'reads', 'orderedWrites', 'intermediateStates', 'branchOutcome'))
    wait_steps = 0

    def finish(status, reason, boundary):
        suffix = () if reason == step['reason'] else (reason,)
        return _result(step['sourceScope'], status, caller=0x276A, state=state, stop=boundary, reads=reads,
                       writes=writes, states=stages, branches=branches, generations=_generation_projection(state),
                       obligations=step['formalObligations'], unresolved=(*step['unresolvedConstraints'], *suffix),
                       iterations=step['iterations'], reason=reason, frozenStep=step, waitSteps=wait_steps,
                       nextAcquisitionInvoked=False)

    if step['reason'] != 'ColdRepeatSelected':
        return finish(step['status'], step['reason'], step['stopBoundary'])
    regs = state['registers']
    waiting = 'STOP_BEFORE_WAIT_2766'
    if regs['lrb'] != 0x41 or regs['scb'] is None:
        return finish(UNKNOWN, 'WaitLocalOrPointingBankUnestablished', waiting)
    dpl = 0x84 + regs['scb'] * 8
    identity = query['step']['iterationId']
    occupied = set(state['generations'].values())
    possible_carry = (0, 1) if regs['cf'] is None else (regs['cf'],)
    for wait in range(query['maxWaitSteps']):
        ordinal = wait + 1
        local_gen = f'M2cy:2766:{identity}:{ordinal}'
        dpl_gen = f'M2cy:2768:{identity}:{ordinal}'
        generated = {local_gen, dpl_gen}
        if generated & occupied:
            return finish(OUTSIDE, 'ColdWaitGenerationCollision', waiting)
        occupied.update(generated)
        old_local, old_dpl = _data(state, 0x0208), _data(state, dpl)
        new_local_values = {value // 2 * 2 + carry for value in _domain(old_local) for carry in possible_carry}
        possible_dpl = {(value - 1) % 256 for value in _domain(old_dpl)}
        for pc, address, before, values, gen, kind in (
            (0x2766, 0x0208, old_local, new_local_values, local_gen, 'CarryToLocalBit0'),
            (0x2768, dpl, old_dpl, possible_dpl, dpl_gen, 'DplOnlyDecrement'),
        ):
            reads.append({'pc': pc, 'address': address, 'widthBits': 8, 'space': 'DATA', 'slot': before})
            after = _replace_data(state, address, values, gen)
            writes.append(_effect(pc, address, before, after, kind))
            stages.append({'pc': pc, 'slot': after})
        wait_steps = ordinal
        taken = _agreed(value != 0 for value in possible_dpl)
        branches.append({'pc': 0x2768, 'taken': taken, 'next': {None: None, False: 0x276A, True: 0x2766}[taken]})
        if taken is None:
            return finish('IndeterminateBranch', 'WaitDplPredicateUnknown', 'STOP_BEFORE_WAIT_EDGE_2768')
        if not taken:
            return finish(UNKNOWN, 'FrozenAcquisitionNamespaceCannotBeReused', 'STOP_BEFORE_CAL_276A')
    return finish(UNKNOWN, 'ColdWaitBoundReached', waiting)


def _helper_comparison(state, possible, comparand):
    rhs = range(256) if comparand is None else (comparand,)
    relations = {(left > right) - (left < right) for left in possible for right in rhs}
    state['registers'].update(cf=_agreed(int(rel < 0) for rel in relations),
                              zf=_agreed(int(rel == 0) for rel in relations))
    return {'printedOr': [True], 'comparativeAnd': sorted({rel > 0 for rel in relations})}


def helper_5cd9(query):
    snapshot = query['snapshot']
    state = {name: deepcopy(snapshot[name]) for name in SNAPSHOT_FIELDS}
    reads, writes, stages, branches = [], [], [], []
    lineage = None
    invocation = query['invocationId']
    counter = query['counterF7']

    def finish(status, reason, stop):
        return _result(HELPER_SCOPE, status, caller=0x2777, state=state, stop=stop, reads=reads,
                       writes=writes, states=stages, branches=branches, generations=_generation_projection(state),
                       unresolved=(*HELPER_GAPS, *((reason,) if status != COMPLETE else ())), reason=reason,
                       invocationId=invocation, data03d1Lineage=lineage, operandClass='InventedComparandsAndMarker',
                       nativeNormalRouteEstablished=False)

    def mark(pc):
        stages.append({'pc': pc, 'state': deepcopy(state)})

    def generation(pc):
        return f'M2cy:{pc:04X}:{invocation}'

    entry = 0x5CD9
    if (query['entryEstablished'] is not True or snapshot['assumptions']['noInterference'] is not True or
            snapshot['assumptions']['dataMapping'] != 'ConditionalByteArray'):
        return finish(UNKNOWN, 'HelperEntryOrInterferenceUnestablished', 'STOP_BEFORE_HELPER_5CD9')
    if state['registers']['scb'] != 0:
        return finish(UNKNOWN, 'ColdHelperScb0Required', 'STOP_BEFORE_HELPER_5CD9')
    occupied = set(state['generations'].values())
    if counter is not None:
        occupied.add(counter['slot']['generation'])
    if any(generation(pc) in occupied for pc in (entry, 0x5CEF, 0x5CF1, 0x5CF6)):
        return finish(OUTSIDE, 'HelperGenerationCollision', 'STOP_BEFORE_HELPER_5CD9')

    addresses = (0x84, 0x85)
    old_dp = [_data(state, address) for address in addresses]
    new_dp = [_replace_data(state, address, (byte,), generation(entry))
              for address, byte in zip(addresses, (0x03D1).to_bytes(2, 'little'), strict=True)]
    old_values = [slot['value'] for slot in old_dp]
    writes.append({'pc': entry, 'address': 0x84, 'widthBits': 16, 'kind': 'SelectedDpWrite',
                   'before': old_dp, 'after': new_dp, 'sameValue': None if None in old_values else old_values == [209, 3]})
    mark(entry)
    current = _data(state, 0x03D1)
    lineage = data03d1_reaching_definitions(query['lineage']) if query['lineage'] is not None else None
    stop = 'STOP_BEFORE_DATA03D1_READ_5CDC'
    if lineage is None or lineage['reason'] != 'ConditionalIndexedGenerationAt5cdc':
        return finish(UNKNOWN, 'Data03d1ReachingDefinitionUnestablished', stop)
    proof = lineage['state']['lastSlots']['03D1']
    if any(proof[field] != current[field] for field in ('value', 'generation')):
        return finish(OUTSIDE, 'Data03d1SnapshotMismatch', stop)
    if snapshot['assumptions']['ordinaryByteSemantics'] is not True:
        return finish(UNKNOWN, 'OrdinaryByteSemanticsUnestablished', stop)

    values = _domain(current)
    reads.append({'pc': 0x5CDC, 'address': 0x03D1, 'widthBits': 8, 'space': 'DATA', 'slot': current})
    _accumulate_low(state, values, True)
    mark(0x5CDC)
    hypotheses = _helper_comparison(state, values, query['thresholds']['5CDD'])
    mark(0x5CDD)
    consensus = _agreed(branch for possibilities in hypotheses.values() for branch in possibilities)
    branches.append({'pc': 0x5CDF, 'taken': consensus, 'next': {True: 0x5CED, False: 0x5CE1, None: None}[consensus],
                     'hypotheses': hypotheses})
    if consensus is not True:
        return finish('IndeterminateBranch', 'PrimaryC8BranchUnresolved', 'STOP_BEFORE_JGT_5CDF')

    marker = query['errorByte']
    possible_marker = range(256) if marker is None else (marker,)
    _accumulate_low(state, possible_marker, True)
    mark(0x5CED)
    state['data00af'] = _slot(marker, generation(0x5CEF))
    writes.append(_effect(0x5CEF, 0x00AF, _slot(), state['data00af'], 'ConditionalHelperMarker'))
    mark(0x5CEF)
    if (counter is None or (counter['sourcePc'], counter['firstCall'], counter['noInterference']) != (0x2773, True, True)
            or counter['slot']['generation'] is None or counter['slot']['value'] != 1
            or counter['slot']['generation'] != counter['expectedGeneration']):
        return finish(UNKNOWN, 'FirstCallCounterGenerationUnestablished', 'STOP_BEFORE_DECB_5CF1')
    original_counter = counter['slot']
    reads.append({'pc': 0x5CF1, 'address': 0x00F7, 'widthBits': 8, 'space': 'DATA', 'slot': original_counter})
    state['counterF7'] = _slot((original_counter['value'] - 1) % 256, generation(0x5CF1))
    writes.append(_effect(0x5CF1, 0x00F7, original_counter, state['counterF7'], 'ConditionalByteDecrement'))
    state['registers'].update(zf=1, hc=0)
    mark(0x5CF1)
    branches.append({'pc': 0x5CF4, 'taken': False, 'next': 0x5CF6})
    before = _data(state, 0xF5)
    after = _replace_data(state, 0xF5, possible_marker, generation(0x5CF6))
    writes.append(_effect(0x5CF6, 0xF5, before, after, 'ConditionalHelperMarker'))
    mark(0x5CF6)
    return finish(COMPLETE, 'FirstCallFaultRoute', 'STOP_BEFORE_BRK_5CF8')


def _ordinary_indexed_alias(address):
    return address is not None and (address < 0x00C0 or address in (0x0208, 0x0230, 0x0356) or
                                    0x03C6 <= address <= 0x03D4)


def rt5cf9_obligations(query):
    call, boundary, expected = (query[key] for key in ('frameQuery', 'helperBoundary', 'expectedFrameGeneration'))
    frame = call['frame']
    ssp, pre_rt = call['incomingSsp'], call['sspBeforeReturn']
    address = None if ssp is None else ssp // 2 * 2
    pushed = None if ssp is None else (ssp - 2) % 65536
    popped = None if pre_rt is None else (pre_rt + 2) % 65536
    source = None if popped is None else popped // 2 * 2
    saved = None if None in (frame['low'], frame['high']) else frame['low'] + frame['high'] * 256
    guarded_alias = _ordinary_indexed_alias(address) or address in (0x00AE, 0x00F4, 0x00F6, 0x00F8,
                                                                   0x00FA, 0x025A, 0x03D0)
    premises = ('matchingEntryReturn', 'stackMemoryApplicable', 'balancedNesting', 'frameIntegrity', 'noAliasInterference')
    rejection = _first_refusal((
        (call['claim'] != 'ConditionalOnly', OUTSIDE, 'NonConditionalFrameClaim'),
        ((call['callerPc'], call['declaredTarget'], call['returnPc']) != (0x2777, 0x5CD9, 0x5CF9),
         OUTSIDE, 'HelperReturnSourceMismatch'),
        (call['sourceBinding'] != 'M2cyStatic2777FrameV1', UNKNOWN, 'HelperReturnSourceBindingRequired'),
        (boundary == 0x5CF8, OUTSIDE, 'FaultBoundaryIsNotNormalReturn'),
        (boundary != 0x5CF9, UNKNOWN, 'HypotheticalNormalFrontierRequired'),
        (frame['kind'] != 'NormalCall', OUTSIDE, 'InterruptFrameCannotReturnViaRt'),
        (None in (ssp, pre_rt), UNKNOWN, 'StackPointerUnknown'),
        (pre_rt != pushed, OUTSIDE, 'UnbalancedStackPointer'),
        (guarded_alias, OUTSIDE, 'HelperFrameAliasRequiresIndependentProof'),
        (any(call['premises'][name] is not True for name in premises), UNKNOWN, 'FramePremisesNotEstablished'),
        (None in (expected, frame['generation'], frame['address'], frame['creatorPc'], saved),
         UNKNOWN, 'FrameContentsOrOwnerUnknown'),
        ((frame['generation'], frame['address'], frame['creatorPc'], saved) != (expected, address, 0x2777, 0x277A),
         OUTSIDE, 'FrameDoesNotMatchHelperCall'),
    ))
    status, reason = rejection or (COMPLETE, 'ConditionalMatchingFrame')
    geometry = {'frameAddress': address, 'sspAfterCall': pushed, 'sspAfterReturn': popped,
                'returnReadAddress': source, 'savedPc': saved}
    state = {'geometry': geometry, 'formalReturnedPc': None if rejection else 0x277A, 'candidateReturnPc': 0x277A,
             'nativeReturnEstablished': False}
    obligations = ({'kind': 'FormalCalWordStore', 'pc': 0x2777, 'address': address, 'widthBits': 16, 'value': 0x277A},
                   {'kind': 'FormalRtWordRead', 'pc': 0x5CF9, 'address': source, 'widthBits': 16, 'value': saved})
    return _result((0x2777, 0x5CD9, 0x5CF8, 0x5CF9), status, caller=0x2777, state=state,
                   stop='STOP_BEFORE_BRK_5CF8' if boundary == 0x5CF8 else 'STOP_BEFORE_RT_5CF9',
                   evidence='StaticFormalSourceObligation', obligations=obligations,
                   unresolved=(reason,) if rejection else ('ActualNativeReturnUnobserved',),
                   generations={'expectedFrame': expected, 'suppliedFrame': frame['generation']}, reason=reason)


OPERATIONS = {func.__name__: func for func in (
    data00fa_caller_reaching_definitions, cold_reacquisition_step, cold_reacquisition_sequence,
    helper_5cd9, data03d1_reaching_definitions, cold_adc_generation_timeline, rt5cf9_obligations,
)}


def record(case):
    return deepcopy(_record(case, OPERATIONS[case['operation']](case['input'])))
