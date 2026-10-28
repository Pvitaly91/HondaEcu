"""Independent, invented-only source-consistency oracle for M2ce.

Authored from accepted M2aq/M2ap/M2ar/M2as/M2cd contracts and complete
primary page review before reading the new M2ce analysis implementations.
This is a finite relation checker, never a CPU, execution log or admission.
"""

from copy import deepcopy


REASONS = (
    "ResetVectorIsNotActualResetEvent", "ResetCauseColdSourceMismatch",
    "WdtCommandSafetyUnknown", "WriteOnlyWdtReadbackInvented",
    "DataProgramSourceConfusion", "NumericNoninterferenceDoesNotDischargeBus",
    "ForcedP4NativeOutcome", "PulseSampleOrderMismatch", "PulseSampleTokenReused",
    "RetirementRankIsNotMilliseconds", "StalePendingBeforeClear", "WrongIrqFactor",
    "HostPendingRejected", "WrongSspSource", "WrongScb", "WrongLrb", "WrongX1",
    "WrongEffectiveAddress", "WrongReturnPc", "StaleCanaryNotCurrentCalFrame",
    "MissingFirstExchange", "MissingRestoreExchange", "StorageGenerationNotFresh",
    "WrongSemanticCreator", "CrossMachineFrame", "TechnicalSspImport",
    "IgnoredControlEffects", "LogicalPswFlagsUnknown", "WrongCmpFlags",
    "FaultBranchAccepted", "RtiIsNotRt", "HostSelectedRtEntry", "HostSspRepair",
    "ActualObservationFabricated", "UnknownMemoryApplicability",
    "HistoricalFingerprintRewritten", "SourceGuardSelfApproval",
    "PrecalReadBorrowedFutureFrame",
)


def reviewed_case():
    """A correlated invented hypothesis; None is deliberately not favorable."""
    return {
        "root": {"cause": "ExternalRes", "vectorAddress": 0, "vectorTarget": 0x24ED,
                 "actualResetClaim": False, "coldSourcesRetained": True},
        "wdt": {"hardwareSafe": None, "readback": None},
        "external": {"space": "DATA", "address": 0x4700, "numericIndependent": True,
                     "readCompletion": None, "sideEffects": None},
        "earlyP4": {"value": 0, "origin": "InventedOnly", "forcedNative": False},
        "pulses": {"samples": [
            {"selector": selector, "phase": phase, "level": level,
             "readerPC": (0x2629, 0x2634, 0x263F)[phase],
             "sequence": index + 1, "token": f"invented-sample-{index + 1}",
             "origin": "InventedOnly"}
            for index, (selector, phase, level) in enumerate(
                (s, p, b) for s in (2, 3) for p, b in enumerate((0, 1, 0)))],
                   "physicalMilliseconds": None},
        "irq": {"clearPC": 0x261E, "readerPC": 0x264B, "branchPC": 0x264E,
                "wordBit": 13, "highBit": 5, "factor": "PWM1Overflow",
                "clearSequence": 1, "ownerSequence": 2, "readerSequence": 3,
                "origin": "InventedOnly"},
        "context": {"sspSourcePC": 0x24F8, "ssp": 0x047E, "scb": 0, "lrb": 0x0040,
                    "x1": 0x03FA, "effectiveAddress": 0x047E,
                    "history": "invented-one-history",
                    "bindings": ["invented-one-history"] * 6, "technicalImport": False},
        "precal": {"readerPC": 0x2682, "readToken": "old047E", "value": None,
                   "dpToken": "old047E", "futureFrameSubstitution": False},
        "frame": {"callPC": 0x2689, "targetPC": 0x5C5C, "returnPC": 0x268C,
                  "creator": "CAL2689/first", "staleCanary": False,
                  "exchangePCs": [0x5C68, 0x5C6C],
                  "generationTokens": ["frameA", "frameB", "frameC"],
                  "restoredCreator": "CAL2689/first", "savedAccumulatorToken": "frameA",
                  "readerToken": "frameC", "history": "invented-one-history"},
        "flags": {"producerPC": 0x5C7C, "cf": False, "zf": True, "hc": None,
                  "dd": True, "logicalFlagsKnown": False, "jneNextPC": 0x5C80},
        "rt": {"form": "RT", "pc": 0x5C80, "entrySource": "ReachedByJne",
               "sspManuallyRepaired": False, "stopBeforePC": 0x268C},
        "controls": {"ignored": False, "savedIEWriterPC": 0x2569,
                     "savedIEZeroProducerPC": 0x2566},
        "actual": {"cpuExecutions": 0, "romExecutions": 0, "machineId": None,
                   "instructionIndex": None, "writeOrdinal": None},
        "memory": {"actualDevice": "Unknown", "assumedInternal": False},
        "preservation": {"historicalExpected": "invented-old-sha",
                         "recordedExpected": "invented-old-sha"},
        "approval": {"author": "invented-author", "approver": "invented-independent-reviewer",
                     "approvedIdentity": "invented-source-sha", "sourceIdentity": "invented-source-sha"},
    }


