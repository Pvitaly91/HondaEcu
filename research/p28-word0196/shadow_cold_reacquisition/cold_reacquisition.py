"""Cold caller software projection across explicit hypothetical handoffs."""
from copy import deepcopy

from enclosing_caller_return import state as accepted
from indexed_suffix_ie_provenance.composition import indexed_suffix_composition
from indexed_suffix_ie_provenance.return_obligations import indexed_return_obligations
from indexed_suffix_ie_provenance.suffix import indexed_suffix_post_ie

from .wire import result

SCOPE = (0x2766, 0x2768, 0x276A, 0x276D, 0x276F, 0x2771, 0x2773, 0x2777)
CALLER = 0x276A
STEP_FIELDS = ('inputClass', 'iterationId', 'prefixQuery', 'shadow', 'postIe', 'returnQuery',
               'returnHandoff', 'callerP2', 'counterF7')
POST_FIELDS = ('entry', 'p2', 'tm2', 'shadow', 'offPage', 'secondIeBoundary')
GAPS = ('ActualIndexedReturnUnobserved', 'NativeP2AndAdcReadbacksUnestablished',
        'NativeIterationCountUnestablished')


def slot_values(slot):
    return accepted.frozen.candidates(slot['value'], {f'v.{bit}': value for bit, value in slot['knownBits'].items()}, 'v')


def data_slot(state, address):
    key = f'{address:04X}'
    return {'value': state['memory'][key], 'generation': state['generations'][key],
            'knownBits': {field[-1]: value for field, value in state['knownBits'].items()
                          if field.startswith(key + '.')}}


def set_accumulator_low(state, values, *, load=False):
    regs = state['registers']
    regs['al'] = accepted.frozen.unique(values)
    regs['zf'] = accepted.frozen.unique({int(value == 0) for value in values})
    if load:
        regs['dd'] = 0
    bits = {key: value for key, value in state['registerKnownBits'].items() if not key.startswith('AL.')}
    bits.update(accepted.frozen.bit_consensus(values, 'AL'))
    state['registerKnownBits'] = bits


def written_slot(state, address, values, generation):
    key = f'{address:04X}'
    value = accepted.frozen.unique(values)
    bits = accepted.frozen.bit_consensus(values, key)
    state['memory'][key] = value
    state['generations'][key] = generation
    state['knownBits'] = {k: v for k, v in state['knownBits'].items() if not k.startswith(key + '.')}
    state['knownBits'].update(bits)
    return data_slot(state, address)


def data_write(pc, address, before, after, kind):
    return {'pc': pc, 'address': address, 'widthBits': 8, 'kind': kind,
            'before': before, 'after': after,
            'sameValue': None if None in (before['value'], after['value']) else before['value'] == after['value']}


def _snapshot(state, prefix_query):
    return {'inputClass': prefix_query['inputClass'], 'assumptions': prefix_query['snapshot']['assumptions'],
            **{field: state[field] for field in accepted.STATE_FIELDS}}


def projected_generations(state):
    if state is None:
        return None
    extensions = {'counterF7': '00F7', 'data00af': '00AF'}
    return {**state['generations'], **{address: state[field]['generation']
                                     for field, address in extensions.items() if field in state}}


