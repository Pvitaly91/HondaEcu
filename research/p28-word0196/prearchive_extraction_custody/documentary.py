"""Bounded archive dependency, artifact identity, and chronology checks."""
from datetime import datetime
from itertools import combinations
import re

from enclosing_caller_return.state import need, shape

SOURCES = {
    'ArchivedParent2004': ('ContemporaneousAttachment', 'HistoricalAttachmentMetadata'),
    'HistoricalAttachment': ('ContemporaneousAttachment', 'HistoricalAttachmentMetadata'),
    'HistoricalTableMirror': ('SecondaryRepublication', 'HistoricalAttachmentMetadata'),
    'ArchivePreImport': ('ArchiveImportRecord', 'GitArchiveBlob'),
    'ArchiveImport': ('ArchiveImportRecord', 'GitArchiveBlob'),
    'ArchiveDedup': ('ByteIdenticalMirror', 'GitArchiveBlob'),
    'ProjectAcquisition': ('AuthenticatedProjectAcquisition', 'GitArchiveBlob'),
    'SearchIndex': ('SearchIndexOnly', None),
    'SnapshotUnavailable': ('UnknownOrigin', None),
    'CatalogueAttribution': ('CatalogueAttribution', None),
    'ThirdPartyPhoto': ('ThirdPartyExample', None),
    'FixtureOriginalRecord': ('InventedOriginalRecord', 'FixtureOrigin'),
    'FixtureDependentMirror': ('InventedMirror', 'FixtureOrigin'),
    'FixtureOtherOrigin': ('InventedOtherRecord', 'FixtureOtherOrigin'),
}
DATES = (
    {'event': 'AttachmentUpload', 'time': '2004-02-19T19:35', 'zone': None,
     'source': 'HistoricalAttachment', 'authority': 'RecordedUploadMetadata'},
    {'event': 'EarlyParentRevision', 'time': '2004-05-21T23:35', 'zone': 'UTC',
     'source': 'ArchivedParent2004', 'authority': 'RecordedParentRevision'},
    {'event': 'ArchivedParentReplay', 'time': '2004-05-22T16:20:12', 'zone': 'UTC',
     'source': 'ArchivedParent2004', 'authority': 'AuthenticatedArchiveCapture'},
    {'event': 'ParentRevision', 'time': '2007-04-02T17:06', 'zone': 'UTC',
     'source': 'HistoricalAttachment', 'authority': 'RecordedParentRevision'},
    {'event': 'ArchivePreImport', 'time': '2024-08-10T22:29:55', 'zone': 'UTC',
     'source': 'ArchivePreImport', 'authority': 'RecordedGitMetadata'},
    {'event': 'ArchiveImport', 'time': '2024-08-11T03:29:47', 'zone': 'UTC',
     'source': 'ArchiveImport', 'authority': 'RecordedGitMetadata'},
    {'event': 'ArchiveDeduplication', 'time': '2024-12-28T14:51:51', 'zone': 'UTC',
     'source': 'ArchiveDedup', 'authority': 'RecordedGitMetadata'},
    {'event': 'ProjectAcquisition', 'time': '2026-09-04', 'zone': 'UTC',
     'source': 'ProjectAcquisition', 'authority': 'AcceptedAcquisitionDossier'},
)
ARCHIVE_HISTORY = (
    ('ArchivePreImport', '8db2006a08bfc157911d6c4dfca7be6db9a7bc58', 2, 'FirstMatchingTreeInReviewedAncestry'),
    ('ArchiveImport', 'e9dbf236b814e5abb203069d09071880474475d9', 3, 'LaterImportAddsDependentCopy'),
    ('ArchiveDedup', '0fcca91f1124672b7b756118d9fd5d701102eefc', 1, 'TwoRemovedOneRenamed'),
)


def _source_ids(source_ids):
    need(type(source_ids) is list and len(source_ids) <= len(SOURCES)
         and all(type(item) is str and item in SOURCES for item in source_ids)
         and len(set(source_ids)) == len(source_ids), 'ClosedUniqueSourceIdsRequired')
    invented = sum(item.startswith('Fixture') for item in source_ids)
    need(invented in (0, len(source_ids)), 'FixtureAndActualSourceMixingRefused')
    return sorted(source_ids)


