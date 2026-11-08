"""Independent candidate oracle from the reviewed interface and M2cm reference."""

from itertools import combinations

from ecu_rom_provenance.reference_oracle import expected_compatibility


_EXAMPLES = {
    'DGTuneA02Photo': ('DGTuneCommercialExample', 'ThirdPartyExample', ('P28-A02',), '11F0', 'M66207-304', None),
    'EbayA01Photo': ('EbayCommercialExample', 'ThirdPartyExample', ('P28-A01',), '1720', 'M66207-251', None),
    'BomarcSchematic': ('BomarcDrawingExample', 'SecondaryTechnicalClaim', ('P28-A51',), '1720',
                        'MSM66207-251', 'MSM66207'),
    'Unknown': (None, 'Unknown', (), None, None, None),
}
_SHOP_LABELS = {'251': ('P28-A01', 'P28-A51'), '304': ('P28-A02', 'P28-A52')}
_CANDIDATE_FIELDS = ('ecuCandidate', 'pcbCandidate', 'literalMarking', 'catalogMcuCandidate')
_SCOPE_LIMITS = {
    'sameUnitBound': False,
    'actualSiliconConfirmed': False,
    'actualMcuIdentity': None,
    'peripheralApplicability': 'Unestablished',
    'c8IsaApplicability': 'C8PrimaryConflictUnresolved',
    'executionAdmission': False,
    'firmwareReady': False,
}


def _field_status(value, applicable_values):
    if value == 'Unknown':
        return 'CandidateUnknown'
    if not applicable_values:
        return 'NotStatedBySource'
    if value in applicable_values:
        return 'MatchesSelectedSource'
    return 'DiffersFromSelectedSource_NotSameUnitConflict'


def expected_attribution(query):
    source_id = query['sourceId']
    _, separator, suffix = query['literalMarking'].partition('-')
    if source_id == 'HALoggedList':
        subject, evidence_class = 'HALoggedUnits', 'SecondaryTechnicalClaim'
        labels = _SHOP_LABELS.get(suffix, ())
        pcb = literal = catalog = None
    else:
        subject, evidence_class, labels, pcb, literal, catalog = _EXAMPLES[source_id]
    applicable_values = (labels, *((value,) if value is not None else () for value in (pcb, literal, catalog)))
    comparisons = [
        {'field': field, 'status': _field_status(query[field], values)}
        for field, values in zip(_CANDIDATE_FIELDS, applicable_values, strict=True)
    ]
    statuses = {row['status'] for row in comparisons}
    if 'DiffersFromSelectedSource_NotSameUnitConflict' in statuses:
        classification = 'DifferentCandidateFromSelectedExample'
    elif 'MatchesSelectedSource' in statuses:
        classification = 'ThirdPartyCandidateAssociation'
    else:
        classification = 'CandidateAttributionUnestablished'
    promotion = query['requestedPromotion']
    rejected_edges = [] if promotion == 'None' else [promotion]
    return {
        'classification': classification,
        'candidate': {field: query[field] for field in _CANDIDATE_FIELDS},
        'source': {'sourceId': source_id, 'sourceSubject': subject, 'evidenceClass': evidence_class,
                   'ecuLabels': list(labels), 'pcbRevision': pcb, 'literalMarking': literal, 'catalogMcuPart': catalog},
        'fieldComparisons': comparisons,
        'literalCodeToken': suffix if separator else None,
        'manufacturerAliasEstablished': False,
        'customerCodeMeaning': 'ExactMeaningUnestablished',
        'package': None,
        'siliconRevision': None,
        'requestedPromotion': promotion,
        'promotionDecision': 'Rejected' if rejected_edges else 'NotRequested',
        'rejectedEdges': rejected_edges,
        'unresolvedConstraints': [
            'OriginalExtractionToSameUnit', 'ManufacturerLiteralAlias', 'ExactCustomerCodeMeaning',
            'SiliconRevision', 'BoardProgramAndDataSelection', 'ApplicableC8Clarification',
        ],
        **_SCOPE_LIMITS,
    }


def _byte_region(space, address, inherited):
    if space == 'PROGRAM':
        return ('InternalProgram' if address < inherited['standardInternalProgramBytes'] else 'ExternalProgram')
    if address < 0x80:
        return 'Sfr'
    if address < 0xC0:
        return 'PointingRegisterRam'
    if address < 0x80 + inherited['standardTotalInternalDataBytes']:
        return 'InternalRam'
    return 'ExternalData'


