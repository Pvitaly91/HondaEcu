"""Independent source-intent equations, without new implementation imports."""
from copy import deepcopy

from payload_consumer_tail.reference_oracle import (
    Reference as FrozenReference, COMMON, _bits, _memory_bits, _zero,
    _integer, _generation, _input_class,
)
from payload_consumer_tail.corpus import ADDRESSES as OLD_ADDRESSES
from post_consumer_continuation.reference_oracle import (
    _checked as frozen_checked, _slot, _domain, _same_source, _nullable_bool,
    stbuf_boundary_obligations as frozen_stbuf,
)
from .corpus import CONFIG_SITES, READER_SITES, SFR_KEYS, SOURCE_BINDING, cases

ADDRESSES = tuple(sorted((*OLD_ADDRESSES, '0208', '0209')))
AUTHORITY = {'actualHardwareObservation': None, 'actualBufferWrite': None,
    'actualTransmission': None, 'actualTxCompletion': None, 'actualTxIrqDelivery': None,
    'actualPeripheralClockEvent': None, 'cpuInstructionRetirements': 0,
    'actualPeripheralOperations': 0, 'executionStatus': 'EXECUTION_BLOCKED',
    'firmwareReady': False, 'stbufStopBoundary': 'STOP_BEFORE_STBUF_2995'}
HYPOTHESIS_SCOPE = tuple(sorted((*CONFIG_SITES, *READER_SITES, 0x2995)))
JOIN_SCOPE = (*CONFIG_SITES, 0x2995)

# Copied solely from the frozen primary proof's seven ordered situation lists.
SITUATIONS = {
    'IdleWrite': {'documentedRules': ['TX_SETUP_BEFORE_STBUF', 'STBUF_WRITE_ONLY_8_LSB_FIRST',
        'TRANSMIT_TWO_STAGES', 'IDLE_STBUF_WRITE_STARTS_TRANSMISSION', 'STBUF_TO_SHIFT_HALF_CLK_DOC',
        'UART_NORMAL_WSTBUF_LSTSF_START', 'TX_READY_AT_START_IRQ_BIT2'],
        'unknownRules': ['ACTUAL_ECU_APPLICABILITY', 'ACTUAL_NATIVE_TX_READINESS', 'STBUF_WRITE_SPECIFIC_ACK']},
    'BusyWrite': {'documentedRules': ['TRANSMIT_TWO_STAGES', 'BUSY_WRITE_CONTINUES_PREVIOUS_TRANSMISSION',
        'BUFFERED_NEXT_START_RAISES_TX_READY'], 'unknownRules': ['ACTUAL_NATIVE_TX_READINESS',
        'FULL_HOLDING_BUFFER_WRITE_COLLISION', 'HARDWARE_SET_SOFTWARE_CLEAR_PRIORITY']},
    'Completion': {'documentedRules': ['UART_NORMAL_FRAME_END_STOP_BIT', 'BUFFERED_NEXT_START_RAISES_TX_READY'],
        'unknownRules': ['TX_COMPLETE_INTERRUPT', 'ACTUAL_NATIVE_TX_READINESS']},
    'ModeChange': {'documentedRules': ['TX_SETUP_BEFORE_STBUF', 'RX_MODE_CHANGE_REQUIRES_SREN_ZERO',
        'BRG_RELOAD_WRITE_NOT_COUNTER_SEED'], 'unknownRules': ['TX_MODE_CHANGE_DURING_ACTIVE_TRANSFER',
        'CLOCK_OR_RELOAD_CHANGE_DURING_ACTIVE_TRANSFER', 'STCON_FULL_LENGTH_STOP_PARITY_ENCODING']},
    'Acknowledge': {'documentedRules': [], 'unknownRules': ['STBUF_WRITE_SPECIFIC_ACK',
        'TX_REQUEST_READ_ACK', 'HARDWARE_SET_SOFTWARE_CLEAR_PRIORITY', 'IE_POLARITY_CONFLICT']},
    'Reassertion': {'documentedRules': ['BUFFERED_NEXT_START_RAISES_TX_READY'],
        'unknownRules': ['LEVEL_REASSERT_WITHOUT_NEW_DATA', 'HARDWARE_SET_SOFTWARE_CLEAR_PRIORITY']},
    'Collision': {'documentedRules': ['BUSY_WRITE_CONTINUES_PREVIOUS_TRANSMISSION',
        'BUFFERED_NEXT_START_RAISES_TX_READY'], 'unknownRules': ['FULL_HOLDING_BUFFER_WRITE_COLLISION',
        'HARDWARE_SET_SOFTWARE_CLEAR_PRIORITY', 'TX_MODE_CHANGE_DURING_ACTIVE_TRANSFER']},
}


