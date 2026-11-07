"""Selected software effects around two unapplied IE store frontiers."""
from copy import deepcopy

from enclosing_caller_return import state as accepted

from .provenance import shadow_word
from .wire import result


PRE_SCOPE = (0x5CB7, 0x5CB9)
IE_SCOPE = (0x5CB9,)
POST_SCOPE = (0x5CBB, 0x5CBE, 0x5CC2, 0x5CC6, 0x5CC9, 0x5CCB, 0x5CCD)
IE_FIELDS = ('mcuApplicability', 'ieOwner', 'physicalSf', 'mieState', 'pendingGenerations', 'frameAndNesting')
IE_GAP = 'IeHardwareEffectUnestablished'
POST_GAPS = ('PhysicalP2OwnershipUnestablished', 'PhysicalTm2OwnershipUnestablished', IE_GAP,
             'RtFrameAndNativeContinuationUnestablished')
POST_OBLIGATIONS = ('IndependentPostIeEntry', 'P2SelectedReadSourceAndOutputDataOwner',
                    'Tm2CounterGenerationAndReadApplicability', 'Page0200Mapping', 'SecondIeSoftwareBoundaryOnly')
PSWH_BITS = {'mie': 0, 'dd': 4, 'hc': 5, 'zf': 6, 'cf': 7}
FRONTIERS = {0x5CB9: 'STOP_BEFORE_IE_WRITE_5CB9', 0x5CCB: 'STOP_BEFORE_IE_WRITE_5CCB'}


def _state(query, fields, reason):
    accepted.shape(query, ('inputClass', 'snapshot', *fields), reason)
    snapshot = query['snapshot']
    accepted.validate(snapshot)
    accepted.input_class(query['inputClass'])
    accepted.need(query['inputClass'] == snapshot['inputClass'], 'SuffixSnapshotInputClassMismatch')
    return {name: deepcopy(snapshot[name]) for name in accepted.STATE_FIELDS}


def _snapshot_qualified(query):
    assumptions = query['snapshot']['assumptions']
    return assumptions['dataMapping'] == 'ConditionalByteArray' and assumptions['noInterference'] is True


def _declared_shadow(query, address):
    if not _snapshot_qualified(query):
        return 'IndeterminateObligation', 'SuffixSnapshotMappingOrContinuityUnestablished', None
    shadow = query['shadow']
    status, reason, word = shadow_word(shadow, address)
    if status != 'CompleteConditional':
        return status, reason, None
    if query['inputClass'] != shadow['inputClass']:
        return 'OutsideVerifiedScope', 'SnapshotShadowBindingMismatch', None
    snapshot = query['snapshot']
    for offset, part in enumerate(('low', 'high')):
        key = f'{address + offset:04X}'
        prefix = f'{key}.'
        slot = {'value': snapshot['memory'][key], 'generation': snapshot['generations'][key],
                'knownBits': {k[-1]: v for k, v in snapshot['knownBits'].items() if k.startswith(prefix)}}
        if slot != shadow[part]:
            return 'OutsideVerifiedScope', 'SnapshotShadowBindingMismatch', None
    return status, reason, word


def _pack(bits, width):
    return sum(value << int(bit) for bit, value in bits.items()) if len(bits) == width else None


def _bits(value, known_bits, width):
    return dict(known_bits) if value is None else {str(i): (value >> i) & 1 for i in range(width)}


def _read(pc, address, width, value, bits, generation, kind):
    return {'pc': pc, 'address': address, 'widthBits': width, 'value': value, 'knownBits': bits,
            'generation': generation, 'kind': kind}


def _event(pc, address, width, kind, before, value, bits, prior_gen=None, generation=None):
    same = None if before is None or value is None else before == value
    return {'pc': pc, 'address': address, 'widthBits': width, 'kind': kind, 'before': before,
            'value': value, 'knownBits': bits, 'priorGeneration': prior_gen, 'generation': generation,
            'sameValue': same, 'actualHardwareObservation': None}


def _step(pc, state):
    return {'pc': pc, 'state': deepcopy(state)}


