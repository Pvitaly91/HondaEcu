"""M2bq source draft: freeze first, then bounded actual continuous execution.

No execution occurs on import or --freeze-only. Every positive architectural
value is frozen from immutable independent references before building/running
the new composite harness. Actual rows are compared in full and retained using
an explicitly reversible codec, then whole decompressed streams are compared.
"""

import argparse
import gzip
from pathlib import Path
import sys
sys.dont_write_bytecode = True
from production_composite_common import (
    BASE_SHA, COMPOSITE_SHA, binding, bounded_json, canonical, first_difference,
    reference_bindings, require,
)
from production_composite_corpus import coverage, iter_cases, seed_digest
from production_composite_emission import emitted_program
from production_composite_oracle import architectural_projection, actual_architectural_projection, expected_case
from production_composite_projection import SCHEMA, restore
import production_composite_records as records
import production_composite_boundary as boundary
from production_composite_stream import (
    CanonicalWriter, Harness, ROW_LIMIT, compare_full_stream, file_binding, native_build, write_new,
)
from production_composite_topology import SCHEMA as TOPOLOGY_SCHEMA, source_bindings as topology_bindings

HERE = Path(__file__).resolve().parent
INPUT_NAME = "research/p28-word0196/rust-production-composite/closed_inputs.json"
FREEZE = "pre-runtime-freeze.json"


def owned_path(root, value, role):
    root = Path(root).resolve()
    lexical = Path(value)
    if not lexical.is_absolute():
        lexical = root / lexical
    path = lexical.resolve()
    require(path.is_relative_to(root), "M2bqOutputMustRemainInsideRepository")
    name = path.relative_to(root).as_posix()
    require(role in ("evidence", "target") and ".." not in lexical.parts, "ClosedOwnedRoleAndNoTraversal")
    parts = path.relative_to(root).parts
    required_root = "m2bq-public-evidence" if role == "evidence" else "m2bq-runtime-target"
    require(len(parts) >= 2 and parts[0:2] == (".tmp", required_root), "ExactM2bqRoleRootRequired")
    if role == "evidence":
        require(len(parts) >= 3 and parts[2] == "composite", "CompositeEvidenceCannotUseCompatibilityOrPinnedRole")
    # The local immutable ownership record predates the complete protected
    # Before. CI uses precisely these source-bound two roots, never a prefix
    # that could select the pinned/legacy tree or a historical cache.
    ownership_path = root / "private/reports/m2bq/OWNED_OUTPUT_PATHS.json"
    if ownership_path.exists():
        ownership = bounded_json(ownership_path.read_bytes())
        require(ownership["milestone"] == "M2bq" and ownership["exactBase"] == BASE_SHA
                and ".tmp/" + required_root in ownership["repositoryTemporaryRoots"]
                and ownership["oldM2bpRootsReclassified"] is False, "ActualImmutableLocalOwnershipRole")
    require(path == lexical.absolute(), "NoLinkedOwnedOutputParents")
    return path


def negative_expected(root):
    # This module owns the independent refusal/fault protocol. It must be
    # complete, reviewed and source-bound before either freeze can succeed.
    import production_composite_negative as negative
    result = list(negative.expected_negative_records(root))
    require(len(result) == 33, "ExactFrozenNegativeCapabilityInventory")
    return result


def prepare_inputs(root):
    """Pure preparation, invoked only after the protected Before release.

    The file contains invented seeds only, never PROGRAM bytes. A publication
    step must copy this unchanged new file before the final source manifest is
    materialized. A second differing generation is refused, never overwritten.
    """
    target = HERE / "rust-production-composite/closed_inputs.json"
    values = list(iter_cases(root))
    content = canonical(values) + b"\n"
    if target.exists():
        require(target.read_bytes() == content, "ExistingClosedInputsMustRemainByteIdentical")
    else:
        with target.open("xb") as output:
            output.write(content)
    return {"classification": "PureInventedSeedSourcePreparation_NoCpu", "path": str(target),
            "binding": file_binding(target), "cases": len(values), "cpuInstances": 0,
            "programBytesPersisted": 0}


