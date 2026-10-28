"""Finite static bridge obligations and new invented relational controls."""
from copy import deepcopy
import json
from pathlib import Path

from native_data0217_011f_bridge.constraint_model import INVENTED, STATIC, solve

BASE = '8c4d573c7b745a4021d7da4c2b318ac07c800633'
EXPECTED_CONTRACT = {
    'schemaVersion': 1, 'milestone': 'M2cc', 'baseSha': BASE,
    'baseSourceCount': 1150,
    'baseSourceFingerprintSha256': 'cc6d2297ef3ef05ecb774ca734c16e6a2b50a83614476c31040dcf082467f84e',
    'classification': STATIC,
    'timelineScope': 'SingleCompletedProducerHelperThenSingleAssumedReceiverInvocation',
    'producer': {'programAddress': 0x60EC, 'space': 'PROGRAM', 'sourceBit': 7,
        'pcs': [0x5F66, 0x5F6A, 0x5F6B], 'lengths': [4, 1, 3], 'targetAddress': 0x0217, 'targetBit': 3},
    'callers': [{'pc': 0x27D0, 'returnPc': 0x27D3}, {'pc': 0x4069, 'returnPc': 0x406C}],
    'helper': {'entry': 0x5F45, 'return': 0x60E4, 'nodes': 226, 'edges': 253,
        'producerPrefixInstruction': 14, 'laterRetainingByteWriter': 0x6039,
        'selectedBitOwnerIsWholeByteGeneration': False},
    'copyRoots': [0x0379, 0x03ED], 'copyWriters': [0x5C35, 0x0408], 'readerPc': 0x064C,
    'selectedBitProofRequiresAllNeighborOwners': False,
    'selectedBitProofAdmitsActualByteRead': False,
    'staticAssumedIrqIsObservedDelivery': False,
    'nativeGenerationsMayBeImported': False,
    'sourceApprovalPolicy': 'SeparateExplicitReviewAndLiteralPin_NotSelfApproval',
    'InheritedHistoricalGeneratedRunnerExceptions': 1, 'AuthorizedExternalToolingExceptions': 1,
    'AuthorizedPreservationExceptions': 2, 'StrictHistoricalPreservationPass': False,
    'newUnauthorizedProtectedDifferencesRequired': 0,
    'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0, 'actualRetiredInstructions': 0,
    'runtimeAdmissionGranted': False, 'firmwareReady': False,
}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False)


def validate_contract(value):
    if canonical(value) != canonical(EXPECTED_CONTRACT):
        raise ValueError('ExactClosedM2ccContractRequired')
    return True


def read_contract():
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('DuplicateContractKey')
            result[key] = value
        return result
    path = Path(__file__).with_name('contract.json')
    if path.stat().st_size > 16384:
        raise ValueError('BoundedContractRequired')
    result = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique)
    validate_contract(result)
    return result


def renumber(case):
    for index, event in enumerate(case['events']):
        event.update(machine=case['machineId'], ordinal=index + 1)
    return case


