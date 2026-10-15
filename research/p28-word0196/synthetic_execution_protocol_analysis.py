"""M2bk closed static reference obligations, not an instruction-stream executor.

The input is reviewed IR, never PROGRAM bytes. No codec, CPU, Bus, process,
filesystem or external continuation is invoked. Selected PROGRAM extents are
unobserved expectations. Only invented states within this closed profile exist.
"""

import hashlib
import json


class ProtocolError(Exception):
    """Atomic refusal: fixed code, location and stage strings; no partial result."""

    def __init__(self, code, location, stage):
        self.code = code
        self.location = location
        self.stage = stage
        self.args = (code, location, stage)


_PROVENANCE = "InventedOnly_NoNativeGenerationOwner"
_STATIC = "StaticExpectedTrace_NoExecutionObservation"
_MASKS = {"CF": 32768, "ZF": 16384, "HC": 8192, "DD": 4096}
_ALL_FLAGS = ["CF", "ZF", "HC", "DD", "OtherPSW"]
_DATA_KEYS = ["0108", "0109", "010A", "010B", "010C", "010D", "010E", "010F",
              "0117", "0124", "0128", "012A", "018E", "018F", "0196", "0197"]
_ENTRY_KEYS = ["pc", "a", "al", "ah", "psw", "cf", "zf", "hc", "dd", "otherPsw",
               "lrb", "scb", "ssp", "pointingBanks", "sf", "halted"]
_A = {"kind": "AccumulatorLow", "name": "AL", "widthBits": 8, "address": None}

# Reviewed identity, synthetic PC, form, length, DD mode, operation, page, pattern.
# These are source identities and geometry, not opcodes or a decoder.
_SITES = (
    (0x556F, 0x1000, "lb-a-page", 2, "R", "LB", 124, 747),
    (0x5571, 0x1002, "sllb-a", 1, "0", "SLLB", 197, 2198),
    (0x5572, 0x1003, "rolb-page", 3, "U", "ROLB", 173, 1862),
    (0x5575, 0x1006, "lb-a-r0", 1, "R", "LB", 124, 739),
    (0x5576, 0x1007, "andb-a-page", 2, "0", "ANDB", 76, 333),
    (0x5578, 0x1009, "cmp-page-imm16", 5, "U", "CMP", 90, 498),
    (0x557D, 0x100E, "jlt-rel8", 2, "U", "JLT", 120, 719),
    (0x557F, 0x1010, "movb-r1-page", 3, "U", "MOVB", 153, 1504),
    (0x5582, 0x1013, "andb-page-a", 3, "U", "ANDB", 77, 349),
    (0x5585, 0x1016, "jbs-page-bit7", 3, "U", "JBS", 119, 716),
    (0x5588, 0x1019, "jbs-page-bit5", 3, "U", "JBS", 119, 714),
    (0x558B, 0x101C, "andb-page-a", 3, "U", "ANDB", 77, 349),
    (0x558E, 0x101F, "orb-page-imm8", 4, "U", "ORB", 163, 1678),
    (0x5592, 0x1023, "lb-a-page", 2, "R", "LB", 124, 747),
    (0x5594, 0x1025, "orb-a-imm8", 2, "0", "ORB", 160, 1619),
    ("DirectJ_NotBelow", 0x1027, "j-address", 3, "U", "J", 116, None),
    (0x55BF, 0x102A, "lb-a-imm8", 2, "R", "LB", 124, 738),
    (0x55C1, 0x102C, "stb-a-page", 2, "0", "STB", 208, 2301),
    (0x55C3, 0x102E, "stb-a-page", 2, "0", "STB", 208, 2301),
    ("DirectJ_Below", 0x1030, "j-address", 3, "U", "J", 116, None),
)
_COMMON = [0x556F, 0x5571, 0x5572, 0x5575, 0x5576, 0x5578, 0x557D]
_PREFIX = [0x557F, 0x5582, 0x5585]
_END = [0x5592, 0x5594, "DirectJ_NotBelow"]
_PATHS = {
    "A": _COMMON + [0x55BF, 0x55C1, 0x55C3, "DirectJ_Below"],
    "B": _COMMON + _PREFIX + _END,
    "C": _COMMON + _PREFIX + [0x5588] + _END,
    "D": _COMMON + _PREFIX + [0x5588, 0x558B, 0x558E] + _END,
}
_COUNTS = {"A": (11, 5, 3), "B": (13, 9, 3), "C": (14, 10, 3), "D": (16, 12, 5)}
_WRITERS = {"A": [0x5572, 0x55C1, 0x55C3], "B": [0x5572, 0x557F, 0x5582],
            "C": [0x5572, 0x557F, 0x5582],
            "D": [0x5572, 0x557F, 0x5582, 0x558B, 0x558E]}


def _reject(code, location, stage):
    raise ProtocolError(code, location, stage)


