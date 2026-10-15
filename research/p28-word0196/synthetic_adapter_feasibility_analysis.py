"""Closed M2bl adapter mathematics, never instruction execution.

Inputs contain opaque PROGRAM identities and invented abstract access/transition
claims, not executable contents. The model checks address translation, reviewed
admission, state representation, access topology and exit/fetch obligations.
It performs no opcode arithmetic, invokes no CPU/codec, and grants no runtime
authority. The M2bk expected-state domain is neither imported nor narrowed.
"""

import hashlib
import json


_SOURCE = "M2bjVerifiedSyntheticComposite_20Nodes_51Bytes"
_COMPOSITE = "91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1"
_MANUAL = "f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271"
_MODEL = "IndependentSyntheticAdapterModel"
_INVENTED = "InventedOnly_NoNativeGenerationOwner"
_TRANSITION = "InventedAbstractTransitionRecords_NotCPUTrace"
_FUNCTIONAL = "InventedAbstractFunctionalDATAAccess_NotObserved"
_DATA_ADDRESSES = list(range(0x108, 0x110)) + [0x117, 0x124, 0x128, 0x12A, 0x18E, 0x18F, 0x196, 0x197]
_DATA_KEYS = [format(address, "04X") for address in _DATA_ADDRESSES]
_LOCAL_KEYS = _DATA_KEYS[:8]
_RETAIN = ["ah", "hc", "otherPsw", "lrb", "scb", "ssp", "pointingBanks", "halted", "sf"]
_SF = {"status": "SFMeaningStorageNotEstablished", "meaning": None,
       "storage": None, "widthBits": None, "value": None}
_FLAGS = {"cf": 0x8000, "zf": 0x4000, "hc": 0x2000, "dd": 0x1000}
_READS_ONE = 0x0CC8
_STORAGE = 0x0337

# Original logical site, invented synthetic PC, exact form, reviewed length.
# These identities are not an opcode table or an executable instruction stream.
_SITES = (
    (0x556F, 0x1000, "lb-a-page", 2), (0x5571, 0x1002, "sllb-a", 1),
    (0x5572, 0x1003, "rolb-page", 3), (0x5575, 0x1006, "lb-a-r0", 1),
    (0x5576, 0x1007, "andb-a-page", 2), (0x5578, 0x1009, "cmp-page-imm16", 5),
    (0x557D, 0x100E, "jlt-rel8", 2), (0x557F, 0x1010, "movb-r1-page", 3),
    (0x5582, 0x1013, "andb-page-a", 3), (0x5585, 0x1016, "jbs-page-bit7", 3),
    (0x5588, 0x1019, "jbs-page-bit5", 3), (0x558B, 0x101C, "andb-page-a", 3),
    (0x558E, 0x101F, "orb-page-imm8", 4), (0x5592, 0x1023, "lb-a-page", 2),
    (0x5594, 0x1025, "orb-a-imm8", 2),
    ("DirectJ_NotBelow", 0x1027, "j-address", 3),
    (0x55BF, 0x102A, "lb-a-imm8", 2), (0x55C1, 0x102C, "stb-a-page", 2),
    (0x55C3, 0x102E, "stb-a-page", 2), ("DirectJ_Below", 0x1030, "j-address", 3),
)
_COMMON = [0x556F, 0x5571, 0x5572, 0x5575, 0x5576, 0x5578, 0x557D]
_PREFIX = [0x557F, 0x5582, 0x5585]
_SUFFIX = [0x5592, 0x5594, "DirectJ_NotBelow"]
_PATHS = {
    "A": _COMMON + [0x55BF, 0x55C1, 0x55C3, "DirectJ_Below"],
    "B": _COMMON + _PREFIX + _SUFFIX,
    "C": _COMMON + _PREFIX + [0x5588] + _SUFFIX,
    "D": _COMMON + _PREFIX + [0x5588, 0x558B, 0x558E] + _SUFFIX,
}
_BRANCH_TARGETS = {0x557D: 0x102A, 0x5585: 0x1023, 0x5588: 0x1023}
_PRIMARY = {
    "lb-a-page": (124, ["FixedF4", "PageOffset8"]),
    "sllb-a": (197, ["Fixed53"]),
    "rolb-page": (173, ["FixedC4", "PageOffset8", "FixedB7"]),
    "lb-a-r0": (124, ["Fixed78"]),
    "andb-a-page": (76, ["FixedD7", "PageOffset8"]),
    "cmp-page-imm16": (90, ["FixedB4", "EvenPageOffset8", "FixedC0", "Immediate16Low8", "Immediate16High8"]),
    "jlt-rel8": (120, ["FixedCA", "SignedRelative8"]),
    "movb-r1-page": (153, ["FixedC4", "PageOffset8", "Fixed49"]),
    "andb-page-a": (77, ["FixedC4", "PageOffset8", "FixedD1"]),
    "jbs-page-bit7": (119, ["FixedEF", "PageOffset8", "SignedRelative8"]),
    "jbs-page-bit5": (119, ["FixedED", "PageOffset8", "SignedRelative8"]),
    "orb-page-imm8": (163, ["FixedC4", "PageOffset8", "FixedE0", "Immediate8"]),
    "orb-a-imm8": (160, ["FixedE6", "Immediate8"]),
    "lb-a-imm8": (124, ["Fixed77", "Immediate8"]),
    "stb-a-page": (208, ["FixedD4", "PageOffset8"]),
    "j-address": (116, ["Fixed03", "ProgramTargetLow8", "ProgramTargetHigh8"]),
}