def _outcome(reason):
    return {"valid": reason is None, "firstMissingObligation": reason,
            "conditionalTerminalPC": 0x268C if reason is None else None,
            "classification": "InventedOnly_ConditionalObligationsMatch" if reason is None else "InventedOnly_Refused",
            "actualCpuExecutions": 0, "actualRomExecutions": 0,
            "actualMachineId": None, "actualInstructionIndex": None,
            "actualWriteOrdinal": None, "runtimeAdmission": "Blocked", "firmwareReady": False}


def validate_integrated_case(case):
    """Reject relational contradictions; no supplied hypothesis grants runtime."""
    r, w, e = case["root"], case["wdt"], case["external"]
    p, q, c = case["pulses"], case["irq"], case["context"]
    f, flags, ret = case["frame"], case["flags"], case["rt"]
    samples = p["samples"]
    expected_samples = [(s, phase, bit, reader, i + 1)
                        for i, (s, phase, bit, reader) in enumerate(
                            (s, phase, bit, reader) for s in (2, 3)
                            for phase, (bit, reader) in enumerate(zip((0, 1, 0), (0x2629, 0x2634, 0x263F))))]
    actual_samples = [(x["selector"], x["phase"], x["level"], x["readerPC"], x["sequence"]) for x in samples]
    generations = f["generationTokens"]
    actual = case["actual"]
    checks = (
        r["actualResetClaim"] is not False,
        (r["cause"], r["vectorAddress"], r["vectorTarget"], r["coldSourcesRetained"]) != ("ExternalRes", 0, 0x24ED, True),
        w["hardwareSafe"] is not None,
        w["readback"] is not None,
        (e["space"], e["address"]) != ("DATA", 0x4700),
        e["numericIndependent"] is not True or e["readCompletion"] is not None or e["sideEffects"] is not None,
        case["earlyP4"] != {"value": 0, "origin": "InventedOnly", "forcedNative": False},
        actual_samples != expected_samples or any(x["origin"] != "InventedOnly" for x in samples),
        len({x["token"] for x in samples}) != len(samples),
        p["physicalMilliseconds"] is not None,
        not q["clearSequence"] < q["ownerSequence"] < q["readerSequence"],
        (q["clearPC"], q["readerPC"], q["branchPC"], q["wordBit"], q["highBit"], q["factor"]) != (0x261E, 0x264B, 0x264E, 13, 5, "PWM1Overflow"),
        q["origin"] != "InventedOnly",
        (c["sspSourcePC"], c["ssp"]) != (0x24F8, 0x047E),
        c["scb"] != 0,
        c["lrb"] != 0x0040,
        c["x1"] != 0x03FA,
        c["effectiveAddress"] != ((0x0084 + c["x1"]) & 0xFFFE),
        (f["callPC"], f["targetPC"], f["returnPC"]) != (0x2689, 0x5C5C, 0x2689 + 3),
        f["staleCanary"] is not False,
        0x5C68 not in f["exchangePCs"],
        0x5C6C not in f["exchangePCs"],
        len(generations) != 3 or len(set(generations)) != 3 or f["exchangePCs"] != [0x5C68, 0x5C6C],
        f["creator"] != "CAL2689/first" or f["restoredCreator"] != f["creator"] or f["savedAccumulatorToken"] != generations[0] or f["readerToken"] != generations[-1],
        f["history"] != c["history"] or any(x != c["history"] for x in c["bindings"]),
        c["technicalImport"] is not False,
        case["controls"] != {"ignored": False, "savedIEWriterPC": 0x2569, "savedIEZeroProducerPC": 0x2566},
        flags["logicalFlagsKnown"] is not False or flags["hc"] is not None,
        (flags["producerPC"], flags["cf"], flags["zf"], flags["dd"]) != (0x5C7C, False, True, True),
        flags["jneNextPC"] != 0x5C80,
        (ret["form"], ret["pc"]) != ("RT", 0x5C80),
        ret["entrySource"] != "ReachedByJne",
        ret["sspManuallyRepaired"] is not False,
        actual != {"cpuExecutions": 0, "romExecutions": 0, "machineId": None, "instructionIndex": None, "writeOrdinal": None},
        case["memory"] != {"actualDevice": "Unknown", "assumedInternal": False},
        case["preservation"]["historicalExpected"] != case["preservation"]["recordedExpected"],
        case["approval"]["author"] == case["approval"]["approver"] or case["approval"]["approvedIdentity"] != case["approval"]["sourceIdentity"],
        case["precal"] != {"readerPC": 0x2682, "readToken": "old047E", "value": None, "dpToken": "old047E", "futureFrameSubstitution": False} or ret["stopBeforePC"] != 0x268C,
    )
    return _outcome(next((name for name, violated in zip(REASONS, checks) if violated), None))


