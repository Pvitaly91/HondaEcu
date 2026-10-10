"""Bounded primary-reviewed static IR analysis; no codecs, CPU, IO or codegen.

Expressions are obligations over symbolic inputs, not concrete instruction
execution. Original PCs are audit identities only, never placement authority.
All intermediate flag effects and same-value writes remain mandatory even
where backward functional liveness says their scalar values are dead.
"""
from __future__ import annotations

import json

from independent_encoder import FormId


FLAGS = ("CF", "ZF", "HC", "DD") + tuple(f"PSW{i}" for i in range(12))
GROUP_FLAGS = ("CF", "ZF", "HC", "DD", "OtherPSW")
ENTRY = 0x556F
STOPS = (0x5596, 0x55C5)
# Independently reviewed native identity, NOT an encoding or opcode table.
# pc -> form id, native mnemonic, length, DD mode, pattern identity, operand
# address/immediate, primary PDF page, printed page, historical C annotation.
SITE_PROFILE = {
    0x556F: ("lb-a-page", "LB A, off N8", 2, "R", 747, 0x18E, 124, "3-70", "IR556F"),
    0x5571: ("sllb-a", "SLLB A", 1, "0", 2198, None, 197, "3-144", "IR5571"),
    0x5572: ("rolb-page", "ROLB off N8", 3, "U", 1862, 0x18E, 173, "3-120", "IR5572"),
    0x5575: ("lb-a-r0", "LB A, r0", 1, "R", 739, 0x108, 124, "3-70", "IR5575"),
    0x5576: ("andb-a-page", "ANDB A, off N8", 2, "0", 333, 0x18E, 76, "3-24", "IR5576"),
    0x5578: ("cmp-page-imm16", "CMP off N8, #N16", 5, "U", 498, 0x196, 90, "3-38", "IR5578"),
    0x557D: ("jlt-rel8", "JLT rel8", 2, "U", 719, None, 120, "3-66", "IR557D"),
    0x557F: ("movb-r1-page", "MOVB r1, off N8", 3, "U", 1504, 0x117, 153, "3-99", "IR557F"),
    0x5582: ("andb-page-a", "ANDB off N8, A", 3, "U", 349, 0x117, 77, "3-25", "IR5582"),
    0x5585: ("jbs-page-bit7", "JBS off N8.7, rel8", 3, "U", 716, 0x12A, 119, "3-65", "IR5585/5588"),
    0x5588: ("jbs-page-bit5", "JBS off N8.5, rel8", 3, "U", 714, 0x124, 119, "3-65", "IR5585/5588"),
    0x558B: ("andb-page-a", "ANDB off N8, A", 3, "U", 349, 0x18F, 77, "3-25", "IR558B/558E"),
    0x558E: ("orb-page-imm8", "ORB off N'8, #N8", 4, "U", 1678, 0x12A, 163, "3-110", "IR558B/558E"),
    0x5592: ("lb-a-page", "LB A, off N8", 2, "R", 747, 0x18F, 124, "3-70", "IR5592/5594"),
    0x5594: ("orb-a-imm8", "ORB A, #N8", 2, "0", 1619, 0xF0, 160, "3-107", "IR5592/5594"),
    0x55BF: ("lb-a-imm8", "LB A, #N8", 2, "R", 738, 0x0F, 124, "3-70", "IR55BF/55C1/55C3"),
    0x55C1: ("stb-a-page", "STB A, off N8", 2, "0", 2301, 0x117, 208, "3-155", "IR55BF/55C1/55C3"),
    0x55C3: ("stb-a-page", "STB A, off N8", 2, "0", 2301, 0x18F, 208, "3-155", "IR55BF/55C1/55C3"),
}
SUCCESSORS = {
    0x556F: [0x5571], 0x5571: [0x5572], 0x5572: [0x5575],
    0x5575: [0x5576], 0x5576: [0x5578], 0x5578: [0x557D],
    0x557D: [0x55BF, 0x557F], 0x557F: [0x5582], 0x5582: [0x5585],
    0x5585: [0x5592, 0x5588], 0x5588: [0x5592, 0x558B],
    0x558B: [0x558E], 0x558E: [0x5592], 0x5592: [0x5594],
    0x5594: [0x5596], 0x55BF: [0x55C1], 0x55C1: [0x55C3], 0x55C3: [0x55C5],
}
IR_METADATA = json.loads(r'''{
  "schemaVersion": 1,
  "classification": "ReviewedInstructionFaithfulOfflineIR",
  "entryPc": 21871,
  "stopBeforePcs": [
    21910,
    21957
  ],
  "context": {
    "lrb": 33,
    "currentPage": 256,
    "localBank": 264,
    "scb": "DerivedPSWLowThreeBits",
    "requiredIncomingDD": "Either;556FresetsDD0",
    "aliasesOutsideDeclaredFields": "NotEstablished",
    "instructionExtents": "IndependentlyComparedToProtectedOriginalAndListing",
    "physicalNames": "Unknown",
    "cycles": "Excluded;NoCycleEquivalenceClaim"
  },
  "stateTypes": {
    "AL": "u8",
    "AH": "u8",
    "A": "u16",
    "PSW": "u16",
    "PC": "pc16",
    "RAMByte": "u8",
    "RAMWord": "u16",
    "CF": "bool",
    "ZF": "bool",
    "HC": "bool",
    "DD": "bool"
  },
  "numericRules": {
    "unsignedOnly": true,
    "byteTruncation": "Modulo256",
    "wordAccess": "EvenLittleEndian",
    "loadByteExtension": "None;AHpreserved",
    "signExtension": "NoneInThisFragment",
    "accumulatorByteOperations": "DD0;EstablishedBy556F"
  },
  "retainedState": [
    "AH",
    "HC",
    "OtherPSW",
    "LRB",
    "X1",
    "X2",
    "DP",
    "USP",
    "SSP",
    "SF",
    "Halted",
    "RAM0124",
    "RAM0128",
    "RAM0196",
    "RAM0197",
    "localr0",
    "localr2..r7"
  ],
  "provenanceRestrictions": {
    "nativeOwnerAcceptedFromHost": false,
    "hostContext": "OfflineAnnotationOnly",
    "actualRuntimeSource": "NotEstablished",
    "word0196PhysicalRole": "Unknown"
  }
}''')
NODE_KEYS = {"pc", "form", "incomingContext", "inputs", "outputs", "flagsRead",
             "flagsWritten", "flagsPreserved", "effects", "branchPredicate", "successors", "provenance"}
