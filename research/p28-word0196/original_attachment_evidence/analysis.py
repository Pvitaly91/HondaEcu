"""Complete M2de canonical records and frozen authority."""
from hashlib import sha256
import json
from pathlib import Path

from prearchive_extraction_custody.analysis import AUTHORITY, canonical

from .ci import BASE, ROOT

SOURCE_PATHS = frozenset({
    'research/p28-word0196/prearchive_extraction_custody/contract.json',
    'research/p28-word0196/prearchive_extraction_custody/documentary.py',
    'research/p28-word0196/prearchive_extraction_custody/extraction.py',
    'research/p28-word0196/target_mcu_c8_applicability/contract.json',
    'research/p28-word0196/ecu_rom_provenance/acquisition_audit.json',
    'research/p28-word0196/original_attachment_evidence/source_scope.json',
    'docs/M2DD_PREARCHIVE_EXTRACTION_CUSTODY.md',
})


def record(case, output):
    query = case['input']
    selected = query.get('digital', query)
    sources = list(selected.get('sourceIds', []))
    if query.get('sourceId'):
        sources.append(query['sourceId'])
    if 'physical' in query:
        sources.append(query['physical']['extraction']['sourceId'])
        sources.extend(row['sourceId'] for row in query['physical']['links'])
    digital = output.get('digitalAxis', output)
    return {
        'caseId': case['id'], 'operation': case['operation'], 'sourceIdentities': sorted(set(sources)),
        'evidenceClass': 'InventedPolicyControl' if any(key.startswith('Fixture') for key in sources)
        else 'BoundedDocumentaryEvaluation',
        'attachmentIdentity': digital.get('actualOriginalPayloadBound', digital.get('actualAttachmentToBlobBinding')),
        'digestProvenance': output.get('digestProvenance'),
        'digitalJoinStatus': digital.get('digitalJoinStatus'),
        'extractionSession': output['physicalExtractionRecord'],
        'donorSubject': output['actualEcuIdentity'],
        'sameUnitRelation': 'SameUnitUnbound',
        'chronology': output.get('chronology'),
        'dependencyLineage': digital.get('dependencyLineage', []),
        'acceptedEdges': output.get('acceptedEdges', []), 'rejectedEdges': output.get('rejectedEdges', []),
        'unresolvedConstraints': output.get('unresolvedConstraints', []),
        'input': query, 'output': output, 'executionAuthority': dict(AUTHORITY),
    }


def operations():
    from .identity import (attachment_to_rom_blob_proof, documentary_evidence_status,
                           historical_attachment_payload_identity, historical_digest_authenticity)

    return {function.__name__: function for function in (
        historical_attachment_payload_identity, historical_digest_authenticity,
        attachment_to_rom_blob_proof, documentary_evidence_status,
    )}


def validate_contract(contract):
    if type(contract) is not dict or set(contract) != {
        'schemaVersion', 'milestone', 'baseSha', 'authority', 'operations',
        'sources', 'boundaries', 'canonical', 'sourceReviewIdentity',
    }:
        raise ValueError('ClosedSourceContractRequired')
    if (type(contract['schemaVersion']) is not int or contract['schemaVersion'] != 1
            or contract['milestone'] != 'M2de' or contract['baseSha'] != BASE
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
