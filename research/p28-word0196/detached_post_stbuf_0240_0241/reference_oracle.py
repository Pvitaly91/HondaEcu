"""Expected M2dg records from the reviewed ISA and frozen M2df reference."""
from copy import deepcopy
from itertools import product

from alternate_parser_response_checksum.analysis import AUTHORITY, canonical
from alternate_parser_response_checksum.corpus import composition_cases
from alternate_parser_response_checksum.reference_oracle import expected as m2df_reference


_ENTRY = 0x0240
_EPILOGUE = 0x0244
_EPILOGUE_BOUNDARY = 'STOP_BEFORE_EPILOGUE_0244'
_STBUF_BOUNDARY = 'STOP_BEFORE_STBUF_023E'
_REG_WIDTHS = dict(al=8, ah=8, cf=1, zf=1, hc=1, dd=1, mie=1,
                   otherPsw=16, lrb=16, scb=3, usp=16, ssp=16)
_FRAGMENT_OBLIGATIONS = ('UnprovedNativeHandoff', 'ActualStbufAcceptanceUnknown',
                         'PhysicalDataMappingUnknown', 'TxProgressionUnknown',
                         'EpilogueEffectsOutsideScope')
_PROJECTION_OBLIGATIONS = ('StbufAcceptanceAndTransmissionUnestablished',
                           'NativePostStbufPcUnestablished', 'ActualPeripheralMappingUnestablished')
_INGRESS_OBLIGATIONS = ('DifferentSourceIngressProvenance', 'EpilogueEffectsOutsideScope',
                        'NativePostStbufPcUnestablished')


def _exact_keys(value, *keys):
    return type(value) is dict and value.keys() == set(keys)


def _unsigned(value, width):
    return value is None or type(value) is int and 0 <= value < 2 ** width


def _hex_address(value):
    return type(value) is str and len(value) == 4 and all(ch in '0123456789ABCDEF' for ch in value)


def _tag(value):
    return value is None or type(value) is str and 1 <= len(value) <= 256


def _bit(value, position):
    return value // 2 ** int(position) % 2


def _bit_matches(value, position, bit):
    return type(bit) is int and bit in (0, 1) and (value is None or _bit(value, position) == bit)


def _typed_state(state):
    if not _exact_keys(state, 'registers', 'memory', 'generations', 'knownBits',
                       'registerGenerations', 'registerKnownBits'):
        return False
    if any(type(fields) is not dict for fields in state.values()):
        return False
    registers, data = state['registers'], state['memory']
    if any(key not in _REG_WIDTHS or not _unsigned(value, _REG_WIDTHS[key]) for key, value in registers.items()):
        return False
    other_psw = registers.get('otherPsw')
    if other_psw is not None and any(_bit(other_psw, p) for p in (0, 1, 2, 8, 12, 13, 14, 15)):
        return False
    if len(data) > 512 or any(not _hex_address(addr) or int(addr, 16) < 8 or not _unsigned(val, 8)
                              for addr, val in data.items()):
        return False
    if data.keys() != state['generations'].keys() or any(not _tag(value) for value in state['generations'].values()):
        return False
    if any(name not in registers or not _tag(value) for name, value in state['registerGenerations'].items()):
        return False
    for location, value in state['knownBits'].items():
        if type(location) is not str or len(location) != 6 or location[4] != '.':
            return False
        address, position = location[:4], location[5]
        if address not in data or position not in '01234567' or not _bit_matches(data[address], position, value):
            return False
    for name, bits in state['registerKnownBits'].items():
        if name not in ('al', 'ah') or name not in registers or type(bits) is not dict:
            return False
        for position, value in bits.items():
            if (type(position) is not str or len(position) != 1 or position not in '01234567'
                    or not _bit_matches(registers[name], position, value)):
                return False
    selected_bank, usp = registers.get('scb'), registers.get('usp')
    if selected_bank is not None and usp is not None:
        high, low = divmod(usp, 256)
        base = 134 + selected_bank * 8
        for address, aliased in ((base, low), (base + 1, high)):
            slot = format(address, '04X')
            recorded = data.get(slot)
            if recorded is not None and recorded != aliased:
                return False
            if any(_bit(aliased, location[-1]) != value for location, value in state['knownBits'].items()
                   if location[:4] == slot):
                return False
    return True


