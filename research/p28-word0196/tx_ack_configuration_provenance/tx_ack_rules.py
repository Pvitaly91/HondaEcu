"""Classified manufacturer obligations; no acknowledge or hardware event is performed."""
from copy import deepcopy
from .stcon_allocation import ACK_RULES
from .primary_sources import binding_reason
from .state import formal, input_class, need


def tx_ack_documentary_obligations(query):
    need(type(query) is dict and set(query) == {'inputClass', 'sourceBinding', 'rule', 'applicability', 'claim'},
         'ClosedAckQueryRequired')
    input_class(query['inputClass'])
    need(query['sourceBinding'] is None or type(query['sourceBinding']) is dict, 'TypedSourceBindingRequired')
    need(type(query['rule']) is str and query['rule'] in ACK_RULES, 'ClosedDocumentaryRuleRequired')
    need(type(query['applicability']) is str and query['applicability'] in {
        'QualifiedStandardProfile', 'UnknownActualEcu', 'ActualEcuVerified'}, 'TypedApplicabilityQualificationRequired')
    need(type(query['claim']) is str and query['claim'] in {
        'DocumentaryOnly', 'ActualAck', 'ActualTx', 'Fifo', 'TxCompleteIrq', 'RuntimeAdmission'}, 'ClosedAckClaimRequired')
    state = {'rule': query['rule'], 'relationship': deepcopy(ACK_RULES[query['rule']]),
        'applicability': query['applicability'], 'txReadyVector': 12, 'txReadyBit': 2,
        'txBrgVector': 36, 'txBrgBit': 14, 'rxReadyVector': 10, 'rxReadyBit': 1,
        'iePolarityResolution': None, 'actualPendingGeneration': None,
        'actualAcknowledge': None, 'physicalApplicability': None}
    status, reason = 'CompleteConditional', 'DocumentaryAckObligationsSpecified'
    error = binding_reason(query['sourceBinding'])
    if query['claim'] != 'DocumentaryOnly' or query['applicability'] == 'ActualEcuVerified':
        status, reason = 'OutsideVerifiedScope', 'UnestablishedTransmitAuthorityClaim'
    elif error:
        status, reason = 'OutsideVerifiedScope', error
    return formal('tx_ack_documentary_obligations', query, state, (0x2995,), status, reason,
        ('HardwareApplicabilityUnknown', 'TxSpecificAckAndReassertionNotEstablished',
         'IePolaritySourceConflictRetained', 'NoAcknowledgeEventPerformed'),
        'ManufacturerAckObligations_NotPeripheralSimulation')