FORM_KEYS = {"mnemonic", "pinnedPatternIndex", "length", "ddMode", "parsedOperation", "operands"}
ERROR_CODES = frozenset(("Shape", "IRContext", "IRInventory", "CFG", "FormMapping",
                        "Operand", "DDEffect", "DDConflict", "FlagEffect", "FlagDependency",
                        "Effect", "TerminalInvariant", "Contract", "SourceIdentity", "SourcePolicy"))
PRESERVED_CONTEXT = ("AH", "HC", "OtherPSW", "SCB", "LRB", "X1", "X2", "DP",
                     "USP", "SSP", "SFUninterpreted", "localr0", "localr2..r7",
                     "RAM0124", "RAM0128", "RAM0196", "RAM0197")


class TypedLoweringError(ValueError):
    """Deterministic refusal with no partial analysis or execution authority."""

    def __init__(self, code: str, path: str):
        if code not in ERROR_CODES or type(path) is not str:
            raise ValueError("Invalid static error definition")
        self.code = code
        self.path = path
        self.args = (f"{code}: {path}",)


def demand(condition, code, path):
    if not condition:
        raise TypedLoweringError(code, path)


def strict_same(value, expected):
    if type(value) is not type(expected):
        return False
    if type(value) is dict:
        return value.keys() == expected.keys() and all(strict_same(value[k], expected[k]) for k in value)
    if type(value) in (list, tuple):
        return len(value) == len(expected) and all(strict_same(a, b) for a, b in zip(value, expected))
    return value == expected


def expect(value, expected, code, path):
    demand(strict_same(value, expected), code, path)


def _page(address, width=8, selector="n8"):
    return {"kind": "CurrentPageRam", "address": address, "widthBits": width,
            "selectorField": selector, "requiredLrb": 0x21,
            "byteOrder": "LittleEndian" if width == 16 else "NotApplicable"}


def _acc():
    return {"kind": "AccumulatorLow", "name": "AL", "widthBits": 8, "address": None}


def _local(number):
    return {"kind": "LocalRegister", "name": f"r{number}", "widthBits": 8, "address": 0x108 + number}


def _imm(value, width=8):
    return {"kind": "CodeOwnedImmediate", "value": value, "widthBits": width}


def _zf(value):
    return {"op": "AssignZeroFlag", "type": "bool", "value": value}


