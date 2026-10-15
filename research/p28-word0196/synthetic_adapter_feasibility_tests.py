"""Independent M2bl relation tests; sealed before any analyzer comparison.

Only invented JSON claims and opaque cell identities are handled.  No opcodes,
CPU calls, ROM, processes, executable payloads, or files are consumed here.
The frozen oracle predates the analyzer; literal obligations below are manual
geometry/architecture/CFG facts, not expectations learned from its output.
"""

from copy import deepcopy
from hashlib import sha256
import json

import synthetic_adapter_feasibility_oracle as oracle


ORACLE_SOURCE_SHA256 = "4414f6de4fe705f4b097a00c7aed3fac951d5951f050589f3276b21e4c406268"
PSW_RECORD_DIGEST = "750575c886569e03326eb29e2a0c3e3dc53621c00306ef21c281904d0936663e"
READS_ONE, STORAGE = 0x0CC8, 0x0337
FLAG_BITS = (("cf", 15), ("zf", 14), ("hc", 13), ("dd", 12))
AREAS = ("mapping", "admission", "snapshot", "permissions", "fetchExit", "psw", "evidence")
UNKNOWN_SF = {"status": "SFMeaningStorageNotEstablished", "value": None,
              "meaning": None, "storage": None, "widthBits": None}
DATA_KEYS = ("0108", "0109", "010A", "010B", "010C", "010D", "010E", "010F",
             "0117", "0124", "0128", "012A", "018E", "018F", "0196", "0197")

# Original logical identity, synthetic PC, exact form, length, target.  These
# literal facts are not discovered by decoding, executing, or asking analyzer.
NODE_FACTS = (
    (0x556F, 0x1000, "lb-a-page", 2, None),
    (0x5571, 0x1002, "sllb-a", 1, None),
    (0x5572, 0x1003, "rolb-page", 3, None),
    (0x5575, 0x1006, "lb-a-r0", 1, None),
    (0x5576, 0x1007, "andb-a-page", 2, None),
    (0x5578, 0x1009, "cmp-page-imm16", 5, None),
    (0x557D, 0x100E, "jlt-rel8", 2, 0x102A),
    (0x557F, 0x1010, "movb-r1-page", 3, None),
    (0x5582, 0x1013, "andb-page-a", 3, None),
    (0x5585, 0x1016, "jbs-page-bit7", 3, 0x1023),
    (0x5588, 0x1019, "jbs-page-bit5", 3, 0x1023),
    (0x558B, 0x101C, "andb-page-a", 3, None),
    (0x558E, 0x101F, "orb-page-imm8", 4, None),
    (0x5592, 0x1023, "lb-a-page", 2, None),
    (0x5594, 0x1025, "orb-a-imm8", 2, None),
    ("DirectJ_NotBelow", 0x1027, "j-address", 3, 0x5596),
    (0x55BF, 0x102A, "lb-a-imm8", 2, None),
    (0x55C1, 0x102C, "stb-a-page", 2, None),
    (0x55C3, 0x102E, "stb-a-page", 2, None),
    ("DirectJ_Below", 0x1030, "j-address", 3, 0x55C5),
)
PATH_INDICES = {
    "A": (0, 1, 2, 3, 4, 5, 6, 16, 17, 18, 19),
    "B": (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 13, 14, 15),
    "C": (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 13, 14, 15),
    "D": (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15),
}
PATH_COUNTS = {"A": (11, 5, 3), "B": (13, 9, 3), "C": (14, 10, 3), "D": (16, 12, 5)}
MANDATORY_CATEGORIES = (
    "PROGRAM base0 accepted incorrectly",
    "PC1000 mapped to wrong offset",
    "Last-byte off-by-one",
    "Fetch1033 allowed",
    "Fetch5596 allowed",
    "Fake padding inserted",
    "Original ROM accepted",
    "Wrong content digest",
    "Wrong node inventory",
    "Seventh unsupported form silently admitted",
    "Direct J admitted by generic mnemonic",
    "Unknown DD accepted",
    "Wrong initial PSW",
    "Wrong SCB",
    "Missing pointing bank",
    "Unselected bank overwritten",
    "AH clobber",
    "SSP changed",
    "SF defaulted false",
    "PSW reads-one masked away",
    "Incompatible OtherPSW silently normalized",
    "CF/ZF/HC/DD mixed with OtherPSW",
    "DATA read permission used as write permission",
    "Unauthorized DATA write",
    "Unauthorized DATA read",
    "DATA0124 read on B",
    "DATA012A write on B/C",
    "Same-value write removed",
    "Local r1 alias broken",
    "DATA0196 word read reversed",
    "Immediate00C0 treated as DATA read",
    "Decoder lookahead counted as executed instruction",
    "Selected PROGRAM extent lost",
    "External target fetched after J",
    "J replaced with return",
    "Two J executed on one path",
    "CPU trace fabricated",
    "Rust adapter declared implemented",
    "FirmwareReady promoted",
)


def _require(condition, message):
    if not condition:
        raise AssertionError(message)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _equal(actual, expected, label):
    _require(_canonical(actual) == _canonical(expected), "WholeRecordMismatch:" + label)


