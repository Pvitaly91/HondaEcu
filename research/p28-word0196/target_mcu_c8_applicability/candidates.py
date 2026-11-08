"""Source-scoped candidate and address relations; never hardware admission.

The inherited M2cm capacity row is returned unchanged. New interval relations
describe explicit standard-device premises, not the physical studied board.
The source facts are the frozen M2cm commercial examples and third-party
drawing/list, not new observations or a general evidence-authentication API.
"""
from ecu_rom_provenance.compatibility import ECUS, MCUS, CONFIGURATIONS, classify


_CANDIDATE_FIELDS = (
    'ecuCandidate', 'pcbCandidate', 'literalMarking', 'catalogMcuCandidate')
_MARKINGS = ('M66207-251', 'M66207-304', 'MSM66207-251', 'Unknown')
_PROMOTIONS = ('None', 'SameUnitIdentity', 'ManufacturerAlias',
               'SiliconRevision', 'C8Semantics')
_SOURCE_IDS = ('DGTuneA02Photo', 'EbayA01Photo', 'HALoggedList',
               'BomarcSchematic', 'Unknown')
_DATA_PREMISES = ('StandardMap', 'ExternalDataDocumented', 'Unknown')
_SELECTIONS = ('Unknown', 'SocketVisible', 'SchematicOnly', 'HypotheticalEaLow')


def _require(condition, reason):
    if condition is not True:
        raise ValueError(reason)


def _choice(value, choices, reason):
    _require(type(value) is str and value in choices, reason)


def _closed(value, fields, reason):
    _require(type(value) is dict and set(value) == set(fields), reason)


def _unbound():
    return {
        'sameUnitBound': False, 'actualSiliconConfirmed': False,
        'actualMcuIdentity': None, 'peripheralApplicability': 'Unestablished',
        'c8IsaApplicability': 'C8PrimaryConflictUnresolved',
        'executionAdmission': False, 'firmwareReady': False,
    }


def _source_facts(source_id, code):
    # Literal labels are deliberately not a manufacturer alias map. A drawing's
    # catalog-part assertion is scoped to its own subject, not to the ROM donor.
    subject, evidence, labels, pcb, literal, part = (
        None, 'Unknown', [], None, None, None)
    if source_id == 'DGTuneA02Photo':
        subject, evidence, labels, pcb, literal = (
            'DGTuneCommercialExample', 'ThirdPartyExample', ['P28-A02'],
            '11F0', 'M66207-304')
    elif source_id == 'EbayA01Photo':
        subject, evidence, labels, pcb, literal = (
            'EbayCommercialExample', 'ThirdPartyExample', ['P28-A01'],
            '1720', 'M66207-251')
    elif source_id == 'BomarcSchematic':
        subject, evidence, labels, pcb, literal, part = (
            'BomarcDrawingExample', 'SecondaryTechnicalClaim', ['P28-A51'],
            '1720', 'MSM66207-251', 'MSM66207')
    elif source_id == 'HALoggedList':
        subject, evidence = 'HALoggedUnits', 'SecondaryTechnicalClaim'
        if code == '251':
            labels = ['P28-A01', 'P28-A51']
        elif code == '304':
            labels = ['P28-A02', 'P28-A52']
    return {
        'sourceId': source_id, 'sourceSubject': subject,
        'evidenceClass': evidence, 'ecuLabels': labels, 'pcbRevision': pcb,
        'literalMarking': literal, 'catalogMcuPart': part,
    }


