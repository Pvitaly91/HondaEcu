"""M2bq independently frozen negative controls, never production execution.

Expected states/effects come from immutable reference prefixes. The separately
reviewed Bus/API protocol supplies refusal events, not ISA effects. Runtime
capabilities, admission-only controls, component-unit guards and comparator
mutations are explicitly different authorities. Nothing runs on import.
"""
from copy import deepcopy
from production_composite_common import COMPOSITE_SHA, require
from production_composite_corpus import iter_cases
from production_composite_oracle import expected_case, expected_execution_components, expected_permissions

PROGRAM_IDS = (
    "program-wrong-digest-label", "program-content-changed", "program-wrong-base",
    "program-wrong-end", "program-short-stream", "program-dd1-changed",
    "program-node-count", "program-node-form", "program-node-operand",
    "program-node-successor", "program-node-dd", "program-provenance",
)
SEED_IDS = ("seed-missing-byte", "seed-extra-byte", "seed-r-alias", "seed-er-alias")
CONSTRUCTOR_IDS = ("budget-zero", "budget-seventeen", "entry-wrong-pc", "entry-wrong-lrb")
SESSION_SPECS = (
    ("functional-read-outside-step", "D", 16, 0),
    ("functional-write-readonly-low", "D", 16, 0),
    ("functional-write-readonly-high", "D", 16, 0),
    ("functional-write-gate-B", "B", 16, 0),
    ("functional-write-gate-C", "C", 16, 0),
    ("functional-reseed", "D", 16, 0),
    ("functional-second-transition", "D", 16, 0),
    ("functional-legacy-step", "D", 16, 0),
    ("functional-program-probe", "D", 16, 0),
    ("budget-one-exhaustion", "D", 1, 1),
    ("terminal-seal-A", "A", 16, 11),
    ("terminal-seal-D", "D", 16, 16),
)
NEGATIVE_IDS = PROGRAM_IDS + SEED_IDS + ("psw-incompatible-admission",) + CONSTRUCTOR_IDS + tuple(
    row[0] for row in SESSION_SPECS)
METADATA_ONLY_IDS = ("program-wrong-digest-label", "program-provenance")
COMPONENT_TESTS = (
    "composite_closed_inventory_and_all_four_path_boundaries_are_exact",
    "composite_closed_node_refuses_mid_instruction_wrong_dd_and_wrong_path",
    "composite_closed_successor_requires_actual_j_and_prevents_second_j",
    "composite_seed_inventory_aliases_and_derived_paths_are_closed",
    "composite_opaque_non_emitter_payload_is_never_admitted",
    "composite_per_instruction_rights_refuse_index_form_path_width_and_direction",
    "composite_rmw_requires_current_instruction_read_not_prior_seed_or_failed_event",
    "composite_current_step_selection_never_reassociates_prior_program_events",
    "composite_budget_guard_faults_before_any_new_program_or_data_attempt",
    "composite_legacy_budget16_still_seals_after_one_retirement",
    "composite_retirement_continues_only_closed_successor_then_seals_actual_j",
    "composite_retirement_rejects_non_j_exit_or_wrong_external_authority",
    "composite_host_api_escape_refusals_are_sticky_and_never_service_data",
)
SCHEMA = {
    "version": 1, "runtimeNegativeRecords": 33, "metadataOnlyAdmissionRecords": 2,
    "closedSessionRecords": 12, "positive5470CasesChanged": 0,
    "separateNegativeCompletedRoutes": {"A": 1, "D": 1},
    "separateNegativeSuccessfulRetirements": 28,
    "negativeCpuInstances": 16, "negativeBusInstances": 12,
    "cpuCountMeaning": "ActualProductionCpuValueConstructions_IncludingFourRefusedBeforeBusConstructors",
    "busCountMeaning": "ActualProductionBusInstances_OnlyInsideAcceptedSessionConstructors",
    "negativeStepCalls": 33, "negativeSharedExecutionCalls": 28,
    "componentUnitGuardFunctions": list(COMPONENT_TESTS),
    "componentGuardsAreNotCompositeRuntimeExecutions": True,
    "allActualNegativeFieldsRetained": True, "canonicalFieldsExcluded": [],
    "permissionDenials": "PublicCompositeHostDataCallsRefusedBeforeProductionBus_NotFabricatedFunctionalEvents",
    "inaccessibleStateMutations": "ActualComponentGuardsOrComparatorMutations_NotPublicRuntimeInjection",
    "originalRomExecutions": 0, "firmwareReady": False,
}


