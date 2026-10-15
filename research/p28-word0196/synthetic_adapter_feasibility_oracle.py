"""Independent M2bl mathematical adapter oracle, sealed before its analyzer.

Inputs are invented abstract claims, never executable bytes or CPU observations.
The fixed geometry, paths, operands and access topology are independently taken
from M2bk/M2bd, M2av C11/IR and M2aw standard-device architecture.  Primary form
pages refer to the September 1991 MSM66201 manual.  The two PSW masks describe
unchanged Rust representation facts, not Rust-produced expected states.

No file/process/network/CPU interface, payload, opcode interpreter or assembler
exists here.  DATA values assigned to invented events are intentionally arbitrary;
this module checks adapter relations, not instruction arithmetic.  Passing these
relations never demonstrates a Rust adapter or execution of the M2bj fragment.
"""

from copy import deepcopy
from hashlib import sha256
import json


MANUAL_SHA256 = "f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271"
COMPOSITE_SHA256 = "91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1"
SOURCE_IDENTITY = "M2bjVerifiedSyntheticComposite_20Nodes_51Bytes"
PROVENANCE = "InventedOnly_NoNativeGenerationOwner"
MODEL_EVIDENCE = "IndependentSyntheticAdapterModel"
ABSTRACT_ACCESS = "InventedAbstractFunctionalDATAAccess_NotObserved"
ABSTRACT_FETCH = "InventedAbstractTransitionRecords_NotCPUTrace"
READS_ONE = 0x0CC8
STORAGE = 0x0337
PSW_PRIMARY_PAGE_SHA256 = "cc0376abbea029239224d015bd63d509540778addf0f23ffd1265f23bd9d1fbd"
# Standard-device users manual page30/31, section3.2.2(1), figure3-5:
# absent bits3/6/7/10/11 read1; writable Other bits9/8/5/4/2/1/0.
# Exact ECU ASIC identity remains unknown; Route A is explicitly conditional.
AREAS = ("mapping", "admission", "snapshot", "permissions", "fetchExit", "psw", "evidence")
DATA_KEYS = ("0108", "0109", "010A", "010B", "010C", "010D", "010E", "010F",
             "0117", "0124", "0128", "012A", "018E", "018F", "0196", "0197")
UNKNOWN_SF = {"status": "SFMeaningStorageNotEstablished", "value": None,
              "meaning": None, "storage": None, "widthBits": None}
FLAGS = (("cf", 32768), ("zf", 16384), ("hc", 8192), ("dd", 4096))
SNAPSHOT_KEYS = ("provenance", "pc", "a", "al", "ah", "psw", "cf", "zf", "hc",
                 "dd", "otherPsw", "lrb", "scb", "ssp", "pointingBanks",
                 "localData", "localAliases", "halted", "sf")


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def _uint(value, maximum, code):
    _require(type(value) is int and 0 <= value <= maximum, code)


def _keys(value, names, code):
    _require(type(value) is dict and set(value) == set(names), code)


def _same(left, right, code):
    # JSON's bool and int are distinct contract types despite Python equality.
    _require(json.dumps(left, sort_keys=True, separators=(",", ":"))
             == json.dumps(right, sort_keys=True, separators=(",", ":")), code)


def _json_value(value, active=None, depth=0, budget=None):
    """Closed primitive boundary; reject cycles/depth before relation checks."""
    if active is None:
        active, budget = [], [0]
    budget[0] += 1
    _require(depth <= 48 and budget[0] <= 20000, "JsonDepthOrNodeLimit")
    if value is None or type(value) in (bool, int):
        return
    if type(value) is str:
        _require(len(value) <= 4096, "JsonStringLimit")
        return
    _require(type(value) in (dict, list), "JsonPrimitiveType")
    _require(len(value) <= 4096, "JsonContainerLimit")
    _require(not any(value is ancestor for ancestor in active), "JsonCycle")
    active.append(value)
    if type(value) is dict:
        for key, child in value.items():
            _require(type(key) is str, "JsonObjectKeyType")
            _json_value(child, active, depth + 1, budget)
    else:
        for child in value:
            _json_value(child, active, depth + 1, budget)
    active.pop()


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True).encode("ascii")).hexdigest()


def _operand(kind, *values):
    result = {"kind": kind}
    if values:
        result["value"] = values[0]
    if len(values) == 2:
        result["bit"] = values[1]
    return result


# Literal reviewed source obligations, never discovered by decoding a stream.
# logical id, PROGRAM pc, FormId, length, primary PDF page, typed operands,
# architectural DD domain, branch/direct target, successor order.
_NODE_ROWS = (
    (0x556F, 0x1000, "lb-a-page", 2, 124,
     (_operand("AccumulatorA"), _operand("PageOffset8", 0x8E)), (0, 1), None, (0x1002,)),
    (0x5571, 0x1002, "sllb-a", 1, 197,
     (_operand("AccumulatorA"),), (0,), None, (0x1003,)),
    (0x5572, 0x1003, "rolb-page", 3, 173,
     (_operand("PageOffset8", 0x8E),), (0, 1), None, (0x1006,)),
    (0x5575, 0x1006, "lb-a-r0", 1, 124,
     (_operand("AccumulatorA"), _operand("Register0", 0)), (0, 1), None, (0x1007,)),
    (0x5576, 0x1007, "andb-a-page", 2, 76,
     (_operand("AccumulatorA"), _operand("PageOffset8", 0x8E)), (0,), None, (0x1009,)),
    (0x5578, 0x1009, "cmp-page-imm16", 5, 90,
     (_operand("EvenPageOffset8", 0x96), _operand("Immediate16", 0x00C0)),
     (0, 1), None, (0x100E,)),
    (0x557D, 0x100E, "jlt-rel8", 2, 120,
     (_operand("TargetPC16", 0x102A),), (0, 1), 0x102A, (0x102A, 0x1010)),
    (0x557F, 0x1010, "movb-r1-page", 3, 153,
     (_operand("Register1", 1), _operand("PageOffset8", 0x17)),
     (0, 1), None, (0x1013,)),
    (0x5582, 0x1013, "andb-page-a", 3, 77,
     (_operand("PageOffset8", 0x17), _operand("AccumulatorA")), (0, 1), None, (0x1016,)),
    (0x5585, 0x1016, "jbs-page-bit7", 3, 119,
     (_operand("PageBit7", 0x2A, 7), _operand("TargetPC16", 0x1023)),
     (0, 1), 0x1023, (0x1023, 0x1019)),
    (0x5588, 0x1019, "jbs-page-bit5", 3, 119,
     (_operand("PageBit5", 0x24, 5), _operand("TargetPC16", 0x1023)),
     (0, 1), 0x1023, (0x1023, 0x101C)),
    (0x558B, 0x101C, "andb-page-a", 3, 77,
     (_operand("PageOffset8", 0x8F), _operand("AccumulatorA")), (0, 1), None, (0x101F,)),
    (0x558E, 0x101F, "orb-page-imm8", 4, 163,
     (_operand("PageOffset8", 0x2A), _operand("Immediate8", 1)),
     (0, 1), None, (0x1023,)),
    (0x5592, 0x1023, "lb-a-page", 2, 124,
     (_operand("AccumulatorA"), _operand("PageOffset8", 0x8F)), (0, 1), None, (0x1025,)),
    (0x5594, 0x1025, "orb-a-imm8", 2, 160,
     (_operand("AccumulatorA"), _operand("Immediate8", 0xF0)), (0,), None, (0x1027,)),
    ("DirectJ_NotBelow", 0x1027, "j-address", 3, 116,
     (_operand("ProgramTarget16", 0x5596),), (0, 1), 0x5596, (0x5596,)),
    (0x55BF, 0x102A, "lb-a-imm8", 2, 124,
     (_operand("AccumulatorA"), _operand("Immediate8", 0x0F)), (0, 1), None, (0x102C,)),
    (0x55C1, 0x102C, "stb-a-page", 2, 208,
     (_operand("AccumulatorA"), _operand("PageOffset8", 0x17)), (0,), None, (0x102E,)),
    (0x55C3, 0x102E, "stb-a-page", 2, 208,
     (_operand("AccumulatorA"), _operand("PageOffset8", 0x8F)), (0,), None, (0x1030,)),
    ("DirectJ_Below", 0x1030, "j-address", 3, 116,
     (_operand("ProgramTarget16", 0x55C5),), (0, 1), 0x55C5, (0x55C5,)),
)

