"""Curated invented ownership examples and closed research-only authority."""
from copy import deepcopy
import json
from pathlib import Path

from native_data011f_011b_ownership.symbolic_owner import INVENTED, run_scenario

BASE = '2e327d2ade8d419180f1088cb277a306accbab4f'
EXPECTED_CONTRACT = {
    'schemaVersion': 1, 'milestone': 'M2cb', 'baseSha': BASE,
    'classification': 'StaticProvenanceCanonical_NotOriginalRomCpuExecution',
    'targets': [{'address': 0x011F, 'bit': 3, 'readerPC': 0x064C},
        {'address': 0x011B, 'bit': 7, 'readerPC': 0x064F}],
    'proofLevels': ['StaticWriter', 'ConditionalReachableWriter',
        'SourceValueUnderPreconditions', 'ActualSameMachineWriter', 'GenerationPreservedToReader'],
    'proofLevelsInterchangeable': False,
    'baseSourceCount': 1133,
    'baseSourceFingerprintSha256': '2ce07be5dcc42c6403f099ce0f82ccae061eac6b9947f132029dfa74e2f295ad',
    'newSourceApproval': 'SeparateExplicitWorkflowPin_AfterIndependentReview',
    'unknownValuesMayAcquireOwners': False,
    'defaultCanaryMaySelectVerifiedRoute': False,
    'historicalGenerationsMayBeImported': False,
    'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0,
    'actualRetiredInstructions': 0, 'runtimeFeatureAdded': False,
    'InheritedHistoricalGeneratedRunnerExceptions': 1,
    'AuthorizedExternalToolingExceptions': 1, 'AuthorizedPreservationExceptions': 2,
    'StrictHistoricalPreservationPass': False,
    'newUnauthorizedProtectedDifferencesRequired': 0,
    'firmwareReady': False,
}


