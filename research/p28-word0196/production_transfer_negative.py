"""M2br private draft: independent partial-state/refusal protocol components.

The complete positive reference is itself authored before observations. Prefixes
below retain actual partial work expected from the reviewed API/lifecycle; they
do not roll back a Cpu or fill a missing actual report. Private-state mutations
belong to genuine component guards, not fabricated public runtime capabilities.
"""

from copy import deepcopy
from production_transfer_common import bq_modules, require
from production_transfer_corpus import smoke_cases
from production_transfer_emission import program_claims, segment_claim
from production_transfer_oracle import expected_case

REQUIRED_CATEGORIES = (
    "WrongCallerOpcode", "WrongCallerTarget", "WrongCompositeDigest", "WrongCompositeContentOrDDPair",
    "WrongContinuationDigest", "WrongContinuationContent", "WrongSegmentBaseEndOrLength",
    "OverlapOrGapAndReplacement", "MissingTicket", "ForgedClaim", "ReusedTicket", "CrossSessionTicket",
    "StaleArchitecturalState", "StaleDataState", "WrongSourceOrDestination", "PrematureOrNonJAuthority",
    "UnauthorizedTargetOrPathMapping", "PendingProgramAttempt", "PendingDataWrite", "PendingStep",
    "PostCheckpointProgramAttempt", "ReseedOrReconstruct", "BudgetExhaustion", "SecondTerminalJ",
    "StickyFault", "WrongDdOrPsw", "ForbiddenDataOrSfr", "MissingSameValueWrite",
    "GlobalOrdinalOrOldEventReclassification", "ExternalRomFileOrHexBoundary",
)
SCHEMA = {"classification": "IndependentPreRuntimeLifecycleAndPartialEffectExpectations",
          "actualRuntimeRefusalsSeparateFromMetadataOnly": True,
          "privateMutationControls": "ActualComponentGuardsOrComparatorMutations_NotPublicCpuInjection",
          "positive5470Changed": 0, "rollbackClaimed": False, "excludedFields": [],
          "requiredCategories": list(REQUIRED_CATEGORIES), "originalRomExecutions": 0, "firmwareReady": False}
PROGRAM_IDS = ("caller-wrong-opcode", "caller-wrong-target", "composite-wrong-sha", "continuation-wrong-sha",
    "caller-wrong-base", "overlapping-continuation", "unauthorized-continuation-replacement", "partial-continuations",
    "composite-content-changed", "composite-dd1-changed", "composite-node-count", "composite-operand",
    "composite-dd-context", "caller-provenance", "caller-wrong-end", "continuation-wrong-end", "caller-short", "continuation-short")
ENTRY_IDS = ("entry-budget-zero", "entry-budget-19", "entry-wrong-pc", "entry-wrong-lrb", "entry-nonzero-counters", "entry-incoherent-psw")
SEED_IDS = ("seed-alias-conflict", "seed-extra-address")
RUNTIME_IDS = ("premature-ticket", "pending-extra-step", "pending-fetch", "pending-write", "pending-reseed", "duplicate-ticket",
    "claim-target", "claim-source", "claim-destination", "claim-architecture", "claim-data", "claim-journal", "claim-counters", "claim-ordinal",
    "cross-session-ticket", "reused-ticket", "legacy-one-step-api", "legacy-composite-api", "functional-data-read", "functional-data-write",
    "functional-sfr-read", "functional-program-gap", "between-stage-reseed", "global-budget-exhaustion",
    "checkpoint-extra-step", "checkpoint-fetch", "checkpoint-write", "checkpoint-reseed", "checkpoint-ticket", "sticky-fault",
    "claim-wrong-continuation-path")
SCHEMA.update({"runtimeCanonicalRecords": 58, "programAdmissionRecords": 18, "entryAdmissionRecords": 6,
               "seedAdmissionRecords": 2, "runtimeSessionRecords": 32, "metadataOnlyAdmissionRecords": 3,
               "opaqueHandleOrClaimStringsAreNotAuthority": True,
               "expectedSeparateNegativeCpuValues": 39, "expectedSeparateNegativeBusInstances": 33,
               "expectedSeparateNegativeRetirements": 112, "expectedSeparateNegativeStepCalls": 119,
               "expectedSeparateNegativeTicketsIssued": 30, "expectedSeparateNegativeTicketsConsumed": 19,
               "expectedSeparateNegativeTicketRefusals": 15,
               "expectedSeparateNegativeProgramRefusals": 5, "expectedSeparateNegativePreBusDataRefusals": 6})