def source_state(root, pinned, legacy):
    import production_composite_analysis as analysis
    proof, contract = analysis.source_checks(root, pinned, legacy)
    require(proof["passed"] is True and contract["milestone"] == "M2bq", "ReviewedNewSourceTransition")
    from production_composite_negative import SCHEMA as negative_schema
    runtime_protocol = {"compiledHeaderPaths": list(records.HEADER_PATHS), "closedInputs": binding(root, INPUT_NAME),
                        "losslessProjection": SCHEMA, "programTopology": TOPOLOGY_SCHEMA,
                        "negativeProtocol": negative_schema,
                        "executableBoundaryRecords": 2,
                        "canonicalRecords": {"positiveIncludingFourSmokes": 5478, "negativeIncludingHeader": 36}}
    require(first_difference(runtime_protocol, contract["runtimeProtocol"]) is None,
            "ContractMustMatchReviewedLosslessRuntimeProtocolExactly")
    require(first_difference({"source": "ActualUnchangedM2bjEmitter_InMemoryOnly", "base": 4096,
            "endExclusive": 4147, "length": 51, "nodes": 20, "forms": 16, "sha256": COMPOSITE_SHA,
            "bothDdActualContentHashRequired": True, "dd0Dd1BytesEqual": True, "immutableAfterAdmission": True,
            "persistentOrPublicFullPayloadAllowed": False, "ephemeralInMemoryStdinSerializationAllowed": True,
            "arbitraryStreamOrFileLoaderAllowed": False}, contract["program"]) is None,
            "ClosedActualEmitterIdentityAndNoLoaderContract")
    require(first_difference({"mode": "ClosedM2bjComposite", "defaultOffFeature": "p28-word0196-audit",
            "mechanism": ["ProductionCpu", "ProductionBus", "ProductionDecodeChecked", "SharedProductionExecuteDecoded"],
            "oneCpuPerCase": True, "oneBusPerCase": True, "oneDataInitializationPerCase": True,
            "oneFunctionalTransitionPerCase": True, "reseedBetweenStepsAllowed": False,
            "expectedStateAssignmentAllowed": False, "maximumRetirements": 16, "budgetCheckedBeforeDecoder": True,
            "actualSuccessorCheckedBeforeNextFetch": True, "terminalDirectJCount": 1, "terminalPcs": [21910, 21957],
            "externalFetchAllowed": False, "postTerminalApiRefusalRequired": True,
            "partialFaultStateMustBeRetained": True, "partialFaultEffectsClaimedAtomic": False}, contract["execution"]) is None,
            "ClosedContinuousExecutionContract")
    counts = contract["coverageRequirementsNotActualResults"]
    require(all(type(counts[key]) is type(value) and counts[key] == value for key, value in {
        "initialSmokeExecutionsSeparate": 4, "positiveCases": 5470, "internalSfPairs": 2735,
        "positiveRetirements": 73784, "positiveLogicalReads": 49112, "positiveLogicalWrites": 19162,
        "negativeCanonicalRecords": 33, "pureCodecAndComparatorTests": 32,
        "executableBoundaryRecords": 2,
        "negativeOrSmokeCountersIncludedIn5470": False}.items()), "IndependentExpectedCoverageIsNotActualEvidence")
    require(contract["compatibilityRequirements"]["legacyBudgetAboveOneStillSealsAfterOne"] is True
            and contract["compatibilityRequirements"]["architecturalOrObservationFieldsExcluded"] == []
            and contract["jsonMayPromoteEvidenceStatus"] is False and contract["firmwareReady"] is False,
            "NoOneStepRelaxationOrJsonAuthorityPromotion")
    return {"sourceProof": proof, "contract": binding(root, "research/p28-word0196/production_composite_contract.json"),
            "immutableReferences": reference_bindings(root), "topologySources": topology_bindings(root),
            "compiledSources": [binding(root, name) for name in records.HEADER_PATHS],
            "closedInventedInputs": binding(root, INPUT_NAME)}


