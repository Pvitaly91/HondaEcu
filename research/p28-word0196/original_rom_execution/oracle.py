"""Independent original-site expectations, never an instruction executor.

Architectural math is the unchanged M2bk structured/C11 reference, with only
coordinate adaptation and removal of the synthetic direct J. The original
instruction path ends by natural fallthrough before the P2 instruction. No ROM
reader, CPU, decoder, subprocess, or runtime observation supplies expected math.
Full observations remain canonical; instrumentation fields have separate strict
source-level invariants, not a claim of hardware timing or native input ownership.
"""

from copy import deepcopy
from hashlib import sha256
import re

import synthetic_execution_protocol_oracle as reference
import independent_encoder as encoder
from . import corpus


FORM = {
    0x556F: (747, "LB A, off N8"), 0x5571: (2198, "SLLB A"),
    0x5572: (1862, "ROLB off N8"), 0x5575: (739, "LB A, r0"),
    0x5576: (333, "ANDB A, off N8"), 0x5578: (498, "CMP off N8, #N16"),
    0x557D: (719, "JLT rel8"), 0x557F: (1504, "MOVB r1, off N8"),
    0x5582: (349, "ANDB off N8, A"), 0x5585: (716, "JBS off N8.7, rel8"),
    0x5588: (714, "JBS off N8.5, rel8"), 0x558B: (349, "ANDB off N8, A"),
    0x558E: (1678, "ORB off N'8, #N8"), 0x5592: (747, "LB A, off N8"),
    0x5594: (1619, "ORB A, #N8"), 0x55BF: (738, "LB A, #N8"),
    0x55C1: (2301, "STB A, off N8"), 0x55C3: (2301, "STB A, off N8"),
}
LENGTHS = dict(zip(FORM, (2, 1, 3, 1, 2, 5, 2, 3, 3, 3, 3, 3, 4, 2, 2, 2, 2, 2)))
SHA = re.compile(r"[0-9a-f]{64}\Z")


def _equal(actual, expected, path):
    if type(actual) is not type(expected):
        raise ValueError("ExactTypeMismatch:" + path)
    if type(expected) is dict:
        if set(actual) != set(expected):
            raise ValueError("ExactKeysMismatch:" + path)
        for key in expected:
            _equal(actual[key], expected[key], path + "/" + str(key))
    elif type(expected) is list:
        if len(actual) != len(expected):
            raise ValueError("ExactLengthMismatch:" + path)
        for index, (left, right) in enumerate(zip(actual, expected)):
            _equal(left, right, path + "/" + str(index))
    elif actual != expected:
        raise ValueError("ExactValueMismatch:" + path)


def _closed(value, fields, path):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError("ClosedObservationShape:" + path)


def _pc(pc, kind):
    return pc + (corpus.PUBLIC_PC_DELTA if kind == "public_fixture" else 0)


def _address(address, kind):
    return corpus.PUBLIC_DATA.get(address, address) if kind == "public_fixture" else address


def _reference_input(case):
    entry = case["entry"]
    return {"id": case["case_id"], "classification": reference.PROVENANCE,
            "entry": {"pc": 0x1000, "a": entry["a"], "al": entry["al"], "ah": entry["ah"],
                      "psw": entry["psw"], **{name: int(entry[name]) for name in ("cf", "zf", "hc", "dd")},
                      "otherPsw": entry["other_psw"], "lrb": entry["lrb"], "scb": entry["scb"],
                      "ssp": entry["ssp"], "pointingBanks": [[bank[name] for name in ("x1", "x2", "dp", "usp")]
                                                                  for bank in entry["pointing_banks"]],
                      "sf": deepcopy(reference.UNKNOWN_SF), "halted": False},
            "data": {f"{int(address):04X}": value for address, value in case["data"].items()},
            "localAliases": {"r": list(entry["local_r"]), "er": list(entry["local_er"])}}