def _need(condition, code):
    if not condition:
        raise ValueError(code)


def _closed(value, names, code):
    _need(type(value) is dict and set(value) == set(names), code)


def _uint(value, maximum, code):
    _need(type(value) is int and 0 <= value <= maximum, code)


def _same(actual, expected, code):
    # Exact JSON comparison, including bool-versus-integer distinctions.
    _need(json.dumps(actual, sort_keys=True, separators=(",", ":")) ==
          json.dumps(expected, sort_keys=True, separators=(",", ":")), code)


def _copy_json(value):
    active, count = set(), [0]

    def walk(item, depth):
        count[0] += 1
        _need(depth <= 48 and count[0] <= 20000, "JsonBoundaryBound")
        if item is None or type(item) in (bool, int):
            return item
        if type(item) is str:
            _need(len(item) <= 4096, "JsonBoundaryString")
            return item
        _need(type(item) in (list, dict), "JsonBoundaryPrimitive")
        _need(id(item) not in active, "JsonBoundaryCycle")
        _need(len(item) <= 4096, "JsonBoundaryContainer")
        active.add(id(item))
        if type(item) is list:
            result = [walk(child, depth + 1) for child in item]
        else:
            _need(all(type(key) is str and len(key) <= 4096 for key in item), "JsonBoundaryKey")
            result = {key: walk(child, depth + 1) for key, child in item.items()}
        active.remove(id(item))
        return result

    return walk(value, 0)


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=True, sort_keys=True,
                                    separators=(",", ":")).encode("ascii")).hexdigest()


def _opaque(offset):
    return "InventedOpaqueCell-" + str(offset)


def _segment():
    return {
        "basePc16": 4096, "endExclusive": 4147, "exactLength": 51,
        "sourceIdentity": _SOURCE, "immutableContentDigest": _COMPOSITE,
        "programAddressingMode": "SubtractBase_NoModulo_NoPadding",
        "externalAnchorExclusion": [0x5596, 0x55C5], "paddingBytes": 0,
        "overlappingSegments": [], "opaqueContent": [_opaque(index) for index in range(51)],
        "contentAvailability": "NoExecutableBytes_OpaqueIdentitiesOnly",
        "contentDigestEvidence": "UpstreamIdentityPin_NotMeasuredOpaqueContentDigest",
        "evidenceKind": _MODEL,
    }


