"""Source-bounded DATA03CB retention and prospective CAL2777 frame hazards."""
from copy import deepcopy

from cold_return_c8_writer_proof.competing_writers import data03cb_competing_writer_exclusion
from enclosing_caller_return.call_return_obligations import frame_alias
from enclosing_caller_return.state import input_class, label, need, number, shape, slot, tri

SOURCE = 'M2dbHelperWriterFootprintV1'
CLAIMS = ('ConditionalOnly', 'NativeOwner', 'ModeConsumerReached', 'ActualHardware', 'RuntimeAdmission')
SCOPE = (0x2777, 0x5CB4, 0x5CD9, 0x5CDC, 0x5CDF, 0x5CEF, 0x5CF1, 0x5CF4, 0x5CF6, 0x5CF8, 0x5CF9)
FOOTPRINTS = ((0x5CD9, 0x0084, 16), (0x5CEF, 0x00AF, 8), (0x5CF1, 0x00F7, 8), (0x5CF6, 0x00F5, 8))
GAPS = ('PrimaryC8ConflictUnresolved', 'FullHelperNormalIngressUnestablished', 'NativeModeRead60ccUnbound')
COMPLETE, UNKNOWN, OUTSIDE = 'CompleteConditional', 'IndeterminateObligation', 'OutsideVerifiedScope'


def _pre_helper_event(event):
    kind = event.get('kind')
    if kind == 'Frame':
        return event.get('pc') == 0x276A
    if kind == 'Local':
        return event.get('pc') == 0x2766
    return kind in ('Indexed', 'OffPage', 'Unknown')


def _prior_generations(writer, query):
    initial = query['initialTimeline']['initial'].values()
    writes = (*writer['frozenWriter']['orderedWrites'], *writer['orderedWrites'])
    return {row['generation'] for row in (*initial, *writes)}


def _formal_high_slot(generation):
    return {'value': 0x27, 'knownBits': {}, 'generation': generation}


