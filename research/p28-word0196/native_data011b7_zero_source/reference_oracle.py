"""Independent, invented-state constraints; this module never executes target code.

Authored from reviewed instruction extents and primary semantic obligations before
reading the new producer/route models. A compatible four-read packet is a finite
conditional example, not an observed interrupt history or a native ownership proof.
"""

CLASSIFICATION = "StaticData011B7ZeroSourceProvenance_NotCpuExecution"
REASONS = (
    "WrongSourceAddress",
    "WrongDD",
    "WrongUSP",
    "WrongSCB",
    "WrongLRB",
    "WrongPage",
    "WrongHighByteMapping",
    "InjectedDATA03F3",
    "HostBranch2919Outcome",
    "CLR291BBypassed",
    "AccumulatorMutationBeforeStore",
    "CopyBeforeSourceGeneration",
    "UnknownBufferOverwrite",
    "ImportedM2agFixedSource",
    "ImportedM2bzCanary",
    "WrongSourceWord0217",
    "WordWriterTreatedAsByte",
    "SameValueGenerationDeduplicated",
    "SBRDirectionAssumed",
    "ArtificialIRQTransition",
    "WrongCallerRTFrame",
    "CrossMachineGeneration",
    "MissingIndependent011F3Gate",
    "WrongJBS064FSuccessor",
    "FalseOriginalRomExecution",
    "HistoricalFingerprintModified",
    "Length3CannotWriteFlagAt0269",
    "PacketReadIdentityReused",
    "SourceIrqBit1IsNotInputGateBit9",
    "Later2966ReadBorrowed2917",
    "UnknownAliasIsNotActualOverwrite",
)


def _integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def reviewed_case(case_id="positive-direct-f01", flag=1, route="A"):
    """Construct one explicit conditional fixture, without native identifiers."""
    machine = "model:" + case_id
    reads = [
        {"role": role, "pc": pc, "value": value,
         "readId": "model:read:" + role, "invocation": "model:irq:" + role}
        for role, pc, value in (
            ("H", 0x0277, 0x21), ("L", 0x027F, 4),
            ("F", 0x0262, flag), ("K", 0x0284, (-(0x21 + 4 + flag)) % 256),
        )
    ]
    copying = route != "A"
    int1 = route == "B-int1"
    return {
        "caseId": case_id,
        "classification": "InventedOnly_ConditionalPacketAndZeroSource",
        "machineId": machine,
        "source": {
            "space": "DATA", "address": 0x0055, "widthBits": 8,
            "generationKind": "InventedConditionalSfrReads",
            "injected03F3": None, "importedHistoricalOwner": None,
            "canary": None, "reads": reads,
        },
        "handler": {
            "entry": 0x0213, "vector": 0x000A, "irqWordBit": 1,
            "scb": 2, "lrb": 0x007E, "mode0356Bit1": 1,
            "old0356Bit6": 0, "initialR7": 0,
            "actualModeOwner": None, "actualInitialR7Owner": None,
            "actualReadOwners": None, "actualIRQHistory": None,
        },
        "producer": {
            "scb": 0, "scope": "ConditionalColdProducerContext_NotGlobalScbRule",
            "lrb": 0x0041, "page": 0x0200, "usp": 0x0180,
            "ddAfterCLR": 1, "incomingDD": None,
            "ordinaryAccumulator": "ExplicitConditionalHypothesis",
            "highByteOffset": 1, "hostBranch2919": None,
            "clrReached": True, "accumulatorMutated": False,
            "storeWidthBits": 16, "storePCs": [0x291C, 0x291E, 0x2920, 0x2922],
            "read2917Token": "model:read2917:F-generation",
            "read2966Token": "model:separate-read2966-unknown",
            "read2966ActualValue": None,
        },
        "route": {
            "kind": route, "sourceWord": 0x0212, "targetWord": 0x011A,
            "copyRoot": (0x0379 if int1 else 0x03ED) if copying else None,
            "copyLoadPC": (0x5C2B if int1 else 0x03FE) if copying else None,
            "copyWriterPC": (0x5C2D if int1 else 0x0400) if copying else None,
            "storeSequence": 5, "copySequence": 6 if copying else None,
            "copyFrameMatches": True, "sourceMachine": machine, "copyMachine": machine,
            "bufferOverwrittenUnknown": False, "deduplicateSameValue": False,
            "sbrDirection": "PrimaryConflictUnresolved", "fabricatedIRQ": False,
            "unknownAlias": False, "claimedActualOverwrite": False,
            "directBeforeReceiverCopy": False,
        },
        "reader": {
            "pc": 0x064F, "gate011F3": 0,
            "gateSource": "InventedIndependentConditionalSource_NotNativeOwner",
            "successor": 0x0652, "irqH1WordBit": 9, "oldIrqH1": 0,
            "actualGateOwner": None, "actuallyExecuted": False,
        },
        "history": {
            "source": "model:one-history", "data012A": "model:one-history",
            "caller": "model:one-history", "frame": "model:one-history",
            "selector013C": "model:one-history", "data012AValue": 0,
        },
        "actual": {
            "cpuExecutions": 0, "romExecutions": 0, "irqDeliveries": 0,
            "machineId": None, "instructionIndex": None, "writeOrdinal": None,
        },
        "preservation": {"historicalExpected": "model:old-sha", "recordedExpected": "model:old-sha"},
    }


