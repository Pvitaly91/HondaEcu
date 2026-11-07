"""Conditional DATA03CB writer windows and a source-bound, detached USP proof."""
from copy import deepcopy

from enclosing_caller_return.state import frozen, input_class, label, need, number, shape, slot, tri
from shadow_cold_reacquisition.adc_generation_timeline import cold_adc_generation_timeline, validate as validate_timeline

from .cold_source_join import cold_caller_mode_source_join
from .wire import result

SOURCE = 'M2czData03cbSourceV1'
TARGET, AL_SOURCE, USP_STORE = 0x03CB, 0x27AE, 0x27B2
COMPLETE, UNKNOWN, OUTSIDE = 'CompleteConditional', 'IndeterminateObligation', 'OutsideVerifiedScope'
CLAIMS = ('ConditionalOnly', 'NativeOwner', 'ModeConsumerReached', 'ActualHardware', 'RuntimeAdmission')
USP_SCOPE = (0x277A, 0x279E, 0x27A2, AL_SOURCE, 0x27B0, USP_STORE, 0x7C0B, 0x7C11)
USP_PREMISES = ('hypotheticalReturn', 'symbolicSfr', 'dataMapping', 'noInterference')
USP_OBLIGATIONS = ('SeparateFormal277aHandoff', 'QualifiedSymbolicAdcAndSfrContext',
                   'ColdLrb0041AndScb0', 'ExactRetainedUspGeneration', 'SymbolicPrivateImmediateAt27ae')
LOCAL = {0x2766: 8, 0x27C3: 16, 0x7DF4: 8}
INDIRECT = (0x2785, 0x27AD, 0x27B9, 0x27BB)
FRAME_CALLERS = (0x276A, 0x2777, 0x27D0)
LATE_ORDER = (0x2777, 0x2785, 0x27AD, 0x27B2, 0x27B9, 0x27BB, 0x27C3, 0x27D0, 0x7DF4)
SCOPE = tuple(sorted({*USP_SCOPE, *LOCAL, *INDIRECT, *FRAME_CALLERS, 0x5CAF, 0x5CB4, 0x5CC2, 0x60CC}))
WINDOW_STOP = 'STOP_BEFORE_UNBOUND_MODE_READ_60CC'
WINDOW_GAPS = ('NoGlobalWriterExclusion', 'NativeData03cbOwnerUnbound', 'ModeConsumer60ccUnbound')
WINDOW_OBLIGATIONS = ('ExactFrozenIndex5Writer', 'OrderedLaterSourceEvents', 'ExcludeUnknownAliasesAndInterference',
                      'SeparateHelperReturnAndModeEntry')
EVENT_FIELDS = {
    'Indexed': ('iterationId', 'fromIteration', 'p2', 'adcr0h', 'scb', 'generation', 'returned', 'repeat'),
    'Frame': ('pc', 'ssp', 'generation', 'pathEstablished', 'memoryApplicable'),
    'Usp27B2': ('proof',),
    'Local': ('pc', 'lrb', 'generation', 'pathEstablished'),
    'OffPage': ('pc', 'lrb', 'generation', 'pathEstablished'),
    'Indirect': ('pc', 'address', 'generation', 'pathEstablished'),
    'Unknown': (),
}


def _validate_alias(query):
    shape(query, ('inputClass', 'sourceBinding', 'entryUsp', 'currentUsp', 'lrb', 'scb', 'dd',
                  'alRead', 'writerGeneration', 'premises', 'claim'), 'ClosedUsp27b2QueryRequired')
    input_class(query['inputClass'])
    need(query['claim'] in CLAIMS and label(query['sourceBinding']) and label(query['writerGeneration']),
         'TypedUsp27b2ClaimRequired')
    for field in ('entryUsp', 'currentUsp'):
        word = query[field]
        shape(word, ('value', 'generation'), 'ClosedUspWordRequired')
        need(number(word['value'], 0xFFFF) and label(word['generation']), 'TypedUspWordRequired')
    need(number(query['lrb'], 0xFFFF) and number(query['scb'], 7) and number(query['dd'], 1),
         'TypedUspAddressContextRequired')
    al = query['alRead']
    shape(al, ('sourcePc', 'address', 'slot'), 'ClosedUspStoreSourceRequired')
    need(number(al['sourcePc'], 0xFFFF) and number(al['address'], 0xFFFF), 'TypedUspStoreSourceRequired')
    slot(al['slot'])
    shape(query['premises'], USP_PREMISES, 'ClosedUspContinuityPremisesRequired')
    need(all(tri(value) for value in query['premises'].values()), 'TypedUspContinuityPremisesRequired')


