"""Full-output records and immutable source bindings for M2dj."""
from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType

from mode_zero_parser_corridor.analysis import AUTHORITY as inherited, canonical

from .ci import BASE, ROOT

AUTHORITY = MappingProxyType(dict(inherited))
BOUNDARIES = ['STOP_BEFORE_UNQUALIFIED_SRBUF_READ_02AE',
              'STOP_BEFORE_UNQUALIFIED_INDIRECT_DATA_READ_02B7',
              'STOP_BEFORE_UNQUALIFIED_INDIRECT_DATA_READ_02C5',
              'STOP_BEFORE_UNREVIEWED_02B8', 'STOP_BEFORE_UNREVIEWED_02C6', 'STOP_BEFORE_STBUF_2995']
SOURCE_PATHS = frozenset({
    'research/p28-word0196/mode_zero_parser_corridor/contract.json',
    'research/p28-word0196/mode_zero_parser_corridor/source_inventory.json',
    'research/p28-word0196/detached_post_stbuf_0240_0241/fragment.py',
    'research/p28-word0196/payload_consumer_tail/state.py',
    'research/p28-word0196/alternate_parser_response_checksum/addressing.py',
    'docs/M2AW_NX8_200_TARGET_ABI_CONTRACT.md',
    'research/p28-word0196/detached_dp_parser_continuation/source_inventory.json',
})


def record(case, output):
    inputs = case['input'] if type(case['input']) is dict else {}
    state = output.get('state')
    registers = None if state is None else state['registers']
    steps = output.get('steps', [])
    return {
        'caseId': case['id'], 'operation': case['operation'], 'input': case['input'], 'output': output,
        'sourceScope': 'Detached02B0ThroughQualifiedIndirectRead',
        'sourceIdentities': ['M2djReviewedDetachedDp', 'OKI1991Primary', 'FrozenM2diSrbuf02AEBarrier'],
        'evidenceClass': 'ConditionalSoftwareEffect_NotRuntimeObservation',
        'entryClass': output.get('entryClass'), 'inputClass': inputs.get('inputClass'),
        'assumptions': inputs.get('assumptions'), 'registerState': registers, 'a16': output.get('a16'),
        'flags': None if registers is None else {key: registers.get(key) for key in ('cf', 'zf', 'hc', 'dd')},
        'scb': None if registers is None else registers.get('scb'),
        'pointerState': output.get('pointer'),
        'sourceEdges': [{'pc': step['pc'], 'next': step['next']} for step in steps],
        'branchDecisions': [{'pc': step['pc'], 'next': step['next'], 'taken': step['branchTaken'],
                             'evidence': step['predicateEvidence']}
                            for step in steps if step['kind'] == 'Branch'],
        'reads': output.get('reads', []), 'programDependencies': [],
        'orderedWrites': output.get('journal', []), 'intermediateStates': [step['state'] for step in steps],
        'memoryQualification': output.get('qualification', output if 'classification' in output else None),
        'unresolvedConstraints': output.get('unresolved', []),
        'stopBoundary': output.get('stopBoundary'), 'executionAuthority': dict(AUTHORITY),
    }


def operations():
    from .continuation import detached_02b0_02b2_transform
    from .data_access import indirect_data_address_qualification

    return {fn.__name__: fn for fn in (detached_02b0_02b2_transform, indirect_data_address_qualification)}


def validate_contract(contract):
    if type(contract) is not dict or set(contract) != {
        'schemaVersion', 'milestone', 'baseSha', 'authority', 'operations',
        'sources', 'boundaries', 'canonical', 'sourceReviewIdentity',
    }:
        raise ValueError('ClosedSourceContractRequired')
    if (type(contract['schemaVersion']) is not int or contract['schemaVersion'] != 1
            or contract['milestone'] != 'M2dj' or contract['baseSha'] != BASE
            or canonical(contract['authority']) != canonical(dict(AUTHORITY))
            or contract['boundaries'] != BOUNDARIES or contract['operations'] != sorted(operations())):
        raise ValueError('ExactSourceContractRequired')
    if type(contract['sources']) is not dict or set(contract['sources']) != SOURCE_PATHS:
        raise ValueError('ClosedSourceBindingInventoryRequired')
    for path, digest in contract['sources'].items():
        if sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise ValueError('FrozenSourceBindingChanged')
    review = contract['sourceReviewIdentity']
    if type(review) is not str or len(review) != 64 or any(ch not in '0123456789abcdef' for ch in review):
        raise ValueError('SourceReviewFingerprintRequired')
    return contract


def load_contract():
    return validate_contract(json.loads(Path(__file__).with_name('contract.json').read_bytes()))
