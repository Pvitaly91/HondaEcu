"""Full public-safe documentary records and an immutable authority boundary."""
from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType

from helper_ingress_frame_handoff.analysis import AUTHORITY as prior_authority, canonical

from .ci import BASE, ROOT

AUTHORITY = MappingProxyType({
    **prior_authority,
    'actualMcuIdentity': None,
    'actualSiliconConfirmed': False,
})

SOURCE_PATHS = frozenset({
    'research/p28-word0196/ecu_rom_provenance/contract.json',
    'research/p28-word0196/ecu_rom_provenance/acquisition_audit.json',
    'research/p28-word0196/ecu_rom_provenance/compatibility.py',
    'research/p28-word0196/helper_ingress_frame_handoff/contract.json',
    'docs/M2AM_C8_EQUALITY_EVIDENCE.md',
    'docs/M2CL_ACTUAL_ECU_SILICON_APPLICABILITY.md',
})


def record(case, output):
    query = case['input']
    custody = query.get('custody', query)
    isa = query.get('isa', query)
    ids = sorted(set(custody.get('sourceIds', []) + isa.get('sourceIds', [])))
    if query.get('sourceId'):
        ids = sorted(set([*ids, query['sourceId']]))
    if query.get('programPremise'):
        ids.append('M2cmFrozenCompatibility')
    fixture = any(source.startswith('Fixture') for source in ids)
    return {
        'caseId': case['id'],
        'operation': case['operation'],
        'sourceIdentities': ids,
        'evidenceClass': 'InventedPolicyControl' if fixture else 'BoundedDocumentaryEvaluation',
        'sourceApplicability': 'CandidateAndProjectScopeOnly',
        'physicalSubjectIdentity': None,
        'romProvenance': output.get('hardwareAxis', output).get('projectArchiveAcquisition'),
        'ecuCandidate': query.get('ecuCandidate'),
        'pcbCandidate': query.get('pcbCandidate'),
        'mcuCandidate': query.get('mcuCandidate', isa.get('catalogPart', query.get('catalogMcuCandidate'))),
        'literalMarking': query.get('literalMarking'),
        'customerCode': isa.get('customerCode'),
        'siliconRevision': isa.get('siliconRevision'),
        'memoryAssumptions': {'program': query.get('programPremise'), 'data': query.get('dataPremise')},
        'manufacturerDocumentIdentity': [source for source in ids if source.startswith('Oki')],
        'c8Evidence': {'requestedOpcode': isa.get('opcode'), 'targetRule': None},
        'acceptedEdges': output.get('acceptedEdges', []),
        'rejectedEdges': output.get('rejectedEdges', []),
        'unresolvedConstraints': output.get('unresolvedConstraints', output.get('missingProof', [])),
        'input': query,
        'output': output,
        'executionAuthority': dict(AUTHORITY),
    }


def operations():
    from .candidates import mcu_candidate_attribution, memory_architecture_compatibility
    from .graph import target_c8_applicability
    from .isa import c8_revision_evidence, customer_code_applicability
    from .provenance import rom_to_hardware_provenance

    return {function.__name__: function for function in (
        rom_to_hardware_provenance, mcu_candidate_attribution, memory_architecture_compatibility,
        customer_code_applicability, c8_revision_evidence, target_c8_applicability,
    )}


def validate_contract(contract):
    required = {'schemaVersion', 'milestone', 'baseSha', 'authority', 'operations',
                'sources', 'boundaries', 'canonical', 'sourceReviewIdentity'}
    if type(contract) is not dict or set(contract) != required:
        raise ValueError('ClosedSourceContractRequired')
    if (type(contract['schemaVersion']) is not int or contract['schemaVersion'] != 1
            or contract['milestone'] != 'M2dc' or contract['baseSha'] != BASE
            or canonical(contract['authority']) != canonical(dict(AUTHORITY))
            or contract['boundaries'] != ['STOP_BEFORE_IE_WRITE_5CB9', 'STOP_BEFORE_IE_WRITE_5CCB',
                                         'STOP_BEFORE_BRK_5CF8', 'STOP_BEFORE_STBUF_2995']
            or contract['operations'] != sorted(operations())):
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