def control_seeds(root):
    return dict(zip("ABCD", smoke_cases(root)))


def error(code, address, detail):
    return {"code": code, "address": address, "detail": detail}


def prefix_report(root, request, retired, committed, taken, budget=18, continuations=True):
    """Expected report just after a legal prefix, including ONE report snapshot.

    A failed step's additional pre-step diagnostic, an actual refusal attempt,
    or a failed commit's diagnostic must be appended explicitly by its scenario.
    ``taken`` is actual opaque-handle issuance, not just a serialized J record.
    """
    complete = expected_case(root, request)["report"]
    n = len(complete["steps"]) - 2
    require(type(retired) is int and 0 <= retired <= n + 2 and committed in (0, 1, 2)
            and taken in (0, 1, 2) and committed <= taken, "ClosedExpectedPrefixCounters")
    require((retired <= 1 or committed >= 1) and (retired < n + 2 or committed == 2)
            and (committed == 0 or retired >= 1) and (committed < 2 or retired >= n + 1),
            "LegalExpectedPrefixWithoutHostReconstruction")
    require(continuations or retired <= n + 1 and committed <= 1 and taken <= 1,
            "AbsentContinuationCannotMintSecondAuthority")
    role = "ContinuationBelow" if request["path"] == "A" else "ContinuationNotBelow"
    active_role = "Caller" if committed == 0 else "Composite" if committed == 1 else role
    stage = "Caller" if committed == 0 else "Composite" if committed == 1 else "Continuation"
    terminal_without_mapping = not continuations and retired == n + 1
    checkpoint = complete["checkpoint"] if retired == n + 2 else None
    pending = (retired == 1 and committed == 0) or (retired == n + 1 and committed == 1 and continuations)
    phase = "Sealed" if checkpoint is not None or terminal_without_mapping else "TransferPending" if pending else "Functional"
    steps = deepcopy(complete["steps"][:retired])
    current = deepcopy(steps[-1]["after"] if steps else complete["entry"])
    program_end = steps[-1]["program_span"][1] if steps else 0
    logical_end = steps[-1]["logical_span"][1] if steps else 48
    raw_end = steps[-1]["raw_span"][1] if steps else 80
    keep_diagnostics = 1 + 2 * retired + committed
    diagnostics = deepcopy(complete["audit"]["diagnostic_events"][:keep_diagnostics])
    diagnostic_stamps = deepcopy(complete["journal_stages"]["diagnostic"][:keep_diagnostics])
    if terminal_without_mapping:
        diagnostic_stamps[-1]["phase"] = "Sealed"
    diagnostics.append({"ordinal": len(diagnostics), "kind": "RawRamSnapshot", "range": [0x80, 0x1000], "byte_count": 3968})
    diagnostic_stamps.append({"ordinal": len(diagnostic_stamps), "stage": stage, "phase": phase})
    minted = int(retired >= 1) + int(retired >= n + 1 and continuations)
    require(taken <= minted, "CannotIssueHandleBeforeActualJ")
    tickets = deepcopy(complete["tickets"][:minted])
    selected = segment_claim(active_role)
    with bq_modules(root) as modules:
        permissions = modules["production_composite_oracle"].expected_permissions(request["path"]) \
            if stage == "Composite" and not pending else {"reads": [], "writes": [], "raw_reads": [], "raw_writes": []}
    audit = {"entry_pc": 0x0FF0, "current_pc": current["cpu"]["pc"],
             "program_base": selected["base"], "program_end_exclusive": selected["end_exclusive"],
             "program_sha256": selected["sha256"], "program_events": deepcopy(complete["audit"]["program_events"][:program_end]),
             "data_events": deepcopy(complete["audit"]["data_events"][:logical_end]),
             "raw_data_events": deepcopy(complete["audit"]["raw_data_events"][:raw_end]),
             "diagnostic_events": diagnostics, "data_admission_refusals": [], "permissions": permissions,
             "phase": phase, "budget": budget, "successful_retirements": retired, "step_calls": retired,
             "execution_calls": retired, "shared_execution_calls": retired, "sealed": phase == "Sealed",
             "terminal_reason": "InventedContinuationCheckpoint" if checkpoint is not None else
                 "ActualDirectJCompleted" if terminal_without_mapping else "ActualDirectJTransferPending" if pending else None,
             "external_exit": current["cpu"]["pc"] if pending or terminal_without_mapping else None, "first_fault": None}
    return {"mode": complete["mode"], "path": request["path"],
            "programs": program_claims() if continuations else program_claims()[:2],
            "stage": stage, "entry": deepcopy(complete["entry"]), "current": current,
            "steps": steps, "tickets": tickets, "commits": deepcopy(complete["commits"][:committed]),
            "pending": deepcopy(tickets[-1]) if pending else None,
            "tickets_issued": taken, "tickets_consumed": committed, "tickets_refused": 0, "ticket_refusals": [],
            "checkpoint": checkpoint, "completed": checkpoint is not None,
            "composite_direct_j_count": int(retired >= n + 1),
            "journal_stages": {"program": deepcopy(complete["journal_stages"]["program"][:program_end]),
                               "logical": deepcopy(complete["journal_stages"]["logical"][:logical_end]),
                               "raw": deepcopy(complete["journal_stages"]["raw"][:raw_end]),
                               "diagnostic": diagnostic_stamps}, "audit": audit}