def _load(pc, word, state):
    bits = word['knownBits']
    regs, known = state['registers'], state['registerKnownBits']
    for offset, name in enumerate(('AL', 'AH')):
        byte = {str(i): bits[str(8 * offset + i)] for i in range(8) if str(8 * offset + i) in bits}
        for i in range(8):
            known.pop(f'{name}.{i}', None)
        known.update({f'{name}.{i}': value for i, value in byte.items()})
        regs[name.lower()] = _pack(byte, 8)
    regs.update(dd=1, zf=word['zf'])
    return _read(pc, word['address'], 16, word['word'], bits, word['generation'], 'DataWord')


def _result(status, reason, scope, state, pc, *, reads=(), writes=(), intermediate=(),
            obligations=(), unresolved=(), intent=None):
    return result(status, source_scope=scope, state=state, stop=FRONTIERS.get(pc, accepted.stop_name(pc)),
                  reads=reads, writes=writes, intermediate=intermediate, obligations=obligations,
                  unresolved=unresolved, generations=state['generations'], reason=reason, ieIntent=intent)


def indexed_suffix_pre_ie(query):
    """Apply the zero-page word load at 5CB7 to an exactly bound snapshot."""
    state = _state(query, ('shadow',), 'ClosedIndexedPreIeQueryRequired')
    status, reason, word = _declared_shadow(query, 0x00FA)
    if word is None:
        return _result(status, reason, PRE_SCOPE, state, 0x5CB7, unresolved=(reason,))
    read = _load(0x5CB7, word, state)
    return _result(status, 'QualifiedShadowWordLoaded', PRE_SCOPE, state, 0x5CB9, reads=(read,),
                   intermediate=(_step(0x5CB7, state),), unresolved=(IE_GAP,))


def _ie_intent(pc, state):
    regs, known = state['registers'], state['registerKnownBits']
    bits = {}
    for offset, name in enumerate(('AL', 'AH')):
        byte_bits = {k[-1]: v for k, v in known.items() if k.startswith(f'{name}.')}
        bits.update({str(8 * offset + int(bit)): v
                     for bit, v in _bits(regs[name.lower()], byte_bits, 8).items()})
    return {'pc': pc, 'address': 0x001A, 'widthBits': 16, 'source': 'A', 'value': _pack(bits, 16),
            'knownBits': bits, 'effectClass': 'SoftwareIntent', 'actualPeripheralWrite': None}


def _ie_refusal(query, state):
    if query['attempt'] != 'Intent':
        return 'OutsideVerifiedScope', query['attempt'] + 'Forbidden'
    if query['polarity'] != 'Unresolved':
        return 'OutsideVerifiedScope', 'IePolarityConflictUnresolved'
    if query['descriptor'] != {'address': 0x001A, 'width': 16, 'source': 'A'}:
        return 'OutsideVerifiedScope', 'IeDescriptorMismatch'
    dd = state['registers']['dd']
    if dd != 1:
        return ('IndeterminateObligation' if dd is None else 'OutsideVerifiedScope'), 'WordStoreDdRequired'
    return None


def ie5cb9_boundary_obligations(query):
    """Describe the prospective word store without mutating the IE register."""
    state = _state(query, ('descriptor', 'attempt', 'polarity', 'hardwarePremises'), 'ClosedIeBoundaryQueryRequired')
    premises, descriptor = query['hardwarePremises'], query['descriptor']
    accepted.shape(premises, IE_FIELDS, 'ClosedIeHardwarePremisesRequired')
    accepted.shape(descriptor, ('address', 'width', 'source'), 'ClosedIeDescriptorRequired')
    accepted.need(all(accepted.tri(value) for value in premises.values()), 'TypedIeHardwarePremisesRequired')
    accepted.need(type(descriptor['address']) is int and 0 <= descriptor['address'] <= 0xFFFF
                  and type(descriptor['width']) is int and descriptor['width'] in (8, 16)
                  and type(descriptor['source']) is str, 'TypedIeDescriptorRequired')
    accepted.need(type(query['attempt']) is str and query['attempt'] in ('Intent', 'ActualIeWrite', 'ActualIrqDelivery')
                  and type(query['polarity']) is str and query['polarity'] in ('Unresolved', 'Set1', 'Set0'),
                  'TypedIeBoundaryRequestRequired')
    obligations = (*IE_FIELDS, 'IePolarityConflict')
    refusal = _ie_refusal(query, state)
    if refusal is not None:
        status, reason = refusal
        return _result(status, reason, IE_SCOPE, state, 0x5CB9, obligations=obligations, unresolved=(reason,))
    unresolved = (*(field for field in IE_FIELDS if premises[field] is not True), 'IePolarityConflict', IE_GAP)
    return _result('IndeterminateObligation', 'IeSoftwareIntentOnly', IE_SCOPE, state, 0x5CB9,
                   obligations=obligations, unresolved=unresolved, intent=_ie_intent(0x5CB9, state))


