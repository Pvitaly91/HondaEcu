"""Independent M2be positional mathematics, prepared before the new analyzer.

Historical sites are logical identities and length facts only. This module has
no analyzer, encoder, decoder, CPU, file, network or process dependency. It
returns mathematical integers and symbolic obligations, never instruction bytes.
All terminal markers are research end boundaries, not executable instructions.
"""

# (LogicalSiteId, exact form identity, length, logical block, within-block offset).
# These literal reviewed rows are not an opcode or emission table.
SITES = (
    (0x556F, "lb-a-page", 2, "Common", 0),
    (0x5571, "sllb-a", 1, "Common", 2),
    (0x5572, "rolb-page", 3, "Common", 3),
    (0x5575, "lb-a-r0", 1, "Common", 6),
    (0x5576, "andb-a-page", 2, "Common", 7),
    (0x5578, "cmp-page-imm16", 5, "Common", 9),
    (0x557D, "jlt-rel8", 2, "Common", 14),
    (0x557F, "movb-r1-page", 3, "NotBelow", 0),
    (0x5582, "andb-page-a", 3, "NotBelow", 3),
    (0x5585, "jbs-page-bit7", 3, "NotBelow", 6),
    (0x5588, "jbs-page-bit5", 3, "NotBelow", 9),
    (0x558B, "andb-page-a", 3, "NotBelow", 12),
    (0x558E, "orb-page-imm8", 4, "NotBelow", 15),
    (0x5592, "lb-a-page", 2, "NotBelow", 19),
    (0x5594, "orb-a-imm8", 2, "NotBelow", 21),
    (0x55BF, "lb-a-imm8", 2, "Below", 0),
    (0x55C1, "stb-a-page", 2, "Below", 2),
    (0x55C3, "stb-a-page", 2, "Below", 4),
)
BLOCKS = (
    ("Common", 0x556F, 0x557F),
    ("NotBelow", 0x557F, 0x5596),
    ("Below", 0x55BF, 0x55C5),
)
FALLTHROUGHS = (
    (0x556F, 0x5571), (0x5571, 0x5572), (0x5572, 0x5575),
    (0x5575, 0x5576), (0x5576, 0x5578), (0x5578, 0x557D),
    (0x557D, 0x557F), (0x557F, 0x5582), (0x5582, 0x5585),
    (0x5585, 0x5588), (0x5588, 0x558B), (0x558B, 0x558E),
    (0x558E, 0x5592), (0x5592, 0x5594),
    (0x55BF, 0x55C1), (0x55C1, 0x55C3),
)
TAKEN_BRANCHES = ((0x557D, 0x55BF), (0x5585, 0x5592), (0x5588, 0x5592))
TERMINAL_EDGES = ((0x5594, 0x5596, "NotBelow"), (0x55C3, 0x55C5, "Below"))
COMMON_PATH = (0x556F, 0x5571, 0x5572, 0x5575, 0x5576, 0x5578, 0x557D)
PATHS = (
    ("A", COMMON_PATH + (0x55BF, 0x55C1, 0x55C3), 0x55C5),
    ("B", COMMON_PATH + (0x557F, 0x5582, 0x5585, 0x5592, 0x5594), 0x5596),
    ("C", COMMON_PATH + (0x557F, 0x5582, 0x5585, 0x5588, 0x5592, 0x5594), 0x5596),
    ("D", COMMON_PATH + (0x557F, 0x5582, 0x5585, 0x5588, 0x558B, 0x558E,
                         0x5592, 0x5594), 0x5596),
)
WRITES = {
    "A": ((0x5572, 0x018E, 8), (0x55C1, 0x0117, 8), (0x55C3, 0x018F, 8)),
    "B": ((0x5572, 0x018E, 8), (0x557F, 0x0109, 8), (0x5582, 0x0117, 8)),
    "C": ((0x5572, 0x018E, 8), (0x557F, 0x0109, 8), (0x5582, 0x0117, 8)),
    "D": ((0x5572, 0x018E, 8), (0x557F, 0x0109, 8), (0x5582, 0x0117, 8),
          (0x558B, 0x018F, 8), (0x558E, 0x012A, 8)),
}


