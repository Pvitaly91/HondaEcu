"""Documentary extraction and same-unit joins without physical authority.

Reviewed archive records attest their own documentary roles only. The closed
invented records exercise eligibility, subject binding and custody obligations;
even a complete fixture chain leaves actual extraction, donor, MCU and factory
originality unknown. No caller-supplied authentication flag can add a source.
"""
from types import MappingProxyType


_BASE_SOURCES = MappingProxyType({
    'HistoricalAttachment': 'ContemporaneousAttachment',
    'ArchiveImport': 'ArchiveImportRecord',
    'ArchiveDedup': 'ByteIdenticalMirror',
    'ProjectAcquisition': 'ProjectAcquisitionRecord',
    'ThirdPartyPhoto': 'ThirdPartyExample',
    'CatalogueAttribution': 'CatalogueAttribution',
})
_EXTRACTION_SOURCES = MappingProxyType({
    **{name: (kind, None, None, False) for name, kind in _BASE_SOURCES.items()},
    'FixtureExtractionA': ('OriginalExtractionRecord', 'UnitA', 'FixtureImageA', True),
    'FixtureExtractionB': ('OriginalExtractionRecord', 'UnitB', 'FixtureImageB', True),
    'FixtureExtractionMirrorA': ('SecondaryRepublication', 'UnitA', 'FixtureImageA', True),
})
_RECORD_TYPES = frozenset(row[0] for row in _EXTRACTION_SOURCES.values())
_IMAGE_IDENTITIES = (
    'ExactFullByteMatch', 'MatchingArchivedBlob', 'MatchingDocumentedCryptographicDigest',
    'PartialHashOnly', 'SizeOnly', 'FilenameOnly', 'DifferentBytes', 'SourceUnavailable',
)
_CUSTODY = ('Missing', 'ClaimOnly', 'AuthenticatedCrossLink')
_METHODS = ('Unknown', 'InternalROM', 'ExternalEPROM', 'ModifiedMemory', 'Copy', 'Repacked')
_PHYSICAL_METHODS = ('InternalROM', 'ExternalEPROM', 'ModifiedMemory')
_ORIGINALITY = ('None', 'FixtureFactoryA', 'FixtureModifiedA', 'ArchiveChecksum')
_EXTRACTION_KEYS = (
    'sourceId', 'recordType', 'unitId', 'artifactId', 'imageIdentity',
    'custody', 'method', 'originalitySourceId',
)
_RELATIONS = ('ECUToCaseLabel', 'ECUToPCB', 'PCBToMCUMarking')
_SUBJECTS = (None, 'UnitA', 'UnitB', 'LabelA', 'LabelB', 'BoardA', 'BoardB',
             'MarkingA', 'MarkingB')
_LINK_SOURCES = MappingProxyType({
    'FixtureLabelA': ('ECUToCaseLabel', 'UnitA', 'LabelA', 'UnitA'),
    'FixtureLabelB': ('ECUToCaseLabel', 'UnitB', 'LabelB', 'UnitB'),
    'FixtureBoardA': ('ECUToPCB', 'UnitA', 'BoardA', 'UnitA'),
    'FixtureBoardB': ('ECUToPCB', 'UnitB', 'BoardB', 'UnitB'),
    'FixtureMcuA': ('PCBToMCUMarking', 'BoardA', 'MarkingA', 'UnitA'),
    'FixtureMcuB': ('PCBToMCUMarking', 'BoardB', 'MarkingB', 'UnitB'),
})
# These tuples are explicitly invented controls. Their resemblance to catalog
# labels is not a link to a photograph, real ECU, manufacturer part or revision.
_UNIT_FACTS = MappingProxyType({
    'UnitA': ('P28-A01', '1720', 'M66207-251'),
    'UnitB': ('P28-A02', '11F0', 'M66207-304'),
})


def _require(condition, reason):
    if condition is not True:
        raise ValueError(reason)


def _closed(value, keys, reason):
    _require(type(value) is dict and set(value) == set(keys), reason)


def _choice(value, choices, reason, nullable=False):
    _require((nullable and value is None)
             or (type(value) is str and value in choices), reason)


def _unknown_actual():
    return {
        'actualOriginalPhysicalExtraction': None, 'actualEcuIdentity': None,
        'actualMcuIdentity': None, 'factoryOriginality': None,
        'actualHardwareObservation': None, 'actualSiliconConfirmed': False,
        'executionAdmission': False, 'firmwareReady': False,
    }


