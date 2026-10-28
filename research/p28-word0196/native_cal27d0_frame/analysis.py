"""Small new M2cd static corpus, not replay of M2cc CPU or invented histories."""
from copy import deepcopy
import json
from pathlib import Path

from .frame_model import CONDITIONS, evaluate
from .helper_frame import analyze_helper_frames, reviewed_write_inventory
from .ssp_lineage import reviewed_ssp_lineage, analyze_ssp_lineage
from .cal_rt_semantics import semantics_contract, architecture_aliases, memory_applicability

STATIC = 'StaticCalRtFrameProvenance_NotCpuExecution'
RESEARCH = 'CONDITIONAL_FRAME_INTEGRITY_ESTABLISHED / EXECUTION_BLOCKED'
EXPECTED_CONTRACT = {
    'schemaVersion': 1, 'milestone': 'M2cd', 'classification': STATIC,
    'baseSha': 'd461861c8a8714d34d66d5933646e4158b6adbc4',
    'baseSourceFingerprintSha256': '0ba9e36333aa73ea87fef7e11a97213a70ad2e9e110060f07e11d52372b61689',
    'callerPC': 0x27D0, 'calleeEntryPC': 0x5F45, 'requiredReturnPC': 0x27D3,
    'calLength': 3, 'rtConsumerPC': 0x60E4, 'rtForm': 'RT_NotRTI',
    'sspCandidateSource': 0x24F8, 'conditionalSspCandidate': 0x047E, 'conditionalColdScb': 0,
    'nativeIncomingSspEstablished': False, 'helperNodes': 226, 'helperEdges': 253,
    'helperMustMayWriteRows': 238, 'frameWidth': 16, 'byteOrder': 'LittleEndian',
    'alignment': 'WordAddressMasksBit0_NotAnOddSspHardwareBan',
    'counterexampleFrameAddresses': [0x0382, 0x0006],
    'preservedHistoryMayBeImportedFromTechnicalSnapshot': False,
    'sourceConditionsAreObservedNativeProof': False,
    'inventedConstraintCases': 12, 'analysisRecords': 5, 'negativeRequirementCategories': 33,
    'runtimeAdmissionGranted': False, 'actualFrameReadAdmitted': False,
    'actualNativeInstructionIndex': None, 'actualLogicalWriteOrdinal': None,
    'actualRawByteWriteOrdinals': None, 'actualAllNativeWriteOrdinal': None,
    'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0, 'actualRetiredInstructions': 0,
    'InheritedHistoricalGeneratedRunnerExceptions': 1, 'AuthorizedExternalToolingExceptions': 1,
    'AuthorizedPreservationExceptions': 2, 'StrictHistoricalPreservationPass': False,
    'researchClassification': RESEARCH, 'firmwareReady': False,
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
        allow_nan=False).encode('ascii')


def validate_contract(value):
    if canonical(value) != canonical(EXPECTED_CONTRACT):
        raise ValueError('FrozenExactM2cdContractRequired')
    return value


def read_contract():
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('DuplicateContractField')
            result[key] = value
        return result
    value = json.loads(Path(__file__).with_name('contract.json').read_bytes(), object_pairs_hook=unique)
    return validate_contract(value)


def example(name='conditional-047e', incoming=0x047E, kind='Conditional24F8'):
    creator = 'model:' + name + ':CAL27D0'
    return {'caseId': name, 'classification': 'InventedOnly_FrameSpecification', 'machineId': 'model:' + name,
        'incomingSSP': incoming, 'source': {'kind': kind,
            'ownerId': None if kind == 'Unknown' else 'model:' + name + ':SSP-source',
            'conditions': {key: True for key in CONDITIONS}},
        'context': {'page': 0x0200, 'local': 0x0208, 'usp': 0x0180, 'scb': 0,
            'accumulatorMode': 'ExplicitOrdinaryInvented', 'mapping': 'InventedWritableRetainedData',
            'asyncHistory': 'ExplicitNoAsyncHypothesis'},
        'call': {'pc': 0x27D0, 'length': 3, 'target': 0x5F45, 'returnPc': 0x27D3, 'creator': creator},
        'helper': {'normalReturn': 'AssumedReviewedPredicates', 'finalA': 0x0500, 'programBit': 0},
        'events': [], 'consumer': {'pc': 0x60E4, 'form': 'RT', 'creator': creator, 'machine': 'model:' + name}}


def event(case, *, address, value, kind='Write', width=2, suffix='extra-write', pc=0x7000):
    return {'eventId': 'model:' + case['caseId'] + ':' + suffix, 'machine': case['machineId'],
        'kind': kind, 'pc': pc, 'address': address, 'widthBytes': width, 'value': value}


def curated_cases():
    cases = [example()]
    row = example('conditional-047e-other-bit'); row['helper'].update(programBit=1, finalA=0x0700); cases.append(row)
    cases.append(example('odd-047f-arithmetic', 0x047F, 'InventedHostOnly'))
    cases.append(example('high-fffe-invented-memory', 0xFFFE, 'InventedHostOnly'))
    cases.append(example('unknown-incoming', None, 'Unknown'))
    cases.append(example('counterexample-0382', 0x0382, 'InventedHostOnly'))
    cases.append(example('counterexample-0006', 0x0006, 'InventedHostOnly'))
    for name, key in (('missing-prior-276a', 'cal276A'), ('missing-prior-2777', 'cal2777')):
        row = example(name); row['source']['conditions'][key] = None; cases.append(row)
    row = example('unestablished-asic-map'); row['context']['mapping'] = 'UnknownAsic'; cases.append(row)
    row = example('unknown-asynchronous-history'); row['context']['asyncHistory'] = 'Unknown'; cases.append(row)
    row = example('same-value-new-storage'); row['events'].append(event(row, address=0x047E, value=0x27D3, kind='SameValueWrite')); cases.append(row)
    return cases