def strict_equal(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(strict_equal(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(strict_equal(a, b) for a, b in zip(left, right))
    return left == right


def validate_contract(value):
    if not strict_equal(value, EXPECTED_CONTRACT):
        raise ValueError('ClosedReviewedM2cbContractRequired')
    return True


def read_contract():
    def unique(pairs):
        output = {}
        for key, value in pairs:
            if key in output:
                raise ValueError('DuplicateContractKeyRefused')
            output[key] = value
        return output
    path = Path(__file__).with_name('contract.json')
    if path.stat().st_size > 16384:
        raise ValueError('BoundedContractRequired')
    value = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique)
    validate_contract(value)
    return value


def example(case_id):
    machine = 'invented:' + case_id
    return {'caseId': case_id, 'classification': INVENTED, 'machineId': machine,
        'context': {'lrb': 0x21, 'usp': 0x280, 'scb': 2},
        'history': 'invented-serial', 'context012A': 'invented-serial', 'old012A': 0,
        'seeds': [{'address': address, 'value': value, 'owner': 'invented:seed' + format(address, '04X')}
            for address, value in ((0x0212, 0x31), (0x0213, 0x80), (0x0216, 0x5A), (0x0217, 0xA5))],
        'events': [{'op': 'copy', 'pc': pc, 'source': source, 'target': target,
            'width': 16, 'complete': True, 'sourceMachine': machine}
            for pc, source, target in ((0x0400, 0x0212, 0x011A), (0x0408, 0x0216, 0x011E))],
        'reader': {'address': 0x011F, 'bit': 3},
        'constraints': {key: True for key in ('rootReachable', 'writerDominates',
            'irqEstablished', 'stackPreserved', 'aliasesResolved', 'historyCompatible')}}


def curated_scenarios():
    cases = []
    item = example('owned-word'); cases.append(item)
    item = example('unknown-canary'); item['seeds'][-1]['owner'] = None; cases.append(item)
    item = example('unknown-byte'); item['seeds'][-1]['value'] = None; item['seeds'][-1]['owner'] = None; cases.append(item)
    item = example('same-value-writes'); item['events'].append(deepcopy(item['events'][-1])); cases.append(item)
    item = example('word-overlap'); item['events'].append({'op': 'overlap', 'pc': 0x7000, 'address': 0x011E, 'value': 0xA55A}); cases.append(item)
    item = example('indirect-alias'); item['events'].append({'op': 'unknownAlias', 'addresses': [0x011E, 0x011F]}); cases.append(item)
    item = example('program-bit-with-unknown-neighbors')
    item['seeds'][-1].update(value=None, owner=None)
    item['events'].insert(0, {'op': 'programBit', 'pc': 0x5F6B, 'programByte': 0x80}); cases.append(item)
    item = example('program-bit-preserved-neighbors')
    item['events'].insert(0, {'op': 'programBit', 'pc': 0x5F6B, 'programByte': 0}); cases.append(item)
    item = example('011b-word-source'); item['reader'] = {'address': 0x011B, 'bit': 7}; cases.append(item)
    item = example('current-entry-writer-bypass')
    item['history'] = item['context012A'] = 'invented-current-entry'
    item['constraints'].update(rootReachable=False, writerDominates=False, irqEstablished=False, stackPreserved=False)
    item['events'] = []; cases.append(item)
    item = example('earlier-caller-old-bit3'); item['old012A'] = 8; cases.append(item)
    item = example('incompatible-012a-history'); item['context012A'] = 'invented-other-caller'; cases.append(item)
    return cases


def verify_claim(scenario, claimed):
    from native_data011f_011b_ownership.reference_oracle import reference_scenario
    expected = reference_scenario(scenario)
    actual = run_scenario(scenario)
    if not strict_equal(expected, actual) or not strict_equal(expected, claimed):
        raise ValueError('IndependentFullSymbolicStateOrEffectMismatch')
    return True


def symbolic_records():
    records = []
    for scenario in curated_scenarios():
        actual = run_scenario(scenario)
        verify_claim(scenario, actual)
        records.append({'input': scenario, 'result': actual,
            'independentFullStateEffectComparison': 'PASS',
            'comparisonScope': 'InventedSymbolicLedger_NotProductionCpuObservations'})
    return records


def missing_frontier():
    """Closest concrete obligations, never a request for whole-ECU emulation."""
    return {
        'classification': 'MinimalMissingEvidenceFrontier_NotExecutionAdmission',
        'source011F': {
            'closestCopyWriters': [0x0408, 0x5C35], 'sourceWord': [0x0216, 0x0217],
            'selectedBitRelationship': 'DATA0217.bit3_to_DATA011F.bit3',
            'codeBitCandidate': [0x5F66, 0x5F6A, 0x5F6B], 'programSource': 0x60EC,
            'firstObligation': 'SameMachineReached5F6BThenRetained0217Bit3UntilChosenCopy',
            'remainingByteObligation': 'Other0217BitsAnd0216RequireIndependentOwners',
            'alternateCandidates': [0x2710, 0x5B8A, 0x5B86]},
        'source011B': {
            'closestCopyWriters': [0x0400, 0x5C2D], 'sourceWord': [0x0212, 0x0213],
            'selectedBitRelationship': 'DATA0213.bit7_to_DATA011B.bit7',
            'zeroCandidates': [0x291B, 0x291C, 0x2920],
            'indexedCandidates': [0x5B7E, 0x5B82, 0x5B86, 0x5B8A],
            'bitmapSetDirection': 'PrimaryFunctionDescriptionConflict_NotIndependentlyClosed',
            'firstObligation': 'ReachedOwnedZeroContextOrOwnedBitmapInputThenPreservedGeneration',
            'limiterHistory': 'HistoricalTechnicalInputOnly_NotNativeProducer'},
        'sameMachineBridge': {
            'candidateRoots': [0x0379, 0x03ED], 'currentRoot': 0x063B,
            'currentRootBypassesEarlierWriters': True,
            'firstObligation': 'OneOrderedSourceProducerCopyCallerHistory_NoCrossRootGenerationImport',
            'int1HelperFrame': [0x038A, 0x5C2B, 0x5C3F, 0x038D],
            'retainedTechnicalCall': [0x063B, 0x54F5, 0x5688, 0x063E],
            'requiredReader': 0x064C, 'conditionalSecondReader': 0x064F,
            'externalObligations': ['GenuineEntryAndIrqFrame', 'OwnedSspAndNonoverlap',
                'CompletedRequiredHelperReturns', 'NoIndirectOrNestedFrameOverwrite',
                'SourceConsistent012ABit3History'],
            'physicalIrqOrSchedulerRecovered': False},
        'currentMachineGenerationEstablished': False,
        'staticLineageIsActualGeneration': False,
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0,
        'researchClassification': 'CONDITIONAL_SOURCE_LINEAGE_ESTABLISHED / EXECUTION_BLOCKED',
        'firmwareReady': False,
    }


def canonical_records():
    from native_data011f_011b_ownership.source_inventory import reviewed_inventory
    from native_data011f_011b_ownership.buffer_lineage import lineage_dags
    from native_data011f_011b_ownership.caller_reachability import analyze_cfg
    from native_data011f_011b_ownership.alias_analysis import aliases
    read_contract()
    records = [{'caseId': case, 'classification': EXPECTED_CONTRACT['classification'],
        'data': data, 'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0}
        for case, data in (
            ('source-owner-inventory', reviewed_inventory()),
            ('buffer-copy-lineages', lineage_dags()),
            ('caller-cfg-feasibility', analyze_cfg()),
            ('alias-preservation-obligations', aliases()),
            ('minimal-missing-evidence-frontier', missing_frontier()))]
    for item in symbolic_records():
        records.append({'caseId': item['input']['caseId'],
            'classification': EXPECTED_CONTRACT['classification'], 'data': item,
            'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0})
    # Graph APIs use integer PCs as keys. Normalize those keys once at the
    # JSON boundary before canonical sorting, preserving every value/field.
    return json.loads(json.dumps(records, ensure_ascii=True, allow_nan=False))
