"""Full bounded software records with immutable execution restrictions."""
from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType

from original_attachment_evidence.analysis import AUTHORITY as prior_authority, canonical

from .ci import BASE, ROOT

AUTHORITY = MappingProxyType({**prior_authority, 'actualStbufWrite': None, 'actualTxReady': None,
                              'actualTxCompletion': None})
BOUNDARIES = ['STOP_BEFORE_STBUF_023E', 'STOP_BEFORE_EPILOGUE_0244', 'STOP_BEFORE_STBUF_2995']
SOURCE_PATHS = frozenset({
    'research/p28-word0196/length_checksum_dataflow/contract.json',
    'research/p28-word0196/length_checksum_dataflow/dispatch.py',
    'research/p28-word0196/conditional_flag_mode_shadow/state.py',
    'research/p28-word0196/original_attachment_evidence/contract.json',
    'research/p28-word0196/alternate_parser_response_checksum/source_inventory.json',
    'docs/M2AW_NX8_200_TARGET_ABI_CONTRACT.md',
})


def record(case, output):
    selected = output.get('alternate') or output.get('prefix') or output
    state = selected.get('state')
    registers = state.get('registers') if state else None
    prefix = output.get('prefix')
    steps = selected.get('steps', [])
    reads = selected.get('reads', [])
    if output.get('alternate') is not None:
        steps = prefix['steps'] + steps
        reads = prefix['reads'] + reads
    journal = output.get('orderedWrites', selected.get('journal', []))
    return {
        'caseId': case['id'], 'operation': case['operation'],
        'sourceScope': output.get('sourceScope', case['operation']),
        'sourceIdentities': ['M2dfReviewedInventory', 'M2coFrozenStatusPrefix', 'OKI1991Primary'],
        'evidenceClass': 'ConditionalSoftwareEffect_NotRuntimeObservation',
        'input': case['input'], 'output': output, 'sourceBranchDecisions': [
            row for row in steps if row.get('kind') == 'Branch'],
        'registerState': registers, 'flags': {name: registers.get(name) for name in ('cf', 'zf', 'hc', 'dd')}
        if registers else None,
        'dataReads': [row for row in reads if row.get('space') == 'DATA'],
        'programDependencies': selected.get('programDependencies', [
            row for row in reads if row.get('space') == 'PROGRAM']),
        'orderedWrites': journal, 'writerGenerations': [
            row.get('event', row).get('afterGeneration') for row in journal],
        'responseCandidate': selected.get('responseCandidate'),
        'checksumState': selected.get('checksumState', output.get('result')),
        'intermediateStates': selected.get('intermediateStates', []),
        'unresolvedConstraints': selected.get('unresolvedConstraints', []),
        'stopBoundary': selected.get('stopBoundary') or output.get('boundary'), 'executionAuthority': dict(AUTHORITY),
    }


def operations():
    from .addressing import alternate_memory_read_obligations, program_to_data_address_qualification
    from .checksum import alternate_checksum_accumulation
    from .composition import alternate_parser_step
    from .path import alternate_auxiliary_024c_0253, alternate_response_selector

    return {function.__name__: function for function in (
        alternate_response_selector, alternate_auxiliary_024c_0253, alternate_parser_step,
        program_to_data_address_qualification, alternate_memory_read_obligations,
        alternate_checksum_accumulation,
    )}


def validate_contract(contract):
    if type(contract) is not dict or set(contract) != {
        'schemaVersion', 'milestone', 'baseSha', 'authority', 'operations',
        'sources', 'boundaries', 'canonical', 'sourceReviewIdentity',
    }:
        raise ValueError('ClosedSourceContractRequired')
    if (type(contract['schemaVersion']) is not int or contract['schemaVersion'] != 1
            or contract['milestone'] != 'M2df' or contract['baseSha'] != BASE
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
