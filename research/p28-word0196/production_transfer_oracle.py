"""M2br private draft: independent complete three-stage expectation components.

J and immediate-LB effects follow the retained manufacturer facts. Composite
state/effects come only from the unchanged M2bk reference, M2av IR/C11 and M2bd
obligations. Production code is not interpreted here. The separately labelled
Bus, diagnostic, ticket and PROGRAM models are expected observation protocols,
never actual observations or native ECU evidence. Nothing runs on import.
"""

from copy import deepcopy
from hashlib import sha256
from production_transfer_common import (
    COMPOSITE_SHA, DATA_INVENTORY, MANUAL_SHA, PROVENANCE, RAM_BEGIN, RAM_END,
    bq_modules, canonical, first_difference, profile_instruction, require, segment_identities,
)
from production_transfer_corpus import historical_case, PATH_EXPECTATIONS
from production_transfer_topology import expected_program_components

SCHEMA = {"architecture": "ManufacturerJ116_LB124_ImmutableM2bk_M2avIR_C11_M2bd",
          "data": "SameM2bqOrderedLogicalRawEffects_SingleInitialization_NoAddedFunctionalAccess",
          "cycles": "UnchangedSourceAccounting_NotPhysicalOrManufacturerExactTiming",
          "callerPrefix": {"instructions": 1, "cycles": 7, "programCallbacks": 7},
          "continuationSuffix": {"instructions": 1, "cycles": 4, "programCallbacks": 5},
          "snapshots": "Constructor1_BeforeAfterEachRetirement2_ActualCommit2_Report1",
          "ticketDigests": "ArchitectureAndFullRam_WithGlobalFunctionalBoundaries_DiagnosticsRecordedSeparately",
          "nativeSf": "UnknownMeaningStorageWidth_InternalBooleanRetained",
          "all3968RamBytesCompared": True, "excludedCanonicalFields": [],
          "originalRomExecutions": 0, "firmwareReady": False}


def cpu_full_psw(cpu):
    require(set(cpu) == {"pc", "a", "ssp", "lrb", "zf", "cf", "hc", "dd", "sf", "psw_other",
                         "cycles", "instructions", "halted"}, "CompleteCpuDigestInput")
    require(cpu["psw_other"] & ~0x0337 == 0, "RepresentableStoredOtherPsw")
    return cpu["psw_other"] | 0x0CC8 | sum(int(cpu[name]) << shift
           for name, shift in (("cf", 15), ("zf", 14), ("hc", 13), ("dd", 12)))


def architecture_digest(snapshot):
    cpu = snapshot["cpu"]
    material = bytearray(b"M2brCpuStateV1\0")
    for value in (cpu["pc"], cpu["a"], cpu["ssp"], cpu["lrb"], cpu_full_psw(cpu), cpu["psw_other"]):
        require(type(value) is int and 0 <= value <= 65535, "ArchitectureDigestU16")
        material.extend(value.to_bytes(2, "little"))
    for name in ("zf", "cf", "hc", "dd", "sf", "halted"):
        require(type(cpu[name]) is bool, "ArchitectureDigestBoolean")
        material.append(int(cpu[name]))
    for name in ("cycles", "instructions"):
        value = cpu[name]
        require(type(value) is int and 0 <= value < 1 << 64, "ArchitectureDigestU64")
        material.extend(value.to_bytes(8, "little"))
    return sha256(material).hexdigest()


def data_digest(snapshot):
    require(snapshot["ram_range"] == [RAM_BEGIN, RAM_END] and type(snapshot["ram"]) is list
            and len(snapshot["ram"]) == RAM_END - RAM_BEGIN
            and all(type(v) is int and 0 <= v <= 255 for v in snapshot["ram"]), "CompleteRamDigestInput")
    return sha256(b"M2brDataStateV1\0" + RAM_BEGIN.to_bytes(2, "little")
                  + RAM_END.to_bytes(2, "little") + bytes(snapshot["ram"])).hexdigest()


