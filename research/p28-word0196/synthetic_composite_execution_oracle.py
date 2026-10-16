"""M2bn independent expectations and strict public-safe record comparator.

Architectural values come exclusively from the unchanged M2bk structured oracle
and M2av C11/IR semantics, never Rust Cpu/decoder/executor output. The separately
labelled PROGRAM acquisition topology models the frozen decoder's callback
protocol only; it is not manufacturer semantics or a CPU effect oracle.
No complete PROGRAM payload is returned or persisted by this module.
"""

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from functools import lru_cache
import re

import synthetic_execution_protocol_oracle as reference
import synthetic_composite_primary_oracle as primary
from synthetic_composite_execution_corpus import PROVENANCE, UNKNOWN_SF, canonical_json

BASE_SHA = "b9e580f7cd554dd44676a5829444ece265bb517c"
COMPOSITE_SHA = "91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1"
SCOPE = "CpuStateAndProductionDecoderWithResearch16FormExecutor"
SOURCE_BINDINGS = {
    "synthetic_execution_protocol_oracle.py": "6448541d61e1bdfad9578c73f34260f45271dfb2df0247cfe2fc9072f8e9c4ba",
    "word0196_equivalent.c": "4b189d4ed3e97e0d197f6c558755cf056a89c1dc7122653c5c557e7ab62d76d3",
    "word0196_equivalent.h": "df8da1511708fb29cb747981a959544e549a67a9a982e15586b5c12ce8826f0e",
    "word0196_ir.json": "4fdbd6b7dbdd8f48d5a43e123ca93a33a003c22556a0c40b5296d5f409e085c4",
    "synthetic_adapter_feasibility_oracle.py": "4414f6de4fe705f4b097a00c7aed3fac951d5951f050589f3276b21e4c406268",
    "typed_lowering_contract.json": "6f62c23e99f72e7df51a0117b7c5ff600d892f2a8d3e4c4231a383e1d96c6bf4",
    "synthetic_composite_primary_oracle.py": "b3aecd90e3ef159b9aeec04ec6a46324a245bdcfb23a5ef80ad8d3d11b921c47",
}
DECODER_TABLE_SHA = "77697d4b0e3c90372326156bf1a8544486d07f4aa8f93c67cf9e5f2af6c7eff1"

# These identity numbers are fixed source/table bindings, not semantics evidence.
# The original18 indices are pinned in the M2av IR; direct J's index is a frozen
# table identity. Mnemonics/lengths/operands independently follow primary rows.
NODE_IDENTITIES = {
    "556F": (747, "LB A, off N8"), "5571": (2198, "SLLB A"),
    "5572": (1862, "ROLB off N8"), "5575": (739, "LB A, r0"),
    "5576": (333, "ANDB A, off N8"), "5578": (498, "CMP off N8, #N16"),
    "557D": (719, "JLT rel8"), "557F": (1504, "MOVB r1, off N8"),
    "5582": (349, "ANDB off N8, A"), "5585": (716, "JBS off N8.7, rel8"),
    "5588": (714, "JBS off N8.5, rel8"), "558B": (349, "ANDB off N8, A"),
    "558E": (1678, "ORB off N'8, #N8"), "5592": (747, "LB A, off N8"),
    "5594": (1619, "ORB A, #N8"), "55BF": (738, "LB A, #N8"),
    "55C1": (2301, "STB A, off N8"), "55C3": (2301, "STB A, off N8"),
    "DirectJ_NotBelow": (684, "J addr16"), "DirectJ_Below": (684, "J addr16"),
}

