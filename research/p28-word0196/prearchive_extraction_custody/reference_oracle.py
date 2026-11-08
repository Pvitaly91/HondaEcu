"""Independent expectations for archival and physical-custody policy cases."""
from .documentary_reference import (
    expected_attachment, expected_chronology, expected_dependency, expected_identity, expected_lineage,
)

ACTUAL_UNKNOWN = {
    'actualOriginalPhysicalExtraction': None, 'actualEcuIdentity': None, 'actualMcuIdentity': None,
    'factoryOriginality': None, 'actualHardwareObservation': None, 'actualSiliconConfirmed': False,
    'executionAdmission': False, 'firmwareReady': False,
}

EXTRACTION_FAILURES = {
    'historical': 'OriginalExtractionRecordNotEstablished',
    'forged-primary': 'RefusedEvidencePromotion',
    'mirror': 'DerivativeCannotEstablishExtraction',
    'weak-hash': 'FullImageBindingUnestablished',
    'missing-bytes': 'FullImageBindingUnestablished',
    'different-bytes': 'ImageIdentityMismatch',
    'different-subject': 'SourceSubjectOrArtifactMismatch',
    'different-artifact': 'SourceSubjectOrArtifactMismatch',
    'missing-custody': 'ExtractionCustodyUnestablished',
    'unknown-method': 'ExtractionMethodUnestablished',
    'copy': 'NonPhysicalArtifactProduction',
    'repacked': 'NonPhysicalArtifactProduction',
}


def _read(q, fixture):
    name = fixture.removeprefix('read-')
    kind = EXTRACTION_FAILURES.get(name, 'FixtureExtractionChainOnly')
    accepted = kind == 'FixtureExtractionChainOnly'
    reviewed = name in ('historical', 'forged-primary')
    nonprimary = reviewed or name == 'mirror'
    weak = name in ('weak-hash', 'missing-bytes', 'different-bytes')
    missing = []
    if nonprimary:
        missing.append('OriginalExtractionRecord')
    if nonprimary or name == 'different-subject':
        missing.append('SourceSubjectBinding')
    if nonprimary or name == 'different-artifact':
        missing.append('ExtractionImageBinding')
    if weak:
        missing.append('FullImageIdentity')
    if nonprimary or name == 'missing-custody':
        missing.append('AuthenticatedExtractionCustody')
    if nonprimary or name in ('unknown-method', 'copy', 'repacked'):
        missing.append('PhysicalReadMethod')
    if not reviewed:
        missing.append('AuthenticNonFixtureExtractionRecord')
    missing.append('IndependentFactoryOriginalityEvidence')
    originality, proof = {
        'checksum-factory': ('Unknown', 'RefusedChecksumPromotion'),
        'fixture-factory': ('FactoryUnmodifiedFirmware', 'FixtureOnly'),
        'fixture-modified': ('ModifiedFirmware', 'FixtureOnly'),
        'fixture-originality-conflict': ('ConflictingClaims', 'FixtureConflict'),
    }.get(name, ('Unknown', 'Unestablished'))
    return dict(
        classification=kind, sourceId=q['sourceId'],
        sourceClass='ReviewedDocumentary' if reviewed else 'InventedPolicyFixture',
        recordType=q['recordType'], recordTypeSupported=name != 'forged-primary',
        conditionalExtractionEstablished=accepted, conditionalUnitId=q['unitId'] if accepted else None,
        conditionalArtifactId=q['artifactId'] if accepted else None,
        imageIdentity=q['imageIdentity'], identitySupportsFullLink=not weak, method=q['method'],
        conditionalFactoryOriginality=originality, originalityEvidenceStatus=proof,
        acceptedEdges=['ExtractionRecordToUnit', 'ExtractionRecordToImage', 'ImageToStudiedRom'] if accepted else [],
        rejectedEdges=[] if accepted else [kind], missingObligations=missing, **ACTUAL_UNKNOWN,
    )


LINK_EXPECTATIONS = {
    'fixture-complete': ('ConditionalFixtureLink',) * 3,
    'missing-mcu': ('ConditionalFixtureLink',) * 2,
    'missing-pcb': ('ConditionalFixtureLink', 'MissingPcbCustodyEdge'),
    'different-ecu': ('ConditionalFixtureLink', 'DifferentPhysicalSubject', 'MissingPcbCustodyEdge'),
    'third-party': ('ConditionalFixtureLink', 'SourceCannotBindStudiedUnit', 'MissingPcbCustodyEdge'),
    'duplicate': ('ConditionalFixtureLink', 'DependentDuplicate', 'ConditionalFixtureLink', 'ConditionalFixtureLink'),
    'mismatched-board-link': ('ConditionalFixtureLink', 'SourceClaimMismatch', 'MissingPcbCustodyEdge'),
    'real-extraction-absent': ('ExtractionRootUnestablished',) * 3,
}


def _donor(case):
    name, q = case['id'].removeprefix('donor-'), case['input']
    extraction = _read(q['extraction'], 'read-historical' if name == 'real-extraction-absent' else 'read-fixture-full')
    links = [{'index': i, 'sourceId': row['sourceId'], 'relation': row['relation'], 'status': status}
             for i, (row, status) in enumerate(zip(q['links'], LINK_EXPECTATIONS[name], strict=True))]
    joined = {row['relation'] for row in links if row['status'] == 'ConditionalFixtureLink'}
    roles = ('ECUToCaseLabel', 'ECUToPCB', 'PCBToMCUMarking')
    accepted = len(joined) == len(roles)
    obligations = ['SameUnitCaseLabel', 'SameUnitPcb', 'SameUnitMcuMarking']
    return dict(
        classification='FixtureSameUnitChainOnly' if accepted else 'SameUnitChainUnestablished',
        extraction=extraction, conditionalSameUnitChain=accepted,
        conditionalUnitId=extraction['conditionalUnitId'],
        conditionalCaseLabel='P28-A01' if roles[0] in joined else None,
        conditionalPcb='1720' if roles[1] in joined else None,
        conditionalMcuMarking='M66207-251' if roles[2] in joined else None, linkResults=links,
        acceptedEdges=extraction['acceptedEdges'] + [role for role in roles if role in joined],
        rejectedEdges=[{'index': row['index'], 'reason': row['status']} for row in links
                       if row['status'] != 'ConditionalFixtureLink'],
        missingObligations=extraction['missingObligations'] +
        [obligation for role, obligation in zip(roles, obligations) if role not in joined] + ['AuthenticSameUnitCustody'],
        **ACTUAL_UNKNOWN,
    )


def expected(case):
    operation = case['operation']
    if operation == 'extraction_session_provenance':
        return _read(case['input'], case['id'])
    if operation == 'same_unit_donor_binding':
        return _donor(case)
    return {
        'prearchive_source_lineage': expected_lineage,
        'historical_attachment_provenance': expected_attachment,
        'archive_copy_dependency': expected_dependency,
        'rom_artifact_identity': expected_identity,
        'historical_chronology_consistency': expected_chronology,
    }[operation](case['input'])