def data03cb_post_helper_lineage(query):
    """Check a write envelope without choosing a helper branch or performing a frame write."""
    shape(query, ('inputClass', 'sourceBinding', 'writerQuery', 'requestedGeneration', 'helperFrame',
                  'helperScb', 'data03d1', 'noInterference', 'claim'), 'ClosedPostHelperLineageRequired')
    input_class(query['inputClass'])
    need(query['claim'] in CLAIMS and label(query['sourceBinding']) and label(query['requestedGeneration'])
         and number(query['helperScb'], 7) and tri(query['noInterference']), 'TypedPostHelperLineageRequired')
    frame = query['helperFrame']
    shape(frame, ('incomingSsp', 'creatorPc', 'generation', 'memoryApplicable'), 'ClosedProspectiveHelperFrameRequired')
    need(number(frame['incomingSsp'], 0xFFFF) and number(frame['creatorPc'], 0xFFFF)
         and label(frame['generation']) and tri(frame['memoryApplicable']), 'TypedProspectiveHelperFrameRequired')
    writer_query = query['writerQuery']
    need(type(writer_query) is dict and writer_query.get('inputClass') == query['inputClass'],
         'PostHelperWriterInputClassMismatch')
    data03d1 = slot(query['data03d1'])
    writer = candidate = formal_frame = counter_hazard = None
    after_03cb = after_03d1 = None
    same_03cb = same_03d1 = None

    def finish(status, reason):
        retained = status == COMPLETE
        return deepcopy({
            'status': status, 'reason': reason, 'sourceScope': list(SCOPE),
            'stopBoundary': 'STOP_BEFORE_HELPER_5CD9' if retained else 'STOP_BEFORE_CAL_2777',
            'state': {'candidateGeneration': None if candidate is None else candidate['generation'],
                      'data03cbAfterFormalCall': after_03cb, 'data03d1AfterFormalCall': after_03d1,
                      'sameValue03cbFrameWrite': same_03cb, 'sameValue03d1FrameWrite': same_03d1,
                      'formalFrame': formal_frame, 'counterFrameHazard': counter_hazard,
                      'conditionalHelperBodyRetainedGeneration': candidate['generation'] if retained else None,
                      'selectedHelperFrontier': None, 'connectedModeRead': False, 'nativeOwner': None},
            'bodyWriteScope': 'SelectedScb0ConditionalDataMapping',
            'bodyWriterFootprints': [{'pc': pc, 'address': addr, 'widthBits': width}
                                     for pc, addr, width in FOOTPRINTS],
            'possibleStaticTermini': ['STOP_BEFORE_BRK_5CF8', 'STOP_BEFORE_RT_5CF9'],
            'unresolvedConstraints': list(GAPS if retained else (*GAPS, reason)),
            'frozenWriter': writer,
        })

    if query['claim'] != 'ConditionalOnly':
        return finish(OUTSIDE, 'NonConditionalPostHelperClaim')
    if query['sourceBinding'] != SOURCE:
        return finish(UNKNOWN if query['sourceBinding'] is None else OUTSIDE, 'ExactHelperWriterSourceRequired')
    events = writer_query.get('events')
    need(type(events) is list and all(type(event) is dict for event in events), 'TypedPreHelperEventsRequired')
    if not all(_pre_helper_event(event) for event in events):
        return finish(OUTSIDE, 'WriterEventOutsidePreHelperWindow')
    writer = data03cb_competing_writer_exclusion(writer_query)
    candidate = writer['state']['candidate']
    if writer['status'] != COMPLETE:
        return finish(writer['status'], writer['reason'])
    if candidate['generation'] != query['requestedGeneration']:
        return finish(UNKNOWN, 'RequestedPostHelperGenerationUnlinked')
    if query['helperScb'] != 0 or query['noInterference'] is not True:
        return finish(UNKNOWN, 'HelperMappingOrInterferenceUnestablished')
    if frame['creatorPc'] is None or frame['generation'] is None:
        return finish(UNKNOWN, 'ProspectiveHelperFrameOwnerUnbound')
    if frame['creatorPc'] != 0x2777:
        return finish(OUTSIDE, 'WrongProspectiveHelperFrameCreator')
    if frame['incomingSsp'] is None or frame['memoryApplicable'] is not True:
        return finish(UNKNOWN, 'ProspectiveHelperFrameGeometryOrMappingUnbound')
    generation = frame['generation']
    if generation in _prior_generations(writer, writer_query) or generation == data03d1['generation']:
        return finish(OUTSIDE, 'ProspectiveHelperFrameGenerationReused')

    address = frame['incomingSsp'] & 0xFFFE
    formal_frame = {'creatorPc': 0x2777, 'address': address, 'widthBits': 16,
                    'returnCandidate': 0x277A, 'generation': generation, 'effectClass': 'FormalWriteOnly'}
    after_03cb, after_03d1 = candidate, data03d1
    if address == 0x03CA:
        after_03cb = {**_formal_high_slot(generation), 'writerPc': 0x2777, 'iterationId': None}
        same_03cb = None if candidate['value'] is None else candidate['value'] == after_03cb['value']
        return finish(UNKNOWN, 'ProspectiveHelperFrameReownsData03cb')
    if address == 0x03D0:
        after_03d1 = _formal_high_slot(generation)
        same_03d1 = None if data03d1['value'] is None else data03d1['value'] == after_03d1['value']
        return finish(UNKNOWN, 'ProspectiveHelperFrameReownsData03d1')
    if address == 0x00F6:
        counter_hazard = {'counterAddress': 0x00F7, 'savedHighBefore': 0x27, 'decrementHighCandidate': 0x26,
                          'incrementHighCandidate': 0x28, 'nonzeroUnderBothUpdates': True,
                          'originalReturnWordPreserved': False, 'requiresAdmittedFaultArm': True}
        return finish(OUTSIDE, 'CounterAliasCannotPreserveCandidateReturn')
    if (frame_alias(address, False) != 'OrdinaryDataCandidate' or address == 0x4700 or
            any(address <= addr < address + 2 or addr <= address < addr + width // 8
                for _, addr, width in FOOTPRINTS)):
        return finish(OUTSIDE, 'ProspectiveHelperFrameAliasesControlOrFixedWrite')
    return finish(COMPLETE, 'HelperBodyFootprintPreservesData03cbGeneration')
