"""M2br private draft: freeze independent expectations BEFORE build/new Cpu.

Only the explicit execute-freeze mode starts owned host children. Full actual
wire records are compared first, then retained losslessly with supplementary
typed BQ windows. Actual old BQ observations are a SEPARATE regression input,
never a source of the new expected states or effects. No execution on import.
"""

import argparse
from copy import deepcopy
from pathlib import Path
import sys
sys.dont_write_bytecode = True
from production_transfer_common import (
    BASE_BQ, BASE_BP, BASE_BO, COMPOSITE_SHA, binding, bounded_json, canonical,
    first_difference, reference_bindings, require,
)
from production_transfer_corpus import EXPECTED, ENTRY_TRANSFORMATION, iter_cases, seed_digests, smoke_cases
from production_transfer_emission import emitted_program, program_claims
from production_transfer_oracle import SCHEMA as ORACLE_SCHEMA, cpu_full_psw, expected_case
from production_transfer_projection import (
    SCHEMA as PROJECTION_SCHEMA, compare_m2bq_window, restore, wire_from_canonical,
)
from production_transfer_topology import SCHEMA as TOPOLOGY_SCHEMA, source_bindings as topology_bindings
from production_transfer_stream import (
    CanonicalWriter, Harness, ROW_LIMIT, STREAM_LIMIT, canonical_row, compare_full_stream,
    file_binding, native_build, read_rows, write_new,
)
import production_transfer_records as records
import production_transfer_negative as negative
import production_transfer_boundary as boundary
import production_transfer_protocol_tests as protocol_tests

FREEZE = "pre-runtime-freeze.json"
EXPECTED_LOCK = "independent-expectation-lock.json"
STREAMS = ("admission", "positive", "negative")
FINAL_REPORT = "private/reports/m2br/FINAL_REPORT_UK.md"
EXECUTION = {"mode": "ClosedInventedCallerCompositeContinuation", "defaultOffFeature": "p28-word0196-audit",
    "oneProductionCpuPerCase": True, "oneProductionBusPerCase": True, "oneDataInitializationPerCase": True,
    "initialCpuPc": 0x0FF0, "inputEntryPcUnchanged": 0x1000, "maximumRetirements": 18,
    "maximumCompositeRetirements": 16, "actualDirectJEdges": 2, "opaqueSingleUseTicketsRequired": True,
    "hostPcAssignmentAtBoundaryAllowed": False, "hostCpuReplacementAllowed": False,
    "reseedAllowed": False, "counterResetAllowed": False, "pendingFunctionalAccessAllowed": False,
    "stageScopedPermissionsRequired": True, "continuationCheckpointBeforeNextFetch": True,
    "oldCompositeApiStillSealsAtJ": True, "partialFaultEffectsRetained": True, "faultAtomicityClaimed": False,
    "physicalTimingClaimed": False, "physicalSfMeaningEstablished": False,
    "originalRomExecutionAllowed": False, "firmwareReady": False}


def runtime_protocol(root):
    return {"compiledHeaderPaths": list(records.HEADER_PATHS), "closedInputs": binding(root, records.INPUT_NAME),
            "oracle": ORACLE_SCHEMA, "losslessProjection": PROJECTION_SCHEMA,
            "programTopology": TOPOLOGY_SCHEMA, "negativeProtocol": negative.SCHEMA,
            "executableBoundary": boundary.SCHEMA, "initialCpuContext": ENTRY_TRANSFORMATION,
            "pureHostProtocolTests": list(protocol_tests.TEST_NAMES),
            "meaningfulComparatorMutations": list(negative.COMPARATOR_MUTATIONS),
            "canonicalRecords": {"admission": 32, "positiveIncludingFourSmokes": 5478, "negativeIncludingHeader": 62},
            "framing": "EveryIndependentRawAndProjectedRecordMeasuredBeforeBuild_Finite16MiBCap_Stream8GiB",
            "authorityOrder": ["IndependentTransferExpectedLock_NoPeerRuntimeInput",
                               "HistoricalCompatibilityReferenceFreeze_WithHonestBaselineCpuCounts",
                               "FinalTransferFreeze_BindsImmutableLockAndPeerFreeze_NoExpectedRegeneration",
                               "ActiveCompatibilityExecution", "NewTransferExecution"],
            "actualOldBqRecordUsedAsExpectation": False}


