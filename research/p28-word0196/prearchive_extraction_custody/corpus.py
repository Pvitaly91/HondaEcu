"""Reviewed documentary inputs and explicitly invented policy controls."""
from copy import deepcopy

ARCHIVE_IDS = ('ArchivedParent2004', 'HistoricalAttachment', 'ArchivePreImport', 'ArchiveImport', 'ArchiveDedup',
               'ProjectAcquisition')


def case(operation, name, query):
    return {'id': name, 'operation': operation, 'input': deepcopy(query)}


def artifact(source, method=None, count=None, match=None, claim='Inspect'):
    return dict(sourceId=source, method=method, byteCount=count, match=match, claim=claim)


def documentary_cases():
    for name, ids, claim in (
        ('recorded', ARCHIVE_IDS, 'Inspect'),
        ('blocked-snapshot', (*ARCHIVE_IDS, 'SnapshotUnavailable'), 'Inspect'),
        ('earliest-within-scope', ('ArchiveImport', 'ArchiveDedup'), 'Inspect'),
        ('only-dedup', ('ArchiveDedup',), 'Inspect'),
        ('missing-source', ('SearchIndex',), 'Inspect'),
        ('promotion-publication', ARCHIVE_IDS, 'AssertOriginalPublication'),
        ('promotion-donor', ARCHIVE_IDS, 'AssertDonor'),
    ):
        yield case('prearchive_source_lineage', 'lineage-' + name, {'sourceIds': list(ids), 'claim': claim})
    for name, ids, claim in (
        ('mixed-document-scope', (*ARCHIVE_IDS, 'HistoricalTableMirror', 'SearchIndex'), 'Inspect'),
        ('same-blob-three-paths', ('ArchivePreImport', 'ArchiveImport', 'ArchiveDedup'), 'IndependentExtractionWitness'),
        ('fixture-independent-record', ('FixtureOriginalRecord', 'FixtureDependentMirror', 'FixtureOtherOrigin'), 'Inspect'),
        ('no-origin', ('SearchIndex', 'ThirdPartyPhoto', 'CatalogueAttribution'), 'Inspect'),
    ):
        yield case('archive_copy_dependency', 'dependency-' + name, {'sourceIds': list(ids), 'claim': claim})
    for name, source, claim in (
        ('parent-2004-replay', 'ArchivedParent2004', 'Inspect'),
        ('parent-retained', 'HistoricalAttachment', 'Inspect'),
        ('derivative', 'HistoricalTableMirror', 'Inspect'),
        ('index-only', 'SearchIndex', 'Inspect'),
        ('snapshot-unavailable', 'SnapshotUnavailable', 'Inspect'),
        ('force-read-date', 'HistoricalAttachment', 'PhysicalExtraction'),
        ('force-observed-http', 'HistoricalAttachment', 'ObservedHttp'),
        ('invent-parent', 'SnapshotUnavailable', 'InventParent'),
    ):
        yield case('historical_attachment_provenance', 'attachment-' + name, {'sourceId': source, 'claim': claim})
    for name, q in (
        ('project-exact', artifact('ProjectAcquisition')),
        ('earliest-blob', artifact('ArchivePreImport')),
        ('dedup-blob', artifact('ArchiveDedup')),
        ('attachment-no-bytes', artifact('HistoricalAttachment')),
        ('archived-page-no-bytes', artifact('ArchivedParent2004')),
        ('unavailable', artifact('SnapshotUnavailable')),
        ('full-byte-fixture', artifact('FixtureArtifact', 'FullBytes', 32768, True)),
        ('same-size-different', artifact('FixtureArtifact', 'FullBytes', 32768, False)),
        ('partial', artifact('FixtureArtifact', 'PartialHash', 32768, True)),
        ('filename', artifact('FixtureArtifact', 'Filename')),
        ('digest-only', artifact('FixtureArtifact', 'DocumentedDigest', 32768, True)),
        ('size-only', artifact('FixtureArtifact', 'Size', 32768)),
        ('reject-factory', artifact('ProjectAcquisition', claim='FactoryOriginality')),
        ('reject-same-donor', artifact('ArchiveDedup', claim='SameDonor')),
        ('reject-mcu-size', artifact('ProjectAcquisition', claim='InferMcuFromSize')),
    ):
        yield case('rom_artifact_identity', 'artifact-' + name, q)
    for claim in ('Inspect', 'ArchiveDateIsReadDate', 'UploadDateIsReadDate', 'UnknownZoneIsUtc',
                  'LiteralHttpIsObserved', 'MirrorIsFirstPublication'):
        yield case('historical_chronology_consistency', 'chronology-recorded-' + claim,
                   {'mode': 'Recorded', 'events': [], 'claim': claim})
    for name, times in (
        ('consistent', ('2001-02-03T10:11:12', '2001-02-04T10:11:12', 'UTC')),
        ('contradiction', ('2001-02-05T10:11:12', '2001-02-04T10:11:12', 'UTC')),
        ('unknown-zone', ('2001-02-03T10:11', '2001-02-04T10:11:12', None)),
    ):
        first, second, zone = times
        yield case('historical_chronology_consistency', 'chronology-invented-' + name,
                   {'mode': 'Invented', 'claim': 'Inspect', 'events': [
                       {'event': 'AttachmentUpload', 'time': second, 'zone': 'UTC'},
                       {'event': 'PhysicalExtraction', 'time': first, 'zone': zone},
                   ]})


