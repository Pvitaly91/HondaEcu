"""Verify scope relationships without converting documentary locators to hardware."""
from hashlib import sha256

MODELS = frozenset(('MSM66201', 'MSM66207', 'MSM66P201', 'MSM66P207'))
STANDARD_TARGETS = {
    'JapaneseY3': MODELS,
    'EnglishY4': MODELS,
    'ISA1991': frozenset(('MSM66201',)),
    'UserIncomplete': frozenset(('MSM66201', 'MSM66207')),
}
FIELDS = frozenset(('sourceId', 'scope', 'targetModel', 'actualEcuId', 'donorLinked',
                    'romCustodyLinked', 'maskRevisionConfirmed', 'actualHardwareObservation'))


def verify_bytes(raw, digest, count):
    if (type(raw) is not bytes or type(count) is not int or count < 1
            or type(digest) is not str or len(digest) != 64
            or any(c not in '0123456789abcdef' for c in digest)):
        raise ValueError('ExplicitByteIdentityRequired')
    if len(raw) != count or sha256(raw).hexdigest() != digest:
        raise ValueError('SourceBytesDiffer')
    return {'byteIdentityVerified': True, 'actualEcuConfirmed': False, 'executionAdmission': False}


def validate_claim(kind, record):
    if type(kind) is not str or type(record) is not dict or set(record) != FIELDS:
        raise ValueError('ClosedDocumentaryProvenanceRecordRequired')
    if (record['actualEcuId'] is not None or record['actualHardwareObservation'] is not None
            or any(record[k] is not False for k in (
            'donorLinked', 'romCustodyLinked', 'maskRevisionConfirmed'))):
        raise ValueError('NoActualUnitOrHostSuppliedOwnershipAuthority')
    if kind == 'StandardDeviceProperty':
        if (type(record['sourceId']) is not str or record['sourceId'] not in STANDARD_TARGETS
                or record['scope'] != 'StandardDocument' or type(record['targetModel']) is not str
                or record['targetModel'] not in STANDARD_TARGETS[record['sourceId']]):
            raise ValueError('NamedStandardSourceScopeRequired')
        classification = 'StandardDocumentOnly'
    elif kind == 'ArchiveAssociation':
        if (record['sourceId'] != 'ArchiveCatalogue' or record['scope'] != 'ArchiveCatalogue'
                or record['targetModel'] is not None):
            raise ValueError('ArchiveAssociationCannotIdentifyChip')
        classification = 'ArchiveAssociationOnly'
    elif kind == 'ThirdPartyBoardObservation':
        if (record['sourceId'] != 'BomarcSchematic' or record['scope'] != 'UnlinkedThirdPartyBoard'
                or record['targetModel'] != 'MSM66207'):
            raise ValueError('DrawingScopedBoardObservationRequired')
        classification = 'UnlinkedBoardObservation'
    else:
        raise ValueError('ActualHardwareIdentityNotAdmittedByM2cl')
    return {'classification': classification, 'actualEcuConfirmed': False, 'executionAdmission': False}
