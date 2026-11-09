"""Expected mode-zero records from primary forms and frozen reference inputs."""
from copy import deepcopy

from conditional_flag_mode_shadow.state import validate as frozen_status_schema
from detached_post_stbuf_0240_0241.reference_oracle import _typed_state
from length_checksum_dataflow.reference_oracle import parser_step as frozen_status_reference

from .analysis import AUTHORITY

_ID = 'M2diReviewedModeZero'
_MAIN_PC = 0x029D
_MAIN_CLASS = 'DetachedEntry029D'
_SUFFIX_CLASS = 'DetachedPostRbEntry'
_LIMITS = ['PhysicalSfrMappingUnknown', 'NativeModeZeroIngressUnproved', 'ActualSrbufOwnerUnknown',
           'RxReadyAcknowledgementAndReassertionUnknown', 'SrstatCollisionOrderingUnknown',
           'IrqPendingAndFrameUnknown']
_BARRIERS = {
    0x029E: ('UnqualifiedSrstatBit3Rmw', 'STOP_BEFORE_UNQUALIFIED_SRSTAT_RMW_029E', 3),
    0x02A5: ('UnqualifiedSrstatBit2Rmw', 'STOP_BEFORE_UNQUALIFIED_SRSTAT_RMW_02A5', 2),
    0x02AE: ('UnqualifiedSrbufRead', 'STOP_BEFORE_UNQUALIFIED_SRBUF_READ_02AE', None),
}
_SUFFIXES = {
    0x02A1: {'rb': 0x029E, 'bit': 3, 'add': 0x02A3, 'immediate': 1, 'target': 0x02A5},
    0x02A8: {'rb': 0x02A5, 'bit': 2, 'add': 0x02AA, 'immediate': 2, 'target': 0x02AC},
}


def _keys(value, *names):
    return type(value) is dict and set(value) == set(names)


def _generation(value):
    return value is None or type(value) is str and 1 <= len(value) <= 256


def _admission(query, pc, entry, *, post_rb=False):
    fields = ['sourceId', 'entryPc', 'entryClass', 'assumptions', 'state']
    if post_rb:
        fields.append('statusHypothesis')
    if not _keys(query, *fields):
        return 'ClosedModeZeroSnapshotRequired', None
    if query['sourceId'] != _ID:
        return 'ExactReviewedModeZeroSourceRequired', None
    if pc is None or type(query['entryPc']) is not int or query['entryPc'] != pc or query['entryClass'] != entry:
        return 'ExactDetachedEntryRequired', None
    assumptions = query['assumptions']
    if (not _keys(assumptions, 'noInterference')
            or type(assumptions['noInterference']) not in (bool, type(None))):
        return 'ClosedModeZeroPremisesRequired', None
    if not _typed_state(query['state']):
        return 'TypedModeZeroStateRequired', None
    state = deepcopy(query['state'])
    return (None if assumptions['noInterference'] is True else 'NoInterferencePremiseRequired', state)


def _boundary(pc):
    reason, name, bit = _BARRIERS[pc]
    if bit is None:
        obligation = (0x55, 'SRBUF', 'ReadOnly', 'Read', 'PeripheralReadBlocked')
    else:
        obligation = (0x56, 'SRSTAT', 'ReadWrite', 'ReadModifyWrite', 'PotentialSfr')
    address, register, permission, access, classification = obligation
    return reason, name, dict(pc=pc, space='DATA', address=address, widthBits=8, standardRegister=register,
                              standardPermission=permission, access=access, bit=bit, classification=classification,
                              actualAccess=None, actualValue=None, physicalMappingEstablished=False)


def _result(status, reason, pc, entry, state, steps=(), journal=()):
    name, obligation = None, None
    if status == 'PeripheralBoundaryBlocked':
        reason, name, obligation = _boundary(pc)
    return dict(status=status, reason=reason, entryClass=entry, stopPc=pc, stopBoundary=name,
                state=state, steps=list(steps), reads=[], journal=list(journal), peripheralObligation=obligation,
                unresolved=list(_LIMITS), executionAuthority=dict(AUTHORITY))


def _register_event(pc, target, state):
    return dict(pc=pc, next=target, kind='RegisterEffect', branchTaken=None, predicateEvidence=None,
                state=deepcopy(state))


def _branch_event(pc, target, state, condition, evidence):
    return dict(pc=pc, next=target, kind='Branch', branchTaken=condition, predicateEvidence=evidence,
                state=deepcopy(state))


def _propose_generations(pc, names, state, additional=()):
    occupied = [*state['generations'].values(), *state['registerGenerations'].values(), *additional]
    proposed = {name: 'M2di:{:04X}:{}'.format(pc, name.upper()) for name in names}
    if any(tag in occupied for tag in proposed.values()):
        return None
    return proposed