def positive_expectations(root):
    yield records.header(root)
    yield records.program_admission()
    yield records.psw_sweep()
    from production_composite_negative import control_seeds
    smokes = control_seeds(root)
    for index, path in enumerate("ABCD", 1):
        expected = expected_case(root, smokes[path])
        expected["kind"] = "composite_smoke_observation"
        expected["smoke_index"] = index
        yield expected
    for request in iter_cases(root):
        yield expected_case(root, request)
    yield records.summary()


def freeze(root, pinned, legacy, output, target):
    require(not (output / FREEZE).exists(), "ImmutableFreezeAlreadyExists")
    output.mkdir(parents=True, exist_ok=True)
    before = source_state(root, pinned, legacy)
    request_values = bounded_json((root / INPUT_NAME).read_bytes(), 32 * 1024 * 1024)
    require(type(request_values) is list and len(request_values) == 5470, "FrozenCompiled5470SeedSource")
    require(canonical(request_values) == canonical(list(iter_cases(root))), "CompiledSeedFileMustEqualUnchangedM2bnCorpus")
    _, emission = emitted_program(root)
    positive = CanonicalWriter(output / "expected-positive.jsonl.gz")
    for record in positive_expectations(root):
        positive.put(record)
    positive_info = positive.close()
    negative = CanonicalWriter(output / "expected-negative.jsonl.gz")
    negative.put(records.header(root))
    for record in boundary.expected_records(root):
        negative.put(record)
    for record in negative_expected(root):
        negative.put(record)
    negative_info = negative.close()
    require(positive_info["records"] == 5478 and negative_info["records"] == 36,
            "ExactFrozenRowsIncludeFourInitialSmokesAndUnchanged5470Corpus")
    after = source_state(root, pinned, legacy)
    require(first_difference(before, after) is None, "SourcesChangedDuringIndependentFreeze")
    import production_composite_negative as negative_protocol
    specimen = negative_protocol.comparator_control(root)
    frozen = {"milestone": "M2bq", "schemaVersion": 1, "classification": "IndependentPreRuntimeFreeze_NotExecutionEvidence",
              "exactBase": BASE_SHA, "newCompositeExecutionsBeforeFreeze": 0,
              "newCompositeCpuInstancesBeforeFreeze": 0, "originalRomExecutions": 0,
              "sourceState": before, "orderedSeeds": seed_digest(root), "coverage": coverage(root),
              "losslessSchema": SCHEMA, "programTopologySchema": TOPOLOGY_SCHEMA,
              "actualEmitterReceipt": emission, "expectedPositive": positive_info,
              "expectedNegative": negative_info, "expectedNegativeRecords": 33,
              "expectedExecutableBoundaryRecords": 2, "executableBoundarySchema": boundary.SCHEMA,
              "negativeProtocolSchema": negative_protocol.SCHEMA,
              "negativeCaseIds": list(negative_protocol.NEGATIVE_IDS),
              "negativeControlSeeds": negative_protocol.control_seeds(root),
              "initialSmokeControlSeeds": [negative_protocol.control_seeds(root)[path] for path in "ABCD"],
              "expectedSmokeCounters": {"executions": 4, "cpuInstances": 4, "busInstances": 4,
                                        "retirements": 54, "logicalReads": 36, "logicalWrites": 14},
              "comparatorSpecimenRequest": specimen["request"],
              "comparatorSpecimenExpectedSha256": __import__("hashlib").sha256(canonical(specimen["expected"])).hexdigest(),
              "comparatorMutationIds": specimen["mutationIds"],
              "outputRelative": output.relative_to(root).as_posix(), "targetRelative": target.relative_to(root).as_posix(),
              "cpuExecutionNotAuthorizedByJson": True, "firmwareReady": False}
    write_new(output / FREEZE, frozen)
    # Pure tests are run only after the durable formal freeze exists and are
    # source-bound. They cannot construct a Cpu/Bus or call any target process.
    from production_composite_protocol_tests import run_pure_tests
    checks = run_pure_tests(root)
    checks["preRuntimeFreeze"] = file_binding(output / FREEZE)
    write_new(output / "pure-protocol-tests.json", checks)
    return frozen