def verify_case(case, claimed=None):
    from .reference_oracle import reference_case
    inventory = reviewed_write_inventory()
    actual, expected = evaluate(case, inventory), reference_case(case, inventory)
    if canonical(actual) != canonical(expected) or claimed is not None and canonical(claimed) != canonical(expected):
        raise ValueError('IndependentFullFrameProvenanceMismatch')
    return actual


def native_frame_obligations():
    return {'classification': STATIC, 'callerPC': 0x27D0, 'rtConsumerPC': 0x60E4, 'requiredReturnPC': 0x27D3,
        'requiredFutureWitness': ['SameActualCpuBusAndProgramSource', 'ActualIncomingSspOwnerAndContext',
            'CALInstructionIndex', 'FrameLogicalAndRawByteAndAllNativeWriteOrdinals',
            'EveryInterveningWriteIncludingSameValue', 'CurrentFrameGenerationAndCreator',
            'RTInstructionIndexAndActualReadLinkage', 'NoHostReseedOrCallerSnapshotRestore'],
        'frameAliases': architecture_aliases(), 'nativeEvents': None, 'actualNativeInstructionIndex': None,
        'actualLogicalWriteOrdinal': None, 'actualRawByteWriteOrdinals': None, 'actualAllNativeWriteOrdinal': None,
        'actualFrameReadAdmitted': False, 'runtimeAdmissionGranted': False,
        'modelEventIdsAreNativeOrdinals': False, 'retirementCountsArePhysicalTime': False,
        'fullPswScbSspOrSfMayBeDefaulted': False, 'firmwareReady': False}


def minimum_frontier():
    return {'classification': STATIC, 'sourcePC': 0x24F8, 'conditionalCandidate': 0x047E,
        'actualIncomingSSP': None, 'actualIncomingSspOwner': None,
        'earliestReach': 'ApplicableResetOrIndependentHistoryBefore24ED',
        'firstControl': 0x24F4, 'firstExternalRead': 0x251C, 'firstUnobservedMatchedCall': 0x2689,
        'specificReturns': [
            {'caller': 0x2689, 'callee': 0x5C5C, 'rt': 0x5C80, 'return': 0x268C},
            {'caller': 0x268D, 'callee': 0x5C5C, 'rt': 0x5C80, 'return': 0x2690},
            {'caller': 0x276A, 'callee': 0x5C86, 'rt': 0x5CCD, 'return': 0x276D},
            {'caller': 0x2777, 'callee': 0x5CD9, 'rt': 0x5CF9, 'return': 0x277A}],
        'newPrior2777Read': {'pc': 0x5CDC, 'address': 0x03D1, 'candidateWriter': 0x5CAF,
            'candidateIndex': 3, 'c8PrimaryConflictSites': [0x5CDF, 0x5CE7],
            'firstErrorCounterSource': 0x2773, 'fault': 0x5CF8},
        'A_Source24F8To27D0': 'EarliestSourceAuthorityRoute_StillNeedsReachingGatesAndEverySpecificPriorReturn',
        'B_Previous276A2777': 'NextConcreteLaterCallGap_AfterEarlier2689_268DHistory_2777NowNarrowedTo03D1AndC8',
        'C_Helper047EPreservation': 'LocalSynchronousDisjointnessEstablished_DoesNotSupplyEarlierSourceOrAsicMap',
        'earliestBlockerRemovedByC': False, 'proposedFirstRuntime': None,
        'smallestNextEvidence': 'NarrowRooted2689OwnFrameAndRestorationAfterApplicableColdEntryGates_Then276AAnd2777Owners',
        'independentLaterTask': 'Resolve2777_03D1OwnerAndPrimaryC8ReturnPredicatesWithoutChoosingHostInput',
        'stillUnknownAfterLocal047EProof': ['NativeIncomingSSP', 'ActualAsicWritableRetainedMapping',
            'SFApplicabilityAndStackSafety', 'RealPriorReturns', 'AsynchronousHistory', 'ProducerToReceiverBridge'],
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0, 'actualRetiredInstructions': 0,
        'firmwareReady': False}


def canonical_records():
    read_contract()
    records = [{'caseId': name, 'classification': STATIC, 'data': data,
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0}
        for name, data in (
            ('primary-cal-rt-architecture', {'semantics': semantics_contract(), 'memory': memory_applicability()}),
            ('ssp-source-and-predecessors', {'reviewed': reviewed_ssp_lineage(), 'analysis': analyze_ssp_lineage()}),
            ('helper-writes-frame-matrix-and-termination', analyze_helper_frames()),
            ('matching-native-frame-obligations', native_frame_obligations()),
            ('minimum-missing-evidence-frontier', minimum_frontier()))]
    for case in curated_cases():
        records.append({'caseId': case['caseId'], 'classification': STATIC,
            'data': {'input': case, 'result': verify_case(case),
                'independentFullConstraintComparison': 'PASS',
                'comparisonScope': 'InventedFrameRelations_NotProductionCpuTrace'},
            'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0})
    return json.loads(json.dumps(records, ensure_ascii=True, allow_nan=False))