def fault(code, address, detail):
    return {"code": code, "address": address, "detail": detail}


def program_fault(identity):
    if identity == "program-provenance":
        return fault("WrongEmissionProvenance", None, "verified invented M2bj emission only")
    if identity in ("program-wrong-base", "program-wrong-end"):
        return fault("WrongCompositeMapping", None, "exact 1000..1033")
    if identity == "program-short-stream":
        return fault("WrongCompositeLength", None, "both actual streams must be exactly51 bytes")
    if identity in ("program-wrong-digest-label", "program-content-changed", "program-dd1-changed"):
        return fault("WrongCompositeDigest", None, "actual both-DD content, never a caller label")
    return fault("CompositeInventoryMismatch", None, "all20 ordered identities, forms, operands, DD and successors")


def admission(identity, classification, error, cpu=0):
    return {"kind": "negative_admission", "id": identity, "classification": classification,
            "accepted": False, "error": error, "metadata_only": identity in METADATA_ONLY_IDS,
            "cpu_instances": cpu, "bus_instances": 0, "actual_step_calls": 0,
            "positive_composite_executions": 0, "negative_control_composite_executions": 0,
            "original_rom_executions": 0, "firmware_ready": False}


def control_seeds(root):
    selected = {}
    for case in iter_cases(root):
        if case["path"] not in selected:
            require(case["internal_sf"] is False, "FirstClosedControlUsesOriginalSfFalseSeed")
            selected[case["path"]] = deepcopy(case)
        if set(selected) == set("ABCD"):
            break
    require(set(selected) == set("ABCD"), "FourFrozenNegativeControlSeeds")
    return selected


def _prefix(root, request, budget, count):
    parts = expected_execution_components(root, request)
    require(0 <= count <= len(parts["steps"]), "ClosedReferencePrefixLength")
    steps = deepcopy(parts["steps"][:count])
    current = deepcopy(steps[-1]["after"] if count else parts["entry"])
    logical_stop = steps[-1]["logical_span"][1] if count else 48
    raw_stop = steps[-1]["raw_span"][1] if count else 80
    program_stop = steps[-1]["program_span"][1] if count else 0
    complete = count == len(parts["steps"])
    diagnostics = deepcopy(parts["diagnostic_events"][:1 + 2 * count])
    audit = {
        "entry_pc": 4096, "current_pc": current["cpu"]["pc"],
        "program_base": 4096, "program_end_exclusive": 4147, "program_sha256": COMPOSITE_SHA,
        "program_events": deepcopy(parts["program_events"][:program_stop]),
        "data_events": deepcopy(parts["data_events"][:logical_stop]),
        "raw_data_events": deepcopy(parts["raw_data_events"][:raw_stop]),
        "diagnostic_events": diagnostics, "data_admission_refusals": [],
        "permissions": expected_permissions(parts["path"]), "phase": "Sealed" if complete else "Functional",
        "budget": budget, "successful_retirements": count, "step_calls": count,
        "execution_calls": count, "shared_execution_calls": count, "sealed": complete,
        "terminal_reason": "ActualDirectJCompleted" if complete else None,
        "external_exit": parts["terminal_pc"] if complete else None, "first_fault": None,
    }
    return {"mode": "ClosedM2bjComposite", "program_node_count": 20, "path": request["path"],
            "entry": deepcopy(parts["entry"]), "current": current, "steps": steps,
            "direct_j_count": int(complete), "completed": complete, "audit": audit}


def _diagnostic(report):
    rows = report["audit"]["diagnostic_events"]
    rows.append({"ordinal": len(rows), "kind": "RawRamSnapshot", "range": [128, 4096], "byte_count": 3968})