def usp27b2_alias_proof(query):
    """Derive a byte alias from an owned USP, with a separate numeric candidate."""
    _validate_alias(query)
    entry, current, al = query['entryUsp'], query['currentUsp'], query['alRead']
    value, gen = current['value'], current['generation']
    writer_gen = query['writerGeneration']
    candidate = None if value is None else (value - 0x4E) & 0xFFFF
    numeric_overlap = None if candidate is None else candidate == TARGET
    if query['claim'] != 'ConditionalOnly':
        status, reason = OUTSIDE, 'NonConditionalUspClaim'
    elif query['sourceBinding'] != SOURCE:
        status = UNKNOWN if query['sourceBinding'] is None else OUTSIDE
        reason = 'UspSourceBindingUnqualified'
    elif query['dd'] == 1:
        status, reason = OUTSIDE, 'UspStoreDescriptorMismatch'
    elif None in (value, gen, entry['value'], entry['generation'], query['dd']):
        status, reason = UNKNOWN, 'CurrentUspGenerationUnbound'
    elif current != entry:
        status, reason = OUTSIDE, 'UspGenerationNotRetained'
    elif (query['lrb'], query['scb']) != (0x0041, 0):
        status, reason = UNKNOWN, 'UspCorridorBankContextUnqualified'
    elif any(query['premises'][name] is not True for name in USP_PREMISES):
        status, reason = UNKNOWN, 'UspCorridorHandoffUnqualified'
    elif (al['sourcePc'], al['address']) != (AL_SOURCE, None):
        status, reason = OUTSIDE, 'UspStoreAlSourceMismatch'
    elif writer_gen is None or al['slot']['generation'] is None:
        status, reason = UNKNOWN, 'UspStoreGenerationMissing'
    elif writer_gen in (gen, al['slot']['generation']):
        status, reason = OUTSIDE, 'UspWriterGenerationReused'
    elif candidate < 0x00C0 or candidate == 0x4700:
        status, reason = OUTSIDE, 'UspDestinationOutsideReviewedDataScope'
    else:
        status = COMPLETE
        reason = 'QualifiedUspByteOverlap' if numeric_overlap else 'QualifiedUspByteDisjoint'
    admitted = status == COMPLETE
    state = {'numericAddressCandidate': candidate, 'numericOverlapCandidate': numeric_overlap,
             'qualifiedAddress': candidate if admitted else None, 'overlap03cb': numeric_overlap if admitted else None,
             'retainedUspGeneration': gen if admitted else None, 'nativeOwner': None,
             'alSourceClass': 'PrivateImmediateAt27AE_SymbolicInput' if admitted else None}
    writes = ({'pc': USP_STORE, 'address': candidate, 'widthBits': 8,
               'slot': {**al['slot'], 'generation': writer_gen}},) if admitted else ()
    gaps = ('NativeIncomingUspUnbound', 'NativePostHelperPathUnbound')
    return result(status, source_scope=USP_SCOPE, caller=0x276A, state=state,
                  stop='STOP_BEFORE_27B4' if admitted else 'STOP_BEFORE_USP_STORE_27B2',
                  writes=writes, generations={'usp': gen if admitted else None, 'writer': writer_gen if admitted else None},
                  obligations=USP_OBLIGATIONS, unresolved=gaps if admitted else (*gaps, reason), reason=reason)


