"""Formal byte-store prerequisites; no DATA0051 read, latch, or write is modeled."""
from copy import deepcopy
from .source_inventory import SOURCE_BINDING, binding_matches
from .state import COMMON, frozen, need, number, slot, slot_values

PREMISES = ('deviceApplicability', 'physicalByteAccessAndSf', 'accessMapping', 'peripheralOwnership',
            'transmitterReady', 'clockResetStconGeneration', 'serialConfiguration',
            'peripheralInterferenceExcluded', 'acceptanceSemantics', 'irqAckCollisionSemantics')
SPECIFIC = ('PhysicalMcuApplicabilityNotEstablished', 'StbufLifecycleAndOwnershipNotEstablished',
            'NoPeripheralOperationPerformed')


def stbuf_boundary_obligations(query):
    need(type(query) is dict and set(query) == {'inputClass', 'sourceBinding', 'pc', 'dd',
        'prospectiveAL', 'softwareReached', 'softwareNoInterference', 'premises', 'claim'},
        'ClosedStbufObligationQueryRequired')
    need(type(query['inputClass']) is str and query['inputClass'] in frozen.inherited.INPUT_CLASSES,
         'ActualHardwareInputNotAdmitted')
    need(query['sourceBinding'] is None or type(query['sourceBinding']) is dict, 'TypedSourceBindingRequired')
    need(number(query['pc'], 65535) and number(query['dd'], 1), 'TypedStbufContextRequired')
    for key in ('softwareReached', 'softwareNoInterference'):
        need(query[key] is None or type(query[key]) is bool, 'TypedSoftwarePremiseRequired')
    slot(query['prospectiveAL'])
    premises = query['premises']
    need(type(premises) is dict and set(premises) == set(PREMISES)
         and all(v is None or type(v) is bool for v in premises.values()), 'TypedPeripheralPremisesRequired')
    need(type(query['claim']) is str and query['claim'] in {
        'ObligationsOnly', 'ActualBufferWrite', 'ActualTransmit', 'TxComplete', 'IRQ', 'CpuExecution'},
        'ClosedPeripheralClaimRequired')
    missing = []
    for key, reason in (('pc', 'UnknownBoundaryPc'), ('dd', 'UnknownByteDescriptor'),
                        ('softwareReached', 'SoftwareBoundaryNotEstablished'),
                        ('softwareNoInterference', 'SoftwareInterferenceNotExcluded')):
        if query[key] is None:
            missing.append(reason)
    if len(slot_values(query['prospectiveAL'])) != 1:
        missing.append('ProspectiveAlUnknown')
    if query['prospectiveAL']['generation'] is None:
        missing.append('ProspectiveAlGenerationUnknown')
    missing.extend('PremiseUnknown:' + key for key in PREMISES if premises[key] is None)
    status, reason = 'CompleteConditional', 'HypotheticalStbufObligationsSpecified'
    if query['claim'] != 'ObligationsOnly':
        status, reason = 'OutsideVerifiedScope', 'PeripheralExecutionNotAuthorized'
    elif query['sourceBinding'] is None:
        status, reason = 'OutsideVerifiedScope', 'SourceBindingMissing'
    elif not binding_matches(query['sourceBinding']):
        status, reason = 'OutsideVerifiedScope', 'SourceBindingMismatch'
    elif query['pc'] is not None and query['pc'] != 0x2995:
        status, reason = 'OutsideVerifiedScope', 'WrongStbufBoundary'
    elif query['dd'] == 1:
        status, reason = 'OutsideVerifiedScope', 'WordStoreInterpretationNotByteStbuf'
    elif query['softwareReached'] is False or query['softwareNoInterference'] is False:
        status, reason = 'OutsideVerifiedScope', 'DeclaredSoftwarePremiseFalse'
    elif any(v is False for v in premises.values()):
        status, reason = 'OutsideVerifiedScope', 'DeclaredPeripheralPremiseFalse'
    elif missing:
        status, reason = 'IndeterminateObligation', 'StbufObligationsNotEstablished'
    constraints = [*COMMON, *SPECIFIC]
    if status != 'CompleteConditional' and reason not in constraints:
        constraints.append(reason)
    return {'procedure': 'stbuf_boundary_obligations', 'status': status, 'reason': reason,
        'boundary': 0x2995, 'inputClass': query['inputClass'], 'sourceScope': [0x2995],
        'state': {'prospectiveAL': deepcopy(query['prospectiveAL']), 'descriptorDD': query['dd'],
            'destinationAddress': 0x51, 'widthBits': 8, 'form': 'STB A,N8', 'instructionLength': 2,
            'retainedFlags': ['CF', 'ZF', 'HC', 'DD'], 'resetValue': None, 'readbackNotSpecified': True,
            'declaredPremisesNotObserved': True, 'actualBufferWrite': None, 'actualAcceptance': None,
            'actualTransmission': None, 'actualCompletion': None, 'actualTxIrq': None},
        'reads': [], 'journal': [], 'steps': [], 'intermediateStates': [], 'missingPremises': missing,
        'unresolvedConstraints': constraints, 'effectClass': 'FormalStbufObligations_NotPeripheralOperation',
        'actualHardwareObservation': None, 'cpuInstructionRetirements': 0,
        'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False}


def unknown_query(effects):
    return {'inputClass': effects.input['inputClass'], 'sourceBinding': deepcopy(SOURCE_BINDING),
        'pc': 0x2995, 'dd': effects.r['dd'], 'prospectiveAL': {'value': effects.r['al'],
            'knownBits': {k[-1]: v for k, v in effects.state['registerKnownBits'].items() if k.startswith('AL.')},
            'generation': 'ConditionalAl:298F:DATA03F1&1F'}, 'softwareReached': True,
        'softwareNoInterference': effects.input['assumptions']['noInterference'],
        'premises': dict.fromkeys(PREMISES), 'claim': 'ObligationsOnly'}