def mcu_candidate_attribution(query):
    """Compare a candidate tuple with one frozen, unlinked source subject.

    A mismatch is not a same-unit conflict and never rules out an actual ECU.
    Requested upward promotions are retained as explicit rejections. Neither
    a numeric suffix nor a guessed standard part creates silicon identity.
    """
    _closed(query, (*_CANDIDATE_FIELDS, 'sourceId', 'requestedPromotion'),
            'ClosedCandidateQueryRequired')
    _choice(query['ecuCandidate'], ECUS, 'ClosedEcuCandidateRequired')
    _choice(query['pcbCandidate'], ('11F0', '1720', 'Unknown'),
            'ClosedPcbCandidateRequired')
    _choice(query['literalMarking'], _MARKINGS, 'ClosedLiteralMarkingRequired')
    _choice(query['catalogMcuCandidate'], (*MCUS, 'Unknown'),
            'ClosedCatalogMcuCandidateRequired')
    _choice(query['sourceId'], _SOURCE_IDS, 'ClosedCandidateSourceRequired')
    _choice(query['requestedPromotion'], _PROMOTIONS,
            'ClosedCandidatePromotionRequired')
    code = (None if query['literalMarking'] == 'Unknown'
            else query['literalMarking'].rsplit('-', 1)[1])
    source = _source_facts(query['sourceId'], code)
    observed = (source['ecuLabels'], source['pcbRevision'],
                source['literalMarking'], source['catalogMcuPart'])
    comparisons = []
    for field, fact in zip(_CANDIDATE_FIELDS, observed):
        candidate = query[field]
        if candidate == 'Unknown':
            status = 'CandidateUnknown'
        elif fact is None or fact == []:
            status = 'NotStatedBySource'
        elif (candidate in fact if type(fact) is list else candidate == fact):
            status = 'MatchesSelectedSource'
        else:
            status = 'DiffersFromSelectedSource_NotSameUnitConflict'
        comparisons.append({'field': field, 'status': status})
    statuses = [row['status'] for row in comparisons]
    if 'DiffersFromSelectedSource_NotSameUnitConflict' in statuses:
        classification = 'DifferentCandidateFromSelectedExample'
    elif 'MatchesSelectedSource' in statuses:
        classification = 'ThirdPartyCandidateAssociation'
    else:
        classification = 'CandidateAttributionUnestablished'
    promotion = query['requestedPromotion']
    return {
        'classification': classification,
        'candidate': {field: query[field] for field in _CANDIDATE_FIELDS},
        'source': source, 'fieldComparisons': comparisons,
        'literalCodeToken': code, 'manufacturerAliasEstablished': False,
        'customerCodeMeaning': 'ExactMeaningUnestablished',
        'package': None, 'siliconRevision': None,
        'requestedPromotion': promotion,
        'promotionDecision': 'NotRequested' if promotion == 'None' else 'Rejected',
        'rejectedEdges': [] if promotion == 'None' else [promotion],
        'unresolvedConstraints': [
            'OriginalExtractionToSameUnit', 'ManufacturerLiteralAlias',
            'ExactCustomerCodeMeaning', 'SiliconRevision',
            'BoardProgramAndDataSelection', 'ApplicableC8Clarification'],
        **_unbound(),
    }


def _segments(start, end, regions):
    return [
        {'start': max(start, low), 'endExclusive': min(end, high), 'region': name}
        for low, high, name in regions if max(start, low) < min(end, high)
    ]


def _premise_fit(space, segments, program_premise, data_premise, selection):
    names = {segment['region'] for segment in segments}
    if space == 'PROGRAM':
        if program_premise == 'Unknown':
            return 'Unknown'
        if program_premise == 'InternalOnly32K':
            return ('ConflictsWithInternalOnlyPremise' if 'ExternalProgram' in names
                    else 'FitsStandardInternalProgram_PremiseOnly')
        if selection == 'HypotheticalEaLow':
            return 'ConditionalExternalProgram_SelectionHypothesisOnly'
        return 'DocumentedCapacityOnly_SelectionUnknown'
    if 'Sfr' in names:
        return 'SfrApplicabilityUnestablished'
    if data_premise == 'Unknown':
        return 'Unknown'
    if 'ExternalData' in names:
        return ('DocumentedExternalData_CircuitUnknown'
                if data_premise == 'ExternalDataDocumented'
                else 'ExternalDataProofRequired')
    return 'FitsStandardInternalData_PremiseOnly'


