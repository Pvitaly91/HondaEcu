"""Independent case expectations over the reviewed redacted source inventory."""
import json
from pathlib import Path

from prearchive_extraction_custody.documentary_reference import expected_chronology
from prearchive_extraction_custody.reference_oracle import expected as expected_prearchive

SOURCES = json.loads(Path(__file__).with_name('source_scope.json').read_bytes())
PHYSICAL_UNKNOWN = {
    'actualEcuIdentity': None, 'actualMcuIdentity': None, 'physicalExtractionRecord': None,
    'factoryOriginality': None, 'exactC8Rule': None,
}
PAYLOAD_STATUS = {
    'KnownLaterBlob': 'ByteIdenticalDerivative',
    'HistoricalCaptureJune2004': 'AuthenticatedOriginalAttachmentBytes',
    'HistoricalCaptureSeptember2004': 'AuthenticatedOriginalAttachmentBytes',
    'FixtureOriginalExact': 'AuthenticatedOriginalAttachmentBytes',
    'FixtureConflictBytes': 'ConflictingAttachmentIdentity',
    'FixtureWrongParent': 'UnqualifiedPayloadIdentity',
    'FixtureMirrorEqual': 'ByteIdenticalDerivative',
    'FixtureMirrorDuplicate': 'ByteIdenticalDerivative',
    'FixtureTruncated': 'PartialIdentityEvidence',
    'FixtureTransformed': 'UnqualifiedPayloadIdentity',
    'FixtureUnavailable': 'UnavailableAttachmentPayload',
}
DIGEST_STATUS = {
    'KnownLaterDigest': 'LaterComputedDigest',
    'ArchiveCaptureDigest': 'ArchiveCaptureDigest',
    'FixtureOriginalDigest': 'AuthenticatedOriginalAttachmentDigest',
    'FixtureConflictDigest': 'ConflictingAttachmentIdentity',
    'FixtureLaterDigest': 'LaterComputedDigest',
    'FixtureCopiedDigest': 'CopiedDigestClaim',
    'FixtureUnknownDigest': 'UnknownDigestOrigin',
    'FixturePartialDigest': 'PartialIdentityEvidence',
    'FixtureLegacyDigest': 'PartialIdentityEvidence',
    'FixtureUnboundDigest': 'HistoricalDigestBindingUnestablished',
}

EXACT, DIGEST = 'ExactHistoricalAttachmentToBlobBinding', 'DigestQualifiedAttachmentToBlobBinding'
DERIVATIVE, UNBOUND = 'OnlyLaterDerivativeEstablished', 'HistoricalAttachmentUnbound'
CONFLICT = 'AttachmentIdentityConflict'
JOIN_EXPECTATIONS = {
    'reviewed-sources': DERIVATIVE, 'unavailable-fixture': UNBOUND, 'conditional-exact': EXACT,
    'restored-captures': EXACT, 'archive-digest-alone': UNBOUND,
    'conditional-digest': DIGEST, 'qualified-both': EXACT, 'conflict': CONFLICT, 'later-only': DERIVATIVE,
    'wrong-parent': UNBOUND, 'weak': UNBOUND, 'force-donor': DERIVATIVE, 'force-factory': EXACT,
    'force-c8': DIGEST, 'force-execution': EXACT,
}


def _payload(source):
    return PAYLOAD_STATUS.get(source, 'HistoricalMetadataOnly')


def _digest(source):
    return DIGEST_STATUS.get(source, 'DigestNotAvailable')


def _evidence(source, operation):
    data = SOURCES[source]
    common = dict(sourceId=source, evidenceClass=data['scope'], sourceSubject=data['subject'],
                  identityComparison=data['comparison'], sourceIndependence=data['independentOfTarget'],
                  **PHYSICAL_UNKNOWN)
    if operation == 'historical_attachment_payload_identity':
        return dict(common, status=_payload(source), completeContent=data['complete'],
                    archiveCaptureUtc=data['captureUtc'],
                    actualOriginalPayloadBound=source in ('HistoricalCaptureJune2004', 'HistoricalCaptureSeptember2004'))
    return dict(common, status=_digest(source), digestProvenance=data['digestOrigin'], algorithm=data['algorithm'],
                completeDigest=data['complete'] if source in DIGEST_STATUS else None, actualOriginalDigestBound=False)