def contract_requirements(root):
    """Pure materializer input AFTER protected-Before release, not a verdict."""
    return {"milestone": "M2br", "exactBase": BASE_BQ, "exactM2bp": BASE_BP, "exactM2bo": BASE_BO,
            "classification": "ResearchOnlySpecification_NotRuntimeOrAcceptanceAuthority",
            "programs": program_claims(), "execution": deepcopy(EXECUTION),
            "runtimeProtocol": runtime_protocol(root), "coverageRequirementsNotActualResults": deepcopy(EXPECTED),
            "sourceManifestsOrHistoricalPinsMayBeRewritten": False, "jsonMayPromoteEvidenceStatus": False,
            "originalRomExecutionsAllowed": 0, "persistentFullProgramPayloadAllowed": False,
            "ephemeralInMemoryStdinSerializationAllowed": True, "firmwareReady": False}


def source_state(root, bq, bp, bo):
    import production_transfer_analysis as analysis
    proof, contract = analysis.source_checks(root, bq, bp, bo)
    require(proof["passed"] is True and proof["sourceRoleSelectionDeclaredBeforeRuntime"] is True,
            "ReviewedFourVersionCommittedAndPhysicalSourceRoles")
    for key, value in contract_requirements(root).items():
        require(first_difference(value, contract[key]) is None, "ExactPredeclaredTransferContract:" + key)
    return {"sourceProof": proof, "runtimeContract": binding(root, "research/p28-word0196/production_transfer_contract.json"),
            "immutableReferences": reference_bindings(root), "topologySources": topology_bindings(root),
            "compiledSources": [binding(root, path) for path in records.HEADER_PATHS],
            "closedInventedInputs": binding(root, records.INPUT_NAME)}


def owned_path(root, value, role):
    root = Path(root).resolve()
    lexical = Path(value)
    if not lexical.is_absolute():
        lexical = root / lexical
    path = lexical.resolve()
    require(path.is_relative_to(root) and ".." not in lexical.parts and path == lexical.absolute(), "ClosedUnlinkedOwnedPath")
    name = path.relative_to(root).as_posix()
    required = ".tmp/m2br-owned/public-evidence/transfer" if role == "evidence" else ".tmp/m2br-owned/runtime-target/transfer"
    require(role in ("evidence", "target") and (name == required or name.startswith(required + "/")), "ExactTransferRoleRoot")
    ownership = root / "private/reports/m2br/OWNED_OUTPUT_PATHS.json"
    if ownership.exists():
        manifest = bounded_json(ownership.read_bytes())
        require(manifest["milestone"] == "M2br" and manifest["exactBase"] == BASE_BQ
                and manifest["repositoryTemporaryRoots"] == [".tmp/m2br-owned"]
                and manifest["oldOwnedRootsReclassified"] is False, "ImmutableLocalOwnershipManifest")
    return path


def peer_path(root, value, filename):
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    require(path.resolve() == path.absolute() and path.is_relative_to(root)
            and path.relative_to(root).as_posix() == ".tmp/m2br-owned/public-evidence/compatibility/composite/" + filename,
            "ExactActualM2bqPeerRole:" + filename)
    return path


def _relative(root, path):
    return Path(path).relative_to(root).as_posix()


def _bound(root, path):
    return binding(root, _relative(root, path))


def _verify(root, row):
    require(type(row) is dict and set(row) == {"path", "bytes", "sha256"}
            and binding(root, row["path"]) == row, "ExactCurrentBoundEvidence")
    return root / row["path"]


def positive_expectations(root):
    yield records.header(root)
    yield records.program_admission()
    yield records.psw_sweep()
    for index, request in enumerate(smoke_cases(root), 1):
        row = expected_case(root, request)
        row["kind"], row["smoke_index"] = "transfer_smoke_observation", index
        yield row
    for request in iter_cases(root):
        yield expected_case(root, request)
    yield records.expected_summary(58)


def negative_expectations(root):
    yield records.header(root)
    yield from boundary.expected_records(root)
    yield from negative.expected_negative_records(root)


def admission_expectations(root):
    yield records.header(root)
    yield records.program_admission()
    yield records.psw_sweep()
    yield from boundary.expected_records(root)
    generator = negative.expected_negative_records(root)
    try:
        for row in generator:
            if row["kind"] != "transfer_negative_admission":
                break
            yield row
    finally:
        generator.close()


def _failure(output, phase, failure, extra=None):
    path = output / "FIRST_FAILURE.json"
    if not path.exists():
        write_new(path, {"classification": "FirstActualAttemptFailure_NoAcceptanceOrRetry", "phase": phase,
                        "error": repr(failure), "acceptance": False, "automaticRetry": False, **(extra or {})})


