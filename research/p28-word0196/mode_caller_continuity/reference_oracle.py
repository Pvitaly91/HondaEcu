"""Independent source equations and immutable frozen references, never new models."""
from copy import deepcopy

from tx_ack_configuration_provenance.reference_oracle import (
    Reference as ParentReference, _snapshot as parent_checked, _known, _values,
    _consensus, tx_configuration_reader as parent_reader,
    mode_bit1_producer as parent_producer,
)
from tx_ack_configuration_provenance.corpus import READBACK_KEYS as OLD_READBACK_KEYS
from stbuf_stcon_transmit_source.reference_oracle import (
    stcon_configuration as parent_config, _formal, AUTHORITY,
    ADDRESSES as CS_ADDRESSES, _source,
)
from post_consumer_continuation.reference_oracle import _slot, _domain, _nullable_bool, stbuf_boundary_obligations as frozen_stbuf
from payload_consumer_tail.reference_oracle import _bits, _memory_bits, _zero, _integer, _generation, _input_class, canonical
from .corpus import (ADDRESSES, OLD_ADDRESSES, READBACK_KEYS, WRITER_SITES, MODE_SITES,
    CONFIG_SITES, READER_SITES, REACHING_SITES, JOIN_SITES, ENTRIES, PATHS, STAGES, cases)
from .primary_sources import SOURCE_BINDING, APPLICABILITY, binding_reason

STATE_KEYS = ('memory', 'knownBits', 'registers', 'generations', 'registerKnownBits', 'configurationIntents', 'sfrReadbacks')
SPECIFIC = ('ConditionalSourceReconstructionOnly', 'ActualNativeContinuityNotEstablished', 'Stbuf2995NotPerformed')


def _project(snapshot, cs=False):
    value = {key: deepcopy(snapshot[key]) for key in ('inputClass', *STATE_KEYS, 'assumptions')}
    addresses = CS_ADDRESSES if cs else OLD_ADDRESSES
    for key in ('memory', 'generations'):
        value[key] = {address: value[key][address] for address in addresses}
    value['knownBits'] = {key: bit for key, bit in value['knownBits'].items() if key[:4] in addresses}
    if cs:
        value.pop('sfrReadbacks')
    else:
        value['sfrReadbacks'] = {key: value['sfrReadbacks'][key] for key in OLD_READBACK_KEYS}
    return value


def _snapshot(query, producer=False):
    shape = {'inputClass', *STATE_KEYS, 'assumptions'} | ({'entry'} if producer else set())
    if type(query) is not dict or set(query) != shape:
        raise ValueError('ReferenceSnapshotShape')
    if producer and (type(query['entry']) is not str or query['entry'] not in ENTRIES):
        raise ValueError('ReferenceModeEntry')
    for field in ('memory', 'generations'):
        if type(query[field]) is not dict or set(query[field]) != set(ADDRESSES):
            raise ValueError('ReferenceDataShape')
    if any(not _integer(v, 255) for v in query['memory'].values()) or any(not _generation(v) for v in query['generations'].values()):
        raise ValueError('ReferenceDataType')
    if type(query['knownBits']) is not dict:
        raise ValueError('ReferenceKnownBits')
    for key, bit in query['knownBits'].items():
        if (type(key) is not str or len(key) != 6 or key[:4] not in ADDRESSES or key[4] != '.'
                or key[-1] not in '01234567' or type(bit) is not int or bit not in (0, 1)):
            raise ValueError('ReferenceKnownBitType')
        raw = query['memory'][key[:4]]
        if raw is not None and (raw >> int(key[-1])) & 1 != bit:
            raise ValueError('ReferenceKnownBitContradiction')
    if type(query['sfrReadbacks']) is not dict or set(query['sfrReadbacks']) != set(READBACK_KEYS):
        raise ValueError('ReferenceReadbackShape')
    for item in query['sfrReadbacks'].values():
        _slot(item)
    parent_checked(_project(query))
    return deepcopy(query)


def _pointer(state, base, prefix):
    bank = state['registers']['scb']
    if bank is None:
        return {'dataAddress': None, 'value': None, 'knownBits': {}}
    address = base + 8 * bank
    bits = {8 * part + bit: value for part in range(2) for bit, value in _memory_bits(state, address + part).items()}
    return {'dataAddress': address, 'value': sum(bits[n] << n for n in range(16)) if len(bits) == 16 else None,
        'knownBits': {prefix + '.' + str(bit): value for bit, value in bits.items()}}