def _translate(segment, requested_pc):
    standard = _segment()
    _closed(segment, standard, "SegmentClosedShape")
    _uint(segment["basePc16"], 65535, "SegmentOverflowOrLength")
    _uint(segment["exactLength"], 65536, "SegmentOverflowOrLength")
    _need(segment["exactLength"] > 0 and
          segment["basePc16"] + segment["exactLength"] <= 65536, "SegmentOverflowOrLength")
    _same(segment["endExclusive"], segment["basePc16"] + segment["exactLength"], "SegmentEndRelation")
    for key, value in standard.items():
        _same(segment[key], value, "SegmentBinding:" + key)
    _uint(requested_pc, 65535, "ProgramPcDomain")
    _need(segment["basePc16"] <= requested_pc < segment["endExclusive"], "ProgramOutOfRange")
    return requested_pc - segment["basePc16"]


def _mapping(payload):
    _closed(payload, ["segment", "requestedPc", "claimedOffset"], "MappingPayload")
    offset = _translate(payload["segment"], payload["requestedPc"])
    _uint(payload["claimedOffset"], 50, "ProgramOffsetSubtractionRelation")
    _same(payload["claimedOffset"], offset, "ProgramOffsetSubtractionRelation")
    return {"classification": "SyntheticSegmentAddressTranslationModelVerified",
            "requestedPc": payload["requestedPc"], "offset": offset, "opaqueIdentity": _opaque(offset),
            "paddingBytes": 0, "rustSegmentMapping": "NotImplemented",
            "contentDigestMeasured": False, "evidenceKind": _MODEL}


def _operand(kind, value=None, bit=None):
    result = {"kind": kind}
    if value is not None:
        result["value"] = value
    if bit is not None:
        result["bit"] = bit
    return result


def _typed_operands(identity):
    accumulator = _operand("AccumulatorA")
    page = lambda value: _operand("PageOffset8", value)
    if identity in (0x556F, 0x5576, 0x5592):
        return [accumulator, page(0x8F if identity == 0x5592 else 0x8E)]
    if identity == 0x5571:
        return [accumulator]
    if identity == 0x5572:
        return [page(0x8E)]
    if identity == 0x5575:
        return [accumulator, _operand("Register0", 0)]
    if identity == 0x5578:
        return [_operand("EvenPageOffset8", 0x96), _operand("Immediate16", 0xC0)]
    if identity == 0x557D:
        return [_operand("TargetPC16", 0x102A)]
    if identity == 0x557F:
        return [_operand("Register1", 1), page(0x17)]
    if identity in (0x5582, 0x558B):
        return [page(0x17 if identity == 0x5582 else 0x8F), accumulator]
    if identity in (0x5585, 0x5588):
        bit, address = (7, 0x2A) if identity == 0x5585 else (5, 0x24)
        return [_operand("PageBit" + str(bit), address, bit), _operand("TargetPC16", 0x1023)]
    if identity == 0x558E:
        return [page(0x2A), _operand("Immediate8", 1)]
    if identity in (0x5594, 0x55BF):
        return [accumulator, _operand("Immediate8", 240 if identity == 0x5594 else 15)]
    if identity in (0x55C1, 0x55C3):
        return [accumulator, page(0x17 if identity == 0x55C1 else 0x8F)]
    _need(identity in ("DirectJ_NotBelow", "DirectJ_Below"), "UnreviewedNode")
    return [_operand("ProgramTarget16", 0x5596 if identity == "DirectJ_NotBelow" else 0x55C5)]


def _inventory():
    nodes = []
    for index, (identity, pc, form, length) in enumerate(_SITES):
        target = _BRANCH_TARGETS.get(identity)
        if type(identity) is str:
            target = 0x5596 if identity == "DirectJ_NotBelow" else 0x55C5
            successors = [target]
        else:
            successors = [pc + length] if target is None else [target, pc + length]
        page, components = _PRIMARY[form]
        nodes.append({
            "nodeIdentity": identity, "syntheticPc": pc, "formId": form, "length": length,
            "architecturalDd": [0] if form in ("sllb-a", "andb-a-page", "orb-a-imm8", "stb-a-page") else [0, 1],
            "reachableDd": [0, 1] if index == 0 else [0],
            "typedOperands": _typed_operands(identity), "target": target, "successors": successors,
            "primaryPatternEvidence": {"manualSha256": _MANUAL,
                "patternIdentity": "IM1991:" + form + ":PDF" + str(page), "pdfPage": page,
                "uninstantiatedPatternComponents": list(components)},
            "opaqueNodeIdentity": "InventedOpaqueNodeIdentity-" + str(index),
        })
    return nodes


