"""Independent documentary expectations from reviewed archive and attachment facts."""

from copy import deepcopy
from datetime import datetime
from itertools import combinations


_EVIDENCE = {
    'ArchivePreImport': 'ArchiveImportRecord',
    'ArchiveImport': 'ArchiveImportRecord',
    'ArchiveDedup': 'ByteIdenticalMirror',
    'ProjectAcquisition': 'AuthenticatedProjectAcquisition',
    'ArchivedParent2004': 'ContemporaneousAttachment',
    'HistoricalAttachment': 'ContemporaneousAttachment',
    'HistoricalTableMirror': 'SecondaryRepublication',
    'CatalogueAttribution': 'CatalogueAttribution',
    'ThirdPartyPhoto': 'ThirdPartyExample',
    'SearchIndex': 'SearchIndexOnly',
    'SnapshotUnavailable': 'UnknownOrigin',
    'FixtureOriginalRecord': 'InventedOriginalRecord',
    'FixtureDependentMirror': 'InventedMirror',
    'FixtureOtherOrigin': 'InventedOtherRecord',
}
_ORIGIN_GROUPS = {
    'FixtureOrigin': {'FixtureOriginalRecord', 'FixtureDependentMirror'},
    'FixtureOtherOrigin': {'FixtureOtherOrigin'},
    'GitArchiveBlob': {'ArchivePreImport', 'ArchiveImport', 'ArchiveDedup', 'ProjectAcquisition'},
    'HistoricalAttachmentMetadata': {'ArchivedParent2004', 'HistoricalAttachment', 'HistoricalTableMirror'},
}
_ARCHIVE_EXPECTED = {
    'ArchivePreImport': ('8db2006a08bfc157911d6c4dfca7be6db9a7bc58', 2, 'FirstMatchingTreeInReviewedAncestry'),
    'ArchiveImport': ('e9dbf236b814e5abb203069d09071880474475d9', 3, 'LaterImportAddsDependentCopy'),
    'ArchiveDedup': ('0fcca91f1124672b7b756118d9fd5d701102eefc', 1, 'TwoRemovedOneRenamed'),
}
_DIGITAL_EDGES = (
    ('ArchivePreImport', 'EarlierGitBlob', 'ImportedGitBlob'),
    ('ArchiveImport', 'ImportedGitBlob', 'PinnedArchiveImage'),
    ('ArchiveDedup', 'PinnedArchiveImage', 'DeduplicatedGitBlob'),
    ('ProjectAcquisition', 'PinnedArchiveImage', 'StudiedImage'),
)
_RECORDED_EVENTS = (
    ('AttachmentUpload', '2004-02-19T19:35', None, 'HistoricalAttachment', 'RecordedUploadMetadata'),
    ('EarlyParentRevision', '2004-05-21T23:35', 'UTC', 'ArchivedParent2004', 'RecordedParentRevision'),
    ('ArchivedParentReplay', '2004-05-22T16:20:12', 'UTC', 'ArchivedParent2004', 'AuthenticatedArchiveCapture'),
    ('ParentRevision', '2007-04-02T17:06', 'UTC', 'HistoricalAttachment', 'RecordedParentRevision'),
    ('ArchivePreImport', '2024-08-10T22:29:55', 'UTC', 'ArchivePreImport', 'RecordedGitMetadata'),
    ('ArchiveImport', '2024-08-11T03:29:47', 'UTC', 'ArchiveImport', 'RecordedGitMetadata'),
    ('ArchiveDeduplication', '2024-12-28T14:51:51', 'UTC', 'ArchiveDedup', 'RecordedGitMetadata'),
    ('ProjectAcquisition', '2026-09-04', 'UTC', 'ProjectAcquisition', 'AcceptedAcquisitionDossier'),
)
_EVENT_FIELDS = ('event', 'time', 'zone', 'source', 'authority')
_INVENTED_ORDER = ('PhysicalExtraction', 'OriginalPublication', 'AttachmentUpload', 'ArchiveImport',
                   'ArchiveDeduplication', 'ProjectAcquisition', 'LocalVerification')
_REFUSED = 'RefusedEvidencePromotion'


