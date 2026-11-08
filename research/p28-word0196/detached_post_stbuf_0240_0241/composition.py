"""Source-identity checks and formal relations across the unevaluated STBUF."""
from copy import deepcopy

from alternate_parser_response_checksum.analysis import AUTHORITY, canonical
from alternate_parser_response_checksum.composition import alternate_parser_step
from alternate_parser_response_checksum.path import alternate_response_selector

from .fragment import detached_0240_0241_transform

M2DF_SHA = 'a9eeb45292a120711bb1adf918385675c2456409'
M2DF_FINGERPRINT = 'a1c554e17305f199effbc2e3aae2b42ab83081da7e527b4eeeab181faf691e55'
SOURCE_ID = 'M2dgReviewed0240_0241'
STBUF_STOP = 'STOP_BEFORE_STBUF_023E'
EPILOGUE_STOP = 'STOP_BEFORE_EPILOGUE_0244'
_SOURCE_FIELDS = {'baseSha', 'sourceFingerprint', 'operation', 'input', 'result'}
_PREMISES = {'cpuProjection', 'noInterference', 'ordinaryInternalRam'}
_CANDIDATE_OUTCOMES = {'LengthRegisterResponse', 'ProgramSelectedDataResponse', 'NegatedChecksumResponse'}
_REGISTERS = ('al', 'ah', 'cf', 'zf', 'hc', 'dd', 'mie', 'otherPsw', 'lrb', 'scb', 'usp', 'ssp')
_RELEVANT_DATA = {'0356', '03F5', '03F6', '00F8', '00F9'}
_POINTER_OFFSETS = {'x1': 0, 'x2': 2, 'dp': 4, 'usp': 6}
_PROJECTION_OBLIGATIONS = ('StbufAcceptanceAndTransmissionUnestablished',
                           'NativePostStbufPcUnestablished', 'ActualPeripheralMappingUnestablished')
_INGRESS_OBLIGATIONS = ('DifferentSourceIngressProvenance', 'EpilogueEffectsOutsideScope',
                        'NativePostStbufPcUnestablished')


def _shape(value, fields):
    return type(value) is dict and value.keys() == fields


def _source(source):
    if not _shape(source, _SOURCE_FIELDS):
        return 'ClosedM2dfSourceEnvelopeRequired', None, None
    if (source['baseSha'] != M2DF_SHA or source['sourceFingerprint'] != M2DF_FINGERPRINT
            or source['operation'] not in ('alternate_response_selector', 'alternate_parser_step')):
        return 'ExactM2dfSourceIdentityRequired', None, None
    operation = source['operation']
    model = alternate_parser_step if operation == 'alternate_parser_step' else alternate_response_selector
    try:
        replay = model(source['input'])
        matches = canonical(replay) == canonical(source['result'])
    except (ValueError, TypeError, KeyError, RecursionError, OverflowError):
        matches = False
    if not matches:
        return 'FrozenM2dfReplayMismatch', None, None
    if operation == 'alternate_parser_step':
        return None, replay['alternate'], 'M2dfFrozenStatusPrefixToAlternate0227'
    return None, replay, 'M2dfAlternate0227'


def _events():
    return {'steps': [], 'reads': [], 'journal': [], 'executionAuthority': dict(AUTHORITY)}


def _projection(reason, path=None, snapshot=None, candidate=None, boundary=None):
    return {'status': 'RefusedSourcePremise' if snapshot is None else 'ConditionalCpuStateProjection',
            'reason': reason, 'sourcePath': path, 'projectedInput': snapshot, 'candidate': candidate,
            'stopBoundary': boundary, 'unresolved': list(_PROJECTION_OBLIGATIONS), **_events()}


def _selected_path(selected, stop_pc, stop_boundary):
    return (selected is not None and selected['status'] == 'CompleteConditional'
            and selected['entryQualification'] == 'DetachedConditionalSourcePath'
            and selected['boundary'] == stop_pc and selected['stopBoundary'] == stop_boundary
            and selected['steps'][0]['pc'] == 0x0227 and selected['steps'][-1]['next'] == stop_pc)


