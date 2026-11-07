"""Independent M2cx equations over accepted references and qualified premises."""

from copy import deepcopy
from itertools import product

from enclosing_caller_return.reference_oracle import (
    AUTHORITY as ACCEPTED_AUTHORITY,
    call_return_obligations as accepted_frame,
    indexed_acquisition_caller as accepted_indexed,
)
from payload_consumer_tail.reference_oracle import canonical


BASE = 'e072dd9cf2ff68bacd3ea8353decae9ff55b7383'
AUTHORITY = {**ACCEPTED_AUTHORITY, 'actualIeWrite': None, 'actualIrqDelivery': None}
APPLICABILITY = 'ConditionalSoftwareOnly_HardwareApplicabilityUnestablished'
SOURCE_IDENTITIES = {
    'm2cwBase': BASE,
    'm2cvFrameReview': '7e4ba87467d98becfeff774b92bfdf2c3aeca07e88baf7b713fd9aafba14c9f8',
    'm2cwSourceBinding': '912c5fc8fc26dc06fe21b83c96fc81a17875292b682d1f9d3a812d2926098ae7',
    'primaryIsa': 'f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271',
}
OUTPUT_FIELDS = (
    'sourceScope', 'sourceIdentities', 'evidenceClass', 'applicability', 'state', 'branchOutcome',
    'reads', 'orderedWrites', 'generations', 'intermediateStates', 'formalObligations',
    'unresolvedConstraints', 'stopBoundary',
)


def _result(scope, status, *, state=None, stop=None, evidence='ConditionalSourceModel',
            reads=(), writes=(), generations=None, states=(), obligations=(), unresolved=(),
            branches=(), **extra):
    return deepcopy({
        'status': status, 'sourceScope': list(scope), 'sourceIdentities': SOURCE_IDENTITIES,
        'evidenceClass': evidence, 'applicability': APPLICABILITY, 'state': state, 'branchOutcome': list(branches),
        'reads': list(reads), 'orderedWrites': list(writes), 'generations': generations,
        'intermediateStates': list(states), 'formalObligations': list(obligations),
        'unresolvedConstraints': list(unresolved), 'stopBoundary': stop, **AUTHORITY, **extra,
    })