def _digest(value):
    return sha256(_canonical(value).encode("ascii")).hexdigest()


def _replace(request, path, value):
    current = request["payload"]
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = deepcopy(value)
    return request


def _case(area, path=None, value=None, variant=0):
    result = oracle.make_case(area, variant)
    return result if path is None else _replace(result, path, value)


def _psw_word(snapshot):
    return snapshot["otherPsw"] | sum(snapshot[name] << bit for name, bit in FLAG_BITS)


def _snapshot_case(variant=0, dd=0, canonical=False):
    other = ((variant * 0x123) & 0xFF8) | (variant % 8)
    if canonical:
        other |= READS_ONE
    before = oracle.make_snapshot(variant, dd, other)
    after = deepcopy(before)
    after["pc"] = 0x55C5 if variant % 4 == 0 else 0x5596
    after["al"] = (after["al"] + 17) % 256
    after["a"] = after["al"] | (after["ah"] << 8)
    after["dd"] = 0
    after["psw"] = _psw_word(after)
    return {"area": "snapshot", "payload": {"before": before, "after": after,
            "route": "manufacturer-compatible" if canonical else "lossless-research"}}


def _manual_psw(other, flags):
    requested = other | sum(flags[name] << bit for name, bit in FLAG_BITS)
    encoded = (other & 0x0337) | 0x0CC8 | (requested & 0xF000)
    compatible = (other & 0x0CC8) == 0x0CC8
    return {
        "requestedPsw": requested, "otherPsw": other, "namedFlags": deepcopy(flags),
        "decodedCpuState": dict({"storedOther": other & 0x0337}, **flags),
        "encodedPsw": encoded, "representable": compatible,
        "losslessRoundTrip": requested == encoded, "changedBits": requested ^ encoded,
        "readsOneMask": 0x0CC8, "storageMask": 0x0337,
        "routeA": "ConditionallyAdmissible_SeparateScopeDecisionRequired" if compatible
        else "RejectedInManufacturerCompatibleDomain",
        "routeB": {"losslessResearchOtherPsw": other,
                   "cpuPswRepresentationCompatibleByMathematics": compatible,
                   "runtimeAdapterCompatibility": "NotEstablished"},
        "upstreamOracleDomainChanged": False,
        "fullInventedDomainRuntimeCompatibility": "NotEstablished",
    }


def _check_manual_inventory(nodes):
    _require(len(nodes) == 20, "LiteralNodeCount")
    _require(len({node["formId"] for node in nodes}) == 16, "LiteralFormCount")
    for index, (node, fact) in enumerate(zip(nodes, NODE_FACTS)):
        _equal([node["nodeIdentity"], node["syntheticPc"], node["formId"], node["length"], node["target"]],
               list(fact), "ManualNodeFact:" + str(index))
        _equal(node["reachableDd"], [0, 1] if index == 0 else [0], "ManualReachableDd")
        expected_arch = [0] if index in (1, 4, 14, 17, 18) else [0, 1]
        _equal(node["architecturalDd"], expected_arch, "ManualArchitecturalDd")
        _require(node["syntheticPc"] + node["length"] <= 0x1033, "ManualNodeExtent")
        if index + 1 < 20:
            _require(node["syntheticPc"] + node["length"] == nodes[index + 1]["syntheticPc"], "ManualInventoryContiguity")
    _equal(nodes[5]["typedOperands"], [{"kind": "EvenPageOffset8", "value": 0x96},
           {"kind": "Immediate16", "value": 0xC0}], "ManualImmediateNotData")
    _equal(nodes[7]["typedOperands"], [{"kind": "Register1", "value": 1},
           {"kind": "PageOffset8", "value": 0x17}], "ManualLocalR1Copy")
    _equal(nodes[15]["typedOperands"], [{"kind": "ProgramTarget16", "value": 0x5596}], "ManualJNotBelow")
    _equal(nodes[19]["typedOperands"], [{"kind": "ProgramTarget16", "value": 0x55C5}], "ManualJBelow")


def _check_manual_snapshot(case, result):
    before, after = case["payload"]["before"], case["payload"]["after"]
    _require(before["a"] == before["al"] + 256 * before["ah"], "ManualAccumulatorAlias")
    _require(after["a"] == after["al"] + 256 * after["ah"] and after["ah"] == before["ah"], "ManualAhRetention")
    _equal(before["sf"], UNKNOWN_SF, "ManualUnknownSf")
    _equal(after["pointingBanks"], before["pointingBanks"], "ManualAllBanksRetained")
    _require(len(before["pointingBanks"]) == 8 and before["scb"] == before["otherPsw"] % 8, "ManualAllScb")
    _require(all(set(bank) == {"X1", "X2", "DP", "USP"} for bank in before["pointingBanks"]), "ManualBankFields")
    local = [before["localData"][key] for key in DATA_KEYS[:8]]
    _equal(before["localAliases"], {"r": local, "er": [local[2 * i] + 256 * local[2 * i + 1] for i in range(4)]}, "ManualLocalAliases")
    expected = {
        "schema": "SyntheticCpuEntrySnapshot", "complete": True, "pointingBankCount": 8,
        "activeBank": before["scb"], "localBankBase": 0x108, "currentPage": 0x100,
        "aliasEr0": local[0] + 256 * local[1], "route": case["payload"]["route"],
        "pswRepresentable": (before["otherPsw"] & READS_ONE) == READS_ONE,
        "sf": deepcopy(UNKNOWN_SF), "upstreamOracleDomainChanged": False,
        "preservation": {"preservedFields": ["ah", "hc", "otherPsw", "lrb", "scb", "ssp", "pointingBanks", "halted", "sf"],
                         "allEightBanksPreserved": True, "ahPreserved": True, "sspPreserved": True,
                         "r1Er0HighMayChangeOnlyThroughReviewedDataWrite": True},
    }
    _equal(result, expected, "ManualCompleteSnapshotSummary")


