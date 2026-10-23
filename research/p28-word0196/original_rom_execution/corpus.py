"""Small explicit technical states for M2bt, never native input ownership.

There are 32 base states, each with two separately initialized internal host-SF
experiments.  Every byte and pointing word used by the production admission is
explicit.  These are not a recovered scheduler, historical native snapshots or
an exhaustive PSW x DATA proof.  No ROM, opcode, CPU or process interface exists.
"""

from copy import deepcopy
from collections import Counter
import json


MODE = "OriginalRomBytes_TechnicalSeededExecution"
PROVENANCE = "TechnicalSeeded_NoNativeGenerationOwner"
UNKNOWN_SF = {"status": "SFMeaningStorageNotEstablished", "value": None,
              "meaning": None, "storage": None, "width_bits": None}
READS_ONE = 0x0CC8
ENTRY_PC = 0x556F
INVENTORY = tuple(range(0x0108, 0x0110)) + (0x0117, 0x0124, 0x0128, 0x012A, 0x018E, 0x018F, 0x0196, 0x0197)
PATH_COUNTS = {"A": (10, 5, 3), "B": (12, 9, 3), "C": (13, 10, 3), "D": (15, 12, 5)}
FAMILY_BASE_COUNTS = {"path-dd-hc": 16, "word-boundary": 7, "same-value-writer": 7,
                      "short-circuit-b": 2}
PUBLIC_PC_DELTA = 0x6000 - ENTRY_PC
PUBLIC_DATA = {0x0196: 0x019A, 0x0197: 0x019B, 0x018E: 0x0192,
               0x018F: 0x0193, 0x0117: 0x011B, 0x012A: 0x012D, 0x0124: 0x012E}


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def is_representable(psw):
    if type(psw) is not int or not 0 <= psw <= 65535:
        raise ValueError("PswU16Domain")
    return psw & READS_ONE == READS_ONE


