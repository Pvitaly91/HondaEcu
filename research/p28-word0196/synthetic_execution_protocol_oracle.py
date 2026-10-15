"""Independent M2bk invented-state expectation oracle; never a CPU executor.

Expected values are authored from the September 1991 MSM66201 manual, the
reviewed M2av structured algorithm and M2bd/M2bh path obligations.  There is no
instruction fetch, opcode dispatch, program payload, operational codec, Rust,
analyzer, ROM, process or file interface.  Literal paths and explicit structured
formulas describe future expectations, not execution observations or native
generation ownership.  All selected and unselected pointing banks are retained;
SF meaning, native storage and native width remain unknown.

Primary pages (PDF numbering): LB124, SLLB197, ROLB173, ANDB76/77, CMP90,
JLT120/121, MOVB153, JBS119, ORB160/163, STB208, direct J116.
Source reconstruction: word0196_equivalent.c IR556F through IR55C3, not a
translation of an emulator or of the new protocol analyzer.
"""

from copy import deepcopy
from hashlib import sha256
import json


BASE_SHA = "be7ed4a72dc5f8758bfa4293db0f881ba9bb7536"
MANUAL_SHA256 = "f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271"
COMPOSITE_SHA256 = "91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1"
PROVENANCE = "InventedOnly_NoNativeGenerationOwner"
UNKNOWN_SF = {"status": "UnknownNativeMeaningStorageWidth", "value": None}
DATA_KEYS = (
    "0108", "0109", "010A", "010B", "010C", "010D", "010E", "010F",
    "0117", "0124", "0128", "012A", "018E", "018F", "0196", "0197",
)
ENTRY_KEYS = (
    "pc", "a", "al", "ah", "psw", "cf", "zf", "hc", "dd", "otherPsw",
    "lrb", "scb", "ssp", "pointingBanks", "sf", "halted",
)

# Fixed reviewed logical sequences, not an execution engine's selected output.
PATHS = {
    "A": (0x556F, 0x5571, 0x5572, 0x5575, 0x5576, 0x5578, 0x557D,
          0x55BF, 0x55C1, 0x55C3, "DirectJ_Below"),
    "B": (0x556F, 0x5571, 0x5572, 0x5575, 0x5576, 0x5578, 0x557D,
          0x557F, 0x5582, 0x5585, 0x5592, 0x5594, "DirectJ_NotBelow"),
    "C": (0x556F, 0x5571, 0x5572, 0x5575, 0x5576, 0x5578, 0x557D,
          0x557F, 0x5582, 0x5585, 0x5588, 0x5592, 0x5594,
          "DirectJ_NotBelow"),
    "D": (0x556F, 0x5571, 0x5572, 0x5575, 0x5576, 0x5578, 0x557D,
          0x557F, 0x5582, 0x5585, 0x5588, 0x558B, 0x558E, 0x5592,
          0x5594, "DirectJ_NotBelow"),
}


def _scalar(value, maximum, label):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError("Independent oracle scalar domain: " + label)


