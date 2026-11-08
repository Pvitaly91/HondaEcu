"""Prove a detached cold DATA03CB generation through the frozen mode reader."""

from enclosing_caller_return.call_return_obligations import call_return_obligations
from enclosing_caller_return.state import input_class, label, need, shape, tri, validate
from cold_return_c8_writer_proof.competing_writers import (
    data03cb_competing_writer_exclusion, usp27b2_alias_proof,
)
from mode_middle_corridor.composition import mode_enclosing_continuation

from .wire import result

SOURCE = 'M2daColdModeWindowV1'
CLAIMS = ('ConditionalOnly', 'NativeOwner', 'ActualHardware')
PREMISES = ('detached277a', 'reviewedPath', 'noInterference')
COMPLETE, UNKNOWN, OUTSIDE = 'CompleteConditional', 'IndeterminateObligation', 'OutsideVerifiedScope'
WINDOW_SCOPE = (0x277A, 0x279E, 0x27A2, 0x27AE, 0x27B0, 0x27B2, 0x27C5, 0x27CA,
                0x27CC, 0x27CE, 0x27D0, 0x7C0B, 0x7C11)
MODE_SCOPE = (*WINDOW_SCOPE, 0x5F45, 0x60C0, 0x60C9, 0x60CC, 0x60E4)
WINDOW_GAPS = ('NativeHelperReturnUnestablished', 'NativeUspOwnerUnbound', 'NativeModeEntryUnobserved')
MODE_GAPS = ('NativeHelperReturnUnestablished', 'NativeData03cbOwnerUnbound', 'NativeModeReadUnobserved')
CORRIDOR_BRANCHES = (
    {'pc': 0x27C5, 'taken': None, 'next': None, 'possibleSuccessors': [0x27CC, 0x27C7]},
    {'pc': 0x27CA, 'taken': None, 'next': None, 'possibleSuccessors': [0x27CE, 0x27CC]},
)


def _matching_class(query, fields):
    input_class(query['inputClass'])
    need(query['claim'] in CLAIMS, 'TypedDetachedModeClaimRequired')
    need(all(type(query[key]) is dict and query[key].get('inputClass') == query['inputClass']
             for key in fields), 'DetachedModeInputClassMismatch')


def _before_detached_window(event):
    kind = event.get('kind')
    if kind == 'Frame':
        return event.get('pc') in (0x276A, 0x2777)
    if kind == 'Local':
        return event.get('pc') == 0x2766
    return kind in ('Indexed', 'OffPage', 'Unknown')


def _occupied_generations(writer, initial):
    return {row['generation'] for row in initial['initial'].values()} | {
        row['generation'] for row in (*writer['frozenWriter']['orderedWrites'], *writer['orderedWrites'])
    }