def lock_independent_expected(root, bq, bp, bo, output, target, peers):
    require(not output.exists(), "FreshTransferFreezeOutputRequired_NoOverwriteOrRetry")
    output.mkdir(parents=True)
    writers, receipts, maximum_raw = {}, {}, 0
    try:
        before = source_state(root, bq, bp, bo)
        values = bounded_json((root / records.INPUT_NAME).read_bytes(), 32 * 1024 * 1024)
        require(type(values) is list and len(values) == 5470, "ImmutableOriginal5470InputFile")
        independent_inputs = iter_cases(root)
        try:
            for actual_input in values:
                independently_original = next(independent_inputs)
                require(first_difference(independently_original, actual_input) is None, "EveryCompiledOriginalInputFieldUnchanged")
            _eof(independent_inputs, "ExtraIndependentInputOutsideSealed5470")
        finally:
            independent_inputs.close()
        for name, producer in (("positive", positive_expectations), ("negative", negative_expectations), ("admission", admission_expectations)):
            writer = CanonicalWriter(root, output / ("expected-" + name + ".jsonl.gz"))
            writers[name] = writer
            for row in producer(root):
                maximum_raw = max(maximum_raw, len(canonical(row)) + 1)
                require(maximum_raw <= ROW_LIMIT, "IndependentRawExpectedRecordWithinFiniteHardCap")
                writer.put(row)
            receipts[name] = writer.close()
        require([receipts[name]["records"] for name in STREAMS] == [32, 5478, 62], "IndependentClosedCanonicalInventories")
        _, control, mutations = negative.comparator_control(root)
        control_identity = [control["case_id"], control["internal_sf"]]
        _, emission = emitted_program(root)
        require(first_difference(before, source_state(root, bq, bp, bo)) is None, "FullSourceGraphStableAcrossIndependentFreeze")
        frozen = {"classification": "IndependentTransferExpectedAuthorityLockedBeforeHistoricalReferenceAndNewTransferCpu", "milestone": "M2br",
                  "sourceState": before, "programIdentity": emission, "inputIdentity": seed_digests(root),
                  "expectedStreams": receipts, "expectedPaths": {name: _relative(root, output / ("expected-" + name + ".jsonl.gz")) for name in STREAMS},
                  "canonicalLanes": {name: {"records": row["records"], "bytes": row["decompressedBytes"],
                      "sha256": row["sha256"], "maxRowBytes": row["maximumRowBytes"],
                      "expectedCompressed": _bound(root, output / ("expected-" + name + ".jsonl.gz"))}
                      for name, row in receipts.items()},
                  "maximumRawObservationBytes": maximum_raw,
                  "maximumProjectedRecordBytes": max(row["maximumRowBytes"] for row in receipts.values()),
                  "finiteRawHardCap": ROW_LIMIT, "finiteStreamCap": STREAM_LIMIT,
                  "comparatorControl": {"caseKey": control_identity, "mutations": mutations},
                  "peerFuturePaths": {key: _relative(root, path) for key, path in peers.items()},
                  "targetRole": _relative(root, target), "newTransferExecutionsBeforeFreeze": 0,
                  "newTargetCpuInstancesBeforeFreeze": 0, "newHarnessBuildsBeforeFreeze": 0,
                  "newCpuExecutionsBeforeThisFreeze": 0, "newCpuExecutionScope": "ActiveM2brTransferOnly",
                  "peerRuntimeOutputUsedToDefineExpected": False,
                  "historicalCpuChronology": "NotStartedByThisPureDriver_ActualCompatibilityNativeReceiptsMustBindThisPriorLock",
                  "allExpectedArchitecturalAndJournalFieldsFrozen": True, "firmwareReady": False}
        write_new(output / EXPECTED_LOCK, frozen)
        return {"passed": True, "mode": "lock-independent-expected", "expectationLock": _bound(root, output / EXPECTED_LOCK),
                "newTargetCpuInstances": 0, "builds": 0}
    except BaseException as failure:
        cleanup = []
        for writer in writers.values():
            try:
                writer.close()
            except BaseException as error:
                cleanup.append("PartialExpectedClose:" + repr(error))
        _failure(output, "independent-freeze-before-build", failure, {"cleanupDiagnostics": cleanup})
        raise