def curated_controls():
    """Six compatible witnesses and 31 relation-changing refusals; no sweep."""
    cases = []
    for case_id, flag, route, incoming in (
        ("positive-direct-f01", 1, "A", None),
        ("positive-direct-f03", 3, "A", 0),
        ("positive-direct-fff", 255, "A", 1),
        ("positive-serial-f01", 1, "B-serial", None),
        ("positive-serial-f81", 129, "B-serial", None),
        ("positive-int1-f01", 1, "B-int1", None),
    ):
        value = reviewed_case(case_id, flag, route)
        value["producer"]["incomingDD"] = incoming
        cases.append({"caseId": case_id, "input": value})
    mutations = (
        ("WrongSourceAddress", "A", "source", "address", 0x03F3),
        ("WrongDD", "A", "producer", "ddAfterCLR", 0),
        ("WrongUSP", "A", "producer", "usp", 0x0190),
        ("WrongSCB", "A", "producer", "scb", 2),
        ("WrongLRB", "A", "producer", "lrb", 0x0042),
        ("WrongPage", "A", "producer", "page", 0x0100),
        ("WrongHighByteMapping", "A", "producer", "highByteOffset", 0),
        ("InjectedDATA03F3", "A", "source", "injected03F3", 1),
        ("HostBranch2919Outcome", "A", "producer", "hostBranch2919", "fallthrough"),
        ("CLR291BBypassed", "A", "producer", "clrReached", False),
        ("AccumulatorMutationBeforeStore", "A", "producer", "accumulatorMutated", True),
        ("CopyBeforeSourceGeneration", "B-serial", "route", "copySequence", 4),
        ("UnknownBufferOverwrite", "B-serial", "route", "bufferOverwrittenUnknown", True),
        ("ImportedM2agFixedSource", "A", "source", "importedHistoricalOwner", "M2ag_fixedSource"),
        ("ImportedM2bzCanary", "A", "source", "canary", 0xA5),
        ("WrongSourceWord0217", "B-serial", "route", "sourceWord", 0x0216),
        ("WordWriterTreatedAsByte", "A", "producer", "storeWidthBits", 8),
        ("SameValueGenerationDeduplicated", "B-serial", "route", "deduplicateSameValue", True),
        ("SBRDirectionAssumed", "A", "route", "sbrDirection", "Set1Established"),
        ("ArtificialIRQTransition", "A", "route", "fabricatedIRQ", True),
        ("WrongCallerRTFrame", "B-int1", "route", "copyFrameMatches", False),
        ("CrossMachineGeneration", "A", "route", "sourceMachine", "model:other"),
        ("MissingIndependent011F3Gate", "A", "reader", "gate011F3", None),
        ("WrongJBS064FSuccessor", "A", "reader", "successor", 0x065F),
        ("FalseOriginalRomExecution", "A", "actual", "romExecutions", 1),
        ("HistoricalFingerprintModified", "A", "preservation", "recordedExpected", "model:changed-sha"),
        ("Length3CannotWriteFlagAt0269", "A", None, None, None),
        ("PacketReadIdentityReused", "A", None, None, None),
        ("SourceIrqBit1IsNotInputGateBit9", "B-int1", "reader", "irqH1WordBit", 1),
        ("Later2966ReadBorrowed2917", "A", "producer", "read2966Token", "model:read2917:F-generation"),
        ("UnknownAliasIsNotActualOverwrite", "A", None, None, None),
    )
    for label, route, group, key, replacement in mutations:
        case_id = "negative-" + label
        value = reviewed_case(case_id, 1, route)
        if group is not None:
            value[group][key] = replacement
        elif label == "Length3CannotWriteFlagAt0269":
            value["source"]["reads"][1]["value"] = 3
            value["source"]["reads"][3]["value"] = (-(0x21 + 3 + 1)) % 256
        elif label == "PacketReadIdentityReused":
            value["source"]["reads"][2]["readId"] = value["source"]["reads"][0]["readId"]
        else:
            value["route"]["unknownAlias"] = True
            value["route"]["claimedActualOverwrite"] = True
        cases.append({"caseId": case_id, "input": value})
    return cases


