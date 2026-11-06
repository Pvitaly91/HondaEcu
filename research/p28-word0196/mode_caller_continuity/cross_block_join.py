"""Explicit mathematical state handoffs, without invented native call/return continuity."""
from copy import deepcopy
from post_consumer_continuation.stbuf_obligations import stbuf_boundary_obligations
from .data03cb_writers import data03cb_indexed_writer, WRITER_SITES
from .mode_producer_extended import mode_producer_extended, MODE_SITES
from .caller_cfg import configuration_caller, configuration_reader_caller, CONFIGURATION_SITES, READER_CALLER_SITES
from .primary_sources import binding_reason
from .state import Effects, Boundary, MODE_ENTRIES, input_class, need, validate

STAGE_ORDER = ['IndexedWriter', 'ModeProducer', 'ConfigurationCaller', 'ReaderCaller']
HANDOFFS = ('writerToMode', 'modeToConfiguration', 'configurationToReader')
SCOPE = tuple(sorted(set((*WRITER_SITES, *MODE_SITES, *CONFIGURATION_SITES, *READER_CALLER_SITES, 0x2995))))


def cross_block_source_join(query):
    need(type(query) is dict and set(query) == {'inputClass', 'sourceBinding', 'snapshot', 'modeEntry',
        'stageOrder', 'handoffs', 'noInterference', 'stbufQuery', 'claim'}, 'ClosedCrossBlockQueryRequired')
    input_class(query['inputClass'])
    validate(query['snapshot'])
    need(query['sourceBinding'] is None or type(query['sourceBinding']) is dict, 'TypedSourceBindingRequired')
    need(type(query['modeEntry']) is str and query['modeEntry'] in MODE_ENTRIES, 'ClosedExtendedModeEntryRequired')
    order = query['stageOrder']
    need(type(order) is list and len(order) <= 8 and all(type(v) is str and v in STAGE_ORDER for v in order), 'TypedBoundedStageOrderRequired')
    handoffs = query['handoffs']
    need(type(handoffs) is dict and set(handoffs) == set(HANDOFFS)
         and all(v is None or type(v) is bool for v in handoffs.values()), 'ThreeExplicitHandoffPremisesRequired')
    need(query['noInterference'] is None or type(query['noInterference']) is bool, 'TypedInterferencePremiseRequired')
    need(type(query['claim']) is str and query['claim'] in {'ConditionalOnly', 'NativeOwner', 'ActualHardware', 'RuntimeAdmission'}, 'ClosedSourceClaimRequired')
    stbuf = stbuf_boundary_obligations(query['stbufQuery'])
    need(query['snapshot']['inputClass'] == query['stbufQuery']['inputClass'] == query['inputClass'], 'SameQualifiedInputClassRequired')
    effects = Effects(query['snapshot'], 'cross_block_source_join', SCOPE)
    effects.specific.extend(('ExplicitHandoffsAreNotNativeContinuity', 'ReaderTo2995PathNotEstablished'))
    edges = []
    boundary = 0x5CA5
    try:
        if query['claim'] != 'ConditionalOnly':
            effects.halt('OutsideVerifiedScope', 'NativeOwnershipClaimNotEstablished', None)
        error = binding_reason(query['sourceBinding'])
        if error:
            effects.halt('OutsideVerifiedScope', error, None)
        if order != STAGE_ORDER:
            effects.halt('OutsideVerifiedScope', 'UnreviewedStageOrder', None)
        if stbuf['status'] == 'OutsideVerifiedScope':
            effects.halt('OutsideVerifiedScope', 'NestedStbufObligationRefused', boundary)
        if query['noInterference'] is not True:
            effects.halt('IndeterminateObligation', 'CrossBlockInterferenceNotExcluded', None)
        effects.admit(boundary)
        stages = (data03cb_indexed_writer, mode_producer_extended, configuration_caller, configuration_reader_caller)
        for index, function in enumerate(stages):
            if index:
                name = HANDOFFS[index - 1]
                premise = handoffs[name]
                edges.append({'edge': name, 'premise': premise,
                    'classification': 'ExplicitStateHandoffPremise' if premise is True else 'BlockedByNativeContinuity',
                    'nativeContinuityEstablished': False, 'fromBoundary': boundary,
                    'missingProof': ['ActualCallReturnFrame', 'NativeScheduling', 'InterveningWriterExclusion']})
                if premise is not True:
                    effects.halt('OutsideVerifiedScope' if premise is False else 'IndeterminateObligation',
                        'HandoffPremiseRejected' if premise is False else 'HandoffPremiseNotEstablished', boundary)
            snapshot = effects.snapshot(query['modeEntry'] if index == 1 else None)
            child = function(snapshot)
            effects.absorb(child)
            boundary = child['boundary']
            if child['status'] != 'CompleteConditional':
                effects.halt(child['status'], child['reason'], boundary)
            if index == 0 and child['conditionalData03cbWriterEstablished'] is not True:
                effects.halt('IndeterminateObligation', 'IndexedWriterDidNotEstablishData03cb', boundary)
        result = effects.finish('ConditionalSoftwareCompositionOnly', boundary)
    except Boundary as stopped:
        result = effects.result(stopped.status, stopped.reason, stopped.pc)
    result['state'].update(sourceEdges=deepcopy(edges), actualNativeContinuity=None,
        actualNativeData03cbOwner=None, actualCurrentStconOwner=None)
    result['stbufObligations'] = deepcopy(stbuf)
    return result