def _slots(value):
    if type(value) is not dict or set(value) != set(SFR_KEYS):
        raise ValueError('ReferenceIntentSlots')
    for item in value.values():
        _slot(item)


def _source(value):
    if value is not None and type(value) is not dict:
        raise ValueError('ReferenceSourceType')


def _snapshot(value):
    shape = {'inputClass', 'memory', 'knownBits', 'registers', 'generations', 'assumptions', 'registerKnownBits', 'configurationIntents'}
    if type(value) is not dict or set(value) != shape:
        raise ValueError('ReferenceSnapshotShape')
    for field in ('memory', 'generations'):
        if type(value[field]) is not dict or set(value[field]) != set(ADDRESSES):
            raise ValueError('ReferenceSnapshotMemory')
    for raw in value['memory'].values():
        if not _integer(raw, 255): raise ValueError('ReferenceMemoryByte')
    if any(not _generation(label) for label in value['generations'].values()):
        raise ValueError('ReferenceGeneration')
    if type(value['knownBits']) is not dict:
        raise ValueError('ReferenceKnownBits')
    for key, bit in value['knownBits'].items():
        if (type(key) is not str or len(key) != 6 or key[:4] not in ADDRESSES or key[4] != '.'
                or key[5] not in '01234567' or type(bit) is not int or bit not in (0, 1)):
            raise ValueError('ReferenceKnownBit')
        raw = value['memory'][key[:4]]
        if raw is not None and (raw >> int(key[-1])) & 1 != bit:
            raise ValueError('ReferenceKnownBitContradiction')
    projected = {key: deepcopy(item) for key, item in value.items() if key != 'configurationIntents'}
    for field in ('memory', 'generations'):
        projected[field] = {key: projected[field][key] for key in OLD_ADDRESSES}
    projected['knownBits'] = {key: bit for key, bit in projected['knownBits'].items() if key[:4] in OLD_ADDRESSES}
    frozen_checked(projected)
    _slots(value['configurationIntents'])
    return deepcopy(value), projected


class Reference(FrozenReference):
    def __init__(self, snapshot):
        original, projected = _snapshot(snapshot)
        super().__init__({key: val for key, val in projected.items() if key != 'registerKnownBits'},
            'stcon_configuration', CONFIG_SITES,
            ['PeripheralConfigurationIntentOnly', 'NativeConfigurationOwnerNotEstablished', 'Stbuf2995NotPerformed'])
        self.original = original
        self.state = {key: deepcopy(original[key]) for key in ('memory', 'knownBits', 'registers',
            'generations', 'registerKnownBits', 'configurationIntents')}

    def result(self, boundary, outcome=None, status='CompleteConditional', reason='VerifiedSelectedSourcePath'):
        return {**super().result(boundary, outcome, status, reason), **deepcopy(AUTHORITY),
                'stopBoundary': 'STOP_BEFORE_DATA4700_288E'}

    def intent(self, pc, address, value, kind, source):
        key = f'{address:04X}'
        before = deepcopy(self.state['configurationIntents'][key])
        bits = {} if value is not None else {key[3:]: bit for key, bit in self.state['registerKnownBits'].items() if key.startswith('AL.')}
        number = len(self.journal) + 1
        label = f'ConditionalEffect:stcon_configuration:{pc:04X}:{number}'
        self.state['configurationIntents'][key] = {'value': value, 'knownBits': bits, 'generation': label}
        self.journal.append({'ordinal': number, 'pc': pc, 'space': 'SOFTWARE_SFR_INTENT',
            'address': address, 'widthBits': 8, 'before': before['value'], 'after': value,
            'beforeBytes': [before['value']], 'afterBytes': [value], 'kind': kind,
            'sameDeclaredValue': None if before['value'] is None or value is None else before['value'] == value,
            'beforeGeneration': [before['generation']], 'afterGeneration': label,
            'valueSource': source, 'effectClass': 'StaticRomSfrWriteIntent_NotPerformedIO',
            'knownBitsBefore': before['knownBits'], 'knownBitsAfter': deepcopy(bits),
            'actualHardwareObservation': None})
        self.intermediate.append({'afterOrdinal': number, 'pc': pc, 'state': deepcopy(self.state)})

    def load_literal(self, pc, byte, successor):
        if self.original['assumptions']['ordinaryByteSemantics'] is not True:
            return self.outside(pc, 'OrdinaryByteSemanticsNotEstablished')
        self.register_byte('al', _bits(byte)); self.registers.update(dd=0, zf=int(byte == 0))
        self.step(pc, successor)
        return None

    def load_local(self, pc, address, successor):
        if self.original['assumptions']['ordinaryByteSemantics'] is not True:
            return self.outside(pc, 'OrdinaryByteSemanticsNotEstablished')
        self.read(pc, address)
        bits = _memory_bits(self.state, address)
        self.register_byte('al', bits); self.registers.update(dd=0, zf=_zero(bits, 8))
        self.step(pc, successor)
        return None