def _expect(condition, code, location, stage):
    if not condition:
        _reject(code, location, stage)


def _json_copy(value, location, maximum=200000):
    """Exact primitive types, bounded depth/size, no custom objects or cycles."""
    active = set()
    count = [0]

    def visit(item, depth):
        count[0] += 1
        _expect(count[0] <= maximum and depth <= 48,
                "InputBoundExceeded", location, "Input")
        if item is None or type(item) is bool:
            return item
        if type(item) is int:
            _expect(-0x100000000 <= item <= 0x100000000,
                    "IntegerDomain", location, "Input")
            return item
        if type(item) is str:
            _expect(len(item) <= 65536, "InputBoundExceeded", location, "Input")
            return item
        _expect(type(item) in (list, dict), "JsonType", location, "Input")
        identity = id(item)
        _expect(identity not in active, "InputCycle", location, "Input")
        active.add(identity)
        _expect(len(item) <= 10000, "InputBoundExceeded", location, "Input")
        if type(item) is list:
            result = [visit(child, depth + 1) for child in item]
        else:
            _expect(all(type(key) is str and len(key) <= 256 for key in item),
                    "JsonObjectKey", location, "Input")
            result = {key: visit(child, depth + 1) for key, child in item.items()}
        active.remove(identity)
        return result

    return visit(value, 0)


def _keys(value, keys, location, stage):
    _expect(type(value) is dict and set(value) == set(keys),
            "ClosedShape", location, stage)


def _uint(value, maximum, location, stage="Scenario"):
    _expect(type(value) is int and 0 <= value <= maximum,
            "UnsignedDomain", location, stage)


def _equal(actual, expected, location, stage):
    # Unlike Python equality, JSON equality distinguishes True from integer1.
    _expect(json.dumps(actual, sort_keys=True, separators=(",", ":")) ==
            json.dumps(expected, sort_keys=True, separators=(",", ":")),
            "ReviewedRelationMismatch", location, stage)


def _page(address, width=8, selector="n8"):
    return {"kind": "CurrentPageRam", "address": address, "widthBits": width,
            "selectorField": selector, "requiredLrb": 33,
            "byteOrder": "LittleEndian" if width == 16 else "NotApplicable"}


def _local(number):
    return {"kind": "LocalRegister", "name": "r" + str(number),
            "widthBits": 8, "address": 0x108 + number}


def _imm(value, width=8):
    return {"kind": "CodeOwnedImmediate", "value": value, "widthBits": width}


def _effect(op, value_type="u8", **fields):
    return dict({"op": op, "type": value_type}, **fields)


def _zero(value="AL"):
    return _effect("AssignZeroFlag", "bool", value=value)


def _ordered(op, destination, **fields):
    return _effect(op, destination=destination, orderedWrite=True,
                   sameValueWrite="RetainFreshOrdinal", **fields)