def _validate_window(query):
    shape(query, ('inputClass', 'sourceBinding', 'initialTimeline', 'requestedGeneration', 'events',
                  'noInterference', 'claim'), 'ClosedData03cbWriterWindowRequired')
    input_class(query['inputClass'])
    need(query['claim'] in CLAIMS and label(query['sourceBinding']) and label(query['requestedGeneration'])
         and tri(query['noInterference']), 'TypedData03cbWriterWindowRequired')
    validate_timeline(query['initialTimeline'])
    need(query['initialTimeline']['inputClass'] == query['inputClass'], 'WriterTimelineInputClassMismatch')
    events = query['events']
    need(type(events) is list and len(events) <= 24, 'BoundedCompetingWriterEventsRequired')
    seen = set()
    for event in events:
        need(type(event) is dict and type(event.get('kind')) is str and event['kind'] in EVENT_FIELDS,
             'TypedCompetingWriterEventRequired')
        kind = event['kind']
        shape(event, ('kind', 'id', *EVENT_FIELDS[kind]), 'ClosedCompetingWriterEventRequired')
        identity = event['id']
        need(identity is not None and label(identity) and identity not in seen, 'DistinctCompetingWriterIdRequired')
        seen.add(identity)
        if kind == 'Indexed':
            slot(event['p2'])
            slot(event['adcr0h'])
            need(all(label(event[k]) for k in ('iterationId', 'fromIteration', 'generation'))
                 and number(event['scb'], 7) and tri(event['returned']) and tri(event['repeat']),
                 'TypedIndexedRepeatWriterRequired')
        elif kind == 'Usp27B2':
            _validate_alias(event['proof'])
            need(event['proof']['inputClass'] == query['inputClass'], 'UspWriterInputClassMismatch')
        elif kind != 'Unknown':
            need(number(event['pc'], 0xFFFF) and label(event['generation']) and tri(event['pathEstablished']),
                 'TypedMappedWriterRequired')
            operand = 'ssp' if kind == 'Frame' else 'address' if kind == 'Indirect' else 'lrb'
            need(number(event[operand], 0xFFFF), 'TypedWriterAddressContextRequired')
            if kind == 'Frame':
                need(tri(event['memoryApplicable']), 'TypedFrameMappingPremiseRequired')


def _indexed_effect(event, previous, used_iterations):
    identity = event['iterationId']
    if identity is None or identity in used_iterations or event['fromIteration'] != previous:
        return OUTSIDE, 'IndexedRepeatIdentityMismatch', None
    if event['returned'] is not True or event['repeat'] is not True:
        return UNKNOWN, 'IndexedReturnOrRepeatUnestablished', None
    p2 = event['p2']
    values = frozen.candidates(p2['value'], {f'v.{k}': v for k, v in p2['knownBits'].items()}, 'v')
    indexes = {value >> 5 for value in values}
    if len(indexes) != 1 or event['scb'] is None or p2['generation'] is None:
        return UNKNOWN, 'IndexedSelectorOrBankUnbound', None
    if event['adcr0h']['generation'] is None:
        return UNKNOWN, 'Adcr0hSourceGenerationUnbound', None
    index = next(iter(indexes))
    return COMPLETE, None, (0x5CB4, 0x03C6 + index, 8, event['adcr0h']['value'],
                            event['adcr0h']['knownBits'], event['generation'], identity, index)


def _mapped_effect(event):
    pc, kind = event['pc'], event['kind']
    allowed = {'Frame': FRAME_CALLERS, 'Local': LOCAL, 'OffPage': (0x5CC2,), 'Indirect': INDIRECT}
    if pc not in allowed[kind]:
        return OUTSIDE, 'UnreviewedCompetingWriterSite', None
    if event['pathEstablished'] is False:
        return COMPLETE, None, None
    if event['pathEstablished'] is not True:
        return UNKNOWN, 'CompetingWriterPathUnestablished', None
    if kind == 'Frame':
        width, value = 16, pc + 3
        ssp = event['ssp']
        if ssp is None or event['memoryApplicable'] is not True:
            return UNKNOWN, 'FrameAliasOrMappingUnbound', None
        address = ssp & 0xFFFE
        if address < 0x00C0 or address == 0x4700:
            return OUTSIDE, 'FrameControlOrUnsupportedAlias', None
    elif kind == 'Indirect':
        address, width, value = event['address'], 8, None
        if address is None:
            return UNKNOWN, 'IndirectAliasUnbound', None
        # The reviewed fixed DP assignments exclude this byte. The input
        # remains a conditional address, never an extracted private operand.
        if address == TARGET or address < 0x00C0 or address == 0x4700:
            return OUTSIDE, 'IndirectAddressContradictsReviewedFootprint', None
    else:
        lrb = event['lrb']
        if lrb is None:
            return UNKNOWN, 'WriterBankOrPageUnbound', None
        width = LOCAL[pc] if kind == 'Local' else 16
        address = (lrb & 0x1FFF) << 3 if kind == 'Local' else ((lrb & 0x1FE0) << 3) | 0x5A
        value = None
        if address < 0x00C0 or address == 0x4700:
            return OUTSIDE, 'LocalOrPageControlAlias', None
    return COMPLETE, None, (pc, address, width, value, {}, event['generation'], None, None)