def append_diagnostic_before_report(report, phase=None):
    """An actual failed-commit/pre-step snapshot precedes the final report read."""
    phase = report["audit"]["phase"] if phase is None else phase
    diagnostics, stages = report["audit"]["diagnostic_events"], report["journal_stages"]["diagnostic"]
    diagnostics.append(deepcopy(diagnostics[-1]))
    diagnostics[-1]["ordinal"] = len(diagnostics) - 1
    stages.append({"ordinal": len(stages), "stage": report["stage"], "phase": report["audit"]["phase"]})
    # The former last item represents the extra acquisition; the new last item
    # is the report snapshot, both current-stage reads with no RAM mutation.
    stages[-2]["phase"] = phase


def latch(report, failure, operation=None, extra_step_calls=0):
    require(report["audit"]["first_fault"] is None, "FirstExpectedFaultOnly")
    report["audit"]["first_fault"] = deepcopy(failure)
    report["audit"]["step_calls"] += extra_step_calls
    report["completed"] = False
    if operation is not None:
        report["ticket_refusals"].append({"ordinal": len(report["ticket_refusals"]),
                                          "operation": operation, "error": deepcopy(failure)})
        report["tickets_refused"] += 1
    return report


def _operation(name, failure=None):
    return {"operation": name, "accepted": failure is None, "error": deepcopy(failure)}


def _program_refusal(report, address, failure):
    audit = report["audit"]
    last = report["steps"][-1] if report["steps"] else None
    origin = last["outcome"]["pc_before"] if last else report["entry"]["cpu"]["pc"]
    offset = address - audit["program_base"] if audit["program_base"] <= address < audit["program_end_exclusive"] else None
    instruction_offset = address - origin if address >= origin else None
    ordinal = len(audit["program_events"])
    audit["program_events"].append({"ordinal": ordinal, "pc": audit["current_pc"], "address": address,
        "segment_offset": offset, "instruction_offset": instruction_offset,
        "acquired_purpose": "DiagnosticProgramProbe", "selection_association": None,
        "selected_length": last["outcome"]["len"] if last else None, "serviced": False, "refusal": deepcopy(failure)})
    report["journal_stages"]["program"].append({"ordinal": ordinal, "stage": report["stage"], "phase": audit["phase"]})


def _data_refusal(report, address, width, write, value, failure):
    rows, audit = report["audit"]["data_admission_refusals"], report["audit"]
    rows.append({"ordinal": len(rows), "classification": "PreBusApiAdmissionRefusal", "phase": audit["phase"],
                 "pc": audit["current_pc"], "address": address, "width": width,
                 "operation": "Write" if write else "Read", "requested_value": value,
                 "production_bus_called": False, "serviced": False, "refusal": deepcopy(failure)})


def _admission(identity, failure, cpu=0, metadata=False):
    return {"kind": "transfer_negative_admission", "id": identity, "accepted": False, "error": failure,
            "classification": "ActualClosedAdmissionRefusal", "metadata_only": metadata,
            "cpu_instances": cpu, "bus_instances": 0, "actual_step_calls": 0,
            "original_rom_executions": 0, "firmware_ready": False}


