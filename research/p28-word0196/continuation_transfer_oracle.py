"""Independent continuation identity and invented transfer mathematics.

Prepared from retained M2bd/M2be obligations and separately reviewed primary
length/PC facts before any M2bf analyzer comparison. No analyzer/codec/CPU/IO
dependency. These are static requirements and integer predicates, not execution.
"""

COMMON = (0x556F, 0x5571, 0x5572, 0x5575, 0x5576, 0x5578, 0x557D)
PATHS = (
    ("A", COMMON + (0x55BF, 0x55C1, 0x55C3), 0x55C5),
    ("B", COMMON + (0x557F, 0x5582, 0x5585, 0x5592, 0x5594), 0x5596),
    ("C", COMMON + (0x557F, 0x5582, 0x5585, 0x5588, 0x5592, 0x5594), 0x5596),
    ("D", COMMON + (0x557F, 0x5582, 0x5585, 0x5588, 0x558B, 0x558E,
                    0x5592, 0x5594), 0x5596),
)
WRITES = {
    "A": ((0x5572, 0x018E, 8), (0x55C1, 0x0117, 8), (0x55C3, 0x018F, 8)),
    "B": ((0x5572, 0x018E, 8), (0x557F, 0x0109, 8), (0x5582, 0x0117, 8)),
    "C": ((0x5572, 0x018E, 8), (0x557F, 0x0109, 8), (0x5582, 0x0117, 8)),
    "D": ((0x5572, 0x018E, 8), (0x557F, 0x0109, 8), (0x5582, 0x0117, 8),
          (0x558B, 0x018F, 8), (0x558E, 0x012A, 8)),
}
TARGETS = {"NotBelow": 0x5596, "Below": 0x55C5}
LENGTHS = {"SJ-address": 2, "J-address": 3}
PRESERVED = ("AH", "HC", "OtherPSW", "SCB", "LRB", "X1", "X2", "DP", "USP",
             "SSP", "localr0", "localr2..r7", "DATA0124", "DATA0128",
             "DATA0196", "DATA0197", "SFUninterpreted")


def expected_exit_requirements():
    """Logical state requirements, not native observations or new write journals."""
    rows = []
    for name, target in TARGETS.items():
        below = name == "Below"
        paths = [path_name for path_name, _, stop in PATHS if stop == target]
        rows.append({
            "id": name, "targetPC": target,
            "pathIds": paths,
            "pathLengths": [len(pcs) for path_name, pcs, _ in PATHS if path_name in paths],
            "AL": {"kind": "ConstantByte", "value": 0x0F} if below else
                  {"kind": "FinalMemoryOrImmediate", "address": 0x018F, "immediate": 0xF0},
            "CF": int(below), "ZF": 0, "DD": 0,
            "AH": "IncomingAH", "HC": "IncomingHC", "OtherPSW": "IncomingOtherPSW",
            "LRB": 0x21, "SCB": "IncomingPSWLowThreeBits",
            "SSP": "IncomingSSP", "pointingRegisters": "AllIncomingBanks",
            "preserved": list(PRESERVED),
            "nativeRejoin": "NotEstablished",
        })
    return rows


def span_failure(origin, length):
    if type(origin) is not int or not 0 <= origin <= 65535:
        return "Origin"
    if type(length) is not int or length not in (2, 3):
        return "Length"
    return "Span" if origin + length > 65536 else None


def transfer_failure(form, origin, target):
    """Independent form-specific mathematical constraints; no byte emission."""
    if type(form) is not str or form not in ("SJ-address", "J-address", "J-obj"):
        return "Form"
    if form == "J-obj":
        return "Owner"
    if type(origin) is not int or not 0 <= origin <= 65535:
        return "Origin"
    if type(target) is not int or not 0 <= target <= 65535:
        return "Target"
    if origin + LENGTHS[form] > 65536:
        return "Span"
    if form == "SJ-address" and origin + 2 > 65535:
        return "NextPC"
    if form == "SJ-address" and not -128 <= target - origin - 2 <= 127:
        return "Relative"
    return None

def relative_origin_interval(target):
    """Inverting the reviewed inequality; invented origins, not usable ROM space."""
    if type(target) is not int or not 0 <= target <= 65535:
        raise ValueError("Independent target address domain")
    lower, upper = max(0, target - 129), min(65533, target + 126)
    return {"minimum": lower, "maximum": upper,
            "originCount": max(0, upper - lower + 1)}


