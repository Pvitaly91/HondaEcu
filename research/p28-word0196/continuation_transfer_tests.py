"""Independent invented continuation constraints; no codec or CPU execution."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

from continuation_transfer_oracle import (
    FAILURE_CODES, LENGTHS, TARGETS, expected_hypothesis, expected_path_rows,
    expected_scalar, expected_transfer, relative_origin_interval, transfer_failure,
)

HERE = Path(__file__).resolve().parent
PROOF_LEVELS = {
    "continuationPC": "OriginalContinuationPCIdentified",
    "mapping": "PathToExitMappingSpecified",
    "context": "StaticContextNoninterferenceRequirementsSpecified",
    "nativeExitIsolation": "NativeExitIsolationNotEstablished",
    "actualDownstreamRejoin": "ActualDownstreamRejoinNotEstablished",
    "targetCodeGeneration": "TargetCodeGenerationNotReady",
    "firmwareIntegration": "FirmwareIntegrationNotEstablished",
}


def stable(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def contract_mutations(model, upstream):
    """Real fields/relations, with independent preimplementation refusal reasons."""
    rows = []
    def add(label, mutate, code, stage, domain):
        candidate, old = copy.deepcopy(model), copy.deepcopy(upstream)
        mutate(candidate, old)
        rows.append((label, candidate, old, code, stage, domain))
    def state(index, key, value):
        return lambda c, u: c["continuations"][index]["requiredFinalState"].__setitem__(key, value)

    add("missing-continuation", lambda c, u: c["continuations"].pop(),
        "ContinuationInventory", "Continuation", "ContinuationIdentity")
    add("extra-continuation", lambda c, u: c["continuations"].append(copy.deepcopy(c["continuations"][0])),
        "ContinuationInventory", "Continuation", "ContinuationIdentity")
    add("swapped-continuation-rows", lambda c, u: c["continuations"].reverse(),
        "ContinuationInventory", "Continuation", "ContinuationIdentity")
    add("wrong-target", lambda c, u: c["continuations"][0].__setitem__("originalTargetPC", 0x5597),
        "TargetIdentityMismatch", "Continuation", "ContinuationIdentity")
    def swap(c, u):
        c["continuations"][0]["originalTargetPC"], c["continuations"][1]["originalTargetPC"] = 0x55C5, 0x5596
    add("swapped-targets", swap, "TargetIdentityMismatch", "Continuation", "ContinuationIdentity")
    add("wrong-last-site", lambda c, u: c["continuations"][0].__setitem__("lastLogicalSiteId", 0x5592),
        "TargetIdentityMismatch", "Continuation", "ContinuationIdentity")
    add("wrong-path-to-exit", lambda c, u: c["pathToContinuation"].__setitem__("C", "Below"),
        "PathMappingMismatch", "Path", "PathRelation")
    add("wrong-row-paths", lambda c, u: c["continuations"][0].__setitem__("pathIds", ["A"]),
        "PathMappingMismatch", "Path", "PathRelation")
    add("wrong-below-AL", state(1, "AL", {"kind": "ConstantByte", "value": 16}),
        "ExitStateMismatch", "Context", "StaticExitContext")
    add("wrong-notbelow-AL", state(0, "AL", {"kind": "ConstantByte", "value": 240}),
        "ExitStateMismatch", "Context", "StaticExitContext")
    for index, branch in ((0, "NotBelow"), (1, "Below")):
        for key, bad in (("CF", 1 - index), ("ZF", 1), ("DD", 1), ("AH", "Clobbered"),
                         ("HC", "Zero"), ("OtherPSW", "Zero"), ("SCB", 2),
                         ("LRB", 34), ("SSP", 0), ("pointingRegisters", "Clobbered")):
            add(f"{branch}-{key}-clobber", state(index, key, bad),
                "ExitStateMismatch", "Context", "StaticExitContext")
    add("historical13-witness-invented",
        lambda c, u: c["continuations"][0]["requiredPathEffects"][1].__setitem__("historicalCoverage", "HistoricalNativeValidated"),
        "PathEffectsMismatch", "Context", "PathEffectsAndWitness")
    add("unordered-writes",
        lambda c, u: c["continuations"][0]["requiredPathEffects"][2]["orderedWrites"].reverse(),
        "PathEffectsMismatch", "Context", "PathEffectsAndWitness")
    add("same-value-write-dropped",
        lambda c, u: c["continuations"][1]["requiredPathEffects"][0]["orderedWrites"][0].__setitem__("sameValueWrite", "DropIfUnchanged"),
        "PathEffectsMismatch", "Context", "PathEffectsAndWitness")
    add("first-gate-added-DATA0124-read",
        lambda c, u: c["continuations"][0]["requiredPathEffects"][0]["orderedReads"].append(
            {"pc": 0x5588, "address": 0x124, "widthBits": 8, "mode": "CurrentPage", "byteOrder": "Byte"}),
        "PathEffectsMismatch", "Context", "PathEffectsAndWitness")
    for key, bad in (("stackFrameEstablished", True), ("syntheticReturnAddressAllowed", True),
                     ("additionalFunctionalRAMReadsAuthorized", True), ("additionalRAMWritesAuthorized", True),
                     ("pointerSetupWritesAuthorized", True), ("LRB", 34), ("SCB", "Fixed2"),
                     ("sameValueWrites", "Discard"), ("gateShortCircuitPreserved", False),
                     ("unknownSFMeaningStorage", "EstablishedZero"), ("targetCompilerABI", "Established"),
                     ("RAMCodeRelocationRebasesData", True)):
        add(f"noninterference-{key}",
            lambda c, u, k=key, v=bad: c["contextNoninterference"].__setitem__(k, v),
            "ContextMismatch", "Context", "SideEffectObligation")
    add("old-SSP-frame-invented",
        lambda c, u: c["upstreamStaticObligations"]["stackRequirements"].__setitem__("frameAvailability", "Established"),
        "ContextMismatch", "Context", "SideEffectObligation")
    for key, bad in (("currentDenseHypotheticalTransferOverlapsBelow", False),
                     ("positiveGap", "SafeHalt"), ("additionalTransferSpaceReserved", True),
                     ("symbolicExplicitTransfer", "AlreadyInserted")):
        add(f"terminal-{key}", lambda c, u, k=key, v=bad: c["terminalFindings"].__setitem__(k, v),
            "TerminalHazardMismatch", "Terminal", "TerminalHypothesisPolicy")
    add("STOP-as-instruction",
        lambda c, u: c["inheritedLayout"]["terminalHazardPolicy"].__setitem__("stopOpcode", True),
        "TerminalHazardMismatch", "Terminal", "TerminalHypothesisPolicy")
    add("excluded-region-free-ROM",
        lambda c, u: c["inheritedLayout"]["originalExcludedRegion"].__setitem__("classification", "FreeROM"),
        "TerminalHazardMismatch", "Terminal", "TerminalHypothesisPolicy")
    add("new-executable-sites",
        lambda c, u: c["inheritedLayout"].__setitem__("newExecutableSites", 2),
        "TerminalHazardMismatch", "Terminal", "TerminalHypothesisPolicy")
    for label, mutate in (
        ("direct-J-falsely-rel8-limited", lambda c, u: c["reachabilityRules"]["DirectJ"].__setitem__("signedRelativeLimit", 127)),
        ("direct-J-wrong-length", lambda c, u: c["reachabilityRules"]["DirectJ"].__setitem__("documentedLength", 2)),
        ("SJ-wrong-length", lambda c, u: c["reachabilityRules"]["SJ"].__setitem__("documentedLength", 3)),
        ("SJ-wrap-repair", lambda c, u: c["reachabilityRules"]["SJ"].__setitem__("noModuloRepair", False)),
        ("J-obj-as-direct", lambda c, u: c["reachabilityRules"]["IndirectJ"].__setitem__("destinationSource", "ImmediateTarget")),
        ("J-obj-forged-pointer-owner", lambda c, u: c["reachabilityRules"]["IndirectJ"].__setitem__("pointerOwner", "Established")),
        ("J-obj-extra-access-authorized", lambda c, u: c["reachabilityRules"]["IndirectJ"].__setitem__("additionalFunctionalOperandReadAuthorized", True)),
        ("native-exit-promoted", lambda c, u: c["evidenceLevels"].__setitem__("nativeExitIsolation", "Verified")),
        ("JGT-C8-promoted", lambda c, u: c["historicalStatuses"].__setitem__("JGT_C8", "Resolved")),
        ("firmware-ready", lambda c, u: c["permissions"].__setitem__("FirmwareBIN", True)),
        ("transfer-already-encoded", lambda c, u: c["counts"].__setitem__("opcodeBytesGenerated", 3)),
    ):
        add(label, mutate, "Contract", "Metadata", "ClosedMetadataPolicy_NotReachProof")
    add("old-upstream-changed", lambda c, u: u["context"].__setitem__("requiredLRB", 34),
        "UpstreamIdentity", "Upstream", "ImmutableUpstream")
    add("unknown-top-field", lambda c, u: c.__setitem__("nativeExitVerified", True),
        "ContractShape", "Metadata", "ClosedMetadataPolicy_NotReachProof")
    return rows


def scalar_negative_cases():
    rows = []
    good = expected_scalar("A", 0xF123, 0xA3, 15)["arguments"]
    def add(label, index, bad, code, stage="Context"):
        args = list(good)
        args[index] = bad
        rows.append((label, args, code, stage))
    add("path-invalid", 0, "E", "PathInvalid", "Input")
    for index, name, bad in ((1, "incoming-PSW", 65536), (2, "incoming-AH", 256),
                             (3, "final-RAM-byte", -1), (4, "actual-A", 65536),
                             (5, "actual-PSW", 65536)):
        add(name, index, bad, "ContextValueInvalid", "Input")
        add(name + "-bool", index, True, "ContextValueInvalid", "Input")
    add("below-final-RAM-not15", 3, 14, "ExitRAMMismatch")
    add("below-AL-clobber", 4, good[4] - 1, "ExitALMismatch")
    add("below-AH-clobber", 4, good[4] - 256, "ExitAHMismatch")
    for bit, name in ((15, "CF"), (14, "ZF"), (12, "DD"), (13, "HC")):
        add(f"below-{name}-clobber", 5, good[5] ^ (2 ** bit), f"Exit{name}Mismatch")
    add("below-OtherPSW-clobber", 5, good[5] ^ 1, "ExitOtherPSWMismatch")
    for name in ("B", "C", "D"):
        args = expected_scalar(name, 0xF123, 0xA3, 0x8F)["arguments"]
        wrong = list(args)
        wrong[4] -= 1
        rows.append((name + "-wrong-AL", wrong, "ExitALMismatch", "Context"))
        wrong = list(args)
        wrong[5] += 32768
        rows.append((name + "-wrong-CF", wrong, "ExitCFMismatch", "Context"))
    return rows


def main():
    if sys.argv[1:] == ["--observe-absent"]:
        assert not (HERE / "continuation_transfer_analysis.py").exists()
        print(json.dumps({"milestone": "M2bf", "kind": "AnalyzerNotImplemented", "analyzerCalls": 0,
                          "testsRun": 0, "fakeRED": False}, sort_keys=True))
        return
    assert not sys.argv[1:], "Only fixed repository metadata and invented scalars are accepted"
    from continuation_transfer_analysis import (
        TransferError, check_exit_state, evaluate_exit_obligations,
        inspect_terminal_hypothesis, transfer_geometry,
    )
    contract = json.loads((HERE / "external_continuation_contract.json").read_text(encoding="utf-8"))
    upstream = json.loads((HERE / "typed_lowering_contract.json").read_text(encoding="utf-8"))
    counts = {"geometryCalls": 0, "geometrySuccesses": 0, "geometryRefusals": 0,
              "fullOriginGeometryCalls": 0, "completeDirectTargetCalls": 0,
              "scalarSuccessCalls": 0, "scalarRefusalCalls": 0,
              "contractSuccessCalls": 0, "contractRefusalCalls": 0,
              "contractMutationLabels": 0, "hypothesisSuccessCalls": 0, "hypothesisRefusalCalls": 0,
              "hypothesisRowsCompared": 0, "existingAssignmentsCompared": 0, "immutabilityChecks": 0}
    geometry_keys, scalar_keys, mutation_keys, hypothesis_keys = set(), set(), set(), set()
    reasons, mutation_domains = {}, {}

    def reason(error, code, stage):
        assert (error.code, error.stage) == (code, stage), (error.code, error.stage, code, stage)
        assert type(error.path) is str and error.path
        assert not hasattr(error, "partialResult")
        key = stage + "/" + code
        reasons[key] = reasons.get(key, 0) + 1

    def geometry(form, origin, target):
        counts["geometryCalls"] += 1
        geometry_keys.add(stable([form, origin, target]))
        failure = transfer_failure(form, origin, target)
        try:
            actual = transfer_geometry(form, origin, target)
        except TransferError as error:
            assert failure is not None
            reason(error, *FAILURE_CODES[failure])
            counts["geometryRefusals"] += 1
        else:
            assert failure is None
            assert actual == expected_transfer(form, origin, target)
            counts["geometrySuccesses"] += 1

    for form in ("SJ-address", "J-address"):
        for target in (0x5596, 0x55C5):
            for origin in range(65536):
                geometry(form, origin, target)
                counts["fullOriginGeometryCalls"] += 1
    for origin in (0, 0xFFFD):
        for target in range(65536):
            geometry("J-address", origin, target)
            counts["completeDirectTargetCalls"] += 1
    for target in (0x5596, 0x55C5):
        for displacement in (-129, -128, -1, 0, 127, 128):
            geometry("SJ-address", target - 2 - displacement, target)
    for form, origin, target in (
        ("SJ-address", 0xFFFE, 0xFFFF), ("SJ-address", 0xFFFD, 0xFFFF),
        ("SJ-address", 126, 0), ("SJ-address", 127, 0),
        ("J-address", 0xFFFD, 0xFFFF), ("J-address", 0xFFFE, 0),
        ("J-address", 0, 65536), ("J-address", 0, -1),
        ("SJ-address", 0, 65536), ("SJ-address", 0, -1),
        ("J-address", -1, 0), ("J-address", 65536, 0),
        ("SJ-address", True, 0), ("J-address", 0, True),
        ("SJ-address", "4096", 0), ("J-address", 0, 1.0),
        ("J-obj", 0x1000, 0x5596),
        ("CAL", 0x1000, 0x5596), ("SCAL", 0x1000, 0x5596),
        ("RT", 0x1000, 0x5596), ("RTI", 0x1000, 0x5596),
        ("BRK", 0x1000, 0x5596), ("HALT", 0x1000, 0x5596),
        ("STOP", 0x1000, 0x5596), ("ConditionalAlwaysTrue", 0x1000, 0x5596),
    ):
        geometry(form, origin, target)

    def scalar(path, psw, ah, data):
        case = expected_scalar(path, psw, ah, data)
        args = case["arguments"]
        scalar_keys.add(tuple(args))
        actual = check_exit_state(*args)
        assert actual == case["result"]
        counts["scalarSuccessCalls"] += 1
    for path in ("A", "B", "C", "D"):
        for psw in range(65536):
            scalar(path, psw, 0xA3, 15 if path == "A" else 0x8F)
    for path in ("B", "C", "D"):
        for ah in range(256):
            for data in range(256):
                scalar(path, 0xF123, ah, data)
    for ah in range(256):
        scalar("A", 0xF123, ah, 15)
    scalar_negative_inputs = set()
    for label, args, code, stage in scalar_negative_cases():
        scalar_negative_inputs.add(stable(args))
        seen = []
        for _ in range(2):
            try:
                check_exit_state(*args)
            except TransferError as error:
                reason(error, code, stage)
                seen.append((error.code, error.path, error.stage, str(error)))
                counts["scalarRefusalCalls"] += 1
            else:
                raise AssertionError("Scalar context mutation accepted: " + label)
        assert seen[0] == seen[1]

    before = stable(contract), stable(upstream)
    result = evaluate_exit_obligations(contract, upstream)
    counts["contractSuccessCalls"] += 1
    assert (stable(contract), stable(upstream)) == before
    counts["immutabilityChecks"] += 2
    assert result == {
        "passed": True, "classification": "StaticExternalContinuationObligations",
        "continuations": contract["continuations"], "paths": expected_path_rows(),
        "contextNoninterference": contract["contextNoninterference"], "proofLevels": PROOF_LEVELS,
        "counts": {"instructionSites": 18, "supportedForms": 15, "instructionLengthSum": 45,
                   "newExecutableSites": 0, "historicalPath13NativeWitnesses": 0},
        "executionBlocked": True, "runtimePermission": False,
        "targetBytes": 0, "codecCalls": 0, "CPUExecutions": 0, "actualROMExecutions": 0,
        "currentSourceStaticOnly": True,
    }
    for label, candidate, old, code, stage, domain in contract_mutations(contract, upstream):
        counts["contractMutationLabels"] += 1
        mutation_keys.add(stable([candidate, old]))
        mutation_domains[domain] = mutation_domains.get(domain, 0) + 1
        before = stable(candidate), stable(old)
        seen = []
        for _ in range(2):
            try:
                evaluate_exit_obligations(candidate, old)
            except TransferError as error:
                reason(error, code, stage)
                seen.append((error.code, error.path, error.stage, str(error)))
                counts["contractRefusalCalls"] += 1
            else:
                raise AssertionError("Contract mutation accepted: " + label)
            assert (stable(candidate), stable(old)) == before
            counts["immutabilityChecks"] += 2
        assert seen[0] == seen[1]

    def hypothesis(base, gap, form):
        candidate = {"syntheticBase": base, "gap": gap, "classification": "InventedOnlyImmutableM2beGeometry"}
        expected = expected_hypothesis(base, gap, form)
        hypothesis_keys.add(stable([candidate, form]))
        snapshot = stable(candidate)
        try:
            actual = inspect_terminal_hypothesis(candidate, form)
        except TransferError as error:
            assert "failure" in expected
            reason(error, *expected["failure"])
            counts["hypothesisRefusalCalls"] += 1
        else:
            assert "failure" not in expected
            assert actual == expected
            counts["hypothesisSuccessCalls"] += 1
            counts["hypothesisRowsCompared"] += 2
            counts["existingAssignmentsCompared"] += 18
        assert stable(candidate) == snapshot
        counts["immutabilityChecks"] += 1

    for base in (0, 0x1000, 0x2345, 0x556F, 0x8000, 0xF000):
        for gap in range(105):
            for form in ("SJ-address", "J-address"):
                hypothesis(base, gap, form)
    for base, gap in ((0xFFD3, 0), (0xFFD0, 0), (0xFFAA, 41), (0xFF6B, 104),
                      (0xFFD4, 0), (0x1000, 105), (0, 65536)):
        for form in ("SJ-address", "J-address"):
            hypothesis(base, gap, form)
    assert counts["fullOriginGeometryCalls"] == 262144
    assert counts["completeDirectTargetCalls"] == 131072
    assert counts["scalarSuccessCalls"] == 459008 and len(scalar_keys) == 459004
    assert counts["contractRefusalCalls"] == 2 * counts["contractMutationLabels"]
    print(json.dumps({
        "milestone": "M2bf", "passed": True, "failed": 0, "skipped": 0, "firstMismatch": None,
        "counts": counts, "uniqueGeometryInputs": len(geometry_keys),
        "uniquePositiveScalarInputs": len(scalar_keys),
        "scalarNegativeLabels": len(scalar_negative_cases()),
        "uniqueNegativeScalarInputs": len(scalar_negative_inputs),
        "uniqueContractMutationInputs": len(mutation_keys),
        "uniqueHypothesisInputs": len(hypothesis_keys),
        "mutationDomains": mutation_domains, "refusalReasons": reasons,
        "independentSJOriginIntervals": {name: relative_origin_interval(target) for name, target in TARGETS.items()},
        "geometryDomain": "InventedIntegerRepresentability_NotROMPlacement",
        "scalarDomain": "InventedTerminalConstraintAlgebra_NotCPUOrNativeObservation",
        "hypothesisDomain": "Immutable18Sites45Bytes_FutureOverheadOnly_NoInsertion",
        "actualROMExecutions": 0, "encoderCalls": 0, "decoderCalls": 0,
        "CPUExecutions": 0, "targetBytes": 0, "nativeExitIsolation": "NotEstablished",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
