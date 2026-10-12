"""Independent M2bh positional and path-enumerated static expectations.

Own literal logical identities and mathematical offsets, not analyzer output,
codec/CPU execution, opcode tables or machine bytes. Two transfer identities
are abstract slots and never historical original PCs or observed instructions.
"""

J_NB = "DirectJ_NotBelow"
J_BELOW = "DirectJ_Below"
NODE_ROWS = (
    (0x556F, 2, "Common", 0), (0x5571, 1, "Common", 2),
    (0x5572, 3, "Common", 3), (0x5575, 1, "Common", 6),
    (0x5576, 2, "Common", 7), (0x5578, 5, "Common", 9),
    (0x557D, 2, "Common", 14), (0x557F, 3, "NotBelow", 16),
    (0x5582, 3, "NotBelow", 19), (0x5585, 3, "NotBelow", 22),
    (0x5588, 3, "NotBelow", 25), (0x558B, 3, "NotBelow", 28),
    (0x558E, 4, "NotBelow", 31), (0x5592, 2, "NotBelow", 35),
    (0x5594, 2, "NotBelow", 37), (J_NB, 3, "DirectJ_NotBelow", 39),
    (0x55BF, 2, "Below", 42), (0x55C1, 2, "Below", 44),
    (0x55C3, 2, "Below", 46), (J_BELOW, 3, "DirectJ_Below", 48),
)
SUCCESSORS = {
    0x556F: (0x5571,), 0x5571: (0x5572,), 0x5572: (0x5575,),
    0x5575: (0x5576,), 0x5576: (0x5578,), 0x5578: (0x557D,),
    0x557D: (0x55BF, 0x557F), 0x557F: (0x5582,), 0x5582: (0x5585,),
    0x5585: (0x5592, 0x5588), 0x5588: (0x5592, 0x558B),
    0x558B: (0x558E,), 0x558E: (0x5592,), 0x5592: (0x5594,),
    0x5594: (J_NB,), J_NB: (0x5596,),
    0x55BF: (0x55C1,), 0x55C1: (0x55C3,), 0x55C3: (J_BELOW,),
    J_BELOW: (0x55C5,),
}
ANCHORS = (0x5596, 0x55C5)
TAKEN = ((0x557D, 0x55BF), (0x5585, 0x5592), (0x5588, 0x5592))
DD_REQUIRED_ZERO = (0x5571, 0x5576, 0x5594, 0x55C1, 0x55C3)
DD_ZERO_WRITERS = (0x556F, 0x5575, 0x5592, 0x55BF)
FLAGS = ("CF", "ZF", "HC", "DD") + tuple("PSW" + str(bit) for bit in range(12))
FLAG_WRITES = {
    0x556F: ("ZF", "DD"), 0x5571: ("CF",), 0x5572: ("CF",),
    0x5575: ("ZF", "DD"), 0x5576: ("ZF",), 0x5578: ("CF", "ZF"),
    0x557D: (), 0x557F: (), 0x5582: ("ZF",), 0x5585: (), 0x5588: (),
    0x558B: ("ZF",), 0x558E: ("ZF",), 0x5592: ("ZF", "DD"),
    0x5594: ("ZF",), J_NB: (), 0x55BF: ("ZF", "DD"),
    0x55C1: (), 0x55C3: (), J_BELOW: (),
}
FUNCTIONAL_READS = {0x5572: ("CF",), 0x557D: ("CF",)}
MEMORY = {
    0x556F: (("Read", 0x018E, 8),), 0x5571: (),
    0x5572: (("Read", 0x018E, 8), ("Write", 0x018E, 8)),
    0x5575: (("Read", 0x0108, 8),), 0x5576: (("Read", 0x018E, 8),),
    0x5578: (("Read", 0x0196, 16),), 0x557D: (),
    0x557F: (("Read", 0x0117, 8), ("Write", 0x0109, 8)),
    0x5582: (("Read", 0x0117, 8), ("Write", 0x0117, 8)),
    0x5585: (("Read", 0x012A, 8),), 0x5588: (("Read", 0x0124, 8),),
    0x558B: (("Read", 0x018F, 8), ("Write", 0x018F, 8)),
    0x558E: (("Read", 0x012A, 8), ("Write", 0x012A, 8)),
    0x5592: (("Read", 0x018F, 8),), 0x5594: (), J_NB: (),
    0x55BF: (), 0x55C1: (("Write", 0x0117, 8),),
    0x55C3: (("Write", 0x018F, 8),), J_BELOW: (),
}


