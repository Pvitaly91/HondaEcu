"""Closed source-domain obligations and invented static review; no CPU API.

The private sealed-observation audit is separate. This public component checks
unchanged source inventory and compares two independently written expectation
calculations. It cannot read a ROM, import generations or admit native gates.
"""
from copy import deepcopy
import json
from pathlib import Path

BASE = 'f77d2cc1468fe128ba4ad393c3e0a1a5dab423fc'
INVENTED = 'InventedOnly_NotNativeRuntimeOrCurrentM2bzState'
UNOWNED = 'UnownedTechnicalBusCanary_NotBranchAuthority'
EXPECTED_CONTRACT = {
    'schemaVersion': 1, 'milestone': 'M2ca',
    'classification': 'BlockedSourceProvenanceAndInventedStaticGateReview_NotExecutionAdmission',
    'baseSha': 'f77d2cc1468fe128ba4ad393c3e0a1a5dab423fc',
    'baseSourceCount': 1119,
    'baseSourceFingerprint': '6ac80491f49bddb6581821c637d395a4807e3832f5019224fca9024a16fd09d6',
    'newSourceFingerprintPolicy': 'DerivedFromAllCurrentRawSourceRows_NotEmbeddedOrSelfAuthorized',
    'currentContext': {'prefixReferenceInstructions': 49, 'entryReferencePc': 0x063B,
        'terminalReferencePc': 0x064C, 'lrb': 0x0021, 'offPage': 0x0100,
        'localBank': [0x0108, 0x0110], 'pointingBanks': [0x0080, 0x00C0],
        'ordinaryDataInventory': [0x0108, 0x0109, 0x010A, 0x010B, 0x010C, 0x010D, 0x010E, 0x010F,
            0x0110, 0x0111, 0x0112, 0x0113, 0x0114, 0x0115, 0x0116, 0x0117,
            0x0124, 0x0128, 0x012A, 0x018E, 0x018F, 0x0196, 0x0197],
        'explicitOldStackByteSeeds': 2, 'separateOnceSelectorSnapshot': True,
        'initial012A': [0, 128], 'afterNative5685': 0, 'old012ABit0': 0, 'old012ABit3': 0,
        'importedRuntimeStateOrGeneration': False},
    'sources': {
        '011F': {'address': 0x011F, 'width': 8, 'readerPc': 0x064C, 'bit': 3,
            'classification': 'UnownedTechnicalBusCanary_NotBranchAuthority', 'generation': None,
            'currentReaderAdmitted': False, 'newInitialSourceAllowed': False},
        '011B': {'address': 0x011B, 'width': 8, 'readerPc': 0x064F, 'bit': 7,
            'classification': 'UnownedTechnicalBusCanary_NotBranchAuthority', 'generation': None,
            'currentReaderAdmitted': False, 'newInitialSourceAllowed': False},
        '012A': {'address': 0x012A, 'width': 8, 'readerPcs': [0x0652, 0x065F], 'bits': [0, 3],
            'classification': 'ExistingAuthorizedTechnicalSource',
            'currentByteWriterRequirement': 'SameMachine5685Retirement40_IfNewPrefixWereAdmitted',
            'retainedLowBitOwner': 'ExistingTechnicalSeed_NotPhysicalNativeOwner',
            'generationImported': False, 'newInitialBit0OrBit3Allowed': False}},
    'publicFixtureMapping': {'private0117': 0x011B, 'private012A': 0x012D,
        'literalPublic011BIsPrivateBranch011B': False,
        'unownedOriginalBranch011BHasAdmittedSourceMatchedCell': False},
    'historicalSources': {'011FWordAlias': 0x011E, '011FStaticWriters': [0x0408, 0x5C35],
        '011BHistoricalOwner': 'IntegratedLimiterInitializationAndAdaptiveFixedSource',
        'classification': 'HistoricalSourceOnly_NotTransferred', 'transferAllowed': False},
    'sites': [
        {'pc': 0x064C, 'length': 3, 'form': 'JBS off011F.3,rel8', 'successors': [0x064F, 0x065F]},
        {'pc': 0x064F, 'length': 3, 'form': 'JBS off011B.7,rel8', 'successors': [0x0652, 0x065F]},
        {'pc': 0x0652, 'length': 3, 'form': 'RB off012A.0', 'successors': [0x0655]},
        {'pc': 0x0655, 'length': 2, 'form': 'JEQ rel8', 'successors': [0x0657, 0x065F]},
        {'pc': 0x065F, 'length': 3, 'form': 'RB off012A.3', 'successors': [0x0662]},
        {'pc': 0x0662, 'length': 2, 'form': 'JNE rel8', 'successors': [0x0664, 0x0667]}],
    'primaryReferences': {'JBS': '3-65', 'RB': '3-114', 'JEQ/JNE': '3-66',
        'authority': 'ManufacturerInstructionSemantics_SeparatelyReviewed_NotDecoderRecognition'},
    'candidateProgram': {'windows': [[0x063B, 0x0664], [0x54F5, 0x5689]],
        'windowBytes': [41, 404], 'totalBytes': 445, 'callerExpansion': 24,
        'oldReviewedSites': 59, 'newReviewedSites': 6, 'reviewedSites': 65,
        'actualNewWindowOpened': False, 'programAdmissionGranted': False,
        'forbiddenStopBefore': [0x0657, 0x0664, 0x0667]},
    'routes': [
        {'name': 'PrimaryTakenSkipCAL', 'conditions': {'011F.3': 1, 'old012A.3': 1},
            'pcs': [0x064C, 0x065F, 0x0662], 'terminal': 0x0667, 'referenceBudget': 52,
            'currentOriginalAdmission': False},
        {'name': 'FallthroughDirectToCALBoundary', 'conditions': {'011F.3': 0, '011B.7': 1, 'old012A.3': 0},
            'pcs': [0x064C, 0x064F, 0x065F, 0x0662], 'terminal': 0x0664, 'referenceBudget': 53,
            'currentOriginalAdmission': False},
        {'name': 'FallthroughVia012A0', 'conditions': {'011F.3': 0, '011B.7': 0, 'old012A.0': 0, 'old012A.3': 0},
            'pcs': [0x064C, 0x064F, 0x0652, 0x0655, 0x065F, 0x0662], 'terminal': 0x0664, 'referenceBudget': 55,
            'currentOriginalAdmission': False},
        {'name': 'FallthroughToTRNSITBoundary', 'conditions': {'011F.3': 0, '011B.7': 0, 'old012A.0': 1},
            'pcs': [0x064C, 0x064F, 0x0652, 0x0655], 'terminal': 0x0657, 'referenceBudget': 53,
            'currentOriginalAdmission': False}],
    'inventedExamples': [
        {'caseId': 'invented-m2ca-a', 'gateBytes': {'011F': 0x58, '011B': 0x00, '012A': 0xBC}},
        {'caseId': 'invented-m2ca-b', 'gateBytes': {'011F': 0x50, '011B': 0x80, '012A': 0xB4}},
        {'caseId': 'invented-m2ca-c', 'gateBytes': {'011F': 0x50, '011B': 0x00, '012A': 0xB4}},
        {'caseId': 'invented-m2ca-d', 'gateBytes': {'011F': 0x50, '011B': 0x00, '012A': 0xB5}}],
    'inventedRetained': {'a': 0xC35A, 'psw': 0xB5A7, 'lrb': 0x0021, 'scb': 7, 'ssp': 0x07FE,
        'pointing': [0x1357, 0x2468, 0x369A, 0xABCD], 'local_r': [0, 0x55, 0xAA, 0xFF, 0x31, 0x72, 0xA3, 0xB4]},
    'proofPolicy': {'inventedVectorsAreCurrentM2bzStates': False,
        'expectedArchitecturalEffectsAreProductionJournals': False,
        'expectedInstructionCountsAreActualRetirements': False, 'cpuOrBusInstances': 0,
        'runtimeCanonicalComparison': 'NotApplicable_NoAdmittedCorpus',
        'staticCanonicalComparison': 'FullDecompressedBytes_LocalUbuntuWindows',
        'unknownSourcesMayBeFilledWithA5': False, 'oldGenerationImportAllowed': False},
    'authority': {'originalBranchExecutionAdmitted': False, 'admittedRoutes': [],
        'newInitialGateInputsAllowed': [], 'runtimeFeatureAdded': False, 'newExecutableAdded': False,
        'hardwareObserved': False, 'firmwareReady': False},
    'preservation': {'inheritedHistoricalGeneratedRunnerExceptions': 1,
        'authorizedExternalPythonToolingExceptions': 1, 'totalDocumentedExceptions': 2,
        'historicalExpectedFingerprintsRewritten': False, 'strictHistoricalPreservationPass': False,
        'newUnauthorizedProtectedDifferencesRequired': 0},
}