def _pswh(state):
    regs = state['registers']
    bits = {str(bit): regs[name] for name, bit in PSWH_BITS.items() if regs[name] is not None}
    if regs['otherPsw'] is not None:
        bits.update({str(bit): (regs['otherPsw'] >> (8 + bit)) & 1 for bit in (1, 2, 3)})
    return _pack(bits, 8), bits


def _mask_pswh(pc, mie, state, reads, writes):
    before, bits = _pswh(state)
    reads.append(_read(pc, 0x0005, 8, before, bits, None, 'ArchitectureRegister'))
    state['registers'].update(mie=mie, cf=None, zf=None, hc=None)
    after, bits = _pswh(state)
    writes.append(_event(pc, 0x0005, 8, 'PswhMask', before, after, bits))


def _operand(value, address, width, name):
    if value is None:
        return 'IndeterminateObligation', name + 'SymbolicOperandUnestablished'
    accepted.shape(value, ('address', 'widthBits', 'value', 'knownBits', 'generation', 'evidenceClass'),
                   'ClosedSuffixOperandRequired')
    accepted.need(type(value['address']) is int and 0 <= value['address'] <= 0xFFFF
                  and type(value['widthBits']) is int and value['widthBits'] in (8, 16)
                  and type(value['evidenceClass']) is str and accepted.label(value['generation']),
                  'TypedSuffixOperandRequired')
    if (value['address'], value['widthBits'], value['evidenceClass']) != (address, width, 'SuppliedSymbolic'):
        return 'OutsideVerifiedScope', name + 'OperandDescriptorMismatch'
    bits, raw = value['knownBits'], value['value']
    accepted.need(accepted.number(raw, (1 << width) - 1) and type(bits) is dict
                  and set(bits) <= {str(i) for i in range(width)}
                  and all(type(v) is int and v in (0, 1) for v in bits.values()), 'TypedSuffixOperandKnowledgeRequired')
    accepted.need(raw is None or all((raw >> int(bit)) & 1 == v for bit, v in bits.items()),
                  'ContradictorySuffixOperandBits')
    if value['generation'] is None:
        return 'IndeterminateObligation', name + 'SymbolicOperandUnestablished'
    return None


def _domain_consensus(values, width):
    all_ones = (1 << width) - 1
    any_ones = 0
    for value in values:
        all_ones &= value
        any_ones |= value
    return {str(i): (all_ones >> i) & 1 for i in range(width) if (all_ones ^ any_ones) >> i & 1 == 0}


def _add_p2(state, operand, reads, writes):
    raw, generation = operand['value'], operand['generation']
    bits = _bits(raw, operand['knownBits'], 8)
    read = _read(0x5CBE, 0x0024, 8, raw, bits, generation, 'SuppliedSymbolicOperand')
    reads.append(read)
    sums = [value + 0x20 for value in range(256) if all((value >> int(bit)) & 1 == b for bit, b in bits.items())]
    byte_sums = {value & 255 for value in sums}
    after = _domain_consensus(byte_sums, 8)
    state['registers'].update(cf=_pack(_domain_consensus({value >> 8 for value in sums}, 1), 1),
                              zf=_pack(_domain_consensus({int(value == 0) for value in byte_sums}, 1), 1), hc=0)
    writes.append(_event(0x5CBE, 0x0024, 8, 'P2WriteIntent', raw, _pack(after, 8), after, generation))