def freeze(root, bq, bp, bo, output, target, peers):
    """Finalize an already locked authority; no expected stream is regenerated."""
    require((output / EXPECTED_LOCK).is_file() and not (output / FREEZE).exists()
            and not (output / "FIRST_FAILURE.json").exists(), "ExistingImmutableExpectedAuthorityLockRequired")
    try:
        lock_binding = _bound(root, output / EXPECTED_LOCK)
        locked = bounded_json((output / EXPECTED_LOCK).read_bytes(), 16 * 1024 * 1024)
        state = source_state(root, bq, bp, bo)
        require(first_difference(locked["sourceState"], state) is None
                and locked["targetRole"] == _relative(root, target)
                and locked["peerFuturePaths"] == {key: _relative(root, value) for key, value in peers.items()}
                and locked["peerRuntimeOutputUsedToDefineExpected"] is False,
                "IndependentAuthorityAndEveryExpectedInputStillOriginal")
        for name in STREAMS:
            require(file_binding(root / locked["expectedPaths"][name]) == locked["expectedStreams"][name]["compressed"],
                    "ImmutableExpectedStreamBeforeFinalFreeze:" + name)
        peer_binding = _bound(root, peers["freeze"])
        peer = bounded_json(peers["freeze"].read_bytes(), 16 * 1024 * 1024)
        require(first_difference(peer["sourceState"]["sourceProof"], state["sourceProof"]) is None,
                "HistoricalCompatibilityFreezeHasSameCompleteNewSourceGraph")
        historical = peer["historicalReferenceExecution"]
        require(historical["scope"] == "PinnedM2bqDefaultProbeMicroAndCapabilitiesOnly_ProtocolConstructionsNotExposed"
                and (historical["probeCpuInstances"], historical["probeBusInstances"], historical["probePositiveExecutions"],
                     historical["probeCapabilityAttempts"], historical["protocolProcesses"]) == (470, 470, 468, 2, 22)
                and historical["protocolCpuConstructionCount"] is None and historical["protocolBusConstructionCount"] is None
                and historical["protocolConstructionCountStatus"] == "NotExposedByLegacyProtocol",
                "HonestSeparatelyCountedHistoricalReferenceExecution_NotGlobalCpuZero")
        frozen = {**locked, "classification": "FormalTransferExecutionFreeze_BindsPriorIndependentAuthorityAndHistoricalCompatibilityFreeze",
                  "independentExpectationLock": lock_binding, "peerFreeze": peer_binding,
                  "historicalReferenceExecution": deepcopy(historical),
                  "expectedStreamsRegeneratedDuringFinalization": False,
                  "historicalReferenceCpuMayHaveRunBeforeThisFinalFreeze": True,
                  "historicalReferenceCpuCountsAuthority": "ActualCompatibilityFreezeNativeReceipts_NotGlobalZeroClaim"}
        require(lock_binding == _bound(root, output / EXPECTED_LOCK), "PriorIndependentAuthorityUnchangedDuringFinalization")
        write_new(output / FREEZE, frozen)
        return {"passed": True, "mode": "freeze-only", "freeze": _bound(root, output / FREEZE),
                "independentExpectationLock": lock_binding, "newTargetCpuInstances": 0, "builds": 0}
    except BaseException as failure:
        _failure(output, "final-freeze-no-regeneration", failure)
        raise


def _restore_rows(root, path):
    rows = read_rows(path)
    try:
        for row in rows:
            yield restore(root, row)
    finally:
        rows.close()


def _peer_records(root, path):
    rows = _restore_rows(root, path)
    try:
        for row in rows:
            if row.get("kind") in ("composite_observation", "composite_smoke_observation"):
                yield row
    finally:
        rows.close()


def peer_actual_state(root, peers, state):
    frozen = bounded_json(peers["freeze"].read_bytes(), 16 * 1024 * 1024)
    summary = bounded_json(peers["summary"].read_bytes(), 16 * 1024 * 1024)
    require(summary["passed"] is True and summary["positiveCases"] == 5470 and summary["smokeCases"] == 4
            and summary["activePositiveCanonical"] == _bound(root, peers["canonical"])
            and summary["preRuntimeFreeze"] == _bound(root, peers["freeze"])
            and first_difference(summary["sourceState"]["sourceProof"], state["sourceProof"]) is None
            and first_difference(frozen["sourceState"]["sourceProof"], state["sourceProof"]) is None,
            "ActualCompleteM2bqPeerAndSameFourVersionSourceGraph")
    return {key: _bound(root, path) for key, path in peers.items()}


def _new_totals():
    return {"executions": 0, "cpuInstances": 0, "busInstances": 0, "dataInitializations": 0,
            "retirements": 0, "sharedExecutionCalls": 0, "sourceAccountingCycles": 0,
            "stageRetirements": {"Caller": 0, "Composite": 0, "Continuation": 0},
            "pathCounts": {path: 0 for path in "ABCD"}, "programCallbacks": 0, "refusedProgramEvents": 0,
            "logicalReads": 0, "logicalWrites": 0, "rawReads": 0, "rawWrites": 0,
            "diagnosticEvents": 0, "sameValueWrites": 0, "ticketsIssued": 0, "ticketsConsumed": 0,
            "ticketRefusals": 0, "checkpointCount": 0, "compositeDirectJCount": 0,
            "observedPsw": set(), "observedIncomingDd": set(), "observedInternalSf": set(), "casePairs": {}}