PROJECTION_RULES = {
    "classification": "PublicSafeFullDeclaredSemanticProjection_NoRawProgramPayload",
    "platformExclusions": [],
    "programFields": "all actual access addresses/order/purpose/serviced/refusal/extent association; no byte values",
    "architecturalFields": "complete entry/terminal and every step snapshot; all32 pointing words and aliases",
    "dataFields": "complete before/after inventoried bytes, ordered logical/raw/seed/diagnostic journals",
    "counters": "all retirement/lifecycle/internalSF counters; cycles synthetic only, no physical-time claim",
    "syntheticCycles": "unchanged decoder source accounting:2*length plus1 for directJ plus4 for taken conditional branch",
    "comparison": "strict recursive exact types/keys/order; first mismatch, no normalization",
    "stateExpectationSource": "FrozenM2bkReferenceCase_M2avC11IR_M2bdPrimaryDataflow",
    "programTopologyExpectationSource": "SeparateFrozenDecoderSourceInstrumentationModel_NotStateSemantics",
    "physicalSf": "Unknown; paired internal field experiments only",
}


def _logical_id(value):
    return value if type(value) is str else f"{value:04X}"


def _reference_input(request):
    entry = request["entry"]
    return {"id": request["case_id"], "classification": PROVENANCE,
            "entry": {"pc": entry["pc"], "a": entry["a"], "al": entry["al"],
                      "ah": entry["ah"], "psw": entry["psw"],
                      **{name: int(entry[name]) for name in ("cf", "zf", "hc", "dd")},
                      "otherPsw": entry["other_psw"], "lrb": entry["lrb"],
                      "scb": entry["scb"], "ssp": entry["ssp"],
                      "pointingBanks": [[bank[name] for name in ("x1", "x2", "dp", "usp")]
                                        for bank in entry["pointing_banks"]],
                      "sf": deepcopy(reference.UNKNOWN_SF), "halted": entry["halted"]},
            "data": {f"{int(address):04X}": value for address, value in request["data"].items()},
            "localAliases": {"r": deepcopy(entry["local_r"]),
                             "er": deepcopy(entry["local_er"])}}


def _snapshot(state):
    return {"pc": state["pc"], "a": state["a"], "al": state["al"], "ah": state["ah"],
            "psw": state["psw"], **{name: bool(state[name]) for name in ("cf", "zf", "hc", "dd")},
            "other_psw": state["otherPsw"], "lrb": state["lrb"], "scb": state["scb"],
            "ssp": state["ssp"],
            "pointing_banks": [dict(zip(("x1", "x2", "dp", "usp"), bank))
                               for bank in state["pointingBanks"]],
            "local_r": deepcopy(state["locals"]), "local_er": deepcopy(state["er"]),
            "halted": state["halted"], "provenance": PROVENANCE, "sf": deepcopy(UNKNOWN_SF)}


def _decode(row):
    identifier = _logical_id(row["logicalId"])
    fields = {"n8": 0, "n8_alt": 0, "n16": 0, "addr16": 0, "rel8": 0}
    operands = {"556F": {"n8": 142}, "5572": {"n8": 142},
                "5576": {"n8": 142}, "5578": {"n8": 150, "n16": 192},
                "557D": {"rel8": 26}, "557F": {"n8": 23},
                "5582": {"n8": 23}, "5585": {"n8": 42, "rel8": 10},
                "5588": {"n8": 36, "rel8": 7}, "558B": {"n8": 143},
                "558E": {"n8_alt": 42, "n8": 1}, "5592": {"n8": 143},
                "5594": {"n8": 240}, "55BF": {"n8": 15},
                "55C1": {"n8": 23}, "55C3": {"n8": 143},
                "DirectJ_NotBelow": {"addr16": 0x5596},
                "DirectJ_Below": {"addr16": 0x55C5}}
    fields.update(operands.get(identifier, {}))
    index, mnemonic = NODE_IDENTITIES[identifier]
    form = row["form"]
    return {"form": form, "mnemonic": mnemonic, "index": index, "len": row["length"],
            "dd_before": bool(row["stateBefore"]["dd"]),
            "dd_after": bool(row["stateAfter"]["dd"]), **fields}


