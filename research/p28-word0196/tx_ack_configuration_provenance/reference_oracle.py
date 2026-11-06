"""Independently derived source equations; never imports the new mathematical model."""
from copy import deepcopy

from payload_consumer_tail.reference_oracle import (
    Reference as FrozenEffects, COMMON, _bits, _memory_bits, _zero, _integer,
    _generation, _input_class, canonical,
)
from stbuf_stcon_transmit_source.reference_oracle import (
    _snapshot as old_snapshot, _source, _formal, AUTHORITY,
    stcon_writer_lineage as frozen_lineage,
)
from post_consumer_continuation.reference_oracle import (
    _slot, _domain, _same_source, _nullable_bool,
    stbuf_boundary_obligations as frozen_stbuf,
)
from .corpus import SOURCE_BINDING, READBACK_KEYS, READER_SITES, PRODUCER_SITES, PATHS, cases

# Exact fourteen documentary rows, transcribed from the frozen primary proof.
ACK_RULES = {
    'TX_READY_REQUEST_AT_UART_START': {'classification': 'ManufacturerDocumented',
        'inheritedFactIds': ['TX_READY_AT_START_IRQ_BIT2', 'UART_NORMAL_WSTBUF_LSTSF_START'],
        'qualification': 'InheritedM2csStandardProfile_NotNewObservation'},
    'GENERIC_QUALIFIED_INTERRUPT_ENTRY_ACK': {'classification': 'SourceQualifiedConditional',
        'source': 'InheritedIrqProof_Print164_169',
        'qualification': 'Generic serviced-factor clearing only under qualified entry; conflicting IE polarity retained; no TX-specific STBUF-write/read ACK inferred'},
    'STBUF_WRITE_ACK': {'classification': 'Unknown', 'unknownFactIds': ['STBUF_WRITE_SPECIFIC_ACK']},
    'TX_REQUEST_READ_ACK': {'classification': 'Unknown', 'unknownFactIds': ['TX_REQUEST_READ_ACK']},
    'AUTOMATIC_REASSERT_WITHOUT_NEW_DATA': {'classification': 'Unknown', 'unknownFactIds': ['LEVEL_REASSERT_WITHOUT_NEW_DATA']},
    'ACTIVE_PREVIOUS_AND_BUFFERED_NEXT': {'classification': 'ManufacturerDocumented',
        'inheritedFactIds': ['TRANSMIT_TWO_STAGES', 'BUSY_WRITE_CONTINUES_PREVIOUS_TRANSMISSION', 'BUFFERED_NEXT_START_RAISES_TX_READY'],
        'qualification': 'Only the described two-stage/one-next-data case, not a queue or third-write rule'},
    'FULL_HOLDING_BUFFER_THIRD_WRITE': {'classification': 'Unknown', 'unknownFactIds': ['FULL_HOLDING_BUFFER_WRITE_COLLISION']},
    'HARDWARE_SET_SOFTWARE_CLEAR_PRIORITY': {'classification': 'Unknown', 'unknownFactIds': ['HARDWARE_SET_SOFTWARE_CLEAR_PRIORITY']},
    'TX_MODE_CHANGE_DURING_TRANSFER': {'classification': 'Unknown', 'unknownFactIds': ['TX_MODE_CHANGE_DURING_ACTIVE_TRANSFER'],
        'qualification': 'Receiver SREN0 restriction is not transferred'},
    'CLOCK_RELOAD_CHANGE_DURING_TRANSFER': {'classification': 'Unknown', 'unknownFactIds': ['CLOCK_OR_RELOAD_CHANGE_DURING_ACTIVE_TRANSFER']},
    'SEPARATE_TX_COMPLETE_INTERRUPT': {'classification': 'Unknown', 'unknownFactIds': ['TX_COMPLETE_INTERRUPT']},
    'STANDARD_RESET_DESCRIPTORS': {'classification': 'ManufacturerDocumented',
        'qualification': 'Inherited table descriptors only; not current hardware state or operational reset sequence; older preliminary spec corroborates standard66201 table'},
    'CURRENT_NATIVE_READY_OR_RESET_STATE': {'classification': 'Unknown', 'unknownFactIds': ['ACTUAL_NATIVE_TX_READINESS', 'ACTUAL_ECU_APPLICABILITY']},
    'IE_POLARITY': {'classification': 'SourceConflict', 'unknownFactIds': ['IE_POLARITY_CONFLICT'],
        'qualification': 'Printed165/168/169 and167 predicates remain unresolved'},
}


