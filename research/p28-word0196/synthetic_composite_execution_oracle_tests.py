"""M2bn independent, bounded reference checks; never invokes a Rust CPU.

Runtime observation sensitivity is exposed by the oracle and must separately be
run on actual independently passing observations by the execution validator.
These static checks are not counted as composite executions or admission runs.
"""

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import synthetic_composite_execution_corpus as corpus
import synthetic_composite_execution_oracle as oracle


def require(condition, label):
    if not condition:
        raise AssertionError(label)


def static_checks(repository_root):
    patterns = oracle.load_instrumentation_patterns(repository_root)
    summary = corpus.coverage_summary()
    require(summary["baseCases"] == 2735 and summary["cpuInstances"] == 5470,
            "IndependentFiniteFamilySum")
    rows, flag_sets, same_sites, identities = Counter(), {}, set(), set()
    compact_hash, expectation_hash = sha256(), sha256()
    first_by_path, short = {}, []
    cases = list(corpus.iter_base_cases())
    require(len({case["case_id"] for case in cases}) == len(cases), "UniqueBaseCaseIdentities")
    for case in cases:
        untouched = deepcopy(case)
        expected = oracle.expected_case(case, patterns)
        require(case == untouched, "ExpectationDoesNotMutateEntry")
        path = case["path"]
        rows[path] += 1
        first_by_path.setdefault(path, (case, expected))
        instructions, reads, writes = corpus.PATH_COUNTS[path]
        require(expected["retired_instructions"] == instructions, "ExactPathInstructionBudget")
        require(len(expected["steps"]) == instructions, "FullStepCount")
        require(sum(event["operation"] == "Read" for event in expected["data_journal"]) == reads,
                "ExactLogicalReadCount")
        require(sum(event["operation"] == "Write" for event in expected["data_journal"]) == writes,
                "ExactWriteCount")
        require(len(expected["raw_data_journal"]) == reads + writes + 1,
                "OneActualLogicalLe16RequiresTwoOrderedBytes")
        require(expected["before"] == case["entry"], "WholeEntryEqualityIncludingAllPointingBanks")
        require(expected["after"]["pointing_banks"] == case["entry"]["pointing_banks"],
                "All32PointingWordsRetained")
        for key in ("ah", "hc", "other_psw", "lrb", "scb", "ssp", "sf", "halted"):
            require(expected["before"][key] == expected["after"][key], "WholeRetainedContext:" + key)
        require(expected["after"]["cf"] == (path == "A") and not expected["after"]["zf"]
                and not expected["after"]["dd"], "TerminalFlags")
        require(expected["steps"][0]["before"]["dd"] == case["entry"]["dd"]
                and not expected["steps"][0]["after"]["dd"], "FirstActualLbResponsibleForDdZero")
        for before, after in zip(expected["steps"], expected["steps"][1:]):
            require(before["after"] == after["before"], "SourceStateContinuity")
        require(all(event["address"] < 0x1033 and event["serviced"]
                    and event["refusal"] is None for event in expected["program_events"]),
                "NoPositiveExternalFetchExpected")
        require(expected["steps"][-1]["form"] == "j-address"
                and expected["direct_j_count"] == 1, "OneFinalDirectJ")
        require(expected["external_transfer"] == (0x55C5 if path == "A" else 0x5596),
                "ActualTargetIdentityObligation")
        require(sum(step["form"] == "j-address" for step in expected["steps"]) == 1,
                "NoSecondOrZeroStepJ")
        if path == "B":
            require(not any(event["address"] == 0x124 for event in expected["data_journal"]),
                    "FirstGateSuppressesSecondFunctionalRead")
        if path in ("C", "D"):
            require(sum(event["address"] == 0x124 and event["operation"] == "Read"
                        for event in expected["data_journal"]) == 1, "SecondGateMustBeRead")
        for event in expected["data_journal"]:
            if event["operation"] == "Write" and event["same_value"]:
                same_sites.add(next(step["node_identity"] for step in expected["steps"]
                                    if step["pc_before"] == event["pc"]))
        identities.update(step["node_identity"] for step in expected["steps"])
        if case["family"] == "path-dd-flags":
            flag_sets.setdefault(path, set()).add(tuple(case["entry"][name]
                                                      for name in ("dd", "cf", "zf", "hc")))
        if case["family"] == "short-circuit-b":
            short.append((case, expected))
        if case["family"] == "carry-dependencies":
            x = case["data"][str(0x18E)]
            shift, rotate, compare, branch = [expected["steps"][index] for index in (1, 2, 5, 6)]
            require(shift["after"]["cf"] == bool(x & 128), "ShiftBit7CarryDependency")
            require(rotate["before"]["cf"] == shift["after"]["cf"], "RolIncomingCarryContinuity")
            rotate_write = expected["data_journal"][rotate["logical_end"] - 1]
            require(rotate_write["value"] == ((2 * x + (x >> 7)) & 255), "RolThroughIncomingCf")
            word = case["data"][str(0x196)] + 256 * case["data"][str(0x197)]
            require(compare["after"]["cf"] == (word < 192)
                    and compare["after"]["zf"] == (word == 192), "UnsignedCompareBorrowAndEquality")
            require(branch["branch_taken"] == compare["after"]["cf"], "JltConsumesActualCf")
        compact_hash.update(corpus.canonical_json(oracle.c11_expected_projection(case)) + b"\n")
        expectation_hash.update(corpus.canonical_json(expected) + b"\n")
    require(all(len(flags) == 16 for flags in flag_sets.values()) and len(flag_sets) == 4,
            "AllFourPathsBothDdAllEightCfZfHcCombinations")
    require(same_sites == {"5572", "557F", "5582", "558B", "558E", "55C1", "55C3"},
            "SameValueWriteAtEveryReachableSite")
    require(identities == set(oracle.NODE_IDENTITIES), "AllTwentyLogicalNodes")
    require(len(short) == 4, "FourControlledShortCircuitCases")
    require(len({tuple((event["address"], event["operation"], event["value"])
                       for event in expected["data_journal"]) for _, expected in short}) == 1,
            "SecondGateVariationsDoNotChangeBFunctionalEffects")
    require(len({(expected["after"]["a"], expected["after"]["psw"])
                 for _, expected in short}) == 1, "ShortCircuitFinalScalarStateInvariant")
    strict_refusals = []
    for expected, actual, label in ((False, 0, "bool-not-int"), ({"a": 1}, {}, "missing-field"),
                                    ([1, 2], [2, 1], "ordered-events"),
                                    ({"a": 1}, {"a": 1, "b": 2}, "extra-field")):
        mismatch = oracle.first_difference(expected, actual)
        require(mismatch is not None, "StrictComparatorSensitivity:" + label)
        strict_refusals.append({"name": label, "firstMismatch": mismatch})
    source_bindings = []
    for name, digest in oracle.SOURCE_BINDINGS.items():
        path = Path(repository_root) / "research/p28-word0196" / name
        actual_digest = sha256(path.read_bytes()).hexdigest()
        require(actual_digest == digest, "FrozenIndependentSourceIdentity:" + name)
        source_bindings.append({"path": name, "sha256": actual_digest})
    return {"classification": "IndependentStaticCorpusAndReferenceChecks_NotCPUExecution",
            "passed": True, "staticBaseCasesChecked": len(cases), "coverage": summary,
            "allTwentyNodeIdentities": sorted(identities), "sameValueWriterSites": sorted(same_sites),
            "strictComparatorChecks": strict_refusals,
            "baseExpectedSemanticStreamSha256": expectation_hash.hexdigest(),
            "baseCompactC11ExpectationStreamSha256": compact_hash.hexdigest(),
            "sourceBindings": source_bindings, "CPUExecutions": 0,
            "actualROMExecutions": 0, "targetBinaryOutputs": 0,
            "failures": 0, "skipped": 0}


if __name__ == "__main__":
    print(json.dumps(static_checks(Path(__file__).resolve().parents[2]),
                     sort_keys=True, separators=(",", ":")))
