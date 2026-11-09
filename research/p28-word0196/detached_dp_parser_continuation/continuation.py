"""The confirmed DP, flag and conditional DATA effects of the detached corridor."""
from copy import deepcopy

from detached_post_stbuf_0240_0241.fragment import _valid_state

from .analysis import AUTHORITY
from .data_access import indirect_data_address_qualification

SOURCE_ID = 'M2djReviewedDetachedDp'
ENTRY = 'DetachedSymbolicEntry02B0'
FIELDS = {'sourceId', 'entryPc', 'entryClass', 'inputClass', 'a16', 'scbKnownBits', 'assumptions', 'state'}
MAPS = ('ConditionalStandardInternal201', 'ConditionalStandardInternal207')
LIMITS = ('UnprovedNativeIngress', 'ActualSrbufProducerUnknown', 'ActualDataMappingUnknown',
          'PhysicalStackOrFrameOverlapUnknown', 'HistoricalLocalWriterContinuityNotEstablished',
          'PeripheralAndInterruptLifecycleUnknown')


def _shape(value, fields):
    return type(value) is dict and value.keys() == fields


def _bits(value, partial, width):
    return ({str(bit): value >> bit & 1 for bit in range(width)} if value is not None else dict(partial))


def _scalar(known, width):
    return sum(value << int(bit) for bit, value in known.items()) if len(known) == width else None


def _word(low, high):
    return {**low, **{str(8 + int(bit)): value for bit, value in high.items()}}


def _part(word, offset):
    return {str(bit - offset): word[str(bit)] for bit in range(offset, offset + 8) if str(bit) in word}


def _accumulator(state):
    r, known = state['registers'], state['registerKnownBits']
    return _word(*(_bits(r.get(key), known.get(key, {}), 8) for key in ('al', 'ah')))


def _zero(known, width):
    return 0 if 1 in known.values() else 1 if len(known) == width else None


def _pointer(state):
    scb = state['registers'].get('scb')
    if scb is None:
        return None
    base = 0x0084 + 8 * scb
    keys = [f'{base:04X}', f'{base + 1:04X}']
    parts = [_bits(state['memory'].get(key),
                   {field[-1]: value for field, value in state['knownBits'].items() if field[:4] == key}, 8)
             for key in keys]
    known = _word(*parts)
    return {'bank': scb, 'addresses': [base, base + 1], 'bytes': [_scalar(part, 8) for part in parts],
            'generations': [state['generations'].get(key) for key in keys],
            'knownBits': known, 'value': _scalar(known, 16)}


def _admit(query):
    if not _shape(query, FIELDS):
        return 'ClosedDetachedDpSnapshotRequired', None
    if (query['sourceId'] != SOURCE_ID or type(query['entryPc']) is not int or query['entryPc'] != 0x02B0
            or query['entryClass'] != ENTRY or query['inputClass'] not in ('SymbolicInput', 'SyntheticTestInput')):
        return 'ExactDetachedDpEntryRequired', None
    a16, selectors, assumptions = query['a16'], query['scbKnownBits'], query['assumptions']
    if (not _shape(assumptions, {'noInterference', 'dataMapping'}) or assumptions['dataMapping'] not in (*MAPS, 'Unknown')
            or assumptions['noInterference'] is not None and type(assumptions['noInterference']) is not bool
            or a16 is not None and (type(a16) is not int or not 0 <= a16 <= 0xFFFF)
            or type(selectors) is not dict or not selectors.keys() <= {'0', '1', '2'}
            or any(type(v) is not int or v not in (0, 1) for v in selectors.values())
            or not _valid_state(query['state'])):
        return 'TypedDetachedDpStateRequired', None
    state = deepcopy(query['state'])
    if a16 is not None and any(a16 >> int(bit) & 1 != value for bit, value in _accumulator(state).items()):
        return 'ContradictoryAccumulatorAliases', state
    scb = state['registers'].get('scb')
    if scb is not None and any(scb >> int(bit) & 1 != value for bit, value in selectors.items()):
        return 'ContradictoryScbKnowledge', state
    if assumptions['noInterference'] is not True:
        return 'NoInterferencePremiseRequired', state
    if scb is None:
        scb = _scalar(selectors, 3)
        if scb is None:
            return 'SelectedPointingBankUnknown', state
        state['registers']['scb'] = scb
        if not _valid_state(state):
            return 'ContradictorySelectedBankAlias', deepcopy(query['state'])
    if assumptions['dataMapping'] not in MAPS:
        return 'UnqualifiedDpMapping', state
    if a16 is not None:
        # This refines the declared input. It creates no write or new source generation.
        state['registers'].update(al=a16 & 255, ah=a16 >> 8)
        state['registerKnownBits'].clear()
    return None, state