def need(value, reason):
    if value is not True:
        raise ValueError(reason)


def exact_equal(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(exact_equal(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(exact_equal(a, b) for a, b in zip(left, right))
    return left == right


def read_contract(path=None):
    path = Path(path) if path is not None else Path(__file__).with_name('contract.json')
    need(path.is_file() and path.stat().st_size <= 65536, 'BoundedResearchContractRequired')
    def unique(pairs):
        value = {}
        for key, item in pairs:
            need(key not in value, 'DuplicateResearchContractKeyRefused'); value[key] = item
        return value
    result = json.loads(path.read_bytes(), object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NonfiniteResearchContractRefused')))
    need(type(result) is dict, 'ResearchContractObjectRequired')
    return result


def validate_contract(value=None):
    value = read_contract() if value is None else value
    need(exact_equal(value, EXPECTED_CONTRACT), 'ClosedProvenanceOrStaticResearchContractMismatch')
    from native_post_return_selector import corpus as prior_corpus, oracle as prior_oracle
    from .gate_model import FORM_CONTRACT, current_source_admission_obligations
    ordinary = sorted(prior_corpus.INVENTORY)
    need(ordinary == value['currentContext']['ordinaryDataInventory'] and len(ordinary) == 23
         and 0x011B not in ordinary and 0x011F not in ordinary
         and prior_corpus.PUBLIC_DATA[0x0117] == 0x011B
         and prior_corpus.PUBLIC_DATA[0x012A] == 0x012D,
         'ExactUnchangedSourceInventoryAndPublicMappingCollisionRequired')
    old, new = set(prior_oracle.FORM), {row['pc'] for row in FORM_CONTRACT}
    need(len(old) == 59 and len(new) == len(FORM_CONTRACT) == 6 and not old & new
         and len(old | new) == 65 and sorted(new) == [row['pc'] for row in value['sites']],
         'ActualReviewed59PlusDisjointSixSiteInventoriesRequired')
    for form, row in zip(FORM_CONTRACT, value['sites']):
        targets = sorted({pc for pc in (form['taken'], form['fallthrough']) if pc is not None})
        need(form['pc'] == row['pc'] and form['length'] == row['length']
             and form['form'] == row['form'] and targets == sorted(row['successors']),
             'IndependentSixFormLengthAndSuccessorAgreementRequired')
    obligation = current_source_admission_obligations()
    need(obligation['original_rom_routes_admitted'] == [] and obligation['new_source_inputs'] == []
         and obligation['historical_source_transfers'] == []
         and obligation['first_blocked_reader_pc'] == 0x064C
         and obligation['sources']['011B']['classification'] == obligation['sources']['011F']['classification'] == UNOWNED
         and obligation['unowned_a5_may_select_branch'] is False,
         'MissingCurrentBranchSourcesCannotAcquireRuntimeAuthority')
    return {'schemaVersion': 1, 'milestone': 'M2ca', 'passed': True,
        'classification': 'StaticSourceDomainObligations_NotPrivateRuntimeObservation',
        'ordinaryDataInventory': ordinary, 'oldReviewedSites': sorted(old), 'newReviewedSites': sorted(new),
        'combinedReviewedSites': sorted(old | new), 'runtimeAdmission': False,
        'actualCpuExecutions': 0, 'originalRomExecutions': 0, 'firmwareReady': False}


def invented_vectors(value=None):
    value = read_contract() if value is None else value
    validate_contract(value)
    return [{'classification': INVENTED, 'case_id': item['caseId'],
        'gate_bytes': deepcopy(item['gateBytes']), 'retained': deepcopy(value['inventedRetained'])}
        for item in value['inventedExamples']]


def static_records(source_fingerprint, value=None):
    need(type(source_fingerprint) is str and len(source_fingerprint) == 64
         and all(c in '0123456789abcdef' for c in source_fingerprint), 'CurrentRawSourceFingerprintRequired')
    from .gate_model import primary_expected_trace, build_review_envelope, validate_review_envelope
    from .gate_reference_oracle import reference_outcome
    value = read_contract() if value is None else value
    records = []
    for vector, route in zip(invented_vectors(value), value['routes']):
        primary = primary_expected_trace(vector); reference = reference_outcome(vector)
        need(exact_equal(primary, reference), 'IndependentInventedGateExpectedTraceMismatch')
        need(primary['route_class'] == route['name'] and primary['expected_pc_sequence'] == route['pcs']
             and primary['expected_full_route_retirements'] == route['referenceBudget'],
             'ConditionalRouteSpecificationAndIndependentExpectationsMustAgree')
        envelope = build_review_envelope(vector); compared = validate_review_envelope(envelope)
        records.append({'schemaVersion': 1, 'milestone': 'M2ca',
            'classification': 'InventedStaticCanonicalReview_NotCpuOrOriginalRomObservation',
            'sourceFingerprintSha256': source_fingerprint, 'caseIndex': len(records), 'vector': vector,
            'primaryExpected': primary, 'independentReference': reference,
            'reviewEnvelope': envelope, 'comparison': compared})
    need(len(records) == 4 and sum(r['primaryExpected']['expected_full_route_retirements'] for r in records) == 213,
         'FourConditionalReferencePathsOnly_NotRuntimeRetirementCounts')
    return records
