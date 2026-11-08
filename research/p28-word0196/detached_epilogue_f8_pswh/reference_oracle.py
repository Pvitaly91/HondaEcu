"""Independent source equations and historical reference replay for M2dh."""
from copy import deepcopy

from alternate_parser_response_checksum.reference_oracle import expected as m2df
from detached_post_stbuf_0240_0241.analysis import AUTHORITY, canonical
from detached_post_stbuf_0240_0241.reference_oracle import expected as m2dg

_W = dict(al=8, ah=8, dd=1, zf=1, cf=1, hc=1, mie=1, otherPsw=16,
          lrb=16, scb=3, usp=16, ssp=16)
_UPPER = ((7, 'cf'), (6, 'zf'), (5, 'hc'), (4, 'dd'), (0, 'mie'))
_FLAGS = ('cf', 'zf', 'hc', 'dd', 'mie', 'otherPsw')
_SHADOW_WRITERS = [(0x2569, 0), (0x3F16, 0x2BAB), (0x3F2A, 0xA9A3), (0x54E5, 0x2BAB)]
_MEMORY = 'ConditionalDocumentedInternalRam'
_EFFECT_STOP = 'STOP_BEFORE_IE_WRITE_0249'
_INGRESS_STOP = 'STOP_BEFORE_EPILOGUE_0244'
_DIRECT, _DETACHED = 'DirectM2dfIngress', 'DetachedM2dgIngress'
_FROZEN = {
    _DIRECT: ('a9eeb45292a120711bb1adf918385675c2456409',
              'a1c554e17305f199effbc2e3aae2b42ab83081da7e527b4eeeab181faf691e55'),
    _DETACHED: ('b20f1341219888afd72b950e4a592e18b0e3f02a',
                '466c2a69e86de5f56058166d28e6c82e93243caa84f7655a730957d12da98470'),
}
_EFFECT_LIMITS = ('ActualHardwareShadowOwnerUnknown', 'ActualDataMapAndFrameOverlapUnknown',
                  'PswhSelfDestinationFlagApplicabilityUnresolved', 'ActualIePolarityAndPendingStateUnknown',
                  'ActualIeAcknowledgementAndReassertionUnknown', 'RtiFrameAndNativeReturnUnestablished')
_INGRESS_LIMITS = ('UnprovedNativeHandoff', 'PhysicalDataMappingUnknown', 'HardwareInterruptStateUnknown')
_COMPARE_LIMITS = ('SourceHistoriesRemainDistinct', 'CurrentNativeShadowOwnerUnknown',
                   'PswhFlagPrecedenceUnestablished', 'IeAndRtiOutsideScope')


def _keys(value, fields):
    return type(value) is dict and sorted(value, key=str) == sorted(fields.split())


def _unsigned(value, width):
    return value is None or type(value) is int and value in range(2 ** width)


def _optional_bool(value):
    return value is True or value is False or value is None


def _generation(value):
    return value is None or type(value) is str and 1 <= len(value) <= 256


def _bit(value, index):
    return value // 2 ** index % 2


def _valid_bits(bits, value):
    return type(bits) is dict and all(
        key in tuple(map(str, range(8))) and type(flag) is int and flag in (0, 1)
        and (value is None or flag == _bit(value, int(key))) for key, flag in bits.items())


def _valid_shadow(value):
    if not _keys(value, 'low high writer events'):
        return False
    for name in ('low', 'high'):
        slot = value[name]
        if not _keys(slot, 'value knownBits generation') or not _unsigned(slot['value'], 8):
            return False
        if not _valid_bits(slot['knownBits'], slot['value']) or not _generation(slot['generation']):
            return False
    writer = value['writer']
    if writer is not None and (not _keys(writer, 'pc generation')
                               or not _unsigned(writer['pc'], 16) or not _generation(writer['generation'])):
        return False
    events = value['events']
    if type(events) is not list or len(events) > 32:
        return False
    return all(_keys(row, 'address widthBits generation value') and _unsigned(row['address'], 16)
               and type(row['widthBits']) is int and row['widthBits'] in (8, 16)
               and _generation(row['generation']) and _unsigned(row['value'], row['widthBits'])
               for row in events)