def _caller_state(reference):
    result = deepcopy(reference["entryState"])
    result["pc"] = 0x0FF0
    return result


def continuation_state(reference):
    result = deepcopy(reference["terminalState"])
    immediate = 0 if reference["path"] == "A" else 0xA5
    result["al"] = immediate
    result["a"] = (result["a"] & 0xFF00) | immediate
    result["zf"], result["dd"] = int(immediate == 0), 0
    result["psw"] = (result["psw"] & ~0x5000) | (int(immediate == 0) << 14)
    result["pc"] += 2
    return result


def tiny_decode(role, incoming_dd):
    require(type(incoming_dd) is bool, "ExactIncomingDd")
    caller = role == "Caller"
    require(caller or role in ("ContinuationBelow", "ContinuationNotBelow"), "ClosedTinyForm")
    immediate = 0 if role == "ContinuationBelow" else 0xA5
    return {"index": 684 if caller else 738, "mnemonic": "J addr16" if caller else "LB A, #N8",
            "len": 3 if caller else 2, "dd_before": incoming_dd,
            "dd_after": incoming_dd if caller else False,
            "dd_after_option": None if caller else False,
            "cycles": 7 if caller else 4, "n8": 0 if caller else immediate, "n16": 0,
            "addr16": 0x1000 if caller else 0, "rel8": 0, "n8_alt": 0, "n16_alt": 0, "s8": 0}


def _seed_once(data, request):
    require(tuple(sorted(int(k) for k in request["data"])) == DATA_INVENTORY, "SameSixteenDataSeeds")
    for address, value in sorted(request["data"].items(), key=lambda row: int(row[0])):
        data.event(0x0FF0, None, int(address), 8, "Write", value, "Seed")
    for bank, row in enumerate(request["entry"]["pointing_banks"]):
        for slot, name in enumerate(("x1", "x2", "dp", "usp")):
            data.event(0x0FF0, None, 0x80 + bank * 8 + slot * 2, 16, "Write", row[name], "Seed")
    require((len(data.logical), len(data.raw), data.write_ordinal, data.raw_write_ordinal)
            == (48, 80, 48, 80), "ExactlyOne48Logical80RawInitialization")