def data03cb_competing_writer_exclusion(query):
    """Join a frozen index-5 seed with ordered conditional writer footprints."""
    _validate_window(query)
    initial = query['initialTimeline']
    seed = current = writer = None
    events, states, repeats, usp_proofs = [], [], [], []

    def finish(status, reason, relation):
        retained = current['generation'] if status == COMPLETE and current is not None else None
        return result(status, source_scope=SCOPE, caller=0x276A, stop=WINDOW_STOP,
                      state={'localWriterProven': seed is not None, 'candidate': seed,
                             'lastEstablishedSlot': current, 'retention': relation, 'nativeOwner': None},
                      writes=events, intermediate=states, iterations=repeats,
                      generations={'candidate': None if seed is None else seed['generation'],
                                   'lastEstablished': None if current is None else current['generation'],
                                   'retained': retained},
                      obligations=WINDOW_OBLIGATIONS,
                      unresolved=WINDOW_GAPS if status == COMPLETE else (*WINDOW_GAPS, reason),
                      reason=reason, frozenWriter=writer, uspProofs=usp_proofs)

    if query['claim'] != 'ConditionalOnly':
        return finish(OUTSIDE, 'NonConditionalWriterClaim', 'ConflictingWriterEvidence')
    if query['sourceBinding'] != SOURCE:
        return finish(UNKNOWN if query['sourceBinding'] is None else OUTSIDE,
                      'WriterSourceBindingUnqualified', 'SourcePathUnestablished')
    if len(initial['events']) != 1 or initial['events'][0]['kind'] != 'Acquisition':
        return finish(OUTSIDE, 'OneInitialIndexedAcquisitionRequired', 'ConflictingWriterEvidence')
    writer = cold_adc_generation_timeline(initial)
    slot03cb = writer['state']['lastSlots']['03CB']
    if writer['status'] != COMPLETE or slot03cb['writerPc'] != 0x5CB4 or slot03cb['generation'] is None:
        return finish(UNKNOWN, 'FrozenIndex5WriterUnestablished', 'MissingGeneration')
    seed = current = {**slot03cb, 'knownBits': {}}
    previous = seed['iterationId']
    used_iterations = {previous}
    occupied = {entry['generation'] for entry in writer['orderedWrites']}
    occupied.update(entry['generation'] for entry in initial['initial'].values() if entry['generation'] is not None)
    repeats.extend(writer['iterations'])
    late = -1
    for event in query['events']:
        kind = event['kind']
        if kind == 'Unknown':
            return finish(UNKNOWN, 'PotentialUnknownWriter', 'UnexcludedInterference')
        if kind == 'Indexed':
            status, reason, effect = _indexed_effect(event, previous, used_iterations)
        elif kind == 'Usp27B2':
            proof = usp27b2_alias_proof(event['proof'])
            usp_proofs.append(proof)
            status, reason = proof['status'], proof['reason']
            effect = None
            if status == COMPLETE:
                change = proof['orderedWrites'][0]
                observed = change['slot']
                effect = (USP_STORE, change['address'], 8, observed['value'], observed['knownBits'],
                          observed['generation'], None, None)
        else:
            status, reason, effect = _mapped_effect(event)
        if status != COMPLETE:
            return finish(status, reason, 'UnknownAlias' if status == UNKNOWN else 'ConflictingWriterEvidence')
        if effect is None:
            continue
        pc, address, width, value, bits, gen, iteration, index = effect
        if pc in LATE_ORDER:
            rank = LATE_ORDER.index(pc)
            if rank <= late:
                return finish(OUTSIDE, 'WriterSourceOrderMismatch', 'ConflictingWriterEvidence')
            late = rank
        elif late >= 0:
            return finish(OUTSIDE, 'IndexedWriterAfterColdExit', 'ConflictingWriterEvidence')
        if gen is None:
            return finish(UNKNOWN, 'CompetingWriterGenerationMissing', 'MissingGeneration')
        if gen in occupied:
            return finish(OUTSIDE, 'CompetingWriterGenerationReused', 'ConflictingWriterEvidence')
        occupied.add(gen)
        if iteration is not None:
            repeats.append({'iterationId': iteration, 'fromIteration': previous, 'selectedIndex': index,
                            'suppliedP2': event['p2']['value'], 'suppliedAdcr0h': value})
            previous = iteration
            used_iterations.add(iteration)
        overlap = address <= TARGET < address + width // 8
        before = deepcopy(current)
        if overlap:
            byte = None if value is None else (value >> (8 * (TARGET - address))) & 0xFF
            current = {'value': byte, 'knownBits': bits, 'generation': gen, 'writerPc': pc, 'iterationId': iteration}
        same = None if not overlap or None in (before['value'], current['value']) else before['value'] == current['value']
        events.append({'id': event['id'], 'kind': kind, 'pc': pc, 'address': address, 'widthBits': width,
                       'generation': gen, 'overlap03cb': overlap, 'sameValue': same,
                       'before': before, 'after': deepcopy(current)})
        states.append({'eventId': event['id'], 'lastEstablishedSlot': deepcopy(current)})
    if query['noInterference'] is not True:
        return finish(UNKNOWN, 'InterferenceNotExcluded', 'UnexcludedInterference')
    if query['requestedGeneration'] is None:
        return finish(UNKNOWN, 'RequestedGenerationMissing', 'MissingGeneration')
    if query['requestedGeneration'] != seed['generation']:
        return finish(UNKNOWN, 'RequestedGenerationNotTheSeed', 'StaleGeneration')
    if current['generation'] != seed['generation']:
        return finish(UNKNOWN, 'ReviewedWriterReplacedSeed', 'CompetingWriterPresent')
    return finish(COMPLETE, 'ScopedWriterExclusionEstablished',
                  'ConditionalGenerationRetained' if events else 'ConfirmedLocalNoOverwrite')