def _mapping(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError("Independent oracle closed mapping: " + label)


def _validate_scenario(scenario):
    _mapping(scenario, ("id", "classification", "entry", "data", "localAliases"),
             "scenario")
    identifier = scenario["id"]
    if (type(identifier) is not str or not 1 <= len(identifier) <= 96
            or not identifier.isascii()
            or any(not (character.isalnum() or character in "-_")
                   for character in identifier)):
        raise ValueError("Independent oracle invented identifier")
    if type(scenario["classification"]) is not str or scenario["classification"] != PROVENANCE:
        raise ValueError("Independent oracle accepts invented snapshots only")
    entry, data, aliases = scenario["entry"], scenario["data"], scenario["localAliases"]
    _mapping(entry, ENTRY_KEYS, "entry")
    _mapping(data, DATA_KEYS, "DATA")
    _mapping(aliases, ("r", "er"), "localAliases")
    for name in ("pc", "a", "psw", "lrb", "ssp"):
        _scalar(entry[name], 65535, name)
    for name in ("al", "ah"):
        _scalar(entry[name], 255, name)
    for name in ("cf", "zf", "hc", "dd"):
        _scalar(entry[name], 1, name)
    _scalar(entry["otherPsw"], 4095, "otherPsw")
    _scalar(entry["scb"], 7, "scb")
    if entry["pc"] != 0x1000 or entry["lrb"] != 0x0021:
        raise ValueError("Independent oracle entry context")
    if entry["a"] != entry["al"] + 256 * entry["ah"]:
        raise ValueError("Independent oracle accumulator alias")
    for name, shift in (("cf", 15), ("zf", 14), ("hc", 13), ("dd", 12)):
        if entry[name] != (entry["psw"] // (2 ** shift)) % 2:
            raise ValueError("Independent oracle PSW alias: " + name)
    if entry["otherPsw"] != entry["psw"] % 4096 or entry["scb"] != entry["psw"] % 8:
        raise ValueError("Independent oracle OtherPSW/SCB alias")
    if type(entry["halted"]) is not bool or entry["halted"] is not False:
        raise ValueError("Independent oracle non-halted invented entry")
    _mapping(entry["sf"], ("status", "value"), "SF")
    if (type(entry["sf"]["status"]) is not str
            or entry["sf"]["status"] != UNKNOWN_SF["status"]
            or entry["sf"]["value"] is not None):
        raise ValueError("Independent oracle SF remains unknown")
    banks = entry["pointingBanks"]
    if type(banks) is not list or len(banks) != 8:
        raise ValueError("Independent oracle eight pointing banks required")
    for bank in banks:
        if type(bank) is not list or len(bank) != 4:
            raise ValueError("Independent oracle four pointing registers per bank")
        for value in bank:
            _scalar(value, 65535, "pointing register")
    for value in data.values():
        _scalar(value, 255, "DATA byte")
    for name, count, maximum in (("r", 8, 255), ("er", 4, 65535)):
        if type(aliases[name]) is not list or len(aliases[name]) != count:
            raise ValueError("Independent oracle local alias domain")
        for value in aliases[name]:
            _scalar(value, maximum, "local alias")
    local = [data[f"{0x0108 + index:04X}"] for index in range(8)]
    pairs = [local[2 * index] + 256 * local[2 * index + 1] for index in range(4)]
    if aliases["r"] != local or aliases["er"] != pairs:
        raise ValueError("Independent oracle local DATA/er alias")


def make_scenario(word, gate_a, gate_b, incoming_dd, variant=0):
    """Closed invented fixture, including nonzero retained-bank canaries.

    gate_a and gate_b are complete DATA012A and DATA0124 bytes, not booleans.
    The eight variants exercise AH, initial flags, all SCB selectors, carry and
    same-value writes without assigning any native or physical provenance.
    """
    for value, maximum, name in ((word, 65535, "word"), (gate_a, 255, "gate_a"),
                                  (gate_b, 255, "gate_b"), (incoming_dd, 1, "DD"),
                                  (variant, 7, "variant")):
        _scalar(value, maximum, name)
    ah, al = (0x35 + 29 * variant) % 256, (0x17 + 41 * variant) % 256
    cf, zf, hc = variant % 2, (variant // 2) % 2, (variant // 4) % 2
    other = ((0x0B80 ^ (variant * 0x11B)) & 0x0FF8) | variant
    psw = other + 4096 * incoming_dd + 8192 * hc + 16384 * zf + 32768 * cf
    local = [((index + 1) * 37 + variant * 19) % 256 for index in range(8)]
    local[0] = (0x00, 0xFF, 0x55, 0xAA, 0x81, 0x7F, 0x01, 0xF0)[variant]
    data = {f"{0x0108 + index:04X}": value for index, value in enumerate(local)}
    data.update({
        "0117": (0x0F, 0xF0, 0xA5, 0x5A, 0x00, 0xFF, 0x81, 0x7E)[variant],
        "0124": gate_b, "0128": (0xA6 + variant * 17) % 256, "012A": gate_a,
        "018E": (0x00, 0xFF, 0x80, 0x7F, 0x81, 0x01, 0x55, 0xAA)[variant],
        "018F": (0x00, 0xFF, 0x35, 0x80, 0x0F, 0xF0, 0x66, 0x99)[variant],
        "0196": word % 256, "0197": word // 256,
    })
    scenario = {
        "id": f"w{word:05d}-a{gate_a:03d}-b{gate_b:03d}-dd{incoming_dd}-v{variant}",
        "classification": PROVENANCE,
        "entry": {
            "pc": 0x1000, "a": al + 256 * ah, "al": al, "ah": ah,
            "psw": psw, "cf": cf, "zf": zf, "hc": hc, "dd": incoming_dd,
            "otherPsw": other, "lrb": 0x0021, "scb": variant,
            "ssp": (0x0137 + 0x135 * variant) % 65536,
            "pointingBanks": [
                [(((bank + 1) * 0x1021 + (register + 1) * 0x0317
                   + variant * 0x0421) % 65536) or 1 for register in range(4)]
                for bank in range(8)
            ],
            "sf": deepcopy(UNKNOWN_SF), "halted": False,
        },
        "data": data,
        "localAliases": {"r": list(local),
                         "er": [local[2 * i] + 256 * local[2 * i + 1]
                                for i in range(4)]},
    }
    _validate_scenario(scenario)
    return scenario


def _psw_flag(psw, power, value):
    """Replace one documented bit using positional arithmetic."""
    old = (psw // power) % 2
    return psw + power * (int(value) - old)


def _loaded_psw(psw, value):
    return _psw_flag(_psw_flag(psw, 16384, value == 0), 4096, False)


def reference_case(scenario):
    """Independent static expectation via explicit structured C-style formulas.

    Recording helpers serialize already selected source-level effects; they
    never fetch/decode instructions or dispatch by PC.  No program bytes are
    accepted or produced.  Caller objects are not mutated.
    """
    _validate_scenario(scenario)
    entry, data = deepcopy(scenario["entry"]), deepcopy(scenario["data"])
    a, psw, pc = entry["a"], entry["psw"], 0x1000
    trace, reads, writes = [], [], []

    def snapshot():
        state = deepcopy(entry)
        state.update({"pc": pc, "a": a, "al": a % 256, "ah": a // 256,
                      "psw": psw, "cf": (psw // 32768) % 2,
                      "zf": (psw // 16384) % 2, "hc": (psw // 8192) % 2,
                      "dd": (psw // 4096) % 2, "otherPsw": psw % 4096,
                      "scb": psw % 8})
        state["locals"] = [data[f"{0x0108 + index:04X}"] for index in range(8)]
        state["er"] = [state["locals"][2 * index]
                       + 256 * state["locals"][2 * index + 1] for index in range(4)]
        return state

    def note(logical, form, origin, length, next_pc, next_al, next_psw,
             read_specs=(), write_specs=(), branch=None, external=False):
        nonlocal a, psw, pc
        if pc != origin:
            raise ValueError("Independent source formula sequence conflict")
        before = snapshot()
        step = len(trace) + 1
        these_reads, these_writes = [], []
        for address, width in read_specs:
            cells = [data[f"{address:04X}"]]
            if width == 16:
                cells.append(data[f"{address + 1:04X}"])
            value = sum(cell * (256 ** index) for index, cell in enumerate(cells))
            these_reads.append({"step": step, "logicalId": logical,
                                "syntheticPc": origin, "space": "DATA",
                                "address": address, "widthBits": width,
                                "value": value, "bytes": cells,
                                "provenance": PROVENANCE})
        for address, value, kind in write_specs:
            key = f"{address:04X}"
            old = data[key]
            these_writes.append({"step": step, "logicalId": logical,
                                 "syntheticPc": origin, "space": "DATA",
                                 "address": address, "widthBits": 8,
                                 "oldValue": old, "value": value,
                                 "ordinal": len(writes) + len(these_writes) + 1,
                                 "sameValue": old == value, "kind": kind,
                                 "provenance": PROVENANCE})
            data[key] = value
        a = (a // 256) * 256 + next_al
        psw, pc = next_psw, next_pc
        trace.append({"step": step, "syntheticPc": origin, "logicalId": logical,
                      "form": form, "length": length, "stateBefore": before,
                      "stateAfter": snapshot(), "dataReads": these_reads,
                      "dataWrites": these_writes, "branchTaken": branch,
                      "externalTransfer": "AbstractExternalContinuation_ExpectedOnly"
                      if external else None, "provenance": PROVENANCE})
        reads.extend(deepcopy(these_reads))
        writes.extend(deepcopy(these_writes))

    x, r0 = data["018E"], data["0108"]
    original117, original18f = data["0117"], data["018F"]
    word = data["0196"] + 256 * data["0197"]
    carry_from_shift = x // 128
    rotated = (2 * x + carry_from_shift) % 256
    mask = r0 & rotated
    below = word < 192

    # Common source prefix; all post-state values are independently specified.
    note(0x556F, "lb-a-page", 0x1000, 2, 0x1002, x,
         _loaded_psw(psw, x), ((0x018E, 8),))
    note(0x5571, "sllb-a", 0x1002, 1, 0x1003, (2 * x) % 256,
         _psw_flag(psw, 32768, carry_from_shift))
    note(0x5572, "rolb-page", 0x1003, 3, 0x1006, a % 256,
         _psw_flag(psw, 32768, x >= 128), ((0x018E, 8),),
         ((0x018E, rotated, "RMW"),))
    note(0x5575, "lb-a-r0", 0x1006, 1, 0x1007, r0,
         _loaded_psw(psw, r0), ((0x0108, 8),))
    note(0x5576, "andb-a-page", 0x1007, 2, 0x1009, mask,
         _psw_flag(psw, 16384, mask == 0), ((0x018E, 8),))
    compare_psw = _psw_flag(_psw_flag(psw, 32768, below), 16384, word == 192)
    note(0x5578, "cmp-page-imm16", 0x1009, 5, 0x100E, mask,
         compare_psw, ((0x0196, 16),))
    note(0x557D, "jlt-rel8", 0x100E, 2, 0x102A if below else 0x1010,
         mask, psw, branch=below)

    if below:
        path = "A"
        note(0x55BF, "lb-a-imm8", 0x102A, 2, 0x102C, 15,
             _loaded_psw(psw, 15))
        note(0x55C1, "stb-a-page", 0x102C, 2, 0x102E, 15, psw,
             write_specs=((0x0117, 15, "Store"),))
        note(0x55C3, "stb-a-page", 0x102E, 2, 0x1030, 15, psw,
             write_specs=((0x018F, 15, "Store"),))
        note("DirectJ_Below", "j-address", 0x1030, 3, 0x55C5, 15, psw,
             external=True)
    else:
        note(0x557F, "movb-r1-page", 0x1010, 3, 0x1013, mask, psw,
             ((0x0117, 8),), ((0x0109, original117, "LocalRegisterStore"),))
        and117 = original117 & mask
        note(0x5582, "andb-page-a", 0x1013, 3, 0x1016, mask,
             _psw_flag(psw, 16384, and117 == 0), ((0x0117, 8),),
             ((0x0117, and117, "RMW"),))
        first_gate = data["012A"] >= 128
        note(0x5585, "jbs-page-bit7", 0x1016, 3,
             0x1023 if first_gate else 0x1019, mask, psw,
             ((0x012A, 8),), branch=first_gate)
        if first_gate:
            path = "B"
        else:
            second_gate = (data["0124"] // 32) % 2 == 1
            note(0x5588, "jbs-page-bit5", 0x1019, 3,
                 0x1023 if second_gate else 0x101C, mask, psw,
                 ((0x0124, 8),), branch=second_gate)
            if second_gate:
                path = "C"
            else:
                path = "D"
                and18f = original18f & mask
                note(0x558B, "andb-page-a", 0x101C, 3, 0x101F, mask,
                     _psw_flag(psw, 16384, and18f == 0), ((0x018F, 8),),
                     ((0x018F, and18f, "RMW"),))
                or12a = data["012A"] | 1
                note(0x558E, "orb-page-imm8", 0x101F, 4, 0x1023, mask,
                     _psw_flag(psw, 16384, or12a == 0), ((0x012A, 8),),
                     ((0x012A, or12a, "RMW"),))
        final18f = data["018F"]
        note(0x5592, "lb-a-page", 0x1023, 2, 0x1025, final18f,
             _loaded_psw(psw, final18f), ((0x018F, 8),))
        final_al = final18f | 240
        note(0x5594, "orb-a-imm8", 0x1025, 2, 0x1027, final_al,
             _psw_flag(psw, 16384, final_al == 0))
        note("DirectJ_NotBelow", "j-address", 0x1027, 3, 0x5596,
             final_al, psw, external=True)

    if tuple(row["logicalId"] for row in trace) != PATHS[path]:
        raise ValueError("Independent literal path conflict")
    return {
        "classification": "StaticExpectedTrace_NoExecutionObservation",
        "scenarioId": scenario["id"], "path": path,
        "entryState": deepcopy(trace[0]["stateBefore"]),
        "terminalState": snapshot(), "terminalData": deepcopy(data),
        "instructionCount": len(trace), "originalInstructionCount": len(trace) - 1,
        "terminalPc": pc, "readCount": len(reads), "writeCount": len(writes),
        "trace": trace, "orderedReads": reads, "orderedWrites": writes,
        "programFetches": [
            {"step": row["step"], "space": "PROGRAM", "start": row["syntheticPc"],
             "endExclusive": row["syntheticPc"] + row["length"],
             "classification": "ExpectedSelectedInstructionExtent_NotObserved"}
            for row in trace
        ],
        "directJCount": 1, "actualSyntheticExecution": "NotRun",
        "externalExitObservation": "SyntheticExternalExitObservationNotRun",
        "historicalPathWitness": "StaticPrimaryAndInventedCoverage" if path == "C"
        else "HistoricalCorpusHasOriginalPathWitness_NotNewObservation",
    }


def self_check():
    """Bounded reference-only checks, before any analyzer comparison.

    Mathematical expectations and conservation checks are checked directly;
    no emulator, byte stream, file, actual execution or analyzer is consulted.
    """
    counts = {"A": (11, 5, 3), "B": (13, 9, 3),
              "C": (14, 10, 3), "D": (16, 12, 5)}
    write_addresses = {"A": (0x018E, 0x0117, 0x018F),
                       "B": (0x018E, 0x0109, 0x0117),
                       "C": (0x018E, 0x0109, 0x0117),
                       "D": (0x018E, 0x0109, 0x0117, 0x018F, 0x012A)}
    aggregate = sha256()
    cases, observed_paths, scbs = 0, set(), set()
    same_value_writes = 0
    for word in (0, 191, 192, 193, 255, 256, 65535):
        for gate_a, gate_b in ((0, 0), (128, 0), (0, 32), (129, 33)):
            for incoming_dd in (0, 1):
                for variant in range(8):
                    scenario = make_scenario(word, gate_a, gate_b, incoming_dd, variant)
                    untouched = deepcopy(scenario)
                    result = reference_case(scenario)
                    path = ("A" if word < 192 else "B" if gate_a & 128
                            else "C" if gate_b & 32 else "D")
                    terminal, initial = result["terminalState"], scenario["entry"]
                    original, final = scenario["data"], result["terminalData"]
                    x = original["018E"]
                    rotated = ((x << 1) & 255) | (x >> 7)
                    mask = original["0108"] & rotated
                    final18f = (15 if path == "A" else original["018F"] & mask
                                if path == "D" else original["018F"])
                    al = 15 if path == "A" else final18f | 240
                    checks = (
                        scenario == untouched, result["path"] == path,
                        (result["instructionCount"], result["readCount"],
                         result["writeCount"]) == counts[path],
                        tuple(row["logicalId"] for row in result["trace"]) == PATHS[path],
                        tuple(row["address"] for row in result["orderedWrites"])
                        == write_addresses[path],
                        terminal["pc"] == (0x55C5 if path == "A" else 0x5596),
                        terminal["a"] == (initial["ah"] << 8) | al,
                        terminal["ah"] == initial["ah"], terminal["al"] == al,
                        terminal["cf"] == int(word < 192), terminal["zf"] == 0,
                        terminal["dd"] == 0, terminal["hc"] == initial["hc"],
                        terminal["otherPsw"] == initial["otherPsw"],
                        terminal["psw"] == ((initial["psw"] & 0x2FFF)
                                            | (0x8000 if path == "A" else 0)),
                        terminal["pointingBanks"] == initial["pointingBanks"],
                        terminal["ssp"] == initial["ssp"], terminal["lrb"] == 33,
                        terminal["scb"] == initial["scb"], terminal["sf"] == UNKNOWN_SF,
                        final["018E"] == rotated, final["018F"] == final18f,
                        final["0117"] == (15 if path == "A" else original["0117"] & mask),
                        final["012A"] == (original["012A"] | (1 if path == "D" else 0)),
                        terminal["locals"][1] == (original["0109"] if path == "A"
                                                  else original["0117"]),
                        all(final[key] == original[key] for key in
                            ("0108", "010A", "010B", "010C", "010D", "010E", "010F",
                             "0124", "0128", "0196", "0197")),
                        [row["ordinal"] for row in result["orderedWrites"]]
                        == list(range(1, result["writeCount"] + 1)),
                        path != "B" or all(row["address"] != 0x0124
                                            for row in result["orderedReads"]),
                        all(0x1000 <= row["start"] < row["endExclusive"] <= 0x1033
                            for row in result["programFetches"]),
                        sum(row["externalTransfer"] is not None
                            for row in result["trace"]) == 1,
                        result["trace"][-1]["externalTransfer"]
                        == "AbstractExternalContinuation_ExpectedOnly",
                        result["actualSyntheticExecution"] == "NotRun",
                    )
                    if not all(checks):
                        raise ValueError("Independent self-check failure: "
                                         + scenario["id"] + ":"
                                         + str([i for i, value in enumerate(checks) if not value]))
                    for previous, following in zip(result["trace"], result["trace"][1:]):
                        if previous["stateAfter"] != following["stateBefore"]:
                            raise ValueError("Independent source-state continuity conflict")
                    aggregate.update(json.dumps(result, sort_keys=True, separators=(",", ":"),
                                                ensure_ascii=True).encode("ascii"))
                    same_value_writes += sum(row["sameValue"] for row in result["orderedWrites"])
                    cases += 1
                    observed_paths.add(path)
                    scbs.add(initial["scb"])
    return {"classification": "IndependentStaticReferenceSelfCheck_NoExecutionObservation",
            "baseSha": BASE_SHA, "manualSha256": MANUAL_SHA256,
            "compositeIdentityOnlySha256": COMPOSITE_SHA256,
            "cases": cases, "paths": sorted(observed_paths), "scbValues": sorted(scbs),
            "incomingDd": [0, 1], "sameValueWritesChecked": same_value_writes,
            "expectedCasesSha256": aggregate.hexdigest(), "failed": 0, "skipped": 0,
            "analyzerCalls": 0, "operationalCodecCalls": 0, "emitterCalls": 0,
            "CPUExecutions": 0, "actualROMExecutions": 0, "targetBinaryOutputs": 0,
            "actualSyntheticExecution": "NotRun", "passed": True}


if __name__ == "__main__":
    print(json.dumps(self_check(), sort_keys=True, separators=(",", ":")))