def _latch(report, error):
    audit = report["audit"]
    if audit["first_fault"] is None:
        audit["first_fault"] = deepcopy(error)
    report["completed"] = False
    return deepcopy(audit["first_fault"])


def _program_refusal(report, address, error):
    audit = report["audit"]
    origin = report["steps"][-1]["outcome"]["pc_before"] if report["steps"] else 4096
    length = report["steps"][-1]["outcome"]["len"] if report["steps"] else None
    rows = audit["program_events"]
    rows.append({"ordinal": len(rows), "pc": audit["current_pc"], "address": address,
                 "segment_offset": address - 4096 if 4096 <= address < 4147 else None,
                 "instruction_offset": address - origin if 0 <= address - origin <= 0xFFFFFFFF else None,
                 "acquired_purpose": "DiagnosticProgramProbe", "selection_association": None,
                 "selected_length": length, "serviced": False, "refusal": deepcopy(error)})


def _data_refusal(report, address, width, write, error):
    audit = report["audit"]
    rows = audit["data_admission_refusals"]
    rows.append({"ordinal": len(rows), "classification": "PreBusApiAdmissionRefusal",
                 "phase": audit["phase"], "pc": audit["current_pc"], "address": address,
                 "width": width, "operation": "Write" if write else "Read",
                 "requested_value": 85 if write else None, "production_bus_called": False,
                 "serviced": False, "refusal": deepcopy(error)})


def _operation(name, error):
    return {"operation": name, "accepted": False, "error": deepcopy(error)}


def expected_session(root, identity, request, budget, prefix):
    report = _prefix(root, request, budget, prefix)
    operations = []
    audit = report["audit"]
    complete = report["completed"]
    if identity.startswith("functional-write") or identity == "functional-read-outside-step":
        write = identity != "functional-read-outside-step"
        address = 0x196 if identity in ("functional-read-outside-step", "functional-write-readonly-low") else (
            0x197 if identity == "functional-write-readonly-high" else 0x12A)
        width = 8 if write else 16
        name = {"functional-read-outside-step": "data-read-word0196",
                "functional-write-readonly-low": "data-write-word0196-low",
                "functional-write-readonly-high": "data-write-word0196-high"}.get(identity, "data-write-gate012a")
        error = _latch(report, fault("CompositeCapabilityDataDenied", address,
                       "closed DATA access must arise only from the actual selected production instruction"))
        _data_refusal(report, address, width, write, error)
        operations.append(_operation(name, error))
    elif identity == "functional-reseed":
        error = _latch(report, fault("SeedOutsideSetup", 0x117, "single initialization phase only"))
        operations.append(_operation("seed-after-functional", error))
    elif identity == "functional-second-transition":
        error = _latch(report, fault("InvalidPhaseTransition", None, "Setup to Functional occurs exactly once"))
        operations.append(_operation("second-functional-transition", error))
    elif identity == "functional-legacy-step":
        audit["step_calls"] += 1
        error = _latch(report, fault("WrongCompositeApi", None,
                                   "caller-selected one-step API cannot enter a closed composite"))
        operations.append(_operation("caller-selected-legacy-step", error))
    elif identity == "functional-program-probe":
        error = _latch(report, fault("ProgramPurposeOrPhaseDenied", 4096,
                                   "actual callback purpose and lifecycle must agree"))
        _program_refusal(report, 4096, error)
        operations.append(_operation("program-probe-in-functional", error))
    elif identity == "budget-one-exhaustion":
        # step_composite takes its real before diagnostic, then budget denies
        # before decode. The second faulted attempt never reaches a snapshot.
        _diagnostic(report)
        audit["step_calls"] += 2
        error = _latch(report, fault("InstructionBudgetExceeded", 4098, "bounded before decoder invocation"))
        operations.extend((_operation("step-after-budget", error), _operation("step-after-first-fault", error)))
        _program_refusal(report, 4098, error)
        operations.append(_operation("program-after-first-fault", error))
    elif identity in ("terminal-seal-A", "terminal-seal-D"):
        audit["step_calls"] += 1
        error = _latch(report, fault("SessionSealed", None, "no functional or PROGRAM access after terminal seal"))
        operations.append(_operation("extra-step-after-direct-j", error))
        _program_refusal(report, audit["current_pc"], error)
        operations.append(_operation("external-program-probe-after-j", error))
        _data_refusal(report, 0x196, 16, False, error)
        operations.append(_operation("data-read-after-j", error))
        _data_refusal(report, 0x117, 8, True, error)
        operations.extend((_operation("data-write-after-j", error), _operation("reseed-after-j", error),
                           _operation("functional-after-j", error)))
    else:
        raise AssertionError("UnknownFrozenNegativeControl:" + identity)
    _diagnostic(report)  # One actual composite_report call after all planned operations.
    return {"kind": "negative_session", "id": identity,
            "classification": "ActualClosedCompositeSessionCapability",
            "source_case_id": request["case_id"], "source_internal_sf": request["internal_sf"],
            "actual_successful_prefix_steps": prefix, "completed_before_negative_operation": complete,
            "prefix_error": None, "operations": operations, "report": report, "metadata_only": False,
            "cpu_instances": 1, "bus_instances": 1, "data_initializations": 1, "functional_transitions": 1,
            "positive_composite_executions": 0, "negative_control_composite_executions": int(complete),
            "original_rom_executions": 0, "firmware_ready": False}