def cold_to_mode_intervening_writes(query):
    """Retain only the byte and USP lineage across an independently qualified 277A entry."""
    shape(query, ('inputClass', 'sourceBinding', 'writerQuery', 'uspProof', 'modeFrame', 'premises', 'claim'),
          'ClosedDetachedColdWindowRequired')
    _matching_class(query, ('writerQuery', 'uspProof', 'modeFrame'))
    need(label(query['sourceBinding']), 'TypedDetachedColdSourceRequired')
    shape(query['premises'], PREMISES, 'ClosedDetachedColdPremisesRequired')
    need(all(tri(value) for value in query['premises'].values()), 'TypedDetachedColdPremisesRequired')

    writer = usp = frame = candidate = carried = None
    frame_address = retained_usp = None
    reads, writes, branches, intermediate = [], [], [], []
    obligations = ['IndependentDetached277aEntry', 'CompleteReviewedColdWriterFootprint',
                   'ExplicitUspGenerationAt27b2', 'DisjointOrdinaryModeFrame']

    def finish(status, reason, stop='STOP_BEFORE_DETACHED_277A'):
        ready = status == COMPLETE
        return result(status, source_scope=WINDOW_SCOPE, caller=0x276A, stop=stop,
                      state={'candidate': candidate, 'carriedSlot': carried, 'frameAddress': frame_address,
                             'retainedUspGeneration': retained_usp, 'conditionalModeCallReady': ready,
                             'nativeOwner': None},
                      reads=reads, writes=writes, branches=branches, intermediate=intermediate,
                      generations={'candidate': None if candidate is None else candidate['generation'],
                                   'atModeEntry': carried['generation'] if ready else None,
                                   'modeFrame': frame['state']['frame']['generation'] if ready else None},
                      obligations=obligations, unresolved=WINDOW_GAPS if ready else (*WINDOW_GAPS, reason),
                      reason=reason, frozenWriter=writer, frozenUsp=usp, frozenModeFrame=frame)

    if query['claim'] != 'ConditionalOnly':
        return finish(OUTSIDE, 'NonConditionalColdWindowClaim')
    if query['sourceBinding'] != SOURCE:
        status = UNKNOWN if query['sourceBinding'] is None else OUTSIDE
        return finish(status, 'ColdWindowSourceBindingUnqualified')
    writer_query = query['writerQuery']
    events = writer_query.get('events')
    need(type(events) is list and all(type(event) is dict for event in events), 'TypedEarlyWriterEventsRequired')
    if not all(_before_detached_window(event) for event in events):
        return finish(OUTSIDE, 'WriterEventOutsidePre277aWindow')
    writer = data03cb_competing_writer_exclusion(writer_query)
    candidate = writer['state']['candidate']
    carried = writer['state']['lastEstablishedSlot']
    if writer['status'] != COMPLETE:
        return finish(writer['status'], writer['reason'])
    if any(query['premises'][key] is not True for key in PREMISES):
        return finish(UNKNOWN, 'DetachedColdWindowPremisesUnestablished')

    occupied = _occupied_generations(writer, writer_query['initialTimeline'])
    usp = usp27b2_alias_proof(query['uspProof'])
    if usp['status'] != COMPLETE:
        return finish(usp['status'], usp['reason'], 'STOP_BEFORE_USP_STORE_27B2')
    usp_write, = usp['orderedWrites']
    replacement = usp_write['slot']
    if replacement['generation'] in occupied:
        return finish(OUTSIDE, 'ColdUspWriterGenerationReused', 'STOP_BEFORE_USP_STORE_27B2')
    occupied.add(replacement['generation'])
    retained_usp = usp['generations']['usp']
    reads.extend(usp['reads'])
    overlap = usp['state']['overlap03cb']
    same_value = (replacement['value'] == carried['value'] if overlap and
                  None not in (replacement['value'], carried['value']) else None)
    writes.append({**usp_write, 'overlap03cb': overlap, 'sameValue03cb': same_value})
    if overlap:
        carried = {**replacement, 'writerPc': 0x27B2, 'iterationId': None}
    intermediate.append({'pc': 0x27B2, 'carriedSlot': carried})
    if overlap:
        return finish(UNKNOWN, 'UspStoreReplacedCandidateGeneration', 'STOP_BEFORE_27B4')

    # Both source branch arms converge before the call. The reviewed fixed
    # DATA writes and control/USP footprints are disjoint under this mapping.
    branches.extend(CORRIDOR_BRANCHES)
    call_boundary = 'STOP_BEFORE_CAL_27D0'
    frame_query = query['modeFrame']
    if frame_query.get('callerPc') != 0x27D0:
        return finish(OUTSIDE, 'ColdModeFrameCallerMismatch', call_boundary)
    frame = call_return_obligations(frame_query)
    frame_address = frame['state']['geometry']['frameAddress']
    obligations.extend(frame['frameObligations'])
    if frame_address == 0x03CA:
        return finish(UNKNOWN, 'ModeFrameCouldOverwriteData03cb', call_boundary)
    if frame_address == 0x4700:
        return finish(OUTSIDE, 'ModeFrameUnsupportedMapping', call_boundary)
    if frame['status'] != COMPLETE:
        return finish(frame['status'], frame['reason'], call_boundary)
    if frame['state']['frame']['generation'] in occupied:
        return finish(OUTSIDE, 'ColdModeFrameGenerationReused', call_boundary)
    intermediate.append({'pc': 0x27D0, 'carriedSlot': carried})
    return finish(COMPLETE, 'DetachedColdWriterWindowRetained', call_boundary)


def _candidate_in_snapshot(slot, snapshot):
    bits = {key[5:]: value for key, value in snapshot['knownBits'].items() if key.startswith('03CB.')}
    return (snapshot['memory']['03CB'], snapshot['generations']['03CB'], bits) == (
        slot['value'], slot['generation'], slot['knownBits'])