def _snapshot(query, producer=False):
    shape = {'inputClass', 'memory', 'knownBits', 'registers', 'generations',
             'assumptions', 'registerKnownBits', 'configurationIntents', 'sfrReadbacks'}
    if type(query) is not dict or set(query) != shape | ({'entry'} if producer else set()):
        raise ValueError('ReferenceSnapshotShape')
    if producer and query['entry'] not in ('Compare3cb', 'SymbolicCarryTail'):
        raise ValueError('ReferenceProducerEntry')
    projected = {key: deepcopy(value) for key, value in query.items() if key not in ('entry', 'sfrReadbacks')}
    for field in ('memory', 'generations'):
        if type(projected[field]) is not dict or '03CB' not in projected[field]:
            raise ValueError('ReferenceAddedData')
        projected[field].pop('03CB')
    if not _integer(query['memory']['03CB'], 255) or not _generation(query['generations']['03CB']):
        raise ValueError('ReferenceAddedDataType')
    if type(query['knownBits']) is not dict:
        raise ValueError('ReferenceKnownBits')
    projected['knownBits'] = {}
    for key, value in query['knownBits'].items():
        if type(key) is str and key.startswith('03CB.'):
            if len(key) != 6 or key[-1] not in '01234567' or type(value) is not int or value not in (0, 1):
                raise ValueError('ReferenceAddedKnownBit')
            raw = query['memory']['03CB']
            if raw is not None and (raw >> int(key[-1])) & 1 != value:
                raise ValueError('ReferenceAddedBitContradiction')
        else:
            projected['knownBits'][key] = value
    _, frozen = old_snapshot(projected)
    if type(query['sfrReadbacks']) is not dict or set(query['sfrReadbacks']) != set(READBACK_KEYS):
        raise ValueError('ReferenceReadbackShape')
    for value in query['sfrReadbacks'].values():
        _slot(value)
    return deepcopy(query), frozen


def _consensus(values):
    values = set(values)
    return next(iter(values)) if len(values) == 1 else None


def _known(values):
    values = tuple(values)
    return {bit: (values[0] >> bit) & 1 for bit in range(8)
            if len({(byte >> bit) & 1 for byte in values}) == 1}


def _values(bits):
    return {byte for byte in range(256) if all((byte >> bit) & 1 == value for bit, value in bits.items())}