class _Path:
    def __init__(self, state):
        self.state = state
        self.steps, self.reads, self.writes = [], [], []
        self.qualification = None
        self.used = (set(state['generations'].values()) | set(state['registerGenerations'].values())
                     if state is not None else set())

    def result(self, status, pc, reason=None, boundary=None):
        state = self.state
        accumulator = None if state is None else _accumulator(state)
        return {'status': status, 'reason': reason, 'entryClass': ENTRY, 'stopPc': pc, 'stopBoundary': boundary,
                'state': state, 'a16': None if accumulator is None else {
                    'value': _scalar(accumulator, 16), 'knownBits': accumulator},
                'pointer': None if state is None else _pointer(state),
                'steps': self.steps, 'reads': self.reads, 'journal': self.writes,
                'qualification': self.qualification, 'unresolved': list(LIMITS),
                'executionAuthority': dict(AUTHORITY)}

    def fresh(self, pc, names):
        tags = {name: f'M2dj:{pc:04X}:{name.upper()}' for name in names}
        if set(tags.values()) & self.used:
            return None
        self.used.update(tags.values())
        return tags

    def step(self, pc, following, flag=None, taken=None):
        evidence = None if flag is None else {
            'flag': flag, 'value': self.state['registers'].get(flag),
            'generation': self.state['registerGenerations'].get(flag), 'takenWhen': 1}
        self.steps.append({'pc': pc, 'next': following, 'kind': 'Branch' if flag else 'RegisterEffect',
                           'branchTaken': taken, 'predicateEvidence': evidence, 'state': deepcopy(self.state)})

    def assign(self, pc, word, width, flags):
        registers = ('al', 'ah') if width == 16 else ('al',)
        tags = self.fresh(pc, (*registers, *flags))
        if tags is None:
            return False
        for offset, name in enumerate(registers):
            part = _part(word, offset * 8)
            value = _scalar(part, 8)
            self.state['registers'][name] = value
            self.state['registerKnownBits'].pop(name, None)
            if value is None:
                self.state['registerKnownBits'][name] = part
        self.state['registers'].update(flags)
        self.state['registerGenerations'].update(tags)
        return True

    def store_dp(self, pc, bits, source, source_tags):
        view = _pointer(self.state)
        addresses = view['addresses']
        keys = [f'{address:04X}' for address in addresses]
        if not all(key in self.state['memory'] for key in keys):
            return 'SelectedDpBackingBytesMissing'
        if None in view['generations']:
            return 'PointerGenerationMissing'
        tags = self.fresh(pc, ('dp.low', 'dp.high'))
        if tags is None:
            return 'RegisterGenerationCollision'
        parts = [_part(bits, offset) for offset in (0, 8)]
        after = [_scalar(part, 8) for part in parts]
        generations = list(tags.values())
        known = {field: value for field, value in self.state['knownBits'].items() if field[:4] not in keys}
        for key, value, part, generation in zip(keys, after, parts, generations, strict=True):
            self.state['memory'][key] = value
            self.state['generations'][key] = generation
            if value is None:
                known.update({f'{key}.{bit}': v for bit, v in part.items()})
        self.state['knownBits'] = known
        self.writes.append({'ordinal': len(self.writes) + 1, 'pc': pc, 'space': 'DATA',
                            'address': addresses[0], 'widthBits': 16, 'bank': view['bank'],
                            'kind': 'PointingRegisterWordStore', 'valueSource': source,
                            'beforeBytes': view['bytes'], 'afterBytes': after,
                            'beforeKnownBits': view['knownBits'], 'afterKnownBits': bits,
                            'beforeGenerations': view['generations'], 'afterGenerations': generations,
                            'sourceGenerations': source_tags, 'sameValue': None if None in (*view['bytes'], *after)
                            else view['bytes'] == after})
        return None

    def branch(self, pc, flag, yes, no):
        value = self.state['registers'].get(flag)
        if value is None:
            self.step(pc, None, flag)
            return None
        taken = value == 1
        following = yes if taken else no
        self.step(pc, following, flag, taken)
        return following

    def read_indirect(self, pc, assumptions):
        width = 16 if pc == 0x02B7 else 8
        view = _pointer(self.state)
        q = indirect_data_address_qualification({
            'pc': pc, 'space': 'DATA', 'widthBits': width, 'state': self.state,
            'assumptions': assumptions, 'expectedDpGenerations': view['generations'], 'interveningWrites': [],
        })
        self.qualification = q
        if not q['allowed']:
            return self.result('UnqualifiedIndirectDataRead', pc, q['classification'],
                               f'STOP_BEFORE_UNQUALIFIED_INDIRECT_DATA_READ_{pc:04X}')
        bits = q['knownBits']
        if not self.assign(pc, bits, width, {'dd': int(width == 16), 'zf': _zero(bits, width)}):
            return self.result('OutsideVerifiedScope', pc, 'RegisterGenerationCollision')
        self.reads.append({'pc': pc, 'space': 'DATA', 'address': q['effectiveAddress'], 'widthBits': width,
                           'value': q['value'], 'bytes': q['sourceBytes'], 'knownBits': bits,
                           'generations': q['sourceGenerations'], 'kind': 'ConditionalIndirectDataOperand'})
        following = pc + 1
        self.step(pc, following)
        return self.result('ConditionalSourcePrefixEstablished', following,
                           'DownstreamEffectsOutsideScope', f'STOP_BEFORE_UNREVIEWED_{following:04X}')


