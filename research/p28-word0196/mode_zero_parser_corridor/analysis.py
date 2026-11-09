"""Closed sources and complete canonical records for M2di."""
from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType

from detached_epilogue_f8_pswh.analysis import AUTHORITY as inherited, canonical

from .ci import BASE, ROOT

AUTHORITY = MappingProxyType({**inherited, 'actualSrbufRead': None, 'actualReceivedByte': None,
                              'actualRxReady': None, 'actualRxReadyAcknowledgement': None,
                              'actualRxReadyReassertion': None})
BOUNDARIES = ['STOP_BEFORE_UNQUALIFIED_SRSTAT_RMW_029E', 'STOP_BEFORE_UNQUALIFIED_SRSTAT_RMW_02A5',
              'STOP_BEFORE_UNQUALIFIED_SRBUF_READ_02AE', 'STOP_BEFORE_STBUF_2995']
SOURCE_PATHS = frozenset({
    'research/p28-word0196/length_checksum_dataflow/contract.json',
    'research/p28-word0196/length_checksum_dataflow/dispatch.py',
    'research/p28-word0196/length_checksum_dataflow/state.py',
    'research/p28-word0196/length_checksum_dataflow/reference_oracle.py',
    'research/p28-word0196/conditional_flag_mode_shadow/state.py',
    'research/p28-word0196/detached_post_stbuf_0240_0241/fragment.py',
    'research/p28-word0196/payload_consumer_tail/state.py',
    'research/p28-word0196/detached_epilogue_f8_pswh/contract.json',
    'research/p28-word0196/mode_zero_parser_corridor/source_inventory.json',
})


def record(case, output):
    state = output['state']
    registers = None if state is None else state['registers']
    inputs = case['input'] if type(case['input']) is dict else {}
    typed = inputs.get('snapshot') if type(inputs.get('snapshot')) is dict else inputs
    prefix = output.get('prefix')
    branches = [{'phase': phase, 'pc': row['pc'], 'next': row['next'], 'taken': row['branchTaken'],
                 'evidence': row.get('predicateEvidence')}
                for phase, rows in (('FrozenM2co', prefix['steps'] if prefix is not None else []),
                                    ('M2di', output['steps']))
                for row in rows if row['kind'] == 'Branch']
    return {
        'caseId': case['id'], 'operation': case['operation'], 'input': case['input'], 'output': output,
        'sourceScope': 'ModeZero021F_029D_WithDetachedPostRbSuffixes',
        'sourceIdentities': ['M2diReviewedModeZero', 'OKI1991Primary', 'FrozenM2coJbr021F'],
        'evidenceClass': 'ConditionalSoftwareEffect_NotRuntimeObservation',
        'entryClass': output['entryClass'], 'inputClass': typed.get('inputClass', typed.get('entryClass')),
        'assumptions': typed.get('assumptions'),
        'sourceEdges': [{'pc': row['pc'], 'next': row['next']} for row in output['steps']],
        'branchDecisions': branches,
        'registerState': registers,
        'flags': None if registers is None else {key: registers.get(key) for key in ('cf', 'zf', 'hc', 'dd')},
        'knownBits': None if state is None else {'data': state['knownBits'], 'registers': state.get('registerKnownBits')},
        'generations': None if state is None else {'data': state['generations'], 'registers': state.get('registerGenerations')},
        'reads': output['reads'], 'orderedWrites': output['journal'],
        'intermediateStates': [row['state'] for row in output['steps']],
        'memoryQualification': {'conditionalModel': inputs.get('memoryModel'),
                                'physicalMappingEstablished': False},
        'peripheralObligation': output['peripheralObligation'], 'unresolvedConstraints': output['unresolved'],
        'stopBoundary': output['stopBoundary'], 'executionAuthority': dict(AUTHORITY),
    }


def operations():
    from .composition import mode_zero_parser_step
    from .corridor import mode_zero_corridor_029d, mode_zero_detached_suffix

    return {fn.__name__: fn for fn in (mode_zero_parser_step, mode_zero_corridor_029d,
                                      mode_zero_detached_suffix)}


def validate_contract(contract):
    if type(contract) is not dict or set(contract) != {
        'schemaVersion', 'milestone', 'baseSha', 'authority', 'operations',
        'sources', 'boundaries', 'canonical', 'sourceReviewIdentity',
    }:
        raise ValueError('ClosedSourceContractRequired')
    if (type(contract['schemaVersion']) is not int or contract['schemaVersion'] != 1
            or contract['milestone'] != 'M2di' or contract['baseSha'] != BASE
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