def _expand(child, held):
    result = deepcopy(held)
    for key in ('memory', 'generations', 'registers', 'configurationIntents', 'sfrReadbacks'):
        result[key].update(deepcopy(child.get(key, {})))
    result['knownBits'] = {key: bit for key, bit in held['knownBits'].items() if key[:4] not in child['memory']}
    result['knownBits'].update(deepcopy(child['knownBits']))
    result['registerKnownBits'] = deepcopy(child['registerKnownBits'])
    return result


class Reference(ParentReference):
    def __init__(self, snapshot, procedure, scope, specific=(), producer=False):
        original = _snapshot(snapshot, producer)
        super().__init__(_project(original))
        self.original, self.name, self.scope = original, procedure, list(scope)
        self.specific = [*SPECIFIC, *specific]
        self.state = {key: deepcopy(original[key]) for key in STATE_KEYS}
        self.inherited = []

    def result(self, boundary, outcome=None, status='CompleteConditional', reason='VerifiedSelectedSourcePath'):
        value = super().result(boundary, outcome, status, reason)
        value.update(x1State=_pointer(self.state, 0x80, 'X1'), inheritedResults=deepcopy(self.inherited))
        return value

    def read(self, *args, **kwargs):
        value = super().read(*args, **kwargs)
        self.reads[-1]['stage'] = self.name
        return value

    def symbolic_read(self, *args, **kwargs):
        value = super().symbolic_read(*args, **kwargs)
        self.reads[-1]['stage'] = self.name
        return value

    def step(self, *args, **kwargs):
        super().step(*args, **kwargs)
        self.steps[-1].update(stage=self.name, afterX1State=_pointer(self.state, 0x80, 'X1'))

    def write(self, *args, **kwargs):
        super().write(*args, **kwargs)
        self.journal[-1].update(stage=self.name, stageOrdinal=self.journal[-1]['ordinal'])
        self.intermediate[-1].update(stage=self.name, stageOrdinal=self.intermediate[-1]['afterOrdinal'])

    def current(self, entry=None):
        q = {'inputClass': self.original['inputClass'], 'assumptions': deepcopy(self.original['assumptions']), **deepcopy(self.state)}
        if entry is not None:
            q['entry'] = entry
        return q

    def absorb(self, child):
        self.inherited.append(deepcopy(child))
        held, offset = deepcopy(self.state), len(self.journal)
        for event in child['journal']:
            row = deepcopy(event); ordinal = row['ordinal']
            row.update(ordinal=offset + ordinal, stage=child['procedure'], stageOrdinal=ordinal)
            self.journal.append(row)
        for item in child['intermediateStates']:
            row = deepcopy(item); ordinal = row['afterOrdinal']
            row.update(afterOrdinal=offset + ordinal, stage=child['procedure'], stageOrdinal=ordinal,
                state=_expand(row['state'], held))
            self.intermediate.append(row)
        for item in child['reads']:
            self.reads.append({**deepcopy(item), 'stage': child['procedure']})
        for item in child['steps']:
            row = deepcopy(item)
            row['afterRegisters'] = {**deepcopy(held['registers']), **row['afterRegisters']}
            row.update(stage=child['procedure'])
            row.setdefault('afterX1State', _pointer(held, 0x80, 'X1'))
            self.steps.append(row)
        self.state = _expand(child['state'], held)
        for reason in child['unresolvedConstraints']:
            from payload_consumer_tail.reference_oracle import COMMON
            if reason not in COMMON and reason not in self.specific:
                self.specific.append(reason)

    def literal_word(self, pc, value, next_pc):
        self.register_byte('al', _bits(value & 255)); self.register_byte('ah', _bits(value >> 8))
        self.registers.update(dd=1, zf=int(value == 0)); self.step(pc, next_pc)

    def x1_read(self, pc):
        address = 0x80 + self.registers['scb'] * 8
        self.read(pc, address, 16, 'ARCHITECTURAL_ADDRESS_DEPENDENCY', 'PointingRegisterAlias')
        return _pointer(self.state, 0x80, 'X1')['value']

    def branch_stop(self, pc, bit, yes, no):
        self.step(pc, None if bit is None else yes if bit else no, 'Branch', None if bit is None else bool(bit))
        return self.result(pc, status='IndeterminateBranch', reason='UnknownBranchPredicate') if bit is None else None