def detached_02b0_02b2_transform(snapshot):
    """Apply the bounded detached DP path and stop before any unqualified effect."""
    reason, state = _admit(snapshot)
    path = _Path(state)
    if reason:
        return path.result('RefusedSourcePremise', 0x02B0, reason)
    generations = [state['registerGenerations'].get(key) for key in ('al', 'ah')]
    if None in generations:
        return path.result('OutsideVerifiedScope', 0x02B0, 'AccumulatorSourceGenerationMissing')
    reason = path.store_dp(0x02B0, _accumulator(state), 'A16', generations)
    if reason:
        return path.result('OutsideVerifiedScope', 0x02B0, reason)
    path.step(0x02B0, 0x02B1)
    view = _pointer(state)
    bits = view['knownBits']
    if not path.assign(0x02B1, bits, 16, {'dd': 1, 'zf': _zero(bits, 16)}):
        return path.result('OutsideVerifiedScope', 0x02B1, 'RegisterGenerationCollision')
    path.reads.append({'pc': 0x02B1, 'space': 'REGISTER', 'address': view['addresses'][0], 'widthBits': 16,
                       'value': view['value'], 'bytes': view['bytes'], 'knownBits': bits,
                       'generations': view['generations'], 'kind': 'SelectedDpRegisterOperand'})
    path.step(0x02B1, 0x02B2)
    target = path.branch(0x02B2, 'zf', 0x02C2, 0x02B4)
    if target is None:
        return path.result('IndeterminateBranch', 0x02B2, 'WordZeroPredicateUnknown')
    if target == 0x02C2:
        reason = path.store_dp(0x02C2, _bits(0x035C, {}, 16), 'Immediate035C', [])
        if reason:
            return path.result('OutsideVerifiedScope', 0x02C2, reason)
        path.step(0x02C2, 0x02C5)
        return path.read_indirect(0x02C5, snapshot['assumptions'])
    before = _accumulator(state)
    shifted = {str(int(bit) - 1): value for bit, value in before.items() if bit != '0'}
    shifted['15'] = 0
    if not path.assign(0x02B4, shifted, 16, {'cf': before.get('0')}):
        return path.result('OutsideVerifiedScope', 0x02B4, 'RegisterGenerationCollision')
    path.step(0x02B4, 0x02B5)
    target = path.branch(0x02B5, 'cf', 0x02C5, 0x02B7)
    if target is None:
        return path.result('IndeterminateBranch', 0x02B5, 'ShiftCarryPredicateUnknown')
    return path.read_indirect(target, snapshot['assumptions'])