def _data03cb_overlap(event):
    if event['space'] != 'DATA':
        return False
    address, width = event['address'], event['widthBits']
    return address is None or width not in (8, 16) or address <= 0x03CB < address + width // 8


def data03cb_to_60cc_source_proof(query):
    """Verify the exact slot against an unchanged detached mode-entry snapshot."""
    shape(query, ('inputClass', 'windowQuery', 'modeQuery', 'claim'), 'ClosedData03cbReadProofRequired')
    _matching_class(query, ('windowQuery', 'modeQuery'))
    window = mode = None
    retained = None

    def finish(status, reason, stop):
        accepted = status == COMPLETE
        state = None if mode is None else mode['state']
        return result(status, source_scope=MODE_SCOPE, caller=0x27D0, stop=stop,
                      state={'conditionalRead60cc': accepted, 'readGeneration': retained if accepted else None,
                             'registers': None if state is None else state['registers'],
                             'registerKnownBits': None if state is None else state['registerKnownBits'],
                             'nativeOwner': None},
                      generations={'candidate': retained, 'at60cc': retained if accepted else None},
                      reads=[] if mode is None else mode['reads'], writes=[] if mode is None else mode['journal'],
                      branches=[] if mode is None else [step for step in mode['steps'] if step['kind'] == 'Branch'],
                      intermediate=[] if mode is None else mode['intermediateStates'],
                      obligations=[] if window is None else window['formalObligations'],
                      unresolved=MODE_GAPS if accepted else (*MODE_GAPS, reason), reason=reason,
                      windowResult=window, frozenMode=mode)

    if query['claim'] != 'ConditionalOnly':
        return finish(OUTSIDE, 'NonConditionalData03cbReadClaim', 'STOP_BEFORE_MODE_ENTRY_5F45')
    window = cold_to_mode_intervening_writes(query['windowQuery'])
    if window['status'] != COMPLETE:
        return finish(window['status'], window['reason'], window['stopBoundary'])

    slot = window['state']['carriedSlot']
    retained = slot['generation']
    mode_query = query['modeQuery']
    shape(mode_query, ('inputClass', 'prefixQuery', 'program', 'sourceBinding'), 'ClosedFrozenModeQueryRequired')
    prefix = mode_query['prefixQuery']
    shape(prefix, ('inputClass', 'callerPc', 'snapshot', 'entry', 'entryEstablished', 'program'),
          'ClosedFrozenModePrefixRequired')
    stop = 'STOP_BEFORE_MODE_ENTRY_5F45'
    if prefix['callerPc'] != 0x27D0 or prefix['entry'] != 'From5F45':
        return finish(OUTSIDE, 'DetachedModeCallerOrEntryMismatch', stop)
    if prefix['entryEstablished'] is not True:
        return finish(UNKNOWN, 'DetachedModeEntryUnestablished', stop)
    snapshot = prefix['snapshot']
    validate(snapshot)
    context = snapshot['registers']
    usp = query['windowQuery']['uspProof']['currentUsp']['value']
    if (context['lrb'], context['scb'], context['dd'], context['usp']) != (0x0041, 0, 0, usp):
        return finish(UNKNOWN, 'DetachedModeRegisterHandoffMismatch', stop)
    frame_address = window['state']['frameAddress']
    if any(f'{address:04X}' in snapshot['memory'] for address in (frame_address, frame_address + 1)):
        return finish(OUTSIDE, 'DetachedModeFrameAliasesSnapshot', stop)
    if not _candidate_in_snapshot(slot, snapshot):
        return finish(UNKNOWN, 'ModeEntryData03cbGenerationMismatch', stop)

    mode = mode_enclosing_continuation(mode_query)
    stop = mode['exactStopBoundary']
    matches = [read for read in mode['reads'] if
               (read['pc'], read['space'], read['address'], read['widthBits']) == (0x60CC, 'DATA', 0x03CB, 8)]
    if mode['status'] != COMPLETE or stop != 'STOP_BEFORE_RT_60E4' or len(matches) != 1:
        return finish(UNKNOWN, 'Mode60ccReadNotReachedInCompleteScope', stop)
    if (any(_data03cb_overlap(event) for event in mode['journal']) or
            mode['state']['generations']['03CB'] != retained or matches[0]['value'] != slot['value']):
        return finish(UNKNOWN, 'FrozenModeWriterOrReadContradiction', stop)
    return finish(COMPLETE, 'DetachedData03cbRead60ccProven', stop)