def revalidate(root, pinned, legacy, output, target, frozen):
    require(frozen["milestone"] == "M2bq" and frozen["exactBase"] == BASE_SHA
            and frozen["newCompositeExecutionsBeforeFreeze"] == 0, "ExactIndependentPreRuntimeFreeze")
    require(frozen["outputRelative"] == output.relative_to(root).as_posix()
            and frozen["targetRelative"] == target.relative_to(root).as_posix(), "FrozenOwnedOutputAndTargetPaths")
    require(first_difference(frozen["sourceState"], source_state(root, pinned, legacy)) is None,
            "AllRuntimeSourcesMustMatchIndependentFreeze")
    for lane in ("Positive", "Negative"):
        require(file_binding(output / ("expected-" + lane.lower() + ".jsonl.gz"))
                == frozen["expected" + lane]["compressed"], "ImmutableExpectedStreamChanged:" + lane)
    checks = bounded_json((output / "pure-protocol-tests.json").read_bytes())
    require(checks["passed"] is True and checks["testCount"] == 32 and checks["cpuInstances"] == 0
            and checks["preRuntimeFreeze"] == file_binding(output / FREEZE), "ActualPureProtocolTestsRequiredBeforeCpu")
    for name in ("FIRST_FAILURE.json", "runtime.start.json", "runtime.end.json", "runtime.failure.json", "summary.json"):
        require(not (output / name).exists(), "OneActualAttemptOnly_NoRetry:" + name)


def frozen_records(path):
    total = 0
    with gzip.open(path, "rb") as source:
        while line := source.readline(ROW_LIMIT + 1):
            require(len(line) <= ROW_LIMIT and line.endswith(b"\n"), "FrozenBoundedCompleteRecord")
            total += len(line)
            require(total <= 8 * 1024 * 1024 * 1024, "BoundedFrozenExpectationStream")
            yield restore(bounded_json(line, ROW_LIMIT))