def example(case_id='invented-p-int1-bit0', caller=0x27D0, root=0x0379, bit=0):
    machine = 'invented:' + case_id
    known_neighbors = root == 0x03ED
    byte = 0x20 | bit << 3
    result = {'caseId': case_id, 'machineId': machine, 'classification': INVENTED,
        'callerPc': caller, 'copyRoot': root, 'programByte': 0x35 | bit << 7,
        'previousProgramByte': 0x81, 'sourceIdentity': 'invented:' + case_id + ':program',
        'incoming': {'ah': 0x34 if caller == 0x27D0 else 0xC7, 'hc': 1, 'otherPsw': 0x0125,
            'dd': int(caller == 0x4069), 'ssp': 0x07E0,
            'bufferByte': byte if known_neighbors else None, 'targetByte': byte if known_neighbors else None},
        'context': {'producerPage': 0x0200, 'copyLrb': 0x0021, 'copyUsp': 0x0280, 'copyScb': 2,
            'sourceHistory': case_id, 'context012A': case_id, 'earlierCalls': [], 'old012ABit3': 0},
        'hypotheses': {'helperPredicatesSatisfied': True, 'aliasesDisjoint': True,
            'irqFrameAssumedSafe': True, 'receiverPredicatesSatisfied': True},
        'events': [
            {'kind': 'call', 'pc': caller, 'returnPc': caller + 3, 'frameWord': caller + 3},
            {'kind': 'producer', 'pc': 0x5F6B, 'programAddress': 0x60EC, 'sourceSpace': 'PROGRAM',
                'sourceBit': 7, 'shift': 'SLLB A', 'dd': 0, 'page': 0x0200, 'hostCf': None},
            {'kind': 'retainedRmw', 'pc': 0x6039, 'bit': 6, 'value': 0},
            {'kind': 'return', 'pc': 0x60E4, 'returnPc': caller + 3, 'frameCallerPc': caller, 'frameOrdinal': 1},
            {'kind': 'external', 'receiver': root, 'evidence': 'ExplicitAssumptionOnly', 'actualDelivery': False},
            {'kind': 'copy', 'loadPc': 0x5C33 if root == 0x0379 else 0x0406,
                'writerPc': 0x5C35 if root == 0x0379 else 0x0408,
                'sourceWord': 0x0216, 'targetWord': 0x011E, 'width': 16,
                'endian': 'little', 'accumulatorMutated': False},
            {'kind': 'reader', 'pc': 0x064C, 'address': 0x011F, 'bit': 3, 'actualRead': False},
        ]}
    return renumber(result)


def curated_cases():
    cases = [example('invented-' + name + '-' + receiver + '-bit' + str(bit), caller, root, bit)
        for name, caller in (('p', 0x27D0), ('q', 0x4069))
        for receiver, root in (('int1', 0x0379), ('serial', 0x03ED)) for bit in (0, 1)]
    item = example('blocked-missing-external'); item['events'][4]['evidence'] = 'Missing'; cases.append(item)
    item = example('blocked-missing-frame'); item['hypotheses']['irqFrameAssumedSafe'] = False; cases.append(item)
    item = example('blocked-alias'); item['hypotheses']['aliasesDisjoint'] = False; cases.append(item)
    item = example('unsatisfiable-producer-bypass'); item['events'].pop(1); renumber(item); cases.append(item)
    return cases


def verify_case(case, claimed=None):
    from native_data0217_011f_bridge.reference_oracle import reference_case
    actual, expected = solve(case), reference_case(case)
    if canonical(actual) != canonical(expected) or claimed is not None and canonical(claimed) != canonical(expected):
        raise ValueError('IndependentFullConstraintStateMismatch')
    return actual


def generation_obligations():
    return {
        'classification': STATIC, 'sourceToken': 'PROGRAM60EC.bit7',
        'producer': 0x5F6B, 'laterByteWriter': 0x6039,
        'selectedBitSemanticProducerRetainedAfter6039': True,
        'wholeByteStorageGenerationUnchangedAfter6039': False,
        'sameValueWriteCreatesFreshStorageGeneration': True,
        'sourceRetainedUntilCopy': 'ConditionalOnNoSelectedBitOrOverlappingWriter',
        'targetRetainedUntil064C': 'ConditionalOnNoSelectedBitOrOverlappingWriter',
        'selectedBitSemanticLineage': 'EstablishedConditionalRelationship_NotActualGeneration',
        'wholeByteClassification': 'WholeByteValueNotFullyOwned', 'actualByteReadAdmitted': False,
        'neighborValuesMayBeFilledFromSelectedBit': False,
        'unknownSourceOverwriteAfterCopyNecessarilyDestroysTargetToken': False,
        'mandatoryFrameCounterexample': {'evenSsp': 0x0382, 'writerPc': 0x60E3,
            'overwritingWords': [0x0500, 0x0700], 'matchingEitherCallerReturn': False},
        'mandatoryAccumulatorFrameCounterexample': {'evenSsp': 0x0006,
            'finalA': [0x0500, 0x0700], 'matchingEitherCallerLowReturnByte': False},
        'conservativeFrameDomainsCannotBeDeclaredDisjoint': ['0000..00BF', '0200..02FF', '0356'],
        'architecturalEffectsScope': 'MandatoryPrefixAndTrioRelationships_NotWholeHelperCpuTrace',
        'producerSourcePage': 0x0200, 'receiverPage': 0x0100,
        'reuseAliasLibrary': 'native_data011f_011b_ownership.alias_analysis',
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0, 'actualRetiredInstructions': 0,
    }