def data03cb_indexed_writer(snapshot):
    r = Reference(snapshot, 'data03cb_indexed_writer', WRITER_SITES)
    selected = None
    def result(boundary, outcome=None, status='CompleteConditional', reason='VerifiedSelectedSourcePath'):
        return {**r.result(boundary, outcome, status, reason), 'selectedIndex': selected,
            'conditionalData03cbWriterEstablished': status == 'CompleteConditional' and selected == 5}
    failure = r.admit(0x5CA5)
    if failure is not None:
        return {**failure, 'selectedIndex': None, 'conditionalData03cbWriterEstablished': False}
    for pc, address, nxt in ((0x5CA5, 0x24, 0x5CA7),):
        failure = r.byte_load(pc, address, nxt)
        if failure is not None:
            return {**failure, 'selectedIndex': selected, 'conditionalData03cbWriterEstablished': False}
    values = _values(r.register_byte_bits('al'))
    r.register_byte('al', _known({((v & 15) << 4) | (v >> 4) for v in values})); r.step(0x5CA7, 0x5CA8)
    values = _values(r.register_byte_bits('al')); r.registers['cf'] = _consensus(v & 1 for v in values)
    r.register_byte('al', _known({v >> 1 for v in values})); r.step(0x5CA8, 0x5CA9)
    r.mask_al(0x5CA9, 7, 0x5CAB); selected = r.registers['al']
    r.register_byte('ah', _bits(0)); r.registers['dd'] = 1; r.step(0x5CAB, 0x5CAC)
    bank = r.registers['scb']
    if bank is None:
        return result(0x5CAC, status='OutsideVerifiedScope', reason='PointerBankNotEstablished')
    address = 0x80 + 8 * bank
    partial = {f'{address:04X}.{bit}': v for bit, v in r.register_byte_bits('al').items()} if r.registers['al'] is None else None
    r.write(0x5CAC, address, [r.registers['al'], r.registers['ah']], 'PointingRegisterWrite', 'A', partial=partial)
    r.step(0x5CAC, 0x5CAD)
    for load, sfr, store, base, nxt in ((0x5CAD, 0x63, 0x5CAF, 0x3CE, 0x5CB2), (0x5CB2, 0x61, 0x5CB4, 0x3C6, 0x5CB7)):
        failure = r.byte_load(load, sfr, store)
        if failure is not None:
            return {**failure, 'selectedIndex': selected, 'conditionalData03cbWriterEstablished': False}
        index = r.x1_read(store)
        if index is None:
            return result(store, status='IndeterminateObligation', reason='IndexedAddressNotEstablished')
        if not 0 <= index <= 7:
            return result(store, status='OutsideVerifiedScope', reason='IndexedAddressOutsideReviewedRange')
        target = base + index
        partial = {f'{target:04X}.{bit}': v for bit, v in r.register_byte_bits('al').items()} if r.registers['al'] is None else None
        r.write(store, target, [r.registers['al']], 'IndexedStore', 'AL', partial=partial); r.step(store, nxt)
    return result(0x5CB7, 'IndexedAdcBytesStored')


def mode_producer_extended(snapshot):
    r = Reference(snapshot, 'mode_producer_extended', MODE_SITES, producer=True)
    entry = snapshot['entry']; first = 0x60BD if entry == 'At60BD' else 0x60C9 if entry == 'Compare3cb' else 0x60D2
    failure = r.admit(first)
    if failure is not None: return failure
    if entry == 'At60BD':
        if r.registers['lrb'] != 0x41: return r.outside(0x60BD, 'LocalBank0208NotEstablished')
        r.read(0x60BD, 0x208); r.compare(_values(_memory_bits(r.state, 0x208)), 0); r.step(0x60BD, 0x60C0)
        zf = r.registers['zf']; failure = r.branch_stop(0x60C0, zf, 0x60C9, 0x60C2)
        if failure is not None: return failure
        if zf == 0: return r.outside(0x60C2, 'ProgramTableSourceNotAdmitted')
        entry = 'Compare3cb'
    child_query = _project(r.current()); child_query['entry'] = entry
    child = parent_producer(child_query); r.absorb(child)
    if child['status'] != 'CompleteConditional':
        return r.result(child['boundary'], child['outcome'], child['status'], child['reason'])
    r.literal_word(0x60D7, 0x700, 0x60DA)
    lrb = r.registers['lrb']
    if lrb is None or lrb & 0x1FE0 != 0x40: return r.outside(0x60DA, 'LocalPage0216NotEstablished')
    r.read(0x60DA, 0x216); bit = r.bit(0x216, 3); failure = r.branch_stop(0x60DA, bit, 0x60E0, 0x60DD)
    if failure is not None: return failure
    if bit == 0: r.literal_word(0x60DD, 0x500, 0x60E0)
    failure = r.pointer_write(0x60E0, 0x382, 0x60E3)
    if failure is not None: return failure
    r.pointer_read(0x60E3); r.store_a(0x60E3, 0x382, word=True); r.step(0x60E3, 0x60E4)
    return r.result(0x60E4, 'ConditionalModeWordPrepared')


