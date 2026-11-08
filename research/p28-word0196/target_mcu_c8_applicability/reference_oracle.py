"""Independent expected records for the fixed documentary corpus."""
from itertools import combinations

from .candidate_reference import expected_attribution, expected_memory

ARCHIVE_ORIGINS = {'ArchiveDedup', 'ArchiveImport', 'M1aAcquisition'}
FIXTURE_AGREEMENT = {'FixtureSameUnitA', 'FixtureSameUnitMirror', 'FixtureIndependentAgreement'}


def _custody(case):
    q = case['input']
    sources = sorted(q['sourceIds'])
    fixture = any(item.startswith('Fixture') for item in sources)
    binding = q['archiveBinding']
    acquisition = binding == 'ExactAuthenticatedArchive' and 'M1aAcquisition' in sources
    request = q['requestedConclusion']
    classification = {
        'ProjectArchiveAcquisition': 'ProjectArchiveAcquisitionOnly' if acquisition else 'ArchiveAcquisitionNotEstablished',
        'WitnessComparison': 'FixtureWitnessComparisonOnly' if fixture else 'DocumentaryWitnessComparisonOnly',
        'OriginalPhysicalExtraction': 'OriginalPhysicalExtractionNotEstablished',
        'StudiedDonor': 'FixtureCannotEstablishActualProvenance' if fixture else 'StudiedDonorNotEstablished',
        'FactoryOriginality': 'FactoryOriginalityNotEstablished',
        'PhysicalExtractionDate': 'PhysicalExtractionDateNotEstablished',
    }[request]
    if binding in ('FilenameOnly', 'ByteIdentityMismatch'):
        classification = {'FilenameOnly': 'FilenameOnlyIdentityRefused',
                          'ByteIdentityMismatch': 'ArchiveByteIdentityMismatch'}[binding]
    pairs = []
    for left, right in combinations(sources, 2):
        pair = {left, right}
        if pair <= ARCHIVE_ORIGINS or pair == {'FixtureSameUnitA', 'FixtureSameUnitMirror'}:
            relation = 'DependentDuplicate'
        elif pair <= FIXTURE_AGREEMENT:
            relation = 'FixtureIndependentSameUnitAgreement'
        elif fixture:
            relation = 'FixtureExclusiveSameUnitConflict'
        elif pair == {'A01Photo', 'A02Photo'}:
            relation = 'DifferentPhysicalSubjects'
        else:
            relation = 'DifferentDocumentaryScopes'
        pairs.append({'left': left, 'right': right, 'relation': relation})
    count = len(sources) - max(0, len(set(sources) & ARCHIVE_ORIGINS) - 1)
    count -= int({'FixtureSameUnitA', 'FixtureSameUnitMirror'} <= set(sources))
    return dict(classification=classification, projectArchiveAcquisition=acquisition,
                originalPhysicalExtraction=None, studiedDonor=None, factoryOriginality=None,
                physicalExtractionDate=None, independentWitnessCount=count, sourceCount=len(sources),
                pairRelations=pairs, missingProof=['OriginalExtractionRecord', 'SameUnitLabelPcbMcuCustody',
                    'AcquiredImageToExtractionByteBinding', 'IndependentFactoryOriginalityEvidence'],
                actualHardwareConfirmed=False, actualMcuIdentity=None, executionAdmission=False, firmwareReady=False)


DOCUMENTS = (
    ('EmulatorBehavior', 'SecondaryTechnicalClaim', ('EmulatorBehavior',)),
    ('Oki1991C8Instruction', 'PrimaryDocumentText', ('Oki1991C8Instruction', 'Oki1991C8SameEditionMirror')),
    ('Oki1998InstructionList', 'ManufacturerMnemonicList', ('Oki1998InstructionList',)),
    ('Oki1998JointDeviceSpec', 'ManufacturerPartFamily', ('Oki1998EnDeviceSpec', 'Oki1998JaDeviceSpec')),
    ('Oki1999Nx8500S', 'ComparativeFamilyEvidence', ('Oki1999Nx8500S',)),
    ('OkiNov1990_207DeviceSpec', 'PreliminaryManufacturerMnemonicList', ('OkiNov1990_207DeviceSpec',)),
    ('SearchIndexOnly', 'SearchIndexOnly', ('SearchIndexOnly',)),
)


def _witnesses(q):
    selected = set(q['sourceIds'])
    return [{'documentId': doc, 'scope': scope, 'sourceIds': [key for key in keys if key in selected]}
            for doc, scope, keys in DOCUMENTS if selected.intersection(keys)]