def stcon_configuration(snapshot):
    r = Reference(snapshot)
    if r.original['assumptions']['noInterference'] is not True:
        return r.outside(0x286D, 'NoInterferencePremiseNotEstablished')
    labels = [*r.state['generations'].values(), *(item['generation'] for item in r.state['configurationIntents'].values())]
    if any(label is not None and label.startswith('ConditionalEffect:stcon_configuration:') for label in labels):
        return r.outside(0x286D, 'EffectNamespaceAlreadyPresent')
    if r.registers['lrb'] != 0x41:
        return r.outside(0x286D, 'LocalBank0208NotEstablished')
    for pc, address, byte, successor in ((0x286D, 0x208, 0x1C, 0x286F), (0x286F, 0x209, 0x8C, 0x2871)):
        r.write(pc, address, [byte], 'LocalRegisterWrite', 'Literal'); r.step(pc, successor)
    failure = r.load_literal(0x2871, 0xDF, 0x2873)
    if failure is not None: return failure
    bank = r.registers['scb']
    if bank is None: return r.outside(0x2873, 'PointerBankNotEstablished')
    dp = 0x84 + bank * 8
    r.write(0x2873, dp, [0x56, 3], 'PointingRegisterWrite', 'Literal'); r.step(0x2873, 0x2876)
    r.read(0x2876, dp, 16, 'ARCHITECTURAL_ADDRESS_DEPENDENCY', 'PointingRegisterAlias')
    r.read(0x2876, 0x356); r.registers['cf'] = r.bit(0x356, 1); r.step(0x2876, 0x2878)
    taken = r.registers['cf']
    r.step(0x2878, None if taken is None else 0x2880 if taken else 0x287A, 'Branch', None if taken is None else bool(taken))
    if taken is None:
        return r.result(0x2878, status='IndeterminateBranch', reason='UnknownBranchPredicate')
    if not taken:
        for pc, address, byte, successor in ((0x287A, 0x208, 0x31, 0x287C), (0x287C, 0x209, 0xA1, 0x287E)):
            r.write(pc, address, [byte], 'LocalRegisterWrite', 'Literal'); r.step(pc, successor)
        failure = r.load_literal(0x287E, 0xFB, 0x2880)
        if failure is not None: return failure
    for pc, address, successor in ((0x2880, 0x48, 0x2882), (0x2882, 0x49, 0x2884)):
        r.intent(pc, address, r.registers['al'], 'Store', 'AL'); r.step(pc, successor)
    r.intent(0x2884, 0x4A, 0x12, 'ImmediateStore', 'Literal'); r.step(0x2884, 0x2888)
    failure = r.load_local(0x2888, 0x208, 0x2889)
    if failure is not None: return failure
    r.intent(0x2889, 0x50, r.registers['al'], 'Store', 'AL'); r.step(0x2889, 0x288B)
    failure = r.load_local(0x288B, 0x209, 0x288C)
    if failure is not None: return failure
    r.intent(0x288C, 0x54, r.registers['al'], 'Store', 'AL'); r.step(0x288C, 0x288E)
    return r.result(0x288E, 'SerialConfigurationIntentsPrepared')