class Reference(FrozenEffects):
    def __init__(self, query, producer=False):
        original, projected = _snapshot(query, producer)
        name = 'mode_bit1_producer' if producer else 'tx_configuration_reader'
        specific = (['ConditionalModeProducerNotNativeOwner', 'ProducerToConfigurationPathNotEstablished', 'Stbuf2995NotPerformed']
            if producer else ['SuppliedSymbolicReadbacksNotHardwareObservations', 'NativeConfigurationOwnerNotEstablished', 'Stbuf2995NotPerformed'])
        super().__init__({key: value for key, value in projected.items() if key != 'registerKnownBits'},
                         name, PRODUCER_SITES if producer else READER_SITES, specific)
        self.original = original
        self.state = {key: deepcopy(original[key]) for key in ('memory', 'knownBits', 'registers',
            'generations', 'registerKnownBits', 'configurationIntents', 'sfrReadbacks')}

    def result(self, boundary, outcome=None, status='CompleteConditional', reason='VerifiedSelectedSourcePath'):
        return {**super().result(boundary, outcome, status, reason), **deepcopy(AUTHORITY),
                'stopBoundary': 'STOP_BEFORE_STBUF_2995'}

    def step(self, pc, successor, kind='Linear', taken=None):
        super().step(pc, successor, kind, taken)
        self.steps[-1]['afterRegisters'] = deepcopy(self.registers)

    def admit(self, pc):
        failure = self.guard(pc)
        if failure is not None:
            return failure
        labels = [item['generation'] for field in ('configurationIntents', 'sfrReadbacks')
                  for item in self.state[field].values()]
        if any(label is not None and label.startswith('ConditionalEffect:' + self.name + ':') for label in labels):
            return self.outside(pc, 'EffectNamespaceAlreadyPresent')
        return None

    def pointer_write(self, pc, value, next_pc):
        bank = self.registers['scb']
        if bank is None:
            return self.outside(pc, 'PointerBankNotEstablished')
        self.write(pc, 0x84 + bank * 8, [value & 255, value >> 8], 'PointingRegisterWrite', 'Literal')
        self.step(pc, next_pc)
        return None

    def pointer_read(self, pc):
        self.read(pc, 0x84 + self.registers['scb'] * 8, 16,
                  'ARCHITECTURAL_ADDRESS_DEPENDENCY', 'PointingRegisterAlias')

    def symbolic_read(self, pc, address):
        item = self.state['sfrReadbacks'][f'{address:04X}']
        raw = item['value']
        self.reads.append({'pc': pc, 'space': 'SYMBOLIC_SFR_READBACK', 'address': address,
            'widthBits': 8, 'value': raw, 'bytes': [raw],
            'knownBits': {f'{address:04X}.' + bit: value for bit, value in item['knownBits'].items()},
            'generations': [item['generation']], 'accessRole': 'SuppliedReadbackOperand',
            'actualHardwareObservation': None})
        return _domain(item)

    def byte_load(self, pc, address, next_pc):
        if self.original['assumptions']['ordinaryByteSemantics'] is not True:
            return self.outside(pc, 'OrdinaryByteSemanticsNotEstablished')
        values = self.symbolic_read(pc, address)
        bits = _known(values)
        self.register_byte('al', bits)
        self.registers.update(dd=0, zf=_zero(bits, 8))
        self.step(pc, next_pc)
        return None

    def mask_al(self, pc, mask, next_pc):
        values = {byte & mask for byte in _values(self.register_byte_bits('al'))}
        bits = _known(values)
        self.register_byte('al', bits)
        self.registers['zf'] = _zero(bits, 8)
        self.step(pc, next_pc)

    def compare(self, values, expected):
        self.registers.update(cf=_consensus(int(value < expected) for value in values),
                              zf=_consensus(int(value == expected) for value in values))

    def mismatch_branch(self, pc, next_pc, outcome):
        zf = self.registers['zf']
        target = None if zf is None else 0x3FB1 if zf == 0 else next_pc
        self.step(pc, target, 'Branch', None if zf is None else zf == 0)
        if zf is None:
            return self.result(pc, status='IndeterminateBranch', reason='UnknownBranchPredicate')
        return self.result(target, outcome) if zf == 0 else None


def tx_configuration_reader(snapshot):
    r = Reference(snapshot)
    failure = r.admit(0x3FD4)
    if failure is not None: return failure
    failure = r.pointer_write(0x3FD4, 0x0356, 0x3FD7)
    if failure is not None: return failure
    r.pointer_read(0x3FD7); r.read(0x3FD7, 0x0356)
    r.registers['cf'] = r.bit(0x0356, 1); r.step(0x3FD7, 0x3FD9)
    carry = r.registers['cf']
    r.step(0x3FD9, None if carry is None else 0x3FF7 if carry == 0 else 0x3FDB,
           'Branch', None if carry is None else carry == 0)
    if carry is None:
        return r.result(0x3FD9, status='IndeterminateBranch', reason='UnknownBranchPredicate')
    if carry == 0: return r.result(0x3FF7, 'GuardBypass')
    for load, mask_pc, cmp_pc, branch, address, mask, expected, next_pc, outcome in (
        (0x3FDB, 0x3FDD, 0x3FDF, 0x3FE1, 0x4A, 0xF3, 0x12, 0x3FE3, 'MismatchSTTMC'),
        (0x3FE3, 0x3FE5, 0x3FE7, 0x3FE9, 0x50, 0x7F, 0x1C, 0x3FEB, 'MismatchSTCON')):
        failure = r.byte_load(load, address, mask_pc)
        if failure is not None: return failure
        r.mask_al(mask_pc, mask, cmp_pc)
        r.compare(_values(r.register_byte_bits('al')), expected); r.step(cmp_pc, branch)
        failure = r.mismatch_branch(branch, next_pc, outcome)
        if failure is not None: return failure
    for cmp_pc, branch, address, expected, next_pc, outcome in (
        (0x3FEB, 0x3FEF, 0x54, 0x8C, 0x3FF1, 'MismatchSRCON'),
        (0x3FF1, 0x3FF5, 0x49, 0xDF, 0x3FF7, 'MismatchSTTMR')):
        r.compare(r.symbolic_read(cmp_pc, address), expected); r.step(cmp_pc, branch)
        failure = r.mismatch_branch(branch, next_pc, outcome)
        if failure is not None: return failure
    return r.result(0x3FF7, 'AllConfigurationChecksMatch')