# Uninstantiated manufacturer code-column pattern evidence, never converted to
# octets or populated with this fragment's operands.  Fixed symbolic columns
# are pinned through M2ba/M2bb and direct J through M2bg, independently of Rust.
PRIMARY_PATTERN_COMPONENTS = {
    "lb-a-page": ["FixedF4", "PageOffset8"],
    "sllb-a": ["Fixed53"],
    "rolb-page": ["FixedC4", "PageOffset8", "FixedB7"],
    "lb-a-r0": ["Fixed78"],
    "andb-a-page": ["FixedD7", "PageOffset8"],
    "cmp-page-imm16": ["FixedB4", "EvenPageOffset8", "FixedC0", "Immediate16Low8", "Immediate16High8"],
    "jlt-rel8": ["FixedCA", "SignedRelative8"],
    "movb-r1-page": ["FixedC4", "PageOffset8", "Fixed49"],
    "andb-page-a": ["FixedC4", "PageOffset8", "FixedD1"],
    "jbs-page-bit7": ["FixedEF", "PageOffset8", "SignedRelative8"],
    "jbs-page-bit5": ["FixedED", "PageOffset8", "SignedRelative8"],
    "orb-page-imm8": ["FixedC4", "PageOffset8", "FixedE0", "Immediate8"],
    "orb-a-imm8": ["FixedE6", "Immediate8"],
    "j-address": ["Fixed03", "ProgramTargetLow8", "ProgramTargetHigh8"],
    "lb-a-imm8": ["Fixed77", "Immediate8"],
    "stb-a-page": ["FixedD4", "PageOffset8"],
}

# Primary pattern identities bind exact manufacturer rows without accepting or
# synthesizing code cells.  The private/source validator separately binds sources.
def admission_inventory():
    return [{"nodeIdentity": row[0], "syntheticPc": row[1], "formId": row[2],
             "length": row[3], "typedOperands": deepcopy(list(row[5])),
             "architecturalDd": list(row[6]),
             "reachableDd": [0, 1] if index == 0 else [0],
             "target": row[7], "successors": list(row[8]),
             "primaryPatternEvidence": {
                 "manualSha256": MANUAL_SHA256, "pdfPage": row[4],
                 "patternIdentity": "IM1991:" + row[2] + ":PDF" + str(row[4]),
                 "uninstantiatedPatternComponents": deepcopy(PRIMARY_PATTERN_COMPONENTS[row[2]])},
             "opaqueNodeIdentity": "InventedOpaqueNodeIdentity-" + str(index)}
            for index, row in enumerate(_NODE_ROWS)]


PATH_INDICES = {
    "A": (0, 1, 2, 3, 4, 5, 6, 16, 17, 18, 19),
    "B": (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 13, 14, 15),
    "C": (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 13, 14, 15),
    "D": (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15),
}


def make_segment():
    return {"basePc16": 0x1000, "endExclusive": 0x1033, "exactLength": 51,
            "sourceIdentity": SOURCE_IDENTITY, "immutableContentDigest": COMPOSITE_SHA256,
            "programAddressingMode": "SubtractBase_NoModulo_NoPadding",
            "externalAnchorExclusion": [0x5596, 0x55C5], "paddingBytes": 0,
            "overlappingSegments": [], "evidenceKind": MODEL_EVIDENCE,
            "contentAvailability": "NoExecutableBytes_OpaqueIdentitiesOnly",
            "contentDigestEvidence": "UpstreamIdentityPin_NotMeasuredOpaqueContentDigest",
            "opaqueContent": ["InventedOpaqueCell-" + str(index) for index in range(51)]}


def _validate_segment(segment):
    expected = make_segment()
    _keys(segment, expected, "SegmentSchema")
    for name in ("basePc16", "endExclusive", "exactLength", "paddingBytes"):
        _uint(segment[name], 65536, "SegmentIntegerDomain")
    _require(segment["basePc16"] <= 65535
             and 0 < segment["exactLength"]
             and segment["basePc16"] + segment["exactLength"] <= 65536,
             "SegmentOverflowOrLength")
    _require(segment["endExclusive"] == segment["basePc16"] + segment["exactLength"],
             "SegmentEndRelation")
    _require(type(segment["opaqueContent"]) is list
             and len(segment["opaqueContent"]) == segment["exactLength"], "SegmentContentLength")
    for field in expected:
        _same(segment[field], expected[field], "SegmentBinding:" + field)


def translate_program(segment, requested_pc):
    _validate_segment(segment)
    _uint(requested_pc, 65535, "ProgramPcDomain")
    _require(segment["basePc16"] <= requested_pc < segment["endExclusive"], "ProgramOutOfRange")
    return requested_pc - segment["basePc16"]