def _runtime(root, request, identity):
    checkpoint = identity.startswith("checkpoint-")
    second_edge = identity == "claim-wrong-continuation-path"
    functional = identity.startswith("functional-") or identity in ("between-stage-reseed", "global-budget-exhaustion")
    premature = identity in ("premature-ticket", "legacy-one-step-api", "legacy-composite-api")
    retired = 13 if checkpoint else 12 if second_edge else 1 if not premature else 0
    committed = 2 if checkpoint else 1 if functional or second_edge or identity == "reused-ticket" else 0
    taken = committed
    if identity.startswith("claim-") or identity == "duplicate-ticket":
        taken = 1
    if second_edge:
        taken = 2
    budget = 1 if identity == "global-budget-exhaustion" else 18
    report = prefix_report(root, request, retired, committed, taken, budget)
    operations, other, instances = [], None, 1
    pending_error = error("TransferPending", None, "PROGRAM/DATA/execution/reseed denied before ticket commit")
    sealed_error = error("SessionSealed", None, "no functional or PROGRAM access after terminal seal")
    if identity == "premature-ticket":
        fault = error("TransferNotPending", None, "actual direct J must retire first")
        operations.append(_operation("take-ticket", fault))
        latch(report, fault, "TakeTicket")
    elif identity == "duplicate-ticket":
        fault = error("TransferTicketAlreadyIssued", None, "one opaque handle for each pending edge")
        operations.extend((_operation("take-ticket-first"), _operation("take-ticket-second", fault)))
        latch(report, fault, "TakeTicket")
    elif identity.startswith("claim-"):
        fault = error("TransferClaimMismatch", None, "all immutable owner-bound actual J/state/journal/counter fields must agree")
        append_diagnostic_before_report(report)
        operations.append(_operation("commit-wrong-continuation-path" if second_edge else "commit-mutated-claim", fault))
        latch(report, fault, "CommitTicket")
    elif identity == "cross-session-ticket":
        other = prefix_report(root, request, 1, 0, 1)
        instances = 2
        fault = error("CrossSessionTransferTicket", None, "opaque owner authority never comes from a serialized claim")
        append_diagnostic_before_report(report)
        operations.append(_operation("commit-other-session-ticket", fault))
        latch(report, fault, "CommitTicket")
    elif identity == "reused-ticket":
        fault = error("TransferTicketAlreadyConsumed", None, "single-use pending authority")
        append_diagnostic_before_report(report)
        operations.extend((_operation("commit-ticket-first"), _operation("commit-ticket-second", fault)))
        latch(report, fault, "CommitTicket")
    elif identity in ("legacy-one-step-api", "legacy-composite-api"):
        fault = error("WrongTransferApi", None, "old one-step API cannot enter a closed transfer") if identity == "legacy-one-step-api" else \
            error("WrongCompositeApi", None, "explicit closed constructor required")
        operations.append(_operation("legacy-step" if identity == "legacy-one-step-api" else "legacy-composite-step", fault))
        latch(report, fault, extra_step_calls=1)
    elif identity in ("pending-extra-step", "checkpoint-extra-step", "global-budget-exhaustion"):
        fault = pending_error if identity == "pending-extra-step" else sealed_error
        if identity == "global-budget-exhaustion":
            fault = error("InstructionBudgetExceeded", 0x1000, "bounded before decoder invocation")
            append_diagnostic_before_report(report)
        operations.append(_operation("step-transfer", fault))
        latch(report, fault, extra_step_calls=1)
    elif identity in ("pending-fetch", "checkpoint-fetch", "functional-program-gap"):
        address = 0x1000 if identity == "pending-fetch" else 0x55C7 if checkpoint else 0x2000
        fault = pending_error if identity == "pending-fetch" else sealed_error if checkpoint else \
            error("ProgramPurposeOrPhaseDenied", address, "actual callback purpose and lifecycle must agree")
        _program_refusal(report, address, fault)
        operations.append(_operation("program-gap-probe" if functional else "program-probe", fault))
        latch(report, fault)
    elif identity in ("pending-write", "functional-data-write", "checkpoint-write", "functional-data-read", "functional-sfr-read"):
        write = identity.endswith("write")
        address = 0x18E if write else 0x10 if identity == "functional-sfr-read" else 0x196
        width = 8 if write or address == 0x10 else 16
        fault = pending_error if identity == "pending-write" else sealed_error if checkpoint else \
            error("TransferCapabilityDataDenied", address, "only actual stage instructions may access DATA")
        _data_refusal(report, address, width, write, 0x42 if write else None, fault)
        operations.append(_operation("data-write" if write else "data-read-sfr" if address == 0x10 else "data-read", fault))
        latch(report, fault)
    elif identity in ("pending-reseed", "between-stage-reseed", "checkpoint-reseed"):
        fault = pending_error if identity == "pending-reseed" else sealed_error if checkpoint else \
            error("SeedOutsideSetup", 0x196, "single initialization phase only")
        operations.append(_operation("reseed", fault))
        latch(report, fault)
    elif identity == "checkpoint-ticket":
        fault = error("SessionSealed", None, "no authority after terminal seal")
        operations.append(_operation("take-ticket", fault))
        latch(report, fault, "TakeTicket")
    elif identity == "sticky-fault":
        _program_refusal(report, 0x1000, pending_error)
        _data_refusal(report, 0x18E, 8, True, 0x42, pending_error)
        operations.extend(_operation(name, pending_error) for name in
                          ("pending-program-fault", "step-after-fault", "write-after-fault", "ticket-after-fault"))
        latch(report, pending_error, "TakeTicket", extra_step_calls=1)
    else:
        raise ValueError("ClosedIndependentNegativeIdentity:" + identity)
    return {"kind": "transfer_negative_runtime", "id": identity, "classification": "ActualPublicApiRuntimeRefusal",
            "operations": operations, "report": report, "other_session_report": other,
            "cpu_instances": instances, "bus_instances": instances, "data_initializations": instances,
            "functional_transitions": instances, "positive_transfer_executions": 0,
            "original_rom_executions": 0, "firmware_ready": False}