def _make(family, index, path, dd, hc, **overrides):
    salt = (0x4D326274 + index * 0x9E37 + sum(map(ord, family)) * 0x41) & 65535
    scb = index % 8
    free = index % 16
    other = READS_ONE | scb | ((free & 1) << 4) | ((free & 2) << 4) \
        | ((free & 4) << 6) | ((free & 8) << 6)
    cf, zf = (index + dd) % 2, ((index // 2) + dd) % 2
    psw = other | (cf << 15) | (zf << 14) | (hc << 13) | (dd << 12)
    ah = (0, 1, 127, 128, 255)[index % 5]
    al = (salt * 41 + 23) & 255
    local = [(salt + 37 * (number + 1)) & 255 for number in range(8)]
    local[0] = (0, 1, 127, 128, 255)[index % 5]
    word = 191 if path == "A" else 192
    gate_a = (salt & 127) | (128 if path == "B" else 0)
    gate_b = (salt & 223) | (32 if path == "C" else 0)
    values = {"word": word, "gate_a": gate_a, "gate_b": gate_b,
              "ram117": (salt * 7 + 15) & 255, "ram18f": (salt * 11 + 129) & 255,
              "e": (0, 1, 127, 128, 255)[index % 5]}
    if set(overrides) - set(values) - {"r1"}:
        raise ValueError("ClosedCorpusOverride")
    values.update({key: value for key, value in overrides.items() if key in values})
    if "r1" in overrides:
        local[1] = overrides["r1"]
    word = values["word"]
    data = {str(0x0108 + number): value for number, value in enumerate(local)}
    data.update({str(0x0117): values["ram117"], str(0x0124): values["gate_b"],
                 str(0x0128): (salt * 3 + 166) & 255, str(0x012A): values["gate_a"],
                 str(0x018E): values["e"], str(0x018F): values["ram18f"],
                 str(0x0196): word & 255, str(0x0197): word >> 8})
    entry = {"pc": ENTRY_PC, "a": al | (ah << 8), "al": al, "ah": ah, "psw": psw,
             "cf": bool(cf), "zf": bool(zf), "hc": bool(hc), "dd": bool(dd),
             "other_psw": other, "lrb": 0x0021, "scb": scb,
             "ssp": (0x37A1 + index * 0x239) & 65535,
             "pointing_banks": [{name: (salt + (bank * 4 + slot + 1) * 0x317) & 65535
                                  for slot, name in enumerate(("x1", "x2", "dp", "usp"))}
                                 for bank in range(8)],
             "local_r": local, "local_er": [local[2 * number] | (local[2 * number + 1] << 8)
                                             for number in range(4)],
             "halted": False, "provenance": PROVENANCE, "sf": deepcopy(UNKNOWN_SF)}
    case = {"kind": "case", "case_id": f"m2bt-{family}-{index:03d}", "family": family,
            "mode": MODE, "source_classification": "SyntheticOnly", "native_input_claimed": False,
            "entry": entry, "data": data, "path": path, "internal_sf": False,
            "budget": PATH_COUNTS[path][0]}
    validate_case(case)
    return case


def validate_case(case):
    keys = {"kind", "case_id", "family", "mode", "source_classification", "native_input_claimed",
            "entry", "data", "path", "internal_sf", "budget"}
    if type(case) is not dict or set(case) != keys:
        raise ValueError("ClosedTechnicalCase")
    if case["kind"] != "case" or case["mode"] != MODE or case["source_classification"] != "SyntheticOnly" \
            or case["native_input_claimed"] is not False or type(case["internal_sf"]) is not bool:
        raise ValueError("TechnicalInputCannotClaimNativeOwnership")
    identifier = case["case_id"]
    if type(identifier) is not str or not 1 <= len(identifier) <= 96 or not identifier.isascii() \
            or any(not (character.isalnum() or character in "-_") for character in identifier):
        raise ValueError("ClosedCaseIdentity")
    if type(case["family"]) is not str or not case["family"]:
        raise ValueError("ClosedCaseFamily")
    entry, data = case["entry"], case["data"]
    entry_keys = {"pc", "a", "al", "ah", "psw", "cf", "zf", "hc", "dd", "other_psw", "lrb", "scb",
                  "ssp", "pointing_banks", "local_r", "local_er", "halted", "provenance", "sf"}
    if type(entry) is not dict or set(entry) != entry_keys or type(data) is not dict \
            or set(data) != {str(address) for address in INVENTORY}:
        raise ValueError("CompleteExplicitEntryAndDataRequired")
    for name in ("pc", "a", "psw", "lrb", "ssp"):
        if type(entry[name]) is not int or not 0 <= entry[name] <= 65535:
            raise ValueError("EntryU16Domain_" + name)
    if entry["pc"] != ENTRY_PC or entry["lrb"] != 0x0021 or not is_representable(entry["psw"]):
        raise ValueError("OriginalEntryOrRepresentablePswRequired")
    for name in ("al", "ah"):
        if type(entry[name]) is not int or not 0 <= entry[name] <= 255:
            raise ValueError("EntryU8Domain_" + name)
    if entry["a"] != entry["al"] | (entry["ah"] << 8):
        raise ValueError("AccumulatorAliasMismatch")
    for name, shift in (("cf", 15), ("zf", 14), ("hc", 13), ("dd", 12)):
        if type(entry[name]) is not bool or entry[name] != bool(entry["psw"] & (1 << shift)):
            raise ValueError("PswAliasMismatch_" + name)
    if type(entry["other_psw"]) is not int or entry["other_psw"] != entry["psw"] & 0x0FFF \
            or type(entry["scb"]) is not int or entry["scb"] != entry["psw"] & 7:
        raise ValueError("OtherPswOrScbMismatch")
    if entry["halted"] is not False or entry["provenance"] != PROVENANCE or entry["sf"] != UNKNOWN_SF:
        raise ValueError("UnknownPhysicalSfAndTechnicalProvenanceRequired")
    if type(entry["pointing_banks"]) is not list or len(entry["pointing_banks"]) != 8:
        raise ValueError("ExplicitEightPointingBanksRequired")
    for bank in entry["pointing_banks"]:
        if type(bank) is not dict or set(bank) != {"x1", "x2", "dp", "usp"} \
                or any(type(value) is not int or not 0 <= value <= 65535 for value in bank.values()):
            raise ValueError("ExplicitFourPointingWordsRequired")
    if any(type(value) is not int or not 0 <= value <= 255 for value in data.values()):
        raise ValueError("DataByteDomain")
    local = [data[str(0x0108 + index)] for index in range(8)]
    if type(entry["local_r"]) is not list or entry["local_r"] != local \
            or any(type(value) is not int for value in entry["local_r"]) \
            or type(entry["local_er"]) is not list \
            or entry["local_er"] != [local[2 * index] | (local[2 * index + 1] << 8) for index in range(4)] \
            or any(type(value) is not int for value in entry["local_er"]):
        raise ValueError("LocalRegisterAliasMismatch")
    word = data[str(0x0196)] | (data[str(0x0197)] << 8)
    path = "A" if word < 192 else "B" if data[str(0x012A)] & 128 else "C" if data[str(0x0124)] & 32 else "D"
    if case["path"] != path or type(case["budget"]) is not int or case["budget"] != PATH_COUNTS[path][0]:
        raise ValueError("PathPredicateOrExactOriginalBudgetMismatch")
    return True


def iter_base_cases():
    index = 0
    for path_index, path in enumerate("ABCD"):
        for dd in (0, 1):
            for hc in (0, 1):
                yield _make("path-dd-hc", index, path, dd, hc)
                index += 1
    for index, (word, path) in enumerate(((0, "A"), (191, "A"), (192, "D"), (193, "C"),
                                         (255, "B"), (256, "C"), (65535, "D"))):
        yield _make("word-boundary", index, path, index % 2, (index // 2) % 2, word=word)
    controls = (("A", {"e": 0}), ("B", {"ram117": 0, "r1": 0}),
                ("D", {"ram117": 0}), ("D", {"ram18f": 0}),
                ("D", {"gate_a": 1}), ("A", {"ram117": 15}), ("A", {"ram18f": 15}))
    for index, (path, overrides) in enumerate(controls):
        yield _make("same-value-writer", index, path, index % 2, (index // 2) % 2, **overrides)
    for index, gate_b in enumerate((0, 255)):
        # All other initialized fields intentionally equal: this tests that B
        # neither reads nor depends on the second gate.
        case = _make("short-circuit-b", 0, "B", 1, 1, gate_b=gate_b)
        case["case_id"] = f"m2bt-short-circuit-b-{index:03d}"
        yield case


def iter_cases():
    for base in iter_base_cases():
        for internal_sf in (False, True):
            case = deepcopy(base)
            case["case_id"] += "-sf1" if internal_sf else "-sf0"
            case["internal_sf"] = internal_sf
            validate_case(case)
            yield case


def wire_case(case, program_kind="private"):
    """Strip only the three host authority labels; explicitly map public roles.

    A sealed case always uses the reviewed logical roles. The public fixture is
    a separate invented program, not a relocation or publication of OEM bytes.
    """
    validate_case(case)
    if program_kind not in ("private", "public_fixture"):
        raise ValueError("ClosedProgramKind")
    result = deepcopy(case)
    for field in ("mode", "source_classification", "native_input_claimed"):
        del result[field]
    if program_kind == "public_fixture":
        result["entry"]["pc"] += PUBLIC_PC_DELTA
        result["data"] = {str(PUBLIC_DATA.get(int(key), int(key))): value
                          for key, value in result["data"].items()}
    return result


def historical_technical_cases(m2bs_report, selected_sources):
    """Read-only reconciliation of three previously qualified source snapshots.

    This does not produce a strict native entry: seven unobserved pointing banks,
    halted and host SF are explicit technical completions. Recorded initial DATA
    is pre-upstream; actual journal observations are folded to the entry fence.
    The returned obligations retain the prior source-CPU observations separately.
    No CPU, ROM, file or process interface is used here.
    """
    samples = m2bs_report["historical"]["privateEvidence"]["fresh_reconciled_original_a_samples"]
    if type(samples) is not list or len(samples) != 3 or {v["path"] for v in samples} != {"A", "B", "D"}:
        raise ValueError("ThreeQualifiedHistoricalPathsRequired")
    cases, obligations = [], []
    for sample_index, sample in enumerate(samples):
        binding = sample["source_binding"]
        source = selected_sources[binding["source_id"]]
        if source.public_binding() != binding or source.kind != "HistoricalSourceCpuObservations":
            raise ValueError("HistoricalSelectedSourceBindingMismatch")
        pointer = sample["raw_pointer"]
        if type(pointer) is not str or not pointer.startswith("/word0196AlternateSequences/"):
            raise ValueError("QualifiedHistoricalCheckpointPointerRequired")
        checkpoint = source.document
        for token in pointer.split("/")[1:]:
            checkpoint = checkpoint[int(token)] if type(checkpoint) is list else checkpoint[token]
        entry, final = sample["entry_snapshot"], sample["exit_snapshot"]
        if checkpoint["alternate"]["entry"] != entry or checkpoint["alternate"]["exit"] != final \
                or checkpoint["machineId"] != sample["source_cpu_machine_id"]:
            raise ValueError("HistoricalSnapshotOrMachineMismatch")
        initial = checkpoint["stateBefore"]
        names = {0x0117: "byte0117", 0x0124: "byte0124", 0x0128: "byte0128",
                 0x012A: "byte012a", 0x018E: "byte018e", 0x018F: "byte018f"}
        data = {address: initial[name] for address, name in names.items()}
        journal = checkpoint["continuityJournal"]
        fence = next((i for i, row in enumerate(journal) if row[0] == 1 and row[1] == ENTRY_PC), None)
        if fence is None:
            raise ValueError("HistoricalEntryFunctionalReadFenceMissing")
        # All actual reads and writes disclose the current value at that point.
        # Folding is data reconciliation, not an execution of old instructions.
        for origin, pc, address, width, write, value in journal[:fence]:
            for offset in range(width // 8):
                if address + offset in data or address + offset in (0x0196, 0x0197):
                    data[address + offset] = (value >> (offset * 8)) & 255
        for index, value in enumerate(entry["registers"]):
            data[0x0108 + index] = value
        if set(data) != set(INVENTORY):
            raise ValueError("HistoricalEntryDataNotReconstructible")
        base = _make("qualified-history-technical-completion", sample_index, sample["path"],
                     int(entry["dd"]), (entry["psw"] >> 13) & 1)
        e = base["entry"]
        psw, a = entry["psw"], entry["accumulator"]
        e.update({"a": a, "al": a & 255, "ah": a >> 8, "psw": psw,
                  "cf": bool(psw & 0x8000), "zf": bool(psw & 0x4000),
                  "hc": bool(psw & 0x2000), "dd": bool(psw & 0x1000),
                  "other_psw": psw & 0x0FFF, "scb": psw & 7,
                  "lrb": entry["lrb"], "ssp": entry["ssp"],
                  "local_r": list(entry["registers"]),
                  "local_er": [entry["registers"][2*i] | (entry["registers"][2*i+1] << 8) for i in range(4)]})
        e["pointing_banks"][e["scb"]] = {name: entry[name] for name in ("x1", "x2", "dp", "usp")}
        base["data"] = {str(key): value for key, value in data.items()}
        validate_case(base)
        ids = []
        for internal_sf in (False, True):
            case = deepcopy(base)
            case["case_id"] += "-sf1" if internal_sf else "-sf0"
            case["internal_sf"] = internal_sf
            validate_case(case)
            cases.append(case)
            ids.append(case["case_id"])
        accesses = checkpoint["alternate"]["accesses"]
        expected_writes = [{"pc": row[0], "address": row[1], "width": row[2], "value": row[4]}
                           for row in accesses if row[3] == 1]
        obligations.append({"case_ids": ids, "path": sample["path"], "source_binding": binding,
                            "raw_pointer": pointer, "source_cpu_machine_id": sample["source_cpu_machine_id"],
                            "source_cpu_session_group": sample["source_cpu_session_group"],
                            "entry_snapshot": entry, "exit_snapshot": final,
                            "native_pc_sequence": sample["native_pc_sequence"],
                            "ordered_writes": expected_writes,
                            "entry_data_reconciliation": "RecordedPreUpstreamBytesThenActualJournalUntil556F",
                            "classification": "QualifiedHistoricalSubsetWithTechnicalCompletion_NotStrictNativeInput",
                            "new_cpu_is_historical_cpu": False})
    unknown = [f"pointingBank{bank}.{name}" for bank in (0, 1, 3, 4, 5, 6, 7)
               for name in ("X1", "X2", "DP", "USP")] + ["SF", "P2", "RelevantDownstreamSFR",
               "NativeStackFrame", "InterruptContext", "PeripheralContext", "NativeScheduler"]
    return {"cases": cases, "obligations": obligations, "unknownFields": unknown,
            "strictNativeInputs": 0, "historicalPathCWitnesses": 0,
            "technicalCompletions": ["unobserved pointing banks", "halted=false", "internal host SF pair"]}


def coverage_summary():
    families, paths, psws, scbs, words, other = Counter(), Counter(), set(), set(), set(), set()
    reads = writes = retirements = 0
    for case in iter_cases():
        families[case["family"]] += 1
        paths[case["path"]] += 1
        psws.add(case["entry"]["psw"])
        scbs.add(case["entry"]["scb"])
        other.add(case["entry"]["other_psw"])
        words.add(case["data"][str(0x0196)] | (case["data"][str(0x0197)] << 8))
        count, read_count, write_count = PATH_COUNTS[case["path"]]
        retirements += count
        reads += read_count
        writes += write_count
    if dict(families) != {name: count * 2 for name, count in FAMILY_BASE_COUNTS.items()}:
        raise ValueError("ExactClosedCorpusFamilyCount")
    return {"classification": "ExplicitTechnicalCorpus_NoRuntimeObservation", "baseCases": 32,
            "casesWithInternalSfPairs": 64, "families": dict(families), "paths": dict(paths),
            "expectedRetirements": retirements, "expectedLogicalReads": reads, "expectedWrites": writes,
            "wordBoundaries": sorted(words), "representablePswValues": len(psws),
            "scbSelectors": sorted(scbs), "distinctOtherPswValues": len(other),
            "all2048RepresentablePswValuesExecuted": False, "nativeOwnerClaimed": False,
            "physicalSf": deepcopy(UNKNOWN_SF)}
