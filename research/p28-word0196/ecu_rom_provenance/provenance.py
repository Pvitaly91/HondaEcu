"""Classify bounded documentary relations without admitting actual hardware."""
from hashlib import sha256

KINDS = {
    'ProjectArchiveAcquisition': ('M1aPublicReport', 'ProjectAcquisitionOnly'),
    'CatalogueAssociation': ('ArchiveCatalogue', 'NonExclusiveCatalogueAssociation'),
    'ShopLoggedUnit': ('HALoggedList', 'UnlinkedShopReportedUnit'),
    'UnlinkedDrawing': ('BomarcSchematic', 'UnlinkedThirdPartyDrawing'),
    'UnlinkedPhotoA01': ('EbayA01Photo', 'UnlinkedVisibleCommercialUnit'),
    'UnlinkedPhotoA02': ('DGTuneA02Photo', 'UnlinkedVisibleCommercialUnit'),
    'StandardManufacturer': ('JapaneseY3', 'StandardNamedDeviceOnly'),
    'RomLength': ('M1aPublicReport', 'PayloadPropertyOnly'),
    'Checksum': ('M1fPublicReport', 'PayloadPropertyOnly'),
    'IsaCompatibility': ('ISA1991', 'ReviewedStandardIsaOnly'),
}
FIELDS = {'kind', 'sourceId', 'scope', 'actualEcuId', 'sameUnitLink', 'romExtractionLinked',
          'maskRevisionConfirmed', 'safeStackConfirmed', 'rxAckConfirmed', 'actualHardwareObservation'}
CLAIM_FIELDS = {'subject', 'property', 'value', 'unitScope', 'exclusive', 'independenceGroup'}


def verify_bytes(raw, digest, count):
    if (type(raw) is not bytes or type(count) is not int or count < 1
            or type(digest) is not str or len(digest) != 64
            or any(c not in '0123456789abcdef' for c in digest)):
        raise ValueError('ExplicitTypedBytesSizeHashRequired')
    if len(raw) != count or sha256(raw).hexdigest() != digest:
        raise ValueError('DocumentByteIdentityMismatch')
    return {'byteIdentityVerified': True, 'hardwareAuthenticityEstablished': False,
            'actualSiliconConfirmed': False, 'executionAdmission': False}


def classify_evidence(record):
    if type(record) is not dict or set(record) != FIELDS:
        raise ValueError('ClosedDocumentaryEvidenceRecordRequired')
    kind = record['kind']
    if type(kind) is not str or kind not in KINDS:
        raise ValueError('NoPhysicalOrHostAssertionAuthority')
    source, result = KINDS[kind]
    if record['sourceId'] != source or record['scope'] != kind:
        raise ValueError('SourceKindScopeRelationshipRequired')
    if (record['actualEcuId'] is not None or record['actualHardwareObservation'] is not None
            or record['sameUnitLink'] is not None
            or any(record[key] is not False for key in (
                'romExtractionLinked', 'maskRevisionConfirmed', 'safeStackConfirmed', 'rxAckConfirmed'))):
        raise ValueError('UnobservedSameUnitOrPeripheralOwnerPromotion')
    return {'evidenceClass': result, 'projectAcquisitionScopeOnly': kind == 'ProjectArchiveAcquisition',
            'privateSourceBytesVerifiedByThisClassifier': False,
            'actualSiliconConfirmed': False, 'executionAdmission': False, 'firmwareReady': False}


def compare_claims(left, right):
    """Exclusivity is a premise in controls, not proof of authentic observations."""
    for claim in (left, right):
        if (type(claim) is not dict or set(claim) != CLAIM_FIELDS
                or any(type(claim[k]) is not str or not claim[k] for k in (
                    'subject', 'property', 'value', 'independenceGroup'))
                or type(claim['exclusive']) is not bool
                or not (claim['unitScope'] is None or type(claim['unitScope']) is str and claim['unitScope'])):
            raise ValueError('TypedScopedAttributionClaimRequired')
    if left['subject'] != right['subject'] or left['property'] != right['property']:
        relation = 'DifferentSubjectsOrProperties'
    elif left['value'] == right['value']:
        relation = 'SameValue_NotIndependentIdentityProof'
    elif (left['unitScope'] is not None and left['unitScope'] == right['unitScope']
          and left['exclusive'] and right['exclusive']
          and left['independenceGroup'] != right['independenceGroup']):
        relation = 'ExclusiveSameUnitConflict_UnderDeclaredPremises'
    elif left['independenceGroup'] == right['independenceGroup']:
        relation = 'DependentSourceDifference_NotIndependentConfirmation'
    else:
        relation = 'NonExclusiveAttributionDifference'
    return {'relation': relation, 'authenticityEstablishedByComparison': False,
            'studiedUnitIdentityEstablished': False, 'executionAdmission': False}
