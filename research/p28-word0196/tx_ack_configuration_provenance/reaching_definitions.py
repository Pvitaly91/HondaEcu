"""Declared generations do not create missing inter-block control-flow edges."""
from copy import deepcopy
from stbuf_stcon_transmit_source.lineage import stcon_writer_lineage
from .primary_sources import binding_reason
from .state import formal, input_class, need, label

PATHS = ('ConfigurationSuffix', 'ReaderWindow', 'ProducerToConfiguration',
         'ConfigurationTo2995', 'ReaderTo2995')
REACHING_SCOPE = (0x2889, 0x288B, 0x288C, 0x288E, 0x3FD4, 0x3FF5, 0x2995, 0x60D5)


def tx_configuration_reaching_definitions(query):
    need(type(query) is dict and set(query) == {'inputClass', 'sourceBinding', 'timelineQuery',
        'path', 'entryGeneration', 'requestedGeneration', 'noInterference', 'claim'}, 'ClosedReachingQueryRequired')
    input_class(query['inputClass'])
    need(query['sourceBinding'] is None or type(query['sourceBinding']) is dict, 'TypedSourceBindingRequired')
    need(type(query['path']) is str and query['path'] in PATHS, 'ClosedSourcePathRequired')
    need(label(query['entryGeneration']) and label(query['requestedGeneration']), 'TypedGenerationLabelsRequired')
    need(query['noInterference'] is None or type(query['noInterference']) is bool, 'TypedInterferencePremiseRequired')
    need(type(query['claim']) is str and query['claim'] in {'ConditionalOnly', 'NativeOwner', 'ActualTx'},
         'ClosedReachingClaimRequired')
    timeline = stcon_writer_lineage(query['timelineQuery'])
    need(query['timelineQuery']['inputClass'] == query['inputClass'], 'SameQualifiedInputClassRequired')
    current = timeline['state']['lastSlot']['generation']
    kind = timeline['state']['lastKind']
    status, relation, reason = 'CompleteConditional', 'ConditionalWriterRetained', 'ConditionalBoundedWriterRetained'
    error = binding_reason(query['sourceBinding'])
    if query['claim'] != 'ConditionalOnly':
        status, relation, reason = 'OutsideVerifiedScope', 'SourceConflict', 'UnestablishedNativeOwnerClaim'
    elif error:
        status, relation, reason = 'OutsideVerifiedScope', 'SourceConflict', error
    elif timeline['status'] == 'OutsideVerifiedScope':
        status, relation, reason = 'OutsideVerifiedScope', 'SourceConflict', 'DeclaredTimelineRefused'
    else:
        status = 'IndeterminateObligation'
        if query['noInterference'] is not True or query['timelineQuery']['noInterference'] is not True or kind == 'UnknownWriter':
            relation, reason = 'UnknownInterference', 'InterferenceNotExcluded'
        elif kind != 'ConfigIntent':
            relation, reason = 'CompetingWriter', 'CompetingConfigurationWriter'
        elif None in (current, query['entryGeneration'], query['requestedGeneration']):
            relation, reason = 'MissingReachingPath', 'MissingGenerationObligation'
        elif current != query['entryGeneration']:
            relation, reason = 'CompetingWriter', 'EntryGenerationReplaced'
        elif query['requestedGeneration'] != current:
            relation, reason = 'StaleGeneration', 'StaleRequestedGeneration'
        elif query['path'] not in ('ConfigurationSuffix', 'ReaderWindow'):
            relation, reason = 'MissingReachingPath', 'SourceCfgEdgeNotEstablished'
        else:
            status = 'CompleteConditional'
    state = {'timeline': deepcopy(timeline), 'reachingDefinitions': {'path': query['path'],
        'entryGeneration': query['entryGeneration'], 'requestedGeneration': query['requestedGeneration'],
        'currentGeneration': current, 'relation': relation}, 'actualNativeOwner': None}
    return formal('tx_configuration_reaching_definitions', query, state, REACHING_SCOPE, status, reason,
        ('DeclaredConfigurationHistoryOnly', 'NativeStconOwnerNotEstablished',
         'ConfigurationTo2995PathNotEstablished'), 'ConditionalSourceReachingDefinitions')