def admit_node(node, incoming_dd, source_identity=SOURCE_IDENTITY, content_digest=COMPOSITE_SHA256):
    _uint(incoming_dd, 1, "AdmissionDdDomain")
    _same(source_identity, SOURCE_IDENTITY, "AdmissionSourceIdentity")
    _same(content_digest, COMPOSITE_SHA256, "AdmissionContentDigest")
    _require(type(node) is dict, "AdmissionNodeSchema")
    candidates = [item for item in admission_inventory()
                  if item["syntheticPc"] == node.get("syntheticPc")]
    _require(len(candidates) == 1, "AdmissionUnknownPc")
    expected = candidates[0]
    _same(node, expected, "AdmissionExactNodeRelation")
    _require(incoming_dd in expected["architecturalDd"], "AdmissionArchitecturalDd")
    _require(incoming_dd in expected["reachableDd"], "AdmissionReachableDd")
    return True


def encode_cpu_psw_state(state):
    """Mathematical serialization of masks, not a Rust CPU call."""
    _keys(state, ("storedOther", "cf", "zf", "hc", "dd"), "PswStateSchema")
    _uint(state["storedOther"], 4095, "PswStoredDomain")
    _require(state["storedOther"] & ~STORAGE == 0, "PswStoredMask")
    result = state["storedOther"] + READS_ONE
    for name, mask in FLAGS:
        _uint(state[name], 1, "PswNamedFlagDomain")
        result += mask * state[name]
    return result