def expected_negative_records(root):
    """All33 complete records calculated before any new production observation."""
    selected = control_seeds(root)
    for identity in PROGRAM_IDS:
        yield admission(identity, "ActualClosedProgramAdmission", program_fault(identity))
    for identity in SEED_IDS:
        error = fault("IncompleteCompositeSeeds", None, "exact sixteen inventoried bytes") if identity in (
            "seed-missing-byte", "seed-extra-byte") else fault(
                "ConflictingCompositeAliases", None, "explicit r/er aliases must match actual seed bytes")
        yield admission(identity, "ActualClosedSeedAdmission", error)
    yield admission("psw-incompatible-admission", "ActualAdmissionOnlyNoCpu",
                    fault("IncompatiblePsw", None, "canonical reads-one bits must already be present"))
    for identity in CONSTRUCTOR_IDS:
        if identity.startswith("budget-"):
            error = fault("InvalidEntryState", 4096, "explicit canonical coherent PC/PSW; budget1..16; not halted")
        else:
            error = fault("InvalidCompositeEntry", 4097 if identity == "entry-wrong-pc" else 4096,
                          "exact invented PC/LRB and fresh counters; no PC relocation")
        yield admission(identity, "ActualConstructorRefusalAfterOneCpuBeforeBus", error, cpu=1)
    for identity, path, budget, prefix in SESSION_SPECS:
        yield expected_session(root, identity, selected[path], budget, prefix)