def _admission(query):
    if not _exact_keys(query, 'sourceId', 'entryPc', 'inputClass', 'assumptions', 'state'):
        return 'ClosedDetachedSnapshotRequired'
    if query['sourceId'] != 'M2dgReviewed0240_0241':
        return 'ReviewedSourceIdentityRequired'
    if query['entryPc'] != _ENTRY or type(query['entryPc']) is not int:
        return 'ExactDetachedEntry0240Required'
    if query['inputClass'] not in ('SymbolicInput', 'SyntheticTestInput', 'ManufacturerSourceQualifiedState'):
        return 'SymbolicInputClassRequired'
    assumptions = query['assumptions']
    if (not _exact_keys(assumptions, 'noInterference', 'ordinaryInternalRam')
            or not all(type(value) in (bool, type(None)) for value in assumptions.values())):
        return 'ClosedDetachedPremisesRequired'
    if not _typed_state(query['state']):
        return 'TypedSourceStateRequired'
    if assumptions['noInterference'] is not True:
        return 'NoInterferencePremiseRequired'
    if query['state']['registers'].get('lrb') != 126:
        return 'ExactReviewedLrb007ERequired'
    if assumptions['ordinaryInternalRam'] is not True:
        return 'OrdinaryWritableDataPremiseRequired'
    return None


def _known_consensus(values):
    first, *rest = values
    return first if all(value == first for value in rest) else None


def _concretizations(value, partial):
    if value is not None:
        return [value]
    fixed = sum(2 ** int(position) * bit for position, bit in partial.items())
    free = [2 ** position for position in range(8) if str(position) not in partial]
    return [fixed + sum(included) for included in product(*[(0, weight) for weight in free])]


def _increment(value):
    """Evaluate the bit-level carry path separately from byte modulo addition."""
    carry, output, half = 1, 0, 0
    for position in range(8):
        carry, result_bit = divmod(_bit(value, position) + carry, 2)
        output += result_bit * 2 ** position
        if position == 3:
            half = carry
    return output, {'zf': int(output == 0), 'hc': half}


def _set_status(value):
    old_bit = _bit(value, 6)
    return value + 64 * (1 - old_bit), {'zf': 1 - old_bit}


def _fragment_record(status, reason, pc, state=None, steps=(), reads=(), journal=()):
    return dict(status=status, reason=reason, stopPc=pc,
                stopBoundary=_EPILOGUE_BOUNDARY if pc == _EPILOGUE else None,
                state=state, entryKind='DetachedSymbolicEntry', steps=list(steps), reads=list(reads),
                journal=list(journal), unresolved=list(_FRAGMENT_OBLIGATIONS),
                executionAuthority=dict(AUTHORITY))


def _fragment(snapshot):
    refusal = _admission(snapshot)
    if refusal is not None:
        return _fragment_record('RefusedDetachedEntry', refusal, _ENTRY)
    state = deepcopy(snapshot['state'])
    steps, reads, writes = [], [], []
    for number, (pc, following, slot, function, source, flag_names) in enumerate((
        (0x0240, 0x0241, '03F5', _increment, 'r5+1', ('zf', 'hc')),
        (0x0241, 0x0244, '0356', _set_status, 'DATA0356.Bit6Set', ('zf',)),
    ), 1):
        generation = f'M2dg:DATA:{pc:04X}:{number}'
        flag_tags = {name: f'M2dg:Flag:{pc:04X}:{name.upper()}' for name in flag_names}
        prior = state['generations'].get(slot)
        available_tags = [*state['generations'].values(), *state['registerGenerations'].values()]
        refusal = None
        if slot not in state['memory']:
            refusal = 'RequiredDataSlotMissing'
        elif prior is None:
            refusal = 'RequiredDataGenerationMissing'
        elif any(tag in available_tags for tag in (generation, *flag_tags.values())):
            refusal = 'WriterGenerationCollision'
        if refusal:
            return _fragment_record('OutsideVerifiedScope', refusal, pc, state, steps, reads, writes)

        before = state['memory'][slot]
        prefix = slot + '.'
        partial = {location[-1]: value for location, value in state['knownBits'].items()
                   if location.startswith(prefix)}
        address = int(slot, 16)
        reads.append(dict(pc=pc, space='DATA', address=address, widthBits=8, value=before,
                          knownBits=partial, generation=prior, kind='FunctionalRmwRead'))
        possible_inputs = _concretizations(before, partial)
        transitions = [function(value) for value in possible_inputs]
        after_bytes = [new for new, _ in transitions]
        after = _known_consensus(after_bytes)
        before_flags = {name: state['registers'].get(name) for name in flag_names}
        after_flags = {name: _known_consensus([flags[name] for _, flags in transitions]) for name in flag_names}

        state['memory'][slot], state['generations'][slot] = after, generation
        for key in list(state['knownBits']):
            if key.startswith(prefix):
                del state['knownBits'][key]
        if after is None:
            for position in range(8):
                shared = _known_consensus([_bit(byte, position) for byte in after_bytes])
                if shared is not None:
                    state['knownBits'][prefix + str(position)] = shared
        state['registers'].update(after_flags)
        state['registerGenerations'].update(flag_tags)
        writes.append(dict(ordinal=number, pc=pc, space='DATA', address=address, widthBits=8,
                           before=before, after=after, beforeGeneration=prior, afterGeneration=generation,
                           valueSource=source, kind='RMW',
                           sameValue=_known_consensus([a == b for a, b in zip(possible_inputs, after_bytes, strict=True)]),
                           effectClass='ConditionalSoftwareEffect'))
        steps.append(dict(pc=pc, next=following, edge='ConfirmedStaticCFG', branchPredicate=None,
                          beforeFlags=before_flags, afterFlags=after_flags, state=deepcopy(state)))
    return _fragment_record('ConditionalSourceArrivalAt0244', None, _EPILOGUE, state, steps, reads, writes)