def _data_events(result):
    logical, raw, ranges = [], [], []
    for row in result["trace"]:
        begin, raw_begin = len(logical), len(raw)
        for read in row["dataReads"]:
            ordinal = len(logical) + 1
            for offset, byte in enumerate(read["bytes"]):
                raw.append({"ordinal": len(raw) + 1, "logical_ordinal": ordinal,
                            "address": read["address"] + offset, "operation": "Read", "value": byte})
            logical.append({"ordinal": ordinal, "phase": "ExecutedFunctionalDataAccess",
                            "pc": row["syntheticPc"], "address": read["address"],
                            "width": read["widthBits"], "operation": "Read", "value": read["value"],
                            "old_value": None, "write_ordinal": None, "kind": None,
                            "same_value": False, "constituents": deepcopy(read["bytes"])})
        for write in row["dataWrites"]:
            ordinal = len(logical) + 1
            raw.append({"ordinal": len(raw) + 1, "logical_ordinal": ordinal,
                        "address": write["address"], "operation": "Write", "value": write["value"]})
            logical.append({"ordinal": ordinal, "phase": "ExecutedFunctionalDataAccess",
                            "pc": row["syntheticPc"], "address": write["address"], "width": 8,
                            "operation": "Write", "value": write["value"], "old_value": write["oldValue"],
                            "write_ordinal": write["ordinal"], "kind": write["kind"],
                            "same_value": write["sameValue"], "constituents": [write["value"]]})
        ranges.append((begin, len(logical), raw_begin, len(raw)))
    return logical, raw, ranges


def _auxiliary_events(request, result):
    seed, diagnostics, pointing = [], [], {}
    for address, value in sorted(request["data"].items(), key=lambda item: int(item[0])):
        seed.append({"ordinal": len(seed) + 1, "phase": "SeedInitializationAccess",
                     "address": int(address), "width": 8, "value": value})
    for bank, values in enumerate(request["entry"]["pointing_banks"]):
        for slot, name in enumerate(("x1", "x2", "dp", "usp")):
            address, value = 0x80 + bank * 8 + slot * 2, values[name]
            seed.append({"ordinal": len(seed) + 1, "phase": "SeedInitializationAccess",
                         "address": address, "width": 16, "value": value})
            pointing[address], pointing[address + 1] = value & 255, value >> 8
    def note(address, value):
        diagnostics.append({"ordinal": len(diagnostics) + 1, "phase": "DiagnosticSnapshotRead",
                            "address": address, "width": 8, "value": value})
    def snapshot(state):
        for address in range(0x80, 0xC0):
            note(address, pointing[address])
        for index, value in enumerate(state["locals"]):
            note(0x108 + index, value)
    snapshot(result["entryState"])
    for address, value in sorted(request["data"].items(), key=lambda item: int(item[0])):
        note(int(address), value)
    for row in result["trace"]:
        snapshot(row["stateBefore"])
        for write in row["dataWrites"]:
            note(write["address"], write["oldValue"])
        snapshot(row["stateAfter"])
    snapshot(result["terminalState"])
    for address, value in sorted(result["terminalData"].items()):
        note(int(address, 16), value)
    return seed, diagnostics


def load_instrumentation_patterns(repository_root):
    """Frozen table/source identity for callback instrumentation only."""
    path = Path(repository_root) / "rust/p28-slice-runner/src/full_decoder.rs"
    content = path.read_bytes()
    if sha256(content).hexdigest() != DECODER_TABLE_SHA:
        raise ValueError("FrozenDecoderInstrumentationSourceChanged")
    pattern = r'OpcodePattern\s*\{\s*mnemonic:\s*"([^"\n]+)",\s*dd_mode:\s*\x27([01RUS])\x27,\s*bytes_pat:\s*&\[([^\]]*)\]\s*\}'
    rows = [(mnemonic, tuple(re.findall(r'"([^"\n]*)"', text)), dd)
            for mnemonic, dd, text in re.findall(pattern, content.decode("utf-8"))]
    if len(rows) != 2623:
        raise ValueError("FrozenDecoderInstrumentationTableCount")
    return tuple(rows)


def _program_events(result, patterns):
    signature = tuple((row["syntheticPc"], row["length"], _logical_id(row["logicalId"]),
                       bool(row["stateBefore"]["dd"])) for row in result["trace"])
    return deepcopy(_program_template(signature, patterns))