def expected_execution_components(root, request):
    original = historical_case(request)
    with bq_modules(root) as modules:
        model = modules["production_composite_oracle"]
        reference = model.reference_case(root, original)
        data = model.ExpectedDataProtocol()
        with modules["production_composite_common"].reference_modules(root) as legacy:
            old = legacy["synthetic_composite_execution_oracle"]
            primary = legacy["synthetic_composite_primary_oracle"]
            # These are fixed reviewed old functions. No new production output
            # or active effects implementation is an input to the reference.
            decode_reference = old._decode
            primary_nodes = primary.NODES
            primary_instruction = primary.expected_instruction
            _seed_once(data, request)
            sf, cycles, retired = request["internal_sf"], 0, 0
            entry_state = _caller_state(reference)
            entry = data.snapshot(entry_state, sf, cycles, retired)
            steps, pending = [], []
            topology = expected_program_components(root, reference)

            def append_tiny(role, before_state, after_state):
                nonlocal cycles, retired
                before = data.snapshot(before_state, sf, cycles, retired)
                decoded = tiny_decode(role, bool(before_state["dd"]))
                cycles += decoded["cycles"]
                retired += 1
                after = data.snapshot(after_state, sf, cycles, retired)
                pc = before_state["pc"]
                identity = "CallerJ" if role == "Caller" else role + "LB"
                outcome = {"pc_before": pc, "pc_after": after_state["pc"],
                           "decoded_index": decoded["index"], "mnemonic": decoded["mnemonic"],
                           "len": decoded["len"], "decoded": decoded,
                           "selected_extent": [pc, pc + decoded["len"]],
                           "selected_extent_sha256": sha256(profile_instruction(role)).hexdigest(),
                           "retired": True, "external_exit": after_state["pc"] if role == "Caller" else None}
                steps.append({"global_index": retired, "stage": role, "stage_index": 1,
                              "node_identity": identity, "form": "j-address" if role == "Caller" else "lb-a-imm8",
                              "before": before, "after": after, "outcome": outcome,
                              "program_span": topology["step_spans"][retired - 1],
                              "logical_span": [len(data.logical)] * 2, "raw_span": [len(data.raw)] * 2})

            append_tiny("Caller", entry_state, reference["entryState"])
            pending.append({"edge": 0, "source": "Caller", "destination": "Composite",
                            "snapshot": deepcopy(steps[-1]["after"]), "program_boundary": 7,
                            "logical_boundary": len(data.logical), "raw_boundary": len(data.raw),
                            "write_ordinal": data.write_ordinal, "raw_write_ordinal": data.raw_write_ordinal})
            # Each successful commit acquires a new diagnostic snapshot to check
            # the actual live CPU/RAM. It must not reset/copy architectural state.
            caller_commit = data.snapshot(reference["entryState"], sf, cycles, retired)
            for local_index, row in enumerate(reference["trace"], 1):
                identifier = model.logical_id(row)
                decoded = decode_reference(row)
                before = data.snapshot(row["stateBefore"], sf, cycles, retired)
                logical_start, raw_start = len(data.logical), len(data.raw)
                for read in row["dataReads"]:
                    value, _ = data.event(row["syntheticPc"], decoded["index"], read["address"],
                                          read["widthBits"], "Read")
                    require(value == read["value"], "IndependentReferenceReadAndMemoryAgree")
                for write in row["dataWrites"]:
                    _, old_value = data.event(row["syntheticPc"], decoded["index"], write["address"],
                                             8, "Write", write["value"])
                    require(old_value == write["oldValue"], "IndependentReferenceWriterPriorValue")
                cost = 2 * row["length"] + int(identifier.startswith("DirectJ_"))
                cycles += cost + (4 if row["branchTaken"] is True else 0)
                retired += 1
                after = data.snapshot(row["stateAfter"], sf, cycles, retired)
                primary_index = next(index for index, node in enumerate(primary_nodes)
                                     if (node.node_id if type(node.node_id) is str else f"{node.node_id:04X}") == identifier)
                wire_decode = {k: v for k, v in decoded.items() if k != "form"}
                wire_decode.update({"dd_after_option": False if identifier in ("556F", "5575", "5592", "55BF") else None,
                                    "cycles": cost, "n16_alt": 0, "s8": 0})
                outcome = {"pc_before": row["syntheticPc"], "pc_after": row["stateAfter"]["pc"],
                           "decoded_index": wire_decode["index"], "mnemonic": wire_decode["mnemonic"],
                           "len": wire_decode["len"], "decoded": wire_decode,
                           "selected_extent": [row["syntheticPc"], row["syntheticPc"] + row["length"]],
                           "selected_extent_sha256": sha256(primary_instruction(primary_index)).hexdigest(),
                           "retired": True,
                           "external_exit": reference["terminalPc"] if identifier.startswith("DirectJ_") else None}
                steps.append({"global_index": retired, "stage": "Composite", "stage_index": local_index,
                              "node_identity": identifier, "form": model.FORM_IDS[identifier],
                              "before": before, "after": after, "outcome": outcome,
                              "program_span": topology["step_spans"][retired - 1],
                              "logical_span": [logical_start, len(data.logical)],
                              "raw_span": [raw_start, len(data.raw)]})
            role = "ContinuationBelow" if reference["path"] == "A" else "ContinuationNotBelow"
            pending.append({"edge": 1, "source": "Composite", "destination": role,
                            "snapshot": deepcopy(steps[-1]["after"]),
                            "program_boundary": topology["stage_spans"]["Composite"][1],
                            "logical_boundary": len(data.logical), "raw_boundary": len(data.raw),
                            "write_ordinal": data.write_ordinal, "raw_write_ordinal": data.raw_write_ordinal})
            continuation_commit = data.snapshot(reference["terminalState"], sf, cycles, retired)
            terminal_state = continuation_state(reference)
            append_tiny(role, reference["terminalState"], terminal_state)
            current = data.snapshot(terminal_state, sf, cycles, retired)
    expected = PATH_EXPECTATIONS[reference["path"]]
    require((retired, cycles, len(data.diagnostics))
            == (expected["total_retirements"], expected["total_cycles"],
                2 * expected["composite_retirements"] + 8), "IndependentThreeStageCountsAndDiagnosticProtocol")
    require(data.logical[:48] == [{**row, "pc": 0x0FF0} for row in data.logical[:48]], "TrueInitialSeedPc")
    for edge in pending:
        edge["architecture_sha256"] = architecture_digest(edge["snapshot"])
        edge["data_sha256"] = data_digest(edge["snapshot"])
    return {"reference": reference, "entry": entry, "current": current, "steps": steps,
            "program_events": topology["events"], "stage_program_events": topology["stage_events"],
            "program_stage_spans": topology["stage_spans"], "logical_events": data.logical,
            "raw_events": data.raw, "diagnostic_events": data.diagnostics,
            "pending_expectations": pending, "commit_snapshots": [caller_commit, continuation_commit],
            "retired": retired, "cycles": cycles, "path": reference["path"],
            "checkpoint_pc": terminal_state["pc"], "expected_only": True,
            "historical_semantics": "UnchangedM2bkM2bnM2avM2bd", "manual_sha256": MANUAL_SHA,
            "composite_sha256": COMPOSITE_SHA, "provenance": PROVENANCE}


