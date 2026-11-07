"""Bounded helper model with symbolic private comparands and separate frame proof."""
from copy import deepcopy

from enclosing_caller_return import state as accepted
from enclosing_caller_return.call_return_obligations import PREMISES, frame_alias, validate

from .adc_generation_timeline import data03d1_reaching_definitions
from .cold_reacquisition import (
    data_slot, data_write, projected_generations, set_accumulator_low, slot_values, written_slot,
)
from .wire import result

CALLER, ENTRY, FAULT, RT, CANDIDATE = 0x2777, 0x5CD9, 0x5CF8, 0x5CF9, 0x277A
HELPER_SCOPE = (ENTRY, 0x5CDC, 0x5CDD, 0x5CDF, 0x5CE1, 0x5CE3, 0x5CE5, 0x5CE7,
                0x5CE9, 0x5CEB, 0x5CED, 0x5CEF, 0x5CF1, 0x5CF4, 0x5CF6, FAULT, RT)
FRAME_SOURCE = 'M2cyStatic2777FrameV1'
FRAME_ALIASES = frozenset((0x00AE, 0x00F4, 0x00F6, 0x00F8, 0x00FA, 0x025A, 0x03D0))
HELPER_GAPS = ('PrimaryC8PredicateUnresolved', 'NativeData03d1OwnershipUnestablished',
               'NativeHelperExecutionUnestablished')
THRESHOLDS = ('5CDD', '5CE1', '5CE5', '5CE9')
HELPER_FIELDS = ('inputClass', 'snapshot', 'invocationId', 'lineage', 'entryEstablished',
                 'thresholds', 'errorByte', 'counterF7')


def _new_slot(value, generation):
    return {'value': value, 'knownBits': {}, 'generation': generation}


def _private_comparison(registers, values, threshold):
    thresholds = range(256) if threshold is None else (threshold,)
    flags = {(int(value < right), int(value == right)) for value in values for right in thresholds}
    registers['cf'] = accepted.frozen.unique({cf for cf, _ in flags})
    registers['zf'] = accepted.frozen.unique({zf for _, zf in flags})
    return {name: sorted({predicate(cf, zf) for cf, zf in flags}) for name, predicate in (
        ('printedOr', lambda cf, zf: not cf or not zf),
        ('comparativeAnd', lambda cf, zf: not cf and not zf),
    )}


