"""Source-qualified word read and PSWH alias effect with a hard stop before IE."""
from copy import deepcopy

from indexed_suffix_ie_provenance.provenance import SHADOW_WRITERS
from payload_consumer_tail.state import bit_consensus, candidates, unique

from .analysis import AUTHORITY

SOURCE_ID = 'M2dhReviewed0244_0246'
MEMORY_MODEL = 'ConditionalDocumentedInternalRam'
UNQUALIFIED = 'STOP_BEFORE_UNQUALIFIED_0244_OR_0246'
IE_STOP = 'STOP_BEFORE_IE_WRITE_0249'
WIDTHS = {'al': 8, 'ah': 8, 'cf': 1, 'zf': 1, 'hc': 1, 'dd': 1, 'mie': 1, 'otherPsw': 16,
          'lrb': 16, 'scb': 3, 'usp': 16, 'ssp': 16}
PSWH_BITS = {'mie': 0, 'dd': 4, 'hc': 5, 'zf': 6, 'cf': 7}
OBLIGATIONS = ('ActualHardwareShadowOwnerUnknown', 'ActualDataMapAndFrameOverlapUnknown',
               'PswhSelfDestinationFlagApplicabilityUnresolved', 'ActualIePolarityAndPendingStateUnknown',
               'ActualIeAcknowledgementAndReassertionUnknown', 'RtiFrameAndNativeReturnUnestablished')
SHADOW = SHADOW_WRITERS[0x00F8]


def _shape(obj, fields):
    return type(obj) is dict and obj.keys() == set(fields.split())


def _uint(value, width):
    return value is None or type(value) is int and 0 <= value < 1 << width


def _tag(value):
    return value is None or type(value) is str and 0 < len(value) <= 256


def _bits(value, bits):
    return (type(bits) is dict and all(type(key) is str and len(key) == 1 and key in '01234567'
                                      and type(bit) is int and bit in (0, 1)
                                      and (value is None or value >> int(key) & 1 == bit)
                                      for key, bit in bits.items()))


def _shadow_valid(shadow):
    if not _shape(shadow, 'low high writer events'):
        return False
    for part in (shadow['low'], shadow['high']):
        if (not _shape(part, 'value knownBits generation') or not _uint(part['value'], 8)
                or not _bits(part['value'], part['knownBits']) or not _tag(part['generation'])):
            return False
    writer = shadow['writer']
    if writer is not None and (not _shape(writer, 'pc generation') or not _uint(writer['pc'], 16)
                               or not _tag(writer['generation'])):
        return False
    events = shadow['events']
    return type(events) is list and len(events) <= 32 and all(
        _shape(event, 'address widthBits generation value')
        and type(event['widthBits']) is int and event['widthBits'] in (8, 16)
        and _uint(event['address'], 16) and _tag(event['generation']) and _uint(event['value'], event['widthBits'])
        for event in events)


def _admit(snapshot):
    if not _shape(snapshot, 'sourceId entryPc entryClass assumptions registers registerGenerations registerKnownBits shadow'):
        return 'ClosedDetachedEpilogueSnapshotRequired', None
    if snapshot['sourceId'] != SOURCE_ID or type(snapshot['entryPc']) is not int or snapshot['entryPc'] != 0x0244:
        return 'ExactReviewedDetachedEntryRequired', None
    if snapshot['entryClass'] != 'DetachedSymbolic0244':
        return 'DetachedSymbolicClassRequired', None
    assumptions = snapshot['assumptions']
    if (not _shape(assumptions, 'noInterference memoryModel pswhAlias')
            or any(assumptions[key] is not None and type(assumptions[key]) is not bool
                   for key in ('noInterference', 'pswhAlias'))
            or assumptions['memoryModel'] not in (None, MEMORY_MODEL, 'Unknown')):
        return 'ClosedEpiloguePremisesRequired', None
    r, g, k = (snapshot[key] for key in ('registers', 'registerGenerations', 'registerKnownBits'))
    if (any(type(row) is not dict for row in (r, g, k)) or not r.keys() <= WIDTHS.keys()
            or not all(_uint(value, WIDTHS[name]) for name, value in r.items())
            or r.get('otherPsw') is not None and r['otherPsw'] & 0xF107
            or not g.keys() <= r.keys() or not all(_tag(value) for value in g.values())
            or not k.keys() <= {'al', 'ah'} or not k.keys() <= r.keys()
            or not all(_bits(r[name], bits) for name, bits in k.items())
            or not _shadow_valid(snapshot['shadow'])):
        return 'TypedEpilogueStateRequired', None
    state = deepcopy({'registers': r, 'registerGenerations': g, 'registerKnownBits': k})
    if assumptions['noInterference'] is not True:
        return 'NoInterferencePremiseRequired', state
    if assumptions['memoryModel'] != MEMORY_MODEL:
        return 'QualifiedShadowRamReadRequired', state
    return None, state