def expected_transfer(form, origin, target):
    failure = transfer_failure(form, origin, target)
    if failure is not None:
        return {"failure": failure}
    length = LENGTHS[form]
    return {
        "passed": True, "classification": "SyntheticTransferRepresentabilityOnly",
        "formId": form, "origin": origin, "length": length,
        "endExclusive": origin + length, "nextPC": origin + length,
        "target": target,
        "signedDelta": target - origin - 2 if form == "SJ-address" else None,
        "targetRepresentable": True, "executionBlocked": True,
        "runtimePermission": False, "targetBytes": 0, "encoderCalls": 0,
        "decoderCalls": 0, "CPUExecutions": 0, "actualROMExecutions": 0,
    }

def expected_terminal_hazards(base, gap, form):
    """Unmodified 45-byte geometry; extra length is hypothetical overhead only."""
    if type(base) is not int or type(gap) is not int or gap < 0 or form not in LENGTHS:
        raise ValueError("Independent terminal hypothesis domain")
    not_below_end, below_begin = base + 39, base + 39 + gap
    below_end = below_begin + 6
    length = LENGTHS[form]
    rows = []
    for name, origin in (("NotBelow", not_below_end), ("Below", below_end)):
        target = TARGETS[name]
        candidate_end = origin + length
        overlaps_below = name == "NotBelow" and max(origin, below_begin) < min(candidate_end, below_end)
        rows.append({
            "id": name, "logicalTarget": target, "syntheticBoundary": origin,
            "ordinaryFallthroughMatchesTarget": origin == target,
            "existingDenseFallthroughHazard": name == "NotBelow" and gap == 0,
            "positiveGapIsSafeExit": False,
            "hypotheticalTransferLength": length,
            "hypotheticalTransferEnd": candidate_end,
            "hypotheticalOverlapWithBelow": overlaps_below,
            "hypotheticalSelfTarget": origin == target,
            "geometryFailure": transfer_failure(form, origin, target),
            "actualTransferInserted": False,
            "instructionSitesRemain": 18,
            "originalLengthSumRemains": 45,
            "nativeExitIsolation": "NativeExitIsolationNotEstablished",
            "physicalReservation": "NotEstablished",
        })
    return rows

def expected_scalar(path_id, incoming_psw, incoming_ah, final_data018f):
    """Closed invented terminal equations; never an instruction or RAM executor."""
    if type(path_id) is not str or path_id not in ("A", "B", "C", "D"):
        raise ValueError("Independent path domain")
    if type(incoming_psw) is not int or not 0 <= incoming_psw <= 65535:
        raise ValueError("Independent incoming PSW domain")
    if any(type(value) is not int or not 0 <= value <= 255
           for value in (incoming_ah, final_data018f)):
        raise ValueError("Independent invented byte domain")
    below = path_id == "A"
    al = 15 if below else final_data018f | 240
    cf = int(below)
    hc = int((incoming_psw % 16384) >= 8192)
    preserved = incoming_psw % 4096
    final_psw = cf * 32768 + hc * 8192 + preserved
    actual_a = incoming_ah * 256 + al
    return {
        "arguments": [path_id, incoming_psw, incoming_ah,
                      final_data018f, actual_a, final_psw],
        "result": {
            "passed": True, "classification": "InventedTerminalScalarConstraintCheck_NotRuntimeState",
            "pathId": path_id, "originalTargetPC": 0x55C5 if below else 0x5596,
            "AL": al, "AH": incoming_ah, "CF": cf, "ZF": 0, "DD": 0, "HC": hc,
            "OtherPSW": preserved, "SCB": incoming_psw % 8,
            "executionBlocked": True, "runtimePermission": False,
            "actualRAMReads": 0, "actualRAMWrites": 0,
            "CPUExecutions": 0, "actualROMExecutions": 0,
        },
    }

SITE_LENGTHS = (
    (0x556F, 2), (0x5571, 1), (0x5572, 3), (0x5575, 1), (0x5576, 2),
    (0x5578, 5), (0x557D, 2), (0x557F, 3), (0x5582, 3), (0x5585, 3),
    (0x5588, 3), (0x558B, 3), (0x558E, 4), (0x5592, 2), (0x5594, 2),
    (0x55BF, 2), (0x55C1, 2), (0x55C3, 2),
)
READS = {
    "A": (0x556F, 0x5572, 0x5575, 0x5576, 0x5578),
    "B": (0x556F, 0x5572, 0x5575, 0x5576, 0x5578, 0x557F, 0x5582, 0x5585, 0x5592),
    "C": (0x556F, 0x5572, 0x5575, 0x5576, 0x5578, 0x557F, 0x5582, 0x5585, 0x5588, 0x5592),
    "D": (0x556F, 0x5572, 0x5575, 0x5576, 0x5578, 0x557F, 0x5582, 0x5585, 0x5588,
          0x558B, 0x558E, 0x5592),
}
FAILURE_CODES = {
    "Form": ("UnsupportedTransferForm", "Policy"),
    "Owner": ("PointerOwnerNotEstablished", "Ownership"),
    "Origin": ("OriginInvalid", "Origin"),
    "Target": ("TargetInvalid", "Target"),
    "Span": ("SpanOutsideProfile", "Span"),
    "NextPC": ("NextPCOutsideProfile", "NoWrap"),
    "Relative": ("Rel8OutOfRange", "Reach"),
}


