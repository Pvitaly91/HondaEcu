"""Closed M2dd canonical records and immutable research authority."""
from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType

from target_mcu_c8_applicability.analysis import AUTHORITY as prior_authority, canonical

from .ci import BASE, ROOT

AUTHORITY = MappingProxyType({**prior_authority, 'actualEcuIdentity': None, 'exactC8Rule': None})
SOURCE_PATHS = frozenset({
    'research/p28-word0196/ecu_rom_provenance/contract.json',
    'research/p28-word0196/ecu_rom_provenance/acquisition_audit.json',
    'research/p28-word0196/target_mcu_c8_applicability/contract.json',
    'docs/M2CM_ECU_ROM_PROVENANCE_BRIDGE.md',
    'docs/M2DC_TARGET_MCU_C8_APPLICABILITY.md',
    'docs/M1A_REAL_ROM_FINDINGS.md',
})


def record(case, output):
    query = case['input']
    extraction = query.get('extraction', query)
    ids = list(query.get('sourceIds', []))
    if extraction.get('sourceId'):
        ids.append(extraction['sourceId'])
    ids.extend(link['sourceId'] for link in query.get('links', []))
    ids.extend(event['source'] for event in output.get('events', []))
    invented = query.get('mode') == 'Invented' or any(item.startswith('Fixture') for item in ids)
    return {
        'caseId': case['id'], 'operation': case['operation'], 'sourceIdentities': sorted(set(ids)),
        'evidenceClass': 'InventedPolicyControl' if invented else 'BoundedDocumentaryEvaluation',
        'digitalArtifactIdentity': output.get('identityClass', extraction.get('imageIdentity')),
        'chronology': output.get('events', output.get('recordedUpload')),
        'physicalSubjectIdentity': None,
        'sourceDependence': output.get('knownOriginGroups', []),
        'archiveMetadata': output.get('archiveHistory', []),
        'extractionRecord': output.get('actualOriginalPhysicalExtraction'),
        'donorBindingStatus': 'SameUnitUnbound',
        'acceptedEdges': output.get('acceptedEdges', []), 'rejectedEdges': output.get('rejectedEdges', []),
        'missingObligations': output.get('missingObligations', []),
        'input': query, 'output': output, 'executionAuthority': dict(AUTHORITY),
    }


def operations():
    from .documentary import (archive_copy_dependency, historical_attachment_provenance,
                              historical_chronology_consistency, prearchive_source_lineage,
                              rom_artifact_identity)
    from .extraction import extraction_session_provenance, same_unit_donor_binding

    return {function.__name__: function for function in (
        prearchive_source_lineage, historical_attachment_provenance, archive_copy_dependency,
        rom_artifact_identity, historical_chronology_consistency,
        extraction_session_provenance, same_unit_donor_binding,
    )}


def validate_contract(contract):
    if type(contract) is not dict or set(contract) != {
        'schemaVersion', 'milestone', 'baseSha', 'authority', 'operations',
        'sources', 'boundaries', 'canonical', 'sourceReviewIdentity',
    }:
        raise ValueError('ClosedSourceContractRequired')
    if (type(contract['schemaVersion']) is not int or contract['schemaVersion'] != 1
            or contract['milestone'] != 'M2dd' or contract['baseSha'] != BASE
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
