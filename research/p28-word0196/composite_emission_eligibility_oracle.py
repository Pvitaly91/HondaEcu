"""Independent M2bi typed mapping and mathematical preflight expectations.

Frozen before planner authoring. Only the unchanged pure M2bh expectation
helper is reused for inherited fields; novel20 typed mapping remains ownliteral.
Numeric fields are mathematical origins/operands/lengths, never instruction bytes.
"""
from static_composition_oracle import expected_result as inherited_expected_result

ROWS = ((21871, "lb-a-page", 2, 0, "Common", (("AccumulatorA", {}), ("PageOffset8", {"value": 142}))), (21873, "sllb-a", 1, 2, "Common", (("AccumulatorA", {}),)), (21874, "rolb-page", 3, 3, "Common", (("PageOffset8", {"value": 142}),)), (21877, "lb-a-r0", 1, 6, "Common", (("AccumulatorA", {}), ("Register0", {"value": 0}))), (21878, "andb-a-page", 2, 7, "Common", (("AccumulatorA", {}), ("PageOffset8", {"value": 142}))), (21880, "cmp-page-imm16", 5, 9, "Common", (("EvenPageOffset8", {"value": 150}), ("Immediate16", {"value": 192}))), (21885, "jlt-rel8", 2, 14, "Common", (("TargetPC16", {"logicalTargetNodeId": 21951, "valueSource": "SyntheticAssignedPC"}),)), (21887, "movb-r1-page", 3, 16, "NotBelow", (("Register1", {"value": 1}), ("PageOffset8", {"value": 23}))), (21890, "andb-page-a", 3, 19, "NotBelow", (("PageOffset8", {"value": 23}), ("AccumulatorA", {}))), (21893, "jbs-page-bit7", 3, 22, "NotBelow", (("PageBit7", {"offset": 42, "bit": 7}), ("TargetPC16", {"logicalTargetNodeId": 21906, "valueSource": "SyntheticAssignedPC"}))), (21896, "jbs-page-bit5", 3, 25, "NotBelow", (("PageBit5", {"offset": 36, "bit": 5}), ("TargetPC16", {"logicalTargetNodeId": 21906, "valueSource": "SyntheticAssignedPC"}))), (21899, "andb-page-a", 3, 28, "NotBelow", (("PageOffset8", {"value": 143}), ("AccumulatorA", {}))), (21902, "orb-page-imm8", 4, 31, "NotBelow", (("PageOffset8", {"value": 42}), ("Immediate8", {"value": 1}))), (21906, "lb-a-page", 2, 35, "NotBelow", (("AccumulatorA", {}), ("PageOffset8", {"value": 143}))), (21908, "orb-a-imm8", 2, 37, "NotBelow", (("AccumulatorA", {}), ("Immediate8", {"value": 240}))), ("DirectJ_NotBelow", "j-address", 3, 39, "DirectJ_NotBelow", (("ProgramTarget16", {"value": 21910}),)), (21951, "lb-a-imm8", 2, 42, "Below", (("AccumulatorA", {}), ("Immediate8", {"value": 15}))), (21953, "stb-a-page", 2, 44, "Below", (("AccumulatorA", {}), ("PageOffset8", {"value": 23}))), (21955, "stb-a-page", 2, 46, "Below", (("AccumulatorA", {}), ("PageOffset8", {"value": 143}))), ("DirectJ_Below", "j-address", 3, 48, "DirectJ_Below", (("ProgramTarget16", {"value": 21957}),)))
J_NB, J_BELOW = "DirectJ_NotBelow", "DirectJ_Below"
DD0_REQUIRED = (0x5571, 0x5576, 0x5594, 0x55C1, 0x55C3)
DD0_WRITERS = (0x556F, 0x5575, 0x5592, 0x55BF)
SUCCESSORS = {
    0x556F: (0x5571,), 0x5571: (0x5572,), 0x5572: (0x5575,),
    0x5575: (0x5576,), 0x5576: (0x5578,), 0x5578: (0x557D,),
    0x557D: (0x55BF, 0x557F), 0x557F: (0x5582,), 0x5582: (0x5585,),
    0x5585: (0x5592, 0x5588), 0x5588: (0x5592, 0x558B),
    0x558B: (0x558E,), 0x558E: (0x5592,), 0x5592: (0x5594,),
    0x5594: (J_NB,), J_NB: (0x5596,), 0x55BF: (0x55C1,),
    0x55C1: (0x55C3,), 0x55C3: (J_BELOW,), J_BELOW: (0x55C5,),
}
TAKEN = ((0x557D, 0x55BF), (0x5585, 0x5592), (0x5588, 0x5592))
WRITES = {
    0x5572: (0x018E,), 0x557F: (0x0109,), 0x5582: (0x0117,),
    0x558B: (0x018F,), 0x558E: (0x012A,), 0x55C1: (0x0117,), 0x55C3: (0x018F,),
}


