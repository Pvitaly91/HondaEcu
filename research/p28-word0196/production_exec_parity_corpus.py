"""M2bo finite invented microprobe inputs, frozen before production execution.

Only the already sealed M2bm instruction/operand bytes are admitted. Additional
contexts vary DATA/register/representable PSW inputs, never instruction bytes.
Importing or generating the corpus performs no CPU execution or compilation.
"""

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_SHA = "50dfe6b0ee814caddb69eaaa9c01936d9894bed5"
FIXTURE_PATH = "rust-synthetic-adapter/tests/fixtures/microprobe_expectations.json"
FIXTURE_SHA = "7535b5edc203b759d8049a5905328695e0591a7cb7d874519d3f73a8646db343"
PROVENANCE = "InventedOnly_NoNativeGenerationOwner"
UNKNOWN_SF = {"status": "SFMeaningStorageNotEstablished", "value": None,
              "meaning": None, "storage": None, "width_bits": None}
READS_ONE = 0x0CC8
RAM_START, RAM_END, SCRATCH = 0x80, 0x1000, 0xA5
BYTE_EDGES = (0, 1, 127, 128, 255)
WORD_EDGES = (0, 191, 192, 193, 65535)
FAMILY_COUNTS = {"sealed-m2bm": 51, "flags-scb": 128,
                 "byte-edges": 50, "cmp-word-boundaries": 5}
DD_ZERO_FORMS = frozenset(("sllb-a", "andb-a-page", "orb-a-imm8", "stb-a-page"))
BYTE_EDGE_FORMS = ("lb-a-page", "sllb-a", "rolb-page", "lb-a-r0",
                   "andb-a-page", "movb-r1-page", "andb-page-a",
                   "orb-page-imm8", "orb-a-imm8", "stb-a-page")
FROZEN_DECODED_INDICES = {
    "lb-a-page": 747, "sllb-a": 2198, "rolb-page": 1862, "lb-a-r0": 739,
    "andb-a-page": 333, "cmp-page-imm16": 498, "jlt-rel8": 719,
    "movb-r1-page": 1504, "andb-page-a": 349, "jbs-page-bit7": 716,
    "jbs-page-bit5": 714, "orb-page-imm8": 1678, "orb-a-imm8": 1619,
    "lb-a-imm8": 738, "stb-a-page": 2301, "j-address": 684,
}


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def source_bindings():
    """Check immutable historical fixture bytes before reading their values."""
    path = HERE / FIXTURE_PATH
    actual = sha256(path.read_bytes()).hexdigest()
    if actual != FIXTURE_SHA:
        raise ValueError("SealedM2bmFixtureIdentityMismatch")
    return {"research/p28-word0196/" + FIXTURE_PATH: actual}


def fixture():
    source_bindings()
    value = json.loads((HERE / FIXTURE_PATH).read_text(encoding="utf-8"))
    if (value["total_positive_contexts"], value["total_positive_instances"],
            len(value["main_cases"]), len(value["control_cases"]),
            len(value["dd_cases"])) != (51, 102, 16, 23, 12):
        raise ValueError("SealedM2bmInventoryMismatch")
    return value


def sealed_cases():
    value = fixture()
    rows = deepcopy(value["main_cases"] + value["control_cases"])
    main = {row["id"]: row for row in value["main_cases"]}
    for item in value["dd_cases"]:
        row = deepcopy(main[item["baseCase"]])
        row["id"] = item["id"]
        row["entryOverride"]["psw"] = item["beforePsw"]
        row["expected"]["psw"] = item["afterPsw"]
        rows.append(row)
    if len(rows) != len({row["id"] for row in rows}) or len(rows) != 51:
        raise ValueError("SealedM2bmUniqueContextsMismatch")
    return rows


def is_representable(psw):
    return type(psw) is int and 0 <= psw <= 65535 and psw & READS_ONE == READS_ONE


def own_aliases(entry, data, a=None, psw=None):
    """One owner per value; conflicting aliases are never silently normalized."""
    a = entry["a"] if a is None else a
    psw = entry["psw"] if psw is None else psw
    entry.update(a=a, al=a & 255, ah=a >> 8, psw=psw,
                 other_psw=psw & 4095, scb=psw & 7)
    for name, bit in (("cf", 15), ("zf", 14), ("hc", 13), ("dd", 12)):
        entry[name] = bool(psw & (1 << bit))
    entry["local_r"] = [data[str(0x108 + index)] for index in range(8)]
    entry["local_er"] = [entry["local_r"][2 * index] +
                         256 * entry["local_r"][2 * index + 1] for index in range(4)]


def _sealed_request(value, row):
    common = value["common_entry"]
    data = {str(int(address, 16)): int(byte, 16)
            for address, byte in value["common_data"].items()}
    data.update({str(int(address, 16)): int(byte, 16)
                 for address, byte in row["dataOverride"].items()})
    entry = {name: int(common[name], 16) for name in ("pc", "a", "psw", "lrb", "ssp")}
    entry.update(pointing_banks=[{name.lower(): int(bank[name], 16)
                                  for name in ("X1", "X2", "DP", "USP")}
                                 for bank in common["pointingBanks"]],
                 halted=False, provenance=PROVENANCE, sf=deepcopy(UNKNOWN_SF))
    own_aliases(entry, data, int(row["entryOverride"].get("a", common["a"]), 16),
                int(row["entryOverride"].get("psw", common["psw"]), 16))
    instruction = [int(byte, 16) for byte in row["bytesHex"]]
    guards = [0xA5 if index % 2 == 0 else 0x5A for index in range(6 - len(instruction))]
    return {"case_id": row["id"], "fixture_id": row["id"], "family": "sealed-m2bm",
            "form": row["form"], "bytes": instruction, "guards": guards,
            "content_digest": sha256(bytes(instruction + guards)).hexdigest(),
            "entry": entry, "data": data, "internal_sf": False,
            "physical_entry_pc": 0, "scratch": SCRATCH, "budget": 1,
            "expected_decoded_index": FROZEN_DECODED_INDICES[row["form"]],
            "expected_length": row["length"]}