def _ordered(op, destination, **fields):
    return {"op": op, "type": "u8", "destination": destination, **fields,
            "orderedWrite": True, "sameValueWrite": "RetainFreshOrdinal"}


def _semantic_profile(pc):
    """Own primary semantic primitives, not copied executable operations."""
    form, _, _, _, _, operand, _, _, _ = SITE_PROFILE[pc]
    if form in ("lb-a-page", "lb-a-r0", "lb-a-imm8"):
        source = (_page(operand) if form == "lb-a-page" else
                  _local(0) if form == "lb-a-r0" else _imm(operand))
        inputs = ([f"RAM{operand:04X}:u8"] if form != "lb-a-imm8" else []) + ["AH:u8"]
        effects = [{"op": "LoadAccumulatorLow", "type": "u8", "source": source,
                    "extension": "None", "preserveHighByte": True},
                   _zf("AL"), {"op": "AssignDataDescriptor", "type": "bool", "value": False}]
        return [ _acc(), source ], inputs, ["AL:u8"], [], ["ZF", "DD"], effects, None
    if form == "sllb-a":
        effects = [{"op": "LogicalShiftLeft", "type": "u8", "source": "AL", "distance": 1,
                    "truncation": "Modulo256", "zeroFill": True},
                   {"op": "AssignCarryFromOldBit", "type": "bool", "source": "AL", "bit": 7}]
        return [_acc()], ["AL:u8"], ["AL:u8"], [], ["CF"], effects, None
    if form == "rolb-page":
        effects = [_ordered("ReadModifyWriteRotateThroughCarry", _page(operand), direction="Left",
                            distance=1, carryInput="IncomingCF", carryOutput="OldBit7", truncation="Modulo256")]
        return [_page(operand)], [f"RAM{operand:04X}:u8", "CF:bool"], [f"RAM{operand:04X}:u8"], ["CF"], ["CF"], effects, None
    if form == "andb-a-page":
        effects = [{"op": "BitwiseAnd", "type": "u8", "destination": _acc(), "left": "AL",
                    "right": _page(operand), "preserveHighByte": True}, _zf("AL")]
        return [_acc(), _page(operand)], ["AL:u8", f"RAM{operand:04X}:u8"], ["AL:u8"], [], ["ZF"], effects, None
    if form == "cmp-page-imm16":
        effects = [{"op": "UnsignedCompare", "type": "u16", "left": _page(operand, 16),
                    "right": _imm(0xC0, 16), "carryMeaning": "UnsignedBorrow", "zeroMeaning": "Equal",
                    "accumulatorWrite": False, "ramWrite": False, "extension": "None"}]
        return [_page(operand, 16), _imm(0xC0, 16)], ["RAM0196:u16"], [], [], ["CF", "ZF"], effects, None
    if form == "movb-r1-page":
        effects = [_ordered("CopyByte", _local(1), source=_page(operand))]
        return [_local(1), _page(operand)], ["RAM0117:u8"], ["RAM0109:u8"], [], [], effects, None
    if form == "andb-page-a":
        effects = [_ordered("ReadModifyWriteAnd", _page(operand), source="AL"), _zf("WriteResult")]
        return [_page(operand), _acc()], [f"RAM{operand:04X}:u8", "AL:u8"], [f"RAM{operand:04X}:u8"], [], ["ZF"], effects, None
    if form == "orb-page-imm8":
        effects = [_ordered("ReadModifyWriteOr", _page(operand, selector="n8_alt"), source=_imm(1)), _zf("WriteResult")]
        return [_page(operand, selector="n8_alt"), _imm(1)], ["RAM012A:u8"], ["RAM012A:u8"], [], ["ZF"], effects, None
    if form == "orb-a-imm8":
        effects = [{"op": "BitwiseOr", "type": "u8", "destination": _acc(), "left": "AL",
                    "right": _imm(operand), "preserveHighByte": True}, _zf("AL")]
        return [_acc(), _imm(operand)], ["AL:u8", "AH:u8"], ["AL:u8"], [], ["ZF"], effects, None
    if form == "stb-a-page":
        effects = [_ordered("StoreByte", _page(operand), source="AL")]
        return [_acc(), _page(operand)], ["AL:u8"], [f"RAM{operand:04X}:u8"], [], [], effects, None
    true_pc, false_pc = SUCCESSORS[pc]
    if form == "jlt-rel8":
        predicate = {"op": "FlagIsSet", "type": "bool", "flag": "CF"}
        condition, operands, inputs, flags = "CF", [], ["CF:bool"], ["CF"]
    else:
        bit = 7 if form == "jbs-page-bit7" else 5
        predicate = {"op": "BitIsSet", "type": "bool", "address": operand, "bit": bit}
        condition, operands, inputs, flags = predicate, [_page(operand)], [f"RAM{operand:04X}:u8"], []
    effects = [{"op": "ConditionalJump", "type": "pc16", "condition": condition,
                "ifTrue": true_pc, "ifFalse": false_pc}]
    return operands, inputs, [], flags, [], effects, predicate