def existing_assignments(base, gap):
    rows = []
    for pc, length in SITE_LENGTHS:
        # Logical intervals determine within-block offsets; gap is invented.
        assigned = (base + pc - 0x556F if pc < 0x557F else
                    base + 16 + pc - 0x557F if pc < 0x55BF else
                    base + 39 + gap + pc - 0x55BF)
        rows.append({"logicalSiteId": pc, "syntheticAssignedPC": assigned,
                     "length": length, "endExclusive": assigned + length})
    return rows


def expected_hypothesis(base, gap, form):
    """Independent full projection of the frozen mathematical hypothesis API."""
    assignments = existing_assignments(base, gap)
    if max(row["endExclusive"] for row in assignments) > 65536:
        return {"failure": ("SpanOutsideProfile", "Span")}
    if 23 + gap > 127:
        return {"failure": ("OldInternalBranchOutOfRange", "ExistingCFG")}
    hypotheses = []
    for own_row in expected_terminal_hazards(base, gap, form):
        origin, end = own_row["syntheticBoundary"], own_row["hypotheticalTransferEnd"]
        overlaps = [row["logicalSiteId"] for row in assignments
                    if max(origin, row["syntheticAssignedPC"]) < min(end, row["endExclusive"])]
        failure = own_row["geometryFailure"]
        code, stage = FAILURE_CODES[failure] if failure else (None, None)
        hypotheses.append({
            "continuationId": own_row["id"], "originalTargetPC": own_row["logicalTarget"],
            "syntheticTransferOrigin": origin, "hypotheticalLength": LENGTHS[form],
            "hypotheticalEndExclusive": end,
            "representability": {
                "feasible": failure is None,
                "signedDelta": own_row["logicalTarget"] - origin - 2
                               if failure is None and form == "SJ-address" else None,
                "errorCode": code, "stage": stage,
            },
            "overlapLogicalSites": overlaps,
            "terminalHazard": "PotentialFallthroughIntoSyntheticBlock"
                              if own_row["existingDenseFallthroughHazard"] else "UnmodeledGapOrOutsideRegion",
            "originalNaturalFallthroughIdentity": own_row["ordinaryFallthroughMatchesTarget"],
            "hypotheticalSelfTarget": own_row["hypotheticalSelfTarget"],
            "spaceOwnership": "NotEstablished_NotFreeROM",
            "nativeExitIsolation": "NotEstablished",
            "actualDownstreamRejoin": "NotEstablished",
            "requiresFutureReservationOrRelayout": True, "transferInserted": False,
        })
    return {
        "passed": True, "classification": "HypotheticalContinuationTransferBudget_NotExecutableLayout",
        "formId": form,
        "existingGeometry": {"instructionSites": 18, "instructionLengthSum": 45,
                            "blockLengths": {"Common": 16, "NotBelow": 23, "Below": 6},
                            "syntheticBase": base, "gap": gap, "JLTDelta": 23 + gap,
                            "existingLayoutNotModified": True},
        "existingAssignments": assignments, "hypotheses": hypotheses,
        "hypotheticalTransferOverhead": 2 * LENGTHS[form],
        "newExecutableSites": 0, "executionBlocked": True, "runtimePermission": False,
        "targetBytes": 0, "CPUExecutions": 0, "actualROMExecutions": 0,
    }


def expected_path_rows():
    rows = []
    for name, pcs, target in PATHS:
        rows.append({
            "pathId": name, "originalInstructionCount": len(pcs),
            "continuationId": "Below" if name == "A" else "NotBelow",
            "originalTargetPC": target,
            "requiredFinalAL": {"kind": "ConstantByte", "value": 15} if name == "A" else
                               {"kind": "FinalMemoryOrImmediate", "address": 0x18F, "immediate": 0xF0},
            "requiredCF": int(name == "A"), "requiredZF": 0, "requiredDD": 0,
            "historicalCoverage": "StaticPrimaryAndInventedCoverage" if name == "C" else "HistoricalNativeValidated",
            "orderedReadSites": list(READS[name]),
            "orderedWriterSites": [row[0] for row in WRITES[name]],
            "writeCount": len(WRITES[name]), "sameValueWrites": "RetainFreshOrdinal",
            "mustNotRead": [0x124] if name == "B" else [],
        })
    return rows