def enumerated_paths():
    """Own recursive graph traversal; external anchors are not internal nodes."""
    paths = []
    def visit(node, prior):
        if node in ANCHORS:
            paths.append((prior, node))
            return
        if node in prior:
            raise ValueError("Independent cycle")
        for next_node in SUCCESSORS[node]:
            visit(next_node, prior + (node,))
    visit(0x556F, ())
    return paths


def classified_edges():
    rows = []
    for source, targets in SUCCESSORS.items():
        for target in targets:
            kind = ("ExternalTransfer" if source in (J_NB, J_BELOW) else
                    "ConditionalTaken" if (source, target) in TAKEN else "Fallthrough")
            rows.append((source, target, kind))
    return rows


def expected_geometry(base, gap):
    """Half-open assigned-node intervals; unmodeled holes are not executable."""
    if type(base) is not int or not 0 <= base <= 65535:
        return {"failure": "Origin"}
    if type(gap) is not int or gap < 0:
        return {"failure": "Gap"}
    assignments = []
    for node, length, block, offset in NODE_ROWS:
        assigned = base + offset + (gap if block in ("Below", "DirectJ_Below") else 0)
        assignments.append({"node": node, "start": assigned, "endExclusive": assigned + length,
                            "length": length, "block": block})
    if any(row["start"] > 65535 or row["endExclusive"] > 65536 for row in assignments):
        return {"failure": "Span"}
    if 26 + gap > 127:
        return {"failure": "Reach"}
    collisions = [(anchor, row["node"]) for anchor in ANCHORS for row in assignments
                  if row["start"] <= anchor < row["endExclusive"]]
    hole_start, hole_end = base + 42, base + 42 + gap
    gap_aliases = [anchor for anchor in ANCHORS if hole_start <= anchor < hole_end]
    return {"assignments": assignments, "JLTDelta": 26 + gap,
            "JBS7Delta": 10, "JBS5Delta": 7, "extent": 51 + gap,
            "nodeCollisions": collisions, "gapAliases": gap_aliases,
            "hole": {"start": hole_start, "endExclusive": hole_end},
            "physicalPlacementAuthorized": False, "nativeExitIsolation": "NotEstablished"}


def expected_dd(initial):
    """Path-wise domain union, not an analyzer topological propagation routine."""
    if type(initial) is not tuple or not initial or any(type(x) is not int or x not in (0, 1) for x in initial):
        raise ValueError("Independent DD input domain")
    arrivals = {node: [] for node, *_ in NODE_ROWS}
    departures = {node: [] for node, *_ in NODE_ROWS}
    for nodes, _ in enumerated_paths():
        state = set(initial)
        for node in nodes:
            arrivals[node].append(set(state))
            if node in DD_REQUIRED_ZERO and state != {0}:
                raise ValueError("Independent DD selection conflict")
            if node in DD_ZERO_WRITERS:
                state = {0}
            departures[node].append(set(state))
    rows = []
    for node, *_ in NODE_ROWS:
        incoming, outgoing = set.union(*arrivals[node]), set.union(*departures[node])
        rows.append({"node": node, "incomingMay": sorted(incoming),
                     "incomingMust": next(iter(incoming)) if len(incoming) == 1 else None,
                     "outgoingMay": sorted(outgoing),
                     "outgoingMust": next(iter(outgoing)) if len(outgoing) == 1 else None,
                     "requiresDD0": node in DD_REQUIRED_ZERO})
    return rows