def _memory_location(value):
    mode = "LocalRegister" if value["kind"] == "LocalRegister" else "CurrentPage"
    return {"address": value["address"], "widthBits": value["widthBits"], "mode": mode,
            "byteOrder": "LittleEndian" if value["widthBits"] == 16 else "Byte"}


def _lowered_site(node):
    pc = node["pc"]
    form, _, length, dd_mode, _, address, page, printed, _ = SITE_PROFILE[pc]
    # Shared FormId is used as a type identity only. Never any codec function.
    demand(FormId(form).value == form, "FormMapping", f"{pc:04X}.FormId")
    if form in ("lb-a-page", "andb-a-page", "stb-a-page"):
        operands = [{"kind": "AccumulatorA"}, {"kind": "PageOffset8", "value": address - 0x100}]
    elif form == "sllb-a":
        operands = [{"kind": "AccumulatorA"}]
    elif form == "rolb-page":
        operands = [{"kind": "PageOffset8", "value": address - 0x100}]
    elif form == "lb-a-r0":
        operands = [{"kind": "AccumulatorA"}, {"kind": "Register0", "value": 0}]
    elif form == "cmp-page-imm16":
        operands = [{"kind": "EvenPageOffset8", "value": address - 0x100}, {"kind": "Immediate16", "value": 0xC0}]
    elif form == "movb-r1-page":
        operands = [{"kind": "Register1", "value": 1}, {"kind": "PageOffset8", "value": address - 0x100}]
    elif form == "andb-page-a":
        operands = [{"kind": "PageOffset8", "value": address - 0x100}, {"kind": "AccumulatorA"}]
    elif form == "jlt-rel8":
        operands = [{"kind": "TargetPC16", "value": node["successors"][0]}]
    elif form.startswith("jbs-page-bit"):
        bit = 7 if form == "jbs-page-bit7" else 5
        operands = [{"kind": f"PageBit{bit}", "offset": address - 0x100, "bit": bit},
                    {"kind": "TargetPC16", "value": node["successors"][0]}]
    elif form == "orb-page-imm8":
        operands = [{"kind": "PageOffset8", "value": address - 0x100}, {"kind": "Immediate8", "value": 1}]
    else:
        operands = [{"kind": "AccumulatorA"}, {"kind": "Immediate8", "value": address}]
    reads, writes = [], []
    for effect in node["effects"]:
        op = effect["op"]
        if op == "LoadAccumulatorLow" and effect["source"]["kind"] != "CodeOwnedImmediate":
            reads.append(_memory_location(effect["source"]))
        elif op == "BitwiseAnd":
            reads.append(_memory_location(effect["right"]))
        elif op == "UnsignedCompare":
            reads.append(_memory_location(effect["left"]))
        elif op == "CopyByte":
            reads.append(_memory_location(effect["source"]))
        elif op.startswith("ReadModifyWrite"):
            reads.append(_memory_location(effect["destination"]))
        elif op == "ConditionalJump" and type(effect["condition"]) is dict:
            reads.append(_memory_location(_page(effect["condition"]["address"])))
        if op in ("CopyByte", "StoreByte") or op.startswith("ReadModifyWrite"):
            writes.append({**_memory_location(effect["destination"]), "operation": op,
                           "ordered": effect["orderedWrite"], "sameValueWrite": effect["sameValueWrite"]})
    functional = [flag for flag in node["flagsRead"] if flag != "DD"]
    branch = None
    if node["branchPredicate"] is not None:
        predicate = node["branchPredicate"]
        pred = ({"kind": "FlagEquals", "flag": predicate["flag"], "value": 1}
                if predicate["op"] == "FlagIsSet" else
                {"kind": "MemoryBitEquals", "address": predicate["address"], "bit": predicate["bit"], "value": 1})
        distance = node["successors"][0] - (pc + length)
        demand(-128 <= distance <= 127 and pc + length <= 0xFFFF, "CFG", f"{pc:04X}.relativeDistance")
        branch = {"predicate": pred, "producerPc": 0x5578 if form == "jlt-rel8" else None,
                  "trueTarget": node["successors"][0], "falseTarget": node["successors"][1],
                  "mathematicalSignedDistance": distance}
    return {"pc": pc, "formId": form, "length": length, "typedOperands": operands,
            "dataWidthBits": None if form == "jlt-rel8" else 16 if form == "cmp-page-imm16" else 8,
            "dd": {"selection": "RequiresDD0" if dd_mode == "0" else "AcceptsBothIncomingDD",
                   "transfer": "SetsDD0WhenExecuted" if dd_mode == "R" else "PreservesDD"},
            "flags": {"functionalRead": functional, "written": list(node["flagsWritten"]),
                      "preserved": list(node["flagsPreserved"]), "selectionRead": ["DD"] if dd_mode == "0" else []},
            "memory": {"reads": reads, "writes": writes}, "successors": list(node["successors"]), "branch": branch,
            "primary": {"pdfPage": page, "printedPage": "3-66/3-67" if form == "jlt-rel8" else printed}}