def _flags(flags, dd, scb):
    retained = (0, 0x10, 0x20, 0x100, 0x200, 0x330, 0x130, 0x230)[scb]
    return READS_ONE | ((flags & 1) << 15) | (((flags >> 1) & 1) << 14) \
        | (((flags >> 2) & 1) << 13) | (dd << 12) | retained | scb


def _varied(base, family, index, psw, *, byte=None, word=None):
    result = deepcopy(base)
    result.update(case_id=f"{family}-{index:03d}", family=family)
    # Fixed integer canaries, not random seeds or production defaults. All32
    # words remain distinct; SCB selects each bank in the flags family.
    entry, data = result["entry"], result["data"]
    entry["pointing_banks"] = [
        {name: (0x2111 + (bank * 4 + slot) * 0x317 + index * 11) & 65535
         for slot, name in enumerate(("x1", "x2", "dp", "usp"))}
        for bank in range(8)]
    entry["ssp"] = (0x37A1 + index * 17) & 65535
    a = ((0xA5 + index * 13) & 255) * 256 + (entry["a"] & 255)
    if byte is not None:
        form = result["form"]
        if form in ("sllb-a", "orb-a-imm8", "stb-a-page"):
            a = (a & 0xFF00) | byte
        else:
            address = {"lb-a-page": 0x117, "rolb-page": 0x18E,
                       "lb-a-r0": 0x108, "andb-a-page": 0x117,
                       "movb-r1-page": 0x117, "andb-page-a": 0x117,
                       "orb-page-imm8": 0x12A}[form]
            data[str(address)] = byte
    if word is not None:
        data[str(0x196)], data[str(0x197)] = word & 255, word >> 8
    own_aliases(entry, data, a, psw)
    return result


def build_base_contexts():
    """234 independently seeded contexts, no unbounded Cartesian expansion."""
    value = fixture()
    rows = sealed_cases()
    result = [_sealed_request(value, row) for row in rows]
    main = {row["form"]: _sealed_request(value, row) for row in value["main_cases"]}
    for form_index, (form, base) in enumerate(main.items()):
        for flags in range(8):
            dd = 0 if form in DD_ZERO_FORMS else (flags + form_index) % 2
            result.append(_varied(base, "flags-scb", form_index * 8 + flags,
                                  _flags(flags, dd, flags)))
    for form_index, form in enumerate(BYTE_EDGE_FORMS):
        for edge_index, byte in enumerate(BYTE_EDGES):
            index = form_index * 5 + edge_index
            dd = 0 if form in DD_ZERO_FORMS else edge_index % 2
            result.append(_varied(main[form], "byte-edges", index,
                                  _flags(edge_index % 8, dd, edge_index % 8), byte=byte))
    for index, word in enumerate(WORD_EDGES):
        result.append(_varied(main["cmp-page-imm16"], "cmp-word-boundaries", index,
                              _flags(index, index % 2, index), word=word))
    if Counter(row["family"] for row in result) != Counter(FAMILY_COUNTS):
        raise ValueError("FiniteFamilyCountMismatch")
    if len(result) != len({row["case_id"] for row in result}) or len(result) != 234:
        raise ValueError("FiniteCorpusIdentityMismatch")
    return result


def build_corpus():
    result = []
    for base in build_base_contexts():
        for internal_sf in (False, True):
            row = deepcopy(base)
            row["internal_sf"] = internal_sf
            row["case_id"] += "-sf1" if internal_sf else "-sf0"
            result.append(row)
    return result


def coverage(cases=None):
    cases = build_corpus() if cases is None else cases
    forms = sorted({row["form"] for row in cases})
    flag_rows = [row for row in cases if row["family"] == "flags-scb"]
    return {"baseContexts": len(cases) // 2, "positiveCases": len(cases),
            "familyCases": dict(sorted(Counter(row["family"] for row in cases).items())),
            "forms": forms, "formCount": len(forms), "sfVariants": [False, True],
            "scbSelectors": sorted({row["entry"]["scb"] for row in cases}),
            "flagsScbPerForm": {form: sorted({row["entry"]["psw"] & 0xE000
                                              for row in flag_rows if row["form"] == form})
                                for form in forms},
            "byteEdges": list(BYTE_EDGES), "wordBoundaries": list(WORD_EDGES),
            "representableFullPsw": sum(is_representable(value) for value in range(65536)),
            "incompatibleFullPsw": sum(not is_representable(value) for value in range(65536)),
            "instructionBytesSource": "ExactSealedM2bmFixturesOnly",
            "fullCartesianProduct": False, "noCpuOrDecoderExecution": True}