def _admission(payload):
    _closed(payload, ["sourceIdentity", "immutableContentDigest", "nodes", "entryDd"], "AdmissionPayload")
    _same(payload["sourceIdentity"], _SOURCE, "AdmissionSourceIdentity")
    _same(payload["immutableContentDigest"], _COMPOSITE, "AdmissionContentDigest")
    _uint(payload["entryDd"], 1, "AdmissionDdDomain")
    planned = _inventory()
    _need(type(payload["nodes"]) is list and len(payload["nodes"]) == 20, "AdmissionExactInventoryCount")
    for actual, expected in zip(payload["nodes"], planned):
        _closed(actual, expected, "AdmissionExactNodeRelation")
        _same([actual["syntheticPc"], actual["nodeIdentity"]],
              [expected["syntheticPc"], expected["nodeIdentity"]], "AdmissionExactInventoryOrder")
        _same(actual, expected, "AdmissionExactNodeRelation")
        dd = payload["entryDd"] if actual["syntheticPc"] == 4096 else 0
        _need(dd in actual["architecturalDd"] and dd in actual["reachableDd"], "AdmissionDdDomain")
    forms = sorted({node["formId"] for node in planned})
    return {"classification": "Closed16FormAdmissionModelVerified", "entryDd": payload["entryDd"],
            "exactFormCount": len(forms), "forms": forms, "nodeCount": len(planned),
            "originalNodeCount": sum(type(node["nodeIdentity"]) is int for node in planned),
            "nodes": planned, "runtimeAdmission": "NotImplemented"}


def _named_flags(flags):
    _closed(flags, _FLAGS, "PswNamedFlagShape")
    for value in flags.values():
        _uint(value, 1, "PswNamedFlagDomain")


def _psw(payload):
    _closed(payload, ["otherPsw", "namedFlags"], "PswPayload")
    other, flags = payload["otherPsw"], payload["namedFlags"]
    _uint(other, 4095, "OtherPswLow12Domain")
    _named_flags(flags)
    named = sum(_FLAGS[name] * flags[name] for name in _FLAGS)
    requested = other | named
    stored = other & _STORAGE
    encoded = stored | _READS_ONE | named
    representable = (other & _READS_ONE) == _READS_ONE
    decoded = {"storedOther": encoded & _STORAGE}
    decoded.update({name: int(bool(encoded & mask)) for name, mask in _FLAGS.items()})
    return {
        "otherPsw": other, "namedFlags": flags.copy(), "requestedPsw": requested,
        "decodedCpuState": decoded, "encodedPsw": encoded,
        "changedBits": requested ^ encoded, "representable": representable,
        "losslessRoundTrip": encoded == requested, "storageMask": _STORAGE,
        "readsOneMask": _READS_ONE,
        "routeA": "ConditionallyAdmissible_SeparateScopeDecisionRequired" if representable
        else "RejectedInManufacturerCompatibleDomain",
        "routeB": {"losslessResearchOtherPsw": other,
                   "cpuPswRepresentationCompatibleByMathematics": representable,
                   "runtimeAdapterCompatibility": "NotEstablished"},
        "upstreamOracleDomainChanged": False,
        "fullInventedDomainRuntimeCompatibility": "NotEstablished",
    }


def _data_map(value, local=False):
    keys = _LOCAL_KEYS if local else _DATA_KEYS
    _closed(value, keys, "SnapshotLocalData" if local else "DataClosedInventory")
    for item in value.values():
        _uint(item, 255, "DataByteDomain")


def _aliases(data):
    local = [data[key] for key in _LOCAL_KEYS]
    return {"r": local, "er": [local[2 * index] | (local[2 * index + 1] << 8)
                               for index in range(4)]}


def _validate_aliases(aliases, data, code):
    _closed(aliases, ["r", "er"], code)
    for key, length, maximum in (("r", 8, 255), ("er", 4, 65535)):
        _need(type(aliases[key]) is list and len(aliases[key]) == length, code)
        for value in aliases[key]:
            _uint(value, maximum, code)
    _same(aliases, _aliases(data), code)