def _graph(nodes):
    edges, postorder, visited, active, paths = [], [], set(), set(), []
    def visit(pc, path):
        if pc in STOPS:
            paths.append((path, pc))
            return
        demand(pc in nodes, "CFG", f"undefinedSuccessor.{pc:04X}")
        demand(pc not in active, "CFG", f"cycle.{pc:04X}")
        active.add(pc)
        node = nodes[pc]
        demand(type(node["successors"]) is list and 1 <= len(node["successors"]) <= 2
               and all(type(x) is int and 0 <= x <= 65535 for x in node["successors"]),
               "CFG", f"{pc:04X}.successors")
        demand(len(set(node["successors"])) == len(node["successors"]), "CFG", f"{pc:04X}.duplicateSuccessor")
        for successor in node["successors"]:
            edges.append([pc, successor])
            visit(successor, path + [pc])
        active.remove(pc)
        if pc not in visited:
            visited.add(pc)
            postorder.append(pc)
    visit(ENTRY, [])
    demand(visited == set(nodes), "CFG", "unreachableSite")
    unique_edges = []
    for edge in edges:
        if edge not in unique_edges:
            unique_edges.append(edge)
    return unique_edges, list(reversed(postorder)), paths


def _dd_analysis(nodes, topo, initial_dd):
    demand(type(initial_dd) is tuple and initial_dd
           and all(type(x) is int and x in (0, 1) for x in initial_dd)
           and len(set(initial_dd)) == len(initial_dd), "Shape", "initialDD")
    incoming = {pc: set() for pc in nodes}
    incoming[ENTRY] = set(initial_dd)
    outgoing, rows = {}, {}
    for pc in topo:
        node = nodes[pc]
        may = incoming[pc]
        demand(may, "DDConflict", f"{pc:04X}.unreachableDD")
        if node["form"]["ddMode"] == "0":
            demand(may == {0}, "DDConflict", f"{pc:04X}.RequiresDD0")
        result = set(may)
        for effect in node["effects"]:
            if effect.get("op") == "AssignDataDescriptor":
                demand(type(effect.get("value")) is bool, "DDEffect", f"{pc:04X}.DDtransfer")
                result = {int(effect["value"])}
        outgoing[pc] = result
        for successor in node["successors"]:
            if successor in incoming:
                incoming[successor].update(result)
            else:
                demand(result == {0}, "DDConflict", f"{successor:04X}.terminalDD")
        rows[pc] = {"pc": pc, "incomingMay": sorted(may),
                    "incomingMust": next(iter(may)) if len(may) == 1 else None,
                    "outgoingMay": sorted(result), "outgoingMust": next(iter(result)) if len(result) == 1 else None,
                    "selection": "RequiresDD0" if node["form"]["ddMode"] == "0" else "AcceptsBothIncomingDD",
                    "transfer": "SetsDD0WhenExecuted" if node["form"]["ddMode"] == "R" else "PreservesDD",
                    "incomingKnowledge": "IncomingDDUnknown" if len(may) > 1 else f"KnownDD{next(iter(may))}"}
    return [rows[pc] for pc in SITE_PROFILE]


def _expanded(group):
    return [f for f in FLAGS if f in group or (f.startswith("PSW") and "OtherPSW" in group)]