def summarize_actual_negative_records(rows):
    """Derive actual counters; whole frozen-row equality is a separate gate.

    This function alone cannot set firstMismatch=null or promote admission/
    component observations to successful positive composite execution.
    """
    require(type(rows) is list and tuple(row["id"] for row in rows) == NEGATIVE_IDS,
            "ExactOrderedActual33NegativeInventory")
    totals = {"records": len(rows), "admissionRecords": 0, "sessionRecords": 0,
              "metadataOnlyAdmissionRecords": 0, "actualCpuValueConstructions": 0,
              "actualBusInstances": 0, "actualStepCalls": 0, "actualSharedExecutionCalls": 0,
              "actualSuccessfulRetirements": 0, "actualDataInitializations": 0,
              "actualFunctionalTransitions": 0, "negativeCompletedRoutes": 0,
              "negativeCompletedPathCounts": {}, "refusedProgramAttempts": 0,
              "servicedProgramEvents": 0, "externalProgramAttempts": 0,
              "servicedExternalProgramAttempts": 0, "preBusDataAdmissionRefusals": 0,
              "positiveCompositeExecutionsCountedHere": 0}
    for row in rows:
        require(row["positive_composite_executions"] == 0 and row["original_rom_executions"] == 0
                and row["firmware_ready"] is False, "NegativeControlsCannotPromotePositiveOrRomScope")
        for source, target in (("cpu_instances", "actualCpuValueConstructions"),
                               ("bus_instances", "actualBusInstances")):
            require(type(row[source]) is int and row[source] >= 0, "ActualConstructionCounterType")
            totals[target] += row[source]
        totals["metadataOnlyAdmissionRecords"] += int(row["metadata_only"])
        if row["kind"] == "negative_admission":
            require(row["accepted"] is False and row["error"] is not None
                    and row["actual_step_calls"] == 0 and row["bus_instances"] == 0,
                    "ActualConstructorRefusalBeforeBusOrStep")
            totals["admissionRecords"] += 1
            continue
        require(row["kind"] == "negative_session" and row["prefix_error"] is None,
                "ActualNegativePrefixCannotBeSilentlyRetriedOrIgnored")
        totals["sessionRecords"] += 1
        audit = row["report"]["audit"]
        require(audit["first_fault"] is not None and row["report"]["completed"] is False
                and all(op["accepted"] is False and op["error"] is not None for op in row["operations"]),
                "EveryPlannedActualNegativeOperationReallyRefused")
        for source, target in (("step_calls", "actualStepCalls"),
                               ("shared_execution_calls", "actualSharedExecutionCalls"),
                               ("successful_retirements", "actualSuccessfulRetirements")):
            require(type(audit[source]) is int and audit[source] >= 0, "ActualAuditCounterType")
            totals[target] += audit[source]
        totals["actualDataInitializations"] += row["data_initializations"]
        totals["actualFunctionalTransitions"] += row["functional_transitions"]
        if row["completed_before_negative_operation"]:
            require(row["negative_control_composite_executions"] == 1
                    and row["report"]["direct_j_count"] == 1, "OneActualNegativeRouteBeforeTerminalEscapeTest")
            path = row["report"]["path"]
            totals["negativeCompletedRoutes"] += 1
            totals["negativeCompletedPathCounts"][path] = totals["negativeCompletedPathCounts"].get(path, 0) + 1
        else:
            require(row["negative_control_composite_executions"] == 0, "NoFalseNegativeRouteCompletion")
        for event in audit["program_events"]:
            totals["servicedProgramEvents"] += int(event["serviced"])
            totals["refusedProgramAttempts"] += int(not event["serviced"])
            if not 4096 <= event["address"] < 4147:
                totals["externalProgramAttempts"] += 1
                totals["servicedExternalProgramAttempts"] += int(event["serviced"])
        require(all(event["production_bus_called"] is False and event["serviced"] is False
                    for event in audit["data_admission_refusals"]), "PreBusRefusalsNotFabricatedFunctionalBusEvents")
        totals["preBusDataAdmissionRefusals"] += len(audit["data_admission_refusals"])
    expected = {"records": 33, "admissionRecords": 21, "sessionRecords": 12,
                "metadataOnlyAdmissionRecords": 2, "actualCpuValueConstructions": 16,
                "actualBusInstances": 12, "actualStepCalls": 33, "actualSharedExecutionCalls": 28,
                "actualSuccessfulRetirements": 28, "actualDataInitializations": 12,
                "actualFunctionalTransitions": 12, "negativeCompletedRoutes": 2,
                "negativeCompletedPathCounts": {"A": 1, "D": 1}, "refusedProgramAttempts": 4,
                "externalProgramAttempts": 2, "servicedExternalProgramAttempts": 0,
                "preBusDataAdmissionRefusals": 9, "positiveCompositeExecutionsCountedHere": 0}
    require(all(totals[key] == value for key, value in expected.items()),
            "ActualNegativeCountersMustMatchIndependentlyFrozenProtocol")
    return {"classification": "ActualNegativeCounters_NotPositive5470Coverage_NotWholeRowEqualityAlone",
            **totals, "componentGuardExecutionsCountedHere": 0,
            "wholeFrozenRowEqualityRequiredSeparately": True,
            "cpuCountMeaning": SCHEMA["cpuCountMeaning"], "busCountMeaning": SCHEMA["busCountMeaning"],
            "originalRomExecutions": 0, "firmwareReady": False}