def helper_5cd9(query):
    """Project admitted prefix and error effects without choosing one C8 hypothesis."""
    accepted.shape(query, HELPER_FIELDS, 'ClosedHelper5cd9QueryRequired')
    accepted.input_class(query['inputClass'])
    snapshot = query['snapshot']
    accepted.validate(snapshot)
    accepted.need(snapshot['inputClass'] == query['inputClass'], 'HelperSnapshotInputClassMismatch')
    invocation = query['invocationId']
    accepted.need(accepted.label(invocation) and invocation is not None and accepted.tri(query['entryEstablished']),
                  'TypedHelperEntryRequired')
    accepted.shape(query['thresholds'], THRESHOLDS, 'FourInventedComparandsRequired')
    accepted.need(all(accepted.number(value, 255) for value in query['thresholds'].values())
                  and accepted.number(query['errorByte'], 255), 'TypedInventedHelperOperandsRequired')
    counter = query['counterF7']
    if counter is not None:
        accepted.shape(counter, ('slot', 'sourcePc', 'firstCall', 'noInterference', 'expectedGeneration'),
                       'ClosedFirstHelperCounterRequired')
        accepted.slot(counter['slot'])
        accepted.need(accepted.number(counter['sourcePc'], 0xFFFF) and accepted.tri(counter['firstCall'])
                      and accepted.tri(counter['noInterference']) and accepted.label(counter['expectedGeneration']),
                      'TypedFirstHelperCounterRequired')

    state = {name: deepcopy(snapshot[name]) for name in accepted.STATE_FIELDS}
    registers = state['registers']
    reads, writes, intermediate, branches = [], [], [], []
    lineage = None

    def mark(pc):
        intermediate.append({'pc': pc, 'state': deepcopy(state)})

    def finish(status, reason, stop):
        return result(status, source_scope=HELPER_SCOPE, caller=CALLER, state=state, stop=stop, reads=reads,
                      writes=writes, branches=branches, intermediate=intermediate, generations=projected_generations(state),
                      unresolved=HELPER_GAPS if status == 'CompleteConditional' else (*HELPER_GAPS, reason),
                      reason=reason, invocationId=invocation, data03d1Lineage=lineage,
                      operandClass='InventedComparandsAndMarker', nativeNormalRouteEstablished=False)

    assumptions = snapshot['assumptions']
    if (query['entryEstablished'] is not True or assumptions['noInterference'] is not True
            or assumptions['dataMapping'] != 'ConditionalByteArray'):
        return finish('IndeterminateObligation', 'HelperEntryOrInterferenceUnestablished', 'STOP_BEFORE_HELPER_5CD9')
    if registers['scb'] != 0:
        return finish('IndeterminateObligation', 'ColdHelperScb0Required', 'STOP_BEFORE_HELPER_5CD9')
    ids = {pc: f'M2cy:{pc:04X}:{invocation}' for pc in (ENTRY, 0x5CEF, 0x5CF1, 0x5CF6)}
    occupied = set(state['generations'].values())
    if counter is not None:
        occupied.add(counter['slot']['generation'])
    if occupied.intersection(ids.values()):
        return finish('OutsideVerifiedScope', 'HelperGenerationCollision', 'STOP_BEFORE_HELPER_5CD9')

    before_dp = [data_slot(state, address) for address in (0x84, 0x85)]
    after_dp = [written_slot(state, address, {value}, ids[ENTRY])
                for address, value in ((0x84, 0xD1), (0x85, 3))]
    writes.append({'pc': ENTRY, 'address': 0x0084, 'widthBits': 16, 'kind': 'SelectedDpWrite',
                   'before': before_dp, 'after': after_dp,
                   'sameValue': None if any(slot['value'] is None for slot in before_dp) else
                   [slot['value'] for slot in before_dp] == [slot['value'] for slot in after_dp]})
    mark(ENTRY)
    current = data_slot(state, 0x03D1)
    if query['lineage'] is not None:
        accepted.need(type(query['lineage']) is dict and query['lineage'].get('inputClass') == query['inputClass'],
                      'HelperLineageInputClassMismatch')
        lineage = data03d1_reaching_definitions(query['lineage'])
    if lineage is None or lineage['reason'] != 'ConditionalIndexedGenerationAt5cdc':
        return finish('IndeterminateObligation', 'Data03d1ReachingDefinitionUnestablished', 'STOP_BEFORE_DATA03D1_READ_5CDC')
    observed = lineage['state']['lastSlots']['03D1']
    if (observed['value'], observed['generation']) != (current['value'], current['generation']):
        return finish('OutsideVerifiedScope', 'Data03d1SnapshotMismatch', 'STOP_BEFORE_DATA03D1_READ_5CDC')
    if snapshot['assumptions']['ordinaryByteSemantics'] is not True:
        return finish('IndeterminateObligation', 'OrdinaryByteSemanticsUnestablished', 'STOP_BEFORE_DATA03D1_READ_5CDC')
    reads.append({'pc': 0x5CDC, 'address': 0x03D1, 'widthBits': 8, 'space': 'DATA', 'slot': current})
    values = slot_values(current)
    set_accumulator_low(state, values, load=True)
    mark(0x5CDC)
    hypotheses = _private_comparison(registers, values, query['thresholds']['5CDD'])
    mark(0x5CDD)
    consensus = set(hypotheses['printedOr']) | set(hypotheses['comparativeAnd'])
    taken = accepted.frozen.unique(consensus)
    target = None if taken is None else 0x5CED if taken else 0x5CE1
    branches.append({'pc': 0x5CDF, 'taken': taken, 'next': target, 'hypotheses': hypotheses})
    if taken is not True:
        return finish('IndeterminateBranch', 'PrimaryC8BranchUnresolved', 'STOP_BEFORE_JGT_5CDF')

    error = query['errorByte']
    set_accumulator_low(state, range(256) if error is None else {error}, load=True)
    mark(0x5CED)
    state['data00af'] = _new_slot(error, ids[0x5CEF])
    writes.append(data_write(0x5CEF, 0x00AF, _new_slot(None, None), state['data00af'], 'ConditionalHelperMarker'))
    mark(0x5CEF)
    if (counter is None or counter['sourcePc'] != 0x2773 or counter['firstCall'] is not True
            or counter['noInterference'] is not True or counter['slot']['generation'] is None
            or counter['slot']['generation'] != counter['expectedGeneration']
            or counter['slot']['value'] != 1):
        return finish('IndeterminateObligation', 'FirstCallCounterGenerationUnestablished', 'STOP_BEFORE_DECB_5CF1')
    reads.append({'pc': 0x5CF1, 'address': 0x00F7, 'widthBits': 8, 'space': 'DATA', 'slot': counter['slot']})
    state['counterF7'] = _new_slot(0, ids[0x5CF1])
    writes.append(data_write(0x5CF1, 0x00F7, counter['slot'], state['counterF7'], 'ConditionalByteDecrement'))
    registers.update(zf=1, hc=0)
    mark(0x5CF1)
    branches.append({'pc': 0x5CF4, 'taken': False, 'next': 0x5CF6})
    before_f5 = data_slot(state, 0x00F5)
    after_f5 = written_slot(state, 0x00F5, range(256) if error is None else {error}, ids[0x5CF6])
    writes.append(data_write(0x5CF6, 0x00F5, before_f5, after_f5, 'ConditionalHelperMarker'))
    mark(0x5CF6)
    return finish('CompleteConditional', 'FirstCallFaultRoute', 'STOP_BEFORE_BRK_5CF8')