def _snapshot_value(snapshot, route, entry):
    _closed(snapshot, ["pc", "a", "al", "ah", "psw", "cf", "zf", "hc", "dd",
                      "otherPsw", "lrb", "scb", "ssp", "pointingBanks", "localData",
                      "localAliases", "halted", "sf", "provenance"], "SnapshotClosedShape")
    for key in ("pc", "a", "psw", "lrb", "ssp"):
        _uint(snapshot[key], 65535, "SnapshotWordDomain")
    for key in ("al", "ah"):
        _uint(snapshot[key], 255, "SnapshotByteDomain")
    _uint(snapshot["otherPsw"], 4095, "OtherPswLow12Domain")
    _uint(snapshot["scb"], 7, "SnapshotScbDomain")
    flags = {name: snapshot[name] for name in _FLAGS}
    _named_flags(flags)
    _same(snapshot["a"], snapshot["al"] | (snapshot["ah"] << 8), "SnapshotAccumulatorAlias")
    _same(snapshot["psw"], snapshot["otherPsw"] |
          sum(flags[name] * _FLAGS[name] for name in _FLAGS), "SnapshotOtherPswScbAlias")
    _same(snapshot["scb"], snapshot["psw"] & 7, "SnapshotOtherPswScbAlias")
    if entry:
        _same(snapshot["pc"], 0x1000, "SnapshotEntryPc")
    _same(snapshot["lrb"], 33, "SnapshotLrbContext")
    _same(snapshot["halted"], False, "SnapshotHalted")
    _same(snapshot["provenance"], _INVENTED, "SnapshotProvenance")
    _same(snapshot["sf"], _SF, "SnapshotUnknownSf")
    banks = snapshot["pointingBanks"]
    _need(type(banks) is list and len(banks) == 8, "SnapshotAllEightBanks")
    for bank in banks:
        _closed(bank, ["X1", "X2", "DP", "USP"], "SnapshotAllEightBanks")
        for value in bank.values():
            _uint(value, 65535, "SnapshotPointingRegisterDomain")
    _data_map(snapshot["localData"], local=True)
    _validate_aliases(snapshot["localAliases"], snapshot["localData"], "SnapshotLocalAlias")
    representable = (snapshot["otherPsw"] & _READS_ONE) == _READS_ONE
    if route == "manufacturer-compatible":
        _need(representable, "SnapshotPswNotRepresentable")
    return {
        "schema": "SyntheticCpuEntrySnapshot", "complete": True, "route": route,
        "currentPage": 256, "localBankBase": 264, "pointingBankCount": 8,
        "activeBank": snapshot["scb"], "aliasEr0": snapshot["localAliases"]["er"][0],
        "pswRepresentable": representable, "sf": _copy_json(_SF),
        "upstreamOracleDomainChanged": False,
    }


def _snapshot(payload):
    _closed(payload, ["before", "after", "route"], "SnapshotPayload")
    route = payload["route"]
    _need(type(route) is str and route in ("lossless-research", "manufacturer-compatible"), "SnapshotRoute")
    before, after = payload["before"], payload["after"]
    result = _snapshot_value(before, route, True)
    _snapshot_value(after, route, False)
    for field in _RETAIN:
        _same(after[field], before[field], "PreservedContext:" + field)
    for key in _LOCAL_KEYS:
        if key != "0109":
            _same(after["localData"][key], before["localData"][key], "PreservedContext:localData")
    # r1 may differ as a RAM alias, not as an unrelated host scalar. The DATA
    # event model independently requires its sole reviewed initial0117 copy.
    result["preservation"] = {
        "preservedFields": list(_RETAIN), "allEightBanksPreserved": True,
        "ahPreserved": True, "sspPreserved": True,
        "r1Er0HighMayChangeOnlyThroughReviewedDataWrite": True,
    }
    return result


def _path(value):
    _need(type(value) is str and value in _PATHS, "ReviewedPathDomain")
    return _PATHS[value]


