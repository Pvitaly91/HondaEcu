"""Independent M2bu source-level expectations, never a CPU executor.

The six predecessor formulas come from M2y and the immutable manufacturer-bound
M2bs context contract. Their resulting *expected* state enters the unchanged
M2bk/M2av structured mathematical reference. This is offline expectation
composition, never state transfer between actual machines or an execution seam.
No ROM, production decoder, process, Rust result or actual observation supplies
the expected math. Public encoding is transient and independently typed.
"""
from copy import deepcopy
from hashlib import sha256

import independent_encoder as encoder
from original_rom_boundary.decode import decode_extent
from original_rom_execution import oracle as previous
from . import corpus

PREFIX_FORM = {
    0x54F5: (703, "JBR off N8.2, rel8", "jbr-page-bit2", 3),
    0x54F8: (1375, "MOVB r0, #N8", "movb-r0-imm8", 2),
    0x54FA: (732, "L A, off N8", "l-a-page", 2),
    0x54FC: (2284, "ST A, er1", "st-a-er1", 1),
    0x54FD: (563, "CMPB off N'8, #N8", "cmpb-page-imm8", 4),
    0x5501: (718, "JNE rel8", "jne-rel8", 2),
}
FORM = {**{pc: (row[0], row[1]) for pc, row in PREFIX_FORM.items()}, **previous.FORM}
LENGTHS = {**{pc: row[3] for pc, row in PREFIX_FORM.items()}, **previous.LENGTHS}
_equal, _closed = previous._equal, previous._closed


def diagnostic_snapshot_count(retirements):
    """Source-level M2bu wrapper instrumentation, never physical ECU work.

    Two constructor snapshots, four per successful step (outer continuity,
    inner before/after, retained last-state update), two at report closure.
    This deliberately differs from the unchanged M2bt 2*N+2 lifecycle.
    """
    if type(retirements) is not int or not 1 <= retirements <= 21:
        raise ValueError("ClosedM2buDiagnosticRetirementDomain")
    return 4 * retirements + 4


def _pc(pc, kind):
    return pc + (corpus.PUBLIC_PC_DELTA if kind == "public_fixture" else 0)


def _address(address, kind):
    return corpus.PUBLIC_DATA.get(address, address) if kind == "public_fixture" else address


def _flag(psw, bit, value):
    return (psw & ~(1 << bit)) | (int(value) << bit)


def _seed_map(case, kind):
    memory = {_address(int(key), kind): value for key, value in case["data"].items()}
    for bank, words in enumerate(case["entry"]["pointing_banks"]):
        for slot, name in enumerate(("x1", "x2", "dp", "usp")):
            address, word = 0x80 + bank * 8 + slot * 2, words[name]
            memory[address], memory[address + 1] = word & 255, word >> 8
    return memory