def _formal(query, procedure, state, scope, status, reason, specific, effect, boundary=0x2995, **extra):
    return {'procedure': procedure, 'status': status, 'reason': reason, 'boundary': boundary,
        'inputClass': query['inputClass'], 'sourceScope': list(scope), 'state': deepcopy(state),
        'reads': [], 'journal': [], 'steps': [], 'intermediateStates': [],
        'unresolvedConstraints': list(dict.fromkeys([*COMMON, *specific,
            *([] if status == 'CompleteConditional' else [reason])])),
        'effectClass': effect, 'stopBoundary': 'STOP_BEFORE_STBUF_2995', **deepcopy(AUTHORITY), **extra}


def _binding_reason(value):
    return 'SourceBindingMissing' if value is None else 'SourceBindingMismatch' if not _same_source(value, SOURCE_BINDING) else None


def _consensus(values):
    values = set(values)
    return next(iter(values)) if len(values) == 1 else None


def _bit(domain, position):
    return _consensus((value >> position) & 1 for value in domain)


def _hypotheses_checked(query):
    if type(query) is not dict or set(query) != {'inputClass', 'sourceBinding', 'configurationIntents', 'claim'}:
        raise ValueError('ReferenceHypothesisShape')
    _input_class(query['inputClass']); _source(query['sourceBinding']); _slots(query['configurationIntents'])
    if query['claim'] not in ('DocumentaryOnly', 'ActualEcuApplicable', 'ActualOwner', 'ActualReady', 'Rx000ATx'):
        raise ValueError('ReferenceHypothesisClaim')