def _reviewed_instruction(pc):
    """Closed primary/source semantic relations, independent of new oracle."""
    operands, effects, reads, writes = [], [], [], []
    predicate = None
    site = next(row for row in _SITES if row[0] == pc)
    successors = [pc + site[3]]
    if pc in (0x556F, 0x5575, 0x5592, 0x55BF):
        source = {0x556F: _page(0x18E), 0x5575: _local(0),
                  0x5592: _page(0x18F), 0x55BF: _imm(15)}[pc]
        operands = [_A, source]
        effects = [_effect("LoadAccumulatorLow", source=source, extension="None",
                           preserveHighByte=True), _zero(),
                   _effect("AssignDataDescriptor", "bool", value=False)]
        writes = ["ZF", "DD"]
    elif pc == 0x5571:
        operands = [_A]
        effects = [_effect("LogicalShiftLeft", source="AL", distance=1,
                           truncation="Modulo256", zeroFill=True),
                   _effect("AssignCarryFromOldBit", "bool", source="AL", bit=7)]
        reads, writes = ["DD"], ["CF"]
    elif pc == 0x5572:
        operands = [_page(0x18E)]
        effects = [_ordered("ReadModifyWriteRotateThroughCarry", operands[0],
                            direction="Left", distance=1, carryInput="IncomingCF",
                            carryOutput="OldBit7", truncation="Modulo256")]
        reads, writes = ["CF"], ["CF"]
    elif pc in (0x5576, 0x5594):
        right = _page(0x18E) if pc == 0x5576 else _imm(240)
        operands = [_A, right]
        effects = [_effect("BitwiseAnd" if pc == 0x5576 else "BitwiseOr",
                           destination=_A, left="AL", right=right,
                           preserveHighByte=True), _zero()]
        reads, writes = ["DD"], ["ZF"]
    elif pc == 0x5578:
        operands = [_page(0x196, 16), _imm(192, 16)]
        effects = [_effect("UnsignedCompare", "u16", left=operands[0],
                           right=operands[1], carryMeaning="UnsignedBorrow",
                           zeroMeaning="Equal", accumulatorWrite=False,
                           ramWrite=False, extension="None")]
        writes = ["CF", "ZF"]
    elif pc == 0x557D:
        successors = [0x55BF, 0x557F]
        predicate = {"op": "FlagIsSet", "type": "bool", "flag": "CF"}
        effects = [_effect("ConditionalJump", "pc16", condition="CF",
                           ifTrue=successors[0], ifFalse=successors[1])]
        reads = ["CF"]
    elif pc == 0x557F:
        operands = [_local(1), _page(0x117)]
        effects = [_ordered("CopyByte", operands[0], source=operands[1])]
    elif pc in (0x5582, 0x558B):
        operands = [_page(0x117 if pc == 0x5582 else 0x18F), _A]
        effects = [_ordered("ReadModifyWriteAnd", operands[0], source="AL"),
                   _zero("WriteResult")]
        writes = ["ZF"]
    elif pc in (0x5585, 0x5588):
        address, bit = (0x12A, 7) if pc == 0x5585 else (0x124, 5)
        operands = [_page(address)]
        successors = [0x5592, pc + 3]
        predicate = {"op": "BitIsSet", "type": "bool", "address": address, "bit": bit}
        effects = [_effect("ConditionalJump", "pc16", condition=predicate,
                           ifTrue=successors[0], ifFalse=successors[1])]
    elif pc == 0x558E:
        operands = [_page(0x12A, selector="n8_alt"), _imm(1)]
        effects = [_ordered("ReadModifyWriteOr", operands[0], source=operands[1]),
                   _zero("WriteResult")]
        writes = ["ZF"]
    elif pc in (0x55C1, 0x55C3):
        operands = [_A, _page(0x117 if pc == 0x55C1 else 0x18F)]
        effects = [_ordered("StoreByte", operands[1], source="AL")]
        reads = ["DD"]
    else:
        _reject("UnreviewedLogicalIdentity", "ir.instructions", "IR")
    return {"operands": operands, "effects": effects, "flagsRead": reads,
            "flagsWritten": writes,
            "flagsPreserved": [flag for flag in _ALL_FLAGS if flag not in writes],
            "branchPredicate": predicate, "successors": successors}


def _check_ir(ir):
    _expect(type(ir) is dict, "ClosedShape", "ir", "IR")
    _equal(ir.get("entryPc"), 0x556F, "ir.entryPc", "IR")
    _equal(ir.get("stopBeforePcs"), [0x5596, 0x55C5], "ir.stopBeforePcs", "IR")
    context = ir.get("context")
    _expect(type(context) is dict, "ClosedShape", "ir.context", "IR")
    for key, value in (("lrb", 33), ("currentPage", 256), ("localBank", 264),
                       ("scb", "DerivedPSWLowThreeBits"),
                       ("requiredIncomingDD", "Either;556FresetsDD0")):
        _equal(context.get(key), value, "ir.context." + key, "IR")
    _equal(ir.get("numericRules"), {
        "unsignedOnly": True, "byteTruncation": "Modulo256",
        "wordAccess": "EvenLittleEndian", "loadByteExtension": "None;AHpreserved",
        "signExtension": "NoneInThisFragment",
        "accumulatorByteOperations": "DD0;EstablishedBy556F"}, "ir.numericRules", "IR")
    original = [row for row in _SITES if type(row[0]) is int]
    rows = ir.get("instructions")
    _expect(type(rows) is list and len(rows) == len(original),
            "InstructionInventory", "ir.instructions", "IR")
    result = {}
    for index, (row, spec) in enumerate(zip(rows, original)):
        loc = "ir.instructions[" + str(index) + "]"
        _expect(type(row) is dict, "ClosedShape", loc, "IR")
        pc, _, _, length, dd_mode, operation, page, pattern = spec
        _equal(row.get("pc"), pc, loc + ".pc", "IR")
        form = row.get("form")
        _expect(type(form) is dict, "ClosedShape", loc + ".form", "IR")
        for key, value in (("length", length), ("ddMode", dd_mode),
                           ("parsedOperation", operation), ("pinnedPatternIndex", pattern)):
            _equal(form.get(key), value, loc + ".form." + key, "IR")
        wanted = _reviewed_instruction(pc)
        _equal(form.get("operands"), wanted["operands"], loc + ".form.operands", "IR")
        for key in ("effects", "flagsRead", "flagsWritten", "flagsPreserved",
                    "branchPredicate", "successors"):
            _equal(row.get(key), wanted[key], loc + "." + key, "IR")
        provenance = row.get("provenance")
        _expect(type(provenance) is dict, "ClosedShape", loc + ".provenance", "IR")
        _equal(provenance.get("primaryPdfPage"), page, loc + ".primaryPdfPage", "IR")
        result[pc] = row
    return result