def configuration_caller(snapshot):
    r = Reference(snapshot, 'configuration_caller', CONFIG_SITES)
    failure = r.admit(0x2869)
    if failure is not None: return failure
    if r.registers['lrb'] != 0x41: return r.outside(0x2869, 'LocalPage02cdNotEstablished')
    r.write(0x2869, 0x2CD, [0x32], 'ImmediateStore', 'Literal'); r.step(0x2869, 0x286D)
    child = parent_config(_project(r.current(), cs=True)); r.absorb(child)
    if child['status'] != 'CompleteConditional':
        return r.result(child['boundary'], child['outcome'], child['status'], child['reason'])
    failure = r.pointer_write(0x288E, 0x4700, 0x2891)
    if failure is not None: return failure
    return r.result(0x2891, 'ConfigurationIntentsPreparedBeforeExternalRead')


def configuration_reader_caller(snapshot):
    r = Reference(snapshot, 'configuration_reader_caller', READER_SITES)
    failure = r.admit(0x3FCC)
    if failure is not None: return failure
    failure = r.byte_load(0x3FCC, 0x58, 0x3FCE)
    if failure is not None: return failure
    r.mask_al(0x3FCE, 0x5F, 0x3FD0)
    r.compare(_values(r.register_byte_bits('al')), 0x10); r.step(0x3FD0, 0x3FD2)
    taken = None if r.registers['zf'] is None else 1 - r.registers['zf']
    failure = r.branch_stop(0x3FD2, taken, 0x3FB1, 0x3FD4)
    if failure is not None: return failure
    boundary = 0x3FB1
    if not taken:
        child = parent_reader(_project(r.current())); r.absorb(child)
        if child['status'] != 'CompleteConditional':
            return r.result(child['boundary'], child['outcome'], child['status'], child['reason'])
        boundary = child['boundary']
    if boundary == 0x3FB1:
        r.write(0x3FB1, 0xF5, [0x50], 'ImmediateStore', 'Literal'); r.step(0x3FB1, 0x3FB5)
        return r.result(0x3FB5, 'FailureDiagnosticPrepared')
    r.load_word(0x3FF7, 0xFA, 0x3FF9)
    return r.result(0x3FF9, 'ReaderAcceptedBeforeIeWrite')


def _shape(q, keys):
    if type(q) is not dict or set(q) != set(keys): raise ValueError('ReferenceFormalShape')
    _input_class(q['inputClass']); _source(q['sourceBinding'])
    if q['claim'] not in ('ConditionalOnly', 'NativeOwner', 'ActualHardware', 'RuntimeAdmission'): raise ValueError('ReferenceClaim')