def _shape(case):
    groups = ("source", "handler", "producer", "route", "reader", "history", "actual", "preservation")
    if not isinstance(case, dict) or any(not isinstance(case.get(key), dict) for key in groups):
        return False
    if not isinstance(case.get("caseId"), str) or not isinstance(case.get("machineId"), str):
        return False
    required = reviewed_case()
    if not required.keys() <= case.keys() or any(
        not required[group].keys() <= case[group].keys() for group in groups
    ):
        return False
    reads = case["source"].get("reads")
    return (
        isinstance(reads, list) and len(reads) == 4
        and all(isinstance(row, dict) and _integer(row.get("value"))
                and 0 <= row["value"] <= 255
                and isinstance(row.get("readId"), str)
                and isinstance(row.get("invocation"), str) for row in reads)
    )


def _reason(case):
    if not _shape(case):
        return "ClosedCaseShapeRequired"
    source, handler, producer, route, reader, history, actual, preservation = (
        case[key] for key in ("source", "handler", "producer", "route", "reader", "history", "actual", "preservation")
    )
    rows = source["reads"]
    values = [row["value"] for row in rows]
    copying = route.get("kind") in ("B-serial", "B-int1")
    int1 = route.get("kind") == "B-int1"
    store_order, copy_order = route.get("storeSequence"), route.get("copySequence")
    actual_claim = (
        any(actual.get(key) != 0 for key in ("cpuExecutions", "romExecutions", "irqDeliveries"))
        or any(actual.get(key) is not None for key in ("machineId", "instructionIndex", "writeOrdinal"))
        or reader.get("actuallyExecuted") is not False
        or reader.get("actualGateOwner") is not None
        or any(handler.get(key) is not None for key in (
            "actualModeOwner", "actualInitialR7Owner", "actualReadOwners", "actualIRQHistory"))
    )
    predicates = (
        source.get("space") != "DATA" or source.get("address") != 0x0055 or source.get("widthBits") != 8,
        producer.get("ddAfterCLR") != 1,
        producer.get("usp") != 0x0180,
        producer.get("scb") != 0,
        producer.get("lrb") != 0x0041,
        producer.get("page") != 0x0200,
        producer.get("highByteOffset") != 1,
        source.get("injected03F3") is not None,
        producer.get("hostBranch2919") is not None,
        producer.get("clrReached") is not True,
        producer.get("accumulatorMutated") is not False,
        copying and (not _integer(store_order) or not _integer(copy_order) or copy_order <= store_order),
        copying and route.get("bufferOverwrittenUnknown") is not False,
        source.get("importedHistoricalOwner") is not None,
        source.get("canary") is not None,
        route.get("sourceWord") != 0x0212 or route.get("targetWord") != 0x011A,
        producer.get("storeWidthBits") != 16,
        route.get("deduplicateSameValue") is not False,
        route.get("sbrDirection") != "PrimaryConflictUnresolved",
        route.get("fabricatedIRQ") is not False,
        copying and route.get("copyFrameMatches") is not True,
        route.get("sourceMachine") != case["machineId"] or route.get("copyMachine") != case["machineId"],
        reader.get("gate011F3") != 0 or reader.get("gateSource") != "InventedIndependentConditionalSource_NotNativeOwner",
        reader.get("successor") != 0x0652,
        actual_claim,
        preservation.get("historicalExpected") != preservation.get("recordedExpected"),
        values[1] == 3,
        len({row["readId"] for row in rows}) != 4 or len({row["invocation"] for row in rows}) != 4,
        int1 and (reader.get("irqH1WordBit") != 9 or reader.get("oldIrqH1") != 0),
        producer.get("read2966Token") == producer.get("read2917Token") or producer.get("read2966ActualValue") is not None,
        route.get("unknownAlias") is True and route.get("claimedActualOverwrite") is True,
    )
    for label, failed in zip(REASONS, predicates):
        if failed:
            return label
    if handler.get("mode0356Bit1") != 1:
        return "ParserModeGateNotSatisfied"
    if sum(values) % 256:
        return "PacketChecksumNotAccepted"
    if values[0] != 0x21:
        return "Command21PredicateNotSatisfied"
    if not values[2] & 1:
        return "CurrentFlagBit0BypassesCLR"
    if values[1] != 4 or [(row.get("role"), row.get("pc")) for row in rows] != [
        ("H", 0x0277), ("L", 0x027F), ("F", 0x0262), ("K", 0x0284)
    ]:
        return "PacketReadSitesWrong"
    if any(handler.get(key) != expected for key, expected in (
        ("entry", 0x0213), ("vector", 0x000A), ("irqWordBit", 1),
        ("scb", 2), ("lrb", 0x007E), ("old0356Bit6", 0), ("initialR7", 0),
    )):
        return "HandlerContextWrong"
    copy_context = {
        "A": (None, None, None),
        "B-serial": (0x03ED, 0x03FE, 0x0400),
        "B-int1": (0x0379, 0x5C2B, 0x5C2D),
    }
    if route.get("kind") not in copy_context or (
        route.get("copyRoot"), route.get("copyLoadPC"), route.get("copyWriterPC")
    ) != copy_context[route.get("kind")]:
        return "RouteCopyContextWrong"
    if len({history.get(key) for key in ("source", "data012A", "caller", "frame", "selector013C")}) != 1:
        return "UncorrelatedCallerHistory"
    if reader.get("pc") != 0x064F:
        return "WrongReaderBoundary"
    if producer.get("storePCs") != [0x291C, 0x291E, 0x2920, 0x2922]:
        return "WrongStoreInventory"
    if route.get("kind") == "A" and route.get("directBeforeReceiverCopy") is True:
        return "DirectGenerationDominatedByReceiverCopy"
    if (case.get("classification") != "InventedOnly_ConditionalPacketAndZeroSource"
            or source.get("generationKind") != "InventedConditionalSfrReads"
            or producer.get("scope") != "ConditionalColdProducerContext_NotGlobalScbRule"
            or producer.get("ordinaryAccumulator") != "ExplicitConditionalHypothesis"):
        return "ClosedCaseShapeRequired"
    return None