def rt5cf9_obligations(query):
    """Qualify the ordinary CAL2777 frame for a separately supplied normal frontier."""
    accepted.shape(query, ('inputClass', 'frameQuery', 'helperBoundary', 'expectedFrameGeneration'),
                   'ClosedHelperReturnQueryRequired')
    accepted.input_class(query['inputClass'])
    call = query['frameQuery']
    validate(call)
    accepted.need(call['inputClass'] == query['inputClass'], 'HelperFrameInputClassMismatch')
    boundary, expected = query['helperBoundary'], query['expectedFrameGeneration']
    accepted.need(accepted.number(boundary, 0xFFFF) and accepted.label(expected), 'TypedHelperReturnBoundaryRequired')
    frame = call['frame']
    incoming, pre_rt = call['incomingSsp'], call['sspBeforeReturn']
    address = None if incoming is None else incoming & 0xFFFE
    after_cal = None if incoming is None else (incoming - 2) & 0xFFFF
    after_rt = None if pre_rt is None else (pre_rt + 2) & 0xFFFF
    read_address = None if after_rt is None else after_rt & 0xFFFE
    saved_pc = None if None in (frame['low'], frame['high']) else frame['low'] | frame['high'] << 8
    geometry = {'frameAddress': address, 'sspAfterCall': after_cal, 'sspAfterReturn': after_rt,
                'returnReadAddress': read_address, 'savedPc': saved_pc}
    ordinary_alias = address is not None and frame_alias(address, False) != 'OrdinaryDataCandidate'
    aliases = ordinary_alias or address in FRAME_ALIASES
    missing = [name for name in PREMISES if call['premises'][name] is not True]
    if call['claim'] != 'ConditionalOnly':
        status, reason = 'OutsideVerifiedScope', 'NonConditionalFrameClaim'
    elif (call['callerPc'], call['declaredTarget'], call['returnPc']) != (CALLER, ENTRY, RT):
        status, reason = 'OutsideVerifiedScope', 'HelperReturnSourceMismatch'
    elif call['sourceBinding'] != FRAME_SOURCE:
        status, reason = 'IndeterminateObligation', 'HelperReturnSourceBindingRequired'
    elif boundary == FAULT:
        status, reason = 'OutsideVerifiedScope', 'FaultBoundaryIsNotNormalReturn'
    elif boundary != RT:
        status, reason = 'IndeterminateObligation', 'HypotheticalNormalFrontierRequired'
    elif frame['kind'] != 'NormalCall':
        status, reason = 'OutsideVerifiedScope', 'InterruptFrameCannotReturnViaRt'
    elif None in (incoming, pre_rt):
        status, reason = 'IndeterminateObligation', 'StackPointerUnknown'
    elif pre_rt != after_cal:
        status, reason = 'OutsideVerifiedScope', 'UnbalancedStackPointer'
    elif aliases:
        status, reason = 'OutsideVerifiedScope', 'HelperFrameAliasRequiresIndependentProof'
    elif missing:
        status, reason = 'IndeterminateObligation', 'FramePremisesNotEstablished'
    elif None in (expected, frame['generation'], frame['address'], frame['creatorPc'], saved_pc):
        status, reason = 'IndeterminateObligation', 'FrameContentsOrOwnerUnknown'
    elif (frame['generation'], frame['address'], frame['creatorPc'], saved_pc) != (expected, address, CALLER, CANDIDATE):
        status, reason = 'OutsideVerifiedScope', 'FrameDoesNotMatchHelperCall'
    else:
        status, reason = 'CompleteConditional', 'ConditionalMatchingFrame'
    obligations = ({'kind': 'FormalCalWordStore', 'pc': CALLER, 'address': address, 'widthBits': 16, 'value': CANDIDATE},
                   {'kind': 'FormalRtWordRead', 'pc': RT, 'address': read_address, 'widthBits': 16, 'value': saved_pc})
    complete = status == 'CompleteConditional'
    return result(status, source_scope=(CALLER, ENTRY, FAULT, RT), evidence_class='StaticFormalSourceObligation',
                  caller=CALLER, state={'geometry': geometry, 'formalReturnedPc': CANDIDATE if complete else None,
                                       'candidateReturnPc': CANDIDATE, 'nativeReturnEstablished': False},
                  stop='STOP_BEFORE_BRK_5CF8' if boundary == FAULT else 'STOP_BEFORE_RT_5CF9',
                  obligations=obligations, unresolved=('ActualNativeReturnUnobserved',) if complete else (reason,),
                  generations={'expectedFrame': expected, 'suppliedFrame': frame['generation']}, reason=reason)
