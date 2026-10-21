"""M2br private draft: exactly the sealed immutable M2bq invented input file.

The input's old entry PC1000 is not rewritten. The new constructor separately
initializes the fresh invented caller CPU at0FF0 before any execution. This is
not a transfer-time PC assignment. All original inputs and pair order remain.
"""

from copy import deepcopy
from hashlib import sha256
from production_transfer_common import bq_modules, canonical, first_difference, require

EXPECTED = {"positiveCases": 5470, "internalSfPairs": 2735,
            "pathCounts": {"A": 1396, "B": 1360, "C": 1338, "D": 1376},
            "callerRetirements": 5470, "compositeRetirements": 73784,
            "continuationRetirements": 5470, "totalRetirements": 84724,
            "logicalReads": 49112, "logicalWrites": 19162,
            "rawFunctionalReads": 54582, "rawFunctionalWrites": 19162,
            "softwareAccountingCycles": 448100, "programCallbacks": 2551820,
            "separateSmokeCases": 4, "separateSmokeRetirements": 62,
            "separateSmokeLogicalReads": 36, "separateSmokeLogicalWrites": 14,
            "separateSmokeSoftwareAccountingCycles": 328, "separateSmokeProgramCallbacks": 1870}
PATH_EXPECTATIONS = {
    "A": {"composite_retirements": 11, "total_retirements": 13,
          "composite_cycles": 55, "total_cycles": 66, "reads": 5, "writes": 3,
          "continuation": "ContinuationBelow", "checkpoint": 0x55C7},
    "B": {"composite_retirements": 13, "total_retirements": 15,
          "composite_cycles": 69, "total_cycles": 80, "reads": 9, "writes": 3,
          "continuation": "ContinuationNotBelow", "checkpoint": 0x5598},
    "C": {"composite_retirements": 14, "total_retirements": 16,
          "composite_cycles": 75, "total_cycles": 86, "reads": 10, "writes": 3,
          "continuation": "ContinuationNotBelow", "checkpoint": 0x5598},
    "D": {"composite_retirements": 16, "total_retirements": 18,
          "composite_cycles": 85, "total_cycles": 96, "reads": 12, "writes": 5,
          "continuation": "ContinuationNotBelow", "checkpoint": 0x5598},
}
ENTRY_TRANSFORMATION = {"inputEntryPcUnchanged": 0x1000, "freshInitialCpuPc": 0x0FF0,
                        "reason": "AuthorizedInventedCallerConstructorContext_BeforeFirstInstruction",
                        "inputFieldsChanged": 0, "transferBoundaryPcAssignmentAllowed": False}


def historical_case(request):
    require(type(request) is dict and type(request["entry"]) is dict
            and request["entry"]["pc"] == 0x1000, "UnchangedSealedHistoricalInputEntry")
    return deepcopy(request)


def case_key(request):
    require(type(request["case_id"]) is str and type(request["internal_sf"]) is bool,
            "ExactCaseAndInternalSfKey")
    return [request["case_id"], request["internal_sf"]]


def iter_cases(root):
    with bq_modules(root) as modules:
        corpus = modules["production_composite_corpus"]
        count = 0
        for original in corpus.iter_cases(root):
            require(original["entry"]["pc"] == 0x1000, "SealedHistoricalEntry")
            request = deepcopy(original)
            require(first_difference(original, historical_case(request)) is None,
                    "EveryM2bqInputFieldRetainedByteForByte")
            count += 1
            yield request
        require(count == 5470, "ExactUnchangedPositive5470")


def smoke_cases(root):
    selected = {}
    iterator = iter_cases(root)
    try:
        for case in iterator:
            if case["internal_sf"] is False and case["path"] not in selected:
                selected[case["path"]] = deepcopy(case)
            if len(selected) == 4:
                break
    finally:
        iterator.close()
    require(set(selected) == set("ABCD"), "FourIndependentInitialSmokeSeeds")
    return [selected[path] for path in "ABCD"]


def seed_digests(root):
    historical, transfer, count = sha256(), sha256(), 0
    for request in iter_cases(root):
        historical.update(canonical(historical_case(request)) + b"\n")
        transfer.update(canonical(request) + b"\n")
        count += 1
    return {"classification": "PreRuntimeIndependentInputIdentity_NotExecutionEvidence",
            "records": count, "caseKey": ["case_id", "internal_sf"],
            "historicalM2bqSeedSha256": historical.hexdigest(), "transferSeedSha256": transfer.hexdigest(),
            "declaredEntryTransformation": deepcopy(ENTRY_TRANSFORMATION)}


def psw_expectations():
    for value in range(65536):
        yield {"psw": value, "accepted": value & 0x0CC8 == 0x0CC8,
               "cpu_instances": 0, "bus_instances": 0, "step_calls": 0}
