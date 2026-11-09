"""Bounded register effects separated by the mode-zero peripheral barriers."""
from copy import deepcopy

from detached_post_stbuf_0240_0241.fragment import _valid_state
from length_checksum_dataflow.state import arithmetic
from payload_consumer_tail.state import bit_consensus, candidates, unique

from .analysis import AUTHORITY

SOURCE_ID = 'M2diReviewedModeZero'
STOPS = {0x029E: 'STOP_BEFORE_UNQUALIFIED_SRSTAT_RMW_029E',
         0x02A5: 'STOP_BEFORE_UNQUALIFIED_SRSTAT_RMW_02A5',
         0x02AE: 'STOP_BEFORE_UNQUALIFIED_SRBUF_READ_02AE'}
REASONS = {0x029E: 'UnqualifiedSrstatBit3Rmw', 0x02A5: 'UnqualifiedSrstatBit2Rmw',
           0x02AE: 'UnqualifiedSrbufRead'}
_ENTRY_FIELDS = {'sourceId', 'entryPc', 'entryClass', 'assumptions', 'state'}
_SUFFIX = {0x02A1: (0x029E, 3, 0x02A3, 1, 0x02A5),
           0x02A8: (0x02A5, 2, 0x02AA, 2, 0x02AC)}
_LIMITS = ('PhysicalSfrMappingUnknown', 'NativeModeZeroIngressUnproved', 'ActualSrbufOwnerUnknown',
           'RxReadyAcknowledgementAndReassertionUnknown', 'SrstatCollisionOrderingUnknown',
           'IrqPendingAndFrameUnknown')


def _shape(value, fields):
    return type(value) is dict and value.keys() == fields


def _tag(value):
    return value is None or type(value) is str and 0 < len(value) <= 256


def _admit(query, pc, entry, suffix=False):
    if not _shape(query, _ENTRY_FIELDS | ({'statusHypothesis'} if suffix else set())):
        return 'ClosedModeZeroSnapshotRequired', None
    if query['sourceId'] != SOURCE_ID:
        return 'ExactReviewedModeZeroSourceRequired', None
    if pc is None or type(query['entryPc']) is not int or query['entryPc'] != pc or query['entryClass'] != entry:
        return 'ExactDetachedEntryRequired', None
    assumptions = query['assumptions']
    if (not _shape(assumptions, {'noInterference'})
            or assumptions['noInterference'] is not None and type(assumptions['noInterference']) is not bool):
        return 'ClosedModeZeroPremisesRequired', None
    if not _valid_state(query['state']):
        return 'TypedModeZeroStateRequired', None
    state = deepcopy(query['state'])
    if assumptions['noInterference'] is not True:
        return 'NoInterferencePremiseRequired', state
    return None, state


def _peripheral(pc):
    status = pc != 0x02AE
    return {'pc': pc, 'space': 'DATA', 'address': 0x0056 if status else 0x0055, 'widthBits': 8,
            'standardRegister': 'SRSTAT' if status else 'SRBUF',
            'standardPermission': 'ReadWrite' if status else 'ReadOnly',
            'access': 'ReadModifyWrite' if status else 'Read',
            'bit': {0x029E: 3, 0x02A5: 2}.get(pc),
            'classification': 'PotentialSfr' if status else 'PeripheralReadBlocked',
            'actualAccess': None, 'actualValue': None, 'physicalMappingEstablished': False}


def _result(status, reason, pc, entry, state, steps=(), journal=()):
    blocked = status == 'PeripheralBoundaryBlocked'
    return {'status': status, 'reason': reason, 'entryClass': entry, 'stopPc': pc,
            'stopBoundary': STOPS[pc] if blocked else None, 'state': state, 'steps': list(steps),
            'reads': [], 'journal': list(journal), 'peripheralObligation': _peripheral(pc) if blocked else None,
            'unresolved': list(_LIMITS), 'executionAuthority': dict(AUTHORITY)}


def _tags(state, pc, fields, extra=()):
    tags = {name: f'M2di:{pc:04X}:{name.upper()}' for name in fields}
    existing = set(state['registerGenerations'].values()) | set(state['generations'].values()) | set(extra)
    return None if set(tags.values()) & existing else tags


def _step(pc, target, state, branch=None, evidence=None):
    return {'pc': pc, 'next': target, 'kind': 'Branch' if evidence is not None else 'RegisterEffect',
            'branchTaken': branch, 'predicateEvidence': evidence, 'state': deepcopy(state)}


def _blocked(pc, entry, state, steps, journal=()):
    return _result('PeripheralBoundaryBlocked', REASONS[pc], pc, entry, state, steps, journal)


def _corridor(snapshot, qualification):
    reason, state = _admit(snapshot, 0x029D, 'DetachedEntry029D')
    if reason:
        return _result('RefusedSourcePremise', reason, 0x029D, qualification, state)
    tags = _tags(state, 0x029D, ('al', 'dd', 'zf'))
    if tags is None:
        return _result('OutsideVerifiedScope', 'RegisterGenerationCollision', 0x029D, qualification, state)
    state['registers'].update(al=0, dd=0, zf=1)
    state['registerGenerations'].update(tags)
    state['registerKnownBits'].pop('al', None)
    return _blocked(0x029E, qualification, state, [_step(0x029D, 0x029E, state)])