def reference_case(case):
    """Resolve finite conditional relations, retaining every actual owner unknown."""
    reason = _reason(case)
    valid = reason is None
    shaped = _shape(case)
    case_id = case.get("caseId") if isinstance(case, dict) else None
    values = [row["value"] for row in case["source"]["reads"]] if shaped else None
    route = case["route"] if shaped else {}
    alias_unknown = valid and route.get("unknownAlias") is True
    writer = (0x291C if route.get("kind") == "A" else route.get("copyWriterPC")) if valid else None
    known = valid and not alias_unknown
    return {
        "caseId": case_id, "valid": valid, "firstMismatch": reason,
        "firstMissingObligation": reason if reason else "CurrentSourceISRAndPacketEntryStateOwners",
        "classification": "InventedOnly_ConditionalZeroRelations" if valid else "InventedOnly_Refused",
        "packetChecksum": sum(values) % 256 if valid else None,
        "flagBit0": values[2] & 1 if valid else None,
        "branch2919ConditionalNext": 0x291B if valid else None,
        "writerWordValue": 0 if valid else None,
        "writerAddresses": [0x011A, 0x011B, 0x011C, 0x011D, 0x0212, 0x0213, 0x0214, 0x0215] if valid else [],
        "semanticZeroOwner": "model:" + case_id + ":CLR291B" if valid else None,
        "latestStorageWriterPC": writer if known else None,
        "latestStorageGeneration": (
            "model:" + case_id + (":ST291C:1" if route.get("kind") == "A" else ":COPY:5")
        ) if known else None,
        "readerBit7": 0 if known else None,
        "conditionalReaderSuccessor": 0x0652 if known else None,
        "preservation": ("UnresolvedAlias" if alias_unknown else "ConditionalNoRelevantOverlapHypothesis") if valid else "NotEstablishedRefused",
        "actualSourceOwners": {
            "mode0356Bit1": None, "initialR7": None, "reads0055": None,
            "data03F1": None, "data03F3": None, "irqHistory": None,
        },
        "actualCpuExecutions": 0, "actualOriginalRomExecutions": 0, "actualIRQDeliveries": 0,
        "actualMachineId": None, "actualNativeInstructionIndex": None, "actualWriterOrdinal": None,
        "actualBranch064FExecuted": False, "runtimeAdmission": "Blocked", "firmwareReady": False,
    }