def _reaching_checked(q):
    _shape(q, ('inputClass', 'sourceBinding', 'initial', 'events', 'path', 'entryGeneration', 'requestedGeneration', 'noInterference', 'claim'))
    _slot(q['initial'])
    if q['path'] not in PATHS or not _nullable_bool(q['noInterference']) or any(not _generation(q[k]) for k in ('entryGeneration', 'requestedGeneration')):
        raise ValueError('ReferenceReachingFields')
    if type(q['events']) is not list or len(q['events']) > 32: raise ValueError('ReferenceEventsBound')
    shapes = {'IndexedWriter': {'kind', 'id', 'sourcePc', 'p2', 'adcr0h', 'generation', 'scb'},
        'AlternateStore': {'kind', 'id', 'address', 'widthBits', 'value', 'generation'}, 'UnknownWriter': {'kind', 'id'}}
    seen = set()
    for e in q['events']:
        if (type(e) is not dict or type(e.get('kind')) is not str or e['kind'] not in shapes or set(e) != shapes[e['kind']]
                or type(e['id']) is not str or not e['id'] or e['id'] in seen): raise ValueError('ReferenceEventShape')
        seen.add(e['id'])
        if e['kind'] == 'IndexedWriter':
            _slot(e['p2']); _slot(e['adcr0h'])
            if not _integer(e['sourcePc'], 65535) or not _integer(e['scb'], 7): raise ValueError('ReferenceIndexedDescriptor')
        if e['kind'] == 'AlternateStore':
            if (not _integer(e['address'], 65535) or type(e['widthBits']) is not int or e['widthBits'] not in (8, 16)
                    or not _integer(e['value'], (1 << e['widthBits']) - 1)): raise ValueError('ReferenceAlternateDescriptor')
        if e['kind'] != 'UnknownWriter' and not _generation(e['generation']): raise ValueError('ReferenceEventGeneration')


def data03cb_reaching_definitions(query):
    _reaching_checked(query)
    slot, kind, journal, history = deepcopy(query['initial']), 'InitialUnbound', [], []
    labels = {slot['generation']} - {None}
    boundary = None; relation, status, reason = 'ConfirmedLocalWriterRelation', 'CompleteConditional', 'ReviewedIndexedWriterRelation'
    error = binding_reason(query['sourceBinding'])
    if query['claim'] != 'ConditionalOnly': relation, status, reason = 'SourceConflict', 'OutsideVerifiedScope', 'NativeOwnershipClaimNotEstablished'
    elif error: relation, status, reason = 'SourceConflict', 'OutsideVerifiedScope', error
    else:
        for index, e in enumerate(query['events']):
            refusal = None
            if e['kind'] == 'IndexedWriter':
                if e['sourcePc'] != 0x5CB4: refusal = 'UnreviewedIndexedWriter'
                elif e['scb'] is None: refusal = 'SelectedX1BankNotEstablished'
            if refusal is None and e['kind'] != 'UnknownWriter' and e['generation'] is not None and e['generation'] in labels:
                refusal = 'WriterGenerationReused'
            if refusal:
                relation, status, reason, boundary = 'SourceConflict', 'OutsideVerifiedScope', refusal, index
                break
            before = deepcopy(slot); address, width, value, overlap = None, None, None, None
            if e['kind'] == 'IndexedWriter':
                selected = _consensus(v >> 5 for v in _domain(e['p2']))
                address = None if selected is None else 0x3C6 + selected
                width, value = 8, e['adcr0h']['value']
                overlap = None if address is None else address == 0x3CB
                if overlap:
                    slot = deepcopy(e['adcr0h']); slot['generation'] = e['generation']; kind = 'ReviewedIndexedWriter'
                elif overlap is None:
                    slot = {'value': None, 'knownBits': {}, 'generation': None}; kind = 'UnknownIndexedWriter'
            elif e['kind'] == 'AlternateStore':
                address, width, value = e['address'], e['widthBits'], e['value']
                if address is not None and width == 16: address &= 0xFFFE
                overlap = None if address is None else address <= 0x3CB < address + width // 8
                if overlap:
                    byte = None if value is None else (value >> (8 * (0x3CB - address))) & 255
                    slot = {'value': byte, 'knownBits': {}, 'generation': e['generation']}; kind = 'AlternateStore'
                elif overlap is None:
                    slot = {'value': None, 'knownBits': {}, 'generation': None}; kind = 'UnknownWriter'
            else:
                slot = {'value': None, 'knownBits': {}, 'generation': None}; kind = 'UnknownWriter'
            if e['kind'] != 'UnknownWriter' and e['generation'] is not None: labels.add(e['generation'])
            same = before['value'] == slot['value'] if overlap is True and before['value'] is not None and slot['value'] is not None else None
            journal.append({'ordinal': len(journal) + 1, 'eventId': e['id'], 'kind': e['kind'],
                'sourcePc': 0x5CB4 if e['kind'] == 'IndexedWriter' else None, 'address': address,
                'widthBits': width, 'declaredValue': value, 'beforeSlot': before, 'afterSlot': deepcopy(slot),
                'targetOverlap': overlap, 'sameDeclaredValue': same, 'effectClass': 'DeclaredSourceEffects_NotRuntimeObservations'})
            history.append({'eventId': e['id'], 'eventIndex': index, 'state': {'lastSlot': deepcopy(slot), 'lastKind': kind}})
        if status == 'CompleteConditional':
            if query['noInterference'] is not True or kind in ('UnknownWriter', 'UnknownIndexedWriter'):
                relation, status, reason = 'UnknownInterference', 'IndeterminateObligation', 'InterferenceNotExcluded'
            elif kind == 'InitialUnbound': relation, status, reason = 'MissingGeneration', 'IndeterminateObligation', 'NoReviewedWriterGeneration'
            elif kind != 'ReviewedIndexedWriter': relation, status, reason = 'CompetingWriter', 'IndeterminateObligation', 'CompetingData03cbWriter'
            elif any(v is None for v in (slot['generation'], query['entryGeneration'], query['requestedGeneration'])):
                relation, status, reason = 'MissingGeneration', 'IndeterminateObligation', 'GenerationObligationMissing'
            elif slot['generation'] != query['entryGeneration']: relation, status, reason = 'CompetingWriter', 'IndeterminateObligation', 'EntryGenerationReplaced'
            elif slot['generation'] != query['requestedGeneration']: relation, status, reason = 'StaleGeneration', 'IndeterminateObligation', 'StaleRequestedGeneration'
            elif query['path'] not in PATHS[:2]: relation, status, reason = 'ReachingPathUnestablished', 'IndeterminateObligation', 'SourcePathTo60ccNotEstablished'
            elif query['path'] == 'WriterWindowRetention': relation, reason = 'ConditionalWriterRetained', 'ConditionalLocalWriterRetained'
    state = {'lastSlot': slot, 'lastKind': kind, 'reachingDefinitions': {'path': query['path'],
        'entryGeneration': query['entryGeneration'], 'requestedGeneration': query['requestedGeneration'],
        'currentGeneration': slot['generation'], 'relation': relation}, 'actualNativeData03cbOwner': None}
    value = _formal(query, 'data03cb_reaching_definitions', state, REACHING_SITES, status, reason,
        [*SPECIFIC, 'NativeData03cbOwnerNotEstablished', 'SourceReachingPathBeyondLocalWindowUnestablished'],
        'ConditionalData03cbReachingDefinitions', boundary=boundary)
    value.update(journal=journal, intermediateStates=history)
    return value