def _validate_extraction(query):
    _closed(query, _EXTRACTION_KEYS, 'ClosedExtractionQueryRequired')
    _choice(query['sourceId'], _EXTRACTION_SOURCES, 'KnownExtractionSourceRequired')
    _choice(query['recordType'], _RECORD_TYPES, 'ClosedExtractionRecordTypeRequired')
    _choice(query['unitId'], ('UnitA', 'UnitB'), 'ClosedExtractionUnitRequired', nullable=True)
    _choice(query['artifactId'], ('StudiedRom', 'FixtureImageA', 'FixtureImageB'),
            'ClosedExtractionArtifactRequired', nullable=True)
    _choice(query['imageIdentity'], _IMAGE_IDENTITIES, 'ClosedImageIdentityRequired')
    _choice(query['custody'], _CUSTODY, 'ClosedExtractionCustodyRequired')
    _choice(query['method'], _METHODS, 'ClosedExtractionMethodRequired')
    _choice(query['originalitySourceId'], _ORIGINALITY, 'ClosedOriginalitySourceRequired')


def _session_classification(query, source, primary, identity_supported):
    kind, unit, artifact, fixture = source
    if query['recordType'] != kind:
        return 'RefusedEvidencePromotion'
    if not fixture:
        return 'OriginalExtractionRecordNotEstablished'
    if not primary:
        return 'DerivativeCannotEstablishExtraction'
    if query['imageIdentity'] == 'DifferentBytes':
        return 'ImageIdentityMismatch'
    if query['unitId'] != unit or query['artifactId'] != artifact:
        return 'SourceSubjectOrArtifactMismatch'
    if not identity_supported:
        return 'FullImageBindingUnestablished'
    if query['custody'] != 'AuthenticatedCrossLink':
        return 'ExtractionCustodyUnestablished'
    if query['method'] == 'Unknown':
        return 'ExtractionMethodUnestablished'
    if query['method'] not in _PHYSICAL_METHODS:
        return 'NonPhysicalArtifactProduction'
    return 'FixtureExtractionChainOnly'


def _originality(query, eligible):
    source = query['originalitySourceId']
    if source == 'None':
        return 'Unknown', 'Unestablished'
    if source == 'ArchiveChecksum':
        return 'Unknown', 'RefusedChecksumPromotion'
    if not eligible or query['unitId'] != 'UnitA' or query['artifactId'] != 'FixtureImageA':
        return 'Unknown', 'RefusedUnboundOriginalitySource'
    if source == 'FixtureModifiedA':
        return 'ModifiedFirmware', 'FixtureOnly'
    if query['method'] == 'ModifiedMemory':
        return 'ConflictingClaims', 'FixtureConflict'
    return 'FactoryUnmodifiedFirmware', 'FixtureOnly'


def extraction_session_provenance(query):
    """Validate the source role, whole-image link and extraction-unit custody.

    Full-byte comparison, archived-blob identity and a documented cryptographic
    digest retain distinct names. None proves a physical donor by itself. The
    registry contains no authenticated physical extraction of the studied ROM.
    """
    _validate_extraction(query)
    source = _EXTRACTION_SOURCES[query['sourceId']]
    kind, unit, artifact, fixture = source
    supported = query['recordType'] == kind
    primary = fixture and supported and kind == 'OriginalExtractionRecord'
    identity_supported = query['imageIdentity'] in _IMAGE_IDENTITIES[:3]
    classification = _session_classification(query, source, primary, identity_supported)
    eligible = classification == 'FixtureExtractionChainOnly'
    obligations = (
        ('OriginalExtractionRecord', primary),
        ('SourceSubjectBinding', primary and query['unitId'] == unit),
        ('ExtractionImageBinding', primary and query['artifactId'] == artifact),
        ('FullImageIdentity', identity_supported),
        ('AuthenticatedExtractionCustody', primary and query['custody'] == 'AuthenticatedCrossLink'),
        ('PhysicalReadMethod', primary and query['method'] in _PHYSICAL_METHODS),
    )
    missing = [name for name, established in obligations if not established]
    if fixture:
        missing.append('AuthenticNonFixtureExtractionRecord')
    missing.append('IndependentFactoryOriginalityEvidence')
    originality, originality_status = _originality(query, eligible)
    edges = ['ExtractionRecordToUnit', 'ExtractionRecordToImage', 'ImageToStudiedRom'] if eligible else []
    return {
        'classification': classification, 'sourceId': query['sourceId'],
        'sourceClass': 'InventedPolicyFixture' if fixture else 'ReviewedDocumentary',
        'recordType': query['recordType'], 'recordTypeSupported': supported,
        'conditionalExtractionEstablished': eligible,
        'conditionalUnitId': query['unitId'] if eligible else None,
        'conditionalArtifactId': query['artifactId'] if eligible else None,
        'imageIdentity': query['imageIdentity'], 'identitySupportsFullLink': identity_supported,
        'method': query['method'], 'conditionalFactoryOriginality': originality,
        'originalityEvidenceStatus': originality_status,
        'acceptedEdges': edges, 'rejectedEdges': [] if eligible else [classification],
        'missingObligations': missing, **_unknown_actual(),
    }


