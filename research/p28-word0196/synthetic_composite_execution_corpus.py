"""M2bn deterministic invented inputs; no CPU, decoder or PROGRAM interface.

Families are deliberately separate, bounded sweeps, not a Cartesian product or
an exhaustive DATA-state claim. Every base case has two independently initialized
internal-SF experiments. The architectural SF descriptor stays entirely unknown.
"""

from copy import deepcopy
from collections import Counter

PROVENANCE = "InventedOnly_NoNativeGenerationOwner"
UNKNOWN_SF = {"status": "SFMeaningStorageNotEstablished", "value": None,
              "meaning": None, "storage": None, "width_bits": None}
SEED = 0x4D32626E
READS_ONE = 0x0CC8
REPRESENTATIVES = (0, 1, 127, 128, 255)
PATH_COUNTS = {"A": (11, 5, 3), "B": (13, 9, 3),
               "C": (14, 10, 3), "D": (16, 12, 5)}
FAMILY_CASE_COUNTS = {"representable-psw": 2048, "path-dd-flags": 64,
                      "word-boundaries-gates": 40, "all-data018e": 256,
                      "all-ah": 256, "representative-data": 20,
                      "all-scb-pointing": 8, "same-value-writers": 7,
                      "short-circuit-b": 4, "carry-dependencies": 32}


def canonical_json(value):
    import json
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")


def is_representable(psw):
    if type(psw) is not int or not 0 <= psw <= 65535:
        raise ValueError("PswU16Domain")
    return (psw & READS_ONE) == READS_ONE


def _psw(flags, dd, scb=3):
    return READS_ONE | ((flags & 1) << 15) | (((flags >> 1) & 1) << 14) \
        | (((flags >> 2) & 1) << 13) | (dd << 12) | scb


def _make(family, index, path, psw, *, word=None, gate_a=None, gate_b=None,
          e=None, ah=None, r0=None, ram117=None, ram18f=None):
    if path not in PATH_COUNTS or not is_representable(psw):
        raise ValueError("CorpusPathOrRepresentability")
    salt = (SEED + index * 0x9E37 + sum(map(ord, family)) * 0x41) & 65535
    local = [((salt >> (n % 3)) + 37 * (n + 1)) & 255 for n in range(8)]
    if r0 is not None:
        local[0] = r0
    if ah is None:
        ah = (salt * 29 + 53) & 255
    al = (salt * 41 + 23) & 255
    if word is None:
        word = 191 if path == "A" else 192 + salt % (65536 - 192)
    if gate_a is None:
        gate_a = (salt & 127) | (128 if path == "B" else 0)
    if gate_b is None:
        gate_b = (salt & 223) | (32 if path == "C" else 0)
    data = {str(0x108 + n): value for n, value in enumerate(local)}
    data.update({str(0x117): (salt * 7 + 15) & 255 if ram117 is None else ram117,
                 str(0x124): gate_b, str(0x128): (salt * 3 + 166) & 255,
                 str(0x12A): gate_a, str(0x18E): salt & 255 if e is None else e,
                 str(0x18F): (salt * 11 + 129) & 255 if ram18f is None else ram18f,
                 str(0x196): word & 255, str(0x197): word >> 8})
    actual_path = ("A" if word < 192 else "B" if gate_a & 128
                   else "C" if gate_b & 32 else "D")
    if actual_path != path:
        raise ValueError("CorpusPredicateDisagreesWithRequestedFamilyPath")
    entry = {"pc": 0x1000, "a": al + 256 * ah, "al": al, "ah": ah,
             "psw": psw, "cf": bool(psw & 0x8000), "zf": bool(psw & 0x4000),
             "hc": bool(psw & 0x2000), "dd": bool(psw & 0x1000),
             "other_psw": psw & 4095, "lrb": 33, "scb": psw & 7,
             "ssp": (salt * 19 + 0x37A1) & 65535,
             "pointing_banks": [{name: (salt + (bank * 4 + slot + 1) * 0x317) & 65535
                                  for slot, name in enumerate(("x1", "x2", "dp", "usp"))}
                                 for bank in range(8)],
             "local_r": list(local),
             "local_er": [local[n * 2] + 256 * local[n * 2 + 1] for n in range(4)],
             "halted": False, "provenance": PROVENANCE, "sf": deepcopy(UNKNOWN_SF)}
    return {"kind": "case", "case_id": f"{family}-{index:05d}", "family": family,
            "entry": entry, "data": data, "path": path, "internal_sf": False,
            "budget": 16}