def _flag_dataflow(nodes, topo):
    before, after, uses, kills = {}, {}, {}, {}
    predecessors = {pc: [] for pc in nodes}
    for pc, node in nodes.items():
        for succ in node["successors"]:
            if succ in predecessors:
                predecessors[succ].append(pc)
    for pc in topo:
        before[pc] = {flag: ({"Initial"} if pc == ENTRY else
                            set().union(*(after[p][flag] for p in predecessors[pc]))) for flag in FLAGS}
        kills[pc] = set(nodes[pc]["flagsWritten"])
        uses[pc] = set(nodes[pc]["flagsRead"])  # DD is separately identified as selection in output.
        after[pc] = {flag: ({pc} if flag in kills[pc] else set(before[pc][flag])) for flag in FLAGS}
    live_in, live_out = {}, {}
    for pc in reversed(topo):
        needed = set().union(*(set(FLAGS) if succ in STOPS else live_in[succ] for succ in nodes[pc]["successors"]))
        live_out[pc] = needed
        live_in[pc] = uses[pc] | (needed - kills[pc])
    rows = []
    for pc in SITE_PROFILE:
        functional = [f for f in nodes[pc]["flagsRead"] if f != "DD"]
        rows.append({"pc": pc, "functionalRead": functional, "formSelectionRead": ["DD"] if "DD" in uses[pc] else [],
                     "written": list(nodes[pc]["flagsWritten"]), "preserved": _expanded(nodes[pc]["flagsPreserved"]),
                     "reachingWriters": {f: sorted(before[pc][f], key=str) for f in FLAGS},
                     "reachingWritersOut": {f: sorted(after[pc][f], key=str) for f in FLAGS},
                     "liveIn": [f for f in FLAGS if f in live_in[pc]], "liveOut": [f for f in FLAGS if f in live_out[pc]],
                     "initialValueLive": {f: "Initial" in before[pc][f] and f in live_in[pc] for f in FLAGS},
                     "mayClobber": {f: False for f in FLAGS}, "allPathsObligation": True,
                     "intermediateWritesMandatory": True})
    for consumer, writer in ((0x5572, 0x5571), (0x557D, 0x5578)):
        demand(before[consumer]["CF"] == {writer}, "FlagDependency", f"{consumer:04X}.CFproducer")
    return rows


def _constant(value):
    return ["const", value]


def _expression(op, *args):
    # Small abstract simplification proves terminalZF without executing a CPU.
    if op == "zero8":
        value = args[0]
        if value[0] == "const":
            return _constant(int(value[1] == 0))
        if value[0] == "or8" and any(a[0] == "const" and a[1] != 0 for a in value[1:]):
            return _constant(0)
    return [op, *args]