def cross_block_source_join(query):
    _shape(query, ('inputClass', 'sourceBinding', 'snapshot', 'modeEntry', 'stageOrder', 'handoffs', 'noInterference', 'stbufQuery', 'claim'))
    _snapshot(query['snapshot'])
    if query['snapshot']['inputClass'] != query['inputClass'] or type(query['stbufQuery']) is not dict or query['stbufQuery'].get('inputClass') != query['inputClass']:
        raise ValueError('ReferenceNestedInputClass')
    if query['modeEntry'] not in ENTRIES or not _nullable_bool(query['noInterference']): raise ValueError('ReferenceJoinFields')
    if type(query['stageOrder']) is not list or len(query['stageOrder']) > 8 or any(type(v) is not str or v not in STAGES for v in query['stageOrder']): raise ValueError('ReferenceStageOrderShape')
    if type(query['handoffs']) is not dict or set(query['handoffs']) != {'writerToMode', 'modeToConfiguration', 'configurationToReader'} or any(not _nullable_bool(v) for v in query['handoffs'].values()): raise ValueError('ReferenceHandoffs')
    stbuf = frozen_stbuf(query['stbufQuery'])
    r = Reference(query['snapshot'], 'cross_block_source_join', JOIN_SITES,
        ('ExplicitHandoffsAreNotNativeContinuity', 'ReaderTo2995PathNotEstablished'))
    edges = []
    def result(boundary, outcome=None, status='CompleteConditional', reason='VerifiedSelectedSourcePath'):
        output = r.result(boundary, outcome, status, reason)
        output['state'].update(sourceEdges=deepcopy(edges), actualNativeContinuity=None,
            actualNativeData03cbOwner=None, actualCurrentStconOwner=None)
        output['stbufObligations'] = deepcopy(stbuf)
        return output
    error = binding_reason(query['sourceBinding'])
    if query['claim'] != 'ConditionalOnly': return result(None, status='OutsideVerifiedScope', reason='NativeOwnershipClaimNotEstablished')
    if error: return result(None, status='OutsideVerifiedScope', reason=error)
    if query['stageOrder'] != list(STAGES): return result(None, status='OutsideVerifiedScope', reason='UnreviewedStageOrder')
    if stbuf['status'] == 'OutsideVerifiedScope': return result(0x5CA5, status='OutsideVerifiedScope', reason='NestedStbufObligationRefused')
    if query['noInterference'] is not True: return result(None, status='IndeterminateObligation', reason='CrossBlockInterferenceNotExcluded')
    failure = r.admit(0x5CA5)
    if failure is not None: return result(failure['boundary'], status=failure['status'], reason=failure['reason'])
    boundary = None
    operations = (data03cb_indexed_writer, mode_producer_extended, configuration_caller, configuration_reader_caller)
    for index, operation in enumerate(operations):
        if index:
            key = ('writerToMode', 'modeToConfiguration', 'configurationToReader')[index - 1]
            premise = query['handoffs'][key]
            edges.append({'edge': key, 'premise': premise,
                'classification': 'ExplicitStateHandoffPremise' if premise is True else 'BlockedByNativeContinuity',
                'nativeContinuityEstablished': False, 'fromBoundary': boundary,
                'missingProof': ['ActualCallReturnFrame', 'NativeScheduling', 'InterveningWriterExclusion']})
            if premise is not True:
                return result(boundary, status='OutsideVerifiedScope' if premise is False else 'IndeterminateObligation',
                    reason='HandoffPremiseRejected' if premise is False else 'HandoffPremiseNotEstablished')
        child = operation(r.current(query['modeEntry'] if index == 1 else None)); r.absorb(child); boundary = child['boundary']
        if child['status'] != 'CompleteConditional': return result(boundary, child['outcome'], child['status'], child['reason'])
        if index == 0 and not child['conditionalData03cbWriterEstablished']:
            return result(boundary, status='IndeterminateObligation', reason='IndexedWriterDidNotEstablishData03cb')
    return result(boundary, 'ConditionalSoftwareCompositionOnly')