COMPARATOR_MUTATIONS = (
    "cf", "zf", "dd", "al", "ah", "pc-successor", "decoded-index", "one-data-byte", "write-order",
    "missing-same-value-write", "false-rmw-read", "missing-selected-program-event",
    "corrupt-terminal-target", "retained-pointing-bank", "mutated-prior-program-event",
    "fabricated-decoder-callback", "reordered-program-events",
)


def comparator_control(root):
    """Select the meaningful D specimen using only independent before-runtime data."""
    for request in iter_cases(root):
        if request["path"] != "D" or request["internal_sf"] is not False:
            continue
        expected = expected_case(root, request)
        writes = [row for row in expected["report"]["audit"]["data_events"]
                  if row["phase"] == "Functional" and row["operation"] == "Write"]
        if any(row["same_value"] is True for row in writes):
            return {"classification": "IndependentFrozenComparatorSpecimen_NotExecution",
                    "request": deepcopy(request), "expected": expected,
                    "mutationIds": list(COMPARATOR_MUTATIONS)}
    raise AssertionError("NoMeaningfulSameValueWriterComparatorControlInFrozenCorpus")


def comparator_mutations(record):
    """Apply only frozen meaningful changes to an independently matched full row.

    The caller must freeze a D-path specimen with a same-value writer before
    execution; these transformations cannot create or revise expectations.
    """
    report = record["report"]
    require(report["path"] == "D" and len(report["steps"]) == 16, "FullFrozenDComparatorSpecimen")
    audit = report["audit"]
    writers = [i for i, row in enumerate(audit["data_events"])
               if row["phase"] == "Functional" and row["operation"] == "Write"]
    same = next((i for i in writers if audit["data_events"][i]["same_value"] is True), None)
    read = next((i for i, row in enumerate(audit["data_events"])
                 if row["phase"] == "Functional" and row["operation"] == "Read"
                 and row["pc"] in (0x1003, 0x1013, 0x101C, 0x101F)), None)
    selected = next((i for i, row in enumerate(audit["program_events"])
                     if row["acquired_purpose"] == "ArchitecturalSelectedFetch"), None)
    probe = next((i for i, row in enumerate(audit["program_events"])
                  if row["acquired_purpose"] == "DecoderProbe"), None)
    require(len(writers) >= 2 and None not in (same, read, selected, probe), "MeaningfulFrozenMutationRelations")
    for identity in COMPARATOR_MUTATIONS:
        changed = deepcopy(record)
        target, events = changed["report"], changed["report"]["audit"]
        if identity in ("cf", "zf", "dd"):
            target["current"]["cpu"][identity] = not target["current"]["cpu"][identity]
        elif identity in ("al", "ah"):
            target["current"]["cpu"]["a"] ^= 1 if identity == "al" else 256
        elif identity == "pc-successor":
            target["steps"][0]["outcome"]["pc_after"] ^= 1
        elif identity == "decoded-index":
            target["steps"][0]["outcome"]["decoded"]["index"] ^= 1
        elif identity == "one-data-byte":
            target["current"]["ram"][0x117 - 0x80] ^= 1
        elif identity == "write-order":
            a, b = writers[:2]
            events["data_events"][a], events["data_events"][b] = events["data_events"][b], events["data_events"][a]
        elif identity == "missing-same-value-write":
            events["data_events"].pop(same)
        elif identity == "false-rmw-read":
            events["data_events"][read]["pc"] ^= 1
        elif identity == "missing-selected-program-event":
            events["program_events"].pop(selected)
        elif identity == "corrupt-terminal-target":
            events["external_exit"] ^= 1
        elif identity == "retained-pointing-bank":
            target["current"]["ram"][0] ^= 1
        elif identity == "mutated-prior-program-event":
            events["program_events"][probe]["pc"] = target["steps"][1]["outcome"]["pc_before"]
        elif identity == "fabricated-decoder-callback":
            events["program_events"].append(deepcopy(events["program_events"][probe]))
        elif identity == "reordered-program-events":
            events["program_events"][0], events["program_events"][1] = events["program_events"][1], events["program_events"][0]
        yield {"id": identity, "metadata_only": False, "mutated": changed}
