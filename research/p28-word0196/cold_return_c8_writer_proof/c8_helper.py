"""Source-qualified C8 comparison and detached helper continuations."""
from copy import deepcopy

from enclosing_caller_return import state as accepted
from shadow_cold_reacquisition.cold_reacquisition import (
    data_slot, data_write, projected_generations, set_accumulator_low, slot_values, written_slot,
)
from shadow_cold_reacquisition.helper_5cd9 import HELPER_SCOPE, helper_5cd9

from .wire import result


PRIMARY = 'OKI_MSM66201_3_66_3_67'
C8_SITES = {0x5CDF: (0x5CED, 0x5CE1), 0x5CE7: (0x5CED, 0x5CE9)}
FLAG_PAIRS = ((0, 0), (0, 1), (1, 0), (1, 1))
C8_QUERY = ('inputClass', 'pc', 'conditionCode', 'target', 'fallthrough', 'authority', 'cf', 'zf', 'producer')


def _row(cf, zf):
    return {'cf': cf, 'zf': zf, 'printedOr': cf == 0 or zf == 0, 'comparativeAnd': cf == 0 and zf == 0}


def _outcome(pairs):
    rows = [_row(cf, zf) for cf, zf in sorted(pairs)]
    union = {row[name] for row in rows for name in ('printedOr', 'comparativeAnd')}
    if union == {True}:
        return 'ConsensusTaken', True, rows
    if union == {False}:
        return 'ConsensusNotTaken', False, rows
    if rows and all(row['printedOr'] != row['comparativeAnd'] for row in rows):
        return 'Disagreement', None, rows
    return 'UnknownPredicate', None, rows


def c8_branch_consensus(query):
    """Compare source interpretations over an explicit flag or CMP domain."""
    accepted.shape(query, C8_QUERY, 'ClosedC8BranchQueryRequired')
    accepted.input_class(query['inputClass'])
    pc, code, target, fallthrough = (query[name] for name in ('pc', 'conditionCode', 'target', 'fallthrough'))
    cf, zf, producer = query['cf'], query['zf'], query['producer']
    accepted.need(all(accepted.number(value, 0xFFFF) for value in (pc, target, fallthrough))
                  and accepted.number(code, 0xFF) and accepted.number(cf, 1) and accepted.number(zf, 1)
                  and accepted.label(query['authority']) and type(producer) is str
                  and producer in ('ExplicitFlags', 'UnsignedByteCompare'), 'TypedC8BranchInputRequired')
    stop = {0x5CDF: 'STOP_BEFORE_JGT_5CDF', 0x5CE7: 'STOP_BEFORE_JGT_5CE7'}.get(pc, 'STOP_BEFORE_UNBOUND_C8')
    state = {'flagReads': ['CF', 'ZF'], 'flagWrites': [], 'length': 2, 'displacementWidthBits': 8,
             'compareDomain': producer, 'table': [_row(carry, zero) for carry, zero in FLAG_PAIRS],
             'candidateRows': []}
    outcome, branch = None, []
    if query['authority'] != PRIMARY:
        status, reason = 'IndeterminateObligation', 'ApplicablePrimarySourceRequired'
    elif code != 0xC8 or C8_SITES.get(pc) != (target, fallthrough):
        status, reason = 'OutsideVerifiedScope', 'C8SourceSiteOrEdgeMismatch'
    else:
        pairs = [(carry, zero) for carry, zero in FLAG_PAIRS
                 if (cf is None or cf == carry) and (zf is None or zf == zero)
                 and (producer == 'ExplicitFlags' or (carry, zero) != (1, 1))]
        if not pairs:
            status, reason = 'OutsideVerifiedScope', 'UnsignedCompareFlagPairImpossible'
        else:
            outcome, taken, state['candidateRows'] = _outcome(pairs)
            status = 'CompleteConditional' if taken is not None else 'IndeterminateBranch'
            reason = outcome
            branch = [{'pc': pc, 'taken': taken, 'next': None if taken is None else target if taken else fallthrough}]
    return result(status, source_scope=tuple(C8_SITES), state=state, stop=stop, branches=branch, reason=reason,
                  classification=outcome, predicateAuthority='PrimarySourceConflict',
                  unresolved=('NativeC8PredicateUnestablished',))


def _compare(state, values, threshold):
    comparands = range(256) if threshold is None else (threshold,)
    pairs = {(int(value < rhs), int(value == rhs)) for value in values for rhs in comparands}
    state['registers'].update(cf=accepted.frozen.unique({cf for cf, _ in pairs}),
                              zf=accepted.frozen.unique({zf for _, zf in pairs}))
    return pairs