@lru_cache(maxsize=8)
def _program_template(signature, patterns):
    # Separate source-derived observation-integrity model. Actual observations
    # must be acquired by the Rust callback, not manufactured from this model.
    payload = primary.expected_reference_for_test(0)
    events = []
    fixed = lambda token: len(token) == 2 and all(c in "0123456789abcdefABCDEF" for c in token)
    for step, (pc, length, identifier, incoming_dd) in enumerate(signature, 1):
        start = pc - 4096
        offsets = [0]
        first = payload[start]
        candidates = [index for index, (_, tokens, _) in enumerate(patterns)
                      if tokens and fixed(tokens[0]) and int(tokens[0], 16) == first]
        candidates.sort(key=lambda index: (-sum(fixed(t) for t in patterns[index][1]),
                                           -len(patterns[index][1])))
        selected = None
        for index in candidates:
            _, tokens, dd = patterns[index]
            if dd == "1" and not incoming_dd or dd == "0" and incoming_dd:
                continue
            for offset, token in enumerate(tokens):
                offsets.append(offset)
                if start + offset >= len(payload):
                    raise ValueError("FrozenDecoderWouldReadBeyondSyntheticSegment")
                if fixed(token) and int(token, 16) != payload[start + offset]:
                    break
            else:
                selected = index
                break
        if selected != NODE_IDENTITIES[identifier][0]:
            raise ValueError("IndependentIdentityVersusInstrumentationSelection")
        for purpose, offsets_for_purpose in (("DecoderProbe", offsets),
                                             ("ArchitecturalSelectedFetch", range(length))):
            for offset in offsets_for_purpose:
                events.append({"ordinal": len(events) + 1, "step": step, "pc": pc,
                               "address": pc + offset, "offset": start + offset,
                               "instruction_offset": offset, "acquired_purpose": purpose,
                               "purpose": "DecoderLookahead" if purpose == "DecoderProbe"
                               and offset >= length else purpose,
                               "selected_extent_length": length, "serviced": True, "refusal": None})
    return events


def expected_case(request, patterns=None):
    """Whole safe expected observation, generated before Rust observations."""
    result = reference.reference_case(_reference_input(request))
    if result["path"] != request["path"]:
        raise ValueError("PermissionProfileDoesNotFollowEntryPredicate")
    logical, raw, ranges = _data_events(result)
    steps, retirements = [], []
    for row, bounds in zip(result["trace"], ranges):
        identifier = _logical_id(row["logicalId"])
        decode = _decode(row)
        primary_index = next(index for index, node in enumerate(primary.NODES)
                             if _logical_id(node.node_id) == identifier)
        steps.append({"index": row["step"], "node_identity": identifier,
                      "pc_before": row["syntheticPc"], "pc_after": row["stateAfter"]["pc"],
                      "form": decode["form"], "decode": decode,
                      "before": _snapshot(row["stateBefore"]), "after": _snapshot(row["stateAfter"]),
                      "branch_taken": row["branchTaken"],
                      "logical_start": bounds[0], "logical_end": bounds[1],
                      "raw_start": bounds[2], "raw_end": bounds[3],
                      "selected_extent_sha256": sha256(primary.expected_instruction(primary_index)).hexdigest()})
        retirements.append({"ordinal": row["step"], "pc_before": row["syntheticPc"],
                            "pc_after": row["stateAfter"]["pc"], "form": decode["form"]})
    seed, diagnostics = _auxiliary_events(request, result)
    expected = {"kind": "observation", "accepted": True, "error": None,
                "case_id": request["case_id"], "family": request["family"],
                "permission_path": result["path"], "scope": SCOPE,
                "before": _snapshot(result["entryState"]), "after": _snapshot(result["terminalState"]),
                "before_data": deepcopy(request["data"]),
                "after_data": {str(int(address, 16)): value for address, value in result["terminalData"].items()},
                "steps": steps, "data_journal": logical, "raw_data_journal": raw,
                "seed_journal": seed, "diagnostic_journal": diagnostics, "retirements": retirements,
                "retired_instructions": result["instructionCount"], "cpu_instances": 1,
                "direct_j_count": 1, "external_transfer": result["terminalPc"],
                "program_sealed": True, "lifecycle_sealed": True,
                "internal_sf_before": request["internal_sf"], "internal_sf_after": request["internal_sf"],
                "cycles": sum(2 * row["length"] + (1 if type(row["logicalId"]) is str else 0)
                              + (4 if row["branchTaken"] is True else 0) for row in result["trace"]),
                "instructions": result["instructionCount"], "composite_executions": 1,
                "production_exec_integrated": False, "original_rom_executions": 0}
    if patterns is not None:
        expected["program_events"] = _program_events(result, patterns)
    return expected


