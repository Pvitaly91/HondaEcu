"""Qualify original payload and digest evidence without exposing its bytes."""
import json
from pathlib import Path
import re
from types import MappingProxyType

from enclosing_caller_return.state import need, shape

SOURCE_SCOPE = Path(__file__).with_name('source_scope.json')
SOURCES = MappingProxyType({
    key: MappingProxyType(value) for key, value in json.loads(SOURCE_SCOPE.read_bytes()).items()
})
FIELDS = ('scope', 'evidence', 'subject', 'origin', 'historicalBinding', 'complete',
          'comparison', 'digestOrigin', 'algorithm', 'untransformed', 'independentOfTarget', 'captureUtc')
NO_PHYSICAL_INFERENCE = {
    'actualEcuIdentity': None, 'actualMcuIdentity': None, 'physicalExtractionRecord': None,
    'factoryOriginality': None, 'exactC8Rule': None,
}


def _source(source_id):
    need(type(source_id) is str and source_id in SOURCES, 'ReviewedSourceIdentityRequired')
    row = dict(SOURCES[source_id])
    shape(row, FIELDS, 'ClosedReviewedSourceScopeRequired')
    need(row['scope'] in ('ReviewedDocumentary', 'InventedPolicyControl')
         and row['evidence'] in ('Payload', 'Digest', 'Metadata', 'Unavailable', 'Partial')
         and row['subject'] in ('HistoricalAttachment', 'LaterArchiveBlob', 'OtherAttachment', None)
         and row['origin'] in ('HistoricalPublication', 'ArchiveBlobLineage', 'FixtureOtherOrigin', None)
         and row['comparison'] in ('Equal', 'Different', None)
         and row['digestOrigin'] in ('OriginalAttachmentDigest', 'LaterComputedDigest',
                                     'CopiedDigestClaim', 'UnknownDigestOrigin', 'ArchiveCaptureDigest', None)
         and row['algorithm'] in ('SHA256', 'SHA512', 'Legacy', None)
         and (row['captureUtc'] is None or type(row['captureUtc']) is str and re.fullmatch(
             r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z', row['captureUtc']))
         and all(row[key] is None or type(row[key]) is bool for key in (
             'historicalBinding', 'complete', 'untransformed', 'independentOfTarget')),
         'TypedReviewedSourceScopeRequired')
    return row


def _historically_bound(row):
    return (row['subject'] == 'HistoricalAttachment' and row['historicalBinding'] is True
            and row['independentOfTarget'] is True and row['untransformed'] is True)


def _payload_class(row):
    if row['evidence'] == 'Unavailable':
        return 'UnavailableAttachmentPayload'
    if row['evidence'] == 'Partial':
        return 'PartialIdentityEvidence'
    if row['evidence'] != 'Payload':
        return 'HistoricalMetadataOnly'
    if row['complete'] is not True:
        return 'PartialIdentityEvidence'
    if _historically_bound(row) and row['comparison'] == 'Equal':
        return 'AuthenticatedOriginalAttachmentBytes'
    if _historically_bound(row) and row['comparison'] == 'Different':
        return 'ConflictingAttachmentIdentity'
    if row['comparison'] == 'Equal' and row['subject'] == 'LaterArchiveBlob':
        return 'ByteIdenticalDerivative'
    return 'UnqualifiedPayloadIdentity'


def _digest_class(row):
    if row['evidence'] != 'Digest':
        return 'DigestNotAvailable'
    if row['digestOrigin'] != 'OriginalAttachmentDigest':
        return row['digestOrigin'] or 'UnknownDigestOrigin'
    if row['complete'] is not True or row['algorithm'] not in ('SHA256', 'SHA512'):
        return 'PartialIdentityEvidence'
    if not _historically_bound(row) or row['comparison'] is None:
        return 'HistoricalDigestBindingUnestablished'
    return ('AuthenticatedOriginalAttachmentDigest' if row['comparison'] == 'Equal'
            else 'ConflictingAttachmentIdentity')


def historical_attachment_payload_identity(query):
    """Check custody, identity, and completeness of a selected payload record."""
    shape(query, ('sourceId',), 'ClosedAttachmentPayloadQueryRequired')
    row = _source(query['sourceId'])
    classification = _payload_class(row)
    return {
        'status': classification, 'sourceId': query['sourceId'], 'evidenceClass': row['scope'],
        'sourceSubject': row['subject'], 'identityComparison': row['comparison'],
        'completeContent': row['complete'], 'sourceIndependence': row['independentOfTarget'],
        'archiveCaptureUtc': row['captureUtc'],
        'actualOriginalPayloadBound': (row['scope'] == 'ReviewedDocumentary' and
                                      classification == 'AuthenticatedOriginalAttachmentBytes'),
        **NO_PHYSICAL_INFERENCE,
    }


def historical_digest_authenticity(query):
    """Distinguish an original full digest from subsequent blob computations."""
    shape(query, ('sourceId',), 'ClosedAttachmentDigestQueryRequired')
    row = _source(query['sourceId'])
    classification = _digest_class(row)
    return {
        'status': classification, 'sourceId': query['sourceId'], 'evidenceClass': row['scope'],
        'sourceSubject': row['subject'], 'digestProvenance': row['digestOrigin'],
        'algorithm': row['algorithm'], 'completeDigest': row['complete'] if row['evidence'] == 'Digest' else None,
        'identityComparison': row['comparison'], 'sourceIndependence': row['independentOfTarget'],
        'actualOriginalDigestBound': (row['scope'] == 'ReviewedDocumentary' and
                                     classification == 'AuthenticatedOriginalAttachmentDigest'),
        **NO_PHYSICAL_INFERENCE,
    }


def attachment_to_rom_blob_proof(query):
    """Join the historical subject to the pinned digital target only."""
    shape(query, ('sourceIds', 'claim'), 'ClosedDigitalJoinQueryRequired')
    ids = query['sourceIds']
    need(type(ids) is list and len(ids) <= 12 and all(type(item) is str for item in ids)
         and len(ids) == len(set(ids)), 'ClosedUniqueSourceSelectionRequired')
    need(query['claim'] in ('Inspect', 'AssertDonor', 'AssertFactoryOriginality', 'AssertC8', 'AuthorizeExecution'),
         'KnownDigitalJoinClaimRequired')
    rows = [(identity, _source(identity)) for identity in sorted(ids)]
    scopes = {row['scope'] for _, row in rows}
    need(len(scopes) <= 1, 'MixedInventedAndDocumentarySourcesRefused')
    evidence = [{'sourceId': identity, 'payloadClass': _payload_class(row), 'digestClass': _digest_class(row),
                 'sourceSubject': row['subject'], 'origin': row['origin'], 'archiveCaptureUtc': row['captureUtc']}
                for identity, row in rows]
    outcomes = {item[field] for item in evidence for field in ('payloadClass', 'digestClass')}
    sources = {}
    for identity, row in rows:
        if row['origin'] is not None:
            sources.setdefault(row['origin'], []).append(identity)
    if 'ConflictingAttachmentIdentity' in outcomes:
        verdict = 'AttachmentIdentityConflict'
    elif 'AuthenticatedOriginalAttachmentBytes' in outcomes:
        verdict = 'ExactHistoricalAttachmentToBlobBinding'
    elif 'AuthenticatedOriginalAttachmentDigest' in outcomes:
        verdict = 'DigestQualifiedAttachmentToBlobBinding'
    elif 'ByteIdenticalDerivative' in outcomes:
        verdict = 'OnlyLaterDerivativeEstablished'
    else:
        verdict = 'HistoricalAttachmentUnbound'
    promotion = query['claim'] != 'Inspect'
    qualified = verdict in ('ExactHistoricalAttachmentToBlobBinding', 'DigestQualifiedAttachmentToBlobBinding')
    actual = qualified and scopes == {'ReviewedDocumentary'} and not promotion
    conditional = qualified and scopes == {'InventedPolicyControl'} and not promotion
    return {
        'status': 'RefusedEvidencePromotion' if promotion else verdict, 'digitalJoinStatus': verdict,
        'actualAttachmentToBlobBinding': verdict if actual else None,
        'conditionalFixtureBinding': verdict if conditional else None,
        'sourceEvidence': evidence,
        'dependencyLineage': [{'origin': origin, 'sourceIds': sources[origin]} for origin in sorted(sources)],
        'unboundSourceOrigins': [identity for identity, row in rows if row['origin'] is None],
        'independentExtractionWitnessCount': 0,
        'acceptedEdges': ['HistoricalAttachmentToPinnedBlob'] if actual else
        ['InventedAttachmentToInventedBlob'] if conditional else [],
        'rejectedEdges': [query['claim']] if promotion else [],
        'unresolvedConstraints': ([] if actual else ['AuthenticatedHistoricalAttachmentIdentity']) +
        ['ContemporaneousExtractionCustody', 'SameUnitDonorBinding', 'IndependentFactoryOriginality',
         'ApplicableC8RevisionEvidence'],
        **NO_PHYSICAL_INFERENCE,
    }


def documentary_evidence_status(query):
    """Evaluate the two evidence axes without promoting one into the other."""
    from prearchive_extraction_custody.documentary import historical_chronology_consistency
    from prearchive_extraction_custody.extraction import same_unit_donor_binding

    shape(query, ('digital', 'physical'), 'ClosedTwoAxisQueryRequired')
    digital = attachment_to_rom_blob_proof(query['digital'])
    physical = same_unit_donor_binding(query['physical'])
    recorded = historical_chronology_consistency({'mode': 'Recorded', 'events': [], 'claim': 'Inspect'})
    actual = digital['actualAttachmentToBlobBinding']
    if digital['status'] == 'RefusedEvidencePromotion':
        status = 'RefusedEvidencePromotion'
    elif digital['status'] == 'AttachmentIdentityConflict':
        status = 'ConditionalFixtureConflict' if any(
            item['sourceId'].startswith('Fixture') for item in digital['sourceEvidence']
        ) else 'EXTRACTION_SOURCE_IDENTITY_CONFLICT'
    else:
        status = {
            'ExactHistoricalAttachmentToBlobBinding': 'ORIGINAL_ATTACHMENT_BYTE_IDENTITY_ESTABLISHED',
            'DigestQualifiedAttachmentToBlobBinding': 'ORIGINAL_ATTACHMENT_DIGEST_IDENTITY_ESTABLISHED',
        }.get(actual, 'EXTRACTION_EVIDENCE_DEPENDENCY_CONFIRMED')
    return {
        'status': status, 'digitalAxis': digital, 'physicalAxis': physical,
        'chronology': {'recordedEvents': recorded['events'], 'observedPhysicalExtractionTime': None,
                       'originalPublicationTime': None, 'dateOrderConfersCustody': False,
                       'verifiedAttachmentCaptureTimes': sorted({row['archiveCaptureUtc'] for row in
                           digital['sourceEvidence'] if row['archiveCaptureUtc'] is not None})},
        'minimumNextEvidence': {
            'digital': None if actual else 'AuthenticHistoricalAttachmentBytesOrOriginalCompleteDigest',
            'physical': 'ContemporaneousReadRecordBindingFullImageToStableDonor',
        },
        'acceptedEdges': digital['acceptedEdges'] if actual else [],
        'conditionalFixtureEdges': ([] if actual else digital['acceptedEdges']) + physical['acceptedEdges'],
        'rejectedEdges': digital['rejectedEdges'] + physical['rejectedEdges'],
        'unresolvedConstraints': digital['unresolvedConstraints'],
        **NO_PHYSICAL_INFERENCE,
    }