def positions(base, gap):
    return {node: base + offset + (gap if component in ("Below", J_BELOW) else 0)
            for node, _, _, offset, component, _ in ROWS}


def paths():
    found = []
    def visit(node, prior):
        if node in (0x5596, 0x55C5):
            found.append((prior, node))
            return
        if node in prior:
            raise ValueError("Unexpected independent cycle")
        for target in SUCCESSORS[node]:
            visit(target, prior + (node,))
    visit(0x556F, ())
    return found


def expected_dd(initial):
    """Path-enumerated transfer domains; not codec metadata or CPU mutation."""
    domains_in = {node: set() for node, *_ in ROWS}
    domains_out = {node: set() for node, *_ in ROWS}
    for nodes, _ in paths():
        state = set(initial)
        for node in nodes:
            domains_in[node].update(state)
            if node in DD0_REQUIRED and state != {0}:
                raise ValueError("Independent DD0 obligation")
            if node in DD0_WRITERS:
                state = {0}
            domains_out[node].update(state)
    return [{"nodeId": node, "incomingMay": sorted(domains_in[node]),
             "incomingMust": next(iter(domains_in[node])) if len(domains_in[node]) == 1 else None,
             "outgoingMay": sorted(domains_out[node]),
             "outgoingMust": next(iter(domains_out[node])) if len(domains_out[node]) == 1 else None}
            for node, *_ in ROWS]


def projected_typed_rows(base, gap, initial):
    assigned = positions(base, gap)
    dd = {row["nodeId"]: row["incomingMay"] for row in expected_dd(initial)}
    planned = []
    for node, form, length, _, component, operands in ROWS:
        typed = []
        for kind, fields in operands:
            if kind == "TargetPC16":
                typed.append({"kind": kind, "fields": {"value": assigned[fields["logicalTargetNodeId"]]}})
            else:
                typed.append({"kind": kind, "fields": dict(fields)})
        planned.append({
            "nodeId": node, "originalLogicalSiteId": node if type(node) is int else None,
            "route": "A" if type(node) is int else "B", "form": form,
            "origin": assigned[node], "length": length, "endExclusive": assigned[node] + length,
            "typedOperands": typed, "incomingDDValues": dd[node],
            "scalarRequestVariants": [{"incoming_dd": value} for value in dd[node]],
            "successors": list(SUCCESSORS[node]),
        })
    return planned


def geometry_reason(base, gap, assignments=None):
    """First actual geometric relation, computed independently of planner output."""
    if type(base) is not int or not 0 <= base <= 65535:
        return "RequestDomain"
    if type(gap) is not int or gap < 0:
        return "RequestDomain"
    assigned = positions(base, gap) if assignments is None else assignments
    lengths = {node: length for node, _, length, *_ in ROWS}
    spans = [(node, assigned[node], assigned[node] + lengths[node]) for node, *_ in ROWS]
    if any(type(start) is not int or start < 0 or start > 65535 or end > 65536
           for _, start, end in spans):
        return "SpanOutsideProfile"
    for index, (_, begin, end) in enumerate(spans):
        for _, other_begin, other_end in spans[index + 1:]:
            if max(begin, other_begin) < min(end, other_end):
                return "InstructionOverlap"
    for source, targets in SUCCESSORS.items():
        if type(source) is str:
            continue
        for target in targets:
            if (source, target) not in TAKEN and assigned[source] + lengths[source] != assigned[target]:
                return "FallthroughMismatch"
    for source, target in TAKEN:
        next_pc = assigned[source] + lengths[source]
        if next_pc > 65535:
            return "BranchNextOutsideProfile"
        delta = assigned[target] - next_pc
        if not -128 <= delta <= 127:
            return "Rel8OutOfRange"
        wanted = 26 + gap if source == 0x557D else 10 if source == 0x5585 else 7
        if delta != wanted:
            return "BranchTargetMismatch"
    if any(begin <= anchor < end for anchor in (0x5596, 0x55C5) for _, begin, end in spans):
        return "SyntheticExternalAnchorCollision"
    if assigned != positions(base, gap):
        return "ComponentPlanMismatch"
    return None