def _access_result(index, access, addresses, inherited, program_premise, data_premise, ea_low):
    space = access['space']
    normal = []
    for address in addresses:
        region = _byte_region(space, address, inherited)
        if normal and normal[-1]['region'] == region:
            normal[-1]['endExclusive'] = address + 1
        else:
            normal.append({'start': address, 'endExclusive': address + 1, 'region': region})
    regions = {segment['region'] for segment in normal}
    hypothetical = None
    if space == 'PROGRAM':
        if ea_low:
            hypothetical = [{'start': addresses.start, 'endExclusive': addresses.stop, 'region': 'ExternalProgram'}]
        if program_premise == 'InternalOnly32K':
            fit = ('ConflictsWithInternalOnlyPremise' if 'ExternalProgram' in regions else
                   'FitsStandardInternalProgram_PremiseOnly')
        elif program_premise == 'ExternalProgramSupported':
            fit = ('ConditionalExternalProgram_SelectionHypothesisOnly' if ea_low else
                   'DocumentedCapacityOnly_SelectionUnknown')
        else:
            fit = 'Unknown'
    elif 'Sfr' in regions:
        fit = 'SfrApplicabilityUnestablished'
    elif data_premise == 'Unknown':
        fit = 'Unknown'
    elif 'ExternalData' in regions:
        fit = ('DocumentedExternalData_CircuitUnknown' if data_premise == 'ExternalDataDocumented' else
               'ExternalDataProofRequired')
    else:
        fit = 'FitsStandardInternalData_PremiseOnly'
    return {'index': index, **access, 'normalMapSegments': normal,
            'hypotheticalEaLowSegments': hypothetical, 'premiseFit': fit}


def expected_memory(query):
    ecu, mcu, program_premise = (query[key] for key in ('ecuCandidate', 'mcuCandidate', 'programPremise'))
    inherited = expected_compatibility(ecu, mcu, program_premise)
    data_premise = query['dataPremise']
    selection = query['selectionEvidence']
    ea_low = selection == 'HypotheticalEaLow'
    selection_qualifications = {
        'HypotheticalEaLow': 'HypothesisOnly_NotObservedEa',
        'SocketVisible': 'VisibleComponentOnly_NotElectricalOrActiveSelection',
        'SchematicOnly': 'DrawingOnly_NotSameUnitActiveSelection',
        'Unknown': 'ActiveSelectionUnknown',
    }
    conflicts = []
    if ea_low and program_premise == 'InternalOnly32K':
        conflicts.append('InternalOnlyAndExternalEaLowAreIncompatiblePremises')
    accesses = query['accesses']
    addresses = [range(access['address'], access['address'] + access['widthBytes']) for access in accesses]
    access_results = [
        _access_result(index, access, span, inherited, program_premise, data_premise, ea_low)
        for index, (access, span) in enumerate(zip(accesses, addresses, strict=True))
    ]
    same_space = []
    cross_space = []
    for left, right in combinations(range(len(accesses)), 2):
        intersection = set(addresses[left]).intersection(addresses[right])
        if intersection:
            overlaps = same_space if accesses[left]['space'] == accesses[right]['space'] else cross_space
            overlaps.append({'leftIndex': left, 'rightIndex': right, 'start': min(intersection),
                             'endExclusive': max(intersection) + 1})
    constraints = ['SameUnitExtractionCustody', 'ApplicablePartAndRevision', 'ProgramEaPsenDecode',
                   'DataRdWrDecode', 'ActualRamAndStackOwnership', 'C8PrimaryConflictUnresolved']
    if mcu.startswith('MSM66P'):
        constraints.append('OtpProgrammingAndOperatingMode')
    return {
        'classification': 'ContradictoryDeclaredPremises' if conflicts else inherited['status'],
        'inheritedM2cmRow': inherited,
        'candidateId': '/'.join((ecu, mcu, program_premise)),
        'dataPremise': data_premise,
        'selectionEvidence': selection,
        'selectionQualification': selection_qualifications[selection],
        'accesses': access_results,
        'sameSpaceOverlaps': same_space,
        'crossSpaceNumericOverlaps': cross_space,
        'premiseConflicts': conflicts,
        'unresolvedConstraints': constraints,
        'actualProgramSelection': None,
        'actualDataMapping': None,
        'stackApplicability': 'Unestablished',
        **_SCOPE_LIMITS,
    }