def _lineage(shadow, parts, generations):
    writer, events = shadow['writer'], shadow['events']
    candidate_value = SHADOW.get(writer['pc']) if writer else None
    overlap, unknown = [], []
    for ordinal, event in enumerate(events, 1):
        address = event['address']
        if address is None:
            unknown.append(ordinal)
        else:
            base = address & 0xFFFE if event['widthBits'] == 16 else address
            if {0xF8, 0xF9}.intersection(range(base, base + event['widthBits'] // 8)):
                overlap.append(ordinal)
    if overlap or unknown:
        classification = 'InterveningWriterPossible'
    elif writer is not None and candidate_value is None:
        classification = 'UnreviewedCandidateWriter'
    elif None in generations or writer is not None and writer['generation'] is None:
        classification = 'CurrentReadGenerationMissing'
    elif writer is None:
        classification = 'CurrentReadGenerationsDeclared'
    elif generations != [writer['generation']] * 2:
        classification = 'CandidateGenerationMismatch'
    elif parts != [candidate_value & 255, candidate_value >> 8]:
        classification = 'CandidateValueNotEstablished'
    elif any(event['generation'] == writer['generation'] for event in events):
        classification = 'CandidateGenerationReused'
    else:
        classification = 'ConditionalCandidateGenerationMatched'
    return {'classification': classification,
            'knownSourceProducers': [{'pc': pc, 'value': value} for pc, value in SHADOW.items()],
            'candidateWriter': deepcopy(writer), 'candidateWord': candidate_value,
            'readGenerations': generations, 'interveningEvents': deepcopy(events),
            'overlapOrdinals': overlap, 'unknownFootprintOrdinals': unknown,
            'nativeOwner': None, 'conditionalWordWriterGenerationMatched':
                classification == 'ConditionalCandidateGenerationMatched'}


def _pswh(r):
    bits = {str(bit): r[key] for key, bit in PSWH_BITS.items() if r.get(key) is not None}
    if r.get('otherPsw') is not None:
        bits.update({str(bit): r['otherPsw'] >> (8 + bit) & 1 for bit in (1, 2, 3)})
    return _byte(bits)


def _byte(bits):
    return {'value': sum(value << int(bit) for bit, value in bits.items()) if len(bits) == 8 else None,
            'knownBits': bits}


def _result(reason, pc, state=None, proof=None, pswh=None, intent=None, steps=(), reads=(), journal=()):
    return {'status': 'ConditionalSourceArrivalAt0249' if reason is None else 'OutsideVerifiedScope',
            'reason': reason, 'entryClass': 'DetachedSymbolic0244', 'stopPc': pc,
            'stopBoundary': IE_STOP if pc == 0x0249 else UNQUALIFIED, 'state': state,
            'shadowProof': proof, 'pswh': pswh, 'prospectiveIe': intent, 'steps': list(steps),
            'reads': list(reads), 'journal': list(journal), 'unresolved': list(OBLIGATIONS),
            'executionAuthority': dict(AUTHORITY)}


def _fresh(state, pc, names, generations):
    tags = {key: f'M2dh:{pc:04X}:{key.upper()}' for key in names}
    if set(tags.values()) & (set(state['registerGenerations'].values()) | set(generations)):
        return None
    return tags


def detached_epilogue_0244_0246(snapshot):
    """Apply only the independently qualified prefix and report prospective IE metadata."""
    reason, state = _admit(snapshot)
    if reason is not None:
        return _result(reason, 0x0244, state)
    shadow = snapshot['shadow']
    slots = [shadow['low'], shadow['high']]
    generations = [slot['generation'] for slot in slots]
    load_tags = _fresh(state, 0x0244, ('al', 'ah', 'dd', 'zf'), generations)
    if load_tags is None:
        return _result('RegisterGenerationCollision', 0x0244, state)
    values = [candidates(slot['value'], {f'B.{key}': value for key, value in slot['knownBits'].items()}, 'B')
              for slot in slots]
    parts = [unique(byte) for byte in values]
    known = [{key[-1]: value for key, value in bit_consensus(byte, 'B').items()} for byte in values]
    word = None if None in parts else parts[0] | parts[1] << 8
    word_bits = {str(8 * offset + int(bit)): value for offset, byte in enumerate(known) for bit, value in byte.items()}
    zero = 0 if any(0 not in byte for byte in values) else 1 if all(byte == {0} for byte in values) else None
    state['registers'].update(al=parts[0], ah=parts[1], dd=1, zf=zero)
    state['registerKnownBits'].update(al=known[0], ah=known[1])
    state['registerGenerations'].update(load_tags)
    proof = _lineage(shadow, parts, generations)
    reads = [{'pc': 0x0244, 'space': 'DATA', 'address': 0xF8, 'widthBits': 16,
              'value': word, 'bytes': parts, 'knownBits': word_bits, 'generations': generations,
              'kind': 'FunctionalWordOperand'}]
    steps = [{'pc': 0x0244, 'next': 0x0246, 'edge': 'ConfirmedStaticCFG', 'state': deepcopy(state)}]
    if snapshot['assumptions']['pswhAlias'] is not True:
        return _result('PswhAliasPremiseRequired', 0x0246, state, proof, steps=steps, reads=reads)
    mask_tags = _fresh(state, 0x0246, ('mie', 'cf', 'hc', 'zf'), generations)
    if mask_tags is None:
        return _result('RegisterGenerationCollision', 0x0246, state, proof, steps=steps, reads=reads)
    r = state['registers']
    before = _pswh(r)
    masked = _byte({**before['knownBits'], '0': 0})
    before_tags = {key: state['registerGenerations'].get(key) for key in PSWH_BITS}
    prior_mie = r.get('mie')
    # The specific PSWH-destination warning leaves these three flags undefined.
    # The generic ANDB table and the mask describe the candidate byte only.
    r.update(mie=0, cf=None, hc=None, zf=None)
    state['registerGenerations'].update(mask_tags)
    after = _pswh(r)
    pswh = {'before': before, 'maskCandidate': masked, 'after': after, 'mask': 0xFE,
            'maskCandidateSameValue': None if prior_mie is None else prior_mie == 0,
            'flagRule': 'FamilyPswhDestinationWarning_GenericIsaTableCandidateOnly',
            'unresolvedFlags': ['cf', 'hc', 'zf']}
    reads.append({'pc': 0x0246, 'space': 'REGISTER', 'address': 5, 'widthBits': 8,
                  'value': before['value'], 'knownBits': before['knownBits'], 'generations': before_tags,
                  'kind': 'PswhAliasOperand'})
    journal = [{'ordinal': 1, 'pc': 0x0246, 'space': 'REGISTER', 'address': 5, 'widthBits': 8,
                'before': before['value'], 'after': after['value'], 'beforeGenerations': before_tags,
                'afterGenerations': mask_tags, 'kind': 'RegisterMask', 'valueSource': 'PSWH&FE',
                'maskCandidateSameValue': pswh['maskCandidateSameValue']}]
    steps.append({'pc': 0x0246, 'next': 0x0249, 'edge': 'ConfirmedStaticCFG', 'state': deepcopy(state)})
    intent = {'pc': 0x0249, 'space': 'DATA', 'address': 0x1A, 'widthBits': 16, 'requiredDd': 1,
              'value': word, 'knownBits': word_bits, 'sourceGenerations': generations,
              'accumulatorGenerations': [load_tags['al'], load_tags['ah']], 'actualWrite': None}
    return _result(None, 0x0249, state, proof, pswh, intent, steps, reads, journal)
