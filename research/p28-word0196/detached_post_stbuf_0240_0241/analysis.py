"""Source bindings and full records for detached software results."""
from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType

from alternate_parser_response_checksum.analysis import AUTHORITY as prior_authority, canonical

from .ci import BASE, ROOT

AUTHORITY = MappingProxyType(dict(prior_authority))
BOUNDARIES = ['STOP_BEFORE_STBUF_023E', 'STOP_BEFORE_EPILOGUE_0244', 'STOP_BEFORE_STBUF_2995']
SOURCE_PATHS = frozenset({
    'research/p28-word0196/alternate_parser_response_checksum/contract.json',
    'research/p28-word0196/alternate_parser_response_checksum/source_inventory.json',
    'research/p28-word0196/alternate_parser_response_checksum/path.py',
    'research/p28-word0196/alternate_parser_response_checksum/composition.py',
    'research/p28-word0196/alternate_parser_response_checksum/reference_oracle.py',
    'research/p28-word0196/conditional_flag_mode_shadow/state.py',
    'research/p28-word0196/detached_post_stbuf_0240_0241/source_inventory.json',
    'docs/M2AW_NX8_200_TARGET_ABI_CONTRACT.md',
})


def record(case, output):
    state = output.get('state')
    registers = state['registers'] if state is not None else None
    return {
        'caseId': case['id'], 'operation': case['operation'], 'input': case['input'], 'output': output,
        'sourceScope': 'Detached0240_0241_StopBefore0244',
        'sourceIdentities': ['M2dgReviewed0240_0241', 'OKI1991Primary', 'FrozenM2df'],
        'evidenceClass': 'ConditionalSoftwareEffect_NotRuntimeObservation',
        'sourceEdges': [{'pc': step['pc'], 'next': step['next']} for step in output['steps']],
        'registerState': registers,
        'flags': {key: registers.get(key) for key in ('cf', 'zf', 'hc', 'dd', 'mie', 'otherPsw')}
        if registers is not None else None,
        'dataReads': output['reads'], 'programDependencies': [], 'orderedWrites': output['journal'],
        'writerGenerations': [row['afterGeneration'] for row in output['journal']],
        'intermediateStates': [step['state'] for step in output['steps']],
        'unresolvedConstraints': output['unresolved'], 'stopBoundary': output['stopBoundary'],
        'executionAuthority': dict(AUTHORITY),
    }


def operations():
    from .composition import epilogue_0244_ingress_comparison, m2df_candidate_to_detached_0240
    from .fragment import detached_0240_0241_transform

    return {function.__name__: function for function in (
        detached_0240_0241_transform, m2df_candidate_to_detached_0240, epilogue_0244_ingress_comparison,
    )}


def validate_contract(contract):
    if type(contract) is not dict or set(contract) != {
        'schemaVersion', 'milestone', 'baseSha', 'authority', 'operations',
        'sources', 'boundaries', 'canonical', 'sourceReviewIdentity',
    }:
        raise ValueError('ClosedSourceContractRequired')
    if (type(contract['schemaVersion']) is not int or contract['schemaVersion'] != 1
            or contract['milestone'] != 'M2dg' or contract['baseSha'] != BASE
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