def mode_zero_corridor_029d(snapshot):
    """Clear AL at an independent symbolic entry and stop before the first SRSTAT RMW."""
    return _corridor(snapshot, 'DetachedEntry029D')


def _add(state, pc, amount, extra):
    if state['registers'].get('dd') != 0:
        return 'ByteFormDd0Required'
    if state['registerGenerations'].get('al') is None:
        return 'AlSourceGenerationMissing'
    tags = _tags(state, pc, ('al', 'cf', 'hc', 'zf'), extra)
    if tags is None:
        return 'RegisterGenerationCollision'
    known = state['registerKnownBits'].get('al', {})
    raw = state['registers'].get('al')
    possible = candidates(raw, {f'AL.{bit}': value for bit, value in known.items()}, 'AL')
    arithmetic_rows = [arithmetic(value, amount) for value in possible]
    values = {row['al'] for row in arithmetic_rows}
    flags = {key: unique({row[key] for row in arithmetic_rows}) for key in ('cf', 'hc', 'zf')}
    al = unique(values)
    state['registers'].update(al=al, **flags)
    state['registerGenerations'].update(tags)
    state['registerKnownBits'].pop('al', None)
    if al is None:
        state['registerKnownBits']['al'] = {key[-1]: value for key, value in bit_consensus(values, 'AL').items()}
    return None


def _store_ah(state, extra):
    r, tags, bits = (state[key] for key in ('registers', 'registerGenerations', 'registerKnownBits'))
    if r.get('dd') != 0:
        return 'ByteFormDd0Required', None
    if tags.get('al') is None:
        return 'AlSourceGenerationMissing', None
    new = _tags(state, 0x02AC, ('ah',), extra)
    if new is None:
        return 'RegisterGenerationCollision', None
    low, high = r.get('al'), r.get('ah')
    event = {'ordinal': 1, 'pc': 0x02AC, 'space': 'REGISTER', 'address': 0x0007, 'widthBits': 8,
             'alias': 'DATA0007=AH', 'before': high, 'after': low, 'beforeGeneration': tags.get('ah'),
             'afterGeneration': new['ah'], 'sourceGeneration': tags['al'], 'kind': 'RegisterAliasStore',
             'valueSource': 'AL', 'sameValue': None if None in (low, high) else low == high}
    r['ah'] = low
    tags.update(new)
    bits.pop('ah', None)
    if 'al' in bits:
        bits['ah'] = dict(bits['al'])
    return None, event


def mode_zero_detached_suffix(snapshot):
    """Model a software-only suffix from an explicit post-RB flag hypothesis."""
    pc = snapshot.get('entryPc') if type(snapshot) is dict else None
    pc = pc if type(pc) is int and pc in _SUFFIX else None
    entry = 'DetachedPostRbEntry'
    reason, state = _admit(snapshot, pc, entry, suffix=True)
    if reason:
        return _result('RefusedSourcePremise', reason, pc, entry, state)
    source, bit, add, amount, target = _SUFFIX[pc]
    premise = snapshot['statusHypothesis']
    if (not _shape(premise, {'sourcePc', 'bit', 'value', 'generation'})
            or type(premise['sourcePc']) is not int or premise['sourcePc'] != source
            or type(premise['bit']) is not int or premise['bit'] != bit
            or premise['value'] is not None and (type(premise['value']) is not int or premise['value'] not in (0, 1))
            or not _tag(premise['generation'])):
        return _result('RefusedSourcePremise', 'ExactDetachedStatusBitPremiseRequired', pc, entry, state)
    value, generation = premise['value'], premise['generation']
    zf, zf_generation = state['registers'].get('zf'), state['registerGenerations'].get('zf')
    evidence = {'statusPc': source, 'address': 0x0056, 'bit': bit, 'hypotheticalOldBit': value,
                'oldBitGeneration': generation, 'zf': zf, 'zfGeneration': zf_generation,
                'sourceClass': 'DetachedSymbolicPremise_NoSrstatAccess'}
    if value is None or zf is None or generation is None or zf_generation is None:
        reason = 'OldSrstatBitOrZfUnknown' if value is None or zf is None else 'PredicateGenerationMissing'
        return _result('IndeterminateBranch', reason, pc, entry, state,
                       [_step(pc, None, state, evidence=evidence)])
    if zf != 1 - value:
        return _result('RefusedSourcePremise', 'ContradictoryDetachedZfPremise', pc, entry, state)
    taken = zf == 1
    steps = [_step(pc, target if taken else add, state, taken, evidence)]
    extra = (generation, zf_generation)
    if not taken:
        reason = _add(state, add, amount, extra)
        if reason:
            return _result('OutsideVerifiedScope', reason, add, entry, state, steps)
        steps.append(_step(add, target, state))
    if target == 0x02A5:
        return _blocked(target, entry, state, steps)
    reason, event = _store_ah(state, extra)
    if reason:
        return _result('OutsideVerifiedScope', reason, 0x02AC, entry, state, steps)
    steps.append(_step(0x02AC, 0x02AE, state))
    return _blocked(0x02AE, entry, state, steps, [event])