def summary():
    edge_count = sum(len(targets) for targets in SUCCESSORS.values())
    all_paths = paths()
    return {
        "nodes": len(ROWS), "routeA": sum(type(node) is int for node, *_ in ROWS),
        "routeB": sum(type(node) is str for node, *_ in ROWS),
        "originalForms": len({form for node, form, *_ in ROWS if type(node) is int}),
        "plannedLength": sum(length for _, _, length, *_ in ROWS), "edges": edge_count,
        "paths": [len(nodes) for nodes, _ in all_paths],
        "writes": [sum(len(WRITES.get(node, ())) for node in nodes) for nodes, _ in all_paths],
        "branchDeltas": [positions(0x1000, 0)[target] - positions(0x1000, 0)[source]
                         - next(row[2] for row in ROWS if row[0] == source) for source, target in TAKEN],
        "eligibleScope": "OnlyBase1000Gap0_ForSeparateMilestone_NotEmissionPermission",
        "encoderCalls": 0, "decoderCalls": 0, "compositeBytes": 0, "CPUExecutions": 0,
    }

PRIMARY = {
    "lb-a-page": (124, "3-70"), "sllb-a": (197, "3-144"), "rolb-page": (173, "3-120"),
    "lb-a-r0": (124, "3-70"), "andb-a-page": (76, "3-24"),
    "cmp-page-imm16": (90, "3-38"), "jlt-rel8": (120, "3-66/3-67"),
    "movb-r1-page": (153, "3-99"), "andb-page-a": (77, "3-25"),
    "jbs-page-bit7": (119, "3-65"), "jbs-page-bit5": (119, "3-65"),
    "orb-page-imm8": (163, "3-110"), "orb-a-imm8": (160, "3-107"),
    "lb-a-imm8": (124, "3-70"), "stb-a-page": (208, "3-155"),
    "j-address": (116, "3-62"),
}
FUTURE_VERIFICATION = {"primary": {"classification": "FutureGenericManufacturerPerInstructionAcceptance_NotImplementedOrRun", "ruleInventory": [{"ruleId": "PrimaryRule_lb-a-page", "form": "lb-a-page", "primaryPage": {"pdfPage": 124, "printedPage": "3-70"}, "exactLength": 2, "operandClassesAndExactSlots": [{"kind": "AccumulatorA", "slots": [], "domain": []}, {"kind": "PageOffset8", "slots": ["value"], "domain": [0, 255]}], "symbolicCodeColumnRoles": ["ManufacturerFixedF4", "PageOffset8Raw"], "DDselection": "AcceptsBothIncomingDD", "DDeffect": "SetsDD0WhenExecuted", "incomingDDValues": [0, 1], "fixedCellIdentitySource": "PreservedM2bbAndM2bcManufacturerSealedFacts_NotEncoderOrDecoderOutput", "fieldOrder": "ManufacturerCodeColumns_ExactOperandOrder", "byteOrder": "SingleOperandWidthOrFollowingPCRelative", "relative": None, "CMPWordProfile": None, "newAcceptanceVerifierImplemented": False, "byteEvidenceStage": "SingleInstructionEvidenceInherited_CompositeByteProofNotRun"}, {"ruleId": "PrimaryRule_sllb-a", "form": "sllb-a", "primaryPage": {"pdfPage": 197, "printedPage": "3-144"}, "exactLength": 1, "operandClassesAndExactSlots": [{"kind": "AccumulatorA", "slots": [], "domain": []}], "symbolicCodeColumnRoles": ["ManufacturerFixed53"], "DDselection": "RequiresDD0", "DDeffect": "PreservesDD", "incomingDDValues": [0], "fixedCellIdentitySource": "PreservedM2bbAndM2bcManufacturerSealedFacts_NotEncoderOrDecoderOutput", "fieldOrder": "ManufacturerCodeColumns_ExactOperandOrder", "byteOrder": "SingleOperandWidthOrFollowingPCRelative", "relative": None, "CMPWordProfile": None, "newAcceptanceVerifierImplemented": False, "byteEvidenceStage": "SingleInstructionEvidenceInherited_CompositeByteProofNotRun"}, {"ruleId": "PrimaryRule_rolb-page", "form": "rolb-page", "primaryPage": {"pdfPage": 173, "printedPage": "3-120"}, "exactLength": 3, "operandClassesAndExactSlots": [{"kind": "PageOffset8", "slots": ["value"], "domain": [0, 255]}], "symbolicCodeColumnRoles": ["ManufacturerFixedC4", "PageOffset8Raw", "ManufacturerFixedB7"], "DDselection": "AcceptsBothIncomingDD", "DDeffect": "PreservesDD", "incomingDDValues": [0, 1], "fixedCellIdentitySource": "PreservedM2bbAndM2bcManufacturerSealedFacts_NotEncoderOrDecoderOutput", "fieldOrder": "ManufacturerCodeColumns_ExactOperandOrder", "byteOrder": "SingleOperandWidthOrFollowingPCRelative", "relative": None, "CMPWordProfile": None, "newAcceptanceVerifierImplemented": False, "byteEvidenceStage": "SingleInstructionEvidenceInherited_CompositeByteProofNotRun"}, {"ruleId": "PrimaryRule_lb-a-r0", "form": "lb-a-r0", "primaryPage": {"pdfPage": 124, "printedPage": "3-70"}, "exactLength": 1, "operandClassesAndExactSlots": [{"kind": "AccumulatorA", "slots": [], "domain": []}, {"kind": "Register0", "slots": ["value"], "domain": [0]}], "symbolicCodeColumnRoles": ["ManufacturerFixed78_Register0Identity"], "DDselection": "AcceptsBothIncomingDD", "DDeffect": "SetsDD0WhenExecuted", "incomingDDValues": [0, 1], "fixedCellIdentitySource": "PreservedM2bbAndM2bcManufacturerSealedFacts_NotEncoderOrDecoderOutput", "fieldOrder": "ManufacturerCodeColumns_ExactOperandOrder", "byteOrder": "SingleOperandWidthOrFollowingPCRelative", "relative": None, "CMPWordProfile": None, "newAcceptanceVerifierImplemented": False, "byteEvidenceStage": "SingleInstructionEvidenceInherited_CompositeByteProofNotRun"}, {"ruleId": "PrimaryRule_andb-a-page", "form": "andb-a-page", "primaryPage": {"pdfPage": 76, "printedPage": "3-24"}, "exactLength": 2, "operandClassesAndExactSlots": [{"kind": "AccumulatorA", "slots": [], "domain": []}, {"kind": "PageOffset8", "slots": ["value"], "domain": [0, 255]}], "symbolicCodeColumnRoles": ["ManufacturerFixedD7", "PageOffset8Raw"], "DDselection": "RequiresDD0", "DDeffect": "PreservesDD", "incomingDDValues": [0], "fixedCellIdentitySource": "PreservedM2bbAndM2bcManufacturerSealedFacts_NotEncoderOrDecoderOutput", "fieldOrder": "ManufacturerCodeColumns_ExactOperandOrder", "byteOrder": "SingleOperandWidthOrFollowingPCRelative", "relative": None, "CMPWordProfile": None, "newAcceptanceVerifierImplemented": False, "byteEvidenceStage": "SingleInstructionEvidenceInherited_CompositeByteProofNotRun"}, {"ruleId": "PrimaryRule_cmp-page-imm16", "form": "cmp-page-imm16", "primaryPage": {"pdfPage": 90, "printedPage": "3-38"}, "exactLength": 5, "operandClassesAndExactSlots": [{"kind": "EvenPageOffset8", "slots": ["value"], "domain": [0, 254]}, {"kind": "Immediate16", "slots": ["value"], "domain": [0, 65535]}], "symbolicCodeColumnRoles": ["ManufacturerFixedB4", "EvenPageOffset8Raw", "ManufacturerFixedC0", "Immediate16Low", "Immediate16High"], "DDselection": "AcceptsBothIncomingDD", "DDeffect": "PreservesDD", "incomingDDValues": [0, 1], "fixedCellIdentitySource": "PreservedM2bbAndM2bcManufacturerSealedFacts_NotEncoderOrDecoderOutput", "fieldOrder": "ManufacturerCodeColumns_ExactOperandOrder", "byteOrder": "Immediate16Lower8ThenUpper8", "relative": None, "CMPWordProfile": "EvenRawOffset_NoAlignDown_NoRebasing_NotUniversalISAInvalidity", "newAcceptanceVerifierImplemented": False, "byteEvidenceStage": "SingleInstructionEvidenceInherited_CompositeByteProofNotRun"}, {"ruleId": "PrimaryRule_jlt-rel8", "form": "jlt-rel8", "primaryPage": {"pdfPage": 120, "printedPage": "3-66/3-67"}, "exactLength": 2, "operandClassesAndExactSlots": [{"kind": "TargetPC16", "slots": ["value"], "domain": [0, 65535]}], "symbolicCodeColumnRoles": ["ManufacturerFixedCA_JLTOnly", "SignedRel8FromFollowingInstruction"], "DDselection": "AcceptsBothIncomingDD", "DDeffect": "PreservesDD", "incomingDDValues": [0, 1], "fixedCellIdentitySource": "PreservedM2bbAndM2bcManufacturerSealedFacts_NotEncoderOrDecoderOutput", "fieldOrder": "ManufacturerCodeColumns_ExactOperandOrder", "byteOrder": "SingleOperandWidthOrFollowingPCRelative", "relative": {"equation": "target-(origin+exactLength)", "minimum": -128, "maximum": 127, "followingPCMaximum": 65535, "noWrap": True, "octetsComputedNow": 0}, "CMPWordProfile": None, "newAcceptanceVerifierImplemented": False, "byteEvidenceStage": "SingleInstructionEvidenceInherited_CompositeByteProofNotRun"}, {"ruleId": "PrimaryRule_movb-r1-page", "form": "movb-r1-page", "primaryPage": {"pdfPage": 153, "printedPage": "3-99"}, "exactLength": 3, "operandClassesAndExactSlots": [{"kind": "Register1", "slots": ["value"], "domain": [1]}, {"kind": "PageOffset8", "slots": ["value"], "domain": [0, 255]}], "symbolicCodeColumnRoles": ["ManufacturerFixedC4", "PageOffset8Raw", "ManufacturerFixed49_Register1Identity"], "DDselection": "AcceptsBothIncomingDD", "DDeffect": "PreservesDD", "incomingDDValues": [0, 1], "fixedCellIdentitySource": "PreservedM2bbAndM2bcManufacturerSealedFacts_NotEncoderOrDecoderOutput", "fieldOrder": "ManufacturerCodeColumns_ExactOperandOrder", "byteOrder": "SingleOperandWidthOrFollowingPCRelative", "relative": None, "CMPWordProfile": None, "newAcceptanceVerifierImplemented": False, "byteEvidenceStage": "SingleInstructionEvidenceInherited_CompositeByteProofNotRun"}, {"ruleId": "PrimaryRule_andb-page-a", "form": "andb-page-a", "primaryPage": {"pdfPage": 77, "printedPage": "3-25"}, "exactLength": 3, "operandClassesAndExactSlots": [{"kind": "PageOffset8", "slots": ["value"], "domain": [0, 255]}, {"kind": "AccumulatorA", "slots": [], "domain": []}], "symbolicCodeColumnRoles": ["ManufacturerFixedC4", "PageOffset8Raw", "ManufacturerFixedD1"], "DDselection": "AcceptsBothIncomingDD", "DDeffect": "PreservesDD", "incomingDDValues": [0, 1], "fixedCellIdentitySource": "PreservedM2bbAndM2bcManufacturerSealedFacts_NotEncoderOrDecoderOutput", "fieldOrder": "ManufacturerCodeColumns_ExactOperandOrder", "byteOrder": "SingleOperandWidthOrFollowingPCRelative", "relative": None, "CMPWordProfile": None, "newAcceptanceVerifierImplemented": False, "byteEvidenceStage": "SingleInstructionEvidenceInherited_CompositeByteProofNotRun"}, {"ruleId": "PrimaryRule_jbs-page-bit7", "form": "jbs-page-bit7", "primaryPage": {"pdfPage": 119, "printedPage": "3-65"}, "exactLength": 3, "operandClassesAndExactSlots": [{"kind": "PageBit7", "slots": ["offset", "bit"], "domain": [0, 255]}, {"kind": "TargetPC16", "slots": ["value"], "domain": [0, 65535]}], "symbolicCodeColumnRoles": ["ManufacturerFixedEF_Bit7Identity", "PageBit7OffsetRaw", "SignedRel8FromFollowingInstruction"], "DDselection": "AcceptsBothIncomingDD", "DDeffect": "PreservesDD", "incomingDDValues": [0, 1], "fixedCellIdentitySource": "PreservedM2bbAndM2bcManufacturerSealedFacts_NotEncoderOrDecoderOutput", "fieldOrder": "ManufacturerCodeColumns_ExactOperandOrder", "byteOrder": "SingleOperandWidthOrFollowingPCRelative", "relative": {"equation": "target-(origin+exactLength)", "minimum": -128, "maximum": 127, "followingPCMaximum": 65535, "noWrap": True, "octetsComputedNow": 0}, "CMPWordProfile": None, "newAcceptanceVerifierImplemented": False, "byteEvidenceStage": "SingleInstructionEvidenceInherited_CompositeByteProofNotRun"}, {"ruleId": "PrimaryRule_jbs-page-bit5", "form": "jbs-page-bit5", "primaryPage": {"pdfPage": 119, "printedPage": "3-65"}, "exactLength": 3, "operandClassesAndExactSlots": [{"kind": "PageBit5", "slots": ["offset", "bit"], "domain": [0, 255]}, {"kind": "TargetPC16", "slots": ["value"], "domain": [0, 65535]}], "symbolicCodeColumnRoles": ["ManufacturerFixedED_Bit5Identity", "PageBit5OffsetRaw", "SignedRel8FromFollowingInstruction"], "DDselection": "AcceptsBothIncomingDD", "DDeffect": "PreservesDD", "incomingDDValues": [0, 1], "fixedCellIdentitySource": "PreservedM2bbAndM2bcManufacturerSealedFacts_NotEncoderOrDecoderOutput", "fieldOrder": "ManufacturerCodeColumns_ExactOperandOrder", "byteOrder": "SingleOperandWidthOrFollowingPCRelative", "relative": {"equation": "target-(origin+exactLength)", "minimum": -128, "maximum": 127, "followingPCMaximum": 65535, "noWrap": True, "octetsComputedNow": 0}, "CMPWordProfile": None, "newAcceptanceVerifierImplemented": False, "byteEvidenceStage": "SingleInstructionEvidenceInherited_CompositeByteProofNotRun"}, {"ruleId": "PrimaryRule_orb-page-imm8", "form": "orb-page-imm8", "primaryPage": {"pdfPage": 163, "printedPage": "3-110"}, "exactLength": 4, "operandClassesAndExactSlots": [{"kind": "PageOffset8", "slots": ["value"], "domain": [0, 255]}, {"kind": "Immediate8", "slots": ["value"], "domain": [0, 255]}], "symbolicCodeColumnRoles": ["ManufacturerFixedC4", "PageOffset8Raw", "ManufacturerFixedE0", "Immediate8Raw"], "DDselection": "AcceptsBothIncomingDD", "DDeffect": "PreservesDD", "incomingDDValues": [0, 1], "fixedCellIdentitySource": "PreservedM2bbAndM2bcManufacturerSealedFacts_NotEncoderOrDecoderOutput", "fieldOrder": "ManufacturerCodeColumns_ExactOperandOrder", "byteOrder": "SingleOperandWidthOrFollowingPCRelative", "relative": None, "CMPWordProfile": None, "newAcceptanceVerifierImplemented": False, "byteEvidenceStage": "SingleInstructionEvidenceInherited_CompositeByteProofNotRun"}, {"ruleId": "PrimaryRule_orb-a-imm8", "form": "orb-a-imm8", "primaryPage": {"pdfPage": 160, "printedPage": "3-107"}, "exactLength": 2, "operandClassesAndExactSlots": [{"kind": "AccumulatorA", "slots": [], "domain": []}, {"kind": "Immediate8", "slots": ["value"], "domain": [0, 255]}], "symbolicCodeColumnRoles": ["ManufacturerFixedE6", "Immediate8Raw"], "DDselection": "RequiresDD0", "DDeffect": "PreservesDD", "incomingDDValues": [0], "fixedCellIdentitySource": "PreservedM2bbAndM2bcManufacturerSealedFacts_NotEncoderOrDecoderOutput", "fieldOrder": "ManufacturerCodeColumns_ExactOperandOrder", "byteOrder": "SingleOperandWidthOrFollowingPCRelative", "relative": None, "CMPWordProfile": None, "newAcceptanceVerifierImplemented": False, "byteEvidenceStage": "SingleInstructionEvidenceInherited_CompositeByteProofNotRun"}, {"ruleId": "PrimaryRule_lb-a-imm8", "form": "lb-a-imm8", "primaryPage": {"pdfPage": 124, "printedPage": "3-70"}, "exactLength": 2, "operandClassesAndExactSlots": [{"kind": "AccumulatorA", "slots": [], "domain": []}, {"kind": "Immediate8", "slots": ["value"], "domain": [0, 255]}], "symbolicCodeColumnRoles": ["ManufacturerFixed77", "Immediate8Raw"], "DDselection": "AcceptsBothIncomingDD", "DDeffect": "SetsDD0WhenExecuted", "incomingDDValues": [0, 1], "fixedCellIdentitySource": "PreservedM2bbAndM2bcManufacturerSealedFacts_NotEncoderOrDecoderOutput", "fieldOrder": "ManufacturerCodeColumns_ExactOperandOrder", "byteOrder": "SingleOperandWidthOrFollowingPCRelative", "relative": None, "CMPWordProfile": None, "newAcceptanceVerifierImplemented": False, "byteEvidenceStage": "SingleInstructionEvidenceInherited_CompositeByteProofNotRun"}, {"ruleId": "PrimaryRule_stb-a-page", "form": "stb-a-page", "primaryPage": {"pdfPage": 208, "printedPage": "3-155"}, "exactLength": 2, "operandClassesAndExactSlots": [{"kind": "AccumulatorA", "slots": [], "domain": []}, {"kind": "PageOffset8", "slots": ["value"], "domain": [0, 255]}], "symbolicCodeColumnRoles": ["ManufacturerFixedD4", "PageOffset8Raw"], "DDselection": "RequiresDD0", "DDeffect": "PreservesDD", "incomingDDValues": [0], "fixedCellIdentitySource": "PreservedM2bbAndM2bcManufacturerSealedFacts_NotEncoderOrDecoderOutput", "fieldOrder": "ManufacturerCodeColumns_ExactOperandOrder", "byteOrder": "SingleOperandWidthOrFollowingPCRelative", "relative": None, "CMPWordProfile": None, "newAcceptanceVerifierImplemented": False, "byteEvidenceStage": "SingleInstructionEvidenceInherited_CompositeByteProofNotRun"}, {"ruleId": "PrimaryRule_j-address", "form": "j-address", "primaryPage": {"pdfPage": 116, "printedPage": "3-62"}, "exactLength": 3, "operandClassesAndExactSlots": [{"kind": "ProgramTarget16", "slots": ["value"], "domain": [0, 65535]}], "symbolicCodeColumnRoles": ["ManufacturerFixed03", "ProgramTarget16Low", "ProgramTarget16High"], "DDselection": "AcceptsBothIncomingDD", "DDeffect": "PreservesDD", "incomingDDValues": [0, 1], "fixedCellIdentitySource": "PreservedM2bgPrimaryBeforeImplementationLiteralAndFreshFullPage116Review_NotEncoderOutput", "fieldOrder": "Lower8ThenUpper8", "byteOrder": "ProgramTarget16Lower8ThenUpper8", "relative": None, "CMPWordProfile": None, "newAcceptanceVerifierImplemented": False, "byteEvidenceStage": "SingleInstructionEvidenceInherited_CompositeByteProofNotRun"}], "ruleCount": 16, "exactLengthRequired": True, "fixedCellsAndOperandOrderRequired": True, "widthAndExactTypeRequired": True, "LELowHighRequired": True, "relativeTargetAndNoWrapRequired": True, "DDApplicabilityRequired": True, "expectedFrom": "SealedManufacturerFactsAndOriginalIndependentFixtures_NeverEncoderOutput", "fullExpected51Program": False, "sharedCodecTableAsOracle": False, "compatibilityRoundTripAloneNotPrimaryProof": True, "implementationStatus": "NotImplemented", "actualCalls": 0}, "decode": {"classification": "FuturePerInstructionDecodeCompatibility_NotImplementedOrRun", "routeACount": 18, "routeBCount": 2, "exactPerInstructionBoundaries": True, "exactLength": True, "exactForm": True, "exactOperandKindsAndValues": True, "originAndDDContext": True, "relocatedInternalTargets": True, "unchangedAbsoluteExternalTargets": True, "noTrailing": True, "noGenericStreamDecoder": True, "meaning": "EncodeDecodeAndDecodeEncodeCompatibilityOnly_NotCPUOrCompositeSemanticsProof", "implementationStatus": "NotImplemented", "actualCalls": 0}, "atomicity": {"classification": "FutureTransactionalInMemoryAtomicityRequirement_NotImplementedOrRun", "allPreflightBeforeAnyCodecCall": True, "allPerInstructionChecksBeforeCompositePublication": True, "onAnyError": "NoPartialCompositeBufferPublished", "noSkippedInstruction": True, "noFallback": True, "noPartialSuccess": True, "noPadding": True, "noIgnoredTrailing": True, "perInstructionExactLengthRequired": True, "sumExactLengthRequired": 51, "codecErrors": "TerminalFailure_NoCoercionOrContinue", "inMemoryOnly": True, "implementationStatus": "NotImplemented", "actualCalls": 0}, "orderedEffects": "SeparateFutureProof_NotByteIdentity_NotExecuted"}
RUNTIME_STATUS = {
    "ActualCompositeEmission": "NotRun", "CompositeMachineCode": "NotGenerated",
    "ActualTargetExecution": "NotObserved", "NativeExitIsolation": "NotEstablished",
    "ActualDownstreamRejoin": "NotEstablished", "PhysicalROMPlacement": "NotEstablished",
    "TargetProgramEquivalence": "NotEstablished", "FirmwareIntegration": "NotEstablished",
    "FirmwareReady": False,
}
INHERITED_ORACLE_BINDING = {
    "file": "research/p28-word0196/static_composition_oracle.py",
    "sha256": "bde29d3150c9f9d6918435f08fc1edf051869f523c7c0e4dc6f0b52f24244462",
    "bytes": 22613,
    "use": "InheritedM2bhProjectionOnly_OwnNovelTypedMapping_NoPlannerOutput",
}