def _cpu(state, pc, case, instructions, cycles):
    return {"pc": pc, "a": state["a"], "ssp": state["ssp"], "lrb": state["lrb"],
            **{name: bool(state[name]) for name in ("cf", "zf", "hc", "dd")},
            "sf": case["internal_sf"], "psw_other": state["psw"] & 0x0337,
            "cycles": cycles, "instructions": instructions, "halted": False}


def _seed_map(case, kind):
    result = {_address(int(key), kind): value for key, value in case["data"].items()}
    for bank, words in enumerate(case["entry"]["pointing_banks"]):
        for slot, name in enumerate(("x1", "x2", "dp", "usp")):
            address = 0x80 + bank * 8 + slot * 2
            result[address], result[address + 1] = words[name] & 255, words[name] >> 8
    return result


def expected_case(case, program_kind="private"):
    """Complete independently expected original-site state and DATA effects.

    Unknown ambient RAM has a relational frame condition, not invented native
    expected bytes. Host counters are separately labelled implementation stats.
    """
    corpus.validate_case(case)
    if program_kind not in ("private", "public_fixture"):
        raise ValueError("ClosedProgramKind")
    model = reference.reference_case(_reference_input(case))
    rows = model["trace"][:-1]
    if model["path"] != case["path"] or len(rows) != case["budget"]:
        raise ValueError("IndependentOriginalPathConflict")
    memory = _seed_map(case, program_kind)
    initial_memory = deepcopy(memory)
    steps, accesses = [], []
    cycles, write_ordinal = 0, 0
    for index, row in enumerate(rows):
        native_pc = row["logicalId"]
        pc = _pc(native_pc, program_kind)
        next_pc = _pc(rows[index + 1]["logicalId"] if index + 1 < len(rows) else model["terminalPc"], program_kind)
        before = {"cpu": _cpu(row["stateBefore"], pc, case, index, cycles),
                  "owned_ram": {str(key): value for key, value in memory.items()},
                  "full_psw": row["stateBefore"]["psw"]}
        events = []
        for read in row["dataReads"]:
            events.append({"pc": pc, "instruction_index": FORM[native_pc][0],
                           "address": _address(read["address"], program_kind), "width": read["widthBits"],
                           "operation": "Read", "requested_value": None, "value": read["value"],
                           "old_value": None, "write_ordinal": None, "same_value": None})
        for write in row["dataWrites"]:
            address = _address(write["address"], program_kind)
            events.append({"pc": pc, "instruction_index": FORM[native_pc][0], "address": address,
                           "width": 8, "operation": "Write", "requested_value": write["value"],
                           "value": write["value"], "old_value": write["oldValue"],
                           "write_ordinal": 48 + write_ordinal, "same_value": write["sameValue"]})
            write_ordinal += 1
            memory[address] = write["value"]
        cycles += 2 * row["length"] + (4 if row["branchTaken"] is True else 0)
        after = {"cpu": _cpu(row["stateAfter"], next_pc, case, index + 1, cycles),
                 "owned_ram": {str(key): value for key, value in memory.items()},
                 "full_psw": row["stateAfter"]["psw"]}
        steps.append({"index": index + 1, "native_site_identity": f"{native_pc:04X}",
                      "pc": pc, "next_pc": next_pc, "form": row["form"],
                      "decoded_index": FORM[native_pc][0], "mnemonic": FORM[native_pc][1],
                      "length": row["length"], "branch_taken": row["branchTaken"],
                      "before": before, "after": after, "data_events": events})
        accesses.extend(events)
    return {"classification": "IndependentOriginalSiteReference_NoCpuObservation",
            "case_id": case["case_id"], "program_kind": program_kind, "path": model["path"],
            "entry": steps[0]["before"], "terminal": steps[-1]["after"], "steps": steps,
            "ordered_data_events": accesses, "instruction_count": len(rows),
            "logical_read_count": sum(e["operation"] == "Read" for e in accesses),
            "write_count": write_ordinal, "stop_before_pc": steps[-1]["next_pc"],
            "initial_owned_ram": {str(key): value for key, value in initial_memory.items()},
            "ambient_ram_rule": "EveryUnownedBytePreservedFromActualEntry_NoNativeValueClaim",
            "host_counter_rule": "ProductionInstrumentation_2xLengthPlus4TakenConditional_NotHardwareTime",
            "native_input_ownership": False, "physical_sf": deepcopy(corpus.UNKNOWN_SF),
            "actual_cpu_executions_by_oracle": 0}