def archive_copy_dependency(query):
    """Group evidence by supported dependence rather than locator count."""
    shape(query, ('sourceIds', 'claim'), 'ClosedArchiveDependencyQueryRequired')
    ids = _source_ids(query['sourceIds'])
    need(query['claim'] in ('Inspect', 'IndependentExtractionWitness'), 'KnownArchiveDependencyClaimRequired')
    groups, unresolved = {}, []
    for name in ids:
        _, origin = SOURCES[name]
        if origin is None:
            unresolved.append(name)
        else:
            groups.setdefault(origin, []).append(name)
    pairs = [
        {'left': left, 'right': right, 'relation': 'DependentForOrigin' if SOURCES[left][1] == SOURCES[right][1]
         else 'DifferentEvidenceScope'}
        for left, right in combinations(ids, 2) if SOURCES[left][1] and SOURCES[right][1]
    ]
    return {
        'status': 'ReviewedSourceDependencies' if query['claim'] == 'Inspect' else 'RefusedEvidencePromotion',
        'sourceCount': len(ids), 'knownOriginGroups': [{'origin': key, 'members': groups[key]} for key in sorted(groups)],
        'sourceClasses': [{'sourceId': name, 'evidenceClass': SOURCES[name][0]} for name in ids],
        'originUnbound': unresolved, 'pairs': pairs, 'independentExtractionWitnessCount': 0,
    }


def historical_attachment_provenance(query):
    """Distinguish the retained upload record from parent and extraction claims."""
    shape(query, ('sourceId', 'claim'), 'ClosedHistoricalAttachmentQueryRequired')
    source = query['sourceId']
    need(source in ('ArchivedParent2004', 'HistoricalAttachment', 'HistoricalTableMirror', 'SearchIndex', 'SnapshotUnavailable')
         and query['claim'] in ('Inspect', 'PhysicalExtraction', 'ObservedHttp', 'InventParent'),
         'KnownAttachmentScopeRequired')
    early = source == 'ArchivedParent2004'
    authenticated = early or source == 'HistoricalAttachment'
    return {
        'status': 'RefusedEvidencePromotion' if query['claim'] != 'Inspect' else (
            'AuthenticatedHistoricalMetadata' if authenticated else
            'DerivativeMetadataOnly' if source == 'HistoricalTableMirror' else
            'AccessUnavailable' if source == 'SnapshotUnavailable' else 'ArchiveIndexOnly'),
        'sourceId': source, 'recordedUpload': DATES[0].copy() if authenticated else None,
        'parentTopic': 'EcuDefinitionCodes' if authenticated else None,
        'retainedParentRevision': ('r1.20' if early else 'r1.84') if authenticated else None,
        'recordedParentRevision': DATES[1 if early else 3].copy() if authenticated else None,
        'archiveCapture': DATES[2].copy() if early else None,
        'catalogueAttribution': 'P28-A01' if authenticated else None,
        'catalogueAndAttachmentShareParent': True if authenticated else None,
        'numericAttachmentId': None,
        'uploaderIdentity': None, 'originalPublicationRecord': None, 'parentExtractionRecord': None,
        'linkedPayloadIdentity': None, 'sameUnitDonor': None, 'physicalExtractionTime': None,
        'independentlyObservedHttp': None,
        'missingObligations': ['ExactAttachmentPayloadBinding', 'AuthenticatedOriginalPublication',
                               'ContemporaneousExtractionWithDonorAndBytes'],
    }