def _bits(value, width):
    return {str(i): value // (2 ** i) % 2 for i in range(width)}


def _domain(value, known, width=8):
    if value is not None:
        return (value,)
    fixed = sum(2 ** int(bit) for bit, digit in known.items() if digit)
    unknown_places = [i for i in range(width) if str(i) not in known]
    return tuple(fixed + sum(2 ** place * digit for place, digit in zip(unknown_places, pattern, strict=True))
                 for pattern in product((0, 1), repeat=len(unknown_places)))


def _common(values, width):
    full = {str(i): {value // (2 ** i) % 2 for value in values} for i in range(width)}
    return {i: next(iter(values)) for i, values in full.items() if len(values) == 1}


def _scalar(values):
    values = set(values)
    return next(iter(values)) if len(values) == 1 else None


def _datum(state, address):
    address = f'{address:04X}'
    return {'value': state['memory'][address], 'generation': state['generations'][address],
            'knownBits': {key[-1]: bit for key, bit in state['knownBits'].items()
                          if key.startswith(f'{address}.')}}


def _put_register(state, register, value, knowledge):
    state['registers'][register] = value
    bits = state['registerKnownBits']
    for key in tuple(bits):
        if key.startswith(register.upper() + '.'):
            del bits[key]
    bits.update({f'{register.upper()}.{key}': bit for key, bit in knowledge.items()})


def _knowledge(slot, width=8):
    return _bits(slot['value'], width) if slot['value'] is not None else slot['knownBits']


def _qualified_rejections(checks, complete):
    return next(((status, reason) for failed, status, reason in checks if failed),
                ('CompleteConditional', complete))


def _event_addresses(event):
    address = event['address']
    if address is None:
        return ()
    width_bytes = event['widthBits'] // 8
    start = address // width_bytes * width_bytes
    return tuple(range(start, start + width_bytes))


def _reused_generation(events, original):
    known_generations = [event['generation'] for event in events if event['generation'] is not None]
    return original in known_generations or len(set(known_generations)) != len(known_generations)


SHADOW_WRITERS = {
    0xFA: {0x256B: 0, 0x3F18: 0x02A0, 0x3F2C: 0x00A0, 0x54DD: 0x02A0},
    0xF8: {0x2569: 0, 0x3F16: 0x2BAB, 0x3F2A: 0xA9A3, 0x54E5: 0x2BAB},
}


def _shadow(query, address):
    low, high = query['low'], query['high']
    gen = query['generation']
    source = query['sourcePc']
    writers = SHADOW_WRITERS.get(address, {})
    state = {'address': address, 'word': None, 'knownBits': {}, 'zf': None,
             'generation': None, 'candidateSourcePc': source, 'nativeGeneration': None}
    events = query['events']
    knowledge = {**_knowledge(low), **{str(8 + int(i)): digit for i, digit in _knowledge(high).items()}}
    word = sum(int(digit) * 2 ** int(i) for i, digit in knowledge.items()) if len(knowledge) == 16 else None
    source_value = writers.get(source)
    checks = (
        (query['claim'] != 'ConditionalOnly', 'OutsideVerifiedScope', 'NonConditionalShadowClaim'),
        (query['address'] != address, 'OutsideVerifiedScope', 'WrongShadowAddress'),
        (query['mappingEstablished'] is False, 'OutsideVerifiedScope', 'UnsupportedShadowMapping'),
        (query['mappingEstablished'] is None, 'IndeterminateObligation', 'ShadowMappingUnestablished'),
        (source is not None and source not in writers, 'OutsideVerifiedScope', 'UnreviewedShadowWriter'),
        (None in (gen, low['generation'], high['generation']), 'IndeterminateObligation', 'ShadowGenerationMissing'),
        (low['generation'] != gen or high['generation'] != gen, 'OutsideVerifiedScope', 'StaleShadowGeneration'),
        (_reused_generation(events, gen), 'OutsideVerifiedScope', 'ShadowGenerationReused'),
        (any({address, address + 1}.intersection(_event_addresses(e)) for e in events),
         'IndeterminateObligation', 'OverlappingShadowWriter'),
        (query['noInterference'] is not True or any(e['address'] is None for e in events),
         'IndeterminateObligation', 'ShadowInterferenceUnresolved'),
        (source_value is not None and any(source_value // 2 ** int(i) % 2 != b for i, b in knowledge.items()),
         'OutsideVerifiedScope', 'ReviewedShadowValueMismatch'),
        (source is not None and word is None, 'IndeterminateObligation', 'ReviewedShadowValueUnbound'),
    )
    status, reason = _qualified_rejections(
        checks, 'ReviewedShadowWriterRetained' if source is not None else 'QualifiedSymbolicShadowWord')
    if status == 'CompleteConditional':
        zero = 0 if 1 in knowledge.values() else 1 if word == 0 else None
        state.update(word=word, knownBits=knowledge, zf=zero, generation=gen)
    return status, reason, state


def data00fa_shadow_lineage(query):
    status, reason, state = _shadow(query, 0xFA)
    unresolved = ['NativeShadowGenerationUnestablished', 'ConfigurationReaderToSuffixContinuityUnestablished']
    if status != 'CompleteConditional':
        unresolved.append(reason)
    return _result(
        (0x2566, 0x256B, 0x3F18, 0x3F2C, 0x3FF7, 0x54DD, 0x5CB7), status,
        state=state, stop='STOP_BEFORE_INDEXED_CONTINUATION_5CB7', generations={'shadow': state['generation']},
        obligations=('ExactLittleEndianShadowPair', 'CurrentGenerationAndNoInterference',
                     'SharedSlotOnlyWithConfigurationReader'),
        unresolved=unresolved, reason=reason,
    )


SNAPSHOT_FIELDS = (
    'memory', 'knownBits', 'registers', 'generations', 'registerKnownBits',
    'configurationIntents', 'sfrReadbacks',
)
IE_PREMISES = ('mcuApplicability', 'ieOwner', 'physicalSf', 'mieState',
               'pendingGenerations', 'frameAndNesting')
IE_CONSTRAINT = 'IeHardwareEffectUnestablished'
SUFFIX_CONTEXT = 'SuffixSnapshotMappingOrContinuityUnestablished'


def _initial(snapshot):
    return {name: deepcopy(snapshot[name]) for name in SNAPSHOT_FIELDS}


def _mapped(snapshot):
    assumptions = snapshot['assumptions']
    return assumptions['dataMapping'] == 'ConditionalByteArray' and assumptions['noInterference'] is True


def _read(pc, address, width, value, known, generation, kind):
    return {'pc': pc, 'address': address, 'widthBits': width, 'value': value,
            'knownBits': known, 'generation': generation, 'kind': kind}


def _source_word(state, query, address, pc, input_class):
    status, reason, word = _shadow(query, address)
    if status != 'CompleteConditional':
        return status, reason, None
    if (query['inputClass'] != input_class or query['low'] != _datum(state, address)
            or query['high'] != _datum(state, address + 1)):
        return 'OutsideVerifiedScope', 'SnapshotShadowBindingMismatch', None
    knowledge = word['knownBits']
    for index, register in enumerate(('al', 'ah')):
        byte = {str(int(bit) - 8 * index): digit for bit, digit in knowledge.items()
                if int(bit) // 8 == index}
        value = sum(2 ** int(bit) * digit for bit, digit in byte.items()) if len(byte) == 8 else None
        _put_register(state, register, value, byte)
    state['registers'].update(dd=1, zf=word['zf'])
    return status, 'QualifiedShadowWordLoaded', _read(
        pc, address, 16, word['word'], knowledge, word['generation'], 'DataWord')


def indexed_suffix_pre_ie(query):
    snapshot = query['snapshot']
    state = _initial(snapshot)
    read = None
    if _mapped(snapshot):
        status, reason, read = _source_word(state, query['shadow'], 0xFA, 0x5CB7, query['inputClass'])
    else:
        status, reason = 'IndeterminateObligation', SUFFIX_CONTEXT
    return _result(
        (0x5CB7, 0x5CB9), status, state=state,
        stop='STOP_BEFORE_INDEXED_CONTINUATION_5CB7' if read is None else 'STOP_BEFORE_IE_WRITE_5CB9',
        reads=[] if read is None else [read], generations=state['generations'],
        states=[] if read is None else [{'pc': 0x5CB7, 'state': state}],
        unresolved=[reason if read is None else IE_CONSTRAINT], reason=reason, ieIntent=None,
    )


def _accumulator_bits(state):
    all_bits = {}
    for index, register in enumerate(('al', 'ah')):
        value = state['registers'][register]
        bits = ({key[-1]: bit for key, bit in state['registerKnownBits'].items()
                 if key.startswith(register.upper() + '.')} if value is None else _bits(value, 8))
        all_bits.update({str(8 * index + int(bit)): digit for bit, digit in bits.items()})
    return all_bits


def _pack(bits, width):
    return sum(2 ** int(bit) * value for bit, value in bits.items()) if len(bits) == width else None


def _intent(state, pc):
    bits = _accumulator_bits(state)
    return {'pc': pc, 'address': 0x1A, 'widthBits': 16, 'source': 'A',
            'value': _pack(bits, 16), 'knownBits': bits,
            'effectClass': 'SoftwareIntent', 'actualPeripheralWrite': None}


def ie5cb9_boundary_obligations(query):
    state = _initial(query['snapshot'])
    dd = state['registers']['dd']
    status, reason = _qualified_rejections((
        (query['attempt'] == 'ActualIeWrite', 'OutsideVerifiedScope', 'ActualIeWriteForbidden'),
        (query['attempt'] == 'ActualIrqDelivery', 'OutsideVerifiedScope', 'ActualIrqDeliveryForbidden'),
        (query['polarity'] != 'Unresolved', 'OutsideVerifiedScope', 'IePolarityConflictUnresolved'),
        (query['descriptor'] != {'address': 0x1A, 'width': 16, 'source': 'A'},
         'OutsideVerifiedScope', 'IeDescriptorMismatch'),
        (dd != 1, 'IndeterminateObligation' if dd is None else 'OutsideVerifiedScope', 'WordStoreDdRequired'),
    ), 'IeSoftwareIntentOnly')
    prospective = status == 'CompleteConditional'
    missing = [premise for premise in IE_PREMISES if query['hardwarePremises'][premise] is not True]
    unresolved = [*missing, 'IePolarityConflict', IE_CONSTRAINT] if prospective else [reason]
    return _result(
        (0x5CB9,), 'IndeterminateObligation' if prospective else status, state=state,
        stop='STOP_BEFORE_IE_WRITE_5CB9', generations=state['generations'],
        obligations=(*IE_PREMISES, 'IePolarityConflict'), unresolved=unresolved, reason=reason,
        ieIntent=_intent(state, 0x5CB9) if prospective else None,
    )


POST_SCOPE = (0x5CBB, 0x5CBE, 0x5CC2, 0x5CC6, 0x5CC9, 0x5CCB, 0x5CCD)
POST_OBLIGATIONS = (
    'IndependentPostIeEntry', 'P2SelectedReadSourceAndOutputDataOwner',
    'Tm2CounterGenerationAndReadApplicability', 'Page0200Mapping', 'SecondIeSoftwareBoundaryOnly',
)
POST_CONSTRAINTS = (
    'PhysicalP2OwnershipUnestablished', 'PhysicalTm2OwnershipUnestablished',
    IE_CONSTRAINT, 'RtFrameAndNativeContinuationUnestablished',
)


def _write(pc, address, width, kind, before, value, knowledge, prior=None, generation=None):
    return {'pc': pc, 'address': address, 'widthBits': width, 'kind': kind, 'before': before,
            'value': value, 'knownBits': knowledge, 'priorGeneration': prior, 'generation': generation,
            'sameValue': None if None in (before, value) else before == value, 'actualHardwareObservation': None}


def _pswh(registers):
    bits = {str(position): registers[key] for position, key in
            ((0, 'mie'), (4, 'dd'), (5, 'hc'), (6, 'zf'), (7, 'cf')) if registers[key] is not None}
    other = registers['otherPsw']
    if other is not None:
        for position in (1, 2, 3):
            bits[str(position)] = other // 2 ** (position + 8) % 2
    return bits


def _mask_pswh(registers, pc, mie):
    before = _pswh(registers)
    raw_before = _pack(before, 8)
    registers.update(mie=mie, cf=None, zf=None, hc=None)
    after = _pswh(registers)
    return (
        _read(pc, 5, 8, raw_before, before, None, 'ArchitectureRegister'),
        _write(pc, 5, 8, 'PswhMask', raw_before, _pack(after, 8), after),
    )


def _operand(op, address, width, name):
    if op is None:
        return 'IndeterminateObligation', f'{name}SymbolicOperandUnestablished'
    if (op['address'], op['widthBits'], op['evidenceClass']) != (address, width, 'SuppliedSymbolic'):
        return 'OutsideVerifiedScope', f'{name}OperandDescriptorMismatch'
    if op['generation'] is None:
        return 'IndeterminateObligation', f'{name}SymbolicOperandUnestablished'
    return 'CompleteConditional', None


def _add_p2(registers, op):
    knowledge = _knowledge(op)
    operands = _domain(op['value'], knowledge)
    sums = tuple(value + 32 for value in operands)
    lows = tuple(total % 256 for total in sums)
    after_bits = _common(lows, 8)
    registers.update(cf=_scalar(total // 256 for total in sums),
                     zf=_scalar(int(low == 0) for low in lows),
                     hc=_scalar((value % 16 + 32 % 16) // 16 for value in operands))
    return (
        _read(0x5CBE, 0x24, 8, op['value'], knowledge, op['generation'], 'SuppliedSymbolicOperand'),
        _write(0x5CBE, 0x24, 8, 'P2WriteIntent', op['value'], _pack(after_bits, 8), after_bits, op['generation']),
    )


def _store_tm2(state, op):
    pc, address = 0x5CC2, 0x025A
    knowledge = _knowledge(op, 16)
    slots = state['offPage']
    old_slots = tuple(slots[key] for key in ('025A', '025B'))
    old_bytes = [slot['value'] for slot in old_slots]
    prior = [slot['generation'] for slot in old_slots]
    before = None if None in old_bytes else old_bytes[0] + 256 * old_bytes[1]
    occupied = set(state['generations'].values()).union(prior, (op['generation'],))
    ordinal = 1
    while f'M2cx.5CC2.{ordinal}' in occupied:
        ordinal += 1
    generation = f'M2cx.5CC2.{ordinal}'
    for index, key in enumerate(('025A', '025B')):
        bits = {str(int(bit) - index * 8): value for bit, value in knowledge.items() if int(bit) // 8 == index}
        slots[key] = {'value': _pack(bits, 8), 'knownBits': bits, 'generation': generation}
    return (
        _read(pc, 0x38, 16, op['value'], knowledge, op['generation'], 'SuppliedSymbolicOperand'),
        _write(pc, address, 16, 'DataWordStore', before, _pack(knowledge, 16),
               knowledge, prior, [generation, generation]),
    )


def indexed_suffix_post_ie(query):
    snapshot = query['snapshot']
    state = _initial(snapshot)
    state['offPage'] = deepcopy(query['offPage'])
    registers = state['registers']
    reads, writes, stages = [], [], []

    def report(status, reason, stop, intent=None):
        unresolved = list(POST_CONSTRAINTS)
        if status != 'CompleteConditional':
            unresolved.append(reason)
        return _result(
            POST_SCOPE, status, state=state, stop=stop, reads=reads, writes=writes,
            generations=state['generations'], states=stages, obligations=POST_OBLIGATIONS,
            unresolved=unresolved, reason=reason, ieIntent=intent,
        )

    def record_effect(pc, read, write=None):
        reads.append(read)
        if write is not None:
            writes.append(write)
        stages.append({'pc': pc, 'state': deepcopy(state)})

    if query['entry'] != 'HypotheticalPostIe5CBB':
        return report('OutsideVerifiedScope', 'PostIeEntryNotAdmitted', 'STOP_BEFORE_PC_5CBB')
    if not _mapped(snapshot):
        return report('IndeterminateObligation', SUFFIX_CONTEXT, 'STOP_BEFORE_PC_5CBB')
    record_effect(0x5CBB, *_mask_pswh(registers, 0x5CBB, 0))

    p2 = query['p2']
    status, reason = _operand(p2, 0x24, 8, 'P2')
    if reason is not None:
        return report(status, reason, 'STOP_BEFORE_PC_5CBE')
    record_effect(0x5CBE, *_add_p2(registers, p2))

    lrb = registers['lrb']
    if lrb is None:
        return report('IndeterminateObligation', 'OffPageAddressUnestablished', 'STOP_BEFORE_PC_5CC2')
    if lrb // 32 % 256 != 2:
        return report('OutsideVerifiedScope', 'OffPageAddressOutsideVerifiedScope', 'STOP_BEFORE_PC_5CC2')
    tm2 = query['tm2']
    status, reason = _operand(tm2, 0x38, 16, 'Tm2')
    if reason is not None:
        return report(status, reason, 'STOP_BEFORE_PC_5CC2')
    record_effect(0x5CC2, *_store_tm2(state, tm2))
    record_effect(0x5CC6, *_mask_pswh(registers, 0x5CC6, 1))
    status, reason, read = _source_word(state, query['shadow'], 0xF8, 0x5CC9, query['inputClass'])
    if read is None:
        return report(status, reason, 'STOP_BEFORE_PC_5CC9')
    record_effect(0x5CC9, read)
    intent = _intent(state, 0x5CCB)
    if query['secondIeBoundary'] is not True:
        return report('IndeterminateObligation', 'SecondIeBoundaryUnestablished', 'STOP_BEFORE_IE_WRITE_5CCB', intent)
    return report('CompleteConditional', 'ConditionalPostIeEffects', 'STOP_BEFORE_RT_5CCD', intent)


def data03cb_suffix_retention(query):
    writer, selected = query['writerPc'], query['selectedIndex']
    entry, observed = query['entry'], query['observed']
    initial, current = entry['generation'], observed['generation']
    requested, page, events = query['requestedGeneration'], query['page'], query['events']
    competing = None
    for event in events:
        footprint = _event_addresses(event)
        if 0x03CB not in footprint:
            continue
        byte = None if event['value'] is None else event['value'] // (256 ** footprint.index(0x03CB)) % 256
        before = entry['value']
        competing = {'kind': event['kind'], 'address': footprint[0], 'widthBits': event['widthBits'],
                     'generation': event['generation'], 'value': byte,
                     'sameValue': None if None in (before, byte) else before == byte}
        break
    entry_bits, observed_bits = _knowledge(entry), _knowledge(observed)
    conflict = any(bit in observed_bits and observed_bits[bit] != value for bit, value in entry_bits.items())
    status, reason = _qualified_rejections((
        (query['claim'] != 'ConditionalOnly', 'OutsideVerifiedScope', 'NonConditionalRetentionClaim'),
        (writer is not None and writer != 0x5CB4, 'OutsideVerifiedScope', 'UnreviewedIndexedWriter'),
        (selected is not None and selected != 5, 'OutsideVerifiedScope', 'IndexDoesNotWriteData03cb'),
        (page is not None and page % 256 != 0, 'OutsideVerifiedScope', 'InvalidDataPage'),
        (writer is None or selected is None, 'IndeterminateObligation', 'IndexedWriterUnestablished'),
        (None in (initial, current, requested), 'IndeterminateObligation', 'Data03cbGenerationMissing'),
        (requested != initial, 'OutsideVerifiedScope', 'StaleData03cbGeneration'),
        (_reused_generation(events, initial), 'OutsideVerifiedScope', 'Data03cbGenerationReused'),
        (competing is not None, 'IndeterminateObligation', 'CompetingData03cbWriter'),
        (query['noInterference'] is not True or any(e['address'] is None for e in events),
         'IndeterminateObligation', 'Data03cbInterferenceUnresolved'),
        (current != initial, 'IndeterminateObligation', 'Data03cbGenerationChanged'),
        (conflict, 'OutsideVerifiedScope', 'Data03cbValueGenerationConflict'),
    ), 'ConditionalData03cbGenerationRetained')
    retained = initial if status == 'CompleteConditional' else None
    state = {
        'localSuffixRetention': True,
        'offPageWrite': {'address': None if page is None or page % 256 else page + 0x5A, 'widthBits': 16},
        'entryGeneration': initial, 'observedGeneration': current, 'retainedGeneration': retained,
        'nativeReachingDefinition': None,
    }
    unresolved = ['NativeData03cbOwnerUnestablished', 'CallerToModeContinuityUnestablished']
    if retained is None:
        unresolved.append(reason)
    return _result(
        (0x5CB4, 0x5CB7, 0x5CB9, 0x5CBB, 0x5CBE, 0x5CC2, 0x5CC6, 0x5CC9, 0x5CCB, 0x5CCD),
        status, state=state, stop='STOP_BEFORE_RT_5CCD', generations={'data03cb': retained},
        obligations=('IndexedWriterAt5CB4Index5', 'LocalSuffixWritesDisjointFromData03cb',
                     'ExcludeCompetingAndAsynchronousWrites'),
        unresolved=unresolved, reason=reason, competingWrite=competing,
    )


def indexed_return_obligations(query):
    frame_query = query['frameQuery']
    caller = frame_query['callerPc']
    reviewed_caller = caller in (0x276A, 0x2B64)
    child = accepted_frame(frame_query) if reviewed_caller else None
    expected, generation = query['expectedFrameGeneration'], frame_query['frame']['generation']
    assumptions = query['additionalPremises']
    missing = [name for name in ('noInterveningFrameWrites', 'noSuffixFrameAlias')
               if assumptions[name] is not True]
    if child is None:
        status, reason = 'OutsideVerifiedScope', 'UnreviewedIndexedCaller'
    elif child['status'] != 'CompleteConditional':
        status, reason = child['status'], child['reason']
    else:
        address = child['state']['geometry']['frameAddress']
        status, reason = _qualified_rejections((
            (query['postIeBoundary'] != 0x5CCD,
             'IndeterminateObligation', 'HypotheticalPreRtBoundaryNotEstablished'),
            (address in (0xF8, 0xFA, 0x25A), 'OutsideVerifiedScope', 'IndexedSuffixFrameAlias'),
            (expected is None, 'IndeterminateObligation', 'ExpectedFrameGenerationUnknown'),
            (expected != generation, 'OutsideVerifiedScope', 'StaleFrameGeneration'),
            (bool(missing), 'IndeterminateObligation', 'IndexedFramePremisesNotEstablished'),
        ), 'MatchingHypotheticalIndexedFrame')
    candidate = caller + 3 if reviewed_caller else None
    complete = status == 'CompleteConditional'
    state = {'callerPc': caller, 'candidateReturnPc': candidate,
             'formalReturnedPc': candidate if complete else None,
             'nativeFrameOwnerEstablished': False, 'nativeReturnEstablished': False}
    unresolved = ['ActualNativeFrameOwnershipUnestablished'] if complete else (
        missing if reason == 'IndexedFramePremisesNotEstablished' else [reason])
    return _result(
        (0x276A, 0x2B64, 0x5C86, 0x5CCD), status, evidence='StaticFormalSourceObligation',
        state=state, stop='STOP_BEFORE_RT_5CCD', generations={'expectedFrame': expected, 'suppliedFrame': generation},
        obligations=() if child is None else child['frameObligations'], unresolved=unresolved,
        reason=reason, frozenFrameResult=child,
    )


def indexed_suffix_composition(query):
    prefix_query = query['prefixQuery']
    prefix = accepted_indexed(prefix_query)
    appended = prefix['status'] == 'CompleteConditional' and prefix['boundary'] == 0x5CB7
    suffix = None
    if appended:
        snapshot = deepcopy(prefix['state'])
        snapshot['inputClass'] = prefix_query['inputClass']
        snapshot['assumptions'] = prefix_query['snapshot']['assumptions']
        suffix = indexed_suffix_pre_ie({'inputClass': query['inputClass'], 'snapshot': snapshot,
                                        'shadow': query['shadow']})
    branches = [{'pc': item['pc'], 'taken': item['branchTaken'], 'next': item['next']}
                for item in prefix['steps'] if item['kind'] == 'Branch']
    if suffix is None:
        stop, generations = prefix['exactStopBoundary'], prefix['state']['generations']
        last, reads, writes, states, obligations = (
            prefix, prefix['reads'], prefix['journal'], prefix['intermediateStates'], ())
    else:
        stop, generations = suffix['stopBoundary'], suffix['generations']
        last, reads, writes, states, obligations = (
            suffix, (*prefix['reads'], *suffix['reads']), (*prefix['journal'], *suffix['orderedWrites']),
            (*prefix['intermediateStates'], *suffix['intermediateStates']), suffix['formalObligations'])
    return _result(
        sorted({*prefix['sourceScope'], 0x5CB7, 0x5CB9}), last['status'], state=last['state'], stop=stop,
        reads=reads, writes=writes, generations=generations, states=states, obligations=obligations,
        unresolved=last['unresolvedConstraints'], branches=branches, reason=last['reason'],
        frozenPrefixResult=prefix, preIeResult=suffix, postIeComposed=False,
    )


OPERATIONS = {operation.__name__: operation for operation in (
    indexed_suffix_pre_ie, data00fa_shadow_lineage, ie5cb9_boundary_obligations,
    indexed_suffix_post_ie, indexed_suffix_composition, data03cb_suffix_retention,
    indexed_return_obligations,
)}


def record(case):
    operation = case['operation']
    output = OPERATIONS[operation](case['input'])
    projection = {field: output[field] for field in OUTPUT_FIELDS}
    return deepcopy({
        'caseId': case['id'], 'operation': operation, 'input': case['input'], 'output': output,
        **projection, 'executionAuthority': {key: output[key] for key in AUTHORITY},
    })