def transmit_configuration_hypotheses(query):
    _hypotheses_checked(query)
    domains = {key: _domain(value) for key, value in query['configurationIntents'].items()}
    tx, baud, rx = domains['0050'], domains['004A'], domains['0054']
    serial = {0: 'UART', 1: 'Synchronous'}.get(_bit(tx, 1))
    protocol = {0: 'Normal', 1: 'Multiprocessor'}.get(_bit(tx, 0)) if serial == 'UART' else None
    modes = ('AutoReloadTimer', 'TransmissionBaudGenerator', 'TransmissionReceivingBaudGenerator', 'TransmissionReceivingBaudGenerator')
    divisors = (2, 4, 8, 16, 32, 128, 512, 512)
    equal = True if len(domains['0048']) == len(domains['0049']) == 1 and domains['0048'] == domains['0049'] else False if domains['0048'].isdisjoint(domains['0049']) else None
    parity = _bit(tx, 5)
    decoded = {'serialMode': serial, 'uartProtocol': protocol,
        'normalLengthCode': _consensus((v >> 2) & 3 for v in tx) if protocol == 'Normal' else None,
        'multiprocessorDataAddress': {0: 'Data', 1: 'Address'}.get(_bit(tx, 2)) if protocol == 'Multiprocessor' else None,
        'multiprocessorBit3Ignored': True if protocol == 'Multiprocessor' else False if protocol == 'Normal' else None,
        'uartStopLengthCode': _bit(tx, 4) if serial == 'UART' else None,
        'synchronousClockRole': {0: 'Slave', 1: 'Master'}.get(_bit(tx, 4)) if serial == 'Synchronous' else None,
        'paritySelectionBit5': parity, 'bit6MeaningfulWhenBit5One': None if parity is None else bool(parity),
        'stconBit7Meaning': None, 'baudGeneratorModeCode': _consensus(v & 3 for v in baud),
        'baudGeneratorMode': _consensus(modes[v & 3] for v in baud),
        'baudGeneratorRunBit': _bit(baud, 4), 'baudGeneratorClockCode': _consensus(v >> 5 for v in baud),
        'baudGeneratorClockDivisor': _consensus(divisors[v >> 5] for v in baud),
        'baudCounterAndReloadDeclaredEqual': equal, 'sttmcDocumentedReadBits': {'2': 1, '3': 1},
        'srconMode': _consensus(('UARTNormal', 'UARTMultiprocessor', 'SynchronousNormal', 'SynchronousMultiprocessor')[v & 3] for v in rx),
        'srconReceivingPermission': {0: 'ReceivingProhibited', 1: 'ReceivingAllowed'}.get(_bit(rx, 7)),
        'effectiveBaudRate': None}
    predicates = []
    for pc, address, mask, expected in ((0x3FDF, 0x4A, 0xF3, 0x12), (0x3FE7, 0x50, 0x7F, 0x1C), (0x3FEB, 0x54, 0xFF, 0x8C), (0x3FF1, 0x49, 0xFF, 0xDF)):
        predicates.append({'sourcePc': pc, 'address': address, 'mask': mask, 'expected': expected,
            'matches': _consensus(v & mask == expected for v in domains[f'{address:04X}']),
            'requiredGuard': 'DATA0356.1=1_NotObserved',
            'classification': 'ConditionalDeclaredSlotPredicate_NotPerformedRead'})
    unknown = ['STCON_FULL_LENGTH_STOP_PARITY_ENCODING', 'STCON_BIT7_OR_TX_PERMISSION_FIELD',
        'GENERAL_BAUD_RATE_FORMULA', 'ACTUAL_ECU_APPLICABILITY', 'ACTUAL_NATIVE_TX_READINESS']
    unknown += ['UnknownDeclaredByte:' + key for key in SFR_KEYS if len(domains[key]) != 1]
    status, reason = 'CompleteConditional', 'DocumentaryConfigurationRelationshipsOnly'
    binding = _binding_reason(query['sourceBinding'])
    if query['claim'] != 'DocumentaryOnly': status, reason = 'OutsideVerifiedScope', 'UnestablishedHardwareConfigurationClaim'
    elif binding: status, reason = 'OutsideVerifiedScope', binding
    return _formal(query, 'transmit_configuration_hypotheses', {'configurationIntents': deepcopy(query['configurationIntents']),
        'decoded': decoded, 'unknownFields': unknown, 'reviewedMaskedPredicates': predicates,
        'actualEcuApplicability': None, 'actualConfigurationOwner': None, 'actualReady': None},
        HYPOTHESIS_SCOPE, status, reason, ['PhysicalMcuApplicabilityNotEstablished', 'NativeConfigurationOwnerNotEstablished',
        'StconFieldEncodingPartiallyUnavailable', 'NoPhysicalBaudRateEstablished'], 'DocumentaryConfigurationHypotheses_NotHardwareState')


def tx_lifecycle_obligations(query):
    if type(query) is not dict or set(query) != {'inputClass', 'sourceBinding', 'situation', 'applicability', 'claim'}:
        raise ValueError('ReferenceLifecycleShape')
    _input_class(query['inputClass']); _source(query['sourceBinding'])
    if type(query['situation']) is not str or query['situation'] not in SITUATIONS or query['applicability'] not in ('QualifiedStandardProfile', 'UnknownActualEcu', 'ActualEcuVerified') or query['claim'] not in ('DocumentaryOnly', 'ActualTx', 'Fifo', 'TxCompleteIrq', 'AckByWrite', 'Rx000ATx'):
        raise ValueError('ReferenceLifecycleType')
    status, reason = 'CompleteConditional', 'DocumentaryTransmitObligationsSpecified'
    binding = _binding_reason(query['sourceBinding'])
    if query['claim'] != 'DocumentaryOnly' or query['applicability'] == 'ActualEcuVerified':
        status, reason = 'OutsideVerifiedScope', 'UnestablishedTransmitAuthorityClaim'
    elif binding: status, reason = 'OutsideVerifiedScope', binding
    return _formal(query, 'tx_lifecycle_obligations', {'situation': query['situation'],
        'applicability': query['applicability'], **deepcopy(SITUATIONS[query['situation']]),
        'txReadyVector': 12, 'txReadyBit': 2, 'txBrgVector': 36, 'txBrgBit': 14,
        'rxReadyVector': 10, 'rxReadyBit': 1, 'iePolarityResolution': None,
        'physicalApplicability': None, 'actualPendingGeneration': None}, [0x2995], status, reason,
        ['HardwareApplicabilityUnknown', 'ActualNativeObservationNotEstablished',
        'TxAckReassertionCollisionNotEstablished', 'IePolaritySourceConflictRetained'],
        'ManufacturerTxObligations_NotPeripheralSimulation')