def _public_requests():
    """Typed, independently encoded, explicitly invented fixture only."""
    E, F = encoder, encoder.FormId
    A, P, T = E.AccumulatorA, E.PageOffset8, E.TargetPC16
    requests = [
        (0x556F, F.LB_A_PAGE, (A(), P(0x92))), (0x5571, F.SLLB_A, (A(),)),
        (0x5572, F.ROLB_PAGE, (P(0x92),)), (0x5575, F.LB_A_R0, (A(), E.Register0())),
        (0x5576, F.ANDB_A_PAGE, (A(), P(0x92))),
        (0x5578, F.CMP_PAGE_IMM16, (E.EvenPageOffset8(0x9A), E.Immediate16(192))),
        (0x557D, F.JLT_REL8, (T(_pc(0x55BF, "public_fixture")),)),
        (0x557F, F.MOVB_R1_PAGE, (E.Register1(), P(0x1B))),
        (0x5582, F.ANDB_PAGE_A, (P(0x1B), A())),
        (0x5585, F.JBS_PAGE_BIT7, (E.PageBit7(0x2D), T(_pc(0x5592, "public_fixture")))),
        (0x5588, F.JBS_PAGE_BIT5, (E.PageBit5(0x2E), T(_pc(0x5592, "public_fixture")))),
        (0x558B, F.ANDB_PAGE_A, (P(0x93), A())),
        (0x558E, F.ORB_PAGE_IMM8, (P(0x2D), E.Immediate8(1))),
        (0x5592, F.LB_A_PAGE, (A(), P(0x93))),
        (0x5594, F.ORB_A_IMM8, (A(), E.Immediate8(240))),
        (0x55BF, F.LB_A_IMM8, (A(), E.Immediate8(15))),
        (0x55C1, F.STB_A_PAGE, (A(), P(0x1B))),
        (0x55C3, F.STB_A_PAGE, (A(), P(0x93))),
    ]
    return [E.EncoderRequest(form, operands, 0, _pc(pc, "public_fixture")) for pc, form, operands in requests]


def public_program_identity():
    """Freeze independent invented PROGRAM identity before any Rust invocation.

    Bytes exist only transiently in memory and are never a native/OEM fixture.
    There is no generic program input, target execution, file or output payload.
    """
    payload, hashes = bytearray([0xA5] * 86), {}
    for request in _public_requests():
        encoded = encoder.encode_instruction(request)
        if type(encoded) is not encoder.EncodedInstruction:
            raise ValueError("IndependentPublicFixtureEncodingRefused")
        start = request.origin_pc - 0x6000
        payload[start:start + encoded.length] = encoded.encoded_bytes
        hashes[str(request.origin_pc)] = sha256(encoded.encoded_bytes).hexdigest()
    return {"program_base": 0x6000, "program_end_exclusive": 0x6056,
            "program_sha256": sha256(payload).hexdigest(), "source_binding": None,
            "selected_extent_sha256": hashes}


def _snapshot(actual, expected, entry_ram, path):
    _closed(actual, ("cpu", "ram", "ram_range"), path)
    _equal(actual["ram_range"], [128, 4096], path + "/ram_range")
    _equal(actual["cpu"], expected["cpu"], path + "/cpu")
    ram = actual["ram"]
    if type(ram) is not list or len(ram) != 3968 or any(type(v) is not int or not 0 <= v <= 255 for v in ram):
        raise ValueError("CompleteRamSnapshotRequired:" + path)
    for address in range(128, 4096):
        key = str(address)
        value = expected["owned_ram"].get(key, entry_ram[address - 128])
        _equal(ram[address - 128], value, path + "/ram/" + key)