def mode_bit1_producer(snapshot):
    r = Reference(snapshot, producer=True)
    first = 0x60C9 if snapshot['entry'] == 'Compare3cb' else 0x60D2
    failure = r.admit(first)
    if failure is not None: return failure
    if snapshot['entry'] == 'Compare3cb':
        failure = r.pointer_write(0x60C9, 0x03CB, 0x60CC)
        if failure is not None: return failure
        r.pointer_read(0x60CC); r.read(0x60CC, 0x03CB)
        r.compare(_values(_memory_bits(r.state, 0x03CB)), 128); r.step(0x60CC, 0x60CF)
        before = r._packed_pswh()
        r.reads.append({'pc': 0x60CF, 'space': 'REGISTER', 'address': 5, 'widthBits': 8,
            'value': before, 'bytes': [before],
            'knownBits': {'0005.' + str(bit): r.registers[key] for key, bit in
                (('mie', 0), ('dd', 4), ('hc', 5), ('zf', 6), ('cf', 7)) if r.registers[key] is not None},
            'generations': [None], 'accessRole': 'RegisterOperand'})
        r.registers['cf'] = None if r.registers['cf'] is None else 1 - r.registers['cf']
        r.registers['zf'] = None
        r.specific.append('PswhSelfDestinationZfPrecedenceNotEstablished')
        ordinal = len(r.journal) + 1
        r.journal.append({'ordinal': ordinal, 'pc': 0x60CF, 'space': 'REGISTER', 'address': 5,
            'widthBits': 8, 'before': before, 'after': None, 'beforeBytes': [before], 'afterBytes': [None],
            'kind': 'RegisterXor', 'sameValue': None, 'beforeGeneration': [None],
            'afterGeneration': f'ConditionalEffect:{r.name}:60CF:{ordinal}', 'valueSource': 'PSWH^80',
            'effectClass': 'ConditionalRomEffect'})
        r.intermediate.append({'afterOrdinal': ordinal, 'pc': 0x60CF, 'state': deepcopy(r.state)})
        r.step(0x60CF, 0x60D2)
    failure = r.pointer_write(0x60D2, 0x0356, 0x60D5)
    if failure is not None: return failure
    r.pointer_read(0x60D5); r.read(0x60D5, 0x0356)
    old = r.state['memory']['0356']; carry = r.registers['cf']
    source = _values(_memory_bits(r.state, 0x0356))
    possible = {(byte & 0xFD) | (bit << 1) for byte in source for bit in ((0, 1) if carry is None else (carry,))}
    after = None if old is None or carry is None else (old & 0xFD) | (carry << 1)
    partial = {'0356.' + str(bit): value for bit, value in _known(possible).items()} if after is None else None
    r.write(0x60D5, 0x0356, [after], 'RMW', 'CarryBitMove:1', partial=partial)
    r.step(0x60D5, 0x60D7)
    return r.result(0x60D7, 'ConditionalModeBit1Written')


def _binding(value):
    return 'SourceBindingMissing' if value is None else 'SourceBindingMismatch' if not _same_source(value, SOURCE_BINDING) else None


def _shape(query, fields, claims):
    if type(query) is not dict or set(query) != set(fields): raise ValueError('ReferenceQueryShape')
    _input_class(query['inputClass']); _source(query['sourceBinding'])
    if query['claim'] not in claims: raise ValueError('ReferenceClaim')


