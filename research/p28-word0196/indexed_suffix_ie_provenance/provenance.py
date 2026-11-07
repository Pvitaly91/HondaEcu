"""Conditional DATA shadow and indexed writer generations within closed scopes."""
from types import MappingProxyType

from enclosing_caller_return.state import input_class, label, need, number, shape, slot, tri

from .wire import result

SHADOW_SCOPE = (0x2566, 0x256B, 0x3F18, 0x3F2C, 0x3FF7, 0x54DD, 0x5CB7)
SUFFIX_SCOPE = (0x5CB4, 0x5CB7, 0x5CB9, 0x5CBB, 0x5CBE, 0x5CC2, 0x5CC6, 0x5CC9, 0x5CCB, 0x5CCD)
SHADOW_WRITERS = MappingProxyType({
    0x00FA: MappingProxyType({0x256B: 0, 0x3F18: 0x02A0, 0x3F2C: 0x00A0, 0x54DD: 0x02A0}),
    0x00F8: MappingProxyType({0x2569: 0, 0x3F16: 0x2BAB, 0x3F2A: 0xA9A3, 0x54E5: 0x2BAB}),
})
SHADOW_FIELDS = ('inputClass', 'address', 'sourcePc', 'generation', 'low', 'high', 'mappingEstablished',
                 'noInterference', 'events', 'claim')
RETENTION_FIELDS = ('inputClass', 'selectedIndex', 'writerPc', 'entry', 'observed', 'requestedGeneration',
                    'page', 'events', 'noInterference', 'claim')
EVENT_KINDS = ('DirectStore', 'IndirectStore', 'FrameStore', 'IndexedAcquisition', 'UnknownWriter')
CLAIMS = ('ConditionalOnly', 'NativeOwner', 'ActualHardware', 'RuntimeAdmission')


def _knowledge(byte):
    if byte['value'] is None:
        return dict(byte['knownBits'])
    return {str(i): (byte['value'] >> i) & 1 for i in range(8)}


def _events(query, *, retention):
    events = query['events']
    need(type(events) is list and len(events) <= 32, 'BoundedWriterEventsRequired')
    fields = ('address', 'widthBits', 'generation')
    if retention:
        fields = (*fields, 'kind', 'value')
    for event in events:
        shape(event, fields, 'ClosedWriterEventRequired')
        need(number(event['address'], 0xFFFF) and label(event['generation'])
             and type(event['widthBits']) is int and event['widthBits'] in (8, 16), 'TypedWriterEventRequired')
        if retention:
            kind, addr = event['kind'], event['address']
            need(type(kind) is str and kind in EVENT_KINDS
                 and number(event['value'], (1 << event['widthBits']) - 1), 'TypedRetentionEventRequired')
            if kind == 'UnknownWriter':
                need(addr is None and event['value'] is None, 'UnknownWriterCannotOwnAnAddressOrValue')
            if kind == 'IndexedAcquisition':
                need(event['widthBits'] == 8 and (addr is None or 0x03C6 <= addr <= 0x03CD),
                     'IndexedWriterFootprintMismatch')
    return events


def _candidate_footprint(event):
    addr = event['address']
    if addr is not None and event['widthBits'] == 16:
        return addr & 0xFFFE
    return addr