def _valid_registers(r, g, b):
    if not all(type(row) is dict for row in (r, g, b)):
        return False
    if any(key not in _W or not _unsigned(value, _W[key]) for key, value in r.items()):
        return False
    other = r.get('otherPsw')
    if other is not None and any(_bit(other, n) for n in (15, 14, 13, 12, 8, 2, 1, 0)):
        return False
    return (all(key in r and _generation(value) for key, value in g.items())
            and all(key in r and key in ('al', 'ah') and _valid_bits(bits, r[key]) for key, bits in b.items()))


def _empty_events(limits):
    return dict(steps=[], reads=[], journal=[], unresolved=list(limits), executionAuthority=dict(AUTHORITY))


def _effect_record(reason, stop, state=None, proof=None, **extra):
    base = dict(status='ConditionalSourceArrivalAt0249' if reason is None else 'OutsideVerifiedScope',
                reason=reason, stopPc=stop, entryClass='DetachedSymbolic0244',
                stopBoundary=_EFFECT_STOP if stop == 0x0249 else 'STOP_BEFORE_UNQUALIFIED_0244_OR_0246',
                state=state, shadowProof=proof, pswh=None, prospectiveIe=None)
    return {**base, **_empty_events(_EFFECT_LIMITS), **extra}


def _entry(snapshot):
    fields = 'sourceId entryPc entryClass assumptions registers registerGenerations registerKnownBits shadow'
    if not _keys(snapshot, fields):
        return 'ClosedDetachedEpilogueSnapshotRequired', None
    if snapshot['sourceId'] != 'M2dhReviewed0244_0246' or type(snapshot['entryPc']) is not int or snapshot['entryPc'] != 0x0244:
        return 'ExactReviewedDetachedEntryRequired', None
    if snapshot['entryClass'] != 'DetachedSymbolic0244':
        return 'DetachedSymbolicClassRequired', None
    premises = snapshot['assumptions']
    if (not _keys(premises, 'noInterference memoryModel pswhAlias')
            or not all(_optional_bool(premises[field]) for field in ('noInterference', 'pswhAlias'))
            or premises['memoryModel'] not in (None, _MEMORY, 'Unknown')):
        return 'ClosedEpiloguePremisesRequired', None
    state = {field: deepcopy(snapshot[field]) for field in ('registers', 'registerGenerations', 'registerKnownBits')}
    if not (_valid_registers(*state.values()) and _valid_shadow(snapshot['shadow'])):
        return 'TypedEpilogueStateRequired', None
    if premises['noInterference'] is not True:
        return 'NoInterferencePremiseRequired', state
    return (None if premises['memoryModel'] == _MEMORY else 'QualifiedShadowRamReadRequired'), state


def _value(bits):
    return sum(2 ** int(position) for position, value in bits.items() if value) if len(bits) == 8 else None


def _byte_knowledge(slot):
    if slot['value'] is None:
        bits = dict(slot['knownBits'])
        return _value(bits), bits
    n = slot['value']
    return n, {str(index): _bit(n, index) for index in range(8)}


def _shadow_source(shadow, parts, tags):
    candidate, events = shadow['writer'], shadow['events']
    word = None if candidate is None else dict(_SHADOW_WRITERS).get(candidate['pc'])
    overlaps, unresolved = [], []
    for index, event in enumerate(events, 1):
        if event['address'] is None:
            unresolved.append(index)
        elif (event['widthBits'] == 16 and event['address'] // 2 == 124
              or event['widthBits'] == 8 and event['address'] in (248, 249)):
            overlaps.append(index)
    if overlaps or unresolved:
        status = 'InterveningWriterPossible'
    elif candidate is None:
        status = 'CurrentReadGenerationMissing' if None in tags else 'CurrentReadGenerationsDeclared'
    elif word is None:
        status = 'UnreviewedCandidateWriter'
    elif None in tags or candidate['generation'] is None:
        status = 'CurrentReadGenerationMissing'
    elif tags[0] != candidate['generation'] or tags[1] != candidate['generation']:
        status = 'CandidateGenerationMismatch'
    elif None in parts or parts[0] + 256 * parts[1] != word:
        status = 'CandidateValueNotEstablished'
    elif candidate['generation'] in [row['generation'] for row in events]:
        status = 'CandidateGenerationReused'
    else:
        status = 'ConditionalCandidateGenerationMatched'
    return dict(classification=status, knownSourceProducers=[dict(pc=pc, value=n) for pc, n in _SHADOW_WRITERS],
                candidateWriter=deepcopy(candidate), candidateWord=word, readGenerations=tags,
                interveningEvents=deepcopy(events), overlapOrdinals=overlaps, unknownFootprintOrdinals=unresolved,
                nativeOwner=None, conditionalWordWriterGenerationMatched=status == 'ConditionalCandidateGenerationMatched')