def expected_flag_writers():
    """Independent path-enumerated reaching writers and value-liveness unions."""
    incoming = {node: {flag: set() for flag in FLAGS} for node, *_ in NODE_ROWS}
    outgoing = {node: {flag: set() for flag in FLAGS} for node, *_ in NODE_ROWS}
    live_in = {node: set() for node, *_ in NODE_ROWS}
    live_out = {node: set() for node, *_ in NODE_ROWS}
    for nodes, _ in enumerated_paths():
        writers = {flag: "Incoming" for flag in FLAGS}
        for node in nodes:
            for flag in FLAGS:
                incoming[node][flag].add(writers[flag])
            for flag in FLAG_WRITES[node]:
                writers[flag] = node
            for flag in FLAGS:
                outgoing[node][flag].add(writers[flag])
        required = set(FLAGS)
        for node in reversed(nodes):
            live_out[node].update(required)
            required.difference_update(FLAG_WRITES[node])
            required.update(FUNCTIONAL_READS.get(node, ()))
            if node in DD_REQUIRED_ZERO:
                required.add("DD")
            live_in[node].update(required)
    return [{"node": node,
             "reachingWritersIn": {flag: sorted(incoming[node][flag], key=str) for flag in FLAGS},
             "reachingWritersOut": {flag: sorted(outgoing[node][flag], key=str) for flag in FLAGS},
             "liveIn": [flag for flag in FLAGS if flag in live_in[node]],
             "liveOut": [flag for flag in FLAGS if flag in live_out[node]]}
            for node, *_ in NODE_ROWS]


def expected_path_effects():
    rows = []
    for index, (nodes, anchor) in enumerate(enumerated_paths()):
        name = ("A", "B", "C", "D")[index]
        accesses = [{"node": node, "mode": mode, "address": address, "widthBits": width}
                    for node in nodes for mode, address, width in MEMORY[node]]
        writes = [{**access, "sameValueWrite": "RetainFreshOrdinal"}
                  for access in accesses if access["mode"] == "Write"]
        rows.append({"pathId": name, "nodes": list(nodes), "externalTarget": anchor,
                     "originalInstructionCount": len(nodes) - 1, "composedNodeCount": len(nodes),
                     "abstractJCount": sum(node in (J_NB, J_BELOW) for node in nodes),
                     "orderedAccesses": accesses, "orderedWrites": writes,
                     "CF": int(name == "A"), "ZF": 0, "DD": 0,
                     "AH": "IncomingAH", "HC": "IncomingHC", "OtherPSW": "IncomingOtherPSW",
                     "AL": {"kind": "ConstantByte", "value": 15} if name == "A" else
                           {"kind": "FinalMemoryOrImmediate", "address": 0x18F, "immediate": 0xF0},
                     "historicalCoverage": "StaticPrimaryAndInventedCoverage" if name == "C" else "HistoricalNativeValidated"})
    return rows


def independent_summary():
    edges = classified_edges()
    return {"originalSites": 18, "abstractJSlots": 2, "compositeNodes": len(NODE_ROWS),
            "originalLengthSum": sum(length for node, length, *_ in NODE_ROWS if type(node) is int),
            "addedTransferLength": sum(length for node, length, *_ in NODE_ROWS if type(node) is str),
            "denseLength": sum(length for _, length, *_ in NODE_ROWS),
            "edges": len(edges),
            "fallthroughEdges": sum(row[2] == "Fallthrough" for row in edges),
            "conditionalTakenEdges": sum(row[2] == "ConditionalTaken" for row in edges),
            "externalTransferEdges": sum(row[2] == "ExternalTransfer" for row in edges),
            "composedPathLengths": [len(nodes) for nodes, _ in enumerated_paths()],
            "writeCounts": [len(row["orderedWrites"]) for row in expected_path_effects()],
            "maxDenseBase": 65536 - 51, "maxGap101Base": 65536 - 152,
            "codecCalls": 0, "CPUExecutions": 0, "generatedMachineBytes": 0}



