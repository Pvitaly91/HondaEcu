"""Byte identity and reviewed metadata are separate from hardware semantics."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path


def documents():
    return deepcopy(json.loads(Path(__file__).with_name('contract.json').read_bytes())['documents'])


def verify_bytes(raw, expected_sha256, expected_bytes):
    if (type(raw) is not bytes or type(expected_bytes) is not int or expected_bytes < 1
            or type(expected_sha256) is not str or len(expected_sha256) != 64
            or any(c not in '0123456789abcdef' for c in expected_sha256)):
        raise ValueError('ExplicitByteIdentityRequired')
    if len(raw) != expected_bytes or sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('DocumentBytesDiffer')
    return {'byteIdentityVerified': True, 'manufacturerSemanticsAuthenticated': False,
            'executionAdmission': False}


def validate_document(record, raw=None):
    if type(record) is not dict or type(record.get('sourceId')) is not str:
        raise ValueError('ClosedDocumentRecordRequired')
    registry = {r['sourceId']: r for r in documents()}
    expected = registry.get(record['sourceId'])
    if expected is None or record != expected:
        raise ValueError('UnreviewedDocumentMetadataOrClaim')
    result = {'byteIdentityVerified': False, 'manufacturerSemanticsAuthenticated': False,
              'executionAdmission': False}
    if raw is not None:
        result = verify_bytes(raw, expected['sha256'], expected['bytes'])
    return {'sourceId': expected['sourceId'], **result}