def _code(case):
    name, q = case['id'].removeprefix('code-'), case['input']
    status = 'CustomerCodeSemanticsUnestablished'
    reason = {
        'numeric-mismatch': 'LiteralNumberAndAssertedCodeDiffer',
        'unknown-part': 'ReviewedCatalogPartRequired',
        'locator-only': 'ApplicableManufacturerDeviceSpecificationRequired',
    }.get(name, 'ManufacturerAliasCodeAndRevisionMappingMissing')
    if name.endswith('-promotion'):
        status, reason = 'OutsideVerifiedScope', 'UnsupportedCodeOrRevisionPromotion'
    package = {
        'otp': ['SS', 'JS'], 'early-only': [], 'locator-only': [], 'unknown-part': [],
    }.get(name, ['SS', 'GS-BK', 'JS'])
    technology = {'otp': 'OTP', 'locator-only': None, 'unknown-part': None}.get(name, 'MaskROM')
    suffix = {'M66207-251': '251', 'M66207-304': '304'}.get(q['literalMarking'])
    return dict(status=status, reason=reason, literalMarking=q['literalMarking'], literalNumericSuffix=suffix,
                catalogPart=q['catalogPart'], assertedCustomerCode=q['customerCode'],
                assertedRevision=q['siliconRevision'],
                catalogCodeNumberField='xxx' if technology == 'MaskROM' and package else None,
                catalogPackageSuffixes=package, catalogProgramTechnology=technology, manufacturerLiteralAlias=None,
                resolvedCustomerCode=None, resolvedSiliconRevision=None, sourceWitnesses=_witnesses(q),
                actualMcuIdentity=None, actualSiliconConfirmed=False,
                unresolvedConstraints=['ApplicableManufacturerLiteralAlias', 'SpecificCustomerOrMaskCodeMapping',
                                       'ExactSiliconRevisionBinding'])


def _isa(case):
    name, q = case['id'].removeprefix('isa-'), case['input']
    part = q['catalogPart']
    reasons = {
        'wrong-family': 'OnlyComparativeFamilySource',
        'wrong-opcode': 'ExactC8OpcodeRequired',
        '201-with-207-only': 'ExactPredicateWitnessMissing',
        'early-207': 'ManufacturerFamilyOrMnemonicOnly',
        'early-otp': 'ManufacturerFamilyOrMnemonicOnly',
        'unverified-stepping': 'RevisionSpecificC8ProofMissing',
        'unbound-part': 'ReviewedCatalogPartRequired',
        'emulator': 'ExactPredicateWitnessMissing',
    }
    promoted = name.startswith('force-')
    status = 'OutsideVerifiedScope' if promoted or name == 'wrong-opcode' else 'C8_PRIMARY_CONFLICT_UNRESOLVED'
    reason = 'TargetOrPredicatePromotionRefused' if promoted else reasons.get(
        name, 'PublishedC8PredicateConflictUnresolved')
    joint = name in ('combined', 'unverified-stepping', 'force-or', 'force-and', 'force-target')
    early = joint or name in ('early-207', 'early-otp')
    primary = joint or name in ('printed-and-mirror', 'unbound-part')
    primary_text = (dict(catalogPart='MSM66201', opcode=0xC8, predicate='PrintedOr',
                         sameCatalogPart=part == 'MSM66201') if primary else None)
    related = dict(core='nX-8/500S', opcode=0xF0, predicate='ComparativeAnd') if joint or name == 'wrong-family' else None
    return dict(status=status, reason=reason, catalogPart=part, opcode=q['opcode'],
                assertedRevision=q['siliconRevision'], assertedCustomerCode=q['customerCode'],
                documentedCore='nX-8/200' if joint else None,
                otpCounterpartOf='MSM66207' if name == 'early-otp' else None,
                familyInstructionListScope='JC' if joint else None,
                preliminary207Mnemonic='JC GT denotes greater comparison' if early else None,
                primaryC8Text=primary_text, comparativeText=related, sourceWitnesses=_witnesses(q),
                exactRevisionApplicable=None, exactSiliconPredicate=None, actualMcuIdentity=None,
                actualSiliconConfirmed=False, newDecisiveEvidence=False,
                unresolvedConstraints=['ExactPartAndSiliconRevisionApplicability', 'ApplicableExactC8Clarification',
                                       'ApplicableVerifiedSiliconObservation'])


MISSING_EDGES = (
    ('ArchiveAcquisition', 'PrearchiveExtraction', 'OriginalExtractionRecordWithExactByteIdentity'),
    ('PrearchiveExtraction', 'ECUPhysicalDonor', 'OriginalExtractionRecordLinkedToStableDonor'),
    ('ECUPhysicalDonor', 'ECULabel', 'SameUnitLabelCustody'),
    ('ECUPhysicalDonor', 'PCBRevision', 'SameUnitBoardCustody'),
    ('PCBRevision', 'MCUMarking', 'ReadableSameUnitMarkingAndPackage'),
    ('MCUMarking', 'CatalogMCUPart', 'ApplicableManufacturerAlias'),
    ('CatalogMCUPart', 'CustomerCode', 'ApplicableManufacturerCodeMapping'),
    ('CustomerCode', 'SiliconRevision', 'VerifiedSiliconRevision'),
    ('PCBRevision', 'ProgramMemorySelection', 'SameUnitProgramDeviceEaAndDecode'),
    ('PCBRevision', 'DataMemoryMapping', 'SameUnitDataDecodeAndStackMapping'),
    ('SiliconRevision', 'ManufacturerISA', 'ExactPartRevisionManualApplicability'),
    ('ManufacturerISA', 'C8InstructionRule', 'ApplicableExactC8Clarification'),
    ('SiliconRevision', 'C8SiliconObservation', 'AuthenticatedExistingCmpAndC8Observation'),
    ('C8InstructionRule', 'TargetC8Applicability', 'BothProofAxesBoundToSameRevision'),
)