def first_difference(expected, actual, path="$", depth=0):
    if depth > 64:
        return {"field": path, "expected": "bounded primitive tree", "actual": "depth over64"}
    if type(expected) is not type(actual):
        return {"field": path, "expected": expected, "actual": actual,
                "reason": "ExactJsonTypeMismatch"}
    if type(expected) is dict:
        if set(expected) != set(actual):
            return {"field": path, "expectedKeys": sorted(expected), "actualKeys": sorted(actual),
                    "reason": "ClosedObservationKeysMismatch"}
        for key in sorted(expected):
            mismatch = first_difference(expected[key], actual[key], path + "." + key, depth + 1)
            if mismatch is not None:
                return mismatch
    elif type(expected) is list:
        if len(expected) != len(actual):
            return {"field": path, "expectedLength": len(expected), "actualLength": len(actual),
                    "reason": "OrderedObservationLengthMismatch"}
        for index, (left, right) in enumerate(zip(expected, actual)):
            mismatch = first_difference(left, right, path + f"[{index}]", depth + 1)
            if mismatch is not None:
                return mismatch
    elif expected != actual:
        return {"field": path, "expected": expected, "actual": actual, "reason": "SemanticValueMismatch"}
    return None


def compare_observation(request, actual, patterns):
    expected = expected_case(request, patterns)
    mismatch = first_difference(expected, actual)
    if mismatch is not None:
        mismatch["case_id"] = request["case_id"]
        mismatch["internal_sf"] = request["internal_sf"]
        mismatch["entry"] = deepcopy(request["entry"])
    return mismatch


def c11_input_line(request):
    e, d = request["entry"], request["data"]
    bank = e["pointing_banks"][e["scb"]]
    values = [e["a"], e["psw"], 0x556F, e["lrb"],
              *[bank[name] for name in ("x1", "x2", "dp", "usp")], e["ssp"],
              int(request["internal_sf"]), int(e["halted"]), 1, 0,
              *e["local_r"], *[d[str(address)] for address in
                               (0x117, 0x124, 0x128, 0x12A, 0x18E, 0x18F, 0x196, 0x197)]]
    return request["case_id"] + ("-sf1" if request["internal_sf"] else "-sf0") \
        + " " + " ".join(map(str, values)) + "\n"