def _lineage_checked(query):
    if type(query) is not dict or set(query) != {'inputClass', 'sourceBinding', 'initial', 'events', 'noInterference', 'claim'}:
        raise ValueError('ReferenceLineageShape')
    _input_class(query['inputClass']); _source(query['sourceBinding']); _slot(query['initial'])
    if not _nullable_bool(query['noInterference']) or query['claim'] not in ('ConditionalOnly', 'NativeOwner', 'ActualTx', 'ResetOwner', 'Rx000ATx'):
        raise ValueError('ReferenceLineagePremise')
    if type(query['events']) is not list or not 1 <= len(query['events']) <= 32:
        raise ValueError('ReferenceLineageBound')
    shapes = {'ConfigIntent': {'kind', 'id', 'path', 'value', 'generation', 'dd'},
        'AlternateIntent': {'kind', 'id', 'address', 'widthBits', 'value', 'generation', 'dd'},
        'UnknownWriter': {'kind', 'id'}, 'Boundary': {'kind', 'id', 'requestedGeneration'}}
    seen = set()
    for item in query['events']:
        if (type(item) is not dict or type(item.get('kind')) is not str or item['kind'] not in shapes
                or set(item) != shapes[item['kind']] or type(item['id']) is not str
                or not item['id'] or item['id'] in seen):
            raise ValueError('ReferenceTimelineEvent')
        seen.add(item['id'])
        if item['kind'] == 'ConfigIntent':
            if item['path'] not in ('Bit1Set', 'Bit1Clear') or not _integer(item['value'], 255):
                raise ValueError('ReferenceConfigIntent')
        if item['kind'] == 'AlternateIntent':
            if (type(item['address']) is not int or item['address'] not in (0x4F, 0x50, 0x51, 0x52, 0x54)
                    or type(item['widthBits']) is not int or item['widthBits'] not in (8, 16)
                    or not _integer(item['value'], (1 << item['widthBits']) - 1)):
                raise ValueError('ReferenceAlternateIntent')
        if item['kind'] in ('ConfigIntent', 'AlternateIntent'):
            if not _generation(item['generation']) or not _integer(item['dd'], 1):
                raise ValueError('ReferenceWriterType')
        if item['kind'] == 'Boundary' and not _generation(item['requestedGeneration']):
            raise ValueError('ReferenceBoundaryGeneration')