def tx_configuration_reaching_definitions(query):
    _shape(query, ('inputClass', 'sourceBinding', 'timelineQuery', 'path', 'entryGeneration', 'requestedGeneration', 'noInterference', 'claim'),
           ('ConditionalOnly', 'NativeOwner', 'ActualTx'))
    if query['path'] not in PATHS or not all(_generation(query[key]) for key in ('entryGeneration', 'requestedGeneration')) or not _nullable_bool(query['noInterference']):
        raise ValueError('ReferenceReachingQuery')
    if type(query['timelineQuery']) is not dict or query['timelineQuery'].get('inputClass') != query['inputClass']:
        raise ValueError('ReferenceInputClassMismatch')
    timeline = frozen_lineage(query['timelineQuery'])
    current = timeline['state']['lastSlot']['generation']
    relation, status, reason = 'ConditionalWriterRetained', 'CompleteConditional', 'ConditionalBoundedWriterRetained'
    error = _binding(query['sourceBinding'])
    if query['claim'] != 'ConditionalOnly': relation, status, reason = 'SourceConflict', 'OutsideVerifiedScope', 'UnestablishedNativeOwnerClaim'
    elif error: relation, status, reason = 'SourceConflict', 'OutsideVerifiedScope', error
    elif timeline['status'] == 'OutsideVerifiedScope': relation, status, reason = 'SourceConflict', 'OutsideVerifiedScope', 'DeclaredTimelineRefused'
    elif query['noInterference'] is not True or query['timelineQuery']['noInterference'] is not True or timeline['state']['lastKind'] == 'UnknownWriter':
        relation, status, reason = 'UnknownInterference', 'IndeterminateObligation', 'InterferenceNotExcluded'
    elif timeline['state']['lastKind'] != 'ConfigIntent': relation, status, reason = 'CompetingWriter', 'IndeterminateObligation', 'CompetingConfigurationWriter'
    elif any(value is None for value in (current, query['entryGeneration'], query['requestedGeneration'])):
        relation, status, reason = 'MissingReachingPath', 'IndeterminateObligation', 'MissingGenerationObligation'
    elif current != query['entryGeneration']: relation, status, reason = 'CompetingWriter', 'IndeterminateObligation', 'EntryGenerationReplaced'
    elif query['requestedGeneration'] != current: relation, status, reason = 'StaleGeneration', 'IndeterminateObligation', 'StaleRequestedGeneration'
    elif query['path'] not in ('ConfigurationSuffix', 'ReaderWindow'):
        relation, status, reason = 'MissingReachingPath', 'IndeterminateObligation', 'SourceCfgEdgeNotEstablished'
    state = {'timeline': timeline, 'reachingDefinitions': {'path': query['path'],
        'entryGeneration': query['entryGeneration'], 'requestedGeneration': query['requestedGeneration'],
        'currentGeneration': current, 'relation': relation}, 'actualNativeOwner': None}
    return _formal(query, 'tx_configuration_reaching_definitions', state,
        sorted((0x2889, 0x288B, 0x288C, 0x288E, 0x3FD4, 0x3FF5, 0x2995, 0x60D5)), status, reason,
        ['DeclaredConfigurationHistoryOnly', 'NativeStconOwnerNotEstablished', 'ConfigurationTo2995PathNotEstablished'],
        'ConditionalSourceReachingDefinitions')


def tx_ack_documentary_obligations(query):
    _shape(query, ('inputClass', 'sourceBinding', 'rule', 'applicability', 'claim'),
        ('DocumentaryOnly', 'ActualAck', 'ActualTx', 'Fifo', 'TxCompleteIrq', 'RuntimeAdmission'))
    if query['rule'] not in ACK_RULES or query['applicability'] not in ('QualifiedStandardProfile', 'UnknownActualEcu', 'ActualEcuVerified'):
        raise ValueError('ReferenceAckQuery')
    state = {'rule': query['rule'], 'relationship': deepcopy(ACK_RULES[query['rule']]), 'applicability': query['applicability'],
        'txReadyVector': 12, 'txReadyBit': 2, 'txBrgVector': 36, 'txBrgBit': 14, 'rxReadyVector': 10, 'rxReadyBit': 1,
        'iePolarityResolution': None, 'actualPendingGeneration': None, 'actualAcknowledge': None, 'physicalApplicability': None}
    status, reason = 'CompleteConditional', 'DocumentaryAckObligationsSpecified'
    error = _binding(query['sourceBinding'])
    if query['claim'] != 'DocumentaryOnly' or query['applicability'] == 'ActualEcuVerified': status, reason = 'OutsideVerifiedScope', 'UnestablishedTransmitAuthorityClaim'
    elif error: status, reason = 'OutsideVerifiedScope', error
    return _formal(query, 'tx_ack_documentary_obligations', state, [0x2995], status, reason,
        ['HardwareApplicabilityUnknown', 'TxSpecificAckAndReassertionNotEstablished', 'IePolaritySourceConflictRetained', 'NoAcknowledgeEventPerformed'],
        'ManufacturerAckObligations_NotPeripheralSimulation')