def _access_topology(path):
    """Reviewed access relations; stores are abstract values, never CPU results."""
    _path(path)
    common = [
        (0x556F, "Read", 0x18E, 8),
        (0x5572, "Read", 0x18E, 8), (0x5572, "Write", 0x18E, 8),
        (0x5575, "Read", 0x108, 8), (0x5576, "Read", 0x18E, 8),
        (0x5578, "Read", 0x196, 16),
    ]
    if path == "A":
        return common + [(0x55C1, "Write", 0x117, 8), (0x55C3, "Write", 0x18F, 8)]
    tail = [(0x557F, "Read", 0x117, 8), (0x557F, "Write", 0x109, 8),
            (0x5582, "Read", 0x117, 8), (0x5582, "Write", 0x117, 8),
            (0x5585, "Read", 0x12A, 8)]
    if path != "B":
        tail.append((0x5588, "Read", 0x124, 8))
    if path == "D":
        tail.extend([(0x558B, "Read", 0x18F, 8), (0x558B, "Write", 0x18F, 8),
                     (0x558E, "Read", 0x12A, 8), (0x558E, "Write", 0x12A, 8)])
    return common + tail + [(0x5592, "Read", 0x18F, 8)]


def _permission_sets(topology):
    reads, writes = set(), set()
    for _, kind, address, width in topology:
        selected = reads if kind == "Read" else writes
        selected.add(address)
        if width == 16:
            selected.add(address + 1)
    return sorted(reads), sorted(writes)


def _permissions(payload):
    _closed(payload, ["classification", "diagnosticSnapshotRead", "events", "finalData",
                      "finalLocalAliases", "initialData", "path", "readPermissions",
                      "seedInitializationAccess", "writePermissions"], "DataPayload")
    _same(payload["classification"], "InventedAdapterRelations_NoInstructionArithmetic", "DataFunctionalCategory")
    topology = _access_topology(payload["path"])
    read_permissions, write_permissions = _permission_sets(topology)
    _same(payload["readPermissions"], read_permissions, "DataReadPermissionPolicyRelation")
    _same(payload["writePermissions"], write_permissions, "DataWritePermissionPolicyRelation")
    _same(payload["seedInitializationAccess"], _DATA_ADDRESSES, "DataSeedCategory")
    _same(payload["diagnosticSnapshotRead"], _DATA_ADDRESSES, "DataDiagnosticCategory")
    _data_map(payload["initialData"])
    _data_map(payload["finalData"])
    state = payload["initialData"].copy()
    events = payload["events"]
    _need(type(events) is list and len(events) == len(topology), "DataExactEventCount")
    ordinal, same_value_count, read_count = 0, 0, 0
    for index, (event, spec) in enumerate(zip(events, topology)):
        identity, kind, address, width = spec
        fields = ["eventIndex", "nodeIdentity", "kind", "space", "address",
                  "widthBits", "classification", "value"]
        fields += ["rawByteReads"] if kind == "Read" else ["oldValue", "writeOrdinal", "sameValue"]
        _closed(event, fields, "DataOrderedAccessRelation")
        _same(event["classification"], _FUNCTIONAL, "DataFunctionalCategory")
        _same([event["eventIndex"], event["nodeIdentity"], event["kind"], event["space"],
               event["address"], event["widthBits"]],
              [index + 1, identity, kind, "DATA", address, width], "DataOrderedAccessRelation")
        _uint(event["value"], 65535 if width == 16 else 255, "DataValueDomain")
        key = format(address, "04X")
        if kind == "Read":
            byte_addresses = [address] if width == 8 else [address, address + 1]
            raw = [{"address": cell, "value": state[format(cell, "04X")]} for cell in byte_addresses]
            _same(event["rawByteReads"], raw, "DataRawReadOrderAndValues")
            value = state[key] | (state[format(address + 1, "04X")] << 8) if width == 16 else state[key]
            _same(event["value"], value, "DataReadValueRelation")
            read_count += 1
        else:
            ordinal += 1
            _uint(event["oldValue"], 255, "DataOldValueDomain")
            _uint(event["writeOrdinal"], 5, "DataWriteOrdinal")
            _same(event["oldValue"], state[key], "DataWriteOldValueRelation")
            _same(event["writeOrdinal"], ordinal, "DataWriteOrdinal")
            unchanged = event["value"] == state[key]
            _same(event["sameValue"], unchanged, "DataSameValueRetention")
            same_value_count += int(unchanged)
            if address == 0x109:
                _same(event["value"], payload["initialData"]["0117"], "DataR1CopyRelation")
            state[key] = event["value"]
    _same(payload["finalData"], state, "DataFinalStateRelation")
    _validate_aliases(payload["finalLocalAliases"], state, "DataLocalAliasRelation")
    return {
        "path": payload["path"], "readPermissions": read_permissions, "writePermissions": write_permissions,
        "logicalReadCount": read_count, "writeCount": ordinal, "sameValueWrites": same_value_count,
        "word0196": payload["initialData"]["0196"] | (payload["initialData"]["0197"] << 8),
        "eventDigest": _digest(events), "finalData": state, "finalLocalAliases": _aliases(state),
        "seedInitializationAccess": list(_DATA_ADDRESSES), "diagnosticSnapshotRead": list(_DATA_ADDRESSES),
        "functionalEvidence": "ExpectedModelOnly_NotActualJournal", "actualFunctionalJournal": "NotRun",
    }