def _execute(root, pinned, legacy, output, target, frozen, resources):
    revalidate(root, pinned, legacy, output, target, frozen)
    write_new(output / "source-transition.json", frozen["sourceState"])
    executable, build_receipt = native_build(root, target, output)
    executable_before = file_binding(executable)
    process = None
    positive = CanonicalWriter(output / "positive-canonical.jsonl.gz")
    resources["positive"] = positive
    negative = CanonicalWriter(output / "negative-canonical.jsonl.gz")
    resources["negative"] = negative
    expected_positive = iter(frozen_records(output / "expected-positive.jsonl.gz"))
    expected_negative = iter(frozen_records(output / "expected-negative.jsonl.gz"))
    counters = {"positiveCpuInstances": 0, "positiveBusInstances": 0, "positiveDataInitializations": 0,
                "positiveFunctionalTransitions": 0, "positiveCompositeExecutions": 0,
                "successfulRetirements": 0, "functionalLogicalReads": 0, "functionalLogicalWrites": 0,
                "seedLogicalWrites": 0, "seedRawWrites": 0, "programCallbacks": 0,
                "selectedFetches": 0, "decoderProbes": 0, "internalSfPairs": 0,
                "pathCounts": {path: 0 for path in "ABCD"}, "positiveRefusedProgramEvents": 0,
                "positiveExternalProgramAttempts": 0, "positiveServicedExternalProgramAttempts": 0,
                "functionalSameValueWrites": 0, "functionalRawReads": 0, "functionalRawWrites": 0,
                "diagnosticSnapshots": 0}
    observed_psw, observed_dd, observed_sf, observed_scb, observed_nodes, observed_forms, observed_ah, observed_18e = (set() for _ in range(8))
    negative_rows = []
    executable_boundary_rows, executable_boundary_receipts = [], []
    prior_pair = None
    smoke_counters = {"executions": 0, "cpuInstances": 0, "busInstances": 0,
                      "retirements": 0, "logicalReads": 0, "logicalWrites": 0,
                      "pathCounts": {path: 0 for path in "ABCD"}, "programCallbacks": 0}

    def compare(expected, actual, lane):
        difference = first_difference(expected, actual)
        if difference is not None:
            write_new(output / "FIRST_FAILURE.json", {"milestone": "M2bq", "passed": False,
                      "classification": "FirstActualObservationMismatch_NoRetry", "lane": lane,
                      "firstMismatch": difference, "caseKey": [actual.get("case_id"), actual.get("internal_sf")],
                      "preRuntimeFreeze": file_binding(output / FREEZE), "acceptance": False})
            raise ValueError("IndependentFullObservationMismatch:" + difference["field"])

    try:
        process = Harness([str(executable)], root, output)
        resources["process"] = process
        actual_header = process.receive()
        positive.put(actual_header)
        negative.put(actual_header)
        compare(next(expected_positive), actual_header, "positive-header")
        compare(next(expected_negative), actual_header, "negative-header")
        for actual, receipt in boundary.observe(executable, root, output):
            negative.put(actual)
            compare(next(expected_negative), actual, "no-cpu-executable-loader-or-arbitrary-command-refusal")
            executable_boundary_rows.append(actual)
            executable_boundary_receipts.append(receipt)
        require(len(executable_boundary_rows) == 2, "TwoActualExecutableBoundaryRefusalsBeforeAnyNewCpu")
        program, emission = emitted_program(root)
        require(emission == frozen["actualEmitterReceipt"], "ActualInMemoryEmitterIdentityMustMatchFreeze")
        process.send(program)
        del program
        actual = process.receive()
        positive.put(actual)
        compare(next(expected_positive), actual, "actual-program-admission")
        process.send({"kind": "psw_sweep"})
        actual = process.receive()
        positive.put(actual)
        compare(next(expected_positive), actual, "all65536-admission-only-psw")
        for index, request in enumerate(frozen["initialSmokeControlSeeds"], 1):
            process.send({"kind": "smoke", "input": request})
            actual = process.receive()
            positive.put(actual)
            compare(next(expected_positive), actual, "initial-closed-four-path-smoke")
            compare(architectural_projection(root, request), actual_architectural_projection(actual),
                    "initial-smoke-independent-architectural-projection")
            audit = actual["report"]["audit"]
            smoke_counters["executions"] += actual["full_production_composite_executions"]
            smoke_counters["cpuInstances"] += actual["cpu_instances"]
            smoke_counters["busInstances"] += actual["bus_instances"]
            smoke_counters["retirements"] += audit["successful_retirements"]
            smoke_counters["pathCounts"][actual["report"]["path"]] += 1
            smoke_counters["programCallbacks"] += len(audit["program_events"])
            smoke_counters["logicalReads"] += sum(row["phase"] == "Functional" and row["operation"] == "Read"
                                                   for row in audit["data_events"])
            smoke_counters["logicalWrites"] += sum(row["phase"] == "Functional" and row["operation"] == "Write"
                                                    for row in audit["data_events"])
        require(all(smoke_counters[key] == expected for key, expected in frozen["expectedSmokeCounters"].items())
                and smoke_counters["pathCounts"] == {path: 1 for path in "ABCD"}, "FourActualSmokesCountedSeparately")
        for ordinal, request in enumerate(iter_cases(root)):
            process.send(request)
            actual = process.receive()
            positive.put(actual)
            compare(next(expected_positive), actual, "continuous-positive")
            shared_expected = architectural_projection(root, request)
            shared_actual = actual_architectural_projection(actual)
            compare(shared_expected, shared_actual, "independent-shared-architectural-projection")
            report, audit = actual["report"], actual["report"]["audit"]
            counters["pathCounts"][report["path"]] += 1
            observed_psw.add(shared_actual["entry"]["psw"])
            observed_dd.add(report["entry"]["cpu"]["dd"])
            observed_sf.add(report["entry"]["cpu"]["sf"])
            observed_scb.add(shared_actual["entry"]["scb"])
            observed_ah.add(report["entry"]["cpu"]["a"] >> 8)
            observed_18e.add(report["entry"]["ram"][0x18E - 0x80])
            observed_nodes.update(step["node_identity"] for step in report["steps"])
            observed_forms.update(step["form"] for step in report["steps"])
            for name, actual_name in (("positiveCpuInstances", "cpu_instances"), ("positiveBusInstances", "bus_instances"),
                                      ("positiveDataInitializations", "data_initializations"),
                                      ("positiveFunctionalTransitions", "functional_transitions"),
                                      ("positiveCompositeExecutions", "full_production_composite_executions")):
                counters[name] += actual[actual_name]
            counters["successfulRetirements"] += audit["successful_retirements"]
            for row in audit["data_events"]:
                if row["phase"] == "Seed":
                    counters["seedLogicalWrites"] += row["operation"] == "Write"
                else:
                    counters["functionalLogicalReads"] += row["operation"] == "Read"
                    counters["functionalLogicalWrites"] += row["operation"] == "Write"
                    counters["functionalSameValueWrites"] += row["operation"] == "Write" and row["same_value"] is True
            seed_logical = {row["ordinal"] for row in audit["data_events"] if row["phase"] == "Seed"}
            counters["seedRawWrites"] += sum(row["operation"] == "Write" and row["logical_ordinal"] in seed_logical
                                             for row in audit["raw_data_events"])
            counters["functionalRawReads"] += sum(row["operation"] == "Read" and row["logical_ordinal"] not in seed_logical
                                                   for row in audit["raw_data_events"])
            counters["functionalRawWrites"] += sum(row["operation"] == "Write" and row["logical_ordinal"] not in seed_logical
                                                    for row in audit["raw_data_events"])
            counters["diagnosticSnapshots"] += len(audit["diagnostic_events"])
            counters["programCallbacks"] += len(audit["program_events"])
            counters["decoderProbes"] += sum(row["acquired_purpose"] == "DecoderProbe" for row in audit["program_events"])
            counters["selectedFetches"] += sum(row["acquired_purpose"] == "ArchitecturalSelectedFetch" for row in audit["program_events"])
            counters["positiveRefusedProgramEvents"] += sum(not row["serviced"] for row in audit["program_events"])
            external = [row for row in audit["program_events"] if not 4096 <= row["address"] < 4147]
            counters["positiveExternalProgramAttempts"] += len(external)
            counters["positiveServicedExternalProgramAttempts"] += sum(row["serviced"] for row in external)
            # Pair identity is explicit. Full rows were compared above; this
            # supplementary check never normalizes SF in canonical evidence.
            if ordinal % 2 == 0:
                prior_pair = request["case_id"]
            else:
                require(request["case_id"] == prior_pair and actual["internal_sf"] is True,
                        "ActualAdjacentInternalSfPair")
                counters["internalSfPairs"] += 1
        process.send({"kind": "capabilities"})
        for _ in range(33):
            actual = process.receive()
            negative.put(actual)
            compare(next(expected_negative), actual, "negative-capability")
            negative_rows.append(actual)
        require(next(expected_negative, None) is None, "AllNegativeExpectedRecordsConsumedThroughEOF")
        process.send({"kind": "finish"})
        actual = process.receive()
        positive.put(actual)
        compare(next(expected_positive), actual, "actual-positive-summary")
        require(next(expected_positive, None) is None, "AllPositiveExpectedRecordsConsumedThroughEOF")
        process.finish()
        positive_info, negative_info = positive.close(), negative.close()
        require(file_binding(executable) == executable_before, "ActualRuntimeBinaryUnchanged")
        after_sources = source_state(root, pinned, legacy)
        require(first_difference(frozen["sourceState"], after_sources) is None, "FrozenSourcesUnchangedAfterActualExecution")
        require(file_binding(output / "expected-positive.jsonl.gz") == frozen["expectedPositive"]["compressed"]
                and file_binding(output / "expected-negative.jsonl.gz") == frozen["expectedNegative"]["compressed"],
                "IndependentExpectedStreamsRemainImmutableAfterActualExecution")
        positive_comparison = compare_full_stream(output / "expected-positive.jsonl.gz", output / "positive-canonical.jsonl.gz")
        negative_comparison = compare_full_stream(output / "expected-negative.jsonl.gz", output / "negative-canonical.jsonl.gz")
        require(positive_comparison["leftCompressed"] == frozen["expectedPositive"]["compressed"]
                and negative_comparison["leftCompressed"] == frozen["expectedNegative"]["compressed"]
                and positive_comparison["rightCompressed"] == positive_info["compressed"]
                and negative_comparison["rightCompressed"] == negative_info["compressed"],
                "FullByteComparisonJoinsSameImmutableOracleAndActualStreams")
        require(counters["positiveCompositeExecutions"] == counters["positiveCpuInstances"]
                == counters["positiveBusInstances"] == counters["positiveDataInitializations"]
                == counters["positiveFunctionalTransitions"] == 5470, "ActualContinuous5470SingleInstanceCases")
        require((counters["successfulRetirements"], counters["functionalLogicalReads"], counters["functionalLogicalWrites"])
                == (73784, 49112, 19162), "ActualIndependentFunctionalTotals")
        require(len(observed_psw) == 2048 and observed_dd == observed_sf == {False, True}
                and observed_scb == set(range(8)) and len(observed_nodes) == 20 and len(observed_forms) == 16
                and counters["positiveRefusedProgramEvents"] == counters["positiveExternalProgramAttempts"]
                == counters["positiveServicedExternalProgramAttempts"] == 0, "ActualClosedCoverageAndNoPostJFetch")
        counters.update({"distinctEntryPswCount": len(observed_psw), "entryPswValues": sorted(observed_psw),
                         "incomingDdValues": sorted(observed_dd), "internalSfValues": sorted(observed_sf),
                         "scbSelectors": sorted(observed_scb), "executedNodeIdentities": sorted(observed_nodes),
                         "executedForms": sorted(observed_forms), "distinctEntryAhCount": len(observed_ah),
                         "distinctInitialData018eCount": len(observed_18e)})
        from production_composite_negative import summarize_actual_negative_records
        negative_totals = summarize_actual_negative_records(negative_rows)
        result = {"milestone": "M2bq", "passed": True, "classification": "ActualContinuousProductionCompositeVerified_InventedOnly",
                  "exactBase": BASE_SHA, "programSha256": COMPOSITE_SHA,
                  "preRuntimeFreeze": file_binding(output / FREEZE), "sourceTransition": file_binding(output / "source-transition.json"),
                  "pureProtocolTests": file_binding(output / "pure-protocol-tests.json"),
                  "actualBuild": build_receipt, "actualExecutable": executable_before,
                  "runtimeStart": file_binding(output / "runtime.start.json"), "runtimeEnd": file_binding(output / "runtime.end.json"),
                  "positiveCanonical": positive_info, "negativeCanonical": negative_info,
                  "positiveWholeStreamComparison": positive_comparison, "negativeWholeStreamComparison": negative_comparison,
                  "actualPositiveCounters": counters, "actualNegativeCounters": negative_totals,
                  "actualSmokeCounters": smoke_counters,
                  "actualExecutableBoundaryCounters": {"records": len(executable_boundary_rows),
                      "processes": len(executable_boundary_receipts),
                      "cpuInstances": sum(row["cpu_instances"] for row in executable_boundary_rows),
                      "busInstances": sum(row["bus_instances"] for row in executable_boundary_rows)},
                  "executableBoundaryCommandReceipts": executable_boundary_receipts,
                  "all5470FullRawReportsMatch": True, "all5470IndependentArchitecturalProjectionsMatch": True,
                  "all33FullNegativeReportsMatch": True, "firstMismatch": None,
                  "originalRomExecutions": 0, "persistentProgramPayloads": 0, "nativeRejoinObserved": False,
                  "firmwareReady": False, "automaticRetries": 0}
        write_new(output / "summary.json", result)
        return result
    except BaseException as error:
        if process is not None:
            process.abort()
        if not (output / "FIRST_FAILURE.json").exists():
            write_new(output / "FIRST_FAILURE.json", {"milestone": "M2bq", "passed": False,
                      "classification": "FirstActualAttemptFailure_NoRetry", "diagnostic": str(error),
                      "acceptance": False, "automaticRetries": 0})
        raise