def decode_cpu_psw_state(psw):
    _uint(psw, 65535, "PswWordDomain")
    return dict({"storedOther": psw & STORAGE},
                **{name: (psw // mask) % 2 for name, mask in FLAGS})


def check_psw_round_trip(other_psw, named_flags):
    _uint(other_psw, 4095, "OtherPswLow12Domain")
    _keys(named_flags, ("cf", "zf", "hc", "dd"), "PswFlagsSchema")
    for value in named_flags.values():
        _uint(value, 1, "PswNamedFlagDomain")
    requested = other_psw + sum(named_flags[name] * mask for name, mask in FLAGS)
    decoded = decode_cpu_psw_state(requested)
    encoded = encode_cpu_psw_state(decoded)
    compatible = all((other_psw // (2 ** position)) % 2 == 1
                     for position in (3, 6, 7, 10, 11))
    return {"requestedPsw": requested, "otherPsw": other_psw, "namedFlags": deepcopy(named_flags),
            "decodedCpuState": decoded, "encodedPsw": encoded,
            "representable": compatible, "losslessRoundTrip": requested == encoded,
            "changedBits": requested ^ encoded, "readsOneMask": READS_ONE,
            "storageMask": STORAGE,
            "routeA": "ConditionallyAdmissible_SeparateScopeDecisionRequired" if compatible
            else "RejectedInManufacturerCompatibleDomain",
            "routeB": {"losslessResearchOtherPsw": other_psw,
                       "cpuPswRepresentationCompatibleByMathematics": compatible,
                       "runtimeAdapterCompatibility": "NotEstablished"},
            "upstreamOracleDomainChanged": False,
            "fullInventedDomainRuntimeCompatibility": "NotEstablished"}


def _aliases(local):
    return {"r": list(local),
            "er": [local[2 * index] + 256 * local[2 * index + 1] for index in range(4)]}


def make_snapshot(variant=0, dd=0, other_psw=None):
    _uint(variant, 15, "SnapshotVariantDomain")
    _uint(dd, 1, "SnapshotDdDomain")
    if other_psw is None:
        other_psw = ((variant * 0x123) & 0x0FF8) | (variant % 8)
    _uint(other_psw, 4095, "OtherPswLow12Domain")
    flags = {"cf": variant % 2, "zf": (variant // 2) % 2,
             "hc": (variant // 4) % 2, "dd": dd}
    al, ah = (23 + 29 * variant) % 256, (53 + 41 * variant) % 256
    local = [(37 * (index + 1) + 19 * variant) % 256 for index in range(8)]
    result = {"provenance": PROVENANCE, "pc": 0x1000, "a": al + 256 * ah,
              "al": al, "ah": ah, "psw": other_psw + sum(flags[n] * m for n, m in FLAGS),
              "otherPsw": other_psw, "lrb": 0x0021, "scb": other_psw % 8,
              "ssp": (0x0137 + 0x0135 * variant) % 65536,
              "pointingBanks": [{name: (0x1021 * (bank + 1) + 0x0317 * (register + 1)
                                        + 0x0421 * variant) % 65536
                                 for register, name in enumerate(("X1", "X2", "DP", "USP"))}
                                for bank in range(8)],
              "localData": {f"{0x0108 + i:04X}": value for i, value in enumerate(local)},
              "localAliases": _aliases(local), "halted": False, "sf": deepcopy(UNKNOWN_SF)}
    result.update(flags)
    return result


def validate_snapshot(snapshot, route="lossless-research", entry=True):
    _keys(snapshot, SNAPSHOT_KEYS, "SnapshotSchema")
    _same(snapshot["provenance"], PROVENANCE, "SnapshotProvenance")
    for name in ("pc", "a", "psw", "lrb", "ssp"):
        _uint(snapshot[name], 65535, "SnapshotU16:" + name)
    for name in ("al", "ah"):
        _uint(snapshot[name], 255, "SnapshotU8:" + name)
    _uint(snapshot["otherPsw"], 4095, "SnapshotOtherPswDomain")
    _uint(snapshot["scb"], 7, "SnapshotScbDomain")
    _require(snapshot["a"] == snapshot["al"] + 256 * snapshot["ah"], "SnapshotAccumulatorAlias")
    for name, mask in FLAGS:
        _uint(snapshot[name], 1, "SnapshotFlagDomain")
        _require(snapshot[name] == (snapshot["psw"] // mask) % 2, "SnapshotPswFlagAlias")
    _require(snapshot["otherPsw"] == snapshot["psw"] % 4096
             and snapshot["scb"] == snapshot["psw"] % 8, "SnapshotOtherPswScbAlias")
    _require(snapshot["lrb"] == 0x0021, "SnapshotLrb")
    _require(type(entry) is bool, "SnapshotEntryDomain")
    if entry:
        _require(snapshot["pc"] == 0x1000, "SnapshotEntryPc")
    _require(type(snapshot["halted"]) is bool and not snapshot["halted"], "SnapshotHalted")
    _same(snapshot["sf"], UNKNOWN_SF, "SnapshotUnknownSf")
    banks = snapshot["pointingBanks"]
    _require(type(banks) is list and len(banks) == 8, "SnapshotAllEightBanks")
    for bank in banks:
        _keys(bank, ("X1", "X2", "DP", "USP"), "SnapshotPointingBankSchema")
        for value in bank.values():
            _uint(value, 65535, "SnapshotPointingRegisterDomain")
    _keys(snapshot["localData"], DATA_KEYS[:8], "SnapshotLocalDataSchema")
    for value in snapshot["localData"].values():
        _uint(value, 255, "SnapshotLocalDataDomain")
    local = [snapshot["localData"][key] for key in DATA_KEYS[:8]]
    _same(snapshot["localAliases"], _aliases(local), "SnapshotLocalAlias")
    _require(route in ("lossless-research", "manufacturer-compatible"), "SnapshotRoute")
    psw = check_psw_round_trip(snapshot["otherPsw"], {n: snapshot[n] for n, _ in FLAGS})
    if route == "manufacturer-compatible":
        _require(psw["representable"], "SnapshotPswNotRepresentable")
    return {"schema": "SyntheticCpuEntrySnapshot", "complete": True, "pointingBankCount": 8,
            "activeBank": snapshot["scb"], "localBankBase": 0x0108,
            "currentPage": 0x0100, "aliasEr0": local[0] + 256 * local[1],
            "route": route, "pswRepresentable": psw["representable"],
            "sf": deepcopy(UNKNOWN_SF), "upstreamOracleDomainChanged": False}


def validate_preserved_context(before, after):
    validate_snapshot(before)
    validate_snapshot(after, entry=False)
    fields = ("ah", "hc", "otherPsw", "lrb", "scb", "ssp", "pointingBanks", "halted", "sf")
    for field in fields:
        _same(before[field], after[field], "PreservedContext:" + field)
    for key in DATA_KEYS[:8]:
        if key != "0109":
            _same(before["localData"][key], after["localData"][key], "PreservedLocalByte:" + key)
    return {"preservedFields": list(fields), "allEightBanksPreserved": True,
            "ahPreserved": True, "sspPreserved": True,
            "r1Er0HighMayChangeOnlyThroughReviewedDataWrite": True}


def data_permissions(path):
    _require(type(path) is str and path in PATH_INDICES, "DataPath")
    reads = [0x0108, 0x018E, 0x0196, 0x0197]
    writes = [0x018E, 0x0117, 0x018F] if path == "A" else [0x018E, 0x0109, 0x0117]
    if path != "A":
        reads += [0x0117, 0x012A, 0x018F]
    if path in ("C", "D"):
        reads.append(0x0124)
    if path == "D":
        writes += [0x018F, 0x012A]
    return {"path": path, "readPermissions": sorted(reads), "writePermissions": sorted(writes),
            "seedInitializationAccess": [int(key, 16) for key in DATA_KEYS],
            "diagnosticSnapshotRead": [int(key, 16) for key in DATA_KEYS],
            "functionalEvidence": "ExpectedModelOnly_NotActualJournal"}


# Logical access identity/type/address/width; no arithmetic or opcode dispatch.
_COMMON_ACCESS = ((0x556F, "Read", 0x018E, 8),
                  (0x5572, "Read", 0x018E, 8), (0x5572, "Write", 0x018E, 8),
                  (0x5575, "Read", 0x0108, 8), (0x5576, "Read", 0x018E, 8),
                  (0x5578, "Read", 0x0196, 16))
_NOT_BELOW_ACCESS = ((0x557F, "Read", 0x0117, 8), (0x557F, "Write", 0x0109, 8),
                     (0x5582, "Read", 0x0117, 8), (0x5582, "Write", 0x0117, 8),
                     (0x5585, "Read", 0x012A, 8))


def _access_topology(path):
    _require(path in PATH_INDICES, "DataPath")
    if path == "A":
        return _COMMON_ACCESS + ((0x55C1, "Write", 0x0117, 8), (0x55C3, "Write", 0x018F, 8))
    result = _COMMON_ACCESS + _NOT_BELOW_ACCESS
    if path in ("C", "D"):
        result += ((0x5588, "Read", 0x0124, 8),)
    if path == "D":
        result += ((0x558B, "Read", 0x018F, 8), (0x558B, "Write", 0x018F, 8),
                   (0x558E, "Read", 0x012A, 8), (0x558E, "Write", 0x012A, 8))
    return result + ((0x5592, "Read", 0x018F, 8),)


def make_data_case(path="A", variant=0):
    _uint(variant, 15, "DataVariant")
    permissions = data_permissions(path)
    initial = {key: (index * 31 + variant * 7 + 5) % 256 for index, key in enumerate(DATA_KEYS)}
    working, events, ordinal = deepcopy(initial), [], 0
    for index, (node, kind, address, width) in enumerate(_access_topology(path)):
        key, old = f"{address:04X}", working[f"{address:04X}"]
        event = {"eventIndex": index + 1, "nodeIdentity": node, "kind": kind,
                 "space": "DATA", "address": address, "widthBits": width,
                 "classification": ABSTRACT_ACCESS}
        if kind == "Read":
            cells = [old] if width == 8 else [old, working[f"{address + 1:04X}"]]
            event.update({"value": sum(value * 256 ** i for i, value in enumerate(cells)),
                          "rawByteReads": [{"address": address + i, "value": value}
                                           for i, value in enumerate(cells)]})
        else:
            ordinal += 1
            # An abstract invented store; first is deliberately a same-value RMW.
            new = old if ordinal == 1 else (old + ordinal * 11 + variant) % 256
            if address == 0x0109:
                new = initial["0117"]  # reviewed local r1 copy/er0 alias relation
            event.update({"oldValue": old, "value": new, "writeOrdinal": ordinal,
                          "sameValue": old == new})
            working[key] = new
        events.append(event)
    return {"path": path, "initialData": initial, "events": events, "finalData": working,
            "finalLocalAliases": _aliases([working[key] for key in DATA_KEYS[:8]]),
            "readPermissions": permissions["readPermissions"],
            "writePermissions": permissions["writePermissions"],
            "seedInitializationAccess": permissions["seedInitializationAccess"],
            "diagnosticSnapshotRead": permissions["diagnosticSnapshotRead"],
            "classification": "InventedAdapterRelations_NoInstructionArithmetic"}


def validate_data_events(case):
    _keys(case, ("path", "initialData", "events", "finalData", "finalLocalAliases",
                 "readPermissions", "writePermissions", "seedInitializationAccess",
                 "diagnosticSnapshotRead", "classification"), "DataCaseSchema")
    permissions = data_permissions(case["path"])
    _same(case["readPermissions"], permissions["readPermissions"], "DataReadPermissionPolicyRelation")
    _same(case["writePermissions"], permissions["writePermissions"], "DataWritePermissionPolicyRelation")
    _same(case["classification"], "InventedAdapterRelations_NoInstructionArithmetic", "DataEvidence")
    for field in ("seedInitializationAccess", "diagnosticSnapshotRead"):
        _same(case[field], permissions[field], "DataAccessCategory:" + field)
    _keys(case["initialData"], DATA_KEYS, "DataInitialInventory")
    for value in case["initialData"].values():
        _uint(value, 255, "DataByteDomain")
    _require(type(case["events"]) is list, "DataEventsList")
    topology = _access_topology(case["path"])
    _require(len(case["events"]) == len(topology), "DataExactEventCount")
    memory, ordinal, reads, same_value = deepcopy(case["initialData"]), 0, 0, 0
    for index, (event, expected) in enumerate(zip(case["events"], topology)):
        node, kind, address, width = expected
        common = ("eventIndex", "nodeIdentity", "kind", "space", "address", "widthBits", "classification", "value")
        _keys(event, common + (("rawByteReads",) if kind == "Read"
                              else ("oldValue", "writeOrdinal", "sameValue")), "DataEventSchema")
        _same([event["eventIndex"], event["nodeIdentity"], event["kind"], event["address"], event["widthBits"]],
              [index + 1, node, kind, address, width], "DataOrderedAccessRelation")
        _same(event["space"], "DATA", "DataSpace")
        _same(event["classification"], ABSTRACT_ACCESS, "DataFunctionalCategory")
        permitted = permissions["readPermissions" if kind == "Read" else "writePermissions"]
        _require(all(cell in permitted for cell in range(address, address + width // 8)), "DataPermission")
        key = f"{address:04X}"
        if kind == "Read":
            reads += 1
            cells = [{"address": cell, "value": memory[f"{cell:04X}"]}
                     for cell in range(address, address + width // 8)]
            _same(event["rawByteReads"], cells, "DataRawReadOrderAndValues")
            weighted = sum(item["value"] * 256 ** i for i, item in enumerate(cells))
            _same(event["value"], weighted, "DataLittleEndianReadRelation")
        else:
            ordinal += 1
            _uint(event["value"], 255, "DataWrittenByteDomain")
            _same(event["oldValue"], memory[key], "DataStoreOldValue")
            _same(event["writeOrdinal"], ordinal, "DataFreshStoreOrdinal")
            _same(event["sameValue"], event["value"] == memory[key], "DataSameValueIdentity")
            same_value += int(event["sameValue"])
            if address == 0x0109:
                _same(event["value"], case["initialData"]["0117"], "DataR1CopyRelation")
            memory[key] = event["value"]
    _same(case["finalData"], memory, "DataFinalMemoryRelation")
    _same(case["finalLocalAliases"], _aliases([memory[key] for key in DATA_KEYS[:8]]), "DataLocalAliasRelation")
    return dict(permissions, logicalReadCount=reads, writeCount=ordinal,
                sameValueWrites=same_value, word0196=case["initialData"]["0196"]
                + 256 * case["initialData"]["0197"], finalData=memory,
                finalLocalAliases=deepcopy(case["finalLocalAliases"]),
                eventDigest=_digest(case["events"]), actualFunctionalJournal="NotRun")


def make_fetch_case(path="A", variant=0):
    _uint(variant, 15, "FetchVariant")
    _require(path in PATH_INDICES, "FetchPath")
    inventory, segment, events, raw_sequence = admission_inventory(), make_segment(), [], 0
    selected = [inventory[index] for index in PATH_INDICES[path]]
    for index, node in enumerate(selected):
        pc, length = node["syntheticPc"], node["length"]
        raw = []
        for address in range(pc, pc + length):
            raw_sequence += 1
            raw.append({"sequence": raw_sequence, "requestedPc": address,
                        "offset": address - 0x1000, "purpose": "ArchitecturalSelectedFetch",
                        "opaqueIdentity": segment["opaqueContent"][address - 0x1000]})
        # Bounded retained lookahead is diagnostic, never an executed node.
        if index == 0:
            raw_sequence += 1
            address = pc + length
            raw.append({"sequence": raw_sequence, "requestedPc": address,
                        "offset": address - 0x1000, "purpose": "DecoderLookahead",
                        "opaqueIdentity": segment["opaqueContent"][address - 0x1000]})
        next_pc = selected[index + 1]["syntheticPc"] if index + 1 < len(selected) else node["target"]
        branch = (next_pc == node["target"]) if node["formId"] in (
            "jlt-rel8", "jbs-page-bit7", "jbs-page-bit5") else None
        external = node["formId"] == "j-address"
        events.append({"step": index + 1, "entryPc": pc, "selectedLength": length,
                       "selectedExtent": {"space": "PROGRAM", "start": pc, "endExclusive": pc + length},
                       "rawProgramReads": raw, "decodedInstruction": {
                           "nodeIdentity": node["nodeIdentity"], "formId": node["formId"], "length": length,
                           "classification": "InventedDecodedIdentityClaim_NotDecoderOutput"},
                       "incomingDd": variant % 2 if index == 0 else 0,
                       "nextPc": next_pc, "branchDecision": branch,
                       "externalTransfer": {"kind": "DirectJ", "target": next_pc} if external else None,
                       "classification": ABSTRACT_FETCH})
    exit_pc = 0x55C5 if path == "A" else 0x5596
    return {"entryPc": 0x1000, "path": path, "events": events,
            "rawProgramObservationLedger": [deepcopy(raw) for event in events
                                             for raw in event["rawProgramReads"]],
            "stop": {"afterStep": len(events), "pc": exit_pc,
                     "exitIdentity": "Below" if path == "A" else "NotBelow",
                     "reason": "StopAfterOneDirectJBeforeExternalFetch"},
            "postStopProgramReads": [], "classification": ABSTRACT_FETCH}


def validate_fetch_case(case):
    _keys(case, ("entryPc", "path", "events", "rawProgramObservationLedger", "stop",
                 "postStopProgramReads", "classification"), "FetchCaseSchema")
    _same(case["entryPc"], 0x1000, "FetchEntryPc")
    _same(case["classification"], ABSTRACT_FETCH, "FetchEvidenceClassification")
    _require(type(case["path"]) is str and case["path"] in PATH_INDICES, "FetchPath")
    nodes = [admission_inventory()[i] for i in PATH_INDICES[case["path"]]]
    _require(type(case["events"]) is list and len(case["events"]) == len(nodes), "FetchExactExecutedCount")
    segment, raw_all, selected_extents, lookahead, direct_j = make_segment(), [], [], 0, 0
    for index, (event, node) in enumerate(zip(case["events"], nodes)):
        _keys(event, ("step", "entryPc", "selectedLength", "selectedExtent", "rawProgramReads",
                      "decodedInstruction", "incomingDd", "nextPc", "branchDecision",
                      "externalTransfer", "classification"), "FetchEventSchema")
        _same(event["classification"], ABSTRACT_FETCH, "FetchEventEvidence")
        _same([event["step"], event["entryPc"], event["selectedLength"]],
              [index + 1, node["syntheticPc"], node["length"]], "FetchSelectedInstructionRelation")
        admit_node(node, event["incomingDd"])
        extent = {"space": "PROGRAM", "start": node["syntheticPc"],
                  "endExclusive": node["syntheticPc"] + node["length"]}
        _same(event["selectedExtent"], extent, "FetchSelectedExtent")
        selected_extents.append(extent)
        _same(event["decodedInstruction"], {"nodeIdentity": node["nodeIdentity"],
              "formId": node["formId"], "length": node["length"],
              "classification": "InventedDecodedIdentityClaim_NotDecoderOutput"}, "FetchDecodedIdentity")
        next_pc = nodes[index + 1]["syntheticPc"] if index + 1 < len(nodes) else node["target"]
        _same(event["nextPc"], next_pc, "FetchReviewedPathSuccessor")
        is_branch = node["formId"] in ("jlt-rel8", "jbs-page-bit7", "jbs-page-bit5")
        _same(event["branchDecision"], next_pc == node["target"] if is_branch else None,
              "FetchBranchDecision")
        is_j = node["formId"] == "j-address"
        _same(event["externalTransfer"], {"kind": "DirectJ", "target": next_pc} if is_j else None,
              "FetchDirectJTransfer")
        direct_j += int(is_j)
        _require(type(event["rawProgramReads"]) is list, "FetchRawReadsList")
        architectural = []
        for raw in event["rawProgramReads"]:
            _keys(raw, ("sequence", "requestedPc", "offset", "purpose", "opaqueIdentity"), "FetchRawSchema")
            offset = translate_program(segment, raw["requestedPc"])
            _same([raw["sequence"], raw["offset"], raw["opaqueIdentity"]],
                  [len(raw_all) + 1, offset, segment["opaqueContent"][offset]], "FetchRawTranslationAndOrder")
            _require(raw["purpose"] in ("ArchitecturalSelectedFetch", "DecoderLookahead", "DiagnosticProgramProbe"),
                     "FetchRawPurpose")
            if raw["purpose"] == "ArchitecturalSelectedFetch":
                architectural.append(raw["requestedPc"])
            else:
                lookahead += 1
            raw_all.append(deepcopy(raw))
        _same(architectural, list(range(extent["start"], extent["endExclusive"])), "FetchArchitecturalSelectedExtent")
    _require(direct_j == 1, "FetchExactlyOneDirectJ")
    _same(case["rawProgramObservationLedger"], raw_all, "FetchCompleteRawObservationLedger")
    terminal = 0x55C5 if case["path"] == "A" else 0x5596
    _same(case["stop"], {"afterStep": len(nodes), "pc": terminal,
          "exitIdentity": "Below" if case["path"] == "A" else "NotBelow",
          "reason": "StopAfterOneDirectJBeforeExternalFetch"}, "FetchExitStopIdentity")
    _same(case["postStopProgramReads"], [], "FetchStopBeforeNextProbe")
    return {"path": case["path"], "instructionCount": len(nodes), "directJCount": direct_j,
            "terminalPc": terminal, "selectedExtents": selected_extents,
            "rawProgramReads": raw_all, "lookaheadOrDiagnosticReadCount": lookahead,
            "rawProgramReadCount": len(raw_all), "externalProgramReadCount": 0,
            "cpuExecutionCount": 0, "runtimeExitIsolation": "NotEstablished",
            "classification": "FetchAndExternalTrapContractVerified"}


def _evidence_case():
    return {"evidenceLevel": MODEL_EVIDENCE, "rustAdapterImplementation": "NotRun",
            "syntheticCpuExecutionCount": 0, "originalRomExecutionCount": 0,
            "targetCpuExecution": "NotObserved", "firmwareReady": False,
            "nativeExitIsolation": "NotEstablished", "physicalRomPlacement": "NotEstablished",
            "targetProgramEquivalence": "NotEstablished", "actualDownstreamRejoin": "NotEstablished",
            "firmwareIntegration": "NotEstablished", "targetObjectCount": 0,
            "hexCount": 0, "firmwareBinCount": 0}


def make_case(area, variant=0):
    _require(type(area) is str and area in AREAS, "CaseArea")
    _uint(variant, 15, "CaseVariant")
    path = "ABCD"[variant % 4]
    if area == "mapping":
        offset = (variant * 7) % 51
        payload = {"segment": make_segment(), "requestedPc": 0x1000 + offset,
                   "claimedOffset": offset}
    elif area == "admission":
        payload = {"sourceIdentity": SOURCE_IDENTITY, "immutableContentDigest": COMPOSITE_SHA256,
                   "nodes": admission_inventory(), "entryDd": variant % 2}
    elif area == "snapshot":
        before = make_snapshot(variant, variant % 2)
        after = deepcopy(before)
        after["pc"] = 0x55C5 if path == "A" else 0x5596
        after["al"] = (after["al"] + 17) % 256
        after["a"] = after["al"] + 256 * after["ah"]
        after["dd"] = 0
        after["psw"] = after["otherPsw"] + sum(after[name] * mask for name, mask in FLAGS)
        payload = {"before": before, "after": after, "route": "lossless-research"}
    elif area == "permissions":
        payload = make_data_case(path, variant)
    elif area == "fetchExit":
        payload = make_fetch_case(path, variant)
    elif area == "psw":
        payload = {"otherPsw": ((variant * 0x123) | READS_ONE) % 4096,
                   "namedFlags": {name: (variant // (2 ** index)) % 2
                                  for index, (name, _) in enumerate(FLAGS)}}
    else:
        payload = _evidence_case()
    return {"area": area, "payload": payload}


def reference_case(request):
    """Closed JSON-native request -> independent expected mathematical result."""
    _json_value(request)
    _keys(request, ("area", "payload"), "RequestSchema")
    area, payload = request["area"], request["payload"]
    _require(type(area) is str and area in AREAS, "CaseArea")
    if area == "mapping":
        _keys(payload, ("segment", "requestedPc", "claimedOffset"), "MappingRequestSchema")
        offset = translate_program(payload["segment"], payload["requestedPc"])
        _uint(payload["claimedOffset"], 50, "ProgramClaimedOffsetDomain")
        _same(payload["claimedOffset"], offset, "ProgramOffsetSubtractionRelation")
        return {"classification": "SyntheticSegmentAddressTranslationModelVerified",
                "requestedPc": payload["requestedPc"], "offset": offset,
                "opaqueIdentity": payload["segment"]["opaqueContent"][offset],
                "contentDigestMeasured": False, "paddingBytes": 0,
                "rustSegmentMapping": "NotImplemented", "evidenceKind": MODEL_EVIDENCE}
    if area == "admission":
        _keys(payload, ("sourceIdentity", "immutableContentDigest", "nodes", "entryDd"), "AdmissionRequestSchema")
        _uint(payload["entryDd"], 1, "AdmissionDdDomain")
        _require(type(payload["nodes"]) is list and len(payload["nodes"]) == 20, "AdmissionExactInventoryCount")
        expected = admission_inventory()
        _same([item.get("syntheticPc") if type(item) is dict else None for item in payload["nodes"]],
              [item["syntheticPc"] for item in expected], "AdmissionExactInventoryOrder")
        for index, node in enumerate(payload["nodes"]):
            admit_node(node, payload["entryDd"] if index == 0 else 0,
                       payload["sourceIdentity"], payload["immutableContentDigest"])
        return {"classification": "Closed16FormAdmissionModelVerified", "nodeCount": 20,
                "originalNodeCount": 18, "exactFormCount": 16,
                "forms": sorted({item["formId"] for item in expected}),
                "nodes": expected, "entryDd": payload["entryDd"],
                "runtimeAdmission": "NotImplemented"}
    if area == "snapshot":
        _keys(payload, ("before", "after", "route"), "SnapshotRequestSchema")
        result = validate_snapshot(payload["before"], payload["route"])
        result["preservation"] = validate_preserved_context(payload["before"], payload["after"])
        return result
    if area == "permissions":
        return validate_data_events(payload)
    if area == "fetchExit":
        return validate_fetch_case(payload)
    if area == "psw":
        _keys(payload, ("otherPsw", "namedFlags"), "PswRequestSchema")
        return check_psw_round_trip(payload["otherPsw"], payload["namedFlags"])
    _same(payload, _evidence_case(), "EvidenceAuthorityRefusal")
    return dict(_evidence_case(), classification="EvidenceBoundaryVerified",
                actualSyntheticExecution="BlockedPendingSeparatelyAuthorizedRustAdapter")


def self_check():
    """Independent literal and relation checks, without analyzer or CPU output."""
    aggregate, cases, refusals = sha256(), 0, []

    def positive(request):
        nonlocal cases
        original = deepcopy(request)
        result = reference_case(request)
        _same(request, original, "OracleMutatedInput")
        aggregate.update(json.dumps(result, sort_keys=True, separators=(",", ":")).encode("ascii"))
        cases += 1
        return result

    def refuse(label, request):
        original = deepcopy(request)
        try:
            reference_case(request)
        except ValueError as error:
            _same(request, original, "OracleRefusalMutatedInput")
            refusals.append({"label": label, "code": str(error)})
            return
        raise AssertionError("Oracle accepted mutation: " + label)

    # Geometry: every valid byte and several boundaries, no executable content.
    for pc in range(0x1000, 0x1033):
        case = make_case("mapping")
        case["payload"]["requestedPc"] = pc
        case["payload"]["claimedOffset"] = pc - 0x1000
        result = positive(case)
        _require(result["offset"] == pc - 4096, "OracleMappingLiteral")
    for pc in (0x0FFF, 0x1033, 0x5596, 0x55C5, 65536, -1):
        case = make_case("mapping")
        case["payload"]["requestedPc"] = pc
        refuse("program-range-" + str(pc), case)
    case = make_case("mapping")
    case["payload"]["claimedOffset"] = 1
    refuse("program-base-mapped-to-wrong-offset", case)
    case = make_case("mapping")
    case["payload"]["requestedPc"] = 0x1032
    case["payload"]["claimedOffset"] = 49
    refuse("program-last-byte-off-by-one", case)
    for field, value in (("basePc16", 0), ("basePc16", 65530), ("exactLength", 0),
                         ("exactLength", 52), ("paddingBytes", 4096),
                         ("endExclusive", 0x1032), ("overlappingSegments", [{"base": 4096, "end": 4097}]),
                         ("sourceIdentity", "OriginalROM"), ("immutableContentDigest", "0" * 64)):
        case = make_case("mapping")
        case["payload"]["segment"][field] = value
        refuse("segment-" + field + "-" + str(value), case)
    for dd in (0, 1):
        case = make_case("admission", dd)
        result = positive(case)
        _require((result["nodeCount"], result["exactFormCount"]) == (20, 16), "OracleInventoryLiteral")
    node_dd_checks = 0
    for index, node in enumerate(admission_inventory()):
        for dd in (0, 1):
            expected_admission = index == 0 or dd == 0
            try:
                admit_node(node, dd)
                admitted = True
            except ValueError:
                admitted = False
            _require(admitted == expected_admission, "OracleReachableDdLiteral")
            node_dd_checks += 1
    for field, value in (("formId", "job-j"), ("formId", "sj-rel8"), ("formId", "cal-address"),
                         ("formId", "rt"), ("formId", "j"), ("length", 2),
                         ("target", 0x55C5), ("opaqueNodeIdentity", "ModifiedOpaqueIdentity")):
        case = make_case("admission")
        case["payload"]["nodes"][15][field] = value
        refuse("admission-direct-j-" + field + "-" + str(value), case)
    for field, value in (("typedOperands", []), ("primaryPatternEvidence", {}),
                         ("formId", "nop"), ("syntheticPc", 0x1001)):
        case = make_case("admission")
        case["payload"]["nodes"][0][field] = value
        refuse("admission-exact-" + field, case)
    for change in ("extra", "missing", "unknown-dd"):
        case = make_case("admission")
        if change == "extra":
            case["payload"]["nodes"].append(deepcopy(case["payload"]["nodes"][0]))
        elif change == "missing":
            case["payload"]["nodes"].pop()
        else:
            case["payload"]["entryDd"] = None
        refuse("admission-" + change, case)
    for variant in range(16):
        for area in ("snapshot", "permissions", "fetchExit", "evidence"):
            positive(make_case(area, variant))
    for field, value in (("scb", 7), ("psw", 1), ("sf", False), ("ah", 0), ("ssp", 0)):
        case = make_case("snapshot")
        case["payload"]["after"][field] = value
        refuse("snapshot-" + field, case)
    case = make_case("snapshot")
    case["payload"]["before"]["pointingBanks"].pop()
    refuse("snapshot-missing-bank", case)
    case = make_case("snapshot")
    case["payload"]["after"]["pointingBanks"][7]["USP"] += 1
    refuse("snapshot-unselected-bank-clobber", case)
    case = make_case("snapshot")
    case["payload"]["after"]["localAliases"]["er"][0] += 256
    refuse("snapshot-r1-alias", case)
    case = make_case("snapshot")
    case["payload"]["route"] = "manufacturer-compatible"
    refuse("snapshot-incompatible-psw-not-normalized", case)
    # Relation mutations reach actual ordered data/LE/alias/ordinal checks.
    for label in ("read-as-write", "unauthorized-read", "unauthorized-write", "word-reversed",
                  "immediate-as-data", "same-value-removed", "r1-alias-broken", "diagnostic-in-journal",
                  "r1-copy-broken"):
        case = make_case("permissions", 1)
        payload = case["payload"]
        if label == "read-as-write":
            payload["events"][0]["kind"] = "Write"
        elif label == "unauthorized-read":
            payload["events"][0]["address"] = 0x0128
        elif label == "unauthorized-write":
            payload["events"][2]["address"] = 0x0196
        elif label == "word-reversed":
            payload["events"][5]["rawByteReads"].reverse()
        elif label == "immediate-as-data":
            payload["events"][5]["address"] = 0x00C0
        elif label == "same-value-removed":
            payload["events"].pop(2)
        elif label == "r1-alias-broken":
            payload["finalLocalAliases"]["er"][0] += 256
        elif label == "diagnostic-in-journal":
            payload["events"][0]["classification"] = "DiagnosticSnapshotRead"
        else:
            payload["events"][7]["value"] ^= 1
        refuse("data-" + label, case)
    for path_variant, forbidden in ((1, 0x0124), (1, 0x012A), (2, 0x012A)):
        case = make_case("permissions", path_variant)
        case["payload"]["events"][2]["address"] = forbidden
        refuse("data-forbidden-path-" + str(path_variant) + "-" + str(forbidden), case)
    for field, changed in (("writePermissions", "read-as-write"),
                           ("readPermissions", "write-as-read"),
                           ("writePermissions", "extra-readonly-write"),
                           ("readPermissions", "suppressed-gate-read")):
        case = make_case("permissions", 1)
        payload = case["payload"]
        if changed == "read-as-write":
            payload[field] = deepcopy(payload["readPermissions"])
        elif changed == "write-as-read":
            payload[field] = deepcopy(payload["writePermissions"])
        else:
            payload[field].append(0x0196 if changed == "extra-readonly-write" else 0x0124)
            payload[field].sort()
        refuse("data-policy-" + changed, case)
    for label in ("lookahead-executed", "selected-extent-lost", "external-probe", "post-stop-probe",
                  "return-for-j", "two-j", "wrong-branch", "entry-anchor", "fake-stop", "raw-read-hidden"):
        case = make_case("fetchExit", 1)
        payload = case["payload"]
        if label == "lookahead-executed":
            payload["events"][0]["rawProgramReads"][-1]["purpose"] = "ArchitecturalSelectedFetch"
        elif label == "selected-extent-lost":
            payload["events"][0]["selectedExtent"] = None
        elif label == "external-probe":
            payload["events"][-1]["rawProgramReads"][-1]["requestedPc"] = 0x5596
        elif label == "post-stop-probe":
            payload["postStopProgramReads"] = [{"requestedPc": 0x5596}]
        elif label == "return-for-j":
            payload["events"][-1]["externalTransfer"]["kind"] = "Return"
        elif label == "two-j":
            payload["events"].append(deepcopy(payload["events"][-1]))
        elif label == "wrong-branch":
            payload["events"][6]["nextPc"] = 0x102A
        elif label == "entry-anchor":
            payload["entryPc"] = 0x5596
        elif label == "fake-stop":
            payload["stop"]["afterStep"] -= 1
        else:
            payload["events"][0]["rawProgramReads"].pop(0)
        refuse("fetch-" + label, case)
    representable, incompatible, combinations, psw_digest = 0, 0, 0, sha256()
    for other in range(4096):
        literal_compatible = (other & READS_ONE) == READS_ONE
        representable += int(literal_compatible)
        incompatible += int(not literal_compatible)
        for flags_value in range(16):
            flags = {name: (flags_value >> index) & 1 for index, (name, _) in enumerate(FLAGS)}
            result = check_psw_round_trip(other, flags)
            _require(result["representable"] == literal_compatible
                     and result["losslessRoundTrip"] == literal_compatible, "OraclePswCompatibility")
            _require(result["decodedCpuState"]["storedOther"] == (other & STORAGE), "OraclePswStorage")
            _require(result["encodedPsw"] % 4096 == ((other & STORAGE) | READS_ONE), "OraclePswReadsOne")
            _require(all(result["decodedCpuState"][name] == flags[name] for name, _ in FLAGS), "OraclePswFlags")
            psw_digest.update(json.dumps(result, sort_keys=True, separators=(",", ":")).encode("ascii"))
            combinations += 1
    _require((representable, incompatible, combinations) == (128, 3968, 65536), "OraclePswDomainLiteral")
    for field, value in (("otherPsw", 0x1000), ("otherPsw", True), ("namedFlags", {"cf": 2, "zf": 0, "hc": 0, "dd": 0})):
        case = make_case("psw")
        case["payload"][field] = value
        refuse("psw-domain-" + field + "-" + str(value), case)
    metadata_start = len(refusals)
    for field, value in (("evidenceLevel", "FutureSyntheticCPUExecution"),
                         ("rustAdapterImplementation", "Pass"), ("syntheticCpuExecutionCount", 1),
                         ("firmwareReady", True)):
        case = make_case("evidence")
        case["payload"][field] = value
        refuse("authority-" + field, case)
    cycle = []
    cycle.append(cycle)
    deep = 0
    for _ in range(50):
        deep = [deep]
    boundary_checks = 0
    for invalid in ((1, 2), 0.5, {1: "nonstring-key"}, cycle, deep):
        try:
            reference_case(invalid)
        except ValueError:
            boundary_checks += 1
    _require(boundary_checks == 5, "OracleJsonBoundaryRefusals")
    metadata_only = [item for item in refusals if item["label"].startswith("authority-")
                     or item["label"].startswith("segment-sourceIdentity-")
                     or item["label"].startswith("segment-immutableContentDigest-")]
    return {"classification": "IndependentAdapterOracleSelfCheckPass",
            "modelPositiveCases": cases, "programTranslationCases": 51,
            "exactNodes": 20, "exactForms": 16, "allEightBanks": True,
            "nodeDdContextChecks": node_dd_checks, "jsonBoundaryRefusalCount": boundary_checks,
            "pswLow12Cases": 4096, "pswRepresentableLow12": representable,
            "pswIncompatibleLow12": incompatible, "namedFlagCombinations": 16,
            "pswCartesianCases": combinations, "pswRepresentableCartesian": representable * 16,
            "pswIncompatibleCartesian": incompatible * 16,
            "relationRefusalCount": len(refusals) - len(metadata_only),
            "metadataRefusalCount": len(metadata_only),
            "authorityRefusalCount": len(refusals) - metadata_start,
            "metadataOnlyRefusalLabels": [item["label"] for item in metadata_only],
            "refusals": refusals, "expectationDigest": aggregate.hexdigest(),
            "pswExpectationDigest": psw_digest.hexdigest(),
            "analyzerCalls": 0, "cpuExecutions": 0, "programPayloadBytes": 0,
            "rustExpectedStatesUsed": 0, "upstreamOracleDomainChanged": False}