def cold_reacquisition_step(query):
    """Use one frozen indexed invocation and only the source-owned caller continuation."""
    accepted.shape(query, STEP_FIELDS, 'ClosedColdStepQueryRequired')
    accepted.input_class(query['inputClass'])
    identity = query['iterationId']
    accepted.need(accepted.label(identity) and identity is not None, 'ExactIterationIdentityRequired')
    accepted.need(accepted.tri(query['returnHandoff']), 'TypedColdReturnHandoffRequired')
    prefix_query = query['prefixQuery']
    accepted.shape(prefix_query, ('inputClass', 'callerPc', 'snapshot', 'entryEstablished'),
                   'ClosedColdPrefixQueryRequired')
    accepted.need(prefix_query['inputClass'] == query['inputClass'], 'ColdPrefixInputClassMismatch')
    accepted.validate(prefix_query['snapshot'])
    for name in ('callerP2', 'counterF7'):
        if query[name] is not None:
            accepted.slot(query[name])
    if query['postIe'] is not None:
        accepted.shape(query['postIe'], POST_FIELDS, 'ClosedColdPostIePremiseRequired')

    prefix = post = frame = None
    state = None
    reads, writes, intermediate, branches, obligations = [], [], [], [], []
    scopes = set(SCOPE)

    def finish(status, reason, boundary, selected=None):
        return result(status, source_scope=sorted(scopes), caller=CALLER, state=state, stop=boundary,
                      reads=reads, writes=writes, intermediate=intermediate, branches=branches,
                      generations=projected_generations(state), obligations=obligations,
                      unresolved=GAPS if status == 'CompleteConditional' else (*GAPS, reason),
                      iterations=({'id': identity, 'selectedIndex': selected},), reason=reason,
                      frozenAcquisition=prefix, frozenPostIe=post, frozenIndexedFrame=frame)

    if prefix_query['callerPc'] != CALLER:
        return finish('OutsideVerifiedScope', 'ColdCaller276ARequired', 'STOP_BEFORE_CAL_276A')
    prefix = indexed_suffix_composition({'inputClass': query['inputClass'], 'prefixQuery': prefix_query,
                                         'shadow': query['shadow']})
    selected = prefix['frozenPrefixResult']['selectedIndex']
    state = prefix['state']
    scopes.update(prefix['sourceScope'])
    reads.extend(prefix['reads'])
    writes.extend(prefix['orderedWrites'])
    intermediate.extend(prefix['intermediateStates'])
    branches.extend(prefix['branchOutcome'])
    obligations.extend(prefix['formalObligations'])
    if prefix['status'] != 'CompleteConditional' or prefix['stopBoundary'] != 'STOP_BEFORE_IE_WRITE_5CB9':
        return finish(prefix['status'], prefix['reason'], prefix['stopBoundary'], selected)
    if query['postIe'] is None:
        return finish('IndeterminateObligation', 'ExplicitPostIeBoundaryRequired', prefix['stopBoundary'], selected)

    post = indexed_suffix_post_ie({**query['postIe'], 'inputClass': query['inputClass'],
                                    'snapshot': _snapshot(state, prefix_query)})
    state = post['state']
    scopes.update(post['sourceScope'])
    reads.extend(post['reads'])
    writes.extend(post['orderedWrites'])
    intermediate.extend(post['intermediateStates'])
    obligations.extend(post['formalObligations'])
    if post['status'] != 'CompleteConditional' or post['stopBoundary'] != 'STOP_BEFORE_RT_5CCD':
        return finish(post['status'], post['reason'], post['stopBoundary'], selected)
    if query['returnQuery'] is None:
        return finish('IndeterminateObligation', 'IndexedReturnFrameRequired', post['stopBoundary'], selected)

    accepted.need(type(query['returnQuery']) is dict and query['returnQuery'].get('inputClass') == query['inputClass'],
                  'ColdFrameInputClassMismatch')
    frame = indexed_return_obligations(query['returnQuery'])
    scopes.update(frame['sourceScope'])
    obligations.extend(frame['formalObligations'])
    if frame['status'] != 'CompleteConditional' or frame['state']['formalReturnedPc'] != 0x276D:
        return finish('IndeterminateObligation', 'ColdIndexedReturnUnestablished', post['stopBoundary'], selected)
    if query['returnHandoff'] is not True:
        return finish('IndeterminateObligation', 'ExplicitIndexedReturnHandoffRequired', post['stopBoundary'], selected)

    p2 = query['callerP2']
    if p2 is None or p2['generation'] is None:
        return finish('IndeterminateObligation', 'CallerP2ReadGenerationMissing', 'STOP_BEFORE_P2_READ_276D', selected)
    state = deepcopy(state)
    reads.append({'pc': 0x276D, 'address': 0x0024, 'widthBits': 8, 'space': 'SuppliedSymbolicReadback', 'slot': p2})
    values = slot_values(p2)
    set_accumulator_low(state, values, load=True)
    intermediate.append({'pc': 0x276D, 'state': deepcopy(state)})
    set_accumulator_low(state, {value & 0xE0 for value in values})
    intermediate.append({'pc': 0x276F, 'state': deepcopy(state)})
    zf = state['registers']['zf']
    taken = None if zf is None else zf == 0
    target = None if taken is None else 0x2766 if taken else 0x2773
    branches.append({'pc': 0x2771, 'taken': taken, 'next': target})
    if taken is None:
        return finish('IndeterminateBranch', 'P2SelectorZeroPredicateUnknown', 'STOP_BEFORE_JNE_2771', selected)
    if taken:
        return finish('CompleteConditional', 'ColdRepeatSelected', 'STOP_BEFORE_WAIT_2766', selected)

    before = query['counterF7'] or {'value': None, 'knownBits': {}, 'generation': None}
    generation = f'M2cy:2773:{identity}'
    if generation == before['generation'] or generation in state['generations'].values():
        return finish('OutsideVerifiedScope', 'CounterF7GenerationCollision', 'STOP_BEFORE_COUNTER_2773', selected)
    state['counterF7'] = {'value': 1, 'knownBits': {}, 'generation': generation}
    writes.append(data_write(0x2773, 0x00F7, before, state['counterF7'], 'ColdFirstCallCounter'))
    intermediate.append({'pc': 0x2773, 'state': deepcopy(state)})
    return finish('CompleteConditional', 'ColdLoopExitSelected', 'STOP_BEFORE_CAL_2777', selected)