# Reviewed symbolic obligations, independently recorded before analyzer authoring.
REVIEWED_CONTEXT = {"classification": "StaticObligationRetentionOnly_NotRuntimeAssemblyEquivalence", "initialDD": [0, 1], "DD0AfterLogical556F": True, "carryDependencies": [{"producerLogicalSiteId": 21873, "consumerLogicalSiteId": 21874}, {"producerLogicalSiteId": 21880, "consumerLogicalSiteId": 21885}], "preserved": ["HC", "OtherPSW", "AH", "SCB", "LRB", "X1", "X2", "DP", "USP", "SSP", "localr0", "localr2..r7", "DATA0124", "DATA0128", "DATA0196", "DATA0197", "SFUninterpreted"], "terminalDD": 0, "terminalZF": 0, "terminalCF": {"NotBelow": 0, "Below": 1}, "requiredLRB": 33, "currentPage": 256, "localBank": [264, 271], "word0196": {"address": 406, "highByteAddress": 407, "widthBits": 16, "byteOrder": "LittleEndian", "evenAddressed": True, "codeOwnedImmediate": 192, "hostRebasingAllowed": False}, "potentialWordAliases": [[278, 279], [292, 293], [296, 297], [298, 299], [398, 399], [406, 407]], "unknownStackAliases": "PossibleRegistersRAMSFR_NotGloballyExcluded", "nativeStackSafety": "NotEstablished", "nativeSFMeaningStorage": "PrimaryConflictUnresolved", "sameValueWrites": "RetainFreshOrdinal", "orderedWriteCounts": [3, 3, 3, 5], "firstGateTrueMustNotRead": 292, "historicalPath13NativeWitnesses": 0, "adaptersProloguesFlagWritersAllowed": False}
FORM_NAMES = (
    "lb-a-page", "sllb-a", "rolb-page", "lb-a-r0", "andb-a-page",
    "cmp-page-imm16", "jlt-rel8", "movb-r1-page", "andb-page-a",
    "jbs-page-bit7", "jbs-page-bit5", "andb-page-a", "orb-page-imm8",
    "lb-a-page", "orb-a-imm8", "lb-a-imm8", "stb-a-page", "stb-a-page",
)
WRITE_OPERATIONS = {
    0x5572: "ReadModifyWriteRotateThroughCarry", 0x557F: "CopyByte",
    0x5582: "ReadModifyWriteAnd", 0x558B: "ReadModifyWriteAnd",
    0x558E: "ReadModifyWriteOr", 0x55C1: "StoreByte", 0x55C3: "StoreByte",
}
COMPONENTS = (
    ("Common", 0, 16, 0), ("NotBelow", 16, 39, 0),
    (J_NB, 39, 42, 0), ("Below", 42, 48, 1), (J_BELOW, 48, 51, 1),
)
ISOLATION = {
    "abstractTransferEdge": "Specified", "architecturalPCReplacement": "Documented",
    "syntheticInternalCFG": "StructurallyIsolated", "nativeExitIsolation": "NotEstablished",
    "actualDownstreamRejoin": "NotEstablished", "physicalPlacement": "NotAuthorized",
    "targetEquivalence": "NotEstablished", "firmwareIntegration": "NotEstablished",
}
PERMISSIONS = {
    "codecsImportedOrCalled": False, "compositeBytes": False, "instructionStream": False,
    "CPU": False, "ROM": False, "assemblyObjectsFirmware": False, "GUIHardware": False,
}


def independent_copy(value):
    """No file or analyzer data dependence; return fresh literal expectation trees."""
    if type(value) is dict:
        return {key: independent_copy(scalar) for key, scalar in value.items()}
    if type(value) is list:
        return [independent_copy(scalar) for scalar in value]
    return value


def read_metadata(node, address, width):
    return {"pc": node, "address": address, "widthBits": width,
            "mode": "LocalRegister" if address in (0x0108, 0x0109) else "CurrentPage",
            "byteOrder": "LittleEndian" if width == 16 else "Byte"}


def expected_paths():
    """Independently enumerate graph paths and retain full ordered effect records."""
    rows = []
    for index, (nodes, anchor) in enumerate(enumerated_paths()):
        reads, writes, accesses, conditions = [], [], [], []
        for position, node in enumerate(nodes):
            if node in (0x557D, 0x5585, 0x5588):
                conditions.append({"pc": node, "result": (node, nodes[position + 1]) in TAKEN})
            for kind, address, width in MEMORY[node]:
                record = read_metadata(node, address, width)
                if kind == "Write":
                    record.update(operation=WRITE_OPERATIONS[node], ordered=True,
                                  sameValueWrite="RetainFreshOrdinal",
                                  staticWriteOrdinal=len(writes) + 1)
                    writes.append(record)
                else:
                    reads.append(record)
                accesses.append({"kind": kind, **record})
        name = ("A", "B", "C", "D")[index]
        final_al = ({"kind": "ConstantByte", "value": 15} if name == "A" else
                    {"kind": "FinalMemoryOrImmediate", "address": 0x018F, "immediate": 0xF0})
        rows.append({
            "id": name, "nodeIds": list(nodes), "conditions": conditions,
            "originalInstructionCount": len(nodes) - 1, "abstractTransferCount": 1,
            "composedNodeCount": len(nodes), "transferNodeId": nodes[-1],
            "externalTarget": anchor, "orderedReads": reads, "orderedWrites": writes,
            "orderedAccesses": accesses,
            "finalState": {"AL": final_al, "CF": int(name == "A"), "ZF": 0, "DD": 0,
                           "AH": "IncomingAH", "HC": "IncomingHC", "OtherPSW": "IncomingOtherPSW"},
            "historicalCoverage": ("StaticPrimaryAndInventedCoverage" if name == "C" else
                                   "HistoricalNativeValidated"),
        })
    return rows