def c11_expected_projection(request):
    result = reference.reference_case(_reference_input(request))
    bank = request["entry"]["pointing_banks"][request["entry"]["scb"]]
    def state(source, data, original_pc):
        return {"a": source["a"], "psw": source["psw"], "pc": original_pc,
                "lrb": source["lrb"], **bank, "ssp": source["ssp"],
                "sf": request["internal_sf"], "halted": source["halted"],
                "registers": deepcopy(source["locals"]),
                **{name: data[key] for name, key in
                   (("ram0117", "0117"), ("ram0124", "0124"), ("ram0128", "0128"),
                    ("ram012A", "012A"), ("ram018E", "018E"), ("ram018F", "018F"),
                    ("ram0196Lo", "0196"), ("ram0196Hi", "0197"))}}
    original_rows = result["trace"][:-1]
    original_steps, accesses, writes = [], [], []
    for index, row in enumerate(original_rows):
        successor = original_rows[index + 1]["logicalId"] if index + 1 < len(original_rows) else result["terminalPc"]
        original_steps.append({"pc": row["logicalId"], "nextPc": successor,
                               "a": row["stateAfter"]["a"], "psw": row["stateAfter"]["psw"]})
        for read in row["dataReads"]:
            accesses.append({"pc": row["logicalId"], "address": read["address"],
                             "width": read["widthBits"], "write": False, "value": read["value"]})
        for write in row["dataWrites"]:
            accesses.append({"pc": row["logicalId"], "address": write["address"],
                             "width": 8, "write": True, "value": write["value"]})
            writes.append({"pc": row["logicalId"], "address": write["address"], "width": 8,
                           "oldValue": write["oldValue"], "newValue": write["value"],
                           "eventIndex": 0, "writeOrdinal": write["ordinal"]})
    word = request["data"][str(0x196)] + 256 * request["data"][str(0x197)]
    return {"id": request["case_id"] + ("-sf1" if request["internal_sf"] else "-sf0"),
            "status": "Complete", "entry": state(result["entryState"], _reference_input(request)["data"], 0x556F),
            "final": state(result["terminalState"], result["terminalData"], result["terminalPc"]),
            "compare": {"left": word, "right": 192, "cf": word < 192, "zf": word == 192},
            "branchTaken": word < 192, "stopPc": result["terminalPc"],
            "steps": original_steps, "accesses": accesses, "writes": writes}


def compare_c11(request, actual):
    return first_difference(c11_expected_projection(request), actual)


def sensitivity_checks(request, actual, patterns):
    """Mutate observed evidence, never official PROGRAM or expected values."""
    if compare_observation(request, actual, patterns) is not None:
        raise ValueError("SensitivityControlIsNotAnIndependentlyPassingObservation")
    checks = []
    def check(name, mutate):
        changed = deepcopy(actual)
        mutate(changed)
        mismatch = compare_observation(request, changed, patterns)
        if mismatch is None:
            raise ValueError("ComparatorMissedControlledMutation:" + name)
        checks.append({"name": name, "classification": "SemanticMismatchSensitivity",
                       "firstMismatch": mismatch})
    check("intermediate-cf", lambda value: value["steps"][1]["after"].__setitem__("cf", not value["steps"][1]["after"]["cf"]))
    check("intermediate-zf", lambda value: value["steps"][0]["after"].__setitem__("zf", not value["steps"][0]["after"]["zf"]))
    check("actual-next-pc", lambda value: value["steps"][0].__setitem__("pc_after", 0x1003))
    write_index = next(index for index, event in enumerate(actual["data_journal"]) if event["operation"] == "Write")
    check("data-write-value", lambda value: value["data_journal"][write_index].__setitem__("value", value["data_journal"][write_index]["value"] ^ 1))
    write_indices = [index for index, event in enumerate(actual["data_journal"])
                     if event["operation"] == "Write"]
    def swap_actual_writes(value):
        left, right = write_indices[:2]
        events = value["data_journal"]
        events[left], events[right] = events[right], events[left]
    check("data-write-order", swap_actual_writes)
    same = next((index for index, event in enumerate(actual["data_journal"]) if event["operation"] == "Write" and event["same_value"]), None)
    if same is not None:
        check("missing-same-value-write", lambda value: value["data_journal"].pop(same))
    check("lost-retained-pointing-word", lambda value: value["after"]["pointing_banks"][7].pop("usp"))
    read_index = next(index for index, event in enumerate(actual["data_journal"]) if event["operation"] == "Read")
    check("hidden-extra-read", lambda value: value["data_journal"].insert(read_index, deepcopy(value["data_journal"][read_index])))
    check("reseed-between-steps", lambda value: value["steps"][1].__setitem__("before", deepcopy(value["before"])))
    check("retained-ah-corrupted", lambda value: value["steps"][2]["after"].__setitem__("ah", value["steps"][2]["after"]["ah"] ^ 1))
    check("missing-raw-program-callback", lambda value: value["program_events"].pop(0))
    check("unserviced-program-access-hidden", lambda value: value["program_events"][0].__setitem__("serviced", False))
    return checks
