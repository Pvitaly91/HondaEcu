"""Reviewed local software effects and SFR write intents, never peripheral state."""
from copy import deepcopy
from .source_inventory import CONFIG_SITES, binding_reason
from .state import Boundary, Effects, formal, input_class, intents, need, slot_values


def stcon_configuration(snapshot):
    effects = Effects(snapshot, 'stcon_configuration', CONFIG_SITES)
    try:
        effects.admit(0x286D)
        effects.store(0x286D, 0x208, [0x1C], 'LocalRegisterWrite', 'Literal')
        effects.step(0x286D, 0x286F)
        effects.store(0x286F, 0x209, [0x8C], 'LocalRegisterWrite', 'Literal')
        effects.step(0x286F, 0x2871)
        effects.literal_byte(0x2871, 0xDF, 0x2873)
        if effects.r['scb'] is None:
            effects.halt('OutsideVerifiedScope', 'PointerBankNotEstablished', 0x2873)
        address = 0x84 + 8 * effects.r['scb']
        effects.store(0x2873, address, [0x56, 3], 'PointingRegisterWrite', 'Literal')
        effects.step(0x2873, 0x2876)
        effects.pointer_dependency(0x2876)
        effects.r['cf'] = effects.read_bit(0x2876, 0x356, 1)
        effects.step(0x2876, 0x2878)
        taken = None if effects.r['cf'] is None else bool(effects.r['cf'])
        if not effects.branch(0x2878, taken, 0x2880, 0x287A):
            effects.store(0x287A, 0x208, [0x31], 'LocalRegisterWrite', 'Literal')
            effects.step(0x287A, 0x287C)
            effects.store(0x287C, 0x209, [0xA1], 'LocalRegisterWrite', 'Literal')
            effects.step(0x287C, 0x287E)
            effects.literal_byte(0x287E, 0xFB, 0x2880)
        effects.sfr_intent(0x2880, 0x48, effects.r['al'], 0x2882)
        effects.sfr_intent(0x2882, 0x49, effects.r['al'], 0x2884)
        effects.sfr_intent(0x2884, 0x4A, 0x12, 0x2888, literal=True)
        effects.load_byte(0x2888, 0x208, 0x2889)
        effects.sfr_intent(0x2889, 0x50, effects.r['al'], 0x288B)
        effects.load_byte(0x288B, 0x209, 0x288C)
        effects.sfr_intent(0x288C, 0x54, effects.r['al'], 0x288E)
        return effects.finish('SerialConfigurationIntentsPrepared', 0x288E)
    except Boundary as boundary:
        return effects.result(boundary.status, boundary.reason, boundary.pc)


def consensus(values):
    values = set(values)
    return next(iter(values)) if len(values) == 1 else None