def curated_inputs():
    """One correlated control plus one content mutation for each named relation."""
    edits = (
        ("root", "actualResetClaim", True), ("root", "cause", "Brk"),
        ("wdt", "hardwareSafe", True), ("wdt", "readback", 0),
        ("external", "space", "PROGRAM"), ("external", "readCompletion", True),
        ("earlyP4", "forcedNative", True), ("pulses", "samples", "REORDER"),
        ("pulses", "samples", "REUSE"), ("pulses", "physicalMilliseconds", 375),
        ("irq", "ownerSequence", 0), ("irq", "wordBit", 12),
        ("irq", "origin", "HostSeed"), ("context", "sspSourcePC", 0x27D0),
        ("context", "scb", 2), ("context", "lrb", 0x0041),
        ("context", "x1", 0x03F8), ("context", "effectiveAddress", 0x047C),
        ("frame", "returnPC", 0x2690), ("frame", "staleCanary", True),
        ("frame", "exchangePCs", [0x5C6C]), ("frame", "exchangePCs", [0x5C68]),
        ("frame", "generationTokens", ["frameA", "frameB", "frameA"]),
        ("frame", "restoredCreator", "CAL268D/second"),
        ("frame", "history", "invented-other-machine"), ("context", "technicalImport", True),
        ("controls", "ignored", True), ("flags", "logicalFlagsKnown", True),
        ("flags", "zf", False), ("flags", "jneNextPC", 0x5C81),
        ("rt", "form", "RTI"), ("rt", "entrySource", "HostPcAssignment"),
        ("rt", "sspManuallyRepaired", True), ("actual", "instructionIndex", 20),
        ("memory", "assumedInternal", True), ("preservation", "recordedExpected", "invented-rewritten-sha"),
        ("approval", "approver", "invented-author"), ("precal", "value", 0x268C),
    )
    rows = [{"caseId": "conditional-correlated-control", "category": None, "input": reviewed_case()}]
    for reason, (section, key, value) in zip(REASONS, edits):
        case = reviewed_case()
        if value == "REORDER":
            case[section][key][0], case[section][key][1] = case[section][key][1], case[section][key][0]
        elif value == "REUSE":
            case[section][key][2]["token"] = case[section][key][0]["token"]
        else:
            case[section][key] = deepcopy(value)
        rows.append({"caseId": reason, "category": reason, "input": case})
    return rows


def curated_controls():
    """Return inputs, not canned expected outputs, for an independent analyzer."""
    return curated_inputs()


def _equal(actual, expected, path):
    if actual != expected:
        raise ValueError(f"IndependentOracleMismatch:{path}")


def _actual_fields_unknown(value, path="analysis"):
    if isinstance(value, dict):
        for key, child in value.items():
            here = f"{path}.{key}"
            if key in {"actualMachineId", "actualInstructionIndex", "actualNativeWriteOrdinal", "machineId", "writeOrdinal", "nativeWriteOrdinal", "readerObservation", "factorOwner"}:
                _equal(child, None, here)
            if key in {"actualCpuExecutions", "actualRomExecutions", "cpuExecutions", "romExecutions", "originalRomExecutions"}:
                _equal(child, 0, here)
            if key in {"actualFactorObserved", "actualNativeContextEstablished", "firmwareReady"}:
                _equal(child, False, here)
            _actual_fields_unknown(child, here)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _actual_fields_unknown(child, f"{path}[{index}]")