def expected_dependency(query):
    ids = set(query['sourceIds'])
    selected_groups = {origin: members & ids for origin, members in _ORIGIN_GROUPS.items()}
    origin_known = set().union(*selected_groups.values())
    dependent = set().union(*(set(combinations(sorted(members), 2)) for members in selected_groups.values()))
    return {
        'status': 'ReviewedSourceDependencies' if query['claim'] == 'Inspect' else _REFUSED,
        'sourceCount': len(ids),
        'knownOriginGroups': [{'origin': key, 'members': sorted(members)}
                              for key, members in sorted(selected_groups.items()) if members],
        'sourceClasses': [{'sourceId': key, 'evidenceClass': _EVIDENCE[key]} for key in sorted(ids)],
        'originUnbound': sorted(ids - origin_known),
        'pairs': [{'left': left, 'right': right,
                   'relation': 'DependentForOrigin' if (left, right) in dependent else 'DifferentEvidenceScope'}
                  for left, right in combinations(sorted(origin_known), 2)],
        'independentExtractionWitnessCount': 0,
    }


def _recorded_event(row):
    return dict(zip(_EVENT_FIELDS, row, strict=True))


def expected_attachment(query):
    source = query['sourceId']
    parent_revisions = {
        'ArchivedParent2004': ('r1.20', 'EarlyParentRevision', 'ArchivedParentReplay'),
        'HistoricalAttachment': ('r1.84', 'ParentRevision', None),
    }
    revision, revision_event, replay_event = parent_revisions.get(source, (None, None, None))
    recorded = {event[0]: _recorded_event(event) for event in _RECORDED_EVENTS}
    attributes = {
        'recordedUpload': recorded['AttachmentUpload'],
        'parentTopic': 'EcuDefinitionCodes',
        'retainedParentRevision': revision,
        'recordedParentRevision': recorded.get(revision_event),
        'archiveCapture': recorded.get(replay_event),
        'catalogueAttribution': 'P28-A01',
        'catalogueAndAttachmentShareParent': True,
    }
    status = {
        'ArchivedParent2004': 'AuthenticatedHistoricalMetadata',
        'HistoricalAttachment': 'AuthenticatedHistoricalMetadata',
        'HistoricalTableMirror': 'DerivativeMetadataOnly',
        'SearchIndex': 'ArchiveIndexOnly',
        'SnapshotUnavailable': 'AccessUnavailable',
    }[source]
    return {
        'status': status if query['claim'] == 'Inspect' else _REFUSED,
        'sourceId': source,
        **(attributes if revision is not None else dict.fromkeys(attributes)),
        **dict.fromkeys(('numericAttachmentId', 'uploaderIdentity', 'originalPublicationRecord',
                         'parentExtractionRecord', 'linkedPayloadIdentity', 'sameUnitDonor',
                         'physicalExtractionTime', 'independentlyObservedHttp')),
        'missingObligations': ['ExactAttachmentPayloadBinding', 'AuthenticatedOriginalPublication',
                               'ContemporaneousExtractionWithDonorAndBytes'],
    }


def expected_identity(query):
    source = query['sourceId']
    fixture = source == 'FixtureArtifact'
    actual = source in _ORIGIN_GROUPS['GitArchiveBlob']
    count = 32768 if actual else None
    if fixture:
        count = query['byteCount']
        match = query['match']
        method = query['method']
        full_match = 'DifferentBytes' if count != 32768 else 'ExactFullByteMatch'
        options = {
            'FullBytes': {True: full_match, False: 'DifferentBytes', None: 'SourceUnavailable'}[match],
            'ArchivedBlob': 'MatchingArchivedBlob' if match else 'SourceUnavailable',
            'DocumentedDigest': 'MatchingDocumentedCryptographicDigest' if match else 'SourceUnavailable',
            'PartialHash': 'PartialHashOnly', 'Size': 'SizeOnly', 'Filename': 'FilenameOnly',
            None: 'SourceUnavailable',
        }
        strength = options[method]
    elif source == 'ProjectAcquisition':
        strength = 'ExactFullByteMatch'
    elif actual:
        strength = 'MatchingArchivedBlob'
    elif source in ('ArchivedParent2004', 'HistoricalAttachment'):
        strength = 'SourceBytesNotAuthenticated'
    else:
        strength = 'SourceUnavailable'
    return {
        'status': strength if query['claim'] == 'Inspect' else _REFUSED,
        'sourceId': source, 'identityClass': strength, 'byteCount': count,
        'inventedFixture': fixture, 'actualImageBinding': actual,
        'actualEcuIdentity': None, 'actualMcuIdentity': None, 'factoryOriginality': None,
    }


def _digital_edge(source, start, end):
    return {
        'sourceId': source, 'fromNode': start, 'toNode': end, 'status': 'Proven',
        'subject': 'StudiedImage', 'artifactIdentity': 'RecordedExactDigitalBinding',
        'evidenceClass': _EVIDENCE[source], 'chronology': 'DigitalArchiveEventOnly',
        'sourceIndependence': 'GitArchiveBlob', 'exactApplicability': 'DigitalArchiveOnly',
        'missingObligation': None, 'conflictStatus': None, 'privacyStatus': 'RedactedMetadata',
    }