def extraction(source='FixtureExtractionA', **changes):
    base = dict(sourceId=source, recordType='OriginalExtractionRecord', unitId='UnitA',
                artifactId='FixtureImageA', imageIdentity='ExactFullByteMatch',
                custody='AuthenticatedCrossLink', method='InternalROM', originalitySourceId='None')
    return {**base, **changes}


def link(source, relation, start, end, custody='AuthenticatedCrossLink'):
    return dict(sourceId=source, relation=relation, fromSubject=start, toSubject=end, custody=custody)


def extraction_cases():
    base = extraction()
    document = {**base, 'sourceId': 'HistoricalAttachment', 'recordType': 'ContemporaneousAttachment',
                'unitId': None, 'artifactId': None, 'method': 'Unknown', 'custody': 'Missing'}
    for name, q in (
        ('historical', document),
        ('forged-primary', {**document, 'recordType': 'OriginalExtractionRecord'}),
        ('mirror', {**base, 'sourceId': 'FixtureExtractionMirrorA', 'recordType': 'SecondaryRepublication'}),
        ('fixture-full', base),
        ('external', {**base, 'method': 'ExternalEPROM'}),
        ('weak-hash', {**base, 'imageIdentity': 'PartialHashOnly'}),
        ('missing-bytes', {**base, 'imageIdentity': 'SourceUnavailable'}),
        ('different-bytes', {**base, 'imageIdentity': 'DifferentBytes'}),
        ('different-subject', {**base, 'unitId': 'UnitB'}),
        ('different-artifact', {**base, 'artifactId': 'FixtureImageB'}),
        ('missing-custody', {**base, 'custody': 'Missing'}),
        ('unknown-method', {**base, 'method': 'Unknown'}),
        ('copy', {**base, 'method': 'Copy'}),
        ('repacked', {**base, 'method': 'Repacked'}),
        ('checksum-factory', {**base, 'originalitySourceId': 'ArchiveChecksum'}),
        ('fixture-factory', {**base, 'originalitySourceId': 'FixtureFactoryA'}),
        ('fixture-modified', {**base, 'method': 'ModifiedMemory', 'originalitySourceId': 'FixtureModifiedA'}),
        ('fixture-originality-conflict', {**base, 'method': 'ModifiedMemory', 'originalitySourceId': 'FixtureFactoryA'}),
    ):
        yield case('extraction_session_provenance', 'read-' + name, q)
    label = link('FixtureLabelA', 'ECUToCaseLabel', 'UnitA', 'LabelA')
    board = link('FixtureBoardA', 'ECUToPCB', 'UnitA', 'BoardA')
    mcu = link('FixtureMcuA', 'PCBToMCUMarking', 'BoardA', 'MarkingA')
    for name, q, links in (
        ('fixture-complete', base, [mcu, label, board]),
        ('missing-mcu', base, [label, board]),
        ('missing-pcb', base, [label, mcu]),
        ('different-ecu', base, [label, link('FixtureBoardB', 'ECUToPCB', 'UnitB', 'BoardB'), mcu]),
        ('third-party', base, [label, {**board, 'sourceId': 'ThirdPartyPhoto'}, mcu]),
        ('duplicate', base, [label, label, board, mcu]),
        ('mismatched-board-link', base, [label, {**board, 'toSubject': 'BoardB'}, mcu]),
        ('real-extraction-absent', document, [label, board, mcu]),
    ):
        yield case('same_unit_donor_binding', 'donor-' + name, {'extraction': q, 'links': links})


def cases():
    yield from documentary_cases()
    yield from extraction_cases()