def edge_predicate(node):
    if node == 0x557D:
        return {"kind": "FlagEquals", "flag": "CF", "value": 1}
    if node in (0x5585, 0x5588):
        return {"kind": "MemoryBitEquals", "address": 0x012A if node == 0x5585 else 0x0124,
                "bit": 7 if node == 0x5585 else 5, "value": 1}
    return None


def canonical_assignments(base, gap):
    return [{"nodeId": node, "assignedPC": base + offset +
             (gap if component in ("Below", J_BELOW) else 0)}
            for node, _, component, offset in NODE_ROWS]


def expected_result(base, gap, initial):
    """Frozen success projection from own positions, DFS and pathwise dataflow.

    This is not an emulator, target interpreter, code generator or analyzer
    wrapper. Inputs are invented scalar placement parameters only. No bytes
    are computed, imported, emitted or persisted.
    """
    geometry = expected_geometry(base, gap)
    if geometry.get("failure") or geometry["nodeCollisions"]:
        raise ValueError("Independent scenario is not accepted")
    positions = {row["nodeId"]: row["assignedPC"] for row in canonical_assignments(base, gap)}
    lengths = {node: length for node, length, _, _ in NODE_ROWS}
    node_spans = [{"nodeId": node, "assignedPC": positions[node],
                   "endExclusive": positions[node] + length, "length": length,
                   "component": component,
                   "nodeKind": "OriginalLogicalInstruction" if type(node) is int else "AbstractTransferSlot",
                   "originalLogicalSiteId": node if type(node) is int else None}
                  for node, length, component, _ in NODE_ROWS]
    component_spans = [
        {"name": name, "nodeIds": [node for node, _, group, _ in NODE_ROWS if group == name],
         "assignedStart": base + begin + coefficient * gap,
         "endExclusive": base + end + coefficient * gap,
         "length": end - begin, "startOffset": begin + coefficient * gap,
         "endOffset": end + coefficient * gap, "gapCoefficient": coefficient}
        for name, begin, end, coefficient in COMPONENTS]
    ordered_edges = [row for row in classified_edges() if row[0] not in (J_NB, J_BELOW)]
    ordered_edges += [row for row in classified_edges() if row[0] in (J_NB, J_BELOW)]
    edge_rows = [
        {"from": source, "to": target, "kind": kind, "predicate": edge_predicate(source),
         "fromAssignedPC": positions[source],
         "fromEndExclusive": positions[source] + lengths[source],
         "toAssignedPC": target if kind == "ExternalTransfer" else positions[target]}
        for source, target, kind in ordered_edges]
    branch_rows = [
        {"nodeId": source, "targetNodeId": target, "assignedPC": positions[source],
         "length": lengths[source], "nextPC": positions[source] + lengths[source],
         "assignedTargetPC": positions[target],
         "signedDelta": positions[target] - positions[source] - lengths[source]}
        for source, target in TAKEN]
    paths = expected_paths()
    dd_rows = [{("nodeId" if key == "node" else key): value for key, value in row.items()}
               for row in expected_dd(tuple(initial))]
    flag_rows = [{("nodeId" if key == "node" else key): value for key, value in row.items()}
                 for row in expected_flag_writers()]
    graph = classified_edges()
    counts = {
        "originalSites": sum(type(node) is int for node, *_ in NODE_ROWS),
        "originalForms": len(set(FORM_NAMES)),
        "abstractTransferSlots": sum(type(node) is str for node, *_ in NODE_ROWS),
        "totalNodes": len(NODE_ROWS),
        "originalInstructionLength": sum(length for node, length, *_ in NODE_ROWS if type(node) is int),
        "abstractTransferLength": sum(length for node, length, *_ in NODE_ROWS if type(node) is str),
        "denseLength": sum(length for _, length, *_ in NODE_ROWS),
        "totalLength": 51 + gap, "edges": len(graph),
        "fallthroughEdges": sum(kind == "Fallthrough" for _, _, kind in graph),
        "conditionalTakenEdges": sum(kind == "ConditionalTaken" for _, _, kind in graph),
        "externalTransferEdges": sum(kind == "ExternalTransfer" for _, _, kind in graph),
        "originalPathCounts": [row["originalInstructionCount"] for row in paths],
        "composedPathCounts": [row["composedNodeCount"] for row in paths],
        "orderedWriteCounts": [len(row["orderedWrites"]) for row in paths],
        "structuralDDDomains": [[0], [1], [0, 1]], "selectedInitialDD": list(initial),
        "historicalPath13NativeWitnesses": 0, "codecCalls": 0, "compositeByteEmissionCalls": 0,
        "CPUExecutions": 0, "actualROMExecutions": 0, "targetObjects": 0, "targetHEX": 0, "FirmwareBIN": 0,
    }
    return {
        "classification": "ReviewedStatic20NodeCompositionSpecification",
        "nodeSpans": node_spans, "componentSpans": component_spans,
        "gap": {"assignedStart": base + 42, "endExclusive": base + 42 + gap,
                "startOffset": 42, "endOffset": 42 + gap, "length": gap,
                "classification": "Unmodeled_NotPadding_NotFreeROM_NotExecutable_NotPhysicalPlacement"},
        "edgeRows": edge_rows, "branchRows": branch_rows, "paths": paths,
        "ddFlow": dd_rows, "flagFlow": flag_rows,
        "contextObligations": independent_copy(REVIEWED_CONTEXT),
        "anchorObservations": [
            {"anchor": anchor, "gapContainsAnchor": anchor in geometry["gapAliases"],
             "assignedNodeCollision": False,
             "classification": ("UnknownGapAnchor_NotSafeFreeROM_NotPhysicalPlacement"
                                if anchor in geometry["gapAliases"] else
                                "OutsideAssignedNodeSpans_NotPhysicalPlacement")}
            for anchor in ANCHORS],
        "counts": counts, "isolation": independent_copy(ISOLATION),
        "permissions": independent_copy(PERMISSIONS),
    }


