"""Independent M2dj expectations using primary-source ternary bit vectors."""
from copy import deepcopy

from detached_post_stbuf_0240_0241.reference_oracle import _typed_state

from .analysis import AUTHORITY

_RAM_LIMITS = {'ConditionalStandardInternal201': 639, 'ConditionalStandardInternal207': 1151}
_BYTE_WIDTH = {695: 16, 709: 8}
_ADDR_ALIAS = {0: 'SSP.low', 1: 'SSP.high', 2: 'LRB.low', 3: 'LRB.high', 4: 'PSWL', 5: 'PSWH',
               6: 'AL', 7: 'AH', 24: 'IRQ.low', 25: 'IRQ.high', 26: 'IE.low', 27: 'IE.high',
               80: 'STCON', 81: 'STBUF', 84: 'SRCON', 85: 'SRBUF', 86: 'SRSTAT'}
_HALTS = ('WriteOnlyRegisterReadBlocked', 'UnresolvedReadSideEffect',
          'ArchitecturalRegisterAliasUnqualified', 'PotentialSfrRead', 'AddressApplicabilityUnknown',
          'ExternalDataApplicabilityUnknown')
_ENTRY = 'DetachedSymbolicEntry02B0'
_LIMITS = ['UnprovedNativeIngress', 'ActualSrbufProducerUnknown', 'ActualDataMappingUnknown',
           'PhysicalStackOrFrameOverlapUnknown', 'HistoricalLocalWriterContinuityNotEstablished',
           'PeripheralAndInterruptLifecycleUnknown']


def _shape(obj, *fields):
    return type(obj) is dict and len(obj) == len(fields) and all(field in obj for field in fields)


def _integer(value, max_value):
    return type(value) is int and 0 <= value <= max_value


def _label(value):
    return value is None or type(value) is str and 1 <= len(value) <= 256