def _move_tm2(state, operand, reads, writes):
    raw, generation = operand['value'], operand['generation']
    bits = _bits(raw, operand['knownBits'], 16)
    reads.append(_read(0x5CC2, 0x0038, 16, raw, bits, generation, 'SuppliedSymbolicOperand'))
    slots = state['offPage']
    before_bytes = [slots[key]['value'] for key in ('025A', '025B')]
    before = None if None in before_bytes else before_bytes[0] | before_bytes[1] << 8
    prior = [slots[key]['generation'] for key in ('025A', '025B')]
    occupied = {*prior, *state['generations'].values(), generation}
    next_gen = next(f'M2cx.5CC2.{i}' for i in range(1, len(occupied) + 2)
                    if f'M2cx.5CC2.{i}' not in occupied)
    for offset, key in enumerate(('025A', '025B')):
        byte = {str(i): bits[str(8 * offset + i)] for i in range(8) if str(8 * offset + i) in bits}
        slots[key] = {'value': _pack(byte, 8), 'knownBits': byte, 'generation': next_gen}
    writes.append(_event(0x5CC2, 0x025A, 16, 'DataWordStore', before, _pack(bits, 16), bits, prior,
                         [next_gen, next_gen]))


def indexed_suffix_post_ie(query):
    """Evaluate a disconnected source projection from the declared 5CBB boundary."""
    state = _state(query, ('entry', 'p2', 'tm2', 'shadow', 'offPage', 'secondIeBoundary'),
                   'ClosedIndexedPostIeQueryRequired')
    accepted.need(type(query['entry']) is str and accepted.tri(query['secondIeBoundary']), 'TypedPostIePremisesRequired')
    accepted.shape(query['offPage'], ('025A', '025B'), 'ClosedOffPageWordRequired')
    for slot in query['offPage'].values():
        accepted.slot(slot)
    state['offPage'] = deepcopy(query['offPage'])
    reads, writes, intermediate = [], [], []

    def finish(status, reason, pc, intent=None):
        gaps = POST_GAPS if status == 'CompleteConditional' else (*POST_GAPS, reason)
        return _result(status, reason, POST_SCOPE, state, pc, reads=reads, writes=writes,
                       intermediate=intermediate, obligations=POST_OBLIGATIONS, unresolved=gaps, intent=intent)

    if query['entry'] != 'HypotheticalPostIe5CBB':
        return finish('OutsideVerifiedScope', 'PostIeEntryNotAdmitted', 0x5CBB)
    if not _snapshot_qualified(query):
        return finish('IndeterminateObligation', 'SuffixSnapshotMappingOrContinuityUnestablished', 0x5CBB)
    _mask_pswh(0x5CBB, 0, state, reads, writes)
    intermediate.append(_step(0x5CBB, state))

    refusal = _operand(query['p2'], 0x0024, 8, 'P2')
    if refusal is not None:
        return finish(*refusal, 0x5CBE)
    _add_p2(state, query['p2'], reads, writes)
    intermediate.append(_step(0x5CBE, state))

    lrb = state['registers']['lrb']
    if lrb is None:
        return finish('IndeterminateObligation', 'OffPageAddressUnestablished', 0x5CC2)
    if (lrb & 0x1FE0) << 3 != 0x0200:
        return finish('OutsideVerifiedScope', 'OffPageAddressOutsideVerifiedScope', 0x5CC2)
    refusal = _operand(query['tm2'], 0x0038, 16, 'Tm2')
    if refusal is not None:
        return finish(*refusal, 0x5CC2)
    _move_tm2(state, query['tm2'], reads, writes)
    intermediate.append(_step(0x5CC2, state))

    _mask_pswh(0x5CC6, 1, state, reads, writes)
    intermediate.append(_step(0x5CC6, state))
    status, reason, word = _declared_shadow(query, 0x00F8)
    if word is None:
        return finish(status, reason, 0x5CC9)
    reads.append(_load(0x5CC9, word, state))
    intermediate.append(_step(0x5CC9, state))

    intent = _ie_intent(0x5CCB, state)
    if query['secondIeBoundary'] is not True:
        return finish('IndeterminateObligation', 'SecondIeBoundaryUnestablished', 0x5CCB, intent)
    return finish('CompleteConditional', 'ConditionalPostIeEffects', 0x5CCD, intent)