def expected_negative_records(root):
    for identity in PROGRAM_IDS:
        if identity in ("composite-wrong-sha", "composite-content-changed", "composite-dd1-changed"):
            failure = error("WrongCompositeDigest", None, "actual both-DD content, never a caller label")
        elif identity in ("composite-node-count", "composite-operand", "composite-dd-context"):
            failure = error("CompositeInventoryMismatch", None, "all20 ordered identities, forms, operands, DD and successors")
        elif identity == "partial-continuations":
            failure = error("IncompleteTransferProfiles", None, "both invented continuations or neither; no mutable replacement")
        else:
            below = identity in ("continuation-wrong-sha", "overlapping-continuation", "unauthorized-continuation-replacement",
                                 "continuation-wrong-end", "continuation-short")
            failure = error("TransferSegmentAdmissionMismatch", 0x55C5 if below else 0x0FF0,
                            "only exact independently frozen invented profile/base/end/content/provenance")
        yield _admission(identity, failure, metadata=identity in
                         ("caller-provenance", "composite-wrong-sha", "continuation-wrong-sha"))
    for identity in ENTRY_IDS:
        yield _admission(identity, error("InvalidTransferEntry", 0x1000 if identity == "entry-wrong-pc" else 0x0FF0,
                         "fresh invented caller PC/counters; exact representable context; budget1..18"), cpu=1)
    yield _admission("seed-alias-conflict", error("ConflictingCompositeAliases", None, "explicit r/er aliases must match actual seed bytes"))
    yield _admission("seed-extra-address", error("IncompleteCompositeSeeds", None, "exact sixteen inventoried bytes"))
    request = control_seeds(root)["A"]
    for identity in RUNTIME_IDS:
        yield _runtime(root, request, identity)
    report = prefix_report(root, request, 12, 1, 1, continuations=False)
    failure = error("SessionSealed", None, "no functional or PROGRAM access after terminal seal")
    _program_refusal(report, 0x55C5, failure)
    latch(report, failure, extra_step_calls=1)
    yield {"kind": "transfer_negative_runtime", "id": "missing-continuations-sealed-stop",
           "classification": "ActualAbsentContinuationSealedStop",
           "operations": [_operation("post-terminal-probe", failure), _operation("post-terminal-step", failure)],
           "report": report, "other_session_report": None, "cpu_instances": 1, "bus_instances": 1,
           "data_initializations": 1, "functional_transitions": 1, "positive_transfer_executions": 0,
           "original_rom_executions": 0, "firmware_ready": False}