def _tags(pc, registers):
    return {register: 'M2dh:%04X:%s' % (pc, register.upper()) for register in registers}


def _collision(fresh, state, generations):
    old = tuple(state['registerGenerations'].values()) + tuple(generations)
    return any(tag in old for tag in fresh.values())


def _pswh_view(registers):
    bits = {str(n): registers[name] for n, name in _UPPER if registers.get(name) is not None}
    other = registers.get('otherPsw')
    if other is not None:
        bits.update({str(n): _bit(other, n + 8) for n in (1, 2, 3)})
    return dict(value=_value(bits), knownBits=bits)


def _step(pc, next_pc, state):
    return dict(pc=pc, next=next_pc, edge='ConfirmedStaticCFG', state=deepcopy(state))


def _epilogue(query):
    refusal, state = _entry(query)
    if refusal is not None:
        return _effect_record(refusal, 0x0244, state)
    shadow = query['shadow']
    slots = shadow['low'], shadow['high']
    tags = [part['generation'] for part in slots]
    load_tags = _tags(0x0244, ('al', 'ah', 'dd', 'zf'))
    if _collision(load_tags, state, tags):
        return _effect_record('RegisterGenerationCollision', 0x0244, state)
    low, low_bits = _byte_knowledge(slots[0])
    high, high_bits = _byte_knowledge(slots[1])
    word_bits = {**low_bits, **{str(8 + int(n)): value for n, value in high_bits.items()}}
    word = None if low is None or high is None else low + 256 * high
    zero = 0 if 1 in word_bits.values() else 1 if len(word_bits) == 16 else None
    state['registers'].update(al=low, ah=high, dd=1, zf=zero)
    state['registerKnownBits'].update(al=low_bits, ah=high_bits)
    state['registerGenerations'].update(load_tags)
    shadow_proof = _shadow_source(shadow, [low, high], tags)
    reads = [dict(pc=0x0244, space='DATA', address=248, widthBits=16, value=word, bytes=[low, high],
                  knownBits=word_bits, generations=tags, kind='FunctionalWordOperand')]
    steps = [_step(0x0244, 0x0246, state)]
    if query['assumptions']['pswhAlias'] is not True:
        return _effect_record('PswhAliasPremiseRequired', 0x0246, state, shadow_proof, steps=steps, reads=reads)
    mask_tags = _tags(0x0246, ('mie', 'cf', 'hc', 'zf'))
    if _collision(mask_tags, state, tags):
        return _effect_record('RegisterGenerationCollision', 0x0246, state, shadow_proof, steps=steps, reads=reads)

    registers = state['registers']
    before = _pswh_view(registers)
    candidate_bits = {**before['knownBits'], '0': 0}
    candidate = dict(value=_value(candidate_bits), knownBits=candidate_bits)
    source_generations = {name: state['registerGenerations'].get(name) for _, name in _UPPER}
    same_candidate = None if registers.get('mie') is None else registers['mie'] == 0
    for name in ('cf', 'hc', 'zf'):
        registers[name] = None
    registers['mie'] = 0
    state['registerGenerations'].update(mask_tags)
    after = _pswh_view(registers)
    pswh = dict(before=before, maskCandidate=candidate, after=after, mask=254,
                maskCandidateSameValue=same_candidate,
                flagRule='FamilyPswhDestinationWarning_GenericIsaTableCandidateOnly',
                unresolvedFlags=['cf', 'hc', 'zf'])
    reads.append(dict(pc=0x0246, space='REGISTER', address=5, widthBits=8, value=before['value'],
                      knownBits=before['knownBits'], generations=source_generations, kind='PswhAliasOperand'))
    journal = [dict(ordinal=1, pc=0x0246, space='REGISTER', address=5, widthBits=8, before=before['value'],
                    after=after['value'], beforeGenerations=source_generations, afterGenerations=mask_tags,
                    kind='RegisterMask', valueSource='PSWH&FE', maskCandidateSameValue=same_candidate)]
    steps.append(_step(0x0246, 0x0249, state))
    intent = dict(pc=0x0249, space='DATA', address=26, widthBits=16, requiredDd=1, value=word,
                  knownBits=word_bits, sourceGenerations=tags,
                  accumulatorGenerations=[load_tags['al'], load_tags['ah']], actualWrite=None)
    return _effect_record(None, 0x0249, state, shadow_proof, pswh=pswh, prospectiveIe=intent,
                          steps=steps, reads=reads, journal=journal)


