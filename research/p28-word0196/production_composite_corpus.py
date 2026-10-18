"""M2bq source draft: unchanged M2bn seeds, with explicit pair identities.

No production Cpu, Bus, decoding, execution, output file, process or clock is
used here. Additional boundary/refusal controls never alter the 5470 corpus.
"""

from copy import deepcopy
from hashlib import sha256
from production_composite_common import canonical, reference_modules, require

EXPECTED_COUNTS = {"baseCases": 2735, "executions": 5470, "internalSfPairs": 2735,
                   "retirements": 73784, "logicalReads": 49112, "logicalWrites": 19162}


def case_key(case):
    require(type(case["case_id"]) is str and type(case["internal_sf"]) is bool, "ClosedCaseKey")
    return [case["case_id"], case["internal_sf"]]


def iter_cases(root):
    with reference_modules(root) as modules:
        corpus = modules["synthetic_composite_execution_corpus"]
        seen = set()
        count = 0
        prior = None
        for item in corpus.iter_cases():
            key = case_key(item)
            require(tuple(key) not in seen, "DuplicateCaseAndInternalSf")
            seen.add(tuple(key))
            if count % 2 == 0:
                require(key[1] is False, "SfPairStartsFalse")
                prior = deepcopy(item)
            else:
                peer = deepcopy(item)
                require(key[1] is True and key[0] == prior["case_id"], "AdjacentSameSeedSfPair")
                peer["internal_sf"] = False
                require(peer == prior, "SfPairMustDifferOnlyInternalField")
            count += 1
            yield item
        require(count == EXPECTED_COUNTS["executions"], "ExactUnchanged5470Cases")


def seed_digest(root):
    digest, count = sha256(), 0
    for item in iter_cases(root):
        digest.update(canonical(item) + b"\n")
        count += 1
    return {"classification": "OrderedUnchangedM2bnInventedSeedStream", "records": count,
            "sha256": digest.hexdigest(), "key": ["case_id", "internal_sf"]}


def iter_psw_admission_expectations():
    """All 65536 validations are admission-only; none constructs a Cpu."""
    for value in range(65536):
        yield {"psw": value, "accepted": value & 0x0CC8 == 0x0CC8,
               "cpu_instances": 0, "bus_instances": 0, "step_calls": 0}


def coverage(root):
    with reference_modules(root) as modules:
        result = modules["synthetic_composite_execution_corpus"].coverage_summary()
    require(result["baseCases"] == 2735 and result["executionsWithInternalSfPairs"] == 5470,
            "UnchangedCorpusCardinality")
    require((result["expectedRetirements"], result["expectedLogicalReads"], result["expectedWrites"])
            == (73784, 49112, 19162), "IndependentExpectedTotals")
    return {"classification": "ExpectedCoverage_NotExecutionEvidence", "original": result,
            "caseIdentity": ["case_id", "internal_sf"], "required": deepcopy(EXPECTED_COUNTS),
            "separateBoundaryControls": [255, 256], "extraPositiveCompositeCases": 0}