OPERATIONS = {f.__name__: f for f in (data03cb_indexed_writer, mode_producer_extended,
    configuration_caller, configuration_reader_caller, data03cb_reaching_definitions, cross_block_source_join)}


def evaluate(case):
    return OPERATIONS[case['operation']](deepcopy(case['input']))


def record(case, output):
    state = output['state']
    generations = {'data': deepcopy(state.get('generations')),
        'softwareIntents': {key: slot['generation'] for key, slot in state['configurationIntents'].items()} if 'configurationIntents' in state else None,
        'suppliedReadbacks': {key: slot['generation'] for key, slot in state['sfrReadbacks'].items()} if 'sfrReadbacks' in state else None,
        'writerEvents': [{'ordinal': e['ordinal'], 'before': deepcopy(e.get('beforeGeneration')), 'after': deepcopy(e.get('afterGeneration'))} for e in output['journal']],
        'reachingDefinitions': deepcopy(state.get('reachingDefinitions'))}
    return {'caseId': case['id'], 'operation': case['operation'], 'input': deepcopy(case['input']), 'output': deepcopy(output),
        'sourceScope': deepcopy(output['sourceScope']), 'sourceIdentities': deepcopy(SOURCE_BINDING),
        'evidenceClass': 'StaticRomSoftwareEffect' if case['operation'] in tuple(OPERATIONS)[:4] else 'ConditionalSoftwareRelationship',
        'applicability': APPLICABILITY,
        'branchOutcome': [{'pc': step['pc'], 'taken': step['branchTaken'], 'next': step['next']} for step in output['steps'] if step['kind'] == 'Branch'],
        'state': deepcopy(state), 'reads': deepcopy(output['reads']), 'orderedWrites': deepcopy(output['journal']),
        'generations': generations, 'intermediateStates': deepcopy(output['intermediateStates']),
        'unresolvedConstraints': deepcopy(output['unresolvedConstraints']), 'stopBoundary': output['stopBoundary'],
        'executionAuthority': {key: deepcopy(output[key]) for key in AUTHORITY}}


def canonical_records():
    for case in cases():
        yield canonical(record(case, evaluate(case)))