def _check_program_geometry(composition, contract, ir_rows):
    _expect(type(composition) is dict and type(contract) is dict,
            "ClosedShape", "contracts", "Contract")
    _equal(contract.get("exactBase"), "be7ed4a72dc5f8758bfa4293db0f881ba9bb7536",
           "contract.exactBase", "Contract")
    _equal(contract.get("program"), {
        "space": "PROGRAM", "base": 0x1000, "endExclusive": 0x1033, "length": 51,
        "sha256": "91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1",
        "contentSource": "VerifiedM2bjEmitterOnly_NotLoadedByM2bk",
        "originalRomAllowed": False, "arbitraryStreamAllowed": False, "paddingBytes": 0,
        "mappingCapability": "SyntheticProgramMappingCapabilityNotEstablished"},
        "contract.program", "Program")
    nodes, old_nodes = contract.get("nodes"), composition.get("nodeInventory")
    _expect(type(nodes) is list and len(nodes) == 20 and
            type(old_nodes) is list and len(old_nodes) == 20,
            "InstructionInventory", "contract.nodes", "Geometry")
    by_id = {}
    mapping = {row[0]: row[1] for row in _SITES}
    for index, (node, old, spec) in enumerate(zip(nodes, old_nodes, _SITES)):
        loc = "contract.nodes[" + str(index) + "]"
        _expect(type(node) is dict and type(old) is dict, "ClosedShape", loc, "Geometry")
        identity, pc, form, length, _, _, page, _ = spec
        _equal([node.get("logicalId"), node.get("syntheticPc"), node.get("form"),
                node.get("length"), node.get("primaryPdfPage")],
               [identity, pc, form, length, page], loc + ".identity", "Geometry")
        _equal([old.get("nodeId"), old.get("origin"), old.get("form"),
                old.get("length"), old.get("primaryPdfPage")],
               [identity, pc, form, length, page], "composition.nodeInventory", "Geometry")
        if type(identity) is str:
            target = 0x5596 if identity == "DirectJ_NotBelow" else 0x55C5
            successors, reads, writes = [target], [], []
        else:
            row = ir_rows[identity]
            successors = []
            for successor in row["successors"]:
                if successor == 0x5596:
                    successors.append(mapping["DirectJ_NotBelow"])
                elif successor == 0x55C5:
                    successors.append(mapping["DirectJ_Below"])
                else:
                    successors.append(mapping[successor])
            target = successors[0] if row["branchPredicate"] is not None else None
            reads, writes = row["flagsRead"], row["flagsWritten"]
        _equal(node.get("successors"), successors, loc + ".successors", "CFG")
        _equal(node.get("target"), target, loc + ".target", "CFG")
        _equal(old.get("target"), target, "composition.nodeInventory.target", "CFG")
        _equal(node.get("flagsRead"), reads, loc + ".flagsRead", "Dataflow")
        _equal(node.get("flagsWritten"), writes, loc + ".flagsWritten", "Dataflow")
        if index + 1 < len(_SITES):
            _expect(pc + length == _SITES[index + 1][1],
                    "SegmentContinuity", loc, "Geometry")
        by_id[identity] = node
    _expect(_SITES[-1][1] + _SITES[-1][3] == 0x1033,
            "SegmentContinuity", "contract.nodes", "Geometry")
    _expect(sum(len(node["successors"]) for node in nodes) == 23,
            "CfgEdgeCount", "contract.nodes", "CFG")
    paths = contract.get("paths")
    _keys(paths, "ABCD", "contract.paths", "Paths")
    conditions = {"A": "UnsignedWord0196<192", "B": "UnsignedWord0196>=192AndBit012A7",
                  "C": "UnsignedWord0196>=192AndNotBit012A7AndBit01245",
                  "D": "UnsignedWord0196>=192AndNotBit012A7AndNotBit01245"}
    for path, ids in _PATHS.items():
        value = paths[path]
        count, reads, writes = _COUNTS[path]
        wanted = {"condition": conditions[path], "originalCount": count - 1,
                  "count": count, "terminalPc": 0x55C5 if path == "A" else 0x5596,
                  "logicalIds": ids, "writerIds": _WRITERS[path], "readCount": reads,
                  "writeCount": writes,
                  "historicalWitness": "StaticPrimaryAndInventedCoverage" if path == "C"
                  else "HistoricalCorpusHasOriginalPathWitness_NotNewObservation"}
        _equal(value, wanted, "contract.paths." + path, "Paths")
        visited = set()
        for position, identity in enumerate(ids):
            node = by_id[identity]
            _expect(identity not in visited, "CfgCycle", "contract.paths." + path, "CFG")
            visited.add(identity)
            next_pc = by_id[ids[position + 1]]["syntheticPc"] if position + 1 < count else wanted["terminalPc"]
            _expect(next_pc in node["successors"], "PathEdge", "contract.paths." + path, "CFG")
        _expect(sum(type(item) is str for item in ids) == 1 and type(ids[-1]) is str,
                "ExternalTransferCount", "contract.paths." + path, "Exit")
    return by_id