def expected_case(case, program_kind="private"):
    corpus.validate_case(case)
    if program_kind not in ("private", "public_fixture"):
        raise ValueError("ClosedM2buProgramKind")
    memory = _seed_map(case, program_kind)
    initial_memory = deepcopy(memory)
    entry = case["entry"]
    a, psw, current_pc = entry["a"], entry["psw"], corpus.ENTRY_PC
    instructions = cycles = write_count = 0
    steps, accesses = [], []

    def value(address, width=8):
        address = _address(address, program_kind)
        return sum(memory[address + i] << (8 * i) for i in range(width // 8))

    def snapshot():
        return {"cpu": {"pc": _pc(current_pc, program_kind), "a": a, "ssp": entry["ssp"],
            "lrb": entry["lrb"], "cf": bool(psw & 0x8000), "zf": bool(psw & 0x4000),
            "hc": bool(psw & 0x2000), "dd": bool(psw & 0x1000), "sf": case["internal_sf"],
            "psw_other": psw & 0x0337, "cycles": cycles, "instructions": instructions, "halted": False},
            "owned_ram": {str(key): val for key, val in memory.items()}, "full_psw": psw}

    def note(pc, form, next_pc, *, new_a=None, new_psw=None, reads=(), writes=(), branch=None):
        nonlocal a, psw, current_pc, instructions, cycles, write_count
        if current_pc != pc:
            raise ValueError("IndependentContinuousExpectedPcSequenceConflict")
        before = snapshot()
        events = []
        for address, width in reads:
            events.append({"pc": _pc(pc, program_kind), "instruction_index": FORM[pc][0],
                "address": _address(address, program_kind), "width": width, "operation": "Read",
                "requested_value": None, "value": value(address, width), "old_value": None,
                "write_ordinal": None, "same_value": None})
        for address, width, written in writes:
            old, mapped = value(address, width), _address(address, program_kind)
            events.append({"pc": _pc(pc, program_kind), "instruction_index": FORM[pc][0],
                "address": mapped, "width": width, "operation": "Write", "requested_value": written,
                "value": written, "old_value": old, "write_ordinal": 48 + write_count, "same_value": old == written})
            for offset in range(width // 8):
                memory[mapped + offset] = (written >> (8 * offset)) & 255
            write_count += 1
        if new_a is not None:
            a = new_a
        if new_psw is not None:
            psw = new_psw
        current_pc = next_pc
        cycles += 2 * LENGTHS[pc] + (4 if branch is True else 0)
        instructions += 1
        steps.append({"index": instructions, "native_site_identity": f"{pc:04X}",
            "pc": _pc(pc, program_kind), "next_pc": _pc(next_pc, program_kind), "form": form,
            "decoded_index": FORM[pc][0], "mnemonic": FORM[pc][1], "length": LENGTHS[pc],
            "branch_taken": branch, "before": before, "after": snapshot(), "data_events": events})
        accesses.extend(events)

    bit_clear = not bool(value(0x0128) & 4)
    note(0x54F5, "jbr-page-bit2", 0x5533 if bit_clear else 0x54F8,
         reads=((0x0128, 8),), branch=bit_clear)
    if not bit_clear:
        note(0x54F8, "movb-r0-imm8", 0x54FA, writes=((0x0108, 8, 255),))
        word = value(0x0196, 16)
        note(0x54FA, "l-a-page", 0x54FC, new_a=word,
             new_psw=_flag(_flag(psw, 14, word == 0), 12, True), reads=((0x0196, 16),))
        note(0x54FC, "st-a-er1", 0x54FD, writes=((0x010A, 16, a),))
        q = value(0x0117)
        note(0x54FD, "cmpb-page-imm8", 0x5501,
             new_psw=_flag(_flag(psw, 15, q < 15), 14, q == 15), reads=((0x0117, 8),))
        taken = not bool(psw & 0x4000)
        note(0x5501, "jne-rel8", 0x556F if taken else 0x5503, branch=taken)
        if taken:
            # Only independent EXPECTED mathematical state crosses this adapter.
            # The actual executor must remain one CPU/Bus and never use this as
            # a seed, callback, JSON machine transfer or reset at556F.
            post = corpus._as_previous_domain(case)
            post["data"] = {str(addr): value(addr) for addr in corpus.INVENTORY}
            post["entry"].update(a=a, al=a & 255, ah=a >> 8, psw=psw,
                cf=bool(psw & 0x8000), zf=bool(psw & 0x4000), hc=bool(psw & 0x2000),
                dd=bool(psw & 0x1000), other_psw=psw & 0x0FFF)
            local = [value(0x0108 + i) for i in range(8)]
            post["entry"].update(local_r=local,
                local_er=[local[2 * i] | local[2 * i + 1] << 8 for i in range(4)])
            reference = previous.reference.reference_case(previous._reference_input(post))
            suffix = reference["trace"][:-1]  # No synthetic direct-J instruction.
            if reference["path"] != case["path"] or len(suffix) + 6 != case["budget"]:
                raise ValueError("IndependentM2avSuffixPathConflict")
            for index, row in enumerate(suffix):
                next_pc = suffix[index + 1]["logicalId"] if index + 1 < len(suffix) else reference["terminalPc"]
                for read in row["dataReads"]:
                    if read["value"] != value(read["address"], read["widthBits"]):
                        raise ValueError("IndependentPrefixSuffixDataRelationConflict")
                note(row["logicalId"], row["form"], next_pc, new_a=row["stateAfter"]["a"],
                     new_psw=row["stateAfter"]["psw"],
                     reads=tuple((event["address"], event["widthBits"]) for event in row["dataReads"]),
                     writes=tuple((event["address"], 8, event["value"]) for event in row["dataWrites"]),
                     branch=row["branchTaken"])
    if instructions != case["budget"] or current_pc != corpus.TERMINALS[case["path"]]:
        raise ValueError("IndependentExactBoundaryBudgetConflict")
    positive = case["path"] in "ABCD" and len(case["path"]) == 1
    predecessor_count = 6 if not bit_clear else 1
    return {"classification": "IndependentEntryToExitReference_NoCpuObservation", "case_id": case["case_id"],
        "program_kind": program_kind, "path": case["path"], "entry": steps[0]["before"],
        "terminal": steps[-1]["after"], "steps": steps, "ordered_data_events": accesses,
        "instruction_count": instructions, "native_predecessor_retirements": predecessor_count,
        "algorithm_retirements": instructions - predecessor_count, "positive_completed": positive,
        "boundary_only": not positive, "handoff_expected": positive,
        "logical_read_count": sum(event["operation"] == "Read" for event in accesses),
        "write_count": write_count, "stop_before_pc": _pc(current_pc, program_kind),
        "initial_owned_ram": {str(key): val for key, val in initial_memory.items()},
        "ambient_ram_rule": "EveryUnownedBytePreservedFromActualEntry_NoNativeValueClaim",
        "host_counter_rule": "ProductionInstrumentation_2xLengthPlus4TakenConditional_NotHardwareTime",
        "data0196_generation": "TechnicalInitialSeedPair_No05ebExecutionOrNativeGenerationOwnerClaim",
        "er1_suffix_read_claimed": False, "native_input_ownership": False,
        "physical_sf": deepcopy(corpus.UNKNOWN_SF), "actual_cpu_executions_by_oracle": 0}


def _public_prefix_extent(pc):
    """Manufacturer code cells plus invented operands, never a copied ROM cell."""
    origin = _pc(pc, "public_fixture")
    if pc == 0x54F5:
        raw = bytes((0xDA, 0x30, _pc(0x5533, "public_fixture") - (origin + 3)))
    elif pc == 0x54F8:
        raw = bytes((0x98, 255))
    elif pc == 0x54FA:
        raw = bytes((0xE4, 0x9A))
    elif pc == 0x54FC:
        raw = bytes((0x89,))
    elif pc == 0x54FD:
        raw = bytes((0xC4, 0x1B, 0xC0, 15))
    elif pc == 0x5501:
        raw = bytes((0xCE, _pc(0x556F, "public_fixture") - (origin + 2)))
    else:
        raise ValueError("ClosedSixPredecessorPublicFormsRequired")
    # Frozen independent context recognizer, not production Rust decoding.
    for dd in ((1,) if pc == 0x54FC else (0, 1)):
        decoded = decode_extent(raw, origin, dd)
        if decoded["formId"] != PREFIX_FORM[pc][2] or decoded["length"] != PREFIX_FORM[pc][3]:
            raise ValueError("IndependentInventedPredecessorEncodingConflict")
    return raw


def public_program_identity():
    """Transient independently invented208-byte fixture; no returned payload."""
    payload, hashes = bytearray([0xA5] * 208), {}
    for pc in corpus.PREFIX:
        raw = _public_prefix_extent(pc)
        offset = pc - corpus.ENTRY_PC
        payload[offset:offset + len(raw)] = raw
        hashes[str(_pc(pc, "public_fixture"))] = sha256(raw).hexdigest()
    # Reuse only typed logical requests from the separately invented M2bt
    # fixture, with a distinct invented origin/target domain. Not OEM bytes.
    for request in previous._public_requests():
        native_pc = request.origin_pc - previous.corpus.PUBLIC_PC_DELTA
        operands = tuple(encoder.TargetPC16(item.value - previous.corpus.PUBLIC_PC_DELTA + corpus.PUBLIC_PC_DELTA)
            if type(item) is encoder.TargetPC16 else item for item in request.typed_operands)
        translated = encoder.EncoderRequest(request.reviewed_form_id, operands, request.incoming_dd,
                                            _pc(native_pc, "public_fixture"))
        encoded = encoder.encode_instruction(translated)
        if type(encoded) is not encoder.EncodedInstruction:
            raise ValueError("IndependentInventedSuffixEncodingRefused")
        offset = native_pc - corpus.ENTRY_PC
        payload[offset:offset + encoded.length] = encoded.encoded_bytes
        hashes[str(_pc(native_pc, "public_fixture"))] = sha256(encoded.encoded_bytes).hexdigest()
    return {"program_base": corpus.PUBLIC_BASE, "program_end_exclusive": corpus.PUBLIC_BASE + 208,
        "program_sha256": sha256(payload).hexdigest(), "source_binding": None, "selected_extent_sha256": hashes}


def _seed_events(case, kind):
    logical, raw, memory = [], [], {}
    seeds = sorted((int(address), 8, val) for address, val in corpus.wire_case(case, kind)["data"].items())
    for bank, words in enumerate(case["entry"]["pointing_banks"]):
        seeds.extend((0x80 + bank * 8 + slot * 2, 16, words[name])
            for slot, name in enumerate(("x1", "x2", "dp", "usp")))
    for address, width, val in seeds:
        ordinal = len(logical)
        old = sum(memory.get(address + i, 0xA5) << (8 * i) for i in range(width // 8))
        logical.append({"ordinal": ordinal, "phase": "Seed", "pc": _pc(corpus.ENTRY_PC, kind),
            "instruction_index": None, "address": address, "width": width, "operation": "Write",
            "requested_value": val, "value": val, "old_value": old, "write_ordinal": ordinal,
            "same_value": old == val, "serviced": True, "refusal": None})
        for i in range(width // 8):
            byte, old_byte = (val >> (8 * i)) & 255, memory.get(address + i, 0xA5)
            raw.append({"ordinal": len(raw), "logical_ordinal": ordinal, "address": address + i,
                "operation": "Write", "requested_value": byte, "value": byte, "old_value": old_byte,
                "write_ordinal": len(raw), "same_value": old_byte == byte, "serviced": True, "refusal": None})
            memory[address + i] = byte
    return logical, raw


def _data_expected(case, expected, kind):
    logical, raw = _seed_events(case, kind)
    spans, raw_writes = [], len(raw)
    for step in expected["steps"]:
        start = len(logical), len(raw)
        for event in step["data_events"]:
            ordinal = len(logical)
            logical.append({"ordinal": ordinal, "phase": "Functional", **event, "serviced": True, "refusal": None})
            for i in range(event["width"] // 8):
                writing = event["operation"] == "Write"
                val = (event["value"] >> (8 * i)) & 255
                old = (event["old_value"] >> (8 * i)) & 255 if writing else None
                raw.append({"ordinal": len(raw), "logical_ordinal": ordinal, "address": event["address"] + i,
                    "operation": event["operation"], "requested_value": val if writing else None, "value": val,
                    "old_value": old, "write_ordinal": raw_writes if writing else None,
                    "same_value": old == val if writing else None, "serviced": True, "refusal": None})
                raw_writes += int(writing)
        spans.append({"logical_span": [start[0], len(logical)], "raw_span": [start[1], len(raw)]})
    return logical, raw, spans


def _decoded(step, kind):
    pc = int(step["native_site_identity"], 16)
    if pc not in PREFIX_FORM:
        return previous._decoded(step, kind)
    n8 = n8_alt = rel8 = 0
    if pc == 0x54F5:
        n8, rel8 = _address(0x0128, kind) & 255, 59
    elif pc == 0x54F8:
        n8 = 255
    elif pc == 0x54FA:
        n8 = _address(0x0196, kind) & 255
    elif pc == 0x54FD:
        n8, n8_alt = 15, _address(0x0117, kind) & 255
    elif pc == 0x5501:
        rel8 = 108
    return {"index": step["decoded_index"], "mnemonic": step["mnemonic"], "len": step["length"],
        "dd_before": step["before"]["cpu"]["dd"], "dd_after": step["after"]["cpu"]["dd"],
        "dd_after_option": True if pc == 0x54FA else None, "cycles": 2 * step["length"],
        "n8": n8, "n8_alt": n8_alt, "n16": 0, "n16_alt": 0, "s8": 0, "rel8": rel8, "addr16": 0}


def compare_observation(case, actual, program_kind="private", program_identity=None):
    """Exact complete architectural/journal comparison; never alter expectations."""
    expected = expected_case(case, program_kind)
    if program_identity is None and program_kind == "public_fixture":
        program_identity = public_program_identity()
    _closed(program_identity, ("program_base", "program_end_exclusive", "program_sha256",
                              "source_binding", "selected_extent_sha256"), "program_identity")
    _equal(set(program_identity["selected_extent_sha256"]), {str(_pc(pc, program_kind)) for pc in FORM}, "program/closed24")
    _equal(program_identity["program_base"], _pc(corpus.ENTRY_PC, program_kind), "program/base")
    _equal(program_identity["program_end_exclusive"], _pc(0x55C5, program_kind), "program/end")
    for digest in [program_identity["program_sha256"], *program_identity["selected_extent_sha256"].values()]:
        if type(digest) is not str or previous.SHA.fullmatch(digest) is None:
            raise ValueError("FrozenProgramIdentityRequired")
    if program_kind == "public_fixture":
        _equal(program_identity, public_program_identity(), "program/independent_public_encoding")
    _closed(actual, ("kind", "case_id", "family", "internal_sf", "accepted", "error",
                    "actual_successful_step_returns", "report"), "observation")
    for key, val in (("kind", "entry_continuity_observation"), ("case_id", case["case_id"]),
        ("family", case["family"]), ("internal_sf", case["internal_sf"]), ("accepted", True),
        ("error", None), ("actual_successful_step_returns", case["budget"])):
        _equal(actual[key], val, key)
    report = actual["report"]
    _closed(report, ("classification", "source_binding", "program_node_count", "path", "entry", "current",
        "full_psw", "steps", "completed", "stop_before_pc", "audit", "positive_completed", "boundary_only",
        "actual_handoff_observed", "native_predecessor_retirements", "algorithm_retirements"), "report")
    fixed = {"classification": corpus.MODE if program_kind == "private" else "ExplicitInventedPublicEntryFixture",
        "source_binding": program_identity["source_binding"], "program_node_count": 24, "path": case["path"],
        "completed": True, "stop_before_pc": expected["stop_before_pc"], "full_psw": expected["terminal"]["full_psw"],
        "positive_completed": expected["positive_completed"], "boundary_only": expected["boundary_only"],
        "actual_handoff_observed": expected["handoff_expected"],
        "native_predecessor_retirements": expected["native_predecessor_retirements"],
        "algorithm_retirements": expected["algorithm_retirements"]}
    for key, val in fixed.items():
        _equal(report[key], val, "report/" + key)
    if type(report["steps"]) is not list or len(report["steps"]) != case["budget"]:
        raise ValueError("ExactContinuousRetirementRecordsRequired")
    ram = report["entry"]["ram"]
    previous._snapshot(report["entry"], expected["entry"], ram, "entry")
    previous._snapshot(report["current"], expected["terminal"], ram, "terminal")
    logical, raw, spans = _data_expected(case, expected, program_kind)
    for index, (step, obligation) in enumerate(zip(report["steps"], expected["steps"])):
        _closed(step, ("index", "node_identity", "full_psw_before", "full_psw_after", "before", "after",
                      "outcome", "program_span", "logical_span", "raw_span"), "step")
        _equal(step["index"], index + 1, "step/index")
        _equal(step["node_identity"], f"ClosedSite_{obligation['pc']:04X}", "step/node_identity")
        for which in ("before", "after"):
            previous._snapshot(step[which], obligation[which], ram, f"step/{index}/{which}")
            _equal(step["full_psw_" + which], obligation[which]["full_psw"], "step/psw_" + which)
        for field in ("logical_span", "raw_span"):
            _equal(step[field], spans[index][field], "step/" + field)
        outcome = {"pc_before": obligation["pc"], "pc_after": obligation["next_pc"],
            "decoded_index": obligation["decoded_index"], "mnemonic": obligation["mnemonic"], "len": obligation["length"],
            "decoded": _decoded(obligation, program_kind),
            "selected_extent": [obligation["pc"], obligation["pc"] + obligation["length"]],
            "selected_extent_sha256": program_identity["selected_extent_sha256"][str(obligation["pc"])],
            "retired": True, "external_exit": None}
        _equal(step["outcome"], outcome, "step/outcome")
    audit = report["audit"]
    _closed(audit, ("entry_pc", "current_pc", "program_base", "program_end_exclusive", "program_sha256",
        "program_events", "data_events", "raw_data_events", "diagnostic_events", "data_admission_refusals",
        "permissions", "phase", "budget", "successful_retirements", "step_calls", "execution_calls",
        "shared_execution_calls", "sealed", "terminal_reason", "external_exit", "first_fault"), "audit")
    fields = {"entry_pc": _pc(corpus.ENTRY_PC, program_kind), "current_pc": expected["stop_before_pc"],
        **{key: program_identity[key] for key in ("program_base", "program_end_exclusive", "program_sha256")},
        "data_events": logical, "raw_data_events": raw, "data_admission_refusals": [],
        "permissions": previous._permissions(expected), "phase": "Sealed", "budget": case["budget"],
        "successful_retirements": case["budget"], "step_calls": case["budget"], "execution_calls": case["budget"],
        "shared_execution_calls": case["budget"], "sealed": True, "terminal_reason": "OriginalStopBeforeReached",
        "external_exit": None, "first_fault": None}
    for key, val in fields.items():
        _equal(audit[key], val, "audit/" + key)
    _equal(audit["diagnostic_events"], [{"ordinal": i, "kind": "RawRamSnapshot", "range": [128, 4096],
        "byte_count": 3968} for i in range(diagnostic_snapshot_count(case["budget"]))], "audit/diagnostics")
    previous._program_events(audit["program_events"], list(zip(report["steps"], expected["steps"])), program_identity)
    return {"passed": True, "expected": expected,
        "comparison": {"classification": "IndependentEntryToExitStateAndCompleteAuditValidated" if expected["positive_completed"]
            else "IndependentPredecessorAlternateBoundaryValidated_NotAlgorithmCompletion",
            "firstMismatch": None, "retirements": case["budget"], "path": case["path"],
            "positiveCompleted": expected["positive_completed"], "boundaryOnly": expected["boundary_only"],
            "nativeInputOwnership": False, "physicalExecutionClaimed": False, "omittedActualFields": []}}