def _main(snapshot, entry=_MAIN_CLASS):
    failure, state = _admission(snapshot, _MAIN_PC, _MAIN_CLASS)
    if failure is not None:
        return _result('RefusedSourcePremise', failure, _MAIN_PC, entry, state)
    generations = _propose_generations(_MAIN_PC, ['al', 'zf', 'dd'], state)
    if generations is None:
        return _result('OutsideVerifiedScope', 'RegisterGenerationCollision', _MAIN_PC, entry, state)
    state['registers'].update({'al': 0, 'zf': 1, 'dd': 0})
    state['registerGenerations'].update(generations)
    state['registerKnownBits'].pop('al', None)
    return _result('PeripheralBoundaryBlocked', None, 0x029E, entry, state,
                   [_register_event(_MAIN_PC, 0x029E, state)])


def _bit(value, position):
    return (value // (2 ** int(position))) % 2


def _possible(raw, bits):
    if raw is not None:
        return [raw]
    return [n for n in range(256) if all(_bit(n, position) == value for position, value in bits.items())]


def _consensus(values):
    values = list(values)
    first = values[0]
    return first if all(value == first for value in values[1:]) else None


def _reference_add(operand, amount):
    """Independently calculate the carry chain through the byte."""
    carry, result, halfway = 0, 0, None
    for position in range(8):
        carry, bit = divmod(_bit(operand, position) + _bit(amount, position) + carry, 2)
        result += bit * 2 ** position
        if position == 3:
            halfway = carry
    return dict(al=result, zf=int(result == 0), cf=carry, hc=halfway)


def _writer_admission(state, pc, fields, additional):
    registers, tags = state['registers'], state['registerGenerations']
    if registers.get('dd') != 0:
        return 'ByteFormDd0Required', None
    if tags.get('al') is None:
        return 'AlSourceGenerationMissing', None
    fresh = _propose_generations(pc, fields, state, additional)
    return ('RegisterGenerationCollision', None) if fresh is None else (None, fresh)


def _suffix(snapshot):
    pc = snapshot.get('entryPc') if type(snapshot) is dict else None
    if type(pc) is not int or pc not in _SUFFIXES:
        pc = None
    entry = _SUFFIX_CLASS
    failure, state = _admission(snapshot, pc, entry, post_rb=True)
    if failure is not None:
        return _result('RefusedSourcePremise', failure, pc, entry, state)
    site = _SUFFIXES[pc]
    premise = snapshot['statusHypothesis']
    if (not _keys(premise, 'sourcePc', 'bit', 'value', 'generation')
            or type(premise['sourcePc']) is not int or premise['sourcePc'] != site['rb']
            or type(premise['bit']) is not int or premise['bit'] != site['bit']
            or premise['value'] is not None and (type(premise['value']) is not int or premise['value'] not in (0, 1))
            or not _generation(premise['generation'])):
        return _result('RefusedSourcePremise', 'ExactDetachedStatusBitPremiseRequired', pc, entry, state)
    registers, tags, bits = (state[key] for key in ('registers', 'registerGenerations', 'registerKnownBits'))
    value, generation = premise['value'], premise['generation']
    zf, zf_tag = registers.get('zf'), tags.get('zf')
    evidence = dict(statusPc=site['rb'], address=0x56, bit=site['bit'], hypotheticalOldBit=value,
                    oldBitGeneration=generation, zf=zf, zfGeneration=zf_tag,
                    sourceClass='DetachedSymbolicPremise_NoSrstatAccess')
    if None in (value, zf, generation, zf_tag):
        reason = 'OldSrstatBitOrZfUnknown' if None in (value, zf) else 'PredicateGenerationMissing'
        return _result('IndeterminateBranch', reason, pc, entry, state,
                       [_branch_event(pc, None, state, None, evidence)])
    if (value, zf) not in ((0, 1), (1, 0)):
        return _result('RefusedSourcePremise', 'ContradictoryDetachedZfPremise', pc, entry, state)

    add_pc, target = site['add'], site['target']
    steps = [_branch_event(pc, target if value == 0 else add_pc, state, value == 0, evidence)]
    additional = [generation, zf_tag]
    if value == 1:
        names = ('al', 'zf', 'cf', 'hc')
        failure, fresh = _writer_admission(state, add_pc, names, additional)
        if failure is not None:
            return _result('OutsideVerifiedScope', failure, add_pc, entry, state, steps)
        possible = _possible(registers.get('al'), bits.get('al', {}))
        concrete = [_reference_add(operand, site['immediate']) for operand in possible]
        registers.update({name: _consensus(row[name] for row in concrete) for name in names})
        tags.update(fresh)
        bits.pop('al', None)
        if registers['al'] is None:
            bits['al'] = {str(position): bit for position in range(8)
                          if (bit := _consensus(_bit(row['al'], position) for row in concrete)) is not None}
        steps.append(_register_event(add_pc, target, state))
    if target == 0x02A5:
        return _result('PeripheralBoundaryBlocked', None, target, entry, state, steps)

    failure, fresh = _writer_admission(state, target, ['ah'], additional)
    if failure is not None:
        return _result('OutsideVerifiedScope', failure, target, entry, state, steps)
    old, new = registers.get('ah'), registers.get('al')
    event = dict(ordinal=1, pc=target, space='REGISTER', address=7, widthBits=8, alias='DATA0007=AH',
                 before=old, after=new, beforeGeneration=tags.get('ah'), afterGeneration=fresh['ah'],
                 sourceGeneration=tags['al'], kind='RegisterAliasStore', valueSource='AL',
                 sameValue=None if old is None or new is None else old == new)
    registers['ah'] = new
    tags.update(fresh)
    bits.pop('ah', None)
    if 'al' in bits:
        bits['ah'] = deepcopy(bits['al'])
    steps.append(_register_event(target, 0x02AE, state))
    return _result('PeripheralBoundaryBlocked', None, 0x02AE, entry, state, steps, [event])


def _composition_result(reason, prefix=None, handoff=None, corridor=None):
    if corridor is not None:
        return deepcopy(dict(corridor, prefix=prefix, handoff=handoff, corridor=corridor))
    status = 'RefusedSourcePremise'
    entry = 'FrozenM2coStatusPrefix'
    if prefix is not None and reason == prefix['reason']:
        status = prefix['status']
        if prefix['steps'] and prefix['steps'][0]['branchTaken'] is False:
            entry = 'FrozenM2coOrdinaryPath'
    if reason == 'UnknownBranchPredicate' and entry == 'FrozenM2coStatusPrefix':
        status = 'IndeterminateBranchAt021F'
    return deepcopy(dict(status=status, reason=reason, entryClass=entry,
                         stopPc=0x021F if prefix is None else prefix['boundary'],
                         stopBoundary=None, state=None if prefix is None else prefix['state'], steps=[], reads=[],
                         journal=[], peripheralObligation=None, unresolved=[] if reason is None else [reason],
                         executionAuthority=dict(AUTHORITY), prefix=prefix, handoff=None, corridor=None))


def _compose(query):
    if not _keys(query, 'sourceId', 'snapshot', 'statusGeneration', 'memoryModel'):
        return _composition_result('ClosedModeZeroCompositionRequired')
    if query['sourceId'] != _ID:
        return _composition_result('ExactReviewedModeZeroSourceRequired')
    try:
        snapshot = frozen_status_schema(query['snapshot'])
    except ValueError:
        return _composition_result('TypedFrozenM2coSnapshotRequired')
    mapping = 'ConditionalStandardInternal207'
    if query['memoryModel'] != mapping:
        return _composition_result('QualifiedStatus0356MappingRequired')
    requested = query['statusGeneration']
    declared = snapshot['generations']['0356']
    if requested is None or declared is None:
        return _composition_result('Status0356GenerationMissing')
    if not _generation(requested):
        return _composition_result('TypedStatusGenerationRequired')
    if requested != declared:
        return _composition_result('Status0356GenerationMismatch')
    prefix = frozen_status_reference(snapshot)
    if not prefix['steps']:
        return _composition_result(prefix['reason'], prefix)
    raw = snapshot['memory']['0356']
    mode = snapshot['knownBits'].get('0356.1') if raw is None else _bit(raw, 1)
    if mode != 0:
        return _composition_result(prefix['reason'], prefix)
    handoff = dict(entryPc=0x029D, branchPc=0x021F, branchTaken=True, statusAddress=0x0356,
                   statusGeneration=declared, memoryModel=mapping, reseeded=False)
    downstream = dict(sourceId=_ID, entryPc=_MAIN_PC, entryClass=_MAIN_CLASS,
                      assumptions={'noInterference': snapshot['assumptions']['noInterference']},
                      state=dict(prefix['state'], registerGenerations={}, registerKnownBits={}))
    corridor = _main(downstream, 'ConfirmedEntryFrom021F')
    return _composition_result(corridor['reason'], prefix, handoff, corridor)


def expected(case):
    """Compute a full static expected record without importing any M2di model."""
    return {'mode_zero_corridor_029d': _main, 'mode_zero_detached_suffix': _suffix,
            'mode_zero_parser_step': _compose}[case['operation']](case['input'])