def _validate_links(links):
    _require(type(links) is list and len(links) <= 8, 'BoundedSameUnitLinksRequired')
    for link in links:
        _closed(link, ('sourceId', 'relation', 'fromSubject', 'toSubject', 'custody'),
                'ClosedSameUnitLinkRequired')
        _choice(link['sourceId'], (*_BASE_SOURCES, *_LINK_SOURCES), 'KnownSameUnitSourceRequired')
        _choice(link['relation'], _RELATIONS, 'ClosedSameUnitRelationRequired')
        _choice(link['fromSubject'], _SUBJECTS, 'ClosedFromSubjectRequired', nullable=True)
        _choice(link['toSubject'], _SUBJECTS, 'ClosedToSubjectRequired', nullable=True)
        _choice(link['custody'], _CUSTODY, 'ClosedSameUnitCustodyRequired')


def _link_status(link, extraction, seen):
    source_id = link['sourceId']
    if source_id in _BASE_SOURCES:
        return 'SourceCannotBindStudiedUnit'
    if not extraction['conditionalExtractionEstablished']:
        return 'ExtractionRootUnestablished'
    relation, before, after, unit = _LINK_SOURCES[source_id]
    if (link['relation'], link['fromSubject'], link['toSubject']) != (relation, before, after):
        return 'SourceClaimMismatch'
    if unit != extraction['conditionalUnitId']:
        return 'DifferentPhysicalSubject'
    if link['custody'] != 'AuthenticatedCrossLink':
        return 'LinkCustodyUnestablished'
    if source_id in seen:
        return 'DependentDuplicate'
    seen.add(source_id)
    return 'ConditionalFixtureLink'


def same_unit_donor_binding(query):
    """Join independently scoped links through one extraction's unit and PCB.

    MCU evidence must connect to the PCB already linked to the same fixture
    unit. Input order cannot manufacture a missing edge, a duplicate source
    cannot supply a second role, and unrelated records remain explicit refusals.
    A complete result remains an invented policy control, never actual identity.
    """
    _closed(query, ('extraction', 'links'), 'ClosedDonorBindingQueryRequired')
    _validate_links(query['links'])
    extraction = extraction_session_provenance(query['extraction'])
    seen, results = set(), []
    for index, link in enumerate(query['links']):
        results.append({
            'index': index, 'sourceId': link['sourceId'], 'relation': link['relation'],
            'status': _link_status(link, extraction, seen),
        })
    board_joined = any(row['relation'] == 'ECUToPCB' and row['status'] == 'ConditionalFixtureLink'
                       for row in results)
    if not board_joined:
        for row in results:
            if row['relation'] == 'PCBToMCUMarking' and row['status'] == 'ConditionalFixtureLink':
                row['status'] = 'MissingPcbCustodyEdge'
    joined = {row['relation'] for row in results if row['status'] == 'ConditionalFixtureLink'}
    complete = extraction['conditionalExtractionEstablished'] and joined == set(_RELATIONS)
    facts = _UNIT_FACTS.get(extraction['conditionalUnitId'], (None, None, None))
    missing = list(extraction['missingObligations'])
    missing.extend(obligation for relation, obligation in zip(
        _RELATIONS, ('SameUnitCaseLabel', 'SameUnitPcb', 'SameUnitMcuMarking'))
        if relation not in joined)
    missing.append('AuthenticSameUnitCustody')
    return {
        'classification': 'FixtureSameUnitChainOnly' if complete else 'SameUnitChainUnestablished',
        'extraction': extraction, 'conditionalSameUnitChain': complete,
        'conditionalUnitId': extraction['conditionalUnitId'],
        'conditionalCaseLabel': facts[0] if 'ECUToCaseLabel' in joined else None,
        'conditionalPcb': facts[1] if 'ECUToPCB' in joined else None,
        'conditionalMcuMarking': facts[2] if 'PCBToMCUMarking' in joined else None,
        'linkResults': results,
        'acceptedEdges': [*extraction['acceptedEdges'], *(relation for relation in _RELATIONS if relation in joined)],
        'rejectedEdges': [{'index': row['index'], 'reason': row['status']} for row in results
                          if row['status'] != 'ConditionalFixtureLink'],
        'missingObligations': missing, **_unknown_actual(),
    }