def expected_case(root, request):
    """Complete pre-runtime expected public wire record, not an observation."""
    from production_transfer_emission import program_claims, segment_claim
    parts = expected_execution_components(root, request)
    count, n = parts["retired"], len(parts["reference"]["trace"])
    continuation = "ContinuationBelow" if parts["path"] == "A" else "ContinuationNotBelow"
    steps = []
    for row in parts["steps"]:
        role = row["stage"]
        stage = "Continuation" if role.startswith("Continuation") else role
        index = row["global_index"]
        prefix_instructions = 0 if stage == "Caller" else 1 if stage == "Composite" else n + 1
        prefix_cycles = 0 if stage == "Caller" else 7 if stage == "Composite" else parts["cycles"] - 4
        node = row["node_identity"]
        if stage == "Caller":
            node = "InventedCaller_J1000"
        elif stage == "Continuation":
            node = "InventedBelow_LB00" if parts["path"] == "A" else "InventedNotBelow_LBA5"
        steps.append({"index": index, "stage": stage, "stage_index": row["stage_index"],
                      "segment": segment_claim(role)["id"], "node_identity": node, "form": row["form"],
                      "before": row["before"], "after": row["after"], "outcome": row["outcome"],
                      "program_span": row["program_span"], "logical_span": row["logical_span"],
                      "raw_span": row["raw_span"],
                      "stage_relative_instructions": row["after"]["cpu"]["instructions"] - prefix_instructions,
                      "stage_relative_cycles": row["after"]["cpu"]["cycles"] - prefix_cycles})
    tickets = []
    for edge, step in zip(parts["pending_expectations"], (steps[0], steps[-2])):
        retired = step["after"]["cpu"]["instructions"]
        tickets.append({"transition_ordinal": edge["edge"], "source": segment_claim(edge["source"]),
                        "destination": segment_claim(edge["destination"]),
                        "source_instruction_pc": step["outcome"]["pc_before"],
                        "retired_instruction": step["outcome"], "actual_target_pc": step["after"]["cpu"]["pc"],
                        "architecture_sha256": edge["architecture_sha256"], "data_sha256": edge["data_sha256"],
                        "journal": {"program": edge["program_boundary"], "logical": edge["logical_boundary"],
                                    "raw": edge["raw_boundary"], "logical_writes": edge["write_ordinal"],
                                    "raw_writes": edge["raw_write_ordinal"]},
                        "counters": {"successful_retirements": retired, "step_calls": retired,
                                     "shared_execution_calls": retired, "cpu_instructions": retired,
                                     "cpu_cycles": step["after"]["cpu"]["cycles"]},
                        "provenance": PROVENANCE, "classification": "ResearchOnly_ActualDirectJRetired_TransferPending"})
    commits = [{"transition": tickets[0], "observed": parts["commit_snapshots"][0],
                "committed": True, "diagnostic_span": [3, 4]},
               {"transition": tickets[1], "observed": parts["commit_snapshots"][1],
                "committed": True, "diagnostic_span": [2 * n + 4, 2 * n + 5]}]
    diagnostic_phases = [(None, "Setup"), ("Caller", "Functional"),
                         ("Caller", "TransferPending"), ("Caller", "TransferPending")]
    for index in range(n):
        diagnostic_phases.extend((("Composite", "Functional"),
                                  ("Composite", "TransferPending" if index == n - 1 else "Functional")))
    diagnostic_phases.extend((("Composite", "TransferPending"), ("Continuation", "Functional"),
                              ("Continuation", "Sealed"), ("Continuation", "Sealed")))
    require(len(diagnostic_phases) == len(parts["diagnostic_events"]), "EveryDiagnosticAttributedToActualAcquisitionPhase")
    stage_stamps = {"program": [{"ordinal": index, "stage": "Continuation" if row["stage"].startswith("Continuation") else row["stage"],
                                 "phase": "Executing"} for index, row in enumerate(parts["stage_program_events"])],
                    "logical": [{"ordinal": row["ordinal"], "stage": None if row["phase"] == "Seed" else "Composite",
                                 "phase": "Setup" if row["phase"] == "Seed" else "Executing"}
                                for row in parts["logical_events"]],
                    "raw": [{"ordinal": index, "stage": None if index < 80 else "Composite",
                             "phase": "Setup" if index < 80 else "Executing"}
                            for index in range(len(parts["raw_events"]))],
                    "diagnostic": [{"ordinal": index, "stage": stage, "phase": phase}
                                   for index, (stage, phase) in enumerate(diagnostic_phases)]}
    selected = segment_claim(continuation)
    audit = {"entry_pc": 0x0FF0, "current_pc": parts["checkpoint_pc"],
             "program_base": selected["base"], "program_end_exclusive": selected["end_exclusive"],
             "program_sha256": selected["sha256"], "program_events": parts["program_events"],
             "data_events": parts["logical_events"], "raw_data_events": parts["raw_events"],
             "diagnostic_events": parts["diagnostic_events"], "data_admission_refusals": [],
             "permissions": {"reads": [], "writes": [], "raw_reads": [], "raw_writes": []},
             "phase": "Sealed", "budget": 18, "successful_retirements": count, "step_calls": count,
             "execution_calls": count, "sealed": True, "shared_execution_calls": count,
             "terminal_reason": "InventedContinuationCheckpoint", "external_exit": None, "first_fault": None}
    report = {"mode": "ClosedInventedCallerCompositeContinuation", "path": parts["path"],
              "programs": program_claims(), "stage": "Continuation", "entry": parts["entry"],
              "current": parts["current"], "steps": steps, "tickets": tickets, "commits": commits,
              "pending": None, "tickets_issued": 2, "tickets_consumed": 2, "tickets_refused": 0,
              "ticket_refusals": [], "checkpoint": parts["checkpoint_pc"], "completed": True,
              "composite_direct_j_count": 1, "journal_stages": stage_stamps, "audit": audit}
    return {"kind": "transfer_observation", "case_id": request["case_id"], "family": request["family"],
            "internal_sf": request["internal_sf"], "accepted": True, "error": None, "report": report,
            "actual_successful_step_returns": count, "cpu_instances": 1, "bus_instances": 1,
            "data_initializations": 1, "functional_transitions": 1, "transfer_execution_attempts": 1,
            "full_production_transfer_executions": 1, "full_production_composite_executions": 1,
            "original_rom_executions": 0, "firmware_ready": False}