def m2df_candidate_to_detached_0240(query):
    """Project the documented DD0 STB CPU frame under explicit symbolic premises."""
    if not _shape(query, {'source', 'assumptions'}):
        return _projection('ClosedProjectionQueryRequired')
    reason, selected, path = _source(query['source'])
    if reason is not None:
        return _projection(reason)
    if not _selected_path(selected, 0x023E, STBUF_STOP) or selected['outcome'] not in _CANDIDATE_OUTCOMES:
        return _projection('M2dfCandidateBoundaryRequired', path)
    premises = query['assumptions']
    if not _shape(premises, _PREMISES) or not all(value is True for value in premises.values()):
        return _projection('ExplicitProjectionAssumptionsRequired', path, boundary=STBUF_STOP)
    if selected['state']['registers']['dd'] != 0:
        return _projection('M2dfByteStorePrerequisiteRequired', path, boundary=STBUF_STOP)
    # A manufacturer-qualified input never upgrades this projection beyond symbolic input.
    input_class = ('SyntheticTestInput' if selected['inputClass'] == 'SyntheticTestInput'
                   else 'SymbolicInput')
    snapshot = {'sourceId': SOURCE_ID, 'entryPc': 0x0240, 'inputClass': input_class,
                'assumptions': {key: premises[key] for key in ('noInterference', 'ordinaryInternalRam')},
                'state': {**selected['state'], 'registerGenerations': selected['registerGenerations'],
                          'registerKnownBits': selected['registerKnownBits']}}
    return _projection('ExplicitCpuVisibleStbProjectionOnly', path, deepcopy(snapshot),
                       deepcopy(selected['responseCandidate']), STBUF_STOP)


def _ingress(reason, direct=None, detached=None, fields=None):
    fields = {} if fields is None else fields
    return {'status': 'RefusedSourcePremise' if direct is None else 'DistinctSourceIngressCompared',
            'reason': reason, 'stopBoundary': EPILOGUE_STOP if direct is not None else None,
            'direct': direct, 'detached': detached,
            'fields': fields, 'discrepancies': sorted(key for key, row in fields.items()
                                                     if row['relation'] == 'Different'),
            'unknown': sorted(key for key, row in fields.items() if row['relation'] == 'Unknown'),
            'unresolved': list(_INGRESS_OBLIGATIONS), **_events()}


def _pair(left, right):
    relation = 'Unknown' if left is None or right is None else 'Equal' if left == right else 'Different'
    return {'direct': left, 'detached': right, 'relation': relation}


def _word(low, high):
    return None if low is None or high is None else low | (high << 8)


def _bit(value, index, known):
    return known if value is None else (value >> int(index)) & 1


