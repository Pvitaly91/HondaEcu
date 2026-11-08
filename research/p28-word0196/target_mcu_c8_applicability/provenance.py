"""Classify archive provenance and documentary relations within reviewed sources."""

from itertools import combinations


_QUERY_KEYS = {'archiveBinding', 'sourceIds', 'requestedConclusion'}
_ARCHIVE_BINDINGS = {'ExactAuthenticatedArchive', 'ByteIdentityMismatch', 'FilenameOnly', 'Unknown'}
_CONCLUSIONS = {
    'ProjectArchiveAcquisition', 'OriginalPhysicalExtraction', 'StudiedDonor',
    'FactoryOriginality', 'PhysicalExtractionDate', 'WitnessComparison',
}
# The import and dedup metadata refer to the same archive lineage as M1a's
# acquisition. Historical attachment metadata is a separate documentary scope.
_DOCUMENTARY_ORIGINS = {
    'M1aAcquisition': 'ProjectArchiveLineage',
    'ArchiveImport': 'ProjectArchiveLineage',
    'ArchiveDedup': 'ProjectArchiveLineage',
    'HistoricalAttachment': 'HistoricalAttachmentMetadata',
    'A01Photo': 'CommercialA01Subject',
    'A02Photo': 'CommercialA02Subject',
    'HALoggedList': 'ShopObservations',
    'RetailFitment': 'RetailFitmentCatalogue',
}
# These premises are solely controls for exclusivity and independence on the
# same invented unit. Documentary input cannot supply or override these facts.
_FIXTURE_CLAIMS = {
    'FixtureSameUnitA': ('FixtureOriginA', 'MarkingA'),
    'FixtureSameUnitMirror': ('FixtureOriginA', 'MarkingA'),
    'FixtureSameUnitB': ('FixtureOriginB', 'MarkingB'),
    'FixtureIndependentAgreement': ('FixtureOriginC', 'MarkingA'),
}
_MISSING_PROOF = (
    'OriginalExtractionRecord', 'SameUnitLabelPcbMcuCustody',
    'AcquiredImageToExtractionByteBinding', 'IndependentFactoryOriginalityEvidence',
)


def _pair_relation(left, right, origins, is_fixture):
    if origins[left] == origins[right]:
        return 'DependentDuplicate'
    if is_fixture:
        if _FIXTURE_CLAIMS[left][1] == _FIXTURE_CLAIMS[right][1]:
            return 'FixtureIndependentSameUnitAgreement'
        return 'FixtureExclusiveSameUnitConflict'
    if {left, right} == {'A01Photo', 'A02Photo'}:
        return 'DifferentPhysicalSubjects'
    return 'DifferentDocumentaryScopes'


def _classification(binding, conclusion, project_acquisition, is_fixture):
    if is_fixture:
        if conclusion == 'WitnessComparison':
            return 'FixtureWitnessComparisonOnly'
        return 'FixtureCannotEstablishActualProvenance'
    if binding == 'ByteIdentityMismatch':
        return 'ArchiveByteIdentityMismatch'
    if binding == 'FilenameOnly':
        return 'FilenameOnlyIdentityRefused'
    if conclusion == 'WitnessComparison':
        return 'DocumentaryWitnessComparisonOnly'
    if conclusion == 'ProjectArchiveAcquisition':
        return 'ProjectArchiveAcquisitionOnly' if project_acquisition else 'ArchiveAcquisitionNotEstablished'
    return f'{conclusion}NotEstablished'


def rom_to_hardware_provenance(query):
    """Evaluate a closed documentary query under the frozen M2cm source bindings.

    ``archiveBinding`` is the result of the admitted archive byte-identity
    check in this source scope. The model never accepts caller-supplied
    documentary records, identity strings, physical assertions, or ROM bytes.
    The count measures distinct documentary origins across their own scopes.
    """
    if type(query) is not dict or set(query) != _QUERY_KEYS:
        raise ValueError('ClosedProvenanceQueryRequired')
    binding = query['archiveBinding']
    if type(binding) is not str or binding not in _ARCHIVE_BINDINGS:
        raise ValueError('UnknownArchiveBinding')
    conclusion = query['requestedConclusion']
    if type(conclusion) is not str or conclusion not in _CONCLUSIONS:
        raise ValueError('UnknownProvenanceConclusion')
    sources = query['sourceIds']
    if (type(sources) is not list
            or any(type(source) is not str or (
                source not in _DOCUMENTARY_ORIGINS and source not in _FIXTURE_CLAIMS
            ) for source in sources)
            or len(set(sources)) != len(sources)):
        raise ValueError('ClosedDocumentarySourceIdsRequired')
    is_fixture = any(source in _FIXTURE_CLAIMS for source in sources)
    if is_fixture and any(source in _DOCUMENTARY_ORIGINS for source in sources):
        raise ValueError('MixedFixtureAndDocumentarySources')
    if is_fixture:
        origins = {source: _FIXTURE_CLAIMS[source][0] for source in sources}
    else:
        origins = {source: _DOCUMENTARY_ORIGINS[source] for source in sources}
    project_acquisition = binding == 'ExactAuthenticatedArchive' and 'M1aAcquisition' in origins

    return {
        'classification': _classification(binding, conclusion, project_acquisition, is_fixture),
        'projectArchiveAcquisition': project_acquisition,
        'originalPhysicalExtraction': None,
        'studiedDonor': None,
        'factoryOriginality': None,
        'physicalExtractionDate': None,
        'independentWitnessCount': len(set(origins.values())),
        'sourceCount': len(sources),
        'pairRelations': [
            {'left': left, 'right': right, 'relation': _pair_relation(left, right, origins, is_fixture)}
            for left, right in combinations(sorted(sources), 2)
        ],
        'missingProof': list(_MISSING_PROOF),
        'actualHardwareConfirmed': False,
        'actualMcuIdentity': None,
        'executionAdmission': False,
        'firmwareReady': False,
    }