def rom_artifact_identity(query):
    """Classify the evidence strength while keeping full payloads private."""
    shape(query, ('sourceId', 'method', 'byteCount', 'match', 'claim'), 'ClosedArtifactIdentityQueryRequired')
    source, method = query['sourceId'], query['method']
    need(source in ('ProjectAcquisition', 'ArchivePreImport', 'ArchiveImport', 'ArchiveDedup',
                    'ArchivedParent2004', 'HistoricalAttachment', 'SnapshotUnavailable', 'FixtureArtifact')
         and query['claim'] in ('Inspect', 'FactoryOriginality', 'SameDonor', 'InferMcuFromSize')
         and method in (None, 'FullBytes', 'ArchivedBlob', 'DocumentedDigest', 'PartialHash', 'Size', 'Filename')
         and (query['byteCount'] is None or type(query['byteCount']) is int and 0 <= query['byteCount'] <= 65536)
         and (query['match'] is None or type(query['match']) is bool), 'KnownArtifactEvidenceRequired')
    invented = source == 'FixtureArtifact'
    need(invented or (method, query['byteCount'], query['match']) == (None, None, None),
         'CallerSuppliedRealEvidenceRefused')
    if invented:
        strength = {
            'FullBytes': 'ExactFullByteMatch', 'ArchivedBlob': 'MatchingArchivedBlob',
            'DocumentedDigest': 'MatchingDocumentedCryptographicDigest', 'PartialHash': 'PartialHashOnly',
            'Size': 'SizeOnly', 'Filename': 'FilenameOnly', None: 'SourceUnavailable',
        }[method]
        if method == 'FullBytes' and query['match'] is not True:
            strength = 'DifferentBytes' if query['match'] is False else 'SourceUnavailable'
        elif method == 'FullBytes' and query['byteCount'] != 32768:
            strength = 'DifferentBytes'
        elif method in ('ArchivedBlob', 'DocumentedDigest') and query['match'] is not True:
            strength = 'SourceUnavailable'
        count = query['byteCount']
    else:
        strength, count = {
            'ProjectAcquisition': ('ExactFullByteMatch', 32768),
            'ArchivePreImport': ('MatchingArchivedBlob', 32768),
            'ArchiveImport': ('MatchingArchivedBlob', 32768),
            'ArchiveDedup': ('MatchingArchivedBlob', 32768),
            'ArchivedParent2004': ('SourceBytesNotAuthenticated', None),
            'HistoricalAttachment': ('SourceBytesNotAuthenticated', None),
            'SnapshotUnavailable': ('SourceUnavailable', None),
        }[source]
    return {
        'status': 'RefusedEvidencePromotion' if query['claim'] != 'Inspect' else strength,
        'sourceId': source, 'identityClass': strength, 'byteCount': count,
        'inventedFixture': invented, 'actualImageBinding': not invented and strength in (
            'ExactFullByteMatch', 'MatchingArchivedBlob'),
        'actualEcuIdentity': None, 'actualMcuIdentity': None, 'factoryOriginality': None,
    }


def _edge(source, start, end, status, missing=None):
    historical = source == 'ArchivedParent2004'
    return {'sourceId': source, 'fromNode': start, 'toNode': end, 'status': status,
            'subject': 'HistoricalAttachmentRecord' if historical else 'StudiedImage' if status == 'Proven' else None,
            'artifactIdentity': 'RecordedExactDigitalBinding' if status == 'Proven' and not historical else None,
            'evidenceClass': SOURCES[source][0] if source else 'UnknownOrigin',
            'chronology': 'AuthenticatedParentReplayMetadata' if historical else 'DigitalArchiveEventOnly'
            if status == 'Proven' else None,
            'sourceIndependence': SOURCES[source][1] if source else None,
            'exactApplicability': 'PublicationMetadataOnly' if historical else 'DigitalArchiveOnly'
            if status == 'Proven' else 'Unestablished',
            'missingObligation': missing, 'conflictStatus': None, 'privacyStatus': 'RedactedMetadata'}


def prearchive_source_lineage(query):
    """Project the proved digital chain and its unresolved prearchive boundary."""
    shape(query, ('sourceIds', 'claim'), 'ClosedPrearchiveLineageQueryRequired')
    ids = _source_ids(query['sourceIds'])
    need(query['claim'] in ('Inspect', 'AssertOriginalPublication', 'AssertDonor'),
         'KnownPrearchiveLineageClaimRequired')
    accepted = []
    for source, start, end in (
        ('ArchivedParent2004', 'ArchivedParent2004', 'HistoricalAttachment'),
        ('ArchivePreImport', 'EarlierGitBlob', 'ImportedGitBlob'),
        ('ArchiveImport', 'ImportedGitBlob', 'PinnedArchiveImage'),
        ('ArchiveDedup', 'PinnedArchiveImage', 'DeduplicatedGitBlob'),
        ('ProjectAcquisition', 'PinnedArchiveImage', 'StudiedImage'),
    ):
        if source in ids:
            accepted.append(_edge(source, start, end, 'Proven'))
    gaps = [
        _edge('HistoricalAttachment' if 'HistoricalAttachment' in ids else None,
              'HistoricalAttachment', 'ImportedGitBlob', 'Unresolved',
              'ExactHistoricalAttachmentToImportedBlobBinding'),
        _edge(None, 'OriginalPublication', 'OriginalExtraction', 'Unresolved',
              'ContemporaneousExtractionRecordWithFullImageBinding'),
        _edge(None, 'OriginalExtraction', 'SameUnitDonor', 'Unresolved',
              'StableDonorIdentityBoundToReadSession'),
    ]
    if 'SnapshotUnavailable' in ids:
        gaps.insert(0, _edge('SnapshotUnavailable', 'CandidatePublication', 'HistoricalAttachment', 'Unavailable',
                            'AccessibleAuthenticatedPublication'))
    return {
        'status': 'DocumentaryCustodyGapCharacterized' if query['claim'] == 'Inspect' else 'RefusedEvidencePromotion',
        'sourceIds': ids, 'acceptedEdges': accepted, 'rejectedEdges': gaps,
        'archiveHistory': [{'sourceId': key, 'commit': commit, 'matchingEntries': count, 'relation': relation}
                           for key, commit, count, relation in ARCHIVE_HISTORY if key in ids],
        'earliestAuthenticatedMetadata': 'ArchivedParent2004' if 'ArchivedParent2004' in ids else
        'HistoricalAttachment' if 'HistoricalAttachment' in ids else None,
        'earliestAuthenticatedExactArtifact': next(
            (key for key in ('ArchivePreImport', 'ArchiveImport', 'ArchiveDedup', 'ProjectAcquisition') if key in ids),
            None),
        'originalPublication': None, 'originalExtraction': None, 'sameUnitDonor': None,
        'minimumExtractionEvidence': 'ContemporaneousReadSessionBindingExactImageAndStableDonor',
    }