def _fetch_exit(payload):
    _closed(payload, ["classification", "entryPc", "events", "path", "postStopProgramReads",
                      "rawProgramObservationLedger", "stop"], "FetchPayload")
    _same(payload["classification"], _TRANSITION, "FetchInventedClassification")
    _same(payload["entryPc"], 4096, "FetchEntryPc")
    path = _path(payload["path"])
    events = payload["events"]
    _need(type(events) is list and len(events) == len(path), "FetchExactExecutedCount")
    by_identity = {node["nodeIdentity"]: node for node in _inventory()}
    selected_extents, flattened_raw = [], []
    diagnostic_count, direct_count = 0, 0
    terminal = 0x55C5 if payload["path"] == "A" else 0x5596
    for index, (event, identity) in enumerate(zip(events, path)):
        _closed(event, ["branchDecision", "classification", "decodedInstruction", "entryPc",
                        "externalTransfer", "incomingDd", "nextPc", "rawProgramReads",
                        "selectedExtent", "selectedLength", "step"], "FetchEventShape")
        node = by_identity[identity]
        pc, length = node["syntheticPc"], node["length"]
        _same(event["classification"], _TRANSITION, "FetchInventedClassification")
        _same([event["step"], event["entryPc"]], [index + 1, pc], "FetchReviewedPathIdentity")
        _same(event["selectedLength"], length, "FetchSelectedLength")
        extent = {"space": "PROGRAM", "start": pc, "endExclusive": pc + length}
        _same(event["selectedExtent"], extent, "FetchSelectedExtent")
        _closed(event["decodedInstruction"], ["classification", "formId", "length", "nodeIdentity"],
                "FetchClaimedDecodedIdentity")
        _same(event["decodedInstruction"], {
            "classification": "InventedDecodedIdentityClaim_NotDecoderOutput",
            "nodeIdentity": identity, "formId": node["formId"], "length": length},
            "FetchClaimedDecodedIdentity")
        _uint(event["incomingDd"], 1, "AdmissionDdDomain")
        if index != 0:
            _same(event["incomingDd"], 0, "FetchReachableDd")
        next_pc = by_identity[path[index + 1]]["syntheticPc"] if index + 1 < len(path) else terminal
        _same(event["nextPc"], next_pc, "FetchReviewedPathSuccessor")
        if identity in _BRANCH_TARGETS:
            branch = next_pc == _BRANCH_TARGETS[identity]
        else:
            branch = None
        _same(event["branchDecision"], branch, "FetchBranchDecision")
        if type(identity) is str:
            _same(event["externalTransfer"], {"kind": "DirectJ", "target": terminal}, "FetchDirectJTransfer")
            direct_count += 1
        else:
            _same(event["externalTransfer"], None, "FetchUnexpectedExternalTransfer")
        raw = event["rawProgramReads"]
        _need(type(raw) is list and 0 < len(raw) <= 4096, "FetchRawReadInventory")
        architectural_addresses = []
        for read in raw:
            _closed(read, ["sequence", "requestedPc", "offset", "purpose", "opaqueIdentity"],
                    "FetchRawReadShape")
            _uint(read["sequence"], 65535, "FetchRawTranslationAndOrder")
            _uint(read["offset"], 50, "FetchRawTranslationAndOrder")
            offset = _translate(_segment(), read["requestedPc"])
            _same([read["sequence"], read["offset"], read["opaqueIdentity"]],
                  [len(flattened_raw) + 1, offset, _opaque(offset)], "FetchRawTranslationAndOrder")
            _need(type(read["purpose"]) is str and
                  read["purpose"] in ("ArchitecturalSelectedFetch", "DecoderLookahead", "DiagnosticProgramProbe"),
                  "FetchRawPurposeClassification")
            if read["purpose"] == "ArchitecturalSelectedFetch":
                architectural_addresses.append(read["requestedPc"])
            else:
                diagnostic_count += 1
            flattened_raw.append(read.copy())
        # Lookahead is retained in the raw ledger but never substituted for
        # an architectural selected extent or an executed instruction.
        _same(architectural_addresses, list(range(pc, pc + length)), "FetchArchitecturalSelectedExtent")
        selected_extents.append(extent)
    _same(direct_count, 1, "FetchExactlyOneDirectJ")
    _same(payload["rawProgramObservationLedger"], flattened_raw, "FetchRawObservationLedgerRelation")
    _same(payload["postStopProgramReads"], [], "FetchStopBeforeNextProbe")
    _same(payload["stop"], {"afterStep": len(path),
          "exitIdentity": "Below" if payload["path"] == "A" else "NotBelow",
          "pc": terminal, "reason": "StopAfterOneDirectJBeforeExternalFetch"}, "FetchExitStopIdentity")
    return {
        "classification": "FetchAndExternalTrapContractVerified", "path": payload["path"],
        "instructionCount": len(events), "selectedExtents": selected_extents,
        "rawProgramReadCount": len(flattened_raw), "rawProgramReads": flattened_raw,
        "lookaheadOrDiagnosticReadCount": diagnostic_count, "directJCount": direct_count,
        "terminalPc": terminal, "externalProgramReadCount": 0,
        "runtimeExitIsolation": "NotEstablished", "cpuExecutionCount": 0,
    }