def _check_contract_obligations(contract):
    _equal(contract.get("entryContexts"), {
        "pc": 4096, "incomingDD": [0, 1], "firstLbEstablishesDD": 0,
        "lrb": 33, "currentPage": 256, "localBank": [264, 272],
        "scb": "IncomingPSWLowThreeBits", "flagMasks": dict(_MASKS, OtherPSW=4095),
        "sf": {"meaning": None, "storage": None, "widthBits": None, "defaultValueAllowed": False},
        "halted": False, "pointingBanks": 8,
        "pointingRegistersPerBank": ["X1", "X2", "DP", "USP"]}, "contract.entryContexts", "Context")
    _equal(contract.get("word0196"), {
        "address": 0x196, "widthBits": 16, "byteOrder": "LittleEndian", "readOnly": True,
        "oddAddressAllowed": False,
        "readNormalization": "LogicalR16MatchesConsecutiveRaw0196Low0197High_NoHiddenOrReorderedByteRead"},
        "contract.word0196", "Data")
    _equal(contract.get("codeOwnedImmediate"), {"space": "PROGRAM", "value": 192,
           "widthBits": 16, "dataReadAllowed": False}, "contract.codeOwnedImmediate", "Data")
    _equal(contract.get("semantics"), {
        "comparison": "Unsigned16BorrowAndEquality", "carryDependencies": [[0x5571, 0x5572], [0x5578, 0x557D]],
        "rolCarryInput": "IncomingCF", "sllCarryOutput": "OldALBit7",
        "rolCarryOutput": "OldDATA018EBit7", "jltPredicate": "CF==1",
        "firstGate": {"address": 0x12A, "bit": 7},
        "secondGate": {"address": 0x124, "bit": 5, "readWhen": "OnlyFirstGateFalse"},
        "directJ": {"space": "PROGRAM", "dataReads": 0, "dataWrites": 0, "sspWrites": 0,
                    "flagWrites": [], "pcOperation": "ReplaceWithImmediate16",
                    "documentaryScope": "ManufacturerFunctionAndFlagTablesOnly_NoRuntimeEvidence"},
        "rolbPrintingConflict": "DescriptionWordLongRetained_ByteHeadingDiagramAndExactFormEstablished_NoNewFix"},
        "contract.semantics", "Semantics")
    _equal(contract.get("instructionBudget"), {"maximum": 16,
        "pathCounts": {path: value[0] for path, value in _COUNTS.items()},
        "safetyBound": 16, "extraVerifiedStepsAllowed": False}, "contract.instructionBudget", "Budget")
    _equal(contract.get("externalExit"), {"anchors": [0x5596, 0x55C5],
        "when": "AfterExactlyOneDirectJ_PCReplaced_BeforeAnyTargetFetch",
        "targetBytesAllowed": False, "stubOpcodesAllowed": False,
        "observation": "SyntheticExternalExitObservationNotRun", "nativeRejoin": "NotEstablished"},
        "contract.externalExit", "Exit")
    rows = contract.get("dataInventory")
    _expect(type(rows) is list and len(rows) == len(_DATA_KEYS),
            "DataInventory", "contract.dataInventory", "Data")
    read_paths = {0x108: "ABCD", 0x117: "BCD", 0x124: "CD", 0x12A: "BCD",
                  0x18E: "ABCD", 0x18F: "BCD", 0x196: "ABCD", 0x197: "ABCD"}
    write_paths = {0x109: "BCD", 0x117: "ABCD", 0x12A: "D", 0x18E: "ABCD", 0x18F: "AD"}
    for index, (key, row) in enumerate(zip(_DATA_KEYS, rows)):
        address = int(key, 16)
        alias = ("r0=low(er0)" if key == "0108" else "r1=high(er0)" if key == "0109"
                 else "EvenLEWord0196" if key in ("0196", "0197")
                 else "ReviewedPotentialWordAliasOnly_NoAdditionalAccess")
        wanted = {"key": key, "address": address, "widthBits": 8,
                  "addressing": "LrbSelectedLocalBank" if address < 0x110 else "CurrentPageOrRetainedByte",
                  "initialOwnership": _PROVENANCE, "readPaths": list(read_paths.get(address, "")),
                  "writePaths": list(write_paths.get(address, "")), "alias": alias, "physicalMeaning": "Unknown"}
        _equal(row, wanted, "contract.dataInventory[" + str(index) + "]", "Data")
    _equal(contract.get("authority"), {
        "actualSyntheticCompositeExecution": "NotRun", "targetCpuExecution": "NotObserved",
        "actualRomExecutions": 0, "targetObjects": 0, "hex": 0, "firmwareBin": 0,
        "firmwareReady": False, "nativeExitIsolation": "NotEstablished",
        "actualDownstreamRejoin": "NotEstablished", "physicalRomPlacement": "NotEstablished",
        "targetProgramEquivalence": "NotEstablished", "firmwareIntegration": "NotEstablished",
        "physicalRpmAvailable": False, "productionAdmissionChanges": False,
        "guiHardwareAllowed": False}, "contract.authority", "Authority")