def iter_base_cases():
    """Exact ordered corpus. No result, decoder or external seed influences it."""
    compatible = (value for value in range(65536) if is_representable(value))
    for index, psw in enumerate(compatible):
        yield _make("representable-psw", index, "ABCD"[index % 4], psw)
    index = 0
    for path in "ABCD":
        for dd in (0, 1):
            for flags in range(8):
                yield _make("path-dd-flags", index, path, _psw(flags, dd, flags))
                index += 1
    index = 0
    for word in (0, 191, 192, 193, 65535):
        for a, b in ((0, 0), (0, 32), (128, 0), (128, 32)):
            for dd in (0, 1):
                path = "A" if word < 192 else "B" if a & 128 else "C" if b & 32 else "D"
                yield _make("word-boundaries-gates", index, path,
                            _psw(index % 8, dd, index % 8), word=word, gate_a=a, gate_b=b)
                index += 1
    for value in range(256):
        representative = REPRESENTATIVES[value % 5]
        yield _make("all-data018e", value, "ABCD"[value % 4],
                    _psw(value % 8, value % 2, value % 8), e=value,
                    r0=representative, ram117=representative, ram18f=representative)
    for value in range(256):
        representative = REPRESENTATIVES[value % 5]
        yield _make("all-ah", value, "ABCD"[value % 4],
                    _psw(value % 8, value % 2, value % 8), ah=value,
                    r0=representative, ram117=representative, ram18f=representative)
    for index, (path, value) in enumerate((p, v) for p in "ABCD" for v in REPRESENTATIVES):
        yield _make("representative-data", index, path,
                    _psw(index % 8, index % 2, index % 8),
                    r0=value, ram117=value, ram18f=value)
    for scb in range(8):
        yield _make("all-scb-pointing", scb, "ABCD"[scb % 4], _psw(scb, scb % 2, scb))
    same = (("A", {"e": 0}), ("B", {"ram117": 0}),
            ("D", {"ram117": 0}), ("D", {"ram18f": 0}),
            ("D", {"gate_a": 1}), ("A", {"ram117": 15}),
            ("A", {"ram18f": 15}))
    for index, (path, overrides) in enumerate(same):
        case = _make("same-value-writers", index, path,
                     _psw(index % 8, index % 2, index % 8), **overrides)
        if index == 1:
            case["data"][str(0x109)] = case["data"][str(0x117)]
            case["entry"]["local_r"][1] = case["data"][str(0x109)]
            case["entry"]["local_er"][0] = case["entry"]["local_r"][0] \
                + 256 * case["entry"]["local_r"][1]
        yield case
    for index, gate_b in enumerate((0, 32, 255, 95)):
        # Shared index deliberately gives identical other entry/data fields.
        case = _make("short-circuit-b", 0, "B", _psw(7, 1), gate_b=gate_b)
        case["case_id"] = f"short-circuit-b-{index:05d}"
        yield case
    index = 0
    for value in (0, 1, 64, 127, 128, 129, 254, 255):
        for word in (191, 192):
            for dd in (0, 1):
                yield _make("carry-dependencies", index, "A" if word < 192 else "D",
                            _psw(index % 8, dd, index % 8), e=value, word=word)
                index += 1


def iter_cases():
    for base in iter_base_cases():
        for internal_sf in (False, True):
            case = deepcopy(base)
            case["internal_sf"] = internal_sf
            yield case


def coverage_summary():
    families, paths, psws, scbs = Counter(), Counter(), set(), set()
    words, e_values, ah_values = set(), set(), set()
    pointing_values = [set() for _ in range(32)]
    retirements = logical_reads = writes = 0
    for case in iter_base_cases():
        family, path, entry, data = case["family"], case["path"], case["entry"], case["data"]
        families[family] += 1
        paths[path] += 1
        scbs.add(entry["scb"])
        if family == "representable-psw":
            psws.add(entry["psw"])
        if family == "word-boundaries-gates":
            words.add(data[str(0x196)] + 256 * data[str(0x197)])
        if family == "all-data018e":
            e_values.add(data[str(0x18E)])
        if family == "all-ah":
            ah_values.add(entry["ah"])
        for bank, values in enumerate(entry["pointing_banks"]):
            for slot, name in enumerate(("x1", "x2", "dp", "usp")):
                pointing_values[4 * bank + slot].add(values[name])
        instructions, reads, stores = PATH_COUNTS[path]
        retirements += instructions * 2
        logical_reads += reads * 2
        writes += stores * 2
    if dict(families) != FAMILY_CASE_COUNTS:
        raise ValueError("ExactCorpusFamilyCounts")
    return {"seed": SEED, "baseCases": sum(families.values()),
            "executionsWithInternalSfPairs": sum(families.values()) * 2,
            "cpuInstances": sum(families.values()) * 2,
            "families": {name: {"baseCases": count, "executions": count * 2}
                         for name, count in families.items()},
            "paths": {name: {"baseCases": count, "executions": count * 2}
                      for name, count in paths.items()},
            "expectedRetirements": retirements,
            "expectedLogicalReads": logical_reads, "expectedWrites": writes,
            "expectedRawDataEvents": logical_reads + writes + sum(paths.values()) * 2,
            "representableFullPswValues": len(psws), "scbSelectors": sorted(scbs),
            "wordBoundaries": sorted(words), "data018eValues": len(e_values),
            "ahValues": len(ah_values),
            "distinctValuesPerPointingWord": [len(values) for values in pointing_values],
            "notExhaustivePswTimesPathTimesData": True,
            "admissionOnlyChecksIncludedInCpuExecutionCount": False}
