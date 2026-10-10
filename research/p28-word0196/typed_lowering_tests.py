"""Invented-only independent static/dataflow/CFG tests; no target emission.

Expected mapping/path/flag/DD facts were sealed before the analyzer existed.
Only scalar mathematical expressions are evaluated; no CPU, IR executor or
native write journal is created. Every real IR mutation must be refused.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys

import typed_lowering_oracle as oracle


HERE = Path(__file__).resolve().parent

# Independently authored data-use tables, added before their first comparison.
# These do not read the analyzer's tables/output to establish expected liveness.
DATA_DOMAIN = ("AL", "AH") + tuple(f"RAM{0x108 + x:04X}" for x in range(8)) + (
    "RAM0117", "RAM0124", "RAM0128", "RAM012A", "RAM018E", "RAM018F",
    "RAM0196", "RAM0197", "LRB", "SCB", "X1", "X2", "DP", "USP", "SSP", "SFUninterpreted")
DATA_READS = {
    0x556F: ("RAM018E", "AH"), 0x5571: ("AL",),
    0x5572: ("RAM018E",), 0x5575: ("RAM0108", "AH"),
    0x5576: ("AL", "RAM018E"), 0x5578: ("RAM0196",), 0x557D: (),
    0x557F: ("RAM0117",), 0x5582: ("RAM0117", "AL"),
    0x5585: ("RAM012A",), 0x5588: ("RAM0124",), 0x558B: ("RAM018F", "AL"),
    0x558E: ("RAM012A",), 0x5592: ("RAM018F", "AH"),
    0x5594: ("AL", "AH"), 0x55BF: ("AH",), 0x55C1: ("AL",), 0x55C3: ("AL",),
}
DATA_WRITES = {
    0x556F: ("AL",), 0x5571: ("AL",), 0x5572: ("RAM018E",),
    0x5575: ("AL",), 0x5576: ("AL",), 0x5578: (), 0x557D: (),
    0x557F: ("RAM0109",), 0x5582: ("RAM0117",), 0x5585: (), 0x5588: (),
    0x558B: ("RAM018F",), 0x558E: ("RAM012A",), 0x5592: ("AL",),
    0x5594: ("AL",), 0x55BF: ("AL",), 0x55C1: ("RAM0117",), 0x55C3: ("RAM018F",),
}


def expected_data_liveness():
    before = {pc: set() for pc in oracle.SUCCESSORS}
    after = {pc: set() for pc in oracle.SUCCESSORS}
    for pcs in oracle.PATH_PCS.values():
        needed = set(DATA_DOMAIN)
        for pc in reversed(pcs):
            after[pc].update(needed)
            needed.difference_update(DATA_WRITES[pc])
            needed.update(DATA_READS[pc])
            before[pc].update(needed)
    return [{"pc": pc, "read": list(DATA_READS[pc]), "written": list(DATA_WRITES[pc]),
             "liveIn": sorted(before[pc]), "liveOut": sorted(after[pc]),
             "mayClobber": False, "memoryEffectsMandatory": True}
            for pc in oracle.SUCCESSORS]


def demand(condition, message):
    if not condition:
        raise AssertionError(message)


def descriptor(value):
    fields = () if value["kind"] == "AccumulatorA" else (
        (value["offset"], value["bit"]) if value["kind"] in ("PageBit7", "PageBit5")
        else (value["value"],))
    return {"type": value["kind"], "fields": list(fields)}


def check_analysis(actual, initial_dd):
    expected = oracle.expected_bundle()
    demand(actual["passed"] is True, "Actual static validation did not pass")
    demand(actual["classification"] == "ReviewedStaticTypedLoweringSpecification", "Wrong classification")
    demand(actual["instructionSites"] == 18 and actual["uniqueForms"] == 15, "Mapping counts")
    actual_sites = {row["pc"]: row for row in actual["sites"]}
    demand(list(actual_sites) == [row["pc"] for row in expected["mapping"]], "Full exact site inventory/order")
    for row in expected["mapping"]:
        seen = actual_sites[row["pc"]]
        for key in ("pc", "formId", "length", "successors"):
            demand(seen[key] == row[key], f"Mapping {row['pc']:04X}/{key}")
        demand([descriptor(x) for x in seen["typedOperands"]] == row["typedOperands"], "Exact operand kinds/scalars")
        demand(seen["dd"]["selection"] == row["ddPrecondition"], "Selection not DD transfer")
        demand(seen["dd"]["transfer"] == row["ddTransfer"], "LB DD transfer")
    expected_edges = {(pc, target) for pc, targets in oracle.SUCCESSORS.items() for target in targets}
    demand({tuple(edge) for edge in actual["cfg"]["edges"]} == expected_edges, "Full CFG edges, not site-count proof")
    demand(actual["cfg"]["entryPc"] == 0x556F and actual["cfg"]["stopBeforePcs"] == [0x5596, 0x55C5], "CFG boundaries")
    paths = {tuple(row["pcList"]): row for row in actual["paths"]}
    demand(set(paths) == {tuple(row["pcList"]) for row in expected["paths"]}, "Four complete ordered paths")
    for row in expected["paths"]:
        seen = paths[tuple(row["pcList"])]
        for key in ("pcList", "stopBeforePc", "instructionCount", "memoryAccesses", "orderedWrites"):
            demand(seen[key] == row[key], f"Path {row['name']}/{key}")
        demand([(c["pc"], bool(c["value"])) for c in seen["conditions"]] ==
               [(c["pc"], bool(c["value"])) for c in row["conditions"]], "Exact branch choices/order")
        demand(seen["historicalWitness"] == row["historicalWitness"], "13-step path is not a native witness")
    dd_expected = oracle.expected_dd(initial_dd)
    demand(len(actual["ddAnalysis"]) == 18, "All DD sites")
    for row, seen in zip(dd_expected, actual["ddAnalysis"]):
        demand(seen["pc"] == row["pc"], "DD order")
        for source, target in (("mayIncoming", "incomingMay"), ("mayOutgoing", "outgoingMay")):
            demand(seen[target] == row[source], f"DD may {row['pc']:04X}")
        for source, target in (("mustIncoming", "incomingMust"), ("mustOutgoing", "outgoingMust")):
            want = row[source][0] if len(row[source]) == 1 else None
            demand(seen[target] == want, f"DD must {row['pc']:04X}")
        demand(seen["incomingKnowledge"] == row["classification"], "DD knowledge label matches own singleton domain")
    demand(actual["flagDomain"] == expected["flagDomain"], "Declared PSW scalar domain")
    demand(len(actual["flagAnalysis"]) == 18, "All flag obligations")
    for row, seen in zip(expected["flags"], actual["flagAnalysis"]):
        pc = row["pc"]
        demand(seen["pc"] == pc, "Flag row order")
        demand(seen["functionalRead"] == list(oracle.FUNCTIONAL_FLAG_READS.get(pc, ())), "Functional CF read")
        demand(seen["formSelectionRead"] == (["DD"] if pc in oracle.DD_ZERO_REQUIRED else []), "DD selection is separate")
        demand(seen["written"] == list(oracle.FLAG_WRITES[pc]), "Architectural flag writes")
        demand(seen["preserved"] == [flag for flag in oracle.FLAG_DOMAIN if flag not in oracle.FLAG_WRITES[pc]], "PSW preservation")
        for flag in oracle.FLAG_DOMAIN:
            demand(set(seen["reachingWriters"][flag]) == set(row["reachingWritersIn"][flag]),
                   f"Reaching writer {pc:04X}/{flag}")
        demand(set(seen["liveIn"]) == set(row["liveIn"]), f"Backward live-in {pc:04X}")
        demand(set(seen["liveOut"]) == set(row["liveOut"]), f"Backward live-out {pc:04X}")
        demand(seen["initialValueLive"] == row["initialValueLive"], "Initial flag value live only when reaching and required")
        demand(seen["mayClobber"] == dict.fromkeys(oracle.FLAG_DOMAIN, False), "No snapshot-discard clobber permission")
        demand(seen["allPathsObligation"] is True, "All paths flag proof")
    demand(len(actual["dataLiveness"]) == 18, "All data liveness sites")
    for row, seen in zip(expected_data_liveness(), actual["dataLiveness"]):
        for key in ("pc", "mayClobber", "memoryEffectsMandatory"):
            demand(seen[key] == row[key], f"Data obligation {row['pc']:04X}/{key}")
        for key in ("read", "written", "liveIn", "liveOut"):
            demand(set(seen[key]) == set(row[key]), f"Independent data liveness {row['pc']:04X}/{key}")
    return {row["name"]: paths[tuple(row["pcList"])] for row in expected["paths"]}


def freeze_expression(value):
    demand(type(value) is list and value and type(value[0]) is str, "Typed symbolic expression")
    op = value[0]
    arity = {"input": 1, "const": 1, "and8": 2, "or8": 2, "shl8": 1,
             "bit7": 1, "rol8": 2, "zero8": 1, "lt16": 2, "eq16": 2}
    demand(op in arity and len(value) == arity[op] + 1, "Closed symbolic expression operation/arity")
    if op == "input":
        demand(type(value[1]) is str, "Symbolic input name")
        return (op, value[1])
    if op == "const":
        demand(type(value[1]) in (int, bool), "Symbolic scalar constant")
        return (op, value[1])
    return tuple([op] + [freeze_expression(child) for child in value[1:]])


def evaluate(expression, state, cache):
    if expression in cache:
        return cache[expression]
    op = expression[0]
    if op == "input":
        name = expression[1]
        aliases = {"RAM0108": "r0", "RAM0109": "r1"}
        name = aliases.get(name, name)
        if name.startswith("PSW") and name[3:].isdigit():
            result = (state["OtherPSW"] // (2 ** int(name[3:]))) % 2
        else:
            result = state[name]
    elif op == "const":
        result = expression[1]
    else:
        values = [evaluate(child, state, cache) for child in expression[1:]]
        if op == "and8":
            result = values[0] & values[1]
        elif op == "or8":
            result = values[0] | values[1]
        elif op == "shl8":
            result = (2 * values[0]) % 256
        elif op == "bit7":
            result = values[0] // 128
        elif op == "rol8":
            result = (2 * values[0] + values[1]) % 256
        elif op == "zero8":
            result = int(values[0] == 0)
        elif op == "lt16":
            result = int(values[0] < values[1])
        else:
            result = int(values[0] == values[1])
    cache[expression] = result
    return result


def invented_state(word=192, x=0xB7, r0=0xD9, gate1=0, gate2=0, dd=0, serial=0):
    return {"RAM0196": word, "RAM018E": x, "r0": r0, "r1": serial % 256,
            "RAM0117": (serial * 17 + 15) % 256, "RAM018F": (serial * 31 + 0x55) % 256,
            "RAM012A": gate1, "RAM0124": gate2, "AH": (serial * 43 + 0xA5) % 256,
            "AL": (serial * 23) % 256, "CF": serial % 2, "ZF": (serial // 2) % 2,
            "HC": (serial // 4) % 2, "DD": dd, "OtherPSW": serial % 4096,
            "RAM0128": (serial * 37) % 256, "RAM0197": word // 256,
            "LRB": 33, "SCB": serial % 8, "X1": 0x3210, "X2": 0x7654,
            "DP": 0xBA98, "USP": 0xFEDC, "SSP": 0x43A2,
            "SFHostReplay": "UninterpretedRetainedSymbol"}


def check_symbolic(paths):
    compiled = {}
    for name, path in paths.items():
        terminal = path["terminal"]
        compiled[name] = {field: freeze_expression(terminal[field])
                          for field in ("AL", "AH", "CF", "ZF", "HC", "DD", "OtherPSW")}
        for name_ram, value in terminal["ram"].items():
            compiled[name][name_ram] = freeze_expression(value)
    counts = dict.fromkeys(oracle.PATH_PCS, 0)
    dd_counts = {0: 0, 1: 0}
    unique_states = set()
    checked = 0

    def probe(state):
        nonlocal checked
        snapshot = dict(state)
        expected = oracle.invented_algebra(state)
        name = expected["path"]
        cache = {}
        for field in ("AL", "AH", "CF", "ZF", "HC", "DD", "OtherPSW"):
            demand(evaluate(compiled[name][field], state, cache) == expected[field], f"Invented terminal {name}/{field}")
        for field in ("RAM018E", "RAM0117", "RAM018F", "RAM012A"):
            demand(field in compiled[name], f"Missing symbolic RAM obligation {field}")
            demand(evaluate(compiled[name][field], state, cache) == expected[field], f"Invented memory equation {name}/{field}")
        if "RAM0109" in compiled[name]:
            demand(evaluate(compiled[name]["RAM0109"], state, cache) == expected["r1"], "Local r1/high-er0 equation")
        demand(state == snapshot, "Symbolic checks may not mutate invented input")
        unique_states.add(tuple(sorted(state.items())))
        counts[name] += 1
        dd_counts[state["DD"]] += 1
        checked += 1

    # Full word domain: below/equal/above, both incoming DD and all gate paths.
    for word in range(65536):
        group = word % 3
        probe(invented_state(word=word, gate1=128 if group == 0 else 0,
                             gate2=32 if group == 1 else 0, dd=word % 2, serial=word))
    # Every rotate input and r0 byte pair; CF producer dependency stays structural.
    for x in range(256):
        for r0 in range(256):
            group = x % 4
            probe(invented_state(word=191 if group == 0 else 192 + r0,
                                 x=x, r0=r0, gate1=128 if group == 1 else 0,
                                 gate2=32 if group == 2 else 0, dd=r0 % 2, serial=256 * x + r0))
    # Gates' neighbor bits, bit0 already set, and retained PSW scalar domains.
    for gate1 in (0, 1, 2, 3, 0x7F, 0x80, 0x81, 0xFE, 0xFF):
        for gate2 in (0, 1, 2, 0x1F, 0x20, 0x21, 0x7F, 0x80, 0xFF):
            for dd in (0, 1):
                probe(invented_state(gate1=gate1, gate2=gate2, dd=dd, serial=gate1 + gate2))
    for retained in range(4096):
        state = invented_state(gate1=128 if retained % 2 else 0,
                               gate2=32 if retained % 4 == 0 else 0, dd=retained % 2, serial=retained)
        state["OtherPSW"] = retained
        probe(state)
    same_value_cases = 0
    for name in oracle.PATH_PCS:
        state = invented_state(word=0 if name == "A" else 192, x=255, r0=255,
                               gate1=128 if name == "B" else 1, gate2=32 if name == "C" else 0)
        state.update(RAM0117=15, RAM018F=15, r1=15)
        expected = oracle.invented_algebra(state)
        demand(expected["path"] == name, "Invented same-value path")
        demand(expected["RAM018E"] == state["RAM018E"], "Unchanged ROL value still write")
        demand(len(paths[name]["orderedWrites"]) == (5 if name == "D" else 3), "Same-value writes remain distinct")
        if name == "A":
            demand(expected["RAM0117"] == 15 and expected["RAM018F"] == 15, "Two unchanged STB obligations")
        if name == "D":
            demand(expected["RAM012A"] == state["RAM012A"], "Unchanged OR bit0 still write")
        probe(state)
        same_value_cases += 1
    demand(all(counts.values()) and all(dd_counts.values()), "Complete invented path/DD coverage")
    return {"inventedSymbolicStates": checked, "inventedStatesByPath": counts,
            "inventedSymbolicCountUnit": "ActualChecksNotNecessarilyUniqueStates",
            "uniqueInventedStates": len(unique_states), "overlappingInventedChecks": checked - len(unique_states),
            "inventedStatesByIncomingDD": dd_counts, "sameValueWriteCases": same_value_cases,
            "fullWordDomainCases": 65536, "rotateAndR0CrossedCases": 65536,
            "gateNeighborCases": 162, "retainedPSWDomainCases": 4096}


def replace(root, route, value):
    parent = root
    for key in route[:-1]:
        parent = parent[key]
    parent[route[-1]] = value


def negative_mutations(contract, ir):
    cases = []

    def put(label, target, route, value):
        cases.append((label, lambda c, i, t=target, p=route, v=value: replace(c if t == "contract" else i, p, deepcopy(v))))

    def node(pc):
        return next(index for index, item in enumerate(ir["instructions"]) if item["pc"] == pc)

    def site(pc):
        return next(index for index, item in enumerate(contract["sites"]) if item["pc"] == pc)

    # Real instruction/effect/CFG mutations, not merely documentary status swaps.
    for pc in oracle.SUCCESSORS:
        idx = node(pc)
        put(f"IR_wrong_length_{pc:04X}", "ir", ("instructions", idx, "form", "length"), 6)
        put(f"IR_missing_successor_{pc:04X}", "ir", ("instructions", idx, "successors"), [])
        put(f"IR_extra_successor_{pc:04X}", "ir", ("instructions", idx, "successors"),
            list(ir["instructions"][idx]["successors"]) + [0x556F])
        put(f"IR_extra_flag_clobber_{pc:04X}", "ir", ("instructions", idx, "flagsWritten"),
            list(ir["instructions"][idx]["flagsWritten"]) + ["HC"])
        put(f"contract_wrong_form_{pc:04X}", "contract", ("sites", site(pc), "formId"), "unsupported-form")
        put(f"contract_width_{pc:04X}", "contract", ("sites", site(pc), "dataWidthBits"), 32)
    put("IR_missing_DD_setting_effect", "ir", ("instructions", node(0x556F), "effects"),
        ir["instructions"][node(0x556F)]["effects"][:2])
    put("IR_LB_sets_DD1", "ir", ("instructions", node(0x556F), "effects", 2, "value"), True)
    put("IR_missing_LB_DD_writer", "ir", ("instructions", node(0x556F), "flagsWritten"), ["ZF"])
    put("IR_wrong_DD_injection", "ir", ("instructions", node(0x5571), "form", "ddMode"), "1")
    put("IR_LB_wrong_incoming_restriction", "ir", ("instructions", node(0x556F), "form", "ddMode"), "0")
    put("IR_wrong_r0", "ir", ("instructions", node(0x5575), "form", "operands", 1, "name"), "r1")
    put("IR_wrong_r1", "ir", ("instructions", node(0x557F), "form", "operands", 0, "name"), "r0")
    put("IR_wrong_local_bank", "ir", ("context", "localBank"), 0x100)
    put("IR_wrong_LRB", "ir", ("context", "lrb"), 0x20)
    put("IR_wrong_current_page", "ir", ("context", "currentPage"), 0x200)
    put("IR_unknown_SCB_fixed_assumption", "ir", ("context", "scb"), "Always2")
    put("IR_wrong_page_address", "ir", ("instructions", node(0x556F), "form", "operands", 1, "address"), 0x18F)
    put("IR_odd_word_CMP", "ir", ("instructions", node(0x5578), "form", "operands", 0, "address"), 0x197)
    put("IR_CMP_byte_width", "ir", ("instructions", node(0x5578), "form", "operands", 0, "widthBits"), 8)
    put("IR_wrong_CMP_immediate", "ir", ("instructions", node(0x5578), "form", "operands", 1, "value"), 0xC1)
    put("IR_immediate_as_RAM", "ir", ("instructions", node(0x5578), "form", "operands", 1),
        {"kind": "CurrentPageRam", "address": 0xC0, "widthBits": 16,
         "selectorField": "n8", "requiredLrb": 33, "byteOrder": "LittleEndian"})
    put("IR_branch_wrong_target", "ir", ("instructions", node(0x557D), "successors"), [0x5592, 0x557F])
    put("IR_cycle", "ir", ("instructions", node(0x5594), "successors"), [0x556F])
    put("IR_missing_terminal", "ir", ("stopBeforePcs",), [0x5596])
    put("IR_execute_P2_boundary", "ir", ("instructions", node(0x5594), "successors"), [0x5598])
    put("IR_JLT_reads_ZF", "ir", ("instructions", node(0x557D), "flagsRead"), ["ZF"])
    put("IR_JLT_predicate_ZF", "ir", ("instructions", node(0x557D), "branchPredicate", "flag"), "ZF")
    put("IR_CMP_missing_CF_writer", "ir", ("instructions", node(0x5578), "flagsWritten"), ["ZF"])
    put("IR_intervening_CF_clobber", "ir", ("instructions", node(0x557D), "effects"),
        [{"op": "AssignCarryFromOldBit", "type": "bool", "source": "AL", "bit": 7}] +
        ir["instructions"][node(0x557D)]["effects"])
    put("IR_ROL_circular_rotate", "ir", ("instructions", node(0x5572), "effects", 0, "carryInput"), "OldBit7")
    put("IR_ROL_wrong_CF_source", "ir", ("instructions", node(0x5572), "flagsRead"), ["ZF"])
    put("IR_JBS_changes_flags", "ir", ("instructions", node(0x5585), "flagsWritten"), ["CF", "ZF", "HC", "DD"])
    put("IR_gate_order_reversed", "ir", ("instructions", node(0x5582), "successors"), [0x5588])
    put("IR_forced_second_gate_read", "ir", ("instructions", node(0x5585), "inputs"), ["RAM012A:u8", "RAM0124:u8"])
    put("IR_forced_second_gate_effect", "ir", ("instructions", node(0x5585), "effects"),
        ir["instructions"][node(0x5588)]["effects"] + ir["instructions"][node(0x5585)]["effects"])
    put("IR_reordered_conditional_writes", "ir", ("instructions", node(0x5588), "successors"), [0x5592, 0x558E])
    put("IR_removed_same_value_STB", "ir", ("instructions", node(0x55C1), "effects", 0, "sameValueWrite"), "RemoveIfEqual")
    put("IR_missing_018E_RMW", "ir", ("instructions", node(0x5572), "effects"), [])
    put("IR_illegal_012A_store", "ir", ("instructions", node(0x55C1), "effects", 0, "destination", "address"), 0x12A)
    put("IR_AH_clobber", "ir", ("instructions", node(0x556F), "effects", 0, "preserveHighByte"), False)
    put("IR_SSP_modified", "ir", ("instructions", node(0x557F), "effects", 0, "destination"),
        {"kind": "SystemStackPointer", "widthBits": 16, "address": 0})
    put("IR_missing_other_PSW_preservation", "ir", ("instructions", node(0x5578), "flagsPreserved"), ["HC", "DD"])
    put("IR_invented_SF_semantics", "ir", ("stateTypes", "SF"), "NativeBoolAtPSW11")
    put("IR_host_owner_claimed_native", "ir", ("provenanceRestrictions", "nativeOwnerAcceptedFromHost"), True)
    put("IR_unverified_physical_role", "ir", ("provenanceRestrictions", "word0196PhysicalRole"), "RPM")
    cases.append(("IR_missing_LB_site", lambda c, i: i["instructions"].pop(0)))
    cases.append(("IR_reordered_instructions", lambda c, i: i["instructions"].reverse()))
    cases.append(("IR_extra_P2_site", lambda c, i: i["instructions"].append(
        dict(deepcopy(i["instructions"][-1]), pc=0x5596))))
    # Contract operand/context/provenance/exit substitutions all fail closed.
    put("full_DATA_for_raw_offset", "contract", ("sites", site(0x556F), "typedOperands", 1, "value"), 0x18E)
    put("wrong_raw_page_offset", "contract", ("sites", site(0x556F), "typedOperands", 1, "value"), 0x8F)
    put("odd_EvenPageOffset8", "contract", ("sites", site(0x5578), "typedOperands", 0, "value"), 0x97)
    put("wrong_immediate00C0", "contract", ("sites", site(0x5578), "typedOperands", 1, "value"), 0xC1)
    put("wrong_Immediate8_for16", "contract", ("sites", site(0x5578), "typedOperands", 1, "kind"), "Immediate8")
    put("wrong_Register0", "contract", ("sites", site(0x5575), "typedOperands", 1, "value"), 1)
    put("wrong_Register1", "contract", ("sites", site(0x557F), "typedOperands", 0, "value"), 0)
    put("wrong_Bit7", "contract", ("sites", site(0x5585), "typedOperands", 0, "bit"), 5)
    put("wrong_Bit5", "contract", ("sites", site(0x5588), "typedOperands", 0, "bit"), 7)
    put("wrong_typed_branch_target", "contract", ("sites", site(0x557D), "typedOperands", 0, "value"), 0x5592)
    put("contract_wrong_DD_transfer", "contract", ("sites", site(0x556F), "dd", "transfer"), "PreservesDD")
    put("contract_wrong_DD_selection", "contract", ("sites", site(0x556F), "dd", "selection"), "RequiresDD0")
    put("contract_injected_DD1_requirement", "contract", ("sites", site(0x5571), "dd", "selection"), "RequiresDD1")
    for field, value in (("requiredLRB", 32), ("currentPage", 512), ("localBankBase", 256),
                         ("fixedSCBAssumption", 2), ("LRBRebasingAllowed", True),
                         ("hostPointerCastsAllowed", True), ("localPairByteOrder", "BigEndian")):
        put(f"context_{field}", "contract", ("context", field), value)
    put("entry_invented_subroutine", "contract", ("nativeBoundary", "entry"), "NativeCFunctionEntry")
    put("exit_invented_return", "contract", ("nativeBoundary", "ordinaryReturnAllowed"), True)
    put("terminal_stop_is_RT", "contract", ("nativeBoundary", "stopBoundariesAreRT"), True)
    put("host_source_owner_native", "contract", ("provenance", "nativeOwnerAcceptedFromHost"), True)
    put("physical_RPM_meaning", "contract", ("provenance", "currentWord0196PhysicalRole"), "RPM")
    put("invented_native13_witness", "contract", ("provenance", "historicalNativePath13Witnesses"), 1)
    for idx in range(4):
        put(f"path_wrong_finalDD_{idx}", "contract", ("pathObligations", idx, "finalDD"), 1)
        put(f"path_wrong_finalZF_{idx}", "contract", ("pathObligations", idx, "finalZF"), 1)
        put(f"path_wrong_finalCF_{idx}", "contract", ("pathObligations", idx, "finalCF"), 0 if idx == 0 else 1)
        cases.append((f"path_missing_store_{idx}", lambda c, i, n=idx: c["pathObligations"][n]["orderedWrites"].pop()))
        cases.append((f"path_reordered_writes_{idx}", lambda c, i, n=idx: c["pathObligations"][n]["orderedWrites"].reverse()))
    for flag in ("CF", "ZF", "HC", "DD", "OtherPSW"):
        put(f"future_clobber_{flag}", "contract", ("flagDomain", "futureMayClobber"), True)
    for field in contract["permissions"]:
        put(f"forbidden_permission_{field}", "contract", ("permissions", field), True)
    for field in contract["counts"]:
        put(f"forbidden_actual_generation_{field}", "contract", ("counts", field), 1)
    for field in contract["unresolved"]:
        put(f"unresolved_claim_{field}", "contract", ("unresolved", field), "Established")
    put("generated_target_program_status", "contract", ("classification",), "GeneratedNativeProgram")
    put("target_equivalence_status", "contract", ("classification",), "TargetMachineCodeEquivalenceVerified")
    put("boolean_schema_integer", "contract", ("schemaVersion",), True)
    put("boolean_address_integer", "ir", ("entryPc",), True)
    put("boolean_DD_constant_integer", "contract", ("context", "initialDD", 0), False)
    return cases


def check_builtin_io_source_policy(validate_analysis_source, error_type):
    """Static parsing only: appended fixture calls are never executed."""
    source = (HERE / "typed_lowering_analysis.py").read_text(encoding="utf-8")
    positive = validate_analysis_source(source)
    demand(positive["passed"] is True and positive["codecCalls"] == 0,
           "Current pure analyzer is the source-policy positive control")
    refused = 0
    for fixture in ("input()", "print(1)", "breakpoint()", "help()"):
        try:
            validate_analysis_source(source + "\n" + fixture + "\n")
        except error_type as error:
            demand(error.code == "SourcePolicy", f"Builtin IO static refusal: {fixture}")
            refused += 1
        else:
            raise AssertionError(f"Builtin IO source fixture accepted: {fixture}")
    return {"sourcePolicyChecks": 1 + refused, "sourcePolicyPositiveControls": 1,
            "sourcePolicyBuiltinIORefusals": refused, "sourcePolicyFixtureExecutions": 0}


def run():
    from validate_typed_lowering_contract import (
        analyze_ir, validate_contract, validate_analysis_source, TypedLoweringError,
    )

    source_policy = check_builtin_io_source_policy(validate_analysis_source, TypedLoweringError)
    ir = json.loads((HERE / "word0196_ir.json").read_text(encoding="utf-8"))
    contract = json.loads((HERE / "typed_lowering_contract.json").read_text(encoding="utf-8"))
    before_ir, before_contract = deepcopy(ir), deepcopy(contract)
    results = []
    for domain in ((0,), (1,), (0, 1)):
        result = analyze_ir(ir, initial_dd=domain)
        results.append(result)
        check_analysis(result, domain)
    validated = validate_contract(contract, ir)
    demand({key: validated[key] for key in results[-1]} == results[-1],
           "Contract validation computes the same actual shared analysis")
    demand(set(validated) - set(results[-1]) == {"status", "missingMappings", "ambiguousMappings"},
           "Only explicit documentary contract result fields are additive")
    demand(validated["missingMappings"] == 0 and validated["ambiguousMappings"] == 0 and
           validated["status"] == "M2bd Typed IR-to-Form Mapping and Dataflow Obligations Established",
           "No partial/missing lowering result")
    symbolic = check_symbolic(check_analysis(validated, (0, 1)))
    labels = set()
    mutated_inputs = set()
    negatives = 0
    deterministic_errors = {}
    for label, mutate in negative_mutations(contract, ir):
        demand(label not in labels, f"Duplicate mutation identity {label}")
        labels.add(label)
        changed_contract, changed_ir = deepcopy(contract), deepcopy(ir)
        mutate(changed_contract, changed_ir)
        demand(json.dumps(changed_contract, sort_keys=True) != json.dumps(contract, sort_keys=True) or
               json.dumps(changed_ir, sort_keys=True) != json.dumps(ir, sort_keys=True), f"No-op mutation {label}")
        mutated_inputs.add(json.dumps([changed_contract, changed_ir], sort_keys=True))
        first = None
        for repeat in range(2):
            try:
                validate_contract(changed_contract, changed_ir)
            except TypedLoweringError as error:
                observed = (error.code, error.path)
                demand(type(error.code) is str and error.code and type(error.path) is str and error.path,
                       f"Explicit deterministic error {label}")
                if repeat == 0:
                    first = observed
                else:
                    demand(observed == first, f"Repeat changed refusal identity {label}")
            else:
                raise AssertionError(f"Invalid real IR/contract mutation accepted: {label}")
        negatives += 1
        deterministic_errors[label] = {"code": first[0], "path": first[1]}
    demand(ir == before_ir and contract == before_contract, "Validation does not mutate source objects")
    return {"passed": True, "milestone": "M2bd", "classification": "InventedStaticLoweringChecksOnly",
            "correctMappings": 18, "uniqueFormIdentities": 15, "initialDDDomains": 3,
            "pathObligationChecks": 12, "flagDependencyRows": 54, "negativeMutations": negatives,
            "dataLivenessRows": 54,
            "uniqueMutatedInputs": len(mutated_inputs), "overlappingMutationLabels": negatives - len(mutated_inputs),
            "deterministicRefusalCalls": 2 * negatives, "refusalIdentities": deterministic_errors,
            "failed": 0, "skipped": 0, "firstMismatch": None, **symbolic, **source_policy,
            "actualROMExecutions": 0, "encoderOriginalSiteCalls": 0, "decoderNativeFragmentCalls": 0,
            "emittedTargetBytes": 0, "instructionStreams": 0, "nativeWriteJournalsCreated": 0,
            "historicalNative13StepWitnesses": 0}


if __name__ == "__main__":
    if sys.argv[1:] == ["--observe-absent"]:
        absent = not (HERE / "validate_typed_lowering_contract.py").exists()
        demand(absent, "Absent observation requires a genuinely absent analyzer")
        print(json.dumps({"status": "AnalyzerNotImplemented", "analyzerCalls": 0,
                          "fakeRedFailure": False}, sort_keys=True))
    else:
        demand(len(sys.argv) == 1, "No arbitrary file/ROM or execution input")
        print(json.dumps(run(), sort_keys=True))