def _junction(case):
    q = case['input']
    bound = case['id'] != 'junction-filename-unbound'
    first = {'from': 'StudiedROM', 'to': 'ArchiveAcquisition', 'sourceId': 'M2cmRecordedArchiveAcquisition',
             'locator': 'M2cmAcquisitionAudit', 'subject': 'StudiedImage', 'category': 'AuthenticatedArchive',
             'provenance': 'RecordedProjectAcquisition', 'independence': 'AcceptedProjectRecord',
             'rationale': 'ExactRecordedByteBinding' if bound else 'RequiredEdgeUnverified', 'conflict': None,
             'applicability': 'ProjectFileOnly' if bound else 'NotEstablished',
             'missingConfirmation': None if bound else 'ExactAcceptedProjectArchiveBinding',
             'privacy': 'RedactedDocumentaryMetadata'}
    missing = [] if bound else [first]
    for start, end, proof in MISSING_EDGES:
        row = {'from': start, 'to': end, 'sourceId': None, 'locator': None, 'subject': None, 'category': 'Unknown',
               'provenance': 'Unbound', 'independence': 'NoQualifiedWitness', 'rationale': 'RequiredEdgeUnverified',
               'conflict': None, 'applicability': 'NotEstablished', 'missingConfirmation': proof,
               'privacy': 'RedactedDocumentaryMetadata'}
        if end == 'C8InstructionRule':
            row.update(sourceId='Oki1991C8Instruction', locator='PrintedPage3-66', subject='MSM66201Manual',
                       category='PrimaryTextWithUnresolvedConflict', provenance='AcceptedManufacturerText',
                       independence='OneDocumentIdentity', conflict='OR_AND_UNRESOLVED')
        missing.append(row)
    nodes = ['StudiedROM', 'ArchiveAcquisition', 'PrearchiveExtraction', 'ECUPhysicalDonor', 'ECULabel',
             'PCBRevision', 'MCUMarking', 'CatalogMCUPart', 'CustomerCode', 'SiliconRevision',
             'ProgramMemorySelection', 'DataMemoryMapping', 'ManufacturerISA', 'C8InstructionRule',
             'C8SiliconObservation', 'TargetC8Applicability']
    status, reason = {
        'Inspect': ('IndeterminateObligation', 'TargetMcuAndExactC8ApplicabilityUnresolved'),
        'AssertTargetRule': ('OutsideVerifiedScope', 'TargetJunctionUnestablished'),
        'AuthorizeExecution': ('OutsideVerifiedScope', 'DocumentaryEvidenceConfersNoExecutionAuthority'),
    }[q['claim']]
    return dict(status=status, reason=reason, hardwareAxis=_custody({'input': q['custody']}),
                isaAxis=_isa({'id': 'isa-combined', 'input': q['isa']}), nodes=nodes,
                acceptedEdges=[first] if bound else [], rejectedEdges=missing,
                actualMcuIdentity=None, actualSiliconConfirmed=False, targetC8Applicability=None,
                junctionEstablished=False, unresolvedConstraints=['OriginalPhysicalExtractionUnbound',
                    'SameUnitMcuRevisionUnbound', 'ExactC8PrimaryConflictUnresolved'],
                minimumProofPacket=[
                    {'record': 'OriginalExtractionCustody', 'binds': ['ExactStudiedByteIdentity', 'StableDonor']},
                    {'record': 'ExistingSameUnitDocumentation',
                     'binds': ['ECULabel', 'BothPcbSides', 'FullMcuMarking', 'ProgramDeviceAndSelection']},
                    {'record': 'ApplicableManufacturerRevisionEvidence',
                     'binds': ['ExactPartAndRevision', 'ExactC8EqualityAndLowerRule']},
                ])


def expected(case):
    return {
        'rom_to_hardware_provenance': _custody,
        'mcu_candidate_attribution': lambda item: expected_attribution(item['input']),
        'memory_architecture_compatibility': lambda item: expected_memory(item['input']),
        'customer_code_applicability': _code,
        'c8_revision_evidence': _isa,
        'target_c8_applicability': _junction,
    }[case['operation']](case)
