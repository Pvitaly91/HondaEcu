"""Documentary TX relationships and a software-source join; no peripheral operation."""
from post_consumer_continuation.stbuf_obligations import stbuf_boundary_obligations
from .configuration import transmit_configuration_hypotheses
from .lineage import stcon_writer_lineage
from .source_inventory import CONFIG_SITES, binding_reason
from .state import formal, input_class, need


def tx_lifecycle_obligations(query):
    from .tx_documentary_rules import SITUATIONS
    need(type(query) is dict and set(query) == {'inputClass', 'sourceBinding', 'situation', 'applicability', 'claim'},
         'ClosedTransmitLifecycleQueryRequired')
    input_class(query['inputClass'])
    need(query['sourceBinding'] is None or type(query['sourceBinding']) is dict, 'TypedSourceBindingRequired')
    need(type(query['situation']) is str and query['situation'] in SITUATIONS, 'ClosedDocumentarySituationRequired')
    need(type(query['applicability']) is str and query['applicability'] in {
        'QualifiedStandardProfile', 'UnknownActualEcu', 'ActualEcuVerified'}, 'TypedApplicabilityQualificationRequired')
    need(type(query['claim']) is str and query['claim'] in {
        'DocumentaryOnly', 'ActualTx', 'Fifo', 'TxCompleteIrq', 'AckByWrite', 'Rx000ATx'}, 'ClosedTransmitClaimRequired')
    state = {'situation': query['situation'], 'applicability': query['applicability'],
        'documentedRules': SITUATIONS[query['situation']]['documentedRules'],
        'unknownRules': SITUATIONS[query['situation']]['unknownRules'],
        'txReadyVector': 0xC, 'txReadyBit': 2, 'txBrgVector': 0x24, 'txBrgBit': 14,
        'rxReadyVector': 0xA, 'rxReadyBit': 1, 'iePolarityResolution': None,
        'physicalApplicability': None, 'actualPendingGeneration': None}
    status, reason = 'CompleteConditional', 'DocumentaryTransmitObligationsSpecified'
    source_error = binding_reason(query['sourceBinding'])
    if query['claim'] != 'DocumentaryOnly' or query['applicability'] == 'ActualEcuVerified':
        status, reason = 'OutsideVerifiedScope', 'UnestablishedTransmitAuthorityClaim'
    elif source_error:
        status, reason = 'OutsideVerifiedScope', source_error
    return formal('tx_lifecycle_obligations', query, state, (0x2995,), status, reason,
        ('HardwareApplicabilityUnknown', 'ActualNativeObservationNotEstablished',
         'TxAckReassertionCollisionNotEstablished', 'IePolaritySourceConflictRetained'),
        'ManufacturerTxObligations_NotPeripheralSimulation')


def stbuf2995_source_join(query):
    names = ('configurationQuery', 'lineageQuery', 'lifecycleQuery', 'stbufQuery')
    need(type(query) is dict and set(query) == {'inputClass', 'sourceBinding', *names, 'claim'},
         'ClosedStbufSourceJoinRequired')
    input_class(query['inputClass'])
    need(query['sourceBinding'] is None or type(query['sourceBinding']) is dict, 'TypedSourceBindingRequired')
    need(type(query['claim']) is str and query['claim'] in {
        'ConditionalOnly', 'ActualTx', 'NativeOwner', 'RuntimeAdmission'}, 'ClosedJoinClaimRequired')
    configuration = transmit_configuration_hypotheses(query['configurationQuery'])
    lineage = stcon_writer_lineage(query['lineageQuery'])
    lifecycle = tx_lifecycle_obligations(query['lifecycleQuery'])
    stbuf = stbuf_boundary_obligations(query['stbufQuery'])
    need(all(query[name]['inputClass'] == query['inputClass'] for name in names), 'SameQualifiedInputClassRequired')
    state = {'configuration': configuration, 'lineage': lineage, 'lifecycle': lifecycle, 'stbuf': stbuf,
             'actualNativeConfigurationOwner': None, 'actualTxReadiness': None}
    status, reason = 'CompleteConditional', 'ConditionalSoftwareAndDocumentaryJoinOnly'
    source_error = binding_reason(query['sourceBinding'])
    if query['claim'] != 'ConditionalOnly':
        status, reason = 'OutsideVerifiedScope', 'UnestablishedTransmitAuthorityClaim'
    elif source_error:
        status, reason = 'OutsideVerifiedScope', source_error
    elif any(part['status'] == 'OutsideVerifiedScope' for part in (configuration, lineage, lifecycle, stbuf)):
        status, reason = 'OutsideVerifiedScope', 'NestedSourceObligationRefused'
    elif lineage['state']['lastSlot'] != query['configurationQuery']['configurationIntents']['0050']:
        status, reason = 'OutsideVerifiedScope', 'ConfigurationLineageMismatch'
    elif not lineage['configurationChecks'] or lineage['configurationChecks'][-1]['relation'] != 'ConditionalConfigurationWriterAtBoundary':
        status, reason = 'IndeterminateObligation', 'ConfigurationWriterAt2995NotEstablished'
    elif stbuf['status'] != 'CompleteConditional':
        status, reason = 'IndeterminateObligation', 'StbufPrerequisitesNotEstablished'
    return formal('stbuf2995_source_join', query, state, (*CONFIG_SITES, 0x2995), status, reason,
        ('NativeConfigurationTo2995ContinuityNotEstablished', 'PhysicalTransmitterReadinessNotEstablished',
         'NoStbufWritePerformed'), 'ConditionalSoftwareDocumentaryJoin_NotPeripheralAdmission')
