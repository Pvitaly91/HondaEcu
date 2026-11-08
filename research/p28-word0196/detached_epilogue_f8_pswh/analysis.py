"""Complete canonical records and closed source bindings for M2dh."""
from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType

from detached_post_stbuf_0240_0241.analysis import AUTHORITY as prior_authority, canonical

from .ci import BASE, ROOT

AUTHORITY = MappingProxyType(dict(prior_authority))
BOUNDARIES = ['STOP_BEFORE_STBUF_023E', 'STOP_BEFORE_EPILOGUE_0244', 'STOP_BEFORE_IE_WRITE_0249',
              'STOP_BEFORE_UNQUALIFIED_0244_OR_0246', 'STOP_BEFORE_STBUF_2995']
SOURCE_PATHS = frozenset({
    'research/p28-word0196/alternate_parser_response_checksum/contract.json',
    'research/p28-word0196/alternate_parser_response_checksum/path.py',
    'research/p28-word0196/alternate_parser_response_checksum/reference_oracle.py',
    'research/p28-word0196/detached_post_stbuf_0240_0241/contract.json',
    'research/p28-word0196/detached_post_stbuf_0240_0241/fragment.py',
    'research/p28-word0196/detached_post_stbuf_0240_0241/reference_oracle.py',
    'research/p28-word0196/payload_consumer_tail/state.py',
    'research/p28-word0196/conditional_flag_mode_shadow/state.py',
    'research/p28-word0196/indexed_suffix_ie_provenance/provenance.py',
    'research/p28-word0196/detached_epilogue_f8_pswh/source_inventory.json',
})


def record(case, output):
    state = output.get('state')
    registers = state['registers'] if state is not None else {}
    al, ah = registers.get('al'), registers.get('ah')
    return {
        'caseId': case['id'], 'operation': case['operation'], 'input': case['input'], 'output': output,
        'sourceScope': 'Detached0244_0246_StopBefore0249',
        'sourceIdentities': ['M2dhReviewed0244_0246', 'OKI1991Primary', 'Msm66201_207FamilyPswhWarning',
                             'FrozenM2dfM2dg', 'FrozenM2cxShadowCandidates'],
        'evidenceClass': 'ConditionalSoftwareEffect_NotRuntimeObservation',
        'entryClass': output['entryClass'], 'sourceHistory': output.get('sourceHistory'),
        'sourceEdges': [{'pc': row['pc'], 'next': row['next']} for row in output['steps']],
        'registerState': registers if state is not None else None,
        'accumulatorWord': None if None in (al, ah) else al | ah << 8,
        'knownBits': state['registerKnownBits'] if state is not None else None,
        'flags': {name: registers.get(name) for name in ('cf', 'zf', 'hc', 'dd', 'mie', 'otherPsw')}
        if state is not None else None,
        'pswh': output.get('pswh'), 'shadowProof': output.get('shadowProof'),
        'reads': output['reads'], 'orderedWrites': output['journal'],
        'intermediateStates': [row['state'] for row in output['steps']],
        'unresolvedConstraints': output['unresolved'], 'prospectiveIe': output.get('prospectiveIe'),
        'stopBoundary': output['stopBoundary'], 'executionAuthority': dict(AUTHORITY),
    }


def operations():
    from .epilogue import detached_epilogue_0244_0246
    from .ingress import compare_epilogue_ingresses, epilogue_ingress_adapter

    return {fn.__name__: fn for fn in (detached_epilogue_0244_0246, epilogue_ingress_adapter,
                                      compare_epilogue_ingresses)}


def validate_contract(contract):
    if type(contract) is not dict or set(contract) != {
        'schemaVersion', 'milestone', 'baseSha', 'authority', 'operations',
        'sources', 'boundaries', 'canonical', 'sourceReviewIdentity',
    }:
        raise ValueError('ClosedSourceContractRequired')
    if (type(contract['schemaVersion']) is not int or contract['schemaVersion'] != 1
            or contract['milestone'] != 'M2dh' or contract['baseSha'] != BASE
            or canonical(contract['authority']) != canonical(dict(AUTHORITY))
            or contract['boundaries'] != BOUNDARIES or contract['operations'] != sorted(operations())):
        raise ValueError('ExactSourceContractRequired')
    if type(contract['sources']) is not dict or set(contract['sources']) != SOURCE_PATHS:
        raise ValueError('ClosedSourceBindingInventoryRequired')
    for path, digest in contract['sources'].items():
        if sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise ValueError('FrozenSourceBindingChanged')
    review = contract['sourceReviewIdentity']
    if (type(review) is not str or len(review) != 64
            or any(ch not in '0123456789abcdef' for ch in review)):
        raise ValueError('SourceReviewFingerprintRequired')
    return contract


def load_contract():
    return validate_contract(json.loads(Path(__file__).with_name('contract.json').read_bytes()))
