"""Continue the exact frozen M2co mode-zero branch into the new software prefix."""
from copy import deepcopy

from conditional_flag_mode_shadow.state import validate
from length_checksum_dataflow.dispatch import parser_step

from .analysis import AUTHORITY
from .corridor import _corridor

_SOURCE_ID = 'M2diReviewedModeZero'
_MAPPING = 'ConditionalStandardInternal207'
_QUERY_FIELDS = {'sourceId', 'snapshot', 'statusGeneration', 'memoryModel'}
_STATE_KEYS = ('registers', 'memory', 'generations', 'knownBits')


def _result(reason, *, prefix=None, handoff=None, corridor=None):
    if corridor is not None:
        return deepcopy({**corridor, 'prefix': prefix, 'handoff': handoff, 'corridor': corridor})
    ordinary = bool(prefix and prefix['steps'] and prefix['steps'][0]['branchTaken'] is False
                    and reason == prefix['reason'])
    unknown = reason == 'UnknownBranchPredicate' and not ordinary
    status = ('IndeterminateBranchAt021F' if unknown else prefix['status']
              if prefix is not None and reason == prefix['reason'] else 'RefusedSourcePremise')
    return deepcopy({
        'status': status, 'reason': reason,
        'entryClass': 'FrozenM2coOrdinaryPath' if ordinary else 'FrozenM2coStatusPrefix',
        'stopPc': prefix['boundary'] if prefix is not None else 0x021F,
        'stopBoundary': None, 'state': prefix['state'] if prefix is not None else None,
        'steps': [], 'reads': [], 'journal': [], 'peripheralObligation': None,
        'unresolved': [] if reason is None else [reason], 'executionAuthority': dict(AUTHORITY),
        'prefix': prefix, 'handoff': None, 'corridor': None,
    })


def _mode(snapshot):
    raw = snapshot['memory']['0356']
    return snapshot['knownBits'].get('0356.1') if raw is None else (raw >> 1) & 1


def _exact_entry(snapshot, prefix, mode):
    first = prefix['steps'][0]
    read = prefix['reads'][0]
    condition = None if mode is None else mode == 0
    target = None if mode is None else 0x029D if mode == 0 else 0x0222
    known = {field: value for field, value in snapshot['knownBits'].items() if field.startswith('0356.')}
    value = snapshot['memory']['0356']
    return ((first['pc'], first['next'], first['kind'], first['branchTaken']) == (0x021F, target, 'Branch', condition)
            and read == {'pc': 0x021F, 'space': 'DATA', 'address': 0x0356, 'widthBits': 8,
                         'value': value, 'bytes': [value], 'knownBits': known})


def mode_zero_parser_step(query):
    """Verify the retained DATA0356 generation before delegating to frozen M2co."""
    if type(query) is not dict or query.keys() != _QUERY_FIELDS:
        return _result('ClosedModeZeroCompositionRequired')
    if query['sourceId'] != _SOURCE_ID:
        return _result('ExactReviewedModeZeroSourceRequired')
    try:
        snapshot = validate(query['snapshot'])
    except ValueError:
        return _result('TypedFrozenM2coSnapshotRequired')
    if query['memoryModel'] != _MAPPING:
        return _result('QualifiedStatus0356MappingRequired')
    generation = query['statusGeneration']
    if generation is None or snapshot['generations']['0356'] is None:
        return _result('Status0356GenerationMissing')
    if type(generation) is not str or not 0 < len(generation) <= 256:
        return _result('TypedStatusGenerationRequired')
    if generation != snapshot['generations']['0356']:
        return _result('Status0356GenerationMismatch')

    prefix = parser_step(snapshot)
    if not prefix['steps']:
        return _result(prefix['reason'], prefix=prefix)
    mode = _mode(snapshot)
    if not prefix['reads'] or not _exact_entry(snapshot, prefix, mode):
        return _result('ExactFrozenStatusHandoffNotEstablished', prefix=prefix)
    if mode == 1:
        return _result(prefix['reason'], prefix=prefix)
    state = {key: snapshot[key] for key in _STATE_KEYS}
    if (len(prefix['steps']) != 1 or len(prefix['reads']) != 1 or prefix['journal']
            or prefix['intermediateStates'] or prefix['state'] != state):
        return _result('ExactFrozenStatusHandoffNotEstablished', prefix=prefix)
    if mode is None:
        expected = ('IndeterminateBranch', 'UnknownBranchPredicate', 0x021F)
        if (prefix['status'], prefix['reason'], prefix['boundary']) != expected:
            return _result('ExactFrozenStatusHandoffNotEstablished', prefix=prefix)
        return _result(prefix['reason'], prefix=prefix)
    expected = ('OutsideVerifiedScope', 'UnmodeledBranch', 0x029D)
    if (prefix['status'], prefix['reason'], prefix['boundary']) != expected:
        return _result('ExactFrozenStatusHandoffNotEstablished', prefix=prefix)
    handoff = {'entryPc': 0x029D, 'branchPc': 0x021F, 'branchTaken': True, 'statusAddress': 0x0356,
               'statusGeneration': generation, 'memoryModel': _MAPPING, 'reseeded': False}
    entry = {'sourceId': _SOURCE_ID, 'entryPc': 0x029D, 'entryClass': 'DetachedEntry029D',
             'assumptions': {'noInterference': snapshot['assumptions']['noInterference']},
             'state': {**prefix['state'], 'registerGenerations': {}, 'registerKnownBits': {}}}
    corridor = _corridor(entry, 'ConfirmedEntryFrom021F')
    return _result(corridor['reason'], prefix=prefix, handoff=handoff, corridor=corridor)