def _join(q, verdict):
    selected = sorted(q['sourceIds'])
    blocked = q['claim'] != 'Inspect'
    restored = any(source in ('HistoricalCaptureJune2004', 'HistoricalCaptureSeptember2004') for source in selected)
    actual_binding = EXACT if restored and not blocked else None
    fixture_binding = verdict if not restored and not blocked and verdict in (EXACT, DIGEST) else None
    evidence = [
        dict(sourceId=source, payloadClass=_payload(source), digestClass=_digest(source),
             sourceSubject=SOURCES[source]['subject'], origin=SOURCES[source]['origin'],
             archiveCaptureUtc=SOURCES[source]['captureUtc'])
        for source in selected
    ]
    lineages = sorted({item['origin'] for item in evidence if item['origin'] is not None})
    return dict(
        status='RefusedEvidencePromotion' if blocked else verdict, digitalJoinStatus=verdict,
        actualAttachmentToBlobBinding=actual_binding, conditionalFixtureBinding=fixture_binding, sourceEvidence=evidence,
        dependencyLineage=[dict(origin=origin, sourceIds=[item['sourceId'] for item in evidence if item['origin'] == origin])
                           for origin in lineages],
        unboundSourceOrigins=[item['sourceId'] for item in evidence if item['origin'] is None],
        independentExtractionWitnessCount=0,
        acceptedEdges=['HistoricalAttachmentToPinnedBlob'] if actual_binding else
        ['InventedAttachmentToInventedBlob'] if fixture_binding else [],
        rejectedEdges=[q['claim']] if blocked else [],
        unresolvedConstraints=([] if actual_binding else ['AuthenticatedHistoricalAttachmentIdentity']) +
        ['ContemporaneousExtractionCustody', 'SameUnitDonorBinding', 'IndependentFactoryOriginality',
         'ApplicableC8RevisionEvidence'],
        **PHYSICAL_UNKNOWN,
    )


STATUS_CASES = {
    'reviewed': (EXACT, 'real-extraction-absent'),
    'digital-fixture-missing-donor': (EXACT, 'real-extraction-absent'),
    'digital-fixture-complete-donor': (DIGEST, 'fixture-complete'),
    'digital-fixture-missing-mcu': (EXACT, 'missing-mcu'),
    'digital-fixture-wrong-donor': (EXACT, 'different-ecu'),
    'digital-fixture-conflict': (CONFLICT, 'fixture-complete'),
}


def _status(case):
    q = case['input']
    verdict, donor = STATUS_CASES[case['id'].removeprefix('status-')]
    digital = _join(q['digital'], verdict)
    physical = expected_prearchive(dict(id='donor-' + donor, operation='same_unit_donor_binding', input=q['physical']))
    events = expected_chronology(dict(mode='Recorded', events=[], claim='Inspect'))['events']
    restored = case['id'] == 'status-reviewed'
    return dict(
        status='ORIGINAL_ATTACHMENT_BYTE_IDENTITY_ESTABLISHED' if restored else
        'ConditionalFixtureConflict' if verdict == CONFLICT else 'EXTRACTION_EVIDENCE_DEPENDENCY_CONFIRMED',
        digitalAxis=digital, physicalAxis=physical,
        chronology=dict(recordedEvents=events, observedPhysicalExtractionTime=None,
                        originalPublicationTime=None, dateOrderConfersCustody=False,
                        verifiedAttachmentCaptureTimes=['2004-06-17T08:30:20Z', '2004-09-01T20:57:27Z'] if restored else []),
        minimumNextEvidence=dict(digital=None if restored else 'AuthenticHistoricalAttachmentBytesOrOriginalCompleteDigest',
                                 physical='ContemporaneousReadRecordBindingFullImageToStableDonor'),
        acceptedEdges=digital['acceptedEdges'] if restored else [],
        conditionalFixtureEdges=([] if restored else digital['acceptedEdges']) + physical['acceptedEdges'],
        rejectedEdges=digital['rejectedEdges'] + physical['rejectedEdges'],
        unresolvedConstraints=digital['unresolvedConstraints'], **PHYSICAL_UNKNOWN,
    )


def expected(case):
    operation = case['operation']
    if operation == 'attachment_to_rom_blob_proof':
        return _join(case['input'], JOIN_EXPECTATIONS[case['id'].removeprefix('join-')])
    if operation == 'documentary_evidence_status':
        return _status(case)
    return _evidence(case['input']['sourceId'], operation)