def _ingress_result(reason, history=None, projected=None):
    return dict(status='RefusedSourcePremise' if projected is None else 'QualifiedSymbolicIngress', reason=reason,
                entryClass=history['sourceKind'] if history is not None else None,
                stopBoundary=_INGRESS_STOP if history is not None else None,
                projectedInput=projected, sourceHistory=history, **_empty_events(_INGRESS_LIMITS))


def _reference_history(source):
    if not _keys(source, 'kind baseSha sourceFingerprint input result'):
        return 'ClosedFrozenIngressSourceRequired', None
    kind = source['kind']
    if type(kind) is not str or _FROZEN.get(kind) != (source['baseSha'], source['sourceFingerprint']):
        return 'ExactFrozenIngressIdentityRequired', None
    direct = kind == _DIRECT
    operation = 'alternate_response_selector' if direct else 'detached_0240_0241_transform'
    try:
        prior = (m2df if direct else m2dg)(dict(operation=operation, input=source['input']))
        if canonical(prior) != canonical(source['result']):
            return 'FrozenIngressReplayMismatch', None
    except (ValueError, KeyError, TypeError, RecursionError, OverflowError):
        return 'FrozenIngressReplayMismatch', None
    steps = prior['steps']
    if direct:
        if (prior['status'], prior['outcome'], prior['entryQualification'], prior['boundary'],
                prior['stopBoundary'], prior['responseCandidate'], prior['prospectiveStbufIntent']) != (
                'CompleteConditional', 'CounterBeyondLength', 'DetachedConditionalSourcePath', 0x0244,
                _INGRESS_STOP, None, None) or not steps or steps[0]['pc'] != 0x0227 or (
                steps[-1]['pc'], steps[-1]['next'], steps[-1]['branchTaken']) != (0x024F, 0x0244, True):
            return 'Direct024fIngressRequired', None
        origin, assumptions, missing = ('M2df024fTo0244', source['input']['snapshot']['assumptions'],
                                        prior['unresolvedConstraints'])
        state = {**prior['state'], **{key: prior[key] for key in ('registerGenerations', 'registerKnownBits')}}
    else:
        if (prior['status'], prior['entryKind'], prior['stopPc'], prior['stopBoundary']) != (
                'ConditionalSourceArrivalAt0244', 'DetachedSymbolicEntry', 0x0244, _INGRESS_STOP) or [
                (row['pc'], row['next']) for row in steps] != [(0x0240, 0x0241), (0x0241, 0x0244)]:
            return 'CompleteDetached0240IngressRequired', None
        origin, assumptions, missing = 'M2dg0240To0241To0244', source['input']['assumptions'], prior['unresolved']
        state = prior['state']
    return None, dict(sourceKind=kind, sourceBaseSha=source['baseSha'], sourceFingerprint=source['sourceFingerprint'],
                      sourcePath=origin, sourceState=state, sourceAssumptions=assumptions,
                      precedingWrites=prior['journal'], steps=steps, unresolved=missing)


def _ingress(query):
    if not _keys(query, 'source assumptions shadowEvidence'):
        return _ingress_result('ClosedEpilogueIngressQueryRequired')
    refusal, history = _reference_history(query['source'])
    if refusal is not None:
        return _ingress_result(refusal)
    premises, evidence = query['assumptions'], query['shadowEvidence']
    if (not _keys(premises, 'noInterference memoryModel pswhAlias')
            or not _optional_bool(premises['noInterference']) or not _optional_bool(premises['pswhAlias'])
            or premises['memoryModel'] is not None and type(premises['memoryModel']) is not str):
        return deepcopy(_ingress_result('ClosedEpilogueIngressAssumptionsRequired', history))
    if not _keys(evidence, 'writer events'):
        return deepcopy(_ingress_result('ClosedIngressShadowEvidenceRequired', history))
    state = history['sourceState']
    shadow = dict(evidence)
    for part, address in (('low', '00F8'), ('high', '00F9')):
        if address not in state['memory'] or address not in state['generations']:
            return deepcopy(_ingress_result('ExactFrozenShadowByteSlotsRequired', history))
        bits = {field.rsplit('.', 1)[-1]: bit for field, bit in state['knownBits'].items()
                if field.startswith(address + '.')}
        shadow[part] = dict(value=state['memory'][address], generation=state['generations'][address], knownBits=bits)
    projected = dict(sourceId='M2dhReviewed0244_0246', entryPc=0x0244, entryClass='DetachedSymbolic0244',
                     assumptions=premises, shadow=shadow,
                     **{key: state[key] for key in ('registers', 'registerGenerations', 'registerKnownBits')})
    return deepcopy(_ingress_result('ExactFrozenIngressReplay', history, projected))