def summarize_actual_negative_records(rows):
    """Derive counters; full frozen-row equality must be established separately."""
    expected_ids = list(PROGRAM_IDS + ENTRY_IDS + SEED_IDS + RUNTIME_IDS) + ["missing-continuations-sealed-stop"]
    totals = {"records": 0, "metadataOnlyAdmissionRecords": 0, "cpuValues": 0, "busInstances": 0,
              "successfulRetirements": 0, "stepCalls": 0, "sharedExecutionCalls": 0,
              "ticketsIssued": 0, "ticketsConsumed": 0, "ticketRefusals": 0,
              "programRefusals": 0, "preBusDataRefusals": 0, "completedTransferSessions": 0,
              "checkpointReachedBeforeLaterRefusal": 0, "actualContinuationRetirements": 0,
              "softwareAccountingCycles": 0, "diagnosticEvents": 0,
              "functionalLogicalReads": 0, "functionalLogicalWrites": 0}
    for index, row in enumerate(rows):
        require(index < len(expected_ids) and row["id"] == expected_ids[index], "EveryActualNegativeIdentityInFrozenOrder")
        totals["records"] += 1
        totals["cpuValues"] += row["cpu_instances"]
        totals["busInstances"] += row["bus_instances"]
        if row["kind"] == "transfer_negative_admission":
            require(row["accepted"] is False and row["error"] is not None, "ActualAdmissionMustRefuse")
            totals["metadataOnlyAdmissionRecords"] += int(row["metadata_only"])
            continue
        for report in (row["report"], row["other_session_report"]):
            if report is None:
                continue
            audit = report["audit"]
            totals["successfulRetirements"] += audit["successful_retirements"]
            totals["stepCalls"] += audit["step_calls"]
            totals["sharedExecutionCalls"] += audit["shared_execution_calls"]
            totals["ticketsIssued"] += report["tickets_issued"]
            totals["ticketsConsumed"] += report["tickets_consumed"]
            totals["ticketRefusals"] += report["tickets_refused"]
            totals["completedTransferSessions"] += int(report["completed"])
            totals["checkpointReachedBeforeLaterRefusal"] += int(report["checkpoint"] is not None)
            totals["actualContinuationRetirements"] += sum(step["stage"] == "Continuation" and step["outcome"]["retired"]
                                                          for step in report["steps"])
            totals["softwareAccountingCycles"] += report["current"]["cpu"]["cycles"]
            totals["diagnosticEvents"] += len(audit["diagnostic_events"])
            totals["programRefusals"] += sum(not event["serviced"] for event in audit["program_events"])
            totals["preBusDataRefusals"] += len(audit["data_admission_refusals"])
            for event in audit["data_events"]:
                if event["phase"] == "Functional" and event["serviced"]:
                    totals["functionalLogicalReads" if event["operation"] == "Read" else "functionalLogicalWrites"] += 1
    require((totals["records"], totals["metadataOnlyAdmissionRecords"], totals["cpuValues"], totals["busInstances"],
             totals["successfulRetirements"], totals["stepCalls"], totals["sharedExecutionCalls"],
             totals["ticketsIssued"], totals["ticketsConsumed"], totals["ticketRefusals"], totals["programRefusals"],
             totals["preBusDataRefusals"], totals["functionalLogicalReads"], totals["functionalLogicalWrites"])
            == (58, 3, 39, 33, 112, 119, 112, 30, 19, 15, 5, 6, 35, 21),
            "ActualSeparateNegativeCountersMustMatchIndependentProtocol")
    require((totals["completedTransferSessions"], totals["checkpointReachedBeforeLaterRefusal"],
             totals["actualContinuationRetirements"]) == (0, 5, 5), "PostCheckpointFaultCannotErasePriorRealRetirements")
    require((totals["softwareAccountingCycles"], totals["diagnosticEvents"]) == (615, 321), "SeparateNegativeSourceCountersAndAllDiagnosticReads")
    return totals


COMPARATOR_MUTATIONS = (
    "caller_pc", "caller_cf", "caller_dd", "caller_cycles", "composite_pc", "composite_cf", "composite_zf",
    "composite_ah", "composite_raw_write_order", "same_value_write_missing", "program_old_ordinal",
    "program_reclassified", "stage_program_stamp", "data_decoded_identity", "data_global_ordinal",
    "ticket_architecture", "ticket_data", "ticket_source", "ticket_destination", "ticket_target",
    "ticket_program_boundary", "ticket_write_ordinal", "ticket_global_cycles", "commit_observed_ram",
    "commit_diagnostic_span", "continuation_al", "continuation_cf", "continuation_zf", "continuation_dd",
    "checkpoint_pc", "pointing_bank_retention", "partial_report_promoted",
)