def _evidence(payload):
    required = {
        "evidenceLevel": _MODEL, "rustAdapterImplementation": "NotRun",
        "syntheticCpuExecutionCount": 0, "originalRomExecutionCount": 0,
        "targetObjectCount": 0, "hexCount": 0, "firmwareBinCount": 0,
        "firmwareReady": False, "nativeExitIsolation": "NotEstablished",
        "actualDownstreamRejoin": "NotEstablished", "physicalRomPlacement": "NotEstablished",
        "targetProgramEquivalence": "NotEstablished", "firmwareIntegration": "NotEstablished",
        "targetCpuExecution": "NotObserved",
    }
    _closed(payload, required, "EvidenceAuthorityRefusal")
    _same(payload, required, "EvidenceAuthorityRefusal")
    result = required.copy()
    result["classification"] = "EvidenceBoundaryVerified"
    result["actualSyntheticExecution"] = "BlockedPendingSeparatelyAuthorizedRustAdapter"
    return result


def analyze_case(request):
    """Check a closed invented adapter case and return complete mathematical facts.

    All caller data is copied after strict bounded JSON validation. Failures raise
    deterministic ValueError codes and expose no partial successful object.
    No analyzer result can authorize instruction/ROM execution or firmware output.
    """
    value = _copy_json(request)
    _closed(value, ["area", "payload"], "AdapterRequestShape")
    _need(type(value["area"]) is str, "AdapterArea")
    handlers = {
        "mapping": _mapping, "admission": _admission, "snapshot": _snapshot,
        "permissions": _permissions, "fetchExit": _fetch_exit, "psw": _psw,
        "evidence": _evidence,
    }
    _need(value["area"] in handlers, "AdapterArea")
    return handlers[value["area"]](value["payload"])
