"""Independent source windows remain separate until a reaching CFG edge is established."""
from post_consumer_continuation.stbuf_obligations import stbuf_boundary_obligations
from .reader_cfg import tx_configuration_reader, READER_SITES
from .mode_producer import mode_bit1_producer, PRODUCER_SITES
from .reaching_definitions import tx_configuration_reaching_definitions
from .tx_ack_rules import tx_ack_documentary_obligations
from .primary_sources import binding_reason
from .state import formal, input_class, need


def stbuf2995_configuration_provenance(query):
    names = ('readerQuery', 'producerQuery', 'reachingQuery', 'ackQuery', 'stbufQuery')
    need(type(query) is dict and set(query) == {'inputClass', 'sourceBinding', *names, 'claim'},
         'ClosedConfigurationProvenanceQueryRequired')
    input_class(query['inputClass'])
    need(query['sourceBinding'] is None or type(query['sourceBinding']) is dict, 'TypedSourceBindingRequired')
    need(type(query['claim']) is str and query['claim'] in {
        'ConditionalOnly', 'NativeOwner', 'ActualTx', 'RuntimeAdmission'}, 'ClosedProvenanceClaimRequired')
    parts = [fn(query[name]) for name, fn in zip(names, (tx_configuration_reader, mode_bit1_producer,
        tx_configuration_reaching_definitions, tx_ack_documentary_obligations, stbuf_boundary_obligations))]
    need(all(query[name]['inputClass'] == query['inputClass'] for name in names), 'SameQualifiedInputClassRequired')
    state = dict(zip(('reader', 'producer', 'reaching', 'ack', 'stbuf'), parts))
    state.update(actualNativeConfigurationOwner=None, actualTxReadiness=None, continuousCfgEstablished=False)
    status, reason = 'IndeterminateObligation', 'ConfigurationTo2995PathNotEstablished'
    error = binding_reason(query['sourceBinding'])
    if query['claim'] != 'ConditionalOnly':
        status, reason = 'OutsideVerifiedScope', 'UnestablishedTransmitAuthorityClaim'
    elif error:
        status, reason = 'OutsideVerifiedScope', error
    elif any(part['status'] == 'OutsideVerifiedScope' for part in parts):
        status, reason = 'OutsideVerifiedScope', 'NestedSourceObligationRefused'
    elif any(part['status'] != 'CompleteConditional' for part in parts):
        reason = 'NestedConditionalPremisesNotEstablished'
    return formal('stbuf2995_configuration_provenance', query, state,
        (*READER_SITES, *PRODUCER_SITES, 0x286D, 0x288C, 0x2995), status, reason,
        ('NativeConfigurationTo2995ContinuityNotEstablished',
         'PhysicalTransmitterReadinessNotEstablished', 'NoStbufWritePerformed'),
        'ConditionalConfigurationProvenance_NotPeripheralAdmission')