def minimum_frontier():
    return {
        'classification': STATIC,
        'P': {'caller': 0x27D0, 'requiredReturn': 0x27D3, 'helperRt': 0x60E4,
            'firstPostReturnUnprovedCall': 0x2810, 'callee': 0x5BF5, 'returnPc': 0x2813},
        'Q': {'caller': 0x4069, 'requiredEarlierCall': 0x4068, 'requiredReturn': 0x406C,
            'helperRt': 0x60E4, 'firstPostReturnUnprovedCall': 0x4165,
            'callee': 0x28AE, 'returnPc': 0x4166,
            'mieClear': 0x4077, 'mieSet': 0x4133},
        'firstSharedExternalGap': 'NoListedProducerReturnToReceiverEdge_RealPendingIeMiePriorityAndFrameNotEstablished',
        'INT1': {'vector': 0x0026, 'irqIeBit': 15, 'entry': 0x0379,
            'copyCaller': 0x038A, 'copyHelper': 0x5C2B, 'copyWriter': 0x5C35,
            'copyRt': 0x5C3F, 'copyReturn': 0x038D},
        'serial': {'vector': 0x000E, 'irqIeBit': 3, 'entry': 0x03ED,
            'copyLoad': 0x0406, 'copyWriter': 0x0408, 'readerBypassGate': 0x040E},
        'comparison': {'serialAvoidsExtraCopyHelperCalFrame': True,
            'irqSourcesInterchangeable': False, 'provenIntegratedWinner': None,
            'reason': 'BothNeedUnobservedDistinctExternalEventsAndOwnFramesContexts'},
        'doNotRetroactivelyExtend063BSession': True,
        'sourceFullByteReadAdmission': 'NotGrantedByBitLineage',
        'actualProducerGeneration': 'NotObserved', 'actualCopyGeneration': 'NotObserved',
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0, 'firmwareReady': False,
    }


def canonical_records():
    from native_data0217_011f_bridge.helper_cfg import analyze_helper, reviewed_helper
    from native_data0217_011f_bridge.bridge_reachability import analyze_bridges
    read_contract()
    records = [{'caseId': name, 'classification': STATIC, 'data': value,
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0}
        for name, value in (
            ('helper-cfg-and-entry-contracts', {'reviewed': reviewed_helper(), 'properties': analyze_helper()}),
            ('producer-to-copy-bridges', analyze_bridges()),
            ('generation-and-alias-obligations', generation_obligations()),
            ('minimum-missing-evidence-frontier', minimum_frontier()))]
    for case in curated_cases():
        records.append({'caseId': case['caseId'], 'classification': STATIC,
            'data': {'input': case, 'result': verify_case(case),
                'independentFullConstraintComparison': 'PASS',
                'comparisonScope': 'InventedRelationalConstraints_NotProductionCpuTrace'},
            'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0})
    # Normalize integer CFG keys before sorting canonical JSON, preserving all
    # fields/values and making parse/re-serialization byte-stable on both OSes.
    return json.loads(json.dumps(records, ensure_ascii=True, allow_nan=False))
