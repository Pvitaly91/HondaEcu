"""Thirty-two explicit M2bu technical states, not recovered native owners.

The current direct user request explicitly authorizes M2bu; its scope review is
retained privately. Sixteen states (four paths x DD x HC) are each paired with
both internal host-SF booleans. The unchanged M2bt validator is reused only as a
scalar/alias admission predicate, not as a predecessor execution observation.
"""
from collections import Counter
from copy import deepcopy
import json

from original_rom_execution import corpus as previous

MODE = "OriginalRomBytes_TechnicalCallerToExitExecution"
PROVENANCE = previous.PROVENANCE
UNKNOWN_SF = deepcopy(previous.UNKNOWN_SF)
READS_ONE = previous.READS_ONE
ENTRY_PC = 0x54F5
PUBLIC_BASE = 0x6200
PUBLIC_PC_DELTA = PUBLIC_BASE - ENTRY_PC
INVENTORY = previous.INVENTORY
PUBLIC_DATA = {**previous.PUBLIC_DATA, 0x0128: 0x0130}
PREFIX = (0x54F5, 0x54F8, 0x54FA, 0x54FC, 0x54FD, 0x5501)
BUDGETS = {"A": 16, "B": 18, "C": 19, "D": 21, "JbrAlternate": 1, "JneAlternate": 6}
TERMINALS = {"A": 0x55C5, "B": 0x5596, "C": 0x5596, "D": 0x5596,
             "JbrAlternate": 0x5533, "JneAlternate": 0x5503}
WORDS = {"A": (0x0000, 0x007F, 0x00BF, 0x0001),
         "B": (0x00C0, 0x00C1, 0x00FF, 0xFFFF),
         "C": (0x00C0, 0x0100, 0xFFFF, 0x00C1),
         "D": (0x00C0, 0x00FF, 0x0100, 0xFFFF)}


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def word0196(case):
    return case["data"][str(0x0196)] | (case["data"][str(0x0197)] << 8)


def algorithm_path(case):
    data = case["data"]
    return ("A" if word0196(case) < 192 else "B" if data[str(0x012A)] & 128
            else "C" if data[str(0x0124)] & 32 else "D")


def route(case):
    if not case["data"][str(0x0128)] & 4:
        return "JbrAlternate"
    if case["data"][str(0x0117)] == 15:
        return "JneAlternate"
    return algorithm_path(case)


def _as_previous_domain(case):
    """Scalar/alias adapter only; never an actual CPU or execution handoff."""
    value = deepcopy(case)
    value["mode"] = previous.MODE
    value["entry"]["pc"] = previous.ENTRY_PC
    value["path"] = algorithm_path(case)
    value["budget"] = previous.PATH_COUNTS[value["path"]][0]
    return value


def validate_case(case):
    fields = {"kind", "case_id", "family", "mode", "source_classification", "native_input_claimed",
              "entry", "data", "path", "internal_sf", "budget"}
    if type(case) is not dict or set(case) != fields or case["mode"] != MODE:
        raise ValueError("ClosedM2buTechnicalCase")
    if type(case["entry"]) is not dict or case["entry"].get("pc") != ENTRY_PC:
        raise ValueError("NativePredecessorEntryRequired")
    previous.validate_case(_as_previous_domain(case))
    expected = route(case)
    if case["path"] != expected or type(case["budget"]) is not int or case["budget"] != BUDGETS[expected]:
        raise ValueError("PredecessorPredicateOrExactM2buBudgetMismatch")
    return True