def named_positive_scenarios():
    return (
        ("dense-reference", 0x1000, 0), ("old-symbolic-gap41", 0x1000, 41),
        ("JLT-positive-127", 0x1000, 101), ("last-direct-J-FFFD", 0xFFCD, 0),
        ("gap101-last-direct-J-FFFD", 0xFF68, 101),
        ("anchor5596-exact-end-exclusive", 0x5596 - 51, 0),
        ("anchor55C5-exact-end-exclusive-and-gap5596", 0x55C5 - 152, 101),
        ("both-anchors-in-unmodeled-gap", 0x5540, 101),
    )


def collision_descriptors():
    """All51 assigned byte positions x two anchors x two gaps x three DD domains.

    Offset expression is deliberately non-mutating inside the byte loop.
    Labels overlap for some contexts; report natural unique context count.
    """
    rows = []
    for anchor in ANCHORS:
        for gap in (0, 101):
            for initial in ((0,), (1,), (0, 1)):
                for node, length, component, offset in NODE_ROWS:
                    adjusted_offset = offset + (gap if component in ("Below", J_BELOW) else 0)
                    for byte_position in range(length):
                        base = anchor - adjusted_offset - byte_position
                        rows.append({"label": f"anchor-{anchor}-node-{node}-byte-{byte_position}-gap-{gap}-DD-{initial}",
                                     "base": base, "gap": gap, "initial": list(initial),
                                     "expectedCode": "SyntheticExternalAnchorCollision", "expectedStage": "Anchor"})
    return rows
