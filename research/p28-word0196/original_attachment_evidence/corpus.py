"""Narrow payload, digest, and join cases. No payload or digest bytes."""
from copy import deepcopy

from prearchive_extraction_custody.corpus import extraction_cases


def _case(operation, name, query):
    return {'id': name, 'operation': operation, 'input': deepcopy(query)}


def cases():
    for source in (
        'HistoricalMetadata', 'KnownLaterBlob', 'HistoricalCaptureJune2004', 'HistoricalCaptureSeptember2004',
        'FixtureOriginalExact', 'FixtureConflictBytes',
        'FixtureWrongParent', 'FixtureMirrorEqual', 'FixtureTruncated', 'FixtureTransformed',
        'FixtureIndexOnly', 'FixtureUnavailable',
    ):
        yield _case('historical_attachment_payload_identity', 'payload-' + source, {'sourceId': source})
    for source in (
        'HistoricalMetadata', 'KnownLaterDigest', 'ArchiveCaptureDigest', 'FixtureOriginalDigest', 'FixtureConflictDigest',
        'FixtureLaterDigest', 'FixtureCopiedDigest', 'FixtureUnknownDigest', 'FixturePartialDigest',
        'FixtureLegacyDigest', 'FixtureUnboundDigest',
    ):
        yield _case('historical_digest_authenticity', 'digest-' + source, {'sourceId': source})
    for name, sources, claim in (
        ('reviewed-sources', ('HistoricalMetadata', 'KnownLaterBlob', 'KnownLaterDigest'), 'Inspect'),
        ('restored-captures', ('HistoricalCaptureJune2004', 'HistoricalCaptureSeptember2004',
                               'ArchiveCaptureDigest', 'KnownLaterBlob'), 'Inspect'),
        ('archive-digest-alone', ('ArchiveCaptureDigest', 'KnownLaterDigest'), 'Inspect'),
        ('unavailable-fixture', ('FixtureUnavailable',), 'Inspect'),
        ('conditional-exact', ('FixtureOriginalExact',), 'Inspect'),
        ('conditional-digest', ('FixtureOriginalDigest',), 'Inspect'),
        ('qualified-both', ('FixtureOriginalDigest', 'FixtureOriginalExact'), 'Inspect'),
        ('conflict', ('FixtureOriginalExact', 'FixtureConflictDigest'), 'Inspect'),
        ('later-only', ('FixtureMirrorEqual', 'FixtureMirrorDuplicate', 'FixtureLaterDigest'), 'Inspect'),
        ('wrong-parent', ('FixtureWrongParent', 'FixtureUnboundDigest'), 'Inspect'),
        ('weak', ('FixturePartialDigest', 'FixtureIndexOnly', 'FixtureTruncated'), 'Inspect'),
        ('force-donor', ('KnownLaterBlob',), 'AssertDonor'),
        ('force-factory', ('FixtureOriginalExact',), 'AssertFactoryOriginality'),
        ('force-c8', ('FixtureOriginalDigest',), 'AssertC8'),
        ('force-execution', ('FixtureOriginalExact',), 'AuthorizeExecution'),
    ):
        yield _case('attachment_to_rom_blob_proof', 'join-' + name, {'sourceIds': list(sources), 'claim': claim})
    physical = {row['id']: row['input'] for row in extraction_cases() if row['operation'] == 'same_unit_donor_binding'}
    for name, sources, donor in (
        ('reviewed', ('HistoricalCaptureJune2004', 'HistoricalCaptureSeptember2004',
                      'ArchiveCaptureDigest', 'KnownLaterBlob'), 'real-extraction-absent'),
        ('digital-fixture-missing-donor', ('FixtureOriginalExact',), 'real-extraction-absent'),
        ('digital-fixture-complete-donor', ('FixtureOriginalDigest',), 'fixture-complete'),
        ('digital-fixture-missing-mcu', ('FixtureOriginalExact',), 'missing-mcu'),
        ('digital-fixture-wrong-donor', ('FixtureOriginalExact',), 'different-ecu'),
        ('digital-fixture-conflict', ('FixtureOriginalExact', 'FixtureConflictDigest'), 'fixture-complete'),
    ):
        yield _case('documentary_evidence_status', 'status-' + name, {
            'digital': {'sourceIds': list(sources), 'claim': 'Inspect'},
            'physical': physical['donor-' + donor],
        })
