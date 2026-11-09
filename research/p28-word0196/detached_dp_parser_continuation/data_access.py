"""Qualify the two reviewed indirect operands against one symbolic DATA state."""

from detached_post_stbuf_0240_0241.fragment import _valid_state

from .analysis import AUTHORITY


_FIELDS = {'pc', 'space', 'widthBits', 'state', 'assumptions', 'expectedDpGenerations', 'interveningWrites'}
_WIDTH = {0x02B7: 16, 0x02C5: 8}
_RAM_END = {'ConditionalStandardInternal201': 0x0280, 'ConditionalStandardInternal207': 0x0480}
_REGISTER_NAMES = ('X1', 'X2', 'DP', 'USP')
_LOW_ALIASES = ('SSP.low', 'SSP.high', 'LRB.low', 'LRB.high', 'PSWL', 'PSWH', 'AL', 'AH')
_STANDARD_SFR = {
    0x0018: 'IRQ.low', 0x0019: 'IRQ.high', 0x001A: 'IE.low', 0x001B: 'IE.high',
    0x0050: 'STCON', 0x0051: 'STBUF', 0x0054: 'SRCON', 0x0055: 'SRBUF', 0x0056: 'SRSTAT',
}
_BLOCKING_CLASSES = ('WriteOnlyRegisterReadBlocked', 'UnresolvedReadSideEffect',
                     'ArchitecturalRegisterAliasUnqualified', 'PotentialSfrRead',
                     'AddressApplicabilityUnknown', 'ExternalDataApplicabilityUnknown')


def _shape(value, fields):
    return type(value) is dict and value.keys() == fields


def _generation(value):
    return value is None or type(value) is str and 0 < len(value) <= 256


def _events_valid(writes):
    return type(writes) is list and len(writes) <= 32 and all(
        _shape(event, {'address', 'widthBits', 'generation'})
        and (event['address'] is None or type(event['address']) is int and 0 <= event['address'] <= 0xFFFF)
        and type(event['widthBits']) is int and event['widthBits'] in (8, 16)
        and _generation(event['generation']) for event in writes)


def _byte_bits(state, address):
    key = f'{address:04X}'
    value = state['memory'][key]
    if value is not None:
        return {str(bit): value >> bit & 1 for bit in range(8)}
    known = state['knownBits']
    return {str(bit): known[f'{key}.{bit}'] for bit in range(8) if f'{key}.{bit}' in known}


def _byte_value(bits, first_bit=0):
    if len(bits.keys() & {str(bit) for bit in range(first_bit, 8)}) != 8 - first_bit:
        return None
    return sum(bits[str(bit)] << bit for bit in range(first_bit, 8))