def _missing_edge(source, start, end, obligation, status='Unresolved'):
    return {
        'sourceId': source, 'fromNode': start, 'toNode': end, 'status': status,
        'subject': None, 'artifactIdentity': None, 'evidenceClass': _EVIDENCE.get(source, 'UnknownOrigin'),
        'chronology': None, 'sourceIndependence': 'HistoricalAttachmentMetadata' if source == 'HistoricalAttachment' else None,
        'exactApplicability': 'Unestablished', 'missingObligation': obligation, 'conflictStatus': None,
        'privacyStatus': 'RedactedMetadata',
    }


def expected_lineage(query):
    selected = set(query['sourceIds'])
    attachment = 'HistoricalAttachment' if 'HistoricalAttachment' in selected else None
    gaps = []
    if 'SnapshotUnavailable' in selected:
        gaps.append(_missing_edge('SnapshotUnavailable', 'CandidatePublication', 'HistoricalAttachment',
                                  'AccessibleAuthenticatedPublication', 'Unavailable'))
    gaps.extend((
        _missing_edge(attachment, 'HistoricalAttachment', 'ImportedGitBlob',
                      'ExactHistoricalAttachmentToImportedBlobBinding'),
        _missing_edge(None, 'OriginalPublication', 'OriginalExtraction',
                      'ContemporaneousExtractionRecordWithFullImageBinding'),
        _missing_edge(None, 'OriginalExtraction', 'SameUnitDonor', 'StableDonorIdentityBoundToReadSession'),
    ))
    history = [{'sourceId': key, 'commit': commit, 'matchingEntries': count, 'relation': relation}
               for key, (commit, count, relation) in _ARCHIVE_EXPECTED.items() if key in selected]
    earliest = next((row[0] for row in _DIGITAL_EDGES if row[0] in selected), None)
    accepted = [_digital_edge(*row) for row in _DIGITAL_EDGES if row[0] in selected]
    if 'ArchivedParent2004' in selected:
        accepted.insert(0, {
            'sourceId': 'ArchivedParent2004', 'fromNode': 'ArchivedParent2004', 'toNode': 'HistoricalAttachment',
            'status': 'Proven', 'subject': 'HistoricalAttachmentRecord', 'artifactIdentity': None,
            'evidenceClass': 'ContemporaneousAttachment', 'chronology': 'AuthenticatedParentReplayMetadata',
            'sourceIndependence': 'HistoricalAttachmentMetadata', 'exactApplicability': 'PublicationMetadataOnly',
            'missingObligation': None, 'conflictStatus': None, 'privacyStatus': 'RedactedMetadata',
        })
    return {
        'status': 'DocumentaryCustodyGapCharacterized' if query['claim'] == 'Inspect' else _REFUSED,
        'sourceIds': sorted(selected),
        'acceptedEdges': accepted, 'rejectedEdges': gaps, 'archiveHistory': history,
        'earliestAuthenticatedMetadata': 'ArchivedParent2004' if 'ArchivedParent2004' in selected else attachment,
        'earliestAuthenticatedExactArtifact': earliest,
        'originalPublication': None, 'originalExtraction': None, 'sameUnitDonor': None,
        'minimumExtractionEvidence': 'ContemporaneousReadSessionBindingExactImageAndStableDonor',
    }


def expected_chronology(query):
    if query['mode'] == 'Recorded':
        events = [_recorded_event(row) for row in _RECORDED_EVENTS]
    else:
        events_by_name = {item['event']: item for item in query['events']}
        events = [{**deepcopy(events_by_name[key]), 'source': 'InventedDocumentaryControl',
                   'authority': 'InventedNotObserved'} for key in _INVENTED_ORDER if key in events_by_name]
    instants = {event['event']: datetime.fromisoformat(event['time']) for event in events
                if event['zone'] == 'UTC' and event['time'] is not None and 'T' in event['time']}
    relations = []
    for first, second in combinations((row['event'] for row in events), 2):
        if first in instants and second in instants:
            state = 'Conflicting' if instants[first] > instants[second] else 'Consistent'
        else:
            state = 'Unresolved'
        relations.append({'fromEvent': first, 'toEvent': second, 'status': state})
    results = {row['status'] for row in relations}
    status = next((item for item in ('Conflicting', 'Unresolved', 'Consistent') if item in results), 'Unresolved')
    return {
        'status': status if query['claim'] == 'Inspect' else _REFUSED,
        'events': events, 'relations': relations, 'actualExtractionTime': None,
        'originalPublicationTime': None, 'observedHttpResponse': None, 'chronologyEstablishesProvenance': False,
    }
