"""M2br private draft: lossless absolute observations and typed BQ window.

Absolute evidence is never replaced by a relative view. The historical window
is supplementary and narrowly translates the declared caller prefix. Seed PC,
new lifecycle/tickets/extra diagnostics stay in the full absolute report; they
are not silently relabelled as historical M2bq observations.
"""

from copy import deepcopy
from production_transfer_common import bq_modules, canonical, first_difference, require

SCHEMA = {"codec": "M2bqLosslessJsonAndRamSparseA5V1",
          "absoluteObservationRetainedInFull": True, "excludedFields": [], "platformExclusions": [],
          "supplementaryWindow": "M2brExplicitCallerPrefixToM2bqWindowV1",
          "callerPrefix": {"cycles": 7, "instructions": 1, "programEvents": 7},
          "dataDecodedPatternIndicesAreNotStepOrdinals": True,
          "seedPcDifference": {"historical": 0x1000, "transfer": 0x0FF0,
                               "scope": "OutsideCompositeFunctionalWindow_AbsoluteSeedEvidenceRetained"},
          "newLifecycleOrExtraDiagnosticEventsDropped": False}


def project(root, actual):
    with bq_modules(root) as modules:
        codec = modules["production_composite_projection"]
        projected = codec.project(actual)
        require(first_difference(actual, codec.restore(projected)) is None, "CompleteTransferObservationRoundTrip")
        return projected


def restore(root, projected):
    with bq_modules(root) as modules:
        return modules["production_composite_projection"].restore(projected)


def canonical_row(root, actual):
    return canonical(project(root, canonical_observation(actual))) + b"\n"


def canonical_observation(actual):
    if actual.get("kind") not in ("transfer_observation", "transfer_smoke_observation"):
        return actual
    report = actual["report"]
    if actual["accepted"] is True and report["completed"] is True:
        try:
            window = composite_window(report["steps"], report["audit"]["program_events"],
                                      report["audit"]["data_events"], report["audit"]["raw_data_events"])
        except ValueError as failure:
            # Retain the complete malformed/partial actual report, but never
            # turn this into a comparable or accepted regression observation.
            window = {"classification": "ActualWindowNotComparable", "reason": str(failure), "comparable": False}
    else:
        window = {"classification": "ActualPartialTransfer_NotComparable", "comparable": False,
                  "partialStepCount": len(report["steps"])}
    return {"kind": "transfer_canonical_observation", "actual_observation": actual,
            "m2bq_composite_window": window}


def wire_from_canonical(value):
    if value.get("kind") == "transfer_canonical_observation":
        require(set(value) == {"kind", "actual_observation", "m2bq_composite_window"}, "ClosedTransferCanonicalEnvelope")
        return value["actual_observation"]
    return value


def _relative_snapshot(snapshot):
    result = deepcopy(snapshot)
    cpu = result["cpu"]
    require(type(cpu["cycles"]) is int and cpu["cycles"] >= 7
            and type(cpu["instructions"]) is int and cpu["instructions"] >= 1, "ActualCallerPrefixPresent")
    cpu["cycles"] -= 7
    cpu["instructions"] -= 1
    return result