def _time(record):
    raw = record['time']
    if raw is None:
        return None
    need(type(raw) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?)?', raw) is not None,
         'ExactDocumentaryTimeFormatRequired')
    try:
        value = datetime.fromisoformat(raw)
    except ValueError:
        raise ValueError('InvalidDocumentaryTime') from None
    return value if record['zone'] == 'UTC' and 'T' in raw else None


def historical_chronology_consistency(query):
    """Compare dates only when scope, time zone and an ordering claim permit it."""
    shape(query, ('mode', 'events', 'claim'), 'ClosedChronologyQueryRequired')
    need(query['mode'] in ('Recorded', 'Invented')
         and query['claim'] in ('Inspect', 'ArchiveDateIsReadDate', 'UploadDateIsReadDate',
                                'UnknownZoneIsUtc', 'LiteralHttpIsObserved', 'MirrorIsFirstPublication')
         and type(query['events']) is list and len(query['events']) <= 8, 'KnownChronologyScopeRequired')
    if query['mode'] == 'Recorded':
        need(not query['events'], 'FrozenRecordedChronologyRequired')
        events = [item.copy() for item in DATES]
    else:
        events = []
        for item in query['events']:
            shape(item, ('event', 'time', 'zone'), 'ClosedInventedChronologyEventRequired')
            need(item['event'] in ('PhysicalExtraction', 'OriginalPublication', 'AttachmentUpload', 'ArchiveImport',
                                   'ArchiveDeduplication', 'ProjectAcquisition', 'LocalVerification')
                 and item['zone'] in ('UTC', None), 'KnownChronologyEventRequired')
            events.append({**item, 'source': 'InventedDocumentaryControl', 'authority': 'InventedNotObserved'})
        need(len({item['event'] for item in events}) == len(events), 'UniqueChronologyEventsRequired')
    ranks = ('PhysicalExtraction', 'OriginalPublication', 'AttachmentUpload', 'EarlyParentRevision',
             'ArchivedParentReplay', 'ParentRevision', 'ArchivePreImport', 'ArchiveImport',
             'ArchiveDeduplication', 'ProjectAcquisition', 'LocalVerification')
    order = sorted(events, key=lambda item: ranks.index(item['event']))
    times = {item['event']: _time(item) for item in order}
    relations = []
    for earlier, later in combinations(order, 2):
        left, right = earlier['event'], later['event']
        a, b = times[left], times[right]
        state = 'Unresolved' if a is None or b is None else 'Consistent' if a <= b else 'Conflicting'
        relations.append({'fromEvent': left, 'toEvent': right, 'status': state})
    if query['claim'] != 'Inspect':
        status = 'RefusedEvidencePromotion'
    elif any(row['status'] == 'Conflicting' for row in relations):
        status = 'Conflicting'
    elif not relations or any(row['status'] == 'Unresolved' for row in relations):
        status = 'Unresolved'
    else:
        status = 'Consistent'
    return {'status': status, 'events': order, 'relations': relations,
            'actualExtractionTime': None, 'originalPublicationTime': None, 'observedHttpResponse': None,
            'chronologyEstablishesProvenance': False}