def _seed_events(case, kind):
    logical, raw = [], []
    memory = {}
    seeds = [(int(address), 8, value) for address, value in corpus.wire_case(case, kind)["data"].items()]
    seeds.sort()
    for bank, words in enumerate(case["entry"]["pointing_banks"]):
        seeds.extend((0x80 + bank * 8 + slot * 2, 16, words[name])
                     for slot, name in enumerate(("x1", "x2", "dp", "usp")))
    for address, width, value in seeds:
        ordinal = len(logical)
        old = sum(memory.get(address + offset, 0xA5) << (8 * offset) for offset in range(width // 8))
        logical.append({"ordinal": ordinal, "phase": "Seed", "pc": _pc(0x556F, kind), "instruction_index": None,
                        "address": address, "width": width, "operation": "Write", "requested_value": value,
                        "value": value, "old_value": old, "write_ordinal": ordinal,
                        "same_value": old == value, "serviced": True, "refusal": None})
        for offset in range(width // 8):
            byte, old_byte = (value >> (8 * offset)) & 255, memory.get(address + offset, 0xA5)
            raw.append({"ordinal": len(raw), "logical_ordinal": ordinal, "address": address + offset,
                        "operation": "Write", "requested_value": byte, "value": byte,
                        "old_value": old_byte, "write_ordinal": len(raw), "same_value": old_byte == byte,
                        "serviced": True, "refusal": None})
            memory[address + offset] = byte
    return logical, raw


def _data_expected(case, expected, kind):
    logical, raw = _seed_events(case, kind)
    spans = []
    raw_writes = len(raw)
    for step in expected["steps"]:
        left = [len(logical), len(raw)]
        for source in step["data_events"]:
            ordinal = len(logical)
            event = {"ordinal": ordinal, "phase": "Functional", **source,
                     "serviced": True, "refusal": None}
            logical.append(event)
            for offset in range(source["width"] // 8):
                writing = source["operation"] == "Write"
                value = (source["value"] >> (8 * offset)) & 255
                old = None if not writing else (source["old_value"] >> (8 * offset)) & 255
                raw.append({"ordinal": len(raw), "logical_ordinal": ordinal,
                            "address": source["address"] + offset, "operation": source["operation"],
                            "requested_value": value if writing else None, "value": value,
                            "old_value": old, "write_ordinal": raw_writes if writing else None,
                            "same_value": old == value if writing else None, "serviced": True, "refusal": None})
                raw_writes += int(writing)
        spans.append({"logical_span": [left[0], len(logical)], "raw_span": [left[1], len(raw)]})
    return logical, raw, spans


def _decoded(step, kind):
    pc = int(step["native_site_identity"], 16)
    n8, n8_alt, n16, rel8 = 0, 0, 0, 0
    role = {0x556F: 0x18E, 0x5572: 0x18E, 0x5576: 0x18E, 0x5578: 0x196,
            0x557F: 0x117, 0x5582: 0x117, 0x5585: 0x12A, 0x5588: 0x124,
            0x558B: 0x18F, 0x5592: 0x18F, 0x55C1: 0x117, 0x55C3: 0x18F}
    if pc in role:
        n8 = _address(role[pc], kind) & 255
    if pc == 0x5578:
        n16 = 192
    if pc in (0x557D, 0x5585, 0x5588):
        rel8 = {0x557D: 64, 0x5585: 10, 0x5588: 7}[pc]
    if pc == 0x558E:
        n8, n8_alt = 1, _address(0x12A, kind) & 255
    if pc in (0x5594, 0x55BF):
        n8 = 240 if pc == 0x5594 else 15
    return {"index": step["decoded_index"], "mnemonic": step["mnemonic"], "len": step["length"],
            "dd_before": step["before"]["cpu"]["dd"], "dd_after": step["after"]["cpu"]["dd"],
            "dd_after_option": False if pc in (0x556F, 0x5575, 0x5592, 0x55BF) else None,
            "cycles": 2 * step["length"], "n8": n8, "n8_alt": n8_alt, "n16": n16,
            "n16_alt": 0, "s8": 0, "rel8": rel8, "addr16": 0}


def _permissions(expected):
    reads, writes = {}, {}
    for step in expected["steps"]:
        for event in step["data_events"]:
            key = (event["address"], event["width"])
            if event["operation"] == "Read":
                reads[key] = {"address": key[0], "width": key[1]}
            else:
                writes[key] = {"access": {"address": key[0], "width": key[1]},
                               "rmw_required": step["native_site_identity"] in ("5572", "5582", "558B", "558E")}
    return {"reads": [reads[key] for key in sorted(reads)], "writes": [writes[key] for key in sorted(writes)],
            "raw_reads": sorted({a + i for a, w in reads for i in range(w // 8)}),
            "raw_writes": sorted({a + i for a, w in writes for i in range(w // 8)})}


def _program_events(events, steps, identity):
    if type(events) is not list:
        raise ValueError("ProgramEventsListRequired")
    cursor = 0
    for step_index, (actual, expected) in enumerate(steps):
        span = actual["program_span"]
        if type(span) is not list or len(span) != 2 or any(type(v) is not int for v in span) \
                or span[0] != cursor or not cursor < span[1] <= len(events):
            raise ValueError("ProgramSpanClosedPartition")
        selected = []
        saw_selected = False
        for event in events[span[0]:span[1]]:
            _closed(event, ("ordinal", "pc", "address", "segment_offset", "instruction_offset",
                           "acquired_purpose", "selection_association", "selected_length", "serviced", "refusal"), "PROGRAM")
            _equal(event["ordinal"], cursor, "PROGRAM/ordinal")
            _equal(event["pc"], expected["pc"], "PROGRAM/pc")
            address = event["address"]
            if type(address) is not int or not identity["program_base"] <= address < identity["program_end_exclusive"]:
                raise ValueError("ProgramAccessOutsideVerifiedSegment")
            _equal(event["segment_offset"], address - identity["program_base"], "PROGRAM/segment_offset")
            _equal(event["instruction_offset"], address - expected["pc"], "PROGRAM/instruction_offset")
            _equal(event["selected_length"], expected["length"], "PROGRAM/selected_length")
            _equal(event["serviced"], True, "PROGRAM/serviced")
            _equal(event["refusal"], None, "PROGRAM/refusal")
            purpose = event["acquired_purpose"]
            if purpose == "ArchitecturalSelectedFetch":
                saw_selected = True
                _equal(event["selection_association"], None, "PROGRAM/selected_association")
                selected.append(address)
            elif purpose == "DecoderProbe" and not saw_selected:
                _equal(event["selection_association"], "SelectedExtent" if address - expected["pc"] < expected["length"]
                       else "DecoderLookahead", "PROGRAM/probe_association")
            else:
                raise ValueError("ProgramPurposeOrderOrUnexpectedProbe")
            cursor += 1
        _equal(selected, list(range(expected["pc"], expected["pc"] + expected["length"])), "PROGRAM/exact_selected_extent")
    _equal(cursor, len(events), "PROGRAM/no_unassigned_or_terminal_fetch")


def compare_observation(case, actual, program_kind="private", program_identity=None):
    """Reject first exact state/effect/instrumentation disagreement.

    Full raw observations, not this success summary, belong in canonical records.
    A successful comparison grants neither strict native ownership nor a physical
    ECU claim. PROGRAM lookahead is recorded separately from selected execution.
    """
    expected = expected_case(case, program_kind)
    if program_identity is None and program_kind == "public_fixture":
        program_identity = public_program_identity()
    _closed(program_identity, ("program_base", "program_end_exclusive", "program_sha256",
                              "source_binding", "selected_extent_sha256"), "program_identity")
    identity = program_identity
    for digest in [identity["program_sha256"], *identity["selected_extent_sha256"].values()]:
        if type(digest) is not str or not SHA.fullmatch(digest):
            raise ValueError("FrozenIndependentProgramShaRequired")
    _equal(set(identity["selected_extent_sha256"]), {str(_pc(pc, program_kind)) for pc in FORM}, "identity/closed18")
    _equal(identity["program_base"], _pc(0x556F, program_kind), "identity/base")
    _equal(identity["program_end_exclusive"], _pc(0x55C5, program_kind), "identity/end")
    if program_kind == "public_fixture":
        _equal(identity, public_program_identity(), "identity/public_independent_encoding")
    _closed(actual, ("kind", "case_id", "family", "internal_sf", "accepted", "error",
                     "actual_successful_step_returns", "report"), "observation")
    for key, value in (("kind", "original_rom_observation"), ("case_id", case["case_id"]),
                       ("family", case["family"]), ("internal_sf", case["internal_sf"]),
                       ("accepted", True), ("error", None), ("actual_successful_step_returns", case["budget"])):
        _equal(actual[key], value, key)
    report = actual["report"]
    _closed(report, ("classification", "source_binding", "program_node_count", "path", "entry", "current",
                     "full_psw", "steps", "completed", "stop_before_pc", "audit"), "report")
    classification = corpus.MODE if program_kind == "private" else "ExplicitInventedPublicFixture"
    for key, value in (("classification", classification), ("source_binding", identity["source_binding"]),
                       ("program_node_count", 18), ("path", case["path"]), ("completed", True),
                       ("stop_before_pc", expected["stop_before_pc"]), ("full_psw", expected["terminal"]["full_psw"])):
        _equal(report[key], value, "report/" + key)
    if type(report["steps"]) is not list or len(report["steps"]) != case["budget"]:
        raise ValueError("ExactRetiredInstructionRecordsRequired")
    ram = report["entry"]["ram"]
    _snapshot(report["entry"], expected["entry"], ram, "entry")
    _snapshot(report["current"], expected["terminal"], ram, "terminal")
    logical, raw, spans = _data_expected(case, expected, program_kind)
    for index, (step, obligation) in enumerate(zip(report["steps"], expected["steps"])):
        _closed(step, ("index", "node_identity", "full_psw_before", "full_psw_after", "before", "after",
                       "outcome", "program_span", "logical_span", "raw_span"), "step")
        _equal(step["index"], index + 1, "step/index")
        _equal(step["node_identity"], f"ClosedSite_{obligation['pc']:04X}", "step/node_identity")
        for which in ("before", "after"):
            _snapshot(step[which], obligation[which], ram, f"step/{index}/{which}")
            _equal(step["full_psw_" + which], obligation[which]["full_psw"], "step/full_psw_" + which)
        for field in ("logical_span", "raw_span"):
            _equal(step[field], spans[index][field], "step/" + field)
        outcome = {"pc_before": obligation["pc"], "pc_after": obligation["next_pc"],
                   "decoded_index": obligation["decoded_index"], "mnemonic": obligation["mnemonic"],
                   "len": obligation["length"], "decoded": _decoded(obligation, program_kind),
                   "selected_extent": [obligation["pc"], obligation["pc"] + obligation["length"]],
                   "selected_extent_sha256": identity["selected_extent_sha256"][str(obligation["pc"])],
                   "retired": True, "external_exit": None}
        _equal(step["outcome"], outcome, "step/outcome")
    audit = report["audit"]
    _closed(audit, ("entry_pc", "current_pc", "program_base", "program_end_exclusive", "program_sha256",
                    "program_events", "data_events", "raw_data_events", "diagnostic_events", "data_admission_refusals",
                    "permissions", "phase", "budget", "successful_retirements", "step_calls", "execution_calls",
                    "shared_execution_calls", "sealed", "terminal_reason", "external_exit", "first_fault"), "audit")
    fixed = {"entry_pc": expected["entry"]["cpu"]["pc"], "current_pc": expected["stop_before_pc"],
             **{key: identity[key] for key in ("program_base", "program_end_exclusive", "program_sha256")},
             "data_events": logical, "raw_data_events": raw, "data_admission_refusals": [],
             "permissions": _permissions(expected), "phase": "Sealed", "budget": case["budget"],
             "successful_retirements": case["budget"], "step_calls": case["budget"],
             "execution_calls": case["budget"], "shared_execution_calls": case["budget"], "sealed": True,
             "terminal_reason": "OriginalStopBeforeReached", "external_exit": None, "first_fault": None}
    for key, value in fixed.items():
        _equal(audit[key], value, "audit/" + key)
    diagnostics = [{"ordinal": index, "kind": "RawRamSnapshot", "range": [128, 4096], "byte_count": 3968}
                   for index in range(2 * case["budget"] + 2)]
    _equal(audit["diagnostic_events"], diagnostics, "audit/diagnostics")
    _program_events(audit["program_events"], list(zip(report["steps"], expected["steps"])), identity)
    return {"passed": True, "expected": expected,
            "comparison": {"classification": "IndependentOriginalSiteStateEffectsAndCompleteAuditValidated",
                           "firstMismatch": None, "retirements": case["budget"],
                           "path": case["path"], "nativeInputOwnership": False,
                           "physicalExecutionClaimed": False, "omittedActualFields": []}}


def compare_historical_subset(case, observation, obligation):
    """Qualified old source-CPU subset, not whole-state/native ownership equality."""
    if case["case_id"] not in obligation["case_ids"] or case["path"] != obligation["path"]:
        raise ValueError("HistoricalTechnicalCaseBindingMismatch")
    report = observation["report"]
    for label, snapshot, old in (("entry", report["entry"], obligation["entry_snapshot"]),
                                 ("exit", report["current"], obligation["exit_snapshot"])):
        cpu = snapshot["cpu"]
        _equal({"pc": cpu["pc"], "accumulator": cpu["a"], "lrb": cpu["lrb"], "ssp": cpu["ssp"]},
               {key: old[key] for key in ("pc", "accumulator", "lrb", "ssp")}, "historical/" + label)
        psw = cpu["psw_other"] | corpus.READS_ONE | sum(int(cpu[name]) << shift for name, shift in
                                                       (("cf", 15), ("zf", 14), ("hc", 13), ("dd", 12)))
        _equal(psw, old["psw"], "historical/" + label + "/psw")
        _equal(snapshot["ram"][0x108 - 128:0x110 - 128], old["registers"], "historical/locals")
        for slot, name in enumerate(("x1", "x2", "dp", "usp")):
            address = 0x80 + (old["psw"] & 7) * 8 + slot * 2
            words = snapshot["ram"][address - 128:address - 126]
            _equal(words[0] | words[1] << 8, old[name], "historical/" + name)
    _equal([step["outcome"]["pc_before"] for step in report["steps"]], obligation["native_pc_sequence"], "historical/pcs")
    writes = [{"pc": event["pc"], "address": event["address"], "width": event["width"], "value": event["value"]}
              for event in report["audit"]["data_events"] if event["phase"] == "Functional" and event["operation"] == "Write"]
    _equal(writes, obligation["ordered_writes"], "historical/ordered_writes")
    return {"passed": True, "classification": "HistoricalQualifiedSubsetOnly_TechnicalUnknownCompletionsRetained",
            "path": case["path"], "oldAndNewCpuSameInstance": False, "strictNativeOwnershipEstablished": False}