def _at(document, path):
    value = document
    try:
        for key in path:
            value = value[key]
    except (KeyError, IndexError, TypeError):
        return {"missingPath": list(path)}
    return value


def _literal_checks(document, expected, prefix):
    return [
        {"field": prefix + "." + ".".join(map(str, path)), "expected": value, "actual": _at(document, path)}
        for path, value in expected if _at(document, path) != value
    ]


def independent_check(producer, route):
    """Compare independently fixed source obligations, never CPU observations."""
    producer_expected = (
        (("classification",), CLASSIFICATION),
        (("standardSource", "address"), 0x0055),
        (("standardSource", "widthBits"), 8),
        (("standardSource", "access"), "ReadOnly"),
        (("standardSource", "resetValue"), None),
        (("standardSource", "actualRead"), None),
        (("standardSource", "actualEcuApplicabilityEstablished"), False),
        (("handlerContext", "entryPC"), 0x0213),
        (("handlerContext", "programVector"), 0x000A),
        (("handlerContext", "standardIrqWordBit"), 1),
        (("handlerContext", "pswWriterPC"), 0x0217),
        (("handlerContext", "pswWrittenLiteral"), 0x0102),
        (("handlerContext", "conditionalSCB"), 2),
        (("handlerContext", "fullPswReadbackIsWrittenLiteral"), False),
        (("handlerContext", "lrbWriterPC"), 0x021C),
        (("handlerContext", "requiredLRB"), 0x007E),
        (("handlerContext", "pageBase"), 0x0300),
        (("handlerContext", "localBase"), 0x03F0),
        (("handlerContext", "r1Address"), 0x03F1),
        (("handlerContext", "r2Address"), 0x03F2),
        (("handlerContext", "r3Address"), 0x03F3),
        (("handlerContext", "r5Address"), 0x03F5),
        (("handlerContext", "r6Address"), 0x03F6),
        (("handlerContext", "r7Address"), 0x03F7),
        (("handlerContext", "returnPC"), 0x029C),
        (("handlerContext", "actualHandlerEntryObserved"), False),
        (("parserContext", "entryPC"), 0x28AE),
        (("parserContext", "requiredLRB"), 0x0041),
        (("parserContext", "pageBase"), 0x0200),
        (("parserContext", "requiredSCB"), 0),
        (("parserContext", "requiredUSP"), 0x0180),
        (("parserContext", "handlerOrReceiverContextMayBeImported"), False),
        (("predicate", "sourceAddress"), 0x03F3),
        (("predicate", "sourceReaderPC"), 0x2917),
        (("predicate", "predicateWriterPC"), 0x2918),
        (("predicate", "branchPC"), 0x2919),
        (("predicate", "branchDisplacement"), 0x48),
        (("predicate", "branchTarget"), 0x2963),
        (("predicate", "fallthroughPC"), 0x291B),
        (("predicate", "shiftRecomputesZf"), False),
        (("predicate", "actualSourceValue"), None),
        (("predicate", "later2966ReadMayReuse2917Observation"), False),
        (("packetConstraints", "symbols", "H"), 0x21),
        (("packetConstraints", "symbols", "L"), 4),
        (("packetConstraints", "readOrder"), [0x0277, 0x027F, 0x0262, 0x0284]),
        (("packetConstraints", "samePeripheralSampleMayBeReused"), False),
        (("packetConstraints", "initialR7", "requiredValue"), 0),
        (("packetConstraints", "initialR7", "actualValue"), None),
        (("packetConstraints", "initialR7", "currentOwnerEstablished"), False),
        (("packetConstraints", "actualSameMachinePacketObserved"), False),
        (("packetConstraints", "sharedHandlerPrefix"), [0x0213, 0x0215, 0x0217, 0x021C, 0x021F, 0x0222, 0x0225]),
        (("zero", "producerPC"), 0x291B),
        (("zero", "wordValue"), 0),
        (("zero", "AL"), 0), (("zero", "AH"), 0),
        (("zero", "DD"), 1), (("zero", "ZF"), 1),
        (("zero", "CF"), "Retained1OnSelectedFallthrough"),
        (("zero", "HC"), "RetainedIncomingUnknown"),
        (("zero", "interveningAccumulatorMutation"), False),
        (("zero", "interveningControlTransfer"), False),
        (("zero", "selectedHighByteBit"), 7),
        (("zero", "sameValueStoreCreatesFreshGeneration"), True),
        (("zero", "actualZeroWriterObserved"), False),
        (("actualNative", "actualCpuExecutions"), 0),
        (("actualNative", "actualOriginalRomExecutions"), 0),
        (("actualNative", "actualRetiredInstructions"), 0),
        (("actualNative", "actualMachineId"), None),
        (("actualNative", "actualNativeInstructionIndex"), None),
        (("actualNative", "actualAllNativeWriteOrdinal"), None),
        (("actualNative", "actualBranch064CExecuted"), False),
        (("actualNative", "actualBranch064FExecuted"), False),
        (("actualNative", "actualSourceOwnerEstablished"), False),
        (("runtimeAdmission",), "Blocked"), (("firmwareReady",), False),
    )
    route_expected = (
        (("classification",), CLASSIFICATION),
        (("contexts", "producer", "requiredDD"), 1),
        (("contexts", "producer", "requiredUSP"), 0x0180),
        (("contexts", "producer", "requiredPage"), 0x0200),
        (("contexts", "receiver", "psw"), 0x0102),
        (("contexts", "receiver", "scb"), 2),
        (("contexts", "receiver", "lrb"), 0x0021),
        (("contexts", "receiver", "page"), 0x0100),
        (("contexts", "receiver", "usp"), 0x0280),
        (("zeroInt1Gate", "copiedLowByte"), 0),
        (("zeroInt1Gate", "readerPC"), 0x0396),
        (("zeroInt1Gate", "wordBit"), 9),
        (("zeroInt1Gate", "vectorIdentity"), 0x001A),
        (("zeroInt1Gate", "requiredOldValue"), 0),
        (("zeroInt1Gate", "zeroPath"), [0x0390, 0x0393, 0x0396, 0x0399, 0x03A5, 0x03A8]),
        (("zeroInt1Gate", "oneBypass"), [0x039B, 0x039E, 0x03A2, 0x069A]),
        (("postZero", "callPC"), 0x79D5),
        (("postZero", "target"), 0x5EE3),
        (("postZero", "requiredRT"), 0x5EF0),
        (("postZero", "returnPC"), 0x79D8),
        (("postZero", "calleeC8Site"), 0x5EEE),
        (("postZero", "c8PrimaryConflictResolved"), False),
        (("second03F3Read", "pc"), 0x2966),
        (("second03F3Read", "sourceAddress"), 0x03F3),
        (("second03F3Read", "widthBits"), 8),
        (("second03F3Read", "shiftPCs"), [0x2967, 0x2968]),
        (("second03F3Read", "predicatePC"), 0x2969),
        (("second03F3Read", "selectedBit"), 1),
        (("second03F3Read", "canBorrow2917ReadValueOrGeneration"), False),
        (("runtimeAdmission",), "Blocked"), (("firmwareReady",), False),
    )
    mismatches = _literal_checks(producer, producer_expected, "producer")
    mismatches.extend(_literal_checks(route, route_expected, "route"))
    # Each full-word zero is a new store even if both bytes already held zero.
    stores = producer.get("zero", {}).get("stores", [])
    projection = [(row.get("pc"), row.get("address"), row.get("widthBits"), row.get("footprint")) for row in stores]
    expected_stores = [
        (0x291C, 0x011A, 16, [0x011A, 0x011B]),
        (0x291E, 0x011C, 16, [0x011C, 0x011D]),
        (0x2920, 0x0212, 16, [0x0212, 0x0213]),
        (0x2922, 0x0214, 16, [0x0214, 0x0215]),
    ]
    if projection != expected_stores:
        mismatches.append({"field": "producer.zero.stores", "expected": expected_stores, "actual": projection})
    stage_projection = [(row.get("role"), row.get("path")) for row in producer.get("packetConstraints", {}).get("stages", [])]
    stage_paths = [
        ("H", [0x0255, 0x0256, 0x0275, 0x0277, 0x0279, 0x027A, 0x027B, 0x027D,
               0x0270, 0x0272, 0x0295, 0x0297, 0x029A, 0x029C]),
        ("L", [0x0255, 0x0256, 0x0258, 0x0259, 0x025B, 0x027F, 0x0281, 0x0282,
               0x026D, 0x026F, 0x0270, 0x0272, 0x0295, 0x0297, 0x029A, 0x029C]),
        ("F", [0x0255, 0x0256, 0x0258, 0x0259, 0x025B, 0x025D, 0x025F, 0x0260,
               0x0262, 0x0264, 0x0267, 0x0269, 0x026A, 0x026D, 0x026F, 0x0270,
               0x0272, 0x0295, 0x0297, 0x029A, 0x029C]),
        ("K", [0x0255, 0x0256, 0x0258, 0x0259, 0x025B, 0x025D, 0x025F, 0x0260,
               0x0284, 0x0286, 0x0287, 0x0289, 0x028A, 0x028C, 0x028E, 0x0290,
               0x0293, 0x0295, 0x0297, 0x029A, 0x029C]),
    ]
    if stage_projection != stage_paths:
        mismatches.append({"field": "producer.packetConstraints.stages.path", "expected": stage_paths, "actual": stage_projection})
    return {"valid": not mismatches, "firstMismatch": mismatches[0] if mismatches else None,
            "mismatches": mismatches, "comparedFactCount": len(producer_expected) + len(route_expected) + 2,
            "actualCpuExecutions": 0, "actualOriginalRomExecutions": 0,
            "actualIRQDeliveries": 0, "firmwareReady": False}