def own_copy(value):
    if type(value) is dict:
        return {key: own_copy(item) for key, item in value.items()}
    if type(value) is list:
        return [own_copy(item) for item in value]
    return value


def expected_plan(initial):
    """Own literal novel mapping over exactly the one allowlisted synthetic plan."""
    base, gap = 0x1000, 0
    inherited = inherited_expected_result(base, gap, tuple(initial))
    projected = projected_typed_rows(base, gap, tuple(initial))
    plans = []
    for index, row in enumerate(projected):
        node, form, length, offset, component, operands = ROWS[index]
        typed = own_copy(row["typedOperands"])
        relocated = (operands[-1][1]["logicalTargetNodeId"]
                     if node in (0x557D, 0x5585, 0x5588) else None)
        variants = []
        for scalar in row["incomingDDValues"]:
            if type(node) is int:
                variants.append({
                    "requestClass": "EncoderRequest",
                    "fields": {"reviewed_form_id": {"enumClass": "FormId", "value": form},
                               "typed_operands": {"container": "tuple", "items": own_copy(typed)},
                               "incoming_dd": scalar, "origin_pc": row["origin"]},
                })
            else:
                variants.append({
                    "requestClass": "DirectJEncodeRequest",
                    "fields": {"target": own_copy(typed[0]), "origin_pc": row["origin"],
                               "incoming_dd": scalar},
                })
        page, printed = PRIMARY[form]
        plans.append({
            "nodeId": node, "originalLogicalSiteId": row["originalLogicalSiteId"],
            "nodeKind": "OriginalLogicalInstruction" if type(node) is int else "AbstractTransferSlot",
            "routeId": row["route"], "formId": form, "assignedPC": row["origin"],
            "endExclusive": row["endExclusive"], "plannedLength": length,
            "incomingDDDomain": list(row["incomingDDValues"]), "typedOperands": typed,
            "successorIds": list(row["successors"]), "relocatedTargetNodeId": relocated,
            "primary": {"pdfPage": page, "printedPage": printed},
            "requestVariants": variants,
        })
    retained = {key: own_copy(inherited[key]) for key in (
        "componentSpans", "gap", "edgeRows", "branchRows", "paths", "ddFlow", "flagFlow",
        "contextObligations", "anchorObservations", "permissions")}
    counts = own_copy(inherited["counts"])
    counts.update(
        routeANodes=sum(row["routeId"] == "A" for row in plans),
        routeBNodes=sum(row["routeId"] == "B" for row in plans),
        totalRequestVariants=sum(len(row["requestVariants"]) for row in plans),
        unresolvedTypedMappings=0, syntheticEligibleLayouts=1)
    return {
        "classification": "ReviewedStatic20NodeTypedEmissionPlan",
        "verdict": "SyntheticCompositeEmissionEligibleForSeparateMilestone",
        "nodePlans": plans, **retained, "counts": counts,
        "futureVerification": own_copy(FUTURE_VERIFICATION),
        "runtimeStatus": own_copy(RUNTIME_STATUS),
    }