def memory_architecture_compatibility(query):
    """Overlay standard spans and independent memory-selection obligations.

    All segments are half-open and never wrap. The access width is a proposed
    byte extent, not an instruction permission or an actual bus transaction.
    Same-space intersections expose potential aliases. Cross-space numeric
    intersections explicitly do not establish a shared physical storage cell.
    """
    _closed(query, ('ecuCandidate', 'mcuCandidate', 'programPremise', 'dataPremise',
                    'accesses', 'selectionEvidence'), 'ClosedMemoryQueryRequired')
    _choice(query['ecuCandidate'], ECUS, 'ClosedEcuCandidateRequired')
    _choice(query['mcuCandidate'], MCUS, 'ClosedMcuCandidateRequired')
    _choice(query['programPremise'], CONFIGURATIONS, 'ClosedProgramPremiseRequired')
    _choice(query['dataPremise'], _DATA_PREMISES, 'ClosedDataPremiseRequired')
    _choice(query['selectionEvidence'], _SELECTIONS, 'ClosedSelectionEvidenceRequired')
    accesses = query['accesses']
    _require(type(accesses) is list and len(accesses) <= 16, 'BoundedAccessInventoryRequired')
    for access in accesses:
        _closed(access, ('space', 'address', 'widthBytes'), 'ClosedMemoryAccessRequired')
        _choice(access['space'], ('PROGRAM', 'DATA'), 'SeparateAddressSpaceRequired')
        _require(type(access['address']) is int and 0 <= access['address'] <= 65535
                 and type(access['widthBytes']) is int and access['widthBytes'] in (1, 2)
                 and access['address'] + access['widthBytes'] <= 65536,
                 'NonwrappingTypedByteExtentRequired')

    ecu, mcu, program = (query[name] for name in
                         ('ecuCandidate', 'mcuCandidate', 'programPremise'))
    inherited = classify(ecu, mcu, program)
    program_end = inherited['standardInternalProgramBytes']
    data_end = 128 + inherited['standardTotalInternalDataBytes']
    maps = {
        'PROGRAM': ((0, program_end, 'InternalProgram'),
                    (program_end, 65536, 'ExternalProgram')),
        'DATA': ((0, 128, 'Sfr'), (128, 192, 'PointingRegisterRam'),
                 (192, data_end, 'InternalRam'), (data_end, 65536, 'ExternalData')),
    }
    selection = query['selectionEvidence']
    qualifications = {
        'Unknown': 'ActiveSelectionUnknown',
        'SocketVisible': 'VisibleComponentOnly_NotElectricalOrActiveSelection',
        'SchematicOnly': 'DrawingOnly_NotSameUnitActiveSelection',
        'HypotheticalEaLow': 'HypothesisOnly_NotObservedEa',
    }
    projected = []
    for index, access in enumerate(accesses):
        start, end = access['address'], access['address'] + access['widthBytes']
        segments = _segments(start, end, maps[access['space']])
        ea_low = None
        if access['space'] == 'PROGRAM' and selection == 'HypotheticalEaLow':
            ea_low = [{'start': start, 'endExclusive': end, 'region': 'ExternalProgram'}]
        projected.append({
            'index': index, **access, 'normalMapSegments': segments,
            'hypotheticalEaLowSegments': ea_low,
            'premiseFit': _premise_fit(access['space'], segments, program,
                                       query['dataPremise'], selection),
        })
    same, separate = [], []
    for left_index, left in enumerate(accesses):
        for right_index in range(left_index + 1, len(accesses)):
            right = accesses[right_index]
            start = max(left['address'], right['address'])
            end = min(left['address'] + left['widthBytes'],
                      right['address'] + right['widthBytes'])
            if start < end:
                row = {'leftIndex': left_index, 'rightIndex': right_index,
                       'start': start, 'endExclusive': end}
                (same if left['space'] == right['space'] else separate).append(row)
    conflicts = (['InternalOnlyAndExternalEaLowAreIncompatiblePremises']
                 if program == 'InternalOnly32K' and selection == 'HypotheticalEaLow'
                 else [])
    constraints = ['SameUnitExtractionCustody', 'ApplicablePartAndRevision',
                   'ProgramEaPsenDecode', 'DataRdWrDecode', 'ActualRamAndStackOwnership',
                   'C8PrimaryConflictUnresolved']
    if mcu.startswith('MSM66P'):
        constraints.append('OtpProgrammingAndOperatingMode')
    return {
        'classification': ('ContradictoryDeclaredPremises' if conflicts
                           else inherited['status']),
        'inheritedM2cmRow': inherited, 'candidateId': '/'.join((ecu, mcu, program)),
        'dataPremise': query['dataPremise'], 'selectionEvidence': selection,
        'selectionQualification': qualifications[selection], 'accesses': projected,
        'sameSpaceOverlaps': same, 'crossSpaceNumericOverlaps': separate,
        'premiseConflicts': conflicts, 'unresolvedConstraints': constraints,
        'actualProgramSelection': None, 'actualDataMapping': None,
        'stackApplicability': 'Unestablished', **_unbound(),
    }