def _overlaps(event, targets):
    addr = _candidate_footprint(event)
    return addr is not None and any(addr <= target < addr + event['widthBits'] // 8 for target in targets)


def _reused(events, generation):
    generations = [event['generation'] for event in events if event['generation'] is not None]
    return generation in generations or len(generations) != len(set(generations))


def _claim(query):
    input_class(query['inputClass'])
    need(type(query['claim']) is str and query['claim'] in CLAIMS and tri(query['noInterference']),
         'TypedConditionalOwnershipClaimRequired')


def _shadow_admission(query, address, events):
    outside, unknown = 'OutsideVerifiedScope', 'IndeterminateObligation'
    if query['claim'] != 'ConditionalOnly':
        return outside, 'NonConditionalShadowClaim'
    if query['address'] != address:
        return outside, 'WrongShadowAddress'
    if query['mappingEstablished'] is False:
        return outside, 'UnsupportedShadowMapping'
    if query['mappingEstablished'] is None:
        return unknown, 'ShadowMappingUnestablished'
    if query['sourcePc'] is not None and query['sourcePc'] not in SHADOW_WRITERS[address]:
        return outside, 'UnreviewedShadowWriter'
    generation = query['generation']
    low, high = query['low']['generation'], query['high']['generation']
    if None in (generation, low, high):
        return unknown, 'ShadowGenerationMissing'
    if not generation == low == high:
        return outside, 'StaleShadowGeneration'
    if _reused(events, generation):
        return outside, 'ShadowGenerationReused'
    if any(_overlaps(event, (address, address + 1)) for event in events):
        return unknown, 'OverlappingShadowWriter'
    if query['noInterference'] is not True or any(event['address'] is None for event in events):
        return unknown, 'ShadowInterferenceUnresolved'
    return None


def shadow_word(query, address):
    """Admit a declared same-generation pair, preserving any missing value bits."""
    shape(query, SHADOW_FIELDS, 'ClosedShadowLineageQueryRequired')
    _claim(query)
    need(address in SHADOW_WRITERS and number(query['address'], 0xFFFF)
         and number(query['sourcePc'], 0xFFFF) and label(query['generation'])
         and tri(query['mappingEstablished']), 'TypedShadowLineageRequired')
    for part in ('low', 'high'):
        slot(query[part])
    events = _events(query, retention=False)
    source = query['sourcePc']
    state = {'address': address, 'word': None, 'knownBits': {}, 'zf': None, 'generation': None,
             'candidateSourcePc': source, 'nativeGeneration': None}
    refusal = _shadow_admission(query, address, events)
    if refusal is not None:
        return refusal[0], refusal[1], state
    bits = _knowledge(query['low'])
    bits.update({str(8 + int(bit)): value for bit, value in _knowledge(query['high']).items()})
    word = sum(value << int(bit) for bit, value in bits.items()) if len(bits) == 16 else None
    if source is not None:
        expected = SHADOW_WRITERS[address][source]
        if any((expected >> int(bit)) & 1 != value for bit, value in bits.items()):
            return 'OutsideVerifiedScope', 'ReviewedShadowValueMismatch', state
        if word is None:
            return 'IndeterminateObligation', 'ReviewedShadowValueUnbound', state
    state.update(word=word, knownBits=bits, zf=0 if 1 in bits.values() else 1 if word == 0 else None,
                 generation=query['generation'])
    reason = 'QualifiedSymbolicShadowWord' if source is None else 'ReviewedShadowWriterRetained'
    return 'CompleteConditional', reason, state


def _unresolved(fixed, status, reason):
    return fixed if status == 'CompleteConditional' else (*fixed, reason)


def data00fa_shadow_lineage(query):
    """Separate the two-reader source relation from current native ownership."""
    status, reason, state = shadow_word(query, 0x00FA)
    return result(status, source_scope=SHADOW_SCOPE, state=state, stop='STOP_BEFORE_INDEXED_CONTINUATION_5CB7',
                  generations={'shadow': state['generation']}, reason=reason,
                  obligations=('ExactLittleEndianShadowPair', 'CurrentGenerationAndNoInterference',
                               'SharedSlotOnlyWithConfigurationReader'),
                  unresolved=_unresolved(('NativeShadowGenerationUnestablished',
                                          'ConfigurationReaderToSuffixContinuityUnestablished'), status, reason))


def _overwriting_event(events, entry_value):
    for event in events:
        if not _overlaps(event, (0x03CB,)):
            continue
        addr, value = _candidate_footprint(event), event['value']
        target_byte = None if value is None else (value >> (8 * (0x03CB - addr))) & 0xFF
        return {'kind': event['kind'], 'address': addr, 'widthBits': event['widthBits'],
                'generation': event['generation'], 'value': target_byte,
                'sameValue': None if None in (target_byte, entry_value) else target_byte == entry_value}
    return None


def _retention_admission(query, events, page, competing):
    outside, unknown = 'OutsideVerifiedScope', 'IndeterminateObligation'
    if query['claim'] != 'ConditionalOnly':
        return outside, 'NonConditionalRetentionClaim'
    if query['writerPc'] not in (None, 0x5CB4):
        return outside, 'UnreviewedIndexedWriter'
    if query['selectedIndex'] not in (None, 5):
        return outside, 'IndexDoesNotWriteData03cb'
    if page is not None and page & 0xFF:
        return outside, 'InvalidDataPage'
    if query['writerPc'] is None or query['selectedIndex'] is None:
        return unknown, 'IndexedWriterUnestablished'
    entry, observed, requested = query['entry']['generation'], query['observed']['generation'], query['requestedGeneration']
    if None in (entry, observed, requested):
        return unknown, 'Data03cbGenerationMissing'
    if requested != entry:
        return outside, 'StaleData03cbGeneration'
    if _reused(events, entry):
        return outside, 'Data03cbGenerationReused'
    if competing is not None:
        return unknown, 'CompetingData03cbWriter'
    if query['noInterference'] is not True or any(event['address'] is None for event in events):
        return unknown, 'Data03cbInterferenceUnresolved'
    if observed != entry:
        return unknown, 'Data03cbGenerationChanged'
    original, current = _knowledge(query['entry']), _knowledge(query['observed'])
    if any(original[bit] != current[bit] for bit in original.keys() & current.keys()):
        return outside, 'Data03cbValueGenerationConflict'
    return 'CompleteConditional', 'ConditionalData03cbGenerationRetained'


def data03cb_suffix_retention(query):
    """Check preservation of one declared generation against ordered competing footprints."""
    shape(query, RETENTION_FIELDS, 'ClosedSuffixRetentionQueryRequired')
    _claim(query)
    need(number(query['writerPc'], 0xFFFF) and number(query['selectedIndex'], 7)
         and number(query['page'], 0xFFFF) and label(query['requestedGeneration']), 'TypedSuffixRetentionRequired')
    entry, observed = slot(query['entry']), slot(query['observed'])
    events = _events(query, retention=True)
    competing = _overwriting_event(events, entry['value'])
    page = query['page']
    status, reason = _retention_admission(query, events, page, competing)
    retained = entry['generation'] if status == 'CompleteConditional' else None
    state = {'localSuffixRetention': True,
             'offPageWrite': {'address': None if page is None or page & 0xFF else page | 0x5A, 'widthBits': 16},
             'entryGeneration': entry['generation'], 'observedGeneration': observed['generation'],
             'retainedGeneration': retained, 'nativeReachingDefinition': None}
    return result(status, source_scope=SUFFIX_SCOPE, state=state, stop='STOP_BEFORE_RT_5CCD',
                  generations={'data03cb': retained}, reason=reason, competingWrite=competing,
                  obligations=('IndexedWriterAt5CB4Index5', 'LocalSuffixWritesDisjointFromData03cb',
                               'ExcludeCompetingAndAsynchronousWrites'),
                  unresolved=_unresolved(('NativeData03cbOwnerUnestablished',
                                          'CallerToModeContinuityUnestablished'), status, reason))