def _path_obligations(nodes, sites, pcs, stop):
    memory = {address: ["input", f"RAM{address:04X}"] for address in
              (*range(0x108, 0x110), 0x117, 0x124, 0x128, 0x12A, 0x18E, 0x18F, 0x196, 0x197)}
    # RAM0196 input is an abstract reviewedLE u16 value; both physical byte aliases
    # remain preserved. No host word loads, pointer casts or RAM00C0 reads exist.
    symbols = {name: ["input", name] for name in ("AL", "AH", "CF", "ZF", "HC", "DD", "OtherPSW")}
    conditions, accesses, writes, flag_obligations = [], [], [], []
    writers = {f: "Initial" for f in GROUP_FLAGS}
    for index, pc in enumerate(pcs):
        node, site = nodes[pc], sites[pc]
        old_al, write_result = symbols["AL"], None
        for read in site["memory"]["reads"]:
            accesses.append({"site": pc, "mode": "Read", "address": read["address"], "widthBits": read["widthBits"]})
        for effect in node["effects"]:
            op = effect["op"]
            if op == "LoadAccumulatorLow":
                source = effect["source"]
                symbols["AL"] = (_constant(source["value"]) if source["kind"] == "CodeOwnedImmediate" else memory[source["address"]])
            elif op == "LogicalShiftLeft":
                symbols["AL"] = _expression("shl8", old_al)
            elif op == "AssignCarryFromOldBit":
                symbols["CF"] = _expression("bit7", old_al)
            elif op == "ReadModifyWriteRotateThroughCarry":
                addr = effect["destination"]["address"]
                old = memory[addr]
                write_result = _expression("rol8", old, symbols["CF"])
                symbols["CF"] = _expression("bit7", old)
                memory[addr] = write_result
            elif op == "BitwiseAnd":
                symbols["AL"] = _expression("and8", old_al, memory[effect["right"]["address"]])
            elif op == "UnsignedCompare":
                left, right = memory[effect["left"]["address"]], _constant(effect["right"]["value"])
                symbols["CF"], symbols["ZF"] = _expression("lt16", left, right), _expression("eq16", left, right)
            elif op == "CopyByte":
                memory[effect["destination"]["address"]] = memory[effect["source"]["address"]]
            elif op in ("ReadModifyWriteAnd", "ReadModifyWriteOr"):
                addr = effect["destination"]["address"]
                rhs = symbols["AL"] if op == "ReadModifyWriteAnd" else _constant(effect["source"]["value"])
                write_result = _expression("and8" if op == "ReadModifyWriteAnd" else "or8", memory[addr], rhs)
                memory[addr] = write_result
            elif op == "BitwiseOr":
                symbols["AL"] = _expression("or8", old_al, _constant(effect["right"]["value"]))
            elif op == "StoreByte":
                memory[effect["destination"]["address"]] = symbols["AL"]
            elif op == "AssignZeroFlag":
                value = symbols["AL"] if effect["value"] == "AL" else write_result
                demand(value is not None, "Effect", f"{pc:04X}.ZFsource")
                symbols["ZF"] = _expression("zero8", value)
            elif op == "AssignDataDescriptor":
                symbols["DD"] = _constant(int(effect["value"]))
            elif op == "ConditionalJump":
                successor = pcs[index + 1] if index + 1 < len(pcs) else stop
                taken = successor == effect["ifTrue"]
                predicate = node["branchPredicate"]
                text = ("CF" if predicate["op"] == "FlagIsSet" else
                        f"RAM{predicate['address']:04X}.{predicate['bit']}")
                conditions.append({"pc": pc, "predicate": text, "value": taken})
                if predicate["op"] == "FlagIsSet":
                    symbols["CF"] = _constant(int(taken))  # Path assumption, not execution.
            else:
                raise TypedLoweringError("Effect", f"{pc:04X}.unsupportedSymbolicPrimitive")
        for write in site["memory"]["writes"]:
            accesses.append({"site": pc, "mode": "Write", "address": write["address"], "widthBits": write["widthBits"]})
            writes.append({"site": pc, "address": write["address"], "widthBits": write["widthBits"],
                           "sameValueWrite": write["sameValueWrite"]})
        for f in node["flagsWritten"]:
            writers[f] = pc
            flag_obligations.append({"site": pc, "flag": f, "expression": symbols[f]})
    below = stop == 0x55C5
    for flag, expected in (("CF", int(below)), ("ZF", 0), ("DD", 0)):
        expect(symbols[flag], _constant(expected), "TerminalInvariant", f"{stop:04X}.{flag}")
    for name in ("AH", "HC", "OtherPSW"):
        expect(symbols[name], ["input", name], "TerminalInvariant", f"{stop:04X}.{name}")
    symbols["ram"] = {f"RAM{a:04X}": x for a, x in memory.items()}
    symbols["preservedContext"] = list(PRESERVED_CONTEXT)
    return {"pcList": pcs, "stopBeforePc": stop, "instructionCount": len(pcs), "conditions": conditions,
            "memoryAccesses": accesses, "orderedWrites": writes, "terminal": symbols,
            "terminalFlagWriters": {f: writers[f] for f in ("CF", "ZF", "DD")},
            "flagWriteObligations": flag_obligations,
            "historicalWitness": "StaticPrimaryAndInventedCoverage" if len(pcs) == 13 else "HistoricalCompletedPathExists"}


def _data_liveness(nodes, topo):
    reads, kills = {}, {}
    for pc, node in nodes.items():
        reads[pc] = {item.split(":")[0] for item in node["inputs"] if item.split(":")[0] not in GROUP_FLAGS}
        kills[pc] = {item.split(":")[0] for item in node["outputs"]}
    terminal = {"AL", "AH", "LRB", "SCB", "X1", "X2", "DP", "USP", "SSP", "SFUninterpreted"}
    terminal |= {f"RAM{a:04X}" for a in (*range(0x108, 0x110), 0x117, 0x124, 0x128, 0x12A, 0x18E, 0x18F, 0x196, 0x197)}
    incoming, outgoing = {}, {}
    for pc in reversed(topo):
        needed = set().union(*(terminal if s in STOPS else incoming[s] for s in nodes[pc]["successors"]))
        outgoing[pc], incoming[pc] = needed, reads[pc] | (needed - kills[pc])
    return [{"pc": pc, "read": sorted(reads[pc]), "written": sorted(kills[pc]), "liveIn": sorted(incoming[pc]),
             "liveOut": sorted(outgoing[pc]), "mayClobber": False, "memoryEffectsMandatory": True} for pc in SITE_PROFILE]