def stcon_writer_lineage(query):
    _lineage_checked(query)
    state = {'lastSlot': deepcopy(query['initial']), 'lastKind': 'InitialUnbound'}
    journal, history, checks = [], [], []
    specific = ['NativeStconOwnerNotEstablished', 'OnlyDeclaredConfigurationHistory']
    def result(status='CompleteConditional', reason='ConditionalConfigurationTimelineOnly', boundary=None):
        return _formal(query, 'stcon_writer_lineage', state, [0x2889, 0x2995], status, reason,
            specific, 'ConditionalConfigurationTimeline_NotPeripheralObservations', boundary,
            journal=deepcopy(journal), intermediateStates=deepcopy(history), configurationChecks=deepcopy(checks))
    if query['claim'] != 'ConditionalOnly':
        return result('OutsideVerifiedScope', 'UnestablishedConfigurationOwnershipClaim')
    binding = _binding_reason(query['sourceBinding'])
    if binding: return result('OutsideVerifiedScope', binding)
    generations = set() if query['initial']['generation'] is None else {query['initial']['generation']}
    for index, item in enumerate(query['events']):
        kind = item['kind']
        if kind in ('ConfigIntent', 'AlternateIntent'):
            if kind == 'ConfigIntent' and item['value'] != (0x1C if item['path'] == 'Bit1Set' else 0x31):
                return result('OutsideVerifiedScope', 'ConfigurationSourceValueMismatch', index)
            required = 0 if kind == 'ConfigIntent' or item['widthBits'] == 8 else 1
            if item['dd'] != required:
                return result('OutsideVerifiedScope', 'ByteDescriptorNotEstablished', index)
            label = item['generation']
            if label is not None and label in generations:
                return result('OutsideVerifiedScope', 'WriterGenerationReused', index)
            if label is not None: generations.add(label)
        if kind == 'Boundary':
            current = state['lastSlot']
            if query['noInterference'] is not True: relation = 'InterferenceNotExcluded'
            elif state['lastKind'] == 'UnknownWriter': relation = 'UnknownInterveningWriter'
            elif current['generation'] is None: relation = 'MissingConfigurationGeneration'
            elif item['requestedGeneration'] != current['generation']: relation = 'StaleRequestedGeneration'
            elif state['lastKind'] != 'ConfigIntent': relation = 'AlternateWriterNotReviewedConfiguration'
            else: relation = 'ConditionalConfigurationWriterAtBoundary'
            checks.append({'eventId': item['id'], 'address': 80, 'widthBits': 8,
                'currentSlot': deepcopy(current), 'requestedGeneration': item['requestedGeneration'], 'relation': relation})
        else:
            before = deepcopy(state['lastSlot'])
            address = None if kind == 'UnknownWriter' else 80 if kind == 'ConfigIntent' else item['address'] if item['widthBits'] == 8 else item['address'] & 0xFFFE
            width = None if kind == 'UnknownWriter' else 8 if kind == 'ConfigIntent' else item['widthBits']
            overlap = None if kind == 'UnknownWriter' else address <= 80 < address + width // 8
            if kind == 'UnknownWriter':
                state.update(lastSlot={'value': None, 'knownBits': {}, 'generation': None}, lastKind='UnknownWriter')
            elif overlap:
                byte = None if item['value'] is None else (item['value'] >> ((80 - address) * 8)) & 255
                state.update(lastSlot={'value': byte, 'knownBits': {}, 'generation': item['generation']}, lastKind=kind)
            after = deepcopy(state['lastSlot'])
            journal.append({'ordinal': len(journal) + 1, 'eventId': item['id'], 'kind': kind,
                'sourcePc': 0x2889 if kind == 'ConfigIntent' else None, 'address': address, 'widthBits': width,
                'declaredValue': None if kind == 'UnknownWriter' else item['value'],
                'beforeSlot': before, 'afterSlot': after, 'targetOverlap': overlap,
                'sameDeclaredValue': before['value'] == after['value'] if overlap and before['value'] is not None and after['value'] is not None else None,
                'effectClass': 'ConditionalConfigurationTimeline_NotPeripheralObservations'})
        history.append({'eventId': item['id'], 'eventIndex': index, 'state': deepcopy(state)})
    return result()


def stbuf2995_source_join(query):
    if type(query) is not dict or set(query) != {'inputClass', 'sourceBinding', 'configurationQuery', 'lineageQuery', 'lifecycleQuery', 'stbufQuery', 'claim'}:
        raise ValueError('ReferenceJoinShape')
    _input_class(query['inputClass']); _source(query['sourceBinding'])
    if query['claim'] not in ('ConditionalOnly', 'ActualTx', 'NativeOwner', 'RuntimeAdmission'):
        raise ValueError('ReferenceJoinClaim')
    configuration = transmit_configuration_hypotheses(query['configurationQuery'])
    lineage = stcon_writer_lineage(query['lineageQuery'])
    lifecycle = tx_lifecycle_obligations(query['lifecycleQuery'])
    stbuf = frozen_stbuf(query['stbufQuery'])
    if any(query[name]['inputClass'] != query['inputClass'] for name in ('configurationQuery', 'lineageQuery', 'lifecycleQuery', 'stbufQuery')):
        raise ValueError('ReferenceJoinInputClassMismatch')
    state = {'configuration': configuration, 'lineage': lineage, 'lifecycle': lifecycle,
        'stbuf': stbuf, 'actualNativeConfigurationOwner': None, 'actualTxReadiness': None}
    status, reason = 'CompleteConditional', 'ConditionalSoftwareAndDocumentaryJoinOnly'
    binding = _binding_reason(query['sourceBinding'])
    if query['claim'] != 'ConditionalOnly': status, reason = 'OutsideVerifiedScope', 'UnestablishedTransmitAuthorityClaim'
    elif binding: status, reason = 'OutsideVerifiedScope', binding
    elif any(value['status'] == 'OutsideVerifiedScope' for value in (configuration, lineage, lifecycle, stbuf)):
        status, reason = 'OutsideVerifiedScope', 'NestedSourceObligationRefused'
    elif lineage['state']['lastSlot'] != query['configurationQuery']['configurationIntents']['0050']:
        status, reason = 'OutsideVerifiedScope', 'ConfigurationLineageMismatch'
    elif not lineage['configurationChecks'] or lineage['configurationChecks'][-1]['relation'] != 'ConditionalConfigurationWriterAtBoundary':
        status, reason = 'IndeterminateObligation', 'ConfigurationWriterAt2995NotEstablished'
    elif stbuf['status'] != 'CompleteConditional':
        status, reason = 'IndeterminateObligation', 'StbufPrerequisitesNotEstablished'
    return _formal(query, 'stbuf2995_source_join', state, JOIN_SCOPE, status, reason,
        ['NativeConfigurationTo2995ContinuityNotEstablished', 'PhysicalTransmitterReadinessNotEstablished',
        'NoStbufWritePerformed'], 'ConditionalSoftwareDocumentaryJoin_NotPeripheralAdmission')