def data03cb_to_mode_reaching_definitions(query):
    """Bind the local seed to the actual conditional cold prefix, then stop at its unresolved edge."""
    shape(query, ('inputClass', 'writerQuery', 'coldJoinQuery', 'proposedRead', 'claim'),
          'ClosedData03cbModeReachQueryRequired')
    input_class(query['inputClass'])
    read = query['proposedRead']
    shape(read, ('pc', 'address', 'widthBits', 'generation'), 'ClosedProposedModeReadRequired')
    need(query['claim'] in CLAIMS and number(read['pc'], 0xFFFF) and number(read['address'], 0xFFFF)
         and number(read['widthBits'], 16) and label(read['generation']), 'TypedProposedModeReadRequired')
    writer_query, cold_query = query['writerQuery'], query['coldJoinQuery']
    need(type(writer_query) is dict and type(cold_query) is dict
         and writer_query.get('inputClass') == cold_query.get('inputClass') == query['inputClass'],
         'ModeReachingInputClassMismatch')
    writer = cold = None
    linked = False

    def finish(status, reason, boundary):
        state = {'localWriterProven': bool(writer and writer['state']['localWriterProven']),
                 'conditionalRetention': bool(writer and writer['status'] == COMPLETE),
                 'linkedToColdPrefix': linked, 'conditionalSourcePathTo60cc': False, 'nativeOwnership': None}
        return result(status, source_scope=SCOPE, caller=0x276A, state=state, stop=boundary,
                      generations=None if writer is None else writer['generations'],
                      iterations=() if writer is None else writer['iterations'],
                      obligations=WINDOW_OBLIGATIONS,
                      unresolved=(*WINDOW_GAPS, reason), reason=reason, writerResult=writer, coldResult=cold)

    if query['claim'] != 'ConditionalOnly':
        return finish(OUTSIDE, 'NonConditionalModeReadClaim', WINDOW_STOP)
    if (read['pc'], read['address'], read['widthBits']) != (0x60CC, TARGET, 8):
        return finish(OUTSIDE, 'ModeReadSourceIdentityMismatch', WINDOW_STOP)
    writer = data03cb_competing_writer_exclusion(writer_query)
    if writer['status'] != COMPLETE:
        return finish(writer['status'], writer['reason'], writer['stopBoundary'])
    seed = writer['state']['candidate']
    if read['generation'] != seed['generation']:
        return finish(UNKNOWN, 'ModeReadGenerationMismatch', WINDOW_STOP)
    cold = cold_caller_mode_source_join(cold_query)
    cold_step = cold['frozenColdResult']
    if cold_step is not None and cold_step['frozenAcquisition'] is not None:
        child = cold_step['frozenAcquisition']['frozenPrefixResult']
        linked = (child['conditionalData03cbWriterEstablished'] is True and child['selectedIndex'] == 5
                  and bool(cold_step['iterations'])
                  and cold_step['iterations'][0]['id'] == seed['iterationId']
                  and child['state']['memory']['03CB'] == seed['value']
                  and child['state']['generations']['03CB'] == seed['generation'])
    if not linked:
        return finish(UNKNOWN, 'ColdPrefixWriterGenerationUnlinked', cold['stopBoundary'])
    return finish(UNKNOWN, 'ModeReadSourcePathUnestablished', cold['stopBoundary'])