def analyze_ir(ir, initial_dd=(0, 1)):
    """Analyze a reviewed bounded IR object; no IO or concrete CPU state input.

    Validation does not accept a mutated IR merely because its JSON carries
    a reviewed status. Graph traversal and DD transfer precede exact primary
    effects pinning, followed by real reaching/liveness/symbolic obligations.
    """
    demand(type(ir) is dict and set(ir) == set(IR_METADATA) | {"instructions"}, "Shape", "IR.root")
    expect({k: ir[k] for k in IR_METADATA}, IR_METADATA, "IRContext", "IR.metadata")
    instructions = ir["instructions"]
    demand(type(instructions) is list and len(instructions) == 18, "IRInventory", "IR.instructions")
    demand(all(type(n) is dict and set(n) == NODE_KEYS and type(n.get("pc")) is int and
               type(n.get("form")) is dict and set(n["form"]) == FORM_KEYS and
               type(n.get("effects")) is list and all(type(e) is dict for e in n["effects"]) for n in instructions),
           "Shape", "IR.instructionSchema")
    expect([n["pc"] for n in instructions], list(SITE_PROFILE), "IRInventory", "IR.siteInventory")
    nodes = {n["pc"]: n for n in instructions}
    edges, topo, paths = _graph(nodes)
    dd_rows = _dd_analysis(nodes, topo, initial_dd)
    for pc, node in nodes.items():
        form, mnemonic, length, dd_mode, identity, _, page, printed, tag = SITE_PROFILE[pc]
        operands, inputs, outputs, functional, written, effects, predicate = _semantic_profile(pc)
        expect(node["form"], {"mnemonic": mnemonic, "pinnedPatternIndex": identity, "length": length,
                             "ddMode": dd_mode, "parsedOperation": mnemonic.split()[0], "operands": operands},
               "FormMapping", f"{pc:04X}.formOperands")
        expect(node["inputs"], inputs, "Operand", f"{pc:04X}.inputs")
        expect(node["outputs"], outputs, "Operand", f"{pc:04X}.outputs")
        read = ["DD"] if dd_mode == "0" else functional
        expect(node["flagsRead"], read, "FlagEffect", f"{pc:04X}.flagsRead")
        expect(node["flagsWritten"], written, "FlagEffect", f"{pc:04X}.flagsWritten")
        expect(node["flagsPreserved"], [f for f in GROUP_FLAGS if f not in written], "FlagEffect", f"{pc:04X}.flagsPreserved")
        expect(node["effects"], effects, "Effect", f"{pc:04X}.primaryEffects")
        expect(node["branchPredicate"], predicate, "CFG", f"{pc:04X}.predicate")
        expect(node["successors"], SUCCESSORS[pc], "CFG", f"{pc:04X}.successors")
        expect(node["incomingContext"], ["LRB0021"] + ([] if pc == ENTRY else ["ByteModeEstablishedAt556F"]),
               "IRContext", f"{pc:04X}.incomingContext")
        expect(node["provenance"], {"primaryPdfPage": page, "primaryPrintedPage": printed,
                                   "nativeExtentIndependentlyVerified": True, "cStatementTags": [tag]},
               "IRContext", f"{pc:04X}.provenance")
    demand(sorted(len(p) for p, _ in paths) == [10, 12, 13, 15], "CFG", "fourCompletePaths")
    site_rows = [_lowered_site(nodes[pc]) for pc in SITE_PROFILE]
    sites = {s["pc"]: s for s in site_rows}
    return {"milestone": "M2bd", "classification": "ReviewedStaticTypedLoweringSpecification", "passed": True,
            "instructionSites": 18, "uniqueForms": len({s["formId"] for s in site_rows}), "sites": site_rows,
            "flagDomain": list(FLAGS), "cfg": {"entryPc": ENTRY, "stopBeforePcs": list(STOPS),
            "edges": edges, "topologicalOrder": topo}, "ddAnalysis": dd_rows,
            "flagAnalysis": _flag_dataflow(nodes, topo), "dataLiveness": _data_liveness(nodes, topo),
            "paths": [_path_obligations(nodes, sites, p, stop) for p, stop in paths],
            "encoderCalls": 0, "decoderCalls": 0, "actualROMExecutions": 0, "generatedTargetBytes": 0,
            "nativeExecutionAuthority": False}
