"""M2bh independently prepared static-composition expectations and mutations.

No codec, CPU, ROM or stream generation is part of this suite. Actual analyzer
comparison starts only after an honest preimplementation absence observation.
Each negative call must fail on its prescribed real relation twice; this is
determinism verification, never retry-until-pass.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys

from static_composition_oracle import (
    ANCHORS, FLAGS, J_NB, J_BELOW, NODE_ROWS, TAKEN, canonical_assignments,
    classified_edges, collision_descriptors, enumerated_paths, expected_dd,
    expected_flag_writers, expected_geometry, expected_paths, expected_result,
    independent_summary, named_positive_scenarios,
)

HERE = Path(__file__).resolve().parent
DOMAINS = ((0,), (1,), (0, 1))
MAIN_BASES = (0, 0x1000, 0x2345, 0x4000, 0x8000, 0xF000)


def stable(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def fingerprint(value):
    return hashlib.sha256(stable(value).encode("utf-8")).hexdigest()


def request(base=0x1000, gap=0, initial=(0, 1), assignments=None):
    return {"syntheticBase": base, "gap": gap, "initialDD": list(initial),
            "nodeAssignments": assignments, "classification": "InventedOnlyStaticComposition"}


def model_mutations():
    """Closed independent input patches, sealed before analyzer authoring."""
    cases = []
    def add(label, code, stage, *patches):
        cases.append({"label": label, "expectedCode": code, "expectedStage": stage,
                      "patches": list(patches)})
    def set_at(path, value):
        return {"op": "set", "path": path, "value": value}
    def remove(path):
        return {"op": "delete", "path": path}
    def paired(relative, value):
        return (set_at(["ir", "instructions"] + relative, value),
                set_at(["contract", "originalIRInstructions"] + relative, value))

    for key in ("ir", "contract", "request"):
        add("null-" + key, "InputShape", "Input", set_at([key], None))
    for key, field in (("ir", "instructions"), ("contract", "abstractTransfers"),
                       ("contract", "originalSiteObligations")):
        add("missing-" + field, "InputShape", "Input", remove([key, field]))
    add("old-site-missing", "OriginalSiteInventory", "Inventory",
        remove(["contract", "originalSiteObligations", 17]))
    add("old-site-duplicate", "OriginalSiteInventory", "Inventory",
        set_at(["contract", "originalSiteObligations", 1, "pc"], 0x556F))
    add("old-site-identity-not-PC16", "OriginalSiteInventory", "Inventory",
        set_at(["contract", "originalSiteObligations", 0, "pc"], 65536))
    add("original-IR-site-missing", "OriginalSiteInventory", "Inventory",
        remove(["ir", "instructions", 17]),
        remove(["contract", "originalIRInstructions", 17]))
    for index in (0, 1, 5, 17):
        add("old-length-" + str(index), "OriginalFormLengthMismatch", "Inventory",
            set_at(["contract", "originalSiteObligations", index, "length"], 6))
    add("old-form-not-supported", "OriginalFormLengthMismatch", "Inventory",
        set_at(["contract", "originalSiteObligations", 0, "formId"], "j-address"))
    add("old-IR-length-changed", "OriginalFormLengthMismatch", "Inventory",
        *paired([0, "form", "length"], 3))
    add("transfer-missing", "TransferInventory", "Transfer",
        remove(["contract", "abstractTransfers", 1]))
    add("transfer-duplicate-identity", "TransferInventory", "Transfer",
        set_at(["contract", "abstractTransfers", 1, "nodeId"], J_NB))
    transfer_bad = {
        "nodeKind": "OriginalLogicalInstruction", "originalLogicalSiteId": 0x5596,
        "formId": "sj-address", "length": 2, "predecessor": 0x5592,
        "target": 0x55C5, "dd": {"selection": "RequiresDD0", "transfer": "SetsDD0WhenExecuted"},
        "flagsRead": ["CF"], "flagsWritten": ["ZF"], "functionalDATAReads": [0x018F],
        "DATAWrites": [0x018F], "stackWrites": ["SSP"], "PCReplacement": "Fallthrough",
        "nativeHistoricalObservation": True,
    }
    for key, value in transfer_bad.items():
        add("transfer-spec-" + key, "TransferSpecificationMismatch", "Transfer",
            set_at(["contract", "abstractTransfers", 0, key], value))
    add("transfer-below-wrong-target", "TransferSpecificationMismatch", "Transfer",
        set_at(["contract", "abstractTransfers", 1, "target"], 0x5596))
    add("CFG-edge-missing", "CFGRelationMismatch", "CFG",
        remove(["contract", "composedCFG", 22]))
    add("CFG-J-NB-fallthrough", "CFGRelationMismatch", "CFG",
        set_at(["contract", "composedCFG", 21, "kind"], "Fallthrough"))
    add("CFG-J-NB-internal-target", "CFGRelationMismatch", "CFG",
        set_at(["contract", "composedCFG", 21, "to"], 0x55BF))
    add("CFG-original-last-bypasses-J", "CFGRelationMismatch", "CFG",
        set_at(["contract", "composedCFG", 17, "to"], 0x5596))
    add("CFG-cycle-original", "CFGRelationMismatch", "CFG",
        set_at(["contract", "composedCFG", 0, "to"], 0x556F))
    add("CFG-invented-predicate", "CFGRelationMismatch", "CFG",
        set_at(["contract", "composedCFG", 6, "predicate", "value"], 0))
    add("IR-branch-cross-path", "CFGRelationMismatch", "CFG",
        *paired([6, "successors", 0], 0x5592))
    add("IR-branch-CF-to-ZF", "CFGRelationMismatch", "CFG",
        *paired([6, "branchPredicate", "flag"], "ZF"))
    add("typed-JLT-target", "CFGRelationMismatch", "CFG",
        set_at(["contract", "originalSiteObligations", 6, "successors", 0], 0x5592))
    add("DD-first-LB-sets-one", "DDRequirementViolation", "DD",
        *paired([0, "effects", 2, "value"], True))
    add("DD-first-LB-reset-removed", "DDRequirementViolation", "DD",
        remove(["ir", "instructions", 0, "effects", 2]),
        remove(["contract", "originalIRInstructions", 0, "effects", 2]))
    add("DD-second-LB-sets-one", "DDRequirementViolation", "DD",
        *paired([3, "effects", 2, "value"], True))
    add("DD-required-selection-promoted", "DDRequirementViolation", "DD",
        set_at(["contract", "originalSiteObligations", 1, "dd", "selection"], "AcceptsBothIncomingDD"))
    add("CF-SLL-writer-removed", "FlagDependencyMismatch", "Flags",
        set_at(["contract", "originalSiteObligations", 1, "flags", "written"], []))
    add("CF-ROL-reader-removed", "FlagDependencyMismatch", "Flags",
        set_at(["contract", "originalSiteObligations", 2, "flags", "functionalRead"], []))
    add("HC-preservation-removed", "FlagDependencyMismatch", "Flags",
        set_at(["contract", "originalSiteObligations", 1, "flags", "preserved"], ["ZF", "DD", "OtherPSW"]))
    add("ZF-JLT-functional-writer-invented", "FlagDependencyMismatch", "Flags",
        set_at(["contract", "originalSiteObligations", 6, "flags", "written"], ["ZF"]))
    add("word0196-width-changed", "MemoryEffectMismatch", "Memory",
        set_at(["contract", "originalSiteObligations", 5, "memory", "reads", 0, "widthBits"], 8))
    add("word0196-byteorder-changed", "MemoryEffectMismatch", "Memory",
        set_at(["contract", "originalSiteObligations", 5, "memory", "reads", 0, "byteOrder"], "BigEndian"))
    add("old-read-address-changed", "MemoryEffectMismatch", "Memory",
        set_at(["contract", "originalSiteObligations", 0, "memory", "reads", 0, "address"], 0x018F))
    add("raw-IR-fresh-read-address-changed", "MemoryEffectMismatch", "Memory",
        *paired([0, "effects", 0, "source", "address"], 0x018F))
    add("raw-IR-same-value-write-suppressed", "MemoryEffectMismatch", "Memory",
        *paired([2, "effects", 0, "sameValueWrite"], "Suppress"))
    add("raw-IR-ordered-write-erased", "MemoryEffectMismatch", "Memory",
        *paired([7, "effects", 0, "orderedWrite"], False))
    add("path-write-same-value-suppressed", "MemoryEffectMismatch", "Memory",
        set_at(["contract", "paths", 0, "originalPath", "orderedWrites", 0, "sameValueWrite"], "Suppress"))
    add("path-first-gate-read-permission-added", "MemoryEffectMismatch", "Memory",
        set_at(["contract", "paths", 1, "originalPath", "mustNotRead"], []))
    add("context-LRB-rebased", "ContextObligationMismatch", "Context",
        set_at(["contract", "context", "requiredLRB"], 0))
    add("context-word-owner-rebased", "ContextObligationMismatch", "Context",
        set_at(["contract", "context", "word0196", "codeOwnedImmediate"], 0))
    add("context-stack-global-safety-promoted", "ContextObligationMismatch", "Context",
        set_at(["contract", "context", "nativeStackSafety"], "Verified"))
    add("continuation-owner-promoted", "ContinuationMismatch", "Continuation",
        set_at(["contract", "continuations", 0, "nativeOwnerCreated"], True))
    add("continuation-original-PC-changed", "ContinuationMismatch", "Continuation",
        set_at(["contract", "continuations", 0, "originalTargetPC"], 0x55C5))

    for field, values in (
        ("syntheticBase", (-1, 65536, True, False, 4096.0, "4096", None)),
        ("gap", (-1, True, False, 0.0, "0", None)),
        ("initialDD", ([], [1, 0], [0, 0], [0, 1, 1], [True], [False], [2], 0, None)),
        ("classification", ("FirmwareReady", "InventedOnlySymbolicLayout", None)),
    ):
        for value in values:
            add("request-" + field + "-" + repr(value),
                "InputShape" if type(value) is float else "RequestDomain",
                "Input" if type(value) is float else "Request",
                set_at(["request", field], value))
    add("request-unknown-runtime-field", "RequestDomain", "Request",
        set_at(["request", "runtimePermission"], True))
    for field in ("syntheticBase", "gap", "initialDD", "classification", "nodeAssignments"):
        add("request-missing-" + field, "RequestDomain", "Request", remove(["request", field]))
    for field, value in (("expectedLength", 7), ("startConstant", 43),
                         ("endConstant", 49), ("gapCoefficient", 0)):
        add("component-plan-" + field, "ComponentPlanMismatch", "Plan",
            set_at(["contract", "componentPlan", 3, field], value))
    add("component-node-order-changed", "ComponentPlanMismatch", "Plan",
        set_at(["contract", "componentPlan", 0, "nodeIds"], [0x5571, 0x556F]))
    for field, value in (("composedNodeCount", 10), ("abstractTransferCount", 0),
                         ("transferNodeId", J_NB), ("externalTarget", 0x5596)):
        add("path-clause-" + field, "ComponentPlanMismatch", "Plan",
            set_at(["contract", "paths", 0, field], value))
    add("metadata-runtime-promotion", "MetadataMismatch", "Metadata",
        set_at(["contract", "permissions", "targetCPUExecution"], True))
    add("metadata-firmware-promotion", "MetadataMismatch", "Metadata",
        set_at(["contract", "permissions", "FirmwareReady"], True))
    add("metadata-path13-native-promotion", "MetadataMismatch", "Metadata",
        set_at(["contract", "declaredStaticFacts", "historicalPath13NativeWitnesses"], 1))
    add("metadata-semantic-count-promotion", "MetadataMismatch", "Metadata",
        set_at(["contract", "declaredStaticFacts", "historicalRunner", "semanticAccountingIdentities"], 39))

    third_transfer = {
        "nodeId": "DirectJ_ThirdForbidden", "nodeKind": "AbstractTransferSlot",
        "originalLogicalSiteId": None, "formId": "j-address", "length": 3,
        "predecessor": 0x55C3, "target": 0x5596,
        "dd": {"selection": "AcceptsBothIncomingDD", "transfer": "PreservesDD"},
        "flagsRead": [], "flagsWritten": [], "functionalDATAReads": [], "DATAWrites": [],
        "stackWrites": [], "PCReplacement": "ExternalProgramTarget", "nativeHistoricalObservation": False,
    }
    add("third-J-transfer-injected", "TransferInventory", "Transfer",
        {"op": "append", "path": ["contract", "abstractTransfers"], "value": third_transfer})
    for index in (0, 1):
        for form in ("cal-address", "rt", "nop"):
            add("J-slot-" + str(index) + "-replaced-by-" + form,
                "TransferSpecificationMismatch", "Transfer",
                set_at(["contract", "abstractTransfers", index, "formId"], form))
    for field, value in (
        ("PCReplacement", "Return"), ("flagsWritten", ["CF"]),
        ("dd", {"selection": "AcceptsBothIncomingDD", "transfer": "SetsDD1WhenExecuted"}),
        ("LRB", 0), ("SCB", 0), ("prologue", ["SavePSW"])):
        add("J-adapter-or-context-clobber-" + field, "TransferSpecificationMismatch", "Transfer",
            set_at(["contract", "abstractTransfers", 0, field], value))
    add("actual-raw-CopyByte-write-duplicated", "MemoryEffectMismatch", "Memory",
        {"op": "duplicate", "path": ["ir", "instructions", 7, "effects", 0]},
        {"op": "duplicate", "path": ["contract", "originalIRInstructions", 7, "effects", 0]})
    add("actual-raw-558B-RMW-removed", "MemoryEffectMismatch", "Memory",
        remove(["ir", "instructions", 11, "effects", 0]),
        remove(["contract", "originalIRInstructions", 11, "effects", 0]))
    add("ordered-path-writes-reversed", "MemoryEffectMismatch", "Memory",
        {"op": "reverse", "path": ["contract", "paths", 0, "originalPath", "orderedWrites"]})
    add("actual-pathC-historical-native-promotion", "MetadataMismatch", "Metadata",
        set_at(["contract", "paths", 2, "originalPath", "historical"], "HistoricalNativeValidated"))
    add("geometry-component-length-total-wrong", "ComponentPlanMismatch", "Plan",
        set_at(["contract", "geometry", "lengths", 2], 2))
    add("geometry-Below-block-start-wrong", "ComponentPlanMismatch", "Plan",
        set_at(["contract", "geometry", "denseOffsets", 3, 0], 41))
    for key, value in (
        ("CompositeMachineCode", "Generated"), ("physicalROMPlacement", "Established"),
        ("nativeExitIsolation", "Established"), ("actualDownstreamRejoin", "Established"),
        ("originalExcluded41ByteRegion", "VerifiedFreeROM")):
        add("metadata-authority-promotion-" + key, "MetadataMismatch", "Metadata",
            set_at(["contract", "declaredStaticFacts", key], value))
    return cases


def apply_patch_to_inputs(inputs, patch):
    cursor = inputs
    for key in patch["path"][:-1]:
        cursor = cursor[key]
    last = patch["path"][-1]
    if patch["op"] == "delete":
        del cursor[last]
    elif patch["op"] == "append":
        cursor[last].append(copy.deepcopy(patch["value"]))
    elif patch["op"] == "duplicate":
        cursor.insert(last + 1, copy.deepcopy(cursor[last]))
    elif patch["op"] == "reverse":
        cursor[last].reverse()
    else:
        cursor[last] = copy.deepcopy(patch["value"])


def materialize(ir, model, case):
    inputs = {"ir": copy.deepcopy(ir), "contract": copy.deepcopy(model), "request": request()}
    for patch in case["patches"]:
        apply_patch_to_inputs(inputs, patch)
    return inputs


def geometry_mutations():
    cases = []
    def add(label, code, stage, candidate):
        cases.append({"label": label, "expectedCode": code, "expectedStage": stage, "request": candidate})
    add("first-too-far-gap102", "Rel8OutOfRange", "Branch", request(gap=102))
    add("huge-gap-real-span-refusal", "SpanOutsideProfile", "Span", request(gap=2 ** 80))
    add("dense-base-one-above-FFCD", "SpanOutsideProfile", "Span", request(base=0xFFCE))
    add("gap101-base-one-above-FF68", "SpanOutsideProfile", "Span", request(base=0xFF69, gap=101))
    add("span-before-out-of-reach", "SpanOutsideProfile", "Span", request(base=0xFFCD, gap=102))
    assignments = canonical_assignments(0x1000, 0)
    add("assignments-missing", "AssignmentInventory", "Assignment", request(assignments=assignments[:-1]))
    extra = copy.deepcopy(assignments) + [{"nodeId": "InventedThirdJ", "assignedPC": 0x2000}]
    add("assignments-extra", "AssignmentInventory", "Assignment", request(assignments=extra))
    duplicate = copy.deepcopy(assignments)
    duplicate[-1]["nodeId"] = J_NB
    add("assignments-duplicate-ID", "AssignmentInventory", "Assignment", request(assignments=duplicate))
    for bad in (65536, -1, True, 4096.0, None):
        mutated = copy.deepcopy(assignments)
        mutated[0]["assignedPC"] = bad
        add("assignment-PC-" + repr(bad),
            "InputShape" if type(bad) is float else "AssignmentInventory",
            "Input" if type(bad) is float else "Assignment", request(assignments=mutated))
    mutated = copy.deepcopy(assignments)
    mutated[0]["extraField"] = True
    add("assignment-extra-field", "AssignmentInventory", "Assignment", request(assignments=mutated))
    mutated = copy.deepcopy(assignments)
    mutated[1]["assignedPC"] = mutated[0]["assignedPC"]
    add("actual-old-span-overlap", "InstructionOverlap", "Span", request(assignments=mutated))
    mutated = copy.deepcopy(assignments)
    mutated[15]["assignedPC"] += 1
    add("actual-J-NB-footprint-overlap-Below", "InstructionOverlap", "Span", request(assignments=mutated))
    mutated = copy.deepcopy(assignments)
    mutated[19]["assignedPC"] += 1
    add("actual-new-J-Below-predecessor-gap", "FallthroughMismatch", "Fallthrough", request(assignments=mutated))
    mutated = copy.deepcopy(assignments)
    for row in mutated:
        if row["nodeId"] in (0x557F, 0x5582, 0x5585, 0x5588, 0x558B, 0x558E, 0x5592, 0x5594, J_NB,
                             0x55BF, 0x55C1, 0x55C3, J_BELOW):
            row["assignedPC"] += 1
    add("actual-JLT-false-fallthrough-gap", "FallthroughMismatch", "Fallthrough", request(assignments=mutated))
    for delta, code in ((-129, "Rel8OutOfRange"), (-128, "BranchTargetMismatch"),
                        (127, "BranchTargetMismatch"), (128, "Rel8OutOfRange")):
        mutated = copy.deepcopy(assignments)
        shift = delta - 26
        for row in mutated:
            if row["nodeId"] in (0x55BF, 0x55C1, 0x55C3, J_BELOW):
                row["assignedPC"] += shift
        add("actual-rel8-" + str(delta) + "-undeclared-relayout", code, "Branch", request(assignments=mutated))

    for node, origin, label in (
        (J_NB, 0x1000 + 9, "J-inside-Common"),
        (J_NB, 0x1000 + 36, "J-before-original5594"),
        (J_BELOW, 0x1000 + 45, "J-before-original55C3")):
        mutated = copy.deepcopy(assignments)
        for row in mutated:
            if row["nodeId"] == node:
                row["assignedPC"] = origin
        add(label, "InstructionOverlap", "Span", request(assignments=mutated))
    mutated = copy.deepcopy(assignments)
    for row in mutated:
        if row["nodeId"] in (0x5592, 0x5594, J_NB, 0x55BF, 0x55C1, 0x55C3, J_BELOW):
            row["assignedPC"] += 1
    add("actual-JBS-distances-shifted-breaking-predecessor-fallthrough",
        "FallthroughMismatch", "Fallthrough", request(assignments=mutated))
    return cases


def load_inputs(directory):
    return (json.loads((directory / "word0196_ir.json").read_text(encoding="utf-8")),
            json.loads((directory / "static_composition_contract.json").read_text(encoding="utf-8")))


def preparation(ir, model):
    summary = independent_summary()
    assert summary["compositeNodes"] == 20 and summary["edges"] == 23
    assert summary["denseLength"] == 51 and summary["originalLengthSum"] == 45
    assert summary["composedPathLengths"] == [11, 13, 14, 16]
    assert summary["writeCounts"] == [3, 3, 3, 5]
    assert summary["maxDenseBase"] == 0xFFCD and summary["maxGap101Base"] == 0xFF68
    for initial in DOMAINS:
        dd = {row["node"]: row for row in expected_dd(initial)}
        assert dd[0x556F]["incomingMay"] == list(initial)
        assert all(row["outgoingMay"] == [0] for row in dd.values())
        assert all(dd[node]["incomingMay"] == [0] for node, *_ in NODE_ROWS if node != 0x556F)
    flags = {row["node"]: row for row in expected_flag_writers()}
    assert flags[0x5572]["reachingWritersIn"]["CF"] == [0x5571]
    assert flags[0x557D]["reachingWritersIn"]["CF"] == [0x5578]
    for node in (J_NB, J_BELOW):
        assert flags[node]["reachingWritersIn"] == flags[node]["reachingWritersOut"]
        assert flags[node]["liveIn"] == list(FLAGS) == flags[node]["liveOut"]
    labels, contexts, expected_hashes = 0, set(), []
    for base in MAIN_BASES:
        for gap in range(102):
            for initial in DOMAINS:
                result = expected_result(base, gap, initial)
                expected_hashes.append(fingerprint(result))
                contexts.add((base, gap, initial))
                labels += 1
    main_labels = labels
    for _, base, gap in named_positive_scenarios():
        for initial in DOMAINS:
            expected_hashes.append(fingerprint(expected_result(base, gap, initial)))
            contexts.add((base, gap, initial))
            labels += 1
    collisions = collision_descriptors()
    collision_keys = {(row["base"], row["gap"], tuple(row["initial"])) for row in collisions}
    assert all(expected_geometry(row["base"], row["gap"])["nodeCollisions"] for row in collisions)
    cases = model_mutations()
    base_inputs = {"ir": ir, "contract": model, "request": request()}
    actual_mutant_fingerprints = []
    for case in cases:
        mutated = materialize(ir, model, case)
        assert fingerprint(mutated) != fingerprint(base_inputs), case["label"]
        actual_mutant_fingerprints.append(fingerprint(mutated))
    geometry_cases = geometry_mutations()
    geometry_keys = {stable(case["request"]) for case in geometry_cases}
    assert labels == 1860 and main_labels == 1836 and len(contexts) == 1851
    assert len(collisions) == 612 and len(collision_keys) == 600
    return {
        "independentSummary": summary,
        "mainPositiveLabels": main_labels, "namedPositiveLabels": labels - main_labels,
        "namedLabelsOverlapMainGeometry": 9, "uniquePositiveGeometryContexts": len(contexts),
        "explicitCanonicalAssignmentLabels": 6,
        "modelMutationLabels": len(cases), "uniqueModelMutantInputs": len(set(actual_mutant_fingerprints)),
        "geometryNegativeLabels": len(geometry_cases), "uniqueGeometryNegativeRequests": len(geometry_keys),
        "anchorCollisionLabels": len(collisions), "uniqueAnchorCollisionContexts": len(collision_keys),
        "expectedPositiveProjectionCorpusSHA256": fingerprint(expected_hashes),
        "expectedModelMutationDescriptorSHA256": fingerprint(cases),
        "actualModelMutationInputCorpusSHA256": fingerprint(actual_mutant_fingerprints),
        "expectedGeometryMutationDescriptorSHA256": fingerprint(geometry_cases),
        "expectedCollisionDescriptorSHA256": fingerprint(collisions),
        "analyzerCalls": 0, "encoderCalls": 0, "decoderCalls": 0,
        "CPUExecutions": 0, "actualROMExecutions": 0, "compositeBytes": 0, "fakeRED": False,
    }


def main():
    directory = HERE
    if "--data-directory" in sys.argv:
        directory = Path(sys.argv[sys.argv.index("--data-directory") + 1]).resolve()
    ir, model = load_inputs(directory)
    prepared = preparation(ir, model)
    analyzer_path = directory / "static_composition_analysis.py"
    if "--prepare-only" in sys.argv or "--observe-absent" in sys.argv:
        if "--observe-absent" in sys.argv:
            assert not analyzer_path.exists(), "Absence observation requires actually absent analyzer"
            prepared["actualAnalyzerAbsent"] = True
            prepared["fakeRED"] = False
        prepared["phase"] = "PreimplementationIndependentPreparation"
        prepared["passed"] = True
        print(json.dumps(prepared, sort_keys=True))
        return

    from static_composition_analysis import CompositionError, evaluate_composition

    baseline_hashes = fingerprint(ir), fingerprint(model)
    counts = {"positiveCalls": 0, "negativeCalls": 0, "repeatedNegativeDeterminismCalls": 0,
              "modelMutationLabels": 0, "geometryNegativeLabels": 0, "anchorCollisionLabels": 0}
    observed_codes, positive_geometry, positive_inputs, negative_inputs = set(), set(), set(), set()

    def positive(label, candidate):
        expected = expected_result(candidate["syntheticBase"], candidate["gap"], tuple(candidate["initialDD"]))
        actual = evaluate_composition(ir, model, candidate)
        counts["positiveCalls"] += 1
        assert type(actual) is dict and actual == expected, (
            label, "Independent projection mismatch", fingerprint(actual), fingerprint(expected))
        assert set(actual) == set(expected)
        positive_geometry.add((candidate["syntheticBase"], candidate["gap"], tuple(candidate["initialDD"])))
        positive_inputs.add(stable(candidate))
        return actual

    for base in MAIN_BASES:
        for gap in range(102):
            for initial in DOMAINS:
                positive("main", request(base, gap, initial))
    for label, base, gap in named_positive_scenarios():
        for initial in DOMAINS:
            positive(label, request(base, gap, initial))
    for initial in DOMAINS:
        assignments = canonical_assignments(0x1000, 0)
        positive("explicit-canonical20", request(initial=initial, assignments=assignments))
        positive("explicit-reverse-input-inventory", request(initial=initial, assignments=list(reversed(assignments))))

    def negative(label, case, inputs):
        before = fingerprint(inputs)
        negative_inputs.add(before)
        seen = []
        for repetition in range(2):
            try:
                evaluate_composition(inputs["ir"], inputs["contract"], inputs["request"])
            except CompositionError as error:
                assert type(error.code) is str and error.code == case["expectedCode"], (
                    label, error.code, case["expectedCode"])
                assert type(error.stage) is str and error.stage == case["expectedStage"], (
                    label, error.stage, case["expectedStage"])
                assert type(error.path) is str and error.path
                assert not any(hasattr(error, field) for field in ("result", "partial", "nodeSpans", "record"))
                seen.append((error.code, error.path, error.stage, error.args))
                observed_codes.add(error.code)
            else:
                raise AssertionError((label, "Expected refusal did not occur"))
            counts["negativeCalls"] += 1
            if repetition:
                counts["repeatedNegativeDeterminismCalls"] += 1
        assert seen[0] == seen[1], (label, "Non-deterministic refusal")
        assert fingerprint(inputs) == before, (label, "Analyzer mutated refused inputs")

    for case in model_mutations():
        negative(case["label"], case, materialize(ir, model, case))
        counts["modelMutationLabels"] += 1
    for case in geometry_mutations():
        inputs = {"ir": ir, "contract": model, "request": copy.deepcopy(case["request"])}
        negative(case["label"], case, inputs)
        counts["geometryNegativeLabels"] += 1
    for case in collision_descriptors():
        inputs = {"ir": ir, "contract": model,
                  "request": request(case["base"], case["gap"], tuple(case["initial"]))}
        negative(case["label"], case, inputs)
        counts["anchorCollisionLabels"] += 1

    assert (fingerprint(ir), fingerprint(model)) == baseline_hashes
    assert counts["positiveCalls"] == 1866
    assert len(positive_geometry) == 1851 and len(positive_inputs) == 1857
    assert counts["negativeCalls"] == 2 * (
        len(model_mutations()) + len(geometry_mutations()) + len(collision_descriptors()))
    print(json.dumps({
        "milestone": "M2bh", "passed": True, "failed": 0, "skipped": 0,
        "counts": counts, "uniquePositiveGeometryContexts": len(positive_geometry),
        "uniquePositiveRequestInputs": len(positive_inputs), "uniqueNegativeInputs": len(negative_inputs),
        "observedRefusalCodes": sorted(observed_codes),
        "defensiveUnreachedRefusal": "BranchNextOutsideProfile_NoArtificialCoverageClaim",
        "independentPreparation": prepared,
        "encoderCalls": 0, "decoderCalls": 0, "CPUExecutions": 0, "actualROMExecutions": 0,
        "compositeBytes": 0, "instructionStreams": 0, "targetObjects": 0, "targetHEX": 0, "FirmwareBIN": 0,
        "historicalPath13NativeWitnesses": 0,
        "nativeExitIsolation": "NotEstablished", "actualDownstreamRejoin": "NotEstablished",
        "physicalPlacement": "NotAuthorized", "firmwareIntegration": "NotEstablished",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