def transmit_configuration_hypotheses(query):
    from .tx_documentary_rules import STTMC
    need(type(query) is dict and set(query) == {'inputClass', 'sourceBinding', 'configurationIntents', 'claim'},
         'ClosedConfigurationHypothesesRequired')
    input_class(query['inputClass'])
    intents(query['configurationIntents'])
    need(query['sourceBinding'] is None or type(query['sourceBinding']) is dict, 'TypedSourceBindingRequired')
    need(type(query['claim']) is str and query['claim'] in {'DocumentaryOnly', 'ActualEcuApplicable',
        'ActualOwner', 'ActualReady', 'Rx000ATx'}, 'ClosedHypothesesClaimRequired')
    values = {k: slot_values(v) for k, v in query['configurationIntents'].items()}
    stcon, timer, receive = values['0050'], values['004A'], values['0054']
    def bits(domain, start, width=1):
        return consensus((v >> start) & ((1 << width) - 1) for v in domain)
    serial = {0: 'UART', 1: 'Synchronous'}.get(bits(stcon, 1))
    protocol = {0: 'Normal', 1: 'Multiprocessor'}.get(bits(stcon, 0)) if serial == 'UART' else None
    parity = bits(stcon, 5)
    counter, reload = values['0048'], values['0049']
    equal = (True if len(counter) == len(reload) == 1 and counter == reload else
             False if not counter & reload else None)
    decoded = {'serialMode': serial, 'uartProtocol': protocol,
        'normalLengthCode': bits(stcon, 2, 2) if protocol == 'Normal' else None,
        'multiprocessorDataAddress': {0: 'Data', 1: 'Address'}.get(bits(stcon, 2)) if protocol == 'Multiprocessor' else None,
        'multiprocessorBit3Ignored': None if protocol is None else protocol == 'Multiprocessor',
        'uartStopLengthCode': bits(stcon, 4) if serial == 'UART' else None,
        'synchronousClockRole': {0: 'Slave', 1: 'Master'}.get(bits(stcon, 4)) if serial == 'Synchronous' else None,
        'paritySelectionBit5': parity, 'bit6MeaningfulWhenBit5One': None if parity is None else bool(parity),
        'stconBit7Meaning': None, 'baudGeneratorModeCode': bits(timer, 0, 2),
        'baudGeneratorMode': consensus(STTMC['modeTable'][str(v & 3)] for v in timer),
        'baudGeneratorRunBit': bits(timer, 4), 'baudGeneratorClockCode': bits(timer, 5, 3),
        'baudGeneratorClockDivisor': consensus(STTMC['clockDivisorsByCode'][v >> 5] for v in timer),
        'baudCounterAndReloadDeclaredEqual': equal, 'sttmcDocumentedReadBits': {'2': 1, '3': 1},
        'srconMode': consensus(('UARTNormal', 'UARTMultiprocessor', 'SynchronousNormal',
                                'SynchronousMultiprocessor')[v & 3] for v in receive),
        'srconReceivingPermission': {0: 'ReceivingProhibited', 1: 'ReceivingAllowed'}.get(bits(receive, 7)),
        'effectiveBaudRate': None}
    predicates = [{'sourcePc': pc, 'address': address, 'mask': mask, 'expected': expected,
        'matches': consensus(v & mask == expected for v in values[f'{address:04X}']),
        'requiredGuard': 'DATA0356.1=1_NotObserved',
        'classification': 'ConditionalDeclaredSlotPredicate_NotPerformedRead'}
        for pc, address, mask, expected in ((0x3FDF, 0x4A, 0xF3, 0x12), (0x3FE7, 0x50, 0x7F, 0x1C),
                                           (0x3FEB, 0x54, 255, 0x8C), (0x3FF1, 0x49, 255, 0xDF))]
    unknown = ['STCON_FULL_LENGTH_STOP_PARITY_ENCODING', 'STCON_BIT7_OR_TX_PERMISSION_FIELD',
        'GENERAL_BAUD_RATE_FORMULA', 'ACTUAL_ECU_APPLICABILITY', 'ACTUAL_NATIVE_TX_READINESS']
    unknown.extend('UnknownDeclaredByte:' + key for key in sorted(values) if len(values[key]) != 1)
    status, reason = 'CompleteConditional', 'DocumentaryConfigurationRelationshipsOnly'
    source_error = binding_reason(query['sourceBinding'])
    if query['claim'] != 'DocumentaryOnly':
        status, reason = 'OutsideVerifiedScope', 'UnestablishedHardwareConfigurationClaim'
    elif source_error:
        status, reason = 'OutsideVerifiedScope', source_error
    scope = (*CONFIG_SITES, 0x3FD4, 0x3FD7, 0x3FD9, 0x3FDB, 0x3FDD, 0x3FDF, 0x3FE1, 0x3FE3,
             0x3FE5, 0x3FE7, 0x3FE9, 0x3FEB, 0x3FEF, 0x3FF1, 0x3FF5, 0x2995)
    return formal('transmit_configuration_hypotheses', query,
        {'configurationIntents': deepcopy(query['configurationIntents']), 'decoded': decoded,
         'unknownFields': unknown, 'reviewedMaskedPredicates': predicates, 'actualEcuApplicability': None,
         'actualConfigurationOwner': None, 'actualReady': None}, scope, status, reason,
        ('PhysicalMcuApplicabilityNotEstablished', 'NativeConfigurationOwnerNotEstablished',
         'StconFieldEncodingPartiallyUnavailable', 'NoPhysicalBaudRateEstablished'),
        'DocumentaryConfigurationHypotheses_NotHardwareState')