def stbuf2995_configuration_provenance(query):
    _shape(query, ('inputClass', 'sourceBinding', 'readerQuery', 'producerQuery', 'reachingQuery', 'ackQuery', 'stbufQuery', 'claim'),
        ('ConditionalOnly', 'NativeOwner', 'ActualTx', 'RuntimeAdmission'))
    for key in ('readerQuery', 'producerQuery', 'reachingQuery', 'ackQuery', 'stbufQuery'):
        if type(query[key]) is not dict or query[key].get('inputClass') != query['inputClass']: raise ValueError('ReferenceNestedInputClass')
    reader = tx_configuration_reader(query['readerQuery'])
    producer = mode_bit1_producer(query['producerQuery'])
    reaching = tx_configuration_reaching_definitions(query['reachingQuery'])
    ack = tx_ack_documentary_obligations(query['ackQuery'])
    stbuf = frozen_stbuf(query['stbufQuery'])
    state = {'reader': reader, 'producer': producer, 'reaching': reaching, 'ack': ack, 'stbuf': stbuf,
        'actualNativeConfigurationOwner': None, 'actualTxReadiness': None, 'continuousCfgEstablished': False}
    status, reason = 'IndeterminateObligation', 'ConfigurationTo2995PathNotEstablished'
    error = _binding(query['sourceBinding'])
    if query['claim'] != 'ConditionalOnly': status, reason = 'OutsideVerifiedScope', 'UnestablishedTransmitAuthorityClaim'
    elif error: status, reason = 'OutsideVerifiedScope', error
    elif any(item['status'] == 'OutsideVerifiedScope' for item in (reader, producer, reaching, ack, stbuf)):
        status, reason = 'OutsideVerifiedScope', 'NestedSourceObligationRefused'
    elif any(item['status'] != 'CompleteConditional' for item in (reader, producer, reaching, ack, stbuf)):
        reason = 'NestedConditionalPremisesNotEstablished'
    return _formal(query, 'stbuf2995_configuration_provenance', state,
        sorted((*READER_SITES, *PRODUCER_SITES, 0x286D, 0x288C, 0x2995)), status, reason,
        ['NativeConfigurationTo2995ContinuityNotEstablished', 'PhysicalTransmitterReadinessNotEstablished', 'NoStbufWritePerformed'],
        'ConditionalConfigurationProvenance_NotPeripheralAdmission')


OPERATIONS = {'tx_configuration_reader': tx_configuration_reader, 'mode_bit1_producer': mode_bit1_producer,
    'tx_configuration_reaching_definitions': tx_configuration_reaching_definitions,
    'tx_ack_documentary_obligations': tx_ack_documentary_obligations,
    'stbuf2995_configuration_provenance': stbuf2995_configuration_provenance}


def evaluate(case):
    return OPERATIONS[case['operation']](deepcopy(case['input']))


def record(case, output):
    state = output['state']
    generations = {'data': deepcopy(state.get('generations')),
        'softwareIntents': {key: value['generation'] for key, value in state['configurationIntents'].items()} if 'configurationIntents' in state else None,
        'suppliedReadbacks': {key: value['generation'] for key, value in state['sfrReadbacks'].items()} if 'sfrReadbacks' in state else None,
        'writerEvents': [{'ordinal': event['ordinal'], 'before': deepcopy(event.get('beforeGeneration')),
                          'after': deepcopy(event.get('afterGeneration'))} for event in output['journal']],
        'reachingDefinitions': deepcopy(state.get('reachingDefinitions'))}
    operation = case['operation']
    evidence = 'StaticRomSoftwareEffect' if operation in ('tx_configuration_reader', 'mode_bit1_producer') else 'ManufacturerDocumented' if operation == 'tx_ack_documentary_obligations' else 'ConditionalSoftwareRelationship'
    return {'caseId': case['id'], 'operation': operation, 'input': deepcopy(case['input']), 'output': deepcopy(output),
        'sourceScope': deepcopy(output['sourceScope']), 'evidenceClass': evidence,
        'applicability': 'StandardMsm66201_207_Documented_NotEcuApplicable', 'branchOutcome': [
            {'pc': step['pc'], 'taken': step['branchTaken'], 'next': step['next']} for step in output['steps'] if step['kind'] == 'Branch'],
        'state': deepcopy(state), 'reads': deepcopy(output['reads']), 'orderedWrites': deepcopy(output['journal']),
        'generations': generations, 'intermediateStates': deepcopy(output['intermediateStates']),
        'unresolvedConstraints': deepcopy(output['unresolvedConstraints']), 'stopBoundary': output['stopBoundary'],
        'executionAuthority': {key: deepcopy(output[key]) for key in AUTHORITY}}


def canonical_records():
    for case in cases():
        yield canonical(record(case, evaluate(case)))