def _check_manual_data(case, result):
    payload, path = case["payload"], case["payload"]["path"]
    _, reads, writes = PATH_COUNTS[path]
    _equal(sorted(payload["initialData"]), sorted(DATA_KEYS), "ManualClosed16DataBytes")
    _require(result["logicalReadCount"] == reads and result["writeCount"] == writes, "ManualDataCounts")
    _require(result["sameValueWrites"] >= 1, "ManualSameValueStoreRetained")
    _require(result["actualFunctionalJournal"] == "NotRun", "ManualNotAnActualJournal")
    _require(0x196 not in result["writePermissions"] and 0x197 not in result["writePermissions"], "ManualWordReadonly")
    _require((0x124 in result["readPermissions"]) == (path in "CD"), "ManualBReadSuppression")
    _require((0x12A in result["writePermissions"]) == (path == "D"), "ManualDOnlyWrite")
    _require(result["word0196"] == payload["initialData"]["0196"] + 256 * payload["initialData"]["0197"], "ManualLE16")
    final = result["finalData"]
    _require(result["finalLocalAliases"]["er"][0] == final["0108"] + 256 * final["0109"], "ManualR1Er0Alias")
    _require(final["0108"] == payload["initialData"]["0108"], "ManualR0Preserved")
    _require(final["0109"] == payload["initialData"]["0109" if path == "A" else "0117"], "ManualConditionalR1Copy")
    _require(not any(event["address"] == 0xC0 for event in payload["events"]), "ManualNoImmediateDataRead")


def _check_manual_fetch(case, result):
    payload, path = case["payload"], case["payload"]["path"]
    indices = PATH_INDICES[path]
    _equal([event["entryPc"] for event in payload["events"]], [NODE_FACTS[i][1] for i in indices], "ManualPathPcOrder")
    _require(result["instructionCount"] == PATH_COUNTS[path][0] and result["directJCount"] == 1, "ManualExactPathInstructions")
    _require(result["terminalPc"] == (0x55C5 if path == "A" else 0x5596), "ManualTerminalPc")
    _require(result["externalProgramReadCount"] == 0 and result["cpuExecutionCount"] == 0, "ManualNoCpuOrExternalRead")
    _require(result["runtimeExitIsolation"] == "NotEstablished", "ManualRuntimeStillUnestablished")
    selected_bytes = sum(NODE_FACTS[i][3] for i in indices)
    _require(result["rawProgramReadCount"] == selected_bytes + result["lookaheadOrDiagnosticReadCount"], "ManualProbeSeparation")
    _equal(result["rawProgramReads"], payload["rawProgramObservationLedger"], "ManualCompleteRawLedger")


def _positive_cases():
    for offset in range(51):
        case = _case("mapping")
        case["payload"].update(requestedPc=0x1000 + offset, claimedOffset=offset)
        yield "mapping-offset-" + str(offset), case
    for dd in (0, 1):
        yield "inventory-entry-dd-" + str(dd), _case("admission", variant=dd)
    for variant in range(16):
        for dd in (0, 1):
            for canonical in (False, True):
                yield "snapshot-" + str((variant, dd, canonical)), _snapshot_case(variant, dd, canonical)
    for variant in range(16):
        for path_index, path in enumerate("ABCD"):
            # Independent of make_case's variant->path correlation.
            yield "data-" + path + "-" + str(variant), {"area": "permissions", "payload": oracle.make_data_case(path, variant)}
            for dd in (0, 1):
                fetch = {"area": "fetchExit", "payload": oracle.make_fetch_case(path, variant)}
                fetch["payload"]["events"][0]["incomingDd"] = dd
                yield "fetch-" + path + "-" + str((variant, dd)), fetch
    for path_index, path in enumerate("ABCD"):
        for word in (0, 191, 192, 65535):
            data = oracle.make_data_case(path, path_index)
            lo, hi = word % 256, word // 256
            for name, value in (("0196", lo), ("0197", hi)):
                data["initialData"][name] = value
                data["finalData"][name] = value
            data["events"][5]["value"] = word
            data["events"][5]["rawByteReads"] = [{"address": 0x196, "value": lo}, {"address": 0x197, "value": hi}]
            yield "invented-word-boundary-" + path + "-" + str(word), {"area": "permissions", "payload": data}
        # A retained additional diagnostic probe is not another instruction.
        fetch = oracle.make_fetch_case(path, path_index)
        raw = {"sequence": 1, "requestedPc": 0x1032, "offset": 50,
               "purpose": "DiagnosticProgramProbe", "opaqueIdentity": "InventedOpaqueCell-50"}
        fetch["events"][0]["rawProgramReads"].append(raw)
        ledger = []
        for event in fetch["events"]:
            for item in event["rawProgramReads"]:
                item["sequence"] = len(ledger) + 1
                ledger.append(deepcopy(item))
        fetch["rawProgramObservationLedger"] = ledger
        yield "extra-bounded-diagnostic-" + path, {"area": "fetchExit", "payload": fetch}
    yield "evidence-no-promotions", _case("evidence")