def independent_check(gates, frame):
    """Check projected source obligations independently, without running code."""
    _actual_fields_unknown(gates, "gates")
    _actual_fields_unknown(frame, "frame")
    config = gates["nativeConfiguration"]
    _equal((config["p4io0D"], config["p4sfFC"]), (0x0D, 0xFC), "port-multiplex")
    for name, command, enabled in (("pwm0", 0x3E, False), ("pwm1", 0x7E, True)):
        pwm = config[name]
        _equal(pwm["command"], command, name + ".command")
        _equal(pwm["overflowRequestEnabled"], bool(command & 0x40), name + ".erq-bit6")
        _equal(pwm["overflowRequestEnabled"], enabled, name + ".enabled")
        _equal((pwm["clockSelect"], pwm["widthBits"], pwm["mode"], pwm["run"], pwm["lowActive"]),
               (command & 3, 12, "PWM", bool(command & 0x10), bool(command & 0x20)), name + ".configuration")
        _equal(pwm["statusBit7WrittenValueIsObservedOverflow"], False, name + ".command-is-not-overflow-observation")
    _equal(gates["pulseReads"]["selectedBits"], [2, 3], "pulse-selectors")
    _equal(gates["pulseReads"]["readerSourceByBit"], {"2": "PWM0OutputData", "3": "PWM1OutputData"}, "ordinary-port-read-source")
    _equal([(r["counterSetupPC"], r["rank"], r["decPC"], r["zeroBranchPC"], r["readerPC"], r["branchPC"], r["requiredBit"]) for r in gates["pulseReads"]["phases"]],
           [(0x2623, 0x177, 0x2626, 0x2627, 0x2629, 0x262C, 0),
            (0x262E, 0x177, 0x2631, 0x2632, 0x2634, 0x2637, 1),
            (0x2639, 0x0B2, 0x263C, 0x263D, 0x263F, 0x2642, 0)], "pulse-counter-source-relations")
    _equal((gates["pulseReads"]["ordinaryReadNoFunctionalPortWrite"], gates["pulseReads"]["readModifyWriteReadsPinInstead"]), (True, True), "ordinary-vs-rmw")
    _equal(gates["pulseReads"]["physicalMillisecondsFromRank"], None, "no-physical-time-conversion")
    _equal(gates["earlyP4Gate"]["readerPC"], 0x2528, "early-port-reader")
    _equal((gates["earlyP4Gate"]["selectedBit"], gates["earlyP4Gate"]["requiredBit"]), (1, 0), "early-port-condition")
    irq = gates["freshIrq"]
    _equal((irq["clearPC"], irq["readerPC"], irq["branchPC"]), (0x261E, 0x264B, 0x264E), "clear-reader-branch")
    _equal((irq["selectedWordBit"], irq["selectedHighBit"]), (13, 5), "pwm-factor-bit")
    _equal(irq["enabledStandardFactorSource"], "PWM1OverflowOnly", "pwm-source-refinement")
    _equal(irq["disabledSource"], "PWM0", "pwm0-request-disabled")
    _equal((irq["zfIfOldBitOne"], irq["acknowledgedSelectedBit"], irq["success"], irq["fault"]), (0, 0, 0x2655, 0x2650), "irq-oldbit-branch")
    context = frame["context"]
    _equal((context["lrb"], context["scb"], context["x1"]), (0x40, 0, 0x03FA), "entry-context")
    _equal((context["pageBase"], context["localBase"]), (((0x40 & 0x1FE0) << 3) & 0xFFFF, (0x40 << 3) & 0xFFFF), "lrb-geometry")
    inventory = frame["instructionInventory"]
    _equal([row["pc"] for row in inventory], [0x267C, 0x267F, 0x2682, 0x2686, 0x2689, 0x5C5C, 0x5C5D, 0x5C60, 0x5C65, 0x5C68, 0x5C6C, 0x5C70, 0x5C71, 0x5C74, 0x5C76, 0x5C78, 0x5C7B, 0x5C7C, 0x5C7E, 0x5C80], "first-contract-pcs")
    _equal([row["length"] for row in inventory], [3, 3, 4, 3, 3, 1, 3, 5, 3, 4, 4, 1, 3, 2, 2, 3, 1, 2, 2, 1], "first-contract-lengths")
    _equal([row["form"] for row in inventory], [
        "MOV LRB, #N16", "MOV X1, #N16", "MOV DP, N16[X1]", "L A, #N16", "CAL addr16",
        "MOV X2, A", "SB off N8.7", "AND N8, #N16", "ANDB PSWH, #N8",
        "XCHG A, N16[X1]", "XCHG A, N16[X1]", "ST A, er3", "ORB PSWH, #N8",
        "L A, N8", "ST A, N8", "RB off N8.7", "L A, er3", "CMP A, X2", "JNE rel8", "RT"], "first-contract-forms")
    terminal = frame["terminalProjection"]
    for name, value in {"pc": 0x268C, "ssp": 0x047E, "a": 0x5555, "dd": 1, "cf": 0, "zf": 1, "hc": None, "mie": 1, "scb": 0, "lrb": 0x40, "wholeStateIndependentOfPriorWord": False}.items():
        _equal(terminal[name], value, "terminal." + name)
    _equal(frame["sourceCuts"]["priorWord"]["readPc"], 0x2682, "old-word-reader")
    _equal(frame["sourceCuts"]["priorWord"]["readAddress"], (0x84 + 0x03FA) & 0xFFFE, "old-word-address")
    _equal(frame["sourceCuts"]["priorWord"]["numericIndependenceRemovesReadAuthority"], False, "read-authority")
    _equal(frame["sourceCuts"]["savedIe"]["controlEffectsDischargedByAccumulatorKill"], False, "control-authority")
    _equal(frame["sourceCuts"]["savedIe"]["sourceWriterPc"], 0x2569, "saved-ie-generation")
    _equal(frame["sourceCuts"]["savedIe"]["loadPc"], 0x5C74, "saved-ie-reader")
    _equal(frame["sourceCuts"]["savedIe"]["accumulatorKillPc"], 0x5C7B, "saved-ie-numeric-projection-kill")
    chronology = frame["symbolicChronology"]
    _equal([(r["pc"], r["action"], r["address"], r["widthBits"], r["value"]) for r in chronology], [
        (0x2682, "ReadOldWordIntoDP", 0x047E, 16, None),
        (0x2689, "ConditionalFrameStore", 0x047E, 16, 0x2689 + 3),
        (0x2689, "ConditionalSspDecrement", 0x0000, 16, (0x047E - 2) & 0xFFFF),
        (0x5C5C, "ConditionalPatternStore", 0x0082, 16, 0x5555),
        (0x5C68, "ExchangeTemporaryFrameStore", 0x047E, 16, 0x5555),
        (0x5C68, "ExchangeSavesCurrentFrameInA", 0x0006, 16, 0x268C),
        (0x5C6C, "ExchangeFreshFrameRestoration", 0x047E, 16, 0x268C),
        (0x5C6C, "ExchangeRecoversPatternInA", 0x0006, 16, 0x5555),
        (0x5C70, "ConditionalLocalStore", 0x0206, 16, 0x5555),
        (0x5C7B, "ConditionalAccumulatorReload", 0x0006, 16, 0x5555),
        (0x5C80, "ConditionalRead_NotWriteGeneration", 0x047E, 16, 0x268C)], "chronology")
    old, cal, _, _, temporary, saved, restored, *_ = chronology
    reader = chronology[-1]
    _equal(len({cal["outputToken"], temporary["outputToken"], restored["outputToken"]}), 3, "distinct-frame-storage-generations")
    _equal(saved["sourceToken"], cal["outputToken"], "saved-current-cal-word")
    _equal(restored["sourceToken"], saved["outputToken"], "restore-from-saved-register-token")
    _equal(restored["previousToken"], temporary["outputToken"], "restore-replaces-temporary")
    _equal(reader["sourceToken"], restored["outputToken"], "rt-reads-current-restored-generation")
    _equal((cal["semanticCreator"], saved["semanticCreator"], restored["semanticCreator"], reader["semanticCreator"]),
           (cal["semanticCreator"],) * 4, "retained-semantic-creator")
    if not cal["semanticCreator"]:
        raise ValueError("IndependentOracleMismatch:missing-caller-creator")
    _equal(frame["sourceCuts"]["priorWord"]["sourceToken"], old["sourceToken"], "prior-read-token")
    _equal(terminal["dp"], {"classification": "SourceValueUnknown", "sourceReadPC": 0x2682,
                            "sourceToken": old["sourceToken"], "value": None}, "retained-unknown-dp")
    _equal(frame["sourceCuts"]["priorWord"]["terminalDependentFields"], ["dp", "DATA0084_0085"], "not-whole-state-independent")
    return {"independentOracle": "PASS", "scope": "ProjectedStaticObligationsAndInventedRelationsOnly",
            "actualCpuExecutions": 0, "actualRomExecutions": 0, "runtimeAdmission": "Blocked",
            "firstMismatch": None, "firmwareReady": False}