def _base(path, index):
    p = "ABCD".index(path)
    dd, hc = index // 2, index % 2
    cf, zf = p & 1, p >> 1
    scb = (2 * p + 2 * dd + hc) % 8
    salt = (0x4D326275 + 0x197 * (4 * p + index)) & 65535
    other = READS_ONE | scb | ((salt ^ (salt >> 3)) & 0x0330)
    psw = other | cf << 15 | zf << 14 | hc << 13 | dd << 12
    word = WORDS[path][index]
    q, x = (0, 14, 16, 255)[index], (0, 255, 128, 127)[index]
    local = [(salt + 37 * number) & 255 for number in range(8)]
    local[0] = (0, 255, 0x33, 0x80)[index]
    if index == 1:
        local[1], local[2], local[3] = q, word & 255, word >> 8
    gate_a = ((salt & 0x7F) | 0x80) if path == "B" else (0, 1, 2, 0x7F)[index]
    gate_b = (salt & 0xDF) | (0x20 if path == "C" else 0)
    if path == "B":
        gate_b = (0, 255, 0x20, 0xDF)[index]
    data = {str(0x0108 + i): value for i, value in enumerate(local)}
    data.update({str(0x0117): q, str(0x0124): gate_b,
                 str(0x0128): ((salt * 3 + 166) & 255) | 4,
                 str(0x012A): gate_a, str(0x018E): x,
                 str(0x018F): (15, 255, 0, 128)[index],
                 str(0x0196): word & 255, str(0x0197): word >> 8})
    a = (word ^ 0xA55A ^ (salt >> 2)) & 65535
    entry = {"pc": ENTRY_PC, "a": a, "al": a & 255, "ah": a >> 8, "psw": psw,
             "cf": bool(cf), "zf": bool(zf), "hc": bool(hc), "dd": bool(dd),
             "other_psw": other, "lrb": 0x21, "scb": scb,
             "ssp": (0x37A1 + 0x239 * (4 * p + index)) & 65535,
             "pointing_banks": [{name: (salt + (bank * 4 + slot + 1) * 0x317) & 65535
                 for slot, name in enumerate(("x1", "x2", "dp", "usp"))} for bank in range(8)],
             "local_r": local, "local_er": [local[2 * i] | local[2 * i + 1] << 8 for i in range(4)],
             "halted": False, "provenance": PROVENANCE, "sf": deepcopy(UNKNOWN_SF)}
    return {"kind": "case", "case_id": f"m2bu-{path.lower()}-{index:02d}", "family": "entry-dd-hc-sf",
            "mode": MODE, "source_classification": "SyntheticOnly", "native_input_claimed": False,
            "entry": entry, "data": data, "path": path, "internal_sf": False, "budget": BUDGETS[path]}


def iter_cases():
    for path in "ABCD":
        for index in range(4):
            for sf in (False, True):
                case = _base(path, index)
                case["internal_sf"] = sf
                case["case_id"] += "-sf1" if sf else "-sf0"
                validate_case(case)
                yield case


def iter_branch_controls():
    for route_name, change in (("JbrAlternate", "gate"), ("JneAlternate", "equality")):
        case = _base("D", 0)
        case["case_id"] = "m2bu-boundary-" + change
        case["family"] = "bounded-predecessor-branch"
        if change == "gate":
            case["data"][str(0x0128)] &= 0xFB
        else:
            case["data"][str(0x0117)] = 15
        case["path"], case["budget"] = route_name, BUDGETS[route_name]
        validate_case(case)
        yield case


def wire_case(case, program_kind="private"):
    validate_case(case)
    if program_kind not in ("private", "public_fixture"):
        raise ValueError("ClosedM2buProgramKind")
    result = deepcopy(case)
    for field in ("mode", "source_classification", "native_input_claimed"):
        del result[field]
    if program_kind == "public_fixture":
        result["entry"]["pc"] += PUBLIC_PC_DELTA
        result["data"] = {str(PUBLIC_DATA.get(int(key), int(key))): value for key, value in result["data"].items()}
    return result


def coverage(cases=None):
    cases = list(iter_cases()) if cases is None else list(cases)
    for case in cases:
        validate_case(case)
    return {"cases": len(cases), "paths": dict(Counter(case["path"] for case in cases)),
            "retirements": sum(case["budget"] for case in cases),
            "incomingFlagVectors": sorted({tuple(int(case["entry"][name]) for name in ("cf", "zf", "hc", "dd")) for case in cases}),
            "scbs": sorted({case["entry"]["scb"] for case in cases}),
            "words": sorted({word0196(case) for case in cases}),
            "physicalSfKnown": False, "nativeGenerationOwnerEstablished": False}