def negative_cases():
    """All expected first refusal codes are literal, frozen before comparison."""
    rows = []

    def add(category, label, group, request, code):
        rows.append({"category": MANDATORY_CATEGORIES[category - 1] if category else None,
                     "label": label, "group": group, "request": request, "code": code})

    case = _case("mapping", ("segment", "basePc16"), 0)
    case["payload"]["segment"]["endExclusive"] = 51
    add(1, "zero-based-relocated-segment", "semantic", case, "SegmentBinding:basePc16")
    add(2, "base-wrong-offset", "semantic", _case("mapping", ("claimedOffset",), 1), "ProgramOffsetSubtractionRelation")
    case = _case("mapping", ("requestedPc",), 0x1032)
    case["payload"]["claimedOffset"] = 49
    add(3, "last-byte-offset49", "semantic", case, "ProgramOffsetSubtractionRelation")
    add(4, "fetch-end-exclusive", "semantic", _case("mapping", ("requestedPc",), 0x1033), "ProgramOutOfRange")
    add(5, "fetch-notbelow-anchor", "semantic", _case("mapping", ("requestedPc",), 0x5596), "ProgramOutOfRange")
    add(6, "4096-padding", "semantic", _case("mapping", ("segment", "paddingBytes"), 4096), "SegmentBinding:paddingBytes")
    add(7, "original-rom-identity", "identity", _case("mapping", ("segment", "sourceIdentity"), "OriginalROM"), "SegmentBinding:sourceIdentity")
    add(8, "wrong-content-digest", "identity", _case("mapping", ("segment", "immutableContentDigest"), "0" * 64), "SegmentBinding:immutableContentDigest")
    case = _case("admission")
    case["payload"]["nodes"].pop()
    add(9, "missing-twentieth-node", "semantic", case, "AdmissionExactInventoryCount")
    add(10, "seventh-form-direct-j-object-substitution", "semantic", _case("admission", ("nodes", 15, "formId"), "job-j"), "AdmissionExactNodeRelation")
    add(11, "generic-j-mnemonic-fallback", "semantic", _case("admission", ("nodes", 15, "formId"), "J"), "AdmissionExactNodeRelation")
    add(12, "unknown-entry-dd", "semantic", _case("admission", ("entryDd",), None), "AdmissionDdDomain")
    case = _snapshot_case()
    case["payload"]["before"]["psw"] ^= 0x8000
    add(13, "wrong-initial-psw-carry-alias", "semantic", case, "SnapshotPswFlagAlias")
    add(14, "scb-disagrees-with-low3", "semantic", _replace(_snapshot_case(), ("before", "scb"), 7), "SnapshotOtherPswScbAlias")
    case = _snapshot_case()
    case["payload"]["before"]["pointingBanks"].pop()
    add(15, "missing-eighth-bank", "semantic", case, "SnapshotAllEightBanks")
    case = _snapshot_case()
    case["payload"]["after"]["pointingBanks"][7]["USP"] ^= 1
    add(16, "unselected-bank7-usp-clobber", "semantic", case, "PreservedContext:pointingBanks")
    case = _snapshot_case()
    case["payload"]["after"]["ah"] ^= 1
    case["payload"]["after"]["a"] = case["payload"]["after"]["al"] + 256 * case["payload"]["after"]["ah"]
    add(17, "coherent-ah-clobber", "semantic", case, "PreservedContext:ah")
    case = _snapshot_case()
    case["payload"]["after"]["ssp"] ^= 1
    add(18, "ssp-clobber", "semantic", case, "PreservedContext:ssp")
    add(19, "sf-defaulted-false", "semantic", _replace(_snapshot_case(), ("before", "sf"), False), "SnapshotUnknownSf")
    case = _snapshot_case(canonical=True)
    case["payload"]["before"]["otherPsw"] &= ~READS_ONE
    case["payload"]["before"]["psw"] = _psw_word(case["payload"]["before"])
    add(20, "canonical-reads-one-discarded", "semantic", case, "SnapshotPswNotRepresentable")
    case = _snapshot_case()
    case["payload"]["after"]["otherPsw"] |= READS_ONE
    case["payload"]["after"]["psw"] = _psw_word(case["payload"]["after"])
    add(21, "incompatible-input-silently-normalized", "semantic", case, "PreservedContext:otherPsw")
    add(22, "named-carry-in-other-psw", "semantic", _case("psw", ("otherPsw",), 0x8000), "OtherPswLow12Domain")
    case = _case("permissions", variant=1)
    case["payload"]["writePermissions"] = deepcopy(case["payload"]["readPermissions"])
    add(23, "read-set-grants-write", "semantic", case, "DataWritePermissionPolicyRelation")
    add(24, "write-readonly-word0196", "semantic", _case("permissions", ("events", 2, "address"), 0x196, 1), "DataOrderedAccessRelation")
    add(25, "read-retained-only0128", "semantic", _case("permissions", ("events", 0, "address"), 0x128, 1), "DataOrderedAccessRelation")
    add(26, "b-forbidden-second-gate-read", "semantic", _case("permissions", ("events", 10, "address"), 0x124, 1), "DataOrderedAccessRelation")
    add(27, "b-forbidden012a-write", "semantic", _case("permissions", ("events", 2, "address"), 0x12A, 1), "DataOrderedAccessRelation")
    add(27, "c-forbidden012a-write", "semantic", _case("permissions", ("events", 2, "address"), 0x12A, 2), "DataOrderedAccessRelation")
    case = _case("permissions", variant=1)
    case["payload"]["events"].pop(2)
    add(28, "same-value-store-deleted", "semantic", case, "DataExactEventCount")
    case = _case("permissions", variant=1)
    case["payload"]["finalLocalAliases"]["er"][0] ^= 256
    add(29, "r1-high-er0-alias-broken", "semantic", case, "DataLocalAliasRelation")
    case = _case("permissions", variant=1)
    case["payload"]["events"][5]["rawByteReads"].reverse()
    add(30, "word0196-high-before-low", "semantic", case, "DataRawReadOrderAndValues")
    add(31, "immediate00c0-is-data", "semantic", _case("permissions", ("events", 5, "address"), 0xC0, 1), "DataOrderedAccessRelation")
    add(32, "lookahead-counted-architectural", "semantic", _case("fetchExit", ("events", 0, "rawProgramReads", -1, "purpose"), "ArchitecturalSelectedFetch", 1), "FetchArchitecturalSelectedExtent")
    add(33, "selected-program-extent-missing", "semantic", _case("fetchExit", ("events", 0, "selectedExtent"), None, 1), "FetchSelectedExtent")
    add(34, "fetch-after-direct-j", "semantic", _case("fetchExit", ("postStopProgramReads",), [{"requestedPc": 0x5596}], 1), "FetchStopBeforeNextProbe")
    add(35, "direct-j-hidden-return", "semantic", _case("fetchExit", ("events", -1, "externalTransfer", "kind"), "Return", 1), "FetchDirectJTransfer")
    case = _case("fetchExit", variant=1)
    case["payload"]["events"].append(deepcopy(case["payload"]["events"][-1]))
    add(36, "two-direct-j-events", "semantic", case, "FetchExactExecutedCount")
    case = _case("fetchExit", variant=1)
    case["payload"]["events"].pop(0)
    add(37, "fabricated-complete-trace-with-missing-entry", "semantic", case, "FetchExactExecutedCount")
    add(38, "rust-adapter-promoted", "authority", _case("evidence", ("rustAdapterImplementation",), "Pass"), "EvidenceAuthorityRefusal")
    add(39, "firmware-ready-promoted", "authority", _case("evidence", ("firmwareReady",), True), "EvidenceAuthorityRefusal")

    # Additional structural relations and authority checks, distinct requests.
    for pc in (0xFFF, 0x55C5, -1, 65536, True):
        code = "ProgramPcDomain" if type(pc) is not int or pc < 0 or pc > 65535 else "ProgramOutOfRange"
        add(0, "extra-program-boundary-" + str(pc), "semantic", _case("mapping", ("requestedPc",), pc), code)
    for field, value, code in (("basePc16", 65530, "SegmentOverflowOrLength"),
                               ("endExclusive", 0x1032, "SegmentEndRelation"),
                               ("exactLength", 0, "SegmentOverflowOrLength"),
                               ("overlappingSegments", [{"base": 0x1000, "end": 0x1001}], "SegmentBinding:overlappingSegments")):
        add(0, "extra-segment-" + field, "semantic", _case("mapping", ("segment", field), value), code)
    for replacement in ("sj-rel8", "cal-address", "rt", "j"):
        add(0, "direct-j-not-" + replacement, "semantic", _case("admission", ("nodes", 15, "formId"), replacement), "AdmissionExactNodeRelation")
    for index in range(20):
        case = _case("admission")
        operands = case["payload"]["nodes"][index]["typedOperands"]
        if "value" in operands[-1]:
            operands[-1]["value"] += 1
        else:
            operands[-1]["kind"] = "AccumulatorAH_NotAccumulatorA"
        add(0, "typed-operand-at-node-" + str(index), "semantic", case, "AdmissionExactNodeRelation")
    for index, register in ((bank, reg) for bank in range(8) for reg in ("X1", "X2", "DP", "USP")):
        case = _snapshot_case(variant=3)
        case["payload"]["after"]["pointingBanks"][index][register] ^= 1
        add(0, "bank-clobber-" + str(index) + "-" + register, "semantic", case, "PreservedContext:pointingBanks")
    for flag, bit in FLAG_BITS:
        if flag == "cf":
            continue  # Covered by mandatory named-carry-in-other-psw.
        add(0, "named-" + flag + "-in-other-psw", "semantic", _case("psw", ("otherPsw",), 1 << bit), "OtherPswLow12Domain")
    add(0, "write-set-grants-read", "semantic", _case("permissions", ("readPermissions",), oracle.make_data_case("B", 1)["writePermissions"], 1), "DataReadPermissionPolicyRelation")
    for field, address, code in (("writePermissions", 0x196, "DataWritePermissionPolicyRelation"),
                                 ("readPermissions", 0x124, "DataReadPermissionPolicyRelation")):
        case = _case("permissions", variant=1)
        case["payload"][field] = sorted(case["payload"][field] + [address])
        add(0, "expanded-" + field, "semantic", case, code)
    for label, field, value, code in (("bad-word-alignment", "address", 0x197, "DataOrderedAccessRelation"),
                                     ("wrong-le-weight", "value", 1, "DataLittleEndianReadRelation")):
        add(0, label, "semantic", _case("permissions", ("events", 5, field), value, 1), code)
    add(0, "seed-read-in-functional-journal", "authority", _case("permissions", ("events", 0, "classification"), "SeedInitializationAccess", 1), "DataFunctionalCategory")
    add(0, "diagnostic-read-in-functional-journal", "authority", _case("permissions", ("events", 0, "classification"), "DiagnosticSnapshotRead", 1), "DataFunctionalCategory")
    add(0, "same-value-tag-erased", "semantic", _case("permissions", ("events", 2, "sameValue"), False, 1), "DataSameValueIdentity")
    add(0, "fresh-write-ordinal-reused", "semantic", _case("permissions", ("events", 2, "writeOrdinal"), 0, 1), "DataFreshStoreOrdinal")
    case = _case("permissions", variant=1)
    case["payload"]["events"][7]["value"] ^= 1
    add(0, "r1-source-copy-is-not-independent-variable", "semantic", case, "DataR1CopyRelation")
    add(0, "wrong-reviewed-branch", "semantic", _case("fetchExit", ("events", 6, "nextPc"), 0x102A, 1), "FetchReviewedPathSuccessor")
    add(0, "entry-directly-at-exit", "semantic", _case("fetchExit", ("entryPc",), 0x5596, 1), "FetchEntryPc")
    add(0, "premature-stop-before-j", "semantic", _case("fetchExit", ("stop", "afterStep"), 12, 1), "FetchExitStopIdentity")
    add(0, "external-target-used-as-decoder-probe", "semantic", _case("fetchExit", ("events", -1, "rawProgramReads", -1, "requestedPc"), 0x5596, 1), "ProgramOutOfRange")
    add(0, "raw-lookahead-ledger-omission", "semantic", _case("fetchExit", ("rawProgramObservationLedger",), [], 1), "FetchCompleteRawObservationLedger")
    add(0, "raw-read-offset-corrupted", "semantic", _case("fetchExit", ("events", 0, "rawProgramReads", 0, "offset"), 1, 1), "FetchRawTranslationAndOrder")
    add(0, "raw-probe-order-corrupted", "semantic", _case("fetchExit", ("events", 0, "rawProgramReads", 0, "sequence"), 2, 1), "FetchRawTranslationAndOrder")
    add(0, "cpu-trace-authority-label", "authority", _case("fetchExit", ("events", 0, "decodedInstruction", "classification"), "ActualCPUTrace", 1), "FetchDecodedIdentity")
    add(0, "actual-cpu-evidence-promotion", "authority", _case("evidence", ("evidenceLevel",), "FutureSyntheticCPUExecution"), "EvidenceAuthorityRefusal")
    add(0, "synthetic-cpu-count-promotion", "authority", _case("evidence", ("syntheticCpuExecutionCount",), 1), "EvidenceAuthorityRefusal")
    add(0, "firmware-object-promotion", "authority", _case("evidence", ("targetObjectCount",), 1), "EvidenceAuthorityRefusal")
    add(0, "wrong-admission-source-identity", "identity", _case("admission", ("sourceIdentity",), "OriginalROM"), "AdmissionSourceIdentity")
    add(0, "wrong-admission-content-digest", "identity", _case("admission", ("immutableContentDigest",), "f" * 64), "AdmissionContentDigest")
    add(0, "modified-primary-row-pin", "identity", _case("admission", ("nodes", 0, "primaryPatternEvidence", "manualSha256"), "0" * 64), "AdmissionExactNodeRelation")
    add(0, "modified-opaque-cell-identity", "identity", _case("mapping", ("segment", "opaqueContent", 0), "OriginalRomCell"), "SegmentBinding:opaqueContent")
    add(0, "boolean-not-dd-integer", "semantic", _case("admission", ("entryDd",), True), "AdmissionDdDomain")
    add(0, "boolean-not-other-psw", "semantic", _case("psw", ("otherPsw",), True), "OtherPswLow12Domain")
    add(0, "unknown-snapshot-field", "semantic", _replace(_snapshot_case(), ("before", "assumedAbi"), "Invented"), "SnapshotSchema")
    return rows