def _check_scenario(scenario):
    _keys(scenario, ["id", "classification", "entry", "data", "localAliases"], "scenario", "Scenario")
    identity = scenario["id"]
    _expect(type(identity) is str and 1 <= len(identity) <= 96 and
            all(character in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-" for character in identity),
            "ScenarioIdentity", "scenario.id", "Scenario")
    _equal(scenario["classification"], _PROVENANCE, "scenario.classification", "Scenario")
    entry, data, aliases = scenario["entry"], scenario["data"], scenario["localAliases"]
    _keys(entry, _ENTRY_KEYS, "scenario.entry", "Scenario")
    _keys(data, _DATA_KEYS, "scenario.data", "Scenario")
    _keys(aliases, ["r", "er"], "scenario.localAliases", "Scenario")
    for key in ("pc", "a", "psw", "lrb", "ssp"):
        _uint(entry[key], 65535, "scenario.entry." + key)
    for key in ("al", "ah"):
        _uint(entry[key], 255, "scenario.entry." + key)
    for key in ("cf", "zf", "hc", "dd"):
        _uint(entry[key], 1, "scenario.entry." + key)
        _equal(entry[key], int(bool(entry["psw"] & _MASKS[key.upper()])), "scenario.entry." + key, "Scenario")
    _uint(entry["otherPsw"], 4095, "scenario.entry.otherPsw")
    _uint(entry["scb"], 7, "scenario.entry.scb")
    _equal(entry["pc"], 0x1000, "scenario.entry.pc", "Scenario")
    _equal(entry["lrb"], 33, "scenario.entry.lrb", "Scenario")
    _equal(entry["a"], entry["al"] + 256 * entry["ah"], "scenario.entry.a", "Scenario")
    _equal(entry["otherPsw"], entry["psw"] & 4095, "scenario.entry.otherPsw", "Scenario")
    _equal(entry["scb"], entry["psw"] & 7, "scenario.entry.scb", "Scenario")
    _equal(entry["sf"], {"status": "UnknownNativeMeaningStorageWidth", "value": None}, "scenario.entry.sf", "Scenario")
    _equal(entry["halted"], False, "scenario.entry.halted", "Scenario")
    banks = entry["pointingBanks"]
    _expect(type(banks) is list and len(banks) == 8, "PointingBanks", "scenario.entry.pointingBanks", "Scenario")
    for bank in banks:
        _expect(type(bank) is list and len(bank) == 4, "PointingBanks", "scenario.entry.pointingBanks", "Scenario")
        for value in bank:
            _uint(value, 65535, "scenario.entry.pointingBanks")
    for key in _DATA_KEYS:
        _uint(data[key], 255, "scenario.data." + key)
    _equal(aliases["r"], [data[key] for key in _DATA_KEYS[:8]], "scenario.localAliases.r", "Scenario")
    _equal(aliases["er"], [data[_DATA_KEYS[2 * index]] + 256 * data[_DATA_KEYS[2 * index + 1]]
                            for index in range(4)], "scenario.localAliases.er", "Scenario")


def _snapshot(state, data):
    result = {key: _json_copy(state[key], "snapshot") for key in _ENTRY_KEYS}
    result["al"] = state["a"] & 255
    result["ah"] = state["a"] >> 8
    for flag, mask in _MASKS.items():
        result[flag.lower()] = int(bool(state["psw"] & mask))
    result["otherPsw"] = state["psw"] & 4095
    result["scb"] = state["psw"] & 7
    result["locals"] = [data[key] for key in _DATA_KEYS[:8]]
    result["er"] = [result["locals"][2 * index] + 256 * result["locals"][2 * index + 1]
                    for index in range(4)]
    return result


def _set_flag(state, name, value):
    mask = _MASKS[name]
    state["psw"] = (state["psw"] & (65535 ^ mask)) | (mask if value else 0)


def _set_al(state, value):
    state["a"] = (state["a"] & 0xFF00) | value


def _derive_case(ir_rows, nodes, contract, scenario):
    data, state = scenario["data"].copy(), _json_copy(scenario["entry"], "state")
    word = data["0196"] + 256 * data["0197"]
    # No writer precedes either gate's read; common RMWs target other cells.
    path = ("A" if word < 192 else "B" if data["012A"] & 128 else
            "C" if data["0124"] & 32 else "D")
    ids = _PATHS[path]
    entry_state = _snapshot(state, data)
    trace, all_reads, all_writes, fetches = [], [], [], []
    permission = {row["address"]: row for row in contract["dataInventory"]}

    # This iterates a statically selected reviewed source path, not a PC-driven
    # machine loop. Only named IR effects accepted by _check_ir may be expanded.
    for index, identity in enumerate(ids):
        step = index + 1
        node = nodes[identity]
        pc = node["syntheticPc"]
        _expect(state["pc"] == pc, "PathPcDiscontinuity", "trace", "Reference")
        before = _snapshot(state, data)
        reads, writes = [], []
        branch_taken, external = None, None

        def read_operand(operand):
            if operand["kind"] == "CodeOwnedImmediate":
                return operand["value"]
            address, width = operand["address"], operand["widthBits"]
            addresses = [address] if width == 8 else [address, address + 1]
            for selected in addresses:
                _expect(selected in permission and path in permission[selected]["readPaths"],
                        "UnexpectedDataRead", "trace.dataReads", "Reference")
            constituents = [data[format(selected, "04X")] for selected in addresses]
            value = constituents[0] + (256 * constituents[1] if width == 16 else 0)
            reads.append({"step": step, "logicalId": identity, "syntheticPc": pc,
                          "space": "DATA", "address": address, "widthBits": width,
                          "value": value, "bytes": constituents, "provenance": _PROVENANCE})
            return value

        def write_operand(operand, value, kind):
            address = operand["address"]
            _expect(address in permission and path in permission[address]["writePaths"] and
                    operand["widthBits"] == 8 and 0 <= value <= 255,
                    "UnexpectedDataWriter", "trace.dataWrites", "Reference")
            key = format(address, "04X")
            old = data[key]
            writes.append({"step": step, "logicalId": identity, "syntheticPc": pc,
                           "space": "DATA", "address": address, "widthBits": 8,
                           "oldValue": old, "value": value,
                           "ordinal": len(all_writes) + len(writes) + 1,
                           "sameValue": old == value, "kind": kind, "provenance": _PROVENANCE})
            data[key] = value

        if type(identity) is str:
            state["pc"] = node["target"]
            external = "AbstractExternalContinuation_ExpectedOnly"
        else:
            row = ir_rows[identity]
            _expect(row["form"]["ddMode"] != "0" or not state["psw"] & _MASKS["DD"],
                    "DataDescriptorContext", "trace.stateBefore.dd", "Reference")
            old_al = state["a"] & 255
            write_result = None
            selected_successor = row["successors"][0]
            for effect in row["effects"]:
                op = effect["op"]
                if op == "LoadAccumulatorLow":
                    _set_al(state, read_operand(effect["source"]))
                elif op == "AssignZeroFlag":
                    selected = state["a"] & 255 if effect["value"] == "AL" else write_result
                    _expect(type(selected) is int, "MissingWriteResult", "trace.flags", "Reference")
                    _set_flag(state, "ZF", selected == 0)
                elif op == "AssignDataDescriptor":
                    _set_flag(state, "DD", effect["value"])
                elif op == "LogicalShiftLeft":
                    _set_al(state, (old_al * 2) & 255)
                elif op == "AssignCarryFromOldBit":
                    _set_flag(state, "CF", bool(old_al & 128))
                elif op == "ReadModifyWriteRotateThroughCarry":
                    value = read_operand(effect["destination"])
                    carry = int(bool(state["psw"] & _MASKS["CF"]))
                    _set_flag(state, "CF", bool(value & 128))
                    write_operand(effect["destination"], (value * 2 + carry) & 255, "RMW")
                elif op in ("BitwiseAnd", "BitwiseOr"):
                    right = read_operand(effect["right"])
                    value = (state["a"] & 255) & right if op == "BitwiseAnd" else (state["a"] & 255) | right
                    _set_al(state, value)
                elif op == "UnsignedCompare":
                    left, right = read_operand(effect["left"]), read_operand(effect["right"])
                    _set_flag(state, "CF", left < right)
                    _set_flag(state, "ZF", left == right)
                elif op == "CopyByte":
                    value = read_operand(effect["source"])
                    write_operand(effect["destination"], value, "LocalRegisterStore")
                elif op in ("ReadModifyWriteAnd", "ReadModifyWriteOr"):
                    left = read_operand(effect["destination"])
                    right = state["a"] & 255 if effect["source"] == "AL" else read_operand(effect["source"])
                    write_result = left & right if op == "ReadModifyWriteAnd" else left | right
                    write_operand(effect["destination"], write_result, "RMW")
                elif op == "StoreByte":
                    write_operand(effect["destination"], state["a"] & 255, "Store")
                elif op == "ConditionalJump":
                    condition = effect["condition"]
                    branch_taken = (bool(state["psw"] & _MASKS["CF"]) if condition == "CF"
                                    else bool(read_operand(_page(condition["address"])) & (1 << condition["bit"])))
                    selected_successor = effect["ifTrue"] if branch_taken else effect["ifFalse"]
                else:
                    _reject("UnreviewedEffect", "ir.effects", "Reference")
            if selected_successor == 0x5596:
                state["pc"] = nodes["DirectJ_NotBelow"]["syntheticPc"]
            elif selected_successor == 0x55C5:
                state["pc"] = nodes["DirectJ_Below"]["syntheticPc"]
            else:
                state["pc"] = nodes[selected_successor]["syntheticPc"]
        after = _snapshot(state, data)
        for key in ("ah", "hc", "otherPsw", "lrb", "scb", "ssp", "pointingBanks", "sf", "halted"):
            _equal(after[key], entry_state[key], "trace.preservation." + key, "Preservation")
        trace.append({"step": step, "syntheticPc": pc, "logicalId": identity,
                      "form": node["form"], "length": node["length"],
                      "stateBefore": before, "stateAfter": after,
                      "dataReads": reads, "dataWrites": writes, "branchTaken": branch_taken,
                      "externalTransfer": external, "provenance": _PROVENANCE})
        all_reads.extend(reads)
        all_writes.extend(writes)
        fetches.append({"step": step, "space": "PROGRAM", "start": pc,
                        "endExclusive": pc + node["length"],
                        "classification": "ExpectedSelectedInstructionExtent_NotObserved"})
    expected_count, expected_reads, expected_writes = _COUNTS[path]
    _equal([len(trace), len(all_reads), len(all_writes)],
           [expected_count, expected_reads, expected_writes], "trace.counts", "Reference")
    _equal([write["logicalId"] for write in all_writes], _WRITERS[path], "trace.writerOrder", "Reference")
    terminal = _snapshot(state, data)
    expected_al = 15 if path == "A" else data["018F"] | 240
    _equal([terminal["pc"], terminal["al"], terminal["cf"], terminal["zf"], terminal["dd"]],
           [0x55C5 if path == "A" else 0x5596, expected_al, int(path == "A"), 0, 0],
           "terminalState", "Reference")
    if path == "B":
        _expect(all(read["address"] != 0x124 for read in all_reads),
                "SecondGateReadNotSuppressed", "trace.dataReads", "Reference")
    return {"classification": _STATIC, "scenarioId": scenario["id"], "path": path,
            "entryState": entry_state, "terminalState": terminal, "terminalData": data,
            "instructionCount": len(trace), "originalInstructionCount": len(trace) - 1,
            "terminalPc": terminal["pc"], "readCount": len(all_reads), "writeCount": len(all_writes),
            "trace": trace, "orderedReads": all_reads, "orderedWrites": all_writes,
            "programFetches": fetches, "directJCount": 1,
            "actualSyntheticExecution": "NotRun",
            "externalExitObservation": "SyntheticExternalExitObservationNotRun",
            "historicalPathWitness": "StaticPrimaryAndInventedCoverage" if path == "C"
            else "HistoricalCorpusHasOriginalPathWitness_NotNewObservation"}


def _canonical_digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=True, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def _check_closed_identities(ir, composition, contract):
    # Late closed identities supplement the meaningful semantic/geometry checks.
    identities = (
        (ir, "b9b7cf545e780eb749b92e4a737aae44d1636e8bc50e10d6c5b9ccce1feb6060", "ir"),
        (composition, "501de8dd37d9a842e7cbc8dba3c94a067132e8b6923cd6b6d424cf839430936e", "composition"),
        (contract, "83bbc32a3c150c3466ff5160890d9046cdc9a69f94438cfc1078df079af81fcd", "contract"),
    )
    for value, digest, location in identities:
        _equal(_canonical_digest(value), digest, location + ".closedIdentity", "ClosedIdentity")


def analyze_protocol(reviewed_ir, reviewed_composition, protocol_contract, scenario):
    """Return complete static expectations or an atomic ProtocolError.

    No bytes, CPU callbacks, arbitrary instructions or actual observations are
    accepted. Entry/terminal snapshots are source-derived invented expectations.
    """
    ir = _json_copy(reviewed_ir, "ir")
    composition = _json_copy(reviewed_composition, "composition")
    contract = _json_copy(protocol_contract, "contract")
    seed = _json_copy(scenario, "scenario", 4096)
    rows = _check_ir(ir)
    nodes = _check_program_geometry(composition, contract, rows)
    _check_contract_obligations(contract)
    _check_scenario(seed)
    result = _derive_case(rows, nodes, contract, seed)
    _check_closed_identities(ir, composition, contract)
    return result


def validate_expected_trace(reviewed_ir, reviewed_composition, protocol_contract,
                            scenario, proposed_expected_case):
    """Exact whole-case comparison, never replace expected state by observations."""
    proposed = _json_copy(proposed_expected_case, "proposedExpectedCase")
    expected = analyze_protocol(reviewed_ir, reviewed_composition, protocol_contract, scenario)
    _equal(proposed, expected, "proposedExpectedCase", "TraceComparison")
    return expected