def _compare(left, right, direct, detached):
    left_r, right_r = left['registers'], right['registers']
    left_al, left_ah = left_r.get('al'), left_r.get('ah')
    right_al, right_ah = right_r.get('al'), right_r.get('ah')
    fields = {
        'registers.a': _pair(_word(left_al, left_ah), _word(right_al, right_ah)),
        'sourcePath': _pair(direct['sourcePath'], detached['sourcePath']),
        'precedingWrites': _pair(direct['precedingWrites'], detached['precedingWrites']),
        'unresolvedObligations': _pair(direct['unresolved'], detached['unresolved']),
    }
    fields.update({f'registers.{key}': _pair(left_r.get(key), right_r.get(key)) for key in _REGISTERS})
    left_gen, right_gen = left['registerGenerations'], right['registerGenerations']
    for register in sorted(left_gen.keys() | right_gen.keys()):
        fields[f'registerGenerations.{register}'] = _pair(left_gen.get(register), right_gen.get(register))
    left_data_bits, right_data_bits = left['knownBits'], right['knownBits']
    for field in sorted(left_data_bits.keys() | right_data_bits.keys()):
        address, bit = field.split('.')
        if address in _RELEVANT_DATA:
            fields[f'knownBits.{field}'] = _pair(
                _bit(left['memory'].get(address), bit, left_data_bits.get(field)),
                _bit(right['memory'].get(address), bit, right_data_bits.get(field)))
    for register in ('al', 'ah'):
        left_bits = left['registerKnownBits'].get(register, {})
        right_bits = right['registerKnownBits'].get(register, {})
        for bit in sorted(left_bits.keys() | right_bits.keys()):
            fields[f'registerKnownBits.{register}.{bit}'] = _pair(
                _bit(left_r.get(register), bit, left_bits.get(bit)),
                _bit(right_r.get(register), bit, right_bits.get(bit)))
    for key in ('memory', 'generations'):
        for address in sorted(_RELEVANT_DATA):
            fields[f'{key}.{address}'] = _pair(left[key].get(address), right[key].get(address))
    for name, offset in _POINTER_OFFSETS.items():
        left_addresses = _pointer_bytes(left_r.get('scb'), offset)
        right_addresses = _pointer_bytes(right_r.get('scb'), offset)
        fields[f'pointerBank.{name}.address'] = _pair(
            left_addresses[0] if left_addresses else None, right_addresses[0] if right_addresses else None)
        for key in ('memory', 'generations'):
            for i, part in enumerate(('low', 'high')):
                fields[f'pointerBank.{name}.{key}.{part}'] = _pair(
                    left[key].get(left_addresses[i]) if left_addresses else None,
                    right[key].get(right_addresses[i]) if right_addresses else None)
    return fields


def _pointer_bytes(scb, offset):
    if scb is None:
        return ()
    address = 0x80 + 8 * scb + offset
    return f'{address:04X}', f'{address + 1:04X}'


def epilogue_0244_ingress_comparison(query):
    """Compare distinct source arrivals without admitting the 0244 instruction."""
    if not _shape(query, {'source', 'detached'}):
        return _ingress('ClosedIngressQueryRequired')
    reason, selected, path = _source(query['source'])
    if reason is not None:
        return _ingress(reason)
    if (not _selected_path(selected, 0x0244, EPILOGUE_STOP)
            or selected['outcome'] != 'CounterBeyondLength' or selected['responseCandidate'] is not None
            or selected['steps'][-1]['pc'] != 0x024F or selected['steps'][-1]['branchTaken'] is not True):
        return _ingress('M2dfDirect0244Required')
    try:
        downstream = detached_0240_0241_transform(query['detached'])
    except (ValueError, TypeError, KeyError, RecursionError, OverflowError):
        return _ingress('Detached0244Required')
    if (downstream['status'] != 'ConditionalSourceArrivalAt0244' or downstream['stopPc'] != 0x0244
            or downstream['stopBoundary'] != EPILOGUE_STOP):
        return _ingress('Detached0244Required')
    left = {**selected['state'], 'registerGenerations': selected['registerGenerations'],
            'registerKnownBits': selected['registerKnownBits']}
    right = downstream['state']
    source_result = query['source']['result']
    if path == 'M2dfAlternate0227':
        source_steps, writes = selected['steps'], selected['journal']
    else:
        source_steps = source_result['prefix']['steps'] + selected['steps']
        writes = source_result['orderedWrites']
    direct = {'sourcePath': path, 'steps': source_steps, 'precedingWrites': writes,
              'unresolved': selected['unresolvedConstraints']}
    detached = {'sourcePath': downstream['entryKind'], 'steps': downstream['steps'],
                'precedingWrites': downstream['journal'], 'unresolved': downstream['unresolved']}
    fields = _compare(left, right, direct, detached)
    return deepcopy(_ingress('SourcePathsRemainDistinct', direct, detached, fields))