def _detached_fault(query, state, reads, writes, branches, mark):
    counter = query['counterF7']
    ids = {pc: f'M2cz:{pc:04X}:{query["invocationId"]}' for pc in (0x5CEF, 0x5CF1, 0x5CF6)}
    occupied = set(projected_generations(state).values())
    if counter is not None:
        occupied.add(counter['slot']['generation'])
    if occupied.intersection(ids.values()):
        return 'OutsideVerifiedScope', 'HelperGenerationCollision', 'STOP_BEFORE_ERROR_MARKER_5CED'

    error = query['errorByte']
    values = range(256) if error is None else {error}
    set_accumulator_low(state, values, load=True)
    mark(0x5CED)
    before = {'value': None, 'knownBits': {}, 'generation': None}
    state['data00af'] = {'value': error, 'knownBits': {}, 'generation': ids[0x5CEF]}
    writes.append(data_write(0x5CEF, 0x00AF, before, state['data00af'], 'ConditionalHelperMarker'))
    mark(0x5CEF)

    if (counter is None or counter['sourcePc'] != 0x2773 or counter['firstCall'] is not True
            or counter['noInterference'] is not True or counter['slot']['generation'] is None
            or counter['slot']['generation'] != counter['expectedGeneration']
            or counter['slot']['value'] != 1):
        return 'IndeterminateObligation', 'FirstCallCounterGenerationUnestablished', 'STOP_BEFORE_DECB_5CF1'
    reads.append({'pc': 0x5CF1, 'address': 0x00F7, 'widthBits': 8, 'space': 'DATA', 'slot': counter['slot']})
    state['counterF7'] = {'value': 0, 'knownBits': {}, 'generation': ids[0x5CF1]}
    writes.append(data_write(0x5CF1, 0x00F7, counter['slot'], state['counterF7'], 'ConditionalByteDecrement'))
    state['registers'].update(zf=1, hc=0)
    mark(0x5CF1)
    branches.append({'pc': 0x5CF4, 'taken': False, 'next': 0x5CF6})
    before = data_slot(state, 0x00F5)
    after = written_slot(state, 0x00F5, values, ids[0x5CF6])
    writes.append(data_write(0x5CF6, 0x00F5, before, after, 'ConditionalHelperMarker'))
    mark(0x5CF6)
    return 'CompleteConditional', 'DetachedFirstCallFaultRoute', 'STOP_BEFORE_BRK_5CF8'


def helper_5cd9_extended(query):
    """Retain the full-path frontier and evaluate an explicitly detached suffix."""
    accepted.shape(query, ('entry', 'helperQuery', 'detachedHandoff'), 'ClosedExtendedHelperQueryRequired')
    entry, helper_query, handoff = query['entry'], query['helperQuery'], query['detachedHandoff']
    accepted.need(type(entry) is str and entry in ('Full', 'Detached5CE1') and accepted.tri(handoff),
                  'TypedExtendedHelperEntryRequired')
    child = helper_5cd9(helper_query)
    state = deepcopy(child['state'])
    branches, reads, writes, intermediate = (deepcopy(child[key]) for key in
                                              ('branchOutcome', 'reads', 'orderedWrites', 'intermediateStates'))
    detached = entry == 'Detached5CE1'
    classification = None

    def finish(status, reason, stop, normal=False):
        return result(status, source_scope=HELPER_SCOPE, state=state, stop=stop, reads=reads, writes=writes,
                      branches=branches, intermediate=intermediate, generations=projected_generations(state),
                      caller=0x2777, obligations=child['formalObligations'], unresolved=child['unresolvedConstraints'],
                      reason=reason, entry=entry, detachedNormalFrontier=normal, connectedNormalFrontier=False,
                      secondC8Classification=classification, frozenHelper=child)

    def mark(pc):
        intermediate.append({'pc': pc, 'state': deepcopy(state)})

    if not detached:
        if handoff is not None:
            return finish('OutsideVerifiedScope', 'DetachedHandoffCannotQualifyFullEntry', child['stopBoundary'])
        return finish(child['status'], child['reason'], child['stopBoundary'])
    if handoff is not True or child['stopBoundary'] != 'STOP_BEFORE_JGT_5CDF':
        return finish('IndeterminateObligation', 'Detached5ce1HandoffUnestablished', child['stopBoundary'])
    if not any(False in outcomes for outcomes in branches[-1]['hypotheses'].values()):
        return finish('OutsideVerifiedScope', 'DetachedFallthroughContradictsInputDomain', child['stopBoundary'])

    # The explicit detached premise grants only entry to this local suffix.
    # Keep the exact predecessor state and leave its C8 branch unresolved.
    registers = state['registers']
    values = accepted.frozen.candidates(registers['al'], state['registerKnownBits'], 'AL')
    pairs = _compare(state, values, helper_query['thresholds']['5CE1'])
    mark(0x5CE1)
    taken = accepted.frozen.unique({cf == 0 for cf, _ in pairs})
    branches.append({'pc': 0x5CE3, 'taken': taken, 'next': None if taken is None else 0x5CF9 if taken else 0x5CE5})
    if taken is True:
        return finish('CompleteConditional', 'DetachedJgeNormalFrontier', 'STOP_BEFORE_RT_5CF9', normal=True)
    if taken is None:
        return finish('IndeterminateBranch', 'DetachedJgePredicateUnknown', 'STOP_BEFORE_JGE_5CE3')

    pairs = _compare(state, values, helper_query['thresholds']['5CE5'])
    mark(0x5CE5)
    classification, taken, rows = _outcome(pairs)
    branches.append({'pc': 0x5CE7, 'taken': taken, 'next': 0x5CED if taken is True else None,
                     'candidateRows': rows})
    if taken is not True:
        return finish('IndeterminateBranch', 'SecondC8BranchUnresolved', 'STOP_BEFORE_JGT_5CE7')
    return finish(*_detached_fault(helper_query, state, reads, writes, branches, mark))