def _pointing_alias(address, scb):
    if 0x0080 <= address < 0x00C0:
        bank, offset = divmod(address - 0x0080, 8)
        return {'bank': bank, 'register': _REGISTER_NAMES[offset // 2], 'byteOffset': offset % 2,
                'selected': bank == scb}
    return None


def _byte_obligation(address, scb, mapping):
    alias = _pointing_alias(address, scb)
    shadow = ('F8/F9' if address in (0x00F8, 0x00F9) else 'FA/FB'
              if address in (0x00FA, 0x00FB) else None)
    register = _LOW_ALIASES[address] if address < len(_LOW_ALIASES) else _STANDARD_SFR.get(address)
    if address == 0x0051:
        classification = 'WriteOnlyRegisterReadBlocked'
    elif address == 0x0055:
        classification = 'UnresolvedReadSideEffect'
    elif address < len(_LOW_ALIASES):
        classification = 'ArchitecturalRegisterAliasUnqualified'
    elif address < 0x0080:
        classification = 'PotentialSfrRead'
    elif mapping == 'Unknown':
        classification = 'AddressApplicabilityUnknown'
    elif address >= _RAM_END[mapping]:
        classification = 'ExternalDataApplicabilityUnknown'
    elif alias is not None:
        classification = 'ConditionalPointerBankRead'
    elif shadow is not None:
        classification = 'QualifiedSoftwareShadowRead'
    else:
        classification = 'QualifiedOrdinaryDataRead'
    return {'address': address, 'classification': classification, 'standardRegister': register,
            'pointingAlias': alias, 'shadowAlias': shadow}


def _local_aliases(addresses, lrb):
    if lrb is None:
        return None
    base = (lrb & 0x1FFF) * 8
    return [{'address': address, 'register': f'r{address - base}', 'lrb': lrb}
            for address in addresses if base <= address < base + 8]


def _overlap(writes, addresses):
    for event in writes:
        address = event['address']
        count = event['widthBits'] // 8
        base = address & 0xFFFE if count == 2 else address
        if any(base <= target < base + count for target in addresses):
            return True
    return False


def _result(query):
    return {'pc': query.get('pc'), 'space': query.get('space'), 'rawAddress': None, 'effectiveAddress': None,
            'widthBits': query.get('widthBits'), 'classification': 'ClosedIndirectDataQueryRequired', 'allowed': False,
            'byteObligations': [], 'sourceBytes': [], 'sourceGenerations': [], 'knownBits': {}, 'value': None,
            'actualHardwareRead': None, 'pointerStorage': None, 'pointerGenerations': [], 'interveningWrites': [],
            'localAliases': None, 'executionAuthority': dict(AUTHORITY)}


def indirect_data_address_qualification(query):
    """Resolve the selected DP and qualify every byte before any mathematical read."""
    out = _result(query if type(query) is dict else {})

    def stop(reason):
        return {**out, 'classification': reason}

    if not _shape(query, _FIELDS):
        return out
    pc, width, state, assumptions = (query[key] for key in ('pc', 'widthBits', 'state', 'assumptions'))
    if type(pc) is not int or pc not in _WIDTH:
        return stop('OutsideVerifiedReadScope')
    if query['space'] != 'DATA':
        return stop('WrongDataAddressSpace')
    if type(width) is not int or width != _WIDTH[pc]:
        return stop('WrongDataReadWidth')
    if not _valid_state(state):
        return stop('TypedIndirectDataStateRequired')
    if (not _shape(assumptions, {'dataMapping', 'noInterference'})
            or assumptions['dataMapping'] not in (*_RAM_END, 'Unknown')
            or assumptions['noInterference'] is not None and type(assumptions['noInterference']) is not bool):
        return stop('TypedIndirectDataAssumptionsRequired')
    expected, writes = query['expectedDpGenerations'], query['interveningWrites']
    if type(expected) is not list or len(expected) != 2 or not all(_generation(tag) for tag in expected):
        return stop('TypedDpGenerationPairRequired')
    if not _events_valid(writes):
        return stop('TypedInterveningWritesRequired')
    out['interveningWrites'] = [dict(event) for event in writes]
    if assumptions['noInterference'] is not True:
        return stop('NoInterferencePremiseRequired')
    scb = state['registers'].get('scb')
    if scb is None:
        return stop('SelectedPointingBankUnknown')
    base = 0x0084 + 8 * scb
    out['pointerStorage'] = base
    pair = (f'{base:04X}', f'{base + 1:04X}')
    out['pointerGenerations'] = current = [state['generations'].get(key) for key in pair]
    if not all(key in state['memory'] for key in pair):
        return stop('SelectedDpBackingBytesMissing')
    if None in (*current, *expected):
        return stop('PointerGenerationMissing')
    if current != expected:
        return stop('PointerGenerationMismatch')
    if any(event['address'] is None for event in writes):
        return stop('UnknownInterveningWriteFootprint')
    if _overlap(writes, (base, base + 1)):
        return stop('InterveningDpWriteOverlap')
    low, high = (_byte_bits(state, address) for address in (base, base + 1))
    low_value, high_value = _byte_value(low), _byte_value(high)
    if low_value is not None and high_value is not None:
        out['rawAddress'] = low_value + 256 * high_value
    low_effective = _byte_value(low, first_bit=1 if width == 16 else 0)
    if low_effective is None or high_value is None:
        return stop('UnknownEffectiveAddress')
    effective = low_effective + 256 * high_value
    out['effectiveAddress'] = effective
    addresses = tuple(range(effective, effective + width // 8))
    out['byteObligations'] = obligations = [_byte_obligation(address, scb, assumptions['dataMapping'])
                                             for address in addresses]
    out['localAliases'] = _local_aliases(addresses, state['registers'].get('lrb'))
    classes = {item['classification'] for item in obligations}
    for classification in _BLOCKING_CLASSES:
        if classification in classes:
            return stop(classification)
    if _overlap(writes, addresses):
        return stop('InterveningTargetWriteOverlap')
    targets = [f'{address:04X}' for address in addresses]
    if not all(key in state['memory'] for key in targets):
        return stop('IndirectDataBytesMissing')
    generations = [state['generations'][key] for key in targets]
    if None in generations:
        return stop('IndirectDataGenerationMissing')
    parts = [_byte_bits(state, address) for address in addresses]
    values = [_byte_value(bits) for bits in parts]
    return {**out, 'classification': 'ConditionalOrdinaryDataRead', 'allowed': True,
            'sourceBytes': values, 'sourceGenerations': generations,
            'knownBits': {str(8 * offset + int(bit)): value for offset, bits in enumerate(parts)
                          for bit, value in bits.items()},
            'value': None if None in values else sum(value << (8 * offset) for offset, value in enumerate(values))}