def execute(root, pinned, legacy, output, target, frozen):
    """Guard all setup as well as runtime; never abandon owned partial output."""
    resources = {}
    try:
        return _execute(root, pinned, legacy, output, target, frozen, resources)
    except BaseException as error:
        if not (output / "FIRST_FAILURE.json").exists():
            write_new(output / "FIRST_FAILURE.json", {"milestone": "M2bq", "passed": False,
                      "classification": "FirstActualSetupOrRuntimeFailure_NoRetry", "diagnostic": str(error),
                      "acceptance": False, "automaticRetries": 0})
        raise
    finally:
        process = resources.get("process")
        if process is not None and not process.finished:
            process.abort()
        partial, diagnostics = {}, []
        for name in ("positive", "negative"):
            writer = resources.get(name)
            if writer is not None:
                try:
                    partial[name] = writer.close()
                except BaseException as close_error:
                    diagnostics.append({"lane": name, "diagnostic": str(close_error)})
        if not (output / "summary.json").exists() and (partial or diagnostics):
            write_new(output / "PARTIAL_CANONICAL_STREAMS.json", {
                "classification": "ActualRetainedPartialStreams_NotAcceptance", "streams": partial,
                "closeDiagnostics": diagnostics, "automaticRetry": False, "passed": False})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical-root")
    parser.add_argument("--pinned-root")
    parser.add_argument("--output-dir")
    parser.add_argument("--target-dir")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-inputs-only", action="store_true")
    mode.add_argument("--freeze-only", action="store_true")
    mode.add_argument("--execute-freeze", action="store_true")
    args = parser.parse_args()
    root = Path.cwd().resolve()
    require(not (root / "private/reports/m2bq/FINAL_REPORT_UK.md").exists(),
            "MilestoneFinalReportAlreadyWritten_StopRequired")
    if args.prepare_inputs_only:
        print(canonical(prepare_inputs(root)).decode("ascii"))
        return
    require(all((args.historical_root, args.pinned_root, args.output_dir, args.target_dir)),
            "ExactHistoricalPinnedOutputAndTargetArgumentsRequired")
    pinned, legacy = Path(args.pinned_root).resolve(), Path(args.historical_root).resolve()
    output, target = owned_path(root, args.output_dir, "evidence"), owned_path(root, args.target_dir, "target")
    require(output != target and not output.is_relative_to(target) and not target.is_relative_to(output),
            "SeparateOwnedEvidenceAndBuildTargets")
    if args.freeze_only:
        value = freeze(root, pinned, legacy, output, target)
        print(canonical({"milestone": "M2bq", "classification": value["classification"],
                         "freeze": file_binding(output / FREEZE), "newCompositeExecutionsBeforeFreeze": 0}).decode("ascii"))
    else:
        value = execute(root, pinned, legacy, output, target, bounded_json((output / FREEZE).read_bytes(), 4 * 1024 * 1024))
        compact = {key: item for key, item in value["actualPositiveCounters"].items() if key != "entryPswValues"}
        print(canonical({"milestone": "M2bq", "passed": value["passed"], "summary": file_binding(output / "summary.json"),
                         "actualPositiveCounters": compact,
                         "actualSmokeCounters": value["actualSmokeCounters"],
                         "actualNegativeCounters": value["actualNegativeCounters"]}).decode("ascii"))


if __name__ == "__main__":
    main()