def cold_reacquisition_sequence(query):
    """Carry an admitted invocation into its bounded wait without reseeding it."""
    accepted.shape(query, ('inputClass', 'step', 'maxWaitSteps'), 'ClosedColdSequenceQueryRequired')
    accepted.input_class(query['inputClass'])
    limit = query['maxWaitSteps']
    accepted.need(type(limit) is int and 0 <= limit <= 256, 'BoundedColdWaitRequired')
    accepted.need(type(query['step']) is dict and query['step'].get('inputClass') == query['inputClass'],
                  'ColdSequenceInputClassMismatch')
    step = cold_reacquisition_step(query['step'])
    state = deepcopy(step['state'])
    reads, writes = list(step['reads']), list(step['orderedWrites'])
    intermediate, branches = list(step['intermediateStates']), list(step['branchOutcome'])
    wait_steps = 0

    def finish(status, reason, stop):
        return result(status, source_scope=step['sourceScope'], caller=CALLER, state=state, stop=stop,
                      reads=reads, writes=writes, intermediate=intermediate, branches=branches,
                      generations=projected_generations(state), obligations=step['formalObligations'],
                      unresolved=step['unresolvedConstraints'] if reason == step['reason'] else
                      (*step['unresolvedConstraints'], reason), iterations=step['iterations'], reason=reason,
                      frozenStep=step, waitSteps=wait_steps, nextAcquisitionInvoked=False)

    if step['reason'] != 'ColdRepeatSelected':
        return finish(step['status'], step['reason'], step['stopBoundary'])
    regs = state['registers']
    if regs['lrb'] != 0x0041 or regs['scb'] is None:
        return finish('IndeterminateObligation', 'WaitLocalOrPointingBankUnestablished', 'STOP_BEFORE_WAIT_2766')
    address = 0x84 + 8 * regs['scb']
    identity = query['step']['iterationId']
    occupied = set(state['generations'].values())
    for ordinal in range(1, limit + 1):
        local_gen, dpl_gen = (f'M2cy:{pc:04X}:{identity}:{ordinal}' for pc in (0x2766, 0x2768))
        if occupied.intersection((local_gen, dpl_gen)):
            return finish('OutsideVerifiedScope', 'ColdWaitGenerationCollision', 'STOP_BEFORE_WAIT_2766')
        occupied.update((local_gen, dpl_gen))
        local = data_slot(state, 0x0208)
        reads.append({'pc': 0x2766, 'address': 0x0208, 'widthBits': 8, 'space': 'DATA', 'slot': local})
        carry = (0, 1) if regs['cf'] is None else (regs['cf'],)
        after = written_slot(state, 0x0208, {(value & 0xFE) | bit for value in slot_values(local) for bit in carry},
                             local_gen)
        writes.append(data_write(0x2766, 0x0208, local, after, 'CarryToLocalBit0'))
        intermediate.append({'pc': 0x2766, 'slot': after})
        dpl = data_slot(state, address)
        reads.append({'pc': 0x2768, 'address': address, 'widthBits': 8, 'space': 'DATA', 'slot': dpl})
        after_values = {(value - 1) & 255 for value in slot_values(dpl)}
        after = written_slot(state, address, after_values, dpl_gen)
        writes.append(data_write(0x2768, address, dpl, after, 'DplOnlyDecrement'))
        intermediate.append({'pc': 0x2768, 'slot': after})
        wait_steps += 1
        taken = accepted.frozen.unique({value != 0 for value in after_values})
        branches.append({'pc': 0x2768, 'taken': taken,
                         'next': None if taken is None else 0x2766 if taken else 0x276A})
        if taken is None:
            return finish('IndeterminateBranch', 'WaitDplPredicateUnknown', 'STOP_BEFORE_WAIT_EDGE_2768')
        if not taken:
            return finish('IndeterminateObligation', 'FrozenAcquisitionNamespaceCannotBeReused', 'STOP_BEFORE_CAL_276A')
    return finish('IndeterminateObligation', 'ColdWaitBoundReached', 'STOP_BEFORE_WAIT_2766')