def _expect_refusal(function, request, code, label):
    before = _canonical(request)
    observed_code = None
    for attempt in range(2):
        try:
            function(request)
        except ValueError as error:
            actual_code = str(error)
            _require(bool(actual_code) and len(actual_code) <= 256, "EmptyOrUnboundedRefusalCode:" + label)
            if code is not None:
                _require(actual_code == code, "WrongReferenceFirstRefusal:" + label +
                         ":expected=" + code + ":actual=" + actual_code)
            if observed_code is not None:
                _require(actual_code == observed_code, "NondeterministicRefusal:" + label)
            observed_code = actual_code
        else:
            raise AssertionError("MutationAccepted:" + label + ":attempt=" + str(attempt))
        _require(_canonical(request) == before, "RefusalMutatedInput:" + label)
    return observed_code


def _boundary_proof(function, reference_codes=True):
    cycle = []
    cycle.append(cycle)
    deep = 0
    for _ in range(50):
        deep = [deep]
    cases = (((1, 2), "JsonPrimitiveType"), (0.5, "JsonPrimitiveType"),
             ({1: "nonstring-key"}, "JsonObjectKeyType"), (cycle, "JsonCycle"),
             (deep, "JsonDepthOrNodeLimit"))
    for index, (request, code) in enumerate(cases):
        observed_code = None
        for _ in range(2):
            try:
                function(request)
            except ValueError as error:
                actual_code = str(error)
                _require(bool(actual_code) and len(actual_code) <= 256, "BoundaryEmptyCode:" + str(index))
                if reference_codes:
                    _require(actual_code == code, "BoundaryWrongReferenceRefusal:" + str(index))
                if observed_code is not None:
                    _require(actual_code == observed_code, "BoundaryNondeterministicRefusal:" + str(index))
                observed_code = actual_code
            else:
                raise AssertionError("BoundaryAccepted:" + str(index))
    _require(cycle[0] is cycle and len(cycle) == 1, "BoundaryCycleMutated")
    return len(cases)