def _accumulate(totals, row):
    report, audit = row["report"], row["report"]["audit"]
    require(row["accepted"] is True and row["error"] is None and report["completed"] is True, "ActualCompleteThreeStageCase")
    totals["executions"] += 1
    totals["cpuInstances"] += row["cpu_instances"]
    totals["busInstances"] += row["bus_instances"]
    totals["dataInitializations"] += row["data_initializations"]
    totals["retirements"] += audit["successful_retirements"]
    totals["sharedExecutionCalls"] += audit["shared_execution_calls"]
    totals["sourceAccountingCycles"] += report["current"]["cpu"]["cycles"]
    totals["pathCounts"][report["path"]] += 1
    for step in report["steps"]:
        totals["stageRetirements"][step["stage"]] += int(step["outcome"]["retired"])
    totals["programCallbacks"] += len(audit["program_events"])
    totals["refusedProgramEvents"] += sum(not event["serviced"] for event in audit["program_events"])
    totals["diagnosticEvents"] += len(audit["diagnostic_events"])
    for event in audit["data_events"]:
        if event["phase"] == "Functional" and event["serviced"]:
            totals["logicalReads" if event["operation"] == "Read" else "logicalWrites"] += 1
            totals["sameValueWrites"] += int(event["operation"] == "Write" and event["same_value"] is True)
    for event in audit["raw_data_events"]:
        if audit["data_events"][event["logical_ordinal"]]["phase"] == "Functional" and event["serviced"]:
            totals["rawReads" if event["operation"] == "Read" else "rawWrites"] += 1
    totals["ticketsIssued"] += report["tickets_issued"]
    totals["ticketsConsumed"] += report["tickets_consumed"]
    totals["ticketRefusals"] += report["tickets_refused"]
    totals["checkpointCount"] += int(report["checkpoint"] is not None)
    totals["compositeDirectJCount"] += report["composite_direct_j_count"]
    totals["observedPsw"].add(cpu_full_psw(report["entry"]["cpu"]))
    totals["observedIncomingDd"].add(report["entry"]["cpu"]["dd"])
    totals["observedInternalSf"].add(row["internal_sf"])
    totals["casePairs"].setdefault(row["case_id"], set()).add(row["internal_sf"])


def _finish_totals(totals, smoke=False):
    observed = dict(totals)
    observed["observedPsw"] = sorted(observed["observedPsw"])
    observed["observedIncomingDd"] = sorted(observed["observedIncomingDd"])
    observed["observedInternalSf"] = sorted(observed["observedInternalSf"])
    pairs = observed.pop("casePairs")
    observed["internalSfPairs"] = sum(values == {False, True} for values in pairs.values())
    expected = (4, 62, 328, 1870, 36, 14, 40, 14, 8, 8) if smoke else (5470, 84724, 448100, 2551820, 49112, 19162, 54582, 19162, 10940, 10940)
    require(tuple(observed[key] for key in ("executions", "retirements", "sourceAccountingCycles", "programCallbacks",
            "logicalReads", "logicalWrites", "rawReads", "rawWrites", "ticketsIssued", "ticketsConsumed")) == expected,
            "ActualSmokeOrMainTotalsMustMatchIndependentFrozenRequirements")
    require(observed["refusedProgramEvents"] == observed["ticketRefusals"] == 0
            and observed["cpuInstances"] == observed["busInstances"] == observed["dataInitializations"] == observed["executions"],
            "OneActualCpuBusAndInitialization_NoPositiveRefusal")
    if not smoke:
        require(observed["pathCounts"] == EXPECTED["pathCounts"] and len(observed["observedPsw"]) == 2048
                and observed["internalSfPairs"] == 2735 and observed["observedIncomingDd"] == [False, True]
                and observed["observedInternalSf"] == [False, True], "ActualSealed5470Coverage")
        require(observed["stageRetirements"] == {"Caller": 5470, "Composite": 73784, "Continuation": 5470}
                and observed["diagnosticEvents"] == 191328, "ActualGlobalStagesAndAllDiagnosticSnapshots")
    else:
        require(observed["pathCounts"] == dict.fromkeys("ABCD", 1)
                and observed["stageRetirements"] == {"Caller": 4, "Composite": 54, "Continuation": 4}
                and observed["diagnosticEvents"] == 140, "FourSeparateActualSmokeStages")
    return observed


