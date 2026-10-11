"""Independent M2be geometry and refusal checks; no code emission or CPU calls.

Expected addresses and distances come from the separately prepared mathematical
oracle, not analyzer output. Actual full layout evaluations, unique request
scenarios, boundary controls and repeated refusal calls are reported separately.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

from layout_feasibility_oracle import (
    FALLTHROUGHS, PATHS, SITES, WRITES,
    expected_layout, named_scenarios, relative_condition, reviewed_arithmetic,
    span_condition,
)

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = Path(__file__).resolve().parent
PROOF_LEVELS = {
    "instructionGeometry": "InstructionSpanGeometryVerified",
    "internalCFG": "SyntheticInternalBranchReachVerified",
    "context": "StaticContextPreservationObligationsVerified",
    "nativeExitIsolation": "NativeExitIsolationNotEstablished",
    "physicalROMPlacement": "PhysicalROMPlacementNotEstablished",
    "targetProgramEquivalence": "TargetProgramEquivalenceNotEstablished",
    "firmwareIntegration": "FirmwareIntegrationNotEstablished",
}
CONTEXT = {
    "initialDD": [0, 1], "DD0After556F": True,
    "carryDependencies": [{"producer": 0x5571, "consumer": 0x5572},
                          {"producer": 0x5578, "consumer": 0x557D}],
    "HC": "Preserved", "OtherPSW": "Preserved", "AH": "Preserved",
    "LRB": 33, "currentPage": 256, "localBank": [264, 271],
    "SCB": "IncomingPSWLowThreeBits_NotFixed",
    "SSP": "Retained_NoFrameEstablished", "SF": "PrimaryConflictUnresolved",
    "dataAddresses": [0x117, 0x124, 0x128, 0x12A, 0x18E, 0x18F, 0x196, 0x197],
    "RAMAddressesRelocated": False, "r1Alias": "HighByteEr0_R0Retained_NotWholeEr0",
    "word0196": "EvenLE16_CodeOwned00C0_NotRAM00C0",
    "potentialWordAliases": [[0x116, 0x117], [0x124, 0x125], [0x128, 0x129],
                            [0x12A, 0x12B], [0x18E, 0x18F], [0x196, 0x197]],
    "stackAliases": "UnknownSSPMayAliasRegistersRamOrSFR",
    "runtimeContextVerified": False, "nativeOwnerCreated": False,
}
SPAN_CODES = {"Origin": "OriginInvalid", "Length": "LengthInvalid", "Span": "SpanOutsideProfile"}
BRANCH_CODES = SPAN_CODES | {
    "NextPC": "BranchNextOutsideProfile", "Target": "TargetInvalid", "Rel8": "Rel8OutOfRange",
}


def request(base=0x1000, gaps=(0, 0), order=("Common", "NotBelow", "Below"), assignments=None):
    return {"syntheticBase": base, "blockOrder": list(order), "gaps": list(gaps),
            "siteAssignments": assignments, "classification": "InventedOnlySymbolicLayout"}


def _stable(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _explicit_assignments(base=0x1000, gap=0):
    return [{"logicalSiteId": pc, "syntheticAssignedPC": start}
            for pc, start, _ in expected_layout(base, (0, gap))["spans"]]


def _change_assignment(rows, site, delta):
    row = next(row for row in rows if row["logicalSiteId"] == site)
    row["syntheticAssignedPC"] += delta


def _negative_definitions(upstream):
    """Mutations prepared from input semantics, NEVER learned from failed output."""
    entries = []
    def add(label, change, code, stage, domain="StaticLayoutOrContextMutation"):
        model, candidate = copy.deepcopy(upstream), request()
        change(model, candidate)
        entries.append((label, model, candidate, code, stage, domain))

    add("missing-instruction-site", lambda m, r: m["sites"].pop(), "InventoryMismatch", "Inventory")
    add("duplicate-instruction-site",
        lambda m, r: m["sites"].__setitem__(1, copy.deepcopy(m["sites"][0])),
        "InventoryMismatch", "Inventory")
    add("wrong-logical-site-identity", lambda m, r: m["sites"][0].__setitem__("pc", 0x556E),
        "SiteIdentityMismatch", "Inventory")
    add("wrong-length", lambda m, r: m["sites"][0].__setitem__("length", 3),
        "LengthMismatch", "Inventory")
    add("bool-is-not-length", lambda m, r: m["sites"][1].__setitem__("length", True),
        "LengthMismatch", "Inventory")
    add("wrong-form", lambda m, r: m["sites"][0].__setitem__("formId", "jlt-rel8"),
        "FormMismatch", "Inventory")
    add("altered-DD-requirement",
        lambda m, r: m["sites"][1]["dd"].__setitem__("selection", "AcceptsBothIncomingDD"),
        "ContextMismatch", "Context")
    add("altered-DD-transfer",
        lambda m, r: m["sites"][0]["dd"].__setitem__("transfer", "PreservesDD"),
        "ContextMismatch", "Context")
    add("altered-CFG-edge", lambda m, r: m["sites"][0].__setitem__("successors", [0x5572]),
        "CFGChanged", "Inventory")
    add("wrong-conditional-target",
        lambda m, r: m["sites"][6]["branch"].__setitem__("trueTarget", 0x557F),
        "CFGChanged", "Inventory")
    add("wrong-conditional-predicate",
        lambda m, r: m["sites"][6]["branch"]["predicate"].__setitem__("value", 0),
        "CFGChanged", "Inventory")
    add("unknown-instruction-inserted",
        lambda m, r: m["sites"].append({"pc": 0x5596, "formId": "implicit-jump", "length": 1}),
        "InventoryMismatch", "Inventory")
    add("implicit-RT", lambda m, r: m["nativeBoundary"].__setitem__("ordinaryReturnAllowed", True),
        "ContextMismatch", "Context")
    add("invented-STOP-opcode", lambda m, r: m["nativeBoundary"].__setitem__("stopBoundariesAreRT", True),
        "ContextMismatch", "Context")
    add("invented-trampoline", lambda m, r: m["nativeBoundary"].__setitem__("adapter", "NativeTrampoline"),
        "ContextMismatch", "Context")
    add("invented-C-ABI", lambda m, r: m["nativeBoundary"].__setitem__("nativeCFunctionEntry", "Established"),
        "ContextMismatch", "Context")
    add("invented-safe-stack-frame", lambda m, r: m["nativeBoundary"].__setitem__("stackSafety", "Established"),
        "ContextMismatch", "Context")
    add("LRB-rebasing", lambda m, r: m["context"].__setitem__("requiredLRB", 0x22),
        "ContextMismatch", "Context")
    add("changed-current-page", lambda m, r: m["context"].__setitem__("currentPage", 0x200),
        "ContextMismatch", "Context")
    add("changed-SCB-assumption", lambda m, r: m["context"].__setitem__("fixedSCBAssumption", 2),
        "ContextMismatch", "Context")
    add("changed-page-offset",
        lambda m, r: m["sites"][0]["typedOperands"][1].__setitem__("value", 0x8F),
        "ContextMismatch", "Context")
    add("changed-word-immediate",
        lambda m, r: m["sites"][5]["typedOperands"][1].__setitem__("value", 0xC1),
        "ContextMismatch", "Context")
    add("changed-LE-word-policy",
        lambda m, r: m["addressObligations"][-1].__setitem__("byteOrder", "BigEndian"),
        "ContextMismatch", "Context")
    add("reordered-writes",
        lambda m, r: m["pathObligations"][3]["orderedWrites"].reverse(),
        "ContextMismatch", "Context")
    add("unordered-writes",
        lambda m, r: m["pathObligations"][3]["orderedWrites"][0].__setitem__("ordered", False),
        "ContextMismatch", "Context")
    add("dropped-same-value-write",
        lambda m, r: m["sites"][2]["memory"]["writes"][0].__setitem__("sameValueWrite", "DropIfUnchanged"),
        "ContextMismatch", "Context")
    add("short-circuit-removed", lambda m, r: m["sites"][9].__setitem__("successors", [0x5588]),
        "CFGChanged", "Inventory")
    add("DATA0124-read-on-first-gate-true",
        lambda m, r: m["pathObligations"][1]["orderedReads"].append(
            {"pc": 0x5588, "address": 0x0124, "widthBits": 8, "mode": "CurrentPage", "byteOrder": "Byte"}),
        "ContextMismatch", "Context")
    add("historical-13-step-witness-invented",
        lambda m, r: m["pathObligations"][2].__setitem__("historical", "HistoricalNativeValidated"),
        "ContextMismatch", "Context")
    add("gap-as-verified-free-ROM",
        lambda m, r: m["nativeBoundary"].__setitem__("codePlacement", "VerifiedFreeROM"),
        "ContextMismatch", "Context")
    add("hidden-executable-padding", lambda m, r: r.__setitem__("executablePadding", "NOP"),
        "RequestShape", "Input", "ClosedInputPolicy")
    add("synthetic-address-as-actual-placement",
        lambda m, r: r.__setitem__("classification", "ActualROMPlacementVerified"),
        "Classification", "Policy", "ClosedInputPolicy")
    add("firmware-readiness-promoted",
        lambda m, r: r.__setitem__("classification", "ExecutableLayoutVerified"),
        "Classification", "Policy", "ClosedInputPolicy")
    add("bad-input-root", lambda m, r: r.__setitem__("unreviewedField", None),
        "RequestShape", "Input", "ClosedInputPolicy")
    add("negative-gap", lambda m, r: r.__setitem__("gaps", [0, -1]), "GapInvalid", "Input")
    add("huge-gap-real-span-refusal", lambda m, r: r.__setitem__("gaps", [0, 65536]),
        "OriginInvalid", "Span", "ActualSpanGeometry")
    add("bool-gap", lambda m, r: r.__setitem__("gaps", [0, True]), "GapInvalid", "Input")
    add("duplicate-block-order", lambda m, r: r.__setitem__("blockOrder", ["Common", "Below", "Below"]),
        "BlockOrderInvalid", "Input")
    add("entry-block-not-first", lambda m, r: r.__setitem__("blockOrder", ["Below", "Common", "NotBelow"]),
        "EntryBlockOrder", "Policy")
    add("below-breaks-JLT-false", lambda m, r: r.__setitem__("blockOrder", ["Common", "Below", "NotBelow"]),
        "FallthroughMismatch", "Fallthrough", "ActualFallthroughGeometry")
    add("gap-breaks-JLT-false", lambda m, r: r.__setitem__("gaps", [1, 0]),
        "FallthroughMismatch", "Fallthrough", "ActualFallthroughGeometry")
    add("gap105-actual-displacement128", lambda m, r: r.__setitem__("gaps", [0, 105]),
        "Rel8OutOfRange", "Branch", "ActualBranchGeometry")
    add("span-exceeds-FFFF", lambda m, r: r.__setitem__("syntheticBase", 0xFFD4),
        "SpanOutsideProfile", "Span", "ActualSpanGeometry")
    for label, value in (("origin-negative", -1), ("origin10000", 65536),
                         ("origin-bool", True), ("origin-string", "4096"),
                         ("origin-float", 4096.0), ("origin-null", None)):
        add(label, lambda m, r, v=value: r.__setitem__("syntheticBase", v),
            "OriginInvalid", "Span", "AddressTypeOrRange")

    def with_assignments(change):
        def mutate(model, candidate):
            rows = _explicit_assignments()
            change(rows)
            candidate["siteAssignments"] = rows
        return mutate
    add("missing-assignment", with_assignments(lambda rows: rows.pop()), "AssignmentShape", "Input")
    add("duplicate-assignment", with_assignments(lambda rows: rows.__setitem__(1, copy.deepcopy(rows[0]))),
        "AssignmentInventory", "Inventory")
    add("actual-instruction-overlap", with_assignments(lambda rows: _change_assignment(rows, 0x5571, -2)),
        "InstructionOverlap", "Overlap", "ActualSpanGeometry")
    add("actual-below-join-gap", with_assignments(lambda rows: _change_assignment(rows, 0x55C3, 1)),
        "FallthroughMismatch", "Fallthrough", "ActualFallthroughGeometry")
    def shift_after(rows, first):
        logical_order = [row[0] for row in SITES]
        for row in rows[logical_order.index(first):]:
            row["syntheticAssignedPC"] += 1
    for label, site in (("actual-common-edge-gap", 0x5572), ("actual-JLT-false-gap", 0x557F),
                        ("actual-JBS7-false-gap", 0x5588), ("actual-JBS5-false-gap", 0x558B),
                        ("actual-join5592-to5594-gap", 0x5594)):
        add(label, with_assignments(lambda rows, first=site: shift_after(rows, first)),
            "FallthroughMismatch", "Fallthrough", "ActualFallthroughGeometry")
    def move_below(rows, delta):
        for row in rows:
            if row["logicalSiteId"] >= 0x55BF:
                row["syntheticAssignedPC"] += delta
    add("actual-assigned-target-displacement128", with_assignments(lambda rows: move_below(rows, 105)),
        "Rel8OutOfRange", "Branch", "ActualBranchGeometry")
    add("actual-assigned-target-displacement-minus129",
        with_assignments(lambda rows: move_below(rows, -152)),
        "Rel8OutOfRange", "Branch", "ActualBranchGeometryControl_NotAdmissibleRearrangement")
    add("actual-independent-addresses-disagree-declared-gap",
        with_assignments(lambda rows: move_below(rows, 1)),
        "AssignmentModelMismatch", "Policy", "ActualGeometryThenPlanPolicy")
    return entries


def main():
    if sys.argv[1:] == ["--observe-absent"]:
        absent = not (RESEARCH / "layout_feasibility_analysis.py").exists()
        assert absent, "Absence observation requires genuinely absent analyzer"
        print(json.dumps({"milestone": "M2be", "kind": "AnalyzerNotImplemented", "analyzerCalls": 0,
                          "testsRun": 0, "fakeRED": False}, sort_keys=True))
        return
    assert not sys.argv[1:], "No ROM, paths or execution arguments accepted"
    from layout_feasibility_analysis import (
        LayoutError, branch_geometry, evaluate_layout, instruction_span,
    )
    upstream = json.loads((RESEARCH / "typed_lowering_contract.json").read_text(encoding="utf-8"))
    canonical_upstream = _stable(upstream)
    counts = {"layoutSuccessCalls": 0, "layoutRefusalCalls": 0,
              "successfulLayoutLabels": 0, "negativeMutationLabels": 0,
              "branchControlCalls": 0, "branchControlSuccesses": 0, "branchControlRefusals": 0,
              "spanControlCalls": 0, "spanControlSuccesses": 0, "spanControlRefusals": 0,
              "assignmentRowsCompared": 0, "edgeRowsCompared": 0,
              "terminalMarkersCompared": 0, "proofLevelChecks": 0,
              "immutabilityChecks": 0, "contextRowsCompared": 0, "pathRowsCompared": 0,
              "orderedWriteObligationsCompared": 0, "holeRowsCompared": 0}
    success_keys, geometry_keys, negative_keys, branch_keys, span_keys = set(), set(), set(), set(), set()
    reasons, domains = {}, {}

    def unchanged(model, candidate, before):
        assert (_stable(model), _stable(candidate)) == before, "Pure APIs mutated caller data"
        counts["immutabilityChecks"] += 2

    def successful(candidate, label):
        base, gaps, order = candidate["syntheticBase"], tuple(candidate["gaps"]), tuple(candidate["blockOrder"])
        expected = expected_layout(base, gaps, order)
        assert expected["geometryWithinAddressSpace"] and expected["allInternalFallthroughsAdjacent"]
        assert expected["allRelativeBranchesInRange"] and expected["canonicalBlockOrder"]
        before = canonical_upstream, _stable(candidate)
        actual = evaluate_layout(upstream, candidate)
        counts["layoutSuccessCalls"] += 1
        counts["successfulLayoutLabels"] += 1
        success_keys.add(_stable(candidate))
        geometry_keys.add(tuple(expected["spans"]))
        unchanged(upstream, candidate, before)
        assert actual["passed"] is True and actual["executionBlocked"] is True
        assert actual["runtimePermission"] is False and actual["targetBytes"] == 0
        assert actual["proofLevels"] == PROOF_LEVELS
        counts["proofLevelChecks"] += len(PROOF_LEVELS)
        assert actual["geometry"] == {
            "instructionSites": 18, "instructionLengthSum": 45,
            "blockLengths": {"Common": 16, "NotBelow": 23, "Below": 6},
            "originalOuterEnvelope": 86, "originalExcludedRegion": 41,
        }
        assert len(actual["assignments"]) == 18
        actual_assignments = {row["logicalSiteId"]: row for row in actual["assignments"]}
        assert len(actual_assignments) == 18
        for pc, form, length, _, _ in SITES:
            start = expected["assigned"][pc]
            assert actual_assignments[pc] == {
                "logicalSiteId": pc, "syntheticAssignedPC": start,
                "length": length, "endExclusive": start + length, "formId": form,
            }, label
            counts["assignmentRowsCompared"] += 1
        assert [row["logicalSiteId"] for row in actual["assignments"]] == [row[0] for row in SITES]
        assert len(actual["edges"]) == 21
        edge_rows = {(row["source"], row["target"], row["kind"]): row for row in actual["edges"]}
        assert len(edge_rows) == 21
        lengths = {pc: length for pc, _, length, _, _ in SITES}
        for source, target in FALLTHROUGHS:
            row = edge_rows[(source, target, "Fallthrough")]
            assert row == {"source": source, "target": target, "kind": "Fallthrough",
                           "assignedSource": expected["assigned"][source],
                           "nextPC": expected["assigned"][source] + lengths[source],
                           "assignedTarget": expected["assigned"][target],
                           "signedDelta": None, "feasible": True}, label
            counts["edgeRowsCompared"] += 1
        for branch in expected["branches"]:
            source, target = branch["site"], branch["targetSite"]
            assert edge_rows[(source, target, "ConditionalTaken")] == {
                "source": source, "target": target, "kind": "ConditionalTaken",
                "assignedSource": branch["branchStart"], "nextPC": branch["nextPC"],
                "assignedTarget": branch["targetStart"], "signedDelta": branch["signedDelta"],
                "feasible": True}, label
            counts["edgeRowsCompared"] += 1
        assert len(actual["terminalMarkers"]) == 2
        markers = {row["logicalStopBefore"]: row for row in actual["terminalMarkers"]}
        for terminal in expected["terminals"]:
            stop, source = terminal["logicalTerminalMarker"], terminal["lastLogicalSite"]
            boundary = terminal["syntheticBoundary"]
            assert edge_rows[(source, stop, "AnalyticalTerminal")] == {
                "source": source, "target": stop, "kind": "AnalyticalTerminal",
                "assignedSource": expected["assigned"][source], "nextPC": boundary,
                "assignedTarget": boundary, "signedDelta": None, "feasible": True}, label
            adjacent = terminal["physicallyAdjacentBlocks"]
            assert len(adjacent) <= 1
            assert markers[stop] == {
                "logicalStopBefore": stop, "assignedEndExclusive": boundary,
                "requiredContinuation": "ExternalNativeContinuationNotEstablished",
                "adjacentBlock": adjacent[0] if adjacent else None,
                "hazard": "PotentialFallthroughIntoSyntheticBlock" if adjacent else "UnmodeledGapOrOutsideRegion",
                "nativeExitIsolation": "Blocked",
            }, label
            counts["edgeRowsCompared"] += 1
            counts["terminalMarkersCompared"] += 1
        assert actual["contextRetention"] == CONTEXT, label
        counts["contextRowsCompared"] += len(CONTEXT)
        assert actual["pathsLogical"] == upstream["pathObligations"]
        assert len(actual["pathsLogical"]) == 4
        for actual_path, (name, logical_sites, terminal) in zip(actual["pathsLogical"], PATHS):
            assert (actual_path["id"], actual_path["pcs"], actual_path["terminal"],
                    actual_path["instructionCount"]) == (name, list(logical_sites), terminal, len(logical_sites))
            assert [(w["pc"], w["address"], w["widthBits"]) for w in actual_path["orderedWrites"]] == list(WRITES[name])
            assert all(w["ordered"] is True and w["sameValueWrite"] == "RetainFreshOrdinal"
                       for w in actual_path["orderedWrites"])
            assert (actual_path["finalCF"], actual_path["finalZF"], actual_path["finalDD"]) == (
                int(name == "A"), 0, 0)
            if name == "B":
                assert 0x0124 in actual_path["mustNotRead"]
                assert all(read["address"] != 0x0124 for read in actual_path["orderedReads"])
            if name == "C":
                assert actual_path["historical"] == "StaticPrimaryAndInventedCoverage"
            counts["pathRowsCompared"] += 1
            counts["orderedWriteObligationsCompared"] += len(WRITES[name])
        assert actual["currentSourceStaticOnly"] is True and actual["historicalCoverageInheritedOnly"] is True
        assert all(actual[key] == 0 for key in
                   ("encoderCalls", "decoderCalls", "CPUExecutions", "actualROMExecutions", "nativeWriteJournals"))
        max_end = max(end for _, _, end in expected["spans"])
        assert actual["syntheticEnvelope"] == {
            "start": base, "endExclusive": max_end, "extent": max_end - base,
        }
        assert actual["holes"] == [{"start": h["start"], "endExclusive": h["endExclusive"],
                                    "classification": "UnmodeledSymbolicHole_NotPaddingOrFreeROM"}
                                   for h in expected["holes"]]
        counts["holeRowsCompared"] += len(expected["holes"])
        return actual

    for row in named_scenarios():
        expected = row["expected"]
        if (expected["canonicalBlockOrder"] and expected["geometryWithinAddressSpace"] and
                expected["allInternalFallthroughsAdjacent"] and expected["allRelativeBranchesInRange"]):
            successful(request(row["base"], row["gaps"], row["order"]), row["label"])
    for base in (0, 0x1000, 0x2345, 0x556F, 0x8000, 0xF000):
        for gap in range(105):
            successful(request(base, (0, gap)), f"relocated-{base}-gap-{gap}")
    successful(request(assignments=_explicit_assignments()), "explicit-canonical-assignment")

    for label, model, candidate, code, stage, domain in _negative_definitions(upstream):
        counts["negativeMutationLabels"] += 1
        negative_keys.add((_stable(model), _stable(candidate)))
        domains[domain] = domains.get(domain, 0) + 1
        before = _stable(model), _stable(candidate)
        seen = []
        for _ in range(2):
            try:
                evaluate_layout(model, candidate)
            except LayoutError as error:
                assert (error.code, error.stage) == (code, stage), (label, error.code, error.stage, code, stage)
                assert type(error.path) is str and error.path
                assert not hasattr(error, "partialResult")
                seen.append((error.code, error.path, error.stage, str(error)))
                counts["layoutRefusalCalls"] += 1
                reasons[code] = reasons.get(code, 0) + 1
            else:
                raise AssertionError(f"Mutation not refused: {label}")
            unchanged(model, candidate, before)
        assert seen[0] == seen[1], f"Non-deterministic refusal: {label}"

    def branch_control(start, length, target):
        expected_failure = relative_condition(start, length, target)
        branch_keys.add(_stable([start, length, target]))
        counts["branchControlCalls"] += 1
        try:
            actual = branch_geometry(start, length, target)
        except LayoutError as error:
            assert expected_failure is not None
            assert error.code == BRANCH_CODES[expected_failure]
            assert error.stage == ("Span" if expected_failure in SPAN_CODES else "Branch")
            counts["branchControlRefusals"] += 1
        else:
            assert expected_failure is None, (start, length, target)
            assert actual == {"nextPC": start + length, "signedDelta": target - start - length,
                              "feasible": True}
            counts["branchControlSuccesses"] += 1

    for start in (0x1000, 0x8000, 0xFF00):
        for length in (2, 3):
            for delta in range(-129, 129):
                branch_control(start, length, start + length + delta)
    for start, length, target in (
        (0xFFFE, 2, 0xFFFF), (0xFFFD, 3, 0xFFFF),
        (0xFFFF, 2, 0xFFFF), (0x10000, 2, 0xFFFF),
        (0, 2, -1), (0xFFFC, 2, 0x10000),
        (0xFFFD, 2, 0xFFFF), (0xFFFC, 3, 0xFFFF),
        (0, 2, 0), (0, 3, 0),
    ):
        branch_control(start, length, target)

    def span_control(start, length):
        expected_failure = span_condition(start, length)
        span_keys.add(_stable([start, length]))
        counts["spanControlCalls"] += 1
        try:
            actual = instruction_span(start, length)
        except LayoutError as error:
            assert expected_failure is not None
            assert (error.code, error.stage) == (SPAN_CODES[expected_failure], "Span")
            counts["spanControlRefusals"] += 1
        else:
            assert expected_failure is None
            assert actual == {"start": start, "endExclusive": start + length, "lastByte": start + length - 1}
            counts["spanControlSuccesses"] += 1

    for start in range(0xFFF8, 0x10002):
        for length in range(1, 6):
            span_control(start, length)
    for start, length in ((0, 1), (0xFFFF, 1), (-1, 1), (True, 1), (1, True),
                          (1, 0), (1, -1), (1, 6), (1, 1.0), ("1", 1), (None, 1)):
        span_control(start, length)
    assert counts["layoutRefusalCalls"] == 2 * counts["negativeMutationLabels"]
    assert counts["edgeRowsCompared"] == 21 * counts["layoutSuccessCalls"]
    assert counts["assignmentRowsCompared"] == 18 * counts["layoutSuccessCalls"]
    assert counts["terminalMarkersCompared"] == 2 * counts["layoutSuccessCalls"]
    assert canonical_upstream == _stable(upstream)
    print(json.dumps({
        "milestone": "M2be", "passed": True, "failed": 0, "skipped": 0, "firstMismatch": None,
        "independentArithmetic": reviewed_arithmetic(),
        "counts": counts,
        "deduplicatedSuccessfulLayoutRequests": len(success_keys),
        "deduplicatedSuccessfulGeometricAssignments": len(geometry_keys),
        "deduplicatedNegativeMutationInputs": len(negative_keys),
        "deduplicatedBranchControls": len(branch_keys), "deduplicatedSpanControls": len(span_keys),
        "negativeDomains": domains, "refusalReasons": reasons,
        "allExitIsolationBlocked": True,
        "branchControlDomain": "InventedScalarGeometryOnly_NotAdmissibleCFGRearrangements",
        "M2beTargetBytes": 0, "M2beOriginalROMExecutions": 0,
        "encoderCalls": 0, "decoderCalls": 0, "CPUCalls": 0,
        "executionAuthority": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