OPERATIONS = {'stcon_configuration': stcon_configuration, 'stcon_writer_lineage': stcon_writer_lineage,
    'tx_lifecycle_obligations': tx_lifecycle_obligations, 'stbuf2995_source_join': stbuf2995_source_join,
    'transmit_configuration_hypotheses': transmit_configuration_hypotheses}
EVIDENCE = {'stcon_configuration': 'StaticRomSoftwareEffect',
    'stcon_writer_lineage': 'ConditionalSoftwareRelationship',
    'tx_lifecycle_obligations': 'ManufacturerDocumented',
    'stbuf2995_source_join': 'ConditionalSoftwareRelationship',
    'transmit_configuration_hypotheses': 'ConditionalSoftwareRelationship'}


def evaluate(case):
    return OPERATIONS[case['operation']](deepcopy(case['input']))


def record(case, output):
    state = output['state']
    nested_lineage = state.get('lineage')
    writer_generations = []
    for event in output['journal']:
        before = event.get('beforeGeneration', [event['beforeSlot']['generation']] if 'beforeSlot' in event else None)
        after = event.get('afterGeneration', event['afterSlot']['generation'] if 'afterSlot' in event else None)
        writer_generations.append({'ordinal': event['ordinal'], 'before': deepcopy(before), 'after': deepcopy(after)})
    lineage = {'stateGenerations': deepcopy(state.get('generations')),
        'configurationIntentGenerations': {key: value['generation'] for key, value in state['configurationIntents'].items()} if 'configurationIntents' in state else None,
        'lastConfigurationSlot': deepcopy(state.get('lastSlot', nested_lineage['state']['lastSlot'] if nested_lineage is not None else None)),
        'configurationChecks': deepcopy(output.get('configurationChecks', nested_lineage['configurationChecks'] if nested_lineage is not None else None)),
        'orderedWriterGenerations': writer_generations}
    return {'caseId': case['id'], 'operation': case['operation'], 'input': deepcopy(case['input']),
        'sourceScope': deepcopy(output['sourceScope']), 'evidenceClass': EVIDENCE[case['operation']],
        'applicability': 'StandardMsm66201_207_Documented_NotEcuApplicable', 'output': deepcopy(output),
        'state': deepcopy(state), 'branchOutcome': [{'pc': step['pc'], 'taken': step['branchTaken'], 'next': step['next']}
            for step in output['steps'] if step['kind'] == 'Branch'], 'reads': deepcopy(output['reads']),
        'orderedWrites': deepcopy(output['journal']), 'generationLineage': lineage,
        'intermediateStates': deepcopy(output['intermediateStates']),
        'unresolvedConstraints': deepcopy(output['unresolvedConstraints']), 'stopBoundary': output['stopBoundary'],
        'executionAuthority': {key: deepcopy(output[key]) for key in AUTHORITY}}


def canonical(value):
    import json
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('ascii')


def canonical_records():
    for case in cases():
        yield canonical(record(case, evaluate(case)))