def reviewed_arithmetic():
    """Compute from literal extents, not the supplied contract or analyzer."""
    lengths = {block: sum(length for _, _, length, name, _ in SITES if name == block)
               for block, _, _ in BLOCKS}
    return {
        "siteCount": len({pc for pc, *_ in SITES}),
        "distinctForms": len({form for _, form, *_ in SITES}),
        "instructionBytes": sum(row[2] for row in SITES),
        "blockLengths": lengths,
        "outerEnvelope": 0x55C5 - 0x556F,
        "excludedUnmodeledRegion": {"start": 0x5596, "endExclusive": 0x55BF,
                                   "length": 0x55BF - 0x5596},
        "edgeCount": len(FALLTHROUGHS) + len(TAKEN_BRANCHES) + len(TERMINAL_EDGES),
        "internalFallthroughCount": len(FALLTHROUGHS),
        "conditionalTakenCount": len(TAKEN_BRANCHES),
        "analyticalTerminalCount": len(TERMINAL_EDGES),
        "referenceSignedDeltas": [
            {"site": pc, "target": target,
             "delta": target - (pc + next(row[2] for row in SITES if row[0] == pc))}
            for pc, target in TAKEN_BRANCHES],
        "pathLengths": [len(path) for _, path, _ in PATHS],
        "orderedWriteCounts": [len(WRITES[name]) for name, _, _ in PATHS],
        "targetBytes": 0,
        "executionAuthority": False,
    }


def span_condition(start, length):
    """Independent mathematical interval predicate; bool is not an address."""
    if type(start) is not int or not 0 <= start <= 65535:
        return "Origin"
    if type(length) is not int or not 1 <= length <= 5:
        return "Length"
    return "Span" if start + length > 65536 else None


def relative_condition(start, length, target):
    """No encoding, two's-complement conversion, modulo repair or CPU execution."""
    failure = span_condition(start, length)
    if failure is not None:
        return failure
    if start + length > 65535:
        return "NextPC"
    if type(target) is not int or not 0 <= target <= 65535:
        return "Target"
    delta = target - start - length
    return "Rel8" if delta < -128 or delta > 127 else None


def interval_overlap(spans):
    """Quadratic independent intersection test, not an analyzer sort algorithm."""
    pairs = []
    for index, (identity, start, end) in enumerate(spans):
        for other, other_start, other_end in spans[index + 1:]:
            if max(start, other_start) < min(end, other_end):
                pairs.append((identity, other))
    return pairs