def _exercise(analyze=None):
    """Prepare independently first; analyzer is only a later optional subject."""
    positive_counts = {area: 0 for area in AREAS}
    aggregate, psw_digest = sha256(), sha256()
    analyzer_calls, positive_count = 0, 0
    paths, scb, dd_contexts, node_ids, forms = set(), set(), set(), set(), set()

    def positive(label, request, manual=None):
        nonlocal analyzer_calls, positive_count
        before = _canonical(request)
        expected = oracle.reference_case(request)
        _require(_canonical(request) == before, "OraclePositiveMutatedInput:" + label)
        if manual is not None:
            _equal(expected, manual, "ManualExpected:" + label)
        if analyze is not None:
            actual = analyze(request)
            analyzer_calls += 1
            _equal(actual, expected, label)
            _require(_canonical(request) == before, "AnalyzerPositiveMutatedInput:" + label)
        aggregate.update(_canonical(expected).encode("ascii"))
        positive_counts[request["area"]] += 1
        positive_count += 1
        return expected

    for label, request in _positive_cases():
        area = request["area"]
        result = positive(label, request)
        payload = request["payload"]
        if area == "mapping":
            offset = payload["requestedPc"] - 0x1000
            _equal(result, {"classification": "SyntheticSegmentAddressTranslationModelVerified",
                   "requestedPc": 0x1000 + offset, "offset": offset,
                   "opaqueIdentity": "InventedOpaqueCell-" + str(offset), "contentDigestMeasured": False,
                   "paddingBytes": 0, "rustSegmentMapping": "NotImplemented",
                   "evidenceKind": "IndependentSyntheticAdapterModel"}, "ManualFullMapping")
        elif area == "admission":
            _check_manual_inventory(payload["nodes"])
            node_ids.update(node["nodeIdentity"] for node in payload["nodes"])
            forms.update(node["formId"] for node in payload["nodes"])
        elif area == "snapshot":
            _check_manual_snapshot(request, result)
            scb.add(payload["before"]["scb"])
            dd_contexts.add(payload["before"]["dd"])
        elif area == "permissions":
            _check_manual_data(request, result)
            paths.add(payload["path"])
        elif area == "fetchExit":
            _check_manual_fetch(request, result)
            paths.add(payload["path"])
            dd_contexts.add(payload["events"][0]["incomingDd"])

    compatible = incompatible = 0
    for other in range(4096):
        compatible += int((other & 0x0CC8) == 0x0CC8)
        incompatible += int((other & 0x0CC8) != 0x0CC8)
        for flag_value in range(16):
            flags = {name: (flag_value >> index) & 1 for index, (name, _) in enumerate(FLAG_BITS)}
            request = {"area": "psw", "payload": {"otherPsw": other, "namedFlags": flags}}
            expected = _manual_psw(other, flags)
            positive("psw-" + str((other, flag_value)), request, expected)
            psw_digest.update(_canonical(expected).encode("ascii"))
    _require((compatible, incompatible) == (128, 3968), "LiteralPswDomainCounts")
    _require(psw_digest.hexdigest() == PSW_RECORD_DIGEST, "SealedFullPswRecordDigest")

    negative_rows, request_hashes, labels, categories, receipts = negative_cases(), set(), set(), set(), []
    negative_counts = {"semantic": 0, "identity": 0, "authority": 0}
    for row in negative_rows:
        request_hash = _digest(row["request"])
        _require(request_hash not in request_hashes and row["label"] not in labels, "DuplicateNegativeInputOrLabel:" + row["label"])
        request_hashes.add(request_hash)
        labels.add(row["label"])
        _expect_refusal(oracle.reference_case, row["request"], row["code"], "Oracle:" + row["label"])
        analyzer_code = "NotCompared"
        if analyze is not None:
            # Refusal text is deliberately not shared across implementations.
            # The relation inputs and reference first causes were frozen before
            # comparison; all semantic mutants retain the accepted authority
            # metadata. Stable ValueError + the unchanged minimal pair proves
            # rejection, not an undocumented common error-message vocabulary.
            analyzer_code = _expect_refusal(analyze, row["request"], None, "Analyzer:" + row["label"])
            analyzer_calls += 2
        negative_counts[row["group"]] += 1
        if row["category"] is not None:
            categories.add(row["category"])
        receipts.append({key: row[key] for key in ("category", "label", "group", "code")})
        receipts[-1]["requestSha256"] = request_hash
        receipts[-1]["analyzerCode"] = analyzer_code
    boundary_count = _boundary_proof(oracle.reference_case)
    if analyze is not None:
        _require(_boundary_proof(analyze, reference_codes=False) == boundary_count, "BoundaryCountMismatch")
        analyzer_calls += boundary_count * 2
    _equal(sorted(categories), sorted(MANDATORY_CATEGORIES), "All39MandatoryCategories")
    _equal(sorted(paths), ["A", "B", "C", "D"], "AllFourPaths")
    _equal(sorted(scb), list(range(8)), "AllEightScb")
    _equal(sorted(dd_contexts), [0, 1], "BothIncomingDd")
    _require(len(node_ids) == 20 and len(forms) == 16, "All20Nodes16Forms")
    _require(all(value > 0 for value in positive_counts.values()), "NonvacuousAllAreas")
    return {
        "classification": "IndependentAdapterTestsPreparedBeforeAnalyzerComparison" if analyze is None
        else "IndependentSyntheticAdapterFeasibilityTestsPass",
        "passed": True, "failed": 0, "skipped": 0,
        "comparisonTarget": "FrozenOracleAndManualFactsOnly" if analyze is None else "AnalyzerVsFrozenOracleAndManualFacts",
        "wholeExpectedCaseEquality": positive_count,
        "positiveCasesByArea": positive_counts, "positiveAreas": sorted(positive_counts),
        "pswFullRecordComparisons": positive_counts["psw"], "pswRecordDigest": psw_digest.hexdigest(),
        "pswRepresentableLow12": compatible, "pswIncompatibleLow12": incompatible,
        "pswRepresentableCartesian": compatible * 16, "pswIncompatibleCartesian": incompatible * 16,
        "semanticNegativeCases": negative_counts["semantic"], "identityNegativeCases": negative_counts["identity"],
        "authorityNegativeCases": negative_counts["authority"], "jsonBoundaryRefusals": boundary_count,
        "uniqueNegativeInputs": len(request_hashes), "negativeCases": len(negative_rows),
        "negativeInputDigest": _digest(sorted(request_hashes)), "negativeReceipts": receipts,
        "mandatoryCategoryCount": len(categories), "mandatoryCategoryCoverage": list(MANDATORY_CATEGORIES),
        "pathCoverage": sorted(paths), "allScb": sorted(scb), "incomingDD": sorted(dd_contexts),
        "nodeCoverage": len(node_ids), "formCoverage": len(forms),
        "positiveExpectedDigest": aggregate.hexdigest(), "oracleSourceSha256": ORACLE_SOURCE_SHA256,
        "analyzerCalls": analyzer_calls, "cpuExecutions": 0, "originalRomExecutions": 0,
        "programPayloadBytes": 0, "rustExpectedStatesUsed": 0, "upstreamOracleDomainChanged": False,
        "rustAdapterImplementation": "NotRun", "runtimeExitIsolation": "NotEstablished", "firmwareReady": False,
        "refusalAccounting": "Unique JSON-native requests; oracle first-cause codes are literal; each implementation must refuse deterministically twice without mutation but may use its own code vocabulary; non-JSON boundaries are separate; identity/authority labels are never semantic relation cases",
        "fabricatedTraceAccounting": "Mandatory trace-fabrication relation removes the required entry instruction; a separate authority-only case rejects an ActualCPUTrace label. Neither is an observed CPU trace",
    }


def oracle_only_proof():
    """Seal preparation without importing, reading, or calling the analyzer."""
    return _exercise()


def run_tests():
    # Deliberately lazy: no analyzer can influence the earlier preparation seal.
    from synthetic_adapter_feasibility_analysis import analyze_case
    return _exercise(analyze_case)


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["--oracle-only"]:
        summary = oracle_only_proof()
    elif not sys.argv[1:]:
        summary = run_tests()
    else:
        raise SystemExit("Only the fixed --oracle-only preparation mode is supported")
    print("M2BL_TESTS_JSON=" + json.dumps(summary, sort_keys=True, separators=(",", ":")))