def _prior(source):
    if not _exact_keys(source, 'baseSha', 'sourceFingerprint', 'operation', 'input', 'result'):
        return 'ClosedM2dfSourceEnvelopeRequired', None, None
    op = source['operation']
    if (source['baseSha'] != 'a9eeb45292a120711bb1adf918385675c2456409'
            or source['sourceFingerprint'] != 'a1c554e17305f199effbc2e3aae2b42ab83081da7e527b4eeeab181faf691e55'
            or op not in ('alternate_response_selector', 'alternate_parser_step')):
        return 'ExactM2dfSourceIdentityRequired', None, None
    try:
        if op == 'alternate_response_selector':
            reference = m2df_reference({'operation': op, 'input': source['input']})
            result = reference
            path = 'M2dfAlternate0227'
        else:
            fixture = next(item for item in composition_cases()
                           if canonical(item['input']) == canonical(source['input']))
            reference = m2df_reference(fixture)
            result = reference['alternate']
            path = 'M2dfFrozenStatusPrefixToAlternate0227'
        if canonical(reference) == canonical(source['result']):
            return None, result, path
    except (ValueError, TypeError, KeyError, StopIteration, RecursionError, OverflowError):
        pass
    return 'FrozenM2dfReplayMismatch', None, None


def _arrives(selected, pc, stop):
    if not selected or selected['status'] != 'CompleteConditional':
        return False
    trace = selected['steps']
    return (selected['entryQualification'] == 'DetachedConditionalSourcePath'
            and selected['boundary'] == pc and selected['stopBoundary'] == stop
            and bool(trace) and (trace[0]['pc'], trace[-1]['next']) == (0x0227, pc))


def _evidence(obligations):
    return dict(steps=[], reads=[], journal=[], executionAuthority=dict(AUTHORITY), unresolved=list(obligations))


def _projection(query):
    result = dict(status='RefusedSourcePremise', reason=None, sourcePath=None, projectedInput=None, candidate=None,
                  stopBoundary=None, **_evidence(_PROJECTION_OBLIGATIONS))
    if not _exact_keys(query, 'source', 'assumptions'):
        return {**result, 'reason': 'ClosedProjectionQueryRequired'}
    error, selected, path = _prior(query['source'])
    if error is not None:
        return {**result, 'reason': error}
    result['sourcePath'] = path
    if (not _arrives(selected, 0x023E, _STBUF_BOUNDARY)
            or selected['outcome'] not in ('LengthRegisterResponse', 'ProgramSelectedDataResponse',
                                           'NegatedChecksumResponse')):
        return {**result, 'reason': 'M2dfCandidateBoundaryRequired'}
    result['stopBoundary'] = _STBUF_BOUNDARY
    assumptions = query['assumptions']
    if (not _exact_keys(assumptions, 'cpuProjection', 'noInterference', 'ordinaryInternalRam')
            or not all(value is True for value in assumptions.values())):
        return {**result, 'reason': 'ExplicitProjectionAssumptionsRequired'}
    if selected['state']['registers']['dd'] != 0:
        return {**result, 'reason': 'M2dfByteStorePrerequisiteRequired'}
    projected_class = 'SyntheticTestInput' if selected['inputClass'] == 'SyntheticTestInput' else 'SymbolicInput'
    projected = dict(sourceId='M2dgReviewed0240_0241', entryPc=_ENTRY, inputClass=projected_class,
                     assumptions=dict(noInterference=True, ordinaryInternalRam=True),
                     state=_lift(selected))
    return {**result, 'status': 'ConditionalCpuStateProjection', 'reason': 'ExplicitCpuVisibleStbProjectionOnly',
            'projectedInput': deepcopy(projected), 'candidate': deepcopy(selected['responseCandidate'])}


def _lift(selected):
    return dict(selected['state'], registerGenerations=selected['registerGenerations'],
                registerKnownBits=selected['registerKnownBits'])


def _word(registers):
    lo, hi = registers.get('al'), registers.get('ah')
    return None if lo is None or hi is None else lo + hi * 256