def expected_layout(base, gaps=(0, 0), order=("Common", "NotBelow", "Below")):
    """Own fixed-position equations over invented scalar addresses.

    Arbitrary order is used solely to expose adjacency violations. Admissibility
    is additionally constrained to the separately authorized canonical order.
    End-exclusive terminal markers may equal 65536; they are not PC16 operands.
    """
    if type(base) is not int or not 0 <= base <= 65535:
        raise ValueError("Independent synthetic origin domain")
    if type(gaps) is not tuple or len(gaps) != 2 or any(type(g) is not int or g < 0 for g in gaps):
        raise ValueError("Independent symbolic gaps domain")
    if type(order) is not tuple or sorted(order) != ["Below", "Common", "NotBelow"]:
        raise ValueError("Independent blocks domain")
    block_lengths = reviewed_arithmetic()["blockLengths"]
    starts, cursor = {}, base
    for ordinal, block in enumerate(order):
        starts[block] = cursor
        cursor += block_lengths[block]
        if ordinal < 2:
            cursor += gaps[ordinal]
    assigned = {pc: starts[block] + offset for pc, _, _, block, offset in SITES}
    spans = [(pc, assigned[pc], assigned[pc] + length) for pc, _, length, _, _ in SITES]
    lengths = {pc: length for pc, _, length, _, _ in SITES}
    fallthroughs = [{"site": source, "successor": target,
                     "sourceEnd": assigned[source] + lengths[source],
                     "targetStart": assigned[target],
                     "adjacent": assigned[source] + lengths[source] == assigned[target]}
                    for source, target in FALLTHROUGHS]
    branches = [{"site": source, "targetSite": target,
                 "branchStart": assigned[source], "nextPC": assigned[source] + lengths[source],
                 "targetStart": assigned[target],
                 "signedDelta": assigned[target] - assigned[source] - lengths[source],
                 "failure": relative_condition(assigned[source], lengths[source], assigned[target])}
                for source, target in TAKEN_BRANCHES]
    terminals = []
    for source, marker, block in TERMINAL_EDGES:
        boundary = assigned[source] + lengths[source]
        physically_adjacent = [name for name, _, _ in BLOCKS if starts[name] == boundary]
        terminals.append({
            "logicalTerminalMarker": marker,
            "lastLogicalSite": source,
            "syntheticBoundary": boundary,
            "physicallyAdjacentBlocks": physically_adjacent,
            "accidentalFallthrough": bool(physically_adjacent),
            "continuation": "BranchSelectedExternalContinuationNotEstablished",
            "instructionAtMarker": False,
            "nativeExitIsolation": "NativeExitIsolationNotEstablished",
        })
    holes = []
    for ordinal, block in enumerate(order[:-1]):
        begin = starts[block] + block_lengths[block]
        end = starts[order[ordinal + 1]]
        if end > begin:
            holes.append({"start": begin, "endExclusive": end, "length": end - begin,
                          "behavior": "Unmodeled", "verifiedFreeROM": False,
                          "executablePadding": False})
    return {
        "assigned": assigned,
        "spans": spans,
        "blockStarts": starts,
        "spanFailures": [(pc, span_condition(start, end - start))
                         for pc, start, end in spans if span_condition(start, end - start)],
        "overlaps": interval_overlap(spans),
        "fallthroughs": fallthroughs,
        "branches": branches,
        "terminals": terminals,
        "holes": holes,
        "pathIdentities": [{"id": name, "logicalSites": list(path), "logicalTerminal": terminal,
                           "instructionCount": len(path),
                           "orderedWrites": [list(row) for row in WRITES[name]]}
                          for name, path, terminal in PATHS],
        "canonicalBlockOrder": order == ("Common", "NotBelow", "Below"),
        "geometryWithinAddressSpace": all(span_condition(start, end - start) is None
                                         for _, start, end in spans),
        "allInternalFallthroughsAdjacent": all(row["adjacent"] for row in fallthroughs),
        "allRelativeBranchesInRange": all(row["failure"] is None for row in branches),
        "nativeIntegration": "NativeIntegrationNotEstablished",
        "executionAuthority": False,
    }


def named_scenarios():
    """Literal labels and independent arithmetic, never post-analyzer fixtures."""
    rows = [
        ("A-original-shaped-reference", 0x556F, (0, 41), ("Common", "NotBelow", "Below")),
        ("B-dense-invented", 0x1000, (0, 0), ("Common", "NotBelow", "Below")),
        ("C-gap-maximum-signed", 0x1000, (0, 104), ("Common", "NotBelow", "Below")),
        ("C-gap-first-too-far", 0x1000, (0, 105), ("Common", "NotBelow", "Below")),
        ("E-last-nonbranch-byte-FFFF", 0xFFD3, (0, 0), ("Common", "NotBelow", "Below")),
        ("E-last-span-exceeds-FFFF", 0xFFD4, (0, 0), ("Common", "NotBelow", "Below")),
        ("E-reference-gap-last-byte-FFFF", 0xFFAA, (0, 41), ("Common", "NotBelow", "Below")),
        ("E-rel8-limit-gap-last-byte-FFFF", 0xFF6B, (0, 104), ("Common", "NotBelow", "Below")),
        ("F-below-between-fallthrough-blocks", 0x1000, (0, 0), ("Common", "Below", "NotBelow")),
        ("F-gap-breaks-JLT-false", 0x1000, (1, 0), ("Common", "NotBelow", "Below")),
    ]
    return [{"label": label, "base": base, "gaps": list(gaps), "order": list(order),
             "expected": expected_layout(base, gaps, order)}
            for label, base, gaps, order in rows]