def comparator_mutations(record):
    require(record["kind"] == "transfer_observation" and record["report"]["path"] == "D",
            "FrozenDComparatorSpecimenRequired")
    for identity in COMPARATOR_MUTATIONS:
        changed = deepcopy(record)
        report, audit = changed["report"], changed["report"]["audit"]
        steps, tickets = report["steps"], report["tickets"]
        if identity == "caller_pc": steps[0]["after"]["cpu"]["pc"] += 1
        elif identity == "caller_cf": steps[0]["after"]["cpu"]["cf"] = not steps[0]["after"]["cpu"]["cf"]
        elif identity == "caller_dd": steps[0]["after"]["cpu"]["dd"] = not steps[0]["after"]["cpu"]["dd"]
        elif identity == "caller_cycles": steps[0]["after"]["cpu"]["cycles"] -= 1
        elif identity == "composite_pc": steps[2]["after"]["cpu"]["pc"] += 1
        elif identity == "composite_cf": steps[2]["after"]["cpu"]["cf"] = not steps[2]["after"]["cpu"]["cf"]
        elif identity == "composite_zf": steps[2]["after"]["cpu"]["zf"] = not steps[2]["after"]["cpu"]["zf"]
        elif identity == "composite_ah": steps[2]["after"]["cpu"]["a"] ^= 0x100
        elif identity == "composite_raw_write_order": audit["raw_data_events"][81:83] = reversed(audit["raw_data_events"][81:83])
        elif identity == "same_value_write_missing":
            position = next(index for index, event in enumerate(audit["data_events"]) if event["phase"] == "Functional"
                            and event["operation"] == "Write" and event["same_value"] is True)
            del audit["data_events"][position]
        elif identity == "program_old_ordinal": audit["program_events"][0]["ordinal"] += 1
        elif identity == "program_reclassified": audit["program_events"][0]["selection_association"] = "DecoderLookahead"
        elif identity == "stage_program_stamp": report["journal_stages"]["program"][0]["stage"] = "Composite"
        elif identity == "data_decoded_identity": audit["data_events"][48]["instruction_index"] += 1
        elif identity == "data_global_ordinal": audit["data_events"][48]["ordinal"] -= 48
        elif identity == "ticket_architecture": tickets[0]["architecture_sha256"] = "0" * 64
        elif identity == "ticket_data": tickets[0]["data_sha256"] = "0" * 64
        elif identity == "ticket_source": tickets[0]["source"]["base"] += 1
        elif identity == "ticket_destination": tickets[0]["destination"]["base"] += 1
        elif identity == "ticket_target": tickets[0]["actual_target_pc"] += 1
        elif identity == "ticket_program_boundary": tickets[0]["journal"]["program"] += 1
        elif identity == "ticket_write_ordinal": tickets[1]["journal"]["logical_writes"] -= 48
        elif identity == "ticket_global_cycles": tickets[1]["counters"]["cpu_cycles"] -= 7
        elif identity == "commit_observed_ram": report["commits"][0]["observed"]["ram"][0] ^= 1
        elif identity == "commit_diagnostic_span": report["commits"][0]["diagnostic_span"][1] += 1
        elif identity == "continuation_al": steps[-1]["after"]["cpu"]["a"] ^= 1
        elif identity == "continuation_cf": steps[-1]["after"]["cpu"]["cf"] = not steps[-1]["after"]["cpu"]["cf"]
        elif identity == "continuation_zf": steps[-1]["after"]["cpu"]["zf"] = not steps[-1]["after"]["cpu"]["zf"]
        elif identity == "continuation_dd": steps[-1]["after"]["cpu"]["dd"] = True
        elif identity == "checkpoint_pc": report["checkpoint"] += 1
        elif identity == "pointing_bank_retention": report["current"]["ram"][8] ^= 1
        elif identity == "partial_report_promoted": report["steps"].pop(); report["completed"] = True
        yield identity, changed


def comparator_control(root):
    from production_transfer_corpus import iter_cases
    iterator = iter_cases(root)
    try:
        for request in iterator:
            if request["path"] != "D" or request["internal_sf"] is not False:
                continue
            record = expected_case(root, request)
            if any(event["phase"] == "Functional" and event["operation"] == "Write" and event["same_value"] is True
                   for event in record["report"]["audit"]["data_events"]):
                return request, record, list(COMPARATOR_MUTATIONS)
    finally:
        iterator.close()
    raise ValueError("IndependentFrozenSameValueWriterComparatorControlNotFound")