def _bit(value, position):
    return (value // (2 ** position)) % 2


def _vector(value, partial, width):
    if value is not None:
        return tuple(_bit(value, bit) for bit in range(width))
    return tuple(partial.get(str(bit)) for bit in range(width))


def _number(vector):
    if None in vector:
        return None
    return sum(bit * (2 ** position) for position, bit in enumerate(vector))


def _known(vector):
    return {str(position): bit for position, bit in enumerate(vector) if bit is not None}


def _zero(vector):
    if any(bit == 1 for bit in vector):
        return 0
    return None if None in vector else 1


def _location(address):
    return format(address, '04X')


def _data_vector(state, address):
    slot = _location(address)
    bits = {str(i): state['knownBits'].get(f'{slot}.{i}') for i in range(8)}
    return _vector(state['memory'].get(slot), bits, 8)


def _register_vector(state, register):
    return _vector(state['registers'].get(register), state['registerKnownBits'].get(register, {}), 8)


def _register_word(state):
    return _register_vector(state, 'al') + _register_vector(state, 'ah')


def _dp_address(bank):
    return 132 + 8 * bank


def _check_writes(writes):
    return type(writes) is list and len(writes) <= 32 and all(
        _shape(event, 'address', 'widthBits', 'generation')
        and (event['address'] is None or _integer(event['address'], 65535))
        and type(event['widthBits']) is int and event['widthBits'] in (8, 16)
        and _label(event['generation']) for event in writes)


def _overlap_set(writes):
    footprints = set()
    for row in writes:
        if row['widthBits'] == 8:
            footprints.add(row['address'])
        else:
            boundary = 2 * (row['address'] // 2)
            footprints.update((boundary, boundary + 1))
    return footprints


def _operand_byte(address, active_bank, mapping):
    bank, in_bank = divmod(address - 128, 8)
    pointer_alias = None
    if bank in range(8):
        register = ('X1', 'X2', 'DP', 'USP')[in_bank // 2]
        pointer_alias = dict(bank=bank, register=register, byteOffset=in_bank % 2, selected=bank == active_bank)
    shadow = 'F8/F9' if address in (248, 249) else 'FA/FB' if address in (250, 251) else None
    if address < 128:
        category = {81: 'WriteOnlyRegisterReadBlocked', 85: 'UnresolvedReadSideEffect'}.get(address)
        if category is None:
            category = 'ArchitecturalRegisterAliasUnqualified' if address < 8 else 'PotentialSfrRead'
    elif mapping not in _RAM_LIMITS:
        category = 'AddressApplicabilityUnknown'
    elif address > _RAM_LIMITS[mapping]:
        category = 'ExternalDataApplicabilityUnknown'
    elif pointer_alias is not None:
        category = 'ConditionalPointerBankRead'
    elif shadow is not None:
        category = 'QualifiedSoftwareShadowRead'
    else:
        category = 'QualifiedOrdinaryDataRead'
    return dict(address=address, classification=category, standardRegister=_ADDR_ALIAS.get(address),
                pointingAlias=pointer_alias, shadowAlias=shadow)


def _data_reference(query):
    context = query if type(query) is dict else {}
    result = dict(pc=context.get('pc'), space=context.get('space'), rawAddress=None, effectiveAddress=None,
                  widthBits=context.get('widthBits'), classification='ClosedIndirectDataQueryRequired',
                  allowed=False, byteObligations=[], sourceBytes=[], sourceGenerations=[], knownBits={},
                  value=None, actualHardwareRead=None, pointerStorage=None, pointerGenerations=[],
                  interveningWrites=[], localAliases=None, executionAuthority=dict(AUTHORITY))

    def stop(label):
        return {**result, 'classification': label}

    if not _shape(query, 'pc', 'space', 'widthBits', 'state', 'assumptions', 'expectedDpGenerations',
                  'interveningWrites'):
        return result
    pc, width = query['pc'], query['widthBits']
    if not _integer(pc, 65535) or pc not in _BYTE_WIDTH:
        return stop('OutsideVerifiedReadScope')
    if query['space'] != 'DATA':
        return stop('WrongDataAddressSpace')
    if not _integer(width, 16) or width != _BYTE_WIDTH[pc]:
        return stop('WrongDataReadWidth')
    state, assumptions = query['state'], query['assumptions']
    if not _typed_state(state):
        return stop('TypedIndirectDataStateRequired')
    if (not _shape(assumptions, 'dataMapping', 'noInterference')
            or assumptions['dataMapping'] not in (*_RAM_LIMITS, 'Unknown')
            or type(assumptions['noInterference']) not in (bool, type(None))):
        return stop('TypedIndirectDataAssumptionsRequired')
    requested, writes = query['expectedDpGenerations'], query['interveningWrites']
    if type(requested) is not list or len(requested) != 2 or not all(_label(tag) for tag in requested):
        return stop('TypedDpGenerationPairRequired')
    if not _check_writes(writes):
        return stop('TypedInterveningWritesRequired')
    result['interveningWrites'] = deepcopy(writes)
    if assumptions['noInterference'] is not True:
        return stop('NoInterferencePremiseRequired')
    bank = state['registers'].get('scb')
    if bank is None:
        return stop('SelectedPointingBankUnknown')
    first = _dp_address(bank)
    storage = (first, first + 1)
    result['pointerStorage'] = first
    storage_slots = [_location(address) for address in storage]
    active = [state['generations'].get(slot) for slot in storage_slots]
    result['pointerGenerations'] = active
    if not set(storage_slots).issubset(state['memory']):
        return stop('SelectedDpBackingBytesMissing')
    if None in active or None in requested:
        return stop('PointerGenerationMissing')
    if active != requested:
        return stop('PointerGenerationMismatch')
    if any(event['address'] is None for event in writes):
        return stop('UnknownInterveningWriteFootprint')
    overlaps = _overlap_set(writes)
    if overlaps.intersection(storage):
        return stop('InterveningDpWriteOverlap')
    pointer = _data_vector(state, first) + _data_vector(state, first + 1)
    result['rawAddress'] = _number(pointer)
    if width == 16:
        pointer = (0,) + pointer[1:]
    address = _number(pointer)
    if address is None:
        return stop('UnknownEffectiveAddress')
    result['effectiveAddress'] = address
    addresses = [address + offset for offset in range(width // 8)]
    records = [_operand_byte(target, bank, assumptions['dataMapping']) for target in addresses]
    result['byteObligations'] = records
    lrb = state['registers'].get('lrb')
    if lrb is not None:
        local = 8 * (lrb % 8192)
        result['localAliases'] = [dict(address=target, register=f'r{target - local}', lrb=lrb)
                                  for target in addresses if target in range(local, local + 8)]
    for forbidden in _HALTS:
        if any(row['classification'] == forbidden for row in records):
            return stop(forbidden)
    if overlaps.intersection(addresses):
        return stop('InterveningTargetWriteOverlap')
    slots = [_location(target) for target in addresses]
    if not set(slots).issubset(state['memory']):
        return stop('IndirectDataBytesMissing')
    generations = [state['generations'][slot] for slot in slots]
    if None in generations:
        return stop('IndirectDataGenerationMissing')
    vectors = [_data_vector(state, target) for target in addresses]
    combined = sum(vectors, ())
    return {**result, 'classification': 'ConditionalOrdinaryDataRead', 'allowed': True,
            'sourceBytes': [_number(vector) for vector in vectors], 'sourceGenerations': generations,
            'knownBits': _known(combined), 'value': _number(combined)}


def _entry_snapshot(query):
    if not _shape(query, 'sourceId', 'entryPc', 'entryClass', 'inputClass', 'a16', 'scbKnownBits',
                  'assumptions', 'state'):
        return 'ClosedDetachedDpSnapshotRequired', None
    if (query['sourceId'], query['entryPc'], query['entryClass']) != ('M2djReviewedDetachedDp', 688, _ENTRY):
        return 'ExactDetachedDpEntryRequired', None
    if type(query['entryPc']) is not int or query['inputClass'] not in ('SymbolicInput', 'SyntheticTestInput'):
        return 'ExactDetachedDpEntryRequired', None
    word, selector, premise, original = (query[key] for key in ('a16', 'scbKnownBits', 'assumptions', 'state'))
    if (not _shape(premise, 'dataMapping', 'noInterference')
            or premise['dataMapping'] not in (*_RAM_LIMITS, 'Unknown')
            or type(premise['noInterference']) not in (bool, type(None))
            or word is not None and not _integer(word, 65535)
            or type(selector) is not dict or any(key not in ('0', '1', '2') for key in selector)
            or any(not _integer(value, 1) for value in selector.values())
            or not _typed_state(original)):
        return 'TypedDetachedDpStateRequired', None
    state = deepcopy(original)
    declared_word = _register_word(state)
    if word is not None and any(bit is not None and bit != _bit(word, position)
                                for position, bit in enumerate(declared_word)):
        return 'ContradictoryAccumulatorAliases', state
    bank = state['registers'].get('scb')
    if bank is not None and any(value != _bit(bank, int(position)) for position, value in selector.items()):
        return 'ContradictoryScbKnowledge', state
    if premise['noInterference'] is not True:
        return 'NoInterferencePremiseRequired', state
    if bank is None:
        bank = _number(_vector(None, selector, 3))
        if bank is None:
            return 'SelectedPointingBankUnknown', state
        state['registers']['scb'] = bank
        if not _typed_state(state):
            return 'ContradictorySelectedBankAlias', deepcopy(original)
    if premise['dataMapping'] not in _RAM_LIMITS:
        return 'UnqualifiedDpMapping', state
    if word is not None:
        high, low = divmod(word, 256)
        state['registers'].update(al=low, ah=high)
        state['registerKnownBits'] = {}
    return None, state


def _pointer_snapshot(state):
    bank = state['registers'].get('scb')
    if bank is None:
        return None, None
    base = _dp_address(bank)
    vector = _data_vector(state, base) + _data_vector(state, base + 1)
    addresses = [base, base + 1]
    metadata = dict(bank=bank, addresses=addresses, bytes=[_number(vector[:8]), _number(vector[8:])],
                    generations=[state['generations'].get(_location(address)) for address in addresses],
                    knownBits=_known(vector), value=_number(vector))
    return metadata, vector


class _Witness:
    """Preserve observations while interpreting source equations over ternary bits."""

    def __init__(self, state):
        self.state = state
        self.trace = []
        self.operands = []
        self.stores = []
        self.checked_operand = None
        self.tags = [] if state is None else list(state['generations'].values()) + list(
            state['registerGenerations'].values())

    def finish(self, status, stop, reason, boundary=None):
        state = self.state
        value = None
        pointer = None
        if state is not None:
            bits = _register_word(state)
            value = dict(value=_number(bits), knownBits=_known(bits))
            pointer, _ = _pointer_snapshot(state)
        return dict(status=status, reason=reason, entryClass=_ENTRY, stopPc=stop, stopBoundary=boundary,
                    state=state, a16=value, pointer=pointer, steps=self.trace, reads=self.operands,
                    journal=self.stores, qualification=self.checked_operand, unresolved=list(_LIMITS),
                    executionAuthority=dict(AUTHORITY))

    def record(self, pc, successor, *, branch=None, flag=None):
        evidence = None
        if flag is not None:
            evidence = dict(flag=flag, value=self.state['registers'].get(flag),
                            generation=self.state['registerGenerations'].get(flag), takenWhen=1)
        self.trace.append(dict(pc=pc, next=successor, kind='RegisterEffect' if flag is None else 'Branch',
                               branchTaken=branch, predicateEvidence=evidence, state=deepcopy(self.state)))

    def issue(self, pc, fields):
        new = {name: 'M2dj:{:04X}:{}'.format(pc, name.upper()) for name in fields}
        if any(tag in self.tags for tag in new.values()):
            return None
        self.tags += list(new.values())
        return new

    def accum(self, pc, vector, **flags):
        touched = {'al': vector[:8]}
        if len(vector) == 16:
            touched['ah'] = vector[8:]
        update = self.issue(pc, [*touched, *flags])
        if update is None:
            return False
        state = self.state
        for register, bits in touched.items():
            state['registers'][register] = _number(bits)
            state['registerKnownBits'].pop(register, None)
            if state['registers'][register] is None:
                state['registerKnownBits'][register] = _known(bits)
        state['registers'].update(flags)
        state['registerGenerations'].update(update)
        return True

    def set_dp(self, pc, vector, source, provenance):
        old, _ = _pointer_snapshot(self.state)
        slots = [_location(address) for address in old['addresses']]
        if not set(slots).issubset(self.state['memory']):
            return 'SelectedDpBackingBytesMissing'
        if None in old['generations']:
            return 'PointerGenerationMissing'
        tags = self.issue(pc, ['dp.low', 'dp.high'])
        if tags is None:
            return 'RegisterGenerationCollision'
        parts = [vector[:8], vector[8:]]
        new_bytes = [_number(part) for part in parts]
        known = self.state['knownBits']
        for key in list(known):
            if key[:4] in slots:
                del known[key]
        for index, key in enumerate(slots):
            self.state['memory'][key] = new_bytes[index]
            self.state['generations'][key] = tags['dp.low' if index == 0 else 'dp.high']
            if new_bytes[index] is None:
                for position, bit in _known(parts[index]).items():
                    known[f'{key}.{position}'] = bit
        same = None
        if None not in new_bytes + old['bytes']:
            same = new_bytes == old['bytes']
        self.stores.append(dict(ordinal=len(self.stores) + 1, pc=pc, space='DATA', address=old['addresses'][0],
                                widthBits=16, bank=old['bank'], kind='PointingRegisterWordStore',
                                valueSource=source, beforeBytes=old['bytes'], afterBytes=new_bytes,
                                beforeKnownBits=old['knownBits'], afterKnownBits=_known(vector),
                                beforeGenerations=old['generations'], afterGenerations=list(tags.values()),
                                sourceGenerations=provenance, sameValue=same))
        return None

    def indirect(self, site, premise):
        width = _BYTE_WIDTH[site]
        pointer, _ = _pointer_snapshot(self.state)
        query = dict(pc=site, space='DATA', widthBits=width, state=self.state, assumptions=premise,
                     expectedDpGenerations=pointer['generations'], interveningWrites=[])
        proof = self.checked_operand = _data_reference(query)
        if not proof['allowed']:
            boundary = 'STOP_BEFORE_UNQUALIFIED_INDIRECT_DATA_READ_{:04X}'.format(site)
            return self.finish('UnqualifiedIndirectDataRead', site, proof['classification'], boundary)
        bits = _vector(proof['value'], proof['knownBits'], width)
        if not self.accum(site, bits, dd=int(width == 16), zf=_zero(bits)):
            return self.finish('OutsideVerifiedScope', site, 'RegisterGenerationCollision')
        self.operands.append(dict(pc=site, space='DATA', address=proof['effectiveAddress'], widthBits=width,
                                  value=proof['value'], bytes=proof['sourceBytes'], knownBits=proof['knownBits'],
                                  generations=proof['sourceGenerations'], kind='ConditionalIndirectDataOperand'))
        self.record(site, site + 1)
        return self.finish('ConditionalSourcePrefixEstablished', site + 1, 'DownstreamEffectsOutsideScope',
                           'STOP_BEFORE_UNREVIEWED_{:04X}'.format(site + 1))


def _continuation_reference(query):
    failure, state = _entry_snapshot(query)
    witness = _Witness(state)
    if failure:
        return witness.finish('RefusedSourcePremise', 688, failure)
    provenance = [state['registerGenerations'].get(name) for name in ('al', 'ah')]
    if None in provenance:
        return witness.finish('OutsideVerifiedScope', 688, 'AccumulatorSourceGenerationMissing')
    entry_word = _register_word(state)
    failure = witness.set_dp(688, entry_word, 'A16', provenance)
    if failure:
        return witness.finish('OutsideVerifiedScope', 688, failure)
    witness.record(688, 689)
    direct, stored_word = _pointer_snapshot(state)
    is_zero = _zero(stored_word)
    if not witness.accum(689, stored_word, dd=1, zf=is_zero):
        return witness.finish('OutsideVerifiedScope', 689, 'RegisterGenerationCollision')
    witness.operands.append(dict(pc=689, space='REGISTER', address=direct['addresses'][0],
                                 widthBits=16, value=direct['value'], bytes=direct['bytes'],
                                 knownBits=direct['knownBits'], generations=direct['generations'],
                                 kind='SelectedDpRegisterOperand'))
    witness.record(689, 690)
    if is_zero is None:
        witness.record(690, None, flag='zf')
        return witness.finish('IndeterminateBranch', 690, 'WordZeroPredicateUnknown')
    if is_zero == 1:
        witness.record(690, 706, branch=True, flag='zf')
        failure = witness.set_dp(706, _vector(860, {}, 16), 'Immediate035C', [])
        if failure:
            return witness.finish('OutsideVerifiedScope', 706, failure)
        witness.record(706, 709)
        return witness.indirect(709, query['assumptions'])
    witness.record(690, 692, branch=False, flag='zf')
    carry, shifted_word = stored_word[0], stored_word[1:] + (0,)
    if not witness.accum(692, shifted_word, cf=carry):
        return witness.finish('OutsideVerifiedScope', 692, 'RegisterGenerationCollision')
    witness.record(692, 693)
    if carry is None:
        witness.record(693, None, flag='cf')
        return witness.finish('IndeterminateBranch', 693, 'ShiftCarryPredicateUnknown')
    indirect_site = 709 if carry == 1 else 695
    witness.record(693, indirect_site, branch=carry == 1, flag='cf')
    return witness.indirect(indirect_site, query['assumptions'])


def expected(case):
    """Produce the complete expected canonical output without M2dj implementations."""
    return {'detached_02b0_02b2_transform': _continuation_reference,
            'indirect_data_address_qualification': _data_reference}[case['operation']](case['input'])