def _eof(iterator, reason):
    try:
        next(iterator)
    except StopIteration:
        return
    raise ValueError(reason)


def _stage_failure(difference, expected):
    path = difference["field"]
    if ".steps[" in path and expected.get("report"):
        tail = path.split(".steps[", 1)[1]
        index = int(tail.split("]", 1)[0])
        if index < len(expected["report"]["steps"]):
            return expected["report"]["steps"][index]["stage"]
    if ".tickets[0]" in path or ".commits[0]" in path:
        return "Caller"
    if ".tickets[1]" in path or ".commits[1]" in path:
        return "Composite"
    return "ContinuationOrRecordEnvelope"


def execute(root, bq, bp, bo, output, target, peers):
    require((output / FREEZE).is_file() and not (output / "summary.json").exists()
            and not (output / "FIRST_FAILURE.json").exists()
            and not (output / "build.start.json").exists() and not (output / "runtime.start.json").exists(),
            "ExactlyOneActualExecutionAttemptFromExistingImmutableFreeze")
    frozen_binding = _bound(root, output / FREEZE)
    frozen = bounded_json((output / FREEZE).read_bytes(), 16 * 1024 * 1024)
    writers, readers, child, peer_rows = {}, {}, None, None
    partial_receipts, mutation_receipt = {}, None
    totals, smokes = _new_totals(), _new_totals()
    mismatch, last_actual = None, None
    try:
        state = source_state(root, bq, bp, bo)
        require(first_difference(frozen["sourceState"], state) is None
                and frozen["newTargetCpuInstancesBeforeFreeze"] == frozen["newHarnessBuildsBeforeFreeze"] == 0
                and frozen["targetRole"] == _relative(root, target)
                and frozen["peerFuturePaths"] == {key: _relative(root, value) for key, value in peers.items()},
                "CompleteFormalSourceInputAndRoleFreezeStillExactBeforeBuild")
        _verify(root, frozen["independentExpectationLock"])
        require(frozen["expectedStreamsRegeneratedDuringFinalization"] is False
                and frozen["peerRuntimeOutputUsedToDefineExpected"] is False, "AcyclicIndependentExpectedAuthority")
        require(frozen["peerFreeze"] == _bound(root, peers["freeze"]), "ImmutablePeerFreezeStillExact")
        peer_before = peer_actual_state(root, peers, state)
        expected_paths = {name: root / frozen["expectedPaths"][name] for name in STREAMS}
        for name, path in expected_paths.items():
            require(file_binding(path) == frozen["expectedStreams"][name]["compressed"], "ImmutableIndependentExpectedStream:" + name)
            readers[name] = _restore_rows(root, path)
        pure = protocol_tests.run(root)
        write_new(output / "pure-protocol-tests.json", pure)
        require(first_difference(state, source_state(root, bq, bp, bo)) is None, "SourcesStableAfterActualPureControls")
        binary, build = native_build(root, target, output)
        binary_binding = file_binding(binary)
        for name in STREAMS:
            writers[name] = CanonicalWriter(root, output / (name + "-canonical.jsonl.gz"))
        child = Harness([str(binary)], root, output, row_limit=frozen["maximumRawObservationBytes"])

        def accept(name, actual):
            nonlocal mismatch, last_actual
            # Keep the complete bounded parsed stdout wire before any expected
            # row lookup, comparison, or supplemental projection can fail. This
            # never captures the ephemeral PROGRAM command sent on stdin.
            last_actual = {"stream": name, "actualWire": actual,
                           "source": "ParsedBoundedActualStdout_NotStdinOrProgramCommand"}
            try:
                frozen_row = next(readers[name])
            except StopIteration as failure:
                raise ValueError("UnexpectedExtraActualRecord:" + name) from failure
            expected = wire_from_canonical(frozen_row)
            difference = first_difference(expected, actual)
            # Strict full-wire comparison happens BEFORE deriving the typed
            # supplementary window. A failing complete partial report is still
            # retained, and can never obtain an accepted comparison receipt.
            writers[name].put(actual)
            if difference is not None:
                mismatch = {"stream": name, "stage": _stage_failure(difference, expected), "difference": difference}
                raise ValueError("FullActualWireMismatch:" + name + ":" + difference["field"])
            return expected

        actual_header = child.receive()
        accept("positive", actual_header)
        accept("negative", actual_header)
        accept("admission", actual_header)
        boundary_receipts = []
        for actual, receipt in boundary.observe(binary, root, output):
            accept("negative", actual)
            # Admission scope duplicates the SAME actual no-Cpu observation;
            # it never starts another child or increments execution counters.
            # Its declared order is header, program, PSW, then these boundaries,
            # so retain bounded pending rows until those two actual admissions.
            boundary_receipts.append((actual, receipt))
        program, emission = emitted_program(root)
        require(first_difference(frozen["programIdentity"], emission) is None, "ActualEmitterAndTinyProfilesStillFrozen")
        child.send(program)
        del program
        admission = child.receive()
        accept("positive", admission)
        accept("admission", admission)
        child.send({"kind": "psw_sweep"})
        psw = child.receive()
        accept("positive", psw)
        accept("admission", psw)
        for actual, _ in boundary_receipts:
            accept("admission", actual)
        peer_rows = _peer_records(root, peers["canonical"])
        regressions, main_regressions, smoke_regressions = 0, 0, 0

        def compare_peer(actual):
            nonlocal regressions, main_regressions, smoke_regressions, mismatch
            try:
                old_actual = next(peer_rows)
            except StopIteration as failure:
                raise ValueError("ActualM2bqPeerEndedBeforeTransferCorpus") from failure
            _, difference = compare_m2bq_window(actual, old_actual)
            if difference is not None:
                mismatch = {"stream": "actual-m2bq-regression", "stage": "Composite", "difference": difference}
                raise ValueError("FullActualM2bqStageRelativeWindowMismatch:" + difference["field"])
            regressions += 1
            if actual["kind"] == "transfer_smoke_observation":
                smoke_regressions += 1
            else:
                main_regressions += 1

        for request in smoke_cases(root):
            child.send({"kind": "smoke", "input": request})
            actual = child.receive()
            accept("positive", actual)
            compare_peer(actual)
            _accumulate(smokes, actual)
        iterator = iter_cases(root)
        try:
            for request in iterator:
                child.send(request)
                actual = child.receive()
                expected = accept("positive", actual)
                compare_peer(actual)
                _accumulate(totals, actual)
                if [actual["case_id"], actual["internal_sf"]] == frozen["comparatorControl"]["caseKey"]:
                    require(mutation_receipt is None, "ExactlyOneFrozenComparatorSpecimen")
                    observed = []
                    for identity, changed in negative.comparator_mutations(actual):
                        difference = first_difference(expected, changed)
                        require(difference is not None, "ActualComparatorMutationWasNotRejected:" + identity)
                        observed.append({"id": identity, "refused": True, "firstMismatchPath": difference["field"]})
                    require([row["id"] for row in observed] == frozen["comparatorControl"]["mutations"], "ExactFrozen32MeaningfulMutations")
                    mutation_receipt = {"passed": True, "classification": "ActualFullWireComparatorMutations_NoExtraCpu",
                                        "caseKey": frozen["comparatorControl"]["caseKey"], "mutations": observed,
                                        "count": len(observed), "extraCpuInstances": 0}
                    write_new(output / "comparator-controls.json", mutation_receipt)
        finally:
            iterator.close()
        child.send({"kind": "capabilities"})
        for _ in range(58):
            actual = child.receive()
            accept("negative", actual)
            if actual.get("kind") == "transfer_negative_admission":
                accept("admission", actual)
        child.send({"kind": "finish"})
        accept("positive", child.receive())
        runtime = child.finish()
        require(mutation_receipt is not None, "ActualFrozenComparatorControlWasObserved")
        for name, reader in readers.items():
            _eof(reader, "FrozenExpectedRecordsRemainAfterActualFinish:" + name)
        _eof(peer_rows, "ActualM2bqPeerHasExtraCompositeObservation")
        require((regressions, main_regressions, smoke_regressions) == (5474, 5470, 4), "CompleteSeparateActualM2bqRegression")
        actual_streams = {name: writers[name].close() for name in STREAMS}
        negative_rows = _restore_rows(root, output / "negative-canonical.jsonl.gz")
        try:
            caps = (row for row in negative_rows if row.get("kind") in ("transfer_negative_admission", "transfer_negative_runtime"))
            # This finite32-session scope is read one complete row at a time;
            # the full5470 corpus is never retained in memory.
            negative_summary = negative.summarize_actual_negative_records(caps)
        finally:
            negative_rows.close()
        comparisons = {name: compare_full_stream(expected_paths[name], output / (name + "-canonical.jsonl.gz")) for name in STREAMS}
        for name, path in expected_paths.items():
            require(file_binding(path) == frozen["expectedStreams"][name]["compressed"], "ExpectedStreamsUnchangedAfterActualFullComparison")
        require(peer_before == peer_actual_state(root, peers, state), "ActualM2bqPeerSourcesAndFullCanonicalUnchangedAcrossRegression")
        require(frozen_binding == _bound(root, output / FREEZE) and file_binding(binary) == binary_binding
                and first_difference(state, source_state(root, bq, bp, bo)) is None,
                "AllRuntimeSourceBinaryInputAndFreezeIdentitiesStillExact")
        main_totals, smoke_totals = _finish_totals(totals), _finish_totals(smokes, True)
        summary = {"milestone": "M2br", "passed": True, "classification": "ActualBoundedInventedHandoff_ResearchOnly",
                   "sourceState": state, "preRuntimeFreeze": frozen_binding, "streams": actual_streams,
                   "canonicalBindings": {name: _bound(root, output / (name + "-canonical.jsonl.gz")) for name in STREAMS},
                   "wholeStreamComparisons": comparisons, "positive": main_totals, "smoke": smoke_totals,
                   "negative": negative_summary, "executableBoundaryControls": [receipt for _, receipt in boundary_receipts],
                   "admissionScope": {"canonicalRecords": 32, "sharedObservationsNotNewExecutions": True,
                                      "refusedConstructorCpuValuesAlreadyCountedInNegative": 6, "extraCpuInstances": 0},
                   "actualM2bqRegression": {"passed": True, "peerEvidence": peer_before, "records": regressions,
                                             "positiveCases": main_regressions, "smokeCases": smoke_regressions,
                                             "role": "ActualOldObservationRegression_NotIndependentExpectationSource"},
                   "pureProtocolTests": _bound(root, output / "pure-protocol-tests.json"),
                   "comparatorControls": _bound(root, output / "comparator-controls.json"),
                   "actualBinary": binary_binding, "build": build, "runtime": runtime,
                   "firstMismatch": None, "firstMismatchByStage": {"Caller": None, "Composite": None, "Continuation": None},
                   "originalRomExecutions": 0, "nativeDownstreamExecution": False, "persistentTargetBinaryPayloads": 0,
                   "firmwareReady": False, "automaticRetries": 0}
        write_new(output / "summary.json", summary)
        return {"passed": True, "mode": "execute-freeze", "summary": _bound(root, output / "summary.json"),
                "positiveCases": main_totals["executions"], "retirements": main_totals["retirements"]}
    except BaseException as failure:
        cleanup = []
        if child is not None:
            try:
                child.abort()
            except BaseException as error:
                cleanup.append("OwnedChildCleanup:" + repr(error))
        for name, writer in writers.items():
            try:
                partial_receipts[name] = writer.close()
            except BaseException as error:
                cleanup.append("PartialCanonicalClose:" + name + ":" + repr(error))
        _failure(output, "actual-build-or-transfer", failure,
                 {"firstMismatch": mismatch, "partialCanonicalStreams": partial_receipts,
                  "cleanupDiagnostics": cleanup, "completedPositiveCases": totals["executions"],
                  "lastBoundedActualWireBeforeFailure": last_actual})
        raise
    finally:
        for reader in list(readers.values()) + ([peer_rows] if peer_rows is not None else []):
            reader.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-root", required=True)
    parser.add_argument("--pinned-bp-root", required=True)
    parser.add_argument("--pinned-bq-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--target-dir", required=True)
    parser.add_argument("--m2bq-canonical", required=True)
    parser.add_argument("--m2bq-summary", required=True)
    parser.add_argument("--m2bq-freeze", required=True)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--lock-independent-expected", action="store_true")
    modes.add_argument("--freeze-only", action="store_true")
    modes.add_argument("--execute-freeze", action="store_true")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    require(not (root / FINAL_REPORT).exists(), "StopAfterFinalReport_NoFurtherMilestoneWork")
    bq, bp, bo = (Path(value).resolve() for value in (arguments.pinned_bq_root, arguments.pinned_bp_root, arguments.historical_root))
    output, target = owned_path(root, arguments.output_dir, "evidence"), owned_path(root, arguments.target_dir, "target")
    peers = {"canonical": peer_path(root, arguments.m2bq_canonical, "active-positive-canonical.jsonl.gz"),
             "summary": peer_path(root, arguments.m2bq_summary, "summary.json"),
             "freeze": peer_path(root, arguments.m2bq_freeze, FREEZE)}
    if arguments.lock_independent_expected:
        result = lock_independent_expected(root, bq, bp, bo, output, target, peers)
    elif arguments.freeze_only:
        result = freeze(root, bq, bp, bo, output, target, peers)
    else:
        result = execute(root, bq, bp, bo, output, target, peers)
    print(canonical(result).decode("ascii"))


if __name__ == "__main__":
    try:
        main()
    except Exception as failure:
        print("M2BR_TRANSFER_FAILURE=" + str(failure), file=sys.stderr)
        raise SystemExit(1)