def composite_window(steps, program_events, logical_events, raw_events):
    """Closed shared fields only; entire containing report must ALSO compare.

    Accepts real TransferStepRecord objects, not host-patched Cpu state. Every
    old BQ step field is represented; new transfer fields remain in the absolute
    parent record and in explicit mapping evidence. DATA ``instruction_index``
    is a decoder identity and is deliberately not changed.
    """
    require(type(steps) is list and len(steps) >= 3 and steps[0]["stage"] == "Caller"
            and steps[-1]["stage"] == "Continuation", "ClosedThreeStageObservedOrder")
    middle = steps[1:-1]
    require(len(middle) in (11, 13, 14, 16) and all(row["stage"] == "Composite" for row in middle),
            "CompleteM2bqWindowRequired")
    result_steps, mapping = [], []
    for local_index, row in enumerate(middle, 1):
        require(row["index"] == local_index + 1 and row["stage_index"] == local_index,
                "ActualGlobalAndStageIndicesAgree")
        require(row["stage_relative_instructions"] == row["after"]["cpu"]["instructions"] - 1
                and row["stage_relative_cycles"] == row["after"]["cpu"]["cycles"] - 7,
                "ReportedRelativeCountersMustDeriveFromAbsolute")
        start, end = row["program_span"]
        require(start >= 7 and end > start, "CompositeProgramSpanAfterCaller")
        result_steps.append({"index": local_index, "node_identity": row["node_identity"], "form": row["form"],
                             "before": _relative_snapshot(row["before"]),
                             "after": _relative_snapshot(row["after"]), "outcome": deepcopy(row["outcome"]),
                             "program_span": [start - 7, end - 7],
                             "logical_span": deepcopy(row["logical_span"]), "raw_span": deepcopy(row["raw_span"])})
        mapping.append({"absolute_instruction": row["index"], "stage_instruction": local_index,
                        "absolute_program_span": [start, end], "relative_program_span": [start - 7, end - 7],
                        "absolute_cycles_before": row["before"]["cpu"]["cycles"],
                        "absolute_cycles_after": row["after"]["cpu"]["cycles"],
                        "relative_cycles_before": row["before"]["cpu"]["cycles"] - 7,
                        "relative_cycles_after": row["after"]["cpu"]["cycles"] - 7})
    program_begin, program_end = middle[0]["program_span"][0], middle[-1]["program_span"][1]
    require(program_begin == 7, "ExactlySevenRealCallerProgramCallbacks")
    relative_program = deepcopy(program_events[program_begin:program_end])
    for local_ordinal, event in enumerate(relative_program):
        require(event["ordinal"] == local_ordinal + 7, "TrueGlobalProgramOrdinal")
        event["ordinal"] -= 7
    logical_begin, logical_end = middle[0]["logical_span"][0], middle[-1]["logical_span"][1]
    raw_begin, raw_end = middle[0]["raw_span"][0], middle[-1]["raw_span"][1]
    require((logical_begin, raw_begin) == (48, 80), "NoCallerFunctionalDataAccessOrReseed")
    actual_j_count = sum(row["outcome"]["mnemonic"] == "J addr16" for row in middle)
    require(actual_j_count == 1 and middle[-1]["outcome"]["mnemonic"] == "J addr16",
            "ExactlyOneActualCompositeTerminalJInObservedWindow")
    shared = {"entry": _relative_snapshot(middle[0]["before"]),
              "terminal": _relative_snapshot(middle[-1]["after"]), "steps": result_steps,
              "program_events": relative_program,
              "functional_logical_events": deepcopy(logical_events[logical_begin:logical_end]),
              "functional_raw_events": deepcopy(raw_events[raw_begin:raw_end]),
              "direct_j_count": actual_j_count, "instruction_count": len(middle),
              "terminal_pc": middle[-1]["after"]["cpu"]["pc"]}
    return {"classification": "SupplementaryTypedComparison_NotReplacementForAbsoluteEvidence",
            "policy": deepcopy(SCHEMA), "mapping": mapping, "shared": shared}


def historical_window(record):
    """The actual old BQ positive record is a regression input, NOT an oracle."""
    require(record["kind"] in ("composite_observation", "composite_smoke_observation")
            and record["accepted"] is True and record["error"] is None, "CompleteActualHistoricalM2bqRecord")
    report = record["report"]
    require(report["mode"] == "ClosedM2bjComposite" and report["completed"] is True
            and report["direct_j_count"] == 1, "HistoricalM2bqClosedSuccessfulScope")
    audit = report["audit"]
    return {"entry": deepcopy(report["entry"]), "terminal": deepcopy(report["current"]),
            "steps": deepcopy(report["steps"]), "program_events": deepcopy(audit["program_events"]),
            "functional_logical_events": deepcopy(audit["data_events"][48:]),
            "functional_raw_events": deepcopy(audit["raw_data_events"][80:]),
            "direct_j_count": report["direct_j_count"], "instruction_count": len(report["steps"]),
            "terminal_pc": report["current"]["cpu"]["pc"]}


def compare_m2bq_window(transfer_record, actual_historical_record):
    require([transfer_record["case_id"], transfer_record["internal_sf"]]
            == [actual_historical_record["case_id"], actual_historical_record["internal_sf"]],
            "SameSealedCaseAndInternalSfForHistoricalRegression")
    report, audit = transfer_record["report"], transfer_record["report"]["audit"]
    view = composite_window(report["steps"], audit["program_events"], audit["data_events"], audit["raw_data_events"])
    return view, first_difference(historical_window(actual_historical_record), view["shared"],
                                  "$.m2bq_stage_relative_regression")