def _lane_values(lane):
    ingress, local = lane['ingress'], lane['local']
    projected = ingress['projectedInput']
    before = projected['registers']
    after = (local['state'] or {}).get('registers', {})
    return {
        'memoryModel': projected['assumptions']['memoryModel'],
        'lowGeneration': projected['shadow']['low']['generation'],
        'highGeneration': projected['shadow']['high']['generation'],
        'prospectiveIeWord': (local['prospectiveIe'] or {}).get('value'),
        'prospectiveIeKnownBits': (local['prospectiveIe'] or {}).get('knownBits'),
        'pswhMaskCandidate': (local['pswh'] or {}).get('maskCandidate'),
        'shadowClassification': (local['shadowProof'] or {}).get('classification'),
        'sourcePath': ingress['sourceHistory']['sourcePath'],
        **{'incoming.' + flag: before.get(flag) for flag in _FLAGS},
        **{'local.' + key: after.get(key) for key in ('al', 'ah', *_FLAGS)},
    }


def _compare(query):
    result = dict(status='RefusedSourcePremise', reason='ClosedIngressComparisonRequired', entryClass=None,
                  stopBoundary=None, direct=None, detached=None, fields={}, **_empty_events(_COMPARE_LIMITS))
    if not _keys(query, 'direct detached'):
        return result
    for key, kind in (('direct', _DIRECT), ('detached', _DETACHED)):
        ingress = _ingress(query[key])
        projected = ingress['projectedInput']
        result[key] = dict(ingress=ingress, local=_epilogue(projected)
                           if projected is not None and ingress['entryClass'] == kind else None)
    lanes = result['direct'], result['detached']
    if any(lane['local'] is None for lane in lanes):
        return {**result, 'reason': 'DistinctQualifiedIngressKindsRequired'}
    left, right = map(_lane_values, lanes)
    fields = {key: dict(direct=left[key], detached=right[key],
                        relation='Unknown' if left[key] is None or right[key] is None else
                        'Equal' if left[key] == right[key] else 'Different') for key in left}
    complete = all(lane['local']['status'] == 'ConditionalSourceArrivalAt0249' for lane in lanes)
    qualified = ('CurrentReadGenerationsDeclared', 'ConditionalCandidateGenerationMatched')
    equality_keys = ('memoryModel', 'lowGeneration', 'highGeneration', 'prospectiveIeWord',
                     'prospectiveIeKnownBits', 'pswhMaskCandidate')
    equal = (complete and left['memoryModel'] == _MEMORY
             and all(fields[key]['relation'] == 'Equal' for key in equality_keys)
             and all(row['shadowClassification'] in qualified for row in (left, right))
             and all(fields['incoming.' + flag]['relation'] != 'Different' for flag in _FLAGS)
             and all(left[key] == right[key] for key in left if key.startswith('local.')))
    return {**result, 'status': 'ConditionalEquivalentLocalEpilogueEffect' if equal else
            'DistinctLocalEpilogueEffectsCompared', 'reason': 'ExactConditionalLocalEffectsMatch' if equal else
            'LocalEquivalenceNotEstablished' if complete else 'LocalEpilogueProofIncomplete',
            'stopBoundary': _EFFECT_STOP if complete else None, 'fields': fields}


def expected(case):
    """Generate the full static expectation using only independently modeled effects."""
    return {'detached_epilogue_0244_0246': _epilogue, 'epilogue_ingress_adapter': _ingress,
            'compare_epilogue_ingresses': _compare}[case['operation']](case['input'])