def _comparison_columns(state, provenance, data_bits, register_bits, register_tags):
    registers = state['registers']
    columns = {'registers.a': _word(registers), 'sourcePath': provenance['sourcePath'],
               'precedingWrites': provenance['precedingWrites'], 'unresolvedObligations': provenance['unresolved']}
    columns.update({f'registers.{field}': registers.get(field) for field in _REG_WIDTHS})
    columns.update({f'registerGenerations.{field}': state['registerGenerations'].get(field) for field in register_tags})
    for location in data_bits:
        address, position = location.split('.')
        value = state['memory'].get(address)
        columns[f'knownBits.{location}'] = (state['knownBits'].get(location) if value is None else _bit(value, position))
    for name, position in register_bits:
        value = registers.get(name)
        columns[f'registerKnownBits.{name}.{position}'] = (
            state['registerKnownBits'].get(name, {}).get(position) if value is None else _bit(value, position))
    scb = registers.get('scb')
    for kind in ('memory', 'generations'):
        for address in ('0356', '03F5', '03F6', '00F8', '00F9'):
            columns[f'{kind}.{address}'] = state[kind].get(address)
        for register, displacement in (('x1', 0), ('x2', 2), ('dp', 4), ('usp', 6)):
            first = None if scb is None else 128 + scb * 8 + displacement
            columns[f'pointerBank.{register}.address'] = None if first is None else format(first, '04X')
            for offset, part in enumerate(('low', 'high')):
                columns[f'pointerBank.{register}.{kind}.{part}'] = (
                    None if first is None else state[kind].get(format(first + offset, '04X')))
    return columns


def _ingress(query):
    result = dict(status='RefusedSourcePremise', reason=None, stopBoundary=None, direct=None, detached=None,
                  fields={}, discrepancies=[], unknown=[], **_evidence(_INGRESS_OBLIGATIONS))
    if not _exact_keys(query, 'source', 'detached'):
        return {**result, 'reason': 'ClosedIngressQueryRequired'}
    error, selected, path = _prior(query['source'])
    if error:
        return {**result, 'reason': error}
    if (not _arrives(selected, _EPILOGUE, _EPILOGUE_BOUNDARY) or selected['outcome'] != 'CounterBeyondLength'
            or selected['responseCandidate'] is not None
            or (selected['steps'][-1]['pc'], selected['steps'][-1]['branchTaken']) != (0x024F, True)):
        return {**result, 'reason': 'M2dfDirect0244Required'}
    after = _fragment(query['detached'])
    if after['status'] != 'ConditionalSourceArrivalAt0244':
        return {**result, 'reason': 'Detached0244Required'}
    frozen = query['source']['result']
    trace, writes = selected['steps'], selected['journal']
    if path == 'M2dfFrozenStatusPrefixToAlternate0227':
        trace, writes = frozen['prefix']['steps'] + trace, frozen['orderedWrites']
    direct = dict(sourcePath=path, steps=trace, precedingWrites=writes, unresolved=selected['unresolvedConstraints'])
    detached = dict(sourcePath=after['entryKind'], steps=after['steps'], precedingWrites=after['journal'],
                    unresolved=after['unresolved'])
    left, right = _lift(selected), after['state']
    data_bits = {key for state in (left, right) for key in state['knownBits']
                 if key[:4] in ('0356', '03F5', '03F6', '00F8', '00F9')}
    register_bits = {(reg, bit) for state in (left, right) for reg in ('al', 'ah')
                     for bit in state['registerKnownBits'].get(reg, {})}
    register_tags = left['registerGenerations'].keys() | right['registerGenerations'].keys()
    fields = {}
    left_columns = _comparison_columns(left, direct, data_bits, register_bits, register_tags)
    right_columns = _comparison_columns(right, detached, data_bits, register_bits, register_tags)
    for key, left_value in left_columns.items():
        right_value = right_columns[key]
        relation = ('Unknown' if None in (left_value, right_value) else
                    'Equal' if left_value == right_value else 'Different')
        fields[key] = dict(direct=left_value, detached=right_value, relation=relation)
    return {**result, 'status': 'DistinctSourceIngressCompared', 'reason': 'SourcePathsRemainDistinct',
            'stopBoundary': _EPILOGUE_BOUNDARY, 'direct': direct, 'detached': detached, 'fields': fields,
            'discrepancies': sorted(key for key in fields if fields[key]['relation'] == 'Different'),
            'unknown': sorted(key for key in fields if fields[key]['relation'] == 'Unknown')}


def expected(case):
    """Compute the complete frozen expectation without importing M2dg models."""
    return {
        'detached_0240_0241_transform': _fragment,
        'm2df_candidate_to_detached_0240': _projection,
        'epilogue_0244_ingress_comparison': _ingress,
    }[case['operation']](case['input'])
